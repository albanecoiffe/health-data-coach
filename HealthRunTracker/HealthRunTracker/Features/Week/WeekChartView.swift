import Charts
import SwiftUI

struct WeekChartView: View {
    let weeklyData: [DailyRunData]
    let onSelect: ([DailyRunData]) -> Void

    var body: some View {
        Chart(weeklyData) { dataPoint in
            BarMark(
                x: .value("Jour", dataPoint.dayLabel),
                y: .value("Distance", dataPoint.distanceKm)
            )
            .cornerRadius(6)
            .foregroundStyle(
                LinearGradient(
                    colors: [.blue.opacity(0.9), .blue.opacity(0.4)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
        }
        .chartOverlay { proxy in
            GeometryReader { geo in
                Rectangle()
                    .fill(.clear)
                    .contentShape(Rectangle())
                    .onTapGesture { location in
                        let x = location.x - geo[proxy.plotAreaFrame].origin.x

                        if let day: String = proxy.value(atX: x) {
                            let daySessions = weeklyData
                                .filter { $0.dayLabel == day }
                                .sorted { $0.date < $1.date }

                            if !daySessions.isEmpty {
                                onSelect(daySessions)
                            }
                        }
                    }
            }
        }
        .chartYAxis { AxisMarks(position: .leading) }
        .frame(height: 220)
        .padding(.horizontal)
    }
}
