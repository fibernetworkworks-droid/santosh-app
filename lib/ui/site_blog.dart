// v0.364 BLOG + BHASHAYEN: her website's blog posts and languages on the phone. Posts are WRITTEN by the Content writer
// (Kalam) in chat ("blog likho: ...") and go up with her Haan on its card; here she sees them, hides / shows / deletes
// (each with a confirm) and picks the site's extra languages (up to 4).
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../state.dart';
import 'glass.dart';

String _t(dynamic v) => v == null ? '' : '$v';
List<dynamic> _l(dynamic v) => v is List ? v : const [];

class SiteBlogPage extends StatefulWidget {
  const SiteBlogPage({super.key, required this.app, required this.id, this.name = ''});
  final Santosh app;
  final String id;
  final String name;
  @override
  State<SiteBlogPage> createState() => _SiteBlogPageState();
}

class _SiteBlogPageState extends State<SiteBlogPage> {
  Map<String, dynamic>? _b;
  String _err = '';
  bool _busy = false;
  Set<String> _langs = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = await widget.app.api!.siteBlog(widget.id);
      if (mounted) {
        setState(() {
          _b = b;
          _err = '';
          _langs = _l(b['extra']).map((x) => _t(x)).toSet();
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<bool> _sure(String q) async =>
      await showDialog<bool>(
          context: context,
          builder: (c) => AlertDialog(content: Text(q), actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne do')),
                TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan')),
              ])) ==
      true;

  Future<void> _act(String slug, String action, String question) async {
    if (!await _sure(question)) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.siteBlogAct(widget.id, slug, action);
      if (mounted) _snack(_t(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _saveLangs() async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.siteLanguages(widget.id, _langs.toList());
      if (mounted) _snack(_t(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    final posts = _l(b?['posts']);
    final max = (b?['max_extra'] is int) ? b!['max_extra'] as int : 4;
    final prev = _t(b?['preview']).replaceAll(RegExp(r'/$'), '');
    return Scaffold(
      appBar: AppBar(title: Text(widget.name.isEmpty ? 'Blog aur bhashayen' : '${widget.name} · blog')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(14), children: [
          if (_err.isNotEmpty) Text(_err, style: const TextStyle(color: C.bad)),
          if (b == null && _err.isEmpty) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
          if (b != null) ...[
            Glass(
              radius: 18,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Naya post', style: display(15)),
                const SizedBox(height: 6),
                const Text('Chat mein likhiye: "blog likho: <kis baare mein, aapki apni baatein>". Content writer aapki aawaz mein '
                    'likhega, facts jaanchega, phir card par aapki Haan se website par lagega (abhi ya time par).',
                    style: TextStyle(color: C.muted, fontSize: 13)),
              ]),
            ),
            const SizedBox(height: 12),
            Text('Posts (${posts.length})', style: display(15)),
            const SizedBox(height: 6),
            if (posts.isEmpty) const Text('Abhi koi post nahi.', style: TextStyle(color: C.faint)),
            for (final raw in posts)
              Builder(builder: (context) {
                final p = raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
                final live = _t(p['status']) == 'published';
                final slug = _t(p['slug']);
                return Card(
                  color: C.panel,
                  child: ListTile(
                    title: Text(_t(p['title']), maxLines: 2, overflow: TextOverflow.ellipsis),
                    subtitle: Text('${_t(p['date'])} · ${{'published': 'Live', 'scheduled': 'Time par', 'hidden': 'Chhupa'}[_t(p['status'])] ?? _t(p['status'])}'
                        '${_t(p['category']).isEmpty ? '' : ' · ${_t(p['category'])}'}',
                        style: const TextStyle(fontSize: 12, color: C.muted)),
                    onTap: live && prev.isNotEmpty ? () => launchUrl(Uri.parse('$prev/blog/$slug/')) : null,
                    trailing: PopupMenuButton<String>(
                      enabled: !_busy,
                      onSelected: (a) => _act(slug, a, {
                            'hide': 'Yeh post website se hata dein? Baad mein wapas laga sakte hain.',
                            'show': 'Yeh post website par wapas lagayein?',
                            'delete': 'Yeh post hamesha ke liye mita dein? Wapas nahi aayega.',
                          }[a]!),
                      itemBuilder: (_) => [
                        if (live) const PopupMenuItem(value: 'hide', child: Text('Hatao (chhupao)')),
                        if (!live) const PopupMenuItem(value: 'show', child: Text('Wapas lagao')),
                        const PopupMenuItem(value: 'delete', child: Text('Mitao', style: TextStyle(color: C.bad))),
                      ],
                    ),
                  ),
                );
              }),
            const SizedBox(height: 16),
            Text('Website ki bhashayen', style: display(15)),
            const SizedBox(height: 4),
            Text('Pehli bhasha: ${_t(b['language'])}. $max aur tak chuniye - har page aur har post Hoola anuvaad karega.',
                style: const TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 6, children: [
              for (final raw in _l(b['choices']))
                Builder(builder: (context) {
                  final c = raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
                  final code = _t(c['code']);
                  final on = _langs.contains(code);
                  return FilterChip(
                    label: Text('${_t(c['label'])} · ${_t(c['english'])}'),
                    selected: on,
                    onSelected: (!on && _langs.length >= max) || _busy
                        ? null
                        : (v) => setState(() => v ? _langs.add(code) : _langs.remove(code)),
                  );
                }),
            ]),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(onPressed: _busy ? null : _saveLangs, child: const Text('Bhashayen save karo')),
            ),
          ],
        ]),
      ),
    );
  }
}
