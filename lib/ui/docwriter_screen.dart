/// Profile > "<name> · Technical writer" (Docs Sahayak).
/// Aaj (stale docs, publish cards, products to prove) · Docs (manuals, quick starts, how-tos, FAQ, admin, API, release notes)
/// · Sources (Hoola app / site, her live site with ownership proof + recorded steps, GitHub read-only, files) · Niyam
/// (audience, tone, languages, glossary, words never translated, her support line, GitHub token typed only here).
/// Nothing goes public without her tap on the publish card.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _kinds = <(String, String)>[
  ('manual', 'User manual'),
  ('quickstart', 'Quick start'),
  ('howto', 'How-to'),
  ('faq', 'FAQ'),
  ('admin', 'Admin guide'),
  ('api', 'API reference'),
  ('release_notes', 'Release notes'),
  ('changelog', 'Changelog'),
];
const _langs = <(String, String)>[('en', 'English'), ('hinglish', 'Hinglish'), ('hi', 'हिंदी'), ('mr', 'मराठी')];
const _sources = <(String, String, String)>[
  ('hoola_app', 'Hoola ki banayi app', 'App number (A-0001)'),
  ('hoola_site', 'Hoola ki banayi website', 'Site number (S-0001)'),
  ('web', 'Meri live website / web app', 'https://...'),
  ('github', 'Mera GitHub repo (sirf padhna)', 'owner/repo'),
];

Widget _img(Santosh app, String path, {double? height}) {
  final api = app.api;
  if (api == null || path.isEmpty) return const SizedBox.shrink();
  final base = api.baseUrl.endsWith('/') ? api.baseUrl.substring(0, api.baseUrl.length - 1) : api.baseUrl;
  return ClipRRect(
    borderRadius: BorderRadius.circular(10),
    child: Image.network('$base$path',
        height: height,
        fit: BoxFit.contain,
        headers: {if (api.apiKey.isNotEmpty) 'Authorization': 'Bearer ${api.apiKey}'},
        errorBuilder: (_, __, ___) => const SizedBox(height: 40, child: Center(child: Icon(Icons.image_not_supported_outlined)))),
  );
}

Future<String?> _ask(BuildContext context, String title, {String hint = '', bool lines = false, bool obscure = false, String initial = ''}) async {
  final c = TextEditingController(text: initial);
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: c,
        obscureText: obscure,
        autofocus: true,
        minLines: lines ? 4 : 1,
        maxLines: lines ? 12 : 1,
        decoration: InputDecoration(hintText: hint),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage')),
      ],
    ),
  );
  if (ok != true || c.text.trim().isEmpty) return null;
  return c.text.trim();
}

Future<String?> _pick(BuildContext context, String title, List<(String, String)> opts) => showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: ListView(shrinkWrap: true, children: [
          ListTile(title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800))),
          for (final (id, label) in opts) ListTile(title: Text(label), onTap: () => Navigator.pop(c, id)),
        ]),
      ),
    );

class DocwriterScreen extends StatefulWidget {
  const DocwriterScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DocwriterScreen> createState() => _DocwriterScreenState();
}

