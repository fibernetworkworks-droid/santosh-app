/// Profile > Product sahayak: Hoola as the product manager.
/// Aaj (what needs her) · Backlog (problems with evidence, her scores) · Roadmap (Abhi / Agla / Baad mein, capacity,
/// dependency problems, suggested plan) · Specs (PRD with Given / When / Then, dev / QA tasks) · Release (notes from what
/// shipped, Play / App Store text, publish card) · Niyam (product, KPIs, capacity, GitHub token typed only here).
/// Nothing goes outside without her tap on a publish card (ProductPublishCard).
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
String _num(dynamic v) {
  if (v == null) return '-';
  final d = v is num ? v.toDouble() : double.tryParse('$v');
  if (d == null) return '$v';
  return d == d.roundToDouble() ? d.toInt().toString() : d.toStringAsFixed(2);
}

Future<dynamic> _call(Santosh app, String method, String path, {Object? body}) =>
    app.api!.call(method, path, body: body, timeout: const Duration(seconds: 120));

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {Map<String, String> initial = const {}, String ok = 'Aage', bool obscureFirst = false}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (i, (k, label)) in fields.indexed)
            TextField(
              controller: c[k],
              obscureText: obscureFirst && i == 0,
              maxLines: obscureFirst && i == 0 ? 1 : null,
              decoration: InputDecoration(labelText: label),
            ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

const _bucketLabel = {'now': 'Abhi', 'next': 'Agla', 'later': 'Baad mein'};

class ProductScreen extends StatefulWidget {
  const ProductScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ProductScreen> createState() => _ProductScreenState();
}

class _ProductScreenState extends State<ProductScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _metrics;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _map(await _call(widget.app, 'GET', '/api/product'));
      final m = _map(await _call(widget.app, 'GET', '/api/product/metrics'));
      if (mounted) setState(() {
        _d = d;
        _metrics = m;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, method, path, body: body));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _newIdea() async {
    final f = await _form(context, 'Idea / dikkat / competitor note', const [
      ('text', 'Aapke shabd (har line ek baat)'),
      ('competitor', 'Competitor ka naam (ho to)'),
    ]);
    if (f == null || f['text'] == null) return;
    await _run('POST', '/api/product/ideas', {...f, if (f['competitor'] != null) 'source': 'competitor'});
  }

  Future<void> _newRelease() async {
    final f = await _form(context, 'Naya release', const [
      ('version', 'Version (jaise 2.4.0)'),
      ('text', 'Kya ship hua (har line ek badlaav)'),
      ('since', 'Kab se (dd-mm-yyyy, khaali = pichhla release)'),
    ]);
    if (f == null || f['version'] == null) return;
    final r = await _run('POST', '/api/product/releases', f);
    final rel = _map(r?['release']);
    if (rel.isNotEmpty && mounted) _openRelease(_s(rel['number']));
  }

  void _openOpp(String ref) => Navigator.push(
      context, MaterialPageRoute(builder: (_) => ProductOppPage(app: widget.app, ref: ref))).then((_) => _load());
  void _openSpec(String ref) => Navigator.push(
      context, MaterialPageRoute(builder: (_) => ProductSpecPage(app: widget.app, ref: ref))).then((_) => _load());
  void _openRelease(String ref) => Navigator.push(
      context, MaterialPageRoute(builder: (_) => ProductReleasePage(app: widget.app, ref: ref))).then((_) => _load());

  Widget _oppTile(Map<String, dynamic> o) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => _openOpp(_s(o['number'])),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(_s(o['number']), style: const TextStyle(fontSize: 11.5, color: C.faint, fontWeight: FontWeight.w800)),
                const SizedBox(width: 8),
                Expanded(child: Text(_s(o['title']), style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(o['score'] == null ? 'score?' : _num(o['score']),
                    fg: o['score'] == null ? C.warn : C.onAccent, bg: o['score'] == null ? const Color(0x1FFFFFFF) : C.accent),
              ]),
              const SizedBox(height: 4),
              Wrap(spacing: 6, runSpacing: 4, children: [
                for (final s in (o['sources'] as List? ?? const [])) Pill('$s'),
                if ((o['seen'] ?? 0) > 0) Pill('${o['seen']} log'),
                if (_s(o['bucket']).isNotEmpty) Pill(_bucketLabel[_s(o['bucket'])] ?? _s(o['bucket']), fg: C.teal),
                if (_s(o['kano']).isNotEmpty) Pill(_s(o['kano'])),
              ]),
            ]),
          ),
        ),
      );

  Widget _today() {
    final d = _map(_d?['day']);
    final pubs = _list(_d?['publishes']);
    final dups = _list(_d?['duplicates']);
    final m = _metrics ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: GlassButton(label: 'Feedback padho', icon: Icons.download_rounded,
            onTap: _busy ? null : () => _run('POST', '/api/product/harvest', {}))),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Naya idea', icon: Icons.lightbulb_outline_rounded, onTap: _busy ? null : _newIdea)),
      ]),
      for (final p in pubs) ...[
        const SizedBox(height: 10),
        ProductPublishCard(app: widget.app, data: p, onDone: _load),
      ],
      if (dups.isNotEmpty) ...[
        const SizedBox(height: 12),
        const Caption('Ek jaise lag rahe hain'),
        for (final p in dups)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              child: Row(children: [
                Expanded(child: Text('${p['a']} ${p['a_title']}\n${p['b']} ${p['b_title']}', style: const TextStyle(fontSize: 12.5))),
                TextButton(
                    onPressed: _busy ? null : () => _run('POST', '/api/product/opportunities/${p['a']}/merge', {'into': p['b']}),
                    child: const Text('Milao')),
              ]),
            ),
          ),
      ],
      const SizedBox(height: 12),
      const Caption('Number (KPI)'),
      Text(_s(m['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
      for (final k in _list(m['kpis']))
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Glass(
            padding: const EdgeInsets.all(10),
            child: Row(children: [
              Expanded(
                  child: Text('${k['north_star'] == true ? '★ ' : ''}${k['name']}: ${_num(k['latest'])} ${_s(k['unit'])}'
                      '${k['target'] != null ? ' (lakshya ${_num(k['target'])})' : ''}',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700))),
              IconButton(
                icon: const Icon(Icons.add_rounded),
                tooltip: 'Aaj ka number',
                onPressed: () async {
                  final f = await _form(context, _s(k['name']), const [('value', 'Number'), ('day', 'Tareekh (khaali = aaj)')]);
                  if (f == null || f['value'] == null) return;
                  await _run('POST', '/api/product/metrics', {'kpi': k['id'], 'value': double.tryParse(f['value']!), 'day': f['day'] ?? ''});
                },
              ),
            ]),
          ),
        ),
      for (final r in _list(m['shipped']))
        if (_map(r['result']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('• ${r['number']} ${r['title']}: ${_s(_map(r['result'])['say'])}', style: const TextStyle(fontSize: 12.5)),
          ),
    ]);
  }

  Widget _backlog() {
    final b = _map(_d?['backlog']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(_s(b['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 8),
      GlassButton(
          label: 'Nayi dikkat likho',
          icon: Icons.add_rounded,
          onTap: _busy
              ? null
              : () async {
                  final f = await _form(context, 'Graahak ki dikkat', const [('title', 'Ek line'), ('problem', 'Thoda vistaar'), ('who', 'Kinke liye')]);
                  if (f == null || f['title'] == null) return;
                  await _run('POST', '/api/product/opportunities', f);
                }),
      const SizedBox(height: 8),
      for (final o in _list(b['items'])) _oppTile(o),
    ]);
  }

  Widget _roadmap() {
    final rm = _map(_d?['roadmap']);
    final bk = _map(rm['buckets']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(_s(rm['say']), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      for (final p in _list(rm['problems']))
        Text('• ${p['say']}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(
          child: GlassButton(
            label: 'Sujhaav do',
            icon: Icons.auto_awesome_rounded,
            onTap: _busy
                ? null
                : () async {
                    final r = await _run('POST', '/api/product/roadmap/plan', {'apply': false});
                    if (r == null || !mounted) return;
                    final moves = _list(r['moves']).where((m) => m['from'] != m['to']).toList();
                    final ok = await showDialog<bool>(
                      context: context,
                      builder: (d) => AlertDialog(
                        title: const Text('Roadmap ka sujhaav'),
                        content: SingleChildScrollView(
                          child: Text([
                            for (final m in moves) '${m['number']} ${m['title']}: ${_bucketLabel[m['to']] ?? m['to']}',
                            if ((r['unscored'] as List? ?? const []).isNotEmpty) '\nScore baaki: ${(r['unscored'] as List).join(', ')}',
                          ].join('\n')),
                        ),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
                          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Lagao')),
                        ],
                      ),
                    );
                    if (ok == true) await _run('POST', '/api/product/roadmap/plan', {'apply': true});
                  },
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
            child: GlassButton(
                label: 'Files', icon: Icons.description_rounded, onTap: _busy ? null : () => _run('POST', '/api/product/roadmap/files', {}))),
      ]),
      const SizedBox(height: 6),
      GlassButton(
          label: 'Graahakon ko dikhao (card)',
          icon: Icons.public_rounded,
          onTap: _busy ? null : () => _run('POST', '/api/product/publish', {'what': 'roadmap', 'dest': 'page'})),
      for (final b in const ['now', 'next', 'later']) ...[
        const SizedBox(height: 12),
        Builder(builder: (_) {
          final v = _map(bk[b]);
          final cap = v['capacity'];
          return Text('${_bucketLabel[b]} · ${_num(v['effort'])}${cap != null ? ' / ${_num(cap)}' : ''} person-month',
              style: TextStyle(fontWeight: FontWeight.w800, color: v['over'] == true ? C.bad : C.ink));
        }),
        const SizedBox(height: 6),
        for (final o in _list(_map(bk[b])['items'])) _oppTile(o),
      ],
    ]);
  }

  Widget _specs() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Backlog mein kisi dikkat par "Spec likho" dabaiye.', style: TextStyle(fontSize: 12.5, color: C.muted)),
        const SizedBox(height: 8),
        for (final sp in _list(_d?['specs']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _openSpec(_s(sp['number'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  Expanded(child: Text('${sp['number']} ${sp['title']}\n${sp['stories']} story · v${sp['version']}',
                      style: const TextStyle(fontWeight: FontWeight.w700))),
                  Pill(sp['status'] == 'ready' ? 'taiyaar' : '${sp['blocks']} baaki', fg: sp['status'] == 'ready' ? C.ok : C.warn),
                ]),
              ),
            ),
          ),
      ]);

  Widget _releases() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(label: 'Naya release', icon: Icons.rocket_launch_rounded, onTap: _busy ? null : _newRelease),
        const SizedBox(height: 8),
        for (final r in _list(_d?['releases']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _openRelease(_s(r['number'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  Expanded(child: Text('${r['version']} · ${r['title']}\n${r['day']} · ${r['items']} badlaav',
                      style: const TextStyle(fontWeight: FontWeight.w700))),
                  Pill(_s(r['status']), fg: r['status'] == 'published' ? C.ok : C.chip),
                ]),
              ),
            ),
          ),
      ]);

  Widget _rules() {
    final st = _map(_d?['settings']);
    final cap = _map(st['capacity']);
    final gh = _map(st['github']);
    final ns = _map(st['north_star']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Product: ${_s(st['product']).isEmpty ? '-' : st['product']}', style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Users: ${_s(st['who']).isEmpty ? '-' : st['who']}', style: const TextStyle(fontSize: 12.5)),
          Text('Score: ${_s(st['scoring']).toUpperCase()} · Capacity: Abhi ${_num(cap['now'])}, Agla ${_num(cap['next'])}, Baad ${_num(cap['later'])}',
              style: const TextStyle(fontSize: 12.5)),
          Text('North star: ${_s(ns['name']).isEmpty ? '-' : ns['name']}', style: const TextStyle(fontSize: 12.5)),
          Text('GitHub: ${gh['joined'] == true ? '${gh['label']} · ${st['repo']}' : 'juda nahi'}', style: const TextStyle(fontSize: 12.5)),
        ]),
      ),
      const SizedBox(height: 8),
      GlassButton(
        label: 'Product aur capacity',
        icon: Icons.tune_rounded,
        onTap: () async {
          final f = await _form(context, 'Product ke niyam', const [
            ('product', 'Kya bana rahe hain'),
            ('who', 'Kinke liye'),
            ('now', 'Abhi ki capacity (person-month)'),
            ('next', 'Agle ki capacity'),
            ('later', 'Baad ki capacity'),
            ('scoring', 'rice ya ice'),
            ('ns', 'North star number (jaise: har hafte order karne wale)'),
            ('ns_target', 'North star lakshya'),
          ], initial: {
            'product': _s(st['product']),
            'who': _s(st['who']),
            'scoring': _s(st['scoring']),
            if (cap['now'] != null) 'now': _num(cap['now']),
            if (cap['next'] != null) 'next': _num(cap['next']),
            if (cap['later'] != null) 'later': _num(cap['later']),
            if (_s(ns['name']).isNotEmpty) 'ns': _s(ns['name']),
          });
          if (f == null) return;
          await _run('PUT', '/api/product/settings', {
            if (f['product'] != null) 'product': f['product'],
            if (f['who'] != null) 'who': f['who'],
            if (f['scoring'] != null) 'scoring': f['scoring']!.toLowerCase(),
            'capacity': {for (final b in ['now', 'next', 'later']) if (f[b] != null) b: f[b]},
            if (f['ns'] != null) 'north_star': {'name': f['ns'], if (f['ns_target'] != null) 'target': f['ns_target']},
          });
        },
      ),
      const SizedBox(height: 6),
      GlassButton(
        label: 'KPI jodo',
        icon: Icons.insights_rounded,
        onTap: () async {
          final f = await _form(context, 'KPI', const [('name', 'Naam'), ('unit', 'Unit (%, log, ₹)'), ('target', 'Lakshya'), ('better', 'up ya down')]);
          if (f == null || f['name'] == null) return;
          await _run('POST', '/api/product/kpis', {...f, if (f['target'] != null) 'target': double.tryParse(f['target']!)});
        },
      ),
      const SizedBox(height: 6),
      GlassButton(
        label: gh['joined'] == true ? 'GitHub token badlo' : 'GitHub jodo (sirf padhne ke liye)',
        icon: Icons.code_rounded,
        onTap: () async {
          final f = await _form(context, 'GitHub (fine-grained token)', const [
            ('token', 'Token (Pull requests + Contents: read; release ke liye Contents: write)'),
            ('repo', 'Repo (owner/naam)'),
          ], initial: {'repo': _s(st['repo'])}, obscureFirst: true, ok: 'Jodo');
          if (f == null || f['token'] == null) return;
          await _run('PUT', '/api/product/github', f);
        },
      ),
      if (gh['joined'] == true)
        TextButton(onPressed: () => _run('DELETE', '/api/product/github'), child: const Text('GitHub token hatao')),
      const SizedBox(height: 8),
      const Text('Hoola apne se koi number (reach, effort, revenue) nahi gadhta. Roadmap / release notes bahar sirf aapke tap se jaate hain.',
          style: TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Backlog', 'Roadmap', 'Specs', 'Release', 'Niyam'];
    final body = [_today, _backlog, _roadmap, _specs, _releases, _rules][_tab]();
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Product sahayak'),
        actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _busy ? null : _load)],
      ),
      body: Column(children: [
        SizedBox(
          height: 44,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (final (i, t) in tabs.indexed)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ),
          ]),
        ),
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        Expanded(
          child: _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [body]),
                ),
        ),
      ]),
    );
  }
}

