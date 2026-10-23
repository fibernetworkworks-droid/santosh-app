/// Profile > Compliance officer (Compliance Sahayak).
/// Aaj (late with penalty andaaza, this week, her taps waiting, questions) · Calendar (own items + GST / Payroll / Daftar / CS rows read
/// from those Sahayaks) · Lagu kya (what applies and why, with sources) · Certificate (monthly draft -> her sign-off) · Niyam (business
/// facts, licence dates, owners, team). Marking a duty done needs a saboot file or her own word; "portal par file karo" and the
/// certificate sign-off happen ONLY on her tap here. Hoola never logs in, pays or submits on a portal. Jaankari, not legal advice.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());
bool? _yes(String? v) {
  if (v == null || v.trim().isEmpty) return null;
  final t = v.trim().toLowerCase();
  return const ['haan', 'ha', 'yes', 'y', 'true', '1', 'hai'].contains(t);
}

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _stateColor(String st) => switch (st) {
      'late' || 'stale' || 'rejected' => C.bad,
      'due' || 'no_date' || 'waiting' || 'file_ok' => C.warn,
      'done' || 'signed' || 'approved' => C.ok,
      _ => C.chip,
    };

String _stateLabel(String st) => switch (st) {
      'late' => 'late',
      'due' => 'is hafte',
      'upcoming' => 'aage',
      'no_date' => 'tareekh?',
      'done' => 'ho gaya',
      'na' => 'lagu nahi',
      'file_ok' => 'file ki haan',
      _ => st,
    };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: (k == 'note' || k == 'reason') ? 3 : 1),
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

class ComplianceScreen extends StatefulWidget {
  const ComplianceScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ComplianceScreen> createState() => _ComplianceScreenState();
}

