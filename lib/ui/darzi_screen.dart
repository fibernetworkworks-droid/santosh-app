/// Profile > Darzi (v0.82): Hoola as a tailor's / boutique's coworker.
/// Aaj (today's trials / deliveries / late, the week's load), Orders (status, money, ready message, slip),
/// Graahak (every customer's measurements, every version), Daam (her Haan on new prices + her price list),
/// Niyam (pieces a day, closed day, rush charge, her own rules). Chat cards: price card, 'taiyaar hai' draft, the morning list.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
double? _num(String t) => double.tryParse(t.trim().replaceAll(',', '').replaceAll('₹', '').replaceAll('Rs', '').trim());
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

const _flow = ['new', 'cutting', 'stitching', 'trial', 'ready'];
const _word = {
  'new': 'Naya',
  'cutting': 'Cutting',
  'stitching': 'Silai',
  'trial': 'Trial',
  'ready': 'Taiyaar',
  'delivered': 'De diya',
  'cancelled': 'Cancel',
};

Color _col(String s) => switch (s) {
      'ready' => C.ok,
      'delivered' => C.teal,
      'cancelled' => C.faint,
      'trial' => C.accent2,
      _ => C.accentSoft,
    };

void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

/// How full a day is (pieces due / pieces a day); without a limit a busy day shows a little bar.
double _load(Map<String, dynamic> w) {
  final cap = (w['cap'] as num?) ?? 0;
  final n = (w['pieces'] as num?) ?? 0;
  if (cap > 0) return (n / cap).clamp(0.0, 1.0).toDouble();
  return n > 0 ? 0.3 : 0.0;
}

String _iso(DateTime d) => '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

Future<String?> _pickDate(BuildContext context, String current) async {
  final now = DateTime.now();
  final init = DateTime.tryParse(current) ?? now.add(const Duration(days: 5));
  final d = await showDatePicker(
      context: context,
      initialDate: init.isBefore(now) ? now : init,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 365)));
  return d == null ? null : _iso(d);
}

/// Refreshes a tab whenever a darzi event arrives.
mixin _Live<T extends StatefulWidget> on State<T> {
  Santosh get app;
  int _tick = -1;
  Future<void> reload();
  void _onApp() {
    if (app.darziTick != _tick) {
      _tick = app.darziTick;
      reload();
    }
  }

  void startLive() {
    _tick = app.darziTick;
    app.addListener(_onApp);
    reload();
  }

  void stopLive() => app.removeListener(_onApp);
}

class DarziScreen extends StatelessWidget {
  const DarziScreen({super.key, required this.app});
  final Santosh app;

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 5,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: const Text('Darzi sahayak'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Aaj'),
              Tab(text: 'Orders'),
              Tab(text: 'Graahak'),
              Tab(text: 'Daam'),
              Tab(text: 'Niyam'),
            ]),
          ),
          floatingActionButton: FloatingActionButton.extended(
            backgroundColor: C.accent,
            foregroundColor: C.onAccent,
            icon: const Icon(Icons.add_rounded),
            label: const Text('Naya order', style: TextStyle(fontWeight: FontWeight.w800)),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DarziNewOrderPage(app: app))),
          ),
          body: Aurora(
            child: TabBarView(children: [
              _TodayTab(app: app),
              _OrdersTab(app: app),
              _CustomersTab(app: app),
              _PricesTab(app: app),
              _RulesTab(app: app),
            ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- one order in a list
class DarziOrderTile extends StatelessWidget {
  const DarziOrderTile({super.key, required this.o, required this.app});
  final Map<String, dynamic> o;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final st = _s(o['status']);
    final cust = Map<String, dynamic>.from((o['customer'] as Map?) ?? const {});
    final late = o['late'] == true;
    final left = o['days_left'];
    final when = st == 'delivered'
        ? 'Diya ${_s(o['delivered_on'])}'
        : 'Delivery ${_s(o['deliver_nice'])}${left is int && left >= 0 && st != 'ready' ? ' · $left din' : ''}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DarziOrderPage(app: app, id: _s(o['id'])))),
        child: Glass(
          border: late ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text(_s(o['number']), style: const TextStyle(color: C.faint, fontWeight: FontWeight.w800, fontSize: 12)),
              const SizedBox(width: 8),
              Expanded(child: Text(_s(cust['name']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
              Pill(_word[st] ?? st, fg: _col(st), bg: _col(st).withOpacity(.16)),
            ]),
            const SizedBox(height: 4),
            Text(_s(o['what']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.chip)),
            const SizedBox(height: 4),
            Row(children: [
              Icon(late ? Icons.warning_amber_rounded : Icons.event_rounded, size: 15, color: late ? C.bad : C.muted),
              const SizedBox(width: 4),
              Expanded(
                  child: Text(late ? 'Der ho gayi: ${_s(o['deliver_nice'])}' : when,
                      style: TextStyle(color: late ? C.bad : C.muted, fontSize: 12.5))),
              if (_s(o['trial_nice']).isNotEmpty && st != 'delivered')
                Text('Trial ${_s(o['trial_nice'])}  ', style: const TextStyle(color: C.accent2, fontSize: 12)),
              if ((o['balance_paise'] ?? 0) is num && (o['balance_paise'] as num) > 0)
                Text('Baaki ${_s(o['balance'])}', style: const TextStyle(color: C.warn, fontSize: 12, fontWeight: FontWeight.w700)),
            ]),
            if ((o['quote_pending'] as List?)?.isNotEmpty == true)
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text('Daam aapki haan ka intezaar kar raha hai', style: TextStyle(color: C.accent, fontSize: 12)),
              ),
          ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- Aaj
class _TodayTab extends StatefulWidget {
  const _TodayTab({required this.app});
  final Santosh app;
  @override
  State<_TodayTab> createState() => _TodayTabState();
}

class _TodayTabState extends State<_TodayTab> with _Live {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  String? _err;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final d = await app.api!.darziToday();
      if (mounted) setState(() {
        _d = d;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Widget _section(String title, List<Map<String, dynamic>> rows, Color c) => rows.isEmpty
      ? const SizedBox.shrink()
      : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 12, 4, 8),
            child: Text('$title (${rows.length})', style: TextStyle(color: c, fontWeight: FontWeight.w800)),
          ),
          for (final o in rows) DarziOrderTile(o: o, app: app),
        ]);

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        if (d == null && _err == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
        if (d != null) ...[
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(d['nice']), style: display(18)),
              const SizedBox(height: 6),
              Text(_s(d['text']), style: const TextStyle(color: C.chip, height: 1.4)),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 6, children: [
                Pill('${(d['trials'] as List).length} trial', fg: C.accent2),
                Pill('${(d['deliveries'] as List).length} delivery', fg: C.ok),
                if ((d['late'] as List).isNotEmpty) Pill('${(d['late'] as List).length} der', fg: C.bad),
                Pill('${d['open_orders']} chalu'),
                if ((d['quotes_pending'] ?? 0) > 0) Pill('${d['quotes_pending']} daam baaki', fg: C.accent),
              ]),
            ]),
          ),
          const SizedBox(height: 12),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Hafte ka kaam (delivery wale kapde)', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 10),
              for (final w in _list(d['week']))
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(children: [
                    SizedBox(width: 78, child: Text(_s(w['nice']), style: const TextStyle(color: C.muted, fontSize: 12.5))),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          minHeight: 9,
                          value: _load(w),
                          backgroundColor: C.panel,
                          color: w['full'] == true ? C.bad : C.accent,
                        ),
                      ),
                    ),
                    SizedBox(
                        width: 54,
                        child: Text((w['cap'] ?? 0) > 0 ? ' ${w['pieces']}/${w['cap']}' : ' ${w['pieces']}',
                            textAlign: TextAlign.right, style: const TextStyle(fontSize: 12.5))),
                  ]),
                ),
            ]),
          ),
          _section('Der ho gayi', _list(d['late']), C.bad),
          _section('Aaj trial', _list(d['trials']), C.accent2),
          _section('Aaj dena hai', _list(d['deliveries']), C.ok),
          _section('Taiyaar, 3+ din se nahi le gaye', _list(d['waiting_pickup']), C.warn),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- Orders