/// One opportunity: evidence, her scores, Kano, roadmap place, spec.
class ProductOppPage extends StatefulWidget {
  const ProductOppPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<ProductOppPage> createState() => _ProductOppPageState();
}

class _ProductOppPageState extends State<ProductOppPage> {
  Map<String, dynamic>? _o;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final o = _map(await _call(widget.app, 'GET', '/api/product/opportunities/${widget.ref}'));
      if (mounted) setState(() => _o = o);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _act(String action, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/product/opportunities/${widget.ref}/$action', body: body));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _score() async {
    final o = _o ?? const {};
    final f = await _form(context, 'Aapka andaaza (RICE)', const [
      ('reach', 'Reach: kitne log, 3 mahine mein'),
      ('impact', 'Impact: 3 / 2 / 1 / 0.5 / 0.25'),
      ('confidence', 'Confidence: 100 / 80 / 50'),
      ('effort', 'Effort: "2 hafte" / "1 mahina"'),
    ], initial: {
      if (o['reach'] != null) 'reach': _num(o['reach']),
      if (o['impact'] != null) 'impact': _num(o['impact']),
      if (o['confidence'] != null) 'confidence': _num((o['confidence'] as num) * 100),
      if (o['effort'] != null) 'effort': _num(o['effort']),
    }, ok: 'Save');
    if (f == null) return;
    await _act('score', f);
  }

