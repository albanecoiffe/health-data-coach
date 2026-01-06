import Foundation
import Combine

struct SnapshotRange: Codable {
    let start: String
    let end: String
}

struct SnapshotBatchPayload: Codable {
    let left: SnapshotRange
    let right: SnapshotRange
}

struct CoachAPIResponse: Codable {
    let reply: String?
    let type: String?
    let period: PeriodPayload?
    let snapshots: SnapshotBatchPayload?
    let meta: [String: String]?
}

struct PeriodPayload: Codable {
    let start: String
    let end: String
}


class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var currentInput: String = ""

    private let healthManager: HealthManager

    init(healthManager: HealthManager) {
        self.healthManager = healthManager
    }

    func sendMessage() {
        let text = currentInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        let userMsg = ChatMessage(text: text, isUser: true)
        messages.append(userMsg)
        currentInput = ""

        // 🔑 On autorise toujours l'envoi
        Task {
            let reply = await askPythonBot(text) ?? "Erreur dans la réponse du coach."
            await MainActor.run {
                self.messages.append(ChatMessage(text: reply, isUser: false))
            }
        }
    }


    func askPythonBot(_ message: String) async -> String? {

        guard let url = URL(string: "http://192.168.1.77:8000/chat") else {
            return "URL invalide."
        }

        let calendar = Calendar.current
        let now = Date()
        let interval = calendar.dateInterval(of: .weekOfYear, for: now)!
        
        // 🔑 ON ATTEND LE SNAPSHOT
        return await withCheckedContinuation { continuation in

            healthManager.makeSnapshot(
                from: interval.start,
                to: interval.end
            ) { snapshot in

                Task {
                    let payload = ChatRequest(
                        message: message,
                        snapshot: snapshot
                    )

                    do {
                        var req = URLRequest(url: url)
                        req.httpMethod = "POST"
                        req.setValue("application/json", forHTTPHeaderField: "Content-Type")

                        let encoder = JSONEncoder()
                        encoder.keyEncodingStrategy = .convertToSnakeCase
                        req.httpBody = try encoder.encode(payload)

                        let (data, response) = try await URLSession.shared.data(for: req)

                        guard let http = response as? HTTPURLResponse,
                              (200...299).contains(http.statusCode) else {
                            continuation.resume(returning: "Erreur serveur")
                            return
                        }

                        let decoded = try JSONDecoder().decode(CoachAPIResponse.self, from: data)

                        print("🟣 RAW:", String(data: data, encoding: .utf8) ?? "nil")
                        print("🟣 reply:", decoded.reply ?? "nil")
                        print("🟣 type:", decoded.type ?? "nil")

                        // 🟢 Réponse finale
                        if let reply = decoded.reply {
                            continuation.resume(returning: reply)
                            return
                        }

                        // 🟣 Demande SNAPSHOT BATCH (COMPARAISON)
                        if decoded.type == "REQUEST_SNAPSHOT_BATCH",
                           let batch = decoded.snapshots,
                           let meta = decoded.meta {

                            let formatter = DateFormatter()
                            formatter.dateFormat = "yyyy-MM-dd"

                            guard
                                let leftStart = formatter.date(from: batch.left.start),
                                let leftEnd = formatter.date(from: batch.left.end),
                                let rightStart = formatter.date(from: batch.right.start),
                                let rightEnd = formatter.date(from: batch.right.end)
                            else {
                                continuation.resume(returning: "Erreur période comparaison")
                                return
                            }

                            let reply = await self.requestSnapshotBatchAndRetry(
                                message: message,
                                leftStart: leftStart,
                                leftEnd: leftEnd,
                                rightStart: rightStart,
                                rightEnd: rightEnd,
                                meta: meta
                            )

                            continuation.resume(returning: reply)
                            return
                        }

                        // 🟠 Demande SNAPSHOT SIMPLE
                        if decoded.type == "REQUEST_SNAPSHOT",
                           let period = decoded.period {

                            let formatter = DateFormatter()
                            formatter.dateFormat = "yyyy-MM-dd"

                            guard
                                let start = formatter.date(from: period.start),
                                let end = formatter.date(from: period.end)
                            else {
                                continuation.resume(returning: "Erreur période")
                                return
                            }

                            let reply = await self.requestSnapshotAndRetry(
                                message: message,
                                start: start,
                                end: end
                            )

                            continuation.resume(returning: reply)
                            return
                        }

                        continuation.resume(returning: "Réponse invalide du serveur")



                    } catch {
                        print("❌ ERREUR RÉSEAU:", error)
                        continuation.resume(returning: "Le coach ne répond pas")
                    }
                }
            }
        }
    }



    private func sendPayload(_ payload: ChatRequest) async -> String? {

        guard let url = URL(string: "http://192.168.1.77:8000/chat") else {
            return "URL invalide."
        }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            req.httpBody = try encoder.encode(payload)

            let (data, _) = try await URLSession.shared.data(for: req)
            let decoded = try JSONDecoder().decode(CoachAPIResponse.self, from: data)

            return decoded.reply

        } catch {
            return "Erreur serveur."
        }
    }
    
    private func sendPayloadRaw(_ payload: ChatRequest) async -> CoachAPIResponse? {
        guard let url = URL(string: "http://192.168.1.77:8000/chat") else {
            return nil
        }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            req.httpBody = try encoder.encode(payload)

            let (data, _) = try await URLSession.shared.data(for: req)
            return try JSONDecoder().decode(CoachAPIResponse.self, from: data)
        } catch {
            return nil
        }
    }
    
    func requestSnapshotAndRetry(
        message: String,
        start: Date,
        end: Date
    ) async -> String? {

        await withCheckedContinuation { continuation in

            healthManager.makeSnapshot(from: start, to: end) { snapshot in
                Task {
                    let payload = ChatRequest(
                        message: message,
                        snapshot: snapshot
                    )

                    let reply = await self.sendPayload(payload)
                    continuation.resume(returning: reply)
                }
            }
        }
    }

    func requestSnapshotBatchAndRetry(
        message: String,
        leftStart: Date,
        leftEnd: Date,
        rightStart: Date,
        rightEnd: Date,
        meta: [String: String]
    ) async -> String? {

        await withCheckedContinuation { continuation in

            // ======================================================
            // 🔑 CAS ANNUEL
            // ======================================================
            if meta["period_context"] == "YEAR" {

                let calendar = Calendar.current
                let leftYear = calendar.component(.year, from: leftStart)
                let rightYear = calendar.component(.year, from: rightStart)

                healthManager.makeYearSnapshot(year: leftYear) { leftSnapshot in
                    self.healthManager.makeYearSnapshot(year: rightYear) { rightSnapshot in

                        Task {
                            let payload = ChatRequest(
                                message: message,
                                snapshot: leftSnapshot,   // requis par FastAPI
                                snapshots: SnapshotPair(
                                    left: leftSnapshot,
                                    right: rightSnapshot
                                ),
                                meta: meta
                            )

                            let decoded = await self.sendPayloadRaw(payload)
                            continuation.resume(
                                returning: decoded?.reply ?? "Erreur comparaison annuelle."
                            )
                        }
                    }
                }

                return
            }

            // ======================================================
            // 🔵 CAS SEMAINE / MOIS (inchangé)
            // ======================================================
            healthManager.makeSnapshot(from: leftStart, to: leftEnd) { leftSnapshot in
                self.healthManager.makeSnapshot(from: rightStart, to: rightEnd) { rightSnapshot in

                    Task {
                        let payload = ChatRequest(
                            message: message,
                            snapshot: leftSnapshot,   // requis par FastAPI
                            snapshots: SnapshotPair(
                                left: leftSnapshot,
                                right: rightSnapshot
                            ),
                            meta: meta
                        )

                        let decoded = await self.sendPayloadRaw(payload)
                        continuation.resume(
                            returning: decoded?.reply ?? "Erreur comparaison."
                        )
                    }
                }
            }
        }
    }
}
