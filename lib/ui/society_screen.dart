/// Profile > Society Sahayak: Hoola as the housing society manager / secretary's coworker.
/// Aaj (cards waiting for her, dues, complaints, dates) · Flats (members, nominations, parking, receipts) · Bills (make, dues,
/// reminders) · Shikayat · Meeting (AGM / SGM / committee: notice, attendance, resolutions, minutes) · Kharcha (vendors / AMC,
/// spends) · Gate (staff + visitors) · Niyam (heads, caps, accounts for the auditor).
/// Bills to members, notices, messages, spends (fingerprint once a phone key is set up) and penalties run ONLY after HER tap.
/// Hoola never takes or pays money: the bill carries the society's own UPI link and she marks "paisa mila".
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
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

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Continue', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(
                controller: c[k],
                decoration: InputDecoration(labelText: label),
                maxLines: (k == 'body' || k == 'text' || k == 'notes' || k == 'agenda') ? 4 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
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

class SocietyScreen extends StatefulWidget {
  const SocietyScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SocietyScreen> createState() => _SocietyScreenState();
}

class _SocietyScreenState extends State<SocietyScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic> _dues = {};
  Map<String, dynamic> _acc = {};
  List<Map<String, dynamic>> _complaints = [];
  List<Map<String, dynamic>> _spends = [];
  List<Map<String, dynamic>> _visits = [];
  List<Map<String, dynamic>> _calendar = [];
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = widget.app.api!;
      final d = _m(await api.call('GET', '/api/society'));
      final du = _m(await api.call('GET', '/api/society/dues'));
      final cp = _m(await api.call('GET', '/api/society/complaints', query: {'status': 'open'}));
      final sp = _m(await api.call('GET', '/api/society/spends'));
      final vi = _m(await api.call('GET', '/api/society/visits', query: {'inside': 'true'}));
      final ca = _m(await api.call('GET', '/api/society/calendar'));
      final ac = _m(await api.call('GET', '/api/society/accounts'));
      if (mounted) {
        setState(() {
          _d = d;
          _dues = du;
          _complaints = _list(cp['complaints']);
          _spends = _list(sp['spends']);
          _visits = _list(vi['visits']);
          _calendar = _list(ca['calendar']);
          _acc = ac;
        });
      }
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

  void _openFlat(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => SocietyFlatPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _addFlat() async {
    final f = await _form(context, 'New flat / member', const [
      ('unit', 'Flat no (A-101)'),
      ('owner_name', 'Member name'),
      ('owner_phone', 'Mobile'),
      ('carpet_sqft', 'Carpet area (sq ft)'),
      ('taps', 'Number of taps / inlets'),
      ('cost', 'Construction cost ₹ (architect certificate)'),
      ('opening_due', 'Previous dues ₹ (if any)'),
    ], ok: 'Add');
    if (f == null || (f['unit'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    for (final k in ['carpet_sqft', 'taps', 'cost', 'opening_due']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _run('POST', '/api/society/flats', body);
  }

  Future<void> _importFlats() async {
    final files = await pickAttachmentsOfType(context, FileType.any);
    if (files.isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/society/flats/import', files.first.name, files.first.bytes);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _makeBills() async {
    final f = await _form(context, 'This month\'s bills', const [('period', 'Month (YYYY-MM, empty = this month)')], ok: 'Make bills');
    if (f == null) return;
    await _run('POST', '/api/society/bills', {'period': f['period'] ?? ''});
  }

  Future<void> _remind() async {
    final f = await _form(context, 'Dues reminder', const [('min_days', 'Minimum age of dues (days)'), ('text', 'Your own message (empty = Hoola\'s)')],
        ok: 'Make card');
    if (f == null) return;
    await _run('POST', '/api/society/remind', {'min_days': int.tryParse(f['min_days'] ?? '') ?? 0, 'text': f['text'] ?? ''});
  }

  Future<void> _complaint() async {
    final f = await _form(context, 'New complaint / request', const [('flat', 'Flat (if any)'), ('text', 'What is the problem')], ok: 'Record it');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '/api/society/complaints', f);
  }

  Future<void> _complaintStatus(Map<String, dynamic> c) async {
    final st = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (_) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, l) in const [('assigned', 'Given to vendor'), ('working', 'Work in progress'), ('resolved', 'Fixed'), ('closed', 'Closed')])
            ListTile(title: Text(l), onTap: () => Navigator.pop(context, k)),
        ]),
      ),
    );
    if (st == null) return;
    await _run('PATCH', '/api/society/complaints/${_s(c['id'])}', {'status': st});
  }

  Future<void> _meeting() async {
    final f = await _form(context, 'New meeting', const [
      ('kind', 'agm / sgm / committee'),
      ('day', 'Date (YYYY-MM-DD)'),
      ('time', 'Time (HH:MM)'),
      ('place', 'Place'),
      ('agenda', 'Agenda: one topic per line (empty for AGM = standard)'),
    ], ok: 'Plan');
    if (f == null || (f['day'] ?? '').isEmpty) return;
    final agenda = (f['agenda'] ?? '').split('\n').map((x) => x.trim()).where((x) => x.isNotEmpty).toList();
    final r = await _run('POST', '/api/society/meetings',
        {'kind': f['kind'] ?? 'agm', 'day': f['day'], 'time': f['time'] ?? '', 'place': f['place'] ?? '', if (agenda.isNotEmpty) 'agenda': agenda});
    final m = _m(r?['meeting']);
    if (m.isNotEmpty && mounted) _openMeeting(_s(m['id']));
  }

  void _openMeeting(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => SocietyMeetingPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _notice() async {
    final f = await _form(context, 'Notice / circular', const [('kind', 'notice / circular / defaulters'), ('title', 'Subject'), ('body', 'Text')],
        ok: 'Make draft');
    if (f == null) return;
    final r = await _run('POST', '/api/society/notices', {'kind': f['kind'] ?? 'notice', 'title': f['title'] ?? '', 'body': f['body'] ?? ''});
    final n = _m(r?['notice']);
    if (n.isNotEmpty && mounted) {
      final go = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
                title: Text(_s(n['title'])),
                content: SingleChildScrollView(child: Text([_s(n['body']), ..._strs(n['checks']).map((c) => '⚠ $c')].join('\n\n'))),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Not now')),
                  TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Card for your approval')),
                ],
              ));
      if (go == true) await _run('POST', '/api/society/notices/${_s(n['id'])}/send');
    }
  }

  Future<void> _contract() async {
    final f = await _form(context, 'Vendor / AMC', const [
      ('vendor', 'Vendor name'),
      ('kind', 'lift / security / housekeeping / water_tank / pest / fire / cctv / generator / pump / other'),
      ('phone', 'Mobile'),
      ('amount', 'Amount ₹ (of the contract)'),
      ('per', 'month / year / visit'),
      ('start', 'Start (YYYY-MM-DD)'),
      ('end', 'End (YYYY-MM-DD)'),
    ], ok: 'Save');
    if (f == null || (f['vendor'] ?? '').isEmpty) return;
    await _run('POST', '/api/society/contracts', {...f, if (f['amount'] != null) 'amount': _n(f['amount'])});
  }

  Future<void> _spend() async {
    final f = await _form(context, 'New expense (with your approval)', const [
      ('kind', 'repair / amc / purchase / tax / utility / audit / other'),
      ('what', 'For what'),
      ('amount', 'Amount ₹ (from quote / bill)'),
      ('vendor', 'Vendor'),
      ('fund', 'general / repair / sinking'),
      ('resolution', 'General body resolution (sinking / major repair)'),
    ], ok: 'Make card');
    if (f == null || (f['what'] ?? '').isEmpty) return;
    await _run('POST', '/api/society/spends', {...f, 'amount': _n(f['amount'])});
  }

  Future<void> _visitor() async {
    final f = await _form(context, 'Gate entry', const [
      ('name', 'Name'),
      ('flat', 'Which flat'),
      ('purpose', 'Work'),
      ('phone', 'Mobile (only the last 4 digits are kept)'),
      ('vehicle', 'Vehicle no.'),
      ('kind', 'visitor / delivery / staff / vendor'),
    ], ok: 'Inside');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('POST', '/api/society/visits', f);
  }

  Future<void> _staff() async {
    final f = await _form(context, 'Society staff', const [
      ('name', 'Name'),
      ('role', 'guard / housekeeping / lift_operator / gardener / plumber / electrician / maid / driver / other'),
      ('agency', 'Agency'),
      ('phone', 'Mobile'),
      ('verified_on', 'Police verification date'),
    ], ok: 'Save');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('POST', '/api/society/staff', f);
  }

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Society details and rules', const [
      ('name', 'Society name'),
      ('reg_no', 'Registration no'),
      ('address', 'Address'),
      ('state', 'State (MH...)'),
      ('upi_id', 'Society UPI ID'),
      ('upi_name', 'Name on UPI'),
      ('noc_pct', 'Non-occupancy % (MH max 10)'),
      ('interest_pct', 'Interest % per year (GB rate, MH max 12)'),
      ('grace_days', 'Grace days before interest'),
      ('due_days', 'Days after the bill when it is due'),
      ('bill_day', 'Day to make bills (1-28)'),
      ('term_ends', 'Committee term ends (YYYY-MM-DD)'),
      ('auditor', 'Statutory auditor'),
      ('morning_time', 'Morning note (HH:MM)'),
      ('rules', 'Your bye-law notes'),
    ], ok: 'Save', initial: {for (final e in st.entries) if (e.value != null && e.value is! Map && e.value is! List) e.key: '${e.value}'});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['noc_pct', 'interest_pct', 'grace_days', 'due_days', 'bill_day']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _run('PUT', '/api/society/settings', body);
  }

  Future<void> _head(Map<String, dynamic> h) async {
    final f = await _form(context, _s(h['label']), const [('rate', 'Rate (your number)'), ('label', 'Name')],
        ok: 'Save', initial: {'rate': h['rate'] is Map ? '' : _s(h['rate']), 'label': _s(h['label'])});
    if (f == null) return;
    final rate = h['basis'] == 'parking' ? {'car': _n(f['rate'])} : _n(f['rate']);
    await _run('POST', '/api/society/heads', {'key': h['key'], 'rate': rate, 'label': f['label'] ?? ''});
  }

  Widget _cardsList(List<Map<String, dynamic>> cards) => Column(children: [
        for (final c in cards) ...[SocietyApprovalCard(app: widget.app, data: {'card': c}, onDone: _load), const SizedBox(height: 8)],
      ]);

  Widget _todayTab() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: GradientButton(label: 'Make bills', icon: Icons.receipt_long_rounded, height: 46, onTap: _busy ? null : _makeBills)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Complaint', icon: Icons.report_problem_rounded, onTap: _busy ? null : _complaint)),
      ]),
      const SizedBox(height: 12),
      if (_list(day['cards']).isNotEmpty) ...[const Caption('NEEDS YOUR APPROVAL'), _cardsList(_list(day['cards']))],
      if (_list(day['calendar']).isNotEmpty) ...[
        const Caption('DATES'),
        for (final c in _list(day['calendar']))
          ListTile(
              dense: true,
              leading: Icon(Icons.event_rounded, color: (c['days_left'] ?? 0) < 0 ? C.bad : C.warn),
              title: Text(_s(c['what'])),
              subtitle: Text('${_s(c['on'])} · ${(c['days_left'] ?? 0) < 0 ? 'expired' : '${c['days_left']} days'}')),
      ],
      if (_complaints.isNotEmpty) ...[
        const Caption('OPEN COMPLAINTS'),
        for (final c in _complaints.take(5)) SocietyComplaintCard(app: widget.app, data: {'complaint': c}),
      ],
    ]);
  }

  Widget _flatsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'Add flat', icon: Icons.add_home_rounded, height: 46, onTap: _busy ? null : _addFlat)),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Member sheet', icon: Icons.upload_file_rounded, onTap: _busy ? null : _importFlats)),
        ]),
        const SizedBox(height: 12),
        for (final f in _list(_d?['flats']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _openFlat(_s(f['id'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  const Icon(Icons.apartment_rounded, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(f['unit'])} · ${_s(f['owner_name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text(
                        [
                          if (f['occupancy'] == 'tenant') 'tenant',
                          if (_list(f['parking']).isNotEmpty) 'parking ${_list(f['parking']).map((p) => _s(p['slot'])).join(', ')}',
                          if (_strs(f['missing']).isNotEmpty) 'pending: ${_strs(f['missing']).join(', ')}',
                        ].join(' · '),
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ])),
                  if ((f['due'] ?? 0) > 0) Pill(_s(f['due_text']), fg: C.warn),
                ]),
              ),
            ),
          ),
        if (_list(_d?['flats']).isEmpty) const Text('No flats yet. Add one or add the member list sheet.', style: TextStyle(color: C.muted)),
      ]);

  Widget _billsTab() {
    final b = _m(_dues['buckets']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Total dues: ${_s(_dues['total_text'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          Text('0-30: ₹${_s(b['0-30'])} · 31-90: ₹${_s(b['31-90'])} · 91-180: ₹${_s(b['91-180'])} · 180+: ₹${_s(b['180+'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(_dues['recovery']).isNotEmpty && _list(_dues['defaulters']).isNotEmpty)
            Text(_s(_dues['recovery']), style: const TextStyle(color: C.faint, fontSize: 11.5)),
        ]),
      ),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: GradientButton(label: 'Make bills', icon: Icons.receipt_long_rounded, height: 46, onTap: _busy ? null : _makeBills)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Remind', icon: Icons.notifications_active_rounded, onTap: _busy ? null : _remind)),
      ]),
      const SizedBox(height: 12),
      const Caption('DUES (BY FLAT)'),
      for (final r in _list(_dues['flats']))
        ListTile(
          dense: true,
          leading: Icon(Icons.circle, size: 12, color: r['defaulter'] == true ? C.bad : C.warn),
          title: Text('${_s(r['unit'])} · ${_s(r['owner'])}'),
          subtitle: Text('${_s(r['days'])} days · ${_s(r['bucket'])}${r['no_messages'] == true ? ' · do not want messages' : ''}'),
          trailing: Text(_s(r['due_text']), style: const TextStyle(fontWeight: FontWeight.w800)),
          onTap: () {
            final f = _list(_d?['flats']).where((x) => x['unit'] == r['unit']).toList();
            if (f.isNotEmpty) _openFlat(_s(f.first['id']));
          },
        ),
      if (_list(_dues['flats']).isEmpty) const Text('No dues on anyone.', style: TextStyle(color: C.muted)),
    ]);
  }

  Widget _complaintsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New complaint / request', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _complaint),
        const SizedBox(height: 12),
        for (final c in _complaints)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(onTap: () => _complaintStatus(c), child: SocietyComplaintCard(app: widget.app, data: {'complaint': c})),
          ),
        if (_complaints.isEmpty) const Text('No open complaints.', style: TextStyle(color: C.muted)),
      ]);

  Widget _meetingsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'New meeting', icon: Icons.groups_rounded, height: 46, onTap: _busy ? null : _meeting)),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Notice / circular', icon: Icons.campaign_rounded, onTap: _busy ? null : _notice)),
        ]),
        const SizedBox(height: 12),
        const Caption('MEETINGS'),
        for (final m in _list(_d?['meetings']))
          ListTile(
            dense: true,
            leading: const Icon(Icons.event_note_rounded, color: C.accent),
            title: Text('${_s(m['number'])} · ${_s(m['kind']).toUpperCase()} · ${_s(m['day'])}'),
            subtitle: Text('${_s(m['status'])} · quorum ${_s(m['quorum'])}'),
            onTap: () => _openMeeting(_s(m['id'])),
          ),
        const SizedBox(height: 8),
        const Caption('NOTICES'),
        for (final n in _list(_d?['notices']))
          ListTile(
            dense: true,
            leading: Icon(Icons.description_rounded, color: n['status'] == 'approved' ? C.ok : C.faint),
            title: Text('${_s(n['number'])} · ${_s(n['title'])}'),
            subtitle: Text('${_s(n['kind_label'])} · ${_s(n['status'])}${_s(n['issued_on']).isEmpty ? '' : ' · ${_s(n['issued_on'])}'}'),
            onTap: n['status'] == 'draft' ? () => _run('POST', '/api/society/notices/${_s(n['id'])}/send') : null,
          ),
      ]);

  Widget _spendTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'Expense card', icon: Icons.payments_rounded, height: 46, onTap: _busy ? null : _spend)),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Vendor / AMC', icon: Icons.handyman_rounded, onTap: _busy ? null : _contract)),
        ]),
        const SizedBox(height: 12),
        const Caption('VENDORS / AMC'),
        for (final c in _list(_d?['contracts']))
          ListTile(
            dense: true,
            leading: Icon(Icons.handshake_rounded, color: (c['days_left'] ?? 999) <= 30 ? C.warn : C.ok),
            title: Text('${_s(c['vendor'])} · ${_s(c['kind_label'])}'),
            subtitle: Text([
              if (_s(c['amount_text']).isNotEmpty) '${_s(c['amount_text'])}/${_s(c['per'])}',
              if (_s(c['end']).isNotEmpty) 'ends ${_s(c['end'])} (${_s(c['days_left'])} days)',
            ].join(' · ')),
            trailing: _s(c['phone']).isEmpty
                ? null
                : IconButton(icon: const Icon(Icons.call_rounded), onPressed: () => Native.openExternal(url: 'tel:${_s(c['phone'])}')),
          ),
        const SizedBox(height: 8),
        const Caption('EXPENSES'),
        for (final x in _spends)
          ListTile(
            dense: true,
            title: Text('${_s(x['number'])} · ${_s(x['what'])}'),
            subtitle: Text('${_s(x['kind_label'])} · ${_s(x['fund_label'])} · ${_s(x['status'])}'),
            trailing: x['status'] == 'approved'
                ? TextButton(
                    child: const Text('I have paid'),
                    onPressed: () async {
                      final f = await _form(context, 'I have paid', const [('amount', 'How much paid'), ('ref', 'UTR / cheque no')],
                          initial: {'amount': _s(x['amount'])});
                      if (f != null) await _run('POST', '/api/society/spends/${_s(x['id'])}/done', {'amount': _n(f['amount']), 'ref': f['ref'] ?? ''});
                    })
                : Text(_s(x['amount_text']), style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
      ]);

  Widget _gateTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'Gate entry', icon: Icons.login_rounded, height: 46, onTap: _busy ? null : _visitor)),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Add staff', icon: Icons.badge_rounded, onTap: _busy ? null : _staff)),
        ]),
        const SizedBox(height: 12),
        const Caption('INSIDE NOW'),
        for (final v in _visits)
          ListTile(
            dense: true,
            leading: const Icon(Icons.person_pin_circle_rounded, color: C.accent),
            title: Text('${_s(v['name'])} · ${_s(v['unit'])}'),
            subtitle: Text([_s(v['kind']), _s(v['purpose']), _s(v['vehicle'])].where((x) => x.isNotEmpty).join(' · ')),
            trailing: TextButton(child: const Text('Outside'), onPressed: () => _run('POST', '/api/society/visits/${_s(v['id'])}/out')),
          ),
        if (_visits.isEmpty) const Text('Nobody inside right now.', style: TextStyle(color: C.muted)),
        const SizedBox(height: 8),
        const Caption('STAFF'),
        for (final x in _list(_d?['staff']))
          ListTile(
            dense: true,
            leading: Icon(Icons.badge_rounded, color: x['recheck_due'] == true ? C.warn : C.ok),
            title: Text('${_s(x['name'])} · ${_s(x['role'])}'),
            subtitle: Text(_s(x['verified_on']).isEmpty ? 'No police verification' : 'Verified ${_s(x['verified_on'])} · again ${_s(x['recheck_on'])}'),
          ),
        const Text('Gate register entries are deleted automatically after the days you set (DPDP); only the last 4 digits of the phone are kept.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]);

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    final caps = _m(st['caps']);
    final inc = _m(_acc['income']);
    final exp = _m(_acc['expenditure']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['name']).isEmpty ? 'Society' : _s(st['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text(_s(st['law']), style: const TextStyle(color: C.muted, fontSize: 12)),
          Text(
              'UPI: ${_s(st['upi_id']).isEmpty ? 'not given' : _s(st['upi_id'])} · Non-occupancy ${_s(st['noc_pct'])}% · Interest ${_s(st['interest_pct'])}%'
              '${caps['noc_cap_pct'] != null ? ' (limit ${caps['noc_cap_pct']}% / ${caps['interest_cap_pct']}%)' : ''}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          for (final p in _strs(st['warnings'])) Text('⚠ $p', style: const TextStyle(color: C.warn, fontSize: 12)),
          const SizedBox(height: 8),
          GlassButton(label: 'Edit', icon: Icons.edit_rounded, onTap: _settings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('BILL HEADS (TAP = RATE)'),
      for (final h in _list(st['heads']))
        ListTile(
          dense: true,
          title: Text(_s(h['label'])),
          subtitle: Text(_s(_m(st['bases'])[h['basis']])),
          trailing: Text(h['rate'] == null ? 'no rate' : (h['rate'] is Map ? _m(h['rate']).entries.map((e) => '${e.key} ₹${e.value}').join(', ') : _s(h['rate']))),
          onTap: () => _head(h),
        ),
      const SizedBox(height: 12),
      Caption('ACCOUNTS FY ${_s(_acc['fy'])} (FOR THE AUDITOR)'),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final e in inc.entries) Text('${e.key}: ₹${e.value}', style: const TextStyle(fontSize: 12.5)),
          Text('Income: ₹${_s(_acc['income_total'])} · Expense: ₹${_s(_acc['expenditure_total'])} · Surplus: ₹${_s(_acc['surplus'])}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final e in exp.entries) Text('− ${e.key}: ₹${e.value}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          for (final n in _strs(_acc['notes'])) Text(n, style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      ),
      const SizedBox(height: 8),
      GlassButton(label: 'Excel register', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run('POST', '/api/society/register')),
      const SizedBox(height: 12),
      const Caption('DATES'),
      for (final c in _calendar)
        ListTile(
            dense: true,
            leading: Icon(c['done'] == true ? Icons.check_circle_rounded : Icons.event_rounded, color: c['done'] == true ? C.ok : C.warn),
            title: Text(_s(c['what'])),
            subtitle: Text(_s(c['on']))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Today', 'Flats', 'Bills', 'Complaints', 'Meeting', 'Expenses', 'Gate', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Society manager'),
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
                  child: switch (_tab) {
                    0 => _todayTab(),
                    1 => _flatsTab(),
                    2 => _billsTab(),
                    3 => _complaintsTab(),
                    4 => _meetingsTab(),
                    5 => _spendTab(),
                    6 => _gateTab(),
                    _ => _rulesTab(),
                  },
                ),
        ),
      ]),
    );
  }
}

