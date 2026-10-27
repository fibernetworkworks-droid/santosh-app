/// Profile > Logistics Sahayak: Hoola as a logistics coordinator.
/// Aaj (dispatch board: nikalna hai, raste mein, late, e-way bill, POD baaki) · Shipments (S-0001 -> timeline, update, location,
/// papers LR / challan / packing, e-way bill card, POD photo, customer drafts) · Party · Niyam (firm, LR / challan prefix, GSP keys).
/// Customer messages go only when SHE sends them (or taps business WhatsApp); e-way bill filing goes only by her tap here.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

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

double? _n(String? v) => v == null ? null : double.tryParse(v.replaceAll(',', ''));

Color _stColor(String s) => switch (s) {
      'delivered' => C.ok,
      'delayed' || 'breakdown' || 'held' => C.bad,
      'cancelled' || 'returned' => C.muted,
      'booked' || 'loaded' => C.chip,
      _ => C.accent,
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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'text' || k == 'goods_text' ? 3 : 1),
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

const _base = '/api/logistics';

class LogisticsScreen extends StatefulWidget {
  const LogisticsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<LogisticsScreen> createState() => _LogisticsScreenState();
}

class _LogisticsScreenState extends State<LogisticsScreen> {
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
      final d = await widget.app.api!.call('GET', _base);
      if (mounted) setState(() => _d = _m(d));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _newShipment() async {
    final f = await _form(context, 'Naya shipment', const [
      ('consignee', 'Maal kisko (party ka naam)'),
      ('consignee_gstin', 'Unka GSTIN (ho to)'),
      ('consignee_place', 'Shehar'),
      ('consignee_pincode', 'PIN code'),
      ('consignee_phone', 'Unka phone'),
      ('goods_text', 'Maal (jaise: cement 120 bag @ 380)'),
      ('doc_no', 'Invoice / challan no.'),
      ('doc_date', 'Invoice ki tareekh'),
      ('vehicle_no', 'Gaadi no.'),
      ('transporter_name', 'Transporter'),
      ('driver_phone', 'Driver ka phone'),
      ('distance_km', 'Doori (km)'),
      ('eta', 'Kab tak pahunchega (jaise: kal shaam)'),
      ('thok_order', 'Ya Thok bill no. (bill se sab bhar jayega)'),
    ]);
    if (f == null) return;
    await _do('POST', '$_base/shipments', {...f, if (f['distance_km'] != null) 'distance_km': _n(f['distance_km'])});
  }

