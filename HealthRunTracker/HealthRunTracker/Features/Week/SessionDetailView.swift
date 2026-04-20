import SwiftUI

struct SessionDetailView: View {
    let session: DailyRunData

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                SessionMetricsGrid(session: session)
                HRZoneBarChart(session: session)

                if !session.heartRateTimeline.isEmpty {
                    HeartRateTimelineChart(samples: session.heartRateTimeline)
                }
            }
            .padding()
        }
        .background(Color.black.ignoresSafeArea())
        .navigationTitle(session.dayLabel)
        .navigationBarTitleDisplayMode(.inline)
    }
}
