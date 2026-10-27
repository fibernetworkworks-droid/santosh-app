/// v0.132 App Sahayak, part 4: the REAL native Android app from her approved design. Screens are written in Kotlin +
/// Jetpack Compose (tiles go writing -> compiling -> done, or 'saada' when a screen got its simple code version), the
/// build runs on Hoola's build machine, and the APK installs on her phone through Android's own Install screen (sha256
/// checked, package must be the app's own in.hoola.preview.* id). The project ZIP opens in Android Studio.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _stUi = {
  'writing': 'Kotlin likh raha', 'building': 'Compile ho raha', 'fixing': 'Galtiyan theek', 'ready': 'APK taiyaar',
  'zip': 'Project ZIP', 'failed': 'Dikkat', '': 'Shuru nahi',
};
const _tileUi = {
  'todo': ('…', C.faint), 'writing': ('likh raha', C.accent), 'written': ('likh di', C.teal), 'compiling': ('compile', C.teal),
  'fixing': ('theek', C.warn), 'done': ('✓', C.ok), 'code': ('saada', C.warn),
};

String _mb(dynamic b) => b == null ? '' : '${(_i(b) / 1024 / 1024).toStringAsFixed(1)} MB';

/// Download + check + Android's own Install screen.
Future<void> installPreview(BuildContext context, Santosh app, Map<String, dynamic> v) async {
  final apk = _map(v['apk']);
  final url = _s(v['apk_url']);
  if (url.isEmpty || apk.isEmpty) {
    _snack(context, 'APK link nahi mila (7 din purana ho gaya?). "Android app banao" dobara kahiye.');
    return;
  }
  final server = app.api!.absolute('/');
  _snack(context, 'APK download ho raha hai (${_mb(apk['size'])})…');
  final r = await Native.previewDownload(app.api!.absolute(url), _s(apk['sha256']), _s(apk['package']), server);
  if (!context.mounted) return;
  if (_s(r['error']).isNotEmpty || _s(r['path']).isEmpty) {
    _snack(context, _s(r['error']).isEmpty ? 'Download nahi hua.' : _s(r['error']));
    return;
  }
  final res = await Native.previewInstall(_s(r['path']), _s(apk['package']));
  if (!context.mounted) return;
  if (res == 'permission') {
    _snack(context, '"Install unknown apps" mein Hoola ko allow kijiye, phir dobara dabaiye.');
  } else if (res != null && res.isNotEmpty) {
    _snack(context, res);
  }
}

/// The build panel on the app design page.
class AndroidBuildPanel extends StatefulWidget {
  const AndroidBuildPanel({super.key, required this.app, required this.id, required this.approved});
  final Santosh app;
  final String id;
  final bool approved;
  @override
  State<AndroidBuildPanel> createState() => _AndroidBuildPanelState();
}

