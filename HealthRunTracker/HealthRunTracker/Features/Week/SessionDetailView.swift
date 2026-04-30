import SwiftUI

struct SessionDetailView: View {
    @EnvironmentObject var healthManager: HealthManager
    let session: DailyRunData

    @State private var selectedSessionType: String = ""
    @State private var sessionDetailText: String = ""
    @State private var isSaving = false
    @State private var saveMessage: String = ""

    private var currentSession: DailyRunData {
        healthManager.weeklyData.first(where: { $0.id == session.id }) ?? session
    }

    private var isLocked: Bool {
        if let sessionType = currentSession.sessionType {
            return !sessionType.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        return false
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                if !healthManager.sessionMetadataErrorText.isEmpty {
                    Text("Erreur métadonnées: \(healthManager.sessionMetadataErrorText)")
                        .font(.footnote)
                        .foregroundColor(.red)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                if isLocked {
                    SessionClassificationReadOnlyCard(
                        sessionType: currentSession.sessionType ?? "—",
                        sessionDetail: currentSession.sessionDetail
                    )
                } else {
                    SessionClassificationEditableCard(
                        selectedSessionType: $selectedSessionType,
                        sessionDetailText: $sessionDetailText,
                        suggestedType: currentSession.predictedSessionType,
                        saveMessage: saveMessage,
                        isSaving: isSaving,
                        onSave: saveMetadata
                    )
                }

                SessionMetricsGrid(session: currentSession)
                HRZoneBarChart(session: currentSession)

                if !currentSession.heartRateTimeline.isEmpty {
                    HeartRateTimelineChart(samples: currentSession.heartRateTimeline)
                }
            }
            .padding()
        }
        .background(Color.black.ignoresSafeArea())
        .navigationTitle(currentSession.dayLabel)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            syncLocalStateFromCurrentSession()
            healthManager.refreshMetadata(for: currentSession)
        }
        .onChange(of: currentSession.sessionType) { _, _ in
            syncLocalStateFromCurrentSession()
        }
        .onChange(of: currentSession.predictedSessionType) { _, _ in
            syncLocalStateFromCurrentSession()
        }
        .onChange(of: currentSession.sessionDetail) { _, _ in
            syncLocalStateFromCurrentSession()
        }
    }

    private func saveMetadata() {
        isSaving = true
        saveMessage = ""

        healthManager.updateSessionMetadata(
            for: currentSession,
            sessionType: selectedSessionType.isEmpty ? nil : selectedSessionType,
            sessionDetail: sessionDetailText.trimmingCharacters(in: .whitespacesAndNewlines)
        ) { result in
            DispatchQueue.main.async {
                isSaving = false
                switch result {
                case .success:
                    saveMessage = "Enregistré"
                case .failure:
                    saveMessage = "Erreur lors de l'enregistrement"
                }
            }
        }
    }

    private func syncLocalStateFromCurrentSession() {
        if isLocked {
            selectedSessionType = currentSession.sessionType ?? ""
        } else if selectedSessionType.isEmpty {
            selectedSessionType = currentSession.effectiveSessionType ?? ""
        }

        if sessionDetailText.isEmpty {
            sessionDetailText = currentSession.sessionDetail ?? ""
        }
    }
}

private struct SessionClassificationReadOnlyCard: View {
    let sessionType: String
    let sessionDetail: String?

