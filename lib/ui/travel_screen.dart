/// Profile > Yatra Sahayak: Hoola as the travel agent / trip planner.
/// Aaj (trips in the next 7 days, cards waiting for her haan) · Trips (T-0001: travellers, day-by-day plan, options pasted by
/// her + comparison, rail booking windows, documents, packing, bookings, client quotes) · Niyam (own / agency, markup, partner key).
/// A booking starts ONLY after her tap on the card; Hoola's browser then stops at payment and she pays herself.
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

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Set<String> secret = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(
              controller: c[k],
              obscureText: secret.contains(k),
              decoration: InputDecoration(labelText: label),
              maxLines: (k == 'text' && !secret.contains(k)) ? 5 : 1,
            ),
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

Widget _line(String label, String value) => value.isEmpty
    ? const SizedBox.shrink()
    : Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Text('$label: $value', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      );

IconData _modeIcon(String m) => switch (m) {
      'train' => Icons.train_rounded,
      'flight' => Icons.flight_rounded,
      'bus' => Icons.directions_bus_rounded,
      'hotel' => Icons.hotel_rounded,
      'cab' => Icons.local_taxi_rounded,
      _ => Icons.place_rounded,
    };

class TravelScreen extends StatefulWidget {
  const TravelScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<TravelScreen> createState() => _TravelScreenState();
}

class _TravelScreenState extends State<TravelScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/travel'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  void _open(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => TravelTripPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Future<void> _newTrip() async {
    final f = await _form(context, 'Nayi yatra', const [
      ('destination', 'Kahan jaana hai'),
      ('origin', 'Kahan se'),
      ('start_date', 'Jaane ki date (DD-MM-YYYY)'),
      ('end_date', 'Wapsi ki date (DD-MM-YYYY)'),
      ('budget', 'Budget (₹, ho to)'),
      ('prefs', 'Pasand / zaroorat (veg, beach, lower berth...)'),
      ('client_name', 'Graahak ka naam (agency ho to)'),
      ('client_phone', 'Graahak ka mobile'),
    ], ok: 'Banao');
    if (f == null || (f['destination'] ?? '').isEmpty) return;
    final r = await _call(context, widget.app, 'POST', '/api/travel/trips', f);
    final t = _m(r?['trip']);
    if (t['number'] != null && mounted) _open(_s(t['number']));
  }

  Widget _tripTile(Map<String, dynamic> t) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => _open(_s(t['number'])),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(
                    child: Text('${_s(t['number'])} · ${_s(t['title'])}',
                        style: const TextStyle(fontWeight: FontWeight.w800), maxLines: 2, overflow: TextOverflow.ellipsis)),
                Pill(_s(t['status_label'])),
              ]),
              _line('Dates', [_s(t['start_date']), _s(t['end_date'])].where((x) => x.isNotEmpty).join(' se ')),
              if (_list(t['travellers']).isNotEmpty) _line('Yatri', _list(t['travellers']).map((x) => _s(x['name'])).join(', ')),
              if (t['for_client'] == true) _line('Graahak', _s(t['client_name'])),
            ]),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      appBar: AppBar(title: const Text('Yatra Sahayak'), actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))]),
      floatingActionButton: FloatingActionButton.extended(
          onPressed: _newTrip, icon: const Icon(Icons.add_location_alt_rounded), label: const Text('Nayi yatra')),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
                child: SegmentedButton<int>(
                  segments: const [
                    ButtonSegment(value: 0, label: Text('Aaj')),
                    ButtonSegment(value: 1, label: Text('Trips')),
                    ButtonSegment(value: 2, label: Text('Niyam')),
                  ],
                  selected: {_tab},
                  onSelectionChanged: (v) => setState(() => _tab = v.first),
                ),
              ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.fromLTRB(12, 8, 12, 90), children: switch (_tab) {
                    0 => _today(d),
                    1 => [for (final t in _list(d['trips'])) _tripTile(t)],
                    _ => [TravelSettingsPanel(app: widget.app, data: _m(d['settings']), onSaved: _load)],
                  }),
                ),
              ),
            ]),
    );
  }

  List<Widget> _today(Map<String, dynamic> d) {
    final day = _m(d['day']);
    return [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Caption('AGLE 7 DIN'),
          Text(_s(day['say']).isEmpty ? 'Agle 7 din mein koi yatra nahi.' : _s(day['say'])),
        ]),
      ),
      const SizedBox(height: 10),
      if (_list(d['waiting']).isNotEmpty) const Caption('AAPKI HAAN BAAKI'),
      for (final b in _list(d['waiting'])) TravelBookingCard(app: widget.app, data: b),
      for (final q in _list(d['quotes'])) TravelQuoteCard(app: widget.app, data: q),
      const SizedBox(height: 8),
      const Text('Railway / airline ke niyam badalte rehte hain: IRCTC / airline / embassy ki site par pakka karein. '
          'Hoola kabhi pay nahi karta; booking aapki haan ke baad payment par rukti hai.',
          style: TextStyle(fontSize: 12, color: C.faint)),
    ];
  }
}

