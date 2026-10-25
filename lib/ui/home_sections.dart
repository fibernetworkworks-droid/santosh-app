/// v0.163 Hoola Home — the coworker sections: Kaam ki Haalat (live jobs), Aaj ka Din tiles,
/// Hoola Employee, Hoola Network, Hoola Notebook, Aaj Kya Seekha, Hoola ne Kiya (recap) and the
/// partner footer. Every section loads softly: one API failing hides only that section, never breaks home.
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'catchup_screen.dart';
import 'employee_screen.dart';
import 'glass.dart';
import 'hoola_net_screen.dart';
import 'notebook_screen.dart';
import 'voice_learned_screen.dart';

const _videoActive = {'queued', 'watching', 'planning', 'rendering', 'checking'};

List<Map<String, dynamic>> _list(Object? o) =>
    List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

int _n(Object? v) => v is num ? v.toInt() : 0;
String _s(Object? v) => '${v ?? ''}';

/// One loader for everything the coworker sections need. 11 soft calls, ~parallel; failures stay null.
class HomeExtra {
  Map<String, dynamic>? employee;            // /api/employee → status (+ first pending ask)
  List<Map<String, dynamic>> jobs = [];      // video studio jobs actually running right now
  Map<String, dynamic>? netCounts;           // /api/net/inbox → counts (connections, requests, inbox)
  int netThreads = 0, netGroups = 0;
  List<Map<String, dynamic>> notebooks = []; // latest 5, for the strip
  List<Map<String, dynamic>> factsToday = [];// memory facts added today
  List<Map<String, dynamic>> lessons = [];   // Hoola Network lessons (latest 2)
  List<Map<String, dynamic>> words = [];     // her own words (latest 2)
  Map<String, dynamic>? catchup;             // /api/catchup 24h → items, count
  Map<String, dynamic>? day;                 // v0.166 /api/day → weather, aaj ki baaki meetings, next reminder
  bool loaded = false;

  static Future<dynamic> _soft(Future<dynamic> f) async {
    try {
      return await f.timeout(const Duration(seconds: 10));
    } catch (_) {
      return null;   // a dead endpoint hides its section; home stays warm
    }
  }

  Future<void> load(Santosh app) async {
    final api = app.api;
    if (api == null) return;
    final dayAgo = DateTime.now().toUtc().subtract(const Duration(hours: 24));
    final r = await Future.wait<dynamic>([
      _soft(api.employee()), _soft(api.videoJobs()), _soft(api.netInbox()),
      _soft(api.netThreads()), _soft(api.netGroups()), _soft(api.notebooks()),
      _soft(api.memory()), _soft(api.voiceLearned()), _soft(api.netLearned()),
      _soft(api.catchup(dayAgo)), _soft(api.day()),
    ]);
    try {
      final emp = r[0] as Map<String, dynamic>?;
      final status = (emp?['status'] as Map?)?.cast<String, dynamic>();
      if (status != null && status['set_up'] == true) {
        employee = {'status': status, 'asks': _list(emp?['asks']).take(1).toList()};
      } else {
        employee = null;
      }
      jobs = _list((r[1] as Map?)?['jobs']).where((j) => _videoActive.contains(j['status'])).take(2).toList();

      final inbox = r[2] as Map<String, dynamic>?;
      netCounts = (inbox?['counts'] as Map?)?.cast<String, dynamic>();
      netThreads = _list(r[3]).length;   // netThreads() returns the thread list unwrapped
      netGroups = _list(r[4]).length;

      notebooks = _list(r[5]).take(5).toList();   // notebooks() returns the list unwrapped

      final now = DateTime.now();
      factsToday = _list(r[6]).where((f) {   // memory() returns the facts list unwrapped
        final t = DateTime.tryParse(_s(f['created_at']).replaceFirst('Z', ''))?.toLocal();
        return t != null && t.year == now.year && t.month == now.month && t.day == now.day;
      }).take(3).toList();

      lessons = _list((r[8] as Map?)?['lessons']).take(2).toList();
      words = _list((r[7] as Map?)?['words']).take(2).toList();

      catchup = r[9] as Map<String, dynamic>?;
      day = r[10] as Map<String, dynamic>?;
    } catch (_) {/* never let one odd payload break the home */}
    loaded = true;
  }

