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
  static Future<bool> running() async => await _call<bool>('isRunning') ?? false;
  static Future<String> status() async => await _call<String>('status') ?? '';

  /// True only for the first caller, so the app and the service never run the same phone action twice.
  /// When the native side is missing it returns true (the app is then the only one running actions).
  static Future<bool> claim(String id) async => await _call<bool>('claim', {'id': id}) ?? true;

  static Future<bool> batteryOptimized() async => await _call<bool>('batteryOptimized') ?? false;
  static Future<void> askBattery() async => _call('askBattery');
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
}
