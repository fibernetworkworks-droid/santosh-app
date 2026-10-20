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
  static Future<void> openMakerPerms() async => _call('openMakerPerms');
  /// v0.57 reel scroll analysis (Android Usage Access: times only, never screen content).
  static Future<bool> usageAllowed() async => await _call<bool>('usageAllowed') ?? false;
  static Future<void> usageSettings() async => _call('usageSettings');
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
