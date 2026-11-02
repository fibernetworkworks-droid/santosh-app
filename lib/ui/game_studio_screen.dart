/// v0.386 STUDIO PROJECT (Game Desk > Studio projects): one game as a long project - milestones, a task board where
/// every task is one small change that waits for her OK, a decisions log she can ask "why" from, the nightly build and
/// the morning report. Same server as the web console: /api/gamestudio*.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'game_assets_screen.dart';
import 'game_bible_screen.dart';
import 'game_qa_screen.dart';
import 'game_release_screen.dart';
import 'game_roles_screen.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _cols = [
  ('review', 'Waiting for your OK', C.warn),
  ('working', 'Hoola working', C.accentSoft),
  ('blocked', 'Stuck', C.bad),
  ('todo', 'To do', C.muted),
  ('done', 'Done', C.ok),
];

class GameStudioScreen extends StatefulWidget {
  const GameStudioScreen({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<GameStudioScreen> createState() => _GameStudioScreenState();
}

class _GameStudioScreenState extends State<GameStudioScreen> {
  Map<String, dynamic> _p = {};
  bool _loaded = false;
  bool _busy = false;
  String _milestone = '';
  int _priority = 2;
  final _task = TextEditingController();
  final _decision = TextEditingController();
  final _why = TextEditingController();
  List<Map<String, dynamic>> _found = [];
  String _whyNote = '';
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _task.dispose();
    _decision.dispose();
    _why.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    _timer?.cancel();
    try {
      final p = await widget.app.api!.gameStudio(widget.id);
      if (!mounted) return;
      setState(() {
        _p = p;
        _loaded = true;
        if (_milestone.isEmpty) _milestone = _s(p['milestone']);
      });
      final counts = Map<String, dynamic>.from((p['counts'] as Map?) ?? const {});
      if (_i(counts['working']) > 0) _timer = Timer(const Duration(seconds: 5), _load);
    } catch (e) {
      if (mounted) {
        setState(() => _loaded = true);
        _snack(context, '$e');
      }
    }
  }

  Future<void> _call(Future<dynamic> Function() f, String ok) async {
    setState(() => _busy = true);
    try {
      await f();
      if (mounted && ok.isNotEmpty) _snack(context, ok);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Future<String?> _ask(String title, String hint) async {
    final c = TextEditingController();
    final r = await showDialog<String>(
        context: context,
        builder: (d) => AlertDialog(
              title: Text(title),
              content: TextField(controller: c, maxLines: 3, minLines: 1, decoration: InputDecoration(hintText: hint)),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d), child: const Text('Cancel')),
                TextButton(onPressed: () => Navigator.pop(d, c.text.trim()), child: const Text('OK')),
              ],
            ));
    c.dispose();
    return r;
  }

  Future<void> _act(Map<String, dynamic> t, String action) async {
    final id = _s(_p['id']);
    final num = _s(t['number']);
    if (action == 'start') {
      return _call(() => widget.app.api!.gameStudioStart(id, task: num), 'Building. It will wait for your OK.');
    }
    var note = '';
    if (action == 'back') {
      final n = await _ask('What was wrong?', 'Hoola tries again with this');
      if (n == null) return;
      note = n;
    } else if (action == 'ok') {
      note = await _ask('Anything to remember?', 'Optional: saved as a decision') ?? '';
    }
    await _call(() => widget.app.api!.gameStudioTask(id, num, action, note: note), action == 'ok' ? 'Done.' : '');
  }

