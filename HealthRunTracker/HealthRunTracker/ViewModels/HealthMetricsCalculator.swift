import Foundation
import HealthKit

struct HealthMetricsCalculator {

    enum HeartRateZones {
        static let z1Upper = 139.0
        static let z2Upper = 152.0
        static let z3Upper = 165.0
        static let z4Upper = 178.0
    }

    static func computeZones(
        samples: [(bpm: Double, deltaMin: Double)]
    ) -> (z1: Double, z2: Double, z3: Double, z4: Double, z5: Double) {

        var z1 = 0.0, z2 = 0.0, z3 = 0.0, z4 = 0.0, z5 = 0.0

        for s in samples {
            switch s.bpm {
            case ..<HeartRateZones.z1Upper: z1 += s.deltaMin
            case HeartRateZones.z1Upper..<HeartRateZones.z2Upper: z2 += s.deltaMin
            case HeartRateZones.z2Upper..<HeartRateZones.z3Upper: z3 += s.deltaMin
            case HeartRateZones.z3Upper..<HeartRateZones.z4Upper: z4 += s.deltaMin
            default: z5 += s.deltaMin
            }
        }

        return (z1, z2, z3, z4, z5)
    }

    static func averageHR(_ values: [Double]) -> Double? {
        guard !values.isEmpty else { return nil }
        return values.reduce(0, +) / Double(values.count)
    }
}

extension HealthMetricsCalculator {

    static func buildSamples(
        from hrSamples: [HKQuantitySample]
    ) -> [(bpm: Double, deltaMin: Double)] {

        guard hrSamples.count > 1 else { return [] }

        var result: [(Double, Double)] = []

        for i in 0..<(hrSamples.count - 1) {
            let s1 = hrSamples[i]
            let s2 = hrSamples[i + 1]

            let bpm1 = s1.quantity.doubleValue(for: .count().unitDivided(by: .minute()))
            let bpm2 = s2.quantity.doubleValue(for: .count().unitDivided(by: .minute()))
            let bpm = (bpm1 + bpm2) / 2.0

            let delta = s2.startDate.timeIntervalSince(s1.startDate) / 60.0
            if delta > 0 {
                result.append((bpm, delta))
            }
        }

        return result
    }
}