  @override
  Widget build(BuildContext context) {
    final o = _o;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.ref)),
      body: o == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
              Text(_s(o['title']), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              if (_s(o['problem']).isNotEmpty) Text(_s(o['problem']), style: const TextStyle(fontSize: 13, color: C.muted)),
              const SizedBox(height: 10),
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(o['score'] == null ? 'Score baaki' : 'Score ${_num(o['score'])}',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                  if (_s(o['formula']).isNotEmpty) Text(_s(o['formula']), style: const TextStyle(fontSize: 12, color: C.muted)),
                  if (_s(o['ask']).isNotEmpty) Text(_s(o['ask']), style: const TextStyle(fontSize: 12.5, color: C.warn)),
                  for (final n in (o['score_notes'] as List? ?? const [])) Text('$n', style: const TextStyle(fontSize: 12, color: C.warn)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 8, children: [
                    TextButton(onPressed: _busy ? null : _score, child: const Text('Andaaza do')),
                    if ((o['seen'] ?? 0) > 0)
                      TextButton(
                          onPressed: _busy ? null : () => _act('score', {'use_seen': true}),
                          child: Text('Reach = ${o['seen']} dekhe gaye log')),
                  ]),
                ]),
              ),
              const SizedBox(height: 10),
              const Caption('Roadmap par'),
              Wrap(spacing: 6, children: [
                for (final b in const ['now', 'next', 'later', 'none'])
                  ChoiceChip(
                    label: Text(_bucketLabel[b] ?? 'Backlog'),
                    selected: (_s(o['bucket']).isEmpty ? 'none' : _s(o['bucket'])) == b,
                    onSelected: _busy ? null : (_) => _act('place', {'bucket': b}),
                  ),
              ]),
              const SizedBox(height: 10),
              const Caption('Kano (graahak ke liye kaisa)'),
              Wrap(spacing: 6, children: [
                for (final k in const ['must', 'performance', 'attractive', 'indifferent'])
                  ChoiceChip(label: Text(k), selected: o['kano'] == k, onSelected: _busy ? null : (_) => _act('kano', {'category': k})),
              ]),
              const SizedBox(height: 12),
              const Caption('Saboot'),
              for (final e in _list(o['evidence']))
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Glass(
                    padding: const EdgeInsets.all(10),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${e['label']}${e['count'] != null ? ' · ${e['count']}' : ''}${e['people'] != null ? ' · ${e['people']} log' : ''}'
                          '${e['rupees'] != null ? ' · ~₹${_num(e['rupees'])}' : ''}',
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
                      if (_s(e['trend']).isNotEmpty) Text(_s(e['trend']), style: const TextStyle(fontSize: 12, color: C.muted)),
                      if (_s(e['note']).isNotEmpty) Text(_s(e['note']), style: const TextStyle(fontSize: 12, color: C.muted)),
                      for (final q in (e['quotes'] as List? ?? const []))
                        Text('“$q”', style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
                    ]),
                  ),
                ),
              const SizedBox(height: 12),
              const Caption('Tareeke (solutions)'),
              for (final s in _list(o['solutions']))
                Text('${s['chosen'] == true ? '✓ ' : '• '}${s['text']}', style: const TextStyle(fontSize: 13)),
              TextButton(
                onPressed: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Naya tareeka', const [('text', 'Tareeka'), ('assumption', 'Kya maan rahe hain (test karna hai)')]);
                        if (f == null || f['text'] == null) return;
                        await _act('solution', f);
                      },
                child: const Text('Tareeka jodo'),
              ),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                  child: GradientButton(
                    label: 'Spec likho',
                    icon: Icons.article_rounded,
                    onTap: _busy
                        ? null
                        : () async {
                            final r = await _act('spec', {});
                            final sp = _map(r?['spec']);
                            if (sp.isNotEmpty && mounted) {
                              Navigator.push(context,
                                  MaterialPageRoute(builder: (_) => ProductSpecPage(app: widget.app, ref: _s(sp['number']))));
                            }
                          },
                  ),
                ),
              ]),
              const SizedBox(height: 8),
              Wrap(spacing: 8, children: [
                TextButton(onPressed: _busy ? null : () => _act('ship', {}), child: const Text('Ship ho gaya')),
                if (_s(o['shipped_on']).isNotEmpty)
                  TextButton(onPressed: _busy ? null : () => _act('result', {}), child: const Text('Pehle / baad dekho')),
                TextButton(
                  onPressed: _busy
                      ? null
                      : () async {
                          final f = await _form(context, 'Chhod dein?', const [('reason', 'Wajah')], ok: 'Chhodo');
                          if (f == null) return;
                          await _act('drop', f);
                        },
                  child: const Text('Chhodo', style: TextStyle(color: C.bad)),
                ),
              ]),
              if (_map(o['result']).isNotEmpty) Text(_s(_map(o['result'])['say']), style: const TextStyle(fontSize: 12.5)),
            ]),
    );
  }
}

