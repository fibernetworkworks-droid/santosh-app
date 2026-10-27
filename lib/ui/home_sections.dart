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

/// One loader for everything the coworker sections need. 12 soft calls, ~parallel; failures stay null.
class HomeExtra {
  Map<String, dynamic>? employee;            // /api/employee → status (+ first pending ask + team count)
  List<Map<String, dynamic>> empRoles = [];  // v0.168 ROLES catalog — the choose-the-job cards
  List<Map<String, dynamic>> jobs = [];      // video studio jobs actually running right now
  Map<String, dynamic>? netCounts;           // /api/net/inbox → counts (connections, requests, inbox)
  int netThreads = 0, netGroups = 0;
  List<Map<String, dynamic>> netWaiting = [];  // v0.171 top knocks (from, what, kind) for the home cards
  List<Map<String, dynamic>> netThreadList = [];// v0.171 latest 2 baatein (peer, last msg) for the home cards
  List<Map<String, dynamic>> netConn = [];     // v0.171 active dost (label, handle, relation, vip, verified)
  List<Map<String, dynamic>> netGroupList = []; // v0.171 latest 2 mandali (emoji, name, count)
  List<Map<String, dynamic>> notebooks = []; // latest 5, for the strip
  List<Map<String, dynamic>> factsToday = [];// memory facts added today
  List<Map<String, dynamic>> lessons = [];   // Hoola Network lessons (latest 2)
  List<Map<String, dynamic>> words = [];     // her own words (latest 2)
  List<Map<String, dynamic>> fixes = [];     // v0.175 misheard→meant corrections (confirmed first)
  List<Map<String, dynamic>> skills = [];    // v0.175 skills installed from the network
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
      _soft(api.catchup(dayAgo)), _soft(api.day()), _soft(api.netConnections()),
    ]);
    try {
      final emp = r[0] as Map<String, dynamic>?;
      empRoles = _list(emp?['roles']);   // v0.168 keep the job catalog even before hiring
      final status = (emp?['status'] as Map?)?.cast<String, dynamic>();
      if (status != null && status['set_up'] == true) {
        final team = _list(emp?['team']);
        employee = {
          'status': status,
          'asks': _list(emp?['asks']).take(1).toList(),
          'team_active': team.where((m) => m['active'] != false).length,
        };
      } else {
        employee = null;
      }
      jobs = _list((r[1] as Map?)?['jobs']).where((j) => _videoActive.contains(j['status'])).take(2).toList();

      final inbox = r[2] as Map<String, dynamic>?;
      netCounts = (inbox?['counts'] as Map?)?.cast<String, dynamic>();
      netWaiting = _list(inbox?['waiting']).take(2).toList();   // v0.171 knock detail cards
      netThreads = _list(r[3]).length;   // netThreads() returns the thread list unwrapped
      netThreadList = _list(r[3]).take(2).toList();
      netGroups = _list(r[4]).length;
      netGroupList = _list(r[4]).take(2).toList();
      netConn = _list(r[11]).where((l) => l['status'] == 'active').take(8).toList();

      notebooks = _list(r[5]).take(5).toList();   // notebooks() returns the list unwrapped

      final now = DateTime.now();
      factsToday = _list(r[6]).where((f) {   // memory() returns the facts list unwrapped
        final t = DateTime.tryParse(_s(f['created_at']).replaceFirst('Z', ''))?.toLocal();
        return t != null && t.year == now.year && t.month == now.month && t.day == now.day;
      }).take(3).toList();

      lessons = _list((r[8] as Map?)?['lessons']).take(2).toList();
      words = _list((r[7] as Map?)?['words']).take(2).toList();
      fixes = _list((r[7] as Map?)?['fixes']).take(2).toList();    // v0.175 same voiceLearned call
      skills = _list((r[8] as Map?)?['skills']).take(2).toList();  // v0.175 same netLearned call

      catchup = r[9] as Map<String, dynamic>?;
      day = r[10] as Map<String, dynamic>?;
    } catch (_) {/* never let one odd payload break the home */}
    loaded = true;
  }

  int get catchupCount => catchup == null ? 0 : _list(catchup!['items']).length;
  bool get nothingNew =>
      employee == null && jobs.isEmpty && notebooks.isEmpty && factsToday.isEmpty && lessons.isEmpty && words.isEmpty && fixes.isEmpty && skills.isEmpty && catchupCount == 0;
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

/// HOOLA EMPLOYEE — v0.168 premium: nothing hired yet → pick-the-job cards straight on home;
/// hired → the job card with today's duties + trust tiers, stats, the waiting ask, and a
/// hire-more CTA. Every job carries its own topic icon + gradient, like the Jaldi tiles.
class EmployeeSection extends StatelessWidget {
  const EmployeeSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;

