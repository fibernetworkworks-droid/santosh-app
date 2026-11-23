// v0.999.90 HOOLA VOCAL, GLOBAL, ON THE PHONE (design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue, PhoneVoices
// board 3): Your sounds - every sound Hoola made for her (speech, dialogue, dubs, effects), by day, with All / Speech /
// Dialogue / Dubs / Effects, play, Dub it (speech and dialogue), Download or share, Delete. A sound or a dub that could
// not be made is said plainly, with why, that nothing was charged, and what to do next.
// v0.999.163 (canvas claude.ai/artifact/VDXqUd7zx9TMxwTjVcXiJz): kinds incl. Clean-ups and Kept, search, how many are kept on
// the server, a star on kept sounds (Keep with a star / Stop keeping), and Select: hold a sound (or tap Select) to tick
// several, then Keep all or Remove them in one tap.
import 'package:flutter/material.dart';

import '../hoola_theme.dart';
import 'vocal_kit.dart';

class VocalSoundsPage extends StatefulWidget {
  const VocalSoundsPage({super.key, required this.store, required this.player, required this.onAsk, this.embedded = false});
  final VocalStore store;
  /// Inside the Vocal frame (no Back bar of its own).
  final bool embedded;
  final VocalPlayer player;
  /// Words to put in the Vocal chat box (never sent by themselves): "Dub Product tour into ".
  final void Function(String words) onAsk;
  @override
  State<VocalSoundsPage> createState() => _VocalSoundsPageState();
}

class _VocalSoundsPageState extends State<VocalSoundsPage> {
  String _filter = 'All';
  String _q = '';
  bool _picking = false;
  final Set<String> _chosen = {};
  bool _busy = false;
  List<Map<String, dynamic>> _dubs = const [];
  VocalStore get store => widget.store;

  static const _kinds = ['All', 'Speech', 'Dialogue', 'Dubs', 'Effects', 'Clean-ups', 'Kept'];

  bool _in(String f, Map<String, dynamic> r) {
    if (f == 'All') return true;
    if (f == 'Kept') return r['star'] == true;
    final k = crS(r['kind']);
    if (f == 'Clean-ups') return k == 'cleanup' || k == 'isolate';
    if (f == 'Dialogue') return k == 'dialogue' || k == 'podcast';
    return vocalFilterOf(k) == f;
  }

  bool _matches(Map<String, dynamic> r) {
    final q = _q.trim().toLowerCase();
    if (q.isEmpty) return true;
    return [r['title'], r['text'], r['voice_name'], store.langName(crS(r['lang'])), store.langNative(crS(r['lang']))]
        .map(crS).any((x) => x.toLowerCase().contains(q));
  }

  int get _keptMax {
    final u = crMap(store.ov['usage']), l = crMap(store.ov['limits']);
    final n = crInt(u['kept_max']) > 0 ? crInt(u['kept_max']) : crInt(l['history']);
    return n > 0 ? n : 300;
  }

