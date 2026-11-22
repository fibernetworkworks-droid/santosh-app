// v0.999.96 HOOLA VOCAL REDESIGN, PHONE (docs/HOOLA_VOCAL_REDESIGN.md section 5, board PhoneSpeech): Speech - her words
// with tone tags ([warm] [pause] ...) that work on every engine and are never read aloud, the settings as rows (language,
// voice, style, speed, takes, the download format), the takes with their waveforms, and ONE black pill with the price in
// credits. Nothing is spent until she taps. Create > Voice opens this page too (one place).
import 'dart:async';

import 'package:flutter/material.dart';

import '../hoola_theme.dart';
import 'vocal_home.dart' show VocalLanguageSheet;
import 'vocal_kit.dart';
import 'vocal_voices.dart' show VocalVoicesPage;

/// The tone tags the design offers (every engine honours them; none is read aloud).
const List<String> kVocalTones = ['[warm]', '[whispers]', '[laughs]', '[excited]', '[pause]', '[slowly]'];

/// Speeds she can pick.
const List<String> kVocalSpeeds = ['0.8x', '0.9x', '1.0x', '1.1x', '1.2x'];

class VocalSpeechPage extends StatefulWidget {
  const VocalSpeechPage({super.key, required this.store, required this.player, required this.settings, this.conv = '', this.text = '',
      this.embedded = true});
  final VocalStore store;
  final VocalPlayer player;
  final VocalSettings settings;
  final String conv, text;
  final bool embedded;
  @override
  State<VocalSpeechPage> createState() => _VocalSpeechPageState();
}

class _VocalSpeechPageState extends State<VocalSpeechPage> {
  late final TextEditingController _words = TextEditingController(text: widget.text);
  String _format = 'mp3';
  List<Map<String, dynamic>> _takes = [];
  Map<String, dynamic> _quote = const {};
  bool _busy = false;
  Timer? _wait;

  VocalSettings get vs => widget.settings;
  VocalStore get store => widget.store;

  @override
  void initState() {
    super.initState();
    _words.addListener(() {
      if (!mounted) return;
      setState(() {});
      _requote();
    });
    _requote(now: true);
  }

  @override
  void dispose() {
    _wait?.cancel();
    _words.dispose();
    super.dispose();
  }

  void _requote({bool now = false}) {
    _wait?.cancel();
    if (VocalStore.debug) {
      _quote = crMap(VocalStore.debugData!['quote']);
      return;
    }
    _wait = Timer(Duration(milliseconds: now ? 0 : 400), () async {
      final api = store.app.api;
      if (api == null) return;
      try {
        final q = await api.vocalQuote(vs.quote(_words.text));
        if (mounted) setState(() => _quote = q);
      } catch (_) {}
    });
  }

  /// A tone tag where the cursor is (or at the end), with a space each side.
  void _tag(String t) {
    final v = _words.value;
    final sel = v.selection;
    final at = sel.isValid ? sel.start : v.text.length;
    final end = sel.isValid ? sel.end : v.text.length;
    final before = v.text.substring(0, at);
    final ins = '${before.isEmpty || before.endsWith(' ') || before.endsWith('\n') ? '' : ' '}$t ';
    final text = v.text.replaceRange(at, end, ins);
    _words.value = TextEditingValue(text: text, selection: TextSelection.collapsed(offset: at + ins.length));
  }

