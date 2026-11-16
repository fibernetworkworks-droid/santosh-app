/// v0.947 HOOLA AUTO on the phone (design: claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz, boards P0-P6): a whole client
/// project run by specialist agents on Hoola Code sessions. Home (projects), mission control (phases, needs you,
/// agents, live feed), one agent (its conversation, current session steps, change requests, tasks), a gate (G1-G8, the
/// go-live merge), the intake (Hoola asks, found answers, conflicts, the client link) and the environments.
/// All on the server's /api/auto routes; every gate is her tap carrying the gate's hash.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'devsahayak_drawer.dart' show devOpenSession, hcTime;
import 'devsahayak_kit.dart';
import 'hoola_theme.dart';

const String _base = '/api/auto/projects';

Future<Map<String, dynamic>> _call(Santosh app, String method, String path, {Object? body}) async =>
    hcM(await app.api!.call(method, path, body: body, timeout: const Duration(minutes: 3)));

Color autoStateColor(CodeColors c, String s) {
  switch (s) {
    case 'run':
    case 'working':
    case 'queued':
      return c.accent;
    case 'need':
    case 'needs':
    case 'paused':
      return c.amber;
    case 'done':
      return c.green;
    default:
      return c.ink5;
  }
}

String _stateWord(String s) => const {
      'working': 'Working',
      'queued': 'Waiting for a slot',
      'needs': 'Needs you',
      'done': 'Done',
      'wait': 'Not started',
      'todo': 'To do',
      'failed': 'Failed',
      'skipped': 'Skipped',
    }[s] ??
    s;

String _at(String iso) {
  final d = DateTime.tryParse(iso);
  return d == null ? '' : hcTime(d.toLocal());
}

String _rs(dynamic v) {
  final n = (v is num) ? v : num.tryParse('$v') ?? 0;
  final s = n.round().toString();
  if (s.length <= 3) return 'Rs $s';
  final last = s.substring(s.length - 3);
  var rest = s.substring(0, s.length - 3);
  final parts = <String>[];
  while (rest.length > 2) {
    parts.insert(0, rest.substring(rest.length - 2));
    rest = rest.substring(0, rest.length - 2);
  }
  if (rest.isNotEmpty) parts.insert(0, rest);
  return 'Rs ${parts.join(',')},$last';
}

BoxDecoration _cardBox(CodeColors c, {Color? edge, Color? fill}) => BoxDecoration(
      color: fill ?? c.card,
      borderRadius: HoolaRadius.r(HoolaRadius.card),
      border: Border.all(color: edge ?? c.line),
    );

/// The page head (design: back 48, title 17/600 + a line, a slot on the right).
class _Head extends StatelessWidget {
  const _Head({required this.title, this.sub = '', this.trailing = const []});
  final String title;
  final String sub;
  final List<Widget> trailing;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return SizedBox(
      height: 60,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Row(children: [
          HcIconButton(icon: Icons.arrow_back_rounded, label: 'Back', color: c.ink, onTap: () => Navigator.maybePop(context)),
          Expanded(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 17, weight: FontWeight.w600)),
              if (sub.isNotEmpty)
                Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink4)),
            ]),
          ),
          ...trailing,
        ]),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill(this.text, {this.color, this.fill});
  final String text;
  final Color? color;
  final Color? fill;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: fill ?? c.chip, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
      child: Text(text, style: HcType.mono(c, 13, color: color ?? c.ink2)),
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar(this.pct, {this.color, this.height = 5});
  final num pct;
  final Color? color;
  final double height;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final f = (pct / 100).clamp(0.0, 1.0).toDouble();
    return ClipRRect(
      borderRadius: HoolaRadius.r(height),
      child: SizedBox(
        height: height,
        child: Stack(children: [
          Positioned.fill(child: ColoredBox(color: c.raised)),
          FractionallySizedBox(widthFactor: f, child: ColoredBox(color: color ?? c.accent)),
        ]),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge(this.text, {required this.fill, required this.ink});
  final String text;
  final Color fill;
  final Color ink;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: fill, borderRadius: HoolaRadius.r(6)),
      child: Text(text, style: HcType.ui(c, 12, weight: FontWeight.w500, color: ink)),
    );
  }
}

Widget _tick(CodeColors c, String state, {double size = 16}) {
  if (state == 'done') return Icon(Icons.check_rounded, size: size, color: c.green);
  if (state == 'working' || state == 'queued') return HcDot(c.accent, size: 7);
  if (state == 'needs') return Icon(Icons.warning_amber_rounded, size: size, color: c.amber);
  return Container(
    width: 9,
    height: 9,
    decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: c.radioOff, width: 1.5)),
  );
}

Widget _loading(CodeColors c) => Center(child: CircularProgressIndicator(strokeWidth: 2, color: c.accent));

// ================================================================================================== P0 / home
class AutoHomePage extends StatefulWidget {
  const AutoHomePage({super.key, required this.app});
  final Santosh app;

  @override
  State<AutoHomePage> createState() => _AutoHomePageState();
}

