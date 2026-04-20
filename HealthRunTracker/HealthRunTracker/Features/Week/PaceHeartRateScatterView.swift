import Charts
import SwiftUI

struct PaceHeartRateScatterView: View {
    let sessions: [DailyRunData]

    private var points: [PaceHeartRatePoint] {
        sessions.compactMap { session in
            guard session.distanceKm > 0, session.averageHeartRate > 0 else { return nil }

            return PaceHeartRatePoint(
                date: session.date,
                dayLabel: session.dayLabel,
                paceMinPerKm: session.durationMin / session.distanceKm,
                averageHeartRate: session.averageHeartRate,
                distanceKm: session.distanceKm
            )
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Allure vs cardio")
                    .font(.headline.bold())
                    .foregroundColor(.white)

                Text("Un point par séance")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }

            if points.isEmpty {
                Text("Pas assez de séances avec fréquence cardiaque moyenne pour afficher la relation allure/cardio.")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            } else {
                Chart(points) { point in
                    PointMark(
                        x: .value("Allure min/km", point.paceMinPerKm),
                        y: .value("FC moyenne", point.averageHeartRate)
                    )
                    .symbolSize(max(45, min(150, point.distanceKm * 10)))
                    .foregroundStyle(.cyan)
                    .annotation(position: .top) {
                        Text(point.dayLabel)
                            .font(.caption2.weight(.semibold))
                            .foregroundColor(.gray)
                    }
                }
                .chartXAxisLabel("min/km")
                .chartYAxisLabel("bpm")
                .chartYAxis { AxisMarks(position: .leading) }
                .frame(height: 220)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.06))
        )
        .padding(.horizontal)
    }
}

private struct PaceHeartRatePoint: Identifiable {
    let id = UUID()
    let date: Date
    let dayLabel: String
    let paceMinPerKm: Double
    let averageHeartRate: Double
    let distanceKm: Double
}
