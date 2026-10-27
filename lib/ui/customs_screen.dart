/// Profile > Customs Sahayak: Hoola as the import & customs desk.
/// Aaj (BE deadlines, demurrage / detention clocks, filing cards waiting) · Shipments (I-0001: goods lines with HS, documents
/// checklist, landed cost from HER rates, clearance timeline) · HS jaanch (suggestion = andaaza, chapter notes, regulators) · Niyam.
/// FILING waits for HER tap on the card: only then the Bill of Entry data goes to her CHA. Hoola never files on ICEGATE, never pays duty.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _level(String l) => switch (l) { 'bad' => C.bad, 'warn' => C.warn, 'ok' => C.ok, _ => C.muted };

const _stages = [
  ('shipped', 'Chal pada'),
  ('arrived', 'Pahuncha'),
  ('igm', 'IGM'),
  ('be_filed', 'BE file'),
  ('query', 'Sawaal / exam'),
  ('assessed', 'Assessment'),
  ('duty_paid', 'Duty jama'),
  ('ooc', 'Out of Charge'),
  ('delivered', 'Godown'),
  ('empty_returned', 'Container wapas'),
];

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {String ok = 'Aage'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'desc' || k == 'note' ? 3 : 1),
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

num? _n(String? v) => v == null ? null : num.tryParse(v.replaceAll(',', ''));

class CustomsScreen extends StatefulWidget {
  const CustomsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CustomsScreen> createState() => _CustomsScreenState();
}

