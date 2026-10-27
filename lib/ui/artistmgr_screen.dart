/// Profile > Artist Sahayak: Hoola as a musician's manager.
/// Aaj (today / tomorrow's shows, holds ending, balances, releases, cards waiting) · Gigs (paste an offer, list, gig page with money,
/// rider, cards) · Artists (roster, members + splits, registrations, blocked days, payout) · Release (plan, tracks / ISRC, final
/// metadata) · Niyam (agency, UPI, commission, travel gaps, hold hours, advance, distributors, terms).
/// Every reply / contract / confirm / invoice / payment request / message / release final runs only after HER tap; the payout statement
/// also needs her phone's fingerprint once a phone key is set up. A double-booked artist is refused by the server.
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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label),
                maxLines: (k == 'text' || k == 'terms' || k == 'notes' || k == 'rules' || k == 'members') ? 4 : 1),
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

Widget _draftButtons(Map<String, dynamic> d, {String name = ''}) {
  final wa = _s(d['wa']), sms = _s(d['sms']);
  if (wa.isEmpty && sms.isEmpty) return const SizedBox.shrink();
  final who = name.isEmpty ? '' : ' · $name';
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft$who', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft$who', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (_s(d['upi']).isNotEmpty) const Pill('UPI link aapke UPI ID ka'),
  ]);
}

/// "Arif, vocals, 9822022222, 40" per line -> members list.
List<Map<String, dynamic>> _members(String text) => [
      for (final line in text.split('\n'))
        if (line.trim().isNotEmpty)
          () {
            final p = line.split(',').map((x) => x.trim()).toList();
            return <String, dynamic>{
              'name': p[0],
              if (p.length > 1 && p[1].isNotEmpty) 'role': p[1],
              if (p.length > 2 && p[2].isNotEmpty) 'phone': p[2],
              if (p.length > 3 && _n(p[3]) != null) 'split_pct': _n(p[3]),
            };
          }(),
    ];

Widget _gigTile(BuildContext context, Map<String, dynamic> g, VoidCallback onTap) => Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: onTap,
        child: Glass(
          child: Row(children: [
            const Icon(Icons.mic_external_on_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(g['number'])} · ${_s(g['artist'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
              Text('${_s(g['day']).isEmpty ? 'tareekh?' : _s(g['day'])} ${_s(g['start'])} · ${_s(g['city'])} ${_s(g['venue'])}',
                  style: const TextStyle(fontSize: 12.5)),
              Text('${_s(g['promoter'])} · fee ${_s(g['fee_text'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
            ])),
            Pill(_s(g['status_label']).isEmpty ? _s(g['status']) : _s(g['status_label'])),
          ]),
        ),
      ),
    );

class ArtistmgrScreen extends StatefulWidget {
  const ArtistmgrScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ArtistmgrScreen> createState() => _ArtistmgrScreenState();
}

