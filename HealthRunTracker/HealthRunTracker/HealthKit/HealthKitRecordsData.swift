import HealthKit

extension HealthManager {

    func computeRecords(completion: @escaping ([RunRecord]) -> Void) {
        let query = HKSampleQuery(
            sampleType: .workoutType(),
            predicate: HKQuery.predicateForWorkouts(with: .running),
            limit: HKObjectQueryNoLimit,
            sortDescriptors: nil
        ) { _, samples, error in

            guard let workouts = samples as? [HKWorkout], error == nil else {
                completion([])
                return
            }

            let targets: [Double] = [10.0, 21.1, 42.195]  // km
            var results: [RunRecord] = []

            for target in targets {
                // Chercher toutes les séances qui font au moins la distance
                let candidates = workouts.filter {
                    ($0.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000 >= target
                }

                guard !candidates.isEmpty else { continue }

                // Meilleure séance = celle avec la durée la plus courte
                if let best = candidates.min(by: { $0.duration < $1.duration }) {

                    let year = Calendar.current.component(.year, from: best.startDate)

                    results.append(
                        RunRecord(
                            distanceTarget: target,
                            bestTime: best.duration,
                            yearAchieved: year
                        )
                    )
                }
            }

            completion(results)
        }

        healthStore.execute(query)
    }

    func computeCumulativeWeekly(for yearOffset: Int) -> [WeeklyDistanceData] {
        let calendar = Calendar.current

        guard let ref = calendar.date(byAdding: .year, value: yearOffset, to: Date()),
              let interval = calendar.dateInterval(of: .year, for: ref) else {
            return []
        }

        let datePredicate = HKQuery.predicateForSamples(withStart: interval.start, end: interval.end)
        let runningPredicate = HKQuery.predicateForWorkouts(with: .running)
        let predicate = NSCompoundPredicate(andPredicateWithSubpredicates: [runningPredicate, datePredicate])

        var results: [WeeklyDistanceData] = []

        let semaphore = DispatchSemaphore(value: 0)

        let query = HKSampleQuery(
            sampleType: .workoutType(),
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: nil
        ) { _, samples, error in

            guard let workouts = samples as? [HKWorkout], error == nil else {
                semaphore.signal()
                return
            }

            var weeklyTotals: [Int: Double] = [:]

            for w in workouts {
                let week = calendar.component(.weekOfYear, from: w.startDate)
                let dist = (w.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000
                weeklyTotals[week, default: 0] += dist
            }

            // Tri par numéro de semaine
            let sorted = weeklyTotals.keys.sorted()

            // Calcul cumulé
            var cumulative: Double = 0
            results = sorted.map { week in
                cumulative += weeklyTotals[week]!
                return WeeklyDistanceData(weekNumber: week, distanceKm: cumulative)
            }

            semaphore.signal()
        }

        healthStore.execute(query)
        semaphore.wait()

        return results
    }
}
