/// Profile > Influencer Sahayak: Hoola as an influencer / talent manager's coworker.
/// Aaj (posts today / tomorrow / late, disclosure problems, unpaid invoices, exclusivity ending, cards waiting) · Creators (roster,
/// follower counts as SHE typed them, rate card from HER numbers) · Deals (pipeline, deliverables, posts, money) · Calendar ·
/// Jaanch (paste any caption: ASCI / CCPA disclosure check) · Niyam (agency, GSTIN, UPI, commission, payment days).
/// Pitch / contract / content to a brand, go-live note to a creator, invoice, creator payout (fingerprint once a phone key is set
/// up), campaign report and any message run only after HER tap. Hoola never posts, never sends, never takes or pays money.
library;

import 'package:flutter/material.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());
String _rs(dynamic v) => v == null ? '[price?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

const _longKeys = {'brief', 'caption', 'script', 'text', 'terms', 'notes', 'csv', 'rules', 'address'};

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Continue', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: _longKeys.contains(k) ? 4 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
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

Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']), mail = _s(draft['mail']), upi = _s(draft['upi']);
  if (wa.isEmpty && sms.isEmpty && mail.isEmpty && upi.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (mail.isNotEmpty) GlassButton(label: 'Email draft', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (upi.isNotEmpty) GlassButton(label: 'Open UPI app', icon: Icons.currency_rupee_rounded, height: 40, onTap: () => Native.openExternal(url: upi)),
  ]);
}

Widget _checkBox(Map<String, dynamic> chk) {
  if (chk.isEmpty) return const SizedBox.shrink();
  final ok = chk['ok'] == true;
  return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Row(children: [
      Icon(ok ? Icons.verified_rounded : Icons.block_rounded, color: ok ? C.ok : C.bad, size: 18),
      const SizedBox(width: 6),
      Text(ok ? 'Disclosure is fine' : 'Blocker', style: TextStyle(fontWeight: FontWeight.w800, color: ok ? C.ok : C.bad)),
    ]),
    for (final b in _strs(chk['block'])) Text('✗ $b', style: const TextStyle(fontSize: 12, color: C.bad)),
    for (final w in _strs(chk['warn'])) Text('• $w', style: const TextStyle(fontSize: 12, color: C.warn)),
  ]);
}

class InfluencerScreen extends StatefulWidget {
  const InfluencerScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<InfluencerScreen> createState() => _InfluencerScreenState();
}

