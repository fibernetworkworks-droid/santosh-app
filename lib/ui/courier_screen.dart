/// Profile > Courier sahayak (courier desk).
/// Aaj (cards waiting for her tap, NDR, RTO, pickups, COD) · Parcel (new parcel -> PIN + carrier's own rates -> booking card
/// that ONLY her tap books -> AWB + label; tracking in the carrier's words; NDR message + re-attempt card; return label) ·
/// COD (remittance sheet upload, pending / mismatch) · Niyam (pickup address, her courier rules, carrier keys typed only here).
/// Hoola never books, charges or touches COD money by itself.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
double _n(String? v) => double.tryParse((v ?? '').replaceAll(',', '').replaceAll('₹', '').trim()) ?? 0;

String _rs(dynamic v) {
  final d = v is num ? v.toDouble() : double.tryParse('$v') ?? 0;
  final whole = d.abs().truncate();
  var s = '$whole';
  if (s.length > 3) {
    final head = s.substring(0, s.length - 3);
    final tail = s.substring(s.length - 3);
    final b = StringBuffer();
    for (var i = 0; i < head.length; i++) {
      if (i > 0 && (head.length - i) % 2 == 0) b.write(',');
      b.write(head[i]);
    }
    s = '$b,$tail';
  }
  final paise = ((d.abs() - whole) * 100).round();
  return '${d < 0 ? '-' : ''}₹$s${paise > 0 ? '.${paise.toString().padLeft(2, '0')}' : ''}';
}

Color _statusColor(String st) => switch (st) {
      'exception' || 'rto' || 'failed' => C.bad,
      'delivered' => C.ok,
      'waiting' || 'draft' || 'manual' => C.warn,
      _ => C.teal,
    };

