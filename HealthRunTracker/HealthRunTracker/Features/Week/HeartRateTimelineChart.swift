import Charts
import SwiftUI

func zoneColor(bpm: Double) -> Color {
    switch bpm {
    case ..<145: return .blue
    case 145..<159: return .teal
    case 159..<173: return .green
    case 173..<186: return .orange
    default: return .red
    }
}

struct HeartRateTimelineChart: View {
    let samples: [HeartRateSample]
    @State private var showFullSession = false

    private var fullDuration: Double {
        samples.last?.timeOffset ?? 600
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Fréquence cardiaque")
                    .font(.headline)
                    .foregroundColor(.white)

                Spacer()

                Button {
                    withAnimation {
                        showFullSession.toggle()
                    }
                } label: {
                    Image(systemName: showFullSession ? "minus.magnifyingglass" : "plus.magnifyingglass")
                        .foregroundColor(.blue)
                }
            }

            Chart {
                ForEach(samples) { sample in
                    LineMark(
                        x: .value("Temps", sample.timeOffset),
                        y: .value("BPM", sample.bpm)
                    )
                    .foregroundStyle(zoneColor(bpm: sample.bpm))
                    .interpolationMethod(.linear)
                }
            }
            .frame(height: 180)
            .chartScrollableAxes(.horizontal)
            .chartXVisibleDomain(length: showFullSession ? fullDuration : 600)
            .chartXAxis {
                AxisMarks(values: .stride(by: 300)) { value in
                    if let seconds = value.as(Double.self) {
                        AxisValueLabel("\(Int(seconds / 60)) min")
                    }
                }
            }
            .chartYAxis {
                AxisMarks(position: .leading)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.05))
        )
    }
}
