/// Profile > Tour Guide Sahayak: Hoola as a local guide's / small tour operator's coworker.
/// Aaj (today / tomorrow tours, enquiries, cards waiting) · Booking (enquiry paste, group files) · Tour (her products with HER
/// price, group size, places with timings only as she gave them) · Licence + Hisaab (renewals, tips / commission) · Niyam.
/// A booking confirmation, every message to guests, refunds, discounts and spends run only after HER tap (fingerprint for
/// refund / spend once a phone key is set up). Hoola never takes or pays money and never invents timings or prices.
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
                maxLines: (k == 'text' || k == 'cancel_policy' || k == 'rules' || k == 'places' || k == 'reason') ? 3 : 1),
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

/// "Shaniwar Wada | 60 | 8:00 | 18:30 | 25 | 300" per line -> places (timings / tickets only what she typed).
List<Map<String, dynamic>> _parsePlaces(String text) {
  final out = <Map<String, dynamic>>[];
  for (final raw in text.split('\n')) {
    final p = raw.split('|').map((e) => e.trim()).toList();
    if (p.isEmpty || p[0].isEmpty) continue;
    final m = <String, dynamic>{'name': p[0]};
    if (p.length > 1 && _n(p[1]) != null) m['stop_min'] = _n(p[1]);
    if (p.length > 2 && p[2].isNotEmpty) m['open'] = p[2];
    if (p.length > 3 && p[3].isNotEmpty) m['close'] = p[3];
    if (p.length > 4 && _n(p[4]) != null) m['ticket_in'] = _n(p[4]);
    if (p.length > 5 && _n(p[5]) != null) m['ticket_foreign'] = _n(p[5]);
    if (p.length > 6 && p[6].isNotEmpty) m['closed_on'] = p[6];
    m['source'] = 'aapne bataya';
    out.add(m);
  }
  return out;
}

class TourguideScreen extends StatefulWidget {
  const TourguideScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<TourguideScreen> createState() => _TourguideScreenState();
}

