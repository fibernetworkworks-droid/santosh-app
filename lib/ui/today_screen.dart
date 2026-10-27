import 'package:flutter/material.dart';

import '../emotion.dart';
import '../state.dart';
import 'approve_sheet.dart';
import 'glass.dart';
import 'home_sections.dart';
import 'live_santosh.dart';

const _days = ['Somvar', 'Mangalvar', 'Budhvar', 'Guruvar', 'Shukravar', 'Shanivar', 'Ravivar'];
const _months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/// Aaj: Hoola's home — she greets the owner, shows what needs their tap, what she is doing right now,
/// their day, her four worlds (Employee, Network, Notebook, what she learned today) and her memory:
/// reminders, routines, lists, a 24-hour recap — and a partner line at the bottom.
class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key, required this.app, this.onTab});
  final Santosh app;
  final ValueChanged<int>? onTab;
  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  final HomeExtra _extra = HomeExtra();
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    if (_loading || !mounted) return;
    _loading = true;
    await _extra.load(widget.app);
    _loading = false;
    if (mounted) setState(() {});
  }

  String _greet() {
    final h = DateTime.now().hour;
    final part = h < 5 ? 'Shubh ratri' : h < 12 ? 'Suprabhat' : h < 17 ? 'Namaste' : h < 21 ? 'Shubh sandhya' : 'Shubh ratri';
    final name = ((widget.app.account?['name'] as String?) ?? '').split(' ').first;
    return name.isEmpty ? part : '$part, $name';
  }

  void _ask(String text) {
    widget.onTab?.call(1);
    widget.app.send(text);
  }

  // v0.167 Jaldi Se Karo: each task gets its own topic gradient tile — one glance and you know the job.
  // Gradients continue the hues the section already used (saffron bill, violet shop, teal route, rose cab).
  Widget _action(IconData icon, List<Color> grad, Color glow, String label, String prompt) => Expanded(
        child: Press(
          onTap: () => _ask(prompt),
          child: Glass(
            radius: 20,
            padding: const EdgeInsets.symmetric(vertical: 13),
            child: Column(children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
                  borderRadius: BorderRadius.circular(17),
                  boxShadow: [BoxShadow(color: glow, blurRadius: 16, offset: const Offset(0, 5))],
                ),
                child: Icon(icon, color: Colors.white, size: 24),
              ),
              const SizedBox(height: 8),
              Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: .2)),
            ]),
          ),
        ),
      );

  /// v0.166 — tiny live weather chip next to the date, fed by the same /api/day call as the Aaj ka Din card.
  Widget? _weatherChip() {
    final w = _extra.day?['weather'] as Map?;
    if (w == null || w['now_c'] is! num) return null;
    final code = w['now_code'] is num ? (w['now_code'] as num).toInt() : null;
    final isDay = w['is_day'] is bool ? w['is_day'] as bool : true;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(color: const Color(0x12FFFFFF), borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x21FFFFFF))),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Text(DayTilesSection.wIconFor(code, isDay), style: const TextStyle(fontSize: 12)),
        const SizedBox(width: 5),
        Text('${(w['now_c'] as num).round()}°', style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: C.chip)),
      ]),
    );
  }

  Widget _hero(BuildContext context) {
    final app = widget.app;
    final pend = app.pendingApprovals.length;
    final line = pend > 0
        ? '$pend kaam aapke approval ka intezaar kar raha hai.'
        : app.reminders.isNotEmpty
            ? 'Agla reminder: ${app.reminders.first['text'] ?? ''}'
            : 'Kuch bhi boliye: bill, dukaan, cab, email, reminder.';
    final onDuty = _extra.employee != null &&
        (_extra.employee!['status'] as Map?)?['paused'] != true &&
        ((_extra.employee!['status'] as Map?)?['enabled'] == true);
    return Glass(
      radius: 30,
      padding: const EdgeInsets.fromLTRB(4, 14, 16, 14),
      child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
        SizedBox(width: 132, height: 170, child: Align(alignment: Alignment.bottomCenter, child: LiveSantosh(feeling: app.mood, size: 150))),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(app.mood == Mood.idle ? 'Main taiyaar hoon' : moodStyles[app.mood]!.label, style: display(18)),
            const SizedBox(height: 6),
            Text(line, maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13.5, height: 1.45, color: C.chip)),
            const SizedBox(height: 12),
            GradientButton(label: 'Baat karein', height: 42, icon: Icons.mic_rounded, onTap: () => widget.onTab?.call(2)),
            const SizedBox(height: 8),
            SizedBox(width: double.infinity, child: GlassButton(label: 'Likh ke boliye', height: 40, onTap: () => widget.onTab?.call(1))),
            const SizedBox(height: 10),
            Row(children: [
              Container(width: 7, height: 7, decoration: const BoxDecoration(color: C.ok, shape: BoxShape.circle)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(onDuty ? 'Online · dukaan pe duty pe, yahan bhi nazar' : 'Online · sab kaamon pe nazar',
                    style: const TextStyle(fontSize: 11.5, color: C.muted), maxLines: 1, overflow: TextOverflow.ellipsis),
              ),
            ]),
          ]),
        ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    // the API connects a moment after the first frame; pick it up whenever it arrives
    if (!_extra.loaded && !_loading && app.api != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    }
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) => RefreshIndicator(
        onRefresh: () async {
          await Future.wait([
            app.refreshReminders(),
            app.refreshLists(),
            app.refreshRoutines(),
            _extra.load(app),
          ]);
          if (mounted) setState(() {});
        },
        color: C.accent,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 18, 16, 24), children: [
          Builder(builder: (context) {
            final d = DateTime.now();
            return Row(children: [
              Expanded(
                child: Text('${_days[d.weekday - 1]}, ${d.day} ${_months[d.month - 1]}',
                    style: const TextStyle(fontSize: 13, color: C.muted, fontWeight: FontWeight.w700, letterSpacing: .3)),
              ),
              _weatherChip() ?? const SizedBox.shrink(),
            ]);
          }),
          const SizedBox(height: 2),
          Text(_greet(), style: display(26)),
          const SizedBox(height: 16),
          Stagger(index: 0, child: _hero(context)),
          const SizedBox(height: 12),
          if (app.pendingApprovals.isNotEmpty) ...[
            Stagger(index: 1, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              HomeLabel('AAPKI HAAN CHAHIYE', count: app.pendingApprovals.length),
              for (final a in app.pendingApprovals)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Press(
                    onTap: () => showApproveSheet(context, app, a),
                    child: Glass(
                      border: const Color(0x66FFB15C),
                      child: Row(children: [
                        const Icon(Icons.verified_outlined, color: C.accent),
                        const SizedBox(width: 12),
                        Expanded(child: Text((a['title'] as String? ?? '').replaceFirst('[DEMO] ', ''), style: const TextStyle(fontWeight: FontWeight.w700))),
                        Text(a['amount'] as String? ?? '', style: display(16, color: C.accentSoft)),
                        const SizedBox(width: 4),
                        const Icon(Icons.chevron_right_rounded, color: C.muted),
                      ]),
                    ),
                  ),
                ),
              const SizedBox(height: 10),
            ])),
          ],
          Stagger(index: 2, child: LiveWorkSection(jobs: _extra.jobs)),
          const SizedBox(height: 14),
          Stagger(index: 3, child: DayTilesSection(extra: _extra, app: app)),
          const SizedBox(height: 20),
          Stagger(index: 4, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const HomeLabel('JALDI SE KARO'),
            Row(children: [
              _action(Icons.receipt_long_rounded, const [Color(0xFFFB923C), Color(0xFFF97316)], const Color(0x59F97316), app.g('Bill bharo'), 'Mera bijli bill bhar do'),
              const SizedBox(width: 10),
              _action(Icons.storefront_rounded, const [Color(0xFFA78BFA), Color(0xFF7C5CFF)], const Color(0x597C5CFF), app.g('Dukaan'), 'Paas ki kirana dukaan se saamaan mangwana hai'),
              const SizedBox(width: 10),
              _action(Icons.near_me_rounded, const [Color(0xFF2DD4BF), Color(0xFF0D9488)], const Color(0x592DD4BF), app.g('Rasta'), 'Paas mein kya khula hai aur rasta batao'),
              const SizedBox(width: 10),
              _action(Icons.local_taxi_rounded, const [Color(0xFFFB7185), Color(0xFFE11D48)], const Color(0x59FB7185), app.g('Cab'), 'Mere liye cab book karni hai'),
            ]),
            const SizedBox(height: 10),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              clipBehavior: Clip.none,
              child: Row(children: [
                _chip(Icons.auto_fix_high_rounded, const [Color(0xFFA78BFA), Color(0xFF7C5CFF)], app.g('Photo banao'), 'Meri ek photo edit karni hai'),
                const SizedBox(width: 8),
                _chip(Icons.movie_rounded, const [Color(0xFFFB7185), Color(0xFFE11D48)], app.g('Video banao'), 'Mere liye ek reel video banani hai'),
                const SizedBox(width: 8),
                _chip(Icons.mail_rounded, const [Color(0xFF2DD4BF), Color(0xFF0D9488)], app.g('Email likho'), 'Ek email likhna hai'),
                const SizedBox(width: 8),
                _chip(Icons.smart_display_rounded, const [Color(0xFFFFB15C), Color(0xFFFB923C)], app.g('TV'), 'TV pe kuch chalao'),
              ]),
            ),
          ])),
          const SizedBox(height: 22),
          Stagger(index: 5, child: EmployeeSection(extra: _extra, app: app)),
          const SizedBox(height: 18),
          Stagger(index: 6, child: NetworkSection(extra: _extra, app: app)),
          const SizedBox(height: 18),
          Stagger(index: 7, child: NotebookSection(extra: _extra, app: app)),
          const SizedBox(height: 18),
          Stagger(index: 8, child: LearnedSection(extra: _extra, app: app, reload: _load)),
          const SizedBox(height: 22),
          ReminderSection(app: app, onTab: widget.onTab),
          const SizedBox(height: 20),
          RoutinesSection(app: app, onTab: widget.onTab),
          const SizedBox(height: 20),
          ListsSection(app: app, onTab: widget.onTab),
          const SizedBox(height: 8),
          RecapSection(extra: _extra, app: app),
          const SizedBox(height: 16),
          const PartnerFooter(),
        ]),
      ),
    );
  }

  // v0.167 chips: proper topic badge instead of an emoji — same Night Glass pill, sharper inside.
  Widget _chip(IconData icon, List<Color> grad, String label, String prompt) => Press(
        onTap: () => _ask(prompt),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(color: const Color(0x12FFFFFF), borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x21FFFFFF))),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.circular(7),
              ),
              child: Icon(icon, color: Colors.white, size: 12),
            ),
            const SizedBox(width: 6),
            Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: C.chip)),
          ]),
        ),
      );
}

