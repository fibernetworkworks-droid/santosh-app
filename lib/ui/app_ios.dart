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
  'writing': 'Writing SwiftUI', 'building': 'Compiling on Mac', 'fixing': 'Fixing errors', 'uploading': 'Going to TestFlight',
  'ready': 'Ready', 'zip': 'Xcode ZIP', 'failed': 'Problem', '': 'Not started',
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
        title: const Text('Send to TestFlight?'),
        content: const Text('This build will go to TestFlight on your Apple account (only testers will see it). Sending to the App Store'
            'is your tap later in App Store Connect.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Not now')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, send')),
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
            '${_i(_map(v['stats'])['code']) > 0 ? ' (${_i(_map(v['stats'])['code'])} plain)' : ''}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (qa['ran'] == true) ...[
          const SizedBox(height: 6),
          Row(children: [
            Icon(qa['passed'] == true ? Icons.verified_rounded : Icons.error_outline_rounded,
                color: qa['passed'] == true ? C.ok : C.bad, size: 18),
            const SizedBox(width: 6),
            Expanded(child: Text('iPhone simulator: ${_i(qa['opened'])}/${_i(qa['total'])} screens opened without a crash', style: display(13))),
          ]),
          Wrap(spacing: 6, runSpacing: 6, children: [
            if (_map(qa['perf'])['launch_ms'] != null) Pill('Opens in ${_map(qa['perf'])['launch_ms']} ms', fg: C.ok),
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
          Text('The iPhone app compiles only on a Mac. One time:', style: display(12.5)),
          const Text('• Add server/app_builder/hoola-ios.yml to your private GitHub builds repo (.github/workflows/).\n'
              '• For TestFlight, add to that repo\'s Secrets: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8, APPLE_TEAM_ID'
              '(App Store Connect > Users and Access > Integrations; never put the key here or in chat).\n'
              '• In App Store Connect: My Apps > + > New App, with this same bundle ID.', style: TextStyle(color: C.muted, fontSize: 11.5)),
        ],
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: _s(v['build']) == '0' ? 'Make iPhone app' : 'Make iPhone app again', height: 36,
              onTap: _busy || working || !widget.approved ? null : () => _build('sim')),
          GlassButton(label: 'Send to TestFlight', color: C.accent, height: 36,
              onTap: _busy || working || st != 'ready' || runner['ready'] != true ? null : () => _build('testflight')),
          if (_s(v['zip_url']).isNotEmpty)
            GlassButton(label: 'Xcode project (ZIP)', height: 36,
                onTap: () => launchUrl(Uri.parse(app.api!.absolute(_s(v['zip_url']))), mode: LaunchMode.externalApplication)),
        ]),
      ],
    ]);
  }
}

/// v0.338 App Store from HER Apple account: steps, listing (edit within Apple's limits), push (listing + screenshots + the
/// TestFlight build, run in her builds repo with her key), Submit for Review only on her tap after a confirm.
class AppStorePanel extends StatefulWidget {
  const AppStorePanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppStorePanel> createState() => _AppStorePanelState();
}

class _AppStorePanelState extends State<AppStorePanel> {
  Map<String, dynamic>? _v;
  bool _busy = false;
  bool _open = false;
  final _f = <String, TextEditingController>{
    for (final k in ['name', 'subtitle', 'keywords', 'promotionalText', 'description']) k: TextEditingController(),
  };
  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _f.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _fill(Map<String, dynamic> v) {
    final l = _map(v['listing']);
    for (final e in _f.entries) {
      e.value.text = _s(l[e.key]);
    }
  }

  Future<void> _load() async {
    try {
      final v = Map<String, dynamic>.from(await app.api!.call('GET', '/api/apps/${widget.id}/appstore') as Map);
      if (!mounted) return;
      setState(() => _v = v);
      _fill(v);
      final st = _s(v['status']);
      if (st == 'pushing' || st == 'submitting') Future.delayed(const Duration(seconds: 10), () { if (mounted) _load(); });
    } catch (_) {}
  }