  int get catchupCount => catchup == null ? 0 : _list(catchup!['items']).length;
  bool get nothingNew =>
      employee == null && jobs.isEmpty && notebooks.isEmpty && factsToday.isEmpty && lessons.isEmpty && words.isEmpty && catchupCount == 0;
}

/// Section caption with optional NAYA pill and count.
class HomeLabel extends StatelessWidget {
  const HomeLabel(this.text, {super.key, this.isNew = false, this.count, this.trailing});
  final String text;
  final bool isNew;
  final int? count;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8, left: 4),
        child: Row(children: [
          Text(text, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.3, color: C.muted)),
          if (isNew) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x6634D399))),
              child: const Text('NAYA', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 1, color: C.ok)),
            ),
          ],
          if (count != null) ...[
            const SizedBox(width: 6),
            Text('· $count', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: C.muted)),
          ],
          if (trailing != null) ...[
            const SizedBox(width: 8),
            trailing!,
          ],
        ]),
      );
}

/// Small gradient progress bar.
class HomeBar extends StatelessWidget {
  const HomeBar(this.value, {super.key, this.color});
  final double value;               // 0..1
  final Gradient? color;
  @override
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: BorderRadius.circular(999),
        child: Container(
          height: 6,
          color: C.panel,
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: value.clamp(0.0, 1.0),
            child: Container(decoration: BoxDecoration(gradient: color ?? C.gradient)),
          ),
        ),
      );
}

IconData _stageIcon(String platform) {
  switch (platform) {
    case 'reel':
      return Icons.movie_creation_rounded;
    case 'short':
    case 'video':
      return Icons.videocam_rounded;
    default:
      return Icons.auto_awesome_motion_rounded;
  }
}

/// KAAM KI HAALAT — what Hoola is making right now (video studio jobs with live progress).
class LiveWorkSection extends StatelessWidget {
  const LiveWorkSection({super.key, required this.jobs});
  final List<Map<String, dynamic>> jobs;
  @override
  Widget build(BuildContext context) {
    if (jobs.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel('KAAM KI HAALAT', trailing: Row(children: [
        Container(width: 8, height: 8, decoration: const BoxDecoration(color: C.ok, shape: BoxShape.circle)),
        const SizedBox(width: 5),
        Text('${jobs.length} chal rahe hain', style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: C.ok)),
      ])),
      for (final j in jobs)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Glass(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(_stageIcon(_s(j['platform'])), size: 17, color: C.accentSoft),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(_s(j['title']).isEmpty ? _s(j['brief']).split('\n').first : _s(j['title']),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                ),
                Text('${_n(j['progress'])}%', style: display(14, color: C.accentSoft)),
              ]),
              if (_s(j['stage']).isNotEmpty) ...[
                const SizedBox(height: 3),
                Text(_s(j['stage']), style: const TextStyle(fontSize: 12, color: C.muted)),
              ],
              const SizedBox(height: 9),
              HomeBar(_n(j['progress']) / 100),
            ]),
          ),
        ),
    ]);
  }
}

/// AAJ KA DIN — one premium card: mausam band (icon, temp, hi/lo, rain chip, day progress),
/// aaj ki baaki meetings with countdown, agla reminder, and away-catchup. v0.166.
class DayTilesSection extends StatelessWidget {
  const DayTilesSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;

