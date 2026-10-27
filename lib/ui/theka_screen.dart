/// Profile > Theka sahayak (v0.117): Hoola as a contractor's coworker.
/// Aaj (deadlines, BG / insurance, delays, money due) · Tender (dates, EMD, papers) · Kaam (project -> BOQ progress, naap,
/// RA bill -> her Haan to submit -> pass / paid, site diary, EOT letter). Bids go in with her DSC; Hoola never pays.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';
import 'gst_screen.dart' show rs;

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
double? _n(String? v) => v == null ? null : double.tryParse(v.replaceAll(',', ''));

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

class ThekaScreen extends StatefulWidget {
  const ThekaScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ThekaScreen> createState() => _ThekaScreenState();
}

class _ThekaScreenState extends State<ThekaScreen> {
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
      final d = await widget.app.api!.thekaDay();
      if (mounted) setState(() => _d = d);
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

  Future<void> _tender([Map<String, dynamic>? t]) async {
    final f = await _form(context, t == null ? 'Naya tender' : _s(t['name']), [
      if (t == null) ('name', 'Kaam ka naam'),
      if (t == null) ('dept', 'Department'),
      if (t == null) ('portal', 'Portal (mahatenders / CPPP / GeM)'),
      if (t == null) ('ref', 'Tender ID'),
      ('last_date', 'Aakhri tareekh (dd-mm-yyyy hh:mm)'),
      ('emd', 'EMD'),
      ('status', 'Status: watching / preparing / submitted / won / lost'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.thekaTender({if (t != null) 'tender': t['id'], ...f, if (f['emd'] != null) 'emd': _n(f['emd'])}));
  }

  Future<void> _project() async {
    final f = await _form(context, 'Naya kaam', const [
      ('name', 'Kaam ka naam'),
      ('client', 'Department / client'),
      ('value', 'Agreement value'),
      ('start', 'Shuru'),
      ('end', 'Poora karne ki tareekh'),
      ('retention_pct', 'Retention % (agreement se)'),
      ('mob_advance', 'Mobilisation advance (ho to)'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.thekaProject({
          ...f,
          for (final k in ['value', 'retention_pct', 'mob_advance']) if (f[k] != null) k: _n(f[k]),
        }));
  }

  Widget _today() {
    final d = _d ?? const {};
    final rc = Map<String, dynamic>.from((d['receivables'] as Map?) ?? const {});
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 8),
      Text(_s(rc['say']), style: const TextStyle(fontSize: 13)),
      for (final b in _list(rc['bills']))
        Text('• ${_s(b['project'])} RA ${b['bill']}: ${rs(b['amount'])} (${b['days']} din, ${_s(b['status'])})', style: const TextStyle(fontSize: 12.5)),
      for (final r in _list(rc['retention']))
        Text('• ${_s(r['project'])}: retention ${rs(r['retention'])}${_s(r['release']).isNotEmpty ? ' - ${r['release']} ko' : ''}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  Widget _tenders() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(label: 'Naya tender', icon: Icons.gavel_rounded, onTap: _busy ? null : () => _tender()),
        const SizedBox(height: 8),
        for (final t in _list(_d?['tenders']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _tender(t),
              child: Glass(
                padding: const EdgeInsets.all(12),
                border: (t['days_left'] ?? 99) <= 1 && (t['status'] == 'watching' || t['status'] == 'preparing') ? C.bad : null,
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(_s(t['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                    Pill(_s(t['status'])),
                  ]),
                  Text('${_s(t['dept'])} · ${_s(t['ref'])} · aakhri ${_s(t['last_date'])}${(t['emd'] ?? 0) > 0 ? ' · EMD ${rs(t['emd'])}' : ''}',
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (_s(t['alert']).isNotEmpty) Text(_s(t['alert']), style: const TextStyle(color: C.warn, fontSize: 12.5)),
                  if (((t['missing'] as List?) ?? const []).isNotEmpty && (t['status'] == 'watching' || t['status'] == 'preparing'))
                    Text('Baaki kaagaz: ${(t['missing'] as List).take(4).join(', ')}${(t['missing'] as List).length > 4 ? '...' : ''}',
                        style: const TextStyle(fontSize: 12)),
                ]),
              ),
            ),
          ),
      ]);

  Widget _projects() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(label: 'Naya kaam', icon: Icons.engineering_rounded, onTap: _busy ? null : _project),
        const SizedBox(height: 8),
        for (final p in _list(_d?['projects']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ThekaProjectPage(app: widget.app, id: _s(p['id'])))).then((_) => _load()),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(p['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text('${_s(p['client'])} · ${rs(p['value'])} · kaam ${p['progress_pct']}% · bill ${rs(p['billed'])}',
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (p['delay'] != null) Text(_s((p['delay'] as Map)['say']), style: const TextStyle(fontSize: 12.5)),
                ]),
              ),
            ),
          ),
      ]);

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Theka sahayak'), actions: [
          IconButton(icon: const Icon(Icons.table_view_rounded), tooltip: 'Register Excel', onPressed: _busy ? null : () => _run(() => widget.app.api!.thekaRegister())),
        ]),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Tender'), (2, 'Kaam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _tenders(), _projects()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Bid aap apne DSC se portal par daalti hain. Naap jaisa liya waisa likha jaata hai. Bill aur chitthi department ko aapki haan se. Paisa Hoola nahi deta / leta.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// One work: BOQ progress, naap, RA bills, diary, EOT.
