import Charts
import SwiftUI

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
                    .foregroundStyle(HeartRateZones.color(for: sample.bpm))
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