  void _open(Map<String, dynamic> s) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => LogisticsShipmentPage(app: widget.app, id: _s(s['id']))))
      .then((_) => _load());

  Widget _tile(Map<String, dynamic> s) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => _open(s),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: (s['late_h'] ?? 0) is num && (s['late_h'] ?? 0) > 0 ? C.bad : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(s['number'])} · ${_s(s['consignee'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(_s(s['status_label']), fg: _stColor(_s(s['status']))),
              ]),
              const SizedBox(height: 4),
              Text(
                  [
                    if (_s(s['to_place']).isNotEmpty) _s(s['to_place']),
                    if (_s(s['vehicle_no']).isNotEmpty) _s(s['vehicle_no']),
                    if (_s(s['eta']).isNotEmpty) 'ETA ${_s(s['eta'])}',
                    if ((s['late_h'] ?? 0) is num && (s['late_h'] ?? 0) > 0) '${s['late_h']} ghante late',
                    if (_s(s['ewb_no']).isNotEmpty) 'EWB ${_s(s['ewb_no'])}',
                  ].join(' · '),
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
              if (_m(s['alert']).isNotEmpty) Text(_s(_m(s['alert'])['text']), style: const TextStyle(fontSize: 12, color: C.warn)),
            ]),
          ),
        ),
      );

  Widget _section(String title, List<Map<String, dynamic>> rows) => rows.isEmpty
      ? const SizedBox.shrink()
      : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox(height: 10),
          Text(title, style: display(14)),
          const SizedBox(height: 6),
          for (final r in rows) _tile(r),
        ]);

  Widget _today() {
    final b = _m(_d?['board']);
    final w = _m(b['waiting']);
    final ot = _m(b['ontime']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(b['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      if ((w['ewb_cards'] ?? 0) > 0 || (w['drafts'] ?? 0) > 0)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text('Aapke tap ka intezaar: ${w['ewb_cards'] ?? 0} e-way bill card, ${w['drafts'] ?? 0} graahak message',
              style: const TextStyle(fontSize: 12.5, color: C.accent)),
        ),
      _section('Late', _list(b['late'])),
      _section('E-way bill par dhyaan', _list(b['ewb'])),
      _section('Aaj nikalna hai', _list(b['today'])),
      _section('Raste mein', _list(b['moving'])),
      _section('E-way bill baaki', _list(b['ewb_missing'])),
      _section('Deliver, par POD photo nahi', _list(b['no_pod'])),
      if (ot.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Samay par pahunchana (asli trips se)', style: display(14)),
        for (final e in ot.entries)
          Text('• ${e.key}: ${_m(e.value)['on_time_pct']}% samay par (${_m(e.value)['trips']} trip)', style: const TextStyle(fontSize: 12.5)),
      ],
    ]);
  }

  Widget _shipments() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, children: [
          GlassButton(label: 'Register Excel', icon: Icons.table_chart_rounded, height: 40, onTap: _busy ? null : () => _do('POST', '$_base/register')),
        ]),
        const SizedBox(height: 8),
        for (final s in _list(_d?['shipments'])) _tile(s),
      ]);

  Future<void> _party([Map<String, dynamic>? p]) async {
    final f = await _form(
        context,
        p == null ? 'Nayi party' : _s(p['name']),
        [
          if (p == null) ('name', 'Naam'),
          ('gstin', 'GSTIN'),
          ('address', 'Pata'),
          ('place', 'Shehar'),
          ('pincode', 'PIN'),
          ('phone', 'Phone'),
          ('kind', 'customer / supplier / transporter'),
        ],
        initial: p == null ? const {} : {for (final k in ['gstin', 'address', 'place', 'pincode', 'phone', 'kind']) k: _s(p[k])});
    if (f == null) return;
    await _do('POST', '$_base/parties', {if (p != null) 'party': p['id'], ...f});
  }

  Widget _parties() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(label: 'Nayi party', icon: Icons.person_add_rounded, height: 40, onTap: _busy ? null : () => _party()),
        const SizedBox(height: 8),
        for (final p in _list(_d?['parties']))
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Press(
              onTap: () => _party(p),
              child: Glass(
                padding: const EdgeInsets.all(10),
                child: Row(children: [
                  Expanded(
                      child: Text('${_s(p['name'])}${_s(p['place']).isNotEmpty ? ' · ${_s(p['place'])}' : ''}',
                          style: const TextStyle(fontWeight: FontWeight.w700))),
                  Pill(_s(p['kind'])),
                ]),
              ),
            ),
          ),
      ]);

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final f = await _form(
        context,
        'Niyam',
        const [
          ('firm', 'Firm ka naam'),
          ('role', 'trader / manufacturer / transporter'),
          ('gstin', 'GSTIN'),
          ('address', 'Pata'),
          ('place', 'Shehar'),
          ('pincode', 'PIN'),
          ('phone', 'Phone'),
          ('carrier_reg', 'Carrier registration (transporter)'),
          ('gta_rate', 'GTA GST % (5 ya 18, warna 0)'),
          ('lr_prefix', 'LR prefix'),
          ('dc_prefix', 'Challan prefix'),
          ('grace_h', 'Kitne ghante der ko late maane'),
          ('silent_h', 'Kitne ghante khabar na aaye to poochhe'),
          ('morning_time', 'Subah ka note (HH:MM)'),
          ('terms', 'LR par shartein'),
        ],
        initial: {for (final e in st.entries) if (e.value is! Map) e.key: _s(e.value)});
    if (f == null) return;
    await _do('PUT', '$_base/settings', {
      ...f,
      for (final k in ['gta_rate', 'grace_h', 'silent_h']) if (f[k] != null) k: _n(f[k]),
    });
  }

  Future<void> _gsp() async {
    final f = await _form(context, 'GSP (e-way bill API) jodiye', const [
      ('base_url', 'GSP API address (https://...)'),
      ('client_id', 'Client ID'),
      ('client_secret', 'Client secret'),
      ('gstin', 'GSTIN'),
      ('username', 'E-way bill API user'),
      ('password', 'API user ka password'),
    ]);
    if (f == null) return;
    await _do('PUT', '$_base/ewb_keys', {'provider': 'gsp', 'creds': f});
  }

  Widget _rules() {
    final st = _m(_d?['settings']);
    final ewb = _m(st['ewb']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['firm']).isEmpty ? 'Firm ka naam bhariye' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('${_s(st['role'])} · GSTIN ${_s(st['gstin']).isEmpty ? '-' : _s(st['gstin'])} · ${_s(st['place'])} ${_s(st['pincode'])}',
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _settings),
        ]),
      ),
      const SizedBox(height: 10),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('E-way bill', style: display(14)),
          Text(
              ewb['joined'] == true
                  ? 'GSP juda: ${_s(ewb['label'])}. Har filing aapke tap se hi jaati hai.'
                  : 'GSP nahi juda: Hoola JSON + portal ke steps deta hai; aap portal par upload karti hain (OTP aapka).',
              style: const TextStyle(fontSize: 12.5, height: 1.35)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 6, children: [
            GlassButton(label: 'GSP jodo', icon: Icons.link_rounded, height: 40, onTap: _busy ? null : _gsp),
            if (ewb['joined'] == true)
              GlassButton(
                  label: 'GSP hatao', icon: Icons.link_off_rounded, height: 40, onTap: _busy ? null : () => _do('PUT', '$_base/ewb_keys', {'provider': 'manual'})),
          ]),
        ]),
      ),
      const SizedBox(height: 10),
      for (final n in ((_d?['never'] as List?) ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Logistics Sahayak')),
        floatingActionButton: _tab <= 1
            ? FloatingActionButton.extended(onPressed: _busy ? null : _newShipment, icon: const Icon(Icons.local_shipping_rounded), label: const Text('Naya maal'))
            : null,
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Shipments'), (2, 'Party'), (3, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _shipments(), _parties(), _rules()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Tracking sirf aapki / driver / transporter / courier ki batayi baat se. Graahak ko message aap bhejti hain; e-way bill portal par sirf aapke tap se. Paisa Hoola nahi leta / deta.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// One shipment: timeline, update, location, papers, e-way bill, POD, drafts.
class LogisticsShipmentPage extends StatefulWidget {
  const LogisticsShipmentPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<LogisticsShipmentPage> createState() => _LogisticsShipmentPageState();
}

class _LogisticsShipmentPageState extends State<LogisticsShipmentPage> {
  Map<String, dynamic>? _v;
  bool _busy = false;
  String get _p => '$_base/shipments/${Uri.encodeComponent(widget.id)}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await widget.app.api!.call('GET', _p);
      if (mounted) setState(() => _v = _m(v));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _update() async {
    final f = await _form(context, 'Kya khabar hai?', const [
      ('text', 'Driver / transporter ne kya bola (jaise: Nagpur cross kiya)'),
      ('status', 'Ya status: dispatched / in_transit / delayed / out_for_delivery / delivered'),
      ('eta', 'Naya ETA (ho to)'),
      ('reason', 'Der ki wajah (der ho to)'),
    ]);
    if (f == null) return;
    await _do('POST', '$_p/update', f);
  }

  Future<void> _location() async {
    final f = await _form(context, 'Driver ki location', const [('text', 'Location ka link paste kijiye')]);
    if (f == null) return;
    await _do('POST', '$_p/location', f);
  }

  Future<void> _edit() async {
    final v = _v ?? const {};
    final f = await _form(
        context,
        'Badlo',
        const [
          ('vehicle_no', 'Gaadi no.'),
          ('driver_name', 'Driver'),
          ('driver_phone', 'Driver phone'),
          ('transporter_name', 'Transporter'),
          ('transporter_gstin', 'Transporter GSTIN / ID'),
          ('distance_km', 'Doori km'),
          ('freight', 'Bhada'),
          ('freight_by', 'paid / to_pay / tbb'),
          ('packages', 'Packets'),
          ('weight_kg', 'Vazan kg'),
          ('eta', 'ETA'),
          ('courier', 'Courier'),
          ('awb', 'AWB'),
        ],
        initial: {for (final k in ['vehicle_no', 'courier', 'awb', 'freight_by']) k: _s(v[k])});
    if (f == null) return;
    await _do('PATCH', _p, {
      ...f,
      for (final k in ['distance_km', 'freight', 'weight_kg']) if (f[k] != null) k: _n(f[k]),
      if (f['packages'] != null) 'packages': int.tryParse(f['packages']!) ?? 0,
    });
  }

  Future<void> _ewbNumber() async {
    final f = await _form(context, 'Portal par bana EWB', const [('ewb_no', 'EWB number (12 ank)'), ('valid_upto', 'Valid upto (jaise 26-10-2026 23:59)')]);
    if (f == null) return;
    await _do('POST', '$_p/ewb_number', f);
  }

  Future<void> _ewbKind(String kind) async {
    Map<String, String>? f = {};
    if (kind == 'part_b') {
      f = await _form(context, 'Gaadi badli (Part B)', const [('vehicle_no', 'Nayi gaadi no.'), ('reason', 'breakdown / transhipment / others'), ('from_place', 'Kahan se')]);
    } else if (kind == 'extend') {
      f = await _form(context, 'Validity badhao', const [
        ('from_place', 'Maal abhi kahan (shehar)'),
        ('from_pincode', 'Wahan ka PIN'),
        ('remaining_km', 'Baaki doori km'),
        ('reason', 'natural_calamity / law_order / transhipment / accident / others'),
      ]);
    }
    if (f == null) return;
    await _do('POST', '$_p/ewb', {'kind': kind, ...f, if (f['remaining_km'] != null) 'remaining_km': _n(f['remaining_km'])});
  }

  Future<void> _photo(ImageSource src, String stage) async {
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 80, maxWidth: 1600);
      if (x == null) return;
      Map<String, String> extra = {};
      if (stage == 'pod') {
        if (!mounted) return;
        final f = await _form(context, 'POD', const [('receiver', 'Kisne liya'), ('remarks', 'Kami / nuksaan (ho to)'), ('short', 'Kitne packet kam')]);
        if (f == null) return;
        extra = {...f, if ((f['remarks'] ?? '').isNotEmpty) 'damaged': 'true'};
      }
      final bytes = await x.readAsBytes();
      setState(() => _busy = true);
      final r = await widget.app.api!.uploadFile('$_p/photo', x.name.isEmpty ? 'photo.jpg' : x.name, bytes, fields: {'stage': stage, ...extra});
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(v == null ? 'Shipment' : _s(v['number']))),
      body: Aurora(
        child: v == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  if (_busy) const LinearProgressIndicator(),
                  _head(v),
                  const SizedBox(height: 10),
                  _actions(v),
                  const SizedBox(height: 10),
                  _ewb(v),
                  for (final m in _list(v['messages']).where((m) => m['status'] == 'draft'))
                    Padding(padding: const EdgeInsets.only(top: 10), child: LogisticsUpdateCard(app: widget.app, data: {'message': m, 'number': v['number']}, onDone: _load)),
                  const SizedBox(height: 10),
                  _timeline(v),
                ]),
              ),
      ),
    );
  }

  Widget _head(Map<String, dynamic> v) {
    final ce = _m(v['consignee']);
    final dr = _m(v['driver']);
    final loc = _m(v['location']);
    final pod = _m(v['pod']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(_s(ce['name']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
          Pill(_s(v['status_label']), fg: _stColor(_s(v['status']))),
        ]),
        Text('${_s(v['from_place'])} → ${_s(v['to_place'])}${(v['distance_km'] ?? 0) > 0 ? ' · ${v['distance_km']} km' : ''}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
        const SizedBox(height: 4),
        for (final g in _list(v['goods']))
          Text('• ${_s(g['name'])} ${_s(g['qty'])} ${_s(g['unit'])}${_s(g['hsn']).isNotEmpty ? ' · HSN ${_s(g['hsn'])}' : ''}', style: const TextStyle(fontSize: 12.5)),
        Text('Keemat ₹${_s(v['value'])} · Invoice ${_s(v['doc_no']).isEmpty ? '-' : _s(v['doc_no'])} · LR ${_s(v['lr_no']).isEmpty ? '-' : _s(v['lr_no'])}',
            style: const TextStyle(fontSize: 12.5)),
        Text(
            'Gaadi ${_s(v['vehicle_no']).isEmpty ? '-' : _s(v['vehicle_no'])}${_s(dr['name']).isNotEmpty ? ' · ${_s(dr['name'])}' : ''}'
            '${_s(v['eta']).isNotEmpty ? ' · ETA ${_s(v['eta'])}' : ''}${(v['late_h'] ?? 0) is num && (v['late_h'] ?? 0) > 0 ? ' · ${v['late_h']} ghante late' : ''}',
            style: const TextStyle(fontSize: 12.5)),
        if (_s(v['awb']).isNotEmpty) Text('Courier ${_s(v['courier'])} · AWB ${_s(v['awb'])}', style: const TextStyle(fontSize: 12.5)),
        if (_s(pod['receiver']).isNotEmpty) Text('POD: ${_s(pod['receiver'])} ${_s(pod['remarks'])}', style: const TextStyle(fontSize: 12.5, color: C.ok)),
        for (final w in ((v['warnings'] as List?) ?? const [])) Text('! $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(loc['maps']).isNotEmpty || _s(dr['phone']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Wrap(spacing: 8, runSpacing: 6, children: [
              if (_s(loc['maps']).isNotEmpty)
                GlassButton(label: 'Location', icon: Icons.place_rounded, height: 38, onTap: () => Native.openExternal(url: _s(loc['maps']))),
              if (_s(dr['phone']).isNotEmpty)
                GlassButton(label: 'Driver ko call', icon: Icons.call_rounded, height: 38, onTap: () => Native.openExternal(url: 'tel:${_s(dr['phone'])}')),
            ]),
          ),
      ]),
    );
  }

  Widget _actions(Map<String, dynamic> v) {
    final open = !['delivered', 'cancelled'].contains(_s(v['status']));
    return Wrap(spacing: 8, runSpacing: 6, children: [
      if (open) GlassButton(label: 'Khabar daalo', icon: Icons.update_rounded, height: 40, onTap: _busy ? null : _update),
      if (open) GlassButton(label: 'Location', icon: Icons.share_location_rounded, height: 40, onTap: _busy ? null : _location),
      if (open) GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _edit),
      if (_s(v['awb']).isNotEmpty) GlassButton(label: 'Courier track', icon: Icons.travel_explore_rounded, height: 40, onTap: _busy ? null : () => _do('POST', '$_p/track')),
      GlassButton(label: 'LR', icon: Icons.receipt_long_rounded, height: 40, onTap: _busy ? null : () => _do('POST', '$_p/docs', {'which': ['lr']})),
      GlassButton(label: 'Packing list', icon: Icons.inventory_2_rounded, height: 40, onTap: _busy ? null : () => _do('POST', '$_p/docs', {'which': ['packing']})),
      GlassButton(label: 'Challan', icon: Icons.description_rounded, height: 40, onTap: _busy ? null : () => _do('POST', '$_p/docs', {'which': ['challan']})),
      if (_s(v['thok_order']).isNotEmpty)
        GlassButton(label: 'Tax invoice', icon: Icons.request_quote_rounded, height: 40, onTap: _busy ? null : () => _do('POST', '$_p/docs', {'which': ['invoice']})),
      GlassButton(label: 'POD photo', icon: Icons.photo_camera_rounded, height: 40, onTap: _busy ? null : () => _photo(ImageSource.camera, 'pod')),
      GlassButton(label: 'Gallery se POD', icon: Icons.photo_library_rounded, height: 40, onTap: _busy ? null : () => _photo(ImageSource.gallery, 'pod')),
      for (final k in const [('dispatch', 'Nikla msg'), ('delay', 'Der msg'), ('delivered', 'Pahuncha msg')])
        GlassButton(label: k.$2, icon: Icons.chat_rounded, height: 40, onTap: _busy ? null : () => _do('POST', '$_p/draft', {'kind': k.$1})),
      if (open)
        GlassButton(
            label: 'Cancel',
            icon: Icons.cancel_rounded,
            height: 40,
            color: C.bad,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Cancel kyun?', const [('reason', 'Wajah')], ok: 'Cancel karo');
                    if (f != null) await _do('POST', '$_p/cancel', f);
                  }),
    ]);
  }

  Widget _ewb(Map<String, dynamic> v) {
    final e = _m(v['ewb']);
    final al = _m(e['alert']);
    return Glass(
      border: al.isNotEmpty ? (al['level'] == 'bad' ? C.bad : C.warn) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('E-way bill', style: display(14)),
        Text(_s(e['why']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
        if (_s(e['no']).isNotEmpty)
          Text('EWB ${_s(e['no'])}${_s(e['valid_upto']).isNotEmpty ? ' · valid ${_s(e['valid_upto'])}' : ''}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
        if (al.isNotEmpty) Text(_s(al['text']), style: TextStyle(fontSize: 12.5, color: al['level'] == 'bad' ? C.bad : C.warn)),
        for (final a in _list(v['ewb_asks']).where((a) => a['status'] == 'waiting'))
          Padding(padding: const EdgeInsets.only(top: 8), child: LogisticsEwbCard(app: widget.app, data: {'ask': a, 'number': v['number']}, onDone: _load)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (_s(e['no']).isEmpty) GlassButton(label: 'E-way bill card', icon: Icons.assignment_rounded, height: 38, onTap: _busy ? null : () => _ewbKind('generate')),
          if (_s(e['no']).isEmpty) GlassButton(label: 'JSON file', icon: Icons.data_object_rounded, height: 38, onTap: _busy ? null : () => _do('POST', '$_p/docs', {'which': ['ewb_json']})),
          GlassButton(label: 'Number daalo', icon: Icons.pin_rounded, height: 38, onTap: _busy ? null : _ewbNumber),
          if (_s(e['no']).isNotEmpty) GlassButton(label: 'Gaadi badli', icon: Icons.swap_horiz_rounded, height: 38, onTap: _busy ? null : () => _ewbKind('part_b')),
          if (_s(e['no']).isNotEmpty) GlassButton(label: 'Extend', icon: Icons.more_time_rounded, height: 38, onTap: _busy ? null : () => _ewbKind('extend')),
        ]),
      ]),
    );
  }

  Widget _timeline(Map<String, dynamic> v) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Safar', style: display(14)),
          const SizedBox(height: 6),
          for (final t in _list(v['timeline']).reversed)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(Icons.circle, size: 9, color: _stColor(_s(t['status']))),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                      '${_s(t['when'])} · ${_s(t['text'])}${_s(t['where']).isNotEmpty ? ' (${_s(t['where'])})' : ''} — ${_s(t['source'])}',
                      style: const TextStyle(fontSize: 12.5, height: 1.3)),
                ),
              ]),
            ),
        ]),
      );
}

