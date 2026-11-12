/// v0.395 GAME BIBLE (Studio project > Game Bible): the game's names and numbers as data - checks, Hoola's drafts
/// waiting for her OK, a seeded balance simulation, and "Put it in the game" (a rebuild with no new code).
/// Detailed editing lives in the web console; here she reads, approves, generates, removes and applies.
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
double _d(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _cols = {
  'character': ['role'],
  'enemy': ['tier', 'hp', 'damage', 'behaviour'],
  'item': ['tier', 'effect', 'price'],
  'level': ['order', 'duration_s', 'reward_coins'],
  'quest': ['goal', 'count'],
  'screen': ['purpose'],
};

Color _hex(String h) {
  final v = int.tryParse(h.replaceFirst('#', ''), radix: 16);
  return v == null || h.length != 7 ? Colors.transparent : Color(0xFF000000 | v);
}

class GameBibleScreen extends StatefulWidget {
  const GameBibleScreen({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<GameBibleScreen> createState() => _GameBibleScreenState();
}

class _GameBibleScreenState extends State<GameBibleScreen> {
  Map<String, dynamic> _v = {};
  Map<String, dynamic> _sim = {};
  bool _loaded = false;
  bool _busy = false;
  final Map<String, TextEditingController> _words = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _words.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _w(String k) => _words.putIfAbsent(k, TextEditingController.new);

  Future<void> _load() async {
    try {
      final v = await widget.app.api!.gameBible(widget.id);
      if (mounted) {
        setState(() {
          _v = v;
          _loaded = true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loaded = true);
        _snack(context, '$e');
      }
    }
  }

  Future<void> _do(String what, {Map<String, dynamic> body = const {}, String ok = ''}) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.gameBibleDo(widget.id, what, body: body);
      if (what == 'simulate' && mounted) setState(() => _sim = r);
      if (mounted && ok.isNotEmpty) _snack(context, ok);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Widget _checks() {
    final c = Map<String, dynamic>.from((_v['check'] as Map?) ?? const {});
    final errs = _strs(c['errors']);
    final warns = _strs(c['warnings']);
    if (errs.isEmpty && warns.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (errs.isNotEmpty) Text('Fix first', style: display(14.5, color: C.bad)),
          for (final e in errs) Text('• $e', style: const TextStyle(color: C.bad, fontSize: 13)),
          if (warns.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text('Worth a look', style: display(14.5))),
          for (final w in warns) Text('• $w', style: const TextStyle(color: C.muted, fontSize: 13)),
        ]),
      ),
    );
  }

  Widget _draft() {
    final d = Map<String, dynamic>.from((_v['draft'] as Map?) ?? const {});
    if (d.isEmpty) return const SizedBox.shrink();
    final add = _list(d['add']);
    final cols = _cols[_s(d['kind'])] ?? const <String>[];
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Draft from Hoola, waiting for your OK', style: display(15)),
          const SizedBox(height: 6),
          if (_s(d['kind']) == 'seed') const Text('A first Bible from the design doc.', style: TextStyle(fontSize: 13.5)),
          for (final e in add)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('${_s(e['name'])}  ·  ${cols.map((c) => '$c ${_s(e[c])}').join(' · ')}', style: const TextStyle(fontSize: 13.5)),
            ),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            FilledButton(onPressed: _busy ? null : () => _do('accept', ok: 'Added to the Bible.'), child: const Text('OK, add')),
            OutlinedButton(onPressed: _busy ? null : () => _do('reject'), child: const Text('No')),
          ]),
        ]),
      ),
    );
  }

  Widget _simBox() {
    if (_sim.isEmpty) return const SizedBox.shrink();
    final levels = _list(_sim['levels']);
    final flags = _strs(_sim['flags']);
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Balance (${_i(_sim['runs'])} plays a level)', style: display(15)),
          const Text('The same Bible always gives the same numbers.', style: TextStyle(color: C.muted, fontSize: 12.5)),
          if (_sim['ok'] != true) Text(_strs(_sim['errors']).join('; '), style: const TextStyle(color: C.bad, fontSize: 13)),
          for (final r in levels)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text(_s(r['name']), style: const TextStyle(fontSize: 13.5))),
                  Text('${(_d(r['win_rate']) * 100).round()}% win', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                ]),
                const SizedBox(height: 4),
                LinearProgressIndicator(value: _d(r['win_rate']).clamp(0, 1).toDouble(), color: C.accent, backgroundColor: C.panel),
              ]),
            ),
          if (flags.isNotEmpty) const SizedBox(height: 8),
          for (final f in flags) Text('• $f', style: const TextStyle(fontSize: 13)),
          if (_sim['ok'] == true && flags.isEmpty) const Text('No balance problems found.', style: TextStyle(fontSize: 13)),
        ]),
      ),
    );
  }

  Widget _kind(String k, Map<String, dynamic> tpl) {
    final rows = _list(((_v['data'] as Map?)?['entities'] as Map?)?[k]);
    final cols = _cols[k] ?? const <String>[];
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_s(tpl['label'])}s  ${rows.length}', style: display(15)),
          for (final e in rows)
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              leading: _s(e['color']).isNotEmpty
                  ? Container(width: 18, height: 18, decoration: BoxDecoration(color: _hex(_s(e['color'])), borderRadius: BorderRadius.circular(5)))
                  : null,
              title: Text(_s(e['name'])),
              subtitle: Text(cols.map((c) => '$c ${_s(e[c])}').join(' · ')),
              trailing: IconButton(
                tooltip: 'Remove',
                icon: const Icon(Icons.delete_outline_rounded),
                onPressed: _busy
                    ? null
                    : () async {
                        final ok = await showDialog<bool>(
                            context: context,
                            builder: (d) => AlertDialog(
                                  title: Text('Remove ${_s(e['name'])}?'),
                                  actions: [
                                    TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                                    TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Remove')),
                                  ],
                                ));
                        if (ok != true) return;
                        setState(() => _busy = true);
                        try {
                          await widget.app.api!.gameBibleRemove(widget.id, k, _s(e['id']));
                        } catch (err) {
                          if (mounted) _snack(context, '$err');
                        }
                        if (mounted) setState(() => _busy = false);
                        await _load();
                      },
              ),
            ),
          TextField(controller: _w(k), decoration: const InputDecoration(hintText: 'Generate, e.g. 3 night enemies')),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
                onPressed: _busy
                    ? null
                    : () {
                        final words = _w(k).text.trim();
                        final m = RegExp(r'\b(\d{1,2})\b').firstMatch(words);
                        _do('generate',
                            body: {'kind': k, 'n': m == null ? 3 : int.parse(m.group(1)!), 'words': words},
                            ok: 'A draft is ready for your OK.');
                      },
                child: const Text('Generate')),
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final version = _i(_v['version']);
    final applied = _i(_v['applied']);
    final pal = _strs(((_v['data'] as Map?)?['style'] as Map?)?['palette']);
    final tpls = Map<String, dynamic>.from((_v['templates'] as Map?) ?? const {});
    return DeskPage(
      title: 'Game Bible',
      onRefresh: _load,
      body: () => RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              Text('v$version · in the game: v$applied. The game reads its names and numbers from here.',
                  style: const TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (version > applied)
                  FilledButton(
                      onPressed: _busy ? null : () => _do('apply', ok: 'Rebuilding the game with the Bible (no new code).'),
                      child: const Text('Put it in the game')),
                OutlinedButton(onPressed: _busy ? null : () => _do('simulate'), child: const Text('Simulate balance')),
                if (version == 0 && (_v['draft'] as Map?)?.isEmpty != false)
                  OutlinedButton(
                      onPressed: _busy ? null : () => _do('seed', ok: 'A draft Bible is ready for your OK.'),
                      child: const Text('First Bible from the design')),
              ]),
              if (pal.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Wrap(spacing: 6, children: [
                    for (final c in pal)
                      Container(width: 26, height: 26, decoration: BoxDecoration(color: _hex(c), borderRadius: BorderRadius.circular(7))),
                  ]),
                ),
              _checks(),
              _draft(),
              _simBox(),
              for (final k in tpls.keys) _kind(k, Map<String, dynamic>.from(tpls[k] as Map)),
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text('Edit entries, the palette, the player and the curves in the web console (Game Desk > board > Game Bible).',
                    style: TextStyle(color: C.faint, fontSize: 12)),
              ),
            ],
          ]),
        ),
    );
  }
}