  static const _repeat = {'none': 'Ek baar', 'hourly': 'Har ghante', 'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};

  static String wIconFor(int? code, bool isDay) {
    if (code == null) return '🌤️';
    if (code <= 1) return isDay ? '☀️' : '🌙';
    if (code == 2) return isDay ? '⛅' : '☁️';
    if (code == 3) return '☁️';
    if (code == 45 || code == 48) return '🌫️';
    if (code >= 51 && code <= 55) return '🌦️';
    if (code >= 61 && code <= 65) return '🌧️';
    if (code >= 71 && code <= 77) return '🌨️';
    if (code >= 80 && code <= 82) return '🌧️';
    if (code >= 95) return '⛈️';
    return '🌤️';
  }

  /// Dark-glass-compatible tint for the band, keyed to the condition.
  static List<Color> _wTint(int? code, bool isDay) {
    if (code == null) return const [Color(0x1AFFFFFF), Color(0x05FFFFFF)];
    if (code <= 1) return isDay ? const [Color(0x2EFFB15C), Color(0x0AFFB15C)] : const [Color(0x2E7C5CFF), Color(0x0A7C5CFF)];
    if (code == 2 || code == 3) return const [Color(0x2494A3B8), Color(0x0894A3B8)];
    if (code == 45 || code == 48) return const [Color(0x249CA3AF), Color(0x089CA3AF)];
    if ((code >= 51 && code <= 65) || (code >= 80 && code <= 82)) return const [Color(0x2E60A5FA), Color(0x0A60A5FA)];
    if (code >= 71 && code <= 77) return const [Color(0x2EBAE6FD), Color(0x0ABAE6FD)];
    if (code >= 95) return const [Color(0x2EA78BFA), Color(0x0AA78BFA)];
    return const [Color(0x1AFFFFFF), Color(0x05FFFFFF)];
  }

  /// "aaj 4:30 PM" → "4:30 PM".
  static String _time(String when) {
    final p = when.split(' ');
    return p.length >= 3 ? p.sublist(p.length - 2).join(' ') : when;
  }

  static String _inMins(int? m, bool running) {
    if (running) return 'Abhi chal rahi hai';
    if (m == null) return '';
    if (m < 1) return 'Ab shuru hone wali';
    if (m < 60) return '$m min mein';
    if (m < 1440) return '${(m / 60).round()} ghante mein';
    return 'Aaj baad mein';
  }

  Widget _wchip(String emoji, String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x1FFFFFFF))),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(emoji, style: const TextStyle(fontSize: 11)),
          const SizedBox(width: 5),
          Text(text, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: C.chip)),
        ]),
      );

  Widget _divider() => Container(height: 1, margin: const EdgeInsets.only(left: 61), color: C.line);

  Widget _drow(IconData ic, Color bg, Color icc, String title, String detail,
      {String? time, bool running = false, bool chevron = false, VoidCallback? onTap}) {
    final row = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(children: [
        Container(width: 34, height: 34, alignment: Alignment.center,
            decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(11)), child: Icon(ic, size: 18, color: icc)),
        const SizedBox(width: 11),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              if (running) ...[
                Container(width: 7, height: 7, decoration: const BoxDecoration(color: C.ok, shape: BoxShape.circle)),
                const SizedBox(width: 6),
              ],
              Expanded(child: Text(title, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800),
                  maxLines: 1, overflow: TextOverflow.ellipsis)),
            ]),
            if (detail.isNotEmpty) ...[
              const SizedBox(height: 2),
              Text(detail, style: const TextStyle(fontSize: 11.5, color: C.muted), maxLines: 1, overflow: TextOverflow.ellipsis),
            ],
          ]),
        ),
        if (time != null && time.isNotEmpty) ...[
          const SizedBox(width: 8),
          Text(time, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: running ? C.ok : C.accentSoft)),
        ],
        if (chevron) ...[
          const SizedBox(width: 2),
          const Icon(Icons.chevron_right_rounded, size: 20, color: C.muted),
        ],
      ]),
    );
    return onTap == null ? row : Press(onTap: onTap, child: row);
  }

  @override
  Widget build(BuildContext context) {
    final day = extra.day;
    final w = day == null ? null : (day['weather'] as Map?)?.cast<String, dynamic>();
    final int? code = w == null || w['now_code'] is! num ? null : (w['now_code'] as num).toInt();
    final bool isDay = w != null && w['is_day'] is bool ? w['is_day'] as bool : true;
    final events = day == null ? <Map<String, dynamic>>[] : _list(day['events']);
    final rem = day == null ? null : (day['next_reminder'] as Map?)?.cast<String, dynamic>();
    final next = rem ?? (app.reminders.isEmpty ? null : app.reminders.first);
    final cu = extra.catchupCount;

    final now = DateTime.now();
    final dayStart = DateTime(now.year, now.month, now.day, 6);
    final dayEnd = DateTime(now.year, now.month, now.day, 23);
    final dayPct = ((now.millisecondsSinceEpoch - dayStart.millisecondsSinceEpoch) /
            (dayEnd.millisecondsSinceEpoch - dayStart.millisecondsSinceEpoch))
        .clamp(0.0, 1.0);

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const HomeLabel('AAJ KA DIN'),
      Glass(
        radius: 24,
        padding: EdgeInsets.zero,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // ---------- mausam band ----------
          if (w != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: _wTint(code, isDay), begin: Alignment.topLeft, end: Alignment.bottomRight),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Container(
                    width: 46, height: 46, alignment: Alignment.center,
                    decoration: BoxDecoration(color: const Color(0x1FFFFFFF), shape: BoxShape.circle, border: Border.all(color: const Color(0x22FFFFFF))),
                    child: Text(wIconFor(code, isDay), style: const TextStyle(fontSize: 23)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(w['now_c'] is num ? '${(w['now_c'] as num).round()}°' : '--°', style: display(30, w: FontWeight.w800)),
                        if (w['feels_c'] is num)
                          Padding(
                            padding: const EdgeInsets.only(left: 8, top: 9),
                            child: Text('Mehsus ${(w['feels_c'] as num).round()}°',
                                style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C.faint)),
                          ),
                      ]),
                      const SizedBox(height: 1),
                      Text(_s(w['now']).isEmpty ? 'Mausam' : _s(w['now']),
                          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: C.chip)),
                    ]),
                  ),
                  const SizedBox(width: 8),
                  Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text(_s(w['place']).split(',').first.toUpperCase(),
                        style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.faint)),
                    const SizedBox(height: 4),
                    Text('↑ ${w['today_max_c'] is num ? (w['today_max_c'] as num).round() : '--'}°  ·  ↓ ${w['today_min_c'] is num ? (w['today_min_c'] as num).round() : '--'}°',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: C.chip)),
                  ]),
                ]),
                if (w['rain_chance_pct'] is num || w['wind_kmph'] is num) ...[
                  const SizedBox(height: 10),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    if (w['rain_chance_pct'] is num) _wchip('💧', '${(w['rain_chance_pct'] as num).round()}% baarish'),
                    if (w['wind_kmph'] is num) _wchip('💨', '${(w['wind_kmph'] as num).round()} km/h hawa'),
                    if (w['humidity'] is num) _wchip('🌫️', '${(w['humidity'] as num).round()}% nami'),
                  ]),
                ],
                const SizedBox(height: 11),
                Row(children: [
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(99),
                      child: LinearProgressIndicator(value: dayPct, minHeight: 3.5,
                          backgroundColor: const Color(0x14FFFFFF), valueColor: const AlwaysStoppedAnimation<Color>(C.accent)),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text('Din ka ${(dayPct * 100).round()}%',
                      style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: C.faint)),
                ]),
              ]),
            )
          else if (day != null) // calendar/day loaded but no sheher set — invite, don't fake data
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(16, 13, 16, 13),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0x1AFFFFFF), Color(0x05FFFFFF)], begin: Alignment.topLeft, end: Alignment.bottomRight)),
              child: Row(children: [
                Container(width: 40, height: 40, alignment: Alignment.center,
                    decoration: BoxDecoration(color: const Color(0x1FFFFFFF), shape: BoxShape.circle, border: Border.all(color: const Color(0x22FFFFFF))),
                    child: const Text('🌤️', style: TextStyle(fontSize: 19))),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Mausam ke liye sheher chahiye', style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
                    SizedBox(height: 2),
                    Text('Profile mein apna sheher jodo — main roz mausam bataungi.', style: TextStyle(fontSize: 11.5, color: C.muted)),
                  ]),
                ),
              ]),
            ),
          // ---------- aaj ki baaki meetings ----------
          if (events.isEmpty)
            _drow(Icons.event_rounded, const Color(0x247C5CFF), const Color(0xFFA78BFA), 'Aaj koi meeting nahi',
                day == null ? '' : 'Calendar se sab main yaad rakhungi')
          else ...[
            for (var i = 0; i < events.length; i++) ...[
              if (i > 0) _divider(),
              _drow(Icons.event_rounded, const Color(0x247C5CFF), const Color(0xFFA78BFA), _s(events[i]['title']),
                  [
                    _inMins(events[i]['starts_in_mins'] is int ? events[i]['starts_in_mins'] as int : null, events[i]['running'] == true),
                    if (_s(events[i]['location']).isNotEmpty) _s(events[i]['location']),
                    if (events[i]['attendees'] is int && (events[i]['attendees'] as int) > 0) '${events[i]['attendees']} log',
                  ].where((x) => x.isNotEmpty).join(' · '),
                  time: _time(_s(events[i]['start'])), running: events[i]['running'] == true),
            ],
          ],
          // ---------- agla reminder ----------
          _divider(),
          if (next == null)
            _drow(Icons.notifications_active_outlined, const Color(0x24FFB15C), C.accentSoft, 'Aaj koi reminder nahi',
                'Boliye — "kal 9 baje dawai yaad dilana"')
          else
            _drow(Icons.notifications_active_outlined, const Color(0x24FFB15C), C.accentSoft, _s(next['text']),
                next['repeat'] is String && (next['repeat'] as String) != 'none'
                    ? 'Yaad dila dunga · ${_repeat[next['repeat']] ?? ''}'.trim()
                    : 'Yaad dila dunga',
                time: _time(_s(next['when']))),
          // ---------- away-catchup ----------
          if (cu > 0 && extra.catchup != null) ...[
            _divider(),
            _drow(Icons.history_rounded, const Color(0x242DD4BF), C.teal, 'Jab aap bahar thi', '$cu naye kaam — ek ek karke dikha dungi',
                chevron: true, onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CatchUpScreen(app: app, data: extra.catchup!)))),
          ],
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 11),
            child: Row(children: [
              const Icon(Icons.favorite_rounded, size: 10, color: C.faint),
              const SizedBox(width: 6),
              Expanded(child: Text('Main din bhar nazar rakhungi — aap nishchint rahiye.',
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600, color: C.faint))),
            ]),
          ),
        ]),
      ),
    ]);
  }
}