  Future<void> _act(String what, [Map<String, dynamic> body = const {}, String ok = '']) async {
    setState(() => _busy = true);
    try {
      final v = Map<String, dynamic>.from(await app.api!.call('POST', '/api/apps/${widget.id}/appstore/$what', body: body) as Map);
      if (!mounted) return;
      setState(() => _v = v);
      _fill(v);
      if (ok.isNotEmpty) _snack(context, ok);
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: const Text('Send for Apple review?'),
      content: const Text('Apple will review this version (usually 1-2 days). After it is approved, releasing to the App Store'
          'is also in your hands. Have you filled in App Information, Age Rating and App Privacy?'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Not now')),
        TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, send')),
      ],
    ));
    if (yes == true) await _act('submit', {'her_tap': true}, 'Sending for Apple review');
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final steps = _list(v?['steps']);
    final done = steps.where((x) => x['done'] == true).length;
    final st = _s(v?['status']);
    final working = st == 'pushing' || st == 'submitting';
    bool d(String id) => steps.any((x) => x['id'] == id && x['done'] == true);
    final lim = _map(v?['limits']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      InkWell(onTap: () => setState(() => _open = !_open), child: Row(children: [
        const Icon(Icons.phone_iphone_outlined, color: C.accent, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Apple App Store', style: display(15))),
        if (v != null) Pill('$done/${steps.length}', fg: done == steps.length ? C.ok : C.accent),
        Icon(_open ? Icons.expand_less : Icons.expand_more, color: C.muted),
      ])),
      if (_s(v?['now']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Row(children: [
        if (working) const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
        if (working) const SizedBox(width: 8),
        Expanded(child: Text(_s(v?['now']), style: const TextStyle(color: C.ink, fontSize: 12.5))),
      ])),
      if (_s(v?['error']).isNotEmpty) Text(_s(v?['error']), style: const TextStyle(color: C.bad, fontSize: 12.5)),
      if (_open && v != null) ...[
        const SizedBox(height: 6),
        for (final x in steps)
          Text('${x['done'] == true ? '✓' : '○'} ${_s(x['label'])}${_s(x['value']).isEmpty ? '' : ' · ${_s(x['value'])}'}',
              style: TextStyle(color: x['done'] == true ? C.ok : C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        for (final k in ['name', 'subtitle', 'keywords', 'promotionalText', 'description'])
          TextField(controller: _f[k], maxLines: k == 'description' ? 5 : 1, maxLength: _i(lim[k]) > 0 ? _i(lim[k]) : null,
              style: const TextStyle(color: C.ink, fontSize: 13),
              decoration: InputDecoration(labelText: const {'name': 'Name', 'subtitle': 'Subtitle', 'keywords': 'Keywords (comma separated)',
                  'promotionalText': 'Promotional text', 'description': 'Description'}[k])),
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: d('listing') ? 'Rewrite listing' : 'Make listing', height: 36,
              onTap: _busy || working ? null : () => _act('listing', {'regen': true})),
          if (d('listing'))
            GlassButton(label: 'Save changes', height: 36, onTap: _busy || working ? null : () => _act('listing',
                {'edit': {for (final e in _f.entries) e.key: e.value.text.trim()}}, 'Listing save')),
          GlassButton(label: 'Send to App Store Connect', height: 36,
              onTap: _busy || working || !d('testflight') || !d('listing') ? null : () => _act('push', {}, 'Sending (a few minutes)')),
          GlassButton(label: 'Send for review', color: C.accent, height: 36,
              onTap: _busy || working || !d('pushed') ? null : _submit),
        ]),
        const SizedBox(height: 8),
        Text('In App Store Connect you must do (once):', style: display(12.5)),
        for (final t in ((v['one_time'] as List?) ?? const [])) Text('• $t', style: const TextStyle(color: C.muted, fontSize: 11.5)),
        const SizedBox(height: 6),
        Text('Answers for App Privacy:', style: display(12.5)),
        for (final x in _list(v['privacy_answers']))
          Text('• ${_s(x['type'])} - ${_s(x['why'])}${x['linked'] == false ? ' (not linked)' : ''}',
              style: const TextStyle(color: C.muted, fontSize: 11.5)),
        Text('Age rating: ${_s(v['age_rating'])}', style: const TextStyle(color: C.muted, fontSize: 11.5)),
        Text('Privacy: ${_s(v['privacy_url'])}\nSupport: ${_s(v['support_url'])}', style: const TextStyle(color: C.faint, fontSize: 11)),
      ],
    ]);
  }
}

