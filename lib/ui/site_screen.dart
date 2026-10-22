/// Profile > "<name> · Website" (v0.121 Website Sahayak): a few words -> plan (her Haan) -> 3 looks (her choice) ->
/// every section built while she watches (live board + preview) -> checks -> changes in her words. One chat card per
/// site, updated in place (also inside calls).
library;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../state.dart';
import 'glass.dart';
import 'site_hosting.dart';

String _s(dynamic v) => v == null ? '' : '$v';
int _i(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _statusUi = {
  'draft': 'Shuru', 'planned': 'Plan: aapki haan', 'looks': 'Look chuniye', 'building': 'Ban raha hai', 'checking': 'Jaanch',
  'ready': 'Taiyaar', 'failed': 'Dikkat', 'stopped': 'Ruka hua',
};
Color _stCol(String s) => switch (s) {
      'ready' => C.ok, 'planned' || 'looks' => C.accent, 'failed' => C.bad, 'building' || 'checking' => C.teal, _ => C.chip };
const _stateCol = {'done': C.ok, 'building': C.accent, 'fixing': C.warn, 'failed': C.bad};

Color _hex(String h, [Color or = C.chip]) {
  final v = h.replaceAll('#', '');
  if (v.length != 6) return or;
  return Color(int.parse('FF$v', radix: 16));
}

Future<void> _openUrl(BuildContext context, Santosh app, String url) async {
  if (url.isEmpty) return;
  final u = Uri.parse(app.api!.absolute(url));
  if (!await launchUrl(u, mode: LaunchMode.externalApplication) && context.mounted) _snack(context, 'Link nahi khula');
}

/// A screenshot from the server (needs the key).
class SiteShot extends StatelessWidget {
  const SiteShot({super.key, required this.app, required this.siteId, required this.name, this.height = 200, this.fit = BoxFit.cover});
  final Santosh app;
  final String siteId;
  final String name;
  final double height;
  final BoxFit fit;
  @override
  Widget build(BuildContext context) {
    if (name.isEmpty || app.api == null) {
      return SizedBox(height: height, child: const Center(child: Icon(Icons.web_rounded, color: C.faint)));
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Image.network(app.api!.absolute('/api/sites/$siteId/shots/$name'), headers: app.api!.authHeaders, height: height,
          fit: fit, alignment: Alignment.topCenter,
          errorBuilder: (_, __, ___) => SizedBox(height: height, child: const Center(child: Icon(Icons.broken_image_outlined))),
          loadingBuilder: (c, w, p) => p == null ? w : SizedBox(height: height, child: const Center(child: CircularProgressIndicator()))),
    );
  }
}

/// The 10 stages as a strip, current one highlighted.
class SiteStages extends StatelessWidget {
  const SiteStages({super.key, required this.v});
  final Map<String, dynamic> v;
  @override
  Widget build(BuildContext context) {
    final stages = _list(v['stages']);
    final cur = stages.indexWhere((e) => e['id'] == v['stage']);
    return SizedBox(
      height: 30,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: stages.length,
        separatorBuilder: (_, __) => const Icon(Icons.chevron_right_rounded, size: 16, color: C.faint),
        itemBuilder: (_, i) {
          final done = i < cur || (v['status'] == 'ready' && i <= cur);
          final now = i == cur && v['status'] != 'ready';
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: now ? C.accent.withOpacity(.25) : (done ? C.ok.withOpacity(.15) : const Color(0x12FFFFFF)),
              borderRadius: BorderRadius.circular(99),
              border: Border.all(color: now ? C.accent : Colors.transparent),
            ),
            child: Text('${done ? '✓ ' : ''}${stages[i]['label']}',
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: now ? C.accent : (done ? C.ok : C.faint))),
          );
        },
      ),
    );
  }
}

