// v0.999.25 HOOLA CREDITS ON THE PHONE (owner: "GO Dodo Payments, Paddle, RAZORPAY, CASHFREE"): Settings > Credits.
// Her wallet (free today on Normal, paid credits, her plan), the plans / extra credits / AI-employee packages for HER
// country (the server picks the price level and the payment service), and recent orders. Buying opens the provider's
// checkout in the phone's browser; credits are added only when the provider confirms (the page asks the server).
import 'dart:async';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_tabs.dart';

String _s(Object? v) => v == null ? '' : '$v';
num _n(Object? v) => v is num ? v : num.tryParse('$v') ?? 0;
String _int(Object? v) {
  final t = _n(v).round().toString();
  return t.replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},');
}

String hoolaCountry() => (ui.PlatformDispatcher.instance.locale.countryCode ?? '').toUpperCase();

class HoolaCreditsPage extends StatefulWidget {
  const HoolaCreditsPage({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaCreditsPage> createState() => _HoolaCreditsPageState();
}

class _HoolaCreditsPageState extends State<HoolaCreditsPage> {
  Map<String, dynamic>? _v;
  String? _err;
  String _busy = '';
  String _emp = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await widget.app.api!.credits(hoolaCountry());
      if (mounted) setState(() {
        _v = v;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  void _toast(String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

  String _money(Object? v, String cur) => cur == 'INR' ? '₹${_int(v)}' : '\$${_n(v) % 1 == 0 ? _int(v) : _n(v).toStringAsFixed(2)}';

  Future<void> _buy(String sku, {bool pack = false}) async {
    if (_busy.isNotEmpty) return;
    if (pack && _emp.isEmpty) {
      _toast('Pick the AI employee first.');
      return;
    }
    setState(() => _busy = sku);
    try {
      final o = await widget.app.api!.creditsCheckout(sku, hoolaCountry(), employee: pack ? _emp : '');
      final url = _s(o['redirect']).isNotEmpty ? _s(o['redirect']) : _s(o['pay_url']);
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
      _toast('Finish the payment in the browser. Credits are added once the payment service confirms it.');
      for (var i = 0; i < 60 && mounted; i++) {
        await Future<void>.delayed(const Duration(seconds: 4));
        final s = await widget.app.api!.creditsOrder(_s(o['order']));
        if (_s(s['status']) != 'pending') {
          _toast(_s(s['status']) == 'paid' ? 'Payment received.' : 'The payment did not go through.');
          break;
        }
      }
      await _load();
    } catch (e) {
      _toast('$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  Widget _card(HoolaColors c, List<Widget> kids) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter, vertical: 6),
        child: Container(
          padding: const EdgeInsets.all(HoolaSpace.s16),
          decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(HoolaRadius.card), border: Border.all(color: c.line)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: kids),
        ),
      );

  Widget _offer(HoolaColors c, String title, String price, String sub, String sku, String button, {bool pack = false}) =>
      _card(c, [
        Row(children: [
          Expanded(child: Text(title, style: HoolaType.title(c))),
          Text(price, style: HoolaType.title(c)),
        ]),
        const SizedBox(height: 4),
        Text(sub, style: HoolaType.small(c)),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: _busy.isEmpty ? () => _buy(sku, pack: pack) : null,
            style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder(),
                minimumSize: const Size.fromHeight(HoolaSpace.touch)),
            child: _busy == sku
                ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                : Text(button),
          ),
        ),
      ]);

  List<Widget> _wallet(HoolaColors c, Map<String, dynamic> w) {
    if (w['on'] != true) return [_card(c, [Text('Credits are off on this server.', style: HoolaType.body(c))])];
    if (w['exempt'] == true) return [_card(c, [Text('This account is never charged.', style: HoolaType.body(c))])];
    final plan = _s(w['plan']).isEmpty
        ? 'No plan'
        : '${_s(w['plan_name'])} plan until ${DateTime.tryParse(_s(w['plan_until']))?.toLocal().toString().split(' ').first ?? ''}';
    return [
      _card(c, [
        Text('${_int(w['paid_left'])} paid credits', style: HoolaType.display(c)),
        const SizedBox(height: 6),
        Text('$plan · ${_int(w['plan_left'])} plan · ${_int(w['topup_left'])} extra', style: HoolaType.small(c)),
        Text('Free today (Normal only): ${_int(w['free_left'])} of ${_int(w['free_daily'])}', style: HoolaType.small(c)),
        const SizedBox(height: 8),
        Text(
          w['unlocked'] == true
              ? 'Every quality tier is open. Each message takes the credits of the tier it runs on - Ultra goes fastest.'
              : 'Free works on Normal. Buy any plan or extra credits to open Ultra, High, Medium and Low.',
          style: HoolaType.body(c).copyWith(color: c.ink2),
        ),
      ]),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = _v;
    final p = Map<String, dynamic>.from((v?['prices'] as Map?) ?? const {});
    final cur = _s(p['currency']);
    final w = Map<String, dynamic>.from((v?['wallet'] as Map?) ?? const {});
    final children = <Widget>[
      const HoolaTabHeader(title: 'Credits', sub: 'One credit is 0.1 US cent of AI cost'),
      if (_err != null)
        Padding(
          padding: const EdgeInsets.all(HoolaSpace.gutter),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Could not load your credits.', style: HoolaType.body(c)),
            Text(_err!, style: HoolaType.small(c)),
            TextButton(onPressed: _load, child: const Text('Try again')),
          ]),
        )
      else if (v == null)
        Padding(padding: const EdgeInsets.all(HoolaSpace.s32), child: Center(child: CircularProgressIndicator(color: c.accent)))
      else ...[
        ..._wallet(c, w),
        if (w['on'] == true && w['exempt'] != true) ...[
          const HoolaSection('Monthly plans'),
          for (final x in ((p['plans'] as List?) ?? const []).cast<Map>())
            _offer(c, _s(x['name']), '${_money(x['price'], cur)} / month', '${_int(x['credits'])} credits a month',
                _s(x['sku']), 'Buy ${_s(x['name'])}'),
          const HoolaSection('Extra credits'),
          for (final x in ((p['topups'] as List?) ?? const []).cast<Map>())
            _offer(c, '${_int(x['credits'])} credits', _money(x['price'], cur), 'Last 12 months', _s(x['sku']), 'Buy'),
          const HoolaSection('AI employees'),
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 0, HoolaSpace.gutter, 6),
            child: Text('Each AI employee has its own package: a number of jobs a month on a set tier. '
                'It is not paid from your credits.', style: HoolaType.small(c)),
          ),
          for (final x in ((v['packs'] as List?) ?? const []).cast<Map>())
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 0, HoolaSpace.gutter, 4),
              child: Text('${_s(x['employee'])} - ${_s(x['name'])}: '
                  '${x['active'] == true ? '${_int(x['left'])} of ${_int(x['jobs'])} jobs left' : 'ended'}',
                  style: HoolaType.body(c)),
            ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
            child: _EmployeePicker(app: widget.app, value: _emp, onChanged: (k) => setState(() => _emp = k)),
          ),
          for (final x in ((p['packs'] as List?) ?? const []).cast<Map>())
            _offer(c, _s(x['name']), '${_money(x['price'], cur)} / month',
                '${_int(x['jobs'])} jobs a month · ${_s(x['tier'])}', _s(x['sku']), 'Buy package', pack: true),
        ],
      ],
    ];
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(backgroundColor: c.bg, surfaceTintColor: c.bg, foregroundColor: c.ink, elevation: 0, toolbarHeight: 48),
      body: SafeArea(
        top: false,
        child: RefreshIndicator(
          color: c.accent,
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.only(bottom: HoolaSpace.s32),
            children: children,
          ),
        ),
      ),
    );
  }
}