class _OrdersTab extends StatefulWidget {
  const _OrdersTab({required this.app});
  final Santosh app;
  @override
  State<_OrdersTab> createState() => _OrdersTabState();
}

class _OrdersTabState extends State<_OrdersTab> with _Live {
  @override
  Santosh get app => widget.app;
  String _status = 'open';
  List<Map<String, dynamic>>? _rows;
  String? _err;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final r = await app.api!.darziOrders(status: _status);
      if (mounted) setState(() {
        _rows = r;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    const filters = {'open': 'Chalu', 'ready': 'Taiyaar', 'delivered': 'Diye gaye', 'all': 'Sab'};
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Wrap(spacing: 8, children: [
          for (final f in filters.entries)
            ChoiceChip(
              label: Text(f.value),
              selected: _status == f.key,
              onSelected: (_) {
                setState(() {
                  _status = f.key;
                  _rows = null;
                });
                reload();
              },
            ),
        ]),
        const SizedBox(height: 12),
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        if (_rows == null && _err == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
        if (_rows != null && _rows!.isEmpty)
          const Padding(padding: EdgeInsets.all(30), child: Center(child: Text('Koi order nahi.', style: TextStyle(color: C.muted)))),
        for (final o in _rows ?? const <Map<String, dynamic>>[]) DarziOrderTile(o: o, app: app),
      ]),
    );
  }
}

// ---------------------------------------------------------------- one order
class DarziOrderPage extends StatefulWidget {
  const DarziOrderPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<DarziOrderPage> createState() => _DarziOrderPageState();
}

