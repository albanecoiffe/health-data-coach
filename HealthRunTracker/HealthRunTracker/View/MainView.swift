import SwiftUI

struct MainView: View {
    @EnvironmentObject var healthManager: HealthManager
    @State private var selectedView = 0

    var body: some View {
        VStack(spacing: 0) {

            Picker("Vue", selection: $selectedView) {
                Text("Semaine").tag(0)
                Text("Chat").tag(1)
                Text("Année").tag(2)
                Text("Carte").tag(3)
            }
            .pickerStyle(.segmented)
            .padding()

            Group {
                if selectedView == 0 {
                    ContentView(healthManager: healthManager)
                } else if selectedView == 1 {
                    ChatView(healthManager: healthManager)
                } else if selectedView == 2 {
                    YearView(healthManager: healthManager)
                } else {
                    RoutesMapView(healthManager: healthManager)
                }
            }
        }
        .background(Color.black.ignoresSafeArea())
        .onAppear {
            healthManager.requestAuthorization()
        }
    }
}
