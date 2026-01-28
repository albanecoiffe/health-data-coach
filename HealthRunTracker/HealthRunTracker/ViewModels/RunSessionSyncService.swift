import Foundation

final class RunSessionSyncService {

    let baseURL: String
    let userId: String

    init(baseURL: String, userId: String) {
        self.baseURL = baseURL
        self.userId = userId
    }

    func upload(_ session: RunSession) {

        guard let url = URL(string: "\(baseURL)/api/run-session") else {
            return
        }

        let formatter = ISO8601DateFormatter()

        let payload = RunSessionPayload(
            user_id: userId,
            start_time: formatter.string(from: session.startDate),
            distance_km: session.distanceKm,
            duration_min: session.durationMin,
            avg_hr: session.avgHR,
            z1_min: session.z1,
            z2_min: session.z2,
            z3_min: session.z3,
            z4_min: session.z4,
            z5_min: session.z5,
            elevation_m: session.elevationGainM,
            active_kcal: session.activeKcal
        )

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONEncoder().encode(payload)

        URLSession.shared.dataTask(with: req).resume()
    }
}
