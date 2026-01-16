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
    // METTRE FALSE QUAND ON VEUT PAS TELECHARGER LES CSV
    private let shouldRefreshCSVOnAppear = true
    
    func refreshSessionsCSVIfNeeded() {
        print("🔄 Refresh sessions CSV")

        healthManager.fetchRunSessions(
            from: Calendar.current.date(byAdding: .month, value: -24, to: Date())!,
            to: Date()
        ) { sessions in
            print("🧪 Sessions fetched:", sessions.count)

            self.healthManager.exportSessionsToCSV(sessions)
            self.healthManager.uploadSessionsCSVToBackend()
        }
    }
    
    private var hasAppeared = false

    init(healthManager: HealthManager) {
        self.healthManager = healthManager
    }

    func onAppear() {
        guard !hasAppeared else {
            print("⚠️ ChatViewModel.onAppear ignoré (déjà appelé)")
            return
        }

        hasAppeared = true
        print("🚀 ChatViewModel.onAppear EXECUTÉ")

        healthManager.buildRunnerSignatureIfNeeded()
        // A COMMENTER QUAND IL Y A PAS BESOIN D'OBTENIR LES CSV MIS A JOUR :
        //debugRunnerSignature()
        //healthManager.debugSessionDataset()
        debugRunnerSignature()
        healthManager.debugSessionDataset()
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

        // 1️⃣ Construire la signature (52 semaines suffisent)
        healthManager.makeWeeklySnapshots(weeks: 52) { signatureWeeks in

            guard let signature = RunnerSignatureBuilder.build(from: signatureWeeks) else {
                print("❌ SIGNATURE BUILD FAILED")
                return
            }

            print("✅ RUNNER SIGNATURE READY")
            dump(signature)

            // 2️⃣ Récupérer les 104 semaines pour le dataset
            self.healthManager.makeWeeklySnapshots(weeks: 104) { datasetWeeks in

                // 3️⃣ Export CSV enrichi
                self.exportWeeksToCSV(datasetWeeks, signature: signature)

                // 4️⃣ Upload backend
                self.uploadCSVToBackend()
            }
        }

        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        print("📂 Documents:", docs)
    }

    func exportWeeksToCSV(
        _ weeks: [WeeklySnapshot],
        signature: RunnerSignature
    ) {

        var csv = ""
        csv += "week_start,week_end,"
        csv += "distance_km,sessions,duration_min,"
        csv += "low_intensity_pct,high_intensity_pct,"
        csv += "variation_km,"
        csv += "longest_run_km,"
        csv += "weekly_load,"
        csv += "sig_weekly_avg_km,sig_weekly_std_km,sig_trend_12w_pct,"
        csv += "sig_z4_z5_avg_pct,sig_z4_z5_trend_12w_pct,"
        csv += "sig_acwr_avg,sig_acwr_max,sig_load_std_trend_12w_pct\n"

        // ✅ ordre chronologique indispensable
        let sorted = weeks.sorted { $0.period.start < $1.period.start }

        var prevDistance: Double? = nil

        for w in sorted {

            let z = w.zonesPercent ?? [:]

            let low = (z["z1"] ?? 0)
                    + (z["z2"] ?? 0)
                    + (z["z3"] ?? 0)

            let high = (z["z4"] ?? 0)
                     + (z["z5"] ?? 0)

            // ✅ variation_km
            let variationKm: Double
            if let prev = prevDistance {
                variationKm = w.totals.distanceKm - prev
            } else {
                variationKm = 0
            }
            prevDistance = w.totals.distanceKm

            // ✅ longest run de la semaine
            let longestRun = w.longestRunKm ?? 0

            // ✅ charge hebdomadaire (proxy simple et valide)
            let weeklyLoad =
                w.totals.durationMin * (1.0 + high)

            let line =
                "\(w.period.start),\(w.period.end)," +
                "\(w.totals.distanceKm)," +
                "\(w.totals.sessions)," +
                "\(w.totals.durationMin)," +
                "\(low)," +
                "\(high)," +
                "\(variationKm)," +
                "\(longestRun)," +
                "\(weeklyLoad)," +
                "\(signature.volume.weekly_avg_km)," +
                "\(signature.volume.weekly_std_km)," +
                "\(signature.volume.trend_12w_pct)," +
                "\(signature.intensity.z4_z5_avg_pct)," +
                "\(signature.intensity.z4_z5_trend_12w_pct)," +
                "\(signature.load.acwrAvg)," +
                "\(signature.load.acwrMax)," +
                "\(signature.adaptation.loadStdTrend12wPct)\n"

            csv += line
        }

        let fileURL = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("weekly_snapshots_24_months.csv")

        do {
            try csv.write(to: fileURL, atomically: true, encoding: .utf8)
            print("✅ CSV exporté :", fileURL)
        } catch {
            print("❌ Erreur export CSV :", error)
        }
    }


    func uploadCSVToBackend() {
        let fileURL = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("weekly_snapshots_24_months.csv")

        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            print("❌ CSV introuvable")
            return
        }

        var request = URLRequest(url: URL(string: "\(baseURL)/upload-weeks-csv")!)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue(
            "multipart/form-data; boundary=\(boundary)",
            forHTTPHeaderField: "Content-Type"
        )

        var body = Data()

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"weeks.csv\"\r\n"
                .data(using: .utf8)!
        )
        body.append("Content-Type: text/csv\r\n\r\n".data(using: .utf8)!)
        body.append(try! Data(contentsOf: fileURL))
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        URLSession.shared.dataTask(with: request) { _, _, error in
            if let error = error {
                print("❌ Upload error:", error)
            } else {
                print("✅ CSV envoyé au backend")
            }
        }.resume()
    }

    
}