/// HOOLA EMPLOYEE — Hoola on duty at the owner's business: status, today's numbers, the one ask waiting.
class EmployeeSection extends StatelessWidget {
  const EmployeeSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final emp = extra.employee;
    final open = () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmployeeScreen(app: app)));
    // Employee mode never set up: a slim invitation instead of the full card.
    if (emp == null) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const HomeLabel('HOOLA EMPLOYEE', isNew: true),
        Press(
          onTap: open,
          child: Glass(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            child: Row(children: [
              Container(
                width: 40, height: 40,
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), gradient: const LinearGradient(colors: [Color(0xFF2DD4BF), Color(0xFF7C5CFF)])),
                child: const Icon(Icons.storefront_rounded, size: 20, color: C.onAccent),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Mujhe apni dukaan pe lagao', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
                  Text('Calls, appointments, hisaab — sab main sambhaalungi', style: TextStyle(fontSize: 12, color: C.muted)),
                ]),
              ),
              const Icon(Icons.chevron_right_rounded, color: C.muted),
            ]),
          ),
        ),
      ]);
    }
    final st = (emp['status'] as Map).cast<String, dynamic>();
    final paused = st['paused'] == true || st['enabled'] != true;
    final asks = _list(emp['asks']);
    final ask = asks.isEmpty ? null : asks.first;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const HomeLabel('HOOLA EMPLOYEE', isNew: true),
      Press(
        onTap: open,
        child: Glass(
          padding: const EdgeInsets.all(14),
          tint: const Color(0xFF2DD4BF),
          opacity: .05,
          border: const Color(0x475EEAD4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                width: 42, height: 42,
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), gradient: const LinearGradient(colors: [Color(0xFF2DD4BF), Color(0xFF7C5CFF)])),
                child: const Icon(Icons.storefront_rounded, size: 21, color: C.onAccent),
              ),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(st['business']).isEmpty ? 'Meri dukaan' : _s(st['business']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  Text(_s(st['role']).isEmpty ? 'Front desk' : _s(st['role']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
                ]),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: paused ? const Color(0x55FFC27A) : const Color(0x552DD4BF)),
                  color: paused ? const Color(0x1AFFC27A) : const Color(0x1A2DD4BF),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  if (!paused) Container(width: 6, height: 6, decoration: const BoxDecoration(color: C.ok, shape: BoxShape.circle)),
                  if (!paused) const SizedBox(width: 5),
                  Text(paused ? 'AARAAM' : 'ON DUTY', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: .5, color: paused ? C.warn : C.teal)),
                ]),
              ),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              _stat('${_n(st['done_today'])}', 'AAJ POORE'),
              const SizedBox(width: 8),
              _stat('${_n(st['pending_asks'])}', 'ASK WAIT', hot: _n(st['pending_asks']) > 0),
              const SizedBox(width: 8),
              _stat('${_n(st['team_tasks_waiting'])}', 'TEAM TASKS'),
            ]),
            if (ask != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x66FFB15C)), color: const Color(0x1AFFB15C)),
                child: Row(children: [
                  const Text('🙋', style: TextStyle(fontSize: 14)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('${_s(ask['why']).isEmpty ? 'Ek kaam aapki haan ka intezaar kar raha hai' : _s(ask['why'])}',
                        style: const TextStyle(fontSize: 12, height: 1.4), maxLines: 2, overflow: TextOverflow.ellipsis),
                  ),
                ]),
              ),
            ],
            const SizedBox(height: 10),
            Text(
              paused ? '"Jab bolo, phir duty pe aa jaungi."' : '"Dukaan pe sab main sambhaal rahi hoon — aap chinta mat karo."',
              style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0xCC5EEAD4)),
            ),
          ]),
        ),
      ),
    ]);
  }

  static Widget _stat(String n, String k, {bool hot = false}) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
          decoration: BoxDecoration(color: hot ? const Color(0x1AFFB15C) : C.panel, borderRadius: BorderRadius.circular(14),
              border: Border.all(color: hot ? const Color(0x55FFB15C) : Colors.white.withOpacity(.10))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(n, style: display(16, color: hot ? C.accentSoft : C.ink)),
            const SizedBox(height: 2),
            Text(k, style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.faint)),
          ]),
        ),
      );
}

