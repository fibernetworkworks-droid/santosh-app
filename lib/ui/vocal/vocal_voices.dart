// v0.999.96 HOOLA VOCAL REDESIGN, PHONE (docs/HOOLA_VOCAL_REDESIGN.md sections 3.1 + 5, boards PhoneVoices, Voices,
// MyVoice): the Voice library in three tabs - Hoola (the voices this server speaks with), Shared (the shared library,
// GET /api/vocal/library: search by description, language / gender / age / use / sort, hear, Add to my voices) and Yours -
// and Your voice in three ways: Record your voice (the consent statement read aloud in the app, checked by the phone,
// then her tick), Describe a voice (three to hear, pick, name) and Change a voice (older, softer, another accent).
// No public figures, no named-person imitation (the server refuses them). Removing a voice deletes its recordings.
import 'dart:async';

import 'package:flutter/material.dart';

import '../hoola_theme.dart';
import 'vocal_home.dart' show VocalLanguageSheet;
import 'vocal_kit.dart';

const Map<String, String> _genders = {'Any gender': '', 'Women': 'female', 'Men': 'male'};
const Map<String, String> _ages = {'Any age': '', 'Young': 'young', 'Middle aged': 'middle_aged', 'Old': 'old'};
const Map<String, String> _uses = {
  'Any use': '', 'Ads': 'ads', 'Narration': 'narration', 'News': 'news', 'Support': 'support', 'Stories': 'stories',
  'Learning': 'learning', 'Social media': 'social',
};
const Map<String, String> _sorts = {'Most used': 'popular', 'Trending': 'trending', 'Newest': 'newest', 'Most added': 'most_added'};

// ------------------------------------------------------------------------------------------------ the Voice library
class VocalVoicesPage extends StatefulWidget {
  const VocalVoicesPage({super.key, required this.store, required this.player, this.lang = 'auto', this.picked = '', this.conv = '',
      this.embedded = false, this.onUse, this.onYourVoice, this.tab = 'Hoola'});
  final VocalStore store;
  final VocalPlayer player;
  final String lang, picked, conv;
  /// Inside the Vocal frame (no Back bar); a voice she uses goes to [onUse] instead of closing the page.
  final bool embedded;
  final ValueChanged<String>? onUse;
  final VoidCallback? onYourVoice;
  final String tab;   // Hoola | Shared | Yours
  @override
  State<VocalVoicesPage> createState() => _VocalVoicesPageState();
}

class _VocalVoicesPageState extends State<VocalVoicesPage> {
  final _q = TextEditingController();
  late String _tab = widget.tab;
  late String _lang = widget.lang;
  String _gender = '', _age = '', _use = '', _sort = 'popular';
  List<Map<String, dynamic>> _shared = [];
  bool _sharedReady = true, _sharedLoading = false, _sharedMore = false, _sharedAsked = false;
  String _sharedWhy = '';
  int _sharedPage = 0;
  Timer? _wait;
  VocalStore get store => widget.store;

  @override
  void initState() {
    super.initState();
    if (_tab == 'Shared') _loadShared();
  }