    private var normalizedType: String {
        sessionType.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var detailText: String {
        let trimmed = (sessionDetail ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "Aucun détail saisi" : trimmed
    }

    private var typeAccent: Color {
        switch normalizedType.lowercased() {
        case "footing":
            return .blue
        case "fractionné":
            return .orange
        case "sortie longue":
            return .green
        case "semi marathon":
            return Color(red: 0.68, green: 0.48, blue: 1.0)
        case "marathon":
            return .red
        default:
            return .white
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Catégorie de séance")
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                        .foregroundColor(.white)

                    Text("Enregistrée dans votre historique")
                        .font(.footnote.weight(.medium))
                        .foregroundColor(.white.opacity(0.45))
                }

                Spacer()

                Image(systemName: "checkmark.seal.fill")
                    .font(.title3)
                    .foregroundColor(typeAccent.opacity(0.9))
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Catégorie")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.white.opacity(0.55))

                HStack(spacing: 10) {
                    Circle()
                        .fill(typeAccent)
                        .frame(width: 10, height: 10)

                    Text(normalizedType.capitalized)
                        .font(.system(size: 20, weight: .semibold, design: .rounded))
                        .foregroundColor(.white)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
                .background(
                    Capsule()
                        .fill(typeAccent.opacity(0.14))
                        .overlay(
                            Capsule()
                                .stroke(typeAccent.opacity(0.35), lineWidth: 1)
                        )
                )
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Détail")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.white.opacity(0.55))

                Text(detailText)
                    .font(.system(size: 18, weight: .medium, design: .rounded))
                    .foregroundColor(.white.opacity(detailText == "Aucun détail saisi" ? 0.5 : 0.95))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .background(
                        RoundedRectangle(cornerRadius: 18)
                            .fill(Color.white.opacity(0.04))
                            .overlay(
                                RoundedRectangle(cornerRadius: 18)
                                    .stroke(Color.white.opacity(0.06), lineWidth: 1)
                            )
                    )
            }
        }
        .padding(22)
        .background(
            RoundedRectangle(cornerRadius: 30)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.05),
                            Color.white.opacity(0.025)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 30)
                        .stroke(Color.white.opacity(0.06), lineWidth: 1)
                )
        )
    }
}

private struct SessionClassificationEditableCard: View {
    @Binding var selectedSessionType: String
    @Binding var sessionDetailText: String

    let suggestedType: String?
    let saveMessage: String
    let isSaving: Bool
    let onSave: () -> Void

    private var accentColor: Color {
        .yellow
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Catégorie de séance")
                    .font(.system(size: 24, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text("Confirmez ou corrigez la prédiction, puis ajoutez le détail si besoin.")
                    .font(.footnote.weight(.medium))
                    .foregroundColor(.white.opacity(0.45))
            }

            if let suggestedType, !suggestedType.isEmpty {
                HStack(spacing: 10) {
                    Image(systemName: "sparkles")
                        .foregroundColor(accentColor)

                    Text("Prédiction: \(suggestedType)")
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(.white.opacity(0.88))
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(accentColor.opacity(0.12))
                        .overlay(
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(accentColor.opacity(0.28), lineWidth: 1)
                        )
                )
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Catégorie")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.white.opacity(0.65))

                Picker("Catégorie", selection: $selectedSessionType) {
                    Text("Sélectionner").tag("")
                    ForEach([
                        "footing",
                        "fractionné",
                        "sortie longue",
                        "semi marathon",
                        "marathon",
                    ], id: \.self) { value in
                        Text(value.capitalized).tag(value)
                    }
                }
                .pickerStyle(.menu)
                .tint(accentColor)
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(Color.white.opacity(0.04))
                        .overlay(
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(Color.white.opacity(0.06), lineWidth: 1)
                        )
                )
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Détail de la séance")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.white.opacity(0.65))

                TextField("Ex: 6x400 R100 4:20/km", text: $sessionDetailText, axis: .vertical)
                    .textFieldStyle(.plain)
                    .padding(14)
                    .foregroundColor(.white)
                    .background(
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color.white.opacity(0.04))
                            .overlay(
                                RoundedRectangle(cornerRadius: 16)
                                    .stroke(Color.white.opacity(0.06), lineWidth: 1)
                            )
                    )
            }

            HStack(spacing: 12) {
                Button(action: onSave) {
                    HStack(spacing: 8) {
                        if isSaving {
                            ProgressView()
                                .tint(.black)
                        } else {
                            Image(systemName: "square.and.arrow.down")
                        }

                        Text(isSaving ? "Enregistrement..." : "Enregistrer")
                            .fontWeight(.semibold)
                        }
                    }
                .buttonStyle(.borderedProminent)
                .tint(accentColor)
                .disabled(isSaving)

                if !saveMessage.isEmpty {
                    Text(saveMessage)
                        .font(.footnote.weight(.semibold))
                        .foregroundColor(saveMessage == "Enregistré" ? .green : .red)
                }
            }
        }
        .padding(22)
        .background(
            RoundedRectangle(cornerRadius: 30)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.05),
                            Color.white.opacity(0.025)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 30)
                        .stroke(Color.white.opacity(0.06), lineWidth: 1)
                )
        )
    }
}
