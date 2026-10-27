/// Profile > Property Sahayak: Hoola as a real estate agent's coworker.
/// Aaj (today's visits, follow-ups, cards waiting, commission due) · Listings (her listings, photos, RERA, publish card) ·
/// Graahak (buyer / tenant leads, matches, share, visits) · Deals (stamp duty estimate from HER rates, TDS note, papers,
/// commission) · Niyam (her RERA number, rates, brokerage, visit times). A listing going public, any message to a client /
/// owner and any paper that names money run only after HER tap (fingerprint for money papers once a phone key is set up).
library;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

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
                maxLines: (k == 'words' || k == 'text' || k == 'description' || k == 'ids_text' || k == 'rules') ? 3 : 1),
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

Widget _section(String t) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 14, 4, 6),
    child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, color: C.muted, fontSize: 13)));

class PropagentScreen extends StatefulWidget {
  const PropagentScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PropagentScreen> createState() => _PropagentScreenState();
}

class _PropagentScreenState extends State<PropagentScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/propagent'));
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

  Future<void> _newListing() async {
    final f = await _form(context, 'Nayi listing', const [
      ('words', 'Property ke baare mein (jaise: 2BHK flat bikri ke liye)'),
      ('purpose', 'sale / rent / lease'),
      ('price', 'Daam (malik ka bataya) - jaise 52 lakh'),
      ('rent', 'Kiraya / mahina (kiraye ke liye)'),
      ('carpet_sqft', 'Carpet area (sq ft)'),
      ('locality', 'Ilaka'),
      ('city', 'Shehar'),
      ('address', 'Pura pata (public nahi hota)'),
      ('owner_name', 'Malik ka naam'),
      ('owner_phone', 'Malik ka phone'),
      ('project', 'Project ka naam (ho to)'),
      ('rera_project_no', 'RERA project no (naya project ho to)'),
    ], ok: 'Banao');
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['carpet_sqft'] != null) body['carpet_sqft'] = _n(f['carpet_sqft']);
    if ((f['rera_project_no'] ?? '').isNotEmpty) body['new_project'] = true;
    final r = await _run('POST', '/api/propagent/listings', body);
    final id = _s(_m(r?['listing'])['id']);
    if (id.isNotEmpty && mounted) _openListing(id);
  }

  void _openListing(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => PropagentListingPage(app: widget.app, id: id)))
      .then((_) => _load());

  void _openLead(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => PropagentLeadPage(app: widget.app, id: id)))
      .then((_) => _load());

  void _openDeal(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => PropagentDealPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newLead() async {
    final f = await _form(context, 'Naya graahak', const [
      ('name', 'Naam'),
      ('phone', 'Phone'),
      ('words', 'Kya chahiye (jaise: 2BHK Gorakshan Road 40-55 lakh)'),
      ('source', 'Kahan se: walk_in / call / portal / referral / whatsapp / cold'),
    ], ok: 'Jodo');
    if (f == null) return;
    final r = await _run('POST', '/api/propagent/leads', f);
    final id = _s(_m(r?['lead'])['id']);
    if (id.isNotEmpty && mounted) _openLead(id);
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      appBar: AppBar(title: const Text('Property Sahayak'), actions: [
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        IconButton(
            tooltip: 'Excel',
            onPressed: _busy ? null : () => _run('POST', '/api/propagent/register'),
            icon: const Icon(Icons.table_view_rounded)),
      ]),
      floatingActionButton: switch (_tab) {
        1 => FloatingActionButton.extended(onPressed: _newListing, icon: const Icon(Icons.add_home_rounded), label: const Text('Listing')),
        2 => FloatingActionButton.extended(onPressed: _newLead, icon: const Icon(Icons.person_add_rounded), label: const Text('Graahak')),
        _ => null,
      },
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today_rounded), label: 'Aaj'),
          NavigationDestination(icon: Icon(Icons.home_work_rounded), label: 'Listings'),
          NavigationDestination(icon: Icon(Icons.people_alt_rounded), label: 'Graahak'),
          NavigationDestination(icon: Icon(Icons.handshake_rounded), label: 'Deals'),
          NavigationDestination(icon: Icon(Icons.tune_rounded), label: 'Niyam'),
        ],
      ),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(14), children: switch (_tab) {
                0 => _today(d),
                1 => _listings(d),
                2 => _leads(d),
                3 => _deals(d),
                _ => _niyam(d),
              }),
            ),
    );
  }

  List<Widget> _today(Map<String, dynamic> d) {
    final day = _m(d['day']);
    final com = _m(day['commission']);
    return [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 15, height: 1.35))),
      if (_list(day['visits']).isNotEmpty) _section('Aaj ki site visit'),
      for (final v in _list(day['visits'])) PropagentVisitCard(app: widget.app, data: {'visit': v}),
      if (_list(d['cards']).any((c) => _s(c['status']) == 'waiting')) _section('Aapki haan ke liye'),
      for (final c in _list(d['cards']).where((c) => _s(c['status']) == 'waiting'))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: PropagentCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      if (_list(day['follow_ups']).isNotEmpty) _section('Follow up'),
      for (final l in _list(day['follow_ups']))
        ListTile(
            title: Text('${_s(l['number'])} ${_s(l['name'])}'),
            subtitle: Text('${_s(l['next_what'])} · ${_s(l['next_at'])}'),
            onTap: () => _openLead(_s(l['id']))),
      if (com['due'] != null && (com['due'] as num) > 0) ...[
        _section('Commission baaki'),
        for (final p in _list(com['pending'])) ListTile(title: Text('${_s(p['deal'])} · ${_s(p['due_text'])}'), subtitle: Text(_s(p['listing']))),
      ],
    ];
  }

  List<Widget> _listings(Map<String, dynamic> d) => [
        for (final l in _list(d['listings']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _openListing(_s(l['id'])),
              child: Glass(
                child: Row(children: [
                  Icon(l['public'] == true ? Icons.public_rounded : Icons.home_rounded, color: l['public'] == true ? C.ok : C.muted),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${_s(l['number'])} · ${_s(l['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                      Text([_s(l['price_text']), if (l['carpet_sqft'] != null) '${l['carpet_sqft']} sq ft carpet', _s(l['status_label'])]
                              .where((x) => x.isNotEmpty)
                              .join(' · '),
                          style: const TextStyle(fontSize: 12.5, color: C.muted)),
                      if (_strs(_m(l['checks'])['block']).isNotEmpty)
                        Text('⚠ ${_strs(_m(l['checks'])['block']).first}', style: const TextStyle(fontSize: 12, color: C.warn)),
                    ]),
                  ),
                ]),
              ),
            ),
          ),
        if (_list(d['listings']).isEmpty) const Caption('Abhi koi listing nahi. Neeche "Listing" dabaiye ya chat mein bataiye.'),
      ];

  List<Widget> _leads(Map<String, dynamic> d) => [
        for (final l in _list(d['leads']))
          ListTile(
            leading: Icon(_s(l['role']) == 'tenant' ? Icons.key_rounded : Icons.real_estate_agent_rounded),
            title: Text('${_s(l['number'])} ${_s(l['name'])} · ${_s(l['stage_label'])}'),
            subtitle: Text(_s(l['need_text'])),
            onTap: () => _openLead(_s(l['id'])),
          ),
        if (_list(d['leads']).isEmpty) const Caption('Koi graahak nahi.'),
      ];

  List<Widget> _deals(Map<String, dynamic> d) => [
        for (final x in _list(d['deals']))
          ListTile(
            leading: const Icon(Icons.handshake_rounded),
            title: Text('${_s(x['number'])} · ${_s(x['listing_title'])}'),
            subtitle: Text('${_s(x['lead_name'])} · ${_s(x['status_label'])}'),
            onTap: () => _openDeal(_s(x['id'])),
          ),
        if (_list(d['deals']).isEmpty) const Caption('Deal graahak ke page se banti hai (pasand aayi listing).'),
      ];

  List<Widget> _niyam(Map<String, dynamic> d) {
    final st = _m(d['settings']);
    final rates = _m(st['rates']);
    return [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['business']).isEmpty ? 'Business ka naam daaliye' : _s(st['business']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('RERA agent: ${_s(st['rera_agent_no']).isEmpty ? '—' : _s(st['rera_agent_no'])}'
              '${_s(st['rera_valid_until']).isEmpty ? '' : ' · ${_s(st['rera_valid_until'])} tak'}'),
          if (st['rera_expired'] == true) const Text('RERA registration khatam: renew kijiye.', style: TextStyle(color: C.bad)),
          Text('Brokerage: ${_s(st['sale_pct']).isEmpty ? '—' : '${_s(st['sale_pct'])}%'} bikri · '
              '${_s(st['rent_months']).isEmpty ? '—' : '${_s(st['rent_months'])} mahina'} kiraya'),
          Text('GST: ${st['gst_on'] == true ? 'haan (${_s(st['gstin'])})' : 'nahi'}'),
          const SizedBox(height: 8),
          GlassButton(
              label: 'Badlo',
              icon: Icons.edit_rounded,
              onTap: () async {
                final f = await _form(context, 'Niyam', const [
                  ('business', 'Business ka naam'),
                  ('agent_name', 'Aapka naam'),
                  ('phone', 'Business phone (public page par)'),
                  ('city', 'Shehar'),
                  ('rera_agent_no', 'RERA agent no (MahaRERA: A5...)'),
                  ('rera_valid_until', 'Registration kab tak (DD-MM-YYYY)'),
                  ('gstin', 'GSTIN (ho to)'),
                  ('sale_pct', 'Bikri brokerage % (har taraf)'),
                  ('rent_months', 'Kiraya brokerage (mahine)'),
                  ('visit_minutes', 'Ek visit kitne minute'),
                  ('morning_time', 'Subah ka note (HH:MM)'),
                  ('rules', 'Aapke niyam'),
                ], initial: {for (final k in st.keys) k: _s(st[k])});
                if (f == null) return;
                final body = <String, dynamic>{...f};
                for (final k in ['sale_pct', 'rent_months', 'visit_minutes']) {
                  if (f[k] != null) body[k] = _n(f[k]);
                }
                if ((f['gstin'] ?? '').isNotEmpty) body['gst_on'] = true;
                await _run('PUT', '/api/propagent/settings', body);
              }),
        ]),
      ),
      _section('Stamp duty / registration rates (aapke numbers, IGR se)'),
      for (final e in rates.entries)
        ListTile(
            title: Text(e.key),
            subtitle: Text(_m(e.value).entries.map((x) => '${x.key}: ${x.value}').join(' · '))),
      GlassButton(
          label: 'Area ka rate jodo',
          icon: Icons.add_rounded,
          onTap: () async {
            final f = await _form(context, 'Rate', const [
              ('area', 'Area / shehar (jaise akola)'),
              ('stamp_pct', 'Stamp duty %'),
              ('cess_pct', 'Cess / LBT % (ho to)'),
              ('women_less_pct', 'Mahila ke liye kam % (ho to)'),
              ('reg_pct', 'Registration %'),
              ('reg_cap', 'Registration ki seema ₹ (ho to)'),
            ]);
            if (f == null || (f['area'] ?? '').isEmpty) return;
            final row = <String, dynamic>{
              for (final k in ['stamp_pct', 'cess_pct', 'women_less_pct', 'reg_pct', 'reg_cap'])
                if (f[k] != null) k: _n(f[k]),
            };
            await _run('PUT', '/api/propagent/settings', {
              'rates': {...rates, f['area']!.toLowerCase(): row}
            });
          }),
      _section('Kabhi nahi'),
      for (final n in _strs(d['never'])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ];
  }
}

