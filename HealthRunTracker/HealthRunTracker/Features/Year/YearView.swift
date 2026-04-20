import SwiftUI
import Charts

struct YearView: View {
    @ObservedObject var healthManager: HealthManager
    @State private var yearOffset: Int = 0 // 0 = année actuelle, -1 = année précédente
    @State private var weeklyDistanceData: [WeeklyDistanceData] = []
    @State private var records: [RunRecord] = []
    @State private var selectedMonth: Int = Calendar.current.component(.month, from: Date())
    @State private var compareOffset: Int? = nil

    private var currentYear: Int {
        let calendar = Calendar.current
        return calendar.component(.year, from: Date()) + yearOffset
    }

    var body: some View {
        ScrollView {
            YearContent(
                healthManager: healthManager,
                yearOffset: $yearOffset,
                weeklyDistanceData: $weeklyDistanceData,
                records: $records,
                selectedMonth: $selectedMonth,
                compareOffset: $compareOffset,
                currentYear: currentYear,
                loadYearData: loadYearData
            )
        }
        .background(Color.black.ignoresSafeArea())
        .onAppear {
            loadYearData()
            healthManager.computeRecords { rec in
                DispatchQueue.main.async {
                    self.records = rec
                }
            }
        }
        .gesture(
            DragGesture()
                .onEnded { value in
                    if value.translation.width < -50 {
                        withAnimation { yearOffset -= 1 }
                        loadYearData()
                    } else if value.translation.width > 50 {
                        if yearOffset < 0 {
                            withAnimation { yearOffset += 1 }
                            loadYearData()
                        }
                    }
                }
        )
    }

struct YearContent: View {
    @ObservedObject var healthManager: HealthManager
    @Binding var yearOffset: Int
    @Binding var weeklyDistanceData: [WeeklyDistanceData]
    @Binding var records: [RunRecord]
    @Binding var selectedMonth: Int
    @Binding var compareOffset: Int?
    @State private var compareWeeklyData: [WeeklyDistanceData] = []
    let currentYear: Int
    let loadYearData: () -> Void

    private func weekToMonthLabel(_ week: Int) -> String {
        let calendar = Calendar(identifier: .iso8601)
        var components = DateComponents()
        components.weekOfYear = week
        components.yearForWeekOfYear = currentYear

        guard let date = calendar.date(from: components) else { return "" }

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "fr_FR")
        formatter.dateFormat = "LLL"

        return formatter.string(from: date)
    }
    