class _TourguideScreenState extends State<TourguideScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/tourguide'));
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
      .push(MaterialPageRoute(builder: (_) => TourguideBookingPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _enquiry() async {
    final f = await _form(context, 'Enquiry paste karo', const [
      ('text', 'WhatsApp / call ki baat (jaisi aayi)'),
      ('tour', 'Tour (TP-01, ho to)'),
      ('lead_name', 'Mehmaan ka naam'),
    ], ok: 'Darj karo');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/tourguide/bookings/enquiry', f);
    final b = _m(r?['booking']);
    if (b['id'] != null && mounted) _open(_s(b['id']));
  }

  Future<void> _newBooking() async {
    final f = await _form(context, 'Nayi booking', const [
      ('tour', 'Tour (TP-01)'),
      ('day', 'Date (DD-MM-YYYY)'),
      ('start_time', 'Samay (07:30)'),
      ('lead_name', 'Mehmaan ka naam'),
      ('phone', 'Mobile'),
      ('guests', 'Kitne log'),
      ('language', 'Bhasha (hindi / english / marathi ...)'),
      ('pickup', 'Pickup'),
      ('special_needs', 'Khaas zaroorat (wheelchair, bachche...)'),
    ], ok: 'Banao');
    if (f == null || (f['tour'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    if (f['guests'] != null) body['guests'] = _n(f['guests']);
    final r = await _run('POST', '/api/tourguide/bookings', body);
    final b = _m(r?['booking']);
    if (b['id'] != null && mounted) _open(_s(b['id']));
  }

  Future<void> _tourForm([Map<String, dynamic>? t]) async {
    final places = _list(t?['places'])
        .map((p) => [p['name'], p['stop_min'] ?? '', p['open'] ?? '', p['close'] ?? '', p['ticket_in'] ?? '', p['ticket_foreign'] ?? '',
              _strs(p['closed_on']).join(' ')].map(_s).join(' | '))
        .join('\n');
    final f = await _form(context, t == null ? 'Naya tour' : 'Tour badlo', const [
      ('title', 'Naam'),
      ('kind', 'city_walk / heritage / temple / trek / food / nature / boat / day_trip'),
      ('city', 'Shehar'),
      ('duration_min', 'Kitne minute'),
      ('price_pp', 'Daam per vyakti (aapka)'),
      ('price_group', 'Ya poore group ka daam'),
      ('group_max', 'Max log'),
      ('meeting_point', 'Kahan milna'),
      ('includes', 'Shaamil'),
      ('excludes', 'Shaamil nahi'),
      ('places', 'Jagahein: naam | minute | khule | band | ticket Bharat | ticket videshi | band din (har line ek)'),
    ], ok: 'Save', initial: {
      if (t != null)
        for (final k in ['title', 'kind', 'city', 'duration_min', 'price_pp', 'price_group', 'group_max', 'meeting_point', 'includes', 'excludes'])
          if (t[k] != null) k: _s(t[k]),
      if (t != null) 'places': places,
    });
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['duration_min', 'price_pp', 'price_group', 'group_max']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    if (f['places'] != null) body['places'] = _parsePlaces(f['places']!);
    if (t == null) {
      await _run('POST', '/api/tourguide/tours', body);
    } else {
      await _run('PATCH', '/api/tourguide/tours/${_s(t['id'])}', body);
    }
  }

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Niyam', const [
      ('business', 'Business ka naam'),
      ('guide_name', 'Aapka naam (intro mein)'),
      ('phone', 'Aapka mobile'),
      ('city', 'Shehar'),
      ('upi_id', 'UPI ID (khaali = Employee wala)'),
      ('cancel_policy', 'Cancellation / refund policy (har confirmation mein jayegi)'),
      ('review_link', 'Review link (Google / TripAdvisor)'),
      ('gst_mode', 'GST: none / guide / tour5 / tour18'),
      ('parallel_tours', 'Ek saath kitne tour (team)'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('rules', 'Aapke niyam'),
    ], initial: {
      for (final k in ['business', 'guide_name', 'phone', 'city', 'upi_id', 'cancel_policy', 'review_link', 'gst_mode', 'parallel_tours', 'morning_time', 'rules'])
        k: _s(st[k]),
    }, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['parallel_tours'] != null) body['parallel_tours'] = _n(f['parallel_tours']);
    await _run('PUT', '/api/tourguide/settings', body);
  }

  Future<void> _licence() async {
    final f = await _form(context, 'Licence', const [
      ('kind', 'iitf / iitg_heritage / iitg_adventure / state / asi_site / first_aid / adventure / other'),
      ('ref', 'Number'),
      ('holder', 'Kiska'),
      ('authority', 'Kisne diya'),
      ('valid_to', 'Kab tak (DD-MM-YYYY)'),
    ], ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/tourguide/licences', f);
  }

  Future<void> _ledgerAdd() async {
    final f = await _form(context, 'Hisaab', const [
      ('kind', 'tip / commission_in / commission_out'),
      ('amount', 'Kitna'),
      ('party', 'Kisse / kisko'),
      ('booking', 'Booking (B-0001, ho to)'),
      ('note', 'Note'),
    ], ok: 'Darj');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['amount'] != null) body['amount'] = _n(f['amount']);
    await _run('POST', '/api/tourguide/ledger', body);
  }

  Future<void> _spend() async {
    final f = await _form(context, 'Kharcha (aapki haan se)', const [
      ('what', 'Kis cheez ka'),
      ('amount', 'Kitna (bill / quote)'),
      ('party', 'Kisko'),
      ('booking', 'Booking (ho to)'),
    ], ok: 'Card banao');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['amount'] != null) body['amount'] = _n(f['amount']);
    await _run('POST', '/api/tourguide/spends', body);
  }

  Widget _bookingTile(Map<String, dynamic> b) => Press(
        onTap: () => _open(_s(b['id'])),
        child: Glass(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(b['number'])} · ${_s(b['lead_name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(b['status_label']), fg: _s(b['status']) == 'confirmed' ? C.ok : (_s(b['status']) == 'enquiry' ? C.warn : C.chip)),
            ]),
            Text('${_s(b['tour'])} · ${_s(b['day'])} ${_s(b['start_time'])} · ${_s(b['guests'])} log · ${_s(b['total_text'])}',
                style: const TextStyle(fontSize: 12.5, color: C.muted)),
          ]),
        ),
      );

  Widget _today() {
    final d = _m(_d?['day']);
    final cards = _list(_d?['cards']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
      const SizedBox(height: 10),
      if (cards.isNotEmpty) const Caption('AAPKI HAAN CHAHIYE'),
      for (final c in cards)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: TourguideCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      if (_list(d['today']).isNotEmpty) const Caption('AAJ'),
      for (final b in _list(d['today'])) _bookingTile(b),
      if (_list(d['tomorrow']).isNotEmpty) const Caption('KAL'),
      for (final b in _list(d['tomorrow'])) _bookingTile(b),
    ]);
  }

  Widget _bookingsTab() => ListView(padding: const EdgeInsets.all(14), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'Enquiry paste', icon: Icons.content_paste_rounded, height: 44, onTap: _busy ? null : _enquiry)),
          const SizedBox(width: 8),
          GlassButton(label: 'Nayi', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _newBooking),
        ]),
        const SizedBox(height: 10),
        for (final b in _list(_d?['bookings'])) _bookingTile(b),
      ]);

  Widget _toursTab() => ListView(padding: const EdgeInsets.all(14), children: [
        GradientButton(label: 'Naya tour', icon: Icons.tour_rounded, height: 46, onTap: _busy ? null : () => _tourForm()),
        const SizedBox(height: 10),
        for (final t in _list(_d?['tours']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.map_rounded, color: C.accent),
                const SizedBox(width: 8),
                Expanded(child: Text('${_s(t['number'])} · ${_s(t['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                IconButton(onPressed: _busy ? null : () => _tourForm(t), icon: const Icon(Icons.edit_rounded, size: 18)),
              ]),
              Text('${_s(t['kind_label'])} · ${_s(t['city'])} · ${_s(t['duration_min'])} min · ${_s(t['price_text'])} · max ${_s(t['group_max'])}',
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
              for (final p in _list(t['places']))
                Text('• ${_s(p['name'])}  ${_s(p['open']).isEmpty ? 'samay pata nahi' : '${_s(p['open'])}-${_s(p['close'])}'}',
                    style: const TextStyle(fontSize: 12, color: C.faint)),
              if (_strs(t['missing']).isNotEmpty)
                Text('Baaki: ${_strs(t['missing']).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
              const SizedBox(height: 6),
              Wrap(spacing: 8, children: [
                GlassButton(
                    label: 'AI sujhav (jagahein)',
                    height: 36,
                    onTap: _busy ? null : () => _run('POST', '/api/tourguide/tours/${_s(t['id'])}/suggest', {})),
                GlassButton(
                    label: 'Intro script',
                    height: 36,
                    onTap: _busy ? null : () => _run('POST', '/api/tourguide/tours/${_s(t['id'])}/script', {'language': 'hinglish'})),
              ]),
            ]),
          ),
      ]);

  Widget _moneyTab() {
    final led = _m(_d?['ledger']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      const Caption('LICENCE'),
      for (final l in _list(_d?['licences']))
        Glass(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          border: _s(l['state']) == 'khatam' ? C.bad : (_s(l['state']) == 'jald' ? C.warn : null),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(l['kind_label'])} · ${_s(l['ref'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            _line('Kab tak', '${_s(l['valid_to'])} (${_s(l['days_left'])} din)'),
            if (_s(l['note']).isNotEmpty) Text(_s(l['note']), style: const TextStyle(fontSize: 12, color: C.muted)),
          ]),
        ),
      Row(children: [
        GlassButton(label: 'Licence jodo', icon: Icons.badge_rounded, height: 40, onTap: _busy ? null : _licence),
        const SizedBox(width: 8),
        GlassButton(label: 'iitf.gov.in', icon: Icons.open_in_new_rounded, height: 40, onTap: () => Native.openExternal(url: 'https://iitf.gov.in')),
      ]),
      const SizedBox(height: 14),
      const Caption('HISAAB (IS MAHINE)'),
      Glass(child: Text(_s(led['say']), style: const TextStyle(fontSize: 13))),
      const SizedBox(height: 8),
      Row(children: [
        GlassButton(label: 'Tip / commission', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : _ledgerAdd),
        const SizedBox(width: 8),
        GlassButton(label: 'Kharcha card', icon: Icons.payments_rounded, height: 40, onTap: _busy ? null : _spend),
      ]),
      for (final x in _list(led['entries']))
        Text('${_s(x['on'])} · ${_s(x['kind'])} · ${_s(x['amount_text'])} · ${_s(x['party'])}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _line('Business', _s(st['business'])),
          _line('Guide', _s(st['guide_name'])),
          _line('UPI', _s(st['upi_used'])),
          _line('Cancellation', _s(st['cancel_policy']).isEmpty ? 'abhi nahi likhi (confirmation nahi banegi)' : _s(st['cancel_policy'])),
          _line('GST', _s(st['gst_note'])),
          _line('Ek saath tour', _s(st['parallel_tours'])),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.tune_rounded, onTap: _busy ? null : _settings),
        ]),
      ),
      const SizedBox(height: 10),
      const Caption('HOOLA KABHI NAHI'),
      for (final n in _strs(_d?['never'])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 10),
      const Caption('SROT (SOURCES)'),
      for (final x in _list(_d?['sources']))
        Text('• ${_s(x['what'])} (${_s(x['date'])})', style: const TextStyle(fontSize: 11.5, color: C.faint)),
      const SizedBox(height: 10),
      GlassButton(label: 'Register (Excel)', icon: Icons.table_chart_rounded, onTap: _busy ? null : () => _run('POST', '/api/tourguide/register')),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Booking', 'Tour', 'Licence · Hisaab', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Tour guide'),
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
                    1 => _bookingsTab(),
                    2 => _toursTab(),
                    3 => _moneyTab(),
                    _ => _rulesTab(),
                  },
                ),
        ),
      ]),
    );
  }
}

