// v0.912 CREATE NATIVE: "shape it and keep it" - My creations (11), Brand kit (12) and Hoola Cinema (13) of
// claude.ai/artifact/SARfWkfWm8ZtmmnAcU8dYn, plus the viewers every Create screen opens (a picture full screen, a video
// with her key, a song or voice-over, a script). My creations = /api/create/items (search, kinds, sort, select many to
// save or delete - delete asks first). Brand kit = /api/brand/kit + /api/brand/logo, the same kit every poster uses.
// Cinema = the hub and its rules on the phone; its tools run in the console's own Cinema page, signed in.
import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';

import '../../state.dart';
import '../attach.dart';
import '../hoola_theme.dart';
import '../shell/hoola_console_page.dart';
import '../shell/hoola_settings.dart' show hoolaOpenNew;
import 'create_kit.dart';

// ------------------------------------------------------------------------------------------------ opening one creation
/// Opens one creation the way its kind wants: a picture full screen, a video playing, a song or voice-over in a sheet,
/// a script to read.
Future<void> crOpenItem(BuildContext context, CreateStore store, Map<String, dynamic> it) async {
  HapticFeedback.selectionClick();
  final mime = crS(it['mime']);
  if (mime.startsWith('image/')) {
    await hoolaOpenNew(context, store.app, _PictureView(store: store, item: it));
  } else if (mime.startsWith('video/')) {
    await hoolaOpenNew(context, store.app, _VideoView(app: store.app, item: it));
  } else if (mime.startsWith('audio/')) {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: CrAudioCard(app: store.app, item: it, line: '${crKindName(crS(it['kind']))} · ${crWhen(it['created'])}'),
        ),
      ),
    );
  } else if (mime.startsWith('text/')) {
    await hoolaOpenNew(context, store.app, _TextView(store: store, item: it));
  } else {
    await crShareItem(context, store.app, it);
  }
}

/// v0.913 a picture in a dark room: the picture large (pinch to look closer), round glass buttons on top, and a glass
/// panel below with what it is, "Bring it to life" (Hoola Cinema turns a picture into a clip) and the quiet actions.
class _PictureView extends StatelessWidget {
  const _PictureView({required this.store, required this.item});
  final CreateStore store;
  final Map<String, dynamic> item;

