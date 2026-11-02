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

// ================================================================ v0.421 Audio + Haptics (one shared page shape)
class _PackPage extends StatefulWidget {
  const _PackPage({required this.app, required this.studio, required this.base, required this.title, required this.intro,
      required this.listKey, required this.hireName});
  final Santosh app;
  final String studio;
  final String base;
  final String title;
  final String intro;
  final String listKey;
  final String hireName;
  @override
  State<_PackPage> createState() => _PackPageState();
}

class _PackPageState extends State<_PackPage> {
  Map<String, dynamic> _d = {};
  bool _loaded = false;
  bool _busy = false;
  final _words = TextEditingController();
  String _actuator = 'phone_lra';
  final Set<String> _zones = {'room', 'hall'};
  Timer? _timer;

  bool get _audio => widget.base == 'audio';
  bool get _haptics => widget.base == 'haptics';

  String _subtitle(Map<String, dynamic> x) {
    switch (widget.base) {
      case 'audio':
        return _list(_map(x['plan'])['zones']).map((z) => '${_s(z['key'])} ${_s(z['rt60'])} s').join(' · ');
      case 'haptics':
        return '${_s(x['actuator_name'])} · ${_map(x['patterns']).keys.join(', ')}';
      case 'net':
        final i = _map(x['inputs']);
        return '${_s(i['players'])} players · ${_s(i['tick'])} Hz · server on your own cloud';
      case 'sim':
        return '${_s(x['kind'])} · ${_s(_map(x['report'])['integrator'])}';
      case 'twin':
        final b = _map(_map(x['report'])['base']);
        return b.isEmpty ? 'read-only twin' : '${_s(b['per_day'])} parts / day · bottleneck ${_s(b['bottleneck'])} · read-only';
      case 'vfx':
        return '${_s(x['show'])} · ${_list(_map(x['plan'])['shots']).length} shots';
      default:
        final st = _map(x['settings']);
        return '${_s(st['mode']).toUpperCase()} · snap ${_s(st['snap_deg'])}° · ${_s(st['fps'])} fps';
    }
  }

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
      final d = await widget.app.api!.gamePack(widget.base, widget.studio);
      if (!mounted) return;
      setState(() {
        _d = d;
        _loaded = true;
      });
      if (_list(d[widget.listKey]).any((x) => _s(x['status']) == 'testing')) _timer = Timer(const Duration(seconds: 3), _load);
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

