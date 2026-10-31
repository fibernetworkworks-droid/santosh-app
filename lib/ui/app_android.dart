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

  List<Map<String, dynamic>> _crashes = const [];

  Future<void> _load() async {
    try {
      final v = await app.api!.appAndroid(widget.id);
      if (mounted) setState(() => _v = v);
    } catch (_) {}
    try {   // v0.325 crashes her app's users' phones sent
      final c = await app.api!.call('GET', '/api/apps/${widget.id}/crashes');
      if (mounted) setState(() => _crashes = _list((c as Map?)?['crashes']));
    } catch (_) {}
  }

  Future<void> _rollback(int build) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.appAct(widget.id, 'rollback', {'build': build});
      if (mounted) _snack(context, _s(r['now']).isEmpty ? 'Build $build wapas aa rahi hai' : _s(r['now']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _fixCrash(String crash) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.appAct(widget.id, 'fix_crash', {'crash': crash});
      if (mounted) _snack(context, _s(r['say']).isEmpty ? 'Crash theek ho raha hai' : _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
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
      if (_map(v['qa']).isNotEmpty) _QaBox(app: app, id: widget.id, qa: _map(v['qa'])),
      if (_list(v['history']).isNotEmpty) ...[       // v0.325 every build: what changed, and a way back
        const SizedBox(height: 10),
        Text('Versions (${_list(v['history']).length})', style: display(13)),
        for (final (i, h) in _list(v['history']).take(6).indexed)
          Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('v${_s(h['version_name'])} · build ${_i(h['build'])}${i == 0 ? ' · abhi wali' : ''}',
                    style: TextStyle(color: i == 0 ? C.ok : C.ink, fontWeight: FontWeight.w700, fontSize: 12.5)),
                for (final n in ((h['notes'] as List?) ?? const []).take(3))
                  Text('• $n', style: const TextStyle(color: C.muted, fontSize: 11.5)),
              ])),
              if (i > 0 && !working && ((v['kept_builds'] as List?) ?? const []).contains(h['build']))
                TextButton(onPressed: _busy ? null : () => _rollback(_i(h['build'])), child: const Text('Wapas lao')),
            ]),
          ),
      ],
      if (_crashes.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Users ke phone pe crash (${_crashes.length})', style: display(13)),
        for (final c in _crashes.take(5))
          Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
            child: Row(children: [
              Expanded(child: Text('${_s(c['exception']).split(':').first} · ${_i(c['count'])} baar'
                  '${((c['screens'] as List?) ?? const []).isEmpty ? '' : ' · ${(c['screens'] as List).join(', ')}'} · ${_s(c['status'])}',
                  style: TextStyle(color: _s(c['status']) == 'fixing' ? C.muted : C.warn, fontSize: 12))),
              if (_s(c['status']) == 'new' || _s(c['status']) == 'back')
                TextButton(onPressed: _busy ? null : () => _fixCrash(_s(c['id'])), child: const Text('Theek karo')),
            ]),
          ),
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

/// v0.325 HOOLA QA: what the device check found on a real Android emulator after this build compiled.
class _QaBox extends StatelessWidget {
  const _QaBox({required this.app, required this.id, required this.qa});
  final Santosh app;
  final String id;
  final Map<String, dynamic> qa;

  @override
  Widget build(BuildContext context) {
    if (qa['ran'] != true) {
      return Padding(padding: const EdgeInsets.only(top: 8),
          child: Text('Device check nahi chala: ${_s(qa['why'])}', style: const TextStyle(color: C.faint, fontSize: 11.5)));
    }
    final perf = _map(qa['perf']);
    final budget = _map(qa['budget']);
    final shots = ((qa['shots'] as List?) ?? const []).map((e) => '$e').toList();
    final a11y = _list(qa['a11y']);
    Color c(String k) => budget[k] == 'over' ? C.warn : C.ok;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SizedBox(height: 10),
      Row(children: [
        Icon(qa['passed'] == true ? Icons.verified_rounded : Icons.error_outline_rounded,
            color: qa['passed'] == true ? C.ok : C.bad, size: 18),
        const SizedBox(width: 6),
        Expanded(child: Text('Device check: ${_i(qa['opened'])}/${_i(qa['total'])} screens bina crash ke khuli', style: display(13))),
      ]),
      const SizedBox(height: 4),
      Wrap(spacing: 6, runSpacing: 6, children: [
        if (perf['cold_ms'] != null) Pill('Khulti hai ${perf['cold_ms']} ms', fg: c('cold_ms')),
        if (perf['jank_pct'] != null) Pill('Janky frames ${perf['jank_pct']}%', fg: c('jank_pct')),
        if (perf['apk_mb'] != null) Pill('APK ${perf['apk_mb']} MB', fg: c('apk_mb')),
        Pill('${_i(qa['a11y_count'])} accessibility', fg: _i(qa['a11y_count']) == 0 ? C.ok : C.warn),
      ]),
      if (((qa['crashed'] as List?) ?? const []).isNotEmpty)
        Text('Crash: ${(qa['crashed'] as List).join(', ')} (inhe saada version mila)', style: const TextStyle(color: C.bad, fontSize: 12)),
      for (final f in a11y.take(4))
        Text('• ${_s(f['screen'])}: ${_s(f['text'])}', style: const TextStyle(color: C.muted, fontSize: 11.5)),
      if (shots.isNotEmpty) ...[
        const SizedBox(height: 6),
        SizedBox(height: 170, child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final sh in shots)
            Padding(padding: const EdgeInsets.only(right: 6), child: ClipRRect(borderRadius: BorderRadius.circular(8),
                child: Image.network(app.api!.absolute('/api/apps/$id/android/qa/$sh'), headers: app.api!.authHeaders,
                    height: 170, fit: BoxFit.fitHeight, errorBuilder: (_, __, ___) => const SizedBox(width: 1)))),
        ])),
      ],
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