  Future<void> _delete(BuildContext context) async {
    if (await crConfirmDelete(context, 1) && context.mounted) {
      try {
        await store.delete(crS(item['id']));
        if (context.mounted) Navigator.of(context).maybePop();
      } catch (e) {
        if (context.mounted) crToast(context, crError(e));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = crMap(item['meta']);
    final bottom = MediaQuery.paddingOf(context).bottom;
    // the room is always dark, whatever the phone's theme: the picture is the only light in it
    final c = HoolaColors.darkSet;
    final facts = [crWhen(item['created']), crS(m['aspect']), m['quality'] == 'best' ? 'Best quality' : '', 'Made with AI']
        .where((s) => s.isNotEmpty)
        .toList();
    Widget act(CrGlyph g, String label, VoidCallback onTap, {Color? tint}) => Semantics(
          button: true,
          label: label,
          excludeSemantics: true,
          onTap: onTap,
          child: crPress(
            onTap: onTap,
            child: SizedBox(
              width: 64,
              child: Column(children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: crGlass(c, shape: BoxShape.circle, strong: true),
                  alignment: Alignment.center,
                  child: CrIcon(g, size: 19, color: tint ?? c.ink),
                ),
                const SizedBox(height: 6),
                Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink2, fontSize: 12)),
              ]),
            ),
          ),
        );
    return Theme(
      data: hoolaTheme(Brightness.dark),
      child: CrHueScope(
        hue: CrHue.image,
        child: Scaffold(
          backgroundColor: CreateHues.night,
          body: Stack(children: [
            Positioned.fill(
              child: InteractiveViewer(
                maxScale: 5,
                child: Center(child: CrItemImage(app: store.app, item: item, fit: BoxFit.contain, cache: 1600)),
              ),
            ),
            // a dark fade at the top and the bottom so the buttons and words always read
            const Positioned(
              left: 0,
              right: 0,
              top: 0,
              height: 140,
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Color.fromARGB(150, 9, 8, 14), Color.fromARGB(0, 9, 8, 14)],
                    ),
                  ),
                ),
              ),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                child: Row(children: [
                  CrRoundButton(glyph: CrGlyph.back, label: 'Back', onTap: () => Navigator.of(context).maybePop()),
                  const Spacer(),
                  CrRoundButton(glyph: CrGlyph.share, label: 'Save or share', onTap: () => crShareItem(context, store.app, item)),
                ]),
              ),
            ),
            Positioned(
              left: 12,
              right: 12,
              bottom: 12 + bottom,
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
                decoration: crGlass(c, radius: 26, strong: true),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Text(crS(item['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.title(c).copyWith(fontSize: 16)),
                  const SizedBox(height: 4),
                  Text(facts.join(' · '), style: HoolaType.small(c).copyWith(color: c.ink2)),
                  if (crS(m['description']).isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(crS(m['description']), maxLines: 3, overflow: TextOverflow.ellipsis,
                        style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14)),
                  ],
                  const SizedBox(height: 14),
                  CrHueScope(
                    hue: CrHue.video,
                    child: CrMain(
                      label: 'Bring it to life',
                      glyph: CrGlyph.video,
                      height: 50,
                      onTap: () => hoolaOpenNew(context, store.app, CreateCinema(store: store)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
                    act(CrGlyph.share, 'Share', () => crShareItem(context, store.app, item)),
                    act(CrGlyph.down, 'Save', () => crShareItem(context, store.app, item)),
                    act(CrGlyph.trash, 'Delete', () => _delete(context), tint: c.bad),
                  ]),
                ]),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

Future<bool> crConfirmDelete(BuildContext context, int n) async =>
    await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(n == 1 ? 'Delete this creation?' : 'Delete $n creations?'),
        content: const Text('It is removed from Hoola. A copy you already saved or sent stays where it is.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Keep')),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text('Delete', style: TextStyle(color: HoolaColors.of(ctx).bad)),
          ),
        ],
      ),
    ) ==
    true;

class _VideoView extends StatefulWidget {
  const _VideoView({required this.app, required this.item});
  final Santosh app;
  final Map<String, dynamic> item;
  @override
  State<_VideoView> createState() => _VideoViewState();
}

class _VideoViewState extends State<_VideoView> {
  VideoPlayerController? _ctl;
  String _err = '';

  @override
  void initState() {
    super.initState();
    final api = widget.app.api;
    if (api == null) return;
    final ctl = VideoPlayerController.networkUrl(Uri.parse(api.createItemUrl(crS(widget.item['id']))), httpHeaders: api.authHeaders);
    _ctl = ctl;
    ctl.initialize().then((_) {
      if (!mounted) return;
      ctl.play();
      setState(() {});
    }).catchError((Object e) {
      if (mounted) setState(() => _err = 'The video did not play: ${crError(e)}');
    });
    ctl.addListener(() {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _ctl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final ctl = _ctl;
    final ready = ctl != null && ctl.value.isInitialized;
    return CrPage(
      title: crS(widget.item['title']),
      trailing: CrRoundButton(glyph: CrGlyph.share, label: 'Save or share', onTap: () => crShareItem(context, widget.app, widget.item)),
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: Container(
            color: c.sunk,
            child: AspectRatio(
              aspectRatio: ready ? ctl.value.aspectRatio : 9 / 16,
              child: _err.isNotEmpty
                  ? Center(child: Padding(padding: const EdgeInsets.all(20), child: Text(_err, style: HoolaType.small(c))))
                  : !ready
                      ? Center(child: SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2)))
                      : GestureDetector(
                          onTap: () => ctl.value.isPlaying ? ctl.pause() : ctl.play(),
                          child: Stack(fit: StackFit.expand, children: [
                            VideoPlayer(ctl),
                            if (!ctl.value.isPlaying)
                              Center(
                                child: Container(
                                  width: 60,
                                  height: 60,
                                  decoration: BoxDecoration(color: Colors.black.withOpacity(.55), shape: BoxShape.circle),
                                  alignment: Alignment.center,
                                  child: const CrIcon(CrGlyph.play, size: 24, color: Colors.white),
                                ),
                              ),
                          ]),
                        ),
            ),
          ),
        ),
        if (ready) ...[
          const SizedBox(height: 10),
          VideoProgressIndicator(ctl, allowScrubbing: true, colors: VideoProgressColors(playedColor: c.ink, backgroundColor: c.sunk)),
        ],
        const SizedBox(height: 14),
        Text('${crKindName(crS(widget.item['kind']))} · ${crWhen(widget.item['created'])}', style: HoolaType.small(c)),
      ],
    );
  }
}

