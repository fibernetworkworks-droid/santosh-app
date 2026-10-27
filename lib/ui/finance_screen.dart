/// Profile > Financial analyst (v0.95): Hoola reads the books and the bank and says where the money stands.
/// Hisaab (P&L, balance sheet, ratios vs bank benchmarks, what stands out; Tally upload), Cash (bank statement upload,
/// in / out, runway, 13-week forecast), Lena-Dena (receivables aging, reminder drafts, MSME 15 / 45-day payables),
/// Loan (EMI, DSCR after the loan, working capital limit, advance tax). Sharing outside waits for her Haan.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';
import 'gst_screen.dart' show rs;

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

String lakh(dynamic v) {
  final n = (v is num) ? v.toDouble() : double.tryParse('$v') ?? 0;
  if (n.abs() >= 1e7) return '₹${(n / 1e7).toStringAsFixed(2)} cr';
  if (n.abs() >= 1e5) return '₹${(n / 1e5).toStringAsFixed(2)} lakh';
  return rs(n);
}

Color _lvl(String l) => switch (l) { 'bad' => C.bad, 'warn' => C.warn, 'good' => C.ok, _ => C.muted };

Future<PlatformFile?> _pick() async {
  final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
  final f = res?.files.single;
  return (f == null || f.bytes == null) ? null : f;
}

class FinanceScreen extends StatelessWidget {
  const FinanceScreen({super.key, required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: const Text('Financial analyst'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Hisaab'),
              Tab(text: 'Cash'),
              Tab(text: 'Lena-Dena'),
              Tab(text: 'Loan / Tax'),
            ]),
          ),
          body: Aurora(child: TabBarView(children: [_BooksTab(app: app), _CashTab(app: app), _OwedTab(app: app), _LoanTab(app: app)])),
        ),
      );
}

// ---------------------------------------------------------------- Hisaab
class _BooksTab extends StatefulWidget {
  const _BooksTab({required this.app});
  final Santosh app;
  @override
  State<_BooksTab> createState() => _BooksTabState();
}

