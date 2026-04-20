import SwiftUI

struct ContentView: View {
    @ObservedObject var healthManager: HealthManager

    @State private var weekOffset: Int = 0
    @State private var previousWeekData: [DailyRunData] = []
    @State private var selectedSession: DailyRunData?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    WeekHeaderView(
                        weekOffset: weekOffset,
                        weekRangeText: currentWeekRangeText()
                    )

                    WeekStatsGrid(
                        totalDistance: totalDistance(),
                        totalElevation: totalElevation(),
                        totalDuration: totalDuration(),
                        sessionCount: healthManager.weeklyData.count
                    )

                    TrainingLoadGaugeView(
                        sevenDayLoad: healthManager.sevenDayLoad,
                        twentyEightDayLoad: healthManager.twentyEightDayLoad,
                        loadRatio: healthManager.loadRatio
                    )

                    WeekChartView(
                        weeklyData: healthManager.weeklyData,
                        onSelect: { session in
                            selectedSession = session
                        }
                    )

                    WeeklyIntensitySummaryView(
                        sessions: healthManager.weeklyData
                    )

                    PaceHeartRateScatterView(
                        sessions: healthManager.weeklyData
                    )

                    WeekHRZoneChartView(
                        sessions: healthManager.weeklyZoneBreakdown
                    )

                    WeekComparisonView(
                        currentWeekData: healthManager.weeklyData,
                        previousWeekData: previousWeekData
                    )
                }
            }
            .background(Color.black.ignoresSafeArea())
            .onAppear(perform: loadWeekData)
            .gesture(weekSwipeGesture)
            .navigationDestination(item: $selectedSession) { session in
                SessionDetailView(session: session)
            }
        }
    }
}

extension ContentView {
    func loadWeekData() {
        reloadWeek()
    }

    func reloadWeek() {
        healthManager.fetchWeeklyRunningData(for: weekOffset)

        healthManager.fetchWeeklyRuns(for: weekOffset - 1) { runs in
            previousWeekData = runs
        }
    }

    var weekSwipeGesture: some Gesture {
        DragGesture().onEnded { value in
            if value.translation.width < -50 {
                withAnimation { weekOffset -= 1 }
                reloadWeek()
            } else if value.translation.width > 50, weekOffset < 0 {
                withAnimation { weekOffset += 1 }
                reloadWeek()
            }
        }
    }
}

extension ContentView {
    func totalDistance() -> Double {
        healthManager.weeklyData.map(\.distanceKm).reduce(0, +)
    }

    func totalDuration() -> Double {
        healthManager.weeklyData.map(\.durationMin).reduce(0, +)
    }

    func totalElevation() -> Double {
        healthManager.weeklyData.map(\.elevationGainM).reduce(0, +)
    }

    func currentWeekRangeText() -> String? {
        let calendar = Calendar.current
        guard let currentWeek = calendar.date(byAdding: .weekOfYear, value: weekOffset, to: Date()),
              let interval = calendar.dateInterval(of: .weekOfYear, for: currentWeek)
        else { return nil }

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "fr_FR")
        formatter.dateFormat = "d MMM"

        let start = formatter.string(from: interval.start)
        let end = formatter.string(from: interval.end.addingTimeInterval(-86400))

        return "Semaine du \(start) au \(end)"
    }
}
