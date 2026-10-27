/// Profile > Photo Sahayak: Hoola as a photographer's assistant (wedding / event / product / portrait).
/// Aaj (today / tomorrow's shoots, prep, holds ending, instalments, deliveries, cards waiting) · Shoots (book, free check)
/// · Studio (packages at HER prices, gear register incl. drone UIN / insurance) · Niyam (GST, travel gap, hold hours, delivery
/// days, copyright line, payment schedule, refund table, drone RPC).
/// Quote / terms / invoice / gallery delivery / any client message, hold -> confirmed, payment requests, discounts and refunds
/// (fingerprint once a phone key is set up) run only after HER tap. A double-booked shooter is refused by the server.
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
String _rs(dynamic v) => v == null ? '[daam?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';
const _p = '/api/photoassist';

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
                maxLines: (k == 'text' || k == 'terms' || k == 'notes' || k == 'ask' || k == 'includes') ? 3 : 1),
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

Widget _shootTile(BuildContext context, Santosh app, Map<String, dynamic> b, VoidCallback reload) => Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        child: InkWell(
          onTap: () => Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => PhotoassistShootPage(app: app, ref: _s(b['number']))))
              .then((_) => reload()),
          child: Row(children: [
            const Icon(Icons.photo_camera_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(b['number'])} · ${_s(b['kind_label'])} · ${_s(b['client'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text('${_s(b['day'])}${_s(b['end_day']).isNotEmpty ? ' – ${_s(b['end_day'])}' : ''} '
                  '${_s(b['start']).isEmpty ? 'pura din' : '${_s(b['start'])}-${_s(b['end'])}'} · ${_s(b['location'])}',
                  style: const TextStyle(fontSize: 12, color: C.muted)),
            ])),
            Pill(_s(b['status_label'])),
          ]),
        ),
      ),
    );

class PhotoassistScreen extends StatefulWidget {
  const PhotoassistScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PhotoassistScreen> createState() => _PhotoassistScreenState();
}

