/// Profile > Personal tutor (Shiksha suite Phase 2, Guru Sahayak): pick a learner, then
/// Padhai (a doubt taught one rung at a time: hint -> nudge -> steps -> answer) · Practice (from the approved bank, mastery
/// + revision) · Bhasha (language practice with corrections) · Pragati (mastery per topic, weekly report card).
/// A child needs the guardian's consent first; the weekly report reaches the guardian ONLY by her tap on the card.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _disclaimer = 'Hoola ek AI tutor hai: pehle ishaara deta hai, khud sochne deta hai. Jo jawab "code se jaancha" nahi '
    'likha, use teacher se pakka kijiye.';

class GuruScreen extends StatefulWidget {
  const GuruScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<GuruScreen> createState() => _GuruScreenState();
}

class _GuruScreenState extends State<GuruScreen> {
  List<Map<String, dynamic>>? _learners;
  Map<String, dynamic> _day = const {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final l = _map(await widget.app.api!.call('GET', '/api/shiksha/learners'));
      final d = _map(await widget.app.api!.call('GET', '/api/guru'));
      if (mounted) setState(() {
        _learners = _list(l['learners']);
        _day = d;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Personal tutor')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              if (_s(_day['say']).isNotEmpty) Glass(child: Text(_s(_day['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
              const SizedBox(height: 10),
              const Caption('Kisko padhana hai?'),
              if (_learners == null) const Center(child: CircularProgressIndicator()),
              if (_learners != null && _learners!.isEmpty)
                const Text('Abhi koi learner nahi. Chat mein kahiye: "Aarav ko 8-A mein jodo, guardian Sunita 98xxxxxxxx".',
                    style: TextStyle(color: C.muted)),
              for (final l in _learners ?? const <Map<String, dynamic>>[])
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Press(
                    onTap: l['usable'] == true
                        ? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GuruLearnerPage(app: widget.app, learner: l)))
                        : () => _snack(context, 'Pehle guardian ki consent darj kijiye (school ka kaam).'),
                    child: Glass(
                      child: Row(children: [
                        Expanded(child: Text('${_s(l['number'])} · ${_s(l['name'])}${_s(l['class']).isNotEmpty ? ' (${_s(l['class'])})' : ''}',
                            style: const TextStyle(fontWeight: FontWeight.w800))),
                        if (l['usable'] != true) const Pill('CONSENT BAAKI', fg: C.warn),
                      ]),
                    ),
                  ),
                ),
              const SizedBox(height: 10),
              const Caption('Hoola kabhi nahi karega'),
              for (final n in (_day['never'] as List? ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12.5)),
              const SizedBox(height: 14),
              const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

class GuruLearnerPage extends StatefulWidget {
  const GuruLearnerPage({super.key, required this.app, required this.learner});
  final Santosh app;
  final Map<String, dynamic> learner;
  @override
  State<GuruLearnerPage> createState() => _GuruLearnerPageState();
}

class _GuruLearnerPageState extends State<GuruLearnerPage> {
  int _tab = 0;
  bool _busy = false;
  String _session = '';
  String _mode = '';
  final _text = TextEditingController();
  final _typed = TextEditingController();
  final List<(String, String)> _turns = [];      // (who, text)
  Map<String, dynamic>? _question;
  Map<String, dynamic>? _progress;
  Map<String, dynamic>? _path;
  final _subject = TextEditingController(text: 'Mathematics');
  String _next = '';

  String get _ref => _s(widget.learner['number']);

