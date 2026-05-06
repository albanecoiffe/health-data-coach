// Il ne fait plus que : appeler le Reader, appeler le Calculator, appeler le SyncService, exposer du @Published


import Foundation
import HealthKit
import MapKit
import Combine
import SwiftUI

final class HealthManager: ObservableObject {
    // Dependencies
    let reader = HealthKitReader()
    let syncService: RunSessionSyncService
    
    
    let healthStore = HKHealthStore()

    
    init(session: UserSession) {
        self.syncService = RunSessionSyncService(
            baseURL: APIConfig.baseURL,
            userId: session.userId
        )
    }
    
    // Published state
    @Published var weeklyData: [DailyRunData] = []
    @Published var yearlyData: [MonthlyRunData] = []
    @Published var weeklyZoneBreakdown: [SessionZoneBreakdown] = []

    @Published var yearlySessionCount: Int = 0
    @Published var dailyDistances: [Date : Double] = [:]

    @Published var longestRunDistance: Double = 0      // km
    @Published var longestRunDuration: TimeInterval = 0
    @Published var biggestRunElevation: Double = 0     // m

    @Published var sevenDayLoad: Double = 0
    @Published var twentyEightDayLoad: Double = 0
    @Published var loadRatio: Double = 0
    @Published var weeklyHRZones: [String: Double] = Dictionary(
        uniqueKeysWithValues: HeartRateZones.definitions.map { ($0.label, 0.0) }
    )
    @Published var weeklyZoneArray: [HeartRateZoneData] = []
    @Published var syncStatusText: String = "Idle"
    @Published var syncInsertedCount: Int = 0
    @Published var syncUpdatedCount: Int = 0
    @Published var syncDuplicateCount: Int = 0
    @Published var syncErrorCount: Int = 0
    @Published var syncSkippedCount: Int = 0
    @Published var syncIsRunning: Bool = false
    @Published var syncLastErrorText: String = ""
    @Published var sessionMetadataErrorText: String = ""
    @Published var isLoadingWeeklyData: Bool = false

    private var didStartAutomaticSync = false
    private var activeWeeklyRequestID = UUID()

    func beginWeeklyRequest() -> UUID {
        let requestID = UUID()
        activeWeeklyRequestID = requestID
        isLoadingWeeklyData = true
        return requestID
    }

    func isCurrentWeeklyRequest(_ requestID: UUID) -> Bool {
        activeWeeklyRequestID == requestID
    }

    func finishWeeklyRequest(_ requestID: UUID) {
        guard isCurrentWeeklyRequest(requestID) else { return }
        isLoadingWeeklyData = false
    }

    func applyMetadata(
        _ metadataList: [RunSessionMetadata],
        to sessions: [DailyRunData]
    ) -> [DailyRunData] {
        let metadataEntries = metadataList.compactMap { metadata -> (date: Date, metadata: RunSessionMetadata)? in
            guard let date = metadata.startDate else { return nil }
            return (date, metadata)
        }

        let enrichedSessions = sessions.map { session in
            let matched = metadataEntries
                .map { entry in
                    (
                        delta: abs(entry.date.timeIntervalSince(session.date)),
                        metadata: entry.metadata
                    )
                }
                .filter { $0.delta <= 180 }
                .min { $0.delta < $1.delta }

            guard let metadata = matched?.metadata else {
                return session
            }

            return DailyRunData(
                hkWorkout: session.hkWorkout,
                id: session.id,
                date: session.date,
                distanceKm: session.distanceKm,
                durationMin: session.durationMin,
                elevationGainM: session.elevationGainM,
                dayLabel: session.dayLabel,
                averageHeartRate: session.averageHeartRate,
                z1: session.z1,
                z2: session.z2,
                z3: session.z3,
                z4: session.z4,
                z5: session.z5,
                heartRateTimeline: session.heartRateTimeline,
                mergedIntoStartTime: metadata.mergedIntoStartDate,
                sessionType: metadata.session_type,
                predictedSessionType: metadata.predicted_session_type,
                sessionDetail: metadata.session_detail
            )
        }

        return collapseMergedSessions(enrichedSessions)
    }

