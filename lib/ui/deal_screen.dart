import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.102 Hoola Deals: buying a list of items from another avatar, and selling to one.
/// The quote, its sums, the stock and the expiry are worked out by the server's code; the order is placed only by
/// her tap on "Haan, confirm" (fingerprint-signed once a phone is set up), and the seller's Hoola accepts by itself
/// only inside the seller's own written rule.

String _s(dynamic v) => v == null ? '' : '$v';
double _d(dynamic v) => v is num ? v.toDouble() : (double.tryParse('$v') ?? 0);
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Map<String, dynamic> _m(dynamic x) => x is Map ? Map<String, dynamic>.from(x) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic x) =>
    List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

String _inr(dynamic v) {
  final x = _d(v);
  final neg = x < 0;
  final whole = x.abs().floor();
  final paise = ((x.abs() - whole) * 100).round();
  var s = '$whole';
  if (s.length > 3) {
    final last = s.substring(s.length - 3);
    var rest = s.substring(0, s.length - 3);
    final parts = <String>[];
    while (rest.length > 2) {
      parts.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) parts.insert(0, rest);
    s = '${parts.join(',')},$last';
  }
  return '${neg ? '-' : ''}₹$s${paise > 0 ? '.${paise.toString().padLeft(2, '0')}' : ''}';
}

String _qty(dynamic v) {
  final x = _d(v);
  return x == x.roundToDouble() ? '${x.toInt()}' : x.toStringAsFixed(2);
}

String _when(dynamic iso) {
  final t = DateTime.tryParse(_s(iso));
  if (t == null) return '';
  final l = t.toLocal();
  final h = l.hour % 12 == 0 ? 12 : l.hour % 12;
  final now = DateTime.now();
  final day = (l.year == now.year && l.month == now.month && l.day == now.day) ? 'aaj' : '${l.day}/${l.month}';
  return '$day $h:${l.minute.toString().padLeft(2, '0')} ${l.hour < 12 ? 'am' : 'pm'}';
}

const _stateColor = {
  'asked': C.chip, 'quoted': C.accent, 'confirmed': C.violet, 'accepted': C.teal, 'packing': C.teal, 'ready': C.ok,
  'handed_over': C.ok, 'rejected': C.bad, 'cancelled': C.muted, 'expired': C.muted,
};

const _lineWord = {
  'partial': 'kam hai', 'out': 'khatam', 'not_found': 'nahi hai', 'unknown_stock': 'stock pata nahi', 'substitute': 'badle mein',
};

/// One deal as a chat card (also inside the voice call). [full] = the deal page (history, every action).
class DealCard extends StatefulWidget {
  const DealCard({super.key, required this.v, required this.app, this.full = false, this.onChanged});
  final Map<String, dynamic> v;
  final Santosh app;
  final bool full;
  final VoidCallback? onChanged;
  @override
  State<DealCard> createState() => _DealCardState();
}

class _DealCardState extends State<DealCard> {
  Map<String, dynamic>? _fresh;
  bool _busy = false;
  final _code = TextEditingController();

  Map<String, dynamic> get v => _fresh ?? widget.v;

