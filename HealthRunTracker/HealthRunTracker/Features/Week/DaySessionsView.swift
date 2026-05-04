import SwiftUI

struct DaySessionsView: View {
    let dayLabel: String
    let sessions: [DailyRunData]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("\(sessions.count) séances")
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundColor(.white.opacity(0.65))
                    .frame(maxWidth: .infinity, alignment: .leading)

                ForEach(sortedSessions) { session in
                    NavigationLink {
                        SessionDetailView(session: session)
                    } label: {
                        DaySessionRow(session: session)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding()
        }
        .background(Color.black.ignoresSafeArea())
        .navigationTitle(dayLabel)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var sortedSessions: [DailyRunData] {
        sessions.sorted { $0.date < $1.date }
    }
}

private struct DaySessionRow: View {
    let session: DailyRunData

    private var timeText: String {
        session.date.formatted(
            Date.FormatStyle()
                .hour(.twoDigits(amPM: .omitted))
                .minute(.twoDigits)
        )
    }

    private var typeText: String {
        if let sessionType = session.sessionType?.trimmingCharacters(in: .whitespacesAndNewlines),
           !sessionType.isEmpty {
            return sessionType.capitalized
        }

        if let predicted = session.predictedSessionType?.trimmingCharacters(in: .whitespacesAndNewlines),
           !predicted.isEmpty {
            return "Prédiction: \(predicted)"
        }

        return "Catégorie à confirmer"
    }

    var body: some View {
        HStack(alignment: .center, spacing: 14) {
            VStack(alignment: .leading, spacing: 6) {
                Text(timeText)
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text(typeText)
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundColor(.white.opacity(0.58))
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 6) {
                Text(String(format: "%.2f km", session.distanceKm))
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundColor(.blue)

                Text("\(Int(session.durationMin)) min")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundColor(.yellow.opacity(0.9))
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 13, weight: .bold))
                .foregroundColor(.white.opacity(0.28))
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 22)
                .fill(Color.white.opacity(0.05))
                .overlay(
                    RoundedRectangle(cornerRadius: 22)
                        .stroke(Color.white.opacity(0.06), lineWidth: 1)
                )
        )
    }
}
