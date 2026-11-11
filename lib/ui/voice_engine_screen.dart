import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.816 TEEN AWAAZEIN: plus Grok Voice 3.0, GPT-Live-1 and Phonic 1 (from the server's `engines` list).
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

  List<Map<String, dynamic>> _engines(Map<String, dynamic> v) => [
        for (final e in (v['engines'] as List? ?? const []))
          if (e is Map) Map<String, dynamic>.from(e)
      ];

  static const Map<String, IconData> _icons = {
    'grok': Icons.bolt_rounded,
    'gptlive': Icons.hearing_rounded,
    'phonic': Icons.record_voice_over_rounded,
  };

  static const Map<String, String> _blurb = {
    'grok': 'xAI. Ranked near the top for voice quality and answers quickly.',
    'gptlive': 'OpenAI. Listens while it talks, like a real phone call. Has a Hindi voice.',
    'phonic': 'Ranked first for voice quality. Voices with an Indian accent.',
  };

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final allowed = v?['allowed'] == true;
    final why = '${v?['why'] ?? ''}';
    return Scaffold(
      appBar: AppBar(title: const Text('Call voice')),
      body: v == null
          ? Center(child: _err == null ? const CircularProgressIndicator() : Padding(padding: const EdgeInsets.all(24), child: Text(_err!)))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
                _option('gemini', Icons.graphic_eq_rounded, 'Gemini voice',
                    'The current voice. Fast, cheap, tested for everything.'),
                _option('openai', Icons.auto_awesome_rounded, 'Real voice (OpenAI)',
                    allowed
                        ? 'More human-like: "hmm..." while thinking, a light breath after a long sentence, a soft voice. Slightly costlier.'
                        : 'In trial for now - soon for everyone.',
                    enabled: allowed),
                // v0.816 TEEN AWAAZEIN: three more voices she can pick, each with its price and its own reason
                for (final e in _engines(v))
                  _option(
                      '${e['engine']}',
                      _icons[e['engine']] ?? Icons.record_voice_over_rounded,
                      '${e['name']}',
                      (e['allowed'] == true)
                          ? '${_blurb[e['engine']] ?? ''} About ₹${(e['inr_per_min'] as num?)?.toStringAsFixed(1) ?? '?'} a minute.'
                              '${(e['ready'] == true || '${e['why'] ?? ''}'.isEmpty) ? '' : '\n${e['why']}'}'
                          : 'Not open for your account yet.',
                      enabled: e['allowed'] == true),
                for (final e in _engines(v).where((e) => e['engine'] == v['chosen']))
                  Glass(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(14),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${e['name']} - this month', style: const TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      Text('Cost: ₹${(e['month_inr'] as num?)?.toStringAsFixed(2) ?? '0'} / ₹${_num(e['month_budget_inr'])}',
                          style: const TextStyle(fontSize: 13.5)),
                      const SizedBox(height: 4),
                      Text('Your minutes: ${e['my_minutes'] ?? 0} / ${e['my_minutes_cap'] ?? 0}',
                          style: const TextStyle(fontSize: 13.5)),
                      const SizedBox(height: 8),
                      const Text('When the budget or minutes run out, the call automatically uses the Gemini voice.',
                          style: TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
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
                      const Text('Real voice - this month', style: TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      Text('Cost: ₹${(v['month_inr'] as num?)?.toStringAsFixed(2) ?? '0'} / ₹${_num(v['month_budget_inr'])}',
                          style: const TextStyle(fontSize: 13.5)),
                      const SizedBox(height: 4),
                      Text('Your minutes: ${v['my_minutes'] ?? 0} / ${v['my_minutes_cap'] ?? 0}',
                          style: const TextStyle(fontSize: 13.5)),
                      const SizedBox(height: 8),
                      const Text('When the budget or minutes run out, the call automatically uses the Gemini voice.',
                          style: TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                const Padding(
                  padding: EdgeInsets.only(top: 14),
                  child: Text('The change takes effect from the next call.', style: TextStyle(color: C.muted, fontSize: 12.5)),
                ),
              ]),
            ),
    );
  }
}
