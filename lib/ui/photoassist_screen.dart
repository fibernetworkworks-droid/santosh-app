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
String _rs(dynamic v) => v == null ? '[price?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';
const _p = '/api/photoassist';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Next', Map<String, String> initial = const {}}) async {
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
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
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
    if (upi.isNotEmpty) const Pill('UPI link for your UPI ID'),
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
                  '${_s(b['start']).isEmpty ? 'all day' : '${_s(b['start'])}-${_s(b['end'])}'} · ${_s(b['location'])}',
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
      if (_list(_d?['cards']).isNotEmpty) const Caption('WAITING FOR YOUR YES'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: PhotoassistCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('today', 'TODAY\'S SHOOTS'), ('tomorrow', 'TOMORROW\'S SHOOTS'), ('holds_expiring', 'HOLDS EXPIRING')])
        if (_list(day[k]).isNotEmpty) ...[
          Caption(label),
          for (final b in _list(day[k])) _shootTile(context, widget.app, b, _load),
          const SizedBox(height: 8),
        ],
      for (final (k, label) in const [('prep', 'TOMORROW\'S PREPARATION'), ('stages_due', 'INSTALMENT DUE'), ('deliveries', 'DELIVERY')])
        if (_strs(day[k]).isNotEmpty) ...[Caption(label), for (final x in _strs(day[k])) Text('• $x'), const SizedBox(height: 8)],
    ]);
  }

  Future<void> _newShoot() async {
    final f = await _form(context, 'New shoot', const [
      ('kind', 'What for (wedding / pre-wedding / product / portrait ...)'),
      ('client', 'Client name'), ('phone', 'Client ka phone'), ('day', 'Date (2026-12-12)'),
      ('end_day', 'Last day (if it runs several days)'), ('start', 'Start (4 pm)'), ('end', 'End'),
      ('location', 'Location'), ('package', 'Package name'), ('shooters', 'Who will go (names, comma separated; blank = you)'),
      ('drone', 'Drone? (yes / no)'),
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
    final f = await _form(context, 'Is it free?', const [('day', 'Date'), ('start', 'Start'), ('end', 'End'), ('shooter', 'Who (blank = you)')]);
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
          GradientButton(label: 'New shoot', icon: Icons.add_rounded, height: 44, onTap: _newShoot),
          GlassButton(label: 'Is it free?', icon: Icons.event_available_rounded, height: 44, onTap: _checkFree),
        ]),
        if (_free != null) ...[
          const SizedBox(height: 10),
          Glass(border: _free!['free'] == true ? C.ok : C.bad, child: Text(_s(_free!['say']))),
        ],
        const SizedBox(height: 12),
        for (final b in _list(_d?['shoots'])) _shootTile(context, widget.app, b, _load),
        const Text('One photographer, one shoot at a time: the server blocks double booking (travel gap included).',
            style: TextStyle(fontSize: 11.5, color: C.faint)),
      ]);

  Widget _studio() => ListView(padding: const EdgeInsets.all(16), children: [
        const Caption('PACKAGES (YOUR PRICES)'),
        for (final p in _list(_d?['packages']))
          Glass(margin: const EdgeInsets.only(bottom: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(p['name'])} · ${_s(p['price_text'])} / ${_s(p['unit'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            if (_strs(p['includes']).isNotEmpty) Text(_strs(p['includes']).join(', '), style: const TextStyle(fontSize: 12, color: C.muted)),
            if ((p['edits'] ?? 0) != 0) Text('${p['edits']} edited photos included', style: const TextStyle(fontSize: 12, color: C.muted)),
          ])),
        GlassButton(label: 'Add package', icon: Icons.add_rounded, height: 42, onTap: () async {
          final f = await _form(context, 'Package', const [('name', 'Name'), ('price', 'Price (before GST)'),
            ('unit', 'shoot / day / hour / photo'), ('includes', 'What is included (comma separated)'), ('edits', 'How many edited photos included')]);
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
        GlassButton(label: 'Add gear', icon: Icons.add_rounded, height: 42, onTap: () async {
          final f = await _form(context, 'Gear', const [('name', 'Name (Sony A7 IV, DJI Mini 4...)'),
            ('kind', 'camera / lens / flash / light / drone / battery / card / stand'), ('serial', 'Serial'),
            ('uin', 'Drone UIN (Digital Sky)'), ('weight_g', 'Drone weight (grams)'), ('insured_until', 'Insurance valid until')]);
          if (f == null) return;
          await _run('POST', '$_p/gear', {...f, if (f['weight_g'] != null) 'weight_g': _n(f['weight_g'])});
        }),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['studio']).isEmpty ? 'No studio name' : _s(st['studio']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('GST: ${st['gst_on'] == true ? '${st['gst_pct']}% (GSTIN ${_s(st['gstin'])})' : 'no (no GSTIN)'}'),
        Text('UPI: ${_s(st['upi_id']).isEmpty ? '-' : _s(st['upi_id'])}'),
        Text('Travel gap ${_s(st['buffer_minutes'])} min · hold ${_s(st['hold_hours'])} hours · delivery ${_s(st['delivery_days'])} days'),
        Text('Copyright: ${_s(st['copyright']) == 'client' ? 'the client\'s' : 'yours (private licence to the client)'}'),
        if (_s(st['rpc_number']).isNotEmpty) Text('Drone RPC ${_s(st['rpc_number'])} · until ${_s(st['rpc_until'])}'),
        const SizedBox(height: 6),
        for (final x in _strs(st['cancel_lines'])) Text('• $x', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(st['unfair']).isNotEmpty) Text(_s(st['unfair']), style: const TextStyle(fontSize: 12, color: C.warn)),
      ])),
      const SizedBox(height: 10),
      GlassButton(label: 'Change', icon: Icons.edit_rounded, height: 44, onTap: () async {
        final f = await _form(context, 'Rules', const [('studio', 'Studio'), ('gstin', 'GSTIN'), ('upi_id', 'UPI ID'),
          ('phone', 'Phone'), ('address', 'Address'), ('buffer_minutes', 'Travel between two shoots (min)'), ('hold_hours', 'Hold for how many hours'),
          ('delivery_days', 'Delivery within how many days'), ('retention_days', 'Days to keep raw files after delivery'),
          ('copyright', 'keep (yours) / client'), ('rpc_number', 'Drone RPC number'), ('rpc_until', 'RPC valid until'),
          ('morning_time', 'Morning note (08:00)'), ('terms', 'Other terms')], initial: {
          for (final k in const ['studio', 'gstin', 'upi_id', 'phone', 'address', 'copyright', 'rpc_number', 'rpc_until', 'morning_time',
            'terms', 'buffer_minutes', 'hold_hours', 'delivery_days', 'retention_days']) k: _s(st[k]),
        });
        if (f == null) return;
        await _run('PUT', '$_p/settings', f);
      }),
      const SizedBox(height: 10),
      const Text('Copyright Act s.17(b): without a written agreement, the client who paid for the photographs is the first owner. '
          'That is why the booking terms keep a copyright line and a separate yes for the portfolio. This is not legal advice.',
          style: TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Today', 'Shoots', 'Studio', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Photo Assistant'),
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
      if (mounted) _snack(context, 'Looked at $n photos: only hints, the choice is yours.');
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
        for (final (k, l) in const [('keep', 'Keep'), ('maybe', 'Maybe'), ('reject', 'Remove'), ('edit', 'Needs editing')])
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
                '${_s(v['start']).isEmpty ? 'all day' : '${_s(v['start'])}-${_s(v['end'])}'} · ${_s(v['location'])}'),
            Text('Who: ${_strs(v['shooters']).join(', ')} · ${_s(v['status_label'])} · delivery by ${_s(v['delivery_due'])}',
                style: const TextStyle(fontSize: 12, color: C.muted)),
            const SizedBox(height: 6),
            for (final l in _list(q['lines'])) Text('• ${_s(l['name'])} x${_s(l['qty'])} = ${_rs(l['amount'])}'),
            Text('Total ${_s(q['total_text'])} · jama ${_rs(v['paid'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            if (_s(q['tds_note']).isNotEmpty) Text(_s(q['tds_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ])),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (st == 'draft') GlassButton(label: 'Hold', height: 40, onTap: _busy ? () {} : () => _do('hold')),
            if (st == 'hold') GlassButton(label: 'Release hold', height: 40, onTap: _busy ? () {} : () => _do('release')),
            if (st == 'draft' || st == 'hold')
              GradientButton(label: 'Confirm (card)', height: 40, onTap: _busy ? null : () => _do('confirm')),
            GlassButton(label: 'Quotation (card)', height: 40, onTap: () => _do('quote')),
            GlassButton(label: 'Terms (card)', height: 40, onTap: () => _do('contract')),
            if (st == 'confirmed' || st == 'shot') GlassButton(label: 'Ask for payment (card)', height: 40, onTap: () => _do('pay')),
            if (st == 'confirmed') GlassButton(label: 'Shoot done', height: 40, onTap: () => _do('shot')),
            if (st == 'shot' || st == 'delivered')
              GlassButton(label: 'Send gallery (card)', height: 40, onTap: () async {
                final f = await _form(context, 'Your gallery link', const [('link', 'https:// link (Drive / gallery)'),
                  ('what', 'What it is (400 photos, album)'), ('expires', 'Link valid until')]);
                if (f != null) await _do('delivery', f);
              }),
            GlassButton(label: 'Invoice (card)', height: 40, onTap: () => _do('invoice')),
            GlassButton(label: 'Payment received', height: 40, onTap: () async {
              final f = await _form(context, 'Payment received', const [('amount', 'How many'), ('mode', 'upi / cash / bank'), ('ref', 'UTR (last digits)')]);
              if (f != null) await _do('paid', {...f, 'amount': _n(f['amount'])});
            }),
            GlassButton(label: 'Message (card)', height: 40, onTap: () async {
              final f = await _form(context, 'Client ko message', const [('text', 'Message')]);
              if (f != null) await _do('message', f);
            }),
            if (st != 'cancelled' && st != 'done')
              GlassButton(label: 'Cancel', height: 40, color: C.bad, onTap: () async {
                final f = await _form(context, 'Cancel', const [('reason', 'Reason'), ('by', 'client / studio')], ok: 'Cancel it');
                if (f != null) await _do('cancel', f);
              }),
          ]),
          const SizedBox(height: 14),
          const Caption('CHECKS (PERMISSION / DRONE / CHILDREN)'),
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
            final f = await _form(context, 'Add shot', const [('add', 'Shot')]);
            if (f != null) await _do('shots', {'add': [f['add']]});
          }, child: const Text('+ add shot')),
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
                  ? IconButton(icon: const Icon(Icons.photo_camera_rounded), tooltip: 'Photo of the signed form', onPressed: () => _proof(_s(r['id'])))
                  : (_s(r['status']) == 'signed'
                      ? TextButton(
                          onPressed: () async {
                            await _call(context, widget.app, 'POST', '$_p/releases/${_s(r['id'])}/withdraw');
                            await _load();
                          },
                          child: const Text('Returned'))
                      : null),
            ),
          TextButton(onPressed: () async {
            final f = await _form(context, 'New release', const [('kind', 'model / minor / property'), ('person', 'Name'),
              ('guardian', 'Parent / guardian for a child'), ('place', 'Property address'), ('uses', 'portfolio, social_media, advertising'),
              ('lang', 'en / hi')]);
            if (f != null) {
              await _do('release_new', {...f, 'uses': (f['uses'] ?? 'portfolio').split(',').map((e) => e.trim()).toList()});
            }
          }, child: const Text('+ Make release')),
          const Caption('CULLING (HINTS ONLY)'),
          _photoGrid(_list(v['photos'])),
          TextButton(onPressed: _busy ? null : _cull, child: const Text('+ Show photos')),
          Caption('EDITS (${_s(edits['used'])} / package ${_s(edits['included'])})'),
          for (var i = 0; i < editRows.length; i++)
            ListTile(
              dense: true,
              title: Text('${_s(editRows[i]['photo'])}: ${_s(editRows[i]['ask'])}'),
              subtitle: Text(_s(editRows[i]['status'])),
              trailing: _s(editRows[i]['status']) == 'done'
                  ? null
                  : TextButton(onPressed: () => _do('edit', {'index': i + 1, 'status': 'done'}), child: const Text('Done')),
            ),
          TextButton(onPressed: () async {
            final f = await _form(context, 'Client ka edit', const [('photo', 'Photo name'), ('ask', 'What should change')]);
            if (f != null) await _do('edit', f);
          }, child: const Text('+ add edit')),
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
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Photo Assistant' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'No fingerprint was given, so it was not approved.',
        'key_invalidated' => 'A new fingerprint was added to the phone: link this phone again in Profile > Fingerprint approval.',
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
          Pill(switch (st) { 'waiting' => 'your yes?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'old', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(sh['client'])} · ${_s(sh['kind'])} · ${_s(sh['day'])} ${_s(sh['time'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (_s(sh['label']).isNotEmpty) Text(_s(sh['label'])),
        if (_s(sh['link']).isNotEmpty) Text(_s(sh['link']), style: const TextStyle(fontSize: 12, color: C.teal)),
        for (final w in _strs(sh['warn'])) Text('• $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(sh['reason']).isNotEmpty) Text('Reason: ${_s(sh['reason'])}', style: const TextStyle(fontSize: 12)),
        if (_s(sh['why']).isNotEmpty) Text(_s(sh['why']), style: const TextStyle(fontSize: 12)),
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        if (_s(sh['copyright_text']).isNotEmpty) Text(_s(sh['copyright_text']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
        if (kind == 'quote' || kind == 'contract')
          for (final x in _strs(sh['cancel_lines'])) Text('• $x', style: const TextStyle(fontSize: 11.5, color: C.muted)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Yes (fingerprint)' : 'Yes', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'No', height: 42, onTap: _busy ? () {} : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola sends nothing by itself and does not pay or receive money: you send the messages.',
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
              child: Text('Open $shoot'),
            ),
        ])),
      ]),
    );
  }
}
