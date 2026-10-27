/// Hoola Employee (v0.58): Hoola works in the owner's business.
/// Kaam (pause, waiting asks, today's report) · Bharosa (trust per duty) · Team · Hisaab (audit log) · Naukri (setup + job sheet).
/// Every rule here is enforced on the server; this screen only shows and changes the owner's choices.
library;

import 'package:flutter/material.dart';

import '../api.dart';
import '../state.dart';
import 'employee_inbox.dart';
import 'glass.dart';

const _levelColor = {'seekh': C.warn, 'saathi': C.teal, 'bharosa': C.ok};
const _levelShort = {'seekh': 'Seekh', 'saathi': 'Saathi', 'bharosa': 'Bharosa'};
const _days = ['Som', 'Mangal', 'Budh', 'Guru', 'Shukra', 'Shani', 'Ravi'];

List<Map<String, dynamic>> _list(Object? o) =>
    List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

String _when(String? iso) {
  if (iso == null || iso.isEmpty) return '';
  final t = DateTime.tryParse(iso)?.toLocal();
  if (t == null) return '';
  final n = DateTime.now();
  final hm = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  return (t.year == n.year && t.month == n.month && t.day == n.day) ? hm : '${t.day}/${t.month} $hm';
}

class EmployeeScreen extends StatefulWidget {
  const EmployeeScreen({super.key, required this.app, this.initialTab = 0, this.initialRole});
  final Santosh app;
  final int initialTab;      // v0.168 open straight on Team (3) or Naukri (5) from the home section
  final String? initialRole; // v0.168 pre-pick the job on the Naukri tab
  @override
  State<EmployeeScreen> createState() => _EmployeeScreenState();
}

