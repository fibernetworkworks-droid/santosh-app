import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.107 Hoola Deals phase 4: compare quotes (one code-sorted table), standing orders signed once, offers only from
/// shops she opted in to. Every order still goes only from her tap, or from a standing order she signed herself.

String _s(dynamic v) => v == null ? '' : '$v';
double _d(dynamic v) => v is num ? v.toDouble() : (double.tryParse('$v') ?? 0);
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Map<String, dynamic> _m(dynamic x) => x is Map ? Map<String, dynamic>.from(x) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic x) =>
    List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

String _inr(dynamic v) {
  final x = _d(v);
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
  return '${x < 0 ? '-' : ''}₹$s${paise > 0 ? '.${paise.toString().padLeft(2, '0')}' : ''}';
}

String _qty(dynamic v) {
  final x = _d(v);
  return x == x.roundToDouble() ? '${x.toInt()}' : x.toStringAsFixed(2);
}

/// "Parle-G 10 carton" per line -> {item, qty, unit}.
List<Map<String, dynamic>> parseItemLines(String text) {
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

const tierColor = {'trusted': C.ok, 'known': C.teal, 'stranger': C.muted, 'blocked': C.bad};
const _dayWord = {'mon': 'Som', 'tue': 'Mangal', 'wed': 'Budh', 'thu': 'Guru', 'fri': 'Shukra', 'sat': 'Shani', 'sun': 'Ravi'};

Future<T?> _guard<T>(BuildContext context, Future<T> Function() fn) async {
  try {
    return await fn();
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

// ------------------------------------------------------------------------------------------------ compare
class CompareCard extends StatefulWidget {
  const CompareCard({super.key, required this.v, required this.app, this.onChanged});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onChanged;
  @override
  State<CompareCard> createState() => _CompareCardState();
}

class _CompareCardState extends State<CompareCard> {
  Map<String, dynamic>? _fresh;
  bool _busy = false;
  Map<String, dynamic> get v => _fresh ?? widget.v;

  @override
  void didUpdateWidget(covariant CompareCard old) {
    super.didUpdateWidget(old);
    if (old.v != widget.v) _fresh = null;
  }

  Future<void> _reload() async {
    final r = await _guard(context, () => widget.app.api!.netRfq(_s(v['id'])));
    if (r != null && mounted) setState(() => _fresh = r);
    widget.onChanged?.call();
  }

  Future<void> _take(Map<String, dynamic> row) async {
    final opts = List<String>.from((row['pay_options'] as List?) ?? const []);
    final pay = opts.contains('upi') ? 'upi' : (opts.isEmpty ? '' : opts.first);
    setState(() => _busy = true);
    await _guard(context, () => widget.app.api!.netDealAct(_s(row['deal_id']), 'confirm', {'v': row['v'], 'pay': pay}));
    if (mounted) setState(() => _busy = false);
    await _reload();
  }

  @override
  Widget build(BuildContext context) {
    final rows = _l(v['rows']);
    final st = _s(v['state']);
    final chosen = List<String>.from((v['chosen'] as List?) ?? const []);
    final canTake = st == 'ready' || st == 'open' || (st == 'chosen' && v['split'] == true);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.compare_arrows_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(
              child: Text('Tulna · ${_s(v['title']).isEmpty ? '${_l(v['items']).length} item' : _s(v['title'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800), maxLines: 1, overflow: TextOverflow.ellipsis)),
          Pill({'open': 'intezaar', 'ready': 'chuniye', 'chosen': 'chun liya', 'closed': 'band'}[st] ?? st,
              fg: st == 'ready' ? C.accent : C.muted),
        ]),
        if (_s(v['say']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(_s(v['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
        ],
        if (st == 'open')
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Sabke jawab ya samay poora hone tak quotes rok kar rakhe hain, taaki pehla jawab dekh kar jaldi na ho.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
        const SizedBox(height: 8),
        for (final r in rows)
          Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
                color: C.panel,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: r['best'] == true ? C.accent : C.line)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(r['with']), style: const TextStyle(fontWeight: FontWeight.w700))),
                if (r['quoted'] == true)
                  Text(_inr(r['total']), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: r['best'] == true ? C.accent : C.ink))
                else
                  Text(_s(r['say']), style: const TextStyle(color: C.muted, fontSize: 12)),
              ]),
              Wrap(spacing: 6, runSpacing: 4, children: [
                if (r['best'] == true) const Pill('sabse achha', fg: C.accent),
                if (r['verified'] == true) const Pill('verified', fg: C.ok),
                Pill(_s(r['tier']), fg: tierColor[_s(r['tier'])] ?? C.chip),
                if (_d(r['more_by']) > 0) Pill('${_inr(r['more_by'])} zyada', fg: C.muted),
                if (r['credit_days'] != null) Pill('${_s(r['credit_days'])} din udhaar', fg: C.violet),
                if (r['fill_rate'] != null) Pill('pehle ${(_d(r['fill_rate']) * 100).round()}% diya', fg: C.teal),
              ]),
              if ((r['short'] as List?)?.isNotEmpty == true || (r['missing'] as List?)?.isNotEmpty == true)
                Text(
                    [
                      if ((r['short'] as List?)?.isNotEmpty == true) 'kam: ${(r['short'] as List).join(', ')}',
                      if ((r['missing'] as List?)?.isNotEmpty == true) 'nahi: ${(r['missing'] as List).join(', ')}',
                    ].join(' · '),
                    style: const TextStyle(color: C.warn, fontSize: 12)),
              if (r['quoted'] == true && _s(r['state']) == 'quoted' && canTake && !chosen.contains(_s(r['deal_id'])))
                Align(
                  alignment: Alignment.centerRight,
                  child: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: r['best'] == true
                        ? GradientButton(
                            label: 'Isse lo · ${_inr(r['total'])}', icon: Icons.check_rounded, height: 46, onTap: _busy ? null : () => _take(r))
                        : GlassButton(label: 'Isse lo · ${_inr(r['total'])}', icon: Icons.check_rounded, onTap: _busy ? null : () => _take(r)),
                  ),
                ),
              if (chosen.contains(_s(r['deal_id']))) const Pill('chuna gaya ✓', fg: C.ok),
            ]),
          ),
        if (st != 'closed')
          Wrap(spacing: 8, children: [
            FilterChip(
              label: const Text('Split order (ek se zyada)'),
              selected: v['split'] == true,
              onSelected: (x) async {
                final r = await _guard(context, () => widget.app.api!.netRfqAct(_s(v['id']), 'split', on: x));
                if (r != null && mounted) setState(() => _fresh = r);
              },
            ),
            TextButton(
                onPressed: () async {
                  final r = await _guard(context, () => widget.app.api!.netRfqAct(_s(v['id']), 'close'));
                  if (r != null && mounted) setState(() => _fresh = r);
                  widget.onChanged?.call();
                },
                child: const Text('Baaki ko mana karo', style: TextStyle(color: C.muted))),
          ]),
        const Text('Kisi dukaan ko doosre ka quote nahi dikhta. Order sirf aapke tap se.', style: TextStyle(color: C.faint, fontSize: 11)),
      ]),
    );
  }
}

