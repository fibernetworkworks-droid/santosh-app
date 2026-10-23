/// Profile > Wapsi sahayak (returns & refunds desk).
/// Aaj (what needs her) · Returns (requests -> check -> manzoor / mana / jaankari -> pickup -> QC) · Refund (cards that ONLY
/// her tap approves, fingerprint when the phone key is active; then she sends the money and taps "Refund kar diya" + UTR)
/// · Niyam (her return policy in her words, warehouse, courier / gateway keys typed only here). Hoola never moves money.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'gst_screen.dart' show rs;

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

Color _statusColor(String st) => switch (st) {
      'rejected' || 'qc_failed' => C.bad,
      'refunded' || 'exchanged' || 'closed' => C.ok,
      'refund_waiting' || 'new' || 'need_info' => C.warn,
      _ => C.teal,
    };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {Map<String, String> init = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: init[k] ?? '')};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields) TextField(controller: c[k], decoration: InputDecoration(labelText: label)),
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

Future<dynamic> _call(Santosh app, String method, String path, {Object? body}) => app.api!.call(method, path, body: body);

/// Her tap on a refund card: hash of the card she saw + (when needed) the fingerprint. Saying no never needs it.
Future<Map<String, dynamic>> wapsiDecideRefund(Santosh app, Map<String, dynamic> refund, bool yes, {String reason = ''}) async {
  final id = _s(refund['id']);
  final body = <String, dynamic>{'yes': yes, 'hash': _s(refund['hash']), if (reason.isNotEmpty) 'reason': reason};
  try {
    return _m(await _call(app, 'POST', '/api/wapsi/refunds/$id/decide', body: body));
  } on ApiException catch (e) {
    if (!yes || e.status != 428) rethrow;
  }
  final proof = await app.api!.fingerprintProof('wapsi', id);
  return _m(await _call(app, 'POST', '/api/wapsi/refunds/$id/decide', body: {...body, 'proof': proof}));
}

Future<void> _openLink(BuildContext context, String url) async {
  if (url.isEmpty) return;
  final r = await Native.openExternal(url: url);
  if (r.isNotEmpty && r != 'ok' && context.mounted) {
    await Clipboard.setData(ClipboardData(text: url));
    if (context.mounted) _snack(context, 'Link copy kar diya');
  }
}

class WapsiScreen extends StatefulWidget {
  const WapsiScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<WapsiScreen> createState() => _WapsiScreenState();
}