// ---------------------------------------------------------------- listing page
class PropagentListingPage extends StatefulWidget {
  const PropagentListingPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<PropagentListingPage> createState() => _PropagentListingPageState();
}

class _PropagentListingPageState extends State<PropagentListingPage> {
  Map<String, dynamic>? _l;
  List<Map<String, dynamic>> _buyers = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final l = _m(_m(await widget.app.api!.call('GET', '/api/propagent/listings/${widget.id}'))['listing']);
      final b = _m(await widget.app.api!.call('GET', '/api/propagent/listings/${widget.id}/buyers'));
      if (mounted) setState(() {
        _l = l;
        _buyers = _list(b['leads']);
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

  Future<void> _photo(String kind, ImageSource src) async {
    final x = await ImagePicker().pickImage(source: src, imageQuality: 80, maxWidth: 1800);
    if (x == null) return;
    setState(() => _busy = true);
    try {
      final m = await widget.app.api!.uploadFile('/api/propagent/listings/${widget.id}/photo', x.name, await x.readAsBytes(),
          fields: {'kind': kind});
      if (mounted) _snack(context, _s(m['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _publish() async {
    final where = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.public_rounded), title: const Text('Hoola page (link)'), onTap: () => Navigator.pop(c, 'page')),
          ListTile(
              leading: const Icon(Icons.copy_rounded),
              title: const Text('Text copy (portal / WhatsApp status par aap khud daaliye)'),
              onTap: () => Navigator.pop(c, 'copy')),
          ListTile(leading: const Icon(Icons.table_chart_rounded), title: const Text('Portal sheet (Excel)'), onTap: () => Navigator.pop(c, 'sheet')),
        ]),
      ),
    );
    if (where == null) return;
    final r = await _run('POST', '/api/propagent/listings/${widget.id}/publish', {'where': where});
    final card = _m(r?['card']);
    if (card.isNotEmpty && mounted) {
      await showDialog(
          context: context,
          builder: (d) => AlertDialog(
              content: PropagentCardCard(app: widget.app, data: {'card': card}, onDone: () => Navigator.of(d).maybePop())));
      _load();
    }
  }

