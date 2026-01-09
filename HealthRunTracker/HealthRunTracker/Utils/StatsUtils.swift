import Foundation

func avg(_ values: [Double]) -> Double {
    guard !values.isEmpty else { return 0 }
    return values.reduce(0, +) / Double(values.count)
}

func std(_ values: [Double]) -> Double {
    guard values.count > 1 else { return 0 }
    let m = avg(values)
    let variance = values.map { pow($0 - m, 2) }.reduce(0, +) / Double(values.count - 1)
    return sqrt(variance)
}

func trend12WeeksPct(_ values: [Double]) -> Double {
    guard values.count >= 24 else { return 0 }

    let last12 = Array(values.suffix(12))
    let prev12 = Array(values.dropLast(12).suffix(12))

    let a = avg(prev12)
    let b = avg(last12)

    guard a > 0 else { return 0 }
    return ((b - a) / a) * 100
}