/// REMINDERS — v0.176 premium: khaali state shows the invite card (CTA jumps to chat);
/// live state groups the active reminders by day — AAJ / KAL / BAAD MEIN — with
/// time-of-day gradient tiles (subah/dopahar/shaat/raat), repeat chips, a live
/// countdown pill on the next reminder and one-tap dismiss with a snack confirmation.
class ReminderSection extends StatelessWidget {
  const ReminderSection({super.key, required this.app, this.onTab});
  final Santosh app;
  final ValueChanged<int>? onTab;

  static const Map<String, String> repeatLabel = {'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};

  /// Time-of-day look: subah / dopahar / shaam / raat — icon + gradient.
  static (IconData, List<Color>) _look(int hour) {
    if (hour >= 5 && hour < 12) return (Icons.wb_twilight_rounded, [Color(0xFFFBBF24), Color(0xFFD97706)]);
    if (hour >= 12 && hour < 17) return (Icons.wb_sunny_rounded, [Color(0xFFFB923C), Color(0xFFEA580C)]);
    if (hour >= 17 && hour < 21) return (Icons.bedtime_rounded, [Color(0xFFFB7185), Color(0xFFBE123C)]);
    return (Icons.dark_mode_rounded, [Color(0xFF818CF8), Color(0xFF4338CA)]);
  }

  String _countdown(DateTime due, DateTime now) {
    final d = due.difference(now);
    if (d.inMinutes < 1) return app.g('abhi');
    if (d.inMinutes < 60) return app.g('{x} min baad', x: '${d.inMinutes}');
    if (d.inHours < 24) return app.g('{x} ghante baad', x: '${d.inHours}');
    return app.g('{x} din baad', x: '${d.inDays}');
  }

  Future<void> _dismiss(BuildContext context, Map<String, dynamic> r) async {
    await app.api?.cancelReminder('${r['id']}');
    await app.refreshReminders();
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        behavior: SnackBarBehavior.floating,
        content: Row(children: [
          const Icon(Icons.check_rounded, size: 16, color: C.ok),
          const SizedBox(width: 8),
          Expanded(child: Text(app.g('Reminder hata diya'), style: const TextStyle(color: C.ink))),
        ]),
      ));
    }
  }

  Widget _tile(IconData icon, List<Color> grad, {double size = 40, double ic = 19}) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(13),
          boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 13, offset: const Offset(0, 4))],
        ),
        child: Icon(icon, size: ic, color: Colors.white),
      );

  Widget _groupHead(String label) => Padding(
        padding: const EdgeInsets.fromLTRB(8, 10, 8, 2),
        child: Row(children: [
          Text(app.g(label), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.faint)),
          const SizedBox(width: 8),
          Expanded(child: Container(height: 1, color: Colors.white.withOpacity(.06))),
        ]),
      );

  Widget _row(BuildContext context, Map<String, dynamic> r, {bool isNext = false}) {
    final due = DateTime.tryParse('${r['due_at']}')?.toLocal();
    final look = _look(due?.hour ?? 9);
    final rep = repeatLabel[r['repeat']];
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _tile(look.$1, look.$2),
        const SizedBox(width: 11),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['text'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, height: 1.35, color: C.ink)),
            const SizedBox(height: 3),
            Row(children: [
              Flexible(child: Text('${r['when'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: C.faint))),
              if (rep != null) ...[
                const SizedBox(width: 7),
                Icon(Icons.repeat_rounded, size: 11, color: C.faint),
                const SizedBox(width: 3),
                Text(app.g(rep), style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C.faint)),
              ],
              if (isNext && due != null) ...[
                const SizedBox(width: 7),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), color: const Color(0x24FBBF24)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.schedule_rounded, size: 10, color: Color(0xFFFCD34D)),
                    const SizedBox(width: 3),
                    Text(_countdown(due, DateTime.now()), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: Color(0xFFFCD34D))),
                  ]),
                ),
              ],
            ]),
          ]),
        ),
        const SizedBox(width: 4),
        Press(
          onTap: () => _dismiss(context, r),
          child: Container(
            width: 30, height: 30,
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: Colors.white.withOpacity(.10))),
            child: const Icon(Icons.close_rounded, size: 15, color: C.muted),
          ),
        ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final rem = app.reminders;

    // ── Khaali: the invite card — bol kar reminder banwao ──
    if (rem.isEmpty) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        HomeLabel(app.g('REMINDERS')),
        Glass(
          tint: const Color(0xFFFBBF24),
          opacity: .05,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.alarm_rounded, const [Color(0xFFFBBF24), Color(0xFFD97706)]),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.g('Koi reminder nahi'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  const SizedBox(height: 3),
                  Text(app.g('Boliye: "Kal 9 baje dawai yaad dilana" — main turant likh lungi.'),
                      style: const TextStyle(fontSize: 12.5, height: 1.45, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 10),
            Press(
              onTap: () => onTab?.call(1),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x33FBBF24))),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.forum_rounded, size: 14, color: Color(0xFFFCD34D)),
                  const SizedBox(width: 6),
                  Text(app.g('Baat shuru karo'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFFFCD34D))),
                ]),
              ),
            ),
            const SizedBox(height: 10),
            Text(app.g('Har yaad time par dugi.'), style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0x99FCD34D))),
          ]),
        ),
      ]);
    }

    // ── Live: grouped by day, countdown on the next one ──
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final tom = today.add(const Duration(days: 1));
    final groups = <String, List<Map<String, dynamic>>>{'today': [], 'tom': [], 'later': []};
    for (final r in rem) {
      final d = DateTime.tryParse('${r['due_at']}')?.toLocal();
      final day = d == null ? null : DateTime(d.year, d.month, d.day);
      final key = day == today ? 'today' : day == tom ? 'tom' : 'later';
      groups[key]!.add(r);
    }
    final nextId = '${rem.first['id']}';   // server orders by due_at — the soonest gets the countdown
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel(app.g('REMINDERS'), count: rem.length),
      Glass(
        padding: const EdgeInsets.fromLTRB(10, 4, 10, 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final g in const ['today', 'tom', 'later'])
            if (groups[g]!.isNotEmpty) ...[
              _groupHead(g == 'today' ? 'AAJ' : g == 'tom' ? 'KAL' : 'BAAD MEIN'),
              for (final r in groups[g]!) _row(context, r, isNext: '${r['id']}' == nextId),
            ],
        ]),
      ),
    ]);
  }
}

