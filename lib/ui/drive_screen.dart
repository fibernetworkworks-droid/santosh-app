import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

/// Profile > Google Drive: connect Google Drive, see storage and recent files, and what to ask Santosh.
class DriveScreen extends StatefulWidget {
  const DriveScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DriveScreen> createState() => _DriveScreenState();
}

class _DriveScreenState extends State<DriveScreen> {
  Map<String, dynamic> _st = {};
  bool _loaded = false;
  String? _err;
  int _seenTick = 0;

  Santosh get app => widget.app;
  List<Map<String, dynamic>> _list(String k) =>
      List<Map<String, dynamic>>.from((_st[k] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  @override
  void initState() {
    super.initState();
    _seenTick = app.driveLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.driveLinkedTick != _seenTick) {
      _seenTick = app.driveLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.driveState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = r['error'] as String?; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _link() async {
    try {
      final url = await app.api!.driveLinkUrl();
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Map<String, dynamic>? _check;
  bool _checking = false;

  Future<void> _diagnose() async {
    setState(() => _checking = true);
    try {
      final r = await app.api!.googleStatus();
      if (mounted) setState(() => _check = r);
      _load();
    } catch (e) {
      _snack(e.toString());
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  Widget _checkView(Map<String, dynamic> c) {
    final ok = c['ok'] == true;
    final signin = c['signin'] is Map ? Map<String, dynamic>.from(c['signin'] as Map) : null;
    final allowed = signin?['allowed'] is Map ? Map<String, dynamic>.from(signin!['allowed'] as Map) : const <String, dynamic>{};
    final problems = List<String>.from((c['problems'] as List? ?? const []).map((e) => '$e'));
    return Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Icon(ok ? Icons.check_circle_rounded : Icons.error_outline_rounded, color: ok ? C.teal : C.bad),
        const SizedBox(width: 8),
        Expanded(child: Text(ok ? 'Google Drive theek chal raha hai' : 'Drive nahi chal raha',
            style: const TextStyle(fontWeight: FontWeight.w700))),
      ]),
      if (signin != null) ...[
        const SizedBox(height: 8),
        Text('Sign-in: ${signin['email'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 4),
        Wrap(spacing: 6, runSpacing: 4, children: [
          for (final e in allowed.entries)
            Chip(
              visualDensity: VisualDensity.compact,
              avatar: Icon(e.value == true ? Icons.check_rounded : Icons.close_rounded, size: 15, color: e.value == true ? C.teal : C.bad),
              label: Text(e.key, style: const TextStyle(fontSize: 12)),
            ),
        ]),
      ],
      for (final p in problems)
        Padding(padding: const EdgeInsets.only(top: 8), child: Text(p, style: const TextStyle(color: C.chip, fontSize: 13))),
    ]));
  }

  Future<void> _remove(String key) async {
    try {
      final r = await app.api!.driveRemove(key);
      if (mounted) setState(() => _st = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Widget _storage(Map<String, dynamic> s) {
    final pct = (s['percent'] as num?)?.toDouble();
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Jagah: ${s['used'] ?? '-'} / ${s['limit'] ?? '-'}', style: const TextStyle(color: C.chip, fontSize: 12.5)),
        if (pct != null) ...[
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: (pct / 100).clamp(0.0, 1.0),
              minHeight: 7,
              backgroundColor: C.panel,
              color: pct > 90 ? C.bad : (pct > 75 ? C.warn : C.teal),
            ),
          ),
        ],
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final accounts = _list('accounts');
    final storage = _list('storage');
    final recent = _list('recent');
    final canLink = _st['can_link'] == true;
    final hasOwn = accounts.any((a) => a['kind'] == 'google');
    return Scaffold(
      appBar: AppBar(title: const Text('Google Drive'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Hoola aapke Google Drive mein files dhoondhta, padhta, phone / PC / email par bhejta, upload karta, '
                'folder sambhalta aur Google Doc banata hai. Share karna, public link aur Trash hamesha aapke tap ke baad hi.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 14),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            for (final a in accounts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Icon(a['kind'] == 'service' ? Icons.folder_shared_rounded : Icons.add_to_drive_rounded, color: C.teal),
                    const SizedBox(width: 10),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(a['address'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                      Text(a['kind'] == 'service' ? 'Server ka service account: sirf share kiya hua folder' : 'Google Drive',
                          style: const TextStyle(color: C.muted, fontSize: 12.5)),
                      if (a['status'] == 'error') Text(a['error'] as String? ?? 'Login fail', style: const TextStyle(color: C.bad, fontSize: 12)),
                    ])),
                    if (a['removable'] == true)
                      IconButton(tooltip: 'Hataiye', icon: const Icon(Icons.close_rounded, color: C.muted),
                          onPressed: () => _remove(a['key'] as String)),
                  ]),
                  for (final s in storage.where((s) => s['account'] == a['address'] && s['error'] == null)) _storage(s),
                ])),
              ),
            if (_loaded) ...[
              if (!hasOwn)
                GradientButton(label: 'Google Drive jodiye', icon: Icons.add_to_drive_rounded, height: 50, onTap: canLink ? _link : null)
              else
                GlassButton(label: 'Doosra Google account jodiye', icon: Icons.add_rounded, height: 44, onTap: canLink ? _link : null),
              if (!canLink)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text('Is server par Google sign-in abhi chalu nahi hai (GOOGLE_OAUTH_CLIENT_ID / SECRET).',
                      style: TextStyle(color: C.faint, fontSize: 12)),
                ),
            ],
            if (_loaded) ...[
              const SizedBox(height: 10),
              GlassButton(label: _checking ? 'Jaanch ho rahi hai...' : 'Jaanch karo: Drive kyun nahi chal raha?',
                  icon: Icons.health_and_safety_outlined, height: 44, onTap: _checking ? null : _diagnose),
              if (_check != null) Padding(padding: const EdgeInsets.only(top: 10), child: _checkView(_check!)),
            ],
            if (recent.isNotEmpty) ...[
              const SizedBox(height: 18),
              const Text('Haal ki files', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Glass(child: Column(children: [
                for (final f in recent)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    leading: Icon(f['type'] == 'Folder' ? Icons.folder_rounded : Icons.insert_drive_file_outlined, color: C.chip),
                    title: Text(f['name'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis),
                    subtitle: Text('${f['type'] ?? ''} · ${f['used'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12)),
                  ),
              ])),
            ],
            const SizedBox(height: 18),
            const Text('Bolkar dekhiye', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"Drive mein Sharma Traders ka quotation dhoondho"',
              '"Bijli bill wali PDF padho, kitna dena hai?"',
              '"Woh quotation PDF banakar Ramesh ko mail karo"',
              '"Is mail ka attachment Drive ke Invoices folder mein daal do"',
              '"Diwali 2026 naam ka folder banao"',
              '"Report Swati ke saath share karo, sirf dekh sake"',
              '"Drive mein kitni jagah bachi hai?"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}


/// v0.70 Google refused her sign-in (expired / revoked): one card in the chat (and call) with the fix.
class GoogleReconnectCard extends StatelessWidget {
  const GoogleReconnectCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.link_off_rounded, color: C.warn),
          SizedBox(width: 8),
          Expanded(child: Text('Google dobara jodiye', style: TextStyle(fontWeight: FontWeight.w700))),
        ]),
        const SizedBox(height: 6),
        Text('${v['text'] ?? ''}', style: const TextStyle(color: C.chip, fontSize: 13)),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(child: GradientButton(label: 'Google jodiye', icon: Icons.add_to_drive_rounded, height: 44, onTap: () async {
            try {
              final url = await app.api!.driveLinkUrl();
              await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
            } catch (e) {
              if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
            }
          })),
          const SizedBox(width: 8),
          GlassButton(label: 'Jaanch', icon: Icons.health_and_safety_outlined, height: 44,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DriveScreen(app: app)))),
        ]),
      ])),
    );
  }
}
