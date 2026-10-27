/// Profile > Thok sahayak (v0.107): Hoola as a wholesale trader's coworker.
/// Aaj (sales, collection, cheques to deposit, bounced, MSME dues, low stock, today's route) · Order (party + her words ->
/// priced draft with stock / credit / e-way checks -> her Haan makes the GST bill PDF) · Udhaar (outstanding, aging,
/// reminder drafts she sends, "paisa mila") · Party · Stock (margin, reorder drafts to suppliers).
/// Hoola never takes or pays money; the e-way bill / IRN are made by her on the portal.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'gst_screen.dart' show rs;

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Color _lvl(String l) => switch (l) { 'stop' => C.bad, 'warn' => C.warn, _ => C.accent };

Future<void> _wa(String phone, String text) async {
  final p = phone.replaceAll(RegExp(r'\D'), '');
  final to = p.length == 10 ? '91$p' : p;
  await Native.openExternal(url: 'https://wa.me/$to?text=${Uri.encodeComponent(text)}');
}

class ThokScreen extends StatefulWidget {
  const ThokScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ThokScreen> createState() => _ThokScreenState();
}

class _ThokScreenState extends State<ThokScreen> {
  Map<String, dynamic>? _day;
  Map<String, dynamic>? _out;
  List<Map<String, dynamic>> _parties = [];
  List<Map<String, dynamic>> _items = [];
  List<Map<String, dynamic>> _drafts = [];
  Map<String, dynamic>? _reorder;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = widget.app.api!;
    try {
      final d = await api.thokDay();
      final o = await api.thokRead('outstanding');
      final p = await api.thokParties();
      final i = await api.thokItems();
      final dr = await api.thokOrders(status: 'draft');
      if (mounted) {
        setState(() {
          _day = d;
          _out = o;
          _parties = p;
          _items = i;
          _drafts = dr;
        });
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
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

  Future<Map<String, String>?> _form(String title, List<(String, String)> fields, {Map<String, String> init = const {}}) async {
    final c = {for (final (k, _) in fields) k: TextEditingController(text: init[k] ?? '')};
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final (k, label) in fields)
              TextField(controller: c[k], maxLines: k == 'text' ? 4 : 1, decoration: InputDecoration(labelText: label)),
          ]),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage'))],
      ),
    );
    if (ok != true) return null;
    return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
  }

  Future<void> _settings() async {
    final st = Map<String, dynamic>.from((_day?['settings'] as Map?) ?? const {});
    final f = await _form('Firm ki jaankari', const [
      ('firm', 'Firm ka naam'),
      ('gstin', 'GSTIN'),
      ('address', 'Address'),
      ('phone', 'Phone'),
      ('bank', 'Bank (bill par chhapega)'),
      ('prefix', 'Bill prefix (jaise IT)'),
      ('credit_days', 'Udhaar kitne din (aam)'),
      ('aato', 'Saal ka turnover (Rs)'),
    ], init: {for (final k in ['firm', 'gstin', 'address', 'phone', 'bank', 'prefix']) k: _s(st[k]), 'credit_days': _s(st['credit_days'])});
    if (f == null) return;
    await _run(() => widget.app.api!.thokSettings({
          ...f,
          if (f['credit_days'] != null) 'credit_days': int.tryParse(f['credit_days']!) ?? 15,
          if (f['aato'] != null) 'aato': f['aato'],
        }));
  }

  Future<void> _newParty() async {
    final f = await _form('Nayi party', const [
      ('name', 'Naam'),
      ('phone', 'Mobile'),
      ('gstin', 'GSTIN (ho to)'),
      ('kind', 'customer / supplier'),
      ('credit_limit', 'Credit limit (Rs)'),
      ('credit_days', 'Udhaar din'),
      ('route', 'Route / beat (jaise Mon)'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.thokParty({
          ...f,
          if (f['credit_days'] != null) 'credit_days': int.tryParse(f['credit_days']!),
        }));
  }

  Future<void> _newItem() async {
    final f = await _form('Maal / daam', const [
      ('name', 'Naam (jaise Atta 50kg)'),
      ('price', 'Bechne ka daam (GST ke bina)'),
      ('gst_pct', 'GST % (0 / 5 / 18 / 40)'),
      ('unit', 'Unit (bag / kg / box / tin)'),
      ('qty', 'Abhi stock'),
      ('hsn', 'HSN'),
      ('cost', 'Kharid ka daam'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.thokItem({
          ...f,
          if (f['gst_pct'] != null) 'gst_pct': double.tryParse(f['gst_pct']!) ?? 0,
          if (f['qty'] != null) 'qty': double.tryParse(f['qty']!) ?? 0,
        }));
  }

  Future<void> _newOrder() async {
    final f = await _form('Naya order', const [('party', 'Party ka naam / phone'), ('text', 'Order (jaise: atta 10 bori, cheeni 5 bag)')]);
    if (f == null) return;
    final r = await _run(() => widget.app.api!.thokOrder({'party': f['party'] ?? '', 'text': f['text'] ?? ''}));
    if (r != null && mounted) {
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => Padding(
          padding: const EdgeInsets.all(12),
          child: ThokOrderCard(v: {'order_id': (r['order'] as Map)['id']}, app: widget.app, order: Map<String, dynamic>.from(r['order'] as Map)),
        ),
      );
      _load();
    }
  }

  Future<void> _paid(Map<String, dynamic> p) async {
    final f = await _form('${_s(p['party'])} se paisa mila', const [
      ('amount', 'Rakam'),
      ('mode', 'cash / upi / neft / cheque'),
      ('cheque_no', 'Cheque no (cheque ho to)'),
      ('cheque_date', 'Cheque ki tareekh'),
    ]);
    if (f == null || f['amount'] == null) return;
    await _run(() => widget.app.api!.thokReceive({'party': p['party_id'], ...f}));
  }

  Widget _stat(String k, String v, {Color? c}) => Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(v, style: display(17, color: c ?? C.ink)),
          Text(k, style: const TextStyle(color: C.muted, fontSize: 11.5)),
        ]),
      );

  Widget _today() {
    final d = _day ?? const {};
    final route = Map<String, dynamic>.from((d['route'] as Map?) ?? const {});
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Row(children: [
          _stat('aaj bikri', rs(d['sales'] ?? 0)),
          _stat('vasooli', rs(d['collected'] ?? 0)),
          _stat('bazaar mein', rs(d['outstanding'] ?? 0)),
          _stat('due paar', rs(d['overdue'] ?? 0), c: (d['overdue'] ?? 0) > 0 ? C.warn : null),
        ]),
      ),
      const SizedBox(height: 8),
      Text(_s(d['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
      if (_s(route['say']).isNotEmpty) ...[
        const SizedBox(height: 8),
        Glass(padding: const EdgeInsets.all(12), child: Text('Route: ${_s(route['say'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
      ],
      for (final c in _list(d['deposit']))
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Glass(
            padding: const EdgeInsets.all(10),
            child: Text('Bank mein daaliye: ${_s(c['party'])} cheque ${_s(c['cheque_no'])} ${rs(c['amount'])}'),
          ),
        ),
      for (final b in _list(d['bounced']))
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Glass(
            padding: const EdgeInsets.all(10),
            border: C.bad,
            child: Text('Bounce: ${_s(b['party'])} ${rs(b['amount'])} - notice ${_s(b['notice_by'])} tak (vakil se)'),
          ),
        ),
      if (_drafts.isNotEmpty) ...[
        const SizedBox(height: 12),
        Text('Bill ke liye aapki haan', style: display(15)),
        for (final o in _drafts)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: ThokOrderCard(key: ValueKey('to${o['id']}'), v: {'order_id': o['id']}, app: widget.app, order: o, onDone: _load),
          ),
      ],
    ]);
  }

  Widget _udhaar() {
    final o = _out ?? const {};
    final rows = _list(o['parties']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(_s(o['say']), style: const TextStyle(fontSize: 13)),
      const SizedBox(height: 8),
      GlassButton(
        label: 'Vasooli ke message',
        icon: Icons.send_rounded,
        onTap: _busy
            ? null
            : () async {
                final r = await _run(() => widget.app.api!.thokRead('reminders'));
                if (r != null && mounted) setState(() => _reorder = {'drafts': r['drafts']});
              },
      ),
      for (final d in _list(_reorder?['drafts']))
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Glass(
            padding: const EdgeInsets.all(10),
            child: Row(children: [
              Expanded(child: Text(_s(d['text']), style: const TextStyle(fontSize: 12.5))),
              IconButton(icon: const Icon(Icons.send_rounded), onPressed: () => _wa(_s(d['to']), _s(d['text']))),
            ]),
          ),
        ),
      const SizedBox(height: 8),
      for (final r in rows)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: r['over_limit'] == true || (r['oldest_overdue_days'] ?? 0) > 60 ? C.bad : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(r['party']), style: const TextStyle(fontWeight: FontWeight.w800))),
                Text(rs(r['outstanding']), style: const TextStyle(fontWeight: FontWeight.w800)),
              ]),
              Text(
                  [
                    if ((r['overdue'] ?? 0) > 0) 'due paar ${rs(r['overdue'])} (${r['oldest_overdue_days']} din)',
                    if (r['avg_days_to_pay'] != null) 'aam taur par ${r['avg_days_to_pay']} din mein deta hai',
                    if ((r['cheques_pending'] ?? 0) > 0) 'cheque baaki ${rs(r['cheques_pending'])}',
                  ].join(' · '),
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _paid(r), child: const Text('Paisa mila'))),
            ]),
          ),
        ),
    ]);
  }

  Widget _partiesTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, children: [
          GlassButton(label: 'Nayi party', icon: Icons.person_add_alt_rounded, onTap: _busy ? null : _newParty),
          GlassButton(label: 'Firm', icon: Icons.storefront_rounded, onTap: _busy ? null : _settings),
        ]),
        const SizedBox(height: 8),
        for (final p in _parties)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              child: Row(children: [
                Icon(p['kind'] == 'supplier' ? Icons.local_shipping_rounded : Icons.store_rounded, color: C.accent),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(p['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text([_s(p['gstin']), _s(p['route']), if ((p['credit_limit'] ?? 0) > 0) 'limit ${rs(p['credit_limit'])}'].where((x) => x.isNotEmpty).join(' · '),
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
                if (p['ledger'] != null) Text(rs((p['ledger'] as Map)['outstanding']), style: const TextStyle(fontWeight: FontWeight.w700)),
                if (p['supplier'] != null) Text('dena ${rs((p['supplier'] as Map)['payable'])}', style: const TextStyle(fontSize: 12)),
              ]),
            ),
          ),
      ]);

  Widget _stock() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, children: [
          GlassButton(label: 'Maal jodo', icon: Icons.add_box_rounded, onTap: _busy ? null : _newItem),
          GlassButton(
              label: 'Kya mangwana hai',
              icon: Icons.shopping_cart_checkout_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      final r = await _run(() => widget.app.api!.thokRead('reorder'));
                      if (r != null && mounted) setState(() => _reorder = r);
                    }),
        ]),
        for (final d in _list(_reorder?['drafts']).where((d) => d['supplier'] != null))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              child: Row(children: [
                Expanded(child: Text('${_s(d['supplier'])}:\n${_s(d['text'])}', style: const TextStyle(fontSize: 12.5))),
                IconButton(icon: const Icon(Icons.send_rounded), onPressed: _s(d['to']).isEmpty ? null : () => _wa(_s(d['to']), _s(d['text']))),
              ]),
            ),
          ),
        const SizedBox(height: 8),
        for (final it in _items)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              border: it['low'] == true ? C.warn : null,
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(it['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text('${rs(it['price'])}/${_s(it['unit'])} · GST ${it['gst_pct']}%${_s(it['hsn']).isNotEmpty ? ' · HSN ${it['hsn']}' : ''}'
                        '${it['margin_pct'] != null ? ' · munafa ${it['margin_pct']}%' : ''}',
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
                Text(it['free'] == null ? '-' : '${it['free']}', style: display(15, color: it['low'] == true ? C.warn : C.ink)),
              ]),
            ),
          ),
      ]);

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Thok sahayak')),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: _busy ? null : _newOrder,
          icon: const Icon(Icons.add_shopping_cart_rounded),
          label: const Text('Order'),
        ),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Udhaar'), (2, 'Party'), (3, 'Stock')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_day == null) const Center(child: CircularProgressIndicator()) else [_today(), _udhaar(), _partiesTab(), _stock()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Bill aapki haan se banta hai, message aap bhejti hain. Hoola paisa nahi leta / bhejta. E-way bill aur IRN portal par aap / CA banate hain. '
                  'Rs 2 lakh ya zyada nakad ek party se ek din mein nahi.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// Chat card (`thok_order`): the priced draft with its checks; her Haan makes the bill.