class _EmployeeScreenState extends State<EmployeeScreen> {
  Map<String, dynamic>? _o;
  String? _err;
  bool _busy = false;
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final o = await _api.employee();
      if (mounted) setState(() {
        _o = o;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  void _say(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _run(Future<void> Function() f) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await f();
      await _load();
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Map<String, dynamic>? get _p => _o?['profile'] == null ? null : Map<String, dynamic>.from(_o!['profile'] as Map);

  @override
  Widget build(BuildContext context) {
    final p = _p;
    final ready = p != null && p['enabled'] == true;
    return DefaultTabController(
      length: 6,
      initialIndex: widget.initialTab.clamp(0, 5),
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          title: Text('${widget.app.aName} · Employee'),
          bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
            Tab(text: 'Kaam'),
            Tab(text: 'Inbox'),
            Tab(text: 'Bharosa'),
            Tab(text: 'Team'),
            Tab(text: 'Hisaab'),
            Tab(text: 'Naukri'),
          ]),
        ),
        body: Aurora(
          child: _o == null
              ? Center(
                  child: _err != null
                      ? Padding(padding: const EdgeInsets.all(24), child: Text(_err!, style: const TextStyle(color: C.bad)))
                      : const CircularProgressIndicator())
              : TabBarView(children: [
                  ready ? _work() : _notReady(),
                  ready ? EmployeeInboxTab(app: widget.app) : _notReady(),
                  ready ? _trust() : _notReady(),
                  _team(),
                  _AuditTab(api: _api, onChanged: _load),
                  _SetupTab(api: _api, o: _o!, app: widget.app, onSaved: _load, initialRole: widget.initialRole),
                ]),
        ),
      ),
    );
  }

  Widget _notReady() => ListView(padding: const EdgeInsets.all(16), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${widget.app.aName} ko naukri dijiye', style: display(20)),
            const SizedBox(height: 8),
            Text(
                '${widget.app.aName} aapke business mein front desk ya support + vasooli ka kaam karega. Shuru mein har kaam aapse '
                'poochkar karega (Seekh). Jaise-jaise aap "Haan" dabayengi, aap bharosa badha sakti hain. Paise kabhi apne aap nahi; '
                'ek tap mein sab rok sakti hain.',
                style: const TextStyle(color: C.chip, height: 1.35)),
            const SizedBox(height: 12),
            const Text('"Naukri" tab mein business ka naam aur kaam chuniye.', style: TextStyle(color: C.muted)),
          ]),
        ),
      ]);

  // ------------------------------------------------------------------ Kaam
  Widget _work() {
    final st = Map<String, dynamic>.from(_o!['status'] as Map);
    final paused = st['paused'] == true;
    final asks = _list(_o!['asks']);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 32), children: [
        Glass(
          tint: paused ? C.bad : C.ok,
          opacity: .10,
          child: Row(children: [
            Icon(paused ? Icons.pause_circle_filled_rounded : Icons.work_rounded, color: paused ? C.bad : C.ok, size: 34),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(paused ? 'Kaam ruka hua hai' : '${st['business']} mein kaam chalu',
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                Text(
                    paused
                        ? 'Naukri ka koi kaam nahi hoga. Aapke apne kaam chalte rahenge.'
                        : '${st['role']} · aaj ${st['done_today']} kaam · ${st['pending_asks']} aapki haan ke liye',
                    style: const TextStyle(color: C.muted, fontSize: 12.5)),
              ]),
            ),
          ]),
        ),
        const SizedBox(height: 10),
        GradientButton(
          label: paused ? 'Kaam shuru karo' : 'Sab kaam roko',
          icon: paused ? Icons.play_arrow_rounded : Icons.pause_rounded,
          onTap: _busy ? null : () => _run(() => _api.employeePause(!paused)),
        ),
        const SizedBox(height: 18),
        Text('Aapki haan chahiye · ${asks.length}', style: display(17)),
        const SizedBox(height: 8),
        if (asks.isEmpty)
          const Glass(child: Text('Abhi kuch nahi ruka hai.', style: TextStyle(color: C.muted)))
        else
          for (final a in asks)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: EmployeeAskTile(a: a, onDecide: (yes) => _run(() => _api.employeeDecide(a['id'] as String, yes))),
            ),
        const SizedBox(height: 18),
        _ReportCard(api: _api),
        if ((st['team_tasks_waiting'] as num? ?? 0) > 0) ...[
          const SizedBox(height: 10),
          Glass(child: Text('Team ke ${st['team_tasks_waiting']} kaam line mein hain.', style: const TextStyle(color: C.muted))),
        ],
      ]),
    );
  }

  // ------------------------------------------------------------------ Bharosa
  Widget _trust() {
    final trust = _list(_o!['trust']);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 32), children: [
      const Text(
          'Har kaam ka alag bharosa. Seekh = har baar poochega. Saathi = roz ke kaam khud, bade kaam (sabko bhejna, delete, share, '
          'paise) poochkar. Bharosa = din ki seemaa tak sab khud. Aap kisi kaam ko "Galat tha" bolengi to woh ek level neeche aa jayega.',
          style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
      const SizedBox(height: 12),
      for (final t in trust)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${t['label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
                Pill(_levelShort[t['level']] ?? '${t['level']}', fg: _levelColor[t['level']] ?? C.chip),
              ]),
              const SizedBox(height: 2),
              Text('${t['say']}', style: const TextStyle(color: C.faint, fontSize: 12)),
              const SizedBox(height: 10),
              SegmentedButton<String>(
                showSelectedIcon: false,
                segments: const [
                  ButtonSegment(value: 'seekh', label: Text('Seekh')),
                  ButtonSegment(value: 'saathi', label: Text('Saathi')),
                  ButtonSegment(value: 'bharosa', label: Text('Bharosa')),
                ],
                selected: {t['level'] as String},
                onSelectionChanged: _busy
                    ? null
                    : (v) => _run(() async {
                          await _api.employeeTrust(t['duty'] as String, level: v.first);
                        }),
              ),
              const SizedBox(height: 6),
              Text(
                  '${t['level'] == 'seekh' ? 'Har kaam poochega' : 'Din mein ${t['per_day']} kaam tak'} · '
                  '${t['approved']} baar haan${(t['corrections'] as num? ?? 0) > 0 ? ' · ${t['corrections']} galti' : ''}',
                  style: const TextStyle(color: C.muted, fontSize: 12)),
              if ((t['suggest'] as String? ?? '').isNotEmpty) ...[
                const SizedBox(height: 8),
                Row(children: [
                  const Icon(Icons.trending_up_rounded, color: C.ok, size: 18),
                  const SizedBox(width: 6),
                  Expanded(
                      child: Text('${t['approved']} baar sahi raha. ${_levelShort[t['suggest']]} kar dein?',
                          style: const TextStyle(color: C.ok, fontSize: 12.5))),
                  TextButton(
                      onPressed: _busy ? null : () => _run(() async => _api.employeeTrust(t['duty'] as String, level: t['suggest'] as String)),
                      child: const Text('Haan')),
                ]),
              ],
            ]),
          ),
        ),
    ]);
  }

  // ------------------------------------------------------------------ Team
  Widget _team() {
    final team = _list(_o!['team']);
    final duties = _list(_o!['duties']);
    final mine = List<String>.from((_p?['duties'] as List?) ?? const []);
    String dl(String id) => (duties.firstWhere((d) => d['id'] == id, orElse: () => {'label': id}))['label'] as String;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 32), children: [
      Text(
          'Team ke log apne Hoola se ${widget.app.aName} ko kaam de sakte hain (Hoola Network par judna zaroori). Manager naukri ke '
          'saare kaam de sakta hai, staff sirf jo aap chunein. Bade kaam hamesha aapki haan se.',
          style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
      const SizedBox(height: 12),
      for (final m in team)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Glass(
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                  backgroundColor: m['role'] == 'manager' ? C.accent2 : C.violet,
                  child: Text((m['name'] as String).isEmpty ? '?' : (m['name'] as String)[0].toUpperCase(),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
              title: Text('${m['name']}${m['active'] == true ? '' : ' (band)'}', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(
                  [
                    m['role'] == 'manager' ? 'Manager · saare kaam' : 'Staff · ${List<String>.from(m['duties'] as List).map(dl).join(', ')}',
                    if ((m['address'] as String? ?? '').isNotEmpty) m['address'] as String else 'Hoola ID nahi: kaam nahi bhej sakte',
                  ].join('\n'),
                  style: const TextStyle(fontSize: 12)),
              isThreeLine: true,
              trailing: const Icon(Icons.edit_rounded, size: 18),
              onTap: () => _editMember(m, duties, mine),
            ),
          ),
        ),
      GlassButton(label: 'Team mein jodiye', icon: Icons.person_add_alt_1_rounded, onTap: () => _editMember(null, duties, mine)),
    ]);
  }

  Future<void> _editMember(Map<String, dynamic>? m, List<Map<String, dynamic>> duties, List<String> mine) async {
    final name = TextEditingController(text: m?['name'] as String? ?? '');
    final phone = TextEditingController(text: m?['phone'] as String? ?? '');
    final addr = TextEditingController(text: m?['address'] as String? ?? '');
    String role = m?['role'] as String? ?? 'staff';
    bool active = m?['active'] as bool? ?? true;
    final picked = <String>{...List<String>.from((m?['duties'] as List?) ?? const [])};
    final res = await showDialog<String>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: Text(m == null ? 'Naya team member' : '${m['name']}'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: name, textCapitalization: TextCapitalization.words, decoration: const InputDecoration(labelText: 'Naam')),
              TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone (zaroori nahi)')),
              TextField(controller: addr, decoration: const InputDecoration(labelText: 'Unka Hoola ID (naam@server)')),
              const SizedBox(height: 10),
              SegmentedButton<String>(
                showSelectedIcon: false,
                segments: const [ButtonSegment(value: 'staff', label: Text('Staff')), ButtonSegment(value: 'manager', label: Text('Manager'))],
                selected: {role},
                onSelectionChanged: (v) => set(() => role = v.first),
              ),
              if (role == 'staff') ...[
                const SizedBox(height: 8),
                const Text('Yeh kaam de sakte hain:', style: TextStyle(color: C.muted, fontSize: 12.5)),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  for (final d in duties.where((d) => mine.contains(d['id'])))
                    FilterChip(
                      label: Text('${d['label']}'),
                      selected: picked.contains(d['id']),
                      onSelected: (on) => set(() => on ? picked.add(d['id'] as String) : picked.remove(d['id'])),
                    ),
                ]),
              ],
              if (m != null)
                SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Chalu'), value: active, onChanged: (v) => set(() => active = v)),
            ]),
          ),
          actions: [
            if (m != null) TextButton(onPressed: () => Navigator.pop(ctx, 'delete'), child: const Text('Hatao', style: TextStyle(color: C.bad))),
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(ctx, 'save'), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (res == null) return;
    final body = <String, dynamic>{
      'name': name.text.trim(),
      'phone': phone.text.trim(),
      'address': addr.text.trim(),
      'role': role,
      'duties': picked.toList(),
      if (m != null) 'active': active,
    };
    await _run(() async {
      if (res == 'delete') {
        await _api.employeeRemoveMember(m!['id'] as String);
      } else if (m == null) {
        await _api.employeeAddMember(body);
      } else {
        await _api.employeeEditMember(m['id'] as String, body);
      }
    });
  }
}

