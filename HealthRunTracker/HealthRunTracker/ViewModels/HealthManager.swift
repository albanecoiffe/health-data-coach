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

    // Seuils alignés Apple Health (observés)
    static let z1Upper = 139.0   // <139
    static let z2Upper = 152.0   // 140–152
    static let z3Upper = 165.0   // 153–165
    static let z4Upper = 178.0   // 166–178
    // Z5 >= 179
}


struct SessionZoneBreakdown: Identifiable {
    let id = UUID()
    let workoutStart: Date
    let z1: Double
    let z2: Double
    let z3: Double
    let z4: Double
    let z5: Double
}


final class HealthManager: ObservableObject {
    private let healthStore = HKHealthStore()

    @Published var weeklyData: [DailyRunData] = []
    @Published var runnerSignature: RunnerSignature? = nil
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
        let hkWorkout: HKWorkout
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

                self.weeklyZoneBreakdown = results.sorted {
                    $0.workoutStart < $1.workoutStart
                }


                let formatter = DateFormatter()
                formatter.locale = Locale(identifier: "fr_FR")
                formatter.dateFormat = "E"

                let data: [DailyRunData] = workouts.map { workout in

                    let avgHR = workout.statistics(for: HKQuantityType.quantityType(forIdentifier: .heartRate)!)?
                        .averageQuantity()?
                        .doubleValue(for: HKUnit(from: "count/min")) ?? 0

                    let label = formatter.string(from: workout.startDate)

                    // Associer au bon breakdown
                    let zones = results.first {
                        abs($0.workoutStart.timeIntervalSince(workout.startDate)) < 1
                    }

                    return DailyRunData(
                        hkWorkout: workout,
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
                    hkWorkout: workout,
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
        let longestRunKm = weeklyData
            .map(\.distanceKm)
            .max()

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
            comparisonPrevWeek: nil,
            longestRunKm: longestRunDistance
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
                            z5: zones?.z5 ?? 0
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

            // 🔴 Sécurité : aucune séance
            guard !runs.isEmpty else {

                let formatter = DateFormatter()
                formatter.calendar = Calendar(identifier: .gregorian)
                formatter.locale = Locale(identifier: "en_US_POSIX")
                formatter.dateFormat = "yyyy-MM-dd"

                let emptySnapshot = WeeklySnapshot(
                    weekLabel: "Custom period",
                    period: PeriodSnapshot(
                        start: formatter.string(from: startDate),
                        end: formatter.string(from: endDate)
                    ),
                    totals: WeeklyTotals(
                        distanceKm: 0,
                        durationMin: 0,
                        sessions: 0,
                        elevationM: 0,
                        avgHr: nil
                    ),
                    zonesPercent: [:],
                    dailyRuns: [],
                    trainingLoad: nil,
                    comparisonPrevWeek: nil,
                    longestRunKm: nil
                )

                completion(emptySnapshot)
                return
            }

            // ======================================================
            // 1️⃣ Calcul des zones par séance
            // ======================================================
            let group = DispatchGroup()
            var enrichedRuns: [DailyRunData] = []

            for run in runs {
                group.enter()

                self.computeZonesForWorkout(run.hkWorkout) { breakdown in

                    let enriched = DailyRunData(
                        hkWorkout: run.hkWorkout,
                        date: run.date,
                        distanceKm: run.distanceKm,
                        durationMin: run.durationMin,
                        elevationGainM: run.elevationGainM,
                        dayLabel: run.dayLabel,
                        averageHeartRate: run.averageHeartRate,
                        z1: breakdown?.z1 ?? 0,
                        z2: breakdown?.z2 ?? 0,
                        z3: breakdown?.z3 ?? 0,
                        z4: breakdown?.z4 ?? 0,
                        z5: breakdown?.z5 ?? 0
                    )

                    enrichedRuns.append(enriched)
                    group.leave()
                }
            }

            // ======================================================
            // 2️⃣ Construction du snapshot final
            // ======================================================
            group.notify(queue: .main) {

                let totals = WeeklyTotals(
                    distanceKm: enrichedRuns.map(\.distanceKm).reduce(0, +),
                    durationMin: enrichedRuns.map(\.durationMin).reduce(0, +),
                    sessions: enrichedRuns.count,
                    elevationM: enrichedRuns.map(\.elevationGainM).reduce(0, +),
                    avgHr: enrichedRuns.map(\.averageHeartRate).reduce(0, +)
                        / Double(enrichedRuns.count)
                )

                let dailyRuns = enrichedRuns.map {
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

                // ✅ CALCUL CORRECT DES ZONES ICI
                let zonesPercent = self.computeZonesPercent(from: enrichedRuns)

                let longestRun = enrichedRuns.max(by: { $0.distanceKm < $1.distanceKm })

                let trainingLoad = self.computeTrainingLoad(from: enrichedRuns)

                let snapshot = WeeklySnapshot(
                    weekLabel: "Custom period",
                    period: period,
                    totals: totals,
                    zonesPercent: zonesPercent,
                    dailyRuns: dailyRuns,
                    trainingLoad: trainingLoad,
                    comparisonPrevWeek: nil,
                    longestRunKm: longestRun?.distanceKm
                )

                completion(snapshot)
            }
        }
    }

    func makeYearSnapshot(
        year: Int,
        completion: @escaping (WeeklySnapshot) -> Void
    ) {
        let calendar = Calendar.current
        let start = calendar.date(from: DateComponents(year: year, month: 1, day: 1))!
        let end = calendar.date(from: DateComponents(year: year + 1, month: 1, day: 1))!

        makeSnapshot(from: start, to: end, completion: completion)
    }
    
    func computeZonesPercent(from runs: [DailyRunData]) -> [String: Double] {
        let z1 = runs.map(\.z1).reduce(0, +)
        let z2 = runs.map(\.z2).reduce(0, +)
        let z3 = runs.map(\.z3).reduce(0, +)
        let z4 = runs.map(\.z4).reduce(0, +)
        let z5 = runs.map(\.z5).reduce(0, +)
        
        let total = z1 + z2 + z3 + z4 + z5
        guard total > 0 else { return [:] }
        
        return [
            "z1": z1 / total,
            "z2": z2 / total,
            "z3": z3 / total,
            "z4": z4 / total,
            "z5": z5 / total
        ]
    }
}

// MARK: - SNAPSHOT ANNUEL (CHAT)

extension HealthManager {
    func makeYearSnapshot(year: Int) -> WeeklySnapshot {
        let calendar = Calendar.current

        let startDate = calendar.date(from: DateComponents(year: year, month: 1, day: 1))!
        let endDate = calendar.date(from: DateComponents(year: year + 1, month: 1, day: 1))!

        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"

        // 🔹 Données déjà calculées dans yearlyData
        let months = yearlyData.filter { _ in true } // déjà pour l’année courante chargée
        // ⚠️ si tu veux gérer plusieurs années → on adaptera après

        let totalDistance = months.map(\.distanceKm).reduce(0, +)
        let totalDuration = months.map(\.durationMin).reduce(0, +)
        let totalElevation = months.map(\.elevationGainM).reduce(0, +)

        let totals = WeeklyTotals(
            distanceKm: totalDistance,
            durationMin: totalDuration,
            sessions: yearlySessionCount,
            elevationM: totalElevation,
            avgHr: nil           // ❌ PAS DE FC ANNUELLE
        )

        let snapshot = WeeklySnapshot(
            weekLabel: "Année \(year)",
            period: PeriodSnapshot(
                start: formatter.string(from: startDate),
                end: formatter.string(from: endDate)
            ),
            totals: totals,
            zonesPercent: [:],    // ❌ PAS DE ZONES
            dailyRuns: [],        // ❌ PAS DE DAILY RUNS
            trainingLoad: nil,
            comparisonPrevWeek: nil,
            longestRunKm: longestRunDistance
        )

        return snapshot
    }
}

// MARK: - SNAPSHOTS LONG TERME (SIGNATURE)

extension HealthManager {

