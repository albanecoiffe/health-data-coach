import Foundation

struct HeartRateSample: Identifiable, Hashable {
    let id = UUID()
    let timeOffset: Double   // secondes depuis le début
    let bpm: Double
}