/// v0.314 ASLI APP: her app's own backend on the app design page. Every list the installed app keeps (orders, bookings,
/// requests, or a staff app's tables) with its newest rows; she moves a row's status with one tap, and makes an account
/// staff / admin (a staff app's new account sees nothing until she does). New orders also reach her chat by themselves.
class AppDataPanel extends StatefulWidget {
  const AppDataPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppDataPanel> createState() => _AppDataPanelState();
}

class _AppDataPanelState extends State<AppDataPanel> {
  Map<String, dynamic>? _v;
  String _coll = '';
  List<Map<String, dynamic>> _rows = const [];
  List<Map<String, dynamic>>? _members;
  bool _busy = false;
  String _err = '';
  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await app.api!.appData(widget.id);
      final colls = _list(v['collections']);
      final coll = _coll.isNotEmpty ? _coll : (_s(v['order']).isNotEmpty ? _s(v['order']) : (colls.isEmpty ? '' : _s(colls.first['key'])));
      final rows = coll.isEmpty ? <Map<String, dynamic>>[] : await app.api!.appRows(widget.id, coll);
      if (mounted) setState(() { _v = v; _coll = coll; _rows = rows; _err = ''; });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _pick(String coll) async {
    setState(() { _coll = coll; _rows = const []; });
    await _load();
  }

  Future<void> _status(Map<String, dynamic> r, String to) => _set(r, {'status': to});

