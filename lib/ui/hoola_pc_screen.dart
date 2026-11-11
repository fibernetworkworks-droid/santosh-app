import 'dart:async';

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

String _ago(String? iso) {
  final t = DateTime.tryParse(iso ?? '')?.toLocal();
  if (t == null) return 'never';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'just now';
  if (d.inHours < 1) return '${d.inMinutes} min ago';
  if (d.inDays < 1) return '${d.inHours} hrs ago';
  return '${d.inDays} days ago';
}

/// v0.205 HOOLA PC AND MERA PC ARE DIFFERENT SECTIONS: Hoola ka apna PC gets its OWN section —
/// this screen is HOOLA'S OWN computer (its own container in the cloud, hamesha on), completely
/// separate from the "Mera PC" screen, which stays the user's personal PC feature (v0.201 rule).
/// Read-only by design: status + what Hoola did there. No pairing, no search, no file buttons —
/// the Hoola PC is Hoola infrastructure; it pairs itself, the user never pairs it.
class HoolaPcScreen extends StatefulWidget {
  const HoolaPcScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaPcScreen> createState() => _HoolaPcScreenState();
}

class _HoolaPcScreenState extends State<HoolaPcScreen> {
  List<Map<String, dynamic>> _devices = [];
  List<Map<String, dynamic>> _jobs = [];
  String? _err;
  bool _loaded = false;
  Timer? _poll;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 4), (_) => _load(quiet: true));
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _load({bool quiet = false}) async {
    try {
      final r = await Future.wait([app.api!.pcHoolaDevices(), app.api!.pcHoolaJobs()]);
      if (!mounted) return;
      setState(() {
        _devices = r[0];
        _jobs = r[1];
        _loaded = true;
        _err = null;
      });
    } catch (e) {
      if (mounted && !quiet) setState(() => _err = e.toString());
    }
  }

  Widget _introCard() {
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Hoola\'s own computer', style: display(20)),
        const SizedBox(height: 6),
        const Text('This is HOOLA\'s own PC — in its own container, in the cloud, always on. '
            'Hoola works on it by itself: it runs Chrome, handles files and installs software on its own.',
            style: TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: C.chip.withOpacity(0.35), borderRadius: BorderRadius.circular(12)),
          child: const Row(children: [
            Icon(Icons.info_outline_rounded, size: 18, color: C.accentSoft),
            SizedBox(width: 8),
            Expanded(child: Text('This is NOT your personal PC. Your own computer is connected in the "My PC" section — the two are separate.',
                style: TextStyle(fontSize: 12.5, color: C.muted, height: 1.35))),
          ]),
        ),
      ]),
    );
  }

  Widget _deviceCard(Map<String, dynamic> d) {
    final online = d['online'] == true;
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 10, height: 10, decoration: BoxDecoration(shape: BoxShape.circle, color: online ? C.ok : C.faint)),
          const SizedBox(width: 8),
          Expanded(child: Text(d['name'] as String? ?? 'Hoola PC', style: display(18))),
        ]),
        Text(
            online
                ? 'Online · ${d['os'] ?? ''} · always on, reconnects by itself'
                : 'Offline · last seen ${_ago(d['last_seen'] as String?)}. Hoola will start it again by itself.',
            style: TextStyle(color: online ? C.ok : C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        Text('Hoola works on this: Chrome, files, software installs. The work shows in the chat.',
            style: const TextStyle(fontSize: 12, color: C.faint, height: 1.35)),
      ]),
    );
  }

  Widget _notPairedCard() {
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 10, height: 10, decoration: const BoxDecoration(shape: BoxShape.circle, color: C.faint)),
          const SizedBox(width: 8),
          Expanded(child: Text('Hoola PC', style: display(18))),
        ]),
        const Text('Not connected yet. Hoola connects its own PC by itself — it will show here as soon as it connects.',
            style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.4)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola ka PC'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded) ...[
              _introCard(),
              const SizedBox(height: 10),
              if (_devices.isEmpty) _notPairedCard(),
              for (final d in _devices) Padding(padding: const EdgeInsets.only(bottom: 10), child: _deviceCard(d)),
              const SizedBox(height: 14),
              const Caption('WHAT HOOLA DID ON ITS PC'),
              Glass(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                child: Column(children: [
                  if (_jobs.isEmpty) const Padding(padding: EdgeInsets.all(10), child: Text('Nothing yet', style: TextStyle(color: C.faint))),
                  for (final j in _jobs.take(30))
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Icon(j['status'] == 'done' ? Icons.check_circle_rounded : (j['status'] == 'sent' ? Icons.schedule_rounded : Icons.error_outline_rounded),
                            size: 16, color: j['status'] == 'done' ? C.ok : (j['status'] == 'sent' ? C.faint : C.warn)),
                        const SizedBox(width: 8),
                        Expanded(child: Text('${j['summary']}${(j['error'] as String? ?? '').isEmpty ? '' : ' · ${j['error']}'}',
                            style: const TextStyle(fontSize: 12.5))),
                        Text(_ago(j['at'] as String?), style: const TextStyle(color: C.faint, fontSize: 11)),
                      ]),
                    ),
                ]),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}
