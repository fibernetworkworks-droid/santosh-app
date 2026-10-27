// v0.141 Hoola 3D Studio: real Blender on the server (locked box). Chat / call card + Profile screen.
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import '../native.dart';
import '../state.dart';
import 'attach.dart';
import 'glass.dart';
import 'video_editor.dart' show VideoPlayScreen;

const _busyStates = {'queued', 'writing', 'building', 'rendering', 'checking'};
const _mimes = {
  'glb': 'model/gltf-binary',
  'stl': 'model/stl',
  'obj': 'text/plain',
  'fbx': 'application/octet-stream',
  'usdz': 'model/vnd.usdz+zip',
  'blend': 'application/octet-stream',
  'png': 'image/png',
  'mp4': 'video/mp4',
};
const _fmtSay = {
  'glb': 'GLB (web / AR)',
  'stl': 'STL (3D print)',
  'obj': 'OBJ',
  'fbx': 'FBX (games / 3D apps)',
  'usdz': 'USDZ (iPhone AR)',
  'blend': 'Blender file',
};

String _stageSay(Map<String, dynamic> v) {
  final st = '${v['status'] ?? ''}';
  if (st == 'done') return 'Taiyaar';
  if (st == 'failed') return 'Nahi ban paya';
  if (st == 'cancelled') return 'Rok diya';
  final s = '${v['stage'] ?? ''}';
  return s.isNotEmpty ? s : 'Line mein';
}

class Blender3dCard extends StatefulWidget {
  const Blender3dCard({super.key, required this.v, required this.app, this.inPage = false});
  final Map<String, dynamic> v;
  final Santosh app;
  final bool inPage;
  @override
  State<Blender3dCard> createState() => _Blender3dCardState();
}

class _Blender3dCardState extends State<Blender3dCard> {
  final _ctl = TextEditingController();
  bool _busy = false;
  int _view = 0;

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  void _say(String t) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  String _abs(String? p) => widget.app.api?.absolute(p ?? '') ?? '';

  Future<String?> _local(String url, String name) async {
    final api = widget.app.api;
    if (api == null || url.isEmpty) return null;
    final bytes = await api.brandBytes(url);
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/${name.replaceAll(RegExp(r'[^\w\-. ()]'), '_')}');
    await f.writeAsBytes(bytes);
    return f.path;
  }

