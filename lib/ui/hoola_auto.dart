/// v0.947 HOOLA AUTO on the phone (design: claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz, boards P0-P6): a whole client
/// project run by specialist agents on Hoola Code sessions. Home (projects), mission control (phases, needs you,
/// agents, live feed), one agent (its conversation, current session steps, change requests, tasks), a gate (G1-G8, the
/// go-live merge), the intake (Hoola asks, found answers, conflicts, the client link) and the environments.
/// All on the server's /api/auto routes; every gate is her tap carrying the gate's hash.
/// v0.949: add a source on the phone (text, document, recording, repo scan, a connected app), talk to the Intake agent
/// (turn by turn: the phone hears and speaks, the server gets text), and the Monitor after go-live (alerts, Fix it).
library;

import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'chat/hoola_thread.dart';
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
        item('monitor', Icons.notifications_active_outlined, 'Monitor after go-live'),
        item('pause', paused ? Icons.play_arrow_rounded : Icons.pause_rounded, paused ? 'Start the agents again' : 'Pause all agents'),
        const SizedBox(height: 12),
      ]);
    });
    if (!mounted || pick == null) return;
    if (pick == 'intake') _push(AutoIntakePage(app: widget.app, pid: widget.id));
    if (pick == 'env') _push(AutoEnvPage(app: widget.app, pid: widget.id));
    if (pick == 'gates') _push(AutoGatesPage(app: widget.app, pid: widget.id));
    if (pick == 'monitor') _push(AutoMonitorPage(app: widget.app, pid: widget.id));
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
                const SizedBox(height: 10),
                _monitorRow(c, agents),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _monitorRow(CodeColors c, List<Map<String, dynamic>> agents) {
    final mon = agents.firstWhere((a) => hcS(a['role']) == 'monitor', orElse: () => <String, dynamic>{});
    final st = hcS(mon['state']);
    return Material(
      color: c.card,
      borderRadius: HoolaRadius.r(HoolaRadius.card),
      child: InkWell(
        borderRadius: HoolaRadius.r(HoolaRadius.card),
        onTap: () => _push(AutoMonitorPage(app: widget.app, pid: widget.id)),
        child: Container(
          constraints: const BoxConstraints(minHeight: 52),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(borderRadius: HoolaRadius.r(HoolaRadius.card), border: Border.all(color: c.line)),
          child: Row(children: [
            HcDot(autoStateColor(c, st)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Monitor', style: HcType.ui(c, 15, weight: FontWeight.w500)),
                Text(hcS(mon['step']).isNotEmpty ? hcS(mon['step']) : 'Watches the live app after go-live',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: st == 'needs' ? c.amber : c.ink4)),
              ]),
            ),
            Icon(Icons.chevron_right_rounded, color: c.ink4),
          ]),
        ),
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

