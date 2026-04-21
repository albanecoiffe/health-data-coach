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

    private var didStartAutomaticSync = false

    func startAutomaticSyncOnLaunch() {
        guard !didStartAutomaticSync else { return }
        didStartAutomaticSync = true
        requestAuthorization(syncAfterSuccess: true)
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
                    sessions.sorted { $0.startDate < $1.startDate }
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
        let calendar = Calendar.current
        let end = Date()
        let start = calendar.date(byAdding: .month, value: -24, to: end)!
        runSync(from: start, to: end, label: "mise a jour auto 24 mois")
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
