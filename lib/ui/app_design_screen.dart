/// Profile > "<name> · App designer" (v0.128 App Sahayak, part 1): a few words -> plan of every screen (her Haan) ->
/// 3 Home-screen looks (her choice) -> every screen designed while she watches (tiles with real screenshots) ->
/// checks on Android + iPhone -> tap-through prototype -> changes in her words -> "Confirm design" (her tap, exact hash).
/// One chat card per app design, updated in place (also inside calls).
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';
import 'app_money.dart';
import 'app_logic.dart';
import 'app_safety.dart';
import 'app_owndb.dart';
import 'app_track.dart';
import 'app_pay.dart';
import 'app_connect.dart';
import 'app_components.dart';
import 'app_family.dart';
import 'app_jaanch.dart';
import 'app_naksha.dart';
import 'app_ops.dart';
import 'app_login.dart';
import 'app_android.dart';
import 'app_ios.dart';
import 'site_screen.dart' show SiteStages;

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _statusUi = {
  'draft': 'Start', 'planned': 'Plan: your yes', 'looks': 'Choose a look', 'designing': 'Making screens', 'checking': 'Checking',
  'ready': 'Design ready', 'approved': 'Design confirmed', 'failed': 'Problem', 'stopped': 'Stopped',
};
Color _stCol(String s) => switch (s) {
      'ready' => C.accent, 'approved' => C.ok, 'planned' || 'looks' => C.accent, 'failed' => C.bad,
      'designing' || 'checking' => C.teal, _ => C.chip };
const _stateCol = {'done': C.ok, 'building': C.accent, 'fixing': C.warn, 'failed': C.bad};

Color _hex(String h, [Color or = C.chip]) {
  final v = h.replaceAll('#', '');
  if (v.length != 6) return or;
  return Color(int.parse('FF$v', radix: 16));
}

/// A screenshot of one screen (needs the key).
class AppShot extends StatelessWidget {
  const AppShot({super.key, required this.app, required this.appId, required this.name, this.width = 120, this.fit = BoxFit.cover});
  final Santosh app;
  final String appId;
  final String name;
  final double width;
  final BoxFit fit;
  @override
  Widget build(BuildContext context) {
    final h = width * 844 / 390;
    if (name.isEmpty || app.api == null) {
      return Container(width: width, height: h, decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(14)),
          child: const Center(child: Icon(Icons.phone_android_rounded, color: C.faint)));
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(width / 9),
      child: Image.network(app.api!.absolute('/api/apps/$appId/shots/$name'), headers: app.api!.authHeaders, width: width, height: h,
          fit: fit, alignment: Alignment.topCenter, cacheWidth: (width * 2.5).round(),
          errorBuilder: (_, __, ___) => SizedBox(width: width, height: h, child: const Center(child: Icon(Icons.broken_image_outlined))),
          loadingBuilder: (c, w, p) => p == null ? w : SizedBox(width: width, height: h, child: const Center(child: CircularProgressIndicator()))),
    );
  }
}

void _openShot(BuildContext context, Santosh app, String appId, String name, String title) {
  Navigator.of(context).push(MaterialPageRoute(builder: (_) => Scaffold(
        appBar: AppBar(title: Text(title)),
        body: InteractiveViewer(maxScale: 4, child: Center(child: Image.network(app.api!.absolute('/api/apps/$appId/shots/$name'),
            headers: app.api!.authHeaders, fit: BoxFit.contain))),
      )));
}

/// Every screen as a tile: grey -> designing -> done with its real screenshot.
class AppScreenGrid extends StatelessWidget {
  const AppScreenGrid({super.key, required this.app, required this.v, this.compact = false});
  final Santosh app;
  final Map<String, dynamic> v;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    final b = _map(v['board']);
    final id = _s(v['id']);
    final tiles = [for (final p in _list(b['pages'])) for (final s in _list(p['sections'])) s];
    final w = compact ? 64.0 : 96.0;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (_s(b['now']).isNotEmpty)
        Text('Now: ${b['now']}', style: const TextStyle(color: C.ink, fontWeight: FontWeight.w700, fontSize: 13)),
      const SizedBox(height: 6),
      ClipRRect(
        borderRadius: BorderRadius.circular(99),
        child: LinearProgressIndicator(value: _i(b['pct']) / 100, minHeight: 6, color: C.teal, backgroundColor: const Color(0x22FFFFFF)),
      ),
      const SizedBox(height: 4),
      Text('${b['done'] ?? 0} / ${b['total'] ?? 0} screens · ${b['pct'] ?? 0}%', style: const TextStyle(color: C.faint, fontSize: 11.5)),
      const SizedBox(height: 8),
      SizedBox(
        height: w * 844 / 390 + 34,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: tiles.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) {
            final t = tiles[i];
            final col = _stateCol[t['state']] ?? const Color(0x33FFFFFF);
            final thumb = _s(t['thumb']);
            return GestureDetector(
              onTap: thumb.isEmpty ? null : () => _openShot(context, app, id, thumb.replaceFirst('thumb/', ''), _s(t['label'])),
              child: SizedBox(
                width: w,
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Container(
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(w / 8), border: Border.all(color: col.withOpacity(.7), width: 1.5)),
                    child: thumb.isNotEmpty
                        ? AppShot(app: app, appId: id, name: thumb, width: w - 3)
                        : SizedBox(width: w - 3, height: (w - 3) * 844 / 390,
                            child: Center(child: t['state'] == 'building'
                                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                                : Icon(t['state'] == 'done' ? Icons.check_rounded : Icons.phone_android_rounded, color: col))),
                  ),
                  const SizedBox(height: 4),
                  Text(_s(t['label']), maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _stateCol[t['state']] ?? C.faint)),
                ]),
              ),
            );
          },
        ),
      ),
    ]);
  }
}

class AppLooks extends StatefulWidget {
  const AppLooks({super.key, required this.app, required this.v});
  final Santosh app;
  final Map<String, dynamic> v;
  @override
  State<AppLooks> createState() => _AppLooksState();
}