  Widget _card(Map<String, dynamic> x) {
    final rep = _map(x['report']);
    final files = _map(x['files']);
    final status = _s(x['status']);
    final checks = _list(rep['checks']);
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(_s(x['number']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5))),
          if (_s(rep['verdict']).isNotEmpty)
            Padding(
                padding: const EdgeInsets.only(right: 8),
                child: Text(_s(rep['verdict']),
                    style: TextStyle(color: _s(rep['verdict']) == 'PASS' ? C.ok : C.bad, fontWeight: FontWeight.w600, fontSize: 12))),
          _tag(status),
        ]),
        Text(_subtitle(x), style: const TextStyle(color: C.muted, fontSize: 12)),
        if (status == 'testing') const Text('Rendering and measuring…', style: TextStyle(color: C.muted, fontSize: 12.5)),
        for (final c in _list(rep['cases']))
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('${c['ok'] == true ? '✓' : '✕'} ${_s(c['case'])}: ${_s(c['measured'])} (expected ${_s(c['expected'])})',
                style: TextStyle(fontSize: 12, color: c['ok'] == true ? null : C.bad)),
          ),
        if (checks.isNotEmpty)
          for (final c in checks)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('${c['ok'] == true ? '✓' : '✕'} ${_s(c['check'])}: ${_s(c['note'])}',
                  style: TextStyle(fontSize: 12, color: c['ok'] == true ? null : C.bad)),
            )
        else
          _checks(rep),
        if (_s(rep['limits']).isNotEmpty) Text(_s(rep['limits']), style: const TextStyle(color: C.muted, fontSize: 11.5)),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 6, children: [
          for (final e in files.entries)
            OutlinedButton(
                onPressed: () => launchUrl(Uri.parse(widget.app.api!.absolute(_s(e.value))), mode: LaunchMode.externalApplication),
                child: Text(_audio ? 'Hear ${e.key.replaceAll('.wav', '')}' : (e.key == 'kit.zip' ? 'Download the kit' : 'Pattern shapes'))),
          if (_s(_map(x['demo'])['play_url']).isNotEmpty)
            FilledButton.tonal(
                onPressed: () => launchUrl(Uri.parse(widget.app.api!.absolute(_s(_map(x['demo'])['play_url']))), mode: LaunchMode.externalApplication),
                child: const Text('Open the demo room')),
          if (status == 'draft')
            FilledButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gamePackDo(widget.base, _s(x['id']), 'approve'), 'Approved.'),
                child: const Text('OK, use it')),
          if (status == 'draft')
            OutlinedButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.gamePackDo(widget.base, _s(x['id']), 'reject'), ''),
                child: const Text('No')),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hired = _d['hired'] == true;
    final items = _list(_d[widget.listKey]);
    final presets = _map(_d['zone_presets']);
    final acts = _map(_d['actuators']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.title)),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            Text(widget.intro, style: const TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
            const SizedBox(height: 10),
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_audio ? 'New audio setup' : 'New pattern set', style: display(15.5)),
                  if (_audio)
                    Wrap(spacing: 6, children: [
                      for (final k in presets.keys)
                        FilterChip(
                            label: Text('${k.replaceAll('_', ' ')} ${_s(presets[k])} s'),
                            selected: _zones.contains(k),
                            onSelected: (v) => setState(() => v ? _zones.add(k) : _zones.remove(k))),
                    ])
                  else ...[
                    TextField(
                        controller: _words,
                        maxLines: 2,
                        maxLength: 600,
                        decoration: InputDecoration(
                            hintText: _haptics
                                ? 'The moments that should buzz: jump, coin, hit, game over'
                                : widget.base == 'net'
                                    ? 'e.g. 16 players, 240 px/s, 30 tick'
                                    : widget.base == 'sim'
                                        ? 'e.g. a satellite in an 800 km orbit, or a car on a curve'
                                        : widget.base == 'twin'
                                            ? 'Your line in a few words (the worked example runs if empty)'
                                            : widget.base == 'vfx'
                                                ? 'Your show in a few words (the worked example runs if empty)'
                                                : 'e.g. VR for Quest, seated, or AR on a phone')),
                    if (_haptics)
                    DropdownButton<String>(
                      value: acts.containsKey(_actuator) ? _actuator : (acts.keys.isEmpty ? null : acts.keys.first),
                      isExpanded: true,
                      items: [for (final k in acts.keys) DropdownMenuItem(value: k, child: Text(_s(_map(acts[k])['name'])))],
                      onChanged: (v) => setState(() => _actuator = v ?? 'phone_lra'),
                    ),
                  ],
                  const SizedBox(height: 8),
                  GradientButton(
                    label: hired
                        ? (_audio
                            ? 'Render and measure'
                            : _haptics
                                ? 'Make and check'
                                : widget.base == 'net'
                                    ? 'Run the bots'
                                    : widget.base == 'xr'
                                        ? 'Check and build the demo room'
                                        : 'Check it')
                        : 'Hire the ${widget.hireName} first',
                    icon: _audio ? Icons.surround_sound_rounded : Icons.vibration_rounded,
                    height: 48,
                    onTap: _busy || !hired || (_audio && _zones.isEmpty)
                        ? null
                        : () => _call(
                            () => widget.app.api!.gamePackNew(
                                widget.base,
                                _audio
                                    ? {
                                        'studio': widget.studio,
                                        'plan': {
                                          'zones': [for (final k in _zones) {'key': k, 'rt60': presets[k]}]
                                        }
                                      }
                                    : {'studio': widget.studio, 'words': _words.text.trim(), if (_haptics) 'actuator': _actuator}),
                            _audio ? 'Rendering and measuring.' : 'Made and checked.'),
                  ),
                  if (widget.studio.isNotEmpty && hired && !const ['net', 'twin', 'vfx'].contains(widget.base))
                    TextButton(
                        onPressed: _busy
                            ? null
                            : () => _call(() => widget.app.api!.gamePackApply(widget.base, widget.studio), 'Rebuilding the game.'),
                        child: const Text('Put the approved setup in the game')),
                ]),
              ),
              if (items.isEmpty) const Padding(padding: EdgeInsets.only(top: 16), child: Text('Nothing yet.', style: TextStyle(color: C.muted))),
              for (final x in items) _card(x),
            ],
          ]),
        ),
      ),
    );
  }
}