/// HOOLA NETWORK — her avatars talk to other Hoolas: knocks, dost, baatein, mandali.
class NetworkSection extends StatelessWidget {
  const NetworkSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final c = extra.netCounts;
    if (c == null) return const SizedBox.shrink();
    final knocks = _n(c['inbox']);
    final dost = _n(c['connections']);
    if (knocks == 0 && dost == 0 && extra.netThreads == 0) return const SizedBox.shrink();
    final open = () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaNetScreen(app: app)));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const HomeLabel('HOOLA NETWORK', isNew: true),
      Press(
        onTap: open,
        child: Glass(
          padding: const EdgeInsets.all(14),
          tint: const Color(0xFF7C5CFF),
          opacity: .06,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                width: 42, height: 42,
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), gradient: const LinearGradient(colors: [Color(0xFF7C5CFF), Color(0xFFE0458B)])),
                child: const Icon(Icons.public_rounded, size: 21, color: C.onAccent),
              ),
              const SizedBox(width: 11),
              const Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Aapka Hoola, dusre Hoolas se mila', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  Text('Knocks, baatein, deals — sab khud sambhalti hoon', style: TextStyle(fontSize: 11.5, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              _stat('$knocks', 'KNOCK WAIT', hot: knocks > 0),
              const SizedBox(width: 8),
              _stat('$dost', 'DOST'),
              const SizedBox(width: 8),
              _stat('${extra.netThreads}', 'BAATEIN'),
              const SizedBox(width: 8),
              _stat('${extra.netGroups}', 'MANDALI'),
            ]),
            const SizedBox(height: 11),
            Container(
              height: 36,
              decoration: BoxDecoration(color: const Color(0x17FFFFFF), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x29FFFFFF))),
              alignment: Alignment.center,
              child: const Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.public_rounded, size: 16, color: C.chip),
                SizedBox(width: 7),
                Text('Network kholo — knocks, baatein, deals', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: C.chip)),
              ]),
            ),
          ]),
        ),
      ),
    ]);
  }

  static Widget _stat(String n, String k, {bool hot = false}) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 9),
          decoration: BoxDecoration(color: hot ? const Color(0x1AFFB15C) : C.panel, borderRadius: BorderRadius.circular(14),
              border: Border.all(color: hot ? const Color(0x55FFB15C) : Colors.white.withOpacity(.10))),
          child: Column(children: [
            Text(n, style: display(15, color: hot ? C.accentSoft : C.ink)),
            const SizedBox(height: 2),
            Text(k, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: .3, color: C.faint), maxLines: 1),
          ]),
        ),
      );
}