class _AppLooksState extends State<AppLooks> {
  int? _colorsFrom;
  bool _busy = false;
  @override
  Widget build(BuildContext context) {
    final looks = _list(widget.v['looks']);
    final id = _s(widget.v['id']);
    if (looks.isEmpty) return const Text('Making the looks…', style: TextStyle(color: C.faint));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(
        height: 410,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: looks.length,
          separatorBuilder: (_, __) => const SizedBox(width: 12),
          itemBuilder: (_, i) {
            final lk = looks[i];
            final cols = (lk['colors'] as List? ?? const []).map((e) => _hex(_s(e))).toList();
            final shot = _s(_map(lk['shots'])['android']);
            return SizedBox(
              width: 160,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                GestureDetector(onTap: shot.isEmpty ? null : () => _openShot(context, widget.app, id, shot, _s(lk['label'])),
                    child: AppShot(app: widget.app, appId: id, name: shot, width: 160)),
                const SizedBox(height: 4),
                Text('${i + 1}. ${lk['label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
                Row(children: [for (final c in cols) Container(width: 14, height: 14, margin: const EdgeInsets.only(right: 4, top: 4),
                    decoration: BoxDecoration(color: c, shape: BoxShape.circle, border: Border.all(color: const Color(0x44FFFFFF))))]),
                // v0.140 the look's own design DNA (Opus's art direction)
                if (_s(_map(lk['art'])['concept']).isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(_s(_map(lk['art'])['concept']), maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: C.accent, fontSize: 11.5, fontWeight: FontWeight.w700)),
                  Text(_s(_map(lk['art'])['signature']), maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: C.faint, fontSize: 11)),
                ],
                const Spacer(),
                Row(children: [
                  Expanded(child: GlassButton(label: 'This one', height: 34, color: C.accent, onTap: _busy ? null : () => _choose(i))),
                  IconButton(
                    tooltip: 'Its colours',
                    onPressed: () => setState(() => _colorsFrom = _colorsFrom == i ? null : i),
                    icon: Icon(Icons.palette_rounded, color: _colorsFrom == i ? C.accent : C.faint, size: 20),
                  ),
                ]),
              ]),
            );
          },
        ),
      ),
      if (_colorsFrom != null) Text('The colours of look ${_colorsFrom! + 1} will be used', style: const TextStyle(color: C.accent, fontSize: 12)),
    ]);
  }

  Future<void> _choose(int i) async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.appAct(_s(widget.v['id']), 'look', {'index': i, if (_colorsFrom != null) 'colors_from': _colorsFrom});
      if (mounted) _snack(context, 'Started making screens! Each screen shows as soon as it is ready.');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

Future<void> _approve(BuildContext context, Santosh app, Map<String, dynamic> v) async {
  final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        title: const Text('Confirm the design?'),
        content: Text('This ${v['board']?['total'] ?? ''}-screen design (v${v['version']}) will become the blueprint of the real Android / iPhone app. '
            'You can change it later, but you will have to confirm again.'),
        actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Not now')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, confirm'))],
      ));
  if (yes != true) return;
  try {
    final r = await app.api!.appAct(_s(v['id']), 'approve', {'hash': _s(v['hash'])});
    if (context.mounted) _snack(context, _s(r['say']).isEmpty ? 'Design confirmed!' : _s(r['say']));
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
  }
}

void _openPreview(BuildContext context, Santosh app, Map<String, dynamic> v) {
  if (_s(v['preview']).isEmpty) return;
  Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppPreview(app: app, url: _s(v['preview']), title: _s(v['name']))));
}

// ---------------------------------------------------------------- chat / call card
class AppBoardCard extends StatelessWidget {
  const AppBoardCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final st = _s(v['status']);
    final id = _s(v['id']);
    final plan = _map(v['plan']);
    void open() => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppDesignPage(app: app, id: id)));
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.phone_android_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['number']} · ${_s(v['name']).isEmpty ? v['field_label'] : v['name']} app',
              style: display(15), maxLines: 1, overflow: TextOverflow.ellipsis)),
          Pill(_statusUi[st] ?? st, fg: _stCol(st)),
        ]),
        const SizedBox(height: 8),
        SiteStages(v: v),
        const SizedBox(height: 8),
        if (_s(v['say']).isNotEmpty) Text(_s(v['say']), style: const TextStyle(color: C.chip, fontSize: 13)),
        if (st == 'planned') ...[
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final s in _list(plan['screens']).take(14))
              Pill('${s['tab'] == true ? '▣ ' : ''}${s['label']}', fg: s['tab'] == true ? C.accent : C.chip),
            for (final s in _list(plan['code_screens'])) Pill('⚖ ${s['label']}', fg: C.faint),
          ]),
          const SizedBox(height: 8),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(onPressed: open, child: const Text('View / reply')),
            const SizedBox(width: 6),
            GlassButton(label: 'Yes, make 3 looks', height: 38, color: C.accent, onTap: () async {
              try {
                await app.api!.appAct(id, 'plan');
                if (context.mounted) _snack(context, 'Making 3 looks of the home screen.');
              } catch (e) {
                if (context.mounted) _snack(context, '$e');
              }
            }),
          ]),
        ],
        if (st == 'looks') ...[const SizedBox(height: 8), AppLooks(app: app, v: v)],
        if (st == 'designing' || st == 'checking') ...[
          const SizedBox(height: 8),
          AppScreenGrid(app: app, v: v, compact: true),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(onPressed: () => app.api!.appAct(id, 'stop'), child: const Text('Rokiye')),
            TextButton(onPressed: () => _openPreview(context, app, v), child: const Text('Prototype')),
            GlassButton(label: 'Board', height: 36, onTap: open),
          ]),
        ],
        if (st == 'ready' || st == 'approved') ...[
          const SizedBox(height: 8),
          AppScreenGrid(app: app, v: v, compact: true),
          const SizedBox(height: 6),
          Wrap(alignment: WrapAlignment.end, spacing: 6, runSpacing: 6, children: [
            TextButton.icon(onPressed: () => _openPreview(context, app, v), icon: const Icon(Icons.touch_app_rounded, size: 18),
                label: const Text('Tap to try')),
            TextButton(onPressed: open, child: const Text('Change')),
            if (st == 'ready')
              GlassButton(label: 'Confirm design', height: 36, color: C.accent, onTap: () async {
                final full = await app.api!.appGet(id);
                if (context.mounted) await _approve(context, app, full);
              }),
          ]),
        ],
        if (st == 'failed' || st == 'stopped')
          Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => app.api!.appAct(id, 'resume'), child: const Text('Aage badhao'))),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Profile > App designer
class AppDesignScreen extends StatefulWidget {
  const AppDesignScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<AppDesignScreen> createState() => _AppDesignScreenState();
}

