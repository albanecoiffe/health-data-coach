import SwiftUI

struct DaySessionsView: View {
    @EnvironmentObject var healthManager: HealthManager
    let dayLabel: String
    let sessions: [DailyRunData]
    
    @State private var isMerging = false
    @State private var mergeMessage = ""
    @State private var showMergeConfirmation = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("\(currentSessions.count) séances")
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundColor(.white.opacity(0.65))
                    .frame(maxWidth: .infinity, alignment: .leading)

                if canMergeCurrentSessions {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Si ces 2 séances correspondent en réalité à une seule sortie interrompue, vous pouvez les fusionner.")
                            .font(.system(size: 14, weight: .medium, design: .rounded))
                            .foregroundColor(.white.opacity(0.6))

                        Button {
                            showMergeConfirmation = true
                        } label: {
                            HStack(spacing: 10) {
                                if isMerging {
                                    ProgressView()
                                        .tint(.black)
                                } else {
                                    Image(systemName: "arrow.triangle.merge")
                                }

                                Text(isMerging ? "Fusion en cours..." : "Fusionner les 2 séances")
                                    .font(.system(size: 16, weight: .bold, design: .rounded))
                            }
                            .foregroundColor(.black)
                            .padding(.horizontal, 18)
                            .padding(.vertical, 14)
                            .background(
                                Capsule()
                                    .fill(Color.yellow)
                            )
                        }
                        .buttonStyle(.plain)
                        .disabled(isMerging)

                        if !mergeMessage.isEmpty {
                            Text(mergeMessage)
                                .font(.footnote.weight(.semibold))
                                .foregroundColor(mergeMessage == "Séances fusionnées" ? .green : .red)
                        }
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

                ForEach(currentSessions) { session in
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
        .alert("Fusionner les séances ?", isPresented: $showMergeConfirmation) {
            Button("Annuler", role: .cancel) {}
            Button("Fusionner") {
                mergeCurrentSessions()
            }
        } message: {
            Text("Cette action est utile si vous avez interrompu puis repris la même sortie. Si ce sont vraiment 2 entraînements différents, ne les fusionnez pas.")
        }
    }

    private var currentSessions: [DailyRunData] {
        guard let referenceDate = sessions.first?.date else {
            return sessions.sorted { $0.date < $1.date }
        }

        let calendar = Calendar.current
        let liveSessions = healthManager.weeklyData
            .filter { calendar.isDate($0.date, inSameDayAs: referenceDate) }
            .sorted { $0.date < $1.date }

        return liveSessions.isEmpty ? sessions.sorted { $0.date < $1.date } : liveSessions
    }

    private var canMergeCurrentSessions: Bool {
        currentSessions.count == 2
    }

    private func mergeCurrentSessions() {
        guard canMergeCurrentSessions else { return }
        let primary = currentSessions[0]
        let secondary = currentSessions[1]

        isMerging = true
        mergeMessage = ""

        healthManager.mergeSessions(primary: primary, secondary: secondary) { result in
            DispatchQueue.main.async {
                isMerging = false
                switch result {
                case .success:
                    mergeMessage = "Séances fusionnées"
                case .failure:
                    mergeMessage = "Erreur lors de la fusion"
                }
            }
        }
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