class _TextView extends StatefulWidget {
  const _TextView({required this.store, required this.item});
  final CreateStore store;
  final Map<String, dynamic> item;
  @override
  State<_TextView> createState() => _TextViewState();
}

class _TextViewState extends State<_TextView> {
  String? _text;
  @override
  void initState() {
    super.initState();
    widget.store.app.api?.createItemBytes(crS(widget.item['id'])).then((b) {
      if (mounted) setState(() => _text = b == null ? 'This file is no longer on Hoola.' : utf8.decode(b, allowMalformed: true));
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrPage(
      title: crS(widget.item['title']),
      trailing: CrRoundButton(glyph: CrGlyph.share, label: 'Save or share', onTap: () => crShareItem(context, widget.store.app, widget.item)),
      children: [
        CrCard(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
          child: _text == null
              ? Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2)))
              : SelectableText(_text!,
                  style: TextStyle(fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 15, height: 1.6, color: c.ink)),
        ),
      ],
    );
  }
}

// ------------------------------------------------------------------------------------------------ 11 · My creations
const _kinds = [('All', ''), ('Pictures', 'image'), ('Cast', 'cast'), ('Songs', 'song'), ('Voice-overs', 'voice'), ('Dubs', 'dub'), ('Scripts', 'script')];

class CreateLibrary extends StatefulWidget {
  const CreateLibrary({super.key, required this.store});
  final CreateStore store;
  @override
  State<CreateLibrary> createState() => _CreateLibraryState();
}

class _CreateLibraryState extends State<CreateLibrary> {
  final _q = TextEditingController();
  String _kind = '', _sort = 'Newest first';
  bool _select = false, _busy = false;
  final Set<String> _picked = {};

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _list {
    final q = _q.text.trim().toLowerCase();
    final l = widget.store.items.where((i) => (_kind.isEmpty || i['kind'] == _kind) && (q.isEmpty || crS(i['title']).toLowerCase().contains(q))).toList();
    if (_sort == 'Oldest first') l.sort((a, b) => crInt(a['created']).compareTo(crInt(b['created'])));
    if (_sort == 'Name A–Z') l.sort((a, b) => crS(a['title']).toLowerCase().compareTo(crS(b['title']).toLowerCase()));
    return l;
  }

  Future<void> _delete() async {
    if (_picked.isEmpty || !await crConfirmDelete(context, _picked.length)) return;
    setState(() => _busy = true);
    var gone = 0;
    for (final id in _picked.toList()) {
      try {
        await widget.store.delete(id);
        _picked.remove(id);
        gone++;
      } catch (e) {
        if (mounted) crToast(context, crError(e));
      }
    }
    if (mounted) {
      setState(() => _busy = false);
      crToast(context, gone == 1 ? 'Deleted.' : 'Deleted $gone creations.');
    }
  }