class _AppDesignScreenState extends State<AppDesignScreen> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  int _tick = -1;

  @override
  void initState() {
    super.initState();
    _tick = app.appTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.appTick != _tick) {
      _tick = app.appTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.appAll();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final apps = _list(_d?['apps']);
    final lib = _map(_d?['library']);
    return DeskTabsScaffold(
          title: 'App designer',
          tabs: ['My apps', '1 crore ideas', 'Briefs (1 lakh)'],
          fab: FloatingActionButton.extended(
          backgroundColor: C.accent,
          foregroundColor: C.onAccent,
          onPressed: () => _newApp(context),
          icon: const Icon(Icons.add_rounded),
          label: const Text('New app'),
        ),
          pages: () => [
            RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 100), children: [
              if (_d == null) const Center(child: Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator())),
              if (_d != null && apps.isEmpty)
                Glass(child: Text('Say two or three words, like "app for a kirana shop, home delivery". ${app.aName} will design every screen '
                    'will design first (both Android and iPhone), you try it by tapping, and if you like it, "Confirm design". '
                    'The real app will be built from this design.', style: const TextStyle(color: C.chip))),
              for (final a in apps)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Glass(
                    child: ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.phone_android_rounded, color: C.accent),
                      title: Text('${a['number']} · ${_s(a['name']).isEmpty ? a['field_label'] : a['name']}', style: display(14)),
                      subtitle: Text('${a['goal_label']} · ${a['style_label']} · v${a['version']} · ${_map(a['board'])['pct'] ?? 0}%',
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                      trailing: Pill(_statusUi[a['status']] ?? _s(a['status']), fg: _stCol(_s(a['status']))),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppDesignPage(app: app, id: _s(a['id'])))),
                    ),
                  ),
                ),
            ]),
          ),
          AppIdeaFinder(app: app, onStart: (id, words) => _startIdea(context, id, words)),
          _AppIdeas(app: app, counts: lib, onPick: (brief) => _newApp(context, brief: brief)),
          ],
        );
  }

  Future<void> _startIdea(BuildContext context, String id, String words) async {
    try {
      final v = await app.api!.appNew({'idea': id, 'brief': words});
      if (!context.mounted) return;
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppDesignPage(app: app, id: _s(v['id']))));
      _load();
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
  }

  Future<void> _newApp(BuildContext context, {String brief = ''}) async {
    final b = TextEditingController(text: brief);
    final name = TextEditingController();
    final phone = TextEditingController();
    final upi = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (c) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(c).viewInsets.bottom + 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('New app', style: display(18)),
          const SizedBox(height: 8),
          TextField(controller: b, minLines: 2, maxLines: 4,
              decoration: const InputDecoration(labelText: 'What kind of app? (in your own words)', hintText: 'kirana shop, home delivery')),
          TextField(controller: name, decoration: const InputDecoration(labelText: 'App / business name')),
          TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone / WhatsApp')),
          TextField(controller: upi, decoration: const InputDecoration(labelText: 'UPI ID for payments (only the ID, never the PIN)')),
          const SizedBox(height: 12),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Make plan')),
        ]),
      ),
    );
    if (ok != true || b.text.trim().isEmpty) return;
    try {
      final v = await app.api!.appNew({'brief': b.text.trim(), 'name': name.text.trim(), 'answers': {
        if (phone.text.trim().isNotEmpty) 'phone': phone.text.trim(),
        if (upi.text.trim().isNotEmpty) 'upi_id': upi.text.trim(),
      }});
      if (!context.mounted) return;
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppDesignPage(app: app, id: _s(v['id']))));
      _load();
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
  }
}

/// v0.136 her few words -> the best precise app idea + near ones, and the whole 1 crore list page by page.
class AppIdeaFinder extends StatefulWidget {
  const AppIdeaFinder({super.key, required this.app, required this.onStart});
  final Santosh app;
  final void Function(String id, String words) onStart;
  @override
  State<AppIdeaFinder> createState() => _AppIdeaFinderState();
}

class _AppIdeaFinderState extends State<AppIdeaFinder> {
  final _q = TextEditingController();
  Map<String, dynamic>? _d;
  final List<Map<String, dynamic>> _more = [];
  bool _busy = false;
  String _asked = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool more = false}) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final q = more ? _asked : _q.text.trim();
      final d = await widget.app.api!.appIdeas(q: q, offset: more ? _more.length : 0);
      if (!mounted) return;
      setState(() {
        if (!more) {
          _d = d;
          _asked = q;
          _more.clear();
        }
        _more.addAll(_list(d['items']));
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _num(dynamic n) {
    final v = (n is num) ? n.toInt() : int.tryParse('$n') ?? 0;
    if (v >= 10000000) return '${(v / 10000000).toStringAsFixed(2)} crore';
    if (v >= 100000) return '${(v / 100000).toStringAsFixed(1)} lakh';
    return '$v';
  }

  Widget _card(Map<String, dynamic> it, {bool best = false}) {
    final chips = [it['aud_label'], it['scale_label'], it['market_label'], it['tier_label'], it['earn_label']]
        .where((x) => _s(x).isNotEmpty).map((x) => _s(x)).toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (best) const Text('SABSE SAHI IDEA', style: TextStyle(color: C.accent, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1)),
          Text(_s(it['name']), style: display(15)),
          const SizedBox(height: 4),
          Text(_s(it['special']).isEmpty ? _s(it['pitch']) : _s(it['special']), style: const TextStyle(color: C.chip, fontSize: 13)),
          if (chips.isNotEmpty) ...[
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 4, children: [for (final c in chips) Pill(c, fg: C.muted)]),
          ],
          if (best && _s(it['pitch']).isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(_s(it['pitch']), style: const TextStyle(color: C.muted, fontSize: 12)),
          ],
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.tonal(onPressed: () => widget.onStart(_s(it['id']), _asked), child: const Text('Make this')),
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final best = _map(_d?['best']);
    final near = _list(_d?['near']);
    return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 100), children: [
      Text('${_num(_d?['all_ideas'] ?? 0)} app ideas: 1,000 jobs × app goal × for whom × one special feature × '
          'one shop / branches / a whole city × village to overseas. Write two or three words and the best-fitting idea will come first.',
          style: const TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 8),
      TextField(controller: _q, onSubmitted: (_) => _load(),
          decoration: InputDecoration(hintText: 'e.g. kirana, daily milk, orders by WhatsApp',
              prefixIcon: const Icon(Icons.lightbulb_outline_rounded),
              suffixIcon: IconButton(icon: const Icon(Icons.arrow_forward_rounded), onPressed: _load))),
      const SizedBox(height: 10),
      if (_busy && _d == null) const Center(child: Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator())),
      if (_s(_d?['ask']).isNotEmpty) Glass(child: Text(_s(_d?['ask']), style: const TextStyle(color: C.chip))),
      if (best.isNotEmpty) _card(best, best: true),
      for (final n in near) _card(_map(n)),
      if (_more.isNotEmpty) ...[
        const SizedBox(height: 6),
        Text(_asked.isEmpty ? 'All ideas' : 'More ideas for this job · ${_num(_d?['total'] ?? 0)}', style: display(13)),
        const SizedBox(height: 6),
        for (final it in _more)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_s(it['name']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
            subtitle: Text(_s(it['special']), style: const TextStyle(color: C.muted, fontSize: 12)),
            trailing: TextButton(onPressed: () => widget.onStart(_s(it['id']), _asked), child: const Text('Make')),
          ),
        Center(child: TextButton(onPressed: _busy ? null : () => _load(more: true), child: Text(_busy ? '…' : 'Show more'))),
      ],
    ]);
  }
}

