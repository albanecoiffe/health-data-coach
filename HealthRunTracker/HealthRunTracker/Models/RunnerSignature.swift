import Foundation

struct RunnerSignature: Codable {

    struct PeriodSignature: Codable {
        let start: String
        let end: String
        let weeks: Int
    }

    struct VolumeSignature: Codable {
        let weekly_avg_km: Double
        let weekly_std_km: Double
        let trend_12w_pct: Double
    }

    struct DurationSignature: Codable {
        let weeklyAvgMin: Double
        let weeklyStdMin: Double
    }

    struct FrequencySignature: Codable {
        let weeklyAvgSessions: Double
        let weeklyStdSessions: Double
    }

    struct IntensitySignature: Codable {
        let z4_z5_avg_pct: Double
        let z4_z5_trend_12w_pct: Double
        let z1_z3_avg_pct: Double
    }

    struct LoadSignature: Codable {
        let weeklyAvgLoad: Double
        let weeklyStdLoad: Double
        let acwrAvg: Double
        let acwrMax: Double
    }

    struct RegularitySignature: Codable {
        let weeksWithRunsPct: Double
        let longestBreakDays: Int
    }
    
    struct RobustnessSignature: Codable {
        let injuryFreeWeeksPct: Double
        let maxConsecutiveWeeks: Int
        let breaksOver7dCount: Int
    }
    
    struct AdaptationSignature: Codable {
        let loadStdTrend12wPct: Double
    }

    let period: PeriodSignature
    let volume: VolumeSignature
    let duration: DurationSignature
    let frequency: FrequencySignature
    let intensity: IntensitySignature
    let load: LoadSignature
    let regularity: RegularitySignature
    let robustness: RobustnessSignature    
    let adaptation: AdaptationSignature
}
