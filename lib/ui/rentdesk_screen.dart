/// Profile > Rentdesk Sahayak: Hoola as the property manager.
/// Aaj (dues, cards and drafts waiting for her, renewals, registration / police pending) · Units · Kirayedar (tenancies with
/// ledger, receipts, agreement draft, checklist, notice, inspection, deposit settlement) · Haan (her cards + message drafts) ·
/// Repair (requests, vendors) · Niyam (landlord details, PAN to the locker, UPI, reminders). Every message to a tenant, every
/// deposit deduction, rent change / notice and repair spend runs only after HER tap (fingerprint for money once a phone key is
/// set up). Hoola never takes or pays money.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

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
    {String ok = 'Aage', Map<String, String> initial = const {}}) async {
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
                maxLines: (k == 'text' || k == 'address' || k == 'reason' || k == 'rules') ? 3 : 1),
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

Widget _line(String label, String value, {Color? color}) => value.isEmpty
    ? const SizedBox.shrink()
    : Padding(
        padding: const EdgeInsets.only(bottom: 2),
        child: Text('$label: $value', style: TextStyle(fontSize: 12.5, color: color ?? C.muted)),
      );

class RentdeskScreen extends StatefulWidget {
  const RentdeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<RentdeskScreen> createState() => _RentdeskScreenState();
}

