/// Profile > Performance marketer (v0.111 Ads Sahayak): reads her Meta / Google ad reports, finds where money leaks (in
/// rupees, against what a lead is worth to HER), suggests budget changes with reasons that wait for her tap (a raise needs
/// her fingerprint once a phone key is set up), writes ad copies to test and calls a winner only when the numbers say so.
/// Hoola never puts an ad live and never changes a budget by itself.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'attach.dart';
import 'employees_screen.dart' show MetaAdsScreen;
import 'glass.dart';
import 'desk/desk_kit.dart';

String _s(dynamic v) => v == null ? '' : '$v';
double _d(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

String rs(dynamic v) {
  if (v == null || '$v'.isEmpty) return '-';
  final n = _d(v);
  if (n.abs() >= 100000) return '₹${(n / 100000).toStringAsFixed(2)} lakh';
  final whole = n == n.roundToDouble() || n.abs() >= 100;
  final t = whole ? n.round().toString() : n.toStringAsFixed(2);
  final parts = t.split('.');
  final x = parts[0].replaceAllMapped(RegExp(r'(\d)(?=(\d\d)+\d$)'), (m) => '${m[1]},');
  return '₹$x${parts.length > 1 ? '.${parts[1]}' : ''}';
}

const _kindIcon = {
  'no_result': Icons.money_off_rounded,
  'high_cpl': Icons.trending_up_rounded,
  'fatigue': Icons.repeat_rounded,
  'low_ctr': Icons.touch_app_rounded,
  'search_terms': Icons.search_off_rounded,
  'lost_rank': Icons.leaderboard_rounded,
  'quality': Icons.grade_rounded,
  'placement': Icons.place_rounded,
};
const _chKind = {'pause': 'Rokna', 'resume': 'Turn on', 'budget': 'Budget', 'negative': 'Negative keyword', 'other': 'Change'};
const _chStatus = {
  'waiting': 'Waiting for your yes',
  'applied': 'Applied on Meta',
  'manual': 'You do it',
  'done': 'Done',
  'rejected': 'Mana',
  'failed': 'Not applied',
  'stale': 'Purana'
};

Color _stCol(String s) => switch (s) {
      'applied' || 'done' => C.ok,
      'waiting' => C.accent,
      'manual' => C.accent2,
      'failed' => C.bad,
      _ => C.faint,
    };

class AdsScreen extends StatefulWidget {
  const AdsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<AdsScreen> createState() => _AdsScreenState();
}

class _AdsScreenState extends State<AdsScreen> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d0;
  int _tick = -1;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _tick = app.adsTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.adsTick != _tick) {
      _tick = app.adsTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.adsAll();
      if (mounted) setState(() => _d0 = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() fn) async {
    setState(() => _busy = true);
    try {
      final r = await fn();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _import() async {
    final files = await pickAttachments(context, max: 1);
    if (files.isEmpty) return;
    await _run(() => app.api!.adsImport(files.first.name, files.first.bytes));
  }

  @override
  Widget build(BuildContext context) => DeskTabsScaffold(
          title: 'Performance marketer',
          tabs: ['Hisaab', 'Change', 'Copy', 'Niyam'],
          loading: _d0 == null,
          onRefresh: _load,
          pages: () => [
            _ReportTab(app: app, d: _d0!, busy: _busy, onImport: _import, run: _run),
                    _ChangesTab(app: app, changes: _list(_d0!['changes']), run: _run, onChanged: _load),
                    _CopyTab(app: app, tests: _list(_d0!['tests']), onChanged: _load),
                    _RulesTab(app: app, st: _map(_d0!['settings']), onChanged: _load),
          ],
        );
}

// ---------------------------------------------------------------- Hisaab
class _ReportTab extends StatelessWidget {
  const _ReportTab({required this.app, required this.d, required this.busy, required this.onImport, required this.run});
  final Santosh app;
  final Map<String, dynamic> d;
  final bool busy;
  final Future<void> Function() onImport;
  final Future<void> Function(Future<Map<String, dynamic>> Function()) run;

  @override
  Widget build(BuildContext context) {
    final rep = _map(d['report']);
    final st = _map(d['settings']);
    final meta = _map(st['meta']);
    final total = _map(rep['total']);
    final leaks = _list(rep['leaks']);
    final wins = _list(rep['winners']);
    final notes = _list(rep['notes']);
    final money = _map(rep['money']);
    final empty = rep['empty'] == true;
    final target = rep['target'];
    final cpl = total['cpl'];
    final over = target != null && cpl != null && _d(cpl) > _d(target);
    return RefreshIndicator(
      onRefresh: () async => run(() => app.api!.adsReport(30)),
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Row(children: [
          Expanded(child: GlassButton(label: 'Add a report', icon: Icons.upload_file_rounded, height: 44, onTap: busy ? null : onImport)),
          const SizedBox(width: 8),
          Expanded(
            child: GlassButton(
              label: meta['ready'] == true ? 'Meta se lao' : 'Meta jodo (Niyam)',
              icon: Icons.sync_rounded,
              height: 44,
              onTap: busy || meta['ready'] != true ? null : () => run(() => app.api!.adsMetaFetch(14)),
            ),
          ),
        ]),
        if (busy) const Padding(padding: EdgeInsets.all(12), child: LinearProgressIndicator()),
        const SizedBox(height: 12),
        if (empty)
          Glass(
            child: Text(_s(rep['say']).isEmpty
                ? 'Export a report from Meta Ads Manager or Google Ads (Reports > Export > CSV / Excel) and add it here.'
                : _s(rep['say'])),
          )
        else ...[
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${rep['from']} se ${rep['to']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 6),
              Wrap(spacing: 14, runSpacing: 10, children: [
                _stat('Kharcha', rs(total['spend'])),
                _stat('Result', '${_d(total['results']).round()}'),
                _stat('One result', rs(cpl), color: over ? C.bad : C.ok),
                if (target != null) _stat('Target', rs(target)),
                if (total['ctr'] != null) _stat('CTR', '${total['ctr']}%'),
                if (_d(rep['waste']) > 0) _stat('Being wasted', rs(rep['waste']), color: C.bad),
              ]),
              if (_s(rep['target_from']).isNotEmpty)
                Padding(padding: const EdgeInsets.only(top: 6), child: Text('Target: ${rep['target_from']}', style: const TextStyle(color: C.faint, fontSize: 12))),
              if (money.isNotEmpty) ...[
                const SizedBox(height: 8),
                if (money['cost_per_sale'] != null)
                  Text('Actual sales: ${money['sales']} · one sale ${rs(money['cost_per_sale'])}${money['real_roas'] != null ? ' · ROAS ${money['real_roas']}x' : ''}',
                      style: const TextStyle(color: C.chip)),
                if (money['telecall'] != null)
                  Text('Telecaller: ${_map(money['telecall'])['leads']} ad lead, ${_map(money['telecall'])['converted']} bike'
                      '${money['telecall_cost_per_sale'] != null ? ' · ${rs(money['telecall_cost_per_sale'])} per sale' : ''}',
                      style: const TextStyle(color: C.chip, fontSize: 13)),
              ],
              const SizedBox(height: 10),
              GradientButton(label: 'Make budget plan', icon: Icons.tune_rounded, height: 46, onTap: busy ? null : () => run(() => app.api!.adsPlan())),
              const SizedBox(height: 4),
              const Text('The plan is only a suggestion: every change is made only with your yes.', style: TextStyle(color: C.faint, fontSize: 12)),
            ]),
          ),
          if (leaks.isNotEmpty) ...[
            Padding(padding: const EdgeInsets.fromLTRB(4, 16, 4, 6), child: Text('Money is being wasted here', style: display(16))),
            for (final l in leaks)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Glass(
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(_kindIcon[_s(l['kind'])] ?? Icons.warning_amber_rounded, color: C.bad, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(_s(l['text']), style: const TextStyle(fontSize: 13.5)),
                        if (_s(l['fix']).isNotEmpty) Text(_s(l['fix']), style: const TextStyle(color: C.accent, fontSize: 12.5)),
                      ]),
                    ),
                    if (_d(l['waste']) > 0) Pill(rs(l['waste']), fg: C.bad),
                  ]),
                ),
              ),
          ],
          if (wins.isNotEmpty) ...[
            Padding(padding: const EdgeInsets.fromLTRB(4, 12, 4, 6), child: Text('Doing well', style: display(16))),
            for (final w in wins)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.emoji_events_rounded, color: C.ok),
                title: Text(_s(w['text'])),
              ),
          ],
          for (final n in notes)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Glass(child: Row(children: [const Icon(Icons.lightbulb_rounded, color: C.accent2, size: 18), const SizedBox(width: 8), Expanded(child: Text(_s(n['text'])))])),
            ),
          const SizedBox(height: 10),
          Text('India estimate (${_map(rep['benchmark'])['segment']}): ${_map(rep['benchmark'])['note']}', style: const TextStyle(color: C.faint, fontSize: 11.5)),
        ],
        const SizedBox(height: 12),
        GlassButton(label: 'Enter actual sales', icon: Icons.point_of_sale_rounded, height: 40, onTap: () => _sale(context)),
      ]),
    );
  }

  Widget _stat(String label, String value, {Color color = C.ink}) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: const TextStyle(color: C.muted, fontSize: 11.5)),
        Text(value, style: display(17, color: color)),
      ]);

  Future<void> _sale(BuildContext context) async {
    final camp = TextEditingController();
    final count = TextEditingController(text: '1');
    final value = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('How many sales came from ads?'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: camp, decoration: const InputDecoration(labelText: 'Campaign (optional)')),
          TextField(controller: count, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'How many sales')),
          TextField(controller: value, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Total amount (₹)')),
        ]),
        actions: [FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Save'))],
      ),
    );
    if (ok != true) return;
    await run(() => app.api!.adsSale({'campaign': camp.text.trim(), 'count': int.tryParse(count.text.trim()) ?? 1, 'value': double.tryParse(value.text.trim()) ?? 0}));
  }
}