class _ArtistmgrScreenState extends State<ArtistmgrScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/artistmgr'));
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

  void _openGig(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => ArtistmgrGigPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Future<void> _offer() async {
    final f = await _form(context, 'Naya offer', const [
      ('text', 'Promoter ka message (paste karein)'), ('artist', 'Artist'), ('day', 'Tareekh (YYYY-MM-DD)'), ('start', 'Shuru (HH:MM)'),
      ('end', 'Khatam (HH:MM)'), ('city', 'Shehar'), ('venue', 'Venue'), ('fee', 'Fee (₹)'), ('promoter', 'Promoter'), ('phone', 'Promoter phone'),
    ]);
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['fee'] != null) body['fee'] = _n(f['fee']);
    final r = await _run('POST', '/api/artistmgr/gigs', body);
    final gigNo = _s(_m(r?['gig'])['number']);
    if (gigNo.isNotEmpty) _openGig(gigNo);
  }

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('AAPKI HAAN KA INTEZAAR'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: ArtistmgrCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('today', 'AAJ KE SHOW'), ('tomorrow', 'KAL KE SHOW'), ('holds', 'HOLD 24 GHANTE MEIN KHATAM')])
        if (_list(day[k]).isNotEmpty) ...[
          Caption(label),
          for (final g in _list(day[k])) _gigTile(context, g, () => _openGig(_s(g['number']))),
          const SizedBox(height: 8),
        ],
      for (final (k, label) in const [('balances', 'BAAKI PAYMENT'), ('unsettled', 'SETTLEMENT BAAKI'), ('releases', 'RELEASE KE KAAM'),
        ('regs_missing', 'REGISTRATION BAAKI')])
        if (_strs(day[k]).isNotEmpty) ...[Caption(label), for (final x in _strs(day[k])) Text('• $x'), const SizedBox(height: 8)],
      if (day['no_commission'] == true)
        const Text('Commission % Niyam mein nahi: settlement mein commission ki line nahi banegi.', style: TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  Widget _gigs() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya offer / gig', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _offer),
        const SizedBox(height: 12),
        if (_list(_d?['gigs']).isEmpty) const Text('Aage ka koi gig nahi.', style: TextStyle(color: C.muted)),
        for (final g in _list(_d?['gigs'])) _gigTile(context, g, () => _openGig(_s(g['number']))),
      ]);

  Future<void> _artistForm([Map<String, dynamic>? a]) async {
    final init = <String, String>{
      if (a != null) ...{
        'name': _s(a['name']), 'kind': _s(a['kind']), 'genre': _s(a['genre']), 'city': _s(a['city']), 'phone': _s(a['phone']),
        'min_fee': _s(a['min_fee']),
        'members': _list(a['members']).map((m) => [m['name'], m['role'], m['phone'], m['split_pct']].map(_s).join(', ')).join('\n'),
      }
    };
    final f = await _form(context, a == null ? 'Naya artist' : 'Artist badlo', const [
      ('name', 'Naam'), ('kind', 'Kism (singer / band / dj / instrumentalist / composer / lyricist / classical / folk)'), ('genre', 'Genre'),
      ('city', 'Shehar'), ('phone', 'Phone'), ('min_fee', 'Kam se kam fee (₹)'), ('members', 'Members: naam, role, phone, split % (har line)'),
    ], initial: init, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f, if (a != null) 'id': a['id']};
    body.remove('members');
    if (f['min_fee'] != null) body['min_fee'] = _n(f['min_fee']);
    if (f['members'] != null) body['members'] = _members(f['members']!);
    await _run('POST', '/api/artistmgr/artists', body);
  }

  void _openArtist(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => ArtistmgrArtistPage(app: widget.app, id: id, onEdit: _artistForm)))
      .then((_) => _load());

  Widget _artists() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya artist', icon: Icons.person_add_alt_1_rounded, height: 44, onTap: _busy ? null : () => _artistForm()),
        const SizedBox(height: 12),
        for (final a in _list(_d?['artists']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _openArtist(_s(a['id'])),
              child: Glass(
                child: Row(children: [
                  const Icon(Icons.queue_music_rounded, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(a['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text('${_s(a['kind_label'])} · ${_s(a['genre'])} · ${_s(a['city'])}', style: const TextStyle(fontSize: 12.5)),
                    if (_list(a['members']).isNotEmpty)
                      Text(_list(a['members']).map((m) => _s(m['name'])).join(', '), style: const TextStyle(fontSize: 12, color: C.muted)),
                  ])),
                ]),
              ),
            ),
          ),
        if (_list(_d?['payouts']).isNotEmpty) ...[
          const Caption('PAYOUT STATEMENT'),
          for (final p in _list(_d?['payouts']))
            Glass(
              child: Row(children: [
                Expanded(child: Text('${_s(p['number'])} · ${_s(p['artist'])} · ${_s(p['total_text'])}')),
                Pill(_s(p['status'])),
                if (_s(p['status']) == 'approved')
                  TextButton(
                      onPressed: () async {
                        final f = await _form(context, 'Payout bhej diya?', const [('ref', 'UTR / ref')], ok: 'Haan, bhej diya');
                        if (f != null) await _run('POST', '/api/artistmgr/payouts/${_s(p['id'])}/paid', f);
                      },
                      child: const Text('Bhej diya')),
              ]),
            ),
        ],
      ]);

  Future<void> _releaseForm([Map<String, dynamic>? r]) async {
    final f = await _form(context, r == null ? 'Naya release' : 'Release badlo', const [
      ('artist', 'Artist'), ('title', 'Naam'), ('kind', 'single / ep / album'), ('day', 'Release date (YYYY-MM-DD)'),
      ('distributor', 'Distributor'), ('upc', 'UPC (distributor deta hai)'), ('tracks', 'Gaane: title | ISRC (har line)'),
    ], initial: {
      if (r != null) ...{'artist': _s(r['artist']), 'title': _s(r['title']), 'kind': _s(r['kind']), 'day': _s(r['day']),
        'distributor': _s(r['distributor']), 'upc': _s(r['upc'])}
    }, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f, if (r != null) 'id': r['number']};
    body.remove('tracks');
    if (f['tracks'] != null) {
      body['tracks'] = [
        for (final line in f['tracks']!.split('\n'))
          if (line.trim().isNotEmpty)
            {'title': line.split('|').first.trim(), if (line.contains('|')) 'isrc': line.split('|').last.trim()},
      ];
    }
    await _run('POST', '/api/artistmgr/releases', body);
  }

  Widget _releases() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya release', icon: Icons.album_rounded, height: 44, onTap: _busy ? null : () => _releaseForm()),
        const SizedBox(height: 12),
        for (final r in _list(_d?['releases']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => ArtistmgrReleasePage(app: widget.app, ref: _s(r['number']), onEdit: _releaseForm)))
                  .then((_) => _load()),
              child: Glass(
                child: Row(children: [
                  const Icon(Icons.album_rounded, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${_s(r['number'])} · ${_s(r['title'])} · ${_s(r['day'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
                  Pill(_s(r['status'])),
                ]),
              ),
            ),
          ),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['agency']).isEmpty ? 'Agency ka naam nahi' : _s(st['agency']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('UPI ${_s(st['upi_id']).isEmpty ? '?' : _s(st['upi_id'])} · commission ${_s(st['commission_pct']).isEmpty ? '?' : '${_s(st['commission_pct'])}%'}'),
        Text('Same shehar gap ${_s(st['same_city_gap'])} min · alag shehar ${_s(st['travel_gap'])} min · hold ${_s(st['hold_hours'])} ghante'),
        Text('Advance ${_s(st['advance_pct'])}% · baaki show se ${_s(st['balance_days'])} din pehle'),
        for (final d in _list(st['distributors']))
          Text('• ${_s(d['name'])}: ${_s(d['share_pct'])}% · ${_s(d['lead_days'])} din pehle', style: const TextStyle(fontSize: 12.5)),
        if (_s(st['terms']).isNotEmpty) Text('Shartein: ${_s(st['terms'])}', style: const TextStyle(fontSize: 12.5)),
      ])),
      const SizedBox(height: 10),
      GlassButton(
        label: 'Niyam badlo',
        icon: Icons.tune_rounded,
        height: 44,
        onTap: () async {
          final f = await _form(context, 'Niyam', const [
            ('agency', 'Agency'), ('gstin', 'GSTIN'), ('upi_id', 'UPI ID'), ('commission_pct', 'Commission %'), ('royalty_pct', 'Royalty commission %'),
            ('same_city_gap', 'Same shehar gap (min)'), ('travel_gap', 'Alag shehar gap (min)'), ('hold_hours', 'Hold ghante'),
            ('advance_pct', 'Advance %'), ('balance_days', 'Baaki: show se kitne din pehle'), ('morning_time', 'Subah ka note (HH:MM)'),
            ('terms', 'Cancellation / shartein'), ('rules', 'Aapke niyam'),
          ], initial: {for (final k in st.keys) if (st[k] is String || st[k] is num) k: _s(st[k])}, ok: 'Save');
          if (f == null) return;
          final body = <String, dynamic>{...f};
          for (final k in const ['commission_pct', 'royalty_pct', 'same_city_gap', 'travel_gap', 'hold_hours', 'advance_pct', 'balance_days']) {
            if (f[k] != null) body[k] = _n(f[k]);
          }
          await _run('PUT', '/api/artistmgr/settings', body);
        },
      ),
      const SizedBox(height: 12),
      const Text(
          'Fee, tareekh, royalty, ISRC kabhi andaaze se nahi. Promoter / artist ko kuch bhi aapki haan ke baad hi; message aap bhejti hain. '
          'Hoola paise nahi leta / deta.',
          style: TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Gigs', 'Artists', 'Release', 'Niyam'];
    return Scaffold(
      appBar: AppBar(title: Text('${widget.app.aName} · Artist manager')),
      body: _d == null
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
                child: Row(children: [
                  for (final (i, t) in tabs.indexed)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
                    ),
                ]),
              ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: _load,
                  child: switch (_tab) { 0 => _aaj(), 1 => _gigs(), 2 => _artists(), 3 => _releases(), _ => _niyam() },
                ),
              ),
            ]),
    );
  }
}