/// HOOLA KE APNE KAAM — v0.177 premium: the jobs Hoola runs all by herself, with the
/// proof attached. Khaali: the invite card (CTA jumps to chat). Live: rows grouped by
/// next-run day — AAJ / KAL / AAGE — each with a cadence tile (roz / Mon-Fri / hafte /
/// mahine / ghanta / ek baar), repeat + run-count chips, a countdown pill on the soonest
/// job, the last result as one italic line of proof, and one-tap band karo with a snack.
class RoutinesSection extends StatelessWidget {
  const RoutinesSection({super.key, required this.app, this.onTab});
  final Santosh app;
  final ValueChanged<int>? onTab;

  static const Map<String, String> repeatLabel = {'none': 'Ek baar', 'hourly': 'Har ghante', 'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};

  /// Cadence look: har rhythm ka apna rang — one glance and you know the beat.
  static (IconData, List<Color>) _look(String? repeat) {
    switch (repeat) {
      case 'hourly':
        return (Icons.timer_rounded, [Color(0xFF38BDF8), Color(0xFF0369A1)]);
      case 'daily':
        return (Icons.wb_twilight_rounded, [Color(0xFFFBBF24), Color(0xFFD97706)]);
      case 'weekdays':
        return (Icons.work_rounded, [Color(0xFFA78BFA), Color(0xFF7C5CFF)]);
      case 'weekly':
        return (Icons.event_repeat_rounded, [Color(0xFF2DD4BF), Color(0xFF0D9488)]);
      case 'monthly':
        return (Icons.calendar_month_rounded, [Color(0xFFFB7185), Color(0xFFE11D48)]);
      default:
        return (Icons.flag_rounded, [Color(0xFF94A3B8), Color(0xFF475569)]);
    }
  }

  String _countdown(DateTime due, DateTime now) {
    final d = due.difference(now);
    if (d.inMinutes < 1) return app.g('abhi');
    if (d.inMinutes < 60) return app.g('{x} min baad', x: '${d.inMinutes}');
    if (d.inHours < 24) return app.g('{x} ghante baad', x: '${d.inHours}');
    return app.g('{x} din baad', x: '${d.inDays}');
  }

  Future<void> _stop(BuildContext context, Map<String, dynamic> r) async {
    await app.cancelRoutine('${r['id']}');
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        behavior: SnackBarBehavior.floating,
        content: Row(children: [
          const Icon(Icons.check_rounded, size: 16, color: C.ok),
          const SizedBox(width: 8),
          Expanded(child: Text(app.g('Kaam band kar diya'), style: const TextStyle(color: C.ink))),
        ]),
      ));
    }
  }

  Widget _tile(IconData icon, List<Color> grad, {double size = 40, double ic = 19}) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(13),
          boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 13, offset: const Offset(0, 4))],
        ),
        child: Icon(icon, size: ic, color: Colors.white),
      );

  Widget _groupHead(String label) => Padding(
        padding: const EdgeInsets.fromLTRB(8, 10, 8, 2),
        child: Row(children: [
          Text(app.g(label), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.faint)),
          const SizedBox(width: 8),
          Expanded(child: Container(height: 1, color: Colors.white.withOpacity(.06))),
        ]),
      );

  Widget _row(BuildContext context, Map<String, dynamic> r, {bool isNext = false}) {
    final due = DateTime.tryParse('${r['next_run']}')?.toLocal();
    final look = _look(r['repeat'] as String?);
    final rep = repeatLabel[r['repeat']];
    final runs = r['run_count'] is num ? (r['run_count'] as num).toInt() : 0;
    final result = (r['last_result'] as String?) ?? '';
    final title = '${r['title'] ?? ''}';
    final instruct = '${r['instruction'] ?? ''}';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _tile(look.$1, look.$2),
        const SizedBox(width: 11),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, height: 1.35, color: C.ink)),
            if (instruct.isNotEmpty && instruct != title) ...[
              const SizedBox(height: 2),
              Text(instruct, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, height: 1.35, color: C.muted)),
            ],
            const SizedBox(height: 3),
            Row(children: [
              if (rep != null) ...[
                Icon(Icons.repeat_rounded, size: 11, color: C.faint),
                const SizedBox(width: 3),
                Text(app.g(rep), style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C.faint)),
                const SizedBox(width: 7),
              ],
              if (runs > 0) ...[
                Icon(Icons.bolt_rounded, size: 11, color: C.faint),
                const SizedBox(width: 3),
                Text(app.g('{x} baar', x: '$runs'), style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C.faint)),
                const SizedBox(width: 7),
              ],
              Expanded(
                child: Text('${r['next_run_local'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: C.faint)),
              ),
            ]),
            if (isNext && due != null) ...[
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), color: const Color(0x24FBBF24)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.schedule_rounded, size: 10, color: Color(0xFFFCD34D)),
                  const SizedBox(width: 3),
                  Text(_countdown(due, DateTime.now()), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: Color(0xFFFCD34D))),
                ]),
              ),
            ],
            if (result.isNotEmpty) ...[
              const SizedBox(height: 4),
              Row(children: [
                const Icon(Icons.verified_rounded, size: 11, color: C.ok),
                const SizedBox(width: 4),
                Expanded(child: Text(result, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11, height: 1.35, fontStyle: FontStyle.italic, color: C.faint))),
              ]),
            ],
          ]),
        ),
        const SizedBox(width: 4),
        Press(
          onTap: () => _stop(context, r),
          child: Container(
            width: 30, height: 30,
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: Colors.white.withOpacity(.10))),
            child: const Icon(Icons.close_rounded, size: 15, color: C.muted),
          ),
        ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final routines = app.routines;

    // ── Khaali: the invite card — Hoola ka pehla khud-ka-kaam bol kar banwao ──
    if (routines.isEmpty) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        HomeLabel(app.g('HOOLA KE APNE KAAM')),
        Glass(
          tint: const Color(0xFFA78BFA),
          opacity: .05,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.auto_awesome_rounded, const [Color(0xFFA78BFA), Color(0xFF7C5CFF)]),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.g('Hoola ka koi kaam chalu nahi'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  const SizedBox(height: 3),
                  Text(app.g('Boliye: "Har subah 7 baje mausam bata dena" — main roz khud karungi, yaad dilana nahi padega.'),
                      style: const TextStyle(fontSize: 12.5, height: 1.45, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 10),
            Press(
              onTap: () => onTab?.call(1),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x33A78BFA))),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.forum_rounded, size: 14, color: Color(0xFFC4B5FD)),
                  const SizedBox(width: 6),
                  Text(app.g('Baat shuru karo'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFFC4B5FD))),
                ]),
              ),
            ),
            const SizedBox(height: 10),
            Text(app.g('Mera kaam, meri zimmedari — time par, bina yaad dilaye.'), style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0x99C4B5FD))),
          ]),
        ),
      ]);
    }

    // ── Live: agle run ke din ke hisaab se — AAJ / KAL / AAGE ──
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final tom = today.add(const Duration(days: 1));
    final groups = <String, List<Map<String, dynamic>>>{'today': [], 'tom': [], 'later': []};
    for (final r in routines) {
      final d = DateTime.tryParse('${r['next_run']}')?.toLocal();
      final day = d == null ? null : DateTime(d.year, d.month, d.day);
      final key = day == today ? 'today' : day == tom ? 'tom' : 'later';
      groups[key]!.add(r);
    }
    final nextId = '${routines.first['id']}';   // server orders by next_run — the soonest gets the countdown
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel(app.g('HOOLA KE APNE KAAM'), count: routines.length),
      Glass(
        padding: const EdgeInsets.fromLTRB(10, 4, 10, 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final g in const ['today', 'tom', 'later'])
            if (groups[g]!.isNotEmpty) ...[
              _groupHead(g == 'today' ? 'AAJ' : g == 'tom' ? 'KAL' : 'AAGE'),
              for (final r in groups[g]!) _row(context, r, isNext: '${r['id']}' == nextId),
            ],
        ]),
      ),
    ]);
  }
}

