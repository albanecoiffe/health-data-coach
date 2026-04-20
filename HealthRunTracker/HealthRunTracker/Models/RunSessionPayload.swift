import Foundation

struct RunSessionPayload: Codable {
    let user_id: String
    let start_time: String

    let distance_km: Double
    let duration_min: Double
    let avg_hr: Double?

    let z1_min: Double
    let z2_min: Double
    let z3_min: Double
    let z4_min: Double
    let z5_min: Double

    let elevation_m: Double?
    let active_kcal: Double?
}