class _InfluencerScreenState extends State<InfluencerScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _cal;
  Map<String, dynamic>? _chk;
  int _tab = 0;
  bool _busy = false;
  late String _month = DateTime.now().toIso8601String().substring(0, 7);
  final _caption = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _caption.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/influencer'));
      final cal = _m(await widget.app.api!.call('GET', '/api/influencer/calendar', query: {'month': _month}));
      if (mounted) setState(() {
        _d = d;
        _cal = cal;
      });
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

  void _openDeal(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => InfluencerDealPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('WAITING FOR YOUR APPROVAL'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: InfluencerCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('today', 'POST TODAY'), ('tomorrow', 'POST TOMORROW'), ('late', 'LATE'), ('blocked', 'DISCLOSURE BLOCKER')])
        if (_strs(day[k]).isNotEmpty) ...[Caption(label), Wrap(spacing: 6, runSpacing: 6, children: [for (final p in _strs(day[k])) Pill(p)]),
          const SizedBox(height: 10)],
      if (_strs(day['unpaid']).isNotEmpty) ...[const Caption('PAYMENTS PENDING'), for (final x in _strs(day['unpaid'])) Text('• $x')],
      if (_strs(day['exclusivity']).isNotEmpty) ...[const Caption('EXCLUSIVITY'), for (final x in _strs(day['exclusivity'])) Text('• $x')],
    ]);
  }

  Future<void> _newCreator() async {
    final f = await _form(context, 'New creator', const [
      ('name', 'Name'), ('phone', 'Mobile'), ('niche', 'Niche (beauty, food ...)'), ('city', 'City'), ('language', 'Language'),
      ('platform', 'Platform (instagram / youtube)'), ('handle', 'Handle (@...)'), ('followers', 'Followers (e.g. 1.2 lakh)'),
      ('avg_likes', 'Average likes'), ('avg_comments', 'Average comments'), ('qualification', 'Health qualification (if any)'),
      ('sebi_reg', 'SEBI number (finance creator)'), ('upi_id', 'Creator\'s UPI ID (payout)'),
    ], ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/influencer/creators', f);
  }

  Future<void> _rate(Map<String, dynamic> c) async {
    final f = await _form(context, 'Rate: ${_s(c['name'])}', const [
      ('platform', 'Platform'), ('fmt', 'Format (reel / story / video ...)'), ('price', 'Your price (₹, GST extra)'),
      ('usage_days', 'Usage rights days (0 = organic only)'), ('usage_price', 'Usage price'),
    ], ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/influencer/creators/${_s(c['number'])}/rates', {
      ...f,
      if (f['price'] != null) 'price': _n(f['price']),
      if (f['usage_days'] != null) 'usage_days': _n(f['usage_days'])?.toInt(),
      if (f['usage_price'] != null) 'usage_price': _n(f['usage_price']),
    });
  }

  Widget _creators() {
    final cs = _list(_d?['creators']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'New creator', icon: Icons.person_add_rounded, height: 46, onTap: _busy ? null : _newCreator),
      const SizedBox(height: 6),
      const Text('Followers are exactly what you write (with the date). Buying followers / likes: never.',
          style: TextStyle(fontSize: 11.5, color: C.faint)),
      const SizedBox(height: 10),
      for (final c in cs)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(c['number'])} · ${_s(c['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              if (c['virtual'] == true) const Pill('AI / virtual'),
              if (_s(c['sebi_reg']).isNotEmpty) const Padding(padding: EdgeInsets.only(left: 6), child: Pill('SEBI')),
              Padding(padding: const EdgeInsets.only(left: 6), child: Pill(_s(c['status']))),
            ]),
            Text(_s(c['niche']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
            for (final h in _list(c['handles']))
              Text('${_s(h['platform'])} ${_s(h['handle'])} · ${_s(h['followers'] ?? '?')} (${_s(h['on'])})', style: const TextStyle(fontSize: 12)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 6, children: [
              GlassButton(label: 'Rate', icon: Icons.sell_rounded, height: 38, onTap: _busy ? null : () => _rate(c)),
              GlassButton(label: 'Followers update', icon: Icons.trending_up_rounded, height: 38, onTap: _busy ? null : () async {
                final f = await _form(context, 'Today\'s followers', const [('platform', 'Platform'), ('followers', 'Followers'),
                  ('avg_likes', 'Average likes'), ('avg_comments', 'Average comments')], ok: 'Save');
                if (f == null) return;
                final r = await _run('POST', '/api/influencer/creators', {'id': _s(c['number']), ...f});
                final sig = _strs(_m(r?['creator'])['signals']);
                if (sig.isNotEmpty && context.mounted) {
                  await showDialog<void>(context: context, builder: (d) => AlertDialog(
                    title: const Text('Things to note'),
                    content: Text(sig.join('\n\n')),
                    actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('OK'))],
                  ));
                }
              }),
              GlassButton(label: 'Rate card PDF', icon: Icons.picture_as_pdf_rounded, height: 38, onTap: () async {
                final r = await _call(context, widget.app, 'GET', '/api/influencer/creators/${_s(c['number'])}/ratecard');
                if (r == null || !context.mounted) return;
                await showDialog<void>(context: context, builder: (d) => AlertDialog(
                  title: Text('Rate card · ${_s(c['name'])}'),
                  content: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    for (final x in _list(r['rates'])) Text('${_s(x['platform_label'])} ${_s(x['fmt_label'])}: ${_s(x['price_text'])}'),
                    if (_list(r['history']).isNotEmpty) ...[const SizedBox(height: 8), const Text('Your past deals (median):')],
                    for (final h in _list(r['history'])) Text('${_s(h['platform'])} ${_s(h['fmt'])}: ${_rs(h['median'])} (${_s(h['deals'])})'),
                    const SizedBox(height: 8),
                    Text(_s(r['note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
                  ])),
                  actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Close'))],
                ));
              }),
            ]),
          ]),
        ),
    ]);
  }

  Future<void> _newDeal() async {
    final f = await _form(context, 'New brand deal', const [
      ('creator', 'Creator (name / C-001)'), ('brand', 'Brand'), ('brand_contact', 'Who at the brand'), ('brand_phone', 'Brand mobile'),
      ('brand_email', 'Brand email'), ('product', 'Product'), ('brief', 'Brand brief (paste)'),
      ('fmt', 'Deliverable format (reel / story / video)'), ('platform', 'Platform'), ('qty', 'How many'), ('due', 'Due by (DD-MM-YYYY)'),
      ('fee', 'Fee (if different from the rate card)'), ('excl_category', 'Exclusivity category (optional)'),
    ], ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/influencer/deals', {
      for (final k in ['creator', 'brand', 'brand_contact', 'brand_phone', 'brand_email', 'product', 'brief', 'excl_category'])
        if (f[k] != null) k: f[k],
      if (f['fee'] != null) 'fee': _n(f['fee']),
      if (f['fmt'] != null)
        'deliverables': [{'fmt': f['fmt'], 'platform': f['platform'] ?? 'instagram', 'qty': _n(f['qty'])?.toInt() ?? 1, if (f['due'] != null) 'due': f['due']}],
    });
  }

  Widget _deals() {
    final ds = _list(_d?['deals']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'New deal', icon: Icons.handshake_rounded, height: 46, onTap: _busy ? null : _newDeal),
      const SizedBox(height: 12),
      for (final d in ds)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: InkWell(
            onTap: () => _openDeal(_s(d['number'])),
            child: Row(children: [
              const Icon(Icons.campaign_rounded, color: C.accent),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(d['number'])} · ${_s(d['brand'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${_s(d['creator'])} · ${_s(d['product'])} · ${d['fee'] == null ? '[price?]' : _rs(d['fee'])}',
                    style: const TextStyle(fontSize: 12.5, color: C.muted)),
              ])),
              Pill(_s(d['stage_label'])),
            ]),
          ),
        ),
    ]);
  }

  Widget _calendar() {
    final days = _m(_cal?['days']);
    final keys = days.keys.toList()..sort();
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        IconButton(icon: const Icon(Icons.chevron_left_rounded), onPressed: () {
          final dt = DateTime.parse('$_month-01');
          setState(() => _month = DateTime(dt.year, dt.month - 1).toIso8601String().substring(0, 7));
          _load();
        }),
        Expanded(child: Center(child: Text(_month, style: const TextStyle(fontWeight: FontWeight.w800)))),
        IconButton(icon: const Icon(Icons.chevron_right_rounded), onPressed: () {
          final dt = DateTime.parse('$_month-01');
          setState(() => _month = DateTime(dt.year, dt.month + 1).toIso8601String().substring(0, 7));
          _load();
        }),
      ]),
      for (final n in _strs(_cal?['notes'])) Text('• $n', style: const TextStyle(color: C.warn)),
      for (final k in keys) ...[
        Caption(k),
        for (final p in _list(days[k]))
          Glass(
            margin: const EdgeInsets.only(bottom: 6),
            child: InkWell(
              onTap: () => _openDeal(_s(p['deal'])),
              child: Row(children: [
                Expanded(child: Text('${_s(p['number'])} · ${_s(p['creator'])} · ${_s(p['brand'])} · ${_s(p['platform_label'])} ${_s(p['fmt_label'])}')),
                Pill(_s(p['status_label']), fg: p['status'] == 'live' ? C.ok : C.chip),
              ]),
            ),
          ),
      ],
      if (_list(_cal?['undated']).isNotEmpty) ...[const Caption('NO DATE'), for (final p in _list(_cal?['undated'])) Text('• ${_s(p['number'])} ${_s(p['brand'])}')],
    ]);
  }

  Widget _jaanch() => ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Paste any caption: ASCI / CCPA disclosure check (#ad on the first line, video / story / podcast, AI label,'
            'health, finance, crypto).', style: TextStyle(fontSize: 12.5, color: C.muted)),
        const SizedBox(height: 8),
        TextField(controller: _caption, maxLines: 6, decoration: const InputDecoration(hintText: '#ad ...')),
        const SizedBox(height: 8),
        GradientButton(label: 'Check', icon: Icons.fact_check_rounded, height: 46, onTap: _busy ? null : () async {
          try {
            final r = _m(await widget.app.api!.call('POST', '/api/influencer/check', body: {'caption': _caption.text}));
            if (mounted) setState(() => _chk = r);
          } catch (e) {
            if (mounted) _snack(context, '$e');
          }
        }),
        const SizedBox(height: 10),
        if (_chk != null) Glass(child: _checkBox(_chk!)),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['agency']).isEmpty ? 'No agency name' : _s(st['agency']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('GSTIN ${_s(st['gstin']).isEmpty ? '-' : _s(st['gstin'])} · UPI ${_s(st['upi_id']).isEmpty ? '-' : _s(st['upi_id'])}'),
        Text('Commission ${_s(st['commission_pct'] ?? '?')}% · payment in ${_s(st['pay_days'])} days · morning note ${_s(st['morning_time'])}'),
        const SizedBox(height: 6),
        for (final n in _strs(st['notes'])) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.faint)),
      ])),
      const SizedBox(height: 10),
      GradientButton(label: 'Edit rules', icon: Icons.tune_rounded, height: 46, onTap: _busy ? null : () async {
        final f = await _form(context, 'Rules', const [
          ('agency', 'Agency / your name'), ('gstin', 'GSTIN'), ('upi_id', 'Your UPI ID'), ('commission_pct', 'Commission %'),
          ('pay_days', 'Brand payment days'), ('phone', 'Phone'), ('email', 'Email'), ('address', 'Address'), ('terms', 'Contract terms'),
          ('morning_time', 'Morning note (HH:MM)'),
        ], ok: 'Save', initial: {for (final k in ['agency', 'gstin', 'upi_id', 'phone', 'email', 'address', 'terms', 'morning_time']) k: _s(st[k]),
          'commission_pct': _s(st['commission_pct']), 'pay_days': _s(st['pay_days'])});
        if (f == null) return;
        await _run('PUT', '/api/influencer/settings', {
          ...f,
          if (f['commission_pct'] != null) 'commission_pct': _n(f['commission_pct']),
          if (f['pay_days'] != null) 'pay_days': _n(f['pay_days'])?.toInt(),
        });
      }),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Today', 'Creators', 'Deals', 'Calendar', 'Check', 'Rules'];
    final body = switch (_tab) { 0 => _aaj(), 1 => _creators(), 2 => _deals(), 3 => _calendar(), 4 => _jaanch(), _ => _niyam() };
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(title: const Text('Influencer manager'), backgroundColor: Colors.transparent, elevation: 0),
      body: Column(children: [
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ),
          ]),
        ),
        Expanded(child: _d == null ? const Center(child: CircularProgressIndicator()) : RefreshIndicator(onRefresh: _load, child: body)),
      ]),
    );
  }
}

