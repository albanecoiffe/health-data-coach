import SwiftUI

struct WeekStatsGrid: View {
    let totalDistance: Double
    let totalElevation: Double
    let totalDuration: Double
    let sessionCount: Int

    var body: some View {
        LazyVGrid(columns: [
            GridItem(.flexible(), spacing: 14),
            GridItem(.flexible(), spacing: 14)
        ], spacing: 14) {
            StatCardCompact(
                title: "Distance",
                value: "\(String(format: "%.2f", totalDistance)) km",
                color: .blue
            )

            StatCardCompact(
                title: "Dénivelé",
                value: "\(Int(totalElevation)) m",
                color: .green
            )

            StatCardCompact(
                title: "Temps",
                value: "\(Int(totalDuration)) min",
                color: .yellow
            )

            StatCardCompact(
                title: "Séances",
                value: "\(sessionCount)",
                color: .orange
            )
        }
        .padding(.horizontal)
    }
}