class ThekaProjectPage extends StatefulWidget {
  const ThekaProjectPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<ThekaProjectPage> createState() => _ThekaProjectPageState();
}

class _ThekaProjectPageState extends State<ThekaProjectPage> {
  Map<String, dynamic>? _p;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = await widget.app.api!.thekaProjectGet(widget.id);
      if (mounted) setState(() => _p = p);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _act(String action, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.thekaProjectAct(widget.id, action, body);
      if (mounted) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(p?['name']).isEmpty ? 'Kaam' : _s(p?['name']))),
      body: Aurora(
        child: p == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Kaam ${p['progress_pct']}% · bill ${rs(p['billed'])} · retention ${rs(p['retention_held'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    if (p['delay'] != null) Text(_s((p['delay'] as Map)['say']), style: const TextStyle(fontSize: 12.5)),
                  ]),
                ),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(
                      label: 'Naap likho',
                      icon: Icons.straighten_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Naap (MB)', const [('item', 'BOQ item no'), ('qty', 'Maatra'), ('detail', 'L x B x D / chainage'), ('by', 'Kisne liya')]);
                              if (f != null) await _act('measure', {...f, 'qty': _n(f['qty'])});
                            }),
                  GlassButton(label: 'RA bill banao', icon: Icons.receipt_long_rounded, onTap: _busy ? null : () => _act('ra_bill', const {})),
                  GlassButton(
                      label: 'Site diary',
                      icon: Icons.edit_calendar_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Aaj ki site', const [('labour', 'Mazdoor'), ('work', 'Kya kaam hua'), ('hindrance', 'Rukawat (ho to)'), ('by_client', 'Department ki wajah se? (haan / nahi)')]);
                              if (f != null) {
                                await _act('diary', {...f, 'labour': int.tryParse(f['labour'] ?? '') ?? 0, 'by_client': (f['by_client'] ?? '').toLowerCase().startsWith('h')});
                              }
                            }),
                  GlassButton(
                      label: 'EOT chitthi',
                      icon: Icons.mail_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final r = await _act('eot', const {});
                              if (r != null && context.mounted) {
                                await showDialog<void>(
                                  context: context,
                                  builder: (d) => AlertDialog(
                                    title: const Text('EOT arzi (draft)'),
                                    content: SingleChildScrollView(child: SelectableText(_s(r['text']), style: const TextStyle(fontSize: 12.5))),
                                    actions: [TextButton(onPressed: () => Clipboard.setData(ClipboardData(text: _s(r['text']))), child: const Text('Copy'))],
                                  ),
                                );
                              }
                            }),
                ]),
                const SizedBox(height: 12),
                Text('Bill', style: display(15)),
                for (final b in _list(p['bills']))
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: ThekaCard(key: ValueKey('tb${b['id']}${b['status']}'), v: {'bill_id': b['id'], 'label': '${b['final'] == true ? 'Final' : 'RA'} bill ${b['number']}', ...b},
                        app: widget.app, onDone: _load),
                  ),
                const SizedBox(height: 12),
                Text('BOQ', style: display(15)),
                for (final i in _list(p['boq']))
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Glass(
                      padding: const EdgeInsets.all(10),
                      border: (i['flag'] as Map?)?['level'] == 'stop' ? C.bad : ((i['flag'] as Map?) != null ? C.warn : null),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${_s(i['code'])}${i['extra'] == true ? ' (extra)' : ''} · ${_s(i['description'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                        Text('${i['done']} / ${i['qty']} ${_s(i['unit'])} @ ${rs(i['rate'])}${i['done_pct'] != null ? ' (${i['done_pct']}%)' : ''}',
                            style: const TextStyle(color: C.muted, fontSize: 12.5)),
                        if (i['flag'] != null) Text(_s((i['flag'] as Map)['text']), style: const TextStyle(fontSize: 12, color: C.warn)),
                      ]),
                    ),
                  ),
                const SizedBox(height: 12),
                for (final m in _list(p['stock']))
                  Text('${_s(m['item'])}: aaya ${m['in']}, kharch ${m['used']}, bacha ${m['balance']}', style: const TextStyle(fontSize: 12.5)),
              ]),
      ),
    );
  }
}