class InfluencerDealPage extends StatefulWidget {
  const InfluencerDealPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<InfluencerDealPage> createState() => _InfluencerDealPageState();
}

class _InfluencerDealPageState extends State<InfluencerDealPage> {
  Map<String, dynamic>? _d;
  bool _busy = false;
  Map<String, dynamic> _card = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/influencer/deals/${widget.ref}'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    if (r != null && _m(r['card']).isNotEmpty) setState(() => _card = _m(r['card']));
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  String get _base => '/api/influencer/deals/${widget.ref}';

  Future<void> _post(Map<String, dynamic> p) async {
    final f = await _form(context, '${_s(p['number'])} · ${_s(p['platform_label'])} ${_s(p['fmt_label'])}', const [
      ('caption', 'Caption (#ad on the first line)'), ('script', 'Script (video / podcast)'), ('duration_s', 'Video length (seconds)'),
      ('due', 'Date (DD-MM-YYYY)'), ('brand_notes', 'Brand feedback'),
    ], ok: 'Save', initial: {'caption': _s(p['caption']), 'script': _s(p['script']), 'duration_s': _s(p['duration_s']), 'due': _s(p['due']),
      'brand_notes': _s(p['brand_notes'])});
    if (f == null) return;
    await _run('PATCH', '/api/influencer/posts/${_s(p['number'])}', {...f, if (f['duration_s'] != null) 'duration_s': _n(f['duration_s'])});
  }