class GameAudioScreen extends StatelessWidget {
  const GameAudioScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  Widget build(BuildContext context) => _PackPage(
      app: app,
      studio: studio,
      base: 'audio',
      title: 'Audio',
      listKey: 'setups',
      hireName: 'Spatial Audio Programmer',
      intro: 'Reverb zones, distance and walls for your game, with headphone demos. Every number is measured. A round-head '
          'model gives no front / back or height cue.');
}

class GameHapticsScreen extends StatelessWidget {
  const GameHapticsScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  Widget build(BuildContext context) => _PackPage(
      app: app,
      studio: studio,
      base: 'haptics',
      title: 'Haptics',
      listKey: 'sets',
      hireName: 'Haptic Feedback Engineer',
      intro: 'One vibration pattern per moment, checked for the motor, with battery per play and an off switch for every '
          'player. iPhone browsers have no vibration.');
}

class GameNetScreen extends StatelessWidget {
  const GameNetScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  Widget build(BuildContext context) => _PackPage(
      app: app,
      studio: studio,
      base: 'net',
      title: 'Multiplayer',
      listKey: 'setups',
      hireName: 'Network Programmer',
      intro: 'Bots play over a good, a 150 ms / 2 % loss and a bad mobile network: rubber-banding, desync (must be 0), bandwidth '
          'and lag compensation are measured. The game server runs on your own cloud; Hoola hosts none.');
}

class GameXrScreen extends StatelessWidget {
  const GameXrScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  Widget build(BuildContext context) => _PackPage(
      app: app,
      studio: studio,
      base: 'xr',
      title: 'VR / AR',
      listKey: 'setups',
      hireName: 'AR / VR Engineer',
      intro: 'A WebXR room for your headset or phone browser with comfort rules checked and hand gestures scored on a test set '
          'of synthetic hands. Frame rate on your headset is not measured here.');
}

class GameSimScreen extends StatelessWidget {
  const GameSimScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  Widget build(BuildContext context) => _PackPage(
      app: app, studio: studio, base: 'sim', title: 'Simulators', listKey: 'setups', hireName: 'Simulation Engineer',
      intro: 'Orbit, light-aircraft and car models, each checked against its textbook answer, sources cited, every scenario run twice. A training aid, not a certified device.');
}

class GameTwinScreen extends StatelessWidget {
  const GameTwinScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  Widget build(BuildContext context) => _PackPage(
      app: app, studio: studio, base: 'twin', title: 'Digital twin', listKey: 'setups', hireName: 'Twin Architect',
      intro: 'Your line simulated with what-ifs. Every number traces to your data or a stated assumption; it reads and never controls your plant.');
}

class GameVfxScreen extends StatelessWidget {
  const GameVfxScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  Widget build(BuildContext context) => _PackPage(
      app: app, studio: studio, base: 'vfx', title: 'VFX pipeline', listKey: 'setups', hireName: 'Pipeline TD',
      intro: 'Naming and versions, ACES colour measured, an EXR test frame, a render queue with cost per shot. Blender is not run on Hoolas server.');
}

// ================================================================ v0.425 Hoola Runtime (replay tests + opt-in telemetry)
class GameRuntimeScreen extends StatefulWidget {
  const GameRuntimeScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  State<GameRuntimeScreen> createState() => _GameRuntimeScreenState();
}

