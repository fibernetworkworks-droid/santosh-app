/// Profile > Godown Sahayak (warehouse manager): stock by bin, aamad (GRN) + putaway, pick lists with a walking path, cycle
/// counts (blind), and stock badlav / write-off cards that change the stock ONLY after her tap. Hoola never moves money.
/// Tabs: Aaj · Bin · Aamad · Pick · Ginti · Niyam. Cards: WarehouseAdjustCard, WarehouseGrnCard, WarehousePickCard,
/// WarehouseCountCard, WarehouseDayCard.
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'desk/desk_kit.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
double? _n(String? v) => v == null ? null : double.tryParse(v.replaceAll(',', '').trim());
String _q(dynamic v) {
  final d = v is num ? v.toDouble() : double.tryParse(_s(v));
  if (d == null) return _s(v);
  return d == d.roundToDouble() ? d.toInt().toString() : d.toStringAsFixed(2);
}

String _rs(dynamic v) {
  if (v == null) return 'price not known';
  final d = v is num ? v.toDouble() : double.tryParse('$v') ?? 0;
  final neg = d < 0;
  final s = d.abs().round().toString();
  String out = s;
  if (s.length > 3) {
    final head = s.substring(0, s.length - 3);
    final tail = s.substring(s.length - 3);
    final b = StringBuffer();
    for (var i = 0; i < head.length; i++) {
      if (i > 0 && (head.length - i) % 2 == 0) b.write(',');
      b.write(head[i]);
    }
    out = '$b,$tail';
  }
  return '${neg ? '-' : ''}₹$out';
}

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {String ok = 'Aage'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'text' ? 4 : 1),
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

class WarehouseScreen extends StatefulWidget {
  const WarehouseScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<WarehouseScreen> createState() => _WarehouseScreenState();
}

