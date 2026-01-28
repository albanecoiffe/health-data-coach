import SwiftUI
@main

struct HealthRunTrackerApp: App {

    @StateObject var healthManager = HealthManager(
        session: UserSession(userId: "f90a87bf-2104-4456-8a54-b42c307337e7")
    )

    var body: some Scene {
        WindowGroup {
            MainView()
                .environmentObject(healthManager)
        }
    }
}