class _AutoHomePageState extends State<AutoHomePage> {
  Map<String, dynamic>? _d;
  Timer? _t;

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 8), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await _call(widget.app, 'GET', _base);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) {
        setState(() => _d ??= {'projects': const []});
      }
    }
  }

  Future<void> _new() async {
    final id = await hcSheet<String>(context, (_) => _NewProjectSheet(app: widget.app));
    if (id == null || !mounted) return;
    await _load();
    if (!mounted) return;
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => AutoProjectPage(app: widget.app, id: id)));
  }

  void _open(Map<String, dynamic> p) {
    final ph = hcS(p['phase']);
    final id = hcS(p['id']);
    final Widget page = (ph == 'setup')
        ? AutoEnvPage(app: widget.app, pid: id)
        : (ph == 'intake')
            ? AutoIntakePage(app: widget.app, pid: id)
            : AutoProjectPage(app: widget.app, id: id);
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => page)).then((_) => _load());
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final rows = hcList(_d?['projects']);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const _Head(title: 'Hoola Auto'),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
            child: Text(
                'Give Hoola a whole client project. Specialist agents build it, each in its own session you can open and talk to. Every gate waits for your tap.',
                style: HcType.ui(c, 14, color: c.ink3, height: 1.45)),
          ),
          Expanded(
            child: _d == null
                ? _loading(c)
                : RefreshIndicator(
                    color: c.accent,
                    onRefresh: _load,
                    child: rows.isEmpty
                        ? ListView(children: [
                            Padding(
                              padding: const EdgeInsets.all(32),
                              child: Text('No Auto projects yet.', textAlign: TextAlign.center, style: HcType.ui(c, 15, color: c.ink4)),
                            ),
                          ])
                        : ListView.separated(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            itemCount: rows.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 10),
                            itemBuilder: (_, i) => _row(c, rows[i]),
                          ),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            child: HcCreamButton(label: 'New Auto project', icon: Icons.add_rounded, onTap: _new),
          ),
        ]),
      ),
    );
  }

  Widget _row(CodeColors c, Map<String, dynamic> p) {
    final st = hcS(p['state']);
    final gate = hcS(p['gate']);
    return Material(
      color: c.card,
      borderRadius: HoolaRadius.r(HoolaRadius.card),
      child: InkWell(
        borderRadius: HoolaRadius.r(HoolaRadius.card),
        onTap: () => _open(p),
        child: Container(
          decoration: BoxDecoration(borderRadius: HoolaRadius.r(HoolaRadius.card), border: Border.all(color: c.line)),
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              HcDot(autoStateColor(c, st)),
              const SizedBox(width: 10),
              Expanded(child: Text(hcS(p['name']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 16, weight: FontWeight.w500))),
              Text('${hcInt(p['pct'])}%', style: HcType.mono(c, 13, color: c.ink2)),
            ]),
            const SizedBox(height: 4),
            Padding(
              padding: const EdgeInsets.only(left: 18),
              child: Text(hcS(p['sub']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink4)),
            ),
            const SizedBox(height: 10),
            Padding(padding: const EdgeInsets.only(left: 18), child: _Bar(hcInt(p['pct']), color: autoStateColor(c, st))),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.only(left: 18),
              child: Row(children: [
                Expanded(
                  child: Text(gate.isNotEmpty ? gate : hcS(p['phase_label']),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: HcType.ui(c, 13, color: gate.isNotEmpty ? c.amber : c.ink3)),
                ),
                Text('${_rs(p['spent_inr'])} / ${_rs(p['cap_inr'])}', style: HcType.mono(c, 12, color: c.ink4)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

class _NewProjectSheet extends StatefulWidget {
  const _NewProjectSheet({required this.app});
  final Santosh app;

  @override
  State<_NewProjectSheet> createState() => _NewProjectSheetState();
}

class _NewProjectSheetState extends State<_NewProjectSheet> {
  final _name = TextEditingController();
  final _client = TextEditingController();
  List<String> _repos = const [];
  final Set<String> _pick = {};
  bool _busy = false;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _loadRepos();
  }

  @override
  void dispose() {
    _name.dispose();
    _client.dispose();
    super.dispose();
  }

  Future<void> _loadRepos() async {
    try {
      final r = await _call(widget.app, 'GET', '/api/devsahayak/repos');
      if (!mounted) return;
      setState(() {
        _repos = [for (final x in hcList(r['repos'])) if (hcS(x['repo']).isNotEmpty) hcS(x['repo'])];
        if (_repos.isNotEmpty) _pick.add(_repos.first);
        _loaded = true;
      });
    } catch (e) {
      if (mounted) setState(() => _loaded = true);
    }
  }

  Future<void> _create() async {
    if (_name.text.trim().isEmpty) {
      hcSay(context, 'Give the project a name.');
      return;
    }
    setState(() => _busy = true);
    try {
      final p = await _call(widget.app, 'POST', _base,
          body: {'name': _name.text.trim(), 'client_name': _client.text.trim(), 'repos': _pick.toList()});
      if (mounted) Navigator.pop(context, hcS(p['id']));
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        hcSay(context, '$e');
      }
    }
  }

  Widget _field(CodeColors c, TextEditingController ctl, String hint) => TextField(
        controller: ctl,
        style: HcType.ui(c, 16),
        cursorColor: c.accent,
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: HcType.ui(c, 16, color: c.ink5),
          filled: true,
          fillColor: c.field,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
          focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
        const HcSheetHead(title: 'New Auto project', sub: 'Then attach environments and take the client intake'),
        const SizedBox(height: 12),
        _field(c, _name, 'Project name, e.g. Clinic booking app'),
        const SizedBox(height: 10),
        _field(c, _client, 'Client, e.g. Sai Dental Clinic'),
        const SizedBox(height: 16),
        Text('Repositories the agents work in', style: HcType.ui(c, 14, weight: FontWeight.w600)),
        const SizedBox(height: 6),
        if (!_loaded)
          Padding(padding: const EdgeInsets.all(12), child: _loading(c))
        else if (_repos.isEmpty)
          Text('No repositories yet. Add one in Hoola Code settings first; you can attach it later too.',
              style: HcType.ui(c, 13, color: c.ink4, height: 1.4))
        else
          for (final r in _repos)
            InkWell(
              onTap: () => setState(() => _pick.contains(r) ? _pick.remove(r) : _pick.add(r)),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 48),
                child: Row(children: [
                  Icon(_pick.contains(r) ? Icons.check_box_rounded : Icons.check_box_outline_blank_rounded,
                      color: _pick.contains(r) ? c.accent : c.ink4),
                  const SizedBox(width: 10),
                  Expanded(child: Text(r, style: HcType.mono(c, 14))),
                ]),
              ),
            ),
        const SizedBox(height: 16),
        HcCreamButton(label: 'Create project', busy: _busy, onTap: _busy ? null : _create),
      ]),
    );
  }
}

// ================================================================================================== P1 / mission control
class AutoProjectPage extends StatefulWidget {
  const AutoProjectPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;

  @override
  State<AutoProjectPage> createState() => _AutoProjectPageState();
}

class _AutoProjectPageState extends State<AutoProjectPage> {
  Map<String, dynamic>? _m;
  Timer? _t;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final m = await _call(widget.app, 'GET', '$_base/${widget.id}/mission');
      if (mounted) setState(() => _m = m);
    } catch (e) {
      if (mounted && _m == null) hcSay(context, '$e');
    }
  }

  Future<void> _patch(Map<String, dynamic> body) async {
    try {
      await _call(widget.app, 'PATCH', '$_base/${widget.id}', body: body);
      await _load();
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  void _push(Widget page) => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => page)).then((_) => _load());

  Future<void> _menu() async {
    final p = hcM(_m?['project']);
    final paused = p['paused'] == true;
    final pick = await hcSheet<String>(context, (sheet) {
      final c = CodeColors.of(sheet);
      Widget item(String key, IconData icon, String label) => ListTile(
            minVerticalPadding: 14,
            leading: Icon(icon, color: c.ink2),
            title: Text(label, style: HcType.ui(c, 16)),
            onTap: () => Navigator.pop(sheet, key),
          );
      return Column(mainAxisSize: MainAxisSize.min, children: [
        HcSheetHead(title: hcS(p['name'])),
        item('intake', Icons.assignment_outlined, 'Client intake'),
        item('env', Icons.cloud_outlined, 'Environments'),
        item('gates', Icons.flag_outlined, 'Gates G1 to G8'),
        item('pause', paused ? Icons.play_arrow_rounded : Icons.pause_rounded, paused ? 'Start the agents again' : 'Pause all agents'),
        const SizedBox(height: 12),
      ]);
    });
    if (!mounted || pick == null) return;
    if (pick == 'intake') _push(AutoIntakePage(app: widget.app, pid: widget.id));
    if (pick == 'env') _push(AutoEnvPage(app: widget.app, pid: widget.id));
    if (pick == 'gates') _push(AutoGatesPage(app: widget.app, pid: widget.id));
    if (pick == 'pause') await _patch({'paused': !paused});
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final m = _m;
    if (m == null) {
      return Scaffold(backgroundColor: c.bg, body: SafeArea(child: Column(children: [const _Head(title: 'Hoola Auto'), Expanded(child: _loading(c))])));
    }
    final p = hcM(m['project']);
    final agents = hcList(m['agents']);
    final counts = hcM(p['tasks']);
    bool keep(Map<String, dynamic> a) {
      final s = hcS(a['state']);
      if (_filter == 'work') return s == 'working' || s == 'queued';
      if (_filter == 'need') return s == 'needs';
      if (_filter == 'done') return s == 'done';
      return true;
    }

    final shown = agents.where(keep).toList();
    final nWork = agents.where((a) => ['working', 'queued'].contains(hcS(a['state']))).length;
    final nNeed = agents.where((a) => hcS(a['state']) == 'needs').length;
    final nDone = agents.where((a) => hcS(a['state']) == 'done').length;
    final stats = <String>[
      '${hcInt(counts['done'])} of ${hcInt(counts['total'])} tasks',
      '${_rs(p['spent_inr'])} of ${_rs(p['cap_inr'])}',
      if (hcInt(m['day']) > 0) 'day ${hcInt(m['day'])}',
    ].join(' · ');
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(title: hcS(p['name']), sub: hcS(p['phase_label']), trailing: [
            _Pill('${hcInt(p['pct'])}%', color: c.accentInk, fill: c.accentTint),
            HcIconButton(icon: Icons.more_horiz_rounded, label: 'More', onTap: _menu),
          ]),
          Expanded(
            child: RefreshIndicator(
              color: c.accent,
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 16), children: [
                Text(stats, style: HcType.ui(c, 13, color: c.ink3)),
                const SizedBox(height: 12),
                _phases(c, hcList(m['phases'])),
                const SizedBox(height: 14),
                for (final n in hcList(m['needs'])) ...[_need(c, n), const SizedBox(height: 10)],
                Wrap(spacing: 6, runSpacing: 6, children: [
                  HcFilterChip(label: 'All ${agents.length}', on: _filter == 'all', outlined: true, onTap: () => setState(() => _filter = 'all')),
                  HcFilterChip(label: 'Working $nWork', on: _filter == 'work', outlined: true, onTap: () => setState(() => _filter = 'work')),
                  HcFilterChip(label: 'Needs you $nNeed', on: _filter == 'need', outlined: true, onTap: () => setState(() => _filter = 'need')),
                  HcFilterChip(label: 'Done $nDone', on: _filter == 'done', outlined: true, onTap: () => setState(() => _filter = 'done')),
                ]),
                const SizedBox(height: 10),
                Container(
                  decoration: _cardBox(c),
                  child: Column(children: [
                    for (var i = 0; i < shown.length; i++) _agentRow(c, shown[i], i == 0),
                    if (shown.isEmpty)
                      Padding(padding: const EdgeInsets.all(20), child: Text('No agents here.', style: HcType.ui(c, 14, color: c.ink4))),
                  ]),
                ),
                const SizedBox(height: 10),
                Text('${hcInt(m['live_limit'])} Hoola Code sessions run at a time on this server; the others wait for a free slot.',
                    style: HcType.ui(c, 12, color: c.ink4, height: 1.4)),
                const SizedBox(height: 12),
                Material(
                  color: c.card,
                  borderRadius: HoolaRadius.r(HoolaRadius.card),
                  child: InkWell(
                    borderRadius: HoolaRadius.r(HoolaRadius.card),
                    onTap: () => _push(AutoFeedPage(app: widget.app, pid: widget.id)),
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 52),
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(borderRadius: HoolaRadius.r(HoolaRadius.card), border: Border.all(color: c.line)),
                      child: Row(children: [
                        HcDot(c.accent),
                        const SizedBox(width: 10),
                        Expanded(child: Text('Live feed', style: HcType.ui(c, 15, weight: FontWeight.w500))),
                        Text('${hcList(m['feed']).length} events', style: HcType.ui(c, 13, color: c.ink4)),
                        Icon(Icons.chevron_right_rounded, color: c.ink4),
                      ]),
                    ),
                  ),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _phases(CodeColors c, List<Map<String, dynamic>> ph) {
    return Row(children: [
      for (var i = 0; i < ph.length; i++) ...[
        if (i > 0) const SizedBox(width: 4),
        Expanded(
          child: Semantics(
            label: '${hcS(ph[i]['label'])} ${hcInt(ph[i]['pct'])} percent',
            excludeSemantics: true,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _Bar(hcInt(ph[i]['pct']), color: ph[i]['done'] == true ? c.green : c.accent, height: 4),
              const SizedBox(height: 5),
              Text(hcS(ph[i]['label']),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: HcType.ui(c, 12, color: ph[i]['now'] == true ? c.accentInk : (ph[i]['done'] == true ? c.ink3 : c.ink5))),
            ]),
          ),
        ),
      ],
    ]);
  }

  Widget _need(CodeColors c, Map<String, dynamic> n) {
    final kind = hcS(n['kind']);
    VoidCallback? go;
    String btn = 'Open';
    if (kind == 'gate') {
      go = () => _push(AutoGatePage(app: widget.app, pid: widget.id, gid: hcS(n['id'])));
      btn = 'Review';
    } else if (kind == 'task') {
      go = () => _push(AutoAgentPage(app: widget.app, pid: widget.id, role: hcS(n['role'])));
    } else if (kind == 'paused') {
      go = () => _patch({'paused': false});
      btn = 'Resume';
    }
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _cardBox(c),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _Badge('Needs your OK', fill: c.chip, ink: c.amber),
        const SizedBox(height: 8),
        Text(hcS(n['text']), style: HcType.ui(c, 15, height: 1.4)),
        const SizedBox(height: 10),
        Align(alignment: Alignment.centerLeft, child: HcCreamButton(label: btn, height: 44, size: 15, onTap: go)),
      ]),
    );
  }

  Widget _agentRow(CodeColors c, Map<String, dynamic> a, bool first) {
    final st = hcS(a['state']);
    final session = a['session'] == true;
    return InkWell(
      onTap: () => _push(AutoAgentPage(app: widget.app, pid: widget.id, role: hcS(a['role']))),
      child: Container(
        constraints: const BoxConstraints(minHeight: 60),
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
        decoration: BoxDecoration(border: first ? null : Border(top: BorderSide(color: c.line))),
        child: Row(children: [
          HcDot(autoStateColor(c, st)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(hcS(a['label']), style: HcType.ui(c, 15, weight: FontWeight.w500)),
              const SizedBox(height: 2),
              Text(hcS(a['step']).isNotEmpty ? hcS(a['step']) : _stateWord(st),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: st == 'needs' ? c.amber : c.ink4)),
            ]),
          ),
          if (session) ...[
            const SizedBox(width: 10),
            SizedBox(
              width: 56,
              child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text('${hcInt(a['pct'])}%', style: HcType.mono(c, 13, color: c.ink2)),
                const SizedBox(height: 5),
                _Bar(hcInt(a['pct']), color: st == 'done' ? c.green : (st == 'needs' ? c.amber : c.accent), height: 3),
              ]),
            ),
          ],
        ]),
      ),
    );
  }
}

