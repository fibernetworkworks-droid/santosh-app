import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'lock_safe.dart' show MakerSteps;

/// v0.56 "Hoola band na ho": Xiaomi / Oppo / Realme / Vivo / Samsung... battery savers stop apps in the background.
/// The phone tells our server what Android itself knows (battery saver, "restricted", standby bucket, how the app was
/// last stopped); the answer is plain-word problems + this phone family's checklist, each line with a "Kholo" button
/// that opens the right settings page. Only settings pages are opened (Google Play policy); the owner flips the switch.
class KeepAlive {
  static final ValueNotifier<Map<String, dynamic>?> last = ValueNotifier(null);
  static bool _prompting = false;

  /// Checks now (phone facts -> server). Never throws; null when it couldn't check.
  static Future<Map<String, dynamic>?> check(Santosh app) async {
    final facts = await Native.bgHealth();
    if (facts.isEmpty || app.api == null) return null;
    try {
      final r = await app.api!.bgHealth(facts);
      r['facts'] = facts;
      last.value = r;
      return r;
    } catch (_) {
      return null;
    }
  }

  static Future<void> open(BuildContext context, Santosh app) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => KeepAliveScreen(app: app)));

  /// After start: once on strict phones (first-run setup), and again whenever the phone has stopped Hoola since the
  /// last look (at most every 3 days). A small sheet; "Theek karo" opens the checklist.
  static Future<void> maybePrompt(BuildContext context, Santosh app) async {
    if (_prompting) return;
    _prompting = true;
    try {
      final r = await check(app);
      if (r == null || !context.mounted) return;
      final p = await SharedPreferences.getInstance();
      final probs = List<Map<String, dynamic>>.from((r['problems'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
      final lastKill = (r['last_kill'] as num? ?? 0).toInt();
      final seenKill = p.getInt('ka_seen_kill') ?? 0;
      final nowMs = DateTime.now().millisecondsSinceEpoch;
      final quiet = nowMs - (p.getInt('ka_prompt_at') ?? 0) < 3 * 86400000;
      final firstRun = r['strict'] == true && !(p.getBool('ka_onboarded') ?? false);
      final newKills = lastKill > seenKill && probs.any((e) => e['code'] == 'oem_kills' || e['code'] == 'recents_clear');
      if (!firstRun && (!newKills || quiet)) return;
      await p.setBool('ka_onboarded', true);
      await p.setInt('ka_prompt_at', nowMs);
      await p.setInt('ka_seen_kill', lastKill);
      if (!context.mounted) return;
      final brand = _brandName(r);
      final go = await showModalBottomSheet<bool>(
        context: context,
        backgroundColor: const Color(0xFF151A24),
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        builder: (ctx) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 14),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.battery_alert_rounded, color: Color(0xFFFFB15C)),
                const SizedBox(width: 8),
                Expanded(child: Text(newKills ? 'Phone ne ${app.aName} ko band kiya' : '$brand phone: ek baar 1 minute', style: display(20))),
              ]),
              const SizedBox(height: 8),
              Text(
                  newKills
                      ? (probs.firstWhere((e) => e['code'] == 'oem_kills' || e['code'] == 'recents_clear')['title'] as String? ?? '') +
                          '. Isliye reminder / jawab der se ya bilkul nahi aate.'
                      : '$brand phones battery bachane ke liye apps ko background mein band kar dete hain. 3-4 settings ek baar kar dijiye, '
                          'phir ${app.aName} ke reminder, alarm aur jawab time par aayenge.',
                  style: const TextStyle(color: C.muted, fontSize: 13.5, height: 1.4)),
              const SizedBox(height: 14),
              Row(children: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Baad mein')),
                const Spacer(),
                FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Theek karo')),
              ]),
            ]),
          ),
        ),
      );
      if (go == true && context.mounted) await open(context, app);
    } finally {
      _prompting = false;
    }
  }

  static String _brandName(Map<String, dynamic> r) {
    final b = '${(r['facts'] as Map?)?['brand'] ?? r['vendor'] ?? ''}';
    return b.isEmpty ? 'Aapka' : '${b[0].toUpperCase()}${b.substring(1)}';
  }

  static Future<void> runAction(String action) async {
    switch (action) {
      case 'autostart':
        await Native.openAutostart();
      case 'battery':
        await Native.askBattery();
      case 'maker_battery':
        await Native.openMakerBattery();
      case 'maker_perms':
        await Native.openMakerPerms();
      case 'notifications':
        await Native.openNotificationSettings();
      case 'app_info':
        await Native.openMakerPerms();      // falls back to app info on non-Xiaomi phones
    }
  }
}

class KeepAliveScreen extends StatefulWidget {
  const KeepAliveScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<KeepAliveScreen> createState() => _KeepAliveScreenState();
}

