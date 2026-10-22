import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.98 "Call kaisi rahi?" after a call of 20 s or more: one tap 👍 / 👎, and on 👎 what went wrong. It feeds the voice
/// quality numbers (/api/voice/stats) so every change to calls is judged by her too.
class CallRateCard extends StatefulWidget {
  const CallRateCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<CallRateCard> createState() => _CallRateCardState();
}

const _reasons = {
  'cut_off': 'Beech mein kaat diya',
  'slow': 'Jawab der se aaya',
  'misheard': 'Galat samjha',
  'audio': 'Awaaz saaf nahi thi',
  'not_done': 'Kaam nahi hua',
  'too_long': 'Bahut lamba bola',
  'robotic': 'Machine jaisa laga',
};

class _CallRateCardState extends State<CallRateCard> {
  bool? _good;
  final Set<String> _picked = {};
  bool _sent = false;
  bool _busy = false;

  Future<void> _send(bool good) async {
    setState(() {
      _good = good;
      _busy = true;
    });
    try {
      await widget.app.api!.rateCall('${widget.v['call_id']}', good,
          reasons: _picked.toList(), seconds: (widget.v['seconds'] as num?)?.toInt() ?? 0);
      _sent = true;
      widget.v['rated'] = true;
    } catch (_) {}
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final done = widget.v['rated'] == true || (_sent && _good == true);
    return Glass(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.call_end_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(done ? 'Shukriya! Isse calls behtar banengi.' : '${widget.app.aName} ke saath call kaisi rahi?',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
          if (!done && _good == null) ...[
            IconButton(
                tooltip: 'Achhi', onPressed: _busy ? null : () => _send(true), icon: const Icon(Icons.thumb_up_alt_rounded, color: C.ok)),
            IconButton(
                tooltip: 'Theek nahi',
                onPressed: _busy ? null : () => setState(() => _good = false),
                icon: const Icon(Icons.thumb_down_alt_rounded, color: C.bad)),
          ],
        ]),
        if (_good == false && !_sent) ...[
          const SizedBox(height: 6),
          const Text('Kya gadbad hui? (ek ya zyada)', style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final e in _reasons.entries)
              FilterChip(
                label: Text(e.value),
                selected: _picked.contains(e.key),
                onSelected: (on) => setState(() => on ? _picked.add(e.key) : _picked.remove(e.key)),
              ),
          ]),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(onPressed: _busy ? null : () => _send(false), child: const Text('Bhejiye')),
          ),
        ],
        if (_good == false && _sent)
          const Padding(
            padding: EdgeInsets.only(top: 4),
            child: Text('Shukriya, yeh theek karne mein madad karega.', style: TextStyle(color: C.muted, fontSize: 12.5)),
          ),
      ]),
    );
  }
}