  Future<void> _run(Future<void> Function() job) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await job();
    } catch (e) {
      _say('Nahi ho paya: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _share(String url, String name) => _run(() async {
        final p = await _local(url, name);
        if (p == null) return;
        final ext = name.split('.').last.toLowerCase();
        final err = await Native.shareFile(p, mime: _mimes[ext] ?? 'application/octet-stream', title: name);
        if (err != null) _say(err);
      });

  Future<void> _saveImage(String url, String name) => _run(() async {
        final p = await _local(url, name);
        if (p == null) return;
        final err = await Native.saveImage(p, name);
        _say(err ?? 'Gallery mein save ho gayi (Pictures/Hoola)');
      });

  Future<void> _change({String words = '', Map<String, dynamic> extra = const {}}) => _run(() async {
        final api = widget.app.api;
        final id = widget.v['id'];
        if (api == null || id == null) return;
        await api.call('POST', '/api/blender3d/$id/change', body: {'words': words, ...extra});
        _ctl.clear();
        _say(words.isEmpty ? 'Nayi files ban rahi hain' : 'Badlav shuru: naya version aayega');
      });

  Future<void> _cancel() => _run(() async {
        final api = widget.app.api;
        if (api == null) return;
        await api.call('POST', '/api/blender3d/${widget.v['id']}/cancel');
      });

  void _open(String url) {
    Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => Scaffold(
              backgroundColor: Colors.black,
              appBar: AppBar(backgroundColor: Colors.black, foregroundColor: Colors.white, title: Text('${widget.v['title'] ?? '3D'}')),
              body: InteractiveViewer(maxScale: 5, child: Center(child: Image.network(url))),
            )));
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = '${v['status'] ?? ''}';
    final busy = _busyStates.contains(status);
    final renders = ((v['renders'] as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    if (_view >= renders.length) _view = 0;
    final exports = Map<String, dynamic>.from((v['exports'] as Map?) ?? const {});
    final stats = Map<String, dynamic>.from((v['stats'] as Map?) ?? const {});
    final pc = v['print_check'] is Map ? Map<String, dynamic>.from(v['print_check'] as Map) : null;
    final video = v['video'] is Map ? Map<String, dynamic>.from(v['video'] as Map) : null;
    final pct = (v['pct'] as num?)?.toDouble() ?? 0;
    final size = (stats['size_m'] as List?)?.map((e) => ((e as num) * 100).toStringAsFixed(1)).join(' x ');
    final img = renders.isEmpty ? '' : _abs(renders[_view]['url'] as String?);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.view_in_ar_rounded, color: C.teal),
            const SizedBox(width: 10),
            Expanded(
              child: Text('${v['number'] ?? ''} · ${v['title'] ?? '3D model'}',
                  maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
            ),
            if ((v['version'] as num? ?? 0) > 0) Text('v${v['version']}', style: const TextStyle(color: C.faint, fontSize: 12)),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            Expanded(
                child: Text(_stageSay(v),
                    style: TextStyle(color: status == 'failed' ? C.bad : (status == 'done' ? C.ok : C.muted), fontSize: 12.5))),
            if (busy) TextButton(onPressed: _busy ? null : _cancel, child: const Text('Rok do')),
          ]),
          if (busy) ...[
            const SizedBox(height: 4),
            LinearProgressIndicator(value: pct > 0 ? pct / 100 : null, minHeight: 3),
          ],
          if (status == 'failed' && '${v['error'] ?? ''}'.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text('${v['error']}', style: const TextStyle(color: C.faint, fontSize: 12)),
          ],
          if (img.isNotEmpty) ...[
            const SizedBox(height: 10),
            GestureDetector(
              onTap: () => _open(img),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 380),
                  child: Image.network(img,
                      fit: BoxFit.contain,
                      loadingBuilder: (c, w, p) =>
                          p == null ? w : const SizedBox(height: 220, child: Center(child: CircularProgressIndicator())),
                      errorBuilder: (c, e, s) => Container(
                          height: 100,
                          alignment: Alignment.center,
                          child: const Text('Picture ka link purana ho gaya', style: TextStyle(color: C.faint)))),
                ),
              ),
            ),
            if (renders.length > 1) ...[
              const SizedBox(height: 6),
              Wrap(spacing: 6, children: [
                for (var i = 0; i < renders.length; i++)
                  ChoiceChip(
                    label: Text('${renders[i]['view']}'.replaceAll('_', ' ')),
                    selected: i == _view,
                    onSelected: (_) => setState(() => _view = i),
                  ),
              ]),
            ],
            const SizedBox(height: 4),
            const Text('AI se bana · Hoola (Blender)', style: TextStyle(color: C.faint, fontSize: 11)),
          ],
          if (size != null || stats['tris'] != null) ...[
            const SizedBox(height: 6),
            Text(
                [
                  if (size != null) 'Size $size cm',
                  if (stats['tris'] != null) '${stats['tris']} triangles',
                  if (stats['count'] != null) '${stats['count']} hisse',
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12)),
          ],
          if (pc != null) ...[
            const SizedBox(height: 4),
            Text('${pc['say'] ?? ''}', style: TextStyle(color: pc['closed'] == true ? C.ok : C.warn, fontSize: 12)),
          ],
          if ('${v['notes'] ?? ''}'.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text('${v['notes']}', style: const TextStyle(color: C.faint, fontSize: 12)),
          ],
          if (renders.isNotEmpty || exports.isNotEmpty || video != null) ...[
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 6, children: [
              if (renders.isNotEmpty)
                OutlinedButton.icon(
                    onPressed: _busy ? null : () => _saveImage(renders[_view]['url'] as String? ?? '', '${v['number']}.png'),
                    icon: const Icon(Icons.download_rounded, size: 18),
                    label: const Text('Save')),
              if (renders.isNotEmpty)
                OutlinedButton.icon(
                    onPressed: _busy ? null : () => _share(renders[_view]['url'] as String? ?? '', '${v['number']}.png'),
                    icon: const Icon(Icons.share_rounded, size: 18),
                    label: const Text('Bhejo')),
              if (video != null)
                OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => VideoPlayScreen(url: _abs(video['url'] as String?), title: '${v['title'] ?? '3D'} · 360°'))),
                    icon: const Icon(Icons.threesixty_rounded, size: 18),
                    label: const Text('360° video')),
              for (final e in exports.entries)
                if (e.value is Map && (e.value as Map)['url'] != null)
                  ActionChip(
                    avatar: const Icon(Icons.file_present_rounded, size: 16),
                    label: Text(_fmtSay[e.key] ?? e.key.toUpperCase()),
                    onPressed: _busy ? null : () => _share('${(e.value as Map)['url']}', '${(e.value as Map)['name'] ?? '${v['number']}.${e.key}'}'),
                  ),
            ]),
          ],
          if (!busy && (v['version'] as num? ?? 0) > 0) ...[
            const SizedBox(height: 8),
            Row(children: [
              Expanded(
                child: TextField(
                  controller: _ctl,
                  minLines: 1,
                  maxLines: 3,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (t) => t.trim().isEmpty ? null : _change(words: t.trim()),
                  decoration: const InputDecoration(isDense: true, hintText: 'Badlav bolo: "handle bada karo"', border: OutlineInputBorder()),
                ),
              ),
              IconButton(
                  onPressed: _busy ? null : () => _ctl.text.trim().isEmpty ? null : _change(words: _ctl.text.trim()),
                  icon: const Icon(Icons.send_rounded, color: C.teal)),
            ]),
            if (widget.inPage) ...[
              const SizedBox(height: 6),
              Wrap(spacing: 6, runSpacing: 4, children: [
                ActionChip(label: const Text('Sharp render'), onPressed: _busy ? null : () => _change(extra: {'quality': 'final'})),
                ActionChip(label: const Text('360° video'), onPressed: _busy ? null : () => _change(extra: {'turntable': true})),
                ActionChip(
                    label: const Text('Saare angle'),
                    onPressed: _busy ? null : () => _change(extra: {'views': ['three_quarter', 'front', 'side', 'top']})),
                ActionChip(
                    label: const Text('Saari files'),
                    onPressed: _busy ? null : () => _change(extra: {'exports': ['glb', 'stl', 'obj', 'fbx', 'usdz', 'blend']})),
              ]),
            ],
          ],
        ]),
      ),
    );
  }
}