/// Pages and their sections as tiles that go grey -> building -> done.
class SiteBoard extends StatelessWidget {
  const SiteBoard({super.key, required this.v, this.compact = false});
  final Map<String, dynamic> v;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    final b = _map(v['board']);
    final pages = _list(b['pages']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (_s(b['now']).isNotEmpty)
        Text('Abhi: ${b['now']}', style: const TextStyle(color: C.ink, fontWeight: FontWeight.w700, fontSize: 13)),
      const SizedBox(height: 6),
      ClipRRect(
        borderRadius: BorderRadius.circular(99),
        child: LinearProgressIndicator(value: (_i(b['pct'])) / 100, minHeight: 6, color: C.teal, backgroundColor: const Color(0x22FFFFFF)),
      ),
      const SizedBox(height: 4),
      Text('${b['done'] ?? 0} / ${b['total'] ?? 0} section · ${b['pct'] ?? 0}%', style: const TextStyle(color: C.faint, fontSize: 11.5)),
      if (!compact)
        for (final p in pages)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(p['title']), style: const TextStyle(fontWeight: FontWeight.w800, color: C.chip, fontSize: 13)),
              const SizedBox(height: 4),
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final s in _list(p['sections']))
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                    decoration: BoxDecoration(
                      color: (_stateCol[s['state']] ?? const Color(0x33FFFFFF)).withOpacity(.18),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: (_stateCol[s['state']] ?? const Color(0x22FFFFFF)).withOpacity(.6)),
                    ),
                    child: Text('${s['state'] == 'done' ? '✓ ' : s['state'] == 'building' ? '⋯ ' : s['state'] == 'fixing' ? '🔧 ' : ''}${s['label']}',
                        style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: _stateCol[s['state']] ?? C.faint)),
                  ),
              ]),
            ]),
          ),
    ]);
  }
}

class SiteScores extends StatelessWidget {
  const SiteScores({super.key, required this.scores});
  final Map<String, dynamic> scores;
  @override
  Widget build(BuildContext context) {
    Widget one(String label, String key) {
      final n = _i(scores[key]);
      final col = n >= 90 ? C.ok : (n >= 50 ? C.warn : C.bad);
      return Expanded(
        child: Column(children: [
          Text(scores[key] == null ? '–' : '$n', style: display(22, color: col)),
          Text(label, style: const TextStyle(fontSize: 11, color: C.faint)),
        ]),
      );
    }
    return Row(children: [one('Speed', 'performance'), one('Access', 'accessibility'), one('SEO', 'seo'), one('Best', 'best_practices')]);
  }
}

// ---------------------------------------------------------------- chat / call card
class SiteBoardCard extends StatelessWidget {
  const SiteBoardCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final st = _s(v['status']);
    final id = _s(v['id']);
    void open() => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SitePage(app: app, id: id)));
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.web_rounded, color: C.teal, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['number']} · ${_s(v['name']).isEmpty ? v['field_label'] : v['name']}',
              style: display(15), maxLines: 1, overflow: TextOverflow.ellipsis)),
          Pill(_statusUi[st] ?? st, fg: _stCol(st)),
        ]),
        const SizedBox(height: 8),
        SiteStages(v: v),
        const SizedBox(height: 8),
        if (_s(v['say']).isNotEmpty) Text(_s(v['say']), style: const TextStyle(color: C.chip, fontSize: 13)),
        if (st == 'planned') ...[
          const SizedBox(height: 6),
          for (final p in _list(_map(v['plan'])['pages']).take(8))
            Text('• ${p['title']}: ${(p['sections'] as List? ?? const []).join(', ')}',
                style: const TextStyle(fontSize: 12, color: C.muted), maxLines: 2, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 8),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(onPressed: open, child: const Text('Dekho / jawab do')),
            const SizedBox(width: 6),
            GlassButton(label: 'Haan, looks banao', height: 38, color: C.accent, onTap: () async {
              try {
                await app.api!.siteAct(id, 'plan');
                if (context.mounted) _snack(context, '3 looks ban rahe hain, yahin dikhenge.');
              } catch (e) {
                if (context.mounted) _snack(context, '$e');
              }
            }),
          ]),
        ],
        if (st == 'looks') ...[
          const SizedBox(height: 8),
          SiteLooks(app: app, v: v),
        ],
        if (st == 'building' || st == 'checking') ...[
          const SizedBox(height: 8),
          SiteBoard(v: v, compact: true),
          const SizedBox(height: 6),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(onPressed: () => app.api!.siteAct(id, 'stop'), child: const Text('Rokiye')),
            TextButton(onPressed: () => _openUrl(context, app, _s(v['preview'])), child: const Text('Live preview')),
            GlassButton(label: 'Board', height: 36, onTap: open),
          ]),
        ],
        if (st == 'ready') ...[
          const SizedBox(height: 8),
          SiteScores(scores: _map(v['scores'])),
          const SizedBox(height: 8),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(onPressed: () => _openUrl(context, app, _s(v['preview'])), child: const Text('Preview kholo')),
            GlassButton(label: 'Badlav / dekho', height: 36, color: C.accent, onTap: open),
          ]),
        ],
        if (st == 'failed' || st == 'stopped')
          Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => app.api!.siteAct(id, 'resume'), child: const Text('Aage badhao'))),
      ]),
    );
  }
}

