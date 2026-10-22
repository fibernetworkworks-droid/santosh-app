/// Profile > Payroll officer (v0.94): Hoola runs the monthly salary end to end.
/// Aaj (salary / PF / ESIC / TDS due and late), Log (employees: pay split, UAN, ESIC, PAN + bank masked), Salary (make
/// the month's run, see every line and check, Haan / Mana, files: payslips, register, bank file, ECR, ESIC sheet; mark
/// paid after SHE pays), Niyam (company, state, PF / ESIC, minimum wage). Hoola never pays or logs in to a bank.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';
import 'gst_screen.dart' show rs;

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

List<String> _months() {
  final now = DateTime.now();
  return [
    for (var i = 0; i <= 12; i++)
      () {
        final d = DateTime(now.year, now.month - i, 1);
        return '${d.year}-${d.month.toString().padLeft(2, '0')}';
      }()
  ];
}

String _nice(String p) {
  const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  final x = p.split('-');
  if (x.length != 2) return p;
  return '${m[((int.tryParse(x[1]) ?? 1) - 1).clamp(0, 11)]} ${x[0]}';
}

Color _col(String s) => switch (s) {
      'paid' => C.ok,
      'ready' => C.accent,
      'approved' => C.teal,
      'rejected' => C.faint,
      _ => C.muted,
    };

mixin _PayLive<T extends StatefulWidget> on State<T> {
  Santosh get app;
  int _tick = -1;
  Future<void> reload();
  void _onApp() {
    if (app.payTick != _tick) {
      _tick = app.payTick;
      reload();
    }
  }

  void startLive() {
    _tick = app.payTick;
    app.addListener(_onApp);
    reload();
  }

  void stopLive() => app.removeListener(_onApp);
}

class PayrollScreen extends StatelessWidget {
  const PayrollScreen({super.key, required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: const Text('Payroll officer'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Aaj'),
              Tab(text: 'Log'),
              Tab(text: 'Salary'),
              Tab(text: 'Niyam'),
            ]),
          ),
          body: Aurora(
            child: TabBarView(children: [_TodayTab(app: app), _PeopleTab(app: app), _RunsTab(app: app), _RulesTab(app: app)]),
          ),
        ),
      );
}

class _TodayTab extends StatefulWidget {
  const _TodayTab({required this.app});
  final Santosh app;
  @override
  State<_TodayTab> createState() => _TodayTabState();
}

class _TodayTabState extends State<_TodayTab> with _PayLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final d = await app.api!.payToday();
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    if (d == null) return const Center(child: CircularProgressIndicator());
    Widget row(Map<String, dynamic> x, bool late) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            border: late ? C.bad : null,
            child: Row(children: [
              Icon(late ? Icons.warning_amber_rounded : Icons.event_rounded, color: late ? C.bad : C.accent),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(x['label']), style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text('${_s(x['period_nice'])}${_s(x['period_nice']).isEmpty ? '' : ' · '}${late ? 'late' : 'due'} ${_s(x['due_nice'])}',
                      style: TextStyle(color: late ? C.bad : C.muted, fontSize: 12.5)),
                ]),
              ),
            ]),
          ),
        );
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        Glass(child: Text(_s(d['text']), style: const TextStyle(fontSize: 15, height: 1.35))),
        const SizedBox(height: 12),
        if ((d['employees'] ?? 0) == 0)
          const Glass(
              child: Text('Pehle log jodiye (Log > Naya employee), ya Hoola se boliye: "Ramesh Patil, 1 Jan 2019 se, 30,000 mahina, '
                  'basic 15,000".', style: TextStyle(color: C.muted))),
        for (final x in _list(d['late'])) row(x, true),
        for (final x in _list(d['due'])) row(x, false),
      ]),
    );
  }
}

class _PeopleTab extends StatefulWidget {
  const _PeopleTab({required this.app});
  final Santosh app;
  @override
  State<_PeopleTab> createState() => _PeopleTabState();
}

