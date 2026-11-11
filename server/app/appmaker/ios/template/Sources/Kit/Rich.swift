// Made by Hoola App Sahayak (v0.425 RANG), the iPhone twin of Rich.kt - all native SwiftUI / Apple frameworks:
// rows - SignatureRow, PhotosRow (up to 6, photo library or the camera since v0.802), VideoRow (photo library, no permission), AudioRow (voice note; the microphone
// is asked only on Record), RichTextRow (markdown words); showing - ServerPhoto, RichTextView, PhotosStripView,
// VideoPlayerView / AudioPlayerView (15-minute signed address), PdfViewerView (PDFKit); blocks - CalendarBlock,
// KanbanBlock, GanttBlock, LineChartView, PieChartView, CarouselView, OnboardingPager.
import SwiftUI
import PhotosUI
import AVKit
import AVFoundation
import PDFKit

private func tmpFile(_ ext: String) -> URL {
    FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ext)
}

enum Media {
    /// A 15-minute signed address for the phone's own player (players cannot send the sign-in token).
    static func url(_ src: String) async -> URL? {
        if src.hasPrefix("local:") { return URL(fileURLWithPath: String(src.dropFirst(6))) }
        guard src.hasPrefix("f_") else { return nil }
        let r = await Cloud.call("POST", "/files/\(src)/link", [:], token: Auth.shared.token)
        guard r.ok, let p = r.body["path"] as? String else { return nil }
        return URL(string: Cloud.base + p)
    }
}

/// A photo from the app's server (file id) or one still on this phone ("local:...").
struct ServerPhoto: View {
    let src: String
    var height: CGFloat = 180
    @State private var img: UIImage? = nil
    var body: some View {
        ZStack {
            Rectangle().fill(Color.gray.opacity(0.12))
            if let i = img { Image(uiImage: i).resizable().scaledToFill() } else { Image(systemName: "photo").foregroundStyle(.secondary) }
        }
        .frame(height: height).frame(maxWidth: .infinity).clipped().clipShape(RoundedRectangle(cornerRadius: 10))
        .task(id: src) {
            if src.hasPrefix("local:") { img = UIImage(contentsOfFile: String(src.dropFirst(6))) }
            else if src.hasPrefix("f_") {
                if let hit = ImageCache.shared.get(src) { img = hit; return }          // v0.802 MEDIA: downloaded once
                if let d = await Cloud.bytes("/files/\(src)", token: Auth.shared.token), let got = UIImage(data: d) {
                    ImageCache.shared.put(got, src)
                    img = got
                }
            }
        }
    }
}

/// What a saved row shows for its rich fields (photos, signature, video, voice note, formatted text).
struct RichRowParts: View {
    let fields: [Item]
    let r: Item
    var body: some View {
        let rich = fields.filter { ["photo", "signature", "photos", "video", "audio", "richtext"].contains($0.s("type")) && r.has($0.s("key")) && !r.s($0.s("key")).isEmpty }
        if !rich.isEmpty && !r.b("pending") {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(Array(rich.prefix(3).enumerated()), id: \.offset) { _, f in
                    switch f.s("type") {
                    case "photo", "signature": ServerPhoto(src: r.s(f.s("key")), height: 160)
                    case "photos": PhotosStripView(ids: r.s(f.s("key")))
                    case "video": VideoPlayerView(src: r.s(f.s("key")))
                    case "audio": AudioPlayerView(src: r.s(f.s("key")))
                    default: RichTextView(text: r.s(f.s("key")))
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------- rows
struct SignatureRow: View {
    let label: String
    let key: String
    @ObservedObject private var state = AppState.shared
    @State private var strokes: [[CGPoint]] = []
    @State private var current: [CGPoint] = []
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label).font(.subheadline.weight(.semibold))
            if let v = state.form[key], !v.isEmpty {
                ServerPhoto(src: v, height: 140)
                Button(Words.signAgain) { state.form[key] = nil; strokes = [] }.buttonStyle(.bordered)
            } else {
                pad.frame(height: 160)
                HStack {
                    Button(Words.useSignature) { save() }.buttonStyle(.borderedProminent).disabled(strokes.isEmpty)
                    Button(Words.clearWord) { strokes = [] }.buttonStyle(.bordered)
                }
            }
        }
    }
    private var pad: some View {
        Canvas { ctx, _ in
            for s in strokes + [current] where s.count > 1 {
                var p = Path(); p.move(to: s[0]); s.dropFirst().forEach { p.addLine(to: $0) }
                ctx.stroke(p, with: .color(.black), lineWidth: 2.5)
            }
        }
        .background(Color.white).clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gray.opacity(0.4)))
        .gesture(DragGesture(minimumDistance: 0)
            .onChanged { current.append($0.location) }
            .onEnded { _ in if current.count > 1 { strokes.append(current) }; current = [] })
    }
    @MainActor private func save() {
        let view = Canvas { ctx, _ in
            for s in strokes where s.count > 1 {
                var p = Path(); p.move(to: s[0]); s.dropFirst().forEach { p.addLine(to: $0) }
                ctx.stroke(p, with: .color(.black), lineWidth: 2.5)
            }
        }.frame(width: 360, height: 160).background(Color.white)
        let r = ImageRenderer(content: view)
        r.scale = 2
        guard let img = r.uiImage, let jpeg = img.jpegData(compressionQuality: 0.92) else { return }
        let url = tmpFile(".jpg")
        try? jpeg.write(to: url)
        state.form[key] = "local:" + url.path
    }
}