/// A spec (PRD): sections, checks, tasks for the Developer / QA Sahayak, files, change by words.
class ProductSpecPage extends StatefulWidget {
  const ProductSpecPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<ProductSpecPage> createState() => _ProductSpecPageState();
}

class _ProductSpecPageState extends State<ProductSpecPage> {
  Map<String, dynamic>? _sp;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = _map(await _call(widget.app, 'GET', '/api/product/specs/${widget.ref}'));
      if (mounted) setState(() => _sp = s);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _go(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, method, path, body: body));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sp = _sp;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.ref), actions: [
        IconButton(
            icon: const Icon(Icons.copy_rounded),
            tooltip: 'Copy',
            onPressed: sp == null
                ? null
                : () {
                    Clipboard.setData(ClipboardData(text: _s(sp['markdown'])));
                    _snack(context, 'Spec copy ho gaya');
                  }),
      ]),
      body: sp == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
              for (final c in _list(sp['checks']))
                Text('${c['level'] == 'block' ? '⛔' : '⚠'} ${c['say']}',
                    style: TextStyle(fontSize: 12.5, color: c['level'] == 'block' ? C.bad : C.warn)),
              const SizedBox(height: 8),
              Glass(child: SelectableText(_s(sp['markdown']), style: const TextStyle(fontSize: 13, height: 1.4))),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                GlassButton(
                  label: 'Badlav bolo',
                  icon: Icons.edit_note_rounded,
                  onTap: _busy
                      ? null
                      : () async {
                          final f = await _form(context, 'Kya badlein?', const [('instruction', 'Aapke shabd')]);
                          if (f == null || f['instruction'] == null) return;
                          await _go('POST', '/api/product/specs/${widget.ref}/revise', f);
                        },
                ),
                GlassButton(
                  label: 'Dev / QA kaam',
                  icon: Icons.checklist_rounded,
                  onTap: _busy
                      ? null
                      : () async {
                          final r = await _go('GET', '/api/product/specs/${widget.ref}/tasks');
                          if (r == null || !mounted) return;
                          await Clipboard.setData(ClipboardData(text: _s(r['gherkin'])));
                          if (!mounted) return;
                          showDialog<void>(
                            context: context,
                            builder: (d) => AlertDialog(
                              title: Text(_s(r['say'])),
                              content: SingleChildScrollView(
                                child: Text([
                                  for (final t in _list(r['dev_tasks'])) '• ${t['id']}: ${t['title']}',
                                  '',
                                  'Test scenarios (Gherkin) copy ho gaye.',
                                ].join('\n')),
                              ),
                              actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))],
                            ),
                          );
                        },
                ),
                GlassButton(
                    label: 'Word / Markdown',
                    icon: Icons.description_rounded,
                    onTap: _busy ? null : () => _go('POST', '/api/product/specs/${widget.ref}/files', {})),
              ]),
            ]),
    );
  }
}

