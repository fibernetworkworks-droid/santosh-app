/// Profile > Franchise sahayak (v0.115): Hoola as a franchise owner's coworker.
/// Aaj (yesterday's sales vs last week, licences, royalty due, agreement / lease dates) · Outlets (P&L side by side, sale /
/// kharcha entry) · Royalty (statement per brand -> her Haan -> message for the franchisor -> bhara) · Licence + audit.
/// Hoola never pays royalty and never files on licence portals.
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

Future<void> _send(String to, String text) async {
  if (to.contains('@')) {
    await Native.openExternal(url: 'mailto:$to?subject=${Uri.encodeComponent('Monthly sales & royalty statement')}&body=${Uri.encodeComponent(text)}');
  } else if (to.isNotEmpty) {
    final p = to.replaceAll(RegExp(r'\D'), '');
    await Native.openExternal(url: 'https://wa.me/${p.length == 10 ? '91$p' : p}?text=${Uri.encodeComponent(text)}');
  }
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields) TextField(controller: c[k], decoration: InputDecoration(labelText: label)),
        ]),
      ),
      actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage'))],
    ),
  );
  if (ok != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

class FranchiseScreen extends StatefulWidget {
  const FranchiseScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<FranchiseScreen> createState() => _FranchiseScreenState();
}

class _FranchiseScreenState extends State<FranchiseScreen> {
  Map<String, dynamic>? _day;
  Map<String, dynamic>? _cmp;
  Map<String, dynamic>? _lic;
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
      final d = await api.frDay();
      final c = await api.frRead('compare');
      final l = await api.frRead('licences');
      if (mounted) {
        setState(() {
          _day = d;
          _cmp = c;
          _lic = l;
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

  double? _n(String? v) => v == null ? null : double.tryParse(v.replaceAll(',', ''));

  Future<void> _brand() async {
    final f = await _form(context, 'Brand / agreement', const [
      ('brand', 'Brand'),
      ('franchisor', 'Franchisor company'),
      ('contact', 'Report kise (email)'),
      ('royalty_pct', 'Royalty %'),
      ('marketing_pct', 'Marketing %'),
      ('min_guarantee', 'Minimum royalty / outlet / mahina'),
      ('tech_fee', 'Tech fee / outlet / mahina'),
      ('start', 'Agreement shuru (dd-mm-yyyy)'),
      ('term_years', 'Kitne saal'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.frAgreement({
          ...f,
          for (final k in ['royalty_pct', 'marketing_pct', 'min_guarantee', 'tech_fee']) if (f[k] != null) k: _n(f[k]),
          if (f['term_years'] != null) 'term_years': int.tryParse(f['term_years']!) ?? 0,
        }));
  }

  Future<void> _outlet() async {
    final f = await _form(context, 'Outlet', const [('name', 'Outlet ka naam'), ('brand', 'Brand'), ('city', 'Shehar'), ('rent', 'Kiraya / mahina'), ('lease_end', 'Lease kab tak')]);
    if (f == null) return;
    await _run(() => widget.app.api!.frOutlet({...f, if (f['rent'] != null) 'rent': _n(f['rent'])}));
  }

  Future<void> _sale(String outlet) async {
    final f = await _form(context, '$outlet: sale', const [('net', 'Net sale (discount ke baad, GST ke bina)'), ('orders', 'Bill'), ('day', 'Tareekh (khaali = aaj)')]);
    if (f == null || f['net'] == null) return;
    await _run(() => widget.app.api!.frSale({'outlet': outlet, 'net': _n(f['net']), if (f['orders'] != null) 'orders': int.tryParse(f['orders']!), if (f['day'] != null) 'day': f['day']}));
  }

  Future<void> _cost(String outlet) async {
    final f = await _form(context, '$outlet: kharcha', const [('kind', 'Kis cheez ka (maal / staff / bijli / swiggy...)'), ('amount', 'Rakam'), ('month', 'Mahina (YYYY-MM)')]);
    if (f == null || f['amount'] == null) return;
    await _run(() => widget.app.api!.frCost({'outlet': outlet, ...f, 'amount': _n(f['amount'])}));
  }

  Widget _today() {
    final d = _day ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 8),
      for (final s in _list(d['sales']))
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Glass(
            padding: const EdgeInsets.all(10),
            child: Row(children: [
              Expanded(child: Text(_s(s['outlet']), style: const TextStyle(fontWeight: FontWeight.w700))),
              Text(s['net'] == null ? 'kal ki sale nahi' : rs(s['net']), style: TextStyle(color: s['net'] == null ? C.warn : C.ink)),
              if (s['vs_last_week'] != null)
                Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: Text('${(s['vs_last_week'] as num) >= 0 ? '+' : ''}${s['vs_last_week']}%',
                      style: TextStyle(color: (s['vs_last_week'] as num) >= 0 ? C.accent : C.bad, fontWeight: FontWeight.w700)),
                ),
              IconButton(icon: const Icon(Icons.add_rounded), tooltip: 'Sale likho', onPressed: _busy ? null : () => _sale(_s(s['outlet']))),
            ]),
          ),
        ),
      for (final w in _list(d['watch']))
        Text('• ${_s(w['what'])}: ${_s(w['on'])} (${w['days']} din)', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Brand / agreement', icon: Icons.handshake_rounded, onTap: _busy ? null : _brand),
        GlassButton(label: 'Naya outlet', icon: Icons.storefront_rounded, onTap: _busy ? null : _outlet),
      ]),
    ]);
  }

  Widget _outlets() {
    final rows = _list(_cmp?['outlets']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Pichhla mahina: ${_s(_cmp?['say'])}', style: const TextStyle(fontSize: 13)),
      const SizedBox(height: 8),
      for (final o in rows)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: (o['profit'] ?? 0) < 0 ? C.bad : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(o['outlet']), style: const TextStyle(fontWeight: FontWeight.w800))),
                Text(o['margin_pct'] == null ? '-' : '${o['margin_pct']}%', style: display(16, color: (o['profit'] ?? 0) < 0 ? C.bad : C.accent)),
              ]),
              Text('Sale ${rs(o['net'])} · ${o['orders']} bill${o['aov'] != null ? ' · ausat ${rs(o['aov'])}' : ''} · munafa ${rs(o['profit'])}',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              for (final f in (o['flags'] as List? ?? const [])) Text('• $f', style: const TextStyle(fontSize: 12, color: C.warn)),
              Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _cost(_s(o['outlet'])), child: const Text('Kharcha likho'))),
            ]),
          ),
        ),
      GlassButton(label: 'P&L Excel', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run(() => widget.app.api!.frPnlFile())),
    ]);
  }

  Widget _royalty() {
    final ags = _list(_day?['agreements']);
    final sts = _list(_day?['statements']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final a in ags)
          GlassButton(
              label: '${_s(a['brand'])}: pichhle mahine ka statement',
              icon: Icons.receipt_long_rounded,
              onTap: _busy ? null : () => _run(() => widget.app.api!.frStatement({'brand': a['brand']}))),
      ]),
      const SizedBox(height: 8),
      for (final s in sts)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: FrStatementCard(key: ValueKey('fs${s['id']}${s['status']}'), v: {'statement_id': s['id'], ...s}, app: widget.app, onDone: _load),
        ),
    ]);
  }

  Widget _licAudit() {
    final ls = _list(_lic?['licences']);
    final outs = _list(_day?['outlets']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(_s(_lic?['say']), style: const TextStyle(fontSize: 13)),
      const SizedBox(height: 8),
      for (final l in ls)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Glass(
            padding: const EdgeInsets.all(10),
            border: l['state'] == 'expired' || l['state'] == 'late_window' ? C.bad : (l['state'] == 'renew_now' ? C.warn : null),
            child: Text('${_s(l['outlet'])} · ${_s(l['name'])}: ${_s(l['text'])}', style: const TextStyle(fontSize: 12.5)),
          ),
        ),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(
            label: 'Licence jodo',
            icon: Icons.verified_rounded,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Licence', const [('outlet', 'Outlet'), ('kind', 'Kaun sa (fssai / fire noc / trade / shop act...)'), ('valid_to', 'Kab tak valid'), ('number', 'Number')]);
                    if (f != null) await _run(() => widget.app.api!.frLicence(f));
                  }),
        for (final o in outs)
          GlassButton(
              label: '${_s(o['name'])}: audit',
              icon: Icons.checklist_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      final f = await _form(context, '${_s(o['name'])} audit', const [('failed', 'Kya chooka? (comma se; sab theek ho to khaali)')]);
                      if (f == null) return;
                      final failed = (f['failed'] ?? '').split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList();
                      final r = await _run(() => widget.app.api!.frAudit({'outlet': o['name'], 'failed': failed}));
                      final dr = r?['draft'] as Map?;
                      if (dr != null) await _send(_s(dr['to']), _s(dr['text']));
                    }),
      ]),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Franchise sahayak')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Outlets'), (2, 'Royalty'), (3, 'Licence + audit')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_day == null) const Center(child: CircularProgressIndicator()) else [_today(), _outlets(), _royalty(), _licAudit()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Franchisor ko report aapki haan se. Royalty aap bank se bharti hain. Licence ka form aap / consultant bharte hain. '
                  'Agreement ki shart ka matlab vakil / CA se pakka kariye.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// Chat card (`fr_statement`) and row: approve (her Haan) -> message for the franchisor; Bhara gaya. `fr_day` shows text.
class FrStatementCard extends StatefulWidget {
  const FrStatementCard({super.key, required this.v, required this.app, this.onDone});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onDone;
  @override
  State<FrStatementCard> createState() => _FrStatementCardState();
}

class _FrStatementCardState extends State<FrStatementCard> {
  bool _busy = false;
  String _status = '';

  @override
  void initState() {
    super.initState();
    _status = _s(widget.v['status']).isEmpty ? 'draft' : _s(widget.v['status']);
  }

  Future<void> _act(String a) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.frStatementAct(_s(widget.v['statement_id']), a);
      if (a == 'approve') await _send(_s(r['to']), _s(r['text']));
      if (mounted) {
        setState(() => _status = a == 'approve' ? 'approved' : 'paid');
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
    if (v['statement_id'] == null) {
      return Glass(
        child: Row(children: [
          const Icon(Icons.storefront_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(v['text']), style: const TextStyle(fontWeight: FontWeight.w700))),
        ]),
      );
    }
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.receipt_long_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(v['brand'])} · ${_s(v['month'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status),
        ]),
        const SizedBox(height: 4),
        Text('Dena ${rs(v['payable'] ?? 0)}${_s(v['due']).isNotEmpty ? ' · ${_s(v['due'])} tak' : ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        if (_status == 'draft') GradientButton(label: 'Haan, franchisor ko bhejo', icon: Icons.send_rounded, onTap: _busy ? null : () => _act('approve')),
        if (_status == 'approved') GlassButton(label: 'Royalty bhar di', icon: Icons.check_rounded, onTap: _busy ? null : () => _act('paid')),
      ]),
    );
  }
}
