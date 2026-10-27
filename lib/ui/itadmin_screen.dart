/// Profile > IT Admin Sahayak: Hoola as the office's IT administrator.
/// Aaj (renewals, free seats, cards waiting for her Haan, checklists, review) · Licence (subscriptions, seats, renewal) ·
/// Log (people + who has which access; joiner / mover / leaver) · Guides (how-to for staff, screenshots, staff questions) ·
/// Admin (Google Workspace / Microsoft 365 read-only link, access review, good practice, niyam).
/// Any change of access or settings happens ONLY after her tap on the card. Hoola never asks for or keeps a password.
library;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

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

String _rs(dynamic v) {
  if (v == null) return '';
  final n = (v is num) ? v : num.tryParse('$v');
  if (n == null) return '';
  return '₹${n.round()}';
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}, Set<String> hidden = const {}}) async {
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
                obscureText: hidden.contains(k),
                decoration: InputDecoration(labelText: label),
                maxLines: hidden.contains(k) ? 1 : (k == 'words' || k == 'text' ? 5 : 1)),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  final out = {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
  for (final e in c.values) {
    e.dispose();
  }
  return res == true ? out : null;
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

Widget _h(String t) => Padding(
    padding: const EdgeInsets.only(top: 10, bottom: 6), child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)));

Widget _muted(String t) => Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(t, style: const TextStyle(color: C.muted, fontSize: 12.5)));

class ItadminScreen extends StatefulWidget {
  const ItadminScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ItadminScreen> createState() => _ItadminScreenState();
}

