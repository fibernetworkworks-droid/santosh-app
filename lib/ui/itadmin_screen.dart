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
import 'desk/desk_kit.dart';
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
    {String ok = 'Next', Map<String, String> initial = const {}, Set<String> hidden = const {}}) async {
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
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Leave it')),
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
          const Text('Today\'s IT admin', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          if (lines.isEmpty) _muted('All fine: no renewal, card or checklist is pending.'),
          for (final l in lines) Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• $l', style: const TextStyle(fontSize: 13))),
        ]),
      ),
      if (waiting.isNotEmpty) _h('Needs your yes (${waiting.length})'),
      for (final c in waiting)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
      if (approved.isNotEmpty) _h('Approved, still to do in the console'),
      for (final c in approved)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
      if (cls.isNotEmpty) _h('Checklists'),
      for (final c in cls)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminChecklistCard(app: widget.app, data: {'checklist': c, 'person': c['person']}, onDone: _load)),
      if (day['review_due'] == true)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: GlassButton(label: 'Start access review', icon: Icons.fact_check_rounded, onTap: () => _run('POST', '/api/itadmin/reviews')),
        ),
    ]);
  }

  // ---------------- Licence
  Future<void> _licenceForm([Map<String, dynamic>? l]) async {
    final f = await _form(context, l == null ? 'New licence / subscription' : 'Change: ${_s(l['name'])}', const [
      ('name', 'Name (for example Microsoft 365 Business Basic)'),
      ('vendor', 'From whom (vendor / partner)'),
      ('seats_bought', 'How many seats taken'),
      ('seats_used', 'How many in use'),
      ('cost', 'Cost ₹ (your number)'),
      ('cost_per', 'month / year / once'),
      ('renews_on', 'Renewal date (YYYY-MM-DD)'),
      ('owner', 'Who looks after / pays for it'),
      ('login_with', 'Managed from which account (not the password)'),
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
        builder: (d) => AlertDialog(content: const Text('Is the cost per seat?'), actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('No, the whole amount')),
              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Yes, per seat')),
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
        Glass(child: Text('By removing empty seats you could save about ~${_rs(save)} a year.', style: const TextStyle(color: C.ok, fontWeight: FontWeight.w700))),
      const SizedBox(height: 8),
      GlassButton(label: 'New licence', icon: Icons.add_rounded, onTap: _busy ? null : () => _licenceForm()),
      const SizedBox(height: 8),
      if (rows.isEmpty) _muted('No licences yet. When you connect M365 / Workspace, seats will come in by themselves (Admin tab).'),
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
                  if (_s(l['renews_on']).isNotEmpty) 'Renewal ${_s(l['renews_on'])} (${_s(days)} days)',
                  l['auto_renew'] == true ? 'auto-renew ON' : (l['auto_renew'] == false ? 'auto-renew OFF' : 'auto-renew ?'),
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (w.isNotEmpty)
              Text('${_s(w['free'])} seats free${w['rupees_year'] != null ? ' · ~${_rs(w['rupees_year'])}/year' : ''}',
                  style: const TextStyle(color: C.ok, fontSize: 12.5)),
            Row(children: [
              TextButton(
                  onPressed: () async {
                    final f = await _form(context, 'Renewed', const [('renews_on', 'Next date (blank = +1 year)'), ('cost', 'New cost ₹')], ok: 'Save');
                    if (f == null) return;
                    await _run('POST', '/api/itadmin/licences/${_s(l['id'])}/renewed',
                        {if (f['renews_on'] != null) 'renews_on': f['renews_on'], if (f['cost'] != null) 'cost': double.tryParse(f['cost']!)});
                  },
                  child: const Text('I renewed it')),
              TextButton(onPressed: () => _run('DELETE', '/api/itadmin/licences/${_s(l['id'])}'), child: const Text('Remove from the list')),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---------------- Log (people + access)
  Future<void> _newPerson() async {
    final f = await _form(context, 'New person', const [('name', 'Name'), ('email', 'Office email'), ('phone', 'Phone'), ('role', 'Role'), ('department', 'Department')], ok: 'Save');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('POST', '/api/itadmin/people', f);
  }

  Widget _people() {
    final rows = _list(_d?['people']);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(child: GlassButton(label: 'New person', icon: Icons.person_add_alt_rounded, onTap: _busy ? null : _newPerson)),
        const SizedBox(width: 8),
        Expanded(
            child: GlassButton(
                label: 'New joiner',
                icon: Icons.login_rounded,
                onTap: () async {
                  final f = await _form(context, 'A new staff member is joining', const [('name', 'Name'), ('when', 'From when (YYYY-MM-DD)')], ok: 'Make checklist');
                  if (f == null || (f['name'] ?? '').isEmpty) return;
                  final r = await _run('POST', '/api/itadmin/people', {'name': f['name']});
                  final p = _m(r?['person']);
                  if (p['id'] != null) await _run('POST', '/api/itadmin/people/${_s(p['id'])}/joiner', {'when': f['when'] ?? ''});
                })),
      ]),
      const SizedBox(height: 8),
      _muted('This only records who has which access. Never write passwords here.'),
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
    final f = await _form(context, 'New guide', const [
      ('topic', 'About what (for example Office email on a new PC)'),
      ('words', 'How you do it (in your own words, step by step)'),
      ('audience', 'For whom (blank = all staff)'),
    ], ok: 'Make guide');
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
        Expanded(child: GlassButton(label: 'New guide', icon: Icons.menu_book_rounded, onTap: _busy ? null : _newGuide)),
        const SizedBox(width: 8),
        Expanded(
            child: GlassButton(
                label: 'Ask a question',
                icon: Icons.help_outline_rounded,
                onTap: () async {
                  final f = await _form(context, 'Staff IT question', const [('text', 'Question'), ('person', 'Who asked')], ok: 'Answer');
                  if (f == null || (f['text'] ?? '').isEmpty || !mounted) return;
                  final r = await _call(context, widget.app, 'POST', '/api/itadmin/ask', f);
                  if (r != null && mounted) {
                    await showDialog<void>(
                        context: context,
                        builder: (d) => AlertDialog(content: SingleChildScrollView(child: Text(_s(r['say']))), actions: [
                              TextButton(onPressed: () => Navigator.pop(d), child: const Text('OK'))
                            ]));
                  }
                  await _load();
                })),
      ]),
      const SizedBox(height: 8),
      if (rows.isEmpty) _muted('No guides yet. Write down once what you keep explaining again and again.'),
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
                  Text('v${_s(g['version'])} · ${_s(g['asked'])} times it helped', style: const TextStyle(color: C.muted, fontSize: 12.5)),
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
            _h('Staff ask these, but there is no guide'),
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
              Pill(c.isEmpty ? 'Not connected' : (_s(c['mode']) == 'manage' ? 'Read + changes with your yes' : 'Read only'), fg: c.isEmpty ? C.muted : C.ok),
            ]),
            if (c.isNotEmpty) Text('${_s(c['account'])}${_s(c['last_sync']).isNotEmpty ? ' · sync ${_s(c['last_sync'])}' : ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (_s(c['last_error']).isNotEmpty) Text(_s(c['last_error']), style: const TextStyle(color: C.bad, fontSize: 12)),
            Row(children: [
              TextButton(onPressed: onLink, child: Text(c.isEmpty ? 'Connect' : 'Connect again')),
              if (c.isNotEmpty) TextButton(onPressed: () => _run('POST', '/api/itadmin/sync', {'provider': provider}), child: const Text('Read now')),
              if (c.isNotEmpty) TextButton(onPressed: () => _run('DELETE', '/api/itadmin/$provider'), child: const Text('Remove')),
            ]),
          ]),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _muted('Hoola only reads your admin console (users, licences, devices). Any change happens only after your yes on a card.'),
      connTile('Google Workspace', g, () async {
        final mode = await showDialog<String>(
            context: context,
            builder: (d) => SimpleDialog(title: const Text('What permission to give?'), children: [
                  SimpleDialogOption(onPressed: () => Navigator.pop(d, 'read'), child: const Text('Read only (better)')),
                  SimpleDialogOption(onPressed: () => Navigator.pop(d, 'manage'), child: const Text('Read + changes on my yes')),
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
          ('client_secret', 'Client secret (only here; it will never be shown)'),
          ('mode', 'read / manage'),
        ], hidden: const {'client_secret'}, ok: 'Add');
        if (f == null) return;
        final r = await _run('PUT', '/api/itadmin/microsoft', f);
        final cu = _s(r?['consent_url']);
        if (cu.isNotEmpty && mounted) {
          final go = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(content: const Text('Give admin consent now? (Microsoft\'s page will open)'), actions: [
                    TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Later')),
                    TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Open')),
                  ]));
          if (go == true) await Native.openExternal(url: cu);
        }
      }, 'microsoft'),
      _h('Access review'),
      GlassButton(label: 'Start a new review', icon: Icons.fact_check_rounded, onTap: () => _run('POST', '/api/itadmin/reviews')),
      const SizedBox(height: 6),
      for (final r in reviews) Padding(padding: const EdgeInsets.only(bottom: 8), child: ItadminReviewView(app: widget.app, review: r, onDone: _load)),
      _h('Good habits (tick)'),
      for (final p in practices)
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: p['done'] == true,
          title: Text(_s(p['text']), style: const TextStyle(fontSize: 13)),
          subtitle: Text(_s(p['why']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          onChanged: (v) => _run('PUT', '/api/itadmin/settings', {'practices': {_s(p['id']): v == true}}),
        ),
      _h('Rules'),
      GlassButton(
          label: 'Office information',
          icon: Icons.tune_rounded,
          onTap: () async {
            final f = await _form(context, 'IT admin rules', const [
              ('org_name', 'Office name'),
              ('domain', 'Email domain'),
              ('admin_name', 'Who has admin rights'),
              ('standard_systems', 'For every new person (comma separated: Email, Tally, Wi-Fi)'),
              ('morning_time', 'Morning note (HH:MM)'),
              ('rules', 'Your rules'),
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
  Widget build(BuildContext context) {
    // v0.869 R8 wave 2: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'IT Admin',
      tabs: const ['Today', 'Licence', 'Log', 'Guides', 'Admin'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      busy: _busy,
      onRefresh: _load,
      body: () => ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
        [_today(), _licences(), _people(), _guides(), _admin()][_tab],
        const SizedBox(height: 14),
        const Text(
                  'Devices are in the IT Helpdesk register. Every access / setting change happens only through a card with your yes. Hoola never asks for or keeps a password / OTP. You pay the renewal money yourself.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
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
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(p == null ? 'Person' : _s(p['name']))),
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
                      label: 'Add access',
                      icon: Icons.key_rounded,
                      height: 42,
                      onTap: () async {
                        final f = await _form(context, 'Which access (not the password)', const [
                          ('system', 'System (Tally, GST portal, Router, Wi-Fi...)'),
                          ('account', 'Login name / email'),
                          ('level', 'user / admin / owner'),
                        ], ok: 'Recorded');
                        if (f == null) return;
                        final shared = await showDialog<bool>(
                            context: context,
                            builder: (d) => AlertDialog(content: const Text('Do many people share this login?'), actions: [
                                  TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('No')),
                                  TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Yes, shared')),
                                ]));
                        await _go('POST', '/api/itadmin/access', {...f, 'person': widget.id, 'shared': shared == true});
                      }),
                  GlassButton(
                      label: 'Role changed',
                      icon: Icons.swap_horiz_rounded,
                      height: 42,
                      onTap: () async {
                        final f = await _form(context, 'New role', const [('new_role', 'New role / department')], ok: 'Checklist');
                        if (f != null) await _go('POST', '/api/itadmin/people/${widget.id}/mover', f);
                      }),
                  GlassButton(
                      label: 'Leaving',
                      icon: Icons.logout_rounded,
                      height: 42,
                      color: C.warn,
                      onTap: () async {
                        final f = await _form(context, 'Last day', const [('when', 'Date (YYYY-MM-DD, blank = today)')], ok: 'Checklist + cards');
                        if (f != null) await _go('POST', '/api/itadmin/people/${widget.id}/leaver', f);
                      }),
                  if (_s(p['status']) == 'left')
                    GlassButton(label: 'Delete data (DPDP)', icon: Icons.delete_forever_rounded, height: 42, color: C.bad,
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
                            child: const Text('Remove (card)'))
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
                                  errorBuilder: (_, __, ___) => const Text('Screenshot did not open', style: TextStyle(color: C.muted))),
                            ),
                          ),
                        Row(children: [
                          TextButton(onPressed: () => _shot(int.tryParse(_s(st['n'])) ?? 1), child: const Text('Screenshot')),
                          TextButton(
                              onPressed: () async {
                                final f = await _form(context, 'Change step', const [('text', 'Step')], initial: {'text': _s(st['text'])}, ok: 'Save');
                                if (f != null && (f['text'] ?? '').isNotEmpty) await _go('PUT', '/api/itadmin/guides/${widget.id}/steps/${_s(st['n'])}', f);
                              },
                              child: const Text('Change')),
                          TextButton(onPressed: () => _go('PUT', '/api/itadmin/guides/${widget.id}/steps/${_s(st['n'])}', {'remove': true}), child: const Text('Remove')),
                        ]),
                      ]),
                    ),
                  ),
                TextButton(
                    onPressed: () async {
                      final f = await _form(context, 'New step', const [('text', 'Step')], ok: 'Add');
                      final n = _list(g['steps']).length + 1;
                      if (f != null && (f['text'] ?? '').isNotEmpty) await _go('PUT', '/api/itadmin/guides/${widget.id}/steps/$n', f);
                    },
                    child: const Text('+ Add step')),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (_s(g['status']) != 'published')
                    GradientButton(label: 'Publish (for staff)', icon: Icons.publish_rounded, height: 44,
                        onTap: () => _go('POST', '/api/itadmin/guides/${widget.id}/publish', {})),
                  GlassButton(label: 'Word file', icon: Icons.description_rounded, height: 44, onTap: () => _go('POST', '/api/itadmin/guides/${widget.id}/file')),
                  GlassButton(label: 'Turn off', icon: Icons.archive_rounded, height: 44,
                      onTap: () => _go('POST', '/api/itadmin/guides/${widget.id}/publish', {'archive': true})),
                ]),
                if (_list(g['versions']).isNotEmpty) _h('Old versions'),
                for (final v in _list(g['versions']).reversed)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('v${_s(v['version'])} · ${_s(v['steps'])} steps'),
                    subtitle: Text(_s(v['at'])),
                    trailing: TextButton(onPressed: () => _go('POST', '/api/itadmin/guides/${widget.id}/restore', {'version': v['version']}), child: const Text('Bring back')),
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
          Pill(open ? 'Open' : 'Complete', fg: open ? C.warn : C.ok),
        ]),
        for (final it in items)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(it['person']).isEmpty ? '(not connected to anyone)' : _s(it['person'])} · ${_s(it['system'])} · ${_s(it['level'])}',
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
                      child: const Text('Keep')),
                  TextButton(
                      onPressed: () async {
                        await _call(context, app, 'POST', '/api/itadmin/reviews/${_s(review['id'])}/items/${_s(it['id'])}', {'decision': 'remove'});
                        onDone?.call();
                      },
                      child: const Text('Remove (card)')),
                ])
              else if (_s(it['decision']).isNotEmpty)
                Text(_s(it['decision']) == 'keep' ? 'Kept' : 'Card to remove', style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
        if (open)
          TextButton(
              onPressed: () async {
                await _call(context, app, 'POST', '/api/itadmin/reviews/${_s(review['id'])}/close');
                onDone?.call();
              },
              child: const Text('Close review')),
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
      final f = await _form(context, 'Why not? (not needed)', const [('reason', 'Reason')], ok: 'Decline');
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
          Expanded(child: Text('Needs your yes · ${_s(c['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(c['kind_label'])),
        ]),
        const SizedBox(height: 6),
        Text(_s(c['what']), style: const TextStyle(fontWeight: FontWeight.w700)),
        Text('System: ${_s(c['system'])}${_s(c['target']).isNotEmpty ? ' · ${_s(c['target'])}' : ''}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (_s(c['asked_by']).isNotEmpty) Text('Who asked: ${_s(c['asked_by'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 4),
        if (api.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
            child: Text('On yes, this call will go:\n${_s(api['method'])} ${_s(api['url'])}${api['body'] != null ? '\n${_s(api['body'])}' : ''}',
                style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace')),
          )
        else ...[
          const Text('You do it yourself (in the console):', style: TextStyle(fontSize: 12.5)),
          for (final s in steps) Text('• $s', style: const TextStyle(fontSize: 12.5)),
        ],
        if (_s(c['risk']).isNotEmpty) Text('Note: ${_s(c['risk'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(c['undo']).isNotEmpty) Text('Undo: ${_s(c['undo'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(c['result']).isNotEmpty) Text(_s(c['result']), style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (status == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, do it', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Decline', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else if (status == 'approved')
          Row(children: [
            Expanded(child: GradientButton(label: 'I did it', icon: Icons.done_all_rounded, height: 44, onTap: _busy ? null : () => _done(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Did not happen', icon: Icons.error_outline_rounded, height: 44, onTap: _busy ? null : () => _done(false))),
          ])
        else
          Text(switch (status) { 'done' => 'Done.', 'rejected' => 'Declined. Nothing changed.', 'failed' => 'Did not happen.', _ => status },
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
    final label = switch (kind) { 'joiner' => 'New staff', 'mover' => 'Role changed', 'leaver' => 'Leaving', _ => kind };
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
            subtitle: _s(it['change']).isNotEmpty ? const Text('Will be completed from the card (your yes)', style: TextStyle(fontSize: 11, color: C.faint)) : null,
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
              child: const Text('Open IT Admin')),
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
          TextButton(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminScreen(app: app))), child: const Text('Open review')),
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
              child: const Text('See / publish guide')),
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
          Text('Today\'s IT admin note', style: TextStyle(fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 4),
        for (final l in lines) Text('• $l', style: const TextStyle(fontSize: 13)),
        TextButton(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminScreen(app: app))), child: const Text('Open')),
      ]),
    );
  }
}