class Blender3dScreen extends StatefulWidget {
  const Blender3dScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<Blender3dScreen> createState() => _Blender3dScreenState();
}

class _Blender3dScreenState extends State<Blender3dScreen> {
  Map<String, dynamic>? _home;
  String? _err;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    setState(() => _loading = true);
    try {
      final r = await api.call('GET', '/api/blender3d');
      if (mounted) setState(() => _home = Map<String, dynamic>.from(r as Map));
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _new() async {
    final made = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => _NewBlender3d(app: widget.app)));
    if (made == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final health = Map<String, dynamic>.from((_home?['health'] as Map?) ?? const {});
    final items = ((_home?['projects'] as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    return Scaffold(
      appBar: AppBar(title: Text('${widget.app.aName} · 3D Studio')),
      floatingActionButton: FloatingActionButton.extended(
          onPressed: _new, icon: const Icon(Icons.add_rounded), label: const Text('Naya 3D')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Asli Blender, Hoola ke haath mein',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 6),
              const Text(
                  'Bata dijiye kya banana hai: product mockup aapke label ke saath, dukaan / stall ka layout, gift, trophy, '
                  'name plate, 3D print ka part. Render, 360° video aur GLB / STL / USDZ files aapke paas aati hain.',
                  style: TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              if (_home != null)
                Text(
                    health['installed'] == true
                        ? (health['no_network'] == true
                            ? 'Blender taiyaar · har kaam band dibbe mein (internet nahi, aapki chaabiyan nahi)'
                            : 'Blender taiyaar · code check + band dibba')
                        : 'Blender abhi server par install nahi hai (admin: deploy/setup_blender.sh)',
                    style: TextStyle(color: health['installed'] == true ? C.ok : C.warn, fontSize: 12)),
            ]),
          ),
          const SizedBox(height: 12),
          if (_loading && _home == null) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
          if (_err != null && _home == null) Text(_err!, style: const TextStyle(color: C.bad)),
          if (_home != null && items.isEmpty)
            const Padding(
                padding: EdgeInsets.all(20),
                child: Text('Abhi koi 3D nahi bana. "Naya 3D" dabaiye ya chat mein boliye.', style: TextStyle(color: C.faint))),
          for (final p in items)
            InkWell(
              onTap: () async {
                await Navigator.of(context).push(MaterialPageRoute(builder: (_) => _Blender3dPage(app: widget.app, id: '${p['id']}')));
                _load();
              },
              child: Blender3dCard(key: ValueKey('b3l${p['id']}${p['version']}${p['status']}'), v: p, app: widget.app),
            ),
        ]),
      ),
    );
  }
}