struct PhotosRow: View {
    let label: String
    let key: String
    var max = 6
    @ObservedObject private var state = AppState.shared
    @State private var items: [PhotosPickerItem] = []
    private var have: [String] { (state.form[key] ?? "").split(separator: ",").map { String($0) }.filter { !$0.isEmpty } }
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("\(label) (\(have.count)/\(max))").font(.subheadline.weight(.semibold))
            if !have.isEmpty { PhotosStripView(ids: have.joined(separator: ",")) }
            HStack {
                if have.count < max {
                    PhotosPicker(selection: $items, maxSelectionCount: max - have.count, matching: .images) { Label(Words.addPhotos, systemImage: "photo.on.rectangle") }
                    CameraButton { v in state.form[key] = Array((have + [v]).prefix(max)).joined(separator: ",") }   // v0.802 MEDIA
                }
                if !have.isEmpty { Button(Words.remove) { state.form[key] = nil }.buttonStyle(.bordered) }
            }
        }
        .onChange(of: items) { picked in
            guard !picked.isEmpty else { return }
            Task {
                var got: [String] = []
                for it in picked {
                    guard let data = try? await it.loadTransferable(type: Data.self), let img = UIImage(data: data) else { continue }
                    let scale = min(1, 1600 / Swift.max(img.size.width, img.size.height))
                    let size = CGSize(width: img.size.width * scale, height: img.size.height * scale)
                    let small = UIGraphicsImageRenderer(size: size).image { _ in img.draw(in: CGRect(origin: .zero, size: size)) }
                    guard let jpeg = small.jpegData(compressionQuality: 0.85) else { continue }
                    let url = tmpFile(".jpg")
                    try? jpeg.write(to: url)
                    got.append("local:" + url.path)
                }
                await MainActor.run {
                    state.form[key] = Array((have + got).prefix(max)).joined(separator: ",")
                    items = []
                }
            }
        }
    }
}

struct PhotosStripView: View {
    let ids: String
    @State private var big = ""
    var body: some View {
        let list = ids.split(separator: ",").map { String($0) }.filter { !$0.isEmpty }
        VStack(alignment: .leading, spacing: 8) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(list, id: \.self) { s in
                        ServerPhoto(src: s, height: 84).frame(width: 84).onTapGesture { big = big == s ? "" : s }
                    }
                }
            }
            if !big.isEmpty { ServerPhoto(src: big, height: 240) }
        }
    }
}

struct MovieFile: Transferable {
    let url: URL
    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(contentType: .movie) { m in SentTransferredFile(m.url) } importing: { got in
            let dest = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + "." + (got.file.pathExtension.isEmpty ? "mov" : got.file.pathExtension))
            try FileManager.default.copyItem(at: got.file, to: dest)
            return MovieFile(url: dest)
        }
    }
}