// ---------------------------------------------------------------- Badlav
class _ChangesTab extends StatelessWidget {
  const _ChangesTab({required this.app, required this.changes, required this.run, required this.onChanged});
  final Santosh app;
  final List<Map<String, dynamic>> changes;
  final Future<void> Function(Future<Map<String, dynamic>> Function()) run;
  final Future<void> Function() onChanged;
  @override
  Widget build(BuildContext context) {
    final waiting = changes.where((c) => c['status'] == 'waiting').toList();
    final rest = changes.where((c) => c['status'] != 'waiting').toList();
    return RefreshIndicator(
      onRefresh: onChanged,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        if (changes.isEmpty)
          const Padding(padding: EdgeInsets.all(20), child: Text('No changes yet. In the report, tap "Make budget plan".', style: TextStyle(color: C.muted))),
        if (waiting.isNotEmpty) Padding(padding: const EdgeInsets.fromLTRB(4, 4, 4, 8), child: Text('Needs your yes (${waiting.length})', style: display(16))),
        for (final c in waiting) Padding(padding: const EdgeInsets.only(bottom: 10), child: AdsChangeTile(app: app, c: c, onDone: onChanged)),
        if (rest.isNotEmpty) Padding(padding: const EdgeInsets.fromLTRB(4, 12, 4, 8), child: Text('Earlier', style: display(16))),
        for (final c in rest) Padding(padding: const EdgeInsets.only(bottom: 10), child: AdsChangeTile(app: app, c: c, onDone: onChanged)),
      ]),
    );
  }
}