/// One gig: when / where, money (fee, advance, paid, TDS, commission, net), rider, cards, and her actions.
class ArtistmgrGigPage extends StatefulWidget {
  const ArtistmgrGigPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<ArtistmgrGigPage> createState() => _ArtistmgrGigPageState();
}

class _ArtistmgrGigPageState extends State<ArtistmgrGigPage> {
  Map<String, dynamic>? _g;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/artistmgr/gigs/${widget.ref}'));
      if (mounted) setState(() => _g = _m(r['gig']).isNotEmpty ? _m(r['gig']) : r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _act(String what, [Map<String, dynamic>? body]) async {
    await _call(context, widget.app, 'POST', '/api/artistmgr/gigs/${widget.ref}/$what', body ?? {});
    await _load();
  }

  Future<void> _ask(String what, String title, List<(String, String)> fields, {Set<String> nums = const {}}) async {
    final f = await _form(context, title, fields);
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in nums) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _act(what, body);
  }

  @override
  Widget build(BuildContext context) {
    final g = _g;
    if (g == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final money = _m(g['money']), rider = _m(g['rider']);
    final st = _s(g['status']);
    String rs(dynamic v) => v == null ? '[?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';
    return Scaffold(
      appBar: AppBar(title: Text('${_s(g['number'])} · ${_s(g['artist'])}')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(_s(g['event']).isEmpty ? 'Show' : _s(g['event']), style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(g['status_label']).isEmpty ? st : _s(g['status_label'])),
            ]),
            Text('${_s(g['day']).isEmpty ? 'tareekh?' : _s(g['day'])} ${_s(g['start'])}-${_s(g['end'])} · ${_s(g['city'])} ${_s(g['venue'])}'),
            Text('Promoter: ${_s(g['promoter'])} ${_s(g['phone'])}', style: const TextStyle(fontSize: 12.5)),
            if (_strs(g['blanks']).isNotEmpty)
              Text('Abhi nahi pata: ${_strs(g['blanks']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.accent)),
          ])),
          const SizedBox(height: 10),
          const Caption('PAISA'),
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Fee ${_s(g['fee_text'])} · advance ${rs(money['advance'])} · baaki ${rs(money['balance'])} (${_s(money['balance_due'])} tak)'),
            Text('Mila ${rs(money['received'])} · TDS ${rs(money['tds'])} · promoter se baaki ${rs(money['due_from_promoter'])}'),
            Text('Commission ${rs(money['commission'])} · kharcha ${rs(money['expenses_recover'])} · artist ko ${rs(money['net_to_artist'])}'),
            if (_s(g['tds_note']).isNotEmpty) Text(_s(g['tds_note']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
          ])),
          if (rider.isNotEmpty) ...[
            const SizedBox(height: 10),
            const Caption('RIDER'),
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              for (final e in rider.entries) Text('${e.key}: ${_strs(e.value).join(', ')}', style: const TextStyle(fontSize: 12.5)),
            ])),
          ],
          const SizedBox(height: 10),
          for (final c in _list(g['cards']))
            Padding(padding: const EdgeInsets.only(bottom: 10), child: ArtistmgrCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
          const Caption('AAGE KYA'),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (st == 'enquiry') GlassButton(label: 'Hold karo', height: 40, onTap: () => _act('hold')),
            if (st == 'enquiry' || st == 'hold') GlassButton(label: 'Jawab (card)', height: 40, onTap: () => _ask('reply', 'Promoter ko jawab', const [('text', 'Apna text (khaali = Hoola banaye)')])),
            if (st == 'hold') ...[
              GlassButton(label: 'Pakka (card)', height: 40, onTap: () => _act('confirm')),
              GlassButton(label: 'Hold chhodo', height: 40, onTap: () => _act('release')),
            ],
            if (st == 'hold' || st == 'confirmed') GlassButton(label: 'Contract (card)', height: 40, onTap: () => _act('contract')),
            if (st == 'confirmed' || st == 'done') ...[
              GlassButton(label: 'Invoice (card)', height: 40, onTap: () => _act('invoice')),
              GlassButton(label: 'Paise maango (card)', height: 40, onTap: () => _ask('pay', 'Kaunsa paisa?', const [('stage', 'advance / balance'), ('amount', 'Ya amount (₹)')], nums: {'amount'})),
              GlassButton(label: 'Paise mile', height: 40, onTap: () => _ask('paid', 'Paise mile', const [('amount', 'Kitne (₹)'), ('mode', 'upi / cash / bank / cheque'), ('ref', 'UTR / ref')], nums: {'amount'})),
              GlassButton(label: 'TDS kata', height: 40, onTap: () => _ask('tds', 'Promoter ne TDS kaata', const [('amount', 'Kitna (₹)')], nums: {'amount'})),
              GlassButton(label: 'Kharcha', height: 40, onTap: () => _ask('expense', 'Kharcha', const [('what', 'Kya'), ('amount', 'Kitna (₹)'), ('paid_by', 'manager / artist / promoter')], nums: {'amount'})),
              GlassButton(label: 'Travel', height: 40, onTap: () => _ask('travel', 'Kahan se?', const [('origin', 'Shehar')])),
            ],
            if (st == 'confirmed') GlassButton(label: 'Show ho gaya', height: 40, onTap: () => _act('done')),
            GlassButton(label: 'Message (card)', height: 40, onTap: () => _ask('message', 'Message', const [('to', 'promoter / artist / member ka naam'), ('text', 'Text')])),
            if (st != 'done' && st != 'cancelled')
              GlassButton(label: 'Radd', height: 40, onTap: () => _ask('cancel', 'Radd kyun?', const [('reason', 'Wajah'), ('by', 'promoter / artist')])),
            GlassButton(
                label: 'Contract PDF (draft)',
                icon: Icons.picture_as_pdf_rounded,
                height: 40,
                onTap: () => Native.openExternal(url: widget.app.api!.absolute('/api/artistmgr/gigs/${widget.ref}/contract.pdf'))),
          ]),
          const SizedBox(height: 12),
          if (_list(g['log']).isNotEmpty) ...[
            const Caption('LOG'),
            for (final l in _list(g['log']).reversed) Text('• ${_s(l['at'])} ${_s(l['what'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
          ],
        ]),
      ),
    );
  }
}