/// LISTS — v0.177 premium: har list ka apna rang-tile, open items as one-tap check rows,
/// and AAJ POORE KIYE — everything ticked today stays visible with when-lines and a real
/// undo (wapas list mein). Khaali: the invite card (CTA jumps to chat).
class ListsSection extends StatelessWidget {
  const ListsSection({super.key, required this.app, this.onTab});
  final Santosh app;
  final ValueChanged<int>? onTab;

  /// List ka mood: naam dekh ke icon + gradient (shopping / kaam / ghar / office / default).
  static (IconData, List<Color>) _look(String name) {
    final n = name.toLowerCase();
    if (n.contains('shop') || n.contains('bazar') || n.contains('bazaar') || n.contains('kirana')) {
      return (Icons.shopping_cart_rounded, [Color(0xFF2DD4BF), Color(0xFF0D9488)]);
    }
    if (n.contains('kaam') || n.contains('task') || n.contains('todo')) {
      return (Icons.task_alt_rounded, [Color(0xFFA78BFA), Color(0xFF7C5CFF)]);
    }
    if (n.contains('ghar') || n.contains('home')) {
      return (Icons.home_rounded, [Color(0xFFFB7185), Color(0xFFE11D48)]);
    }
    if (n.contains('office') || n.contains('dukan')) {
      return (Icons.work_rounded, [Color(0xFFFFB15C), Color(0xFFD97706)]);
    }
    return (Icons.checklist_rounded, [Color(0xFF60A5FA), Color(0xFF2563EB)]);
  }