class SiteLooks extends StatefulWidget {
  const SiteLooks({super.key, required this.app, required this.v});
  final Santosh app;
  final Map<String, dynamic> v;
  @override
  State<SiteLooks> createState() => _SiteLooksState();
}

class _SiteLooksState extends State<SiteLooks> {
  int? _colorsFrom;
  bool _busy = false;
  @override
  Widget build(BuildContext context) {
    final looks = _list(widget.v['looks']);
    final id = _s(widget.v['id']);
    if (looks.isEmpty) return const Text('Looks ban rahe hain…', style: TextStyle(color: C.faint));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(
        height: 300,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: looks.length,
          separatorBuilder: (_, __) => const SizedBox(width: 10),
          itemBuilder: (_, i) {
            final lk = looks[i];
            final cols = (lk['colors'] as List? ?? const []).map((e) => _hex(_s(e))).toList();
            return SizedBox(
              width: 170,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                GestureDetector(
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => Scaffold(
                      appBar: AppBar(title: Text(_s(lk['label']))),
                      body: SingleChildScrollView(child: Column(children: [
                        SiteShot(app: widget.app, siteId: id, name: _s(_map(lk['shots'])['390']), height: 640, fit: BoxFit.contain),
                        const SizedBox(height: 10),
                        SiteShot(app: widget.app, siteId: id, name: _s(_map(lk['shots'])['1440']), height: 260, fit: BoxFit.contain),
                      ]))))),
                  child: SiteShot(app: widget.app, siteId: id, name: _s(_map(lk['shots'])['390']), height: 210),
                ),
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
      if (_colorsFrom != null)
        Text('Rang look ${_colorsFrom! + 1} ke lagenge', style: const TextStyle(color: C.accent, fontSize: 12)),
    ]);
  }

  Future<void> _choose(int i) async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.siteAct(_s(widget.v['id']), 'look', {'index': i, if (_colorsFrom != null) 'colors_from': _colorsFrom});
      if (mounted) _snack(context, 'Banana shuru! Har section ban-te hi dikhega.');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

class SiteLeadCard extends StatelessWidget {
  const SiteLeadCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Glass(
        child: Row(children: [
          const Icon(Icons.mark_email_unread_rounded, color: C.ok),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${v['site']}: ${_s(v['name']).isEmpty ? v['phone'] : v['name']}', style: display(14)),
            if (_s(v['message']).isNotEmpty) Text(_s(v['message']), style: const TextStyle(color: C.muted, fontSize: 12.5), maxLines: 3),
          ])),
          if (_s(v['phone']).isNotEmpty)
            IconButton(icon: const Icon(Icons.call_rounded, color: C.accent),
                onPressed: () => launchUrl(Uri.parse('tel:${v['phone']}'))),
        ]),
      );
}