class _DarziOrderPageState extends State<DarziOrderPage> with _Live {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _o;
  String? _err;
  bool _busy = false;
  Api get _api => app.api!;
  String get _conv => app.conversationId ?? '';

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final o = await _api.darziOrder(widget.id);
      if (mounted) setState(() {
        _o = o;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<double?> _askMoney(String title, {String initial = '', String hint = ''}) async {
    final c = TextEditingController(text: initial);
    final r = await showDialog<double>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, keyboardType: const TextInputType.numberWithOptions(decimal: true), autofocus: true,
            decoration: InputDecoration(prefixText: '₹ ', hintText: hint)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(context, _num(c.text) ?? 0), child: const Text('Theek')),
        ],
      ),
    );
    return r;
  }

  Future<void> _dates() async {
    final o = _o!;
    final dl = await _pickDate(context, _s(o['deliver_on']));
    if (dl == null || !mounted) return;
    setState(() => _busy = true);
    try {
      var r = await _api.darziUpdateOrder(widget.id, {'deliver_on': dl});
      if (r['saved'] != true && mounted) {
        final probs = List<String>.from(((r['check'] as Map?)?['problems'] as List?) ?? const []);
        final yes = await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Niyam se mel nahi khata'),
            content: Text(probs.join('\n\n')),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Nahi')),
              TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Phir bhi rakho')),
            ],
          ),
        );
        if (yes == true) r = await _api.darziUpdateOrder(widget.id, {'deliver_on': dl, 'force': true});
      }
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _slip() async {
    setState(() => _busy = true);
    try {
      final r = await _api.darziSlip(widget.id, conversationId: _conv);
      final f = Map<String, dynamic>.from((r['file'] as Map?) ?? const {});
      final url = _api.absolute(_s(f['url']));
      if (url.isNotEmpty) await Native.openExternal(url: url);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _readySheet() async {
    try {
      final card = await _api.darziReady(widget.id, conversationId: _conv);
      if (!mounted) return;
      await showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => Padding(
          padding: EdgeInsets.fromLTRB(12, 12, 12, 12 + MediaQuery.of(context).viewInsets.bottom),
          child: DarziReadyCard(v: card, app: app),
        ),
      );
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final o = _o;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(o == null ? 'Order' : 'Order ${_s(o['number'])}')),
      body: Aurora(
        child: o == null
            ? Center(child: _err != null ? Text(_err!, style: const TextStyle(color: C.bad)) : const CircularProgressIndicator())
            : RefreshIndicator(onRefresh: reload, child: _body(o)),
      ),
    );
  }

  Widget _body(Map<String, dynamic> o) {
    final st = _s(o['status']);
    final cust = Map<String, dynamic>.from((o['customer'] as Map?) ?? const {});
    final closed = st == 'delivered' || st == 'cancelled';
    final bal = (o['balance_paise'] as num?) ?? 0;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(cust['name']), style: display(19))),
            Pill(_word[st] ?? st, fg: _col(st), bg: _col(st).withOpacity(.16)),
          ]),
          if (_s(cust['phone']).isNotEmpty) Text(_s(cust['phone']), style: const TextStyle(color: C.muted)),
          const SizedBox(height: 8),
          Text('Liya ${_s(o['received_on'])}  ·  Trial ${_s(o['trial_nice']).isEmpty ? '-' : _s(o['trial_nice'])}  ·  '
              'Delivery ${_s(o['deliver_nice'])}${o['rush'] == true ? ' (jaldi)' : ''}',
              style: TextStyle(color: o['late'] == true ? C.bad : C.chip, fontSize: 13)),
          const SizedBox(height: 8),
          Text('Kul ${_s(o['total'])}  ·  Mila ${_s(o['paid'])}  ·  Baaki ${_s(o['balance'])}',
              style: TextStyle(fontWeight: FontWeight.w800, color: bal > 0 ? C.warn : C.ok)),
          if (_s(o['rush_charge']).isNotEmpty) Text('Jaldi ka charge ${_s(o['rush_charge'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
          if (_s(o['notes']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(o['notes']), style: const TextStyle(color: C.muted))),
        ]),
      ),
      const SizedBox(height: 12),
      for (final it in _list(o['items']))
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(
                    child: Text('${it['qty']} x ${_s(it['label'])}${_s(it['person']).isNotEmpty ? ' (${it['person']})' : ''}',
                        style: const TextStyle(fontWeight: FontWeight.w800))),
                Text(_s(it['price']).isEmpty ? 'daam baaki' : _s(it['price']),
                    style: TextStyle(color: _s(it['price']).isEmpty ? C.accent : C.ink, fontWeight: FontWeight.w700)),
              ]),
              if (_s(it['fabric']).isNotEmpty) Text('Kapda: ${it['fabric']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (_s(it['style']).isNotEmpty) Text('Style: ${it['style']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (it['measure'] is Map) ...[
                const SizedBox(height: 6),
                Text(_s((it['measure'] as Map)['shown']), style: const TextStyle(color: C.chip, fontSize: 13, height: 1.35)),
                if (_s((it['measure'] as Map)['note']).isNotEmpty)
                  Text('Note: ${(it['measure'] as Map)['note']}', style: const TextStyle(color: C.accent2, fontSize: 12.5)),
              ],
            ]),
          ),
        ),
      if (!closed) ...[
        const Padding(padding: EdgeInsets.fromLTRB(4, 6, 4, 8), child: Text('Kaam kahan tak?', style: TextStyle(fontWeight: FontWeight.w800))),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final s in _flow.skip(1))
            ChoiceChip(
              label: Text(_word[s]!),
              selected: st == s,
              onSelected: _busy || st == s ? null : (_) => _run(() => _api.darziStatus(widget.id, s, conversationId: _conv)),
            ),
        ]),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(
              child: GlassButton(
                  label: 'Paise mile',
                  icon: Icons.currency_rupee_rounded,
                  onTap: _busy
                      ? null
                      : () async {
                          final a = await _askMoney('Kitne paise mile?');
                          if (a != null && a > 0) _run(() => _api.darziPay(widget.id, a, how: 'app'));
                        })),
          const SizedBox(width: 10),
          Expanded(
              child: GradientButton(
                  label: 'De diya',
                  icon: Icons.check_circle_rounded,
                  height: 48,
                  onTap: _busy
                      ? null
                      : () async {
                          final a = await _askMoney('Dete waqt kitne mile?', initial: bal > 0 ? (bal / 100).toStringAsFixed(0) : '0');
                          if (a != null) _run(() => _api.darziDeliver(widget.id, paidNow: a > 0 ? a : null, conversationId: _conv));
                        })),
        ]),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: '"Taiyaar hai" message', icon: Icons.chat_rounded, onTap: _busy ? null : _readySheet),
          GlassButton(label: 'Slip (PDF)', icon: Icons.picture_as_pdf_rounded, onTap: _busy ? null : _slip),
          GlassButton(label: 'Tareekh badlo', icon: Icons.event_repeat_rounded, onTap: _busy ? null : _dates),
          GlassButton(
              label: 'Cancel',
              icon: Icons.close_rounded,
              color: C.bad,
              onTap: _busy
                  ? null
                  : () async {
                      final yes = await showDialog<bool>(
                        context: context,
                        builder: (_) => AlertDialog(
                          title: const Text('Order cancel karein?'),
                          actions: [
                            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Nahi')),
                            TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Haan, cancel')),
                          ],
                        ),
                      );
                      if (yes == true) _run(() => _api.darziCancel(widget.id));
                    }),
        ]),
      ] else
        Wrap(spacing: 8, children: [
          GlassButton(label: 'Slip (PDF)', icon: Icons.picture_as_pdf_rounded, onTap: _busy ? null : _slip),
          if (bal > 0)
            GlassButton(
                label: 'Baaki paise mile',
                icon: Icons.currency_rupee_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final a = await _askMoney('Kitne paise mile?', initial: (bal / 100).toStringAsFixed(0));
                        if (a != null && a > 0) _run(() => _api.darziPay(widget.id, a, how: 'app'));
                      }),
        ]),
      const SizedBox(height: 18),
      const Text('Hisaab (log)', style: TextStyle(fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      for (final l in _list(o['log']).reversed)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text('${_s(l['at']).replaceFirst('T', ' ').split('+').first}  ${_s(l['what'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ),
    ]);
  }
}