class _ComplianceScreenState extends State<ComplianceScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _ap;
  Map<String, dynamic>? _cert;
  int _tab = 0;
  bool _busy = false;
  String _area = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/compliance'));
      final ap = _m(await widget.app.api!.call('GET', '/api/compliance/applicability'));
      if (mounted) setState(() {
        _d = d;
        _ap = ap;
      });
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
      .push(MaterialPageRoute(builder: (_) => ComplianceItemPage(app: widget.app, itemRef: ref)))
      .then((_) => _load());

  Widget _itemTile(Map<String, dynamic> v) {
    final st = _s(v['state']);
    final pen = _m(v['penalty']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _open(_s(v['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(v['number'])} · ${_s(v['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_stateLabel(st), fg: _stateColor(st)),
            ]),
            Text(
                [
                  _s(v['area_label']),
                  if (_s(v['due_nice']).isNotEmpty) 'due ${_s(v['due_nice'])}',
                  if (v['days'] != null && st != 'done' && st != 'na') (v['days'] as num) < 0 ? '${-(v['days'] as num)} din late' : '${v['days']} din',
                  if (_s(v['owner']).isNotEmpty) _s(v['owner']),
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (st == 'late' && pen['amount'] != null)
              Text('Penalty andaaza ~Rs ${pen['amount']} (${_s(pen['basis'])})', style: const TextStyle(color: C.bad, fontSize: 12.5))
            else if (st == 'late' && _s(pen['text']).isNotEmpty)
              Text(_s(pen['text']), style: const TextStyle(color: C.bad, fontSize: 12.5)),
          ]),
        ),
      ),
    );
  }

  Widget _linkedTile(Map<String, dynamic> r) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(children: [
          const Icon(Icons.link_rounded, size: 16, color: C.faint),
          const SizedBox(width: 6),
          Expanded(
              child: Text('${_s(r['source_label'])}: ${_s(r['label'])} · ${_s(r['due_nice'])}',
                  style: TextStyle(fontSize: 12.5, color: r['late'] == true ? C.bad : C.muted))),
        ]),
      );

  Widget _today() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: GradientButton(label: 'Calendar banao', icon: Icons.event_repeat_rounded, height: 44, onTap: _busy ? null : () => _run('POST', '/api/compliance/build'))),
        const SizedBox(width: 8),
        GlassButton(label: 'Register', icon: Icons.table_view_rounded, height: 44, onTap: _busy ? null : () => _run('POST', '/api/compliance/register')),
      ]),
      const SizedBox(height: 12),
      if (_list(day['late']).isNotEmpty) ...[const Caption('LATE'), for (final v in _list(day['late'])) _itemTile(v)],
      if (_list(day['soon']).isNotEmpty) ...[const Caption('IS HAFTE'), for (final v in _list(day['soon'])) _itemTile(v)],
      if (_list(day['linked_late']).isNotEmpty) ...[const Caption('DOOSRE SAHAYAK MEIN LATE'), for (final r in _list(day['linked_late'])) _linkedTile(r)],
      for (final f in _list(_d?['filings']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ComplianceFilingCard(app: widget.app, data: {'filing': f}, onDone: _load)),
      if (_strs(day['questions']).isNotEmpty) ...[
        const Caption('AAPSE SAWAAL'),
        for (final q in _strs(day['questions'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $q', style: const TextStyle(fontSize: 13))),
        GlassButton(label: 'Jaankari bharo', icon: Icons.edit_note_rounded, onTap: _editFacts),
      ],
      const SizedBox(height: 10),
      Text(_s(_d?['check']), style: const TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _calendarTab() {
    final cal = _m(_d?['calendar']);
    final items = _list(cal['items']).where((v) => _area.isEmpty || _s(v['area']) == _area).toList();
    final areas = _m(_m(_d?['settings'])['areas']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      SizedBox(
        height: 40,
        child: ListView(scrollDirection: Axis.horizontal, children: [
          Padding(padding: const EdgeInsets.only(right: 6), child: ChoiceChip(label: const Text('Sab'), selected: _area.isEmpty, onSelected: (_) => setState(() => _area = ''))),
          for (final e in areas.entries)
            Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(_s(e.value)), selected: _area == e.key, onSelected: (_) => setState(() => _area = e.key))),
        ]),
      ),
      const SizedBox(height: 8),
      GlassButton(label: 'Apna kaam jodo', icon: Icons.add_task_rounded, onTap: _addCustom),
      const SizedBox(height: 10),
      for (final v in items) _itemTile(v),
      if (items.isEmpty) const Text('Is filter mein koi kaam nahi.', style: TextStyle(color: C.muted)),
      if (_list(cal['linked']).isNotEmpty) ...[
        const SizedBox(height: 10),
        const Caption('DOOSRE SAHAYAK SE (WAHIN PURA KARIYE)'),
        for (final r in _list(cal['linked'])) _linkedTile(r),
      ],
    ]);
  }

  Widget _applyTab() {
    final ap = _m(_ap);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(ap['say']), style: const TextStyle(fontSize: 13.5, height: 1.4))),
      const SizedBox(height: 10),
      for (final x in _list(ap['items']).where((x) => x['applies'] == true))
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(x['label']), style: const TextStyle(fontWeight: FontWeight.w800))),
                if (_s(x['covered_by']).isNotEmpty) Pill('${_s(x['covered_by'])} mein', fg: C.accent),
                if (x['verify'] == true) const Pill('pakka karwaiye', fg: C.warn),
              ]),
              Text('${_s(x['area_label'])} · ${_s(x['why'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
              if (_s(_m(x['source'])['url']).isNotEmpty)
                GestureDetector(
                  onTap: () => Native.openExternal(url: _s(_m(x['source'])['url'])),
                  child: Text('Source: ${_s(_m(x['source'])['title'])} (padha ${_s(_m(x['source'])['read'])})',
                      style: const TextStyle(fontSize: 11.5, color: C.accent)),
                )
              else
                const Text('Source: [citation chahiye] - CA / CS se pakka', style: TextStyle(fontSize: 11.5, color: C.warn)),
            ]),
          ),
        ),
      const Caption('LAGU NAHI'),
      for (final x in _list(ap['items']).where((x) => x['applies'] != true))
        Text('• ${_s(x['label'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  Future<void> _loadCert(String month) async {
    try {
      final c = _m(await widget.app.api!.call('GET', '/api/compliance/certificate', query: month.isEmpty ? null : {'month': month}));
      if (mounted) setState(() => _cert = c);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _certTab() {
    final c = _cert;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(child: GlassButton(label: 'Pichhle mahine ka draft', icon: Icons.description_rounded, onTap: () => _loadCert(''))),
        const SizedBox(width: 8),
        GlassButton(
            label: 'Mahina chuno',
            icon: Icons.calendar_month_rounded,
            onTap: () async {
              final f = await _form(context, 'Mahina', const [('month', 'YYYY-MM (jaise 2026-10)')]);
              if (f != null && (f['month'] ?? '').isNotEmpty) await _loadCert(f['month']!);
            }),
      ]),
      const SizedBox(height: 10),
      if (c != null) ...[
        Glass(child: Text(_s(c['text']), style: const TextStyle(fontSize: 13, height: 1.4))),
        const SizedBox(height: 8),
        for (final x in _list(c['items']))
          Text('• ${_s(x['number'])} ${_s(x['label'])} · ${_s(x['due'])} · ${_stateLabel(_s(x['status']))}${x['carry'] == true ? ' (pichhla)' : ''}',
              style: TextStyle(fontSize: 12.5, color: _s(x['status']) == 'done' ? C.muted : C.warn)),
        for (final x in _list(c['linked'])) Text('• ${_s(x['source'])}: ${_s(x['label'])} · ${_s(x['due'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 10),
        GradientButton(
            label: 'Sign-off card banao',
            icon: Icons.draw_rounded,
            height: 44,
            onTap: _busy ? null : () => _run('POST', '/api/compliance/certificate', {'month': _s(c['month'])})),
      ],
      const SizedBox(height: 12),
      const Caption('CERTIFICATES'),
      for (final x in _list(_d?['certs']))
        x['status'] == 'waiting'
            ? Padding(padding: const EdgeInsets.only(bottom: 8), child: ComplianceCertCard(app: widget.app, data: {'cert': x}, onDone: _load))
            : ListTile(
                dense: true,
                leading: Icon(Icons.verified_rounded, color: _stateColor(_s(x['status']))),
                title: Text('${_s(x['number'])} · ${_s(x['month'])}'),
                subtitle: Text(_s(x['status']) == 'signed' ? 'Sign kiya ${_s(x['signed_on'])}' : _s(x['status'])),
              ),
    ]);
  }

  Future<void> _addCustom() async {
    final f = await _form(context, 'Apna compliance kaam', const [
      ('label', 'Kya kaam (jaise lift inspection, boiler certificate)'),
      ('due', 'Tareekh (DD-MM-YYYY)'),
      ('area', 'Area: licence / labour / fire / pollution / custom'),
      ('owner', 'Kaun karega'),
      ('note', 'Note'),
    ], ok: 'Jodo');
    if (f == null || (f['label'] ?? '').isEmpty) return;
    await _run('POST', '/api/compliance/items', f);
  }

  Future<void> _editFacts() async {
    final st = _m(_d?['settings']);
    final fx = _m(st['facts']);
    final lic = _m(fx['licences']);
    final f = await _form(context, 'Business ki jaankari', const [
      ('entity', 'Type: proprietor / partnership / llp / pvt_ltd / public_ltd / opc / trust'),
      ('state', 'State (Maharashtra ya 27)'),
      ('employees', 'Kitne log kaam karte hain'),
      ('contract_workers', 'Contract workers'),
      ('turnover', 'Pichhle saal ka turnover (Rs)'),
      ('gstin', 'GSTIN (ho to)'),
      ('gst_scheme', 'GST: monthly / qrmp / composition'),
      ('tan', 'TDS kaat-ti hain? (haan / nahi)'),
      ('tcs', 'TCS collect karti hain? (haan / nahi)'),
      ('pt_yearly', 'Staff ka saal ka PT (Rs)'),
      ('sectors', 'Kaam: shop, office, restaurant, factory, food... (comma)'),
      ('food_kind', 'Khana: none / manufacturer / trader / restaurant / milk...'),
      ('pollution', 'Pollution category: none / white / green / orange / red'),
      ('fire_noc', 'Fire NOC chahiye? (haan / nahi)'),
      ('msme_dues', 'MSE supplier ka 45 din se purana baaki? (haan / nahi)'),
      ('agm_date', 'AGM ki tareekh (company)'),
      ('lic_fssai', 'FSSAI licence valid till'),
      ('lic_consent', 'Pollution consent valid till'),
      ('lic_fire', 'Fire NOC valid till'),
      ('lic_shop', 'Shop Act registration valid till'),
      ('lic_trade', 'Trade licence valid till'),
      ('lic_factory', 'Factory licence valid till'),
    ], ok: 'Save', initial: {
      for (final k in ['entity', 'state', 'employees', 'contract_workers', 'turnover', 'gstin', 'gst_scheme', 'pt_yearly', 'food_kind', 'pollution', 'agm_date']) k: _s(fx[k]),
      'sectors': _strs(fx['sectors']).join(', '),
      for (final k in ['tan', 'tcs', 'fire_noc', 'msme_dues']) k: fx[k] == true ? 'haan' : (fx[k] == false ? 'nahi' : ''),
      for (final k in ['fssai', 'consent', 'fire', 'shop', 'trade', 'factory']) 'lic_$k': _s(lic[k]),
    });
    if (f == null) return;
    final facts = <String, dynamic>{};
    final licences = <String, dynamic>{};
    for (final e in f.entries) {
      if (e.key.startsWith('lic_')) {
        licences[e.key.substring(4)] = e.value;
      } else if (['employees', 'contract_workers', 'turnover', 'pt_yearly'].contains(e.key)) {
        facts[e.key] = _n(e.value);
      } else if (['tan', 'tcs', 'fire_noc', 'msme_dues'].contains(e.key)) {
        facts[e.key] = _yes(e.value);
      } else if (e.key == 'sectors') {
        facts['sectors'] = e.value.split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList();
      } else {
        facts[e.key] = e.value;
      }
    }
    if (licences.isNotEmpty) facts['licences'] = licences;
    await _run('PUT', '/api/compliance/settings', {'facts': facts});
  }

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    final owners = _m(st['owners']);
    final f = await _form(context, 'Niyam', const [
      ('firm', 'Business ka naam'),
      ('signatory', 'Certificate par sign karne wala (aapka naam)'),
      ('designation', 'Pad (Director / Proprietor / Partner)'),
      ('windows', 'Yaad dilane ke din (jaise 7,3,1,0)'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('own_tds', 'TDS ka zimmedaar'),
      ('own_gst', 'GST ka zimmedaar'),
      ('own_labour', 'PF / ESIC / labour ka zimmedaar'),
      ('own_licence', 'Licence ka zimmedaar'),
      ('own_roc', 'ROC ka zimmedaar'),
    ], ok: 'Save', initial: {
      for (final k in ['firm', 'signatory', 'designation', 'morning_time']) k: _s(st[k]),
      'windows': _strs(st['windows']).join(','),
      for (final k in ['tds', 'gst', 'labour', 'licence', 'roc']) 'own_$k': _s(owners[k]),
    });
    if (f == null) return;
    final body = <String, dynamic>{};
    final own = <String, dynamic>{...owners};
    for (final e in f.entries) {
      if (e.key.startsWith('own_')) {
        own[e.key.substring(4)] = e.value;
      } else {
        body[e.key] = e.value;
      }
    }
    body['owners'] = own;
    await _run('PUT', '/api/compliance/settings', body);
  }

  Future<void> _addTeam() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Team mein jodo', const [('name', 'Naam'), ('phone', 'Mobile')], ok: 'Jodo');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('PUT', '/api/compliance/settings', {
      'team': [..._list(st['team']), f]
    });
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    final fx = _m(st['facts']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['firm']).isEmpty ? 'Business ka naam daaliye' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text(
              [
                _s(_m(st['entities'])[_s(fx['entity'])]),
                if (_s(fx['state']).isNotEmpty) 'state ${_s(fx['state'])}',
                if (fx['employees'] != null) '${fx['employees']} log',
                if (_s(fx['gstin']).isNotEmpty) 'GSTIN ${_s(fx['gstin'])}',
              ].where((x) => x.isNotEmpty).join(' · '),
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text('Sign-off: ${_s(st['signatory']).isEmpty ? '—' : _s(st['signatory'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'Business ki jaankari', icon: Icons.business_rounded, onTap: _editFacts),
            GlassButton(label: 'Niyam / zimmedaar', icon: Icons.edit_rounded, onTap: _editSettings),
            GlassButton(label: 'Team', icon: Icons.group_add_rounded, onTap: _addTeam),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('TEAM'),
      for (final m in _list(st['team'])) Text('• ${_s(m['name'])} ${_s(m['phone'])}', style: const TextStyle(fontSize: 13)),
      const SizedBox(height: 12),
      const Caption('HOOLA KABHI NAHI'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Aaj', 'Calendar', 'Lagu kya', 'Certificate', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Compliance officer'),
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
                  child: switch (_tab) { 0 => _today(), 1 => _calendarTab(), 2 => _applyTab(), 3 => _certTab(), _ => _rulesTab() },
                ),
        ),
      ]),
    );
  }
}

