/// v0.317 HIRE AN EMPLOYEE (Profile > Employees): the Employee Hub (hire / pause / let go) and the SEO Desk of a
/// hired SEO Specialist (onboarding, KPIs against the baseline, the 90-day plan, alerts, schedule, run-now buttons).
/// A desk exists only while its employee is hired. Same server as the web console: /api/employees*, /api/seo/desk...
/// v0.319 SEO PRO on the desk: health in 7 parts, Google's index answer, AI search bots, trust (E-E-A-T), local score,
/// speed parts + phone screenshot, IndexNow, and "how we'll know" on every plan item.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'cad_desk.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
String _num(dynamic v) {
  if (v == null || v == '') return '–';
  if (v is double) return v.toStringAsFixed(v.truncateToDouble() == v ? 0 : 1);
  return '$v';
}

const _ws = {'technical': 'Technical', 'content': 'Content', 'local': 'Local', 'authority': 'Authority',
    'ai_search': 'AI search', 'reporting': 'Reporting'};
const _cols = [['planned', 'Planned'], ['doing', 'Doing'], ['waiting_her', 'Waiting for you'], ['done', 'Done'], ['skipped', 'Skipped']];

// ------------------------------------------------------------------ the hub
class EmployeesScreen extends StatefulWidget {
  const EmployeesScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<EmployeesScreen> createState() => _EmployeesScreenState();
}

class _EmployeesScreenState extends State<EmployeesScreen> {
  List<Map<String, dynamic>> _emps = [];
  bool _loaded = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.employees();
      if (mounted) {
        setState(() {
          _emps = _list(d['employees']);
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

  Future<void> _act(String key, String action) async {
    if (action == 'leave') {
      final ok = await showDialog<bool>(
          context: context,
          builder: (c) => AlertDialog(
                title: const Text('Let go?'),
                content: const Text('Its jobs stop at once. Its history stays, read-only.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
                  TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Let go')),
                ],
              ));
      if (ok != true) return;
    }
    setState(() => _busy = true);
    try {
      await widget.app.api!.employeeAct(key, action);
      if (mounted) {
        _snack(context, switch (action) {
          'hire' => 'Hired. Set it up on its desk.',
          'pause' => 'Paused. No jobs run until you resume.',
          'resume' => 'Back at work.',
          _ => 'Let go. Its jobs have stopped.',
        });
      }
      await _load();
      if (action == 'hire' && (key == 'seo' || key == 'social' || key == 'cad') && mounted) _openDesk(key);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  void _openDesk(String key) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => key == 'social'
          ? SocialDeskScreen(app: widget.app)
          : key == 'cad'
              ? CadDeskScreen(app: widget.app)
              : SeoDeskScreen(app: widget.app)))
      .then((_) => _load());

  Widget _card(Map<String, dynamic> e) {
    final st = _s(e['status']);
    final hired = st == 'hired' || st == 'paused';
    final live = e['live'] == true;
    Widget list(String title, dynamic xs) {
      final items = ((xs as List?) ?? const []).map((x) => '$x').toList();
      if (items.isEmpty) return const SizedBox.shrink();
      return Padding(
        padding: const EdgeInsets.only(top: 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(color: C.muted, fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          for (final x in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 3),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('•  ', style: TextStyle(color: C.accent)),
                Expanded(child: Text(x, style: const TextStyle(fontSize: 13.5, height: 1.35))),
              ]),
            ),
        ]),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(e['name']), style: display(16))),
            if (st == 'hired') const _Tag('Working', C.ok),
            if (st == 'paused') const _Tag('Paused', C.warn),
            if (!live) const _Tag('Coming soon', C.muted),
          ]),
          const SizedBox(height: 6),
          Text(_s(e['pitch']), style: const TextStyle(fontSize: 14, height: 1.35)),
          if (live) ...[list('What it does', e['does']), list('What it needs', e['needs']), list('What it will never do', e['never'])],
          const SizedBox(height: 12),
          if (live && !hired) GradientButton(label: 'Hire ${_s(e['name'])}', icon: Icons.person_add_alt_1_rounded,
              onTap: _busy ? null : () => _act(_s(e['key']), 'hire')),
          if (hired)
            Wrap(spacing: 8, runSpacing: 8, children: [
              FilledButton.icon(onPressed: _busy ? null : () => _openDesk(_s(e['key'])), icon: const Icon(Icons.dashboard_rounded), label: const Text('Open desk')),
              OutlinedButton(onPressed: _busy ? null : () => _act(_s(e['key']), st == 'paused' ? 'resume' : 'pause'),
                  child: Text(st == 'paused' ? 'Resume' : 'Pause')),
              TextButton(onPressed: _busy ? null : () => _act(_s(e['key']), 'leave'),
                  child: const Text('Let go', style: TextStyle(color: C.bad))),
            ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Employees')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            const Text('Hire an AI employee for one job. It gets its own desk and works 24/7; you stay in charge.',
                style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
            const SizedBox(height: 14),
            if (!_loaded) const Center(child: CircularProgressIndicator()),
            // v0.357 grouped like the console: Business, then Research, CAD, Hardware & Industrial Tech
            for (final g in {for (final e in _emps) _s(e['group']).isEmpty ? 'Business' : _s(e['group'])}) ...[
              Padding(padding: const EdgeInsets.only(top: 8, bottom: 8), child: Text(g, style: display(15))),
              for (final e in _emps.where((e) => (_s(e['group']).isEmpty ? 'Business' : _s(e['group'])) == g)) _card(e),
            ],
          ]),
        ),
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  const _Tag(this.text, this.color);
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: color.withOpacity(.16), borderRadius: BorderRadius.circular(20)),
        child: Text(text, style: TextStyle(color: color, fontSize: 11.5, fontWeight: FontWeight.w600)),
      );
}

// ------------------------------------------------------------------ the SEO desk
class SeoDeskScreen extends StatefulWidget {
  const SeoDeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SeoDeskScreen> createState() => _SeoDeskScreenState();
}