/// One change: what, why, what it should do, and her Haan / Mana (a raise can be edited first).
class AdsChangeTile extends StatefulWidget {
  const AdsChangeTile({super.key, required this.app, required this.c, this.onDone});
  final Santosh app;
  final Map<String, dynamic> c;
  final Future<void> Function()? onDone;
  @override
  State<AdsChangeTile> createState() => _AdsChangeTileState();
}

class _AdsChangeTileState extends State<AdsChangeTile> {
  bool _busy = false;
  late Map<String, dynamic> c = widget.c;

  @override
  void didUpdateWidget(covariant AdsChangeTile old) {
    super.didUpdateWidget(old);
    c = widget.c;
  }

  Future<void> _do(Future<Map<String, dynamic>> Function() fn) async {
    setState(() => _busy = true);
    try {
      final r = await fn();
      if (r['change'] is Map) setState(() => c = Map<String, dynamic>.from(r['change'] as Map));
      if (mounted) _snack(context, _s(r['say']));
      await widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _yes() async {
    double? after;
    if (c['kind'] == 'budget') {
      final ctl = TextEditingController(text: _d(c['after']).round().toString());
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text('${c['target']}: daily budget'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('Now ${rs(c['before'])}. Sujhav ${rs(c['after'])}.', style: const TextStyle(fontSize: 13)),
            TextField(controller: ctl, keyboardType: TextInputType.number, decoration: const InputDecoration(prefixText: '₹ ')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
            FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Yes, apply')),
          ],
        ),
      );
      if (ok != true) return;
      after = double.tryParse(ctl.text.trim());
    }
    await _do(() => widget.app.api!.adsDecide(_s(c['id']), true, after: after));
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(c['status']);
    final oc = _map(c['outcome']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${c['number']} · ${_chKind[_s(c['kind'])] ?? c['kind']} · ${c['target']}', style: display(14.5), maxLines: 2, overflow: TextOverflow.ellipsis)),
          Pill(_chStatus[st] ?? st, fg: _stCol(st)),
        ]),
        if (c['kind'] == 'budget')
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('${rs(c['before'])} → ${rs(c['after'])} per day', style: TextStyle(color: c['spends_more'] == true ? C.accent : C.ok, fontWeight: FontWeight.w700)),
          ),
        const SizedBox(height: 4),
        Text(_s(c['reason']), style: const TextStyle(color: C.chip, fontSize: 13)),
        if (_s(c['expect']).isNotEmpty) Text('Ummeed: ${c['expect']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        if (st == 'manual' || st == 'failed') ...[
          const SizedBox(height: 6),
          Text(_s(c['steps']), style: const TextStyle(color: C.accent2, fontSize: 12.5)),
          if (_s(c['error']).isNotEmpty) Text(_s(c['error']), style: const TextStyle(color: C.bad, fontSize: 12)),
        ],
        if (oc.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text('Impact: ${oc['say']}', style: const TextStyle(color: C.teal, fontSize: 12.5))),
        const SizedBox(height: 8),
        if (_busy)
          const LinearProgressIndicator()
        else if (st == 'waiting')
          Row(children: [
            Expanded(child: GlassButton(label: 'Mana', color: C.bad, height: 42, onTap: () => _do(() => widget.app.api!.adsDecide(_s(c['id']), false)))),
            const SizedBox(width: 8),
            Expanded(child: GradientButton(label: c['spends_more'] == true ? 'Yes (cost will rise)' : 'Yes', height: 42, onTap: _yes)),
          ])
        else if (st == 'manual' || st == 'failed')
          GlassButton(label: 'I did it', icon: Icons.check_rounded, height: 40, onTap: () => _do(() => widget.app.api!.adsDone(_s(c['id'])))),
        if (st == 'waiting' && c['can_apply'] != true)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('After your yes you will get the Ads Manager steps (if your Meta account is linked, Hoola will apply it itself).', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Copy
class _CopyTab extends StatefulWidget {
  const _CopyTab({required this.app, required this.tests, required this.onChanged});
  final Santosh app;
  final List<Map<String, dynamic>> tests;
  final Future<void> Function() onChanged;
  @override
  State<_CopyTab> createState() => _CopyTabState();
}

class _CopyTabState extends State<_CopyTab> {
  String _platform = 'meta';
  final _brief = TextEditingController();
  final _campaign = TextEditingController();
  bool _busy = false;

  Future<void> _write() async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.adsCopies({'brief': _brief.text.trim(), 'platform': _platform, 'campaign': _campaign.text.trim(),
        'conversation_id': widget.app.conversationId ?? ''});
      if (mounted) _snack(context, _s(r['say']));
      await widget.onChanged();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('New ad copy (to test)', style: display(16)),
            const SizedBox(height: 8),
            Wrap(spacing: 6, children: [
              ChoiceChip(label: const Text('Meta (FB / Insta)'), selected: _platform == 'meta', onSelected: (_) => setState(() => _platform = 'meta')),
              ChoiceChip(label: const Text('Google search'), selected: _platform == 'google', onSelected: (_) => setState(() => _platform = 'google')),
            ]),
            TextField(controller: _brief, minLines: 2, maxLines: 5, decoration: const InputDecoration(labelText: 'What to sell / offer (in your own words)')),
            TextField(controller: _campaign, decoration: const InputDecoration(labelText: 'Campaign (optional)')),
            const SizedBox(height: 10),
            _busy ? const Center(child: CircularProgressIndicator()) : GradientButton(label: 'Write copy', icon: Icons.edit_rounded, height: 46, onTap: _write),
            const SizedBox(height: 4),
            Text('${widget.app.aName} writes only from your facts; you put the ad into Ads Manager yourself.', style: const TextStyle(color: C.faint, fontSize: 12)),
          ]),
        ),
        for (final t in widget.tests) Padding(padding: const EdgeInsets.only(top: 12), child: AdsTestCard(app: widget.app, t: t, onChanged: widget.onChanged)),
      ]);
}

