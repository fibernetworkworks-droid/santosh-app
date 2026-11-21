// v0.999.90 HOOLA VOCAL, GLOBAL, ON THE PHONE (design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue, PhoneVoices
// board 3): Your sounds - every sound Hoola made for her (speech, dialogue, dubs, effects), by day, with All / Speech /
// Dialogue / Dubs / Effects, play, Download or share, Delete. A sound or a dub that could not be made is said plainly,
// with why, that nothing was charged, and what to do next.
import 'package:flutter/material.dart';

import '../hoola_theme.dart';
import 'vocal_kit.dart';

class VocalSoundsPage extends StatefulWidget {
  const VocalSoundsPage({super.key, required this.store, required this.player, required this.onAsk});
  final VocalStore store;
  final VocalPlayer player;
  /// Words to put in the Vocal chat box (never sent by themselves): "Dub Product tour into ".
  final void Function(String words) onAsk;
  @override
  State<VocalSoundsPage> createState() => _VocalSoundsPageState();
}

class _VocalSoundsPageState extends State<VocalSoundsPage> {
  String _filter = 'All';
  List<Map<String, dynamic>> _dubs = const [];
  VocalStore get store => widget.store;

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
    final pick = await crPick(context, title, const ['Download or share', 'Delete'], '');
    if (!mounted || pick == null) return;
    if (pick == 'Download or share') await vocalShare(context, store.app, r);
    if (pick == 'Delete' && mounted) {
      final ok = await vocalConfirm(context, 'Delete this sound?', 'It is removed from Your sounds and from its chat. This cannot be undone.', 'Delete');
      if (ok != true) return;
      try {
        if (!VocalStore.debug) await store.app.api?.vocalHistoryDelete(crS(r['id']));
        store.ov = {...store.ov, 'history': store.history.where((x) => crS(x['id']) != crS(r['id'])).toList()};
        store.tell();
      } catch (e) {
        if (mounted) crToast(context, crError(e));
      }
    }
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
          final shown = all.where((r) => _filter == 'All' || vocalFilterOf(crS(r['kind'])) == _filter).toList()
            ..sort((a, b) => vocalEpoch(b['made']).compareTo(vocalEpoch(a['made'])));
          final groups = <String, List<Map<String, dynamic>>>{};
          for (final r in shown) {
            final w = crWhen(vocalEpoch(r['made']));
            groups.putIfAbsent(w.isEmpty ? 'Earlier' : w, () => []).add(r);
          }
          return Scaffold(
            backgroundColor: c.bg,
            body: SafeArea(
              child: Column(children: [
                const VocalTop(title: 'Your sounds'),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Wrap(spacing: 6, runSpacing: 0, children: [
                      for (final f in const ['All', 'Speech', 'Dialogue', 'Dubs', 'Effects']) CrChip(label: f, on: f == _filter, onTap: () => setState(() => _filter = f)),
                    ]),
                  ),
                ),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: _refresh,
                    child: shown.isEmpty
                        ? ListView(children: [
                            Padding(
                              padding: const EdgeInsets.all(32),
                              child: Text(all.isEmpty ? 'Your sounds appear here. Write what Hoola should say in the Vocal chat and send.'
                                  : 'Nothing here yet.', textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 15)),
                            ),
                          ])
                        : ListView(padding: const EdgeInsets.fromLTRB(16, 4, 8, 24), children: [
                            for (final g in groups.entries) ...[
                              Padding(padding: const EdgeInsets.fromLTRB(0, 10, 0, 4), child: Text(g.key, style: HoolaType.label(c))),
                              for (final r in g.value) vocalFailed(r) || r['failed_dub'] == true ? _failed(c, r) : _row(c, r),
                            ],
                          ]),
                  ),
                ),
              ]),
            ),
          );
        },
      ),
    );
  }

  Widget _row(HoolaColors c, Map<String, dynamic> r) {
    final id = crS(r['id']);
    final p = widget.player;
    final title = crS(r['title']).isEmpty ? vocalKindName(crS(r['kind'])) : crS(r['title']);
    final ext = crS(r['ext']) == 'wav' ? 'wav' : 'mp3';
    return Padding(
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
            Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
            Text(_line(r), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
        CrRoundButton(glyph: CrGlyph.layers, label: 'More for $title', size: 36, onTap: () => _menu(r)),
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
                  Navigator.of(context).maybePop();
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
