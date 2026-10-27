/// Profile > Shikayat sahayak (Seva suite): Hoola as the business's complaint handler.
/// Aaj (pavti baaki / der, samay-seema paar, muavze ke card) · Khuli · Sab · Register · Niyam; a case page with proof
/// (EXIF / GPS hataya), stages, closure checklist, closing message drafts she sends, and compensation cards that only
/// her tap (fingerprint for money) can approve. Hoola never pays and never promises what she hasn't approved.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
double? _n(String? v) => v == null ? null : double.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());

Future<Map<String, dynamic>> _call(Santosh app, String method, String path, [Map<String, dynamic>? body]) async {
  final r = await app.api!.call(method, path, body: body);
  return r is Map ? Map<String, dynamic>.from(r) : <String, dynamic>{};
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {Map<String, String> initial = const {}, String ok = 'Aage'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], maxLines: k == 'text' || k == 'resolution' || k == 'reason' ? 3 : 1, decoration: InputDecoration(labelText: label)),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Color _sevColor(String s) => switch (s) { 'urgent' => C.bad, 'high' => C.warn, _ => C.chip };

const _stages = [
  ('acknowledged', 'Pavti di'),
  ('investigating', 'Jaanch'),
  ('waiting_customer', 'Graahak ka intezaar'),
  ('waiting_third_party', 'Company / supplier'),
];

class ShikayatScreen extends StatefulWidget {
  const ShikayatScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ShikayatScreen> createState() => _ShikayatScreenState();
}