/// One flat: member, joint, nominations, parking, bills, receipts; "paisa mila" (receipt) only by her.
class SocietyFlatPage extends StatefulWidget {
  const SocietyFlatPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<SocietyFlatPage> createState() => _SocietyFlatPageState();
}

class _SocietyFlatPageState extends State<SocietyFlatPage> {
  Map<String, dynamic>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final f = _m(await widget.app.api!.call('GET', '/api/society/flats/${widget.id}'));
      if (mounted) setState(() => _f = f);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(String method, String path, [Object? body]) async {
    await _call(context, widget.app, method, path, body);
    await _load();
  }

  Future<void> _edit() async {
    final f = _f ?? {};
    final r = await _form(context, 'Flat ${_s(f['unit'])}', const [
      ('owner_name', 'Member'),
      ('owner_phone', 'Mobile'),
      ('owner_email', 'Email'),
      ('carpet_sqft', 'Carpet sq ft'),
      ('taps', 'Tap'),
      ('cost', 'Construction cost ₹'),
      ('share_cert', 'Share certificate no'),
      ('shares', 'Shares (101-105)'),
      ('occupancy', 'self / tenant / vacant'),
      ('tenant_name', 'Tenant name'),
      ('tenant_phone', 'Tenant mobile'),
    ], ok: 'Save', initial: {for (final e in f.entries) if (e.value != null && e.value is! Map && e.value is! List) e.key: '${e.value}'});
    if (r == null) return;
    final body = <String, dynamic>{...r};
    for (final k in ['carpet_sqft', 'taps', 'cost']) {
      if (r[k] != null) body[k] = _n(r[k]);
    }
    await _do('PATCH', '/api/society/flats/${widget.id}', body);
  }