class _CustomsScreenState extends State<CustomsScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _hs;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/customs'));
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

  void _open(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => CustomsShipmentPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _new() async {
    final f = await _form(context, 'Naya import shipment', const [
      ('supplier', 'Supplier ka naam'),
      ('origin', 'Maal kis desh ka (origin)'),
      ('incoterm', 'Incoterm (FOB / CIF / EXW / CFR / DAP ...)'),
      ('currency', 'Currency (USD / EUR / AED ...)'),
      ('invoice_value', 'Invoice value (us currency mein)'),
      ('mode', 'Mode: sea / air / courier / land'),
      ('port', 'Port / air cargo / ICD'),
      ('bl_no', 'BL / AWB number (ho to)'),
      ('eta', 'ETA (dd-mm-yyyy)'),
    ], ok: 'Banao');
    if (f == null || (f['supplier'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    if (f['invoice_value'] != null) body['invoice_value'] = _n(f['invoice_value']) ?? 0;
    final r = await _run('POST', '/api/customs/shipments', body);
    final s = _m(r?['shipment']);
    if (s['id'] != null && mounted) _open(_s(s['id']));
  }

  Widget _tile(Map<String, dynamic> v) {
    final alerts = _list(_m(v['clock'])['alerts']);
    final worst = alerts.any((a) => a['level'] == 'bad') ? C.bad : alerts.any((a) => a['level'] == 'warn') ? C.warn : null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _open(_s(v['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: worst,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(v['number'])} · ${_s(v['supplier'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(v['stage_label'])),
            ]),
            Text(
                [
                  _s(v['origin']),
                  _s(v['mode_label']),
                  if (_s(v['port']).isNotEmpty) _s(v['port']),
                  if (_s(v['bl_no']).isNotEmpty) _s(v['bl_no']),
                  if (_s(v['be_no']).isNotEmpty) 'BE ${_s(v['be_no'])}',
                ].where((x) => x.isNotEmpty).join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (alerts.isNotEmpty) Text(_s(alerts.first['say']), style: TextStyle(fontSize: 12.5, color: _level(_s(alerts.first['level'])))),
            Text(_s(v['next']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: C.accentSoft)),
          ]),
        ),
      ),
    );
  }

  Widget _today() {
    final d = _d ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      for (final f in _list(d['waiting']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: CustomsFilingCard(app: widget.app, data: {'filing': f}, onDone: _load)),
      for (final a in _list(d['alerts']))
        Text('• ${_s(a['shipment'])}: ${_s(a['say'])}', style: TextStyle(fontSize: 12.5, color: _level(_s(a['level'])))),
      const SizedBox(height: 8),
      if (_list(d['open']).isNotEmpty) Text('Khule shipment', style: display(15)),
      const SizedBox(height: 6),
      for (final v in _list(d['open'])) _tile(v),
    ]);
  }

  Widget _shipments() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GradientButton(label: 'Naya import', icon: Icons.add_rounded, height: 48, onTap: _busy ? null : _new),
        const SizedBox(height: 10),
        if (_list(_d?['shipments']).isEmpty) const Text('Abhi koi shipment nahi.', style: TextStyle(color: C.muted)),
        for (final v in _list(_d?['shipments'])) _tile(v),
      ]);

  Future<void> _hsAsk() async {
    final f = await _form(context, 'HS code ka sujhaav', const [('desc', 'Maal kya hai, kis cheez ka bana, kis kaam ka')], ok: 'Dekho');
    if (f == null || (f['desc'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/customs/hs/suggest', {'desc': f['desc']});
    if (r != null && mounted) setState(() => _hs = r);
  }

  Widget _hsTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GradientButton(label: 'Maal batao, code sujhao', icon: Icons.manage_search_rounded, height: 48, onTap: _busy ? null : _hsAsk),
        const SizedBox(height: 8),
        const Text('Sujhaav sirf andaaza hai. 8 ank ka code Customs Tariff / CHA se pakka kariye; galat code par jurmana aur maal rukta hai.',
            style: TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 10),
        if (_hs != null) ...[
          Text(_s(_hs!['say']), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          for (final c in _list(_hs!['candidates'])) _HsCandidate(c: c),
          Text(_s(_hs!['gir']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ],
      ]);

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Importer ki jaankari', [
      ('firm', 'Firm ka naam (${_s(st['firm'])})'),
      ('iec', 'IEC (${_s(st['iec'])})'),
      ('gstin', 'GSTIN (${_s(st['gstin'])})'),
      ('address', 'Pata'),
      ('cha_name', 'CHA / customs broker (${_s(st['cha_name'])})'),
      ('cha_phone', 'CHA phone'),
      ('cha_email', 'CHA email'),
      ('morning_time', 'Subah ka note (HH:MM, abhi ${_s(st['morning_time'])})'),
    ], ok: 'Save');
    if (f == null || f.isEmpty) return;
    await _run('PUT', '/api/customs/settings', f);
  }

  Widget _rules() {
    final st = _m(_d?['settings']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['firm']).isEmpty ? 'Firm ka naam nahi diya' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('IEC: ${_s(st['iec']).isEmpty ? '—' : _s(st['iec'])}${st['iec_ok'] == true ? ' ✓' : ''} · GSTIN: ${_s(st['gstin']).isEmpty ? '—' : _s(st['gstin'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text('CHA: ${_s(st['cha_name']).isEmpty ? '—' : _s(st['cha_name'])} ${_s(st['cha_phone'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      ),
      const SizedBox(height: 8),
      GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _busy ? null : _settings),
      const SizedBox(height: 10),
      Text('Hoola kya nahi karta', style: display(14)),
      for (final n in ((_d?['never'] as List?) ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Customs Sahayak')),
        floatingActionButton: _tab <= 1
            ? FloatingActionButton.extended(onPressed: _busy ? null : _new, icon: const Icon(Icons.local_shipping_rounded), label: const Text('Naya import'))
            : null,
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Shipments'), (2, 'HS jaanch'), (3, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _shipments(), _hsTab(), _rules()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Bill of Entry ka data CHA ko sirf aapki haan ke baad jaata hai. Hoola ICEGATE par file nahi karta, duty nahi bharta, duty rate khud nahi lagata.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

class _HsCandidate extends StatelessWidget {
  const _HsCandidate({required this.c});
  final Map<String, dynamic> c;
  @override
  Widget build(BuildContext context) {
    final chk = _m(c['check']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(c['formatted']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
            Pill(switch (_s(c['source'])) { 'aapka' => 'aapka pichhla', 'model' => 'andaaza', _ => 'heading' }),
          ]),
          if (_s(c['title']).isNotEmpty) Text(_s(c['title']), style: const TextStyle(fontSize: 12.5)),
          if (_s(c['why']).isNotEmpty) Text(_s(c['why']), style: const TextStyle(fontSize: 12, color: C.muted)),
          if (_s(c['ask']).isNotEmpty) Text('Pakka karne ke liye: ${_s(c['ask'])}', style: const TextStyle(fontSize: 12, color: C.accentSoft)),
          for (final n in ((chk['notes'] as List?) ?? const []).take(1)) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.faint)),
          for (final r in _list(chk['regulators'])) Text('• ${_s(r['label'])}: ${_s(r['doc'])}', style: const TextStyle(fontSize: 11.5, color: C.warn)),
        ]),
      ),
    );
  }
}