struct VideoRow: View {
    let label: String
    let key: String
    @ObservedObject private var state = AppState.shared
    @State private var item: PhotosPickerItem? = nil
    @State private var note = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label).font(.subheadline.weight(.semibold))
            if let v = state.form[key], !v.isEmpty { Muted(v.hasPrefix("local:") ? Words.videoReady : Words.videoSaved) }
            HStack {
                PhotosPicker(selection: $item, matching: .videos) { Label((state.form[key] ?? "").isEmpty ? Words.addVideo : Words.changeVideo, systemImage: "video") }
                if !(state.form[key] ?? "").isEmpty { Button(Words.remove) { state.form[key] = nil }.buttonStyle(.bordered) }
            }
            if !note.isEmpty { Muted(note) }
        }
        .onChange(of: item) { new in
            guard let new = new else { return }
            Task {
                guard let m = try? await new.loadTransferable(type: MovieFile.self) else { await MainActor.run { note = Words.videoTooBig }; return }
                let size = (try? FileManager.default.attributesOfItem(atPath: m.url.path)[.size] as? NSNumber)?.intValue ?? 0
                await MainActor.run {
                    if size > 50 * 1024 * 1024 || size == 0 { note = Words.videoTooBig; try? FileManager.default.removeItem(at: m.url) }
                    else { state.form[key] = "local:" + m.url.path; note = "" }
                }
            }
        }
    }
}

@MainActor
final class Recorder: ObservableObject {
    @Published var on = false
    @Published var secs = 0
    private var rec: AVAudioRecorder? = nil
    private var timer: Timer? = nil
    var url: URL? = nil
    func start() {
        let s = AVAudioSession.sharedInstance()
        try? s.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker])
        try? s.setActive(true)
        let u = tmpFile(".m4a")
        let settings: [String: Any] = [AVFormatIDKey: Int(kAudioFormatMPEG4AAC), AVSampleRateKey: 44100, AVNumberOfChannelsKey: 1,
                                       AVEncoderBitRateKey: 64000]
        guard let r = try? AVAudioRecorder(url: u, settings: settings) else { return }
        r.record(forDuration: 120)
        rec = r; url = u; on = true; secs = 0
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self else { return }
                self.secs += 1
                if self.secs >= 120 { self.stop() }
            }
        }
    }
    func stop() {
        rec?.stop(); rec = nil; on = false
        timer?.invalidate(); timer = nil
    }
}

struct AudioRow: View {
    let label: String
    let key: String
    @ObservedObject private var state = AppState.shared
    @StateObject private var rec = Recorder()
    @State private var note = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label).font(.subheadline.weight(.semibold))
            if rec.on { Muted(Words.recording + " \(rec.secs)s / 120s") }
            else if let v = state.form[key], !v.isEmpty { AudioPlayerView(src: v) }
            HStack {
                if !rec.on {
                    Button((state.form[key] ?? "").isEmpty ? Words.record : Words.recordAgain) {
                        AVAudioSession.sharedInstance().requestRecordPermission { ok in
                            Task { @MainActor in if ok { rec.start() } else { note = Words.micDenied } }
                        }
                    }.buttonStyle(.bordered)
                } else {
                    Button(Words.stopWord) {
                        rec.stop()
                        if let u = rec.url { state.form[key] = "local:" + u.path }
                    }.buttonStyle(.borderedProminent).tint(.red)
                }
                if !(state.form[key] ?? "").isEmpty && !rec.on { Button(Words.remove) { state.form[key] = nil }.buttonStyle(.bordered) }
            }
            if !note.isEmpty { Muted(note) }
        }
    }
}