// ---------------------------------------------------------------- new order
class DarziNewOrderPage extends StatefulWidget {
  const DarziNewOrderPage({super.key, required this.app, this.customer});
  final Santosh app;
  final Map<String, dynamic>? customer;
  @override
  State<DarziNewOrderPage> createState() => _DarziNewOrderPageState();
}

class _Line {
  String garment = 'blouse';
  final qty = TextEditingController(text: '1');
  final price = TextEditingController();
  final person = TextEditingController();
  final style = TextEditingController();
  Map<String, dynamic> body() => {
        'garment': garment,
        'qty': int.tryParse(qty.text.trim()) ?? 1,
        if (person.text.trim().isNotEmpty) 'person': person.text.trim(),
        if (style.text.trim().isNotEmpty) 'style': style.text.trim(),
        if (_num(price.text) != null) 'price': _num(price.text),
      };
}

class _DarziNewOrderPageState extends State<DarziNewOrderPage> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _advance = TextEditingController();
  final _notes = TextEditingController();
  final List<_Line> _lines = [_Line()];
  List<Map<String, dynamic>> _garments = const [];
  String _deliver = '';
  String _trial = '';
  Map<String, dynamic>? _check;
  bool _busy = false;
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    final c = widget.customer;
    if (c != null) {
      _name.text = _s(c['name']);
      _phone.text = _s(c['phone']);
    }
    _api.darziGarments().then((g) {
      if (mounted) setState(() => _garments = g);
    }).catchError((_) {});
  }

  Map<String, dynamic> _body({bool force = false}) => {
        if (widget.customer != null) 'customer': _s(widget.customer!['id']),
        'name': _name.text.trim(),
        'phone': _phone.text.trim(),
        'items': [for (final l in _lines) l.body()],
        'deliver_on': _deliver,
        'trial_on': _trial,
        if (_num(_advance.text) != null) 'advance': _num(_advance.text),
        'notes': _notes.text.trim(),
        'force': force,
        'conversation_id': widget.app.conversationId ?? '',
      };

  Future<void> _doCheck() async {
    setState(() => _busy = true);
    try {
      final r = await _api.darziCheck({
        'items': [for (final l in _lines) l.body()],
        'deliver_on': _deliver,
        'trial_on': _trial,
        'customer': widget.customer != null ? _s(widget.customer!['id']) : _phone.text.trim().isNotEmpty ? _phone.text.trim() : _name.text.trim(),
      });
      if (mounted) setState(() => _check = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _save({bool force = false}) async {
    if (_name.text.trim().isEmpty && _phone.text.trim().isEmpty && widget.customer == null) {
      _snack(context, 'Graahak ka naam ya phone likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await _api.darziNewOrder(_body(force: force));
      if (!mounted) return;
      if (r['saved'] == true) {
        _snack(context, _s(r['say']));
        Navigator.of(context).pop();
        return;
      }
      setState(() => _check = Map<String, dynamic>.from((r['check'] as Map?) ?? const {}));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _line(int i) {
    final l = _lines[i];
    final ids = _garments.map((g) => _s(g['id'])).toList();
    return Glass(
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(children: [
        Row(children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              value: ids.contains(l.garment) ? l.garment : (ids.isEmpty ? null : ids.first),
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Kapda'),
              items: [for (final g in _garments) DropdownMenuItem(value: _s(g['id']), child: Text(_s(g['label'])))],
              onChanged: (v) => setState(() => l.garment = v ?? 'other'),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(width: 52, child: TextField(controller: l.qty, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Kitne'))),
          const SizedBox(width: 8),
          SizedBox(width: 84, child: TextField(controller: l.price, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Daam ₹'))),
          if (_lines.length > 1)
            IconButton(onPressed: () => setState(() => _lines.removeAt(i)), icon: const Icon(Icons.close_rounded, color: C.faint)),
        ]),
        Row(children: [
          Expanded(child: TextField(controller: l.person, decoration: const InputDecoration(labelText: 'Kiske liye (agar koi aur)'))),
          const SizedBox(width: 8),
          Expanded(flex: 2, child: TextField(controller: l.style, decoration: const InputDecoration(labelText: 'Design / style'))),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ck = _check;
    final probs = List<String>.from((ck?['problems'] as List?) ?? const []);
    final notes = List<String>.from((ck?['notes'] as List?) ?? const []);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Naya order')),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Glass(
            child: Column(children: [
              TextField(controller: _name, enabled: widget.customer == null, decoration: const InputDecoration(labelText: 'Graahak ka naam')),
              TextField(controller: _phone, enabled: widget.customer == null, keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(labelText: 'Phone')),
            ]),
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < _lines.length; i++) _line(i),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(onPressed: () => setState(() => _lines.add(_Line())), icon: const Icon(Icons.add_rounded), label: const Text('Aur kapda')),
          ),
          Glass(
            child: Column(children: [
              Row(children: [
                Expanded(
                  child: GlassButton(
                    label: _deliver.isEmpty ? 'Delivery date' : 'Delivery $_deliver',
                    icon: Icons.event_rounded,
                    onTap: () async {
                      final d = await _pickDate(context, _deliver);
                      if (d != null) setState(() => _deliver = d);
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: GlassButton(
                    label: _trial.isEmpty ? 'Trial (optional)' : 'Trial $_trial',
                    icon: Icons.accessibility_new_rounded,
                    onTap: () async {
                      final d = await _pickDate(context, _trial);
                      if (d != null) setState(() => _trial = d);
                    },
                  ),
                ),
              ]),
              const SizedBox(height: 4),
              const Text('Delivery khaali chhodein to Hoola niyam se sabse jaldi ki tareekh rakhega.', style: TextStyle(color: C.faint, fontSize: 11.5)),
              TextField(controller: _advance, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Advance mila ₹')),
              TextField(controller: _notes, decoration: const InputDecoration(labelText: 'Note')),
            ]),
          ),
          if (ck != null) ...[
            const SizedBox(height: 12),
            Glass(
              border: probs.isEmpty ? C.ok : C.warn,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(probs.isEmpty ? 'Niyam ke hisaab se theek' : 'Niyam se mel nahi khata',
                    style: TextStyle(fontWeight: FontWeight.w800, color: probs.isEmpty ? C.ok : C.warn)),
                for (final p in probs) Padding(padding: const EdgeInsets.only(top: 6), child: Text('• $p', style: const TextStyle(color: C.chip))),
                for (final n in notes) Padding(padding: const EdgeInsets.only(top: 6), child: Text('· $n', style: const TextStyle(color: C.muted, fontSize: 12.5))),
                if (_s(ck['earliest_nice']).isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(children: [
                      Expanded(child: Text('Sabse jaldi: ${ck['earliest_nice']}', style: const TextStyle(color: C.accent))),
                      TextButton(onPressed: () => setState(() => _deliver = _s(ck['earliest'])), child: const Text('Yahi rakho')),
                    ]),
                  ),
              ]),
            ),
          ],
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: GlassButton(label: 'Niyam se check', icon: Icons.rule_rounded, onTap: _busy ? null : _doCheck)),
            const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Order save', height: 48, onTap: _busy ? null : () => _save())),
          ]),
          if (probs.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: GlassButton(label: 'Main maanti hoon, phir bhi save karo', color: C.warn, onTap: _busy ? null : () => _save(force: true)),
            ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- Graahak + naap
class _CustomersTab extends StatefulWidget {
  const _CustomersTab({required this.app});
  final Santosh app;
  @override
  State<_CustomersTab> createState() => _CustomersTabState();
}

class _CustomersTabState extends State<_CustomersTab> with _Live {
  @override
  Santosh get app => widget.app;
  final _q = TextEditingController();
  List<Map<String, dynamic>>? _rows;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final r = await app.api!.darziCustomers(q: _q.text.trim());
      if (mounted) setState(() => _rows = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _add() async {
    final n = TextEditingController();
    final p = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Naya graahak'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: n, autofocus: true, decoration: const InputDecoration(labelText: 'Naam')),
          TextField(controller: p, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || n.text.trim().isEmpty) return;
    try {
      final c = await app.api!.darziAddCustomer(n.text.trim(), p.text.trim());
      await reload();
      if (mounted) Navigator.of(context).push(MaterialPageRoute(builder: (_) => DarziCustomerPage(app: app, id: _s(c['id']))));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: reload,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
          Row(children: [
            Expanded(
              child: TextField(
                controller: _q,
                decoration: const InputDecoration(hintText: 'Naam ya phone se dhoondhiye', prefixIcon: Icon(Icons.search_rounded)),
                onSubmitted: (_) => reload(),
              ),
            ),
            IconButton(onPressed: _add, icon: const Icon(Icons.person_add_alt_1_rounded, color: C.accent)),
          ]),
          const SizedBox(height: 10),
          if (_rows == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
          if (_rows != null && _rows!.isEmpty)
            const Padding(padding: EdgeInsets.all(30), child: Center(child: Text('Koi graahak nahi.', style: TextStyle(color: C.muted)))),
          for (final c in _rows ?? const <Map<String, dynamic>>[])
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Press(
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DarziCustomerPage(app: app, id: _s(c['id'])))),
                child: Glass(
                  child: Row(children: [
                    const Icon(Icons.person_rounded, color: C.accentSoft),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(_s(c['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                        if (_s(c['phone']).isNotEmpty) Text(_s(c['phone']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                      ]),
                    ),
                    if ((c['open_orders'] ?? 0) > 0) Pill('${c['open_orders']} chalu', fg: C.accent),
                  ]),
                ),
              ),
            ),
        ]),
      );
}

class DarziCustomerPage extends StatefulWidget {
  const DarziCustomerPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<DarziCustomerPage> createState() => _DarziCustomerPageState();
}

class _DarziCustomerPageState extends State<DarziCustomerPage> with _Live {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _c;
  bool _history = false;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final c = await app.api!.darziCustomer(widget.id, history: _history);
      if (mounted) setState(() => _c = c);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final cust = Map<String, dynamic>.from((c?['customer'] as Map?) ?? const {});
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(cust['name']).isEmpty ? 'Graahak' : _s(cust['name']))),
      body: Aurora(
        child: c == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                if (_s(cust['phone']).isNotEmpty) Text(_s(cust['phone']), style: const TextStyle(color: C.muted)),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(
                      child: GradientButton(
                          label: 'Naya naap',
                          icon: Icons.straighten_rounded,
                          height: 46,
                          onTap: () => Navigator.of(context)
                              .push(MaterialPageRoute(builder: (_) => DarziMeasurePage(app: app, customer: cust)))
                              .then((_) => reload()))),
                  const SizedBox(width: 10),
                  Expanded(
                      child: GlassButton(
                          label: 'Naya order',
                          icon: Icons.add_rounded,
                          onTap: () => Navigator.of(context)
                              .push(MaterialPageRoute(builder: (_) => DarziNewOrderPage(app: app, customer: cust)))
                              .then((_) => reload()))),
                ]),
                const SizedBox(height: 14),
                Row(children: [
                  const Expanded(child: Text('Naap', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16))),
                  TextButton(
                      onPressed: () {
                        setState(() => _history = !_history);
                        reload();
                      },
                      child: Text(_history ? 'Sirf naye' : 'Purane bhi')),
                ]),
                if (_list(c['measures']).isEmpty) const Text('Abhi koi naap nahi.', style: TextStyle(color: C.muted)),
                for (final m in _list(c['measures']))
                  Glass(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(
                            child: Text('${_s(m['garment_label'])}${_s(m['person']).isNotEmpty ? ' · ${m['person']}' : ''}',
                                style: const TextStyle(fontWeight: FontWeight.w800))),
                        Text('${_s(m['created_at']).split('T').first} · ${_s(m['unit'])}', style: const TextStyle(color: C.faint, fontSize: 11.5)),
                      ]),
                      const SizedBox(height: 4),
                      Text(_s(m['shown']), style: const TextStyle(color: C.chip, height: 1.35)),
                      if (_s(m['note']).isNotEmpty) Text('Note: ${m['note']}', style: const TextStyle(color: C.accent2, fontSize: 12.5)),
                    ]),
                  ),
                const SizedBox(height: 14),
                const Text('Orders', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                const SizedBox(height: 8),
                for (final o in _list(c['orders'])) DarziOrderTile(o: o, app: app),
              ]),
      ),
    );
  }
}

