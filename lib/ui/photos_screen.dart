import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication).catchError((_) => false);
}

/// Chat card for a Google Photos pick: the user taps, picks photos in Google Photos, and Santosh carries on.
class PhotosPickCard extends StatelessWidget {
  const PhotosPickCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'waiting';
    final count = (v['count'] as num?)?.toInt() ?? 0;
    final purpose = v['purpose'] as String? ?? '';
    final uri = v['picker_uri'] as String? ?? '';
    final (chip, fg) = switch (status) {
      'ready' => ('$count SELECTED', C.ok),
      'expired' => ('EXPIRES', C.muted),
      _ => ('YOUR TURN', C.warn),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.photo_library_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            const Expanded(child: Text('Google Photos', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(chip, fg: fg),
          ]),
          if (purpose.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text(purpose, style: const TextStyle(color: C.chip, fontSize: 13))),
          const SizedBox(height: 6),
          Text(
            status == 'ready'
                ? 'Photos received. Hoola is carrying on with the work.'
                : status == 'expired'
                    ? 'This link has expired. Ask Hoola again.'
                    : 'Tap below, choose photos in Google Photos and tap "Done". Hoola will see only those photos.',
            style: const TextStyle(color: C.muted, fontSize: 12.5),
          ),
          if (status == 'waiting' && uri.isNotEmpty) ...[
            const SizedBox(height: 10),
            GradientButton(label: 'Choose photos', icon: Icons.photo_library_rounded, height: 48, onTap: () => _open(uri)),
          ],
        ]),
      ),
    );
  }
}

/// Profile > Google Photos: connect a Google account for Photos; explains what Google allows.
class PhotosScreen extends StatefulWidget {
  const PhotosScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PhotosScreen> createState() => _PhotosScreenState();
}

class _PhotosScreenState extends State<PhotosScreen> {
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
    _seen = app.photosLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.photosLinkedTick != _seen) {
      _seen = app.photosLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.photosState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = null; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _link() async {
    try {
      await _open(await app.api!.photosLinkUrl());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _remove(String key) async {
    try {
      final r = await app.api!.photosRemove(key);
      if (mounted) setState(() => _st = r);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final accounts = _list('accounts');
    final canLink = _st['can_link'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('Google Photos'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('You choose photos in Google Photos, and Hoola sends them to your phone, PC, Drive or email. '
                'Hoola can also upload photos and make albums. Under Google\'s policy, Hoola cannot see your whole library, '
                'nor share or delete from it.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 14),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            for (final a in accounts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: Row(children: [
                  const Icon(Icons.photo_library_rounded, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a['address'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(a['can_upload'] == true ? 'Choose + upload' : 'Choose only', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    if (a['status'] == 'error') Text(a['error'] as String? ?? 'Login fail', style: const TextStyle(color: C.bad, fontSize: 12)),
                  ])),
                  if (a['removable'] == true)
                    IconButton(icon: const Icon(Icons.close_rounded, color: C.muted), onPressed: () => _remove(a['key'] as String)),
                ])),
              ),
            if (_loaded && accounts.isEmpty) ...[
              GradientButton(label: 'Link Google Photos', icon: Icons.photo_library_rounded, height: 50, onTap: canLink ? _link : null),
              if (!canLink)
                const Padding(padding: EdgeInsets.only(top: 8),
                    child: Text('Google sign-in is not turned on for this server yet.', style: TextStyle(color: C.faint, fontSize: 12))),
            ] else if (_loaded)
              GlassButton(label: 'Link another Google account', icon: Icons.add_rounded, height: 44, onTap: canLink ? _link : null),
            const SizedBox(height: 18),
            const Text('Try saying', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"Pick the Expo photos and email them to Ramesh"',
              '"Save yesterday\'s site photos to the PC"',
              '"Put this mail\'s photos in the Diwali album in Google Photos"',
              '"Keep the shop photos in the Marketing folder on Drive"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}
