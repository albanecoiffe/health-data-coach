import Foundation

final class RunnerSignatureBuilder {

    static func build(from weeks: [WeeklySnapshot]) -> RunnerSignature? {

        guard weeks.count >= 8 else {
            print("⚠️ Not enough data for signature")
            return nil
        }

        let sorted = weeks.sorted {
            $0.period.start < $1.period.start
        }

        print("🧠 BUILDING RUNNER SIGNATURE")
        print("   weeks:", sorted.count)

        // -------------------------
        // PERIOD
        // -------------------------
        let period = RunnerSignature.PeriodSignature(
            start: sorted.first!.period.start,
            end: sorted.last!.period.end,
            weeks: sorted.count
        )

        // -------------------------
        // VOLUME
        // -------------------------
        let distances = sorted.map { $0.totals.distanceKm }

        let volume = RunnerSignature.VolumeSignature(
            weekly_avg_km: avg(distances),
            weekly_std_km: std(distances),
            trend_12w_pct: trend12WeeksPctExcludingIncomplete(
                values: distances,
                sessions: sorted.map { $0.totals.sessions }
            ),
        )

        // -------------------------
        // DURATION
        // -------------------------
        let durations = sorted.map { $0.totals.durationMin }

        let duration = RunnerSignature.DurationSignature(
            weeklyAvgMin: avg(durations),
            weeklyStdMin: std(durations)
        )

        // -------------------------
        // FREQUENCY
        // -------------------------
        let sessions = sorted.map { Double($0.totals.sessions) }

        let frequency = RunnerSignature.FrequencySignature(
            weeklyAvgSessions: avg(sessions),
            weeklyStdSessions: std(sessions)
        )

        // -------------------------
        // INTENSITY
        // -------------------------
        let z4z5 = sorted.map { $0.z4z5Pct }
        let z1z3 = sorted.map { $0.z1z3Pct }

        let intensity = RunnerSignature.IntensitySignature(
            z4_z5_avg_pct: avg(z4z5),
            z4_z5_trend_12w_pct: trend12WeeksPctExcludingIncomplete(
                values: z4z5,
                sessions: sorted.map { $0.totals.sessions }
            ),
            z1_z3_avg_pct: avg(z1z3)
        )

        // -------------------------
        // LOAD
        // -------------------------
        let loads = sorted.compactMap { $0.trainingLoad?.load7d }

        let acute = Array(loads.suffix(4))
        let chronic = Array(loads.suffix(12))

        let chronicAvg = avg(chronic)

        let acwrValues = acute.map { acuteLoad in
            chronicAvg > 0 ? acuteLoad / chronicAvg : 0
        }

        let load = RunnerSignature.LoadSignature(
            weeklyAvgLoad: avg(loads),
            weeklyStdLoad: std(loads),
            acwrAvg: avg(acwrValues),
            acwrMax: acwrValues.max() ?? 0
        )

        // -------------------------
        // REGULARITY
        // -------------------------
        let weeksWithRunsCount = sorted.filter { $0.weekHasRuns }.count
        let weeksWithRunsPct =
            Double(weeksWithRunsCount) / Double(sorted.count) * 100

        let longestBreak = longestBreakDays(sorted)

        let regularity = RunnerSignature.RegularitySignature(
            weeksWithRunsPct: weeksWithRunsPct,
            longestBreakDays: longestBreak
        )

        // -------------------------
        // ROBUSTNESS
        // -------------------------
        let activeWeeksCount = sorted.filter {
            $0.totals.sessions > 0
        }.count

        let injuryFreeWeeksPct =
            Double(activeWeeksCount) / Double(sorted.count) * 100

        var currentStreak = 0
        var maxStreak = 0
        var breaksOver7d = 0

        for w in sorted {
            if w.totals.sessions > 0 {
                currentStreak += 1
                maxStreak = max(maxStreak, currentStreak)
            } else {
                if currentStreak * 7 >= 7 {
                    breaksOver7d += 1
                }
                currentStreak = 0
            }
        }

        let robustness = RunnerSignature.RobustnessSignature(
            injuryFreeWeeksPct: injuryFreeWeeksPct,
            maxConsecutiveWeeks: maxStreak,
            breaksOver7dCount: breaksOver7d
        )

        // -------------------------
        // ADAPTATION (charge absorption)
        // -------------------------
        let loadStdSeries = sorted.map {
            $0.trainingLoad?.load7d ?? 0
        }

        let adaptation = RunnerSignature.AdaptationSignature(
            loadStdTrend12wPct: trend12WeeksPctExcludingIncomplete(
                values: loadStdSeries,
                sessions: sorted.map { $0.totals.sessions }
            )
        )

        // -------------------------
        // FINAL SIGNATURE
        // -------------------------
        return RunnerSignature(
            period: period,
            volume: volume,
            duration: duration,
            frequency: frequency,
            intensity: intensity,
            load: load,
            regularity: regularity,
            robustness: robustness,
            adaptation: adaptation
        )
    }

    // -------------------------
    // Longest break in days
    // -------------------------
    private static func longestBreakDays(_ weeks: [WeeklySnapshot]) -> Int {
        var current = 0
        var maxBreak = 0

        for w in weeks {
            if w.totals.sessions == 0 {
                current += 7
                maxBreak = max(maxBreak, current)
            } else {
                current = 0
            }
        }
        return maxBreak
    }
}