/// One action waiting for the owner's tap (used in the Employee screen and as a chat card).
class EmployeeAskTile extends StatelessWidget {
  const EmployeeAskTile({super.key, required this.a, required this.onDecide});
  final Map<String, dynamic> a;
  final void Function(bool yes)? onDecide;
  @override
  Widget build(BuildContext context) {
    final status = a['status'] as String? ?? 'pending';
    final big = a['kind'] == 'big';
    return Glass(
      border: big ? C.warn.withOpacity(.5) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(big ? Icons.warning_amber_rounded : Icons.help_outline_rounded, color: big ? C.warn : C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${a['what']}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Text(_when(a['created_at'] as String?), style: const TextStyle(color: C.faint, fontSize: 11.5)),
        ]),
        const SizedBox(height: 4),
        Text('${a['who']} · ${a['duty_label']} · ${a['why']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        if ((a['detail'] as String? ?? '').isNotEmpty) ...[
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
            child: Text('${a['detail']}', style: const TextStyle(fontSize: 12.5, color: C.chip)),
          ),
        ],
        const SizedBox(height: 10),
        if (status == 'pending' && onDecide != null)
          Row(children: [
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, color: C.bad, onTap: () => onDecide!(false))),
            const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Haan, karo', icon: Icons.check_rounded, height: 48, onTap: () => onDecide!(true))),
          ])
        else
          Pill(
              {
                    'done': 'Ho gaya',
                    'running': 'Ho raha hai…',
                    'failed': 'Nahi ho paya',
                    'declined': 'Mana kiya',
                    'expired': 'Purana ho gaya'
                  }[status] ??
                  status,
              fg: status == 'done' ? C.ok : (status == 'failed' || status == 'declined' ? C.bad : C.chip)),
        if (status == 'failed' && (a['result'] as String? ?? '').isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 6), child: Text('${a['result']}', style: const TextStyle(color: C.bad, fontSize: 12))),
      ]),
    );
  }
}

