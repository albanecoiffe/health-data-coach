import Foundation
import HealthKit
import MapKit
import Combine
import SwiftUI

final class YearPolyline: MKPolyline {
    var year: Int = 0
}

// MARK: - Types publics
struct HeartRateZoneData: Identifiable {
    let id = UUID()
    let label: String      // Z1, Z2, Z3...
    let percentage: Double // 0.25 = 25%
    let color: Color       // pour le graphique
}

struct WeeklyDistanceData: Identifiable, Equatable {
    var id: Int { weekNumber }
    let weekNumber: Int
    let distanceKm: Double
}

struct HRZones {
    static let z1 = 138.0
    static let z2 = 151.0
    static let z3 = 164.0
    static let z4 = 178.0
}

struct SessionZoneBreakdown: Identifiable {
    let id = UUID()
    let dayLabel: String
    let z1: Double
    let z2: Double
    let z3: Double
    let z4: Double
    let z5: Double
}


final class HealthManager: ObservableObject {
    private let healthStore = HKHealthStore()

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

    // MARK: - Types internes

    struct DailyRunData: Identifiable {
        let id = UUID()
        let date: Date
        let distanceKm: Double
        let durationMin: Double
        let elevationGainM: Double
        let dayLabel: String
        let averageHeartRate: Double

        let z1: Double
        let z2: Double
        let z3: Double
        let z4: Double
        let z5: Double
    }


    struct MonthlyRunData: Identifiable {
        let id = UUID()
        let month: Int
        let distanceKm: Double
        let durationMin: Double
        let elevationGainM: Double
        let monthLabel: String
    }

    // MARK: - Autorisation HealthKit