/// The conversation is the Hoola chat's own thread (lib/ui/chat/hoola_thread.dart): her message the moment she sends,
/// the agent's reply in the reply serif with markdown, landing word by word when it arrives, one working row, and
/// Copy / Read aloud / Share under the newest reply. The task steps, change requests and the question card ride in it.
class _AutoAgentPageState extends State<AutoAgentPage> {
  Map<String, dynamic>? _v;
  Timer? _t;
  final _msg = TextEditingController();
  bool _busy = false;
  int _epoch = 0;                // goes up when her message is answered: a check begun before it never puts the older copy back
  String? _pend;                 // her message just sent, shown until the server's conversation carries it
  String _pendId = '', _pendBase = '';
  DateTime? _sentAt;

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
    super.dispose();
  }

  Future<void> _load() async {
    final was = _epoch;
    try {
      final v = await _call(widget.app, 'GET', _path);
      if (mounted && was == _epoch) setState(() => _v = v);
    } catch (e) {
      if (mounted && _v == null) hcSay(context, '$e');
    }
  }

  /// Her newest message in the server's copy of this conversation ('' = none yet).
  String _lastYou(Map<String, dynamic>? v) {
    var mark = '';
    for (final m in hcList(v?['chat'])) {
      if (hcS(m['who']) == 'you') mark = '${hcS(m['at'])}|${hcS(m['text']).length}';
    }
    return mark;
  }

  Future<void> _send() async {
    final text = _msg.text.trim();
    if (text.isEmpty || _busy) return;
    final base = _lastYou(_v);
    // her message is in the thread the moment she sends
    setState(() {
      _busy = true;
      _pend = text;
      _pendBase = base;
      _sentAt = DateTime.now();
      _pendId = 'p${DateTime.now().microsecondsSinceEpoch}';
    });
    _msg.clear();
    try {
      final v = await _call(widget.app, 'POST', '$_path/message', body: {'text': text});
      if (!mounted) return;
      _epoch++;
      setState(() {
        _v = v;
        _pend = null;
      });
      final w = hcS(v['warn']);
      if (w.isNotEmpty) hcSay(context, w);
    } catch (e) {
      if (!mounted) return;
      await _load();   // did the server write her message down before it failed?
      if (!mounted) return;
      final kept = _lastYou(_v) != base;
      setState(() => _pend = null);
      if (!kept && _msg.text.trim().isEmpty) {
        // it did not go: her words go back into the box
        _msg.text = text;
        _msg.selection = TextSelection.collapsed(offset: text.length);
      }
      hcSay(context, '$e');
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
                : HoolaThreadView(
                    messages: _thread(c, v, label),
                    working: _busy,
                    since: _sentAt,
                    name: label,
                    onAloud: widget.app.readAloud,
                    onToast: (m) => hcSay(context, m),
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
                    header: Padding(
                      padding: const EdgeInsets.only(bottom: 14),
                      child: Text(hcS(v['does']), style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
                    ),
                  ),
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

  /// The page as one thread: her messages and the agent's replies (a reply's tag and change request right under it),
  /// then the current task's steps, a question the session asks, and the agent's state.
  List<HoolaMsg> _thread(CodeColors c, Map<String, dynamic> v, String label) {
    final ag = hcM(v['agent']);
    final sess = hcM(v['session']);
    final cur = hcM(v['current']);
    final running = sess['running'] == true;
    final steps = hcList(sess['steps']);
    final now = hcS(sess['now']);
    Widget under(Widget w, double gap) => Padding(padding: EdgeInsets.only(bottom: gap), child: w);
    final out = <HoolaMsg>[];
    final used = <String>{};
    for (final m in hcList(v['chat'])) {
      final you = hcS(m['who']) == 'you';
      // a stable name for the message: who said it and when (the server gives no id)
      final base = '${you ? 'y' : 'a'}${hcS(m['at']).isEmpty ? hcS(m['text']).hashCode : hcS(m['at'])}';
      var id = base;
      var i = 1;
      while (!used.add(id)) {
        id = '$base#${i++}';
      }
      out.add(HoolaMsg(id: id, text: hcS(m['text']), mine: you));
      if (you) continue;
      final tag = hcS(m['tag']);
      final ch = hcM(m['change']);
      if (tag.isNotEmpty) out.add(HoolaMsg(id: '$id~tag', text: '', custom: under(_tagChip(c, tag), 18)));
      if (ch.isNotEmpty) out.add(HoolaMsg(id: '$id~cr', text: '', custom: under(_crCard(c, ch), 18)));
    }
    final pend = _pend;
    if (pend != null && _lastYou(v) == _pendBase) out.add(HoolaMsg(id: _pendId, text: pend, mine: true, pending: true));
    if (steps.isNotEmpty || (cur.isNotEmpty && now.isNotEmpty)) {
      out.add(HoolaMsg(
        id: 'task',
        text: '',
        custom: under(
            Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              if (cur.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text('Task ${hcInt(cur['seq'])}: ${hcS(cur['title'])}', style: HcType.ui(c, 14, weight: FontWeight.w600)),
                ),
              if (steps.isNotEmpty) _stepsCard(c, steps),
            ]),
            10),
      ));
    }
    if (hcS(sess['question']).isNotEmpty) {
      out.add(HoolaMsg(
        id: 'question',
        text: '',
        custom: under(
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
            10),
      ));
    }
    if (cur.isNotEmpty && hcS(cur['state']) == 'needs' && hcS(cur['why']).isNotEmpty) {
      out.add(HoolaMsg(id: 'why', text: '', custom: under(Text(hcS(cur['why']), style: HcType.ui(c, 14, color: c.amber, height: 1.4)), 10)));
    }
    // while the agent's session works: the one working row with the step it is on (the chat's own row shows instead
    // while her message is being answered)
    if (running && !_busy) {
      out.add(HoolaMsg(
        id: 'session-working',
        text: '',
        custom: HoolaWorkingRow(label: now.isEmpty ? 'Working' : now, since: DateTime.tryParse(hcS(ag['since'])), name: label),
      ));
    }
    out.add(HoolaMsg(
      id: 'state',
      text: '',
      custom: Row(children: [
        if (!running) ...[
          HcDot(autoStateColor(c, hcS(ag['state']))),
          const SizedBox(width: 8),
          Expanded(child: Text(_stateWord(hcS(ag['state'])), style: HcType.ui(c, 14, color: c.ink3))),
        ] else
          const Spacer(),
        if (hcS(sess['id']).isNotEmpty)
          TextButton(
            onPressed: () => devOpenSession(Navigator.of(context), widget.app, hcS(sess['id'])),
            child: Text('Open full session', style: HcType.ui(c, 14, color: c.accentInk)),
          ),
      ]),
    ));
    return out;
  }

  Widget _tagChip(CodeColors c, String tag) => Align(
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
      );

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

  Widget _stepsCard(CodeColors c, List<Map<String, dynamic>> steps) {
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
  Timer? _fast;

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
    _fast?.cancel();
    _ans.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final v = await _call(widget.app, 'GET', '$_path/intake');
      if (!mounted) return;
      setState(() => _v = v);
      _fast?.cancel();                       // a source still being read: look again in 3 s, stop when none is
      if (autoAnyReading(hcList(v['sources']))) _fast = Timer(const Duration(seconds: 3), _load);
    } catch (e) {
      if (mounted && _v == null) hcSay(context, '$e');
    }
  }

  Future<void> _addSource() async {
    final added = await hcSheet<bool>(context, (_) => AutoAddSourceSheet(app: widget.app, pid: widget.pid), tall: true);
    if (added == true && mounted) {
      hcSay(context, 'Added. The Intake agent is reading it.');
      await _load();
    }
  }

  void _talk() => Navigator.of(context)
      .push(MaterialPageRoute<void>(builder: (_) => AutoTalkPage(app: widget.app, pid: widget.pid)))
      .then((_) => _load());

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
                      const SizedBox(height: 12),
                      HcOutlineButton(label: 'Talk to the Intake agent', icon: Icons.mic_none_rounded, onTap: _talk),
                      const SizedBox(height: 12),
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
                      Row(children: [
                        Expanded(child: Text('Sources', style: HcType.ui(c, 15, weight: FontWeight.w600))),
                        ConstrainedBox(constraints: const BoxConstraints(maxWidth: 170), child: HcOutlineButton(label: 'Add source', icon: Icons.add_rounded, height: 40, size: 14, onTap: _addSource)),
                      ]),
                      const SizedBox(height: 6),
                      for (final s in hcList(v['sources']))
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Row(children: [
                              Expanded(child: Text(hcS(s['name']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14))),
                              Text(autoSourceState(s),
                                  style: HcType.ui(c, 13, color: hcS(s['status']) == 'failed' ? c.red : c.ink4)),
                            ]),
                            if (hcS(s['status']) == 'failed' && hcS(s['note']).isNotEmpty)
                              Text(hcS(s['note']), maxLines: 2, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 12, color: c.ink4)),
                          ]),
                        ),
                      if (hcList(v['sources']).isEmpty)
                        Text('Add a document, a recording, a pasted chat, a repo scan or an app; the Intake agent reads it.',
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

// ================================================================================================== v0.949 add a source
/// The kinds of source she can add from the phone: key, icon, label, line.
const List<(String, IconData, String, String)> autoSourceKinds = [
  ('text', Icons.chat_bubble_outline_rounded, 'Paste email or chat', 'An email, or a WhatsApp or Slack chat'),
  ('doc', Icons.description_outlined, 'Document', 'PDF, Word, text, Excel, PowerPoint or Markdown'),
  ('recording', Icons.mic_none_rounded, 'Recording', 'A call or a meeting: mp3, m4a, wav, ogg, webm or mp4'),
  ('repo', Icons.code_rounded, 'Repo scan', 'Reads the README and the file list of a repo'),
  ('app', Icons.apps_rounded, 'From an app', 'Jira, Linear, Slack, Notion, Figma and more'),
];
const int autoMaxSourceBytes = 12 * 1024 * 1024;
const List<String> autoDocTypes = ['pdf', 'docx', 'txt', 'xlsx', 'pptx', 'md'];
const List<String> autoAudioTypes = ['mp3', 'm4a', 'wav', 'ogg', 'webm', 'mp4'];

/// A source row's state in words.
String autoSourceState(Map<String, dynamic> s) {
  switch (hcS(s['status'])) {
    case 'reading':
      return 'Reading';
    case 'failed':
      return 'Could not read';
    default:
      final n = hcInt(s['answers']);
      return n == 1 ? '1 answer' : '$n answers';
  }
}

bool autoAnyReading(List<Map<String, dynamic>> sources) => sources.any((s) => hcS(s['status']) == 'reading');

/// "Files up to 12 MB" check: '' when the size is fine, else what to say.
String autoSizeProblem(int bytes) =>
    bytes > autoMaxSourceBytes ? 'Files up to 12 MB. This one is ${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB.' : '';

/// The first screen of the add-source sheet: one row per kind.
class AutoSourceKindList extends StatelessWidget {
  const AutoSourceKindList({super.key, required this.onPick});
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Container(
      decoration: _cardBox(c),
      child: Column(children: [
        for (var i = 0; i < autoSourceKinds.length; i++)
          InkWell(
            onTap: () => onPick(autoSourceKinds[i].$1),
            child: Container(
              constraints: const BoxConstraints(minHeight: 60),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(border: i == 0 ? null : Border(top: BorderSide(color: c.line))),
              child: Row(children: [
                Icon(autoSourceKinds[i].$2, color: c.ink2),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(autoSourceKinds[i].$3, style: HcType.ui(c, 15, weight: FontWeight.w500)),
                    Text(autoSourceKinds[i].$4, style: HcType.ui(c, 12, color: c.ink4)),
                  ]),
                ),
                Icon(Icons.chevron_right_rounded, color: c.ink4),
              ]),
            ),
          ),
      ]),
    );
  }
}

