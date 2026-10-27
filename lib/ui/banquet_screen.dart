/// Profile > Banquet Sahayak: Hoola as the banquet hall / lawn sales coworker.
/// Aaj (today / tomorrow's functions, holds ending, count locks, instalments, follow-ups, cards waiting) · Enquiry (paste a
/// WhatsApp / call note, leads) · Calendar (holds that expire, confirmed blocks; free halls for a date) · Booking (menu, quote,
/// payments, BEO, bill) · Venue (halls / lawns, plate packages, extras: HER prices only) · Niyam (GST, slots, hold hours, count
/// lock, payment schedule, cancellation / refund shown upfront, terms).
/// Quotation / terms / bill / any message to a client, hold -> confirmed, discounts and refunds (fingerprint once a phone key is
/// set up) and payment requests run only after HER tap. A double-booked hall + slot is refused by the server.
library;

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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label),
                maxLines: (k == 'text' || k == 'terms' || k == 'items' || k == 'notes' || k == 'beo_notes') ? 4 : 1),
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

Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']), upi = _s(draft['upi']);
  if (wa.isEmpty && sms.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (upi.isNotEmpty) const Pill('UPI link aapke UPI ID ka'),
  ]);
}

const _slotLabel = {'morning': 'Subah', 'evening': 'Shaam', 'full': 'Pura din'};

class BanquetScreen extends StatefulWidget {
  const BanquetScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<BanquetScreen> createState() => _BanquetScreenState();
}

