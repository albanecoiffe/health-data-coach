import Foundation
import HealthKit
// A garder pour le moment car
// j'affiche encore : liste de séances, graph hebdomadaire, vue “Semaine”, stats locales simples

struct DailyRunData: Identifiable, Hashable {
    let hkWorkout: HKWorkout
    let id: UUID
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
    
    let heartRateTimeline: [HeartRateSample]
    let sessionType: String?
    let predictedSessionType: String?
    let sessionDetail: String?

    var effectiveSessionType: String? {
        if let sessionType, !sessionType.isEmpty {
            return sessionType
        }
        if let predictedSessionType, !predictedSessionType.isEmpty {
            return predictedSessionType
        }
        return nil
    }

    static func == (lhs: DailyRunData, rhs: DailyRunData) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}