  Future<void> _receipt() async {
    final r = await _form(context, 'Money received', const [('amount', 'How many ₹'), ('mode', 'upi / cash / cheque / neft'), ('ref', 'UTR / cheque no'), ('day', 'Date (empty = today)')],
        ok: 'Make receipt', initial: {'amount': _s(_f?['due'])});
    if (r == null) return;
    await _do('POST', '/api/society/flats/${widget.id}/receipt', {...r, 'amount': _n(r['amount'])});
  }

  Future<void> _nominate() async {
    final r = await _form(context, 'Nomination (form signed by the member)', const [('name', 'Nominee'), ('relation', 'Relation'), ('share_pct', 'Share %')], ok: 'Save');
    if (r == null || (r['name'] ?? '').isEmpty) return;
    await _do('POST', '/api/society/flats/${widget.id}/nominate', {...r, 'share_pct': _n(r['share_pct'])});
  }

  Future<void> _parking() async {
    final r = await _form(context, 'Parking slot', const [('slot', 'Slot no'), ('kind', 'car / two_wheeler'), ('resolution', 'General body resolution')], ok: 'Assign');
    if (r == null || (r['slot'] ?? '').isEmpty) return;
    await _do('POST', '/api/society/flats/${widget.id}/parking', r);
  }

  Future<void> _transfer() async {
    final r = await _form(context, 'Flat transfer (new member)', const [('new_owner', 'New member'), ('phone', 'Mobile'), ('premium', 'Transfer premium ₹'), ('on', 'Date')],
        ok: 'Transfer');
    if (r == null || (r['new_owner'] ?? '').isEmpty) return;
    await _do('POST', '/api/society/flats/${widget.id}/transfer', {...r, 'premium': _n(r['premium'])});
  }

