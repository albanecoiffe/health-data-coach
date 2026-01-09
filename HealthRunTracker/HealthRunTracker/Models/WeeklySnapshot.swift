import Foundation

struct WeeklyTotals: Codable {
    let distanceKm: Double
    let durationMin: Double
    let sessions: Int
    let elevationM: Double
    let avgHr: Double?
}

struct TrainingLoad: Codable {
    let load7d: Double
    let load28d: Double
    let ratio: Double

    enum CodingKeys: String, CodingKey {
        case load7d = "load_7d"
        case load28d = "load_28d"
        case ratio
    }
}

struct DailyRunSnapshot: Codable {
    let date: String
    let distanceKm: Double
    let durationMin: Double
    let elevationM: Double
    let avgHr: Double

    let z1: Double
    let z2: Double
    let z3: Double
    let z4: Double
    let z5: Double
}

struct WeeklySnapshot: Codable {
    let weekLabel: String
    let period: PeriodSnapshot
    let totals: WeeklyTotals
    let zonesPercent: [String: Double]
    let dailyRuns: [DailyRunSnapshot]
    let trainingLoad: TrainingLoad?
    let comparisonPrevWeek: [String: Double]?
    let longestRunKm: Double?

}

extension WeeklySnapshot {

    func zonePct(_ zone: String) -> Double {
        zonesPercent[zone] ?? 0
    }

    var z1z3Pct: Double {
        zonePct("z1") + zonePct("z3")
    }

    var z4z5Pct: Double {
        zonePct("z4") + zonePct("z5")
    }

    var weekHasRuns: Bool {
        totals.sessions > 0
    }
}