  Widget _milestones() {
    final ms = _list(_p['milestones']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final m in ms)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(m['name']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14))),
                Text('${_i(m['done'])}/${_i(m['total'])}${_s(m['target']).isNotEmpty ? ' · ${_s(m['target'])}' : ''}',
                    style: const TextStyle(color: C.muted, fontSize: 12.5)),
              ]),
              const SizedBox(height: 4),
              LinearProgressIndicator(value: _i(m['pct']) / 100, color: C.accent, backgroundColor: C.panel),
              Row(children: [
                if (_gateFor(_s(m['key'])).isNotEmpty)
                  Text(_s(_gateFor(_s(m['key']))['verdict']), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                const Spacer(),
                TextButton(
                    onPressed: _busy ? null : () => _gate(_s(m['key'])),
                    child: const Text('Gate check', style: TextStyle(fontSize: 12.5))),
              ]),
            ]),
          ),
      ]),
    );
  }

  Map<String, dynamic> _gateFor(String key) =>
      _list(_p['gates']).firstWhere((g) => _s(g['milestone']) == key, orElse: () => <String, dynamic>{});

  Future<void> _gate(String key) async {
    setState(() => _busy = true);
    try {
      final g = await widget.app.api!.gameStudioGate(_s(_p['id']), key);
      if (mounted) {
        final lines = [
          ..._strs(g['blockers']).map((x) => 'Blocker: $x'),
          ..._strs(g['concerns']).map((x) => 'Concern: $x'),
          ..._strs(g['missing']).map((x) => 'Missing: $x'),
          ...Map<String, dynamic>.from((g['views'] as Map?) ?? const {}).entries.map((e) => '${e.key.replaceAll('_', ' ')}: ${e.value}'),
        ];
        await showDialog<void>(
            context: context,
            builder: (d) => AlertDialog(
                  title: Text('${_s(g['name'])}: ${_s(g['verdict'])}'),
                  content: SingleChildScrollView(child: Text([...lines, _s(g['note'])].join('\n\n'))),
                  actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Close'))],
                ));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Widget _add() {
    final ms = _list(_p['milestones']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('New task', style: display(15)),
        TextField(
          controller: _task,
          maxLength: 200,
          decoration: const InputDecoration(hintText: 'One small change, e.g. add a nitro boost (double tap)'),
        ),
        Wrap(spacing: 8, runSpacing: 6, children: [
          for (final m in ms)
            ChoiceChip(
              label: Text(_s(m['name'])),
              selected: _milestone == _s(m['key']),
              onSelected: (_) => setState(() => _milestone = _s(m['key'])),
            ),
        ]),
        const SizedBox(height: 6),
        Wrap(spacing: 8, children: [
          for (final p in const [(1, 'High'), (2, 'Normal'), (3, 'Low')])
            ChoiceChip(label: Text(p.$2), selected: _priority == p.$1, onSelected: (_) => setState(() => _priority = p.$1)),
        ]),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          FilledButton(
              onPressed: _busy
                  ? null
                  : () {
                      final t = _task.text.trim();
                      if (t.length < 3) {
                        _snack(context, 'Write the task in one line.');
                        return;
                      }
                      _call(() => widget.app.api!.gameStudioAdd(_s(_p['id']), t, _milestone, _priority), 'Added to To do.')
                          .then((_) => _task.clear());
                    },
              child: const Text('Add task')),
          OutlinedButton(
              onPressed: _busy
                  ? null
                  : () => _call(() => widget.app.api!.gameStudioPlan(_s(_p['id']), words: _task.text.trim()),
                      'Hoola added the next tasks to To do. Drop any you do not want.'),
              child: const Text('Let Hoola plan')),
        ]),
      ]),
    );
  }

  Widget _taskTile(Map<String, dynamic> t) {
    final st = _s(t['status']);
    Widget b(String a, String label, {bool main = false}) => main
        ? FilledButton(onPressed: _busy ? null : () => _act(t, a), child: Text(label))
        : OutlinedButton(onPressed: _busy ? null : () => _act(t, a), child: Text(label));
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: C.panel,
        borderRadius: BorderRadius.circular(10),
        border: _i(t['priority']) == 1 ? Border.all(color: C.bad.withOpacity(.55)) : null,   // high priority
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_s(t['number'])}  ${_s(t['title'])}', style: const TextStyle(fontSize: 14, height: 1.35)),
        const SizedBox(height: 2),
        Text('${_s(t['role_name'])}${_s(t['role_mode']) == 'writes' ? ' (writes)' : ''} · ${_s(t['milestone'])}'
            '${_s(t['source']) != 'her' ? ' · by Hoola' : ''}${_i(t['version']) > 0 ? ' · v${_i(t['version'])}' : ''}',
            style: const TextStyle(color: C.muted, fontSize: 12)),
        if (_s(t['detail']).isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(t['detail']), style: const TextStyle(color: C.muted, fontSize: 12.5))),
        if (st == 'review' && _s(t['notes']).isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(t['notes']), style: const TextStyle(fontSize: 12.5))),
        if (_s(t['error']).isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(t['error']), style: const TextStyle(color: C.bad, fontSize: 12.5))),
        // v0.406 the crew: how "done" is checked, the counted verdict, and the lead's review
        for (final c in _list(t['criteria']))
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(c['status']) == 'covered' ? '✓ ' : _s(c['status']) == 'failed' ? '✕ ' : '○ ',
                  style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600,
                      color: _s(c['status']) == 'covered' ? C.ok : _s(c['status']) == 'failed' ? C.bad : C.muted)),
              Expanded(child: Text(_s(c['text']), style: TextStyle(fontSize: 12.5, color: _s(c['status']) == 'untested' ? C.muted : C.ink))),
            ]),
          ),
        if (st == 'review' || st == 'done')
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('${_s(t['verdict'])}${t['evidence_old'] == true ? ' · evidence older than the code' : ''}',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600,
                    color: _s(t['verdict']) == 'COMPLETE' ? C.ok : _s(t['verdict']) == 'BLOCKED' ? C.bad : C.warn)),
          ),
        if (_s((t['review'] as Map?)?['summary']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('${_s((t['review'] as Map?)?['by_name'])}: ${_s((t['review'] as Map?)?['summary'])}'
                '${_strs((t['review'] as Map?)?['findings']).map((f) => '\n• $f').join()}', style: const TextStyle(fontSize: 12.5)),
          ),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (st == 'todo') ...[b('start', _s(t['role_mode']) == 'writes' ? 'Write it now' : 'Build now', main: true), b('drop', 'Drop')],
          if (st == 'review') ...[
            b('ok', 'OK', main: true),
            b('back', 'Send back'),
            if (_s(t['role_mode']) != 'writes') b('review', 'Ask the lead'),
          ],
          if (st == 'blocked') ...[b('start', 'Try again', main: true), b('drop', 'Drop')],
          if (st == 'done') b('back', 'Undo'),
        ]),
      ]),
    );
  }

  Widget _board() {
    final tasks = _list(_p['tasks']);
    return Column(children: [
      for (final (key, label, color) in _cols)
        Builder(builder: (_) {
          var mine = tasks.where((t) => _s(t['status']) == key).toList();
          if (key == 'done') mine = mine.reversed.take(10).toList();
          if (mine.isEmpty && key != 'todo') return const SizedBox.shrink();
          return Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
                  const SizedBox(width: 8),
                  Text('$label  ${mine.length}', style: display(14.5)),
                ]),
                if (mine.isEmpty) const Padding(padding: EdgeInsets.only(top: 6), child: Text('Nothing here.', style: TextStyle(color: C.muted))),
                for (final t in mine) _taskTile(t),
              ]),
            ),
          );
        }),
    ]);
  }

  Widget _log() {
    final decs = _list(_p['decisions']);
    final night = Map<String, dynamic>.from((_p['night'] as Map?) ?? const {});
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Nightly build', style: display(15)),
          const SizedBox(height: 4),
          Text(
              night.isEmpty
                  ? 'No nightly build yet.'
                  : '${night['ok'] == true ? 'Passed' : 'Failed'} · v${_i(night['version'])}'
                      '${night['fps'] != null ? ' · ${night['fps']} fps' : ''}${night['load_s'] != null ? ' · ${night['load_s']} s to start' : ''}',
              style: TextStyle(color: night.isEmpty ? C.muted : (night['ok'] == true ? C.ok : C.bad), fontSize: 13.5)),
          if (((night['suspects'] as List?) ?? const []).isNotEmpty)
            Text('Probably from: ${((night['suspects'] as List?) ?? const []).join(', ')}', style: const TextStyle(fontSize: 13)),
          TextButton(
              onPressed: _busy
                  ? null
                  : () async {
                      try {
                        final r = await widget.app.api!.gameStudioSummary(_s(_p['id']));
                        if (!mounted) return;
                        await showDialog<void>(
                            context: context,
                            builder: (d) => AlertDialog(
                                  title: const Text('Morning report'),
                                  content: SingleChildScrollView(child: SelectableText(_s(r['text']))),
                                  actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Close'))],
                                ));
                      } catch (e) {
                        if (mounted) _snack(context, '$e');
                      }
                    },
              child: const Text('Morning report now')),
          const Divider(),
          Text('Decisions', style: display(15)),
          TextField(controller: _decision, maxLength: 600, decoration: const InputDecoration(hintText: 'e.g. no guns: it is for kids')),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
                onPressed: _busy
                    ? null
                    : () {
                        final t = _decision.text.trim();
                        if (t.isEmpty) return;
                        _call(() => widget.app.api!.gameStudioDecide(_s(_p['id']), t), 'Saved.').then((_) => _decision.clear());
                      },
                child: const Text('Save decision')),
          ),
          TextField(controller: _why, decoration: const InputDecoration(hintText: 'Ask why, e.g. why is the jump so high?')),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
                onPressed: () async {
                  final q = _why.text.trim();
                  if (q.isEmpty) return;
                  try {
                    final r = await widget.app.api!.gameStudioWhy(_s(_p['id']), q);
                    if (!mounted) return;
                    setState(() {
                      _found = _list(r['found']);
                      _whyNote = _found.isEmpty ? 'Nothing in the log about this.' : '';
                    });
                  } catch (e) {
                    if (mounted) _snack(context, '$e');
                  }
                },
                child: const Text('Find')),
          ),
          if (_whyNote.isNotEmpty) Text(_whyNote, style: const TextStyle(color: C.muted, fontSize: 13)),
          for (final f in _found)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('${_s(f['text'])}${_s(f['why']).isNotEmpty ? ' - ${_s(f['why'])}' : ''}', style: const TextStyle(fontSize: 13)),
            ),
          const SizedBox(height: 8),
          for (final d in decs.take(20))
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('${_s(d['at']).length >= 10 ? _s(d['at']).substring(0, 10) : ''}  ${_s(d['text'])}'
                  '${_s(d['why']).isNotEmpty ? ' - ${_s(d['why'])}' : ''}', style: const TextStyle(fontSize: 13)),
            ),
        ]),
      ),
    );
  }

  Widget _settings() => Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Glass(
          child: Column(children: [
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('After my OK, start the next task by itself'),
              value: _p['auto'] == true,
              onChanged: _busy ? null : (v) => _call(() => widget.app.api!.gameStudioSettings(_s(_p['id']), {'auto': v}), ''),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Build and play it every night'),
              value: _p['nightly_on'] == true,
              onChanged: _busy ? null : (v) => _call(() => widget.app.api!.gameStudioSettings(_s(_p['id']), {'nightly_on': v}), ''),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: Text('Morning report at ${_i(_p['summary_hour'])} am'),
              value: _p['summary_on'] == true,
              onChanged: _busy ? null : (v) => _call(() => widget.app.api!.gameStudioSettings(_s(_p['id']), {'summary_on': v}), ''),
            ),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final g = Map<String, dynamic>.from((_p['game'] as Map?) ?? const {});
    final url = _s(g['play_url']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_loaded ? '${_s(_p['number'])} ${_s(_p['title'])}' : 'Studio project')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              if (_s(_p['goal']).isNotEmpty) Text(_s(_p['goal']), style: const TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
              const SizedBox(height: 10),
              if (url.isNotEmpty)
                GradientButton(
                    label: 'Play v${_i(g['version'])}',
                    icon: Icons.play_arrow_rounded,
                    height: 48,
                    onTap: () => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication)),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.menu_book_rounded),
                label: Text('Game Bible${_i((_p['bible'] as Map?)?['version']) > 0 ? ' v${_i((_p['bible'] as Map?)?['version'])}' : ''}'
                    '${(_p['bible'] as Map?)?['draft'] == true ? ' · draft waiting' : ''}'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameBibleScreen(app: widget.app, id: _s(_p['id']))));
                  await _load();
                },
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.terrain_outlined),
                label: const Text('Worlds'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameWorldsScreen(app: widget.app, studio: _s(_p['id']))));
                  await _load();
                },
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.sports_baseball_outlined),
                label: const Text('Physics'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GamePhysicsScreen(app: widget.app, studio: _s(_p['id']))));
                  await _load();
                },
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.surround_sound_outlined),
                label: const Text('Audio'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameAudioScreen(app: widget.app, studio: _s(_p['id']))));
                  await _load();
                },
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.vibration_outlined),
                label: const Text('Haptics'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameHapticsScreen(app: widget.app, studio: _s(_p['id']))));
                  await _load();
                },
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.groups_outlined),
                label: const Text('Multiplayer'),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameNetScreen(app: widget.app, studio: _s(_p['id'])))),
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.view_in_ar_outlined),
                label: const Text('VR / AR'),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameXrScreen(app: widget.app, studio: _s(_p['id'])))),
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.replay_circle_filled_outlined),
                label: const Text('Runtime'),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameRuntimeScreen(app: widget.app, studio: _s(_p['id'])))),
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.rocket_launch_outlined),
                label: const Text('Release'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameReleaseScreen(app: widget.app, id: _s(_p['id']))));
                  await _load();
                },
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.bug_report_outlined),
                label: Text('QA${_s((_p['qa'] as Map?)?['verdict']).isNotEmpty ? ' · ${_s((_p['qa'] as Map?)?['verdict'])}' : ''}'
                    '${_i((_p['qa'] as Map?)?['open']) > 0 ? ' · ${_i((_p['qa'] as Map?)?['open'])} bugs' : ''}'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameQaScreen(app: widget.app, id: _s(_p['id']))));
                  await _load();
                },
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.palette_outlined),
                label: Text('Assets${_i((_p['assets'] as Map?)?['count']) > 0 ? ' · ${_i((_p['assets'] as Map?)?['in_game'])} in game' : ''}'
                    '${_i((_p['assets'] as Map?)?['waiting_ok']) > 0 ? ' · ${_i((_p['assets'] as Map?)?['waiting_ok'])} for your OK' : ''}'),
                onPressed: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameAssetsScreen(app: widget.app, id: _s(_p['id']))));
                  await _load();
                },
              ),
              const SizedBox(height: 12),
              _milestones(),
              const SizedBox(height: 12),
              _add(),
              _board(),
              _log(),
              _settings(),
            ],
          ]),
        ),
      ),
    );
  }
}