    func requestAuthorization() {
        guard HKHealthStore.isHealthDataAvailable() else {
            print("⚠️ HealthKit non disponible (simulateur ?)")
            return
        }

        let readTypes: Set<HKObjectType> = [
            HKObjectType.workoutType(),
            HKQuantityType.quantityType(forIdentifier: .distanceWalkingRunning)!,
            HKQuantityType.quantityType(forIdentifier: .heartRate)!,
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

    // MARK: - Données SEMAINE

    func fetchWeeklyRunningData(for offset: Int) {
        let calendar = Calendar.current

        guard let ref = calendar.date(byAdding: .weekOfYear, value: offset, to: Date()),
              let interval = calendar.dateInterval(of: .weekOfYear, for: ref) else { return }

        let datePredicate = HKQuery.predicateForSamples(withStart: interval.start, end: interval.end)
        let runningPredicate = HKQuery.predicateForWorkouts(with: .running)
        let predicate = NSCompoundPredicate(andPredicateWithSubpredicates: [runningPredicate, datePredicate])

        let query = HKSampleQuery(
            sampleType: .workoutType(),
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: nil
        ) { [weak self] _, samples, error in

            guard let self = self,
                  let workouts = samples as? [HKWorkout],
                  error == nil else {
                DispatchQueue.main.async { self?.weeklyData = [] }
                return
            }

            // Reset
            self.weeklyZoneBreakdown = []

            let group = DispatchGroup()
            var results: [SessionZoneBreakdown] = []

            // 1️⃣ Calcul des zones pour chaque workout
            for workout in workouts {
                group.enter()
                self.computeZonesForWorkout(workout) { breakdown in
                    if let b = breakdown { results.append(b) }
                    group.leave()
                }
            }

            // 2️⃣ Une fois TOUTES les zones calculées → construire weeklyData
            group.notify(queue: .main) {

                self.weeklyZoneBreakdown = results.sorted { $0.dayLabel < $1.dayLabel }

                let formatter = DateFormatter()
                formatter.locale = Locale(identifier: "fr_FR")
                formatter.dateFormat = "E"

                let data: [DailyRunData] = workouts.map { workout in

                    let avgHR = workout.statistics(for: HKQuantityType.quantityType(forIdentifier: .heartRate)!)?
                        .averageQuantity()?
                        .doubleValue(for: HKUnit(from: "count/min")) ?? 0

                    let label = formatter.string(from: workout.startDate)

                    // Associer au bon breakdown
                    let zones = results.first { $0.dayLabel == label }

                    return DailyRunData(
                        date: workout.startDate,
                        distanceKm: (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000,
                        durationMin: workout.duration / 60,
                        elevationGainM: (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                            .doubleValue(for: .meter()) ?? 0,
                        dayLabel: label,
                        averageHeartRate: avgHR,
                        z1: zones?.z1 ?? 0,
                        z2: zones?.z2 ?? 0,
                        z3: zones?.z3 ?? 0,
                        z4: zones?.z4 ?? 0,
                        z5: zones?.z5 ?? 0
                    )
                }

                self.weeklyData = data
            }
        }

        healthStore.execute(query)
    }

    // MARK: - Données ANNÉE

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

    // MARK: - Calcul hebdomadaire (graphique annuel)

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

                let hr = s1.quantity.doubleValue(for: HKUnit(from: "count/min"))
                let dt = s2.startDate.timeIntervalSince(s1.startDate) / 60.0  // minutes

                switch hr {
                case ..<HRZones.z1: z1 += dt
                case HRZones.z1..<HRZones.z2: z2 += dt
                case HRZones.z2..<HRZones.z3: z3 += dt
                case HRZones.z3..<HRZones.z4: z4 += dt
                default: z5 += dt
                }
            }

            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "fr_FR")
            formatter.dateFormat = "E"

            let label = formatter.string(from: workout.startDate)

            completion(
                SessionZoneBreakdown(
                    dayLabel: label,
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

// MARK: - Charge 7 jours / 28 jours


// MARK: - Routes GPS (HKWorkoutRoute)

extension HealthManager {

    func updateTrainingLoad() {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())

        let last7 = calendar.date(byAdding: .day, value: -6, to: today)!
        let last28 = calendar.date(byAdding: .day, value: -27, to: today)!

        var load7: Double = 0
        var load28: Double = 0

        for (date, km) in dailyDistances {
            if date >= last7 { load7 += km }
            if date >= last28 { load28 += km }
        }

        sevenDayLoad = load7
        twentyEightDayLoad = load28
        loadRatio = load28 > 0 ? load7 / load28 : 0
    }

    func fetchRunningRoutes(for yearOffset: Int,
                            completion: @escaping ([MKPolyline]) -> Void) {

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
        ) { [weak self] _, samples, error in

            guard let self = self,
                  let workouts = samples as? [HKWorkout],
                  error == nil else {
                completion([])
                return
            }

            var routes: [MKPolyline] = []
            var remaining = workouts.count

            for workout in workouts {
                self.fetchRoute(for: workout) { locs in
                    if !locs.isEmpty {
                        let coords = locs.map { $0.coordinate }
                        let poly = YearPolyline(coordinates: coords, count: coords.count)
                        poly.year = calendar.component(.year, from: workout.startDate)
                        routes.append(poly)
                    }

                    remaining -= 1
                    if remaining == 0 {
                        completion(routes)
                    }
                }
            }
        }

        healthStore.execute(query)
    }

    private func fetchRoute(for workout: HKWorkout,
                            completion: @escaping ([CLLocation]) -> Void) {

        let predicate = HKQuery.predicateForObjects(from: workout)
        let type = HKSeriesType.workoutRoute()

        let query = HKSampleQuery(
            sampleType: type,
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: nil
        ) { [weak self] _, samples, error in

            guard let routes = samples as? [HKWorkoutRoute],
                  let first = routes.first,
                  error == nil else {
                completion([])
                return
            }

            self?.readLocations(from: first, completion: completion)
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
                    date: workout.startDate,
                    distanceKm: (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000,
                    durationMin: workout.duration / 60,
                    elevationGainM: (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                        .doubleValue(for: .meter()) ?? 0,
                    dayLabel: formatter.string(from: workout.startDate),
                    averageHeartRate: avgHR,

                    // Ajout des zones manquantes
                    z1: 0,
                    z2: 0,
                    z3: 0,
                    z4: 0,
                    z5: 0
                )

            }

            completion(data)
        }

        healthStore.execute(query)
    }

    private func readLocations(from route: HKWorkoutRoute,
                               completion: @escaping ([CLLocation]) -> Void) {

        var all: [CLLocation] = []

        let query = HKWorkoutRouteQuery(route: route) { _, locs, done, _ in
            if let locs = locs { all.append(contentsOf: locs) }
            if done { completion(all) }
        }

        healthStore.execute(query)
    }
}

// MARK: - Toutes les années + couleurs

extension HealthManager {

    /// Charge les tracés GPS pour toutes les années trouvées dans HealthKit
    /// Retourne un tableau : (année, polyline, couleur associée)
    func fetchAllYearsRoutes(completion: @escaping ([(year: Int, polyline: MKPolyline, color: Color)]) -> Void) {

        // 1️⃣ Charger toutes les séances Running
        let predicate = HKQuery.predicateForWorkouts(with: .running)
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

            // 2️⃣ Organiser par année
            let calendar = Calendar.current
            var byYear: [Int: [HKWorkout]] = [:]

            for w in workouts {
                let year = calendar.component(.year, from: w.startDate)
                byYear[year, default: []].append(w)
            }

            // 3️⃣ Couleurs fixes par année
            let palette: [Color] = [
                .red,
                .blue,
                .green,
                .orange,
                .purple,
                .pink,
                .teal
            ]
            
            var results: [(Int, MKPolyline, Color)] = []
            let years = byYear.keys.sorted()
            let group = DispatchGroup()

            for (index, year) in years.enumerated() {
                let workoutsOfYear = byYear[year] ?? []
                let yearColor = palette[index % palette.count]

                for workout in workoutsOfYear {
                    group.enter()
                    self.fetchRoute(for: workout) { locs in
                        if !locs.isEmpty {
                            let coords = locs.map { $0.coordinate }
                            let polyline = YearPolyline(coordinates: coords, count: coords.count)
                            polyline.year = year
                            results.append((year, polyline, yearColor))
                        }
                        group.leave()
                    }
                }
            }

            group.notify(queue: .main) {
                completion(results)
            }
        }

        healthStore.execute(query)
    }
}
struct RunRecord {
    let distanceTarget: Double     // en km (10, 21.1, 42.195)
    let bestTime: TimeInterval     // en secondes
    let yearAchieved: Int
}

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
}

extension HealthManager {

