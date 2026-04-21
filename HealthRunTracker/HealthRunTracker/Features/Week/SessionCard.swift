import SwiftUI

struct SessionCard: View {
    let session: DailyRunData

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            header
            duration
            elevation
            speed
            pace
            avgHeartRate
            Divider().background(.white.opacity(0.1))
            zones
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.04))
        )
    }

    private var header: some View {
        HStack {
            Text(session.dayLabel)
                .font(.headline.bold())
                .foregroundColor(.white)
            Spacer()
            Text(String(format: "%.2f km", session.distanceKm))
                .foregroundColor(.blue)
        }
    }

    private var duration: some View {
        statRow("Durée", "\(Int(session.durationMin)) min", .yellow)
    }

    private var elevation: some View {
        statRow("Dénivelé", "\(Int(session.elevationGainM)) m", .green)
    }

    private var speed: some View {
        statRow(
            "Vitesse moy.",
            String(format: "%.2f km/h", session.distanceKm / (session.durationMin / 60)),
            .orange
        )
    }

    private var pace: some View {
        let pace = session.distanceKm > 0 ? session.durationMin / session.distanceKm : 0
        return statRow("Allure", String(format: "%.1f min/km", pace), .orange)
    }

    private var avgHeartRate: some View {
        statRow(
            "FC moy.",
            session.averageHeartRate > 0 ? "\(Int(session.averageHeartRate)) bpm" : "—",
            .red
        )
    }

    private var totalZoneTime: Double {
        HeartRateZones.totalMinutes(for: session)
    }

    private var lowIntensityPercent: Double {
        guard totalZoneTime > 0 else { return 0 }
        return HeartRateZones.lowIntensityMinutes(for: session) / totalZoneTime * 100
    }

    private var highIntensityPercent: Double {
        guard totalZoneTime > 0 else { return 0 }
        return HeartRateZones.highIntensityMinutes(for: session) / totalZoneTime * 100
    }

    private var zones: some View {
        VStack(spacing: 8) {
            VStack(spacing: 4) {
                ForEach(HeartRateZones.values(for: session), id: \.zone.id) { item in
                    zoneRow(item.zone, item.minutes)
                }
            }

            Divider().background(.white.opacity(0.1))

            intensityRow(HeartRateZones.lowIntensityTitle, lowIntensityPercent, .green)
            intensityRow(HeartRateZones.highIntensityTitle, highIntensityPercent, .red)
        }
    }

    private func intensityRow(_ title: String, _ percent: Double, _ color: Color) -> some View {
        HStack {
            Text(title)
                .foregroundColor(.white.opacity(0.8))
            Spacer()
            Text(String(format: "%.0f %%", percent))
                .foregroundColor(color)
                .font(.subheadline.bold())
        }
    }

    private func statRow(_ title: String, _ value: String, _ color: Color) -> some View {
        HStack {
            Text("\(title) :")
                .foregroundColor(.gray)
            Spacer()
            Text(value)
                .foregroundColor(color)
        }
    }

    @ViewBuilder
    private func zoneRow(_ zone: HeartRateZoneDefinition, _ value: Double) -> some View {
        if value > 0 {
            HStack {
                Text("\(zone.label) (\(zone.rangeText)) :")
                    .foregroundColor(.gray)
                Spacer()
                Text(String(format: "%.1f min", value))
                    .foregroundColor(zone.color)
            }
        }
    }
}