  @override
  void didUpdateWidget(covariant DealCard old) {
    super.didUpdateWidget(old);
    if (old.v != widget.v) _fresh = null;     // a newer server event replaced the card's data
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.netDealAct(_s(v['id']), action, body);
      final d = r['deal'];
      if (mounted && d is Map) setState(() => _fresh = Map<String, dynamic>.from(d));
      widget.onChanged?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _ask(String title, String hint) async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, minLines: 1, maxLines: 3, decoration: InputDecoration(hintText: hint)),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Theek hai')),
        ],
      ),
    );
    final t = c.text.trim();
    c.dispose();
    return ok == true ? t : null;
  }

  Widget _lines(Map<String, dynamic> q) {
    final lines = _l(q['lines']);
    if (lines.isEmpty) return const SizedBox.shrink();
    return Column(children: [
      for (final ln in lines)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(ln['item']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                Text(
                  [
                    if (ln['price'] != null) '${_qty(ln['qty'])} ${_s(ln['unit'])} × ${_inr(ln['price'])}'.replaceAll('  ', ' '),
                    if (_d(ln['gst_pct']) > 0) 'GST ${_qty(ln['gst_pct'])}%',
                    if (_d(ln['asked']) != _d(ln['qty']) && _s(ln['status']) != 'substitute') 'maanga ${_qty(ln['asked'])}',
                    if (_s(ln['asked_as']).isNotEmpty) '"${_s(ln['asked_as'])}"',
                  ].join(' · '),
                  style: const TextStyle(color: C.muted, fontSize: 12),
                ),
              ]),
            ),
            const SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text(ln['price'] == null ? '—' : _inr(_d(ln['amount']) + _d(ln['gst'])),
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              if (_lineWord[_s(ln['status'])] != null)
                Padding(
                  padding: const EdgeInsets.only(top: 3),
                  child: Pill(_lineWord[_s(ln['status'])]!, fg: _s(ln['status']) == 'substitute' ? C.teal : C.warn),
                ),
            ]),
          ]),
        ),
    ]);
  }

  Widget _totals(Map<String, dynamic> q) {
    if (q['total'] == null) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.only(top: 8),
      decoration: const BoxDecoration(border: Border(top: BorderSide(color: C.line))),
      child: Row(children: [
        Expanded(
          child: Text('${_inr(q['subtotal'])} + GST ${_inr(q['gst'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ),
        Text(_inr(q['total']), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: C.accent)),
      ]),
    );
  }

  List<Widget> _buttons() {
    final acts = List<String>.from((v['actions'] as List?) ?? const []);
    final buyer = _s(v['role']) == 'buyer';
    final st = _s(v['state']);
    final q = _m(v['quote']);
    final out = <Widget>[];
    void add(Widget w) {
      if (out.isNotEmpty) out.add(const SizedBox(height: 8));
      out.add(w);
    }

    if (buyer && acts.contains('confirm')) {
      add(GradientButton(
          label: 'Haan, confirm · ${_inr(q['total'])}',
          icon: Icons.check_rounded,
          height: 50,
          onTap: _busy ? null : () => _act('confirm', {'v': q['v']})));
    }
    if (!buyer && acts.contains('send_quote') && _s(v['waiting']) == 'quote') {
      add(GradientButton(label: 'Quote bhejo', icon: Icons.send_rounded, height: 50, onTap: _busy ? null : () => _act('send_quote')));
    }
    if (!buyer && acts.contains('accept')) {
      add(GradientButton(label: 'Order pakka karo', icon: Icons.check_rounded, height: 50, onTap: _busy ? null : () => _act('accept')));
    }
    if (!buyer && acts.contains('packing') && st == 'accepted') {
      add(GlassButton(label: 'Packing shuru', icon: Icons.inventory_2_rounded, onTap: _busy ? null : () => _act('packing')));
    }
    if (!buyer && acts.contains('ready')) {
      add(GradientButton(label: 'Parcel taiyaar', icon: Icons.local_shipping_rounded, height: 50, onTap: _busy ? null : () => _act('ready')));
    }
    if (!buyer && acts.contains('handed_over')) {
      add(Row(children: [
        Expanded(
          child: TextField(
            controller: _code,
            keyboardType: TextInputType.number,
            maxLength: 4,
            decoration: const InputDecoration(labelText: 'Graahak ka pickup code', counterText: ''),
          ),
        ),
        const SizedBox(width: 10),
        GlassButton(
            label: 'De diya',
            icon: Icons.handshake_rounded,
            onTap: _busy ? null : () => _act('handed_over', {'code': _code.text.trim()})),
      ]));
    }
    final no = <Widget>[];
    if (acts.contains('reject')) {
      no.add(TextButton(
          onPressed: _busy
              ? null
              : () async {
                  final r = await _ask('Mana karna hai?', 'Wajah (graahak ko dikhegi)');
                  if (r != null) _act('reject', {'reason': r});
                },
          child: const Text('Mana karo', style: TextStyle(color: C.bad))));
    }
    if (acts.contains('cancel')) {
      no.add(TextButton(
          onPressed: _busy
              ? null
              : () async {
                  final r = await _ask(buyer ? 'Order cancel karna hai?' : 'Deal cancel karni hai?', 'Wajah');
                  if (r != null) _act('cancel', {'reason': r});
                },
          child: Text(buyer && st == 'quoted' ? 'Nahi chahiye' : 'Cancel', style: const TextStyle(color: C.muted))));
    }
    if (no.isNotEmpty) add(Wrap(alignment: WrapAlignment.end, children: no));
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final buyer = _s(v['role']) == 'buyer';
    final st = _s(v['state']);
    final q = _m(v['quote']);
    final draft = _m(v['draft']);
    final shown = (!buyer && draft['lines'] != null && (st == 'asked' || _s(v['waiting']) == 'quote')) ? draft : q;
    final ask = _m(v['ask']);
    final rdy = _m(v['ready']);
    final title = _s(v['title']).isEmpty ? 'Deal' : _s(v['title']);
    final buttons = _buttons();
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(buyer ? Icons.shopping_bag_rounded : Icons.storefront_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(buyer ? 'Khareed · ${_s(v['with'])}' : 'Bikri · ${_s(v['with'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800), maxLines: 1, overflow: TextOverflow.ellipsis),
              Text(_s(v['number']).isNotEmpty ? '${_s(v['number'])} · $title' : title,
                  style: const TextStyle(color: C.muted, fontSize: 12), maxLines: 1, overflow: TextOverflow.ellipsis),
            ]),
          ),
          Pill(_s(v['state_say']).isEmpty ? st : _s(v['state_say']), fg: _stateColor[st] ?? C.chip),
        ]),
        if (_s(v['say']).isNotEmpty && !widget.full) ...[
          const SizedBox(height: 8),
          Text(_s(v['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
        ],
        if (buyer && st == 'ready' && _s(rdy['code']).isNotEmpty) ...[
          const SizedBox(height: 10),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(16)),
            child: Column(children: [
              const Text('Counter par yeh code dikhaiye', style: TextStyle(color: C.muted, fontSize: 12)),
              Text(_s(rdy['code']),
                  style: const TextStyle(fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: 8, color: C.ok)),
              Text('${_s(rdy['place'])}${_when(rdy['until']).isEmpty ? '' : ' · ${_when(rdy['until'])} tak'}',
                  textAlign: TextAlign.center, style: const TextStyle(fontSize: 12.5)),
            ]),
          ),
        ],
        if (shown['lines'] != null) ...[
          const SizedBox(height: 10),
          _lines(shown),
          _totals(shown),
          if (q['valid_until'] != null && st == 'quoted')
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Quote ${_when(q['valid_until'])} tak', style: const TextStyle(color: C.faint, fontSize: 11.5)),
            ),
        ] else if (ask['items'] != null) ...[
          const SizedBox(height: 8),
          Text(_l(ask['items']).map((i) => '${_s(i['item'])} × ${_qty(i['qty'])} ${_s(i['unit'])}'.trim()).join('\n'),
              style: const TextStyle(fontSize: 13, height: 1.4)),
        ],
        if (_s(v['reason']).isNotEmpty && (st == 'rejected' || st == 'cancelled')) ...[
          const SizedBox(height: 6),
          Text(_s(v['reason']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ],
        if (buyer && st == 'quoted')
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text('Aapke Haan dabaane par hi order jaayega. Paisa yahan se nahi kat-ta.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
        if (buttons.isNotEmpty) ...[const SizedBox(height: 12), ...buttons],
        if (!widget.full)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => DealPage(app: widget.app, dealId: _s(v['id'])))),
              child: const Text('Poori deal dekho'),
            ),
          ),
        if (widget.full && (v['history'] as List?) != null) ...[
          const SizedBox(height: 12),
          const Text('Kya kya hua', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          for (final h in _l(v['history']))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 26, child: Text('${h['step']}.', style: const TextStyle(color: C.faint, fontSize: 12))),
                Expanded(child: Text(_s(h['say']), style: const TextStyle(fontSize: 12.5))),
                Text(_when(h['at']), style: const TextStyle(color: C.faint, fontSize: 11)),
              ]),
            ),
        ],
      ]),
    );
  }
}