class CompareTab extends StatefulWidget {
  const CompareTab({super.key, required this.app});
  final Santosh app;
  @override
  State<CompareTab> createState() => _CompareTabState();
}

class _CompareTabState extends State<CompareTab> {
  List<Map<String, dynamic>> _xs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await _guard(context, () => widget.app.api!.netRfqs(all: true));
    if (mounted) {
      setState(() {
        _xs = r ?? [];
        _loading = false;
      });
    }
  }

  Future<void> _new() async {
    final to = TextEditingController();
    final items = TextEditingController();
    final note = TextEditingController();
    var win = 30;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Quotes ki tulna'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: to, decoration: const InputDecoration(labelText: '2-5 dukaan (comma se)', hintText: 'Sharma Traders, @gupta.wholesale')),
              TextField(
                  controller: items,
                  minLines: 3,
                  maxLines: 8,
                  decoration: const InputDecoration(labelText: 'Har line: cheez aur maatra', hintText: 'Parle-G 10 carton')),
              TextField(controller: note, decoration: const InputDecoration(labelText: 'Note')),
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                for (final x in const [15, 30, 60, 120])
                  ChoiceChip(label: Text('$x min'), selected: win == x, onSelected: (_) => set(() => win = x)),
              ]),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
          ],
        ),
      ),
    );
    final body = {
      'to': to.text.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
      'items': parseItemLines(items.text),
      'note': note.text.trim(),
      'window_minutes': win,
    };
    for (final c in [to, items, note]) {
      c.dispose();
    }
    if (ok != true || !mounted) return;
    final r = await _guard(context, () => widget.app.api!.netRfqStart(body));
    if (r != null && mounted) _snack(context, _s(r['say']));
    _load();
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          GlassButton(label: 'Nayi tulna (2-5 dukaan)', icon: Icons.compare_arrows_rounded, onTap: _new),
          const SizedBox(height: 12),
          if (_loading) const Center(child: CircularProgressIndicator()),
          if (!_loading && _xs.isEmpty)
            const Padding(
              padding: EdgeInsets.all(12),
              child: Text('Ek hi list kai dukaanon ko: sabke quote ek table mein, kul daam se sajaa kar.', style: TextStyle(color: C.muted)),
            ),
          for (final x in _xs)
            Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: CompareCard(key: ValueKey('rq${x['id']}${x['state']}'), v: x, app: widget.app, onChanged: _load)),
        ]),
      );
}

