// v0.129 Photo banao / photo badlo: the picture Hoola made or changed, with save / share / "badlav bolo".
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

class PhotoMadeCard extends StatefulWidget {
  const PhotoMadeCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<PhotoMadeCard> createState() => _PhotoMadeCardState();
}

class _PhotoMadeCardState extends State<PhotoMadeCard> {
  bool _busy = false;
  final _ctl = TextEditingController();

  String get _url => widget.app.api?.absolute(widget.v['url'] as String? ?? '') ?? '';
  String get _name => (widget.v['name'] as String?) ?? 'hoola_photo.png';
  bool get _edit => widget.v['edit'] == true;

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  Future<String?> _local() async {
    final api = widget.app.api;
    if (api == null) return null;
    final bytes = await api.brandBytes(widget.v['url'] as String? ?? '');
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/${_name.replaceAll(RegExp(r'[^\w\-. ()]'), '_')}');
    await f.writeAsBytes(bytes);
    return f.path;
  }

  void _say(String t) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _run(Future<void> Function() job) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await job();
    } catch (e) {
      _say('Nahi ho paya: $e (link 24 ghante chalta hai; purani photo ho to dobara banwaiye)');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() => _run(() async {
        final p = await _local();
        if (p == null) return;
        final err = await Native.saveImage(p, _name);
        _say(err ?? 'Gallery mein save ho gayi (Pictures/Hoola)');
      });

  Future<void> _share() => _run(() async {
        final p = await _local();
        if (p == null) return;
        final err = await Native.shareFile(p, mime: 'image/png', title: 'Photo bhejiye');
        if (err != null) _say(err);
      });

  Future<void> _change() async {
    final t = _ctl.text.trim();
    final fid = widget.v['file_id'] as String?;
    if (t.isEmpty || fid == null) return;
    _ctl.clear();
    FocusScope.of(context).unfocus();
    await widget.app.send('Is photo mein yeh badlav karo: $t', files: [fid]);
  }

  void _open() {
    if (_url.isEmpty) return;
    Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => Scaffold(
              backgroundColor: Colors.black,
              appBar: AppBar(backgroundColor: Colors.black, foregroundColor: Colors.white, title: Text(_name)),
              body: InteractiveViewer(maxScale: 5, child: Center(child: Image.network(_url))),
            )));
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final prompt = (v['prompt'] as String?) ?? '';
    final best = v['quality'] == 'best';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(_edit ? Icons.auto_fix_high_rounded : Icons.image_rounded, color: C.teal),
            const SizedBox(width: 10),
            Expanded(
                child: Text(_edit ? 'Photo badli' : 'Photo bani',
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5))),
            Text('${v['aspect'] ?? ''} · ${best ? 'best' : 'fast'}', style: const TextStyle(color: C.faint, fontSize: 12)),
          ]),
          const SizedBox(height: 10),
          GestureDetector(
            onTap: _open,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 420),
                child: _url.isEmpty
                    ? const SizedBox(height: 120)
                    : Image.network(_url,
                        fit: BoxFit.contain,
                        loadingBuilder: (c, w, p) =>
                            p == null ? w : const SizedBox(height: 220, child: Center(child: CircularProgressIndicator())),
                        errorBuilder: (c, e, s) => Container(
                            height: 120,
                            alignment: Alignment.center,
                            child: const Text('Photo ka link purana ho gaya (24 ghante)', style: TextStyle(color: C.faint)))),
              ),
            ),
          ),
          if (prompt.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(prompt, maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 12.5)),
          ],
          const SizedBox(height: 4),
          const Text('AI se bana · Hoola', style: TextStyle(color: C.faint, fontSize: 11)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 6, children: [
            OutlinedButton.icon(
                onPressed: _busy ? null : _save,
                icon: const Icon(Icons.download_rounded, size: 18),
                label: const Text('Save')),
            OutlinedButton.icon(
                onPressed: _busy ? null : _share,
                icon: const Icon(Icons.share_rounded, size: 18),
                label: const Text('Bhejo')),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _ctl,
                minLines: 1,
                maxLines: 3,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _change(),
                decoration: const InputDecoration(
                    isDense: true, hintText: 'Badlav bolo: "rang neela karo"', border: OutlineInputBorder()),
              ),
            ),
            IconButton(onPressed: _change, icon: const Icon(Icons.send_rounded, color: C.teal)),
          ]),
        ]),
      ),
    );
  }
}
