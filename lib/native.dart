import 'dart:convert';

import 'package:flutter/services.dart';

/// Bridge to the Kotlin side (background service, own alarms, calendar, battery settings).
class Native {
  static const _ch = MethodChannel('santosh/native');

  static Future<T?> _call<T>(String m, [Map<String, dynamic>? a]) async {
    try {
      return await _ch.invokeMethod<T>(m, a);
    } catch (_) {
      return null; // not on Android, or an old native side
    }
  }

  /// Start (or refresh) background mode. [after] = last event id the app has already shown.
  static Future<bool> start({required String server, required String key, required String conv, required int after}) async =>
      await _call<bool>('startService', {'server': server, 'key': key, 'conv': conv, 'after': after}) ?? false;
  static Future<void> stop() async => _call('stopService');
  /// v0.49 shrink a phone video to fit [mb] MB (Android's own encoder). {path} or {error}.
  static Future<Map<String, dynamic>> compressVideo(String path, {int mb = 24, int clipMs = 0}) async =>
      Map<String, dynamic>.from(await _call<Map>('compressVideo', {'path': path, 'mb': mb, 'clipMs': clipMs}) ?? {'error': 'is phone par nahi ho sakta'});
  /// 0..100 while a video is being made smaller, -1 when none is.
  static Future<int> compressProgress() async => await _call<int>('compressProgress') ?? -1;
  static Future<void> compressCancel() async => _call('compressCancel');
  /// v0.56 What Android knows about Hoola in the background (battery saver, restricted, standby bucket, last exits).
  static Future<Map<String, dynamic>> bgHealth() async {
    final m = await _call<Map>('bgHealth');
    return m == null ? <String, dynamic>{} : Map<String, dynamic>.from(m);
  }
  static Future<void> openMakerBattery() async => _call('openMakerBattery');
  /// v0.83 wait for the next OTP SMS: Android shows its own one-tap "Allow" sheet; only the code comes back
  /// ({code} or {error: denied | timeout | bank | no_code | unavailable | cancelled}).
  static Future<Map<String, dynamic>> otpConsent({int digits = 0}) async {
    final m = await _call<Map>('otpConsent', {'digits': digits});
    return m == null ? <String, dynamic>{'error': 'unavailable'} : Map<String, dynamic>.from(m);
  }
  static Future<void> otpConsentCancel() async => _call('otpConsentCancel');
  // ---- v0.62 Phone mein Hoola ----
  static Future<Map<String, dynamic>> _map(String m, [Map<String, dynamic>? a]) async {
    final r = await _call<Map>(m, a);
    return r == null ? <String, dynamic>{} : Map<String, dynamic>.from(r);
  }
  static Future<Map<String, dynamic>> assistInfo() => _map('assistInfo');
  static Future<void> assistSettings() async => _call('assistSettings');
  static Future<void> chatLink(String server, String key, String conv) async =>
      _call('chatLink', {'server': server, 'key': key, 'conv': conv});
  static Future<Map<String, dynamic>> bubble(bool on, String name) => _map('bubble', {'on': on, 'name': name});
  static Future<Map<String, dynamic>> bubbleInfo() => _map('bubbleInfo');
  static Future<void> bubbleSettings() async => _call('bubbleSettings');
  static Future<int> widgetUpdate({String? name, String? last, String? next}) async =>
      await _call<int>('widgetUpdate', {'name': name, 'last': last, 'next': next}) ?? 0;
  static Future<bool> widgetPin() async => await _call<bool>('widgetPin') ?? false;
  static Future<int> widgetCount() async => await _call<int>('widgetCount') ?? 0;
  static Future<Map<String, dynamic>> updateInfo() => _map('updateInfo');
  static Future<Map<String, dynamic>> updateDownload(String url, String sha256, int size) =>
      _map('updateDownload', {'url': url, 'sha256': sha256, 'size': size});
  static Future<int> updateProgress() async => await _call<int>('updateProgress') ?? -1;
  static Future<void> updateCancel() async => _call('updateCancel');
  /// null = Android's installer is asking the owner; 'permission' = she must allow "install unknown apps" first.
  static Future<String?> updateInstall(String path) async => _call<String>('updateInstall', {'path': path});
  static Future<void> updatePermission() async => _call('updatePermission');
  static Future<void> openMakerPerms() async => _call('openMakerPerms');
  /// v0.57 reel scroll analysis (Android Usage Access: times only, never screen content).
  // v0.84 Galla: UPI payment alerts (only after she gives notification access in Android settings)
  static Future<Map<String, dynamic>> payAlertsInfo() async {
    final r = await _call<Map>('payAlertsInfo');
    return r == null ? <String, dynamic>{} : Map<String, dynamic>.from(r);
  }

  static Future<void> payAlertsSettings() async => _call('payAlertsSettings');
  static Future<Map<String, dynamic>> payAlertsSet(bool on, List<String> apps) async {
    final r = await _call<Map>('payAlertsSet', {'on': on, 'apps': apps});
    return r == null ? <String, dynamic>{} : Map<String, dynamic>.from(r);
  }

