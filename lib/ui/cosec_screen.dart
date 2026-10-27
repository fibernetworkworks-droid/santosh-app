/// Profile > Company secretary (Cosec Sahayak).
/// Aaj (overdue / 30 din / her taps / notices / minutes) · Companies (master, directors by DIN only, members, charges, calendar,
/// events, meetings, registers) · Filings (MCA forms with due dates, card -> her tap, fingerprint once a phone key is set up)
/// · Niyam (her firm, membership no., reminder days). Notices, minutes and "file karo" happen ONLY on her tap here. Hoola never
/// logs in to MCA, never uses a DSC, never pays: draft / jaankari, CS / vakil se pakka.
library;

import 'package:flutter/material.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
List<String> _lines(String? v) => (v ?? '').split(RegExp(r'[\n,]')).map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _stColor(String st) => switch (st) {
      'waiting' || 'notice_waiting' || 'minutes_waiting' => C.accent,
      'filed' || 'approved' || 'minuted' || 'notice_sent' || 'passed' => C.ok,
      'failed' || 'stale' => C.bad,
      'todo' || 'draft' || 'held' => C.warn,
      _ => C.chip,
    };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}, Set<String> multi = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: multi.contains(k) ? 4 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = await app.api!.call(method, path, body: body);
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Future<void> _showDrafts(BuildContext context, Map<String, dynamic> r) async {
  final drafts = _list(r['drafts']);
  if (drafts.isEmpty) return;
  await showModalBottomSheet(
    context: context,
    backgroundColor: C.bgBottom,
    isScrollControlled: true,
    builder: (_) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Caption('NOTICE BHEJIYE (AAP KHUD)'),
          Flexible(
            child: ListView(shrinkWrap: true, children: [
              for (final d in drafts)
                ListTile(
                  dense: true,
                  title: Text('${_s(d['name'])} · ${_s(d['role'])}'),
                  trailing: Wrap(spacing: 4, children: [
                    if (_s(d['email']).isNotEmpty)
                      IconButton(icon: const Icon(Icons.email_rounded), onPressed: () => Native.openExternal(url: _s(d['email']))),
                    if (_s(d['whatsapp']).isNotEmpty)
                      IconButton(icon: const Icon(Icons.chat_rounded), onPressed: () => Native.openExternal(url: _s(d['whatsapp']))),
                  ]),
                ),
            ]),
          ),
          const Text('Hoola khud nahi bhejta. Kis tareekh ko bheja, record ke liye sambhal ke rakhiye.', style: TextStyle(fontSize: 11, color: C.faint)),
        ]),
      ),
    ),
  );
}

class CosecScreen extends StatefulWidget {
  const CosecScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CosecScreen> createState() => _CosecScreenState();
}