// ------------------------------------------------------------------------------------------------ standing orders
class MandateCard extends StatefulWidget {
  const MandateCard({super.key, required this.v, required this.app, this.onChanged});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onChanged;
  @override
  State<MandateCard> createState() => _MandateCardState();
}

class _MandateCardState extends State<MandateCard> {
  Map<String, dynamic>? _fresh;
  bool _busy = false;
  Map<String, dynamic> get v => _fresh ?? widget.v;

  @override
  void didUpdateWidget(covariant MandateCard old) {
    super.didUpdateWidget(old);
    if (old.v != widget.v) _fresh = null;
  }

  Future<void> _act(String a) async {
    setState(() => _busy = true);
    final r = await _guard(context, () => widget.app.api!.netMandateAct(_s(v['id']), a));
    if (mounted) {
      setState(() {
        _busy = false;
        final m = r?['mandate'];
        if (m is Map) _fresh = Map<String, dynamic>.from(m);
      });
      if (r != null && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
    }
    widget.onChanged?.call();
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(v['state']);
    final runs = _l(v['runs']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.event_repeat_rounded, color: C.violet),
          const SizedBox(width: 10),
          Expanded(
              child: Text('Standing order ${_s(v['number'])} · ${_s(v['with'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800), maxLines: 1, overflow: TextOverflow.ellipsis)),
          Pill({'draft': 'aapki haan baaki', 'active': 'chalu', 'paused': 'ruka', 'ended': 'band'}[st] ?? st,
              fg: st == 'active' ? C.ok : (st == 'draft' ? C.warn : C.muted)),
        ]),
        if (_s(v['say']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(_s(v['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
        ],
        const SizedBox(height: 6),
        Text('${_s(v['when'])} · har baar max ${_inr(v['max_total'])} · ${_s(v['until'])} tak',
            style: const TextStyle(fontSize: 12.5)),
        Text('Daam ${_qty(v['tolerance_pct'])}% tak badhe to chalega · ${_qty(v['hold_minutes'])} min rok kar pakka',
            style: const TextStyle(color: C.muted, fontSize: 12)),
        Text(_l(v['items']).map((i) => '${_s(i['item'])} × ${_qty(i['qty'])} ${_s(i['unit'])}'.trim()).join(', '),
            style: const TextStyle(fontSize: 12)),
        if (_s(v['next_say']).isNotEmpty) Text('Agla: ${_s(v['next_say'])}', style: const TextStyle(color: C.teal, fontSize: 12)),
        if (st == 'active' && v['base_set'] != true)
          const Text('Pehla order aapke tap se hoga; uske daam aage ke liye aadhaar banenge.', style: TextStyle(color: C.faint, fontSize: 11.5)),
        for (final r in runs.reversed.take(3))
          Text('• ${_s(r['status'])}${r['total'] == null ? '' : ' ${_inr(r['total'])}'}'
              '${(r['why'] as List?)?.isNotEmpty == true ? ': ${(r['why'] as List).first}' : ''}',
              style: const TextStyle(color: C.faint, fontSize: 11.5)),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (st == 'draft')
            GradientButton(label: 'Haan, chalu karo', icon: Icons.verified_rounded, onTap: _busy ? null : () => _act('sign')),
          if (st == 'paused')
            GradientButton(label: 'Phir chalu karo', icon: Icons.play_arrow_rounded, onTap: _busy ? null : () => _act('resume')),
          if (st == 'active') GlassButton(label: 'Abhi bhejo', icon: Icons.send_rounded, onTap: _busy ? null : () => _act('run')),
          if (st == 'active') GlassButton(label: 'Roko', icon: Icons.pause_rounded, onTap: _busy ? null : () => _act('pause')),
          if (st != 'ended')
            TextButton(onPressed: _busy ? null : () => _act('stop'), child: const Text('Band karo', style: TextStyle(color: C.bad))),
        ]),
      ]),
    );
  }
}

