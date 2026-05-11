import Foundation

enum APIConfig {
    private static func composedBaseURL() -> String? {
        guard
            let scheme = plistValue("HEALTHCOACH_API_SCHEME"),
            let host = plistValue("HEALTHCOACH_API_HOST")
        else {
            return nil
        }

        let trimmedScheme = scheme.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedHost = host.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedScheme.isEmpty, !trimmedHost.isEmpty else { return nil }

        let composed = "\(trimmedScheme)://\(trimmedHost)"
        guard let url = URL(string: composed), url.scheme != nil, url.host != nil else {
            return nil
        }

        return composed
    }

    private static func plistValue(_ key: String) -> String? {
        guard let value = Bundle.main.object(forInfoDictionaryKey: key) as? String else {
            return nil
        }

        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !trimmed.hasPrefix("$(") else {
            return nil
        }

        if key == "HEALTHCOACH_API_BASE_URL" {
            guard let url = URL(string: trimmed), url.scheme != nil, url.host != nil else {
                return nil
            }
        }

        return trimmed
    }

    static let baseURL: String = {
        if let composed = composedBaseURL() {
            return composed
        }

        if let configured = plistValue("HEALTHCOACH_API_BASE_URL") {
            return configured
        }

        return "https://healthcoach-api-ri82.onrender.com"
    }()

    static let importToken: String? = plistValue("HEALTHCOACH_IMPORT_TOKEN")
}