class _PeopleTabState extends State<_PeopleTab> with _PayLive {
  @override
  Santosh get app => widget.app;
  List<Map<String, dynamic>> _e = [];

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final e = await app.api!.payEmployees();
      if (mounted) setState(() => _e = e);
    } catch (_) {}
  }

  Future<void> _edit([Map<String, dynamic>? e]) async {
    final pay = Map<String, dynamic>.from((e?['pay'] as Map?) ?? const {});
    final c = {
      for (final k in ['name', 'phone', 'designation', 'doj', 'basic', 'da', 'hra', 'special', 'uan', 'esic_ip', 'pan', 'account', 'ifsc'])
        k: TextEditingController(
            text: switch (k) {
          'name' || 'phone' || 'designation' || 'doj' || 'uan' || 'esic_ip' => _s(e?[k]),
          'basic' || 'da' || 'hra' || 'special' => pay[k] == null ? '' : '${(pay[k] as num).round()}',
          _ => '',
        })
    };
    var gender = _s(e?['gender']).isEmpty ? 'M' : _s(e?['gender']);
    var regime = _s(e?['regime']).isEmpty ? 'new' : _s(e?['regime']);
    const labels = {
      'name': 'Naam',
      'phone': 'Phone',
      'designation': 'Kaam / pad',
      'doj': 'Joining date (2025-01-31)',
      'basic': 'Basic (mahina)',
      'da': 'DA',
      'hra': 'HRA',
      'special': 'Special / baaki',
      'uan': 'UAN (12 ank)',
      'esic_ip': 'ESIC IP (10 ank)',
      'pan': 'PAN (sirf naya daalna ho to)',
      'account': 'Bank account (sirf naya ho to)',
      'ifsc': 'IFSC',
    };
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => Padding(
          padding: EdgeInsets.fromLTRB(12, 40, 12, 12 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Glass(
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(e == null ? 'Naya employee' : _s(e['name']), style: display(17)),
                for (final k in c.keys)
                  TextField(
                    controller: c[k],
                    keyboardType: ['basic', 'da', 'hra', 'special', 'uan', 'esic_ip', 'account', 'phone'].contains(k)
                        ? TextInputType.number
                        : TextInputType.text,
                    textCapitalization: ['pan', 'ifsc'].contains(k) ? TextCapitalization.characters : TextCapitalization.none,
                    decoration: InputDecoration(
                        labelText: labels[k],
                        helperText: k == 'pan' && e != null
                            ? 'Abhi: ${_s(e['pan'])}'
                            : k == 'account' && e != null
                                ? 'Abhi: ${_s((e['bank'] as Map?)?['account'])}'
                                : null),
                  ),
                const SizedBox(height: 8),
                Wrap(spacing: 8, children: [
                  for (final g in const ['M', 'F'])
                    ChoiceChip(label: Text(g == 'M' ? 'Purush' : 'Mahila'), selected: gender == g, onSelected: (_) => setS(() => gender = g)),
                  for (final r in const ['new', 'old'])
                    ChoiceChip(label: Text('$r regime'), selected: regime == r, onSelected: (_) => setS(() => regime = r)),
                ]),
                const SizedBox(height: 12),
                GradientButton(label: 'Save', icon: Icons.check_rounded, onTap: () => Navigator.pop(ctx, true)),
              ]),
            ),
          ),
        ),
      ),
    );
    if (ok != true) return;
    double? n(String k) => double.tryParse(c[k]!.text.replaceAll(',', '').trim());
    final body = <String, dynamic>{
      if (e != null) 'employee': e['id'],
      'name': c['name']!.text.trim(),
      'gender': gender,
      'regime': regime,
      'pay': {for (final k in ['basic', 'da', 'hra', 'special']) if (n(k) != null) k: n(k)},
      for (final k in ['phone', 'designation', 'doj', 'uan', 'esic_ip', 'pan', 'account', 'ifsc'])
        if (c[k]!.text.trim().isNotEmpty) k: c[k]!.text.trim(),
    };
    if ((body['pay'] as Map).isEmpty) body.remove('pay');
    try {
      final r = await app.api!.paySaveEmployee(body);
      if (mounted) _snack(context, _s(r['say']));
      reload();
    } catch (err) {
      if (mounted) _snack(context, '$err');
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        GradientButton(label: 'Naya employee', icon: Icons.person_add_alt_1_rounded, onTap: () => _edit()),
        const SizedBox(height: 12),
        for (final e in _e)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _edit(e),
              child: Glass(
                child: Row(children: [
                  const Icon(Icons.badge_rounded, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${_s(e['name'])} (${_s(e['code'])})', style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text(
                          [
                            rs(e['monthly_gross'] ?? 0),
                            if (_s(e['designation']).isNotEmpty) _s(e['designation']),
                            if (_s(e['uan']).isEmpty) 'UAN nahi',
                            if (_s((e['bank'] as Map?)?['account']).isEmpty) 'bank nahi',
                          ].join(' · '),
                          style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                ]),
              ),
            ),
          ),
      ]);
}

