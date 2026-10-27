/// Profile > Niryat sahayak (v0.110): Hoola as an exporter's coworker.
/// Aaj (LUT / RCMC / realisation dues) · Shipments (PI -> Bhejo / Pakka (her Haan) -> Shipped -> Paisa aaya) · Buyers.
/// Shipping bill, certificate of origin, e-BRC and forward contracts are hers / her CHA's / her bank's; Hoola never moves money.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Color _lvl(String l) => switch (l) { 'stop' => C.bad, 'warn' => C.warn, _ => C.accent };
String _fc(dynamic cur, dynamic v) => '${_s(cur)} ${((v as num?) ?? 0).toStringAsFixed(2)}';

Future<void> _send(String to, String text) async {
  if (to.contains('@')) {
    await Native.openExternal(url: 'mailto:$to?subject=${Uri.encodeComponent('Proforma / Invoice')}&body=${Uri.encodeComponent(text)}');
  } else {
    final p = to.replaceAll(RegExp(r'\D'), '');
    await Native.openExternal(url: 'https://wa.me/$p?text=${Uri.encodeComponent(text)}');
  }
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {Map<String, String> init = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: init[k] ?? '')};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields) TextField(controller: c[k], maxLines: k == 'text' ? 4 : 1, decoration: InputDecoration(labelText: label)),
        ]),
      ),
      actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage'))],
    ),
  );
  if (ok != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

class NiryatScreen extends StatefulWidget {
  const NiryatScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<NiryatScreen> createState() => _NiryatScreenState();
}

class _NiryatScreenState extends State<NiryatScreen> {
  Map<String, dynamic>? _day;
  List<Map<String, dynamic>> _ships = [];
  List<Map<String, dynamic>> _buyers = [];
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = widget.app.api!;
      final d = await api.niryatDay();
      final s = await api.niryatShipments();
      final b = await api.niryatBuyers();
      if (mounted) {
        setState(() {
          _day = d;
          _ships = s;
          _buyers = b;
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

  Future<void> _settings() async {
    final st = Map<String, dynamic>.from((_day?['settings'] as Map?) ?? const {});
    final f = await _form(context, 'Firm', const [
      ('firm', 'Firm ka naam'),
      ('address', 'Address'),
      ('iec', 'IEC'),
      ('gstin', 'GSTIN'),
      ('ad_bank', 'AD bank + AD code'),
      ('lut_no', 'Is saal ka LUT number'),
      ('rcmc', 'RCMC (council + number)'),
      ('rcmc_valid_to', 'RCMC kab tak'),
    ], init: {for (final k in ['firm', 'address', 'iec', 'gstin', 'ad_bank', 'lut_no', 'rcmc', 'rcmc_valid_to']) k: _s(st[k])});
    if (f == null) return;
    await _run(() => widget.app.api!.niryatSettings(f));
  }

  Future<void> _newBuyer() async {
    final f = await _form(context, 'Naya buyer', const [
      ('name', 'Naam'),
      ('country', 'Desh (jaise UAE, US, GB)'),
      ('currency', 'Currency (USD / EUR / AED...)'),
      ('pay_terms', 'Payment: advance / lc / dp / da / open'),
      ('email', 'Email'),
      ('phone', 'WhatsApp (country code ke saath)'),
      ('address', 'Address'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.niryatBuyer(f));
  }

  Future<void> _newPi() async {
    final f = await _form(context, 'Naya PI', const [
      ('buyer', 'Buyer'),
      ('text', 'Maal: naam maatra @ rate HS code (har line alag)'),
      ('incoterm', 'Incoterm (FOB / CIF / CFR / EXW / DAP)'),
      ('place', 'Port / jagah'),
      ('fx', 'Exchange rate (Rs per unit)'),
      ('freight', 'Freight (CIF / CFR ho to)'),
      ('port_loading', 'Port of loading'),
      ('port_discharge', 'Port of discharge'),
    ], init: const {'incoterm': 'FOB'});
    if (f == null) return;
    await _run(() => widget.app.api!.niryatPi({
          ...f,
          if (f['fx'] != null) 'fx': double.tryParse(f['fx']!) ?? 0,
          if (f['freight'] != null) 'freight': double.tryParse(f['freight']!) ?? 0,
        }));
  }

  @override
  Widget build(BuildContext context) {
    final d = _day ?? const {};
    final r = Map<String, dynamic>.from((d['realisation'] as Map?) ?? const {});
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Niryat sahayak'), actions: [
        IconButton(icon: const Icon(Icons.table_view_rounded), tooltip: 'Export register', onPressed: _busy ? null : () => _run(() => widget.app.api!.niryatRegister())),
      ]),
      floatingActionButton: FloatingActionButton.extended(onPressed: _busy ? null : _newPi, icon: const Icon(Icons.description_rounded), label: const Text('PI')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
            Wrap(spacing: 6, children: [
              for (final (i, t) in const [(0, 'Aaj'), (1, 'Shipments'), (2, 'Buyers')])
                ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
            ]),
            const SizedBox(height: 10),
            if (_busy) const LinearProgressIndicator(),
            if (_day == null) const Center(child: CircularProgressIndicator()),
            if (_day != null && _tab == 0) ...[
              Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
              const SizedBox(height: 8),
              for (final x in _list(r['shipments']))
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Glass(
                    padding: const EdgeInsets.all(10),
                    border: (x['days_left'] ?? 1) < 0 ? C.bad : ((x['days_left'] ?? 99) <= 30 ? C.warn : null),
                    child: Text('${_s(x['number'])} ${_s(x['buyer'])}: baaki ${_fc(x['currency'], x['outstanding'])} · RBI tareekh ${_s(x['realise_by'])} (${x['days_left']} din)'),
                  ),
                ),
              for (final dr in _list(r['drafts']))
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Glass(
                    padding: const EdgeInsets.all(10),
                    child: Row(children: [
                      Expanded(child: Text(_s(dr['text']), style: const TextStyle(fontSize: 12.5))),
                      IconButton(icon: const Icon(Icons.send_rounded), onPressed: _s(dr['to']).isEmpty ? null : () => _send(_s(dr['to']), _s(dr['text']))),
                    ]),
                  ),
                ),
              GlassButton(label: 'Firm / IEC / LUT', icon: Icons.business_rounded, onTap: _busy ? null : _settings),
            ],
            if (_day != null && _tab == 1)
              for (final x in _ships)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: NiryatCard(key: ValueKey('ns${x['id']}${x['status']}'), v: {'shipment_id': x['id']}, app: widget.app, shipment: x, onDone: _load),
                ),
            if (_day != null && _tab == 2) ...[
              GlassButton(label: 'Naya buyer', icon: Icons.person_add_alt_rounded, onTap: _busy ? null : _newBuyer),
              const SizedBox(height: 8),
              for (final b in _buyers)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Glass(
                    padding: const EdgeInsets.all(10),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${_s(b['name'])} · ${_s(b['country'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text('${_s(b['currency'])} · ${_s(b['pay_label'])}${_s(b['fta']).isNotEmpty ? ' · ${b['fta']}' : ''}',
                          style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                ),
            ],
            const SizedBox(height: 14),
            const Text(
                'PI aur invoice buyer ko aapki haan se. Shipping bill (CHA / ICEGATE), certificate of origin (DGFT), e-BRC aur forward contract aap / bank karte hain. '
                'Paisa shipment ke 9 mahine mein (rupee invoice: 12) aana zaroori.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      ),
    );
  }
}

/// A shipment card (chat `niryat_pi`, and each row in Shipments): checks, then her taps for each step.
class NiryatCard extends StatefulWidget {
  const NiryatCard({super.key, required this.v, required this.app, this.shipment, this.onDone});
  final Map<String, dynamic> v;
  final Santosh app;
  final Map<String, dynamic>? shipment;
  final VoidCallback? onDone;
  @override
  State<NiryatCard> createState() => _NiryatCardState();
}

class _NiryatCardState extends State<NiryatCard> {
  Map<String, dynamic>? _x;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _x = widget.shipment;
    if (_x == null && widget.v['shipment_id'] != null) _fetch();
  }

  Future<void> _fetch() async {
    try {
      final x = await widget.app.api!.niryatShipment(_s(widget.v['shipment_id']));
      if (mounted) setState(() => _x = x);
    } catch (_) {}
  }

  Future<void> _act(String a, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.niryatAct(_s(_x!['id']), a, body);
      if (a == 'send_pi') await _send(_s(r['to']), _s(r['text']));
      if (mounted) {
        setState(() => _x = Map<String, dynamic>.from((r['shipment'] as Map?) ?? _x!));
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
    final v = widget.v;
    if (v['shipment_id'] == null) {
      return Glass(
        child: Row(children: [
          const Icon(Icons.public_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(v['text']), style: const TextStyle(fontWeight: FontWeight.w700))),
        ]),
      );
    }
    final x = _x;
    if (x == null) return const Glass(child: LinearProgressIndicator());
    final st = _s(x['status']);
    return Glass(
      border: _list(x['checks']).any((c) => c['level'] == 'stop') ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.public_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['buyer'])} · ${_s(x['country'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill('${_s(x['number'])} · $st'),
        ]),
        const SizedBox(height: 4),
        for (final l in _list(x['lines']))
          Text('${_s(l['item'])} ${l['qty']} ${_s(l['unit'])} @ ${l['rate']} · HS ${_s(l['hs'])}', style: const TextStyle(fontSize: 12.5)),
        Text('${_s(x['incoterm'])} ${_s(x['place'])}: ${_fc(x['currency'], x['total'])} (FOB ${_fc(x['currency'], x['fob'])})',
            style: const TextStyle(fontWeight: FontWeight.w800)),
        Text(_s(x['incoterm_says']), style: const TextStyle(color: C.muted, fontSize: 12)),
        for (final c in _list(x['checks'])) Text('• ${_s(c['text'])}', style: TextStyle(fontSize: 12, color: _lvl(_s(c['level'])))),
        if (_s(x['realise_by']).isNotEmpty)
          Text('Paisa ${_s(x['realise_by'])} tak · mila ${_fc(x['currency'], x['received'])} · baaki ${_fc(x['currency'], x['outstanding'])}',
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (st == 'pi') GlassButton(label: 'Haan, buyer ko bhejo', icon: Icons.send_rounded, onTap: _busy ? null : () => _act('send_pi')),
          if (st == 'pi') GlassButton(label: 'Order pakka: invoice banao', icon: Icons.check_rounded, onTap: _busy ? null : () => _act('confirm')),
          if (st == 'confirmed')
            GlassButton(
                label: 'Maal nikal gaya',
                icon: Icons.directions_boat_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Shipping bill', const [('sb_no', 'Shipping bill no'), ('sb_date', 'SB date'), ('bl_no', 'B/L / AWB no'), ('fx', 'Customs exchange rate')]);
                        if (f != null) await _act('shipped', {...f, if (f['fx'] != null) 'fx': double.tryParse(f['fx']!) ?? 0});
                      }),
          if (st != 'realised' && st != 'cancelled')
            GlassButton(
                label: 'Paisa aaya',
                icon: Icons.currency_exchange_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Bank mein aaya', [('amount', 'Rakam (${_s(x['currency'])})'), ('inr', 'Rupaye mile'), ('ref', 'IRM / e-BRC no')]);
                        if (f != null) {
                          await _act('receive', {...f, 'amount': double.tryParse(f['amount'] ?? '') ?? 0, if (f['inr'] != null) 'inr': double.tryParse(f['inr']!) ?? 0});
                        }
                      }),
        ]),
      ]),
    );
  }
}
