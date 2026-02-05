import SwiftUI
import Charts


// -----------------------------------------------------------
// MARK: - MAIN VIEW
// -----------------------------------------------------------

struct ContentView: View {

    @ObservedObject var healthManager: HealthManager

    // Navigation semaine
    @State private var weekOffset: Int = 0
    @State private var previousWeekData: [DailyRunData] = []

    // Séance sélectionnée (navigation)
    @State private var selectedSession: DailyRunData?

    var body: some View {

        // ⬅️ OBLIGATOIRE pour navigationDestination
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

                    // 📊 Graphe cliquable
                    WeekChartView(
                        weeklyData: healthManager.weeklyData,
                        onSelect: { session in
                            selectedSession = session
                        }
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

            // 🎯 Navigation vers le détail séance
            .navigationDestination(item: $selectedSession) { session in
                SessionDetailView(session: session)
            }
        }
    }
}

// -----------------------------------------------------------
// MARK: - WEEK DATA LOADING
// -----------------------------------------------------------

extension ContentView {

    func loadWeekData() {
        healthManager.requestAuthorization()
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

// -----------------------------------------------------------
// MARK: - WEEK HEADER
// -----------------------------------------------------------

struct WeekHeaderView: View {
    let weekOffset: Int
    let weekRangeText: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            
            HStack(spacing: 10) {
                Text("🏃‍♀️")
                    .font(.system(size: 34))
                Text("Course – Semaine")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }
            .padding(.horizontal)

            if let text = weekRangeText {
                Text(text)
                    .font(.headline.weight(.semibold))
                    .foregroundColor(.gray)
                    .padding(.horizontal)
                    .padding(.top, -10)
            }
        }
    }
}

// -----------------------------------------------------------
// MARK: - WEEK STATS GRID
// -----------------------------------------------------------

struct WeekStatsGrid: View {
    let totalDistance: Double
    let totalElevation: Double
    let totalDuration: Double
    let sessionCount: Int

    var body: some View {
        LazyVGrid(columns: [
            GridItem(.flexible(), spacing: 14),
            GridItem(.flexible(), spacing: 14)
        ], spacing: 14) {

            StatCardCompact(title: "Distance",
                            value: "\(String(format: "%.2f", totalDistance)) km",
                            color: .blue)

            StatCardCompact(title: "Dénivelé",
                            value: "\(Int(totalElevation)) m",
                            color: .green)

            StatCardCompact(title: "Temps",
                            value: "\(Int(totalDuration)) min",
                            color: .yellow)

            StatCardCompact(title: "Séances",
                            value: "\(sessionCount)",
                            color: .orange)
        }
        .padding(.horizontal)
    }
}

// -----------------------------------------------------------
// MARK: - WEEKLY DISTANCE CHART
// -----------------------------------------------------------
struct WeekChartView: View {

    let weeklyData: [DailyRunData]
    let onSelect: (DailyRunData) -> Void

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

        // 🎯 Capture du tap
        .chartOverlay { proxy in
            GeometryReader { geo in
                Rectangle()
                    .fill(.clear)
                    .contentShape(Rectangle())
                    .onTapGesture { location in

                        // Position X dans la zone du graphe
                        let x = location.x - geo[proxy.plotAreaFrame].origin.x

                        // Conversion X → valeur
                        if let day: String = proxy.value(atX: x),
                           let session = weeklyData.first(where: { $0.dayLabel == day }) {
                            onSelect(session)
                        }
                    }
            }
        }

        .chartYAxis { AxisMarks(position: .leading) }
        .frame(height: 220)
        .padding(.horizontal)
    }
}

// -----------------------------------------------------------
// MARK: - WEEK SESSION RECAP (with HR zones)
// -----------------------------------------------------------

