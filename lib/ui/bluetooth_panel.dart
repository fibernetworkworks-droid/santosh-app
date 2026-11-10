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
      _snack('Nothing new found. Put the device in pairing mode (hold the Bluetooth button until the light blinks).');
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
        _snack('TV connected! Now say: "turn up the TV volume", "open YouTube on the TV".');
        widget.onTvConnected?.call();
      } else {
        await tvHelp(context, res['phone_name'] as String? ?? '');
      }
    } else if (action == 'pair') {
      _snack(res['paired'] == true ? '${d['name']} connected.' : 'Press "Pair" on the Android dialog.');
    } else if (action == 'connect') {
      _snack(res['connected'] == true ? '${d['name']} connected.' : 'Tap ${d['name']} once in Bluetooth settings.');
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
            Text(connected ? (d['remote_host'] == true ? 'Linked with Hoola remote' : 'Connected') : (nearby ? 'Nearby' : 'Paired'),
                style: TextStyle(fontSize: 11.5, color: connected ? C.ok : C.faint)),
          ]),
        ),
        if (busy)
          const Padding(padding: EdgeInsets.all(10), child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)))
        else if (tv && !(connected && d['remote_host'] == true))
          TextButton(onPressed: _busy != null ? null : () => _do('tv_pair', d), child: const Text('Set up TV remote'))
        else if (nearby)
          TextButton(onPressed: _busy != null ? null : () => _do('pair', d), child: const Text('Add'))
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
            TextButton(onPressed: () async { await Native.homeAskBluetooth(); await refresh(); }, child: const Text('Give permission'))
          else if (!on)
            TextButton(onPressed: _turnOn, child: const Text('Turn on'))
          else
            TextButton(onPressed: _scanning ? null : _scan, child: Text(_scanning ? 'Searching…' : 'Search nearby')),
        ]),
        const Text('Speakers, earbuds, TV — Hoola can connect and control them. Say: "connect the boAt speaker",'
            '"connect the TV by Bluetooth", "turn up the TV volume".', style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
        if (_scanning) const Padding(padding: EdgeInsets.only(top: 10), child: LinearProgressIndicator(minHeight: 2)),
        if (_nearby.isNotEmpty) ...[
          const SizedBox(height: 10),
          const Caption('NEARBY'),
          for (final d in _nearby.take(12)) _row(d, nearby: true),
        ],
        if (_paired.isNotEmpty) ...[
          const SizedBox(height: 10),
          const Caption('LINKED DEVICES'),
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
                        _snack('TV connected!');
                        widget.onTvConnected?.call();
                      } else {
                        await tvHelp(context, res['phone_name'] as String? ?? '');
                      }
                      await refresh();
                    },
              child: const Text('TV not in the list? Pair the phone with the TV'),
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
        title: const Text('Pair the phone with the TV'),
        content: Text('The phone is visible for 2 minutes.\n\n'
            '1. On the TV open Settings > Bluetooth / Remotes & accessories > "Add accessory".\n'
            '2. Choose "${phoneName.isEmpty ? 'your phone name' : phoneName}" in the list.\n'
            '3. If the code is the same on both, press "Pair".\n\n'
            'When done, press Home > TV > "Remote test".'),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK'))],
      ),
    );

/// Plain words for the phone's Bluetooth / TV-remote error codes.
String btWhy(String err) => switch (err) {
      'permission' => 'Give the "Nearby devices" permission, then press again.',
      'bluetooth_off' => 'Bluetooth is off. Turn Bluetooth on first.',
      'not_found' => 'Device not found. Put it in pairing mode and search again.',
      'needs_screen' => 'Keep the Hoola app open.',
      'tv_not_paired' => 'No TV is paired with the phone yet. Press "Set up TV remote" in Home > Bluetooth.',
      'tv_not_reachable' => 'The TV is paired but did not respond. Turn the TV on and keep the phone close, then try again.',
      'remote_not_ready' => 'The Bluetooth remote did not start. Turn Bluetooth off and on once.',
      'link_dropped' => 'The TV dropped the Bluetooth link. Keep the phone near the TV and try again.',
      'boot_protocol' => 'This TV accepts only arrows, OK and numbers over Bluetooth; volume and Home are on the TV\'s own remote.',
      _ => err,
    };