String copyText(Map<String, dynamic> c) {
  final f = _map(c['fields']);
  if (c['platform'] == 'google') {
    return [
      'Headlines:',
      for (final h in _list(f['headlines'])) '- ${h['text']}',
      'Descriptions:',
      for (final d in _list(f['descriptions'])) '- ${d['text']}',
      if ((f['paths'] as List?)?.isNotEmpty == true) 'Paths: ${(f['paths'] as List).join(' / ')}',
    ].join('\n');
  }
  return 'Primary text: ${f['primary']}\nHeadline: ${f['headline']}\nDescription: ${f['description']}\nButton: ${f['cta']}';
}

class AdsTestCard extends StatelessWidget {
  const AdsTestCard({super.key, required this.app, required this.t, this.onChanged});
  final Santosh app;
  final Map<String, dynamic> t;
  final Future<void> Function()? onChanged;

  Future<void> _result(BuildContext context) async {
    final copies = _list(t['copies']);
    final ctl = {for (final c in copies) _s(c['label']): [TextEditingController(), TextEditingController(), TextEditingController(), TextEditingController()]};
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Numbers for each copy'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final e in ctl.entries) ...[
              Align(alignment: Alignment.centerLeft, child: Text('Copy ${e.key}', style: const TextStyle(fontWeight: FontWeight.w700))),
              Row(children: [
                for (var i = 0; i < 4; i++)
                  Expanded(child: Padding(padding: const EdgeInsets.only(right: 4), child: TextField(controller: e.value[i], keyboardType: TextInputType.number, decoration: InputDecoration(labelText: const ['Impr.', 'Clicks', 'Result', '₹'][i])))),
              ]),
            ],
          ]),
        ),
        actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Check'))],
      ),
    );
    if (ok != true) return;
    final res = {
      for (final e in ctl.entries)
        e.key: {
          'impressions': double.tryParse(e.value[0].text) ?? 0,
          'clicks': double.tryParse(e.value[1].text) ?? 0,
          'results': double.tryParse(e.value[2].text) ?? 0,
          'spend': double.tryParse(e.value[3].text) ?? 0
        }
    };
    try {
      final r = await app.api!.adsTestAct(_s(t['id']), 'result', {'results': res});
      if (context.mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged?.call();
  }

  @override
  Widget build(BuildContext context) {
    final plan = _map(t['plan']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${t['number']} · ${t['platform'] == 'google' ? 'Google' : 'Meta'}${_s(t['campaign']).isNotEmpty ? ' · ${t['campaign']}' : ''}', style: display(15))),
          Pill(_s(t['status']) == 'decided' ? 'Decided' : (_s(t['status']) == 'running' ? 'Running' : 'Draft'), fg: C.accent),
        ]),
        if (_s(plan['say']).isNotEmpty) Text(_s(plan['say']), style: const TextStyle(color: C.muted, fontSize: 12)),
        if (_s(t['verdict']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(t['verdict']), style: const TextStyle(color: C.teal, fontSize: 13))),
        for (final c in _list(t['copies']))
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: c['status'] == 'won' ? C.ok : C.line)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Text('${c['label']} · ${c['angle']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  const Spacer(),
                  if (c['status'] == 'won') const Pill('Jeeta', fg: C.ok),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.copy_rounded, size: 18),
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: copyText(c)));
                      _snack(context, 'Copy ${c['label']} copied');
                    },
                  ),
                ]),
                SelectableText(copyText(c), style: const TextStyle(color: C.chip, fontSize: 13, height: 1.35)),
                for (final x in _list(c['checks']))
                  Text('${x['level'] == 'block' ? '⛔' : '⚠'} ${x['text']}', style: TextStyle(color: x['level'] == 'block' ? C.bad : C.warn, fontSize: 12)),
              ]),
            ),
          ),
        const SizedBox(height: 8),
        Row(children: [
          if (_s(t['status']) == 'draft')
            Expanded(
              child: GlassButton(
                label: 'I made them live',
                height: 40,
                onTap: () async {
                  try {
                    final r = await app.api!.adsTestAct(_s(t['id']), 'live', {});
                    if (context.mounted) _snack(context, _s(r['say']));
                  } catch (e) {
                    if (context.mounted) _snack(context, '$e');
                  }
                  await onChanged?.call();
                },
              ),
            ),
          if (_s(t['status']) != 'decided') ...[
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Enter a number', height: 40, onTap: () => _result(context))),
          ],
        ]),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Niyam
