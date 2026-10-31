// Made by Hoola App Sahayak (v0.332 IPHONE). Crash reports from users' iPhones, like the Android CrashGuard: when the app
// crashes, the kind of crash, the screen it was on and the app's own call frames are written to a file; on the next start
// they go to the business's Hoola server (no login, nothing personal: no form values, no account details).
import Foundation
import Darwin

private var hoolaCrashFd: Int32 = -1
private let hoolaScreenBuf: UnsafeMutablePointer<CChar> = {
    let p = UnsafeMutablePointer<CChar>.allocate(capacity: 64)
    p.initialize(repeating: 0, count: 64)
    return p
}()

private func hoolaWrite(_ s: StaticString) {
    if hoolaCrashFd >= 0 { _ = write(hoolaCrashFd, s.utf8Start, s.utf8CodeUnitCount) }
}

private func hoolaFrames() {
    // best effort after the crash line (the line + screen are already on disk)
    let me = (Bundle.main.executableURL?.lastPathComponent ?? "App")
    for f in Thread.callStackSymbols.prefix(40) where f.contains(me) {
        var parts = f.split(separator: " ", omittingEmptySubsequences: true).map(String.init)
        if parts.count > 3 { parts = Array(parts.dropFirst(3)) }      // "<n> <binary> <address>"
        let sym = parts.joined(separator: " ").components(separatedBy: " + ").first ?? ""
        let line = "at hoola.ios " + sym + "\n"
        _ = line.withCString { write(hoolaCrashFd, $0, strlen($0)) }
    }
}

private func hoolaSignal(_ sig: Int32) {
    switch sig {
    case SIGTRAP: hoolaWrite("SwiftRuntimeError: SIGTRAP (a Swift check failed: force unwrap of nil, index out of range, ...)\n")
    case SIGABRT: hoolaWrite("AbortError: SIGABRT\n")
    case SIGSEGV: hoolaWrite("MemoryError: SIGSEGV\n")
    case SIGBUS: hoolaWrite("MemoryError: SIGBUS\n")
    case SIGILL: hoolaWrite("IllegalInstructionError: SIGILL\n")
    default: hoolaWrite("SignalError: crash\n")
    }
    hoolaWrite("screen: ")
    if hoolaCrashFd >= 0 { _ = write(hoolaCrashFd, hoolaScreenBuf, strlen(hoolaScreenBuf)) }
    hoolaWrite("\n")
    hoolaFrames()
    signal(sig, SIG_DFL)
    raise(sig)
}

enum CrashGuard {
    private static var liveURL: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("hoola_crash.txt")
    }

    /// The screen on view now (kept for the crash line; ids only).
    static func screen(_ id: String) {
        let s = String(id.prefix(48).filter { $0.isLetter || $0.isNumber || $0 == "_" })
        _ = s.withCString { strncpy(hoolaScreenBuf, $0, 63) }
    }

    static func install() {
        let dir = liveURL.deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        // a crash from the last run -> kept to send (UserDefaults survives until the server has it)
        if let d = try? Data(contentsOf: liveURL), !d.isEmpty, let t = String(data: d, encoding: .utf8) {
            UserDefaults.standard.set(t, forKey: "hoola_crash_pending")
        }
        hoolaCrashFd = open(liveURL.path, O_WRONLY | O_CREAT | O_TRUNC, 0o600)
        for s in [SIGTRAP, SIGABRT, SIGSEGV, SIGBUS, SIGILL] { signal(s, hoolaSignal) }
        NSSetUncaughtExceptionHandler { e in
            let t = "\(e.name.rawValue): \(e.reason ?? "")\nscreen: \(String(cString: hoolaScreenBuf))\n"
                + e.callStackSymbols.prefix(20).map { "at hoola.ios " + ($0.components(separatedBy: " + ").first ?? "") }.joined(separator: "\n")
            _ = t.withCString { write(hoolaCrashFd, $0, strlen($0)) }
        }
    }

    /// The kept crash goes to the server (once it answers; a refused one is dropped, a busy server is tried next start).
    static func sendPending() async {
        guard let t = UserDefaults.standard.string(forKey: "hoola_crash_pending"), !t.isEmpty, Cloud.ready else { return }
        let screen = t.components(separatedBy: "\n").first { $0.hasPrefix("screen: ") }.map { String($0.dropFirst(8)) } ?? ""
        let ver = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? ""
        var sys = utsname()
        uname(&sys)
        let model = withUnsafePointer(to: &sys.machine) { $0.withMemoryRebound(to: CChar.self, capacity: 256) { String(cString: $0) } }
        let r = await Cloud.call("POST", "/crash", ["trace": String(t.prefix(6000)), "screen": screen, "ver": "\(ver).\(build)",
                                                    "model": model, "ios": ProcessInfo.processInfo.operatingSystemVersionString])
        if r.ok || (400..<500).contains(r.code) && r.code != 429 {
            UserDefaults.standard.removeObject(forKey: "hoola_crash_pending")
        }
    }
}
