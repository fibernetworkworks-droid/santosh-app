/// Profile > Front Office Sahayak: Hoola as the hotel / lodge / guest-house front desk.
/// Aaj (arrivals, departures, Form C due, holds, dirty rooms, unpaid, her cards + message drafts) · Booking (new booking,
/// paste an OTA mail, upload an OTA sheet, list -> booking page with check-in / out, folio, payments, cards) · Kamre
/// (housekeeping board + availability) · Report (occupancy, ADR, RevPAR, by source, guest register) · Niyam (hotel, GSTIN,
/// UPI, times, cancellation policy, room types and HER rates). Overbooking is refused by the server; discounts, complimentary,
/// cancellation charges, refunds (fingerprint) and bill finalisation run only after HER tap; every guest message is a draft
/// she sends. Hoola never takes or pays money.
library;

import 'package:file_picker/file_picker.dart';
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
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());
String _rs(dynamic v) => v == null ? '[daam?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';

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
                maxLines: (k == 'text' || k == 'address' || k == 'reason' || k == 'rules') ? 4 : 1),
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

Widget _h(String t) => Padding(
      padding: const EdgeInsets.fromLTRB(4, 14, 4, 6),
      child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
    );

Color _roomColor(String st) => switch (st) {
      'dirty' => C.warn,
      'clean' => C.teal,
      'inspected' => C.ok,
      'out_of_order' => C.bad,
      _ => C.chip,
    };

class FrontofficeScreen extends StatefulWidget {
  const FrontofficeScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<FrontofficeScreen> createState() => _FrontofficeScreenState();
}