    /// Construit les snapshots hebdomadaires sur les N dernières semaines
    func makeWeeklySnapshots(
        weeks: Int = 52,
        completion: @escaping ([WeeklySnapshot]) -> Void
    ) {

        let calendar = Calendar.current
        let now = Date()

        let group = DispatchGroup()
        var snapshots: [WeeklySnapshot] = []

        print("🧠 BUILDING \(weeks) WEEKLY SNAPSHOTS")

        for offset in stride(from: -(weeks - 1), through: 0, by: 1) {

            guard
                let ref = calendar.date(byAdding: .weekOfYear, value: offset, to: now),
                let interval = calendar.dateInterval(of: .weekOfYear, for: ref)
            else { continue }

            group.enter()

            self.makeSnapshot(from: interval.start, to: interval.end) { snapshot in
                print("📦 Week", snapshot.period.start, "→", snapshot.totals.sessions, "sessions")
                snapshots.append(snapshot)
                group.leave()
            }
        }

        group.notify(queue: .main) {
            let sorted = snapshots.sorted {
                $0.period.start < $1.period.start
            }

            print("✅ WEEKLY SNAPSHOTS READY:", sorted.count)
            completion(sorted)
        }
    }

    
    func buildRunnerSignatureIfNeeded() {

        // ⚠️ Évite de recalculer inutilement
        guard runnerSignature == nil else {
            print("🧠 Runner signature already built")
            return
        }

        makeWeeklySnapshots(weeks: 52) { weeklySnapshots in

            print("🧪 BUILD SIGNATURE — weeks:", weeklySnapshots.count)

            guard let signature = RunnerSignatureBuilder.build(from: weeklySnapshots) else {
                print("❌ FAILED TO BUILD RUNNER SIGNATURE")
                return
            }

            DispatchQueue.main.async {
                self.runnerSignature = signature
                print("✅ RUNNER SIGNATURE STORED")
            }
        }
    }
    