  Future<void> _edit() async {
    final l = _l ?? {};
    final f = await _form(context, 'Listing badlo', const [
      ('price', 'Daam'),
      ('rent', 'Kiraya / mahina'),
      ('deposit', 'Deposit'),
      ('carpet_sqft', 'Carpet sq ft'),
      ('bhk', 'BHK'),
      ('floor', 'Floor'),
      ('furnishing', 'unfurnished / semi / full'),
      ('parking', 'Parking'),
      ('description', 'Description'),
      ('status', 'active / on_hold / sold / rented / withdrawn'),
    ], initial: {for (final k in l.keys) k: _s(l[k])});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['carpet_sqft'] != null) body['carpet_sqft'] = _n(f['carpet_sqft']);
    if (f['bhk'] != null) body['bhk'] = _n(f['bhk']);
    await _run('PATCH', '/api/propagent/listings/${widget.id}', body);
  }

  @override
  Widget build(BuildContext context) {
    final l = _l;
    final checks = _m(l?['checks']);
    final mandate = _m(l?['mandate']);
    return Scaffold(
      appBar: AppBar(title: Text(_s(l?['number']).isEmpty ? 'Listing' : _s(l?['number'])), actions: [
        IconButton(onPressed: _busy ? null : _edit, icon: const Icon(Icons.edit_rounded)),
      ]),
      body: l == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(l['title']), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                  Text([_s(l['price_text']), if (l['carpet_sqft'] != null) '${l['carpet_sqft']} sq ft carpet', _s(l['status_label'])]
                      .where((x) => x.isNotEmpty)
                      .join(' · ')),
                  if (_s(l['rera_project_no']).isNotEmpty) Text('RERA: ${_s(l['rera_project_no'])}${l['has_qr'] == true ? ' · QR laga' : ''}'),
                  if (_s(l['address']).isNotEmpty) Text('Pata (sirf aapke liye): ${_s(l['address'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
                  Text('Malik: ${_s(l['owner_name'])} ${_s(l['owner_phone_masked'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                  Text(l['public'] == true ? 'Public hai' : 'Public nahi', style: TextStyle(color: l['public'] == true ? C.ok : C.faint)),
                ]),
              ),
              for (final b in _strs(checks['block'])) Text('⛔ $b', style: const TextStyle(color: C.bad, fontSize: 12.5)),
              for (final w in _strs(checks['warn'])) Text('⚠ $w', style: const TextStyle(color: C.warn, fontSize: 12.5)),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (mandate['consent'] != true)
                  GlassButton(
                      label: 'Malik ne haan kahi',
                      icon: Icons.verified_user_rounded,
                      onTap: () async {
                        final f = await _form(context, 'Malik ki haan (marketing)', const [
                          ('commission_pct', 'Malik se commission % (ho to)'),
                          ('until', 'Kab tak (DD-MM-YYYY)'),
                        ]);
                        if (f == null) return;
                        await _run('PATCH', '/api/propagent/listings/${widget.id}', {
                          'mandate': {'consent': true, if (f['commission_pct'] != null) 'commission_pct': _n(f['commission_pct']), if (f['until'] != null) 'until': f['until']}
                        });
                      }),
                GlassButton(label: 'Photo', icon: Icons.photo_camera_rounded, onTap: _busy ? () {} : () => _photo('photo', ImageSource.camera)),
                GlassButton(label: 'Gallery', icon: Icons.photo_library_rounded, onTap: _busy ? () {} : () => _photo('photo', ImageSource.gallery)),
                if (l['new_project'] == true)
                  GlassButton(label: 'MahaRERA QR', icon: Icons.qr_code_rounded, onTap: _busy ? () {} : () => _photo('qr', ImageSource.gallery)),
                GlassButton(
                    label: 'Text banao',
                    icon: Icons.auto_awesome_rounded,
                    onTap: () async {
                      final r = await _run('POST', '/api/propagent/listings/${widget.id}/describe');
                      final t = _s(r?['text']);
                      if (t.isEmpty || !mounted) return;
                      final ok = await showDialog<bool>(
                          context: context,
                          builder: (d) => AlertDialog(content: Text(t), actions: [
                                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
                                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save karo')),
                              ]));
                      if (ok == true) await _run('PATCH', '/api/propagent/listings/${widget.id}', {'description': t});
                    }),
                if (l['public'] == true)
                  GlassButton(label: 'Page band', icon: Icons.public_off_rounded, onTap: () => _run('POST', '/api/propagent/listings/${widget.id}/unpublish')),
                if (l['public'] == true || _list(l['published']).isNotEmpty)
                  GlassButton(label: 'Poster', icon: Icons.image_rounded, onTap: () => _run('POST', '/api/propagent/listings/${widget.id}/poster')),
              ]),
              const SizedBox(height: 10),
              GradientButton(label: 'Public karne ka card', icon: Icons.campaign_rounded, onTap: _busy ? null : _publish),
              if (_list(l['photos']).isNotEmpty) _section('Photo (${_list(l['photos']).length})'),
              if (_list(l['photos']).isNotEmpty)
                SizedBox(
                  height: 96,
                  child: ListView(scrollDirection: Axis.horizontal, children: [
                    for (final p in _list(l['photos']))
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Image.network(widget.app.api!.absolute('/api/propagent/photos/${_s(p['id'])}'),
                              headers: widget.app.api!.authHeaders, width: 120, height: 96, fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => const SizedBox(width: 120, child: Icon(Icons.image_not_supported_rounded))),
                        ),
                      ),
                  ]),
                ),
              if (_buyers.isNotEmpty) _section('Kisko pasand aa sakti hai'),
              for (final b in _buyers)
                ListTile(
                  title: Text('${_s(b['number'])} ${_s(b['name'])} · ${_s(b['score'])}'),
                  subtitle: Text([..._strs(b['why']), ..._strs(b['miss'])].join(' · ')),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PropagentLeadPage(app: widget.app, id: _s(b['lead'])))),
                ),
            ]),
    );
  }
}

