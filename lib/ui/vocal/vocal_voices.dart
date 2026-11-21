// v0.999.90 HOOLA VOCAL, GLOBAL, ON THE PHONE (design canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue, PhoneVoices):
// the Voices list (search, All / Women / Men / her language, Hear = the voice's own preview in that language, Use) and
// Your voice: Design one from words (three to hear, pick, name) or Clone her own (a 10-30 s recording, then her spoken
// yes - the consent line in her language - then a name and a switch that says it is her voice or the person agreed).
// No public figures, no named-person imitation (the server refuses them). Removing a voice deletes both recordings.
import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../hoola_theme.dart';
import 'vocal_home.dart' show VocalLanguageSheet;
import 'vocal_kit.dart';

// ------------------------------------------------------------------------------------------------ the Voices list
class VocalVoicesPage extends StatefulWidget {
  const VocalVoicesPage({super.key, required this.store, required this.player, this.lang = 'auto', this.picked = '', this.conv = ''});
  final VocalStore store;
  final VocalPlayer player;
  final String lang, picked, conv;
  @override
  State<VocalVoicesPage> createState() => _VocalVoicesPageState();
}

class _VocalVoicesPageState extends State<VocalVoicesPage> {
  final _q = TextEditingController();
  String _filter = 'All';
  VocalStore get store => widget.store;

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  String _hearLang(Map<String, dynamic> v) {
    if (widget.lang.isNotEmpty && widget.lang != 'auto') return widget.lang;
    final ls = v['langs'] is List ? (v['langs'] as List).map(crS).where((x) => x != '*').toList() : const <String>[];
    return ls.isEmpty ? 'en' : ls.first;
  }

  String _line(Map<String, dynamic> v) {
    final kind = crS(v['kind']);
    final ls = v['langs'] is List ? (v['langs'] as List).map(crS).where((x) => x != '*').toList() : const <String>[];
    final where = kind == 'clone' ? 'Your clone · every language'
        : kind == 'design' ? 'Designed by you · every language'
        : kind == 'remix' ? 'Your remix · every language'
        : widget.lang != 'auto' && ls.contains(widget.lang) ? store.langNative(widget.lang)
        : ls.isEmpty ? 'Many languages' : '${store.langNative(ls.first)}${ls.length > 1 ? ' +${ls.length - 1}' : ''}';
    return [
      if (crS(v['tone']).isNotEmpty) crS(v['tone']),
      if (crS(v['accent']).isNotEmpty) crS(v['accent']),
      where,
      if (crS(v['tier']) == 'premium') 'Premium',
      if (v['ready'] == false) 'Not ready',
    ].join(' · ');
  }

