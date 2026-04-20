import SwiftUI

struct WeekComparisonView: View {
    let currentWeekData: [DailyRunData]
    let previousWeekData: [DailyRunData]

    private func diffColor(_ value: Double) -> Color {
        value > 0 ? .green : (value < 0 ? .red : .gray)
    }

    var body: some View {
        let curr = (
            dist: currentWeekData.map(\.distanceKm).reduce(0, +),
            dur: currentWeekData.map(\.durationMin).reduce(0, +),
            elev: currentWeekData.map(\.elevationGainM).reduce(0, +),
            sess: currentWeekData.count
        )

        let prev = (
            dist: previousWeekData.map(\.distanceKm).reduce(0, +),
            dur: previousWeekData.map(\.durationMin).reduce(0, +),
            elev: previousWeekData.map(\.elevationGainM).reduce(0, +),
            sess: previousWeekData.count
        )

        VStack(alignment: .leading, spacing: 16) {
            Text("Comparé à la semaine dernière")
                .font(.title3.bold())
                .foregroundColor(.white)
                .padding(.leading, 8)

            comparisonRow("Distance", delta: curr.dist - prev.dist, unit: " km")
            comparisonRow("Temps total", delta: curr.dur - prev.dur, unit: " min")
            comparisonRow("Dénivelé", delta: curr.elev - prev.elev, unit: " m")
            comparisonRow("Séances", delta: Double(curr.sess - prev.sess), unit: "")
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.04))
        )
        .padding(.horizontal)
        .padding(.bottom, 40)
    }

    private func comparisonRow(_ title: String, delta: Double, unit: String) -> some View {
        HStack {
            Text(title).foregroundColor(.gray)
            Spacer()
            Text(String(format: "%+.1f\(unit)", delta))
                .foregroundColor(diffColor(delta))
        }
        .font(.headline)
    }
}
