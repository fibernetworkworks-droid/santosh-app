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

Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<String> _strs(dynamic l) {
  if (l is String) return l.isEmpty ? <String>[] : <String>[l];
  if (l is! List) return <String>[];
  return [for (final e in l) e is Map ? _s(e['name'] ?? e['what'] ?? e) : _s(e)];
}
String _bytes(dynamic v) {
  final n0 = v is num ? v.toDouble() : double.tryParse(_s(v));
  if (n0 == null || n0 < 0) return '-';
  const u = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  var n = n0;
  var i = 0;
  while (n >= 1024 && i < u.length - 1) {
    n = n / 1024;
    i++;
  }
  return '${n >= 100 || i == 0 ? n.round() : n.toStringAsFixed(1)} ${u[i]}';
}

// v0.426 MASTER ARCHITECT: the six kinds of job; assess / migrate read her repo first, so they need one
const _kinds = {
  'design': 'New design',
  'assess': 'Assess',
  'migrate': 'Migration',
  'decide': 'Decide',
  'threat': 'Threat model',
  'scale': 'Scale',
};
const _needsRepo = ['assess', 'migrate'];

const _busyStates = ['reading', 'designing', 'drawing'];
const _stateLabel = {
  'reading': 'Reading the repo',
  'designing': 'Writing the design',
  'drawing': 'Making diagrams',
  'waiting_her': 'Needs your OK',
  'approved': 'Approved',
  'failed': 'Could not be made',
  'cancelled': 'Stopped',
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
  String _kind = 'design';
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
    if (_needsRepo.contains(_kind) && _repo.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('This task needs a GitHub repo (owner/name) - it will read the code first.')));
      return;
    }
    setState(() => _busy = true);
    try {
      final dau = int.tryParse(_dau.text.replaceAll(RegExp(r'[, ]'), ''));
      final p = await widget.app.api!.archStart(brief, repo: _repo.text.trim(), dau: dau, kind: _kind);
      _brief.clear();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('The design is being made - it will take a few minutes.')));
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
                    const Text('New system design', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                    const SizedBox(height: 4),
                    const Text('What the system will do, who will use it, how many people a day. If you have a repo, write owner/name - it will be read first.',
                        style: TextStyle(color: C.faint, fontSize: 12)),
                    const SizedBox(height: 8),
                    Wrap(spacing: 6, runSpacing: 4, children: [
                      for (final k in _kinds.entries)
                        ChoiceChip(
                          label: Text(k.value, style: const TextStyle(fontSize: 12.5)),
                          selected: _kind == k.key,
                          onSelected: (_) => setState(() => _kind = k.key),
                        ),
                    ]),
                    if (_needsRepo.contains(_kind))
                      const Padding(
                        padding: EdgeInsets.only(top: 4),
                        child: Text('This task reads your code first - a GitHub repo is required.',
                            style: TextStyle(color: C.warn, fontSize: 12)),
                      ),
                    const SizedBox(height: 8),
                    TextField(controller: _brief, minLines: 3, maxLines: 8, maxLength: 6000,
                        decoration: const InputDecoration(hintText: 'e.g. a food delivery backend for 3 cities...', border: OutlineInputBorder())),
                    TextField(controller: _repo, decoration: const InputDecoration(labelText: 'GitHub repo (optional) owner/name')),
                    TextField(controller: _dau, keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'How many people a day (users a day)')),
                    const SizedBox(height: 10),
                    FilledButton.icon(
                      onPressed: _busy ? null : _start,
                      icon: const Icon(Icons.architecture_rounded, size: 18),
                      label: Text(_busy ? 'Starting...' : 'Make design'),
                    ),
                  ]),
                ),
                const SizedBox(height: 14),
                if (_ps.isEmpty) const Text('No designs yet.', style: TextStyle(color: C.muted)),
                for (final p in _ps)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Glass(
                      child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(_s(p['title']), style: const TextStyle(fontWeight: FontWeight.w700)),
                        subtitle: Text('${_s(p['kind_title']).isNotEmpty ? '${_s(p['kind_title'])}\n' : ''}'
                            '${_stateLabel[p['status']] ?? _s(p['status'])}'
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

  Widget _line(String t, TextStyle st) => Padding(padding: const EdgeInsets.only(bottom: 4), child: Text(t, style: st));

  Color _sevColor(dynamic s) {
    final k = _s(s).toLowerCase();
    if (k == 'high' || k == 'critical' || k == 'blocker') return C.bad;
    if (k == 'medium') return C.warn;
    return C.muted;
  }

  /// v0.426 MASTER ARCHITECT: the kind's own section, then growth scenarios, boundary rules, module map,
  /// peer review, design checks, API contract. Every key may be missing - only what the server sent is drawn.
  List<Widget> _master(TextStyle body) {
    final x = _m(_p['extra']);
    const small = TextStyle(color: C.muted, fontSize: 12);
    final out = <Widget>[];

    // assessment
    if (x['assessment'] is Map) {
      final a = _m(x['assessment']);
      final sr = _m(x['scorecard_result']);
      out.add(_section('Assessment', [
        if (_s(a['as_is']).isNotEmpty) MdText(_s(a['as_is']), style: body),
        if (sr['average'] != null)
          _line('Score ${_s(sr['average'])}${sr['out_of'] != null ? ' / ${_s(sr['out_of'])}' : ''}'
              '${_strs(sr['weakest']).isNotEmpty ? ' · weakest: ${_strs(sr['weakest']).join(', ')}' : ''}',
              const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
        for (final r in _list(a['scorecard'])) _line('${_s(r['dimension'])}: ${_s(r['score'])} - ${_s(r['why'])}', body),
        if (_strs(a['strengths']).isNotEmpty) _line('Strengths: ${_strs(a['strengths']).join(' · ')}', body),
        for (final r in _list(a['problems']))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(r['severity'])} · ${_s(r['area'])}', style: TextStyle(color: _sevColor(r['severity']), fontSize: 12)),
              Text(_s(r['finding']), style: body),
              if (_s(r['evidence']).isNotEmpty) Text('Evidence: ${_s(r['evidence'])}', style: small),
              Text('→ ${_s(r['fix'])}', style: body),
            ]),
          ),
      ]));
    }

    // migration
    if (x['migration'] is Map) {
      final g = _m(x['migration']);
      out.add(_section('Migration plan', [
        if (_s(g['from']).isNotEmpty || _s(g['to']).isNotEmpty) _line('${_s(g['from'])} → ${_s(g['to'])}', body),
        if (_s(g['strategy']).isNotEmpty)
          _line('Strategy: ${_s(g['strategy'])}${_s(g['why_strategy']).isNotEmpty ? ' - ${_s(g['why_strategy'])}' : ''}', body),
        for (final r in _list(g['phases']))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Phase ${_s(r['phase'])}: ${_s(r['what'])}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
              if (_s(r['rollback']).isNotEmpty) Text('Rollback: ${_s(r['rollback'])}', style: body),
              if (_s(r['exit']).isNotEmpty) Text('When complete: ${_s(r['exit'])}', style: small),
              if (_s(r['risk']).isNotEmpty) Text('Risk: ${_s(r['risk'])}', style: small),
            ]),
          ),
        if (_s(g['data_migration']).isNotEmpty) _line('Data: ${_s(g['data_migration'])}', body),
        if (_s(g['cutover']).isNotEmpty) _line('Cutover: ${_s(g['cutover'])}', body),
      ]));
    }

    // decision
    if (x['decision'] is Map || x['decision_result'] is Map) {
      final dc = _m(x['decision']);
      final dr = _m(x['decision_result']);
      final crit = _list(dc['criteria']);
      final opts = _list(dc['options']);
      out.add(_section('Decision', [
        if (_s(dc['question']).isNotEmpty) _line(_s(dc['question']), const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
        if (_s(dr['error']).isNotEmpty) _line(_s(dr['error']), const TextStyle(color: C.bad, fontSize: 12.5)),
        for (final t in _list(dr['totals']))
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(t['rank'])}. ${_s(t['option'])}  ${_s(t['score'])}', style: body),
              const SizedBox(height: 2),
              LinearProgressIndicator(
                value: ((t['score'] is num ? (t['score'] as num).toDouble() : 0.0) / 100).clamp(0.0, 1.0).toDouble(),
                minHeight: 6,
                color: C.violet,
                backgroundColor: C.line,
              ),
            ]),
          ),
        if (_s(dr['winner']).isNotEmpty)
          _line('${dr['close'] == true ? 'Close call' : 'Winner'}: ${_s(dr['winner'])}'
              '${dr['margin'] != null ? ' (${_s(dr['margin'])} se)' : ''}',
              TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5, color: dr['close'] == true ? C.warn : C.ok)),
        if (_strs(dr['flips']).isNotEmpty) _line('Changes when: ${_strs(dr['flips']).join(' · ')}', small),
        if (_strs(dr['missing']).isNotEmpty) _line('Not scored: ${_strs(dr['missing']).join(' · ')}', small),
        if (crit.isNotEmpty && opts.isNotEmpty)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columnSpacing: 14,
              headingRowHeight: 32,
              columns: [
                const DataColumn(label: Text('Criterion (weight)', style: TextStyle(fontSize: 12))),
                for (final o in opts) DataColumn(label: Text(_s(o['name']), style: const TextStyle(fontSize: 12))),
              ],
              rows: [
                for (final c in crit)
                  DataRow(cells: [
                    DataCell(Text('${_s(c['name'])} (${_s(c['weight'])})', style: const TextStyle(fontSize: 12))),
                    for (final o in opts)
                      DataCell(Text(_s(_m(o['scores'])[_s(c['name'])] ?? '-'), style: const TextStyle(fontSize: 12))),
                  ]),
              ],
            ),
          ),
        for (final o in opts)
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text(_s(o['name']), style: const TextStyle(fontSize: 13.5)),
            subtitle: _s(o['summary']).isEmpty ? null : Text(_s(o['summary']), style: small),
            children: [
              if (_strs(o['pros']).isNotEmpty) _line('Pros: ${_strs(o['pros']).join(' · ')}', body),
              if (_strs(o['cons']).isNotEmpty) _line('Cons: ${_strs(o['cons']).join(' · ')}', body),
              if (_s(o['cost_note']).isNotEmpty) _line(_s(o['cost_note']), small),
            ],
          ),
        if (_s(dc['recommendation']).isNotEmpty) _line('Advice: ${_s(dc['recommendation'])}', body),
      ]));
    }

    // threat model
    final tr = _m(x['threat_result']);
    final threats = _list(tr['rows']).isNotEmpty ? _list(tr['rows']) : _list(x['threats']);
    if (x['threat_result'] is Map || threats.isNotEmpty) {
      out.add(_section('Threat model (STRIDE)', [
        if (tr['total'] != null)
          _line('${_s(tr['total'])} threats${tr['open_high'] != null ? ' · ${_s(tr['open_high'])} high and still open' : ''}', body),
        if (_strs(x['trust_boundaries']).isNotEmpty) _line('Trust boundaries: ${_strs(x['trust_boundaries']).join(' · ')}', small),
        for (final r in threats)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(r['stride'])} · ${_s(r['target'])} · risk ${_s(r['risk'])} (${_s(r['likelihood'])}x${_s(r['impact'])})',
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              Text(_s(r['threat']), style: body),
              Text('→ ${_s(r['mitigation'])} · ${_s(r['status'])}', style: small),
            ]),
          ),
        if (_strs(tr['letters_unused']).isNotEmpty)
          _line('Not considered yet: ${_strs(tr['letters_unused']).join(', ')}', const TextStyle(color: C.warn, fontSize: 12.5)),
        if (_strs(tr['uncovered']).isNotEmpty) _line('Parts without a threat: ${_strs(tr['uncovered']).join(', ')}', small),
      ]));
    }

    // scale plan
    final sp = _list(x['scale_plan']);
    if (sp.isNotEmpty) {
      out.add(_section('Scale plan', [
        for (final r in sp)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(r['at'])}: ${_s(r['breaks'])}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              if (_s(r['signal']).isNotEmpty) Text('Signal: ${_s(r['signal'])}', style: small),
              Text('→ ${_s(r['change'])}', style: body),
            ]),
          ),
      ]));
    }

    // growth scenarios
    final sc = _m(x['scenarios']);
    final scRows = _list(sc['rows']);
    final scBreaks = _list(sc['breaks']);
    if (scRows.isNotEmpty || scBreaks.isNotEmpty) {
      out.add(_section('Growth scenarios (calculated by code)', [
        for (final r in scRows)
          _line('${_s(r['x'])}x: ${_s(r['dau'])} users/day · peak ${_s(r['peak_rps'])} req/s · writes ${_s(r['write_rps'])}/s · '
              '${_s(r['servers'])} servers · storage ${_bytes(r['storage_bytes'])} · egress ${_bytes(r['egress_bps'])}/s', body),
        for (final b in scBreaks)
          _line('Breaks first at ${_s(b['at'])}: ${_s(b['what'])}${_s(b['why']).isNotEmpty ? ' - ${_s(b['why'])}' : ''}',
              const TextStyle(color: C.warn, fontSize: 12.5)),
      ]));
    }

    // boundary rules
    final fr = _list(x['fitness_rules']);
    final fnow = x['fitness_now'] is List ? _list(x['fitness_now']) : null;
    if (fr.isNotEmpty || fnow != null) {
      out.add(_section('Boundary rules', [
        for (final r in fr)
          _line('${_s(r['name'])}: ${_s(r['from'])} ✗ ${_strs(r['must_not_depend_on']).join(', ')}'
              '${_s(r['why']).isNotEmpty ? ' - ${_s(r['why'])}' : ''}', body),
        if (fnow != null && fnow.isEmpty) _line('✓ The code follows every rule today.', const TextStyle(color: C.ok, fontSize: 12.5)),
        if (fnow != null)
          for (final r in fnow)
            _line('Broken: ${_s(r['rule'])} · ${_s(r['from'])} → ${_s(r['to'])}', const TextStyle(color: C.bad, fontSize: 12.5)),
      ]));
    }

    // module map
    final mm = _m(_m(_p['repo_facts'])['module_map']);
    if (mm.isNotEmpty) {
      final cycles = (mm['cycles'] is List ? mm['cycles'] as List : const []);
      out.add(_section('Module map (from the real imports)', [
        _line('${(mm['modules'] is List ? (mm['modules'] as List).length : 0)} modules · '
            '${(mm['edges'] is List ? (mm['edges'] as List).length : 0)} links'
            '${mm['files_scanned'] != null ? ' · ${_s(mm['files_scanned'])} files read' : ''}', small),
        if (cycles.isEmpty) _line('✓ No import cycles.', const TextStyle(color: C.ok, fontSize: 12.5)),
        for (final c in cycles) _line('Cycle: ${_strs(c).join(' → ')}', const TextStyle(color: C.bad, fontSize: 12.5)),
        for (final h in _list(mm['hotspots']))
          _line('${_s(h['module'])}: used by ${_s(h['fan_in'])}, uses ${_s(h['fan_out'])}, ${_s(h['lines'])} lines', body),
      ]));
    }

    // peer review
    if (x['review'] is Map) {
      final rv = _m(x['review']);
      final issues = _list(rv['issues']);
      out.add(_section('Peer review', [
        _line('${_s(rv['verdict']).isNotEmpty ? '${_s(rv['verdict'])} · ' : ''}${issues.length} issues'
            '${rv['revised'] == true ? ' · fixed in this version' : ''}',
            TextStyle(fontSize: 13, color: rv['revised'] == true ? C.ok : C.muted)),
        for (final r in issues)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(r['severity'])} · ${_s(r['area'])}', style: TextStyle(color: _sevColor(r['severity']), fontSize: 12)),
              Text(_s(r['issue']), style: body),
              Text('→ ${_s(r['fix'])}', style: small),
            ]),
          ),
      ]));
    }

    // design checks
    final checks = _list(x['checks']);
    if (checks.isNotEmpty) {
      final pass = checks.where((c) => c['ok'] == true).length;
      out.add(_section('Design checks ($pass/${checks.length} pass)', [
        for (final c in checks)
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text.rich(TextSpan(children: [
              TextSpan(text: c['ok'] == true ? '✓ ' : '✗ ', style: TextStyle(color: c['ok'] == true ? C.ok : C.bad, fontSize: 13.5)),
              TextSpan(text: _s(c['check']), style: body),
              if (_s(c['detail']).isNotEmpty) TextSpan(text: ' - ${_s(c['detail'])}', style: small),
            ])),
          ),
      ]));
    }

    // API contract
    final ac = _m(x['api_check']);
    if (ac.isNotEmpty || _s(_p['api_yaml']).isNotEmpty) {
      out.add(_section('API contract', [
        if (ac['skipped'] != null && ac['skipped'] != false)
          _line('Not checked${ac['skipped'] is String ? ': ${_s(ac['skipped'])}' : ''}.', small)
        else if (ac.isNotEmpty)
          _line(
              ac['ok'] == true
                  ? '✓ Valid OpenAPI: ${_s(ac['paths'])} paths, ${_s(ac['operations'])} operations'
                  : '✗ Could not be parsed: ${_s(ac['error'])}',
              TextStyle(color: ac['ok'] == true ? C.ok : C.bad, fontSize: 12.5)),
        if (_s(_p['api_yaml']).isNotEmpty)
          TextButton(
            onPressed: () => launchUrl(Uri.parse(_url(_s(_p['api_yaml']))), mode: LaunchMode.externalApplication),
            child: const Text('Open api.yaml'),
          ),
      ]));
    }
    return out;
  }


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
                      onPressed: _busy ? null : () => _do(() => api.archApprove(widget.id), 'Approved.'),
                      child: const Text('Approve design'),
                    ),
                  if (_s(_p['pdf']).isNotEmpty)
                    OutlinedButton(
                      onPressed: () => launchUrl(Uri.parse(_url(_s(_p['pdf']))), mode: LaunchMode.externalApplication),
                      child: const Text('PDF'),
                    ),
                  if (_s(_p['api_yaml']).isNotEmpty)
                    OutlinedButton(
                      onPressed: () => launchUrl(Uri.parse(_url(_s(_p['api_yaml']))), mode: LaunchMode.externalApplication),
                      child: const Text('API contract (api.yaml)'),
                    ),
                ]),
                if (_s(_p['kind_title']).isNotEmpty)
                  Text(_s(_p['kind_title']), style: const TextStyle(color: C.faint, fontSize: 12)),
                if (d['summary'] != null) _section('Summary', [MdText(_s(d['summary']), style: body)]),
                ..._master(body),
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
                            Text('Diagram could not be made: ${_s(g['error'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
                        ]),
                      ),
                  ]),
                if (cap['rows'] != null || cap['error'] != null)
                  _section('Capacity (calculated by code)', [
                    if (cap['error'] != null) Text(_s(cap['error']), style: body),
                    for (final r in _list(cap['rows']))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text('${r['what']}: ${r['value']}', style: body),
                      ),
                    if ((cap['assumed'] as List?)?.isNotEmpty ?? false)
                      Text('Estimate (please confirm): ${(cap['assumed'] as List).join(', ')}',
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                if (_list(d['adrs']).isNotEmpty)
                  _section('Decisions (ADRs)', [
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
                  _section('Change', [
                    TextField(controller: _words, maxLength: 2000, minLines: 1, maxLines: 4,
                        decoration: const InputDecoration(hintText: 'e.g. Postgres, not MongoDB; for 10x users')),
                    OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () {
                              final w = _words.text.trim();
                              if (w.isEmpty) return;
                              _words.clear();
                              _do(() => api.archChange(widget.id, w), 'The next version is being made.');
                            },
                      child: const Text('Next version'),
                    ),
                  ]),
                if (status == 'approved' && _s(_p['repo']).isNotEmpty)
                  _section('Pull requests', [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _p['watch_prs'] == true,
                      title: const Text('Review new PRs by itself (draft notes only)', style: TextStyle(fontSize: 13.5)),
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
                                _do(() => api.archReview(widget.id, n), 'PR reviewed - the notes are drafts.');
                              },
                        child: const Text('Review this PR'),
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
                          onPressed: _busy ? null : () => _do(() => api.archPostReview(_s(r['id'])), 'Posted on the PR.'),
                          child: const Text('Post on the PR'),
                        ),
                        TextButton(
                          onPressed: _busy ? null : () => _do(() => api.archDiscardReview(_s(r['id'])), ''),
                          child: const Text('Remove'),
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
