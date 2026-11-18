/// v0.416 RELEASE (Studio project > Release): the live game as real downloads - Linux, Windows, macOS (built on Hoola's
/// server) and Android APK / AAB (built in her private builds repo) - each file checked; the store kit; itch.io uploads
/// only after her tap on the card. Her itch.io key is typed in the web console (Release page), never in chat.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _names = {'linux': 'Linux', 'windows': 'Windows', 'macos': 'macOS', 'android': 'Android'};

class GameReleaseScreen extends StatefulWidget {
  const GameReleaseScreen({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<GameReleaseScreen> createState() => _GameReleaseScreenState();
}

class _GameReleaseScreenState extends State<GameReleaseScreen> {
  Map<String, dynamic> _d = {};
  Map<String, dynamic> _kit = {};
  final Set<String> _pick = {};
  String _fmt = 'apk';
  bool _loaded = false;
  bool _busy = false;
  final Map<String, TextEditingController> _itch = {};
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in _itch.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    _timer?.cancel();
    try {
      final d = await widget.app.api!.gameReleases(widget.id);
      if (!mounted) return;
      setState(() {
        if (!_loaded) {
          final t = Map<String, dynamic>.from((d['targets'] as Map?) ?? const {});
          _pick.addAll(t.entries.where((e) => (e.value as Map)['ready'] == true).map((e) => e.key));
        }
        _d = d;
        _loaded = true;
      });
      if (_list(d['releases']).any((r) => _s(r['status']) == 'building')) _timer = Timer(const Duration(seconds: 6), _load);
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

  void _open(String url) => launchUrl(Uri.parse(widget.app.api!.absolute(url)), mode: LaunchMode.externalApplication);

  Widget _release(Map<String, dynamic> r) {
    final plats = Map<String, dynamic>.from((r['platforms'] as Map?) ?? const {});
    final itch = Map<String, dynamic>.from((r['itch'] as Map?) ?? const {});
    final card = Map<String, dynamic>.from((itch['card'] as Map?) ?? const {});
    final rid = _s(r['id']);
    final ctl = _itch.putIfAbsent(rid, TextEditingController.new);
    final ok = _s(r['status']) == 'done' || _s(r['status']) == 'partial';
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_s(r['number'])} · ${_s(r['version_name'])} · ${_s(r['status'])}', style: display(15)),
          for (final e in plats.entries)
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text('${_names[e.key] ?? e.key} · ${_s((e.value as Map)['status'])}'),
              subtitle: Text([
                if ((e.value as Map)['mb'] != null) '${(e.value as Map)['mb']} MB',
                _s((e.value as Map)['note']),
                ..._strs(((e.value as Map)['checks'] as Map?)?['errors']),
              ].where((x) => x.isNotEmpty).join(' · ')),
              trailing: _s((e.value as Map)['url']).isEmpty
                  ? null
                  : IconButton(icon: const Icon(Icons.download_rounded), onPressed: () => _open(_s((e.value as Map)['url']))),
            ),
          if (ok && card.isNotEmpty && _s(card['hash']).isNotEmpty)
            FilledButton(
                onPressed: _busy
                    ? null
                    : () => _call(() => widget.app.api!.gameItchPush(widget.id, rid, _s(card['hash'])), 'Uploaded to itch.io.'),
                child: Text('Yes, upload to itch.io (${_s(card['target'])})'))
          else if (ok) ...[
            TextField(controller: ctl, decoration: const InputDecoration(hintText: 'itch.io page: your-name/game-name')),
            OutlinedButton(
                onPressed: _busy
                    ? null
                    : () => _call(() => widget.app.api!.gameItchCard(widget.id, rid, ctl.text.trim()), 'The upload card is ready: tap Yes to upload.'),
                child: const Text('Prepare itch.io upload')),
          ],
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = Map<String, dynamic>.from((_d['targets'] as Map?) ?? const {});
    return DeskPage(
      title: 'Release',
      onRefresh: _load,
      body: () => RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            if (!_loaded)
              const Center(child: CircularProgressIndicator())
            else ...[
              Text(_s((_d['identity'] as Map?)?['package']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('New release', style: display(15.5)),
                  for (final p in _names.keys)
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      dense: true,
                      value: _pick.contains(p),
                      onChanged: (v) => setState(() => v == true ? _pick.add(p) : _pick.remove(p)),
                      title: Text(_names[p]!),
                      subtitle: (t[p] as Map?)?['ready'] == true ? null : Text(_s((t[p] as Map?)?['note'])),
                    ),
                  Wrap(spacing: 8, children: [
                    ChoiceChip(label: const Text('Android APK'), selected: _fmt == 'apk', onSelected: (_) => setState(() => _fmt = 'apk')),
                    ChoiceChip(label: const Text('Android AAB (Play)'), selected: _fmt == 'aab', onSelected: (_) => setState(() => _fmt = 'aab')),
                  ]),
                  const SizedBox(height: 8),
                  GradientButton(
                    label: 'Build the release',
                    icon: Icons.rocket_launch_outlined,
                    height: 48,
                    onTap: _busy || _pick.isEmpty
                        ? null
                        : () => _call(() => widget.app.api!.gameReleaseNew(widget.id, _pick.toList(), _fmt), 'Building the release.'),
                  ),
                ]),
              ),
              for (final r in _list(_d['releases'])) _release(r),
              const SizedBox(height: 12),
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Store kit', style: display(15)),
                  const Text('Texts for itch.io, Steam and Google Play, store images, AI disclosure, an age-rating draft. Nothing is published.',
                      style: TextStyle(color: C.muted, fontSize: 12.5)),
                  Wrap(spacing: 8, children: [
                    OutlinedButton(
                        onPressed: _busy
                            ? null
                            : () async {
                                setState(() => _busy = true);
                                try {
                                  final k = await widget.app.api!.gameStoreKit(widget.id);
                                  if (mounted) setState(() => _kit = k);
                                } catch (e) {
                                  if (mounted) _snack(context, '$e');
                                }
                                if (mounted) setState(() => _busy = false);
                              },
                        child: const Text('Make the store kit')),
                    if (_s(_kit['zip']).isNotEmpty) FilledButton(onPressed: () => _open(_s(_kit['zip'])), child: const Text('Download (ZIP)')),
                  ]),
                  if (_kit.isNotEmpty) ...[
                    Text('itch.io: ${_s((_kit['itch'] as Map?)?['tagline'])}', style: const TextStyle(fontSize: 13)),
                    Text('Steam: ${_s((_kit['steam'] as Map?)?['short'])}', style: const TextStyle(fontSize: 13)),
                    Text('Rating draft: ${((_kit['rating'] as Map?)?['expected'] as Map?)?.entries.map((e) => '${e.key} ${e.value}').join(' · ') ?? ''}',
                        style: const TextStyle(fontSize: 13)),
                    for (final n in _strs(_kit['notes'])) Text(n, style: const TextStyle(color: C.muted, fontSize: 12)),
                  ],
                ]),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text('Your itch.io key goes in the web console (Release page), never in chat.',
                    style: TextStyle(color: C.faint, fontSize: 12)),
              ),
            ],
          ]),
        ),
    );
  }
}
