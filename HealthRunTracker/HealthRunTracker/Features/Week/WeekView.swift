import SwiftUI

struct ContentView: View {
    @ObservedObject var healthManager: HealthManager

    @State private var weekOffset: Int = 0
    @State private var previousWeekData: [DailyRunData] = []
    @State private var selectedSession: DailyRunData?
    @State private var selectedDayRoute: DaySessionsRoute?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    WeekHeaderView(
                        weekOffset: weekOffset,
                        weekRangeText: currentWeekRangeText()
                    )

                    if healthManager.isLoadingWeeklyData {
                        HStack(spacing: 10) {
                            ProgressView()
                                .tint(.white)
                            Text(
                                healthManager.weeklyData.isEmpty
                                ? "Chargement rapide des séances..."
                                : "Mise à jour des zones cardiaques..."
                            )
                            .font(.system(size: 14, weight: .semibold, design: .rounded))
                            .foregroundColor(.white.opacity(0.82))
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(
                            Capsule()
                                .fill(Color.white.opacity(0.08))
                                .overlay(
                                    Capsule()
                                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                                )
                        )
                    }

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
                        onSelect: { sessions in
                            if sessions.count == 1, let session = sessions.first {
                                selectedSession = session
                            } else if let firstSession = sessions.first {
                                selectedDayRoute = DaySessionsRoute(
                                    dayLabel: firstSession.dayLabel,
                                    sessions: sessions
                                )
                            }
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
            .navigationDestination(item: $selectedDayRoute) { route in
                DaySessionsView(
                    dayLabel: route.dayLabel,
                    sessions: route.sessions
                )
            }
        }
    }
}

private struct DaySessionsRoute: Identifiable, Hashable {
    let dayLabel: String
    let sessions: [DailyRunData]

    var id: String {
        let sessionIDs = sessions.map(\.id.uuidString).joined(separator: "-")
        return "\(dayLabel)-\(sessionIDs)"
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