class _ReportCard extends StatefulWidget {
  const _ReportCard({required this.api});
  final Api api;
  @override
  State<_ReportCard> createState() => _ReportCardState();
}

class _ReportCardState extends State<_ReportCard> {
  Map<String, dynamic>? _r;
  @override
  void initState() {
    super.initState();
    widget.api.employeeReport().then((r) {
      if (mounted) setState(() => _r = r);
    }).catchError((_) {});
  }

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.summarize_rounded, color: C.accent2, size: 20),
            const SizedBox(width: 8),
            Text('Aaj ki report', style: display(16)),
          ]),
          const SizedBox(height: 8),
          Text(_r == null ? '…' : '${_r!['text']}', style: const TextStyle(color: C.chip, height: 1.4)),
        ]),
      );
}

// ------------------------------------------------------------------ Hisaab (audit log)
class _AuditTab extends StatefulWidget {
  const _AuditTab({required this.api, required this.onChanged});
  final Api api;
  final Future<void> Function() onChanged;
  @override
  State<_AuditTab> createState() => _AuditTabState();
}

class _AuditTabState extends State<_AuditTab> {
  List<Map<String, dynamic>>? _rows;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.api.employeeAudit(limit: 200);
      if (mounted) setState(() => _rows = r);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _wrong(Map<String, dynamic> e) async {
    final c = TextEditingController();
    final note = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Kya galat tha?'),
        content: TextField(
            controller: c,
            maxLines: 3,
            decoration: const InputDecoration(hintText: 'Jaise: patient ko subah 8 se pehle message nahi (yeh niyam ban jayega)')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Galat tha')),
        ],
      ),
    );
    if (note == null) return;
    try {
      final r = await widget.api.employeeWrong(e['id'] as String, note);
      final t = r['trust'] as Map?;
      if (mounted && t != null) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('${t['label']}: ab ${_levelShort[t['level']] ?? t['level']}. Seekh liya.')));
      }
    } catch (err) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$err')));
    }
    await _load();
    await widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;
    if (rows == null) {
      return Center(child: _err != null ? Text(_err!, style: const TextStyle(color: C.bad)) : const CircularProgressIndicator());
    }
    const icon = {
      'done': (Icons.check_circle_rounded, C.ok),
      'asked': (Icons.help_rounded, C.accent),
      'refused': (Icons.block_rounded, C.bad),
      'error': (Icons.error_outline_rounded, C.bad),
      'paused': (Icons.pause_circle_rounded, C.warn),
    };
    return RefreshIndicator(
      onRefresh: _load,
      child: rows.isEmpty
          ? ListView(children: const [Padding(padding: EdgeInsets.all(30), child: Center(child: Text('Abhi koi hisaab nahi.', style: TextStyle(color: C.muted))))])
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 32),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const Divider(height: 1, color: C.line),
              itemBuilder: (_, i) {
                final e = rows[i];
                final ic = icon[e['outcome']] ?? (Icons.info_outline_rounded, C.chip);
                final canWrong = e['outcome'] == 'done' && e['kind'] != 'read' && e['kind'] != 'meta' && e['wrong'] != true;
                return ListTile(
                  dense: true,
                  leading: Icon(ic.$1, color: ic.$2, size: 22),
                  title: Text('${e['what']}', style: TextStyle(fontWeight: FontWeight.w700,
                      decoration: e['wrong'] == true ? TextDecoration.lineThrough : null)),
                  subtitle: Text(
                      [
                        '${_when(e['at'] as String?)} · ${e['who']}${(e['approved_by'] as String? ?? '').isNotEmpty ? ' · aapki haan se' : ''}',
                        if ((e['detail'] as String? ?? '').isNotEmpty) '${e['detail']}',
                        if (e['wrong'] == true) 'Galat bataya${(e['wrong_note'] as String? ?? '').isNotEmpty ? ': ${e['wrong_note']}' : ''}',
                      ].join('\n'),
                      maxLines: 4,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12)),
                  trailing: canWrong ? TextButton(onPressed: () => _wrong(e), child: const Text('Galat tha')) : null,
                );
              },
            ),
    );
  }
}