class _ShikayatScreenState extends State<ShikayatScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await _call(widget.app, 'GET', '/api/shikayat');
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

  Future<void> _new() async {
    final f = await _form(context, 'Nayi shikayat', const [
      ('text', 'Shikayat (graahak ke shabd)'),
      ('customer', 'Graahak ka naam'),
      ('phone', 'Mobile'),
      ('product', 'Saamaan / seva'),
      ('order_ref', 'Order / bill no (ho to)'),
      ('amount', 'Kitne ka liya tha (Rs)'),
      ('channel', 'Kahan se aayi: call / walk_in / whatsapp / email / social'),
    ]);
    if (f == null || (f['text'] ?? '').isEmpty) return;
    final r = await _run(() => _call(widget.app, 'POST', '/api/shikayat/cases', {
          ...f,
          'amount': _n(f['amount']),
          'channel': (f['channel'] ?? 'walk_in').toLowerCase(),
        }));
    final id = _s(_map(r?['case'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  void _open(String id) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShikayatCasePage(app: widget.app, id: id))).then((_) => _load());

  Widget _caseTile(Map<String, dynamic> c) {
    final isLate = c['overdue'] == true || c['ack_late'] == true;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _open(_s(c['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: isLate ? C.bad : (c['severity'] == 'urgent' ? C.bad : null),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                  child: Text('${_s(c['number'])} · ${_s(c['customer']).isEmpty ? 'Graahak' : _s(c['customer'])}',
                      style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(c['stage_label'])),
            ]),
            Text(_s(c['text']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)),
            const SizedBox(height: 4),
            Wrap(spacing: 6, runSpacing: 4, children: [
              if (_s(c['product']).isNotEmpty) Pill(_s(c['product'])),
              for (final l in (c['cause_labels'] as List? ?? const [])) Pill('$l'),
              if (c['severity'] != 'normal') Pill(_s(c['severity']), fg: _sevColor(_s(c['severity']))),
              for (final f in (c['flags'] as List? ?? const []))
                Pill(switch ('$f') {
                  'repeat_customer' => 'phir se',
                  'product_pattern' => 'same saamaan',
                  'legal_threat' => 'court / helpline',
                  'safety' => 'suraksha',
                  'escalated' => 'bahar gaye',
                  'angry' => 'gussa',
                  _ => '$f',
                }, fg: C.warn),
            ]),
            if (_s(c['due']).isNotEmpty && c['stage'] != 'closed' && c['stage'] != 'rejected')
              Text(
                  c['overdue'] == true
                      ? 'Samay-seema nikal gayi (${_s(c['due'])})'
                      : (c['ack_late'] == true ? 'Pavti der se · hal ${_s(c['due'])} tak' : 'Hal ${_s(c['due'])} tak'),
                  style: TextStyle(fontSize: 12, color: isLate ? C.bad : C.muted)),
          ]),
        ),
      ),
    );
  }

  Widget _today() {
    final d = _map(_d?['day']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        Pill('Khuli ${d['open'] ?? 0}'),
        Pill('Pavti baaki ${d['no_ack'] ?? 0}', fg: (d['ack_late'] ?? 0) > 0 ? C.bad : C.chip),
        Pill('Samay paar ${d['overdue'] ?? 0}', fg: (d['overdue'] ?? 0) > 0 ? C.bad : C.chip),
        Pill('Muavza card ${d['comp_pending'] ?? 0}', fg: (d['comp_pending'] ?? 0) > 0 ? C.warn : C.chip),
      ]),
      const SizedBox(height: 10),
      for (final c in _list(_d?['cases']).where((c) => c['overdue'] == true || c['ack_late'] == true || c['severity'] == 'urgent'))
        _caseTile(c),
      GlassButton(
          label: 'Hoola Network / WhatsApp ticket laao',
          icon: Icons.move_to_inbox_rounded,
          onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/shikayat/import_tickets'))),
    ]);
  }

  Widget _all() {
    final rows = _list(_d?['recent'])
        .where((c) => _q.isEmpty || '${c['customer']} ${c['phone']} ${c['product']} ${c['number']} ${c['text']}'.toLowerCase().contains(_q.toLowerCase()))
        .toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      TextField(
        decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded), hintText: 'Naam, number, saamaan...'),
        onChanged: (v) => setState(() => _q = v),
      ),
      const SizedBox(height: 8),
      for (final c in rows) _caseTile(c),
    ]);
  }

  Widget _register() {
    final now = DateTime.now();
    final months = [for (var i = 0; i < 6; i++) DateTime(now.year, now.month - i, 1)];
    String m(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}';
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Har mahine ka register (Excel): har shikayat, samay par pavti / hal, wajah, rating, muavza, aur summary jo regulator ke form mein bhari ja sake.',
          style: TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 8),
      for (final d in months)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: _SummaryTile(app: widget.app, month: m(d), onExcel: () => _run(() => _call(widget.app, 'POST', '/api/shikayat/register', {'month': m(d)}))),
        ),
    ]);
  }

  Widget _settings() {
    final st = _map(_d?['settings']);
    final sectors = _map(_d?['sectors']);
    final eff = _map(st['effective']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Aapka kaam kis niyam mein aata hai?', style: display(15)),
      const SizedBox(height: 6),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final e in sectors.entries)
          ChoiceChip(
            label: Text(_s(_map(e.value)['label'])),
            selected: st['sector'] == e.key,
            onSelected: _busy ? null : (_) => _run(() => _call(widget.app, 'PUT', '/api/shikayat/settings', {'sector': e.key})),
          ),
      ]),
      const SizedBox(height: 8),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Pavti ${eff['ack_hours']} ghante · hal ${eff['resolve_days']} din', style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(_s(st['law']), style: const TextStyle(fontSize: 12.5)),
          for (final n in (st['notes'] as List? ?? const [])) Text('$n', style: const TextStyle(fontSize: 12, color: C.warn)),
        ]),
      ),
      const SizedBox(height: 8),
      GlassButton(
          label: 'Apne niyam',
          icon: Icons.tune_rounded,
          onTap: _busy
              ? null
              : () async {
                  final o = _map(st['officer']);
                  final f = await _form(context, 'Apne niyam', const [
                    ('business', 'Business ka naam'),
                    ('ack_hours', 'Pavti kitne ghante mein (khaali = niyam)'),
                    ('resolve_days', 'Hal kitne din mein (niyam se kam ho sakta hai)'),
                    ('reopen_days', 'Band ke kitne din tak dobara khule'),
                    ('comp_limit', 'Ek muavza is se zyada ho to yaad dilao (Rs)'),
                    ('month_limit', 'Mahine ka muavza seema (Rs)'),
                    ('officer_name', 'Shikayat adhikari ka naam'),
                    ('officer_phone', 'Shikayat adhikari ka number'),
                    ('officer_email', 'Shikayat adhikari ka email'),
                    ('add_rule', 'Naya niyam (jaise: 5000 se upar refund nahi, sirf replacement)'),
                    ('morning_time', 'Subah ki yaad (HH:MM)'),
                  ], initial: {
                    'business': _s(st['business']),
                    if ((st['ack_hours'] ?? 0) > 0) 'ack_hours': _s(st['ack_hours']),
                    if ((st['resolve_days'] ?? 0) > 0) 'resolve_days': _s(st['resolve_days']),
                    'reopen_days': _s(st['reopen_days']),
                    if ((st['comp_limit'] ?? 0) > 0) 'comp_limit': _s(st['comp_limit']),
                    if ((st['month_limit'] ?? 0) > 0) 'month_limit': _s(st['month_limit']),
                    'officer_name': _s(o['name']),
                    'officer_phone': _s(o['phone']),
                    'officer_email': _s(o['email']),
                    'morning_time': _s(st['morning_time']),
                  }, ok: 'Save');
                  if (f == null) return;
                  await _run(() => _call(widget.app, 'PUT', '/api/shikayat/settings', {
                        for (final k in ['business', 'add_rule', 'morning_time']) if (f[k] != null) k: f[k],
                        for (final k in ['ack_hours', 'resolve_days', 'reopen_days', 'comp_limit', 'month_limit']) if (f[k] != null) k: _n(f[k]),
                        'officer': {'name': f['officer_name'] ?? '', 'phone': f['officer_phone'] ?? '', 'email': f['officer_email'] ?? ''},
                      }));
                }),
      const SizedBox(height: 8),
      for (final r in (st['rules'] as List? ?? const [])) Text('• $r', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 10),
      Text('Kya seekha (wajah ke hisaab se)', style: display(14)),
      for (final e in _map(st['learned']).entries)
        Text(
            '• ${_s(_map(_d?['causes'])[e.key]).isEmpty ? e.key : _s(_map(_d?['causes'])[e.key])}: ${_map(e.value)['cases']} band, '
            'ausat ${((_map(e.value)['days'] ?? 0) / ((_map(e.value)['cases'] ?? 1) == 0 ? 1 : _map(e.value)['cases'])).toStringAsFixed(1)} din'
            '${(_map(e.value)['late'] ?? 0) > 0 ? ', ${_map(e.value)['late']} der se' : ''}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 10),
      for (final n in (_d?['never'] as List? ?? const [])) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final open = _list(_d?['cases']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Shikayat sahayak')),
      floatingActionButton: FloatingActionButton.extended(
          onPressed: _busy ? null : _new, icon: const Icon(Icons.add_comment_rounded), label: const Text('Nayi shikayat')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
            Wrap(spacing: 6, children: [
              for (final (i, t) in [(0, 'Aaj'), (1, 'Khuli ${open.length}'), (2, 'Sab'), (3, 'Register'), (4, 'Niyam')])
                ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
            ]),
            const SizedBox(height: 10),
            if (_busy) const LinearProgressIndicator(),
            if (_d == null)
              const Center(child: CircularProgressIndicator())
            else
              [
                _today(),
                Column(children: [for (final c in open) _caseTile(c)]),
                _all(),
                _register(),
                _settings(),
              ][_tab],
            const SizedBox(height: 14),
            const Text(
                'Muavza (refund / replacement / chhoot) sirf aapki haan se; paisa Hoola nahi deta. Graahak ko message aap bhejti hain. Photo / video ki location hata kar rakhi jaati hai.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      ),
    );
  }
}

class _SummaryTile extends StatefulWidget {
  const _SummaryTile({required this.app, required this.month, required this.onExcel});
  final Santosh app;
  final String month;
  final VoidCallback onExcel;
  @override
  State<_SummaryTile> createState() => _SummaryTileState();
}

class _SummaryTileState extends State<_SummaryTile> {
  Map<String, dynamic>? _s0;

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.call('GET', '/api/shikayat/summary', query: {'month': widget.month});
      if (mounted) setState(() => _s0 = _map(r));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(widget.month, style: const TextStyle(fontWeight: FontWeight.w800))),
            TextButton(onPressed: _load, child: const Text('Dekho')),
            TextButton(onPressed: widget.onExcel, child: const Text('Excel')),
          ]),
          if (_s0 != null) Text(_s(_s0!['say']), style: const TextStyle(fontSize: 12.5)),
        ]),
      );
}