  void _open(BuildContext context, {int tab = 0, String? role}) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmployeeScreen(app: app, initialTab: tab, initialRole: role)));

  /// Unique topic look per job (icon + gradient). Anything unknown falls back to the brand tile.
  static (IconData, List<Color>) _look(String role) {
    const vio = [Color(0xFFA78BFA), Color(0xFF7C5CFF)];
    switch (role) {
      case 'front_desk': return (Icons.support_agent_rounded, vio);
      case 'support_collect': return (Icons.headset_mic_rounded, [Color(0xFF2DD4BF), Color(0xFF0D9488)]);
      case 'office': return (Icons.business_center_rounded, [Color(0xFFFBBF24), Color(0xFFD97706)]);
      case 'accounts': return (Icons.calculate_rounded, [Color(0xFF34D399), Color(0xFF059669)]);
      case 'field_service': return (Icons.engineering_rounded, [Color(0xFFFB923C), Color(0xFFEA580C)]);
      case 'sales': return (Icons.trending_up_rounded, [Color(0xFFFB7185), Color(0xFFE11D48)]);
      case 'hr_admin': return (Icons.groups_rounded, [Color(0xFF818CF8), Color(0xFF4F46E5)]);
      case 'marketing': return (Icons.campaign_rounded, [Color(0xFFF472B6), Color(0xFFDB2777)]);
      case 'video_editor': return (Icons.movie_rounded, [Color(0xFFE879F9), Color(0xFFC026D3)]);
      case 'computer_operator': return (Icons.computer_rounded, [Color(0xFF60A5FA), Color(0xFF2563EB)]);
      case 'tailor': return (Icons.checkroom_rounded, [Color(0xFFC084FC), Color(0xFF9333EA)]);
      case 'chai_stall': return (Icons.local_cafe_rounded, [Color(0xFFFCD34D), Color(0xFFF59E0B)]);
      case 'office_manager': return (Icons.inventory_2_rounded, [Color(0xFF94A3B8), Color(0xFF475569)]);
      case 'typist': return (Icons.keyboard_rounded, [Color(0xFF22D3EE), Color(0xFF0891B2)]);
      case 'mobile_shop': return (Icons.phone_android_rounded, [Color(0xFF38BDF8), Color(0xFF0284C7)]);
      case 'gst_practitioner': return (Icons.receipt_long_rounded, [Color(0xFF6EE7B7), Color(0xFF10B981)]);
      case 'insurance_agent': return (Icons.verified_user_rounded, [Color(0xFF7DD3FC), Color(0xFF0284C7)]);
      case 'performance_marketer': return (Icons.ads_click_rounded, [Color(0xFFE879F9), Color(0xFFA21CAF)]);
      case 'web_developer': return (Icons.web_rounded, [Color(0xFFA5B4FC), Color(0xFF6366F1)]);
      case 'brand_designer': return (Icons.palette_rounded, [Color(0xFFF0ABFC), Color(0xFFD946EF)]);
      case 'content_writer': return (Icons.edit_note_rounded, [Color(0xFF86EFAC), Color(0xFF22C55E)]);
      case 'site_manager': return (Icons.construction_rounded, [Color(0xFFFDBA74), Color(0xFFC2410C)]);
      case 'franchise_manager': return (Icons.storefront_rounded, [Color(0xFF5EEAD4), Color(0xFF0D9488)]);
      case 'export_assistant': return (Icons.local_shipping_rounded, [Color(0xFF93C5FD), Color(0xFF1D4ED8)]);
      case 'wholesale_assistant': return (Icons.warehouse_rounded, [Color(0xFFFCA5A5), Color(0xFFDC2626)]);
      case 'seo_specialist': return (Icons.travel_explore_rounded, [Color(0xFF6EE7B7), Color(0xFF059669)]);
      case 'telecaller': return (Icons.call_rounded, [Color(0xFFFDA4AF), Color(0xFFE11D48)]);
      case 'audit_assistant': return (Icons.fact_check_rounded, [Color(0xFF5EEAD4), Color(0xFF0F766E)]);
      case 'financial_analyst': return (Icons.query_stats_rounded, [Color(0xFF6EE7B7), Color(0xFF047857)]);
      case 'payroll_officer': return (Icons.payments_rounded, [Color(0xFFA7F3D0), Color(0xFF059669)]);
      case 'support_agent': return (Icons.support_agent_rounded, [Color(0xFF7DD3FC), Color(0xFF0369A1)]);
      case 'custom': return (Icons.auto_awesome_rounded, vio);
      default: return (Icons.badge_rounded, vio);
    }
  }

  static Widget _tile(IconData icon, List<Color> grad, {double size = 40, double radius = 13, double ic = 20}) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(radius),
          boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 14, offset: const Offset(0, 4))],
        ),
        child: Icon(icon, size: ic, color: Colors.white),
      );

  @override
  Widget build(BuildContext context) {
    final emp = extra.employee;
    final roles = extra.empRoles;
    if (emp == null) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const HomeLabel('HOOLA EMPLOYEE', isNew: true),
        Glass(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.auto_awesome_rounded, const [Color(0xFF2DD4BF), Color(0xFF7C5CFF)], size: 42, radius: 14, ic: 21),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${app.aName} · AI Employee', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  Text(app.g('Naukri chuniye — Hoola wahi kaam sambhalegi'), style: const TextStyle(fontSize: 11.5, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 12),
            if (roles.isEmpty)
              Press(
                onTap: () => _open(context, tab: 5),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), gradient: const LinearGradient(colors: [Color(0xFF2DD4BF), Color(0xFF7C5CFF)])),
                  child: Row(children: [
                    const Icon(Icons.storefront_rounded, size: 20, color: C.onAccent),
                    const SizedBox(width: 12),
                    Expanded(child: Text(app.g('Mujhe apni dukaan pe lagao'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14))),
                    const Icon(Icons.chevron_right_rounded, color: C.muted),
                  ]),
                ),
              )
            else
              SizedBox(
                height: 116,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  clipBehavior: Clip.none,
                  itemCount: roles.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) {
                    final r = roles[i];
                    final id = _s(r['id']);
                    final (icon, grad) = _look(id);
                    return Press(
                      onTap: () => _open(context, tab: 5, role: id),
                      child: Container(
                        width: 128,
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(.10))),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _tile(icon, grad),
                          const Spacer(),
                          Text(_s(r['label']), style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, height: 1.2), maxLines: 2, overflow: TextOverflow.ellipsis),
                          const SizedBox(height: 3),
                          Text(_s(r['say']), style: const TextStyle(fontSize: 9.5, color: C.faint, height: 1.25), maxLines: 2, overflow: TextOverflow.ellipsis),
                        ]),
                      ),
                    );
                  },
                ),
              ),
            const SizedBox(height: 10),
            Press(
              onTap: () => _open(context, tab: 5),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(color: const Color(0x14FFB15C), borderRadius: BorderRadius.circular(13), border: Border.all(color: const Color(0x40FFB15C))),
                child: Row(children: [
                  const Icon(Icons.bolt_rounded, size: 17, color: C.accent),
                  const SizedBox(width: 8),
                  Expanded(child: Text(app.g('Aur AI employee lagao — kaam hoga tez'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: C.accentSoft))),
                  const Icon(Icons.chevron_right_rounded, size: 18, color: C.faint),
                ]),
              ),
            ),
          ]),
        ),
      ]);
    }
    final st = (emp['status'] as Map).cast<String, dynamic>();
    final paused = st['paused'] == true || st['enabled'] != true;
    final asks = _list(emp['asks']);
    final ask = asks.isEmpty ? null : asks.first;
    final trust = _list(st['trust']);
    final teamN = _n(emp['team_active']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const HomeLabel('HOOLA EMPLOYEE', isNew: true),
      Press(
        onTap: () => _open(context),
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
            if (trust.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(app.g('AAJ KE KAAM'), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.faint)),
              const SizedBox(height: 6),
              for (final t in trust.take(4))
                Padding(
                  padding: const EdgeInsets.only(bottom: 5),
                  child: Row(children: [
                    Icon(t['level'] == 'seekh' ? Icons.school_rounded : Icons.check_circle_rounded,
                        size: 14, color: t['level'] == 'seekh' ? C.faint : C.ok),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_s(t['duty']), style: const TextStyle(fontSize: 12, height: 1.3), maxLines: 1, overflow: TextOverflow.ellipsis)),
                    _tier('${t['level']}'),
                  ]),
                ),
            ],
            const SizedBox(height: 10),
            Row(children: [
              _stat('${_n(st['done_today'])}', 'AAJ POORE'),
              const SizedBox(width: 8),
              _stat('${_n(st['pending_asks'])}', 'ASK WAIT', hot: _n(st['pending_asks']) > 0),
              const SizedBox(width: 8),
              _stat(teamN > 0 ? '$teamN + 1' : '${_n(st['team_tasks_waiting'])}', 'TEAM TASKS'),
            ]),
            if (ask != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x66FFB15C)), color: const Color(0x1AFFB15C)),
                child: Row(children: [
                  _tile(Icons.front_hand_rounded, const [Color(0xFFFFB15C), Color(0xFFFB923C)], size: 26, radius: 9, ic: 14),
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
            const SizedBox(height: 10),
            Press(
              onTap: () => _open(context, tab: 3),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(color: const Color(0x14FFB15C), borderRadius: BorderRadius.circular(13), border: Border.all(color: const Color(0x40FFB15C))),
                child: Row(children: [
                  const Icon(Icons.group_add_rounded, size: 17, color: C.accent),
                  const SizedBox(width: 8),
                  Expanded(child: Text(app.g('Aur AI employee lagao — kaam hoga tez'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: C.accentSoft))),
                  const Icon(Icons.chevron_right_rounded, size: 18, color: C.faint),
                ]),
              ),
            ),
          ]),
        ),
      ),
    ]);
  }

  /// Trust tier chip: Seekh (learning) / Saathi (partner) / Bharosa (trusted).
  static Widget _tier(String level) {
    final (label, fg, bg, bc) = switch (level) {
      'bharosa' => ('BHAROSA', const Color(0xFF2DD4BF), const Color(0x1A2DD4BF), const Color(0x552DD4BF)),
      'saathi' => ('SAATHI', C.accentSoft, const Color(0x1AFFB15C), const Color(0x55FFC27A)),
      _ => ('SEEKH', C.faint, Colors.white.withOpacity(.06), Colors.white.withOpacity(.14)),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999), border: Border.all(color: bc)),
      child: Text(label, style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: fg)),
    );
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
/// v0.171 premium: khaali network shows the invite card, live network shows knock detail
/// cards (topic tile by kind), baatein rows that deep-open the thread, a dost strip with
/// relation-coloured rings, mandali chips and the open-network CTA.
class NetworkSection extends StatelessWidget {
  const NetworkSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;