class _AppIdeas extends StatefulWidget {
  const _AppIdeas({required this.app, required this.counts, required this.onPick});
  final Santosh app;
  final Map<String, dynamic> counts;
  final void Function(String brief) onPick;
  @override
  State<_AppIdeas> createState() => _AppIdeasState();
}

class _AppIdeasState extends State<_AppIdeas> {
  Map<String, dynamic>? _d;
  String _industry = '';
  final _q = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.appLibrary(industry: _industry, q: _q.text.trim());
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final inds = _list(_d?['industries']);
    final fields = _list(_d?['fields']);
    final c = _map(_d?['counts']);
    return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 100), children: [
      Text('${c['fields'] ?? 1000} jobs × ${c['goals'] ?? 10} app goals × ${c['styles'] ?? 10} premium styles = '
          '${c['briefs'] ?? 100000} ready app briefs · ${c['screen_designs'] ?? 306} screen designs',
          style: const TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 8),
      TextField(controller: _q, onSubmitted: (_) => _load(),
          decoration: InputDecoration(hintText: 'Search: kirana, clinic, gym, coaching…', prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: IconButton(icon: const Icon(Icons.arrow_forward_rounded), onPressed: _load))),
      const SizedBox(height: 8),
      Wrap(spacing: 6, runSpacing: 6, children: [
        ChoiceChip(label: const Text('Sab'), selected: _industry.isEmpty, onSelected: (_) { _industry = ''; _load(); }),
        for (final i in inds)
          ChoiceChip(label: Text('${i['label']}'), selected: _industry == i['id'], onSelected: (_) { _industry = _s(i['id']); _q.clear(); _load(); }),
      ]),
      const SizedBox(height: 10),
      for (final f in fields)
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(_s(f['en']), style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${f['hi']} · ${f['goal_label']}', style: const TextStyle(color: C.muted)),
          trailing: TextButton(onPressed: () => widget.onPick('${f['en']} ki app'), child: const Text('Start')),
        ),
    ]);
  }
}

// ---------------------------------------------------------------- one app design
class AppDesignPage extends StatefulWidget {
  const AppDesignPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppDesignPage> createState() => _AppDesignPageState();
}