  @override
  void dispose() {
    _wait?.cancel();
    _q.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------- the shared library
  Future<void> _loadShared({bool more = false}) async {
    if (_sharedLoading) return;
    setState(() {
      _sharedLoading = true;
      _sharedAsked = true;
      if (!more) _sharedPage = 0;
    });
    try {
      Map<String, dynamic> r;
      if (VocalStore.debug) {
        r = crMap(VocalStore.debugData!['library']);
      } else {
        final api = store.app.api;
        if (api == null) throw Exception('Not connected to the server right now');
        r = await api.vocalLibrary({
          if (_q.text.trim().isNotEmpty) 'q': _q.text.trim(),
          if (_lang.isNotEmpty && _lang != 'auto') 'lang': _lang,
          if (_gender.isNotEmpty) 'gender': _gender,
          if (_age.isNotEmpty) 'age': _age,
          if (_use.isNotEmpty) 'use': _use,
          'sort': _sort,
          'page': '${more ? _sharedPage + 1 : 0}',
        });
      }
      if (!mounted) return;
      final vs = crList(r['voices']);
      setState(() {
        _sharedReady = r['ready'] != false;
        _sharedWhy = crS(r['why']);
        _sharedMore = r['more'] == true;
        if (more) {
          _shared = [..._shared, ...vs];
          _sharedPage++;
        } else {
          _shared = vs;
        }
      });
    } catch (e) {
      if (mounted) setState(() => _sharedWhy = crError(e));
    }
    if (mounted) setState(() => _sharedLoading = false);
  }

  void _changed() {
    setState(() {});
    if (_tab != 'Shared') return;
    _wait?.cancel();
    _wait = Timer(const Duration(milliseconds: 450), _loadShared);
  }

  // ---------------------------------------------------------------- filters
  Future<void> _pickLang() async {
    final v = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: _lang)),
    );
    if (v == null || !mounted) return;
    _lang = v;
    _changed();
  }

  Future<void> _pickFrom(String title, Map<String, String> opts, String current, void Function(String) put) async {
    final name = opts.entries.firstWhere((e) => e.value == current, orElse: () => opts.entries.first).key;
    final v = await crPick(context, title, opts.keys.toList(), name);
    if (v == null || !mounted) return;
    put(opts[v] ?? '');
    _changed();
  }

  String _nameOf(Map<String, String> opts, String v) => opts.entries.firstWhere((e) => e.value == v, orElse: () => opts.entries.first).key;

  // ---------------------------------------------------------------- one voice
  String _hearLang(Map<String, dynamic> v) {
    if (_lang.isNotEmpty && _lang != 'auto') return _lang;
    final ls = v['langs'] is List ? (v['langs'] as List).map(crS).where((x) => x != '*').toList() : const <String>[];
    return ls.isEmpty ? 'en' : ls.first;
  }

  String _line(Map<String, dynamic> v, {bool shared = false}) {
    if (shared && crS(v['line']).isNotEmpty) return crS(v['line']);
    final kind = crS(v['kind']);
    final ls = v['langs'] is List ? (v['langs'] as List).map(crS).where((x) => x != '*').toList() : const <String>[];
    final where = kind == 'clone' ? 'Your clone · every language'
        : kind == 'design' ? 'Described by you · every language'
        : kind == 'remix' ? 'Changed by you · every language'
        : kind == 'shared' ? 'From the shared library'
        : _lang != 'auto' && ls.contains(_lang) ? store.langNative(_lang)
        : ls.isEmpty ? 'Many languages' : '${store.langNative(ls.first)}${ls.length > 1 ? ' +${ls.length - 1}' : ''}';
    return [
      if (crS(v['tone']).isNotEmpty) crS(v['tone']),
      if (crS(v['accent']).isNotEmpty) crS(v['accent']),
      where,
      if (crS(v['use']).isNotEmpty && !shared) crS(v['use']),
      if (crS(v['tier']) == 'premium') 'Premium',
      if (v['ready'] == false) 'Not ready',
    ].join(' · ');
  }

  String _key(Map<String, dynamic> v, bool shared) => shared ? 'sh_${crS(v['id'])}' : 'pv_${crS(v['id'])}_${_hearLang(v)}';

  void _hear(Map<String, dynamic> v, bool shared) {
    final api = store.app.api;
    final key = _key(v, shared);
    if (shared) {
      final url = crS(v['preview']);
      if (url.isEmpty) {
        crToast(context, 'This voice has no sample to hear.');
        return;
      }
      widget.player.toggle(context, key, () => api!.vocalLibraryPreview(url), ext: 'mp3');
    } else {
      widget.player.toggle(context, key, () => api!.vocalPreviewBytes(crS(v['id']), _hearLang(v)), ext: 'wav');
    }
  }

  void _useVoice(String id) {
    if (widget.onUse != null) {
      widget.onUse!(id);
      crToast(context, 'Your next takes use this voice.');
    } else {
      Navigator.of(context).pop(id);
    }
  }

  Future<void> _add(Map<String, dynamic> v) async {
    try {
      if (!VocalStore.debug) {
        final api = store.app.api;
        if (api == null) throw Exception('Not connected to the server right now');
        await api.vocalLibraryAdd(crS(v['id']), crS(v['owner']), crS(v['name']));
        await store.load();
      }
      if (mounted) crToast(context, '${crS(v['name'])} is in Your voices.');
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
  }

  Future<void> _detail(Map<String, dynamic> v, bool shared) async {
    final name = crS(v['name']);
    final ready = v['ready'] != false;
    final langs = v['langs'] is List ? (v['langs'] as List).map(crS).where((x) => x.isNotEmpty && x != '*').toList() : const <String>[];
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) {
        final c = HoolaColors.of(ctx);
        Widget fact(String k, String val) => val.isEmpty
            ? const SizedBox.shrink()
            : Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SizedBox(width: 92, child: Text(k, style: HoolaType.small(c).copyWith(color: c.ink2))),
                  Expanded(child: Text(val, style: HoolaType.body(c).copyWith(fontSize: 14))),
                ]),
              );
        return CrHueScope(
          hue: CrHue.voice,
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Row(children: [
                  VocalVoiceDot(voice: v, size: 44),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(name, style: HoolaType.heading(c)),
                      Text(shared ? (crInt(v['uses']) > 0 ? 'Shared library · used ${crInt(v['uses'])} times' : 'Shared library')
                          : _line(v), maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
                    ]),
                  ),
                ]),
                const SizedBox(height: 14),
                if (shared && crS(v['line']).isNotEmpty) ...[
                  Text(crS(v['line']), style: HoolaType.body(c)),
                  const SizedBox(height: 12),
                ],
                fact('Speaks', langs.isEmpty ? '' : langs.take(4).map(store.langNative).join(', ') + (langs.length > 4 ? ' + ${langs.length - 4} more' : '')),
                fact('Good for', crS(v['use'])),
                fact('Accent', crS(v['accent'])),
                const SizedBox(height: 6),
                Row(children: [
                  Expanded(child: VocalPill(label: 'Hear it', quiet: true, glyph: CrGlyph.play, onTap: ready ? () => _hear(v, shared) : null)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: VocalPill(
                      label: shared ? 'Add to my voices' : (crS(v['id']) == widget.picked ? 'In use' : 'Use this voice'),
                      onTap: !ready
                          ? null
                          : () {
                              Navigator.of(ctx).pop();
                              if (shared) {
                                _add(v);
                              } else {
                                _useVoice(crS(v['id']));
                              }
                            },
                    ),
                  ),
                ]),
                if (shared) ...[
                  const SizedBox(height: 10),
                  Text('Shared voices were offered by their owners for anyone to use. They speak through the premium engine.',
                      style: HoolaType.small(c).copyWith(fontSize: 12)),
                ],
              ]),
            ),
          ),
        );
      },
    );
  }

  // ---------------------------------------------------------------- the screen
  List<Map<String, dynamic>> _local() {
    final q = _q.text.trim().toLowerCase();
    return store.voices.where((v) {
      final kind = crS(v['kind']);
      final mine = kind.isNotEmpty && kind != 'hoola';
      if (_tab == 'Hoola' && mine) return false;
      if (_tab == 'Yours' && !mine) return false;
      final ls = v['langs'] is List ? (v['langs'] as List).map(crS).toList() : const <String>[];
      if (_tab == 'Hoola') {
        if (_lang.isNotEmpty && _lang != 'auto' && !(ls.contains(_lang) || ls.contains('*'))) return false;
        if (_gender.isNotEmpty && crS(v['gender']) != _gender) return false;
        if (_age.isNotEmpty && !crS(v['age']).startsWith(_age.substring(0, 3))) return false;
        if (_use.isNotEmpty && !crS(v['use']).toLowerCase().contains(_use.substring(0, _use.length > 4 ? 4 : _use.length))) return false;
      }
      if (q.isEmpty) return true;
      final names = ls.map((l) => '${store.langNative(l)} ${store.langName(l)}').join(' ');
      return [v['name'], v['tone'], v['accent'], v['use'], names].map(crS).join(' ').toLowerCase().contains(q);
    }).toList();
  }

  Widget _filters(HoolaColors c) {
    final langName = _lang.isEmpty || _lang == 'auto' ? 'Any language' : store.langNative(_lang);
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(children: [
        VocalChip(label: langName, on: _lang.isNotEmpty && _lang != 'auto', menu: true, onTap: _pickLang),
        const SizedBox(width: 6),
        VocalChip(label: _nameOf(_genders, _gender), on: _gender.isNotEmpty, menu: true,
            onTap: () => _pickFrom('Gender', _genders, _gender, (v) => _gender = v)),
        const SizedBox(width: 6),
        VocalChip(label: _nameOf(_ages, _age), on: _age.isNotEmpty, menu: true, onTap: () => _pickFrom('Age', _ages, _age, (v) => _age = v)),
        const SizedBox(width: 6),
        VocalChip(label: _use.isEmpty ? 'Any use' : 'Use: ${_nameOf(_uses, _use)}', on: _use.isNotEmpty, menu: true,
            onTap: () => _pickFrom('Good for', _uses, _use, (v) => _use = v)),
        if (_tab == 'Shared') ...[
          const SizedBox(width: 6),
          VocalChip(label: _nameOf(_sorts, _sort), menu: true, onTap: () => _pickFrom('Order', _sorts, _sort, (v) => _sort = v)),
        ],
      ]),
    );
  }

  Widget _row(HoolaColors c, Map<String, dynamic> v, {bool shared = false}) {
    final p = widget.player;
    final key = _key(v, shared);
    final name = crS(v['name']);
    final ready = v['ready'] != false;
    final on = !shared && crS(v['id']) == widget.picked;
    return Semantics(
      container: true,
      explicitChildNodes: true,
      child: Container(
          padding: const EdgeInsets.fromLTRB(16, 6, 10, 6),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
          child: Row(children: [
            VocalVoiceDot(voice: v, size: 40),
            const SizedBox(width: 12),
            Expanded(
              child: Semantics(
                button: true,
                label: on ? '$name is in use' : name,
                excludeSemantics: true,
                onTap: () => _detail(v, shared),
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => _detail(v, shared),
                  child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 48),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                    Row(children: [
                      Flexible(child: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600))),
                      if (on) ...[const SizedBox(width: 6), Text('In use', style: HoolaType.small(c).copyWith(fontSize: 12, color: c.accent))],
                    ]),
                    Text(_line(v, shared: shared), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
                  ]),
                  ),
                ),
              ),
            ),
            Semantics(
              button: true,
              label: '${p.playing(key) ? 'Stop' : 'Hear'} $name',
              excludeSemantics: true,
              onTap: ready ? () => _hear(v, shared) : null,
              child: crTap48(ready ? () => _hear(v, shared) : null, Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(color: c.surface, shape: BoxShape.circle, border: Border.all(color: c.line)),
                child: Center(
                  child: p.busy(key)
                      ? SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.6, color: c.ink2))
                      : p.playing(key)
                          ? Container(width: 11, height: 11, decoration: BoxDecoration(color: c.ink, borderRadius: BorderRadius.circular(2)))
                          : CrIcon(CrGlyph.play, size: 14, color: ready ? c.ink : c.ink3),
                ),
              )),
            ),
          ]),
        ),
    );
  }

  Widget _list(HoolaColors c) {
    if (_tab == 'Shared') {
      if (!_sharedAsked || (_sharedLoading && _shared.isEmpty)) {
        return const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator(strokeWidth: 2)));
      }
      if (!_sharedReady || (_shared.isEmpty && _sharedWhy.isNotEmpty)) {
        return ListView(padding: const EdgeInsets.all(16), children: [
          CrNote(_sharedWhy.isEmpty ? 'The shared voice library is not set up on this server yet.' : _sharedWhy, glyph: CrGlyph.info),
        ]);
      }
      if (_shared.isEmpty) {
        return Center(child: Padding(padding: const EdgeInsets.all(32),
            child: Text('No shared voices match. Try other words.', textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 15))));
      }
      return ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        for (final v in _shared) _row(c, v, shared: true),
        if (_sharedMore)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: VocalPill(label: 'Show more voices', quiet: true, busy: _sharedLoading, onTap: () => _loadShared(more: true)),
          ),
      ]);
    }
    final shown = _local();
    return ListView(padding: const EdgeInsets.only(bottom: 24), children: [
      if (_tab == 'Yours')
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          child: VocalPill(label: 'Make your own voice', glyph: CrGlyph.plus, onTap: _yourVoice),
        ),
      if (shown.isEmpty)
        Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
              _tab == 'Yours'
                  ? 'None yet. A voice you record, describe or add from the shared library appears here.'
                  : store.voices.isEmpty
                      ? (store.error.isNotEmpty ? store.error : 'No voices are set up on this server yet.')
                      : 'No voices match.',
              textAlign: TextAlign.center,
              style: HoolaType.small(c).copyWith(fontSize: 15)),
        )
      else
        for (final v in shown) _row(c, v),
    ]);
  }

  Future<void> _yourVoice() async {
    if (widget.onYourVoice != null) {
      widget.onYourVoice!();
      return;
    }
    await Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => HoolaTheme(appearance: store.app.appearance,
            child: VocalYourVoicePage(store: store, player: widget.player, conv: widget.conv))));
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
          child: VocalTabs(tabs: const ['Hoola', 'Shared', 'Yours'], picked: _tab, onPick: (t) {
            setState(() => _tab = t);
            if (t == 'Shared' && !_sharedAsked) _loadShared();
          }),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
          child: TextField(
            controller: _q,
            onChanged: (_) => _changed(),
            textInputAction: TextInputAction.search,
            style: HoolaType.body(c),
            decoration: vocalInput(c, _tab == 'Shared' ? 'Describe a voice' : 'Search voices or a language'),
          ),
        ),
        if (_tab != 'Yours') _filters(c),
        Expanded(child: _list(c)),
      ]),
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Voice library', body: body);
  }
}