class _RentdeskScreenState extends State<RentdeskScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/rentdesk'));
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

  void _openTenancy(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => RentdeskTenancyPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _addUnit() async {
    final f = await _form(context, 'Naya unit', const [
      ('label', 'Naam (Flat 302 / Shop 4 / Bed B2)'),
      ('building', 'Building / society'),
      ('kind', 'flat / house / room / pg_bed / shop / office / godown'),
      ('address', 'Pata'),
      ('pin', 'PIN code'),
      ('area_sqft', 'Area sq ft (aapka number)'),
      ('rent_ask', 'Kiraya (aapka)'),
      ('deposit_ask', 'Deposit (aapka)'),
      ('inventory', 'Saamaan: "2 fan, 1 geyser"'),
    ], ok: 'Jodo');
    if (f == null || (f['label'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    for (final k in ['area_sqft', 'rent_ask', 'deposit_ask']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _run('POST', '/api/rentdesk/units', body);
  }

  Future<void> _newTenancy() async {
    final f = await _form(context, 'Naya kirayedar', const [
      ('unit', 'Unit (U-001 / naam)'),
      ('name', 'Kirayedar ka naam'),
      ('phone', 'Mobile'),
      ('aadhaar', 'Aadhaar (Pehchaan Locker mein jayega, ho to)'),
      ('start', 'Shuru (DD-MM-YYYY)'),
      ('months', 'Kitne mahine (11)'),
      ('rent', 'Kiraya / licence fee mahina'),
      ('deposit', 'Deposit'),
      ('due_day', 'Kis taarikh ko (1-28, khaali = shuru wala din)'),
      ('escalation_pct', 'Har saal badhotri % (agreement)'),
      ('notice_months', 'Notice kitne mahine (1)'),
    ], ok: 'Draft banao');
    if (f == null || (f['unit'] ?? '').isEmpty || (f['name'] ?? '').isEmpty) return;
    setState(() => _busy = true);
    final p = await _call(context, widget.app, 'POST', '/api/rentdesk/people',
        {'name': f['name'], 'phone': f['phone'] ?? '', 'aadhaar': f['aadhaar'] ?? ''});
    final pid = _s(_m(p?['person'])['id']);
    if (pid.isNotEmpty) {
      final body = <String, dynamic>{'unit': f['unit'], 'person': pid, 'start': f['start'] ?? ''};
      for (final k in ['months', 'rent', 'deposit', 'due_day', 'escalation_pct', 'notice_months']) {
        if (f[k] != null) body[k] = _n(f[k]);
      }
      if (f['escalation_pct'] != null) body['escalation_every'] = 12;
      final r = await _call(context, widget.app, 'POST', '/api/rentdesk/tenancies', body);
      final t = _m(r?['tenancy']);
      await _load();
      if (mounted) setState(() => _busy = false);
      if (t['id'] != null && mounted) _openTenancy(_s(t['id']));
      return;
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _newRepair() async {
    final f = await _form(context, 'Repair', const [('unit', 'Unit (U-001 / naam)'), ('text', 'Kya kharab hai')], ok: 'Darj karo');
    if (f == null || (f['unit'] ?? '').isEmpty) return;
    await _run('POST', '/api/rentdesk/requests', f);
  }

  Future<void> _addVendor() async {
    final f = await _form(context, 'Vendor', const [
      ('name', 'Naam'),
      ('phone', 'Mobile'),
      ('trade', 'plumber / electrician / carpenter / painter / appliance / pest / civil / other'),
    ], ok: 'Jodo');
    if (f == null) return;
    await _run('POST', '/api/rentdesk/vendors', f);
  }

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Niyam', const [
      ('landlord_name', 'Aapka naam (receipt par)'),
      ('landlord_address', 'Aapka pata'),
      ('state', 'Rajya code (MH, KA, DL...)'),
      ('city', 'Shehar'),
      ('upi_id', 'UPI ID (khaali = Employee wala)'),
      ('pan', 'PAN (Pehchaan Locker mein jayega)'),
      ('gstin', 'GSTIN (ho to)'),
      ('remind_before', 'Due se kitne din pehle reminder draft'),
      ('grace_days', 'Due ke kitne din baad late draft'),
      ('minor_repair_limit', 'Chhote repair kirayedar ka (Rs tak)'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('rules', 'Aapke niyam'),
    ], initial: {
      for (final k in ['landlord_name', 'landlord_address', 'state', 'city', 'upi_id', 'gstin', 'remind_before', 'grace_days', 'morning_time', 'rules'])
        k: _s(st[k]),
      'minor_repair_limit': _s(st['minor_repair_limit']),
    }, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['remind_before', 'grace_days', 'minor_repair_limit']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _run('PUT', '/api/rentdesk/settings', body);
  }

  Widget _today() {
    final d = _m(_d?['day']);
    final aps = _list(_d?['approvals']);
    final msgs = _list(_d?['messages']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
      const SizedBox(height: 10),
      if (aps.isNotEmpty) const Caption('AAPKI HAAN CHAHIYE'),
      for (final a in aps)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: RentdeskApprovalCard(app: widget.app, data: {'approval': a}, onDone: _load)),
      if (_list(d['overdue']).isNotEmpty) const Caption('BAAKI KIRAYA'),
      for (final o in _list(d['overdue']))
        Glass(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          child: Text('${_s(o['tenancy'])} ${_s(o['who'])} · ${_s(o['what'])} · ₹${_s(o['left'])} · ${_s(o['days'])} din',
              style: const TextStyle(fontSize: 13, color: C.warn)),
        ),
      if (msgs.isNotEmpty) const Caption('MESSAGE DRAFT (AAPKE TAP SE JAYENGE)'),
      for (final m in msgs.take(10))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: RentdeskMessageCard(app: widget.app, data: {'message': m}, onDone: _load)),
      for (final r in _list(d['renewals']))
        Text('Renewal: ${_s(r['tenancy'])} ${_s(r['who'])} · ${_s(r['end'])} (${_s(r['days_left'])} din)',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
      for (final p in _list(d['pending']))
        Text('Baaki: ${_s(p['tenancy'])} ${_s(p['who'])} · ${_strs(p['missing']).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
    ]);
  }

  Widget _unitsTab() => ListView(padding: const EdgeInsets.all(14), children: [
        GradientButton(label: 'Naya unit', icon: Icons.add_home_rounded, height: 46, onTap: _busy ? null : _addUnit),
        const SizedBox(height: 10),
        for (final u in _list(_d?['units']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              const Icon(Icons.apartment_rounded, color: C.accent),
              const SizedBox(width: 8),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(u['number'])} · ${_s(u['label'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text([_s(u['building']), _s(u['kind_label']), _s(u['tenant_name'])].where((x) => x.isNotEmpty).join(' · '),
                      style: const TextStyle(fontSize: 12.5, color: C.muted)),
                ]),
              ),
              Pill(_s(u['status']) == 'vacant' ? 'khali' : (_s(u['status']) == 'notice' ? 'notice' : 'kiraye par'),
                  fg: _s(u['status']) == 'vacant' ? C.warn : C.ok),
            ]),
          ),
      ]);

  Widget _tenanciesTab() => ListView(padding: const EdgeInsets.all(14), children: [
        GradientButton(label: 'Naya kirayedar', icon: Icons.person_add_alt_1_rounded, height: 46, onTap: _busy ? null : _newTenancy),
        const SizedBox(height: 10),
        for (final t in _list(_d?['tenancies']))
          Press(
            onTap: () => _openTenancy(_s(t['id'])),
            child: Glass(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(12),
              border: (t['due_now'] is num && (t['due_now'] as num) > 0) ? C.warn : null,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                      child: Text('${_s(t['number'])} · ${_s(t['tenant_name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                  Pill(_s(t['status_label'])),
                ]),
                Text('${_s(t['unit_label'])} · ${_s(t['rent_text'])}/mahina · ${_s(t['start'])} se ${_s(t['end'])}',
                    style: const TextStyle(fontSize: 12.5, color: C.muted)),
                if (_s(t['due_now_text']).isNotEmpty && t['due_now'] != 0)
                  Text('Baaki ${_s(t['due_now_text'])}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
              ]),
            ),
          ),
      ]);

  Widget _haanTab() => ListView(padding: const EdgeInsets.all(14), children: [
        const Caption('CARDS'),
        for (final a in _list(_d?['approvals']))
          Padding(padding: const EdgeInsets.only(bottom: 8), child: RentdeskApprovalCard(app: widget.app, data: {'approval': a}, onDone: _load)),
        if (_list(_d?['approvals']).isEmpty) const Text('Koi card baaki nahi.', style: TextStyle(color: C.faint)),
        const SizedBox(height: 10),
        const Caption('MESSAGE DRAFT'),
        for (final m in _list(_d?['messages']))
          Padding(padding: const EdgeInsets.only(bottom: 8), child: RentdeskMessageCard(app: widget.app, data: {'message': m}, onDone: _load)),
      ]);

  Widget _repairTab() => ListView(padding: const EdgeInsets.all(14), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'Repair darj', icon: Icons.build_rounded, height: 44, onTap: _busy ? null : _newRepair)),
          const SizedBox(width: 8),
          GlassButton(label: 'Vendor', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _addVendor),
        ]),
        const SizedBox(height: 10),
        for (final r in _list(_d?['requests'])) Padding(padding: const EdgeInsets.only(bottom: 8), child: _RepairTile(app: widget.app, r: r, onDone: _load)),
        const Caption('VENDOR'),
        for (final v in _list(_d?['vendors']))
          Text('${_s(v['name'])} · ${_s(v['trade_label'])} · ${_s(v['phone'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      ]);

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _line('Naam', _s(st['landlord_name'])),
          _line('Rajya', _s(st['state_label'])),
          _line('UPI', _s(st['upi_used'])),
          _line('PAN', _s(st['pan'])),
          _line('Reminder', '${_s(st['remind_before'])} din pehle, ${_s(st['grace_days'])} din baad'),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.tune_rounded, onTap: _busy ? null : _settings),
        ]),
      ),
      const SizedBox(height: 10),
      const Caption('HOOLA KABHI NAHI'),
      for (final n in _strs(_d?['never'])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 10),
      GlassButton(label: 'Register (Excel)', icon: Icons.table_chart_rounded, onTap: _busy ? null : () => _run('POST', '/api/rentdesk/register')),
      const SizedBox(height: 8),
      GlassButton(label: 'IGR Maharashtra kholo', icon: Icons.open_in_new_rounded, onTap: () => Native.openExternal(url: 'https://igrmaharashtra.gov.in')),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Units', 'Kirayedar', 'Haan', 'Repair', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Property manager'),
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
                    0 => _today(),
                    1 => _unitsTab(),
                    2 => _tenanciesTab(),
                    3 => _haanTab(),
                    4 => _repairTab(),
                    _ => _rulesTab(),
                  },
                ),
        ),
      ]),
    );
  }
}