class _WarehouseScreenState extends State<WarehouseScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/warehouse'));
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

  // ---------------------------------------------------------------- Aaj
  Widget _today() {
    final d = _d ?? const {};
    final ne = _m(d['near_expiry']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      for (final a in _list(d['adjusts']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: WarehouseAdjustCard(app: widget.app, data: {'adjust': a}, onDone: _load)),
      if (_list(d['due']).isNotEmpty) ...[
        Text('Counting time', style: display(14)),
        for (final x in _list(d['due']).take(10))
          Text('• [${_s(x['abc'])}] ${_s(x['name'])}${_s(x['last_counted']).isEmpty ? ' (never counted)' : ' (last: ${_s(x['last_counted'])})'}',
              style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 6),
        GlassButton(label: 'Make today\'s count', icon: Icons.fact_check_rounded, height: 42, onTap: _busy ? null : () => _run('POST', '/api/warehouse/counts', {})),
        const SizedBox(height: 10),
      ],
      for (final l in _list(ne['expired']))
        Text('• EXPIRED: ${_s(l['name'])} ${_s(l['batch'])} (${_s(l['bin'])}) ${_q(l['qty'])}', style: const TextStyle(fontSize: 12.5, color: C.bad)),
      for (final l in _list(ne['near']).take(10))
        Text('• ${_s(l['name'])} ${_s(l['batch'])} (${_s(l['bin'])}): ${l['days_left']} days to expiry', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      for (final r in _list(d['recon']).take(10))
        Text('• ${_s(r['name'])}: in bins ${_q(r['in_bins'])}, in the stock list ${_q(r['stock_list'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final (w, label) in const [('stock', 'Stock Excel'), ('ledger', 'Ledger'), ('abc', 'ABC'), ('expiry', 'Expiry'), ('slow', 'Stock on hand')])
          ActionChip(label: Text(label), onPressed: _busy ? null : () => _run('POST', '/api/warehouse/export', {'what': w})),
      ]),
    ]);
  }

  // ---------------------------------------------------------------- Bin
  Future<void> _newBins() async {
    final f = await _form(context, 'Naye bin', const [
      ('zone', 'Zone (jaise A)'),
      ('aisles', 'How many aisles'),
      ('racks', 'Racks per aisle'),
      ('capacity', 'How much stock per bin (units)'),
    ], ok: 'Make');
    if (f == null) return;
    await _run('POST', '/api/warehouse/bins', {
      'many': true,
      'zone': f['zone'] ?? '',
      'aisles': int.tryParse(f['aisles'] ?? '1') ?? 1,
      'racks': int.tryParse(f['racks'] ?? '1') ?? 1,
      if (_n(f['capacity']) != null) 'capacity': _n(f['capacity']),
    });
  }

  Future<void> _move() async {
    final f = await _form(context, 'Move stock', const [('item', 'Item'), ('from_bin', 'From which bin'), ('to_bin', 'To which bin'), ('qty', 'How much'), ('batch', 'Batch (if any)')],
        ok: 'Move');
    if (f == null) return;
    await _run('POST', '/api/warehouse/move', {...f, 'qty': _n(f['qty'])});
  }

  Future<void> _writeoff() async {
    final f = await _form(context, 'Damaged / expired / lost goods', const [
      ('item', 'Item'),
      ('bin', 'Bin'),
      ('qty', 'How much'),
      ('batch', 'Batch (if any)'),
      ('reason', 'Reason: damaged / expired / lost / theft / sample / other'),
      ('note', 'Note'),
    ], ok: 'Make card');
    if (f == null) return;
    await _run('POST', '/api/warehouse/writeoff', {...f, 'qty': _n(f['qty'])});
  }

  Widget _bins() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Naye bin', icon: Icons.grid_view_rounded, height: 42, onTap: _busy ? null : _newBins),
          GlassButton(label: 'Move stock', icon: Icons.swap_horiz_rounded, height: 42, onTap: _busy ? null : _move),
          GlassButton(label: 'Write-off card', icon: Icons.delete_sweep_rounded, height: 42, onTap: _busy ? null : _writeoff),
          GlassButton(label: 'Bin labels', icon: Icons.qr_code_2_rounded, height: 42, onTap: _busy ? null : () => _run('POST', '/api/warehouse/labels', {'what': 'bins'})),
          GlassButton(label: 'SKU labels', icon: Icons.qr_code_rounded, height: 42, onTap: _busy ? null : () => _run('POST', '/api/warehouse/labels', {'what': 'skus'})),
        ]),
        const SizedBox(height: 10),
        if (_list(_d?['bins']).isEmpty) const Text('No bins yet.', style: TextStyle(color: C.muted)),
        for (final b in _list(_d?['bins']))
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Press(
              onTap: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => WarehouseBinPage(app: widget.app, code: _s(b['code']))))
                  .then((_) => _load()),
              child: Glass(
                padding: const EdgeInsets.all(10),
                border: (b['full_pct'] ?? 0) >= 95 ? C.warn : null,
                child: Row(children: [
                  SizedBox(width: 90, child: Text(_s(b['code']), style: const TextStyle(fontWeight: FontWeight.w800))),
                  Expanded(child: Text('${_s(b['kind_label'])} · ${b['skus']} item', style: const TextStyle(fontSize: 12.5, color: C.muted))),
                  Text(b['capacity'] == null ? _q(b['used']) : '${_q(b['used'])}/${_q(b['capacity'])}', style: const TextStyle(fontSize: 12.5)),
                ]),
              ),
            ),
          ),
      ]);

  // ---------------------------------------------------------------- Aamad (GRN)
  Future<void> _grn() async {
    final f = await _form(context, 'Goods received (GRN)', const [
      ('text', 'What arrived (e.g. flour 50 bags, biscuits 20 ctn)'),
      ('supplier', 'Supplier'),
      ('doc', 'Challan / PO / bill no'),
    ], ok: 'Save');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '/api/warehouse/grns', f);
  }

  Widget _inward() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GradientButton(label: 'Goods received', icon: Icons.move_to_inbox_rounded, height: 46, onTap: _busy ? null : _grn),
        const SizedBox(height: 6),
        const Text('If you have a photo of the challan, send it in the chat: Hoola will read it and record it here (with batch / expiry).',
            style: TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 10),
        for (final g in _list(_d?['grns']))
          Padding(padding: const EdgeInsets.only(bottom: 8), child: WarehouseGrnCard(app: widget.app, data: {'grn': g}, onDone: _load)),
      ]);

  // ---------------------------------------------------------------- Pick
  Future<void> _pick(String source) async {
    if (source == 'list') {
      final f = await _form(context, 'Pick list', const [('text', 'What to pick (flour 10 bags, biscuits 5 ctn)'), ('party', 'For whom')], ok: 'Make');
      if (f == null || (f['text'] ?? '').isEmpty) return;
      await _run('POST', '/api/warehouse/picks', {'source': 'list', ...f});
    } else {
      await _run('POST', '/api/warehouse/picks', {'source': source});
    }
  }

  Widget _picks() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Your own list', icon: Icons.list_alt_rounded, height: 42, onTap: _busy ? null : () => _pick('list')),
          GlassButton(label: 'Hoola Deals orders', icon: Icons.storefront_rounded, height: 42, onTap: _busy ? null : () => _pick('deal')),
          GlassButton(label: 'Thok bills', icon: Icons.receipt_long_rounded, height: 42, onTap: _busy ? null : () => _pick('thok')),
        ]),
        const SizedBox(height: 10),
        if (_list(_d?['picks']).isEmpty) const Text('No open pick lists.', style: TextStyle(color: C.muted)),
        for (final p in _list(_d?['picks']))
          Padding(padding: const EdgeInsets.only(bottom: 8), child: WarehousePickCard(app: widget.app, data: {'pick': p}, onDone: _load)),
      ]);

  // ---------------------------------------------------------------- Ginti
  Widget _counts() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GradientButton(label: 'Today\'s count', icon: Icons.fact_check_rounded, height: 44, onTap: _busy ? null : () => _run('POST', '/api/warehouse/counts', {})),
          GlassButton(
              label: 'Choose bins',
              icon: Icons.pin_drop_rounded,
              height: 44,
              onTap: _busy
                  ? null
                  : () async {
                      final f = await _form(context, 'Which bins to count', const [('bins', 'Bin (comma se: A-1-1, A-1-2)')], ok: 'Make');
                      if (f == null) return;
                      await _run('POST', '/api/warehouse/counts',
                          {'bins': (f['bins'] ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList()});
                    }),
          GlassButton(label: 'Redo ABC', icon: Icons.sort_rounded, height: 44, onTap: _busy ? null : () => _run('POST', '/api/warehouse/classify')),
        ]),
        const SizedBox(height: 6),
        const Text('The count is "blind": the sheet does not show the system quantity. If there is a difference, a change card will wait for your tap.',
            style: TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 10),
        for (final c in _list(_d?['counts']))
          Padding(padding: const EdgeInsets.only(bottom: 8), child: WarehouseCountCard(app: widget.app, data: {'count': c}, onDone: _load)),
      ]);

  // ---------------------------------------------------------------- Niyam
  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final cd = _m(st['count_days']);
    final f = await _form(context, 'Godown rules', [
      ('name', 'Godown name (${_s(st['name'])})'),
      ('A', 'Count A items every how many days (${_s(cd['A'])})'),
      ('B', 'B item (${_s(cd['B'])})'),
      ('C', 'C item (${_s(cd['C'])})'),
      ('near_expiry_days', 'Warn about expiry how many days before (${_s(st['near_expiry_days'])})'),
      ('count_bins_per_day', 'How many bins to count each day (${_s(st['count_bins_per_day'])})'),
      ('morning_time', 'Subah ka note (${_s(st['morning_time'])})'),
    ], ok: 'Save');
    if (f == null) return;
    await _run('PUT', '/api/warehouse/settings', {
      if (f['name'] != null) 'name': f['name'],
      if (f['A'] != null || f['B'] != null || f['C'] != null)
        'count_days': {for (final k in ['A', 'B', 'C']) if (f[k] != null) k: int.tryParse(f[k]!) ?? 0},
      if (f['near_expiry_days'] != null) 'near_expiry_days': int.tryParse(f['near_expiry_days']!) ?? 30,
      if (f['count_bins_per_day'] != null) 'count_bins_per_day': int.tryParse(f['count_bins_per_day']!) ?? 10,
      if (f['morning_time'] != null) 'morning_time': f['morning_time'],
    });
  }

  Widget _rules() {
    final st = _m(_d?['settings']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      GlassButton(label: 'Niyam badlo', icon: Icons.tune_rounded, height: 42, onTap: _busy ? null : _settings),
      const SizedBox(height: 8),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('We keep food items (FSSAI)'),
        value: st['food'] == true,
        onChanged: _busy ? null : (v) => _run('PUT', '/api/warehouse/settings', {'food': v}),
      ),
      for (final n in (st['never'] as List? ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 6),
      for (final n in (st['notes'] as List? ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    // v0.869 R8 wave 2: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'Warehouse',
      tabs: const ['Today', 'Bin', 'Receipts', 'Pick', 'Count', 'Rules'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      busy: _busy,
      onRefresh: _load,
      body: () => ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
        [_today(), _bins(), _inward(), _picks(), _counts(), _rules()][_tab],
        const SizedBox(height: 14),
        const Text('Changing stock counts / write-offs happen only with your tap. Prices come from the stock list (Hoola Deals). Hoola does not pay money.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

// ---------------------------------------------------------------- bin page
class WarehouseBinPage extends StatefulWidget {
  const WarehouseBinPage({super.key, required this.app, required this.code});
  final Santosh app;
  final String code;
  @override
  State<WarehouseBinPage> createState() => _WarehouseBinPageState();
}

class _WarehouseBinPageState extends State<WarehouseBinPage> {
  Map<String, dynamic>? _b;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = _m(await widget.app.api!.call('GET', '/api/warehouse/bins/${Uri.encodeComponent(widget.code)}'));
      if (mounted) setState(() => _b = b);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('Bin ${widget.code}')),
      body: Aurora(
        child: b == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.all(16), children: [
                Glass(
                  child: Text('${_s(b['kind_label'])} · ${b['capacity'] == null ? _q(b['used']) : '${_q(b['used'])}/${_q(b['capacity'])}'} units',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
                const SizedBox(height: 8),
                for (final l in _list(b['lots']))
                  Text('• ${_s(l['name'])} ${_q(l['qty'])} ${_s(l['unit'])}${_s(l['batch']).isNotEmpty ? ' · batch ${_s(l['batch'])}' : ''}'
                      '${_s(l['expiry']).isNotEmpty ? ' · exp ${_s(l['expiry'])}' : ''}${(l['serials'] as List? ?? const []).isNotEmpty ? ' · ${(l['serials'] as List).length} serial' : ''}',
                      style: const TextStyle(fontSize: 13)),
                const SizedBox(height: 12),
                Text('Latest activity', style: display(14)),
                for (final m in _list(b['moves']))
                  Text('${_s(m['day'])} ${_s(m['kind'])} ${_s(m['name'])} ${_q(m['qty'])} ${_s(m['ref'])} · ${_s(m['by'])}',
                      style: const TextStyle(fontSize: 12, color: C.muted)),
              ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- cards
/// warehouse_adjust: a stock change after a count / a write-off. ONLY her tap here changes the stock.
class WarehouseAdjustCard extends StatefulWidget {
  const WarehouseAdjustCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<WarehouseAdjustCard> createState() => _WarehouseAdjustCardState();
}

class _WarehouseAdjustCardState extends State<WarehouseAdjustCard> {
  bool _busy = false;
  late String _status = _s(_m(widget.data['adjust'])['status']);

  Future<void> _decide(bool yes) async {
    final a = _m(widget.data['adjust']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not? (optional)', const [('reason', 'Reason')], ok: 'Decline');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/warehouse/adjustments/${_s(a['id'])}/decide', {'yes': yes, 'hash': _s(a['hash']), 'reason': reason});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null) _status = _s(r['status']);
      });
    }
    widget.onDone?.call();
  }

  Future<void> _recount(String count) async {
    setState(() => _busy = true);
    await _call(context, widget.app, 'POST', '/api/warehouse/counts/$count/recount');
    if (mounted) setState(() => _busy = false);
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final a = _m(widget.data['adjust']);
    final first = (a['recount_first'] as List? ?? const []);
    return Glass(
      border: _status == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_s(a['kind']) == 'writeoff' ? Icons.delete_sweep_rounded : Icons.inventory_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('Stock change · ${_s(a['number'])}${_s(a['count']).isNotEmpty ? ' (${_s(a['count'])})' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(a['kind']) == 'writeoff' ? 'write-off' : 'count'),
        ]),
        const SizedBox(height: 6),
        for (final l in _list(a['lines']))
          Text(
              '• ${_s(l['bin'])} ${_s(l['name'])}${_s(l['batch']).isNotEmpty ? ' (${_s(l['batch'])})' : ''}: '
              'record ${_q(l['system'])} -> gina ${_q(l['counted'])} (${(l['diff'] as num? ?? 0) > 0 ? '+' : ''}${_q(l['diff'])})'
              '${l['value'] != null ? ' · ${_rs(l['value'])}' : ''}${_s(l['note']).isNotEmpty ? ' · ${_s(l['note'])}' : ''}',
              style: TextStyle(fontSize: 12.5, color: (l['diff'] as num? ?? 0) < 0 ? C.warn : C.ok)),
        const SizedBox(height: 4),
        Text('Total: ${_rs(a['value'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
        if (first.isNotEmpty) Text('Difference beyond the limit: ${first.join(', ')} - better to recount first.', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(a['itc_note']).isNotEmpty) Text(_s(a['itc_note']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
        const SizedBox(height: 8),
        if (_status == 'waiting') ...[
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, change the stock', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ]),
          if (_s(a['count']).isNotEmpty)
            TextButton(onPressed: _busy ? null : () => _recount(_s(a['count'])), child: const Text('Recount first')),
        ] else
          Text(
              switch (_status) {
                'approved' => 'Stock changed with your yes.',
                'rejected' => 'Declined: stock stays as it was.',
                'stale' => 'Stock moved or was recounted after the card: a new card will come.',
                _ => _status,
              },
              style: TextStyle(color: _status == 'approved' ? C.ok : C.muted, fontSize: 12.5)),
      ]),
    );
  }
}

/// warehouse_grn: what came in + where to put it.
class WarehouseGrnCard extends StatefulWidget {
  const WarehouseGrnCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<WarehouseGrnCard> createState() => _WarehouseGrnCardState();
}

class _WarehouseGrnCardState extends State<WarehouseGrnCard> {
  bool _busy = false;
  late String _status = _s(_m(widget.data['grn'])['status']);

  Future<void> _putaway() async {
    final g = _m(widget.data['grn']);
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/warehouse/grns/${_s(g['id'])}/putaway', {});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null) _status = 'putaway';
      });
    }
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final g = _m(widget.data['grn']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.move_to_inbox_rounded, color: C.teal),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(g['number'])}${_s(g['supplier']).isNotEmpty ? ' · ${_s(g['supplier'])}' : ''}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status == 'putaway' ? 'put away' : 'rakhna baaki'),
        ]),
        const SizedBox(height: 4),
        for (final l in _list(g['lines'])) ...[
          Text('• ${_s(l['name'])} ${_q(l['qty'])} ${_s(l['unit'])}${_s(l['batch']).isNotEmpty ? ' · ${_s(l['batch'])}' : ''}${_s(l['expiry']).isNotEmpty ? ' · exp ${_s(l['expiry'])}' : ''}',
              style: const TextStyle(fontSize: 12.5)),
          for (final p in _list(l['putaway']))
            Text('    -> ${_s(p['bin']).isEmpty ? 'no place' : _s(p['bin'])} ${_q(p['qty'])} (${_s(p['why'])})', style: const TextStyle(fontSize: 12, color: C.muted)),
          for (final n in (l['notes'] as List? ?? const [])) Text('    ! $n', style: const TextStyle(fontSize: 12, color: C.warn)),
        ],
        for (final n in (g['notes'] as List? ?? const [])) Text('! $n', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(_m(g['draft'])['text']).isNotEmpty)
          Text('Draft for the supplier (you send it): ${_s(_m(g['draft'])['text'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_status != 'putaway') ...[
          const SizedBox(height: 8),
          GradientButton(label: 'Yes, keep it this way', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : _putaway),
        ],
      ]),
    );
  }
}