  @override
  Widget build(BuildContext context) {
    final f = _f;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('Flat ${_s(f?['unit'])}')),
      body: f == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(f['owner_name']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                  Text([_s(f['owner_phone']), if (f['carpet_sqft'] != null) '${f['carpet_sqft']} sq ft', _s(f['occupancy'])].where((x) => x.isNotEmpty).join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (f['occupancy'] == 'tenant') Text('Tenant: ${_s(f['tenant_name'])}', style: const TextStyle(fontSize: 12.5)),
                  Text('Due: ${_s(f['due_text']).isEmpty ? '₹0' : _s(f['due_text'])}${(f['advance'] ?? 0) > 0 ? ' · advance ₹${f['advance']}' : ''}',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  for (final x in _strs(f['missing'])) Text('• pending: $x', style: const TextStyle(color: C.warn, fontSize: 12)),
                ]),
              ),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                GradientButton(label: 'Money received', icon: Icons.currency_rupee_rounded, height: 42, onTap: _receipt),
                GlassButton(label: 'Edit', icon: Icons.edit_rounded, onTap: _edit),
                GlassButton(label: 'Nomination', icon: Icons.family_restroom_rounded, onTap: _nominate),
                GlassButton(label: 'Parking', icon: Icons.local_parking_rounded, onTap: _parking),
                GlassButton(label: 'Transfer', icon: Icons.swap_horiz_rounded, onTap: _transfer),
                if (f['occupancy'] == 'tenant' || _s(f['tenant_name']).isNotEmpty)
                  GlassButton(label: 'Forget tenant', icon: Icons.person_remove_rounded,
                      onTap: () => _do('POST', '/api/society/flats/${widget.id}/forget', {'who': 'tenant'})),
              ]),
              const SizedBox(height: 12),
              if (_list(f['nominations']).isNotEmpty) ...[
                const Caption('NOMINATION'),
                for (final n in _list(f['nominations']))
                  Text('• ${_s(n['name'])} (${_s(n['relation'])})${n['share_pct'] != null ? ' ${n['share_pct']}%' : ''}', style: const TextStyle(fontSize: 13)),
              ],
              const SizedBox(height: 8),
              const Caption('BILLS'),
              for (final b in _list(f['bills']))
                ListTile(
                  dense: true,
                  title: Text('${_s(b['number'])} · ${_s(b['period'])}'),
                  subtitle: Text('${_s(b['status'])} · due ${_s(b['due_date'])}'),
                  trailing: Text('₹${_s(b['total'])}${(b['paid'] ?? 0) > 0 ? ' (received ₹${b['paid']})' : ''}'),
                ),
              const Caption('RECEIPTS'),
              for (final r in _list(f['receipts']))
                ListTile(dense: true, title: Text('${_s(r['number'])} · ${_s(r['day'])}'), subtitle: Text(_s(r['mode'])), trailing: Text(_s(r['amount_text']))),
            ]),
    );
  }
}