class _WapsiScreenState extends State<WapsiScreen> {
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _all = [];
  int _tab = 0;
  bool _busy = false;
  String _filter = 'open';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await _call(widget.app, 'GET', '/api/wapsi'));
      final all = _m(await widget.app.api!.call('GET', '/api/wapsi/returns', query: {'status': _filter}));
      if (mounted) {
        setState(() {
          _d = d;
          _all = _list(all['returns']);
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

  Future<void> _newReturn() async {
    final f = await _form(context, 'Naya return', const [
      ('name', 'Graahak ka naam'),
      ('phone', 'Phone'),
      ('items', 'Saamaan (jaise: Kurti x1 @ 899)'),
      ('reason', 'Kya dikkat hai (graahak ke shabd)'),
      ('delivered_on', 'Delivery ki tareekh (DD-MM-YYYY)'),
      ('order_ref', 'Order number'),
      ('pincode', 'PIN code'),
      ('address', 'Pickup ka pata'),
    ]);
    if (f == null) return;
    final r = await _run(() => _call(widget.app, 'POST', '/api/wapsi/returns', body: {
          'customer': {'name': f['name'] ?? '', 'phone': f['phone'] ?? '', 'pincode': f['pincode'] ?? '', 'address': f['address'] ?? ''},
          'items': f['items'] ?? '',
          'reason_text': f['reason'] ?? '',
          'delivered_on': f['delivered_on'] ?? '',
          'order_ref': f['order_ref'] ?? '',
        }));
    final id = _s(_m(r?['return'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  void _open(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => WapsiReturnPage(app: widget.app, id: id)))
      .then((_) => _load());

  Widget _returnTile(Map<String, dynamic> r) => Glass(
        margin: const EdgeInsets.only(bottom: 10),
        child: InkWell(
          onTap: () => _open(_s(r['id'])),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(r['number'])} · ${_s(r['customer'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text(_s(r['what']), style: const TextStyle(fontSize: 12.5, color: C.muted), maxLines: 2, overflow: TextOverflow.ellipsis),
                Text(_s(r['reason_label']), style: const TextStyle(fontSize: 12, color: C.faint)),
              ]),
            ),
            const SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Pill(_s(r['status_label']), fg: _statusColor(_s(r['status']))),
              if ((r['signals'] ?? 0) is num && (r['signals'] as num) > 0)
                const Padding(padding: EdgeInsets.only(top: 4), child: Icon(Icons.flag_rounded, color: C.warn, size: 18)),
            ]),
          ]),
        ),
      );

  Widget _today() {
    final day = _m(_d?['day']);
    final parts = (day['parts'] as List?) ?? const [];
    final waiting = _list(_d?['waiting']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aaj', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 6),
          if (parts.isEmpty) const Text('Sab theek. Koi return aapka intezaar nahi kar raha.', style: TextStyle(color: C.muted)),
          for (final p in parts) Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $p')),
        ]),
      ),
      const SizedBox(height: 12),
      for (final f in waiting) Padding(padding: const EdgeInsets.only(bottom: 10), child: WapsiRefundCard(app: widget.app, data: {'refund': f, 'return_number': f['return_number'], 'customer': f['customer']}, onDone: _load)),
      for (final r in _list(_d?['returns']).take(20)) _returnTile(r),
      const SizedBox(height: 8),
      GradientButton(label: 'Naya return', icon: Icons.add_rounded, onTap: _busy ? null : _newReturn),
    ]);
  }

  Widget _returns() => ListView(padding: const EdgeInsets.all(16), children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final (k, l) in const [('open', 'Khule'), ('new', 'Naye'), ('refund_waiting', 'Refund baaki'), ('refunded', 'Ho gaye'), ('rejected', 'Mana'), ('', 'Sab')])
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
        if (_all.isEmpty) const Text('Koi return nahi.', style: TextStyle(color: C.muted)),
        for (final r in _all) _returnTile(r),
        const SizedBox(height: 8),
        GlassButton(label: 'Register (Excel)', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/wapsi/register'))),
      ]);

  Widget _refunds() => FutureBuilder<dynamic>(
        future: widget.app.api!.call('GET', '/api/wapsi/refunds'),
        builder: (c, snap) {
          final rows = _list(_m(snap.data)['refunds']);
          return ListView(padding: const EdgeInsets.all(16), children: [
            const Text('Har refund sirf aapki haan se. Paisa aap khud bhejti hain; Hoola UTR likhta hai.', style: TextStyle(color: C.muted, fontSize: 12.5)),
            const SizedBox(height: 10),
            if (snap.connectionState != ConnectionState.done) const Center(child: CircularProgressIndicator()),
            for (final f in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: WapsiRefundCard(app: widget.app, data: {'refund': f, 'return_number': f['return_number'], 'customer': f['customer']}, onDone: _load),
              ),
          ]);
        },
      );

  Widget _rules() {
    final st = _m(_d?['settings']);
    final lines = (st['policy_lines'] as List?) ?? const [];
    final law = _list(_d?['law']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aapki return policy', style: TextStyle(fontWeight: FontWeight.w800)),
          for (final l in lines) Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $l', style: const TextStyle(fontSize: 13))),
          const SizedBox(height: 10),
          GlassButton(
            label: 'Apne shabdon mein likhiye',
            icon: Icons.edit_note_rounded,
            onTap: () async {
              final f = await _form(context, 'Return policy', const [('text', 'Jaise: 7 din return, innerwear wapas nahi, tag lage hon, man badalne par 10% fee')]);
              if (f?['text'] != null) await _run(() => _call(widget.app, 'POST', '/api/wapsi/policy', body: {'text': f!['text']}));
            },
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Dukaan aur wapsi ka pata', style: TextStyle(fontWeight: FontWeight.w800)),
          Text('${_s(st['business'])} ${_s(st['gstin'])}'.trim(), style: const TextStyle(color: C.muted)),
          Text(_s(_m(st['warehouse'])['address']), style: const TextStyle(color: C.muted)),
          const SizedBox(height: 8),
          GlassButton(
            label: 'Badlo',
            icon: Icons.store_rounded,
            onTap: () async {
              final w = _m(st['warehouse']);
              final f = await _form(context, 'Dukaan / warehouse', const [
                ('business', 'Business ka naam'), ('gstin', 'GSTIN'), ('state', 'State'), ('w_phone', 'Warehouse phone'),
                ('w_address', 'Warehouse ka pata'), ('w_city', 'Shehar'), ('w_pincode', 'PIN'),
              ], init: {'business': _s(st['business']), 'gstin': _s(st['gstin']), 'state': _s(st['state']), 'w_phone': _s(w['phone']),
                'w_address': _s(w['address']), 'w_city': _s(w['city']), 'w_pincode': _s(w['pincode'])});
              if (f == null) return;
              await _run(() => _call(widget.app, 'PUT', '/api/wapsi/settings', body: {
                    if (f['business'] != null) 'business': f['business'],
                    if (f['gstin'] != null) 'gstin': f['gstin'],
                    if (f['state'] != null) 'state': f['state'],
                    'warehouse': {'name': f['business'] ?? _s(st['business']), 'phone': f['w_phone'] ?? '', 'address': f['w_address'] ?? '',
                      'city': f['w_city'] ?? '', 'state': f['state'] ?? '', 'pincode': f['w_pincode'] ?? ''},
                  }));
            },
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Courier aur gateway (sirf yahan, chat mein kabhi nahi)', style: TextStyle(fontWeight: FontWeight.w800)),
          Text('Courier: ${_s(st['courier'])}${st['courier_joined'] == true ? ' (juda)' : ''} · Gateway: ${_s(st['pg']).isEmpty ? '-' : _s(st['pg'])}${st['pg_joined'] == true ? ' (juda)' : ''}',
              style: const TextStyle(color: C.muted)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final (p, l, fields) in const [
              ('shiprocket', 'Shiprocket', [('email', 'API user email'), ('password', 'API user password')]),
              ('delhivery', 'Delhivery', [('token', 'API token'), ('pickup_location', 'Registered warehouse ka naam')]),
              ('razorpay', 'Razorpay', [('key_id', 'Key ID'), ('key_secret', 'Key secret')]),
              ('cashfree', 'Cashfree', [('key_id', 'App ID'), ('key_secret', 'Secret key')]),
            ])
              GlassButton(
                label: l,
                icon: Icons.key_rounded,
                height: 40,
                onTap: () async {
                  final f = await _secretForm(context, '$l jodiye', fields);
                  if (f != null) await _run(() => _call(widget.app, 'PUT', '/api/wapsi/keys/$p', body: {'creds': f}));
                },
              ),
          ]),
          const SizedBox(height: 6),
          const Text('Gateway key se Hoola sirf refund ka haal padhta hai. Refund aap khud dashboard se karti hain.', style: TextStyle(fontSize: 12, color: C.faint)),
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
    const tabs = ['Aaj', 'Returns', 'Refund', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        title: const Text('Wapsi sahayak'),
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
              : RefreshIndicator(onRefresh: _load, child: [_today, _returns, _refunds, _rules][_tab]()),
        ),
      ]),
    );
  }
}

