/// Profile > Fleet Sahayak: Hoola as the fleet manager.
/// Aaj (today's trips, expired / due papers, service due, diesel signals, spends waiting for her) · Gaadiyan (vehicles, papers,
/// fuel, service, tyres, breakdowns, challans) · Trips (route + load check, vehicle + driver) · Kharcha (spend cards, cost per
/// km) · Niyam (her rates, reminders, official Vahan / eChallan steps). Any spend runs only after HER tap (fingerprint for money
/// once a phone key is set up); Hoola never pays a challan or buys anything.
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

Color _docColor(String st) => switch (st) { 'expired' => C.bad, 'due' => C.warn, 'missing' => C.faint, 'ok' => C.ok, _ => C.chip };

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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'notes' || k == 'items' ? 3 : 1),
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

/// "cement 50kg x 100, 0.04 cbm" lines -> [{name, weight_kg, count, cbm}]
List<Map<String, dynamic>> _parseItems(String text) {
  final out = <Map<String, dynamic>>[];
  for (final raw in text.split(RegExp(r'[\n;]'))) {
    final line = raw.trim();
    if (line.isEmpty) continue;
    final kg = RegExp(r'(\d+(?:\.\d+)?)\s*kg', caseSensitive: false).firstMatch(line);
    final ton = RegExp(r'(\d+(?:\.\d+)?)\s*(?:t|ton|tonne)\b', caseSensitive: false).firstMatch(line);
    final cbm = RegExp(r'(\d+(?:\.\d+)?)\s*cbm', caseSensitive: false).firstMatch(line);
    final cnt = RegExp(r'[x×]\s*(\d+)', caseSensitive: false).firstMatch(line);
    final name = line.split(RegExp(r'\d')).first.trim();
    out.add({
      'name': name.isEmpty ? line : name,
      if (kg != null) 'weight_kg': num.parse(kg.group(1)!),
      if (kg == null && ton != null) 'weight_kg': num.parse(ton.group(1)!) * 1000,
      if (cbm != null) 'cbm': num.parse(cbm.group(1)!),
      'count': cnt != null ? int.parse(cnt.group(1)!) : 1,
    });
  }
  return out;
}

class FleetScreen extends StatefulWidget {
  const FleetScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<FleetScreen> createState() => _FleetScreenState();
}