/// One compliance item: due, owner, saboot files, done (file or her word), lagu nahi, file karne ka card, nudge draft, log.
class ComplianceItemPage extends StatefulWidget {
  const ComplianceItemPage({super.key, required this.app, required this.itemRef});
  final Santosh app;
  final String itemRef;
  @override
  State<ComplianceItemPage> createState() => _ComplianceItemPageState();
}

class _ComplianceItemPageState extends State<ComplianceItemPage> {
  Map<String, dynamic>? _v;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', '/api/compliance/items/${widget.itemRef}'));
      if (mounted) setState(() => _v = v);
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

  Future<String?> _pickFile() async {
    final conv = widget.app.conversationId;
    if (conv == null) {
      _snack(context, 'Pehle chat khulne dijiye.');
      return null;
    }
    final files = await pickAttachmentsOfType(context, FileType.any);
    if (files.isEmpty) return null;
    try {
      final r = await widget.app.api!.chatFile(conv, files.first.name, files.first.bytes);
      return _s(r['file_id']);
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    }
  }

  Future<void> _evidence() async {
    final fid = await _pickFile();
    if (fid == null || fid.isEmpty) return;
    await _run('POST', '/api/compliance/items/${widget.itemRef}/evidence', {'file_id': fid});
  }

  Future<void> _done({required bool word}) async {
    final f = await _form(context, word ? 'Maine kar diya (bina file)' : 'Ho gaya', const [('ack', 'ARN / SRN / challan no. (ho to)'), ('note', 'Note')],
        ok: 'Ho gaya');
    if (f == null) return;
    String? fid;
    if (!word && (_list(_v?['evidence']).isEmpty)) {
      fid = await _pickFile();
      if (fid == null || fid.isEmpty) return;
    }
    await _run('POST', '/api/compliance/items/${widget.itemRef}/done', {...f, 'her_word': word, if (fid != null) 'file_id': fid});
  }