/// One booking: group file, plan, safety + weather, roll call, scripts, money, cards.
class TourguideBookingPage extends StatefulWidget {
  const TourguideBookingPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<TourguideBookingPage> createState() => _TourguideBookingPageState();
}

class _TourguideBookingPageState extends State<TourguideBookingPage> {
  Map<String, dynamic>? _b;
  Map<String, dynamic>? _plan;
  Map<String, dynamic>? _safety;
  String _script = '';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _id => _s(_b?['id']).isEmpty ? widget.id : _s(_b?['id']);

  Future<void> _load() async {
    try {
      final b = _m(await widget.app.api!.call('GET', '/api/tourguide/bookings/${widget.id}'));
      if (mounted) setState(() => _b = b);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _post(String sub, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/tourguide/bookings/$_id/$sub', body ?? {});
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Future<void> _edit() async {
    final b = _b ?? {};
    final f = await _form(context, 'Group file', const [
      ('lead_name', 'Mehmaan ka naam'),
      ('phone', 'Mobile'),
      ('guests', 'Kitne log'),
      ('day', 'Date'),
      ('start_time', 'Samay'),
      ('language', 'Bhasha'),
      ('pickup', 'Pickup'),
      ('special_needs', 'Khaas zaroorat'),
      ('emergency_name', 'Emergency: naam'),
      ('emergency_phone', 'Emergency: number (Pehchaan Locker mein)'),
      ('text', 'Mehmaan: "naam, umr, videshi" har line (ID ho to aakhir mein; locker mein jayega)'),
    ], ok: 'Save', initial: {
      for (final k in ['lead_name', 'phone', 'guests', 'day', 'start_time', 'language', 'pickup', 'special_needs']) k: _s(b[k]),
    });
    if (f == null) return;
    final body = <String, dynamic>{...f}..remove('text');
    if (f['guests'] != null) body['guests'] = _n(f['guests']);
    final gl = <Map<String, dynamic>>[];
    for (final raw in (f['text'] ?? '').split('\n')) {
      final p = raw.split(',').map((e) => e.trim()).toList();
      if (p.isEmpty || p[0].isEmpty) continue;
      final g = <String, dynamic>{'name': p[0]};
      if (p.length > 1 && _n(p[1]) != null) g['age'] = _n(p[1]);
      if (p.length > 2 && p[2].toLowerCase().startsWith('v')) g['nationality'] = 'foreign';
      if (p.length > 3 && p[3].isNotEmpty) g['id'] = p[3];
      gl.add(g);
    }
    if (gl.isNotEmpty) body['guest_list'] = gl;
    setState(() => _busy = true);
    await _call(context, widget.app, 'PATCH', '/api/tourguide/bookings/$_id', body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _money(String kind) async {
    final f = await _form(context, switch (kind) { 'received' => 'Paise mile', 'refund' => 'Refund card', _ => 'Discount card' }, [
      ('amount', 'Kitna'),
      if (kind == 'discount') ('pct', 'Ya % (amount khaali ho to)'),
      if (kind != 'received') ('reason', 'Wajah'),
      if (kind == 'received') ('ref', 'UTR / ref (last digits)'),
    ]);
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['amount'] != null) body['amount'] = _n(f['amount']);
    if (f['pct'] != null) body['pct'] = _n(f['pct']);
    await _post(kind, body);
  }

  Future<void> _roll() async {
    final names = _list(_b?['guest_list']).map((g) => _s(g['name'])).where((x) => x.isNotEmpty).toList();
    final f = await _form(context, 'Ginti', [
      ('checkpoint', 'Kahan (stop)'),
      if (names.isNotEmpty) ('present', 'Kaun aaye (comma se): ${names.join(', ')}') else ('count', 'Kitne aaye'),
    ], ok: 'Darj');
    if (f == null) return;
    final body = <String, dynamic>{'checkpoint': f['checkpoint'] ?? ''};
    if (f['present'] != null) body['present'] = f['present']!.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    if (f['count'] != null) body['count'] = _n(f['count']);
    await _post('roll', body);
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(b?['number']).isEmpty ? 'Booking' : _s(b?['number']))),
      body: b == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(14), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text('${_s(b['lead_name'])} · ${_s(b['guests'])} log', style: const TextStyle(fontWeight: FontWeight.w800))),
                      Pill(_s(b['status_label'])),
                    ]),
                    _line('Tour', _s(b['tour'])),
                    _line('Kab', '${_s(b['day'])} ${_s(b['start_time'])}'),
                    _line('Mobile', _s(b['phone'])),
                    _line('Bhasha', _s(b['language_label'])),
                    _line('Pickup', _s(b['pickup'])),
                    _line('Khaas', _s(b['special_needs']), color: C.warn),
                    _line('Emergency', _s(b['emergency'])),
                    _line('Kul', '${_s(b['total_text'])} (${_s(b['how'])})'),
                    _line('Mila', _s(b['paid'])),
                    _line('Baaki', _s(b['due_text'])),
                    _line('Yatra', _s(b['travel_trip'])),
                    for (final g in _list(b['guest_list']))
                      Text('• ${_s(g['name'])} ${_s(g['age'])} ${_s(g['nationality']) == 'foreign' ? '(videshi)' : ''} ${_s(g['id_masked'])}',
                          style: const TextStyle(fontSize: 12, color: C.faint)),
                  ]),
                ),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(label: 'File badlo', icon: Icons.edit_rounded, height: 38, onTap: _busy ? null : _edit),
                  GlassButton(label: 'Jagah roko', height: 38, onTap: _busy ? null : () => _post('hold')),
                  GradientButton(label: 'Pakka karo (card)', icon: Icons.verified_rounded, height: 38, onTap: _busy ? null : () => _post('confirm')),
                  GlassButton(
                      label: 'Din ka plan',
                      height: 38,
                      onTap: _busy
                          ? null
                          : () async {
                              try {
                                final p = _m(await widget.app.api!.call('GET', '/api/tourguide/bookings/$_id/plan'));
                                if (mounted) setState(() => _plan = p);
                              } catch (e) {
                                if (mounted) _snack(context, '$e');
                              }
                            }),
                  GlassButton(
                      label: 'Safety + mausam',
                      height: 38,
                      onTap: _busy
                          ? null
                          : () async {
                              final r = await _post('safety');
                              if (r != null && mounted) setState(() => _safety = r);
                            }),
                  GlassButton(label: 'Ginti', height: 38, onTap: _busy ? null : _roll),
                  GlassButton(label: 'Ginti sheet', height: 38, onTap: _busy ? null : () => _post('roll_sheet')),
                  GlassButton(
                      label: 'Intro script',
                      height: 38,
                      onTap: _busy
                          ? null
                          : () async {
                              final r = await _post('script', {'language': _s(b['language'])});
                              if (r != null && mounted) setState(() => _script = _s(r['text']));
                            }),
                  GlassButton(label: 'Kal ki yaad (card)', height: 38, onTap: _busy ? null : () => _post('message', {'kind': 'reminder'})),
                  GlassButton(label: 'Paise mile', height: 38, onTap: _busy ? null : () => _money('received')),
                  GlassButton(label: 'Refund', height: 38, onTap: _busy ? null : () => _money('refund')),
                  GlassButton(label: 'Discount', height: 38, onTap: _busy ? null : () => _money('discount')),
                  GlassButton(label: 'Train / flight', height: 38, onTap: _busy ? null : () => _post('travel')),
                  GlassButton(label: 'Ho gaya', height: 38, onTap: _busy ? null : () => _post('status', {'status': 'done'})),
                  GlassButton(label: 'Review maango (card)', height: 38, onTap: _busy ? null : () => _post('review')),
                  GlassButton(label: 'Radd', height: 38, onTap: _busy ? null : () => _post('status', {'status': 'cancelled'})),
                  GlassButton(label: 'Jaankari mitao', height: 38, onTap: _busy ? null : () => _post('forget')),
                ]),
                if (_plan != null) ...[const SizedBox(height: 10), TourguidePlanCard(app: widget.app, data: {'plan': _plan})],
                if (_safety != null) ...[const SizedBox(height: 10), TourguidePlanCard(app: widget.app, data: {'safety': _safety})],
                if (_script.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  TourguideScriptCard(app: widget.app, data: {'text': _script, 'say': 'Intro (aap bolengi)'}),
                ],
                const SizedBox(height: 10),
                for (final c in _list(b['cards']))
                  Padding(padding: const EdgeInsets.only(bottom: 8), child: TourguideCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
                const Caption('LOG'),
                for (final l in _list(b['log']).reversed)
                  Text('${_s(l['at'])} · ${_s(l['by'])}: ${_s(l['what'])}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
              ]),
            ),
    );
  }
}