class _BanquetScreenState extends State<BanquetScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _cal;
  Map<String, dynamic>? _free;
  int _tab = 0;
  bool _busy = false;
  late String _month = DateTime.now().toIso8601String().substring(0, 7);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/banquet'));
      final cal = _m(await widget.app.api!.call('GET', '/api/banquet/calendar', query: {'month': _month}));
      if (mounted) setState(() {
        _d = d;
        _cal = cal;
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
      .push(MaterialPageRoute(builder: (_) => BanquetBookingPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('AAPKI HAAN KA INTEZAAR'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: BanquetCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('today', 'AAJ KE FUNCTION'), ('tomorrow', 'KAL KE FUNCTION'), ('holds_expiring', 'HOLD KHATAM HONE WALE'),
        ('locks', 'FINAL COUNT LOCK PAAS')])
        if (_list(day[k]).isNotEmpty) ...[
          Caption(label),
          for (final b in _list(day[k])) _bookingTile(b),
          const SizedBox(height: 8),
        ],
      if (_strs(day['stages_due']).isNotEmpty) ...[const Caption('KISHT KA SAMAY'), for (final x in _strs(day['stages_due'])) Text('• $x')],
    ]);
  }

  Widget _bookingTile(Map<String, dynamic> b) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        child: InkWell(
          onTap: () => _open(_s(b['number'])),
          child: Row(children: [
            Icon(b['status'] == 'confirmed' ? Icons.event_available_rounded : Icons.hourglass_top_rounded,
                color: b['status'] == 'confirmed' ? C.ok : C.warn),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(b['number'])} · ${_s(b['client'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text('${_s(b['hall'])} · ${_s(b['day'])} ${_s(b['slot_label'])} · ${_s(b['event_label'])} · ${_s(b['final_count'] ?? b['guests'] ?? '?')} log',
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
            ])),
            Pill(_s(b['status_label'])),
          ]),
        ),
      );

  Future<void> _paste() async {
    final f = await _form(context, 'Nayi enquiry', const [
      ('text', 'WhatsApp / call note yahan chipkaiye (sirf likhi baat li jayegi)'),
      ('name', 'Naam'),
      ('phone', 'Mobile'),
      ('day', 'Tareekh (DD-MM-YYYY)'),
      ('slot', 'Subah / shaam / pura din'),
      ('guests', 'Kitne log'),
      ('diet', 'Veg / non-veg / Jain'),
    ], ok: 'Darj karo');
    if (f == null) return;
    await _run('POST', '/api/banquet/leads', {...f, if (f['guests'] != null) 'guests': _n(f['guests'])?.toInt(), 'source': 'paste'});
  }

  Widget _enquiry() {
    final leads = _list(_d?['leads']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Enquiry chipkao / likho', icon: Icons.content_paste_rounded, height: 46, onTap: _busy ? null : _paste),
      const SizedBox(height: 12),
      for (final l in leads)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(l['number'])} · ${_s(l['name']).isEmpty ? _s(l['phone']) : _s(l['name'])}',
                  style: const TextStyle(fontWeight: FontWeight.w700))),
              Pill(_s(l['status'])),
            ]),
            Text('${_s(l['event_label'])} ${_s(l['day'])} ${_slotLabel[_s(l['slot'])] ?? ''} · ${_s(l['guests'] ?? '?')} log · ${_s(l['diet'])}',
                style: const TextStyle(fontSize: 12.5, color: C.muted)),
            if (_s(l['follow_up']).isNotEmpty) Text('Follow-up: ${_s(l['follow_up'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
            Wrap(spacing: 8, runSpacing: 6, children: [
              if (_s(l['booking_id']).isEmpty && l['status'] != 'lost')
                GlassButton(label: 'Booking banao', icon: Icons.add_rounded, height: 38, onTap: _busy ? null : () async {
                  final f = await _form(context, 'Booking ${_s(l['number'])}', const [('hall', 'Hall / lawn'), ('package', 'Menu package')]);
                  if (f == null) return;
                  final r = await _run('POST', '/api/banquet/bookings', {
                    'lead': _s(l['number']),
                    if (f['hall'] != null) 'hall': f['hall'],
                    if (f['package'] != null) 'menu': [{'package': f['package']}],
                  });
                  final num_ = _s(_m(r?['booking'])['number']);
                  if (num_.isNotEmpty && mounted) _open(num_);
                }),
              if (l['status'] != 'lost' && l['status'] != 'booked')
                GlassButton(label: 'Nahi hua', height: 38, onTap: _busy ? null : () async {
                  final f = await _form(context, 'Kyun nahi hua?', const [('lost_reason', 'Daam / tareekh / jagah ...')]);
                  if (f == null) return;
                  await _run('PATCH', '/api/banquet/leads/${_s(l['id'])}', {'status': 'lost', ...f});
                }),
            ]),
          ]),
        ),
    ]);
  }

  Widget _calendar() {
    final days = _m(_cal?['days']);
    final keys = days.keys.toList()..sort();
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        IconButton(icon: const Icon(Icons.chevron_left_rounded), onPressed: () {
          final d = DateTime.parse('$_month-01');
          _month = DateTime(d.year, d.month - 1, 1).toIso8601String().substring(0, 7);
          _load();
        }),
        Expanded(child: Center(child: Text(_month, style: const TextStyle(fontWeight: FontWeight.w800)))),
        IconButton(icon: const Icon(Icons.chevron_right_rounded), onPressed: () {
          final d = DateTime.parse('$_month-01');
          _month = DateTime(d.year, d.month + 1, 1).toIso8601String().substring(0, 7);
          _load();
        }),
      ]),
      GlassButton(label: 'Kis tareekh khaali hai?', icon: Icons.search_rounded, height: 42, onTap: () async {
        final f = await _form(context, 'Khaali hall dhoondo', const [('day', 'Tareekh (YYYY-MM-DD)'), ('slot', 'Subah / shaam / pura din'),
          ('guests', 'Kitne log')]);
        if (f == null || f['day'] == null) return;
        try {
          final r = _m(await widget.app.api!.call('GET', '/api/banquet/free',
              query: {'day': f['day']!, if (f['slot'] != null) 'slot': f['slot']!, if (f['guests'] != null) 'guests': f['guests']!}));
          if (mounted) setState(() => _free = r);
        } catch (e) {
          if (mounted) _snack(context, '$e');
        }
      }),
      if (_free != null) ...[
        const SizedBox(height: 8),
        Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(_free!['say']), style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final h in _list(_free!['halls']))
            Text('${h['free'] == true ? '✓' : '✗'} ${_s(_m(h['hall'])['name'])} (${_s(h['capacity'])})'
                '${_s(h['why']).isEmpty ? '' : ' · ${_s(h['why'])}'}${h['fits'] == false ? ' · chhota' : ''}',
                style: TextStyle(fontSize: 12.5, color: h['free'] == true && h['fits'] == true ? C.ok : C.muted)),
        ])),
      ],
      const SizedBox(height: 12),
      if (keys.isEmpty) const Text('Is mahine koi hold / booking nahi.', style: TextStyle(color: C.faint)),
      for (final k in keys) ...[
        Caption(k),
        for (final x in _list(days[k]))
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(children: [
              Icon(x['kind'] == 'confirmed' ? Icons.lock_rounded : x['kind'] == 'hold' ? Icons.hourglass_top_rounded : Icons.block_rounded,
                  size: 16, color: x['kind'] == 'confirmed' ? C.ok : x['kind'] == 'hold' ? C.warn : C.faint),
              const SizedBox(width: 6),
              Expanded(child: Text('${_s(x['hall'])} · ${_slotLabel[_s(x['slot'])] ?? _s(x['slot'])} · ${_s(x['booking'])} ${_s(x['client'])}'
                  '${x['kind'] == 'hold' ? ' (hold ${_s(x['expires_at']).replaceAll('T', ' ').split('.').first} tak)' : ''}',
                  style: const TextStyle(fontSize: 12.5))),
            ]),
          ),
      ],
    ]);
  }

  Widget _bookings() {
    final bs = _list(_d?['bookings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Nayi booking', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : () async {
        final f = await _form(context, 'Nayi booking', const [('client', 'Client ka naam'), ('phone', 'Mobile'), ('hall', 'Hall / lawn'),
          ('day', 'Tareekh (YYYY-MM-DD)'), ('slot', 'Subah / shaam / pura din'), ('event_type', 'Function (shaadi / birthday ...)'),
          ('guests', 'Kitne log (andaaz)'), ('guarantee', 'Minimum guarantee plate'), ('package', 'Menu package')]);
        if (f == null) return;
        final pkg = f.remove('package');
        final r = await _run('POST', '/api/banquet/bookings', {
          ...f,
          if (pkg != null) 'menu': [{'package': pkg}],
          if (f['guests'] != null) 'guests': _n(f['guests'])?.toInt(),
          if (f['guarantee'] != null) 'guarantee': _n(f['guarantee'])?.toInt(),
        });
        final num_ = _s(_m(r?['booking'])['number']);
        if (num_.isNotEmpty && mounted) _open(num_);
      }),
      const SizedBox(height: 12),
      if (bs.isEmpty) const Text('Aage ki koi booking nahi.', style: TextStyle(color: C.faint)),
      for (final b in bs) _bookingTile(b),
    ]);
  }

  Widget _venue() {
    final hs = _list(_d?['halls']), ps = _list(_d?['packages']), xs = _list(_d?['extras']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Caption('HALL / LAWN'),
      for (final h in hs)
        Text('• ${_s(h['name'])} (${_s(h['kind'])}): ${_s(h['seated'])} baithe / ${_s(h['floating'])} khade · kiraya ${_s(h['rent_text'])}'),
      GlassButton(label: 'Hall / lawn jodo', icon: Icons.add_rounded, height: 40, onTap: () async {
        final f = await _form(context, 'Hall / lawn', const [('name', 'Naam'), ('kind', 'hall / lawn / terrace / poolside'),
          ('seated', 'Baithne wale'), ('floating', 'Khade (floating)'), ('rent', 'Kiraya ek slot (khane ke bina; khaali = khane ke saath)'),
          ('rent_full', 'Pure din ka kiraya')]);
        if (f == null) return;
        await _run('POST', '/api/banquet/halls', {
          ...f,
          for (final k in const ['seated', 'floating']) if (f[k] != null) k: _n(f[k])?.toInt(),
          for (final k in const ['rent', 'rent_full']) if (f[k] != null) k: _n(f[k]),
        });
      }),
      const SizedBox(height: 14),
      const Caption('MENU PACKAGE (PER PLATE)'),
      for (final p in ps) Text('• ${_s(p['name'])} (${_s(p['diet_label'])}) ${_s(p['price_text'])}'
          '${(p['min_plates'] ?? 0) == 0 ? '' : ' · kam se kam ${_s(p['min_plates'])}'}${_strs(p['items']).isEmpty ? '' : '\n   ${_strs(p['items']).join(', ')}'}'),
      GlassButton(label: 'Package jodo', icon: Icons.restaurant_menu_rounded, height: 40, onTap: () async {
        final f = await _form(context, 'Menu package', const [('name', 'Naam'), ('diet', 'veg / nonveg / jain'), ('price', 'Aapka daam per plate'),
          ('min_plates', 'Kam se kam plate'), ('items', 'Items (comma se)')]);
        if (f == null) return;
        await _run('POST', '/api/banquet/packages', {
          ...f,
          if (f['price'] != null) 'price': _n(f['price']),
          if (f['min_plates'] != null) 'min_plates': _n(f['min_plates'])?.toInt(),
        });
      }),
      const SizedBox(height: 14),
      const Caption('EXTRAS (DECOR, DJ, ROOMS ...)'),
      for (final x in xs) Text('• ${_s(x['name'])} ${_s(x['price_text'])}'),
      GlassButton(label: 'Extra jodo', icon: Icons.celebration_rounded, height: 40, onTap: () async {
        final f = await _form(context, 'Extra', const [('name', 'Naam'), ('price', 'Aapka daam'), ('unit', 'event / plate / room_night / hour / nos'),
          ('kind', 'decor / dj / rooms / sound / lights / other')]);
        if (f == null) return;
        await _run('POST', '/api/banquet/extras', {...f, if (f['price'] != null) 'price': _n(f['price'])});
      }),
    ]);
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['venue']).isEmpty ? 'Venue ka naam?' : _s(st['venue']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('GSTIN ${_s(st['gstin']).isEmpty ? '-' : _s(st['gstin'])} · UPI ${_s(st['upi_id']).isEmpty ? '-' : _s(st['upi_id'])}'),
        Text('Khana GST ${_s(st['gst_food'])}% · hall (bina khana) ${_s(st['gst_hall'])}% · extras ${_s(st['gst_extra'])}%'),
        Text(_s(st['gst_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
        SwitchListTile(contentPadding: EdgeInsets.zero, value: st['specified'] == true,
            title: const Text('Specified premises (hotel: koi room ₹7,500+)'),
            onChanged: (v) => _run('PUT', '/api/banquet/settings', {'specified': v})),
        Text('Hold ${_s(st['hold_hours'])} ghante · final count ${_s(st['lock_days'])} din pehle lock · music ${_s(st['music_end'])} tak'),
      ])),
      const SizedBox(height: 10),
      const Caption('CANCELLATION / REFUND (CLIENT KO PEHLE DIKHTA HAI)'),
      for (final x in _strs(st['cancel_lines'])) Text('• $x'),
      for (final x in _strs(st['cancel_notes'])) Text('⚠ $x', style: const TextStyle(color: C.warn, fontSize: 12)),
      const SizedBox(height: 8),
      const Caption('KISHTEIN'),
      for (final x in _list(st['stages'])) Text('• ${_s(x['label'])}: ${_s(x['pct'])}%${x['days_before'] == null ? ' (booking par)' : ' (${_s(x['days_before'])} din pehle)'}'),
      const SizedBox(height: 10),
      GlassButton(label: 'Venue badlo', icon: Icons.edit_rounded, height: 40, onTap: () async {
        final f = await _form(context, 'Venue', const [('venue', 'Venue ka naam'), ('gstin', 'GSTIN'), ('upi_id', 'Aapka UPI ID'),
          ('phone', 'Phone'), ('address', 'Pata'), ('hold_hours', 'Hold kitne ghante'), ('lock_days', 'Final count kitne din pehle'),
          ('music_end', 'Music kab tak (HH:MM)'), ('morning_time', 'Subah ka note (HH:MM)')],
            initial: {for (final k in const ['venue', 'gstin', 'upi_id', 'phone', 'address', 'music_end', 'morning_time']) k: _s(st[k]),
              'hold_hours': _s(st['hold_hours']), 'lock_days': _s(st['lock_days'])});
        if (f == null) return;
        await _run('PUT', '/api/banquet/settings', {
          ...f,
          for (final k in const ['hold_hours', 'lock_days']) if (f[k] != null) k: _n(f[k])?.toInt(),
        });
      }),
      GlassButton(label: 'Refund policy badlo', icon: Icons.policy_rounded, height: 40, onTap: () async {
        final f = await _form(context, 'Har line: "din pehle = % wapas" (jaise 90=90, 30=50, 7=25, 0=0)', const [('text', 'Policy')]);
        if (f == null || f['text'] == null) return;
        final rows = <Map<String, dynamic>>[];
        for (final part in f['text']!.split(RegExp(r'[,\n;]+'))) {
          final kv = part.split('=');
          if (kv.length == 2 && _n(kv[0]) != null && _n(kv[1]) != null) {
            rows.add({'days_before': _n(kv[0])!.toInt(), 'refund_pct': _n(kv[1])});
          }
        }
        if (rows.isEmpty) return;
        await _run('PUT', '/api/banquet/settings', {'cancel': rows});
      }),
      GlassButton(label: 'Booking ki shartein', icon: Icons.article_rounded, height: 40, onTap: () async {
        final f = await _form(context, 'Shartein (terms)', const [('terms', 'Aapki shartein')], initial: {'terms': _s(st['terms'])});
        if (f == null) return;
        await _run('PUT', '/api/banquet/settings', f);
      }),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Enquiry', 'Calendar', 'Booking', 'Venue', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Banquet Sahayak'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _enquiry, _calendar, _bookings, _venue, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

class BanquetBookingPage extends StatefulWidget {
  const BanquetBookingPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<BanquetBookingPage> createState() => _BanquetBookingPageState();
}

class _BanquetBookingPageState extends State<BanquetBookingPage> {
  Map<String, dynamic>? _b;
  bool _busy = false;
  Map<String, dynamic> _draft = {};
  String get _base => '/api/banquet/bookings/${widget.ref}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _b = b);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    if (r != null && _m(r['draft']).isNotEmpty && mounted) setState(() => _draft = _m(r['draft']));
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Future<void> _ask(String what, List<(String, String)> fields, String title, {Map<String, dynamic> Function(Map<String, String>)? conv}) async {
    final f = await _form(context, title, fields);
    if (f == null) return;
    await _run('POST', '$_base/$what', conv == null ? f : conv(f));
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    if (b == null) return const Scaffold(backgroundColor: C.bgTop, body: Center(child: CircularProgressIndicator()));
    final q = _m(b['quote']);
    final st = _s(b['status']);
    final open = st == 'draft' || st == 'hold';
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${_s(b['number'])} · ${_s(b['client'])}')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(b['hall'])} · ${_s(b['day'])} ${_s(b['slot_label'])} (${_s(b['time'])})',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(b['status_label']), fg: st == 'confirmed' ? C.ok : st == 'hold' ? C.warn : C.chip),
            ]),
            Text('${_s(b['event_label'])} · ${_s(b['phone'])} · log ${_s(b['guests'] ?? '?')} · guarantee ${_s(b['guarantee'] ?? '-')}'
                ' · final ${_s(b['final_count'] ?? '-')}${b['locked'] == true ? ' (lock)' : ''}'),
            Text('Final count ki aakhri tareekh: ${_s(b['lock_date'])}${_s(b['hold_until']).isEmpty ? '' : ' · hold ${_s(b['hold_until']).replaceAll('T', ' ').split('.').first} tak'}',
                style: const TextStyle(fontSize: 12, color: C.muted)),
            Text(_s(b['noise']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ])),
          const SizedBox(height: 10),
          const Caption('QUOTATION (CODE SE, AAPKE DAAM)'),
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final l in _list(q['lines']))
              Text('${_s(l['name'])}: ${_s(l['qty'] ?? '?')} ${_s(l['unit'])} × ${_rs(l['rate'])} = ${_rs(l['amount'])} (GST ${_s(l['gst_pct'])}%)',
                  style: const TextStyle(fontSize: 12.5)),
            if ((q['discount'] ?? 0) != 0) Text('Discount: -${_rs(q['discount'])}'),
            Text('GST ${_rs(q['tax'])} (CGST + SGST) · Kul ${_s(q['total_text'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
            for (final x in _strs(q['blanks'])) Text('⚠ $x', style: const TextStyle(color: C.warn, fontSize: 12)),
            for (final x in _strs(q['notes'])) Text('• $x', style: const TextStyle(fontSize: 12, color: C.muted)),
            Text('Jama ${_s(b['paid_text'])}', style: const TextStyle(color: C.ok)),
          ])),
          const SizedBox(height: 8),
          const Caption('KISHTEIN'),
          for (final r in _list(b['stages']))
            Text('${r['paid'] == true ? '✓' : '•'} ${_s(r['label'])} ${_rs(r['amount'])} · ${_s(r['due'])}${r['requested'] == true ? ' · maanga' : ''}'),
          const SizedBox(height: 8),
          const Caption('REFUND POLICY'),
          for (final x in _strs(b['cancel_lines'])) Text('• $x', style: const TextStyle(fontSize: 12.5)),
          const SizedBox(height: 10),
          if (_draft.isNotEmpty) ...[_draftButtons(_draft), const SizedBox(height: 8)],
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (open) GlassButton(label: 'Hold karo', icon: Icons.hourglass_top_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/hold', {})),
            if (st == 'hold') GlassButton(label: 'Hold chhodo', height: 40, onTap: _busy ? null : () => _run('POST', '$_base/release', {})),
            if (open) GradientButton(label: 'Pakki karne ka card', icon: Icons.verified_rounded, height: 42,
                onTap: _busy ? null : () => _run('POST', '$_base/confirm', {})),
            GlassButton(label: 'Quotation card', icon: Icons.request_quote_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/quote', {})),
            GlassButton(label: 'Shartein card', icon: Icons.article_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/contract', {})),
            GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Booking badlo', const [('hall', 'Hall'), ('day', 'Tareekh'), ('slot', 'Slot'), ('guests', 'Log'),
                ('guarantee', 'Minimum guarantee'), ('package', 'Menu package (ek)'), ('extra', 'Extra (naam)'), ('beo_notes', 'Kitchen / setup notes')]);
              if (f == null) return;
              await _run('PATCH', _base, {
                for (final k in const ['hall', 'day', 'slot', 'beo_notes']) if (f[k] != null) k: f[k],
                for (final k in const ['guests', 'guarantee']) if (f[k] != null) k: _n(f[k])?.toInt(),
                if (f['package'] != null) 'menu': [{'package': f['package']}],
                if (f['extra'] != null) 'extras': [..._list(b['extras']), {'name': f['extra']}],
              });
            }),
            GlassButton(label: 'Discount card', icon: Icons.percent_rounded, height: 40, onTap: _busy ? null : () => _ask('discount',
                const [('amount', 'Kitna (₹)'), ('reason', 'Wajah')], 'Discount (aapki haan + fingerprint)',
                conv: (f) => {'amount': _n(f['amount']), 'reason': f['reason'] ?? ''})),
            if (st == 'confirmed') ...[
              GlassButton(label: 'Paise maango', icon: Icons.currency_rupee_rounded, height: 40, onTap: _busy ? null : () => _ask('pay',
                  const [('stage', 'Kisht ka naam / number'), ('amount', 'Ya rakam')], 'Paise maangne ka card',
                  conv: (f) => {'stage': f['stage'] ?? '', if (f['amount'] != null) 'amount': _n(f['amount'])})),
              GlassButton(label: 'Paise mile', icon: Icons.savings_rounded, height: 40, onTap: _busy ? null : () => _ask('paid',
                  const [('amount', 'Kitne mile'), ('mode', 'upi / cash / bank / cheque'), ('ref', 'UTR / ref (aakhri ank)')], 'Paise mile',
                  conv: (f) => {...f, 'amount': _n(f['amount'])})),
              GlassButton(label: 'Final count', icon: Icons.groups_rounded, height: 40, onTap: _busy ? null : () => _ask('count',
                  const [('final', 'Final mehmaan')], 'Final count', conv: (f) => {'final': _n(f['final'])?.toInt()})),
              GlassButton(label: 'BEO / function sheet', icon: Icons.restaurant_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/beo', {})),
              GlassButton(label: 'Bill card', icon: Icons.receipt_long_rounded, height: 40, onTap: _busy ? null : () => _ask('bill',
                  const [('actual', 'Asal plate ginti')], 'Event ke baad ka bill', conv: (f) => {if (f['actual'] != null) 'actual': _n(f['actual'])?.toInt()})),
              GlassButton(label: 'Poora', icon: Icons.done_all_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/done', {})),
            ],
            GlassButton(label: 'Message card', icon: Icons.chat_rounded, height: 40, onTap: _busy ? null : () => _ask('message',
                const [('text', 'Client ko kya likhna hai')], 'Message (aapki haan ke baad draft)')),
            if (st != 'cancelled' && st != 'done')
              GlassButton(label: 'Radd karo', icon: Icons.cancel_rounded, height: 40, color: C.bad, onTap: _busy ? null : () => _ask('cancel',
                  const [('reason', 'Wajah'), ('by', 'client / venue')], 'Booking radd (refund policy se)')),
            if (_m(_m(b['cancel'])['refund_ok']).isNotEmpty && _m(_m(b['cancel'])['refund_ok'])['sent'] != true)
              GlassButton(label: 'Refund bhej diya', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : () => _ask('refund_sent',
                  const [('ref', 'UTR / ref')], 'Refund bhej diya')),
            if ((st == 'done' || st == 'cancelled') && b['forgotten'] != true)
              GlassButton(label: 'Client details hatao (DPDP)', icon: Icons.delete_sweep_rounded, height: 40,
                  onTap: _busy ? null : () => _run('POST', '$_base/forget', {})),
          ]),
          const SizedBox(height: 12),
          if (_list(b['cards']).isNotEmpty) const Caption('CARDS'),
          for (final c in _list(b['cards']))
            Padding(padding: const EdgeInsets.only(bottom: 10), child: BanquetCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
          if (_list(b['payments']).isNotEmpty) ...[
            const Caption('PAISE'),
            for (final p in _list(b['payments']))
              Text('${_s(p['day'])} · ${_s(p['receipt'])} · ${_s(p['mode'])} · ${_rs(p['amount'])}${p['kind'] == 'refund' ? ' (refund)' : ''}'),
          ],
        ]),
      ),
    );
  }
}