struct RichTextRow: View {
    let label: String
    let key: String
    @ObservedObject private var state = AppState.shared
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).font(.subheadline.weight(.semibold))
            HStack {
                Button("B") { add("**", "**") }.buttonStyle(.bordered)
                Button("I") { add("_", "_") }.buttonStyle(.bordered)
                Button("• " + Words.listWord) { add((state.form[key] ?? "").isEmpty || (state.form[key] ?? "").hasSuffix("\n") ? "- " : "\n- ", "") }.buttonStyle(.bordered)
            }
            TextEditor(text: Binding(get: { state.form[key] ?? "" }, set: { state.form[key] = String($0.prefix(4000)) }))
                .frame(minHeight: 110).overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.gray.opacity(0.3)))
            if let v = state.form[key], !v.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { RichTextView(text: v) }
        }
    }
    private func add(_ a: String, _ b: String) {
        state.form[key] = String(((state.form[key] ?? "") + a + b).prefix(4000))
    }
}

/// Markdown words as styled text (Apple's own markdown; never HTML).
struct RichTextView: View {
    let text: String
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(Array(text.components(separatedBy: "\n").enumerated()), id: \.offset) { _, line in
                if line.hasPrefix("# ") {
                    Text(String(line.dropFirst(2))).font(.headline)
                } else if line.hasPrefix("- ") || line.hasPrefix("* ") {
                    Text(styled("•  " + String(line.dropFirst(2))))
                } else if line.trimmingCharacters(in: .whitespaces).isEmpty {
                    Spacer().frame(height: 4)
                } else {
                    Text(styled(line))
                }
            }
        }
    }
    private func styled(_ s: String) -> AttributedString {
        (try? AttributedString(markdown: s, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))) ?? AttributedString(s)
    }
}

// ---------------------------------------------------------------- players + PDF
struct VideoPlayerView: View {
    let src: String
    @State private var player: AVPlayer? = nil
    @State private var want = false
    var body: some View {
        if let p = player {
            VideoPlayer(player: p).frame(height: 220).clipShape(RoundedRectangle(cornerRadius: 10)).onAppear { p.play() }
        } else {
            Button(want ? Words.opening : Words.playVideo) {
                want = true
                Task { if let u = await Media.url(src) { player = AVPlayer(url: u) } else { want = false } }
            }.buttonStyle(.bordered)
        }
    }
}

struct AudioPlayerView: View {
    let src: String
    @State private var player: AVPlayer? = nil
    @State private var playing = false
    var body: some View {
        Button(playing ? Words.pauseWord : Words.playWord) {
            if let p = player {
                if playing { p.pause(); playing = false } else { p.play(); playing = true }
                return
            }
            Task {
                guard let u = await Media.url(src) else { return }
                let p = AVPlayer(url: u)
                player = p
                p.play(); playing = true
            }
        }.buttonStyle(.bordered)
        .onDisappear { player?.pause() }
    }
}

struct PdfKitView: UIViewRepresentable {
    let data: Data
    func makeUIView(context: Context) -> PDFView {
        let v = PDFView()
        v.autoScales = true
        v.document = PDFDocument(data: data)
        return v
    }
    func updateUIView(_ v: PDFView, context: Context) {}
}

/// A PDF inside the app (Apple's PDFKit; links and scripts in it do nothing here).
struct PdfViewerView: View {
    let fid: String
    @State private var data: Data? = nil
    @State private var failed = false
    var body: some View {
        Group {
            if let d = data { PdfKitView(data: d).frame(height: 420).clipShape(RoundedRectangle(cornerRadius: 10)) }
            else if failed { Muted(Words.pdfFailed) }
            else { Muted(Words.opening) }
        }
        .task(id: fid) {
            if let d = await Cloud.bytes("/files/\(fid)", token: Auth.shared.token) { data = d } else { failed = true }
        }
    }
}

// ---------------------------------------------------------------- blocks
private func headOf(_ r: Item) -> String {
    for k in ["name", "title", "service", "item", "subject"] where !r.s(k).isEmpty { return r.s(k) }
    return String(r.id.suffix(6))
}