class _AppDesignPageState extends State<AppDesignPage> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _v;
  int _tick = -1;
  final _change = TextEditingController();
  final Map<int, TextEditingController> _answers = {};
  final Set<String> _drop = {};
  String _plat = 'android';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _tick = app.appTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.appTick != _tick) {
      _tick = app.appTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final v = await app.api!.appGet(widget.id);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _act(String action, [Map<String, dynamic> body = const {}, String ok = '']) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.appAct(widget.id, action, body);
      if (mounted && (ok.isNotEmpty || _s(r['say']).isNotEmpty)) _snack(context, ok.isNotEmpty ? ok : _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    if (v == null) return Scaffold(appBar: AppBar(), body: const Center(child: CircularProgressIndicator()));
    final st = _s(v['status']);
    final plan = _map(v['plan']);
    final checks = _map(v['checks']);
    final overview = _map(_map(v['board'])['overview']);
    final qs = (v['questions'] as List? ?? const []).map((e) => '$e').toList();
    return Scaffold(
      appBar: AppBar(
        title: Text('${v['number']} · ${_s(v['name']).isEmpty ? v['field_label'] : v['name']}'),
        actions: [
          if (_s(v['preview']).isNotEmpty)
            IconButton(tooltip: 'Prototype', icon: const Icon(Icons.touch_app_rounded), onPressed: () => _openPreview(context, app, v)),
          PopupMenuButton<String>(onSelected: (a) async {
            if (a == 'delete') {
              final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
                    title: const Text('Remove this app design?'),
                    actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
                      TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, remove'))]));
              if (yes == true) {
                await app.api!.appDelete(widget.id);
                if (context.mounted) Navigator.pop(context);
              }
            } else if (a == 'link') {
              final u = Uri.parse(app.api!.absolute(_s(v['preview'])));
              await launchUrl(u, mode: LaunchMode.externalApplication);
            }
          }, itemBuilder: (_) => const [
            PopupMenuItem(value: 'link', child: Text('Open the prototype in the browser')),
            PopupMenuItem(value: 'delete', child: Text('Hatao')),
          ]),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(14, 12, 14, 40), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${v['field_label']} · ${v['goal_label']} · ${v['style_label']}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
              Pill(_statusUi[st] ?? st, fg: _stCol(st)),
            ]),
            // v0.138 what she asked for, and whose app it is (her own business's details only when it is for her business)
            if (_s(_map(plan['scope'])['request']).isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('You said: "${_s(_map(plan['scope'])['request'])}"', style: const TextStyle(fontSize: 12.5, fontStyle: FontStyle.italic)),
            ],
            if (_s(_map(plan['scope'])['product_label']).isNotEmpty)
              Text('Will be made: ${_s(_map(plan['scope'])['product_label'])}'
                  '${_s(_map(plan['scope'])['like']).isNotEmpty ? ' (works like ${_s(_map(plan['scope'])['like'])}, with its own name and design)' : ''}',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (_s(_map(plan['scope'])['not_for']).isNotEmpty)
              Text('${_s(_map(plan['scope'])['not_for'])} details are not included in this app (it is a separate app).',
                  style: const TextStyle(color: C.muted, fontSize: 12)),
            const SizedBox(height: 8),
            SiteStages(v: v),
            if (st != 'planned' && st != 'looks') ...[const SizedBox(height: 10), AppScreenGrid(app: app, v: v)],
            if (st == 'designing' || st == 'checking')
              Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _act('stop'), child: const Text('Rokiye'))),
            if (st == 'failed' || st == 'stopped') ...[
              if (_s(v['error']).isNotEmpty) Text(_s(v['error']), style: const TextStyle(color: C.bad, fontSize: 12.5)),
              Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _act('resume'), child: const Text('Aage badhao'))),
            ],
          ])),
          const SizedBox(height: 10),
          if (_map(v['art']).isNotEmpty) ...[AppArtCard(v: v), const SizedBox(height: 10)],
          if (st == 'planned')
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Plan: ${_list(plan['screens']).length + _list(plan['code_screens']).length} screens', style: display(16)),
              const SizedBox(height: 4),
              Text('Neeche tabs: ${(plan['tabs'] as List? ?? const []).join(' · ')}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              Text('Route: ${(plan['flow'] as List? ?? const []).join(' → ')}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              const Text('Remove the tick from any screen you do not want:', style: TextStyle(color: C.faint, fontSize: 12)),
              Wrap(spacing: 6, runSpacing: 4, children: [
                for (final s in _list(plan['screens']))
                  FilterChip(
                    label: Text(_s(s['label'])),
                    selected: !_drop.contains(s['id']),
                    onSelected: s['tab'] == true || s['id'] == 'home' ? null : (on) => setState(() => on ? _drop.remove(s['id']) : _drop.add(_s(s['id']))),
                  ),
              ]),
              const SizedBox(height: 6),
              for (final s in _list(plan['code_screens']))
                Text('⚖ ${s['label']}: ${s['why']}', style: const TextStyle(color: C.faint, fontSize: 11.5)),
              if (qs.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text('A few questions (answer what you know)', style: display(14)),
                for (var i = 0; i < qs.length; i++)
                  TextField(controller: _answers.putIfAbsent(i, () => TextEditingController()), decoration: InputDecoration(labelText: qs[i])),
                Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _act('answers', {
                      'answers': {for (final e in _answers.entries) if (e.value.text.trim().isNotEmpty) '${e.key}': e.value.text.trim()}
                    }, 'Answers saved'), child: const Text('Send answers'))),
              ],
              const SizedBox(height: 8),
              Align(alignment: Alignment.centerRight,
                  child: GlassButton(label: 'Yes, make 3 looks', color: C.accent,
                      onTap: _busy ? null : () => _act('plan', {'drop': _drop.toList()}, 'Making the looks…'))),
            ])),
          if (st == 'looks') Glass(child: AppLooks(app: app, v: v)),
          if (overview.isNotEmpty) ...[
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text('Sab screens', style: display(15)),
                const Spacer(),
                SegmentedButton<String>(
                  segments: [
                    const ButtonSegment(value: 'android', label: Text('Android')),
                    const ButtonSegment(value: 'ios', label: Text('iPhone')),
                    if (overview['android-alt'] != null)
                      ButtonSegment(value: 'android-alt', label: Text(_map(v['design'])['dark'] == true ? 'Light' : 'Dark')),
                  ],
                  selected: {overview[_plat] == null ? 'android' : _plat},
                  onSelectionChanged: (s) => setState(() => _plat = s.first),
                ),
              ]),
              const SizedBox(height: 8),
              GestureDetector(
                onTap: () => _openShot(context, app, widget.id, _s(overview[_plat] ?? overview['android']), 'Sab screens'),
                child: ClipRRect(borderRadius: BorderRadius.circular(12),
                    child: Image.network(app.api!.absolute('/api/apps/${widget.id}/shots/${overview[_plat] ?? overview['android']}'),
                        headers: app.api!.authHeaders,
                        height: 320, fit: BoxFit.cover, alignment: Alignment.topCenter, width: double.infinity,
                        errorBuilder: (_, __, ___) => const SizedBox(height: 60, child: Icon(Icons.broken_image_outlined)))),
              ),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: GlassButton(label: 'Try it by tapping', onTap: () => _openPreview(context, app, v))),
                if (st == 'ready') ...[
                  const SizedBox(width: 8),
                  Expanded(child: GlassButton(label: 'Confirm design', color: C.accent, onTap: _busy ? null : () async {
                    await _approve(context, app, v);
                    await _load();
                  })),
                ],
              ]),
              if (st == 'approved') const Padding(padding: EdgeInsets.only(top: 8),
                  child: Text('✓ Design confirmed. The real Android app will be built from this blueprint (below).', style: TextStyle(color: C.ok, fontSize: 12.5))),
            ])),
            const SizedBox(height: 10),
          ],
          if (st == 'approved' || st == 'ready') ...[
            Glass(child: AndroidBuildPanel(app: app, id: widget.id, approved: st == 'approved')),
            const SizedBox(height: 10),
            Glass(child: AppDataPanel(app: app, id: widget.id)),
            const SizedBox(height: 10),
            Glass(child: AppMoneyPanel(app: app, id: widget.id)),          // v0.376 MAALKIN PHONE
            const SizedBox(height: 10),
            Glass(child: AppLogicPanel(app: app, id: widget.id)),          // v0.382 DIMAAG: the app's brain
            const SizedBox(height: 10),
            Glass(child: AppSafetyPanel(app: app, id: widget.id)),         // v0.390 PAKKI NEEV: backups + limits
            const SizedBox(height: 10),
            Glass(child: AppOwnDbPanel(app: app, id: widget.id)),          // v0.396 APNA DATABASE: her own database
            const SizedBox(height: 10),
            Glass(child: AppTrackPanel(app: app, id: widget.id)),          // v0.412 NAKSHA LIVE: tracking switch + riders
            const SizedBox(height: 10),
            Glass(child: AppPayPanel(app: app, id: widget.id)),            // v0.419 PAISA: her gateway, payments, refunds
            const SizedBox(height: 10),
            Glass(child: AppConnectPanel(app: app, id: widget.id)),        // v0.424 JODO: connectors - approve + runs
            const SizedBox(height: 10),
            Glass(child: AppComponentsPanel(app: app, id: widget.id)),     // v0.425 RANG: custom native components
            const SizedBox(height: 10),
            Glass(child: AppFamilyPanel(app: app, id: widget.id)),         // v0.435 PARIVAAR: apps on this data + partners
            const SizedBox(height: 10),
            Glass(child: AppLoginPanel(app: app, id: widget.id)),          // v0.455 SURAKSHIT LOGIN + security gates
            const SizedBox(height: 10),
            Glass(child: AppJaanchPanel(app: app, id: widget.id)),         // v0.540 JAANCH: proof, crashes, rollout
            const SizedBox(height: 10),
            Glass(child: AppNakshaPanel(app: app, id: widget.id)),         // v0.542 NAKSHA: the plan, module by module
            const SizedBox(height: 10),
            Glass(child: AppOpsPanel(app: app, id: widget.id)),            // v0.546 CHALTA KAAM: use, speed, cost
            const SizedBox(height: 10),
            Glass(child: StorePanel(app: app, id: widget.id)),
            const SizedBox(height: 10),
            Glass(child: IosBuildPanel(app: app, id: widget.id, approved: st == 'approved')),
            const SizedBox(height: 10),
            Glass(child: AppStorePanel(app: app, id: widget.id)),
            const SizedBox(height: 10),
            Glass(child: BhashaPanel(app: app, id: widget.id)),
            const SizedBox(height: 10),
            Glass(child: MatchPanel(app: app, id: widget.id)),
            const SizedBox(height: 10),
            Glass(child: AppCodePanel(app: app, id: widget.id)),
            const SizedBox(height: 10),
          ],
          if (_map(plan['blueprint']).isNotEmpty) ...[
            Glass(child: AppBlueprintCard(app: app, v: v, busy: _busy, onAsk: st == 'planned' || st == 'looks'
                ? null
                : (t) => _act('change', {'instruction': t}))),
            const SizedBox(height: 10),
          ],
          if (_map(v['design']).isNotEmpty) ...[
            Glass(child: AppDesignSystemCard(app: app, v: v, busy: _busy,
                onAsk: (t) => _act('change', {'instruction': t}))),
            const SizedBox(height: 10),
          ],
          if (_list(checks['blocking']).isNotEmpty || _list(checks['warnings']).isNotEmpty || checks['passed'] == true)
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Check (Android + iPhone, small phone)', style: display(15)),
              const SizedBox(height: 6),
              for (final c in _list(checks['blocking']).take(6))
                Text('⛔ ${c['screen']}: ${c['text']}', style: const TextStyle(color: C.bad, fontSize: 12)),
              for (final c in _list(checks['warnings']).take(6))
                Text('⚠ ${_s(c['screen']).isEmpty ? '' : '${c['screen']}: '}${c['text']}', style: const TextStyle(color: C.warn, fontSize: 12)),
              if (_list(checks['blocking']).isEmpty && checks['passed'] == true)
                const Text('✓ All important checks passed', style: TextStyle(color: C.ok, fontSize: 12.5)),
            ])),
          const SizedBox(height: 10),
          if (st == 'ready' || st == 'approved' || st == 'stopped' || st == 'failed' || st == 'designing' || st == 'checking')
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Say a change', style: display(15)),
              const SizedBox(height: 6),
              TextField(controller: _change, minLines: 1, maxLines: 4,
                  decoration: const InputDecoration(hintText: 'remove the coupon from the cart, lighter colour, an offers tab, add a booking screen…')),
              const SizedBox(height: 8),
              Align(alignment: Alignment.centerRight, child: GlassButton(label: 'Badlo', color: C.accent, onTap: _busy ? null : () async {
                final t = _change.text.trim();
                if (t.isEmpty) return;
                await _act('change', {'instruction': t});
                _change.clear();
              })),
              if (_i(v['queued']) > 0) Text('${v['queued']} changes are in the queue', style: const TextStyle(color: C.faint, fontSize: 12)),
            ])),
          const SizedBox(height: 10),
          for (final ver in _list(v['versions']))
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Text('v${ver['version']}', style: display(14)),
              title: Text(_s(ver['note']), maxLines: 2, overflow: TextOverflow.ellipsis),
              subtitle: Text('${ver['screens']} screens', style: const TextStyle(color: C.faint, fontSize: 11.5)),
              trailing: Icon(ver['passed'] == true ? Icons.verified_rounded : Icons.error_outline_rounded,
                  color: ver['passed'] == true ? C.ok : C.warn),
            ),
        ]),
      ),
    );
  }
}