  Widget _postTile(Map<String, dynamic> p) {
    final chk = _m(p['check']);
    final ticks = _m(p['ticks']);
    final n = _s(p['number']);
    return Glass(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('$n · ${_s(p['platform_label'])} ${_s(p['fmt_label'])} · ${_s(p['due']).isEmpty ? 'date?' : _s(p['due'])}',
              style: const TextStyle(fontWeight: FontWeight.w700))),
          Pill(_s(p['status_label']), fg: p['status'] == 'live' ? C.ok : C.chip),
        ]),
        if (_s(p['caption']).isNotEmpty) Text('“${_s(p['caption'])}”', style: const TextStyle(fontSize: 12.5)),
        if (chk.isNotEmpty) _checkBox(chk),
        for (final c in _list(chk['checklist']))
          CheckboxListTile(
            dense: true, contentPadding: EdgeInsets.zero, value: ticks[_s(c['key'])] == true,
            title: Text(_s(c['text']), style: const TextStyle(fontSize: 12)),
            onChanged: _busy ? null : (v) => _run('PATCH', '/api/influencer/posts/$n', {'ticks': {_s(c['key']): v == true}}),
          ),
        if (_m(p['engagement'])['er_pct'] != null)
          Text('Engagement ${_s(_m(p['engagement'])['er_pct'])}% · views ${_s(_m(p['metrics'])['views'] ?? 0)}',
              style: const TextStyle(fontSize: 12, color: C.muted)),
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: 'Caption / script', icon: Icons.edit_rounded, height: 38, onTap: _busy ? null : () => _post(p)),
          if (_s(p['caption']).isNotEmpty && p['status'] != 'live')
            GlassButton(label: 'Send to brand', icon: Icons.outbox_rounded, height: 38, onTap: _busy ? null : () => _run('POST', '/api/influencer/posts/$n/content')),
          if (p['status'] == 'with_brand')
            GlassButton(label: 'Brand said yes', icon: Icons.thumb_up_rounded, height: 38,
                onTap: _busy ? null : () => _run('PATCH', '/api/influencer/posts/$n', {'brand_ok': true})),
          if (p['brand_ok'] == true && p['status'] != 'live')
            GlassButton(label: 'To the creator: post it', icon: Icons.rocket_launch_rounded, height: 38,
                onTap: _busy ? null : () => _run('POST', '/api/influencer/posts/$n/golive')),
          if (p['status'] != 'live')
            GlassButton(label: 'Live link', icon: Icons.link_rounded, height: 38, onTap: _busy ? null : () async {
              final f = await _form(context, 'Link to the live post', const [('live_url', 'https://...')], ok: 'Save');
              if (f == null) return;
              await _run('PATCH', '/api/influencer/posts/$n', f);
            }),
          if (p['status'] == 'live')
            GlassButton(label: 'Numbers', icon: Icons.insights_rounded, height: 38, onTap: _busy ? null : () async {
              final f = await _form(context, 'From platform analytics', const [('views', 'Views'), ('reach', 'Reach'), ('likes', 'Likes'),
                ('comments', 'Comments'), ('shares', 'Shares'), ('saves', 'Saves'), ('clicks', 'Link clicks')], ok: 'Save');
              if (f == null) return;
              await _run('POST', '/api/influencer/posts/$n/metrics', f);
            }),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final money = _m(d?['money']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(title: Text(widget.ref), backgroundColor: Colors.transparent, elevation: 0),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(d['brand'])} · ${_s(d['creator'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                  Text('${_s(d['product'])} · ${_s(d['kind_label'])} · ${_s(d['stage_label'])}', style: const TextStyle(color: C.muted)),
                  if (_strs(d['categories']).isNotEmpty) Text('Category: ${_strs(d['categories']).join(', ')}', style: const TextStyle(fontSize: 12)),
                  if (_s(d['excl_category']).isNotEmpty)
                    Text('Exclusivity: ${_s(d['excl_category'])} ${_s(d['excl_from'])} – ${_s(d['excl_to'])}', style: const TextStyle(fontSize: 12)),
                  for (final x in _list(d['deliverables']))
                    Text('• ${_s(x['platform'])} ${_s(x['fmt'])} x${_s(x['qty'])} · ${x['price'] == null ? '[price?]' : _rs(x['price'])} · ${_s(x['due'])}',
                        style: const TextStyle(fontSize: 12.5)),
                  if (_s(d['brief']).isNotEmpty) Text('Brief: ${_s(d['brief'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
                ])),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 6, children: [
                  for (final (k, label, icon) in const [
                    ('pitch', 'Pitch', Icons.send_rounded), ('contract', 'Contract', Icons.article_rounded),
                    ('invoice', 'Invoice', Icons.receipt_long_rounded), ('payout', 'Creator\'s share', Icons.payments_rounded),
                    ('report', 'Report', Icons.bar_chart_rounded),
                  ])
                    GlassButton(label: label, icon: icon, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/$k')),
                  GlassButton(label: 'Stage', icon: Icons.flag_rounded, height: 40, onTap: _busy ? null : () async {
                    final f = await _form(context, 'Stage', const [('stage', 'lead / pitched / negotiating / contracted / live / done / lost'),
                      ('reason', 'Reason (for lost)')], ok: 'Save');
                    if (f == null) return;
                    await _run('POST', '$_base/stage', f);
                  }),
                  GlassButton(label: 'Money received', icon: Icons.account_balance_wallet_rounded, height: 40, onTap: _busy ? null : () async {
                    final f = await _form(context, 'Money from brand', const [('amount', 'How much received (₹)'), ('tds', 'TDS deducted (₹)'),
                      ('ref', 'UTR (last 4)')], ok: 'Record');
                    if (f == null) return;
                    await _run('POST', '$_base/paid', {...f, 'amount': _n(f['amount']), if (f['tds'] != null) 'tds': _n(f['tds'])});
                  }),
                  GlassButton(label: 'Numbers sheet', icon: Icons.table_chart_rounded, height: 40, onTap: _busy ? null : () async {
                    final f = await _form(context, 'Paste Instagram / YouTube export (CSV)', const [('csv', 'CSV text')], ok: 'Add');
                    if (f == null) return;
                    await _run('POST', '$_base/metrics_text', f);
                  }),
                  GlassButton(label: 'Message', icon: Icons.chat_rounded, height: 40, onTap: _busy ? null : () async {
                    final f = await _form(context, 'Message', const [('text', 'What to write'), ('to', 'brand / creator')], ok: 'Make card');
                    if (f == null) return;
                    await _run('POST', '$_base/message', f);
                  }),
                ]),
                if (_card.isNotEmpty) ...[const SizedBox(height: 10), InfluencerCardCard(app: widget.app, data: {'card': _card}, onDone: _load)],
                const SizedBox(height: 12),
                const Caption('ACCOUNTS'),
                Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Fee ${_rs(money['taxable'])} · GST ${_rs(_m(money['gst'])['total_tax'] ?? 0)} · total ${_s(money['total_text'])}'),
                  Text('Received ${_rs(money['received'])} · TDS ${_rs(money['tds_deducted'])} · due ${money['outstanding'] == null ? '?' : _rs(money['outstanding'])}'),
                  Text('Commission ${_s(money['commission_pct'] ?? '?')}% = ${money['commission'] == null ? '?' : _rs(money['commission'])} · creator\'s share'
                      '${money['creator_due'] == null ? '?' : _rs(money['creator_due'])}'),
                  if (_s(d['invoice_no']).isNotEmpty) Text('Invoice ${_s(d['invoice_no'])} · due ${_s(d['due_on'])}'),
                  for (final x in _strs(_m(money['tds'])['lines'])) Text('• $x', style: const TextStyle(fontSize: 11.5, color: C.faint)),
                  if (_s(_m(money['gst'])['note']).isNotEmpty) Text('• ${_s(_m(money['gst'])['note'])}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
                ])),
                const SizedBox(height: 12),
                const Caption('POSTS'),
                for (final p in _list(d['posts'])) _postTile(p),
              ]),
            ),
    );
  }
}