// -----------------------------------------------------------
// MARK: - SESSION CARD
// -----------------------------------------------------------

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
        .background(RoundedRectangle(cornerRadius: 16)
            .fill(Color.white.opacity(0.04)))
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
        statRow("Vitesse moy.",
                String(format: "%.2f km/h",
                       session.distanceKm / (session.durationMin / 60)),
                .orange)
    }

    private var pace: some View {
        let pace = session.distanceKm > 0 ? session.durationMin / session.distanceKm : 0
        return statRow("Allure",
                       String(format: "%.1f min/km", pace),
                       .orange)
    }

    private var avgHeartRate: some View {
        statRow("FC moy.",
                session.averageHeartRate > 0 ? "\(Int(session.averageHeartRate)) bpm" : "—",
                .red)
    }
    
    private var totalZoneTime: Double {
        session.z1 + session.z2 + session.z3 + session.z4 + session.z5
    }

    private var lowIntensityPercent: Double {
        guard totalZoneTime > 0 else { return 0 }
        return (session.z1 + session.z2 + session.z3) / totalZoneTime * 100
    }

    private var highIntensityPercent: Double {
        guard totalZoneTime > 0 else { return 0 }
        return (session.z4 + session.z5) / totalZoneTime * 100
    }

    private var zones: some View {
        VStack(spacing: 8) {
            VStack(spacing: 4) {
                zoneRow("Z1", session.z1, .green)
                zoneRow("Z2", session.z2, .blue)
                zoneRow("Z3", session.z3, .yellow)
                zoneRow("Z4", session.z4, .orange)
                zoneRow("Z5", session.z5, .red)
            }

            Divider().background(.white.opacity(0.1))

            intensityRow("Low intensity (Z1–Z3)",
                         lowIntensityPercent,
                         .green)

            intensityRow("High intensity (Z4–Z5)",
                         highIntensityPercent,
                         .red)
        }
    }
    private func intensityRow(_ title: String,
                              _ percent: Double,
                              _ color: Color) -> some View {
        HStack {
            Text(title)
                .foregroundColor(.white.opacity(0.8))
            Spacer()
            Text(String(format: "%.0f %%", percent))
                .foregroundColor(color)
                .font(.subheadline.bold())
        }
    }



    // -------------------------------------------------------
    // MARK: - Reusable Rows
    // -------------------------------------------------------

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
    private func zoneRow(_ name: String, _ value: Double, _ color: Color) -> some View {
        if value > 0 {
            HStack {
                Text("\(name) :")
                    .foregroundColor(.gray)
                Spacer()
                Text(String(format: "%.1f min", value))
                    .foregroundColor(color)
            }
        }
    }
}

struct SessionDetailView: View {
    let session: DailyRunData

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {

                SessionMetricsGrid(session: session)

                HRZoneBarChart(session: session)

                // ❤️ FC dans le temps
                if !session.heartRateTimeline.isEmpty {
                    HeartRateTimelineChart(
                        samples: session.heartRateTimeline
                    )
                }
            }
            .padding()
        }
        .background(Color.black.ignoresSafeArea())
        .navigationTitle(session.dayLabel)
        .navigationBarTitleDisplayMode(.inline)
    }
}

// -----------------------------------------------------------
// MARK: - WEEK COMPARISON VIEW
// -----------------------------------------------------------

struct WeekComparisonView: View {
    let currentWeekData: [DailyRunData]
    let previousWeekData: [DailyRunData]

    private func diffColor(_ v: Double) -> Color {
        v > 0 ? .green : (v < 0 ? .red : .gray)
    }

    var body: some View {
        let curr = (
            dist: currentWeekData.map(\.distanceKm).reduce(0, +),
            dur: currentWeekData.map(\.durationMin).reduce(0, +),
            elev: currentWeekData.map(\.elevationGainM).reduce(0, +),
            sess: currentWeekData.count
        )

        let prev = (
            dist: previousWeekData.map(\.distanceKm).reduce(0, +),
            dur: previousWeekData.map(\.durationMin).reduce(0, +),
            elev: previousWeekData.map(\.elevationGainM).reduce(0, +),
            sess: previousWeekData.count
        )

        VStack(alignment: .leading, spacing: 16) {

            Text("Comparé à la semaine dernière")
                .font(.title3.bold())
                .foregroundColor(.white)
                .padding(.leading, 8)

            comparisonRow("Distance",
                          delta: curr.dist - prev.dist,
                          unit: " km")

            comparisonRow("Temps total",
                          delta: curr.dur - prev.dur,
                          unit: " min")

            comparisonRow("Dénivelé",
                          delta: curr.elev - prev.elev,
                          unit: " m")

            comparisonRow("Séances",
                          delta: Double(curr.sess - prev.sess),
                          unit: "")
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.04))
        )
        .padding(.horizontal)
        .padding(.bottom, 40)
    }

    private func comparisonRow(_ title: String, delta: Double, unit: String) -> some View {
        HStack {
            Text(title).foregroundColor(.gray)
            Spacer()
            Text(String(format: "%+.1f\(unit)", delta))
                .foregroundColor(diffColor(delta))
        }
        .font(.headline)
    }
}

// -----------------------------------------------------------
// MARK: - HR ZONE CHART VIEW
// -----------------------------------------------------------

struct WeekHRZoneChartView: View {
    let sessions: [SessionZoneBreakdown]