class AutoAddSourceSheet extends StatefulWidget {
  const AutoAddSourceSheet({super.key, required this.app, required this.pid});
  final Santosh app;
  final String pid;

  @override
  State<AutoAddSourceSheet> createState() => _AutoAddSourceSheetState();
}

class _AutoAddSourceSheetState extends State<AutoAddSourceSheet> {
  String _kind = '';
  bool _busy = false;
  final _name = TextEditingController();
  final _text = TextEditingController();
  final _what = TextEditingController();
  List<String> _repos = const [];
  String _repo = '';
  List<Map<String, dynamic>> _apps = const [];
  bool _appsLoaded = false;
  Map<String, dynamic> _app = const {};

  @override
  void dispose() {
    _name.dispose();
    _text.dispose();
    _what.dispose();
    super.dispose();
  }

  Future<void> _post(Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      await _call(widget.app, 'POST', '$_base/${widget.pid}/sources', body: body);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        hcSay(context, '$e');
      }
    }
  }

  Future<void> _pickFile(String kind) async {
    final res = await FilePicker.platform
        .pickFiles(withData: true, type: FileType.custom, allowedExtensions: kind == 'doc' ? autoDocTypes : autoAudioTypes);
    if (!mounted || res == null || res.files.isEmpty) return;
    final f = res.files.first;
    final bytes = f.bytes;
    if (bytes == null) {
      hcSay(context, 'The file could not be read on this phone. Try another one.');
      return;
    }
    final big = autoSizeProblem(bytes.length);
    if (big.isNotEmpty) {
      hcSay(context, big);
      return;
    }
    await _post({'kind': kind, 'name': f.name, 'data': base64Encode(bytes)});
  }

  Future<void> _loadRepos() async {
    try {
      final v = await _call(widget.app, 'GET', '$_base/${widget.pid}/env');
      if (!mounted) return;
      setState(() {
        _repos = [for (final r in hcList(v['repos'])) if (hcS(r['repo']).isNotEmpty) hcS(r['repo'])];
        if (_repos.isNotEmpty) _repo = _repos.first;
      });
    } catch (_) {}
  }

  Future<void> _loadApps() async {
    try {
      final v = await _call(widget.app, 'GET', '/api/auto/apps?use=intake');
      if (mounted) setState(() => _apps = hcList(v['apps']));
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _appsLoaded = true);
    }
  }

  Future<void> _connect(Map<String, dynamic> a) async {
    try {
      final r = await _call(widget.app, 'POST', '/api/auto/apps/${hcS(a['key'])}/connect');
      final url = hcS(r['url']);
      if (url.isNotEmpty) {
        await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
        if (mounted) hcSay(context, 'Sign in, then tap Refresh.');
      } else if (mounted) {
        hcSay(context, hcS(r['say']).isNotEmpty ? hcS(r['say']) : 'Already connected.');
      }
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  void _choose(String kind) {
    if (kind == 'doc' || kind == 'recording') {
      _pickFile(kind);
      return;
    }
    setState(() => _kind = kind);
    if (kind == 'repo') _loadRepos();
    if (kind == 'app') _loadApps();
  }

  Widget _field(CodeColors c, TextEditingController ctl, String hint, {int lines = 1}) => TextField(
        controller: ctl,
        minLines: lines,
        maxLines: lines == 1 ? 1 : 12,
        style: HcType.ui(c, 15),
        cursorColor: c.accent,
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: HcType.ui(c, 15, color: c.ink5),
          filled: true,
          fillColor: c.field,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
          focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
        ),
      );

  Widget _body(CodeColors c) {
    switch (_kind) {
      case 'text':
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _field(c, _name, 'Name, e.g. Email from Dr. Sai'),
          const SizedBox(height: 10),
          _field(c, _text, 'Paste the email or chat here', lines: 8),
          const SizedBox(height: 12),
          HcCreamButton(
              label: 'Add source',
              busy: _busy,
              onTap: _busy ? null : () => _post({'kind': 'text', 'name': _name.text.trim(), 'text': _text.text})),
        ]);
      case 'repo':
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Hoola reads the README and the file list (read only).', style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
          const SizedBox(height: 8),
          for (final r in _repos)
            InkWell(
              onTap: () => setState(() => _repo = r),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 48),
                child: Row(children: [
                  Icon(_repo == r ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                      color: _repo == r ? c.accent : c.ink4),
                  const SizedBox(width: 10),
                  Expanded(child: Text(r, style: HcType.mono(c, 14))),
                ]),
              ),
            ),
          if (_repos.isEmpty) Text('The project\'s first repository is scanned.', style: HcType.ui(c, 13, color: c.ink4)),
          const SizedBox(height: 12),
          HcCreamButton(label: 'Scan the repo', busy: _busy, onTap: _busy ? null : () => _post({'kind': 'repo', 'name': _repo})),
        ]);
      case 'app':
        if (_app.isNotEmpty) {
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('What should Hoola read from ${hcS(_app['name'])}?', style: HcType.ui(c, 15, weight: FontWeight.w600)),
            const SizedBox(height: 8),
            _field(c, _what, hcS(_app['hint'])),
            const SizedBox(height: 8),
            Text('One read, read only. What comes back is data for the Intake agent.',
                style: HcType.ui(c, 12, color: c.ink4, height: 1.4)),
            const SizedBox(height: 12),
            HcCreamButton(
                label: 'Add source',
                busy: _busy,
                onTap: _busy ? null : () => _post({'kind': 'app', 'app': hcS(_app['key']), 'what': _what.text.trim()})),
          ]);
        }
        if (!_appsLoaded) return Padding(padding: const EdgeInsets.all(20), child: _loading(c));
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Container(
            decoration: _cardBox(c),
            child: Column(children: [
              for (var i = 0; i < _apps.length; i++) _appRow(c, _apps[i], i == 0),
            ]),
          ),
          const SizedBox(height: 10),
          HcOutlineButton(label: 'Refresh', icon: Icons.refresh_rounded, onTap: _loadApps),
        ]);
      default:
        return AutoSourceKindList(onPick: _choose);
    }
  }

  Widget _appRow(CodeColors c, Map<String, dynamic> a, bool first) {
    final st = hcS(a['state']);
    final ready = st == 'ready';
    final canLink = st == 'needs_link' || st == 'needs_key';
    return Container(
      constraints: const BoxConstraints(minHeight: 56),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(border: first ? null : Border(top: BorderSide(color: c.line))),
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(hcS(a['name']), style: HcType.ui(c, 15, weight: FontWeight.w500)),
            Text(hcS(a['say']), style: HcType.ui(c, 12, color: ready ? c.green : c.ink4)),
          ]),
        ),
        if (ready)
          ConstrainedBox(constraints: const BoxConstraints(maxWidth: 120), child: HcOutlineButton(label: 'Use', height: 38, size: 14, onTap: () => setState(() => _app = a)))
        else if (canLink)
          ConstrainedBox(constraints: const BoxConstraints(maxWidth: 120), child: HcOutlineButton(label: 'Sign in', height: 38, size: 14, onTap: () => _connect(a))),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final title = _kind.isEmpty ? 'Add a source' : autoSourceKinds.firstWhere((k) => k.$1 == _kind).$3;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
        HcSheetHead(
          title: title,
          sub: _kind.isEmpty ? 'The Intake agent reads it and marks where every answer came from' : '',
          trailing: _kind.isEmpty
              ? null
              : HcIconButton(
                  icon: Icons.arrow_back_rounded,
                  label: 'Back',
                  onTap: () => setState(() {
                        if (_app.isNotEmpty) {
                          _app = const {};
                        } else {
                          _kind = '';
                        }
                      })),
        ),
        const SizedBox(height: 12),
        if (_busy && (_kind.isEmpty)) Padding(padding: const EdgeInsets.all(12), child: _loading(c)),
        _body(c),
      ]),
    );
  }
}

