/// v0.317 HIRE AN EMPLOYEE (Profile > Employees): the Employee Hub (hire / pause / let go) and the SEO Desk of a
/// hired SEO Specialist (onboarding, KPIs against the baseline, the 90-day plan, alerts, schedule, run-now buttons).
/// A desk exists only while its employee is hired. Same server as the web console: /api/employees*, /api/seo/desk...
/// v0.319 SEO PRO on the desk: health in 7 parts, Google's index answer, AI search bots, trust (E-E-A-T), local score,
/// speed parts + phone screenshot, IndexNow, and "how we'll know" on every plan item.
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
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
      if (action == 'hire' && key == 'seo' && mounted) _openDesk();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  void _openDesk() => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => SeoDeskScreen(app: widget.app)))
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
              FilledButton.icon(onPressed: _busy ? null : _openDesk, icon: const Icon(Icons.dashboard_rounded), label: const Text('Open desk')),
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
            for (final e in _emps) _card(e),
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
Widget _bar(String label, num? score, num max) {
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
          width: 52,
          child: Text(score == null ? '–' : (max == 100 ? '$score' : '$score/$max'),
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
        for (final b in bots)
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
            for (final p in parts) _bar(_s(p['label']), p['ms'] as num?, mx),
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