/// v0.342 her app's code in HER GitHub: one commit per build (Android + iPhone + README + CHANGELOG, never a key).
/// The button only makes the card in the chat; her tap on that card pushes.
class AppCodePanel extends StatefulWidget {
  const AppCodePanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppCodePanel> createState() => _AppCodePanelState();
}

class _AppCodePanelState extends State<AppCodePanel> {
  Map<String, dynamic>? _v;
  bool _busy = false;
  bool _private = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = Map<String, dynamic>.from(await widget.app.api!.call('GET', '/api/apps/${widget.id}/github') as Map);
      if (mounted) setState(() => _v = v);
    } catch (_) {}
  }

  Future<void> _card() async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.call('POST', '/api/apps/${widget.id}/github', body: {'private': _private});
      if (mounted) _snack(context, 'The card is in the chat: press yes there.');
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
    final commits = _list(v?['commits']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.code_rounded, color: C.accent, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Code in your GitHub', style: display(15))),
        if (commits.isNotEmpty) Pill('${commits.length} commits', fg: C.ok),
      ]),
      const SizedBox(height: 4),
      const Text('Full Android + iPhone code, every build a new commit. Signing keys never go.',
          style: TextStyle(color: C.muted, fontSize: 12)),
      if (v != null && v['linked'] != true)
        const Text('First add your GitHub token in Website > Hosting (only in the app).', style: TextStyle(color: C.warn, fontSize: 12)),
      Row(children: [
        Switch(value: _private, onChanged: (x) => setState(() => _private = x)),
        Text(_private ? 'Private repo' : 'Public repo (everyone can see)', style: const TextStyle(color: C.ink, fontSize: 12.5)),
      ]),
      GlassButton(label: 'Put code on GitHub', height: 36,
          onTap: _busy || v == null || v['linked'] != true || v['ready'] != true ? null : _card),
      for (final x in commits.take(3))
        Text('✓ build ${_s(x['build'])} · ${_s(x['repo'])} · ${_s(x['at']).substring(0, _s(x['at']).length >= 10 ? 10 : _s(x['at']).length)}',
            style: const TextStyle(color: C.ok, fontSize: 12)),
    ]);
  }
}

/// v0.343 DESIGN SE MILAAN: each real app screen next to her approved design, a 0-100 match, Opus's differences for the
/// low ones, and a rebuild of only those screens when she asks.
class MatchPanel extends StatefulWidget {
  const MatchPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<MatchPanel> createState() => _MatchPanelState();
}

