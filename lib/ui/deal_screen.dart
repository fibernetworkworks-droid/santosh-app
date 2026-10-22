import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

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
  'handed_over': C.ok, 'rejected': C.bad, 'cancelled': C.muted, 'expired': C.muted, 'disputed': C.warn, 'closed': C.ok,
};

const _payWord = {
  'due': 'paisa baaki', 'requested': 'payment card gaya', 'claimed': 'bheja (pakka nahi)', 'part_paid': 'kuch mila',
  'paid': 'poora mila', 'khata': 'khata par', 'refund_due': 'wapas dena baaki', 'refunded': 'wapas ho gaya',
};
const _payChoiceWord = {'upi': 'UPI se', 'counter': 'Counter par', 'khata': 'Khata (udhaar)'};
const _reasonWord = {
  'short': 'Kam aaya', 'damaged': 'Toota / kharab', 'wrong': 'Galat cheez', 'expired': 'Expiry nikli', 'price': 'Daam galat',
  'other': 'Kuch aur',
};
const _resolveWord = {'refund': 'Paise wapas', 'credit': 'Khata mein jama', 'replace': 'Badal kar denge', 'reject': 'Nahi maana'};

/// v0.106 Pay from HER UPI app: the server builds the link from the pinned payee; a new / changed UPI ID is shown big
/// and needs her own "sahi hai" tap first. Hoola never sees the PIN.
Future<void> payWithUpi(BuildContext context, Future<Map<String, dynamic>> Function() link,
    Future<Map<String, dynamic>> Function() trust) async {
  try {
    var r = await link();
    final st = _s(r['status']);
    if (st != 'ok') {
      if (!context.mounted) return;
      final changed = st == 'payee_changed';
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(changed ? 'UPI ID badla hai!' : 'Pehli baar is UPI ko'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(r['name']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            Text(_s(r['upi_id']), style: const TextStyle(fontSize: 15)),
            if (r['business_verified'] == true) const Padding(padding: EdgeInsets.only(top: 6), child: Pill('Verified business', fg: C.ok)),
            if (changed) ...[
              const SizedBox(height: 8),
              Text('Pehle: ${_s(r['was'])}', style: const TextStyle(color: C.bad)),
              const SizedBox(height: 6),
              const Text('Dukaan ko phone karke pakka kijiye. Dhokebaaz aksar UPI ID badal dete hain.',
                  style: TextStyle(color: C.bad, fontSize: 12.5)),
            ] else
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text('UPI app mein yahi naam dikhe tabhi PIN daaliye.', style: TextStyle(color: C.muted, fontSize: 12.5)),
              ),
            const SizedBox(height: 8),
            Text('Rakam: ${_inr(r['amount'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
            TextButton(
                onPressed: () => Navigator.of(ctx).pop(true),
                child: Text(changed ? 'Maine pakka kiya, naya UPI sahi hai' : 'Haan, yahi sahi hai')),
          ],
        ),
      );
      if (ok != true) return;
      r = await trust();
    }
    final url = _s(r['url']);
    if (url.isEmpty) throw 'Payment link nahi bana';
    final launched = await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    if (!context.mounted) return;
    _snack(context, launched
        ? 'UPI app mein pay karke yahan "Maine pay kiya" dabaiye (UTR ke saath).'
        : 'Phone mein koi UPI app nahi mila.');
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
  }
}

