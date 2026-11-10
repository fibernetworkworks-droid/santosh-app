/// Profile > Shaadi Sahayak: Hoola as the wedding planner's coworker (Indian weddings, every community).
/// Aaj (this week's functions, checklist due, payments due, cards waiting) · Shaadiyan (wedding file: functions with dates +
/// muhurat as the pandit gave it, panchang facts, day-wise timeline, guests + RSVP + headcount, rooms, vendors with HER quotes,
/// budget, checklist, shagun register, registration checklist) · Niyam (firm, mode, fee, GST, UPI, stages).
/// Vendor booking / advance / payment / spend (fingerprint once a phone key is set up), the client quote / payment request and every
/// message to guests run only after HER tap. Hoola never invents a price, date or muhurat and never sends a message itself.
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
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());
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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label),
                maxLines: k == 'text' || k == 'notes' || k == 'terms' || k == 'rows' ? 4 : 1),
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

Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']);
  if (wa.isEmpty && sms.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
  ]);
}

class ShaadiScreen extends StatefulWidget {
  const ShaadiScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ShaadiScreen> createState() => _ShaadiScreenState();
}

class _ShaadiScreenState extends State<ShaadiScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/shaadi'));
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
      .push(MaterialPageRoute(builder: (_) => ShaadiWeddingPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newWedding() async {
    final f = await _form(context, 'New wedding', const [
      ('bride', 'Bride\'s name'),
      ('groom', 'Groom\'s name'),
      ('community', 'Community (marathi / punjabi / muslim / tamil / christian ...)'),
      ('city', 'City'),
      ('state', 'State (e.g. Maharashtra)'),
      ('venue', 'Venue'),
      ('budget', 'Total budget (e.g. 25 lakh)'),
      ('guests_estimate', 'Estimated guests'),
      ('client', 'Client (if you are a planner)'),
      ('client_phone', 'Client phone'),
    ]);
    if (f == null) return;
    final r = await _run('POST', '/api/shaadi/weddings', {
      ...f,
      if (f['guests_estimate'] != null) 'guests_estimate': _n(f['guests_estimate']),
    });
    final id = _s(_m(r?['wedding'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  Widget _aaj() {
    final day = _m(_d?['day']);
    final waiting = _list(day['waiting']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (waiting.isNotEmpty) const Caption('NEEDS YOUR APPROVAL'),
      for (final c in waiting)
        Padding(padding: const EdgeInsets.only(bottom: 10), child: ShaadiCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      if (_strs(day['soon']).isNotEmpty) ...[const Caption('THIS WEEK'), for (final x in _strs(day['soon'])) Text('• $x')],
      if (_strs(day['todo']).isNotEmpty) ...[
        const SizedBox(height: 8),
        const Caption('WORK'),
        for (final x in _strs(day['todo'])) Text('• $x', style: TextStyle(color: x.contains('(der)') ? C.warn : C.ink)),
      ],
      if (_strs(day['payments']).isNotEmpty) ...[const SizedBox(height: 8), const Caption('PAYMENTS DUE'),
        for (final x in _strs(day['payments'])) Text('• $x')],
    ]);
  }

  Widget _weddings() {
    final ws = _list(_d?['weddings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'New wedding', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newWedding),
      const SizedBox(height: 12),
      if (ws.isEmpty) const Text('No weddings yet.', style: TextStyle(color: C.muted)),
      for (final w in ws)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Press(
            onTap: () => _open(_s(w['id'])),
            child: Glass(child: Row(children: [
              const Icon(Icons.favorite_rounded, color: C.accent),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(w['number'])} · ${_s(w['title'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text([_s(w['community_label']), _s(w['city']), if (_s(w['first_date']).isNotEmpty) _s(w['first_date']),
                  if (w['days_left'] != null) '${_s(w['days_left'])} days left'].where((x) => x.isNotEmpty).join(' · '),
                    style: const TextStyle(fontSize: 12.5, color: C.muted)),
              ])),
              Pill(_s(w['status'])),
            ])),
          ),
        ),
    ]);
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['firm']).isEmpty ? 'No firm name' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('Mode: ${_s(st['mode']) == 'agency' ? 'planner for clients' : 'your own family\'s wedding'}'),
        Text('Fee: ${_s(st['fee_mode'])} ${_s(st['fee_value'])} · GST ${_s(st['gst_pct'])}% ${_s(st['gstin']).isEmpty ? '(No GSTIN: GST will not be added)' : _s(st['gstin'])}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
        Text('UPI: ${_s(st['upi_id']).isEmpty ? '-' : _s(st['upi_id'])} · Morning note ${_s(st['morning_time'])}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final x in _list(st['stages'])) Text('• ${_s(x['label'])}: ${_s(x['pct'])}%', style: const TextStyle(fontSize: 12.5)),
      ])),
      const SizedBox(height: 10),
      GradientButton(label: 'Edit rules', icon: Icons.tune_rounded, height: 44, onTap: _busy ? null : () async {
        final f = await _form(context, 'Rules', const [
          ('firm', 'Firm / your name'), ('mode', 'Mode: family / agency'), ('gstin', 'GSTIN (if any)'), ('phone', 'Phone'),
          ('upi_id', 'UPI ID (for client payments)'), ('fee_mode', 'Fee: none / percent / flat'), ('fee_value', 'Fee (% or rupees)'),
          ('gst_pct', 'GST % (confirm with your CA)'), ('morning_time', 'Morning note (HH:MM)'), ('terms', 'Terms'),
        ], initial: {for (final k in ['firm', 'mode', 'gstin', 'phone', 'upi_id', 'fee_mode', 'morning_time', 'terms']) k: _s(st[k])});
        if (f == null) return;
        await _run('PUT', '/api/shaadi/settings', {
          ...f,
          if (f['fee_value'] != null) 'fee_value': _n(f['fee_value']),
          if (f['gst_pct'] != null) 'gst_pct': _n(f['gst_pct']),
        });
      }),
      const SizedBox(height: 10),
      const Text('The muhurat is the priest\'s decision; Hoola only shows the panchang (tithi, nakshatra) for the date you give.'
          'Bookings, advances, payments and messages to guests go only with your tap.', style: TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Today', 'Weddings', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Shaadi Sahayak'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: Column(children: [
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i))),
          ]),
        ),
        Expanded(
          child: _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _weddings, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

class ShaadiWeddingPage extends StatefulWidget {
  const ShaadiWeddingPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<ShaadiWeddingPage> createState() => _ShaadiWeddingPageState();
}

class _ShaadiWeddingPageState extends State<ShaadiWeddingPage> {
  Map<String, dynamic>? _w;
  Map<String, dynamic> _guests = {};
  Map<String, dynamic> _gifts = {};
  Map<String, dynamic> _panchang = {};
  Map<String, dynamic> _reg = {};
  int _tab = 0;
  bool _busy = false;
  String get _base => '/api/shaadi/weddings/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final w = _m(await widget.app.api!.call('GET', _base));
      final g = _m(await widget.app.api!.call('GET', '$_base/guests'));
      if (mounted) setState(() {
        _w = w;
        _guests = g;
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

  List<Map<String, dynamic>> get _fns => _list(_w?['functions']);

  // ---- functions
  Future<void> _editFn(Map<String, dynamic>? f) async {
    final r = await _form(context, f == null ? 'New function' : _s(f['name']), const [
      ('name', 'Name (e.g. Mehendi)'), ('date', 'Date (DD-MM-YYYY)'), ('start', 'Start (e.g. 7 pm)'), ('end', 'End'),
      ('venue', 'Place'), ('muhurat', 'Muhurat (as told by the priest)'), ('muhurat_by', 'Told by (priest\'s name)'),
      ('notes', 'Note'),
    ], initial: f == null ? const {} : {for (final k in ['name', 'date', 'start', 'end', 'venue', 'muhurat', 'muhurat_by', 'notes']) k: _s(f[k])});
    if (r == null) return;
    await _run('POST', '$_base/functions', {...r, if (f != null) 'fn': _s(f['id']), if (f == null) 'add': true});
  }

  Widget _functions() {
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(child: GradientButton(label: 'Add function', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : () => _editFn(null))),
        const SizedBox(width: 8),
        GlassButton(label: 'Panchang', icon: Icons.brightness_5_rounded, height: 44, onTap: _busy ? null : () async {
          final p = await _call(context, widget.app, 'GET', '$_base/panchang');
          if (p != null && mounted) setState(() => _panchang = p);
        }),
      ]),
      const SizedBox(height: 6),
      const Text('The muhurat is only the priest\'s; Hoola shows the panchang for the date (tithi, nakshatra, holiday).',
          style: TextStyle(fontSize: 12, color: C.faint)),
      for (final d in _list(_panchang['days']))
        if (_s(d['date']).isNotEmpty)
          Text('• ${_s(d['function'])} ${_s(d['date'])}: ${_s(d['vaar'])}, ${_s(d['tithi'])} ${_s(d['paksha'])}, ${_s(d['nakshatra'])}'
              '${_strs(d['holidays']).isEmpty ? '' : ' · ${_strs(d['holidays']).join(', ')}'}'
              '${_s(d['muhurat']).isEmpty ? '' : ' · muhurat ${_s(d['muhurat'])} (${_s(d['muhurat_by'])})'}',
              style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 10),
      for (final f in _fns)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(_s(f['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
              IconButton(icon: const Icon(Icons.edit_rounded, color: C.faint), onPressed: _busy ? null : () => _editFn(f)),
              IconButton(icon: const Icon(Icons.delete_outline_rounded, color: C.faint),
                  onPressed: _busy ? null : () => _run('POST', '$_base/functions', {'fn': _s(f['id']), 'remove': true})),
            ]),
            Text([_s(f['date']).isEmpty ? 'date pending' : _s(f['date']), _s(f['start']), _s(f['venue'])].where((x) => x.isNotEmpty).join(' · '),
                style: const TextStyle(fontSize: 12.5, color: C.muted)),
            if (_s(f['muhurat']).isNotEmpty) Text('Muhurat: ${_s(f['muhurat'])} (${_s(f['muhurat_by'])})', style: const TextStyle(fontSize: 12.5)),
            for (final r in _list(f['timeline'])) Text('${_s(r['time']).isEmpty ? '--:--' : _s(r['time'])}  ${_s(r['what'])}',
                style: const TextStyle(fontSize: 12)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, children: [
              GlassButton(label: 'Make timeline', icon: Icons.schedule_rounded, height: 38, onTap: _busy ? null : () =>
                  _run('POST', '$_base/timeline', {'fn': _s(f['id']), 'starter': true})),
              GlassButton(label: 'Invite draft', icon: Icons.mail_rounded, height: 38, onTap: _busy ? null : () => _invite(_s(f['id']))),
            ]),
          ]),
        ),
    ]);
  }

  Future<void> _invite(String fn) async {
    final t = await _call(context, widget.app, 'GET', '$_base/invite_text?fn=$fn');
    if (t == null || !mounted) return;
    final f = await _form(context, 'Message to guests', const [('text', 'Message ({name} = guest\'s name)')],
        ok: 'Make card for approval', initial: {'text': _s(t['text'])});
    if (f == null) return;
    await _run('POST', '$_base/message', {'text': f['text'], 'fn': fn});
  }

  // ---- guests
  Widget _guestsTab() {
    final hc = _list(_w?['headcount']);
    final gs = _list(_guests['guests']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(child: GradientButton(label: 'Add guest', icon: Icons.person_add_rounded, height: 44, onTap: _busy ? null : () async {
          final f = await _form(context, 'Guests', const [
            ('name', 'Name'), ('side', 'Side: bride / groom / common'), ('phone', 'Phone'), ('adults', 'Adults'), ('kids', 'Children'),
            ('city', 'City'), ('diet', 'Food: veg / jain / nonveg'), ('arrive', 'Arrival (DD-MM-YYYY)'), ('depart', 'Departure'),
          ]);
          if (f == null) return;
          await _run('POST', '$_base/guests', {
            ...f,
            if (f['adults'] != null) 'adults': _n(f['adults']),
            if (f['kids'] != null) 'kids': _n(f['kids']),
            if (f['arrive'] != null) 'needs_room': true,
          });
        })),
        const SizedBox(width: 8),
        GlassButton(label: 'Sheet', icon: Icons.upload_file_rounded, height: 44, onTap: _busy ? null : _importGuests),
      ]),
      const SizedBox(height: 10),
      const Caption('COUNT (FOR THE CATERER)'),
      for (final h in hc)
        Text('• ${_s(h['function'])}: yes ${_s(h['yes'])} · maybe ${_s(h['maybe'])} · pending ${_s(h['pending'])} · no ${_s(h['no'])}',
            style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 10),
      GlassButton(label: 'Remind those who have not replied', icon: Icons.notifications_rounded, height: 40, onTap: _busy ? null : () async {
        final t = await _call(context, widget.app, 'GET', '$_base/invite_text?kind=rsvp');
        if (t == null || !mounted) return;
        final f = await _form(context, 'RSVP reminder', const [('text', 'Message')], ok: 'Make card for approval', initial: {'text': _s(t['text'])});
        if (f != null) await _run('POST', '$_base/message', {'text': f['text'], 'pending': true});
      }),
      const SizedBox(height: 10),
      Caption('GUESTS (${_s(_guests['count'])} · ${_s(_guests['heads'])} people)'),
      for (final g in gs)
        Glass(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          child: Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(g['name'])} · ${_s(g['side'])} · ${_s(g['heads'])} log', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(_m(g['rsvp']).entries.map((e) => '${e.key}: ${e.value}').join(', '), style: const TextStyle(fontSize: 12, color: C.muted)),
            ])),
            PopupMenuButton<String>(
              onSelected: (a) => _run('POST', '$_base/rsvp', {'guest': _s(g['id']), 'answer': a}),
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'yes', child: Text('Yes, will come')),
                PopupMenuItem(value: 'maybe', child: Text('Maybe')),
                PopupMenuItem(value: 'no', child: Text('No')),
              ],
            ),
          ]),
        ),
    ]);
  }

  Future<void> _importGuests() async {
    final pick = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['csv', 'xlsx'], withData: true);
    final file = pick?.files.firstOrNull;
    if (file == null || file.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('$_base/guests/import', file.name, file.bytes!);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  // ---- rooms
  Widget _roomsTab() {
    final r = _m(_w?['rooms']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Add room block', icon: Icons.hotel_rounded, height: 44, onTap: _busy ? null : () async {
        final f = await _form(context, 'Rooms', const [
          ('place', 'Hotel / homestay / house'), ('label', 'Room label (e.g. D)'), ('count', 'How many rooms'), ('capacity', 'How many people in one room'),
          ('check_in', 'Check-in (DD-MM-YYYY)'), ('check_out', 'Check-out'), ('rate', 'Hotel rate / night (their quote)'),
        ]);
        if (f == null) return;
        await _run('POST', '$_base/rooms', {
          ...f,
          if (f['count'] != null) 'count': _n(f['count']),
          if (f['capacity'] != null) 'capacity': _n(f['capacity']),
          if (f['rate'] != null) 'rate': _n(f['rate']),
        });
      }),
      const SizedBox(height: 8),
      Text(_s(r['say']), style: const TextStyle(fontSize: 12.5)),
      for (final x in _list(r['waiting']))
        Glass(margin: const EdgeInsets.only(top: 6), padding: const EdgeInsets.all(10), child: Row(children: [
          Expanded(child: Text('${_s(x['name'])} · ${_s(x['heads'])} log · ${_s(x['arrive'])} → ${_s(x['depart'])}')),
          GlassButton(label: 'Room do', height: 36, onTap: _busy ? null : () async {
            final f = await _form(context, 'Which room?', const [('room', 'Room label (e.g. D-1)')]);
            if (f != null) await _run('POST', '$_base/rooms/assign', {'guest': _s(x['id']), 'room': f['room']});
          }),
        ])),
      const SizedBox(height: 10),
      for (final x in _list(r['rooms']))
        Glass(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          child: Text('${_s(x['place'])} ${_s(x['label'])} · ${_s(x['heads'])}/${_s(x['capacity'])} · ${_s(x['check_in'])} → ${_s(x['check_out'])}\n'
              '${_list(x['guests']).map((g) => _s(g['name'])).join(', ')}', style: const TextStyle(fontSize: 12.5)),
        ),
      const Text('Hoola does not overbook: more people than space will not go into one room.', style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  // ---- vendors
  Widget _vendorsTab() {
    final vs = _list(_w?['vendors']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Add vendor', icon: Icons.storefront_rounded, height: 44, onTap: _busy ? null : () async {
        final f = await _form(context, 'Vendor (their quote)', const [
          ('name', 'Name'), ('kind', 'Trade: decor / caterer / photographer / mehendi / dj / pandit / makeup / transport'),
          ('phone', 'Phone'), ('quote', 'Their quote (rupees)'), ('per_plate', 'Per plate (caterer)'), ('plates', 'Plates'),
          ('quote_note', 'What is included'), ('advance', 'Advance (rupees)'), ('advance_due', 'Advance date'),
        ]);
        if (f == null) return;
        await _run('POST', '$_base/vendors', {
          'name': f['name'], 'kind': f['kind'], 'phone': f['phone'], 'quote_note': f['quote_note'],
          if (f['quote'] != null) 'quote': _n(f['quote']),
          if (f['per_plate'] != null) 'per_plate': _n(f['per_plate']),
          if (f['plates'] != null) 'plates': _n(f['plates']),
          if (f['advance'] != null) 'schedule': [{'label': 'Advance', 'amount': _n(f['advance']), 'due': f['advance_due'] ?? ''}],
        });
      }),
      const SizedBox(height: 6),
      const Text('The price is only what the vendor gave; Hoola never makes up prices. Booking and every payment need your tap (fingerprint).',
          style: TextStyle(fontSize: 12, color: C.faint)),
      const SizedBox(height: 10),
      for (final v in vs)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(v['name'])} · ${_s(v['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(v['status']), fg: _s(v['status']) == 'booked' ? C.ok : C.chip),
            ]),
            Text('Quote ${_s(v['quote_text'])} · paid ${_rs(v['paid'])} · due ${_rs(v['due'])}', style: const TextStyle(fontSize: 12.5)),
            if (_s(v['quote_note']).isNotEmpty) Text(_s(v['quote_note']), style: const TextStyle(fontSize: 12, color: C.muted)),
            for (final x in _list(v['schedule']))
              Row(children: [
                Expanded(child: Text('• ${_s(x['label'])} ${_rs(x['amount'])} ${_s(x['due'])} (${_s(x['status'])})', style: const TextStyle(fontSize: 12))),
                if (_s(v['status']) == 'booked' && _s(x['status']) == 'planned')
                  TextButton(onPressed: _busy ? null : () => _run('POST', '$_base/vendors/${_s(v['id'])}/pay', {'item': _s(x['id'])}),
                      child: const Text('To pay')),
                if (_s(x['status']) == 'approved')
                  TextButton(onPressed: _busy ? null : () async {
                    final f = await _form(context, 'I have paid', const [('ref', 'UTR / cheque (last digits)')]);
                    if (f != null) await _run('POST', '$_base/vendors/${_s(v['id'])}/paid', {'item': _s(x['id']), 'ref': f['ref'] ?? ''});
                  }, child: const Text('I have paid')),
              ]),
            if (_s(v['status']) == 'quoted')
              GlassButton(label: 'To book', icon: Icons.verified_rounded, height: 38,
                  onTap: _busy ? null : () => _run('POST', '$_base/vendors/${_s(v['id'])}/book')),
          ]),
        ),
    ]);
  }

  // ---- budget + checklist
  Widget _budgetTab() {
    final b = _m(_w?['budget']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(b['say']))),
      const SizedBox(height: 8),
      GradientButton(label: 'Write budget', icon: Icons.account_balance_wallet_rounded, height: 44, onTap: _busy ? null : () async {
        final f = await _form(context, 'Budget', const [('amount', 'Amount'), ('head', 'For what (empty = total budget)'), ('fn', 'Function (empty = whole wedding)')]);
        if (f != null) await _run('POST', '$_base/budget', {...f, 'amount': _n(f['amount'])});
      }),
      for (final w in _strs(b['warnings'])) Text('⚠ $w', style: const TextStyle(color: C.warn, fontSize: 12.5)),
      const SizedBox(height: 8),
      for (final r in _list(b['rows']))
        Text('• ${_s(r['function'])} / ${_s(r['head_label'])}: budget ${_rs(r['planned'])} · confirmed ${_rs(r['committed'])} · paid ${_rs(r['paid'])}',
            style: TextStyle(fontSize: 12.5, color: r['over'] == true ? C.warn : C.ink)),
    ]);
  }

  Widget _checklistTab() {
    final items = _list(_w?['checklist']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GlassButton(label: 'Registration checklist', icon: Icons.gavel_rounded, height: 40, onTap: _busy ? null : () async {
        final r = await _call(context, widget.app, 'GET', '$_base/registration');
        if (r != null && mounted) setState(() => _reg = r);
      }),
      if (_reg.isNotEmpty)
        Glass(margin: const EdgeInsets.only(top: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(_reg['law']), style: const TextStyle(fontWeight: FontWeight.w800)),
          for (final x in _strs(_reg['items'])) Text('• $x', style: const TextStyle(fontSize: 12.5)),
          if (_s(_reg['state_note']).isNotEmpty) Text(_s(_reg['state_note']), style: const TextStyle(fontSize: 12, color: C.muted)),
          Text(_s(_reg['note']), style: const TextStyle(fontSize: 11, color: C.faint)),
        ])),
      const SizedBox(height: 10),
      for (final c in items)
        CheckboxListTile(
          value: c['done'] == true,
          onChanged: _busy ? null : (v) => _run('POST', '$_base/checklist', {'item': _s(c['id']), 'done': v == true}),
          title: Text(_s(c['what']), style: const TextStyle(fontSize: 13.5)),
          subtitle: Text(_s(c['due']).isEmpty ? 'once the date is fixed' : 'until ${_s(c['due'])}',
              style: TextStyle(fontSize: 12, color: _s(c['state']) == 'late' ? C.warn : C.muted)),
        ),
    ]);
  }

  // ---- shagun (only her screen)
  Widget _shagunTab() {
    final gs = _list(_gifts['gifts']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(child: GradientButton(label: 'Write shagun', icon: Icons.redeem_rounded, height: 44, onTap: _busy ? null : () async {
          final f = await _form(context, 'Shagun / gift', const [
            ('giver', 'Given by'), ('relation', 'Relation'), ('value', 'Amount / estimated value'),
            ('kind', 'cash / upi / cheque / gold / item'), ('what', 'What (if it is a gift)'), ('side', 'Side: bride / groom / common'),
            ('for_whom', 'For whom: bride / groom / both'),
          ]);
          if (f == null) return;
          await _run('POST', '$_base/gifts', {...f, if (f['value'] != null) 'value': _n(f['value'])});
          await _loadGifts();
        })),
        const SizedBox(width: 8),
        GlassButton(label: 'View', icon: Icons.visibility_rounded, height: 44, onTap: _busy ? null : _loadGifts),
      ]),
      const SizedBox(height: 6),
      const Text('This register is only yours: it is never shown to staff, guests or any avatar. Hoola does not keep dowry accounts.',
          style: TextStyle(fontSize: 12, color: C.faint)),
      if (_gifts.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Total ${_rs(_gifts['total'])} · ${_s(_gifts['count'])} entries', style: const TextStyle(fontWeight: FontWeight.w800)),
        Wrap(spacing: 8, children: [
          GlassButton(label: 'Bride\'s list PDF', height: 38, onTap: _busy ? null : () => _run('POST', '$_base/gifts/list', {'for_whom': 'bride'})),
          GlassButton(label: 'Groom\'s list PDF', height: 38, onTap: _busy ? null : () => _run('POST', '$_base/gifts/list', {'for_whom': 'groom'})),
        ]),
        for (final g in gs)
          ListTile(
            dense: true,
            title: Text('${_s(g['giver'])} (${_s(g['relation'])}) · ${_s(g['kind'])} ${_rs(g['value'])}'),
            subtitle: Text([_s(g['what']), _s(g['day']), _s(g['for_whom'])].where((x) => x.isNotEmpty).join(' · ')),
            trailing: IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _busy ? null : () async {
              await _run('DELETE', '/api/shaadi/gifts/${_s(g['id'])}');
              await _loadGifts();
            }),
          ),
      ],
    ]);
  }

  Future<void> _loadGifts() async {
    try {
      final g = _m(await widget.app.api!.call('GET', '$_base/gifts'));
      if (mounted) setState(() => _gifts = g);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _cardsTab() {
    final cs = _list(_w?['cards']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      if (cs.isEmpty) const Text('No cards.', style: TextStyle(color: C.muted)),
      for (final c in cs)
        Padding(padding: const EdgeInsets.only(bottom: 10), child: ShaadiCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Functions', 'Guests', 'Rooms', 'Vendors', 'Budget', 'Checklist', 'Shagun', 'Cards'];
    final w = _w;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(w == null ? 'Shaadi' : '${_s(w['number'])} · ${_s(w['title'])}'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: w == null
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              SizedBox(
                height: 46,
                child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
                  for (var i = 0; i < tabs.length; i++)
                    Padding(padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i))),
                ]),
              ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: _load,
                  child: [_functions, _guestsTab, _roomsTab, _vendorsTab, _budgetTab, _checklistTab, _shagunTab, _cardsTab][_tab](),
                ),
              ),
            ]),
    );
  }
}