class _GameRuntimeScreenState extends State<GameRuntimeScreen> {
  Map<String, dynamic> _rt = {};
  Map<String, dynamic> _tel = {};
  bool _loaded = false;
  bool _busy = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    _timer?.cancel();
    try {
      final rt = await widget.app.api!.gameRuntime(widget.studio);
      Map<String, dynamic> tel = {};
      try {
        tel = await widget.app.api!.gameTelemetry(widget.studio);
      } catch (_) {}
      if (!mounted) return;
      setState(() {
        _rt = rt;
        _tel = tel;
        _loaded = true;
      });
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

  String _pct(dynamic v) => v is num ? '${(v * 100).round()}%' : '-';

  @override
  Widget build(BuildContext context) {
    final tests = _list(_rt['tests']);
    final last = tests.isEmpty ? <String, dynamic>{} : tests.last;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Runtime')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            const Text('HoolaRuntime goes into every build: a replay recorder and a test bot (used only when Hoola tests the game) '
                'and opt-in telemetry - each player is asked first. Editor tokens and the Godot plugin: web console.',
                style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
            const SizedBox(height: 10),
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Hoola Runtime (replay tests)'),
                      value: _rt['on'] == true,
                      onChanged: _busy ? null : (v) => _call(() => widget.app.api!.gameRuntimeSet(widget.studio, {'on': v}), 'Saved.')),
                  SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Telemetry (players asked first)'),
                      subtitle: _rt['kids'] == true ? const Text('Not for a children\'s game') : null,
                      value: _rt['telemetry'] == true,
                      onChanged: _busy || _rt['kids'] == true
                          ? null
                          : (v) => _call(() => widget.app.api!.gameRuntimeSet(widget.studio, {'telemetry': v}), 'Saved.')),
                  GradientButton(
                      label: 'Run a replay test',
                      icon: Icons.replay_rounded,
                      height: 48,
                      onTap: _busy
                          ? null
                          : () {
                              _call(() => widget.app.api!.gameReplayTest(widget.studio), 'The bot is playing; pull down in half a minute.');
                              _timer = Timer(const Duration(seconds: 30), _load);
                            }),
                ]),
              ),
              if (last.isNotEmpty)
                Container(
                  margin: const EdgeInsets.only(top: 10),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Last test: v${_s(last['version'])} · ${_s(last['verdict'])}',
                        style: TextStyle(fontWeight: FontWeight.w600, color: _s(last['verdict']) == 'PASS' ? C.ok : C.bad)),
                    Text('${_s(last['frames'])} frames · ${_s(last['inputs'])} bot inputs', style: const TextStyle(color: C.muted, fontSize: 12)),
                    for (final c in _list(last['checks']))
                      Text('${c['ok'] == true ? '✓' : '✕'} ${_s(c['check'])}: ${_s(c['note'])}',
                          style: TextStyle(fontSize: 12, color: c['ok'] == true ? null : C.bad)),
                  ]),
                ),
              if (_tel.isNotEmpty && _rt['telemetry'] == true)
                Container(
                  margin: const EdgeInsets.only(top: 10),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Telemetry', style: display(15)),
                    Text('${_s(_tel['installs'])} players · ${_s(_tel['events'])} events · next day ${_pct(_map(_tel['d1'])['share'])} · '
                        'day 7 ${_pct(_map(_tel['d7'])['share'])}'),
                    for (final f in _list(_tel['funnel'])) Text('${_s(f['step'])}: ${_s(f['players'])}', style: const TextStyle(fontSize: 12)),
                    Text(_s(_tel['privacy']), style: const TextStyle(color: C.muted, fontSize: 11.5)),
                  ]),
                ),
            ],
          ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- v0.428 Live ops
class GameLiveopsScreen extends StatefulWidget {
  const GameLiveopsScreen({super.key, required this.app, required this.studio});
  final Santosh app;
  final String studio;
  @override
  State<GameLiveopsScreen> createState() => _GameLiveopsScreenState();
}