/// One artist: members / splits, registrations, gigs, releases, ledger, blocked days, payout card.
class ArtistmgrArtistPage extends StatefulWidget {
  const ArtistmgrArtistPage({super.key, required this.app, required this.id, this.onEdit});
  final Santosh app;
  final String id;
  final Future<void> Function([Map<String, dynamic>?])? onEdit;
  @override
  State<ArtistmgrArtistPage> createState() => _ArtistmgrArtistPageState();
}

class _ArtistmgrArtistPageState extends State<ArtistmgrArtistPage> {
  Map<String, dynamic>? _a;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/artistmgr/artists/${widget.id}'));
      if (mounted) setState(() => _a = _m(r['artist']).isNotEmpty ? {...r, ..._m(r['artist'])} : r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _post(String path, [Map<String, dynamic>? body]) async {
    await _call(context, widget.app, 'POST', path, body ?? {});
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final a = _a;
    if (a == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      appBar: AppBar(title: Text(_s(a['name']))),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(a['kind_label'])} · ${_s(a['genre'])} · ${_s(a['city'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            if (_s(a['min_fee']).isNotEmpty) Text('Kam se kam fee ₹${_s(a['min_fee'])}'),
            for (final m in _list(a['members']))
              Text('• ${_s(m['name'])} ${_s(m['role'])}${_s(m['split_pct']).isEmpty ? '' : ' · ${_s(m['split_pct'])}%'}',
                  style: const TextStyle(fontSize: 12.5)),
          ])),
          const SizedBox(height: 10),
          const Caption('ROYALTY REGISTRATIONS'),
          for (final r in _list(a['regs']))
            Glass(
              child: Row(children: [
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(r['label']), style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text(_s(r['why']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
                  if (_s(r['ref']).isNotEmpty) Text('Ref ${_s(r['ref'])}', style: const TextStyle(fontSize: 12)),
                ])),
                PopupMenuButton<String>(
                  onSelected: (v) => _post('/api/artistmgr/artists/${widget.id}/regs', {'key': r['key'], 'status': v}),
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'none', child: Text('Nahi hua')),
                    PopupMenuItem(value: 'applied', child: Text('Apply kiya')),
                    PopupMenuItem(value: 'done', child: Text('Ho gaya')),
                    PopupMenuItem(value: 'na', child: Text('Lagu nahi')),
                  ],
                  child: Pill(_s(r['status'])),
                ),
              ]),
            ),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (widget.onEdit != null)
              GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: () async {
                await widget.onEdit!(a);
                await _load();
              }),
            GlassButton(label: 'Din band karo', icon: Icons.event_busy_rounded, height: 40, onTap: () async {
              final f = await _form(context, 'Artist kab free nahi?', const [('from', 'Se (YYYY-MM-DD)'), ('to', 'Tak (YYYY-MM-DD)'), ('note', 'Kyun')]);
              if (f != null) await _post('/api/artistmgr/artists/${widget.id}/block', f);
            }),
            GlassButton(label: 'Payout statement (card)', icon: Icons.payments_rounded, height: 40,
                onTap: () => _post('/api/artistmgr/artists/${widget.id}/payout')),
            GlassButton(label: 'Message (card)', icon: Icons.chat_rounded, height: 40, onTap: () async {
              final f = await _form(context, 'Message', const [('to', 'artist / member ka naam'), ('text', 'Text')]);
              if (f != null) await _post('/api/artistmgr/artists/${widget.id}/message', f);
            }),
            GlassButton(label: 'Bhool jao (DPDP)', icon: Icons.delete_outline_rounded, height: 40, onTap: () async {
              final ok = await showDialog<bool>(
                  context: context,
                  builder: (d) => AlertDialog(
                        title: const Text('Is artist ki personal jaankari mitayein?'),
                        content: const Text('Naam / phone / members hat jayenge; hisaab ke number rahenge.'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
                          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Mitao')),
                        ],
                      ));
              if (ok == true) await _post('/api/artistmgr/artists/${widget.id}/forget');
            }),
          ]),
          for (final b in _list(a['blocks']))
            ListTile(
              dense: true,
              title: Text('${_s(b['from'])} – ${_s(b['to'])} ${_s(b['note'])}'),
              trailing: IconButton(
                  icon: const Icon(Icons.close_rounded),
                  onPressed: () async {
                    await _call(context, widget.app, 'DELETE', '/api/artistmgr/blocks/${_s(b['id'])}');
                    await _load();
                  }),
            ),
          if (_list(a['gigs']).isNotEmpty) ...[
            const SizedBox(height: 10),
            const Caption('GIGS'),
            for (final g in _list(a['gigs']))
              _gigTile(context, g, () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => ArtistmgrGigPage(app: widget.app, ref: _s(g['number']))))
                  .then((_) => _load())),
          ],
        ]),
      ),
    );
  }
}

