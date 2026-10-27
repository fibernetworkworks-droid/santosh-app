/// Profile > Homestay Sahayak: Hoola as a homestay / B&B / farm stay / villa host's coworker (1-6 rooms).
/// Aaj (arrivals, departures, in house, Form C, cleaning, cards waiting) · Calendar (rooms x nights) · Booking (new enquiry, OTA mail
/// she pastes, iCal file she exports, block dates) · Mehmaan (guests, IDs only in the Pehchaan Locker) · Hisaab (month earnings,
/// occupancy, register) · Niyam (her rates, menu, policy, house rules, registration checklist, her calendar link for OTAs).
/// Every message to a guest, every cancel / refund / spend runs only after HER tap (fingerprint for money once a phone key is set
/// up). A room is never booked twice for a night. Hoola never logs in to an OTA and never takes or pays money.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());
String _rs(dynamic v) {
  final n = v is num ? v : num.tryParse(_s(v));
  if (n == null || n == 0) return '';
  return '₹${n.toStringAsFixed(n == n.roundToDouble() ? 0 : 2)}';
}

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

const _multi = {'text', 'address', 'reason', 'rules', 'house_rules', 'checkin_info', 'policy', 'menu', 'mail', 'notes'};

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
                maxLines: _multi.contains(k) ? (k == 'mail' ? 8 : 3) : 1),
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

Color _statusColor(String st) => switch (st) {
      'confirmed' => C.ok,
      'checked_in' => C.teal,
      'hold' => C.warn,
      'blocked' => C.faint,
      'cancelled' || 'no_show' => C.bad,
      _ => C.chip,
    };

class HomestayScreen extends StatefulWidget {
  const HomestayScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<HomestayScreen> createState() => _HomestayScreenState();
}