class _SeoDeskScreenState extends State<SeoDeskScreen> {
  Map<String, dynamic>? _d;
  bool _busy = false;
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    _poll?.cancel();
    try {
      final d = await widget.app.api!.seoDesk();
      if (!mounted) return;
      setState(() => _d = d);
      if (_s(d['state']) == 'first_run') _poll = Timer(const Duration(seconds: 10), _load);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _call(Future<Map<String, dynamic>> Function() fn, String done) async {
    setState(() => _busy = true);
    try {
      await fn();
      if (mounted) _snack(context, done);
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _connect() async {
    try {
      final url = await widget.app.api!.seoGscLink();
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _onboard() async {
    final f = {for (final k in ['url', 'name', 'city', 'services', 'goal', 'customers', 'competitors']) k: TextEditingController()};
    String trust = 'seekh';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (c) => StatefulBuilder(
        builder: (c, setSheet) => Padding(
          padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(c).viewInsets.bottom + 16),
          child: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text('Set up your SEO Specialist', style: display(17)),
              const SizedBox(height: 4),
              const Text('Then it checks your whole website, reads your Google numbers, saves a baseline and writes a 90-day plan.',
                  style: TextStyle(color: C.muted, fontSize: 13)),
              const SizedBox(height: 12),
              for (final row in const [
                ['url', 'Website address', 'yourbusiness.in'],
                ['name', 'Business name', 'Sharma Dental Clinic'],
                ['city', 'City', 'Nagpur'],
                ['services', 'What you sell (comma separated)', 'Root canal, implants, braces'],
                ['goal', 'What do you want from Google?', 'More calls for implants'],
                ['customers', 'Who are your customers?', 'Families in Dharampeth and Sadar'],
                ['competitors', "Competitors' websites (optional)", 'smiledental.in, citydentist.in'],
              ])
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: TextField(controller: f[row[0]], decoration: InputDecoration(labelText: row[1], hintText: row[2])),
                ),
              const Text('How much may it do on its own?', style: TextStyle(fontWeight: FontWeight.w600)),
              RadioListTile<String>(
                  value: 'seekh', groupValue: trust, onChanged: (v) => setSheet(() => trust = v ?? 'seekh'),
                  title: const Text('Seekh'), subtitle: const Text('Asks you before every change outside Hoola')),
              RadioListTile<String>(
                  value: 'saathi', groupValue: trust, onChanged: (v) => setSheet(() => trust = v ?? 'seekh'),
                  title: const Text('Saathi'), subtitle: const Text('Small, undoable changes; tells you the same day')),
              const SizedBox(height: 8),
              GradientButton(label: 'Start work', icon: Icons.play_arrow_rounded, onTap: () => Navigator.pop(c, true)),
            ]),
          ),
        ),
      ),
    );
    if (ok != true) return;
    final body = <String, dynamic>{for (final e in f.entries) e.key: e.value.text.trim(), 'trust': trust};
    if (_s(body['url']).isEmpty) {
      if (mounted) _snack(context, 'Website address chahiye.');
      return;
    }
    await _call(() => widget.app.api!.seoOnboard(body), 'Started. The first check takes 10-15 minutes.');
  }

  Widget _kpi(Map<String, dynamic> k) {
    final ch = k['change_pct'];
    final good = k['good'] == true;
    return SizedBox(
      width: 150,
      child: Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_num(k['now']), style: display(20)),
          const SizedBox(height: 2),
          Text(_s(k['name']), style: const TextStyle(color: C.muted, fontSize: 12)),
          const SizedBox(height: 4),
          Text('from ${_num(k['baseline'])}${ch == null ? '' : '  ${(ch as num) >= 0 ? '+' : ''}$ch%'}',
              style: TextStyle(fontSize: 11.5, color: ch == null ? C.faint : (good ? C.ok : C.bad))),
        ]),
      ),
    );
  }

  Widget _item(Map<String, dynamic> it) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            _Tag(_ws[_s(it['workstream'])] ?? _s(it['workstream']), C.violet),
            const SizedBox(width: 8),
            Text('Week ${_s(it['week'])}${_s(it['owner']) == 'her' ? ' · needs you' : ''}',
                style: const TextStyle(color: C.muted, fontSize: 12)),
          ]),
          const SizedBox(height: 6),
          Text(_s(it['title']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
          if (_s(it['why']).isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 3), child: Text(_s(it['why']), style: const TextStyle(color: C.muted, fontSize: 12.5))),
          if (_s(it['signal']).isNotEmpty)
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text("How we'll know", style: TextStyle(fontSize: 12.5, color: C.muted)),
                childrenPadding: const EdgeInsets.only(bottom: 4),
                expandedCrossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Early sign: ${_s(it['signal'])}', style: const TextStyle(fontSize: 12.5)),
                  const SizedBox(height: 3),
                  Text('Not working if: ${_s(it['fail_check'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                ],
              ),
            ),
          DropdownButton<String>(
            value: _s(it['status']),
            isDense: true,
            underline: const SizedBox.shrink(),
            items: [for (final c in _cols) DropdownMenuItem(value: c[0], child: Text(c[1], style: const TextStyle(fontSize: 13)))],
            onChanged: _busy
                ? null
                : (v) {
                    if (v != null) _call(() => widget.app.api!.seoRoadmapItem(_s(it['id']), v), 'Updated.');
                  },
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final children = <Widget>[];
    if (d == null) {
      children.add(const Center(child: CircularProgressIndicator()));
    } else if (d['hired'] != true) {
      children.add(const Text('The SEO Specialist is not hired. Hire it in Employees first.', style: TextStyle(fontSize: 14)));
    } else if (d['onboarded'] != true) {
      children.addAll([
        const Text('Five questions, then your SEO Specialist starts: full website check, Google numbers, a baseline and a 90-day plan.',
            style: TextStyle(fontSize: 14, height: 1.35)),
        const SizedBox(height: 14),
        GradientButton(label: 'Set up', icon: Icons.rocket_launch_rounded, onTap: _busy ? null : _onboard),
      ]);
    } else {
      final site = Map<String, dynamic>.from((d['site'] as Map?) ?? const {});
      final google = Map<String, dynamic>.from((d['google'] as Map?) ?? const {});
      final board = Map<String, dynamic>.from((d['board'] as Map?) ?? const {});
      final state = _s(d['state']);
      children.addAll([
        Row(children: [
          Expanded(child: Text(_s(site['name']).isEmpty ? _s(site['url']) : _s(site['name']), style: display(17))),
          _Tag(switch (state) { 'ready' => 'Working', 'first_run' => 'First check running', 'error' => 'Stopped', _ => state },
              state == 'error' ? C.bad : (state == 'ready' ? C.ok : C.warn)),
        ]),
        Text(_s(site['url']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 12),
        if (google['connected'] != true)
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Connect Google', style: display(14)),
              const SizedBox(height: 4),
              const Text('Search Console (and Analytics, if you use it) give the real numbers: clicks, searches, leads. Read-only.',
                  style: TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              FilledButton(onPressed: _connect, child: const Text('Connect Google')),
            ]),
          ),
        if (_s(d['roadmap_status']) == 'draft') ...[
          const SizedBox(height: 10),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Your 90-day plan is ready', style: display(14)),
              const SizedBox(height: 4),
              Text('${_s(d['roadmap_count'])} steps from the real audit. Read them below and approve to start the weekly work.',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              FilledButton(
                  onPressed: _busy ? null : () => _call(widget.app.api!.seoRoadmapApprove, 'Plan approved.'),
                  child: const Text('Approve plan')),
            ]),
          ),
        ],
        const SizedBox(height: 14),
        Wrap(spacing: 10, runSpacing: 10, children: [for (final k in _list(d['kpis'])) _kpi(k)]),
        const SizedBox(height: 6),
        Text('Baseline from ${_s((d['baseline'] as Map?)?['date'])}. Google data runs three days behind.',
            style: const TextStyle(color: C.faint, fontSize: 11.5)),
        if ((d['pro'] as Map?)?['health'] != null) ...[
          const SizedBox(height: 14),
          _HealthCard(Map<String, dynamic>.from(d['pro'] as Map), Map<String, dynamic>.from((d['index'] as Map?) ?? const {})),
          const SizedBox(height: 10),
          _BotsCard(_list((d['pro'] as Map)['ai_bots'])),
          const SizedBox(height: 10),
          _ScoreCard('Trust signals (E-E-A-T)', Map<String, dynamic>.from(((d['pro'] as Map)['eeat'] as Map?) ?? const {}), 'key'),
          const SizedBox(height: 10),
          _ScoreCard('Local search', Map<String, dynamic>.from(((d['pro'] as Map)['local'] as Map?) ?? const {}), 'label'),
          const SizedBox(height: 10),
          _SpeedCard(Map<String, dynamic>.from(((d['latest'] as Map?)?['cwv'] as Map?) ?? const {}),
              Map<String, dynamic>.from((d['shots'] as Map?) ?? const {})),
        ],
        const SizedBox(height: 16),
        Text('90-day plan', style: display(15)),
        for (final c in _cols.take(4)) ...[
          const SizedBox(height: 10),
          Text('${c[1]} (${_list(board[c[0]]).length})', style: const TextStyle(color: C.muted, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          for (final it in _list(board[c[0]])) _item(it),
        ],
        const SizedBox(height: 16),
        Text('Activity and alerts', style: display(15)),
        const SizedBox(height: 6),
        for (final e in _list(d['events']).take(12))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(
                switch (_s(e['level'])) { 'bad' => Icons.error_rounded, 'warn' => Icons.warning_rounded, 'ok' => Icons.check_circle_rounded, _ => Icons.info_rounded },
                color: switch (_s(e['level'])) { 'bad' => C.bad, 'warn' => C.warn, 'ok' => C.ok, _ => C.muted }),
            title: Text(_s(e['text']), style: const TextStyle(fontSize: 13.5)),
            subtitle: Text(_s(e['at']).replaceFirst('T', ' ').split('.').first, style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ),
        const SizedBox(height: 16),
        Text('Runs 24/7', style: display(15)),
        const SizedBox(height: 6),
        for (final j in _list(d['schedule']))
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(children: [
              Expanded(child: Text(_s(j['job']), style: const TextStyle(fontSize: 13.5))),
              Text(_s(j['every']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ]),
          ),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.seoRun('weekly'), 'Full check started.'),
              child: const Text('Full check now')),
          OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.seoRun('daily'), 'Refreshing numbers.'),
              child: const Text('Refresh numbers')),
          OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.seoRun('monthly'), 'The PDF arrives in your chat.'),
              child: const Text('Monthly report now')),
          OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.seoRun('index'), 'Asking Google about your key pages.'),
              child: const Text('Check Google index')),
        ]),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('IndexNow', style: display(14)),
            const SizedBox(height: 4),
            Text(
                _s((d['indexnow'] as Map?)?['key']).isEmpty
                    ? 'Tell Bing and other IndexNow engines about changed pages every week. Google does not use it.'
                    : 'Put a file named ${_s((d['indexnow'] as Map?)?['key'])}.txt with only that key inside at the top of your website.',
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            const SizedBox(height: 8),
            OutlinedButton(
                onPressed: _busy
                    ? null
                    : () async {
                        try {
                          final r = await widget.app.api!.seoRun('indexnow');
                          if (mounted) _snack(context, _s(r['say']));
                          await _load();
                        } catch (e) {
                          if (mounted) _snack(context, '$e');
                        }
                      },
                child: Text(_s((d['indexnow'] as Map?)?['key']).isEmpty ? 'Turn on' : 'Check the file')),
          ]),
        ),
        const SizedBox(height: 16),
        Text('Open fixes on the website', style: display(15)),
        const SizedBox(height: 6),
        for (final t in _list(d['open_tasks']).take(15))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(Icons.circle, size: 10, color: _s(t['level']) == 'bad' ? C.bad : (_s(t['level']) == 'warn' ? C.warn : C.muted)),
            title: Text('${_s(t['priority']).isEmpty ? '' : '${_s(t['priority']).toUpperCase()} · '}${_s(t['text'])}',
                style: const TextStyle(fontSize: 13.5)),
            subtitle: Text('${_s(t['url'])}\n${_s(t['fix'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
          ),
      ]);
    }
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('SEO Desk')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: children),
        ),
      ),
    );
  }
}