class _ItadminScreenState extends State<ItadminScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/itadmin'));
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

  // ---------------- Aaj
  Widget _today() {
    final day = _m(_d?['day']);
    final lines = (day['lines'] as List?)?.map(_s).toList() ?? const <String>[];
    final waiting = _list(day['waiting']);
    final approved = _list(day['approved']);
    final cls = _list(day['checklists']);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aaj ka IT admin', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          if (lines.isEmpty) _muted('Sab theek: koi renewal, card ya checklist baaki nahi.'),
          for (final l in lines) Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• $l', style: const TextStyle(fontSize: 13))),
        ]),
      ),
      if (waiting.isNotEmpty) _h('Aapki haan chahiye (${waiting.length})'),
      for (final c in waiting)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
      if (approved.isNotEmpty) _h('Haan di, console mein karna baaki'),
      for (final c in approved)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
      if (cls.isNotEmpty) _h('Checklists'),
      for (final c in cls)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminChecklistCard(app: widget.app, data: {'checklist': c, 'person': c['person']}, onDone: _load)),
      if (day['review_due'] == true)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: GlassButton(label: 'Access review shuru karo', icon: Icons.fact_check_rounded, onTap: () => _run('POST', '/api/itadmin/reviews')),
        ),
    ]);
  }

  // ---------------- Licence
  Future<void> _licenceForm([Map<String, dynamic>? l]) async {
    final f = await _form(context, l == null ? 'Naya licence / subscription' : 'Badlo: ${_s(l['name'])}', const [
      ('name', 'Naam (jaise Microsoft 365 Business Basic)'),
      ('vendor', 'Kis se (vendor / partner)'),
      ('seats_bought', 'Kitni seats li'),
      ('seats_used', 'Kitni use mein'),
      ('cost', 'Kharcha ₹ (aapka number)'),
      ('cost_per', 'month / year / once'),
      ('renews_on', 'Renewal tareekh (YYYY-MM-DD)'),
      ('owner', 'Kaun dekhta / bharta hai'),
      ('login_with', 'Kis account se manage (password nahi)'),
    ], initial: {
      if (l != null) for (final k in ['name', 'vendor', 'seats_bought', 'seats_used', 'cost', 'cost_per', 'renews_on', 'owner', 'login_with'])
        if (_s(l[k]).isNotEmpty) k: _s(l[k]),
    }, ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['seats_bought', 'seats_used']) {
      if (body[k] != null) body[k] = int.tryParse('${body[k]}');
    }
    if (body['cost'] != null) body['cost'] = double.tryParse('${body['cost']}');
    if (!mounted) return;
    final perSeat = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(content: const Text('Kharcha har seat ka hai?'), actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi, poora')),
              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, per seat')),
            ]));
    if (perSeat != null) body['per_seat'] = perSeat;
    if (l == null) {
      await _run('POST', '/api/itadmin/licences', body);
    } else {
      await _run('PATCH', '/api/itadmin/licences/${_s(l['id'])}', body);
    }
  }

  Widget _licences() {
    final rows = _list(_d?['licences']);
    final save = _m(_m(_d?['day'])['renewals'])['save_year'];
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (save is num && save > 0)
        Glass(child: Text('Khaali seats hata kar ~${_rs(save)} saal ke bach sakte hain.', style: const TextStyle(color: C.ok, fontWeight: FontWeight.w700))),
      const SizedBox(height: 8),
      GlassButton(label: 'Naya licence', icon: Icons.add_rounded, onTap: _busy ? null : () => _licenceForm()),
      const SizedBox(height: 8),
      if (rows.isEmpty) _muted('Abhi koi licence nahi. M365 / Workspace jodne par seats khud aa jayengi (Admin tab).'),
      for (final l in rows) _licTile(l),
    ]);
  }

  Widget _licTile(Map<String, dynamic> l) {
    final days = l['days_left'];
    final w = _m(l['waste']);
    final late = days is num && days < 0;
    final soon = days is num && days <= 30;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _licenceForm(l),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: late ? C.bad : (soon ? C.warn : null),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Pill(_s(l['kind_label'])),
              const SizedBox(width: 6),
              Expanded(child: Text('${_s(l['number'])} · ${_s(l['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              if (_s(l['source']) != 'manual') Pill(_s(l['source']), fg: C.teal),
            ]),
            const SizedBox(height: 4),
            Text(
                [
                  if (l['seats_bought'] != null || l['seats_used'] != null) 'Seats ${_s(l['seats_used'] ?? '?')}/${_s(l['seats_bought'] ?? '?')}',
                  if (l['cost'] != null) '${_rs(l['cost'])}/${_s(l['cost_per'])}${l['per_seat'] == true ? ' per seat' : ''}',
                  if (_s(l['renews_on']).isNotEmpty) 'Renewal ${_s(l['renews_on'])} (${_s(days)} din)',
                  l['auto_renew'] == true ? 'auto-renew ON' : (l['auto_renew'] == false ? 'auto-renew OFF' : 'auto-renew ?'),
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (w.isNotEmpty)
              Text('${_s(w['free'])} seat khaali${w['rupees_year'] != null ? ' · ~${_rs(w['rupees_year'])}/saal' : ''}',
                  style: const TextStyle(color: C.ok, fontSize: 12.5)),
            Row(children: [
              TextButton(
                  onPressed: () async {
                    final f = await _form(context, 'Renew kar diya', const [('renews_on', 'Agli tareekh (khaali = +1 saal)'), ('cost', 'Naya kharcha ₹')], ok: 'Save');
                    if (f == null) return;
                    await _run('POST', '/api/itadmin/licences/${_s(l['id'])}/renewed',
                        {if (f['renews_on'] != null) 'renews_on': f['renews_on'], if (f['cost'] != null) 'cost': double.tryParse(f['cost']!)});
                  },
                  child: const Text('Maine renew kiya')),
              TextButton(onPressed: () => _run('DELETE', '/api/itadmin/licences/${_s(l['id'])}'), child: const Text('List se hatao')),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---------------- Log (people + access)
  Future<void> _newPerson() async {
    final f = await _form(context, 'Naya insaan', const [('name', 'Naam'), ('email', 'Office email'), ('phone', 'Phone'), ('role', 'Kaam'), ('department', 'Department')], ok: 'Save');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('POST', '/api/itadmin/people', f);
  }

  Widget _people() {
    final rows = _list(_d?['people']);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(child: GlassButton(label: 'Naya insaan', icon: Icons.person_add_alt_rounded, onTap: _busy ? null : _newPerson)),
        const SizedBox(width: 8),
        Expanded(
            child: GlassButton(
                label: 'Naya joiner',
                icon: Icons.login_rounded,
                onTap: () async {
                  final f = await _form(context, 'Naya staff aa raha hai', const [('name', 'Naam'), ('when', 'Kab se (YYYY-MM-DD)')], ok: 'Checklist banao');
                  if (f == null || (f['name'] ?? '').isEmpty) return;
                  final r = await _run('POST', '/api/itadmin/people', {'name': f['name']});
                  final p = _m(r?['person']);
                  if (p['id'] != null) await _run('POST', '/api/itadmin/people/${_s(p['id'])}/joiner', {'when': f['when'] ?? ''});
                })),
      ]),
      const SizedBox(height: 8),
      _muted('Yahan sirf likha jata hai ki kis ke paas kaun sa access hai. Password kabhi mat likhiye.'),
      for (final p in rows)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => ItadminPersonPage(app: widget.app, id: _s(p['id']))))
                .then((_) => _load()),
            child: Glass(
              padding: const EdgeInsets.all(12),
              child: Row(children: [
                const Icon(Icons.badge_rounded, color: C.accentSoft),
                const SizedBox(width: 10),
                Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(p['number'])} · ${_s(p['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text([_s(p['role']), _s(p['email'])].where((x) => x.isNotEmpty).join(' · '), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ])),
                Pill(_s(p['status']), fg: _s(p['status']) == 'leaving' ? C.warn : (_s(p['status']) == 'left' ? C.muted : C.ok)),
              ]),
            ),
          ),
        ),
    ]);
  }

  // ---------------- Guides
  Future<void> _newGuide() async {
    final f = await _form(context, 'Naya guide', const [
      ('topic', 'Kis baare mein (jaise Naye PC par office email)'),
      ('words', 'Aap kaise karti hain (apne shabdon mein, step by step)'),
      ('audience', 'Kiske liye (khaali = sab staff)'),
    ], ok: 'Guide banao');
    if (f == null || (f['topic'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/itadmin/guides', f);
    final g = _m(r?['guide']);
    if (g['id'] != null && mounted) {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminGuidePage(app: widget.app, id: _s(g['id'])))).then((_) => _load());
    }
  }

  Widget _guides() {
    final rows = _list(_d?['guides']);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(child: GlassButton(label: 'Naya guide', icon: Icons.menu_book_rounded, onTap: _busy ? null : _newGuide)),
        const SizedBox(width: 8),
        Expanded(
            child: GlassButton(
                label: 'Sawaal poochho',
                icon: Icons.help_outline_rounded,
                onTap: () async {
                  final f = await _form(context, 'Staff ka IT sawaal', const [('text', 'Sawaal'), ('person', 'Kisne poocha')], ok: 'Jawab');
                  if (f == null || (f['text'] ?? '').isEmpty || !mounted) return;
                  final r = await _call(context, widget.app, 'POST', '/api/itadmin/ask', f);
                  if (r != null && mounted) {
                    await showDialog<void>(
                        context: context,
                        builder: (d) => AlertDialog(content: SingleChildScrollView(child: Text(_s(r['say']))), actions: [
                              TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))
                            ]));
                  }
                  await _load();
                })),
      ]),
      const SizedBox(height: 8),
      if (rows.isEmpty) _muted('Abhi koi guide nahi. Aap jo baar baar samjhati hain, ek baar likh dijiye.'),
      for (final g in rows)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => ItadminGuidePage(app: widget.app, id: _s(g['id']))))
                .then((_) => _load()),
            child: Glass(
              padding: const EdgeInsets.all(12),
              child: Row(children: [
                Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(g['number'])} · ${_s(g['title'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text('v${_s(g['version'])} · ${_s(g['asked'])} baar kaam aaya', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ])),
                Pill(_s(g['status']) == 'published' ? 'Live' : 'Draft', fg: _s(g['status']) == 'published' ? C.ok : C.warn),
              ]),
            ),
          ),
        ),
      FutureBuilder<dynamic>(
        future: widget.app.api!.call('GET', '/api/itadmin/gaps'),
        builder: (c, snap) {
          final gaps = _list(_m(snap.data)['gaps']);
          if (gaps.isEmpty) return const SizedBox.shrink();
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            _h('Staff ye poochte hain, guide nahi hai'),
            for (final g in gaps.take(6)) Text('• ${_s(g['topic'])} (${_s(g['count'])}x)', style: const TextStyle(fontSize: 13)),
          ]);
        },
      ),
    ]);
  }

  // ---------------- Admin
  Widget _admin() {
    final conn = _m(_d?['connections']);
    final g = _m(conn['google']);
    final ms = _m(conn['microsoft']);
    final st = _m(_d?['settings']);
    final practices = _list(st['practices']);
    final reviews = _list(_d?['reviews']);
    Widget connTile(String title, Map<String, dynamic> c, VoidCallback onLink, String provider) => Glass(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(c.isEmpty ? 'Juda nahi' : (_s(c['mode']) == 'manage' ? 'Padhna + haan se badlaav' : 'Sirf padhna'), fg: c.isEmpty ? C.muted : C.ok),
            ]),
            if (c.isNotEmpty) Text('${_s(c['account'])}${_s(c['last_sync']).isNotEmpty ? ' · sync ${_s(c['last_sync'])}' : ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (_s(c['last_error']).isNotEmpty) Text(_s(c['last_error']), style: const TextStyle(color: C.bad, fontSize: 12)),
            Row(children: [
              TextButton(onPressed: onLink, child: Text(c.isEmpty ? 'Jodiye' : 'Dobara jodiye')),
              if (c.isNotEmpty) TextButton(onPressed: () => _run('POST', '/api/itadmin/sync', {'provider': provider}), child: const Text('Abhi padho')),
              if (c.isNotEmpty) TextButton(onPressed: () => _run('DELETE', '/api/itadmin/$provider'), child: const Text('Hatao')),
            ]),
          ]),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _muted('Hoola aapke admin console ko sirf padhta hai (users, licence, devices). Koi bhi badlaav card par aapki haan ke baad hi.'),
      connTile('Google Workspace', g, () async {
        final mode = await showDialog<String>(
            context: context,
            builder: (d) => SimpleDialog(title: const Text('Kya permission dein?'), children: [
                  SimpleDialogOption(onPressed: () => Navigator.pop(d, 'read'), child: const Text('Sirf padhna (behtar)')),
                  SimpleDialogOption(onPressed: () => Navigator.pop(d, 'manage'), child: const Text('Padhna + meri haan par badlaav')),
                ]));
        if (mode == null || !mounted) return;
        final r = await _call(context, widget.app, 'POST', '/api/itadmin/google/start', {'mode': mode});
        final url = _s(r?['url']);
        if (url.isNotEmpty) await Native.openExternal(url: url);
      }, 'google'),
      const SizedBox(height: 8),
      connTile('Microsoft 365', ms, () async {
        final f = await _form(context, 'Microsoft 365 (Entra app)', const [
          ('directory_id', 'Directory (tenant) ID'),
          ('client_id', 'Application (client) ID'),
          ('client_secret', 'Client secret (sirf yahan; kabhi dikhaya nahi jayega)'),
          ('mode', 'read / manage'),
        ], hidden: const {'client_secret'}, ok: 'Jodo');
        if (f == null) return;
        final r = await _run('PUT', '/api/itadmin/microsoft', f);
        final cu = _s(r?['consent_url']);
        if (cu.isNotEmpty && mounted) {
          final go = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(content: const Text('Admin consent abhi dena hai? (Microsoft ka page khulega)'), actions: [
                    TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Baad mein')),
                    TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Kholo')),
                  ]));
          if (go == true) await Native.openExternal(url: cu);
        }
      }, 'microsoft'),
      _h('Access review'),
      GlassButton(label: 'Naya review shuru karo', icon: Icons.fact_check_rounded, onTap: () => _run('POST', '/api/itadmin/reviews')),
      const SizedBox(height: 6),
      for (final r in reviews) Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminReviewView(app: widget.app, review: r, onDone: _load)),
      _h('Achhi aadatein (tick karo)'),
      for (final p in practices)
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: p['done'] == true,
          title: Text(_s(p['text']), style: const TextStyle(fontSize: 13)),
          subtitle: Text(_s(p['why']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          onChanged: (v) => _run('PUT', '/api/itadmin/settings', {'practices': {_s(p['id']): v == true}}),
        ),
      _h('Niyam'),
      GlassButton(
          label: 'Office ki jaankari',
          icon: Icons.tune_rounded,
          onTap: () async {
            final f = await _form(context, 'IT admin niyam', const [
              ('org_name', 'Office ka naam'),
              ('domain', 'Email domain'),
              ('admin_name', 'Admin rights kiske paas'),
              ('standard_systems', 'Har naye insaan ko (comma se: Email, Tally, Wi-Fi)'),
              ('morning_time', 'Subah ka note (HH:MM)'),
              ('rules', 'Aapke niyam'),
            ], initial: {
              for (final k in ['org_name', 'domain', 'admin_name', 'morning_time', 'rules']) if (_s(st[k]).isNotEmpty) k: _s(st[k]),
              'standard_systems': ((st['standard_systems'] as List?) ?? const []).join(', '),
            }, ok: 'Save');
            if (f != null) await _run('PUT', '/api/itadmin/settings', f);
          }),
      const SizedBox(height: 8),
      GlassButton(label: 'Register Excel', icon: Icons.table_chart_rounded, onTap: () => _run('POST', '/api/itadmin/register')),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('IT Admin Sahayak')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Licence'), (2, 'Log'), (3, 'Guides'), (4, 'Admin')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _licences(), _people(), _guides(), _admin()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Devices IT Helpdesk ke register mein hain. Access / setting ka har badlaav sirf aapki haan ke card se. Password / OTP Hoola kabhi nahi maangta ya rakhta. Renewal ka paisa aap bharti hain.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- person page
class ItadminPersonPage extends StatefulWidget {
  const ItadminPersonPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<ItadminPersonPage> createState() => _ItadminPersonPageState();
}

class _ItadminPersonPageState extends State<ItadminPersonPage> {
  Map<String, dynamic>? _p;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = _m(await widget.app.api!.call('GET', '/api/itadmin/people/${widget.id}'));
      if (mounted) setState(() => _p = p);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _go(String method, String path, [Object? body]) async {
    await _call(context, widget.app, method, path, body);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(p == null ? 'Insaan' : _s(p['name']))),
      body: Aurora(
        child: p == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.all(16), children: [
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(p['number'])} · ${_s(p['name'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                    Text([_s(p['role']), _s(p['department']), _s(p['email']), _s(p['status'])].where((x) => x.isNotEmpty).join(' · '),
                        style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  ]),
                ),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(
                      label: 'Access jodo',
                      icon: Icons.key_rounded,
                      height: 42,
                      onTap: () async {
                        final f = await _form(context, 'Kaun sa access (password nahi)', const [
                          ('system', 'System (Tally, GST portal, Router, Wi-Fi...)'),
                          ('account', 'Login naam / email'),
                          ('level', 'user / admin / owner'),
                        ], ok: 'Darj');
                        if (f == null) return;
                        final shared = await showDialog<bool>(
                            context: context,
                            builder: (d) => AlertDialog(content: const Text('Yeh login kai log share karte hain?'), actions: [
                                  TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
                                  TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, shared')),
                                ]));
                        await _go('POST', '/api/itadmin/access', {...f, 'person': widget.id, 'shared': shared == true});
                      }),
                  GlassButton(
                      label: 'Kaam badla',
                      icon: Icons.swap_horiz_rounded,
                      height: 42,
                      onTap: () async {
                        final f = await _form(context, 'Naya kaam', const [('new_role', 'Naya kaam / department')], ok: 'Checklist');
                        if (f != null) await _go('POST', '/api/itadmin/people/${widget.id}/mover', f);
                      }),
                  GlassButton(
                      label: 'Chhod rahe hain',
                      icon: Icons.logout_rounded,
                      height: 42,
                      color: C.warn,
                      onTap: () async {
                        final f = await _form(context, 'Aakhri din', const [('when', 'Tareekh (YYYY-MM-DD, khaali = aaj)')], ok: 'Checklist + cards');
                        if (f != null) await _go('POST', '/api/itadmin/people/${widget.id}/leaver', f);
                      }),
                  if (_s(p['status']) == 'left')
                    GlassButton(label: 'Data mitao (DPDP)', icon: Icons.delete_forever_rounded, height: 42, color: C.bad,
                        onTap: () => _go('POST', '/api/itadmin/people/${widget.id}/forget')),
                ]),
                _h('Access'),
                for (final a in _list(p['access']))
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(_s(a['level']) == 'user' ? Icons.person_outline_rounded : Icons.admin_panel_settings_rounded,
                        color: _s(a['level']) == 'user' ? C.muted : C.warn),
                    title: Text('${_s(a['system'])} · ${_s(a['account'])}'),
                    subtitle: Text([
                      _s(a['level']),
                      if (a['shared'] == true) 'shared',
                      '2-step: ${_s(a['mfa'])}',
                      _s(a['status']),
                    ].join(' · ')),
                    trailing: _s(a['status']) == 'active'
                        ? TextButton(
                            onPressed: () => _go('POST', '/api/itadmin/changes',
                                {'kind': _s(a['source']) == 'manual' ? 'access_remove' : 'user_disable', 'access': _s(a['id'])}),
                            child: const Text('Hatao (card)'))
                        : null,
                  ),
                _h('Devices (IT Helpdesk)'),
                for (final d in _list(p['devices'])) Text('• ${_s(d['tag'])} ${_s(d['name'])} ${_s(d['serial'])}', style: const TextStyle(fontSize: 13)),
                _h('Checklists'),
                for (final c in _list(p['checklists']))
                  Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminChecklistCard(app: widget.app, data: {'checklist': c, 'person': p['name']}, onDone: _load)),
              ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- guide page
