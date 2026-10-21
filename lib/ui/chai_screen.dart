/// Profile > Chai stall (v0.84): Hoola as a chai stall's coworker.
/// Aaj (the day's galla from UPI alerts + cash, sales by hour, best hour), Kal (tomorrow's cups, milk / sugar / patti,
/// stock orders that wait for her Haan, how the day went), Galla (UPI alerts from her payment apps with a clear
/// disclosure first, statement upload, recent payments), Menu (what one cup takes, suppliers, her rules).
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
double? _num(String t) => double.tryParse(t.trim().replaceAll(',', '').replaceAll('₹', '').trim());
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
String _q(dynamic v) {
  final n = (v as num?)?.toDouble() ?? 0;
  return n == n.roundToDouble() ? n.toStringAsFixed(0) : n.toStringAsFixed(n < 1 ? 2 : 1);
}

mixin _ChaiLive<T extends StatefulWidget> on State<T> {
  Santosh get app;
  int _tick = -1;
  Future<void> reload();
  void _onApp() {
    if (app.chaiTick != _tick) {
      _tick = app.chaiTick;
      reload();
    }
  }

  void startLive() {
    _tick = app.chaiTick;
    app.addListener(_onApp);
    reload();
  }

  void stopLive() => app.removeListener(_onApp);
}

class ChaiScreen extends StatelessWidget {
  const ChaiScreen({super.key, required this.app});
  final Santosh app;

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: const Text('Chai stall sahayak'),
            bottom: const TabBar(tabs: [Tab(text: 'Aaj'), Tab(text: 'Kal'), Tab(text: 'Galla'), Tab(text: 'Menu')]),
          ),
          body: Aurora(
            child: TabBarView(children: [
              _TodayTab(app: app),
              _TomorrowTab(app: app),
              _GallaTab(app: app),
              _MenuTab(app: app),
            ]),
          ),
        ),
      );
}

Future<void> _addCash(BuildContext context, Santosh app) async {
  final amt = TextEditingController();
  final hr = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Cash ki bikri'),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: amt, autofocus: true, keyboardType: TextInputType.number, decoration: const InputDecoration(prefixText: '₹ ', labelText: 'Kitna cash')),
        TextField(controller: hr, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Kis ghante (0-23, khaali = poore din ka)')),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Jodo')),
      ],
    ),
  );
  final a = _num(amt.text);
  if (ok != true || a == null || a <= 0) return;
  try {
    final r = await app.api!.gallaCash(a, hour: int.tryParse(hr.text.trim()));
    if (context.mounted) _snack(context, _s(r['say']));
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
  }
}

// ---------------------------------------------------------------- Aaj
class _TodayTab extends StatefulWidget {
  const _TodayTab({required this.app});
  final Santosh app;
  @override
  State<_TodayTab> createState() => _TodayTabState();
}