/// warehouse_pick: walking-order pick list; the picker ticks / types what was really picked.
class WarehousePickCard extends StatefulWidget {
  const WarehousePickCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<WarehousePickCard> createState() => _WarehousePickCardState();
}

class _WarehousePickCardState extends State<WarehousePickCard> {
  bool _busy = false;
  late Map<String, dynamic> _p = _m(widget.data['pick']);
  final Map<int, TextEditingController> _c = {};

  @override
  void dispose() {
    for (final c in _c.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _confirm({bool finish = false}) async {
    final picked = <Map<String, dynamic>>[];
    for (final t in _list(_p['tasks'])) {
      if (t['done'] == true) continue;
      final n = (t['n'] as num?)?.toInt() ?? 0;
      final txt = _c[n]?.text.trim() ?? '';
      picked.add({'n': n, if (txt.isNotEmpty) 'qty': _n(txt)});
    }
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/warehouse/picks/${_s(_p['id'])}/confirm', {'picked': picked, 'finish': finish});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['id'] != null) _p = r;
      });
    }
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final open = _s(_p['status']) == 'open';
    return Glass(
      border: open ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.route_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('Pick ${_s(_p['number'])}${_p['wave'] == true ? ' · wave (${(_p['orders'] as List? ?? const []).length} order)' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(_p['status'])),
        ]),
        const SizedBox(height: 4),
        for (final t in _list(_p['tasks']))
          Row(children: [
            SizedBox(width: 26, child: Text('${t['n']}.', style: const TextStyle(fontSize: 12.5))),
            Expanded(
                child: Text('${_s(t['bin'])} · ${_s(t['name'])} ${_q(t['qty'])}${_s(t['batch']).isNotEmpty ? ' (${_s(t['batch'])})' : ''}',
                    style: TextStyle(fontSize: 12.5, color: t['done'] == true ? C.muted : C.ink))),
            if (t['done'] == true)
              Text('picked ${_q(t['picked'])}', style: TextStyle(fontSize: 12, color: (t['short'] ?? 0) > 0 ? C.warn : C.ok))
            else if (open)
              SizedBox(
                width: 64,
                child: TextField(
                  controller: _c.putIfAbsent((t['n'] as num?)?.toInt() ?? 0, () => TextEditingController()),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(isDense: true, hintText: _q(t['qty'])),
                ),
              ),
          ]),
        for (final l in _list(_p['lines']).where((l) => ((l['short'] ?? 0) as num) > 0))
          Text('Short: ${_s(l['name'])} ${_q(l['short'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
        for (final n in (_p['notes'] as List? ?? const [])) Text('! $n', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (open) ...[
          const SizedBox(height: 8),
          const Text('Blank = all of it was picked. If less was found, write the quantity.', style: TextStyle(fontSize: 11.5, color: C.faint)),
          Row(children: [
            Expanded(child: GradientButton(label: 'Picked', icon: Icons.done_all_rounded, height: 42, onTap: _busy ? null : () => _confirm())),
            const SizedBox(width: 8),
            Expanded(
                child: GlassButton(
                    label: 'Sheet (PDF)',
                    icon: Icons.picture_as_pdf_rounded,
                    height: 42,
                    onTap: _busy ? null : () => _call(context, widget.app, 'POST', '/api/warehouse/picks/${_s(_p['id'])}/sheet'))),
          ]),
        ],
      ]),
    );
  }
}