  Future<void> _yourVoice() async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => HoolaTheme(appearance: store.app.appearance,
            child: VocalYourVoicePage(store: store, player: widget.player, conv: widget.conv))));
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final langChip = widget.lang != 'auto' && widget.lang.isNotEmpty ? store.langNative(widget.lang) : '';
    final filters = ['All', 'Women', 'Men', if (langChip.isNotEmpty) langChip, 'Yours'];
    return CrHueScope(
      hue: CrHue.voice,
      child: ListenableBuilder(
        listenable: Listenable.merge([store, widget.player]),
        builder: (context, _) {
          final q = _q.text.trim().toLowerCase();
          final shown = store.voices.where((v) {
            final kind = crS(v['kind']);
            final mine = kind.isNotEmpty && kind != 'hoola';
            final ls = v['langs'] is List ? (v['langs'] as List).map(crS).toList() : const <String>[];
            if (_filter == 'Women' && crS(v['gender']) != 'female') return false;
            if (_filter == 'Men' && crS(v['gender']) != 'male') return false;
            if (_filter == 'Yours' && !mine) return false;
            if (_filter == langChip && langChip.isNotEmpty && !mine && !(ls.contains(widget.lang) || ls.contains('*'))) return false;
            if (q.isEmpty) return true;
            final names = ls.map((l) => '${store.langNative(l)} ${store.langName(l)}').join(' ');
            return [v['name'], v['tone'], v['accent'], v['use'], names].map(crS).join(' ').toLowerCase().contains(q);
          }).toList();
          return Scaffold(
            backgroundColor: c.bg,
            body: SafeArea(
              child: Column(children: [
                VocalTop(title: 'Voices', actions: [
                  Semantics(
                    button: true,
                    label: 'Your voice: make or copy one',
                    excludeSemantics: true,
                    child: crTap48(_yourVoice, Container(
                      height: 36,
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(color: c.pill, borderRadius: BorderRadius.circular(18)),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        CrIcon(CrGlyph.plus, size: 14, color: c.onPill),
                        const SizedBox(width: 6),
                        Text('Your voice', style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w600, color: c.onPill)),
                      ]),
                    )),
                  ),
                  const SizedBox(width: 8),
                ]),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                  child: VocalSearch(controller: _q, hint: 'Search voices or a language', onChanged: (_) => setState(() {})),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Wrap(spacing: 6, runSpacing: 0, children: [
                      for (final f in filters) CrChip(label: f, on: f == _filter, onTap: () => setState(() => _filter = f)),
                    ]),
                  ),
                ),
                Expanded(
                  child: shown.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(32),
                            child: Text(store.voices.isEmpty
                                ? (store.error.isNotEmpty ? store.error : 'No voices are set up on this server yet.')
                                : 'No voices match.', textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 15)),
                          ),
                        )
                      : ListView(padding: const EdgeInsets.fromLTRB(16, 6, 8, 24), children: [for (final v in shown) _row(c, v)]),
                ),
              ]),
            ),
          );
        },
      ),
    );
  }

  Widget _row(HoolaColors c, Map<String, dynamic> v) {
    final id = crS(v['id']);
    final lang = _hearLang(v);
    final key = 'pv_${id}_$lang';
    final p = widget.player;
    final name = crS(v['name']);
    final ready = v['ready'] != false;
    final on = id == widget.picked;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        VocalVoiceDot(voice: v, size: 44),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
            Text(_line(v), maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
        Semantics(
          button: true,
          label: '${p.playing(key) ? 'Stop' : 'Hear'} $name',
          excludeSemantics: true,
          child: crTap48(ready ? () => p.toggle(context, key, () => store.app.api!.vocalPreviewBytes(id, lang), ext: 'wav') : null, Container(
            height: 36,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), border: Border.all(color: c.lineStrong)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              if (p.busy(key))
                SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 1.6, color: c.ink2))
              else
                CrIcon(p.playing(key) ? CrGlyph.minus : CrGlyph.play, size: 12, color: ready ? c.ink : c.ink3),
              const SizedBox(width: 6),
              Text(p.playing(key) ? 'Stop' : 'Hear', style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500, color: ready ? c.ink : c.ink3)),
            ]),
          )),
        ),
        const SizedBox(width: 4),
        Semantics(
          button: true,
          selected: on,
          label: on ? '$name is in use' : 'Use $name',
          excludeSemantics: true,
          child: crTap48(ready ? () => Navigator.of(context).pop(id) : null, Container(
            height: 36,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(color: on ? c.accentSoft : c.sunk, borderRadius: BorderRadius.circular(18)),
            child: Center(child: Text(on ? 'In use' : 'Use', style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w600,
                color: on ? c.accent : (ready ? c.ink : c.ink3)))),
          )),
        ),
      ]),
    );
  }
}

// ------------------------------------------------------------------------------------------------ Your voice
class VocalYourVoicePage extends StatefulWidget {
  const VocalYourVoicePage({super.key, required this.store, required this.player, this.conv = '', this.start = 'Design'});
  final VocalStore store;
  final VocalPlayer player;
  final String conv;
  final String start;   // Design | Clone
  @override
  State<VocalYourVoicePage> createState() => _VocalYourVoicePageState();
}

class _Picked {
  _Picked(this.name, this.bytes);
  final String name;
  final List<int> bytes;
}

class _VocalYourVoicePageState extends State<VocalYourVoicePage> {
  late String _tab = widget.start;
  VocalStore get store => widget.store;
  bool get _debug => VocalStore.debug;

  // design
  final _describe = TextEditingController();
  final _designName = TextEditingController();
  String _gender = 'Any';
  List<Map<String, dynamic>> _previews = [];
  String _pick = '';
  bool _designing = false, _saving = false;

  // clone
  int _step = 1;
  String _cloneLang = 'auto';
  _Picked? _sample, _consent;
  Map<String, dynamic> _line = const {};
  final _cloneName = TextEditingController();
  bool _agree = false, _cloning = false, _lineLoading = false;

