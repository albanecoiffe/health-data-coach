import Charts
import SwiftUI

struct MonthlyTrainingMixView: View {
    let monthlyData: [MonthlyRunData]

    private var chartData: [MonthlyTrainingMetric] {
        monthlyData.flatMap { month in
            [
                MonthlyTrainingMetric(monthLabel: month.monthLabel, metric: "km", value: month.distanceKm, color: .blue),
                MonthlyTrainingMetric(monthLabel: month.monthLabel, metric: "heures", value: month.durationMin / 60, color: .yellow),
                MonthlyTrainingMetric(monthLabel: month.monthLabel, metric: "D+ /100", value: month.elevationGainM / 100, color: .green)
            ]
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Mix mensuel")
                    .font(.headline.bold())
                    .foregroundColor(.white)

                Text("Distance, temps et dénivelé sur la même lecture")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }

            Chart(chartData) { point in
                BarMark(
                    x: .value("Mois", point.monthLabel),
                    y: .value("Valeur", point.value)
                )
                .foregroundStyle(by: .value("Métrique", point.metric))
                .position(by: .value("Métrique", point.metric))
                .cornerRadius(4)
            }
            .chartForegroundStyleScale([
                "km": Color.blue,
                "heures": Color.yellow,
                "D+ /100": Color.green
            ])
            .chartYAxis { AxisMarks(position: .leading) }
            .frame(height: 260)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.06))
        )
        .padding(.horizontal)
    }
}

private struct MonthlyTrainingMetric: Identifiable {
    let id = UUID()
    let monthLabel: String
    let metric: String
    let value: Double
    let color: Color
}