class _PhotoassistScreenState extends State<PhotoassistScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _free;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', _p));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(String method, String path, [Object? body]) async {
    await _call(context, widget.app, method, path, body);
    await _load();
  }

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('AAPKI HAAN KA INTEZAAR'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: PhotoassistCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('today', 'AAJ KE SHOOT'), ('tomorrow', 'KAL KE SHOOT'), ('holds_expiring', 'HOLD KHATAM HONE WALE')])
        if (_list(day[k]).isNotEmpty) ...[
          Caption(label),
          for (final b in _list(day[k])) _shootTile(context, widget.app, b, _load),
          const SizedBox(height: 8),
        ],
      for (final (k, label) in const [('prep', 'KAL KI TAIYAARI'), ('stages_due', 'KISHT KA SAMAY'), ('deliveries', 'DELIVERY')])
        if (_strs(day[k]).isNotEmpty) ...[Caption(label), for (final x in _strs(day[k])) Text('• $x'), const SizedBox(height: 8)],
    ]);
  }

  Future<void> _newShoot() async {
    final f = await _form(context, 'Naya shoot', const [
      ('kind', 'Kis cheez ka (shaadi / pre-wedding / product / portrait ...)'),
      ('client', 'Client ka naam'), ('phone', 'Client ka phone'), ('day', 'Tareekh (2026-12-12)'),
      ('end_day', 'Aakhri din (kai din ka ho to)'), ('start', 'Shuru (shaam 4 baje)'), ('end', 'Khatam'),
      ('location', 'Jagah'), ('package', 'Package ka naam'), ('shooters', 'Kaun jayega (naam, comma se; khaali = aap)'),
      ('drone', 'Drone? (haan / nahi)'),
    ]);
    if (f == null) return;
    final body = <String, dynamic>{...f};
    body.remove('package');
    body.remove('drone');
    if ((f['package'] ?? '').isNotEmpty) body['lines'] = [{'package': f['package']}];
    if ((f['shooters'] ?? '').isNotEmpty) body['shooters'] = f['shooters']!.split(',').map((e) => e.trim()).toList();
    if ((f['drone'] ?? '').toLowerCase().startsWith('h')) body['drone'] = true;
    await _run('POST', '$_p/shoots', body);
  }

  Future<void> _checkFree() async {
    final f = await _form(context, 'Khaali hai?', const [('day', 'Tareekh'), ('start', 'Shuru'), ('end', 'Khatam'), ('shooter', 'Kaun (khaali = aap)')]);
    if (f == null) return;
    try {
      final r = _m(await widget.app.api!.call('GET', '$_p/free', query: {
        'day': f['day'] ?? '', 'start': f['start'] ?? '', 'end': f['end'] ?? '', 'shooter': f['shooter'] ?? 'main'}));
      if (mounted) setState(() => _free = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _shoots() => ListView(padding: const EdgeInsets.all(16), children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GradientButton(label: 'Naya shoot', icon: Icons.add_rounded, height: 44, onTap: _newShoot),
          GlassButton(label: 'Khaali hai?', icon: Icons.event_available_rounded, height: 44, onTap: _checkFree),
        ]),
        if (_free != null) ...[
          const SizedBox(height: 10),
          Glass(border: _free!['free'] == true ? C.ok : C.bad, child: Text(_s(_free!['say']))),
        ],
        const SizedBox(height: 12),
        for (final b in _list(_d?['shoots'])) _shootTile(context, widget.app, b, _load),
        const Text('Ek photographer ka ek samay par ek hi shoot: server double booking mana karta hai (safar ka gap bhi).',
            style: TextStyle(fontSize: 11.5, color: C.faint)),
      ]);

  Widget _studio() => ListView(padding: const EdgeInsets.all(16), children: [
        const Caption('PACKAGE (AAPKE DAAM)'),
        for (final p in _list(_d?['packages']))
          Glass(margin: const EdgeInsets.only(bottom: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(p['name'])} · ${_s(p['price_text'])} / ${_s(p['unit'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            if (_strs(p['includes']).isNotEmpty) Text(_strs(p['includes']).join(', '), style: const TextStyle(fontSize: 12, color: C.muted)),
            if ((p['edits'] ?? 0) != 0) Text('${p['edits']} edited photo shaamil', style: const TextStyle(fontSize: 12, color: C.muted)),
          ])),
        GlassButton(label: 'Package jodo', icon: Icons.add_rounded, height: 42, onTap: () async {
          final f = await _form(context, 'Package', const [('name', 'Naam'), ('price', 'Daam (GST se pehle)'),
            ('unit', 'shoot / day / hour / photo'), ('includes', 'Kya shaamil (comma se)'), ('edits', 'Kitne edited photo shaamil')]);
          if (f == null) return;
          await _run('POST', '$_p/packages', {...f, if (f['price'] != null) 'price': _n(f['price']), if (f['edits'] != null) 'edits': _n(f['edits'])});
        }),
        const SizedBox(height: 16),
        const Caption('GEAR'),
        for (final g in _list(_d?['gear']))
          ListTile(
            leading: Icon(_s(g['kind']) == 'drone' ? Icons.flight_rounded : Icons.camera_alt_rounded, color: C.accent),
            title: Text(_s(g['name'])),
            subtitle: Text([
              _s(g['kind']),
              if (_s(g['serial']).isNotEmpty) 'SN ${_s(g['serial'])}',
              if (_s(g['uin']).isNotEmpty) 'UIN ${_s(g['uin'])}',
              if (g['weight_g'] != null) '${g['weight_g']} g',
              if (_s(g['insured_until']).isNotEmpty) 'insurance ${_s(g['insured_until'])}',
            ].join(' · ')),
          ),
        GlassButton(label: 'Gear jodo', icon: Icons.add_rounded, height: 42, onTap: () async {
          final f = await _form(context, 'Gear', const [('name', 'Naam (Sony A7 IV, DJI Mini 4...)'),
            ('kind', 'camera / lens / flash / light / drone / battery / card / stand'), ('serial', 'Serial'),
            ('uin', 'Drone UIN (Digital Sky)'), ('weight_g', 'Drone vazan gram'), ('insured_until', 'Insurance kab tak')]);
          if (f == null) return;
          await _run('POST', '$_p/gear', {...f, if (f['weight_g'] != null) 'weight_g': _n(f['weight_g'])});
        }),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['studio']).isEmpty ? 'Studio ka naam nahi' : _s(st['studio']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('GST: ${st['gst_on'] == true ? '${st['gst_pct']}% (GSTIN ${_s(st['gstin'])})' : 'nahi (GSTIN nahi)'}'),
        Text('UPI: ${_s(st['upi_id']).isEmpty ? '-' : _s(st['upi_id'])}'),
        Text('Safar ka gap ${_s(st['buffer_minutes'])} min · hold ${_s(st['hold_hours'])} ghante · delivery ${_s(st['delivery_days'])} din'),
        Text('Copyright: ${_s(st['copyright']) == 'client' ? 'client ka' : 'aapka (client ko niji licence)'}'),
        if (_s(st['rpc_number']).isNotEmpty) Text('Drone RPC ${_s(st['rpc_number'])} · ${_s(st['rpc_until'])} tak'),
        const SizedBox(height: 6),
        for (final x in _strs(st['cancel_lines'])) Text('• $x', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(st['unfair']).isNotEmpty) Text(_s(st['unfair']), style: const TextStyle(fontSize: 12, color: C.warn)),
      ])),
      const SizedBox(height: 10),
      GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 44, onTap: () async {
        final f = await _form(context, 'Niyam', const [('studio', 'Studio'), ('gstin', 'GSTIN'), ('upi_id', 'UPI ID'),
          ('phone', 'Phone'), ('address', 'Pata'), ('buffer_minutes', 'Do shoot ke beech safar (min)'), ('hold_hours', 'Hold kitne ghante'),
          ('delivery_days', 'Delivery kitne din mein'), ('retention_days', 'Delivery ke baad raw kitne din'),
          ('copyright', 'keep (aapka) / client'), ('rpc_number', 'Drone RPC number'), ('rpc_until', 'RPC kab tak'),
          ('morning_time', 'Subah ka note (08:00)'), ('terms', 'Baaki shartein')], initial: {
          for (final k in const ['studio', 'gstin', 'upi_id', 'phone', 'address', 'copyright', 'rpc_number', 'rpc_until', 'morning_time',
            'terms', 'buffer_minutes', 'hold_hours', 'delivery_days', 'retention_days']) k: _s(st[k]),
        });
        if (f == null) return;
        await _run('PUT', '$_p/settings', f);
      }),
      const SizedBox(height: 10),
      const Text('Copyright Act s.17(b): likhit samjhaute ke bina paise dekar khinchwai photo ka pehla maalik client hota hai. '
          'Isliye booking terms mein copyright line aur portfolio ki alag haan rakhi hai. Yeh kaanooni salaah nahi.',
          style: TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Shoots', 'Studio', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Photo Sahayak'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _shoots, _studio, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

class PhotoassistShootPage extends StatefulWidget {
  const PhotoassistShootPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<PhotoassistShootPage> createState() => _PhotoassistShootPageState();
}

class _PhotoassistShootPageState extends State<PhotoassistShootPage> {
  Map<String, dynamic>? _v;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _sp => '$_p/shoots/${widget.ref}';

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', _sp));
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(String what, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, 'POST', '$_sp/$what', body ?? <String, dynamic>{});
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _cull() async {
    try {
      final xs = await ImagePicker().pickMultiImage(imageQuality: 85, maxWidth: 1600);
      if (xs.isEmpty) return;
      setState(() => _busy = true);
      var n = 0;
      for (final x in xs.take(40)) {
        final bytes = await x.readAsBytes();
        await widget.app.api!.uploadFile('$_sp/cull', x.name.isEmpty ? 'photo.jpg' : x.name, bytes,
            timeout: const Duration(seconds: 90), tries: 2);
        n++;
      }
      if (mounted) _snack(context, '$n photo dekhi: sirf ishaare, chunav aapka.');
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _proof(String rid) async {
    try {
      final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 85, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      final r = await widget.app.api!.uploadFile('$_p/releases/$rid/proof', 'release.jpg', bytes, tries: 2);
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _pickFor(Map<String, dynamic> p) async {
    final ch = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (c) => Wrap(children: [
        ListTile(title: Text(_s(p['name'])), subtitle: Text(_strs(p['why']).join(' · '))),
        for (final (k, l) in const [('keep', 'Rakho'), ('maybe', 'Shak'), ('reject', 'Hatao'), ('edit', 'Edit karna hai')])
          ListTile(title: Text(l), onTap: () => Navigator.pop(c, k)),
      ]),
    );
    if (ch == null || !mounted) return;
    await _call(context, widget.app, 'POST', '$_p/photos/pick', {'ids': [p['id']], 'choice': ch});
    await _load();
  }

  Widget _photoGrid(List<Map<String, dynamic>> photos) {
    final api = widget.app.api!;
    return Wrap(spacing: 6, runSpacing: 6, children: [
      for (final p in photos)
        GestureDetector(
          onTap: () => _pickFor(p),
          child: Stack(children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.network(api.absolute('$_p/photos/${_s(p['id'])}'), headers: api.authHeaders, width: 96, height: 96,
                  fit: BoxFit.cover, cacheWidth: 200,
                  errorBuilder: (_, __, ___) => Container(width: 96, height: 96, color: C.panel)),
            ),
            Positioned(
              left: 4,
              bottom: 4,
              child: Pill(_s(p['pick']).isNotEmpty ? _s(p['pick']) : '~${_s(p['hint'])}',
                  fg: switch (_s(p['pick']).isNotEmpty ? _s(p['pick']) : _s(p['hint'])) { 'keep' => C.ok, 'reject' => C.bad, _ => C.warn },
                  bg: const Color(0xCC000000)),
            ),
          ]),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    if (v == null) {
      return const Scaffold(backgroundColor: C.bgTop, body: Center(child: CircularProgressIndicator()));
    }
    final q = _m(v['quote']);
    final st = _s(v['status']);
    final edits = _m(v['edits']);
    final shotList = _list(v['shot_list']);
    final gearList = _list(v['gear_list']);
    final editRows = _list(edits['rows']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${_s(v['number'])} · ${_s(v['kind_label'])}')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(v['client'])} · ${_s(v['phone'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
            Text('${_s(v['day'])}${_s(v['end_day']).isNotEmpty ? ' – ${_s(v['end_day'])}' : ''} '
                '${_s(v['start']).isEmpty ? 'pura din' : '${_s(v['start'])}-${_s(v['end'])}'} · ${_s(v['location'])}'),
            Text('Kaun: ${_strs(v['shooters']).join(', ')} · ${_s(v['status_label'])} · delivery ${_s(v['delivery_due'])} tak',
                style: const TextStyle(fontSize: 12, color: C.muted)),
            const SizedBox(height: 6),
            for (final l in _list(q['lines'])) Text('• ${_s(l['name'])} x${_s(l['qty'])} = ${_rs(l['amount'])}'),
            Text('Total ${_s(q['total_text'])} · jama ${_rs(v['paid'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            if (_s(q['tds_note']).isNotEmpty) Text(_s(q['tds_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ])),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (st == 'draft') GlassButton(label: 'Hold', height: 40, onTap: _busy ? () {} : () => _do('hold')),
            if (st == 'hold') GlassButton(label: 'Hold chhodo', height: 40, onTap: _busy ? () {} : () => _do('release')),
            if (st == 'draft' || st == 'hold')
              GradientButton(label: 'Pakka karo (card)', height: 40, onTap: _busy ? null : () => _do('confirm')),
            GlassButton(label: 'Quotation (card)', height: 40, onTap: () => _do('quote')),
            GlassButton(label: 'Terms (card)', height: 40, onTap: () => _do('contract')),
            if (st == 'confirmed' || st == 'shot') GlassButton(label: 'Paise maango (card)', height: 40, onTap: () => _do('pay')),
            if (st == 'confirmed') GlassButton(label: 'Shoot ho gaya', height: 40, onTap: () => _do('shot')),
            if (st == 'shot' || st == 'delivered')
              GlassButton(label: 'Gallery bhejo (card)', height: 40, onTap: () async {
                final f = await _form(context, 'Aapka gallery link', const [('link', 'https:// link (Drive / gallery)'),
                  ('what', 'Kya hai (400 photos, album)'), ('expires', 'Link kab tak')]);
                if (f != null) await _do('delivery', f);
              }),
            GlassButton(label: 'Invoice (card)', height: 40, onTap: () => _do('invoice')),
            GlassButton(label: 'Paise mile', height: 40, onTap: () async {
              final f = await _form(context, 'Paise mile', const [('amount', 'Kitne'), ('mode', 'upi / cash / bank'), ('ref', 'UTR (aakhri ank)')]);
              if (f != null) await _do('paid', {...f, 'amount': _n(f['amount'])});
            }),
            GlassButton(label: 'Message (card)', height: 40, onTap: () async {
              final f = await _form(context, 'Client ko message', const [('text', 'Message')]);
              if (f != null) await _do('message', f);
            }),
            if (st != 'cancelled' && st != 'done')
              GlassButton(label: 'Radd', height: 40, color: C.bad, onTap: () async {
                final f = await _form(context, 'Radd karna', const [('reason', 'Wajah'), ('by', 'client / studio')], ok: 'Radd karo');
                if (f != null) await _do('cancel', f);
              }),
          ]),
          const SizedBox(height: 14),
          const Caption('JAANCH (PERMISSION / DRONE / BACHCHE)'),
          for (final c in _list(v['checks']))
            CheckboxListTile(
              value: c['done'] == true,
              dense: true,
              onChanged: (x) => _do('check', {'key': c['key'], 'done': x == true}),
              title: Text(_s(c['say']), style: TextStyle(fontSize: 12.5, color: _s(c['level']) == 'warn' ? C.warn : C.ink)),
            ),
          const Caption('SHOT LIST'),
          for (var i = 0; i < shotList.length; i++)
            CheckboxListTile(
              value: shotList[i]['done'] == true,
              dense: true,
              onChanged: (_) => _do('shots', {'tick': ['${i + 1}']}),
              title: Text('${_s(shotList[i]['item'])}${shotList[i]['must'] == true ? ' *' : ''}'),
            ),
          TextButton(onPressed: () async {
            final f = await _form(context, 'Shot jodo', const [('add', 'Shot')]);
            if (f != null) await _do('shots', {'add': [f['add']]});
          }, child: const Text('+ shot jodo')),
          const Caption('GEAR CHECKLIST'),
          for (var i = 0; i < gearList.length; i++)
            CheckboxListTile(
              value: gearList[i]['packed'] == true,
              dense: true,
              onChanged: (_) => _do('gear', {'tick': ['${i + 1}']}),
              title: Text(_s(gearList[i]['item']), style: TextStyle(color: gearList[i]['missing'] == true ? C.warn : C.ink)),
            ),
          const Caption('RELEASE / CONSENT'),
          for (final r in _list(v['releases']))
            ListTile(
              title: Text('${_s(r['kind'])}: ${_s(r['person'])}${_s(r['guardian']).isNotEmpty ? ' (guardian ${_s(r['guardian'])})' : ''}'),
              subtitle: Text('${_s(r['status'])} · ${_strs(r['uses']).join(', ')}'),
              trailing: _s(r['status']) == 'draft'
                  ? IconButton(icon: const Icon(Icons.photo_camera_rounded), tooltip: 'Sign kiye form ki photo', onPressed: () => _proof(_s(r['id'])))
                  : (_s(r['status']) == 'signed'
                      ? TextButton(
                          onPressed: () async {
                            await _call(context, widget.app, 'POST', '$_p/releases/${_s(r['id'])}/withdraw');
                            await _load();
                          },
                          child: const Text('Wapas'))
                      : null),
            ),
          TextButton(onPressed: () async {
            final f = await _form(context, 'Nayi release', const [('kind', 'model / minor / property'), ('person', 'Naam'),
              ('guardian', 'Bachche ke liye maa / pita'), ('place', 'Property ka pata'), ('uses', 'portfolio, social_media, advertising'),
              ('lang', 'en / hi')]);
            if (f != null) {
              await _do('release_new', {...f, 'uses': (f['uses'] ?? 'portfolio').split(',').map((e) => e.trim()).toList()});
            }
          }, child: const Text('+ release banao')),
          const Caption('CULLING (SIRF ISHAARE)'),
          _photoGrid(_list(v['photos'])),
          TextButton(onPressed: _busy ? null : _cull, child: const Text('+ photos dikhao')),
          Caption('EDITS (${_s(edits['used'])} / package ${_s(edits['included'])})'),
          for (var i = 0; i < editRows.length; i++)
            ListTile(
              dense: true,
              title: Text('${_s(editRows[i]['photo'])}: ${_s(editRows[i]['ask'])}'),
              subtitle: Text(_s(editRows[i]['status'])),
              trailing: _s(editRows[i]['status']) == 'done'
                  ? null
                  : TextButton(onPressed: () => _do('edit', {'index': i + 1, 'status': 'done'}), child: const Text('Ho gaya')),
            ),
          TextButton(onPressed: () async {
            final f = await _form(context, 'Client ka edit', const [('photo', 'Photo ka naam'), ('ask', 'Kya badalna hai')]);
            if (f != null) await _do('edit', f);
          }, child: const Text('+ edit jodo')),
          const Caption('CARDS'),
          for (final c in _list(v['cards']))
            Padding(padding: const EdgeInsets.only(bottom: 8), child: PhotoassistCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
        ]),
      ),
    );
  }
}

