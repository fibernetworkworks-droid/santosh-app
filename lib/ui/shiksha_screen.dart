/// Profile > Curriculum & exam designer (Shiksha suite, Pathyakram Sahayak): question bank (AI drafts -> teacher approves),
/// papers from the board's blueprint with answer key + marking scheme, year / lesson plans, rubrics, Word files.
/// Tabs: Aaj · Sawaal · Papers · Plans · Niyam. A paper / plan goes outside (file, Google Forms quiz, WhatsApp / email
/// draft) ONLY by her tap on the share card. Children's data needs the guardian's consent (DPDP Act 2023 s.9).
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

const _disclaimer = 'An AI-made draft: a teacher should read and approve it before printing / sharing. The board pattern and '
    'chapters only from the official source; confirm "ESTIMATE" items with the source.';

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {String ok = 'Next'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], minLines: 1, maxLines: k == 'notes' || k == 'task' ? 3 : 1, decoration: InputDecoration(labelText: label)),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Leave it')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Future<void> _open(BuildContext context, String url) async {
  if (url.isEmpty) return;
  final r = await Native.openExternal(url: url);
  if (r.isNotEmpty && r != 'ok' && context.mounted) _snack(context, r);
}

Color _statusColor(String st) => switch (st) {
      'approved' || 'shared' => C.ok,
      'waiting' || 'draft' => C.warn,
      _ => C.muted,
    };

class ShikshaScreen extends StatefulWidget {
  const ShikshaScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ShikshaScreen> createState() => _ShikshaScreenState();
}

