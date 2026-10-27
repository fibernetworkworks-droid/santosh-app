/// Profile > Event Sahayak: Hoola as the event planner's coworker (corporate, conference, launch, birthday, college fest, expo).
/// Aaj (this week's events, late tasks, permissions, cards waiting) · Events (event page: budget by heads with vendor quotes +
/// comparison, client quotation / invoice, vendor bookings, guests + RSVP + invites, tasks, permissions, run of show, report)
/// · Vendors · Niyam (firm, GST, margin, UPI, sound cut-off, team).
/// Vendor bookings / advances (fingerprint once a phone key is set up), the client quotation / invoice, invites / messages and
/// any spend run only after HER tap. Hoola never invents a vendor price and never sends a message itself.
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
    {String ok = 'Aage', Map<String, String> initial = const {}, Set<String> multi = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: multi.contains(k) ? 6 : 1),
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
    final m = _m(await app.api!.call(method, path, body: body));
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']), upi = _s(draft['upi']);
  if (wa.isEmpty && sms.isEmpty && upi.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (upi.isNotEmpty) GlassButton(label: 'UPI app kholo', icon: Icons.currency_rupee_rounded, height: 40, onTap: () => Native.openExternal(url: upi)),
  ]);
}

/// Signs approvekey's challenge with her phone's fingerprint key (money cards once a phone key is set up).
Future<Map<String, dynamic>> _proof(Santosh app, String challengePath, String fallbackTitle) async {
  final ch = _m(await app.api!.call('POST', challengePath));
  final show = _m(ch['show']);
  final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? fallbackTitle : _s(show['title']),
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

/// POST a decide route; on 428 (fingerprint needed) sign the challenge and resend with `proof`.
Future<Map<String, dynamic>> _decideWithFinger(Santosh app, String decidePath, String challengePath, Map<String, dynamic> body,
    String title) async {
  try {
    return _m(await app.api!.call('POST', decidePath, body: body));
  } on ApiException catch (e) {
    if (body['yes'] != true || e.status != 428) rethrow;
    final proof = await _proof(app, challengePath, title);
    return _m(await app.api!.call('POST', decidePath, body: {...body, 'proof': proof}));
  }
}

class EventplanScreen extends StatefulWidget {
  const EventplanScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<EventplanScreen> createState() => _EventplanScreenState();
}

class _EventplanScreenState extends State<EventplanScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/eventplan'));
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
      .push(MaterialPageRoute(builder: (_) => EventplanEventPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newEvent() async {
    final f = await _form(context, 'Naya event', const [
      ('name', 'Event ka naam (jaise Acme dealer meet)'),
      ('client', 'Client'),
      ('client_phone', 'Client ka phone'),
      ('day', 'Tareekh (DD-MM-YYYY)'),
      ('start', 'Shuru (HH:MM)'),
      ('end', 'Khatam (HH:MM)'),
      ('venue', 'Venue'),
      ('city', 'Shahar'),
      ('headcount', 'Kitne log'),
      ('budget', 'Client ka budget'),
      ('brief', 'Brief (client ke shabd)'),
    ], multi: const {'brief'});
    if (f == null) return;
    final r = await _run('POST', '/api/eventplan/events', {
      ...f,
      if (f['headcount'] != null) 'headcount': _n(f['headcount']),
      if (f['budget'] != null) 'budget': _n(f['budget']),
    });
    final id = _s(_m(r?['event'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  Widget _aaj() {
    final day = _m(_d?['day']);
    final w = _m(day['waiting']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(w['bookings']).isNotEmpty) const Caption('VENDOR BOOKING: AAPKI HAAN'),
      for (final b in _list(w['bookings']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: EventplanBookingCard(app: widget.app, data: {'booking': b}, onDone: _load)),
      if (_list(w['docs']).isNotEmpty) const Caption('QUOTE / INVOICE: AAPKI HAAN'),
      for (final d in _list(w['docs']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: EventplanDocCard(app: widget.app, data: {'doc': d}, onDone: _load)),
      if (_list(w['messages']).isNotEmpty) const Caption('MESSAGE / INVITE: AAPKI HAAN'),
      for (final m in _list(w['messages']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: EventplanMessageCard(app: widget.app, data: {'message': m}, onDone: _load)),
      if (_list(w['spends']).isNotEmpty) const Caption('KHARCHA: AAPKI HAAN'),
      for (final x in _list(w['spends']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: EventplanSpendCard(app: widget.app, data: {'spend': x}, onDone: _load)),
    ]);
  }

  Widget _events() {
    final es = _list(_d?['events']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Naya event', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newEvent),
      const SizedBox(height: 12),
      if (es.isEmpty) const Text('Abhi koi event nahi.', style: TextStyle(color: C.muted)),
      for (final e in es)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Press(
            onTap: () => _open(_s(e['id'])),
            child: Glass(child: Row(children: [
              const Icon(Icons.celebration_rounded, color: C.accent),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(e['number'])} · ${_s(e['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text([_s(e['day']), _s(e['client']), _s(e['kind_label']), if (e['headcount'] != null) '${_s(e['headcount'])} log']
                    .where((x) => x.isNotEmpty).join(' · '), style: const TextStyle(fontSize: 12.5, color: C.muted)),
              ])),
              Pill(_s(e['status_label'])),
            ])),
          ),
        ),
    ]);
  }

  Widget _vendors() {
    final vs = _list(_d?['vendors']);
    final heads = _m(_d?['heads']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Vendor jodo', icon: Icons.person_add_rounded, height: 44, onTap: _busy ? null : () async {
        final f = await _form(context, 'Vendor', [
          ('name', 'Naam'), ('head', 'Kaam: ${heads.keys.join(' / ')}'), ('phone', 'Phone'), ('upi_id', 'UPI ID (advance ke liye)'),
          ('gstin', 'GSTIN'), ('fssai', 'FSSAI no (caterer)'), ('notes', 'Note'),
        ]);
        if (f != null) await _run('POST', '/api/eventplan/vendors', f);
      }),
      const SizedBox(height: 10),
      for (final v in vs)
        Glass(margin: const EdgeInsets.only(bottom: 8), child: Row(children: [
          const Icon(Icons.storefront_rounded, color: C.teal),
          const SizedBox(width: 10),
          Expanded(child: Text('${_s(v['name'])} · ${_s(v['head_label'])}\n${_s(v['phone'])}'
              '${_s(v['fssai']).isEmpty ? '' : ' · FSSAI ${_s(v['fssai'])}'}')),
        ])),
    ]);
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    final team = _list(st['team']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['firm']).isEmpty ? 'Firm ka naam nahi' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('${_s(st['gstin']).isEmpty ? 'GSTIN nahi' : 'GSTIN ${_s(st['gstin'])}'} · GST ${_s(st['gst_pct'])}% (SAC ${_s(st['sac'])})',
            style: const TextStyle(color: C.muted)),
        Text('Kamai: ${_s(st['fee_mode'])} · margin ${_s(st['margin_pct'])}% · fee ${_s(st['fee_pct'])}%', style: const TextStyle(fontSize: 12.5)),
        Text('Sound ${_s(st['sound_till'])} tak (Noise Rules) · subah ka note ${_s(st['morning_time'])}', style: const TextStyle(fontSize: 12.5)),
        Text('UPI: ${_s(st['upi_id']).isEmpty ? '(Employee profile se)' : _s(st['upi_id'])}', style: const TextStyle(fontSize: 12.5)),
        if (team.isNotEmpty) Text('Team: ${team.map((t) => _s(t['name'])).join(', ')}', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Niyam', const [
            ('firm', 'Firm'), ('gstin', 'GSTIN'), ('address', 'Pata'), ('phone', 'Phone'), ('email', 'Email'), ('upi_id', 'UPI ID'),
            ('fee_mode', 'Kamai: markup / fee / none'), ('margin_pct', 'Margin % (vendor kharche par)'), ('fee_pct', 'Fee % (fee mode)'),
            ('gst_pct', 'GST % (CA se pakka; event management 18%)'), ('validity_days', 'Quote kitne din valid'),
            ('sound_till', 'Sound kab tak (22:00; state chhoot ho to 23:59 tak)'), ('morning_time', 'Subah ka note (HH:MM)'),
            ('team', 'Team: har line "Naam, phone, role"'), ('terms', 'Terms'),
          ], multi: const {'team', 'terms'}, initial: {for (final k in ['firm', 'gstin', 'address', 'phone', 'email', 'upi_id', 'fee_mode', 'terms',
            'sound_till', 'morning_time']) k: _s(st[k])});
          if (f == null) return;
          final body = <String, dynamic>{...f};
          for (final k in ['margin_pct', 'fee_pct', 'gst_pct', 'validity_days']) {
            if (f[k] != null) body[k] = _n(f[k]);
          }
          if (f['team'] != null) {
            body['team'] = [
              for (final l in f['team']!.split('\n'))
                if (l.trim().isNotEmpty)
                  {'name': l.split(',')[0].trim(), 'phone': l.split(',').length > 1 ? l.split(',')[1].trim() : '',
                    'role': l.split(',').length > 2 ? l.split(',')[2].trim() : ''},
            ];
          }
          await _run('PUT', '/api/eventplan/settings', body);
        }),
      ])),
      const SizedBox(height: 10),
      const Text('Vendor ke daam sirf unke quote se; Hoola daam, tareekh ya licence nahi gadhta. Booking, advance, quotation, '
          'invite aur kharcha sirf aapki haan se.', style: TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Events', 'Vendors', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Event Sahayak'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _events, _vendors, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- event page
class EventplanEventPage extends StatefulWidget {
  const EventplanEventPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<EventplanEventPage> createState() => _EventplanEventPageState();
}

class _EventplanEventPageState extends State<EventplanEventPage> {
  Map<String, dynamic>? _e;
  bool _busy = false;
  String get _base => '/api/eventplan/events/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final e = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _e = e);
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
    final e = _e ?? {};
    final f = await _form(context, 'Event badlo', const [
      ('client', 'Client'), ('client_phone', 'Client phone'), ('client_gstin', 'Client GSTIN'), ('client_state', 'Client state code'),
      ('day', 'Tareekh'), ('start', 'Shuru'), ('end', 'Khatam'), ('venue', 'Venue'), ('headcount', 'Log'), ('budget', 'Client ka budget'),
    ], initial: {for (final k in ['client', 'client_phone', 'client_gstin', 'client_state', 'day', 'start', 'end', 'venue']) k: _s(e[k]),
      'headcount': _s(e['headcount']), 'budget': _s(e['budget'])});
    if (f == null) return;
    await _run('PATCH', _base, {...f, if (f['headcount'] != null) 'headcount': _n(f['headcount']), if (f['budget'] != null) 'budget': _n(f['budget'])});
  }

  Future<void> _facts() async {
    final cur = _m(_e?['facts']);
    final keys = const {
      'sound': 'Sound / loudspeaker', 'food': 'Khana', 'music': 'Recorded music', 'alcohol': 'Sharab', 'pandal': 'Pandal / temporary structure',
      'stage': 'Bada stage / truss', 'fireworks': 'Aatishbaazi', 'drone': 'Drone', 'road': 'Sadak / rally', 'ticketed': 'Ticket bikenge',
    };
    final sel = {for (final k in keys.keys) k: cur[k] == true};
    String venueKind = _s(cur['venue_kind']).isEmpty ? 'indoor' : _s(cur['venue_kind']);
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(builder: (d, set) => AlertDialog(
        title: const Text('Event mein kya hoga?'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          Wrap(spacing: 6, children: [
            for (final v in const ['indoor', 'hotel', 'open', 'public'])
              ChoiceChip(label: Text(v), selected: venueKind == v, onSelected: (_) => set(() => venueKind = v)),
          ]),
          for (final e in keys.entries)
            CheckboxListTile(value: sel[e.key], title: Text(e.value), dense: true, onChanged: (v) => set(() => sel[e.key] = v == true)),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
        ],
      )),
    );
    if (ok != true) return;
    await _run('PATCH', _base, {'facts': {...sel, 'venue_kind': venueKind}});
  }

  Future<void> _vquote() async {
    final f = await _form(context, 'Vendor ka quote (jaisa unhone bataya)', const [
      ('vendor', 'Vendor ka naam'), ('amount', 'Rakam (per plate ho to ek plate ki)'), ('per', 'per: khaali / plate / person / hour / day'),
      ('qty', 'Kitne (plate / ghante)'), ('gst', 'GST: shamil / alag / pata nahi'), ('gst_pct', 'GST %'), ('what', 'Kya milega'),
      ('advance_pct', 'Advance %'), ('cancel_terms', 'Radd karne ki shart'), ('includes', 'Kya shamil'),
    ]);
    if (f == null) return;
    final g = (f['gst'] ?? '').toLowerCase();
    await _run('POST', '$_base/vquotes', {
      ...f, 'amount': _n(f['amount']), if (f['qty'] != null) 'qty': _n(f['qty']), if (f['gst_pct'] != null) 'gst_pct': _n(f['gst_pct']),
      if (f['advance_pct'] != null) 'advance_pct': _n(f['advance_pct']),
      'gst_included': g.startsWith('sha') ? true : (g.startsWith('alag') ? false : null),
    });
  }

  Future<void> _budgetLine() async {
    final f = await _form(context, 'Budget line', const [
      ('item', 'Item'), ('head', 'Head (venue / catering / decor / sound ...)'), ('cost', 'Kharcha (vendor ka quote / aapka; khaali = baad mein)'),
      ('margin_pct', 'Margin % (khaali = aapka default)'), ('pure', 'Client ki taraf se seedha (pure agent)? haan / nahi'),
    ]);
    if (f == null) return;
    await _run('POST', '$_base/budget', {'lines': [
      {'item': f['item'] ?? '', 'head': f['head'] ?? '', if (f['cost'] != null) 'cost': _n(f['cost']),
        if (f['margin_pct'] != null) 'margin_pct': _n(f['margin_pct']), 'pure_agent': (f['pure'] ?? '').toLowerCase().startsWith('h')},
    ]});
  }

  Future<void> _book(Map<String, dynamic> q) async {
    final f = await _form(context, 'Booking: ${_s(q['vendor'])}', const [
      ('advance', 'Advance (khaali = quote ka %)'), ('advance_due', 'Advance kab tak (DD-MM-YYYY)'), ('arrive', 'Event ke din pahunchna (HH:MM)'),
    ]);
    if (f == null) return;
    await _run('POST', '$_base/bookings', {'quote': _s(q['id']), if (f['advance'] != null) 'advance': _n(f['advance']),
      'advance_due': f['advance_due'] ?? '', 'arrive': f['arrive'] ?? ''});
  }

  Future<void> _guests() async {
    final f = await _form(context, 'Mehmaan jodo', const [('text', 'Har line: Naam phone, group')], multi: const {'text'});
    if (f == null) return;
    await _run('POST', '$_base/guests', {'text': f['text'] ?? ''});
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

  Future<void> _rsvp(Map<String, dynamic> g) async {
    final f = await _form(context, 'Jawab: ${_s(g['name'])}', const [('words', 'Unka jawab (haan +2 / nahi / shayad)')]);
    if (f == null) return;
    await _run('POST', '$_base/rsvp', {'guest': _s(g['id']), 'words': f['words'] ?? ''});
  }

  Future<void> _show() async {
    final cues = _list(_m(_e?['show'])['cues']);
    final text = cues.map((c) => '${_s(c['time'])} ${_s(c['what'])}${c['mins'] == null ? '' : ' (${_s(c['mins'])} min)'}'
        '${_s(c['who']).isEmpty ? '' : ' - ${_s(c['who'])}'}${_s(c['where']).isEmpty ? '' : ' | ${_s(c['where'])}'}').join('\n');
    final f = await _form(context, 'Run of show', const [('text', 'Har line: 18:30 Welcome (10 min) - Riya | stage')],
        initial: {'text': text}, multi: const {'text'});
    if (f == null) return;
    await _run('POST', '$_base/show', {'text': f['text'] ?? '', 'replace': true});
  }

  Future<void> _spend() async {
    final f = await _form(context, 'Kharcha (aapki haan se)', const [('what', 'Kis cheez ka'), ('amount', 'Rakam (bill se)'), ('payee', 'Kisko'),
      ('head', 'Head')]);
    if (f == null) return;
    await _run('POST', '$_base/spends', {...f, 'amount': _n(f['amount'])});
  }

  Future<void> _report() async {
    final f = await _form(context, 'Event ke baad', const [('attended', 'Kitne aaye'), ('issues', 'Dikkatein (har line ek)'), ('notes', 'Note')],
        multi: const {'issues', 'notes'});
    if (f == null) return;
    await _run('POST', '$_base/report', {if (f['attended'] != null) 'attended': _n(f['attended']), 'notes': f['notes'] ?? '',
      'issues': (f['issues'] ?? '').split('\n').where((x) => x.trim().isNotEmpty).toList()});
  }

  Widget _section(String title, List<Widget> children, {Widget? action}) => Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Expanded(child: Caption(title)), if (action != null) action]),
          ...children,
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final e = _e;
    if (e == null) return const Scaffold(backgroundColor: C.bgTop, body: Center(child: CircularProgressIndicator()));
    final b = _m(e['budget']);
    final g = _m(e['guests']);
    final gs = _m(g['summary']);
    final tk = _m(e['tasks']);
    final pm = _m(e['permits']);
    final sh = _m(e['show']);
    final vq = _list(e['vquotes']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${_s(e['number'])} · ${_s(e['name'])}'),
          actions: [IconButton(icon: const Icon(Icons.edit_rounded), onPressed: _busy ? null : _edit)]),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(e['kind_label'])} · ${_s(e['status_label'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
            Text('${_s(e['day']).isEmpty ? '[tareekh?]' : _s(e['day'])} ${_s(e['start'])}-${_s(e['end'])} · ${_s(e['venue']).isEmpty ? '[venue?]' : _s(e['venue'])}',
                style: const TextStyle(fontSize: 13)),
            Text('Client: ${_s(e['client'])} · ${_s(e['headcount'])} log · budget ${_s(e['budget_text'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
            const SizedBox(height: 6),
            GlassButton(label: 'Event mein kya hoga (permission ke liye)', icon: Icons.checklist_rounded, height: 38, onTap: _busy ? null : _facts),
          ])),
          _section('BUDGET', [
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(b['say']), style: const TextStyle(fontSize: 13)),
              for (final l in _list(b['lines']))
                Text('${_s(l['id'])} ${_s(l['head_label'])}: ${_s(l['item'])} · kharcha ${_rs(l['cost'])} → client ${_rs(l['client_price'])}'
                    '${l['pure_agent'] == true ? ' (seedha)' : ''}', style: TextStyle(fontSize: 12, color: l['cost'] == null ? C.warn : C.ink)),
              for (final w in _strs(b['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 12, color: C.warn)),
            ])),
          ], action: IconButton(icon: const Icon(Icons.add_rounded, color: C.accent), onPressed: _busy ? null : _budgetLine)),
          _section('VENDOR QUOTES', [
            for (final q in vq)
              Glass(margin: const EdgeInsets.only(bottom: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(q['head_label'])} · ${_s(q['vendor'])} · ${_rs(q['total'] ?? q['base'])}${q['chosen'] == true ? '  ✓ chuna' : ''}',
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                if (_s(q['note']).isNotEmpty) Text('⚠ ${_s(q['note'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
                Text([_s(q['what']), if (q['advance_pct'] != null) 'advance ${_s(q['advance_pct'])}%', _s(q['cancel_terms'])]
                    .where((x) => x.isNotEmpty).join(' · '), style: const TextStyle(fontSize: 12, color: C.muted)),
                Wrap(spacing: 8, children: [
                  if (q['chosen'] != true) GlassButton(label: 'Yeh chuno', height: 36, onTap: _busy ? null : () => _run('POST', '/api/eventplan/vquotes/${_s(q['id'])}/choose')),
                  GlassButton(label: 'Book karo', icon: Icons.event_available_rounded, height: 36, onTap: _busy ? null : () => _book(q)),
                ]),
              ])),
          ], action: IconButton(icon: const Icon(Icons.add_rounded, color: C.accent), onPressed: _busy ? null : _vquote)),
          _section('CLIENT', [
            for (final d in _list(e['docs']).reversed.take(3))
              Padding(padding: const EdgeInsets.only(bottom: 8), child: EventplanDocCard(app: widget.app, data: {'doc': d}, onDone: _load)),
            Wrap(spacing: 8, runSpacing: 6, children: [
              GlassButton(label: 'Quotation banao', icon: Icons.request_quote_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/quote')),
              GlassButton(label: 'Invoice (event ke baad)', icon: Icons.receipt_long_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/invoice')),
              GlassButton(label: 'Client se paise mile', icon: Icons.currency_rupee_rounded, height: 40, onTap: _busy ? null : () async {
                final f = await _form(context, 'Client se mila', const [('amount', 'Kitne'), ('ref', 'UTR / cheque')]);
                if (f != null) await _run('POST', '$_base/client_paid', {'amount': _n(f['amount']), 'ref': f['ref'] ?? ''});
              }),
            ]),
          ]),
          _section('BOOKING / KHARCHA', [
            for (final bk in _list(e['bookings']))
              Padding(padding: const EdgeInsets.only(bottom: 8), child: EventplanBookingCard(app: widget.app, data: {'booking': bk}, onDone: _load)),
            for (final x in _list(e['spends']))
              Padding(padding: const EdgeInsets.only(bottom: 8), child: EventplanSpendCard(app: widget.app, data: {'spend': x}, onDone: _load)),
          ], action: IconButton(icon: const Icon(Icons.add_card_rounded, color: C.accent), onPressed: _busy ? null : _spend)),
          _section('MEHMAAN · ${_s(gs['total'])}', [
            Text(_s(g['say']), style: const TextStyle(fontSize: 12.5)),
            Wrap(spacing: 8, runSpacing: 6, children: [
              GlassButton(label: 'Jodo', icon: Icons.person_add_alt_rounded, height: 38, onTap: _busy ? null : _guests),
              GlassButton(label: 'Sheet', icon: Icons.upload_file_rounded, height: 38, onTap: _busy ? null : _importGuests),
              GlassButton(label: 'Invite (haan se)', icon: Icons.mail_rounded, height: 38,
                  onTap: _busy ? null : () => _run('POST', '$_base/messages', {'kind': 'invite'})),
              GlassButton(label: 'Yaad dilao', icon: Icons.notifications_rounded, height: 38,
                  onTap: _busy ? null : () => _run('POST', '$_base/messages', {'kind': 'reminder'})),
            ]),
            for (final x in _list(g['guests']).take(60))
              ListTile(dense: true, contentPadding: EdgeInsets.zero, title: Text(_s(x['name'])),
                  subtitle: Text([_s(x['group']), x['invited'] == true ? 'invite gaya' : 'invite nahi', if (x['no_messages'] == true) 'message mat bhejo']
                      .where((s) => s.isNotEmpty).join(' · ')),
                  trailing: Text('${_s(x['status']).isEmpty ? '?' : _s(x['status'])}${(x['plus'] ?? 0) == 0 ? '' : ' +${_s(x['plus'])}'}'),
                  onTap: _busy ? null : () => _rsvp(x)),
          ]),
          _section('KAAM · ${_s(tk['late'])} der se', [
            for (final t in _list(tk['tasks']))
              CheckboxListTile(dense: true, contentPadding: EdgeInsets.zero, value: t['status'] == 'done',
                  title: Text(_s(t['what'])), subtitle: Text('${_s(t['due'])}${_s(t['owner']).isEmpty ? ' · koi zimmedar nahi' : ' · ${_s(t['owner'])}'}'),
                  onChanged: _busy ? null : (v) => _run('PATCH', '/api/eventplan/tasks/${_s(t['id'])}', {'status': v == true ? 'done' : 'open'}),
                  secondary: IconButton(icon: const Icon(Icons.person_rounded, size: 20), onPressed: _busy ? null : () async {
                    final f = await _form(context, 'Zimmedar', const [('owner', 'Kaun karega'), ('due', 'Kab tak')], initial: {'owner': _s(t['owner'])});
                    if (f != null) await _run('PATCH', '/api/eventplan/tasks/${_s(t['id'])}', f);
                  })),
          ]),
          _section('PERMISSION', [
            Text(_s(pm['note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
            for (final p in _list(pm['permits']))
              ListTile(dense: true, contentPadding: EdgeInsets.zero,
                  title: Text(_s(p['label']), style: TextStyle(color: p['late'] == true ? C.warn : C.ink)),
                  subtitle: Text('${_s(p['why'])}\n${_s(p['who'])} · ${_s(p['apply_by'])} tak${_s(p['ref']).isEmpty ? '' : ' · ${_s(p['ref'])}'}'),
                  trailing: PopupMenuButton<String>(
                    child: Pill(_s(p['status'])),
                    onSelected: (v) => _run('POST', '$_base/permits', {'key': _s(p['key']), 'status': v}),
                    itemBuilder: (_) => [for (final v in const ['pending', 'applied', 'granted', 'refused', 'not_needed']) PopupMenuItem(value: v, child: Text(v))],
                  )),
          ]),
          _section('RUN OF SHOW', [
            for (final c in _list(sh['timeline']))
              Text('${_s(c['time'])}  ${_s(c['what'])}${_s(c['who']).isEmpty ? '' : ' · ${_s(c['who'])}'}',
                  style: TextStyle(fontSize: 12.5, color: c['kind'] == 'arrival' ? C.teal : C.ink)),
            for (final p in _strs(sh['problems'])) Text('⚠ $p', style: const TextStyle(fontSize: 12, color: C.warn)),
          ], action: IconButton(icon: const Icon(Icons.edit_note_rounded, color: C.accent), onPressed: _busy ? null : _show)),
          const SizedBox(height: 14),
          Wrap(spacing: 8, runSpacing: 6, children: [
            GlassButton(label: 'Event ke baad report', icon: Icons.summarize_rounded, height: 40, onTap: _busy ? null : _report),
            GlassButton(label: 'Mehmaan / client ki details hatao', icon: Icons.delete_sweep_rounded, height: 40,
                onTap: _busy ? null : () => _run('POST', '$_base/forget')),
          ]),
          const SizedBox(height: 30),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
/// eventplan_doc: the client quotation / invoice waits for HER tap. Also in calls.
class EventplanDocCard extends StatefulWidget {
  const EventplanDocCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<EventplanDocCard> createState() => _EventplanDocCardState();
}

class _EventplanDocCardState extends State<EventplanDocCard> {
  bool _busy = false;
  late Map<String, dynamic> _d = _m(widget.data['doc']);
  Map<String, dynamic> _draft = {};

  Future<void> _post(String path, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', path, body: body));
      if (mounted) {
        setState(() {
          if (_m(m['doc']).isNotEmpty) _d = _m(m['doc']);
          if (_m(m['draft']).isNotEmpty) _draft = _m(m['draft']);
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
    final d = _d, t = _m(d['totals']);
    final st = _s(d['status']);
    final id = _s(d['id']);
    final inv = _s(d['kind']) == 'invoice';
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(inv ? Icons.receipt_long_rounded : Icons.request_quote_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${inv ? 'Invoice' : 'Quotation'} ${_s(d['number'])} · ${_s(d['client'])} · ${_s(d['total_text'])}',
              style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'draft' => 'draft', 'approved' => 'bhejne ko taiyaar', 'sent' => 'bheja',
            'accepted' => 'pakka', 'rejected' => 'nahi', _ => st }, fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(d['event'])} · taxable ${_rs(t['taxable'])} + GST ${_rs(t['tax'])}${t['intra'] == false ? ' (IGST)' : ' (CGST + SGST)'}'
            '${(t['pure_agent'] ?? 0) == 0 ? '' : ' + seedha ${_rs(t['pure_agent'])}'}'
            '${inv ? ' · baaki ${_rs(t['balance'])}' : ' · ${_s(d['valid_until'])} tak'}', style: const TextStyle(fontSize: 12.5)),
        for (final b in _strs(d['blanks'])) Text('⚠ $b', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (st == 'draft' && _strs(d['blanks']).isEmpty)
            GlassButton(label: 'Haan ke liye card', icon: Icons.send_rounded, height: 40,
                onTap: _busy ? null : () => _post('/api/eventplan/docs/$id/request', {})),
          if (st == 'waiting') ...[
            GradientButton(label: 'Haan, client ko bhejo', height: 42,
                onTap: _busy ? null : () => _post('/api/eventplan/docs/$id/decide', {'yes': true, 'hash': _s(d['hash'])})),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _post('/api/eventplan/docs/$id/decide', {'yes': false, 'hash': _s(d['hash'])})),
          ],
          if (st == 'approved') GlassButton(label: 'Maine bhej diya', icon: Icons.check_rounded, height: 40,
              onTap: _busy ? null : () => _post('/api/eventplan/docs/$id/mark', {'what': 'sent'})),
          if (!inv && (st == 'approved' || st == 'sent')) GlassButton(label: 'Client ne maana', icon: Icons.handshake_rounded, height: 40,
              onTap: _busy ? null : () => _post('/api/eventplan/docs/$id/mark', {'what': 'accepted'})),
        ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Client ko sirf aapki haan se jaata hai; message aap khud bhejti hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// eventplan_booking: a vendor booking (+ advance) waits for HER tap (+ fingerprint when an advance goes). Also in calls.
class EventplanBookingCard extends StatefulWidget {
  const EventplanBookingCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<EventplanBookingCard> createState() => _EventplanBookingCardState();
}

class _EventplanBookingCardState extends State<EventplanBookingCard> {
  bool _busy = false;
  late Map<String, dynamic> _b = _m(widget.data['booking']);
  Map<String, dynamic> _draft = {};

  Future<void> _go(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final m = await f();
      if (mounted) {
        setState(() {
          if (_m(m['booking']).isNotEmpty) _b = _m(m['booking']);
          if (_m(m['draft']).isNotEmpty) _draft = _m(m['draft']);
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
    final b = _b;
    final st = _s(b['status']);
    final id = _s(b['id']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.event_available_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(b['number'])} · ${_s(b['vendor'])} · ${_s(b['amount_text'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'pakka', 'advance_paid' => 'advance diya', 'rejected' => 'nahi', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(b['event'])} ${_s(b['day'])} · ${_s(b['head_label'])}'
            '${(b['advance'] ?? 0) == 0 ? '' : ' · advance ${_s(b['advance_text'])}${_s(b['advance_due']).isEmpty ? '' : ' (${_s(b['advance_due'])} tak)'}'}'
            '${_s(b['arrive']).isEmpty ? '' : ' · ${_s(b['arrive'])} pahunchna'}', style: const TextStyle(fontSize: 12.5)),
        if (_s(b['terms']).isNotEmpty) Text(_s(b['terms']), style: const TextStyle(fontSize: 12, color: C.muted)),
        for (final c in _strs(b['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, book karo', height: 42, onTap: _busy ? null : () => _go(() => _decideWithFinger(widget.app,
                '/api/eventplan/bookings/$id/decide', '/api/eventplan/bookings/$id/challenge', {'yes': true, 'hash': _s(b['hash'])}, 'Vendor booking')))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _go(() async =>
                _m(await widget.app.api!.call('POST', '/api/eventplan/bookings/$id/decide', body: {'yes': false, 'hash': _s(b['hash'])})))),
          ]),
        if (st == 'approved')
          GlassButton(label: 'Advance diya', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : () async {
            final f = await _form(context, 'Advance diya', const [('amount', 'Kitna'), ('ref', 'UTR')], initial: {'amount': _s(b['advance'])});
            if (f == null) return;
            await _go(() async => _m(await widget.app.api!.call('POST', '/api/eventplan/bookings/$id/paid', body: {'amount': _n(f['amount']), 'ref': f['ref'] ?? ''})));
          }),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola khud paise nahi deta; advance aap apne UPI app se dengi.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// eventplan_spend: any other spend waits for HER tap (+ fingerprint once a phone key is set up). Also in calls.
class EventplanSpendCard extends StatefulWidget {
  const EventplanSpendCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<EventplanSpendCard> createState() => _EventplanSpendCardState();
}

class _EventplanSpendCardState extends State<EventplanSpendCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['spend']);

  Future<void> _go(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final m = await f();
      if (mounted) {
        setState(() { if (_m(m['spend']).isNotEmpty) _x = _m(m['spend']); });
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
    final id = _s(x['id']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.payments_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['number'])} · ${_s(x['what'])} · ${_s(x['amount_text'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'paid' => 'diya', 'rejected' => 'nahi', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(x['event'])} · ${_s(x['head_label'])}${_s(x['payee']).isEmpty ? '' : ' · ${_s(x['payee'])}'}', style: const TextStyle(fontSize: 12.5)),
        for (final c in _strs(x['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan', height: 42, onTap: _busy ? null : () => _go(() => _decideWithFinger(widget.app,
                '/api/eventplan/spends/$id/decide', '/api/eventplan/spends/$id/challenge', {'yes': true, 'hash': _s(x['hash'])}, 'Kharcha')))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _go(() async =>
                _m(await widget.app.api!.call('POST', '/api/eventplan/spends/$id/decide', body: {'yes': false, 'hash': _s(x['hash'])})))),
          ]),
        if (st == 'approved')
          GlassButton(label: 'Maine de diya', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : () => _go(() async =>
              _m(await widget.app.api!.call('POST', '/api/eventplan/spends/$id/paid', body: {})))),
      ]),
    );
  }
}

/// eventplan_message: invites / messages wait for HER tap; then one WhatsApp / SMS link per person she sends. Also in calls.
class EventplanMessageCard extends StatefulWidget {
  const EventplanMessageCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<EventplanMessageCard> createState() => _EventplanMessageCardState();
}

class _EventplanMessageCardState extends State<EventplanMessageCard> {
  bool _busy = false;
  late Map<String, dynamic> _msg = _m(widget.data['message']);
  List<Map<String, dynamic>> _links = [];

  Future<void> _post(String path, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', path, body: body));
      if (mounted) {
        setState(() {
          if (_m(m['message']).isNotEmpty) _msg = _m(m['message']);
          if (m['links'] is List) _links = _list(m['links']);
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
    final x = _msg;
    final st = _s(x['status']);
    final id = _s(x['id']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.mail_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['event'])} · ${_s(x['kind'])} · ${_s(x['count'])} log', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'links taiyaar', 'sent' => 'bheja', 'rejected' => 'nahi', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text(_s(x['text']), style: const TextStyle(fontSize: 12.5)),
        Text(_strs(x['sample']).join(', '), style: const TextStyle(fontSize: 11.5, color: C.muted)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, draft banao', height: 42,
                onTap: _busy ? null : () => _post('/api/eventplan/messages/$id/decide', {'yes': true, 'hash': _s(x['hash'])}))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _post('/api/eventplan/messages/$id/decide', {'yes': false, 'hash': _s(x['hash'])})),
          ]),
        for (final l in _links.take(40))
          ListTile(dense: true, contentPadding: EdgeInsets.zero, title: Text(_s(l['name'])), subtitle: Text(_s(l['phone'])),
              trailing: IconButton(icon: const Icon(Icons.chat_rounded, color: C.ok),
                  onPressed: _s(l['wa']).isEmpty ? null : () => Native.openExternal(url: _s(l['wa'])))),
        if (st == 'approved')
          GlassButton(label: 'Sab ko bhej diya', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : () => _post('/api/eventplan/messages/$id/sent', {})),
        const Text('Hoola khud message nahi bhejta; har link aap apne phone se bhejti hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// eventplan_alert / eventplan_day: plain notes. Calls: no.
class EventplanNoteCard extends StatelessWidget {
  const EventplanNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Row(children: [
          const Icon(Icons.celebration_rounded, color: C.teal),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
          IconButton(
              icon: const Icon(Icons.open_in_new_rounded, color: C.faint),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EventplanScreen(app: app)))),
        ]),
      );
}