/// The Game Desk's "Studio projects" block: open a project, or turn a game that plays into a long project.
class GameStudioList extends StatefulWidget {
  const GameStudioList({super.key, required this.app, required this.games});
  final Santosh app;
  final List<Map<String, dynamic>> games;
  @override
  State<GameStudioList> createState() => _GameStudioListState();
}

class _GameStudioListState extends State<GameStudioList> {
  List<Map<String, dynamic>> _projects = [];
  String _pick = '';
  final _goal = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _goal.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.gameStudios();
      if (mounted) setState(() => _projects = _list(d['projects']));
    } catch (_) {}
  }

  Future<void> _open(String id) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GameStudioScreen(app: widget.app, id: id)));
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final taken = _projects.map((p) => _s((p['game'] as Map?)?['id'])).toSet();
    final free = widget.games.where((g) => _i(g['version']) > 0 && !taken.contains(_s(g['id']))).toList();
    if (_pick.isEmpty && free.isNotEmpty) _pick = _s(free.first['id']);
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Studio projects', style: display(16)),
          const SizedBox(height: 4),
          const Text('A long project around one game: task board, milestones, decisions, nightly build, morning report.',
              style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
          for (final p in _projects)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text('${_s(p['number'])} · ${_s(p['title'])}'),
              subtitle: Text(_i((p['counts'] as Map?)?['review']) > 0
                  ? '${_i((p['counts'] as Map?)?['review'])} waiting for your OK'
                  : '${_i((p['counts'] as Map?)?['todo'])} to do · ${_i((p['counts'] as Map?)?['done'])} done'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => _open(_s(p['id'])),
            ),
          if (free.isNotEmpty) ...[
            const SizedBox(height: 8),
            DropdownButton<String>(
              value: _pick,
              isExpanded: true,
              items: [for (final g in free) DropdownMenuItem(value: _s(g['id']), child: Text('${_s(g['number'])} · ${_s(g['title'])}'))],
              onChanged: (v) => setState(() => _pick = v ?? ''),
            ),
            TextField(controller: _goal, maxLength: 1500, decoration: const InputDecoration(hintText: 'Goal, e.g. release in 6 months')),
            OutlinedButton(
                onPressed: _busy || _pick.isEmpty
                    ? null
                    : () async {
                        setState(() => _busy = true);
                        try {
                          final p = await widget.app.api!.gameStudioNew(_pick, _goal.text.trim());
                          _goal.clear();
                          if (mounted) await _open(_s(p['id']));
                        } catch (e) {
                          if (mounted) _snack(context, '$e');
                        }
                        if (mounted) setState(() => _busy = false);
                      },
                child: const Text('Start a long project')),
          ],
        ]),
      ),
    );
  }
}