/// The design system of the chosen look in plain words: navigation, FAB, cards, header, motion, fonts, light / dark
/// colours, the open side bar / FAB menu pictures, and one-tap structure changes (sent as her words, like 'Say a change').
class AppDesignSystemCard extends StatelessWidget {
  const AppDesignSystemCard({super.key, required this.app, required this.v, required this.onAsk, this.busy = false});
  final Santosh app;
  final Map<String, dynamic> v;
  final void Function(String) onAsk;
  final bool busy;

  static const _quick = [
    ('Side bar', 'use side bar (drawer) navigation, and keep the bottom tabs too'),
    ('Floating bar', 'neeche floating pill navigation bar do'),
    ('Bottom bar', 'normal bottom navigation bar do'),
    ('Speed-dial FAB', 'tapping the plus button opens 3 actions (speed dial FAB)'),
    ('Glass cards', 'make the cards glass-like (frosted)'),
    ('Dark mode', 'make the app dark mode'),
    ('Light + dark', 'make the app work in both light and dark mode'),
  ];

  Widget _swatches(List cols) => Row(children: [
        for (final c in cols)
          Container(width: 22, height: 22, margin: const EdgeInsets.only(right: 4),
              decoration: BoxDecoration(color: _hex(_s(c)), borderRadius: BorderRadius.circular(6), border: Border.all(color: C.line))),
      ]);

  @override
  Widget build(BuildContext context) {
    final d = _map(v['design']);
    final ex = _map(_map(v['board'])['extras']);
    final id = _s(v['id']);
    final mode = switch (_s(d['mode'])) { 'dark' => 'Dark only', 'light' => 'Light only', _ => 'Light + dark' };
    Widget row(String k, String val) => val.isEmpty
        ? const SizedBox.shrink()
        : Padding(padding: const EdgeInsets.only(bottom: 3), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 92, child: Text(k, style: const TextStyle(color: C.faint, fontSize: 12))),
            Expanded(child: Text(val, style: const TextStyle(fontSize: 12.5))),
          ]));
    final fonts = (d['fonts'] as List? ?? const []).map((e) => '$e').where((e) => e.isNotEmpty).toSet().join(' + ');
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Design structure', style: display(15)),
      const SizedBox(height: 8),
      row('Navigation', _s(d['nav'])),
      row('Button (FAB)', _s(d['fab'])),
      row('Cards', _s(d['card'])),
      row('Top part', _s(d['header'])),
      row('Button', _s(d['button'])),
      row('Change screens', _s(d['transition'])),
      row('Texture', _s(d['texture'])),
      row('Font', fonts),
      row('Mode', mode),
      const SizedBox(height: 4),
      Row(children: [
        _swatches(d['colors'] as List? ?? const []),
        if ((d['alt_colors'] as List? ?? const []).isNotEmpty && _s(d['mode']) == 'both') ...[
          const SizedBox(width: 8),
          Text(d['dark'] == true ? 'Light:' : 'Dark:', style: const TextStyle(color: C.faint, fontSize: 11.5)),
          const SizedBox(width: 4),
          _swatches(d['alt_colors'] as List),
        ],
      ]),
      if (ex.isNotEmpty) ...[
        const SizedBox(height: 10),
        SizedBox(height: 170, child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final e in ex.entries)
            Padding(padding: const EdgeInsets.only(right: 8), child: Column(children: [
              GestureDetector(
                onTap: () => _openShot(context, app, id, _s(e.value), e.key.startsWith('drawer') ? 'Side bar' : 'FAB menu'),
                child: AppShot(app: app, appId: id, name: _s(e.value), width: 70)),
              const SizedBox(height: 2),
              Text(e.key.startsWith('drawer') ? 'Side bar' : 'FAB menu', style: const TextStyle(color: C.faint, fontSize: 11)),
            ])),
        ])),
      ],
      const SizedBox(height: 8),
      const Text('Change in one tap (the screens stay the same):', style: TextStyle(color: C.faint, fontSize: 12)),
      const SizedBox(height: 4),
      Wrap(spacing: 6, runSpacing: 4, children: [
        for (final q in _quick) ActionChip(label: Text(q.$1), onPressed: busy ? null : () => onAsk(q.$2)),
      ]),
    ]);
  }
}