// ================================================================================================== P3 / live feed
class AutoFeedPage extends StatefulWidget {
  const AutoFeedPage({super.key, required this.app, required this.pid});
  final Santosh app;
  final String pid;

  @override
  State<AutoFeedPage> createState() => _AutoFeedPageState();
}

class _AutoFeedPageState extends State<AutoFeedPage> {
  Map<String, dynamic>? _m;
  Timer? _t;
  String _f = 'all';

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final m = await _call(widget.app, 'GET', '$_base/${widget.pid}/mission');
      if (mounted) setState(() => _m = m);
    } catch (e) {
      if (mounted && _m == null) hcSay(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final feed = hcList(_m?['feed']).where((e) {
      final k = hcS(e['kind']);
      if (_f == 'done') return k == 'done';
      if (_f == 'need') return k == 'need';
      if (_f == 'build') return hcS(e['role']).startsWith('builder');
      return true;
    }).toList();
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(title: 'Live feed', sub: hcS(hcM(_m?['project'])['name'])),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Wrap(spacing: 6, children: [
              HcFilterChip(label: 'All', on: _f == 'all', outlined: true, onTap: () => setState(() => _f = 'all')),
              HcFilterChip(label: 'Done', on: _f == 'done', outlined: true, onTap: () => setState(() => _f = 'done')),
              HcFilterChip(label: 'Needs you', on: _f == 'need', outlined: true, onTap: () => setState(() => _f = 'need')),
              HcFilterChip(label: 'Builders', on: _f == 'build', outlined: true, onTap: () => setState(() => _f = 'build')),
            ]),
          ),
          Expanded(
            child: _m == null
                ? _loading(c)
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: feed.length,
                    separatorBuilder: (_, __) => Divider(height: 1, color: c.line),
                    itemBuilder: (_, i) {
                      final e = feed[i];
                      final k = hcS(e['kind']);
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          SizedBox(width: 20, child: Center(child: _tick(c, k == 'done' ? 'done' : k == 'need' ? 'needs' : 'working'))),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text.rich(
                                TextSpan(children: [
                                  TextSpan(text: '${hcS(e['who'])} ', style: HcType.ui(c, 14, weight: FontWeight.w600)),
                                  TextSpan(text: hcS(e['text']), style: HcType.ui(c, 14, color: c.ink2, height: 1.4)),
                                ]),
                              ),
                              const SizedBox(height: 3),
                              Text(_at(hcS(e['at'])), style: HcType.mono(c, 12, color: c.ink4)),
                            ]),
                          ),
                        ]),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }
}

// ================================================================================================== P2 / one agent
class AutoAgentPage extends StatefulWidget {
  const AutoAgentPage({super.key, required this.app, required this.pid, required this.role});
  final Santosh app;
  final String pid;
  final String role;

  @override
  State<AutoAgentPage> createState() => _AutoAgentPageState();
}

class _AutoAgentPageState extends State<AutoAgentPage> {
  Map<String, dynamic>? _v;
  Timer? _t;
  final _msg = TextEditingController();
  bool _busy = false;
  final _scroll = ScrollController();

