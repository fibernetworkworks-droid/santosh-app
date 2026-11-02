// Made by Hoola App Sahayak (v0.453 SURAKSHIT LOGIN), the iPhone twin of SignIn.kt: the ways into the app and the
// user's own security page.
//
// The OTP box is the app's own box - the 6 digits go straight to this app's server, are never stored here and never
// shown again. "Sign in with Apple" uses Apple's own system framework (no library, no secret in the app): it returns
// an identity token that the SERVER checks - signature, audience and the single-use nonce - before any account exists.
// A staff account with the second step on finishes at the authenticator code.
import AuthenticationServices
import SwiftUI
import UIKit

enum Ways {
    @MainActor private static var sign: [String: Any] { (AppData.shared.backend["sign"] as? [String: Any]) ?? [:] }
    @MainActor private static var list: [String] { (sign["ways"] as? [Any])?.compactMap { $0 as? String } ?? ["email_password"] }
    @MainActor static var otp: Bool { list.contains("phone_otp") }
    @MainActor static var apple: Bool { list.contains("apple") }
    @MainActor static var password: Bool { list.contains("email_password") || list.isEmpty }
    @MainActor static var consentNeeded: Bool { sign["consent"] as? Bool ?? true }
    @MainActor static var signupOpen: Bool { sign["signup"] as? Bool ?? true }
}

struct SignInScreen: View {
    @ObservedObject private var auth = Auth.shared
    @State private var step = ""
    @State private var busy = false
    @State private var err = ""
    @State private var phone = ""
    @State private var code = ""
    @State private var name = ""
    @State private var email = ""
    @State private var pw = ""
    @State private var twoCode = ""
    @State private var consent = false

    var body: some View {
        Page(step == "two_fa" ? Words.sg2fa : Words.signIn) {
            if step == "two_fa" {
                Muted(Words.sg2faWhy)
                TextField(Words.sgCode, text: $twoCode).textFieldStyle(.roundedBorder).keyboardType(.numberPad)
                MainButton(text: busy ? Words.sending : Words.cont) { go { await auth.twoFa(twoCode) } }
            } else {
                Muted(Words.sgWhy)
                if Ways.consentNeeded { Toggle(Words.sgConsent, isOn: $consent).font(.subheadline) }
                if step == "password" || !Ways.otp {
                    TextField(Words.email, text: $email).textFieldStyle(.roundedBorder)
                        .textContentType(.emailAddress).keyboardType(.emailAddress).textInputAutocapitalization(.never)
                    SecureField(Words.password, text: $pw).textFieldStyle(.roundedBorder).textContentType(.password)
                    MainButton(text: busy ? Words.sending : Words.signIn) { go { await auth.login(email: email, password: pw) } }
                    if Ways.signupOpen {
                        Button(Words.newHere) { go { await auth.signup(email: email, password: pw, name: name, consent: consent) } }.buttonStyle(.borderless)
                    }
                } else if phone.isEmpty {
                    TextField(Words.sgPhone, text: $phone).textFieldStyle(.roundedBorder).keyboardType(.phonePad)
                        .textContentType(.telephoneNumber)
                    MainButton(text: busy ? Words.sending : Words.sgSendCode) { sendCode() }
                } else {
                    Muted(Words.sgSentTo + " " + phone)
                    TextField(Words.sgCode, text: $code).textFieldStyle(.roundedBorder).keyboardType(.numberPad)
                        .textContentType(.oneTimeCode)
                    TextField(Words.name, text: $name).textFieldStyle(.roundedBorder)
                    MainButton(text: busy ? Words.sending : Words.cont) {
                        go { await auth.otpCheck(phone, code, name, consent) }
                    }
                    Button(Words.sgAgain) { phone = ""; code = ""; err = "" }.buttonStyle(.borderless)
                }
                if !err.isEmpty { Text(err).foregroundStyle(.red).font(.subheadline) }
                if Ways.apple { AppleButton(consent: consent, name: name, done: finish) }
                if Ways.otp && Ways.password {
                    Button(step == "password" ? Words.sgUsePhone : Words.sgUseEmail) {
                        step = step == "password" ? "" : "password"
                        err = ""
                    }.buttonStyle(.borderless)
                }
                Muted(Words.sgNever)
            }
        }
    }

    private func sendCode() {
        guard !busy else { return }
        busy = true
        err = ""
        let p = phone
        phone = ""
        Task {
            let e = await auth.otpStart(p)
            busy = false
            if let e { err = e } else { phone = p }
        }
    }

    private func go(_ work: @escaping () async -> String?) {
        guard !busy else { return }
        busy = true
        err = ""
        Task {
            let e = await work()
            busy = false
            finish(e)
        }
    }

    private func finish(_ e: String?) {
        if e == nil {
            pw = ""
            code = ""
            Router.shared.back()
        } else if e == needTwoFa {
            step = "two_fa"
            err = ""
        } else {
            err = e ?? ""
        }
    }
}