class _RulesTab extends StatelessWidget {
  const _RulesTab({required this.app, required this.st, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> st;
  final Future<void> Function() onChanged;

  Future<void> _save(BuildContext context, Map<String, dynamic> body) async {
    try {
      await app.api!.adsSettings(body);
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  Future<void> _meta(BuildContext context) async {
    final acct = TextEditingController(text: _s(_map(st['meta'])['account']));
    final tok = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Connect Meta ad account'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Meta Business Settings > Users > System users > "Hoola" and give it the ad account (Manage campaigns), then Generate '
                'token: ads_read + ads_management. Enter the token here; never in the chat.', style: TextStyle(fontSize: 12.5)),
            TextField(controller: acct, decoration: const InputDecoration(labelText: 'Ad account ID (act_...)')),
            TextField(controller: tok, obscureText: true, enableSuggestions: false, autocorrect: false, decoration: const InputDecoration(labelText: 'Token')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Keep it')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodo')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.adsMeta(acct.text.trim(), tok.text.trim());
      if (context.mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    tok.clear();
    await onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final meta = _map(st['meta']);
    final segs = _map(st['segments']);
    Widget row(String key, String label, String value, {bool number = false, int lines = 1}) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: Text(value.isEmpty || value == '0' || value == '0.0' ? '-' : value, maxLines: 3, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.edit_rounded, size: 18),
          onTap: () async {
            final c = TextEditingController(text: value == '0' || value == '0.0' ? '' : value);
            final ok = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(
                title: Text(label),
                content: TextField(controller: c, minLines: lines, maxLines: lines > 1 ? 6 : 1, keyboardType: number ? TextInputType.number : TextInputType.text),
                actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
              ),
            );
            if (ok == true && context.mounted) await _save(context, {key: number ? (double.tryParse(c.text.trim()) ?? 0) : c.text.trim()});
          },
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('What one lead is worth to you', style: display(16)),
          const SizedBox(height: 4),
          Text(st['max_cpl'] != null ? 'By this math, a lead costing more than ${rs(st['max_cpl'])} means a loss.' : 'Tell Hoola the order value, margin and how many leads turn into sales; it will then work out the right target.',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          row('avg_order', 'Value of one sale (₹)', '${st['avg_order']}', number: true),
          row('margin_pct', 'Margin %', '${st['margin_pct']}', number: true),
          row('close_pct', 'How many of 100 leads buy (%)', '${st['close_pct']}', number: true),
          row('target_cpl', 'My target: cost of one result (₹)', '${st['target_cpl']}', number: true),
          row('month_budget', 'Monthly ad budget (₹)', '${st['month_budget']}', number: true),
          row('max_step_pct', 'How much the budget may change at once (%)', '${st['max_step_pct']}', number: true),
          if (_s(st['target_from']).isNotEmpty) Text('Current target: ${rs(st['target'])} (${st['target_from']})', style: const TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          row('business', 'Business', _s(st['business'])),
          row('offer', 'What you sell / offer', _s(st['offer']), lines: 3),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 4, children: [
            for (final e in segs.entries)
              ChoiceChip(label: Text(_s(e.value)), selected: st['segment'] == e.key, onSelected: (_) => _save(context, {'segment': e.key})),
          ]),
          row('report_time', 'When for the daily check / weekly report', _s(st['report_time'])),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.campaign_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('Meta ad account', style: display(16))),
            Pill(meta['ready'] == true ? 'Juda hai' : 'Not connected', fg: meta['ready'] == true ? C.ok : C.faint),
          ]),
          if (meta['ready'] == true) Text('${meta['name']} · ${meta['account']} · ${meta['currency']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (meta['linked'] == true && meta['ready'] != true)
            const Text('Connected to Facebook - now choose the ad account (Facebook & Instagram ads).', style: TextStyle(color: C.warn, fontSize: 12.5)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
                child: GlassButton(
                    label: meta['linked'] == true ? 'Connect again' : 'Facebook se jodo',
                    icon: Icons.link_rounded,
                    height: 42,
                    onTap: () async {
                      try {
                        final url = await app.api!.adsMetaConnect();
                        await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                      } catch (e) {
                        if (context.mounted) _snack(context, '$e');
                      }
                    })),
            if (meta['linked'] == true) ...[
              const SizedBox(width: 8),
              Expanded(
                child: GlassButton(label: 'Hatao', color: C.bad, height: 42, onTap: () async {
                  await app.api!.adsMetaOff();
                  await onChanged();
                }),
              ),
            ],
          ]),
          Row(children: [
            if (meta['linked'] == true)
              TextButton(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MetaAdsScreen(app: app))),
                  child: const Text('Make a new ad')),
            const Spacer(),
            TextButton(onPressed: () => _meta(context), child: const Text('Token se jodo', style: TextStyle(fontSize: 12))),
          ]),
          const SizedBox(height: 6),
          const Text('Once linked, Hoola brings the report every day; budget changes / pausing only with your yes. A new ad is created PAUSED in Meta, and Start happens only on your tap. '
              'Google Ads: export a report and add it here.', style: TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- chat cards
class AdsPlanCard extends StatelessWidget {
  const AdsPlanCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final cs = _list(v['changes']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.tune_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Ad changes: your yes', style: display(16))),
          if (_d(v['daily_saved']) > 0) Pill('${rs(v['daily_saved'])}/din bachat', fg: C.ok),
        ]),
        if (_s(v['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(v['say']), style: const TextStyle(color: C.muted, fontSize: 12.5))),
        for (final c in cs) Padding(padding: const EdgeInsets.only(top: 10), child: AdsChangeTile(app: app, c: c)),
      ]),
    );
  }
}

class AdsReportCard extends StatelessWidget {
  const AdsReportCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final leaks = _list(v['leaks']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.campaign_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(v['kind'] == 'weekly' ? 'Weekly ads report' : 'Ads ka hisaab', style: display(16))),
          if (_d(v['waste']) > 0) Pill('${rs(v['waste'])} being wasted', fg: C.bad),
        ]),
        const SizedBox(height: 6),
        Text(_s(v['say']), style: const TextStyle(color: C.chip, height: 1.35)),
        for (final l in leaks.take(3)) Padding(padding: const EdgeInsets.only(top: 4), child: Text('• ${l['text']}', style: const TextStyle(fontSize: 12.5, color: C.muted))),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AdsScreen(app: app))), child: const Text('View all')),
        ),
      ]),
    );
  }
}

class AdsCopyCard extends StatelessWidget {
  const AdsCopyCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => AdsTestCard(app: app, t: _map(v['test']));
}
