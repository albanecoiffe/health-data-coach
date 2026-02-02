import SwiftUI

@main
struct HealthRunTrackerApp: App {

    @StateObject var healthManager = HealthManager(
        session: UserSession(userId: "f90a87bf-2104-4456-8a54-b42c307337e7")
    )

    @State private var observer: HealthKitObserver?

    init() {
        print("🚨 APP INIT EXECUTED")
    }

    var body: some Scene {
        WindowGroup {
            MainView()
                .environmentObject(healthManager)
                .onAppear {
                    requestHealthKitAndStartObserver()
                    
                    // ⚠️ TEMPORAIRE : rebuild DB
                    // DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                        // healthManager.syncRunSessionsClean()
                    // }
                }
        }
    }

    private func requestHealthKitAndStartObserver() {

        print("🧩 Requesting HealthKit authorization")

        healthManager.reader.requestAuthorization { granted in
            DispatchQueue.main.async {
                guard granted else {
                    print("❌ HealthKit authorization denied")
                    return
                }

                print("🟢 HealthKit authorization granted")

                if observer == nil {
                    observer = HealthKitObserver(
                        reader: healthManager.reader,
                        syncService: healthManager.syncService
                    )
                    observer?.start()
                }
            }
        }
    }
}
