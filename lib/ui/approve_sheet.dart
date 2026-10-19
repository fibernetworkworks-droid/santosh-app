import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// The payment / order approval sheet: everything shown comes from the server's record,
/// and a deliberate slide (not a tap) approves it.
Future<void> showApproveSheet(BuildContext context, Santosh app, Map<String, dynamic> v) => showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: const Color(0x99060412),
      builder: (_) => _ApproveSheet(app: app, v: v),
    );

class _ApproveSheet extends StatelessWidget {
  const _ApproveSheet({required this.app, required this.v});
  final Santosh app;
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final items = (v['items'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final disclosures = (v['disclosures'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final demo = v['demo'] == true;
    final title = (v['title'] as String? ?? '').replaceFirst('[DEMO] ', '');
    return Glass(
      radius: 34,
      opacity: .1,
      tint: const Color(0xFF1A143A),
      padding: EdgeInsets.fromLTRB(22, 12, 22, 22 + MediaQuery.paddingOf(context).bottom),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Center(child: Container(width: 44, height: 5, decoration: BoxDecoration(color: const Color(0x47FFFFFF), borderRadius: BorderRadius.circular(3)))),
        const SizedBox(height: 14),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Image.asset('assets/images/santosh_thinking.png', height: 74),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('$title?', style: display(19)),
              const SizedBox(height: 2),
              const Text('Santosh ne aapke liye taiyaar kiya', style: TextStyle(color: C.muted, fontSize: 13)),
            ]),
          ),
        ]),
        const SizedBox(height: 16),
        if ((v['amount'] as String? ?? '').isNotEmpty)
          Center(
            child: Column(children: [
              const Text('KUL RAKAM', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.muted, letterSpacing: .8)),
              TweenAnimationBuilder<double>(
                tween: Tween(begin: .85, end: 1),
                duration: const Duration(milliseconds: 500),
                curve: Curves.easeOutBack,
                builder: (context, s, c) => Transform.scale(scale: s, child: c),
                child: Text(v['amount'] as String, style: display(44)),
              ),
            ]),
          ),
        if (demo)
          const Center(
            child: Padding(
              padding: EdgeInsets.only(top: 6),
              child: Pill('DEMO · ASLI PAISE NAHI KATENGE', fg: C.accentSoft, bg: Color(0x24FFB15C)),
            ),
          ),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(18), border: Border.all(color: const Color(0x1FFFFFFF))),
          child: Column(children: [
            if ((v['payee'] as String? ?? '').isNotEmpty) _row('Kisko', v['payee'] as String),
            for (final i in items.take(12)) _row(i['name'] as String? ?? '', i['price'] as String? ?? ''),
            if ((v['pay_method'] as String? ?? '').isNotEmpty) _row('Payment', v['pay_method'] as String, last: true),
          ]),
        ),
        if (disclosures.isNotEmpty) ...[
          // shopping: seller, delivery, returns, origin, customer care — plain facts, shown before paying
          const SizedBox(height: 10),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 190),
            child: SingleChildScrollView(
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                for (final d in disclosures)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      SizedBox(
                        width: 112,
                        child: Text(d['label'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12, height: 1.35)),
                      ),
                      Expanded(child: Text(d['value'] as String? ?? '', style: const TextStyle(fontSize: 12, height: 1.35))),
                    ]),
                  ),
              ]),
            ),
          ),
        ],
        const SizedBox(height: 12),
        const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.verified_user_outlined, color: C.ok, size: 18),
          SizedBox(width: 8),
          Expanded(
            child: Text('Rakam aur payee server ke record se hain. Santosh kabhi PIN, OTP ya card number nahi maangega.',
                style: TextStyle(fontSize: 12.5, color: C.muted, height: 1.4)),
          ),
        ]),
        const SizedBox(height: 16),
        SlideToApprove(
          label: 'Slide karke approve karein',
          onDone: () async {
            Navigator.of(context).pop();
            // money never moves from the lock screen: the phone's own PIN/fingerprint first
            if (await Native.isLocked() && !await Native.requestUnlock()) return;
            await app.decideBazar(v['id'] as String, 'approve');
          },
        ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Abhi nahi', style: TextStyle(color: C.chip, fontWeight: FontWeight.w700)),
        ),
      ]),
    );
  }

  Widget _row(String k, String val, {bool last = false}) => Container(
        padding: const EdgeInsets.symmetric(vertical: 11),
        decoration: BoxDecoration(border: last ? null : const Border(bottom: BorderSide(color: Color(0x14FFFFFF)))),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: Text(k, style: const TextStyle(color: C.muted, fontSize: 13.5))),
          const SizedBox(width: 12),
          Flexible(child: Text(val, textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5))),
        ]),
      );
}

/// Drag the knob to the end to confirm. Harder to trigger by accident than a button.
class SlideToApprove extends StatefulWidget {
  const SlideToApprove({super.key, required this.label, required this.onDone});
  final String label;
  final Future<void> Function() onDone;
  @override
  State<SlideToApprove> createState() => _SlideToApproveState();
}

class _SlideToApproveState extends State<SlideToApprove> with SingleTickerProviderStateMixin {
  double _x = 0;
  bool _done = false;
  late final AnimationController _hint = AnimationController(vsync: this, duration: const Duration(milliseconds: 1800))..repeat(reverse: true);

  @override
  void dispose() {
    _hint.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, box) {
        const knob = 52.0, h = 62.0;
        final max = box.maxWidth - knob - 10;
        return Semantics(
          button: true,
          label: widget.label,
          onTap: _done ? null : () => _finish(),
          child: Container(
            height: h,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFFFB15C), Color(0xFFFF9A3C)]),
              borderRadius: BorderRadius.circular(22),
              boxShadow: const [BoxShadow(color: Color(0x66FF963C), blurRadius: 28, offset: Offset(0, 12))],
            ),
            child: Stack(alignment: Alignment.centerLeft, children: [
              Center(
                child: AnimatedOpacity(
                  opacity: (1 - _x / max * 1.4).clamp(0.0, 1.0),
                  duration: const Duration(milliseconds: 80),
                  child: Text(_done ? 'Ho raha hai…' : widget.label,
                      style: const TextStyle(color: C.onAccent, fontWeight: FontWeight.w800, fontSize: 15.5)),
                ),
              ),
              AnimatedBuilder(
                animation: _hint,
                builder: (context, c) => Positioned(left: 5 + _x + (_x == 0 && !_done ? _hint.value * 10 : 0), child: c!),
                child: GestureDetector(
                  onHorizontalDragUpdate: _done ? null : (d) => setState(() => _x = (_x + d.delta.dx).clamp(0, max)),
                  onHorizontalDragEnd: _done
                      ? null
                      : (_) {
                          if (_x > max * .86) {
                            _finish();
                          } else {
                            setState(() => _x = 0);
                          }
                        },
                  child: Container(
                    width: knob,
                    height: knob,
                    decoration: BoxDecoration(color: C.onAccent, borderRadius: BorderRadius.circular(17)),
                    child: Icon(_done ? Icons.check_rounded : Icons.chevron_right_rounded, color: C.accentSoft, size: 28),
                  ),
                ),
              ),
            ]),
          ),
        );
      });

  Future<void> _finish() async {
    HapticFeedback.heavyImpact();
    setState(() => _done = true);
    await widget.onDone();
  }
}
