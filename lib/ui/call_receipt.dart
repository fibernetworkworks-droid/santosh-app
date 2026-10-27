import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.91 Call ka hisaab: after a voice call, what was decided and what really ran (steps come from the real tool
/// results on the server, never from the model's words).
class CallReceiptCard extends StatelessWidget {
  const CallReceiptCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  List<String> _l(String k) => ((v[k] as List?) ?? const []).map((e) => '$e').where((e) => e.trim().isNotEmpty).toList();

  Widget _section(String title, IconData icon, Color color, List<String> lines) {
    if (lines.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 12.5)),
        const SizedBox(height: 2),
        for (final l in lines)
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(icon, size: 15, color: color),
              const SizedBox(width: 6),
              Expanded(child: Text(l, style: const TextStyle(color: C.chip, fontSize: 13))),
            ]),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final secs = (v['seconds'] as num?)?.toInt() ?? 0;
    final mins = secs < 60 ? '$secs sec' : '${(secs / 60).round()} min';
    final summary = '${v['summary'] ?? ''}'.trim();
    final pending = [..._l('running'), ..._l('follow_up')];
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Glass(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.call_end_rounded, color: C.teal, size: 20),
            const SizedBox(width: 8),
            const Expanded(child: Text('Call ka hisaab', style: TextStyle(fontWeight: FontWeight.w800))),
            Text(mins, style: const TextStyle(color: C.faint, fontSize: 12)),
          ]),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(summary, style: const TextStyle(color: C.ink, fontSize: 13.5)),
          ],
          _section('Tay hua', Icons.handshake_outlined, C.accent, _l('decisions')),
          _section('Ho gaya', Icons.check_circle_rounded, C.ok, _l('done')),
          _section('Nahi ho paya', Icons.error_outline_rounded, C.bad, _l('failed')),
          _section('Baaki / chal raha hai', Icons.schedule_rounded, C.warn, pending),
          if (v['ai'] != true && summary.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('Sirf asli kadam dikhaye gaye hain.', style: TextStyle(color: C.faint, fontSize: 11.5)),
            ),
        ]),
      ),
    );
  }
}