// ================================================================================================== v0.949 talk to Intake
class AutoTalkPage extends StatefulWidget {
  const AutoTalkPage({super.key, required this.app, required this.pid});
  final Santosh app;
  final String pid;

  @override
  State<AutoTalkPage> createState() => _AutoTalkPageState();
}

/// The talk is the Hoola chat's own thread (lib/ui/chat/hoola_thread.dart): her line the moment it is heard or sent,
/// one working row while the agent answers, the reply landing word by word with no card, Copy / Read aloud / Share
/// under the newest reply. Speaking and listening are as before.
class _AutoTalkPageState extends State<AutoTalkPage> {
  final _stt = SpeechToText();
  final _tts = FlutterTts();
  final _ctl = TextEditingController();
  final List<Map<String, dynamic>> _msgs = [];
  DateTime? _sentAt;
  bool _sttReady = false, _listening = false, _gotFinal = false, _busy = false, _speak = true, _complete = false;
  bool _waiting = false;         // her turn is with the agent and its reply is not here yet: the working row shows
  String _heard = '', _note = '';
  int _answered = 0, _of = 0;

  @override
  void initState() {
    super.initState();
    _tts.setLanguage('en-IN');
    _tts.setSpeechRate(.48);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _send('', spoken: true);
    });
  }

  @override
  void dispose() {
    _tts.stop();
    _stt.cancel();
    _ctl.dispose();
    super.dispose();
  }

  Future<void> _send(String said, {required bool spoken}) async {
    final words = said.trim();
    setState(() {
      _busy = true;
      _waiting = true;
      _sentAt = DateTime.now();
      if (words.isNotEmpty) _msgs.add({'who': 'you', 'text': words});
      _heard = '';
    });
    try {
      final r = await _call(widget.app, 'POST', '$_base/${widget.pid}/talk', body: {'said': words, 'spoken': spoken});
      if (!mounted) return;
      setState(() {
        _waiting = false;
        _msgs.add({'who': 'agent', 'text': hcS(r['reply']), 'speak': hcS(r['speak']), 'got': hcList(r['got'])});
        _answered = hcInt(r['answered']);
        _of = hcInt(r['of']);
        _complete = r['complete'] == true;
        if (hcS(r['warn']).isNotEmpty) _note = hcS(r['warn']);
      });
      if (_speak && hcS(r['speak']).isNotEmpty) await _tts.speak(hcS(r['speak']));
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _waiting = false;
        });
      }
    }
  }

  Future<void> _mic() async {
    if (_listening) {
      await _stt.stop(); // the final result follows
      return;
    }
    await _tts.stop();
    _sttReady = _sttReady ||
        await _stt.initialize(
          onStatus: (s) {
            if ((s == 'done' || s == 'notListening') && _listening && !_gotFinal) {
              Future.delayed(const Duration(milliseconds: 400), () {
                if (!mounted || !_listening || _gotFinal) return;
                setState(() => _listening = false);
                if (_heard.trim().isNotEmpty) _send(_heard, spoken: true);
              });
            }
          },
          onError: (SpeechRecognitionError e) {
            if (mounted) setState(() => _listening = false);
          },
        );
    if (!mounted) return;
    if (!_sttReady) {
      setState(() => _note = 'Microphone permission is needed to talk. Allow the mic for Hoola in the phone settings, or type below.');
      return;
    }
    _gotFinal = false;
    setState(() {
      _heard = '';
      _listening = true;
      _note = '';
    });
    await _stt.listen(
      localeId: 'en_IN',
      listenFor: const Duration(seconds: 60),
      pauseFor: const Duration(milliseconds: 3500),
      partialResults: true,
      cancelOnError: true,
      onResult: (r) {
        if (!mounted) return;
        setState(() => _heard = r.recognizedWords);
        if (r.finalResult) {
          _gotFinal = true;
          setState(() => _listening = false);
          if (r.recognizedWords.trim().isNotEmpty) _send(r.recognizedWords, spoken: true);
        }
      },
    );
  }

  /// Read aloud under a reply: the same voice that speaks the replies, with the words the server made for speaking.
  Future<void> _aloud(String words) async {
    var say = words;
    for (final m in _msgs) {
      if (hcS(m['text']) == words && hcS(m['speak']).isNotEmpty) say = hcS(m['speak']);
    }
    await _tts.stop();
    await _tts.speak(say);
  }

  /// The talk as a thread: her lines, the agent's replies, and under a reply the answers it took from her words.
  List<HoolaMsg> _thread(CodeColors c) {
    final out = <HoolaMsg>[];
    for (var i = 0; i < _msgs.length; i++) {
      final m = _msgs[i];
      final me = hcS(m['who']) == 'you';
      out.add(HoolaMsg(id: 't$i', text: hcS(m['text']), mine: me));
      final got = hcList(m['got']);
      if (me || got.isEmpty) continue;
      out.add(HoolaMsg(
        id: 't$i~got',
        text: '',
        custom: Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(children: [
            for (final g in got)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Padding(padding: const EdgeInsets.only(top: 2), child: Icon(Icons.check_rounded, size: 14, color: c.green)),
                  const SizedBox(width: 6),
                  Expanded(
                      child: Text('${hcS(g['q'])} ${hcS(g['value'])}',
                          style: HcType.ui(c, 12, color: c.ink3, height: 1.35))),
                ]),
              ),
          ]),
        ),
      ));
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(
            title: 'Talk to the Intake agent',
            sub: _of == 0 ? '' : '$_answered of $_of answered${_complete ? ' · complete' : ''}',
            trailing: [
              HcIconButton(
                  icon: _speak ? Icons.volume_up_rounded : Icons.volume_off_rounded,
                  label: _speak ? 'Speak replies: on' : 'Speak replies: off',
                  onTap: () {
                    setState(() => _speak = !_speak);
                    if (!_speak) _tts.stop();
                  }),
            ],
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
            child: Text('Spoken answers come in as Found - confirm them on the intake list.',
                style: HcType.ui(c, 12, color: c.ink4, height: 1.4)),
          ),
          Expanded(
            child: HoolaThreadView(
              messages: _thread(c),
              working: _waiting,
              since: _sentAt,
              name: 'Intake agent',
              onAloud: _aloud,
              onToast: (m) => hcSay(context, m),
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
            ),
          ),
          if (_note.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
              child: Text(_note, style: HcType.ui(c, 13, color: c.amber, height: 1.4)),
            ),
          if (_listening || _heard.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
              child: Text(_heard.isEmpty ? 'Listening…' : _heard, style: HcType.ui(c, 15, color: c.ink2, height: 1.4)),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Semantics(
                button: true,
                label: _listening ? 'Stop listening' : 'Talk',
                excludeSemantics: true,
                child: Material(
                  color: _listening ? c.accent : c.raised,
                  shape: const CircleBorder(),
                  child: InkWell(
                    customBorder: const CircleBorder(),
                    onTap: _busy ? null : _mic,
                    child: SizedBox(
                      width: 76,
                      height: 76,
                      child: Icon(_listening ? Icons.stop_rounded : Icons.mic_rounded, size: 34, color: _listening ? c.bg : c.ink),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                  child: TextField(
                    controller: _ctl,
                    minLines: 1,
                    maxLines: 4,
                    style: HcType.ui(c, 15),
                    cursorColor: c.accent,
                    decoration: InputDecoration(
                      hintText: 'Or type the answer',
                      hintStyle: HcType.ui(c, 15, color: c.ink5),
                      filled: true,
                      fillColor: c.field,
                      enabledBorder:
                          OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
                      focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                HcIconButton(
                    icon: Icons.arrow_upward_rounded,
                    label: 'Send',
                    color: c.accent,
                    onTap: _busy
                        ? null
                        : () {
                            final t = _ctl.text;
                            if (t.trim().isEmpty) return;
                            _ctl.clear();
                            _tts.stop();
                            _send(t, spoken: false);
                          }),
              ]),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ================================================================================================== v0.949 the Monitor
const List<(int, String)> autoEvery = [(15, '15 min'), (30, '30 min'), (60, '1 hour'), (180, '3 hours'), (360, '6 hours'), (1440, '1 day')];

String autoEveryLabel(int min) => autoEvery.firstWhere((e) => e.$1 == min, orElse: () => (min, '$min min')).$2;

String _alertWord(String s) =>
    const {'open': 'Needs you', 'fixing': 'Fixing', 'dismissed': 'Dismissed', 'resolved': 'Cleared'}[s] ?? s;

/// One problem the Monitor found. onAct('fix' | 'dismiss' | 'reopen'); onOpen(url) for the fix's pull request.
class AutoAlertCard extends StatelessWidget {
  const AutoAlertCard({super.key, required this.alert, required this.onAct, this.onOpen});
  final Map<String, dynamic> alert;
  final ValueChanged<String> onAct;
  final ValueChanged<String>? onOpen;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final st = hcS(alert['state']);
    final fix = hcM(alert['fix']);
    final times = hcInt(alert['times']);
    final edge = st == 'open' ? c.amber : null;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _cardBox(c, edge: edge),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _Badge(_alertWord(st),
              fill: c.chip, ink: st == 'open' ? c.amber : (st == 'resolved' ? c.green : (st == 'fixing' ? c.accentInk : c.ink4))),
          const Spacer(),
          Text(times > 1 ? 'seen $times times' : _at(hcS(alert['first_at'])), style: HcType.ui(c, 12, color: c.ink4)),
        ]),
        const SizedBox(height: 8),
        Text(hcS(alert['title']), style: HcType.ui(c, 15, weight: FontWeight.w600, height: 1.35)),
        if (hcS(alert['detail']).isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(hcS(alert['detail']), maxLines: 4, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink3, height: 1.4)),
        ],
        if (st == 'fixing' && hcS(fix['say']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(hcS(fix['say']), style: HcType.ui(c, 13, color: c.accentInk)),
        ],
        const SizedBox(height: 10),
        if (st == 'open')
          Row(children: [
            Expanded(child: HcCreamButton(label: 'Fix it', height: 44, size: 15, onTap: () => onAct('fix'))),
            const SizedBox(width: 8),
            Expanded(child: HcOutlineButton(label: 'Dismiss', height: 44, size: 14, onTap: () => onAct('dismiss'))),
          ])
        else if (st == 'fixing' && hcS(fix['url']).isNotEmpty && onOpen != null)
          HcOutlineButton(label: 'Open pull request', icon: Icons.open_in_new_rounded, height: 42, size: 14, onTap: () => onOpen!(hcS(fix['url'])))
        else if (st == 'dismissed')
          HcOutlineButton(label: 'Reopen', height: 42, size: 14, onTap: () => onAct('reopen')),
      ]),
    );
  }
}