    func updateSessionMetadata(
        for session: DailyRunData,
        sessionType: String?,
        sessionDetail: String?,
        completion: ((Result<Void, Error>) -> Void)? = nil
    ) {
        syncService.updateSessionMetadata(
            startDate: session.date,
            sessionType: sessionType,
            sessionDetail: sessionDetail
        ) { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let metadata):
                    self.weeklyData = self.applyMetadata([metadata], to: self.weeklyData)
                    self.weeklyZoneBreakdown = self.weeklyData.map {
                        SessionZoneBreakdown(
                            workoutStart: $0.date,
                            z1: $0.z1,
                            z2: $0.z2,
                            z3: $0.z3,
                            z4: $0.z4,
                            z5: $0.z5
                        )
                    }
                    self.sessionMetadataErrorText = ""
                    completion?(.success(()))
                case .failure(let error):
                    self.sessionMetadataErrorText = error.localizedDescription
                    completion?(.failure(error))
                }
            }
        }
    }

    func mergeWorkoutDetails(
        _ detailedSessions: [DailyRunData],
        into sessions: [DailyRunData]
    ) -> [DailyRunData] {
        let detailsByID = Dictionary(uniqueKeysWithValues: detailedSessions.map { ($0.id, $0) })

        return collapseMergedSessions(
            sessions.map { session in
                guard let detailed = detailsByID[session.id] else {
                    return session
                }

                return DailyRunData(
                    hkWorkout: detailed.hkWorkout,
                    id: detailed.id,
                    date: detailed.date,
                    distanceKm: detailed.distanceKm,
                    durationMin: detailed.durationMin,
                    elevationGainM: detailed.elevationGainM,
                    dayLabel: detailed.dayLabel,
                    averageHeartRate: detailed.averageHeartRate,
                    z1: detailed.z1,
                    z2: detailed.z2,
                    z3: detailed.z3,
                    z4: detailed.z4,
                    z5: detailed.z5,
                    heartRateTimeline: detailed.heartRateTimeline,
                    mergedIntoStartTime: session.mergedIntoStartTime,
                    sessionType: session.sessionType,
                    predictedSessionType: session.predictedSessionType,
                    sessionDetail: session.sessionDetail
                )
            }
            .sorted(by: { $0.date < $1.date })
        )
    }

    func mergeSessions(
        primary: DailyRunData,
        secondary: DailyRunData,
        completion: ((Result<Void, Error>) -> Void)? = nil
    ) {
        syncService.mergeSessions(
            primaryStartDate: primary.date,
            secondaryStartDate: secondary.date
        ) { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let metadataList):
                    self.weeklyData = self.applyMetadata(metadataList, to: self.weeklyData)
                    self.weeklyZoneBreakdown = self.weeklyData.map {
                        SessionZoneBreakdown(
                            workoutStart: $0.date,
                            z1: $0.z1,
                            z2: $0.z2,
                            z3: $0.z3,
                            z4: $0.z4,
                            z5: $0.z5
                        )
                    }
                    self.sessionMetadataErrorText = ""
                    completion?(.success(()))
                case .failure(let error):
                    self.sessionMetadataErrorText = error.localizedDescription
                    completion?(.failure(error))
                }
            }
        }
    }

    private func collapseMergedSessions(_ sessions: [DailyRunData]) -> [DailyRunData] {
        let sortedSessions = sessions.sorted(by: { $0.date < $1.date })

        func matches(_ left: Date, _ right: Date) -> Bool {
            abs(left.timeIntervalSince(right)) <= 180
        }

        var childrenByAnchor: [UUID: [DailyRunData]] = [:]
        var hiddenSessionIDs = Set<UUID>()

        for session in sortedSessions {
            guard let mergedIntoStartTime = session.mergedIntoStartTime else { continue }

            guard let anchor = sortedSessions.first(where: {
                matches($0.date, mergedIntoStartTime) && $0.id != session.id
            }) else {
                continue
            }

            childrenByAnchor[anchor.id, default: []].append(session)
            hiddenSessionIDs.insert(session.id)
        }

        return sortedSessions.compactMap { session in
            guard !hiddenSessionIDs.contains(session.id) else { return nil }
            let children = childrenByAnchor[session.id] ?? []
            guard !children.isEmpty else { return session }
            return mergedSession(anchor: session, children: children)
        }
    }

    private func mergedSession(anchor: DailyRunData, children: [DailyRunData]) -> DailyRunData {
        let allSessions = ([anchor] + children).sorted(by: { $0.date < $1.date })
        let totalDuration = allSessions.reduce(0.0) { $0 + $1.durationMin }
        let weightedHR = allSessions.reduce(0.0) { partial, session in
            partial + (resolvedAverageHeartRate(for: session) * session.durationMin)
        }

        return DailyRunData(
            hkWorkout: anchor.hkWorkout,
            id: anchor.id,
            date: anchor.date,
            distanceKm: allSessions.reduce(0.0) { $0 + $1.distanceKm },
            durationMin: totalDuration,
            elevationGainM: allSessions.reduce(0.0) { $0 + $1.elevationGainM },
            dayLabel: anchor.dayLabel,
            averageHeartRate: totalDuration > 0 ? weightedHR / totalDuration : anchor.averageHeartRate,
            z1: allSessions.reduce(0.0) { $0 + $1.z1 },
            z2: allSessions.reduce(0.0) { $0 + $1.z2 },
            z3: allSessions.reduce(0.0) { $0 + $1.z3 },
            z4: allSessions.reduce(0.0) { $0 + $1.z4 },
            z5: allSessions.reduce(0.0) { $0 + $1.z5 },
            heartRateTimeline: allSessions
                .flatMap(\.heartRateTimeline)
                .sorted(by: { $0.timeOffset < $1.timeOffset }),
            mergedIntoStartTime: nil,
            sessionType: anchor.sessionType,
            predictedSessionType: anchor.predictedSessionType,
            sessionDetail: anchor.sessionDetail
        )
    }

    private func resolvedAverageHeartRate(for session: DailyRunData) -> Double {
        if session.averageHeartRate > 0 {
            return session.averageHeartRate
        }

        guard !session.heartRateTimeline.isEmpty else {
            return 0
        }

        let bpmSum = session.heartRateTimeline.reduce(0.0) { $0 + $1.bpm }
        return bpmSum / Double(session.heartRateTimeline.count)
    }

    func refreshMetadata(for session: DailyRunData) {
        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: session.date)
        guard let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay) else {
            return
        }

        syncService.fetchSessionMetadata(
            startDate: startOfDay,
            endDate: endOfDay
        ) { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let metadataList):
                    self.weeklyData = self.applyMetadata(metadataList, to: self.weeklyData)
                    self.weeklyZoneBreakdown = self.weeklyData.map {
                        SessionZoneBreakdown(
                            workoutStart: $0.date,
                            z1: $0.z1,
                            z2: $0.z2,
                            z3: $0.z3,
                            z4: $0.z4,
                            z5: $0.z5
                        )
                    }
                    self.sessionMetadataErrorText = ""
                case .failure(let error):
                    self.sessionMetadataErrorText = error.localizedDescription
                }
            }
        }
    }

    func startAutomaticSyncOnLaunch() {
        guard !didStartAutomaticSync else { return }
        didStartAutomaticSync = true
        requestAuthorization(syncAfterSuccess: true)
    }

    func syncRecentRunSessionsWhenAppBecomesActive() {
        guard didStartAutomaticSync else {
            startAutomaticSyncOnLaunch()
            return
        }
        guard !syncIsRunning else { return }
        syncRecentRunSessionsOnLaunch()
    }
    
    func requestAuthorization(syncAfterSuccess: Bool = false) {
        guard HKHealthStore.isHealthDataAvailable() else {
            print("⚠️ HealthKit non disponible (simulateur ?)")
            syncStatusText = "HealthKit indisponible (simulateur ?)"
            return
        }

        let readTypes: Set<HKObjectType> = [
            HKObjectType.workoutType(),
            HKQuantityType.quantityType(forIdentifier: .distanceWalkingRunning)!,
            HKQuantityType.quantityType(forIdentifier: .heartRate)!,
            HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned)!,
            HKSeriesType.workoutRoute()   // ROUTES GPS
        ]

        healthStore.requestAuthorization(toShare: [], read: readTypes) { success, error in
            DispatchQueue.main.async {
                if success {
                    self.syncStatusText = "HealthKit autorise."
                } else {
                    self.syncStatusText = "Autorisation HealthKit refusee."
                    self.syncLastErrorText = error?.localizedDescription ?? "erreur inconnue"
                }
            }
            if success {
                self.fetchWeeklyRunningData(for: 0)
                self.fetchYearlyRunningData(for: 0)
                if syncAfterSuccess {
                    self.syncRecentRunSessionsOnLaunch()
                }
            } else {
                print("❌ Refus HealthKit :", error?.localizedDescription ?? "Erreur inconnue")
            }
        }
    }

    func testBackendConnection() {
        syncStatusText = "Test connexion backend..."
        syncLastErrorText = ""
        syncService.pingBackend { result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    self.syncStatusText = "Backend joignable."
                case .failure(let error):
                    self.syncStatusText = "Backend inaccessible."
                    self.syncLastErrorText = error.localizedDescription
                }
            }
        }
    }

    func fetchRunSessionsClean(
        from start: Date,
        to end: Date,
        completion: @escaping ([RunSession]) -> Void
    ) {

        reader.fetchRunningWorkouts(from: start, to: end) { workouts in

            let group = DispatchGroup()
            var sessions: [RunSession] = []

            for workout in workouts {
                group.enter()

                self.reader.fetchHeartRateSamples(for: workout) { hrSamples in

                    let samples = HealthMetricsCalculator.buildSamples(from: hrSamples)

                    let zones = HealthMetricsCalculator.computeZones(samples: samples)

                    let hrValues = hrSamples.map {
                        $0.quantity.doubleValue(
                            for: HKUnit(from: "count/min")
                        )
                    }

                    let avgHR = HealthMetricsCalculator.averageHR(hrValues)

                    let distanceKm =
                        (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000

                    let durationMin = workout.duration / 60

                    let elevation =
                        (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                            .doubleValue(for: .meter())

                    let kcal =
                        workout.statistics(
                            for: HKQuantityType.quantityType(
                                forIdentifier: .activeEnergyBurned
                            )!
                        )?
                        .sumQuantity()?
                        .doubleValue(for: .kilocalorie())

                    let session = RunSession(
                        startDate: workout.startDate,
                        distanceKm: distanceKm,
                        durationMin: durationMin,
                        avgHR: avgHR,
                        z1: zones.z1,
                        z2: zones.z2,
                        z3: zones.z3,
                        z4: zones.z4,
                        z5: zones.z5,
                        elevationGainM: elevation,
                        activeKcal: kcal
                    )

                    sessions.append(session)
                    group.leave()
                }
            }

            group.notify(queue: .main) {
                completion(
                    sessions.sorted(by: { $0.startDate < $1.startDate })
                )
            }
        }
    }
    
    // Rebuild complet (manuel / exceptionnel) 
    //  Méthode de rechargement complet
    // Ce qu’elle fait exactement :
        // relit tout HealthKit sur 24 mois,
        // relit tout HealthKit sur 24 mois,
        // relit tout HealthKit sur 24 mois,
        // relit tout HealthKit sur 24 mois
        
    func syncRunSessionsClean() {

        let calendar = Calendar.current
        let end = Date()
        let start = calendar.date(byAdding: .month, value: -24, to: end)!

        fetchRunSessionsClean(from: start, to: end) { sessions in
            print("🚀 CLEAN sync sessions:", sessions.count)

            for session in sessions {
                self.syncService.upload(session)
            }
        }
    }

    func syncRunSessions(lastMonths: Int = 24) {
        let calendar = Calendar.current
        let end = Date()
        let start = calendar.date(byAdding: .month, value: -lastMonths, to: end)!
        runSync(from: start, to: end, label: "\(lastMonths) mois")
    }

    func syncRecentRunSessionsOnLaunch() {
        syncLatestRunSessions()
    }

    func syncLatestRunSessions() {
        guard !syncIsRunning else { return }

        syncStatusText = "Recherche derniere seance en base..."
        syncLastErrorText = ""

        syncService.fetchLatestSessionStartTime { result in
            let calendar = Calendar.current
            let end = Date()

            let start: Date
            let label: String

            switch result {
            case .success(let latestStartTime):
                if let latestStartTime {
                    start = calendar.date(byAdding: .day, value: -2, to: latestStartTime) ?? latestStartTime
                    label = "nouveautes depuis derniere seance"
                } else {
                    start = calendar.date(byAdding: .month, value: -24, to: end)!
                    label = "premiere synchro 24 mois"
                }
            case .failure(let error):
                DispatchQueue.main.async {
                    self.syncStatusText = "Impossible de lire la derniere seance."
                    self.syncLastErrorText = error.localizedDescription
                }
                return
            }

            DispatchQueue.main.async {
                self.runSync(from: start, to: end, label: label)
            }
        }
    }

    func syncAllRunSessionsHistory() {
        let end = Date()
        var components = DateComponents()
        components.year = 2000
        components.month = 1
        components.day = 1
        let start = Calendar.current.date(from: components) ?? Date.distantPast
        runSync(from: start, to: end, label: "historique complet")
    }

    private func runSync(from start: Date, to end: Date, label: String) {
        if syncIsRunning {
            return
        }

        syncIsRunning = true
        syncStatusText = "Collecte HealthKit (\(label))..."
        syncInsertedCount = 0
        syncUpdatedCount = 0
        syncDuplicateCount = 0
        syncErrorCount = 0
        syncSkippedCount = 0
        syncLastErrorText = ""

        fetchRunSessionsClean(from: start, to: end) { sessions in
            let export = self.prepareSessionsForExport(sessions)

            DispatchQueue.main.async {
                self.syncSkippedCount = export.skippedCount
            }

            guard !export.sessions.isEmpty else {
                DispatchQueue.main.async {
                    self.syncStatusText = export.skippedCount > 0
                        ? "Aucune seance exportable. ignorees=\(export.skippedCount)"
                        : "Aucune seance trouvee."
                    self.syncIsRunning = false
                }
                return
            }

            DispatchQueue.main.async {
                self.syncStatusText = "Envoi \(export.sessions.count) seances (\(label))..."
            }

            let batchSize = 40
            let batches = stride(from: 0, to: export.sessions.count, by: batchSize).map { start in
                Array(export.sessions[start..<min(start + batchSize, export.sessions.count)])
            }

            func sendBatch(_ index: Int) {
                if index >= batches.count {
                    DispatchQueue.main.async {
                        self.syncStatusText = "Termine. inserted=\(self.syncInsertedCount), updated=\(self.syncUpdatedCount), duplicate=\(self.syncDuplicateCount), skipped=\(self.syncSkippedCount), errors=\(self.syncErrorCount)"
                        self.syncIsRunning = false
                    }
                    return
                }

                let batch = batches[index]
                self.syncService.uploadBatch(batch, timeout: 180) { result in
                    DispatchQueue.main.async {
                        switch result {
                        case .success(let response):
                            self.syncInsertedCount += response.inserted ?? 0
                            self.syncUpdatedCount += response.updated ?? 0
                            self.syncDuplicateCount += response.duplicates ?? 0
                        case .failure(let error):
                            self.syncErrorCount += batch.count
                            if self.syncLastErrorText.isEmpty {
                                self.syncLastErrorText = error.localizedDescription
                            }
                        }

                        self.syncStatusText = "Envoi lot \(index + 1)/\(batches.count)... inserted=\(self.syncInsertedCount), updated=\(self.syncUpdatedCount), duplicate=\(self.syncDuplicateCount), skipped=\(self.syncSkippedCount), errors=\(self.syncErrorCount)"
                    }
                    sendBatch(index + 1)
                }
            }

            sendBatch(0)
        }
    }

    private func prepareSessionsForExport(_ sessions: [RunSession]) -> (sessions: [RunSession], skippedCount: Int) {
        let now = Date()
        let maxFutureTolerance: TimeInterval = 5 * 60

        let valid = sessions.filter { session in
            guard session.startDate <= now.addingTimeInterval(maxFutureTolerance) else { return false }
            guard session.distanceKm.isFinite, session.durationMin.isFinite else { return false }
            guard session.distanceKm > 0, session.durationMin > 0 else { return false }
            guard session.distanceKm <= 200, session.durationMin <= 24 * 60 else { return false }

            let zones = [session.z1, session.z2, session.z3, session.z4, session.z5]
            guard zones.allSatisfy({ $0.isFinite && $0 >= 0 }) else { return false }

            if let avgHR = session.avgHR {
                guard avgHR.isFinite, (30...230).contains(avgHR) else { return false }
            }
            if let elevation = session.elevationGainM {
                guard elevation.isFinite, elevation >= 0, elevation <= 10000 else { return false }
            }
            if let kcal = session.activeKcal {
                guard kcal.isFinite, kcal >= 0, kcal <= 20000 else { return false }
            }

            return true
        }

        return (valid, sessions.count - valid.count)
    }

}
