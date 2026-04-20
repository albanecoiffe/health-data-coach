import Charts
import SwiftUI

struct WeeklyVolumeTrendView: View {
    let weeklyData: [WeeklyDistanceData]

    private var movingAverage: [WeeklyMovingAveragePoint] {
        weeklyData.enumerated().map { index, week in
            let start = max(0, index - 3)
            let window = weeklyData[start...index]
            let average = window.map(\.distanceKm).reduce(0, +) / Double(window.count)

            return WeeklyMovingAveragePoint(
                weekNumber: week.weekNumber,
                distanceKm: average
            )
        }
    }

    private var bestWeek: WeeklyDistanceData? {
        weeklyData.max(by: { $0.distanceKm < $1.distanceKm })
    }

    private var averageDistance: Double {
        guard !weeklyData.isEmpty else { return 0 }
        return weeklyData.map(\.distanceKm).reduce(0, +) / Double(weeklyData.count)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Tendance hebdomadaire")
                        .font(.headline.bold())
                        .foregroundColor(.white)

                    Text("Barres = semaine, ligne = moyenne 4 semaines")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text("\(Int(averageDistance)) km")
                        .font(.title3.bold())
                        .foregroundColor(.blue)

                    Text("moyenne")
                        .font(.caption.weight(.semibold))
                        .foregroundColor(.gray)
                }
            }

            if weeklyData.isEmpty {
                ProgressView("Chargement du graphique...")
                    .foregroundColor(.gray)
                    .padding()
            } else {
                Chart {
                    ForEach(weeklyData) { point in
                        BarMark(
                            x: .value("Semaine", point.weekNumber),
                            y: .value("Distance", point.distanceKm)
                        )
                        .foregroundStyle(point.weekNumber == bestWeek?.weekNumber ? .green : .blue.opacity(0.45))
                        .cornerRadius(4)
                    }

                    ForEach(movingAverage) { point in
                        LineMark(
                            x: .value("Semaine", point.weekNumber),
                            y: .value("Moyenne 4 semaines", point.distanceKm)
                        )
                        .foregroundStyle(.yellow)
                        .lineStyle(StrokeStyle(lineWidth: 3))
                        .interpolationMethod(.catmullRom)
                    }
                }
                .chartYAxis { AxisMarks(position: .leading) }
                .chartXAxis {
                    AxisMarks(values: .stride(by: 4)) { value in
                        AxisGridLine()
                        AxisValueLabel {
                            if let week = value.as(Int.self) {
                                Text("S\(week)")
                            }
                        }
                    }
                }
                .frame(height: 260)
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

private struct WeeklyMovingAveragePoint: Identifiable {
    let id = UUID()
    let weekNumber: Int
    let distanceKm: Double
}