/// warehouse_count: a blind count sheet; quantities are typed here, the system figure is never shown.
class WarehouseCountCard extends StatefulWidget {
  const WarehouseCountCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<WarehouseCountCard> createState() => _WarehouseCountCardState();
}

class _WarehouseCountCardState extends State<WarehouseCountCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['count']);
  final Map<int, TextEditingController> _t = {};

  @override
  void dispose() {
    for (final c in _t.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save({bool close = false}) async {
    final entries = <Map<String, dynamic>>[];
    final lines = _list(_c['lines']);
    for (var i = 0; i < lines.length; i++) {
      final v = _n(_t[i]?.text);
      if (v == null) continue;
      final l = lines[i];
      entries.add({'bin': l['bin'], 'item': l['sku'], 'batch': l['batch'], 'qty': v});
    }
    setState(() => _busy = true);
    final id = _s(_c['id']);
    if (entries.isNotEmpty) await _call(context, widget.app, 'POST', '/api/warehouse/counts/$id/enter', {'entries': entries});
    if (close && mounted) await _call(context, widget.app, 'POST', '/api/warehouse/counts/$id/close', {});
    try {
      final v = _m(await widget.app.api!.call('GET', '/api/warehouse/counts/$id'));
      if (mounted && v['id'] != null) setState(() => _c = v);
    } catch (_) {}
    if (mounted) setState(() => _busy = false);
    widget.onDone?.call();
  }

  Future<void> _found() async {
    final f = await _form(context, 'Found more in the bin', const [('bin', 'Bin'), ('item', 'Item'), ('batch', 'Batch (if any)'), ('qty', 'How much')], ok: 'Write');
    if (f == null || _n(f['qty']) == null || !mounted) return;
    await _call(context, widget.app, 'POST', '/api/warehouse/counts/${_s(_c['id'])}/enter', {
      'entries': [
        {...f, 'qty': _n(f['qty'])}
      ]
    });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final open = _s(_c['status']) == 'open';
    final lines = _list(_c['lines']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.fact_check_rounded, color: C.teal),
          const SizedBox(width: 8),
          Expanded(child: Text('Count ${_s(_c['number'])} · ${_s(_c['kind'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill('${_c['counted'] ?? 0}/${_c['total'] ?? 0}'),
        ]),
        Text('Bin: ${(_c['bins'] as List? ?? const []).join(', ')}', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 4),
        for (var i = 0; i < lines.length; i++)
          Row(children: [
            Expanded(
                child: Text('${_s(lines[i]['bin'])} · ${_s(lines[i]['name'])}${_s(lines[i]['batch']).isNotEmpty ? ' (${_s(lines[i]['batch'])})' : ''}',
                    style: const TextStyle(fontSize: 12.5))),
            if (lines[i]['counted'] != null)
              Text('gina ${_q(lines[i]['counted'])}', style: const TextStyle(fontSize: 12, color: C.ok))
            else if (open)
              SizedBox(
                width: 64,
                child: TextField(
                  controller: _t.putIfAbsent(i, () => TextEditingController()),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(isDense: true, hintText: 'how much?'),
                ),
              ),
          ]),
        if (open) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'Write', icon: Icons.save_rounded, height: 40, onTap: _busy ? null : () => _save()),
            GlassButton(label: 'Found more', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : _found),
            GlassButton(
                label: 'Sheet (PDF)',
                icon: Icons.picture_as_pdf_rounded,
                height: 40,
                onTap: _busy ? null : () => _call(context, widget.app, 'POST', '/api/warehouse/counts/${_s(_c['id'])}/sheet')),
            GradientButton(label: 'Close', icon: Icons.done_rounded, height: 40, onTap: _busy ? null : () => _save(close: true)),
          ]),
        ] else
          const Text('Count closed: if there is a difference, a change card will wait for your tap.', style: TextStyle(fontSize: 12, color: C.muted)),
      ]),
    );
  }
}

/// warehouse_day: morning note.
class WarehouseDayCard extends StatelessWidget {
  const WarehouseDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final ne = _m(data['near_expiry']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.warehouse_rounded, color: C.accent),
          SizedBox(width: 8),
          Expanded(child: Text('Today\'s godown note', style: TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
        for (final x in _list(data['due']).take(5)) Text('• ginna: [${_s(x['abc'])}] ${_s(x['name'])}', style: const TextStyle(fontSize: 12.5)),
        for (final l in _list(ne['near']).take(5))
          Text('• ${_s(l['name'])} (${_s(l['bin'])}): ${l['days_left']} days to expiry', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        GlassButton(
            label: 'Open godown',
            icon: Icons.open_in_new_rounded,
            height: 40,
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => WarehouseScreen(app: app)))),
      ]),
    );
  }
}