/// One complaint: details, proof, stages, checklist, messages, compensation.
class ShikayatCasePage extends StatefulWidget {
  const ShikayatCasePage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<ShikayatCasePage> createState() => _ShikayatCasePageState();
}

class _ShikayatCasePageState extends State<ShikayatCasePage> {
  Map<String, dynamic>? _c;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await _call(widget.app, 'GET', '/api/shikayat/cases/${widget.id}');
      if (mounted) setState(() => _c = c);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await _call(widget.app, 'POST', '/api/shikayat/cases/${widget.id}/$action', body);
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

  Future<void> _upload(String name, List<int> bytes, String stage) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/shikayat/cases/${widget.id}/proof', name, bytes,
          fields: {'stage': stage}, tries: 2, timeout: const Duration(seconds: 180));
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addProof(String stage) async {
    final pick = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.photo_camera_rounded, color: C.accent), title: const Text('Camera se photo'), onTap: () => Navigator.pop(ctx, 'camera')),
          ListTile(leading: const Icon(Icons.photo_library_rounded, color: C.accent), title: const Text('Gallery se photo'), onTap: () => Navigator.pop(ctx, 'gallery')),
          ListTile(leading: const Icon(Icons.attach_file_rounded, color: C.accent), title: const Text('Video / screenshot / PDF / koi file'), onTap: () => Navigator.pop(ctx, 'file')),
        ]),
      ),
    );
    if (pick == null) return;
    try {
      if (pick == 'file') {
        if (!mounted) return;
        final files = await pickAttachments(context, max: 4);
        for (final f in files) {
          await _upload(f.name, f.bytes, stage);
        }
        return;
      }
      final x = await ImagePicker().pickImage(source: pick == 'camera' ? ImageSource.camera : ImageSource.gallery, maxWidth: 2400);
      if (x == null) return;
      await _upload(x.name.isEmpty ? 'photo.jpg' : x.name, await x.readAsBytes(), stage);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _message(String kind) async {
    final r = await _act('message', {'kind': kind});
    if (r == null || !mounted) return;
    await showShikayatMessage(context, widget.app, r, onDone: _load);
  }

  Future<void> _close() async {
    final c = _c ?? const {};
    final left = _list(c['checklist']).where((x) => x['ok'] != true).toList();
    if (left.isEmpty) {
      await _act('close');
      return;
    }
    final f = await _form(context, 'Checklist adhoori: ${left.map((x) => x['say']).join('; ')}', const [('reason', 'Phir bhi band karne ki wajah')], ok: 'Phir bhi band');
    if (f == null || (f['reason'] ?? '').isEmpty) return;
    await _act('close', {'force': true, 'reason': f['reason']});
  }

  Future<void> _comp() async {
    String kind = 'refund';
    final f = await showDialog<Map<String, String>>(
      context: context,
      builder: (d) {
        final amount = TextEditingController();
        final item = TextEditingController();
        final reason = TextEditingController();
        return StatefulBuilder(
          builder: (d, set) => AlertDialog(
            title: const Text('Muavza (card banega, aapki haan ke baad hi)'),
            content: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final (k, l) in const [
                    ('refund', 'Refund'),
                    ('replacement', 'Replacement'),
                    ('discount', 'Chhoot'),
                    ('goodwill', 'Goodwill'),
                    ('free_service', 'Muft seva'),
                    ('credit', 'Credit / voucher'),
                  ])
                    ChoiceChip(label: Text(l), selected: kind == k, onSelected: (_) => set(() => kind = k)),
                ]),
                TextField(controller: amount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Rakam / keemat (Rs)')),
                TextField(controller: item, decoration: const InputDecoration(labelText: 'Kya dena hai (replacement ho to)')),
                TextField(controller: reason, maxLines: 2, decoration: const InputDecoration(labelText: 'Kyon')),
              ]),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d), child: const Text('Rehne do')),
              TextButton(
                  onPressed: () => Navigator.pop(d, {'kind': kind, 'amount': amount.text, 'item': item.text, 'reason': reason.text}),
                  child: const Text('Card banao')),
            ],
          ),
        );
      },
    );
    if (f == null) return;
    setState(() => _busy = true);
    try {
      final r = await _call(widget.app, 'POST', '/api/shikayat/cases/${widget.id}/comp',
          {'kind': f['kind'], 'amount': _n(f['amount']), 'item': f['item'] ?? '', 'reason': f['reason'] ?? ''});
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _proofs(List<Map<String, dynamic>> ps) {
    final api = widget.app.api!;
    return Wrap(spacing: 8, runSpacing: 8, children: [
      for (final p in ps)
        Press(
          onTap: () {
            if (p['kind'] == 'photo' || p['kind'] == 'screenshot') {
              showDialog<void>(
                  context: context,
                  builder: (d) => Dialog(child: InteractiveViewer(child: Image.network(api.absolute(_s(p['url'])), headers: api.authHeaders))));
            } else {
              _snack(context, '${_s(p['name'])} (${p['kind']})${p['cleaned'] == true ? ' · metadata hataya' : ''}');
            }
          },
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Stack(children: [
              if (p['kind'] == 'photo' || p['kind'] == 'screenshot')
                Image.network(api.absolute(_s(p['url'])), headers: api.authHeaders, width: 88, height: 88, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox(width: 88, height: 88, child: Icon(Icons.broken_image_rounded)))
              else
                Container(
                  width: 88,
                  height: 88,
                  color: C.panel,
                  alignment: Alignment.center,
                  child: Icon(switch (_s(p['kind'])) { 'video' => Icons.videocam_rounded, 'audio' => Icons.mic_rounded, _ => Icons.description_rounded },
                      color: C.accent),
                ),
              Positioned(
                left: 4,
                bottom: 4,
                child: Pill(p['stage'] == 'fix' ? 'theek' : 'shikayat', fg: p['stage'] == 'fix' ? C.ok : C.chip),
              ),
            ]),
          ),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final open = c != null && !['closed', 'rejected'].contains(c['stage']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(c?['number']).isEmpty ? 'Shikayat' : _s(c?['number']))),
      body: Aurora(
        child: c == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  if (_busy) const LinearProgressIndicator(),
                  Glass(
                    border: c['severity'] == 'urgent' ? C.bad : null,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(
                            child: Text('${_s(c['customer']).isEmpty ? 'Graahak' : _s(c['customer'])}${_s(c['phone']).isNotEmpty ? ' · ${c['phone']}' : ''}',
                                style: const TextStyle(fontWeight: FontWeight.w800))),
                        Pill(_s(c['stage_label'])),
                      ]),
                      const SizedBox(height: 4),
                      SelectableText(_s(c['text']), style: const TextStyle(fontSize: 13.5, height: 1.35)),
                      const SizedBox(height: 6),
                      Text(
                          [
                            if (_s(c['product']).isNotEmpty) _s(c['product']),
                            if (_s(c['order_ref']).isNotEmpty) 'order ${c['order_ref']}',
                            _s(c['channel']),
                            'aayi ${_s(c['received'])}',
                          ].join(' · '),
                          style: const TextStyle(fontSize: 12, color: C.muted)),
                      Text(
                          _s(c['ack_at']).isNotEmpty
                              ? 'Pavti ${_s(c['ack_at'])} · hal ${_s(c['due'])} tak'
                              : 'Pavti ${_s(c['ack_by'])} tak · hal ${_s(c['due'])} tak',
                          style: TextStyle(fontSize: 12, color: c['overdue'] == true || c['ack_late'] == true ? C.bad : C.muted)),
                      if (_s(c['owner']).isNotEmpty) Text('Zimmedaar: ${c['owner']}', style: const TextStyle(fontSize: 12)),
                      if (_s(c['commission']).isNotEmpty)
                        Text('Graahak court jaaye to: ${c['commission']}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
                      if (_map(c['escalated']).isNotEmpty)
                        Text('Graahak bahar gaye: ${_map(c['escalated'])['to']} ${_s(_map(c['escalated'])['ref'])}',
                            style: const TextStyle(fontSize: 12, color: C.bad)),
                    ]),
                  ),
                  const SizedBox(height: 8),
                  Text('Saboot', style: display(15)),
                  const SizedBox(height: 6),
                  _proofs(_list(c['proofs'])),
                  const SizedBox(height: 6),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    GlassButton(label: 'Shikayat ka saboot', icon: Icons.add_a_photo_rounded, onTap: _busy ? null : () => _addProof('complaint')),
                    GlassButton(label: 'Theek hone ka saboot', icon: Icons.verified_rounded, onTap: _busy ? null : () => _addProof('fix')),
                  ]),
                  const SizedBox(height: 12),
                  if (open) ...[
                    Text('Kaam', style: display(15)),
                    const SizedBox(height: 6),
                    Wrap(spacing: 6, runSpacing: 6, children: [
                      for (final (k, l) in _stages)
                        ChoiceChip(label: Text(l), selected: c['stage'] == k, onSelected: _busy ? null : (_) => _act('update', {'stage': k})),
                    ]),
                    const SizedBox(height: 8),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      GlassButton(label: 'Pavti message', icon: Icons.mark_email_read_rounded, onTap: _busy ? null : () => _message('ack')),
                      GlassButton(label: 'Update message', icon: Icons.update_rounded, onTap: _busy ? null : () => _message('update')),
                      GlassButton(
                          label: 'Note / zimmedaar',
                          icon: Icons.edit_note_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Note', const [('note', 'Kya hua'), ('owner', 'Kaun sambhalega (team)'), ('due', 'Nayi tareekh (ho to)')]);
                                  if (f != null) await _act('update', f);
                                }),
                      GradientButton(
                          label: 'Hal ho gaya',
                          icon: Icons.task_alt_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Kya hal kiya', const [('resolution', 'Graahak ko yahi bataya jayega'), ('fix_proof', 'Saboot (bill / photo / unka message)')],
                                      initial: {'resolution': _s(c['resolution']), 'fix_proof': _s(c['fix_proof'])});
                                  if (f != null) await _act('resolve', f);
                                }),
                      GlassButton(label: 'Muavza card', icon: Icons.volunteer_activism_rounded, onTap: _busy ? null : _comp),
                      GlassButton(
                          label: 'Nahi maani',
                          icon: Icons.block_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Shikayat kyon nahi maani', const [('note', 'Saaf wajah (graahak ko bhi batayi jayegi)')]);
                                  if (f != null) {
                                    final r = await _act('update', {'stage': 'rejected', 'note': f['note'] ?? ''});
                                    if (r != null) await _message('reject');
                                  }
                                }),
                      GlassButton(
                          label: 'Graahak bahar gaye',
                          icon: Icons.gavel_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Kahan gaye', const [('to', '1915 / ombudsman / consumer court / social media'), ('ref', 'Docket / notice no')]);
                                  if (f != null) await _act('escalate', f);
                                }),
                    ]),
                  ],
                  if (c['stage'] == 'resolved' || c['stage'] == 'closed') ...[
                    const SizedBox(height: 12),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      GlassButton(label: 'Closing message', icon: Icons.forum_rounded, onTap: _busy ? null : () => _message('close')),
                      GlassButton(
                          label: 'Graahak: theek hua',
                          icon: Icons.thumb_up_alt_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Graahak ne kya kaha', const [('satisfaction', 'Rating 1-5 (ho to)'), ('feedback', 'Unke shabd')]);
                                  if (f != null) await _act('confirm', {'fixed': true, 'satisfaction': int.tryParse(f['satisfaction'] ?? ''), 'feedback': f['feedback'] ?? ''});
                                }),
                      GlassButton(
                          label: 'Graahak: theek nahi',
                          icon: Icons.thumb_down_alt_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Kya abhi bhi dikkat hai', const [('feedback', 'Unke shabd')]);
                                  if (f != null) await _act('confirm', {'fixed': false, 'feedback': f['feedback'] ?? ''});
                                }),
                      GlassButton(label: 'Rating poochho', icon: Icons.star_rate_rounded, onTap: _busy ? null : () => _message('satisfaction')),
                      if (c['stage'] == 'resolved') GradientButton(label: 'Band karo', icon: Icons.lock_rounded, onTap: _busy ? null : _close),
                      if (_s(c['ticket_ref']).isNotEmpty)
                        GlassButton(label: 'Ticket update', icon: Icons.sync_rounded, onTap: _busy ? null : () => _act('ticket_sync')),
                    ]),
                  ],
                  if (c['stage'] == 'closed' || c['stage'] == 'rejected') ...[
                    const SizedBox(height: 8),
                    GlassButton(
                        label: 'Phir kholo',
                        icon: Icons.lock_open_rounded,
                        onTap: _busy
                            ? null
                            : () async {
                                final f = await _form(context, 'Phir kyon khol rahe', const [('reason', 'Wajah')]);
                                if (f != null) await _act('reopen', f);
                              }),
                  ],
                  const SizedBox(height: 12),
                  Text('Band karne se pehle', style: display(15)),
                  for (final x in _list(c['checklist']))
                    Row(children: [
                      Icon(x['ok'] == true ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded, size: 18, color: x['ok'] == true ? C.ok : C.faint),
                      const SizedBox(width: 6),
                      Expanded(child: Text(_s(x['say']), style: const TextStyle(fontSize: 12.5))),
                    ]),
                  if (_list(c['comps']).isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text('Muavza', style: display(15)),
                    for (final x in _list(c['comps']))
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: ShikayatCompCard(
                            key: ValueKey('${x['id']}${x['status']}'), app: widget.app, data: {'comp': x, 'number': c['number']}, onDone: _load),
                      ),
                  ],
                  if (_s(c['resolution']).isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text('Hal', style: display(15)),
                    Text(_s(c['resolution']), style: const TextStyle(fontSize: 13)),
                  ],
                  const SizedBox(height: 12),
                  Text('Graahak aage kahan ja sakte hain', style: display(14)),
                  for (final r in _list(c['routes'])) Text('• ${_s(r['name'])}: ${_s(r['how'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
                  const SizedBox(height: 12),
                  Text('Hisaab', style: display(14)),
                  for (final l in _list(c['log']).reversed)
                    Text('${_s(l['at']).replaceFirst('T', ' ').substring(0, _s(l['at']).length >= 16 ? 16 : _s(l['at']).length)} · ${_s(l['text'])}',
                        style: const TextStyle(fontSize: 11.5, color: C.faint)),
                ]),
              ),
      ),
    );
  }
}

