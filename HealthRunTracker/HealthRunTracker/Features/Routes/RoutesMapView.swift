import SwiftUI
import MapKit

struct RoutesMapView: View {
    @ObservedObject var healthManager: HealthManager

    @State private var polylines: [RoutePolyline] = []

    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 48.8566, longitude: 2.3522),
        span: MKCoordinateSpan(latitudeDelta: 0.2, longitudeDelta: 0.2)
    )

    var body: some View {
        VStack(spacing: 16) {
            Text("🌍 Tracés GPS – Toutes les années")
                .font(.system(size: 26, weight: .bold, design: .rounded))
                .foregroundColor(.white)
                .padding(.top, 16)

            MapViewRepresentable(polylines: polylines, region: $region)
                .frame(height: 450)
                .cornerRadius(20)
                .padding(.horizontal)

            Text("Chaque couleur = une année")
                .foregroundColor(.gray)
                .padding(.bottom, 16)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(Color.black.ignoresSafeArea())
        .onAppear {
            loadAllYears()
        }
    }

    /// Charge toutes les années avec leurs couleurs
    private func loadAllYears() {
        healthManager.fetchAllYearsRoutes { result in
            // result = [(year, polyline, color)]
            var converted: [RoutePolyline] = []

            for item in result {
                // Utilise directement la polyline d'origine (YearPolyline)
                let p = RoutePolyline(polyline: item.polyline, color: item.color)
                converted.append(p)
            }

            self.polylines = converted

            // Recentre sur le premier tracé disponible
            if let first = converted.first, first.polyline.pointCount > 0 {
                var coords = [CLLocationCoordinate2D](repeating: .init(), count: first.polyline.pointCount)
                first.polyline.getCoordinates(&coords, range: NSRange(location: 0, length: first.polyline.pointCount))
                if let coord = coords.first {
                    region.center = coord
                }
            }
        }
    }
}
