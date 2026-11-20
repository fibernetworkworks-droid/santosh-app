// v0.999.60 HOOLA WALLET on the phone (owner: "AI WALLET ... WITH APPROVAL FROM USER -- ORDERING DAILY NEED, BILL
// PAYMENTS, FOOD ORDER" + "ENTIRE WORLD", design claude.ai/artifact/6saoWTun5YqusMghbLzYgn screens 9 + 10, "GO BUILD ALL").
// The phone is where a payment is approved: her unlocked phone, and on a phone linked for fingerprint approvals her
// fingerprint signs THIS payment (Android Keystore, server-checked). Hoola never holds money.
import 'dart:async';

import 'package:flutter/material.dart';

import '../../native.dart';
import '../../state.dart';
import '../hoola_theme.dart';

class HoolaWalletScreen extends StatefulWidget {
  const HoolaWalletScreen({super.key, required this.app});
  final Santosh app;

  @override
  State<HoolaWalletScreen> createState() => _HoolaWalletScreenState();
}

const _catLabel = {
  'groceries': 'Groceries and daily needs', 'food': 'Food orders', 'bills': 'Bills', 'recharge': 'Mobile recharges',
  'shopping': 'Shopping', 'travel': 'Travel',
};
const _catIcon = {
  'groceries': Icons.shopping_basket_outlined, 'food': Icons.restaurant_outlined, 'bills': Icons.receipt_long_outlined,
  'recharge': Icons.phone_android_outlined, 'shopping': Icons.shopping_bag_outlined, 'travel': Icons.flight_outlined,
};
const _stLabel = {
  'waiting': 'Waiting for you', 'approved': 'Approved, paying', 'paid': 'Paid', 'declined': 'You said no', 'stopped': 'Not allowed',
  'expired': 'Expired', 'failed': 'Did not go through', 'refunded': 'Refunded',
};

class _HoolaWalletScreenState extends State<HoolaWalletScreen> with WidgetsBindingObserver {
  Map<String, dynamic>? d;
  String err = '';
  bool busy = false;
  Timer? _poll;
  // setup
  String region = 'IN';
  final monthly = TextEditingController(text: '10000');
  final Set<String> cats = {'groceries', 'food', 'bills', 'recharge'};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
    _poll = Timer.periodic(const Duration(seconds: 8), (_) {
      if (!busy && mounted) _load(quiet: true);
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    monthly.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) _load(quiet: true);
  }

  Future<dynamic> _api(String m, String path, [Object? body]) {
    final api = widget.app.api;
    if (api == null) throw Exception('Sign in to Hoola first');
    return api.call(m, path, body: body);
  }

  Future<void> _load({bool quiet = false}) async {
    try {
      final r = Map<String, dynamic>.from(await _api('GET', '/api/wallet') as Map);
      if (mounted) setState(() { d = r; err = ''; });
    } catch (e) {
      if (mounted && !quiet) setState(() => err = '$e'.replaceFirst('Exception: ', ''));
    }
  }