  Future<void> _language() async {
    final v = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => CrHueScope(hue: CrHue.voice, child: VocalLanguageSheet(store: store, current: vs.lang)),
    );
    if (v == null || !mounted) return;
    setState(() {
      vs.lang = v;
      if (vs.voice.isNotEmpty && !store.voicesFor(v).any((x) => crS(x['id']) == vs.voice)) vs.voice = '';
    });
    _requote(now: true);
  }

  Future<void> _voice() async {
    final id = await Navigator.of(context).push<String>(MaterialPageRoute(
        builder: (_) => HoolaTheme(appearance: store.app.appearance,
            child: VocalVoicesPage(store: store, player: widget.player, lang: vs.lang, picked: vs.voice, conv: widget.conv))));
    if (id != null && mounted) {
      setState(() => vs.voice = id);
      _requote(now: true);
    }
  }

  Future<void> _style() async {
    final names = store.styles.values.toList();
    final v = await crPick(context, 'Style', names, vs.styleName(store));
    if (v == null || !mounted) return;
    final key = store.styles.entries.firstWhere((e) => e.value == v, orElse: () => MapEntry(vs.style, v)).key;
    setState(() => vs.style = key);
  }

  Future<void> _speed() async {
    final v = await crPick(context, 'Speed', kVocalSpeeds, '${vocalSpeed(vs.speed)}x');
    if (v == null || !mounted) return;
    setState(() => vs.speed = double.tryParse(v.replaceAll('x', '')) ?? 1.0);
  }

  Future<void> _takesPick() async {
    final v = await crPick(context, 'Takes', const ['1', '2', '3'], '${vs.takes}',
        notes: const {'1': 'One take', '2': 'Two to pick from', '3': 'Three to pick from'});
    if (v == null || !mounted) return;
    setState(() => vs.takes = int.tryParse(v) ?? 2);
    _requote(now: true);
  }

  Future<void> _formatPick() async {
    final list = vocalFormats(store);
    final v = await crPick(context, 'Download as', [for (final f in list) crS(f['name'])], vocalFormatName(store, _format),
        notes: {for (final f in list) crS(f['name']): crS(f['note'])});
    if (v == null || !mounted) return;
    setState(() => _format = crS(list.firstWhere((f) => crS(f['name']) == v, orElse: () => kVocalFormats.first)['id']));
  }

  Future<void> _speak() async {
    final text = _words.text.trim();
    if (text.isEmpty) return;
    final l = store.lang(vs.lang);
    if (l != null && crS(l['speech']) == 'none') {
      crToast(context, 'No voice engine speaks ${store.langName(vs.lang)} yet. Choose another language.');
      return;
    }
    setState(() => _busy = true);
    try {
      List<Map<String, dynamic>> made;
      if (VocalStore.debug) {
        made = crList(VocalStore.debugData!['speech']);
      } else {
        final api = store.app.api;
        if (api == null) throw Exception('Not connected to the server right now');
        made = vocalMade(await api.vocalTts({...vs.body(text, chat: widget.conv), 'format': _format}));
      }
      if (!mounted) return;
      setState(() => _takes = made);
      if (made.isNotEmpty) {
        crToast(context, '${made.length} take${made.length == 1 ? '' : 's'} ready.');
        final id = crS(made.first['id']);
        final ext = crS(made.first['ext']).isEmpty ? _format : crS(made.first['ext']);
        unawaited(widget.player.toggle(context, id, () => store.app.api!.vocalAudio(id, format: ext), ext: ext));
      }
      unawaited(store.load());
    } catch (e) {
      if (mounted) vocalError(context, store, e);
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _more(Map<String, dynamic> t, String name) async {
    final pick = await vocalMore(context, name, const ['Download', 'Delete']);
    if (!mounted || pick == null) return;
    if (pick == 'Download') await vocalShare(context, store.app, t, store: store);
    if (pick == 'Delete' && mounted && await vocalDeleteSound(context, store, t)) {
      setState(() => _takes = _takes.where((x) => crS(x['id']) != crS(t['id'])).toList());
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final credits = vocalCredits(_quote);
    final body = ListenableBuilder(
      listenable: Listenable.merge([store, widget.player]),
      builder: (context, _) => Column(children: [
        Expanded(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 20), children: [
            const VocalLabel('Words'),
            TextField(
              controller: _words,
              minLines: 4,
              maxLines: 10,
              maxLength: 100000,
              buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
              textCapitalization: TextCapitalization.sentences,
              style: HoolaType.body(c).copyWith(height: 1.5),
              decoration: vocalInput(c, 'Write what Hoola should say. A tone like [warm] or [pause] changes how it is read.'),
            ),
            const SizedBox(height: 6),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(children: [
                for (final t in kVocalTones) Padding(padding: const EdgeInsets.only(right: 6), child: VocalChip(label: t, onTap: () => _tag(t))),
              ]),
            ),
            Text('${_words.text.length} characters · tones are never read aloud',
                style: HoolaType.small(c).copyWith(fontSize: 12)),
            const SizedBox(height: 14),
            VocalRows([
              ('Language', store.langNative(vs.lang), _language),
              ('Voice', vs.voiceName(store), _voice),
              ('Style', vs.styleName(store), _style),
              ('Speed', '${vocalSpeed(vs.speed)}x', _speed),
              ('Takes', '${vs.takes}', _takesPick),
              ('Download as', vocalFormatName(store, _format), _formatPick),
            ]),
            if (_takes.isNotEmpty) ...[
              const SizedBox(height: 18),
              VocalLabel('Takes', note: store.langNative(vs.lang) == 'Auto' ? '' : store.langNative(vs.lang)),
              VocalBox(
                child: Column(children: [
                  for (var i = 0; i < _takes.length; i++) ...[
                    if (i > 0) const SizedBox(height: 8),
                    VocalTakeRow(
                      store: store,
                      player: widget.player,
                      item: _takes[i],
                      name: 'Take ${vocalTakeLetter(_takes[i], i)}',
                      note: widget.player.playing(crS(_takes[i]['id'])) ? 'playing' : '',
                      onMore: () => _more(_takes[i], 'Take ${vocalTakeLetter(_takes[i], i)}'),
                    ),
                  ],
                ]),
              ),
            ],
            const SizedBox(height: 10),
            Text('Every file carries the AI mark.', style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
        VocalDock(
          note: 'Nothing is spent until you tap',
          child: VocalPill(
            label: credits.isEmpty ? 'Speak it' : 'Speak it · $credits',
            busy: _busy,
            onTap: _words.text.trim().isEmpty ? null : _speak,
          ),
        ),
      ]),
    );
    return vocalFrame(context, embedded: widget.embedded, title: 'Speech', body: body);
  }
}
