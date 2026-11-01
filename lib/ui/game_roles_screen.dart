/// v0.420 GAME DESK ROLES (Phase 7 batch 1): the Procedural World Engineer's Worlds and the Physics Engine Developer's
/// Physics, each its own employee. Worlds are made from rules + a seed by code and checked reachable; physics settings
/// are proved in Godot's own physics lab. Nothing enters her game before her OK. Full detail also in the web console.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _status = {
  'draft': ('Waiting for your OK', C.warn),
  'approved': ('In the game', C.ok),
  'rejected': ('Not used', C.muted),
  'failed': ('Failed its checks', C.bad),
  'testing': ('Lab running', C.accentSoft),
};

Widget _tag(String status) {
  final (text, color) = _status[status] ?? (status, C.muted);
  return Text(text, style: TextStyle(color: color, fontSize: 11.5, fontWeight: FontWeight.w600));
}

Widget _checks(Map<String, dynamic> ch) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      for (final e in _strs(ch['errors'])) Text('✕ $e', style: const TextStyle(color: C.bad, fontSize: 12.5)),
      for (final w in _strs(ch['warnings'])) Text('! $w', style: const TextStyle(color: C.muted, fontSize: 12.5)),
      for (final p in _strs(ch['passed'])) Text('✓ $p', style: const TextStyle(fontSize: 12.5)),
    ]);

// ================================================================ Worlds
class GameWorldsScreen extends StatefulWidget {
  const GameWorldsScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  State<GameWorldsScreen> createState() => _GameWorldsScreenState();
}

class _GameWorldsScreenState extends State<GameWorldsScreen> {
  Map<String, dynamic> _d = {};
  bool _loaded = false;
  bool _busy = false;
  String _kind = '';
  final _words = TextEditingController();
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _words.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    _timer?.cancel();
    try {
      final d = await widget.app.api!.gameWorlds(widget.studio);
      if (!mounted) return;
      setState(() {
        _d = d;
        _loaded = true;
      });
      if (_list(d['worlds']).any((w) => _s(_map(w['demo'])['status']) == 'building')) _timer = Timer(const Duration(seconds: 5), _load);
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

  Widget _card(Map<String, dynamic> w) {
    final files = _map(w['files']);
    final st = _map(w['stats']);
    final demo = _map(w['demo']);
    final prev = _s(files['preview.png']);
    final status = _s(w['status']);
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${_s(w['number'])} · ${_s(w['key'])}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5))),
          _tag(status),
        ]),
        Text('${_s(w['kind'])} · seed ${_s(w['seed'])} · ${_i(st['w'])} × ${_i(st['h'])} · ${_s(st['ms'])} ms',
            style: const TextStyle(color: C.muted, fontSize: 12)),
        if (prev.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(widget.app.api!.absolute(prev),
                    filterQuality: FilterQuality.none, errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_outlined))),
          ),
        _checks(_map(w['checks'])),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (status == 'draft')
            FilledButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gameWorldDo(_s(w['id']), 'approve'), 'Approved.'),
                child: const Text('OK, use it')),
          if (status == 'draft')
            OutlinedButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gameWorldDo(_s(w['id']), 'reject'), ''),
                child: const Text('No')),
          if (status != 'failed' && _s(demo['status']) != 'building')
            OutlinedButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gameWorldDo(_s(w['id']), 'demo'), 'Building the walk-it link.'),
                child: Text(_s(demo['play_url']).isEmpty ? 'Walk it in the browser' : 'Build the link again')),
          if (_s(demo['status']) == 'building') const Text('Building the walk-it link…', style: TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(demo['play_url']).isNotEmpty)
            FilledButton.tonal(
                onPressed: () => launchUrl(Uri.parse(widget.app.api!.absolute(_s(demo['play_url']))), mode: LaunchMode.externalApplication),
                child: const Text('Walk it')),
        ]),
        if (_s(demo['status']) == 'failed')
          Text('Walk-it link did not build: ${_strs(demo['errors']).join('; ')}', style: const TextStyle(color: C.bad, fontSize: 12)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hired = _d['hired'] == true;
    final worlds = _list(_d['worlds']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Worlds')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            const Text('Islands, dungeons, cities and platform levels made from rules and a seed (free). Each is made twice to prove '
                'the same seed gives the same world, and every village, room, exit and goal is checked reachable.',
                style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
            const SizedBox(height: 10),
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('New world', style: display(15.5)),
                  TextField(
                      controller: _words,
                      maxLines: 2,
                      maxLength: 600,
                      decoration: const InputDecoration(hintText: 'e.g. a big island with two rivers · a dungeon with 15 rooms')),
                  DropdownButton<String>(
                    value: _kind,
                    isExpanded: true,
                    items: [
                      const DropdownMenuItem(value: '', child: Text('Kind: from my words')),
                      for (final k in _strs(_d['kinds'])) DropdownMenuItem(value: k, child: Text(k)),
                    ],
                    onChanged: (v) => setState(() => _kind = v ?? ''),
                  ),
                  GradientButton(
                    label: hired ? 'Make the world' : 'Hire the Procedural World Engineer first',
                    icon: Icons.terrain_rounded,
                    height: 48,
                    onTap: _busy || !hired
                        ? null
                        : () {
                            if (_words.text.trim().isEmpty && _kind.isEmpty) {
                              _snack(context, 'Write your world in a line, or pick a kind.');
                              return;
                            }
                            _call(() => widget.app.api!.gameWorldNew({'words': _words.text.trim(), 'kind': _kind, 'studio': widget.studio}),
                                'Made and checked.');
                          },
                  ),
                  if (widget.studio.isNotEmpty && hired)
                    TextButton(
                        onPressed: _busy ? null : () => _call(() => widget.app.api!.gameWorldsApply(widget.studio), 'Rebuilding the game with the approved worlds.'),
                        child: const Text('Put approved worlds in the game')),
                ]),
              ),
              if (worlds.isEmpty) const Padding(padding: EdgeInsets.only(top: 16), child: Text('No worlds yet.', style: TextStyle(color: C.muted))),
              for (final w in worlds) _card(w),
            ],
          ]),
        ),
      ),
    );
  }
}