// ---------------------------------------------------------------- Profile > Website
class SiteScreen extends StatefulWidget {
  const SiteScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SiteScreen> createState() => _SiteScreenState();
}

class _SiteScreenState extends State<SiteScreen> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  int _tick = -1;

  @override
  void initState() {
    super.initState();
    _tick = app.siteTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.siteTick != _tick) {
      _tick = app.siteTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.siteAll();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final sites = _list(_d?['sites']);
    final lib = _map(_d?['library']);
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text('${app.aName} · Website'),
          bottom: const TabBar(tabs: [Tab(text: 'Meri websites'), Tab(text: 'Ideas (1 lakh)')]),
        ),
        floatingActionButton: FloatingActionButton.extended(
          backgroundColor: C.accent,
          foregroundColor: C.onAccent,
          onPressed: () => _newSite(context),
          icon: const Icon(Icons.add_rounded),
          label: const Text('Nayi website'),
        ),
        body: TabBarView(children: [
          RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 100), children: [
              if (_d == null) const Center(child: Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator())),
              if (_d != null && sites.isEmpty)
                Glass(child: Text('Do-teen shabd boliye, jaise "mithai dukaan ki website, WhatsApp order". '
                    '${app.aName} plan, design, motion graphics, jaanch, preview sab karega; aap har hissa banta dekhengi.',
                    style: const TextStyle(color: C.chip))),
              for (final s in sites)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Glass(
                    child: ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.web_rounded, color: C.teal),
                      title: Text('${s['number']} · ${_s(s['name']).isEmpty ? s['field_label'] : s['name']}', style: display(14)),
                      subtitle: Text('${s['style_label']} · v${s['version']} · ${_map(s['board'])['pct'] ?? 0}%',
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                      trailing: Pill(_statusUi[s['status']] ?? _s(s['status']), fg: _stCol(_s(s['status']))),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SitePage(app: app, id: _s(s['id'])))),
                    ),
                  ),
                ),
            ]),
          ),
          SiteIdeas(app: app, counts: lib, onPick: (brief) => _newSite(context, brief: brief)),
        ]),
      ),
    );
  }

  Future<void> _newSite(BuildContext context, {String brief = ''}) async {
    final b = TextEditingController(text: brief);
    final name = TextEditingController();
    final phone = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (c) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(c).viewInsets.bottom + 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Nayi website', style: display(18)),
          const SizedBox(height: 8),
          TextField(controller: b, minLines: 2, maxLines: 4,
              decoration: const InputDecoration(labelText: 'Kis cheez ki website? (apne shabdon mein)', hintText: 'mithai dukaan, WhatsApp order')),
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Business ka naam (agar alag ho)')),
          TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone / WhatsApp')),
          const SizedBox(height: 12),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Plan banao')),
        ]),
      ),
    );
    if (ok != true || b.text.trim().isEmpty) return;
    try {
      final v = await app.api!.siteNew({'brief': b.text.trim(), 'name': name.text.trim(),
        if (phone.text.trim().isNotEmpty) 'answers': {'phone': phone.text.trim()}});
      if (!context.mounted) return;
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => SitePage(app: app, id: _s(v['id']))));
      _load();
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
  }
}

/// Browse the library (industries -> business types) and start from one.
class SiteIdeas extends StatefulWidget {
  const SiteIdeas({super.key, required this.app, required this.counts, required this.onPick});
  final Santosh app;
  final Map<String, dynamic> counts;
  final void Function(String brief) onPick;
  @override
  State<SiteIdeas> createState() => _SiteIdeasState();
}