// ------------------------------------------------------------------------------------------------ Your voice
class VocalYourVoicePage extends StatefulWidget {
  const VocalYourVoicePage({super.key, required this.store, required this.player, this.conv = '', this.start = 'Record', this.embedded = false});
  final VocalStore store;
  final VocalPlayer player;
  final String conv;
  final String start;   // Record | Describe | Change
  final bool embedded;
  @override
  State<VocalYourVoicePage> createState() => _VocalYourVoicePageState();
}

class _VocalYourVoicePageState extends State<VocalYourVoicePage> {
  late String _way = widget.start == 'Design' ? 'Describe' : (widget.start == 'Clone' ? 'Record' : widget.start);
  VocalStore get store => widget.store;
  bool get _debug => VocalStore.debug;

  // record
  String _lang = 'en';
  Map<String, dynamic> _line = const {};
  bool _lineLoading = false;
  VocalFile? _said, _file;
  final _cloneName = TextEditingController(text: 'My voice');
  bool _agree = false, _cloning = false;
  Map<String, dynamic> _quote = const {};

  // describe
  final _describe = TextEditingController();
  final _designName = TextEditingController();
  String _gender = 'Any';
  List<Map<String, dynamic>> _previews = [];
  String _pick = '';
  bool _designing = false, _saving = false;