    // MARK: - Training Load (snapshot-based)

    func computeTrainingLoad(from runs: [DailyRunData]) -> TrainingLoad {

        // 🔹 Charge simple = durée pondérée par intensité
        // z4+z5 = intensité forte
        let load = runs.reduce(0.0) { acc, run in
            let intensePct = (run.z4 + run.z5) / max(run.durationMin, 1)
            return acc + run.durationMin * (1 + 2 * intensePct)
        }

        return TrainingLoad(
            load7d: load,
            load28d: 0,   // ❗ PAS de sens à ce niveau
            ratio: 0
        )
    }


}

import HealthKit
import Foundation

import HealthKit
import Foundation

extension HealthManager {

    // ======================================================
    // 🏃‍♂️ RUN SESSION (RAW, PAR SÉANCE)
    // ======================================================
    struct RunSession {
        let startDate: Date
        let distanceKm: Double
        let durationMin: Double

        // Temps en minutes par zone
        let z1: Double
        let z2: Double
        let z3: Double
        let z4: Double
        let z5: Double
    }

    // ======================================================
    // 🫀 ZONE CARDIAQUE POUR UN BPM
    // ======================================================
    func heartRateZone(for bpm: Double, maxHR: Double) -> String {
        let pct = bpm / maxHR

        switch pct {
        case ..<0.7: return "z1"
        case ..<0.8: return "z2"
        case ..<0.9: return "z3"
        case ..<1.0: return "z4"
        default:     return "z5"
        }
    }

    // ======================================================
    // 🫀 CALCUL DES MINUTES PAR ZONE (CORE FIX)
    // ======================================================
    
    func fetchHeartRateZones(
        during workout: HKWorkout,
        maxHR: Double,
        completion: @escaping (Double, Double, Double, Double, Double) -> Void
    ) {

        guard let hrType = HKObjectType.quantityType(forIdentifier: .heartRate) else {
            completion(0, 0, 0, 0, 0)
            return
        }

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
        ) { _, samples, _ in

            guard let samples = samples as? [HKQuantitySample],
                  samples.count > 1 else {
                completion(0, 0, 0, 0, 0)
                return
            }

            var z1 = 0.0, z2 = 0.0, z3 = 0.0, z4 = 0.0, z5 = 0.0

            for i in 0..<(samples.count - 1) {
                let s1 = samples[i]
                let s2 = samples[i + 1]

                let hr1 = s1.quantity.doubleValue(for: .count().unitDivided(by: .minute()))
                let hr2 = s2.quantity.doubleValue(for: .count().unitDivided(by: .minute()))
                let hr = (hr1 + hr2) / 2.0   // 🔑 CLÉ ABSOLUE

                let dt = s2.startDate.timeIntervalSince(s1.startDate) / 60.0
                if dt <= 0 { continue }

                switch hr {
                case ..<HRZones.z1Upper: z1 += dt
                case HRZones.z1Upper..<HRZones.z2Upper: z2 += dt
                case HRZones.z2Upper..<HRZones.z3Upper: z3 += dt
                case HRZones.z3Upper..<HRZones.z4Upper: z4 += dt
                default: z5 += dt
                }
            }

            completion(z1, z2, z3, z4, z5)
        }

        healthStore.execute(query)
    }