/// v0.131 What is under the screens of a complex app: modules + data tables, org levels, roles and what each may do,
/// approval chain, login plan, phone features with their Google Play / App Store status (the ones the stores don't allow are
/// shown with what is used instead), the ER picture / page and the database schema to copy.
class AppBlueprintCard extends StatelessWidget {
  const AppBlueprintCard({super.key, required this.app, required this.v, this.onAsk, this.busy = false});
  final Santosh app;
  final Map<String, dynamic> v;
  final void Function(String)? onAsk;
  final bool busy;

  static const _quick = [
    ('New role', 'add a new role called store keeper, like staff'),
    ('Zone level', 'also add a zone level under region'),
    ('Passkey login', 'also allow login with a passkey'),
    ('Company SSO', 'also allow login through the company Microsoft / Google login (SSO)'),
    ('Offline', 'work without internet too, and sync later'),
  ];
  static const _actLabel = {'read': 'Viewed', 'create': 'Made', 'update': 'Changed', 'delete': 'Hataye', 'approve': 'Approved', 'export': 'Export'};
  static const _scopeLabel = {'none': '-', 'own': 'own', 'unit': 'unit', 'parent': 'parent', 'all': 'all'};

  Color _playCol(String p) => switch (p) { 'ok' => C.ok, 'disclosure' => C.teal, 'declaration' => C.warn, _ => C.bad };

  Future<void> _copySchema(BuildContext context) async {
    try {
      final t = await app.api!.appBlueprintText(_s(v['id']), 'schema.sql');
      await Clipboard.setData(ClipboardData(text: t));
      if (context.mounted) _snack(context, 'Database schema copied (${(t.length / 1024).toStringAsFixed(0)} KB)');
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
  }

  void _openEr(BuildContext context) {
    final u = _s(v['preview']);
    if (u.isEmpty) return;
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => _ErView(url: app.api!.absolute('${u}blueprint/er.html'))));
  }

  @override
  Widget build(BuildContext context) {
    final b = _map(_map(v['plan'])['blueprint']);
    final data = _map(b['data']);
    final roles = _list(b['roles']);
    final matrix = _map(b['matrix']);
    final er = _s(_map(v['board'])['er']);
    Widget head(String t) => Padding(padding: const EdgeInsets.only(top: 10, bottom: 4),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)));
    Widget chips(Iterable<Widget> w) => Wrap(spacing: 6, runSpacing: 4, children: w.toList());
    Widget chip(String t, [Color? c]) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: (c ?? C.chip).withOpacity(.14), borderRadius: BorderRadius.circular(8)),
        child: Text(t, style: TextStyle(fontSize: 11.5, color: c ?? C.ink)));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Inner structure${_s(b['archetype']).isEmpty ? '' : ' · ${b['archetype']}'}', style: display(15)),
      const SizedBox(height: 4),
      Text('${data['tables'] ?? 0} tables · ${data['relations'] ?? 0} rishte · ${roles.length} roles · '
          '${(b['levels'] as List? ?? const []).length} levels${b['offline'] == true ? ' · offline too' : ''}',
          style: const TextStyle(color: C.muted, fontSize: 12.5)),
      head('Organisation levels'),
      Text((b['levels'] as List? ?? const []).join('  ›  '), style: const TextStyle(fontSize: 12.5)),
      head('Who can do what'),
      for (final r in roles)
        Theme(data: Theme.of(context).copyWith(dividerColor: Colors.transparent), child: ExpansionTile(
          tilePadding: EdgeInsets.zero, childrenPadding: const EdgeInsets.only(bottom: 6),
          title: Text(_s(r['label']), style: const TextStyle(fontSize: 13)),
          children: [
            for (final m in _map(matrix[r['id']]).entries)
              Padding(padding: const EdgeInsets.only(bottom: 3), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 92, child: Text(m.key, style: const TextStyle(color: C.faint, fontSize: 11.5))),
                Expanded(child: Text(_map(m.value).entries.where((e) => e.value != 'none')
                    .map((e) => '${_actLabel[e.key] ?? e.key}: ${_scopeLabel[e.value] ?? e.value}').join(' · ').replaceAll(RegExp(r'^$'), '—'),
                    style: const TextStyle(fontSize: 11.5))),
              ])),
          ])),
      if (_list(b['approvals']).isNotEmpty) ...[
        head('Approval (by amount)'),
        for (final a in _list(b['approvals']))
          Text(a['upto'] == null ? '• above that: ${a['role']}' : '• up to ₹${a['upto']}: ${a['role']}', style: const TextStyle(fontSize: 12)),
      ],
      head('Login'),
      chips(_list(b['login']).map((m) => chip(_s(m['label']), C.accent))),
      for (final w in (b['login_warnings'] as List? ?? const []))
        Padding(padding: const EdgeInsets.only(top: 3), child: Text('ℹ $w', style: const TextStyle(color: C.faint, fontSize: 11.5))),
      head('Phone ki suvidhayein (Play / App Store)'),
      chips(_list(b['caps']).map((c) => chip('${c['label']} · ${c['play_label']}', _playCol(_s(c['play']))))),
      for (final p in _list(b['cap_problems']))
        Padding(padding: const EdgeInsets.only(top: 4), child: Text('⛔ ${p['text']}', style: const TextStyle(color: C.bad, fontSize: 12))),
      for (final n in _list(b['cap_notes']))
        Padding(padding: const EdgeInsets.only(top: 3), child: Text('⚠ ${n['text']}', style: const TextStyle(color: C.warn, fontSize: 11.5))),
      head('Data (tables)'),
      for (final m in _map(b['tables']).entries)
        Padding(padding: const EdgeInsets.only(bottom: 4), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 92, child: Text(m.key,
              style: const TextStyle(color: C.faint, fontSize: 11.5))),
          Expanded(child: Text((m.value as List).join(', '), style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace'))),
        ])),
      if ((data['sensitive'] as List? ?? const []).isNotEmpty)
        Text('🔒 Sensitive: ${(data['sensitive'] as List).join(', ')} (screenshots off, every view logged)',
            style: const TextStyle(color: C.faint, fontSize: 11.5)),
      if (er.isNotEmpty) ...[
        const SizedBox(height: 8),
        GestureDetector(onTap: () => _openEr(context),
            child: ClipRRect(borderRadius: BorderRadius.circular(10), child: AppShot(app: app, appId: _s(v['id']), name: er, width: 320))),
      ],
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 6, children: [
        if (_s(v['preview']).isNotEmpty) OutlinedButton.icon(onPressed: () => _openEr(context),
            icon: const Icon(Icons.account_tree_rounded, size: 18), label: const Text('ER diagram')),
        OutlinedButton.icon(onPressed: () => _copySchema(context), icon: const Icon(Icons.copy_rounded, size: 18),
            label: const Text('Database schema copy')),
      ]),
      if (onAsk != null) ...[
        const SizedBox(height: 8),
        const Text('Add in one tap (the screens stay the same):', style: TextStyle(color: C.faint, fontSize: 12)),
        const SizedBox(height: 4),
        Wrap(spacing: 6, runSpacing: 4, children: [
          for (final q in _quick) ActionChip(label: Text(q.$1), onPressed: busy ? null : () => onAsk!(q.$2)),
        ]),
      ],
    ]);
  }
}