/// Amount / mode / UTR, for "paisa mila", refunds and khata money.
Future<Map<String, dynamic>?> moneyDialog(BuildContext context, String title,
    {dynamic amount, bool withMode = true, String hint = ''}) async {
  final a = TextEditingController(text: amount == null || _d(amount) <= 0 ? '' : _qty(amount));
  final u = TextEditingController();
  var mode = 'upi';
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, set) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (hint.isNotEmpty) Text(hint, style: const TextStyle(color: C.muted, fontSize: 12.5)),
            TextField(
                controller: a,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Rakam (₹)')),
            if (withMode) ...[
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                for (final e in const {'upi': 'UPI', 'cash': 'Cash', 'bank': 'Bank'}.entries)
                  ChoiceChip(label: Text(e.value), selected: mode == e.key, onSelected: (_) => set(() => mode = e.key)),
              ]),
            ],
            if (mode != 'cash') TextField(controller: u, decoration: const InputDecoration(labelText: 'UTR / reference (optional)')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Theek hai')),
        ],
      ),
    ),
  );
  final out = <String, dynamic>{'amount': double.tryParse(a.text.trim()), 'mode': mode, 'utr': mode == 'cash' ? '' : u.text.trim()};
  a.dispose();
  u.dispose();
  return ok == true ? out : null;
}

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
  String _pay = '';
  bool _collect = false;
  String _collectMode = 'cash';

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

  Future<void> _disputeDialog() async {
    final q = _m(v['quote']);
    final items = _l(q['lines']).where((l) => _d(l['qty']) > 0).toList();
    final picked = <String, double>{};
    var reason = 'short';
    final note = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Kya galat hai?'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final e in _reasonWord.entries)
                  ChoiceChip(label: Text(e.value), selected: reason == e.key, onSelected: (_) => set(() => reason = e.key)),
              ]),
              const SizedBox(height: 8),
              for (final l in items)
                CheckboxListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  value: picked.containsKey(_s(l['item'])),
                  title: Text('${_s(l['item'])} (${_qty(l['qty'])})'),
                  onChanged: (x) => set(() {
                    if (x == true) {
                      picked[_s(l['item'])] = _d(l['qty']);
                    } else {
                      picked.remove(_s(l['item']));
                    }
                  }),
                ),
              TextField(controller: note, minLines: 1, maxLines: 3, decoration: const InputDecoration(hintText: 'Do line mein bataiye')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Shikayat bhejo')),
          ],
        ),
      ),
    );
    final n = note.text.trim();
    note.dispose();
    if (ok != true) return;
    _act('dispute', {
      'reason': reason,
      'note': n,
      'items': [for (final e in picked.entries) {'item': e.key, 'qty': e.value}],
    });
  }

  Future<void> _resolveDialog() async {
    var action = 'refund';
    final a = TextEditingController();
    final note = TextEditingController();
    final dp = _m(v['dispute']);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Shikayat ka jawab'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_reasonWord[_s(dp['reason'])] ?? ''}${_s(dp['note']).isEmpty ? '' : ': "${_s(dp['note'])}"'}',
                  style: const TextStyle(fontSize: 13)),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final e in _resolveWord.entries)
                  ChoiceChip(label: Text(e.value), selected: action == e.key, onSelected: (_) => set(() => action = e.key)),
              ]),
              if (action == 'refund' || action == 'credit')
                TextField(
                    controller: a,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Rakam (₹)')),
              TextField(controller: note, decoration: InputDecoration(labelText: action == 'reject' ? 'Wajah (zaroori)' : 'Note')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
          ],
        ),
      ),
    );
    final body = <String, dynamic>{'resolution': action, 'amount': double.tryParse(a.text.trim()), 'note': note.text.trim()};
    a.dispose();
    note.dispose();
    if (ok == true) _act('resolve', body);
  }

  Widget _money() {
    final p = _m(v['pay']);
    if (p.isEmpty) return const SizedBox.shrink();
    final st = _s(p['status']);
    final pe = _m(p['payee']);
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.account_balance_wallet_rounded, size: 18, color: C.teal),
          const SizedBox(width: 6),
          Expanded(
            child: Text('${_payChoiceWord[_s(p['choice'])] ?? ''} · ${_inr(p['paid'])} mila / ${_inr(p['due'])}',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          ),
          Pill(_payWord[st] ?? st, fg: st == 'paid' || st == 'refunded' ? C.ok : (st == 'khata' ? C.violet : C.warn)),
        ]),
        if (_s(pe['upi_id']).isNotEmpty && _s(p['choice']) == 'upi')
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('UPI: ${_s(pe['upi_id'])} (${_s(pe['name'])})${pe['business_verified'] == true ? ' · verified' : ''}',
                style: const TextStyle(color: C.muted, fontSize: 12)),
          ),
        if (_s(p['due_on']).isNotEmpty) Text('Khata: ${_s(p['due_on'])} tak dena', style: const TextStyle(color: C.muted, fontSize: 12)),
        for (final r in _l(p['receipts']))
          Text(
              'Rasid ${_s(r['receipt'])}: ${_inr(r['amount'])} ${_s(r['mode'])}'
              '${_s(r['utr_tail']).isEmpty ? '' : ' · ref ..${_s(r['utr_tail'])}'} · ${_when(r['at'])}',
              style: const TextStyle(fontSize: 12)),
        if (_d(p['refund_due']) > 0) Text('Wapas: ${_inr(p['refund_due'])} baaki', style: const TextStyle(color: C.warn, fontSize: 12)),
      ]),
    );
  }

  Widget _disputeBox() {
    final dp = _m(v['dispute']);
    final cr = _m(v['cancel_req']);
    if (dp.isEmpty && _s(cr['status']) != 'waiting') return const SizedBox.shrink();
    final ans = _m(dp['answer']);
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
          color: C.panel, borderRadius: BorderRadius.circular(16), border: Border.all(color: C.warn.withOpacity(.5))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (_s(cr['status']) == 'waiting')
          Text('Cancel request: ${_s(cr['reason'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        if (dp.isNotEmpty) ...[
          Text('Shikayat: ${_reasonWord[_s(dp['reason'])] ?? _s(dp['reason'])}',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          if (_l(dp['lines']).isNotEmpty)
            Text(_l(dp['lines']).map((l) => '${_s(l['item'])} (${_qty(l['qty'])})').join(', '), style: const TextStyle(fontSize: 12)),
          if (_s(dp['note']).isNotEmpty) Text('"${_s(dp['note'])}"', style: const TextStyle(fontSize: 12, color: C.muted)),
          if (ans.isNotEmpty)
            Text(
                'Jawab: ${_resolveWord[_s(ans['action'])] ?? ''}${_d(ans['amount']) > 0 ? ' ${_inr(ans['amount'])}' : ''}'
                '${_s(ans['note']).isEmpty ? '' : ' · ${_s(ans['note'])}'}',
                style: const TextStyle(fontSize: 12.5)),
          if (_s(dp['escalated']).isNotEmpty)
            const Text('Jawab nahi maana gaya. Aage: National Consumer Helpline 1915 / e-Daakhil (edaakhil.nic.in).',
                style: TextStyle(fontSize: 11.5, color: C.muted)),
        ],
      ]),
    );
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
      final terms = _m(q['terms']);
      final opts = List<String>.from((terms['pay_options'] as List?) ?? const ['upi', 'counter']);
      final pick = opts.contains(_pay) ? _pay : (opts.contains('upi') ? 'upi' : (opts.isEmpty ? '' : opts.first));
      if (opts.length > 1) {
        add(Wrap(spacing: 6, runSpacing: 6, children: [
          const Padding(padding: EdgeInsets.only(top: 8), child: Text('Paisa: ', style: TextStyle(color: C.muted))),
          for (final o in opts)
            ChoiceChip(
                label: Text((_payChoiceWord[o] ?? o) + (o == 'khata' ? ' · ${_s(_m(terms['khata'])['days'])} din' : '')),
                selected: pick == o,
                onSelected: (_) => setState(() => _pay = o)),
        ]));
      }
      add(GradientButton(
          label: 'Haan, confirm · ${_inr(q['total'])}',
          icon: Icons.check_rounded,
          height: 50,
          onTap: _busy ? null : () => _act('confirm', {'v': q['v'], 'pay': pick})));
    }
    final pay = _m(v['pay']);
    final left = _d(pay['due_left']);
    final reqs = _l(pay['requests']);
    if (buyer && acts.contains('pay')) {
      add(GradientButton(
          label: 'Pay ${_inr(reqs.isEmpty ? left : reqs.last['amount'])} (UPI app)',
          icon: Icons.currency_rupee_rounded,
          height: 50,
          onTap: _busy
              ? null
              : () => payWithUpi(context, () => widget.app.api!.netDealAct(_s(v['id']), 'pay_link'),
                  () => widget.app.api!.netDealAct(_s(v['id']), 'trust_payee'))));
    }
    if (buyer && acts.contains('paid')) {
      add(GlassButton(
          label: 'Maine pay kiya',
          icon: Icons.task_alt_rounded,
          onTap: _busy
              ? null
              : () async {
                  final r = await _ask('UPI se bhej diya?', 'UTR / UPI reference (UPI app ke payment details mein)');
                  if (r != null) _act('paid', {'utr': r.replaceAll(' ', '')});
                }));
    }
    if (buyer && acts.contains('ok')) {
      add(GradientButton(label: 'Haan, sab sahi mila', icon: Icons.thumb_up_alt_rounded, height: 50, onTap: _busy ? null : () => _act('ok')));
    }
    if (buyer && acts.contains('dispute')) {
      add(GlassButton(label: 'Kuch galat hai (shikayat)', icon: Icons.report_problem_rounded, onTap: _busy ? null : _disputeDialog));
    }
    if (buyer && acts.contains('dispute_close')) {
      add(Row(children: [
        Expanded(
            child: GradientButton(
                label: 'Jawab theek hai', icon: Icons.check_rounded, onTap: _busy ? null : () => _act('dispute_close', {'accept': true}))),
        const SizedBox(width: 8),
        Expanded(
            child: GlassButton(
                label: 'Nahi maanti',
                icon: Icons.gavel_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final r = await _ask('Jawab nahi maana?', 'Kya chahiye (dukaan ko dikhega)');
                        if (r != null) _act('dispute_close', {'accept': false, 'note': r});
                      })),
      ]));
    }
    if (!buyer && acts.contains('received')) {
      add(GradientButton(
          label: '${_s(pay['status']) == 'claimed' ? 'Paisa mila?' : 'Paisa mila'} · ${_inr(left)}',
          icon: Icons.savings_rounded,
          height: 50,
          onTap: _busy
              ? null
              : () async {
                  final r = await moneyDialog(context, 'Paisa aa gaya?',
                      amount: left, hint: 'Apne bank / UPI app mein dekh kar hi. Graahak ka "bhej diya" saboot nahi hai.');
                  if (r != null) _act('received', r);
                }));
    }
    if (!buyer && acts.contains('pay_request') && _s(pay['status']) != 'claimed') {
      add(GlassButton(
          label: reqs.isEmpty ? 'Payment card bhejo' : 'Payment card dobara',
          icon: Icons.request_quote_rounded,
          onTap: _busy ? null : () => _act('pay_request')));
    }
    if (!buyer && acts.contains('refund')) {
      add(GlassButton(
          label: 'Refund diya · ${_inr(pay['refund_due'])}',
          icon: Icons.undo_rounded,
          onTap: _busy
              ? null
              : () async {
                  final r = await moneyDialog(context, 'Refund bhej diya?',
                      amount: pay['refund_due'], withMode: false, hint: 'Apne UPI / bank se bhejne ke baad. Hoola paisa nahi bhejta.');
                  if (r != null) _act('refund', r);
                }));
    }
    if (!buyer && acts.contains('resolve')) {
      add(GradientButton(label: 'Shikayat ka jawab', icon: Icons.support_agent_rounded, height: 50, onTap: _busy ? null : _resolveDialog));
    }
    if (!buyer && acts.contains('cancel_yes')) {
      add(Row(children: [
        Expanded(
            child: GlassButton(
                label: 'Cancel maano', icon: Icons.check_rounded, onTap: _busy ? null : () => _act('cancel_answer', {'yes': true}))),
        const SizedBox(width: 8),
        Expanded(
            child: GlassButton(
                label: 'Mana karo',
                icon: Icons.block_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final r = await _ask('Cancel mana?', 'Wajah (graahak ko dikhegi)');
                        if (r != null) _act('cancel_answer', {'yes': false, 'note': r});
                      })),
      ]));
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
    final open = pay.isNotEmpty && _s(pay['status']) != 'khata' && left > 0;
    if (!buyer && acts.contains('handed_over') && open) {
      add(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        CheckboxListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          value: _collect,
          onChanged: (x) => setState(() => _collect = x == true),
          title: Text('Counter par ${_inr(left)} le liya'),
          subtitle: const Text('Paisa pehle: bina iske saamaan nahi diya jaata', style: TextStyle(fontSize: 11.5)),
        ),
        if (_collect)
          Wrap(spacing: 6, children: [
            for (final e in const {'cash': 'Cash', 'upi': 'UPI'}.entries)
              ChoiceChip(label: Text(e.value), selected: _collectMode == e.key, onSelected: (_) => setState(() => _collectMode = e.key)),
          ]),
      ]));
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
            onTap: _busy
                ? null
                : () => _act('handed_over', {
                      'code': _code.text.trim(),
                      if (open && _collect) 'collect': {'mode': _collectMode, 'amount': left},
                    })),
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
        _money(),
        _disputeBox(),
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
  List<Map<String, dynamic>> _picks = [];
  Map<String, dynamic> _rules = {};
  Map<String, dynamic> _khata = {};
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
      final pk = await app.api!.netPicks();
      Map<String, dynamic> kb = {};
      try {
        kb = await app.api!.netKhata();
      } catch (_) {}                                  // an older server has no khata yet
      if (!mounted) return;
      setState(() {
        _buy = b;
        _sell = s;
        _picks = pk;
        _stock = _l(st['stock']);
        _rules = _m(st['rules']);
        _khata = kb;
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
    final ok = await showDialog<String>(
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
          TextButton(onPressed: () => Navigator.of(ctx).pop(''), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop('catalog'), child: const Text('Unki price list')),
          TextButton(onPressed: () => Navigator.of(ctx).pop('send'), child: const Text('Bhejo')),
        ],
      ),
    );
    final t = to.text.trim();
    final list = _parse(items.text);
    final n = note.text.trim();
    to.dispose();
    items.dispose();
    note.dispose();
    if (ok == 'catalog' && t.isNotEmpty) {
      if (!mounted) return;
      final sent = await showModalBottomSheet<bool>(
          context: context,
          isScrollControlled: true,
          backgroundColor: C.bgBottom,
          builder: (_) => CatalogSheet(app: app, to: t, note: n));
      if (sent == true) _load();
      return;
    }
    if (ok != 'send' || t.isEmpty || list.isEmpty) return;
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
    final low = TextEditingController(text: it == null || it['low_at'] == null ? '' : _qty(it['low_at']));
    final subs = TextEditingController(text: ((it?['subs'] as List?) ?? const []).join(', '));
    var gst = it == null ? 0.0 : _d(it['gst_pct']);
    var shown = it == null ? true : it['public'] != false;
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
              TextField(controller: low, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Itna bache to batao (khaali = nahi)')),
              TextField(controller: subs, decoration: const InputDecoration(labelText: 'Khatam ho to badle mein (stock ke item, comma se)')),
              SwitchListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: const Text('Price list mein dikhe'),
                value: shown,
                onChanged: (x) => set(() => shown = x),
              ),
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
      'low_at': low.text.trim().isEmpty ? null : double.tryParse(low.text.trim()),
      'subs': subs.text.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
      'public': shown,
    };
    for (final c in [name, price, qty, unit, aliases, low, subs]) {
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

  Future<void> _importSheet() async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: ['csv', 'xlsx']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    try {
      final r = await app.api!.netStockImport(f.name, f.bytes!);
      if (mounted) _snack(context, _s(r['say']));
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _stockTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Wrap(spacing: 10, runSpacing: 10, children: [
          GlassButton(label: 'Item jodo', icon: Icons.add_rounded, onTap: () => _editItem()),
          GlassButton(label: 'Sheet se daalo', icon: Icons.upload_file_rounded, onTap: _importSheet),
        ]),
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
                        style: TextStyle(fontWeight: FontWeight.w800, color: it['qty'] == null || it['low'] == true ? C.warn : C.ink)),
                    if (it['low'] == true) const Pill('kam hai', fg: C.warn),
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

  Future<void> _khataDo(String action, Map<String, dynamic> body) async {
    try {
      final r = await app.api!.netKhataAct(action, body);
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _openKhata([Map<String, dynamic>? a]) async {
    final to = TextEditingController(text: _s(a?['with']));
    final lim = TextEditingController(text: a == null ? '' : _qty(a['limit']));
    final days = TextEditingController(text: a == null ? '15' : _qty(a['days']));
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(a == null ? 'Khata kholo' : 'Khata badlo'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          if (a == null) TextField(controller: to, decoration: const InputDecoration(labelText: 'Graahak (naam / @Hoola ID)')),
          TextField(controller: lim, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Seema (₹), 0 = band')),
          TextField(controller: days, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Kitne din mein dena')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
        ],
      ),
    );
    final body = {
      'to': a == null ? to.text.trim() : _s(a['peer']),
      'limit': double.tryParse(lim.text.trim()) ?? 0,
      'days': int.tryParse(days.text.trim()) ?? 15,
    };
    for (final c in [to, lim, days]) {
      c.dispose();
    }
    if (ok == true && _s(body['to']).isNotEmpty) _khataDo('open', body);
  }

  Widget _khataRow(Map<String, dynamic> a, bool mine) {
    final bal = _d(a['balance']);
    final peer = _s(a['peer']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(a['with']), style: const TextStyle(fontWeight: FontWeight.w800))),
            Text(_inr(bal), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: bal > 0 ? (mine ? C.accent : C.warn) : C.ok)),
          ]),
          Text(
              [
                if (mine && _d(a['limit']) > 0) 'seema ${_inr(a['limit'])} · ${_qty(a['days'])} din · ${_inr(a['limit_left'])} bacha',
                if (mine && _s(a['status']) == 'paused') 'band',
                if (_s(a['due_on']).isNotEmpty) '${_s(a['due_on'])} tak${a['overdue'] == true ? ' (nikal gaya)' : ''}',
              ].join(' · '),
              style: TextStyle(color: a['overdue'] == true ? C.bad : C.muted, fontSize: 12)),
          for (final e in _l(a['entries']).take(4))
            Text('${_s(e['kind']) == 'debit' ? '+' : '−'}${_inr(e['amount'])} · ${_s(e['ref'])} · ${_when(e['at'])}',
                style: const TextStyle(fontSize: 11.5, color: C.faint)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (mine && bal > 0)
              GlassButton(label: 'Payment card', icon: Icons.request_quote_rounded, onTap: () => _khataDo('request', {'to': peer})),
            if (mine && bal > 0)
              GlassButton(
                  label: 'Paisa mila',
                  icon: Icons.savings_rounded,
                  onTap: () async {
                    final r = await moneyDialog(context, 'Khata ka paisa aaya?',
                        amount: bal, hint: 'Apne bank / UPI / haath mein dekh kar hi.');
                    if (r != null) _khataDo('received', {'to': peer, ...r});
                  }),
            if (mine) GlassButton(label: 'Seema', icon: Icons.tune_rounded, onTap: () => _openKhata(a)),
            if (!mine && bal > 0)
              GradientButton(
                  label: 'Pay (UPI app)',
                  icon: Icons.currency_rupee_rounded,
                  onTap: () => payWithUpi(context, () => app.api!.netKhataAct('pay_link', {'to': peer}),
                      () => app.api!.netKhataAct('trust_payee', {'to': peer}))),
            if (!mine && bal > 0)
              GlassButton(
                  label: 'Maine pay kiya',
                  icon: Icons.task_alt_rounded,
                  onTap: () async {
                    final r = await moneyDialog(context, 'UPI se bhej diya?', withMode: false, amount: bal);
                    if (r != null) _khataDo('paid', {'to': peer, 'utr': r['utr']});
                  }),
          ]),
        ]),
      ),
    );
  }

  Widget _khataTab() {
    final owed = _l(_khata['owed_to_me']);
    final owe = _l(_khata['i_owe']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Mujhe milna hai', style: TextStyle(color: C.muted, fontSize: 12)),
              Text(_inr(_khata['owed_total']), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: C.accent)),
            ]),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Mujhe dena hai', style: TextStyle(color: C.muted, fontSize: 12)),
              Text(_inr(_khata['owe_total']), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: C.warn)),
            ]),
          ),
        ),
      ]),
      const SizedBox(height: 12),
      GlassButton(label: 'Graahak ka khata kholo', icon: Icons.menu_book_rounded, onTap: () => _openKhata()),
      if (_rules['khata'] != true)
        const Padding(
          padding: EdgeInsets.only(top: 6),
          child: Text('Niyam mein "Khata (udhaar)" chalu karne par hi quote mein khata dikhega.', style: TextStyle(color: C.faint, fontSize: 12)),
        ),
      const SizedBox(height: 12),
      if (owed.isNotEmpty) const Text('Mere graahak', style: TextStyle(fontWeight: FontWeight.w800)),
      for (final a in owed) _khataRow(a, true),
      if (owe.isNotEmpty) const Text('Meri dukaanein', style: TextStyle(fontWeight: FontWeight.w800)),
      for (final a in owe) _khataRow(a, false),
      if (owed.isEmpty && owe.isEmpty)
        const Padding(
          padding: EdgeInsets.all(12),
          child: Text('Khata par liya / diya order yahan apne aap likha jaata hai, dono taraf ek jaisa.', style: TextStyle(color: C.muted)),
        ),
    ]);
  }

  Future<void> _editText(String title, String key, String hint) async {
    final c = TextEditingController(text: _s(_rules[key]));
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, decoration: InputDecoration(hintText: hint)),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
        ],
      ),
    );
    final t = c.text.trim();
    c.dispose();
    if (ok == true) _setRule({key: t});
  }

  Widget _moneyRules() => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Paisa', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(_rules['upi_id']).isEmpty ? 'UPI ID abhi nahi' : _s(_rules['upi_id']),
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                Text(
                    '${_s(_rules['payee_name']).isEmpty ? 'Naam nahi' : _s(_rules['payee_name'])}'
                    '${_rules['business_verified'] == true ? ' · verified business' : ''}',
                    style: const TextStyle(color: C.muted, fontSize: 12)),
              ]),
            ),
            TextButton(onPressed: () => _editText('Aapka UPI ID', 'upi_id', 'naam@bank'), child: const Text('UPI')),
            TextButton(onPressed: () => _editText('UPI par naam', 'payee_name', 'Jaise bank mein hai'), child: const Text('Naam')),
          ]),
          const Text('Graahak ke Hoola is UPI ko yaad rakhte hain; badalne par unhe chetavni milti hai.',
              style: TextStyle(color: C.faint, fontSize: 11.5)),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Saamaan se pehle paisa'),
            subtitle: const Text('Paid, khata, ya counter par usi waqt', style: TextStyle(fontSize: 12)),
            value: _s(_rules['pay_before']) != 'none',
            onChanged: (x) => _setRule({'pay_before': x ? 'handover' : 'none'}),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Counter par cash / UPI chalega'),
            value: _rules['counter_ok'] != false,
            onChanged: (x) => _setRule({'counter_ok': x}),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Khata (udhaar)'),
            subtitle: const Text('Sirf un graahakon ko jinka khata aap kholein', style: TextStyle(fontSize: 12)),
            value: _rules['khata'] == true,
            onChanged: (x) => _setRule({'khata': x}),
          ),
          Text('Pakka hone ke baad free cancel: ${_qty(_rules['cancel_minutes'] ?? 30)} min', style: const TextStyle(fontSize: 12.5)),
          Wrap(spacing: 6, children: [
            for (final x in const [0, 30, 120])
              ChoiceChip(label: Text('$x min'), selected: _d(_rules['cancel_minutes'] ?? 30) == x, onSelected: (_) => _setRule({'cancel_minutes': x})),
          ]),
          const SizedBox(height: 6),
          Text('Shikayat ka samay: ${_qty(_rules['dispute_hours'] ?? 48)} ghante', style: const TextStyle(fontSize: 12.5)),
          Wrap(spacing: 6, children: [
            for (final x in const [24, 48, 168])
              ChoiceChip(label: Text('$x ghante'), selected: _d(_rules['dispute_hours'] ?? 48) == x, onSelected: (_) => _setRule({'dispute_hours': x})),
          ]),
        ]),
      );

  Widget _namesField(String label, String key) => TextFormField(
        key: ValueKey('nf$key${(_rules[key] as List?)?.join(',')}'),
        initialValue: ((_rules[key] as List?) ?? const []).join(', '),
        decoration: InputDecoration(labelText: label, isDense: true),
        onFieldSubmitted: (t) => _setRule({key: t.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList()}),
      );

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
          const Text('Price list kise dikhe', style: TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, children: [
            for (final e in const {'off': 'Kisi ko nahi', 'connected': 'Jude logon ko', 'public': 'Sab ko'}.entries)
              ChoiceChip(label: Text(e.value), selected: (_s(_rules['catalog']).isEmpty ? 'connected' : _s(_rules['catalog'])) == e.key,
                  onSelected: (_) => _setRule({'catalog': e.key})),
          ]),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Stock hai ya nahi, yeh bhi dikhe'),
            value: _rules['show_stock'] == true,
            onChanged: (x) => _setRule({'show_stock': x}),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Pack hote hi graahak ko code chala jaaye'),
            subtitle: const Text('Band ho to packing ke baad aapse poochha jaayega', style: TextStyle(fontSize: 12)),
            value: _rules['auto_ready'] != false,
            onChanged: (x) => _setRule({'auto_ready': x}),
          ),
          const SizedBox(height: 6),
          _namesField('Bharose wale graahak (naam / Hoola ID)', 'trusted'),
          const SizedBox(height: 8),
          _namesField('Packing karne wale (khaali = team ke manager + packing wale)', 'packers'),
          if (((_rules['packers_found'] as List?) ?? const []).isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text('Pick list jaayegi: ${((_rules['packers_found'] as List?) ?? const []).join(', ')}',
                  style: const TextStyle(color: C.muted, fontSize: 12)),
            ),
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
      _moneyRules(),
      const SizedBox(height: 12),
      Text(_s(_rules['say']), style: const TextStyle(color: C.faint, fontSize: 12)),
      const SizedBox(height: 6),
      const Text('Yeh niyam aapke Mere Niyam ka hissa hain. Paisa hamesha aapke tap se.', style: TextStyle(color: C.teal, fontSize: 12)),
    ]);
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 6,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Khareed aur bikri'),
            backgroundColor: Colors.transparent,
            bottom: TabBar(isScrollable: true, tabs: [
              Tab(text: 'Khareed${_buy.isEmpty ? '' : ' (${_buy.length})'}'),
              Tab(text: 'Bikri${_sell.isEmpty ? '' : ' (${_sell.length})'}'),
              Tab(text: 'Packing${_picks.isEmpty ? '' : ' (${_picks.length})'}'),
              const Tab(text: 'Stock'),
              const Tab(text: 'Khata'),
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
                      ListView(padding: const EdgeInsets.all(16), children: [
                        if (_picks.isEmpty)
                          const Padding(
                            padding: EdgeInsets.all(20),
                            child: Text('Jahan aap kaam karti / karte hain, wahan ke Hoola se pick list aayegi to yahan dikhegi.',
                                style: TextStyle(color: C.muted)),
                          ),
                        for (final p in _picks)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: PickCard(key: ValueKey('pk${p['id']}${p['status']}'), v: p, app: app, onChanged: _load),
                          ),
                      ]),
                      _stockTab(),
                      _khataTab(),
                      _rulesTab(),
                    ]),
                  ),
          ),
        ),
      );
}


