import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../native.dart';
import '../../state.dart';
import '../glass.dart';
import 'studio_kit.dart';

/// v0.159 Screen 12 · Final video: a big player, length / size, the AI check score and what it cost, straight into
/// WhatsApp / Instagram / YouTube (she posts it herself), save to the gallery, a link, and "kuch badalna hai?".
class FinalScreen extends StatefulWidget {
  const FinalScreen({super.key, required this.app, required this.name});
  final Santosh app;
  final String name;
  @override
  State<FinalScreen> createState() => _FinalScreenState();
}

class _FinalScreenState extends State<FinalScreen> {
  Map<String, dynamic>? _v;
  int _i = -1;
  String _busy = '';
  final _change = TextEditingController();

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _change.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final v = await app.api!.studioProject(widget.name);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
  }

  Map<String, dynamic> get _out {
    final outs = sList(_v?['outputs']);
    if (outs.isEmpty) return {};
    return outs[_i < 0 || _i >= outs.length ? outs.length - 1 : _i];
  }

  Future<String?> _file() async {
    final o = _out;
    if (o.isEmpty) return null;
    return localCopy(app, '${o['url']}', '${o['name'] ?? '${widget.name}.mp4'}');
  }

  Future<void> _share(String key, String pkg, String label) async {
    setState(() => _busy = key);
    try {
      final p = await _file();
      if (p != null) {
        final err = await Native.shareFile(p, title: 'Video bhejo', app: pkg);
        if (err != null && mounted) studioSnack(context, err);
      }
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
    if (mounted) setState(() => _busy = '');
  }

  Future<void> _save() async {
    setState(() => _busy = 'save');
    try {
      final p = await _file();
      if (p != null) {
        final err = await Native.saveVideo(p, '${widget.name.replaceAll(RegExp(r'[^\w\- ]'), '')}.mp4');
        if (mounted) studioSnack(context, err ?? 'Gallery mein save ho gaya (Movies/Hoola)');
      }
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
    if (mounted) setState(() => _busy = '');
  }

  Future<void> _revise() async {
    final t = _change.text.trim();
    if (t.length < 4) {
      studioSnack(context, 'Kya badalna hai, likhiye');
      return;
    }
    final sent = await app.send('Video Studio "${widget.name}" mein badlav chahiye: $t. Sirf zaroori shots dobara banao, '
        'daam ka card bhejo, phir final video dobara jodo.');
    if (!mounted) return;
    if (sent) {
      _change.clear();
      studioSnack(context, '${app.aName} ko bata diya: badle hue shot ka daam card par aayega.');
    } else {
      studioSnack(context, 'Bhej nahi paya; dobara try kijiye.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final o = _out;
    final outs = sList(v?['outputs']);
    final shots = sList(v?['shots']);
    final scores = shots.map((s) => s['score']).whereType<num>().toList();
    final avg = scores.isEmpty ? null : scores.reduce((a, b) => a + b) / scores.length;
    final ar = aspectOf('${v?['aspect'] ?? '9:16'}');
    return Scaffold(
      backgroundColor: SC.stage,
      body: SafeArea(
        child: v == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.only(bottom: 24), children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 8, 16, 4),
                  child: Row(children: [
                    IconButton(onPressed: () => Navigator.maybePop(context), icon: const Icon(Icons.chevron_left_rounded, size: 30)),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(widget.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: sora(17)),
                        Text(o.isEmpty ? 'Abhi final video nahi' : 'Version ${outs.indexWhere((x) => x['url'] == o['url']) + 1}${o['preview'] == true ? ' · free preview' : ''}',
                            style: body(11.5, color: C.faint)),
                      ]),
                    ),
                    if (o.isNotEmpty) Tag(o['preview'] == true ? 'Preview' : 'Taiyaar', fg: o['preview'] == true ? C.muted : C.ok, size: 11),
                  ]),
                ),
                if (o.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text('Pehle shots banaiye, phir "Final video jodo".', textAlign: TextAlign.center, style: body(14, color: C.muted)),
                  )
                else ...[
                  Center(
                    child: SizedBox(
                      width: ar < 1 ? 280 : 360,
                      height: ar < 1 ? 280 / ar : 360 / ar,
                      child: SVideo(key: ValueKey('final${o['url']}'), app: app, url: '${o['url']}', poster: '${o['thumb'] ?? ''}',
                          autoplay: true),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 8, children: [
                    Tag('${secs(o['seconds'])} · ${o['mb'] ?? '?'} MB', fg: C.chip, bg: SC.card, size: 12),
                    if (avg != null) Tag('AI jaanch ${avg.toStringAsFixed(1)}', fg: avg < 6 ? C.warn : C.ok, bg: SC.card, size: 12),
                    Tag('Kharch ${rupees(v['spent_inr'])}', fg: C.chip, bg: SC.card, size: 12),
                  ]),
                  if (outs.length > 1) ...[
                    const SizedBox(height: 12),
                    Center(
                      child: Wrap(spacing: 8, children: [
                        for (var i = 0; i < outs.length; i++)
                          SChip(label: 'V${i + 1}${outs[i]['preview'] == true ? ' preview' : ''}', on: outs[i]['url'] == o['url'],
                              onTap: () => setState(() => _i = i)),
                      ]),
                    ),
                  ],
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 18, 16, 0),
                    child: Row(children: [
                      _shareTile('wa', Icons.chat_rounded, 'WhatsApp', 'com.whatsapp'),
                      const SizedBox(width: 8),
                      _shareTile('ig', Icons.camera_alt_rounded, 'Instagram', 'com.instagram.android'),
                      const SizedBox(width: 8),
                      _shareTile('yt', Icons.smart_display_rounded, 'YouTube', 'com.google.android.youtube'),
                      const SizedBox(width: 8),
                      _shareTile('more', Icons.share_rounded, 'Aur', ''),
                    ]),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                    child: Row(children: [
                      Expanded(child: SButton(label: 'Gallery mein save', icon: Icons.download_rounded, busy: _busy == 'save', onTap: _save)),
                      const SizedBox(width: 10),
                      Expanded(
                        child: SButton(label: 'Link · 10 din', icon: Icons.link_rounded, primary: false, onTap: () {
                          Clipboard.setData(ClipboardData(text: app.api!.absolute('${o['url']}')));
                          studioSnack(context, 'Link copy ho gaya (10 din chalega)');
                        }),
                      ),
                    ]),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                    child: Text('Video par "AI-generated · Hoola" label hai. Post aap khud kijiye; Hoola kahin post nahi karta.',
                        textAlign: TextAlign.center, style: body(11.5, color: C.faint)),
                  ),
                ],
                Container(
                  margin: const EdgeInsets.fromLTRB(16, 18, 16, 0),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(18)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    Text('Kuch badalna hai?', style: body(14, w: FontWeight.w800)),
                    const SizedBox(height: 10),
                    Row(children: [
                      Expanded(
                        child: TextField(
                          controller: _change,
                          style: body(13.5, w: FontWeight.w500),
                          decoration: InputDecoration(
                            hintText: 'Jaise: ant ka close-up 2 sec lamba karo',
                            hintStyle: body(13, w: FontWeight.w500, color: C.faint),
                            filled: true,
                            fillColor: SC.field,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Press(
                        onTap: _revise,
                        child: Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(color: C.ink, borderRadius: BorderRadius.circular(12)),
                          child: const Icon(Icons.arrow_forward_rounded, color: SC.bg),
                        ),
                      ),
                    ]),
                    const SizedBox(height: 8),
                    Text('Sirf badla hua shot dobara banega. Jodna aur captions free.', style: body(11.5, color: C.faint)),
                  ]),
                ),
              ]),
      ),
    );
  }

  Widget _shareTile(String key, IconData icon, String label, String pkg) => Expanded(
        child: Press(
          onTap: _busy.isNotEmpty ? null : () => _share(key, pkg, label),
          child: Container(
            height: 76,
            decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(16)),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              _busy == key
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: C.ink))
                  : Icon(icon, color: C.ink, size: 22),
              const SizedBox(height: 6),
              Text(label, style: body(11.5, w: FontWeight.w700)),
            ]),
          ),
        ),
      );
}
