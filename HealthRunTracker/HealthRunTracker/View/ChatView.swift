import SwiftUI

struct ChatView: View {
    @ObservedObject var healthManager: HealthManager
    @StateObject private var vm: ChatViewModel

    init(healthManager: HealthManager) {
        self.healthManager = healthManager
        _vm = StateObject(wrappedValue: ChatViewModel(healthManager: healthManager))
    }

    var body: some View {
        VStack {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(vm.messages) { msg in
                            HStack {
                                if msg.isUser { Spacer() }

                                Text(msg.text)
                                    .padding()
                                    .background(msg.isUser ? Color.blue : Color.gray.opacity(0.3))
                                    .foregroundColor(.white)
                                    .cornerRadius(16)
                                    .frame(
                                        maxWidth: UIScreen.main.bounds.width * 0.75,
                                        alignment: msg.isUser ? .trailing : .leading
                                    )
                                // Ajout de la capacité de copier
                                    .contextMenu {
                                            Button {
                                                UIPasteboard.general.string = msg.text
                                            } label: {
                                                Label("Copier", systemImage: "doc.on.doc")
                                            }
                                        }
                                //
                                //

                                if !msg.isUser { Spacer() }
                            }
                            .padding(.horizontal)
                            .id(msg.id)
                        }
                        Color.clear
                            .frame(height: 1)
                            .id("BOTTOM")
                    
                    }
                }
                .onChange(of: vm.messages.count) { _ in
                        withAnimation(.easeOut(duration: 0.3)) {
                            proxy.scrollTo("BOTTOM", anchor: .bottom)
                        }
                }
            }

            HStack {
                TextField("Écrire un message...", text: $vm.currentInput)
                    .padding(12)
                    .background(Color.white.opacity(0.1))
                    .cornerRadius(12)
                    .foregroundColor(.white)

                Button(action: vm.sendMessage) {
                    Image(systemName: "paperplane.fill")
                        .foregroundColor(.white)
                        .font(.system(size: 20))
                        .padding(12)
                        .background(Color.blue)
                        .cornerRadius(12)
                }
            }
            .padding()
            .background(Color.black.opacity(0.8))
        }
        .background(Color.black.ignoresSafeArea())
        .onAppear {
            print("🔥 ChatView onAppear")
            vm.onAppear()
        
        }
    }
}