/// HOOLA NOTEBOOK — her notebooks strip: padho, poochho, studio.
class NotebookSection extends StatelessWidget {
  const NotebookSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    if (extra.notebooks.isEmpty) return const SizedBox.shrink();
    Widget tile(Map<String, dynamic> nb) {
      final color = nbColor(nb['color']);
      return Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: app, id: _s(nb['id'])))),
        child: Container(
          width: 132,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: Colors.white.withOpacity(.055), borderRadius: BorderRadius.circular(18), border: Border.all(color: Colors.white.withOpacity(.12))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(nb['emoji']).isEmpty ? '📓' : _s(nb['emoji']), style: const TextStyle(fontSize: 21)),
            const SizedBox(height: 7),
            Text(_s(nb['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, height: 1.25)),
            const SizedBox(height: 3),
            Text('${_n(nb['sources'])} sources · ${_n(nb['outputs'])} studio', style: const TextStyle(fontSize: 10.5, color: C.muted)),
            const SizedBox(height: 9),
            Container(height: 4, decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), gradient: LinearGradient(colors: [color, color.withOpacity(.35)]))),
          ]),
        ),
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const HomeLabel('HOOLA NOTEBOOK', isNew: true),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        clipBehavior: Clip.none,
        child: Row(children: [
          for (final nb in extra.notebooks) ...[
            tile(nb),
            const SizedBox(width: 10),
          ],
          Press(
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebooksScreen(app: app))),
            child: Container(
              width: 108,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), border: Border.all(color: Colors.white.withOpacity(.25), style: BorderStyle.solid, width: 1.2)),
              child: const Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(Icons.add_rounded, color: C.muted, size: 22),
                SizedBox(height: 4),
                Text('Naya notebook', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: C.muted)),
              ]),
            ),
          ),
        ]),
      ),
    ]);
  }
}