  // v0.97 fingerprint-signed approvals: a key in Android Keystore that signs only after her fingerprint
  static Future<Map<String, dynamic>> approveKeyInfo() async {
    final r = await _call<Map>('approveKeyInfo');
    return r == null ? <String, dynamic>{'supported': false} : Map<String, dynamic>.from(r);
  }

  static Future<Map<String, dynamic>> approveKeyCreate() async {
    final r = await _call<Map>('approveKeyCreate');
    return r == null ? <String, dynamic>{'error': 'not_supported'} : Map<String, dynamic>.from(r);
  }

  static Future<bool> approveKeyDelete() async => await _call<bool>('approveKeyDelete') ?? false;

  /// Shows the fingerprint sheet with [title] / [subtitle]; {signature, device_id} or {error}.
  static Future<Map<String, dynamic>> approveKeySign(String message, String title, String subtitle) async {
    final r = await _call<Map>('approveKeySign', {'message': message, 'title': title, 'subtitle': subtitle});
    return r == null ? <String, dynamic>{'error': 'not_supported'} : Map<String, dynamic>.from(r);
  }

  // v0.90 Phone Doctor: what the phone says about itself, and opening the right Android settings screen
  static Future<Map<String, dynamic>> phoneCheck() async {
    final r = await _call<Map>('phoneCheck');
    return r == null ? <String, dynamic>{} : Map<String, dynamic>.from(r);
  }

  static Future<bool> openSetting(String key, {String package = ''}) async =>
      await _call<bool>('openSetting', {'key': key, 'package': package}) ?? false;

  static Future<bool> usageAllowed() async => await _call<bool>('usageAllowed') ?? false;
  static Future<void> usageSettings() async => _call('usageSettings');
  /// v0.69 why Hoola closed last time (null if it didn't crash). Marks it as reported.
  static Future<Map<String, dynamic>?> lastCrash() async {
    final m = await _call<Map>('lastCrash');
    return m == null ? null : Map<String, dynamic>.from(m);
  }
  /// v0.69 safe voice mode (after a crash in a call): no on-device VAD, no call service. [on] null = just read it.
  static Future<bool> safeVoice({bool? on}) async => await _call<bool>('safeVoice', {if (on != null) 'on': on}) ?? false;
  /// v0.63 Hoola Motion: share a file from the app cache (Android share sheet) / save a video to the gallery.
  /// Both return null when fine, else the reason.
  static Future<String?> shareFile(String path, {String mime = 'video/mp4', String title = 'Share'}) async =>
      _call<String>('shareFile', {'path': path, 'mime': mime, 'title': title});
  static Future<String?> saveVideo(String path, String name) async {
    try {
      return await _ch.invokeMethod<String>('saveVideo', {'path': path, 'name': name});
    } catch (_) {
      return 'Is phone par save nahi ho saka';
    }
  }
  /// v0.118 Brand Sahayak: a final poster into the gallery (Pictures/Hoola). null = saved, else the reason.
  static Future<String?> saveImage(String path, String name) async {
    try {
      return await _ch.invokeMethod<String>('saveImage', {'path': path, 'name': name});
    } catch (_) {
      return 'Is phone par save nahi ho saka';
    }
  }
  /// v0.58 background reel alerts: daily limit (minutes, 0 = off) and the after-11-pm bedtime nudge.
  static Future<Map<String, dynamic>> scrollAlerts({int? budget, bool? bedtime, int? ytShortsPct}) async => Map<String, dynamic>.from(
      await _call<Map>('scrollAlerts', {
            if (budget != null) 'budget': budget,
            if (bedtime != null) 'bedtime': bedtime,
            if (ytShortsPct != null) 'ytShortsPct': ytShortsPct,
          }) ??
          {});
  static Future<Map<String, dynamic>> scrollAlertState() async => Map<String, dynamic>.from(await _call<Map>('scrollAlertState') ?? {});
  static Future<List<Map<String, dynamic>>> usageDays({int days = 7}) async {
    final r = await _call<List>('usageDays', {'days': days});
    return r == null ? [] : r.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }
  static Future<bool> running() async => await _call<bool>('isRunning') ?? false;
  static Future<String> status() async => await _call<String>('status') ?? '';

  /// True only for the first caller, so the app and the service never run the same phone action twice.
  /// When the native side is missing it returns true (the app is then the only one running actions).
  static Future<bool> claim(String id) async => await _call<bool>('claim', {'id': id}) ?? true;

  static Future<bool> batteryOptimized() async => await _call<bool>('batteryOptimized') ?? false;
  static Future<void> askBattery() async => _call('askBattery');
  static Future<Map<String, dynamic>> callStatus() async {
    final m = await _call<Map>('callStatus');
    return m == null ? <String, dynamic>{} : Map<String, dynamic>.from(m);
  }

