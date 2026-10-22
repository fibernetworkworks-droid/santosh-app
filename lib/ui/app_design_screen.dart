/// Profile > "<name> · App designer" (v0.128 App Sahayak, part 1): a few words -> plan of every screen (her Haan) ->
/// 3 Home-screen looks (her choice) -> every screen designed while she watches (tiles with real screenshots) ->
/// checks on Android + iPhone -> tap-through prototype -> changes in her words -> "Design pakka" (her tap, exact hash).
/// One chat card per app design, updated in place (also inside calls).
library;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../state.dart';
import 'glass.dart';
import 'site_screen.dart' show SiteStages;

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _statusUi = {
  'draft': 'Shuru', 'planned': 'Plan: aapki haan', 'looks': 'Look chuniye', 'designing': 'Screens ban rahi', 'checking': 'Jaanch',
  'ready': 'Design taiyaar', 'approved': 'Design pakka', 'failed': 'Dikkat', 'stopped': 'Ruka hua',
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
        Text('Abhi: ${b['now']}', style: const TextStyle(color: C.ink, fontWeight: FontWeight.w700, fontSize: 13)),
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
    if (looks.isEmpty) return const Text('Looks ban rahe hain…', style: TextStyle(color: C.faint));
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
                const Spacer(),
                Row(children: [
                  Expanded(child: GlassButton(label: 'Yeh wala', height: 34, color: C.accent, onTap: _busy ? null : () => _choose(i))),
                  IconButton(
                    tooltip: 'Iske rang',
                    onPressed: () => setState(() => _colorsFrom = _colorsFrom == i ? null : i),
                    icon: Icon(Icons.palette_rounded, color: _colorsFrom == i ? C.accent : C.faint, size: 20),
                  ),
                ]),
              ]),
            );
          },
        ),
      ),
      if (_colorsFrom != null) Text('Rang look ${_colorsFrom! + 1} ke lagenge', style: const TextStyle(color: C.accent, fontSize: 12)),
    ]);
  }

  Future<void> _choose(int i) async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.appAct(_s(widget.v['id']), 'look', {'index': i, if (_colorsFrom != null) 'colors_from': _colorsFrom});
      if (mounted) _snack(context, 'Screens banana shuru! Har screen ban-te hi dikhegi.');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