class _CosecScreenState extends State<CosecScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/cosec'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  void _open(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => CosecEntityPage(app: widget.app, entityRef: ref)))
      .then((_) => _load());

  Future<void> _newEntity() async {
    final f = await _form(context, 'Nayi company / LLP', const [
      ('name', 'Naam'),
      ('kind', 'Kism: private / opc / public / listed / section8 / llp'),
      ('cin', 'CIN (company)'),
      ('llpin', 'LLPIN (LLP)'),
      ('incorporated_on', 'Incorporation ki tareekh (YYYY-MM-DD)'),
      ('paid_up', 'Paid-up capital (jaise 25 lakh)'),
      ('turnover', 'Pichhle saal ka turnover (jaise 3 crore)'),
      ('registered_office', 'Registered office'),
      ('auditor_name', 'Auditor (firm)'),
      ('auditor_frn', 'Auditor FRN'),
      ('auditor_term_to_agm', 'Auditor term kis FY ke AGM tak (jaise 2029-30)'),
      ('last_agm', 'Pichhla AGM (YYYY-MM-DD)'),
    ], ok: 'Banao');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/cosec/entities', f);
    if (r != null && _s(r['id']).isNotEmpty && mounted) _open(_s(r['id']));
  }

  Widget _today() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      GradientButton(label: 'Nayi company / LLP', icon: Icons.domain_add_rounded, height: 46, onTap: _busy ? null : _newEntity),
      const SizedBox(height: 12),
      for (final (key, title) in const [
        ('overdue', 'DER HO GAYI'),
        ('waiting', 'AAPKI HAAN BAAKI'),
        ('soon', '30 DIN MEIN'),
        ('meetings', 'NOTICE BHEJNA'),
        ('minutes', 'MINUTES SIGN'),
        ('board', 'BOARD MEETING'),
      ])
        if (_strs(day[key]).isNotEmpty) ...[
          Caption(title),
          for (final t in _strs(day[key])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
          const SizedBox(height: 8),
        ],
      Text(_s(_d?['draft_line']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  Widget _entitiesTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Nayi company / LLP', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newEntity),
        const SizedBox(height: 12),
        for (final e in _list(_d?['entities']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _open(_s(e['id'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    const Icon(Icons.apartment_rounded, color: C.accent, size: 20),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${_s(e['number'])} · ${_s(e['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                    Pill(_s(e['status']), fg: _s(e['status']) == 'active' ? C.ok : C.warn),
                  ]),
                  Text(
                      [
                        _s(e['kind_label']),
                        if (e['small'] == true) 'small company',
                        _s(e['cin']).isNotEmpty ? _s(e['cin']) : _s(e['llpin']),
                        '${_s(e['directors'])} director / partner',
                      ].where((x) => x.isNotEmpty).join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
            ),
          ),
        if (_list(_d?['entities']).isEmpty) const Text('Abhi koi company nahi.', style: TextStyle(color: C.muted)),
      ]);

  Widget _filingsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        const Caption('AGLE 60 DIN + DER WALE'),
        for (final f in _list(_d?['filings']))
          Padding(padding: const EdgeInsets.only(bottom: 8), child: CosecFilingCard(app: widget.app, data: {'filing': f}, onDone: _load)),
        if (_list(_d?['filings']).isEmpty) const Text('Agle 60 din mein koi filing nahi.', style: TextStyle(color: C.muted)),
      ]);

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    const keys = ['firm', 'cs_name', 'membership_no', 'email', 'phone', 'windows', 'morning_time', 'rules'];
    final f = await _form(context, 'Niyam', const [
      ('firm', 'Aapki firm / company'),
      ('cs_name', 'CS ka naam'),
      ('membership_no', 'Membership no. (ACS / FCS)'),
      ('email', 'Email'),
      ('phone', 'Mobile'),
      ('windows', 'Yaad dilane ke din (jaise 30,15,7,1,0)'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('rules', 'Aapke niyam'),
    ], ok: 'Save', initial: {for (final k in keys) k: _s(st[k])}, multi: const {'rules'});
    if (f == null) return;
    await _run('PUT', '/api/cosec/settings', f);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['firm']).isEmpty ? 'Firm ka naam daaliye' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('${_s(st['cs_name'])} ${_s(st['membership_no'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text('Yaad dilana: ${_s(st['windows'])} din pehle · subah ${_s(st['morning_time'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('HOOLA KABHI NAHI'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Aaj', 'Companies', 'Filings', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Company secretary'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: Column(children: [
        SizedBox(
          height: 44,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ),
          ]),
        ),
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        Expanded(
          child: _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: switch (_tab) { 0 => _today(), 1 => _entitiesTab(), 2 => _filingsTab(), _ => _rulesTab() },
                ),
        ),
      ]),
    );
  }
}

/// One company / LLP: master, people, calendar, events, meetings, registers.
class CosecEntityPage extends StatefulWidget {
  const CosecEntityPage({super.key, required this.app, required this.entityRef});
  final Santosh app;
  final String entityRef;
  @override
  State<CosecEntityPage> createState() => _CosecEntityPageState();
}

class _CosecEntityPageState extends State<CosecEntityPage> {
  Map<String, dynamic>? _e;
  int _tab = 0;
  bool _busy = false;

  String get _ref => _s(_e?['id']).isEmpty ? widget.entityRef : _s(_e?['id']);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/cosec/entities/${Uri.encodeComponent(widget.entityRef)}'));
      if (mounted) setState(() => _e = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Future<void> _editMaster() async {
    final e = _m(_e);
    final aud = _m(e['auditor']);
    final f = await _form(context, 'Company ki jaankari', const [
      ('name', 'Naam'),
      ('cin', 'CIN'),
      ('llpin', 'LLPIN'),
      ('roc', 'ROC'),
      ('incorporated_on', 'Incorporation (YYYY-MM-DD)'),
      ('paid_up', 'Paid-up capital'),
      ('turnover', 'Turnover'),
      ('registered_office', 'Registered office'),
      ('email', 'Company email'),
      ('auditor_name', 'Auditor'),
      ('auditor_frn', 'Auditor FRN'),
      ('auditor_term_to_agm', 'Auditor term (FY, jaise 2029-30)'),
      ('last_agm', 'Pichhla AGM'),
    ], ok: 'Save', initial: {
      for (final k in ['name', 'cin', 'llpin', 'roc', 'incorporated_on', 'registered_office', 'email', 'last_agm']) k: _s(e[k]),
      'paid_up': _s(e['paid_up']),
      'turnover': _s(e['turnover']),
      'auditor_name': _s(aud['name']),
      'auditor_frn': _s(aud['frn']),
      'auditor_term_to_agm': _s(aud['term_to_agm']),
    });
    if (f == null) return;
    await _run('PATCH', '/api/cosec/entities/$_ref', f);
  }

  Future<void> _flag(String key, bool v) => _run('PATCH', '/api/cosec/entities/$_ref', {key: v});

  Future<void> _addPerson(String role) async {
    final f = await _form(context, switch (role) { 'member' => 'Member', 'kmp' => 'KMP', 'partner' => 'Designated partner', _ => 'Director' }, [
      ('name', 'Naam'),
      if (role != 'member') ('din', role == 'partner' ? 'DPIN / DIN (8 ank)' : 'DIN (8 ank)'),
      ('designation', 'Padh (designation)'),
      ('appointed_on', 'Kab se (YYYY-MM-DD)'),
      if (role == 'director') ('kyc_on', 'Pichhli DIR-3 KYC kab (YYYY-MM-DD)'),
      if (role == 'member') ('shares', 'Shares'),
      ('email', 'Email'),
      ('phone', 'Mobile'),
    ], ok: 'Save');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('POST', '/api/cosec/entities/$_ref/people', {...f, 'role': role});
  }

  Future<void> _event() async {
    final f = await _form(context, 'Kya badla? (apne shabdon mein)', const [
      ('words', 'Jaise: naya director, istifa, shares allot, office shift, bank loan'),
      ('on', 'Kab (YYYY-MM-DD)'),
      ('name', 'Kaun (naam)'),
      ('din', 'DIN (director ho to)'),
      ('shares', 'Shares (allotment / transfer)'),
      ('to', 'Kisko (transfer)'),
      ('address', 'Naya pata (office shift)'),
      ('holder', 'Bank / charge holder'),
      ('amount', 'Rakam (charge)'),
    ], ok: 'Note karo');
    if (f == null || (f['words'] ?? '').isEmpty) return;
    final det = <String, dynamic>{
      for (final k in ['name', 'din', 'address', 'holder', 'amount', 'to']) if (f[k] != null) k: f[k],
    };
    if (f['shares'] != null) {
      if (f['to'] != null) {
        det['shares'] = f['shares'];
        det['from'] = f['name'];
      } else if (f['name'] != null) {
        det['allottees'] = [
          {'name': f['name'], 'shares': f['shares']}
        ];
      }
    }
    await _run('POST', '/api/cosec/entities/$_ref/events', {'words': f['words'], 'on': f['on'] ?? '', 'details': det});
  }

  Future<void> _newMeeting() async {
    final f = await _form(context, 'Nayi meeting', const [
      ('kind', 'Kaunsi: board / agm / egm / committee'),
      ('on', 'Tareekh (YYYY-MM-DD)'),
      ('time', 'Samay (jaise 11:00)'),
      ('place', 'Jagah'),
      ('mode', 'physical / vc / hybrid'),
      ('fy', 'AGM: kis FY ke accounts (jaise 2025-26)'),
      ('agenda', 'Agenda (har line ek item; khaali = starter)'),
    ], ok: 'Banao', multi: const {'agenda'});
    if (f == null || (f['on'] ?? '').isEmpty) return;
    await _run('POST', '/api/cosec/entities/$_ref/meetings', {...f, 'agenda': _lines(f['agenda'])});
  }

  Widget _master() {
    final e = _m(_e);
    final aud = _m(e['auditor']);
    final fl = _m(e['flags']);
    final sc = _m(e['small_check']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_s(e['number'])} · ${_s(e['name'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          Text('${_s(e['kind_label'])}${e['small'] == true ? ' · small company' : ''}', style: const TextStyle(color: C.muted)),
          Text(_s(e['cin']).isNotEmpty ? 'CIN ${_s(e['cin'])}' : 'LLPIN ${_s(e['llpin'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(e['registered_office']).isNotEmpty) Text(_s(e['registered_office']), style: const TextStyle(fontSize: 12.5)),
          Text('Auditor: ${_s(aud['name']).isEmpty ? '—' : _s(aud['name'])}${_s(aud['term_to_agm']).isNotEmpty ? ' (term ${_s(aud['term_to_agm'])} AGM tak)' : ''}',
              style: const TextStyle(fontSize: 12.5)),
          Text('Pichhla AGM: ${_s(e['last_agm']).isEmpty ? '—' : _s(e['last_agm'])}', style: const TextStyle(fontSize: 12.5)),
          if (_s(sc['why']).isNotEmpty) Text(_s(sc['why']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _editMaster),
        ]),
      ),
      const SizedBox(height: 8),
      SwitchListTile(
          value: fl['deposits'] != false,
          onChanged: _busy ? null : (v) => _flag('deposits', v),
          title: const Text('Loans / deposits hain (DPT-3)')),
      SwitchListTile(
          value: fl['msme_dues'] == true,
          onChanged: _busy ? null : (v) => _flag('msme_dues', v),
          title: const Text('MSME supplier ka 45 din se zyada baaki (MSME-1)')),
      SwitchListTile(value: fl['dormant'] == true, onChanged: _busy ? null : (v) => _flag('dormant', v), title: const Text('Dormant company')),
      SwitchListTile(value: fl['startup'] == true, onChanged: _busy ? null : (v) => _flag('startup', v), title: const Text('Registered startup')),
      if (_strs(e['board_issues']).isNotEmpty) ...[
        const Caption('BOARD MEETING KI GINTI'),
        for (final t in _strs(e['board_issues'])) Text('• $t', style: const TextStyle(fontSize: 13, color: C.warn)),
      ],
      if (_s(e['next_board_by']).isNotEmpty) Text('Agli Board meeting ${_s(e['next_board_by'])} se pehle (120 din).', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 10),
      GlassButton(
          label: 'Registers Excel', icon: Icons.table_chart_rounded, height: 42, onTap: _busy ? null : () => _run('GET', '/api/cosec/entities/$_ref/registers')),
      const SizedBox(height: 6),
      Text(_s(e['draft_line']), style: const TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _people() {
    final e = _m(_e);
    final llp = _s(e['kind']) == 'llp';
    Widget row(Map<String, dynamic> p) => ListTile(
          dense: true,
          leading: Icon(p['active'] == true ? Icons.person_rounded : Icons.person_off_rounded, color: p['active'] == true ? C.accent : C.faint),
          title: Text('${_s(p['name'])}${_s(p['din']).isNotEmpty ? ' · DIN ${_s(p['din'])}' : ''}'),
          subtitle: Text([
            _s(p['designation']),
            if (_s(p['appointed_on']).isNotEmpty) 'se ${_s(p['appointed_on'])}',
            if (_s(p['ceased_on']).isNotEmpty) 'tak ${_s(p['ceased_on'])}',
            if (_s(p['role']) == 'member') '${_s(p['folio'])} · ${_s(p['shares'])} ${_s(p['share_class'])}',
          ].where((x) => x.isNotEmpty).join(' · ')),
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: llp ? 'Partner jodo' : 'Director jodo', icon: Icons.person_add_rounded, height: 40,
            onTap: _busy ? null : () => _addPerson(llp ? 'partner' : 'director')),
        if (!llp) GlassButton(label: 'KMP', icon: Icons.badge_rounded, height: 40, onTap: _busy ? null : () => _addPerson('kmp')),
        if (!llp) GlassButton(label: 'Member', icon: Icons.group_add_rounded, height: 40, onTap: _busy ? null : () => _addPerson('member')),
      ]),
      const SizedBox(height: 12),
      Caption(llp ? 'DESIGNATED PARTNERS' : 'DIRECTORS'),
      for (final p in _list(e['directors'])) row(p),
      if (_list(e['kmp']).isNotEmpty) ...[const Caption('KMP'), for (final p in _list(e['kmp'])) row(p)],
      if (_list(e['members']).isNotEmpty) ...[const Caption('MEMBERS (MGT-1)'), for (final p in _list(e['members'])) row(p)],
      if (_list(e['charges']).isNotEmpty) ...[
        const Caption('CHARGES'),
        for (final c in _list(e['charges']))
          Text('• ${_s(c['holder'])} ${_s(c['amount'])} · ${_s(c['created_on'])}${_s(c['satisfied_on']).isNotEmpty ? ' · chuka ${_s(c['satisfied_on'])}' : ''}',
              style: const TextStyle(fontSize: 13)),
      ],
      const SizedBox(height: 8),
      const Text('Sirf DIN rakha jaata hai. Aadhaar / PAN Pehchaan Locker mein.', style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _filingsTab() {
    final e = _m(_e);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(
            label: 'Is saal ka calendar', icon: Icons.event_note_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '/api/cosec/entities/$_ref/calendar', {})),
        GlassButton(label: 'Kuch badla (event)', icon: Icons.bolt_rounded, height: 40, onTap: _busy ? null : _event),
      ]),
      const SizedBox(height: 12),
      for (final f in _list(e['filings']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: CosecFilingCard(app: widget.app, data: {'filing': f}, onDone: _load)),
    ]);
  }

  Widget _meetingsTab() {
    final e = _m(_e);
    return ListView(padding: const EdgeInsets.all(16), children: [
      if (_s(e['kind']) != 'llp') GradientButton(label: 'Nayi meeting', icon: Icons.groups_rounded, height: 46, onTap: _busy ? null : _newMeeting),
      const SizedBox(height: 12),
      for (final m in _list(e['meetings']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: CosecMeetingCard(app: widget.app, data: {'meeting': m}, onDone: _load)),
      if (_list(e['resolutions']).isNotEmpty) ...[
        const Caption('RESOLUTIONS REGISTER'),
        for (final r in _list(e['resolutions']))
          Text('• ${_s(r['number'])} (${_s(r['kind'])}, ${_s(r['result'])}) ${_s(r['passed_on'])}: ${_s(r['text'])}', style: const TextStyle(fontSize: 12.5)),
      ],
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Jaankari', 'Log', 'Filings', 'Meetings'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(_e?['name']).isEmpty ? 'Company' : _s(_e?['name'])), actions: [
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
      ]),
      body: Column(children: [
        SizedBox(
          height: 44,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ),
          ]),
        ),
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        Expanded(
          child: _e == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: switch (_tab) { 0 => _master(), 1 => _people(), 2 => _filingsTab(), _ => _meetingsTab() },
                ),
        ),
      ]),
    );
  }
}

