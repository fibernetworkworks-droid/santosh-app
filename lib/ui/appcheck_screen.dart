import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

Color _vColor(String v) => switch (v) { 'danger' => C.bad, 'caution' => C.warn, 'clear' => C.ok, _ => C.faint };
IconData _vIcon(String v) => switch (v) {
      'danger' => Icons.gpp_bad_rounded,
      'caution' => Icons.gpp_maybe_rounded,
      'clear' => Icons.verified_user_rounded,
      _ => Icons.help_outline_rounded,
    };

const _factLabels = {
  'app_name': 'App', 'package': 'Package', 'version': 'Version', 'signed_by': 'Sign kiya', 'company': 'Company',
  'product': 'Product', 'description': 'Kaam', 'built_with': 'Bana hai', 'architecture': 'PC type', 'files_inside': 'Andar files',
};

/// Chat card: App Jaanch verdict for an APK / EXE / file (never run, only read).
class AppCheckCard extends StatelessWidget {
  const AppCheckCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final verdict = v['verdict'] as String? ?? 'unknown';
    final col = _vColor(verdict);
    final flags = List<Map<String, dynamic>>.from((v['flags'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final facts = Map<String, dynamic>.from(v['facts'] as Map? ?? const {});
    final limits = List<String>.from((v['limits'] as List? ?? const []).map((e) => '$e'));
    final perms = v['permissions'] as int? ?? 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(_vIcon(verdict), color: col, size: 26),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(v['name'] as String? ?? 'File', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              Text(v['verdict_text'] as String? ?? '', style: TextStyle(color: col, fontWeight: FontWeight.w700, fontSize: 13.5)),
            ])),
          ]),
          if (facts.isNotEmpty || perms > 0) ...[
            const SizedBox(height: 8),
            for (final e in facts.entries)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 1.5),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SizedBox(width: 84, child: Text(_factLabels[e.key] ?? e.key, style: const TextStyle(color: C.muted, fontSize: 12.5))),
                  Expanded(child: Text('${e.value}', style: const TextStyle(fontSize: 12.5))),
                ]),
              ),
            if (perms > 0)
              Text('$perms permissions maangta hai', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ],
          if (flags.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final f in flags)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Icon(Icons.circle, size: 9, color: switch (f['level']) { 'high' => C.bad, 'medium' => C.warn, _ => C.faint }),
                  ),
                  const SizedBox(width: 8),
                  Expanded(child: Text(f['text'] as String? ?? '', style: const TextStyle(fontSize: 13))),
                ]),
              ),
          ],
          if ((v['advice'] as String? ?? '').isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
              child: Text(v['advice'] as String, style: const TextStyle(fontSize: 12.5, color: C.chip)),
            ),
          ],
          for (final l in limits)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text(l, style: const TextStyle(color: C.faint, fontSize: 11.5))),
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('File chalayi nahi gayi, sirf padhi gayi (REA).', style: TextStyle(color: C.faint, fontSize: 11)),
          ),
        ]),
      ),
    );
  }
}

/// Profile > App Jaanch: pick an APK / EXE someone sent and check it before installing.
class AppCheckScreen extends StatefulWidget {
  const AppCheckScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<AppCheckScreen> createState() => _AppCheckScreenState();
}

class _AppCheckScreenState extends State<AppCheckScreen> {
  Map<String, dynamic> _st = {};
  Map<String, dynamic>? _last;
  bool _loaded = false, _busy = false;
  String? _err;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.appcheckState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = null; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _pick() async {
    final res = await FilePicker.platform.pickFiles(withData: true);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    setState(() { _busy = true; _err = null; });
    try {
      final r = await app.api!.appcheckUpload(f.name, f.bytes!);
      if (mounted) setState(() => _last = r);
      await _load();
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _open(String id) async {
    try {
      final r = await app.api!.appcheckGet(id);
      if (mounted) setState(() => _last = r);
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final on = _st['enabled'] == true;
    final history = List<Map<String, dynamic>>.from((_st['history'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final last = _last;
    return Scaffold(
      appBar: AppBar(title: const Text('App Jaanch'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Kisi ne WhatsApp, SMS ya email par APK / EXE bheji hai? Install karne se pehle yahan jaanchiye. Hoola '
                'file ko chalata nahi, sirf padhta hai: kaunsi permissions (SMS / OTP, screen control), icon chhupta hai kya, kisne '
                'sign kiya, aur naam bank / KYC / challan wala fraud to nahi.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 12),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded && !on)
              const Glass(child: Text('App Jaanch abhi server par chalu nahi hai.', style: TextStyle(color: C.warn))),
            if (_loaded && on)
              GradientButton(
                label: _busy ? 'Jaanch ho rahi hai...' : 'File chuniye aur jaanchiye',
                icon: Icons.shield_rounded, height: 50, onTap: _busy ? null : _pick),
            if (_busy) const Padding(padding: EdgeInsets.only(top: 10), child: LinearProgressIndicator()),
            if (_err != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (last != null) ...[
              const SizedBox(height: 14),
              AppCheckCard(v: {...last, 'permissions': ((last['facts'] as Map?)?['permissions'] as List?)?.length ?? 0,
                  'facts': Map<String, dynamic>.from((last['facts'] as Map? ?? const {}))
                    ..removeWhere((k, v) => !_factLabels.containsKey(k) || v == null || v == '' || (v is List && v.isEmpty))}),
            ],
            if (history.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text('Pichhli jaanch', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              for (final h in history)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  leading: Icon(_vIcon(h['verdict'] as String? ?? ''), color: _vColor(h['verdict'] as String? ?? '')),
                  title: Text(h['name'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text((h['when'] as String? ?? '').split('T').first, style: const TextStyle(color: C.faint, fontSize: 12)),
                  onTap: () => _open(h['id'] as String),
                ),
            ],
            const SizedBox(height: 18),
            const Text('Yaad rakhiye: apps sirf Play Store se. Paise kat gaye hon to turant 1930 ya cybercrime.gov.in.',
                style: TextStyle(color: C.chip, fontSize: 12.5)),
          ]),
        ),
      ),
    );
  }
}
