/// Profile > Bima sahayak (v0.98): Hoola as an insurance agent's coworker.
/// Summary (book, persistency, commission) -> renewals (due / grace / lapsed) with WhatsApp drafts SHE sends, "premium
/// bhara gaya" (the client paid the insurer; Hoola never takes money), clients + policies, renewal-list import, claims
/// with the documents still missing, and the recommendation card that reaches a client only after her Haan.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'gst_screen.dart' show rs;

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

String lakhs(dynamic v) {
  final n = (v is num) ? v.toDouble() : double.tryParse('$v') ?? 0;
  if (n.abs() >= 1e7) return '₹${(n / 1e7).toStringAsFixed(n % 1e7 == 0 ? 0 : 2)} cr';
  if (n.abs() >= 1e5) return '₹${(n / 1e5).toStringAsFixed(n % 1e5 == 0 ? 0 : 1)} lakh';
  return rs(n);
}

Future<void> _wa(String phone, String text) async {
  final p = phone.replaceAll(RegExp(r'\D'), '');
  final to = p.length == 10 ? '91$p' : p;
  await Native.openExternal(url: 'https://wa.me/$to?text=${Uri.encodeComponent(text)}');
}

class InsuranceScreen extends StatefulWidget {
  const InsuranceScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<InsuranceScreen> createState() => _InsuranceScreenState();
}

class _InsuranceScreenState extends State<InsuranceScreen> {
  Map<String, dynamic>? _sum;
  List<Map<String, dynamic>> _drafts = [];
  List<Map<String, dynamic>> _clients = [];
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
      final s = await api.insSummary();
      final d = await api.insReminders();
      final c = await api.insClients();
      if (mounted) {
        setState(() {
          _sum = s;
          _drafts = _list(d['drafts']);
          _clients = c;
        });
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _import() async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx', 'xls']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    await _run(() => widget.app.api!.insImport(f.name, f.bytes!));
  }