/// photoassist_card: everything that waits for HER tap (quote, terms, hold -> confirmed, payment request, gallery delivery,
/// invoice, message, discount*, refund*). *money cards: fingerprint once a phone key is set up (428 -> /challenge -> sign).
class PhotoassistCardCard extends StatefulWidget {
  const PhotoassistCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<PhotoassistCardCard> createState() => _PhotoassistCardCardState();
}

class _PhotoassistCardCardState extends State<PhotoassistCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '$_p/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Photo Sahayak' : _s(show['title']),
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
        r = await widget.app.api!.call('POST', '$_p/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '$_p/cards/$id/decide', body: {...body, 'proof': proof});
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
            'quote' => Icons.request_quote_rounded,
            'contract' => Icons.article_rounded,
            'confirm' => Icons.verified_rounded,
            'discount' => Icons.percent_rounded,
            'refund' => Icons.undo_rounded,
            'pay' => Icons.currency_rupee_rounded,
            'invoice' => Icons.receipt_long_rounded,
            'delivery' => Icons.photo_library_rounded,
            _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['shoot'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(sh['client'])} · ${_s(sh['kind'])} · ${_s(sh['day'])} ${_s(sh['time'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (_s(sh['label']).isNotEmpty) Text(_s(sh['label'])),
        if (_s(sh['link']).isNotEmpty) Text(_s(sh['link']), style: const TextStyle(fontSize: 12, color: C.teal)),
        for (final w in _strs(sh['warn'])) Text('• $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(sh['reason']).isNotEmpty) Text('Wajah: ${_s(sh['reason'])}', style: const TextStyle(fontSize: 12)),
        if (_s(sh['why']).isNotEmpty) Text(_s(sh['why']), style: const TextStyle(fontSize: 12)),
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        if (_s(sh['copyright_text']).isNotEmpty) Text(_s(sh['copyright_text']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
        if (kind == 'quote' || kind == 'contract')
          for (final x in _strs(sh['cancel_lines'])) Text('• $x', style: const TextStyle(fontSize: 11.5, color: C.muted)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Haan (fingerprint)' : 'Haan', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? () {} : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola khud kuch nahi bhejta, paise nahi leta / deta: message aap bhejti hain.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// photoassist_alert / photoassist_day: notes (hold ending, shoot tomorrow, instalment, delivery due, retention, drone papers).
class PhotoassistNoteCard extends StatelessWidget {
  const PhotoassistNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final shoot = _s(data['shoot']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.photo_camera_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
          if (shoot.isNotEmpty)
            TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhotoassistShootPage(app: app, ref: shoot))),
              child: Text('$shoot kholo'),
            ),
        ])),
      ]),
    );
  }
}
