import Charts
import SwiftUI

struct MetricBlock: View {
    let title: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.caption.weight(.semibold))
                .foregroundColor(.gray)

            Text(value)
                .font(.title2.bold())
                .foregroundColor(color)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color.white.opacity(0.06))
        )
    }
}

struct SessionMetricsGrid: View {
    let session: DailyRunData

    var body: some View {
        LazyVGrid(columns: [
            GridItem(.flexible()),
            GridItem(.flexible())
        ], spacing: 14) {
            MetricBlock(
                title: "Distance",
                value: String(format: "%.2f km", session.distanceKm),
                color: .blue
            )

            MetricBlock(
                title: "Durée",
                value: "\(Int(session.durationMin)) min",
                color: .yellow
            )

            MetricBlock(
                title: "Dénivelé",
                value: "\(Int(session.elevationGainM)) m",
                color: .green
            )

            MetricBlock(
                title: "FC moy.",
                value: session.averageHeartRate > 0 ? "\(Int(session.averageHeartRate)) bpm" : "—",
                color: .red
            )
        }
    }
}

struct HRZoneBarChart: View {
    let session: DailyRunData

    private var totalZoneTime: Double {
        HeartRateZones.totalMinutes(for: session)
    }

    private var lowIntensityPct: Double {
        guard totalZoneTime > 0 else { return 0 }
        return HeartRateZones.lowIntensityMinutes(for: session) / totalZoneTime * 100
    }

    private var highIntensityPct: Double {
        guard totalZoneTime > 0 else { return 0 }
        return HeartRateZones.highIntensityMinutes(for: session) / totalZoneTime * 100
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Zones cardiaques")
                .font(.headline)
                .foregroundColor(.white)

            HeartRateZoneLegend()

            Chart {
                ForEach(HeartRateZones.values(for: session), id: \.zone.id) { item in
                    BarMark(
                        x: .value("Zone", item.zone.label),
                        y: .value("Min", item.minutes)
                    )
                    .foregroundStyle(item.zone.color)
                }
            }
            .frame(height: 180)

            Divider().background(.white.opacity(0.1))

            HStack {
                VStack(alignment: .leading) {
                    Text(HeartRateZones.lowIntensityTitle)
                        .foregroundColor(.gray)
                    Text(String(format: "%.0f %%", lowIntensityPct))
                        .font(.headline.bold())
                        .foregroundColor(.green)
                }

                Spacer()

                VStack(alignment: .leading) {
                    Text(HeartRateZones.highIntensityTitle)
                        .foregroundColor(.gray)
                    Text(String(format: "%.0f %%", highIntensityPct))
                        .font(.headline.bold())
                        .foregroundColor(.red)
                }
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.05))
        )
    }
}