// ------------------------------------------------------------------ v0.319 SEO PRO cards
Widget _bar(String label, num? score, num max, {String unit = ''}) {
  final v = score == null || max <= 0 ? 0.0 : (score / max).clamp(0, 1).toDouble();
  return Padding(
    padding: const EdgeInsets.only(top: 7),
    child: Row(children: [
      Expanded(flex: 5, child: Text(label, style: const TextStyle(fontSize: 12.5))),
      Expanded(
        flex: 4,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(value: v, minHeight: 6, backgroundColor: C.faint.withOpacity(.25), color: C.violet),
        ),
      ),
      SizedBox(
          width: unit.isEmpty ? 52 : 64,
          child: Text(score == null ? '–' : (unit.isNotEmpty ? '$score $unit' : (max == 100 ? '$score' : '$score/$max')),
              textAlign: TextAlign.right, style: const TextStyle(fontSize: 12, color: C.muted))),
    ]),
  );
}

Widget _head(String title, dynamic total) => Row(children: [
      Expanded(child: Text(title, style: display(14))),
      Text(total == null ? '–' : '$total', style: display(20)),
      const Text('/100', style: TextStyle(color: C.muted, fontSize: 12)),
    ]);

class _HealthCard extends StatelessWidget {
  const _HealthCard(this.pro, this.index);
  final Map<String, dynamic> pro;
  final Map<String, dynamic> index;