  @override
  void dispose() {
    _text.dispose();
    _typed.dispose();
    _subject.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>?> _call(String method, String path, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    try {
      return _map(await widget.app.api!.call(method, path, body: body, timeout: const Duration(minutes: 2)));
    } catch (e) {
      if (mounted) _snack(context, '$e'.replaceFirst('Exception: ', ''));
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<bool> _ensure(String mode) async {
    if (_session.isNotEmpty && _mode == mode) return true;
    final r = await _call('POST', '/api/guru/sessions', {'learner': _ref, 'mode': mode, if (mode == 'language') 'language': 'English'});
    if (r == null) return false;
    setState(() {
      _session = _s(r['number']);
      _mode = mode;
      _turns.clear();
      _question = null;
      _next = '';
    });
    return true;
  }

  Future<void> _ask() async {
    final t = _text.text.trim();
    if (t.isEmpty || !await _ensure('doubt')) return;
    final r = await _call('POST', '/api/guru/sessions/$_session/doubt', {'text': t});
    if (r == null) return;
    setState(() {
      _turns
        ..add(('Sawaal', t))
        ..add(('Ishaara', _s(r['say'])));
      _next = _s(r['next']);
      _text.clear();
    });
  }

  Future<void> _more() async {
    final r = await _call('POST', '/api/guru/sessions/$_session/hint', {'attempt': _text.text.trim()});
    if (r == null) return;
    setState(() {
      final label = switch (_s(r['rung'])) { 'nudge' => 'Thoda aur', 'step' => 'Steps', 'answer' => 'Poora hal', _ => 'Tutor' };
      _turns.add((label, _s(r['say'])));
      if (_s(r['check_question']).isNotEmpty) _turns.add(('Ab aap try kijiye', _s(r['check_question'])));
      _next = r['done'] == true ? '' : _s(r['next']);
      _text.clear();
    });
  }

  Future<void> _practice() async {
    if (!await _ensure('practice')) return;
    final r = await _call('POST', '/api/guru/sessions/$_session/practice');
    if (r != null) setState(() => _question = {..._map(r['question']), 'why': r['why'], 'mastery': r['mastery']});
  }

  Future<void> _answer(String given) async {
    final r = await _call('POST', '/api/guru/sessions/$_session/answer', {'given': given});
    if (r == null) return;
    setState(() {
      _turns.add(('Jawab: $given', _s(r['say'])));
      for (final st in (r['solution_steps'] as List? ?? const [])) {
        _turns.add(('Step', '$st'));
      }
      _question = null;
    });
  }

  Future<void> _lang() async {
    final t = _text.text.trim();
    if (t.isEmpty || !await _ensure('language')) return;
    final r = await _call('POST', '/api/guru/sessions/$_session/language', {'text': t});
    if (r == null) return;
    setState(() {
      _turns
        ..add(('Aap', t))
        ..add(('Tutor', _s(r['say'])));
      _text.clear();
    });
  }

  Future<void> _loadPath({bool build = false}) async {
    final subj = _subject.text.trim();
    if (subj.isEmpty) return;
    final r = build
        ? await _call('POST', '/api/guru/learners/$_ref/path', {'subject': subj})
        : await _call('GET', '/api/guru/learners/$_ref/path?subject=${Uri.encodeQueryComponent(subj)}');
    if (r != null) setState(() => _path = r);
  }

  Widget _pathBox() {
    final p = _path;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Caption('Mastery path (chapter kram se, gate paar karke aage)'),
      Row(children: [
        Expanded(child: TextField(controller: _subject, decoration: const InputDecoration(labelText: 'Subject'))),
        const SizedBox(width: 8),
        GlassButton(label: 'Dekho', onTap: _busy ? null : () => _loadPath()),
        const SizedBox(width: 6),
        GlassButton(label: 'Banao', onTap: _busy ? null : () => _loadPath(build: true)),
      ]),
      if (p != null) ...[
        const SizedBox(height: 6),
        Text(_s(p['say']), style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 6),
        for (final c in _list(p['chapters']))
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(children: [
              Icon(
                  switch (_s(c['state'])) { 'passed' => Icons.check_circle_rounded, 'current' => Icons.play_circle_rounded, _ => Icons.lock_rounded },
                  size: 18,
                  color: switch (_s(c['state'])) { 'passed' => C.ok, 'current' => C.accent, _ => C.muted }),
              const SizedBox(width: 6),
              Expanded(child: Text(_s(c['chapter']), style: const TextStyle(fontSize: 13))),
              Text('${_s(c['mastery'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
              if (c['due'] == true) const Padding(padding: EdgeInsets.only(left: 6), child: Pill('REVISION', fg: C.warn)),
            ]),
          ),
      ],
      const SizedBox(height: 12),
    ]);
  }

  Future<void> _loadProgress() async {
    final r = await _call('GET', '/api/guru/learners/$_ref/progress');
    if (r != null) setState(() => _progress = r);
  }

  Widget _turnList() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final (who, t) in _turns)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(who, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: C.accent)),
                const SizedBox(height: 4),
                SelectableText(t, style: const TextStyle(fontSize: 13.5, height: 1.4)),
              ]),
            ),
          ),
      ]);

  Widget _padhai() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _turnList(),
        TextField(controller: _text, minLines: 1, maxLines: 4,
            decoration: InputDecoration(labelText: _next.isEmpty ? 'Sawaal likhiye' : 'Aapne kya try kiya? (optional)')),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: GradientButton(label: 'Samjhao', icon: Icons.lightbulb_rounded, height: 44, onTap: _busy ? null : _ask)),
          if (_next.isNotEmpty) ...[
            const SizedBox(width: 8),
            GlassButton(label: 'Aur batao', icon: Icons.arrow_downward_rounded, onTap: _busy ? null : _more),
          ],
        ]),
      ]);

  Widget _practiceTab() {
    final q = _question;
    final opts = (q?['options'] as List? ?? const []);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _turnList(),
      if (q == null) GradientButton(label: 'Agla sawaal', icon: Icons.quiz_rounded, height: 44, onTap: _busy ? null : _practice),
      if (q != null)
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(q['topic'])} · ${_s(q['difficulty'])} · ${_s(q['why'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
            const SizedBox(height: 6),
            Text(_s(q['text']), style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            for (final (i, o) in opts.indexed)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: GlassButton(label: '(${i < 4 ? 'abcd'[i] : i + 1}) $o', onTap: _busy ? null : () => _answer('$o')),
              ),
            if (opts.isEmpty) ...[
              TextField(controller: _typed, minLines: 1, maxLines: 5, decoration: const InputDecoration(labelText: 'Aapka jawab')),
              const SizedBox(height: 8),
              GradientButton(label: 'Jaancho', height: 42, onTap: _busy ? null : () { final g = _typed.text.trim(); _typed.clear(); _answer(g); }),
            ],
          ]),
        ),
    ]);
  }

  Widget _bhasha() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('English bolne / likhne ka abhyas: likhiye, tutor jawab dega aur galti pyaar se sudhaarega.',
            style: TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        _turnList(),
        TextField(controller: _text, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Kuch English mein likhiye')),
        const SizedBox(height: 8),
        GradientButton(label: 'Bhejo', icon: Icons.send_rounded, height: 44, onTap: _busy ? null : _lang),
      ]);

  Widget _pragati() {
    final p = _progress;
    if (p == null) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _pathBox(),
        GlassButton(label: 'Pragati dekho', icon: Icons.insights_rounded, onTap: _loadProgress),
      ]);
    }
    final w = _map(p['week']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _pathBox(),
      Glass(child: Text('Is hafte: ${_s(w['minutes'])} min, ${_s(w['attempts'])} sawaal'
          '${w['accuracy'] != null ? ', ${((w['accuracy'] as num) * 100).round()}% sahi' : ''}',
          style: const TextStyle(fontWeight: FontWeight.w700))),
      const SizedBox(height: 8),
      for (final t in _list(p['topics']))
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(t['topic'])} (${_s(t['subject'])})', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
              if (t['due_now'] == true) const Pill('REVISION', fg: C.warn),
            ]),
            const SizedBox(height: 4),
            LinearProgressIndicator(value: ((t['mastery'] as num?) ?? 0).toDouble(), minHeight: 6),
          ]),
        ),
      const SizedBox(height: 8),
      GlassButton(
          label: 'Guardian ke liye report (card)',
          icon: Icons.outbox_rounded,
          onTap: _busy
              ? null
              : () async {
                  final r = await _call('POST', '/api/guru/learners/$_ref/report', {'via': 'whatsapp'});
                  if (r != null && mounted) _snack(context, _s(r['say']));
                }),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(widget.learner['name']))),
        body: Aurora(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            Wrap(spacing: 6, children: [
              for (final (i, t) in const [(0, 'Padhai'), (1, 'Practice'), (2, 'Bhasha'), (3, 'Pragati')])
                ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
            ]),
            const SizedBox(height: 10),
            if (_busy) const LinearProgressIndicator(),
            [_padhai(), _practiceTab(), _bhasha(), _pragati()][_tab],
            const SizedBox(height: 14),
            const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      );
}