class _FrontofficeScreenState extends State<FrontofficeScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/frontoffice'));
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
      .push(MaterialPageRoute(builder: (_) => FrontofficeBookingPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newBooking() async {
    final types = _list(_d?['types']).map((t) => _s(t['code'])).join(' / ');
    final f = await _form(context, 'Nayi booking', [
      ('room_type', 'Room type ($types)'),
      ('arrive', 'Aana (DD-MM-YYYY / aaj / kal)'),
      ('nights', 'Kitni raat'),
      ('name', 'Mehmaan ka naam'),
      ('phone', 'Mobile'),
      ('adults', 'Kitne log'),
      ('rate', 'Rate / raat (sirf aapne kaha ho; khaali = aapka plan)'),
      ('source', 'Kahan se: walk_in / phone / whatsapp / agent'),
    ], ok: 'Booking banao');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['nights', 'adults', 'rate']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    final r = await _run('POST', '/api/frontoffice/bookings', body);
    final id = _s(_m(r?['booking'])['id']);
    if (id.isNotEmpty) _open(id);
  }

  Future<void> _pasteOta() async {
    final f = await _form(context, 'OTA ka mail paste kijiye', const [
      ('text', 'MakeMyTrip / Goibibo / Booking.com / Agoda / Airbnb mail ka text'),
      ('room_type', 'Room type (agar Hoola pooche)'),
    ], ok: 'Padho');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '/api/frontoffice/import', f);
  }

  Future<void> _uploadSheet() async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
    final file = res?.files.firstOrNull;
    if (file == null || file.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/frontoffice/import/sheet', file.name, file.bytes!, timeout: const Duration(seconds: 90));
      if (mounted) {
        _snack(context, _s(r['say']));
        final notes = _strs(r['notes']);
        if (notes.isNotEmpty) {
          await showDialog<void>(
              context: context,
              builder: (d) => AlertDialog(
                  title: const Text('Sheet ke notes'),
                  content: SingleChildScrollView(child: Text(notes.join('\n'))),
                  actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))]));
        }
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _bookingTile(Map<String, dynamic> b) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        child: InkWell(
          onTap: () => _open(_s(b['id'])),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(b['number'])} · ${_s(b['guest'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${_s(b['type_name'])}${_s(b['room']).isEmpty ? '' : ' · room ${_s(b['room'])}'} · ${_s(b['arrive'])} → ${_s(b['depart'])}',
                    style: const TextStyle(fontSize: 12.5, color: C.muted)),
                Text('${_s(b['source_label'])} · ${b['total'] == null ? 'rate khaali' : _rs(b['total'])}'
                    '${(b['balance'] is num && (b['balance'] as num) > 0) ? ' · baaki ${_rs(b['balance'])}' : ''}',
                    style: const TextStyle(fontSize: 12, color: C.faint)),
              ]),
            ),
            Pill(_s(b['status_label']), fg: _s(b['status']) == 'in_house' ? C.ok : C.chip),
          ]),
        ),
      );

  Widget _aaj() {
    final d = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 14))),
      for (final c in _list(_d?['cards'])) Padding(padding: const EdgeInsets.only(top: 10), child: FrontofficeCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final m in _list(_d?['messages']).take(10))
        Padding(padding: const EdgeInsets.only(top: 10), child: FrontofficeMessageCard(app: widget.app, data: {'message': m}, onDone: _load)),
      if (_list(d['arrivals']).isNotEmpty) _h('Aaj aane wale'),
      for (final b in _list(d['arrivals'])) _bookingTile(b),
      if (_list(d['departures']).isNotEmpty) _h('Aaj jaane wale'),
      for (final b in _list(d['departures'])) _bookingTile(b),
      if (_list(_d?['formc']).isNotEmpty) _h('Form C (videshi mehmaan, 24 ghante)'),
      for (final f in _list(_d?['formc'])) FrontofficeFormCTile(app: widget.app, data: f, onDone: _load),
      if (_list(d['in_house']).isNotEmpty) _h('Ruke hue'),
      for (final b in _list(d['in_house'])) _bookingTile(b),
      if (_list(d['unpaid']).isNotEmpty) _h('Paisa baaki'),
      for (final b in _list(d['unpaid'])) _bookingTile(b),
    ]);
  }

  Widget _bookingsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GradientButton(label: 'Nayi booking', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _newBooking),
          GlassButton(label: 'OTA mail paste', icon: Icons.mail_rounded, height: 44, onTap: _busy ? null : _pasteOta),
          GlassButton(label: 'OTA sheet', icon: Icons.upload_file_rounded, height: 44, onTap: _busy ? null : _uploadSheet),
        ]),
        const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text('OTA par Hoola login nahi karta: aap mail / sheet dijiye. Jo raat bhari ho, wahan booking ban hi nahi sakti.',
              style: TextStyle(fontSize: 11.5, color: C.faint)),
        ),
        _h('Aane wali bookings'),
        for (final b in _list(_d?['upcoming'])) _bookingTile(b),
        if (_list(_d?['upcoming']).isEmpty) const Text('Koi aane wali booking nahi.', style: TextStyle(color: C.muted)),
      ]);

  Widget _rooms() {
    final board = _m(_d?['board']);
    final rooms = _list(board['rooms']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(board['say']))),
      _h('Housekeeping (tap = status badlo)'),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final r in rooms)
          GestureDetector(
            onTap: () => _roomSheet(r),
            child: Container(
              width: 98,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                  color: _roomColor(_s(r['status'])).withOpacity(.16),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: _roomColor(_s(r['status'])))),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(r['number']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                Text(_s(r['type']), style: const TextStyle(fontSize: 11, color: C.muted)),
                Text(_s(r['status_label']), style: TextStyle(fontSize: 11, color: _roomColor(_s(r['status'])))),
                if (r['occupied'] == true) Text(_s(r['guest']), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
                if (_s(r['arriving']).isNotEmpty) Text('aa raha ${_s(r['arriving'])}', style: const TextStyle(fontSize: 10.5, color: C.accent)),
              ]),
            ),
          ),
      ]),
      _h('Khaali kamre'),
      FrontofficeAvailability(app: widget.app),
    ]);
  }

  Future<void> _roomSheet(Map<String, dynamic> r) async {
    final st = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(title: Text('Room ${_s(r['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          for (final (k, l) in const [('dirty', 'Ganda'), ('clean', 'Saaf'), ('inspected', 'Jaancha hua (ready)'), ('out_of_order', 'Kharab / band')])
            ListTile(title: Text(l), leading: Icon(Icons.circle, color: _roomColor(k), size: 14), onTap: () => Navigator.pop(c, k)),
        ]),
      ),
    );
    if (st == null) return;
    var body = <String, dynamic>{'status': st};
    if (st == 'out_of_order') {
      final f = await _form(context, 'Kyon band?', const [('reason', 'Wajah (AC kharab / seepage ...)'), ('until', 'Kab tak (DD-MM-YYYY, khaali = jab tak aap kahein)')]);
      if (f == null) return;
      body = {...body, ...f};
    }
    await _run('POST', '/api/frontoffice/rooms/${_s(r['number'])}/status', body);
  }

  Widget _report() {
    final rep = _m(_d?['report']);
    final t = _m(rep['total']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      FrontofficeReportView(app: widget.app, initial: rep),
      const SizedBox(height: 12),
      GlassButton(
          label: 'Guest register (Excel)',
          icon: Icons.table_chart_rounded,
          onTap: _busy ? null : () => _run('POST', '/api/frontoffice/register', <String, dynamic>{})),
      if (t.isEmpty) const SizedBox.shrink(),
    ]);
  }

  Future<void> _settings() async {
    final s = _m(_d?['settings']);
    final pol = _m(s['cancel_policy']);
    final f = await _form(context, 'Hotel ke niyam', const [
      ('hotel_name', 'Hotel ka naam'),
      ('address', 'Pata'),
      ('phone', 'Phone'),
      ('gstin', 'GSTIN (registered ho to)'),
      ('upi_id', 'Aapka UPI ID'),
      ('check_in_time', 'Check-in samay (12:00)'),
      ('check_out_time', 'Check-out samay (11:00)'),
      ('free_days', 'Kitne din pehle tak free cancellation'),
      ('fee', 'Uske baad: first_night / pct / full'),
      ('pct', 'Agar pct: kitna %'),
      ('review_link', 'Google review link (https://...)'),
      ('morning_time', 'Subah ka note (08:00)'),
    ], initial: {
      'hotel_name': _s(s['hotel_name']),
      'address': _s(s['address']),
      'phone': _s(s['phone']),
      'gstin': _s(s['gstin']),
      'upi_id': _s(s['upi_id']),
      'check_in_time': _s(s['check_in_time']),
      'check_out_time': _s(s['check_out_time']),
      'free_days': _s(pol['free_days']),
      'fee': _s(pol['fee']),
      'pct': _s(pol['pct']),
      'review_link': _s(s['review_link']),
      'morning_time': _s(s['morning_time']),
    }, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f}..removeWhere((k, _) => ['free_days', 'fee', 'pct'].contains(k));
    if (f['free_days'] != null || f['fee'] != null) {
      body['cancel_policy'] = {'free_days': _n(f['free_days']) ?? 0, 'fee': f['fee'] ?? 'first_night', 'pct': _n(f['pct']) ?? 0};
    }
    await _run('PUT', '/api/frontoffice/settings', body);
  }

  Future<void> _roomType([Map<String, dynamic>? t]) async {
    final f = await _form(context, t == null ? 'Naya room type' : 'Room type: ${_s(t['name'])}', const [
      ('name', 'Naam (Deluxe / Standard)'),
      ('code', 'Code (DLX)'),
      ('aliases', 'OTA par naam (comma se)'),
      ('max_adults', 'Zyada se zyada log'),
      ('base', 'Rate / raat (weekday)'),
      ('weekend', 'Weekend rate (Fri, Sat raat)'),
      ('extra_adult', 'Extra adult / raat'),
      ('numbers', 'Kamre (101-105, 201) - sirf naye ke liye'),
    ], initial: t == null
        ? const {}
        : {
            'name': _s(t['name']),
            'code': _s(t['code']),
            'aliases': _s(t['aliases']),
            'max_adults': _s(t['max_adults']),
            'base': _s(t['base']),
            'weekend': _s(t['weekend']),
            'extra_adult': _s(t['extra_adult']),
          }, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f}..remove('numbers');
    for (final k in ['max_adults', 'base', 'weekend', 'extra_adult']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    if (t != null) body['type'] = _s(t['id']);
    final r = await _run('POST', '/api/frontoffice/types', body);
    final code = _s(_m(r?['room_type'])['code']);
    if ((f['numbers'] ?? '').isNotEmpty && code.isNotEmpty) {
      await _run('POST', '/api/frontoffice/rooms', {'type': code, 'numbers': f['numbers']});
    }
  }

  Widget _niyam() {
    final s = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(s['hotel_name']).isEmpty ? 'Hotel ka naam daaliye' : _s(s['hotel_name']), style: const TextStyle(fontWeight: FontWeight.w800)),
          _line('GST', _s(s['gst_note'])),
          _line('UPI', _s(s['upi_id'])),
          _line('Check-in / out', '${_s(s['check_in_time'])} / ${_s(s['check_out_time'])}'),
          _line('Cancellation', _s(s['cancel_policy_text']).isEmpty ? 'set nahi (charge nahi lagega)' : _s(s['cancel_policy_text'])),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _settings),
        ]),
      ),
      _h('Room types aur aapke rate'),
      for (final t in _list(_d?['types']))
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          child: InkWell(
            onTap: () => _roomType(t),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(t['code'])} · ${_s(t['name'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              _line('Rate', t['base'] == null ? 'nahi diya (quote par khaali)' : '${_rs(t['base'])} · weekend ${_rs(t['weekend'] ?? t['base'])}',
                  color: t['base'] == null ? C.warn : null),
              _line('Kamre', _strs(t['rooms']).join(', ')),
              _line('Seasons', _list(t['seasons']).map((x) => '${_s(x['name'])} ${_s(x['from'])}-${_s(x['to'])} ${_rs(x['rate'])}').join('; ')),
            ]),
          ),
        ),
      GlassButton(label: 'Naya room type', icon: Icons.add_rounded, onTap: _busy ? null : () => _roomType()),
      _h('Hoola kabhi nahi karega'),
      for (final n in _strs(_d?['never'])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = const ['Aaj', 'Booking', 'Kamre', 'Report', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        title: Text('${widget.app.aName} · Front office'),
        backgroundColor: Colors.transparent,
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(children: [
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
                    0 => _aaj(),
                    1 => _bookingsTab(),
                    2 => _rooms(),
                    3 => _report(),
                    _ => _niyam(),
                  },
                ),
        ),
      ]),
    );
  }
}

