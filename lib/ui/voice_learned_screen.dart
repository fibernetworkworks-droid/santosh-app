import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.119 "<name> ne kya seekha": what Hoola learned from HER calls (language, pace, pauses, tone, her words, words it
/// misheard before). Numbers and words only, never a recording. She can add, remove, switch off or forget everything.
class VoiceLearnedScreen extends StatefulWidget {
  const VoiceLearnedScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<VoiceLearnedScreen> createState() => _VoiceLearnedScreenState();
}

class _VoiceLearnedScreenState extends State<VoiceLearnedScreen> {
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
      final v = await widget.app.api!.voiceLearned();
      if (mounted) setState(() {
        _v = v;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _run(Future<void> Function() f) async {
    setState(() => _busy = true);
    try {
      await f();
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<String?> _ask(String title, String hint) async {
    final c = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, autofocus: true, decoration: InputDecoration(hintText: hint)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Rakho')),
        ],
      ),
    );
  }

  Future<void> _addWord() async {
    final t = await _ask('Naam / shabd jo theek se sunna hai', 'jaise Rameshwar, Kothrud, Bisleri');
    if (t == null || t.length < 2) return;
    await _run(() async => widget.app.api!.voiceWordAdd(t));
  }

  Future<void> _addFix() async {
    final heard = await _ask('${widget.app.aName} kya galat sunta hai?', 'jaise Rames');
    if (heard == null || heard.isEmpty) return;
    final meant = await _ask('Sahi shabd kya hai?', 'jaise Rameshwar');
    if (meant == null || meant.isEmpty) return;
    await _run(() async => widget.app.api!.voiceFixAdd(heard, meant));
  }

  Future<void> _forget(String part, String what) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('$what bhool jaaye?'),
        content: const Text('Yeh wapas nahi aayega. Agli calls se phir se seekhna shuru hoga (agar seekhna chalu hai).'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Haan, mitao')),
        ],
      ),
    );
    if (ok == true) await _run(() async => widget.app.api!.voiceForget(part));
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 150, child: Text(k, style: const TextStyle(color: C.muted, fontSize: 13))),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 13.5))),
        ]),
      );

  String _num(dynamic x, {int dp = 0, String unit = ''}) {
    final n = (x as num?)?.toDouble();
    if (n == null) return 'abhi pata nahi';
    return '${n.toStringAsFixed(dp)}$unit';
  }

  Widget _title(String t, {Widget? trailing}) => Padding(
        padding: const EdgeInsets.only(top: 18, bottom: 6),
        child: Row(children: [
          Expanded(child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5))),
          if (trailing != null) trailing,
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final name = widget.app.aName;
    final p = Map<String, dynamic>.from((v?['profile'] as Map?) ?? const {});
    final f = Map<String, dynamic>.from((p['facts'] as Map?) ?? const {});
    final lang = v?['language'] as Map?;
    final fixes = List<Map<String, dynamic>>.from(((v?['fixes'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final words = List<Map<String, dynamic>>.from(((v?['words'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final hint = List<String>.from(((p['hint'] as List?) ?? const []).map((e) => '$e'));
    final learn = p['learn'] != false;
    final why = '${p['silence_why'] ?? 'default'}';
    return Scaffold(
      appBar: AppBar(title: Text('$name ne kya seekha')),
      body: v == null
          ? Center(child: _err == null ? const CircularProgressIndicator() : Padding(padding: const EdgeInsets.all(24), child: Text(_err!)))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Glass(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: learn,
                      onChanged: _busy ? null : (on) => _run(() async => widget.app.api!.voiceLearnSet(on)),
                      title: const Text('Calls se seekhna', style: TextStyle(fontWeight: FontWeight.w700)),
                      subtitle: Text(learn ? 'Chalu: aapke rukne, bolne ki raftaar, shabdon se seekhta hai' : 'Band: kuch naya nahi seekhega'),
                    ),
                    Text('${v['privacy'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    const SizedBox(height: 8),
                    Text('${v['say'] ?? ''}', style: const TextStyle(fontSize: 13.5)),
                  ]),
                ),
                _title('Bhasha'),
                Glass(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    _row('Aap bolti hain', lang == null ? 'App ki setting (abhi kuch seekha nahi)' : '${lang['name']}'),
                    if (lang != null && lang['mix'] != null)
                      _row('English mix', '${(((lang['mix'] as num?) ?? 0) * 100).round()}% shabd'),
                    if (lang != null)
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(onPressed: _busy ? null : () => _forget('language', 'Seekhi hui bhasha'), child: const Text('Bhool jao')),
                      ),
                  ]),
                ),
                _title('Bolne ka tareeka', trailing: (p['turns'] as num? ?? 0) > 0
                    ? TextButton(onPressed: _busy ? null : () => _forget('profile', 'Bolne ka tareeka'), child: const Text('Bhool jao'))
                    : null),
                Glass(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    _row('Calls / baatein', '${p['calls'] ?? 0} calls, ${p['turns'] ?? 0} baar aap boliin'),
                    _row('Raftaar', _num(f['pace_wps'], dp: 1, unit: ' shabd / second')),
                    _row('Beech mein rukna', f['pause_p50_ms'] == null ? 'abhi pata nahi' : '${_num(f['pause_p50_ms'])} ms aam, ${_num(f['pause_p90_ms'])} ms lamba'),
                    _row('Jawab se pehle rukta hai', '${p['silence_ms'] ?? 700} ms'
                        '${why == 'default' ? ' (aam setting)' : why.contains('cut_offs') ? ' (aapne bataya beech mein kaat diya)' : ' (aapke rukne se)'}'),
                    _row('Ek baar mein', _num(f['turn_words_median'], unit: ' shabd')),
                    _row('Awaaz ki pitch', f['pitch_hz'] == null ? 'abhi pata nahi' : '${_num(f['pitch_hz'])} Hz (${_num(f['pitch_low_hz'])}-${_num(f['pitch_high_hz'])})'),
                    _row('Utaar-chadhaav', _num(f['tone_spread_st'], dp: 1, unit: ' semitone')),
                    const SizedBox(height: 8),
                    if (hint.isEmpty)
                      const Text('2-3 calls ke baad yahan dikhega ki woh aapse kaise baat karega.', style: TextStyle(color: C.muted, fontSize: 12.5))
                    else ...[
                      const Text('Calls mein woh aise dhyaan rakhta hai:', style: TextStyle(color: C.muted, fontSize: 12.5)),
                      for (final h in hint) Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $h', style: const TextStyle(fontSize: 13))),
                    ],
                    const SizedBox(height: 6),
                    const Text('Aapki awaaz ya lehja copy nahi hota; sirf raftaar, rukna aur shabd.', style: TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
                _title('Galat suna tha', trailing: TextButton.icon(
                    onPressed: _busy ? null : _addFix, icon: const Icon(Icons.add_rounded, size: 18), label: const Text('Jodo'))),
                Glass(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: fixes.isEmpty
                      ? const Padding(padding: EdgeInsets.all(10), child: Text('Kuch nahi. Call mein "Rames nahi, Rameshwar" kahengi to yahan aayega.', style: TextStyle(color: C.muted, fontSize: 13)))
                      : Column(children: [
                          for (final x in fixes)
                            ListTile(
                              dense: true,
                              leading: Icon(x['confirmed'] == true ? Icons.check_circle_rounded : Icons.help_outline_rounded,
                                  color: x['confirmed'] == true ? C.ok : C.warn),
                              title: Text('"${x['heard']}" → ${x['meant']}'),
                              subtitle: Text(x['confirmed'] == true ? 'Pakka: calls mein dhyaan rakhta hai' : 'Ek baar suna: Haan dabaiye to pakka'),
                              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                                if (x['confirmed'] != true)
                                  IconButton(tooltip: 'Haan, sahi', icon: const Icon(Icons.done_rounded),
                                      onPressed: _busy ? null : () => _run(() async => widget.app.api!.voiceFixConfirm((x['id'] as num).toInt()))),
                                IconButton(tooltip: 'Hatao', icon: const Icon(Icons.close_rounded),
                                    onPressed: _busy ? null : () => _run(() async => widget.app.api!.voiceFixRemove((x['id'] as num).toInt()))),
                              ]),
                            ),
                        ]),
                ),
                _title('Aapke naam aur shabd', trailing: TextButton.icon(
                    onPressed: _busy ? null : _addWord, icon: const Icon(Icons.add_rounded, size: 18), label: const Text('Jodo'))),
                Glass(
                  padding: const EdgeInsets.all(12),
                  child: words.isEmpty
                      ? const Text('Jo naam / jagah / cheez woh galat sunta hai, yahan jodiye. Aapke contacts ke naam apne aap jaate hain.',
                          style: TextStyle(color: C.muted, fontSize: 13))
                      : Wrap(spacing: 8, runSpacing: 6, children: [
                          for (final w in words)
                            InputChip(
                              label: Text('${w['term']}'),
                              onDeleted: _busy ? null : () => _run(() async => widget.app.api!.voiceWordRemove((w['id'] as num).toInt())),
                            ),
                        ]),
                ),
                const SizedBox(height: 20),
                OutlinedButton.icon(
                  onPressed: _busy ? null : () => _forget('all', 'Sab kuch'),
                  icon: const Icon(Icons.delete_outline_rounded, color: C.bad),
                  label: const Text('Sab bhool jao', style: TextStyle(color: C.bad)),
                ),
              ]),
            ),
    );
  }
}