class _RepairTile extends StatelessWidget {
  const _RepairTile({required this.app, required this.r, required this.onDone});
  final Santosh app;
  final Map<String, dynamic> r;
  final VoidCallback onDone;

  Future<void> _assign(BuildContext context) async {
    final f = await _form(context, 'Vendor + quote', const [
      ('vendor', 'Vendor ka naam / mobile'),
      ('quote', 'Unka quote (Rs)'),
      ('who_pays', 'Kaun dega: owner / tenant'),
    ]);
    if (f == null) return;
    await _call(context, app, 'POST', '/api/rentdesk/requests/${_s(r['id'])}/assign',
        {'vendor': f['vendor'] ?? '', 'quote': _n(f['quote']), 'who_pays': f['who_pays'] ?? ''});
    onDone();
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(r['status']);
    final v = _m(r['vendor']);
    return Glass(
      padding: const EdgeInsets.all(12),
      border: r['urgent'] == true ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${_s(r['number'])} · ${_s(r['unit_label'])} · ${_s(r['category_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st, fg: st == 'done' ? C.ok : C.warn),
        ]),
        Text(_s(r['text']), style: const TextStyle(fontSize: 13)),
        _line('Vendor', _s(v['name'])),
        _line('Quote', _s(r['quote_text'])),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (st == 'open' || st == 'assigned') GlassButton(label: 'Vendor / quote', height: 38, onTap: () => _assign(context)),
          if (_s(r['vendor_wa']).isNotEmpty)
            GlassButton(label: 'Vendor ko WhatsApp', height: 38, icon: Icons.chat_rounded, onTap: () => Native.openExternal(url: _s(r['vendor_wa']))),
          if (st == 'approved' || ((r['quote'] == null) && st != 'done'))
            GlassButton(label: 'Kaam ho gaya', height: 38, icon: Icons.check_rounded, onTap: () async {
              await _call(context, app, 'POST', '/api/rentdesk/requests/${_s(r['id'])}/done', {});
              onDone();
            }),
        ]),
      ]),
    );
  }
}

