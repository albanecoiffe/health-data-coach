import Charts
import SwiftUI

struct WeekHRZoneChartView: View {
    let sessions: [SessionZoneBreakdown]

    private var totals: [(zone: String, value: Double, color: Color)] {
        [
            ("Z1", sessions.map(\.z1).reduce(0, +), .green),
            ("Z2", sessions.map(\.z2).reduce(0, +), .blue),
            ("Z3", sessions.map(\.z3).reduce(0, +), .yellow),
            ("Z4", sessions.map(\.z4).reduce(0, +), .orange),
            ("Z5", sessions.map(\.z5).reduce(0, +), .red)
        ]
    }

    private var totalZoneTime: Double {
        totals.map(\.value).reduce(0, +)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Zones cardiaques (temps total semaine)")
                .font(.title3.bold())
                .foregroundColor(.white)
                .padding(.leading, 8)

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
                    ForEach(totals, id: \.zone) { item in
                        BarMark(
                            x: .value("Zone", item.zone),
                            y: .value("Minutes", item.value)
                        )
                        .foregroundStyle(item.color)
                    }
                }
                .frame(height: 240)
                .padding(.horizontal)
            }
        }
    }
}