class _AndroidBuildPanelState extends State<AndroidBuildPanel> {
  Map<String, dynamic>? _v;
  int _tick = -1;
  bool _busy = false;
  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _tick = app.appTick;
    app.addListener(_on);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_on);
    super.dispose();
  }

  void _on() {
    if (app.appTick != _tick) {
      _tick = app.appTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final v = await app.api!.appAndroid(widget.id);
      if (mounted) setState(() => _v = v);
    } catch (_) {}
  }

  Future<void> _build([List<String>? redo]) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.appAct(widget.id, 'android', {if (redo != null) 'redo': redo});
      if (mounted) _snack(context, _s(r['say']).isEmpty ? 'Android app banna shuru' : _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v ?? const <String, dynamic>{};
    final st = _s(v['status']);
    final runner = _map(v['runner']);
    final screens = _list(v['screens']);
    final apk = _map(v['apk']);
    final stats = _map(v['stats']);
    final working = st == 'writing' || st == 'building' || st == 'fixing';
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.android_rounded, color: C.ok, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Asli Android app', style: display(15))),
        if (st.isNotEmpty) Pill(_stUi[st] ?? st, fg: st == 'ready' ? C.ok : st == 'failed' ? C.bad : C.accent),
      ]),
      const SizedBox(height: 6),
      if (!widget.approved)
        const Text('Pehle "Design pakka" kijiye: asli app usi naksha se banti hai.', style: TextStyle(color: C.muted, fontSize: 12.5))
      else if (st.isEmpty)
        Text('Kotlin + Jetpack Compose mein har screen likhunga, build machine par compile karke APK aapke phone par. '
            '${runner['ready'] == true ? 'Build: ${runner['where']}.' : 'Build machine abhi set nahi hai: project ZIP milega.'}',
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
      if (_s(v['now']).isNotEmpty) ...[
        const SizedBox(height: 4),
        Row(children: [
          if (working) const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
          if (working) const SizedBox(width: 8),
          Expanded(child: Text(_s(v['now']), style: const TextStyle(color: C.ink, fontSize: 12.5))),
        ]),
      ],
      if (screens.isNotEmpty && st.isNotEmpty) ...[
        const SizedBox(height: 8),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final s in screens)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), color: C.panel,
                  border: Border.all(color: (_tileUi[_s(s['state'])] ?? _tileUi['todo']!).$2.withOpacity(0.6))),
              child: Text('${s['label']} · ${(_tileUi[_s(s['state'])] ?? _tileUi['todo']!).$1}',
                  style: TextStyle(fontSize: 11.5, color: (_tileUi[_s(s['state'])] ?? _tileUi['todo']!).$2)),
            ),
        ]),
      ],
      if (_i(v['rounds']) > 0)
        Padding(padding: const EdgeInsets.only(top: 6),
            child: Text('Compile ke ${v['rounds']} round mein galtiyan theek ki', style: const TextStyle(color: C.faint, fontSize: 11.5))),
      if (st == 'failed' && _s(v['error']).isNotEmpty)
        Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(v['error']), style: const TextStyle(color: C.bad, fontSize: 12.5))),
      if (_s(v['note']).isNotEmpty)
        Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(v['note']), style: const TextStyle(color: C.muted, fontSize: 12.5))),
      if (apk.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('${apk['file']} · ${_mb(apk['size'])} · v${apk['version_name']}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (_i(stats['code']) > 0)
          Text('${stats['code']} screen saada version mein (dobara likhne ke liye "In screens ko dobara likho")',
              style: const TextStyle(color: C.warn, fontSize: 11.5)),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: GlassButton(label: 'Phone pe install karo', color: C.accent,
              onTap: _s(v['apk_url']).isEmpty ? null : () => installPreview(context, app, v))),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Kholo', onTap: () async {
            final ok = await Native.previewOpen(_s(apk['package']));
            if (!ok && context.mounted) _snack(context, 'Pehle install kijiye.');
          })),
        ]),
        const SizedBox(height: 4),
        const Text('Yeh preview build hai (aapke phone ke liye). Play Store par daalna agla kadam hai, aapke apne developer account se.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
      ],
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 6, children: [
        if (widget.approved && !working)
          GlassButton(label: st.isEmpty ? 'Android app banao' : 'Phir se banao', color: st.isEmpty ? C.accent : C.ink, height: 36,
              onTap: _busy ? null : () => _build()),
        if (widget.approved && !working && screens.any((s) => s['state'] == 'code'))
          GlassButton(label: 'Saada screens dobara likho', height: 36,
              onTap: _busy ? null : () => _build([for (final s in screens) if (s['state'] == 'code') _s(s['id'])])),
        if (_s(v['zip_url']).isNotEmpty)
          GlassButton(label: 'Project ZIP (${_mb(v['zip_size'])})', height: 36, onTap: () async {
            final u = app.api!.absolute(_s(v['zip_url']));
            await Clipboard.setData(ClipboardData(text: u));
            await launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication);
            if (context.mounted) _snack(context, 'ZIP ka link copy bhi ho gaya (laptop par Android Studio mein kholiye).');
          }),
      ]),
    ]);
  }
}

/// Chat / call card: one per app, updated in place.
class AndroidBuildCard extends StatelessWidget {
  const AndroidBuildCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final st = _s(v['status']);
    final screens = _list(v['screens']);
    final done = screens.where((s) => s['state'] == 'done' || s['state'] == 'written' || s['state'] == 'code').length;
    return Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.android_rounded, color: C.ok, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('${v['number']} · ${_s(v['name'])} · Android', style: display(14.5), maxLines: 1, overflow: TextOverflow.ellipsis)),
        Pill(_stUi[st] ?? st, fg: st == 'ready' ? C.ok : st == 'failed' ? C.bad : C.accent),
      ]),
      const SizedBox(height: 6),
      Text(_s(v['say']), style: const TextStyle(fontSize: 13)),
      if (screens.isNotEmpty && (st == 'writing' || st == 'building' || st == 'fixing')) ...[
        const SizedBox(height: 6),
        LinearProgressIndicator(value: screens.isEmpty ? null : done / screens.length, minHeight: 4),
      ],
      if (st == 'ready') ...[
        const SizedBox(height: 8),
        GlassButton(label: 'Phone pe install karo', color: C.accent, height: 36, onTap: () => installPreview(context, app, v)),
      ],
    ]));
  }
}
