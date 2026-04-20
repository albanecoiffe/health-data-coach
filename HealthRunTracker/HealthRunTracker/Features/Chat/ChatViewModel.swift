import Foundation
import Combine

class ChatViewModel: ObservableObject {

    private let sessionId = UUID().uuidString
    @Published var messages: [ChatMessage] = []
    @Published var currentInput: String = ""

    private let healthManager: HealthManager
    private var hasAppeared = false

    init(healthManager: HealthManager) {
        self.healthManager = healthManager
    }

    func onAppear() {
        guard !hasAppeared else { return }
        hasAppeared = true
        print("🚀 ChatViewModel.onAppear EXECUTÉ")
    }

    func sendMessage() {
        let text = currentInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        messages.append(ChatMessage(text: text, isUser: true))
        currentInput = ""

        Task {
            let reply = await askPythonBot(text) ?? "Erreur dans la réponse du coach."
            await MainActor.run {
                self.messages.append(ChatMessage(text: reply, isUser: false))
            }
        }
    }

    func askPythonBot(_ message: String) async -> String? {

        guard let url = URL(string: "\(APIConfig.baseURL)/chat") else {
            return "URL invalide."
        }

        return await withCheckedContinuation { continuation in

            print("📤 ASK COACH:", message)

            Task {
                do {
                    let payload = ChatRequest(
                        message: message,
                        meta: ["session_id": self.sessionId]
                    )

                    var request = URLRequest(url: url)
                    request.httpMethod = "POST"
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

                    let encoder = JSONEncoder()
                    encoder.keyEncodingStrategy = .convertToSnakeCase
                    request.httpBody = try encoder.encode(payload)

                    let (data, response) = try await URLSession.shared.data(for: request)

                    guard let http = response as? HTTPURLResponse,
                          (200...299).contains(http.statusCode) else {
                        continuation.resume(returning: "Erreur serveur")
                        return
                    }

                    let decoded = try JSONDecoder().decode(CoachAPIResponse.self, from: data)

                    continuation.resume(
                        returning: decoded.reply ?? "Le coach n’a rien à ajouter."
                    )

                } catch {
                    print("❌ ERREUR RÉSEAU:", error)
                    continuation.resume(returning: "Le coach ne répond pas")
                }
            }
        }
    }
}
