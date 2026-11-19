/// Profile > Personal tutor (Shiksha suite Phase 2, Guru Sahayak): pick a learner, then
/// Padhai (a doubt taught one rung at a time: hint -> nudge -> steps -> answer) · Practice (from the approved bank, mastery
/// + revision) · Bhasha (language practice with corrections) · Pragati (mastery per topic, weekly report card).
/// A child needs the guardian's consent first; the weekly report reaches the guardian ONLY by her tap on the card.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'chat/hoola_thread.dart' show HoolaHerBubble, HoolaLanding, HoolaOnDark, HoolaReplyActions, HoolaWorkingRow;
import 'desk/desk_kit.dart';
import 'glass.dart';
import 'hoola_theme.dart' show HoolaColors, HoolaType;

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _disclaimer = 'Hoola is an AI tutor: it gives hints first and lets the learner think. Where an answer is not marked "checked by code"'
    ', please confirm it with the teacher.';

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
  Widget build(BuildContext context) => DeskPage(
        title: 'Personal tutor',
        onRefresh: _load,
        body: () => RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              if (_s(_day['say']).isNotEmpty) Glass(child: Text(_s(_day['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
              const SizedBox(height: 10),
              const Caption('Who is it for?'),
              if (_learners == null) const Center(child: CircularProgressIndicator()),
              if (_learners != null && _learners!.isEmpty)
                const Text('No learners yet. Tell me in chat: "Add Aarav to 8-A, guardian Sunita 98xxxxxxxx".',
                    style: TextStyle(color: C.muted)),
              for (final l in _learners ?? const <Map<String, dynamic>>[])
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Press(
                    onTap: l['usable'] == true
                        ? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GuruLearnerPage(app: widget.app, learner: l)))
                        : () => _snack(context, 'First record the guardian\'s consent (school\'s job).'),
                    child: Glass(
                      child: Row(children: [
                        Expanded(child: Text('${_s(l['number'])} · ${_s(l['name'])}${_s(l['class']).isNotEmpty ? ' (${_s(l['class'])})' : ''}',
                            style: const TextStyle(fontWeight: FontWeight.w800))),
                        if (l['usable'] != true) const Pill('CONSENT PENDING', fg: C.warn),
                      ]),
                    ),
                  ),
                ),
              const SizedBox(height: 10),
              const Caption('Hoola will never'),
              for (final n in (_day['never'] as List? ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12.5)),
              const SizedBox(height: 14),
              const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
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
  // ---- HOOLA THREAD KIT (chat/hoola_thread.dart): the conversation with the tutor is drawn like the Hoola chat.
  /// Turns before this place are on screen whole; the tutor's turn AT this place is landing word by word, and the
  /// ones after it wait their turn (a hint and its "Now you try" never land at the same time).
  int _landed = 0;
  /// What she has just sent (shown at once, a little lighter, until the tutor has answered) and what the tutor is
  /// doing now (null = not working on a reply) with the time she sent it (the working row's clock).
  String _asking = '';
  String? _work;
  DateTime? _since;
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
      _landed = 0;
      _question = null;
      _next = '';
    });
    return true;
  }

  /// Her own turns (drawn as her bubble); every other turn is the tutor's.
  static bool _mine(String who) => who == 'Question' || who == 'You';

  /// She sent something: it shows at once, the working row starts its clock, and whatever was still landing is
  /// simply there.
  void _begin(String sent, String work) => setState(() {
        _asking = sent;
        _work = work;
        _since = DateTime.now();
        _landed = _turns.length;
      });

  /// The tutor's answer is in (or the call failed): no pending bubble, no working row; the new words land.
  void _settle() {
    _asking = '';
    _work = null;
    _skipMine();
  }

  /// Her own turns need no landing: the place moves on to the tutor's next turn.
  void _skipMine() {
    while (_landed < _turns.length && _mine(_turns[_landed].$1)) {
      _landed++;
    }
  }

  Future<void> _ask() async {
    final t = _text.text.trim();
    if (t.isEmpty) return;
    _text.clear();
    _begin(t, 'Thinking about your question');
    final r = await _ensure('doubt') ? await _call('POST', '/api/guru/sessions/$_session/doubt', {'text': t}) : null;
    if (!mounted) return;
    if (r == null) {
      setState(_settle);
      if (_text.text.isEmpty) _text.text = t;   // nothing she typed is lost
      return;
    }
    setState(() {
      _turns
        ..add(('Question', t))
        ..add(('Hint', _s(r['say'])));
      _next = _s(r['next']);
      _settle();
    });
  }

  Future<void> _more() async {
    final t = _text.text.trim();
    _text.clear();
    _begin(t, 'Working out the next hint');
    final r = await _call('POST', '/api/guru/sessions/$_session/hint', {'attempt': t});
    if (!mounted) return;
    if (r == null) {
      setState(_settle);
      if (_text.text.isEmpty) _text.text = t;
      return;
    }
    setState(() {
      final label = switch (_s(r['rung'])) { 'nudge' => 'A little more', 'step' => 'Steps', 'answer' => 'Full solution', _ => 'Tutor' };
      if (t.isNotEmpty) _turns.add(('You', t));   // what she tried, in her own bubble
      _turns.add((label, _s(r['say'])));
      if (_s(r['check_question']).isNotEmpty) _turns.add(('Now you try', _s(r['check_question'])));
      _next = r['done'] == true ? '' : _s(r['next']);
      _settle();
    });
  }

  Future<void> _practice() async {
    if (!await _ensure('practice')) return;
    final r = await _call('POST', '/api/guru/sessions/$_session/practice');
    if (r != null) setState(() => _question = {..._map(r['question']), 'why': r['why'], 'mastery': r['mastery']});
  }

  Future<void> _answer(String given) async {
    _begin(given, 'Checking your answer');
    final r = await _call('POST', '/api/guru/sessions/$_session/answer', {'given': given});
    if (!mounted) return;
    if (r == null) {
      setState(_settle);
      return;
    }
    setState(() {
      if (given.trim().isNotEmpty) _turns.add(('You', given));   // her answer, in her own bubble
      _turns.add(('Tutor', _s(r['say'])));
      for (final st in (r['solution_steps'] as List? ?? const [])) {
        _turns.add(('Step', '$st'));
      }
      _question = null;
      _settle();
    });
  }

  Future<void> _lang() async {
    final t = _text.text.trim();
    if (t.isEmpty) return;
    _text.clear();
    _begin(t, 'Reading what you wrote');
    final r = await _ensure('language') ? await _call('POST', '/api/guru/sessions/$_session/language', {'text': t}) : null;
    if (!mounted) return;
    if (r == null) {
      setState(_settle);
      if (_text.text.isEmpty) _text.text = t;
      return;
    }
    setState(() {
      _turns
        ..add(('You', t))
        ..add(('Tutor', _s(r['say'])));
      _settle();
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
      const Caption('Mastery path (in chapter order, move ahead after passing the gate)'),
      Row(children: [
        Expanded(child: TextField(controller: _subject, decoration: const InputDecoration(labelText: 'Subject'))),
        const SizedBox(width: 8),
        GlassButton(label: 'View', onTap: _busy ? null : () => _loadPath()),
        const SizedBox(width: 6),
        GlassButton(label: 'Create', onTap: _busy ? null : () => _loadPath(build: true)),
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

  /// The conversation so far, drawn by the shared kit: her turns as her bubble, the tutor's words with no card (a
  /// quiet label above: "Hint", "Steps"), landing word by word when they have just arrived, one turn after the other.
  /// Under the newest of the tutor's turns: Copy and Read aloud.
  Widget _turnList() {
    var newest = -1;
    for (var i = _turns.length - 1; i >= 0; i--) {
      if (!_mine(_turns[i].$1)) {
        newest = i;
        break;
      }
    }
    final settled = _landed >= _turns.length && _work == null;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: HoolaOnDark(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          for (var i = 0; i < _turns.length && i <= _landed; i++)
            if (_mine(_turns[i].$1))
              HoolaHerBubble(_turns[i].$2, key: ValueKey('guru-$_session-$i'))
            else
              _TutorWords(
                key: ValueKey('guru-$_session-$i'),
                label: _turns[i].$1,
                text: _turns[i].$2,
                land: i == _landed,
                onLanded: () {
                  if (mounted && _landed == i) {
                    setState(() {
                      _landed = i + 1;
                      _skipMine();
                    });
                  }
                },
                actions: i == newest && settled
                    ? HoolaReplyActions(
                        text: _turns[i].$2, onToast: (t) => _snack(context, t), onAloud: widget.app.readAloud, share: false)
                    : null,
              ),
        ]),
      ),
    );
  }

  /// While the tutor works on a reply: what she sent (at once) and ONE working row with its clock.
  Widget _waiting() {
    if (_work == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: HoolaOnDark(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (_asking.isNotEmpty) HoolaHerBubble(_asking, pending: true),
          HoolaWorkingRow(label: _work, since: _since, name: 'The tutor'),
        ]),
      ),
    );
  }

  Widget _padhai() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _turnList(),
        _waiting(),
        TextField(controller: _text, minLines: 1, maxLines: 4,
            decoration: InputDecoration(labelText: _next.isEmpty ? 'Write the question' : 'What did you try? (optional)')),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: GradientButton(label: 'Explain', icon: Icons.lightbulb_rounded, height: 44, onTap: _busy ? null : _ask)),
          if (_next.isNotEmpty) ...[
            const SizedBox(width: 8),
            GlassButton(label: 'Tell me more', icon: Icons.arrow_downward_rounded, onTap: _busy ? null : _more),
          ],
        ]),
      ]);

  Widget _practiceTab() {
    final q = _question;
    final opts = (q?['options'] as List? ?? const []);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _turnList(),
      if (q == null) GradientButton(label: 'Next question', icon: Icons.quiz_rounded, height: 44, onTap: _busy ? null : _practice),
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
              TextField(controller: _typed, minLines: 1, maxLines: 5, decoration: const InputDecoration(labelText: 'Your answer')),
              const SizedBox(height: 8),
              GradientButton(label: 'Check', height: 42, onTap: _busy ? null : () { final g = _typed.text.trim(); _typed.clear(); _answer(g); }),
            ],
          ]),
        ),
      if (_work != null) const SizedBox(height: 14),
      _waiting(),
    ]);
  }

  Widget _bhasha() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Practise speaking / writing English: write, and the tutor will answer and gently correct your mistakes.',
            style: TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        _turnList(),
        _waiting(),
        TextField(controller: _text, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Write something in English')),
        const SizedBox(height: 8),
        GradientButton(label: 'Send', icon: Icons.send_rounded, height: 44, onTap: _busy ? null : _lang),
      ]);

  Widget _pragati() {
    final p = _progress;
    if (p == null) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _pathBox(),
        GlassButton(label: 'See progress', icon: Icons.insights_rounded, onTap: _loadProgress),
      ]);
    }
    final w = _map(p['week']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _pathBox(),
      Glass(child: Text('This week: ${_s(w['minutes'])} min, ${_s(w['attempts'])} questions'
          '${w['accuracy'] != null ? ', ${((w['accuracy'] as num) * 100).round()}% correct' : ''}',
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
          label: 'Report for the guardian (card)',
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
  Widget build(BuildContext context) {
    // v0.869 R8 wave 2: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: _s(widget.learner['name']),
      tabs: const ['Study', 'Practice', 'Language', 'Progress'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: false,
      busy: _busy && _work == null,   // a reply in the making shows as the working row in the conversation
      body: () => ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
        [_padhai(), _practiceTab(), _bhasha(), _pragati()][_tab],
        const SizedBox(height: 14),
        const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

/// The tutor's words in the conversation: a quiet label ("Hint", "Steps"), then the words through the shared kit
/// (no card, the reply serif, landing word by word when [land]), and the actions under the newest one.
class _TutorWords extends StatelessWidget {
  const _TutorWords({super.key, required this.label, required this.text, required this.land, required this.onLanded, this.actions});
  final String label;
  final String text;
  final bool land;
  final VoidCallback onLanded;
  final Widget? actions;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(padding: const EdgeInsets.only(bottom: 4), child: Text(label, style: HoolaType.label(c))),
        HoolaLanding(text, land: land, selectable: true, onLanded: onLanded),
        if (actions != null) actions!,
      ]),
    );
  }
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
          Expanded(child: Text('Study report → ${_s(rep['to']).isEmpty ? 'guardian' : _s(rep['to'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(sh['status']).toUpperCase(), fg: waiting ? C.warn : (_s(sh['status']) == 'shared' ? C.ok : C.muted)),
        ]),
        if (_s(rep['text']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(rep['text']), style: const TextStyle(fontSize: 12.5))),
        if (_s(src['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(src['say']), style: const TextStyle(fontSize: 12, color: C.muted))),
        const SizedBox(height: 8),
        if (waiting)
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, make the draft', height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Declined', onTap: _busy ? null : () => _decide(false)),
          ]),
        for (final e in links.entries)
          TextButton.icon(
              onPressed: () async {
                final r = await Native.openExternal(url: _s(e.value));
                if (r.isNotEmpty && r != 'ok' && context.mounted) _snack(context, r);
              },
              icon: Icon(e.key == 'email' ? Icons.mail_rounded : Icons.chat_rounded, size: 18),
              label: Text(e.key == 'email' ? 'Open email draft' : 'Open WhatsApp draft')),
      ]),
    );
  }
}