/// Chat card (`theka_bill`: her Haan to submit, then pass / paid; `theka_letter` / `theka_day`: text).
class ThekaCard extends StatefulWidget {
  const ThekaCard({super.key, required this.v, required this.app, this.onDone});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onDone;
  @override
  State<ThekaCard> createState() => _ThekaCardState();
}

class _ThekaCardState extends State<ThekaCard> {
  bool _busy = false;
  late String _status = _s(widget.v['status']).isEmpty ? 'draft' : _s(widget.v['status']);

  Future<void> _set(String st, [double? amount]) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.thekaBill(_s(widget.v['bill_id']), {'status': st, if (amount != null) 'amount': amount});
      if (mounted) {
        setState(() => _status = st);
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
    if (v['bill_id'] == null) {
      return Glass(
        child: Row(children: [
          const Icon(Icons.engineering_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(v['text']).isNotEmpty ? _s(v['text']) : '${_s(v['project'])}: ${_s(v['title'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
        ]),
      );
    }
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.receipt_long_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(v['project'])} ${_s(v['label'])}'.trim(), style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status),
        ]),
        Text('Haath mein ~${rs(v['net'] ?? 0)}${(v['passed'] ?? 0) > 0 ? ' · pass ${rs(v['passed'])}' : ''}', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (_status == 'draft') GradientButton(label: 'Haan, department ko diya', icon: Icons.check_rounded, onTap: _busy ? null : () => _set('submitted')),
        if (_status == 'submitted')
          GlassButton(
              label: 'Pass hua',
              icon: Icons.verified_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      final f = await _form(context, 'Kitna pass hua', const [('amount', 'Net pass (khaali = poora)')]);
                      if (f != null) await _set('passed', _n(f['amount']));
                    }),
        if (_status == 'passed' || _status == 'submitted')
          Padding(padding: const EdgeInsets.only(top: 6), child: GlassButton(label: 'Paisa aaya', icon: Icons.account_balance_rounded, onTap: _busy ? null : () => _set('paid'))),
      ]),
    );
  }
}