/// v0.105 A pick list on the packer's own Hoola: tick items while packing, "sab pack", "kuch kam hai", and at the
/// counter the customer's code. The code is checked by the shop's Hoola; it is never shown to the packer.
class PickCard extends StatefulWidget {
  const PickCard({super.key, required this.v, required this.app, this.onChanged});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onChanged;
  @override
  State<PickCard> createState() => _PickCardState();
}

class _PickCardState extends State<PickCard> {
  Map<String, dynamic>? _fresh;
  final Set<int> _ticked = {};
  bool _busy = false;
  String _mode = 'cash';
  final _code = TextEditingController();

  Map<String, dynamic> get v => _fresh ?? widget.v;

  @override
  void didUpdateWidget(covariant PickCard old) {
    super.didUpdateWidget(old);
    if (old.v != widget.v) _fresh = null;
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.netPickAct(_s(v['id']), action, body);
      if (mounted) {
        if (r['pick'] is Map) setState(() => _fresh = Map<String, dynamic>.from(r['pick'] as Map));
        _snack(context, _s(r['say']));
      }
      widget.onChanged?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _short() async {
    final lines = _l(v['lines']);
    final ctrls = [for (final l in lines) TextEditingController(text: _qty(l['qty']))];
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kitna mila?'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (var i = 0; i < lines.length; i++)
              TextField(
                controller: ctrls[i],
                keyboardType: TextInputType.number,
                decoration: InputDecoration(labelText: '${_s(lines[i]['item'])} (chahiye ${_qty(lines[i]['qty'])})'),
              ),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Owner ko batao')),
        ],
      ),
    );
    final short = <Map<String, dynamic>>[];
    for (var i = 0; i < lines.length; i++) {
      final got = double.tryParse(ctrls[i].text.trim()) ?? 0;
      if (got < _d(lines[i]['qty'])) short.add({'item': lines[i]['item'], 'qty': got});
    }
    for (final c in ctrls) {
      c.dispose();
    }
    if (ok != true) return;
    if (short.isEmpty) {
      if (mounted) _snack(context, 'Sab poora hai; "Sab pack ho gaya" dabaiye.');
      return;
    }
    _act('short', {'short': short});
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(v['status']);
    final acts = List<String>.from((v['actions'] as List?) ?? const []);
    final lines = _l(v['lines']);
    final word = {
      'new': 'naya', 'packing': 'packing', 'packed': 'pack ho gaya', 'short': 'kam hai', 'ready': 'counter par',
      'handed_over': 'de diya', 'cancelled': 'cancel', 'taken': 'koi aur kar raha',
    }[st] ?? st;
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.inventory_2_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Pick list · ${_s(v['number'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
              Text('${_s(v['business'])} · ${_s(v['customer'])}',
                  style: const TextStyle(color: C.muted, fontSize: 12), maxLines: 1, overflow: TextOverflow.ellipsis),
            ]),
          ),
          Pill(word, fg: st == 'ready' || st == 'handed_over' ? C.ok : (st == 'short' ? C.warn : C.chip)),
        ]),
        if (_s(v['say']).isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(_s(v['say']), style: const TextStyle(fontSize: 13)),
        ],
        const SizedBox(height: 8),
        for (var i = 0; i < lines.length; i++)
          CheckboxListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            value: _ticked.contains(i) || st == 'packed' || st == 'ready' || st == 'handed_over',
            onChanged: acts.contains('packed') ? (x) => setState(() => x == true ? _ticked.add(i) : _ticked.remove(i)) : null,
            title: Text('${_s(lines[i]['item'])} × ${_qty(lines[i]['qty'])} ${_s(lines[i]['unit'])}'.trim(),
                style: const TextStyle(fontSize: 13.5)),
          ),
        if (_s(v['note']).isNotEmpty) Text('Note: ${_s(v['note'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (st == 'ready' && _s(v['place']).isNotEmpty)
          Text('${_s(v['place'])}${_when(v['until']).isEmpty ? '' : ' · ${_when(v['until'])} tak'}',
              style: const TextStyle(color: C.muted, fontSize: 12)),
        const SizedBox(height: 8),
        if (acts.contains('packing') && st == 'new')
          GlassButton(label: 'Packing shuru', icon: Icons.play_arrow_rounded, onTap: _busy ? null : () => _act('packing')),
        if (acts.contains('packed')) ...[
          const SizedBox(height: 8),
          GradientButton(
              label: 'Sab pack ho gaya',
              icon: Icons.check_rounded,
              height: 48,
              onTap: _busy || (_ticked.length < lines.length && lines.length > 1) ? null : () => _act('packed')),
          if (_ticked.length < lines.length && lines.length > 1)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text('Har item par tick lagaiye', style: TextStyle(color: C.faint, fontSize: 11.5)),
            ),
        ],
        if (acts.contains('short'))
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(onPressed: _busy ? null : _short, child: const Text('Kuch kam hai', style: TextStyle(color: C.warn))),
          ),
        if (acts.contains('handover') && _d(v['collect']) > 0)
          Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Pehle ${_inr(v['collect'])} lijiye. Code daalne par yahi rakam jama hogi.',
                  style: const TextStyle(fontWeight: FontWeight.w700, color: C.warn)),
              Wrap(spacing: 6, children: [
                for (final e in const {'cash': 'Cash liya', 'upi': 'UPI aaya'}.entries)
                  ChoiceChip(label: Text(e.value), selected: _mode == e.key, onSelected: (_) => setState(() => _mode = e.key)),
              ]),
            ]),
          ),
        if (acts.contains('handover'))
          Row(children: [
            Expanded(
              child: TextField(
                controller: _code,
                keyboardType: TextInputType.number,
                maxLength: 4,
                decoration: const InputDecoration(labelText: 'Graahak ka code', counterText: ''),
              ),
            ),
            const SizedBox(width: 10),
            GlassButton(
                label: 'Saamaan diya',
                icon: Icons.handshake_rounded,
                onTap: _busy
                    ? null
                    : () => _act('handover', {
                          'code': _code.text.trim(),
                          if (_d(v['collect']) > 0) 'collect': {'mode': _mode, 'amount': _d(v['collect'])},
                        })),
          ]),
      ]),
    );
  }
}