class _BooksTabState extends State<_BooksTab> {
  Map<String, dynamic>? _a;
  String? _err;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final a = await widget.app.api!.finAnalysis();
      if (mounted) setState(() {
        _a = a;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _upload() async {
    final f = await _pick();
    if (f == null) return;
    final now = DateTime.now();
    final fyStart = now.month >= 4 ? now.year : now.year - 1;
    final label = TextEditingController(text: 'FY $fyStart-${(fyStart + 1) % 100} tak');
    final start = TextEditingController(text: '$fyStart-04-01');
    final end = TextEditingController(text: DateTime(now.year, now.month, 0).toIso8601String().substring(0, 10));
    if (!mounted) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Yeh hisaab kis samay ka hai?'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: label, decoration: const InputDecoration(labelText: 'Naam')),
          TextField(controller: start, decoration: const InputDecoration(labelText: 'Shuru (YYYY-MM-DD)')),
          TextField(controller: end, decoration: const InputDecoration(labelText: 'Aakhri din')),
        ]),
        actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Dekho'))],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final a = await widget.app.api!.finBooks(label.text.trim(), start.text.trim(), end.text.trim(), f.name, f.bytes!);
      if (mounted) {
        setState(() => _a = a);
        _snack(context, _s(a['say']));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _report() async {
    try {
      final r = await widget.app.api!.finAct('report', {'snapshot': _s((_a?['snapshot'] as Map?)?['id']), 'conversation_id': widget.app.conversationId ?? ''});
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _share() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Report bahar bhejni hai?'),
        content: const Text('Bank / CA / investor ko yeh hisaab dikhana theek hai?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await widget.app.api!.finAct('share', {'snapshot': _s((_a?['snapshot'] as Map?)?['id']), 'approve': true});
      await Clipboard.setData(ClipboardData(text: _s(r['draft'])));
      if (mounted) _snack(context, '${_s(r['say'])} Note copy ho gaya.');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _kv(String k, dynamic v, {Color? c}) => Padding(
        padding: const EdgeInsets.only(top: 3),
        child: Row(children: [
          Expanded(child: Text(k, style: const TextStyle(color: C.muted, fontSize: 13))),
          Text(lakh(v ?? 0), style: TextStyle(fontWeight: FontWeight.w700, color: c ?? C.ink)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final a = _a;
    final pl = Map<String, dynamic>.from((a?['pl'] as Map?) ?? const {});
    final bs = Map<String, dynamic>.from((a?['bs'] as Map?) ?? const {});
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        GradientButton(label: _busy ? 'Padh raha hoon...' : 'Tally trial balance / P&L daalo', icon: Icons.upload_file_rounded, onTap: _busy ? null : _upload),
        const Padding(
          padding: EdgeInsets.only(top: 6, bottom: 10),
          child: Text('Tally: Display > Trial Balance > Export (Excel). P&L / balance sheet ki photo / PDF chat mein bhi bhej sakti hain.',
              style: TextStyle(color: C.faint, fontSize: 12)),
        ),
        if (a == null && _err != null) Glass(child: Text(_err!, style: const TextStyle(color: C.muted))),
        if (a != null) ...[
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s((a['snapshot'] as Map?)?['label'])}', style: display(16)),
              Text('${_s((a['snapshot'] as Map?)?['start'])} se ${_s((a['snapshot'] as Map?)?['end'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
              const SizedBox(height: 6),
              _kv('Bikri', pl['revenue']),
              _kv('Gross profit', pl['gross_profit'], c: C.ok),
              _kv('Chalane ke kharche', pl['opex']),
              _kv('Depreciation + byaaj', (pl['depreciation'] ?? 0) + (pl['interest'] ?? 0)),
              _kv('Tax se pehle munafa', pl['profit_before_tax'], c: (pl['profit_before_tax'] ?? 0) < 0 ? C.bad : C.accent),
            ]),
          ),
          const SizedBox(height: 10),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Kya dikh raha hai', style: display(15)),
              for (final i in _list(a['insights']))
                Padding(
                  padding: const EdgeInsets.only(top: 5),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(Icons.circle, size: 9, color: _lvl(_s(i['level']))),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_s(i['text']), style: const TextStyle(color: C.chip, fontSize: 13))),
                  ]),
                ),
            ]),
          ),
          const SizedBox(height: 10),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Ratios (bank kya dekhta hai)', style: display(15)),
              for (final r in _list(a['ratios']).where((r) => r['value'] != null))
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Row(children: [
                    Expanded(child: Text(_s(r['label']), style: const TextStyle(color: C.muted, fontSize: 12.5))),
                    Text('${r['value']}', style: TextStyle(fontWeight: FontWeight.w800, color: r['verdict'] == 'weak' ? C.bad : r['verdict'] == 'good' ? C.ok : C.ink)),
                    if (r['benchmark'] != null)
                      Text('  (${r['rule'] == 'min' ? '≥' : '≤'} ${r['benchmark']})', style: const TextStyle(color: C.faint, fontSize: 11.5)),
                  ]),
                ),
            ]),
          ),
          const SizedBox(height: 10),
          Glass(
            child: Column(children: [
              _kv('Lene hain (debtors)', bs['debtors']),
              _kv('Dene hain (creditors)', bs['creditors']),
              _kv('Stock', bs['stock']),
              _kv('Cash + bank', bs['cash_bank']),
              _kv('Loan', bs['loans']),
              _kv('Apna paisa (net worth)', bs['own_funds']),
            ]),
          ),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'MIS report (Excel + PDF)', icon: Icons.summarize_rounded, onTap: _report),
            GlassButton(label: 'Bank / CA ko bhejna', icon: Icons.send_rounded, onTap: _share),
          ]),
        ],
        const SizedBox(height: 10),
        const Text('Yeh hisaab-kitaab ka vishleshan hai, financial salah nahi. Paisa Hoola kabhi nahi bhejta.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Cash
class _CashTab extends StatefulWidget {
  const _CashTab({required this.app});
  final Santosh app;
  @override
  State<_CashTab> createState() => _CashTabState();
}

class _CashTabState extends State<_CashTab> {
  Map<String, dynamic>? _c;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await widget.app.api!.finCash();
      if (mounted) setState(() {
        _c = c;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _upload() async {
    final f = await _pick();
    if (f == null) return;
    try {
      final c = await widget.app.api!.finBank(f.name, f.bytes!);
      if (mounted) {
        setState(() => _c = c);
        _snack(context, _s(c['say']));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final weeks = _list(c?['forecast']);
    final minClose = weeks.isEmpty ? 0.0 : weeks.map((w) => (w['closing'] as num).toDouble()).reduce((a, b) => a < b ? a : b);
    final maxClose = weeks.isEmpty ? 1.0 : weeks.map((w) => (w['closing'] as num).toDouble()).reduce((a, b) => a > b ? a : b);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        GradientButton(label: 'Bank statement daalo (Excel / CSV)', icon: Icons.account_balance_rounded, onTap: _upload),
        const SizedBox(height: 10),
        if (c == null) Glass(child: Text(_err ?? 'Bank statement nahi mila.', style: const TextStyle(color: C.muted))),
        if (c != null) ...[
          Glass(child: Text(_s(c['say']), style: const TextStyle(height: 1.35))),
          const SizedBox(height: 10),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Agle 13 hafte (andaza)', style: display(15)),
              const SizedBox(height: 8),
              SizedBox(
                height: 90,
                child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  for (final w in weeks)
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 2),
                        child: FractionallySizedBox(
                          heightFactor: maxClose == minClose
                              ? 1.0
                              : (0.15 + 0.85 * (((w['closing'] as num).toDouble() - minClose) / (maxClose - minClose))).clamp(0.05, 1.0).toDouble(),
                          child: Container(
                            decoration: BoxDecoration(
                              color: (w['closing'] as num) < 0 ? C.bad : C.accent,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ),
                    ),
                ]),
              ),
              const SizedBox(height: 6),
              Text('Sabse kam: ${lakh((c['lowest_week'] as Map?)?['closing'] ?? 0)} (${_s((c['lowest_week'] as Map?)?['week_from'])} wala hafta)',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ]),
          ),
          const SizedBox(height: 10),
          for (final m in (Map<String, dynamic>.from((c['months'] as Map?) ?? const {})).entries.toList().reversed.take(6))
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Glass(
                padding: const EdgeInsets.all(10),
                child: Row(children: [
                  Expanded(child: Text(m.key, style: const TextStyle(fontWeight: FontWeight.w700))),
                  Text('+${lakh((m.value as Map)['in'])}', style: const TextStyle(color: C.ok)),
                  const SizedBox(width: 10),
                  Text('-${lakh((m.value as Map)['out'])}', style: const TextStyle(color: C.bad)),
                ]),
              ),
            ),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- Lena-Dena
class _OwedTab extends StatefulWidget {
  const _OwedTab({required this.app});
  final Santosh app;
  @override
  State<_OwedTab> createState() => _OwedTabState();
}

class _OwedTabState extends State<_OwedTab> {
  Map<String, dynamic>? _r, _p;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.finAging('receivable');
      final p = await widget.app.api!.finAging('payable');
      if (mounted) setState(() {
        _r = r;
        _p = p;
      });
    } catch (_) {}
  }

  Future<void> _add(String kind) async {
    final party = TextEditingController(), amt = TextEditingController(), bill = TextEditingController(), date = TextEditingController();
    var msme = false;
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, setS) => AlertDialog(
          title: Text(kind == 'receivable' ? 'Kisse lena hai' : 'Kisko dena hai'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: party, decoration: const InputDecoration(labelText: 'Party')),
            TextField(controller: amt, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Rakam')),
            TextField(controller: bill, decoration: const InputDecoration(labelText: 'Bill no')),
            TextField(controller: date, decoration: const InputDecoration(labelText: 'Bill date (YYYY-MM-DD)')),
            if (kind == 'payable')
              CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: msme,
                  onChanged: (v) => setS(() => msme = v ?? false),
                  title: const Text('Supplier micro / small (Udyam) hai')),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
        ),
      ),
    );
    if (ok != true) return;
    try {
      final r = await widget.app.api!.finAddItem({
        'kind': kind,
        'party': party.text.trim(),
        'amount': double.tryParse(amt.text.replaceAll(',', '')),
        'bill': bill.text.trim(),
        'bill_date': date.text.trim(),
        'msme': msme,
      });
      if (mounted) _snack(context, _s(r['say']));
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _reminders() async {
    try {
      final r = await widget.app.api!.finAct('reminders');
      final text = _list(r['drafts']).map((d) => '${_s(d['party'])} (${_s(d['to'])}):\n${_s(d['text'])}').join('\n\n');
      await Clipboard.setData(ClipboardData(text: text));
      if (mounted) _snack(context, '${_s(r['say'])} Copy ho gaye.');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _section(String title, Map<String, dynamic>? a, String kind) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(title, style: display(15))),
            IconButton(onPressed: () => _add(kind), icon: const Icon(Icons.add_circle_outline_rounded, color: C.accent)),
          ]),
          if (a != null) Text(_s(a['say']), style: const TextStyle(color: C.chip, fontSize: 13, height: 1.3)),
          for (final x in _list(a?['items']).take(25))
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(children: [
                Expanded(
                  child: Text('${_s(x['party'])}${_s(x['bill']).isNotEmpty ? ' · ${_s(x['bill'])}' : ''}',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
                Text(rs(x['pending']), style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(width: 8),
                Pill('${x['age']} din',
                    fg: (x['overdue_days'] ?? 0) > 0 || (x['msme_days_left'] ?? 99) < 0 ? C.bad : C.chip,
                    bg: ((x['overdue_days'] ?? 0) > 0 ? C.bad : C.chip).withOpacity(.14)),
              ]),
            ),
          if (kind == 'receivable' && _list(a?['items']).isNotEmpty)
            TextButton.icon(onPressed: _reminders, icon: const Icon(Icons.chat_rounded, size: 18), label: const Text('Yaad dilane ke message')),
        ]),
      );

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
          _section('Lene hain', _r, 'receivable'),
          const SizedBox(height: 10),
          _section('Dene hain', _p, 'payable'),
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text('Micro / small supplier ko 15 din (likhit samjhauta ho to 45 din tak) mein na dene par woh kharcha tax mein nahi ghatta '
                '(Sec 37(2)(g)) aur byaaj 3x bank rate lagta hai.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
        ]),
      );
}

