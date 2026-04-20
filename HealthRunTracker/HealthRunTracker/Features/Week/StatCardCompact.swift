import SwiftUI

struct StatCardCompact: View {
    let title: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: "figure.run.circle.fill")
                    .foregroundColor(color)
                    .font(.system(size: 18))
                Text(title.uppercased())
                    .font(.caption.weight(.semibold))
                    .foregroundColor(.gray)
            }

            Text(value)
                .font(.system(size: 22, weight: .bold, design: .rounded))
                .foregroundColor(color)
                .padding(.top, 4)
        }
        .padding()
        .frame(maxWidth: .infinity, minHeight: 100, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white.opacity(0.05))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.08))
                )
        )
    }
}