class _ShikshaScreenState extends State<ShikshaScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic> _bank = const {};
  int _tab = 0;
  bool _busy = false;
  String _subject = '';
  String _grade = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _map(await widget.app.api!.call('GET', '/api/pathyakram'));
      final b = _map(await widget.app.api!.call('GET', '/api/shiksha/bank', query: {
        if (_subject.isNotEmpty) 'subject': _subject,
        if (_grade.isNotEmpty) 'grade': _grade,
        'limit': '100',
      }));
      if (mounted) setState(() {
        _d = d;
        _bank = b;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // ------------------------------------------------------------------ Aaj
  Widget _today() {
    final d = _d ?? const {};
    final classes = _list(d['classes']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: GradientButton(label: 'Make questions', icon: Icons.quiz_rounded, height: 46, onTap: _busy ? null : _generate)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Make paper', icon: Icons.description_rounded, onTap: _busy ? null : _newPaper)),
      ]),
      const SizedBox(height: 12),
      const Caption('Classes'),
      if (classes.isEmpty) const Text('No classes yet. Say in the chat: "Add class 10-A, subject Maths".', style: TextStyle(color: C.muted)),
      for (final c in classes)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Glass(
            child: Row(children: [
              Expanded(child: Text('${_s(c['number'])} · ${_s(c['name'])} (${_s(c['board'])})', style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill('${_s(c['learners'])} learners', fg: C.muted),
            ]),
          ),
        ),
      if ((d['consent_pending'] ?? 0) is int && (d['consent_pending'] as int) > 0)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text('${d['consent_pending']} students\' guardian consent is pending: until then no marks / study work for them.',
              style: const TextStyle(color: C.warn, fontSize: 12.5)),
        ),
    ]);
  }

  Future<void> _generate() async {
    final f = await _form(context, 'New questions (draft)', const [
      ('subject', 'Subject (for example Mathematics)'),
      ('grade', 'Class (for example 10)'),
      ('chapter', 'Chapter (for example Real Numbers)'),
      ('mcq', 'How many MCQs (1 mark)'),
      ('short', 'How many short answers (3 marks)'),
      ('notes', 'Anything special (optional)'),
    ], ok: 'Make');
    if (f == null) return;
    final counts = <String, int>{
      if ((int.tryParse(f['mcq'] ?? '') ?? 0) > 0) 'mcq': int.parse(f['mcq']!),
      if ((int.tryParse(f['short'] ?? '') ?? 0) > 0) 'short': int.parse(f['short']!),
    };
    await _run(() => widget.app.api!.call('POST', '/api/pathyakram/generate', body: {
          'subject': f['subject'] ?? '',
          'grade': f['grade'] ?? '',
          'chapter': f['chapter'] ?? '',
          'counts': counts.isEmpty ? {'mcq': 5} : counts,
          'marks': {'mcq': 1, 'short': 3},
          if (f['notes'] != null) 'notes': f['notes'],
        }, timeout: const Duration(minutes: 3)));
  }

  // ------------------------------------------------------------------ Sawaal (bank)
  Widget _bankTab() {
    final qs = _list(_bank['questions']);
    final counts = _map(_bank['counts']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: TextField(decoration: const InputDecoration(labelText: 'Subject'), onSubmitted: (v) { _subject = v.trim(); _load(); })),
        const SizedBox(width: 8),
        SizedBox(width: 90, child: TextField(decoration: const InputDecoration(labelText: 'Class'), onSubmitted: (v) { _grade = v.trim(); _load(); })),
      ]),
      const SizedBox(height: 8),
      Text('Total ${_s(_bank['total'])} · draft ${_s(counts['draft'] ?? 0)} · approved ${_s(counts['approved'] ?? 0)}',
          style: const TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 8),
      if (qs.isEmpty) const Text('The bank is empty: tap "Make questions".', style: TextStyle(color: C.muted)),
      for (final q in qs)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => _showQuestion(_s(q['number'])),
            child: Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${_s(q['number'])} · ${_s(q['qtype'])} · ${_s(q['marks'])} marks · ${_s(q['chapter'])}',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5))),
                  Pill(_s(q['status']).toUpperCase(), fg: _statusColor(_s(q['status']))),
                ]),
                const SizedBox(height: 4),
                Text(_s(q['text']), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                for (final c in (q['checks'] as List? ?? const []))
                  Text('• $c', style: const TextStyle(color: C.warn, fontSize: 11.5)),
              ]),
            ),
          ),
        ),
    ]);
  }

  Future<void> _showQuestion(String ref) async {
    Map<String, dynamic> q;
    try {
      q = _map(await widget.app.api!.call('GET', '/api/shiksha/bank/$ref'));
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return;
    }
    if (!mounted) return;
    final draft = _s(q['status']) == 'draft';
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (d) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text('${_s(q['number'])} · ${_s(q['qtype'])} · ${_s(q['marks'])} marks', style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              Text(_s(q['text'])),
              for (final (i, o) in (q['options'] as List? ?? const []).indexed) Text('(${'abcd'.length > i ? 'abcd'[i] : i + 1}) $o'),
              const SizedBox(height: 8),
              Text('Answer: ${_s(q['answer'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              for (final st in (q['steps'] as List? ?? const [])) Text('• $st', style: const TextStyle(fontSize: 12.5)),
              for (final sc in _list(q['scheme'])) Text('${_s(sc['point'])} (${_s(sc['marks'])})', style: const TextStyle(fontSize: 12.5, color: C.muted)),
              for (final c in (q['checks'] as List? ?? const [])) Text('• $c', style: const TextStyle(color: C.warn, fontSize: 12)),
              const SizedBox(height: 12),
              Row(children: [
                if (draft)
                  Expanded(
                    child: GradientButton(label: 'Approve', height: 44, onTap: () async {
                      Navigator.pop(d);
                      await _run(() => widget.app.api!.call('POST', '/api/shiksha/bank/status', body: {'refs': [ref], 'status': 'approved'}));
                    }),
                  ),
                if (draft) const SizedBox(width: 8),
                GlassButton(label: 'Remove', onTap: () async {
                  Navigator.pop(d);
                  await _run(() => widget.app.api!.call('POST', '/api/shiksha/bank/status', body: {'refs': [ref], 'status': 'retired'}));
                }),
              ]),
            ]),
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------------ Papers
  Future<void> _newPaper() async {
    final f = await _form(context, 'New paper', const [
      ('subject', 'Subject (for example Mathematics)'),
      ('grade', 'Class (for example 10)'),
      ('title', 'Name (for example Unit test 1)'),
      ('chapters', 'Chapters, comma separated (blank = all)'),
      ('mcq', 'Section A: how many MCQs (1 mark) - blank = board pattern'),
      ('short', 'Section B: how many short (3 marks)'),
      ('duration', 'Time (minutes)'),
    ], ok: 'Make');
    if (f == null) return;
    final mcq = int.tryParse(f['mcq'] ?? '') ?? 0;
    final sh = int.tryParse(f['short'] ?? '') ?? 0;
    final sections = [
      if (mcq > 0) {'name': 'A', 'qtype': 'mcq', 'count': mcq, 'marks_each': 1},
      if (sh > 0) {'name': 'B', 'qtype': 'short', 'count': sh, 'marks_each': 3},
    ];
    await _run(() => widget.app.api!.call('POST', '/api/pathyakram/papers', body: {
          'subject': f['subject'] ?? '',
          'grade': f['grade'] ?? '',
          if (f['title'] != null) 'title': f['title'],
          if (f['chapters'] != null) 'chapters': f['chapters']!.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
          if (sections.isNotEmpty) 'sections': sections,
          if (int.tryParse(f['duration'] ?? '') != null) 'duration_min': int.parse(f['duration']!),
        }, timeout: const Duration(minutes: 3)));
    if (mounted) setState(() => _tab = 2);
  }

  Widget _papersTab() {
    final ps = _list(_d?['papers']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      GradientButton(label: 'New paper', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newPaper),
      const SizedBox(height: 10),
      if (ps.isEmpty) const Text('No papers yet.', style: TextStyle(color: C.muted)),
      for (final p in ps)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () async {
              await Navigator.of(context).push(MaterialPageRoute(builder: (_) => PathyakramPaperPage(app: widget.app, ref: _s(p['number']))));
              _load();
            },
            child: Glass(
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(p['number'])} · ${_s(p['title'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text('${_s(p['questions'])} questions ·${_s(p['total'])}/${_s(p['max_marks'])} marks'
                        '${(p['drafts'] ?? 0) != 0 ? ' · ${p['drafts']} draft' : ''}${_list(p['gaps']).isNotEmpty ? ' · gaps' : ''}',
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
                Pill(_s(p['status']).toUpperCase(), fg: _statusColor(_s(p['status']))),
              ]),
            ),
          ),
        ),
    ]);
  }

  // ------------------------------------------------------------------ Plans
  Future<void> _newPlan(String kind) async {
    final fields = switch (kind) {
      'year' => const [('subject', 'Subject'), ('grade', 'Class'), ('chapters', 'Chapters in order, comma separated (blank = NCERT list)')],
      'lesson' => const [('subject', 'Subject'), ('grade', 'Class'), ('topic', 'Topic'), ('minutes', 'Period length in minutes (40)')],
      _ => const [('task', 'Rubric for what work (project, essay...)'), ('subject', 'Subject'), ('grade', 'Class'), ('points', 'Total points (20)')],
    };
    final f = await _form(context, kind == 'year' ? 'Year plan' : (kind == 'lesson' ? 'Lesson plan (5E)' : 'Rubric'), fields, ok: 'Make');
    if (f == null) return;
    await _run(() => widget.app.api!.call('POST', '/api/pathyakram/plans/$kind', body: {
          'subject': f['subject'] ?? '',
          'grade': f['grade'] ?? '',
          if (f['chapters'] != null) 'chapters': f['chapters']!.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
          if (f['topic'] != null) 'topic': f['topic'],
          if (int.tryParse(f['minutes'] ?? '') != null) 'minutes': int.parse(f['minutes']!),
          if (f['task'] != null) 'task': f['task'],
          if (double.tryParse(f['points'] ?? '') != null) 'total_points': double.parse(f['points']!),
        }, timeout: const Duration(minutes: 3)));
  }

  Widget _plansTab() {
    final ps = _list(_d?['plans']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Year plan', icon: Icons.calendar_month_rounded, onTap: _busy ? null : () => _newPlan('year')),
        GlassButton(label: 'Lesson plan', icon: Icons.co_present_rounded, onTap: _busy ? null : () => _newPlan('lesson')),
        GlassButton(label: 'Rubric', icon: Icons.grid_on_rounded, onTap: _busy ? null : () => _newPlan('rubric')),
      ]),
      const SizedBox(height: 10),
      if (ps.isEmpty) const Text('No plans yet.', style: TextStyle(color: C.muted)),
      for (final p in ps)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(p['number'])} · ${_s(p['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(_s(p['status']).toUpperCase(), fg: _statusColor(_s(p['status']))),
              ]),
              Wrap(spacing: 4, children: [
                if (_s(p['status']) == 'draft')
                  TextButton(onPressed: () => _run(() => widget.app.api!.call('POST', '/api/pathyakram/plans/${p['number']}/approve')), child: const Text('Approve')),
                TextButton(onPressed: () => _run(() => widget.app.api!.call('POST', '/api/pathyakram/plans/${p['number']}/file')), child: const Text('Word file')),
                if (_s(p['status']) != 'draft')
                  TextButton(
                      onPressed: () => _run(() => widget.app.api!.call('POST', '/api/pathyakram/shares', body: {'what': 'plan', 'ref': p['number'], 'via': 'file'})),
                      child: const Text('Baantna (card)')),
              ]),
            ]),
          ),
        ),
    ]);
  }

  // ------------------------------------------------------------------ Niyam
  Widget _niyam() {
    final d = _d ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Caption('Hoola will never do'),
      for (final n in (d['never'] as List? ?? const [])) Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• $n', style: const TextStyle(fontSize: 13))),
      const SizedBox(height: 10),
      const Caption('Children\'s information (DPDP Act 2023)'),
      const Text('Study / marks work for a child under 18 happens only when the school records the guardian\'s consent (and how it was checked). '
          'If consent is withdrawn the work stops; on "delete data" marks and information are removed.',
          style: TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Curriculum & exam designer')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, children: [
                for (final (i, t) in const [(0, 'Today'), (1, 'Question'), (2, 'Papers'), (3, 'Plans'), (4, 'Rules')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _bankTab(), _papersTab(), _plansTab(), _niyam()][_tab],
              const SizedBox(height: 14),
              const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// One paper: sections with questions (answers on a switch), approve, Word files, swap a question, share card.
class PathyakramPaperPage extends StatefulWidget {
  const PathyakramPaperPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<PathyakramPaperPage> createState() => _PathyakramPaperPageState();
}

class _PathyakramPaperPageState extends State<PathyakramPaperPage> {
  Map<String, dynamic>? _p;
  bool _key = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = _map(await widget.app.api!.call('GET', '/api/pathyakram/papers/${widget.ref}', query: {'key': _key ? 'true' : 'false'}));
      if (mounted) setState(() => _p = p);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _share() async {
    final via = await showDialog<String>(
      context: context,
      builder: (d) => SimpleDialog(title: const Text('How to share?'), children: [
        for (final (k, t) in const [('file', 'Word file only (for print)'), ('form', 'Google Forms quiz (objective questions)'),
          ('whatsapp', 'WhatsApp draft'), ('email', 'Email draft')])
          SimpleDialogOption(onPressed: () => Navigator.pop(d, k), child: Text(t)),
      ]),
    );
    if (via == null || !mounted) return;
    String contact = '';
    if (via == 'whatsapp' || via == 'email') {
      final f = await _form(context, 'To whom', [('to_name', 'Name'), ('to_contact', via == 'email' ? 'Email' : 'Phone')]);
      if (f == null) return;
      contact = f['to_contact'] ?? '';
      await _run(() => widget.app.api!.call('POST', '/api/pathyakram/shares',
          body: {'what': 'paper', 'ref': widget.ref, 'via': via, 'to_name': f['to_name'] ?? '', 'to_contact': contact}));
      return;
    }
    await _run(() => widget.app.api!.call('POST', '/api/pathyakram/shares', body: {'what': 'paper', 'ref': widget.ref, 'via': via}));
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    final draft = _s(p?['status']) == 'draft';
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.ref)),
      body: Aurora(
        child: p == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(p['title']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                    Text('Class ${_s(p['grade'])} · ${_s(p['subject'])} · ${_s(p['total'])}/${_s(p['max_marks'])} marks'
                        '${_s(p['duration_min']) != '0' ? ' · ${_s(p['duration_min'])} min' : ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    Text(_s(_map(p['blueprint'])['say']), style: const TextStyle(fontSize: 12, color: C.muted)),
                    for (final g in _list(p['gaps']))
                      Text('Section ${_s(g['section'])}: ${_s(g['have'])}/${_s(g['need'])} questions (${_s(g['qtype'])}, ${_s(g['marks_each'])} marks)',
                          style: const TextStyle(color: C.warn, fontSize: 12)),
                  ]),
                ),
                const SizedBox(height: 8),
                if (_busy) const LinearProgressIndicator(),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (draft) GradientButton(label: 'Approve', height: 42, onTap: () => _run(() => widget.app.api!.call('POST', '/api/pathyakram/papers/${widget.ref}/approve'))),
                  GlassButton(label: 'Word file', icon: Icons.description_rounded, onTap: () => _run(() => widget.app.api!.call('POST', '/api/pathyakram/papers/${widget.ref}/file', body: {'key': false}))),
                  GlassButton(label: 'Answer key', icon: Icons.key_rounded, onTap: () => _run(() => widget.app.api!.call('POST', '/api/pathyakram/papers/${widget.ref}/file', body: {'key': true}))),
                  if (!draft) GlassButton(label: 'Sharing', icon: Icons.outbox_rounded, onTap: _share),
                ]),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _key,
                  onChanged: (v) {
                    setState(() => _key = v);
                    _load();
                  },
                  title: const Text('Show answers and marking scheme'),
                ),
                for (final sec in _list(p['sections'])) ...[
                  Caption('Section ${_s(sec['name'])}'),
                  for (final q in _list(sec['questions']))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Glass(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            Expanded(child: Text(q['choice'] == true ? 'OR' : 'Q${_s(q['n'])} · ${_s(q['marks'])} marks · ${_s(q['number'])}',
                                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5))),
                            if (_s(q['status']) != 'approved') Pill('DRAFT', fg: C.warn),
                            if (draft)
                              IconButton(
                                tooltip: 'Second question',
                                icon: const Icon(Icons.swap_horiz_rounded, size: 20),
                                onPressed: () => _run(() => widget.app.api!.call('POST', '/api/pathyakram/papers/${widget.ref}/swap', body: {'n': q['n']})),
                              ),
                          ]),
                          Text(_s(q['text']), style: const TextStyle(fontSize: 13)),
                          for (final (i, o) in (q['options'] as List? ?? const []).indexed) Text('(${i < 4 ? 'abcd'[i] : i + 1}) $o', style: const TextStyle(fontSize: 12.5)),
                          if (_key) Text('Answer: ${_s(q['answer'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
                          if (_key) for (final sc in _list(q['scheme'])) Text('${_s(sc['point'])} (${_s(sc['marks'])})', style: const TextStyle(fontSize: 12, color: C.muted)),
                        ]),
                      ),
                    ),
                ],
              ]),
      ),
    );
  }
}

