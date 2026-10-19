import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication).catchError((_) => false);
}

/// Chat card: YouTube videos Santosh found (thumbnail, title, channel, views) that open in the YouTube app.
class YouTubeCard extends StatelessWidget {
  const YouTubeCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final items = List<Map<String, dynamic>>.from((v['items'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final title = v['title'] as String? ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.smart_display_rounded, color: Color(0xFFFF4D4D), size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(title.isEmpty ? 'YouTube' : title, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
          ]),
          const SizedBox(height: 8),
          for (final it in items)
            InkWell(
              onTap: () => _open(it['url'] as String? ?? ''),
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: SizedBox(
                      width: 112, height: 63,
                      child: (it['thumbnail'] as String? ?? '').isEmpty
                          ? Container(color: C.panel, child: const Icon(Icons.play_arrow_rounded, color: C.chip))
                          : Stack(fit: StackFit.expand, children: [
                              Image.network(it['thumbnail'] as String, fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => Container(color: C.panel)),
                              if ((it['duration'] as String? ?? '').isNotEmpty)
                                Positioned(right: 4, bottom: 4, child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                  decoration: BoxDecoration(color: const Color(0xCC000000), borderRadius: BorderRadius.circular(4)),
                                  child: Text(it['duration'] as String, style: const TextStyle(fontSize: 10.5, color: Colors.white)),
                                )),
                            ]),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(it['title'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                    const SizedBox(height: 2),
                    Text([
                      it['channel'] as String? ?? '',
                      if ((it['views_text'] as String? ?? '').isNotEmpty) '${it['views_text']} views',
                      it['published'] as String? ?? '',
                    ].where((x) => x.isNotEmpty).join(' · '), maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ])),
                ]),
              ),
            ),
        ]),
      ),
    );
  }
}

/// Profile > YouTube: connect your channel; see what works without it.
class YouTubeScreen extends StatefulWidget {
  const YouTubeScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<YouTubeScreen> createState() => _YouTubeScreenState();
}

class _YouTubeScreenState extends State<YouTubeScreen> {
  Map<String, dynamic> _st = {};
  bool _loaded = false;
  String? _err;
  int _seen = 0;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _seen = app.youtubeLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.youtubeLinkedTick != _seen) {
      _seen = app.youtubeLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.youtubeState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = null; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _link() async {
    try {
      await _open(await app.api!.youtubeLinkUrl());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Widget _flag(bool on, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Icon(on ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded, size: 18, color: on ? C.ok : C.faint),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: TextStyle(color: on ? C.ink : C.muted, fontSize: 13))),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final accounts = List<Map<String, dynamic>>.from((_st['accounts'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final canLink = _st['can_link'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('YouTube'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('YouTube ke official tareeke se: video dhoondhna, views / subscribers, comments, aur Google Gemini se video '
                'dekh kar summary ya sawaal ka jawab. Apna channel jodne par: aapke videos, analytics, playlists. Comment ka jawab, '
                'video badalna aur upload aapke tap ke baad hi.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 12),
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded) Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _flag(_st['public_search'] == true || accounts.isNotEmpty, 'Video / channel dhoondhna aur stats'),
              _flag(_st['can_watch'] == true, 'Video dekh kar summary / jawab (Gemini)'),
              _flag(accounts.isNotEmpty, 'Mera channel: videos, analytics, playlists, comments ka jawab, upload'),
            ])),
            const SizedBox(height: 12),
            for (final a in accounts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: Row(children: [
                  const Icon(Icons.smart_display_rounded, color: Color(0xFFFF4D4D)),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text((a['channel'] as String? ?? '').isEmpty ? 'YouTube channel' : a['channel'] as String,
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(a['address'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  ])),
                  if (a['removable'] == true)
                    IconButton(icon: const Icon(Icons.close_rounded, color: C.muted), onPressed: () async {
                      try {
                        final r = await app.api!.youtubeRemove(a['key'] as String);
                        if (mounted) setState(() => _st = r);
                      } catch (e) {
                        if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                      }
                    }),
                ])),
              ),
            if (_loaded && accounts.isEmpty)
              GradientButton(label: 'Apna YouTube channel jodiye', icon: Icons.smart_display_rounded, height: 50, onTap: canLink ? _link : null),
            const SizedBox(height: 18),
            const Text('Bolkar dekhiye', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"GPON setup ke Hindi videos dikhao, is mahine ke"',
              '"Is video ka summary do" (link bhejiye)',
              '"Is video mein ONU add karne ke steps kya bataye?"',
              '"Mere channel ke is hafte ke views aur subscribers?"',
              '"Mere FNW Flow demo video par aaye comments ka jawab likho"',
              '"Is video ko notebook mein jodo"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}