/// influencer_card: everything that waits for HER tap (pitch, contract, content to brand, go-live note to creator, invoice,
/// payout*, report, message). *payout: fingerprint once a phone key is set up (428 -> /challenge -> Native.approveKeySign -> resend).
class InfluencerCardCard extends StatefulWidget {
  const InfluencerCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<InfluencerCardCard> createState() => _InfluencerCardCardState();
}

class _InfluencerCardCardState extends State<InfluencerCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/influencer/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Influencer' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'No fingerprint given, so it was not approved.',
        'key_invalidated' => 'A new fingerprint was added to the phone: re-link this phone in Profile > Fingerprint approval.',
        _ => 'Could not approve with fingerprint (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not?', const [('reason', 'Reason (optional)')], ok: 'No');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/influencer/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/influencer/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          if (_m(m['card']).isNotEmpty) _c = _m(m['card']);
          _draft = _m(m['draft']);
        });
        _snack(context, _s(m['say']));
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
    final c = _c, sh = _m(c['show']);
    final st = _s(c['status']), kind = _s(c['kind']);
    final money = c['money'] == true;
    final amount = _s(sh['amount_text']).isNotEmpty ? _s(sh['amount_text']) : _s(sh['total_text']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'pitch' => Icons.send_rounded, 'contract' => Icons.article_rounded, 'content' => Icons.outbox_rounded,
            'golive' => Icons.rocket_launch_rounded, 'invoice' => Icons.receipt_long_rounded, 'payout' => Icons.payments_rounded,
            'report' => Icons.bar_chart_rounded, _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['deal'])} ${_s(sh['post'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'stale', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(sh['brand'])} · ${_s(sh['creator'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (_s(sh['caption']).isNotEmpty) Text('“${_s(sh['caption'])}”', style: const TextStyle(fontSize: 12.5)),
        if (_s(sh['text']).isNotEmpty) Text(_s(sh['text']), maxLines: 8, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)),
        for (final w in _strs(sh['warn'])) Text('• $w', style: const TextStyle(fontSize: 11.5, color: C.warn)),
        for (final x in _strs(sh['tds_lines'])) Text('• $x', style: const TextStyle(fontSize: 11.5, color: C.faint)),
        if (kind == 'payout') Text('Received from brand ${_rs(sh['received'])} · commission ${_s(sh['commission_pct'] ?? '?')}%', style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Yes (fingerprint)' : 'Yes', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola does not post or message by itself and does not take or give money: you send them.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// influencer_alert / influencer_day: notes (post due tomorrow / late, live post without disclosure, brand approval waiting,
/// invoice overdue, exclusivity ending, morning note).
class InfluencerNoteCard extends StatelessWidget {
  const InfluencerNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final deal = _s(data['deal']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.campaign_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
          if (deal.isNotEmpty)
            TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InfluencerDealPage(app: app, ref: deal))),
              child: Text('Open $deal'),
            ),
        ])),
      ]),
    );
  }
}