/// One meeting: agenda, notice, attendance (quorum), resolutions, minutes draft -> pakke.
class SocietyMeetingPage extends StatefulWidget {
  const SocietyMeetingPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<SocietyMeetingPage> createState() => _SocietyMeetingPageState();
}

class _SocietyMeetingPageState extends State<SocietyMeetingPage> {
  Map<String, dynamic>? _m0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = _m(await widget.app.api!.call('GET', '/api/society/meetings/${widget.id}'));
      if (mounted) setState(() => _m0 = m);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(String method, String path, [Object? body]) async {
    await _call(context, widget.app, method, path, body);
    await _load();
  }

  Future<void> _notice() async {
    final m = _m0 ?? {};
    final r = await _call(context, widget.app, 'POST', '/api/society/notices', {'kind': m['kind'], 'meeting': widget.id});
    final n = _m(r?['notice']);
    if (n.isNotEmpty && mounted) await _do('POST', '/api/society/notices/${_s(n['id'])}/send');
  }

  Future<void> _held() async {
    final r = await _form(context, 'Meeting held', const [('present', 'Flats / names present (comma separated)'), ('chair', 'Chairman'), ('notes', 'Discussion notes')],
        ok: 'Minutes draft');
    if (r == null) return;
    final present = (r['present'] ?? '').split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList();
    await _do('POST', '/api/society/meetings/${widget.id}/held', {'present': present, 'chair': r['chair'] ?? '', 'notes': r['notes'] ?? ''});
  }