// ================================================================ Physics
class GamePhysicsScreen extends StatefulWidget {
  const GamePhysicsScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  State<GamePhysicsScreen> createState() => _GamePhysicsScreenState();
}

class _GamePhysicsScreenState extends State<GamePhysicsScreen> {
  Map<String, dynamic> _d = {};
  bool _loaded = false;
  bool _busy = false;
  final _speed = TextEditingController();
  final _wall = TextEditingController();
  final _ticks = TextEditingController();
  final _g = TextEditingController();
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in [_speed, _wall, _ticks, _g]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    _timer?.cancel();
    try {
      final d = await widget.app.api!.gamePhysics(widget.studio);
      if (!mounted) return;
      final df = _map(d['defaults']);
      setState(() {
        _d = d;
        if (!_loaded) {
          _speed.text = _s(df['speed']);
          _wall.text = _s(df['wall']);
          _ticks.text = _s(df['ticks']);
          _g.text = _s(df['gravity']);
        }
        _loaded = true;
      });
      if (_list(d['setups']).any((x) => _s(x['status']) == 'testing')) _timer = Timer(const Duration(seconds: 4), _load);
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

  String _show(dynamic v) => v is Map ? v.entries.map((e) => '${e.key}: ${e.value}').join(' · ') : _s(v);

  Widget _card(Map<String, dynamic> x) {
    final lab = _map(x['lab']);
    final st = _map(x['settings']);
    final inp = _map(x['inputs']);
    final status = _s(x['status']);
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(_s(x['number']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5))),
          if (_s(lab['verdict']).isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Text('${_s(lab['verdict'])} ${_s(lab['passed'])}/${_s(lab['total'])}',
                  style: TextStyle(color: _s(lab['verdict']) == 'PASS' ? C.ok : C.bad, fontWeight: FontWeight.w600, fontSize: 12)),
            ),
          _tag(status),
        ]),
        Text('${_s(inp['speed'])} px/s · ${_s(inp['wall'])} px wall · ${_s(inp['ticks'])} ticks · g ${_s(inp['gravity'])}',
            style: const TextStyle(color: C.muted, fontSize: 12)),
        const SizedBox(height: 4),
        Text('Settings: ${_s(st['ticks'])} ticks${st['ccd'] == true ? ' · continuous collision above ${_s(st['ccd_min_speed'])} px/s' : ''}. ${_s(st['why'])}',
            style: const TextStyle(fontSize: 12.5)),
        if (_s(_map(lab['before'])['say']).isNotEmpty) Text('Why: ${_s(_map(lab['before'])['say'])}', style: const TextStyle(fontSize: 12.5)),
        if (status == 'testing') const Text('The lab is running in Godot…', style: TextStyle(color: C.muted, fontSize: 12.5)),
        for (final c in _list(lab['cases']))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${c['ok'] == true ? '✓' : '✕'} ${_s(c['case'])}: ${_show(c['measured'])} (formula ${_show(c['expected'])})',
                  style: TextStyle(fontSize: 12.5, color: c['ok'] == true ? null : C.bad)),
              Text(_s(c['note']), style: const TextStyle(color: C.muted, fontSize: 11.5)),
            ]),
          ),
        if (_s(x['error']).isNotEmpty) Text(_s(x['error']), style: const TextStyle(color: C.bad, fontSize: 12)),
        if (status == 'draft')
          Wrap(spacing: 8, children: [
            FilledButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gamePhysicsDo(_s(x['id']), 'approve'), 'Approved.'),
                child: const Text('OK, use these settings')),
            OutlinedButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gamePhysicsDo(_s(x['id']), 'reject'), ''),
                child: const Text('No')),
          ]),
      ]),
    );
  }

  Widget _num(String label, TextEditingController c) => Expanded(
      child: TextField(controller: c, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: label)));

  @override
  Widget build(BuildContext context) {
    final hired = _d['hired'] == true;
    final setups = _list(_d['setups']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Physics')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            const Text('Hoola works out the settings from your numbers and proves them in Godot itself: falling, the range of a jump, a '
                'bounce, your fastest body against your thinnest wall, a box stack, a 3D drop, and the whole lab twice. '
                'Fluids are not part of this yet.',
                style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
            const SizedBox(height: 10),
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('New physics setup', style: display(15.5)),
                  Row(children: [_num('Fastest body px/s', _speed), const SizedBox(width: 10), _num('Thinnest wall px', _wall)]),
                  Row(children: [_num('Ticks / s', _ticks), const SizedBox(width: 10), _num('Gravity px/s²', _g)]),
                  const SizedBox(height: 10),
                  GradientButton(
                    label: hired ? 'Run the physics lab' : 'Hire the Physics Engine Developer first',
                    icon: Icons.science_rounded,
                    height: 48,
                    onTap: _busy || !hired
                        ? null
                        : () => _call(
                            () => widget.app.api!.gamePhysicsNew({
                                  'studio': widget.studio,
                                  'inputs': {
                                    'speed': double.tryParse(_speed.text) ?? 0,
                                    'wall': double.tryParse(_wall.text) ?? 0,
                                    'ticks': int.tryParse(_ticks.text) ?? 60,
                                    'gravity': double.tryParse(_g.text) ?? 980,
                                  },
                                }),
                            'The lab is running in Godot.'),
                  ),
                  if (widget.studio.isNotEmpty && hired)
                    TextButton(
                        onPressed: _busy ? null : () => _call(() => widget.app.api!.gamePhysicsApply(widget.studio), 'Rebuilding the game with the approved physics.'),
                        child: const Text('Put approved physics in the game')),
                ]),
              ),
              if (setups.isEmpty) const Padding(padding: EdgeInsets.only(top: 16), child: Text('No physics setups yet.', style: TextStyle(color: C.muted))),
              for (final x in setups) _card(x),
            ],
          ]),
        ),
      ),
    );
  }
}