  void _open(BuildContext context, {int tab = 0}) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaNetScreen(app: app, initialTab: tab)));

  void _openThread(BuildContext context, String id) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaThreadScreen(app: app, threadId: id)));

  /// Topic look per knock kind (icon + gradient). Unknown kinds fall back to the brand knock tile.
  static (IconData, List<Color>) _kindLook(String kind) {
    switch (kind) {
      case 'meeting': return (Icons.event_rounded, const [Color(0xFF60A5FA), Color(0xFF2563EB)]);
      case 'task': return (Icons.task_alt_rounded, const [Color(0xFF34D399), Color(0xFF059669)]);
      case 'reminder': return (Icons.alarm_rounded, const [Color(0xFFFFB15C), Color(0xFFFB923C)]);
      case 'ask': return (Icons.front_hand_rounded, const [Color(0xFFFCD34D), Color(0xFFF59E0B)]);
      case 'message': return (Icons.chat_bubble_rounded, const [Color(0xFFA78BFA), Color(0xFF7C5CFF)]);
      case 'voice_note': return (Icons.graphic_eq_rounded, const [Color(0xFFE879F9), Color(0xFFC026D3)]);
      case 'file': return (Icons.attach_file_rounded, const [Color(0xFF38BDF8), Color(0xFF0284C7)]);
      default: return (Icons.notifications_active_rounded, const [Color(0xFF7C5CFF), Color(0xFFE0458B)]);
    }
  }

  /// Dost ring colour by relation: parivar rose, team sky, business emerald, dost violet.
  static List<Color> _relationLook(String relation) {
    switch (relation) {
      case 'family': return const [Color(0xFFFB7185), Color(0xFFE11D48)];
      case 'team': return const [Color(0xFF38BDF8), Color(0xFF0284C7)];
      case 'business': return const [Color(0xFF34D399), Color(0xFF059669)];
      default: return const [Color(0xFFA78BFA), Color(0xFF7C5CFF)];
    }
  }

  static Widget _tile(IconData icon, List<Color> grad, {double size = 40, double radius = 13, double ic = 20}) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(radius),
          boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 14, offset: const Offset(0, 4))],
        ),
        child: Icon(icon, size: ic, color: Colors.white),
      );

  /// Gradient avatar with the peer's initial — dost strip and baatein rows.
  static Widget _avatar(String name, List<Color> grad, {double size = 38}) {
    final initial = name.isEmpty ? 'H' : name.substring(0, 1).toUpperCase();
    return Container(
      width: size, height: size,
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
        shape: BoxShape.circle,
        boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 10, offset: const Offset(0, 3))],
      ),
      child: Center(child: Text(initial, style: TextStyle(fontSize: size * .42, fontWeight: FontWeight.w800, color: Colors.white))),
    );
  }

  /// Knock one-liner: what → body title → body text, jo pehle mile.
  static String _knockWhat(Map<String, dynamic> k) {
    final body = Map<String, dynamic>.from(k['body'] as Map? ?? const {});
    for (final v in [_s(k['what']), _s(body['title']), _s(body['text'])]) {
      if (v.isNotEmpty) return v;
    }
    return '';
  }

  /// One knock card: topic tile by kind + kaun / kya, tap = inbox tab.
  Widget _knockRow(BuildContext context, Map<String, dynamic> k) {
    final (icon, grad) = _kindLook(_s(k['kind']));
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Press(
        onTap: () => _open(context, tab: 2),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: const Color(0x14FFB15C), borderRadius: BorderRadius.circular(13), border: Border.all(color: const Color(0x40FFB15C))),
          child: Row(children: [
            _tile(icon, grad, size: 34, radius: 11, ic: 17),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text(_s(k['from']).isEmpty ? 'Hoola' : _s(k['from']),
                        style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800), maxLines: 1, overflow: TextOverflow.ellipsis),
                  ),
                  if (_s(k['kind']).isNotEmpty)
                    Text(_s(k['kind']).toUpperCase(), style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.accentSoft)),
                ]),
                const SizedBox(height: 2),
                Text(_knockWhat(k), style: const TextStyle(fontSize: 11.5, color: C.muted, height: 1.3), maxLines: 1, overflow: TextOverflow.ellipsis),
              ]),
            ),
            const Icon(Icons.chevron_right_rounded, size: 18, color: C.faint),
          ]),
        ),
      ),
    );
  }

  /// One baat card: avatar (+bot badge), peer, last line; tap = thread seedha khulta hai.
  Widget _threadRow(BuildContext context, Map<String, dynamic> t) {
    final peer = _s(t['peer_avatar']).isEmpty ? _s(t['with']) : _s(t['peer_avatar']);
    final last = _s(t['last']).isEmpty ? _s(t['subject']) : _s(t['last']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Press(
        onTap: () => _openThread(context, _s(t['id'])),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(13), border: Border.all(color: Colors.white.withOpacity(.10))),
          child: Row(children: [
            Stack(clipBehavior: Clip.none, children: [
              _avatar(peer, const [Color(0xFFA78BFA), Color(0xFF7C5CFF)], size: 36),
              if (t['mode'] == 'handle')
                Positioned(
                  right: -3, bottom: -3,
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: const BoxDecoration(color: C.bgTop, shape: BoxShape.circle),
                    child: const Icon(Icons.smart_toy_rounded, size: 12, color: C.teal),
                  ),
                ),
            ]),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text(peer.isEmpty ? 'Hoola' : '${_s(t['peer_owner']).isEmpty ? peer : '$peer  ·  ${_s(t['peer_owner'])}'}',
                        style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800), maxLines: 1, overflow: TextOverflow.ellipsis),
                  ),
                  if (_s(t['status']).isNotEmpty && _s(t['status']) != 'open')
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(color: Colors.white.withOpacity(.06), borderRadius: BorderRadius.circular(999), border: Border.all(color: Colors.white.withOpacity(.14))),
                      child: Text(_s(t['status']).toUpperCase(), style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.faint)),
                    ),
                ]),
                const SizedBox(height: 2),
                Row(children: [
                  if (_s(t['last_kind']) == 'file') ...[
                    const Icon(Icons.attach_file_rounded, size: 13, color: C.faint),
                    const SizedBox(width: 3),
                  ],
                  Expanded(
                    child: Text(
                      '${t['last_dir'] == 'out' ? app.g('Aapka {x}: ', x: _s(t['my_avatar']).isEmpty ? app.aName : _s(t['my_avatar'])) : ''}$last',
                      style: const TextStyle(fontSize: 11.5, color: C.muted, height: 1.3), maxLines: 1, overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ]),
              ]),
            ),
            const Icon(Icons.chevron_right_rounded, size: 18, color: C.faint),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = extra.netCounts;
    if (c == null) return const SizedBox.shrink();   // network off / old server
    final knocks = _n(c['inbox']);
    final dost = _n(c['connections']);
    final hasAny = knocks > 0 || dost > 0 || extra.netThreads > 0;

    // ── Khaali network: the invite card — pehla dost jodiye ──
    if (!hasAny) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const HomeLabel('HOOLA NETWORK'),
        Glass(
          padding: const EdgeInsets.all(14),
          tint: const Color(0xFF7C5CFF),
          opacity: .06,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.public_rounded, const [Color(0xFF7C5CFF), Color(0xFFE0458B)], size: 42, radius: 14, ic: 21),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.g('Pehle dost se shuru kariye'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  Text(app.g('Dusre Hoolas se knocks, baatein, deals — sab yahan aayega'), style: const TextStyle(fontSize: 11.5, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 12),
            Press(
              onTap: () => _open(context, tab: 1),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), gradient: const LinearGradient(colors: [Color(0xFF7C5CFF), Color(0xFFE0458B)])),
                child: Row(children: [
                  const Icon(Icons.qr_code_rounded, size: 20, color: C.onAccent),
                  const SizedBox(width: 12),
                  Expanded(child: Text(app.g('QR ya ID se pehla dost jodiye'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14))),
                  const Icon(Icons.chevron_right_rounded, color: C.muted),
                ]),
              ),
            ),
            const SizedBox(height: 10),
            Text(app.g('Aapki haan ke bina koi jud nahi sakta'),
                style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0xCCA78BFA))),
          ]),
        ),
      ]);
    }

    // ── Network live: knocks, baatein, dost, mandali ──
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel('HOOLA NETWORK', isNew: knocks > 0),
      Press(
        onTap: () => _open(context),
        child: Glass(
          padding: const EdgeInsets.all(14),
          tint: const Color(0xFF7C5CFF),
          opacity: .06,
          border: const Color(0x47A78BFA),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.public_rounded, const [Color(0xFF7C5CFF), Color(0xFFE0458B)], size: 42, radius: 14, ic: 21),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.g('Aapka Hoola, dusre Hoolas se mila'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  Text(app.g('Knocks, baatein, deals — sab khud sambhalti hoon'), style: const TextStyle(fontSize: 11.5, color: C.muted)),
                ]),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: knocks > 0 ? const Color(0x55FFC27A) : const Color(0x552DD4BF)),
                  color: knocks > 0 ? const Color(0x1AFFB15C) : const Color(0x1A2DD4BF),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  if (knocks == 0) Container(width: 6, height: 6, decoration: const BoxDecoration(color: C.ok, shape: BoxShape.circle)),
                  if (knocks == 0) const SizedBox(width: 5),
                  Text(knocks > 0 ? '$knocks KNOCK' : 'LIVE',
                      style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: .5, color: knocks > 0 ? C.accentSoft : C.teal)),
                ]),
              ),
            ]),
            if (extra.netWaiting.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(app.g('AAJ KE KNOCKS'), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.faint)),
              const SizedBox(height: 6),
              for (final k in extra.netWaiting) _knockRow(context, k),
            ],
            if (extra.netThreadList.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(app.g('AAJ KI BAATEIN'), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.faint)),
              const SizedBox(height: 6),
              for (final t in extra.netThreadList) _threadRow(context, t),
            ],
            if (extra.netConn.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(app.g('AAPKE DOST'), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.faint)),
              const SizedBox(height: 8),
              SizedBox(
                height: 64,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  clipBehavior: Clip.none,
                  itemCount: extra.netConn.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 10),
                  itemBuilder: (_, i) {
                    final l = extra.netConn[i];
                    final name = _s(l['label']);
                    return Press(
                      onTap: () => _open(context, tab: 1),
                      child: SizedBox(
                        width: 46,
                        child: Column(children: [
                          Stack(clipBehavior: Clip.none, children: [
                            _avatar(name, _relationLook(_s(l['relation'])), size: 40),
                            if (l['vip'] == true || l['verified'] == true)
                              Positioned(
                                right: -4, bottom: -4,
                                child: Icon(l['vip'] == true ? Icons.star_rounded : Icons.verified_rounded,
                                    size: 14, color: l['vip'] == true ? C.accent : C.ok),
                              ),
                          ]),
                          const SizedBox(height: 4),
                          Text(name.split(' ').first, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: C.chip),
                              maxLines: 1, overflow: TextOverflow.ellipsis),
                        ]),
                      ),
                    );
                  },
                ),
              ),
            ],
            const SizedBox(height: 10),
            Row(children: [
              _stat('$knocks', 'KNOCK WAIT', hot: knocks > 0),
              const SizedBox(width: 8),
              _stat('$dost', 'DOST'),
              const SizedBox(width: 8),
              _stat('${extra.netThreads}', 'BAATEIN'),
              const SizedBox(width: 8),
              _stat('${extra.netGroups}', 'MANDALI'),
            ]),
            if (extra.netGroupList.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final g in extra.netGroupList)
                  Press(
                    onTap: () => _open(context, tab: 4),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(999), border: Border.all(color: Colors.white.withOpacity(.10))),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        if (_s(g['emoji']).isNotEmpty)
                          Text(_s(g['emoji']), style: const TextStyle(fontSize: 12))
                        else
                          const Icon(Icons.group_rounded, size: 13, color: C.chip),
                        const SizedBox(width: 5),
                        Text('${_s(g['name'])} · ${_n(g['count'])}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: C.chip)),
                      ]),
                    ),
                  ),
              ]),
            ],
            const SizedBox(height: 11),
            Press(
              onTap: () => _open(context),
              child: Container(
                height: 36,
                decoration: BoxDecoration(color: const Color(0x17FFFFFF), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x29FFFFFF))),
                alignment: Alignment.center,
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.public_rounded, size: 16, color: C.chip),
                  const SizedBox(width: 7),
                  Text(app.g('Network kholo — knocks, baatein, deals'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: C.chip)),
                ]),
              ),
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

