import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// Reminders and lists in one place.
class TodayScreen extends StatelessWidget {
  const TodayScreen({super.key, required this.app});
  final Santosh app;

  static const repeatLabel = {'daily': 'Roz', 'weekdays': 'Mon–Fri', 'weekly': 'Har hafte', 'monthly': 'Har mahine'};

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => RefreshIndicator(
          onRefresh: () async {
            await app.refreshReminders();
            await app.refreshLists();
          },
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
            Text('Aaj aur aage', style: display(28)),
            const SizedBox(height: 14),
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
                        decoration: BoxDecoration(color: const Color(0xFFEDE9FE), borderRadius: BorderRadius.circular(12)),
                        child: const Icon(Icons.notifications_active_outlined, color: C.accent, size: 20),
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
