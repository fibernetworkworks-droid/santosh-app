import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.231 "Call ki jaanch": how the voice calls really went (numbers saved per call on the server, so they survive
/// updates), a grade per call with what went wrong in plain words, the same numbers per app version, and her own
/// kaan-test + phone checklist for this version (pass / fail / skip per scenario).
class CallQualityScreen extends StatefulWidget {
  const CallQualityScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CallQualityScreen> createState() => _CallQualityScreenState();
}

class _CallQualityScreenState extends State<CallQualityScreen> {
  Map<String, dynamic>? _q;
  Map<String, dynamic>? _ear;
  String? _err;
  bool _busy = false;
  int _days = 30;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = widget.app.api!;
      final q = await api.voiceQuality(days: _days);
      final ear = await api.voiceEarTest();
      if (mounted) setState(() {
        _q = q;
        _ear = ear;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _mark(String id, String result) async {
    String note = '';
    if (result == 'fail') {
      final c = TextEditingController();
      final t = await showDialog<String>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Kya galat laga?'),
          content: TextField(controller: c, autofocus: true, maxLength: 300,
              decoration: const InputDecoration(hintText: 'jaise: jawab der se aaya, beech mein kaat diya')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Fail likho')),
          ],
        ),
      );
      if (t == null) return;
      note = t;
    }
    setState(() => _busy = true);
    try {
      final ear = await widget.app.api!.voiceEarMark(id, result, note: note);
      if (mounted) setState(() => _ear = ear);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _title(String t, {Widget? trailing}) => Padding(
        padding: const EdgeInsets.only(top: 18, bottom: 6),
        child: Row(children: [
          Expanded(child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5))),
          if (trailing != null) trailing,
        ]),
      );

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 170, child: Text(k, style: const TextStyle(color: C.muted, fontSize: 13))),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 13.5))),
        ]),
      );

  String _ms(dynamic x) {
    final n = (x as num?)?.toDouble();
    return n == null ? 'abhi pata nahi' : '${n.round()} ms';
  }

  String _n(dynamic x, {String unit = ''}) => x == null ? 'abhi pata nahi' : '$x$unit';

  Color _gradeColor(String g) => g == 'good' ? C.ok : (g == 'bad' ? C.bad : C.warn);
  String _gradeWord(String g) => g == 'good' ? 'Achhi' : (g == 'bad' ? 'Kharab' : 'Theek');

  Widget _grades(Map<String, dynamic> o) {
    final g = Map<String, dynamic>.from((o['grades'] as Map?) ?? const {});
    Widget chip(String k) => Padding(
          padding: const EdgeInsets.only(right: 8),
          child: Pill('${_gradeWord(k)} ${g[k] ?? 0}', fg: _gradeColor(k), bg: _gradeColor(k).withOpacity(.16)),
        );
    return Row(children: [chip('good'), chip('ok'), chip('bad')]);
  }

  Widget _overall(Map<String, dynamic> o, Map<String, dynamic> t) {
    final ends = Map<String, dynamic>.from((o['ends'] as Map?) ?? const {});
    return Glass(
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_q?['say'] ?? ''}', style: const TextStyle(fontSize: 13.5)),
        const SizedBox(height: 10),
        _grades(o),
        const SizedBox(height: 10),
        _row('Calls / minute', '${o['calls'] ?? 0} calls, ${o['minutes'] ?? 0} minute'),
        _row('Jawab shuru (aam)', '${_ms(o['reply_start_ms_p50'])}  (lakshya ${t['reply_start_ms_p50'] ?? 1200} ms se kam)'),
        _row('Jawab shuru (dheemi 10%)', '${_ms(o['reply_start_ms_p90'])}  (${t['reply_start_ms_p90'] ?? 2500} ms se kam)'),
        _row('Beech mein tooti', '${o['broken_calls'] ?? 0}'),
        _row('Connection badla', o['goaway'] == 0 || o['goaway'] == null
            ? 'nahi badla'
            : '${o['goaway']} baar, ${_n(o['goaway_graceful_pct'], unit: '%')} baat kate bina'),
        _row('Chup hua (nudge / reconnect)', '${o['stall_nudges'] ?? 0} / ${o['stall_reconnects'] ?? 0}'),
        _row('Khud doosra raasta', '${o['auto_rescues'] ?? 0}'),
        _row('Kaam ki khabar (milayi / dohrayi nahi)', '${o['news_merged'] ?? 0} / ${o['news_deduped'] ?? 0}'),
        _row('Line girne par bachi awaaz', '${o['gap_audio_kept_s'] ?? 0} s aapki, ${o['missed_replayed_s'] ?? 0} s uski'),
        _row('Beech mein rokna / call', _n(o['interruptions_per_call'])),
        _row('Bhasha badli / 100 baat', _n(o['lang_drifts_per_100'])),
        _row('Dobara poochha / 100 baat', _n(o['asked_again_per_100'])),
        _row('Bol kar haan', '${o['voice_approvals'] ?? 0}'),
        if (ends.isNotEmpty)
          _row('Call kaise khatam hui', ends.entries.map((e) => '${_endWord(e.key)} ${e.value}').join(', ')),
      ]),
    );
  }

  String _endWord(String k) => const {
        'hung_up': 'aapne kaata',
        'dropped': 'line toot gayi',
        'error': 'error',
        'stall': 'chup ho gaya',
        'server_restart': 'server update',
        'hold_timeout': 'hold lamba',
      }[k] ?? k;

  Widget _versions(List vs) => Glass(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        child: Column(children: [
          for (final r in vs.map((e) => Map<String, dynamic>.from(e as Map)))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                SizedBox(width: 70, child: Text('v${r['version']}', style: const TextStyle(fontWeight: FontWeight.w700))),
                Expanded(child: Text('${r['calls']} calls · ${_n(r['good_pct'], unit: '% achhi')} · ${_ms(r['reply_start_ms_p50'])}',
                    style: const TextStyle(fontSize: 13))),
              ]),
            ),
        ]),
      );

  Widget _recent(List rs) => Glass(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        child: Column(children: [
          for (final c in rs.map((e) => Map<String, dynamic>.from(e as Map)))
            ListTile(
              dense: true,
              leading: Icon(
                  c['grade'] == 'good'
                      ? Icons.check_circle_rounded
                      : (c['grade'] == 'bad' ? Icons.error_rounded : Icons.remove_circle_outline_rounded),
                  color: _gradeColor('${c['grade']}')),
              title: Text('${_when(c['started'])} · ${_mins(c['seconds'])} · ${c['turns'] ?? 0} baat'
                  '${c['rating'] == true ? ' · 👍' : (c['rating'] == false ? ' · 👎' : '')}'),
              subtitle: Text(
                  [
                    if ((c['problems'] as List?)?.isNotEmpty == true) ...(c['problems'] as List).map((e) => '$e'),
                    if ((c['problems'] as List?)?.isEmpty != false) 'Sab theek',
                    if ('${c['end_say']}'.isNotEmpty) 'Ant: ${c['end_say']}',
                  ].join(' · '),
                  style: const TextStyle(fontSize: 12.5)),
            ),
        ]),
      );

  String _when(dynamic sec) {
    final n = (sec as num?)?.toInt();
    if (n == null) return '';
    final d = DateTime.fromMillisecondsSinceEpoch(n * 1000).toLocal();
    String two(int x) => x.toString().padLeft(2, '0');
    return '${two(d.day)}/${two(d.month)} ${two(d.hour)}:${two(d.minute)}';
  }

  String _mins(dynamic s) {
    final n = (s as num?)?.toDouble();
    if (n == null) return '';
    return n < 60 ? '${n.round()} sec' : '${(n / 60).toStringAsFixed(1)} min';
  }

  Widget _earItem(Map<String, dynamic> t) {
    final r = t['result'] as String?;
    Widget btn(String res, String label, Color col) => Padding(
          padding: const EdgeInsets.only(right: 6),
          child: ChoiceChip(
            label: Text(label),
            selected: r == res,
            selectedColor: col.withOpacity(.28),
            onSelected: _busy ? null : (_) => _mark('${t['id']}', r == res ? 'clear' : res),
          ),
        );
    return Glass(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(t['kind'] == 'phone' ? Icons.smartphone_rounded : Icons.hearing_rounded, size: 18, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${t['title']}', style: const TextStyle(fontWeight: FontWeight.w700))),
        ]),
        const SizedBox(height: 6),
        Text('Kya karein: ${t['do']}', style: const TextStyle(fontSize: 13)),
        const SizedBox(height: 3),
        Text('Achha hai agar: ${t['good']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        if ('${t['note'] ?? ''}'.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text('Aapne likha: ${t['note']}', style: const TextStyle(color: C.bad, fontSize: 12.5))),
        const SizedBox(height: 8),
        Wrap(children: [btn('pass', 'Sahi', C.ok), btn('fail', 'Galat', C.bad), btn('skip', 'Chhodo', C.muted)]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final q = _q;
    final ear = _ear;
    final o = Map<String, dynamic>.from((q?['overall'] as Map?) ?? const {});
    final t = Map<String, dynamic>.from((q?['targets'] as Map?) ?? const {});
    final vs = (q?['versions'] as List?) ?? const [];
    final rs = (q?['recent'] as List?) ?? const [];
    final items = ((ear?['items'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Call ki jaanch')),
      body: q == null
          ? Center(child: _err == null ? const CircularProgressIndicator() : Padding(padding: const EdgeInsets.all(24), child: Text(_err!)))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Wrap(spacing: 8, children: [
                  for (final d in const [7, 30, 90])
                    ChoiceChip(
                      label: Text('$d din'),
                      selected: _days == d,
                      onSelected: (_) {
                        setState(() => _days = d);
                        _load();
                      },
                    ),
                ]),
                _title('Kul milaakar'),
                _overall(o, t),
                if (vs.length > 1) ...[_title('Har version'), _versions(vs)],
                if (rs.isNotEmpty) ...[_title('Pichhli calls'), _recent(rs)],
                _title('Kaan-test · v${ear?['version'] ?? ''}',
                    trailing: Text('${ear?['passed'] ?? 0} sahi · ${ear?['failed'] ?? 0} galat · ${ear?['done'] ?? 0}/${ear?['total'] ?? 0}',
                        style: const TextStyle(color: C.muted, fontSize: 12.5))),
                const Padding(
                  padding: EdgeInsets.only(bottom: 10),
                  child: Text('Har cheez apne phone par call karke aazmaaiye, phir Sahi / Galat dabaaiye. Har naye version par yeh list nayi shuru hoti hai.',
                      style: TextStyle(color: C.muted, fontSize: 12.5)),
                ),
                for (final it in items) _earItem(it),
              ]),
            ),
    );
  }
}