class _HomestayScreenState extends State<HomestayScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _cal;
  Map<String, dynamic>? _rep;
  List<Map<String, dynamic>> _guests = const [];
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/homestay'));
      final cal = _m(await widget.app.api!.call('GET', '/api/homestay/calendar', query: {'days': '14'}));
      if (mounted) setState(() {
        _d = d;
        _cal = cal;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _loadGuests() async {
    try {
      final g = _m(await widget.app.api!.call('GET', '/api/homestay/guests'));
      if (mounted) setState(() => _guests = _list(g['guests']));
    } catch (_) {}
  }

  Future<void> _loadReport([String month = '']) async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/homestay/report', query: month.isEmpty ? null : {'month': month}));
      if (mounted) setState(() => _rep = r);
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

  void _openBooking(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => HomestayBookingPage(app: widget.app, id: id)))
      .then((_) => _load());

  // ---------------------------------------------------------------- actions
  Future<void> _newBooking() async {
    final f = await _form(context, 'Nayi booking (enquiry)', const [
      ('room', 'Kamra (R-01 / naam; do kamre: "R-01, R-02")'),
      ('check_in', 'Check-in (DD-MM-YYYY)'),
      ('check_out', 'Check-out (DD-MM-YYYY)'),
      ('name', 'Mehmaan ka naam'),
      ('phone', 'Mobile'),
      ('adults', 'Bade log'),
      ('children', 'Bachche'),
      ('addons', 'Khaana / extra: "breakfast, dinner"'),
      ('notes', 'Note'),
    ], ok: 'Hold karo');
    if (f == null || (f['room'] ?? '').isEmpty) return;
    final body = <String, dynamic>{
      'room': f['room'],
      'check_in': f['check_in'] ?? '',
      'check_out': f['check_out'] ?? '',
      'name': f['name'] ?? '',
      'phone': f['phone'] ?? '',
      'adults': _n(f['adults']) ?? 2,
      'children': _n(f['children']) ?? 0,
      'notes': f['notes'] ?? '',
      'addons': (f['addons'] ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
    };
    if ((f['room'] ?? '').contains(',')) body['rooms'] = f['room']!.split(',').map((e) => e.trim()).toList();
    final r = await _run('POST', '/api/homestay/bookings', body);
    final id = _s(_m(r?['booking'])['id']);
    if (id.isNotEmpty && mounted) _openBooking(id);
  }

  Future<void> _otaMail() async {
    final f = await _form(context, 'OTA ka mail paste kijiye', const [
      ('mail', 'Airbnb / Booking.com / MakeMyTrip / Agoda mail ka poora text'),
      ('room', 'Kamra (mail mein naam na ho to)'),
    ], ok: 'Padho');
    if (f == null || (f['mail'] ?? '').isEmpty) return;
    await _run('POST', '/api/homestay/ota_email', {'text': f['mail'], 'room': f['room'] ?? ''});
  }

  Future<void> _icalFile() async {
    final rooms = _list(_d?['rooms']);
    if (rooms.isEmpty) return _snack(context, 'Pehle kamra jodiye (Niyam).');
    final f = await _form(context, 'Calendar file (.ics)', const [
      ('room', 'Kis kamre ki file (R-01 / naam)'),
      ('source', 'airbnb / booking / mmt / agoda (khaali = file se)'),
    ], ok: 'File chuno');
    if (f == null || (f['room'] ?? '').isEmpty) return;
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['ics', 'txt']);
    final file = res?.files.single;
    if (file == null || file.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/homestay/ical', file.name, file.bytes!,
          fields: {'room': f['room']!, 'source': f['source'] ?? ''}, tries: 1);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _block() async {
    final f = await _form(context, 'Din band karo', const [
      ('room', 'Kamra'),
      ('start', 'Kab se (DD-MM-YYYY)'),
      ('end', 'Kab tak (check-out jaisa)'),
      ('note', 'Kyon (repair / ghar ka kaam)'),
    ], ok: 'Band karo');
    if (f == null || (f['room'] ?? '').isEmpty) return;
    await _run('POST', '/api/homestay/blocks', f);
  }

  Future<void> _addRoom() async {
    final f = await _form(context, 'Naya kamra', const [
      ('name', 'Naam (Neem room / Cottage 1)'),
      ('beds', 'Bed (1 double + 1 single)'),
      ('base_guests', 'Daam mein kitne log (2)'),
      ('max_guests', 'Zyada se zyada log (3)'),
      ('base_rate', 'Daam / raat (aapka)'),
      ('weekend_rate', 'Shukra / Shani raat ka daam (ho to)'),
      ('extra_person', 'Extra mehmaan / raat'),
      ('ota_names', 'OTA par naam (comma se)'),
    ], ok: 'Jodo');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    for (final k in ['base_guests', 'max_guests', 'base_rate', 'weekend_rate', 'extra_person']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    if (f['ota_names'] != null) body['ota_names'] = f['ota_names']!.split(',').map((e) => e.trim()).toList();
    await _run('POST', '/api/homestay/rooms', body);
  }

  Future<void> _editRoom(Map<String, dynamic> r) async {
    final f = await _form(context, '${_s(r['number'])} ${_s(r['name'])}', const [
      ('base_rate', 'Daam / raat'),
      ('weekend_rate', 'Weekend raat'),
      ('extra_person', 'Extra mehmaan / raat'),
      ('max_guests', 'Zyada se zyada log'),
    ], initial: {
      'base_rate': _s(r['base_rate']),
      'weekend_rate': _s(r['weekend_rate']),
      'extra_person': _s(r['extra_person']),
      'max_guests': _s(r['max_guests']),
    }, ok: 'Save');
    if (f == null) return;
    await _run('PATCH', '/api/homestay/rooms/${_s(r['id'])}', {for (final e in f.entries) e.key: _n(e.value)});
  }

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    const keys = [
      ('business', 'Homestay ka naam'),
      ('host_name', 'Aapka naam'),
      ('phone', 'Aapka mobile'),
      ('address', 'Pata'),
      ('state', 'Rajya code (MH / GA / KL / HP ...)'),
      ('pin', 'PIN code'),
      ('map_link', 'Google Maps link (https://...)'),
      ('upi_id', 'UPI ID (advance / balance aapke UPI mein)'),
      ('gstin', 'GSTIN (ho to)'),
      ('checkin_time', 'Check-in samay (12:00)'),
      ('checkout_time', 'Check-out samay (11:00)'),
      ('advance_pct', 'Advance % (jaise 30)'),
      ('policy', 'Cancellation policy: "7 din pehle 100%, 2 din pehle 50%, uske baad kuch nahi"'),
      ('menu', 'Menu: "breakfast 200, dinner 350, bonfire 500"'),
      ('house_rules', 'Ghar ke niyam'),
      ('checkin_info', 'Aane ka raasta / parking / chaabi (password nahi)'),
      ('review_link', 'Google review link (https://...)'),
      ('morning_time', 'Subah ka note (HH:MM)'),
    ];
    final f = await _form(context, 'Niyam', keys, initial: {
      for (final (k, _) in keys) k: k == 'policy' ? '' : (k == 'menu' ? '' : _s(st[k])),
    }, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['advance_pct'] != null) body['advance_pct'] = _n(f['advance_pct']);
    await _run('PUT', '/api/homestay/settings', body);
  }

  Future<void> _regItem(Map<String, dynamic> it) async {
    final f = await _form(context, _s(it['text']), const [('ref', 'Number / ref (ho to)')], ok: 'Ho gaya');
    if (f == null) return;
    await _run('PUT', '/api/homestay/registration', {'item': it['id'], 'done': true, 'ref': f['ref'] ?? ''});
  }

  Future<void> _regNumber() async {
    final reg = _m(_d?['registration']);
    final f = await _form(context, 'Homestay registration', const [
      ('number', 'Registration number'),
      ('valid_to', 'Kab tak valid (DD-MM-YYYY)'),
    ], initial: {'number': _s(reg['number']), 'valid_to': _s(reg['valid_to'])}, ok: 'Save');
    if (f == null) return;
    await _run('PUT', '/api/homestay/registration', f);
  }

  Future<void> _addGuest() async {
    final f = await _form(context, 'Mehmaan', const [
      ('name', 'Naam'),
      ('phone', 'Mobile (videshi: +desh code)'),
      ('country', 'Desh (IN = Bharat)'),
      ('aadhaar', 'Aadhaar (Pehchaan Locker mein jayega)'),
      ('passport', 'Passport (videshi; Locker mein)'),
      ('visa', 'Visa / e-Visa number (Locker mein)'),
      ('nationality', 'Nationality (videshi)'),
    ], ok: 'Save');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    if (f['nationality'] != null) body['form_c'] = {'nationality': f['nationality']};
    await _run('POST', '/api/homestay/guests', body);
    await _loadGuests();
  }

  // ---------------------------------------------------------------- tabs
  Widget _bookingTile(Map<String, dynamic> b) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        child: Press(
          onTap: () => _openBooking(_s(b['id'])),
          child: Row(children: [
            Icon(_s(b['source']) == 'direct' ? Icons.bed_rounded : Icons.public_rounded, color: _statusColor(_s(b['status']))),
            const SizedBox(width: 8),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(b['number'])} · ${_s(_m(b['guest'])['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text('${_strs(b['rooms']).join(', ')} · ${_s(b['check_in'])} → ${_s(b['check_out'])} · ${_s(b['source_label'])}',
                    style: const TextStyle(fontSize: 12.5, color: C.muted)),
                if (_rs(b['due']).isNotEmpty) Text('Baaki ${_rs(b['due'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
              ]),
            ),
            Pill(_s(b['status_label']), fg: _statusColor(_s(b['status']))),
          ]),
        ),
      );

  Widget _today() {
    final d = _m(_d?['day']);
    final cards = _list(_d?['cards']);
    final tasks = _list(_d?['tasks']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
      const SizedBox(height: 10),
      if (cards.isNotEmpty) const Caption('AAPKE TAP KA INTEZAAR'),
      for (final c in cards)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: HomestayCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      if (_list(d['arrivals']).isNotEmpty) const Caption('AAJ AA RAHE'),
      for (final b in _list(d['arrivals'])) _bookingTile(b),
      if (_list(d['departures']).isNotEmpty) const Caption('AAJ JA RAHE'),
      for (final b in _list(d['departures'])) _bookingTile(b),
      if (_list(d['in_house']).isNotEmpty) const Caption('GHAR MEIN'),
      for (final b in _list(d['in_house'])) _bookingTile(b),
      if (tasks.isNotEmpty) const Caption('SAFAI / LAUNDRY'),
      for (final t in tasks.take(30))
        Glass(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          child: Row(children: [
            Expanded(
              child: Text('${_s(t['room'])} · ${_s(t['what'])}${_s(t['due']).isEmpty ? '' : ' · ${_s(t['due'])} se pehle'}'
                  '${_s(t['assigned']).isEmpty ? '' : ' · ${_s(t['assigned'])}'}',
                  style: const TextStyle(fontSize: 13)),
            ),
            IconButton(
                onPressed: _busy ? null : () => _run('POST', '/api/homestay/tasks/${_s(t['id'])}', {}),
                icon: const Icon(Icons.check_circle_rounded, color: C.ok)),
          ]),
        ),
    ]);
  }

  Widget _calendarTab() {
    final cal = _m(_cal);
    final start = DateTime.tryParse(_s(cal['start'])) ?? DateTime.now();
    final days = (cal['days'] as num?)?.toInt() ?? 14;
    return ListView(padding: const EdgeInsets.all(14), children: [
      const Caption('AGLE 14 DIN (HAR KAMRA, HAR RAAT)'),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const SizedBox(width: 90),
            for (var i = 0; i < days; i++)
              SizedBox(
                width: 34,
                child: Text('${start.add(Duration(days: i)).day}', textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 11, color: C.faint)),
              ),
          ]),
          for (final r in _list(cal['rooms']))
            Row(children: [
              SizedBox(width: 90, child: Text(_s(r['name']).isEmpty ? _s(r['number']) : _s(r['name']), overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12))),
              for (final cell in _strs(r['nights']))
                Container(
                  width: 30,
                  height: 26,
                  margin: const EdgeInsets.all(2),
                  decoration: BoxDecoration(
                    color: cell.isEmpty ? C.panel : _statusColor(cell.split('|').length > 1 ? cell.split('|')[1] : '').withOpacity(.55),
                    borderRadius: BorderRadius.circular(6),
                  ),
                ),
            ]),
        ]),
      ),
      const SizedBox(height: 10),
      const Text('Hara = pakki · peela = hold · neela = ghar mein · dhundla = band', style: TextStyle(fontSize: 11.5, color: C.faint)),
      const SizedBox(height: 14),
      GlassButton(label: 'Din band karo', icon: Icons.block_rounded, onTap: _busy ? null : _block),
    ]);
  }

  Widget _bookingsTab() {
    final up = _list(_d?['upcoming']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      GradientButton(label: 'Nayi booking / enquiry', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newBooking),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'OTA mail paste karo', icon: Icons.mark_email_read_rounded, height: 42, onTap: _busy ? null : _otaMail),
        GlassButton(label: 'Calendar file (.ics)', icon: Icons.event_note_rounded, height: 42, onTap: _busy ? null : _icalFile),
      ]),
      const SizedBox(height: 6),
      const Text('Hoola kisi OTA mein login nahi karta: aap mail paste kijiye ya OTA se calendar export karke file dijiye. '
          'Ek kamra ek raat do baar kabhi book nahi hota.', style: TextStyle(fontSize: 11.5, color: C.faint)),
      const SizedBox(height: 10),
      if (up.isEmpty) const Text('Abhi koi aane wali booking nahi.', style: TextStyle(color: C.muted)),
      for (final b in up) _bookingTile(b),
    ]);
  }

  Widget _guestsTab() => ListView(padding: const EdgeInsets.all(14), children: [
        GradientButton(label: 'Mehmaan jodo', icon: Icons.person_add_alt_1_rounded, height: 46, onTap: _busy ? null : _addGuest),
        const SizedBox(height: 6),
        const Text('Aadhaar / passport / visa number sirf Pehchaan Locker mein; yahan masked dikhta hai.',
            style: TextStyle(fontSize: 11.5, color: C.faint)),
        const SizedBox(height: 10),
        for (final g in _guests)
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Icon(g['foreign'] == true ? Icons.flight_land_rounded : Icons.person_rounded, color: C.accent),
              const SizedBox(width: 8),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(g['number'])} · ${_s(g['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text([_s(g['phone']), _s(g['country']), ..._list(g['ids']).map((x) => '${_s(x['kind'])} ${_s(x['masked'])}')]
                      .where((x) => x.isNotEmpty)
                      .join(' · '), style: const TextStyle(fontSize: 12.5, color: C.muted)),
                ]),
              ),
              if (g['forgotten'] != true)
                IconButton(
                  tooltip: 'Jaankari mitao (DPDP)',
                  onPressed: _busy ? null : () => _run('POST', '/api/homestay/guests/${_s(g['id'])}/forget').then((_) => _loadGuests()),
                  icon: const Icon(Icons.delete_sweep_rounded, color: C.faint),
                ),
            ]),
          ),
      ]);

  Widget _hisaabTab() {
    final r = _m(_rep);
    return ListView(padding: const EdgeInsets.all(14), children: [
      if (r.isEmpty) const Center(child: CircularProgressIndicator()),
      if (r.isNotEmpty) ...[
        Glass(child: Text(_s(r['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          Pill('Occupancy ${_s(r['occupancy'])}%', fg: C.accent),
          Pill('Kamaai ${_rs(r['revenue'])}', fg: C.ok),
          Pill('ADR ${_rs(r['adr'])}'),
          Pill('RevPAR ${_rs(r['revpar'])}'),
        ]),
        const SizedBox(height: 10),
        const Caption('SOURCE KE HISAAB SE'),
        for (final x in _list(r['by_source']))
          _line(_s(x['source']), '${_s(x['bookings'])} booking · ${_s(x['nights'])} raat · ${_rs(x['revenue'])}'),
        const Caption('KAMRE'),
        for (final x in _list(r['by_room'])) _line(_s(x['room']), '${_s(x['nights'])} raat · ${_s(x['occupancy'])}%'),
        Text(_s(r['note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
      ],
      const SizedBox(height: 12),
      GlassButton(
          label: 'Register + hisaab (Excel)',
          icon: Icons.table_chart_rounded,
          onTap: _busy ? null : () => _run('POST', '/api/homestay/register', {'month': _s(r['month'])})),
    ]);
  }

  Widget _niyamTab() {
    final st = _m(_d?['settings']);
    final reg = _m(_d?['registration']);
    final info = _m(reg['state']);
    final base0 = widget.app.api?.baseUrl ?? '';
    final base = base0.endsWith('/') ? base0.substring(0, base0.length - 1) : base0;
    final link = '$base${_s(st['ical_link'])}';
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['business']).isEmpty ? 'Homestay ka naam abhi nahi' : _s(st['business']),
              style: const TextStyle(fontWeight: FontWeight.w800)),
          _line('UPI', _s(st['upi_effective'])),
          _line('Check-in / out', '${_s(st['checkin_time'])} / ${_s(st['checkout_time'])}'),
          _line('Advance', ((st['advance_pct'] as num?) ?? 0) > 0 ? '${_s(st['advance_pct'])}%' : ''),
          _line('Policy', _s(st['policy_text'])),
          _line('Menu', _m(st['menu']).entries.where((e) => !e.key.endsWith('__per')).map((e) => '${e.key} ₹${e.value}').join(', ')),
          const SizedBox(height: 8),
          GlassButton(label: 'Niyam badlo', icon: Icons.tune_rounded, height: 40, onTap: _busy ? null : _settings),
        ]),
      ),
      const SizedBox(height: 10),
      const Caption('KAMRE AUR DAAM'),
      for (final r in _list(_d?['rooms']))
        Glass(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          child: Press(
            onTap: () => _editRoom(r),
            child: Text('${_s(r['number'])} · ${_s(r['name'])} · ${_rs(r['base_rate']).isEmpty ? 'daam baaki' : _rs(r['base_rate'])}'
                '${_rs(r['weekend_rate']).isEmpty ? '' : ' (weekend ${_rs(r['weekend_rate'])})'} · ${_s(r['max_guests'])} log tak',
                style: const TextStyle(fontSize: 13)),
          ),
        ),
      GlassButton(label: 'Kamra jodo', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : _addRoom),
      const SizedBox(height: 12),
      const Caption('APNA CALENDAR OTA KO (GUEST KA NAAM NAHI JAATA)'),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Yeh link Airbnb / Booking.com ke "Import calendar" mein daaliye: Hoola ki bookings wahan band dikhengi.',
              style: TextStyle(fontSize: 12.5, color: C.muted)),
          const SizedBox(height: 6),
          GlassButton(
              label: 'Link copy karo',
              icon: Icons.copy_rounded,
              height: 40,
              onTap: () {
                Clipboard.setData(ClipboardData(text: link));
                _snack(context, 'Calendar link copy hua.');
              }),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('REGISTRATION (STARTER - RAJYA KA PORTAL AAKHRI SACH)'),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(info['scheme']).isEmpty ? _s(info['note']) : _s(info['scheme']), style: const TextStyle(fontWeight: FontWeight.w700)),
          _line('Number', _s(reg['number'])),
          _line('Valid', _s(reg['valid_to']).isEmpty ? '' : '${_s(reg['valid_to'])} (${_s(reg['days_left'])} din)'),
          for (final n in _strs(info['notes'])) Text('• $n', style: const TextStyle(fontSize: 12, color: C.muted)),
          const SizedBox(height: 6),
          for (final it in _list(reg['items']))
            Row(children: [
              Icon(it['done'] != null ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                  size: 18, color: it['done'] != null ? C.ok : (it['must'] == true ? C.warn : C.faint)),
              const SizedBox(width: 6),
              Expanded(child: Text(_s(it['text']), style: const TextStyle(fontSize: 12.5))),
              if (it['done'] == null) TextButton(onPressed: _busy ? null : () => _regItem(it), child: const Text('Ho gaya')),
            ]),
          GlassButton(label: 'Registration number / valid', height: 40, onTap: _busy ? null : _regNumber),
        ]),
      ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Calendar', 'Booking', 'Mehmaan', 'Hisaab', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Homestay host'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: Column(children: [
        SizedBox(
          height: 44,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(
                    label: Text(tabs[i]),
                    selected: _tab == i,
                    onSelected: (_) {
                      setState(() => _tab = i);
                      if (i == 3) _loadGuests();
                      if (i == 4) _loadReport();
                    }),
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
                    1 => _calendarTab(),
                    2 => _bookingsTab(),
                    3 => _guestsTab(),
                    4 => _hisaabTab(),
                    _ => _niyamTab(),
                  },
                ),
        ),
      ]),
    );
  }
}