/// A release: customer notes in Hinglish + English, Play / App Store text, internal changelog, publish card.
class ProductReleasePage extends StatefulWidget {
  const ProductReleasePage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<ProductReleasePage> createState() => _ProductReleasePageState();
}

class _ProductReleasePageState extends State<ProductReleasePage> {
  Map<String, dynamic>? _r;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _map(await _call(widget.app, 'GET', '/api/product/releases/${widget.ref}'));
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _go(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, method, path, body: body));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _block(String title, String text) => Padding(
        padding: const EdgeInsets.only(top: 10),
        child: Glass(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5))),
              Text('${text.length}', style: const TextStyle(fontSize: 11, color: C.faint)),
              IconButton(
                  icon: const Icon(Icons.copy_rounded, size: 18),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: text));
                    _snack(context, 'Copy ho gaya');
                  }),
            ]),
            SelectableText(text, style: const TextStyle(fontSize: 13, height: 1.35)),
          ]),
        ),
      );

  Future<void> _edit() async {
    final n = _map(_r?['notes']);
    final f = await _form(context, 'Notes badlo', const [('hinglish', 'Hinglish (har line ek)'), ('english', 'English (har line ek)')],
        initial: {
          'hinglish': (n['hinglish'] as List? ?? const []).join('\n'),
          'english': (n['english'] as List? ?? const []).join('\n'),
        },
        ok: 'Save');
    if (f == null) return;
    await _go('PUT', '/api/product/releases/${widget.ref}', {
      if (f['hinglish'] != null) 'hinglish': f['hinglish']!.split('\n'),
      if (f['english'] != null) 'english': f['english']!.split('\n'),
    });
  }

  Future<void> _publish() async {
    final dest = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.code_rounded), title: const Text('GitHub release'), onTap: () => Navigator.pop(c, 'github')),
          ListTile(leading: const Icon(Icons.public_rounded), title: const Text('Hoola ka public page (link)'), onTap: () => Navigator.pop(c, 'page')),
          ListTile(
              leading: const Icon(Icons.content_paste_rounded),
              title: const Text('Main khud paste karungi (Play / App Store / WhatsApp)'),
              onTap: () => Navigator.pop(c, 'copy')),
        ]),
      ),
    );
    if (dest == null) return;
    final r = await _go('POST', '/api/product/publish', {'what': 'release', 'ref': widget.ref, 'dest': dest});
    final card = _map(r?['card']);
    if (card.isNotEmpty && mounted) {
      showDialog<void>(
        context: context,
        builder: (d) => AlertDialog(
          content: ProductPublishCard(app: widget.app, data: card, onDone: () {
            Navigator.pop(d);
            _load();
          }),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final n = _map(r?['notes']);
    final play = _map(n['play']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(r == null ? widget.ref : 'Release ${r['version']}')),
      body: r == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
              Text(_s(n['title']), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              Text('${r['day']} · ${r['status']}', style: const TextStyle(fontSize: 12, color: C.muted)),
              for (final c in _list(r['checks']))
                Text('${c['level'] == 'block' ? '⛔' : '⚠'} ${c['say']}',
                    style: TextStyle(fontSize: 12.5, color: c['level'] == 'block' ? C.bad : C.warn)),
              _block('Graahak ke liye (Hinglish)', (n['hinglish'] as List? ?? const []).map((x) => '• $x').join('\n')),
              _block('Customers (English)', (n['english'] as List? ?? const []).map((x) => '• $x').join('\n')),
              _block('Google Play "What\'s new" (Hinglish, 500 tak)', _s(play['hinglish'])),
              _block('Google Play "What\'s new" (en-IN, 500 tak)', _s(play['en-IN'])),
              _block('App Store "What\'s New" (4000 tak)', _s(n['appstore'])),
              _block('Changelog (andar ke liye)', _s(n['changelog'])),
              const SizedBox(height: 12),
              if (r['status'] != 'published')
                Row(children: [
                  Expanded(child: GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _busy ? null : _edit)),
                  const SizedBox(width: 8),
                  Expanded(child: GradientButton(label: 'Publish card', icon: Icons.send_rounded, onTap: _busy ? null : _publish)),
                ]),
              TextButton(
                  onPressed: _busy ? null : () => _go('POST', '/api/product/releases/${widget.ref}/files', {}),
                  child: const Text('Files banao (Word / Markdown)')),
            ]),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards

/// `product_publish`: roadmap / release notes going outside; ONLY this tap sends it (hash of the exact text).
class ProductPublishCard extends StatefulWidget {
  const ProductPublishCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ProductPublishCard> createState() => _ProductPublishCardState();
}

class _ProductPublishCardState extends State<ProductPublishCard> {
  bool _busy = false;
  late String _status = _s(widget.data['status']).isEmpty ? 'waiting' : _s(widget.data['status']);
  String _url = '';

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/product/publish/${widget.data['id']}/decide',
          body: {'yes': yes, 'hash': widget.data['hash']}));
      if (!mounted) return;
      setState(() {
        _status = _s(r['status']);
        _url = _s(r['url']);
      });
      if (yes && _s(widget.data['dest']) == 'copy' && _status == 'published') {
        await Clipboard.setData(ClipboardData(text: _s(widget.data['text'])));
      }
      if (mounted) _snack(context, _s(r['say']));
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    return Glass(
      border: _status == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Icon(Icons.campaign_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Bahar bhejna hai: ${_s(d['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        Text('Kahan: ${_s(d['where']).isEmpty ? _s(d['dest']) : d['where']}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        const SizedBox(height: 6),
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 220),
          child: SingleChildScrollView(child: Text(_s(d['text']), style: const TextStyle(fontSize: 12.5, height: 1.35))),
        ),
        const SizedBox(height: 8),
        if (_status == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, bhejo', onTap: _busy ? null : () => _decide(true), height: 44)),
            const SizedBox(width: 8),
            TextButton(onPressed: _busy ? null : () => _decide(false), child: const Text('Mana')),
          ])
        else
          Row(children: [
            Pill(_status, fg: _status == 'published' ? C.ok : C.chip),
            if (_url.startsWith('http'))
              TextButton(onPressed: () => Native.openExternal(url: _url), child: const Text('Kholo')),
          ]),
      ]),
    );
  }
}

/// `product_backlog` / `product_spec` / `product_release` / `product_day`: a note with a button to the screen.
class ProductNoteCard extends StatelessWidget {
  const ProductNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final spec = _map(data['spec']);
    final rel = _map(data['release']);
    final items = _list(data['items']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.route_rounded, color: C.teal, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, height: 1.35))),
        ]),
        for (final o in items.take(5))
          Text('• ${o['number']} ${o['title']}', style: const TextStyle(fontSize: 12.5)),
        for (final x in (_map(data['notes'])['hinglish'] as List? ?? const []).take(5))
          Text('• $x', style: const TextStyle(fontSize: 12.5)),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () {
              final Widget page = spec.isNotEmpty
                  ? ProductSpecPage(app: app, ref: _s(spec['number']))
                  : rel.isNotEmpty
                      ? ProductReleasePage(app: app, ref: _s(rel['number']))
                      : ProductScreen(app: app);
              Navigator.push(context, MaterialPageRoute(builder: (_) => page));
            },
            child: const Text('Kholo'),
          ),
        ),
      ]),
    );
  }
}
