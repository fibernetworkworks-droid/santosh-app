// v0.353 DASHBOARD: her website's numbers on the phone - the same /api/sites/<id>/dashboard the console draws:
// tiles with the change vs the previous period, visits / enquiries / sales / orders a day as bars, top pages and
// products as rows, order status. Drawn with a small CustomPainter (no chart package).
import 'package:flutter/material.dart';
import '../state.dart';
import 'glass.dart';

String _t(dynamic v) => v == null ? '' : '$v';
num _n(dynamic v) => v is num ? v : (num.tryParse('$v') ?? 0);
List<dynamic> _l(dynamic v) => v is List ? v : const [];
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};

/// 1,20,000 / 1.2 L / 3.4 Cr - the Indian way.
String inr(num v, {bool compact = false}) {
  final a = v.abs();
  String one(num x) => (x * 10).round() % 10 == 0 ? '${(x).round()}' : x.toStringAsFixed(1);
  if (compact) {
    if (a >= 10000000) return '${one(v / 10000000)} Cr';
    if (a >= 100000) return '${one(v / 100000)} L';
    if (a >= 1000) return '${one(v / 1000)}K';
  }
  final whole = v.round().abs().toString();
  String out = whole;
  if (whole.length > 3) {
    final head = whole.substring(0, whole.length - 3), tail = whole.substring(whole.length - 3);
    final parts = <String>[];
    for (var i = head.length; i > 0; i -= 2) {
      parts.insert(0, head.substring(i - 2 < 0 ? 0 : i - 2, i));
    }
    out = '${parts.join(',')},$tail';
  }
  return v < 0 ? '-$out' : out;
}

class SiteDashPage extends StatefulWidget {
  const SiteDashPage({super.key, required this.app, required this.id, this.name = ''});
  final Santosh app;
  final String id;
  final String name;
  @override
  State<SiteDashPage> createState() => _SiteDashPageState();
}