  static Future<void> openAutostart() async => _call('openAutostart');
  static Future<void> openNotificationSettings() async => _call('openNotificationSettings');
  static Future<String?> pushInit(String server, String key) async => _call<String>('pushInit', {'server': server, 'key': key});
  static Future<bool> exactAlarms() async => await _call<bool>('exactAlarms') ?? true;
  static Future<void> askExactAlarms() async => _call('askExactAlarms');
  /// Open a UPI payment / app link / app (from a user tap). Returns "ok" or a short reason.
  static Future<String> openExternal({String url = '', String package = ''}) async =>
      await _call<String>('openExternal', {'url': url, 'package': package}) ?? 'Is phone par nahi khul sakta';
  /// v0.109 Which of these app packages are installed on this phone (Roz ke kaam ticks).
  static Future<Set<String>?> installedApps(List<String> packages) async {
    final r = await _call<List>('installedApps', {'packages': packages});
    return r == null ? null : r.map((e) => '$e').toSet();
  }
  // ---- "Hey Santosh" wake word + lock screen ----
  /// Returns "ok", or "permission" when the mic permission prompt was shown.
  static Future<String> wakeStart() async => await _call<String>('wakeStart') ?? 'unsupported';
  static Future<void> wakeStop() async => _call('wakeStop');
  static Future<void> wakePause() async => _call('wakePause');
  static Future<void> wakeResume() async => _call('wakeResume');
  static Future<Map<String, dynamic>> wakeStatus() async =>
      Map<String, dynamic>.from(await _call<Map>('wakeStatus') ?? const {'on': false, 'wanted': false, 'status': ''});
  static Future<bool> isLocked() async => await _call<bool>('isLocked') ?? false;
  /// Asks for the phone's PIN / fingerprint. true = unlocked.
  static Future<bool> requestUnlock() async => await _call<bool>('requestUnlock') ?? true;
  static Future<void> leaveLockScreen() async => _call('leaveLockScreen');

  static Future<bool> hasLocation() async => await _call<bool>('hasLocation') ?? false;
  static Future<void> askLocation() async => _call('askLocation');
  /// {lat, lng, accuracy, time} or null (no permission / no fix).
  static Future<Map<String, dynamic>?> location() async {
    final m = await _call<Map>('location');
    return m == null ? null : Map<String, dynamic>.from(m);
  }
  static Future<bool> hasCalendar() async => await _call<bool>('hasCalendar') ?? false;
  static Future<void> askCalendar() async => _call('askCalendar');

  // ---- Ghar: home devices (IR blaster, Bluetooth TV remote, DIAL, music) ----
  /// {ir, bluetooth, bluetooth_on, tv_remote, bt_permission, remote_on}
  static Future<Map<String, dynamic>> homeCaps() async =>
      Map<String, dynamic>.from(await _call<Map>('homeCaps') ?? const {'ir': false, 'bluetooth': false, 'tv_remote': false});
  /// Paired Bluetooth devices [{name, address, tv_like}], TVs first.
  static Future<List<Map<String, dynamic>>> homePaired() async =>
      ((await _call<List>('homePaired')) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  /// Asks for "Nearby devices" (Android 12+). Returns true when already allowed.
  static Future<bool> homeAskBluetooth() async => await _call<bool>('homeAskBluetooth') ?? false;
  /// Turns the "Santosh Remote" Bluetooth TV remote on/off. "ok", "permission" or a reason.
  static Future<String> homeRemote(bool on) async => await _call<String>('homeRemote', {'on': on}) ?? 'Is phone par nahi chalta';
  static Future<String> homeDiscoverable() async => await _call<String>('homeDiscoverable') ?? 'Is phone par nahi chalta';
  /// A Bluetooth job (status, devices, scan, pair, connect, disconnect, tv_pair, turn_on, settings).
  /// Returns {ok, result, error}; error "permission" = Nearby devices not allowed (the prompt is shown).
  static Future<Map<String, dynamic>> btRun(String action, [Map<String, dynamic> args = const {}]) async {
    final r = await _call<Map>('btRun', {'action': action, 'args': jsonEncode(args)});
    if (r == null) return {'ok': false, 'result': <String, dynamic>{}, 'error': 'Is phone par Bluetooth nahi chalta'};
    return {
      'ok': r['ok'] == true,
      'result': _deep(r['result']),
      'error': r['error'] as String? ?? '',
    };
  }

  static Map<String, dynamic> _deep(dynamic m) => m is Map
      ? m.map((k, v) => MapEntry(k.toString(), v is Map ? _deep(v) : v is List ? v.map((e) => e is Map ? _deep(e) : e).toList() : v))
      : <String, dynamic>{};
  /// Runs one server-built device command. Returns "ok" or a short reason ("permission" = Nearby devices not allowed).
  static Future<String> homeRun(Map<String, dynamic> action) async =>
      await _call<String>('homeRun', {'action': jsonEncode(action)}) ?? 'Is phone par home devices nahi chalte';
}