class _MatchPanelState extends State<MatchPanel> {
  Map<String, dynamic>? _v;
  String _plat = 'android';
  bool _busy = false;
  bool _open = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = Map<String, dynamic>.from(await widget.app.api!.call('GET', '/api/apps/${widget.id}/match') as Map);
      if (mounted) setState(() => _v = v);
    } catch (_) {}
  }

  Future<void> _check(bool fix) async {
    if (fix) {
      final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        title: const Text('Rebuild these screens?'),
        content: const Text('Only the screens that match the design less will be rewritten by Opus (with the list of differences). The rest of the app stays the same.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Not now')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes')),
        ],
      ));
      if (yes != true) return;
    }
    setState(() => _busy = true);
    try {
      final v = Map<String, dynamic>.from(await widget.app.api!.call('POST', '/api/apps/${widget.id}/match',
          body: {'platform': _plat, 'fix': fix}) as Map);
      if (mounted) {
        setState(() => _v = v);
        _snack(context, _s(v['say']));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = _map(_map(_v?['match'])[_plat]);
    final rows = _list(m['screens']);
    final min = _i(m['min']) == 0 ? 70 : _i(m['min']);
    final low = rows.where((x) => _i(x['score']) < min).length;
    Widget pic(String path) => ClipRRect(borderRadius: BorderRadius.circular(8),
        child: Image.network(widget.app.api!.absolute(path), headers: widget.app.api!.authHeaders, height: 150, fit: BoxFit.fitHeight,
            errorBuilder: (_, __, ___) => const SizedBox(width: 70, height: 150)));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      InkWell(onTap: () => setState(() => _open = !_open), child: Row(children: [
        const Icon(Icons.compare_rounded, color: C.accent, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('Match with design', style: display(15))),
        if (m['avg'] != null) Pill('${m['avg']}%', fg: _i(m['avg']) >= min ? C.ok : C.warn),
        Icon(_open ? Icons.expand_less : Icons.expand_more, color: C.muted),
      ])),
      if (_open) ...[
        const SizedBox(height: 6),
        Row(children: [
          ChoiceChip(label: const Text('Android'), selected: _plat == 'android', onSelected: (_) => setState(() => _plat = 'android')),
          const SizedBox(width: 8),
          ChoiceChip(label: const Text('iPhone'), selected: _plat == 'ios', onSelected: (_) => setState(() => _plat = 'ios')),
        ]),
        if (rows.isEmpty)
          const Text('As soon as the device check screenshots arrive, the match for every screen will show here.', style: TextStyle(color: C.muted, fontSize: 12)),
        if (rows.isNotEmpty)
          Text(low == 0 ? 'All screens match the design.' : '$low screens match the design less.',
              style: TextStyle(color: low == 0 ? C.ok : C.warn, fontSize: 12.5)),
        for (final x in rows.take(12)) Padding(padding: const EdgeInsets.only(top: 10), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(x['label']), style: display(13))),
            Pill('${_i(x['score'])}%', fg: _i(x['score']) >= min ? C.ok : C.warn),
          ]),
          const SizedBox(height: 4),
          Row(children: [
            if (_s(x['design']).isNotEmpty) pic('/api/apps/${widget.id}/shots/${_s(x['design'])}'),
            const SizedBox(width: 8),
            pic('/api/apps/${widget.id}/$_plat/qa/${_s(x['id'])}'),
          ]),
          for (final d in ((x['differences'] as List?) ?? const []))
            Text('• $d', style: const TextStyle(color: C.muted, fontSize: 11.5)),
        ])),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: 'See differences from Opus', height: 36, onTap: _busy ? null : () => _check(false)),
          GlassButton(label: 'Fix (rebuild)', color: C.accent, height: 36,
              onTap: _busy || low == 0 ? null : () => _check(true)),
        ]),
      ],
    ]);
  }
}

/// v0.347 BHASHA: the languages her app carries (customers pick on My account); from the next build.
class BhashaPanel extends StatefulWidget {
  const BhashaPanel({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<BhashaPanel> createState() => _BhashaPanelState();
}

class _BhashaPanelState extends State<BhashaPanel> {
  Map<String, dynamic>? _v;
  List<String> _pick = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = Map<String, dynamic>.from(await widget.app.api!.call('GET', '/api/apps/${widget.id}/bhasha') as Map);
      if (mounted) setState(() { _v = v; _pick = ((v['langs'] as List?) ?? const []).map((e) => '$e').toList(); });
    } catch (_) {}
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.call('POST', '/api/apps/${widget.id}/bhasha', body: {'langs': _pick});
      if (mounted) _snack(context, 'From the next build the app will be in these languages.');
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final all = _map(_v?['all']);
    final cov = _map(_v?['coverage']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.translate_rounded, color: C.accent, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text('App language', style: display(15))),
        if (_i(_v?['words']) > 0) Pill('${_i(_v?['words'])} words', fg: C.ok),
      ]),
      const Text('Customers will pick a language in their account. The app opens in the first language. Your data, like product names and prices, stays as it is.',
          style: TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 6),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final e in all.entries)
          FilterChip(label: Text('${e.value}${cov[e.key] != null ? ' · ${cov[e.key]}%' : ''}'), selected: _pick.contains(e.key),
              onSelected: (on) => setState(() {
                    if (on && !_pick.contains(e.key) && _pick.length < 6) _pick.add(e.key);
                    if (!on) _pick.remove(e.key);
                  })),
      ]),
      const SizedBox(height: 6),
      GlassButton(label: 'Confirm languages', height: 36, onTap: _busy || _pick.isEmpty ? null : _save),
    ]);
  }
}