/// tourguide_card: confirm / message / refund / discount / spend. Decided ONLY by her tap here (fingerprint for refund / spend).
class TourguideCardCard extends StatefulWidget {
  const TourguideCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<TourguideCardCard> createState() => _TourguideCardCardState();
}

class _TourguideCardCardState extends State<TourguideCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/tourguide/cards/$id/challenge'));
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

  Future<void> _decide(bool yes, {String via = 'self'}) async {
    final id = _s(_c['id']);
    final show = _m(_c['show']);
    setState(() => _busy = true);
    try {
      if (yes && via == 'self' && (_s(_c['kind']) == 'confirm' || _s(_c['kind']) == 'message')) {
        final link = _s(show['wa']).isNotEmpty ? _s(show['wa']) : _s(show['sms']);
        if (link.isEmpty) throw Exception('Mehmaan ka mobile nahi.');
        await Native.openExternal(url: link);
      }
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'via': via};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/tourguide/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/tourguide/cards/$id/decide', body: {...body, 'proof': proof});
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

  Future<void> _paid() async {
    final f = await _form(context, 'Maine de diya', const [('ref', 'UTR / ref (last digits)')], ok: 'Darj');
    if (f == null) return;
    final m = await _call(context, widget.app, 'POST', '/api/tourguide/cards/${_s(_c['id'])}/paid', {'ref': f['ref'] ?? ''});
    if (m != null && mounted) setState(() => _c = _m(m['card']).isEmpty ? _c : _m(m['card']));
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final show = _m(c['show']);
    final st = _s(c['status']);
    final kind = _s(c['kind']);
    final talks = kind == 'confirm' || kind == 'message';
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(c['money'] == true ? Icons.payments_rounded : (talks ? Icons.sms_rounded : Icons.discount_rounded), color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · ${_s(c['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'sent' => 'bheja', 'approved' => 'maana', 'done' => 'diya', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' || st == 'stale' ? C.bad : C.ok)),
        ]),
        Text(_s(show['title']), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        if (_s(show['text']).isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(8)),
            child: Text(_s(show['text']), style: const TextStyle(fontSize: 12.5)),
          ),
        _line('Kul', _s(show['amount_text'])),
        _line('Wajah', _s(show['reason'])),
        _line('Policy', _s(show['policy'])),
        _line('GST', _s(show['gst_note'])),
        for (final x in _strs(show['checks'])) Text('⚠ $x', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(
                label: talks ? 'Haan, apne WhatsApp se' : 'Haan',
                icon: talks ? Icons.send_rounded : Icons.check_rounded,
                height: 40,
                onTap: _busy ? null : () => _decide(true)),
            if (talks) GlassButton(label: 'Business number se', height: 40, onTap: _busy ? null : () => _decide(true, via: 'business')),
            GlassButton(label: 'Nahi', height: 40, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved' && c['money'] == true)
          GlassButton(label: 'Maine de diya', icon: Icons.done_all_rounded, height: 40, onTap: _busy ? null : _paid),
        const Text('Hoola paise nahi leta / deta; message bhi aapke tap se hi jaata hai.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// tourguide_booking: one group file, updated in place.
class TourguideBookingCard extends StatelessWidget {
  const TourguideBookingCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final b = _m(data['booking']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TourguideBookingPage(app: app, id: _s(b['id'])))),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.groups_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(b['number'])} · ${_s(b['lead_name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(b['status_label'])),
          ]),
          Text('${_s(b['tour'])} · ${_s(b['day'])} ${_s(b['start_time'])} · ${_s(b['guests'])} log · ${_s(b['total_text'])}',
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
          if (_s(data['say']).isNotEmpty) Text(_s(data['say']), style: const TextStyle(fontSize: 12.5)),
        ]),
      ),
    );
  }
}