  Future<String?> _form(String title, List<(String, String)> fields, Map<String, TextEditingController> ctl) => showDialog<String>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text(title),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              for (final (k, label) in fields) TextField(controller: ctl.putIfAbsent(k, TextEditingController.new), decoration: InputDecoration(labelText: label)),
            ]),
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(d, 'ok'), child: const Text('Save'))],
        ),
      );

  Future<void> _newClient() async {
    final c = <String, TextEditingController>{};
    if (await _form('Naya graahak', const [
          ('name', 'Naam'),
          ('phone', 'Mobile'),
          ('dob', 'Janam tareekh (dd-mm-yyyy)'),
          ('city', 'Shehar'),
          ('income', 'Saal ki kamai (₹)'),
          ('liabilities', 'Loan baaki (₹)'),
        ], c) !=
        'ok') {
      return;
    }
    final b = {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
    for (final k in const ['income', 'liabilities']) {
      if (b[k] != null) b[k] = '${double.tryParse(b[k]!.replaceAll(',', '')) ?? 0}';
    }
    await _run(() => widget.app.api!.insClientSave(b));
  }

  Future<void> _newPolicy(Map<String, dynamic> client) async {
    final c = <String, TextEditingController>{};
    if (await _form('Policy: ${_s(client['name'])}', const [
          ('insurer', 'Company (LIC, Star Health...)'),
          ('plan', 'Plan'),
          ('number', 'Policy number'),
          ('start', 'Shuru (dd-mm-yyyy)'),
          ('mode', 'Mode (yearly / half_yearly / quarterly / monthly)'),
          ('premium', 'Premium (₹)'),
          ('cover', 'Cover / sum assured (₹)'),
          ('nominee', 'Nominee'),
        ], c) !=
        'ok') {
      return;
    }
    final b = <String, dynamic>{'client': _s(client['id'])};
    for (final e in c.entries) {
      final t = e.value.text.trim();
      if (t.isEmpty) continue;
      b[e.key] = (e.key == 'premium' || e.key == 'cover') ? (double.tryParse(t.replaceAll(',', '')) ?? 0) : t;
    }
    await _run(() => widget.app.api!.insPolicySave(b));
  }

  Widget _stat(String k, String v) => Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(v, style: display(20)),
          Text(k, style: const TextStyle(color: C.muted, fontSize: 11.5)),
        ]),
      );

  Widget _policyTile(Map<String, dynamic> p, {bool paid = true}) {
    final st = Map<String, dynamic>.from((p['premium_state'] as Map?) ?? const {});
    final state = _s(st['state']);
    final col = switch (state) { 'grace' => C.warn, 'lapsed' || 'lapsed_final' => C.bad, _ => C.accent };
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: state == 'lapsed' ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(p['client'])} · ${_s(p['insurer'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Text(rs(p['premium']), style: const TextStyle(fontWeight: FontWeight.w800)),
          ]),
          Text('${_s(p['plan'])} · ${_s(p['number'])} · ${_s(p['mode'])} · cover ${lakhs(p['cover'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 4),
          Row(children: [
            Icon(Icons.circle, size: 9, color: col),
            const SizedBox(width: 6),
            Expanded(child: Text(_s(st['label']), style: TextStyle(color: col, fontSize: 12.5, fontWeight: FontWeight.w700))),
            if (paid && (state == 'due' || state == 'grace' || state == 'lapsed'))
              TextButton(
                onPressed: _busy
                    ? null
                    : () async {
                        final ok = await showDialog<bool>(
                          context: context,
                          builder: (d) => AlertDialog(
                            content: Text('${_s(p['client'])} ne ${_s(p['insurer'])} ko ${rs(p['premium'])} bhar diya?'),
                            actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, bhara'))],
                          ),
                        );
                        if (ok == true) await _run(() => widget.app.api!.insPaid(_s(p['id'])));
                      },
                child: const Text('Bhara gaya'),
              ),
          ]),
        ]),
      ),
    );
  }

  Widget _renewals() {
    final r = Map<String, dynamic>.from((_sum?['renewals'] as Map?) ?? const {});
    final all = [..._list(r['grace']), ..._list(r['due']), ..._list(r['lapsed'])];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (_s(r['say']).isNotEmpty) Text(_s(r['say']), style: const TextStyle(fontSize: 13.5, height: 1.35)),
      const SizedBox(height: 10),
      for (final p in all) _policyTile(p),
      if (_drafts.isNotEmpty) ...[
        const SizedBox(height: 6),
        Text('Yaad dilane ke message (aap bhejengi)', style: display(15)),
        const SizedBox(height: 6),
        for (final d in _drafts)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(d['client']), style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(_s(d['text']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    icon: const Icon(Icons.send_rounded, size: 18),
                    label: const Text('WhatsApp kholo'),
                    onPressed: _s(d['to']).isEmpty
                        ? null
                        : () async {
                            await _wa(_s(d['to']), _s(d['text']));
                            try {
                              await widget.app.api!.insReminded(_s(d['policy_id']));
                            } catch (_) {}
                          },
                  ),
                ),
              ]),
            ),
          ),
      ],
      if (all.isEmpty) const Text('Agle 15 din mein koi premium nahi.', style: TextStyle(color: C.muted)),
    ]);
  }

  Widget _clientsTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Naya graahak', icon: Icons.person_add_alt_rounded, onTap: _busy ? null : _newClient),
          GlassButton(label: 'Renewal list (Excel)', icon: Icons.upload_file_rounded, onTap: _busy ? null : _import),
        ]),
        const SizedBox(height: 10),
        for (final c in _clients)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InsClientPage(app: widget.app, client: c))).then((_) => _load()),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  const Icon(Icons.person_rounded, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(c['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text([if (c['age'] != null) '${c['age']} saal', _s(c['city']), _s(c['phone'])].where((x) => x.isNotEmpty).join(' · '),
                          style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                  IconButton(icon: const Icon(Icons.add_card_rounded), tooltip: 'Policy jodo', onPressed: () => _newPolicy(c)),
                ]),
              ),
            ),
          ),
      ]);

  Widget _claimsTab() {
    final cl = _list(_sum?['claims']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (cl.isEmpty) const Text('Koi khula claim nahi.', style: TextStyle(color: C.muted)),
      for (final c in cl)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: c['overdue'] == true ? C.bad : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(c['client'])} · ${_s(c['insurer'])} · ${_s(c['kind'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
              Text('Policy ${_s(c['policy'])} · ${_s(c['status'])}${_s(c['insurer_ref']).isNotEmpty ? ' · ref ${_s(c['insurer_ref'])}' : ''}',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (((c['missing'] as List?) ?? const []).isNotEmpty)
                Text('Baaki: ${((c['missing'] as List?) ?? const []).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
              if (_s(c['escalate']).isNotEmpty) Text('Der ho gayi: ${_s(c['escalate'])}', style: const TextStyle(fontSize: 12.5, color: C.bad)),
            ]),
          ),
        ),
      const SizedBox(height: 6),
      const Text('Claim shuru karne ke liye chat mein bataiye: "Sunita ka hospital claim, policy STAR9".',
          style: TextStyle(color: C.faint, fontSize: 11.5)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final b = Map<String, dynamic>.from((_sum?['book'] as Map?) ?? const {});
    final bd = _list(_sum?['birthdays']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Bima sahayak'), actions: [
        IconButton(
          icon: const Icon(Icons.table_view_rounded),
          tooltip: 'Policy book Excel',
          onPressed: _busy ? null : () => _run(() => widget.app.api!.insBookFile()),
        ),
      ]),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            Glass(
              child: Row(children: [
                _stat('chalu policy', '${b['inforce'] ?? 0}'),
                _stat('saal ka premium', lakhs(b['yearly_premium'] ?? 0)),
                _stat('persistency', b['persistency_pct'] == null ? '-' : '${b['persistency_pct']}%'),
              ]),
            ),
            if (bd.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final x in bd)
                Glass(
                  padding: const EdgeInsets.all(10),
                  child: Row(children: [
                    const Icon(Icons.cake_rounded, color: C.accent),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${_s(x['client'])}: ${_s(x['on'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
                    TextButton(onPressed: () => _wa(_s(x['to']), _s(x['text'])), child: const Text('Badhai')),
                  ]),
                ),
            ],
            const SizedBox(height: 12),
            Wrap(spacing: 6, children: [
              for (final (i, t) in const [(0, 'Premium'), (1, 'Graahak'), (2, 'Claim')])
                ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
            ]),
            const SizedBox(height: 10),
            if (_sum == null) const Center(child: CircularProgressIndicator()),
            if (_sum != null) [_renewals(), _clientsTab(), _claimsTab()][_tab],
            const SizedBox(height: 14),
            const Text(
                'Premium graahak seedha insurer ko bharta hai; Hoola paisa nahi leta. Proposal par sign aur health ki jaankari graahak khud bharega. '
                'Salah graahak ko sirf aapki haan ke baad. Free-look 30 din.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      ),
    );
  }
}

/// One client: needs (life / health gap), policies.
class InsClientPage extends StatefulWidget {
  const InsClientPage({super.key, required this.app, required this.client});
  final Santosh app;
  final Map<String, dynamic> client;
  @override
  State<InsClientPage> createState() => _InsClientPageState();
}

class _InsClientPageState extends State<InsClientPage> {
  Map<String, dynamic>? _needs;
  List<Map<String, dynamic>> _p = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final id = _s(widget.client['id']);
    try {
      final n = await widget.app.api!.insNeeds(id);
      final p = await widget.app.api!.insPolicies(client: id);
      if (mounted) {
        setState(() {
          _needs = n;
          _p = p;
        });
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final life = (_needs?['life'] as Map?) ?? const {};
    final health = (_needs?['health'] as Map?) ?? const {};
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(widget.client['name']))),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          if (_needs != null)
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Zaroorat', style: display(16)),
                const SizedBox(height: 6),
                if (life.isNotEmpty) Text('Life cover: chahiye ${lakhs(life['need'])}, hai ${lakhs(life['existing'])}, gap ${lakhs(life['gap'])}'),
                Text('Health cover: chahiye ${lakhs(health['need'])}, hai ${lakhs(health['existing'])}'),
                const SizedBox(height: 6),
                for (final g in ((_needs?['gaps'] as List?) ?? const [])) Text('• $g', style: const TextStyle(fontSize: 12.5, color: C.warn)),
                const SizedBox(height: 6),
                const Text('Andaza rule of thumb se; final faisla graahak ka.', style: TextStyle(color: C.faint, fontSize: 11.5)),
              ]),
            ),
          const SizedBox(height: 10),
          for (final p in _p)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(p['insurer'])} · ${_s(p['plan'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text('${_s(p['type_label'])} · ${_s(p['number'])} · ${rs(p['premium'])} ${_s(p['mode'])} · cover ${lakhs(p['cover'])}',
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  Text('${_s((p['premium_state'] as Map?)?['label'])}${_s(p['nominee']).isEmpty ? ' · nominee nahi!' : ''}',
                      style: const TextStyle(fontSize: 12.5)),
                ]),
              ),
            ),
        ]),
      ),
    );
  }
}