  @override
  Widget build(BuildContext context) {
    final h = Map<String, dynamic>.from(pro['health'] as Map);
    final counts = Map<String, dynamic>.from((h['counts'] as Map?) ?? const {});
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _head('Website health', h['total']),
        Text(['critical', 'high', 'medium', 'low'].map((k) => '${_s(counts[k])} $k').join(' · '),
            style: const TextStyle(color: C.muted, fontSize: 12)),
        for (final p in _list(h['parts'])) _bar('${_s(p['label'])} (${_s(p['weight'])})', p['score'] as num?, 100),
        if (index['checked'] != null && index['checked'] != 0)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text("${_s(index['indexed'])} of ${_s(index['checked'])} key pages are in Google's index (Google's own answer).",
                style: const TextStyle(fontSize: 12.5)),
          ),
      ]),
    );
  }
}

class _BotsCard extends StatelessWidget {
  const _BotsCard(this.bots);
  final List<Map<String, dynamic>> bots;
  static const _kinds = {'google': 'Google', 'search': 'AI search', 'user': 'On request', 'training': 'Training only'};

  @override
  Widget build(BuildContext context) {
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('AI search', style: display(14)),
        const SizedBox(height: 4),
        const Text('Search bots decide if ChatGPT, Claude or Perplexity can show you. Blocking training bots costs nothing in search.',
            style: TextStyle(color: C.muted, fontSize: 12)),
        for (final b in bots.where((b) => _s(b['kind']) != 'training'))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(children: [
              Expanded(child: Text(_s(b['bot']), style: const TextStyle(fontSize: 13))),
              Text(_kinds[_s(b['kind'])] ?? _s(b['kind']), style: const TextStyle(color: C.muted, fontSize: 12)),
              const SizedBox(width: 8),
              _Tag(b['allowed'] == true ? 'Allowed' : 'Blocked',
                  b['allowed'] == true ? C.ok : (_s(b['kind']) == 'training' ? C.muted : C.bad)),
            ]),
          ),
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
              'Training-only bots: ${bots.where((b) => _s(b['kind']) == 'training' && b['allowed'] == true).length} allowed, '
              '${bots.where((b) => _s(b['kind']) == 'training' && b['allowed'] != true).length} blocked (your choice; no effect on search).',
              style: const TextStyle(color: C.muted, fontSize: 12)),
        ),
      ]),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  const _ScoreCard(this.title, this.data, this.labelKey);
  final String title;
  final Map<String, dynamic> data;
  final String labelKey;

  @override
  Widget build(BuildContext context) {
    String cap(String x) => x.isEmpty ? x : x[0].toUpperCase() + x.substring(1);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _head(title, data['total']),
        for (final p in _list(data['parts'])) _bar(cap(_s(p[labelKey])), p['score'] as num?, (p['max'] as num?) ?? 100),
        if (_s(data['note']).isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 8), child: Text(_s(data['note']), style: const TextStyle(color: C.faint, fontSize: 11.5))),
      ]),
    );
  }
}

class _SpeedCard extends StatelessWidget {
  const _SpeedCard(this.cwv, this.shots);
  final Map<String, dynamic> cwv;
  final Map<String, dynamic> shots;

  @override
  Widget build(BuildContext context) {
    final parts = _list(cwv['lcp_parts']);
    final mx = parts.fold<num>(1, (a, p) => (p['ms'] as num) > a ? p['ms'] as num : a);
    final shot = _s((shots['mobile'] as Map?)?['img']);
    Uint8List? img;
    if (shot.startsWith('data:image/') && shot.contains(',')) {
      try {
        img = base64Decode(shot.substring(shot.indexOf(',') + 1));
      } catch (_) {}
    }
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Speed on phones', style: display(14)),
            const SizedBox(height: 4),
            Text(
                cwv['lcp_ms'] == null
                    ? 'Speed appears after the weekly check.'
                    : 'Main content shows in ${((cwv['lcp_ms'] as num) / 1000).toStringAsFixed(1)} s (good is 2.5 s or less).',
                style: const TextStyle(fontSize: 12.5)),
            for (final p in parts) _bar(_s(p['label']), p['ms'] as num?, mx, unit: 'ms'),
          ]),
        ),
        if (img != null) ...[
          const SizedBox(width: 10),
          ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(img, width: 84, fit: BoxFit.cover)),
        ],
      ]),
    );
  }
}


// ------------------------------------------------------------------ v0.353 the Social Desk (Social Media Manager, Phase 1)
class SocialDeskScreen extends StatefulWidget {
  const SocialDeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SocialDeskScreen> createState() => _SocialDeskScreenState();
}