/// Free rooms per type per night for the dates she picks.
class FrontofficeAvailability extends StatefulWidget {
  const FrontofficeAvailability({super.key, required this.app});
  final Santosh app;
  @override
  State<FrontofficeAvailability> createState() => _FrontofficeAvailabilityState();
}

class _FrontofficeAvailabilityState extends State<FrontofficeAvailability> {
  Map<String, dynamic>? _a;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load([String arrive = '', String depart = '']) async {
    try {
      final q = <String, String>{'days': '7'};
      if (arrive.isNotEmpty) q['arrive'] = arrive;
      if (depart.isNotEmpty) q['depart'] = depart;
      final r = _m(await widget.app.api!.call('GET', '/api/frontoffice/availability', query: q));
      if (mounted) setState(() => _a = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final a = _a;
    if (a == null) return const SizedBox(height: 40, child: Center(child: CircularProgressIndicator()));
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${_s(a['from'])} → ${_s(a['to'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
          TextButton(
              onPressed: () async {
                final f = await _form(context, 'Tareekh', const [('arrive', 'Aana'), ('depart', 'Jaana')]);
                if (f != null) await _load(f['arrive'] ?? '', f['depart'] ?? '');
              },
              child: const Text('Badlo')),
        ]),
        for (final t in _list(a['types'])) ...[
          Text(_s(t['name']), style: const TextStyle(fontWeight: FontWeight.w600)),
          Wrap(spacing: 4, runSpacing: 4, children: [
            for (final n in _list(t['nights']))
              Pill('${_s(n['date']).length >= 10 ? _s(n['date']).substring(8) : _s(n['date'])}: ${_s(n['free'])}',
                  fg: (n['free'] is num && (n['free'] as num) > 0) ? C.ok : C.bad),
          ]),
          const SizedBox(height: 6),
        ],
      ]),
    );
  }
}

