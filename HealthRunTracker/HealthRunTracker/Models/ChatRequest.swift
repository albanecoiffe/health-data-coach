import Foundation

struct ChatRequest: Codable {
    let message: String
    let meta: [String: String]?

    init(
        message: String,
        meta: [String: String]? = nil
    ) {
        self.message = message
        self.meta = meta
    }
}