// ---------------------------------------------------------------- lead page
class PropagentLeadPage extends StatefulWidget {
  const PropagentLeadPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<PropagentLeadPage> createState() => _PropagentLeadPageState();
}

class _PropagentLeadPageState extends State<PropagentLeadPage> {
  Map<String, dynamic>? _l;
  List<Map<String, dynamic>> _matches = [];
  final Set<String> _pick = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/propagent/leads/${widget.id}'));
      if (mounted) setState(() {
        _l = _m(r['lead']);
        _matches = _list(r['matches']);
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

  Future<void> _showCard(Map<String, dynamic>? r) async {
    final card = _m(r?['card']);
    if (card.isEmpty || !mounted) return;
    await showDialog(
        context: context,
        builder: (d) => AlertDialog(content: PropagentCardCard(app: widget.app, data: {'card': card}, onDone: () => Navigator.of(d).maybePop())));
  }

  Future<void> _visit() async {
    final f = await _form(context, 'Site visit', const [('day', 'Din (DD-MM-YYYY ya kal)'), ('start', 'Shuru (HH:MM)')],
        initial: const {'start': '10:00'});
    if (f == null) return;
    final ids = _pick.isEmpty ? _matches.take(3).map((m) => _s(m['listing'])).toList() : _pick.toList();
    final r = await _run('POST', '/api/propagent/visits', {'lead': widget.id, 'listings': ids, 'day': f['day'] ?? '', 'start': f['start'] ?? '10:00'});
    if (r != null && mounted) _snack(context, _s(r['say']));
  }

  @override
  Widget build(BuildContext context) {
    final l = _l;
    return Scaffold(
      appBar: AppBar(title: Text(_s(l?['number']).isEmpty ? 'Graahak' : '${_s(l?['number'])} ${_s(l?['name'])}')),
      body: l == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(l['need_text']).isEmpty ? 'Zaroorat saaf nahi' : _s(l['need_text']), style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text('${_s(l['phone_masked'])} · ${_s(l['stage_label'])} · ${_s(l['source'])}', style: const TextStyle(color: C.muted)),
                  if (_s(l['next_at']).isNotEmpty) Text('Agla: ${_s(l['next_what'])} ${_s(l['next_at'])}'),
                  if (l['consent'] != true) const Text('Baat karne ki haan darj nahi', style: TextStyle(color: C.warn)),
                ]),
              ),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: [
                GlassButton(
                    label: 'Zaroorat badlo',
                    icon: Icons.edit_note_rounded,
                    onTap: () async {
                      final f = await _form(context, 'Zaroorat', const [('words', 'Kya chahiye'), ('next_when', 'Agla call kab'), ('notes', 'Note')]);
                      if (f != null) await _run('PATCH', '/api/propagent/leads/${widget.id}', f);
                    }),
                GlassButton(label: 'Visit plan', icon: Icons.directions_car_rounded, onTap: _busy ? () {} : _visit),
                GlassButton(
                    label: 'Deal banao',
                    icon: Icons.handshake_rounded,
                    onTap: () async {
                      final lid = _pick.isNotEmpty ? _pick.first : (_matches.isNotEmpty ? _s(_matches.first['listing']) : '');
                      if (lid.isEmpty) {
                        _snack(context, 'Pehle listing chuniye.');
                        return;
                      }
                      final f = await _form(context, 'Deal', const [('price', 'Tay daam / kiraya'), ('token', 'Token (ho to)'), ('market_value', 'Ready reckoner value (aapka number)')]);
                      if (f == null) return;
                      final r = await _run('POST', '/api/propagent/deals', {'listing': lid, 'lead': widget.id, ...f});
                      final id = _s(_m(r?['deal'])['id']);
                      if (id.isNotEmpty && mounted) {
                        Navigator.of(context).push(MaterialPageRoute(builder: (_) => PropagentDealPage(app: widget.app, id: id)));
                      }
                    }),
                if (_s(l['stage']) == 'lost' || _s(l['stage']) == 'closed')
                  GlassButton(label: 'Jaankari mitao', icon: Icons.delete_sweep_rounded, color: C.bad, onTap: () => _run('POST', '/api/propagent/leads/${widget.id}/forget')),
              ]),
              _section('Mel khaati listings (chuniye)'),
              for (final m in _matches)
                CheckboxListTile(
                  value: _pick.contains(_s(m['listing'])),
                  onChanged: (v) => setState(() => v == true ? _pick.add(_s(m['listing'])) : _pick.remove(_s(m['listing']))),
                  title: Text('${_s(m['number'])} · ${_s(m['title'])} · ${_s(m['score'])}'),
                  subtitle: Text([_s(m['price_text']), ..._strs(m['why']), ..._strs(m['miss']).map((x) => '⚠ $x')].where((x) => x.isNotEmpty).join(' · ')),
                ),
              if (_matches.isEmpty) const Caption('Abhi koi listing mel nahi khaati.'),
              const SizedBox(height: 8),
              GradientButton(
                  label: 'Inhe bhejne ka card',
                  icon: Icons.send_rounded,
                  onTap: _busy
                      ? null
                      : () async {
                          final r = await _run('POST', '/api/propagent/leads/${widget.id}/share', {if (_pick.isNotEmpty) 'listings': _pick.toList()});
                          await _showCard(r);
                        }),
            ]),
    );
  }
}