class _TodayTabState extends State<_TodayTab> with _ChaiLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _h;
  String? _err;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final d = await app.api!.gallaToday();
      final h = await app.api!.gallaHours();
      if (mounted) setState(() {
        _d = d;
        _h = h;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Widget _bars(List<Map<String, dynamic>> hours) {
    if (hours.isEmpty) return const Text('Abhi ghante ka hisaab nahi.', style: TextStyle(color: C.muted));
    final max = hours.map((h) => (h['amount'] as num).toDouble()).fold<double>(1, (a, b) => b > a ? b : a);
    return SizedBox(
      height: 130,
      child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        for (final h in hours)
          Expanded(
            child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
              Container(
                height: 4 + 96 * ((h['amount'] as num).toDouble() / max),
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(color: C.accent, borderRadius: BorderRadius.circular(4)),
              ),
              const SizedBox(height: 4),
              Text('${h['hour']}', style: const TextStyle(fontSize: 10, color: C.muted)),
            ]),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        if (d == null && _err == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
        if (d != null) ...[
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(d['nice']), style: display(16))),
                if (d['alerts_live'] == true) const Pill('UPI live', fg: C.ok),
              ]),
              const SizedBox(height: 6),
              Text(_s(d['total']), style: display(34, color: C.accent)),
              Text('UPI ${_s(d['upi'])} (${d['upi_count']} payment)  ·  Cash ${_s(d['cash'])}', style: const TextStyle(color: C.chip)),
              if (_s(d['same_weekday_avg']).isNotEmpty || _s(d['yesterday']).isNotEmpty)
                Text([
                  if (_s(d['same_weekday_avg']).isNotEmpty) 'Isi din ka ausat ${d['same_weekday_avg']}',
                  if (_s(d['yesterday']).isNotEmpty) 'kal ${d['yesterday']}',
                ].join('  ·  '), style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              Text(_s(d['text']), style: const TextStyle(color: C.chip, height: 1.4, fontSize: 13)),
            ]),
          ),
          const SizedBox(height: 12),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Aaj ghante ke hisaab se', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 10),
              _bars(_list(d['hours'])),
              if (_h != null && _s(_h!['text']).isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(_s(_h!['text']), style: const TextStyle(color: C.accentSoft, fontSize: 13)),
              ],
            ]),
          ),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: GlassButton(label: 'Cash jodo', icon: Icons.payments_rounded, onTap: () => _addCash(context, app))),
            const SizedBox(width: 10),
            Expanded(
              child: GradientButton(
                label: 'Kal ka plan',
                height: 48,
                icon: Icons.local_cafe_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        setState(() => _busy = true);
                        try {
                          final r = await app.api!.chaiMakePlan(conversationId: app.conversationId ?? '');
                          if (mounted) _snack(context, _s(r['say']));
                          if (mounted) DefaultTabController.of(context).animateTo(1);
                        } catch (e) {
                          if (mounted) _snack(context, '$e');
                        }
                        if (mounted) setState(() => _busy = false);
                      },
              ),
            ),
          ]),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- Kal
class _TomorrowTab extends StatefulWidget {
  const _TomorrowTab({required this.app});
  final Santosh app;
  @override
  State<_TomorrowTab> createState() => _TomorrowTabState();
}

class _TomorrowTabState extends State<_TomorrowTab> with _ChaiLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _plan;
  bool _loaded = false;
  bool _busy = false;
  final _milkLeft = TextEditingController();
  final _ranOut = TextEditingController();
  final _sugarLeft = TextEditingController();
  final _teaLeft = TextEditingController();
  final _cash = TextEditingController();
  final _cups = TextEditingController();

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final p = await app.api!.chaiPlan();
      if (mounted) setState(() {
        _plan = p;
        _loaded = true;
      });
    } catch (e) {
      if (mounted) setState(() => _loaded = true);
    }
  }

  Future<void> _make() async {
    setState(() => _busy = true);
    try {
      final c = int.tryParse(_cups.text.trim());
      if (c != null && c > 0) await app.api!.chaiSaveSettings({'typical_cups': c});
      final r = await app.api!.chaiMakePlan(conversationId: app.conversationId ?? '');
      if (mounted) _snack(context, _s(r['say']));
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _feedback() async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.chaiFeedback({
        'for_date': '',
        if (_num(_milkLeft.text) != null) 'milk_left_l': _num(_milkLeft.text),
        if (_ranOut.text.trim().isNotEmpty) 'ran_out_at': _ranOut.text.trim(),
        if (_num(_sugarLeft.text) != null) 'sugar_left_kg': _num(_sugarLeft.text),
        if (_num(_teaLeft.text) != null) 'tea_left_kg': _num(_teaLeft.text),
        if (_num(_cash.text) != null) 'cash': _num(_cash.text),
      });
      if (mounted) _snack(context, _s(r['say']));
      for (final c in [_milkLeft, _ranOut, _sugarLeft, _teaLeft, _cash]) {
        c.clear();
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: reload,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
          if (!_loaded) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
          if (_loaded && _plan != null) ChaiPlanCard(key: ValueKey('cpt${_plan!['id']}'), v: _plan!, app: app),
          if (_loaded) ...[
            const SizedBox(height: 12),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_plan == null ? 'Kal ka plan abhi nahi bana' : 'Plan dobara banao', style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                const Text('Hoola aapke menu, pichhle hafton ki bikri, kal ki chhutti / baarish / garmi aur bache saamaan se banata hai. '
                    'Roz shaam aapke samay par apne aap bhi banta hai.', style: TextStyle(color: C.muted, fontSize: 12.5)),
                TextField(controller: _cups, keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Roz lagbhag kitne cup? (sirf shuru mein, jab tak hisaab na bane)')),
                const SizedBox(height: 10),
                GradientButton(label: 'Plan banao', height: 46, onTap: _busy ? null : _make),
              ]),
            ),
            const SizedBox(height: 12),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Aaj kaisa raha? (Hoola isse seekhta hai)', style: TextStyle(fontWeight: FontWeight.w800)),
                Row(children: [
                  Expanded(child: TextField(controller: _milkLeft, keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Doodh bacha (litre)'))),
                  const SizedBox(width: 10),
                  Expanded(child: TextField(controller: _ranOut, decoration: const InputDecoration(labelText: 'Ya khatam kab hua (18:30)'))),
                ]),
                Row(children: [
                  Expanded(child: TextField(controller: _sugarLeft, keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Chini bachi (kg)'))),
                  const SizedBox(width: 10),
                  Expanded(child: TextField(controller: _teaLeft, keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Patti bachi (kg)'))),
                ]),
                TextField(controller: _cash, keyboardType: TextInputType.number, decoration: const InputDecoration(prefixText: '₹ ', labelText: 'Aaj ka cash')),
                const SizedBox(height: 10),
                GlassButton(label: 'Likh lo', icon: Icons.check_rounded, onTap: _busy ? null : _feedback),
              ]),
            ),
          ],
        ]),
      );
}