/// One import shipment: lines + HS, documents, cost, timeline, filing card.
class CustomsShipmentPage extends StatefulWidget {
  const CustomsShipmentPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<CustomsShipmentPage> createState() => _CustomsShipmentPageState();
}

class _CustomsShipmentPageState extends State<CustomsShipmentPage> {
  Map<String, dynamic>? _v;
  Map<String, dynamic>? _cost;
  bool _busy = false;

  String get _p => '/api/customs/shipments/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', _p));
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

  Future<void> _edit() async {
    final v = _v ?? const {};
    final f = await _form(context, 'Shipment badlo', [
      ('invoice_value', 'Invoice value (${_s(v['invoice_value'])})'),
      ('fx', 'Exchange rate ₹ (CBIC notified, abhi ${_s(v['fx'])})'),
      ('freight', 'Freight (asli raqam, pata ho to)'),
      ('insurance', 'Insurance (asli raqam, pata ho to)'),
      ('bl_no', 'BL / AWB (${_s(v['bl_no'])})'),
      ('eta', 'ETA (dd-mm-yyyy)'),
      ('free_days', 'Port / CFS free din (${_s(v['free_days'])})'),
      ('demurrage_per_day', 'Demurrage ₹ / din (aapki rate)'),
      ('detention_free_days', 'Container free din (shipping line)'),
      ('detention_per_day', 'Detention ₹ / din'),
      ('cha', 'Is shipment ka CHA'),
    ], ok: 'Save');
    if (f == null || f.isEmpty) return;
    final body = <String, dynamic>{};
    for (final e in f.entries) {
      body[e.key] = const ['bl_no', 'eta', 'cha'].contains(e.key) ? e.value : (_n(e.value) ?? e.value);
    }
    await _run('PATCH', _p, body);
  }

  Future<void> _addLine() async {
    final f = await _form(context, 'Maal ki line', const [
      ('desc', 'Maal (naam, material, kaam)'),
      ('qty', 'Quantity'),
      ('unit', 'Unit (pcs / kg / nos)'),
      ('value', 'Value (invoice currency)'),
    ], ok: 'Jodo');
    if (f == null || (f['desc'] ?? '').isEmpty) return;
    await _run('POST', '$_p/lines', {'desc': f['desc'], 'qty': _n(f['qty']) ?? 0, 'unit': f['unit'] ?? '', 'value': _n(f['value']) ?? 0});
  }

  Future<void> _confirmHs(Map<String, dynamic> ln) async {
    final f = await _form(context, 'Line ${_s(ln['no'])}: pakka HS code', [('hs', '8 ank (abhi ${_s(ln['hs_fmt'])})')], ok: 'Pakka');
    if (f == null || (f['hs'] ?? '').isEmpty) return;
    await _run('POST', '$_p/hs', {'line': ln['no'], 'hs': f['hs']});
  }

  Future<void> _rates(Map<String, dynamic> ln) async {
    final f = await _form(context, 'Line ${_s(ln['no'])}: duty rates (Tariff / CHA se)', const [
      ('bcd', 'BCD %'),
      ('sws', 'SWS % (khaali = BCD ka 10%)'),
      ('igst', 'IGST %'),
      ('cess', 'Compensation cess % (ho to)'),
      ('aidc', 'AIDC % (ho to)'),
    ], ok: 'Save');
    if (f == null || f.isEmpty) return;
    await _run('POST', '$_p/lines', {'no': ln['no'], for (final e in f.entries) e.key: _n(e.value)});
    await _loadCost();
  }

  Future<void> _suggest(Map<String, dynamic> ln) async {
    final r = await _call(context, widget.app, 'POST', '/api/customs/hs/suggest', {'desc': _s(ln['desc']), 'retail': ln['retail'] == true});
    if (r == null || !mounted) return;
    await showDialog<void>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Sujhaav (andaaza)'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [for (final c in _list(r['candidates'])) _HsCandidate(c: c)])),
        actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))],
      ),
    );
  }

  Future<void> _loadCost() async {
    try {
      final c = _m(await widget.app.api!.call('GET', '$_p/cost'));
      if (mounted) setState(() => _cost = c);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _stage(String key, String label) async {
    final f = await _form(context, label, [
      ('at', 'Tareekh (dd-mm-yyyy, khaali = aaj)'),
      if (key == 'be_filed') ('be_no', 'BE number'),
      if (key == 'igm') ('igm_no', 'IGM number'),
      if (key == 'duty_paid') ('amount', 'Kitni duty bhari (₹, jaisa CHA bola)'),
      ('note', 'Note'),
      ('by', 'Kisne bataya (CHA / line)'),
    ], ok: 'Darj karo');
    if (f == null) return;
    await _run('POST', '$_p/stage', {
      'stage': key,
      ...f,
      if (f['amount'] != null) 'amount': _n(f['amount']),
    });
  }

  Widget _lines(Map<String, dynamic> v) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('Maal', style: display(15))),
          GlassButton(label: 'Line', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : _addLine),
        ]),
        const SizedBox(height: 6),
        for (final ln in _list(v['lines']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              padding: const EdgeInsets.all(12),
              border: ln['hs_confirmed'] == true ? null : C.warn,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(ln['no'])}. ${_s(ln['desc'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${_s(ln['qty'])} ${_s(ln['unit'])} · ${_s(v['currency'])} ${_s(ln['value'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                Text(
                    _s(ln['hs_fmt']).isEmpty
                        ? 'HS code nahi'
                        : 'HS ${_s(ln['hs_fmt'])} ${ln['hs_confirmed'] == true ? '(pakka)' : '(andaaza, pakka kariye)'}',
                    style: TextStyle(fontSize: 12.5, color: ln['hs_confirmed'] == true ? C.ok : C.warn)),
                Text(
                    'Rates: BCD ${_s(ln['bcd']).isEmpty ? '?' : _s(ln['bcd'])}% · IGST ${_s(ln['igst']).isEmpty ? '?' : _s(ln['igst'])}%'
                    '${_s(ln['sws']).isNotEmpty ? ' · SWS ${_s(ln['sws'])}%' : ''}',
                    style: const TextStyle(fontSize: 12, color: C.muted)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  GlassButton(label: 'Sujhao', icon: Icons.manage_search_rounded, height: 36, onTap: _busy ? null : () => _suggest(ln)),
                  GlassButton(label: 'HS pakka', icon: Icons.verified_rounded, height: 36, onTap: _busy ? null : () => _confirmHs(ln)),
                  GlassButton(label: 'Rates', icon: Icons.percent_rounded, height: 36, onTap: _busy ? null : () => _rates(ln)),
                  GlassButton(
                      label: 'Hatao', icon: Icons.delete_outline_rounded, height: 36, onTap: _busy ? null : () => _run('DELETE', '$_p/lines/${_s(ln['no'])}')),
                ]),
              ]),
            ),
          ),
      ]);

  Widget _docs(Map<String, dynamic> v) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Kaagaz (${_s(v['docs_missing'])} zaroori baaki)', style: display(15)),
        const SizedBox(height: 6),
        for (final d in _list(v['docs']))
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(
                  switch (_s(d['status'])) { 'have' => Icons.check_circle_rounded, 'na' => Icons.remove_circle_outline_rounded, _ => Icons.radio_button_unchecked_rounded },
                  size: 20,
                  color: switch (_s(d['status'])) { 'have' => C.ok, 'na' => C.muted, _ => d['required'] == true ? C.warn : C.faint }),
              const SizedBox(width: 8),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(d['label']), style: const TextStyle(fontSize: 12.5)),
                  if (_s(d['why']).isNotEmpty) Text(_s(d['why']), style: const TextStyle(fontSize: 11, color: C.faint)),
                  if (_s(d['portal']).isNotEmpty)
                    InkWell(
                      onTap: () => Native.openExternal(url: 'https://${_s(d['portal']).split(' ').first}'),
                      child: Text(_s(d['portal']), style: const TextStyle(fontSize: 11, color: C.accentSoft)),
                    ),
                ]),
              ),
              PopupMenuButton<String>(
                onSelected: (st) => _run('POST', '$_p/docs', {'key': d['key'], 'status': st}),
                itemBuilder: (_) => const [
                  PopupMenuItem(value: 'have', child: Text('Mil gaya')),
                  PopupMenuItem(value: 'missing', child: Text('Baaki')),
                  PopupMenuItem(value: 'na', child: Text('Zaroorat nahi')),
                ],
              ),
            ]),
          ),
      ]);

  Widget _costBox() {
    final c = _cost;
    if (c == null) return GlassButton(label: 'Landed cost dekho', icon: Icons.calculate_rounded, onTap: _busy ? null : _loadCost);
    final t = _m(c['totals']);
    final av = _m(c['value']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Landed cost (andaaza)', style: display(14)),
        const SizedBox(height: 4),
        Text(_s(c['say']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
        if (c['complete'] == true) ...[
          const SizedBox(height: 6),
          Text('Assessable value ₹${_s(t['av'])} · BCD ₹${_s(t['bcd'])} · SWS ₹${_s(t['sws'])} · IGST ₹${_s(t['igst'])}',
              style: const TextStyle(fontSize: 12, color: C.muted)),
          Text('Landed (IGST credit ke baad) ₹${_s(c['landed_cost'])}', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
        ],
        for (final n in ((av['notes'] as List?) ?? const [])) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.faint)),
      ]),
    );
  }

  Widget _timeline(Map<String, dynamic> v) {
    final done = {for (final x in _list(v['timeline'])) _s(x['stage']): x};
    final clock = _m(v['clock']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Clearance', style: display(15)),
      if (_s(clock['be_say']).isNotEmpty) Text(_s(clock['be_say']), style: const TextStyle(fontSize: 12, color: C.muted)),
      for (final k in const ['demurrage', 'detention'])
        if (_m(clock[k]).isNotEmpty) Text(_s(_m(clock[k])['say']), style: TextStyle(fontSize: 12, color: _level(_s(_m(clock[k])['level'])))),
      const SizedBox(height: 6),
      for (final (key, label) in _stages)
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(done.containsKey(key) ? Icons.check_circle_rounded : Icons.circle_outlined, color: done.containsKey(key) ? C.ok : C.faint, size: 20),
          title: Text(label),
          subtitle: done.containsKey(key)
              ? Text([_s(done[key]!['shown']), _s(done[key]!['note']), _s(done[key]!['by'])].where((x) => x.isNotEmpty).join(' · '))
              : null,
          trailing: TextButton(onPressed: _busy ? null : () => _stage(key, label), child: Text(done.containsKey(key) ? 'Badlo' : 'Ho gaya')),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(v == null ? 'Shipment' : '${_s(v['number'])} · ${_s(v['supplier'])}')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: v == null
              ? ListView(children: const [SizedBox(height: 120), Center(child: CircularProgressIndicator())])
              : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
                  if (_busy) const LinearProgressIndicator(),
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(v['next']), style: const TextStyle(fontWeight: FontWeight.w700, height: 1.3)),
                      const SizedBox(height: 6),
                      Text(
                          [
                            'Origin ${_s(v['origin'])}',
                            '${_s(v['incoterm'])} ${_s(v['place'])}'.trim(),
                            '${_s(v['currency'])} ${_s(v['invoice_value'])}',
                            _s(v['mode_label']),
                            if (_s(v['port']).isNotEmpty) _s(v['port']),
                            if (_s(v['bl_no']).isNotEmpty) 'BL/AWB ${_s(v['bl_no'])}',
                            if (v['fta'] == true) 'FTA: ${_s(v['fta_name']).isEmpty ? 'claim' : _s(v['fta_name'])}',
                            if (_s(v['cha']).isNotEmpty) 'CHA ${_s(v['cha'])}',
                          ].join(' · '),
                          style: const TextStyle(fontSize: 12.5, color: C.muted)),
                      Text(_s(v['incoterm_means']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
                      const SizedBox(height: 8),
                      Wrap(spacing: 8, runSpacing: 8, children: [
                        GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _edit),
                        GlassButton(label: 'Data sheet', icon: Icons.table_view_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_p/datasheet')),
                      ]),
                    ]),
                  ),
                  const SizedBox(height: 10),
                  if (v['filing'] is Map && _s(_m(v['filing'])['status']) == 'waiting')
                    Padding(padding: const EdgeInsets.only(bottom: 10), child: CustomsFilingCard(app: widget.app, data: {'filing': v['filing']}, onDone: _load)),
                  _lines(v),
                  const SizedBox(height: 10),
                  _docs(v),
                  const SizedBox(height: 10),
                  _costBox(),
                  const SizedBox(height: 10),
                  if (_list(v['blockers']).isNotEmpty) ...[
                    Text('Filing se pehle', style: display(14)),
                    for (final b in (v['blockers'] as List)) Text('• $b', style: const TextStyle(fontSize: 12.5, color: C.warn)),
                  ],
                  for (final w in ((v['warnings'] as List?) ?? const [])) Text('• $w', style: const TextStyle(fontSize: 12, color: C.muted)),
                  const SizedBox(height: 8),
                  GradientButton(
                      label: 'Filing card banao (aapki haan)',
                      icon: Icons.assignment_turned_in_rounded,
                      height: 48,
                      onTap: _busy ? null : () => _run('POST', '$_p/filing')),
                  const SizedBox(height: 12),
                  _timeline(v),
                ]),
        ),
      ),
    );
  }
}