/// Apple's own button; the token it returns is checked by this app's server, never here.
struct AppleButton: View {
    let consent: Bool
    let name: String
    let done: (String?) -> Void
    @State private var nonce = ""

    var body: some View {
        SignInWithAppleButton(.continue, onRequest: { req in
            req.requestedScopes = [.fullName, .email]
            req.nonce = nonce
        }, onCompletion: { result in
            switch result {
            case .success(let auth):
                guard let cred = auth.credential as? ASAuthorizationAppleIDCredential,
                      let data = cred.identityToken, let token = String(data: data, encoding: .utf8) else {
                    done(Words.tryAgain)
                    return
                }
                let given = [cred.fullName?.givenName, cred.fullName?.familyName].compactMap { $0 }.joined(separator: " ")
                Task { done(await Auth.shared.social("apple", token, nonce, given.isEmpty ? name : given, consent)) }
            case .failure:
                break                                   // the user closed Apple's sheet: nothing to say
            }
        })
        .signInWithAppleButtonStyle(.black)
        .frame(height: 46)
        .task { if nonce.isEmpty { nonce = await Auth.shared.nonce() } }
    }
}

/// This account's own logins, second step and data (not the owner's view).
struct SecurityScreen: View {
    @ObservedObject private var auth = Auth.shared
    @State private var data: Item? = nil
    @State private var tick = 0
    @State private var busy = false
    @State private var secret = ""
    @State private var onCode = ""
    @State private var offCode = ""
    @State private var note = ""

    var body: some View {
        Page(Words.sgSecurity) {
            if auth.me == nil {
                Muted(Words.sgWhy)
                MainButton(text: Words.signIn) { Router.shared.go("hoola_login") }
            } else if let d = data {
                Text(Words.sgLogins).font(.headline)
                ForEach(items(d.o["sessions"]), id: \.id) { s in
                    Card {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(s.s("device")).font(.headline)
                                Muted(s.s("how") + " · " + s.s("ip") + (s.b("this") ? " · " + Words.sgThisPhone : ""))
                            }
                            Spacer()
                            if !s.b("this") {
                                Button(Words.sgEnd) { act("end", ["id": s.id]) }.buttonStyle(.bordered).disabled(busy)
                            }
                        }
                    }
                }
                MainButton(text: Words.sgEndAll, tonal: true) { act("end-all", [:]) }
                if d.b("staff") {
                    Text(Words.sg2fa).font(.headline)
                    Muted(d.b("two_fa") ? Words.sg2faIsOn : Words.sg2faWhy)
                    if !secret.isEmpty {
                        Muted(Words.sg2faAdd)
                        Card { Text(secret).font(.headline) }
                        TextField(Words.sgCode, text: $onCode).textFieldStyle(.roundedBorder).keyboardType(.numberPad)
                        MainButton(text: Words.cont) { act("2fa-on", ["code": onCode]) }
                    } else if !d.b("two_fa") {
                        MainButton(text: Words.sg2faStart) { act("2fa-start", [:]) }
                    } else if !d.b("two_fa_required") {
                        TextField(Words.sgCode, text: $offCode).textFieldStyle(.roundedBorder).keyboardType(.numberPad)
                        MainButton(text: Words.sg2faOff, tonal: true) { act("2fa-off", ["code": offCode]) }
                    } else {
                        Muted(Words.sg2faMust)
                    }
                }
                Text(Words.sgMyData).font(.headline)
                Muted(Words.sgMyDataWhy)
                MainButton(text: Words.sgMyDataGet, tonal: true) { myData() }
                if !note.isEmpty { Muted(note) }
            } else {
                Muted(Words.loading)
            }
        }
        .task(id: "\(auth.me?.id ?? "")#\(tick)") {
            let r = await Cloud.call("GET", "/security", nil, token: auth.token)
            data = r.ok ? Item(o: r.body) : nil
        }
    }

    private func act(_ what: String, _ body: [String: Any]) {
        guard !busy else { return }
        busy = true
        note = ""
        Task {
            let r = await Cloud.call("POST", "/security/\(what)", body, token: auth.token)
            busy = false
            if r.ok {
                if what == "2fa-start" { secret = r.body["secret"] as? String ?? "" }
                if what == "2fa-on" { secret = ""; note = Words.sg2faOn }
                if what == "end-all" { auth.logout() }
                tick += 1
            } else {
                note = r.error.isEmpty ? Words.tryAgain : r.error
            }
        }
    }

    private func myData() {
        guard !busy else { return }
        busy = true
        Task {
            let r = await Cloud.call("GET", "/my-data", nil, token: auth.token)
            busy = false
            if r.ok, let d = try? JSONSerialization.data(withJSONObject: r.body),
               let text = String(data: d, encoding: .utf8) {
                UIPasteboard.general.string = String(text.prefix(100_000))
                note = Words.sgMyDataReady
            } else {
                note = r.error.isEmpty ? Words.tryAgain : r.error
            }
        }
    }
}