  Future<void> _save() async {
    final items = widget.store.items.where((i) => _picked.contains(i['id'])).toList();
    for (final it in items) {
      if (!mounted) return;
      await crShareItem(context, widget.store.app, it);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final store = widget.store;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        final list = _list;
        return CrPage(
          hue: CrHue.video, title: 'My creations',
          onRefresh: () => store.load(quiet: true),
          trailing: TextButton(
            onPressed: () => setState(() {
              _select = !_select;
              _picked.clear();
            }),
            child: Text(_select ? 'Done' : 'Select'),
          ),
          action: _select
              ? Row(children: [
                  CrQuiet(label: 'Delete', color: c.bad, onTap: _picked.isEmpty || _busy ? null : _delete),
                  const SizedBox(width: 10),
                  Expanded(
                    child: CrMain(
                      label: _picked.isEmpty ? 'Tick what to save' : 'Save ${_picked.length} to phone',
                      busy: _busy,
                      onTap: _picked.isEmpty ? null : _save,
                    ),
                  ),
                ])
              : null,
          children: [
            TextField(
              controller: _q,
              onChanged: (_) => setState(() {}),
              style: HoolaType.body(c),
              decoration: InputDecoration(
                hintText: 'Search your creations',
                prefixIcon: Padding(padding: const EdgeInsets.all(14), child: CrIcon(CrGlyph.search, size: 18, color: c.ink3)),
                filled: true,
                fillColor: crWash(c),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 14),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final k in _kinds) CrChip(label: k.$1, on: k.$2 == _kind, onTap: () => setState(() => _kind = k.$2)),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: Text(_select ? '${_picked.length} chosen' : '${list.length} ${list.length == 1 ? 'item' : 'items'}',
                    style: HoolaType.small(c).copyWith(fontSize: 13)),
              ),
              TextButton(
                onPressed: () async {
                  final v = await crPick(context, 'Sort', const ['Newest first', 'Oldest first', 'Name A–Z'], _sort);
                  if (v != null) setState(() => _sort = v);
                },
                child: Text(_sort),
              ),
            ]),
            const SizedBox(height: 6),
            if (list.isEmpty)
              CrNote(store.items.isEmpty ? 'What you make in Create is kept here.' : 'Nothing matches. Try another word or kind.',
                  glyph: CrGlyph.info)
            else
              // v0.913 a wall of two columns of different heights, like a gallery
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                for (final col in [0, 1]) ...[
                  if (col == 1) const SizedBox(width: 10),
                  Expanded(
                    child: Column(children: [
                  for (var i = col; i < list.length; i += 2)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _Tile(
                        height: const [214.0, 176.0, 236.0, 192.0, 168.0, 224.0][i % 6],
                        item: list[i],
                        store: store,
                        selecting: _select,
                        on: _picked.contains(list[i]['id']),
                        onTap: () {
                          final it = list[i];
                          if (_select) {
                            HapticFeedback.selectionClick();
                            setState(() => _picked.contains(it['id']) ? _picked.remove(it['id']) : _picked.add(crS(it['id'])));
                          } else {
                            crOpenItem(context, store, it);
                          }
                        },
                        onLong: () => setState(() {
                          _select = true;
                          _picked.add(crS(list[i]['id']));
                        }),
                      ),
                    ),
                    ]),
                  ),
                ],
              ]),
          ],
        );
      },
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({required this.store, required this.item, required this.selecting, required this.on, required this.onTap, required this.onLong,
      this.height = 200});
  final CreateStore store;
  final Map<String, dynamic> item;
  final bool selecting, on;
  final VoidCallback onTap, onLong;
  final double height;
  @override
  Widget build(BuildContext context) {
    final kind = crS(item['kind']);
    final glyph = switch (kind) {
      'song' => CrGlyph.music,
      'voice' => CrGlyph.voice,
      'dub' => CrGlyph.video,
      'script' => CrGlyph.pen,
      'cast' => CrGlyph.cast,
      _ => CrGlyph.image,
    };
    final pic = crS(item['mime']).startsWith('image/');
    return Semantics(
      button: true,
      selected: on,
      label: '${crKindName(kind)}: ${crS(item['title'])}, ${crWhen(item['created'])}',
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onLongPress: onLong,
        child: SizedBox(
          width: double.infinity,
          height: height,
          child: CrArtCard(
            art: pic
                ? CrItemImage(app: store.app, item: item, cache: 480)
                : Stack(fit: StackFit.expand, children: [
                    CrScene(crSceneFor(item['id'])),
                    Center(child: CrIcon(glyph, size: 30, color: Colors.white)),
                  ]),
            badge: CrBadge(crKindName(kind)),
            title: crS(item['title']),
            line: crWhen(item['created']),
            picked: on,
            label: '${crKindName(kind)}: ${crS(item['title'])}',
            trailing: selecting
                ? Container(
                    width: 26,
                    height: 26,
                    decoration: BoxDecoration(
                      color: on ? Colors.white : Colors.white.withOpacity(.2),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white.withOpacity(.8), width: 1.5),
                    ),
                    alignment: Alignment.center,
                    child: on ? const CrIcon(CrGlyph.check, size: 13, color: CreateHues.onHue) : null,
                  )
                : null,
            onTap: onTap,
          ),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ 12 · Brand kit
Color? crHex(String s) {
  final h = s.replaceAll('#', '').trim();
  if (h.length != 6) return null;
  final v = int.tryParse(h, radix: 16);
  return v == null ? null : Color.fromARGB(255, (v >> 16) & 255, (v >> 8) & 255, v & 255);
}

const _roles = [('primary', 'Main'), ('accent', 'Accent'), ('secondary', 'Second'), ('light', 'Light'), ('dark', 'Text')];
const _swatches = ['#7A1F2B', '#B3261E', '#E8A33D', '#F5A623', '#1F7A52', '#0F766E', '#1565C0', '#3949AB', '#6D28D9', '#BE185D',
  '#3A1208', '#1B1A17', '#57554F', '#FFF6E9', '#FAF9F6', '#FFFFFF'];

class CreateBrand extends StatefulWidget {
  const CreateBrand({super.key, required this.store});
  final CreateStore store;
  @override
  State<CreateBrand> createState() => _CreateBrandState();
}

class _CreateBrandState extends State<CreateBrand> {
  late final Map<String, dynamic> _k = widget.store.kit;
  late final _name = TextEditingController(text: crS(_k['name']));
  late final _tag = TextEditingController(text: crS(_k['tagline']));
  late final _tone = TextEditingController(text: crS(_k['tone']));
  late final _phone = TextEditingController(text: crS(crMap(_k['contact'])['phone']));
  late final _web = TextEditingController(text: crS(crMap(_k['contact'])['website']));
  late final Map<String, String> _cols = {for (final e in crMap(_k['colors']).entries) e.key: '${e.value}'};
  late String _font = crS(_k['font']);
  List<int>? _logo;
  bool _saving = false, _uploading = false;

  @override
  void initState() {
    super.initState();
    if (_k['logo'] == true) {
      widget.store.app.api?.brandBytes('/api/brand/logo?t=${DateTime.now().millisecondsSinceEpoch}').then((b) {
        if (mounted) setState(() => _logo = b);
      }).catchError((Object _) {});
    }
    for (final t in [_name, _tag, _tone, _phone, _web]) {
      t.addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    for (final t in [_name, _tag, _tone, _phone, _web]) {
      t.dispose();
    }
    super.dispose();
  }

  Color _col(String role, Color fallback) => crHex(_cols[role] ?? '') ?? fallback;

  Future<void> _pickLogo() async {
    final picked = await pickAttachmentsOfType(context, FileType.image);
    if (picked.isEmpty || !mounted) return;
    final f = picked.first;
    setState(() => _uploading = true);
    try {
      final r = await widget.store.app.api!.brandLogo(f.name, f.bytes, cleanBg: true);
      final k = crMap(r['kit']);
      setState(() {
        _logo = f.bytes;
        for (final e in crMap(k['colors']).entries) {
          _cols[e.key] = '${e.value}';
        }
      });
      if (mounted) crToast(context, 'Logo saved. Colours read from it.');
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _uploading = false);
  }

  Future<void> _pickColour(String role, String label) async {
    final c = HoolaColors.of(context);
    final hex = TextEditingController(text: _cols[role] ?? '');
    final v = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.viewInsetsOf(ctx).bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('$label colour', style: HoolaType.heading(c)),
          const SizedBox(height: 14),
          Wrap(spacing: 10, runSpacing: 10, children: [
            for (final s in _swatches)
              Semantics(
                button: true,
                label: s,
                child: GestureDetector(
                  onTap: () => Navigator.of(ctx).pop(s),
                  child: Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(color: crHex(s), shape: BoxShape.circle, border: Border.all(color: c.line, width: 1.5)),
                  ),
                ),
              ),
          ]),
          const SizedBox(height: 14),
          TextField(
            controller: hex,
            decoration: const InputDecoration(labelText: 'Or a colour code', hintText: '#1565C0'),
            onSubmitted: (t) => Navigator.of(ctx).pop(t.trim()),
          ),
          const SizedBox(height: 14),
          CrMain(label: 'Use this code', height: 52, onTap: () => Navigator.of(ctx).pop(hex.text.trim())),
        ]),
      ),
    );
    hex.dispose();
    if (v == null || v.isEmpty) return;
    final h = v.startsWith('#') ? v : '#$v';
    if (crHex(h) == null) {
      if (mounted) crToast(context, 'Use a six-letter colour code like #1565C0.');
      return;
    }
    setState(() => _cols[role] = h.toUpperCase());
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await widget.store.saveKit({
        'name': _name.text.trim(),
        'tagline': _tag.text.trim(),
        'tone': _tone.text.trim(),
        if (_font.isNotEmpty) 'font': _font,
        'colors': _cols,
        'contact': {'phone': _phone.text.trim(), 'website': _web.text.trim()},
      });
      if (mounted) crToast(context, 'Brand kit saved. New posters use it.');
    } catch (e) {
      if (mounted) crToast(context, crError(e));
    }
    if (mounted) setState(() => _saving = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final main = _col('primary', c.ink), accent = _col('accent', c.warn), light = _col('light', c.surface), text = _col('dark', c.ink);
    final onMain = main.computeLuminance() > .5 ? text : light;
    final fonts = crMap(_k['fonts']);
    InputDecoration field(String label, [String hint = '']) => InputDecoration(
          labelText: label,
          hintText: hint,
          filled: true,
          fillColor: c.surface,
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.line)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.ink)),
        );
    return CrPage(
      hue: CrHue.film, title: 'Brand kit',
      action: CrMain(label: 'Save brand kit', busy: _saving, onTap: _save, glyph: CrGlyph.check),
      children: [
        Semantics(
          label: 'Live preview of a poster with your brand',
          child: ClipRRect(
            borderRadius: BorderRadius.circular(22),
            child: Container(
              color: main,
              padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(color: accent, shape: BoxShape.circle),
                    clipBehavior: Clip.antiAlias,
                    alignment: Alignment.center,
                    child: _logo != null
                        ? Image.memory(Uint8List.fromList(_logo!), fit: BoxFit.cover)
                        : Text(_name.text.trim().isEmpty ? 'H' : _name.text.trim().substring(0, 1).toUpperCase(),
                            style: TextStyle(fontFamily: HoolaFont.serif, fontSize: 17, color: main)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(_name.text.trim().isEmpty ? 'Your business' : _name.text.trim(), maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontFamily: HoolaFont.sans, fontSize: 15, fontWeight: FontWeight.w600, color: onMain)),
                  ),
                ]),
                const SizedBox(height: 14),
                Text(_tag.text.trim().isEmpty ? 'Your tagline goes here' : _tag.text.trim(),
                    style: TextStyle(fontFamily: HoolaFont.serif, fontSize: 24, height: 1.2, color: onMain)),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
                  decoration: BoxDecoration(color: accent, borderRadius: BorderRadius.circular(18)),
                  child: Text(_phone.text.trim().isEmpty ? 'Call us' : 'Call ${_phone.text.trim()}',
                      style: TextStyle(fontFamily: HoolaFont.sans, fontSize: 13.5, fontWeight: FontWeight.w600,
                          color: accent.computeLuminance() > .5 ? text : light)),
                ),
              ]),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text('Live preview · every new poster uses this', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
        crGap,
        const CrLabel('Logo', note: 'A plain background is removed for you'),
        CrCard(
          child: Row(children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(16), border: Border.all(color: c.line)),
              clipBehavior: Clip.antiAlias,
              alignment: Alignment.center,
              child: _logo != null ? Image.memory(Uint8List.fromList(_logo!), fit: BoxFit.contain) : CrIcon(CrGlyph.brand, size: 24, color: c.ink3),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(_logo == null ? 'No logo yet' : 'Your logo', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
            ),
            CrQuiet(label: _uploading ? 'Adding…' : (_logo == null ? 'Add' : 'Change'), height: 48, onTap: _uploading ? null : _pickLogo),
          ]),
        ),
        crGap,
        const CrLabel('Business'),
        TextField(controller: _name, style: HoolaType.body(c), decoration: field('Name', 'Sharma Sweets')),
        const SizedBox(height: 10),
        TextField(controller: _tag, style: HoolaType.body(c), decoration: field('Tagline', 'Akola ki asli mithaas, 1978 se')),
        const SizedBox(height: 10),
        TextField(controller: _tone, style: HoolaType.body(c), decoration: field('How you talk', 'Warm, family, a little playful')),
        const SizedBox(height: 10),
        TextField(controller: _phone, keyboardType: TextInputType.phone, style: HoolaType.body(c), decoration: field('Phone on posters')),
        const SizedBox(height: 10),
        TextField(controller: _web, keyboardType: TextInputType.url, style: HoolaType.body(c), decoration: field('Website')),
        crGap,
        const CrLabel('Colours', note: 'Tap one to change it'),
        CrCard(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
          child: Row(children: [
            for (final r in _roles)
              Expanded(
                child: Semantics(
                  button: true,
                  label: '${r.$2} colour ${_cols[r.$1] ?? ''}',
                  excludeSemantics: true,
                  onTap: () => _pickColour(r.$1, r.$2),
                  child: GestureDetector(
                    onTap: () => _pickColour(r.$1, r.$2),
                    child: Column(children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(color: _col(r.$1, c.sunk), shape: BoxShape.circle, border: Border.all(color: c.line, width: 1.5)),
                      ),
                      const SizedBox(height: 6),
                      Text(r.$2, style: HoolaType.small(c).copyWith(fontSize: 12, color: c.ink2)),
                    ]),
                  ),
                ),
              ),
          ]),
        ),
        if (fonts.isNotEmpty) ...[
          crGap,
          const CrLabel('Lettering'),
          CrTiles(
            options: [for (final f in fonts.values) '$f'],
            picked: crS(fonts[_font]),
            cols: 2,
            onPick: (v) => setState(() => _font = fonts.entries.firstWhere((e) => '${e.value}' == v).key),
          ),
        ],
        const SizedBox(height: 4),
      ],
    );
  }
}