    var body: some View {
        VStack(spacing: 28) {
            YearHeader(currentYear: currentYear)

            if healthManager.yearlyData.isEmpty {
                Text("Chargement des données Santé…")
                    .foregroundColor(.gray)
                    .padding()
            } else {
                // ====== Statistiques globales ======
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 14) {
                    StatCardCompact(title: "Distance", value: "\(Int(totalDistance())) km", color: .blue)
                    StatCardCompact(title: "Dénivelé", value: "\(Int(totalElevation())) m", color: .green)
                    StatCardCompact(title: "Temps", value: "\(Int(totalDuration())) min", color: .yellow)
                    StatCardCompact(title: "Séances", value: "\(healthManager.yearlySessionCount)", color: .orange)
                }
                .padding(.horizontal)

                // ====== Records personnels ======
                VStack(alignment: .leading, spacing: 12) {
                    Text("🏅 Records personnels")
                        .font(.title2.bold())
                        .foregroundColor(.white)
                        .padding(.leading, 8)

                    if records.isEmpty {
                        Text("Chargement des records…")
                            .foregroundColor(.gray)
                            .padding(.leading, 12)
                    } else {
                        ForEach(records, id: \.distanceTarget) { rec in
                            HStack {
                                Text(labelFor(rec.distanceTarget))
                                    .foregroundColor(.white)
                                    .frame(width: 120, alignment: .leading)

                                Text(timeString(rec.bestTime))
                                    .foregroundColor(.yellow)

                                Spacer()

                                Text("(\(rec.yearAchieved))")
                                    .foregroundColor(.gray)
                            }
                            .padding(.horizontal)
                        }
                    }
                }
                .padding(.horizontal)

                // ====== Autres Records annuels ======
                VStack(alignment: .leading, spacing: 12) {
                    Text("📈 Autres records annuels")
                        .font(.title3.bold())
                        .foregroundColor(.white)
                        .padding(.leading, 8)

                    HStack {
                        Text("Sortie la plus longue")
                            .foregroundColor(.white)
                            .frame(width: 180, alignment: .leading)
                        Text(timeString(healthManager.longestRunDuration))
                            .foregroundColor(.yellow)
                        Spacer()
                    }
                    .padding(.horizontal)

                    HStack {
                        Text("Plus gros D+")
                            .foregroundColor(.white)
                            .frame(width: 180, alignment: .leading)
                        Text("\(Int(healthManager.biggestRunElevation)) m")
                            .foregroundColor(.green)
                        Spacer()
                    }
                    .padding(.horizontal)

                    HStack {
                        Text("Plus longue distance")
                            .foregroundColor(.white)
                            .frame(width: 180, alignment: .leading)
                        Text("\(Int(healthManager.longestRunDistance)) km")
                            .foregroundColor(.cyan)
                        Spacer()
                    }
                    .padding(.horizontal)
                }
                .padding(.horizontal)

                // ====== Graphique mensuel ======
                VStack(alignment: .leading, spacing: 10) {
                    Text("Distance totale par mois")
                        .font(.headline.bold())
                        .foregroundColor(.white)
                        .padding(.leading, 8)

                    Chart(healthManager.yearlyData) { month in
                        let monthMonth = month.month
                        BarMark(
                            x: .value("Mois", month.monthLabel),
                            y: .value("Distance (km)", month.distanceKm)
                        )
                        .foregroundStyle(
                            LinearGradient(
                                colors: [.blue.opacity(0.9), .blue.opacity(0.3)],
                                startPoint: .top, endPoint: .bottom
                            )
                        )
                        .cornerRadius(6)
                    }
                    .frame(height: 250)
                    .padding(.horizontal)
                    .chartOverlay { proxy in
                        GeometryReader { geo in
                            Rectangle()
                                .fill(Color.clear)
                                .contentShape(Rectangle())
                                .onTapGesture { location in
                                    let xPosition = location.x - geo[proxy.plotAreaFrame].origin.x
                                    if let monthLabel: String = proxy.value(atX: xPosition) {
                                        if let tapped = healthManager.yearlyData.first(where: { $0.monthLabel == monthLabel }) {
                                            selectedMonth = tapped.month
                                        }
                                    }
                                }
                        }
                    }

                    // ====== Meilleur mois ======
                    if let best = healthManager.yearlyData.max(by: { $0.distanceKm < $1.distanceKm }) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("🏆 Meilleur mois")
                                .font(.headline.bold())
                                .foregroundColor(.white)
                                .padding(.leading, 8)

                            HStack {
                                Text("\(best.monthLabel) \(currentYear)")
                                    .foregroundColor(.white)
                                    .frame(width: 160, alignment: .leading)
                                Text("\(Int(best.distanceKm)) km")
                                    .foregroundColor(.blue)
                                Spacer()
                            }
                            .padding(.horizontal)

                            HStack {
                                Text("Temps total")
                                    .foregroundColor(.white)
                                    .frame(width: 160, alignment: .leading)
                                Text(timeString(best.durationMin * 60))
                                    .foregroundColor(.yellow)
                                Spacer()
                            }
                            .padding(.horizontal)
                        }
                        .padding(.bottom, 20)
                    }
                }

                // ====== Heatmap annuel ======
                VStack(alignment: .leading, spacing: 12) {
                    Text("📅 Heatmap – Régularité")
                        .font(.headline.bold())
                        .foregroundColor(.white)
                        .padding(.leading, 8)

                    HeatmapCalendar(distances: healthManager.dailyDistances, year: currentYear, currentMonth: $selectedMonth)
                        .frame(height: 320)
                        .padding(.horizontal)
                    
                    // ====== Total du mois sélectionné ======
                    if let monthData = healthManager.yearlyData.first(where: { $0.month == selectedMonth }) {
                        HStack {
                            Text("Total \(monthData.monthLabel.capitalized)")
                                .foregroundColor(.white)
                            Spacer()
                            Text("\(Int(monthData.distanceKm)) km")
                                .foregroundColor(.blue)
                                .bold()
                        }
                        .padding(.horizontal)
                    }
                }

