// lit HealthKit → modèles Swift bruts
// Responsabilités autorisées
// HKSampleQuery
// HKStatisticsQuery
// HKWorkoutRouteQuery
// transformation HKWorkout → données brutes

import HealthKit
import Foundation

final class HealthKitReader {

    let healthStore = HKHealthStore()

    func requestAuthorization(completion: @escaping (Bool) -> Void) {
        let types: Set<HKObjectType> = [
            .workoutType(),
            HKQuantityType.quantityType(forIdentifier: .heartRate)!,
            HKQuantityType.quantityType(forIdentifier: .distanceWalkingRunning)!,
            HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned)!
        ]

        healthStore.requestAuthorization(toShare: [], read: types) { ok, _ in
            completion(ok)
        }
    }

    func fetchRunningWorkouts(
        from start: Date,
        to end: Date,
        completion: @escaping ([HKWorkout]) -> Void
    ) {

        let predicate = NSCompoundPredicate(andPredicateWithSubpredicates: [
            HKQuery.predicateForWorkouts(with: .running),
            HKQuery.predicateForSamples(withStart: start, end: end)
        ])

        let query = HKSampleQuery(
            sampleType: .workoutType(),
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: [
                NSSortDescriptor(
                    key: HKSampleSortIdentifierStartDate,
                    ascending: true
                )
            ]
        ) { _, samples, _ in
            completion(samples as? [HKWorkout] ?? [])
        }

        healthStore.execute(query)
    }

    func fetchHeartRateSamples(
        for workout: HKWorkout,
        completion: @escaping ([HKQuantitySample]) -> Void
    ) {
        let type = HKQuantityType.quantityType(forIdentifier: .heartRate)!

        let predicate = HKQuery.predicateForSamples(
            withStart: workout.startDate,
            end: workout.endDate,
            options: .strictStartDate
        )

        let query = HKSampleQuery(
            sampleType: type,
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: [
                NSSortDescriptor(
                    key: HKSampleSortIdentifierStartDate,
                    ascending: true
                )
            ]
        ) { _, samples, _ in
            completion(samples as? [HKQuantitySample] ?? [])
        }

        healthStore.execute(query)
    }
    
    func resolveElevationGain(
        for workout: HKWorkout,
        completion: @escaping (Double) -> Void
    ) {
        // 1️⃣ Tentative directe via metadata Apple
        if let elevation =
            (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                .doubleValue(for: .meter()) {

            completion(elevation)
            return
        }

        // 2️⃣ Fallback (aucune donnée fiable)
        completion(0)
    }
    
    func fetchActiveEnergy(
        for workout: HKWorkout,
        completion: @escaping (Double?) -> Void
    ) {
        guard let type = HKQuantityType.quantityType(
            forIdentifier: .activeEnergyBurned
        ) else {
            completion(nil)
            return
        }

        let predicate = HKQuery.predicateForSamples(
            withStart: workout.startDate,
            end: workout.endDate,
            options: .strictStartDate
        )

        let query = HKStatisticsQuery(
            quantityType: type,
            quantitySamplePredicate: predicate,
            options: .cumulativeSum
        ) { _, result, _ in
            completion(
                result?.sumQuantity()?.doubleValue(for: .kilocalorie())
            )
        }

        healthStore.execute(query)
    }
}
