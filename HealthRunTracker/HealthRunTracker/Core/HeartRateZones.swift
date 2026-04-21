import SwiftUI

struct HeartRateZoneDefinition: Identifiable {
    let id: String
    let label: String
    let lowerBound: Double?
    let upperBound: Double?
    let color: Color

    var rangeText: String {
        switch (lowerBound, upperBound) {
        case (nil, let upper?):
            return "< \(Int(upper)) bpm"
        case (let lower?, let upper?):
            return "\(Int(lower))-\(Int(upper - 1)) bpm"
        case (let lower?, nil):
            return ">= \(Int(lower)) bpm"
        default:
            return "non defini"
        }
    }
}

enum HeartRateZones {
    // Modifier les seuils cardiaques du coureur ici.
    static let definitions: [HeartRateZoneDefinition] = [
        HeartRateZoneDefinition(
            id: "z1",
            label: "Z1",
            lowerBound: nil,
            upperBound: 145,
            color: .blue
        ),
        HeartRateZoneDefinition(
            id: "z2",
            label: "Z2",
            lowerBound: 145,
            upperBound: 159,
            color: .teal
        ),
        HeartRateZoneDefinition(
            id: "z3",
            label: "Z3",
            lowerBound: 159,
            upperBound: 173,
            color: .green
        ),
        HeartRateZoneDefinition(
            id: "z4",
            label: "Z4",
            lowerBound: 173,
            upperBound: 186,
            color: .orange
        ),
        HeartRateZoneDefinition(
            id: "z5",
            label: "Z5",
            lowerBound: 186,
            upperBound: nil,
            color: .red
        ),
    ]

    static let lowIntensityTitle = "Low intensity (Z1-Z3)"
    static let highIntensityTitle = "High intensity (Z4-Z5)"

    static let z1Upper = definitions[0].upperBound!
    static let z2Upper = definitions[1].upperBound!
    static let z3Upper = definitions[2].upperBound!
    static let z4Upper = definitions[3].upperBound!

    static func definition(for bpm: Double) -> HeartRateZoneDefinition {
        definitions.first { zone in
            let aboveLower = zone.lowerBound.map { bpm >= $0 } ?? true
            let belowUpper = zone.upperBound.map { bpm < $0 } ?? true
            return aboveLower && belowUpper
        } ?? definitions[0]
    }

    static func color(for bpm: Double) -> Color {
        definition(for: bpm).color
    }

    static func values(for session: DailyRunData) -> [(zone: HeartRateZoneDefinition, minutes: Double)] {
        [
            (definitions[0], session.z1),
            (definitions[1], session.z2),
            (definitions[2], session.z3),
            (definitions[3], session.z4),
            (definitions[4], session.z5),
        ]
    }

    static func values(for session: SessionZoneBreakdown) -> [(zone: HeartRateZoneDefinition, minutes: Double)] {
        [
            (definitions[0], session.z1),
            (definitions[1], session.z2),
            (definitions[2], session.z3),
            (definitions[3], session.z4),
            (definitions[4], session.z5),
        ]
    }

    static func values(for session: RunSession) -> [(zone: HeartRateZoneDefinition, minutes: Double)] {
        [
            (definitions[0], session.z1),
            (definitions[1], session.z2),
            (definitions[2], session.z3),
            (definitions[3], session.z4),
            (definitions[4], session.z5),
        ]
    }

    static func totalMinutes(for session: DailyRunData) -> Double {
        values(for: session).map(\.minutes).reduce(0, +)
    }

    static func totalMinutes(for session: RunSession) -> Double {
        values(for: session).map(\.minutes).reduce(0, +)
    }

    static func lowIntensityMinutes(for session: DailyRunData) -> Double {
        session.z1 + session.z2 + session.z3
    }

    static func lowIntensityMinutes(for session: RunSession) -> Double {
        session.z1 + session.z2 + session.z3
    }

    static func highIntensityMinutes(for session: DailyRunData) -> Double {
        session.z4 + session.z5
    }

    static func highIntensityMinutes(for session: RunSession) -> Double {
        session.z4 + session.z5
    }

    static func weeklyTotals(
        from sessions: [SessionZoneBreakdown]
    ) -> [(zone: HeartRateZoneDefinition, minutes: Double)] {
        definitions.map { zone in
            let minutes = sessions
                .flatMap { values(for: $0) }
                .filter { $0.zone.id == zone.id }
                .map(\.minutes)
                .reduce(0, +)
            return (zone, minutes)
        }
    }
}

struct HeartRateZoneLegend: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(HeartRateZones.definitions) { zone in
                HStack(spacing: 8) {
                    Circle()
                        .fill(zone.color)
                        .frame(width: 8, height: 8)
                    Text("\(zone.label) : \(zone.rangeText)")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
            }
        }
        .padding(.horizontal, 8)
    }
}
