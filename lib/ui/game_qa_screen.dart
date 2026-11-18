/// v0.416 QA (Studio project > QA): Hoola's bots play a debug build of the game on phone speeds; the verdict, the
/// golden start screen, the bot runs and the bugs. A bot-found bug closes only when the same bot cannot find it again.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

Color _vc(String v) => v == 'PASS' ? C.ok : v == 'FAIL' ? C.bad : v == 'CONCERNS' ? C.warn : C.muted;

class GameQaScreen extends StatefulWidget {
  const GameQaScreen({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<GameQaScreen> createState() => _GameQaScreenState();
}

class _GameQaScreenState extends State<GameQaScreen> {
  Map<String, dynamic> _d = {};
  bool _loaded = false;
  bool _busy = false;
  final _bug = TextEditingController();
  String _sev = 'major';
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _bug.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    _timer?.cancel();
    try {
      final d = await widget.app.api!.gameQa(widget.id);
      if (!mounted) return;
      setState(() {
        _d = d;
        _loaded = true;
      });
      if (d['running'] == true) _timer = Timer(const Duration(seconds: 8), _load);
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

  Widget _summary() {
    final l = Map<String, dynamic>.from((_d['last'] as Map?) ?? const {});
    if (l.isEmpty) return const Text('The bots have not played this game yet.', style: TextStyle(color: C.muted));
    final perf = Map<String, dynamic>.from((l['perf'] as Map?) ?? const {});
    final gold = Map<String, dynamic>.from((l['golden'] as Map?) ?? const {});
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(_s(l['verdict']), style: display(17, color: _vc(_s(l['verdict'])))),
          const SizedBox(width: 8),
          Text('v${_i(l['version'])}', style: const TextStyle(color: C.muted)),
        ]),
        for (final x in _strs(l['blockers'])) Text('Blocker: $x', style: const TextStyle(color: C.bad, fontSize: 13)),
        for (final x in _strs(l['concerns'])) Text('Concern: $x', style: const TextStyle(fontSize: 13)),
        for (final x in _strs(l['missing'])) Text('Not assessed: $x', style: const TextStyle(color: C.muted, fontSize: 13)),
        if (perf['fps_avg'] != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('${perf['fps_avg']} fps average'
                '${perf['mid_phone_fps'] != null ? ' · ${perf['mid_phone_fps']} on a mid phone' : ''}'
                '${perf['load_s'] != null ? ' · ${perf['load_s']} s to start' : ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ),
        if (_s(gold['candidate_url']).isNotEmpty) ...[
          const SizedBox(height: 8),
          Row(children: [
            if (_s(gold['golden_url']).isNotEmpty)
              Expanded(child: Column(children: [
                Image.network(widget.app.api!.absolute(_s(gold['golden_url'])), height: 140),
                const Text('Golden', style: TextStyle(fontSize: 12, color: C.muted)),
              ])),
            Expanded(child: Column(children: [
              Image.network(widget.app.api!.absolute(_s(gold['candidate_url'])), height: 140),
              Text('This run${gold['diff'] != null ? ' · ${((gold['diff'] as num) * 100).toStringAsFixed(1)}% different' : ''}',
                  style: const TextStyle(fontSize: 12, color: C.muted)),
            ])),
          ]),
          if (_s(gold['verdict']) != 'same')
            TextButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gameQaGolden(widget.id), 'Saved as the golden start screen.'),
                child: const Text('This is how it should look')),
        ],
      ]),
    );
  }

  Widget _bugTile(Map<String, dynamic> b) {
    final st = _s(b['status']);
    final open = st == 'open' || st == 'fixing';
    final rp = Map<String, dynamic>.from((b['repro'] as Map?) ?? const {});
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_s(b['number'])}  ${_s(b['title'])}', style: const TextStyle(fontSize: 14, height: 1.35)),
        Text('${_s(b['severity'])} · ${st == 'fixed' ? 'fixed (bot checked)' : st}'
            '${_i(b['regression']) > 0 ? ' · came back ×${_i(b['regression'])}' : ''}'
            ' · ${_s(b['source']) == 'her' ? 'reported by you' : 'bot ${_s(rp['bot'])} #${_s(rp['seed'])} on ${_s(rp['profile']).replaceAll('_', ' ')}'}'
            '${_s(b['task']).isNotEmpty ? ' · task ${_s(b['task'])}' : ''}',
            style: TextStyle(color: open && (_s(b['severity']) == 'crash' || _s(b['severity']) == 'blocker') ? C.bad : C.muted, fontSize: 12)),
        for (final e in _strs((b['evidence'] as Map?)?['errors']).take(2)) Text(e, style: const TextStyle(color: C.bad, fontSize: 12)),
        Wrap(spacing: 8, children: [
          if (open && _s(b['task']).isEmpty)
            FilledButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gameBugDo(widget.id, _s(b['number']), 'fix'), 'A fix task is on the board.'),
                child: const Text('Fix it')),
          if (open)
            OutlinedButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gameBugDo(widget.id, _s(b['number']), 'wontfix'), ''),
                child: const Text("Won't fix"))
          else
            OutlinedButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gameBugDo(widget.id, _s(b['number']), 'open'), ''),
                child: const Text('Reopen')),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bugs = _list(_d['bugs']);
    return DeskPage(
      title: 'QA',
      onRefresh: _load,
      body: () => RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              const Text('Hoola\'s bots play a debug build on desktop and phone speeds every night, the same way each time.',
                  style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
              const SizedBox(height: 10),
              GradientButton(
                label: _d['running'] == true ? 'Bots are playing…' : 'Run the QA bots now',
                icon: Icons.smart_toy_outlined,
                height: 48,
                onTap: _busy || _d['running'] == true
                    ? null
                    : () => _call(() => widget.app.api!.gameQaRun(widget.id), 'The bots are playing (2-4 minutes).'),
              ),
              const SizedBox(height: 12),
              _summary(),
              const SizedBox(height: 12),
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Bugs  ${_i(_d['open'])} open', style: display(15)),
                  TextField(controller: _bug, maxLength: 200, decoration: const InputDecoration(hintText: 'Report a bug in one line')),
                  Wrap(spacing: 6, children: [
                    for (final s in const ['major', 'crash', 'minor', 'visual', 'perf'])
                      ChoiceChip(label: Text(s), selected: _sev == s, onSelected: (_) => setState(() => _sev = s)),
                  ]),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton(
                        onPressed: _busy
                            ? null
                            : () {
                                final t = _bug.text.trim();
                                if (t.length < 4) {
                                  _snack(context, 'Write the bug in one line.');
                                  return;
                                }
                                _call(() => widget.app.api!.gameBugNew(widget.id, t, _sev), 'Bug saved.').then((_) => _bug.clear());
                              },
                        child: const Text('Report')),
                  ),
                  if (bugs.isEmpty) const Text('No bugs.', style: TextStyle(color: C.muted)),
                  for (final b in bugs) _bugTile(b),
                ]),
              ),
            ],
          ]),
        ),
    );
  }
}