/// Chat cards: the recommendation waiting for her Haan (`ins_advice`) and the morning note (`ins_day`).
class InsCard extends StatefulWidget {
  const InsCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<InsCard> createState() => _InsCardState();
}

class _InsCardState extends State<InsCard> {
  String? _draft;
  String _to = '';
  bool _busy = false;

  Future<void> _haan() async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.insAdvice(_s(widget.v['advice_id']), true);
      if (mounted) {
        setState(() {
          _draft = _s(r['draft']);
          _to = _s(r['to']);
        });
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    if (v['advice_id'] == null) {
      return Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InsuranceScreen(app: widget.app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.health_and_safety_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(v['text']), style: const TextStyle(fontWeight: FontWeight.w700))),
            const Icon(Icons.chevron_right_rounded, color: C.muted),
          ]),
        ),
      );
    }
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.health_and_safety_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text('${_s(v['client'])} ke liye salah taiyaar', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 8),
        if (_draft == null) ...[
          const Text('Options ki tulna aur zaroorat ka record ban gaya. Graahak ko bhejne do?', style: TextStyle(fontSize: 13)),
          const SizedBox(height: 8),
          GradientButton(label: 'Haan, message banao', icon: Icons.check_rounded, onTap: _busy ? null : _haan),
        ] else ...[
          SelectableText(_draft!, style: const TextStyle(fontSize: 12.5, height: 1.35)),
          const SizedBox(height: 8),
          GlassButton(label: 'WhatsApp kholo', icon: Icons.send_rounded, onTap: _to.isEmpty ? null : () => _wa(_to, _draft!)),
        ],
      ]),
    );
  }
}