/// HOOLA NOTEBOOK — her notebooks: padho, poochho, studio.
/// v0.173 premium: khaali state shows the invite card, live state wraps the strip in a
/// glass card with per-notebook colour-tile cards (emoji or book icon), overview lines,
/// source/studio counts, updated date and the open-all CTA.
class NotebookSection extends StatelessWidget {
  const NotebookSection({super.key, required this.extra, required this.app});
  final HomeExtra extra;
  final Santosh app;

  void _all(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebooksScreen(app: app)));

  static Widget _tile(IconData icon, List<Color> grad, {double size = 42, double radius = 14, double ic = 21}) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(radius),
          boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 14, offset: const Offset(0, 4))],
        ),
        child: Icon(icon, size: ic, color: Colors.white),
      );

  /// One notebook card: colour tile (emoji or book icon), title, overview, counts, date.
  Widget _nbCard(BuildContext context, Map<String, dynamic> nb) {
    final col = nbColor(nb['color']);
    final em = _s(nb['emoji']);
    final updated = _s(nb['updated']).split('T').first;
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: app, id: _s(nb['id'])))),
      child: Container(
        width: 150,
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(.10))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              width: 34, height: 34,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [col, col.withOpacity(.55)], begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.circular(11),
                boxShadow: [BoxShadow(color: col.withOpacity(.35), blurRadius: 12, offset: const Offset(0, 3))],
              ),
              child: Center(child: em.isEmpty ? const Icon(Icons.auto_stories_rounded, size: 17, color: Colors.white) : Text(em, style: const TextStyle(fontSize: 16))),
            ),
            const Spacer(),
            if (updated.isNotEmpty)
              Text(updated, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: C.faint)),
          ]),
          const Spacer(),
          Text(_s(nb['title']), maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, height: 1.25)),
          if (_s(nb['overview']).isNotEmpty) ...[
            const SizedBox(height: 3),
            Text(_s(nb['overview']), maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 9.5, color: C.faint, height: 1.3)),
          ],
          const SizedBox(height: 7),
          Row(children: [
            Icon(Icons.library_books_rounded, size: 12, color: col),
            const SizedBox(width: 3),
            Text('${_n(nb['sources'])}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: C.chip)),
            const SizedBox(width: 9),
            Icon(Icons.movie_filter_rounded, size: 12, color: col),
            const SizedBox(width: 3),
            Text('${_n(nb['outputs'])}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: C.chip)),
            const Spacer(),
            Container(width: 22, height: 4, decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), gradient: LinearGradient(colors: [col, col.withOpacity(.35)]))),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // ── Khaali: the invite card — pehla notebook banaiye ──
    if (extra.notebooks.isEmpty) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const HomeLabel('HOOLA NOTEBOOK'),
        Glass(
          padding: const EdgeInsets.all(14),
          tint: const Color(0xFF2DD4BF),
          opacity: .05,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.auto_stories_rounded, const [Color(0xFF2DD4BF), Color(0xFF7C5CFF)]),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.g('Pehla notebook banaiye'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  Text(app.g('Web, PDF, YouTube, Drive — jo daaloge, {a} padh kar yaad rakhegi'),
                      style: const TextStyle(fontSize: 11.5, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 12),
            Press(
              onTap: () => _all(context),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), gradient: const LinearGradient(colors: [Color(0xFF2DD4BF), Color(0xFF7C5CFF)])),
                child: Row(children: [
                  const Icon(Icons.add_rounded, size: 20, color: C.onAccent),
                  const SizedBox(width: 12),
                  Expanded(child: Text(app.g('Notebook banao'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14))),
                  const Icon(Icons.chevron_right_rounded, color: C.muted),
                ]),
              ),
            ),
            const SizedBox(height: 10),
            Text(app.g('Sirf aapke sources — {a} inhi se seekhti hai'),
                style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0xCC5EEAD4))),
          ]),
        ),
      ]);
    }

    // ── Notebooks live: colour-tile cards on the strip ──
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel('HOOLA NOTEBOOK', count: extra.notebooks.length),
      Glass(
        padding: const EdgeInsets.all(14),
        tint: const Color(0xFF2DD4BF),
        opacity: .05,
        border: const Color(0x475EEAD4),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            _tile(Icons.auto_stories_rounded, const [Color(0xFF2DD4BF), Color(0xFF7C5CFF)]),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(app.g('Padho, poochho, studio banao'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                Text(app.g('Sources daalo — {a} padh kar jawab degi'), style: const TextStyle(fontSize: 11.5, color: C.muted)),
              ]),
            ),
          ]),
          const SizedBox(height: 12),
          SizedBox(
            height: 128,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              clipBehavior: Clip.none,
              itemCount: extra.notebooks.length + 1,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                if (i < extra.notebooks.length) return _nbCard(context, extra.notebooks[i]);
                return Press(
                  onTap: () => _all(context),
                  child: Container(
                    width: 96,
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(.25), width: 1.2)),
                    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      const Icon(Icons.add_rounded, color: C.muted, size: 22),
                      const SizedBox(height: 4),
                      Text(app.g('Naya notebook'), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: C.muted), textAlign: TextAlign.center),
                    ]),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 11),
          Press(
            onTap: () => _all(context),
            child: Container(
              height: 36,
              decoration: BoxDecoration(color: const Color(0x17FFFFFF), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x29FFFFFF))),
              alignment: Alignment.center,
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.menu_book_rounded, size: 16, color: C.chip),
                const SizedBox(width: 7),
                Text(app.g('Sab notebooks kholo'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: C.chip)),
              ]),
            ),
          ),
        ]),
      ),
    ]);
  }
}

