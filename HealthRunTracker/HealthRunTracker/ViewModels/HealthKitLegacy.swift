
import HealthKit
import MapKit
import SwiftUI

// ======================================================
// MARK: - Weekly / Yearly UI Data (legacy)
// ======================================================
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
                DispatchQueue.main.async { self?.weeklyData = [] }
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
                        heartRateTimeline: timeline
                    )

                    sessions.append(run)
                    outerGroup.leave()
                }
            }

            outerGroup.notify(queue: .main) {
                self.weeklyData = sessions.sorted { $0.date < $1.date }
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
// ======================================================
// MARK: - Routes GPS (legacy)
// ======================================================

extension HealthManager {
    
    private func readLocations(from route: HKWorkoutRoute,
                               completion: @escaping ([CLLocation]) -> Void) {

        var all: [CLLocation] = []

        let query = HKWorkoutRouteQuery(route: route) { _, locs, done, _ in
            if let locs = locs { all.append(contentsOf: locs) }
            if done { completion(all) }
        }

        healthStore.execute(query)
    }

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

// ======================================================
// MARK: - Records & Aggregations (legacy)
// ======================================================

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

// ======================================================
// MARK: - Snapshot Builders (legacy)
// ======================================================

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