/// tourguide_plan: day plan (stops, timings only as she gave, ticket total) or safety brief (+ weather).
class TourguidePlanCard extends StatelessWidget {
  const TourguidePlanCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final p = _m(data['plan']);
    final sf = _m(data['safety']);
    if (p.isNotEmpty) {
      return Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Din ka plan', style: TextStyle(fontWeight: FontWeight.w800)),
          _line('Milna', _s(p['meeting_point'])),
          for (final x in _list(p['stops']))
            Text('${_s(x['arrive'])}-${_s(x['leave'])}  ${_s(x['name'])}  (khule ${_s(x['open'])}-${_s(x['close'])}, ticket ${_s(x['ticket'])})',
                style: const TextStyle(fontSize: 12.5)),
          _line('Ticket kul', _s(p['ticket_text'])),
          for (final w in _strs(p['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          for (final a in _strs(p['asi_steps'])) Text('• $a', style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      );
    }
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Safety brief', style: TextStyle(fontWeight: FontWeight.w800)),
        for (final w in _strs(sf['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        for (final l in _strs(sf['lines'])) Text('• $l', style: const TextStyle(fontSize: 12.5)),
        if (_s(data['say']).isNotEmpty && sf.isEmpty) Text(_s(data['say']), style: const TextStyle(fontSize: 12.5)),
      ]),
    );
  }
}

/// tourguide_script: an intro the guide SAYS (draft; copy).
class TourguideScriptCard extends StatelessWidget {
  const TourguideScriptCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.record_voice_over_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text(_s(data['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
          ]),
          const SizedBox(height: 6),
          SelectableText(_s(data['text']), style: const TextStyle(fontSize: 13)),
        ]),
      );
}

/// tourguide_alert: missing guest at roll call, licence renewal, tour to mark done, DPDP forget nudge.
class TourguideAlertCard extends StatelessWidget {
  const TourguideAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final urgent = _s(data['kind']) == 'roll';
    return Glass(
      border: urgent ? C.bad : null,
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(urgent ? Icons.warning_rounded : Icons.tour_rounded, color: urgent ? C.bad : C.accent),
        const SizedBox(width: 8),
        Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13))),
      ]),
    );
  }
}

/// tourguide_day: the morning note.
class TourguideDayCard extends StatelessWidget {
  const TourguideDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aaj ke tour', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 6),
          GlassButton(
              label: 'Kholo',
              height: 38,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TourguideScreen(app: app)))),
        ]),
      );
}