class _FleetScreenState extends State<FleetScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _cost;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/fleet'));
      final c = _m(await widget.app.api!.call('GET', '/api/fleet/cost'));
      if (mounted) setState(() {
        _d = d;
        _cost = c;
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

  void _openVehicle(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => FleetVehiclePage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _addVehicle() async {
    final f = await _form(context, 'Nayi gaadi', const [
      ('reg', 'Gaadi number (MH 30 AB 1234)'),
      ('type', 'Type: truck / tempo / pickup / bus / taxi / car'),
      ('make', 'Company / model'),
      ('capacity_t', 'Capacity (tonne)'),
      ('capacity_cbm', 'Body (cbm, ho to)'),
      ('tank_l', 'Tank (litre)'),
      ('reg_date', 'Registration date (DD-MM-YYYY)'),
    ], ok: 'Jodo');
    if (f == null || (f['reg'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    for (final k in ['capacity_t', 'capacity_cbm', 'tank_l']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    final r = await _run('POST', '/api/fleet/vehicles', body);
    final v = _m(r?['vehicle']);
    if (v['id'] != null && mounted) _openVehicle(_s(v['id']));
  }

  Future<void> _newTrip() async {
    final f = await _form(context, 'Nayi trip', const [
      ('origin', 'Kahan se'),
      ('destination', 'Kahan tak'),
      ('day', 'Taarikh (YYYY-MM-DD, khaali = aaj)'),
      ('items', 'Maal: har line "naam 50kg x 100 0.04cbm"'),
      ('vehicle', 'Gaadi (number, ho to)'),
      ('driver', 'Driver ka naam'),
      ('driver_phone', 'Driver ka phone'),
      ('km', 'Distance km (aapka number, ho to)'),
      ('toll', 'Toll (aapka number, ho to)'),
      ('dest_state', 'Kis rajya mein (MP, GJ...)'),
      ('ref', 'LR / order no'),
    ], ok: 'Plan karo');
    if (f == null || (f['origin'] ?? '').isEmpty || (f['destination'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    body['items'] = _parseItems(f['items'] ?? '');
    if (f['km'] != null) body['km'] = _n(f['km']);
    if (f['toll'] != null) body['toll'] = _n(f['toll']);
    final r = await _run('POST', '/api/fleet/trips', body);
    final t = _m(r?['trip']);
    if (t.isNotEmpty && mounted) _showTrip(t);
  }

  void _showTrip(Map<String, dynamic> t) => showModalBottomSheet(
        context: context,
        backgroundColor: C.bgBottom,
        isScrollControlled: true,
        builder: (_) => Padding(padding: const EdgeInsets.all(16), child: SingleChildScrollView(child: FleetTripCard(app: widget.app, data: {'trip': t}))),
      ).then((_) => _load());

  Future<void> _importFuel() async {
    final files = await pickAttachmentsOfType(context, FileType.any);
    if (files.isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/fleet/fuel/import', files.first.name, files.first.bytes);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _vehicleTile(Map<String, dynamic> v) {
    final bad = _strs(v['papers_bad']);
    final due = _strs(v['papers_due']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _openVehicle(_s(v['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: bad.isNotEmpty ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.local_shipping_rounded, color: C.accent, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(_s(v['reg']), style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(v['status']), fg: _s(v['status']) == 'active' ? C.ok : C.warn),
            ]),
            Text(
                [
                  _s(v['type_label']),
                  if (v['capacity_t'] != null) '${v['capacity_t']} t',
                  if (v['kmpl'] != null) '${v['kmpl']} km/l',
                  if (_s(v['driver']).isNotEmpty) _s(v['driver']),
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (bad.isNotEmpty) Text('Rukawat: ${bad.join(', ')}', style: const TextStyle(color: C.bad, fontSize: 12.5)),
            if (due.isNotEmpty) Text('Jaldi: ${due.join(', ')}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
          ]),
        ),
      ),
    );
  }

  Widget _tripTile(Map<String, dynamic> t) {
    final block = _strs(_m(t['checks'])['block']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _showTrip(t),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: block.isNotEmpty ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                  child: Text('${_s(t['number'])} · ${_s(t['origin'])} → ${_s(t['destination'])}',
                      style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(t['status_label'])),
            ]),
            Text(
                [
                  _s(t['day']),
                  if (_s(t['vehicle']).isNotEmpty) _s(t['vehicle']),
                  if (t['km'] != null) '${t['km']} km',
                  if (_s(t['driver']).isNotEmpty) _s(t['driver']),
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (block.isNotEmpty) Text(block.first, style: const TextStyle(color: C.bad, fontSize: 12.5)),
          ]),
        ),
      ),
    );
  }

  Widget _today() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: GradientButton(label: 'Nayi trip', icon: Icons.route_rounded, height: 46, onTap: _busy ? null : _newTrip)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Diesel sheet', icon: Icons.local_gas_station_rounded, onTap: _busy ? null : _importFuel)),
      ]),
      const SizedBox(height: 16),
      for (final x in _list(day['waiting'])) ...[
        FleetSpendCard(app: widget.app, data: {'spend': x}, onDone: _load),
        const SizedBox(height: 8),
      ],
      if (_list(day['trips']).isNotEmpty) ...[const Caption('AAJ KI TRIPS'), for (final t in _list(day['trips'])) _tripTile(t)],
      if (_list(day['expired']).isNotEmpty || _list(day['due']).isNotEmpty) ...[
        const Caption('KAAGAZ'),
        for (final d in [..._list(day['expired']), ..._list(day['due'])])
          ListTile(
            dense: true,
            leading: Icon(Icons.description_rounded, color: _docColor(_s(d['state']))),
            title: Text('${_s(d['vehicle'])} · ${_s(d['label'])}'),
            subtitle: Text(_s(d['state']) == 'expired' ? 'Khatam: ${_s(d['expires'])}' : '${_s(d['days_left'])} din baaki (${_s(d['expires'])})'),
            onTap: () => _openVehicle(_s(d['vehicle_id'])),
          ),
      ],
      if (_list(day['service']).isNotEmpty) ...[
        const Caption('SERVICE'),
        for (final x in _list(day['service']))
          ListTile(
              dense: true,
              leading: Icon(Icons.build_rounded, color: _s(x['state']) == 'late' ? C.bad : C.warn),
              title: Text('${_s(x['vehicle'])} · ${_s(x['item'])}'),
              subtitle: Text(_s(x['why']))),
      ],
      if (_list(day['fuel_flags']).isNotEmpty) ...[
        const Caption('DIESEL KE ISHAARE'),
        for (final x in _list(day['fuel_flags']))
          ListTile(
              dense: true,
              leading: const Icon(Icons.warning_amber_rounded, color: C.warn),
              title: Text('${_s(x['vehicle'])} · ${_s(x['day'])}'),
              subtitle: Text(_list(x['flags']).map((f) => _s(f['say'])).join(' '))),
      ],
      if (_list(day['idle']).isNotEmpty) ...[
        const Caption('KHADI GAADIYAN'),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final x in _list(day['idle'])) Pill('${_s(x['vehicle'])}${x['days'] != null ? ' · ${x['days']} din' : ''}', fg: C.warn),
        ]),
      ],
    ]);
  }

  Widget _vehiclesTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Nayi gaadi jodo', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _addVehicle),
        const SizedBox(height: 12),
        for (final v in _list(_d?['vehicles'])) _vehicleTile(v),
        if (_list(_d?['vehicles']).isEmpty) const Text('Abhi koi gaadi nahi. Number se jodiye.', style: TextStyle(color: C.muted)),
      ]);

  Widget _tripsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Nayi trip / load plan', icon: Icons.route_rounded, height: 46, onTap: _busy ? null : _newTrip),
        const SizedBox(height: 12),
        for (final t in _list(_d?['trips'])) _tripTile(t),
      ]);

  Widget _spendTab() => ListView(padding: const EdgeInsets.all(16), children: [
        const Caption('KHARCHE (AAPKI HAAN SE)'),
        for (final x in _list(_d?['spends'])) ...[FleetSpendCard(app: widget.app, data: {'spend': x}, onDone: _load), const SizedBox(height: 8)],
        if (_list(_d?['spends']).isEmpty) const Text('Koi kharcha card nahi.', style: TextStyle(color: C.muted)),
        const SizedBox(height: 12),
        const Caption('COST PER KM (30 DIN)'),
        for (final r in _list(_cost?['vehicles']))
          ListTile(
            dense: true,
            title: Text(_s(r['vehicle'])),
            subtitle: Text([
              if (r['km'] != null) '${r['km']} km',
              '₹${_s(r['total'])}',
              if (r['kmpl'] != null) '${r['kmpl']} km/l',
              'khadi ${_s(r['idle_days'])} din',
            ].join(' · ')),
            trailing: Text(r['per_km'] == null ? '—' : '₹${r['per_km']}/km', style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
        const SizedBox(height: 8),
        GlassButton(label: 'Excel register', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run('POST', '/api/fleet/register')),
      ]);

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Aapke rate aur niyam', const [
      ('business', 'Business ka naam'),
      ('home_state', 'Ghar ka rajya (MH...)'),
      ('diesel_rate', 'Diesel rate ₹/litre (aapka)'),
      ('petrol_rate', 'Petrol rate ₹/litre'),
      ('cng_rate', 'CNG rate ₹/kg'),
      ('avg_speed', 'Plan ki speed km/h (ho to)'),
      ('idle_days', 'Kitne din khadi = idle'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('rules', 'Aapke niyam'),
    ], ok: 'Save', initial: {for (final e in st.entries) if (e.value != null && e.value is! Map) e.key: '${e.value}'});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['diesel_rate', 'petrol_rate', 'cng_rate', 'avg_speed', 'idle_days']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _run('PUT', '/api/fleet/settings', body);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['business']).isEmpty ? 'Fleet' : _s(st['business']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Diesel: ${st['diesel_rate'] == null ? 'rate nahi diya' : '₹${st['diesel_rate']}/L'} · Subah ${_s(st['morning_time'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('HOOLA KABHI NAHI'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
      const SizedBox(height: 12),
      const Caption('ECHALLAN DEKHNA (AAP KHUD)'),
      for (final t in _strs(_d?['echallan_steps'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
      GlassButton(label: 'eChallan kholo', icon: Icons.open_in_new_rounded, onTap: () => Native.openExternal(url: 'https://echallan.parivahan.gov.in/')),
      const SizedBox(height: 12),
      const Caption('VAHAN / MPARIVAHAN'),
      for (final t in _strs(_d?['vahan_steps'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
      GlassButton(label: 'Vahan kholo', icon: Icons.open_in_new_rounded, onTap: () => Native.openExternal(url: 'https://vahan.parivahan.gov.in/vahanservice/')),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Aaj', 'Gaadiyan', 'Trips', 'Kharcha', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Fleet manager'),
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
                  child: switch (_tab) { 0 => _today(), 1 => _vehiclesTab(), 2 => _tripsTab(), 3 => _spendTab(), _ => _rulesTab() },
                ),
        ),
      ]),
    );
  }
}

class FleetVehiclePage extends StatefulWidget {
  const FleetVehiclePage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<FleetVehiclePage> createState() => _FleetVehiclePageState();
}

class _FleetVehiclePageState extends State<FleetVehiclePage> {
  Map<String, dynamic>? _v;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', '/api/fleet/vehicles/${widget.id}'));
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  String get _vid => _s(_v?['id']).isEmpty ? widget.id : _s(_v?['id']);

  Future<void> _post(String sub, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    await _call(context, widget.app, 'POST', '/api/fleet/vehicles/$_vid/$sub', body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _doc(Map<String, dynamic> d) async {
    final f = await _form(context, _s(d['label']), const [
      ('expires', 'Expiry (kaagaz par jo likha, DD-MM-YYYY)'),
      ('issued', 'Issue / renewal date'),
      ('number', 'Number'),
      ('issuer', 'Kisne diya (insurer / RTO)'),
    ], ok: 'Save', initial: {'expires': d['guess'] == true ? '' : _s(d['expires']), 'number': _s(d['number']), 'issuer': _s(d['issuer'])});
    if (f == null) return;
    await _post('docs', {'kind': _s(d['kind']), ...f});
  }

  Future<void> _fuel() async {
    final f = await _form(context, 'Diesel / fuel', const [
      ('litres', 'Litre'),
      ('amount', 'Rupaye'),
      ('odo', 'Odometer (km)'),
      ('station', 'Pump'),
      ('day', 'Taarikh (khaali = aaj)'),
    ], ok: 'Darj karo');
    if (f == null || f['litres'] == null) return;
    await _post('fuel', {'litres': _n(f['litres']), 'amount': _n(f['amount']), 'odo': _n(f['odo']), 'station': f['station'] ?? '', 'day': f['day'] ?? ''});
  }

  Future<void> _serviceDone() async {
    final f = await _form(context, 'Service ho gayi', const [
      ('items', 'Kya kiya (comma se; "all" = sab)'),
      ('odo', 'Odometer'),
      ('amount', 'Kitna laga (aapne diya)'),
      ('workshop', 'Workshop'),
    ], ok: 'Darj karo');
    if (f == null) return;
    await _post('service_done', {
      'items': (f['items'] ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
      'odo': _n(f['odo']),
      'amount': _n(f['amount']),
      'workshop': f['workshop'] ?? ''
    });
  }

  Future<void> _tyre() async {
    final f = await _form(context, 'Naya tyre', const [
      ('position', 'Position (front-left, rear-2-outer...)'),
      ('brand', 'Brand'),
      ('serial', 'Serial'),
      ('odo', 'Odometer'),
      ('life_km', 'Kitne km chalna chahiye (aapka andaaza)'),
    ], ok: 'Darj karo');
    if (f == null || (f['position'] ?? '').isEmpty) return;
    await _post('tyre', {...f, 'odo': _n(f['odo']), 'life_km': _n(f['life_km'])});
  }

  Future<void> _breakdown() async {
    final f = await _form(context, 'Breakdown', const [('what', 'Kya hua'), ('place', 'Kahan'), ('hours', 'Kitne ghante ruki')], ok: 'Darj karo');
    if (f == null || (f['what'] ?? '').isEmpty) return;
    await _post('breakdown', {...f, 'hours': _n(f['hours'])});
  }

  Future<void> _challan() async {
    final f = await _form(context, 'Challan (eChallan par dekha)', const [
      ('number', 'Challan number'),
      ('amount', 'Rakam'),
      ('offence', 'Kis baat ka'),
      ('day', 'Taarikh'),
    ], ok: 'Darj karo');
    if (f == null) return;
    await _post('challan', {...f, 'amount': _n(f['amount'])});
  }

  Future<void> _spend({String kind = 'other', String what = '', String link = ''}) async {
    final f = await _form(context, 'Kharche ka card', const [
      ('kind', 'Kis cheez ka: service / tyre / permit / tax / insurance / challan / repair'),
      ('what', 'Kya'),
      ('amount', 'Rakam (bill / portal se)'),
      ('vendor', 'Kisko (workshop / dukaan)'),
    ], ok: 'Card banao', initial: {'kind': kind, 'what': what});
    if (f == null || _n(f['amount']) == null) return;
    setState(() => _busy = true);
    await _call(context, widget.app, 'POST', '/api/fleet/spends',
        {'vehicle': _vid, 'kind': f['kind'] ?? kind, 'what': f['what'] ?? what, 'amount': _n(f['amount']), 'vendor': f['vendor'] ?? '', 'link_id': link});
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(v == null ? 'Gaadi' : _s(v['reg']))),
      body: v == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(v['type_label'])} · ${_s(v['make'])} ${_s(v['model'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text(
                        [
                          if (v['capacity_t'] != null) '${v['capacity_t']} t',
                          if (v['capacity_cbm'] != null) '${v['capacity_cbm']} cbm',
                          if (v['odo'] != null) 'odo ${v['odo']}',
                          if (v['kmpl'] != null) '${v['kmpl']} km/l',
                          _s(v['fuel']),
                        ].join(' · '),
                        style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  ]),
                ),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(label: 'Diesel', icon: Icons.local_gas_station_rounded, onTap: _fuel, height: 40),
                  GlassButton(label: 'Service hui', icon: Icons.build_rounded, onTap: _serviceDone, height: 40),
                  GlassButton(label: 'Tyre', icon: Icons.tire_repair_rounded, onTap: _tyre, height: 40),
                  GlassButton(label: 'Breakdown', icon: Icons.car_crash_rounded, onTap: _breakdown, height: 40),
                  GlassButton(label: 'Challan', icon: Icons.receipt_long_rounded, onTap: _challan, height: 40),
                  GlassButton(label: 'Kharcha card', icon: Icons.payments_rounded, onTap: () => _spend(), height: 40, color: C.accent),
                ]),
                const SizedBox(height: 16),
                const Caption('KAAGAZ'),
                for (final d in _list(v['docs']))
                  ListTile(
                    dense: true,
                    leading: Icon(Icons.description_rounded, color: _docColor(_s(d['state']))),
                    title: Text(_s(d['label'])),
                    subtitle: Text(switch (_s(d['state'])) {
                      'missing' => 'Expiry darj nahi: tap karke likhiye',
                      'expired' => 'Khatam ${_s(d['expires'])}',
                      'not_needed' => 'Zaroori nahi',
                      'note' => _s(d['notes']).isEmpty ? 'Balance note' : _s(d['notes']),
                      _ => '${_s(d['expires'])}${d['guess'] == true ? ' (andaaza)' : ''} · ${_s(d['days_left'])} din',
                    }),
                    trailing: _s(d['state']) == 'expired' || _s(d['state']) == 'due'
                        ? IconButton(
                            tooltip: 'Renewal ka kharcha card',
                            icon: const Icon(Icons.payments_rounded, color: C.accent),
                            onPressed: () => _spend(
                                kind: switch (_s(d['kind'])) {
                                  'national_permit' || 'state_permit' => 'permit',
                                  'road_tax' => 'tax',
                                  'insurance' => 'insurance',
                                  'fitness' => 'fitness',
                                  'puc' => 'puc',
                                  _ => 'other',
                                },
                                what: '${_s(d['label'])} renewal'))
                        : null,
                    onTap: () => _doc(d),
                  ),
                const SizedBox(height: 8),
                const Caption('SERVICE'),
                for (final s in _list(v['service']))
                  ListTile(
                    dense: true,
                    leading: Icon(Icons.build_circle_rounded,
                        color: switch (_s(s['state'])) { 'late' => C.bad, 'due' => C.warn, 'ok' => C.ok, _ => C.faint }),
                    title: Text('${_s(s['item'])}${s['starter'] == true ? ' (starter)' : ''}'),
                    subtitle: Text(_s(s['why'])),
                  ),
                if (_list(v['tyres']).isNotEmpty) ...[
                  const Caption('TYRE'),
                  for (final t in _list(v['tyres']).where((t) => _s(t['status']) == 'fitted'))
                    ListTile(
                      dense: true,
                      leading: Icon(Icons.tire_repair_rounded, color: t['due'] == true ? C.warn : C.chip),
                      title: Text('${_s(t['position'])} · ${_s(t['brand'])}'),
                      subtitle: Text(t['km_run'] == null ? '' : '${t['km_run']} km chala${t['life_km'] != null ? ' / ${t['life_km']}' : ''}'),
                    ),
                ],
                const Caption('DIESEL'),
                for (final f in _list(v['fuel']))
                  ListTile(
                    dense: true,
                    leading: Icon(Icons.local_gas_station_rounded, color: _list(f['flags']).isEmpty ? C.chip : C.warn),
                    title: Text('${_s(f['day'])} · ${_s(f['litres'])} L${f['amount'] != null ? ' · ₹${f['amount']}' : ''}'),
                    subtitle: Text([
                      if (f['odo'] != null) 'odo ${f['odo']}',
                      if (f['kmpl'] != null) '${f['kmpl']} km/l',
                      ..._list(f['flags']).map((x) => _s(x['say'])),
                    ].join(' · ')),
                  ),
                const Caption('LOG'),
                for (final e in _list(v['events']))
                  ListTile(
                    dense: true,
                    title: Text('${_s(e['day'])} · ${_s(e['kind'])} · ${_s(e['what'])}'),
                    subtitle: Text([if (e['amount'] != null) '₹${e['amount']}', _s(e['status']), _s(e['by'])].join(' · ')),
                    trailing: _s(e['kind']) == 'challan' && _s(e['status']) == 'open'
                        ? TextButton(
                            onPressed: () => _spend(kind: 'challan', what: 'Challan ${_s(_m(e['data'])['number'])}', link: _s(e['id'])),
                            child: const Text('Card'))
                        : (_s(e['kind']) == 'breakdown' && _s(e['status']) == 'open'
                            ? TextButton(
                                onPressed: () async {
                                  await _call(context, widget.app, 'POST', '/api/fleet/events/${_s(e['id'])}/close', {});
                                  await _load();
                                },
                                child: const Text('Theek hui'))
                            : null),
                  ),
              ]),
            ),
    );
  }
}

