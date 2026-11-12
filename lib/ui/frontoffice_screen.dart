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
import 'desk/desk_kit.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());
String _rs(dynamic v) => v == null ? '[price?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';

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
                maxLines: (k == 'text' || k == 'address' || k == 'reason' || k == 'rules') ? 4 : 1),
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
    final f = await _form(context, 'New booking', [
      ('room_type', 'Room type ($types)'),
      ('arrive', 'Arrival (DD-MM-YYYY / today / tomorrow)'),
      ('nights', 'How many nights'),
      ('name', 'Guest name'),
      ('phone', 'Mobile'),
      ('adults', 'How many people'),
      ('rate', 'Rate / night (only if you said it; empty = your plan)'),
      ('source', 'Source: walk_in / phone / whatsapp / agent'),
    ], ok: 'Make booking');
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
    final f = await _form(context, 'Paste the OTA mail', const [
      ('text', 'Text of the MakeMyTrip / Goibibo / Booking.com / Agoda / Airbnb mail'),
      ('room_type', 'Room type (if Hoola asks)'),
    ], ok: 'Read');
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
                  title: const Text('Sheet notes'),
                  content: SingleChildScrollView(child: Text(notes.join('\n'))),
                  actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('OK'))]));
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
                Text('${_s(b['source_label'])} · ${b['total'] == null ? 'rate empty' : _rs(b['total'])}'
                    '${(b['balance'] is num && (b['balance'] as num) > 0) ? ' · due ${_rs(b['balance'])}' : ''}',
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
      if (_list(d['arrivals']).isNotEmpty) _h('Arriving today'),
      for (final b in _list(d['arrivals'])) _bookingTile(b),
      if (_list(d['departures']).isNotEmpty) _h('Leaving today'),
      for (final b in _list(d['departures'])) _bookingTile(b),
      if (_list(_d?['formc']).isNotEmpty) _h('Form C (foreign guest, 24 hours)'),
      for (final f in _list(_d?['formc'])) FrontofficeFormCTile(app: widget.app, data: f, onDone: _load),
      if (_list(d['in_house']).isNotEmpty) _h('Held'),
      for (final b in _list(d['in_house'])) _bookingTile(b),
      if (_list(d['unpaid']).isNotEmpty) _h('Payment due'),
      for (final b in _list(d['unpaid'])) _bookingTile(b),
    ]);
  }

  Widget _bookingsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GradientButton(label: 'New booking', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _newBooking),
          GlassButton(label: 'OTA mail paste', icon: Icons.mail_rounded, height: 44, onTap: _busy ? null : _pasteOta),
          GlassButton(label: 'OTA sheet', icon: Icons.upload_file_rounded, height: 44, onTap: _busy ? null : _uploadSheet),
        ]),
        const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text('Hoola does not log in to OTA sites: give it the mail / sheet. A booking cannot be made on a night that is full.',
              style: TextStyle(fontSize: 11.5, color: C.faint)),
        ),
        _h('Upcoming bookings'),
        for (final b in _list(_d?['upcoming'])) _bookingTile(b),
        if (_list(_d?['upcoming']).isEmpty) const Text('No upcoming bookings.', style: TextStyle(color: C.muted)),
      ]);

  Widget _rooms() {
    final board = _m(_d?['board']);
    final rooms = _list(board['rooms']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(board['say']))),
      _h('Housekeeping (tap = change status)'),
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
                if (_s(r['arriving']).isNotEmpty) Text('arriving ${_s(r['arriving'])}', style: const TextStyle(fontSize: 10.5, color: C.accent)),
              ]),
            ),
          ),
      ]),
      _h('Empty rooms'),
      FrontofficeAvailability(app: widget.app),
    ]);
  }

  Future<void> _roomSheet(Map<String, dynamic> r) async {
    final st = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(title: Text('Room ${_s(r['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          for (final (k, l) in const [('dirty', 'Dirty'), ('clean', 'Clean'), ('inspected', 'Inspected (ready)'), ('out_of_order', 'Broken / closed')])
            ListTile(title: Text(l), leading: Icon(Icons.circle, color: _roomColor(k), size: 14), onTap: () => Navigator.pop(c, k)),
        ]),
      ),
    );
    if (st == null) return;
    var body = <String, dynamic>{'status': st};
    if (st == 'out_of_order') {
      final f = await _form(context, 'Why closed?', const [('reason', 'Reason (AC broken / seepage ...)'), ('until', 'Until when (DD-MM-YYYY, empty = until you say)')]);
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
    final f = await _form(context, 'Hotel rules', const [
      ('hotel_name', 'Hotel name'),
      ('address', 'Address'),
      ('phone', 'Phone'),
      ('gstin', 'GSTIN (if registered)'),
      ('upi_id', 'Your UPI ID'),
      ('check_in_time', 'Check-in time (12:00)'),
      ('check_out_time', 'Check-out time (11:00)'),
      ('free_days', 'Free cancellation up to how many days before'),
      ('fee', 'After that: first_night / pct / full'),
      ('pct', 'If pct: how much %'),
      ('review_link', 'Google review link (https://...)'),
      ('morning_time', 'Morning note (08:00)'),
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
    final f = await _form(context, t == null ? 'New room type' : 'Room type: ${_s(t['name'])}', const [
      ('name', 'Name (Deluxe / Standard)'),
      ('code', 'Code (DLX)'),
      ('aliases', 'Name on OTA (comma separated)'),
      ('max_adults', 'Maximum people'),
      ('base', 'Rate / night (weekday)'),
      ('weekend', 'Weekend rate (Fri, Sat nights)'),
      ('extra_adult', 'Extra adult / night'),
      ('numbers', 'Rooms (101-105, 201) - only for a new one'),
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
          Text(_s(s['hotel_name']).isEmpty ? 'Enter the hotel name' : _s(s['hotel_name']), style: const TextStyle(fontWeight: FontWeight.w800)),
          _line('GST', _s(s['gst_note'])),
          _line('UPI', _s(s['upi_id'])),
          _line('Check-in / out', '${_s(s['check_in_time'])} / ${_s(s['check_out_time'])}'),
          _line('Cancellation', _s(s['cancel_policy_text']).isEmpty ? 'not set (no charge will be added)' : _s(s['cancel_policy_text'])),
          const SizedBox(height: 8),
          GlassButton(label: 'Edit', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _settings),
        ]),
      ),
      _h('Room types and your rates'),
      for (final t in _list(_d?['types']))
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          child: InkWell(
            onTap: () => _roomType(t),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(t['code'])} · ${_s(t['name'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              _line('Rate', t['base'] == null ? 'not given (left empty on the quote)' : '${_rs(t['base'])} · weekend ${_rs(t['weekend'] ?? t['base'])}',
                  color: t['base'] == null ? C.warn : null),
              _line('Rooms', _strs(t['rooms']).join(', ')),
              _line('Seasons', _list(t['seasons']).map((x) => '${_s(x['name'])} ${_s(x['from'])}-${_s(x['to'])} ${_rs(x['rate'])}').join('; ')),
            ]),
          ),
        ),
      GlassButton(label: 'New room type', icon: Icons.add_rounded, onTap: _busy ? null : () => _roomType()),
      _h('Hoola will never do'),
      for (final n in _strs(_d?['never'])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    // v0.868 R8 wave 1: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'Front office',
      tabs: const ['Today', 'Booking', 'Rooms', 'Report', 'Rules'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      busy: _busy,
      onRefresh: _load,
      body: () => switch (_tab) {
        0 => _aaj(),
        1 => _bookingsTab(),
        2 => _rooms(),
        3 => _report(),
        _ => _niyam(),
      },
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
                final f = await _form(context, 'Date', const [('arrive', 'Arrival'), ('depart', 'Departure')]);
                if (f != null) await _load(f['arrive'] ?? '', f['depart'] ?? '');
              },
              child: const Text('Edit')),
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
    final f = await _form(context, 'Report from', const [('start', 'Se (DD-MM-YYYY)'), ('end', 'Until (DD-MM-YYYY)')]);
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
        TextButton(onPressed: _pick, child: const Text('Date')),
      ]),
      Row(children: [
        tile('Occupancy', '${_s(t['occupancy_pct'])}%'),
        const SizedBox(width: 6),
        tile('ADR', _rs(t['adr'])),
        const SizedBox(width: 6),
        tile('RevPAR', _rs(t['revpar'])),
      ]),
      const SizedBox(height: 8),
      Text('${_s(t['rooms_sold'])} / ${_s(t['rooms_available'])} room-nights · rent ${_rs(t['room_revenue'])}',
          style: const TextStyle(color: C.muted)),
      for (final s in _list(_r['by_source'])) _line(_s(s['label']), '${_s(s['room_nights'])} nights · ${_rs(s['revenue'])}'),
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
            ('passport', 'Passport no. (goes to the ID Locker)'),
            ('visa_number', 'Visa / OCI no.'),
            ('visa_type', 'Visa type'),
            ('visa_expiry', 'Visa valid until (DD-MM-YYYY)'),
            ('arrived_india_on', 'When they came to India'),
            ('coming_from', 'Coming from'),
            ('going_to', 'Going where'),
            ('purpose', 'Purpose of visit'),
            ('room', 'Room (empty = Hoola will pick)'),
          ]
        : const [
            ('id_kind', 'ID: aadhaar / dl / voter / passport'),
            ('id_number', 'ID number (goes to the ID Locker)'),
            ('address', 'Address'),
            ('coming_from', 'Coming from'),
            ('going_to', 'Going where'),
            ('purpose', 'Purpose of visit'),
            ('room', 'Room (empty = Hoola will pick)'),
          ];
    final f = await _form(context, 'Check-in', fields, ok: 'Check-in');
    if (f == null) return;
    await _run('POST', '$_p/checkin', f);
  }

  Future<void> _charge() async {
    final f = await _form(context, 'Add to folio', const [
      ('kind', 'restaurant / room_service / laundry / extra_bed / minibar / transport / other'),
      ('text', 'What (Dinner, 2 shirts ...)'),
      ('amount', 'Rate'),
      ('qty', 'How many'),
    ], ok: 'Add');
    if (f == null) return;
    await _run('POST', '$_p/charge', {...f, 'amount': _n(f['amount']), 'qty': _n(f['qty']) ?? 1});
  }

  Future<void> _received() async {
    final f = await _form(context, 'Money received (only you)', const [('amount', 'How much'), ('mode', 'upi / cash / card / bank / ota'), ('ref', 'UTR / ref (last digits)')],
        ok: 'Record');
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
    final f = await _form(context, 'Discount / free (card for your approval)', const [
      ('amount', 'Discount ₹'),
      ('pct', 'ya %'),
      ('complimentary', 'Fully free? (write yes)'),
      ('reason', 'Reason'),
    ], ok: 'Make card');
    if (f == null) return;
    await _run('POST', '$_p/discount', {
      'amount': _n(f['amount']),
      'pct': _n(f['pct']),
      'complimentary': (f['complimentary'] ?? '').toLowerCase().startsWith('h') || (f['complimentary'] ?? '').toLowerCase() == 'yes',
      'reason': f['reason'] ?? '',
    });
  }

  Future<void> _refund() async {
    final f = await _form(context, 'Refund (your approval + fingerprint)', const [('amount', 'How much'), ('reason', 'Reason')], ok: 'Make card');
    if (f == null) return;
    await _run('POST', '$_p/refund', {'amount': _n(f['amount']), 'reason': f['reason'] ?? ''});
  }

  Future<void> _amend() async {
    final b = _b ?? {};
    final f = await _form(context, 'Change booking', const [
      ('arrive', 'Arrival'),
      ('depart', 'Departure'),
      ('room_type', 'Room type'),
      ('adults', 'Log'),
      ('rate', 'New rate / night (yours)'),
    ], initial: {'arrive': _s(b['arrive']), 'depart': _s(b['depart']), 'room_type': _s(b['type']), 'adults': _s(b['adults'])}, ok: 'Edit');
    if (f == null) return;
    await _run('POST', '$_p/amend', {...f, 'adults': _n(f['adults']), 'rate': _n(f['rate'])});
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    return DeskPage(
      title: b == null ? 'Booking' : '${_s(b['number'])} · ${_s(b['guest'])}',
      loading: b == null,
      onRefresh: _load,
      body: () => b == null ? const SizedBox.shrink() : RefreshIndicator(
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
                    GlassButton(label: 'Edit', height: 42, onTap: _busy ? null : _amend),
                    GlassButton(label: 'Cancel', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/cancel', {'reason': 'owner'})),
                    GlassButton(label: 'Confirmation draft', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/message', {'kind': 'confirmation'})),
                  ],
                  if (_s(b['status']) == 'hold') GlassButton(label: 'Confirm', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/confirm')),
                  if (_s(b['status']) == 'in_house') ...[
                    GradientButton(label: 'Check-out', icon: Icons.logout_rounded, height: 42, onTap: _busy ? null : () => _run('POST', '$_p/checkout')),
                    GlassButton(label: 'Add to folio', height: 42, onTap: _busy ? null : _charge),
                    GlassButton(label: 'Edit', height: 42, onTap: _busy ? null : _amend),
                  ],
                  if (_s(b['status']) == 'checked_out' && _m(b['bill'])['status'] != 'final')
                    GlassButton(label: 'Bill card', height: 42, onTap: _busy ? null : () => _run('POST', '$_p/bill')),
                  GlassButton(label: 'Money received', height: 42, onTap: _busy ? null : _received),
                  GlassButton(label: 'Send UPI link', height: 42, onTap: _busy ? null : _payLink),
                  GlassButton(label: 'Discount / free', height: 42, onTap: _busy ? null : _discount),
                  GlassButton(label: 'Refund', height: 42, onTap: _busy ? null : _refund),
                ]),
                _h('Folio'),
                FrontofficeFolio(folio: _m(b['folio'])),
                _h('Money'),
                for (final p in _list(b['payments'])) _line(_s(p['receipt_no']), '${_rs(p['amount'])} · ${_s(p['mode'])} · ${_s(p['on'])}'),
                if (_list(b['payments']).isEmpty) const Text('Nothing found yet.', style: TextStyle(color: C.muted)),
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
                _h('Rules'),
                Text(_s(b['policy_text']).isEmpty ? 'Cancellation policy is not set.' : _s(b['policy_text']), style: const TextStyle(color: C.muted)),
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
              Text(l['value'] == null ? '[price?]' : '${_rs(l['value'])}${f['gst_on'] == true ? ' +${_s(l['gst_pct'])}%' : ''}',
                  style: TextStyle(fontSize: 12.5, color: l['value'] == null ? C.warn : C.ink)),
            ]),
          ),
        const Divider(color: C.line),
        if ((f['discount'] is num) && (f['discount'] as num) > 0) _line(f['complimentary'] == true ? 'Complimentary' : 'Discount', _rs(f['discount'])),
        if (f['gst_on'] == true) _line('CGST + SGST', '${_rs(f['cgst'])} + ${_rs(f['sgst'])}'),
        _line('Total', _rs(f['total']), color: C.ink),
        _line('Received', _rs(f['paid'])),
        _line('Due', f['balance'] == null ? 'rate empty' : _rs(f['balance']), color: C.accent),
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
            TextButton(onPressed: () => Native.openExternal(url: _s(r['portal'])), child: const Text('Open e-FRRO')),
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
          Text('${_s(data['guest'])} · ${_s(data['kind']) == 'arrival' ? 'arrivals' : 'departure'} · ${_s(data['booking'])}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          _line('Until when', _s(data['due_local']), color: data['overdue'] == true ? C.bad : null),
          _line('Ref', _s(data['ref'])),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 6, children: [
            GlassButton(label: 'See data', height: 38, onTap: () => _show(context)),
            if (_s(data['status']) == 'due')
              GlassButton(
                  label: 'I have filled it in',
                  height: 38,
                  onTap: () async {
                    final f = await _form(context, 'Form C ref', const [('ref', 'Portal reference (if any)')], ok: 'Record');
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
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Your approval' : _s(show['title']),
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
    final f = await _form(context, 'Refund sent', const [('ref', 'UTR / ref'), ('mode', 'upi / bank / cash / card')], ok: 'Record');
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
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'accepted', 'rejected' => 'no', 'stale' => 'stale', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' || st == 'stale' ? C.bad : C.ok)),
        ]),
        Text(_s(show['title']), style: const TextStyle(fontSize: 13)),
        if (kind == 'bill')
          for (final l in _list(show['lines']).take(12))
            _line(_s(l['text']), '${_rs(l['value'])}${show['gst_on'] == true ? ' +${_s(l['gst_pct'])}%' : ''}'),
        if (kind == 'bill') _line('Total', _rs(show['total']), color: C.ink),
        _line('Why', _s(show['why'] ?? show['reason'])),
        _line('How', _s(show['how'])),
        for (final x in _strs(show['checks'])) Text('⚠ $x', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved' && kind == 'refund' && show['done'] != true)
          GlassButton(label: 'Refund sent', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : _refundDone),
        const Text('Hoola does not take or give money; you send the refund from your own app / bank.', style: TextStyle(fontSize: 11, color: C.faint)),
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
        if (link.isEmpty) throw Exception('No guest mobile.');
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
    final f = await _form(context, 'Change message', const [('text', 'Message')], initial: {'text': _s(_x['text'])}, ok: 'Save');
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
          Expanded(child: Text('to ${_s(x['to'])} · ${_s(x['kind'])} · ${_s(x['booking'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st == 'draft' ? 'draft' : (st == 'sent' ? 'sent' : st), fg: st == 'sent' ? C.ok : C.chip),
        ]),
        Text(_s(x['text']), style: const TextStyle(fontSize: 13)),
        if (x['no_messages'] == true) const Text('⚠ This guest has declined messages.', style: TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'draft')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: 'From your own WhatsApp', icon: Icons.send_rounded, height: 40, onTap: _busy ? null : () => _send('self')),
            GlassButton(label: 'Business number se', height: 40, onTap: _busy ? null : () => _send('business')),
            GlassButton(label: 'Edit', height: 40, onTap: _busy ? null : _edit),
            GlassButton(
                label: 'Remove',
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
        _line('Room', '${_s(b['type_name'])}${_s(b['room']).isEmpty ? '' : ' · room ${_s(b['room'])}'}'),
        _line('Date', '${_s(b['arrive'])} → ${_s(b['depart'])} (${_s(b['nights_count'])} nights) · ${_s(b['adults'])} guests'),
        _line('From where', '${_s(b['source_label'])}${_s(b['ota_ref']).isEmpty ? '' : ' · ${_s(b['ota_ref'])}'}'),
        _line('Total', b['total'] == null ? 'rate empty: ${_strs(b['blanks']).join(', ')}' : _rs(b['total']),
            color: b['total'] == null ? C.warn : null),
        if (b['balance'] is num && (b['balance'] as num) > 0) _line('Due', _rs(b['balance']), color: C.accent),
        if (_s(b['hold_until']).isNotEmpty) _line('Hold', 'until ${_s(b['hold_until'])} (confirmed when advance arrives)'),
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
            'overbook' => 'Overbooking prevented',
            'formc' => 'Form C (foreign guest)',
            'hold_released' => 'Hold expired',
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
          Text('Today\'s front desk', style: TextStyle(fontWeight: FontWeight.w800)),
        ]),
        Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
        if (rep.isNotEmpty) _line('Yesterday', 'occupancy ${_s(rep['occupancy_pct'])}% · ADR ${_rs(rep['adr'])} · RevPAR ${_rs(rep['revpar'])}'),
        const SizedBox(height: 6),
        GlassButton(
            label: 'Open front office',
            height: 38,
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FrontofficeScreen(app: app)))),
      ]),
    );
  }
}
