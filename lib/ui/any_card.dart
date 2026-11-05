import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'glass.dart';

/// v0.550 EK JAISA: the plain card for an event kind this app has no screen for yet - the same thing the web
/// console's default card shows (title, one line, status, a few facts, a link). Nothing on it acts by itself:
/// a card that needs her tap always has its own screen; this one only makes sure she SEES every update.
class AnyEventCard extends StatelessWidget {
  const AnyEventCard({super.key, required this.v});
  final Map<String, dynamic> v;

  static const _titleKeys = ['title', 'name', 'label', 'what', 'subject', 'number'];
  static const _lineKeys = ['say', 'summary', 'text', 'reason', 'message'];
  static const _skip = {'id', 'tenant', 'tenant_id', 'conv', 'conversation_id', 'url', 'link', 'open_url', 'status', '_kind'};

  static String _str(Object? o) => o is String ? o.trim() : (o is num || o is bool) ? '$o' : '';

  @override
  Widget build(BuildContext context) {
    final kind = _str(v['_kind']);
    final tk = _titleKeys.firstWhere((k) => _str(v[k]).isNotEmpty, orElse: () => '');
    final lk = _lineKeys.firstWhere((k) => _str(v[k]).isNotEmpty && k != tk, orElse: () => '');
    final label = kind.replaceAll('_', ' ');
    final title = tk.isEmpty ? label : _str(v[tk]);
    var line = lk.isEmpty ? '' : _str(v[lk]);
    if (line.length > 600) line = '${line.substring(0, 600)}…';
    final status = _str(v['status']);
    final link = [_str(v['url']), _str(v['link']), _str(v['open_url'])]
        .firstWhere((u) => u.startsWith('https://') || u.startsWith('http://'), orElse: () => '');
    final facts = <MapEntry<String, String>>[];
    for (final e in v.entries) {
      if (facts.length >= 5) break;
      if (_skip.contains(e.key) || e.key == tk || e.key == lk || e.key.startsWith('_')) continue;
      final s = _str(e.value);
      if (s.isEmpty || s.length > 80) continue;
      facts.add(MapEntry(e.key.replaceAll('_', ' '), s));
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.widgets_rounded, color: C.violet, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            if (status.isNotEmpty) Pill(status.toUpperCase())
            else if (tk.isNotEmpty) Pill(label.toUpperCase()),
          ]),
          if (line.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(line, style: const TextStyle(color: C.chip, fontSize: 14, height: 1.4)),
          ],
          for (final f in facts)
            Padding(
              padding: const EdgeInsets.only(top: 3),
              child: Text('${f.key}: ${f.value}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ),
          if (link.isNotEmpty) ...[
            const SizedBox(height: 10),
            GlassButton(label: 'Kholo', icon: Icons.open_in_new_rounded, height: 42,
                onTap: () => launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication).catchError((_) => false)),
          ],
        ]),
      ),
    );
  }
}
