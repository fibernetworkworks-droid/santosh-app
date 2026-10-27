import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// v0.116 Hoola Deals phase 6: outside AI agents (A2A 1.0) at her public counter and her own messages to them,
/// Account Aggregator / ABDM consent checks (she decides in the official app), her DigiLocker documents, and an
/// optional ONDC listing sheet for the seller app she chooses. Every send / approval stays her tap.

String _s(dynamic v) => v == null ? '' : '$v';
double _d(dynamic v) => v is num ? v.toDouble() : (double.tryParse('$v') ?? 0);
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Map<String, dynamic> _m(dynamic x) => x is Map ? Map<String, dynamic>.from(x) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic x) =>
    List<Map<String, dynamic>>.from((x as List? ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));

String _inr(dynamic v) {
  final x = _d(v);
  final whole = x.abs().floor();
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
  final paise = ((x.abs() - whole) * 100).round();
  return '${x < 0 ? '-' : ''}₹$s${paise > 0 ? '.${paise.toString().padLeft(2, '0')}' : ''}';
}

Future<T?> _guard<T>(BuildContext context, Future<T> Function() fn) async {
  try {
    return await fn();
  } catch (e) {
    if (context.mounted) _snack(context, '$e'.replaceFirst('Exception: ', ''));
    return null;
  }
}

Widget _say(String t, {Color color = C.muted}) =>
    t.isEmpty ? const SizedBox.shrink() : Padding(padding: const EdgeInsets.only(top: 6), child: Text(t, style: TextStyle(fontSize: 13, height: 1.35, color: color)));

const _verdictColor = {'ok': C.ok, 'check': C.warn, 'avoid': C.bad};
const _verdictWord = {'ok': 'theek', 'check': 'dhyaan se', 'avoid': 'khatra'};

// ------------------------------------------------------------------------------------------------ A2A: outside agent at her counter
class A2ATaskCard extends StatefulWidget {
  const A2ATaskCard({super.key, required this.v, required this.app, this.onChanged});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onChanged;
  @override
  State<A2ATaskCard> createState() => _A2ATaskCardState();
}

class _A2ATaskCardState extends State<A2ATaskCard> {
  Map<String, dynamic>? _fresh;
  bool _busy = false;
  late final TextEditingController _reply;
  final _code = TextEditingController();

  Map<String, dynamic> get t => _fresh ?? _m(widget.v['task'] ?? widget.v);

  @override
  void initState() {
    super.initState();
    _reply = TextEditingController(text: _s(t['reply_draft']));
  }