/// One booking: dates, rooms, guest, money, checklist (ID, Form C, police), actions, cards.
class HomestayBookingPage extends StatefulWidget {
  const HomestayBookingPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<HomestayBookingPage> createState() => _HomestayBookingPageState();
}

class _HomestayBookingPageState extends State<HomestayBookingPage> {
  Map<String, dynamic>? _b;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/homestay/bookings/${widget.id}'));
      if (mounted) setState(() => _b = _m(r['booking']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _act(String act, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, 'POST', '/api/homestay/bookings/${widget.id}/$act', body ?? {});
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _message() async {
    const kinds = [
      ('confirmation', 'Confirmation'),
      ('checkin_info', 'Aane ki jaankari'),
      ('house_rules', 'Ghar ke niyam'),
      ('payment', 'Payment link'),
      ('review', 'Review request'),
      ('custom', 'Apna message'),
    ];
    final k = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: ListView(shrinkWrap: true, children: [
          for (final (id, label) in kinds) ListTile(title: Text(label), onTap: () => Navigator.pop(c, id)),
        ]),
      ),
    );
    if (k == null) return;
    String text = '';
    if (k == 'custom') {
      final f = await _form(context, 'Message', const [('text', 'Mehmaan ke liye message')], ok: 'Draft');
      if (f == null) return;
      text = f['text'] ?? '';
    }
    await _act('message', {'kind': k, 'text': text});
  }