Future<void> _approve(BuildContext context, Santosh app, Map<String, dynamic> v) async {
  final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        title: const Text('Design pakka karein?'),
        content: Text('${v['board']?['total'] ?? ''} screens ka yeh design (v${v['version']}) asli Android / iPhone app ka naksha ban jayega. '
            'Baad mein badlav ho sakte hain, phir dobara pakka karna hoga.'),
        actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Abhi nahi')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, pakka'))],
      ));
  if (yes != true) return;
  try {
    final r = await app.api!.appAct(_s(v['id']), 'approve', {'hash': _s(v['hash'])});
    if (context.mounted) _snack(context, _s(r['say']).isEmpty ? 'Design pakka!' : _s(r['say']));
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
            TextButton(onPressed: open, child: const Text('Dekho / jawab do')),
            const SizedBox(width: 6),
            GlassButton(label: 'Haan, 3 looks banao', height: 38, color: C.accent, onTap: () async {
              try {
                await app.api!.appAct(id, 'plan');
                if (context.mounted) _snack(context, 'Home screen ke 3 looks ban rahe hain.');
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
                label: const Text('Tap karke dekho')),
            TextButton(onPressed: open, child: const Text('Badlav')),
            if (st == 'ready')
              GlassButton(label: 'Design pakka', height: 36, color: C.accent, onTap: () async {
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
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text('${app.aName} · App designer'),
          bottom: const TabBar(tabs: [Tab(text: 'Meri apps'), Tab(text: 'Ideas (1 lakh)')]),
        ),
        floatingActionButton: FloatingActionButton.extended(
          backgroundColor: C.accent,
          foregroundColor: C.onAccent,
          onPressed: () => _newApp(context),
          icon: const Icon(Icons.add_rounded),
          label: const Text('Nayi app'),
        ),
        body: TabBarView(children: [
          RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 100), children: [
              if (_d == null) const Center(child: Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator())),
              if (_d != null && apps.isEmpty)
                Glass(child: Text('Do-teen shabd boliye, jaise "kirana dukaan ki app, ghar pe delivery". ${app.aName} har screen '
                    'pehle design karega (Android aur iPhone dono), aap tap karke chalaengi, pasand ho to "Design pakka". '
                    'Asli app usi design se banegi.', style: const TextStyle(color: C.chip))),
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
          _AppIdeas(app: app, counts: lib, onPick: (brief) => _newApp(context, brief: brief)),
        ]),
      ),
    );
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
          Text('Nayi app', style: display(18)),
          const SizedBox(height: 8),
          TextField(controller: b, minLines: 2, maxLines: 4,
              decoration: const InputDecoration(labelText: 'Kis kaam ki app? (apne shabdon mein)', hintText: 'kirana dukaan, ghar pe delivery')),
          TextField(controller: name, decoration: const InputDecoration(labelText: 'App / business ka naam')),
          TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone / WhatsApp')),
          TextField(controller: upi, decoration: const InputDecoration(labelText: 'Payment ka UPI ID (sirf ID, PIN kabhi nahi)')),
          const SizedBox(height: 12),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Plan banao')),
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
      Text('${c['fields'] ?? 1000} kaam × ${c['goals'] ?? 10} app maqsad × ${c['styles'] ?? 10} premium style = '
          '${c['briefs'] ?? 100000} taiyaar app briefs · ${c['screen_designs'] ?? 306} screen designs',
          style: const TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 8),
      TextField(controller: _q, onSubmitted: (_) => _load(),
          decoration: InputDecoration(hintText: 'Dhoondho: kirana, clinic, gym, coaching…', prefixIcon: const Icon(Icons.search_rounded),
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
          trailing: TextButton(onPressed: () => widget.onPick('${f['en']} ki app'), child: const Text('Shuru')),
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
                    title: const Text('App design hata dein?'),
                    actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
                      TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, hatao'))]));
              if (yes == true) {
                await app.api!.appDelete(widget.id);
                if (context.mounted) Navigator.pop(context);
              }
            } else if (a == 'link') {
              final u = Uri.parse(app.api!.absolute(_s(v['preview'])));
              await launchUrl(u, mode: LaunchMode.externalApplication);
            }
          }, itemBuilder: (_) => const [
            PopupMenuItem(value: 'link', child: Text('Prototype browser mein kholo')),
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
          if (st == 'planned')
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Plan: ${_list(plan['screens']).length + _list(plan['code_screens']).length} screens', style: display(16)),
              const SizedBox(height: 4),
              Text('Neeche tabs: ${(plan['tabs'] as List? ?? const []).join(' · ')}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              Text('Raasta: ${(plan['flow'] as List? ?? const []).join(' → ')}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              const Text('Jo screen nahi chahiye uska nishaan hatao:', style: TextStyle(color: C.faint, fontSize: 12)),
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
                Text('Thode sawaal (jitne pata hain utne)', style: display(14)),
                for (var i = 0; i < qs.length; i++)
                  TextField(controller: _answers.putIfAbsent(i, () => TextEditingController()), decoration: InputDecoration(labelText: qs[i])),
                Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _act('answers', {
                      'answers': {for (final e in _answers.entries) if (e.value.text.trim().isNotEmpty) '${e.key}': e.value.text.trim()}
                    }, 'Jawab rakh liye'), child: const Text('Jawab bhejo'))),
              ],
              const SizedBox(height: 8),
              Align(alignment: Alignment.centerRight,
                  child: GlassButton(label: 'Haan, 3 looks banao', color: C.accent,
                      onTap: _busy ? null : () => _act('plan', {'drop': _drop.toList()}, 'Looks ban rahe hain…'))),
            ])),
          if (st == 'looks') Glass(child: AppLooks(app: app, v: v)),
          if (overview.isNotEmpty) ...[
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text('Sab screens', style: display(15)),
                const Spacer(),
                SegmentedButton<String>(
                  segments: const [ButtonSegment(value: 'android', label: Text('Android')), ButtonSegment(value: 'ios', label: Text('iPhone'))],
                  selected: {_plat},
                  onSelectionChanged: (s) => setState(() => _plat = s.first),
                ),
              ]),
              const SizedBox(height: 8),
              GestureDetector(
                onTap: () => _openShot(context, app, widget.id, _s(overview[_plat]), 'Sab screens'),
                child: ClipRRect(borderRadius: BorderRadius.circular(12),
                    child: Image.network(app.api!.absolute('/api/apps/${widget.id}/shots/${overview[_plat]}'), headers: app.api!.authHeaders,
                        height: 320, fit: BoxFit.cover, alignment: Alignment.topCenter, width: double.infinity,
                        errorBuilder: (_, __, ___) => const SizedBox(height: 60, child: Icon(Icons.broken_image_outlined)))),
              ),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: GlassButton(label: 'Tap karke chalaiye', onTap: () => _openPreview(context, app, v))),
                if (st == 'ready') ...[
                  const SizedBox(width: 8),
                  Expanded(child: GlassButton(label: 'Design pakka', color: C.accent, onTap: _busy ? null : () async {
                    await _approve(context, app, v);
                    await _load();
                  })),
                ],
              ]),
              if (st == 'approved') const Padding(padding: EdgeInsets.only(top: 8),
                  child: Text('✓ Design pakka. Asli Android / iPhone app isi naksha se banegi (agla version).', style: TextStyle(color: C.ok, fontSize: 12.5))),
            ])),
            const SizedBox(height: 10),
          ],
          if (_list(checks['blocking']).isNotEmpty || _list(checks['warnings']).isNotEmpty || checks['passed'] == true)
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Jaanch (Android + iPhone, chhota phone)', style: display(15)),
              const SizedBox(height: 6),
              for (final c in _list(checks['blocking']).take(6))
                Text('⛔ ${c['screen']}: ${c['text']}', style: const TextStyle(color: C.bad, fontSize: 12)),
              for (final c in _list(checks['warnings']).take(6))
                Text('⚠ ${_s(c['screen']).isEmpty ? '' : '${c['screen']}: '}${c['text']}', style: const TextStyle(color: C.warn, fontSize: 12)),
              if (_list(checks['blocking']).isEmpty && checks['passed'] == true)
                const Text('✓ Sab zaroori jaanch paas', style: TextStyle(color: C.ok, fontSize: 12.5)),
            ])),
          const SizedBox(height: 10),
          if (st == 'ready' || st == 'approved' || st == 'stopped' || st == 'failed' || st == 'designing' || st == 'checking')
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Badlav bolo', style: display(15)),
              const SizedBox(height: 6),
              TextField(controller: _change, minLines: 1, maxLines: 4,
                  decoration: const InputDecoration(hintText: 'cart mein coupon hatao, rang halka, offers ka tab, booking screen add karo…')),
              const SizedBox(height: 8),
              Align(alignment: Alignment.centerRight, child: GlassButton(label: 'Badlo', color: C.accent, onTap: _busy ? null : () async {
                final t = _change.text.trim();
                if (t.isEmpty) return;
                await _act('change', {'instruction': t});
                _change.clear();
              })),
              if (_i(v['queued']) > 0) Text('${v['queued']} badlav line mein hain', style: const TextStyle(color: C.faint, fontSize: 12)),
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