/// A message draft she sends: copy, WhatsApp, SMS, or business WhatsApp (her tap, 24 h window), then "Bhej diya".
Future<void> showShikayatMessage(BuildContext context, Santosh app, Map<String, dynamic> m, {VoidCallback? onDone}) async {
  final text = TextEditingController(text: _s(m['text']));
  final caseId = _s(m['case_id']);
  final kind = _s(m['kind']).isEmpty ? 'close' : _s(m['kind']);
  await showDialog<void>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text('Graahak ko message (${_s(m['number'])})'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(controller: text, maxLines: 9, style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 6),
          const Text('Aap padh kar bhejiye. Jo muavza aapne maana nahi, uska vaada mat likhiye.', style: TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      ),
      actions: [
        TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: text.text));
              _snack(d, 'Copy ho gaya');
            },
            child: const Text('Copy')),
        if (_s(m['wa_link']).isNotEmpty)
          TextButton(
              onPressed: () async {
                final url = _s(m['wa_link']).split('?').first;
                await Native.openExternal(url: '$url?text=${Uri.encodeComponent(text.text)}');
              },
              child: const Text('WhatsApp')),
        if (_s(m['sms_link']).isNotEmpty)
          TextButton(
              onPressed: () async {
                final url = _s(m['sms_link']).split('?').first;
                await Native.openExternal(url: '$url?body=${Uri.encodeComponent(text.text)}');
              },
              child: const Text('SMS')),
        if (m['business_ok'] == true)
          TextButton(
              onPressed: () async {
                try {
                  final r = await _call(app, 'POST', '/api/shikayat/cases/$caseId/send', {'text': text.text, 'kind': kind});
                  if (d.mounted) {
                    _snack(d, _s(r['say']));
                    Navigator.pop(d);
                  }
                  onDone?.call();
                } catch (e) {
                  if (d.mounted) _snack(d, '$e');
                }
              },
              child: const Text('Business WhatsApp se bhejo')),
        TextButton(
            onPressed: () async {
              try {
                final r = await _call(app, 'POST', '/api/shikayat/cases/$caseId/told', {'kind': kind, 'how': 'whatsapp'});
                if (d.mounted) {
                  _snack(d, _s(r['say']));
                  Navigator.pop(d);
                }
                onDone?.call();
              } catch (e) {
                if (d.mounted) _snack(d, '$e');
              }
            },
            child: const Text('Maine bhej diya')),
      ],
    ),
  );
}

