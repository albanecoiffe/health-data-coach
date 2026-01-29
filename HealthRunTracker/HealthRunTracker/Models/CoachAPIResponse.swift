import Foundation

struct CoachAPIResponse: Codable {
    let reply: String?
    let type: String?
    let meta: [String: String]?
}
