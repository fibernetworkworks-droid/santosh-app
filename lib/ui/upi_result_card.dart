import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// v0.109 After "Paisa bhejo": what happened. The UPI app's own answer (✅ / ❌ / ⏳), or a question when the app
/// said nothing ("Ho gaya / Nahi hua"). When an app refused the payment link, she can copy the UPI ID and send it
/// in the app herself. Hoola never moves money and never sees the UPI PIN.
class UpiResultCard extends StatefulWidget {
  const UpiResultCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<UpiResultCard> createState() => _UpiResultCardState();
}

class _UpiResultCardState extends State<UpiResultCard> {
  bool _busy = false;
  String _err = '';

  String _s(String k) => '${widget.v[k] ?? ''}';

  Future<void> _answer(String a) async {
    setState(() { _busy = true; _err = ''; });
    try {
      await widget.app.api!.upiResult(_s('txn_ref'), answer: a);   // the server sends the updated card
    } catch (e) {
      if (mounted) setState(() => _err = 'Nahi bheja ja saka: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _copyAndOpen() async {
    final vpa = _s('vpa');
    await Clipboard.setData(ClipboardData(text: vpa));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('UPI ID copy ho gaya: $vpa · amount ${_s('amount')} khud likhiye')));
    final res = await Native.openExternal(package: _s('package'));
    if (res != 'ok' && mounted) setState(() => _err = res);
  }

  @override
  Widget build(BuildContext context) {
    final st = _s('status');
    final ask = widget.v['ask'] == true && st != 'completed' && st != 'failed';
    final (IconData icon, Color col, String head) = switch (st) {
      'completed' => (Icons.check_circle_rounded, C.ok, 'Paise chale gaye'),
      'failed' => (Icons.cancel_rounded, C.bad, 'Paise nahi gaye'),
      'pending' => (Icons.schedule_rounded, C.warn, 'Bank se pakka hona baaki'),
      _ => (Icons.help_outline_rounded, C.warn, 'Payment hua?'),
    };
    final who = _s('said_by') == 'app'
        ? '${_s('app').isEmpty ? 'UPI app' : _s('app')} ne bataya'
        : _s('said_by') == 'owner' ? 'Aapne bataya' : '';
    final tail = _s('ref_tail');
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Glass(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: col, size: 22),
            const SizedBox(width: 8),
            Expanded(child: Text(head, style: const TextStyle(fontWeight: FontWeight.w800))),
            Text(_s('amount'), style: TextStyle(color: col, fontWeight: FontWeight.w800, fontSize: 16)),
          ]),
          const SizedBox(height: 6),
          Text('${_s('name')} · ${_s('vpa')}', style: const TextStyle(color: C.chip, fontSize: 13)),
          if (_s('reason').isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s('reason'), style: const TextStyle(color: C.bad, fontSize: 12.5))),
          if (who.isNotEmpty || tail.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text([if (who.isNotEmpty) who, if (tail.isNotEmpty) 'UPI ref ...$tail'].join(' · '),
                  style: const TextStyle(color: C.faint, fontSize: 11.5)),
            ),
          if (ask) ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: GradientButton(label: 'Ho gaya', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : () => _answer('done'))),
              const SizedBox(width: 8),
              Expanded(child: GlassButton(label: 'Nahi hua', icon: Icons.close_rounded, height: 42, onTap: _busy ? null : () => _answer('not'))),
            ]),
          ],
          if (widget.v['blocked'] == true && st != 'completed' && _s('vpa').isNotEmpty) ...[
            const SizedBox(height: 8),
            GlassButton(
                label: 'UPI ID copy karke ${_s('app').isEmpty ? 'app' : _s('app')} kholo',
                icon: Icons.copy_rounded,
                height: 42,
                onTap: _copyAndOpen),
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text('Kuch apps kisi vyakti ko link se payment rok deti hain; app mein UPI ID paste karke bhejiye.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ),
          ],
          if (_err.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 6), child: Text(_err, style: const TextStyle(color: C.bad, fontSize: 12))),
        ]),
      ),
    );
  }
}