/// `logistics_ewb`: an e-way bill filing waiting for HER tap. Only this tap sends it to the portal (GSP) or gives the JSON.
class LogisticsEwbCard extends StatefulWidget {
  const LogisticsEwbCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<LogisticsEwbCard> createState() => _LogisticsEwbCardState();
}

class _LogisticsEwbCardState extends State<LogisticsEwbCard> {
  bool _busy = false;
  late String _status = _s(_m(widget.data['ask'])['status']);
  List<String> _steps = const [];

  Future<void> _decide(bool yes) async {
    final a = _m(widget.data['ask']);
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '$_base/ewb/${_s(a['id'])}/decide', {'yes': yes, 'hash': _s(a['hash'])});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null) {
          _status = _s(_m(r['ask'])['status']);
          _steps = ((_m(r['result'])['steps'] as List?) ?? const []).map((e) => '$e').toList();
        }
      });
    }
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final a = _m(widget.data['ask']);
    final p = _m(a['payload']);
    final c = _m(a['checks']);
    final label = _s(widget.data['label']).isNotEmpty ? _s(widget.data['label']) : 'E-way bill';
    return Glass(
      border: _status == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.assignment_turned_in_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('$label · ${_s(widget.data['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        if (_s(p['docNo']).isNotEmpty)
          Text('${_s(p['docType'])} ${_s(p['docNo'])} ${_s(p['docDate'])} · ${_s(p['toTrdName'])} · ₹${_s(p['totInvValue'])}', style: const TextStyle(fontSize: 12.5)),
        if (_s(p['vehicleNo']).isNotEmpty) Text('Gaadi ${_s(p['vehicleNo'])}${p['transDistance'] != null ? ' · ${p['transDistance']} km' : ''}', style: const TextStyle(fontSize: 12.5)),
        if (c['validity_days'] != null) Text('Validity: ${c['validity_days']} din', style: const TextStyle(fontSize: 12.5)),
        if (p['tripSheetEwbBills'] != null) Text('${(p['tripSheetEwbBills'] as List).length} e-way bill ek gaadi mein', style: const TextStyle(fontSize: 12.5)),
        for (final w in ((c['warnings'] as List?) ?? const [])) Text('! $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(widget.data['how']).isNotEmpty) Text(_s(widget.data['how']), style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (_status == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, bhejo', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else ...[
          Text(
              switch (_status) {
                'done' => 'Portal par ho gaya.',
                'manual' => 'JSON file aapki files mein: portal par upload kijiye, phir EWB number bataiye.',
                'rejected' => 'Mana kiya: kuch nahi bheja.',
                'stale' => 'Purana card: naya banaiye.',
                'failed' => 'Portal ne mana kiya (wajah upar).',
                _ => _status,
              },
              style: TextStyle(fontSize: 12.5, color: _status == 'done' ? C.ok : C.muted)),
          for (final st in _steps) Text('→ $st', style: const TextStyle(fontSize: 12)),
        ],
      ]),
    );
  }
}