  // change
  String _base = '';
  final _change = TextEditingController();
  final _changeName = TextEditingController();
  bool _changing = false;

  @override
  void initState() {
    super.initState();
    final phone = VocalSettings.forPhone(store).lang;
    _lang = phone == 'auto' ? 'en' : phone;
    for (final t in [_describe, _designName, _cloneName, _change, _changeName]) {
      t.addListener(() {
        if (mounted) setState(() {});
      });
    }
    _loadLine();
    _requote();
  }

  @override
  void dispose() {
    for (final t in [_describe, _designName, _cloneName, _change, _changeName]) {
      t.dispose();
    }
    super.dispose();
  }

  Future<void> _requote() async {
    if (_debug) {
      setState(() => _quote = crMap(VocalStore.debugData!['quote']));
      return;
    }
    try {
      final q = await store.app.api?.vocalQuote({'job': 'clone', 'takes': 1});
      if (q != null && mounted) setState(() => _quote = q);
    } catch (_) {}
  }

  // ---------------------------------------------------------------- record
  Future<void> _loadLine() async {
    setState(() => _lineLoading = true);
    try {
      final r = _debug ? crMap(VocalStore.debugData!['consent']) : await store.app.api!.vocalConsentLine(_lang);
      if (mounted) setState(() => _line = r);
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _lineLoading = false);
  }