// ------------------------------------------------------------------ Naukri (setup + job sheet)
class _SetupTab extends StatefulWidget {
  const _SetupTab({required this.api, required this.o, required this.app, required this.onSaved, this.initialRole});
  final Api api;
  final Map<String, dynamic> o;
  final Santosh app;
  final Future<void> Function() onSaved;
  final String? initialRole;   // v0.168 job picked on home pre-fills the role here
  @override
  State<_SetupTab> createState() => _SetupTabState();
}

class _SetupTabState extends State<_SetupTab> {
  late final Map<String, dynamic> _p = Map<String, dynamic>.from((widget.o['profile'] as Map?) ?? const {});
  late final _name = TextEditingController(text: _p['business_name'] as String? ?? '');
  late final _kind = TextEditingController(text: _p['business_kind'] as String? ?? '');
  late final _about = TextEditingController(text: _p['about'] as String? ?? '');
  late final _rules = TextEditingController(text: _p['rules'] as String? ?? '');
  late String _role = _p['role'] as String? ?? widget.initialRole ?? 'front_desk';
  late final Set<String> _custom = {...List<String>.from((_p['custom_duties'] as List?) ?? const [])};
  late final Map<String, dynamic> _hours = Map<String, dynamic>.from((_p['hours'] as Map?) ?? const {});
  late String _open = _hours['open'] as String? ?? '10:00';
  late String _close = _hours['close'] as String? ?? '20:00';
  late final Set<int> _dayset = {...List<int>.from(((_hours['days'] as List?) ?? const [0, 1, 2, 3, 4, 5]).map((e) => (e as num).toInt()))};
  late String _after = _p['after_hours'] as String? ?? 'note';
  late String _report = _p['report_time'] as String? ?? '20:30';
  late bool _replyStaff = _p['reply_to_staff'] as bool? ?? true;
  late String _preset = _p['preset'] as String? ?? '';
  late String _presetWas = _p['preset'] as String? ?? '';
  late final _upi = TextEditingController(text: _p['upi_id'] as String? ?? '');
  late final _upiName = TextEditingController(text: _p['upi_name'] as String? ?? '');
  late int _slot = (_p['slot_minutes'] as num? ?? 30).toInt();
  late bool _inboxOn = _p['inbox_on'] as bool? ?? false;
  bool _busy = false;
  String? _sheet;
  bool _sheetEdited = false;