private let isoDay: DateFormatter = { let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"; f.locale = Locale(identifier: "en_US_POSIX"); return f }()

struct CalendarBlock: View {
    let coll: String
    var dateKey = "date"
    @ObservedObject private var db = Db.shared
    @State private var month = Date()
    @State private var day = ""
    var body: some View {
        let cal = Calendar(identifier: .gregorian)
        let rows = db.rows(coll)
        let byDay = Dictionary(grouping: rows, by: { String($0.s(dateKey).prefix(10)) })
        let first = cal.date(from: cal.dateComponents([.year, .month], from: month)) ?? month
        let count = cal.range(of: .day, in: .month, for: first)?.count ?? 30
        let lead = (cal.component(.weekday, from: first) + 5) % 7
        let cells: [String?] = Array(repeating: nil, count: lead) + (0..<count).map { isoDay.string(from: cal.date(byAdding: .day, value: $0, to: first) ?? first) }
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Button("‹") { month = cal.date(byAdding: .month, value: -1, to: month) ?? month }
                Text(first.formatted(.dateTime.month(.wide).year())).font(.headline)
                Button("›") { month = cal.date(byAdding: .month, value: 1, to: month) ?? month }
            }
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 4), count: 7), spacing: 4) {
                ForEach(Array(cells.enumerated()), id: \.offset) { _, d in
                    let n = d.flatMap { byDay[$0]?.count } ?? 0
                    VStack(spacing: 2) {
                        Text(d.map { String($0.suffix(2)) } ?? "").font(.caption)
                        if n > 0 { Text("•\(n)").font(.caption2) }
                    }
                    .frame(maxWidth: .infinity, minHeight: 40)
                    .background(d != nil && d == day ? Color.accentColor.opacity(0.18) : (n > 0 ? Color.gray.opacity(0.12) : Color.clear))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .onTapGesture { if let d = d { day = d } }
                }
            }
            if !day.isEmpty {
                let list = byDay[day] ?? []
                Muted(day + " · \(list.count)")
                ForEach(list.prefix(20), id: \.id) { r in Card { Text(headOf(r)); Muted([r.s("time"), T(r.s("status"))].filter { !$0.isEmpty }.joined(separator: " · ")) } }
            }
        }
        .task { await db.refresh(coll) }
    }
}

