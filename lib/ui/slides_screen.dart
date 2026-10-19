import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication).catchError((_) => false);
}

/// A Google Slides deck Santosh created / changed, shown in the chat with an Open button.
class SlidesCard extends StatelessWidget {
  const SlidesCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'created';
    final chip = switch (status) {
      'created' => 'NAYI PRESENTATION',
      'deleted' => 'SLIDES HATAYI',
      'updated' => 'BADAL DI',
      'shared' => 'SHARE KI',
      _ => status.toUpperCase(),
    };
    final count = (v['slide_count'] as num?)?.toInt();
    final link = v['link'] as String? ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.slideshow_rounded, color: C.warn, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(v['title'] as String? ?? 'Google Slides', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(chip, fg: C.warn),
          ]),
          if (count != null)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('$count slides', style: const TextStyle(color: C.muted, fontSize: 12.5))),
          if (link.isNotEmpty) ...[
            const SizedBox(height: 10),
            GlassButton(label: 'Presentation kholiye', icon: Icons.open_in_new_rounded, height: 42, onTap: () => _open(link)),
          ],
        ]),
      ),
    );
  }
}

/// Profile > Google Slides: connect a Google account for Slides; see the decks Santosh used recently.
class SlidesScreen extends StatefulWidget {
  const SlidesScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SlidesScreen> createState() => _SlidesScreenState();
}

class _SlidesScreenState extends State<SlidesScreen> {
  Map<String, dynamic> _st = {};
  bool _loaded = false;
  String? _err;
  int _seen = 0;

  Santosh get app => widget.app;
  List<Map<String, dynamic>> _list(String k) =>
      List<Map<String, dynamic>>.from((_st[k] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  @override
  void initState() {
    super.initState();
    _seen = app.slidesLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.slidesLinkedTick != _seen) {
      _seen = app.slidesLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.slidesState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = null; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _link() async {
    try {
      await _open(await app.api!.slidesLinkUrl());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _remove(String key) async {
    try {
      final r = await app.api!.slidesRemove(key);
      if (mounted) setState(() => _st = r);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final accounts = _list('accounts');
    final recent = _list('recent');
    final canLink = _st['can_link'] == true;
    const onlyService = false;
    return Scaffold(
      appBar: AppBar(title: const Text('Google Slides'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Santosh kisi bhi topic par poori presentation banata hai (title, points, table, closing aur speaker notes ke '
                'saath), aapki decks padhkar summary deta hai, slides jodta / badalta / aage-peeche karta hai aur PDF ya PowerPoint '
                'banakar bhejta hai. Slides hatana aur share karna aapke tap ke baad hi.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 14),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            for (final a in accounts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: Row(children: [
                  const Icon(Icons.slideshow_rounded, color: C.warn),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a['address'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text('Google account',
                        style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    if (a['status'] == 'error') Text(a['error'] as String? ?? 'Login fail', style: const TextStyle(color: C.bad, fontSize: 12)),
                  ])),
                  if (a['removable'] == true)
                    IconButton(icon: const Icon(Icons.close_rounded, color: C.muted), onPressed: () => _remove(a['key'] as String)),
                ])),
              ),
            if (_loaded && (accounts.isEmpty || onlyService)) ...[
              GradientButton(label: 'Google Slides jodiye', icon: Icons.slideshow_rounded, height: 50, onTap: canLink ? _link : null),
              if (!canLink)
                const Padding(padding: EdgeInsets.only(top: 8),
                    child: Text('Is server par Google sign-in abhi chalu nahi hai.', style: TextStyle(color: C.faint, fontSize: 12))),
            ] else if (_loaded)
              GlassButton(label: 'Doosra Google account jodiye', icon: Icons.add_rounded, height: 44, onTap: canLink ? _link : null),
            if (recent.isNotEmpty) ...[
              const SizedBox(height: 18),
              const Text('Haal ki presentations', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Glass(child: Column(children: [
                for (final r in recent)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.slideshow_outlined, color: C.chip),
                    title: Text(r['title'] as String? ?? ''),
                    subtitle: Text('${r['used'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12)),
                    onTap: () => _open('https://docs.google.com/presentation/d/${r['id']}/edit'),
                  ),
              ])),
            ],
            const SizedBox(height: 18),
            const Text('Bolkar dekhiye', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"FNW Flow par 8 slide ki pitch presentation banao"',
              '"ITPC training ke liye AI par presentation, Hindi mein"',
              '"Q3 review deck ka summary batao"',
              '"Slide 3 mein Goa ka point jodo"',
              '"Deck mein 2025 ko 2026 kar do"',
              '"Presentation PDF banakar client ko mail karo"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}