/// Occupancy / ADR / RevPAR for a range.
class FrontofficeReportView extends StatefulWidget {
  const FrontofficeReportView({super.key, required this.app, required this.initial});
  final Santosh app;
  final Map<String, dynamic> initial;
  @override
  State<FrontofficeReportView> createState() => _FrontofficeReportViewState();
}

class _FrontofficeReportViewState extends State<FrontofficeReportView> {
  late Map<String, dynamic> _r = widget.initial;

  Future<void> _pick() async {
    final f = await _form(context, 'Report kab ka', const [('start', 'Se (DD-MM-YYYY)'), ('end', 'Tak (DD-MM-YYYY)')]);
    if (f == null) return;
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/frontoffice/report', query: {'start': f['start'] ?? '', 'end': f['end'] ?? ''}));
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = _m(_r['total']);
    Widget tile(String l, String v) => Expanded(
          child: Glass(
            padding: const EdgeInsets.all(10),
            child: Column(children: [
              Text(v, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
              Text(l, style: const TextStyle(fontSize: 11.5, color: C.muted)),
            ]),
          ),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: Text('${_s(_r['from'])} → ${_s(_r['to'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
        TextButton(onPressed: _pick, child: const Text('Tareekh')),
      ]),
      Row(children: [
        tile('Occupancy', '${_s(t['occupancy_pct'])}%'),
        const SizedBox(width: 6),
        tile('ADR', _rs(t['adr'])),
        const SizedBox(width: 6),
        tile('RevPAR', _rs(t['revpar'])),
      ]),
      const SizedBox(height: 8),
      Text('${_s(t['rooms_sold'])} / ${_s(t['rooms_available'])} room-nights · kiraya ${_rs(t['room_revenue'])}',
          style: const TextStyle(color: C.muted)),
      for (final s in _list(_r['by_source'])) _line(_s(s['label']), '${_s(s['room_nights'])} raat · ${_rs(s['revenue'])}'),
      Text(_s(_r['note']), style: const TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }
}

/// One booking: dates, guest, room, folio with GST lines, payments, check-in / out, cards, messages.
class FrontofficeBookingPage extends StatefulWidget {
  const FrontofficeBookingPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<FrontofficeBookingPage> createState() => _FrontofficeBookingPageState();
}

class _FrontofficeBookingPageState extends State<FrontofficeBookingPage> {
  Map<String, dynamic>? _b;
  bool _busy = false;
  final List<Map<String, dynamic>> _cards = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = _m(await widget.app.api!.call('GET', '/api/frontoffice/bookings/${widget.id}'));
      if (mounted) setState(() => _b = b);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    if (r != null) {
      for (final k in ['card', 'refund_card']) {
        final c = _m(r[k]);
        if (c.isNotEmpty) _cards.insert(0, {'card': c});
      }
      final msg = _m(r['message']);
      if (msg.isNotEmpty) _cards.insert(0, {'message': msg});
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  String get _p => '/api/frontoffice/bookings/${widget.id}';

  Future<void> _checkIn() async {
    final foreign = _b?['foreign'] == true;
    final fields = foreign
        ? const [
            ('nationality', 'Nationality'),
            ('passport', 'Passport no. (Pehchaan Locker mein jayega)'),
            ('visa_number', 'Visa / OCI no.'),
            ('visa_type', 'Visa type'),
            ('visa_expiry', 'Visa kab tak (DD-MM-YYYY)'),
            ('arrived_india_on', 'India kab aaye'),
            ('coming_from', 'Kahan se aaye'),
            ('going_to', 'Aage kahan'),
            ('purpose', 'Kis kaam se'),
            ('room', 'Room (khaali = Hoola chunega)'),
          ]
        : const [
            ('id_kind', 'ID: aadhaar / dl / voter / passport'),
            ('id_number', 'ID number (Pehchaan Locker mein jayega)'),
            ('address', 'Pata'),
            ('coming_from', 'Kahan se aaye'),
            ('going_to', 'Aage kahan'),
            ('purpose', 'Kis kaam se'),
            ('room', 'Room (khaali = Hoola chunega)'),
          ];
    final f = await _form(context, 'Check-in', fields, ok: 'Check-in');
    if (f == null) return;
    await _run('POST', '$_p/checkin', f);
  }

  Future<void> _charge() async {
    final f = await _form(context, 'Folio mein jodo', const [
      ('kind', 'restaurant / room_service / laundry / extra_bed / minibar / transport / other'),
      ('text', 'Kya (Dinner, 2 shirt ...)'),
      ('amount', 'Rate'),
      ('qty', 'Kitne'),
    ], ok: 'Jodo');
    if (f == null) return;
    await _run('POST', '$_p/charge', {...f, 'amount': _n(f['amount']), 'qty': _n(f['qty']) ?? 1});
  }

  Future<void> _received() async {
    final f = await _form(context, 'Paisa mila (sirf aap)', const [('amount', 'Kitna'), ('mode', 'upi / cash / card / bank / ota'), ('ref', 'UTR / ref (aakhri ank)')],
        ok: 'Darj karo');
    if (f == null) return;
    await _run('POST', '$_p/received', {...f, 'amount': _n(f['amount'])});
  }

  Future<void> _payLink() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '$_p/pay_link'));
      final url = _s(r['url']);
      if (!mounted) return;
      _snack(context, _s(r['say']));
      if (url.isNotEmpty) await _run('POST', '$_p/message', {'kind': 'payment'});
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _discount() async {
    final f = await _form(context, 'Discount / muft (aapki haan ka card)', const [
      ('amount', 'Discount ₹'),
      ('pct', 'ya %'),
      ('complimentary', 'Poora muft? (haan likhiye)'),
      ('reason', 'Wajah'),
    ], ok: 'Card banao');
    if (f == null) return;
    await _run('POST', '$_p/discount', {
      'amount': _n(f['amount']),
      'pct': _n(f['pct']),
      'complimentary': (f['complimentary'] ?? '').toLowerCase().startsWith('h') || (f['complimentary'] ?? '').toLowerCase() == 'yes',
      'reason': f['reason'] ?? '',
    });
  }

  Future<void> _refund() async {
    final f = await _form(context, 'Refund (aapki haan + fingerprint)', const [('amount', 'Kitna'), ('reason', 'Wajah')], ok: 'Card banao');
    if (f == null) return;
    await _run('POST', '$_p/refund', {'amount': _n(f['amount']), 'reason': f['reason'] ?? ''});
  }

  Future<void> _amend() async {
    final b = _b ?? {};
    final f = await _form(context, 'Booking badlo', const [
      ('arrive', 'Aana'),
      ('depart', 'Jaana'),
      ('room_type', 'Room type'),
      ('adults', 'Log'),
      ('rate', 'Naya rate / raat (aapka)'),
    ], initial: {'arrive': _s(b['arrive']), 'depart': _s(b['depart']), 'room_type': _s(b['type']), 'adults': _s(b['adults'])}, ok: 'Badlo');
    if (f == null) return;
    await _run('POST', '$_p/amend', {...f, 'adults': _n(f['adults']), 'rate': _n(f['rate'])});
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(title: Text(b == null ? 'Booking' : '${_s(b['number'])} · ${_s(b['guest'])}'), backgroundColor: Colors.transparent),
      body: b == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                for (final c in _cards)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: c.containsKey('card')
                        ? FrontofficeCardCard(app: widget.app, data: c, onDone: _load)
                        : FrontofficeMessageCard(app: widget.app, data: c, onDone: _load),
                  ),
                FrontofficeBookingCard(app: widget.app, data: {'booking': b}),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (['hold', 'confirmed'].contains(_s(b['status']))) ...[
                    GradientButton(label: 'Check-in', icon: Icons.login_rounded, height: 42, onTap: _busy ? null : _checkIn),
                    GlassButton(label: 'Badlo', height: 42, onTap: _busy ? null : _amend),
                    GlassButton(label: 'Radd karo', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/cancel', {'reason': 'owner'})),
                    GlassButton(label: 'Confirmation draft', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/message', {'kind': 'confirmation'})),
                  ],
                  if (_s(b['status']) == 'hold') GlassButton(label: 'Pakki karo', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/confirm')),
                  if (_s(b['status']) == 'in_house') ...[
                    GradientButton(label: 'Check-out', icon: Icons.logout_rounded, height: 42, onTap: _busy ? null : () => _run('POST', '$_p/checkout')),
                    GlassButton(label: 'Folio mein jodo', height: 42, onTap: _busy ? null : _charge),
                    GlassButton(label: 'Badlo', height: 42, onTap: _busy ? null : _amend),
                  ],
                  if (_s(b['status']) == 'checked_out' && _m(b['bill'])['status'] != 'final')
                    GlassButton(label: 'Bill ka card', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/bill')),
                  GlassButton(label: 'Paisa mila', height: 42, onTap: _busy ? null : _received),
                  GlassButton(label: 'UPI link bhejo', height: 42, onTap: _busy ? null : _payLink),
                  GlassButton(label: 'Discount / muft', height: 42, onTap: _busy ? null : _discount),
                  GlassButton(label: 'Refund', height: 42, onTap: _busy ? null : _refund),
                ]),
                _h('Folio'),
                FrontofficeFolio(folio: _m(b['folio'])),
                _h('Paise'),
                for (final p in _list(b['payments'])) _line(_s(p['receipt_no']), '${_rs(p['amount'])} · ${_s(p['mode'])} · ${_s(p['on'])}'),
                if (_list(b['payments']).isEmpty) const Text('Abhi kuch nahi mila.', style: TextStyle(color: C.muted)),
                if (_list(b['formc']).isNotEmpty) _h('Form C'),
                for (final f in _list(b['formc'])) FrontofficeFormCTile(app: widget.app, data: f, onDone: _load),
                if (_m(b['bill'])['status'] == 'final') ...[
                  _h('Bill'),
                  _line('Number', _s(_m(b['bill'])['number'])),
                  GlassButton(
                      label: 'Bill PDF file',
                      icon: Icons.picture_as_pdf_rounded,
                      onTap: _busy ? null : () => _run('POST', '/api/frontoffice/bills/${_s(_m(b['bill'])['id'])}/file')),
                ],
                _h('Niyam'),
                Text(_s(b['policy_text']).isEmpty ? 'Cancellation policy set nahi.' : _s(b['policy_text']), style: const TextStyle(color: C.muted)),
                if (_s(b['ota_note']).isNotEmpty) Text(_s(b['ota_note']), style: const TextStyle(fontSize: 12, color: C.warn)),
              ]),
            ),
    );
  }
}

