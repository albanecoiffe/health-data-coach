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
let baseURL = "http://192.168.1.113:8000"


class ChatViewModel: ObservableObject {
    private let sessionId = UUID().uuidString
    @Published var messages: [ChatMessage] = []
    @Published var currentInput: String = ""
    private let healthManager: HealthManager

    init(healthManager: HealthManager) {
        self.healthManager = healthManager
        healthManager.buildRunnerSignatureIfNeeded()
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

        guard let url = URL(string: "\(baseURL)/chat") else {
            return "URL invalide."
        }

        let calendar = Calendar.current
        let now = Date()
        let interval = calendar.dateInterval(of: .weekOfYear, for: now)!

        return await withCheckedContinuation { continuation in

            print("📤 ASK COACH:", message)

            healthManager.makeSnapshot(from: interval.start, to: interval.end) { snapshot in

                print("📦 SNAPSHOT SENT:",
                      snapshot.totals.sessions, "séances /",
                      snapshot.totals.distanceKm, "km")

                Task {
                    do {
                        var meta: [String: String] = [:]
                        meta["session_id"] = self.sessionId

                        let payload = ChatRequest(
                            message: message,
                            snapshot: snapshot,
                            meta: meta,
                            signature: self.healthManager.runnerSignature
                        )

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

                        print("🟣 RAW:", String(data: data, encoding: .utf8) ?? "nil")

                        let decoded = try JSONDecoder().decode(CoachAPIResponse.self, from: data)

                        print("🧠 COACH RESPONSE")
                        print("   type:", decoded.type ?? "nil")
                        print("   reply:", decoded.reply ?? "nil")

                        // ======================================================
                        // 🔑 ROUTING UNIQUE PAR TYPE
                        // ======================================================
                        switch decoded.type {

                        // ===============================
                        // 🟢 RÉPONSE FINALE
                        // ===============================
                        case "ANSWER_NOW", "RECOMMENDATION":
                            continuation.resume(
                                returning: decoded.reply ?? "Le coach n’a rien à ajouter."
                            )
                            return

                        // ===============================
                        // 🟠 SNAPSHOT SIMPLE
                        // ===============================
                        case "REQUEST_SNAPSHOT":
                            guard let period = decoded.period else {
                                continuation.resume(returning: "Erreur période demandée")
                                return
                            }

                            let formatter = DateFormatter()
                            formatter.dateFormat = "yyyy-MM-dd"

                            guard
                                let start = formatter.date(from: period.start),
                                let end = formatter.date(from: period.end)
                            else {
                                continuation.resume(returning: "Erreur parsing période")
                                return
                            }

                            let reply = await self.requestSnapshotAndRetry(
                                message: message,
                                start: start,
                                end: end,
                                meta: decoded.meta
                            )

                            continuation.resume(returning: reply)
                            return

                        // ===============================
                        // 🟣 COMPARAISON
                        // ===============================
                        case "REQUEST_SNAPSHOT_BATCH":
                            guard let batch = decoded.snapshots,
                                  let meta = decoded.meta else {
                                continuation.resume(returning: "Erreur comparaison")
                                return
                            }

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

                        // ===============================
                        // ⚠️ CAS INCONNU
                        // ===============================
                        default:
                            print("⚠️ TYPE INCONNU:", decoded.type ?? "nil")
                            continuation.resume(returning: "Réponse non reconnue du coach.")
                            return
                        }

                    } catch {
                        print("❌ ERREUR RÉSEAU / DÉCODAGE:", error)
                        continuation.resume(returning: "Le coach ne répond pas")
                    }
                }
            }
        }
    }




