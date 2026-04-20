import HealthKit

extension HealthManager {
    func computeZonesForWorkout(_ workout: HKWorkout, completion: @escaping (SessionZoneBreakdown?) -> Void) {
        let hrType = HKQuantityType.quantityType(forIdentifier: .heartRate)!
        let predicate = HKQuery.predicateForSamples(
            withStart: workout.startDate,
            end: workout.endDate,
            options: .strictStartDate
        )
        
        let query = HKSampleQuery(
            sampleType: hrType,
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]
        ) { _, samples, error in
            
            if let error = error {
                print("❌ HR Query error:", error.localizedDescription)
                completion(nil)
                return
            }
            
            // 2️⃣ si pas d'échantillons HR → fin
            guard let hrSamples = samples as? [HKQuantitySample], hrSamples.count > 1 else {
                completion(nil)
                return
            }
            
            
            var z1 = 0.0
            var z2 = 0.0
            var z3 = 0.0
            var z4 = 0.0
            var z5 = 0.0
            
            for i in 0..<hrSamples.count - 1 {
                let s1 = hrSamples[i]
                let s2 = hrSamples[i + 1]
                
                let hr1 = s1.quantity.doubleValue(for: HKUnit(from: "count/min"))
                let hr2 = s2.quantity.doubleValue(for: HKUnit(from: "count/min"))
                let hr = (hr1 + hr2) / 2.0
                let dt = s2.startDate.timeIntervalSince(s1.startDate) / 60.0  // minutes
                
                switch hr {
                case ..<HRZones.z1Upper:
                    z1 += dt
                case HRZones.z1Upper..<HRZones.z2Upper:
                    z2 += dt
                case HRZones.z2Upper..<HRZones.z3Upper:
                    z3 += dt
                case HRZones.z3Upper..<HRZones.z4Upper:
                    z4 += dt
                default:
                    z5 += dt
                }
                
            }
            
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "fr_FR")
            formatter.dateFormat = "E"
            
            let label = formatter.string(from: workout.startDate)
            
            completion(
                SessionZoneBreakdown(
                    workoutStart: workout.startDate,
                    z1: z1,
                    z2: z2,
                    z3: z3,
                    z4: z4,
                    z5: z5
                )
            )
        }
        
        healthStore.execute(query)
    }
}

extension HealthManager {

    func fetchHeartRateTimeline(
        for workout: HKWorkout,
        completion: @escaping ([HeartRateSample]) -> Void
    ) {

        let hrType = HKQuantityType.quantityType(forIdentifier: .heartRate)!
        let predicate = HKQuery.predicateForSamples(
            withStart: workout.startDate,
            end: workout.endDate,
            options: .strictStartDate
        )

        let query = HKSampleQuery(
            sampleType: hrType,
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: [
                NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)
            ]
        ) { _, samples, error in

            guard let samples = samples as? [HKQuantitySample], error == nil else {
                completion([])
                return
            }

            let timeline: [HeartRateSample] = samples.map { s in
                HeartRateSample(
                    timeOffset: s.startDate.timeIntervalSince(workout.startDate),
                    bpm: s.quantity.doubleValue(for: HKUnit(from: "count/min"))
                )
            }

            completion(timeline)
        }

        healthStore.execute(query)
    }
}