/// `customs_filing`: the BE data that would go to her CHA; ONLY her tap here approves (hash checked on the server).
class CustomsFilingCard extends StatefulWidget {
  const CustomsFilingCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<CustomsFilingCard> createState() => _CustomsFilingCardState();
}

class _CustomsFilingCardState extends State<CustomsFilingCard> {
  bool _busy = false;
  late String _status = _s(_m(widget.data['filing'])['status']);
  Map<String, dynamic> _drafts = {};

  @override
  void initState() {
    super.initState();
    _drafts = _m(widget.data['drafts']);
  }

  Future<void> _decide(bool yes) async {
    final f = _m(widget.data['filing']);
    String reason = '';
    if (!yes) {
      final r = await _form(context, 'Kyun nahi? (zaroori nahi)', const [('reason', 'Wajah')], ok: 'Mana karo');
      if (r == null) return;
      reason = r['reason'] ?? '';
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/customs/filings/${_s(f['id'])}/decide', {'yes': yes, 'hash': _s(f['hash']), 'reason': reason});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null) {
          _status = _s(_m(r['filing'])['status']);
          _drafts = _m(r['drafts']);
        }
      });
    }
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final f = _m(widget.data['filing']);
    final s = _m(f['summary']);
    return Glass(
      border: _status == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.assignment_turned_in_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Filing: aapki haan · ${_s(f['number'])} · ${_s(s['shipment'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        Text('${_s(s['supplier'])} (${_s(s['origin'])}) · ${_s(s['incoterm'])} · ${_s(s['currency'])} ${_s(s['invoice_value'])} · ${_s(s['port'])}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
        Text('BE type: ${_s(s['be_type'])} · CHA: ${_s(s['cha']).isEmpty ? '—' : _s(s['cha'])}${s['fta'] == true ? ' · FTA claim' : ''}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final ln in _list(s['lines']))
          Text('• ${_s(ln['desc'])}: ${_s(ln['qty'])} ${_s(ln['unit'])}, HS ${_s(ln['hs'])}, ${_s(ln['value'])}', style: const TextStyle(fontSize: 12)),
        for (final w in ((f['warnings'] as List?) ?? const [])) Text('Dhyaan: $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 4),
        const Text('Haan = data sheet + CHA ko message ka draft. Submit aur duty aap / CHA karte hain; Hoola ICEGATE par file nahi karta.',
            style: TextStyle(fontSize: 11.5, color: C.faint)),
        const SizedBox(height: 8),
        if (_status == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, CHA ko do', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else
          Text(
              switch (_status) {
                'approved' => 'Haan di. CHA ko message aap bhejiye.',
                'rejected' => 'Mana kiya.',
                'stale' => 'Shipment badal gaya: naya card banwaiye.',
                _ => _status,
              },
              style: TextStyle(color: _status == 'approved' ? C.ok : C.muted, fontSize: 12.5)),
        if (_drafts.isNotEmpty)
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (_s(_drafts['whatsapp']).isNotEmpty)
              GlassButton(label: 'WhatsApp CHA', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: _s(_drafts['whatsapp']))),
            if (_s(_drafts['email']).isNotEmpty)
              GlassButton(label: 'Email CHA', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: _s(_drafts['email']))),
          ]),
      ]),
    );
  }
}