class DarziMeasurePage extends StatefulWidget {
  const DarziMeasurePage({super.key, required this.app, required this.customer});
  final Santosh app;
  final Map<String, dynamic> customer;
  @override
  State<DarziMeasurePage> createState() => _DarziMeasurePageState();
}

class _DarziMeasurePageState extends State<DarziMeasurePage> {
  List<Map<String, dynamic>> _garments = const [];
  String _garment = 'blouse';
  final Map<String, TextEditingController> _f = {};
  final _person = TextEditingController();
  final _note = TextEditingController();
  final _free = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    widget.app.api!.darziGarments().then((g) {
      if (mounted) setState(() => _garments = g.where((x) => (x['fields'] as List).isNotEmpty).toList());
    }).catchError((_) {});
  }

  Map<String, dynamic> get _spec => _garments.firstWhere((g) => g['id'] == _garment, orElse: () => <String, dynamic>{'fields': []});

  TextEditingController _ctl(String id) => _f.putIfAbsent(id, () => TextEditingController());

  Future<void> _save() async {
    final vals = <String, dynamic>{};
    for (final e in _f.entries) {
      final n = _num(e.value.text);
      if (n != null) vals[e.key] = n;
    }
    final free = _free.text.trim();
    if (vals.isEmpty && free.isEmpty) {
      _snack(context, 'Koi naap likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.darziMeasure({
        'customer': _s(widget.customer['id']),
        'garment': _garment,
        'values': vals.isNotEmpty ? vals : free,
        'person': _person.text.trim(),
        'note': _note.text.trim(),
      });
      if (!mounted) return;
      final changed = List<String>.from((r['changed'] as List?) ?? const []);
      final missing = List<String>.from((r['missing'] as List?) ?? const []);
      if (changed.isNotEmpty || missing.isNotEmpty) {
        await showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Naap save hua'),
            content: Text([
              if (changed.isNotEmpty) 'Pichhli baar se fark:\n${changed.join('\n')}',
              if (missing.isNotEmpty) 'Abhi baaki: ${missing.join(', ')}',
            ].join('\n\n')),
            actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Theek'))],
          ),
        );
      } else {
        _snack(context, 'Naap save hua');
      }
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final fields = _list(_spec['fields']);
    final must = List<String>.from((_spec['must'] as List?) ?? const []);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('Naap: ${_s(widget.customer['name'])}')),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Glass(
            child: Column(children: [
              DropdownButtonFormField<String>(
                value: _garments.any((g) => g['id'] == _garment) ? _garment : null,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Kapda'),
                items: [for (final g in _garments) DropdownMenuItem(value: _s(g['id']), child: Text(_s(g['label'])))],
                onChanged: (v) => setState(() => _garment = v ?? 'blouse'),
              ),
              TextField(controller: _person, decoration: const InputDecoration(labelText: 'Kiske liye (graahak khud ho to khaali)')),
            ]),
          ),
          const SizedBox(height: 12),
          Glass(
            child: Wrap(spacing: 12, runSpacing: 4, children: [
              for (final f in fields)
                SizedBox(
                  width: 140,
                  child: TextField(
                    controller: _ctl(_s(f['id'])),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
                    decoration: InputDecoration(labelText: '${f['label']}${must.contains(f['id']) ? ' *' : ''}'),
                  ),
                ),
            ]),
          ),
          const SizedBox(height: 12),
          Glass(
            child: Column(children: [
              TextField(
                controller: _free,
                minLines: 1,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Ya seedha likh dijiye', hintText: 'L 15, chest 34, kamar 30, bahi 11 1/2'),
              ),
              TextField(controller: _note, decoration: const InputDecoration(labelText: 'Fitting / style note (loose, deep back...)')),
            ]),
          ),
          const SizedBox(height: 14),
          GradientButton(label: 'Naap save karo', icon: Icons.save_rounded, height: 50, onTap: _busy ? null : _save),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- Daam: her Haan + her price list
