import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.92 Hoola Jaanch: every part of Hoola checked live (about 10 s), what is broken with its fix in plain words,
/// and the last 14 days of real work (tasks, website jobs, crashes).
class JaanchScreen extends StatefulWidget {
  const JaanchScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<JaanchScreen> createState() => _JaanchScreenState();
}

class _JaanchScreenState extends State<JaanchScreen> {
  Map<String, dynamic>? _r;
  String? _err;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      _r = await widget.app.api!.jaanch();
    } catch (e) {
      _err = e.toString();
    }
    if (mounted) setState(() => _busy = false);
  }

  Color _col(dynamic ok) => ok == true ? C.ok : (ok == false ? C.bad : C.warn);
  IconData _ico(dynamic ok) => ok == true ? Icons.check_circle_rounded : (ok == false ? Icons.error_rounded : Icons.info_rounded);

  Widget _check(Map<String, dynamic> c) {
    final fix = '${c['fix'] ?? ''}';
    final detail = '${c['detail'] ?? ''}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        radius: 16,
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(_ico(c['ok']), color: _col(c['ok']), size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${c['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
              if (detail.isNotEmpty) Text(detail, style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (fix.isNotEmpty && c['ok'] != true)
                Padding(
                  padding: const EdgeInsets.only(top: 3),
                  child: Text('Kya karein: $fix', style: TextStyle(color: _col(c['ok']), fontSize: 12.5)),
                ),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _section(String title, List<Widget> kids) => Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 8),
          ...kids,
        ]),
      );

  String _counts(Map? m) {
    if (m == null || m.isEmpty) return '-';
    return m.entries.map((e) => '${e.key} ${e.value}').join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final checks = List<Map<String, dynamic>>.from(((r?['checks'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final sites = checks.where((c) => '${c['id']}'.startsWith('site:')).toList();
    final parts = checks.where((c) => !'${c['id']}'.startsWith('site:')).toList()
      ..sort((a, b) => (a['ok'] == false ? 0 : a['ok'] == null ? 1 : 2).compareTo(b['ok'] == false ? 0 : b['ok'] == null ? 1 : 2));
    final rep = Map<String, dynamic>.from((r?['report'] as Map?) ?? const {});
    final chat = Map<String, dynamic>.from((rep['chat'] as Map?) ?? const {});
    final web = Map<String, dynamic>.from((rep['website'] as Map?) ?? const {});
    final notDone = List<Map>.from((web['not_done'] as List?) ?? const []);
    return Scaffold(
      appBar: AppBar(title: Text('${widget.app.aName} Jaanch'), actions: [
        IconButton(onPressed: _busy ? null : _run, icon: const Icon(Icons.refresh_rounded)),
      ]),
      body: _busy && r == null
          ? const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
              CircularProgressIndicator(),
              SizedBox(height: 12),
              Text('Har hissa jaanch raha hoon (10 second)…', style: TextStyle(color: C.muted)),
            ]))
          : _err != null && r == null
              ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_err!, style: const TextStyle(color: C.bad))))
              : RefreshIndicator(
                  onRefresh: _run,
                  child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
                    Glass(
                      padding: const EdgeInsets.all(14),
                      child: Row(children: [
                        Icon((r?['bad'] ?? 0) == 0 ? Icons.verified_rounded : Icons.build_circle_rounded,
                            color: (r?['bad'] ?? 0) == 0 ? C.ok : C.bad, size: 30),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${r?['ok'] ?? 0} / ${r?['total'] ?? 0} theek', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
                            Text('${r?['say'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                          ]),
                        ),
                      ]),
                    ),
                    _section('Hoola ke hisse', parts.map(_check).toList()),
                    _section('Websites: server se khulti hain?', [
                      const Padding(
                        padding: EdgeInsets.only(bottom: 8),
                        child: Text('Jo server se nahi khultin, unka kaam apne aap aapke PC par chalega (Santosh Desktop khula ho to).',
                            style: TextStyle(color: C.faint, fontSize: 12)),
                      ),
                      ...sites.map(_check),
                    ]),
                    _section('Pichhle ${rep['days'] ?? 14} din ka kaam', [
                      Glass(
                        radius: 16,
                        padding: const EdgeInsets.all(12),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('Chat ke kaam: ${chat['total'] ?? 0}  (${_counts(chat['outcomes'] as Map?)})'),
                          Text('Website ke kaam: ${web['total'] ?? 0}  (${_counts(web['status'] as Map?)})'),
                          Text('App crash: ${rep['crashes'] ?? 0}'),
                          if ((chat['avg_seconds'] ?? 0) != 0) Text('Ek kaam mein ausat: ${chat['avg_seconds']} second'),
                        ]),
                      ),
                      for (final o in notDone.take(6))
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text('• [${o['status']}] ${o['task']}\n   ${o['why'] ?? ''}',
                              style: const TextStyle(color: C.muted, fontSize: 12.5)),
                        ),
                    ]),
                  ]),
                ),
    );
  }
}