/// `logistics_update`: a customer message draft. She sends it (WhatsApp / SMS from her phone) or taps business WhatsApp.
class LogisticsUpdateCard extends StatefulWidget {
  const LogisticsUpdateCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<LogisticsUpdateCard> createState() => _LogisticsUpdateCardState();
}

class _LogisticsUpdateCardState extends State<LogisticsUpdateCard> {
  late Map<String, dynamic> _msg = _m(widget.data['message']);
  bool _busy = false;

  Future<void> _post(String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', path, body);
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['message'] is Map) _msg = _m(r['message']);
      });
    }
    widget.onDone?.call();
  }

  Future<void> _edit() async {
    final f = await _form(context, 'Message badlo', const [('text', 'Message')], initial: {'text': _s(_msg['text'])}, ok: 'Save');
    if (f == null || f['text'] == null) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'PUT', '$_base/messages/${_s(_msg['id'])}', {'text': f['text']});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['message'] is Map) _msg = _m(r['message']);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final draft = _s(_msg['status']) == 'draft';
    final text = _s(_msg['text']);
    final blanks = RegExp(r'\[[^\]]+\]').allMatches(text).map((m) => m.group(0)!).toList();
    return Glass(
      border: draft ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.chat_bubble_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Graahak ke liye · ${_s(widget.data['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(_msg['kind'])),
        ]),
        const SizedBox(height: 6),
        SelectableText(text, style: const TextStyle(fontSize: 12.5, height: 1.35)),
        if (blanks.isNotEmpty) Text('Bhejne se pehle bhariye: ${blanks.join(', ')}', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (draft)
          Wrap(spacing: 8, runSpacing: 6, children: [
            if (_s(_msg['wa_link']).isNotEmpty)
              GlassButton(label: 'WhatsApp', icon: Icons.send_rounded, height: 40, onTap: () => Native.openExternal(url: _s(_msg['wa_link']))),
            if (_s(_msg['sms_link']).isNotEmpty)
              GlassButton(label: 'SMS', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: _s(_msg['sms_link']))),
            GlassButton(
                label: 'Copy',
                icon: Icons.copy_rounded,
                height: 40,
                onTap: () {
                  Clipboard.setData(ClipboardData(text: text));
                  _snack(context, 'Copy ho gaya');
                }),
            GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _edit),
            GlassButton(label: 'Maine bhej diya', icon: Icons.done_all_rounded, height: 40, onTap: _busy ? null : () => _post('$_base/messages/${_s(_msg['id'])}/sent')),
            GlassButton(
                label: 'Business WhatsApp se',
                icon: Icons.storefront_rounded,
                height: 40,
                onTap: _busy || blanks.isNotEmpty ? null : () => _post('$_base/messages/${_s(_msg['id'])}/send', {'hash': _s(_msg['hash'])})),
          ])
        else
          Text(_s(_msg['via']) == 'business' ? 'Business WhatsApp se gaya.' : 'Bhej diya.', style: const TextStyle(fontSize: 12.5, color: C.ok)),
      ]),
    );
  }
}