class ItadminGuidePage extends StatefulWidget {
  const ItadminGuidePage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<ItadminGuidePage> createState() => _ItadminGuidePageState();
}

class _ItadminGuidePageState extends State<ItadminGuidePage> {
  Map<String, dynamic>? _g;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final g = _m(await widget.app.api!.call('GET', '/api/itadmin/guides/${widget.id}'));
      if (mounted) setState(() => _g = g);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _go(String method, String path, [Object? body]) async {
    await _call(context, widget.app, method, path, body);
    await _load();
  }

  Future<void> _shot(int n) async {
    try {
      final x = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      final r = await widget.app.api!.uploadFile('/api/itadmin/guides/${widget.id}/shot', x.name.isEmpty ? 'shot.png' : x.name, bytes, fields: {'n': '$n'});
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final g = _g;
    final api = widget.app.api!;
    final base = api.baseUrl.endsWith('/') ? api.baseUrl.substring(0, api.baseUrl.length - 1) : api.baseUrl;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(g == null ? 'Guide' : _s(g['title']))),
      body: Aurora(
        child: g == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.all(16), children: [
                Row(children: [
                  Pill('${_s(g['number'])} · v${_s(g['version'])}'),
                  const SizedBox(width: 6),
                  Pill(_s(g['status']) == 'published' ? 'Live' : 'Draft', fg: _s(g['status']) == 'published' ? C.ok : C.warn),
                ]),
                const SizedBox(height: 8),
                for (final st in _list(g['steps']))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Glass(
                      padding: const EdgeInsets.all(12),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${_s(st['n'])}. ${_s(st['text'])}', style: const TextStyle(fontSize: 14, height: 1.3)),
                        if (_s(st['shot']).isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: Image.network('$base/api/itadmin/shots/${_s(st['shot'])}', headers: api.authHeaders, fit: BoxFit.contain,
                                  errorBuilder: (_, __, ___) => const Text('Screenshot nahi khula', style: TextStyle(color: C.muted))),
                            ),
                          ),
                        Row(children: [
                          TextButton(onPressed: () => _shot(int.tryParse(_s(st['n'])) ?? 1), child: const Text('Screenshot')),
                          TextButton(
                              onPressed: () async {
                                final f = await _form(context, 'Step badlo', const [('text', 'Step')], initial: {'text': _s(st['text'])}, ok: 'Save');
                                if (f != null && (f['text'] ?? '').isNotEmpty) await _go('PUT', '/api/itadmin/guides/${widget.id}/steps/${_s(st['n'])}', f);
                              },
                              child: const Text('Badlo')),
                          TextButton(onPressed: () => _go('PUT', '/api/itadmin/guides/${widget.id}/steps/${_s(st['n'])}', {'remove': true}), child: const Text('Hatao')),
                        ]),
                      ]),
                    ),
                  ),
                TextButton(
                    onPressed: () async {
                      final f = await _form(context, 'Naya step', const [('text', 'Step')], ok: 'Jodo');
                      final n = _list(g['steps']).length + 1;
                      if (f != null && (f['text'] ?? '').isNotEmpty) await _go('PUT', '/api/itadmin/guides/${widget.id}/steps/$n', f);
                    },
                    child: const Text('+ Step jodo')),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (_s(g['status']) != 'published')
                    GradientButton(label: 'Publish (staff ke liye)', icon: Icons.publish_rounded, height: 44,
                        onTap: () => _go('POST', '/api/itadmin/guides/${widget.id}/publish', {})),
                  GlassButton(label: 'Word file', icon: Icons.description_rounded, height: 44, onTap: () => _go('POST', '/api/itadmin/guides/${widget.id}/file')),
                  GlassButton(label: 'Band karo', icon: Icons.archive_rounded, height: 44,
                      onTap: () => _go('POST', '/api/itadmin/guides/${widget.id}/publish', {'archive': true})),
                ]),
                if (_list(g['versions']).isNotEmpty) _h('Purane version'),
                for (final v in _list(g['versions']).reversed)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('v${_s(v['version'])} · ${_s(v['steps'])} steps'),
                    subtitle: Text(_s(v['at'])),
                    trailing: TextButton(onPressed: () => _go('POST', '/api/itadmin/guides/${widget.id}/restore', {'version': v['version']}), child: const Text('Wapas lao')),
                  ),
              ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- review view