// ---------------------------------------------------------------- deal page
class PropagentDealPage extends StatefulWidget {
  const PropagentDealPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<PropagentDealPage> createState() => _PropagentDealPageState();
}

class _PropagentDealPageState extends State<PropagentDealPage> {
  Map<String, dynamic>? _d;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(_m(await widget.app.api!.call('GET', '/api/propagent/deals/${widget.id}'))['deal']);
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

  String _rs(dynamic v) => v == null ? '—' : '₹$v';

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final est = _m(d?['estimate']);
    final sd = _m(est['stamp']);
    final tds = _m(est['tds']);
    final com = _m(d?['commission']);
    return Scaffold(
      appBar: AppBar(title: Text(_s(d?['number']).isEmpty ? 'Deal' : _s(d?['number']))),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(d['listing_title']), style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text('${_s(d['lead_name'])} · ${_s(d['status_label'])}'),
                  Text('Daam / kiraya: ${_rs(d['price'])} · Token: ${_rs(d['token'])}'),
                  for (final x in _list(d['ids'])) Text('${_s(x['side'])}: ${_s(x['kind'])} ${_s(x['masked'])} (Locker)', style: const TextStyle(fontSize: 12, color: C.muted)),
                ]),
              ),
              if (_s(d['purpose']) == 'sale') ...[
                _section('Stamp duty / registration (andaaza, aapke rates)'),
                if (sd['stamp'] != null)
                  Text('Stamp ${_rs(sd['stamp'])} + cess ${_rs(sd['cess'])} + registration ${_rs(sd['registration'])} = ${_rs(sd['total'])}'),
                for (final m in _strs(sd['missing'])) Text('Chahiye: $m', style: const TextStyle(color: C.warn)),
                if (_s(est['rate_note']).isNotEmpty) Text(_s(est['rate_note']), style: const TextStyle(fontSize: 12, color: C.faint)),
                if (_s(sd['base_note']).isNotEmpty) Text(_s(sd['base_note']), style: const TextStyle(fontSize: 12, color: C.faint)),
              ],
              _section('TDS'),
              Text(_s(tds['say']).isEmpty ? '—' : _s(tds['say']), style: const TextStyle(fontSize: 13)),
              for (final n in _strs(est['nri'])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
              _section('Commission'),
              for (final side in ['buyer', 'seller'])
                if (_m(com[side])['amount'] != null)
                  Text('${side == 'buyer' ? 'Kharidaar / kirayedaar' : 'Malik'}: ${_rs(_m(com[side])['amount'])}'
                      '${_m(com[side])['gst'] != null && _m(com[side])['gst'] != 0 ? ' + GST ${_rs(_m(com[side])['gst'])}' : ''}'),
              Text('Mila ${_rs(com['received'])} · baaki ${_rs(com['due'])}'),
              GlassButton(
                  label: 'Commission mila',
                  icon: Icons.savings_rounded,
                  onTap: () async {
                    final f = await _form(context, 'Commission mila', const [('side', 'buyer / seller'), ('amount', 'Kitna'), ('mode', 'Kaise'), ('ref', 'UTR (ho to)')]);
                    if (f != null) await _run('POST', '/api/propagent/deals/${widget.id}/commission', f);
                  }),
              _section('Kaagaz (draft, aapki haan ke baad Word / PDF)'),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final (k, label) in const [
                  ('token_receipt', 'Token raseed'),
                  ('offer_letter', 'Offer letter'),
                  ('agreement_checklist', 'Checklist'),
                  ('commission_bill', 'Commission bill'),
                ])
                  GlassButton(
                      label: label,
                      icon: Icons.description_rounded,
                      onTap: _busy
                          ? () {}
                          : () async {
                              final r = await _run('POST', '/api/propagent/deals/${widget.id}/document', {'kind': k});
                              final card = _m(r?['card']);
                              if (card.isNotEmpty && mounted) {
                                await showDialog(
                                    context: context,
                                    builder: (dd) => AlertDialog(
                                        content: PropagentCardCard(app: widget.app, data: {'card': card}, onDone: () => Navigator.of(dd).maybePop())));
                              }
                            }),
              ]),
              _section('Checklist'),
              for (final c in _list(d['checklist']))
                CheckboxListTile(
                    value: c['done'] == true,
                    onChanged: (v) => _run('POST', '/api/propagent/deals/${widget.id}/check', {'key': _s(c['key']), 'done': v == true}),
                    title: Text(_s(c['item']), style: const TextStyle(fontSize: 13))),
              _section('Status'),
              Wrap(spacing: 6, children: [
                for (final (k, label) in const [('token', 'Token'), ('agreement', 'Agreement'), ('registered', 'Registry'), ('done', 'Poora'), ('fell', 'Toot gaya')])
                  ChoiceChip(
                      label: Text(label),
                      selected: _s(d['status']) == k,
                      onSelected: (_) => _run('POST', '/api/propagent/deals/${widget.id}/status', {'status': k})),
              ]),
              const SizedBox(height: 12),
              const Caption('Agreement sirf draft: vakil se check karwaiye. Hoola paise nahi leta / deta.'),
            ]),
    );
  }
}