                // ====== Charge d’entraînement ======
                VStack(alignment: .leading, spacing: 10) {
                    Text("🧠 Charge d’entraînement")
                        .font(.headline.bold())
                        .foregroundColor(.white)
                        .padding(.leading, 8)

                    HStack {
                        Text("Sur 7 jours")
                            .foregroundColor(.gray)
                        Spacer()
                        Text("\(String(format: "%.1f", healthManager.sevenDayLoad)) km")
                            .foregroundColor(.yellow)
                    }
                    .padding(.horizontal)

                    HStack {
                        Text("Sur 28 jours")
                            .foregroundColor(.gray)
                        Spacer()
                        Text("\(String(format: "%.1f", healthManager.twentyEightDayLoad)) km")
                            .foregroundColor(.orange)
                    }
                    .padding(.horizontal)

                    HStack {
                        Text("Ratio 7/28")
                            .foregroundColor(.gray)
                        Spacer()
                        Text(String(format: "%.2f", healthManager.loadRatio))
                            .foregroundColor(healthManager.loadRatio > 1.5 ? .red : .green)
                    }
                    .padding(.horizontal)

                    if healthManager.loadRatio > 1.5 {
                        Text("⚠️ Charge élevée → Risque de blessure")
                            .foregroundColor(.red)
                            .padding(.leading, 12)
                    }
                }
                .padding(.horizontal)
                .padding(.bottom, 10)

                // ====== Graphique hebdomadaire ======
                VStack(alignment: .leading, spacing: 10) {
                    Text("Distance totale courue par semaine")
                        .font(.headline.bold())
                        .foregroundColor(.white)
                        .padding(.leading, 8)

                    if weeklyDistanceData.isEmpty {
                        ProgressView("Chargement du graphique…")
                            .foregroundColor(.gray)
                            .padding()
                    } else {
                        Chart(weeklyDistanceData) { point in
                            LineMark(
                                x: .value("Semaine", point.weekNumber),
                                y: .value("Distance (km)", point.distanceKm)
                            )
                            .interpolationMethod(.catmullRom)
                            .foregroundStyle(.blue)
                            .lineStyle(StrokeStyle(lineWidth: 3))

                            PointMark(
                                x: .value("Semaine", point.weekNumber),
                                y: .value("Distance (km)", point.distanceKm)
                            )
                            .symbol(.circle)
                            .symbolSize(50)
                            .foregroundStyle(.blue)
                        }
                        .chartYAxisLabel("Distance (km)")
                        .chartXAxis {
                            AxisMarks(preset: .aligned, values: .stride(by: 4)) { val in
                                AxisGridLine()
                                AxisValueLabel {
                                    if let v = val.as(Int.self) {
                                        Text(weekToMonthLabel(v))
                                    }
                                }
                            }
                        }
                        .animation(.easeInOut(duration: 0.6), value: weeklyDistanceData)
                        .frame(height: 260)
                        .padding(.horizontal)
                    }
                }
                .padding(.bottom, 40)

            }
        }
        .padding(.vertical, 12)
    }

    // MARK: - Helpers
    private func totalDistance() -> Double {
        healthManager.yearlyData.map(\.distanceKm).reduce(0, +)
    }

    private func totalDuration() -> Double {
        healthManager.yearlyData.map(\.durationMin).reduce(0, +)
    }

    private func totalElevation() -> Double {
        healthManager.yearlyData.map(\.elevationGainM).reduce(0, +)
    }

    private func labelFor(_ dist: Double) -> String {
        switch dist {
        case 10.0: return "10 km"
        case 21.1: return "Semi"
        case 42.195: return "Marathon"
        default: return "\(dist) km"
        }
    }

    private func timeString(_ t: TimeInterval) -> String {
        let h = Int(t) / 3600
        let m = (Int(t) % 3600) / 60
        let s = Int(t) % 60
        return h > 0 ? "\(h)h \(m)m \(s)s" : "\(m)m \(s)s"
    }

    private func cumulative(from weeks: [WeeklyDistanceData]) -> [WeeklyDistanceData] {
        var total: Double = 0
        return weeks.map { week in
            total += week.distanceKm
            return WeeklyDistanceData(weekNumber: week.weekNumber, distanceKm: total)
        }
    }

}

    // MARK: - Helpers
    private func loadYearData() {
        healthManager.fetchYearlyRunningData(for: yearOffset)
        healthManager.computeWeeklyDistanceData(for: yearOffset) { data in
            self.weeklyDistanceData = data
        }
    }

    private func totalDistance() -> Double {
        healthManager.yearlyData.map(\.distanceKm).reduce(0, +)
    }

    private func totalDuration() -> Double {
        healthManager.yearlyData.map(\.durationMin).reduce(0, +)
    }

    private func totalElevation() -> Double {
        healthManager.yearlyData.map(\.elevationGainM).reduce(0, +)
    }

    private func labelFor(_ dist: Double) -> String {
        switch dist {
        case 10.0: return "10 km"
        case 21.1: return "Semi"
        case 42.195: return "Marathon"
        default: return "\(dist) km"
        }
    }

    private func timeString(_ t: TimeInterval) -> String {
        let h = Int(t) / 3600
        let m = (Int(t) % 3600) / 60
        let s = Int(t) % 60
        return h > 0 ? "\(h)h \(m)m \(s)s" : "\(m)m \(s)s"
    }
}