class _RunsTab extends StatefulWidget {
  const _RunsTab({required this.app});
  final Santosh app;
  @override
  State<_RunsTab> createState() => _RunsTabState();
}

class _RunsTabState extends State<_RunsTab> with _PayLive {
  @override
  Santosh get app => widget.app;
  List<Map<String, dynamic>> _r = [];
  String _period = _months()[1];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final r = await app.api!.payRuns();
      if (mounted) setState(() => _r = r);
    } catch (_) {}
  }

  Future<void> _make() async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.payMakeRun(_period);
      if (mounted) _snack(context, _s(r['say']));
      final id = _s((r['run'] as Map?)?['id']);
      if (mounted && id.isNotEmpty) {
        await Navigator.of(context).push(MaterialPageRoute(builder: (_) => PayRunPage(app: app, id: id)));
      }
      reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _sheet() async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    try {
      final r = await app.api!.payImportAttendance(_period, f.name, f.bytes!);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            DropdownButton<String>(
              value: _period,
              isExpanded: true,
              items: [for (final p in _months()) DropdownMenuItem(value: p, child: Text(_nice(p)))],
              onChanged: (v) => setState(() => _period = v ?? _period),
            ),
            const Text('Chhutti / OT chat mein bataiye ("Ramesh 2 din chhutti, Suresh 6 ghante OT") ya hazri ki sheet daaliye.',
                style: TextStyle(color: C.faint, fontSize: 12)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              GlassButton(label: 'Hazri sheet', icon: Icons.upload_file_rounded, onTap: _sheet),
              GradientButton(label: _busy ? 'Ruko...' : 'Salary banao', icon: Icons.payments_rounded, onTap: _busy ? null : _make),
            ]),
          ]),
        ),
        const SizedBox(height: 12),
        for (final r in _r)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PayRunPage(app: app, id: _s(r['id'])))),
              child: Glass(
                border: r['status'] == 'ready' ? C.accent : null,
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${_s(r['period_nice'])}${r['kind'] == 'fnf' ? ' · full & final' : ''}', style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text('${(r['totals'] as Map?)?['employees'] ?? 0} log · net ${rs((r['totals'] as Map?)?['net'] ?? 0)}',
                          style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                  Pill(_s(r['status_label']), fg: _col(_s(r['status'])), bg: _col(_s(r['status'])).withOpacity(.16)),
                ]),
              ),
            ),
          ),
      ]);
}

class PayRunPage extends StatelessWidget {
  const PayRunPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Salary')),
        body: Aurora(child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [PayRunView(app: app, id: id)])),
      );
}

/// Chat card for a salary run waiting for her Haan (event `payroll_run`).
class PayRunCard extends StatelessWidget {
  const PayRunCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => PayRunView(app: app, id: _s(v['run_id']), compact: true);
}

class PayDayCard extends StatelessWidget {
  const PayDayCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PayrollScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.payments_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text('Payroll: ${_s(v['text'])}', style: const TextStyle(height: 1.3))),
          ]),
        ),
      );
}

class PayRunView extends StatefulWidget {
  const PayRunView({super.key, required this.app, required this.id, this.compact = false});
  final Santosh app;
  final String id;
  final bool compact;
  @override
  State<PayRunView> createState() => _PayRunViewState();
}

