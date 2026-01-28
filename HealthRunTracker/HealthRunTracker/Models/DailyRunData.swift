import Foundation
import HealthKit

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

