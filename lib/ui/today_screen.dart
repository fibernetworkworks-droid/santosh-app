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

  Widget _action(IconData icon, Color c, String label, String prompt) => Expanded(
        child: Press(
          onTap: () => _ask(prompt),
          child: Glass(
            radius: 20,
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: Column(children: [
              Icon(icon, color: c, size: 24),
              const SizedBox(height: 7),
              Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
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
        Text(DayTilesSection._wIcon(code, isDay), style: const TextStyle(fontSize: 12)),
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

  static const routineRepeat = {'none': 'Ek baar', 'hourly': 'Har ghante', 'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};
  static const repeatLabel = {'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};

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
              _action(Icons.bolt_rounded, C.accentSoft, 'Bill bharo', 'Mera bijli bill bhar do'),
              const SizedBox(width: 10),
              _action(Icons.shopping_cart_outlined, const Color(0xFFC4B5FF), 'Dukaan', 'Paas ki kirana dukaan se saamaan mangwana hai'),
              const SizedBox(width: 10),
              _action(Icons.place_outlined, const Color(0xFF5EEAD4), 'Rasta', 'Paas mein kya khula hai aur rasta batao'),
              const SizedBox(width: 10),
              _action(Icons.local_taxi_outlined, const Color(0xFFFDA4AF), 'Cab', 'Mere liye cab book karni hai'),
            ]),
            const SizedBox(height: 10),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              clipBehavior: Clip.none,
              child: Row(children: [
                _chip('📷 Photo banao', 'Meri ek photo edit karni hai'),
                const SizedBox(width: 8),
                _chip('🎬 Video banao', 'Mere liye ek reel video banani hai'),
                const SizedBox(width: 8),
                _chip('📝 Email likho', 'Ek email likhna hai'),
                const SizedBox(width: 8),
                _chip('📺 TV', 'TV pe kuch chalao'),
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
          const HomeLabel('REMINDERS'),
          if (app.reminders.isEmpty)
            const Glass(child: Text('Koi reminder nahi. Chat mein boliye: "Kal 9 baje dawai yaad dilana".', style: TextStyle(color: C.muted)))
          else
            Glass(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              child: Column(children: [
                for (final r in app.reminders)
                  ListTile(
                    leading: Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(color: const Color(0x24FFB15C), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.notifications_active_outlined, color: C.accentSoft, size: 20),
                    ),
                    title: Text(r['text'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text([r['when'], repeatLabel[r['repeat']]].whereType<String>().join(' · ')),
                    trailing: IconButton(
                      tooltip: 'Reminder hatao',
                      icon: const Icon(Icons.close_rounded, color: C.muted),
                      onPressed: () async {
                        await app.api?.cancelReminder(r['id'] as String);
                        await app.refreshReminders();
                      },
                    ),
                  ),
              ]),
            ),
          const SizedBox(height: 20),
          const HomeLabel('HOOLA KE APNE KAAM'),
          if (app.routines.isEmpty)
            const Glass(child: Text('Hoola khud se koi kaam nahi kar raha. Boliye: "Har subah 7 baje Pune ka mausam aur aaj ke reminders bata dena".', style: TextStyle(color: C.muted)))
          else
            Glass(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              child: Column(children: [
                for (final r in app.routines)
                  ListTile(
                    leading: Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(gradient: C.gradient, borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.auto_awesome_rounded, color: C.onAccent, size: 20),
                    ),
                    title: Text(r['title'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text([
                      routineRepeat[r['repeat']] ?? '',
                      if (r['next_run_local'] != null) 'Agla: ${r['next_run_local']}',
                    ].where((x) => x.isNotEmpty).join(' · ')),
                    trailing: IconButton(
                      tooltip: 'Yeh kaam band karo',
                      icon: const Icon(Icons.close_rounded, color: C.muted),
                      onPressed: () => app.cancelRoutine(r['id'] as String),
                    ),
                  ),
              ]),
            ),
          const SizedBox(height: 20),
          const HomeLabel('LISTS'),
          if (app.lists.isEmpty)
            const Glass(child: Text('Koi list nahi. Boliye: "Doodh aur bread shopping list mein daalo".', style: TextStyle(color: C.muted)))
          else
            for (final e in app.lists.entries)
              Glass(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.fromLTRB(16, 12, 8, 6),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_title(e.key), style: display(19, w: FontWeight.w700)),
                  for (final item in (e.value as List))
                    CheckboxListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                      value: false,
                      title: Text(item['text'] as String? ?? ''),
                      onChanged: (_) async {
                        await app.api?.tickItem((item['id'] as num).toInt());
                        await app.refreshLists();
                      },
                    ),
                ]),
              ),
          const SizedBox(height: 8),
          RecapSection(extra: _extra, app: app),
          const SizedBox(height: 16),
          const PartnerFooter(),
        ]),
      ),
    );
  }

  Widget _chip(String label, String prompt) => Press(
        onTap: () => _ask(prompt),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
          decoration: BoxDecoration(color: const Color(0x12FFFFFF), borderRadius: BorderRadius.circular(999), border: Border.all(color: const Color(0x21FFFFFF))),
          child: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: C.chip)),
        ),
      );

  static String _title(String k) => k.isEmpty ? k : k[0].toUpperCase() + k.substring(1);
}
