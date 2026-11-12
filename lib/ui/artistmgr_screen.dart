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
import 'desk/desk_kit.dart';
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
                maxLines: (k == 'text' || k == 'terms' || k == 'notes' || k == 'rules' || k == 'members') ? 4 : 1),
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

Widget _draftButtons(Map<String, dynamic> d, {String name = ''}) {
  final wa = _s(d['wa']), sms = _s(d['sms']);
  if (wa.isEmpty && sms.isEmpty) return const SizedBox.shrink();
  final who = name.isEmpty ? '' : ' · $name';
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft$who', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft$who', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (_s(d['upi']).isNotEmpty) const Pill('UPI link of your UPI ID'),
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
              Text('${_s(g['day']).isEmpty ? 'date?' : _s(g['day'])} ${_s(g['start'])} · ${_s(g['city'])} ${_s(g['venue'])}',
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
    final f = await _form(context, 'New offer', const [
      ('text', 'Promoter\'s message (paste)'), ('artist', 'Artist'), ('day', 'Date (YYYY-MM-DD)'), ('start', 'Start (HH:MM)'),
      ('end', 'End (HH:MM)'), ('city', 'City'), ('venue', 'Venue'), ('fee', 'Fee (₹)'), ('promoter', 'Promoter'), ('phone', 'Promoter phone'),
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
      if (_list(_d?['cards']).isNotEmpty) const Caption('WAITING FOR YOUR APPROVAL'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: ArtistmgrCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('today', 'TODAY\'S SHOWS'), ('tomorrow', 'TOMORROW\'S SHOWS'), ('holds', 'HOLD EXPIRES IN 24 HOURS')])
        if (_list(day[k]).isNotEmpty) ...[
          Caption(label),
          for (final g in _list(day[k])) _gigTile(context, g, () => _openGig(_s(g['number']))),
          const SizedBox(height: 8),
        ],
      for (final (k, label) in const [('balances', 'PAYMENTS PENDING'), ('unsettled', 'SETTLEMENT PENDING'), ('releases', 'RELEASE TASKS'),
        ('regs_missing', 'REGISTRATION PENDING')])
        if (_strs(day[k]).isNotEmpty) ...[Caption(label), for (final x in _strs(day[k])) Text('• $x'), const SizedBox(height: 8)],
      if (day['no_commission'] == true)
        const Text('Commission % is not in Rules: the settlement will have no commission line.', style: TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  Widget _gigs() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New offer / gig', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _offer),
        const SizedBox(height: 12),
        if (_list(_d?['gigs']).isEmpty) const Text('No upcoming gigs.', style: TextStyle(color: C.muted)),
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
    final f = await _form(context, a == null ? 'New artist' : 'Edit artist', const [
      ('name', 'Name'), ('kind', 'Type (singer / band / dj / instrumentalist / composer / lyricist / classical / folk)'), ('genre', 'Genre'),
      ('city', 'City'), ('phone', 'Phone'), ('min_fee', 'Minimum fee (₹)'), ('members', 'Members: name, role, phone, split % (one per line)'),
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
        GradientButton(label: 'New artist', icon: Icons.person_add_alt_1_rounded, height: 44, onTap: _busy ? null : () => _artistForm()),
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
                        final f = await _form(context, 'Payout sent?', const [('ref', 'UTR / ref')], ok: 'Yes, sent');
                        if (f != null) await _run('POST', '/api/artistmgr/payouts/${_s(p['id'])}/paid', f);
                      },
                      child: const Text('Sent')),
              ]),
            ),
        ],
      ]);

  Future<void> _releaseForm([Map<String, dynamic>? r]) async {
    final f = await _form(context, r == null ? 'New release' : 'Edit release', const [
      ('artist', 'Artist'), ('title', 'Name'), ('kind', 'single / ep / album'), ('day', 'Release date (YYYY-MM-DD)'),
      ('distributor', 'Distributor'), ('upc', 'UPC (given by the distributor)'), ('tracks', 'Songs: title | ISRC (one per line)'),
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
        GradientButton(label: 'New release', icon: Icons.album_rounded, height: 44, onTap: _busy ? null : () => _releaseForm()),
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
        Text(_s(st['agency']).isEmpty ? 'No agency name' : _s(st['agency']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('UPI ${_s(st['upi_id']).isEmpty ? '?' : _s(st['upi_id'])} · commission ${_s(st['commission_pct']).isEmpty ? '?' : '${_s(st['commission_pct'])}%'}'),
        Text('Same city gap ${_s(st['same_city_gap'])} min · different city ${_s(st['travel_gap'])} min · hold ${_s(st['hold_hours'])} hours'),
        Text('Advance ${_s(st['advance_pct'])}% · balance ${_s(st['balance_days'])} days before the show'),
        for (final d in _list(st['distributors']))
          Text('• ${_s(d['name'])}: ${_s(d['share_pct'])}% · ${_s(d['lead_days'])} days before', style: const TextStyle(fontSize: 12.5)),
        if (_s(st['terms']).isNotEmpty) Text('Terms: ${_s(st['terms'])}', style: const TextStyle(fontSize: 12.5)),
      ])),
      const SizedBox(height: 10),
      GlassButton(
        label: 'Edit rules',
        icon: Icons.tune_rounded,
        height: 44,
        onTap: () async {
          final f = await _form(context, 'Rules', const [
            ('agency', 'Agency'), ('gstin', 'GSTIN'), ('upi_id', 'UPI ID'), ('commission_pct', 'Commission %'), ('royalty_pct', 'Royalty commission %'),
            ('same_city_gap', 'Same city gap (min)'), ('travel_gap', 'Different city gap (min)'), ('hold_hours', 'Hold hours'),
            ('advance_pct', 'Advance %'), ('balance_days', 'Balance: how many days before the show'), ('morning_time', 'Morning note (HH:MM)'),
            ('terms', 'Cancellation / terms'), ('rules', 'Your rules'),
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
          'Fee, date, royalty, ISRC are never guessed. Anything to a promoter / artist goes only after your approval; you send the messages.'
          'Hoola does not take or give money.',
          style: TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    // v0.869 R8 wave 2: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'Artist manager',
      tabs: const ['Today', 'Gigs', 'Artists', 'Release', 'Rules'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      onRefresh: _load,
      body: () => switch (_tab) { 0 => _aaj(), 1 => _gigs(), 2 => _artists(), 3 => _releases(), _ => _niyam() },
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
            Text('${_s(g['day']).isEmpty ? 'date?' : _s(g['day'])} ${_s(g['start'])}-${_s(g['end'])} · ${_s(g['city'])} ${_s(g['venue'])}'),
            Text('Promoter: ${_s(g['promoter'])} ${_s(g['phone'])}', style: const TextStyle(fontSize: 12.5)),
            if (_strs(g['blanks']).isNotEmpty)
              Text('Not known yet: ${_strs(g['blanks']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.accent)),
          ])),
          const SizedBox(height: 10),
          const Caption('MONEY'),
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Fee ${_s(g['fee_text'])} · advance ${rs(money['advance'])} · balance ${rs(money['balance'])} (until ${_s(money['balance_due'])})'),
            Text('Received ${rs(money['received'])} · TDS ${rs(money['tds'])} · due from promoter ${rs(money['due_from_promoter'])}'),
            Text('Commission ${rs(money['commission'])} · expenses ${rs(money['expenses_recover'])} · to artist ${rs(money['net_to_artist'])}'),
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
          const Caption('WHAT NEXT'),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (st == 'enquiry') GlassButton(label: 'Hold', height: 40, onTap: () => _act('hold')),
            if (st == 'enquiry' || st == 'hold') GlassButton(label: 'Reply (card)', height: 40, onTap: () => _ask('reply', 'Reply to promoter', const [('text', 'Your own text (empty = Hoola writes)')])),
            if (st == 'hold') ...[
              GlassButton(label: 'Confirm (card)', height: 40, onTap: () => _act('confirm')),
              GlassButton(label: 'Release hold', height: 40, onTap: () => _act('release')),
            ],
            if (st == 'hold' || st == 'confirmed') GlassButton(label: 'Contract (card)', height: 40, onTap: () => _act('contract')),
            if (st == 'confirmed' || st == 'done') ...[
              GlassButton(label: 'Invoice (card)', height: 40, onTap: () => _act('invoice')),
              GlassButton(label: 'Ask for money (card)', height: 40, onTap: () => _ask('pay', 'Which payment?', const [('stage', 'advance / balance'), ('amount', 'Ya amount (₹)')], nums: {'amount'})),
              GlassButton(label: 'Money received', height: 40, onTap: () => _ask('paid', 'Money received', const [('amount', 'How much (₹)'), ('mode', 'upi / cash / bank / cheque'), ('ref', 'UTR / ref')], nums: {'amount'})),
              GlassButton(label: 'TDS deducted', height: 40, onTap: () => _ask('tds', 'Promoter deducted TDS', const [('amount', 'How much (₹)')], nums: {'amount'})),
              GlassButton(label: 'Expense', height: 40, onTap: () => _ask('expense', 'Expense', const [('what', 'What'), ('amount', 'How much (₹)'), ('paid_by', 'manager / artist / promoter')], nums: {'amount'})),
              GlassButton(label: 'Travel', height: 40, onTap: () => _ask('travel', 'From where?', const [('origin', 'City')])),
            ],
            if (st == 'confirmed') GlassButton(label: 'Show done', height: 40, onTap: () => _act('done')),
            GlassButton(label: 'Message (card)', height: 40, onTap: () => _ask('message', 'Message', const [('to', 'name of promoter / artist / member'), ('text', 'Text')])),
            if (st != 'done' && st != 'cancelled')
              GlassButton(label: 'Cancel', height: 40, onTap: () => _ask('cancel', 'Why cancel?', const [('reason', 'Reason'), ('by', 'promoter / artist')])),
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
            if (_s(a['min_fee']).isNotEmpty) Text('Minimum fee ₹${_s(a['min_fee'])}'),
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
                    PopupMenuItem(value: 'none', child: Text('Did not happen')),
                    PopupMenuItem(value: 'applied', child: Text('Applied')),
                    PopupMenuItem(value: 'done', child: Text('Done')),
                    PopupMenuItem(value: 'na', child: Text('Not applicable')),
                  ],
                  child: Pill(_s(r['status'])),
                ),
              ]),
            ),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (widget.onEdit != null)
              GlassButton(label: 'Edit', icon: Icons.edit_rounded, height: 40, onTap: () async {
                await widget.onEdit!(a);
                await _load();
              }),
            GlassButton(label: 'Close the day', icon: Icons.event_busy_rounded, height: 40, onTap: () async {
              final f = await _form(context, 'When is the artist not free?', const [('from', 'Se (YYYY-MM-DD)'), ('to', 'Until (YYYY-MM-DD)'), ('note', 'Why')]);
              if (f != null) await _post('/api/artistmgr/artists/${widget.id}/block', f);
            }),
            GlassButton(label: 'Payout statement (card)', icon: Icons.payments_rounded, height: 40,
                onTap: () => _post('/api/artistmgr/artists/${widget.id}/payout')),
            GlassButton(label: 'Message (card)', icon: Icons.chat_rounded, height: 40, onTap: () async {
              final f = await _form(context, 'Message', const [('to', 'name of artist / member'), ('text', 'Text')]);
              if (f != null) await _post('/api/artistmgr/artists/${widget.id}/message', f);
            }),
            GlassButton(label: 'Forget me (DPDP)', icon: Icons.delete_outline_rounded, height: 40, onTap: () async {
              final ok = await showDialog<bool>(
                  context: context,
                  builder: (d) => AlertDialog(
                        title: const Text('Delete this artist\'s personal information?'),
                        content: const Text('Name / phone / members will be removed; the accounting numbers stay.'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Delete')),
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
          const Caption('SONGS'),
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
                  ? TextButton(onPressed: () => _post('/api/artistmgr/releases/${widget.ref}/step', {'step': p['key']}), child: const Text('Done'))
                  : null,
            ),
          if (_strs(r['problems']).isNotEmpty) ...[
            const Caption('PENDING'),
            for (final x in _strs(r['problems'])) Text('• $x', style: const TextStyle(color: C.accent)),
          ],
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (widget.onEdit != null)
              GlassButton(label: 'Edit', icon: Icons.edit_rounded, height: 40, onTap: () async {
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
        'cancelled' => 'No fingerprint given, so it was not approved.',
        'key_invalidated' => 'A new fingerprint was added to the phone: re-link this phone in Profile > Fingerprint approval.',
        _ => 'Could not approve with fingerprint (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not?', const [('reason', 'Reason (optional)')], ok: 'No');
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
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'stale', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        if (_s(sh['day']).isNotEmpty || _s(sh['city']).isNotEmpty)
          Text('${_s(sh['promoter'])} · ${_s(sh['day'])} ${_s(sh['start'])} · ${_s(sh['city'])} ${_s(sh['venue'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (kind == 'contract') Text('Advance ${_s(sh['advance_text'])} · balance ${_s(sh['balance_text'])} (until ${_s(sh['balance_due'])})', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'invoice' && inv.isNotEmpty) Text('Invoice ${_s(inv['number'])} · total ${_s(inv['total_text'])}', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'payout') ...[
          Text('Total ${_s(sh['total_text'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final x in _list(sh['splits']))
            Text('• ${_s(x['name'])}${_s(x['split_pct']).isEmpty ? '' : ' (${_s(x['split_pct'])}%)'}: ₹${_s(x['amount'])}', style: const TextStyle(fontSize: 12.5)),
        ],
        if (kind == 'release') ...[
          for (final t in _list(sh['tracks'])) Text('• ${_s(t['title'])} · ${_s(t['isrc'])}', style: const TextStyle(fontSize: 12.5)),
          for (final p in _strs(sh['problems'])) Text('• $p', style: const TextStyle(fontSize: 12, color: C.accent)),
        ],
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        if (_s(c['reason']).isNotEmpty) Text('Reason: ${_s(c['reason'])}', style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Yes (fingerprint)' : 'Yes', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_m(_res['draft']).isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_m(_res['draft']))],
        for (final d in _list(_res['drafts'])) ...[const SizedBox(height: 6), _draftButtons(d, name: _s(d['name']))],
        const Text('Hoola does not send anything or take or give money: you send the messages.',
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
                child: Text('Open $gig')),
        ])),
      ]),
    );
  }
}