  /// Keep / stop keeping / remove several (or one) sounds; the list is read again after.
  Future<void> _bulk(List<String> ids, String action) async {
    if (ids.isEmpty) return;
    if (action == 'remove') {
      final ok = await vocalConfirm(context, ids.length == 1 ? 'Remove this sound?' : 'Remove ${ids.length} sounds?',
          'They go from your sounds and from this server. This cannot be undone.', 'Remove');
      if (ok != true || !mounted) return;
    }
    setState(() => _busy = true);
    try {
      if (VocalStore.debug) {
        VocalStore.debugAnswer('history_bulk', {'ids': ids, 'action': action});
        final rows = [
          for (final h in store.history)
            if (!(action == 'remove' && ids.contains(crS(h['id']))))
              ids.contains(crS(h['id'])) && action != 'remove' ? ({...h, 'star': action == 'keep'}..removeWhere((k, v) => k == 'star' && v == false)) : h,
        ];
        store.ov = {...store.ov, 'history': rows};
        store.tell();
      } else {
        await store.app.api!.vocalHistoryBulk(ids, action);
        await store.load();
      }
      if (!mounted) return;
      final n = ids.length;
      crToast(context, switch (action) {
        'keep' => n == 1 ? 'Kept. It stays whatever the limit.' : '$n sounds kept. They stay whatever the limit.',
        'unkeep' => n == 1 ? 'No longer kept with a star.' : '$n sounds no longer kept with a star.',
        _ => n == 1 ? 'Removed.' : '$n sounds removed.',
      });
      setState(() {
        _chosen.clear();
        if (action == 'remove') _picking = false;
      });
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  void initState() {
    super.initState();
    _loadDubs();
  }

  Future<void> _loadDubs() async {
    if (VocalStore.debug) {
      setState(() => _dubs = crList(VocalStore.debugData!['dubs']));
      return;
    }
    try {
      final d = await store.app.api?.vocalDubs();
      if (d != null && mounted) setState(() => _dubs = d);
    } catch (_) {}
  }

  Future<void> _refresh() async {
    await store.load();
    await _loadDubs();
  }

  String _line(Map<String, dynamic> r) {
    final kind = crS(r['kind']);
    final secs = r['seconds'] is num ? r['seconds'] as num : 0;
    return [
      vocalKindName(kind),
      if (crS(r['voice_name']).isNotEmpty && kind != 'dub') crS(r['voice_name']),
      if (crS(r['lang']).isNotEmpty) store.langNative(crS(r['lang'])),
      if (secs > 0) vocalClock(secs),
    ].where((x) => x.isNotEmpty && x != 'Auto').join(' · ');
  }

  /// A dub that could not be made: "Dub into Quechua could not be made".
  List<Map<String, dynamic>> get _failedDubs => [
        for (final d in _dubs)
          if (crS(d['status']) == 'failed')
            {
              'id': crS(d['id']),
              'kind': 'dub',
              'failed_dub': true,
              'title': crS(d['title']).isEmpty ? crS(d['name']) : crS(d['title']),
              'langs': [for (final l in crList(d['langs'])) crS(l['name']).isEmpty ? store.langName(crS(l['code'])) : crS(l['name'])],
              'error': crS(d['error']),
              'made': d['made'] ?? d['created'] ?? 0,
            },
      ];

  Future<void> _menu(Map<String, dynamic> r) async {
    final title = crS(r['title']).isEmpty ? 'This sound' : crS(r['title']);
    final star = r['star'] == true;
    final pick = await vocalMore(context, title,
        [star ? 'Stop keeping' : 'Keep with a star', if (vocalCanDub(r)) 'Dub it', 'Download', 'Select', 'Delete']);
    if (!mounted || pick == null) return;
    if (pick == 'Keep with a star' || pick == 'Stop keeping') await _bulk([crS(r['id'])], star ? 'unkeep' : 'keep');
    if (pick == 'Select') {
      setState(() {
        _picking = true;
        _chosen.add(crS(r['id']));
      });
    }
    if (pick == 'Dub it') await vocalDubTake(context, store, widget.player, r);
    if (pick == 'Download') await vocalShare(context, store.app, r, store: store);
    if (pick == 'Delete' && mounted) await vocalDeleteSound(context, store, r);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrHueScope(
      hue: CrHue.voice,
      child: ListenableBuilder(
        listenable: Listenable.merge([store, widget.player]),
        builder: (context, _) {
          final all = [...store.history, ..._failedDubs];
          final shown = all.where((r) => _in(_filter, r) && _matches(r)).toList()
            ..sort((a, b) => vocalEpoch(b['made']).compareTo(vocalEpoch(a['made'])));
          final groups = <String, List<Map<String, dynamic>>>{};
          for (final r in shown) {
            final w = crWhen(vocalEpoch(r['made']));
            groups.putIfAbsent(w.isEmpty ? 'Earlier' : w, () => []).add(r);
          }
          final kinds = [for (final k in _kinds) if (k == 'All' || k == 'Kept' || k == _filter || all.any((r) => _in(k, r))) k];
          final kept = store.history.where((h) => h['star'] == true).length;
          final chosen = [for (final h in store.history) if (_chosen.contains(crS(h['id']))) crS(h['id'])];
          final selectable = [for (final r in shown) if (r['failed_dub'] != true && !vocalFailed(r)) crS(r['id'])];
          final secs = store.history.where((h) => _chosen.contains(crS(h['id']))).fold<num>(0, (a, h) => a + (h['seconds'] is num ? h['seconds'] as num : 0));
          return vocalFrame(context, embedded: widget.embedded, title: 'Your sounds', body: Column(children: [
                if (_picking)
                  _pickBar(c, chosen, selectable, secs)
                else
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 10, 8, 0),
                    child: Row(children: [
                      Expanded(
                        child: Semantics(
                          label: '${store.history.length} of $_keptMax sounds kept on this server${kept > 0 ? ', $kept with a star' : ''}',
                          excludeSemantics: true,
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('Kept on this server · ${store.history.length} of $_keptMax${kept > 0 ? ' · $kept with a star' : ''}',
                                style: HoolaType.small(c).copyWith(fontSize: 12)),
                            const SizedBox(height: 4),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(3),
                              child: LinearProgressIndicator(
                                value: (store.history.length / _keptMax).clamp(0, 1).toDouble(),
                                minHeight: 5,
                                backgroundColor: c.sunk,
                                color: c.accent,
                              ),
                            ),
                          ]),
                        ),
                      ),
                      const SizedBox(width: 12),
                      VocalChip(label: 'Select', onTap: store.history.isEmpty ? null : () => setState(() => _picking = true)),
                    ]),
                  ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                  child: TextField(
                    style: HoolaType.body(c),
                    decoration: vocalInput(c, 'Search words, voices, languages').copyWith(prefixIcon: Icon(Icons.search_rounded, size: 20, color: c.ink3)),
                    onChanged: (v) => setState(() => _q = v),
                  ),
                ),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                  child: Row(children: [
                    for (final f in kinds)
                      Padding(padding: const EdgeInsets.only(right: 6),
                          child: VocalChip(label: f, on: f == _filter, onTap: () => setState(() => _filter = f))),
                  ]),
                ),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: _refresh,
                    child: shown.isEmpty
                        ? ListView(children: [
                            Padding(
                              padding: const EdgeInsets.all(32),
                              child: Text(all.isEmpty ? 'Your sounds appear here. Write what Hoola should say in the Vocal chat and send.'
                                  : _q.trim().isNotEmpty ? 'No sound has “${_q.trim()}” in it.'
                                  : _filter == 'Kept' ? 'No kept sounds yet. Keep one with a star and it stays whatever the limit.'
                                  : 'Nothing here yet.', textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 15)),
                            ),
                          ])
                        : ListView(padding: const EdgeInsets.fromLTRB(16, 4, 8, 24), children: [
                            for (final g in groups.entries) ...[
                              Padding(padding: const EdgeInsets.fromLTRB(0, 10, 0, 4), child: Text(g.key, style: HoolaType.label(c))),
                              for (final r in g.value) vocalFailed(r) || r['failed_dub'] == true ? _failed(c, r) : _row(c, r),
                            ],
                            Padding(
                              padding: const EdgeInsets.fromLTRB(0, 12, 8, 0),
                              child: Text('The newest $_keptMax are kept. Starred sounds are never removed by the limit.',
                                  style: HoolaType.small(c).copyWith(fontSize: 12)),
                            ),
                          ]),
                  ),
                ),
              ]));
        },
      ),
    );
  }

  Widget _row(HoolaColors c, Map<String, dynamic> r) {
    final id = crS(r['id']);
    final p = widget.player;
    final title = crS(r['title']).isEmpty ? vocalKindName(crS(r['kind'])) : crS(r['title']);
    final ext = crS(r['ext']) == 'wav' ? 'wav' : 'mp3';
    final on = _chosen.contains(id);
    void flip() => setState(() => on ? _chosen.remove(id) : _chosen.add(id));
    if (_picking) {
      return Semantics(
        container: true,
        checked: on,
        label: title,
        excludeSemantics: true,
        onTap: flip,
        child: InkWell(
          onTap: flip,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 2),
            padding: const EdgeInsets.fromLTRB(0, 4, 8, 4),
            decoration: BoxDecoration(color: on ? c.accentSoft : null, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              SizedBox(width: 48, height: 44, child: Checkbox(value: on, onChanged: (_) => flip())),
              const SizedBox(width: 4),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Flexible(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600))),
                    if (r['star'] == true) Padding(padding: const EdgeInsets.only(left: 4), child: Icon(Icons.star_rounded, size: 15, color: c.warn)),
                  ]),
                  Text(_line(r), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
                ]),
              ),
            ]),
          ),
        ),
      );
    }
    return GestureDetector(
      onLongPress: () => setState(() {
        _picking = true;
        _chosen.add(id);
      }),
      child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        VocalPlayButton(
          label: '${p.playing(id) ? 'Pause' : 'Play'} $title',
          playing: p.playing(id),
          loading: p.busy(id),
          size: 44,
          onTap: () => p.toggle(context, id, () => store.app.api!.vocalAudio(id, format: ext), ext: ext),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Flexible(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600))),
              if (r['star'] == true)
                Semantics(label: 'Kept', child: Padding(padding: const EdgeInsets.only(left: 4), child: Icon(Icons.star_rounded, size: 15, color: c.warn))),
            ]),
            Text(_line(r), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
        VocalIconButton(label: 'More for $title', icon: Icons.more_horiz_rounded, onTap: () => _menu(r)),
      ]),
    ),
    );
  }

  /// Select: how many are ticked, Select all shown, Keep all, Remove N, and the way out.
  Widget _pickBar(HoolaColors c, List<String> chosen, List<String> selectable, num secs) {
    final all = selectable.isNotEmpty && selectable.every(_chosen.contains);
    final none = chosen.isEmpty || _busy;
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      padding: const EdgeInsets.fromLTRB(4, 4, 10, 10),
      decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          VocalIconButton(label: 'Stop selecting', icon: Icons.close_rounded, onTap: () => setState(() {
                _picking = false;
                _chosen.clear();
              })),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${chosen.length} selected', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
              Text(chosen.isEmpty ? 'Tick the sounds you want' : '${vocalClock(secs)} of sound', style: HoolaType.small(c).copyWith(fontSize: 12)),
            ]),
          ),
        ]),
        Wrap(spacing: 6, runSpacing: 6, children: [
          VocalChip(label: all ? 'Clear' : 'Select all shown', onTap: selectable.isEmpty ? null : () => setState(() {
                if (all) {
                  _chosen.removeAll(selectable);
                } else {
                  _chosen.addAll(selectable.take(300));
                }
              })),
          VocalChip(label: 'Keep all', onTap: none ? null : () => _bulk(chosen, 'keep')),
          VocalChip(label: chosen.isEmpty ? 'Remove' : 'Remove ${chosen.length}', onTap: none ? null : () => _bulk(chosen, 'remove')),
        ]),
      ]),
    );
  }

  Widget _failed(HoolaColors c, Map<String, dynamic> r) {
    final kind = crS(r['kind']);
    final langs = r['langs'] is List ? (r['langs'] as List).map(crS).where((x) => x.isNotEmpty).toList() : const <String>[];
    final what = kind == 'dub'
        ? 'Dub${langs.isEmpty ? '' : ' into ${langs.join(', ')}'} could not be made'
        : '${crS(r['title']).isEmpty ? vocalKindName(kind) : crS(r['title'])} could not be made';
    final err = crS(r['error']);
    final title = crS(r['title']);
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 6, 8, 6),
      child: Semantics(
        container: true,
        explicitChildNodes: true,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 12, 10),
          decoration: BoxDecoration(color: c.badSoft, borderRadius: BorderRadius.circular(16), border: Border.all(color: c.line)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Padding(padding: const EdgeInsets.only(top: 2), child: CrIcon(CrGlyph.info, size: 16, color: c.bad)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(what, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text('${err.isEmpty ? 'It did not work this time.' : (err.endsWith('.') ? err : '$err.')} Nothing was charged.',
                      style: HoolaType.small(c).copyWith(color: c.ink2)),
                ]),
              ),
            ]),
            Align(
              alignment: Alignment.centerRight,
              child: CrSmall(
                label: kind == 'dub' ? 'Choose another language' : 'Try again in the chat',
                glyph: kind == 'dub' ? CrGlyph.globe : CrGlyph.refresh,
                onTap: () {
                  if (!widget.embedded) Navigator.of(context).maybePop();
                  widget.onAsk(kind == 'dub' ? 'Dub ${title.isEmpty ? 'it' : title} into ' : 'Make ${title.isEmpty ? 'it' : title} again');
                },
              ),
            ),
          ]),
        ),
      ),
    );
  }
}
