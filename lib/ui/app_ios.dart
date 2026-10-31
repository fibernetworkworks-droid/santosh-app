/// v0.332 IPHONE: the REAL iPhone app from her approved design (same design, same backend as Android). Screens are written
/// in Swift + SwiftUI, compiled on a Mac (her GitHub builds repo), every screen opened in an iPhone simulator; 'TestFlight
/// par bhejo' uploads it with HER App Store Connect key, which stays a secret in her builds repo (never in this app or chat).
/// App Store review / release stays her tap in App Store Connect.
library;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _stUi = {
  'writing': 'SwiftUI likh raha', 'building': 'Mac par compile', 'fixing': 'Galtiyan theek', 'uploading': 'TestFlight par ja rahi',
  'ready': 'Taiyaar', 'zip': 'Xcode ZIP', 'failed': 'Dikkat', '': 'Shuru nahi',
};

class IosBuildPanel extends StatefulWidget {
  const IosBuildPanel({super.key, required this.app, required this.id, required this.approved});
  final Santosh app;
  final String id;
  final bool approved;
  @override
  State<IosBuildPanel> createState() => _IosBuildPanelState();
}

class _IosBuildPanelState extends State<IosBuildPanel> {
  Map<String, dynamic>? _v;
  bool _busy = false;
  bool _open = false;
  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = Map<String, dynamic>.from(await app.api!.call('GET', '/api/apps/${widget.id}/ios') as Map);
      if (mounted) setState(() => _v = v);
      final st = _s(v['status']);
      if (st == 'writing' || st == 'building' || st == 'fixing' || st == 'uploading') {
        Future.delayed(const Duration(seconds: 8), () { if (mounted) _load(); });
      }
    } catch (_) {}
  }

  Future<void> _build(String kind) async {
    if (kind == 'testflight') {
      final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        title: const Text('TestFlight par bhejein?'),
        content: const Text('Yeh build aapke Apple account ke TestFlight par jayegi (sirf testers dekhenge). App Store par bhejna '
            'baad mein App Store Connect mein aapka tap hai.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Abhi nahi')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, bhejo')),
        ],
      ));
      if (yes != true) return;
    }
    setState(() => _busy = true);
    try {
      final v = Map<String, dynamic>.from(await app.api!.call('POST', '/api/apps/${widget.id}/ios', body: {'kind': kind}) as Map);
      if (mounted) setState(() => _v = v);
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final st = _s(v?['status']);
    final working = st == 'writing' || st == 'building' || st == 'fixing' || st == 'uploading';
    final qa = _map(v?['qa']);
    final tf = _map(v?['testflight']);
    final runner = _map(v?['runner']);
    final shots = ((qa['shots'] as List?) ?? const []).map((e) => '$e').toList();
    final scr = _list(v?['screens']);
    final done = scr.where((x) => x['state'] == 'done' || x['state'] == 'code').length;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      InkWell(onTap: () => setState(() => _open = !_open), child: Row(children: [
        const Icon(Icons.phone_iphone_rounded, color: C.accent, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('iPhone app', style: display(15))),
        Pill(_stUi[st] ?? st, fg: st == 'ready' ? C.ok : st == 'failed' ? C.bad : C.accent),
        Icon(_open ? Icons.expand_less : Icons.expand_more, color: C.muted),
      ])),
      if (v != null) Padding(padding: const EdgeInsets.only(top: 4), child: Row(children: [
        if (working) const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
        if (working) const SizedBox(width: 8),
        Expanded(child: Text(_s(v['now']).isNotEmpty ? _s(v['now']) : _s(v['say']), style: const TextStyle(color: C.ink, fontSize: 12.5))),
      ])),
      if (_s(v?['error']).isNotEmpty) Text(_s(v?['error']), style: const TextStyle(color: C.bad, fontSize: 12.5)),
      if (tf.isNotEmpty)
        Text('TestFlight: v${_s(tf['version'])} (build ${_s(tf['build'])})', style: const TextStyle(color: C.ok, fontSize: 12.5)),
      if (_open && v != null) ...[
        const SizedBox(height: 6),
        Text('Bundle ID: ${_s(v['bundle_id'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (scr.isNotEmpty) Text('Screens: $done/${scr.length}'
            '${_i(_map(v['stats'])['code']) > 0 ? ' (${_i(_map(v['stats'])['code'])} saada)' : ''}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (qa['ran'] == true) ...[
          const SizedBox(height: 6),
          Row(children: [
            Icon(qa['passed'] == true ? Icons.verified_rounded : Icons.error_outline_rounded,
                color: qa['passed'] == true ? C.ok : C.bad, size: 18),
            const SizedBox(width: 6),
            Expanded(child: Text('iPhone simulator: ${_i(qa['opened'])}/${_i(qa['total'])} screens bina crash ke khuli', style: display(13))),
          ]),
          Wrap(spacing: 6, runSpacing: 6, children: [
            if (_map(qa['perf'])['launch_ms'] != null) Pill('Khulti hai ${_map(qa['perf'])['launch_ms']} ms', fg: C.ok),
            if (_map(qa['perf'])['app_mb'] != null) Pill('App ${_map(qa['perf'])['app_mb']} MB', fg: C.ok),
          ]),
          if (shots.isNotEmpty) ...[
            const SizedBox(height: 6),
            SizedBox(height: 190, child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final sh in shots)
                Padding(padding: const EdgeInsets.only(right: 6), child: ClipRRect(borderRadius: BorderRadius.circular(10),
                    child: Image.network(app.api!.absolute('/api/apps/${widget.id}/ios/qa/$sh'), headers: app.api!.authHeaders,
                        height: 190, fit: BoxFit.fitHeight, errorBuilder: (_, __, ___) => const SizedBox(width: 1)))),
            ])),
          ],
        ],
        if (runner['ready'] != true) ...[
          const SizedBox(height: 6),
          Text('iPhone app sirf Mac par compile hoti hai. Ek baar:', style: display(12.5)),
          const Text('• Apne private GitHub builds repo mein server/app_builder/hoola-ios.yml daaliye (.github/workflows/).\n'
              '• TestFlight ke liye usi repo ke Secrets mein: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8, APPLE_TEAM_ID '
              '(App Store Connect > Users and Access > Integrations; key yahan ya chat mein kabhi nahi).\n'
              '• App Store Connect mein My Apps > + > New App, isi bundle ID se.', style: TextStyle(color: C.muted, fontSize: 11.5)),
        ],
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: _s(v['build']) == '0' ? 'iPhone app banao' : 'iPhone app dobara banao', height: 36,
              onTap: _busy || working || !widget.approved ? null : () => _build('sim')),
          GlassButton(label: 'TestFlight par bhejo', color: C.accent, height: 36,
              onTap: _busy || working || st != 'ready' || runner['ready'] != true ? null : () => _build('testflight')),
          if (_s(v['zip_url']).isNotEmpty)
            GlassButton(label: 'Xcode project (ZIP)', height: 36,
                onTap: () => launchUrl(Uri.parse(app.api!.absolute(_s(v['zip_url']))), mode: LaunchMode.externalApplication)),
        ]),
      ],
    ]);
  }
}
