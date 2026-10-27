import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../state.dart';
import 'artifact_screen.dart';
import 'glass.dart';

/// Mere Artifacts: every app, tracker, chart and document Santosh has built for you.
class ArtifactsScreen extends StatefulWidget {
  const ArtifactsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ArtifactsScreen> createState() => _ArtifactsScreenState();
}

class _ArtifactsScreenState extends State<ArtifactsScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loaded = false;
  String? _err;
  int _tick = 0;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _tick = app.artifactTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  /// A new or updated artifact arrived live: refresh quietly.
  void _onApp() {
    if (app.artifactTick != _tick) {
      _tick = app.artifactTick;
      _load();
    }
  }

  Future<void> _load() async {
    final api = app.api;
    if (api == null) {
      if (mounted) setState(() => _err = 'Hoola se connect nahi hai.');
      return;
    }
    try {
      final r = await api.artifacts();
      if (!mounted) return;
      setState(() {
        _items = r;
        _loaded = true;
        _err = null;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _loaded = true;
          _err = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  Widget _tile(Map<String, dynamic> a) {
    final id = a['id'] as String? ?? '';
    final rawTitle = a['title'] as String? ?? '';
    final title = rawTitle.isEmpty ? 'Artifact' : rawTitle;
    final summary = a['summary'] as String? ?? '';
    final status = a['status'] as String? ?? 'ready';
    final v = a['version'];
    final version = v is num ? v.toInt() : 0;
    final meta = [
      if (version > 0) 'v$version',
      if (artifactAgo(a['updated_at'] as String?).isNotEmpty) artifactAgo(a['updated_at'] as String?),
      if (a['shared'] == true) 'link se share',
    ].join(' · ');
    return Press(
      onTap: id.isEmpty
          ? null
          : () async {
              await openArtifact(context, app, id, title);
              _load();
            },
      child: Glass(
        radius: 20,
        padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
        child: Row(children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(gradient: C.gradient, borderRadius: BorderRadius.circular(13)),
            child: const Icon(Icons.auto_awesome_mosaic_rounded, color: C.onAccent, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
              if (summary.isNotEmpty)
                Text(summary, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.chip, fontSize: 12.5)),
              if (meta.isNotEmpty) Text(meta, style: const TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
          const SizedBox(width: 6),
          if (status == 'building')
            const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.2, color: C.accent))
          else if (status == 'failed')
            const Pill('NAHI BANA', fg: C.bad)
          else
            const Icon(Icons.chevron_right_rounded, color: C.muted),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Mere Artifacts'), backgroundColor: Colors.transparent),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
                if (!_loaded && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
                if (_loaded && _items.isEmpty && _err == null)
                  const Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('Abhi koi artifact nahi', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                      SizedBox(height: 6),
                      Text('Hoola se boliye: "Mere kharche ka tracker banao", "EMI calculator bana do", '
                          '"Kal ki meeting ka plan banao". Woh ek chhota app bana dega jo yahan dikhega.',
                          style: TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
                    ]),
                  ),
                for (var i = 0; i < _items.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Stagger(key: ValueKey(_items[i]['id']), index: math.min(i, 8), child: _tile(_items[i])),
                  ),
              ],
            ),
          ),
        ),
      );
}
