import HealthKit

final class HealthKitObserver {
    private var lastSyncedWorkoutStart: Date?
    private let healthStore = HKHealthStore()
    private let reader: HealthKitReader
    private let syncService: RunSessionSyncService

    init(
        reader: HealthKitReader,
        syncService: RunSessionSyncService
    ) {
        self.reader = reader
        self.syncService = syncService
    }

    func start() {

        let workoutType = HKObjectType.workoutType()

        print("👀 HealthKitObserver started")

        let query = HKObserverQuery(
            sampleType: workoutType,
            predicate: HKQuery.predicateForWorkouts(with: .running)
        ) { _, completion, error in

            if let error = error {
                print("❌ Observer error:", error)
                completion()
                return
            }

            print("🏃‍♂️ New running workout detected")
            self.handleNewWorkout(completion: completion)
        }

        healthStore.execute(query)

        healthStore.enableBackgroundDelivery(
            for: workoutType,
            frequency: .immediate
        ) { success, error in
            if success {
                print("📡 Background delivery enabled")
            } else {
                print("❌ Background delivery failed:", error?.localizedDescription ?? "unknown")
            }
        }
    }
    
    private func handleNewWorkout(completion: @escaping () -> Void) {

        print("⏱ Fetch recent workouts (last 3h)")

        let end = Date()
        let start = Calendar.current.date(byAdding: .day, value: -1, to: end)!

        reader.fetchRunningWorkouts(from: start, to: end) { workouts in

            print("📦 Workouts fetched:", workouts.count)

            guard let latest = workouts.last else {
                print("⚠️ Workout not yet visible — retry in 10s")
                DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
                    self.handleNewWorkout(completion: completion)
                }
                return
            }


            print("🎯 Latest workout start:", latest.startDate)
            print("⏳ Duration:", latest.duration)

            // 👇 très important
            if latest.duration < 60 {
                print("⚠️ Workout too short or not finalized yet — retrying in 10s")
                DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
                    self.handleNewWorkout(completion: completion)
                }
                return
            }
            if let last = self.lastSyncedWorkoutStart,
               abs(last.timeIntervalSince(latest.startDate)) < 1 {
                print("⏭ Workout already synced")
                completion()
                return
            }

            self.processWorkout(latest, completion: completion)
        }
    }
    private func processWorkout(
        _ workout: HKWorkout,
        completion: @escaping () -> Void
    ) {
        print("🔄 Processing workout")

        // 1️⃣ Heart Rate
        reader.fetchHeartRateSamples(for: workout) { hrSamples in

            print("📊 HR samples:", hrSamples.count)

            // ⚠️ Données pas encore prêtes → retry
            guard !hrSamples.isEmpty else {
                print("⚠️ No HR yet — retry in 10s")
                DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
                    self.handleNewWorkout(completion: completion)
                }
                return
            }

            // 2️⃣ Calculs
            let hrValues = hrSamples.map {
                $0.quantity.doubleValue(for: HKUnit(from: "count/min"))
            }

            let avgHR = HealthMetricsCalculator.averageHR(hrValues)

            let samples = HealthMetricsCalculator.buildSamples(from: hrSamples)
            let zones = HealthMetricsCalculator.computeZones(samples: samples)

            let distanceKm =
                (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000

            let durationMin = workout.duration / 60

            // 3️⃣ Elevation + calories
            self.reader.resolveElevationGain(for: workout) { elevation in
                self.reader.fetchActiveEnergy(for: workout) { kcal in

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

                    print("🚀 Uploading session to backend")

                    self.syncService.upload(session)
                    self.lastSyncedWorkoutStart = workout.startDate
                    completion()
                }
            }
        }
    }

    

}
