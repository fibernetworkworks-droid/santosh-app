// Made by Hoola App Sahayak (v0.802 MEDIA), iPhone parity with the Android kit: the in-app camera beside the photo
// library picker (CameraButton / CameraPicker - shown only on a phone that has a camera, the simulator has none), the
// share sheet (ShareButton(text:url:) with ShareLink, shareText(_:url:) for a button's action - the twin of
// Act.share(c, text)), and ONE in-memory cache for every photo the kit downloads from the app's server (ImageCache).
import SwiftUI
import UIKit

enum MediaWords {
    private static func t(_ en: String, _ hi: String, _ hing: String) -> String {
        switch I18n.current { case "hi": return hi; case "hinglish": return hing; case "en": return en; default: return T(en) }
    }
    static var takePhoto: String { t("Take photo", "फ़ोटो खींचें", "Photo khinchiye") }
    static var share: String { t("Share", "शेयर करें", "Share karein") }
}

// ---------------------------------------------------------------- image cache
/// Photos already downloaded from the app's server stay in memory (keyed by file id), so a list scrolled back or a
/// screen opened again does not download them again. NSCache lets iOS empty it when memory runs low.
final class ImageCache {
    static let shared = ImageCache()
    private let cache = NSCache<NSString, UIImage>()

    init() {
        cache.countLimit = 150
        cache.totalCostLimit = 48 * 1024 * 1024
    }

    func get(_ key: String) -> UIImage? {
        cache.object(forKey: key as NSString)
    }

    func put(_ img: UIImage, _ key: String) {
        let cost = Int(img.size.width * img.scale * img.size.height * img.scale * 4)
        cache.setObject(img, forKey: key as NSString, cost: cost)
    }

    func clear() {
        cache.removeAllObjects()
    }
}

// ---------------------------------------------------------------- camera
/// A photo shrunk on the phone (longest side 1600) and kept as a JPEG in the app's temporary folder: the same
/// "local:<path>" value the photo library picker gives, so the outbox uploads it the same way.
func localJpeg(_ img: UIImage) -> String? {
    let scale = min(1, 1600 / max(img.size.width, img.size.height))
    let size = CGSize(width: img.size.width * scale, height: img.size.height * scale)
    let small = UIGraphicsImageRenderer(size: size).image { _ in img.draw(in: CGRect(origin: .zero, size: size)) }
    guard let jpeg = small.jpegData(compressionQuality: 0.85) else { return nil }
    let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".jpg")
    do { try jpeg.write(to: url) } catch { return nil }
    return "local:" + url.path
}

/// "Take photo": opens the camera (iOS asks once, with the reason written in the app's settings). Nothing shows on a
/// device without a camera (the simulator), so the photo library picker beside it is always the other way.
struct CameraButton: View {
    var label: String = ""
    let onPhoto: (String) -> Void
    @State private var open = false

    var body: some View {
        if UIImagePickerController.isSourceTypeAvailable(.camera) {
            Button { open = true } label: { Label(label.isEmpty ? MediaWords.takePhoto : label, systemImage: "camera.fill") }
                .buttonStyle(.bordered)
                .fullScreenCover(isPresented: $open) {
                    CameraPicker { img in
                        open = false
                        if let img = img, let v = localJpeg(img) { onPhoto(v) }
                    }
                    .ignoresSafeArea()
                }
        }
    }
}

struct CameraPicker: UIViewControllerRepresentable {
    let done: (UIImage?) -> Void

    func makeCoordinator() -> Coord { Coord(done: done) }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let vc = UIImagePickerController()
        if UIImagePickerController.isSourceTypeAvailable(.camera) { vc.sourceType = .camera }
        vc.allowsEditing = false
        vc.delegate = context.coordinator
        return vc
    }

    func updateUIViewController(_ vc: UIImagePickerController, context: Context) {}

    @MainActor
    final class Coord: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let done: (UIImage?) -> Void
        init(done: @escaping (UIImage?) -> Void) { self.done = done }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            done(info[.originalImage] as? UIImage)
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            done(nil)
        }
    }
}

// ---------------------------------------------------------------- share
/// The system share sheet for words and / or a link (an order, a receipt link, the shop's address).
struct ShareButton: View {
    let text: String
    var url: String = ""
    var label: String = ""

    var body: some View {
        let title = label.isEmpty ? MediaWords.share : label
        if let u = URL(string: url), u.scheme == "https" || u.scheme == "http" {
            ShareLink(item: u, message: text.isEmpty ? nil : Text(text)) { Label(title, systemImage: "square.and.arrow.up") }
                .buttonStyle(.bordered)
        } else {
            ShareLink(item: text) { Label(title, systemImage: "square.and.arrow.up") }
                .buttonStyle(.bordered)
        }
    }
}

/// The share sheet from inside a button's action (the twin of Android's Act.share(c, text)).
@MainActor
func shareText(_ text: String, url: String = "") {
    var items: [Any] = []
    if !text.isEmpty { items.append(text) }
    if let u = URL(string: url), u.scheme == "https" || u.scheme == "http" { items.append(u) }
    guard !items.isEmpty else { return }
    let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
    guard let scene = scenes.first(where: { $0.activationState == .foregroundActive }) ?? scenes.first,
          let window = scene.windows.first(where: { $0.isKeyWindow }) ?? scene.windows.first,
          var top = window.rootViewController else { return }
    while let next = top.presentedViewController { top = next }
    let vc = UIActivityViewController(activityItems: items, applicationActivities: nil)
    if let pop = vc.popoverPresentationController {          // iPad: the sheet needs a place to point at
        pop.sourceView = top.view
        pop.sourceRect = CGRect(x: top.view.bounds.midX, y: top.view.bounds.midY, width: 0, height: 0)
        pop.permittedArrowDirections = []
    }
    top.present(vc, animated: true)
}