struct YearHeader: View {
    let currentYear: Int

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "calendar")
                .font(.system(size: 32))
            Text("Course – \(currentYear)")
                .font(.system(size: 34, weight: .bold, design: .rounded))
        }
        .foregroundColor(.white)
        .padding(.top, 8)
        .padding(.horizontal)
    }
}

import SwiftUI

struct HeatmapCalendar: View {
    let distances: [Date: Double]
    let year: Int

    private let calendar = Calendar.current
    @Binding var currentMonth: Int

    @State private var selectedDate: Date? = nil
    @State private var selectedDistance: Double? = nil

    init(distances: [Date: Double], year: Int, currentMonth: Binding<Int>) {
        self.distances = distances
        self.year = year
        self._currentMonth = currentMonth
    }

    private var daysInMonth: [Date] {
        var components = DateComponents(year: year, month: currentMonth)
        let monthDate = calendar.date(from: components)!
        let range = calendar.range(of: .day, in: .month, for: monthDate)!

        return range.compactMap { day in
            components.day = day
            return calendar.date(from: components)
        }
    }

    /// Décalage de la première colonne (L = 0 … D = 6)
    private var firstWeekdayOffset: Int {
        guard let firstDay = daysInMonth.first else { return 0 }
        let weekday = calendar.component(.weekday, from: firstDay) // 1 = dimanche
        return (weekday + 5) % 7 // -> lundi = 0
    }

    private func color(for distance: Double) -> Color {
        switch distance {
        case 0:
            return Color.gray.opacity(0.15)
        case 0..<5:
            return Color.blue.opacity(0.3)
        case 5..<10:
            return Color.blue.opacity(0.55)
        case 10..<20:
            return Color.green.opacity(0.75)
        default:
            return Color.green.opacity(1.0)
        }
    }

    var body: some View {
        // ⚠️ on prépare les valeurs AVANT le VStack,
        // puis on fait un `return`
        let offset = firstWeekdayOffset
        let totalCells = daysInMonth.count + offset
        let rows = Int(ceil(Double(totalCells) / 7.0))

        return VStack(spacing: 12) {
            // Navigation mois
            HStack {
                Button(action: { if currentMonth > 1 { currentMonth -= 1 } }) {
                    Image(systemName: "chevron.left")
                        .foregroundColor(.white)
                }
                Spacer()
                Text(calendar.monthSymbols[currentMonth - 1])
                    .font(.title3.bold())
                    .foregroundColor(.white)
                Spacer()
                Button(action: { if currentMonth < 12 { currentMonth += 1 } }) {
                    Image(systemName: "chevron.right")
                        .foregroundColor(.white)
                }
            }
            .padding(.horizontal)

            // Jours de la semaine
            HStack {
                ForEach(["L","M","M","J","V","S","D"], id: \.self) { d in
                    Text(d)
                        .font(.caption)
                        .frame(maxWidth: .infinity)
                        .foregroundColor(.gray)
                }
            }

            // Grille
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 7), spacing: 8) {
                // Cases vides (début du mois)
                ForEach(0..<offset, id: \.self) { _ in
                    Circle()
                        .fill(Color.clear)
                        .frame(width: 18, height: 18)
                }

                // Jours réels
                ForEach(daysInMonth, id: \.self) { date in
                    let key = calendar.startOfDay(for: date)
                    let dist = distances[key, default: 0]

                    Circle()
                        .fill(color(for: dist))
                        .frame(width: 18, height: 18)
                        .onTapGesture {
                            selectedDate = date
                            selectedDistance = dist
                        }
                }

                // Cases vides (fin du mois pour compléter grille)
                let remaining = (7 - ((daysInMonth.count + offset) % 7)) % 7
                ForEach(0..<remaining, id: \.self) { _ in
                    Circle()
                        .fill(Color.clear)
                        .frame(width: 18, height: 18)
                }
            }

            if let d = selectedDate, let km = selectedDistance {
                Text("\(calendar.component(.day, from: d))/\(currentMonth) : \(String(format: "%.1f", km)) km")
                    .font(.caption)
                    .foregroundColor(.white)
                    .padding(.top, 4)
            }
        }
    }
}