class _DocwriterScreenState extends State<DocwriterScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.call('GET', '/api/docwriter');
      if (mounted) setState(() => _d = _map(d));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
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

  Future<void> _newDoc() async {
    final prods = _list(_d?['products']).where((p) => p['verified'] == true).toList();
    if (prods.isEmpty) {
      _snack(context, 'Pehle Sources mein product jodiye (aur sabit kijiye ki aapka hai).');
      setState(() => _tab = 2);
      return;
    }
    final pid = prods.length == 1
        ? _s(prods.first['id'])
        : await _pick(context, 'Kis cheez ke docs?', [for (final p in prods) (_s(p['id']), '${p['name']} (${p['kind']})')]);
    if (pid == null || !mounted) return;
    final kind = await _pick(context, 'Kaunsa doc?', _kinds);
    if (kind == null || !mounted) return;
    final lang = await _pick(context, 'Bhasha', _langs) ?? 'en';
    if (!mounted) return;
    final words = await _ask(context, 'Kuch khaas? (zaroori nahi)', hint: 'Jaise: naye staff ke liye, order lene ka tareeka', lines: true);
    final r = await _run(() => widget.app.api!.call('POST', '/api/docwriter/docs',
        body: {'product': pid, 'kind': kind, 'lang': lang, if (words != null) 'words': words}, timeout: const Duration(minutes: 6)));
    final doc = _map(r?['doc']);
    if (doc.isNotEmpty && mounted) _open(_s(doc['id']));
  }

  void _open(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => DocwriterDocPage(app: widget.app, docId: id)))
      .then((_) => _load());

  Future<void> _addSource() async {
    final kind = await _pick(context, 'Docs kis cheez ke?', [for (final (k, l, _) in _sources) (k, l)]);
    if (kind == null || !mounted) return;
    final hint = _sources.firstWhere((e) => e.$1 == kind).$3;
    final ref = await _ask(context, 'Kaunsa?', hint: hint);
    if (ref == null) return;
    await _run(() => widget.app.api!.call('POST', '/api/docwriter/products', body: {'kind': kind, 'ref': ref}, timeout: const Duration(minutes: 2)));
  }

  Future<void> _recordFlow(Map<String, dynamic> p) async {
    final name = await _ask(context, 'Kaam ka naam', hint: 'Jaise: Naya order kaise karein');
    if (name == null || !mounted) return;
    final steps = await _ask(context, 'Steps (ek line mein ek)',
        hint: 'goto /login\nfill "Email" = demo@shop.in\nclick "Orders"\nscreenshot "Orders ki list"', lines: true);
    if (steps == null) return;
    await _run(() => widget.app.api!.call('POST', '/api/docwriter/products/${p['id']}/flows',
        body: {'name': name, 'steps': steps.split('\n').where((l) => l.trim().isNotEmpty).toList()}, timeout: const Duration(minutes: 4)));
  }

  Future<void> _github() async {
    final t = await _ask(context, 'GitHub fine-grained token',
        hint: 'Sirf is repo par Contents: read, Pull requests: read (publish ke liye write)', obscure: true);
    if (t == null) return;
    await _run(() => widget.app.api!.call('PUT', '/api/docwriter/github', body: {'token': t}));
  }

  Widget _docTile(Map<String, dynamic> d) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        child: InkWell(
          onTap: () => _open(_s(d['id'])),
          child: Row(children: [
            const Icon(Icons.menu_book_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${d['number']} · ${d['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${d['kind_label']} · ${d['lang']} · v${d['version']} · ${d['status']}'
                    '${(d['stale'] ?? 0) > 0 ? ' · ${d['stale']} purane hisse' : ''}',
                    style: const TextStyle(fontSize: 12, color: C.muted)),
              ]),
            ),
            if (_s(d['status']) == 'published') const Icon(Icons.public, color: C.ok, size: 18),
            if (_s(d['status']) == 'stale' || (d['stale'] ?? 0) > 0) const Icon(Icons.update, color: C.warn, size: 18),
          ]),
        ),
      );

  Widget _today() {
    final d = _d ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      if (_list(d['waiting']).isNotEmpty) const Text('Aapki haan ka intezaar', style: TextStyle(fontWeight: FontWeight.w800)),
      for (final x in _list(d['waiting'])) _docTile(x),
      if (_list(d['stale']).isNotEmpty) const Text('Product badla: docs update chahiye', style: TextStyle(fontWeight: FontWeight.w800)),
      for (final x in _list(d['stale'])) _docTile(x),
      const SizedBox(height: 10),
      FilledButton.icon(onPressed: _busy ? null : _newDoc, icon: const Icon(Icons.add), label: const Text('Naya doc')),
    ]);
  }

  Widget _docs() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final x in _list(_d?['docs'])) _docTile(x),
        if (_list(_d?['docs']).isEmpty) const Text('Abhi koi doc nahi.', style: TextStyle(color: C.muted)),
      ]);

  Widget _sourcesTab() {
    final gh = _map(_map(_d?['settings'])['github']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      for (final p in _list(_d?['products']))
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(p['verified'] == true ? Icons.verified_rounded : Icons.help_outline, color: p['verified'] == true ? C.ok : C.warn),
              const SizedBox(width: 8),
              Expanded(child: Text('${p['name']} · ${p['kind']}', style: const TextStyle(fontWeight: FontWeight.w700))),
              Text('${p['version']} · ${p['parts']} hisse', style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
            if (p['verified'] != true) ...[
              const SizedBox(height: 6),
              Text(_s(_map(p['verify'])['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
              for (final k in ['meta', 'file', 'dns'])
                InkWell(
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: _s(_map(p['verify'])[k])));
                    _snack(context, 'Copy ho gaya');
                  },
                  child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Text(_s(_map(p['verify'])[k]), style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace'))),
                ),
            ],
            Wrap(spacing: 6, children: [
              if (p['verified'] != true)
                TextButton(
                    onPressed: () => _run(() => widget.app.api!.call('POST', '/api/docwriter/products/${p['id']}/verify')),
                    child: const Text('Jaancho')),
              if (p['verified'] == true)
                TextButton(
                    onPressed: () => _run(() => widget.app.api!
                        .call('POST', '/api/docwriter/products/${p['id']}/sync', body: {}, timeout: const Duration(minutes: 8))),
                    child: const Text('Sync karo')),
              if (p['verified'] == true && _s(p['kind']) == 'web')
                TextButton(onPressed: () => _recordFlow(p), child: const Text('Steps + screenshot')),
            ]),
          ]),
        ),
      FilledButton.icon(onPressed: _busy ? null : _addSource, icon: const Icon(Icons.add_link), label: const Text('Product jodo')),
      const SizedBox(height: 12),
      Glass(
        child: Row(children: [
          const Icon(Icons.code_rounded),
          const SizedBox(width: 8),
          Expanded(child: Text(gh['joined'] == true ? 'GitHub juda: ${gh['label']} (sirf padhna)' : 'GitHub token nahi juda')),
          TextButton(onPressed: _github, child: Text(gh['joined'] == true ? 'Badlo' : 'Jodo')),
          if (gh['joined'] == true)
            TextButton(onPressed: () => _run(() => widget.app.api!.call('DELETE', '/api/docwriter/github')), child: const Text('Hatao')),
        ]),
      ),
    ]);
  }

  Widget _rules() {
    final st = _map(_d?['settings']);
    Future<void> edit(String key, String title, {bool list = false}) async {
      final cur = st[key];
      final v = await _ask(context, title, lines: list, initial: list ? (cur is List ? cur.join('\n') : '') : _s(cur));
      if (v == null) return;
      await _run(() => widget.app.api!.call('PUT', '/api/docwriter/settings', body: {key: list ? v.split('\n') : v}));
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      ListTile(title: const Text('Product ka naam'), subtitle: Text(_s(st['product_name'])), onTap: () => edit('product_name', 'Product ka naam')),
      ListTile(title: const Text('Kaun padhega'), subtitle: Text(_s(st['audience'])), onTap: () => edit('audience', 'Kaun padhega')),
      ListTile(title: const Text('Lehja'), subtitle: Text(_s(st['tone'])), onTap: () => edit('tone', 'Lehja')),
      ListTile(
          title: const Text('Support contact (docs mein dikhega)'),
          subtitle: Text(_s(st['contact'])),
          onTap: () => edit('contact', 'Support contact')),
      ListTile(
          title: const Text('Kabhi translate na ho'),
          subtitle: Text(((st['keep'] as List?) ?? const []).join(', ')),
          onTap: () => edit('keep', 'Ek line mein ek shabd', list: true)),
      ListTile(
          title: const Text('Mere niyam'),
          subtitle: Text(((st['rules'] as List?) ?? const []).join(' · ')),
          onTap: () => edit('rules', 'Ek line mein ek niyam', list: true)),
      const Padding(padding: EdgeInsets.fromLTRB(16, 8, 16, 4), child: Text('Shabdavali', style: TextStyle(fontWeight: FontWeight.w800))),
      for (final g in _list(st['glossary']))
        ListTile(dense: true, title: Text(_s(g['term'])), subtitle: Text(_s(g['avoid']).isEmpty ? _s(g['note']) : "na ki '${g['avoid']}'")),
      TextButton.icon(
          onPressed: () async {
            final t = await _ask(context, 'Sahi shabd', hint: 'order');
            if (t == null || !mounted) return;
            final a = await _ask(context, 'Iski jagah na likhein (zaroori nahi)', hint: 'booking');
            final g = [..._list(st['glossary']), {'term': t, 'avoid': a ?? ''}];
            await _run(() => widget.app.api!.call('PUT', '/api/docwriter/settings', body: {'glossary': g}));
          },
          icon: const Icon(Icons.add),
          label: const Text('Shabd jodo')),
      const SizedBox(height: 8),
      for (final n in ((_d?['never'] as List?) ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Docs', 'Sources', 'Niyam'];
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Docs sahayak'), actions: [
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
      ]),
      floatingActionButton: FloatingActionButton.extended(onPressed: _busy ? null : _newDoc, icon: const Icon(Icons.edit_note), label: const Text('Naya doc')),
      body: _d == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(14, 6, 14, 90), children: [
                Wrap(spacing: 6, children: [
                  for (var i = 0; i < tabs.length; i++)
                    ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
                ]),
                if (_busy) const LinearProgressIndicator(),
                const SizedBox(height: 10),
                [_today(), _docs(), _sourcesTab(), _rules()][_tab],
              ]),
            ),
    );
  }
}