class AutoMonitorPage extends StatefulWidget {
  const AutoMonitorPage({super.key, required this.app, required this.pid});
  final Santosh app;
  final String pid;

  @override
  State<AutoMonitorPage> createState() => _AutoMonitorPageState();
}

class _AutoMonitorPageState extends State<AutoMonitorPage> {
  Map<String, dynamic>? _v;
  bool _seeded = false, _busy = false, _on = false;
  final _url = TextEditingController();
  int _every = 60;
  final List<(String, TextEditingController)> _feeds = [];
  Timer? _t;

  String get _path => '$_base/${widget.pid}';

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 20), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    _url.dispose();
    for (final f in _feeds) {
      f.$2.dispose();
    }
    super.dispose();
  }

  void _seed(Map<String, dynamic> v) {
    _on = v['on'] == true;
    _url.text = hcS(v['url']);
    _every = hcInt(v['every_min']) == 0 ? 60 : hcInt(v['every_min']);
    for (final f in _feeds) {
      f.$2.dispose();
    }
    _feeds
      ..clear()
      ..addAll([for (final f in hcList(v['feeds'])) (hcS(f['app']), TextEditingController(text: hcS(f['what'])))]);
    _seeded = true;
  }

  Future<void> _load() async {
    try {
      final v = await _call(widget.app, 'GET', '$_path/watch');
      if (!mounted) return;
      setState(() {
        _v = v;
        if (!_seeded) _seed(v);
      });
    } catch (e) {
      if (mounted && _v == null) hcSay(context, '$e');
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() fn, {String done = ''}) async {
    setState(() => _busy = true);
    try {
      final v = await fn();
      if (!mounted) return;
      setState(() => _v = v);
      if (done.isNotEmpty) hcSay(context, done);
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() => _run(
      () => _call(widget.app, 'PUT', '$_path/watch', body: {
            'url': _url.text.trim(),
            'every_min': _every,
            'feeds': [for (final f in _feeds) {'app': f.$1, 'what': f.$2.text.trim()}],
            'on': _on,
          }),
      done: 'Saved.');

  Future<void> _check() => _run(() => _call(widget.app, 'POST', '$_path/watch/check'));

  Future<void> _act(Map<String, dynamic> a, String what) async {
    if (what == 'fix') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) {
          final c = CodeColors.of(d);
          return AlertDialog(
            backgroundColor: c.sheet,
            title: Text('Start a fix?', style: HcType.ui(c, 18, weight: FontWeight.w600)),
            content: Text('Hoola Code will open a pull request against your main branch. You merge it yourself.',
                style: HcType.ui(c, 15, color: c.ink2, height: 1.4)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: Text('Not now', style: HcType.ui(c, 15, color: c.ink3))),
              TextButton(onPressed: () => Navigator.pop(d, true), child: Text('Start the fix', style: HcType.ui(c, 15, color: c.accent))),
            ],
          );
        },
      );
      if (ok != true || !mounted) return;
    }
    await _run(() => _call(widget.app, 'POST', '$_path/alerts/${hcS(a['id'])}/$what'),
        done: what == 'fix' ? 'Fix started in Hoola Code.' : '');
  }

  Future<void> _pickApp(int i) async {
    final apps = hcList(_v?['apps']);
    final key = await hcSheet<String>(context, (sheet) {
      final c = CodeColors.of(sheet);
      return Column(mainAxisSize: MainAxisSize.min, children: [
        const HcSheetHead(title: 'Watch which app?'),
        for (final a in apps)
          ListTile(
            minVerticalPadding: 12,
            title: Text(hcS(a['name']), style: HcType.ui(c, 16)),
            subtitle: Text(hcS(a['say']), style: HcType.ui(c, 12, color: hcS(a['state']) == 'ready' ? c.green : c.ink4)),
            onTap: () => Navigator.pop(sheet, hcS(a['key'])),
          ),
        const SizedBox(height: 12),
      ]);
    });
    if (key == null || !mounted) return;
    setState(() {
      if (i < 0) {
        _feeds.add((key, TextEditingController()));
      } else {
        _feeds[i] = (key, _feeds[i].$2);
      }
    });
  }

  String _appName(String key) {
    final a = hcList(_v?['apps']).firstWhere((x) => hcS(x['key']) == key, orElse: () => <String, dynamic>{});
    return hcS(a['name']).isNotEmpty ? hcS(a['name']) : key;
  }

  String _hint(String key) {
    final a = hcList(_v?['apps']).firstWhere((x) => hcS(x['key']) == key, orElse: () => <String, dynamic>{});
    return hcS(a['hint']).isNotEmpty ? hcS(a['hint']) : 'What to read';
  }

  Widget _input(CodeColors c, TextEditingController ctl, String hint) => TextField(
        controller: ctl,
        style: HcType.ui(c, 15),
        cursorColor: c.accent,
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: HcType.ui(c, 15, color: c.ink5),
          filled: true,
          fillColor: c.field,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
          focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final v = _v;
    final alerts = hcList(v?['alerts']);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Head(
            title: 'Monitor',
            sub: v == null ? '' : (hcInt(v['open']) > 0 ? '${hcInt(v['open'])} need you' : (v['live'] == true ? 'Live project' : 'Starts after go-live')),
          ),
          Expanded(
            child: v == null
                ? _loading(c)
                : RefreshIndicator(
                    color: c.accent,
                    onRefresh: _load,
                    child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 16), children: [
                      Text(hcS(v['says']), style: HcType.ui(c, 14, color: c.ink3, height: 1.45)),
                      const SizedBox(height: 12),
                      if (alerts.isNotEmpty) ...[
                        Text('Problems', style: HcType.ui(c, 15, weight: FontWeight.w600)),
                        const SizedBox(height: 8),
                        for (final a in alerts) ...[
                          AutoAlertCard(
                            alert: a,
                            onAct: (w) => _act(a, w),
                            onOpen: (u) => launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication),
                          ),
                          const SizedBox(height: 8),
                        ],
                        const SizedBox(height: 8),
                      ],
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: _cardBox(c),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                          Row(children: [
                            Expanded(child: Text('Watch this project', style: HcType.ui(c, 15, weight: FontWeight.w600))),
                            HcSwitch(value: _on, label: 'Watch this project', onChanged: (x) => setState(() => _on = x)),
                          ]),
                          const SizedBox(height: 8),
                          Text('The live address', style: HcType.ui(c, 13, color: c.ink4)),
                          const SizedBox(height: 4),
                          _input(c, _url, 'https://shop.example.com'),
                          const SizedBox(height: 12),
                          Text('Check every', style: HcType.ui(c, 13, color: c.ink4)),
                          const SizedBox(height: 6),
                          Wrap(spacing: 6, runSpacing: 6, children: [
                            for (final e in autoEvery)
                              HcFilterChip(label: e.$2, on: _every == e.$1, outlined: true, onTap: () => setState(() => _every = e.$1)),
                          ]),
                          const SizedBox(height: 12),
                          Text('Feeds (read only, up to 5)', style: HcType.ui(c, 13, color: c.ink4)),
                          const SizedBox(height: 6),
                          for (var i = 0; i < _feeds.length; i++)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(children: [
                                ConstrainedBox(constraints: const BoxConstraints(maxWidth: 130), child: HcOutlineButton(label: _appName(_feeds[i].$1), height: 44, size: 14, onTap: () => _pickApp(i))),
                                const SizedBox(width: 8),
                                Expanded(child: _input(c, _feeds[i].$2, _hint(_feeds[i].$1))),
                                HcIconButton(
                                    icon: Icons.delete_outline_rounded,
                                    label: 'Remove feed',
                                    onTap: () {
                                      final gone = _feeds.removeAt(i);
                                      setState(() {});
                                      WidgetsBinding.instance.addPostFrameCallback((_) => gone.$2.dispose());
                                    }),
                              ]),
                            ),
                          if (_feeds.length < 5)
                            Align(
                              alignment: Alignment.centerLeft,
                              child: HcOutlineButton(label: 'Add a feed', icon: Icons.add_rounded, height: 42, size: 14, onTap: () => _pickApp(-1)),
                            ),
                        ]),
                      ),
                      const SizedBox(height: 12),
                      if (hcS(v['last_say']).isNotEmpty)
                        Text('Last check ${_at(hcS(v['last_at']))}: ${hcS(v['last_say'])}',
                            style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
                      if (v['repos'] is List && (v['repos'] as List).isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text('CI on the main branch of ${(v['repos'] as List).join(', ')} is read too.',
                              style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
                        ),
                    ]),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Row(children: [
              Expanded(child: HcOutlineButton(label: 'Check now', icon: Icons.refresh_rounded, onTap: _busy ? null : _check)),
              const SizedBox(width: 8),
              Expanded(child: HcCreamButton(label: 'Save', height: 46, size: 15, busy: _busy, onTap: _busy ? null : _save)),
            ]),
          ),
        ]),
      ),
    );
  }
}