    private func sendPayload(_ payload: ChatRequest) async -> String {

        guard let url = URL(string: "\(baseURL)/chat") else {
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

            return decoded.reply ?? "Aucune réponse du coach."

        } catch {
            return "Erreur serveur."
        }
    }

    
    private func sendPayloadRaw(_ payload: ChatRequest) async -> CoachAPIResponse? {
        guard let url = URL(string: "\(baseURL)/chat") else {
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
        end: Date,
        meta: [String: String]?
    ) async -> String? {

        await withCheckedContinuation { continuation in

            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"

            var enrichedMeta = meta ?? [:]

            // ✅ Période demandée
            enrichedMeta["requested_start"] = formatter.string(from: start)
            enrichedMeta["requested_end"]   = formatter.string(from: end)

            // ✅ Garde-fous
            enrichedMeta["metric"] = enrichedMeta["metric"] ?? "DISTANCE"
            enrichedMeta["reply_mode"] = enrichedMeta["reply_mode"] ?? "FACTUAL"

            healthManager.makeSnapshot(from: start, to: end) { snapshot in
                Task {
                    var finalMeta = enrichedMeta
                    finalMeta["session_id"] = self.sessionId

                    let payload = ChatRequest(
                        message: message,
                        snapshot: snapshot,
                        meta: finalMeta,
                        signature: self.healthManager.runnerSignature
                    )

                    // 🔴 IMPORTANT : on utilise la réponse BRUTE
                    guard let decoded = await self.sendPayloadRaw(payload) else {
                        continuation.resume(returning: "Erreur serveur.")
                        return
                    }

                    print("🔁 RETRY RESPONSE")
                    print("   type:", decoded.type ?? "nil")
                    print("   reply:", decoded.reply ?? "nil")

                    switch decoded.type {

                    // ===============================
                    // 🟢 RÉPONSE FINALE
                    // ===============================
                    case "ANSWER_NOW":
                        continuation.resume(
                            returning: decoded.reply ?? "Le coach n’a rien à ajouter."
                        )
                        return

                    // ===============================
                    // ❌ ERREUR LOGIQUE
                    // ===============================
                    case "REQUEST_SNAPSHOT":
                        continuation.resume(
                            returning: "Erreur interne : snapshot demandé en boucle."
                        )
                        return

                    // ===============================
                    // ⚠️ CAS INATTENDU
                    // ===============================
                    default:
                        continuation.resume(
                            returning: "Réponse non reconnue du coach."
                        )
                        return
                    }
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

            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"

            let enrichedMeta: [String: String] = {
                var m = meta
                m["requested_left_start"] = formatter.string(from: leftStart)
                m["requested_left_end"]   = formatter.string(from: leftEnd)
                m["requested_right_start"] = formatter.string(from: rightStart)
                m["requested_right_end"]   = formatter.string(from: rightEnd)
                return m
            }()

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
                            var finalMeta = enrichedMeta
                            finalMeta["session_id"] = self.sessionId
                            
                            let payload = ChatRequest(
                                message: message,
                                snapshot: leftSnapshot, // requis par FastAPI
                                snapshots: SnapshotPair(
                                    left: leftSnapshot,
                                    right: rightSnapshot
                                ),
                                meta: finalMeta,
                                signature: self.healthManager.runnerSignature
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
            // 🔵 CAS SEMAINE / MOIS
            // ======================================================
            healthManager.makeSnapshot(from: leftStart, to: leftEnd) { leftSnapshot in
                self.healthManager.makeSnapshot(from: rightStart, to: rightEnd) { rightSnapshot in

                    Task {
                        var finalMeta = enrichedMeta
                        finalMeta["session_id"] = self.sessionId
                        let payload = ChatRequest(
                            message: message,
                            snapshot: leftSnapshot,
                            snapshots: SnapshotPair(
                                left: leftSnapshot,
                                right: rightSnapshot
                            ),
                            meta: finalMeta,
                            signature: self.healthManager.runnerSignature
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
    
    func debugRunnerSignature() {

        healthManager.makeWeeklySnapshots(weeks: 52) { weeklySnapshots in

            print("🧪 SNAPSHOTS COUNT:", weeklySnapshots.count)

            if let signature = RunnerSignatureBuilder.build(from: weeklySnapshots) {

                print("✅ RUNNER SIGNATURE")
                dump(signature)

            } else {
                print("❌ SIGNATURE BUILD FAILED")
            }
        }
    }
    


}