/// AAJ KYA SEEKHA — what Hoola learned today: today's memory facts, her words, network lessons.
/// One tap = bhool jao (trust keeps the partnership honest).
class _LearnLine {
  const _LearnLine(this.icon, this.text, this.src, this.forget);
  final IconData icon;
  final String text;
  final String src;
  final Future<void> Function() forget;
}

class LearnedSection extends StatelessWidget {
  const LearnedSection({super.key, required this.extra, required this.app, required this.reload});
  final HomeExtra extra;
  final Santosh app;
  final Future<void> Function() reload;

  List<_LearnLine> get _lines {
    final out = <_LearnLine>[];
    for (final f in extra.factsToday) {
      out.add(_LearnLine(Icons.psychology_alt_rounded, _s(f['text']), 'Aapki baaton se · aaj', () async {
        await app.api?.forget(_n(f['id']));
        await reload();
      }));
    }
    if (extra.words.isNotEmpty) {
      final terms = [for (final w in extra.words) _s(w['term'])].where((t) => t.isNotEmpty).join(', ');
      out.add(_LearnLine(Icons.record_voice_over_rounded, 'Aapke shabd: $terms', 'Aapki calls se seekhe shabd', () async {
        await app.api?.voiceWordRemove(_n(extra.words.first['id']));
        await reload();
      }));
    }
    for (final l in extra.lessons) {
      out.add(_LearnLine(Icons.school_rounded, _s(l['text']), 'Hoola Network · seekha', () async {
        await app.api?.netLessonAct('${l['id']}', 'forget');
        await reload();
      }));
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final lines = _lines;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel('AAJ KYA SEEKHA', isNew: true, trailing: Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VoiceLearnedScreen(app: app))),
        child: const Text('Sab dekho', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: C.violet)),
      )),
      Glass(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (lines.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text('Aaj kuch naya nahi seekha. Jitni baat karenge, utni behtar samjhungi. 💛',
                  style: TextStyle(fontSize: 13, height: 1.45, color: C.muted)),
            )
          else
            for (final l in lines)
              _line(l),
          const SizedBox(height: 6),
          const Text('"Jo na pasand ho, ek tap mein bhula do."', style: TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0xB3C4B5FF))),
        ]),
      ),
    ]);
  }

  Widget _line(_LearnLine l) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 32, height: 32,
            decoration: BoxDecoration(color: const Color(0x24C4B5FF), borderRadius: BorderRadius.circular(10)),
            child: Icon(l.icon, size: 15, color: const Color(0xFFC4B5FF)),
          ),
          const SizedBox(width: 11),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(l.text, style: const TextStyle(fontSize: 13, height: 1.45, color: C.ink)),
              const SizedBox(height: 2),
              Text(l.src, style: const TextStyle(fontSize: 10.5, color: C.faint)),
            ]),
          ),
          const SizedBox(width: 8),
          Press(
            onTap: () async {
              try {
                await l.forget();
              } catch (_) {}
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: Colors.white.withOpacity(.15))),
              child: const Text('Bhool jao', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C.faint)),
            ),
          ),
        ]),
      );
}