class _ErView extends StatefulWidget {
  const _ErView({required this.url});
  final String url;
  @override
  State<_ErView> createState() => _ErViewState();
}

class _ErViewState extends State<_ErView> {
  late final WebViewController _c = WebViewController()
    ..setJavaScriptMode(JavaScriptMode.disabled)
    ..loadRequest(Uri.parse(widget.url));
  @override
  Widget build(BuildContext context) =>
      Scaffold(appBar: AppBar(title: const Text('Data model (ER)')), body: WebViewWidget(controller: _c));
}

/// The tap-through prototype inside the app (Android / iPhone look switch).
class AppPreview extends StatefulWidget {
  const AppPreview({super.key, required this.app, required this.url, required this.title});
  final Santosh app;
  final String url;
  final String title;
  @override
  State<AppPreview> createState() => _AppPreviewState();
}

class _AppPreviewState extends State<AppPreview> {
  late final WebViewController _web;
  String _plat = 'android';
  int _progress = 0;

  String get _base => widget.app.api!.absolute(widget.url);

  @override
  void initState() {
    super.initState();
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(onProgress: (p) {
        if (mounted) setState(() => _progress = p);
      }, onNavigationRequest: (r) {
        if (!r.url.contains('/api/app-preview/')) {
          launchUrl(Uri.parse(r.url), mode: LaunchMode.externalApplication);
          return NavigationDecision.prevent;
        }
        return NavigationDecision.navigate;
      }))
      ..loadRequest(Uri.parse('$_base?p=$_plat'));
  }

  void _switch(String p) {
    setState(() => _plat = p);
    _web.runJavaScript("window.HoolaProto && window.HoolaProto.platform('$p')");
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title.isEmpty ? 'Prototype' : widget.title), actions: [
          TextButton(onPressed: () => _switch(_plat == 'android' ? 'ios' : 'android'),
              child: Text(_plat == 'android' ? 'iPhone look' : 'Android look')),
          IconButton(tooltip: 'Light / dark', icon: const Icon(Icons.dark_mode_outlined),
              onPressed: () => _web.runJavaScript("window.HoolaProto && window.HoolaProto.mode('toggle')")),
          IconButton(tooltip: 'Sab screens', icon: const Icon(Icons.grid_view_rounded),
              onPressed: () => _web.loadRequest(Uri.parse('${_base}all.html'))),
          IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: () => _web.loadRequest(Uri.parse('$_base?p=$_plat'))),
        ]),
        body: Stack(children: [
          WebViewWidget(controller: _web),
          if (_progress < 100) LinearProgressIndicator(value: _progress / 100, minHeight: 2, color: C.teal),
        ]),
      );
}

/// v0.140 the app's own art direction (design DNA by Claude Opus 5.5) and what Opus said after looking at its screenshots.
class AppArtCard extends StatelessWidget {
  const AppArtCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final art = _map(v['art']);
    final scores = _map(_map(v['board'])['scores']);
    final labels = _map(_map(_map(v['plan']))['labels']);
    Widget line(String k, String text) => text.isEmpty
        ? const SizedBox.shrink()
        : Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text.rich(TextSpan(children: [
              TextSpan(text: '$k: ', style: const TextStyle(color: C.faint, fontSize: 12)),
              TextSpan(text: text, style: const TextStyle(fontSize: 12.5)),
            ])),
          );
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.auto_awesome_rounded, color: C.accent, size: 18),
          const SizedBox(width: 6),
          Expanded(child: Text(_s(art['concept']).isEmpty ? 'Design thinking' : _s(art['concept']), style: display(15))),
          if (_s(v['model']).isNotEmpty) Pill(_s(v['model']), fg: C.accent),
        ]),
        if (_s(art['idea']).isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(art['idea']), style: const TextStyle(fontStyle: FontStyle.italic, fontSize: 12.5))),
        line('Identity', _s(art['signature'])),
        line('Layout', _s(art['layout'])),
        line('Shuruaat', _s(art['hero'])),
        line('Motion', _s(art['motion'])),
        if (art['three_d'] == true) line('3D', (art['scenes'] as List? ?? const []).join(', ').isEmpty ? 'yes' : (art['scenes'] as List).join(', ')),
        if (scores.isNotEmpty) ...[
          const SizedBox(height: 8),
          const Text('Opus scored its own screens after looking at them', style: TextStyle(color: C.muted, fontSize: 12)),
          const SizedBox(height: 4),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final e in scores.entries)
              Builder(builder: (_) {
                final s = _map(e.value);
                final sc = double.tryParse(_s(s['score'])) ?? 0;
                final before = _s(s['before']);
                return Pill('${_s(labels[e.key]).isEmpty ? e.key : _s(labels[e.key])}: '
                    '${before.isNotEmpty ? '$before → ' : ''}${sc.toStringAsFixed(1)}/10',
                    fg: sc >= 8 ? C.ok : (sc >= 6 ? C.accent : C.bad));
              }),
          ]),
        ],
      ]),
    );
  }
}