Future<dynamic> _call(Santosh app, String method, String path, {Object? body, Map<String, String>? query}) =>
    app.api!.call(method, path, body: body, query: query);

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {Map<String, String> init = const {}, bool secret = false}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: init[k] ?? '')};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(
              controller: c[k],
              obscureText: secret && (k.contains('password') || k.contains('secret') || k.contains('token') || k.contains('license')),
              decoration: InputDecoration(labelText: label),
            ),
          if (secret) ...[
            const SizedBox(height: 8),
            const Text('Chaabi band tijori mein rehti hai; Hoola ko bhi nahi dikhti. Chat mein kabhi mat likhiye.', style: TextStyle(fontSize: 12)),
          ],
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage')),
      ],
    ),
  );
  if (ok != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Future<void> _openLink(BuildContext context, String url) async {
  if (url.isEmpty) return;
  final r = await Native.openExternal(url: url);
  if (r.isNotEmpty && r != 'ok' && context.mounted) {
    await Clipboard.setData(ClipboardData(text: url));
    if (context.mounted) _snack(context, 'Link copy kar diya');
  }
}

/// Her tap on a courier card: hash of the card she saw + (for a card that may charge her wallet, once her phone key is
/// active) the fingerprint. Saying no never needs it.
Future<Map<String, dynamic>> courierDecide(Santosh app, Map<String, dynamic> card, bool yes, {String reason = ''}) async {
  final id = _s(card['id']);
  final body = <String, dynamic>{'yes': yes, 'hash': _s(card['hash']), if (reason.isNotEmpty) 'reason': reason};
  try {
    return _m(await _call(app, 'POST', '/api/courier/cards/$id/decide', body: body));
  } on ApiException catch (e) {
    if (!yes || e.status != 428) rethrow;
  }
  final proof = await app.api!.fingerprintProof('courier', id);
  return _m(await _call(app, 'POST', '/api/courier/cards/$id/decide', body: {...body, 'proof': proof}));
}

class CourierScreen extends StatefulWidget {
  const CourierScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CourierScreen> createState() => _CourierScreenState();
}

class _CourierScreenState extends State<CourierScreen> {
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _all = [];
  int _tab = 0;
  bool _busy = false;
  String _filter = 'active';
  final _q = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = _m(await _call(widget.app, 'GET', '/api/courier'));
      final all = _m(await _call(widget.app, 'GET', '/api/courier/parcels', query: {'status': _filter, 'q': _q.text.trim()}));
      if (mounted) {
        setState(() {
          _d = d;
          _all = _list(all['parcels']);
        });
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _m(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _open(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => CourierParcelPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newParcel() async {
    final f = await _form(context, 'Naya parcel', const [
      ('name', 'Graahak ka naam'),
      ('phone', 'Graahak ka mobile'),
      ('address', 'Poora pata'),
      ('city', 'Shehar'),
      ('state', 'Rajya'),
      ('pincode', 'PIN code'),
      ('items', 'Saamaan (jaise: Kurti x1 @ 899)'),
      ('payment', 'prepaid / cod'),
      ('cod_amount', 'COD rakam (₹)'),
      ('weight_kg', 'Asli wazan (kg)'),
      ('dims', 'Dabba L x B x H cm (jaise 30x25x5)'),
      ('order_ref', 'Order number'),
    ]);
    if (f == null) return;
    final dims = (f['dims'] ?? '').split(RegExp(r'[xX*× ]+')).map((e) => _n(e)).toList();
    final r = await _run(() => _call(widget.app, 'POST', '/api/courier/parcels', body: {
          'customer': {
            'name': f['name'] ?? '', 'phone': f['phone'] ?? '', 'address': f['address'] ?? '', 'city': f['city'] ?? '',
            'state': f['state'] ?? '', 'pincode': f['pincode'] ?? '',
          },
          'items': f['items'] ?? '',
          'payment': (f['payment'] ?? 'prepaid').toLowerCase(),
          if (f['cod_amount'] != null) 'cod_amount': _n(f['cod_amount']),
          if (f['weight_kg'] != null) 'weight_kg': _n(f['weight_kg']),
          if (dims.length == 3) 'dims': {'l': dims[0], 'b': dims[1], 'h': dims[2]},
          'order_ref': f['order_ref'] ?? '',
        }));
    final id = _s(_m(r?['parcel'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  Widget _tile(Map<String, dynamic> p) => Glass(
        margin: const EdgeInsets.only(bottom: 10),
        child: InkWell(
          onTap: () => _open(_s(p['id'])),
          child: Row(children: [
            Icon(p['kind'] == 'reverse' ? Icons.assignment_return_rounded : Icons.local_shipping_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(p['number'])} · ${_s(p['customer_name'])} ${_s(p['pincode'])}'.trim(), style: const TextStyle(fontWeight: FontWeight.w800)),
                if (_s(p['awb']).isNotEmpty) Text('${_s(p['carrier'])} · AWB ${_s(p['awb'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                if (_s(p['raw']).isNotEmpty) Text('Courier: ${_s(p['raw'])}', style: const TextStyle(fontSize: 12, color: C.faint), maxLines: 2, overflow: TextOverflow.ellipsis),
              ]),
            ),
            const SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Pill(_s(p['status_label']), fg: _statusColor(_s(p['status']))),
              if (p['payment'] == 'cod') Padding(padding: const EdgeInsets.only(top: 4), child: Text('COD ${_rs(p['cod_amount'])}', style: const TextStyle(fontSize: 11.5, color: C.warn))),
            ]),
          ]),
        ),
      );

  Widget _today() {
    final day = _m(_d?['day']);
    final parts = (day['parts'] as List?) ?? const [];
    final cards = _list(_d?['cards']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aaj', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 6),
          if (parts.isEmpty) const Text('Sab theek. Koi parcel aapka intezaar nahi kar raha.', style: TextStyle(color: C.muted)),
          for (final p in parts) Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $p')),
        ]),
      ),
      const SizedBox(height: 12),
      for (final c in cards)
        Padding(padding: const EdgeInsets.only(bottom: 10), child: CourierActionCard(app: widget.app, data: {'card': c}, onDone: _load)),
      Row(children: [
        Expanded(child: GradientButton(label: 'Naya parcel', icon: Icons.add_rounded, onTap: _busy ? null : _newParcel)),
        const SizedBox(width: 8),
        GlassButton(
          label: 'Manifest',
          icon: Icons.table_view_rounded,
          onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/courier/manifest/file')),
        ),
      ]),
      const SizedBox(height: 12),
      for (final p in _list(_d?['parcels']).take(20)) _tile(p),
    ]);
  }

  Widget _parcels() => ListView(padding: const EdgeInsets.all(16), children: [
        TextField(
          controller: _q,
          decoration: const InputDecoration(labelText: 'Dhoondho: P-0001 / AWB / order / phone / naam', prefixIcon: Icon(Icons.search_rounded)),
          onSubmitted: (_) => _load(),
        ),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final (k, l) in const [
            ('active', 'Raste mein'), ('draft', 'Book baaki'), ('waiting', 'Haan baaki'), ('exception', 'NDR'), ('rto', 'RTO'),
            ('delivered', 'Pahunche'), ('', 'Sab'),
          ])
            ChoiceChip(
              label: Text(l),
              selected: _filter == k,
              onSelected: (_) {
                setState(() => _filter = k);
                _load();
              },
            ),
        ]),
        const SizedBox(height: 12),
        if (_all.isEmpty) const Text('Koi parcel nahi.', style: TextStyle(color: C.muted)),
        for (final p in _all) _tile(p),
        const SizedBox(height: 8),
        GlassButton(
          label: 'Return label (graahak se wapas)',
          icon: Icons.assignment_return_rounded,
          onTap: _busy
              ? null
              : () async {
                  final f = await _form(context, 'Return label', const [
                    ('ref', 'Pahunche parcel ka number (P-0001) ya'),
                    ('wapsi_ref', 'Wapsi return number (R-0001)'),
                    ('reason', 'Kyon wapas'),
                  ]);
                  if (f == null) return;
                  await _run(() => _call(widget.app, 'POST', '/api/courier/returns', body: {
                        'ref': f['ref'] ?? '', 'wapsi_ref': f['wapsi_ref'] ?? '', 'reason': f['reason'] ?? '',
                      }));
                },
        ),
      ]);

  Future<void> _remit() async {
    try {
      final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
      final f = res?.files.single;
      if (f == null || f.bytes == null) return;
      await _run(() => widget.app.api!.uploadFile('/api/courier/remit', f.name, f.bytes!, timeout: const Duration(seconds: 120), tries: 2));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _cod() {
    final cod = _m(_d?['cod']);
    Widget line(Map<String, dynamic> x, {bool diff = false}) => Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Row(children: [
            Expanded(
              child: Text('${_s(x['number'])} · ${_s(x['carrier'])} · ${_s(x['awb'])}'
                  '${x['days_since_delivery'] != null ? ' · ${_s(x['days_since_delivery'])} din' : ''}',
                  style: TextStyle(fontSize: 12.5, color: x['late'] == true ? C.bad : C.ink)),
            ),
            Text(diff ? '${_rs(x['remitted'])} / ${_rs(x['cod_amount'])}' : _rs(x['cod_amount']), style: const TextStyle(fontSize: 12.5)),
          ]),
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('COD ka hisaab', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 6),
          Text('Aana baaki: ${_s(cod['pending_count'])} parcel · ${_rs(cod['pending_amount'])}'),
          Text('Aa gaya: ${_s(cod['remitted_count'])} parcel · ${_rs(cod['remitted_amount'])}', style: const TextStyle(color: C.muted)),
          const SizedBox(height: 6),
          Text(_s(cod['note']), style: const TextStyle(fontSize: 12, color: C.faint)),
          const SizedBox(height: 10),
          GradientButton(label: 'Courier ki remittance sheet daalo', icon: Icons.upload_file_rounded, height: 46, onTap: _busy ? null : _remit),
        ]),
      ),
      if (_list(cod['mismatch']).isNotEmpty) ...[
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Rakam alag (aaya / hona tha)', style: TextStyle(fontWeight: FontWeight.w700, color: C.warn)),
            for (final x in _list(cod['mismatch'])) line(x, diff: true),
          ]),
        ),
      ],
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Delivered, COD abhi nahi aaya', style: TextStyle(fontWeight: FontWeight.w700)),
          if (_list(cod['pending']).isEmpty) const Text('Kuch baaki nahi.', style: TextStyle(color: C.muted)),
          for (final x in _list(cod['pending'])) line(x),
        ]),
      ),
      if (_list(cod['unknown']).isNotEmpty) ...[
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Sheet mein AWB jo hamare record mein nahi', style: TextStyle(fontWeight: FontWeight.w700)),
            for (final x in _list(cod['unknown'])) Text('${_s(x['awb'])} · ${_rs(x['amount'])} · ${_s(x['utr'])}', style: const TextStyle(fontSize: 12.5)),
          ]),
        ),
      ],
    ]);
  }

  Widget _rules() {
    final st = _m(_d?['settings']);
    final wh = _m(st['warehouse']);
    final joined = _m(st['joined']);
    final carriers = _list(st['carriers']);
    final law = _list(_d?['law']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Pickup ka pata', style: TextStyle(fontWeight: FontWeight.w800)),
          Text('${_s(st['business'])} · ${_s(wh['address'])} ${_s(wh['pincode'])}'.trim(), style: const TextStyle(color: C.muted)),
          const SizedBox(height: 8),
          GlassButton(
            label: 'Badlo',
            icon: Icons.store_rounded,
            onTap: () async {
              final f = await _form(context, 'Pickup / dukaan', const [
                ('business', 'Business ka naam'), ('gstin', 'GSTIN (e-way bill ke liye)'), ('phone', 'Pickup phone'),
                ('address', 'Pickup ka pata'), ('city', 'Shehar'), ('state', 'Rajya'), ('pincode', 'PIN'),
                ('remit_days', 'COD kitne din mein aana chahiye (aapka andaaza)'),
              ], init: {
                'business': _s(st['business']), 'gstin': _s(st['gstin']), 'phone': _s(wh['phone']), 'address': _s(wh['address']),
                'city': _s(wh['city']), 'state': _s(wh['state']), 'pincode': _s(wh['pincode']),
                'remit_days': _s(st['remit_days']) == '0' ? '' : _s(st['remit_days']),
              });
              if (f == null) return;
              await _run(() => _call(widget.app, 'PUT', '/api/courier/settings', body: {
                    if (f['business'] != null) 'business': f['business'],
                    if (f['gstin'] != null) 'gstin': f['gstin'],
                    if (f['remit_days'] != null) 'remit_days': _n(f['remit_days']).round(),
                    'warehouse': {
                      'name': f['business'] ?? _s(st['business']), 'phone': f['phone'] ?? '', 'address': f['address'] ?? '',
                      'city': f['city'] ?? '', 'state': f['state'] ?? '', 'pincode': f['pincode'] ?? '',
                    },
                  }));
            },
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Courier ke niyam', style: TextStyle(fontWeight: FontWeight.w800)),
          for (final l in (st['rule_lines'] as List?) ?? const []) Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $l')),
          const SizedBox(height: 8),
          GlassButton(
            label: 'Apne shabdon mein',
            icon: Icons.edit_note_rounded,
            onTap: () async {
              final f = await _form(context, 'Courier ke niyam', const [('text', 'Jaise: sabse sasta; COD par Delhivery; Ekart mat lena; 5 kg se upar Xpressbees')],
                  init: {'text': _s(st['rules_text'])});
              if (f?['text'] != null) await _run(() => _call(widget.app, 'POST', '/api/courier/rules', body: {'text': f!['text']}));
            },
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Courier ki chaabi (sirf yahan, chat mein kabhi nahi)', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          for (final c in carriers.where((c) => ((c['keys'] as List?) ?? const []).isNotEmpty))
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(c['label'])}${joined[_s(c['id'])] == true ? ' (juda)' : ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(_s(c['note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
                  ]),
                ),
                GlassButton(
                  label: joined[_s(c['id'])] == true ? 'Badlo' : 'Jodo',
                  icon: Icons.key_rounded,
                  height: 40,
                  onTap: () async {
                    final keys = ((c['keys'] as List?) ?? const []).map((e) => '$e').toList();
                    final f = await _form(context, '${_s(c['label'])} jodiye', [for (final k in keys) (k, k.replaceAll('_', ' '))], secret: true);
                    if (f != null) await _run(() => _call(widget.app, 'PUT', '/api/courier/keys/${_s(c['id'])}', body: {'creds': f}));
                  },
                ),
              ]),
            ),
          const Text('DTDC / Ekart / Xpressbees / India Post: unke app mein book kijiye aur AWB yahan likhiye (ya Shiprocket se in sab ke rate).',
              style: TextStyle(fontSize: 12, color: C.faint)),
        ]),
      ),
      const SizedBox(height: 12),
      for (final l in law)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(l['what']), style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(_s(l['text']), style: const TextStyle(fontSize: 12.5)),
              Text(_s(l['source']), style: const TextStyle(fontSize: 11, color: C.faint)),
            ]),
          ),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Parcel', 'COD', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        title: const Text('Courier sahayak'),
        backgroundColor: Colors.transparent,
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ),
          ]),
        ),
        Expanded(
          child: _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(onRefresh: _load, child: [_today, _parcels, _cod, _rules][_tab]()),
        ),
      ]),
    );
  }
}