class DocwriterDocPage extends StatefulWidget {
  const DocwriterDocPage({super.key, required this.app, required this.docId});
  final Santosh app;
  final String docId;
  @override
  State<DocwriterDocPage> createState() => _DocwriterDocPageState();
}

class _DocwriterDocPageState extends State<DocwriterDocPage> {
  Map<String, dynamic>? _d;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.call('GET', '/api/docwriter/docs/${widget.docId}');
      if (mounted) setState(() => _d = _map(d));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(String method, String path, {Object? body, Duration timeout = const Duration(minutes: 3)}) async {
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call(method, path, body: body, timeout: timeout));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String get _base => '/api/docwriter/docs/${widget.docId}';

  Future<void> _publish() async {
    final dest = await _pick(context, 'Kahan public karein?', const [
      ('page', 'Hoola docs page (public link)'),
      ('github', 'GitHub repo mein pull request'),
      ('wordpress', 'Meri WordPress site'),
    ]);
    if (dest == null) return;
    String? repo;
    if (dest == 'github' && mounted) repo = await _ask(context, 'Repo (khaali = jo juda hai)', hint: 'owner/repo');
    await _run('POST', '$_base/publish', body: {'dest': dest, if (repo != null) 'repo': repo});
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final checks = _map(d?['check_list']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(d?['number']).isEmpty ? 'Doc' : '${d?['number']}'), actions: [
        PopupMenuButton<String>(
          onSelected: (v) async {
            if (v == 'check') await _run('POST', '$_base/check');
            if (v == 'files') await _run('POST', '$_base/files', body: {'formats': ['md', 'docx', 'pdf']});
            if (v == 'translate') {
              final to = await _pick(context, 'Kis bhasha mein?', _langs);
              if (to != null) await _run('POST', '$_base/translate', body: {'to': to}, timeout: const Duration(minutes: 6));
            }
            if (v == 'revise' && mounted) {
              final t = await _ask(context, 'Kya badlein?', hint: 'Jaise: aur aasaan shabd, har step chhota', lines: true);
              if (t != null) await _run('POST', '$_base/revise', body: {'instruction': t}, timeout: const Duration(minutes: 5));
            }
            if (v == 'unpage') await _run('POST', '$_base/unpage');
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'check', child: Text('Jaancho')),
            PopupMenuItem(value: 'revise', child: Text('Badlav bolo')),
            PopupMenuItem(value: 'translate', child: Text('Anuvaad')),
            PopupMenuItem(value: 'files', child: Text('Word + PDF + Markdown')),
            PopupMenuItem(value: 'unpage', child: Text('Docs page hatao')),
          ],
        ),
      ]),
      bottomNavigationBar: d == null
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: FilledButton.icon(
                    onPressed: _busy || ((checks['blocking'] as List?) ?? const []).isNotEmpty ? null : _publish,
                    icon: const Icon(Icons.public),
                    label: Text(((checks['blocking'] as List?) ?? const []).isNotEmpty ? 'Pehle rukawat theek kijiye' : 'Publish (aapki haan se)')),
              ),
            ),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.fromLTRB(14, 6, 14, 30), children: [
              if (_busy) const LinearProgressIndicator(),
              Text(_s(d['title']), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
              Text('${d['kind_label']} · ${d['lang']} · v${d['version']} · ${d['status']}', style: const TextStyle(color: C.muted)),
              if (_s(d['page']).isNotEmpty)
                InkWell(
                    onTap: () => Clipboard.setData(ClipboardData(text: _s(d['page']))).then((_) => _snack(context, 'Link copy')),
                    child: Text(_s(d['page']), style: const TextStyle(color: C.accent, fontSize: 12.5))),
              for (final c in _list(checks['blocking']))
                Text('⛔ ${c['text']}', style: const TextStyle(color: C.bad, fontSize: 12.5)),
              for (final c in _list(checks['warnings']).take(8))
                Text('• ${c['text']}', style: const TextStyle(color: C.warn, fontSize: 12)),
              const SizedBox(height: 10),
              for (final sec in _list(d['section_list']))
                Glass(
                  margin: const EdgeInsets.only(bottom: 10),
                  border: sec['stale'] == true ? C.warn : null,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text(_s(sec['title']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
                      if (sec['edited'] == true) const Chip(label: Text('aapka likha'), visualDensity: VisualDensity.compact),
                      IconButton(
                          icon: const Icon(Icons.edit_outlined, size: 18),
                          onPressed: () async {
                            final t = await _ask(context, 'Khud likhiye', lines: true, initial: _s(sec['body']));
                            if (t != null) await _run('PUT', '$_base/sections/${sec['id']}', body: {'body': t});
                          }),
                    ]),
                    if (sec['stale'] == true) Text('Purana: ${sec['why']}', style: const TextStyle(color: C.warn, fontSize: 12)),
                    for (final sh in _list(sec['shots']))
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Semantics(label: _s(sh['alt']), child: _img(widget.app, _s(sh['url']), height: 320)),
                      ),
                    SelectableText(_s(sec['body']), style: const TextStyle(fontSize: 13.5, height: 1.45)),
                  ]),
                ),
            ]),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