class _PayRunViewState extends State<PayRunView> with _PayLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _r;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    if (widget.id.isEmpty) return;
    try {
      final r = await app.api!.payRun(widget.id);
      if (mounted) setState(() => _r = r);
    } catch (_) {}
  }

  Future<void> _act(String a, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.payRunAct(widget.id, a, {...body, 'conversation_id': app.conversationId ?? ''});
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      if (a == 'drafts' && mounted) {
        final text = _list(r['drafts']).map((d) => '${_s(d['employee'])} (${_s(d['to'])}):\n${_s(d['text'])}').join('\n\n');
        await Clipboard.setData(ClipboardData(text: text));
        if (mounted) _snack(context, 'Sab payslip message copy ho gaye');
      }
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _kv(String k, String v, {Color? c}) => Padding(
        padding: const EdgeInsets.only(top: 3),
        child: Row(children: [
          Expanded(child: Text(k, style: const TextStyle(color: C.muted, fontSize: 13))),
          Text(v, style: TextStyle(fontWeight: FontWeight.w700, color: c ?? C.ink)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final r = _r;
    if (r == null) return const Glass(child: Center(child: CircularProgressIndicator(strokeWidth: 2)));
    final st = _s(r['status']);
    final t = Map<String, dynamic>.from((r['totals'] as Map?) ?? const {});
    final checks = List<String>.from(((r['checks'] as List?) ?? const []).map((e) => '$e'));
    final lines = _list(r['lines']);
    return Glass(
      border: st == 'ready' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.payments_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Salary · ${_s(r['period_nice'])}${r['kind'] == 'fnf' ? ' · full & final' : ''}', style: display(15))),
          Pill(_s(r['status_label']), fg: _col(st), bg: _col(st).withOpacity(.16)),
        ]),
        const SizedBox(height: 6),
        _kv('Log', '${t['employees'] ?? 0}'),
        _kv('Kul pagaar (gross)', rs(t['gross'] ?? 0)),
        _kv('Haath mein (net)', rs(t['net'] ?? 0), c: C.accent),
        if (t['pf_challan'] != null) _kv('PF challan', rs(t['pf_challan'] ?? 0)),
        if (t['esi_challan'] != null) _kv('ESIC', rs(t['esi_challan'] ?? 0)),
        if (t['tds'] != null) _kv('TDS / PT', '${rs(t['tds'] ?? 0)} / ${rs(t['pt'] ?? 0)}'),
        if (t['cost'] != null) _kv('Company ka kharcha', rs(t['cost'] ?? 0)),
        for (final c in checks.take(widget.compact ? 3 : 30))
          Padding(
            padding: const EdgeInsets.only(top: 5),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.info_outline_rounded, size: 15, color: C.warn),
              const SizedBox(width: 6),
              Expanded(child: Text(c, style: const TextStyle(color: C.chip, fontSize: 12.5))),
            ]),
          ),
        if (!widget.compact) ...[
          const SizedBox(height: 10),
          for (final ln in lines)
            Container(
              margin: const EdgeInsets.only(top: 6),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${_s(ln['name'])} (${_s(ln['code'])})', style: const TextStyle(fontWeight: FontWeight.w800))),
                  Text(rs(ln['net'] ?? 0), style: const TextStyle(fontWeight: FontWeight.w800, color: C.accent)),
                ]),
                Text(
                    'Din ${ln['paid_days']}/${ln['days']}${(ln['ot'] ?? 0) > 0 ? ' · OT ${rs(ln['ot'])}' : ''} · gross ${rs(ln['gross'] ?? 0)} · '
                    'PF ${rs((ln['pf'] as Map?)?['ee'] ?? 0)} · ESIC ${rs((ln['esi'] as Map?)?['ee'] ?? 0)} · PT ${rs(ln['pt'] ?? 0)} · '
                    'TDS ${rs(ln['tds'] ?? 0)}${(ln['advance'] ?? 0) > 0 ? ' · advance ${rs(ln['advance'])}' : ''}',
                    style: const TextStyle(color: C.muted, fontSize: 12)),
                if ((ln['fnf'] as Map?) != null)
                  Text(
                      'Full & final: chhutti ${rs((ln['fnf'] as Map)['leave_encashment'] ?? 0)}, gratuity '
                      '${rs(((ln['fnf'] as Map)['gratuity'] as Map?)?['amount'] ?? 0)}, recovery ${rs((ln['fnf'] as Map)['recoveries'] ?? 0)} = '
                      '${rs((ln['fnf'] as Map)['net_payable'] ?? 0)} · ${_s((ln['fnf'] as Map)['pay_by'])} tak',
                      style: const TextStyle(color: C.warn, fontSize: 12)),
              ]),
            ),
        ],
        const SizedBox(height: 10),
        if (st == 'ready' || st == 'rejected')
          Row(children: [
            Expanded(child: GlassButton(label: 'Haan, theek hai', icon: Icons.check_rounded, color: C.ok, onTap: _busy ? null : () => _act('decide', {'approve': true}))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, color: C.bad, onTap: _busy ? null : () => _act('decide', {'approve': false}))),
          ]),
        if (st == 'approved' || st == 'paid')
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'Files (payslip, bank, ECR)', icon: Icons.folder_zip_rounded, onTap: _busy ? null : () => _act('files')),
            GlassButton(label: 'Payslip messages', icon: Icons.chat_rounded, onTap: _busy ? null : () => _act('drafts')),
          ]),
        if (st == 'approved')
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GradientButton(label: 'Maine salary de di', icon: Icons.verified_rounded, onTap: _busy ? null : () => _act('paid')),
          ),
        if (widget.compact)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PayRunPage(app: app, id: widget.id))),
                child: const Text('Har ek ki salary dekho')),
          ),
        const Text('Payment aap apne bank se karengi (bank file upload). Hoola paise nahi bhejta, bank mein login nahi karta.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

class _RulesTab extends StatefulWidget {
  const _RulesTab({required this.app});
  final Santosh app;
  @override
  State<_RulesTab> createState() => _RulesTabState();
}

class _RulesTabState extends State<_RulesTab> {
  Map<String, dynamic>? _s0;
  final _company = TextEditingController(), _state = TextEditingController(), _min = TextEditingController(),
      _pfc = TextEditingController(), _esic = TextEditingController(), _tan = TextEditingController();
  bool _pf = false, _esi = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await widget.app.api!.paySettings();
      if (!mounted) return;
      setState(() {
        _s0 = s;
        _company.text = _s(s['company']);
        _state.text = _s(s['state_name']);
        _min.text = (s['min_wage'] ?? 0) == 0 ? '' : '${(s['min_wage'] as num).round()}';
        _pfc.text = _s(s['pf_code']);
        _esic.text = _s(s['esi_code']);
        _tan.text = _s(s['tan']);
        _pf = s['pf_on'] == true;
        _esi = s['esi_on'] == true;
      });
    } catch (_) {}
  }

  Future<void> _save() async {
    try {
      await widget.app.api!.paySaveSettings({
        'company': _company.text.trim(),
        if (_state.text.trim().isNotEmpty) 'state': _state.text.trim(),
        if (_min.text.trim().isNotEmpty) 'min_wage': double.tryParse(_min.text.replaceAll(',', '')),
        'pf_on': _pf,
        'esi_on': _esi,
        'pf_code': _pfc.text.trim(),
        'esi_code': _esic.text.trim(),
        'tan': _tan.text.trim(),
      });
      if (mounted) _snack(context, 'Save');
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => _s0 == null
      ? const Center(child: CircularProgressIndicator())
      : ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
          Glass(
            child: Column(children: [
              TextField(controller: _company, decoration: const InputDecoration(labelText: 'Company / dukaan ka naam')),
              TextField(controller: _state, decoration: const InputDecoration(labelText: 'State (professional tax ke liye)')),
              TextField(
                  controller: _min,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Minimum wage (mahina, state notification)')),
              SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('PF (EPFO) registered'), value: _pf, onChanged: (v) => setState(() => _pf = v)),
              if (_pf) TextField(controller: _pfc, decoration: const InputDecoration(labelText: 'PF establishment code')),
              SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('ESIC registered'), value: _esi, onChanged: (v) => setState(() => _esi = v)),
              if (_esi) TextField(controller: _esic, decoration: const InputDecoration(labelText: 'ESIC employer code')),
              TextField(controller: _tan, textCapitalization: TextCapitalization.characters, decoration: const InputDecoration(labelText: 'TAN (TDS)')),
              const SizedBox(height: 12),
              GradientButton(label: 'Save', icon: Icons.check_rounded, onTap: _save),
            ]),
          ),
          const SizedBox(height: 10),
          const Glass(
              child: Text(
                  'Hoola ke niyam: Code on Wages (pagaar 7 tareekh tak, basic+DA kam se kam aadha, OT dugna), PF ki seema ₹25,000 '
                  '(17 Sep 2026 se), ESIC ₹21,000 tak, state ka PT, TDS Sec 392 (naya Income-tax Act). PAN aur bank number taale mein, '
                  'sirf aakhri 4 ank dikhte hain.',
                  style: TextStyle(color: C.muted, fontSize: 12.5))),
        ]);
}