  Future<void> _received() async {
    final f = await _form(context, 'Paise mile (aapne dekhe)', const [
      ('amount', 'Raqam'),
      ('mode', 'upi / cash / bank / ota'),
      ('ref', 'UTR / ref (aakhri 4 bhi chalega)'),
    ], ok: 'Darj karo');
    if (f == null || _n(f['amount']) == null) return;
    await _act('received', {'amount': _n(f['amount']), 'mode': f['mode'] ?? 'upi', 'ref': f['ref'] ?? ''});
  }

  Future<void> _payLink() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/homestay/bookings/${widget.id}/pay_link'));
      await Clipboard.setData(ClipboardData(text: _s(r['link'])));
      if (mounted) _snack(context, '${_s(r['say'])} Link copy hua.');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _cancel() async {
    final f = await _form(context, 'Cancel (aapki haan ka card)', const [
      ('by', 'Kisne: guest / host'),
      ('reason', 'Wajah'),
      ('refund', 'Wapas raqam (khaali = aapki policy se)'),
    ], ok: 'Card banao');
    if (f == null) return;
    await _act('cancel', {'by': f['by'] ?? 'guest', 'reason': f['reason'] ?? '', if (_n(f['refund']) != null) 'refund': _n(f['refund'])});
  }

  Future<void> _formC() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/homestay/bookings/${widget.id}/form_c'));
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Form C (Form-III) ki jaankari'),
          content: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(_s(r['law']), style: const TextStyle(fontSize: 12, color: C.warn)),
              const SizedBox(height: 6),
              for (final f in _list(r['fields']))
                Text('${_s(f['label'])}: ${f['missing'] == true ? '— baaki' : _s(f['value'])}',
                    style: TextStyle(fontSize: 12.5, color: f['missing'] == true ? C.warn : C.ink)),
              const SizedBox(height: 6),
              for (final s in _strs(r['steps'])) Text('• $s', style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Native.openExternal(url: 'https://indianfrro.gov.in/frro/FormC'), child: const Text('Portal kholo')),
            TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek')),
          ],
        ),
      );
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _formCDone(String stage) async {
    final f = await _form(context, 'Form C ${stage == 'departure' ? '(jaana)' : '(aana)'} ho gaya', const [('ref', 'Form C reference number')],
        ok: 'Darj karo');
    if (f == null) return;
    await _act('form_c_done', {'ref': f['ref'] ?? '', 'stage': stage});
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(b == null ? 'Booking' : _s(b['number']))),
      body: b == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(14), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(
                          child: Text(_s(_m(b['guest'])['name']).isEmpty ? _s(b['source_label']) : _s(_m(b['guest'])['name']),
                              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16))),
                      Pill(_s(b['status_label']), fg: _statusColor(_s(b['status']))),
                    ]),
                    _line('Kamre', _strs(b['rooms']).join(', ')),
                    _line('Taarikh', '${_s(b['check_in'])} → ${_s(b['check_out'])} (${_s(b['nights'])} raat)'),
                    _line('Log', '${_s(b['adults'])} bade, ${_s(b['children'])} bachche'),
                    _line('Source', '${_s(b['source_label'])} ${_s(b['ota_ref'])}'),
                    _line('Kul', _rs(b['total']).isEmpty ? 'daam baaki' : _rs(b['total'])),
                    _line('Advance', _rs(b['advance'])),
                    _line('Mila', _rs(b['paid'])),
                    _line('Baaki', _rs(b['due']), color: C.warn),
                    _line('Wapas dena', _rs((_n(_s(b['refund_due'])) ?? 0) - (_n(_s(b['refunded'])) ?? 0)), color: C.warn),
                    _line('Hold tak', _s(b['hold_until'])),
                    for (final x in _strs(b['missing'])) Text('⚠ $x', style: const TextStyle(fontSize: 12, color: C.warn)),
                    for (final l in _list(_m(b['quote'])['lines']))
                      Text('${_s(l['item'])} · ${_rs(l['amount'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
                    if (_s(_m(b['quote'])['gst_note']).isNotEmpty)
                      Text(_s(_m(b['quote'])['gst_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
                  ]),
                ),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (_s(b['status']) == 'hold') GlassButton(label: 'Pakki (maine baat ki)', height: 40, onTap: _busy ? null : () => _act('confirm')),
                  if (_s(b['status']) == 'confirmed' || _s(b['status']) == 'hold')
                    GradientButton(label: 'Check-in', icon: Icons.login_rounded, height: 40, onTap: _busy ? null : () => _act('checkin', {'id_seen': true})),
                  if (_s(b['status']) == 'checked_in')
                    GradientButton(label: 'Check-out', icon: Icons.logout_rounded, height: 40, onTap: _busy ? null : () => _act('checkout')),
                  GlassButton(label: 'Message draft', icon: Icons.sms_rounded, height: 40, onTap: _busy ? null : _message),
                  GlassButton(label: 'UPI link', icon: Icons.qr_code_rounded, height: 40, onTap: _busy ? null : _payLink),
                  GlassButton(label: 'Paise mile', icon: Icons.payments_rounded, height: 40, onTap: _busy ? null : _received),
                  if (_m(b['guest'])['foreign'] == true) ...[
                    GlassButton(label: 'Form C jaankari', icon: Icons.assignment_ind_rounded, height: 40, onTap: _busy ? null : _formC),
                    GlassButton(label: 'Form C ho gaya', height: 40, onTap: _busy ? null : () => _formCDone('arrival')),
                    if (_s(b['status']) == 'checked_out')
                      GlassButton(label: 'Departure darj', height: 40, onTap: _busy ? null : () => _formCDone('departure')),
                  ],
                  if (_m(b['checklist']).containsKey('police') && _m(_m(b['checklist'])['police'])['done'] != true)
                    GlassButton(label: 'Thane ko bataya', height: 40, onTap: _busy ? null : () => _act('check', {'item': 'police'})),
                  if (_s(b['status']) == 'confirmed' || _s(b['status']) == 'hold')
                    GlassButton(label: 'Cancel', icon: Icons.cancel_rounded, color: C.bad, height: 40, onTap: _busy ? null : _cancel),
                  if (_s(b['status']) == 'blocked') GlassButton(label: 'Kholo', height: 40, onTap: _busy ? null : () => _act('unblock')),
                ]),
                const SizedBox(height: 12),
                if (_list(b['cards']).isNotEmpty) const Caption('CARDS'),
                for (final c in _list(b['cards']).reversed)
                  Padding(padding: const EdgeInsets.only(bottom: 8), child: HomestayCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
                if (_list(b['tasks']).isNotEmpty) const Caption('SAFAI KAAM'),
                for (final t in _list(b['tasks'])) _line(_s(t['what']), '${_s(t['room'])} · ${_s(t['status'])}'),
                if (_list(b['log']).isNotEmpty) const Caption('LOG'),
                for (final l in _list(b['log']).reversed.take(20)) _line(_s(l['at']), _s(l['what'])),
              ]),
            ),
    );
  }
}