class _SiteDashPageState extends State<SiteDashPage> {
  Map<String, dynamic>? _d;
  String _err = '';
  int _days = 30;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _err = '');
    try {
      final d = await widget.app.api!.siteDashboard(widget.id, days: _days);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Widget _kpi(Map<String, dynamic> k) {
    final ch = k['change_pct'];
    final money = k['money'] == true;
    final value = money ? '₹${inr(_n(k['value']))}' : '${inr(_n(k['value']))}${_t(k['suffix'])}';
    final up = ch is num && ch >= 0;
    return SizedBox(
      width: 150,
      child: Glass(
        radius: 16,
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_t(k['label']), style: const TextStyle(color: C.muted, fontSize: 12)),
          const SizedBox(height: 2),
          Text(value, style: display(20)),
          if (ch is num)
            Text('${up ? '▲' : '▼'} ${ch.abs()}%', style: TextStyle(color: up ? C.ok : C.bad, fontSize: 12)),
        ]),
      ),
    );
  }

  Widget _card(String title, Widget child) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Glass(
          radius: 18,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: display(15)),
            const SizedBox(height: 10),
            child,
          ]),
        ),
      );

  Widget _bars(List<dynamic> values, Color color, {bool money = false}) {
    final v = values.map(_n).toList();
    if (v.every((x) => x == 0)) return const Text('Is samay mein kuch nahi.', style: TextStyle(color: C.faint, fontSize: 13));
    final days = _l(_m(_d?['series'])['days']).map((x) => _t(x)).toList();
    final best = v.reduce((a, b) => a > b ? a : b);
    final at = v.indexOf(best);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(
        height: 120,
        width: double.infinity,
        child: Semantics(
          label: 'Chart: sabse zyada ${money ? '₹' : ''}${inr(best)}${at >= 0 && at < days.length ? ' on ${days[at]}' : ''}',
          child: CustomPaint(painter: _BarsPainter(v, color)),
        ),
      ),
      const SizedBox(height: 4),
      Row(children: [
        Text(days.isNotEmpty ? days.first.substring(5) : '', style: const TextStyle(color: C.faint, fontSize: 11)),
        const Spacer(),
        Text('Max ${money ? '₹' : ''}${inr(best, compact: true)}', style: const TextStyle(color: C.faint, fontSize: 11)),
        const Spacer(),
        Text(days.isNotEmpty ? days.last.substring(5) : '', style: const TextStyle(color: C.faint, fontSize: 11)),
      ]),
    ]);
  }

  Widget _rows(List<dynamic> rows, {bool money = false, int valueAt = 1, String Function(List<dynamic>)? label}) {
    if (rows.isEmpty) return const Text('Abhi kuch nahi.', style: TextStyle(color: C.faint, fontSize: 13));
    final max = rows.map((r) => _n(_l(r).length > valueAt ? _l(r)[valueAt] : 0)).fold<num>(1, (a, b) => b > a ? b : a);
    return Column(children: [
      for (final r in rows.take(8))
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(label != null ? label(_l(r)) : _t(_l(r).first), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 13))),
              Text('${money ? '₹' : ''}${inr(_n(_l(r)[valueAt]), compact: true)}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            ]),
            const SizedBox(height: 3),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(value: (_n(_l(r)[valueAt]) / max).toDouble().clamp(0.0, 1.0), minHeight: 6,
                  backgroundColor: C.panel, color: C.accent),
            ),
          ]),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final sr = _m(d?['series']);
    final app = _m(d?['app']);
    return Scaffold(
      appBar: AppBar(title: Text(widget.name.isEmpty ? 'Website dashboard' : '${widget.name} · dashboard'), actions: [
        IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load, tooltip: 'Dobara'),
      ]),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(14), children: [
          Wrap(spacing: 8, children: [
            for (final n in const [7, 30, 90, 365])
              ChoiceChip(
                label: Text(n == 365 ? '1 saal' : '$n din'),
                selected: _days == n,
                onSelected: (_) {
                  setState(() => _days = n);
                  _load();
                },
              ),
          ]),
          const SizedBox(height: 10),
          if (_err.isNotEmpty) Text(_err, style: const TextStyle(color: C.bad)),
          if (d == null && _err.isEmpty) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
          if (d != null) ...[
            Text(_t(d['say']), style: const TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 8, children: [for (final k in _l(d['kpis'])) _kpi(_m(k))]),
            const SizedBox(height: 12),
            _card('Roz ke visit', _bars(_l(sr['visits']), C.violet)),
            _card('Enquiry + booking roz', _bars([
              for (var i = 0; i < _l(sr['enquiries']).length; i++)
                _n(_l(sr['enquiries'])[i]) + (i < _l(sr['bookings']).length ? _n(_l(sr['bookings'])[i]) : 0)
            ], C.teal)),
            _card('Sabse zyada dekhe gaye page', _rows(_l(d['top_pages']))),
            if (d['shop'] == true) ...[
              _card('Roz ki pakki bikri (₹)', _bars(_l(sr['sales']), C.accent, money: true)),
              _card('Roz ke order', _bars(_l(sr['orders']), C.accent2)),
              _card('Order kis haal mein', _rows(_l(d['status_mix']))),
              _card('Sabse zyada bikne wale', _rows(_l(d['top_products']), money: true, valueAt: 2,
                  label: (r) => '${_t(r.first)} × ${_t(r.length > 1 ? r[1] : '')}')),
            ],
            for (final x in _l(app['lists']).take(6))
              _card('Web app: ${_t(_m(x)['label'])} (naye roz)', _bars(_l(_m(x)['days']), C.teal)),
            const Text('Visit Hoola ka apna server ginta hai (cookie / tracker nahi; bots aur uptime check nahi gine jaate). '
                'Bikri mein sirf woh order jo aapne pakke kiye.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ],
        ]),
      ),
    );
  }
}

class _BarsPainter extends CustomPainter {
  _BarsPainter(this.values, this.color);
  final List<num> values;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;
    final max = values.fold<num>(0, (a, b) => b > a ? b : a);
    final grid = Paint()
      ..color = C.line
      ..strokeWidth = 1;
    for (var i = 0; i <= 3; i++) {
      final y = size.height * i / 3;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    if (max <= 0) return;
    final band = size.width / values.length;
    final w = (band * 0.7).clamp(1.0, 18.0);
    final p = Paint()..color = color;
    for (var i = 0; i < values.length; i++) {
      final h = size.height * (values[i] / max).toDouble();
      if (h <= 0) continue;
      final x = band * i + (band - w) / 2;
      canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(x, size.height - h, w, h), const Radius.circular(2)), p);
    }
  }

  @override
  bool shouldRepaint(covariant _BarsPainter old) => old.values != values || old.color != color;
}