class _PricesTab extends StatefulWidget {
  const _PricesTab({required this.app});
  final Santosh app;
  @override
  State<_PricesTab> createState() => _PricesTabState();
}

class _PricesTabState extends State<_PricesTab> with _Live {
  @override
  Santosh get app => widget.app;
  List<Map<String, dynamic>>? _quotes;
  List<Map<String, dynamic>> _garments = const [];
  Map<String, dynamic>? _st;
  final Map<String, TextEditingController> _price = {};
  final Map<String, TextEditingController> _days = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final q = await app.api!.darziQuotes();
      final st = await app.api!.darziSettings();
      final g = _garments.isEmpty ? await app.api!.darziGarments() : _garments;
      if (!mounted) return;
      final prices = Map<String, dynamic>.from((st['prices'] as Map?) ?? const {});
      final days = Map<String, dynamic>.from((st['usual_days'] as Map?) ?? const {});
      for (final x in g) {
        final id = _s(x['id']);
        _price.putIfAbsent(id, () => TextEditingController()).text = prices[id] == null ? '' : '${(prices[id] as num).round()}';
        _days.putIfAbsent(id, () => TextEditingController()).text = _s(days[id]);
      }
      setState(() {
        _quotes = q;
        _st = st;
        _garments = g;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _saveList() async {
    setState(() => _busy = true);
    try {
      final prices = <String, dynamic>{};
      final days = <String, dynamic>{};
      for (final g in _garments) {
        final id = _s(g['id']);
        prices[id] = _num(_price[id]?.text ?? '');
        final d = int.tryParse(_days[id]?.text.trim() ?? '');
        if (d != null) days[id] = d;
      }
      await app.api!.darziSaveSettings({'prices': prices, 'min_days': days});
      if (mounted) _snack(context, 'Daam aur din save');
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: reload,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
          if ((_quotes ?? const []).isNotEmpty) ...[
            const Text('Aapki haan chahiye', style: TextStyle(fontWeight: FontWeight.w800, color: C.accent)),
            const SizedBox(height: 8),
            for (final q in _quotes!) Padding(padding: const EdgeInsets.only(bottom: 10), child: DarziQuoteCard(key: ValueKey('pq${q['id']}'), v: q, app: app)),
          ],
          if (_st == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
          if (_st != null)
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Daam ki list aur kitne din lagte hain', style: TextStyle(fontWeight: FontWeight.w800)),
                const Text('Jo daam yahan hai woh seedha order mein lagta hai; naya ya alag daam aapki haan se.',
                    style: TextStyle(color: C.faint, fontSize: 12)),
                const SizedBox(height: 8),
                for (final g in _garments)
                  Row(children: [
                    Expanded(child: Text(_s(g['label']), style: const TextStyle(fontSize: 13.5))),
                    SizedBox(
                        width: 90,
                        child: TextField(controller: _price[_s(g['id'])], keyboardType: TextInputType.number,
                            decoration: const InputDecoration(prefixText: '₹ ', isDense: true))),
                    const SizedBox(width: 10),
                    SizedBox(
                        width: 60,
                        child: TextField(controller: _days[_s(g['id'])], keyboardType: TextInputType.number,
                            decoration: const InputDecoration(suffixText: 'din', isDense: true))),
                  ]),
                const SizedBox(height: 12),
                GradientButton(label: 'Save', height: 46, onTap: _busy ? null : _saveList),
              ]),
            ),
        ]),
      );
}

