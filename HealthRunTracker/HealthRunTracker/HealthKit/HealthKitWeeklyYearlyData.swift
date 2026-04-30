import HealthKit
import SwiftUI

extension HealthManager {

    // MARK: - Heart Rate Zones (legacy UI)
    func fetchWeeklyRunningData(for offset: Int) {
        let calendar = Calendar.current

        guard let ref = calendar.date(byAdding: .weekOfYear, value: offset, to: Date()),
              let interval = calendar.dateInterval(of: .weekOfYear, for: ref) else { return }

        let datePredicate = HKQuery.predicateForSamples(withStart: interval.start, end: interval.end)
        let runningPredicate = HKQuery.predicateForWorkouts(with: .running)
        let predicate = NSCompoundPredicate(andPredicateWithSubpredicates: [
            runningPredicate,
            datePredicate
        ])

        let query = HKSampleQuery(
            sampleType: .workoutType(),
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: nil
        ) { [weak self] _, samples, error in

            guard let self = self,
                  let workouts = samples as? [HKWorkout],
                  error == nil else {
                DispatchQueue.main.async {
                    self?.weeklyData = []
                    self?.weeklyZoneBreakdown = []
                }
                return
            }

            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "fr_FR")
            formatter.dateFormat = "E"

            var sessions: [DailyRunData] = []
            let outerGroup = DispatchGroup()

            for workout in workouts {
                outerGroup.enter()

                var zones: SessionZoneBreakdown?
                var timeline: [HeartRateSample] = []

                let innerGroup = DispatchGroup()

                // 1️⃣ Zones FC
                innerGroup.enter()
                self.computeZonesForWorkout(workout) {
                    zones = $0
                    innerGroup.leave()
                }

                // 2️⃣ Timeline FC
                innerGroup.enter()
                self.fetchHeartRateTimeline(for: workout) {
                    timeline = $0
                    innerGroup.leave()
                }

                // 3️⃣ Construire la séance UNE FOIS tout prêt
                innerGroup.notify(queue: .global()) {

                    let avgHR = workout.statistics(
                        for: HKQuantityType.quantityType(forIdentifier: .heartRate)!
                    )?
                    .averageQuantity()?
                    .doubleValue(for: HKUnit(from: "count/min")) ?? 0

                    let run = DailyRunData(
                        hkWorkout: workout,
                        id: workout.uuid,
                        date: workout.startDate,
                        distanceKm: (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000,
                        durationMin: workout.duration / 60,
                        elevationGainM: (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                            .doubleValue(for: .meter()) ?? 0,
                        dayLabel: formatter.string(from: workout.startDate),
                        averageHeartRate: avgHR,
                        z1: zones?.z1 ?? 0,
                        z2: zones?.z2 ?? 0,
                        z3: zones?.z3 ?? 0,
                        z4: zones?.z4 ?? 0,
                        z5: zones?.z5 ?? 0,
                        heartRateTimeline: timeline,
                        sessionType: nil,
                        predictedSessionType: nil,
                        sessionDetail: nil
                    )

                    sessions.append(run)
                    outerGroup.leave()
                }
            }

            outerGroup.notify(queue: .main) {
                let sortedSessions = sessions.sorted { $0.date < $1.date }

                self.syncService.fetchSessionMetadata(
                    startDate: interval.start,
                    endDate: interval.end
                ) { result in
                    DispatchQueue.main.async {
                        let enrichedSessions: [DailyRunData]

                        switch result {
                        case .success(let metadataList):
                            enrichedSessions = self.applyMetadata(metadataList, to: sortedSessions)
                            self.sessionMetadataErrorText = ""
                        case .failure(let error):
                            enrichedSessions = sortedSessions
                            self.sessionMetadataErrorText = error.localizedDescription
                        }

                        self.weeklyData = enrichedSessions
                        self.weeklyZoneBreakdown = enrichedSessions.map {
                            SessionZoneBreakdown(
                                workoutStart: $0.date,
                                z1: $0.z1,
                                z2: $0.z2,
                                z3: $0.z3,
                                z4: $0.z4,
                                z5: $0.z5
                            )
                        }
                    }
                }
            }
        }

        healthStore.execute(query)
    }
    
    func fetchYearlyRunningData(for offset: Int) {
        let calendar = Calendar.current

        guard let ref = calendar.date(byAdding: .year, value: offset, to: Date()),
              let interval = calendar.dateInterval(of: .year, for: ref) else { return }

        let datePredicate = HKQuery.predicateForSamples(withStart: interval.start, end: interval.end)
        let runningPredicate = HKQuery.predicateForWorkouts(with: .running)
        let predicate = NSCompoundPredicate(andPredicateWithSubpredicates: [runningPredicate, datePredicate])

        let query = HKSampleQuery(
            sampleType: .workoutType(),
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: nil
        ) { [weak self] _, samples, error in

            guard let workouts = samples as? [HKWorkout], error == nil else {
                DispatchQueue.main.async {
                    self?.yearlyData = []
                    self?.yearlySessionCount = 0
                }
                return
            }

            // Reset annual records
            var maxDistance: Double = 0
            var maxDuration: TimeInterval = 0
            var maxElevation: Double = 0

            var monthlyDict: [Int: MonthlyRunData] = [:]
            var daily: [Date: Double] = [:]
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "fr_FR")

            for workout in workouts {
                let wDistance = (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000
                let wDuration = workout.duration
                let wElevation = (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                    .doubleValue(for: .meter()) ?? 0

                // Track daily distance
                let day = calendar.startOfDay(for: workout.startDate)
                daily[day, default: 0] += wDistance

                if wDistance > maxDistance { maxDistance = wDistance }
                if wDuration > maxDuration { maxDuration = wDuration }
                if wElevation > maxElevation { maxElevation = wElevation }

                let month = calendar.component(.month, from: workout.startDate)
                let distKm = wDistance
                let durMin = wDuration / 60
                let elev = wElevation

                if let existing = monthlyDict[month] {
                    monthlyDict[month] = MonthlyRunData(
                        month: month,
                        distanceKm: existing.distanceKm + distKm,
                        durationMin: existing.durationMin + durMin,
                        elevationGainM: existing.elevationGainM + elev,
                        monthLabel: existing.monthLabel
                    )
                } else {
                    monthlyDict[month] = MonthlyRunData(
                        month: month,
                        distanceKm: distKm,
                        durationMin: durMin,
                        elevationGainM: elev,
                        monthLabel: formatter.shortMonthSymbols[month - 1].capitalized
                    )
                }
            }

            self?.longestRunDistance = maxDistance
            self?.longestRunDuration = maxDuration
            self?.biggestRunElevation = maxElevation

            DispatchQueue.main.async {
                self?.dailyDistances = daily
                self?.yearlyData = monthlyDict.values.sorted { $0.month < $1.month }
                self?.yearlySessionCount = workouts.count
                self?.updateTrainingLoad()
            }
        }

        healthStore.execute(query)
    }

    func computeWeeklyDistanceData(for yearOffset: Int = 0,
                                   completion: @escaping ([WeeklyDistanceData]) -> Void) {

        let calendar = Calendar.current

        guard let ref = calendar.date(byAdding: .year, value: yearOffset, to: Date()),
              let interval = calendar.dateInterval(of: .year, for: ref) else {
            completion([])
            return
        }

        let datePredicate = HKQuery.predicateForSamples(withStart: interval.start, end: interval.end)
        let runningPredicate = HKQuery.predicateForWorkouts(with: .running)
        let predicate = NSCompoundPredicate(andPredicateWithSubpredicates: [runningPredicate, datePredicate])

        let query = HKSampleQuery(
            sampleType: .workoutType(),
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: nil   // <-- IMPORTANT
        ) { _, samples, error in

            guard let workouts = samples as? [HKWorkout], error == nil else {
                completion([])
                return
            }

            var totals: [Int: Double] = [:]

            for w in workouts {
                let week = calendar.component(.weekOfYear, from: w.startDate)
                totals[week, default: 0] += (w.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000
            }

            completion(
                totals.keys.sorted().map {
                    WeeklyDistanceData(weekNumber: $0, distanceKm: totals[$0]!)
                }
            )
        }

        healthStore.execute(query)
    }
}