class _SiteIdeasState extends State<SiteIdeas> {
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
      final d = await widget.app.api!.siteLibrary(industry: _industry, q: _q.text.trim());
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final inds = _list(_d?['industries']);
    final fields = _list(_d?['fields']);
    final c = _map(_d?['counts']);
    return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 100), children: [
      Text('${c['fields'] ?? 1000} kaam × ${c['goals'] ?? 10} maqsad × ${c['styles'] ?? 10} design = ${c['briefs'] ?? 100000} taiyaar briefs',
          style: const TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 8),
      TextField(controller: _q, onSubmitted: (_) => _load(),
          decoration: InputDecoration(hintText: 'Dhoondho: clinic, coaching, bakery…', prefixIcon: const Icon(Icons.search_rounded),
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
          subtitle: Text('${f['hi']}', style: const TextStyle(color: C.muted)),
          trailing: TextButton(onPressed: () => widget.onPick('${f['en']} ki website'), child: const Text('Shuru')),
        ),
    ]);
  }
}

// ---------------------------------------------------------------- one site
class SitePage extends StatefulWidget {
  const SitePage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<SitePage> createState() => _SitePageState();
}

class _SitePageState extends State<SitePage> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _v;
  int _tick = -1;
  final _change = TextEditingController();
  final Map<int, TextEditingController> _answers = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _tick = app.siteTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.siteTick != _tick) {
      _tick = app.siteTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final v = await app.api!.siteGet(widget.id);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _act(String action, [Map<String, dynamic> body = const {}, String ok = '']) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.siteAct(widget.id, action, body);
      if (mounted && (ok.isNotEmpty || _s(r['say']).isNotEmpty)) _snack(context, ok.isNotEmpty ? ok : _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _photo() async {
    final src = await showModalBottomSheet<ImageSource>(context: context, builder: (c) => Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.photo_camera_rounded), title: const Text('Camera'), onTap: () => Navigator.pop(c, ImageSource.camera)),
          ListTile(leading: const Icon(Icons.photo_library_rounded), title: const Text('Gallery'), onTap: () => Navigator.pop(c, ImageSource.gallery)),
        ]));
    if (src == null) return;
    final x = await ImagePicker().pickImage(source: src, imageQuality: 88, maxWidth: 2400);
    if (x == null || !mounted) return;
    final about = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
          title: const Text('Yeh photo kya hai?'),
          content: TextField(controller: about, decoration: const InputDecoration(hintText: 'dukaan ka front, meri photo, kaju katli…')),
          actions: [TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Rakho'))],
        ));
    if (ok != true) return;
    try {
      final r = await app.api!.sitePhoto(widget.id, x.name, await x.readAsBytes(), about.text.trim());
      if (mounted) _snack(context, _s(r['say']));
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    if (v == null) return Scaffold(appBar: AppBar(), body: const Center(child: CircularProgressIndicator()));
    final st = _s(v['status']);
    final checks = _map(v['checks']);
    final shots = _map(v['shots']);
    final qs = (v['questions'] as List? ?? const []).map((e) => '$e').toList();
    return Scaffold(
      appBar: AppBar(
        title: Text('${v['number']} · ${_s(v['name']).isEmpty ? v['field_label'] : v['name']}'),
        actions: [
          if (_s(v['preview']).isNotEmpty)
            IconButton(tooltip: 'Preview', icon: const Icon(Icons.open_in_new_rounded),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SitePreview(app: app, url: _s(v['preview']), title: _s(v['name']))))),
          PopupMenuButton<String>(onSelected: (a) async {
            if (a == 'export') {
              await _act('export');
            } else if (a == 'delete') {
              final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
                    title: const Text('Website hata dein?'),
                    actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
                      TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, hatao'))]));
              if (yes == true) {
                await app.api!.siteDelete(widget.id);
                if (context.mounted) Navigator.pop(context);
              }
            }
          }, itemBuilder: (_) => const [
            PopupMenuItem(value: 'export', child: Text('ZIP banao (kisi bhi hosting ke liye)')),
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
            const SizedBox(height: 10),
            SiteBoard(v: v),
            if (st == 'building' || st == 'checking')
              Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _act('stop'), child: const Text('Rokiye'))),
            if (st == 'failed' || st == 'stopped') ...[
              if (_s(v['error']).isNotEmpty) Text(_s(v['error']), style: const TextStyle(color: C.bad, fontSize: 12.5)),
              Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _act('resume'), child: const Text('Aage badhao'))),
            ],
          ])),
          const SizedBox(height: 10),
          if (st == 'planned')
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Plan', style: display(16)),
              const SizedBox(height: 6),
              for (final p in _list(_map(v['plan'])['pages']))
                Padding(padding: const EdgeInsets.only(bottom: 4),
                    child: Text('• ${p['title']}: ${(p['sections'] as List? ?? const []).join(', ')}', style: const TextStyle(color: C.chip, fontSize: 13))),
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
                  child: GlassButton(label: 'Haan, 3 looks banao', color: C.accent, onTap: _busy ? null : () => _act('plan', const {}, 'Looks ban rahe hain…'))),
            ])),
          if (st == 'looks') Glass(child: SiteLooks(app: app, v: v)),
          if (st == 'ready' || _map(v['scores']).isNotEmpty) ...[
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [Text('Jaanch', style: display(16)), const Spacer(),
                Text(_s(checks['source']).contains('lighthouse') ? 'Lighthouse' : 'Hoola lab', style: const TextStyle(color: C.faint, fontSize: 11))]),
              const SizedBox(height: 8),
              SiteScores(scores: _map(v['scores'])),
              for (final c in _list(checks['blocking']).take(6))
                Text('⛔ ${c['text']}', style: const TextStyle(color: C.bad, fontSize: 12)),
              for (final c in _list(checks['warnings']).take(4))
                Text('⚠ ${c['text']}', style: const TextStyle(color: C.warn, fontSize: 12)),
              if (_list(checks['blocking']).isEmpty && checks['passed'] == true)
                const Text('✓ Sab zaroori jaanch paas', style: TextStyle(color: C.ok, fontSize: 12.5)),
            ])),
            const SizedBox(height: 10),
          ],
          if (shots.isNotEmpty)
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Phone aur computer par', style: display(15)),
              const SizedBox(height: 8),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Expanded(flex: 2, child: SiteShot(app: app, siteId: widget.id, name: _s(shots['home-390.jpg']), height: 330)),
                const SizedBox(width: 8),
                Expanded(flex: 3, child: SiteShot(app: app, siteId: widget.id, name: _s(shots['home-1440.jpg']), height: 200, fit: BoxFit.contain)),
              ]),
              if (_s(shots['scroll.mp4']).isNotEmpty)
                TextButton.icon(onPressed: () => _openUrl(context, app, '/api/sites/${widget.id}/shots/${shots['scroll.mp4']}'),
                    icon: const Icon(Icons.play_circle_rounded), label: const Text('Motion video (6 sec)')),
            ])),
          const SizedBox(height: 10),
          if (st == 'ready' || st == 'stopped' || st == 'failed' || st == 'building' || st == 'checking')
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Badlav bolo', style: display(15)),
              const SizedBox(height: 6),
              TextField(controller: _change, minLines: 1, maxLines: 4,
                  decoration: const InputDecoration(hintText: 'hero mein meri photo, rang halka, price list hatao…')),
              const SizedBox(height: 8),
              Row(children: [
                TextButton.icon(onPressed: _photo, icon: const Icon(Icons.add_a_photo_rounded), label: const Text('Photo')),
                const Spacer(),
                GlassButton(label: 'Badlo', color: C.accent, onTap: _busy ? null : () async {
                  final t = _change.text.trim();
                  if (t.isEmpty) return;
                  await _act('change', {'instruction': t});
                  _change.clear();
                }),
              ]),
              if (_i(v['queued']) > 0) Text('${v['queued']} badlav line mein hain', style: const TextStyle(color: C.faint, fontSize: 12)),
            ])),
          const SizedBox(height: 10),
          if (_i(v['version']) > 0) ...[
            SiteHostingPanel(app: app, siteId: widget.id, ready: st == 'ready'),
            const SizedBox(height: 12),
            SiteCarePanel(app: app, siteId: widget.id),
            const SizedBox(height: 10),
          ],
          for (final ver in _list(v['versions']).take(10))
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Text('v${ver['version']}', style: display(14)),
              title: Text(_s(ver['note']), maxLines: 2, overflow: TextOverflow.ellipsis),
              subtitle: Text('Speed ${_map(ver['scores'])['performance'] ?? '-'} · Access ${_map(ver['scores'])['accessibility'] ?? '-'}',
                  style: const TextStyle(color: C.faint, fontSize: 11.5)),
              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(ver['passed'] == true ? Icons.verified_rounded : Icons.error_outline_rounded,
                    color: ver['passed'] == true ? C.ok : C.warn),
                IconButton(tooltip: 'Yeh version live karo', icon: const Icon(Icons.history_rounded, size: 20),
                    onPressed: _busy ? null : () => showLaunchSheet(context, app, widget.id, 'rollback-request', {'version': ver['version']})),
              ]),
            ),
          if (_i(v['leads']) > 0)
            TextButton.icon(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SiteLeadsPage(app: app, id: widget.id))),
                icon: const Icon(Icons.mark_email_unread_rounded), label: Text('${v['leads']} enquiries')),
        ]),
      ),
    );
  }
}