// ---------------------------------------------------------------- cards
/// propagent_card: publish / message / document waiting for HER tap. Also in calls.
class PropagentCardCard extends StatefulWidget {
  const PropagentCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<PropagentCardCard> createState() => _PropagentCardCardState();
}

class _PropagentCardCardState extends State<PropagentCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/propagent/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Kaagaz ki haan' : _s(show['title']), _s(show['amount']));
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
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash'])};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/propagent/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/propagent/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() => _c = _m(m['card']).isEmpty ? _c : _m(m['card']));
        _snack(context, _s(m['say']));
      }
      final res = _m(m['result']);
      if (yes && _s(res['wa']).isNotEmpty) await Native.openExternal(url: _s(res['wa']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sent() async {
    try {
      final m = _m(await widget.app.api!.call('POST', '/api/propagent/cards/${_s(_c['id'])}/sent'));
      if (mounted) setState(() => _c = _m(m['card']).isEmpty ? _c : _m(m['card']));
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final st = _s(c['status']);
    final kind = _s(c['kind']);
    final body = _m(c['body']);
    final res = _m(c['result']);
    final title = switch (kind) {
      'publish' => 'Listing public karein? (${_s(body['number'])} · ${_s(c['sub'])})',
      'message' => 'Message: ${_s(body['to']) == 'owner' ? 'malik' : 'graahak'} ${_s(body['name'])}',
      _ => '${_s(body['title'])} · ${_s(body['deal'])}',
    };
    final text = switch (kind) { 'publish' => _s(body['show']), 'message' => _s(body['text']), _ => _s(body['text']) };
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(kind == 'publish' ? Icons.campaign_rounded : (kind == 'message' ? Icons.chat_rounded : Icons.description_rounded), color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · $title', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'sent' => 'bheja', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' || st == 'stale' ? C.bad : C.ok)),
        ]),
        if (_s(c['money_text']).isNotEmpty) Text('Rakam: ${_s(c['money_text'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 220),
          child: SingleChildScrollView(child: Text(text, style: const TextStyle(fontSize: 12.5, height: 1.35))),
        ),
        for (final w in _strs(body['warn'])) Text('⚠ $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        if ((body['blanks'] ?? 0) is num && (body['blanks'] ?? 0) > 0)
          Text('${body['blanks']} khaali jagah aap / vakil bharenge.', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: kind == 'publish' ? 'Haan, public karo' : 'Haan', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? () {} : () => _decide(false)),
          ]),
        if (st == 'approved' && kind == 'message')
          Row(children: [
            Expanded(child: GlassButton(label: 'WhatsApp kholo', icon: Icons.open_in_new_rounded, height: 42, onTap: () => Native.openExternal(url: _s(res['wa'])))),
            const SizedBox(width: 8),
            GlassButton(label: 'Bhej diya', icon: Icons.check_rounded, height: 42, onTap: _sent),
          ]),
        if (st == 'approved' && _s(res['url']).isNotEmpty)
          GlassButton(label: 'Page kholo', icon: Icons.public_rounded, onTap: () => Native.openExternal(url: _s(res['url']))),
        if (st == 'approved' && _s(res['text']).isNotEmpty && kind == 'publish') const Caption('Text copy karke apne portal / status par khud daaliye.'),
        const Text('Hoola khud kuch post / send nahi karta, paise nahi leta.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// propagent_visit: a planned site visit with stops and times. Also in calls.
class PropagentVisitCard extends StatelessWidget {
  const PropagentVisitCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final v = _m(data['visit']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.directions_car_rounded, color: C.teal),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(v['number'])} · ${_s(v['day'])} · ${_s(v['lead_name']).isEmpty ? _s(v['lead']) : _s(v['lead_name'])}',
              style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(v['status'])),
        ]),
        for (final s in _list(v['stops']))
          Text('${_s(s['at'])}  ${_s(s['number'])} ${_s(s['title'])}${s['km'] != null ? ' (${s['km']} km)' : ''}'
              '${_s(s['feedback']).isEmpty ? '' : ' · ${_s(s['feedback'])}'}',
              style: const TextStyle(fontSize: 13)),
        if (v['route_known'] != true) const Text('Doori Maps se nahi: aapke kram mein.', style: TextStyle(fontSize: 11.5, color: C.faint)),
        if (_s(data['say']).isNotEmpty) Text(_s(data['say']), style: const TextStyle(fontSize: 12, color: C.muted)),
      ]),
    );
  }
}

/// propagent_alert: visit reminder / RERA renewal. Also in calls.
class PropagentAlertCard extends StatelessWidget {
  const PropagentAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Row(children: [
          Icon(_s(data['kind']) == 'rera' ? Icons.badge_rounded : Icons.alarm_rounded, color: C.warn),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
        ]),
      );
}

/// propagent_day: the morning note. Not in calls.
class PropagentDayCard extends StatelessWidget {
  const PropagentDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.home_work_rounded, color: C.accent),
            SizedBox(width: 8),
            Text('Property ka aaj', style: TextStyle(fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.35)),
          const SizedBox(height: 6),
          GlassButton(
              label: 'Kholo',
              icon: Icons.open_in_new_rounded,
              height: 40,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PropagentScreen(app: app)))),
        ]),
      );
}