/// One release: tracks with ISRC, plan with dates, problems, final metadata card and steps.
class ArtistmgrReleasePage extends StatefulWidget {
  const ArtistmgrReleasePage({super.key, required this.app, required this.ref, this.onEdit});
  final Santosh app;
  final String ref;
  final Future<void> Function([Map<String, dynamic>?])? onEdit;
  @override
  State<ArtistmgrReleasePage> createState() => _ArtistmgrReleasePageState();
}

class _ArtistmgrReleasePageState extends State<ArtistmgrReleasePage> {
  Map<String, dynamic>? _r;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/artistmgr/releases/${widget.ref}'));
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _post(String path, [Map<String, dynamic>? body]) async {
    await _call(context, widget.app, 'POST', path, body ?? {});
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    if (r == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      appBar: AppBar(title: Text('${_s(r['number'])} · ${_s(r['title'])}')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(r['artist'])} · ${_s(r['kind'])} · ${_s(r['day'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text('Distributor ${_s(r['distributor']).isEmpty ? '?' : _s(r['distributor'])} · UPC ${_s(r['upc']).isEmpty ? '?' : _s(r['upc'])}'),
            Pill(_s(r['status'])),
          ])),
          const SizedBox(height: 10),
          const Caption('GAANE'),
          for (final t in _list(r['tracks']))
            Text('• ${_s(t['title'])} · ${_s(t['isrc']).isEmpty ? 'ISRC?' : _s(t['isrc'])}', style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 10),
          const Caption('PLAN'),
          for (final p in _list(r['plan']))
            ListTile(
              dense: true,
              leading: Icon(_s(p['done']).isNotEmpty ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                  color: p['late'] == true ? C.accent : null),
              title: Text(_s(p['what'])),
              subtitle: Text(_s(p['by'])),
              trailing: _s(p['done']).isEmpty && r['final'] == true
                  ? TextButton(onPressed: () => _post('/api/artistmgr/releases/${widget.ref}/step', {'step': p['key']}), child: const Text('Ho gaya'))
                  : null,
            ),
          if (_strs(r['problems']).isNotEmpty) ...[
            const Caption('BAAKI'),
            for (final x in _strs(r['problems'])) Text('• $x', style: const TextStyle(color: C.accent)),
          ],
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (widget.onEdit != null)
              GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: () async {
                await widget.onEdit!(r);
                await _load();
              }),
            if (r['final'] != true && _strs(r['problems']).isEmpty)
              GradientButton(label: 'Metadata final (card)', height: 42, onTap: () => _post('/api/artistmgr/releases/${widget.ref}/final')),
          ]),
        ]),
      ),
    );
  }
}