/// `customs_shipment`: one live card per shipment (stage, next step, first alert).
class CustomsShipmentCard extends StatelessWidget {
  const CustomsShipmentCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final v = _m(data['shipment']);
    final alerts = _list(data['alerts']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomsShipmentPage(app: app, id: _s(v['id'])))),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.local_shipping_rounded, color: C.teal),
            const SizedBox(width: 8),
            Expanded(child: Text('Import ${_s(v['number'])} · ${_s(v['supplier'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(v['stage_label'])),
          ]),
          const SizedBox(height: 4),
          for (final a in alerts.take(2)) Text(_s(a['say']), style: TextStyle(fontSize: 12.5, color: _level(_s(a['level'])))),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
        ]),
      ),
    );
  }
}

/// `customs_alert`: BE deadline / demurrage / detention / duty payment reminders.
class CustomsAlertCard extends StatelessWidget {
  const CustomsAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: _s(data['id']).isEmpty
            ? null
            : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomsShipmentPage(app: app, id: _s(data['id'])))),
        child: Glass(
          border: _level(_s(data['level'])),
          child: Row(children: [
            Icon(Icons.timer_rounded, color: _level(_s(data['level']))),
            const SizedBox(width: 8),
            Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13, height: 1.3))),
          ]),
        ),
      );
}

/// `customs_day`: the morning import desk note.
class CustomsDayCard extends StatelessWidget {
  const CustomsDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomsScreen(app: app))),
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.wb_sunny_rounded, color: C.accent),
              const SizedBox(width: 8),
              Text('Aaj ka import desk', style: display(14)),
            ]),
            const SizedBox(height: 6),
            for (final l in ((data['lines'] as List?) ?? const []).take(8)) Text('• $l', style: const TextStyle(fontSize: 12.5)),
          ]),
        ),
      );
}