  String get _path => '$_base/${widget.pid}/agents/${widget.role}';

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 4), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    _msg.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final v = await _call(widget.app, 'GET', _path);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted && _v == null) hcSay(context, '$e');
    }
  }

  Future<void> _send() async {
    final text = _msg.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() => _busy = true);
    try {
      final v = await _call(widget.app, 'POST', '$_path/message', body: {'text': text});
      if (!mounted) return;
      _msg.clear();
      setState(() => _v = v);
      final w = hcS(v['warn']);
      if (w.isNotEmpty) hcSay(context, w);
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _decide(Map<String, dynamic> ch, bool yes) async {
    try {
      await _call(widget.app, 'POST', '$_base/${widget.pid}/gates/${hcS(ch['gate'])}/decide', body: {'yes': yes, 'hash': hcS(ch['hash'])});
      await _load();
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  Future<void> _tasks() async {
    await hcSheet<void>(context, (_) => _TasksSheet(app: widget.app, pid: widget.pid, view: _v ?? const {}), tall: true);
    if (mounted) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final v = _v;
    final ag = hcM(v?['agent']);
    final sess = hcM(v?['session']);
    final cur = hcM(v?['current']);
    final label = hcS(ag['label']).isNotEmpty ? hcS(ag['label']) : widget.role;
    final sub = cur.isNotEmpty ? '${hcS(hcM(v?['project'])['name'])} · task ${hcInt(cur['seq'])} of ${hcInt(ag['tasks'])}' : hcS(hcM(v?['project'])['name']);
    final running = sess['running'] == true;
    final steps = hcList(sess['steps']);
    final since = DateTime.tryParse(hcS(ag['since']));
    final secs = since == null ? 0 : DateTime.now().toUtc().difference(since.toUtc()).inSeconds;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(title: label, sub: sub, trailing: [
            if (ag['session'] == true) _Pill('${hcInt(ag['pct'])}%', color: c.accentInk, fill: c.accentTint),
            HcIconButton(icon: Icons.checklist_rounded, label: 'Tasks and proof', onTap: v == null ? null : _tasks),
          ]),
          Expanded(
            child: v == null
                ? _loading(c)
                : ListView(controller: _scroll, padding: const EdgeInsets.fromLTRB(16, 4, 16, 12), children: [
                    Text(hcS(v['does']), style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
                    const SizedBox(height: 14),
                    for (final m in hcList(v['chat'])) ...[_msgRow(c, m), const SizedBox(height: 12)],
                    if (steps.isNotEmpty || hcS(sess['now']).isNotEmpty) ...[
                      if (cur.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Text('Task ${hcInt(cur['seq'])}: ${hcS(cur['title'])}', style: HcType.ui(c, 14, weight: FontWeight.w600)),
                        ),
                      _stepsCard(c, steps, hcS(sess['now'])),
                      const SizedBox(height: 10),
                    ],
                    if (hcS(sess['question']).isNotEmpty) ...[
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: _cardBox(c),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _Badge('Hoola asks', fill: c.accentTint, ink: c.accentInk),
                          const SizedBox(height: 8),
                          Text(hcS(sess['question']), style: HcType.serif(c, 16, height: 1.45)),
                          const SizedBox(height: 10),
                          HcOutlineButton(
                              label: 'Answer in the session',
                              height: 44,
                              onTap: () => devOpenSession(Navigator.of(context), widget.app, hcS(sess['id']))),
                        ]),
                      ),
                      const SizedBox(height: 10),
                    ],
                    if (cur.isNotEmpty && hcS(cur['state']) == 'needs' && hcS(cur['why']).isNotEmpty) ...[
                      Text(hcS(cur['why']), style: HcType.ui(c, 14, color: c.amber, height: 1.4)),
                      const SizedBox(height: 10),
                    ],
                    Row(children: [
                      HcDot(running ? c.accent : autoStateColor(c, hcS(ag['state']))),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                            running ? 'Working · ${hcClock(secs)}' : _stateWord(hcS(ag['state'])),
                            style: HcType.ui(c, 14, color: c.ink3)),
                      ),
                      if (hcS(sess['id']).isNotEmpty)
                        TextButton(
                          onPressed: () => devOpenSession(Navigator.of(context), widget.app, hcS(sess['id'])),
                          child: Text('Open full session', style: HcType.ui(c, 14, color: c.accentInk)),
                        ),
                    ]),
                  ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              HcComposer(
                controller: _msg,
                hint: 'Message $label',
                language: widget.app.language,
                busy: _busy,
                onSend: _send,
                enabled: v != null,
              ),
              const SizedBox(height: 8),
              Center(
                child: Text(
                  [
                    if (hcS(sess['model']).isNotEmpty) hcS(sess['model']),
                    if (ag['session'] == true) 'My tasks ${hcInt(ag['done'])}/${hcInt(ag['tasks'])}',
                    if (hcS('${ag['share'] ?? ''}').isNotEmpty) '${ag['share']}% of project',
                  ].join('   '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: HcType.ui(c, 13, color: c.ink3),
                ),
              ),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _msgRow(CodeColors c, Map<String, dynamic> m) {
    final you = hcS(m['who']) == 'you';
    final ch = hcM(m['change']);
    final tag = hcS(m['tag']);
    final children = <Widget>[];
    if (you) {
      children.add(Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(color: c.raised, borderRadius: HoolaRadius.r(18)),
            child: Text(hcS(m['text']), style: HcType.ui(c, 15, height: 1.4)),
          ),
        ),
      ));
    } else {
      children.add(Text(hcS(m['text']), style: HcType.prose(c)));
      if (tag.isNotEmpty) {
        children.add(const SizedBox(height: 6));
        children.add(Align(
          alignment: Alignment.centerLeft,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(color: c.greenSoft, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.check_rounded, size: 14, color: c.green),
              const SizedBox(width: 4),
              Text(tag, style: HcType.ui(c, 12, color: c.green)),
            ]),
          ),
        ));
      }
      if (ch.isNotEmpty) {
        children.add(const SizedBox(height: 10));
        children.add(_crCard(c, ch));
      }
    }
    return Column(crossAxisAlignment: you ? CrossAxisAlignment.end : CrossAxisAlignment.start, children: children);
  }

  Widget _crCard(CodeColors c, Map<String, dynamic> ch) {
    final st = hcS(ch['state']);
    final waiting = st == 'wait' && hcS(ch['hash']).isNotEmpty;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _cardBox(c),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _Badge(waiting ? 'Needs your OK' : (st == 'approved' ? 'Approved' : st == 'declined' ? 'Not now' : 'Change'),
              fill: waiting ? c.chip : (st == 'approved' ? c.greenSoft : c.chip), ink: waiting ? c.amber : (st == 'approved' ? c.green : c.ink3)),
          const SizedBox(width: 8),
          Text('Change request ${hcS(ch['cr'])}', style: HcType.ui(c, 13, color: c.ink4)),
        ]),
        const SizedBox(height: 8),
        Text(hcS(ch['title']), style: HcType.serif(c, 17, weight: FontWeight.w500)),
        const SizedBox(height: 4),
        Text('About ${hcInt(ch['minutes'])} min · ${_rs(ch['cost_inr'])} · not in the approved spec',
            style: HcType.ui(c, 13, color: c.ink3)),
        if (waiting) ...[
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: HcCreamButton(label: 'Approve', height: 46, size: 15, onTap: () => _decide(ch, true))),
            const SizedBox(width: 8),
            Expanded(child: HcOutlineButton(label: 'Not now', height: 46, onTap: () => _decide(ch, false))),
          ]),
        ],
      ]),
    );
  }

  Widget _stepsCard(CodeColors c, List<Map<String, dynamic>> steps, String now) {
    String txt(Map<String, dynamic> s) {
      for (final k in ['text', 'label', 'say', 'cmd', 'title']) {
        final v = hcS(s[k]);
        if (v.isNotEmpty) return v;
      }
      return hcS(s['k']);
    }

    final rows = steps.where((s) => txt(s).isNotEmpty).toList();
    final last = rows.length > 6 ? rows.sublist(rows.length - 6) : rows;
    return Container(
      decoration: _cardBox(c),
      child: Column(children: [
        for (var i = 0; i < last.length; i++)
          Container(
            constraints: const BoxConstraints(minHeight: 44),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(border: i == 0 ? null : Border(top: BorderSide(color: c.line))),
            child: Row(children: [
              SizedBox(width: 18, child: Center(child: _tick(c, 'done', size: 15))),
              const SizedBox(width: 10),
              Expanded(child: Text(txt(last[i]), maxLines: 2, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14, color: c.ink2))),
            ]),
          ),
        if (now.isNotEmpty)
          Container(
            constraints: const BoxConstraints(minHeight: 44),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(border: last.isEmpty ? null : Border(top: BorderSide(color: c.line))),
            child: Row(children: [
              SizedBox(width: 18, child: Center(child: HcDot(c.accent, size: 7))),
              const SizedBox(width: 10),
              Expanded(child: Text(now, maxLines: 2, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14))),
            ]),
          ),
      ]),
    );
  }
}