/// artistmgr_card: a step waiting for HER tap (reply / contract / confirm / invoice / pay / payout / message / release).
/// The payout card needs her fingerprint once a phone key is set up (428 -> /cards/{id}/challenge -> sign -> resend).
class ArtistmgrCardCard extends StatefulWidget {
  const ArtistmgrCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ArtistmgrCardCard> createState() => _ArtistmgrCardCardState();
}

class _ArtistmgrCardCardState extends State<ArtistmgrCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _res = _m(_c['result']);

  @override
  void didUpdateWidget(covariant ArtistmgrCardCard old) {
    super.didUpdateWidget(old);
    final c = _m(widget.data['card']);
    if (c.isNotEmpty && (_s(c['status']) != _s(_c['status']) || _s(c['hash']) != _s(_c['hash']))) {
      _c = c;
      _res = _m(c['result']);
    }
  }

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/artistmgr/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Artist payout' : _s(show['title']),
        [show['amount'] ?? show['total_text'], show['payee'] ?? show['artist']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
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
        r = await widget.app.api!.call('POST', '/api/artistmgr/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/artistmgr/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          if (_m(m['card']).isNotEmpty) _c = _m(m['card']);
          _res = {..._res, ...m};
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
    final inv = _m(sh['invoice']);
    final amount = [_s(sh['amount_text']), _s(sh['fee_text'])].firstWhere((x) => x.isNotEmpty && x != '[?]', orElse: () => '');
    final tag = [_s(sh['gig']), _s(sh['release']), _s(sh['artist'])].where((x) => x.isNotEmpty).join(' · ');
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'reply' => Icons.reply_rounded, 'contract' => Icons.article_rounded, 'confirm' => Icons.verified_rounded,
            'invoice' => Icons.receipt_long_rounded, 'pay' => Icons.currency_rupee_rounded, 'payout' => Icons.payments_rounded,
            'release' => Icons.album_rounded, _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])}${tag.isEmpty ? '' : ' · $tag'}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        if (_s(sh['day']).isNotEmpty || _s(sh['city']).isNotEmpty)
          Text('${_s(sh['promoter'])} · ${_s(sh['day'])} ${_s(sh['start'])} · ${_s(sh['city'])} ${_s(sh['venue'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (kind == 'contract') Text('Advance ${_s(sh['advance_text'])} · baaki ${_s(sh['balance_text'])} (${_s(sh['balance_due'])} tak)', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'invoice' && inv.isNotEmpty) Text('Invoice ${_s(inv['number'])} · kul ${_s(inv['total_text'])}', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'payout') ...[
          Text('Kul ${_s(sh['total_text'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final x in _list(sh['splits']))
            Text('• ${_s(x['name'])}${_s(x['split_pct']).isEmpty ? '' : ' (${_s(x['split_pct'])}%)'}: ₹${_s(x['amount'])}', style: const TextStyle(fontSize: 12.5)),
        ],
        if (kind == 'release') ...[
          for (final t in _list(sh['tracks'])) Text('• ${_s(t['title'])} · ${_s(t['isrc'])}', style: const TextStyle(fontSize: 12.5)),
          for (final p in _strs(sh['problems'])) Text('• $p', style: const TextStyle(fontSize: 12, color: C.accent)),
        ],
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        if (_s(c['reason']).isNotEmpty) Text('Wajah: ${_s(c['reason'])}', style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Haan (fingerprint)' : 'Haan', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_m(_res['draft']).isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_m(_res['draft']))],
        for (final d in _list(_res['drafts'])) ...[const SizedBox(height: 6), _draftButtons(d, name: _s(d['name']))],
        const Text('Hoola khud kuch nahi bhejta, paise nahi leta / deta: message aap bhejti hain.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// artistmgr_alert / artistmgr_day / artistmgr_gig: notes (hold ending, show tomorrow, balance due, release steps, morning note).
class ArtistmgrNoteCard extends StatelessWidget {
  const ArtistmgrNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final gig = _s(data['gig'] is Map ? _m(data['gig'])['number'] : data['gig']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.mic_external_on_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
          if (gig.isNotEmpty)
            TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArtistmgrGigPage(app: app, ref: gig))),
                child: Text('$gig kholo')),
        ])),
      ]),
    );
  }
}