/// The weekly report for the guardian: ONLY her tap here prepares the WhatsApp / email draft she sends herself.
class GuruReportCard extends StatefulWidget {
  const GuruReportCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<GuruReportCard> createState() => _GuruReportCardState();
}

class _GuruReportCardState extends State<GuruReportCard> {
  Map<String, dynamic>? _done;
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    final sh = _map(widget.data['share']);
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call('POST', '/api/guru/shares/${sh['id']}/decide', body: {'yes': yes, 'hash': sh['hash']}));
      if (mounted) setState(() => _done = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final src = _done ?? widget.data;
    final sh = _map(src['share']);
    final rep = _map(sh['report']);
    final links = _map(src['links']);
    final waiting = _s(sh['status']) == 'waiting';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Icon(Icons.school_rounded, size: 18, color: C.accent),
          const SizedBox(width: 6),
          Expanded(child: Text('Padhai ki report → ${_s(rep['to']).isEmpty ? 'guardian' : _s(rep['to'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(sh['status']).toUpperCase(), fg: waiting ? C.warn : (_s(sh['status']) == 'shared' ? C.ok : C.muted)),
        ]),
        if (_s(rep['text']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(rep['text']), style: const TextStyle(fontSize: 12.5))),
        if (_s(src['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(src['say']), style: const TextStyle(fontSize: 12, color: C.muted))),
        const SizedBox(height: 8),
        if (waiting)
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, draft banao', height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Mana', onTap: _busy ? null : () => _decide(false)),
          ]),
        for (final e in links.entries)
          TextButton.icon(
              onPressed: () async {
                final r = await Native.openExternal(url: _s(e.value));
                if (r.isNotEmpty && r != 'ok' && context.mounted) _snack(context, r);
              },
              icon: Icon(e.key == 'email' ? Icons.mail_rounded : Icons.chat_rounded, size: 18),
              label: Text(e.key == 'email' ? 'Email draft kholo' : 'WhatsApp draft kholo')),
      ]),
    );
  }
}