class StandingTab extends StatefulWidget {
  const StandingTab({super.key, required this.app});
  final Santosh app;
  @override
  State<StandingTab> createState() => _StandingTabState();
}

class _StandingTabState extends State<StandingTab> {
  List<Map<String, dynamic>> _xs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await _guard(context, () => widget.app.api!.netMandates());
    if (mounted) {
      setState(() {
        _xs = r ?? [];
        _loading = false;
      });
    }
  }

  Future<void> _new() async {
    final to = TextEditingController();
    final items = TextEditingController();
    final cap = TextEditingController();
    final at = TextEditingController(text: '09:00');
    var until = DateTime.now().add(const Duration(days: 90));
    final days = <String>{'mon'};
    var tol = 5.0;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Naya standing order'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: to, decoration: const InputDecoration(labelText: 'Kis dukaan se')),
              TextField(
                  controller: items,
                  minLines: 3,
                  maxLines: 8,
                  decoration: const InputDecoration(labelText: 'Roz / har hafte ki list', hintText: 'Doodh 20 litre')),
              const SizedBox(height: 8),
              Wrap(spacing: 4, runSpacing: 4, children: [
                for (final e in _dayWord.entries)
                  FilterChip(
                      label: Text(e.value),
                      selected: days.contains(e.key),
                      onSelected: (x) => set(() => x ? days.add(e.key) : days.remove(e.key))),
              ]),
              TextField(controller: at, decoration: const InputDecoration(labelText: 'Samay (HH:MM)')),
              TextField(controller: cap, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Har order max ₹')),
              const SizedBox(height: 8),
              Text('Daam badhne ki chhoot: ${tol.toStringAsFixed(0)}%', style: const TextStyle(fontSize: 12.5)),
              Wrap(spacing: 6, children: [
                for (final x in const [0.0, 3.0, 5.0, 10.0])
                  ChoiceChip(label: Text('${x.toInt()}%'), selected: tol == x, onSelected: (_) => set(() => tol = x)),
              ]),
              TextButton.icon(
                icon: const Icon(Icons.event_rounded),
                label: Text('${until.day}/${until.month}/${until.year} tak'),
                onPressed: () async {
                  final p = await showDatePicker(
                      context: ctx,
                      initialDate: until,
                      firstDate: DateTime.now().add(const Duration(days: 1)),
                      lastDate: DateTime.now().add(const Duration(days: 365)));
                  if (p != null) set(() => until = p);
                },
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Banao')),
          ],
        ),
      ),
    );
    final body = {
      'to': to.text.trim(),
      'items': parseItemLines(items.text),
      'days': days.toList(),
      'at': at.text.trim(),
      'max_total': double.tryParse(cap.text.trim()),
      'until': '${until.year}-${until.month.toString().padLeft(2, '0')}-${until.day.toString().padLeft(2, '0')}',
      'tolerance_pct': tol,
    };
    for (final c in [to, items, cap, at]) {
      c.dispose();
    }
    if (ok != true || !mounted) return;
    final r = await _guard(context, () => widget.app.api!.netMandateCreate(body));
    if (r != null && mounted) _snack(context, _s(r['say']));
    _load();
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          GlassButton(label: 'Naya standing order', icon: Icons.event_repeat_rounded, onTap: _new),
          const SizedBox(height: 6),
          const Text('Ek baar niyam par haan: har baar code daam, maatra aur seema jaanchta hai. Kuch bhi bahar ho to aapse poochhta hai.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 12),
          if (_loading) const Center(child: CircularProgressIndicator()),
          for (final x in _xs)
            Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: MandateCard(key: ValueKey('md${x['id']}${x['state']}'), v: x, app: widget.app, onChanged: _load)),
        ]),
      );
}