/// P2b: the agent's tasks and proof (skip / retry a task that needs her).
class _TasksSheet extends StatefulWidget {
  const _TasksSheet({required this.app, required this.pid, required this.view});
  final Santosh app;
  final String pid;
  final Map<String, dynamic> view;

  @override
  State<_TasksSheet> createState() => _TasksSheetState();
}

class _TasksSheetState extends State<_TasksSheet> {
  late List<Map<String, dynamic>> _tasks = hcList(widget.view['tasks']);
  bool _busy = false;

  Future<void> _act(String tid, String what) async {
    setState(() => _busy = true);
    try {
      final m = await _call(widget.app, 'POST', '$_base/${widget.pid}/tasks/$tid/$what');
      if (!mounted) return;
      final role = hcS(widget.view['role']);
      setState(() => _tasks = hcList(m['tasks']).where((t) => hcS(t['role']) == role).toList());
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final ag = hcM(widget.view['agent']);
    final proof = hcM(widget.view['proof']);
    final done = _tasks.where((t) => hcS(t['state']) == 'done').length;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      HcSheetHead(title: 'My tasks', sub: '${hcS(ag['label'])} · $done of ${_tasks.length} done'),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
        child: Row(children: [
          _tile(c, '${hcInt(ag['pct'])}%', 'my tasks'),
          const SizedBox(width: 8),
          _tile(c, '${ag['share'] ?? 0}%', 'of project'),
          const SizedBox(width: 8),
          _tile(c, _rs(ag['cost_inr']), 'cost'),
        ]),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
        child: Text('${hcInt(proof['prs'])} pull requests joined the project branch · +${hcInt(proof['added'])} lines',
            style: HcType.ui(c, 13, color: c.ink3)),
      ),
      Expanded(
        child: ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          itemCount: _tasks.length,
          separatorBuilder: (_, __) => Divider(height: 1, color: c.line),
          itemBuilder: (_, i) {
            final t = _tasks[i];
            final st = hcS(t['state']);
            final pr = hcM(t['proof']);
            return Container(
              color: (st == 'working' || st == 'queued') ? c.accentTint : null,
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 22, height: 22, child: Center(child: _tick(c, st))),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${hcInt(t['seq'])}. ${hcS(t['title'])}', style: HcType.ui(c, 14, color: st == 'done' ? c.ink3 : c.ink)),
                    const SizedBox(height: 2),
                    Text(
                        st == 'needs'
                            ? hcS(t['why'])
                            : st == 'done' && hcInt(pr['pr']) > 0
                                ? 'PR #${hcInt(pr['pr'])} · ${hcS(pr['ci'])}'
                                : 'Sprint ${hcInt(t['sprint'])} · ${_stateWord(st)}',
                        style: HcType.ui(c, 12, color: st == 'needs' ? c.amber : c.ink4)),
                    if (st == 'needs' || st == 'failed')
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Wrap(spacing: 8, children: [
                          HcOutlineButton(label: 'Start again', height: 40, size: 14, onTap: _busy ? null : () => _act(hcS(t['id']), 'retry')),
                          HcOutlineButton(label: 'Skip', height: 40, size: 14, onTap: _busy ? null : () => _act(hcS(t['id']), 'skip')),
                        ]),
                      ),
                  ]),
                ),
                if (hcS(t['dev_task_id']).isNotEmpty)
                  HcIconButton(
                      icon: Icons.open_in_new_rounded,
                      label: 'Open its session',
                      size: 18,
                      onTap: () => devOpenSession(Navigator.of(context), widget.app, hcS(t['dev_task_id']))),
              ]),
            );
          },
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        child: Text('Tap a session to see its proof · merging into your main branch is always your tap',
            textAlign: TextAlign.center, style: HcType.ui(c, 12, color: c.ink4)),
      ),
    ]);
  }

  Widget _tile(CodeColors c, String big, String small) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: _cardBox(c),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(big, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.mono(c, 17, color: c.ink)),
            const SizedBox(height: 2),
            Text(small, style: HcType.ui(c, 12, color: c.ink4)),
          ]),
        ),
      );
}

// ================================================================================================== gates
class AutoGatesPage extends StatefulWidget {
  const AutoGatesPage({super.key, required this.app, required this.pid});
  final Santosh app;
  final String pid;

  @override
  State<AutoGatesPage> createState() => _AutoGatesPageState();
}