  Future<void> _set(Map<String, dynamic> r, Map<String, dynamic> set) async {
    setState(() => _busy = true);
    try {
      await app.api!.appRowSet(widget.id, _coll, _s(r['id']), set);
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadMembers() async {
    try {
      final m = await app.api!.appMembers(widget.id);
      if (mounted) setState(() => _members = m);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _role(Map<String, dynamic> m, String role) async {
    try {
      await app.api!.appMemberRole(widget.id, _s(m['id']), role);
      await _loadMembers();
      if (mounted) _snack(context, '${_s(m['email'])}: $role');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final colls = _list(v?['collections']);
    final counts = _map(v?['counts']);
    final cur = colls.firstWhere((c) => _s(c['key']) == _coll, orElse: () => const <String, dynamic>{});
    final fields = _list(cur['fields']);
    final status = fields.firstWhere((f) => _s(f['key']) == 'status', orElse: () => const <String, dynamic>{});
    final opts = ((status['options'] as List?) ?? const []).map((e) => '$e').toList();
    final shown = fields.where((f) => !['status', 'total', 'items', 'paid', 'utr'].contains(_s(f['key']))).take(5).toList();
    final headKey = shown.isEmpty ? 'id' : _s(shown.first['key']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.storage_rounded, color: C.teal, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('App ka data', style: display(15))),
        if (v != null) Pill('${_i(counts['members'])} accounts', fg: C.teal),
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: C.muted, size: 20), tooltip: 'Taaza karo'),
      ]),
      if (_err.isNotEmpty)
        Text(_err, style: const TextStyle(color: C.bad, fontSize: 12.5))
      else if (v == null)
        const Text('Load ho raha hai…', style: TextStyle(color: C.muted, fontSize: 12.5))
      else ...[
        Text(v['live'] == true
            ? 'Aapki app ke log yahin order / booking karte hain; har nayi entry chat mein bhi aati hai.'
            : 'Android app banne ke baad yahan asli orders / bookings aayengi.',
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        SingleChildScrollView(scrollDirection: Axis.horizontal, child: Row(children: [
          for (final c in colls)
            Padding(padding: const EdgeInsets.only(right: 6), child: ChoiceChip(
              label: Text('${_s(c['label'])} ${_i(counts[_s(c['key'])])}'),
              selected: _s(c['key']) == _coll,
              onSelected: (_) => _pick(_s(c['key'])),
            )),
        ])),
        const SizedBox(height: 8),
        if (_rows.isEmpty) const Text('Abhi koi entry nahi.', style: TextStyle(color: C.faint, fontSize: 12.5)),
        for (final r in _rows.take(30))
          Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(r[headKey]).isEmpty ? _s(r['id']) : _s(r[headKey]),
                    style: const TextStyle(color: C.ink, fontWeight: FontWeight.w700))),
                if (_s(r['status']).isNotEmpty) Pill(_s(r['status']), fg: C.accent),
              ]),
              if (_s(r['items']).isNotEmpty) Text(_s(r['items']), style: const TextStyle(color: C.chip, fontSize: 12.5)),
              if (r['total'] is num && (r['total'] as num) > 0)
                Text('₹${(r['total'] as num).toStringAsFixed((r['total'] as num) % 1 == 0 ? 0 : 2)}',
                    style: const TextStyle(color: C.ok, fontWeight: FontWeight.w800)),
              // v0.319 photos her app's users sent, delivery locations (tap = map), the UPI "I have paid" claim
              for (final f in fields.where((f) => _s(f['type']) == 'photo' && _s(r[_s(f['key'])]).startsWith('f_')).take(2))
                Padding(padding: const EdgeInsets.only(top: 6), child: ClipRRect(borderRadius: BorderRadius.circular(10),
                    child: Image.network(app.api!.absolute('/api/apps/${widget.id}/files/${_s(r[_s(f['key'])])}'),
                        headers: app.api!.authHeaders, height: 150, width: double.infinity, fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const SizedBox.shrink()))),
              for (final f in shown.skip(1))
                if (_s(r[_s(f['key'])]).isNotEmpty && _s(f['type']) != 'photo')
                  _s(f['type']) == 'location'
                      ? InkWell(
                          onTap: () => launchUrl(Uri.parse('https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(_s(r[_s(f['key'])]))}'),
                              mode: LaunchMode.externalApplication),
                          child: Text('${_s(f['label'])}: ${_s(r[_s(f['key'])])} (map)', style: const TextStyle(color: C.teal, fontSize: 12)))
                      : Text('${_s(f['label'])}: ${_s(r[_s(f['key'])])}', style: const TextStyle(color: C.muted, fontSize: 12)),
              if (_s(r['paid']).isNotEmpty && _s(r['paid']) != 'No')
                Row(children: [
                  Expanded(child: Text('${_s(r['paid'])}${_s(r['utr']).isEmpty ? '' : ' · UTR ${_s(r['utr'])}'}',
                      style: TextStyle(color: _s(r['paid']) == 'Verified' ? C.ok : C.warn, fontSize: 12.5, fontWeight: FontWeight.w700))),
                  if (_s(r['paid']) == 'Customer says paid')
                    TextButton(onPressed: _busy ? null : () => _set(r, {'paid': 'Verified'}), child: const Text('Bank mein mila: Verified')),
                ]),
              if (opts.isNotEmpty) ...[
                const SizedBox(height: 6),
                SingleChildScrollView(scrollDirection: Axis.horizontal, child: Row(children: [
                  for (final o in opts)
                    Padding(padding: const EdgeInsets.only(right: 6), child: ChoiceChip(
                      label: Text(o, style: const TextStyle(fontSize: 12)),
                      selected: _s(r['status']) == o,
                      onSelected: _busy || _s(r['status']) == o ? null : (_) => _status(r, o),
                    )),
                ])),
              ],
            ]),
          ),
        const SizedBox(height: 4),
        TextButton.icon(
          onPressed: _members == null ? _loadMembers : () => setState(() => _members = null),
          icon: const Icon(Icons.people_alt_rounded, size: 18),
          label: Text(_members == null ? 'Accounts aur roles' : 'Accounts chhupao'),
        ),
        if (_members != null)
          for (final m in _members!)
            Row(children: [
              Expanded(child: Text('${_s(m['name']).isEmpty ? _s(m['email']) : _s(m['name'])} · ${_s(m['email'])}',
                  style: const TextStyle(color: C.ink, fontSize: 12.5))),
              DropdownButton<String>(
                value: ['member', 'staff', 'admin'].contains(_s(m['role'])) ? _s(m['role']) : 'member',
                dropdownColor: C.bgBottom,
                items: const [
                  DropdownMenuItem(value: 'member', child: Text('member')),
                  DropdownMenuItem(value: 'staff', child: Text('staff')),
                  DropdownMenuItem(value: 'admin', child: Text('admin')),
                ],
                onChanged: (x) { if (x != null && x != _s(m['role'])) _role(m, x); },
              ),
            ]),
      ],
    ]);
  }
}
