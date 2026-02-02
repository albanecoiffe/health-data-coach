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
    @Published var weeklyHRZones: [String: Double] = [
        "Z1": 0,
        "Z2": 0,
        "Z3": 0,
        "Z4": 0,
        "Z5": 0
    ]
    @Published var weeklyZoneArray: [HeartRateZoneData] = []

    
    func requestAuthorization() {
        guard HKHealthStore.isHealthDataAvailable() else {
            print("⚠️ HealthKit non disponible (simulateur ?)")
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
            if success {
                self.fetchWeeklyRunningData(for: 0)
                self.fetchYearlyRunningData(for: 0)
            } else {
                print("❌ Refus HealthKit :", error?.localizedDescription ?? "Erreur inconnue")
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

}