    /// Retourne les distances cumulées par semaine pour une année donnée (offset).
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

extension HealthManager {
    func computeWeeklyHRZones(workouts: [HKWorkout]) {
        var z1 = 0.0
        var z2 = 0.0
        var z3 = 0.0
        var z4 = 0.0
        var z5 = 0.0
        var total = 0.0

        for workout in workouts {
            let avgHR = workout.statistics(for: HKQuantityType.quantityType(forIdentifier: .heartRate)!)?
                .averageQuantity()?
                .doubleValue(for: HKUnit(from: "count/min")) ?? 0

            let duration = workout.duration / 60
            total += duration

            switch avgHR {
            case ..<HRZones.z1: z1 += duration
            case HRZones.z1..<HRZones.z2: z2 += duration
            case HRZones.z2..<HRZones.z3: z3 += duration
            case HRZones.z3..<HRZones.z4: z4 += duration
            default: z5 += duration
            }
        }

        DispatchQueue.main.async {
            guard total > 0 else { return }
            self.weeklyHRZones = [
                "Z1": z1 / total,
                "Z2": z2 / total,
                "Z3": z3 / total,
                "Z4": z4 / total,
                "Z5": z5 / total
            ]
            self.weeklyZoneArray = [
                HeartRateZoneData(label: "Z1", percentage: z1 / total, color: .green),
                HeartRateZoneData(label: "Z2", percentage: z2 / total, color: .blue),
                HeartRateZoneData(label: "Z3", percentage: z3 / total, color: .orange),
                HeartRateZoneData(label: "Z4", percentage: z4 / total, color: .red),
                HeartRateZoneData(label: "Z5", percentage: z5 / total, color: .purple)
            ]
        }
    }
}

//
//stats pour le coach
//
extension HealthManager {
    func computeStatsForChat() -> (distance: Double, sessions: Int, avgHR: Double,
                                   z1: Double, z2: Double, z3: Double, z4: Double, z5: Double) {

        let dist = weeklyData.map(\.distanceKm).reduce(0, +)
        let sess = weeklyData.count
        let avg = weeklyData.map(\.averageHeartRate).reduce(0, +) / Double(max(sess, 1))

        let z1 = weeklyData.map(\.z1).reduce(0, +)
        let z2 = weeklyData.map(\.z2).reduce(0, +)
        let z3 = weeklyData.map(\.z3).reduce(0, +)
        let z4 = weeklyData.map(\.z4).reduce(0, +)
        let z5 = weeklyData.map(\.z5).reduce(0, +)

        return (dist, sess, avg, z1, z2, z3, z4, z5)
    }
}


//
// CREATION DU SNAPSHOT
//
extension HealthManager {

    func makeWeeklySnapshot() -> WeeklySnapshot {

        let calendar = Calendar.current
        let now = Date()

        guard let interval = calendar.dateInterval(of: .weekOfYear, for: now) else {
            fatalError("Impossible de calculer l’intervalle de semaine")
        }

        let dateFormatter = DateFormatter()
        dateFormatter.calendar = Calendar(identifier: .gregorian)
        dateFormatter.locale = Locale(identifier: "en_US_POSIX")
        dateFormatter.dateFormat = "yyyy-MM-dd"

        let period = PeriodSnapshot(
            start: dateFormatter.string(from: interval.start),
            end: dateFormatter.string(from: interval.end)
        )

        let totals = WeeklyTotals(
            distanceKm: weeklyData.map(\.distanceKm).reduce(0, +),
            durationMin: weeklyData.map(\.durationMin).reduce(0, +),
            sessions: weeklyData.count,
            elevationM: weeklyData.map(\.elevationGainM).reduce(0, +),
            avgHr: weeklyData.isEmpty
                ? nil
                : weeklyData.map(\.averageHeartRate).reduce(0, +) / Double(weeklyData.count)
        )

        let dailyRuns = weeklyData.map {
            DailyRunSnapshot(
                date: ISO8601DateFormatter().string(from: $0.date),
                distanceKm: $0.distanceKm,
                durationMin: $0.durationMin,
                elevationM: $0.elevationGainM,
                avgHr: $0.averageHeartRate,
                z1: $0.z1,
                z2: $0.z2,
                z3: $0.z3,
                z4: $0.z4,
                z5: $0.z5
            )
        }

        return WeeklySnapshot(
            weekLabel: "Semaine courante",
            period: period,                 // ✅ AJOUT CRITIQUE
            totals: totals,
            zonesPercent: weeklyHRZones,
            dailyRuns: dailyRuns,
            trainingLoad: TrainingLoad(
                load7d: sevenDayLoad,
                load28d: twentyEightDayLoad,
                ratio: loadRatio
            ),
            comparisonPrevWeek: nil
        )
    }

}


// Créer une fonction générique fetchRuns(from:to:)
extension HealthManager {

