import SwiftUI

@main
struct HealthRunTrackerApp: App {
    @Environment(\.scenePhase) private var scenePhase

    @StateObject var healthManager = HealthManager(
        session: UserSession(userId: "f90a87bf-2104-4456-8a54-b42c307337e7")
    )

    var body: some Scene {
        WindowGroup {
            MainView()
                .environmentObject(healthManager)
                .onAppear { healthManager.startAutomaticSyncOnLaunch() }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active {
                        healthManager.syncRecentRunSessionsWhenAppBecomesActive()
                    }
                }
        }
    }
}