// ---------------------------------------------------------------- Loan / Tax
class _LoanTab extends StatefulWidget {
  const _LoanTab({required this.app});
  final Santosh app;
  @override
  State<_LoanTab> createState() => _LoanTabState();
}

class _LoanTabState extends State<_LoanTab> {
  final _amt = TextEditingController(text: '1000000'), _rate = TextEditingController(text: '11'), _yrs = TextEditingController(text: '5');
  Map<String, dynamic>? _loan, _tax;

  Future<void> _check() async {
    try {
      final r = await widget.app.api!.finLoanCheck(double.tryParse(_amt.text) ?? 0, double.tryParse(_rate.text) ?? 0, double.tryParse(_yrs.text) ?? 0);
      if (mounted) setState(() => _loan = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _advance() async {
    try {
      final r = await widget.app.api!.finAct('advance_tax');
      if (mounted) setState(() => _tax = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Naya loan le sakte hain?', style: display(15)),
            Row(children: [
              Expanded(child: TextField(controller: _amt, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Rakam'))),
              const SizedBox(width: 8),
              SizedBox(width: 70, child: TextField(controller: _rate, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Byaaj %'))),
              const SizedBox(width: 8),
              SizedBox(width: 60, child: TextField(controller: _yrs, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Saal'))),
            ]),
            const SizedBox(height: 10),
            GradientButton(label: 'Hisaab lagao', icon: Icons.calculate_rounded, onTap: _check),
            if (_loan != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_s(_loan!['say']), style: const TextStyle(height: 1.35))),
          ]),
        ),
        const SizedBox(height: 10),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Advance tax', style: display(15)),
            const SizedBox(height: 6),
            GlassButton(label: 'Is saal ka andaza', icon: Icons.event_note_rounded, onTap: _advance),
            if (_tax != null) ...[
              Padding(padding: const EdgeInsets.only(top: 10), child: Text(_s(_tax!['say']), style: const TextStyle(height: 1.35))),
              for (final i in _list((_tax!['plan'] as Map?)?['installments']))
                Text('${_s(i['due'])}: ${i['cumulative_pct']}% = ${rs(i['cumulative'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ],
          ]),
        ),
      ]);
}

/// Chat card after books are read (event `fin_report`) or a money alert (event `fin_alert`).
class FinCard extends StatefulWidget {
  const FinCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<FinCard> createState() => _FinCardState();
}

class _FinCardState extends State<FinCard> {
  Map<String, dynamic>? _a;

  @override
  void initState() {
    super.initState();
    if (_s(widget.v['snapshot']).isNotEmpty) {
      widget.app.api!.finAnalysis(snapshot: _s(widget.v['snapshot'])).then((a) {
        if (mounted) setState(() => _a = a);
      }).catchError((Object _) {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final alert = _s(widget.v['text']);
    final pl = Map<String, dynamic>.from((_a?['pl'] as Map?) ?? const {});
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FinanceScreen(app: widget.app))),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(alert.isNotEmpty ? Icons.notifications_active_rounded : Icons.query_stats_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(alert.isNotEmpty ? 'Paisa: dhyaan dijiye' : 'Hisaab: ${_s(widget.v['label'])}', style: display(15))),
          ]),
          if (alert.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(alert, style: const TextStyle(height: 1.3))),
          if (_a != null) ...[
            const SizedBox(height: 6),
            Text('Bikri ${lakh(pl['revenue'])} · munafa ${lakh(pl['profit_before_tax'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            for (final i in _list(_a!['insights']).take(3))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Icon(Icons.circle, size: 8, color: _lvl(_s(i['level']))),
                  const SizedBox(width: 6),
                  Expanded(child: Text(_s(i['text']), style: const TextStyle(color: C.chip, fontSize: 12.5))),
                ]),
              ),
          ],
        ]),
      ),
    );
  }
}