Future<Map<String, String>?> _secretForm(BuildContext context, String title, List<(String, String)> fields) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        for (final (k, label) in fields)
          TextField(controller: c[k], obscureText: k.contains('secret') || k.contains('password') || k == 'token', decoration: InputDecoration(labelText: label)),
        const SizedBox(height: 8),
        const Text('Chaabi band tijori mein rehti hai; Hoola ko bhi nahi dikhti.', style: TextStyle(fontSize: 12)),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Jodiye')),
      ],
    ),
  );
  if (ok != true) return null;
  return {for (final e in c.entries) e.key: e.value.text.trim()};
}

class WapsiReturnPage extends StatefulWidget {
  const WapsiReturnPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<WapsiReturnPage> createState() => _WapsiReturnPageState();
}

class _WapsiReturnPageState extends State<WapsiReturnPage> {
  Map<String, dynamic>? _r;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _base => '/api/wapsi/returns/${widget.id}';

  Future<void> _load() async {
    try {
      final r = _m(await _call(widget.app, 'GET', _base));
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _m(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      final msg = _m(r['message']);
      if (msg.isNotEmpty && mounted) await _showMessage(msg);
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _showMessage(Map<String, dynamic> msg) async {
    await showModalBottomSheet<void>(
      context: context,
      builder: (c) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Graahak ke liye message (aap bhejiye)', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          SelectableText(_s(msg['text'])),
          const SizedBox(height: 12),
          Wrap(spacing: 8, children: [
            if (_s(msg['whatsapp']).isNotEmpty) GlassButton(label: 'WhatsApp', icon: Icons.chat_rounded, onTap: () => _openLink(context, _s(msg['whatsapp']))),
            GlassButton(
              label: 'Copy',
              icon: Icons.copy_rounded,
              onTap: () async {
                await Clipboard.setData(ClipboardData(text: _s(msg['text'])));
                if (c.mounted) Navigator.pop(c);
              },
            ),
          ]),
        ]),
      ),
    );
  }