struct KanbanBlock: View {
    let coll: String
    @ObservedObject private var db = Db.shared
    @ObservedObject private var auth = Auth.shared
    @ObservedObject private var team = Team.shared
    @State private var open = ""
    var body: some View {
        let opts = db.fields(coll).first(where: { $0.s("key") == "status" })?.strings("options") ?? []
        let rows = db.rows(coll)
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: .top, spacing: 10) {
                ForEach(opts, id: \.self) { st in
                    let list = rows.filter { $0.s("status") == st }
                    VStack(alignment: .leading, spacing: 6) {
                        Text(T(st) + " (\(list.count))").font(.headline)
                        ForEach(list.prefix(30), id: \.id) { r in
                            Card {
                                Text(headOf(r))
                                if open == r.id && auth.isStaff && !r.b("pending") && team.mayWork(r) {
                                    ForEach(opts.filter { $0 != st }, id: \.self) { to in
                                        Button("→ " + T(to)) { db.update(coll, r.id, ["status": to]); open = "" }.buttonStyle(.bordered)
                                    }
                                }
                            }
                            .onTapGesture { open = open == r.id ? "" : r.id }
                        }
                    }
                    .padding(8).frame(width: 220, alignment: .topLeading)
                    .background(Color.gray.opacity(0.1)).clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
        .task { await db.refresh(coll) }
    }
}

struct GanttBlock: View {
    let coll: String
    var startKey = "start"
    var endKey = "end"
    @ObservedObject private var db = Db.shared
    var body: some View {
        let rows: [(Item, Date, Date)] = db.rows(coll).compactMap { r in
            guard let a = isoDay.date(from: String(r.s(startKey).prefix(10))) else { return nil }
            let b = isoDay.date(from: String(r.s(endKey).prefix(10))) ?? a
            return (r, a, b < a ? a : b)
        }
        let list = Array(rows.prefix(40))
        VStack(alignment: .leading, spacing: 6) {
            if let lo = list.map({ $0.1 }).min(), let hi = list.map({ $0.2 }).max() {
                let span = max(1, hi.timeIntervalSince(lo) + 86400)
                Muted(isoDay.string(from: lo) + " → " + isoDay.string(from: hi))
                ForEach(Array(list.enumerated()), id: \.offset) { _, x in
                    Muted(headOf(x.0))
                    GeometryReader { g in
                        let x0 = g.size.width * x.1.timeIntervalSince(lo) / span
                        let w = max(6, g.size.width * (x.2.timeIntervalSince(x.1) + 86400) / span)
                        ZStack(alignment: .leading) {
                            Capsule().fill(Color.gray.opacity(0.15))
                            Capsule().fill(Color.accentColor).frame(width: w).offset(x: x0)
                        }
                    }.frame(height: 14)
                }
            } else { Muted(Words.nothingYet) }
        }
        .task { await db.refresh(coll) }
    }
}

struct LineChartView: View {
    let values: [Double]
    var labels: [String] = []
    var body: some View {
        if values.count < 2 { Muted(Words.nothingYet) } else {
            VStack(spacing: 4) {
                GeometryReader { g in
                    let mx = max(values.max() ?? 1, 1e-6), mn = min(0, values.min() ?? 0)
                    let sx = g.size.width / CGFloat(values.count - 1)
                    Path { p in
                        for (i, v) in values.enumerated() {
                            let pt = CGPoint(x: CGFloat(i) * sx, y: g.size.height - CGFloat((v - mn) / (mx - mn)) * g.size.height)
                            if i == 0 { p.move(to: pt) } else { p.addLine(to: pt) }
                        }
                    }.stroke(Color.accentColor, lineWidth: 2.5)
                }.frame(height: 140)
                if let a = labels.first, let b = labels.last { HStack { Muted(a); Spacer(); Muted(b) } }
            }
        }
    }
}

struct PieChartView: View {
    let values: [Double]
    let labels: [String]
    private let colors: [Color] = [.accentColor, .orange, .teal, .purple, .pink, .gray]
    var body: some View {
        let total = values.reduce(0, +)
        if total <= 0 { Muted(Words.nothingYet) } else {
            HStack(spacing: 16) {
                ZStack {
                    ForEach(Array(values.enumerated()), id: \.offset) { i, v in
                        let start = values.prefix(i).reduce(0, +) / total
                        Circle().trim(from: start, to: start + v / total)
                            .stroke(colors[i % colors.count], lineWidth: 18).rotationEffect(.degrees(-90))
                    }
                }.frame(width: 110, height: 110)
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(Array(zip(labels, values).enumerated()), id: \.offset) { i, lv in
                        HStack(spacing: 6) {
                            Circle().fill(colors[i % colors.count]).frame(width: 10, height: 10)
                            Muted("\(lv.0) · \(Int(lv.1 / total * 100))%")
                        }
                    }
                }
            }
        }
    }
}

struct CarouselView: View {
    let photos: [String]
    var height: CGFloat = 220
    var body: some View {
        if !photos.isEmpty {
            TabView {
                ForEach(photos, id: \.self) { s in ServerPhoto(src: s, height: height) }
            }
            .tabViewStyle(.page).frame(height: height + 24)
        }
    }
}

struct OnboardingPager: View {
    let pages: [(String, String)]
    let done: () -> Void
    @State private var at = 0
    var body: some View {
        VStack(spacing: 16) {
            TabView(selection: $at) {
                ForEach(Array(pages.enumerated()), id: \.offset) { i, p in
                    VStack(alignment: .leading, spacing: 10) {
                        Text(p.0).font(.title2.weight(.semibold))
                        Text(p.1)
                    }.padding().tag(i)
                }
            }
            .tabViewStyle(.page).frame(height: 260)
            HStack {
                Button(Words.skipWord) { done() }.buttonStyle(.bordered)
                Spacer()
                Button(at >= pages.count - 1 ? Words.doneWord : Words.nextWord) {
                    if at >= pages.count - 1 { done() } else { withAnimation { at += 1 } }
                }.buttonStyle(.borderedProminent)
            }
        }
    }
}
