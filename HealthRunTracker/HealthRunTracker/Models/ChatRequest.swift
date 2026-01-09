import Foundation

struct SnapshotPair: Codable {
    let left: WeeklySnapshot
    let right: WeeklySnapshot
}

struct ChatRequest: Codable {
    let message: String

    // 🔑 Snapshot principal (TOUJOURS présent)
    let snapshot: WeeklySnapshot

    // 🔁 Comparaison (optionnelle)
    let snapshots: SnapshotPair?
    let meta: [String: String]?
    let signature: RunnerSignature?

    init(
        message: String,
        snapshot: WeeklySnapshot,
        snapshots: SnapshotPair? = nil,
        meta: [String: String]? = nil,
        signature: RunnerSignature? = nil
    ) {
        self.message = message
        self.snapshot = snapshot
        self.snapshots = snapshots
        self.meta = meta
        self.signature = signature
    }
}