class SitePreview extends StatefulWidget {
  const SitePreview({super.key, required this.app, required this.url, required this.title});
  final Santosh app;
  final String url;
  final String title;
  @override
  State<SitePreview> createState() => _SitePreviewState();
}

class _SitePreviewState extends State<SitePreview> {
  late final WebViewController _web;
  int _progress = 0;
  @override
  void initState() {
    super.initState();
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(onProgress: (p) {
        if (mounted) setState(() => _progress = p);
      }, onNavigationRequest: (r) {
        final u = r.url;
        if (u.startsWith('tel:') || u.startsWith('mailto:') || u.contains('wa.me') || !u.contains('/api/site-preview/')) {
          launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication);
          return NavigationDecision.prevent;
        }
        return NavigationDecision.navigate;
      }))
      ..loadRequest(Uri.parse(widget.app.api!.absolute(widget.url)));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title.isEmpty ? 'Preview' : widget.title), actions: [
          IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: () => _web.reload()),
          IconButton(icon: const Icon(Icons.open_in_browser_rounded), onPressed: () => _openUrl(context, widget.app, widget.url)),
        ]),
        body: Stack(children: [
          WebViewWidget(controller: _web),
          if (_progress < 100) LinearProgressIndicator(value: _progress / 100, minHeight: 2, color: C.teal),
        ]),
      );
}

class SiteLeadsPage extends StatefulWidget {
  const SiteLeadsPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<SiteLeadsPage> createState() => _SiteLeadsPageState();
}

class _SiteLeadsPageState extends State<SiteLeadsPage> {
  List<Map<String, dynamic>> _leads = const [];
  @override
  void initState() {
    super.initState();
    widget.app.api!.siteLeads(widget.id).then((l) {
      if (mounted) setState(() => _leads = l);
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Website enquiries')),
        body: ListView(children: [
          for (final l in _leads)
            ListTile(
              title: Text(_s(l['name']).isEmpty ? _s(l['phone']) : _s(l['name'])),
              subtitle: Text('${l['message']}\n${_s(l['at']).split('T').first}', maxLines: 3),
              isThreeLine: true,
              trailing: _s(l['phone']).isEmpty ? null : IconButton(icon: const Icon(Icons.call_rounded),
                  onPressed: () => launchUrl(Uri.parse('tel:${l['phone']}'))),
            ),
        ]),
      );
}