class FrontofficeFolio extends StatelessWidget {
  const FrontofficeFolio({super.key, required this.folio});
  final Map<String, dynamic> folio;
  @override
  Widget build(BuildContext context) {
    final f = folio;
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final l in _list(f['lines']))
          Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Row(children: [
              Expanded(child: Text(_s(l['text']), style: const TextStyle(fontSize: 12.5))),
              Text(l['value'] == null ? '[daam?]' : '${_rs(l['value'])}${f['gst_on'] == true ? ' +${_s(l['gst_pct'])}%' : ''}',
                  style: TextStyle(fontSize: 12.5, color: l['value'] == null ? C.warn : C.ink)),
            ]),
          ),
        const Divider(color: C.line),
        if ((f['discount'] is num) && (f['discount'] as num) > 0) _line(f['complimentary'] == true ? 'Complimentary' : 'Discount', _rs(f['discount'])),
        if (f['gst_on'] == true) _line('CGST + SGST', '${_rs(f['cgst'])} + ${_rs(f['sgst'])}'),
        _line('Kul', _rs(f['total']), color: C.ink),
        _line('Mila', _rs(f['paid'])),
        _line('Baaki', f['balance'] == null ? 'rate khaali' : _rs(f['balance']), color: C.accent),
        Text(_s(f['note']), style: const TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// Form C (Form III) entry: fields to type on indianfrro.gov.in (IDs masked), "Bhar diya" with her reference.
class FrontofficeFormCTile extends StatelessWidget {
  const FrontofficeFormCTile({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;

  Future<void> _show(BuildContext context) async {
    try {
      final r = _m(await app.api!.call('GET', '/api/frontoffice/formc/${_s(data['id'])}'));
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text('Form C · ${_s(data['guest'])}'),
          content: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              for (final f in _list(r['fields'])) _line(_s(f['label']), _s(f['value'])),
              const SizedBox(height: 6),
              Text(_s(r['say']), style: const TextStyle(fontSize: 12, color: C.faint)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Native.openExternal(url: _s(r['portal'])), child: const Text('e-FRRO kholo')),
            TextButton(onPressed: () => Navigator.pop(d), child: const Text('Band')),
          ],
        ),
      );
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        border: data['overdue'] == true ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_s(data['guest'])} · ${_s(data['kind']) == 'arrival' ? 'aagman' : 'departure'} · ${_s(data['booking'])}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          _line('Kab tak', _s(data['due_local']), color: data['overdue'] == true ? C.bad : null),
          _line('Ref', _s(data['ref'])),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 6, children: [
            GlassButton(label: 'Data dekho', height: 38, onTap: () => _show(context)),
            if (_s(data['status']) == 'due')
              GlassButton(
                  label: 'Maine bhar diya',
                  height: 38,
                  onTap: () async {
                    final f = await _form(context, 'Form C ref', const [('ref', 'Portal ka reference (ho to)')], ok: 'Darj karo');
                    if (f == null || !context.mounted) return;
                    await _call(context, app, 'POST', '/api/frontoffice/formc/${_s(data['id'])}/done', {'ref': f['ref'] ?? ''});
                    onDone?.call();
                  }),
          ]),
        ]),
      );
}