/// v0.105 A seller's price list (asked through her avatar): pick quantities and send it as the list.
class CatalogSheet extends StatefulWidget {
  const CatalogSheet({super.key, required this.app, required this.to, this.note = ''});
  final Santosh app;
  final String to;
  final String note;
  @override
  State<CatalogSheet> createState() => _CatalogSheetState();
}

class _CatalogSheetState extends State<CatalogSheet> {
  List<Map<String, dynamic>> _items = [];
  final Map<int, double> _count = {};
  String _from = '';
  String? _err;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.netDealCatalog(widget.to);
      if (mounted) {
        setState(() {
          _items = _l(r['items']);
          _from = _s(r['from']);
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _send() async {
    final list = [
      for (final e in _count.entries)
        if (e.value > 0) {'item': _items[e.key]['item'], 'qty': e.value, 'unit': _items[e.key]['unit']},
    ];
    if (list.isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.netDealAsk(widget.to, list, note: widget.note);
      if (mounted) {
        _snack(context, _s(r['say']));
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        _snack(context, '$e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final n = _count.values.where((x) => x > 0).length;
    return SafeArea(
      child: SizedBox(
        height: MediaQuery.of(context).size.height * .8,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
            child: Row(children: [
              Expanded(
                child: Text(_from.isEmpty ? 'Price list' : 'Price list · $_from',
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              ),
              IconButton(onPressed: () => Navigator.of(context).pop(false), icon: const Icon(Icons.close_rounded)),
            ]),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text('Daam jaankari ke liye hain; pakka quote unke stock se aayega.', style: TextStyle(color: C.faint, fontSize: 12)),
          ),
          Expanded(
            child: _err != null
                ? Center(child: Padding(padding: const EdgeInsets.all(20), child: Text(_err!, style: const TextStyle(color: C.bad))))
                : _items.isEmpty
                    ? const Center(child: CircularProgressIndicator())
                    : ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final it = _items[i];
                          final q = _count[i] ?? 0;
                          return ListTile(
                            dense: true,
                            title: Text(_s(it['item']), style: const TextStyle(fontWeight: FontWeight.w700)),
                            subtitle: Text('${_inr(it['price'])} / ${_s(it['unit']).isEmpty ? 'unit' : _s(it['unit'])}'
                                '${it['in_stock'] == false ? ' · abhi stock nahi' : ''}'),
                            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                              IconButton(
                                  onPressed: q <= 0 ? null : () => setState(() => _count[i] = q - 1),
                                  icon: const Icon(Icons.remove_circle_outline_rounded)),
                              SizedBox(width: 32, child: Text(_qty(q), textAlign: TextAlign.center)),
                              IconButton(
                                  onPressed: () => setState(() => _count[i] = q + 1),
                                  icon: const Icon(Icons.add_circle_outline_rounded, color: C.accent)),
                            ]),
                          );
                        },
                      ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: GradientButton(
                label: n == 0 ? 'Item chuniye' : '$n item ki list bhejo',
                icon: Icons.send_rounded,
                onTap: n == 0 || _busy ? null : _send),
          ),
        ]),
      ),
    );
  }
}


/// v0.106 A khata notice in chat: a payment card for the khata balance, a claim, a receipt, a due date.
class KhataCard extends StatelessWidget {
  const KhataCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final card = _s(v['card']);
    final peer = _s(v['peer']);
    final buyer = _s(v['side']) == 'buyer';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.menu_book_rounded, color: C.violet),
          const SizedBox(width: 10),
          Expanded(child: Text('Khata · ${_s(v['with'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Text(_inr(v['balance']), style: const TextStyle(fontWeight: FontWeight.w900)),
        ]),
        const SizedBox(height: 6),
        Text(_s(v['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
        const SizedBox(height: 8),
        if (buyer && card == 'pay')
          GradientButton(
              label: 'Pay ${_inr(v['amount'])} (UPI app)',
              icon: Icons.currency_rupee_rounded,
              onTap: () => payWithUpi(context, () => app.api!.netKhataAct('pay_link', {'to': peer}),
                  () => app.api!.netKhataAct('trust_payee', {'to': peer}))),
        if (!buyer && (card == 'money' || card == 'due'))
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DealsScreen(app: app))),
              child: const Text('Khata kholo'),
            ),
          ),
      ]),
    );
  }
}