  Future<void> _pickLang() async {
    final v = await showModalBottomSheet<String>(context: context, showDragHandle: true, isScrollControlled: true,
        builder: (_) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: _lang)));
    if (v == null || v == 'auto' || !mounted) return;
    setState(() {
      _lang = v;
      _said = null;
    });
    _loadLine();
  }

  /// The recording that becomes the voice: a file she chose, else the statement she read.
  VocalFile? get _sample => _file ?? _said;

  bool get _cloneReady {
    final s = _said;
    if (s == null || !_agree || _cloneName.text.trim().isEmpty) return false;
    final sample = _sample!;
    return sample.seconds <= 0 || sample.seconds >= 10;
  }

  Future<void> _clone() async {
    final name = _cloneName.text.trim();
    final said = _said;
    final sample = _sample;
    if (!_cloneReady || said == null || sample == null) return;
    setState(() => _cloning = true);
    try {
      if (!_debug) {
        final api = store.app.api;
        if (api == null) throw Exception('Not connected to the server right now');
        final b = await vocalUpload(store, widget.conv, said);
        final a = identical(sample, said) ? b : await vocalUpload(store, widget.conv, sample);
        await api.vocalClone(name: name, fileId: a, consentFileId: b, lang: _lang);
      }
      await store.load();
      if (mounted) {
        crToast(context, '$name is ready in Your voices.');
        setState(() {
          _said = null;
          _file = null;
          _agree = false;
        });
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _cloning = false);
  }

  // ---------------------------------------------------------------- describe
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
      if (mounted) setState(() => _previews = crList(r['previews']).where((p) => crS(p['audio_id']).isNotEmpty).toList());
    } catch (e) {
      if (mounted) vocalError(context, store, e);
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
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _saving = false);
  }

  // ---------------------------------------------------------------- change
  Future<void> _remix() async {
    final change = _change.text.trim();
    if (_base.isEmpty || change.isEmpty) return;
    final base = store.voice(_base);
    final name = _changeName.text.trim().isEmpty ? '${crS(base?['name'])}, changed' : _changeName.text.trim();
    setState(() => _changing = true);
    try {
      if (!_debug) await store.app.api!.vocalRemix(_base, change, name);
      await store.load();
      if (mounted) {
        crToast(context, '$name is saved in Your voices.');
        setState(() {
          _change.clear();
          _changeName.clear();
        });
      }
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _changing = false);
  }

  Future<void> _remove(Map<String, dynamic> v) async {
    final ok = await vocalConfirm(context, 'Remove ${crS(v['name'])}?',
        'The voice and the recordings behind it are deleted. Sounds made with it stay.', 'Remove');
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
      if (mounted) vocalError(context, store, e);
    }
  }

  // ---------------------------------------------------------------- the screen
  @override
  Widget build(BuildContext context) {
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) {
        final c = HoolaColors.of(context);
        final credits = vocalCredits(_quote);
        Widget? dock;
        if (_way == 'Record' && store.canClone) {
          dock = VocalDock(
            note: 'Never a famous or named person’s voice. Someone else’s voice needs them to read the statement themselves.',
            child: VocalPill(label: credits.isEmpty ? 'Make my voice' : 'Make my voice · $credits', busy: _cloning,
                onTap: _cloneReady ? _clone : null),
          );
        }
        return Column(children: [
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
              for (final w in const [
                ('Record', 'Record your voice', '30 seconds in the app, or a file you have'),
                ('Describe', 'Describe a voice', 'A voice made from words, 3 options to hear'),
                ('Change', 'Change a voice', 'Older, softer, another accent'),
              ])
                Padding(padding: const EdgeInsets.only(bottom: 8), child: _wayCard(c, w.$1, w.$2, w.$3)),
              const SizedBox(height: 8),
              if (_way == 'Record') ..._recordPart(c) else if (_way == 'Describe') ..._designPart(c) else ..._changePart(c),
              const SizedBox(height: 24),
              _mine(c),
            ]),
          ),
          if (dock != null) dock,
        ]);
      },
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Your voice', body: body);
  }

  Widget _wayCard(HoolaColors c, String id, String title, String line) {
    final on = _way == id;
    return Semantics(
      button: true,
      selected: on,
      label: title,
      excludeSemantics: true,
      onTap: () => setState(() => _way = id),
      child: Material(
        color: on ? c.accentSoft : c.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: on ? c.accent : c.line)),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => setState(() => _way = id),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 36),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                Text(title, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                Text(line, style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink2)),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _recordPart(HoolaColors c) {
    if (!store.canClone) return [CrNote(store.whyNot('clone'), glyph: CrGlyph.info)];
    final fallback = _line.isNotEmpty && crS(_line['lang']).isNotEmpty && crS(_line['lang']) != _lang;
    return [
      VocalBox(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Read this out loud, in your own voice', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600))),
            VocalChip(label: store.langNative(_lang), menu: true, onTap: _pickLang),
          ]),
          const SizedBox(height: 8),
          if (_lineLoading)
            const Padding(padding: EdgeInsets.all(12), child: Center(child: CircularProgressIndicator(strokeWidth: 2)))
          else if (_line.isNotEmpty) ...[
            Text('“${crS(_line['line'])}”', style: HoolaType.reply(c).copyWith(fontSize: 17)),
            if (crS(_line['english']).isNotEmpty && crS(_line['english']) != crS(_line['line'])) ...[
              const SizedBox(height: 6),
              Text('“${crS(_line['english'])}”', style: HoolaType.small(c)),
            ],
          ],
          if (fallback || crS(_line['note']).isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(crS(_line['note']).isNotEmpty ? crS(_line['note'])
                : 'There is no statement in ${store.langNative(_lang)} yet, so read the English one.', style: HoolaType.small(c).copyWith(fontSize: 12)),
          ],
          const SizedBox(height: 12),
          VocalRecorder(what: 'my-voice', minSeconds: 10, maxSeconds: 30, onDone: (f) => setState(() => _said = f)),
        ]),
      ),
      const SizedBox(height: 10),
      Semantics(
        button: true,
        label: _file == null ? 'Use a recording I have instead' : 'Your recording: ${_file!.name}. Choose another',
        excludeSemantics: true,
        onTap: () async {
          final f = await vocalPickFile(context);
          if (f != null && mounted) setState(() => _file = f);
        },
        child: InkWell(
          onTap: () async {
            final f = await vocalPickFile(context);
            if (f != null && mounted) setState(() => _file = f);
          },
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Row(children: [
              CrIcon(_file == null ? CrGlyph.folder : CrGlyph.check, size: 16, color: _file == null ? c.ink2 : c.ok),
              const SizedBox(width: 8),
              Expanded(
                child: Text(_file == null ? 'Use a recording I have instead (10 to 30 seconds)' : 'Your recording: ${_file!.name}',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontSize: 14, color: c.ink2)),
              ),
            ]),
          ),
        ),
      ),
      const SizedBox(height: 10),
      const VocalLabel('Its name'),
      TextField(controller: _cloneName, maxLength: 40, style: HoolaType.body(c), decoration: vocalInput(c, 'My voice'),
          buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null),
      const SizedBox(height: 10),
      CrSwitch(
        title: 'This is my own voice',
        sub: 'I agree that Hoola keeps this recording as proof of my consent, and I can delete the voice at any time.',
        value: _agree,
        onChanged: (v) => setState(() => _agree = v),
      ),
    ];
  }

  List<Widget> _designPart(HoolaColors c) {
    if (!store.canDesign) return [CrNote(store.whyNot('design'), glyph: CrGlyph.info)];
    return [
      Text('Who it is, how old, how they sound. Hoola makes three to hear; you keep the one you like.',
          style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2)),
      const SizedBox(height: 10),
      TextField(controller: _describe, minLines: 2, maxLines: 5, maxLength: 600, style: HoolaType.body(c),
          buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
          decoration: vocalInput(c, 'An old storyteller from Kerala, slow and kind')),
      const SizedBox(height: 10),
      VocalTabs(tabs: const ['Any', 'Woman', 'Man'], picked: _gender, onPick: (v) => setState(() => _gender = v)),
      const SizedBox(height: 10),
      VocalPill(label: 'Make 3 voices to hear', glyph: CrGlyph.spark, busy: _designing, onTap: _describe.text.trim().length < 8 ? null : _design),
      if (_previews.isNotEmpty) ...[
        const SizedBox(height: 16),
        const VocalLabel('Hear, then pick one'),
        for (var i = 0; i < _previews.length; i++) _preview(c, _previews[i], i),
        if (_pick.isNotEmpty) ...[
          const SizedBox(height: 10),
          const VocalLabel('Its name'),
          TextField(controller: _designName, maxLength: 40, style: HoolaType.body(c), decoration: vocalInput(c, 'Storyteller'),
              buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null),
          const SizedBox(height: 10),
          VocalPill(label: 'Save this voice', busy: _saving, onTap: _designName.text.trim().isEmpty ? null : _saveDesign),
        ],
      ],
      const SizedBox(height: 10),
      Text('A voice from words only: never a real or famous person.', style: HoolaType.small(c).copyWith(fontSize: 12)),
    ];
  }

  Widget _preview(HoolaColors c, Map<String, dynamic> pv, int i) {
    final pid = crS(pv['pid']);
    final audio = crS(pv['audio_id']);
    final title = crS(pv['title']).isEmpty ? 'Option ${i + 1}' : crS(pv['title']);
    final key = 'dz_$pid';
    final on = _pick == pid;
    final p = widget.player;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: VocalBox(
        padding: const EdgeInsets.fromLTRB(6, 2, 8, 2),
        edge: on ? c.accent : null,
        child: Row(children: [
          VocalPlayButton(
            label: '${p.playing(key) ? 'Pause' : 'Play'} $title',
            playing: p.playing(key),
            loading: p.busy(key),
            onTap: () => p.toggle(context, key, () => store.app.api!.vocalAudio(audio), ext: 'wav'),
          ),
          const SizedBox(width: 6),
          Expanded(child: Text(title, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500))),
          VocalChip(label: on ? 'Picked' : 'Pick', on: on, onTap: () => setState(() => _pick = pid)),
        ]),
      ),
    );
  }

  List<Widget> _changePart(HoolaColors c) {
    final mine = store.mine;
    if (mine.isEmpty) {
      return [Text('Record or describe a voice first; then you can make it older, softer or give it another accent.',
          style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2))];
    }
    if (_base.isEmpty || store.voice(_base) == null) _base = crS(mine.first['id']);
    return [
      const VocalLabel('Start from'),
      Wrap(spacing: 6, runSpacing: 0, children: [
        for (final v in mine) VocalChip(label: crS(v['name']), on: crS(v['id']) == _base, onTap: () => setState(() => _base = crS(v['id']))),
      ]),
      const SizedBox(height: 10),
      const VocalLabel('What should change'),
      TextField(controller: _change, minLines: 2, maxLines: 4, maxLength: 300, style: HoolaType.body(c),
          buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
          decoration: vocalInput(c, 'A little older and softer')),
      const SizedBox(height: 10),
      const VocalLabel('Its name'),
      TextField(controller: _changeName, maxLength: 40, style: HoolaType.body(c), decoration: vocalInput(c, 'My voice, softer'),
          buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null),
      const SizedBox(height: 10),
      VocalPill(label: 'Make the changed voice', busy: _changing, onTap: _change.text.trim().isEmpty ? null : _remix),
    ];
  }

  Widget _mine(HoolaColors c) {
    final mine = store.mine;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      VocalLabel('Your voices', note: mine.isEmpty ? '' : '${mine.length}'),
      if (mine.isEmpty)
        Text('None yet. A voice you record, describe or change appears here and speaks every language Hoola speaks.',
            style: HoolaType.small(c))
      else
        for (final v in mine)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Row(children: [
              VocalVoiceDot(voice: v, size: 40),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(crS(v['name']), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                  Text(switch (crS(v['kind'])) {
                    'clone' => 'Recorded · consent kept',
                    'remix' => 'Changed from another voice',
                    'shared' => 'From the shared library',
                    _ => 'Described in words',
                  }, style: HoolaType.small(c).copyWith(fontSize: 12)),
                ]),
              ),
              VocalIconButton(label: 'Remove ${crS(v['name'])}', glyph: CrGlyph.trash, onTap: () => _remove(v)),
            ]),
          ),
    ]);
  }
}