class _SocialDeskScreenState extends State<SocialDeskScreen> {
  Map<String, dynamic>? _d;
  bool _busy = false;
  Timer? _poll;
  static const _plat = {'instagram': 'Instagram', 'facebook': 'Facebook Page'};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    _poll?.cancel();
    try {
      final d = await widget.app.api!.socialDesk();
      if (!mounted) return;
      setState(() => _d = d);
      if (_s(d['state']) == 'first_run') _poll = Timer(const Duration(seconds: 8), _load);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _call(Future<dynamic> Function() fn, String done) async {
    setState(() => _busy = true);
    try {
      await fn();
      if (mounted && done.isNotEmpty) _snack(context, done);
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _connect(String p) async {
    try {
      final url = await widget.app.api!.socialConnect(p);
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
      if (mounted) _snack(context, 'Log in there, then come back and pull down to refresh.');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _setup() async {
    final p = Map<String, dynamic>.from((_d?['profile'] as Map?) ?? const {});
    final f = {
      'business': TextEditingController(text: _s(p['business'])),
      'city': TextEditingController(text: _s(p['city'])),
      'sells': TextEditingController(text: _s(p['sells'])),
      'customers': TextEditingController(),
      'goal': TextEditingController(),
      'languages': TextEditingController(text: ((p['languages'] as List?) ?? ['Hinglish']).join(', ')),
      'facts': TextEditingController(text: _s(p['facts'])),
    };
    const labels = {'business': 'Business name', 'city': 'City', 'sells': 'What you sell', 'customers': 'Who are your customers?',
        'goal': 'What do you want from social media?', 'languages': 'Languages for posts (comma separated)',
        'facts': 'Facts for replies: prices, timings, address, WhatsApp (only these are ever quoted)'};
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (c) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(c).viewInsets.bottom),
        child: SingleChildScrollView(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text('Set up your Social Desk', style: display(17)),
            const SizedBox(height: 10),
            for (final k in labels.keys)
              Padding(padding: const EdgeInsets.only(bottom: 8), child: TextField(controller: f[k], decoration: InputDecoration(labelText: labels[k]))),
            const Text('Posts go out only after your OK. Replies to comments / DMs quote only the facts you give here.',
                style: TextStyle(color: C.muted, fontSize: 12.5)),
            const SizedBox(height: 12),
            GradientButton(label: 'Save', icon: Icons.check_rounded, onTap: () => Navigator.pop(c, true)),
          ]),
        ),
      ),
    );
    if (ok != true) return;
    await _call(() => widget.app.api!.socialOnboard({for (final k in f.keys) k: f[k]!.text.trim(), 'trust': 'seekh'}),
        'Saved. Now connect Instagram or your Facebook Page.');
  }

