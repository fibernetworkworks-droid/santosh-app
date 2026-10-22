import 'package:android_intent_plus/android_intent.dart';
import 'package:android_intent_plus/flag.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;
import 'package:url_launcher/url_launcher.dart';

import 'nav.dart';

/// Everything that has to happen on the phone itself: notifications, alarms, timers, calendar.
class Device {
  Device._();
  static final Device instance = Device._();

  final FlutterLocalNotificationsPlugin _notes = FlutterLocalNotificationsPlugin();
  bool _ready = false;

  static const _channel = AndroidNotificationDetails(
    'santosh_reminders',
    'Hoola reminders',
    channelDescription: 'Reminders and updates from Hoola',
    importance: Importance.high,
    priority: Priority.high,
  );

  Future<void> init() async {
    if (_ready) return;
    tzdata.initializeTimeZones();
    try {
      tz.setLocalLocation(tz.getLocation(await FlutterTimezone.getLocalTimezone()));
    } catch (_) {
      tz.setLocalLocation(tz.getLocation('Asia/Kolkata'));
    }
    await _notes.initialize(const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')));
    _ready = true;
  }

  Future<void> askNotificationPermission() async {
    await _notes
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
  }

  int _idFor(String s) => s.hashCode & 0x7fffffff;

  /// Show something right now (e.g. a Santosh update while the app is in the background).
  Future<void> showNow(String title, String body) async {
    await init();
    await _notes.show(DateTime.now().millisecondsSinceEpoch & 0x7fffffff, title, body,
        const NotificationDetails(android: _channel));
  }

  /// Keep the phone's scheduled notifications in sync with the reminders on the server,
  /// so they still pop up when the app is closed or offline.
  Future<void> syncReminders(List<Map<String, dynamic>> reminders) async {
    await init();
    final pending = await _notes.pendingNotificationRequests();
    final keep = <int>{};
    for (final r in reminders.take(60)) {
      final due = DateTime.tryParse(r['due_at'] as String? ?? '');
      if (due == null || due.isBefore(DateTime.now())) continue;
      final id = _idFor(r['id'] as String);
      keep.add(id);
      await _notes.zonedSchedule(
        id,
        'Hoola',
        'Yaad dila raha hoon: ${r['text']}',
        tz.TZDateTime.from(due, tz.local),
        const NotificationDetails(android: _channel),
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
      );
    }
    for (final p in pending) {
      if (!keep.contains(p.id)) await _notes.cancel(p.id);
    }
  }

  /// Runs one action from Santosh. Returns null on success, or a short reason on failure.
  Future<String?> run(Map<String, dynamic> a) async {
    try {
      switch (a['type']) {
        case 'set_alarm':
          return await _alarm(a);
        case 'set_timer':
          await _launch(AndroidIntent(
            action: 'android.intent.action.SET_TIMER',
            arguments: <String, dynamic>{
              'android.intent.extra.alarm.LENGTH': (a['seconds'] as num).toInt(),
              'android.intent.extra.alarm.MESSAGE': a['label'] ?? 'Hoola timer',
              'android.intent.extra.alarm.SKIP_UI': true,
            },
            flags: const <int>[Flag.FLAG_ACTIVITY_NEW_TASK],
          ));
          return null;
        case 'add_calendar_event':
          await _launch(AndroidIntent(
            action: 'android.intent.action.INSERT',
            data: 'content://com.android.calendar/events',
            flags: const <int>[Flag.FLAG_ACTIVITY_NEW_TASK],
            arguments: <String, dynamic>{
              'title': a['title'] ?? 'Hoola',
              // timestamps are > 2^31, so the platform channel sends them as Java longs as Android expects
              'beginTime': (a['start_ms'] as num).toInt(),
              'endTime': (a['end_ms'] as num).toInt(),
              'eventLocation': a['location'] ?? '',
              'description': a['notes'] ?? '',
            },
          ));
          return null;
        case 'tv_play':
          // Hoola TV: the channel opens in Hoola's own player
          final ch = a['channel'] as String? ?? '';
          if (ch.isEmpty) return 'Channel nahi mila';
          return await openTv(ch) ? null : 'Hoola app kholiye, channel wahan chalega';
        case 'youtube_play':
          // v0.125 straight into the YouTube app (never Hoola's in-app browser), the web page only if YouTube is missing
          final vid = a['video_id'] as String? ?? '';
          final web = Uri.tryParse(a['url'] as String? ?? '');
          if (vid.isNotEmpty) {
            try {
              if (await launchUrl(Uri.parse('vnd.youtube:$vid'), mode: LaunchMode.externalNonBrowserApplication)) return null;
            } catch (_) {}
          }
          if (web == null || !web.hasScheme) return 'YouTube link sahi nahi hai';
          try {
            if (await launchUrl(web, mode: LaunchMode.externalNonBrowserApplication)) return null;
          } catch (_) {}
          return await launchUrl(web, mode: LaunchMode.externalApplication) ? null : 'YouTube phone par nahi khul paya';
        case 'open_url':
          final uri = Uri.tryParse(a['url'] as String? ?? '');
          if (uri == null || !uri.hasScheme) return 'Link sahi nahi hai';
          // inside Santosh's own browser when the app is open; another app for tel:, upi: etc.
          if (await openInApp(uri.toString(), title: a['title'] as String?)) return null;
          final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
          return ok ? null : 'Is link ko kholne wala app phone par nahi mila';
        default:
          return 'This app version does not know "${a['type']}" yet; please update the app.';
      }
    } catch (e) {
      return e.toString();
    }
  }

  Future<String?> _alarm(Map<String, dynamic> a) async {
    const dayNums = {'sun': 1, 'mon': 2, 'tue': 3, 'wed': 4, 'thu': 5, 'fri': 6, 'sat': 7}; // java.util.Calendar
    final days = ((a['days'] as List?) ?? const []).map((d) => dayNums[d]).whereType<int>().toList();
    final base = <String, dynamic>{
      'android.intent.extra.alarm.HOUR': (a['hour'] as num).toInt(),
      'android.intent.extra.alarm.MINUTES': (a['minute'] as num).toInt(),
      'android.intent.extra.alarm.MESSAGE': a['label'] ?? 'Hoola alarm',
      'android.intent.extra.alarm.SKIP_UI': true,
    };
    if (days.isNotEmpty) {
      try {
        await _launch(AndroidIntent(
          action: 'android.intent.action.SET_ALARM',
          arguments: {...base, 'android.intent.extra.alarm.DAYS': days},
          flags: const [Flag.FLAG_ACTIVITY_NEW_TASK],
        ));
        return null;
      } catch (_) {
        // some clock apps reject the repeat list; fall back to a one-time alarm below
      }
    }
    await _launch(AndroidIntent(
        action: 'android.intent.action.SET_ALARM', arguments: base, flags: const [Flag.FLAG_ACTIVITY_NEW_TASK]));
    return null;
  }

  Future<void> _launch(AndroidIntent intent) async {
    final can = await intent.canResolveActivity() ?? false;
    if (!can) throw 'No app on this phone can handle it (clock or calendar app missing)';
    await intent.launch();
  }
}
