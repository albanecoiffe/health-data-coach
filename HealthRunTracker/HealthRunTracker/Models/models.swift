import MapKit
import HealthKit
import SwiftUI

// utilisé pour la carte, purement UI
final class YearPolyline: MKPolyline {
    var year: Int = 0
}

// bar chart des zones HR
struct HeartRateZoneData: Identifiable {
    let id = UUID()
    let label: String      // Z1, Z2, Z3...
    let percentage: Double // 0.25 = 25%
    let color: Color       // pour le graphique
}

// graph semaine
struct WeeklyDistanceData: Identifiable, Equatable {
    var id: Int { weekNumber }
    let weekNumber: Int
    let distanceKm: Double
}

struct HRZones {

    // Seuils alignés Apple Health (observés)
    static let z1Upper = 139.0   // <139
    static let z2Upper = 152.0   // 140–152
    static let z3Upper = 165.0   // 153–165
    static let z4Upper = 178.0   // 166–178
    // Z5 >= 179
}


struct SessionZoneBreakdown: Identifiable {
    let id = UUID()
    let workoutStart: Date
    let z1: Double
    let z2: Double
    let z3: Double
    let z4: Double
    let z5: Double
}

// vue Année locale
struct MonthlyRunData: Identifiable {
    let id = UUID()
    let month: Int
    let distanceKm: Double
    let durationMin: Double
    let elevationGainM: Double
    let monthLabel: String
}

// records, vue année
struct RunRecord {
    let distanceTarget: Double     // en km (10, 21.1, 42.195)
    let bestTime: TimeInterval     // en secondes
    let yearAchieved: Int
}
