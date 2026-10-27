/// Profile > SEO sahayak (v0.103): Hoola as an SEO specialist for her website and Google Business Profile.
/// Website details -> "Jaanch karo" (crawl + fix list) and "Speed" (Core Web Vitals) -> Search Console numbers when her
/// Google account is connected (read-only) -> drafts (page plan, schema, Google post, review reply) that become final on
/// her Haan; she puts them on her site / profile. Hoola never publishes, never buys links, never promises a ranking.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Color _lvl(String l) => switch (l) { 'bad' => C.bad, 'warn' => C.warn, 'good' => C.accent, 'poor' => C.bad, 'ni' => C.warn, _ => C.muted };

class SeoScreen extends StatefulWidget {
  const SeoScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SeoScreen> createState() => _SeoScreenState();
}

class _SeoScreenState extends State<SeoScreen> {
  Map<String, dynamic>? _sum;
  Map<String, dynamic>? _perf;
  List<Map<String, dynamic>> _drafts = [];
  bool _busy = false;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await widget.app.api!.seoSummary();
      final d = s['site'] == null ? <Map<String, dynamic>>[] : await widget.app.api!.seoDrafts();
      if (mounted) {
        setState(() {
          _sum = s;
          _drafts = d;
          _loaded = true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loaded = true);
        _snack(context, '$e');
      }
    }
  }

  Future<Map<String, dynamic>?> _run(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.seoAct(action, body);
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

  Future<void> _site() async {
    final site = (_sum?['site'] as Map?) ?? const {};
    final b = (site['business'] as Map?) ?? const {};
    final c = {
      'url': TextEditingController(text: _s(site['url'])),
      'name': TextEditingController(text: _s(site['name'])),
      'city': TextEditingController(text: _s(b['city'])),
      'phone': TextEditingController(text: _s(b['phone'])),
      'street': TextEditingController(text: _s(b['street'])),
      'pin': TextEditingController(text: _s(b['pin'])),
      'hours': TextEditingController(text: _s(b['hours'])),
      'services': TextEditingController(text: ((site['services'] as List?) ?? const []).join(', ')),
    };
    const labels = {
      'url': 'Website (example.in)',
      'name': 'Business ka naam',
      'city': 'Shehar',
      'phone': 'Phone',
      'street': 'Address',
      'pin': 'Pin code',
      'hours': 'Samay (Mo-Sa 10:00-20:00)',
      'services': 'Kya bechte / karte hain (comma se)',
    };
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Website'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final e in c.entries) TextField(controller: e.value, decoration: InputDecoration(labelText: labels[e.key])),
          ]),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
      ),
    );
    if (ok != true) return;
    final body = <String, dynamic>{
      for (final e in c.entries)
        if (e.key != 'services' && e.value.text.trim().isNotEmpty) e.key: e.value.text.trim(),
      'services': c['services']!.text.split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList(),
      if (site['id'] != null) 'site': site['id'],
    };
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.seoSite(body);
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _connect() async {
    try {
      final url = await widget.app.api!.seoGscLink();
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _ask(String title, String key, String action, {bool stars = false}) async {
    final t = TextEditingController();
    var st = 5;
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, setS) => AlertDialog(
          title: Text(title),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: t, maxLines: stars ? 3 : 1, decoration: InputDecoration(labelText: stars ? 'Review ka text' : 'Kis baare mein')),
            if (stars)
              Wrap(children: [
                for (var i = 1; i <= 5; i++)
                  IconButton(
                      icon: Icon(i <= st ? Icons.star_rounded : Icons.star_border_rounded, color: C.warn), onPressed: () => setS(() => st = i)),
              ]),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Draft banao'))],
        ),
      ),
    );
    if (ok != true || t.text.trim().isEmpty) return;
    await _run(action, {key: t.text.trim(), if (stars) 'stars': st});
  }

  Future<void> _final(Map<String, dynamic> d) async {
    final t = TextEditingController(text: _s(d['text']));
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(_s(d['title'])),
        content: SingleChildScrollView(child: TextField(controller: t, maxLines: null, style: const TextStyle(fontSize: 13))),
        actions: [
          TextButton(onPressed: () => Clipboard.setData(ClipboardData(text: t.text)), child: const Text('Copy')),
          if (d['status'] != 'approved') TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, final')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await widget.app.api!.seoDraftOk(_s(d['id']), t.text);
      await Clipboard.setData(ClipboardData(text: _s(r['text'])));
      if (mounted) _snack(context, '${_s(r['say'])} (copy ho gaya)');
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _cwv() {
    final cw = Map<String, dynamic>.from(((_sum?['site'] as Map?)?['cwv'] as Map?) ?? const {});
    final m = Map<String, dynamic>.from((cw['mobile'] as Map?) ?? const {});
    if (m.isEmpty) return const SizedBox();
    final g = Map<String, dynamic>.from((m['grades'] as Map?) ?? const {});
    Widget one(String k, String label, String v) => Expanded(
          child: Column(children: [
            Text(v, style: display(16, color: _lvl(_s(g[k])))),
            Text(label, style: const TextStyle(color: C.muted, fontSize: 11.5)),
          ]),
        );
    final lcp = m['lcp_ms'] == null ? '-' : '${((m['lcp_ms'] as num) / 1000).toStringAsFixed(1)}s';
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Mobile speed (asli graahak)', style: display(14)),
          const SizedBox(height: 8),
          Row(children: [
            one('lcp', 'LCP (2.5s tak)', lcp),
            one('inp', 'INP (200ms tak)', m['inp_ms'] == null ? '-' : '${m['inp_ms']}ms'),
            one('cls', 'CLS (0.1 tak)', m['cls'] == null ? '-' : '${m['cls']}'),
            Expanded(child: Column(children: [Text('${m['lab_score'] ?? '-'}', style: display(16)), const Text('lab', style: TextStyle(color: C.muted, fontSize: 11.5))])),
          ]),
          for (final f in _list(m['fixes']).take(3))
            Text('• ${_s(f['title'])} (~${((f['save_ms'] as num?) ?? 0) / 1000}s)', style: const TextStyle(fontSize: 12.5)),
        ]),
      ),
    );
  }

  Widget _gsc() {
    final g = Map<String, dynamic>.from((_sum?['gsc'] as Map?) ?? const {});
    final stats = _list(_sum?['stats']);
    if (g['connected'] != true) {
      return Padding(
        padding: const EdgeInsets.only(top: 10),
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Google Search Console', style: display(14)),
            const SizedBox(height: 4),
            const Text('Google par kitne log aapko dhoondh rahe hain, kis shabd se, kis position par: sirf padhne ki permission.',
                style: TextStyle(fontSize: 12.5, color: C.muted)),
            const SizedBox(height: 8),
            GlassButton(label: 'Search Console jodiye', icon: Icons.link_rounded, onTap: g['can_link'] == true ? _connect : null),
          ]),
        ),
      );
    }
    final last = stats.isEmpty ? null : stats.first;
    final p = _perf;
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Google se (${_s(g['address'])})', style: display(14))),
            TextButton(
              onPressed: _busy
                  ? null
                  : () async {
                      final r = await _run('performance');
                      if (r != null && mounted) setState(() => _perf = r);
                    },
              child: const Text('Taaza karo'),
            ),
          ]),
          if (last != null)
            Text('${last['clicks']} click · ${last['impressions']} baar dikhe · position ${last['position']} (${_s(last['start'])} - ${_s(last['end'])})',
                style: const TextStyle(fontSize: 13)),
          if (p != null)
            for (final o in _list(p['opportunities']).take(5))
              Padding(padding: const EdgeInsets.only(top: 4), child: Text('• ${_s(o['do'])}', style: const TextStyle(fontSize: 12.5))),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final site = _sum?['site'] as Map?;
    final tasks = _list(_sum?['top_tasks']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('SEO sahayak'), actions: [
        if (site != null)
          IconButton(icon: const Icon(Icons.table_view_rounded), tooltip: 'Report Excel', onPressed: _busy ? null : () => _run('report')),
      ]),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            if (!_loaded) const Center(child: CircularProgressIndicator()),
            if (_loaded && site == null) ...[
              const Text('Apni website jodiye: Hoola har page jaanchega, speed dekhega, aur Google par aage aane ki fix list banayega.',
                  style: TextStyle(fontSize: 14, height: 1.35)),
              const SizedBox(height: 12),
              GradientButton(label: 'Website jodiye', icon: Icons.language_rounded, onTap: _busy ? null : _site),
            ],
            if (site != null) ...[
              Glass(
                child: Row(children: [
                  Column(children: [
                    Text('${site['score'] ?? 0}', style: display(30)),
                    const Text('SEO score', style: TextStyle(color: C.muted, fontSize: 11.5)),
                  ]),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(site['name']).isEmpty ? _s(site['url']) : _s(site['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text(_s(site['url']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                      Text('${_sum?['open_tasks'] ?? 0} kaam baaki · ${_sum?['bad'] ?? 0} zaroori', style: const TextStyle(fontSize: 12.5)),
                    ]),
                  ),
                  IconButton(icon: const Icon(Icons.edit_rounded), onPressed: _busy ? null : _site),
                ]),
              ),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                GlassButton(label: 'Jaanch karo', icon: Icons.manage_search_rounded, onTap: _busy ? null : () => _run('audit')),
                GlassButton(label: 'Speed', icon: Icons.speed_rounded, onTap: _busy ? null : () => _run('speed')),
                GlassButton(label: 'Schema', icon: Icons.code_rounded, onTap: _busy ? null : () => _run('schema')),
                GlassButton(label: 'Naya page plan', icon: Icons.article_rounded, onTap: _busy ? null : () => _ask('Kis kaam / shabd ke liye page?', 'keyword', 'brief')),
                GlassButton(label: 'Google post', icon: Icons.campaign_rounded, onTap: _busy ? null : () => _ask('Google profile post', 'topic', 'gbp_post')),
                GlassButton(label: 'Review jawab', icon: Icons.reviews_rounded, onTap: _busy ? null : () => _ask('Review ka jawab', 'review', 'review_reply', stars: true)),
              ]),
              if (_busy) const Padding(padding: EdgeInsets.only(top: 10), child: LinearProgressIndicator()),
              _cwv(),
              _gsc(),
              if (tasks.isNotEmpty) ...[
                const SizedBox(height: 14),
                Text('Fix list (pehle zaroori)', style: display(15)),
                const SizedBox(height: 6),
                for (final t in tasks)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Glass(
                      padding: const EdgeInsets.all(12),
                      border: t['level'] == 'bad' ? C.bad : null,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Padding(padding: const EdgeInsets.only(top: 4), child: Icon(Icons.circle, size: 9, color: _lvl(_s(t['level'])))),
                          const SizedBox(width: 8),
                          Expanded(child: Text(_s(t['text']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
                        ]),
                        Text(Uri.tryParse(_s(t['url']))?.path ?? '', style: const TextStyle(color: C.muted, fontSize: 11.5)),
                        const SizedBox(height: 4),
                        Text('Kaise: ${_s(t['fix'])}', style: const TextStyle(fontSize: 12.5)),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: _busy
                                ? null
                                : () async {
                                    await widget.app.api!.seoTask(_s(t['id']), 'done');
                                    await _load();
                                  },
                            child: const Text('Ho gaya'),
                          ),
                        ),
                      ]),
                    ),
                  ),
              ],
              if (_drafts.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text('Drafts', style: display(15)),
                const SizedBox(height: 6),
                for (final d in _drafts.take(10))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Press(
                      onTap: () => _final(d),
                      child: Glass(
                        padding: const EdgeInsets.all(12),
                        child: Row(children: [
                          const Icon(Icons.edit_note_rounded, color: C.accent),
                          const SizedBox(width: 8),
                          Expanded(child: Text(_s(d['title']), style: const TextStyle(fontWeight: FontWeight.w700))),
                          Pill(d['status'] == 'approved' ? 'final' : 'haan baaki'),
                        ]),
                      ),
                    ),
                  ),
              ],
            ],
            const SizedBox(height: 14),
            const Text(
                'Hoola sirf aapki website aur Google ke official tools (Search Console, PageSpeed) dekhta hai. Website / Google profile par badlav '
                'aap lagati hain, aapki haan ke baad. Backlink kharidna, nakli review, keyword bharna kabhi nahi. Ranking ki guarantee koi nahi de sakta.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      ),
    );
  }
}

/// Chat cards: crawl result (`seo_update`), weekly note / drop alert (`seo_week`, `seo_alert`), a draft waiting (`seo_draft`).
class SeoCard extends StatelessWidget {
  const SeoCard({super.key, required this.kind, required this.v, required this.app});
  final String kind;
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final text = switch (kind) {
      'seo_update' => 'Website jaanch poori: score ${v['score'] ?? 0}/100, ${v['bad'] ?? 0} zaroori kaam',
      'seo_draft' => '${_s(v['title'])}: final karne ke liye aapki haan',
      _ => _s(v['text']),
    };
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SeoScreen(app: app))),
      child: Glass(
        border: kind == 'seo_alert' ? C.warn : null,
        child: Row(children: [
          Icon(kind == 'seo_draft' ? Icons.edit_note_rounded : Icons.travel_explore_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: const TextStyle(fontWeight: FontWeight.w700))),
          const Icon(Icons.chevron_right_rounded, color: C.muted),
        ]),
      ),
    );
  }
}
