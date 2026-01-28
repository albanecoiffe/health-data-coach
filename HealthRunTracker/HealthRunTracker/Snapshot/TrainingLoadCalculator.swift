struct TrainingLoadCalculator {
    
    static func computeTrainingLoad(from runs: [DailyRunData]) -> TrainingLoad {
        
        // 🔹 Charge simple = durée pondérée par intensité
        // z4+z5 = intensité forte
        let load = runs.reduce(0.0) { acc, run in
            let intensePct = (run.z4 + run.z5) / max(run.durationMin, 1)
            return acc + run.durationMin * (1 + 2 * intensePct)
        }
        
        return TrainingLoad(
            load7d: load,
            load28d: 0,   // ❗ PAS de sens à ce niveau
            ratio: 0
        )
    }
}