  Future<void> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    final r = await _guard(context, () => widget.app.api!.a2aTaskAct(_s(t['id']), action, body));
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r != null) _fresh = _m(r['task']);
    });
    if (r != null) {
      _snack(context, _s(r['say']).isEmpty ? 'Ho gaya' : _s(r['say']));
      widget.onChanged?.call();
    }
  }

  Widget _lines(Map<String, dynamic> q) {
    final lines = _l(q['lines']);
    if (lines.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SizedBox(height: 8),
      for (final l in lines)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 2),
          child: Row(children: [
            Expanded(child: Text('${_s(l['item'])} × ${_s(l['qty'])} ${_s(l['unit'])}'.trim(), style: const TextStyle(fontSize: 13))),
            if (_s(l['status']) != 'ok' && _s(l['status']).isNotEmpty) Pill(_s(l['status']), fg: C.warn),
            const SizedBox(width: 6),
            Text(_inr(l['amount']), style: const TextStyle(fontWeight: FontWeight.w700)),
          ]),
        ),
      const Divider(color: C.line),
      Row(children: [
        const Expanded(child: Text('Kul (GST milakar)', style: TextStyle(fontWeight: FontWeight.w800))),
        Text(_inr(q['total']), style: const TextStyle(fontWeight: FontWeight.w900, color: C.accent)),
      ]),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final waiting = _s(t['waiting']);
    final order = _m(t['order']);
    final asked = _m(t['asked']);
    final skill = _s(t['skill']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.smart_toy_rounded, color: C.teal),
          const SizedBox(width: 10),
          Expanded(child: Text('Bahar ka AI agent · ${_s(t['caller'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          const Pill('unverified', fg: C.warn),
        ]),
        _say(_s(widget.v['say']).isNotEmpty && _fresh == null ? _s(widget.v['say']) : _s(t['say_state'])),
        if (skill == 'question' && _s(asked['text']).isNotEmpty) _say('"${_s(asked['text'])}"', color: C.ink),
        if (waiting == 'quote') _lines(_m(t['draft'])),
        if (waiting == 'accept' || (skill == 'order' && waiting.isEmpty && order.isEmpty)) _lines(_m(t['quote'])),
        if (order.isNotEmpty) _say('Order ${_s(order['number'])} · ${_s(order['status'])}' +
            (_s(order['code']).isNotEmpty ? ' · code ${_s(order['code'])}' : ''), color: C.ink),
        const SizedBox(height: 10),
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        if (waiting == 'reply') ...[
          TextField(controller: _reply, minLines: 1, maxLines: 4, decoration: const InputDecoration(hintText: 'Aapka jawab')),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GradientButton(label: 'Bhejo', icon: Icons.send_rounded, onTap: _busy ? null : () => _act('reply', {'text': _reply.text}))),
            const SizedBox(width: 8),
            TextButton(onPressed: _busy ? null : () => _act('reject'), child: const Text('Mana')),
          ]),
        ],
        if (waiting == 'quote')
          Row(children: [
            Expanded(child: GradientButton(label: 'Quote bhejo', icon: Icons.request_quote_rounded, onTap: _busy ? null : () => _act('quote'))),
            const SizedBox(width: 8),
            TextButton(onPressed: _busy ? null : () => _act('reject'), child: const Text('Mana')),
          ]),
        if (waiting == 'accept')
          Row(children: [
            Expanded(child: GradientButton(label: 'Order pakka karo', icon: Icons.check_circle_rounded, onTap: _busy ? null : () => _act('accept'))),
            const SizedBox(width: 8),
            TextButton(onPressed: _busy ? null : () => _act('reject'), child: const Text('Mana')),
          ]),
        if (_s(order['status']) == 'accepted')
          Row(children: [
            Expanded(child: GlassButton(label: 'Taiyaar (code bhejo)', icon: Icons.inventory_2_rounded, onTap: _busy ? null : () => _act('ready'))),
            TextButton(onPressed: _busy ? null : () => _act('cancel'), child: const Text('Cancel')),
          ]),
        if (_s(order['status']) == 'ready')
          Row(children: [
            Expanded(child: TextField(controller: _code, keyboardType: TextInputType.number, decoration: const InputDecoration(hintText: 'Graahak ka code'))),
            const SizedBox(width: 8),
            GlassButton(label: 'De diya', onTap: _busy ? null : () => _act('handed_over', {'code': _code.text.trim()})),
          ]),
        if (skill == 'order') _say('Paise sirf aapke counter par; bahar ke agent ko UPI link nahi jaata.', color: C.faint),
      ]),
    );
  }
}

class A2AOutCard extends StatefulWidget {
  const A2AOutCard({super.key, required this.v, required this.app, this.onChanged});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onChanged;
  @override
  State<A2AOutCard> createState() => _A2AOutCardState();
}

class _A2AOutCardState extends State<A2AOutCard> {
  Map<String, dynamic>? _fresh;
  bool _busy = false;
  Map<String, dynamic> get o => _fresh ?? _m(widget.v['out'] ?? widget.v);

  Future<void> _act(String action) async {
    setState(() => _busy = true);
    final r = await _guard(context, () => widget.app.api!.a2aOutAct(_s(o['id']), action));
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r != null) _fresh = r.containsKey('out') ? _m(r['out']) : r;
    });
    if (r != null) {
      if (_s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      widget.onChanged?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(o['status']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.hub_rounded, color: C.violet),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(o['agent']), style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(o['say_status']).isEmpty ? st : _s(o['say_status'])),
        ]),
        _say('Aap: ${_s(o['text'])}', color: C.ink),
        if (_s(o['reply']).isNotEmpty) _say('Unka jawab (jaankari): ${_s(o['reply'])}'),
        const SizedBox(height: 8),
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        if (st == 'draft')
          Row(children: [
            Expanded(child: GradientButton(label: 'Bhejo', icon: Icons.send_rounded, onTap: _busy ? null : () => _act('send'))),
            TextButton(onPressed: _busy ? null : () => _act('drop'), child: const Text('Hatao')),
          ])
        else if (!st.contains('COMPLETED') && !st.contains('CANCELED') && st != 'failed' && st != 'dropped')
          Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : () => _act('poll'), child: const Text('Dobara dekho'))),
      ]),
    );
  }
}

