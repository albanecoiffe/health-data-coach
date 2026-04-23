import Foundation

enum APIConfig {
    private static func plistValue(_ key: String) -> String? {
        guard let value = Bundle.main.object(forInfoDictionaryKey: key) as? String else {
            return nil
        }

        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !trimmed.hasPrefix("$(") else {
            return nil
        }

        return trimmed
    }

    static let baseURL: String = {
        if let configured = plistValue("HEALTHCOACH_API_BASE_URL") {
            return configured
        }

        #if DEBUG
        return "http://MacBook-Pro-de-Albane.local:8000"
        #else
        return "https://healthcoach-api.onrender.com"
        #endif
    }()

    static let importToken: String? = plistValue("HEALTHCOACH_IMPORT_TOKEN")
}