class TravelSettingsPanel extends StatelessWidget {
  const TravelSettingsPanel({super.key, required this.app, required this.data, required this.onSaved});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback onSaved;

  Future<void> _edit(BuildContext context) async {
    final f = await _form(context, 'Yatra ke niyam', const [
      ('mode', 'own (apne trip) ya agency (graahak)'),
      ('agency_name', 'Agency ka naam'),
      ('contact', 'Quote par aapka phone / email'),
      ('home_city', 'Aapka shahar'),
      ('state', 'Rajya (chhutti ki list ke liye)'),
      ('markup_pct', 'Aapka service charge %'),
      ('markup_flat', 'Aapka fixed charge (₹)'),
      ('gst_pct', 'GST % service charge par (0 / 5 / 18)'),
      ('terms', 'Quote ki shartein'),
      ('morning_time', 'Subah ka note (HH:MM)'),
    ], ok: 'Save');
    if (f == null || f.isEmpty) return;
    final body = <String, dynamic>{...f};
    for (final k in ['markup_pct', 'gst_pct']) {
      if (body[k] != null) body[k] = double.tryParse(_s(body[k])) ?? 0;
    }
    if (!context.mounted) return;
    await _call(context, app, 'PUT', '/api/travel/settings', body);
    onSaved();
  }

  Future<void> _partner(BuildContext context) async {
    final f = await _form(context, 'Amadeus partner key (sirf daam dekhne ke liye)', const [
      ('key', 'API key'),
      ('secret', 'API secret'),
      ('env', 'test ya prod'),
    ], ok: 'Jodo', secret: const {'key', 'secret'});
    if (f == null || !context.mounted) return;
    await _call(context, app, 'PUT', '/api/travel/partner', {'provider': 'amadeus', ...f});
    onSaved();
  }

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Caption('NIYAM'),
          _line('Kaam', _s(data['mode']) == 'agency' ? 'Travel agency (graahakon ke trip)' : 'Apne / ghar ke trip'),
          _line('Agency', _s(data['agency_name'])),
          _line('Service charge', '${_s(data['markup_pct'])}% ${_s(data['markup_flat'])}'),
          _line('GST', _s(data['gst_pct'])),
          _line('Shahar', _s(data['home_city'])),
          _line('Partner', _list(data['partners']).map((p) => '${_s(p['provider'])} (${_s(p['env'])})').join(', ')),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: () => _edit(context)),
            GlassButton(label: 'Partner key', icon: Icons.key_rounded, onTap: () => _partner(context)),
          ]),
          const SizedBox(height: 6),
          const Text('Key sirf yahin daaliye (chat mein kabhi nahi). Hoola sirf daam padhta hai, booking ya payment nahi.',
              style: TextStyle(fontSize: 12, color: C.faint)),
        ]),
      );
}

class TravelTripPage extends StatefulWidget {
  const TravelTripPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<TravelTripPage> createState() => _TravelTripPageState();
}

class _TravelTripPageState extends State<TravelTripPage> {
  Map<String, dynamic>? _t;
  Map<String, dynamic>? _cmp;
  bool _busy = false;

  String get _base => '/api/travel/trips/${widget.ref}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _t = t);
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

  Future<void> _addTraveller() async {
    final f = await _form(context, 'Yatri jodo', const [
      ('name', 'Naam (ID par jaisa)'),
      ('age', 'Umar'),
      ('gender', 'M / F'),
      ('berth', 'Berth pasand (lower / upper / side)'),
      ('id_kind', 'ID ka prakar (aadhaar / passport / voter / dl)'),
      ('id_number', 'ID number (locker mein jayega)'),
      ('passport_expiry', 'Passport expiry (DD-MM-YYYY, videsh ho to)'),
    ], ok: 'Jodo', secret: const {'id_number'});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (body['age'] != null) body['age'] = int.tryParse(_s(body['age']));
    await _run('POST', '$_base/travellers', body);
  }