  Future<void> _resolution() async {
    final r = await _form(context, 'Resolution', const [('text', 'Proposed by'), ('proposer', 'Proposer'), ('seconder', 'Seconder'), ('for', 'In favour'), ('against', 'Opposed by')],
        ok: 'Add');
    if (r == null || (r['text'] ?? '').isEmpty) return;
    await _do('POST', '/api/society/meetings/${widget.id}/resolution', {...r, 'for': int.tryParse(r['for'] ?? '') ?? 0, 'against': int.tryParse(r['against'] ?? '') ?? 0});
  }

  Future<void> _final() async {
    final c = TextEditingController(text: _s(_m0?['minutes']));
    final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
              title: const Text('Confirm the minutes'),
              content: TextField(controller: c, maxLines: 14),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Confirmed')),
              ],
            ));
    if (ok == true) await _do('POST', '/api/society/meetings/${widget.id}/minutes', {'text': c.text});
  }

  @override
  Widget build(BuildContext context) {
    final m = _m0;
    final st = _s(m?['status']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${_s(m?['number'])} · ${_s(m?['kind']).toUpperCase()}')),
      body: m == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(m['day'])} ${_s(m['time'])} · ${_s(m['place'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text('Quorum ${_s(m['quorum'])} · present ${_s(m['present_count'])} · $st', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  const SizedBox(height: 6),
                  for (final (i, a) in _strs(m['agenda']).indexed) Text('${i + 1}. $a', style: const TextStyle(fontSize: 13)),
                ]),
              ),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (st == 'planned' && _s(m['notice_id']).isEmpty) GradientButton(label: 'Notice (for your approval)', icon: Icons.campaign_rounded, height: 42, onTap: _notice),
                if (st == 'planned' || st == 'held') GlassButton(label: 'Meeting held', icon: Icons.how_to_reg_rounded, onTap: _held),
                if (st == 'planned' || st == 'held') GlassButton(label: 'Resolution', icon: Icons.gavel_rounded, onTap: _resolution),
                if (st == 'held') GradientButton(label: 'Confirm the minutes', icon: Icons.task_alt_rounded, height: 42, onTap: _final),
              ]),
              const SizedBox(height: 12),
              if (_list(m['resolutions']).isNotEmpty) ...[
                const Caption('RESOLUTIONS'),
                for (final r in _list(m['resolutions']))
                  ListTile(
                      dense: true,
                      leading: Icon(r['passed'] == true ? Icons.check_circle_rounded : Icons.cancel_rounded, color: r['passed'] == true ? C.ok : C.bad),
                      title: Text('${_s(r['no'])}. ${_s(r['text'])}'),
                      subtitle: Text('For ${_s(r['for'])} · Against ${_s(r['against'])}')),
              ],
              if (_s(m['minutes']).isNotEmpty) ...[
                const Caption('MINUTES'),
                Glass(child: SelectableText(_s(m['minutes']), style: const TextStyle(fontSize: 13, height: 1.4))),
              ],
            ]),
    );
  }
}