  Future<void> _addPhoto(String id) async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 90, maxWidth: 1440);
    if (x == null) return;
    final bytes = await x.readAsBytes();
    await _call(() async {
      final a = await widget.app.api!.socialUpload(x.name, bytes);
      return widget.app.api!.socialAttach(id, [_s(a['id'])]);
    }, 'Photo added. Approve the post again when it looks right.');
  }

  Future<void> _publish(Map<String, dynamic> p) async {
    final where = ((p['platforms'] as List?) ?? []).map((x) => _plat[x] ?? x).join(' and ');
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Post now?'),
        content: Text('This goes out on $where exactly as shown, to everyone who follows you.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Post now')),
        ],
      ),
    );
    if (ok != true) return;
    await _call(() => widget.app.api!.socialPublish(_s(p['id'])), 'Posting… the link appears here in a minute.');
    Timer(const Duration(seconds: 6), _load);
  }

  Future<void> _stop() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Emergency stop?'),
        content: const Text('All posting and automatic replies stop, and every queued post goes back to draft.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Stop everything')),
        ],
      ),
    );
    if (ok != true) return;
    await _call(() => widget.app.api!.socialSettings({'stop': true}), 'Stopped. Queued posts are drafts again.');
  }

  Widget _post(Map<String, dynamic> p) {
    final st = _s(p['status']);
    final needOk = p['plan_only'] == true && _s(_d?['trust']) == 'seekh';   // v0.366
    final done = st == 'published' || st == 'publishing';
    final res = Map<String, dynamic>.from((p['result'] as Map?) ?? const {});
    final probs = ((p['problems'] as List?) ?? const []).map((e) => '$e').toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(p['slot']).replaceFirst('T', '  '), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
            _Tag(_s(p['format']), C.violet),
            if (needOk) ...[const SizedBox(width: 6), _Tag('Needs your OK', C.warn)],
            const SizedBox(width: 6),
            _Tag(switch (st) { 'approved' => 'Approved', 'skipped' => 'Skipped', 'publishing' => 'Posting…', 'published' => 'Posted',
                  'failed' => 'Not posted', 'missed' => 'Missed', _ => 'Draft' },
                st == 'approved' || st == 'published' ? C.ok : (st == 'failed' ? C.bad : (st == 'skipped' || st == 'missed' ? C.muted : C.warn))),
          ]),
          const SizedBox(height: 4),
          Text('${((p['platforms'] as List?) ?? []).map((x) => _plat[x] ?? x).join(' + ')}${_s(p['pillar']).isEmpty ? '' : ' · ${_s(p['pillar'])}'}'
              '${_s(p['occasion']).isEmpty ? '' : ' · ${_s(p['occasion'])}'}', style: const TextStyle(color: C.muted, fontSize: 12)),
          const SizedBox(height: 6),
          Text(_s(p['hook']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
          Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text('Caption, hashtags, picture brief', style: TextStyle(fontSize: 12.5, color: C.muted)),
              expandedCrossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SelectableText(_s(p['caption']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 6),
                Text(((p['hashtags'] as List?) ?? []).join(' '), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                if (_s(p['visual']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text('Picture / video: ${_s(p['visual'])}', style: const TextStyle(fontSize: 12.5))),
              ],
            ),
          ),
          if (((p['media'] as List?) ?? const []).isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Wrap(spacing: 6, children: [
                for (final m in _list(p['media']))
                  _s(m['kind']) == 'video'
                      ? const SizedBox(width: 56, height: 70, child: Center(child: Icon(Icons.play_circle_outline_rounded)))
                      : ClipRRect(borderRadius: BorderRadius.circular(8),
                          child: Image.network(_s(m['url']), width: 56, height: 70, fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => const SizedBox(width: 56, height: 70))),
              ]),
            ),
          for (final e in res.entries)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: _s((e.value as Map?)?['link']).isNotEmpty
                  ? InkWell(
                      onTap: () => launchUrl(Uri.parse(_s((e.value as Map)['link'])), mode: LaunchMode.externalApplication),
                      child: Text('Posted on ${_plat[e.key] ?? e.key} - open', style: const TextStyle(color: C.ok, fontSize: 12.5)))
                  : Text('${_plat[e.key] ?? e.key}: ${_s((e.value as Map?)?['error'])}', style: const TextStyle(color: C.bad, fontSize: 12.5)),
            ),
          if (!done && probs.isNotEmpty)
            Text(probs.join(' '), style: const TextStyle(color: C.warn, fontSize: 12.5)),
          if (!done) Wrap(spacing: 8, children: [
            DropdownButton<String>(
              value: ['draft', 'approved', 'skipped'].contains(st) ? st : null,
              hint: Text(st, style: const TextStyle(fontSize: 13)),
              isDense: true,
              underline: const SizedBox.shrink(),
              items: const [
                DropdownMenuItem(value: 'draft', child: Text('Draft', style: TextStyle(fontSize: 13))),
                DropdownMenuItem(value: 'approved', child: Text('Approved', style: TextStyle(fontSize: 13))),
                DropdownMenuItem(value: 'skipped', child: Text('Skipped', style: TextStyle(fontSize: 13))),
              ],
              onChanged: _busy ? null : (v) { if (v != null) _call(() => widget.app.api!.socialPost(_s(p['id']), {'status': v}), ''); },
            ),
            TextButton(
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: '${_s(p['caption'])}\n\n${((p['hashtags'] as List?) ?? []).join(' ')}'));
                if (mounted) _snack(context, 'Caption copied.');
              },
              child: const Text('Copy caption'),
            ),
            TextButton(onPressed: _busy ? null : () => _addPhoto(_s(p['id'])), child: const Text('Add photo')),
            TextButton(
                onPressed: _busy ? null : () => _call(() => widget.app.api!.socialPoster(_s(p['id'])), 'Poster made from your Brand kit.'),
                child: const Text('Make poster')),
            if (needOk)
              FilledButton(
                  onPressed: _busy ? null : () => _call(() => widget.app.api!.socialPost(_s(p['id']), {'status': 'approved'}), 'OK. It goes out at its time.'),
                  child: const Text('OK to post')),
            if (needOk)
              OutlinedButton(onPressed: _busy || probs.isNotEmpty ? null : () => _publish(p), child: const Text('Publish now'))
            else
              FilledButton(onPressed: _busy || probs.isNotEmpty ? null : () => _publish(p), child: const Text('Publish now')),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final children = <Widget>[];
    if (d == null) {
      children.add(const Center(child: CircularProgressIndicator()));
    } else if (d['hired'] != true) {
      children.add(const Text('The Social Media Manager is not hired. Hire it in Employees first.', style: TextStyle(fontSize: 14)));
    } else if (d['onboarded'] != true) {
      children.addAll([
        const Text('A few questions, then connect Instagram or your Facebook Page. It reads your posts, finds what works and plans the month.',
            style: TextStyle(fontSize: 14, height: 1.35)),
        const SizedBox(height: 14),
        GradientButton(label: 'Set up', icon: Icons.rocket_launch_rounded, onTap: _busy ? null : _setup),
      ]);
    } else {
      final prof = Map<String, dynamic>.from((d['profile'] as Map?) ?? const {});
      final accs = _list(d['accounts']);
      final conn = Map<String, dynamic>.from((d['connect'] as Map?) ?? const {});
      final stg = Map<String, dynamic>.from((d['strategy'] as Map?) ?? const {});
      final cal = _list(d['calendar']);
      final pl = Map<String, dynamic>.from((d['pulse'] as Map?) ?? const {});
      final pst = Map<String, dynamic>.from((pl['settings'] as Map?) ?? const {});
      final paused = pst['paused'] == true;
      final bt = Map<String, dynamic>.from((pl['best_times'] as Map?) ?? const {});
      children.addAll([
        Row(children: [
          Expanded(child: Text(_s(prof['business']), style: display(17))),
          _Tag(accs.isEmpty ? 'Connect an account' : switch (_s(d['state'])) { 'ready' => 'Working', 'first_run' => 'Reading your posts', 'error' => 'Stopped', _ => 'Starting' },
              accs.isEmpty ? C.warn : (_s(d['state']) == 'ready' ? C.ok : C.warn)),
        ]),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Accounts', style: display(14)),
            const SizedBox(height: 6),
            for (final a in accs)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.account_circle_rounded),
                title: Text(_s(a['handle']).isEmpty ? _s(a['name']) : _s(a['handle'])),
                subtitle: Text('${_plat[_s(a['platform'])] ?? _s(a['platform'])} · ${_num(a['followers'])} followers'
                    '${_s(a['status']) == 'ok' ? '' : ' · connection ended, connect again'}'
                    '${_s(a['status']) == 'ok' && (a['can_post'] == false || a['can_reply'] == false) ? ' · Connect again to allow posting and replies' : ''}'),
                trailing: TextButton(
                    onPressed: _busy ? null : () => _call(() => widget.app.api!.socialDisconnect(_s(a['id'])), 'Disconnected.'),
                    child: const Text('Disconnect')),
              ),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final p in ['instagram', 'facebook'])
                OutlinedButton(
                  onPressed: conn[p] == true && !_busy ? () => _connect(p) : null,
                  child: Text(conn[p] == true ? 'Connect ${_plat[p]}' : '${_plat[p]}: not set up on the server yet'),
                ),
            ]),
            const SizedBox(height: 6),
            const Text('You log in on Instagram / Facebook\'s own page. Instagram must be a Business or Creator account.',
                style: TextStyle(color: C.muted, fontSize: 12)),
          ]),
        ),
        if (accs.isNotEmpty) ...[
          const SizedBox(height: 10),
          Glass(
            border: paused ? C.warn : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('Posting', style: display(14))),
                _Tag(paused ? 'Paused' : 'On', paused ? C.warn : C.ok),
              ]),
              const SizedBox(height: 4),
              Text(paused
                  ? (_s(pst['pause_reason']).isEmpty ? 'Nothing goes out and no reply is sent on its own until you resume.' : _s(pst['pause_reason']))
                  : (_s(d['trust']) == 'seekh'
                      ? 'Every plan post waits for your OK on its day.${_list(pl['waiting_ok']).isEmpty ? '' : ' ${_list(pl['waiting_ok']).length} wait now.'}'
                      : 'Plan posts go on their own: ${_num(pl['auto_today'] ?? 0)} of ${_num(pl['post_cap'] ?? 0)} today, never between ${_num((pst['quiet'] as List?)?[0] ?? 23)}:00 and ${_num((pst['quiet'] as List?)?[1] ?? 7)}:00.'),
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (paused)
                  FilledButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.socialSettings({'paused': false}), 'Resumed.'),
                      child: const Text('Resume'))
                else
                  OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.socialSettings({'paused': true}), 'Paused.'),
                      child: const Text('Pause all posting')),
                TextButton(onPressed: _busy ? null : _stop, child: const Text('Emergency stop', style: TextStyle(color: C.bad))),
              ]),
            ]),
          ),
          if (_list(bt['slots']).isNotEmpty || _list(pl['boosts']).isNotEmpty) ...[
            const SizedBox(height: 10),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (_list(bt['slots']).isNotEmpty) ...[
                  Text('Best times for you', style: display(14)),
                  const SizedBox(height: 4),
                  for (final x in _list(bt['slots']).take(3))
                    Text('${_s(x['day'])} ${_s(x['band'])} · ${_s(x['lift'])}x your normal (${_num(x['posts'])} posts)', style: const TextStyle(fontSize: 13)),
                  Text('Certainty: ${_s(bt['sure'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
                ],
                for (final x in _list(pl['boosts'])) ...[
                  const SizedBox(height: 8),
                  InkWell(
                    onTap: () => launchUrl(Uri.parse(_s(x['permalink'])), mode: LaunchMode.externalApplication),
                    child: Text('Worth a boost: ${_s(x['fmt'])} from ${_s(x['date'])}, ${_s(x['times'])}x your normal',
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  ),
                  Text(_s(x['plan']), style: const TextStyle(color: C.muted, fontSize: 12)),
                ],
              ]),
            ),
          ],
          const SizedBox(height: 10),
          Press(
            onTap: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => SocialInboxScreen(app: widget.app)))
                .then((_) => _load()),
            child: Glass(
              child: Row(children: [
                const Icon(Icons.forum_rounded, color: C.accent),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Inbox: comments + DMs', style: display(14)),
                    const SizedBox(height: 2),
                    Text('${_num((d['inbox'] as Map?)?['needs'] ?? 0)} need you · ${_num((d['inbox'] as Map?)?['leads'] ?? 0)} leads'
                        ' · ${_num((d['inbox'] as Map?)?['complaints'] ?? 0)} complaints',
                        style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  ]),
                ),
                const Icon(Icons.chevron_right_rounded, color: C.muted),
              ]),
            ),
          ),
        ],
        if (_s(d['calendar_status']) == 'draft' && cal.isNotEmpty) ...[
          const SizedBox(height: 10),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Your 30-day calendar is ready', style: display(14)),
              const SizedBox(height: 4),
              Text('${cal.length} posts planned from your real numbers. Read them below, then approve.',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              FilledButton(onPressed: _busy ? null : () => _call(widget.app.api!.socialApprove, 'Calendar approved.'), child: const Text('Approve calendar')),
            ]),
          ),
        ],
        if (accs.isNotEmpty) ...[
          const SizedBox(height: 14),
          Wrap(spacing: 10, runSpacing: 10, children: [
            for (final k in _list(d['kpis']))
              SizedBox(
                width: 150,
                child: Glass(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_num(k['now']), style: display(20)),
                    Text(_s(k['name']), style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
              ),
          ]),
        ],
        if (stg['pillars'] != null) ...[
          const SizedBox(height: 14),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Strategy', style: display(14)),
              if (_s(stg['goal_metric']).isNotEmpty)
                Padding(padding: const EdgeInsets.only(top: 4), child: Text('Judged on: ${_s(stg['goal_metric'])}', style: const TextStyle(fontSize: 12.5))),
              const SizedBox(height: 6),
              Wrap(spacing: 6, runSpacing: 6, children: [for (final p in _list(stg['pillars'])) _Tag(_s(p['name']), C.violet)]),
              const SizedBox(height: 6),
              Text(((stg['hashtags'] as List?) ?? []).join(' '), style: const TextStyle(color: C.muted, fontSize: 12)),
            ]),
          ),
        ],
        if (cal.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text('Calendar', style: display(15)),
          const SizedBox(height: 6),
          for (final p in cal) _post(p),
        ],
        const SizedBox(height: 16),
        Text('Activity', style: display(15)),
        for (final e in _list(d['events']).take(10))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(switch (_s(e['level'])) { 'bad' => Icons.error_rounded, 'warn' => Icons.warning_rounded, 'ok' => Icons.check_circle_rounded, _ => Icons.info_rounded },
                color: switch (_s(e['level'])) { 'bad' => C.bad, 'warn' => C.warn, 'ok' => C.ok, _ => C.muted }),
            title: Text(_s(e['text']), style: const TextStyle(fontSize: 13.5)),
          ),
        if (accs.isNotEmpty)
          Wrap(spacing: 8, runSpacing: 8, children: [
            OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.socialRun('daily'), 'Reading your latest numbers.'),
                child: const Text('Refresh numbers')),
            OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.socialRun('plan'), 'Rewriting the draft. Approved posts stay.'),
                child: const Text('Rewrite calendar draft')),
            OutlinedButton(onPressed: _busy ? null : () => _call(() => widget.app.api!.socialRun('monthly'), 'Making the PDF - it arrives in your chat.'),
                child: const Text("This month's PDF")),
          ]),
      ]);
    }
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Social Desk')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: children),
        ),
      ),
    );
  }
}