class _Blender3dPage extends StatefulWidget {
  const _Blender3dPage({required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<_Blender3dPage> createState() => _Blender3dPageState();
}

class _Blender3dPageState extends State<_Blender3dPage> {
  Map<String, dynamic>? _v;
  String? _err;
  bool _showCode = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    try {
      final r = await api.call('GET', '/api/blender3d/${widget.id}');
      if (mounted) setState(() => _v = Map<String, dynamic>.from(r as Map));
      if (_busyStates.contains('${_v?['status']}')) {
        await Future.delayed(const Duration(seconds: 4));
        if (mounted) _load();
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _delete() async {
    final api = widget.app.api;
    if (api == null) return;
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: const Text('Ye 3D hata dein?'),
              content: const Text('Saare versions aur files hat jayengi.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
                TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, hatao')),
              ],
            ));
    if (ok != true) return;
    await api.call('DELETE', '/api/blender3d/${widget.id}');
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final objects = ((v?['objects'] as List?) ?? const []).whereType<Map>().toList();
    final history = ((v?['history'] as List?) ?? const []).whereType<Map>().toList();
    return Scaffold(
      appBar: AppBar(title: Text('${v?['number'] ?? '3D'}'), actions: [
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        IconButton(onPressed: _delete, icon: const Icon(Icons.delete_outline_rounded)),
      ]),
      body: v == null
          ? Center(child: _err != null ? Text(_err!, style: const TextStyle(color: C.bad)) : const CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Blender3dCard(key: ValueKey('b3p${v['version']}${v['status']}'), v: v, app: widget.app, inPage: true),
              if ('${v['brief'] ?? ''}'.isNotEmpty)
                Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text('Aapne kaha: ${v['brief']}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
              if (objects.isNotEmpty)
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Model ke hisse', style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 6),
                    for (final o in objects.take(30))
                      Text(
                          '${o['name']} · ${o['type']}${o['tris'] != null ? ' · ${o['tris']} tri' : ''}'
                          '${(o['open_edges'] ?? 0) is num && (o['open_edges'] as num) > 0 ? ' · khule kinare ${o['open_edges']}' : ''}',
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
              const SizedBox(height: 10),
              if (history.length > 1)
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Versions', style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 6),
                    for (final h in history.reversed)
                      Text('v${h['n']} · ${'${h['words'] ?? ''}'.isEmpty ? 'pehla' : h['words']}',
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
              const SizedBox(height: 10),
              if ('${v['script'] ?? ''}'.isNotEmpty)
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    InkWell(
                      onTap: () => setState(() => _showCode = !_showCode),
                      child: Row(children: [
                        const Icon(Icons.code_rounded, size: 18, color: C.faint),
                        const SizedBox(width: 8),
                        const Expanded(child: Text('Blender script (jaanch ke baad chali)', style: TextStyle(fontWeight: FontWeight.w600))),
                        Icon(_showCode ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: C.faint),
                      ]),
                    ),
                    if (_showCode) ...[
                      const SizedBox(height: 8),
                      SelectableText('${v['script']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5, color: C.muted)),
                    ],
                  ]),
                ),
            ]),
    );
  }
}

class _NewBlender3d extends StatefulWidget {
  const _NewBlender3d({required this.app});
  final Santosh app;
  @override
  State<_NewBlender3d> createState() => _NewBlender3dState();
}

class _NewBlender3dState extends State<_NewBlender3d> {
  final _brief = TextEditingController();
  final Set<String> _exports = {'glb'};
  final List<Map<String, String>> _photos = [];
  String _quality = 'preview';
  String _aspect = '1:1';
  bool _print = false;
  bool _turn = false;
  bool _busy = false;

  @override
  void dispose() {
    _brief.dispose();
    super.dispose();
  }

  void _say(String t) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _addPhoto() async {
    final api = widget.app.api;
    final conv = widget.app.conversationId;
    if (api == null || conv == null) return;
    final picked = await pickAttachmentsOfType(context, FileType.image);
    for (final f in picked.take(6 - _photos.length)) {
      try {
        final r = await api.chatFile(conv, f.name, f.bytes);
        setState(() => _photos.add({'id': '${r['file_id']}', 'name': f.name}));
      } catch (e) {
        _say('Photo nahi gayi: $e');
      }
    }
  }

  Future<void> _go() async {
    final api = widget.app.api;
    final b = _brief.text.trim();
    if (api == null) return;
    if (b.length < 6) {
      _say('Thoda detail mein likhiye: kya, size, rang, kis kaam ke liye');
      return;
    }
    setState(() => _busy = true);
    try {
      await api.call('POST', '/api/blender3d', body: {
        'brief': b,
        'conversation_id': widget.app.conversationId ?? '',
        'exports': _exports.toList(),
        'quality': _quality,
        'aspect': _aspect,
        'print': _print,
        'turntable': _turn,
        'photos': _photos.map((p) => p['id']).toList(),
      });
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      _say('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Naya 3D')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        TextField(
          controller: _brief,
          minLines: 3,
          maxLines: 8,
          decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: 'Kya banana hai?',
              hintText: 'Jaise: 250 g achaar ki kaanch ki barni, laal dhakkan, mera label (photo), lakdi ki table par'),
        ),
        const SizedBox(height: 10),
        Wrap(spacing: 6, runSpacing: 4, children: [
          for (final ex in const [
            'Achaar ki barni mera label lagakar',
            'Chai stall ka 3D layout 8x6 feet',
            'Name plate "Sharma Niwas" pital jaisi',
            '3D print ke liye phone stand',
          ])
            ActionChip(label: Text(ex, style: const TextStyle(fontSize: 12)), onPressed: () => setState(() => _brief.text = ex)),
        ]),
        const SizedBox(height: 14),
        Row(children: [
          const Expanded(child: Text('Aapki photo (label / texture)', style: TextStyle(fontWeight: FontWeight.w600))),
          TextButton.icon(onPressed: _photos.length >= 6 ? null : _addPhoto, icon: const Icon(Icons.add_photo_alternate_rounded), label: const Text('Jodo')),
        ]),
        if (_photos.isNotEmpty)
          Wrap(spacing: 6, children: [
            for (final p in List.of(_photos))
              InputChip(label: Text('${p['name']}'), onDeleted: () => setState(() => _photos.remove(p))),
          ]),
        const SizedBox(height: 12),
        const Text('Files', style: TextStyle(fontWeight: FontWeight.w600)),
        Wrap(spacing: 6, children: [
          for (final f in _fmtSay.keys)
            FilterChip(
              label: Text(_fmtSay[f]!),
              selected: _exports.contains(f),
              onSelected: (on) => setState(() => on ? _exports.add(f) : _exports.remove(f)),
            ),
        ]),
        const SizedBox(height: 12),
        const Text('Picture', style: TextStyle(fontWeight: FontWeight.w600)),
        Wrap(spacing: 6, children: [
          for (final a in const ['1:1', '4:5', '9:16', '16:9'])
            ChoiceChip(label: Text(a), selected: _aspect == a, onSelected: (_) => setState(() => _aspect = a)),
          ChoiceChip(label: const Text('Jaldi'), selected: _quality == 'preview', onSelected: (_) => setState(() => _quality = 'preview')),
          ChoiceChip(label: const Text('Sharp'), selected: _quality == 'final', onSelected: (_) => setState(() => _quality = 'final')),
        ]),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: _turn,
          onChanged: (v) => setState(() => _turn = v),
          title: const Text('360° ghoomta video'),
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: _print,
          onChanged: (v) => setState(() {
            _print = v;
            if (v) _exports.add('stl');
          }),
          title: const Text('3D print ke liye'),
          subtitle: const Text('Band (closed) solid model + size check, STL file'),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _busy ? null : _go,
          icon: _busy
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.view_in_ar_rounded),
          label: const Text('Banao'),
        ),
        const SizedBox(height: 10),
        const Text(
            'Famous characters, kisi brand ka logo, asli log aur hathiyar ke parts Hoola nahi banata. Har picture par "AI se bana" likha hota hai.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}
