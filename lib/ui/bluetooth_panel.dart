import 'package:flutter/material.dart';

import '../native.dart';
import 'glass.dart';

/// Ghar > Bluetooth: what the phone is connected to, a nearby scan, pairing, and making the phone the TV's remote.
/// The same jobs Hoola runs when you say "speaker jodo" or "TV ko Bluetooth se jodo".
class BluetoothPanel extends StatefulWidget {
  const BluetoothPanel({super.key, this.onTvConnected});
  final VoidCallback? onTvConnected;
  @override
  State<BluetoothPanel> createState() => _BluetoothPanelState();
}

class _BluetoothPanelState extends State<BluetoothPanel> {
  Map<String, dynamic> _status = const {};
  List<Map<String, dynamic>> _paired = [];
  List<Map<String, dynamic>> _nearby = [];
  bool _scanning = false;
  String? _busy;

  @override
  void initState() {
    super.initState();
    refresh();
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  List<Map<String, dynamic>> _list(dynamic x) =>
      (x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  String _why(String err) => btWhy(err);

  Future<void> refresh() async {
    final s = await Native.btRun('status');
    final d = await Native.btRun('devices');
    if (!mounted) return;
    setState(() {
      _status = Map<String, dynamic>.from(s['result'] as Map? ?? const {});
      _paired = d['ok'] == true ? _list((d['result'] as Map)['devices']) : [];
    });
  }

  Future<void> _turnOn() async {
    final r = await Native.btRun('turn_on');
    if (r['ok'] != true) _snack(_why(r['error'] as String));
    await Future<void>.delayed(const Duration(seconds: 2));
    await refresh();
  }

  Future<void> _scan() async {
    if (_scanning) return;
    setState(() {
      _scanning = true;
      _nearby = [];
    });
    final r = await Native.btRun('scan');
    if (!mounted) return;
    setState(() {
      _scanning = false;
      if (r['ok'] == true) _nearby = _list((r['result'] as Map)['devices']).where((d) => d['paired'] != true).toList();
    });
    if (r['ok'] != true) {
      _snack(_why(r['error'] as String));
    } else if (_nearby.isEmpty) {
      _snack('Kuch naya nahi mila. Device ko pairing mode mein rakhiye (Bluetooth button dabaye rakhiye jab tak light blink kare).');
    }
  }

  Future<void> _do(String action, Map<String, dynamic> d) async {
    setState(() => _busy = d['address'] as String?);
    final r = await Native.btRun(action, {'address': d['address'], 'device': d['name']});
    if (!mounted) return;
    setState(() => _busy = null);
    final res = Map<String, dynamic>.from(r['result'] as Map? ?? const {});
    if (r['ok'] != true) {
      _snack(_why(r['error'] as String));
    } else if (action == 'tv_pair') {
      if (res['connected'] == true) {
        _snack('TV jud gaya! Ab boliye: "TV ki awaaz badhao", "TV pe YouTube kholo".');
        widget.onTvConnected?.call();
      } else {
        await tvHelp(context, res['phone_name'] as String? ?? '');
      }
    } else if (action == 'pair') {
      _snack(res['paired'] == true ? '${d['name']} jud gaya.' : 'Android ke dialog par "Pair" dabaiye.');
    } else if (action == 'connect') {
      _snack(res['connected'] == true ? '${d['name']} connect ho gaya.' : 'Bluetooth settings mein ${d['name']} par ek baar tap kijiye.');
    }
    await refresh();
    if (!mounted) return;
    setState(() => _nearby.removeWhere((x) => x['address'] == d['address'] && (res['paired'] == true || res['connected'] == true)));
  }

  Future<void> tvHelp(BuildContext context, String phoneName) => showTvPairHelp(context, phoneName);

  IconData _icon(String? k) => switch (k) {
        'tv' => Icons.tv_rounded,
        'speaker' => Icons.speaker_rounded,
        'headphones' => Icons.headphones_rounded,
        'car' => Icons.directions_car_rounded,
        'watch' => Icons.watch_rounded,
        'computer' => Icons.laptop_rounded,
        'phone' => Icons.smartphone_rounded,
        'keyboard' => Icons.keyboard_rounded,
        'mouse' => Icons.mouse_rounded,
        'gamepad' => Icons.sports_esports_rounded,
        'light' => Icons.lightbulb_rounded,
        _ => Icons.bluetooth_rounded,
      };

  Widget _row(Map<String, dynamic> d, {required bool nearby}) {
    final tv = d['kind'] == 'tv';
    final busy = _busy == d['address'];
    final connected = d['connected'] == true;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(children: [
        Icon(_icon(d['kind'] as String?), color: connected ? C.ok : C.muted, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(d['name'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600)),
            Text(connected ? (d['remote_host'] == true ? 'Hoola remote se juda' : 'Connected') : (nearby ? 'Aas-paas' : 'Paired'),
                style: TextStyle(fontSize: 11.5, color: connected ? C.ok : C.faint)),
          ]),
        ),
        if (busy)
          const Padding(padding: EdgeInsets.all(10), child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)))
        else if (tv && !(connected && d['remote_host'] == true))
          TextButton(onPressed: _busy != null ? null : () => _do('tv_pair', d), child: const Text('TV remote banaiye'))
        else if (nearby)
          TextButton(onPressed: _busy != null ? null : () => _do('pair', d), child: const Text('Jodiye'))
        else if (!connected)
          TextButton(onPressed: _busy != null ? null : () => _do('connect', d), child: const Text('Connect')),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final on = _status['on'] == true;
    final perm = _status['permission'] != false;
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(on ? Icons.bluetooth_connected_rounded : Icons.bluetooth_disabled_rounded, color: on ? C.accentSoft : C.faint),
          const SizedBox(width: 8),
          Expanded(child: Text('Bluetooth', style: display(18))),
          if (!perm)
            TextButton(onPressed: () async { await Native.homeAskBluetooth(); await refresh(); }, child: const Text('Permission dijiye'))
          else if (!on)
            TextButton(onPressed: _turnOn, child: const Text('Chalu kijiye'))
          else
            TextButton(onPressed: _scanning ? null : _scan, child: Text(_scanning ? 'Dhoondh raha hoon…' : 'Aas-paas dhoondhiye')),
        ]),
        const Text('Speaker, earbuds, TV — Hoola jod sakta hai aur chala sakta hai. Boliye: "boAt speaker jodo", '
            '"TV ko Bluetooth se jodo", "TV ki awaaz badhao".', style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
        if (_scanning) const Padding(padding: EdgeInsets.only(top: 10), child: LinearProgressIndicator(minHeight: 2)),
        if (_nearby.isNotEmpty) ...[
          const SizedBox(height: 10),
          const Caption('AAS-PAAS'),
          for (final d in _nearby.take(12)) _row(d, nearby: true),
        ],
        if (_paired.isNotEmpty) ...[
          const SizedBox(height: 10),
          const Caption('JUDE HUE DEVICE'),
          for (final d in _paired.take(12)) _row(d, nearby: false),
        ],
        if (on && perm)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: _busy != null
                  ? null
                  : () async {
                      final r = await Native.btRun('tv_pair');
                      if (!mounted) return;
                      final res = Map<String, dynamic>.from(r['result'] as Map? ?? const {});
                      if (r['ok'] != true) {
                        _snack(_why(r['error'] as String));
                      } else if (res['connected'] == true) {
                        _snack('TV jud gaya!');
                        widget.onTvConnected?.call();
                      } else {
                        await tvHelp(context, res['phone_name'] as String? ?? '');
                      }
                      await refresh();
                    },
              child: const Text('TV list mein nahi? TV se phone jodiye'),
            ),
          ),
      ]),
    );
  }
}