// ------------------------------------------------------------------------------------------------ offers
class PromoCard extends StatefulWidget {
  const PromoCard({super.key, required this.v, required this.app, this.onChanged});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onChanged;
  @override
  State<PromoCard> createState() => _PromoCardState();
}

class _PromoCardState extends State<PromoCard> {
  String _done = '';

  Future<void> _do(String what, Future<dynamic> Function() fn) async {
    final r = await _guard(context, fn);
    if (r == null || !mounted) return;
    setState(() => _done = what);
    final say = r is Map ? _s(r['say']) : '';
    if (say.isNotEmpty) _snack(context, say);
    widget.onChanged?.call();
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final peer = _s(v['peer']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.local_offer_rounded, color: C.warn),
          const SizedBox(width: 10),
          Expanded(child: Text('Offer · ${_s(v['with'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          if (v['verified'] == true) const Pill('verified', fg: C.ok),
        ]),
        const SizedBox(height: 6),
        Text(_s(v['title']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        if (_s(v['text']).isNotEmpty) Text(_s(v['text']), style: const TextStyle(fontSize: 13)),
        for (final i in _l(v['items']))
          Text('${_s(i['name'])} · ${_inr(i['price'])}${i['mrp'] != null ? ' (MRP ${_inr(i['mrp'])})' : ''}'
              '${_s(i['unit']).isEmpty ? '' : ' / ${_s(i['unit'])}'}',
              style: const TextStyle(fontSize: 12.5)),
        if (_s(v['valid_until']).length >= 10)
          Text('${_s(v['valid_until']).substring(0, 10)} tak', style: const TextStyle(color: C.faint, fontSize: 11.5)),
        const SizedBox(height: 8),
        if (_done.isNotEmpty)
          Text(_done, style: const TextStyle(color: C.teal, fontSize: 12))
        else
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(
                label: 'List banao',
                icon: Icons.playlist_add_rounded,
                onTap: () => _do('List bhej di', () => widget.app.api!.netPromoItem(_s(v['id']), 'order'))),
            TextButton(
                onPressed: () => _do('Inke offers band', () => widget.app.api!.netPromoAct('optout', {'to': peer})),
                child: const Text('Offers band karo')),
            TextButton(
                onPressed: () => _do('Shikayat darj', () => widget.app.api!.netTrustReport(peer, 'spam', kind: 'promo_offer')),
                child: const Text('Report', style: TextStyle(color: C.bad))),
          ]),
        const Text('Yeh offer aapne maanga tha. Order sirf aapke kehne par.', style: TextStyle(color: C.faint, fontSize: 11)),
      ]),
    );
  }
}

class OffersTab extends StatefulWidget {
  const OffersTab({super.key, required this.app});
  final Santosh app;
  @override
  State<OffersTab> createState() => _OffersTabState();
}

