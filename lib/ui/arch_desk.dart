/// v0.410 ARCHITECTURE DESK: the desk of a hired Principal Software Architect (Employees > Open desk).
/// She describes the system (+ her GitHub repo, optional, + users a day); Hoola writes the design on the server:
/// decisions (ADRs), diagrams, capacity worked out in code, risks, a PDF. She approves or asks for the next version,
/// and once approved her pull requests are checked against it (posted on the PR only by her tap). /api/arch/*.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';
import 'md_text.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

const _busyStates = ['reading', 'designing', 'drawing'];
const _stateLabel = {
  'reading': 'Repo padh raha hai',
  'designing': 'Design likh raha hai',
  'drawing': 'Diagrams bana raha hai',
  'waiting_her': 'Aapki haan chahiye',
  'approved': 'Approved',
  'failed': 'Nahi ban saka',
  'cancelled': 'Roka gaya',
};

class ArchDeskScreen extends StatefulWidget {
  const ArchDeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ArchDeskScreen> createState() => _ArchDeskScreenState();
}

class _ArchDeskScreenState extends State<ArchDeskScreen> {
  final _brief = TextEditingController();
  final _repo = TextEditingController();
  final _dau = TextEditingController();
  List<Map<String, dynamic>> _ps = [];
  bool _loaded = false;
  bool _busy = false;
  String _err = '';
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _brief.dispose();
    _repo.dispose();
    _dau.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    _poll?.cancel();
    try {
      final d = await widget.app.api!.archProjects();
      if (!mounted) return;
      setState(() {
        _ps = _list(d['projects']);
        _loaded = true;
        _err = '';
      });
      if (_ps.any((p) => _busyStates.contains(p['status']))) _poll = Timer(const Duration(seconds: 6), _load);
    } catch (e) {
      if (mounted) setState(() {
        _err = '$e';
        _loaded = true;
      });
    }
  }

  Future<void> _start() async {
    final brief = _brief.text.trim();
    if (brief.isEmpty) return;
    setState(() => _busy = true);
    try {
      final dau = int.tryParse(_dau.text.replaceAll(RegExp(r'[, ]'), ''));
      final p = await widget.app.api!.archStart(brief, repo: _repo.text.trim(), dau: dau);
      _brief.clear();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Design ban raha hai - kuch minute lagenge.')));
        await _open(_s(p['id']));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Future<void> _open(String id) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArchDesignScreen(app: widget.app, id: id)));
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Architecture Desk')),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                if (_err.isNotEmpty) Text(_err, style: const TextStyle(color: C.bad)),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Naya system design', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                    const SizedBox(height: 4),
                    const Text('System kya karega, kaun use karega, roz kitne log. Repo ho to owner/naam likhiye - pehle use padhega.',
                        style: TextStyle(color: C.faint, fontSize: 12)),
                    const SizedBox(height: 8),
                    TextField(controller: _brief, minLines: 3, maxLines: 8, maxLength: 6000,
                        decoration: const InputDecoration(hintText: 'e.g. 3 shehron ke liye food delivery backend...', border: OutlineInputBorder())),
                    TextField(controller: _repo, decoration: const InputDecoration(labelText: 'GitHub repo (optional) owner/naam')),
                    TextField(controller: _dau, keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Roz kitne log (users a day)')),
                    const SizedBox(height: 10),
                    FilledButton.icon(
                      onPressed: _busy ? null : _start,
                      icon: const Icon(Icons.architecture_rounded, size: 18),
                      label: Text(_busy ? 'Shuru ho raha hai...' : 'Design banao'),
                    ),
                  ]),
                ),
                const SizedBox(height: 14),
                if (_ps.isEmpty) const Text('Abhi koi design nahi.', style: TextStyle(color: C.muted)),
                for (final p in _ps)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Glass(
                      child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(_s(p['title']), style: const TextStyle(fontWeight: FontWeight.w700)),
                        subtitle: Text('${_stateLabel[p['status']] ?? _s(p['status'])}'
                            '${(p['version'] ?? 0) != 0 ? ' · v${p['version']}' : ''}'
                            '${_s(p['repo']).isNotEmpty ? ' · ${p['repo']}' : ''}'),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () => _open(_s(p['id'])),
                      ),
                    ),
                  ),
              ]),
            ),
    );
  }
}