/// One deal, full page: what was asked, the quote, the history, every action this side can take now.
class DealPage extends StatefulWidget {
  const DealPage({super.key, required this.app, required this.dealId});
  final Santosh app;
  final String dealId;
  @override
  State<DealPage> createState() => _DealPageState();
}

class _DealPageState extends State<DealPage> {
  Map<String, dynamic>? _d;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.netDeal(widget.dealId);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Deal'), backgroundColor: Colors.transparent),
        body: Aurora(
          child: _d == null
              ? Center(child: _err == null ? const CircularProgressIndicator() : Text(_err!, style: const TextStyle(color: C.bad)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.all(16), children: [
                    DealCard(key: ValueKey('dp${_d!['state']}${_d!['updated']}'), v: _d!, app: widget.app, full: true, onChanged: _load),
                  ]),
                ),
        ),
      );
}

/// Profile / Hoola Network > Deals: what she buys, what she sells, her stock list and her selling rules.
class DealsScreen extends StatefulWidget {
  const DealsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DealsScreen> createState() => _DealsScreenState();
}

class _DealsScreenState extends State<DealsScreen> {
  List<Map<String, dynamic>> _buy = [];
  List<Map<String, dynamic>> _sell = [];
  List<Map<String, dynamic>> _stock = [];
  Map<String, dynamic> _rules = {};
  bool _loading = true;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = await app.api!.netDeals(role: 'buyer');
      final s = await app.api!.netDeals(role: 'seller');
      final st = await app.api!.netStock();
      if (!mounted) return;
      setState(() {
        _buy = b;
        _sell = s;
        _stock = _l(st['stock']);
        _rules = _m(st['rules']);
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        _snack(context, '$e');
      }
    }
  }

  /// "Parle-G 10 carton" per line -> {item, qty, unit}.
  List<Map<String, dynamic>> _parse(String text) {
    final out = <Map<String, dynamic>>[];
    final re = RegExp(r'^(.*?)[\s,:x×-]+(\d+(?:\.\d+)?)\s*([A-Za-zऀ-ॿ]+)?\s*$');
    for (final raw in text.split('\n')) {
      final line = raw.trim();
      if (line.isEmpty) continue;
      final m = re.firstMatch(line);
      if (m != null && (m.group(1) ?? '').trim().isNotEmpty) {
        out.add({'item': m.group(1)!.trim(), 'qty': double.parse(m.group(2)!), 'unit': (m.group(3) ?? '').trim()});
      } else {
        out.add({'item': line, 'qty': 1});
      }
    }
    return out;
  }

  Future<void> _newList() async {
    final to = TextEditingController();
    final items = TextEditingController();
    final note = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nayi list bhejo'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: to, decoration: const InputDecoration(labelText: 'Kise (naam / @Hoola ID / business)')),
            TextField(
                controller: items,
                minLines: 4,
                maxLines: 10,
                decoration: const InputDecoration(labelText: 'Har line: cheez aur maatra', hintText: 'Parle-G 10 carton\nTata Salt 1kg 20')),
            TextField(controller: note, decoration: const InputDecoration(labelText: 'Note (kab tak chahiye...)')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
        ],
      ),
    );
    final t = to.text.trim();
    final list = _parse(items.text);
    final n = note.text.trim();
    to.dispose();
    items.dispose();
    note.dispose();
    if (ok != true || t.isEmpty || list.isEmpty) return;
    try {
      final r = await app.api!.netDealAsk(t, list, note: n);
      if (mounted) _snack(context, _s(r['say']));
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _editItem([Map<String, dynamic>? it]) async {
    final name = TextEditingController(text: _s(it?['name']));
    final price = TextEditingController(text: it == null ? '' : _qty(it['price']));
    final qty = TextEditingController(text: it == null || it['qty'] == null ? '' : _qty(it['qty']));
    final unit = TextEditingController(text: _s(it?['unit']));
    final aliases = TextEditingController(text: ((it?['aliases'] as List?) ?? const []).join(', '));
    var gst = it == null ? 0.0 : _d(it['gst_pct']);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: Text(it == null ? 'Naya item' : 'Item badlo'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam')),
              TextField(controller: price, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Daam (GST ke bina, ek unit)')),
              TextField(controller: qty, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Stock mein kitna (khaali = gina nahi)')),
              TextField(controller: unit, decoration: const InputDecoration(labelText: 'Unit (carton, packet, kg...)')),
              TextField(controller: aliases, decoration: const InputDecoration(labelText: 'Doosre naam (comma se)')),
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                for (final g in const [0.0, 5.0, 12.0, 18.0, 28.0, 40.0])
                  ChoiceChip(label: Text('GST ${g.toInt()}%'), selected: gst == g, onSelected: (_) => set(() => gst = g)),
              ]),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
          ],
        ),
      ),
    );
    final body = <String, dynamic>{
      'name': name.text.trim(),
      'price': double.tryParse(price.text.trim()) ?? 0,
      'qty': qty.text.trim().isEmpty ? null : double.tryParse(qty.text.trim()),
      'unit': unit.text.trim(),
      'gst_pct': gst,
      'aliases': aliases.text.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
    };
    for (final c in [name, price, qty, unit, aliases]) {
      c.dispose();
    }
    if (ok != true || _s(body['name']).isEmpty) return;
    try {
      await app.api!.netStockPut([body]);
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _setRule(Map<String, dynamic> body) async {
    try {
      final r = await app.api!.netDealRulesPut(body);
      if (mounted) setState(() => _rules = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _dealList(List<Map<String, dynamic>> xs, String empty) => ListView(padding: const EdgeInsets.all(16), children: [
        if (xs.isEmpty) Padding(padding: const EdgeInsets.all(20), child: Text(empty, style: const TextStyle(color: C.muted))),
        for (final d in xs)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: DealCard(key: ValueKey('dl${d['id']}${d['state']}${d['updated']}'), v: d, app: app, onChanged: _load),
          ),
      ]);

  Widget _stockTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GlassButton(label: 'Item jodo', icon: Icons.add_rounded, onTap: () => _editItem()),
        const SizedBox(height: 12),
        if (_stock.isEmpty)
          const Padding(
            padding: EdgeInsets.all(12),
            child: Text('Jo aap bechte hain uska daam, GST aur stock yahan likhiye. Graahak ki list aane par Hoola isi se quote '
                'banata hai (khud se daam kabhi nahi banata).', style: TextStyle(color: C.muted)),
          ),
        for (final it in _stock)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _editItem(it),
              child: Glass(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(it['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                      Text('${_inr(it['price'])} / ${_s(it['unit']).isEmpty ? 'unit' : _s(it['unit'])} · GST ${_qty(it['gst_pct'])}%',
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                    ]),
                  ),
                  Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text(it['qty'] == null ? 'gina nahi' : '${_qty(it['free'])} khaali',
                        style: TextStyle(fontWeight: FontWeight.w800, color: it['qty'] == null ? C.warn : C.ink)),
                    if (_d(it['reserved']) > 0)
                      Text('${_qty(it['reserved'])} order mein', style: const TextStyle(color: C.faint, fontSize: 11)),
                  ]),
                  IconButton(
                    tooltip: 'Hatao',
                    icon: const Icon(Icons.delete_outline_rounded, color: C.muted),
                    onPressed: () async {
                      try {
                        await app.api!.netStockDelete(_s(it['id']));
                        _load();
                      } catch (e) {
                        if (mounted) _snack(context, '$e');
                      }
                    },
                  ),
                ]),
              ),
            ),
          ),
      ]);

  Widget _rulesTab() {
    final aq = _s(_rules['auto_quote']).isEmpty ? 'off' : _s(_rules['auto_quote']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Quote khud bhejna', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text('Sirf tab jab list ki har cheez stock mein ho aur rakam seema ke andar ho.',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, children: [
            for (final e in const {'off': 'Har baar mujhse', 'trusted': 'Bharose walon ko', 'connected': 'Sab jude logon ko'}.entries)
              ChoiceChip(label: Text(e.value), selected: aq == e.key, onSelected: (_) => _setRule({'auto_quote': e.key})),
          ]),
          const SizedBox(height: 8),
          Text('Seema: ${_inr(_rules['auto_quote_max'])}', style: const TextStyle(fontSize: 12.5)),
          Wrap(spacing: 6, children: [
            for (final x in const [5000, 25000, 100000])
              ActionChip(label: Text(_inr(x)), onPressed: () => _setRule({'auto_quote_max': x})),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Order khud pakka karna', style: TextStyle(fontWeight: FontWeight.w800)),
            subtitle: Text('Graahak ke confirm ke baad, stock dobara dekh kar, ${_inr(_rules['auto_accept_max'])} tak',
                style: const TextStyle(fontSize: 12.5)),
            value: _rules['auto_accept'] == true,
            onChanged: (x) => _setRule({'auto_accept': x}),
          ),
          Wrap(spacing: 6, children: [
            for (final x in const [5000, 25000, 100000])
              ActionChip(label: Text(_inr(x)), onPressed: () => _setRule({'auto_accept_max': x})),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Pickup ki jagah', style: TextStyle(fontWeight: FontWeight.w800)),
          Text(_s(_rules['place']).isEmpty ? 'Abhi nahi likhi' : _s(_rules['place']), style: const TextStyle(color: C.muted)),
          const SizedBox(height: 6),
          GlassButton(
            label: 'Badlo',
            icon: Icons.edit_location_alt_rounded,
            onTap: () async {
              final c = TextEditingController(text: _s(_rules['place']));
              final ok = await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Pickup ki jagah'),
                  content: TextField(controller: c, decoration: const InputDecoration(hintText: 'Jaise: Counter 3, Gala no. 12')),
                  actions: [
                    TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
                    TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
                  ],
                ),
              );
              final t = c.text.trim();
              c.dispose();
              if (ok == true) _setRule({'place': t});
            },
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Text(_s(_rules['say']), style: const TextStyle(color: C.faint, fontSize: 12)),
    ]);
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Khareed aur bikri'),
            backgroundColor: Colors.transparent,
            bottom: TabBar(isScrollable: true, tabs: [
              Tab(text: 'Khareed${_buy.isEmpty ? '' : ' (${_buy.length})'}'),
              Tab(text: 'Bikri${_sell.isEmpty ? '' : ' (${_sell.length})'}'),
              const Tab(text: 'Stock'),
              const Tab(text: 'Niyam'),
            ]),
          ),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: _newList,
            backgroundColor: C.accent,
            foregroundColor: C.onAccent,
            icon: const Icon(Icons.playlist_add_rounded),
            label: const Text('Nayi list'),
          ),
          body: Aurora(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : RefreshIndicator(
                    onRefresh: _load,
                    child: TabBarView(children: [
                      _dealList(_buy, 'Kisi dukaan ya wholesaler ko list bhejiye: "Nayi list". Unka Hoola quote bhejega, aap haan karengi tabhi order jaayega.'),
                      _dealList(_sell, 'Jab koi aapke Hoola ko list bhejega, quote yahan taiyaar milega.'),
                      _stockTab(),
                      _rulesTab(),
                    ]),
                  ),
          ),
        ),
      );
}