// ------------------------------------------------------------------------------------------------ reminders / DigiLocker cards
class ConsentReminderCard extends StatelessWidget {
  const ConsentReminderCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final c = _m(v['consent']);
    final rail = _s(v['rail']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(rail == 'aa' ? Icons.account_balance_rounded : Icons.local_hospital_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(rail == 'aa' ? 'AA consent chalu hai' : 'Health records consent chalu hai',
              style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        _say(_s(v['say'])),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(
              child: GlassButton(
                  label: 'Revoke kar diya',
                  icon: Icons.block_rounded,
                  onTap: () async {
                    final r = await _guard(context, () => app.api!.handoffMark(rail, _s(c['id']), 'revoked'));
                    if (r != null && context.mounted) _snack(context, _s(r['say']));
                  })),
          TextButton(
              onPressed: () => Native.openExternal(
                  url: rail == 'aa'
                      ? 'https://play.google.com/store/search?q=account%20aggregator&c=apps'
                      : 'https://play.google.com/store/search?q=ABHA%20app%20NHA&c=apps'),
              child: const Text('App kholo')),
        ]),
      ]),
    );
  }
}

class DigiLockerCard extends StatelessWidget {
  const DigiLockerCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final docs = _l(v['issued']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.folder_special_rounded, color: C.teal),
          SizedBox(width: 10),
          Expanded(child: Text('DigiLocker', style: TextStyle(fontWeight: FontWeight.w800))),
        ]),
        _say(_s(v['say'])),
        if (_s(v['url']).isNotEmpty) ...[
          const SizedBox(height: 8),
          GradientButton(label: 'DigiLocker kholo', icon: Icons.open_in_new_rounded, onTap: () => Native.openExternal(url: _s(v['url']))),
        ],
        for (final d in docs.take(6)) _DocRow(d: d, app: app),
      ]),
    );
  }
}

class _DocRow extends StatelessWidget {
  const _DocRow({required this.d, required this.app});
  final Map<String, dynamic> d;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Row(children: [
          Expanded(child: Text('${_s(d['name'])} · ${_s(d['issuer'])}', style: const TextStyle(fontSize: 13))),
          if (d['is_id'] == true) const Pill('ID', fg: C.warn),
          if (d['aadhaar'] == true)
            const Padding(padding: EdgeInsets.only(left: 6), child: Text('DigiLocker mein hi', style: TextStyle(fontSize: 11, color: C.faint)))
          else
            TextButton(
                onPressed: () async {
                  final r = await _guard(context, () => app.api!.digilockerFetch(_s(d['uri'])));
                  if (r != null && context.mounted) _snack(context, _s(r['say']));
                },
                child: const Text('File banao')),
        ]),
      );
}

// ------------------------------------------------------------------------------------------------ the screen
class HandoffScreen extends StatefulWidget {
  const HandoffScreen({super.key, required this.app, this.tab = 0});
  final Santosh app;
  final int tab;
  @override
  State<HandoffScreen> createState() => _HandoffScreenState();
}

