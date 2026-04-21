import Charts
import SwiftUI

struct WeekHRZoneChartView: View {
    let sessions: [SessionZoneBreakdown]

    private var totals: [(zone: HeartRateZoneDefinition, minutes: Double)] {
        HeartRateZones.weeklyTotals(from: sessions)
    }

    private var totalZoneTime: Double {
        totals.map(\.minutes).reduce(0, +)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Zones cardiaques (temps total semaine)")
                .font(.title3.bold())
                .foregroundColor(.white)
                .padding(.leading, 8)

            HeartRateZoneLegend()

            if sessions.isEmpty {
                Text("Aucune donnée cette semaine")
                    .foregroundColor(.gray)
                    .padding()
            } else if totalZoneTime <= 0 {
                Text("Aucune donnée de fréquence cardiaque exploitable cette semaine")
                    .foregroundColor(.gray)
                    .padding()
            } else {
                Chart {
                    ForEach(totals, id: \.zone.id) { item in
                        BarMark(
                            x: .value("Zone", item.zone.label),
                            y: .value("Minutes", item.minutes)
                        )
                        .foregroundStyle(item.zone.color)
                    }
                }
                .frame(height: 240)
                .padding(.horizontal)
            }
        }
    }
}