/// One design: summary, diagrams, capacity sheet, ADRs, risks, approve / next version, PR checks.
class ArchDesignScreen extends StatefulWidget {
  const ArchDesignScreen({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<ArchDesignScreen> createState() => _ArchDesignScreenState();
}

class _ArchDesignScreenState extends State<ArchDesignScreen> {
  final _words = TextEditingController();
  final _pr = TextEditingController();
  Map<String, dynamic> _p = {};
  bool _busy = false;
  String _err = '';
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _words.dispose();
    _pr.dispose();
    super.dispose();
  }

  String _url(String path) => widget.app.api!.absolute(path);

  Future<void> _load() async {
    _poll?.cancel();
    try {
      final p = await widget.app.api!.archGet(widget.id);
      if (!mounted) return;
      setState(() {
        _p = p;
        _err = '';
      });
      if (_busyStates.contains(p['status'])) _poll = Timer(const Duration(seconds: 6), _load);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _do(Future<dynamic> Function() call, String ok) async {
    setState(() => _busy = true);
    try {
      await call();
      if (mounted && ok.isNotEmpty) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Widget _section(String title, List<Widget> kids) => Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 6),
            ...kids,
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final api = widget.app.api!;
    final d = Map<String, dynamic>.from((_p['design'] as Map?) ?? const {});
    final cap = Map<String, dynamic>.from((_p['capacity'] as Map?) ?? const {});
    final status = _s(_p['status']);
    final busy = _busyStates.contains(status);
    const body = TextStyle(fontSize: 13.5, height: 1.4, color: C.chip);
    return Scaffold(
      appBar: AppBar(title: Text(_s(_p['title']).isEmpty ? 'Design' : _s(_p['title']))),
      body: _p.isEmpty && _err.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                if (_err.isNotEmpty) Text(_err, style: const TextStyle(color: C.bad)),
                Text('${_stateLabel[status] ?? status}${(_p['version'] ?? 0) != 0 ? ' · v${_p['version']}' : ''}'
                    '${busy && _s(_p['stage']).isNotEmpty ? ' · ${_p['stage']}' : ''}',
                    style: const TextStyle(color: C.muted, fontSize: 12)),
                if (_s(_p['error']).isNotEmpty) Text(_s(_p['error']), style: const TextStyle(color: C.bad)),
                Wrap(spacing: 8, runSpacing: 4, children: [
                  if (status == 'waiting_her')
                    FilledButton(
                      onPressed: _busy ? null : () => _do(() => api.archApprove(widget.id), 'Approve ho gaya.'),
                      child: const Text('Approve design'),
                    ),
                  if (_s(_p['pdf']).isNotEmpty)
                    OutlinedButton(
                      onPressed: () => launchUrl(Uri.parse(_url(_s(_p['pdf']))), mode: LaunchMode.externalApplication),
                      child: const Text('PDF'),
                    ),
                ]),
                if (d['summary'] != null) _section('Saar', [MdText(_s(d['summary']), style: body)]),
                if (_list(_p['diagrams']).isNotEmpty)
                  _section('Diagrams', [
                    for (final g in _list(_p['diagrams']))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(_s(g['name']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                          const SizedBox(height: 4),
                          if (g['ok'] == true && _s(g['png']).isNotEmpty)
                            InteractiveViewer(
                              maxScale: 5,
                              child: Container(color: Colors.white, child: Image.network(_url(_s(g['png'])), fit: BoxFit.contain)),
                            )
                          else
                            Text('Diagram nahi ban saka: ${_s(g['error'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
                        ]),
                      ),
                  ]),
                if (cap['rows'] != null || cap['error'] != null)
                  _section('Capacity (code se hisaab)', [
                    if (cap['error'] != null) Text(_s(cap['error']), style: body),
                    for (final r in _list(cap['rows']))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text('${r['what']}: ${r['value']}', style: body),
                      ),
                    if ((cap['assumed'] as List?)?.isNotEmpty ?? false)
                      Text('Andaaza (pakka kijiye): ${(cap['assumed'] as List).join(', ')}',
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                if (_list(d['adrs']).isNotEmpty)
                  _section('Faisle (ADRs)', [
                    for (final a in _list(d['adrs']))
                      ExpansionTile(
                        tilePadding: EdgeInsets.zero,
                        title: Text('${_s(a['id'])}: ${_s(a['title'])}', style: const TextStyle(fontSize: 13.5)),
                        children: [
                          Text('Decision: ${_s(a['decision'])}', style: body),
                          const SizedBox(height: 4),
                          Text('Consequences: ${_s(a['consequences'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
                          const SizedBox(height: 8),
                        ],
                      ),
                  ]),
                if (_list(d['risks']).isNotEmpty)
                  _section('Risks', [
                    for (final r in _list(d['risks']))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text('• ${_s(r['risk'])} (${_s(r['likelihood'])}/${_s(r['impact'])}) → ${_s(r['mitigation'])}', style: body),
                      ),
                  ]),
                if (!busy && (_p['version'] ?? 0) != 0)
                  _section('Badlav', [
                    TextField(controller: _words, maxLength: 2000, minLines: 1, maxLines: 4,
                        decoration: const InputDecoration(hintText: 'e.g. MongoDB nahi, Postgres; 10 guna users ke liye')),
                    OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () {
                              final w = _words.text.trim();
                              if (w.isEmpty) return;
                              _words.clear();
                              _do(() => api.archChange(widget.id, w), 'Agla version ban raha hai.');
                            },
                      child: const Text('Agla version'),
                    ),
                  ]),
                if (status == 'approved' && _s(_p['repo']).isNotEmpty)
                  _section('Pull requests', [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _p['watch_prs'] == true,
                      title: const Text('Naye PR khud dekhe (sirf draft notes)', style: TextStyle(fontSize: 13.5)),
                      onChanged: (v) => _do(() => api.archWatch(widget.id, v), ''),
                    ),
                    Row(children: [
                      Expanded(child: TextField(controller: _pr, keyboardType: TextInputType.number,
                          decoration: const InputDecoration(hintText: 'PR number'))),
                      TextButton(
                        onPressed: _busy
                            ? null
                            : () {
                                final n = int.tryParse(_pr.text.trim());
                                if (n == null) return;
                                _do(() => api.archReview(widget.id, n), 'PR dekh liya - notes draft hain.');
                              },
                        child: const Text('Is PR ko dekho'),
                      ),
                    ]),
                  ]),
                for (final r in _list(_p['reviews']))
                  _section('PR #${r['pr']} · ${_s(r['verdict'])}', [
                    Text(_s(r['title']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                    MdText(_s(r['summary']), style: body),
                    for (final f in _list(r['findings']))
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text('${_s(f['severity'])} · ${_s(f['area'])}: ${_s(f['finding'])}\n→ ${_s(f['fix'])}', style: body),
                      ),
                    if (r['status'] == 'draft')
                      Wrap(spacing: 8, children: [
                        FilledButton(
                          onPressed: _busy ? null : () => _do(() => api.archPostReview(_s(r['id'])), 'PR par post ho gaya.'),
                          child: const Text('PR par post karo'),
                        ),
                        TextButton(
                          onPressed: _busy ? null : () => _do(() => api.archDiscardReview(_s(r['id'])), ''),
                          child: const Text('Hatao'),
                        ),
                      ])
                    else
                      Text(_s(r['status']), style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
              ]),
            ),
    );
  }
}