/// Which AI employee a package is for (the live employees from GET /api/employees).
class _EmployeePicker extends StatefulWidget {
  const _EmployeePicker({required this.app, required this.value, required this.onChanged});
  final Santosh app;
  final String value;
  final ValueChanged<String> onChanged;
  @override
  State<_EmployeePicker> createState() => _EmployeePickerState();
}

class _EmployeePickerState extends State<_EmployeePicker> {
  List<Map<String, dynamic>> _list = const [];

  @override
  void initState() {
    super.initState();
    unawaited(() async {
      try {
        final r = await widget.app.api!.employees();
        final l = [
          for (final e in ((r['employees'] as List?) ?? const []).cast<Map>())
            if (e['live'] == true) Map<String, dynamic>.from(e),
        ];
        if (mounted) setState(() => _list = l);
      } catch (_) {}
    }());
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return DropdownButton<String>(
      isExpanded: true,
      value: widget.value.isEmpty ? null : widget.value,
      hint: Text('Pick the AI employee', style: HoolaType.body(c).copyWith(color: c.ink3)),
      items: [
        for (final e in _list)
          DropdownMenuItem(value: _s(e['key']), child: Text(_s(e['name']), overflow: TextOverflow.ellipsis)),
      ],
      onChanged: (k) => widget.onChanged(k ?? ''),
    );
  }
}