/// frontoffice_card: a decision only HER tap makes (discount / comp / cancellation charge / refund (fingerprint) / bill final).
class FrontofficeCardCard extends StatefulWidget {
  const FrontofficeCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<FrontofficeCardCard> createState() => _FrontofficeCardCardState();
}

class _FrontofficeCardCardState extends State<FrontofficeCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/frontoffice/cards/$id/challenge'));
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
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash'])};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/frontoffice/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/frontoffice/cards/$id/decide', body: {...body, 'proof': proof});
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

  Future<void> _refundDone() async {
    final f = await _form(context, 'Refund bhej diya', const [('ref', 'UTR / ref'), ('mode', 'upi / bank / cash / card')], ok: 'Darj karo');
    if (f == null) return;
    await _call(context, widget.app, 'POST', '/api/frontoffice/cards/${_s(_c['id'])}/refund_done', f);
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final show = _m(c['show']);
    final st = _s(c['status']);
    final kind = _s(c['kind']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(c['money'] == true ? Icons.payments_rounded : Icons.hotel_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · ${_s(c['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'maana', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' || st == 'stale' ? C.bad : C.ok)),
        ]),
        Text(_s(show['title']), style: const TextStyle(fontSize: 13)),
        if (kind == 'bill')
          for (final l in _list(show['lines']).take(12))
            _line(_s(l['text']), '${_rs(l['value'])}${show['gst_on'] == true ? ' +${_s(l['gst_pct'])}%' : ''}'),
        if (kind == 'bill') _line('Kul', _rs(show['total']), color: C.ink),
        _line('Kyon', _s(show['why'] ?? show['reason'])),
        _line('Kaise', _s(show['how'])),
        for (final x in _strs(show['checks'])) Text('⚠ $x', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved' && kind == 'refund' && show['done'] != true)
          GlassButton(label: 'Refund bhej diya', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : _refundDone),
        const Text('Hoola paise nahi leta / deta; refund aap apne app / bank se bhejti hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// frontoffice_message: a DRAFT for the guest. Sent only from her tap (own WhatsApp / SMS, or the business number).
class FrontofficeMessageCard extends StatefulWidget {
  const FrontofficeMessageCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<FrontofficeMessageCard> createState() => _FrontofficeMessageCardState();
}

class _FrontofficeMessageCardState extends State<FrontofficeMessageCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['message']);

  Future<void> _send(String via) async {
    setState(() => _busy = true);
    try {
      if (via == 'self') {
        final link = _s(_x['wa']).isNotEmpty ? _s(_x['wa']) : _s(_x['sms']);
        if (link.isEmpty) throw Exception('Mehmaan ka mobile nahi.');
        await Native.openExternal(url: link);
      }
      final m = _m(await widget.app.api!.call('POST', '/api/frontoffice/messages/${_s(_x['id'])}/send', body: {'via': via, 'hash': _s(_x['hash'])}));
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
      final m = _m(await widget.app.api!.call('PUT', '/api/frontoffice/messages/${_s(_x['id'])}', body: {'text': f['text'] ?? ''}));
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
          Expanded(child: Text('${_s(x['to'])} ko · ${_s(x['kind'])} · ${_s(x['booking'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
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
                        await _call(context, widget.app, 'POST', '/api/frontoffice/messages/${_s(x['id'])}/drop');
                        widget.onDone?.call();
                      }),
          ]),
      ]),
    );
  }
}