class _OffersTabState extends State<OffersTab> {
  List<Map<String, dynamic>> _inbox = [];
  List<Map<String, dynamic>> _optins = [];
  Map<String, dynamic> _aud = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await _guard(context, () => widget.app.api!.netPromos());
    final a = await _guard(context, () => widget.app.api!.netPromoAudience());
    if (mounted) {
      setState(() {
        _inbox = _l(r?['offers']);
        _optins = _l(r?['opted_in']);
        _aud = a ?? {};
        _loading = false;
      });
    }
  }

  Future<void> _optin() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kis dukaan ke offers chahiye?'),
        content: TextField(controller: c, decoration: const InputDecoration(hintText: 'Naam / @Hoola ID')),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Haan')),
        ],
      ),
    );
    final t = c.text.trim();
    c.dispose();
    if (ok != true || t.isEmpty || !mounted) return;
    final r = await _guard(context, () => widget.app.api!.netPromoAct('optin', {'to': t}));
    if (r != null && mounted) _snack(context, _s(r['say']));
    _load();
  }

  Future<void> _send() async {
    final title = TextEditingController();
    final text = TextEditingController();
    final items = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Offer bhejo'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Title', hintText: 'Diwali offer')),
            TextField(controller: text, minLines: 1, maxLines: 4, decoration: const InputDecoration(labelText: 'Do line')),
            TextField(
                controller: items,
                minLines: 2,
                maxLines: 8,
                decoration: const InputDecoration(labelText: 'Har line: cheez daam [MRP]', hintText: 'Parle-G 430 450')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Aage')),
        ],
      ),
    );
    final its = <Map<String, dynamic>>[];
    for (final raw in items.text.split('\n')) {
      final m = RegExp(r'^(.*?)\s+(\d+(?:\.\d+)?)(?:\s+(\d+(?:\.\d+)?))?\s*$').firstMatch(raw.trim());
      if (m != null) {
        its.add({'name': m.group(1)!.trim(), 'price': double.parse(m.group(2)!), if (m.group(3) != null) 'mrp': double.parse(m.group(3)!)});
      }
    }
    final body = {'title': title.text.trim(), 'text': text.text.trim(), 'items': its, 'valid_days': 7};
    for (final c in [title, text, items]) {
      c.dispose();
    }
    if (ok != true || !mounted) return;
    final pv = await _guard(context, () => widget.app.api!.netPromoAct('preview', body));
    if (pv == null || !mounted) return;
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Bhejein?'),
        content: Text(_s(pv['say'])),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text('Haan, ${_s(pv['to'])} ko bhejo')),
        ],
      ),
    );
    if (go != true || !mounted) return;
    final r = await _guard(context, () => widget.app.api!.netPromoAct('send', body));
    if (r != null && mounted) _snack(context, _s(r['say']));
    _load();
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_loading) const Center(child: CircularProgressIndicator()),
          Wrap(spacing: 10, runSpacing: 10, children: [
            GlassButton(label: 'Dukaan ke offers lo', icon: Icons.notifications_active_rounded, onTap: _optin),
            GlassButton(label: 'Mere graahakon ko offer', icon: Icons.campaign_rounded, onTap: _send),
          ]),
          const SizedBox(height: 6),
          Text('Mere offers ${_s(_aud['on'] ?? 0)} graahakon ne maange hain · hafte mein ek graahak ko 2 tak',
              style: const TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 12),
          for (final o in _optins.where((o) => _s(o['status']) == 'on'))
            Row(children: [
              const Icon(Icons.check_circle_rounded, size: 16, color: C.ok),
              const SizedBox(width: 6),
              Expanded(child: Text(_s(o['with']), style: const TextStyle(fontSize: 13))),
              TextButton(
                  onPressed: () async {
                    await _guard(context, () => widget.app.api!.netPromoAct('optout', {'to': _s(o['peer'])}));
                    _load();
                  },
                  child: const Text('Band')),
            ]),
          const SizedBox(height: 8),
          if (!_loading && _inbox.isEmpty)
            const Text('Sirf un dukaanon ke offers aate hain jinke liye aapne haan kahi. Har offer par "band karo".',
                style: TextStyle(color: C.muted)),
          for (final o in _inbox)
            Padding(padding: const EdgeInsets.only(bottom: 12), child: PromoCard(key: ValueKey('pr${o['id']}'), v: o, app: widget.app, onChanged: _load)),
        ]),
      );
}

/// Trust controls for one connection (deal page): tier + set trusted / known / auto + report.
class TrustChip extends StatelessWidget {
  const TrustChip({super.key, required this.app, required this.peer, required this.tier, required this.say, this.onChanged});
  final Santosh app;
  final String peer;
  final String tier;
  final String say;
  final VoidCallback? onChanged;

  @override
  Widget build(BuildContext context) => PopupMenuButton<String>(
        tooltip: 'Bharosa',
        onSelected: (x) async {
          final r = await _guard(context, () => x == 'report' ? app.api!.netTrustReport(peer, 'spam') : app.api!.netTrustSet(peer, x));
          if (r != null && context.mounted) _snack(context, _s(r['say']).isEmpty ? 'Ho gaya: ${_s(r['word'])}' : _s(r['say']));
          onChanged?.call();
        },
        itemBuilder: (_) => const [
          PopupMenuItem(value: 'trusted', child: Text('Bharosemand (auto quote / order meri seema tak)')),
          PopupMenuItem(value: 'known', child: Text('Sirf jaan-pehchaan (har order mere tap se)')),
          PopupMenuItem(value: 'auto', child: Text('Apne aap (rishte se)')),
          PopupMenuItem(value: 'report', child: Text('Shikayat / spam')),
        ],
        child: Pill(say.isEmpty ? tier : say, fg: tierColor[tier] ?? C.chip),
      );
}
