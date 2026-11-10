/// Profile > Research assistant (Shiksha suite Phase 4, Shodh Sahayak): research projects; papers found ONLY through
/// official open APIs (OpenAlex, Crossref, arXiv, PubMed, Semantic Scholar), include / exclude, the review matrix,
/// research gaps, references (APA / IEEE / Harvard, BibTeX, RIS). Analysis and drafts run from the chat.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _note = 'Every paper comes from an official scholarly API; DOIs are checked with Crossref. References are built by code. Drafts are AI-assisted: '
    'read and edit them, and disclose as your university requires.';

class ShodhScreen extends StatefulWidget {
  const ShodhScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ShodhScreen> createState() => _ShodhScreenState();
}

class _ShodhScreenState extends State<ShodhScreen> {
  List<Map<String, dynamic>>? _projects;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _map(await widget.app.api!.call('GET', '/api/shodh'));
      if (mounted) setState(() => _projects = _list(d['projects']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _new() async {
    final t = TextEditingController();
    final q = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('New research project'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: t, decoration: const InputDecoration(labelText: 'Topic')),
          TextField(controller: q, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Research question')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Make')),
        ],
      ),
    );
    if (ok != true || t.text.trim().isEmpty) return;
    try {
      await widget.app.api!.call('POST', '/api/shodh/projects', body: {'title': t.text.trim(), 'question': q.text.trim()});
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Research assistant')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              GradientButton(label: 'New project', icon: Icons.add_rounded, height: 46, onTap: _new),
              const SizedBox(height: 10),
              if (_projects == null) const Center(child: CircularProgressIndicator()),
              for (final p in _projects ?? const <Map<String, dynamic>>[])
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Press(
                    onTap: () async {
                      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShodhProjectPage(app: widget.app, project: p)));
                      _load();
                    },
                    child: Glass(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${_s(p['number'])} · ${_s(p['title'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                        if (_s(p['question']).isNotEmpty) Text(_s(p['question']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C.muted)),
                        Text('Papers: ${_map(p['papers']).entries.map((e) => '${e.key} ${e.value}').join(', ')}', style: const TextStyle(fontSize: 12)),
                      ]),
                    ),
                  ),
                ),
              const SizedBox(height: 14),
              const Text(_note, style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

class ShodhProjectPage extends StatefulWidget {
  const ShodhProjectPage({super.key, required this.app, required this.project});
  final Santosh app;
  final Map<String, dynamic> project;
  @override
  State<ShodhProjectPage> createState() => _ShodhProjectPageState();
}

class _ShodhProjectPageState extends State<ShodhProjectPage> {
  int _tab = 0;
  bool _busy = false;
  List<Map<String, dynamic>> _papers = const [];
  List<Map<String, dynamic>> _matrix = const [];
  List<Map<String, dynamic>> _gaps = const [];
  final _q = TextEditingController();
  final Set<String> _sources = {'openalex', 'crossref', 'arxiv'};

  String get _ref => _s(widget.project['number']);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>?> _call(String m, String path, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call(m, path, body: body, timeout: const Duration(minutes: 3)));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e'.replaceFirst('Exception: ', ''));
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _load() async {
    final r = await _call('GET', '/api/shodh/projects/$_ref/papers');
    final m = await _call('GET', '/api/shodh/projects/$_ref/matrix');
    if (mounted) setState(() {
      _papers = _list(r?['papers']);
      _matrix = _list(m?['rows']);
    });
  }

  Widget _searchTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        TextField(controller: _q, decoration: const InputDecoration(labelText: 'Keywords (jaise: spaced repetition mathematics India)')),
        const SizedBox(height: 6),
        Wrap(spacing: 6, children: [
          for (final s in const ['openalex', 'crossref', 'arxiv', 'pubmed', 'semantic_scholar'])
            FilterChip(label: Text(s), selected: _sources.contains(s), onSelected: (v) => setState(() => v ? _sources.add(s) : _sources.remove(s))),
        ]),
        const SizedBox(height: 8),
        GradientButton(
            label: 'Search papers',
            icon: Icons.search_rounded,
            height: 44,
            onTap: _busy
                ? null
                : () async {
                    await _call('POST', '/api/shodh/projects/$_ref/search', {'query': _q.text.trim(), 'sources': _sources.toList()});
                    await _load();
                  }),
        const SizedBox(height: 10),
        for (final p in _papers)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${_s(p['number'])} · ${_s(p['title'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
                  Pill(_s(p['status']).toUpperCase(), fg: _s(p['status']) == 'included' ? C.ok : (_s(p['status']) == 'excluded' ? C.muted : C.warn)),
                ]),
                Text('${(p['authors'] as List? ?? const []).take(3).join(', ')} · ${_s(p['year'])} · ${_s(p['venue'])}',
                    style: const TextStyle(fontSize: 12, color: C.muted)),
                Wrap(spacing: 4, children: [
                  TextButton(onPressed: () => _screen(_s(p['number']), true), child: const Text('Include')),
                  TextButton(onPressed: () => _screen(_s(p['number']), false), child: const Text('Exclude')),
                  if (_s(p['oa_url']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(p['oa_url'])), child: const Text('Free PDF')),
                  if (_s(p['doi']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: 'https://doi.org/${_s(p['doi'])}'), child: const Text('DOI')),
                ]),
              ]),
            ),
          ),
      ]);

  Future<void> _screen(String ref, bool inc) async {
    await _call('POST', '/api/shodh/projects/$_ref/screen', {'refs': [ref], 'include': inc});
    await _load();
  }

  Widget _matrixTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
              child: GlassButton(
                  label: 'Write a summary (from the abstract)',
                  onTap: _busy
                      ? null
                      : () async {
                          await _call('POST', '/api/shodh/projects/$_ref/summarize', {'refs': _matrix.map((r) => r['number']).toList()});
                          await _load();
                        })),
          const SizedBox(width: 8),
          GlassButton(
              label: 'Research gaps',
              onTap: _busy
                  ? null
                  : () async {
                      final r = await _call('POST', '/api/shodh/projects/$_ref/gaps');
                      if (r != null && mounted) setState(() => _gaps = _list(r['gaps']));
                    }),
        ]),
        const SizedBox(height: 8),
        for (final g in _gaps)
          Glass(child: Text('${_s(g['gap'])} (${(g['papers'] as List? ?? const []).join(', ')})', style: const TextStyle(fontSize: 13))),
        for (final r in _matrix)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(r['number'])} · ${_s(r['cite'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
                Text(_s(r['title']), style: const TextStyle(fontSize: 12.5)),
                for (final k in const ['method', 'data', 'findings', 'limitations'])
                  if (_s(r[k]).isNotEmpty) Text('$k: ${_s(r[k])}', style: const TextStyle(fontSize: 12, color: C.muted)),
              ]),
            ),
          ),
      ]);

  Widget _refsTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('The included papers list as a file (BibTeX or RIS imports into Zotero / Mendeley).', style: TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final (style, fmt, label) in const [('apa', 'text', 'APA'), ('ieee', 'text', 'IEEE'), ('harvard', 'text', 'Harvard'), ('', 'bibtex', 'BibTeX'), ('', 'ris', 'RIS')])
            GlassButton(label: label, onTap: _busy ? null : () => _call('POST', '/api/shodh/projects/$_ref/references', {'style': style, 'format': fmt})),
        ]),
      ]);

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: Text('$_ref · ${_s(widget.project['title'])}')),
        body: Aurora(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            Wrap(spacing: 6, children: [
              for (final (i, t) in const [(0, 'Papers'), (1, 'Matrix'), (2, 'References')])
                ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
            ]),
            const SizedBox(height: 10),
            if (_busy) const LinearProgressIndicator(),
            [_searchTab(), _matrixTab(), _refsTab()][_tab],
            const SizedBox(height: 14),
            const Text(_note, style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      );
}
