import 'dart:async';

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

String _ago(String? iso) {
  final t = DateTime.tryParse(iso ?? '')?.toLocal();
  if (t == null) return 'kabhi nahi';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'abhi';
  if (d.inHours < 1) return '${d.inMinutes} min pehle';
  if (d.inDays < 1) return '${d.inHours} ghante pehle';
  return '${d.inDays} din pehle';
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
        Text('Hoola ka apna computer', style: display(20)),
        const SizedBox(height: 6),
        const Text('Yeh HOOLA ka apna PC hai — apne container mein, cloud mein, hamesha on. '
            'Hoola isi par khud kaam karta hai: Chrome chalata hai, files sambhalta hai, software khud install karta hai.',
            style: TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: C.chip.withOpacity(0.35), borderRadius: BorderRadius.circular(12)),
          child: const Row(children: [
            Icon(Icons.info_outline_rounded, size: 18, color: C.accentSoft),
            SizedBox(width: 8),
            Expanded(child: Text('Yeh aapka personal PC NAHI hai. Aapka apna computer "Mera PC" section mein juda hota hai — dono alag-alag hain.',
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
                ? 'Online · ${d['os'] ?? ''} · hamesha on, khud dobara judta hai'
                : 'Offline · aakhri baar ${_ago(d['last_seen'] as String?)}. Hoola ise khud dobara chalayega.',
            style: TextStyle(color: online ? C.ok : C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        Text('Is par Hoola kaam karta hai: Chrome, files, software install. Kaam ki baatein chat mein dikhti hain.',
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
        const Text('Abhi juda nahi hai. Hoola apne PC ko khud jodta hai — jaise hi judaega, yahan dikhega.',
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
              const Caption('HOOLA NE APNE PC PAR KYA KIYA'),
              Glass(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                child: Column(children: [
                  if (_jobs.isEmpty) const Padding(padding: EdgeInsets.all(10), child: Text('Abhi tak kuch nahi', style: TextStyle(color: C.faint))),
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