  Future<void> _na() async {
    final f = await _form(context, 'Lagu nahi', const [('reason', 'Kyun lagu nahi (certificate mein jaayega)')], ok: 'Save');
    if (f == null || (f['reason'] ?? '').isEmpty) return;
    await _run('POST', '/api/compliance/items/${widget.itemRef}/na', f);
  }

  Future<void> _edit() async {
    final v = _m(_v);
    final f = await _form(context, 'Tareekh / zimmedaar', const [('due', 'Aapki tareekh (DD-MM-YYYY)'), ('owner', 'Kaun karega'), ('note', 'Note')],
        ok: 'Save', initial: {'owner': _s(v['owner']), 'note': _s(v['note'])});
    if (f == null) return;
    await _run('PATCH', '/api/compliance/items/${widget.itemRef}', f);
  }

  Future<void> _nudge() async {
    final r = await _call(context, widget.app, 'GET', '/api/compliance/items/${widget.itemRef}/nudge');
    if (r != null && _s(r['whatsapp']).isNotEmpty) await Native.openExternal(url: _s(r['whatsapp']));
  }

  @override
  Widget build(BuildContext context) {
    final v = _m(_v);
    final st = _s(v['state']);
    final pen = _m(v['penalty']);
    final src = _m(v['source']);
    final open = st != 'done' && st != 'na';
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(v['number']).isEmpty ? 'Kaam' : _s(v['number']))),
      body: _v == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(_s(v['label']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
                    Pill(_stateLabel(st), fg: _stateColor(st)),
                  ]),
                  Text('${_s(v['area_label'])} · due ${_s(v['due_nice']).isEmpty ? '?' : _s(v['due_nice'])}${v['due_own'] == true ? ' (aapki tareekh)' : ''}',
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (_s(v['owner']).isNotEmpty) Text('Zimmedaar: ${_s(v['owner'])}', style: const TextStyle(fontSize: 12.5)),
                  if (_s(v['portal']).isNotEmpty) Text('Portal: ${_s(v['portal'])}', style: const TextStyle(fontSize: 12.5)),
                  Text('Saboot: ${_s(v['evidence_hint'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                  if (_s(pen['text']).isNotEmpty)
                    Text('Penalty (starter): ${_s(pen['text'])}${pen['amount'] != null ? ' · andaaza ~Rs ${pen['amount']}' : ''}',
                        style: TextStyle(fontSize: 12.5, color: st == 'late' ? C.bad : C.muted)),
                  if (_s(src['url']).isNotEmpty)
                    GestureDetector(
                        onTap: () => Native.openExternal(url: _s(src['url'])),
                        child: Text('Source: ${_s(src['title'])}', style: const TextStyle(fontSize: 11.5, color: C.accent)))
                  else
                    Text('Source: ${_s(src['title'])}', style: const TextStyle(fontSize: 11.5, color: C.warn)),
                  if (v['verify'] == true) const Text('CA / CS / vakil se pakka karwaiye.', style: TextStyle(fontSize: 11.5, color: C.warn)),
                  if (_s(v['ack']).isNotEmpty) Text('Ack: ${_s(v['ack'])}', style: const TextStyle(fontSize: 12.5)),
                  if (_s(v['done_how']).isNotEmpty)
                    Text(_s(v['done_how']) == 'evidence' ? 'Ho gaya: saboot ke saath' : 'Ho gaya: aapke kehne par',
                        style: const TextStyle(fontSize: 12.5, color: C.ok)),
                  if (_s(v['note']).isNotEmpty) Text(_s(v['note']), style: const TextStyle(fontSize: 12.5)),
                ]),
              ),
              const SizedBox(height: 10),
              if (open)
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GradientButton(label: 'Ho gaya (file ke saath)', icon: Icons.task_alt_rounded, height: 42, onTap: _busy ? null : () => _done(word: false)),
                  GlassButton(label: 'Maine kar diya', icon: Icons.record_voice_over_rounded, height: 42, onTap: _busy ? null : () => _done(word: true)),
                  GlassButton(label: 'Saboot jodo', icon: Icons.attach_file_rounded, height: 42, onTap: _busy ? null : _evidence),
                  GlassButton(label: 'File karne ka card', icon: Icons.upload_file_rounded, height: 42,
                      onTap: _busy ? null : () => _run('POST', '/api/compliance/items/${widget.itemRef}/filing')),
                  GlassButton(label: 'Tareekh / zimmedaar', icon: Icons.edit_calendar_rounded, height: 42, onTap: _busy ? null : _edit),
                  GlassButton(label: 'Yaad dilao (draft)', icon: Icons.chat_rounded, height: 42, onTap: _busy ? null : _nudge),
                  GlassButton(label: 'Lagu nahi', icon: Icons.block_rounded, height: 42, onTap: _busy ? null : _na),
                ])
              else
                GlassButton(label: 'Dobara kholo', icon: Icons.undo_rounded, onTap: _busy ? null : () => _run('POST', '/api/compliance/items/${widget.itemRef}/reopen')),
              const SizedBox(height: 12),
              if (_list(v['evidence']).isNotEmpty) ...[
                const Caption('SABOOT'),
                for (final e in _list(v['evidence'])) Text('• ${_s(e['name'])} · ${_s(e['at'])} · ${_s(e['by'])}', style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 10),
              ],
              if (_strs(v['steps']).isNotEmpty) ...[
                const Caption('PORTAL PAR (AAP KHUD)'),
                for (final t in _strs(v['steps'])) Text('• $t', style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 10),
              ],
              const Caption('LOG'),
              for (final l in _list(v['log']).reversed) Text('${_s(l['at']).replaceAll('T', ' ')} · ${_s(l['by'])}: ${_s(l['what'])}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
            ]),
    );
  }
}