class RentdeskTenancyPage extends StatefulWidget {
  const RentdeskTenancyPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<RentdeskTenancyPage> createState() => _RentdeskTenancyPageState();
}

class _RentdeskTenancyPageState extends State<RentdeskTenancyPage> {
  Map<String, dynamic>? _t;
  Map<String, dynamic>? _insp;
  Map<String, dynamic>? _settle;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = _m(await widget.app.api!.call('GET', '/api/rentdesk/tenancies/${widget.id}'));
      if (mounted) setState(() => _t = t);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  String get _tid => _s(_t?['id']).isEmpty ? widget.id : _s(_t?['id']);

  Future<Map<String, dynamic>?> _post(String sub, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/rentdesk/tenancies/$_tid/$sub', body ?? {});
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Future<void> _receive() async {
    final f = await _form(context, 'Paisa mila', const [
      ('amount', 'Kitna mila'),
      ('mode', 'upi / bank / cash / cheque'),
      ('ref', 'UTR / cheque no (aakhri ank)'),
      ('on', 'Kab (DD-MM-YYYY, khaali = aaj)'),
    ], initial: {'amount': _s(_t?['due_now']), 'mode': 'upi'}, ok: 'Darj karo');
    if (f == null) return;
    await _post('receive', {'amount': _n(f['amount']), 'mode': f['mode'] ?? 'upi', 'ref': f['ref'] ?? '', 'on': f['on'] ?? ''});
  }

  Future<void> _rentChange() async {
    final f = await _form(context, 'Kiraya badlav', const [('new_rent', 'Naya kiraya'), ('from', 'Kab se (DD-MM-YYYY)'), ('why', 'Kyon')]);
    if (f == null) return;
    await _post('rent_change', {'new_rent': _n(f['new_rent']), 'from': f['from'] ?? '', 'why': f['why'] ?? ''});
  }

  Future<void> _notice(String kind) async {
    final f = kind == 'vacate'
        ? await _form(context, 'Khali karne ka notice', const [('vacate_on', 'Kab tak (DD-MM-YYYY)'), ('reason', 'Wajah (chitthi mein)')])
        : await _form(context, 'Renewal', const [('new_rent', 'Naya kiraya (ho to)'), ('from', 'Kab se')]);
    if (f == null) return;
    await _post('notice', {'kind': kind, 'vacate_on': f['vacate_on'] ?? '', 'reason': f['reason'] ?? '', 'new_rent': _n(f['new_rent']),
      'from': f['from'] ?? ''});
  }

  Future<void> _check(Map<String, dynamic> it) async {
    String ref = '';
    if (_s(it['id']) == 'registration' || _s(it['id']) == 'police') {
      final f = await _form(context, _s(it['what']).split(' (').first, const [('ref', 'Document / reference no'), ('on', 'Taarikh')]);
      if (f == null) return;
      ref = f['ref'] ?? '';
    }
    await _post('check', {'item': it['id'], 'done': _s(it['done']).isEmpty, 'ref': ref});
  }

  Future<void> _inspection(String kind) async {
    final r = await _post('inspection', {'kind': kind});
    if (r != null && mounted) setState(() => _insp = _m(r['inspection']));
  }

  Future<void> _setCond(Map<String, dynamic> it, String c) async {
    final id = _s(_insp?['id']);
    final r = await _call(context, widget.app, 'PATCH', '/api/rentdesk/inspections/$id', {
      'items': [
        {'key': it['key'], 'condition': c}
      ]
    });
    if (r != null && mounted) setState(() => _insp = _m(r['inspection']));
  }

  Future<void> _photo(Map<String, dynamic> it) async {
    final files = await pickAttachmentsOfType(context, FileType.image);
    if (files.isEmpty) return;
    try {
      final r = await widget.app.api!.uploadFile('/api/rentdesk/photos', files.first.name, files.first.bytes,
          fields: {'owner_kind': 'inspection', 'owner_id': _s(_insp?['id']), 'item': _s(it['key'])});
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _closeInspection() async {
    final f = await _form(context, 'Meter / chaabi', const [('electricity', 'Bijli meter'), ('water', 'Paani meter'), ('keys', 'Chaabiyan')]);
    final r = await _call(context, widget.app, 'PATCH', '/api/rentdesk/inspections/${_s(_insp?['id'])}', {
      'meters': {if (f?['electricity'] != null) 'electricity': _n(f?['electricity']), if (f?['water'] != null) 'water': _n(f?['water'])},
      'keys': _n(f?['keys']),
      'close': true,
    });
    if (r != null && mounted) setState(() => _insp = null);
    await _load();
  }

  Future<void> _settlement() async {
    final r = await _post('settlement');
    if (r != null && mounted) setState(() => _settle = _m(r['settlement']));
  }

  Future<void> _deduct() async {
    final f = await _form(context, 'Katauti', const [('what', 'Kis cheez ki'), ('amount', 'Rakam (aapka number / bill)'), ('reason', 'Wajah')]);
    if (f == null) return;
    final r = await _call(context, widget.app, 'POST', '/api/rentdesk/settlements/${_s(_settle?['id'])}/line',
        {'what': f['what'] ?? '', 'amount': _n(f['amount']), 'reason': f['reason'] ?? ''});
    if (r != null && mounted) setState(() => _settle = _m(r['settlement']));
  }

  Future<void> _settleRequest() async {
    final r = await _call(context, widget.app, 'POST', '/api/rentdesk/settlements/${_s(_settle?['id'])}/request');
    if (r != null && r['approval'] != null && mounted) {
      await showModalBottomSheet(
          context: context,
          backgroundColor: C.bgBottom,
          builder: (_) => Padding(
              padding: const EdgeInsets.all(16),
              child: RentdeskApprovalCard(app: widget.app, data: {'approval': r['approval']}, onDone: _load)));
    }
    await _load();
  }

  Future<void> _refundPaid() async {
    final f = await _form(context, 'Maine deposit wapas de diya', const [('amount', 'Kitna diya'), ('ref', 'UTR (aakhri ank)')],
        initial: {'amount': _s(_settle?['refund'])});
    if (f == null) return;
    final r = await _call(context, widget.app, 'POST', '/api/rentdesk/settlements/${_s(_settle?['id'])}/paid',
        {'amount': _n(f['amount']), 'ref': f['ref'] ?? ''});
    if (r != null && mounted) setState(() => _settle = _m(r['settlement']));
    await _load();
  }

  Widget _inspectionPanel() {
    final x = _insp!;
    const conds = ['good', 'fair', 'damaged', 'missing'];
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_s(x['kind']) == 'move_out' ? 'Move-out' : 'Move-in'} inspection', style: const TextStyle(fontWeight: FontWeight.w800)),
        for (final it in _list(x['items']))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(it['room'])} · ${_s(it['item'])}', style: const TextStyle(fontSize: 13))),
                IconButton(icon: const Icon(Icons.photo_camera_rounded, size: 20), onPressed: () => _photo(it)),
              ]),
              Wrap(spacing: 6, children: [
                for (final c in conds)
                  ChoiceChip(
                      label: Text(c, style: const TextStyle(fontSize: 11.5)),
                      selected: _s(it['condition']) == c,
                      onSelected: (_) => _setCond(it, c)),
              ]),
            ]),
          ),
        const SizedBox(height: 8),
        GradientButton(label: 'Inspection band karo', height: 42, onTap: _busy ? null : _closeInspection),
        const Text('Photo se location / camera ki jaankari hata di jaati hai.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }

  Widget _settlementPanel() {
    final x = _settle!;
    final st = _s(x['status']);
    return Glass(
      border: C.accent,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Deposit hisaab', style: TextStyle(fontWeight: FontWeight.w800)),
        _line('Deposit paas', _s(x['held_text'])),
        _line('Baaki kiraya / bill', _s(x['dues_text'])),
        for (final l in _list(x['lines'])) _line('Katauti ${_s(l['what'])}', '₹${_s(l['amount'])} ${_s(l['reason'])}', color: C.warn),
        _line(x['tenant_owes'] == true ? 'Kirayedar ko dena' : 'Wapas dena', _s(x['refund_text']), color: C.ink),
        for (final g in _list(x['suggest']))
          Text('• ${_s(g['room'])} ${_s(g['item'])}: ${_s(g['was'])} -> ${_s(g['now'])} (rakam aap likhiye)',
              style: const TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (st == 'draft' || st == 'waiting') GlassButton(label: 'Katauti jodo', height: 40, onTap: _busy ? null : _deduct),
          if (st == 'draft' || st == 'waiting') GradientButton(label: 'Haan ke liye card', height: 40, onTap: _busy ? null : _settleRequest),
          if (st == 'approved') GradientButton(label: 'Maine de diya', height: 40, onTap: _busy ? null : _refundPaid),
          GlassButton(
              label: 'PDF',
              height: 40,
              onTap: () => _call(context, widget.app, 'POST', '/api/rentdesk/settlements/${_s(x['id'])}/file')),
        ]),
        const Text('Aam ghisaav deposit se nahi katta. Paise aap khud bhejti hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(t == null ? 'Tenancy' : '${_s(t['number'])} · ${_s(t['tenant_name'])}')),
      body: t == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(14), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(t['unit_label'])} · ${_s(t['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    _line('Status', _s(t['status_label'])),
                    _line('Samay', '${_s(t['start'])} se ${_s(t['end'])} (${_s(t['months'])} mahine)'),
                    _line('Kiraya', '${_s(t['rent_text'])}/mahina'),
                    _line('Deposit', '${_s(t['deposit_text'])} (paas: ₹${_s(t['deposit_held'])})'),
                    _line('Abhi baaki', _s(t['due_now_text']), color: C.warn),
                    _line('Lock-in tak', _s(t['lock_in_until'])),
                    _line('Badhotri', _strs(t['escalations']).join(', ')),
                  ]),
                ),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (_s(t['status']) == 'draft') GradientButton(label: 'Chalu karo', height: 42, onTap: _busy ? null : () => _post('activate')),
                  GlassButton(label: 'Agreement draft', icon: Icons.description_rounded, height: 42, onTap: _busy ? null : () => _post('agreement')),
                  if (_s(t['status']) != 'draft') ...[
                    GradientButton(label: 'Paisa mila', height: 42, onTap: _busy ? null : _receive),
                    GlassButton(label: 'Kiraya badlav', height: 42, onTap: _busy ? null : _rentChange),
                    GlassButton(label: 'Renewal', height: 42, onTap: _busy ? null : () => _notice('renewal')),
                    GlassButton(label: 'Notice', height: 42, onTap: _busy ? null : () => _notice('vacate')),
                    GlassButton(label: 'Move-in', height: 42, onTap: _busy ? null : () => _inspection('move_in')),
                    GlassButton(label: 'Move-out', height: 42, onTap: _busy ? null : () => _inspection('move_out')),
                    GlassButton(label: 'Deposit hisaab', height: 42, onTap: _busy ? null : _settlement),
                    GlassButton(
                        label: 'UPI link',
                        height: 42,
                        onTap: () async {
                          final r = await _call(context, widget.app, 'GET', '/api/rentdesk/tenancies/$_tid/pay_link');
                          final url = _s(r?['url']);
                          if (url.isNotEmpty) {
                            await _call(context, widget.app, 'POST', '/api/rentdesk/tenancies/$_tid/message',
                                {'kind': 'custom', 'text': 'Kiraya ₹${_s(r?['amount'])} is UPI ID par: ${_s(r?['upi_id'])}'});
                          }
                        }),
                  ],
                ]),
                if (_insp != null) ...[const SizedBox(height: 10), _inspectionPanel()],
                if (_settle != null) ...[const SizedBox(height: 10), _settlementPanel()],
                const SizedBox(height: 10),
                const Caption('CHECKLIST'),
                for (final it in _list(t['checklist']))
                  CheckboxListTile(
                    dense: true,
                    value: _s(it['done']).isNotEmpty,
                    onChanged: _busy ? null : (_) => _check(it),
                    title: Text(_s(it['what']), style: const TextStyle(fontSize: 12.5)),
                    subtitle: _s(it['done']).isEmpty ? null : Text(_s(it['done']), style: const TextStyle(fontSize: 11)),
                  ),
                const Caption('KANOON / TAX (CA / VAKIL SE PAKKA)'),
                for (final n in _strs(t['notes'])) Text('• $n', style: const TextStyle(fontSize: 12, color: C.muted)),
                const SizedBox(height: 10),
                const Caption('HISAAB'),
                for (final c in _list(t['charges']))
                  _line('${_s(c['kind_label'])} ${_s(c['period'])} (${_s(c['due_on'])})', '${_s(c['amount_text'])} · ${_s(c['status'])}',
                      color: _s(c['status']) == 'paid' ? C.ok : C.warn),
                const SizedBox(height: 8),
                const Caption('RECEIPT'),
                for (final p in _list(t['payments']))
                  Row(children: [
                    Expanded(child: Text('${_s(p['receipt_no'])} · ${_s(p['amount_text'])} · ${_s(p['on'])} · ${_s(p['mode'])}', style: const TextStyle(fontSize: 12.5))),
                    if (_s(p['receipt_no']).isNotEmpty)
                      IconButton(
                          icon: const Icon(Icons.picture_as_pdf_rounded, size: 20),
                          onPressed: () => _call(context, widget.app, 'POST', '/api/rentdesk/payments/${_s(p['id'])}/receipt')),
                  ]),
              ]),
            ),
    );
  }
}