// ---------------------------------------------------------------- Niyam
class _RulesTab extends StatefulWidget {
  const _RulesTab({required this.app});
  final Santosh app;
  @override
  State<_RulesTab> createState() => _RulesTabState();
}

class _RulesTabState extends State<_RulesTab> {
  final _shop = TextEditingController();
  final _pieces = TextEditingController();
  final _rush = TextEditingController();
  final _remeasure = TextEditingController();
  final _morning = TextEditingController();
  final _rules = TextEditingController();
  final _template = TextEditingController();
  String _unit = 'inch';
  Set<int> _closed = {};
  bool _enabled = true;
  bool _loaded = false;
  bool _busy = false;
  static const _days = ['Som', 'Mangal', 'Budh', 'Guru', 'Shukra', 'Shani', 'Ravi'];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await widget.app.api!.darziSettings();
      if (!mounted) return;
      setState(() {
        _shop.text = _s(s['shop_name']);
        _pieces.text = _s(s['pieces_per_day']);
        _rush.text = _s(s['rush_percent']);
        _remeasure.text = _s(s['remeasure_months']);
        _morning.text = _s(s['morning_time']);
        _rules.text = List<String>.from((s['rules'] as List?) ?? const []).join('\n');
        _template.text = _s(s['ready_template']);
        _unit = _s(s['unit']).isEmpty ? 'inch' : _s(s['unit']);
        _closed = Set<int>.from(((s['closed_days'] as List?) ?? const []).map((e) => (e as num).toInt()));
        _enabled = s['enabled'] != false;
        _loaded = true;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.darziSaveSettings({
        'enabled': _enabled,
        'shop_name': _shop.text.trim(),
        'unit': _unit,
        'pieces_per_day': int.tryParse(_pieces.text.trim()) ?? 0,
        'rush_percent': int.tryParse(_rush.text.trim()) ?? 0,
        'remeasure_months': int.tryParse(_remeasure.text.trim()) ?? 6,
        'morning_time': _morning.text.trim(),
        'closed_days': _closed.toList(),
        'rules': _rules.text.split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
        'ready_template': _template.text.trim(),
      });
      if (mounted) _snack(context, 'Niyam save');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => !_loaded
      ? const Center(child: CircularProgressIndicator())
      : ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: _enabled,
                onChanged: (v) => setState(() => _enabled = v),
                title: Text('${widget.app.aName} darzi ka kaam sambhale'),
                subtitle: const Text('Subah ki list, order ki jaanch, WhatsApp par graahak ko order ka haal'),
              ),
              TextField(controller: _shop, decoration: const InputDecoration(labelText: 'Dukaan ka naam')),
              const SizedBox(height: 8),
              Row(children: [
                const Text('Naap: '),
                ChoiceChip(label: const Text('inch'), selected: _unit == 'inch', onSelected: (_) => setState(() => _unit = 'inch')),
                const SizedBox(width: 6),
                ChoiceChip(label: const Text('cm'), selected: _unit == 'cm', onSelected: (_) => setState(() => _unit = 'cm')),
              ]),
              TextField(controller: _pieces, keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Roz kitne kapde de sakti hain (0 = koi seemaa nahi)')),
              TextField(controller: _rush, keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Jaldi (rush) ka extra charge %')),
              TextField(controller: _remeasure, keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Kitne mahine baad dobara naap lein')),
              TextField(controller: _morning, decoration: const InputDecoration(labelText: 'Subah ki list kab (HH:MM)')),
              const SizedBox(height: 10),
              const Text('Dukaan kis din band rehti hai', style: TextStyle(color: C.muted)),
              Wrap(spacing: 6, children: [
                for (var i = 0; i < 7; i++)
                  FilterChip(
                    label: Text(_days[i]),
                    selected: _closed.contains(i),
                    onSelected: (v) => setState(() => v ? _closed.add(i) : _closed.remove(i)),
                  ),
              ]),
            ]),
          ),
          const SizedBox(height: 12),
          Glass(
            child: Column(children: [
              TextField(
                controller: _rules,
                minLines: 3,
                maxLines: 8,
                decoration: const InputDecoration(
                    labelText: 'Apne niyam (ek line mein ek)', hintText: 'Bridal blouse 15 din se kam nahi\nShaadi season mein advance 50%'),
              ),
              TextField(
                controller: _template,
                minLines: 2,
                maxLines: 5,
                decoration: const InputDecoration(
                    labelText: '"Taiyaar hai" message', helperText: '{name} {items} {shop} {number} {balance} {balance_line} likh sakti hain'),
              ),
            ]),
          ),
          const SizedBox(height: 14),
          GradientButton(label: 'Niyam save karo', height: 50, onTap: _busy ? null : _save),
        ]);
}