/// society_card: anything waiting for HER tap (bills / notice / message / spend / penalty). Also in calls.
/// Approving a spend asks for her fingerprint once a phone key is set up (428 -> challenge -> sign -> resend).
class SocietyApprovalCard extends StatefulWidget {
  const SocietyApprovalCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SocietyApprovalCard> createState() => _SocietyApprovalCardState();
}

class _SocietyApprovalCardState extends State<SocietyApprovalCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  List<Map<String, dynamic>> _sendList = [];
  String _groupText = '';

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/society/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Society expense' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'No fingerprint given, so it was not approved.',
        'key_invalidated' => 'A new fingerprint was added to the phone: re-link this phone in Profile > Fingerprint approval.',
        _ => 'Could not approve with fingerprint (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes, {String via = ''}) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not', const [('reason', 'Reason (for you)')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason, 'via': via};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/society/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/society/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          _c = _m(m['card']).isEmpty ? _c : _m(m['card']);
          _sendList = [..._list(m['bills']), ..._list(m['messages'])];
          _groupText = _s(m['group_text']);
        });
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  List<Widget> _details(String kind, Map<String, dynamic> d) {
    final t = const TextStyle(fontSize: 12.5);
    switch (kind) {
      case 'bills':
        return [
          Text('${_s(d['count'])} bills · total ${_s(d['total_text'])} · due ${_s(d['due_date'])}', style: t),
          for (final b in _list(d['sample']))
            Text('${_s(b['unit'])}: ${_s(b['total_text'])} (${_list(b['lines']).map((l) => _s(l['label']).split(' (').first).join(', ')})',
                style: const TextStyle(fontSize: 12, color: C.muted)),
          if (d['upi'] != true) const Text('The society UPI ID was not given: the bill will have no pay link.', style: TextStyle(fontSize: 12, color: C.warn)),
          for (final p in [..._strs(d['problems']).take(6), ..._strs(d['warnings'])]) Text('⚠ $p', style: const TextStyle(fontSize: 12, color: C.warn)),
        ];
      case 'notice':
        return [
          Text(_s(d['kind_label']), style: t),
          Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
            child: Text(_s(d['body']), style: const TextStyle(fontSize: 12.5, height: 1.35), maxLines: 18, overflow: TextOverflow.ellipsis),
          ),
          for (final p in _strs(d['checks'])) Text('⚠ $p', style: const TextStyle(fontSize: 12, color: C.warn)),
        ];
      case 'message':
        return [
          Text('${_s(d['count'])} members · ${d['via'] == 'business' ? 'business WhatsApp' : 'you will send it yourself'}', style: t),
          for (final p in _list(d['preview']))
            Text('${_s(p['unit'])}: ${_s(p['text'])}', style: const TextStyle(fontSize: 12, color: C.muted), maxLines: 4, overflow: TextOverflow.ellipsis),
          for (final p in _strs(d['skipped'])) Text('Left out: $p', style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ];
      case 'spend':
        return [
          Text('${_s(d['kind_label'])} · ${_s(d['amount_text'])} · ${_s(d['fund_label'])}', style: t),
          Text(_s(d['what']), style: t),
          if (_s(d['vendor']).isNotEmpty) Text('To whom: ${_s(d['vendor'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          if (_s(d['resolution']).isNotEmpty) Text('Resolution: ${_s(d['resolution'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
          for (final p in _strs(d['checks'])) Text('⚠ $p', style: const TextStyle(fontSize: 12, color: C.warn)),
          const Text('Hoola does not pay money itself; you / the treasurer pay from the society account.', style: TextStyle(fontSize: 11, color: C.faint)),
        ];
      case 'penalty':
        return [
          Text('${_s(d['unit'])} · ${_s(d['amount_text'])}', style: t),
          Text(_s(d['what']), style: t),
          Text('Rule: ${_s(d['rule'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        ];
    }
    return [];
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final st = _s(c['status']);
    final kind = _s(c['kind']);
    final d = _m(c['data']);
    final canBusiness = kind == 'bills' || kind == 'message';
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'bills' => Icons.receipt_long_rounded,
            'notice' => Icons.campaign_rounded,
            'message' => Icons.chat_rounded,
            'spend' => Icons.payments_rounded,
            _ => Icons.gavel_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(c['title']), style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'stale', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'approved' ? C.ok : C.bad)),
        ]),
        ..._details(kind, d),
        const SizedBox(height: 8),
        if (st == 'waiting') ...[
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: canBusiness ? 'Yes, make the drafts' : 'Yes', height: 42, onTap: _busy ? null : () => _decide(true, via: 'self'))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
          if (canBusiness) ...[
            const SizedBox(height: 6),
            GlassButton(
                label: 'Yes, from business WhatsApp',
                icon: Icons.send_rounded,
                onTap: _busy ? null : () => _decide(true, via: 'business')),
          ],
        ],
        if (_sendList.isNotEmpty) ...[
          const SizedBox(height: 8),
          const Text('You send to each member:', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
          for (final x in _sendList)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('${_s(x['unit'])} · ${_s(x['owner'])}'),
              trailing: x['sent'] == true
                  ? const Icon(Icons.done_all_rounded, color: C.ok)
                  : (_s(x['wa']).isEmpty
                      ? const Text('no phone', style: TextStyle(fontSize: 11, color: C.faint))
                      : TextButton(child: const Text('WhatsApp'), onPressed: () => Native.openExternal(url: _s(x['wa'])))),
            ),
        ],
        if (_groupText.isNotEmpty)
          GlassButton(
              label: 'Copy text for the group',
              icon: Icons.copy_rounded,
              onTap: () {
                Clipboard.setData(ClipboardData(text: _groupText));
                _snack(context, 'Copied: paste it in the society group / notice board.');
              }),
      ]),
    );
  }
}