    private var totals: [(zone: String, value: Double, color: Color)] {
        [
            ("Z1", sessions.map(\.z1).reduce(0,+), .green),
            ("Z2", sessions.map(\.z2).reduce(0,+), .blue),
            ("Z3", sessions.map(\.z3).reduce(0,+), .yellow),
            ("Z4", sessions.map(\.z4).reduce(0,+), .orange),
            ("Z5", sessions.map(\.z5).reduce(0,+), .red)
        ]
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {

            Text("Zones cardiaques (temps total semaine)")
                .font(.title3.bold())
                .foregroundColor(.white)
                .padding(.leading, 8)

            if sessions.isEmpty {
                Text("Aucune donnée cette semaine")
                    .foregroundColor(.gray)
                    .padding()
            } else {
                Chart {
                    ForEach(totals, id: \.zone) { item in
                        BarMark(
                            x: .value("Zone", item.zone),
                            y: .value("Minutes", item.value)
                        )
                        .foregroundStyle(item.color)
                    }
                }
                .frame(height: 240)   // ← indispensable
                .padding(.horizontal)
            }
        }
    }
}

// -----------------------------------------------------------
// MARK: - COMPACT STAT CARD
// -----------------------------------------------------------

struct StatCardCompact: View {
    let title: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: "figure.run.circle.fill")
                    .foregroundColor(color)
                    .font(.system(size: 18))
                Text(title.uppercased())
                    .font(.caption.weight(.semibold))
                    .foregroundColor(.gray)
            }
            Text(value)
                .font(.system(size: 22, weight: .bold, design: .rounded))
                .foregroundColor(color)
                .padding(.top, 4)
        }
        .padding()
        .frame(maxWidth: .infinity, minHeight: 100, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.05))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.08))
                )
        )
    }
}

// -----------------------------------------------------------
// MARK: - HELPERS
// -----------------------------------------------------------
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

// -------------------------------
// Block pour ecire les donn&es dans des blocks
// -------------------------------
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

            MetricBlock(title: "Distance",
                        value: String(format: "%.2f km", session.distanceKm),
                        color: .blue)

            MetricBlock(title: "Durée",
                        value: "\(Int(session.durationMin)) min",
                        color: .yellow)

            MetricBlock(title: "Dénivelé",
                        value: "\(Int(session.elevationGainM)) m",
                        color: .green)

            MetricBlock(title: "FC moy.",
                        value: session.averageHeartRate > 0
                              ? "\(Int(session.averageHeartRate)) bpm"
                              : "—",
                        color: .red)
        }
    }
}

struct HRZoneBarChart: View {
    let session: DailyRunData

    private var totalZoneTime: Double {
        session.z1 + session.z2 + session.z3 + session.z4 + session.z5
    }

    private var lowIntensityPct: Double {
        guard totalZoneTime > 0 else { return 0 }
        return (session.z1 + session.z2 + session.z3) / totalZoneTime * 100
    }

    private var highIntensityPct: Double {
        guard totalZoneTime > 0 else { return 0 }
        return (session.z4 + session.z5) / totalZoneTime * 100
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {

            Text("Zones cardiaques")
                .font(.headline)
                .foregroundColor(.white)

            Chart {
                BarMark(x: .value("Zone", "Z1"), y: .value("Min", session.z1))
                    .foregroundStyle(.green)
                BarMark(x: .value("Zone", "Z2"), y: .value("Min", session.z2))
                    .foregroundStyle(.blue)
                BarMark(x: .value("Zone", "Z3"), y: .value("Min", session.z3))
                    .foregroundStyle(.yellow)
                BarMark(x: .value("Zone", "Z4"), y: .value("Min", session.z4))
                    .foregroundStyle(.orange)
                BarMark(x: .value("Zone", "Z5"), y: .value("Min", session.z5))
                    .foregroundStyle(.red)
            }
            .frame(height: 180)

            Divider().background(.white.opacity(0.1))

            // 📊 Intensité
            HStack {
                VStack(alignment: .leading) {
                    Text("Low intensity (Z1–Z3)")
                        .foregroundColor(.gray)
                    Text(String(format: "%.0f %%", lowIntensityPct))
                        .font(.headline.bold())
                        .foregroundColor(.green)
                }

                Spacer()

                VStack(alignment: .leading) {
                    Text("High intensity (Z4–Z5)")
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

func zoneColor(bpm: Double) -> Color {
    switch bpm {
    case ..<153: return .blue
    case 153..<164: return .teal
    case 164..<173: return .green
    case 174..<182: return .orange
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

                // 🔍 Bouton zoom
                Button {
                    withAnimation {
                        showFullSession.toggle()
                    }
                } label: {
                    Image(systemName: showFullSession
                          ? "minus.magnifyingglass"
                          : "plus.magnifyingglass")
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

            // ✅ SCROLL
            .chartScrollableAxes(.horizontal)

            // ✅ ZOOM LOGIQUE
            .chartXVisibleDomain(
                length: showFullSession ? fullDuration : 600
            )

            // ✅ AXE X
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