    func fetchRuns(
        from startDate: Date,
        to endDate: Date,
        completion: @escaping ([DailyRunData]) -> Void
    ) {

        let calendar = Calendar.current
        let endInclusive = calendar.date(
            bySettingHour: 23,
            minute: 59,
            second: 59,
            of: endDate
        )!

        let datePredicate = HKQuery.predicateForSamples(
            withStart: startDate,
            end: endInclusive,
            options: [] // ❗️ IMPORTANT : PAS strictStartDate
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
        ) { _, samples, error in

            guard let workouts = samples as? [HKWorkout], error == nil else {
                print("❌ fetchRuns error:", error?.localizedDescription ?? "unknown")
                completion([])
                return
            }

            print("🏃‍♂️ fetchRuns → \(workouts.count) workouts")
            for w in workouts {
                let km = (w.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000
                print("   •", w.startDate, String(format: "%.2f km", km))
            }

            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "fr_FR")
            formatter.dateFormat = "yyyy-MM-dd"

            let runs = workouts.map { workout -> DailyRunData in
                let avgHR = workout.statistics(
                    for: HKQuantityType.quantityType(forIdentifier: .heartRate)!
                )?
                .averageQuantity()?
                .doubleValue(for: HKUnit(from: "count/min")) ?? 0

                return DailyRunData(
                    date: workout.startDate,
                    distanceKm: (workout.totalDistance?.doubleValue(for: .meter()) ?? 0) / 1000,
                    durationMin: workout.duration / 60,
                    elevationGainM: (workout.metadata?["HKElevationAscended"] as? HKQuantity)?
                        .doubleValue(for: .meter()) ?? 0,
                    dayLabel: formatter.string(from: workout.startDate),
                    averageHeartRate: avgHR,
                    z1: 0, z2: 0, z3: 0, z4: 0, z5: 0
                )
            }

            completion(runs)
        }

        healthStore.execute(query)
    }
}

extension HealthManager {

    func makeSnapshot(
        from startDate: Date,
        to endDate: Date,
        completion: @escaping (WeeklySnapshot) -> Void
    ) {

        fetchRuns(from: startDate, to: endDate) { runs in

            print("📦 SNAPSHOT BUILD")
            print("   Runs count:", runs.count)
            print("   Total km:", runs.map(\.distanceKm).reduce(0, +))

            let totals = WeeklyTotals(
                distanceKm: runs.map(\.distanceKm).reduce(0, +),
                durationMin: runs.map(\.durationMin).reduce(0, +),
                sessions: runs.count,
                elevationM: runs.map(\.elevationGainM).reduce(0, +),
                avgHr: runs.isEmpty
                    ? nil
                    : runs.map(\.averageHeartRate).reduce(0, +) / Double(runs.count)
            )

            let dailyRuns = runs.map {
                DailyRunSnapshot(
                    date: ISO8601DateFormatter().string(from: $0.date),
                    distanceKm: $0.distanceKm,
                    durationMin: $0.durationMin,
                    elevationM: $0.elevationGainM,
                    avgHr: $0.averageHeartRate,
                    z1: $0.z1,
                    z2: $0.z2,
                    z3: $0.z3,
                    z4: $0.z4,
                    z5: $0.z5
                )
            }

            let formatter = DateFormatter()
            formatter.calendar = Calendar(identifier: .gregorian)
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.dateFormat = "yyyy-MM-dd"

            let period = PeriodSnapshot(
                start: formatter.string(from: startDate),
                end: formatter.string(from: endDate)
            )

            let snapshot = WeeklySnapshot(
                weekLabel: "Custom period",
                period: period,
                totals: totals,
                zonesPercent: [:],
                dailyRuns: dailyRuns,
                trainingLoad: nil,
                comparisonPrevWeek: nil
            )

            completion(snapshot)
        }
    }
}