/// frontoffice_booking: one booking (updated in place by its id).
class FrontofficeBookingCard extends StatelessWidget {
  const FrontofficeBookingCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final b = _m(data['booking']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.hotel_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(b['number'])} · ${_s(b['guest'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(b['status_label']), fg: _s(b['status']) == 'in_house' ? C.ok : C.chip),
        ]),
        _line('Kamra', '${_s(b['type_name'])}${_s(b['room']).isEmpty ? '' : ' · room ${_s(b['room'])}'}'),
        _line('Tareekh', '${_s(b['arrive'])} → ${_s(b['depart'])} (${_s(b['nights_count'])} raat) · ${_s(b['adults'])} log'),
        _line('Kahan se', '${_s(b['source_label'])}${_s(b['ota_ref']).isEmpty ? '' : ' · ${_s(b['ota_ref'])}'}'),
        _line('Kul', b['total'] == null ? 'rate khaali: ${_strs(b['blanks']).join(', ')}' : _rs(b['total']),
            color: b['total'] == null ? C.warn : null),
        if (b['balance'] is num && (b['balance'] as num) > 0) _line('Baaki', _rs(b['balance']), color: C.accent),
        if (_s(b['hold_until']).isNotEmpty) _line('Hold', '${_s(b['hold_until'])} tak (advance aane par pakki)'),
        if (data['say'] != null) Text(_s(data['say']), style: const TextStyle(fontSize: 12, color: C.faint)),
      ]),
    );
  }
}