class _AutoGatesPageState extends State<AutoGatesPage> {
  List<Map<String, dynamic>>? _g;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.call('GET', '$_base/${widget.pid}/gates', timeout: const Duration(minutes: 1));
      if (mounted) setState(() => _g = hcList(r));
    } catch (e) {
      if (mounted) {
        setState(() => _g ??= const []);
        hcSay(context, '$e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final g = _g;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const _Head(title: 'Your gates', sub: 'Every gate waits for your tap'),
          Expanded(
            child: g == null
                ? _loading(c)
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: g.length,
                    separatorBuilder: (_, __) => Divider(height: 1, color: c.line),
                    itemBuilder: (_, i) {
                      final x = g[i];
                      final st = hcS(x['state']);
                      final n = hcInt(x['n']);
                      return InkWell(
                        onTap: st == 'wait'
                            ? null
                            : () => Navigator.of(context)
                                .push(MaterialPageRoute<void>(builder: (_) => AutoGatePage(app: widget.app, pid: widget.pid, gid: hcS(x['id']))))
                                .then((_) => _load()),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(minHeight: 56),
                          child: Row(children: [
                            SizedBox(width: 36, child: Text(hcS(x['code']), style: HcType.mono(c, 13, color: st == 'now' ? c.amber : c.ink4))),
                            Expanded(
                              child: Text(
                                  hcS(x['name']) + (hcS(x['code']) == 'G4' && n > 0 ? ' · sprint $n' : hcS(x['code']) == 'G5' && n > 0 ? ' · CR-$n' : ''),
                                  style: HcType.ui(c, 15, weight: st == 'now' ? FontWeight.w600 : FontWeight.w400)),
                            ),
                            if (st == 'approved') Icon(Icons.check_rounded, size: 18, color: c.green),
                            if (st == 'now') Text('now', style: HcType.ui(c, 13, color: c.amber)),
                            if (st == 'wait') Text(hcS(x['when']), style: HcType.ui(c, 12, color: c.ink4)),
                            if (st == 'changes') Text('changes asked', style: HcType.ui(c, 12, color: c.ink3)),
                          ]),
                        ),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }
}

class AutoGatePage extends StatefulWidget {
  const AutoGatePage({super.key, required this.app, required this.pid, required this.gid});
  final Santosh app;
  final String pid;
  final String gid;

  @override
  State<AutoGatePage> createState() => _AutoGatePageState();
}

class _AutoGatePageState extends State<AutoGatePage> {
  Map<String, dynamic>? _g;
  final _note = TextEditingController();
  bool _busy = false;

  String get _path => '$_base/${widget.pid}/gates/${widget.gid}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final g = await _call(widget.app, 'GET', _path);
      if (mounted) setState(() => _g = g);
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  Future<void> _decide(bool yes) async {
    if (!yes && _note.text.trim().isEmpty) {
      hcSay(context, 'Write what should change.');
      return;
    }
    setState(() => _busy = true);
    try {
      await _call(widget.app, 'POST', '$_path/decide', body: {'yes': yes, 'hash': hcS(_g?['hash']), 'note': _note.text.trim()});
      if (mounted) Navigator.maybePop(context);
    } catch (e) {
      if (mounted) {
        hcSay(context, '$e');
        await _load();
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _merge(Map<String, dynamic> pr) async {
    final ci = hcS(pr['ci']);
    final red = ci.toLowerCase().contains('fail') || ci.toLowerCase().contains('chal');
    String reason = '';
    if (red) {
      final ctl = TextEditingController();
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) {
          final c = CodeColors.of(d);
          return AlertDialog(
            backgroundColor: c.sheet,
            title: Text('CI is not green', style: HcType.ui(c, 18, weight: FontWeight.w600)),
            content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(ci, style: HcType.ui(c, 14, color: c.ink3)),
              const SizedBox(height: 10),
              TextField(
                controller: ctl,
                style: HcType.ui(c, 15),
                cursorColor: c.accent,
                decoration: InputDecoration(hintText: 'Why merge anyway?', hintStyle: HcType.ui(c, 15, color: c.ink5)),
              ),
            ]),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: Text('Cancel', style: HcType.ui(c, 15, color: c.ink3))),
              TextButton(onPressed: () => Navigator.pop(d, true), child: Text('Merge', style: HcType.ui(c, 15, color: c.accentInk))),
            ],
          );
        },
      );
      reason = ctl.text.trim();
      ctl.dispose();
      if (ok != true) return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      await _call(widget.app, 'POST', '$_base/${widget.pid}/golive/${hcInt(pr['index'])}/merge', body: {'sha': hcS(pr['sha']), 'reason': reason});
      if (mounted) hcSay(context, 'Merged into ${hcS(pr['base'])}.');
      await _load();
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final g = _g;
    final code = hcS(g?['code']);
    final n = hcInt(g?['n']);
    final now = hcS(g?['state']) == 'now';
    final title = g == null ? 'Gate' : '$code · ${hcS(g['name'])}${code == 'G4' ? ' · sprint $n' : ''}';
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(title: title, sub: hcS(g?['means'])),
          Expanded(
            child: g == null
                ? _loading(c)
                : ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 16), children: [
                    ..._body(c, code, hcM(g['body']), g),
                    if (hcS(g['note']).isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Text('Your note: ${hcS(g['note'])}', style: HcType.ui(c, 13, color: c.ink3)),
                    ],
                  ]),
          ),
          if (now)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                TextField(
                  controller: _note,
                  minLines: 1,
                  maxLines: 3,
                  style: HcType.ui(c, 15),
                  cursorColor: c.accent,
                  decoration: InputDecoration(
                    hintText: 'Anything to change? (needed for Ask for changes)',
                    hintStyle: HcType.ui(c, 14, color: c.ink5),
                    filled: true,
                    fillColor: c.field,
                    enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
                    focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
                  ),
                ),
                const SizedBox(height: 10),
                HcCreamButton(label: _approveLabel(code, n), busy: _busy, onTap: _busy ? null : () => _decide(true)),
                const SizedBox(height: 8),
                HcOutlineButton(label: 'Ask for changes', onTap: _busy ? null : () => _decide(false)),
                const SizedBox(height: 8),
                Text('Your tap is the approval. Nothing reaches your main branch without G7 and its merge tap.',
                    textAlign: TextAlign.center, style: HcType.ui(c, 12, color: c.ink4)),
              ]),
            ),
        ]),
      ),
    );
  }

  String _approveLabel(String code, int n) => const {
        'G1': 'Approve the scope',
        'G2': 'Approve the design',
        'G3': 'Approve the plan and start',
        'G5': 'Approve the change',
        'G6': 'Sign off UAT',
        'G7': 'Approve go-live',
        'G8': 'Accept the handover',
      }[code] ??
      (code == 'G4' ? 'Approve sprint $n' : 'Approve');

  Widget _section(CodeColors c, String title, List<Widget> rows) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: _cardBox(c),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: HcType.ui(c, 15, weight: FontWeight.w600)),
            const SizedBox(height: 8),
            ...rows,
          ]),
        ),
      );

  Widget _line(CodeColors c, String text, {Color? color, bool tick = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (tick) ...[Padding(padding: const EdgeInsets.only(top: 2), child: Icon(Icons.check_rounded, size: 15, color: c.green)), const SizedBox(width: 8)],
          Expanded(child: Text(text, style: HcType.ui(c, 14, color: color ?? c.ink2, height: 1.4))),
        ]),
      );

  List<Widget> _body(CodeColors c, String code, Map<String, dynamic> b, Map<String, dynamic> g) {
    final out = <Widget>[];
    if (code == 'G1') {
      out.add(Text(hcS(b['title']), style: HcType.serif(c, 22, weight: FontWeight.w500)));
      out.add(const SizedBox(height: 6));
      out.add(Text(hcS(b['summary']), style: HcType.ui(c, 14, color: c.ink3, height: 1.45)));
      out.add(const SizedBox(height: 12));
      out.add(Text('${hcInt(b['stories'])} stories · ${hcInt(b['tasks'])} tasks · ${hcInt(b['weeks'])} weeks · cap ${_rs(b['cap_inr'])}',
          style: HcType.mono(c, 13, color: c.ink2)));
      out.add(const SizedBox(height: 12));
      out.add(_section(c, 'What will be built', [
        for (final s in hcList(b['scope'])) _line(c, '${hcS(s['title'])} · ${hcInt(s['stories'])} stories'),
      ]));
      if (hcList(b['out']).isNotEmpty || (b['out'] is List && (b['out'] as List).isNotEmpty)) {
        out.add(_section(c, 'Not in this project', [for (final x in (b['out'] as List? ?? const [])) _line(c, '$x')]));
      }
      if (hcS(b['done_when']).isNotEmpty) out.add(_section(c, 'Done when', [_line(c, hcS(b['done_when']))]));
      if (b['assumptions'] is List && (b['assumptions'] as List).isNotEmpty) {
        out.add(_section(c, 'Assumptions', [for (final x in b['assumptions'] as List) _line(c, '$x', color: c.amber)]));
      }
      out.add(_section(c, 'The team', [
        for (final t in hcList(b['team'])) _line(c, '${hcS(t['label'])}${hcInt(t['tasks']) > 0 ? ' · ${hcInt(t['tasks'])} tasks' : ''}'),
      ]));
    } else if (code == 'G2') {
      if (hcS(b['stack']).isNotEmpty) out.add(_section(c, 'Stack', [_line(c, hcS(b['stack']))]));
      out.add(_section(c, 'Architecture', [for (final x in (b['architecture'] as List? ?? const [])) _line(c, '$x')]));
      out.add(_section(c, 'Data', [
        for (final d in hcList(b['data'])) _line(c, '${hcS(d['name'])}: ${(d['fields'] as List? ?? const []).join(', ')}'),
      ]));
      out.add(_section(c, 'Screens', [for (final s in hcList(b['screens'])) _line(c, '${hcS(s['name'])} (${hcS(s['for'])}): ${hcS(s['shows'])}')]));
      out.add(_section(c, 'API', [for (final x in (b['api'] as List? ?? const [])) _line(c, '$x')]));
      out.add(_section(c, 'Risks', [for (final r in hcList(b['risks'])) _line(c, '${hcS(r['risk'])}: ${hcS(r['plan'])}')]));
    } else if (code == 'G3') {
      out.add(Text('${hcInt(b['tasks'])} tasks · ${hcInt(b['sprints'])} sprints · about ${hcInt(b['weeks'])} weeks',
          style: HcType.serif(c, 20, weight: FontWeight.w500)));
      out.add(const SizedBox(height: 12));
      out.add(_section(c, 'Sprints', [for (final s in hcList(b['per_sprint'])) _line(c, 'Sprint ${hcInt(s['sprint'])}: ${hcInt(s['tasks'])} tasks')]));
      out.add(_section(c, 'Cost', [
        _line(c, 'Estimate ${_rs(b['est_inr'])}, cost cap ${_rs(b['cap_inr'])}'),
        _line(c, hcS(b['est_note']), color: c.ink4),
      ]));
      out.add(_section(c, 'How work joins', [_line(c, 'Project branch ${hcS(b['branch'])}'), _line(c, hcS(b['merge_rule']), color: c.ink3)]));
      out.add(_section(c, 'The team', [for (final t in hcList(b['team'])) _line(c, '${hcS(t['label'])} · ${hcInt(t['tasks'])} tasks')]));
    } else if (code == 'G4') {
      out.add(Text('Sprint ${hcInt(b['sprint'])} of ${hcInt(b['of'])}', style: HcType.serif(c, 20, weight: FontWeight.w500)));
      out.add(const SizedBox(height: 4));
      out.add(Text('On the project branch ${hcS(b['branch'])}', style: HcType.mono(c, 13, color: c.ink3)));
      out.add(const SizedBox(height: 12));
      out.add(_section(c, 'What was built', [
        for (final t in hcList(b['done']))
          _line(c, '${hcS(t['title'])} · ${hcS(t['role'])}${hcInt(t['pr']) > 0 ? ' · PR #${hcInt(t['pr'])}' : ''}${hcS(t['ci']).isNotEmpty ? ' · ${hcS(t['ci'])}' : ''}',
              tick: true),
      ]));
    } else if (code == 'G5') {
      out.add(Text('${hcS(b['cr'])}: ${hcS(b['title'])}', style: HcType.serif(c, 20, weight: FontWeight.w500)));
      out.add(const SizedBox(height: 8));
      out.add(Text(hcS(b['detail']), style: HcType.ui(c, 14, color: c.ink2, height: 1.45)));
      out.add(const SizedBox(height: 12));
      out.add(_section(c, 'Price', [
        _line(c, 'About ${hcInt(b['minutes'])} minutes of ${hcS(b['role'])} · ${_rs(b['cost_inr'])} · ${hcInt(b['tests'])} tests'),
        _line(c, hcS(b['says']), color: c.ink4),
      ]));
    } else if (code == 'G6') {
      out.add(Text(hcS(b['says']), style: HcType.ui(c, 15, height: 1.45)));
      out.add(const SizedBox(height: 12));
      out.add(_section(c, '${hcInt(b['tasks_done'])} tasks done', [
        for (final t in hcList(b['proof'])) _line(c, '${hcS(t['title'])}${hcInt(t['pr']) > 0 ? ' · PR #${hcInt(t['pr'])}' : ''}', tick: true),
      ]));
    } else if (code == 'G7') {
      out.add(Text(hcS(b['says']), style: HcType.ui(c, 15, height: 1.45)));
      out.add(const SizedBox(height: 12));
      final prs = hcList(g['golive']);
      if (prs.isNotEmpty) {
        out.add(_section(c, 'Go-live pull requests', [
          for (final pr in prs)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${hcS(pr['repo'])} · PR #${hcInt(pr['pr'])} into ${hcS(pr['base'])}', style: HcType.mono(c, 13)),
                if (hcS(pr['ci']).isNotEmpty) Text(hcS(pr['ci']), style: HcType.ui(c, 13, color: c.ink3)),
                const SizedBox(height: 6),
                if (hcS(pr['state']) == 'merged')
                  Text('Merged', style: HcType.ui(c, 14, color: c.green))
                else if (hcS(pr['state']) == 'open' && hcS(pr['sha']).isNotEmpty)
                  HcCreamButton(label: 'Merge into ${hcS(pr['base'])}', height: 44, size: 15, onTap: _busy ? null : () => _merge(pr))
                else if (hcS(pr['error']).isNotEmpty)
                  Text(hcS(pr['error']), style: HcType.ui(c, 13, color: c.red)),
              ]),
            ),
        ]));
      } else {
        out.add(_section(c, 'Repositories', [for (final r in (b['repos'] as List? ?? const [])) _line(c, '$r · from ${hcS(b['branch'])}')]));
      }
    } else if (code == 'G8') {
      out.add(_section(c, 'Handover pack', [
        for (final t in hcList(b['docs'])) _line(c, '${hcS(t['title'])}${hcInt(t['pr']) > 0 ? ' · PR #${hcInt(t['pr'])}' : ''}', tick: true),
      ]));
      out.add(_section(c, 'Go-live', [
        for (final pr in hcList(b['golive'])) _line(c, '${hcS(pr['repo'])} · PR #${hcInt(pr['pr'])} · ${hcS(pr['state'])}'),
      ]));
    }
    return out;
  }
}