/// shaadi_card: anything that waits for HER tap (vendor booking / payment / spend with fingerprint, client quote / payment
/// request, messages to guests). Also in calls. One card per id, updated in place.
class ShaadiCardCard extends StatefulWidget {
  const ShaadiCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ShaadiCardCard> createState() => _ShaadiCardCardState();
}

class _ShaadiCardCardState extends State<ShaadiCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  Map<String, dynamic> _res = {};

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/shaadi/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Wedding expense' : _s(show['title']),
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
        r = await widget.app.api!.call('POST', '/api/shaadi/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/shaadi/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          if (_m(m['card']).isNotEmpty) _c = _m(m['card']);
          _res = m;
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

  String _title() {
    final sh = _m(_c['show']);
    return switch (_s(_c['kind'])) {
      'vendor_book' => 'Booking: ${_s(sh['vendor'])} (${_s(sh['kind'])}) · ${_rs(sh['quote'])}',
      'vendor_pay' => 'Payment: ${_s(sh['vendor'])} · ${_s(sh['item'])} ${_rs(sh['amount'])}',
      'spend' => 'Expense: ${_s(sh['what'])} · ${_rs(sh['amount'])}',
      'client_quote' => 'Client quote: ${_s(sh['client'])} · ${_rs(sh['total'])}',
      'client_pay' => 'Client se: ${_s(sh['stage'])} ${_rs(sh['amount'])}',
      _ => 'Message: to ${_s(sh['count'])} people',
    };
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final sh = _m(c['show']);
    final st = _s(c['status']);
    final res = _res.isNotEmpty ? _res : _m(c['result']);
    final links = _list(res['links']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(c['money'] == true ? Icons.currency_rupee_rounded : Icons.favorite_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · ${_title()}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'stale', 'done' => 'done', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text(_s(sh['title']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final f in _strs(sh['functions'])) Text('• $f', style: const TextStyle(fontSize: 12)),
        if (_s(sh['quote_note']).isNotEmpty) Text(_s(sh['quote_note']), style: const TextStyle(fontSize: 12)),
        if (_m(sh['advance']).isNotEmpty)
          Text('Advance: ${_s(_m(sh['advance'])['label'])} ${_rs(_m(sh['advance'])['amount'])} ${_s(_m(sh['advance'])['due'])}',
              style: const TextStyle(fontSize: 12.5)),
        for (final x in _list(sh['schedule'])) Text('• ${_s(x['label'])} ${_rs(x['amount'])} ${_s(x['due'])}', style: const TextStyle(fontSize: 12)),
        if (_s(c['kind']) == 'client_quote') ...[
          if ((sh['fee'] ?? 0) != 0) Text('Fee: ${_rs(sh['fee'])} (${_s(sh['fee_note'])})', style: const TextStyle(fontSize: 12.5)),
          for (final x in _list(sh['lines'])) Text('• ${_s(x['name'])} ${_rs(x['amount'])}', style: const TextStyle(fontSize: 12)),
          Text('GST ${_rs(sh['gst'])} · Total ${_rs(sh['total'])} · until ${_s(sh['valid_until'])}', style: const TextStyle(fontSize: 12.5)),
        ],
        if (_s(c['kind']) == 'message') ...[
          Text(_s(sh['audience']), style: const TextStyle(fontSize: 12, color: C.muted)),
          Text(_s(sh['text']), style: const TextStyle(fontSize: 12.5)),
          for (final x in _strs(sh['skipped'])) Text('– $x', style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ],
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_m(res['draft']).isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_m(res['draft']))],
        if (_s(res['upi']).isNotEmpty)
          GlassButton(label: 'Copy / open UPI link', icon: Icons.qr_code_rounded, height: 38, onTap: () => Native.openExternal(url: _s(res['upi']))),
        for (final l in links)
          Row(children: [
            Expanded(child: Text(_s(l['name']), style: const TextStyle(fontSize: 12.5))),
            if (_s(l['wa']).isNotEmpty)
              IconButton(icon: const Icon(Icons.chat_rounded, color: C.ok), onPressed: () => Native.openExternal(url: _s(l['wa']))),
            if (_s(l['sms']).isNotEmpty)
              IconButton(icon: const Icon(Icons.sms_rounded, color: C.faint), onPressed: () => Native.openExternal(url: _s(l['sms']))),
          ]),
        if (_s(c['kind']) == 'spend' && st == 'approved')
          GlassButton(label: 'I have paid', icon: Icons.check_rounded, height: 38, onTap: _busy ? null : () async {
            await _call(context, widget.app, 'POST', '/api/shaadi/cards/${_s(c['id'])}/paid', {'ref': ''});
            widget.onDone?.call();
          }),
        const Text('Hoola does not send money or messages itself; you send them.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// shaadi_alert / shaadi_day: plain notes. Calls: no.
class ShaadiNoteCard extends StatelessWidget {
  const ShaadiNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Row(children: [
          const Icon(Icons.favorite_border_rounded, color: C.teal),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
          IconButton(
              icon: const Icon(Icons.open_in_new_rounded, color: C.faint),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShaadiScreen(app: app)))),
        ]),
      );
}
