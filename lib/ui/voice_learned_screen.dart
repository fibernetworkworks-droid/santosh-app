import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

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
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Leave it')),
          TextButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Keep')),
        ],
      ),
    );
  }

  Future<void> _addWord() async {
    final t = await _ask('Name / word to hear correctly', 'for example Rameshwar, Kothrud, Bisleri');
    if (t == null || t.length < 2) return;
    await _run(() async => widget.app.api!.voiceWordAdd(t));
  }

  Future<void> _addFix() async {
    final heard = await _ask('${widget.app.aName} — what does it mishear?', 'for example Rames');
    if (heard == null || heard.isEmpty) return;
    final meant = await _ask('What is the correct word?', 'for example Rameshwar');
    if (meant == null || meant.isEmpty) return;
    await _run(() async => widget.app.api!.voiceFixAdd(heard, meant));
  }

  Future<void> _forget(String part, String what) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Forget $what?'),
        content: const Text('This will not come back. It will start learning again from the next calls (if learning is on).'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('No')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Yes, delete')),
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
    if (n == null) return 'not known yet';
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
    return DeskPage(
      title: 'What $name has learned',
      body: () => v == null
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
                      title: const Text('Learning from calls', style: TextStyle(fontWeight: FontWeight.w700)),
                      subtitle: Text(learn ? 'On: learns from your pauses, speaking speed and words' : 'Off: will not learn anything new'),
                    ),
                    Text('${v['privacy'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    const SizedBox(height: 8),
                    Text('${v['say'] ?? ''}', style: const TextStyle(fontSize: 13.5)),
                  ]),
                ),
                _title('Language'),
                Glass(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    _row('You speak', lang == null ? 'App setting (nothing learned yet)' : '${lang['name']}'),
                    if (lang != null && lang['mix'] != null)
                      _row('English mix', '${(((lang['mix'] as num?) ?? 0) * 100).round()}% shabd'),
                    if (lang != null)
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(onPressed: _busy ? null : () => _forget('language', 'Learned language'), child: const Text('Forget')),
                      ),
                  ]),
                ),
                _title('Way of speaking', trailing: (p['turns'] as num? ?? 0) > 0
                    ? TextButton(onPressed: _busy ? null : () => _forget('profile', 'Way of speaking'), child: const Text('Forget'))
                    : null),
                Glass(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    _row('Calls / chats', '${p['calls'] ?? 0} calls, ${p['turns'] ?? 0} times you spoke'),
                    _row('Speed', _num(f['pace_wps'], dp: 1, unit: ' words / second')),
                    _row('Pausing in between', f['pause_p50_ms'] == null ? 'not known yet' : '${_num(f['pause_p50_ms'])} ms typical,${_num(f['pause_p90_ms'])} ms long'),
                    _row('Pauses before answering', '${p['silence_ms'] ?? 700} ms'
                        '${why == 'default' ? ' (aam setting)' : why.contains('cut_offs') ? ' (you said it cut in)' : ' (from your pauses)'}'),
                    _row('At a time', _num(f['turn_words_median'], unit: ' words')),
                    _row('Voice pitch', f['pitch_hz'] == null ? 'not known yet' : '${_num(f['pitch_hz'])} Hz (${_num(f['pitch_low_hz'])}-${_num(f['pitch_high_hz'])})'),
                    _row('Ups and downs', _num(f['tone_spread_st'], dp: 1, unit: ' semitone')),
                    const SizedBox(height: 8),
                    if (hint.isEmpty)
                      const Text('After 2-3 calls, it will show here how it talks to you.', style: TextStyle(color: C.muted, fontSize: 12.5))
                    else ...[
                      const Text('In calls it keeps this in mind:', style: TextStyle(color: C.muted, fontSize: 12.5)),
                      for (final h in hint) Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $h', style: const TextStyle(fontSize: 13))),
                    ],
                    const SizedBox(height: 6),
                    const Text('Your voice or accent is not copied; only speed, pauses and words.', style: TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
                _title('Misheard', trailing: TextButton.icon(
                    onPressed: _busy ? null : _addFix, icon: const Icon(Icons.add_rounded, size: 18), label: const Text('Add'))),
                Glass(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: fixes.isEmpty
                      ? const Padding(padding: EdgeInsets.all(10), child: Text('Nothing. If you say "not Rames, Rameshwar" in a call, it will show here.', style: TextStyle(color: C.muted, fontSize: 13)))
                      : Column(children: [
                          for (final x in fixes)
                            ListTile(
                              dense: true,
                              leading: Icon(x['confirmed'] == true ? Icons.check_circle_rounded : Icons.help_outline_rounded,
                                  color: x['confirmed'] == true ? C.ok : C.warn),
                              title: Text('"${x['heard']}" → ${x['meant']}'),
                              subtitle: Text(x['confirmed'] == true ? 'Confirmed: kept in mind in calls' : 'Heard once: tap Yes to confirm'),
                              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                                if (x['confirmed'] != true)
                                  IconButton(tooltip: 'Yes, correct', icon: const Icon(Icons.done_rounded),
                                      onPressed: _busy ? null : () => _run(() async => widget.app.api!.voiceFixConfirm((x['id'] as num).toInt()))),
                                IconButton(tooltip: 'Remove', icon: const Icon(Icons.close_rounded),
                                    onPressed: _busy ? null : () => _run(() async => widget.app.api!.voiceFixRemove((x['id'] as num).toInt()))),
                              ]),
                            ),
                        ]),
                ),
                _title('Your names and words', trailing: TextButton.icon(
                    onPressed: _busy ? null : _addWord, icon: const Icon(Icons.add_rounded, size: 18), label: const Text('Add'))),
                Glass(
                  padding: const EdgeInsets.all(12),
                  child: words.isEmpty
                      ? const Text('Add names / places / things it mishears. Your contacts\' names go in by themselves.',
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
                  onPressed: _busy ? null : () => _forget('all', 'Everything'),
                  icon: const Icon(Icons.delete_outline_rounded, color: C.bad),
                  label: const Text('Forget everything', style: TextStyle(color: C.bad)),
                ),
              ]),
            ),
    );
  }
}