/// How to add the phone from the TV's side, with the name the TV will actually show.
Future<void> showTvPairHelp(BuildContext context, String phoneName) => showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('TV se phone jodiye'),
        content: Text('Phone 2 minute ke liye dikh raha hai.\n\n'
            '1. TV par Settings > Bluetooth / Remotes & accessories > "Add accessory" kholiye.\n'
            '2. List mein "${phoneName.isEmpty ? 'aapke phone ka naam' : phoneName}" chuniye.\n'
            '3. Dono par code same ho to "Pair" dabaiye.\n\n'
            'Ho jaye to Ghar mein TV > "Remote test" dabaiye.'),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Theek hai'))],
      ),
    );

/// Plain words for the phone's Bluetooth / TV-remote error codes.
String btWhy(String err) => switch (err) {
      'permission' => '"Nearby devices" ki permission dijiye, phir dobara dabaiye.',
      'bluetooth_off' => 'Bluetooth band hai. Pehle Bluetooth chalu kijiye.',
      'not_found' => 'Device nahi mila. Use pairing mode mein rakhkar dobara dhoondhiye.',
      'needs_screen' => 'Hoola app khula rakhiye.',
      'tv_not_paired' => 'Abhi koi TV phone se paired nahi hai. Ghar > Bluetooth mein "TV remote banaiye" dabaiye.',
      'tv_not_reachable' => 'TV paired hai par jawab nahi diya. TV chalu kijiye aur phone paas rakhiye, phir dobara.',
      'remote_not_ready' => 'Bluetooth remote shuru nahi hua. Bluetooth ek baar band-chalu kijiye.',
      'link_dropped' => 'TV ne Bluetooth link chhod diya. Phone TV ke paas rakhkar dobara try kijiye.',
      'boot_protocol' => 'Yeh TV Bluetooth se sirf arrows, OK aur number leta hai; awaaz aur Home TV ke remote se.',
      _ => err,
    };
