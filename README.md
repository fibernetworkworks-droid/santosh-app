# Santosh, the Android app

The phone app for **Santosh Core**. You chat or talk to Santosh in Hindi, Marathi, English and other Indian languages, and he does the work.

## What it does (daily-life pack 1)

| You say | Santosh does |
|---|---|
| "Kal subah 9 baje dawai yaad dilana" | Creates a reminder. Your phone notifies you even if the app is closed. |
| "Roz raat 10 baje paani peena yaad dilana" | Sets a repeating reminder (daily, weekdays, weekly or monthly) |
| "Subah 6 baje ka alarm lagao" | Sets a real alarm in your phone's Clock app |
| "10 minute ka timer" | Starts a timer in the Clock app |
| "Friday 4 baje doctor appointment, Ruby Hall" | Opens your Calendar with the event filled in (you tap Save), plus a reminder before it |
| "Yaad rakhna, car insurance 12 March ko khatam hai" | Remembers it and uses it later. He refuses passwords, OTPs, PINs and card numbers. |
| "Doodh aur bread shopping list mein daalo" | Lists you can tick off on the **Aaj** tab |
| "Pune ka mausam?" | Weather and rain chance |
| "Roz subah 7:30 briefing bhejna" | A morning summary every day: weather, today's reminders, open lists |
| WhatsApp campaigns | Everything from v0.1 (attach a leads file with the paperclip) |

Tap the mic and speak; Santosh replies aloud in your language (you can turn that off in Profile).

## Screens
- **Chat:** glass chat with live steps, campaign cards and the mic.
- **Aaj:** reminders (tap ✕ to cancel) and lists (tick items off).
- **Profile:** name, city, morning briefing time, language and voice, what Santosh remembers (you can delete any fact), server settings.

---

## Build the APK

### Option A: GitHub builds it for you (no setup on your PC)
1. Create a new **private** GitHub repository and push this `santosh_app` folder to it.
2. GitHub Actions runs `.github/workflows/build-apk.yml` automatically. That workflow generates the Android project, applies Santosh's settings, sets the app icon and builds the APK.
3. Open the repo's **Actions** tab, click the latest run, and download **santosh-apk**. Install `app-release.apk` on your phone (allow "install unknown apps").

### Option B: on your VPS or PC
You need the Flutter SDK (stable) and Android SDK / Android Studio, with Java 17.
```bash
cd santosh_app
flutter create --org com.newtika --project-name santosh --platforms android .
python3 tool/patch_android.py
flutter pub get
dart run flutter_launcher_icons
flutter build apk --release        # or: flutter run   (with a phone connected)
```
The APK is at `build/app/outputs/flutter-apk/app-release.apk`.

> I wrote this app without being able to compile it, because my workspace couldn't download Flutter. If the first build shows an error, it's most likely a plugin version. Run `flutter pub upgrade --major-versions` and build again, or send me the error and I'll fix it.

For the Play Store you'll later need your own signing key (`flutter build appbundle` with a keystore). The APK above uses the debug key, which is fine for testing.

## First run
1. Start Santosh Core (the backend) and note its address, for example `https://santosh.yourdomain.com` or `http://YOUR-VPS-IP:8077` for testing.
2. Open the app, pick your language, enter your name, the server address and the `API_KEY` from the server's `.env`.
3. Allow notifications and the microphone when Android asks.

## How phone actions work
The backend can't touch your phone, so for alarms, timers and calendar entries Santosh sends the phone a **device action**. The app runs it with Android's standard Clock and Calendar intents and reports back. If the app wasn't open within 15 minutes, Santosh tells you in the chat that it didn't reach the phone. Reminders are also stored on the phone, so they pop up without internet.
