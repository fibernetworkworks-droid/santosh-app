import 'package:flutter/material.dart';

import '../emotion.dart';
import '../state.dart';
import 'approve_sheet.dart';
import 'glass.dart';
import 'live_santosh.dart';

/// "Jab aap offline the": what Santosh kept doing while the phone was off or the app was away.
class CatchUpScreen extends StatelessWidget {
  const CatchUpScreen({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  String _time(String iso) {
    final t = DateTime.tryParse(iso)?.toLocal();
    if (t == null) return '';
    final h = t.hour % 12 == 0 ? 12 : t.hour % 12;
    return '$h:${t.minute.toString().padLeft(2, '0')}${t.hour < 12 ? ' AM' : ' PM'}';
  }

  @override
  Widget build(BuildContext context) {
    final items = (data['items'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final pending = (data['pending'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final hours = (data['away_hours'] as num? ?? 0).toInt();
    return Scaffold(
      body: Aurora(
        child: SafeArea(
          child: ListView(padding: const EdgeInsets.fromLTRB(18, 18, 18, 24), children: [
            Stagger(
              index: 0,
              child: Glass(
                radius: 28,
                padding: const EdgeInsets.fromLTRB(18, 16, 6, 0),
                child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 18),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Welcome back!', style: display(24)),
                        const SizedBox(height: 6),
                        Text('Aap $hours ghante door the. Maine kaam jaari rakha. Yeh raha hisaab:',
                            style: const TextStyle(fontSize: 13.5, height: 1.45, color: C.chip)),
                      ]),
                    ),
                  ),
                  const LiveSantosh(feeling: Mood.happy, size: 140, aura: true),
                ]),
              ),
            ),
            const SizedBox(height: 14),
            Stagger(
              index: 1,
              child: Row(children: [
                _stat('${items.length}', 'kaam / khabar', C.ok),
                const SizedBox(width: 8),
                _stat('${pending.length}', 'approve karein', C.accentSoft),
              ]),
            ),
            const SizedBox(height: 18),
            if (pending.isNotEmpty) ...[
              const Caption('APKE TAP KA INTEZAAR'),
              for (final a in pending)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Glass(
                    border: const Color(0x66FFB15C),
                    child: Row(children: [
                      Expanded(
                        child: Text('${(a['title'] as String? ?? '').replaceFirst('[DEMO] ', '')}  ${a['amount'] ?? ''}',
                            style: const TextStyle(fontWeight: FontWeight.w700)),
                      ),
                      GradientButton(label: 'Approve', height: 38, onTap: () => showApproveSheet(context, app, a)),
                    ]),
                  ),
                ),
              const SizedBox(height: 8),
            ],
            if (items.isNotEmpty) ...[
              const Caption('JAB AAP OFFLINE THE'),
              Glass(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                child: Column(children: [
                  for (final (i, it) in items.indexed)
                    Stagger(
                      index: i + 2,
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(border: i == items.length - 1 ? null : const Border(bottom: BorderSide(color: C.line))),
                        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          SizedBox(width: 66, child: Text(_time(it['at'] as String? ?? ''), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.accentSoft))),
                          Expanded(child: Text(it['text'] as String? ?? '', style: const TextStyle(fontSize: 13.5, height: 1.4))),
                        ]),
                      ),
                    ),
                ]),
              ),
            ],
            const SizedBox(height: 18),
            GlassButton(label: 'Theek hai, aage badhiye', height: 52, onTap: () => Navigator.of(context).pop()),
          ]),
        ),
      ),
    );
  }

  Widget _stat(String n, String label, Color c) => Expanded(
        child: Glass(
          radius: 18,
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Column(children: [
            Text(n, style: display(24, color: c)),
            Text(label, style: const TextStyle(fontSize: 11.5, color: C.muted, fontWeight: FontWeight.w600)),
          ]),
        ),
      );
}
