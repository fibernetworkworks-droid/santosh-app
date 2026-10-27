import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.98 Kharcha: what Hoola's AI cost this month (chat, calls, website jobs, videos...), the monthly limit, the trend.
class KharchaScreen extends StatefulWidget {
  const KharchaScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<KharchaScreen> createState() => _KharchaScreenState();
}

class _KharchaScreenState extends State<KharchaScreen> {
  Map<String, dynamic>? _r;
  String? _err;
  bool _busy = false;
  int _days = 30;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.usageReport(days: _days);
      if (mounted) setState(() {
        _r = r;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  String _rs(dynamic v) {
    final n = (v as num?)?.toDouble() ?? 0;
    if (n >= 100) {
      final s = n.round().toString();
      // Indian grouping: 12,34,567
      if (s.length <= 3) return '₹$s';
      final last3 = s.substring(s.length - 3);
      var rest = s.substring(0, s.length - 3);
      final parts = <String>[];
      while (rest.length > 2) {
        parts.insert(0, rest.substring(rest.length - 2));
        rest = rest.substring(0, rest.length - 2);
      }
      if (rest.isNotEmpty) parts.insert(0, rest);
      return '₹${parts.join(',')},$last3';
    }
    return '₹${n.toStringAsFixed(n < 10 ? 2 : 0)}';
  }

  Future<void> _setLimit(double inr) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.usageLimit(inr);
      _r = r;
      widget.app.usage = {
        'spent_inr': (r['month'] as Map)['spent_inr'],
        'limit_inr': (r['month'] as Map)['limit_inr'],
        'pct': (r['month'] as Map)['pct'],
      };
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _customLimit() async {
    final c = TextEditingController();
    final v = await showDialog<double>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Mahine ki seema (₹)'),
        content: TextField(controller: c, keyboardType: TextInputType.number, decoration: const InputDecoration(hintText: 'jaise 3000')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, double.tryParse(c.text.replaceAll(',', '').trim())), child: const Text('Rakho')),
        ],
      ),
    );
    if (v != null && v >= 0) await _setLimit(v);
  }

  Widget _bar(double frac, Color color, {double h = 10}) => ClipRRect(
        borderRadius: BorderRadius.circular(h),
        child: Stack(children: [
          Container(height: h, color: C.panel),
          FractionallySizedBox(widthFactor: frac.clamp(0.0, 1.0), child: Container(height: h, color: color)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final m = Map<String, dynamic>.from((r?['month'] as Map?) ?? const {});
    final limit = (m['limit_inr'] as num?)?.toDouble() ?? 0;
    final spent = (m['spent_inr'] as num?)?.toDouble() ?? 0;
    final pct = limit > 0 ? spent / limit : 0.0;
    final color = pct >= 1 ? C.bad : (pct >= .8 ? C.warn : C.ok);
    final feats = List<Map<String, dynamic>>.from(((r?['features'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final models = List<Map<String, dynamic>>.from(((r?['models'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final daily = List<Map<String, dynamic>>.from(((r?['daily'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final maxDay = daily.fold<double>(0, (a, d) => math.max(a, (d['inr'] as num?)?.toDouble() ?? 0));
    final topFeat = feats.isEmpty ? 0.0 : ((feats.first['inr'] as num?)?.toDouble() ?? 0);
    return Scaffold(
      appBar: AppBar(title: const Text('AI ka kharcha')),
      body: r == null
          ? Center(child: _err == null ? const CircularProgressIndicator() : Padding(padding: const EdgeInsets.all(24), child: Text(_err!)))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
                Glass(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Is mahine', style: TextStyle(color: C.muted)),
                    const SizedBox(height: 2),
                    Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                      Text(_rs(spent), style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w800)),
                      const SizedBox(width: 8),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 5),
                        child: Text(limit > 0 ? '/ ${_rs(limit)} seema' : 'koi seema nahi', style: const TextStyle(color: C.muted)),
                      ),
                    ]),
                    if (limit > 0) ...[const SizedBox(height: 8), _bar(pct, color)],
                    const SizedBox(height: 8),
                    Text('Isi raftaar se mahine ke ant tak ~${_rs(m['projected_inr'])}', style: const TextStyle(color: C.muted, fontSize: 13)),
                    if (m['over'] == true)
                      const Padding(
                        padding: EdgeInsets.only(top: 6),
                        child: Text('Seema poori: background kaam (routine, website / video jobs, team ke kaam) ruke hain. Aapki chat aur call chalti hai.',
                            style: TextStyle(color: C.bad, fontSize: 12.5)),
                      ),
                  ]),
                ),
                const SizedBox(height: 14),
                const Text('Mahine ki seema', style: TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final v in const [500.0, 1000.0, 2000.0, 5000.0])
                    ChoiceChip(label: Text(_rs(v)), selected: limit == v, onSelected: _busy ? null : (_) => _setLimit(v)),
                  ActionChip(label: const Text('Apni likhiye'), onPressed: _busy ? null : _customLimit),
                  ChoiceChip(label: const Text('Koi seema nahi'), selected: limit == 0, onSelected: _busy ? null : (_) => _setLimit(0)),
                ]),
                const Padding(
                  padding: EdgeInsets.only(top: 6),
                  child: Text('80% par aapko bataya jayega; 100% par background kaam ruk jayenge, aapki apni chat aur call nahi.',
                      style: TextStyle(color: C.faint, fontSize: 12)),
                ),
                const SizedBox(height: 18),
                Row(children: [
                  const Expanded(child: Text('Roz ka kharcha', style: TextStyle(fontWeight: FontWeight.w800))),
                  for (final d in const [7, 30])
                    Padding(
                      padding: const EdgeInsets.only(left: 6),
                      child: ChoiceChip(
                          label: Text('$d din'),
                          selected: _days == d,
                          onSelected: (_) {
                            setState(() => _days = d);
                            _load();
                          }),
                    ),
                ]),
                const SizedBox(height: 8),
                SizedBox(
                  height: 90,
                  child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    for (final d in daily)
                      Expanded(
                        child: Tooltip(
                          message: '${d['day']}: ${_rs(d['inr'])}',
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 1),
                            child: Container(
                              height: maxDay > 0 ? math.max(2, 86 * (((d['inr'] as num?)?.toDouble() ?? 0) / maxDay)) : 2,
                              decoration: BoxDecoration(color: C.accent.withOpacity(.85), borderRadius: BorderRadius.circular(3)),
                            ),
                          ),
                        ),
                      ),
                  ]),
                ),
                const SizedBox(height: 18),
                const Text('Kahan gaya', style: TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                if (feats.isEmpty) const Text('Abhi koi kharcha nahi.', style: TextStyle(color: C.muted)),
                for (final f in feats)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(child: Text('${f['label']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                        Text('${_rs(f['inr'])} · ${f['share']}%', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                      ]),
                      const SizedBox(height: 4),
                      _bar(topFeat > 0 ? ((f['inr'] as num?)?.toDouble() ?? 0) / topFeat : 0, C.violet, h: 7),
                    ]),
                  ),
                const SizedBox(height: 10),
                const Text('Models', style: TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                for (final mm in models)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(children: [
                      Expanded(
                          child: Text('${mm['model']}${mm['estimate'] == true ? ' (andaaza)' : ''}',
                              style: const TextStyle(fontSize: 13), overflow: TextOverflow.ellipsis)),
                      Text(
                          '${mm['calls']} baar${((mm['minutes'] as num?) ?? 0) > 0 ? ' · ${mm['minutes']} min' : ''} · ${_rs(mm['inr'])}',
                          style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                const SizedBox(height: 10),
                Text('${r['note'] ?? ''}', style: const TextStyle(color: C.faint, fontSize: 12)),
              ]),
            ),
    );
  }
}
