import Foundation

struct RunSessionBatchResponse: Codable {
    let status: String
    let inserted: Int?
    let updated: Int?
    let duplicates: Int?
    let total: Int?
}

struct RunSessionLatestResponse: Codable {
    let user_id: String
    let total: Int
    let latest_start_time: String?
}

final class RunSessionSyncService {

    let baseURL: String
    let userId: String

    init(baseURL: String, userId: String) {
        self.baseURL = APIConfig.baseURL
        self.userId = userId
    }

    func pingBackend(completion: @escaping (Result<String, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/health/db") else {
            completion(.failure(NSError(domain: "sync", code: -1)))
            return
        }

        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.timeoutInterval = 10

        URLSession.shared.dataTask(with: req) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion(.failure(NSError(domain: "sync", code: -2)))
                return
            }

            guard 200..<300 ~= http.statusCode else {
                completion(.failure(NSError(domain: "sync", code: http.statusCode)))
                return
            }

            let body = data.flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
            completion(.success(body))
        }.resume()
    }

    func fetchLatestSessionStartTime(completion: @escaping (Result<Date?, Error>) -> Void) {
        var components = URLComponents(string: "\(baseURL)/api/run-sessions/latest")
        components?.queryItems = [
            URLQueryItem(name: "user_id", value: userId)
        ]

        guard let url = components?.url else {
            completion(.failure(NSError(domain: "sync", code: -1)))
            return
        }

        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.timeoutInterval = 10

        URLSession.shared.dataTask(with: req) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion(.failure(NSError(domain: "sync", code: -2)))
                return
            }

            guard 200..<300 ~= http.statusCode else {
                completion(.failure(NSError(domain: "sync", code: http.statusCode)))
                return
            }

            guard let data else {
                completion(.success(nil))
                return
            }

            do {
                let decoded = try JSONDecoder().decode(RunSessionLatestResponse.self, from: data)
                guard let latestString = decoded.latest_start_time else {
                    completion(.success(nil))
                    return
                }

                let formatter = ISO8601DateFormatter()
                completion(.success(formatter.date(from: latestString)))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    func upload(_ session: RunSession, completion: ((Result<String, Error>) -> Void)? = nil) {
        print("📤 POST run-session:", session.startDate)

        guard let url = URL(string: "\(baseURL)/api/run-session") else {
            completion?(.failure(NSError(domain: "sync", code: -1)))
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
        req.timeoutInterval = 20
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONEncoder().encode(payload)

        URLSession.shared.dataTask(with: req) { data, response, error in
            if let error = error {
                completion?(.failure(error))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion?(.failure(NSError(domain: "sync", code: -2)))
                return
            }

            guard 200..<300 ~= http.statusCode else {
                completion?(.failure(NSError(domain: "sync", code: http.statusCode)))
                return
            }

            guard let data else {
                completion?(.success("inserted"))
                return
            }

            if
                let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                let status = json["status"] as? String
            {
                completion?(.success(status))
            } else {
                completion?(.success("ok"))
            }
        }.resume()
    }

    func uploadBatch(
        _ sessions: [RunSession],
        timeout: TimeInterval = 120,
        completion: @escaping (Result<RunSessionBatchResponse, Error>) -> Void
    ) {
        guard let url = URL(string: "\(baseURL)/api/run-sessions/batch") else {
            completion(.failure(NSError(domain: "sync", code: -1)))
            return
        }

        let formatter = ISO8601DateFormatter()
        let payloads = sessions.map { s in
            RunSessionPayload(
                user_id: userId,
                start_time: formatter.string(from: s.startDate),
                distance_km: s.distanceKm,
                duration_min: s.durationMin,
                avg_hr: s.avgHR,
                z1_min: s.z1,
                z2_min: s.z2,
                z3_min: s.z3,
                z4_min: s.z4,
                z5_min: s.z5,
                elevation_m: s.elevationGainM,
                active_kcal: s.activeKcal
            )
        }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.timeoutInterval = timeout
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONEncoder().encode(payloads)

        URLSession.shared.dataTask(with: req) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion(.failure(NSError(domain: "sync", code: -2)))
                return
            }

            guard 200..<300 ~= http.statusCode else {
                completion(.failure(NSError(domain: "sync", code: http.statusCode)))
                return
            }

            guard let data else {
                completion(
                    .success(
                        RunSessionBatchResponse(
                            status: "ok",
                            inserted: sessions.count,
                            updated: 0,
                            duplicates: 0,
                            total: sessions.count
                        )
                    )
                )
                return
            }

            do {
                let decoded = try JSONDecoder().decode(RunSessionBatchResponse.self, from: data)
                completion(.success(decoded))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
}