class _KeepAliveScreenState extends State<KeepAliveScreen> with WidgetsBindingObserver {
  Map<String, dynamic>? _r = KeepAlive.last.value;
  bool _busy = true;
  Set<String> _done = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) _load();     // back from a settings page: check again
  }

  Future<void> _load() async {
    if (mounted) setState(() => _busy = true);
    final p = await SharedPreferences.getInstance();
    _done = (p.getStringList('ka_done') ?? const []).toSet();
    final r = await KeepAlive.check(widget.app);
    if (!mounted) return;
    setState(() {
      _r = r ?? _r;
      _busy = false;
    });
  }

  Future<void> _toggle(String id, bool on) async {
    setState(() => on ? _done.add(id) : _done.remove(id));
    final p = await SharedPreferences.getInstance();
    await p.setStringList('ka_done', _done.toList());
  }

  /// A line Android can confirm by itself is ticked from the real state; others by the owner's "Ho gaya".
  bool? _auto(String id, String action) {
    final f = (_r?['facts'] as Map?) ?? const {};
    if (action == 'notifications') return f['notifications'] == true;
    if (action == 'battery' || (action == 'maker_battery' && id == 'battery' && f['battery_optimized'] != null)) {
      if (f['background_restricted'] == true) return false;
      return f['battery_optimized'] == false ? true : null;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final probs = List<Map<String, dynamic>>.from((r?['problems'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final items = List<Map<String, dynamic>>.from((r?['checklist'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final counts = Map<String, dynamic>.from(r?['counts'] as Map? ?? const {});
    final kills = (counts['oem_kill'] as num? ?? 0) + (counts['recents_clear'] as num? ?? 0);
    final brand = r == null ? '' : KeepAlive._brandName(r);
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${widget.app.aName} band na ho')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: [
          Glass(
            child: Row(children: [
              Icon(r == null ? Icons.hourglass_top_rounded : (probs.isEmpty ? Icons.verified_rounded : Icons.battery_alert_rounded),
                  color: r == null ? C.muted : (probs.isEmpty ? C.ok : const Color(0xFFFFB15C)), size: 34),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(
                      r == null
                          ? (_busy ? 'Jaanch raha hoon…' : 'Jaanch nahi paye (server se judiye)')
                          : probs.isEmpty
                              ? 'Sab theek lag raha hai'
                              : '${probs.length} cheez theek karni hai',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                  if (r != null)
                    Text(
                        kills > 0
                            ? 'Pichhle 7 din mein phone ne ${widget.app.aName} ko $kills baar background mein band kiya.'
                            : 'Pichhle 7 din mein phone ne ${widget.app.aName} ko band nahi kiya.',
                        style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
              if (_busy) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
            ]),
          ),
          for (final p in probs) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: const Color(0x2EFFB15C), borderRadius: BorderRadius.circular(16)),
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${p['title']}', style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xFFFFD9A8))),
                    Text('${p['fix']}', style: const TextStyle(fontSize: 12.5, color: Color(0xFFFFD9A8))),
                  ]),
                ),
                if ('${p['action']}' != 'none' && '${p['action']}' != 'recents')
                  TextButton(onPressed: () => KeepAlive.runAction('${p['action']}'), child: const Text('Kholo')),
              ]),
            ),
          ],
          const SizedBox(height: 18),
          Text(brand.isEmpty ? 'Ek baar yeh kar dijiye' : '$brand phone par ek baar yeh kar dijiye', style: display(18)),
          const SizedBox(height: 4),
          const Text('Har line ka "Kholo" sahi settings page kholta hai. Wahan switch aap khud ON kijiye, phir wapas aaiye.',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          for (final (i, it) in items.indexed)
            _ChecklistRow(
              n: i + 1,
              item: it,
              auto: _auto('${it['id']}', '${it['action']}'),
              done: _done.contains('${it['id']}'),
              onDone: (v) => _toggle('${it['id']}', v),
            ),
          if (r != null && '${r['vendor'] ?? ''}'.isNotEmpty && widget.app.api != null)
            MakerSteps(app: widget.app, brand: '${(r['facts'] as Map?)?['brand'] ?? r['vendor']}'),
          const SizedBox(height: 14),
          OutlinedButton.icon(
            onPressed: _busy ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Dobara jaanchiye'),
          ),
        ]),
      ),
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow({required this.n, required this.item, required this.auto, required this.done, required this.onDone});
  final int n;
  final Map<String, dynamic> item;
  final bool? auto;     // known from Android: true = done, false = not done, null = only the owner knows
  final bool done;
  final ValueChanged<bool> onDone;

  @override
  Widget build(BuildContext context) {
    final ok = auto ?? done;
    final action = '${item['action']}';
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
      decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(14)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(ok ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded, color: ok ? C.ok : C.muted, size: 22),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('$n. ${item['title']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
            const SizedBox(height: 2),
            Text('${item['how']}', style: const TextStyle(fontSize: 12.5, height: 1.35, color: C.muted)),
            if (auto == null)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  style: TextButton.styleFrom(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact),
                  onPressed: () => onDone(!done),
                  child: Text(done ? 'Ho gaya ✓ (wapas lo)' : 'Ho gaya'),
                ),
              ),
          ]),
        ),
        if (action != 'recents' && action != 'none')
          TextButton(onPressed: () => KeepAlive.runAction(action), child: const Text('Kholo')),
      ]),
    );
  }
}
