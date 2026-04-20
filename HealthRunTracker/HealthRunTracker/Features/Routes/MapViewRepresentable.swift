import SwiftUI
import MapKit
import UIKit

extension UIColor {
    convenience init(from color: Color) {
        let ui = UIColor(color)
        var r: CGFloat = 0
        var g: CGFloat = 0
        var b: CGFloat = 0
        var a: CGFloat = 0
        ui.getRed(&r, green: &g, blue: &b, alpha: &a)
        self.init(red: r, green: g, blue: b, alpha: a)
    }
}

struct RoutePolyline: Identifiable {
    let id = UUID()
    let polyline: MKPolyline
    let color: Color
}

class ColoredMKPolyline: MKPolyline {
    var id: UUID!
}

struct MapViewRepresentable: View {
    var polylines: [RoutePolyline]
    @Binding var region: MKCoordinateRegion

    var body: some View {
        Map(coordinateRegion: $region,
            interactionModes: [.zoom, .pan],
            showsUserLocation: false)
        .overlay(
            MapOverlay(polylines: polylines)
        )
    }
}

struct MapOverlay: UIViewRepresentable {
    var polylines: [RoutePolyline]

    func makeUIView(context: Context) -> MKMapView {
        let map = MKMapView()
        map.delegate = context.coordinator
        map.isRotateEnabled = false
        map.overrideUserInterfaceStyle = .dark
        return map
    }

    func updateUIView(_ uiView: MKMapView, context: Context) {
        uiView.removeOverlays(uiView.overlays)

        for item in polylines {

            // On crée une polyline AVEC un ID embarqué
            let coords = item.polyline.coordinates
            let newLine = ColoredMKPolyline(coordinates: coords, count: coords.count)
            newLine.id = item.id

            context.coordinator.polyDict[item.id] = item.color
            uiView.addOverlay(newLine)
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator: NSObject, MKMapViewDelegate {
        var polyDict: [UUID: Color] = [:]

        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {

            guard let line = overlay as? ColoredMKPolyline else {
                return MKOverlayRenderer(overlay: overlay)
            }

            let renderer = MKPolylineRenderer(polyline: line)
            let color = polyDict[line.id] ?? .white
            renderer.strokeColor = UIColor(from: color)
            renderer.lineWidth = 4
            renderer.alpha = 0.9
            return renderer
        }
    }
}

// Petite extension pratique
extension MKPolyline {
    var coordinates: [CLLocationCoordinate2D] {
        var coords = [CLLocationCoordinate2D](repeating: .init(), count: pointCount)
        getCoordinates(&coords, range: NSRange(location: 0, length: pointCount))
        return coords
    }
}
