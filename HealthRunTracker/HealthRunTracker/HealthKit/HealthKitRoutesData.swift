import HealthKit
import MapKit
import SwiftUI

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