  Future<void> _photo(ImageSource src, String stage) async {
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 80, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      await _run(() => widget.app.api!.uploadFile('$_base/photo', x.name.isEmpty ? 'photo.jpg' : x.name, bytes, fields: {'stage': stage}));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _decide(String d) async {
    var reason = '';
    if (d != 'approve') {
      final f = await _form(context, d == 'reject' ? 'Mana kyon? (graahak ko dikhega)' : 'Graahak se kya chahiye?', const [('reason', 'Wajah / sawaal')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    await _run(() => _call(widget.app, 'POST', '$_base/decide', body: {'decision': d, 'reason': reason}));
  }

  Future<void> _qc() async {
    final list = _list(_m(_r?['check'])['qc_list']);
    final vals = {for (final x in list) _s(x['key']): true};
    final ded = TextEditingController();
    final why = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('QC: dabba kholte waqt video banaiye'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              for (final x in list)
                SwitchListTile(
                  dense: true,
                  title: Text(_s(x['label'])),
                  value: vals[_s(x['key'])] ?? true,
                  onChanged: (v) => set(() => vals[_s(x['key'])] = v),
                ),
              TextField(controller: ded, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Kataayi ₹ (sirf graahak ki kharabi)')),
              TextField(controller: why, decoration: const InputDecoration(labelText: 'Kataayi ki wajah')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('QC pakka')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    final dd = double.tryParse(ded.text.trim());
    await _run(() => _call(widget.app, 'POST', '$_base/qc', body: {
          'checklist': vals,
          if (dd != null && dd > 0) 'result': 'partial',
          if (dd != null && dd > 0) 'deduction': dd,
          'deduction_reason': why.text.trim(),
        }));
  }

  Widget _photoStrip(List<Map<String, dynamic>> ph) {
    final api = widget.app.api!;
    return SizedBox(
      height: 100,
      child: ListView(scrollDirection: Axis.horizontal, children: [
        for (final p in ph)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: _s(p['kind']) == 'video'
                  ? Container(width: 96, height: 96, color: C.panel, child: const Icon(Icons.videocam_rounded))
                  : Image.network(api.absolute(_s(p['url'])), headers: api.authHeaders, width: 96, height: 96, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(width: 96, height: 96, color: C.panel, child: const Icon(Icons.broken_image_rounded))),
            ),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    if (r == null) return const Scaffold(backgroundColor: C.bgTop, body: Center(child: CircularProgressIndicator()));
    final st = _s(r['status']);
    final chk = _m(r['check']);
    final cust = _m(r['customer']);
    final pickup = _m(r['pickup']);
    final refund = r['refund'] == null ? null : _m(r['refund']);
    final ph = _list(r['photos']);
    final verdict = _s(chk['verdict']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(title: Text('${_s(r['number'])} · ${_s(cust['name'])}'), backgroundColor: Colors.transparent),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(_s(r['reason_label']), style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(r['status_label']), fg: _statusColor(st)),
            ]),
            for (final i in _list(r['items'])) Text('${_s(i['name'])} x${_s(i['qty'])} · ${rs(i['price'])}', style: const TextStyle(fontSize: 13)),
            if (_s(r['reason_text']).isNotEmpty) Text('Graahak: "${_s(r['reason_text'])}"', style: const TextStyle(fontSize: 12.5, color: C.muted)),
            Text('Order ${_s(r['order_ref'])} · delivery ${_s(_m(r['order'])['delivered_on'])} · ${_s(cust['phone'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
          ]),
        ),
        const SizedBox(height: 10),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(switch (verdict) { 'approve' => 'Policy: theek hai', 'ask_more' => 'Policy: pehle aur jaankari', _ => 'Policy: mana banta hai (faisla aapka)' },
                style: TextStyle(fontWeight: FontWeight.w800, color: verdict == 'approve' ? C.ok : verdict == 'ask_more' ? C.warn : C.bad)),
            if (chk['fault'] == true) const Text('Galti dukaan ki taraf: kanoon mana karne nahi deta.', style: TextStyle(fontSize: 12.5, color: C.warn)),
            for (final a in (chk['asks'] as List?) ?? const []) Text('? $a', style: const TextStyle(fontSize: 12.5)),
            for (final n in (chk['notes'] as List?) ?? const []) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
            for (final s in _list(r['signals'])) Text('⚑ ${_s(s['text'])} (signal, faisla aapka)', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          ]),
        ),
        const SizedBox(height: 10),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Photo / video (location hata kar rakhi)', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            if (ph.isNotEmpty) _photoStrip(ph),
            Wrap(spacing: 8, runSpacing: 8, children: [
              GlassButton(label: 'Camera', icon: Icons.photo_camera_rounded, height: 40, onTap: _busy ? null : () => _photo(ImageSource.camera, st == 'received' ? 'qc' : 'customer')),
              GlassButton(label: 'Gallery', icon: Icons.photo_library_rounded, height: 40, onTap: _busy ? null : () => _photo(ImageSource.gallery, st == 'received' ? 'qc' : 'customer')),
            ]),
          ]),
        ),
        const SizedBox(height: 10),
        if (pickup.isNotEmpty)
          Glass(
            margin: const EdgeInsets.only(bottom: 10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Pickup: ${_s(pickup['provider'])} ${_s(pickup['awb']).isEmpty ? '' : '· AWB ${_s(pickup['awb'])}'}', style: const TextStyle(fontWeight: FontWeight.w700)),
              for (final s in (pickup['steps'] as List?) ?? const []) Text('• $s', style: const TextStyle(fontSize: 12.5)),
              for (final e in _list(pickup['events']).take(4)) Text('${_s(e['at'])} ${_s(e['what'])} ${_s(e['where'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
        if (refund != null) WapsiRefundCard(app: widget.app, data: {'refund': refund, 'return_number': r['number'], 'customer': cust['name']}, onDone: _load),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (['new', 'need_info', 'qc_failed'].contains(st)) ...[
            GradientButton(label: 'Manzoor', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide('approve')),
            GlassButton(label: 'Jaankari maango', icon: Icons.help_outline_rounded, onTap: _busy ? null : () => _decide('ask')),
            GlassButton(label: 'Mana', icon: Icons.close_rounded, color: C.bad, onTap: _busy ? null : () => _decide('reject')),
          ],
          if (st == 'pickup_manual' || st == 'approved') ...[
            GlassButton(label: 'Pickup book', icon: Icons.local_shipping_rounded, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/pickup', body: {}))),
            GlassButton(
              label: 'AWB likho',
              icon: Icons.numbers_rounded,
              onTap: () async {
                final f = await _form(context, 'Tracking number', const [('awb', 'AWB'), ('courier', 'Courier')]);
                if (f?['awb'] != null) await _run(() => _call(widget.app, 'POST', '$_base/pickup', body: {'awb': f!['awb'], 'courier': f['courier'] ?? ''}));
              },
            ),
          ],
          if (st == 'pickup_booked' || st == 'in_transit') GlassButton(label: 'Tracking', icon: Icons.route_rounded, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/track'))),
          if (['pickup_booked', 'pickup_manual', 'in_transit', 'approved'].contains(st))
            GlassButton(label: 'Saamaan aa gaya', icon: Icons.inventory_2_rounded, onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '$_base/received'))),
          if (st == 'received') GradientButton(label: 'QC kijiye', icon: Icons.fact_check_rounded, height: 44, onTap: _busy ? null : _qc),
          if (st == 'qc_passed' || (st == 'received' && chk['pickup_needed'] == false))
            GlassButton(
              label: 'Refund banao',
              icon: Icons.currency_rupee_rounded,
              onTap: () async {
                final f = await _form(context, 'Refund (card aapki haan ke liye)', const [('mode', 'original / upi / bank / store_credit (khaali = apne aap)'), ('upi', 'Graahak ka UPI ID (COD par)')]);
                if (f != null) await _run(() => _call(widget.app, 'POST', '$_base/refund', body: {'mode': f['mode'] ?? '', 'upi': f['upi'] ?? ''}));
              },
            ),
          GlassButton(
            label: 'Message',
            icon: Icons.sms_rounded,
            onTap: () async {
              try {
                final m = _m(await widget.app.api!.call('GET', '$_base/message', query: {'kind': st == 'need_info' ? 'ask' : 'status'}));
                if (mounted) await _showMessage(m);
              } catch (e) {
                if (mounted) _snack(context, '$e');
              }
            },
          ),
        ]),
        const SizedBox(height: 14),
        for (final l in _list(r['log']).reversed.take(10)) Text('${_s(l['at']).split('T').first} · ${_s(l['text'])}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
      ]),
    );
  }
}

