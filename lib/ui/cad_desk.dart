/// v0.357 ENGINEERING DESK: the CAD Desk of a hired CAD Engineer (Employees > CAD Engineer > Open desk).
/// She writes the part and its sizes in mm; Hoola designs it in a locked box on the server and returns STEP / STL,
/// four views and a drawing PDF, with checks. Same server as the console: /api/eng/*.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

class CadDeskScreen extends StatefulWidget {
  const CadDeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CadDeskScreen> createState() => _CadDeskScreenState();
}

class _CadDeskScreenState extends State<CadDeskScreen> {
  final _brief = TextEditingController();
  final _change = <String, TextEditingController>{};
  List<Map<String, dynamic>> _ps = [];
  bool _loaded = false;
  bool _busy = false;
  String _err = '';
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _brief.dispose();
    for (final c in _change.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    _poll?.cancel();
    try {
      final d = await widget.app.api!.engProjects();
      if (!mounted) return;
      setState(() {
        _ps = _list(d['projects']);
        _loaded = true;
        _err = '';
      });
      if (_ps.any((p) => !['done', 'failed'].contains(_s(p['status'])))) {
        _poll = Timer(const Duration(seconds: 4), _load);
      }
    } catch (e) {
      if (mounted) setState(() {
        _err = '$e';
        _loaded = true;
      });
    }
  }

  Future<void> _run(Future<dynamic> Function() f, String ok) async {
    setState(() => _busy = true);
    try {
      await f();
      if (mounted && ok.isNotEmpty) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  String _url(String path) => widget.app.api!.absolute(path);

  Future<void> _open(String path) async {
    await launchUrl(Uri.parse(_url(path)), mode: LaunchMode.externalApplication);
  }

  Widget _card(Map<String, dynamic> p) {
    final st = _s(p['status']);
    final v = p['latest'] is Map ? Map<String, dynamic>.from(p['latest'] as Map) : null;
    final files = v == null ? <String, dynamic>{} : Map<String, dynamic>.from((v['files'] as Map?) ?? const {});
    final busy = !['done', 'failed'].contains(st);
    final bb = v?['bbox'] is Map ? Map<String, dynamic>.from(v!['bbox'] as Map) : null;
    final ctl = _change.putIfAbsent(_s(p['id']), () => TextEditingController());
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(p['title'])}${v != null ? '  v${_s(v['n'])}' : ''}', style: display(16))),
            Text(busy ? _s(p['stage']) : (st == 'done' ? 'Ready' : 'Failed'),
                style: TextStyle(fontSize: 12, color: st == 'failed' ? C.bad : (busy ? C.warn : C.ok))),
          ]),
          if (_s(p['error']).isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(p['error']), style: const TextStyle(color: C.bad, fontSize: 13))),
          if (busy) const Padding(padding: EdgeInsets.only(top: 10), child: LinearProgressIndicator()),
          if (files.isNotEmpty) ...[
            const SizedBox(height: 10),
            GridView.count(
              crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8, crossAxisSpacing: 8,
              children: [
                for (final k in const ['iso', 'front', 'top', 'right'])
                  if (files['$k.png'] != null)
                    GestureDetector(
                      onTap: () => _open(_s(files['$k.png'])),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Container(color: Colors.white, child: Image.network(_url(_s(files['$k.png'])), fit: BoxFit.contain)),
                      ),
                    ),
              ],
            ),
          ],
          if (bb != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('${_s(bb['x'])} x ${_s(bb['y'])} x ${_s(bb['z'])} mm'
                  '${_s(v?['assumed']).isNotEmpty && _s(v?['assumed']).toLowerCase() != 'none' ? ' · Assumed: ${_s(v?['assumed'])}' : ''}',
                  style: const TextStyle(color: C.muted, fontSize: 13)),
            ),
          if (v != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Wrap(spacing: 6, runSpacing: 6, children: [
                for (final c in _list(v['checks']))
                  Text('${c['ok'] == true ? '✓' : '✗'} ${_s(c['name'])}',
                      style: TextStyle(fontSize: 12.5, color: c['ok'] == true ? C.ok : C.bad)),
              ]),
            ),
          if (files.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Wrap(spacing: 8, runSpacing: 8, children: [
                for (final f in const [['part.step', 'STEP'], ['part.stl', 'STL'], ['drawing.pdf', 'Drawing PDF']])
                  if (files[f[0]] != null)
                    OutlinedButton(onPressed: () => _open(_s(files[f[0]])), child: Text(f[1])),
              ]),
            ),
          if (v != null && !busy) ...[
            const SizedBox(height: 10),
            TextField(controller: ctl, decoration: const InputDecoration(hintText: 'Change it, e.g. holes 10 mm, wall 3 mm thicker')),
            const SizedBox(height: 6),
            Row(children: [
              FilledButton(
                onPressed: _busy ? null : () {
                  final w = ctl.text.trim();
                  if (w.isEmpty) return;
                  ctl.clear();
                  _run(() => widget.app.api!.engChange(_s(p['id']), w), 'Making the next version.');
                },
                child: const Text('Make next version'),
              ),
              const Spacer(),
              TextButton(
                onPressed: _busy ? null : () => _run(() => widget.app.api!.engDelete(_s(p['id'])), 'Deleted.'),
                child: const Text('Delete', style: TextStyle(color: C.bad)),
              ),
            ]),
          ],
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('CAD Desk')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            const Text('Describe a part with its sizes in mm. Hoola designs it, checks it and gives STEP, STL and a drawing. '
                'Drafts for your engineer\'s review, not certified.', style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
            const SizedBox(height: 12),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                TextField(
                  controller: _brief, minLines: 2, maxLines: 5,
                  decoration: const InputDecoration(hintText: 'e.g. L bracket 80 x 40 mm, 10 mm thick, upright 30 mm, two 8 mm holes'),
                ),
                const SizedBox(height: 10),
                GradientButton(
                  label: 'Design this part', icon: Icons.view_in_ar_rounded,
                  onTap: _busy ? null : () {
                    final b = _brief.text.trim();
                    if (b.isEmpty) return;
                    _brief.clear();
                    _run(() => widget.app.api!.engStart(b), 'Designing. It takes about a minute.');
                  },
                ),
              ]),
            ),
            const SizedBox(height: 14),
            if (_err.isNotEmpty) Text(_err, style: const TextStyle(color: C.bad)),
            if (!_loaded) const Center(child: CircularProgressIndicator()),
            if (_loaded && _ps.isEmpty && _err.isEmpty)
              const Padding(padding: EdgeInsets.all(16), child: Text('No parts yet.', style: TextStyle(color: C.muted))),
            for (final p in _ps) _card(p),
          ]),
        ),
      ),
    );
  }
}
