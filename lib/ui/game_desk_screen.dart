/// v0.370 GAME DESK (Employees > Game Developer > Open desk): original games from her words in Godot 4.
/// A short design doc first (her OK or her changes), then Hoola builds it, plays it itself (frames, taps, screenshots,
/// errors) and puts a private play link here. Same server as the web console: /api/game*.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _busyStates = {'designing', 'queued', 'writing', 'building', 'testing'};
const _label = {
  'designing': ('Writing the design', C.accentSoft), 'design_ready': ('Waiting for your OK', C.warn),
  'queued': ('Queued', C.accentSoft), 'writing': ('Writing code', C.accentSoft), 'building': ('Building', C.accentSoft),
  'testing': ('Playing it', C.accentSoft), 'done': ('Ready to play', C.ok), 'failed': ('Did not work', C.bad),
  'cancelled': ('Stopped', C.muted),
};

class GameDeskScreen extends StatefulWidget {
  const GameDeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<GameDeskScreen> createState() => _GameDeskScreenState();
}

class _GameDeskScreenState extends State<GameDeskScreen> {
  Map<String, dynamic> _d = {};
  bool _loaded = false;
  bool _busy = false;
  String _orientation = 'portrait';
  final _brief = TextEditingController();
  final Map<String, TextEditingController> _notes = {};
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _brief.dispose();
    for (final c in _notes.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _note(String id) => _notes.putIfAbsent(id, TextEditingController.new);

  Future<void> _load() async {
    _timer?.cancel();
    try {
      final d = await widget.app.api!.gameHome();
      if (!mounted) return;
      setState(() {
        _d = d;
        _loaded = true;
      });
      if (_list(d['games']).any((g) => _busyStates.contains(_s(g['status'])))) {
        _timer = Timer(const Duration(seconds: 4), _load);
      }
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

  Future<void> _open(String url) async {
    if (url.isEmpty) return;
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  Widget _newGame(bool ready) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('New game', style: display(16)),
          const SizedBox(height: 8),
          TextField(
            controller: _brief,
            minLines: 2,
            maxLines: 5,
            maxLength: 2000,
            decoration: const InputDecoration(hintText: 'Your idea in 2-3 lines: what the player does, how they win, who it is for'),
          ),
          Wrap(spacing: 8, children: [
            for (final o in const ['portrait', 'landscape', 'square'])
              ChoiceChip(
                label: Text(o[0].toUpperCase() + o.substring(1)),
                selected: _orientation == o,
                onSelected: (_) => setState(() => _orientation = o),
              ),
          ]),
          const SizedBox(height: 10),
          GradientButton(
            label: 'Write the design',
            icon: Icons.sports_esports_rounded,
            onTap: (_busy || !ready)
                ? null
                : () {
                    final b = _brief.text.trim();
                    if (b.length < 8) {
                      _snack(context, 'Write your idea in 2-3 lines first.');
                      return;
                    }
                    _call(() => widget.app.api!.gameNew(b, _orientation), 'Writing the design doc…').then((_) => _brief.clear());
                  },
          ),
          const SizedBox(height: 6),
          const Text('A short design doc comes first; nothing is built until you say OK. The play link stays private until you share it.',
              style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
        ]),
      );

  Widget _card(Map<String, dynamic> g) {
    final id = _s(g['id']);
    final st = _s(g['status']);
    final (text, color) = _label[st] ?? (st, C.muted);
    final busy = _busyStates.contains(st);
    final url = _s(g['play_url']);
    final nums = Map<String, dynamic>.from((g['numbers'] as Map?) ?? const {});
    final shots = ((g['shots'] as List?) ?? const []).map((e) => '$e').toList();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(g['number'])} · ${_s(g['title'])}', style: display(15.5))),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: color.withOpacity(.16), borderRadius: BorderRadius.circular(20)),
              child: Text(text, style: TextStyle(color: color, fontSize: 11.5, fontWeight: FontWeight.w600)),
            ),
          ]),
          if (busy) ...[
            const SizedBox(height: 10),
            LinearProgressIndicator(value: ((g['pct'] as num?) ?? 5) / 100, color: C.accent, backgroundColor: C.panel),
            const SizedBox(height: 6),
            Text(_s(g['stage']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ],
          if (_s(g['error']).isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(_s(g['error']), style: const TextStyle(color: C.bad, fontSize: 13)),
          ],
          if (st == 'design_ready') ...[
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
              child: SelectableText(_s(g['design']), style: const TextStyle(fontSize: 13.5, height: 1.45)),
            ),
            TextField(controller: _note(id), maxLines: 3, minLines: 1, decoration: const InputDecoration(hintText: 'Want changes? Write them, or just build it')),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              FilledButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.gameApprove(id), 'Building. Hoola plays it before it reaches you.'),
                  child: const Text('Build it')),
              OutlinedButton(
                  onPressed: _busy
                      ? null
                      : () {
                          final fb = _note(id).text.trim();
                          if (fb.isEmpty) {
                            _snack(context, 'Write what should change in the design.');
                            return;
                          }
                          _call(() => widget.app.api!.gameApprove(id, feedback: fb), 'Rewriting the design…').then((_) => _note(id).clear());
                        },
                  child: const Text('Change the design')),
            ]),
          ],
          if (url.isNotEmpty) ...[
            const SizedBox(height: 10),
            GradientButton(label: 'Play', icon: Icons.play_arrow_rounded, height: 48, onTap: () => _open(url)),
            const SizedBox(height: 6),
            const Text('Private: only people with this link can play. Share it when you are happy.',
                style: TextStyle(color: C.muted, fontSize: 12.5)),
            if (nums.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Wrap(spacing: 14, runSpacing: 4, children: [
                  if (nums['fps_server'] != null) Text('${nums['fps_server']} fps on the server', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (nums['load_s'] != null) Text('${nums['load_s']} s to start', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (nums['download_mb'] != null) Text('${nums['download_mb']} MB download', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
            if (_s(g['notes']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(g['notes']), style: const TextStyle(fontSize: 13))),
            if (shots.isNotEmpty)
              SizedBox(
                height: 170,
                child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.only(top: 10), children: [
                  for (final s in shots)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.network(s, fit: BoxFit.cover, errorBuilder: (_, __, ___) => const SizedBox(width: 90)),
                      ),
                    ),
                ]),
              ),
            TextField(controller: _note('c$id'), maxLines: 3, minLines: 1, decoration: const InputDecoration(hintText: 'What should change? e.g. faster, add a shield')),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              FilledButton(
                  onPressed: _busy
                      ? null
                      : () {
                          final w = _note('c$id').text.trim();
                          if (w.isEmpty) {
                            _snack(context, 'Write what should change first.');
                            return;
                          }
                          _call(() => widget.app.api!.gameChange(id, w), 'Making a new version. The current one keeps working.')
                              .then((_) => _note('c$id').clear());
                        },
                  child: const Text('Make a new version')),
              TextButton(onPressed: _busy ? null : () => _delete(id), child: const Text('Delete', style: TextStyle(color: C.bad))),
            ]),
            const Text('The whole Godot project downloads from the web console (Game Desk).', style: TextStyle(color: C.faint, fontSize: 12)),
          ],
          if (busy)
            Align(alignment: Alignment.centerLeft, child: TextButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.gameCancel(id), ''), child: const Text('Stop'))),
          if (!busy && url.isEmpty && st != 'design_ready')
            TextButton(onPressed: _busy ? null : () => _delete(id), child: const Text('Delete', style: TextStyle(color: C.bad))),
        ]),
      ),
    );
  }

  Future<void> _delete(String id) async {
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: const Text('Delete this game?'),
              content: const Text('The game and its play link go away.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
                TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Delete')),
              ],
            ));
    if (ok == true) await _call(() => widget.app.api!.gameDelete(id), 'Deleted.');
  }

  @override
  Widget build(BuildContext context) {
    final h = Map<String, dynamic>.from((_d['health'] as Map?) ?? const {});
    final ready = h['ready'] == true;
    final games = _list(_d['games']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Game Desk')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            Text(ready ? 'Original games from your words, built in Godot ${_s(h['version'])} and played by Hoola before you see them.'
                    : (_loaded ? 'Godot is not installed on the server yet.' : ''),
                style: TextStyle(color: ready ? C.muted : C.bad, fontSize: 13.5, height: 1.35)),
            const SizedBox(height: 12),
            if (!_loaded) const Center(child: CircularProgressIndicator()) else _newGame(ready),
            for (final g in games) _card(g),
          ]),
        ),
      ),
    );
  }
}