/// frontoffice_alert: overbook (OTA mail that doesn't fit), Form C due / late, hold released, no-show.
class FrontofficeAlertCard extends StatelessWidget {
  const FrontofficeAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final kind = _s(data['kind']);
    final bad = kind == 'overbook' || (kind == 'formc' && _m(data['formc'])['overdue'] == true);
    return Glass(
      border: bad ? C.bad : C.warn,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(kind == 'formc' ? Icons.badge_rounded : Icons.warning_amber_rounded, color: bad ? C.bad : C.warn),
          const SizedBox(width: 8),
          Expanded(
              child: Text(switch (kind) {
            'overbook' => 'Overbooking roki',
            'formc' => 'Form C (videshi mehmaan)',
            'hold_released' => 'Hold khatam',
            'no_show' => 'No-show?',
            _ => 'Front desk',
          }, style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
        if (kind == 'formc' && _m(data['formc']).isNotEmpty) ...[
          const SizedBox(height: 6),
          FrontofficeFormCTile(app: app, data: _m(data['formc'])),
        ],
      ]),
    );
  }
}

/// frontoffice_day: morning note (arrivals, departures, Form C, cards / drafts waiting, yesterday's occupancy).
class FrontofficeDayCard extends StatelessWidget {
  const FrontofficeDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final rep = _m(data['report']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.wb_sunny_rounded, color: C.accent),
          SizedBox(width: 8),
          Text('Aaj ka front desk', style: TextStyle(fontWeight: FontWeight.w800)),
        ]),
        Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
        if (rep.isNotEmpty) _line('Kal', 'occupancy ${_s(rep['occupancy_pct'])}% · ADR ${_rs(rep['adr'])} · RevPAR ${_rs(rep['revpar'])}'),
        const SizedBox(height: 6),
        GlassButton(
            label: 'Front office kholo',
            height: 38,
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FrontofficeScreen(app: app)))),
      ]),
    );
  }
}