class DocwriterDocCard extends StatelessWidget {
  const DocwriterDocCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final d = _map(data['doc']);
    final ch = _map(d['checks']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.menu_book_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${d['number']} · ${d['title']}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 4),
        Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
        Text('${d['kind_label']} · ${d['lang']} · v${d['version']} · ${d['sections']} hisse · ${ch['blocking'] ?? 0} rukawat',
            style: const TextStyle(fontSize: 12, color: C.muted)),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DocwriterDocPage(app: app, docId: _s(d['id'])))),
              child: const Text('Kholo')),
        ),
      ]),
    );
  }
}

class DocwriterPublishCard extends StatefulWidget {
  const DocwriterPublishCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<DocwriterPublishCard> createState() => _DocwriterPublishCardState();
}

class _DocwriterPublishCardState extends State<DocwriterPublishCard> {
  String _done = '';
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    final d = _map(widget.data['doc']);
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call('POST', '/api/docwriter/docs/${d['id']}/decide',
          body: {'yes': yes, 'hash': widget.data['hash']}, timeout: const Duration(minutes: 3)));
      setState(() => _done = _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _map(widget.data['doc']);
    return Glass(
      border: C.accent,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Docs public karein? Aapki haan chahiye', style: TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        Text('${d['number']} · ${d['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
        Text('Kahan: ${widget.data['where']}', style: const TextStyle(fontSize: 12.5)),
        for (final w in ((widget.data['warnings'] as List?) ?? const []).take(4)) Text('• $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 6),
        Text(_s(widget.data['preview']), maxLines: 8, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (_done.isNotEmpty)
          Text(_done, style: const TextStyle(color: C.ok, fontWeight: FontWeight.w700))
        else
          Row(children: [
            Expanded(child: FilledButton(onPressed: _busy ? null : () => _decide(true), child: const Text('Haan, public karo'))),
            const SizedBox(width: 8),
            OutlinedButton(onPressed: _busy ? null : () => _decide(false), child: const Text('Nahi')),
          ]),
      ]),
    );
  }
}

class DocwriterSyncCard extends StatelessWidget {
  const DocwriterSyncCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.sync_rounded, color: C.teal),
            const SizedBox(width: 8),
            Expanded(child: Text('Docs sync: ${_map(data['product'])['name']}', style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          const SizedBox(height: 4),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
          for (final r in _list(data['docs']))
            TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DocwriterDocPage(app: app, docId: _s(r['doc'])))),
                child: Text('${r['number']}: ${r['updated']} update · ${((r['stale'] as List?) ?? const []).length} badle')),
        ]),
      );
}

class DocwriterShotsCard extends StatelessWidget {
  const DocwriterShotsCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final imgs = ((data['images'] as List?) ?? const []).map((e) => '$e').toList();
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.photo_library_outlined, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(_map(data['flow'])['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
        const SizedBox(height: 6),
        SizedBox(
          height: 180,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: imgs.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (_, i) => _img(app, imgs[i], height: 180),
          ),
        ),
      ]),
    );
  }
}