/// One parcel: address, weights, the carrier's quotes, booking card, AWB / label, tracking events, NDR, messages.
class CourierParcelPage extends StatefulWidget {
  const CourierParcelPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<CourierParcelPage> createState() => _CourierParcelPageState();
}

class _CourierParcelPageState extends State<CourierParcelPage> {
  Map<String, dynamic>? _p;
  bool _busy = false;
  String get _base => '/api/courier/parcels/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = _m(await _call(widget.app, 'GET', _base));
      if (mounted) setState(() => _p = p);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _m(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _message(String kind) async {
    try {
      final m = _m(await widget.app.api!.call('GET', '$_base/message', query: {'kind': kind}));
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Graahak ke liye message'),
          content: SingleChildScrollView(child: Text(_s(m['text']))),
          actions: [
            TextButton(onPressed: () => Clipboard.setData(ClipboardData(text: _s(m['text']))), child: const Text('Copy')),
            if (_s(m['whatsapp']).isNotEmpty) TextButton(onPressed: () => _openLink(context, _s(m['whatsapp'])), child: const Text('WhatsApp kholo')),
            TextButton(onPressed: () => Navigator.pop(d), child: const Text('Band')),
          ],
        ),
      );
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    if (p == null) return const Scaffold(backgroundColor: C.bgTop, body: Center(child: CircularProgressIndicator()));
    final st = _s(p['status']);
    final c = _m(p['customer']);
    final w = _m(p['weight']);
    final sv = _m(p['serviceable']);
    final pick = _m(_m(p['pick'])['best']);
    final nd = _m(p['ndr']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(title: Text('${_s(p['number'])} ${p['kind'] == 'reverse' ? '(return)' : ''}'), backgroundColor: Colors.transparent),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(c['name']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16))),
                Pill(_s(p['status_label']), fg: _statusColor(st)),
              ]),
              Text('${_s(c['address'])} ${_s(c['city'])} ${_s(c['pincode'])}'.trim(), style: const TextStyle(color: C.muted)),
              Text(_s(p['phone_masked']), style: const TextStyle(color: C.faint, fontSize: 12)),
              const SizedBox(height: 6),
              Text('${_list(p['items']).map((i) => '${_s(i['name'])} x${_s(i['qty'])}').join(', ')} · keemat ${_rs(p['value'])}'),
              Text(p['payment'] == 'cod' ? 'COD: ${_rs(p['cod_amount'])} lena hai' : 'Prepaid', style: const TextStyle(color: C.warn)),
              Text('Wazan ${_s(w['dead_kg'])} kg · volumetric ${_s(w['volumetric_kg'])} kg · chargeable ${_s(w['chargeable_kg'])} kg',
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
              if (_s(p['eway_no']).isNotEmpty) Text('E-way bill ${_s(p['eway_no'])}', style: const TextStyle(fontSize: 12.5)),
            ]),
          ),
          for (final b in (p['blocking'] as List?) ?? const [])
            Padding(padding: const EdgeInsets.only(top: 6), child: Text('⛔ $b', style: const TextStyle(color: C.bad, fontSize: 12.5))),
          for (final b in (p['warnings'] as List?) ?? const [])
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('⚠ $b', style: const TextStyle(color: C.warn, fontSize: 12.5))),
          const SizedBox(height: 12),
          if (_s(p['awb']).isNotEmpty)
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(p['carrier'])} · AWB ${_s(p['awb'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                if (_s(p['raw']).isNotEmpty) Text('Courier ne kaha: ${_s(p['raw'])}'),
                if (_s(p['edd']).isNotEmpty) Text('Courier ki ummeed: ${_s(p['edd'])}', style: const TextStyle(color: C.muted)),
                for (final e in _list(p['events']).take(8))
                  Text('${_s(e['at'])} · ${_s(e['what'])} ${_s(e['where'])}'.trim(), style: const TextStyle(fontSize: 11.5, color: C.faint)),
                if (nd.isNotEmpty && st == 'exception') ...[
                  const Divider(),
                  Text('Delivery nahi hui: ${_s(nd['label'])} (koshish ${_s(nd['attempts'])})', style: const TextStyle(color: C.bad)),
                  const Text('Courier aam taur par 3 koshish ke baad wapas bhej deta hai.', style: TextStyle(fontSize: 11.5, color: C.faint)),
                ],
              ]),
            )
          else if (sv.isNotEmpty || pick.isNotEmpty)
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(sv['ok'] == true ? 'PIN par delivery hoti hai${sv['cod'] == false ? ' (COD nahi)' : ''}' : 'PIN par delivery nahi',
                    style: TextStyle(fontWeight: FontWeight.w700, color: sv['ok'] == true ? C.ok : C.bad)),
                for (final q in _list(p['quotes']).take(6))
                  Row(children: [
                    Expanded(child: Text('${_s(q['courier'])}${q['days'] != null ? ' · ~${_s(q['days'])} din' : ''}', style: const TextStyle(fontSize: 12.5))),
                    Text(q['rate'] == null ? 'rate ?' : _rs(q['rate']), style: const TextStyle(fontSize: 12.5)),
                  ]),
                if (_s(_m(p['pick'])['why']).isNotEmpty) Text('Chuna: ${_s(pick['courier'])} (${_s(_m(p['pick'])['why'])})', style: const TextStyle(fontSize: 12, color: C.muted)),
              ]),
            ),
          const SizedBox(height: 12),
          for (final card in _list(p['cards']).where((x) => x['status'] == 'waiting'))
            Padding(padding: const EdgeInsets.only(bottom: 10), child: CourierActionCard(app: widget.app, data: {'card': card}, onDone: _load)),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (['draft', 'failed'].contains(st)) ...[
              GlassButton(label: 'PIN + rate dekho', icon: Icons.price_check_rounded, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/check'))),
              GradientButton(label: 'Booking card', icon: Icons.local_shipping_rounded, height: 44,
                  onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/book', body: {}))),
            ],
            if (['draft', 'failed', 'manual', 'waiting'].contains(st))
              GlassButton(
                label: 'Maine book kiya (AWB)',
                icon: Icons.numbers_rounded,
                onTap: () async {
                  final f = await _form(context, 'Tracking number', const [('awb', 'AWB / article number'), ('carrier', 'Courier (DTDC / India Post / ...)')]);
                  if (f?['awb'] != null) await _run(() => _call(widget.app, 'POST', '$_base/awb', body: {'awb': f!['awb'], 'carrier': f['carrier'] ?? ''}));
                },
              ),
            if (['draft', 'failed'].contains(st))
              GlassButton(
                label: 'Badlo',
                icon: Icons.edit_rounded,
                onTap: () async {
                  final f = await _form(context, 'Badlav', const [
                    ('weight_kg', 'Wazan (kg)'), ('pincode', 'PIN'), ('phone', 'Mobile'), ('address', 'Pata'), ('eway_no', 'E-way bill number'),
                    ('cod_amount', 'COD rakam'),
                  ]);
                  if (f == null) return;
                  await _run(() => _call(widget.app, 'PATCH', _base, body: {
                        if (f['weight_kg'] != null) 'weight_kg': _n(f['weight_kg']),
                        if (f['eway_no'] != null) 'eway_no': f['eway_no'],
                        if (f['cod_amount'] != null) 'cod_amount': _n(f['cod_amount']),
                        if (f['pincode'] != null || f['phone'] != null || f['address'] != null)
                          'customer': {
                            if (f['pincode'] != null) 'pincode': f['pincode'],
                            if (f['phone'] != null) 'phone': f['phone'],
                            if (f['address'] != null) 'address': f['address'],
                          },
                      }));
                },
              ),
            if (_s(p['awb']).isNotEmpty && !['delivered', 'cancelled'].contains(st))
              GlassButton(label: 'Tracking', icon: Icons.route_rounded, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/track'))),
            if (_s(p['track_link']).isNotEmpty) GlassButton(label: 'Courier ka page', icon: Icons.open_in_new_rounded, onTap: () => _openLink(context, _s(p['track_link']))),
            if (_s(_m(p['label'])['path']).isNotEmpty || _s(_m(p['label'])['file_id']).isNotEmpty)
              GlassButton(label: 'Label aapki files mein', icon: Icons.picture_as_pdf_rounded, onTap: () => _snack(context, 'Label PDF chat ki files mein hai (Label-${_s(p['number'])}.pdf).')),
            if (_s(p['awb']).isNotEmpty) GlassButton(label: 'Graahak ko message', icon: Icons.sms_rounded, onTap: () => _message(st == 'delivered' ? 'delivered' : 'shipped')),
            if (st == 'exception') ...[
              GlassButton(label: 'NDR message', icon: Icons.sms_failed_rounded, onTap: () => _message('ndr')),
              GradientButton(
                label: 'Dobara bhejo (card)',
                icon: Icons.replay_rounded,
                height: 44,
                onTap: () async {
                  final f = await _form(context, 'Dobara delivery', const [
                    ('when', 'Din (YYYY-MM-DD)'), ('phone', 'Naya phone (agar)'), ('address', 'Sahi pata / landmark (agar)'), ('note', 'Note'),
                  ]);
                  if (f == null) return;
                  await _run(() => _call(widget.app, 'POST', '$_base/ndr', body: {'action': 'reattempt', ...f}));
                },
              ),
              GlassButton(label: 'Wapas mangwao (RTO card)', icon: Icons.undo_rounded, color: C.bad,
                  onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/ndr', body: {'action': 'rto'}))),
            ],
            if (st == 'booked') GlassButton(label: 'Cancel (card)', icon: Icons.cancel_rounded, color: C.bad, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/cancel'))),
            if (st == 'delivered' && p['kind'] == 'forward')
              GlassButton(label: 'Return label', icon: Icons.assignment_return_rounded,
                  onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/courier/returns', body: {'ref': _s(p['number'])}))),
            if (['delivered', 'cancelled', 'rto'].contains(st))
              GlassButton(label: 'Graahak ki jaankari mitao', icon: Icons.delete_sweep_rounded, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/forget'))),
          ]),
          const SizedBox(height: 14),
          for (final l in _list(p['log']).reversed.take(10))
            Text('${_s(l['at']).split('T').first} · ${_s(l['text'])}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      ),
    );
  }
}

/// Chat / call card for `courier_card`: a booking / return label / NDR action / cancel that ONLY her tap sends to the carrier
/// (fingerprint once her phone key is active, for cards that may charge her courier wallet).
class CourierActionCard extends StatefulWidget {
  const CourierActionCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<CourierActionCard> createState() => _CourierActionCardState();
}

class _CourierActionCardState extends State<CourierActionCard> {
  late Map<String, dynamic> _c = _m(widget.data['card']);
  bool _busy = false;

  @override
  void didUpdateWidget(covariant CourierActionCard old) {
    super.didUpdateWidget(old);
    _c = _m(widget.data['card']);
  }

  Future<void> _decide(bool yes) async {
    var reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyon roka?', const [('reason', 'Wajah (aapke liye)')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final r = await courierDecide(widget.app, _c, yes, reason: reason);
      if (mounted) {
        setState(() {
          if (r['card'] is Map) _c = _m(r['card']);
        });
        if (_s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
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
    final c = _c;
    final b = _m(c['body']);
    final st = _s(c['status']);
    final kind = _s(c['kind']);
    final res = _m(c['result']);
    final icon = switch (kind) {
      'reverse' => Icons.assignment_return_rounded,
      'ndr' => Icons.replay_rounded,
      'cancel' => Icons.cancel_rounded,
      _ => Icons.local_shipping_rounded,
    };
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(icon, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(b['title']).isEmpty ? '${_s(c['number'])} · ${_s(b['parcel_number'])}' : _s(b['title']), style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'Aapki haan baaki', 'done' => 'Ho gaya', 'rejected' => 'Roka', 'stale' => 'Purana', 'failed' => 'Nahi hua', _ => st }),
        ]),
        const SizedBox(height: 6),
        if (_s(b['courier']).isNotEmpty || b['rate'] != null)
          Row(children: [
            Expanded(child: Text('${_s(b['courier'])}${b['days'] != null ? ' · ~${_s(b['days'])} din' : ''}')),
            Text(b['rate'] == null ? 'rate courier batayega' : _rs(b['rate']), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
          ]),
        if (_s(b['to']).isNotEmpty) Text('Kahan: ${_s(b['to'])}', style: const TextStyle(fontSize: 12.5)),
        if (_s(b['from']).isNotEmpty) Text('Kahan se: ${_s(b['from'])}', style: const TextStyle(fontSize: 12.5)),
        if (b['payment'] == 'cod') Text('COD ${_rs(b['cod_amount'])} · ${_s(b['chargeable_kg'])} kg', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (b['payment'] == 'prepaid') Text('Prepaid · ${_s(b['chargeable_kg'])} kg', style: const TextStyle(fontSize: 12.5)),
        if (_s(b['reason']).isNotEmpty) Text('Wajah: ${_s(b['reason'])}', style: const TextStyle(fontSize: 12.5)),
        if (_m(b['fix']).isNotEmpty)
          Text([
            if (_s(_m(b['fix'])['date']).isNotEmpty) 'din ${_s(_m(b['fix'])['date'])}',
            if (_s(_m(b['fix'])['address']).isNotEmpty) 'pata: ${_s(_m(b['fix'])['address'])}',
            if (_s(_m(b['fix'])['note']).isNotEmpty) _s(_m(b['fix'])['note']),
          ].join(' · '), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (b['by'] == 'customer') const Text('Graahak ne WhatsApp par bataya', style: TextStyle(fontSize: 11.5, color: C.faint)),
        for (final w in (b['warnings'] as List?) ?? const []) Text('⚠ $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(b['say']).isNotEmpty) Text(_s(b['say']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(
              child: GradientButton(
                label: switch (kind) { 'ndr' => 'Haan, courier ko bolo', 'cancel' => 'Haan, cancel karo', 'reverse' => 'Haan, pickup book karo', _ => 'Haan, book karo' },
                icon: c['money'] == true ? Icons.fingerprint_rounded : Icons.check_rounded,
                height: 46,
                onTap: _busy ? null : () => _decide(true),
              ),
            ),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', color: C.bad, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'failed' && _s(res['error']).isNotEmpty) Text('Courier: ${_s(res['error'])}', style: const TextStyle(fontSize: 12.5, color: C.bad)),
        if (st == 'done' && _s(res['awb']).isNotEmpty) Text('AWB ${_s(res['awb'])}', style: const TextStyle(fontSize: 12.5, color: C.ok)),
        if (st == 'done') for (final s in (res['steps'] as List?) ?? const []) Text('• $s', style: const TextStyle(fontSize: 12.5)),
      ]),
    );
  }
}

/// Chat card for `courier_parcel` (new / booked / out for delivery / delivered / NDR / RTO): opens the parcel page.
class CourierParcelCard extends StatelessWidget {
  const CourierParcelCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final p = _m(data['parcel']);
    final st = _s(p['status']);
    return Glass(
      child: InkWell(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CourierParcelPage(app: app, id: _s(p['id'])))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(p['kind'] == 'reverse' ? Icons.assignment_return_rounded : Icons.local_shipping_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(p['number'])} · ${_s(p['customer_name'])} ${_s(p['pincode'])}'.trim(), style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(p['status_label']), fg: _statusColor(st)),
          ]),
          if (_s(p['awb']).isNotEmpty) Text('${_s(p['carrier'])} · AWB ${_s(p['awb'])}', style: const TextStyle(fontSize: 12.5)),
          if (_s(p['raw']).isNotEmpty) Text('Courier: ${_s(p['raw'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          if (st == 'exception') Text('Delivery nahi hui: ${_s(_m(p['ndr'])['label'])} · graahak ke liye message taiyaar', style: const TextStyle(fontSize: 12, color: C.bad)),
          for (final b in ((p['blocking'] as List?) ?? const []).take(2)) Text('⛔ $b', style: const TextStyle(fontSize: 12, color: C.warn)),
        ]),
      ),
    );
  }
}

/// Chat card for `courier_day` (morning note / manifest reminder).
class CourierDayCard extends StatelessWidget {
  const CourierDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: InkWell(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CourierScreen(app: app))),
          child: Row(children: [
            const Icon(Icons.local_shipping_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(data['text']), style: const TextStyle(fontWeight: FontWeight.w600))),
          ]),
        ),
      );
}