class ItadminReviewView extends StatelessWidget {
  const ItadminReviewView({super.key, required this.app, required this.review, this.onDone});
  final Santosh app;
  final Map<String, dynamic> review;
  final VoidCallback? onDone;

  @override
  Widget build(BuildContext context) {
    final items = _list(review['items']);
    final open = _s(review['status']) == 'open';
    return Glass(
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${_s(review['number'])} · ${_s(review['decided'])}/${_s(review['total'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(open ? 'Khula' : 'Poora', fg: open ? C.warn : C.ok),
        ]),
        for (final it in items)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(it['person']).isEmpty ? '(kisi se juda nahi)' : _s(it['person'])} · ${_s(it['system'])} · ${_s(it['level'])}',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              if ((it['flags'] as List?)?.isNotEmpty == true)
                Text((it['flags'] as List).map(_s).join(', '), style: const TextStyle(fontSize: 12, color: C.warn)),
              if (open && _s(it['decision']).isEmpty)
                Row(children: [
                  TextButton(
                      onPressed: () async {
                        await _call(context, app, 'POST', '/api/itadmin/reviews/${_s(review['id'])}/items/${_s(it['id'])}', {'decision': 'keep'});
                        onDone?.call();
                      },
                      child: const Text('Rakho')),
                  TextButton(
                      onPressed: () async {
                        await _call(context, app, 'POST', '/api/itadmin/reviews/${_s(review['id'])}/items/${_s(it['id'])}', {'decision': 'remove'});
                        onDone?.call();
                      },
                      child: const Text('Hatao (card)')),
                ])
              else if (_s(it['decision']).isNotEmpty)
                Text(_s(it['decision']) == 'keep' ? 'Rakha' : 'Hatane ka card', style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
        if (open)
          TextButton(
              onPressed: () async {
                await _call(context, app, 'POST', '/api/itadmin/reviews/${_s(review['id'])}/close');
                onDone?.call();
              },
              child: const Text('Review band karo')),
      ]),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
/// itadmin_change: an access / settings change waiting for HER tap. The only approve path.
class ItadminChangeCard extends StatefulWidget {
  const ItadminChangeCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ItadminChangeCard> createState() => _ItadminChangeCardState();
}

class _ItadminChangeCardState extends State<ItadminChangeCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['change']);