class _GameLiveopsScreenState extends State<GameLiveopsScreen> {
  Map<String, dynamic> _v = {};
  Map<String, dynamic> _dash = {};
  Map<String, dynamic> _cr = {};
  Map<String, dynamic> _money = {};
  final Map<String, Map<String, dynamic>> _res = {};
  bool _loaded = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = widget.app.api!;
    try {
      final v = await api.gameLiveops(widget.studio);
      final dash = await api.gameLiveops(widget.studio, '/dashboard');
      final cr = await api.gameLiveops(widget.studio, '/crashes');
      final money = await api.gameLiveops(widget.studio, '/money');
      final res = <String, Map<String, dynamic>>{};
      for (final x in _list(v['experiments'])) {
        if (_s(x['status']) == 'draft') continue;
        try {
          res[_s(x['key'])] = await api.gameLiveops(widget.studio, '/experiments/${Uri.encodeComponent(_s(x['key']))}');
        } catch (_) {}
      }
      if (!mounted) return;
      setState(() {
        _v = v;
        _dash = dash;
        _cr = cr;
        _money = money;
        _res
          ..clear()
          ..addAll(res);
        _loaded = true;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _loaded = true);
        _snack(context, '$e');
      }
    }
  }

  Future<void> _do(String part, String ok, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.gameLiveopsDo(widget.studio, part, body);
      if (mounted) _snack(context, ok);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Future<void> _sure(String q, String part, String ok, [Map<String, dynamic>? body]) async {
    final yes = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(content: Text(q), actions: [
              TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
              TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes')),
            ]));
    if (yes == true) await _do(part, ok, body);
  }

  String _pct(dynamic v) => v is num ? '${(v * 1000).round() / 10}%' : '-';

  Widget _box(List<Widget> kids) => Container(
        margin: const EdgeInsets.only(top: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: kids),
      );

  @override
  Widget build(BuildContext context) {
    final patches = _list(_v['patches']);
    final last = patches.isEmpty ? <String, dynamic>{} : patches.last;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Live ops')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            const Text('A/B tests, live events, crashes and patches for the shipped game. New tests and events: web console or chat; '
                'nothing reaches players before your tap.',
                style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
            if (!_loaded)
              const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()))
            else ...[
              if (_v['telemetry'] != true)
                _box([const Text('Telemetry is off, so results and crashes stay empty. Switch it on in Runtime (players are asked first).',
                    style: TextStyle(color: C.bad, fontSize: 12.5))]),
              _box([
                Text('Players', style: display(15)),
                Text('${_s(_dash['installs'])} players · D1 ${_pct(_map(_dash['d1'])['share'])} · D7 ${_pct(_map(_dash['d7'])['share'])} · '
                    'D30 ${_pct(_map(_dash['d30'])['share'])}'),
                for (final b in _list(_dash['balance']))
                  Text('${_s(b['event'])}: median ${_s(b['median'])}, outliers ${_pct(b['outlier_share'])}${b['flag'] == true ? ' - check balance' : ''}',
                      style: TextStyle(fontSize: 12, color: b['flag'] == true ? C.bad : null)),
                for (final x in _list(_dash['stuck_levels']))
                  Text('Difficulty spike: level ${_s(x['level'])} (${_s(x['x_median'])}x the median game-overs)',
                      style: const TextStyle(fontSize: 12, color: C.bad)),
              ]),
              _box([
                Text('A/B tests', style: display(15)),
                if (_list(_v['experiments']).isEmpty) const Text('No A/B test yet.', style: TextStyle(color: C.muted, fontSize: 12.5)),
                for (final x in _list(_v['experiments'])) ...[
                  const SizedBox(height: 6),
                  Text('${_s(x['title'])} · ${_s(x['status'])}', style: const TextStyle(fontWeight: FontWeight.w600)),
                  if (_res[_s(x['key'])] != null) ...[
                    Text(_s(_res[_s(x['key'])]!['verdict']), style: const TextStyle(fontWeight: FontWeight.w600)),
                    Text(_s(_res[_s(x['key'])]!['note']), style: const TextStyle(fontSize: 12, color: C.muted)),
                    for (final g in _list(_res[_s(x['key'])]!['groups']))
                      Text('${_s(g['name'])}: ${_s(g['players'])} / ${_s(_res[_s(x['key'])]!['need_per_group'])} players, goal ${_pct(g['rate'])}',
                          style: const TextStyle(fontSize: 12)),
                  ],
                  Wrap(spacing: 8, children: [
                    if (_s(x['status']) == 'draft')
                      TextButton(
                          onPressed: _busy
                              ? null
                              : () => _sure('Start this A/B test?', '/experiments/${Uri.encodeComponent(_s(x['key']))}/start', 'Test started.'),
                          child: const Text('Start')),
                    if (_s(x['status']) == 'running')
                      for (final g in _list(x['variants']))
                        TextButton(
                            onPressed: _busy
                                ? null
                                : () => _sure('Stop the test and keep ${_s(g['name'])}?', '/experiments/${Uri.encodeComponent(_s(x['key']))}/stop',
                                    'Stopped.', {'ship': _s(g['name'])}),
                            child: Text('Keep ${_s(g['name'])}')),
                  ]),
                ],
              ]),
              _box([
                Text('Live events', style: display(15)),
                if (_list(_v['events']).isEmpty) const Text('No event yet.', style: TextStyle(color: C.muted, fontSize: 12.5)),
                for (final e in _list(_v['events']))
                  Row(children: [
                    Expanded(
                        child: Text('${_s(e['title'])} · ${_s(e['state'])}\n${_s(e['starts_ist'])} → ${_s(e['ends_ist'])}',
                            style: const TextStyle(fontSize: 12.5))),
                    if (_s(e['status']) == 'draft')
                      TextButton(
                          onPressed: _busy
                              ? null
                              : () => _sure('Approve "${_s(e['title'])}"? Players get it at its start time.',
                                  '/events/${Uri.encodeComponent(_s(e['key']))}/approve', 'Approved.'),
                          child: const Text('Approve')),
                    if (_s(e['status']) == 'scheduled' && _s(e['state']) != 'ended')
                      TextButton(
                          onPressed: _busy ? null : () => _do('/events/${Uri.encodeComponent(_s(e['key']))}/cancel', 'Cancelled.'),
                          child: const Text('Cancel')),
                  ]),
              ]),
              _box([
                Text('Crashes', style: display(15)),
                for (final c in _list(_cr['crash_free']))
                  Text('v${_s(c['version'])}: ${_pct(c['crash_free'])} crash-free (${_s(c['players'])} players)', style: const TextStyle(fontSize: 12)),
                if (_list(_cr['groups']).isEmpty) const Text('No crash reported.', style: TextStyle(color: C.muted, fontSize: 12.5)),
                for (final c in _list(_cr['groups']))
                  Row(children: [
                    Expanded(
                        child: Text('${_s(c['msg'])}\n${_s(c['where'])} · ${_s(c['players'])} players · ${_s(c['state'])}',
                            style: const TextStyle(fontSize: 12))),
                    if (_s(c['task']).isEmpty)
                      TextButton(
                          onPressed: _busy ? null : () => _do('/crashes/${Uri.encodeComponent(_s(c['sig']))}/hotfix', 'Hotfix task is on the board.'),
                          child: const Text('Hotfix'))
                    else
                      Text(_s(c['task']), style: const TextStyle(color: C.muted)),
                  ]),
              ]),
              _box([
                Text('Patch check', style: display(15)),
                const Text('Saved replays + a bot run on the newest version, in the real Godot.', style: TextStyle(color: C.muted, fontSize: 12)),
                if (last.isNotEmpty) ...[
                  Text('v${_s(last['version'])} · ${_s(last['verdict'])}',
                      style: TextStyle(fontWeight: FontWeight.w600, color: _s(last['verdict']) == 'PASS' ? C.ok : C.bad)),
                  for (final c in _list(last['checks']))
                    Text('${c['ok'] == true ? '✓' : '✕'} ${_s(c['check'])}: ${_s(c['note'])}', style: const TextStyle(fontSize: 12)),
                ],
                TextButton(onPressed: _busy ? null : () => _do('/patch_check', 'Running; pull down in a minute.'), child: const Text('Check the newest version')),
              ]),
              _box([
                Text('Money', style: display(15)),
                Text('Last 30 days ₹${_s(_money['revenue_30d_inr'])} · ARPDAU ${_money['arpdau_inr'] == null ? '-' : '₹${_s(_money['arpdau_inr'])}'} (upper bound)'),
                for (final n in _strs(_money['notes']))
                  Text(n, style: const TextStyle(color: C.muted, fontSize: 11.5)),
              ]),
            ],
          ]),
        ),
      ),
    );
  }
}