class ThokOrderCard extends StatefulWidget {
  const ThokOrderCard({super.key, required this.v, required this.app, this.order, this.onDone});
  final Map<String, dynamic> v;
  final Santosh app;
  final Map<String, dynamic>? order;
  final VoidCallback? onDone;
  @override
  State<ThokOrderCard> createState() => _ThokOrderCardState();
}

class _ThokOrderCardState extends State<ThokOrderCard> {
  Map<String, dynamic>? _o;
  Map<String, dynamic>? _billed;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _o = widget.order;
    if (_o == null) _fetch();
  }

  Future<void> _fetch() async {
    try {
      final o = await widget.app.api!.thokGetOrder(_s(widget.v['order_id']));
      if (mounted) setState(() => _o = o);
    } catch (_) {}
  }

  Future<void> _act(String a) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.thokOrderAct(_s(widget.v['order_id']), a);
      if (mounted) {
        setState(() {
          if (a == 'bill') _billed = r;
          _o = Map<String, dynamic>.from((r['order'] as Map?) ?? {...?_o, 'status': 'cancelled'});
        });
        _snack(context, _s(r['say']));
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
    final o = _o;
    if (o == null) return const Glass(child: LinearProgressIndicator());
    final ck = Map<String, dynamic>.from((o['checks'] as Map?) ?? const {});
    final credit = Map<String, dynamic>.from((ck['credit'] as Map?) ?? const {});
    final draft = Map<String, dynamic>.from((_billed?['draft'] as Map?) ?? const {});
    return Glass(
      border: credit['level'] == 'stop' ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Icon(Icons.receipt_long_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(o['party']), style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(o['status'] == 'billed' ? _s(o['number']) : _s(o['status'])),
        ]),
        const SizedBox(height: 6),
        for (final l in _list(o['lines']))
          Text('${_s(l['item'])}  ${l['qty']} ${_s(l['unit'])} x ${rs(l['rate'])}  = ${rs(l['taxable'])}${l['short'] == true ? '  (stock kam)' : ''}',
              style: TextStyle(fontSize: 12.5, color: l['short'] == true ? C.warn : C.ink)),
        const SizedBox(height: 4),
        Text('GST ${rs(o['tax'])} (${o['intra'] == true ? 'CGST+SGST' : 'IGST'}) · Kul ${rs(o['total'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
        if (credit.isNotEmpty) Text(_s(credit['text']), style: TextStyle(fontSize: 12.5, color: _lvl(_s(credit['level'])))),
        if (((ck['missing'] as List?) ?? const []).isNotEmpty) Text('List mein nahi: ${(ck['missing'] as List).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if ((ck['eway'] as Map?)?['needed'] == true) const Text('E-way bill chahiye (portal par aap banayengi).', style: TextStyle(fontSize: 12.5, color: C.warn)),
        if (ck['einvoice'] == true) const Text('IRN (e-invoice) bhi chahiye.', style: TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (o['status'] == 'draft')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, bill banao', icon: Icons.check_rounded, onTap: _busy ? null : () => _act('bill'))),
            const SizedBox(width: 8),
            TextButton(onPressed: _busy ? null : () => _act('cancel'), child: const Text('Cancel')),
          ]),
        if (draft.isNotEmpty)
          GlassButton(label: 'Party ko WhatsApp', icon: Icons.send_rounded, onTap: () => _wa(_s(draft['to']), _s(draft['text']))),
      ]),
    );
  }
}

/// Chat card for `thok_alert` / `thok_day`.
class ThokCard extends StatelessWidget {
  const ThokCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ThokScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.warehouse_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(v['text']), style: const TextStyle(fontWeight: FontWeight.w700))),
            const Icon(Icons.chevron_right_rounded, color: C.muted),
          ]),
        ),
      );
}
