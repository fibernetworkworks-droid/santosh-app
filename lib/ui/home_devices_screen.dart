import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'bluetooth_panel.dart';
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
      res = 'Allow the "Nearby devices" permission, then try again.';
    }
    final ok = res == 'ok';
    final id = action['command_id'] as String?;
    if (id != null) {
      try {
        await app.api!.homeResult(id, ok, ok ? '' : res);   // the code goes to the server; the words to the owner
      } catch (_) {}
    }
    return ok ? null : btWhy(res);
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
                title: const Text('IR blaster not found'),
                content: const Text('To run an AC, the phone needs an IR blaster (Redmi, POCO, iQOO, some OnePlus/Realme). '
                    'This phone does not seem to have one. For a Samsung/LG AC, connect the brand account below.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('OK')),
                  TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Connect anyway')),
                ],
              ));
      if (go != true) return;
    }
    List<Map<String, dynamic>> paired = const [];
    if (kind == 'tv') {
      if (_caps['tv_remote'] != true) {
        _snack('A TV remote needs Android 9+ and Bluetooth.');
        return;
      }
      if (!await Native.homeAskBluetooth()) {
        _snack('Allow the "Nearby devices" permission, then tap "Connect TV" again.');
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
          title: Text({'speaker': 'Connect speaker', 'tv': 'Connect TV', 'ac': 'Connect AC'}[kind]!),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Name (for example Bedroom AC)')),
              TextField(controller: room, decoration: const InputDecoration(labelText: 'Room (optional)')),
              if (kind == 'ac') TextField(controller: brand, decoration: const InputDecoration(labelText: 'Brand (LG, Midea, Voltas…)')),
              if (kind == 'speaker')
                const Padding(
                  padding: EdgeInsets.only(top: 10),
                  child: Text('First pair the speaker in the phone\'s Bluetooth settings. Hoola never raises the volume above 90%.',
                      style: TextStyle(color: C.muted, fontSize: 12.5)),
                ),
              if (kind == 'tv') ...[
                const SizedBox(height: 10),
                const Text('Choose a TV paired with the phone (if first time, connect it later):', style: TextStyle(color: C.muted, fontSize: 12.5)),
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
                    decoration: const InputDecoration(labelText: 'TV Wi-Fi IP (optional, for example 192.168.1.20)')),
              ],
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Leave it')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Connect')),
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
                content: Text('Hold the top of the phone towards the AC (within 2-3 metres), then tap "Send".\n'
                    'Hoola will send "Cool 24°C". (${p['label']})'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Later')),
                  TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Send')),
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
                title: const Text('Did the AC beep?'),
                content: const Text('Did the AC turn on and show 24°C?'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('No')),
                  TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Yes')),
                ],
              ));
      if (beeped == true) {
        final r = await app.api!.homeIrConfirm(d['id'] as String, p['protocol'] as String);
        _snack(r['message'] as String? ?? 'AC is ready');
        return;
      }
    }
    _snack('Hoola does not understand this AC\'s remote yet. For a Samsung/LG AC, connect the brand account.');
  }

  List<Map> _protocols() => const [
        {'protocol': 'coolix', 'label': 'Midea family'},
        {'protocol': 'lg2_ac', 'label': 'LG inverter'},
        {'protocol': 'lg_ac', 'label': 'LG classic'},
      ];

  // ---------------------------------------------------------------- TV remote
  /// Pairs the TV with Hoola's Bluetooth remote: the phone connects to an already-paired TV itself; otherwise it
  /// becomes visible and the TV adds it (the TV shows the phone's own Bluetooth name, which we display).
  Future<void> _tvSetup(Map<String, dynamic> d) async {
    final r = await Native.homeRemote(true);
    if (r != 'ok') {
      _snack(r == 'permission' ? 'Allow the "Nearby devices" permission.' : r);
      return;
    }
    final t = Map<String, dynamic>.from(d['target'] as Map? ?? const {});
    final res = await Native.btRun('tv_pair', {if (t['bt_address'] != null) 'address': t['bt_address']});
    if (!mounted) return;
    final out = Map<String, dynamic>.from(res['result'] as Map? ?? const {});
    if (res['ok'] != true) {
      final e = res['error'] as String? ?? '';
      _snack(e == 'permission' ? 'Allow the "Nearby devices" permission.' : e == 'bluetooth_off' ? 'Turn on Bluetooth first.' : e);
      return;
    }
    if (out['connected'] == true) {
      await _tvTest(d);
      return;
    }
    await showTvPairHelp(context, out['phone_name'] as String? ?? '');
    if (!mounted) return;
    final test = await showDialog<bool>(
        context: context,
        builder: (_) => AlertDialog(
              backgroundColor: C.bgBottom,
              title: const Text('Connected to the TV?'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Later')),
                TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Test')),
              ],
            ));
    if (test == true) await _tvTest(d);
  }

  Future<void> _tvTest(Map<String, dynamic> d) async {
    try {
      final t = await app.api!.homeTvTest(d['id'] as String);
      final err = await _runOnPhone(Map<String, dynamic>.from(t['device_action'] as Map));
      _snack(err ?? 'Did the TV volume go up and down? Then the TV is connected. Now say: "Play YouTube on the TV".');
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
                const Text('Sign in on LG\'s site and create a "Personal Access Token" (with device permission), '
                    'then paste it here. Never send it in chat.', style: TextStyle(color: C.muted, fontSize: 13)),
                const SizedBox(height: 8),
                if (url.isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: url), child: const Text('Open LG token page')),
                TextField(controller: tok, obscureText: true, decoration: const InputDecoration(labelText: 'Token')),
              ]),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Leave it')),
                TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Connect')),
              ],
            ));
    if (ok != true || tok.text.trim().isEmpty) return;
    final r = await app.api!.homeLinkLg(tok.text.trim());
    _snack(r['message'] as String? ?? 'LG ThinQ connected');
    await _load(quiet: true);
  }

  Future<void> _unlink(Map<String, dynamic> l) async => _guard(() async {
        await app.api!.homeUnlink(l['provider'] as String);
        await _load(quiet: true);
      });

  Future<void> _sync() async => _guard(() async {
        await app.api!.homeSync();
        await _load(quiet: true);
        _snack('Appliances refreshed');
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
      return '${d['brand'] ?? ''} account · ${ro ? 'view only (for safety)' : 'can be operated'}';
    }
    if (d['kind'] == 'ac') {
      if (d['ready'] != true) return 'Remote test pending';
      final s = Map<String, dynamic>.from(d['last_set'] as Map? ?? const {});
      return s['power'] == true ? 'Last time: ${s['mode']} ${s['temp_c']}°C (IR does not read back)' : 'Last time: off';
    }
    if (d['kind'] == 'tv') {
      final t = Map<String, dynamic>.from(d['target'] as Map? ?? const {});
      if (t['bt_address'] != null) return 'Bluetooth: ${t['bt_address']}';
      return _caps['tv_saved'] == true ? 'Connected to Hoola remote' : 'Tap Menu > "Remote test / connect"';
    }
    return 'Phone volume / Bluetooth speaker';
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
                if (d['kind'] == 'ac' || d['kind'] == 'tv') const PopupMenuItem(value: 'test', child: Text('Remote test / connect')),
                const PopupMenuItem(value: 'remove', child: Text('Remove')),
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
            Text(linked ? 'Connected' : (configured ? 'Fridge, washing machine, AC (brand account)' : 'Not running on the server yet'),
                style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ]),
        ),
        if (linked)
          TextButton(onPressed: _busy ? null : () => _unlink(l), child: const Text('Remove'))
        else
          TextButton(onPressed: _busy || !configured ? null : () => _link(l),
              child: Text(l['token_in_app'] == true ? 'Enter token' : 'Connect')),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final remoteOn = _caps['remote_on'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('Home'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Home devices', style: display(20)),
                const SizedBox(height: 6),
                const Text('Control an AC (IR), TV (Bluetooth remote) and speaker from the phone. Then say: '
                    '"Set the Bedroom AC to 24", "Turn the TV volume down", "Play Arijit\'s songs".',
                    style: TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
                const SizedBox(height: 8),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  Pill(_caps['ir'] == true ? 'IR blaster: yes' : 'IR blaster: no', fg: _caps['ir'] == true ? C.ok : C.faint),
                  Pill(_caps['bluetooth_on'] == true ? 'Bluetooth: on' : 'Bluetooth: off', fg: _caps['bluetooth_on'] == true ? C.ok : C.faint),
                  if (remoteOn) const Pill('TV remote: on', fg: C.ok),
                ]),
              ]),
            ),
            const SizedBox(height: 14),
            BluetoothPanel(onTvConnected: () async {
              if (!_devices.any((d) => d['kind'] == 'tv')) {
                try {
                  await app.api!.homeAdd('tv', 'TV');
                } catch (_) {}
              }
              await _load(quiet: true);
            }),
            const SizedBox(height: 14),
            Row(children: [
              Expanded(child: GlassButton(label: 'AC', icon: Icons.ac_unit_rounded, height: 44, onTap: _busy ? null : () => _add('ac'))),
              const SizedBox(width: 8),
              Expanded(child: GlassButton(label: 'TV', icon: Icons.tv_rounded, height: 44, onTap: _busy ? null : () => _add('tv'))),
              const SizedBox(width: 8),
              Expanded(child: GlassButton(label: 'Speaker', icon: Icons.speaker_rounded, height: 44, onTap: _busy ? null : () => _add('speaker'))),
            ]),
            const SizedBox(height: 16),
            const Caption('MY DEVICES'),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded && _devices.isEmpty)
              const Padding(padding: EdgeInsets.all(12), child: Text('No devices yet. Connect one from above.', style: TextStyle(color: C.faint))),
            for (final d in _devices) _deviceCard(d),
            if (_devices.any((d) => d['kind'] == 'tv'))
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Keep the TV remote running in the background'),
                subtitle: const Text('The TV stays connected to the Hoola remote even when the app is closed', style: TextStyle(fontSize: 12, color: C.faint)),
                value: remoteOn,
                onChanged: (v) async {
                  final r = await Native.homeRemote(v);
                  if (r != 'ok') _snack(r == 'permission' ? 'Allow the "Nearby devices" permission.' : r);
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
            const Text('Safety: the AC is always 20–28°C (default 24°C). The fridge and washing machine are view-only, '
                'never turned on/off. No geyser for now (not without a 16A smart plug and an auto-off timer).',
                style: TextStyle(color: C.faint, fontSize: 11.5, height: 1.4)),
          ]),
        ),
      ),
    );
  }
}