/// compliance_filing: "portal par file karo?" ONLY on her tap (hash checked). She logs in / pays / submits herself. Also in calls.
class ComplianceFilingCard extends StatefulWidget {
  const ComplianceFilingCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ComplianceFilingCard> createState() => _ComplianceFilingCardState();
}

class _ComplianceFilingCardState extends State<ComplianceFilingCard> {
  bool _busy = false;
  late Map<String, dynamic> _f = _m(widget.data['filing']);

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/compliance/filings/${_s(_f['id'])}/decide', body: {'yes': yes, 'hash': _s(_f['hash'])}));
      if (mounted) {
        final st = _s(r['status']).isNotEmpty ? _s(r['status']) : _s(_m(r['filing'])['status']);
        setState(() => _f = {..._f, 'status': st.isEmpty ? (yes ? 'approved' : 'rejected') : st});
        _snack(context, _s(r['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) {
        setState(() => _f = {..._f, 'status': 'stale'});
        _snack(context, '$e');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(_f['status']);
    final show = _m(_f['show']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.upload_file_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(_f['number'])} · ${_s(show['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'stale' => 'purana', 'rejected' => 'nahi', _ => st }, fg: _stateColor(st)),
        ]),
        Text('Due ${_s(show['due'])} · ${_s(show['portal'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final t in _strs(show['steps'])) Text('• $t', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, file karungi', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Abhi nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'stale') const Text('Kaam badal gaya: naya card banaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        const Text('Login, OTP, payment aur submit aap khud karti hain; Hoola nahi.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// compliance_cert: monthly compliance certificate; sign-off ONLY on her tap (hash checked, stale if anything changed). Also in calls.
class ComplianceCertCard extends StatefulWidget {
  const ComplianceCertCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ComplianceCertCard> createState() => _ComplianceCertCardState();
}

class _ComplianceCertCardState extends State<ComplianceCertCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['cert']);

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/compliance/certs/${_s(_c['id'])}/decide', body: {'yes': yes, 'hash': _s(_c['hash'])}));
      if (mounted) {
        final c = _m(r['cert']);
        setState(() => _c = {..._c, 'status': _s(c['status']).isEmpty ? (yes ? 'signed' : 'rejected') : _s(c['status'])});
        _snack(context, _s(r['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) {
        setState(() => _c = {..._c, 'status': 'stale'});
        _snack(context, '$e');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(_c['status']);
    final content = _m(_c['content']);
    final counts = _m(content['counts']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.verified_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(_c['number'])} · Compliance certificate ${_s(content['month_label']).isEmpty ? _s(_c['month']) : _s(content['month_label'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'sign-off?', 'signed' => 'sign kiya', 'stale' => 'purana', 'rejected' => 'nahi', _ => st }, fg: _stateColor(st)),
        ]),
        if (counts.isNotEmpty)
          Text('Kul ${_s(counts['total'])} · ho gaye ${(counts['done_evidence'] ?? 0) + (counts['done_word'] ?? 0)} · baaki ${_s(counts['open'])} · lagu nahi ${_s(counts['na'])}',
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final e in _strs(content['exceptions']).take(6)) Text('• $e', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (_s(content['text']).isNotEmpty) Text(_s(content['text']), maxLines: 6, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, sign-off', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'stale') const Text('Card ke baad kaam badle: naya draft banaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        const Text('App mein tap = sign-off (digital signature nahi). Draft / jaankari: CA / CS se pakka karwaiye.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// compliance_alert / compliance_day: reminders, late with penalty andaaza, morning note.
class ComplianceNoteCard extends StatelessWidget {
  const ComplianceNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final item = _m(data['item']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.fact_check_rounded, color: C.accent),
        const SizedBox(width: 8),
        Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4))),
        IconButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => item.isNotEmpty ? ComplianceItemPage(app: app, itemRef: _s(item['id'])) : ComplianceScreen(app: app))),
            icon: const Icon(Icons.open_in_new_rounded, size: 18)),
      ]),
    );
  }
}