// ------------------------------------------------------------------------------------------------ 13 · Hoola Cinema
const _cinemaTools = [
  ('Cinema still', 'A picture with a real camera and lens look', CrGlyph.camera),
  ('Motion transfer', 'Your character copies the moves in a clip', CrGlyph.people),
  ('Character swap', 'Put your saved character into a video', CrGlyph.cast),
  ('Item swap', 'Change a product or object in a clip', CrGlyph.layers),
  ('Restyle', '16 looks, from anime to oil painting', CrGlyph.brand),
  ('Talking photo', 'A photo speaks your words in a Hoola voice', CrGlyph.voice),
  ('Lip sync', 'Match a video’s lips to new audio', CrGlyph.mic),
  ('Picture to video', 'Bring one still picture to life', CrGlyph.video),
  ('Content factory', 'One brief, up to 6 scenes in one go', CrGlyph.grid),
  ('Characters', 'Faces you saved, with their yes on record', CrGlyph.people),
];

class CreateCinema extends StatefulWidget {
  const CreateCinema({super.key, required this.store});
  final CreateStore store;
  @override
  State<CreateCinema> createState() => _CreateCinemaState();
}

class _CreateCinemaState extends State<CreateCinema> {
  Map<String, dynamic> _o = const {};
  String _err = '';
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final d = CreateStore.debugData;
    if (d != null) {
      setState(() {
        _o = crMap(d['cinema']);
        _loaded = true;
      });
      return;
    }
    final api = widget.store.app.api;
    if (api == null) return;
    try {
      final r = crMap(await api.call('GET', '/api/cinema'));
      if (mounted) setState(() {
        _o = r;
        _loaded = true;
        _err = '';
      });
    } catch (e) {
      if (mounted) setState(() {
        _loaded = true;
        _err = crError(e);
      });
    }
  }

  void _open(String tool) =>
      hoolaOpenConsole(context, widget.store.app, '/console/?v=creative&a=cinema', 'Hoola Cinema · $tool').then((_) => _load());

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final keyOk = _o['key_set'] == true;
    final today = crMap(_o['today']);
    final jobs = crList(_o['jobs']);
    return CrPage(
      hue: CrHue.song, title: 'Hoola Cinema',
      onRefresh: _load,
      children: [
        const CrIntro('Change a video like a film studio',
            'Move a photo, swap in a face you have a yes for, restyle a clip or make a talking photo.'),
        crGap,
        const CrNote('Before a job starts, tick that you own the video. A real person’s face needs their recorded yes. '
            'Up to 20 jobs a day.'),
        if (_loaded && (_err.isNotEmpty || !keyOk)) ...[
          const SizedBox(height: 12),
          CrNote(
              _err.isNotEmpty
                  ? (_err.contains('404') || _err.toLowerCase().contains('not found')
                      ? 'Hoola Cinema is not switched on on this server yet.'
                      : _err)
                  : 'Hoola Cinema needs its engine key on the server first. The owner adds it once in the server settings.',
              glyph: CrGlyph.info),
        ],
        if (keyOk && today.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('${crInt(today['used'])} of ${crInt(today['limit']) == 0 ? 20 : crInt(today['limit'])} jobs used today',
              style: HoolaType.small(c)),
        ],
        crGap,
        LayoutBuilder(builder: (context, box) {
          final w = (box.maxWidth - 12) / 2;
          return Wrap(spacing: 12, runSpacing: 12, children: [
            for (final t in _cinemaTools)
              SizedBox(
                width: w,
                child: Semantics(
                  button: true,
                  label: '${t.$1}. ${t.$2}',
                  excludeSemantics: true,
                  onTap: () => _open(t.$1),
                  child: CrCard(
                    onTap: () => _open(t.$1),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 116),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        CrDisc(t.$3),
                        const SizedBox(height: 10),
                        Text(t.$1, style: HoolaType.title(c).copyWith(fontSize: 14.5)),
                        const SizedBox(height: 2),
                        Text(t.$2, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                      ]),
                    ),
                  ),
                ),
              ),
          ]);
        }),
        if (jobs.isNotEmpty) ...[
          crGap,
          const CrLabel('Recent jobs'),
          CrCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(children: [
              for (final (i, j) in jobs.take(8).indexed) ...[
                if (i > 0) Divider(height: 1, color: c.line),
                ListTile(
                  minVerticalPadding: 12,
                  leading: Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(color: crTone(c, j['id']), borderRadius: BorderRadius.circular(12)),
                  ),
                  title: Text(crS(j['title']).isEmpty ? crS(j['tool']) : crS(j['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                  subtitle: Text(crS(j['state']).isEmpty ? crS(j['status']) : crS(j['state']), style: HoolaType.small(c)),
                  onTap: () => _open('Recent jobs'),
                ),
              ],
            ]),
          ),
        ],
        const SizedBox(height: 14),
        Text('Cinema’s tools open in Hoola’s Cinema page, already signed in.', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
      ],
    );
  }
}
