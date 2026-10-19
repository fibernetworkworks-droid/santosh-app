import 'package:flutter/material.dart';

import '../emotion.dart';
import '../state.dart';
import 'approve_sheet.dart';
import 'glass.dart';
import 'live_santosh.dart';

const _days = ['Somvar', 'Mangalvar', 'Budhvar', 'Guruvar', 'Shukravar', 'Shanivar', 'Ravivar'];
const _months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/// Aaj: Santosh's home — greeting, Santosh himself, quick actions, approvals, reminders, his own jobs and lists.
class TodayScreen extends StatelessWidget {
  const TodayScreen({super.key, required this.app, this.onTab});
  final Santosh app;
  final ValueChanged<int>? onTab;

  String _greet() {
    final h = DateTime.now().hour;
    final part = h < 5 ? 'Shubh ratri' : h < 12 ? 'Suprabhat' : h < 17 ? 'Namaste' : h < 21 ? 'Shubh sandhya' : 'Shubh ratri';
    final name = ((app.account?['name'] as String?) ?? '').split(' ').first;
    return name.isEmpty ? part : '$part, $name';
  }

  void _ask(String text) {
    onTab?.call(1);
    app.send(text);
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

  Widget _hero(BuildContext context) {
    final pend = app.pendingApprovals.length;
    final line = pend > 0
        ? '$pend kaam aapke approval ka intezaar kar raha hai.'
        : app.reminders.isNotEmpty
            ? 'Agla reminder: ${app.reminders.first['text'] ?? ''}'
            : 'Kuch bhi boliye: bill, dukaan, cab, email, reminder.';
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
            GradientButton(label: 'Baat karein', height: 42, icon: Icons.mic_rounded, onTap: () => onTab?.call(2)),
            const SizedBox(height: 8),
            SizedBox(width: double.infinity, child: GlassButton(label: 'Likh ke boliye', height: 40, onTap: () => onTab?.call(1))),
          ]),
        ),
      ]),
    );
  }

  static const routineRepeat = {'none': 'Ek baar', 'hourly': 'Har ghante', 'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};
  static const repeatLabel = {'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => RefreshIndicator(
          onRefresh: () async {
            await app.refreshReminders();
            await app.refreshLists();
            await app.refreshRoutines();
          },
          color: C.accent,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 18, 16, 24), children: [
            Builder(builder: (context) {
              final d = DateTime.now();
              return Text('${_days[d.weekday - 1]}, ${d.day} ${_months[d.month - 1]}',
                  style: const TextStyle(fontSize: 13, color: C.muted, fontWeight: FontWeight.w700, letterSpacing: .3));
            }),
            const SizedBox(height: 2),
            Text(_greet(), style: display(26)),
            const SizedBox(height: 16),
            Stagger(index: 0, child: _hero(context)),
            const SizedBox(height: 12),
            Stagger(
              index: 1,
              child: Row(children: [
                _action(Icons.bolt_rounded, C.accentSoft, 'Bill bharo', 'Mera bijli bill bhar do'),
                const SizedBox(width: 10),
                _action(Icons.shopping_cart_outlined, const Color(0xFFC4B5FF), 'Dukaan', 'Paas ki kirana dukaan se saamaan mangwana hai'),
                const SizedBox(width: 10),
                _action(Icons.place_outlined, const Color(0xFF5EEAD4), 'Rasta', 'Paas mein kya khula hai aur rasta batao'),
                const SizedBox(width: 10),
                _action(Icons.local_taxi_outlined, const Color(0xFFFDA4AF), 'Cab', 'Mere liye cab book karni hai'),
              ]),
            ),
            const SizedBox(height: 20),
            if (app.pendingApprovals.isNotEmpty) ...[
              const _Label('APPROVAL CHAHIYE'),
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
            ],
            const _Label('REMINDERS'),
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
            const _Label('SANTOSH KE APNE KAAM'),
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
            const _Label('LISTS'),
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
          ]),
        ),
      );

  static String _title(String k) => k.isEmpty ? k : k[0].toUpperCase() + k.substring(1);
}

class _Label extends StatelessWidget {
  const _Label(this.t);
  final String t;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8, left: 4),
        child: Text(t, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.3, color: C.muted)),
      );
}