    // ======================================================
    // 📥 FETCH DES SÉANCES BRUTES
    // ======================================================
    func fetchRunSessions(
        from start: Date,
        to end: Date,
        maxHR: Double = 190,
        completion: @escaping ([RunSession]) -> Void
    ) {
        print("🚨 fetchRunSessions called")
        let workoutPredicate = HKQuery.predicateForWorkouts(with: .running)
        let datePredicate = HKQuery.predicateForSamples(
            withStart: start,
            end: end,
            options: .strictStartDate
        )

        let predicate = NSCompoundPredicate(
            andPredicateWithSubpredicates: [workoutPredicate, datePredicate]
        )

        let query = HKSampleQuery(
            sampleType: HKObjectType.workoutType(),
            predicate: predicate,
            limit: HKObjectQueryNoLimit,
            sortDescriptors: [
                NSSortDescriptor(
                    key: HKSampleSortIdentifierStartDate,
                    ascending: true
                )
            ]
        ) { _, samples, _ in

            guard let workouts = samples as? [HKWorkout] else {
                completion([])
                return
            }

            let group = DispatchGroup()
            var sessions: [RunSession] = []

            for workout in workouts {
                group.enter()

                self.fetchHeartRateZones(
                    during: workout,
                    maxHR: maxHR
                ) { z1, z2, z3, z4, z5 in

                    let distanceKm =
                        (workout.totalDistance?
                            .doubleValue(for: .meter()) ?? 0) / 1000

                    let durationMin = workout.duration / 60

                    sessions.append(
                        RunSession(
                            startDate: workout.startDate,
                            distanceKm: distanceKm,
                            durationMin: durationMin,
                            z1: z1,
                            z2: z2,
                            z3: z3,
                            z4: z4,
                            z5: z5
                        )
                    )

                    group.leave()
                }
            }

            group.notify(queue: .main) {
                completion(
                    sessions.sorted { $0.startDate < $1.startDate }
                )
            }
        }

        healthStore.execute(query)
    }

    // ======================================================
    // 📄 EXPORT CSV (AVEC % CALCULÉS APRÈS)
    // ======================================================
    func exportSessionsToCSV(_ sessions: [RunSession]) {

        var csv =
        "date,distance_km,duration_min,pace_min_per_km," +
        "z1_min,z2_min,z3_min,z4_min,z5_min," +
        "low_intensity_pct,high_intensity_pct\n"

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"

        for s in sessions {

            let total = s.z1 + s.z2 + s.z3 + s.z4 + s.z5

            let lowPct = total > 0
                ? (s.z1 + s.z2 + s.z3) / total
                : 0

            let highPct = total > 0
                ? (s.z4 + s.z5) / total
                : 0

            let pace = s.distanceKm > 0
                ? s.durationMin / s.distanceKm
                : 0

            let line =
            "\(formatter.string(from: s.startDate))," +
            "\(s.distanceKm)," +
            "\(s.durationMin)," +
            "\(pace)," +
            "\(s.z1),\(s.z2),\(s.z3),\(s.z4),\(s.z5)," +
            "\(lowPct),\(highPct)\n"

            csv.append(line)
        }

        let fileURL = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("run_sessions_24_months.csv")

        do {
            try csv.write(to: fileURL, atomically: true, encoding: .utf8)
            print("✅ SESSIONS CSV EXPORTÉ :", fileURL)
        } catch {
            print("❌ CSV export error:", error)
        }
    }
    
    // ======================================================
    // 📤 UPLOAD SESSIONS CSV → BACKEND
    // ======================================================
    func uploadSessionsCSVToBackend() {
        
        print("🚀 uploadSessionsCSVToBackend CALLED")

        let fileURL = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("run_sessions_24_months.csv")

        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            print("❌ Sessions CSV introuvable")
            return
        }

        guard let url = URL(string: "\(baseURL)/upload-sessions-csv") else {
            print("❌ URL backend invalide")
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue(
            "multipart/form-data; boundary=\(boundary)",
            forHTTPHeaderField: "Content-Type"
        )

        var body = Data()

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"run_sessions_24_months.csv\"\r\n"
                .data(using: .utf8)!
        )
        body.append("Content-Type: text/csv\r\n\r\n".data(using: .utf8)!)
        body.append((try? Data(contentsOf: fileURL)) ?? Data())
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        URLSession.shared.dataTask(with: request) { _, response, error in
            if let error = error {
                print("❌ Upload sessions CSV error:", error)
                return
            }

            if let http = response as? HTTPURLResponse {
                print("✅ Sessions CSV upload status:", http.statusCode)
            }
        }.resume()
    }

    // ======================================================
    // 🧪 DEBUG GLOBAL
    // ======================================================
    func debugSessionDataset() {

        let calendar = Calendar.current
        let end = Date()
        let start = calendar.date(byAdding: .month, value: -24, to: end)!

        fetchRunSessions(from: start, to: end) { sessions in
            print("🟩 SESSIONS FOUND:", sessions.count)
            self.exportSessionsToCSV(sessions)
            self.uploadSessionsCSVToBackend()
        }
    }
}