  Future<void> _paste() async {
    final f = await _form(context, 'Daam paste kijiye', const [
      ('text', 'Har option ek line mein (naam, samay, ₹ daam, rating)'),
      ('leg', 'out (jaana) / back (wapsi) / stay (hotel)'),
    ], ok: 'Jodo');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '$_base/options', f);
  }

  Future<void> _compare() async {
    final r = await _call(context, widget.app, 'GET', '$_base/compare');
    if (r != null && mounted) setState(() => _cmp = _m(r['compare']));
  }

  Widget _section(String title, List<Widget> children) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Caption(title), ...children])),
      );

  Widget _option(Map<String, dynamic> o) => Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(_modeIcon(_s(o['mode'])), size: 20, color: o['chosen'] == true ? C.accent : C.muted),
          const SizedBox(width: 8),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(o['name'])} ${_s(o['code'])}'.trim(), style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(
                  [
                    _s(o['day']),
                    if (_s(o['depart']).isNotEmpty) '${_s(o['depart'])}-${_s(o['arrive'])}',
                    _s(o['duration']),
                    _s(o['cls_label']),
                    _s(o['quota_label']),
                    o['rating'] == null ? '' : '★ ${_s(o['rating'])}',
                    '${_s(o['price'])}${o['per_night'] == true ? ' / raat' : ''}',
                  ].where((x) => x.isNotEmpty).join(' · '),
                  style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
          PopupMenuButton<String>(
            onSelected: (v) async {
              final id = _s(o['id']);
              if (v == 'choose') await _run('POST', '$_base/options/$id/choose', {'on': o['chosen'] != true});
              if (v == 'book') await _run('POST', '$_base/book', {'option': id});
              if (v == 'delete') await _run('DELETE', '$_base/options/$id');
            },
            itemBuilder: (_) => [
              PopupMenuItem(value: 'choose', child: Text(o['chosen'] == true ? 'Chunav hatao' : 'Yeh chuno')),
              const PopupMenuItem(value: 'book', child: Text('Booking card bhejo')),
              const PopupMenuItem(value: 'delete', child: Text('Hatao')),
            ],
          ),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final t = _t;
    return Scaffold(
      appBar: AppBar(title: Text(widget.ref), actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))]),
      body: t == null
          ? const Center(child: CircularProgressIndicator())
          : AbsorbPointer(
              absorbing: _busy,
              child: ListView(padding: const EdgeInsets.fromLTRB(12, 8, 12, 40), children: [
                _section('YATRA', [
                  Text(_s(t['title']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                  _line('Dates', '${_s(t['start_date'])} se ${_s(t['end_date'])} (${_s(t['days'])} din)'),
                  _line('Budget', _s(t['budget'])),
                  _line('Pasand', _s(t['prefs'])),
                  _line('Status', _s(t['status_label'])),
                  if (_m(t['visa']).isNotEmpty) _line('Visa', _s(_m(t['visa'])['say'])),
                  for (final h in _list(t['holidays'])) _line('Chhutti', _s(h['say'])),
                ]),
                _section('YATRI', [
                  for (final x in _list(t['travellers']))
                    Text('${_s(x['name'])}${x['age'] == null ? '' : ' (${_s(x['age'])})'}'
                        '${_s(x['id_masked']).isEmpty ? '' : ' · ID ${_s(x['id_masked'])}'}'),
                  for (final p in _list(t['passport'])) _line('Passport ${_s(p['name'])}', _s(p['say'])),
                  const SizedBox(height: 6),
                  GlassButton(label: 'Yatri jodo', icon: Icons.person_add_alt_rounded, onTap: _addTraveller),
                ]),
                _section('PLAN (DIN-BA-DIN)', [
                  for (final d in _list(_m(t['itinerary'])['days'])) ...[
                    Text('Din ${_s(d['day'])} ${_s(d['date'])}: ${_s(d['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    for (final it in _list(d['items']))
                      Row(children: [
                        Expanded(
                            child: Text('• ${_s(it['time']).isEmpty ? '' : '${_s(it['time'])} '}${_s(it['place'])}: ${_s(it['what'])}',
                                style: const TextStyle(fontSize: 12.5))),
                        if (_s(it['map']).isNotEmpty)
                          IconButton(
                              iconSize: 18,
                              onPressed: () => Native.openExternal(url: _s(it['map'])),
                              icon: const Icon(Icons.map_rounded)),
                      ]),
                  ],
                  const SizedBox(height: 6),
                  GlassButton(label: 'Plan banao', icon: Icons.auto_awesome_rounded, onTap: () => _run('POST', '$_base/itinerary', {})),
                ]),
                _section('OPTIONS AUR TULNA', [
                  for (final o in _list(t['options'])) _option(o),
                  if (_cmp != null)
                    for (final e in _cmp!.entries)
                      for (final r in _list(_m(e.value)['rows']))
                        if (((r['tags'] as List?) ?? const []).isNotEmpty)
                          _line('${e.key} ${_s(r['name'])}', ((r['tags'] as List?) ?? const []).join(', ')),
                  const SizedBox(height: 6),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    GlassButton(label: 'Daam paste karo', icon: Icons.content_paste_rounded, onTap: _paste),
                    GlassButton(label: 'Tulna', icon: Icons.compare_arrows_rounded, onTap: _compare),
                    GlassButton(
                        label: 'IRCTC kholo',
                        icon: Icons.open_in_new_rounded,
                        onTap: () => Native.openExternal(url: 'https://www.irctc.co.in/nget/train-search')),
                  ]),
                ]),
                if (_list(t['windows']).isNotEmpty)
                  _section('TRAIN BOOKING KA SAMAY', [
                    for (final w in _list(t['windows'])) ...[
                      Text(_s(w['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                      _line('Booking khulegi', _s(w['arp_open']).replaceAll('T', ' ')),
                      if (w['tatkal'] is Map) _line('Tatkal', _s(_m(w['tatkal'])['say'])),
                      _line('Chart', _s(w['chart']).replaceAll('T', ' ')),
                    ],
                  ]),
                _section('KAAGAZ', [
                  for (final d in _list(t['docs']))
                    CheckboxListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      value: d['have'] == true,
                      title: Text(_s(d['title']), style: TextStyle(fontWeight: d['must'] == true ? FontWeight.w700 : FontWeight.w400)),
                      subtitle: _s(d['why']).isEmpty ? null : Text(_s(d['why']), style: const TextStyle(fontSize: 11.5)),
                      onChanged: (v) => _run('POST', '$_base/docs', {'item': _s(d['id']), 'have': v == true}),
                    ),
                ]),
                _section('PACKING', [
                  for (final p in _list(t['packing']))
                    CheckboxListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      value: p['done'] == true,
                      title: Text(_s(p['item'])),
                      onChanged: (v) => _run('POST', '$_base/packing', {'item': _s(p['item']), 'done': v == true}),
                    ),
                ]),
                _section('BOOKING', [
                  for (final b in _list(t['bookings'])) TravelBookingCard(app: widget.app, data: b),
                  if (t['for_client'] == true) ...[
                    for (final q in _list(t['quotes'])) TravelQuoteCard(app: widget.app, data: q),
                    GlassButton(label: 'Graahak ka quote', icon: Icons.request_quote_rounded, onTap: () => _run('POST', '$_base/quote')),
                  ],
                ]),
                Text(_s(t['disclaimer']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
              ]),
            ),
    );
  }
}

/// travel_booking: booking card. Only "Haan, book karo" here (her tap) starts it; Hoola stops at payment, she pays.
class TravelBookingCard extends StatefulWidget {
  const TravelBookingCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<TravelBookingCard> createState() => _TravelBookingCardState();
}

class _TravelBookingCardState extends State<TravelBookingCard> {
  Map<String, dynamic>? _over;
  bool _busy = false;

  Map<String, dynamic> get _b => _over ?? widget.data;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/travel/bookings/${_s(_b['id'])}/decide',
        {'yes': yes, 'hash': _s(_b['hash'])});
    if (mounted) setState(() {
      _busy = false;
      if (r != null && r['booking'] is Map) _over = _m(r['booking']);
    });
  }

  Future<void> _done() async {
    final f = await _form(context, 'Book ho gaya?', const [('pnr', 'PNR / booking number'), ('paid', 'Kitna pay kiya (₹)')], ok: 'Save');
    if (f == null || !mounted) return;
    final r = await _call(context, widget.app, 'POST', '/api/travel/bookings/${_s(_b['id'])}/done', f);
    if (mounted && r != null && r['booking'] is Map) setState(() => _over = _m(r['booking']));
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    final c = _m(b['card']);
    final st = _s(b['status']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        border: st == 'waiting' ? C.accent : null,
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(_modeIcon(_s(c['mode'])), size: 20),
            const SizedBox(width: 6),
            Expanded(child: Text('${_s(b['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(b['status_label'])),
          ]),
          _line('Trip', '${_s(c['trip'])}${_s(c['client']).isEmpty ? '' : ' · ${_s(c['client'])}'}'),
          _line('Kahan', [_s(c['from']), _s(c['to'])].where((x) => x.isNotEmpty).join(' -> ')),
          _line('Kab', [_s(c['day']), _s(c['depart'])].where((x) => x.isNotEmpty).join(' ')),
          _line('Class / quota', [_s(c['cls_label']), _s(c['quota_label'])].where((x) => x.isNotEmpty).join(' · ')),
          _line('Yatri', _list(c['travellers']).map((x) => '${_s(x['name'])}${x['age'] == null ? '' : ' (${_s(x['age'])})'}').join(', ')),
          _line('Daam', _s(c['price'])),
          _line('Kaise', _s(c['route'])),
          for (final n in (c['notes'] as List?) ?? const []) _line('Dhyaan', _s(n)),
          if (_s(b['pnr']).isNotEmpty) _line('PNR', _s(b['pnr'])),
          const SizedBox(height: 8),
          if (st == 'waiting')
            Row(children: [
              Expanded(
                  child: GradientButton(
                      label: 'Haan, book karo', icon: Icons.check_rounded, height: 46, onTap: _busy ? null : () => _decide(true))),
              const SizedBox(width: 8),
              TextButton(onPressed: _busy ? null : () => _decide(false), child: const Text('Mana')),
            ]),
          if (st == 'self' && _s(c['link']).isNotEmpty)
            GlassButton(label: 'Site kholo', icon: Icons.open_in_new_rounded, onTap: () => Native.openExternal(url: _s(c['link']))),
          if (['working', 'waiting_payment', 'self', 'approved'].contains(st))
            TextButton(onPressed: _done, child: const Text('Book ho gaya (PNR daalo)')),
        ]),
      ),
    );
  }
}

