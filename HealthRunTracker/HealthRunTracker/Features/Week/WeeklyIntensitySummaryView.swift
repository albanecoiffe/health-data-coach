import Charts
import SwiftUI

struct WeeklyIntensitySummaryView: View {
    let sessions: [DailyRunData]

    private var segments: [IntensitySegment] {
        let easy = sessions.map { $0.z1 + $0.z2 }.reduce(0, +)
        let moderate = sessions.map(\.z3).reduce(0, +)
        let hard = sessions.map { $0.z4 + $0.z5 }.reduce(0, +)

        return [
            IntensitySegment(label: "Facile", minutes: easy, color: .green),
            IntensitySegment(label: "Modéré", minutes: moderate, color: .yellow),
            IntensitySegment(label: "Intense", minutes: hard, color: .red)
        ]
    }

    private var totalMinutes: Double {
        segments.map(\.minutes).reduce(0, +)
    }

    private var easyPercent: Double {
        guard totalMinutes > 0 else { return 0 }
        return segments.first(where: { $0.label == "Facile" })!.minutes / totalMinutes * 100
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Équilibre d'intensité")
                        .font(.headline.bold())
                        .foregroundColor(.white)

                    Text(totalMinutes > 0 ? "\(Int(easyPercent)) % facile" : "Pas de cardio exploitable")
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(easyPercent >= 70 ? .green : .orange)
                }

                Spacer()
            }

            if totalMinutes > 0 {
                Chart(segments) { segment in
                    BarMark(
                        x: .value("Minutes", segment.minutes),
                        y: .value("Intensité", segment.label)
                    )
                    .foregroundStyle(segment.color)
                    .cornerRadius(6)
                }
                .chartXAxis { AxisMarks(position: .bottom) }
                .chartYAxis { AxisMarks(position: .leading) }
                .frame(height: 150)

                HStack {
                    ForEach(segments) { segment in
                        IntensityLegendItem(segment: segment, totalMinutes: totalMinutes)
                        if segment.id != segments.last?.id {
                            Spacer()
                        }
                    }
                }
            } else {
                Text("Les zones Z1 à Z5 seront affichées ici dès que les séances contiennent des mesures cardiaques.")
                    .font(.subheadline)
                    .foregroundColor(.gray)
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

private struct IntensitySegment: Identifiable {
    let id = UUID()
    let label: String
    let minutes: Double
    let color: Color
}

private struct IntensityLegendItem: View {
    let segment: IntensitySegment
    let totalMinutes: Double

    private var percent: Double {
        guard totalMinutes > 0 else { return 0 }
        return segment.minutes / totalMinutes * 100
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 5) {
                Circle()
                    .fill(segment.color)
                    .frame(width: 8, height: 8)

                Text(segment.label)
                    .font(.caption.weight(.semibold))
                    .foregroundColor(.gray)
            }

            Text("\(Int(percent)) %")
                .font(.subheadline.bold())
                .foregroundColor(.white)
        }
    }
}