/// Tomorrow's plan with one stock-order card per supplier; nothing is ordered until she taps Haan.
class ChaiPlanCard extends StatefulWidget {
  const ChaiPlanCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<ChaiPlanCard> createState() => _ChaiPlanCardState();
}

class _ChaiPlanCardState extends State<ChaiPlanCard> {
  String _busy = '';

  Future<void> _decide(Map<String, dynamic> o, bool yes) async {
    setState(() => _busy = _s(o['id']));
    try {
      final r = await widget.app.api!.chaiDecide(_s(o['id']), yes, conversationId: widget.app.conversationId ?? '');
      final nv = Map<String, dynamic>.from((r['order'] as Map?) ?? const {});
      final orders = _list(widget.v['orders']);
      final i = orders.indexWhere((x) => x['id'] == o['id']);
      if (i >= 0) orders[i] = {...orders[i], ...nv};
      widget.v['orders'] = orders;
      if (mounted) _snack(context, _s(r['say']));
      if (yes && _s(nv['wa_link']).isNotEmpty) await Native.openExternal(url: _s(nv['wa_link']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = '');
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final need = Map<String, dynamic>.from((v['need'] as Map?) ?? const {});
    final buy = Map<String, dynamic>.from((v['buy'] as Map?) ?? const {});
    final reasons = List<String>.from((v['reasons'] as List?) ?? const []);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.local_cafe_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Kal ka saamaan: ${_s(v['nice'])}', style: display(16))),
          if (_s(v['status']) == 'done') const Pill('Ho gaya', fg: C.ok),
        ]),
        const SizedBox(height: 8),
        Text('~${v['cups']} cup  ·  bikri ~${_s(v['sales'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 6, children: [
          Pill('Doodh ${_q(need['milk_l'])} L', fg: C.ink),
          Pill('Chini ${_q(need['sugar_kg'])} kg', fg: C.ink),
          Pill('Patti ${_q(need['tea_kg'])} kg', fg: C.ink),
        ]),
        if (buy.values.any((x) => (x as num) > 0))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('Lena hai: ${[
              if ((buy['milk_l'] ?? 0) > 0) 'doodh ${_q(buy['milk_l'])} L',
              if ((buy['sugar_kg'] ?? 0) > 0) 'chini ${_q(buy['sugar_kg'])} kg',
              if ((buy['tea_kg'] ?? 0) > 0) 'patti ${_q(buy['tea_kg'])} kg',
            ].join(', ')}', style: const TextStyle(color: C.accent, fontWeight: FontWeight.w700)),
          ),
        if (reasons.isNotEmpty)
          Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text('Kyun itna?', style: TextStyle(fontSize: 13, color: C.muted)),
              children: [for (final r in reasons) Align(alignment: Alignment.centerLeft, child: Text('• $r', style: const TextStyle(color: C.chip, fontSize: 12.5)))],
            ),
          ),
        for (final o in _list(v['orders']))
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(o['supplier']), style: const TextStyle(fontWeight: FontWeight.w800))),
                if (_s(o['status']) != 'pending')
                  Pill(_s(o['status']) == 'approved' ? 'Haan' : 'Mana', fg: _s(o['status']) == 'approved' ? C.ok : C.faint),
              ]),
              Text(_s(o['what']), style: const TextStyle(color: C.chip)),
              if (_s(o['site']).isNotEmpty) Text('${o['site']} se (payment aap karengi)', style: const TextStyle(color: C.muted, fontSize: 12)),
              const SizedBox(height: 6),
              if (_s(o['status']) == 'pending')
                Row(children: [
                  Expanded(child: GlassButton(label: 'Mana', height: 40, onTap: _busy.isNotEmpty ? null : () => _decide(o, false))),
                  const SizedBox(width: 8),
                  Expanded(child: GradientButton(label: 'Haan, order karo', height: 40, onTap: _busy.isNotEmpty ? null : () => _decide(o, true))),
                ])
              else if (_s(o['status']) == 'approved' && _s(o['wa_link']).isNotEmpty)
                GlassButton(label: 'WhatsApp par bhejo', icon: Icons.send_rounded, height: 40,
                    onTap: () => Native.openExternal(url: _s(o['wa_link']))),
            ]),
          ),
        const SizedBox(height: 4),
        Text('${widget.app.aName} khud order ya payment nahi karta: aapki haan ke baad message / order aap tak.',
            style: const TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Galla: UPI alerts (disclosure first), statement, payments
class _GallaTab extends StatefulWidget {
  const _GallaTab({required this.app});
  final Santosh app;
  @override
  State<_GallaTab> createState() => _GallaTabState();
}

class _GallaTabState extends State<_GallaTab> with _ChaiLive, WidgetsBindingObserver {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic> _info = const {};
  List<Map<String, dynamic>> _recent = const [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    startLive();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    stopLive();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) reload();     // back from Android settings
  }

  @override
  Future<void> reload() async {
    try {
      final info = await Native.payAlertsInfo();
      final r = await app.api!.gallaRecent();
      if (mounted) setState(() {
        _info = info;
        _recent = r;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  List<String> get _picked => List<String>.from((_info['apps'] as List?) ?? const []);

  Future<bool> _disclose() async {
    final ok = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        title: const Text('UPI alerts se galla'),
        content: SingleChildScrollView(
          child: Text(
            '${app.aName} aapke phone par aane wale sirf in payment apps ke "paise mile" wale notification padhega: '
            '${_list(_info['all']).where((a) => _picked.contains(a['package'])).map((a) => a['label']).join(', ')}.\n\n'
            'Kya jaata hai aapke Hoola server par: rakam, samay, app ka naam, bhejne wale ka pehla naam, reference ke aakhri 4 ank. '
            'Bas itna.\n\n'
            'Kya kabhi nahi: OTP, PIN, password, SMS, chat, doosre apps ke notification, bheje hue paise, poora notification. '
            'Yeh sab phone par hi chhod diya jaata hai.\n\n'
            'Kyun: roz ki bikri, sabse achha ghanta aur kal ka doodh-chini apne aap nikalne ke liye.\n\n'
            'Agle screen par Android "Notification access" mein "Hoola Galla" chalu kijiye. Kabhi bhi yahan se band kar sakti hain.',
            style: const TextStyle(height: 1.4),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Samajh gayi, chalu karo')),
        ],
      ),
    );
    return ok == true;
  }

  Future<void> _toggle(bool on) async {
    if (on && !await _disclose()) return;
    setState(() => _busy = true);
    try {
      final info = await Native.payAlertsSet(on, _picked);
      await app.api!.gallaSaveSettings({'apps': _picked});
      if (mounted) setState(() => _info = info);
      if (on && info['granted'] != true) await Native.payAlertsSettings();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _pickApp(String pkg, bool on) async {
    final apps = {..._picked};
    on ? apps.add(pkg) : apps.remove(pkg);
    try {
      final info = await Native.payAlertsSet(_info['on'] == true, apps.toList());
      await app.api!.gallaSaveSettings({'apps': apps.toList()});
      if (mounted) setState(() => _info = info);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _statement() async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: ['csv', 'xlsx']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.gallaStatement(f.name, f.bytes!);
      if (mounted) _snack(context, _s(r['say']));
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final on = _info['on'] == true;
    final granted = _info['granted'] == true;
    final last = (_info['last_sent'] as num?)?.toInt() ?? 0;
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        Glass(
          border: on && granted ? C.ok : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: on,
              onChanged: _busy ? null : _toggle,
              title: const Text('UPI alerts se galla', style: TextStyle(fontWeight: FontWeight.w800)),
              subtitle: Text(on
                  ? (granted ? 'Chalu: har UPI payment apne aap judta hai' : 'Android mein Notification access abhi nahi mila')
                  : 'Band: sirf jo aap batayengi / statement bhejengi'),
            ),
            if (on && !granted)
              GradientButton(label: 'Notification access kholo', height: 44, onTap: () => Native.payAlertsSettings()),
            if (on && granted)
              Text('Bheje: ${_info['sent_total'] ?? 0}  ·  ruke: ${_info['pending'] ?? 0}'
                  '${last > 0 ? '  ·  aakhri ${DateTime.fromMillisecondsSinceEpoch(last).toLocal().toString().substring(11, 16)}' : ''}',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
            const SizedBox(height: 8),
            const Text('Kaun se payment app padhe jaayein', style: TextStyle(color: C.muted)),
            for (final a in _list(_info['all']))
              CheckboxListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                value: _picked.contains(a['package']),
                onChanged: (x) => _pickApp(_s(a['package']), x ?? false),
                title: Text(_s(a['label'])),
                subtitle: a['business'] == true ? null : const Text('Personal app: ghar ke paise bhi gin sakta hai', style: TextStyle(fontSize: 11.5)),
              ),
            const Text('Sirf "paise mile" alert. OTP, SMS, bheje hue paise kabhi nahi.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: GlassButton(label: 'Statement (CSV / Excel)', icon: Icons.upload_file_rounded, onTap: _busy ? null : _statement)),
          const SizedBox(width: 10),
          Expanded(child: GlassButton(label: 'Cash jodo', icon: Icons.payments_rounded, onTap: () => _addCash(context, app))),
        ]),
        const SizedBox(height: 14),
        const Text('Haal ke payment', style: TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        if (_recent.isEmpty) const Text('Abhi koi payment nahi.', style: TextStyle(color: C.muted)),
        for (final r in _recent)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(r['source'] == 'cash' ? Icons.payments_rounded : Icons.qr_code_2_rounded, color: C.accentSoft),
            title: Text('${_s(r['amount'])}  ${_s(r['payer'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text('${_s(r['at'])}  ·  ${_s(r['app']).isEmpty ? _s(r['source']) : _s(r['app'])}', style: const TextStyle(fontSize: 12)),
            trailing: IconButton(
              icon: const Icon(Icons.remove_circle_outline_rounded, color: C.faint),
              tooltip: 'Galat hai, hatao',
              onPressed: () async {
                try {
                  await app.api!.gallaVoid(_s(r['id']));
                  await reload();
                } catch (e) {
                  if (context.mounted) _snack(context, '$e');
                }
              },
            ),
          ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Menu, suppliers, rules
class _MenuTab extends StatefulWidget {
  const _MenuTab({required this.app});
  final Santosh app;
  @override
  State<_MenuTab> createState() => _MenuTabState();
}

class _Item {
  _Item(Map<String, dynamic> m)
      : name = TextEditingController(text: _s(m['name'])),
        price = TextEditingController(text: _q(m['price'])),
        milk = TextEditingController(text: _q(m['milk_ml'])),
        sugar = TextEditingController(text: _q(m['sugar_g'])),
        tea = TextEditingController(text: _q(m['tea_g'])),
        share = TextEditingController(text: _q(m['share']));
  final TextEditingController name, price, milk, sugar, tea, share;
  Map<String, dynamic> body() => {
        'name': name.text.trim(),
        'price': _num(price.text) ?? 0,
        'milk_ml': _num(milk.text) ?? 0,
        'sugar_g': _num(sugar.text) ?? 0,
        'tea_g': _num(tea.text) ?? 0,
        'share': _num(share.text) ?? 0,
      };
}

class _Sup {
  _Sup(Map<String, dynamic> m)
      : name = TextEditingController(text: _s(m['name'])),
        phone = TextEditingController(text: _s(m['phone'])),
        site = TextEditingController(text: _s(m['site'])),
        items = Set<String>.from((m['items'] as List?) ?? const ['milk']);
  final TextEditingController name, phone, site;
  final Set<String> items;
  Map<String, dynamic> body() => {'name': name.text.trim(), 'phone': phone.text.trim(), 'site': site.text.trim(), 'items': items.toList()};
}

class _MenuTabState extends State<_MenuTab> {
  Map<String, dynamic>? _st;
  final List<_Item> _items = [];
  final List<_Sup> _sups = [];
  final _stall = TextEditingController();
  final _other = TextEditingController();
  final _cashPct = TextEditingController();
  final _safety = TextEditingController();
  final _packet = TextEditingController();
  final _planTime = TextEditingController();
  final _rules = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final st = await widget.app.api!.chaiSettings();
      if (!mounted) return;
      setState(() {
        _st = st;
        _items
          ..clear()
          ..addAll(_list(st['menu']).map(_Item.new));
        _sups
          ..clear()
          ..addAll(_list(st['suppliers']).map(_Sup.new));
        _stall.text = _s(st['stall_name']);
        _other.text = _s(st['other_pct']);
        _cashPct.text = _q(st['cash_pct']);
        _safety.text = _s(st['safety_pct']);
        _packet.text = _s(st['milk_packet_ml']);
        _planTime.text = _s(st['plan_time']);
        _rules.text = List<String>.from((st['rules'] as List?) ?? const []).join('\n');
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.chaiSaveSettings({
        'stall_name': _stall.text.trim(),
        'menu': [for (final i in _items) if (i.name.text.trim().isNotEmpty) i.body()],
        'suppliers': [for (final s in _sups) if (s.name.text.trim().isNotEmpty) s.body()],
        'other_pct': _num(_other.text) ?? 20,
        'cash_pct': _num(_cashPct.text) ?? 40,
        'safety_pct': _num(_safety.text) ?? 10,
        'milk_packet_ml': _num(_packet.text) ?? 500,
        'plan_time': _planTime.text.trim(),
        'rules': _rules.text.split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
      });
      if (mounted) _snack(context, 'Save ho gaya');
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _f(TextEditingController c, String label, {double w = 70}) => SizedBox(
        width: w,
        child: TextField(controller: c, keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: label, isDense: true)),
      );

  @override
  Widget build(BuildContext context) {
    final st = _st;
    if (st == null) return const Center(child: CircularProgressIndicator());
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(controller: _stall, decoration: const InputDecoration(labelText: 'Stall ka naam')),
          const SizedBox(height: 8),
          Text('Seekha hua: ek cup mein asal mein ~${_q(st['real_milk_per_cup_ml'])} ml doodh'
              '${(st['factor_learned'] ?? 0) > 0 ? ' (${st['factor_learned']} din se)' : ' (abhi menu se)'}; '
              'cash ~${_q(st['cash_pct'])}%${(st['cash_learned'] ?? 0) > 0 ? ' (seekha)' : ' (andaza)'}.',
              style: const TextStyle(color: C.accentSoft, fontSize: 12.5)),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Menu: ek cup mein kya lagta hai', style: TextStyle(fontWeight: FontWeight.w800)),
          const Text('Hissa % = sau cup mein se kitne yeh (andaza).', style: TextStyle(color: C.faint, fontSize: 11.5)),
          for (var i = 0; i < _items.length; i++)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Column(children: [
                Row(children: [
                  Expanded(child: TextField(controller: _items[i].name, decoration: const InputDecoration(labelText: 'Naam', isDense: true))),
                  IconButton(onPressed: () => setState(() => _items.removeAt(i)), icon: const Icon(Icons.close_rounded, color: C.faint)),
                ]),
                Wrap(spacing: 8, children: [
                  _f(_items[i].price, '₹ daam'),
                  _f(_items[i].milk, 'Doodh ml'),
                  _f(_items[i].sugar, 'Chini g'),
                  _f(_items[i].tea, 'Patti g'),
                  _f(_items[i].share, 'Hissa %'),
                ]),
              ]),
            ),
          TextButton.icon(
              onPressed: () => setState(() => _items.add(_Item(const {'name': '', 'price': 10, 'milk_ml': 50, 'sugar_g': 8, 'tea_g': 2.5, 'share': 10}))),
              icon: const Icon(Icons.add_rounded),
              label: const Text('Aur item')),
          Wrap(spacing: 12, children: [
            _f(_other, 'Chai ke alawa %', w: 120),
            _f(_cashPct, 'Cash %', w: 80),
            _f(_safety, 'Extra %', w: 80),
            _f(_packet, 'Packet ml', w: 90),
          ]),
          TextField(controller: _planTime, decoration: const InputDecoration(labelText: 'Roz plan kab (HH:MM)')),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Saamaan kahan se', style: TextStyle(fontWeight: FontWeight.w800)),
          for (var i = 0; i < _sups.length; i++)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: TextField(controller: _sups[i].name, decoration: const InputDecoration(labelText: 'Naam (Gopal doodhwala)', isDense: true))),
                  IconButton(onPressed: () => setState(() => _sups.removeAt(i)), icon: const Icon(Icons.close_rounded, color: C.faint)),
                ]),
                Row(children: [
                  Expanded(child: TextField(controller: _sups[i].phone, keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(labelText: 'WhatsApp number', isDense: true))),
                  const SizedBox(width: 8),
                  Expanded(child: TextField(controller: _sups[i].site,
                      decoration: const InputDecoration(labelText: 'Ya site (blinkit, jiomart)', isDense: true))),
                ]),
                Wrap(spacing: 6, children: [
                  for (final it in const {'milk': 'Doodh', 'sugar': 'Chini', 'tea': 'Patti'}.entries)
                    FilterChip(
                      label: Text(it.value),
                      selected: _sups[i].items.contains(it.key),
                      onSelected: (v) => setState(() => v ? _sups[i].items.add(it.key) : _sups[i].items.remove(it.key)),
                    ),
                ]),
              ]),
            ),
          TextButton.icon(onPressed: () => setState(() => _sups.add(_Sup(const {'items': ['milk']}))), icon: const Icon(Icons.add_rounded), label: const Text('Supplier jodo')),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: TextField(
          controller: _rules,
          minLines: 2,
          maxLines: 6,
          decoration: const InputDecoration(labelText: 'Apne niyam (ek line mein ek)', hintText: 'Doodh 20 litre se zyada ek din mein nahi\nRavivar ko 30% zyada'),
        ),
      ),
      const SizedBox(height: 14),
      GradientButton(label: 'Save karo', height: 50, onTap: _busy ? null : _save),
    ]);
  }
}