/// Chat card `shikayat_case`: a new / changed complaint (tap = open it).
class ShikayatCaseCard extends StatelessWidget {
  const ShikayatCaseCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final c = _map(data['case']);
    final ev = _s(data['event']);
    return Press(
      onTap: _s(c['id']).isEmpty
          ? null
          : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShikayatCasePage(app: app, id: _s(c['id'])))),
      child: Glass(
        border: c['severity'] == 'urgent' ? C.bad : null,
        child: Row(children: [
          Icon(ev == 'closed' ? Icons.lock_rounded : (ev == 'resolved' ? Icons.task_alt_rounded : Icons.report_problem_rounded), color: C.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${ev == 'new' ? 'Nayi shikayat' : 'Shikayat'} ${_s(c['number'])}${_s(c['customer']).isNotEmpty ? ' · ${c['customer']}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              Text(
                  [
                    _s(c['stage_label']),
                    if ((c['cause_labels'] as List?)?.isNotEmpty == true) (c['cause_labels'] as List).join(', '),
                    if (_s(c['due']).isNotEmpty && ev == 'new') 'hal ${c['due']} tak',
                  ].join(' · '),
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
            ]),
          ),
          const Icon(Icons.chevron_right_rounded, color: C.faint),
        ]),
      ),
    );
  }
}