  @override
  void initState() {
    super.initState();
    final phone = VocalSettings.forPhone(store).lang;
    _cloneLang = phone == 'auto' ? 'en' : phone;
    _describe.addListener(() => setState(() {}));
    _designName.addListener(() => setState(() {}));
    _cloneName.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _describe.dispose();
    _designName.dispose();
    _cloneName.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------- design
  Future<void> _design() async {
    final d = _describe.text.trim();
    if (d.length < 8) {
      crToast(context, 'Describe the voice in a few words first: who, how old, how they sound.');
      return;
    }
    setState(() {
      _designing = true;
      _previews = [];
      _pick = '';
    });
    try {
      final r = _debug
          ? crMap(VocalStore.debugData!['design'])
          : await store.app.api!.vocalDesign(d, gender: _gender == 'Woman' ? 'female' : _gender == 'Man' ? 'male' : '');
      if (mounted) setState(() => _previews = crList(r['previews']));
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _designing = false);
  }

  Future<void> _saveDesign() async {
    final name = _designName.text.trim();
    if (_pick.isEmpty || name.isEmpty) return;
    setState(() => _saving = true);
    try {
      if (!_debug) await store.app.api!.vocalDesignSave(_pick, name);
      await store.load();
      if (mounted) {
        crToast(context, '$name is saved in Your voices.');
        setState(() {
          _previews = [];
          _pick = '';
          _designName.clear();
        });
      }
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _saving = false);
  }

  // ---------------------------------------------------------------- clone
  Future<_Picked?> _pickAudio() async {
    if (_debug) return _Picked('recording.m4a', const [1]);
    final r = await FilePicker.platform.pickFiles(type: FileType.audio, withData: true);
    final f = r?.files.firstOrNull;
    if (f == null) return null;
    final b = f.bytes;
    if (b == null) {
      if (mounted) crToast(context, 'This recording could not be read.');
      return null;
    }
    if (b.length > 30 * 1024 * 1024) {
      if (mounted) crToast(context, 'This recording is over 30 MB. Choose a shorter one.');
      return null;
    }
    return _Picked(f.name, b);
  }

  Future<void> _loadLine() async {
    setState(() => _lineLoading = true);
    try {
      final r = _debug ? crMap(VocalStore.debugData!['consent']) : await store.app.api!.vocalConsentLine(_cloneLang);
      if (mounted) setState(() => _line = r);
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _lineLoading = false);
  }

  Future<void> _clone() async {
    final name = _cloneName.text.trim();
    final api = store.app.api;
    if (name.isEmpty || !_agree || _sample == null || _consent == null) return;
    setState(() => _cloning = true);
    try {
      if (!_debug) {
        if (api == null) throw Exception('Not connected to the server right now');
        var conv = widget.conv;
        if (conv.isEmpty) conv = crS((await api.vocalChat())['id']);
        final a = crS((await api.chatFile(conv, _sample!.name, _sample!.bytes))['file_id']);
        final b = crS((await api.chatFile(conv, _consent!.name, _consent!.bytes))['file_id']);
        if (a.isEmpty || b.isEmpty) throw Exception('A recording did not upload. Try again.');
        await api.vocalClone(name: name, fileId: a, consentFileId: b, lang: _cloneLang);
      }
      await store.load();
      if (mounted) {
        crToast(context, '$name is ready in Your voices.');
        setState(() {
          _step = 1;
          _sample = null;
          _consent = null;
          _agree = false;
          _cloneName.clear();
        });
      }
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _cloning = false);
  }

  Future<void> _remove(Map<String, dynamic> v) async {
    final ok = await vocalConfirm(context, 'Remove ${crS(v['name'])}?',
        'The voice and both recordings behind it are deleted. Sounds made with it stay.', 'Remove');
    if (ok != true) return;
    try {
      if (!_debug) await store.app.api?.vocalDeleteVoice(crS(v['id']));
      if (_debug) {
        store.ov = {...store.ov, 'voices': store.voices.where((x) => crS(x['id']) != crS(v['id'])).toList()};
        store.tell();
      } else {
        await store.load();
      }
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
  }

  // ---------------------------------------------------------------- the screen
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrHueScope(
      hue: CrHue.voice,
      child: ListenableBuilder(
        listenable: Listenable.merge([store, widget.player]),
        builder: (context, _) => Scaffold(
          backgroundColor: c.bg,
          body: SafeArea(
            child: Column(children: [
              VocalTop(title: 'Your voice', sub: _tab == 'Clone' ? 'Step $_step of 3' : 'Design one from words'),
              Expanded(
                child: ListView(padding: const EdgeInsets.fromLTRB(20, 4, 20, 24), children: [
                  CrSegment(options: const ['Design', 'Clone'], picked: _tab, onPick: (v) => setState(() => _tab = v)),
                  const SizedBox(height: 18),
                  if (_tab == 'Design') ..._designPart(c) else ..._clonePart(c),
                  const SizedBox(height: 26),
                  _mine(c),
                ]),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  List<Widget> _designPart(HoolaColors c) {
    if (!store.canDesign) return [CrNote(store.whyNot('design'), glyph: CrGlyph.info)];
    return [
      Text('Describe a voice', style: HoolaType.display(c)),
      const SizedBox(height: 4),
      Text('Who it is, how old, how they sound. Hoola makes three to hear; you keep the one you like.', style: HoolaType.small(c).copyWith(fontSize: 15)),
      const SizedBox(height: 14),
      CrTextCard(title: 'The voice', controller: _describe, max: 600, lines: 3,
          hint: 'A calm grandmother from Nairobi, warm and slow, a little husky'),
      const SizedBox(height: 12),
      CrSegment(options: const ['Any', 'Woman', 'Man'], picked: _gender, onPick: (v) => setState(() => _gender = v)),
      const SizedBox(height: 12),
      CrMain(label: 'Make 3 voices to hear', height: 48, glyph: CrGlyph.spark, busy: _designing,
          onTap: _describe.text.trim().length < 8 ? null : _design),
      if (_previews.isNotEmpty) ...[
        const SizedBox(height: 18),
        const CrLabel('Hear, then pick one'),
        for (var i = 0; i < _previews.length; i++) _preview(c, _previews[i], i),
        const SizedBox(height: 12),
        if (_pick.isNotEmpty) ...[
          CrTextCard(title: 'Its name', controller: _designName, max: 40, lines: 1, hint: 'Bibi'),
          const SizedBox(height: 12),
          CrMain(label: 'Save this voice', height: 48, busy: _saving,
              onTap: _designName.text.trim().isEmpty ? null : _saveDesign),
        ],
      ],
      const SizedBox(height: 12),
      Text('A voice from words only: never a real or famous person.', style: HoolaType.small(c).copyWith(fontSize: 12)),
    ];
  }

  Widget _preview(HoolaColors c, Map<String, dynamic> pv, int i) {
    final pid = crS(pv['pid']);
    final audio = crS(pv['audio_id']);
    final title = crS(pv['title']).isEmpty ? 'Voice ${i + 1}' : crS(pv['title']);
    final key = 'dz_$pid';
    final on = _pick == pid;
    final p = widget.player;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: CrCard(
        padding: const EdgeInsets.fromLTRB(8, 4, 8, 4),
        edge: on ? CrHue.voice.a : null,
        child: Row(children: [
          VocalPlayButton(
            label: '${p.playing(key) ? 'Pause' : 'Play'} $title',
            playing: p.playing(key),
            loading: p.busy(key),
            onTap: () => p.toggle(context, key, () => store.app.api!.vocalAudio(audio), ext: 'wav'),
          ),
          const SizedBox(width: 6),
          Expanded(child: Text(title, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500))),
          Semantics(
            button: true,
            selected: on,
            label: on ? '$title is picked' : 'Pick $title',
            excludeSemantics: true,
            child: crTap48(() => setState(() => _pick = pid), Container(
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(color: on ? c.accentSoft : c.sunk, borderRadius: BorderRadius.circular(18)),
              child: Center(child: Text(on ? 'Picked' : 'Pick', style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w600,
                  color: on ? c.accent : c.ink))),
            )),
          ),
        ]),
      ),
    );
  }

  List<Widget> _clonePart(HoolaColors c) {
    if (!store.canClone) return [CrNote(store.whyNot('clone'), glyph: CrGlyph.info)];
    Widget fileCard(_Picked? f, String empty, VoidCallback onTap) => Semantics(
          button: true,
          label: f == null ? empty : 'Chosen: ${f.name}. Choose another',
          excludeSemantics: true,
          child: CrCard(
            onTap: onTap,
            padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
            child: Row(children: [
              Container(
                width: 40, height: 40,
                decoration: BoxDecoration(gradient: CrHue.voice.gradient, shape: BoxShape.circle),
                child: const Center(child: CrIcon(CrGlyph.mic, size: 18, color: CreateHues.onHue)),
              ),
              const SizedBox(width: 12),
              Expanded(child: Text(f == null ? empty : f.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500))),
              CrIcon(f == null ? CrGlyph.plus : CrGlyph.check, size: 16, color: f == null ? c.ink3 : c.ok),
            ]),
          ),
        );
    switch (_step) {
      case 1:
        return [
          Text('Your voice, in 10 to 30 seconds', style: HoolaType.display(c)),
          const SizedBox(height: 4),
          Text('A clear recording of one person talking, with no music behind. Say which language you speak in it.',
              style: HoolaType.small(c).copyWith(fontSize: 15)),
          const SizedBox(height: 14),
          fileCard(_sample, 'Choose the recording', () async {
            final f = await _pickAudio();
            if (f != null) setState(() => _sample = f);
          }),
          const SizedBox(height: 12),
          Semantics(
            button: true,
            label: 'The language I speak in it: ${store.langNative(_cloneLang)}',
            excludeSemantics: true,
            child: CrCard(
              padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
              onTap: () async {
                final v = await showModalBottomSheet<String>(context: context, showDragHandle: true, isScrollControlled: true,
                    builder: (_) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: _cloneLang)));
                if (v != null && v != 'auto') setState(() => _cloneLang = v);
              },
              child: Row(children: [
                Expanded(child: Text('Spoken in ${store.langNative(_cloneLang)}', style: HoolaType.body(c))),
                CrIcon(CrGlyph.chevron, size: 16, color: c.ink3),
              ]),
            ),
          ),
          const SizedBox(height: 14),
          CrMain(label: 'Next', height: 48, onTap: _sample == null ? null : () {
            setState(() => _step = 2);
            _loadLine();
          }),
        ];
      case 2:
        final fallback = _line.isNotEmpty && crS(_line['lang']).isNotEmpty && crS(_line['lang']) != _cloneLang;
        return [
          Text('Now say yes, in your own voice', style: HoolaType.display(c)),
          const SizedBox(height: 4),
          Text('Read this line aloud and record it. It is in the language you spoke in step 1.',
              style: HoolaType.small(c).copyWith(fontSize: 15)),
          const SizedBox(height: 14),
          if (_lineLoading)
            const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator(strokeWidth: 2)))
          else if (_line.isNotEmpty)
            CrCard(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('“${crS(_line['line'])}”', style: HoolaType.reply(c).copyWith(fontSize: 18)),
                if (crS(_line['english']).isNotEmpty && crS(_line['english']) != crS(_line['line'])) ...[
                  const SizedBox(height: 8),
                  Text('“${crS(_line['english'])}”', style: HoolaType.small(c)),
                ],
              ]),
            ),
          if (fallback) ...[
            const SizedBox(height: 8),
            CrNote('There is no consent line in ${store.langNative(_cloneLang)} yet, so read the English one.', glyph: CrGlyph.info),
          ],
          const SizedBox(height: 12),
          fileCard(_consent, 'Choose the recording of you saying it', () async {
            final f = await _pickAudio();
            if (f != null) setState(() => _consent = f);
          }),
          const SizedBox(height: 8),
          Text('Hoola checks this is the same voice as your recording. Removing the voice deletes both.',
              style: HoolaType.small(c).copyWith(fontSize: 12)),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: CrQuiet(label: 'Back', height: 48, onTap: () => setState(() => _step = 1))),
            const SizedBox(width: 10),
            Expanded(child: CrMain(label: 'Next', height: 48, onTap: _consent == null ? null : () => setState(() => _step = 3))),
          ]),
        ];
      default:
        return [
          Text('Name your voice', style: HoolaType.display(c)),
          const SizedBox(height: 14),
          CrTextCard(title: 'Its name', controller: _cloneName, max: 40, lines: 1, hint: 'My voice'),
          const SizedBox(height: 12),
          CrSwitch(
            title: 'This is my own voice, or the person agreed',
            sub: 'Never a public figure or someone who did not say yes.',
            value: _agree,
            onChanged: (v) => setState(() => _agree = v),
          ),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: CrQuiet(label: 'Back', height: 48, onTap: () => setState(() => _step = 2))),
            const SizedBox(width: 10),
            Expanded(child: CrMain(label: 'Make my voice', height: 48, busy: _cloning,
                onTap: _cloneName.text.trim().isEmpty || !_agree ? null : _clone)),
          ]),
        ];
    }
  }

  Widget _mine(HoolaColors c) {
    final mine = store.mine;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      CrLabel('Your voices', note: mine.isEmpty ? '' : '${mine.length}'),
      if (mine.isEmpty)
        Text('None yet. A voice you design or copy appears here and speaks every language Hoola speaks.', style: HoolaType.small(c))
      else
        for (final v in mine)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              VocalVoiceDot(voice: v, size: 40),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(crS(v['name']), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                  Text(crS(v['kind']) == 'clone' ? 'Your clone' : crS(v['kind']) == 'remix' ? 'A remix' : 'Designed from words',
                      style: HoolaType.small(c).copyWith(fontSize: 12)),
                ]),
              ),
              CrRoundButton(glyph: CrGlyph.trash, label: 'Remove ${crS(v['name'])}', size: 36, onTap: () => _remove(v)),
            ]),
          ),
    ]);
  }
}
