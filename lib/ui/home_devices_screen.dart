import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// Ghar: the user's home devices. Speaker / TV / AC run from this phone (Bluetooth, IR blaster, Wi-Fi);
/// Samsung SmartThings, LG ThinQ and Bosch/Siemens Home Connect appliances come from the brand's own account.
class HomeDevicesScreen extends StatefulWidget {
  const HomeDevicesScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<HomeDevicesScreen> createState() => _HomeDevicesScreenState();
}

class _HomeDevicesScreenState extends State<HomeDevicesScreen> with WidgetsBindingObserver {
  List<Map<String, dynamic>> _devices = [];
  List<Map<String, dynamic>> _links = [];
  Map<String, dynamic> _caps = const {};
  bool _loaded = false;
  bool _busy = false;
  String? _err;

  Santosh get app => widget.app;

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

  // back from a brand sign-in page or the permission screen: refresh
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _load(quiet: true);
  }

  Future<void> _load({bool quiet = false}) async {
    try {
      final r = await app.api!.homeDevices();
      final caps = await Native.homeCaps();
      if (!mounted) return;
      setState(() {
        _devices = (r['devices'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _links = (r['links'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _caps = caps;
        _loaded = true;
        _err = null;
      });
    } catch (e) {
      if (mounted && !quiet) setState(() => _err = e.toString());
    }
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  String _clean(Object e) => e.toString().replaceFirst('Exception: ', '');

  /// Runs a server-built command on this phone and reports the result. Returns null when it worked.
  Future<String?> _runOnPhone(Map<String, dynamic> action) async {
    var res = await Native.homeRun(action);
    if (res == 'permission') {
      await Native.homeAskBluetooth();
      res = '"Nearby devices" ki permission dijiye, phir dobara try kijiye.';
    }
    final ok = res == 'ok';
    final id = action['command_id'] as String?;
    if (id != null) {
      try {
        await app.api!.homeResult(id, ok, ok ? '' : res);
      } catch (_) {}
    }
    return ok ? null : res;
  }

  Future<void> _guard(Future<void> Function() fn) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await fn();
    } catch (e) {
      _snack(_clean(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // ---------------------------------------------------------------- add devices
  Future<void> _add(String kind) async {
    if (kind == 'ac' && _caps['ir'] != true) {
      final go = await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
                backgroundColor: C.bgBottom,
                title: const Text('IR blaster nahi mila'),
                content: const Text('AC chalane ke liye phone mein IR blaster chahiye (Redmi, POCO, iQOO, kuch OnePlus/Realme). '
                    'Is phone mein nahi dikh raha. Samsung/LG AC ho to neeche brand account jodiye.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Theek hai')),
                  TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Phir bhi jodiye')),
                ],
              ));
      if (go != true) return;
    }
    List<Map<String, dynamic>> paired = const [];
    if (kind == 'tv') {
      if (_caps['tv_remote'] != true) {
        _snack('TV remote ke liye Android 9+ aur Bluetooth chahiye.');
        return;
      }
      if (!await Native.homeAskBluetooth()) {
        _snack('"Nearby devices" ki permission dijiye, phir dobara "TV jodiye" dabaiye.');
        return;
      }
      paired = await Native.homePaired();
    }
    if (!mounted) return;
    final name = TextEditingController(text: {'speaker': 'Speaker', 'tv': 'Hall TV', 'ac': 'Bedroom AC'}[kind]);
    final room = TextEditingController();
    final brand = TextEditingController();
    final ip = TextEditingController();
    String? bt;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setD) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: Text({'speaker': 'Speaker jodiye', 'tv': 'TV jodiye', 'ac': 'AC jodiye'}[kind]!),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam (jaise Bedroom AC)')),
              TextField(controller: room, decoration: const InputDecoration(labelText: 'Kamra (optional)')),
              if (kind == 'ac') TextField(controller: brand, decoration: const InputDecoration(labelText: 'Brand (LG, Midea, Voltas…)')),
              if (kind == 'speaker')
                const Padding(
                  padding: EdgeInsets.only(top: 10),
                  child: Text('Speaker ko pehle phone ki Bluetooth settings se jodiye. Hoola awaaz 90% se upar nahi le jaata.',
                      style: TextStyle(color: C.muted, fontSize: 12.5)),
                ),
              if (kind == 'tv') ...[
                const SizedBox(height: 10),
                const Text('Phone se juda TV chuniye (pehli baar ho to baad mein jodiye):', style: TextStyle(color: C.muted, fontSize: 12.5)),
                for (final d in paired.take(8))
                  RadioListTile<String>(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    value: d['address'] as String,
                    groupValue: bt,
                    onChanged: (v) => setD(() => bt = v),
                    title: Text(d['name'] as String? ?? ''),
                    subtitle: Text(d['address'] as String? ?? '', style: const TextStyle(fontSize: 11)),
                  ),
                TextField(controller: ip, keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'TV ka Wi-Fi IP (optional, jaise 192.168.1.20)')),
              ],
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne dijiye')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodiye')),
          ],
        ),
      ),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    await _guard(() async {
      final target = <String, dynamic>{
        if (bt != null) 'bt_address': bt,
        if (ip.text.trim().isNotEmpty) 'ip': ip.text.trim(),
      };
      final d = await app.api!.homeAdd(kind, name.text.trim(), room: room.text.trim(), brand: brand.text.trim(), target: target);
      await _load(quiet: true);
      if (kind == 'ac') {
        final tries = (d['setup']?['try_protocols'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        if (mounted) await _acSetup(d, tries);
      }
      if (kind == 'tv' && mounted) await _tvSetup(d);
    });
    await _load(quiet: true);
  }

  // ---------------------------------------------------------------- AC remote test ("did it beep?")
  Future<void> _acSetup(Map<String, dynamic> d, List<Map<String, dynamic>> tries) async {
    final list = tries.isNotEmpty
        ? tries
        : (_protocols()).map((e) => Map<String, dynamic>.from(e)).toList();
    for (var i = 0; i < list.length; i++) {
      final p = list[i];
      if (!mounted) return;
      final send = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (_) => AlertDialog(
                backgroundColor: C.bgBottom,
                title: Text('${d['name']}: remote test ${i + 1}/${list.length}'),
                content: Text('Phone ka upar wala hissa AC ki taraf rakhiye (2-3 metre ke andar), phir "Bhejiye" dabaiye.\n'
                    'Hoola "Cool 24°C" bhejega. (${p['label']})'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Baad mein')),
                  TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Bhejiye')),
                ],
              ));
      if (send != true) return;
      String? err;
      try {
        final t = await app.api!.homeIrTest(d['id'] as String, p['protocol'] as String);
        err = await _runOnPhone(Map<String, dynamic>.from(t['device_action'] as Map));
      } catch (e) {
        err = _clean(e);
      }
      if (!mounted) return;
      if (err != null) {
        _snack(err);
        return;
      }
      final beeped = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (_) => AlertDialog(
                backgroundColor: C.bgBottom,
                title: const Text('Kya AC ne beep kiya?'),
                content: const Text('AC chalu hua aur 24°C dikha raha hai?'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Nahi')),
                  TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Haan')),
                ],
              ));
      if (beeped == true) {
        final r = await app.api!.homeIrConfirm(d['id'] as String, p['protocol'] as String);
        _snack(r['message'] as String? ?? 'AC taiyaar hai');
        return;
      }
    }
    _snack('Is AC ka remote abhi Hoola nahi samajhta. Samsung/LG ho to brand account jodiye.');
  }

  List<Map> _protocols() => const [
        {'protocol': 'coolix', 'label': 'Midea family'},
        {'protocol': 'lg2_ac', 'label': 'LG inverter'},
        {'protocol': 'lg_ac', 'label': 'LG classic'},
      ];

  // ---------------------------------------------------------------- TV remote
  Future<void> _tvSetup(Map<String, dynamic> d) async {
    final r = await Native.homeRemote(true);
    if (r != 'ok') {
      _snack(r == 'permission' ? '"Nearby devices" ki permission dijiye.' : r);
      return;
    }
    if (!mounted) return;
    final paired = await showDialog<bool>(
        context: context,
        builder: (_) => AlertDialog(
              backgroundColor: C.bgBottom,
              title: const Text('TV se jodiye'),
              content: const Text('1. "Phone dikhaiye" dabaiye (2 minute ke liye phone dikhega).\n'
                  '2. TV par Settings > Bluetooth / Remotes & accessories > Add device kholiye.\n'
                  '3. "Santosh Remote" chuniye.\n4. Ho jaye to "Test" dabaiye.'),
              actions: [
                TextButton(onPressed: () => Native.homeDiscoverable(), child: const Text('Phone dikhaiye')),
                TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Test')),
              ],
            ));
    if (paired == true) await _tvTest(d);
  }

  Future<void> _tvTest(Map<String, dynamic> d) async {
    try {
      final t = await app.api!.homeTvTest(d['id'] as String);
      final err = await _runOnPhone(Map<String, dynamic>.from(t['device_action'] as Map));
      _snack(err ?? 'TV ki awaaz upar-neeche hui? To TV jud gaya. Ab boliye: "TV pe YouTube chalao".');
    } catch (e) {
      _snack(_clean(e));
    }
  }

  // ---------------------------------------------------------------- brand accounts
  Future<void> _link(Map<String, dynamic> l) async {
    final provider = l['provider'] as String;
    await _guard(() async {
      final r = await app.api!.homeLinkStart(provider);
      if (provider == 'lg_thinq') {
        if (mounted) await _lgToken(r['url'] as String? ?? '');
        return;
      }
      final res = await Native.openExternal(url: r['url'] as String);
      if (res != 'ok') _snack(res);
    });
  }

  /// LG ThinQ: the personal access token is typed here, never in chat. The server stores it encrypted.
  Future<void> _lgToken(String url) async {
    final tok = TextEditingController();
    final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
              backgroundColor: C.bgBottom,
              title: const Text('LG ThinQ token'),
              content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('LG ki site par sign in karke "Personal Access Token" banaiye (device permission ke saath), '
                    'phir yahan paste kijiye. Chat mein kabhi mat bhejiye.', style: TextStyle(color: C.muted, fontSize: 13)),
                const SizedBox(height: 8),
                if (url.isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: url), child: const Text('LG token page kholiye')),
                TextField(controller: tok, obscureText: true, decoration: const InputDecoration(labelText: 'Token')),
              ]),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne dijiye')),
                TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodiye')),
              ],
            ));
    if (ok != true || tok.text.trim().isEmpty) return;
    final r = await app.api!.homeLinkLg(tok.text.trim());
    _snack(r['message'] as String? ?? 'LG ThinQ jud gaya');
    await _load(quiet: true);
  }

  Future<void> _unlink(Map<String, dynamic> l) async => _guard(() async {
        await app.api!.homeUnlink(l['provider'] as String);
        await _load(quiet: true);
      });

  Future<void> _sync() async => _guard(() async {
        await app.api!.homeSync();
        await _load(quiet: true);
        _snack('Appliances refresh ho gaye');
      });

  Future<void> _remove(Map<String, dynamic> d) async => _guard(() async {
        await app.api!.homeRemove(d['id'] as String);
        await _load(quiet: true);
      });

  // ---------------------------------------------------------------- UI
  IconData _icon(String? kind) => switch (kind) {
        'speaker' => Icons.speaker_rounded,
        'tv' => Icons.tv_rounded,
        'ac' => Icons.ac_unit_rounded,
        'fridge' => Icons.kitchen_rounded,
        'washer' => Icons.local_laundry_service_rounded,
        _ => Icons.devices_other_rounded,
      };

  String _status(Map<String, dynamic> d) {
    if (d['channel'] == 'cloud') {
      final ro = d['kind'] == 'fridge' || d['kind'] == 'washer';
      return '${d['brand'] ?? ''} account se · ${ro ? 'sirf dekh sakte hain (safety)' : 'chala sakte hain'}';
    }
    if (d['kind'] == 'ac') {
      if (d['ready'] != true) return 'Remote test baaki hai';
      final s = Map<String, dynamic>.from(d['last_set'] as Map? ?? const {});
      return s['power'] == true ? 'Aakhri baar: ${s['mode']} ${s['temp_c']}°C (IR ulta nahi padhta)' : 'Aakhri baar: band';
    }
    if (d['kind'] == 'tv') {
      final t = Map<String, dynamic>.from(d['target'] as Map? ?? const {});
      return t['bt_address'] != null ? 'Bluetooth: ${t['bt_address']}' : 'Bluetooth se "Santosh Remote" jodiye';
    }
    return 'Phone ki awaaz / Bluetooth speaker';
  }

  Widget _deviceCard(Map<String, dynamic> d) {
    final local = d['channel'] != 'cloud';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        radius: 18,
        padding: const EdgeInsets.fromLTRB(14, 10, 4, 10),
        child: Row(children: [
          Icon(_icon(d['kind'] as String?), color: C.accentSoft),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${d['name']}${(d['room'] as String? ?? '').isEmpty ? '' : ' · ${d['room']}'}',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
              Text(_status(d), style: TextStyle(fontSize: 12, color: d['kind'] == 'ac' && d['ready'] != true ? C.warn : C.faint)),
            ]),
          ),
          if (local)
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert_rounded, color: C.muted),
              onSelected: (v) async {
                if (v == 'test' && d['kind'] == 'ac') await _acSetup(d, const []);
                if (v == 'test' && d['kind'] == 'tv') await _tvSetup(d);
                if (v == 'remove') await _remove(d);
                await _load(quiet: true);
              },
              itemBuilder: (_) => [
                if (d['kind'] == 'ac' || d['kind'] == 'tv') const PopupMenuItem(value: 'test', child: Text('Remote test / jodiye')),
                const PopupMenuItem(value: 'remove', child: Text('Hataiye')),
              ],
            ),
        ]),
      ),
    );
  }

  Widget _linkRow(Map<String, dynamic> l) {
    final linked = l['linked'] == true;
    final configured = l['configured'] != false;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Icon(linked ? Icons.check_circle_rounded : Icons.link_rounded, color: linked ? C.ok : C.muted, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(l['name'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(linked ? 'Juda hai' : (configured ? 'Fridge, washing machine, AC (brand ka account)' : 'Server par abhi chalu nahi'),
                style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ]),
        ),
        if (linked)
          TextButton(onPressed: _busy ? null : () => _unlink(l), child: const Text('Hataiye'))
        else
          TextButton(onPressed: _busy || !configured ? null : () => _link(l),
              child: Text(l['token_in_app'] == true ? 'Token daaliye' : 'Jodiye')),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final remoteOn = _caps['remote_on'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('Ghar'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Ghar ke device', style: display(20)),
                const SizedBox(height: 6),
                const Text('Phone se AC (IR), TV (Bluetooth remote) aur speaker chalaiye. Phir boliye: '
                    '"Bedroom AC 24 pe karo", "TV ki awaaz kam karo", "Arijit ke gaane chalao".',
                    style: TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
                const SizedBox(height: 8),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  Pill(_caps['ir'] == true ? 'IR blaster: hai' : 'IR blaster: nahi', fg: _caps['ir'] == true ? C.ok : C.faint),
                  Pill(_caps['bluetooth_on'] == true ? 'Bluetooth: on' : 'Bluetooth: off', fg: _caps['bluetooth_on'] == true ? C.ok : C.faint),
                  if (remoteOn) const Pill('TV remote: chalu', fg: C.ok),
                ]),
              ]),
            ),
            const SizedBox(height: 14),
            Row(children: [
              Expanded(child: GlassButton(label: 'AC', icon: Icons.ac_unit_rounded, height: 44, onTap: _busy ? null : () => _add('ac'))),
              const SizedBox(width: 8),
              Expanded(child: GlassButton(label: 'TV', icon: Icons.tv_rounded, height: 44, onTap: _busy ? null : () => _add('tv'))),
              const SizedBox(width: 8),
              Expanded(child: GlassButton(label: 'Speaker', icon: Icons.speaker_rounded, height: 44, onTap: _busy ? null : () => _add('speaker'))),
            ]),
            const SizedBox(height: 16),
            const Caption('MERE DEVICE'),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded && _devices.isEmpty)
              const Padding(padding: EdgeInsets.all(12), child: Text('Abhi koi device nahi. Upar se jodiye.', style: TextStyle(color: C.faint))),
            for (final d in _devices) _deviceCard(d),
            if (_devices.any((d) => d['kind'] == 'tv'))
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('TV remote background mein chalu rakhein'),
                subtitle: const Text('App band ho tab bhi TV "Santosh Remote" se juda rahe', style: TextStyle(fontSize: 12, color: C.faint)),
                value: remoteOn,
                onChanged: (v) async {
                  final r = await Native.homeRemote(v);
                  if (r != 'ok') _snack(r == 'permission' ? '"Nearby devices" ki permission dijiye.' : r);
                  await _load(quiet: true);
                },
              ),
            const SizedBox(height: 14),
            const Caption('BRAND ACCOUNT (FRIDGE, WASHING MACHINE, AC)'),
            Glass(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              child: Column(children: [
                for (final l in _links) _linkRow(l),
                if (_links.any((l) => l['linked'] == true))
                  Align(alignment: Alignment.centerRight, child: TextButton(onPressed: _busy ? null : _sync, child: const Text('Refresh'))),
              ]),
            ),
            const SizedBox(height: 12),
            const Text('Suraksha: AC hamesha 20–28°C (default 24°C). Fridge aur washing machine sirf dekhe jaate hain, '
                'chalu/band nahi hote. Geyser abhi nahi (16A smart plug aur auto-off timer ke bina nahi).',
                style: TextStyle(color: C.faint, fontSize: 11.5, height: 1.4)),
          ]),
        ),
      ),
    );
  }
}