/// A paper is ready (chat card): summary + open the paper page.
class PathyakramPaperCard extends StatelessWidget {
  const PathyakramPaperCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final p = _map(data['paper']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Icon(Icons.description_rounded, size: 18, color: C.accent),
          const SizedBox(width: 6),
          Expanded(child: Text('${_s(p['number'])} · ${_s(p['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(p['status']).toUpperCase(), fg: _statusColor(_s(p['status']))),
        ]),
        if (_s(data['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, color: C.muted))),
        TextButton(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PathyakramPaperPage(app: app, ref: _s(p['number'])))),
          child: const Text('Open paper'),
        ),
      ]),
    );
  }
}

/// A paper / plan going outside: ONLY her tap here decides (POST /api/pathyakram/shares/{id}/decide).
class PathyakramShareCard extends StatefulWidget {
  const PathyakramShareCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<PathyakramShareCard> createState() => _PathyakramShareCardState();
}

class _PathyakramShareCardState extends State<PathyakramShareCard> {
  Map<String, dynamic>? _done;
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    final sh = _map(widget.data['share']);
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call('POST', '/api/pathyakram/shares/${sh['id']}/decide',
          body: {'yes': yes, 'hash': sh['hash']}, timeout: const Duration(minutes: 2)));
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
    final res = _map(sh['result']).isNotEmpty ? _map(sh['result']) : src;
    final links = _map(res['links']);
    final form = _map(res['form']);
    final waiting = _s(sh['status']) == 'waiting';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Icon(Icons.outbox_rounded, size: 18, color: C.accent),
          const SizedBox(width: 6),
          Expanded(child: Text('${_s(sh['number'])}: ${_s(src['number'] ?? sh['what'])} · ${_s(sh['via'])}${sh['with_key'] == true ? ' + answer key' : ''}',
              style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(sh['status']).toUpperCase(), fg: _statusColor(_s(sh['status']))),
        ]),
        if (_s(src['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(src['say']), style: const TextStyle(fontSize: 12.5, color: C.muted))),
        const SizedBox(height: 8),
        if (waiting)
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, prepare', height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Decline', onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_s(form['responder_link']).isNotEmpty)
          TextButton.icon(onPressed: () => _open(context, _s(form['responder_link'])), icon: const Icon(Icons.quiz_rounded, size: 18), label: const Text('Open quiz link')),
        for (final e in links.entries)
          TextButton.icon(
              onPressed: () => _open(context, _s(e.value)),
              icon: Icon(e.key == 'email' ? Icons.mail_rounded : Icons.chat_rounded, size: 18),
              label: Text(e.key == 'email' ? 'Open email draft' : 'Open WhatsApp draft (attach the file yourself)')),
      ]),
    );
  }
}
