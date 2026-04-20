import SwiftUI

struct TrainingLoadGaugeView: View {
    let sevenDayLoad: Double
    let twentyEightDayLoad: Double
    let loadRatio: Double

    private var ratioColor: Color {
        switch loadRatio {
        case ..<0.8:
            return .blue
        case 0.8...1.3:
            return .green
        case 1.3...1.5:
            return .orange
        default:
            return .red
        }
    }

    private var statusText: String {
        switch loadRatio {
        case ..<0.8:
            return "Charge basse"
        case 0.8...1.3:
            return "Charge stable"
        case 1.3...1.5:
            return "Hausse marquée"
        default:
            return "Pic de charge"
        }
    }

    private var progress: Double {
        min(max(loadRatio / 1.8, 0), 1)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Charge d'entraînement")
                        .font(.headline.bold())
                        .foregroundColor(.white)

                    Text(statusText)
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(ratioColor)
                }

                Spacer()

                Text(String(format: "%.2f", loadRatio))
                    .font(.system(size: 32, weight: .bold, design: .rounded))
                    .foregroundColor(ratioColor)
            }

            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.white.opacity(0.10))

                    Capsule()
                        .fill(ratioColor)
                        .frame(width: max(8, geometry.size.width * progress))
                }
            }
            .frame(height: 12)

            HStack {
                LoadMetric(title: "7 jours", value: "\(Int(sevenDayLoad)) km", color: .yellow)
                Spacer()
                LoadMetric(title: "28 jours", value: "\(Int(twentyEightDayLoad)) km", color: .orange)
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

private struct LoadMetric: View {
    let title: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title.uppercased())
                .font(.caption.weight(.semibold))
                .foregroundColor(.gray)

            Text(value)
                .font(.headline.bold())
                .foregroundColor(color)
        }
    }
}
