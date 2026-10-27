import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// v0.97 Fingerprint se haan: money cards are approved only by this phone's fingerprint (a key in Android Keystore that
/// signs the exact card). Adding a second phone or removing one waits 24 hours unless a set-up phone gives its fingerprint.
class ApproveKeyScreen extends StatefulWidget {
  const ApproveKeyScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ApproveKeyScreen> createState() => _ApproveKeyScreenState();
}

class _ApproveKeyScreenState extends State<ApproveKeyScreen> {
  Map<String, dynamic>? _server;
  Map<String, dynamic> _phone = const {};
  bool _busy = false;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await widget.app.api!.approveKeyStatus();
      final p = await Native.approveKeyInfo();
      if (mounted) setState(() {
        _server = s;
        _phone = p;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  List<Map<String, dynamic>> get _devices =>
      List<Map<String, dynamic>>.from(((_server?['devices'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  Map<String, dynamic>? get _mine {
    final id = '${_phone['device_id'] ?? ''}';
    for (final d in _devices) {
      if (d['device_id'] == id) return d;
    }
    return null;
  }

  bool get _mineActive => _mine?['status'] == 'active' && _phone['has_key'] == true;

  Future<void> _run(Future<void> Function() f) async {
    setState(() => _busy = true);
    try {
      await f();
    } catch (e) {
      _snack('$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _addThisPhone() => _run(() async {
        final k = await Native.approveKeyCreate();
        if (k['public_key'] == null) {
          _snack(switch ('${k['error']}') {
            'no_fingerprint' => 'Pehle phone ki Settings mein fingerprint / face lock lagaiye.',
            'not_supported' => 'Is phone mein yeh suvidha nahi hai (Android 9+ aur fingerprint chahiye). Slide se haan chalta rahega.',
            _ => 'Chaabi nahi ban payi: ${k['error']}',
          });
          return;
        }
        final r = await widget.app.api!.approveKeyAdd('${k['device_id']}', '${k['public_key']}',
            '${_phone['model'] ?? 'Phone'}', k['strongbox'] == true);
        _snack('${r['say'] ?? 'Ho gaya'}');
      });

  Future<void> _remove(Map<String, dynamic> d) => _run(() async {
        Map<String, dynamic>? proof;
        if (_mineActive) {
          proof = await widget.app.api!.fingerprintProof('remove', '${d['device_id']}');
        }
        final r = await widget.app.api!.approveKeyRemove('${d['device_id']}', proof: proof);
        if (d['device_id'] == _phone['device_id'] && r['status'] == 'removed') await Native.approveKeyDelete();
        _snack('${r['say'] ?? 'Ho gaya'}');
      });

  Future<void> _cancel(Map<String, dynamic> d) => _run(() async {
        final r = await widget.app.api!.approveKeyCancel('${d['device_id']}');
        _snack('${r['say'] ?? 'Ho gaya'}');
      });

  String _when(dynamic iso) {
    final t = DateTime.tryParse('${iso ?? ''}')?.toLocal();
    if (t == null) return '';
    return '${t.day}/${t.month} ${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  Widget _device(Map<String, dynamic> d) {
    final me = d['device_id'] == _phone['device_id'];
    final st = '${d['status']}';
    final line = st == 'pending'
        ? 'Naya: ${_when(d['active_after'])} ke baad chalu hoga'
        : d['remove_after'] != null
            ? 'Hat raha hai: ${_when(d['remove_after'])} ke baad'
            : 'Chalu${d['strongbox'] == true ? ' · alag security chip' : ''}${d['last_used'] != null ? ' · aakhri haan ${_when(d['last_used'])}' : ''}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        radius: 16,
        padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
        child: Row(children: [
          Icon(st == 'active' && d['remove_after'] == null ? Icons.verified_user_rounded : Icons.schedule_rounded,
              color: st == 'active' && d['remove_after'] == null ? C.ok : C.warn),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${d['label'] ?? 'Phone'}${me ? ' (yeh phone)' : ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(line, style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ]),
          ),
          if (st == 'pending' || d['remove_after'] != null)
            TextButton(onPressed: _busy ? null : () => _cancel(d), child: const Text('Rok do'))
          else
            TextButton(onPressed: _busy ? null : () => _remove(d), child: const Text('Hatao')),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final on = _server?['on'] == true;
    final supported = _phone['supported'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('Fingerprint se haan')),
      body: _server == null && _err == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
                Glass(
                  padding: const EdgeInsets.all(14),
                  child: Row(children: [
                    Icon(on ? Icons.fingerprint_rounded : Icons.swipe_rounded, color: on ? C.ok : C.warn, size: 34),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(on ? 'Chalu hai' : 'Band hai', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
                        Text('${_server?['say'] ?? _err ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                      ]),
                    ),
                  ]),
                ),
                const SizedBox(height: 12),
                const Text(
                    'Chalu hone par paise wale card (bill, UPI, order, AI video ka kharcha) sirf jude hue phone ke fingerprint se '
                    'haan honge. App ki chaabi chori bhi ho jaye to koi aur haan nahi kar sakta. Naya phone jodna ya hatana 24 '
                    'ghante baad hota hai, jab tak jude hue phone se fingerprint na diya jaye.',
                    style: TextStyle(color: C.faint, fontSize: 12.5)),
                const SizedBox(height: 14),
                ..._devices.map(_device),
                const SizedBox(height: 8),
                if (!supported)
                  const Text('Is phone mein yeh suvidha nahi hai (Android 9+ aur fingerprint / face lock chahiye).',
                      style: TextStyle(color: C.warn))
                else if (!_mineActive && _mine?['status'] != 'pending')
                  GlassButton(
                    label: _phone['enrolled'] == true ? 'Is phone ko jodiye' : 'Pehle phone mein fingerprint lagaiye',
                    icon: Icons.fingerprint_rounded,
                    onTap: _busy || _phone['enrolled'] != true ? null : _addThisPhone,
                  ),
              ]),
            ),
    );
  }
}
