import SwiftUI

struct WeekHeaderView: View {
    let weekOffset: Int
    let weekRangeText: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 10) {
                Text("🏃‍♀️")
                    .font(.system(size: 34))
                Text("Course – Semaine")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }
            .padding(.horizontal)

            if let text = weekRangeText {
                Text(text)
                    .font(.headline.weight(.semibold))
                    .foregroundColor(.gray)
                    .padding(.horizontal)
                    .padding(.top, -10)
            }
        }
    }
}