  void _toast(String m, {bool bad = false}) {
    final c = HoolaColors.of(context);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(m), backgroundColor: bad ? c.bad : c.pill, behavior: SnackBarBehavior.floating));
  }

  Future<void> _do(Future<dynamic> Function() f, [String ok = '']) async {
    if (busy) return;
    setState(() => busy = true);
    try {
      await f();
      if (ok.isNotEmpty) _toast(ok);
      await _load(quiet: true);
    } catch (e) {
      _toast('$e'.replaceFirst('Exception: ', '').replaceFirst(RegExp(r'^ApiException\(\d+\): '), ''), bad: true);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  String _sym() => '${d?['symbol'] ?? '₹'}';
  String _money(num minor) {
    final v = minor / 100;
    final whole = v.truncate();
    final frac = ((v - whole) * 100).round();
    String g;
    if ((d?['region'] ?? 'IN') == 'IN') {
      var s = '$whole';
      var n = s.length > 3 ? s.substring(s.length - 3) : s;
      var rest = s.length > 3 ? s.substring(0, s.length - 3) : '';
      while (rest.isNotEmpty) {
        final cut = rest.length > 2 ? rest.length - 2 : 0;
        n = '${rest.substring(cut)},$n';
        rest = rest.substring(0, cut);
      }
      g = n;
    } else {
      g = whole.toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');
    }
    return '${_sym()} $g${frac == 0 ? '' : '.${frac.toString().padLeft(2, '0')}'}';
  }

  // ------------------------------------------------------------------ approve
  Future<void> _approve(Map p, bool yes) async {
    final api = widget.app.api;
    if (api == null) return;
    if (yes && await Native.isLocked() && !await Native.requestUnlock()) {
      _toast('Unlock your phone to approve a payment.', bad: true);
      return;
    }
    await _do(() => api.walletDecide('${p['id']}', yes),
        yes ? 'Approved. Hoola is placing the order.' : 'Not paid. Hoola is told.');
  }

  void _openPay(Map p) {
    final c = HoolaColors.of(context);
    final items = List<Map>.from((p['items'] as List?) ?? const []);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 22),
          child: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
              Center(child: Container(width: 40, height: 5, decoration: BoxDecoration(color: c.lineStrong, borderRadius: BorderRadius.circular(5)))),
              const SizedBox(height: 14),
              Text('Hoola wants to pay', style: HoolaType.label(c).copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 10),
              Row(children: [
                _tile(c, '${p['category']}', 46),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${p['shop']}', style: HoolaType.hero(c).copyWith(fontSize: 22)),
                  Text('${p['title']}', style: HoolaType.small(c), maxLines: 2, overflow: TextOverflow.ellipsis),
                ])),
                Text('${p['amount_text']}', style: HoolaType.hero(c).copyWith(fontSize: 28)),
              ]),
              const SizedBox(height: 10),
              for (final i in items.take(10))
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 9),
                  decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
                  child: Row(children: [
                    Expanded(child: Text('${i['name']}${(i['qty'] ?? 1) > 1 ? ' × ${i['qty']}' : ''}', style: HoolaType.body(c))),
                    if ((i['amount'] ?? 0) > 0) Text(_money(i['amount'] as num), style: HoolaType.code(c, size: 14)),
                  ]),
                ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(14)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_catLabel[p['category']] ?? p['category']}${(p['shop_host'] ?? '') != '' ? ' · ${p['shop_host']}' : ''}', style: HoolaType.small(c)),
                  if (p['new_shop'] == true) ...[
                    const SizedBox(height: 4),
                    Text('A shop you have not paid before', style: HoolaType.small(c).copyWith(color: c.warn, fontWeight: FontWeight.w600)),
                  ],
                  const SizedBox(height: 4),
                  Text('Inside your limits · ${_left('${p['expires']}')}', style: HoolaType.small(c).copyWith(color: c.ok)),
                ]),
              ),
              const SizedBox(height: 18),
              Center(
                child: Semantics(
                  button: true,
                  label: 'Pay ${p['amount_text']} with fingerprint',
                  child: InkWell(
                    customBorder: const CircleBorder(),
                    onTap: () {
                      Navigator.pop(ctx);
                      _approve(p, true);
                    },
                    child: Container(
                      width: 76, height: 76,
                      decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle, boxShadow: [BoxShadow(color: c.sunk, spreadRadius: 8)]),
                      child: Icon(Icons.fingerprint, size: 38, color: c.onPill),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Center(child: Text('Touch to pay ${p['amount_text']}', style: HoolaType.title(c))),
              const SizedBox(height: 16),
              OutlinedButton(
                style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(46), shape: const StadiumBorder(), side: BorderSide(color: c.lineStrong)),
                onPressed: () {
                  Navigator.pop(ctx);
                  _approve(p, false);
                },
                child: Text("Don't pay", style: HoolaType.button(c)),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  String _left(String iso) {
    final t = DateTime.tryParse(iso);
    if (t == null) return '';
    final m = t.difference(DateTime.now()).inSeconds;
    if (m <= 0) return 'expired';
    return 'expires in ${(m / 60).ceil()} min';
  }

  // ------------------------------------------------------------------ limits
  void _openLimits() {
    final c = HoolaColors.of(context);
    final L = Map<String, dynamic>.from(d!['limits'] as Map);
    final ctl = {for (final k in ['monthly', 'per_buy', 'per_day']) k: TextEditingController(text: '${((L[k] ?? 0) as num) ~/ 100}')};
    final cat = Map<String, dynamic>.from(L['cats'] as Map);
    final catOn = {for (final k in cat.keys) k: (cat[k]['on'] ?? false) as bool};
    final catCtl = {for (final k in cat.keys) k: TextEditingController(text: '${((cat[k]['limit'] ?? 0) as num) ~/ 100}')};
    bool known = L['known_only'] == true;
    int n(TextEditingController t) => (int.tryParse(t.text.replaceAll(RegExp(r'[^\d]'), '')) ?? 0) * 100;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 22),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('Limits and rules', style: HoolaType.display(c)),
              const SizedBox(height: 14),
              for (final e in [('monthly', 'Each month'), ('per_buy', 'One payment'), ('per_day', 'One day')]) ...[
                _field(c, e.$2, ctl[e.$1]!),
                const SizedBox(height: 10),
              ],
              const SizedBox(height: 8),
              Text('What Hoola may pay for', style: HoolaType.title(c)),
              for (final k in cat.keys)
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Row(children: [
                    _tile(c, k, 36),
                    const SizedBox(width: 10),
                    Expanded(child: Text(_catLabel[k] ?? k, style: HoolaType.body(c))),
                    SizedBox(width: 104, child: _field(c, '', catCtl[k]!, enabled: catOn[k]!)),
                    Switch(value: catOn[k]!, onChanged: (v) => set(() => catOn[k] = v)),
                  ]),
                ),
              const SizedBox(height: 10),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: known,
                onChanged: (v) => set(() => known = v),
                title: Text('Only shops I have paid before', style: HoolaType.body(c)),
                subtitle: Text('A new shop is marked on the card.', style: HoolaType.small(c)),
              ),
              Text('Your fingerprint is needed for every payment. Hoola never pays a person, loans, investments, crypto, betting or gift cards.',
                  style: HoolaType.small(c)),
              const SizedBox(height: 16),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, minimumSize: const Size.fromHeight(48), shape: const StadiumBorder()),
                onPressed: () {
                  Navigator.pop(ctx);
                  _do(() => _api('PUT', '/api/wallet/limits', {
                        'monthly': n(ctl['monthly']!), 'per_buy': n(ctl['per_buy']!), 'per_day': n(ctl['per_day']!), 'known_only': known,
                        'cats': {for (final k in cat.keys) k: {'on': catOn[k], 'limit': n(catCtl[k]!)}},
                      }), 'Limits saved.');
                },
                child: Text('Save limits', style: HoolaType.button(c, color: c.onPill)),
              ),
            ]),
          ),
        ),
      )),
    );
  }

  Widget _field(HoolaColors c, String label, TextEditingController t, {bool enabled = true}) => TextField(
        controller: t,
        enabled: enabled,
        keyboardType: TextInputType.number,
        style: HoolaType.code(c, size: 15),
        decoration: InputDecoration(
          labelText: label.isEmpty ? null : label,
          prefixText: '${_sym()} ',
          isDense: true,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );

  void _openAddMoney() {
    final c = HoolaColors.of(context);
    showModalBottomSheet(
      context: context,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Add money', style: HoolaType.display(c)),
            const SizedBox(height: 12),
            Text(
                (d?['partner'] ?? '') != '' && d?['mode'] == 'balance'
                    ? 'Top up from your own UPI app. Money you do not spend can go back to your bank.'
                    : 'A wallet balance must be held by a licensed payment partner in your country (in India, a wallet licensed by the RBI). '
                        'Hoola never holds money itself, and no partner is connected yet.\n\nUntil then, after you approve, Hoola pays from your own '
                        'UPI app or card. Your PIN stays in your UPI app.',
                style: HoolaType.body(c).copyWith(color: c.ink2)),
          ]),
        ),
      ),
    );
  }

  // ------------------------------------------------------------------ building
  Widget _tile(HoolaColors c, String cat, double size) => Container(
        width: size, height: size,
        decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(size * .28)),
        child: Icon(_catIcon[cat] ?? Icons.shopping_basket_outlined, size: size * .46, color: c.ink2),
      );

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: d == null
            ? Center(child: err.isEmpty
                ? Text('Opening your wallet…', style: HoolaType.body(c).copyWith(color: c.ink3))
                : Padding(padding: const EdgeInsets.all(24), child: Text(err, style: HoolaType.body(c), textAlign: TextAlign.center)))
            : d!['exists'] != true
                ? _setup(c)
                : RefreshIndicator(onRefresh: () => _load(), child: _home(c)),
      ),
    );
  }

  Widget _topBar(HoolaColors c) => Row(children: [
        IconButton(tooltip: 'Back', onPressed: () => Navigator.maybePop(context), icon: Icon(Icons.arrow_back, color: c.ink)),
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(HoolaRadius.pill)),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.fingerprint, size: 15, color: c.ink2),
            const SizedBox(width: 5),
            Text('Every payment needs your fingerprint', style: HoolaType.label(c).copyWith(fontWeight: FontWeight.w600)),
          ]),
        ),
        const Spacer(),
        const SizedBox(width: 48),
      ]);

  Widget _setup(HoolaColors c) {
    final regions = Map<String, dynamic>.from((d!['regions'] as Map?) ?? const {});
    return ListView(padding: const EdgeInsets.fromLTRB(18, 8, 18, 28), children: [
      _topBar(c),
      const SizedBox(height: 8),
      Text('Let Hoola pay for the everyday things', style: HoolaType.hero(c)),
      const SizedBox(height: 10),
      Text('Groceries, food orders, bills and recharges. Hoola fills the cart, checks the total, and stops. You approve with your fingerprint, and only then does the money move.',
          style: HoolaType.body(c).copyWith(color: c.ink2)),
      const SizedBox(height: 20),
      DropdownButtonFormField<String>(
        value: region,
        decoration: InputDecoration(labelText: 'Country', border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
        items: [for (final e in regions.entries) DropdownMenuItem(value: e.key, child: Text('${e.value['name']} · ${e.value['symbol']}'))],
        onChanged: (v) => setState(() => region = v ?? 'IN'),
      ),
      const SizedBox(height: 14),
      TextField(
        controller: monthly,
        keyboardType: TextInputType.number,
        style: HoolaType.code(c, size: 15),
        decoration: InputDecoration(labelText: 'Monthly limit', prefixText: '${regions[region]?['symbol'] ?? ''} ',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
      ),
      const SizedBox(height: 16),
      Text('What Hoola may pay for', style: HoolaType.title(c)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final k in _catLabel.keys)
          FilterChip(
            selected: cats.contains(k),
            label: Text(_catLabel[k]!),
            avatar: Icon(_catIcon[k], size: 16),
            onSelected: (v) => setState(() => v ? cats.add(k) : cats.remove(k)),
          ),
      ]),
      const SizedBox(height: 14),
      Text('Hoola pays each time from your own UPI app or card, after your approval. A wallet balance needs a licensed payment partner in your country.',
          style: HoolaType.small(c)),
      const SizedBox(height: 18),
      FilledButton(
        style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, minimumSize: const Size.fromHeight(50), shape: const StadiumBorder()),
        onPressed: busy
            ? null
            : () => _do(() => _api('POST', '/api/wallet/setup', {
                  'region': region, 'mode': 'each',
                  'monthly': (int.tryParse(monthly.text.replaceAll(RegExp(r'[^\d]'), '')) ?? 0) * 100, 'cats': cats.toList(),
                }), 'Hoola Wallet is on.'),
        child: Text('Turn on Hoola Wallet', style: HoolaType.button(c, color: c.onPill)),
      ),
      const SizedBox(height: 12),
      Text('Never allowed: paying a person, loans, investments, crypto, betting or gift cards, or paying because a page or message said so.',
          style: HoolaType.small(c)),
    ]);
  }

  Widget _home(HoolaColors c) {
    final w = d!;
    final sp = Map<String, dynamic>.from((w['spent'] as Map?) ?? const {});
    final L = Map<String, dynamic>.from((w['limits'] as Map?) ?? const {});
    final txt = Map<String, dynamic>.from((w['text'] as Map?) ?? const {});
    final pays = List<Map>.from((w['payments'] as List?) ?? const []);
    final waiting = pays.where((p) => p['status'] == 'waiting').toList();
    final recent = pays.where((p) => p['status'] != 'waiting').take(12).toList();
    final monthlyLim = (L['monthly'] ?? 0) as num;
    final frac = monthlyLim > 0 ? (((sp['month'] ?? 0) as num) / monthlyLim).clamp(0.0, 1.0).toDouble() : 0.0;
    final paused = w['paused'] == true;
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return ListView(padding: const EdgeInsets.fromLTRB(18, 8, 18, 28), children: [
      _topBar(c),
      const SizedBox(height: 6),
      Text('Hoola Wallet', style: HoolaType.hero(c)),
      if (paused) Padding(padding: const EdgeInsets.only(top: 6), child: Text('All spending is paused.', style: HoolaType.body(c).copyWith(color: c.bad, fontWeight: FontWeight.w600))),
      const SizedBox(height: 14),
      Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: c.pill, borderRadius: BorderRadius.circular(HoolaRadius.cardLg)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(w['balance'] != null ? 'Wallet balance' : 'Left to spend this month', style: HoolaType.small(c).copyWith(color: c.onPill.withOpacity(.75))),
          const SizedBox(height: 8),
          Text(w['balance'] != null ? _money(w['balance'] as num) : '${txt['left'] ?? ''}',
              style: HoolaType.hero(c).copyWith(color: c.onPill, fontSize: 38, height: 1)),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(5),
            child: LinearProgressIndicator(value: frac, minHeight: 5, backgroundColor: c.onPill.withOpacity(.2), color: c.onPill),
          ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: Text('${txt['month']} spent of ${txt['monthly']}', style: HoolaType.small(c).copyWith(color: c.onPill.withOpacity(.8)))),
            Text(months[DateTime.now().month - 1], style: HoolaType.small(c).copyWith(color: c.onPill.withOpacity(.8))),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: FilledButton(
                style: FilledButton.styleFrom(backgroundColor: c.onPill, foregroundColor: c.pill, minimumSize: const Size.fromHeight(44), shape: const StadiumBorder()),
                onPressed: _openAddMoney,
                child: Text('Add money', style: HoolaType.button(c, color: c.pill).copyWith(fontSize: 14)),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(44), shape: const StadiumBorder(), side: BorderSide(color: c.onPill.withOpacity(.35))),
                onPressed: _openLimits,
                child: Text('Limits', style: HoolaType.button(c, color: c.onPill).copyWith(fontSize: 14)),
              ),
            ),
          ]),
        ]),
      ),
      const SizedBox(height: 14),
      for (final p in waiting) ...[
        Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
          decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(HoolaRadius.card), border: Border.all(color: c.accent.withOpacity(.25))),
          child: Row(children: [
            _tile(c, '${p['category']}', 38),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${p['shop']} is waiting for you', style: HoolaType.title(c).copyWith(fontSize: 14)),
              Text('${(p['items'] as List?)?.length ?? 0} items · ${p['amount_text']}', style: HoolaType.small(c)),
            ])),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, minimumSize: const Size(0, 40), shape: const StadiumBorder()),
              onPressed: busy ? null : () => _openPay(p),
              child: Text('Review', style: HoolaType.button(c, color: c.onPill).copyWith(fontSize: 13)),
            ),
          ]),
        ),
        const SizedBox(height: 10),
      ],
      const SizedBox(height: 8),
      Text('Recent', style: HoolaType.title(c)),
      const SizedBox(height: 4),
      if (recent.isEmpty)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text('Nothing paid yet. Ask Hoola in the chat: "Order milk, bread and eggs for home".', style: HoolaType.body(c).copyWith(color: c.ink2)),
        ),
      for (final p in recent)
        Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
          child: Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${p['title']}', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600), maxLines: 1, overflow: TextOverflow.ellipsis),
              Text('${p['shop']} · ${_stLabel[p['status']] ?? p['status']}${(p['status'] == 'stopped' || p['status'] == 'failed') && '${p['reason']}'.isNotEmpty ? ' · ${p['reason']}' : ''}',
                  style: HoolaType.small(c).copyWith(color: p['status'] == 'stopped' || p['status'] == 'failed' ? c.bad : c.ink3), maxLines: 2, overflow: TextOverflow.ellipsis),
            ])),
            const SizedBox(width: 10),
            Text('${p['amount_text']}', style: HoolaType.code(c, size: 14)),
          ]),
        ),
      const SizedBox(height: 18),
      OutlinedButton(
        style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(46), shape: const StadiumBorder(), side: BorderSide(color: paused ? c.lineStrong : c.bad.withOpacity(.4))),
        onPressed: busy ? null : () => _do(() => _api('PUT', '/api/wallet/limits', {'paused': !paused}), paused ? 'Spending is on again.' : 'All spending paused.'),
        child: Text(paused ? 'Turn spending back on' : 'Pause all spending', style: HoolaType.button(c, color: paused ? c.ink : c.bad).copyWith(fontSize: 14)),
      ),
    ]);
  }
}
