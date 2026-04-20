import SwiftUI
import Charts

struct WeeklyDistanceChart: View {
    @State private var weeklyData: [WeeklyDistanceData] = []
    @ObservedObject var healthManager: HealthManager

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Distance totale courue par semaine")
                .font(.headline.bold())
                .foregroundColor(.white)
                .padding(.leading, 8)

            if weeklyData.isEmpty {
                ProgressView("Chargement du graphique…")
                    .foregroundColor(.gray)
                    .padding()
            } else {
                Chart {
                    ForEach(weeklyData) { point in
                        LineMark(
                            x: .value("Semaine", Double(point.weekNumber)), // 👈 forcer Double ici
                            y: .value("Distance (km)", point.distanceKm)
                        )
                        .interpolationMethod(.catmullRom)
                        .foregroundStyle(Color.blue)
                        .lineStyle(StrokeStyle(lineWidth: 3, lineCap: .round))

                        PointMark(
                            x: .value("Semaine", Double(point.weekNumber)),
                            y: .value("Distance (km)", point.distanceKm)
                        )
                        .symbol(.circle)
                        .symbolSize(14)
                        .foregroundStyle(Color.blue)
                    }
                }
                // 👇 Forcer le domaine X à être continu de 0 à 52
                .chartXScale(domain: 0...52)
                .chartYScale(domain: yDomain)

                // 👇 Créer des ticks fixes toutes les 4 semaines
                .chartXAxis {
                    AxisMarks(values: stride(from: 0, through: 52, by: 4).map { Double($0) }) { value in
                        AxisGridLine().foregroundStyle(.gray.opacity(0.25))
                        AxisTick()
                        AxisValueLabel {
                            if let week = value.as(Double.self) {
                                Text("\(Int(week))")
                                    .font(.caption2)
                                    .foregroundColor(.gray)
                            }
                        }
                    }
                }

                // 👇 Axe Y à gauche classique
                .chartYAxis {
                    AxisMarks(position: .leading)
                }

                .frame(height: 280)
                .padding(.horizontal)
                .background(Color.white.opacity(0.03))
                .cornerRadius(12)
                .padding(.bottom, 8)
            }
        }
        .onAppear {
            loadData()
        }
    }

    // MARK: - Helpers

    private var yDomain: ClosedRange<Double> {
        let maxValue = weeklyData.map { $0.distanceKm }.max() ?? 0
        return 0...(max(40, maxValue * 1.2))
    }

    private func loadData() {
        healthManager.computeWeeklyDistanceData { data in
            if data.isEmpty {
                // ✅ Génération de mock si pas de données HealthKit
                self.weeklyData = (1...52).map {
                    WeeklyDistanceData(weekNumber: $0, distanceKm: Double.random(in: 5...40))
                }
            } else {
                self.weeklyData = data.sorted { $0.weekNumber < $1.weekNumber }
            }
            print("✅ Chargement terminé : \(weeklyData.count) points")
        }
    }
}