  @override
  void didUpdateWidget(covariant ItadminChangeCard old) {
    super.didUpdateWidget(old);
    final n = _m(widget.data['change']);
    if (n.isNotEmpty) _c = n;
  }

  Future<void> _decide(bool yes) async {
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyun nahi? (zaroori nahi)', const [('reason', 'Wajah')], ok: 'Mana karo');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/itadmin/changes/${_s(_c['id'])}/decide', {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['change'] is Map) _c = _m(r['change']);
      });
    }
    widget.onDone?.call();
  }

  Future<void> _done(bool ok) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/itadmin/changes/${_s(_c['id'])}/done', {'ok': ok});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['change'] is Map) _c = _m(r['change']);
      });
    }
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final status = _s(c['status']);
    final api = _m(c['api']);
    final steps = (c['steps'] as List?)?.map(_s).toList() ?? const <String>[];
    return Glass(
      border: status == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.admin_panel_settings_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Aapki haan chahiye · ${_s(c['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(c['kind_label'])),
        ]),
        const SizedBox(height: 6),
        Text(_s(c['what']), style: const TextStyle(fontWeight: FontWeight.w700)),
        Text('System: ${_s(c['system'])}${_s(c['target']).isNotEmpty ? ' · ${_s(c['target'])}' : ''}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (_s(c['asked_by']).isNotEmpty) Text('Kisne maanga: ${_s(c['asked_by'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 4),
        if (api.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
            child: Text('Haan par yeh call jayegi:\n${_s(api['method'])} ${_s(api['url'])}${api['body'] != null ? '\n${_s(api['body'])}' : ''}',
                style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace')),
          )
        else ...[
          const Text('Aap khud karengi (console mein):', style: TextStyle(fontSize: 12.5)),
          for (final s in steps) Text('• $s', style: const TextStyle(fontSize: 12.5)),
        ],
        if (_s(c['risk']).isNotEmpty) Text('Dhyaan: ${_s(c['risk'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(c['undo']).isNotEmpty) Text('Wapas: ${_s(c['undo'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(c['result']).isNotEmpty) Text(_s(c['result']), style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (status == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, karo', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else if (status == 'approved')
          Row(children: [
            Expanded(child: GradientButton(label: 'Maine kar diya', icon: Icons.done_all_rounded, height: 44, onTap: _busy ? null : () => _done(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Nahi hua', icon: Icons.error_outline_rounded, height: 44, onTap: _busy ? null : () => _done(false))),
          ])
        else
          Text(switch (status) { 'done' => 'Ho gaya.', 'rejected' => 'Mana kiya. Kuch nahi badla.', 'failed' => 'Nahi hua.', _ => status },
              style: TextStyle(color: status == 'done' ? C.ok : C.muted, fontSize: 12.5)),
      ]),
    );
  }
}

/// itadmin_checklist: joiner / mover / leaver checklist with ticks (change items close through their card).
class ItadminChecklistCard extends StatefulWidget {
  const ItadminChecklistCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ItadminChecklistCard> createState() => _ItadminChecklistCardState();
}

class _ItadminChecklistCardState extends State<ItadminChecklistCard> {
  late Map<String, dynamic> _cl = _m(widget.data['checklist']);

  Future<void> _tick(Map<String, dynamic> it, bool v) async {
    final r = await _call(context, widget.app, 'POST', '/api/itadmin/checklists/${_s(_cl['id'])}/items/${_s(it['id'])}', {'done': v});
    if (r != null && r['checklist'] is Map && mounted) setState(() => _cl = _m(r['checklist']));
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final items = _list(_cl['items']);
    final kind = _s(_cl['kind']);
    final label = switch (kind) { 'joiner' => 'Naya staff', 'mover' => 'Kaam badla', 'leaver' => 'Chhod rahe', _ => kind };
    return Glass(
      padding: const EdgeInsets.all(12),
      border: kind == 'leaver' && _s(_cl['status']) == 'open' ? C.warn : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$label: ${_s(widget.data['person'])} · ${_s(_cl['done'])}/${_s(_cl['total'])} · ${_s(_cl['due'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
        if (_s(widget.data['say']).isNotEmpty) Text(_s(widget.data['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final it in items)
          CheckboxListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            value: it['done'] == true,
            title: Text(_s(it['text']), style: const TextStyle(fontSize: 13)),
            subtitle: _s(it['change']).isNotEmpty ? const Text('Card se poora hoga (aapki haan)', style: TextStyle(fontSize: 11, color: C.faint)) : null,
            onChanged: _s(it['change']).isNotEmpty ? null : (v) => _tick(it, v == true),
          ),
      ]),
    );
  }
}

/// itadmin_renewal: one renewal reminder.
class ItadminRenewalCard extends StatelessWidget {
  const ItadminRenewalCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final l = _m(data['licence']);
    return Glass(
      border: C.warn,
      child: Row(children: [
        const Icon(Icons.event_repeat_rounded, color: C.warn),
        const SizedBox(width: 10),
        Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Renewal · ${_s(l['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5)),
          TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminScreen(app: app))),
              child: const Text('IT Admin kholo')),
        ])),
      ]),
    );
  }
}

/// itadmin_review: a new access review started.
class ItadminReviewCard extends StatelessWidget {
  const ItadminReviewCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.fact_check_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('Access review ${_s(_m(data['review'])['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5)),
          TextButton(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminScreen(app: app))), child: const Text('Review kholo')),
        ]),
      );
}

/// itadmin_guide: a guide was written / updated (draft until she publishes).
class ItadminGuideCard extends StatelessWidget {
  const ItadminGuideCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final g = _m(data['guide']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.menu_book_rounded, color: C.accentSoft),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(g['number'])} · ${_s(g['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill('v${_s(g['version'])}'),
        ]),
        Text(_s(data['say']), style: const TextStyle(fontSize: 12.5)),
        if (_s(g['id']).isNotEmpty)
          TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminGuidePage(app: app, id: _s(g['id'])))),
              child: const Text('Guide dekho / publish')),
      ]),
    );
  }
}

/// itadmin_day: morning note.
class ItadminDayCard extends StatelessWidget {
  const ItadminDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final lines = (data['lines'] as List?)?.map(_s).toList() ?? const <String>[];
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.wb_sunny_rounded, color: C.accent),
          SizedBox(width: 8),
          Text('Aaj ka IT admin note', style: TextStyle(fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 4),
        for (final l in lines) Text('• $l', style: const TextStyle(fontSize: 13)),
        TextButton(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminScreen(app: app))), child: const Text('Kholo')),
      ]),
    );
  }
}