/// AAJ KYA SEEKHA — what Hoola learned today, category-wise: chats, voice, network.
/// v0.175 premium: khaali state shows the invite card; live state groups the real
/// learning into three labelled blocks — BAATEIN SE (today's facts, auto/manual + time),
/// AWAAZ SE (her words + misheard→meant fixes with counts), NETWORK SE (lessons with
/// topic chips + installed skills) — every forgettable row forgets in one tap.
class LearnedSection extends StatelessWidget {
  const LearnedSection({super.key, required this.extra, required this.app, required this.reload});
  final HomeExtra extra;
  final Santosh app;
  final Future<void> Function() reload;

  void _all(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => VoiceLearnedScreen(app: app)));

  static const List<Color> _cViolet = [Color(0xFFA78BFA), Color(0xFF7C5CFF)];
  static const List<Color> _cRose = [Color(0xFFFB7185), Color(0xFFE11D48)];
  static const List<Color> _cEmerald = [Color(0xFF34D399), Color(0xFF0D9488)];

  Widget _tile(IconData icon, List<Color> grad, {double size = 40, double ic = 20}) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(13),
          boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 13, offset: const Offset(0, 4))],
        ),
        child: Icon(icon, size: ic, color: Colors.white),
      );

  String _when(String iso) {
    final t = DateTime.tryParse(iso.replaceFirst('Z', ''))?.toLocal();
    if (t == null) return '';
    return '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  Widget _catHead(IconData icon, List<Color> grad, String label, int count) => Padding(
        padding: const EdgeInsets.only(bottom: 2),
        child: Row(children: [
          _tile(icon, grad),
          const SizedBox(width: 11),
          Expanded(child: Text(app.g(label), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.1, color: C.chip))),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), color: grad.last.withOpacity(.18)),
            child: Text('$count', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: grad.first)),
          ),
        ]),
      );

  Widget _forget(Future<void> Function() act) => Press(
        onTap: () async {
          try {
            await act();
            await reload();
          } catch (_) {}
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: Colors.white.withOpacity(.13))),
          child: Text(app.g('Bhool jao'), style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C.faint)),
        ),
      );

  Widget _sep() => Container(height: 1, margin: const EdgeInsets.symmetric(vertical: 9), color: Colors.white.withOpacity(.06));

  Widget _emptyLine(String s) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Text(s, style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: C.faint)),
      );

  Widget _factRow(Map<String, dynamic> f) {
    final when = _when(_s(f['created_at']));
    final auto = f['auto'] == true;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(f['text']), maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5, height: 1.4, color: C.ink)),
            const SizedBox(height: 3),
            Row(children: [
              if (when.isNotEmpty)
                Text(app.g('aaj · {x}', x: when), style: const TextStyle(fontSize: 10, color: C.faint)),
              if (auto) ...[
                const SizedBox(width: 7),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x55A78BFA))),
                  child: Text(app.g('khud seekha'), style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Color(0xFFC4B5FD))),
                ),
              ],
            ]),
          ]),
        ),
        const SizedBox(width: 8),
        _forget(() => app.api!.forget(_n(f['id']))),
      ]),
    );
  }

  Widget _wordRow(Map<String, dynamic> w) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(w['term']), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: C.ink)),
              const SizedBox(height: 3),
              Text(_s(w['source']) == 'call' ? app.g('Calls se pakda') : app.g('Aapne sikhaya'),
                  style: const TextStyle(fontSize: 10, color: C.faint)),
            ]),
          ),
          const SizedBox(width: 8),
          _forget(() => app.api!.voiceWordRemove(_n(w['id']))),
        ]),
      );

  Widget _fixRow(Map<String, dynamic> x) {
    final cnt = _n(x['count']);
    final ok = x['confirmed'] == true;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Flexible(
                child: Text('"${_s(x['heard'])}"', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, color: C.faint, decoration: TextDecoration.lineThrough, decorationColor: Color(0x33FFFFFF))),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.east_rounded, size: 13, color: Color(0xFFFB7185)),
              const SizedBox(width: 6),
              Flexible(
                child: Text(_s(x['meant']), maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: C.ink)),
              ),
            ]),
            const SizedBox(height: 3),
            Row(children: [
              if (cnt > 0)
                Text(app.g('{x} baar galat suna', x: '$cnt'), style: const TextStyle(fontSize: 10, color: C.faint)),
              if (ok) ...[
                const SizedBox(width: 7),
                const Icon(Icons.check_circle_rounded, size: 12, color: Color(0xFF34D399)),
                const SizedBox(width: 3),
                Text(app.g('pakka'), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF6EE7B7))),
              ],
            ]),
          ]),
        ),
        const SizedBox(width: 8),
        _forget(() => app.api!.voiceFixRemove(_n(x['id']))),
      ]),
    );
  }

  Widget _lessonRow(Map<String, dynamic> l) {
    final topic = _s(l['topic']);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (topic.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(bottom: 4),
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x5534D399))),
                child: Text(topic.toUpperCase(), style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: .8, color: Color(0xFF6EE7B7))),
              ),
            Text(_s(l['text']), maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5, height: 1.4, color: C.ink)),
          ]),
        ),
        const SizedBox(width: 8),
        _forget(() => app.api!.netLessonAct('${l['id']}', 'forget')),
      ]),
    );
  }

  Widget _skillRow(Map<String, dynamic> sk) {
    final comm = _s(sk['community']);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(children: [
        Container(
          width: 26, height: 26,
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: _cEmerald, begin: Alignment.topLeft, end: Alignment.bottomRight),
            borderRadius: BorderRadius.circular(8),
            boxShadow: [BoxShadow(color: _cEmerald.last.withOpacity(.30), blurRadius: 9, offset: const Offset(0, 3))],
          ),
          child: const Icon(Icons.extension_rounded, size: 14, color: Colors.white),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(sk['name']), maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: C.ink)),
            const SizedBox(height: 2),
            Text(comm.isEmpty ? app.g('Network se seekhi skill') : app.g('{x} se seekhi skill', x: comm),
                maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10, color: C.faint)),
          ]),
        ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final facts = extra.factsToday;
    final words = extra.words;
    final fixes = extra.fixes;
    final lessons = extra.lessons;
    final skills = extra.skills;
    final total = facts.length + words.length + fixes.length + lessons.length + skills.length;

    // ── Khaali: the invite card — aaj kuch naya nahi seekha ──
    if (total == 0) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        HomeLabel(app.g('AAJ KYA SEEKHA')),
        Glass(
          tint: const Color(0xFFA78BFA),
          opacity: .05,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.auto_awesome_rounded, _cViolet),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.g('Aaj kuch naya nahi seekha'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  const SizedBox(height: 3),
                  Text(app.g('Baat karo, calls lo, network chalao — jitna karengi, utna seekhungi.'),
                      style: const TextStyle(fontSize: 12.5, height: 1.45, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 10),
            Text(app.g('Har baat aur har call se kuch naya sikhti hoon.'),
                style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0xB3C4B5FF))),
          ]),
        ),
      ]);
    }

    // ── Live: the real learning, category-wise ──
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel(app.g('AAJ KYA SEEKHA'), isNew: true, count: total, trailing: Press(
        onTap: () => _all(context),
        child: Text(app.g('Sab dekho'), style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: C.violet)),
      )),
      Glass(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _catHead(Icons.forum_rounded, _cViolet, 'BAATEIN SE', facts.length),
          if (facts.isEmpty)
            _emptyLine(app.g('Aaj baaton se kuch naya nahi.'))
          else
            for (final f in facts) _factRow(f),
          _sep(),
          _catHead(Icons.graphic_eq_rounded, _cRose, 'AWAAZ SE', words.length + fixes.length),
          if (words.isEmpty && fixes.isEmpty)
            _emptyLine(app.g('Aaj awaaz se kuch naya nahi.'))
          else ...[
            for (final w in words) _wordRow(w),
            for (final x in fixes) _fixRow(x),
          ],
          _sep(),
          _catHead(Icons.school_rounded, _cEmerald, 'NETWORK SE', lessons.length + skills.length),
          if (lessons.isEmpty && skills.isEmpty)
            _emptyLine(app.g('Network se aaj kuch naya nahi.'))
          else ...[
            for (final l in lessons) _lessonRow(l),
            for (final sk in skills) _skillRow(sk),
          ],
          const SizedBox(height: 4),
          Text(app.g('"Jo na pasand ho, ek tap mein bhula do."'),
              style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0xB3C4B5FF))),
        ]),
      ),
    ]);
  }
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