/// `logistics_shipment`: shipment summary (updated in place); tap opens it.
class LogisticsShipmentCard extends StatelessWidget {
  const LogisticsShipmentCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final v = _m(data['shipment']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LogisticsShipmentPage(app: app, id: _s(v['id'])))),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.local_shipping_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(v['number'])} · ${_s(_m(v['consignee'])['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(v['status_label']), fg: _stColor(_s(v['status']))),
          ]),
          const SizedBox(height: 4),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
          for (final w in ((v['warnings'] as List?) ?? const []).take(3)) Text('! $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        ]),
      ),
    );
  }
}

/// `logistics_alert`: late vs ETA, e-way bill expiring / expired, no news while moving.
class LogisticsAlertCard extends StatelessWidget {
  const LogisticsAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final bad = ['ewb_expired', 'ewb_max', 'late'].contains(_s(data['kind']));
    return Glass(
      border: bad ? C.bad : C.warn,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(bad ? Icons.warning_amber_rounded : Icons.schedule_rounded, color: bad ? C.bad : C.warn),
          const SizedBox(width: 8),
          Expanded(child: Text('Logistics · ${_s(data['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        Text(_s(data['text']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(
              label: 'Kholo',
              icon: Icons.open_in_new_rounded,
              height: 38,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LogisticsShipmentPage(app: app, id: _s(data['id']))))),
          if (_s(data['phone']).isNotEmpty)
            GlassButton(label: 'Driver ko call', icon: Icons.call_rounded, height: 38, onTap: () => Native.openExternal(url: 'tel:${_s(data['phone'])}')),
        ]),
      ]),
    );
  }
}

/// `logistics_day`: the morning dispatch note.
class LogisticsDayCard extends StatelessWidget {
  const LogisticsDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LogisticsScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.local_shipping_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(data['text']), style: const TextStyle(fontSize: 13, height: 1.35))),
          ]),
        ),
      );
}