/// society_complaint: one complaint / request, updated in place. Also in calls.
class SocietyComplaintCard extends StatelessWidget {
  const SocietyComplaintCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final c = _m(data['complaint']);
    return Glass(
      padding: const EdgeInsets.all(12),
      border: c['urgent'] == true ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(c['urgent'] == true ? Icons.warning_rounded : Icons.report_problem_rounded, color: c['urgent'] == true ? C.bad : C.warn, size: 20),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(c['number'])} · ${_s(c['category'])}${_s(c['unit']).isEmpty ? '' : ' · ${_s(c['unit'])}'}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(c['status_label'])),
        ]),
        Text(_s(c['text']), style: const TextStyle(fontSize: 13)),
        Text([if (_s(c['vendor']).isNotEmpty) 'Vendor: ${_s(c['vendor'])}', '${_s(c['age_days'])} days old'].join(' · '),
            style: const TextStyle(fontSize: 11.5, color: C.faint)),
      ]),
    );
  }
}

/// society_alert: a date coming / passed (AGM, audit, election, AMC, police verification) or an urgent complaint.
class SocietyAlertCard extends StatelessWidget {
  const SocietyAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        padding: const EdgeInsets.all(12),
        border: data['kind'] == 'complaint' ? C.bad : C.warn,
        child: Row(children: [
          Icon(data['kind'] == 'complaint' ? Icons.warning_rounded : Icons.event_rounded, color: data['kind'] == 'complaint' ? C.bad : C.warn),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
          IconButton(
              icon: const Icon(Icons.open_in_new_rounded),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SocietyScreen(app: app)))),
        ]),
      );
}

/// society_day: the morning note.
class SocietyDayCard extends StatelessWidget {
  const SocietyDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.apartment_rounded, color: C.accent),
            SizedBox(width: 8),
            Text('Today in the society', style: TextStyle(fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
          const SizedBox(height: 8),
          GlassButton(
              label: 'Open society',
              icon: Icons.open_in_new_rounded,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SocietyScreen(app: app)))),
        ]),
      );
}
