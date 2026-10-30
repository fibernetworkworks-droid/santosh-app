import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.274 "Call ki awaaz": which engine speaks her calls - Gemini (the default voice) or Real voice (OpenAI: more
/// human, breaths and "hmm", costs more). The choice works from the next call; the server falls back to Gemini on
/// its own (and says why here) when there is no key, the month's budget or her minutes are used up.
class VoiceEngineScreen extends StatefulWidget {
  const VoiceEngineScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<VoiceEngineScreen> createState() => _VoiceEngineScreenState();
}

class _VoiceEngineScreenState extends State<VoiceEngineScreen> {
  Map<String, dynamic>? _v;
  String? _err;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await widget.app.api!.voiceEngine();
      if (mounted) setState(() {
        _v = v;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _pick(String engine) async {
    if (_busy || _v?['chosen'] == engine) return;
    setState(() => _busy = true);
    try {
      final v = await widget.app.api!.voiceEngineSet(engine);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _option(String engine, IconData icon, String title, String body, {bool enabled = true}) {
    final chosen = _v?['chosen'] == engine;
    return Opacity(
      opacity: enabled ? 1 : .5,
      child: GestureDetector(
        onTap: enabled && !_busy ? () => _pick(engine) : null,
        child: Glass(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(icon, color: chosen ? C.accent : C.muted),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5)),
                const SizedBox(height: 4),
                Text(body, style: const TextStyle(color: C.muted, fontSize: 13)),
              ]),
            ),
            Icon(chosen ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                color: chosen ? C.accent : C.muted),
          ]),
        ),
      ),
    );
  }

  String _num(dynamic x) => (x as num?)?.toStringAsFixed(0) ?? '0';

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final allowed = v?['allowed'] == true;
    final why = '${v?['why'] ?? ''}';
    return Scaffold(
      appBar: AppBar(title: const Text('Call ki awaaz')),
      body: v == null
          ? Center(child: _err == null ? const CircularProgressIndicator() : Padding(padding: const EdgeInsets.all(24), child: Text(_err!)))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
                _option('gemini', Icons.graphic_eq_rounded, 'Gemini awaaz',
                    'Abhi wali awaaz. Tez, sasti, har cheez ke liye tested.'),
                _option('openai', Icons.auto_awesome_rounded, 'Real voice (OpenAI)',
                    allowed
                        ? 'Zyada insaan jaisi: sochte waqt "hmm...", lambi baat ke baad halki saans, naram awaaz. Thoda mehnga.'
                        : 'Abhi trial mein hai - jald hi sabke liye.',
                    enabled: allowed),
                if (why.isNotEmpty)
                  Glass(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(14),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const Icon(Icons.info_outline_rounded, color: C.accentSoft, size: 20),
                      const SizedBox(width: 10),
                      Expanded(child: Text(why, style: const TextStyle(fontSize: 13.5))),
                    ]),
                  ),
                if (allowed)
                  Glass(
                    padding: const EdgeInsets.all(14),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const Text('Real voice - is mahine', style: TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      Text('Kharcha: ₹${(v['month_inr'] as num?)?.toStringAsFixed(2) ?? '0'} / ₹${_num(v['month_budget_inr'])}',
                          style: const TextStyle(fontSize: 13.5)),
                      const SizedBox(height: 4),
                      Text('Aapke minute: ${v['my_minutes'] ?? 0} / ${v['my_minutes_cap'] ?? 0}',
                          style: const TextStyle(fontSize: 13.5)),
                      const SizedBox(height: 8),
                      const Text('Budget ya minute khatam hone par call apne aap Gemini awaaz par chalti hai.',
                          style: TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                const Padding(
                  padding: EdgeInsets.only(top: 14),
                  child: Text('Badlaav agli call se lagta hai.', style: TextStyle(color: C.muted, fontSize: 12.5)),
                ),
              ]),
            ),
    );
  }
}