/// homestay_card: a message for a guest (sent only by HER tap: own WhatsApp / SMS or the business number) or a cancel / refund /
/// spend card (only HER tap; fingerprint for money once a phone key is active).
class HomestayCardCard extends StatefulWidget {
  const HomestayCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<HomestayCardCard> createState() => _HomestayCardCardState();
}

class _HomestayCardCardState extends State<HomestayCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/homestay/cards/$id/challenge'));
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
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyon nahi', const [('reason', 'Wajah (aapke liye)')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/homestay/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/homestay/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() => _c = _m(m['card']).isEmpty ? _c : _m(m['card']));
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send(String via) async {
    final show = _m(_c['show']);
    setState(() => _busy = true);
    try {
      if (via == 'self') {
        final links = _m(show['links']);
        final link = _s(links['whatsapp']).isNotEmpty ? _s(links['whatsapp']) : _s(links['sms']);
        if (link.isEmpty) throw Exception('Mehmaan ka mobile nahi.');
        if (_strs(show['blanks']).isNotEmpty) throw Exception('Pehle khaali jagah bhariye: ${_strs(show['blanks']).join(', ')}');
        await Native.openExternal(url: link);
      }
      final m = _m(await widget.app.api!.call('POST', '/api/homestay/cards/${_s(_c['id'])}/send', body: {'via': via, 'hash': _s(_c['hash'])}));
      if (mounted) {
        setState(() => _c = _m(m['card']).isEmpty ? _c : _m(m['card']));
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
    final show = _m(_c['show']);
    final f = await _form(context, 'Message badlo', const [('text', 'Message')], initial: {'text': _s(show['text'])}, ok: 'Save');
    if (f == null) return;
    try {
      final m = _m(await widget.app.api!.call('PUT', '/api/homestay/cards/${_s(_c['id'])}', body: {'text': f['text'] ?? ''}));
      if (mounted) setState(() => _c = _m(m['card']).isEmpty ? _c : _m(m['card']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final show = _m(c['show']);
    final st = _s(c['status']);
    final isMsg = _s(c['kind']) == 'message';
    return Glass(
      border: st == 'waiting' ? (isMsg ? C.violet : C.accent) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(isMsg ? Icons.sms_rounded : (c['money'] == true ? Icons.payments_rounded : Icons.gavel_rounded), color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · ${_s(show['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) {
            'waiting' => isMsg ? 'draft' : 'aapki haan?',
            'sent' => 'bheja',
            'approved' => 'maana',
            'rejected' => 'nahi',
            'stale' => 'purana',
            'paid' => 'diya',
            _ => st,
          }, fg: st == 'waiting' ? C.accent : (st == 'rejected' || st == 'stale' ? C.bad : C.ok)),
        ]),
        if (isMsg) Text(_s(show['text']), style: const TextStyle(fontSize: 13)),
        if (!isMsg) ...[
          _line('Mehmaan', _s(show['guest'])),
          _line('Taarikh', _s(show['dates'])),
          _line('Raqam', _s(show['amount_text']), color: C.warn),
          _line('Kyon', _s(show['why'])),
          _line('Vendor', _s(show['vendor'])),
        ],
        for (final b in _strs(show['blanks'])) Text('⚠ Khaali: $b', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting' && isMsg)
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
                        await _call(context, widget.app, 'POST', '/api/homestay/cards/${_s(c['id'])}/drop');
                        widget.onDone?.call();
                      }),
          ]),
        if (st == 'waiting' && !isMsg)
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        const Text('Hoola paise nahi leta / deta; mehmaan ko message bhi aapke tap se hi jaata hai.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// homestay_booking: a booking was made / changed (OTA mail, file, check-out). Tap opens it.
class HomestayBookingCard extends StatelessWidget {
  const HomestayBookingCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final b = _m(data['booking']);
    return Glass(
      child: Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HomestayBookingPage(app: app, id: _s(b['id'])))),
        child: Row(children: [
          Icon(Icons.bed_rounded, color: _statusColor(_s(b['status']))),
          const SizedBox(width: 8),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(b['number'])} · ${_strs(b['rooms']).join(', ')}', style: const TextStyle(fontWeight: FontWeight.w800)),
              Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
            ]),
          ),
          Pill(_s(b['status_label']), fg: _statusColor(_s(b['status']))),
        ]),
      ),
    );
  }
}

/// homestay_alert (clash, Form C clock, hold ended, late check-out, registration) and homestay_day (morning note).
class HomestayAlertCard extends StatelessWidget {
  const HomestayAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final k = _s(data['kind']);
    final urgent = k == 'clash' || k == 'form_c';
    return Glass(
      border: urgent ? C.bad : null,
      child: Row(children: [
        Icon(switch (k) {
          'clash' => Icons.warning_amber_rounded,
          'form_c' => Icons.assignment_ind_rounded,
          'registration' => Icons.verified_rounded,
          'hold' => Icons.timer_off_rounded,
          _ => Icons.notifications_active_rounded,
        }, color: urgent ? C.bad : C.accent),
        const SizedBox(width: 8),
        Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13))),
        IconButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HomestayScreen(app: app))),
            icon: const Icon(Icons.chevron_right_rounded)),
      ]),
    );
  }
}

class HomestayDayCard extends StatelessWidget {
  const HomestayDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Press(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HomestayScreen(app: app))),
          child: Row(children: [
            const Icon(Icons.wb_sunny_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Aaj ka homestay', style: TextStyle(fontWeight: FontWeight.w800)),
                Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
              ]),
            ),
          ]),
        ),
      );
}