/// rentdesk_approval: deposit deduction / rent change / notice / repair spend. Only her tap decides; money = fingerprint.
class RentdeskApprovalCard extends StatefulWidget {
  const RentdeskApprovalCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<RentdeskApprovalCard> createState() => _RentdeskApprovalCardState();
}

class _RentdeskApprovalCardState extends State<RentdeskApprovalCard> {
  bool _busy = false;
  late Map<String, dynamic> _a = _m(widget.data['approval']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/rentdesk/approvals/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Aapki haan' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'Fingerprint nahi diya, isliye haan nahi hui.',
        'key_invalidated' => 'Phone mein naya fingerprint juda hai: Profile > Fingerprint se haan mein phone phir se jodiye.',
        _ => 'Fingerprint se haan nahi ho payi (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_a['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyon nahi', const [('reason', 'Wajah (aapke liye)')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_a['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/rentdesk/approvals/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/rentdesk/approvals/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() => _a = _m(m['approval']).isEmpty ? _a : _m(m['approval']));
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final a = _a;
    final show = _m(a['show']);
    final st = _s(a['status']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(a['money'] == true ? Icons.payments_rounded : Icons.gavel_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(a['number'])} · ${_s(a['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'maana', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' || st == 'stale' ? C.bad : C.ok)),
        ]),
        Text(_s(show['title']), style: const TextStyle(fontSize: 13)),
        for (final l in _list(show['lines'])) _line('Katauti ${_s(l['what'])}', '₹${_s(l['amount'])} ${_s(l['reason'])}'),
        if (show['refund'] != null) _line('Wapas', '₹${_s(show['refund'])}'),
        for (final c in _strs(show['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        const Text('Hoola paise nahi leta / deta; message bhi aapke tap se hi jaata hai.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// rentdesk_message: a DRAFT for the tenant. Sent only from her tap (own WhatsApp / SMS, or the business number).
class RentdeskMessageCard extends StatefulWidget {
  const RentdeskMessageCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<RentdeskMessageCard> createState() => _RentdeskMessageCardState();
}

class _RentdeskMessageCardState extends State<RentdeskMessageCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['message']);

  Future<void> _send(String via) async {
    setState(() => _busy = true);
    try {
      if (via == 'self') {
        final link = _s(_x['wa']).isNotEmpty ? _s(_x['wa']) : _s(_x['sms']);
        if (link.isEmpty) throw Exception('Kirayedar ka mobile nahi.');
        await Native.openExternal(url: link);
      }
      final m = _m(await widget.app.api!.call('POST', '/api/rentdesk/messages/${_s(_x['id'])}/send', body: {'via': via, 'hash': _s(_x['hash'])}));
      if (mounted) {
        setState(() => _x = _m(m['message']).isEmpty ? _x : _m(m['message']));
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _edit() async {
    final f = await _form(context, 'Message badlo', const [('text', 'Message')], initial: {'text': _s(_x['text'])}, ok: 'Save');
    if (f == null) return;
    try {
      final m = _m(await widget.app.api!.call('PUT', '/api/rentdesk/messages/${_s(_x['id'])}', body: {'text': f['text'] ?? ''}));
      if (mounted) setState(() => _x = _m(m['message']).isEmpty ? _x : _m(m['message']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final x = _x;
    final st = _s(x['status']);
    return Glass(
      border: st == 'draft' ? C.violet : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.sms_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['to'])} ko · ${_s(x['kind'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st == 'draft' ? 'draft' : (st == 'sent' ? 'bheja' : st), fg: st == 'sent' ? C.ok : C.chip),
        ]),
        Text(_s(x['text']), style: const TextStyle(fontSize: 13)),
        if (x['no_messages'] == true) const Text('⚠ Inhone message mana kiya hai.', style: TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'draft')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: 'Apne WhatsApp se', icon: Icons.send_rounded, height: 40, onTap: _busy ? null : () => _send('self')),
            GlassButton(label: 'Business number se', height: 40, onTap: _busy ? null : () => _send('business')),
            GlassButton(label: 'Badlo', height: 40, onTap: _busy ? null : _edit),
            GlassButton(
                label: 'Hatao',
                height: 40,
                onTap: _busy
                    ? null
                    : () async {
                        await _call(context, widget.app, 'POST', '/api/rentdesk/messages/${_s(x['id'])}/drop');
                        widget.onDone?.call();
                      }),
          ]),
      ]),
    );
  }
}

/// rentdesk_receipt: money she marked received + the receipt / thank-you draft.
class RentdeskReceiptCard extends StatelessWidget {
  const RentdeskReceiptCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final p = _m(data['payment']);
    final msg = _m(data['message']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.receipt_long_rounded, color: C.ok),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(p['receipt_no'])} · ${_s(p['amount_text'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
          const SizedBox(height: 6),
          GlassButton(
              label: 'Receipt PDF',
              icon: Icons.picture_as_pdf_rounded,
              height: 38,
              onTap: () => _call(context, app, 'POST', '/api/rentdesk/payments/${_s(p['id'])}/receipt')),
        ]),
      ),
      if (msg.isNotEmpty) ...[const SizedBox(height: 6), RentdeskMessageCard(app: app, data: {'message': msg})],
    ]);
  }
}

/// rentdesk_alert: renewal window, registration / police pending, repair logged, DPDP forget nudge.
class RentdeskAlertCard extends StatelessWidget {
  const RentdeskAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final urgent = _m(data['request'])['urgent'] == true;
    return Glass(
      border: urgent ? C.bad : null,
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(urgent ? Icons.warning_rounded : Icons.home_work_rounded, color: urgent ? C.bad : C.accent),
        const SizedBox(width: 8),
        Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13))),
      ]),
    );
  }
}

/// rentdesk_day: the morning note.
class RentdeskDayCard extends StatelessWidget {
  const RentdeskDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aaj ka kiraya note', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 6),
          GlassButton(
              label: 'Kholo',
              height: 38,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => RentdeskScreen(app: app)))),
        ]),
      );
}
