import HealthKit
import SwiftUI

/// Observe HealthKit pour détecter automatiquement
/// les nouvelles séances de course (running)
/// et les envoyer au backend une seule fois.
final class HealthKitObserver {

    /// Garde en mémoire la dernière séance déjà synchronisée
    /// (valable uniquement pour la session courante de l’app)
    private var lastSyncedWorkoutStart: Date?

    /// Accès à HealthKit
    private let healthStore = HKHealthStore()

    /// Lecture des données HealthKit (workouts, HR, calories, etc.)
    private let reader: HealthKitReader

    /// Service réseau chargé d’envoyer les séances au backend
    private let syncService: RunSessionSyncService

    init(
        reader: HealthKitReader,
        syncService: RunSessionSyncService
    ) {
        self.reader = reader
        self.syncService = syncService
    }

    /// Démarre l’observation HealthKit
    /// → appelée une seule fois au lancement de l’app
    func start() {

        let workoutType = HKObjectType.workoutType()

        print("👀 HealthKitObserver started")

        // 1️⃣ Observer HealthKit :
        // déclenché quand un nouveau workout RUNNING est ajouté ou modifié
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

            // Dès qu’un événement est détecté,
            // on tente de récupérer la nouvelle séance
            self.handleNewWorkout(completion: completion)
        }

        healthStore.execute(query)

        // 2️⃣ Active la livraison en background
        // → l’app peut être réveillée même fermée
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

    /// Récupère les workouts récents et identifie
    /// la nouvelle séance à synchroniser
    private func handleNewWorkout(completion: @escaping () -> Void) {

        print("⏱ Fetch recent workouts (last 24h)")

        let end = Date()
        let start = Calendar.current.date(byAdding: .day, value: -30, to: end)!

        // On relit les séances récentes
        reader.fetchRunningWorkouts(from: start, to: end) { workouts in

            print("📦 Workouts fetched:", workouts.count)

            // Si HealthKit n’a encore rien retourné
            // (cas fréquent juste après la fin d’une séance)
            guard let latest = workouts.last else {
                print("⚠️ Workout not yet visible — retry in 10s")
                DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
                    self.handleNewWorkout(completion: completion)
                }
                return
            }

            print("🎯 Latest workout start:", latest.startDate)
            print("⏳ Duration:", latest.duration)

            // 1️⃣ Séance pas encore finalisée par Apple
            if latest.duration < 60 {
                print("⚠️ Workout too short or not finalized yet — retrying in 10s")
                DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
                    self.handleNewWorkout(completion: completion)
                }
                return
            }

            // 2️⃣ Séance déjà synchronisée pendant cette session d’app
            if let last = self.lastSyncedWorkoutStart,
               abs(last.timeIntervalSince(latest.startDate)) < 1 {
                print("⏭ Workout already synced")
                completion()
                return
            }

            // 3️⃣ Nouvelle séance valide → on la traite
            self.processWorkout(latest, completion: completion)
        }
    }

    /// Transforme un HKWorkout en RunSession
    /// puis l’envoie au backend
    private func processWorkout(
        _ workout: HKWorkout,
        completion: @escaping () -> Void
    ) {
        print("🔄 Processing workout")

        // 1️⃣ Récupération des données de fréquence cardiaque
        reader.fetchHeartRateSamples(for: workout) { hrSamples in

            print("📊 HR samples:", hrSamples.count)

            // HR pas encore prête → on réessaie plus tard
            guard !hrSamples.isEmpty else {
                print("⚠️ No HR yet — retry in 10s")
                DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
                    self.handleNewWorkout(completion: completion)
                }
                return
            }

            // 2️⃣ Calculs métriques
            let hrValues = hrSamples.map {
                $0.quantity.doubleValue(for: HKUnit(from: "count/min"))
            }

            let avgHR = HealthMetricsCalculator.averageHR(hrValues)

            let samples = HealthMetricsCalculator.buildSamples(from: hrSamples)
            let zones = HealthMetricsCalculator.computeZones(samples: samples)

            let distanceKm =
                (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000

            let durationMin = workout.duration / 60

            // 3️⃣ Élévation + calories (asynchrones)
            self.reader.resolveElevationGain(for: workout) { elevation in
                self.reader.fetchActiveEnergy(for: workout) { kcal in

                    // 4️⃣ Construction du modèle métier
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

                    // 5️⃣ Envoi au backend
                    self.syncService.upload(session)

                    // Marque cette séance comme synchronisée
                    self.lastSyncedWorkoutStart = workout.startDate

                    completion()
                }
            }
        }
    }
}
