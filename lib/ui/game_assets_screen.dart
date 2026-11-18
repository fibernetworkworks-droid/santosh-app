/// v0.416 ASSETS (Studio project > Assets): the game's art, sounds, music, voice and 3D models. Pictures, music and
/// voice cost money: they wait on a price card until she taps "Make" here. Every file is checked by the server and
/// enters the game only after her OK. Detailed making (presets, palette lock, uploads) also lives in the web console.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _status = {
  'priced': ('Waiting for your tap', C.warn),
  'making': ('Being made', C.accentSoft),
  'draft': ('Waiting for your OK', C.warn),
  'approved': ('In the game', C.ok),
  'rejected': ('Not used', C.muted),
  'failed': ('Failed its checks', C.bad),
};
const _images = {'sprite', 'icon', 'ui', 'background'};
const _sounds = {'sfx', 'music', 'voice'};

class GameAssetsScreen extends StatefulWidget {
  const GameAssetsScreen({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<GameAssetsScreen> createState() => _GameAssetsScreenState();
}

class _GameAssetsScreenState extends State<GameAssetsScreen> {
  Map<String, dynamic> _v = {};
  List<Map<String, dynamic>> _sug = [];
  final Set<String> _picked = {};
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
      final v = await widget.app.api!.gameAssets(widget.id);
      if (!mounted) return;
      setState(() {
        _v = v;
        _loaded = true;
        _picked
          ..clear()
          ..addAll(_list((v['card'] as Map?)?['items']).map((e) => _s(e['id'])));
      });
      if (_list(v['assets']).any((a) => _s(a['status']) == 'making')) _timer = Timer(const Duration(seconds: 5), _load);
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

  Widget _card() {
    final card = Map<String, dynamic>.from((_v['card'] as Map?) ?? const {});
    final items = _list(card['items']);
    if (items.isEmpty) return const SizedBox.shrink();
    final total = items.where((i) => _picked.contains(_s(i['id']))).fold<num>(0, (a, i) => a + ((i['cost_inr'] as num?) ?? 0));
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Price card', style: display(15.5)),
          const Text('Nothing is spent until you tap Make.', style: TextStyle(color: C.muted, fontSize: 12.5)),
          for (final i in items)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              value: _picked.contains(_s(i['id'])),
              onChanged: (v) => setState(() => v == true ? _picked.add(_s(i['id'])) : _picked.remove(_s(i['id']))),
              title: Text('${_s(i['key'])} · ${_s(i['kind'])}'),
              subtitle: Text('about Rs ${_s(i['cost_inr'])}'),
            ),
          GradientButton(
            label: 'Make for about Rs ${total.toStringAsFixed(0)}',
            icon: Icons.auto_awesome_rounded,
            height: 48,
            onTap: _busy || _picked.isEmpty
                ? null
                : () => _call(() => widget.app.api!.gameAssetsSpend(widget.id, _picked.toList()), 'Making them. Each waits for your OK.'),
          ),
        ]),
      ),
    );
  }

  Widget _tile(Map<String, dynamic> a) {
    final (text, color) = _status[_s(a['status'])] ?? (_s(a['status']), C.muted);
    final url = _s(a['url']);
    final kind = _s(a['kind']);
    final meta = Map<String, dynamic>.from((a['meta'] as Map?) ?? const {});
    final checks = Map<String, dynamic>.from((a['checks'] as Map?) ?? const {});
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
          width: 72,
          height: 72,
          child: url.isEmpty
              ? const Icon(Icons.hourglass_empty_rounded, color: C.muted)
              : _images.contains(kind)
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.network(widget.app.api!.absolute(url), fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_outlined)))
                  : IconButton(
                      tooltip: 'Play / open',
                      icon: Icon(_sounds.contains(kind) ? Icons.play_circle_outline_rounded : Icons.view_in_ar_rounded, size: 36),
                      onPressed: () => launchUrl(Uri.parse(widget.app.api!.absolute(url)), mode: LaunchMode.externalApplication),
                    ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(_s(a['key']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14))),
              Text(text, style: TextStyle(color: color, fontSize: 11.5, fontWeight: FontWeight.w600)),
            ]),
            Text('${_s(a['label'])} · v${_i(a['version'])}${_i(a['approved']) > 0 ? ' · in game v${_i(a['approved'])}' : ''}'
                '${meta['w'] != null ? ' · ${meta['w']}×${meta['h']}' : ''}${meta['seconds'] != null ? ' · ${meta['seconds']} s' : ''}'
                '${meta['palette_share'] != null ? ' · palette ${((meta['palette_share'] as num) * 100).round()}%' : ''}',
                style: const TextStyle(color: C.muted, fontSize: 12)),
            for (final e in _strs(checks['errors'])) Text(e, style: const TextStyle(color: C.bad, fontSize: 12.5)),
            for (final w in _strs(checks['warnings'])) Text(w, style: const TextStyle(color: C.muted, fontSize: 12)),
            if (_s(a['status']) == 'draft')
              Wrap(spacing: 8, children: [
                FilledButton(
                    onPressed: _busy ? null : () => _call(() => widget.app.api!.gameAssetsDo(widget.id, _s(a['key']), 'approve'), 'In the game at the next build.'),
                    child: const Text('OK, use it')),
                OutlinedButton(
                    onPressed: _busy ? null : () => _call(() => widget.app.api!.gameAssetsDo(widget.id, _s(a['key']), 'reject'), ''),
                    child: const Text('No')),
              ]),
          ]),
        ),
      ]),
    );
  }

  Widget _suggestions() {
    if (_sug.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('The game still needs', style: display(15)),
          for (final x in _sug)
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text('${_s(x['key'])} · ${_s(x['kind'])}'),
              subtitle: Text(_s(x['words'])),
              trailing: TextButton(
                onPressed: _busy
                    ? null
                    : () => _call(
                        () => widget.app.api!.gameAssetsNew(widget.id, {
                              'kind': x['kind'],
                              'key': x['key'],
                              'words': x['words'],
                              if (x['preset'] != null) 'preset': x['preset'],
                            }),
                        _i(x['cost_inr']) > 0 ? 'Added to the price card.' : 'Making it.'),
                child: Text(_i(x['cost_inr']) > 0 ? 'Price it' : 'Make it'),
              ),
            ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = _list(_v['assets']);
    return DeskPage(
      title: 'Assets',
      onRefresh: _load,
      body: () => RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              Text('${_i(_v['in_game'])} in the game · Rs ${_s(_v['spent_inr'])} spent. Art follows the Game Bible palette; '
                  'sounds are made in code for free.', style: const TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                FilledButton(
                    onPressed: _busy ? null : () => _call(() => widget.app.api!.gameAssetsApply(widget.id), 'Rebuilding the game with the approved assets.'),
                    child: const Text('Put approved assets in the game')),
                OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () async {
                            try {
                              final r = await widget.app.api!.gameAssetsSuggest(widget.id);
                              if (mounted) setState(() => _sug = _list(r['suggest']));
                            } catch (e) {
                              if (mounted) _snack(context, '$e');
                            }
                          },
                    child: const Text('What does it still need?')),
              ]),
              _card(),
              _suggestions(),
              if (items.isEmpty) const Padding(padding: EdgeInsets.only(top: 16), child: Text('No assets yet.', style: TextStyle(color: C.muted))),
              for (final a in items) _tile(a),
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text('Sound presets, palette lock and your own uploads: web console (Game Desk > board > Assets).',
                    style: TextStyle(color: C.faint, fontSize: 12)),
              ),
            ],
          ]),
        ),
    );
  }
}