/// Chat / call card for `wapsi_refund`: the amount worked out by code, line by line. "Haan" = her tap (fingerprint when
/// her phone key is active); after that she sends the money herself and taps "Refund kar diya" with the UTR.
class WapsiRefundCard extends StatefulWidget {
  const WapsiRefundCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<WapsiRefundCard> createState() => _WapsiRefundCardState();
}

class _WapsiRefundCardState extends State<WapsiRefundCard> {
  late Map<String, dynamic> _f = _m(widget.data['refund']);
  Map<String, dynamic> _how = {};
  bool _busy = false;

  @override
  void didUpdateWidget(covariant WapsiRefundCard old) {
    super.didUpdateWidget(old);
    _f = _m(widget.data['refund']);
  }

  Future<void> _do(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted) {
        setState(() {
          if (r['refund'] is Map) _f = _m(r['refund']);
          if (r['how'] is Map) _how = _m(r['how']);
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
    final f = _f;
    final st = _s(f['status']);
    final calc = _m(f['calc']);
    final how = _how.isNotEmpty ? _how : _m(_m(f['pg'])['how']);
    final id = _s(f['id']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.currency_rupee_rounded, color: C.accent),
          const SizedBox(width: 6),
          Expanded(
            child: Text('Refund ${_s(f['number'])} · ${_s(widget.data['return_number'])} ${_s(widget.data['customer'])}'.trim(),
                style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
          Pill(switch (st) { 'waiting' => 'Aapki haan baaki', 'approved' => 'Aap bhejiye', 'done' => 'Ho gaya', 'rejected' => 'Roka', _ => st }),
        ]),
        const SizedBox(height: 6),
        for (final l in _list(calc['lines'])) Row(children: [
          Expanded(child: Text('${_s(l['name'])} x${_s(l['qty'])}${(l['coupon_share'] ?? 0) != 0 ? ' (coupon −${rs(l['coupon_share'])})' : ''}', style: const TextStyle(fontSize: 12.5))),
          Text(rs(l['net']), style: const TextStyle(fontSize: 12.5)),
        ]),
        for (final a in _list(calc['add'])) Row(children: [Expanded(child: Text('+ ${_s(a['what'])}', style: const TextStyle(fontSize: 12.5))), Text(rs(a['amount']))]),
        for (final d in _list(calc['deductions']))
          Row(children: [Expanded(child: Text('− ${_s(d['what'])}', style: const TextStyle(fontSize: 12.5, color: C.warn))), Text(rs(d['amount']))]),
        const Divider(),
        Row(children: [
          Expanded(child: Text('Kul · ${_s(f['mode'])}${_s(f['to']).isNotEmpty && _s(f['to']) != 'original' ? ' · ${_s(f['to'])}' : ''}', style: const TextStyle(fontWeight: FontWeight.w700))),
          Text(rs(f['amount']), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        ]),
        for (final n in (calc['notes'] as List?) ?? const []) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.muted)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, refund manzoor', icon: Icons.fingerprint_rounded, height: 46,
                onTap: _busy ? null : () => _do(() => wapsiDecideRefund(widget.app, f, true)))),
            const SizedBox(width: 8),
            GlassButton(
              label: 'Nahi',
              color: C.bad,
              onTap: _busy
                  ? null
                  : () async {
                      final r = await _form(context, 'Kyon roka?', const [('reason', 'Wajah (aapke liye)')]);
                      if (r != null) await _do(() => wapsiDecideRefund(widget.app, f, false, reason: r['reason'] ?? ''));
                    },
            ),
          ]),
        if (st == 'approved') ...[
          for (final s in (how['steps'] as List?) ?? const []) Text('• $s', style: const TextStyle(fontSize: 12.5)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (_s(how['dashboard']).isNotEmpty) GlassButton(label: 'Dashboard kholo', icon: Icons.open_in_new_rounded, height: 40, onTap: () => _openLink(context, _s(how['dashboard']))),
            if (_s(how['upi_link']).isNotEmpty) GlassButton(label: 'UPI app kholo', icon: Icons.qr_code_rounded, height: 40, onTap: () => _openLink(context, _s(how['upi_link']))),
            if (_s(how['to']).contains('@'))
              GlassButton(label: 'UPI ID copy', icon: Icons.copy_rounded, height: 40, onTap: () => Clipboard.setData(ClipboardData(text: _s(how['to'])))),
            if (how['can_check'] == true)
              GlassButton(label: 'Jaanch karo', icon: Icons.sync_rounded, height: 40,
                  onTap: _busy ? null : () => _do(() async => _m(await _call(widget.app, 'POST', '/api/wapsi/refunds/$id/pg_check')))),
            GradientButton(
              label: 'Refund kar diya',
              icon: Icons.done_all_rounded,
              height: 40,
              onTap: _busy
                  ? null
                  : () async {
                      final r = await _form(context, 'Refund ka reference', const [('utr', 'UTR / ARN / coupon code')]);
                      if (r?['utr'] != null) await _do(() async => _m(await _call(widget.app, 'POST', '/api/wapsi/refunds/$id/done', body: {'utr': r!['utr']})));
                    },
            ),
          ]),
        ],
        if (st == 'done') ...[
          Text('Ref ${_s(f['utr'])}${_s(f['credit_note']).isNotEmpty ? ' · Credit note ${_s(f['credit_note'])}' : ''}', style: const TextStyle(fontSize: 12.5, color: C.ok)),
        ],
        if ((st == 'approved' || st == 'done') && _s(f['credit_note']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: GlassButton(label: 'Credit note PDF', icon: Icons.picture_as_pdf_rounded, height: 40,
                onTap: _busy ? null : () => _do(() async => _m(await _call(widget.app, 'POST', '/api/wapsi/refunds/$id/credit_note')))),
          ),
      ]),
    );
  }
}