/// banquet_card: everything that waits for HER tap (quote, terms, hold -> confirmed, discount*, refund*, payment request, bill,
/// message). *money cards: fingerprint once a phone key is set up (428 -> /challenge -> Native.approveKeySign -> resend).
class BanquetCardCard extends StatefulWidget {
  const BanquetCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<BanquetCardCard> createState() => _BanquetCardCardState();
}

class _BanquetCardCardState extends State<BanquetCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/banquet/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Banquet' : _s(show['title']),
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
      final f = await _form(context, 'Kyun nahi?', const [('reason', 'Wajah (optional)')], ok: 'Nahi');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/banquet/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/banquet/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          if (_m(m['card']).isNotEmpty) _c = _m(m['card']);
          _draft = _m(m['draft']);
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

  @override
  Widget build(BuildContext context) {
    final c = _c, sh = _m(c['show']);
    final st = _s(c['status']), kind = _s(c['kind']);
    final money = c['money'] == true;
    final amount = _s(sh['amount_text']).isNotEmpty ? _s(sh['amount_text']) : _s(sh['total_text']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'quote' => Icons.request_quote_rounded, 'contract' => Icons.article_rounded, 'confirm' => Icons.verified_rounded,
            'discount' => Icons.percent_rounded, 'refund' => Icons.undo_rounded, 'pay' => Icons.currency_rupee_rounded,
            'bill' => Icons.receipt_long_rounded, _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['booking'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(sh['client'])} · ${_s(sh['hall'])} · ${_s(sh['day'])} ${_s(sh['slot'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (_s(sh['label']).isNotEmpty) Text(_s(sh['label'])),
        if (_s(sh['reason']).isNotEmpty) Text('Wajah: ${_s(sh['reason'])}', style: const TextStyle(fontSize: 12)),
        if (_s(sh['why']).isNotEmpty) Text(_s(sh['why']), style: const TextStyle(fontSize: 12)),
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'bill') Text('Jama ${_rs(sh['paid'])} · baaki ${_s(sh['balance_text'])}', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'quote' || kind == 'contract')
          for (final x in _strs(sh['cancel_lines'])) Text('• $x', style: const TextStyle(fontSize: 11.5, color: C.muted)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Haan (fingerprint)' : 'Haan', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola khud kuch nahi bhejta, paise nahi leta / deta: message aap bhejti hain.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// banquet_alert / banquet_day: notes (hold ending, count lock, instalment due, function tomorrow, morning note).
class BanquetNoteCard extends StatelessWidget {
  const BanquetNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final booking = _s(data['booking']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.celebration_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
          if (booking.isNotEmpty)
            TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BanquetBookingPage(app: app, ref: booking))),
              child: Text('$booking kholo'),
            ),
        ])),
      ]),
    );
  }
}
