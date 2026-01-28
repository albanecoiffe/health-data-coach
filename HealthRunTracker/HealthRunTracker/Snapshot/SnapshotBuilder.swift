import Foundation

struct SnapshotBuilder {

    // MARK: - Weekly snapshots (N semaines)

    static func makeWeeklySnapshots(
        healthManager: HealthManager,
        weeks: Int,
        completion: @escaping ([WeeklySnapshot]) -> Void
    ) {
        let calendar = Calendar.current
        let now = Date()

        let group = DispatchGroup()
        var snapshots: [WeeklySnapshot] = []
        snapshots.reserveCapacity(weeks)

        for offset in stride(from: -(weeks - 1), through: 0, by: 1) {
            guard
                let ref = calendar.date(byAdding: .weekOfYear, value: offset, to: now),
                let interval = calendar.dateInterval(of: .weekOfYear, for: ref)
            else { continue }

            group.enter()
            makeSnapshot(
                healthManager: healthManager,
                from: interval.start,
                to: interval.end
            ) { snapshot in
                snapshots.append(snapshot)
                group.leave()
            }
        }

        group.notify(queue: .main) {
            completion(
                snapshots.sorted { $0.period.start < $1.period.start }
            )
        }
    }

    // MARK: - Snapshot custom period (async)

    static func makeSnapshot(
        healthManager: HealthManager,
        from startDate: Date,
        to endDate: Date,
        completion: @escaping (WeeklySnapshot) -> Void
    ) {
        healthManager.fetchRuns(from: startDate, to: endDate) { runs in

            guard !runs.isEmpty else {
                completion(emptySnapshot(startDate: startDate, endDate: endDate))
                return
            }

            let group = DispatchGroup()
            var enrichedRuns: [DailyRunData] = []
            enrichedRuns.reserveCapacity(runs.count)

            for run in runs {
                group.enter()
                healthManager.computeZonesForWorkout(run.hkWorkout) { breakdown in

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

            group.notify(queue: .main) {
                completion(
                    buildSnapshot(startDate: startDate, endDate: endDate, runs: enrichedRuns)
                )
            }
        }
    }

    // MARK: - Year snapshot (async)

    static func makeYearSnapshot(
        healthManager: HealthManager,
        year: Int,
        completion: @escaping (WeeklySnapshot) -> Void
    ) {
        let calendar = Calendar.current
        let start = calendar.date(from: DateComponents(year: year, month: 1, day: 1))!
        let end = calendar.date(from: DateComponents(year: year + 1, month: 1, day: 1))!
        makeSnapshot(healthManager: healthManager, from: start, to: end, completion: completion)
    }

    // MARK: - Snapshot from already loaded weeklyData (sync)

    static func makeWeeklySnapshotFromState(healthManager: HealthManager) -> WeeklySnapshot {
        let calendar = Calendar.current
        let now = Date()

        guard let interval = calendar.dateInterval(of: .weekOfYear, for: now) else {
            fatalError("Impossible de calculer l’intervalle de semaine")
        }

        let period = PeriodSnapshot(
            start: dateString(interval.start),
            end: dateString(interval.end)
        )

        let totals = WeeklyTotals(
            distanceKm: healthManager.weeklyData.map(\.distanceKm).reduce(0, +),
            durationMin: healthManager.weeklyData.map(\.durationMin).reduce(0, +),
            sessions: healthManager.weeklyData.count,
            elevationM: healthManager.weeklyData.map(\.elevationGainM).reduce(0, +),
            avgHr: healthManager.weeklyData.isEmpty
                ? nil
                : healthManager.weeklyData.map(\.averageHeartRate).reduce(0, +) / Double(healthManager.weeklyData.count)
        )

        let dailyRuns = healthManager.weeklyData.map {
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
            period: period,
            totals: totals,
            zonesPercent: healthManager.weeklyHRZones,
            dailyRuns: dailyRuns,
            trainingLoad: TrainingLoad(
                load7d: healthManager.sevenDayLoad,
                load28d: healthManager.twentyEightDayLoad,
                ratio: healthManager.loadRatio
            ),
            comparisonPrevWeek: nil,
            longestRunKm: healthManager.longestRunDistance
        )
    }

    // MARK: - Pure helpers

    static func computeZonesPercent(from runs: [DailyRunData]) -> [String: Double] {
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

    static func computeStatsForChat(from weeklyData: [DailyRunData])
    -> (distance: Double, sessions: Int, avgHR: Double, z1: Double, z2: Double, z3: Double, z4: Double, z5: Double) {

        let dist = weeklyData.map(\.distanceKm).reduce(0, +)
        let sess = weeklyData.count
        let avg = weeklyData.isEmpty ? 0 : weeklyData.map(\.averageHeartRate).reduce(0, +) / Double(weeklyData.count)

        return (
            dist,
            sess,
            avg,
            weeklyData.map(\.z1).reduce(0, +),
            weeklyData.map(\.z2).reduce(0, +),
            weeklyData.map(\.z3).reduce(0, +),
            weeklyData.map(\.z4).reduce(0, +),
            weeklyData.map(\.z5).reduce(0, +)
        )
    }

    // MARK: - Private snapshot building

    private static func buildSnapshot(
        startDate: Date,
        endDate: Date,
        runs: [DailyRunData]
    ) -> WeeklySnapshot {

        let totals = WeeklyTotals(
            distanceKm: runs.map(\.distanceKm).reduce(0, +),
            durationMin: runs.map(\.durationMin).reduce(0, +),
            sessions: runs.count,
            elevationM: runs.map(\.elevationGainM).reduce(0, +),
            avgHr: runs.map(\.averageHeartRate).reduce(0, +) / Double(max(runs.count, 1))
        )

        let dailyRuns = runs.map {
            DailyRunSnapshot(
                date: ISO8601DateFormatter().string(from: $0.date),
                distanceKm: $0.distanceKm,
                durationMin: $0.durationMin,
                elevationM: $0.elevationGainM,
                avgHr: $0.averageHeartRate,
                z1: $0.z1, z2: $0.z2, z3: $0.z3, z4: $0.z4, z5: $0.z5
            )
        }

        let period = PeriodSnapshot(
            start: dateString(startDate),
            end: dateString(endDate)
        )

        let zonesPercent = computeZonesPercent(from: runs)
        let longestRun = runs.max(by: { $0.distanceKm < $1.distanceKm })

        // si tu as un TrainingLoadCalculator séparé, remplace ici :
        let trainingLoad = TrainingLoadCalculator.computeTrainingLoad(from: runs)

        return WeeklySnapshot(
            weekLabel: "Custom period",
            period: period,
            totals: totals,
            zonesPercent: zonesPercent,
            dailyRuns: dailyRuns,
            trainingLoad: trainingLoad,
            comparisonPrevWeek: nil,
            longestRunKm: longestRun?.distanceKm
        )
    }

    private static func emptySnapshot(startDate: Date, endDate: Date) -> WeeklySnapshot {
        WeeklySnapshot(
            weekLabel: "Custom period",
            period: PeriodSnapshot(start: dateString(startDate), end: dateString(endDate)),
            totals: WeeklyTotals(distanceKm: 0, durationMin: 0, sessions: 0, elevationM: 0, avgHr: nil),
            zonesPercent: [:],
            dailyRuns: [],
            trainingLoad: nil,
            comparisonPrevWeek: nil,
            longestRunKm: nil
        )
    }

    private static func dateString(_ d: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: d)
    }
}