/// fleet_spend: a spend that waits for HER tap (fingerprint for money once a phone key is set up). Also in calls.
class FleetSpendCard extends StatefulWidget {
  const FleetSpendCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<FleetSpendCard> createState() => _FleetSpendCardState();
}

class _FleetSpendCardState extends State<FleetSpendCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['spend']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/fleet/spends/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Kharche ki haan' : _s(show['title']),
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
    final id = _s(_x['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyon nahi', const [('reason', 'Wajah (aapke liye)')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_x['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/fleet/spends/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/fleet/spends/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() => _x = _m(m['spend']).isEmpty ? _x : _m(m['spend']));
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _paid() async {
    final f = await _form(context, 'Maine de diya', const [('amount', 'Kitna diya'), ('ref', 'UTR / receipt no (ho to)')],
        initial: {'amount': _s(_x['amount'])});
    if (f == null) return;
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', '/api/fleet/spends/${_s(_x['id'])}/done', body: {'amount': _n(f['amount']), 'ref': f['ref'] ?? ''}));
      if (mounted) {
        setState(() => _x = _m(m['spend']).isEmpty ? _x : _m(m['spend']));
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
    final x = _x;
    final st = _s(x['status']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.payments_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(x['number'])} · ${_s(x['kind_label'])} ${_s(x['amount_text'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'maana', 'done' => 'diya', 'rejected' => 'nahi', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' ? C.bad : C.ok)),
        ]),
        if (_s(x['vehicle']).isNotEmpty) Text('Gaadi: ${_s(x['vehicle'])}', style: const TextStyle(fontSize: 12.5)),
        Text(_s(x['what']), style: const TextStyle(fontSize: 13)),
        if (_s(x['vendor']).isNotEmpty) Text('Kisko: ${_s(x['vendor'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final c in _strs(x['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (_s(x['where']).isNotEmpty) Text(_s(x['where']), style: const TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, maana', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved')
          GlassButton(label: 'Maine de diya', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : _paid),
        const Text('Hoola khud paise nahi deta; aap khud dijiye.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// fleet_trip: a planned trip with load fit, papers, estimate. Also in calls.
class FleetTripCard extends StatelessWidget {
  const FleetTripCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  Future<void> _status(BuildContext context, String id, String status) async {
    final f = await _form(context, status == 'started' ? 'Trip shuru' : 'Trip poori', const [('odo', 'Odometer (km)')], ok: 'Haan');
    if (f == null || !context.mounted) return;
    await _call(context, app, 'POST', '/api/fleet/trips/$id/status', {'status': status, 'odo': _n(f['odo'])});
  }

  Future<void> _assign(BuildContext context, String id, List<String> suggest) async {
    final f = await _form(context, 'Gaadi aur driver', const [('vehicle', 'Gaadi number'), ('driver', 'Driver'), ('driver_phone', 'Driver ka phone')],
        ok: 'Tay karo', initial: {'vehicle': suggest.isEmpty ? '' : suggest.first});
    if (f == null || !context.mounted) return;
    await _call(context, app, 'POST', '/api/fleet/trips/$id/assign', f);
  }

  @override
  Widget build(BuildContext context) {
    final t = _m(data['trip']);
    final ch = _m(t['checks']);
    final est = _m(t['estimate']);
    final fit = _m(ch['fit']);
    final split = _m(ch['split']);
    final suggest = _list(ch['suggest']).map((x) => _s(x['vehicle'])).toList();
    final st = _s(t['status']);
    return Glass(
      border: _strs(ch['block']).isNotEmpty ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.route_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(t['number'])} · ${_s(t['origin'])} → ${_s(t['destination'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(t['status_label'])),
        ]),
        Text(
            [
              _s(t['day']),
              if (t['km'] != null) '${t['km']} km${_s(t['km_source']) == 'maps' ? ' (Maps)' : ''}',
              if (_s(t['vehicle']).isNotEmpty) _s(t['vehicle']),
              if (_s(t['driver']).isNotEmpty) _s(t['driver']),
            ].join(' · '),
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (fit.isNotEmpty)
          Text('Load: ${_s(fit['weight_kg'])} kg${fit['weight_pct'] != null ? ' (${fit['weight_pct']}% wazan)' : ''}',
              style: const TextStyle(fontSize: 12.5)),
        for (final b in _strs(ch['block'])) Text('⛔ $b', style: const TextStyle(fontSize: 12.5, color: C.bad)),
        for (final w in _strs(ch['warn'])) Text('⚠ $w', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (suggest.isNotEmpty && _s(t['vehicle']).isEmpty) Text('Sahi gaadi: ${suggest.join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.ok)),
        if (split.isNotEmpty)
          Text('Baantkar: ${_list(split['plan']).map((p) => '${_s(p['vehicle'])} ${_s(p['weight_kg'])} kg').join('; ')}',
              style: const TextStyle(fontSize: 12.5)),
        if (est['total_rs'] != null)
          Text('Andaaza (aapke rate): diesel ₹${_s(est['fuel_rs'])} + toll ₹${_s(est['toll_rs'])} = ₹${_s(est['total_rs'])}',
              style: const TextStyle(fontSize: 12.5))
        else if (_strs(est['missing']).isNotEmpty)
          Text('Andaaza ke liye chahiye: ${_strs(est['missing']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (st == 'planned' || st == 'assigned')
            GlassButton(label: 'Gaadi / driver', height: 38, onTap: () => _assign(context, _s(t['id']), suggest)),
          if (st == 'assigned') GlassButton(label: 'Shuru', height: 38, onTap: () => _status(context, _s(t['id']), 'started')),
          if (st == 'started') GlassButton(label: 'Poori', height: 38, onTap: () => _status(context, _s(t['id']), 'done')),
          if (_s(t['driver_phone']).isNotEmpty)
            GlassButton(label: 'Driver ko call', icon: Icons.call_rounded, height: 38, onTap: () => Native.openExternal(url: 'tel:${_s(t['driver_phone'])}')),
        ]),
      ]),
    );
  }
}

/// fleet_alert: a paper / service / diesel / breakdown alert. Also in calls.
class FleetAlertCard extends StatelessWidget {
  const FleetAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final k = _s(data['kind']);
    final icon = switch (k) {
      'doc' => Icons.description_rounded,
      'service' => Icons.build_rounded,
      'fuel' || 'fuel_import' => Icons.local_gas_station_rounded,
      'breakdown' => Icons.car_crash_rounded,
      _ => Icons.local_shipping_rounded,
    };
    return Glass(
      border: C.warn,
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: C.warn),
        const SizedBox(width: 10),
        Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.35))),
      ]),
    );
  }
}

/// fleet_day: the morning fleet note. Not in calls.
class FleetDayCard extends StatelessWidget {
  const FleetDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.wb_sunny_rounded, color: C.accent),
            SizedBox(width: 8),
            Text('Aaj ka fleet note', style: TextStyle(fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.35)),
          const SizedBox(height: 8),
          GlassButton(
              label: 'Fleet kholo',
              height: 38,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FleetScreen(app: app)))),
        ]),
      );
}
