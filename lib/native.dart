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
  static Future<bool> hasCalendar() async => await _call<bool>('hasCalendar') ?? false;
  static Future<void> askCalendar() async => _call('askCalendar');
}