/// cosec_filing: one MCA form with its due date; "Card banao" -> her tap "Haan, file karo" (fingerprint once a phone key is
/// active) -> MCA V3 steps she does herself -> "Ho gaya" with SRN. Also in calls.
class CosecFilingCard extends StatefulWidget {
  const CosecFilingCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<CosecFilingCard> createState() => _CosecFilingCardState();
}

class _CosecFilingCardState extends State<CosecFilingCard> {
  bool _busy = false;
  late Map<String, dynamic> _f = _m(widget.data['filing']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/cosec/filings/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Filing ki haan' : _s(show['title']), _s(show['subtitle']));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'Fingerprint nahi diya, isliye haan nahi hui.',
        'key_invalidated' => 'Phone mein naya fingerprint juda hai: Profile > Fingerprint se haan mein phone phir se jodiye.',
        _ => 'Fingerprint se haan nahi ho payi (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _go(Future<dynamic> Function() fn) async {
    setState(() => _busy = true);
    try {
      final m = _m(await fn());
      if (mounted) {
        final f = m['filing'] != null ? _m(m['filing']) : m;
        if (_s(f['id']).isNotEmpty) setState(() => _f = f);
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<dynamic> _decide(bool yes) async {
    final id = _s(_f['id']);
    final body = {'yes': yes, 'hash': _s(_f['hash'])};
    try {
      return await widget.app.api!.call('POST', '/api/cosec/filings/$id/decide', body: body);
    } on ApiException catch (e) {
      if (!yes || e.status != 428) rethrow;
      final proof = await _proof(id);
      return await widget.app.api!.call('POST', '/api/cosec/filings/$id/decide', body: {...body, 'proof': proof});
    }
  }

  Future<void> _done() async {
    final f = await _form(context, '${_s(_f['form'])} file ho gaya', const [('srn', 'SRN'), ('filed_on', 'Kab (YYYY-MM-DD)'), ('fee', 'Fee bhari (Rs)')]);
    if (f == null) return;
    await _go(() => widget.app.api!.call('POST', '/api/cosec/filings/${_s(_f['id'])}/done',
        body: {'srn': f['srn'] ?? '', 'filed_on': f['filed_on'] ?? '', 'fee': num.tryParse(f['fee'] ?? '')}));
  }

  Future<void> _skip() async {
    final f = await _form(context, 'Zaroori kyun nahi?', const [('reason', 'Wajah (record ke liye)')]);
    if (f == null || (f['reason'] ?? '').isEmpty) return;
    await _go(() => widget.app.api!.call('POST', '/api/cosec/filings/${_s(_f['id'])}/skip', body: {'reason': f['reason']}));
  }

  @override
  Widget build(BuildContext context) {
    final f = _f;
    final st = _s(f['status']);
    final card = _m(f['card']);
    final fee = _m(f['fee']);
    final left = f['days_left'];
    final isMeeting = f['is_meeting'] == true;
    return Glass(
      border: st == 'waiting' ? C.accent : (f['late'] == true ? C.bad : null),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.assignment_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(f['form'])} · ${_s(f['period'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st == 'waiting' ? 'aapki haan?' : st, fg: _stColor(st)),
        ]),
        if (_s(f['entity']).isNotEmpty) Text(_s(f['entity']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        Text(_s(f['label']), style: const TextStyle(fontSize: 12.5)),
        Text(
            'Aakhri tareekh ${_s(f['due']).isEmpty ? '—' : _s(f['due'])}${f['est'] == true ? ' (andaaza)' : ''}'
            '${left is num && st != 'filed' && st != 'not_needed' ? (left < 0 ? ' · ${-left} din der' : ' · $left din') : ''}',
            style: TextStyle(fontSize: 12.5, color: f['late'] == true ? C.bad : C.muted)),
        Text(_s(f['basis']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
        if (fee.isNotEmpty) Text(_s(fee['text']), style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(f['note']).isNotEmpty) Text(_s(f['note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
        if (st == 'waiting' || st == 'approved') ...[
          for (final b in _strs(card['blockers'])) Text('✗ $b', style: const TextStyle(fontSize: 12.5, color: C.bad)),
          for (final c in _strs(card['checks'])) Text('• $c', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_strs(card['signers']).isNotEmpty) Text('Sign: ${_strs(card['signers']).join(', ')}', style: const TextStyle(fontSize: 12)),
        ],
        if (st == 'approved') ...[
          const SizedBox(height: 4),
          const Caption('MCA V3 PAR AAP KHUD'),
          for (final (i, s) in _strs(card['steps']).indexed) Text('${i + 1}. $s', style: const TextStyle(fontSize: 12.5)),
        ],
        if (_s(f['srn']).isNotEmpty) Text('SRN ${_s(f['srn'])} · ${_s(f['filed_on'])}', style: const TextStyle(fontSize: 12.5, color: C.ok)),
        const SizedBox(height: 8),
        if (st == 'todo' && !isMeeting)
          Row(children: [
            Expanded(
                child: GlassButton(
                    label: 'Card banao',
                    icon: Icons.fact_check_rounded,
                    height: 40,
                    onTap: _busy ? null : () => _go(() => widget.app.api!.call('POST', '/api/cosec/filings/${_s(f['id'])}/request')))),
            const SizedBox(width: 8),
            GlassButton(label: 'Zaroori nahi', height: 40, onTap: _busy ? null : _skip),
          ]),
        if (st == 'waiting')
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: 'Haan, file karo', height: 42, onTap: _busy || _strs(card['blockers']).isNotEmpty ? null : () => _go(() => _decide(true)))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _go(() => _decide(false))),
          ]),
        if (st == 'approved' || (st == 'todo' && (_s(f['form']).startsWith('DIR-3 KYC') || _s(f['form']) == 'ADT-3')))
          GlassButton(label: 'Ho gaya (SRN)', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : _done),
        const Text('Login, DSC aur fee MCA par aap khud. Draft / jaankari - CS / vakil se pakka.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// cosec_notice / cosec_minutes: a meeting with its notice or minutes waiting for her tap. Also used on the company page.
/// Also in calls (only the two waiting kinds).
class CosecMeetingCard extends StatefulWidget {
  const CosecMeetingCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<CosecMeetingCard> createState() => _CosecMeetingCardState();
}

class _CosecMeetingCardState extends State<CosecMeetingCard> {
  bool _busy = false;
  late Map<String, dynamic> _mt = _m(widget.data['meeting']);

  String get _id => _s(_mt['id']);

  Future<Map<String, dynamic>?> _go(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    Map<String, dynamic>? out;
    try {
      out = _m(await widget.app.api!.call(method, path, body: body));
      if (mounted) {
        final mm = out['meeting'] != null ? _m(out['meeting']) : out;
        if (mm.containsKey('kind_label') && _s(mm['id']) == _id) setState(() => _mt = {..._mt, ...mm});
        _snack(context, _s(out['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    return out;
  }

  Future<void> _notice() async {
    final f = await _form(context, 'Notice', const [('send_on', 'Kab bhejoge (YYYY-MM-DD, khaali = aaj)'), ('mode', 'email / hand / post / courier')]);
    if (f == null) return;
    final short = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
              content: const Text('Shorter notice ki sahmati hai? (zaroori kaam / members ki likhit sahmati)'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, hai')),
              ],
            ));
    await _go('POST', '/api/cosec/meetings/$_id/notice', {...f, 'shorter_consent': short == true});
  }

  Future<void> _attendance() async {
    final f = await _form(context, 'Kaun aaya', const [
      ('present', 'Maujood (naam ya DIN, comma / line)'),
      ('interested', 'Jinka hit juda tha (ho to)'),
      ('chair', 'Chairperson'),
      ('members_count', 'Kul members (general meeting)'),
    ], multi: const {'present'});
    if (f == null || (f['present'] ?? '').isEmpty) return;
    await _go('POST', '/api/cosec/meetings/$_id/attendance', {
      'present': _lines(f['present']),
      'interested': _lines(f['interested']),
      'chair': f['chair'] ?? '',
      'members_count': int.tryParse(f['members_count'] ?? ''),
    });
  }

  Future<void> _resolution() async {
    final general = ['agm', 'egm'].contains(_s(_mt['kind']));
    final f = await _form(context, 'Resolution', [
      ('kind', general ? 'ordinary / special' : 'board'),
      ('text', 'RESOLVED THAT ...'),
      ('votes_for', 'For (votes / shares)'),
      ('votes_against', 'Against'),
    ], multi: const {'text'});
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _go('POST', '/api/cosec/meetings/$_id/resolutions', {
      'kind': f['kind'] ?? (general ? 'ordinary' : 'board'),
      'text': f['text'],
      'votes_for': num.tryParse(f['votes_for'] ?? ''),
      'votes_against': num.tryParse(f['votes_against'] ?? ''),
    });
  }

  Future<void> _editMinutes() async {
    var mt = _mt;
    if (_s(mt['minutes']).isEmpty) {
      final r = await _go('POST', '/api/cosec/meetings/$_id/minutes/draft');
      if (r == null || !mounted) return;
      mt = _mt;
    }
    final f = await _form(context, 'Minutes', const [('text', 'Minutes (bhariye [..] wali jagah)')],
        ok: 'Save', initial: {'text': _s(mt['minutes'])}, multi: const {'text'});
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _go('PUT', '/api/cosec/meetings/$_id/minutes', {'text': f['text']});
  }

  Future<void> _decideNotice(bool yes) async {
    final r = await _go('POST', '/api/cosec/meetings/$_id/notice/decide', {'yes': yes, 'hash': _s(_mt['notice_hash'])});
    if (r != null && yes && mounted) await _showDrafts(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final m = _mt;
    final st = _s(m['status']);
    final card = _m(m['card']);
    final q = _m(m['quorum']);
    final dl = _m(m['deadlines']);
    return Glass(
      border: st.endsWith('waiting') ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.groups_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(m['number'])} · ${_s(m['kind_label'])} · ${_s(m['on'])} ${_s(m['time'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st.endsWith('waiting') ? 'aapki haan?' : st, fg: _stColor(st)),
        ]),
        if (_s(card['entity']).isNotEmpty) Text(_s(card['entity']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (_s(m['place']).isNotEmpty) Text(_s(m['place']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (st == 'draft' && _s(m['latest_notice']).isNotEmpty)
          Text('Notice ${_s(m['latest_notice'])} tak bhejna', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (_s(m['notice_sent_on']).isNotEmpty) Text('Notice gaya: ${_s(m['notice_sent_on'])}', style: const TextStyle(fontSize: 12.5)),
        if (q.isNotEmpty)
          Text('Quorum ${_s(q['present'])} / ${_s(q['need'])} ${q['ok'] == true ? '✓' : '✗'} · ${_s(q['note'])}',
              style: TextStyle(fontSize: 12.5, color: q['ok'] == true ? C.ok : C.bad)),
        if (['held', 'minutes_waiting'].contains(st) && _s(dl['sign_by']).isNotEmpty)
          Text('Minutes ${_s(dl['sign_by'])} tak sign${_s(dl['draft_by']).isNotEmpty ? ' (draft ${_s(dl['draft_by'])} tak directors ko)' : ''}',
              style: const TextStyle(fontSize: 12, color: C.muted)),
        if (st.endsWith('waiting')) ...[
          for (final b in _strs(card['blockers'])) Text('✗ $b', style: const TextStyle(fontSize: 12.5, color: C.bad)),
          for (final c in _strs(card['checks'])) Text('• $c', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_s(card['text']).isNotEmpty)
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text('Poora text dekho', style: TextStyle(fontSize: 13)),
              children: [SelectableText(_s(card['text']), style: const TextStyle(fontSize: 12.5, height: 1.35))],
            ),
        ],
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (st == 'draft') GlassButton(label: 'Notice card', icon: Icons.mail_rounded, height: 40, onTap: _busy ? null : _notice),
          if (st == 'notice_waiting') ...[
            GradientButton(
                label: 'Haan, notice bhejo', height: 42, onTap: _busy || _strs(card['blockers']).isNotEmpty ? null : () => _decideNotice(true)),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decideNotice(false)),
          ],
          if (st == 'notice_sent' || st == 'held')
            GlassButton(label: 'Kaun aaya', icon: Icons.how_to_reg_rounded, height: 40, onTap: _busy ? null : _attendance),
          if (st == 'held') ...[
            GlassButton(label: 'Resolution', icon: Icons.gavel_rounded, height: 40, onTap: _busy ? null : _resolution),
            GlassButton(label: 'Minutes', icon: Icons.edit_note_rounded, height: 40, onTap: _busy ? null : _editMinutes),
            GlassButton(
                label: 'Sign ke liye card', icon: Icons.draw_rounded, height: 40, onTap: _busy ? null : () => _go('POST', '/api/cosec/meetings/$_id/minutes')),
          ],
          if (st == 'minutes_waiting') ...[
            GradientButton(
                label: 'Haan, minutes pakke',
                height: 42,
                onTap: _busy || _strs(card['blockers']).isNotEmpty
                    ? null
                    : () => _go('POST', '/api/cosec/meetings/$_id/minutes/decide', {'yes': true, 'hash': _s(m['minutes_hash'])})),
            GlassButton(
                label: 'Nahi',
                height: 42,
                onTap: _busy ? null : () => _go('POST', '/api/cosec/meetings/$_id/minutes/decide', {'yes': false, 'hash': _s(m['minutes_hash'])})),
          ],
        ]),
        const SizedBox(height: 4),
        const Text('Notice / minutes ka draft: CS / vakil se pakka. Hoola khud kuch nahi bhejta.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// cosec_alert / cosec_day / cosec_event: reminders, the morning note, and what an event created. Calls: no.
class CosecNoteCard extends StatelessWidget {
  const CosecNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.apartment_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
              for (final f in _list(data['filings']))
                Text('• ${_s(f['form'])} ${_s(f['due']).isEmpty ? '' : '— ${_s(f['due'])}'}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
            ]),
          ),
          IconButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CosecScreen(app: app))),
              icon: const Icon(Icons.open_in_new_rounded, size: 18)),
        ]),
      );
}