/// travel_quote: client quote with her service charge. "Haan, PDF banao" (her tap) makes the PDF + message draft she sends.
class TravelQuoteCard extends StatefulWidget {
  const TravelQuoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<TravelQuoteCard> createState() => _TravelQuoteCardState();
}

class _TravelQuoteCardState extends State<TravelQuoteCard> {
  Map<String, dynamic>? _res;
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/travel/quotes/${_s(widget.data['id'])}/decide',
        {'yes': yes, 'hash': _s(widget.data['hash'])});
    if (mounted) setState(() {
      _busy = false;
      _res = r;
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = _m(widget.data['card']);
    final st = _s(_m(_res?['quote'])['status']).isNotEmpty ? _s(_m(_res?['quote'])['status']) : _s(widget.data['status']);
    final drafts = _m(_res?['drafts']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        border: st == 'waiting' ? C.accent : null,
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(c['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(st),
          ]),
          for (final l in _list(c['lines'])) _line(_s(l['what']), _s(l['amount'])),
          _line('Kharcha', _s(c['cost'])),
          _line('Aapka charge', _s(c['service_charge'])),
          _line('GST', _s(c['gst'])),
          Text('Kul: ${_s(c['total'])}${_s(c['per_person']).isEmpty ? '' : ' (${_s(c['per_person'])} prati vyakti)'}',
              style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          if (st == 'waiting')
            Row(children: [
              Expanded(
                  child: GradientButton(
                      label: 'Haan, PDF banao', icon: Icons.picture_as_pdf_rounded, height: 46, onTap: _busy ? null : () => _decide(true))),
              const SizedBox(width: 8),
              TextButton(onPressed: _busy ? null : () => _decide(false), child: const Text('Mana')),
            ]),
          if (_s(drafts['whatsapp']).isNotEmpty)
            GlassButton(label: 'WhatsApp draft kholo', icon: Icons.chat_rounded, onTap: () => Native.openExternal(url: _s(drafts['whatsapp']))),
          if (_s(drafts['email']).isNotEmpty)
            TextButton(onPressed: () => Native.openExternal(url: _s(drafts['email'])), child: const Text('Email draft')),
        ]),
      ),
    );
  }
}

/// travel_trip (new trip / plan ready), travel_reminder (booking opens, Tatkal, chart, web check-in, passport, eve), travel_day.
class TravelNoteCard extends StatelessWidget {
  const TravelNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final trip = data['trip'] is Map ? _m(data['trip']) : <String, dynamic>{};
    final ref = trip.isNotEmpty ? _s(trip['number']) : _s(data['trip']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () {
          if (ref.isEmpty) {
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => TravelScreen(app: app)));
          } else {
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => TravelTripPage(app: app, ref: ref)));
          }
        },
        child: Glass(
          padding: const EdgeInsets.all(12),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Icon(Icons.luggage_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(ref.isEmpty ? 'Yatra' : '$ref ${_s(trip['title'])}'.trim(), style: const TextStyle(fontWeight: FontWeight.w800)),
                Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