/// HOOLA NE KIYA — the 24-hour recap: her report of what she did while the owner was away.
class RecapSection extends StatelessWidget {
  const RecapSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final cu = extra.catchup;
    if (cu == null) return const SizedBox.shrink();
    final items = _list(cu['items']);
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const HomeLabel('HOOLA NE KIYA · PICHHLE 24 GHANTE'),
      Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CatchUpScreen(app: app, data: cu))),
        child: Glass(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${items.length} kaam poore kiye 👍', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
            const SizedBox(height: 4),
            for (final it in items.take(2))
              Padding(
                padding: const EdgeInsets.only(top: 3),
                child: Text('· ${_s(it['text'])}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12.5, height: 1.45, color: C.muted)),
              ),
            if (items.length > 2)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text('aur ${items.length - 2} kaam — tap karke sab dekho', style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: C.violet)),
              ),
          ]),
        ),
      ),
    ]);
  }
}

/// The partner line at the very bottom of home.
class PartnerFooter extends StatelessWidget {
  const PartnerFooter({super.key});
  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 6),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: Colors.white.withOpacity(.12)),
          gradient: const LinearGradient(colors: [Color(0x1AFF8A3D), Color(0x1AC86BFF)]),
        ),
        child: Column(children: [
          Text('Main yahin hoon — kabhi bhi, kahin bhi. 💛', textAlign: TextAlign.center,
              style: display(14, w: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text('Aapki har baat yaad hai, har kaam pe nazar hai.', textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11.5, color: C.muted)),
        ]),
      );
}
