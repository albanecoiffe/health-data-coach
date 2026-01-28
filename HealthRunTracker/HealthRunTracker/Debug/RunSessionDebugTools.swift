import Foundation

/// ⚠️ UTILISATION MANUELLE UNIQUEMENT
/// Debug / bootstrap backend / export dataset
struct RunSessionDebugTools {

    static func exportSessionsToCSV(_ sessions: [RunSession]) {
        var csv =
        "date,distance_km,duration_min,pace_min_per_km," +
        "z1_min,z2_min,z3_min,z4_min,z5_min," +
        "low_intensity_pct,high_intensity_pct\n"

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"

        for s in sessions {
            let total = s.z1 + s.z2 + s.z3 + s.z4 + s.z5
            let lowPct = total > 0 ? (s.z1 + s.z2 + s.z3) / total : 0
            let highPct = total > 0 ? (s.z4 + s.z5) / total : 0
            let pace = s.distanceKm > 0 ? s.durationMin / s.distanceKm : 0

            csv +=
            "\(formatter.string(from: s.startDate))," +
            "\(s.distanceKm)," +
            "\(s.durationMin)," +
            "\(pace)," +
            "\(s.z1),\(s.z2),\(s.z3),\(s.z4),\(s.z5)," +
            "\(lowPct),\(highPct)\n"
        }

        let fileURL = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("run_sessions_24_months.csv")

        try? csv.write(to: fileURL, atomically: true, encoding: .utf8)
        print("✅ CSV exporté:", fileURL)
    }

    static func uploadSessionsCSVToBackend() {
        
        print("🚀 uploadSessionsCSVToBackend CALLED")

        let fileURL = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("run_sessions_24_months.csv")

        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            print("❌ Sessions CSV introuvable")
            return
        }

        guard let url = URL(string: "\(baseURL)/upload-sessions-csv") else {
            print("❌ URL backend invalide")
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue(
            "multipart/form-data; boundary=\(boundary)",
            forHTTPHeaderField: "Content-Type"
        )

        var body = Data()

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"run_sessions_24_months.csv\"\r\n"
                .data(using: .utf8)!
        )
        body.append("Content-Type: text/csv\r\n\r\n".data(using: .utf8)!)
        body.append((try? Data(contentsOf: fileURL)) ?? Data())
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        URLSession.shared.dataTask(with: request) { _, response, error in
            if let error = error {
                print("❌ Upload sessions CSV error:", error)
                return
            }

            if let http = response as? HTTPURLResponse {
                print("✅ Sessions CSV upload status:", http.statusCode)
            }
        }.resume()
    }
}