/// Chat card `shikayat_message`: a draft for the customer (she sends it).
class ShikayatMessageCard extends StatelessWidget {
  const ShikayatMessageCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.forum_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('Graahak ke liye draft · ${_s(data['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['text']), maxLines: 8, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, height: 1.35)),
          const SizedBox(height: 8),
          GlassButton(label: 'Dekho aur bhejo', icon: Icons.send_rounded, onTap: () => showShikayatMessage(context, app, data)),
        ]),
      );
}

/// Chat card `shikayat_day` / `shikayat_alert`: the morning list and deadline reminders.
class ShikayatNoteCard extends StatelessWidget {
  const ShikayatNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShikayatScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.support_agent_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(data['text']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
          ]),
        ),
      );
}

/// Chat card `shikayat_comp`: refund / replacement / chhoot / goodwill. ONLY her tap decides; money needs her fingerprint
/// once a phone key is set up (428 -> challenge -> sign -> resend). Then she gives it herself and taps "De diya".
class ShikayatCompCard extends StatefulWidget {
  const ShikayatCompCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ShikayatCompCard> createState() => _ShikayatCompCardState();
}

class _ShikayatCompCardState extends State<ShikayatCompCard> {
  bool _busy = false;
  late Map<String, dynamic> _comp = _map(widget.data['comp']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = await _call(widget.app, 'POST', '/api/shikayat/comp/$id/challenge');
    final show = _map(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Muavze ki haan' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'Fingerprint nahi diya, isliye haan nahi hui.',
        'key_invalidated' => 'Phone mein naya fingerprint juda hai: Profile > Fingerprint se haan mein phone phir se jodiye.',
        _ => 'Fingerprint se haan nahi ho payi (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_comp['id']);
    String note = '';
    if (!yes) {
      final f = await _form(context, 'Kyon nahi', const [('note', 'Wajah (aapke liye)')]);
      if (f == null) return;
      note = f['note'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_comp['hash']), 'note': note};
      Map<String, dynamic> r;
      try {
        r = await _call(widget.app, 'POST', '/api/shikayat/comp/$id/decide', body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await _call(widget.app, 'POST', '/api/shikayat/comp/$id/decide', {...body, 'proof': proof});
      }
      if (mounted) {
        setState(() => _comp = _map(r['comp']).isEmpty ? _comp : _map(r['comp']));
        _snack(context, _s(r['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _given() async {
    final f = await _form(context, 'Kaise diya', const [('how', 'UPI / cash / naya saamaan / bill mein chhoot'), ('ref', 'UTR / bill no (ho to)')]);
    if (f == null) return;
    setState(() => _busy = true);
    try {
      final r = await _call(widget.app, 'POST', '/api/shikayat/comp/${_s(_comp['id'])}/given', {'how': f['how'] ?? '', 'ref': f['ref'] ?? ''});
      if (mounted) {
        setState(() => _comp = _map(r['comp']).isEmpty ? _comp : _map(r['comp']));
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
    final x = _comp;
    final st = _s(x['status']);
    final show = _map(widget.data['show']);
    return Glass(
      border: st == 'pending' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.volunteer_activism_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text(
                  '${_s(show['case']).isNotEmpty ? show['case'] : _s(widget.data['number'])} · ${_s(x['kind_label'])}${_s(x['amount_text']).isNotEmpty ? ' ${x['amount_text']}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'pending' => 'aapki haan?', 'approved' => 'maana', 'given' => 'diya', 'rejected' => 'nahi', _ => st },
              fg: st == 'pending' ? C.accent : (st == 'rejected' ? C.bad : C.ok)),
        ]),
        if (_s(show['customer']).isNotEmpty) Text('Graahak: ${show['customer']}', style: const TextStyle(fontSize: 12.5)),
        if (_s(x['item']).isNotEmpty) Text('Dena: ${x['item']}', style: const TextStyle(fontSize: 12.5)),
        if (_s(x['reason']).isNotEmpty) Text(_s(x['reason']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final ch in (x['checks'] as List? ?? const [])) Text('• $ch', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(x['given_how']).isNotEmpty) Text('Diya: ${x['given_how']}', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (st == 'pending')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, dena hai', icon: Icons.fingerprint_rounded, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Nahi', icon: Icons.close_rounded, onTap: _busy ? null : () => _decide(false))),
          ]),
        if (st == 'approved') GlassButton(label: 'Maine de diya', icon: Icons.check_rounded, onTap: _busy ? null : _given),
        const SizedBox(height: 4),
        const Text('Paisa / saamaan aap khud dengi; Hoola sirf hisaab rakhta hai.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}