class _HandoffScreenState extends State<HandoffScreen> {
  Map<String, dynamic> _h = {};
  Map<String, dynamic> _a2a = {};
  Map<String, dynamic> _ondc = {};
  bool _loading = true;
  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final h = await app.api!.handoff();
      final a = await app.api!.a2aHome();
      final o = await app.api!.ondc();
      if (!mounted) return;
      setState(() {
        _h = h;
        _a2a = a;
        _ondc = o;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 5,
        initialIndex: widget.tab,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Consent, kaagaz, bahar ke agents'),
            backgroundColor: Colors.transparent,
            bottom: const TabBar(isScrollable: true, tabs: [
              Tab(text: 'Bank data (AA)'),
              Tab(text: 'Health (ABHA)'),
              Tab(text: 'DigiLocker'),
              Tab(text: 'ONDC'),
              Tab(text: 'Bahar ke agents'),
            ]),
          ),
          body: Aurora(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(children: [
                    _list([_aaIntro(), for (final c in _l(_h['aa'])) _consent('aa', c), _aaApps()]),
                    _list([_abdmIntro(), for (final c in _l(_h['abdm'])) _consent('abdm', c)]),
                    _list(_dlTab()),
                    _list(_ondcTab()),
                    _list(_a2aTab()),
                  ]),
          ),
        ),
      );

  Widget _list(List<Widget> kids) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          for (final k in kids) Padding(padding: const EdgeInsets.only(bottom: 12), child: k),
        ]),
      );

  // ---------------- AA
  Widget _aaIntro() => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Account Aggregator consent jaancho', style: TextStyle(fontWeight: FontWeight.w800)),
          _say('Loan / card / insurance ke liye bank data ka consent aaya? Jo dikh raha hai yahan daaliye: ${app.aName} bataega kya zyada '
              'maanga gaya. Approve / Reject aap AA app mein hi karengi; ${app.aName} data nahi leta, OTP nahi maangta.'),
          const SizedBox(height: 8),
          GradientButton(label: 'Naya consent jaancho', icon: Icons.fact_check_rounded, onTap: _newAa),
        ]),
      );

  Widget _aaApps() => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('RBI-licensed AA apps', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final a in _l(_h['aa_apps']))
              ActionChip(label: Text(_s(a['name'])), onPressed: () => Native.openExternal(url: _s(a['play']))),
          ]),
        ]),
      );

  Future<void> _newAa() async {
    final req = TextEditingController();
    final months = TextEditingController(text: '12');
    final life = TextEditingController();
    final exp = TextEditingController();
    final aaApp = TextEditingController();
    var forWhat = 'loan';
    var fetch = 'ONETIME';
    var mode = 'VIEW';
    final fis = <String>{'DEPOSIT'};
    const fiOpts = {'DEPOSIT': 'Bank account', 'TERM_DEPOSIT': 'FD', 'RECURRING_DEPOSIT': 'RD', 'MUTUAL_FUNDS': 'Mutual fund',
        'EQUITIES': 'Shares', 'INSURANCE_POLICIES': 'Insurance', 'NPS': 'NPS', 'GSTR1_3B': 'GST returns'};
    const forOpts = {'loan': 'Loan', 'loan_running': 'Chalta loan', 'credit_card': 'Credit card', 'insurance': 'Insurance',
        'wealth': 'Investment', 'budget': 'Budget app', 'tax': 'Tax', 'rent': 'Kiraya / job', 'other': 'Doosra'};
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Consent mein kya likha hai?'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: req, decoration: const InputDecoration(labelText: 'Kaun maang raha hai (bank / NBFC / app)')),
              const SizedBox(height: 8),
              const Text('Kis liye', style: TextStyle(fontSize: 12, color: C.faint)),
              Wrap(spacing: 6, children: [
                for (final e in forOpts.entries) ChoiceChip(label: Text(e.value), selected: forWhat == e.key, onSelected: (_) => set(() => forWhat = e.key)),
              ]),
              const SizedBox(height: 8),
              const Text('Kaunse accounts', style: TextStyle(fontSize: 12, color: C.faint)),
              Wrap(spacing: 6, children: [
                for (final e in fiOpts.entries)
                  FilterChip(label: Text(e.value), selected: fis.contains(e.key), onSelected: (v) => set(() => v ? fis.add(e.key) : fis.remove(e.key))),
              ]),
              TextField(controller: months, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Kitne mahine purana data')),
              Wrap(spacing: 6, children: [
                for (final f in const ['ONETIME', 'PERIODIC'])
                  ChoiceChip(label: Text(f == 'ONETIME' ? 'Ek baar' : 'Baar-baar'), selected: fetch == f, onSelected: (_) => set(() => fetch = f)),
                for (final m in const ['VIEW', 'STORE'])
                  ChoiceChip(label: Text(m == 'VIEW' ? 'Sirf dekhenge' : 'Rakhenge'), selected: mode == m, onSelected: (_) => set(() => mode = m)),
              ]),
              TextField(controller: life, decoration: const InputDecoration(labelText: 'Data kitne din rakhenge (jaise 1 YEAR)')),
              TextField(controller: exp, decoration: const InputDecoration(labelText: 'Consent kab tak (YYYY-MM-DD)')),
              TextField(controller: aaApp, decoration: const InputDecoration(labelText: 'AA app (OneMoney, Finvu...)')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jaancho')),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    final r = await _guard(context, () => app.api!.handoffReview('aa', {
          'requester': req.text, 'for_what': forWhat, 'fi_types': fis.toList(), 'months': double.tryParse(months.text),
          'fetch_type': fetch, 'consent_mode': mode, 'data_life': life.text, 'expiry': exp.text, 'aa_app': aaApp.text}));
    if (r == null || !mounted) return;
    await _showReview(r);
    _load();
  }

  Future<void> _showReview(Map<String, dynamic> r) async {
    final c = _m(r['consent']);
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(children: [
          Expanded(child: Text(_s(r['say']).split('.').first)),
          if (_s(c['verdict']).isNotEmpty) Pill(_verdictWord[_s(c['verdict'])] ?? '', fg: _verdictColor[_s(c['verdict'])] ?? C.muted),
        ]),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(r['plain'])),
            for (final f in _l(c['flags'])) _say('• ${_s(f['say'])}', color: _s(f['level']) == 'avoid' ? C.bad : C.warn),
            const SizedBox(height: 8),
            for (final s in (r['steps'] as List? ?? const [])) _say('→ $s'),
            _say(_s(r['rule_of_thumb']), color: C.faint),
          ]),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Samajh gayi'))],
      ),
    );
  }

  Widget _consent(String rail, Map<String, dynamic> c) {
    final status = _s(c['status']);
    final flags = _l(c['flags']);
    final title = rail == 'aa'
        ? '${_s(c['requester']).isEmpty ? 'AA consent' : _s(c['requester'])} · ${_s(c['for_say'])}'
        : '${_s(c['requester']).isEmpty ? 'Health consent' : _s(c['requester'])} · ${_s(c['purpose_say'])}';
    final what = rail == 'aa'
        ? ((_m(c['terms'])['fi_types'] as List? ?? const []).join(', '))
        : (c['hi_say'] as List? ?? const []).join(', ');
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800))),
          if (rail == 'aa') Pill(_verdictWord[_s(c['verdict'])] ?? '', fg: _verdictColor[_s(c['verdict'])] ?? C.muted),
          const SizedBox(width: 6),
          Pill(status),
        ]),
        if (rail == 'abdm' && _s(c['for_whom']) != 'self') _say('Kiske liye: ${_s(c['for_whom'])}'),
        if (what.isNotEmpty) _say(what),
        for (final f in flags) _say('• ${_s(f['say'])}', color: _s(f['level']) == 'avoid' ? C.bad : C.warn),
        if (_s(c['remind_at']).isNotEmpty) _say('Revoke yaad: ${_s(c['remind_at']).substring(0, 10)}', color: C.faint),
        const SizedBox(height: 6),
        Wrap(spacing: 6, children: [
          if (status == 'reviewed') ...[
            ActionChip(label: const Text('Approve kiya'), onPressed: () => _mark(rail, c, 'approved')),
            ActionChip(label: const Text('Mana kiya'), onPressed: () => _mark(rail, c, rail == 'aa' ? 'rejected' : 'denied')),
          ],
          if (status == 'approved') ActionChip(label: const Text('Revoke kiya'), onPressed: () => _mark(rail, c, 'revoked')),
          ActionChip(
              label: const Text('Hatao'),
              onPressed: () async {
                await _guard(context, () => app.api!.handoffForget(rail, _s(c['id'])));
                _load();
              }),
        ]),
      ]),
    );
  }

  Future<void> _mark(String rail, Map<String, dynamic> c, String status) async {
    final r = await _guard(context, () => app.api!.handoffMark(rail, _s(c['id']), status));
    if (r != null && mounted) _snack(context, _s(r['say']));
    _load();
  }

  // ---------------- ABDM
  Widget _abdmIntro() => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('ABHA / health records', style: TextStyle(fontWeight: FontWeight.w800)),
          _say('Hospital ya doctor ne records maange? Request yahan daaliye; ${app.aName} samjhaega. Approve / Deny aap ABHA app mein karengi. '
              '${app.aName} koi health record nahi dekhta.'),
          const SizedBox(height: 8),
          GradientButton(label: 'Request jaancho', icon: Icons.health_and_safety_rounded, onTap: _newAbdm),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final t in const {'abha': 'ABHA kya hai', 'scan_share': 'Scan & Share', 'link': 'Records jodna', 'consent': 'Consent',
                'family': 'Parivaar', 'privacy': 'Privacy'}.entries)
              ActionChip(label: Text(t.value), onPressed: () => _help(t.key)),
          ]),
        ]),
      );

  Future<void> _help(String topic) async {
    final r = await _guard(context, () => app.api!.abdmHelp(topic));
    if (r == null || !mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final s in (r['steps'] as List? ?? const [])) _say('• $s', color: C.ink),
          _say(_s(r['say']), color: C.faint),
        ]),
        actions: [
          TextButton(onPressed: () => Native.openExternal(url: 'https://abha.abdm.gov.in'), child: const Text('abha.abdm.gov.in')),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Theek')),
        ],
      ),
    );
  }

  Future<void> _newAbdm() async {
    final req = TextEditingController();
    final from = TextEditingController();
    final exp = TextEditingController();
    var purpose = 'CAREMGT';
    var who = 'self';
    final types = <String>{'Prescription', 'DiagnosticReport'};
    const pOpts = {'CAREMGT': 'Ilaaj', 'HPAYMT': 'Bill / claim', 'BTG': 'Emergency', 'PUBHLTH': 'Public health', 'DSRCH': 'Research',
        'PATRQT': 'Maine maanga'};
    const tOpts = {'Prescription': 'Parchi', 'DiagnosticReport': 'Lab report', 'OPConsultation': 'OPD', 'DischargeSummary': 'Discharge',
        'ImmunizationRecord': 'Teeka', 'HealthDocumentRecord': 'Doosre kaagaz', 'WellnessRecord': 'Wellness', 'Invoice': 'Bill'};
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('ABHA app mein kya maanga hai?'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: req, decoration: const InputDecoration(labelText: 'Kaun (hospital / doctor / lab)')),
              Wrap(spacing: 6, children: [
                for (final e in pOpts.entries) ChoiceChip(label: Text(e.value), selected: purpose == e.key, onSelected: (_) => set(() => purpose = e.key)),
              ]),
              Wrap(spacing: 6, children: [
                for (final e in tOpts.entries)
                  FilterChip(label: Text(e.value), selected: types.contains(e.key), onSelected: (v) => set(() => v ? types.add(e.key) : types.remove(e.key))),
              ]),
              TextField(controller: from, decoration: const InputDecoration(labelText: 'Kab se ke records (YYYY-MM-DD)')),
              TextField(controller: exp, decoration: const InputDecoration(labelText: 'Kab tak dekh payenge (YYYY-MM-DD)')),
              Wrap(spacing: 6, children: [
                for (final w in const ['self', 'maa', 'papa', 'pati', 'patni', 'beta', 'beti'])
                  ChoiceChip(label: Text(w == 'self' ? 'Main' : w), selected: who == w, onSelected: (_) => set(() => who = w)),
              ]),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jaancho')),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    final r = await _guard(context, () => app.api!.handoffReview('abdm', {
          'requester': req.text, 'purpose': purpose, 'hi_types': types.toList(), 'data_from': from.text, 'expiry': exp.text,
          'for_whom': who}));
    if (r == null || !mounted) return;
    await _showReview(r);
    _load();
  }

  // ---------------- DigiLocker
  List<Widget> _dlTab() {
    final d = _m(_h['digilocker']);
    final manual = _m(d['manual']);
    return [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Expanded(child: Text('Mere DigiLocker kaagaz', style: TextStyle(fontWeight: FontWeight.w800))),
            Pill(d['connected'] == true ? 'juda hai' : 'juda nahi', fg: d['connected'] == true ? C.ok : C.muted),
          ]),
          _say('Sign in DigiLocker ke apne page par (OTP wahin). Aadhaar file nahi banti; ID documents kisi aur ke avatar ko nahi jaate.'),
          if (_s(d['say']).isNotEmpty) _say(_s(d['say']), color: C.warn),
          const SizedBox(height: 8),
          if (d['configured'] == true)
            GradientButton(
                label: d['connected'] == true ? 'Dobara jodo (list taaza)' : 'DigiLocker jodo',
                icon: Icons.link_rounded,
                onTap: () async {
                  final r = await _guard(context, () => app.api!.digilockerStart());
                  if (r != null && _s(r['url']).isNotEmpty) {
                    await Native.openExternal(url: _s(r['url']));
                    if (mounted) _snack(context, _s(r['say']));
                  }
                }),
          if (d['configured'] != true) ...[
            for (final s in (manual['steps'] as List? ?? const [])) _say('• $s', color: C.ink),
            const SizedBox(height: 6),
            GlassButton(
                label: 'DigiLocker app kholo',
                icon: Icons.open_in_new_rounded,
                onTap: () => Native.openExternal(package: 'com.digilocker.android', url: _s(_m(manual['app'])['play']))),
          ],
          if (d['connected'] == true)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                  onPressed: () async {
                    await _guard(context, () => app.api!.digilockerOff());
                    _load();
                  },
                  child: const Text('Judaav hatao')),
            ),
        ]),
      ),
      if (_l(d['issued']).isNotEmpty)
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Issued documents', style: TextStyle(fontWeight: FontWeight.w800)),
            for (final doc in _l(d['issued'])) _DocRow(d: doc, app: app),
          ]),
        ),
      if (_l(d['pulled']).isNotEmpty)
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Files banayi', style: TextStyle(fontWeight: FontWeight.w800)),
            for (final p in _l(d['pulled']))
              _say('${_s(p['name'])}${p['hmac_ok'] == true ? ' · DigiLocker jaanch ✓' : ''}${p['is_id'] == true ? ' · ID (sirf aapke liye)' : ''}',
                  color: C.ink),
          ]),
        ),
    ];
  }

  // ---------------- ONDC
  List<Widget> _ondcTab() {
    final l = _m(_ondc['listing']);
    final domains = _m(_ondc['domains']);
    return [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Expanded(child: Text('ONDC par bechna (optional)', style: TextStyle(fontWeight: FontWeight.w800))),
            Switch(
                value: l['on'] == true,
                onChanged: (v) async {
                  await _guard(context, () => app.api!.ondcSetup({'on': v}));
                  _load();
                }),
          ]),
          _say('ONDC par dukaan ek registered seller app ke through lagti hai (woh orders aur paise sambhalte hain). '
              '${app.aName} aapke stock se unke liye sheet banata hai aur kami bataata hai; ONDC se khud nahi judta.'),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final e in domains.entries)
              ChoiceChip(
                  label: Text(_s(e.value).split(' (').first),
                  selected: _s(l['domain']) == e.key,
                  onSelected: (_) async {
                    await _guard(context, () => app.api!.ondcSetup({'domain': e.key}));
                    _load();
                  }),
          ]),
          const SizedBox(height: 8),
          GlassButton(label: 'Dukaan ki jaankari', icon: Icons.edit_rounded, onTap: () => _ondcEdit(l)),
        ]),
      ),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Expanded(child: Text('Taiyaari', style: TextStyle(fontWeight: FontWeight.w800))),
            Pill(_ondc['ready'] == true ? 'taiyaar' : 'adhoori', fg: _ondc['ready'] == true ? C.ok : C.warn),
          ]),
          for (final b in (_ondc['blockers'] as List? ?? const [])) _say('✗ $b', color: C.bad),
          for (final w in (_ondc['warnings'] as List? ?? const [])) _say('! $w', color: C.warn),
          for (final g in _l(_ondc['item_gaps']).take(12)) _say('${_s(g['item'])}: ${(g['missing'] as List? ?? const []).join(', ')}'),
          const SizedBox(height: 8),
          GradientButton(
              label: 'Seller app ke liye sheet nikaalo',
              icon: Icons.table_view_rounded,
              onTap: () async {
                final r = await _guard(context, () => app.api!.ondcExport());
                if (r != null && mounted) _snack(context, _s(r['say']));
                _load();
              }),
          for (final h in (_ondc['how'] as List? ?? const [])) _say('→ $h', color: C.faint),
        ]),
      ),
    ];
  }

  Future<void> _ondcEdit(Map<String, dynamic> l) async {
    final care = _m(l['care']);
    final c = {
      'store_name': TextEditingController(text: _s(l['store_name'])),
      'seller_app': TextEditingController(text: _s(l['seller_app'])),
      'gstin': TextEditingController(text: _s(l['gstin'])),
      'fssai': TextEditingController(text: _s(l['fssai'])),
      'care_name': TextEditingController(text: _s(care['name'])),
      'care_phone': TextEditingController(text: _s(care['phone'])),
      'care_email': TextEditingController(text: _s(care['email'])),
      'pincodes': TextEditingController(text: (l['pincodes'] as List? ?? const []).join(', ')),
      'ship_minutes': TextEditingController(text: _s(l['ship_minutes'])),
    };
    const labels = {'store_name': 'Dukaan ka naam', 'seller_app': 'Seller app (jo aapne chuna)', 'gstin': 'GSTIN', 'fssai': 'FSSAI (khana)',
        'care_name': 'Customer care naam', 'care_phone': 'Customer care phone', 'care_email': 'Customer care email',
        'pincodes': 'Pincodes (comma se)', 'ship_minutes': 'Kitne minute mein bhejengi'};
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('ONDC dukaan'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final e in c.entries) TextField(controller: e.value, decoration: InputDecoration(labelText: labels[e.key])),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    await _guard(context, () => app.api!.ondcSetup({
          'store_name': c['store_name']!.text, 'seller_app': c['seller_app']!.text, 'gstin': c['gstin']!.text,
          'fssai': c['fssai']!.text, 'pincodes': c['pincodes']!.text, 'ship_minutes': int.tryParse(c['ship_minutes']!.text),
          'care': {'name': c['care_name']!.text, 'phone': c['care_phone']!.text, 'email': c['care_email']!.text}}));
    _load();
  }

  // ---------------- outside agents (A2A 1.0)
  List<Widget> _a2aTab() {
    final mode = _s(_a2a['mode']);
    return [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Bahar ke AI agents (A2A 1.0)', style: TextStyle(fontWeight: FontWeight.w800)),
          _say('Doosre platforms ke AI agents sirf aapke public business counter tak aate hain. Har jawab, quote aur order aapke tap se.'),
          const SizedBox(height: 6),
          Wrap(spacing: 6, children: [
            for (final e in const {'off': 'Band', 'questions': 'Sirf sawaal', 'orders': 'Sawaal + order list'}.entries)
              ChoiceChip(
                  label: Text(e.value),
                  selected: mode == e.key,
                  onSelected: (_) async {
                    await _guard(context, () => app.api!.a2aMode(e.key));
                    _load();
                  }),
          ]),
          const SizedBox(height: 6),
          InkWell(
            onTap: () {
              Clipboard.setData(ClipboardData(text: _s(_a2a['card'])));
              _snack(context, 'Agent card ka pata copy hua');
            },
            child: _say('Agent card: ${_s(_a2a['card'])}  (copy)', color: C.faint),
          ),
          const SizedBox(height: 8),
          GlassButton(label: 'Kisi agent ko message', icon: Icons.add_comment_rounded, onTap: _newOut),
        ]),
      ),
      for (final t in _l(_a2a['tasks'])) A2ATaskCard(key: ValueKey('at${t['id']}${t['updated_at']}'), v: {'task': t}, app: app, onChanged: _load),
      for (final o in _l(_a2a['outs'])) A2AOutCard(key: ValueKey('ao${o['id']}${o['updated_at']}'), v: {'out': o}, app: app, onChanged: _load),
    ];
  }

  Future<void> _newOut() async {
    final url = TextEditingController();
    final text = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Bahar ke agent ko'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: url, decoration: const InputDecoration(labelText: 'Unki website / agent card (https://...)')),
          TextField(controller: text, minLines: 2, maxLines: 5, decoration: const InputDecoration(labelText: 'Kya poochhna hai')),
          _say('Phone number, pata, ID ya OTP mat likhiye.', color: C.faint),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Taiyaar karo')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final r = await _guard(context, () => app.api!.a2aOutNew({'url': url.text.trim(), 'text': text.text}));
    if (r != null && mounted) _snack(context, _s(r['say']));
    _load();
  }
}
