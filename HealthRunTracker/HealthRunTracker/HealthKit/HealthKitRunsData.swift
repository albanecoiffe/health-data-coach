import HealthKit

extension HealthManager {
    
    func fetchRuns(
        from startDate: Date,
        to endDate: Date,
        completion: @escaping ([DailyRunData]) -> Void
    ) {
        
        
        
        let datePredicate = HKQuery.predicateForSamples(
            withStart: startDate,
            end: endDate,
            options: .strictStartDate
        )
        
        
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
                completion([])
                return
            }
            
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "fr_FR")
            formatter.dateFormat = "yyyy-MM-dd"
            
            let group = DispatchGroup()
            var results: [DailyRunData] = []
            
            for workout in workouts {
                group.enter()
                
                self.computeZonesForWorkout(workout) { zones in
                    
                    let avgHR = workout.statistics(
                        for: HKQuantityType.quantityType(forIdentifier: .heartRate)!
                    )?
                        .averageQuantity()?
                        .doubleValue(for: HKUnit(from: "count/min")) ?? 0
                    
                    let run = DailyRunData(
                        hkWorkout: workout,
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
                        z5: zones?.z5 ?? 0, heartRateTimeline: []
                    )
                    
                    results.append(run)
                    group.leave()
                }
            }
            
            group.notify(queue: .main) {
                completion(results)
            }
        }
        
        healthStore.execute(query)
    }
    
    func fetchWeeklyRuns(for offset: Int, completion: @escaping ([DailyRunData]) -> Void) {

        let calendar = Calendar.current

        guard let ref = calendar.date(byAdding: .weekOfYear, value: offset, to: Date()),
              let interval = calendar.dateInterval(of: .weekOfYear, for: ref) else {
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
            sortDescriptors: nil
        ) { _, samples, error in

            guard let workouts = samples as? [HKWorkout], error == nil else {
                completion([])
                return
            }

            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "fr_FR")
            formatter.dateFormat = "E"

            let data = workouts.map { workout in
                let avgHR = workout.statistics(for: HKQuantityType.quantityType(forIdentifier: .heartRate)!)?
                    .averageQuantity()?
                    .doubleValue(for: HKUnit(from: "count/min")) ?? 0
                return DailyRunData(
                    hkWorkout: workout,
                    date: workout.startDate,
                    distanceKm: (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000,
                    durationMin: workout.duration / 60,
                    elevationGainM: (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                        .doubleValue(for: .meter()) ?? 0,
                    dayLabel: formatter.string(from: workout.startDate),
                    averageHeartRate: avgHR,
                    z1: 0, z2: 0, z3: 0, z4: 0, z5: 0, heartRateTimeline: []
                )


            }

            completion(data)
        }

        healthStore.execute(query)
    }
}