  @override
  void initState() {
    super.initState();
    if (widget.o['profile'] != null) _loadSheet();
  }

  Future<void> _loadSheet() async {
    try {
      final s = await widget.api.employeeJobSheet();
      if (mounted) setState(() {
        _sheet = s['text'] as String?;
        _sheetEdited = s['edited'] == true;
      });
    } catch (_) {}
  }

  Future<String?> _pickTime(String now) async {
    final parts = now.split(':');
    final t = await showTimePicker(
        context: context, initialTime: TimeOfDay(hour: int.tryParse(parts[0]) ?? 10, minute: int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0));
    if (t == null) return null;
    return '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  Future<void> _save({bool? enable}) async {
    setState(() => _busy = true);
    try {
      final presetNew = _preset.isNotEmpty && _preset != _presetWas;
      final saved = await widget.api.employeeSave({
        'role': _role,
        if (_role == 'custom') 'duties': _custom.toList(),
        'business_name': _name.text.trim(),
        if (!presetNew || _kind.text.trim().isNotEmpty) 'business_kind': _kind.text.trim(),
        'about': _about.text.trim(),
        if (!presetNew) 'rules': _rules.text.trim(),
        'hours': {'open': _open, 'close': _close, 'days': (_dayset.toList()..sort())},
        if (!presetNew) 'after_hours': _after,
        'report_time': _report,
        'reply_to_staff': _replyStaff,
        if (presetNew) 'preset': _preset,
        'upi_id': _upi.text.trim(),
        'upi_name': _upiName.text.trim(),
        if (!presetNew) 'slot_minutes': _slot,
        'inbox_on': _inboxOn,
        if (enable != null) 'enabled': enable,
      });
      if (enable != null) _p['enabled'] = enable;
      _p.addAll(saved);
      _presetWas = _preset;
      _rules.text = saved['rules'] as String? ?? _rules.text;
      _role = saved['role'] as String? ?? _role;
      _after = saved['after_hours'] as String? ?? _after;
      _slot = (saved['slot_minutes'] as num? ?? _slot).toInt();
      if (_kind.text.isEmpty) _kind.text = saved['business_kind'] as String? ?? '';
      await widget.onSaved();
      await _loadSheet();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Save ho gaya')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _editSheet() async {
    final c = TextEditingController(text: _sheet ?? '');
    final r = await Navigator.of(context).push<String>(MaterialPageRoute(
      builder: (ctx) => Scaffold(
        appBar: AppBar(title: const Text('Job sheet'), actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, ''), child: const Text('Apne aap wali')),
          TextButton(onPressed: () => Navigator.pop(ctx, c.text), child: const Text('Save')),
        ]),
        body: Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(controller: c, maxLines: null, expands: true, style: const TextStyle(fontSize: 14, height: 1.4)),
        ),
      ),
    ));
    if (r == null) return;
    try {
      final s = await widget.api.employeeSetJobSheet(r);
      if (mounted) setState(() {
        _sheet = s['text'] as String?;
        _sheetEdited = s['edited'] == true;
      });
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final roles = _list(widget.o['roles']);
    final duties = _list(widget.o['duties']);
    final enabled = _p['enabled'] == true;
    final presets = _list(widget.o['presets']);
    final hint = presets.firstWhere((x) => x['id'] == _preset, orElse: () => const <String, dynamic>{})['about_hint'] as String?;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Business ka prakaar', style: display(17)),
          const Text('Ek tap mein kaam, samay aur shuruaati niyam bhar jayenge. Baad mein sab badal sakti hain.',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          Wrap(spacing: 6, runSpacing: 4, children: [
            for (final pr in presets)
              ChoiceChip(
                label: Text('${pr['label']}'),
                selected: _preset == pr['id'],
                showCheckmark: false,
                selectedColor: C.accent,
                labelStyle: TextStyle(color: _preset == pr['id'] ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                onSelected: (_) => setState(() {
                  _preset = pr['id'] as String;
                  _role = pr['role'] as String;
                }),
              ),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Business', style: display(17)),
          TextField(controller: _name, textCapitalization: TextCapitalization.words, decoration: const InputDecoration(labelText: 'Business ka naam')),
          TextField(controller: _kind, decoration: const InputDecoration(labelText: 'Kya business hai (clinic, dukaan, ISP…)')),
          TextField(
              controller: _about,
              maxLines: 4,
              minLines: 2,
              decoration: InputDecoration(labelText: 'Graahakon ko kya batana hai (daam, services, pata…)', helperText: hint, helperMaxLines: 2)),
        ]),
      ),
      const SizedBox(height: 12),
      Text('Kaam', style: display(17)),
      const SizedBox(height: 6),
      for (final r in roles)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => setState(() => _role = r['id'] as String),
            child: Glass(
              border: _role == r['id'] ? C.accent : null,
              child: Row(children: [
                Icon(_role == r['id'] ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                    color: _role == r['id'] ? C.accent : C.faint),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${r['label']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text('${r['say']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  ]),
                ),
              ]),
            ),
          ),
        ),
      if (_role == 'custom')
        Wrap(spacing: 6, runSpacing: 4, children: [
          for (final d in duties)
            FilterChip(
              label: Text('${d['label']}'),
              selected: _custom.contains(d['id']),
              onSelected: (on) => setState(() => on ? _custom.add(d['id'] as String) : _custom.remove(d['id'])),
            ),
        ]),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Samay', style: display(17)),
          Row(children: [
            Expanded(
                child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Khulta hai'),
                    subtitle: Text(_open),
                    onTap: () async {
                      final t = await _pickTime(_open);
                      if (t != null) setState(() => _open = t);
                    })),
            Expanded(
                child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Band hota hai'),
                    subtitle: Text(_close),
                    onTap: () async {
                      final t = await _pickTime(_close);
                      if (t != null) setState(() => _close = t);
                    })),
          ]),
          Wrap(spacing: 4, children: [
            for (var i = 0; i < 7; i++)
              FilterChip(
                  label: Text(_days[i]),
                  selected: _dayset.contains(i),
                  onSelected: (on) => setState(() => on ? _dayset.add(i) : _dayset.remove(i))),
          ]),
          const SizedBox(height: 8),
          const Text('Band samay mein:', style: TextStyle(color: C.muted, fontSize: 12.5)),
          DropdownButton<String>(
            value: _after,
            isExpanded: true,
            dropdownColor: C.bgBottom,
            items: const [
              DropdownMenuItem(value: 'note', child: Text('Sandesh likh le, subah bataye')),
              DropdownMenuItem(value: 'answer', child: Text('Aam sawaalon ka jawab de')),
              DropdownMenuItem(value: 'quiet', child: Text('Kuch na kare')),
            ],
            onChanged: (v) => setState(() => _after = v ?? 'note'),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Roz ki report'),
            subtitle: Text('$_report baje'),
            trailing: const Icon(Icons.schedule_rounded),
            onTap: () async {
              final t = await _pickTime(_report);
              if (t != null) setState(() => _report = t);
            },
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Team ko kaam ka jawab bheje'),
            subtitle: const Text('Phone number, email jaisi cheezein hata kar', style: TextStyle(fontSize: 12)),
            value: _replyStaff,
            onChanged: (v) => setState(() => _replyStaff = v),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('WhatsApp par graahak', style: display(17)),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('${widget.app.aName} graahakon ko jawab de'),
            subtitle: const Text('Business number par aaye message: sawaal, appointment, shikayat, baaki paisa. Bharosa ke hisaab se.',
                style: TextStyle(fontSize: 12)),
            value: _inboxOn,
            onChanged: (v) => setState(() => _inboxOn = v),
          ),
          Row(children: [
            const Text('Ek appointment: ', style: TextStyle(color: C.muted)),
            DropdownButton<int>(
              value: const [10, 15, 20, 30, 45, 60, 90, 120].contains(_slot) ? _slot : 30,
              dropdownColor: C.bgBottom,
              items: [for (final m in const [10, 15, 20, 30, 45, 60, 90, 120]) DropdownMenuItem(value: m, child: Text('$m min'))],
              onChanged: (v) => setState(() => _slot = v ?? 30),
            ),
          ]),
          TextField(controller: _upi, decoration: const InputDecoration(labelText: 'Paisa lene ka UPI ID (naam@bank)')),
          TextField(controller: _upiName, decoration: const InputDecoration(labelText: 'UPI par naam')),
          const SizedBox(height: 4),
          const Text('Graahak apne UPI app se khud bharta hai. Hoola kabhi paisa nahi bhejta ya leta.',
              style: TextStyle(color: C.faint, fontSize: 11.5)),
        ]),
      ),
      const SizedBox(height: 12),
      BizChannelCard(api: widget.api),
      const SizedBox(height: 12),
      Glass(
        child: TextField(
            controller: _rules,
            maxLines: 5,
            minLines: 2,
            decoration: const InputDecoration(labelText: 'Aapke niyam (har line ek niyam)', hintText: '- 500 se zyada ki chhoot kabhi nahi')),
      ),
      const SizedBox(height: 14),
      GradientButton(
        label: enabled ? 'Save karo' : 'Save karke naukri shuru karo',
        icon: Icons.check_rounded,
        onTap: _busy ? null : () => _save(enable: enabled ? null : true),
      ),
      if (enabled) ...[
        const SizedBox(height: 10),
        GlassButton(label: 'Employee mode band karo', icon: Icons.power_settings_new_rounded, color: C.bad,
            onTap: _busy ? null : () => _save(enable: false)),
      ],
      if (_sheet != null) ...[
        const SizedBox(height: 18),
        Row(children: [
          Expanded(child: Text('Job sheet${_sheetEdited ? ' (aapki likhi)' : ''}', style: display(17))),
          TextButton.icon(onPressed: _editSheet, icon: const Icon(Icons.edit_rounded, size: 16), label: const Text('Badlo')),
        ]),
        Glass(child: SelectableText(_sheet!, style: const TextStyle(color: C.chip, fontSize: 13, height: 1.4))),
      ],
    ]);
  }
}

/// Chat card: something Hoola wanted to do on its own and needs the owner's Haan.
class EmployeeAskCard extends StatefulWidget {
  const EmployeeAskCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<EmployeeAskCard> createState() => _EmployeeAskCardState();
}

class _EmployeeAskCardState extends State<EmployeeAskCard> {
  bool _busy = false;
  @override
  Widget build(BuildContext context) => EmployeeAskTile(
        a: widget.v,
        onDecide: _busy || widget.app.api == null
            ? null
            : (yes) async {
                setState(() => _busy = true);
                try {
                  final r = await widget.app.api!.employeeDecide(widget.v['id'] as String, yes);
                  widget.v.addAll(r);
                } catch (e) {
                  if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                }
                if (mounted) setState(() => _busy = false);
              },
      );
}

/// Chat card: the day's work report.
class EmployeeReportCard extends StatelessWidget {
  const EmployeeReportCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.summarize_rounded, color: C.accent2, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('${app.aName} ki report', style: display(16))),
          ]),
          const SizedBox(height: 8),
          Text('${v['text'] ?? ''}', style: const TextStyle(color: C.chip, height: 1.4)),
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmployeeScreen(app: app))),
              child: const Text('Poora hisaab'),
            ),
          ),
        ]),
      );
}