  Future<void> _tick(Map<String, dynamic> item) async {
    await app.api?.tickItem((item['id'] as num).toInt());
    await app.refreshLists();
  }

  Future<void> _undo(BuildContext context, Map<String, dynamic> item) async {
    await app.api?.undoItem((item['id'] as num).toInt());
    await app.refreshLists();
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        behavior: SnackBarBehavior.floating,
        content: Row(children: [
          const Icon(Icons.undo_rounded, size: 16, color: C.ok),
          const SizedBox(width: 8),
          Expanded(child: Text(app.g('Wapas list mein'), style: const TextStyle(color: C.ink))),
        ]),
      ));
    }
  }

  Widget _tile(IconData icon, List<Color> grad, {double size = 40, double ic = 19}) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: grad, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(13),
          boxShadow: [BoxShadow(color: grad.last.withOpacity(.35), blurRadius: 13, offset: const Offset(0, 4))],
        ),
        child: Icon(icon, size: ic, color: Colors.white),
      );

  Widget _groupHead(String label, {Color? pill, int? count}) => Padding(
        padding: const EdgeInsets.fromLTRB(8, 10, 8, 2),
        child: Row(children: [
          Text(app.g(label), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.faint)),
          const SizedBox(width: 8),
          Expanded(child: Container(height: 1, color: Colors.white.withOpacity(.06))),
          if (pill != null && count != null) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), color: pill.withOpacity(.16)),
              child: Text('$count', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: pill)),
            ),
          ],
        ]),
      );

  static String _title(String k) => k.isEmpty ? k : k[0].toUpperCase() + k.substring(1);

  String _when(String iso) {
    final d = DateTime.tryParse(iso)?.toLocal();
    if (d == null) return '';
    final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
    return '$h:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'am' : 'pm'}';
  }

  @override
  Widget build(BuildContext context) {
    final lists = app.lists;
    final done = app.doneToday;
    final openCount = lists.values.fold<int>(0, (n, v) => n + (v as List).length);

    // ── Khaali: the invite card — pehli list bol kar banwao ──
    if (lists.isEmpty && done.isEmpty) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        HomeLabel(app.g('LISTS')),
        Glass(
          tint: const Color(0xFF2DD4BF),
          opacity: .05,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(Icons.checklist_rounded, const [Color(0xFF2DD4BF), Color(0xFF0D9488)]),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.g('Koi list nahi'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  const SizedBox(height: 3),
                  Text(app.g('Boliye: "Doodh aur bread shopping list mein daalo" — main likh lungi, aur tick karti jaungi.'),
                      style: const TextStyle(fontSize: 12.5, height: 1.45, color: C.muted)),
                ]),
              ),
            ]),
            const SizedBox(height: 10),
            Press(
              onTap: () => onTab?.call(1),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x332DD4BF))),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.forum_rounded, size: 14, color: Color(0xFF5EEAD4)),
                  const SizedBox(width: 6),
                  Text(app.g('Baat shuru karo'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF5EEAD4))),
                ]),
              ),
            ),
            const SizedBox(height: 10),
            Text(app.g('Har chhoti cheez likhi jaayegi — poore hote hi neeche tikti jaayegi.'),
                style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0x995EEAD4))),
          ]),
        ),
      ]);
    }

    // ── Live: per-list cards with one-tap check rows + the AAJ POORE KIYE feed ──
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      HomeLabel(app.g('LISTS'), count: openCount),
      for (final e in lists.entries)
        Glass(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tile(_look(e.key).$1, _look(e.key).$2, size: 34, ic: 16),
              const SizedBox(width: 10),
              Expanded(child: Text(_title(e.key), style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800))),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), color: _look(e.key).$2.last.withOpacity(.16)),
                child: Text(app.g('{x} baaki', x: '${(e.value as List).length}'),
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: _look(e.key).$2.first)),
              ),
            ]),
            const SizedBox(height: 4),
            for (final item in (e.value as List))
              Press(
                onTap: () => _tick(item as Map<String, dynamic>),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 7),
                  child: Row(children: [
                    Container(
                      width: 22, height: 22,
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(7), border: Border.all(color: Colors.white.withOpacity(.18))),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Text(item['text'] as String? ?? '', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: C.ink))),
                    Icon(Icons.check_rounded, size: 14, color: Colors.white.withOpacity(.22)),
                  ]),
                ),
              ),
          ]),
        ),
      if (done.isNotEmpty)
        Glass(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _groupHead('AAJ POORE KIYE', count: done.length, pill: const Color(0xFF34D399)),
            for (final item in done)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
                child: Row(children: [
                  Container(
                    width: 26, height: 26,
                    decoration: BoxDecoration(color: const Color(0x2434D399), borderRadius: BorderRadius.circular(9)),
                    child: const Icon(Icons.check_rounded, size: 15, color: Color(0xFF6EE7B7)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(item['text'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, height: 1.3, color: C.chip)),
                      const SizedBox(height: 2),
                      Row(children: [
                        Flexible(child: Text(_title('${item['list_name'] ?? ''}'), maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: C.faint))),
                        if ('${item['done_at'] ?? ''}'.isNotEmpty) ...[
                          const SizedBox(width: 6),
                          Text(app.g('aaj · {x}', x: _when('${item['done_at']}')), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: C.faint)),
                        ],
                      ]),
                    ]),
                  ),
                  const SizedBox(width: 4),
                  Press(
                    onTap: () => _undo(context, item),
                    child: Container(
                      width: 30, height: 30,
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: Colors.white.withOpacity(.10))),
                      child: const Icon(Icons.undo_rounded, size: 15, color: C.muted),
                    ),
                  ),
                ]),
              ),
          ]),
        ),
    ]);
  }
}