// ================================================================================================== P5 / intake
class AutoIntakePage extends StatefulWidget {
  const AutoIntakePage({super.key, required this.app, required this.pid});
  final Santosh app;
  final String pid;

  @override
  State<AutoIntakePage> createState() => _AutoIntakePageState();
}

class _AutoIntakePageState extends State<AutoIntakePage> {
  Map<String, dynamic>? _v;
  final _ans = TextEditingController();
  bool _busy = false;
  Timer? _t;

  String get _path => '$_base/${widget.pid}';

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 10), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    _ans.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final v = await _call(widget.app, 'GET', '$_path/intake');
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted && _v == null) hcSay(context, '$e');
    }
  }

  Future<void> _do(Future<Map<String, dynamic>> Function() fn) async {
    setState(() => _busy = true);
    try {
      final v = await fn();
      if (!mounted) return;
      if (v['sections'] != null) setState(() => _v = v);
      final w = hcS(v['warn']);
      if (w.isNotEmpty) hcSay(context, w);
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _answer(String key, String value) async {
    if (value.trim().isEmpty) return;
    await _do(() => _call(widget.app, 'PUT', '$_path/intake/$key', body: {'value': value.trim()}));
    _ans.clear();
  }

  Future<void> _confirm(String key, String pick) => _do(() => _call(widget.app, 'POST', '$_path/intake/$key/confirm', body: {'pick': pick}));

  Future<void> _link() async {
    setState(() => _busy = true);
    try {
      final r = await _call(widget.app, 'POST', '$_path/client-link', body: {'on': true});
      if (!mounted) return;
      final url = hcS(r['url']);
      await hcSheet<void>(context, (sheet) {
        final c = CodeColors.of(sheet);
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const HcSheetHead(title: 'Client link', sub: 'No login for the client. Works 30 days, only for this project.'),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: _cardBox(c, fill: c.field),
              child: SelectableText(url, style: HcType.mono(c, 13)),
            ),
            const SizedBox(height: 8),
            Text(hcS(r['note']), style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
            const SizedBox(height: 12),
            HcCreamButton(
                label: 'Copy link',
                icon: Icons.copy_rounded,
                onTap: () {
                  Clipboard.setData(ClipboardData(text: url));
                  hcSay(sheet, 'Copied.');
                }),
          ]),
        );
      });
      await _load();
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _review() async {
    setState(() => _busy = true);
    try {
      await _call(widget.app, 'POST', '$_path/review', body: {'note': ''});
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute<void>(builder: (_) => AutoProjectPage(app: widget.app, id: widget.pid)));
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final v = _v;
    final got = hcInt(v?['answered']);
    final of = hcInt(v?['of']);
    final link = hcM(v?['client_link']);
    final next = hcM(v?['next']);
    final found = <Map<String, dynamic>>[
      for (final s in hcList(v?['sections']))
        for (final f in hcList(s['fields']))
          if (hcS(f['state']) == 'found' || hcS(f['state']) == 'conflict') f,
    ];
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(
            title: 'Client intake',
            sub: '$got of $of${link['on'] == true ? ' · link sent' : ''}${hcS(link['signed']).isNotEmpty ? ' · client signed off' : ''}',
            trailing: [
              HcIconButton(
                  icon: Icons.cloud_outlined,
                  label: 'Environments',
                  onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => AutoEnvPage(app: widget.app, pid: widget.pid)))),
            ],
          ),
          Expanded(
            child: v == null
                ? _loading(c)
                : RefreshIndicator(
                    color: c.accent,
                    onRefresh: _load,
                    child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 16), children: [
                      _Bar(of == 0 ? 0 : 100 * got / of, height: 6),
                      const SizedBox(height: 14),
                      if (next.isNotEmpty) _asks(c, next),
                      if (found.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        Text('Check what was found', style: HcType.ui(c, 15, weight: FontWeight.w600)),
                        const SizedBox(height: 8),
                        for (final f in found) ...[_foundCard(c, f), const SizedBox(height: 8)],
                      ],
                      const SizedBox(height: 16),
                      Text('Sections', style: HcType.ui(c, 15, weight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      Container(
                        decoration: _cardBox(c),
                        child: Column(children: [
                          for (final s in hcList(v['sections']))
                            Container(
                              constraints: const BoxConstraints(minHeight: 48),
                              padding: const EdgeInsets.symmetric(horizontal: 14),
                              decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
                              child: Row(children: [
                                SizedBox(
                                    width: 20,
                                    child: Center(child: _tick(c, hcInt(s['done']) >= hcInt(s['of']) ? 'done' : 'todo'))),
                                const SizedBox(width: 10),
                                Expanded(child: Text(hcS(s['name']), style: HcType.ui(c, 15))),
                                Text('${hcInt(s['done'])}/${hcInt(s['of'])}', style: HcType.mono(c, 13, color: c.ink4)),
                              ]),
                            ),
                        ]),
                      ),
                      const SizedBox(height: 16),
                      Text('Sources', style: HcType.ui(c, 15, weight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      for (final s in hcList(v['sources']))
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(children: [
                            Expanded(child: Text(hcS(s['name']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14))),
                            Text(
                                hcS(s['status']) == 'reading'
                                    ? 'Reading'
                                    : hcS(s['status']) == 'failed'
                                        ? 'Could not read'
                                        : '${hcInt(s['answers'])} answers',
                                style: HcType.ui(c, 13, color: hcS(s['status']) == 'failed' ? c.red : c.ink4)),
                          ]),
                        ),
                      if (hcList(v['sources']).isEmpty)
                        Text('Add documents, recordings or chats from the web console; the Intake agent reads them.',
                            style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
                    ]),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                Expanded(child: HcOutlineButton(label: 'Client link', icon: Icons.link_rounded, onTap: _busy ? null : _link)),
                const SizedBox(width: 8),
                Expanded(
                  child: HcCreamButton(
                      label: 'Send for review', height: 46, size: 15, busy: _busy, onTap: (_busy || v?['can_review'] != true) ? null : _review),
                ),
              ]),
              const SizedBox(height: 8),
              Text('You can send with gaps. Agents that need a missing input wait and ask.',
                  textAlign: TextAlign.center, style: HcType.ui(c, 12, color: c.ink4)),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _asks(CodeColors c, Map<String, dynamic> q) {
    final key = hcS(q['key']);
    final choices = (q['choices'] as List? ?? const []).map((e) => '$e').toList();
    final conflict = hcS(q['state']) == 'conflict';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _cardBox(c),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _Badge('Hoola asks', fill: c.accentTint, ink: c.accentInk),
        const SizedBox(height: 8),
        Text(hcS(q['q']), style: HcType.serif(c, 17, height: 1.4)),
        Text(hcS(q['section']), style: HcType.ui(c, 12, color: c.ink4)),
        const SizedBox(height: 10),
        if (conflict)
          Text('Two sources disagree; settle it below.', style: HcType.ui(c, 13, color: c.amber))
        else ...[
          if (choices.isNotEmpty)
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final ch in choices) HcOutlineButton(label: ch, height: 42, size: 14, onTap: _busy ? null : () => _answer(key, ch)),
            ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _ans,
                minLines: 1,
                maxLines: 4,
                style: HcType.ui(c, 15),
                cursorColor: c.accent,
                decoration: InputDecoration(
                  hintText: choices.isEmpty ? 'Type the answer' : 'Or type my own answer',
                  hintStyle: HcType.ui(c, 15, color: c.ink5),
                  filled: true,
                  fillColor: c.field,
                  enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
                  focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            HcIconButton(icon: Icons.arrow_upward_rounded, label: 'Save answer', color: c.accent, onTap: _busy ? null : () => _answer(key, _ans.text)),
          ]),
        ],
      ]),
    );
  }

  Widget _foundCard(CodeColors c, Map<String, dynamic> f) {
    final key = hcS(f['key']);
    final conflict = hcS(f['state']) == 'conflict';
    final alt = hcM(f['alt']);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _cardBox(c),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(hcS(f['q']), style: HcType.ui(c, 13, color: c.ink4)),
        const SizedBox(height: 4),
        Text(hcS(f['value']), style: HcType.ui(c, 15, weight: FontWeight.w600)),
        Text('From ${hcS(f['source_ref']).isNotEmpty ? hcS(f['source_ref']) : hcS(f['source_label'])}',
            style: HcType.ui(c, 12, color: c.amber)),
        if (conflict) ...[
          const SizedBox(height: 8),
          Text('Other source says: ${hcS(alt['value'])}', style: HcType.ui(c, 15, weight: FontWeight.w600)),
          Text('From ${hcS(alt['source_ref'])}', style: HcType.ui(c, 12, color: c.amber)),
        ],
        const SizedBox(height: 10),
        if (conflict)
          Row(children: [
            Expanded(child: HcOutlineButton(label: 'Keep the first', height: 44, size: 14, onTap: _busy ? null : () => _confirm(key, 'a'))),
            const SizedBox(width: 8),
            Expanded(child: HcOutlineButton(label: 'Take the other', height: 44, size: 14, onTap: _busy ? null : () => _confirm(key, 'b'))),
          ])
        else
          Align(
            alignment: Alignment.centerLeft,
            child: HcCreamButton(label: 'Yes, correct', height: 44, size: 15, onTap: _busy ? null : () => _confirm(key, '')),
          ),
      ]),
    );
  }
}