/// v0.365 SOCIAL INBOX: comments on her posts and her DMs, sorted, each with a reply drafted from her facts.
/// Send / Hide / Ignore are her taps; Hoola never deletes and never messages anyone first.
class SocialInboxScreen extends StatefulWidget {
  const SocialInboxScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SocialInboxScreen> createState() => _SocialInboxScreenState();
}

class _SocialInboxScreenState extends State<SocialInboxScreen> {
  String _box = 'needs';
  Map<String, dynamic>? _d;
  bool _busy = false;
  final Map<String, TextEditingController> _ed = {};
  static const _boxes = {'needs': 'Needs you', 'leads': 'Leads', 'complaints': 'Complaints', 'done': 'Done'};
  static const _cls = {'lead': 'Lead', 'question': 'Question', 'praise': 'Praise', 'complaint': 'Complaint', 'spam': 'Spam',
      'abuse': 'Abuse', 'other': 'Other'};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _ed.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.socialInbox(_box);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(Future<dynamic> Function() fn, String done) async {
    setState(() => _busy = true);
    try {
      await fn();
      if (mounted) _snack(context, done);
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Color _clsColor(String c) => switch (c) {
        'lead' => C.ok,
        'complaint' => C.warn,
        'spam' || 'abuse' => C.bad,
        'praise' => C.violet,
        _ => C.muted,
      };

  Widget _item(Map<String, dynamic> it) {
    final id = _s(it['id']);
    final st = _s(it['status']);
    final open = st == 'new' || st == 'drafted' || st == 'failed';
    final ed = _ed.putIfAbsent(id, () => TextEditingController(text: _s(it['draft'])));
    final where = '${_s(it['platform']) == 'instagram' ? 'Instagram' : 'Facebook'} ${_s(it['kind']) == 'dm' ? 'DM' : 'comment'}';
    final hideable = _s(it['kind']) == 'comment';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(it['author']).isEmpty ? 'Someone' : _s(it['author'])} · $where',
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
            _Tag(_cls[_s(it['cls'])] ?? _s(it['cls']), _clsColor(_s(it['cls']))),
          ]),
          if (_s(it['post']).isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 2), child: Text('On: ${_s(it['post'])}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: C.muted, fontSize: 12))),
          const SizedBox(height: 6),
          SelectableText(_s(it['text']), style: const TextStyle(fontSize: 14, height: 1.35)),
          if (_s(it['note']).isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(it['note']), style: const TextStyle(color: C.muted, fontSize: 12))),
          if (_s(it['error']).isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(it['error']), style: const TextStyle(color: C.bad, fontSize: 12.5))),
          if (!open) ...[
            const SizedBox(height: 6),
            Text(switch (st) { 'replied' => '${it['auto'] == true ? 'Hoola replied' : 'You replied'}: ${_s(it['reply'])}',
                'hidden' => it['auto'] == true ? 'Hidden by Hoola (not deleted)' : 'Hidden (not deleted)', _ => 'No reply needed' },
                style: TextStyle(color: st == 'replied' ? C.ok : C.muted, fontSize: 12.5)),
            if (st == 'hidden')
              TextButton(onPressed: _busy ? null : () => _do(() => widget.app.api!.socialInboxHide(id, false), 'Shown again.'),
                  child: const Text('Unhide')),
            if (st == 'ignored')
              TextButton(onPressed: _busy ? null : () => _do(() => widget.app.api!.socialInboxSet(id, {'status': 'drafted'}), 'Back in Needs you.'),
                  child: const Text('Bring back')),
          ] else ...[
            const SizedBox(height: 8),
            if (it['dm_closed'] == true)
              const Text('Meta lets a business answer a DM only within 24 hours. Reply from the Instagram / Facebook app yourself.',
                  style: TextStyle(color: C.warn, fontSize: 12.5))
            else
              TextField(controller: ed, minLines: 1, maxLines: 5, decoration: const InputDecoration(labelText: 'Reply (edit before sending)')),
            if (it['needs_her'] == true && it['dm_closed'] != true)
              const Padding(padding: EdgeInsets.only(top: 4), child: Text('Check this one: it may need a fact only you know.',
                  style: TextStyle(color: C.warn, fontSize: 12))),
            const SizedBox(height: 6),
            Wrap(spacing: 8, children: [
              if (it['dm_closed'] != true)
                FilledButton(
                    onPressed: _busy ? null : () => _do(() => widget.app.api!.socialInboxReply(id, ed.text.trim()), 'Reply sent.'),
                    child: const Text('Send reply')),
              if (hideable)
                OutlinedButton(onPressed: _busy ? null : () => _do(() => widget.app.api!.socialInboxHide(id, true), 'Hidden. Nothing deleted.'),
                    child: const Text('Hide')),
              TextButton(onPressed: _busy ? null : () => _do(() => widget.app.api!.socialInboxSet(id, {'status': 'ignored'}), 'Moved to Done.'),
                  child: const Text('No reply needed')),
            ]),
          ],
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final counts = Map<String, dynamic>.from((d?['counts'] as Map?) ?? const {});
    final items = _list(d?['items']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Inbox')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: () async {
            try {
              await widget.app.api!.socialRun('inbox');
            } catch (_) {}
            await Future<void>.delayed(const Duration(seconds: 3));
            await _load();
          },
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final b in _boxes.entries)
                ChoiceChip(
                  label: Text('${b.value}${b.key == 'done' ? '' : ' ${_num(counts[b.key] ?? 0)}'}'),
                  selected: _box == b.key,
                  onSelected: (_) {
                    setState(() => _box = b.key);
                    _load();
                  },
                ),
            ]),
            const SizedBox(height: 10),
            if (d == null)
              const Center(child: CircularProgressIndicator())
            else if (items.isEmpty)
              const Padding(padding: EdgeInsets.only(top: 24), child: Text('Nothing here. Pull down to check Instagram / Facebook now.',
                  style: TextStyle(color: C.muted, fontSize: 13.5)))
            else
              for (final it in items) _item(it),
          ]),
        ),
      ),
    );
  }
}

/// v0.365 chat card for a new social lead / complaint: opens the Inbox.
class SocialCard extends StatelessWidget {
  const SocialCard({super.key, required this.kind, required this.v, required this.app});
  final String kind;
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SocialInboxScreen(app: app))),
      child: Glass(
        border: kind == 'social_alert' ? C.warn : null,
        child: Row(children: [
          Icon(kind == 'social_lead' ? Icons.person_add_alt_1_rounded : Icons.forum_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(v['text']), style: const TextStyle(fontWeight: FontWeight.w700))),
          const Icon(Icons.chevron_right_rounded, color: C.muted),
        ]),
      ),
    );
  }
}