/// Chat card for `wapsi_return` (a new / changed return request): verdict + the asks; opens the return page.
class WapsiReturnCard extends StatelessWidget {
  const WapsiReturnCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final r = _m(data['return']);
    final chk = _m(r['check']);
    final v = _s(chk['verdict']);
    return Glass(
      child: InkWell(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => WapsiReturnPage(app: app, id: _s(r['id'])))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.assignment_return_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(r['number'])} · ${_s(_m(r['customer'])['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(r['status_label']), fg: _statusColor(_s(r['status']))),
          ]),
          Text('${_list(r['items']).map((i) => _s(i['name'])).join(', ')} · ${_s(r['reason_label'])}', style: const TextStyle(fontSize: 12.5)),
          Text(switch (v) { 'approve' => 'Policy: theek hai · kholiye aur manzoor kijiye', 'ask_more' => 'Pehle: ${((chk['asks'] as List?) ?? const []).take(1).join()}', _ => 'Policy: mana banta hai (faisla aapka)' },
              style: TextStyle(fontSize: 12, color: v == 'approve' ? C.ok : C.warn)),
          if (_list(r['signals']).isNotEmpty) Text('⚑ ${_s(_list(r['signals']).first['text'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
        ]),
      ),
    );
  }
}

/// Chat card for `wapsi_day` (morning note).
class WapsiDayCard extends StatelessWidget {
  const WapsiDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: InkWell(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => WapsiScreen(app: app))),
          child: Row(children: [
            const Icon(Icons.assignment_return_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(data['text']), style: const TextStyle(fontWeight: FontWeight.w600))),
          ]),
        ),
      );
}
