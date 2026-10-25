import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.158 one plain line above the chat while Hoola works: what is running, where, and Rokiye (stop).
/// (It replaces the 3D Work Theatre, which is gone.)
const _where = {
  'email': 'Email', 'browser': 'Hoola ka browser', 'payment': 'Bill / Payment', 'bluetooth': 'Ghar / Bluetooth',
  'network': 'Hoola Network', 'pc': 'Aapka PC', 'website': 'Website / App', 'work': 'Kaam',
};
const _icon = {
  'email': Icons.mail_rounded, 'browser': Icons.public_rounded, 'payment': Icons.currency_rupee_rounded,
  'bluetooth': Icons.bluetooth_rounded, 'network': Icons.hub_rounded, 'pc': Icons.desktop_windows_rounded,
  'website': Icons.web_rounded, 'work': Icons.bolt_rounded,
};

String _detail(Map<String, dynamic> w) {
  final d = Map<String, dynamic>.from(w['data'] as Map? ?? const {});
  final v = d['account'] ?? d['url'] ?? d['biller'] ?? d['device'] ?? d['peer'] ?? d['app'];
  return v is String && v.isNotEmpty ? v : '';
}

class WorkStrip extends StatefulWidget {
  const WorkStrip({super.key, required this.app});
  final Santosh app;
  @override
  State<WorkStrip> createState() => _WorkStripState();
}

class _WorkStripState extends State<WorkStrip> {
  bool _stopping = false;
  Object? _last;

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final w = app.work;
    if (w == null) return const SizedBox.shrink();
    if (!identical(w, _last)) {
      _last = w;
      if (w['phase'] == 'start') _stopping = false;
    }
    final scene = w['scene'] as String? ?? 'work';
    final phase = w['phase'] as String? ?? 'start';
    final status = switch (phase) {
      'done' => app.g('Ho gaya'),
      'error' => app.g('Nahi ho paya'),
      'waiting' => app.g('Aapki haan chahiye'),
      'stopped' => app.g('Roka gaya'),
      _ => app.g('Chal raha hai'),
    };
    final col = switch (phase) { 'done' => C.ok, 'error' => C.bad, 'stopped' => C.faint, _ => C.accentSoft };
    final detail = _detail(w);
    final steps = app.workLog.length;
    return Glass(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 6),
      padding: const EdgeInsets.fromLTRB(12, 6, 4, 6),
      radius: 18,
      child: Row(children: [
        Icon(_icon[scene] ?? Icons.bolt_rounded, size: 18, color: col),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(w['label'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
            Text(
                [status, _where[scene] ?? app.g('Kaam'), if (detail.isNotEmpty) detail, if (steps > 1) app.g('{x} kadam', x: '$steps')].join(' · '),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: col)),
          ]),
        ),
        if (phase == 'start')
          TextButton.icon(
            onPressed: _stopping
                ? null
                : () async {
                    setState(() => _stopping = true);
                    await app.stopWork();
                  },
            style: TextButton.styleFrom(foregroundColor: const Color(0xFFFCA5A5), minimumSize: const Size(44, 40)),
            icon: const Icon(Icons.stop_rounded, size: 18),
            label: Text(_stopping ? app.g('Rok raha…') : app.g('Rokiye'), style: const TextStyle(fontWeight: FontWeight.w800)),
          )
        else
          IconButton(tooltip: app.g('Band kijiye'), onPressed: app.closeWork, icon: const Icon(Icons.close_rounded, color: C.muted, size: 20)),
      ]),
    );
  }
}