// ================================================================================================== P4 / environments
class AutoEnvPage extends StatefulWidget {
  const AutoEnvPage({super.key, required this.app, required this.pid});
  final Santosh app;
  final String pid;

  @override
  State<AutoEnvPage> createState() => _AutoEnvPageState();
}

class _AutoEnvPageState extends State<AutoEnvPage> {
  Map<String, dynamic>? _v;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await _call(widget.app, 'GET', '$_base/${widget.pid}/env');
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  Widget _row(CodeColors c, String name, String sub, String state, bool ok) => Container(
        constraints: const BoxConstraints(minHeight: 56),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
        child: Row(children: [
          Container(
            width: 32,
            height: 32,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: c.chip, borderRadius: HoolaRadius.r(8)),
            child: Text(name.isEmpty ? '?' : name.substring(0, 1).toUpperCase(), style: HcType.ui(c, 14, weight: FontWeight.w600)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 15)),
              if (sub.isNotEmpty) Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 12, color: c.ink4)),
            ]),
          ),
          const SizedBox(width: 8),
          Text(state, style: HcType.ui(c, 13, weight: FontWeight.w500, color: ok ? c.green : c.amber)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final v = _v;
    final env = hcM(v?['env']);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(title: 'Attach environments', sub: v == null ? '' : '${hcInt(v['connected'])} of ${hcInt(v['required'])} connected'),
          Expanded(
            child: v == null
                ? _loading(c)
                : ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 16), children: [
                    _Bar(hcInt(v['required']) == 0 ? 0 : 100 * hcInt(v['connected']) / hcInt(v['required']), height: 6),
                    const SizedBox(height: 14),
                    Container(
                      decoration: _cardBox(c),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
                          child: Text('Code and environment', style: HcType.ui(c, 15, weight: FontWeight.w600)),
                        ),
                        _row(c, 'GitHub', 'Branches and pull requests on the project branch', v['github'] == true ? 'Connected' : 'Connect',
                            v['github'] == true),
                        for (final r in hcList(v['repos']))
                          _row(
                              c,
                              hcS(r['repo']),
                              [
                                if (hcS(r['ci']).isNotEmpty) 'CI: ${hcS(r['ci'])}',
                                if ((r['keys'] as List? ?? const []).isNotEmpty) 'Keys for ${(r['keys'] as List).join(', ')}',
                              ].join(' · '),
                              r['added'] == true ? 'Connected' : 'Add in Hoola Code',
                              r['added'] == true),
                        _row(c, hcS(env['name']).isNotEmpty ? hcS(env['name']) : 'Environment', 'Network, variables and setup script',
                            'Set', true),
                      ]),
                    ),
                    if (hcList(v['needed']).isNotEmpty || (v['needed'] is List && (v['needed'] as List).isNotEmpty)) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: _cardBox(c),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('Still needed', style: HcType.ui(c, 15, weight: FontWeight.w600)),
                          const SizedBox(height: 6),
                          for (final x in (v['needed'] as List? ?? const []))
                            Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Text('$x', style: HcType.ui(c, 14, color: c.amber))),
                        ]),
                      ),
                    ],
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: _cardBox(c),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Rules for the agents', style: HcType.ui(c, 15, weight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        for (final x in (v['rules'] as List? ?? const []))
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Padding(padding: const EdgeInsets.only(top: 3), child: Icon(Icons.lock_outline_rounded, size: 14, color: c.ink4)),
                              const SizedBox(width: 8),
                              Expanded(child: Text('$x', style: HcType.ui(c, 14, color: c.ink2, height: 1.4))),
                            ]),
                          ),
                      ]),
                    ),
                    const SizedBox(height: 12),
                    Text(hcS(v['not_connected']), style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
                    const SizedBox(height: 6),
                    Text('${hcInt(v['live_limit'])} Hoola Code sessions run at a time on this server.',
                        style: HcType.ui(c, 13, color: c.ink4)),
                  ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: HcCreamButton(
              label: 'Continue to client intake',
              onTap: v == null
                  ? null
                  : () => Navigator.of(context)
                      .pushReplacement(MaterialPageRoute<void>(builder: (_) => AutoIntakePage(app: widget.app, pid: widget.pid))),
            ),
          ),
        ]),
      ),
    );
  }
}