// ---------------------------------------------------------------- chat cards
/// A price Hoola prepared; nothing is promised until she says Haan.
class DarziQuoteCard extends StatefulWidget {
  const DarziQuoteCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<DarziQuoteCard> createState() => _DarziQuoteCardState();
}

class _DarziQuoteCardState extends State<DarziQuoteCard> {
  late final TextEditingController _p = TextEditingController(
      text: widget.v['price_rupees'] == null ? '' : '${(widget.v['price_rupees'] as num).round()}');
  bool _busy = false;
  bool _toList = true;

  Future<void> _decide(bool yes) async {
    final price = _num(_p.text);
    if (yes && (price == null || price <= 0)) {
      _snack(context, 'Daam likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.darziDecideQuote(_s(widget.v['id']), yes, price: yes ? price : null, toList: yes ? _toList : null);
      widget.v.addAll(Map<String, dynamic>.from((r['quote'] as Map?) ?? const {}));
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final pending = _s(v['status']) == 'pending';
    return Glass(
      border: pending ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.sell_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Naya daam: ${_s(v['label'])}', style: display(15.5))),
          if (!pending) Pill(_s(v['status']) == 'approved' ? 'Pakka ${_s(v['price'])}' : 'Mana', fg: _s(v['status']) == 'approved' ? C.ok : C.faint),
        ]),
        const SizedBox(height: 4),
        Text([if (_s(v['customer']).isNotEmpty) _s(v['customer']), if (_s(v['order_number']).isNotEmpty) 'Order ${v['order_number']}'].join(' · '),
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
        if (_s(v['why']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(v['why']), style: const TextStyle(color: C.chip))),
        if (_s(v['list_price']).isNotEmpty) Text('List mein: ${v['list_price']}', style: const TextStyle(color: C.faint, fontSize: 12)),
        if (pending) ...[
          const SizedBox(height: 8),
          Row(children: [
            SizedBox(
              width: 130,
              child: TextField(controller: _p, keyboardType: TextInputType.number, decoration: const InputDecoration(prefixText: '₹ ', labelText: 'Daam')),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: CheckboxListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                value: _toList,
                onChanged: (x) => setState(() => _toList = x ?? true),
                title: const Text('List mein bhi', style: TextStyle(fontSize: 12.5)),
              ),
            ),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            Expanded(child: GlassButton(label: 'Mana', onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Haan, pakka', height: 48, onTap: _busy ? null : () => _decide(true))),
          ]),
        ],
      ]),
    );
  }
}

/// 'Taiyaar hai' message: Hoola drafts, she sends (her WhatsApp / SMS, or the business WhatsApp with her tap).
class DarziReadyCard extends StatefulWidget {
  const DarziReadyCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<DarziReadyCard> createState() => _DarziReadyCardState();
}

class _DarziReadyCardState extends State<DarziReadyCard> {
  late final TextEditingController _t = TextEditingController(text: _s(widget.v['text']));
  bool _busy = false;
  String get _phone => _s(widget.v['phone']);

  Future<void> _open(String how) async {
    final text = Uri.encodeComponent(_t.text.trim());
    final url = how == 'sms' ? 'sms:+91$_phone?body=$text' : 'https://wa.me/91$_phone?text=$text';
    await Native.openExternal(url: url);
    try {
      await widget.app.api!.darziTold(_s(widget.v['order_id']), how);
    } catch (_) {}
    if (mounted) setState(() => widget.v['status'] = 'opened');
  }

  Future<void> _business() async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.darziSendBusiness(_s(widget.v['order_id']), _t.text.trim());
      widget.v['status'] = 'sent';
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final st = _s(v['status']);
    return Glass(
      border: st == 'draft' ? C.ok : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.checkroom_rounded, color: C.ok, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Taiyaar: ${_s(v['customer'])} (${_s(v['number'])})', style: display(15.5))),
          if (st == 'sent') const Pill('Bheja', fg: C.ok),
          if (st == 'opened') const Pill('WhatsApp khola', fg: C.teal),
        ]),
        const SizedBox(height: 4),
        Text(_s(v['what']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        TextField(controller: _t, minLines: 2, maxLines: 6, decoration: const InputDecoration(labelText: 'Message (badal sakti hain)')),
        const SizedBox(height: 10),
        if (_phone.length == 10)
          Row(children: [
            Expanded(child: GradientButton(label: 'WhatsApp par bhejo', icon: Icons.send_rounded, height: 46, onTap: _busy ? null : () => _open('whatsapp'))),
            const SizedBox(width: 8),
            GlassButton(label: 'SMS', onTap: _busy ? null : () => _open('sms')),
          ])
        else
          GlassButton(
              label: 'Message copy karo',
              icon: Icons.copy_rounded,
              onTap: () {
                Clipboard.setData(ClipboardData(text: _t.text.trim()));
                _snack(context, 'Copy ho gaya (graahak ka phone save nahi hai)');
              }),
        if (v['can_business'] == true) ...[
          const SizedBox(height: 8),
          GlassButton(label: 'Business WhatsApp se bhejo', icon: Icons.verified_rounded, onTap: _busy || st == 'sent' ? null : _business),
        ],
        const SizedBox(height: 4),
        Text('${widget.app.aName} khud nahi bhejta: aap dabayengi tabhi jayega.', style: const TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

/// The morning list (trials, deliveries, late) in the chat.
class DarziDayCard extends StatelessWidget {
  const DarziDayCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.content_cut_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('Aaj ki silai', style: display(16))),
            if ((v['late'] ?? 0) > 0) Pill('${v['late']} der', fg: C.bad),
          ]),
          const SizedBox(height: 8),
          Text(_s(v['text']), style: const TextStyle(color: C.chip, height: 1.4)),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DarziScreen(app: app))),
              child: const Text('Darzi kholo'),
            ),
          ),
        ]),
      );
}
