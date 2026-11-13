/// Profile > Seekhe hue kaam (v0.63): the multi-step jobs Hoola learned to do by itself. Each one is only a hint for
/// the next similar job; the owner can switch one off, rename it, rewrite its steps in her own words, or delete it.
library;

import 'package:flutter/material.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

class ProceduresScreen extends StatefulWidget {
  const ProceduresScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ProceduresScreen> createState() => _ProceduresScreenState();
}

class _ProceduresScreenState extends State<ProceduresScreen> {
  List<Map<String, dynamic>>? _rows;
  Map<String, dynamic>? _tasks;
  List<Map<String, dynamic>> _lessons = const [];
  String? _err;
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await _api.procedures();
      Map<String, dynamic>? t;
      List<Map<String, dynamic>> l = const [];
      try {
        t = await _api.agentTasks();
        l = await _api.agentLessons();
      } catch (_) {}
      if (mounted) setState(() {
        _rows = r;
        _tasks = t;
        _lessons = l;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  void _say(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _toggle(Map<String, dynamic> p, bool on) async {
    try {
      await _api.procedureEdit(p['id'] as String, active: on);
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  Future<void> _edit(Map<String, dynamic> p) async {
    final title = TextEditingController(text: p['title'] as String? ?? '');
    final steps = TextEditingController(
        text: List<Map<String, dynamic>>.from(((p['steps'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)))
            .map((s) => '${s['label']}')
            .join('\n'));
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Edit'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Name')),
            const SizedBox(height: 8),
            TextField(
                controller: steps,
                minLines: 3,
                maxLines: 10,
                decoration: const InputDecoration(labelText: 'Steps (one per line)', helperText: 'In your words; Hoola will do it this way')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _api.procedureEdit(p['id'] as String,
          title: title.text.trim(), steps: steps.text.split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList());
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  Future<void> _delete(Map<String, dynamic> p) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('Forget "${p['title']}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('No')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Forget', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _api.procedureDelete(p['id'] as String);
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;
    final name = widget.app.aName;
    return DeskPage(
      title: 'Learned tasks',
      onRefresh: _load,
      body: () => RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            Glass(
              child: Text(
                  'When $name does a long task (4+ steps) well, it remembers the method here. When similar work comes next time,'
                  'it does it faster this way. Only the steps are remembered, not your details (numbers, names, money).'
                  'A method that fails again and again is turned off by itself.',
                  style: const TextStyle(color: C.chip, height: 1.35, fontSize: 13)),
            ),
            const SizedBox(height: 12),
            if (_tasks != null) _hisaab(_tasks!),
            if (_lessons.isNotEmpty) ...[
              const SizedBox(height: 4),
              const Text('Learned fixes', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              for (final l in _lessons.take(20)) _lesson(l),
              const SizedBox(height: 12),
              const Text('Learned methods', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
            ],
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (rows == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (rows != null && rows.isEmpty)
              Padding(
                padding: const EdgeInsets.all(30),
                child: Center(
                    child: Text('Nothing learned yet. Have $name do a long task, like "make a grocery list and remind me every month".',
                        textAlign: TextAlign.center, style: const TextStyle(color: C.muted))),
              ),
            for (final p in rows ?? const <Map<String, dynamic>>[]) _card(p),
          ]),
        ),
    );
  }

  Widget _hisaab(Map<String, dynamic> t) {
    final sum = Map<String, dynamic>.from((t['summary'] as Map?) ?? const {});
    final tasks = List<Map<String, dynamic>>.from(((t['tasks'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)))
        .where((x) => x['outcome'] != 'talk')
        .toList();
    if (tasks.isEmpty) return const SizedBox.shrink();
    Color col(String o) => o == 'done' ? C.teal : (o == 'partial' ? C.warn : C.bad);
    String word(String o) => const {'done': 'Done', 'partial': 'Incomplete', 'stuck': 'Stuck', 'stopped': 'Stopped'}[o] ?? o;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Work summary', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 4),
          Text(
              '${sum['tasks'] ?? 0} tasks · ${sum['done_pct'] ?? '-'}% completed · ${sum['fixed_on_the_way'] ?? 0} where it got stuck and found a fix by itself',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          for (final x in tasks.take(6))
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(color: col('${x['outcome']}').withOpacity(.18), borderRadius: BorderRadius.circular(8)),
                  child: Text(word('${x['outcome']}'), style: TextStyle(color: col('${x['outcome']}'), fontSize: 11, fontWeight: FontWeight.w700)),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${x['request']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)),
                    if ('${x['left'] ?? ''}'.isNotEmpty)
                      Text('Pending: ${x['left']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.warn, fontSize: 11.5)),
                    Text('${x['steps']} steps · ${x['seconds']} sec${(x['fixes'] as num? ?? 0) > 0 ? ' · ${x['fixes']} fixes' : ''}',
                        style: const TextStyle(color: C.faint, fontSize: 11)),
                  ]),
                ),
              ]),
            ),
        ]),
      ),
    );
  }

  Widget _lesson(Map<String, dynamic> l) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Glass(
          padding: const EdgeInsets.fromLTRB(14, 10, 4, 10),
          child: Row(children: [
            const Icon(Icons.lightbulb_outline_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${l['label']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                Text('Stuck: ${l['problem']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
                Text('Fix: ${l['fix']}', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.teal, fontSize: 12)),
                Text('Helped ${l['helped']} times', style: const TextStyle(color: C.faint, fontSize: 11)),
              ]),
            ),
            IconButton(
                tooltip: 'Forget',
                icon: const Icon(Icons.delete_outline_rounded, size: 19, color: C.muted),
                onPressed: () async {
                  try {
                    await _api.agentLessonDelete('${l['id']}');
                    await _load();
                  } catch (e) {
                    _say('$e');
                  }
                }),
          ]),
        ),
      );

  Widget _card(Map<String, dynamic> p) {
    final steps = List<Map<String, dynamic>>.from(((p['steps'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final watch = List<String>.from(((p['watch_out'] as List?) ?? const []).map((e) => '$e'));
    final on = p['active'] == true;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Opacity(
        opacity: on ? 1 : .55,
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.auto_awesome_rounded, color: C.accent, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text('${p['title']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
              Switch(value: on, onChanged: (v) => _toggle(p, v)),
            ]),
            const SizedBox(height: 6),
            for (final (i, s) in steps.indexed)
              Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Container(
                    width: 20,
                    height: 20,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(color: const Color(0x26FFB15C), borderRadius: BorderRadius.circular(6)),
                    child: Text('${i + 1}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: C.accentSoft)),
                  ),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${s['label']}', style: const TextStyle(fontSize: 13))),
                ]),
              ),
            if (watch.isNotEmpty) ...[
              const SizedBox(height: 4),
              for (final w in watch.take(3))
                Text('Note: $w', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.warn, fontSize: 11.5)),
            ],
            const SizedBox(height: 6),
            Row(children: [
              Expanded(
                child: Text(
                    'Used ${p['uses']} times · worked ${p['wins']} times${(p['fails'] as num? ?? 0) > 0 ? ' · got stuck ${p['fails']} times' : ''}',
                    style: const TextStyle(color: C.faint, fontSize: 11.5)),
              ),
              IconButton(tooltip: 'Edit', icon: const Icon(Icons.edit_rounded, size: 19), onPressed: () => _edit(p)),
              IconButton(tooltip: 'Forget', icon: const Icon(Icons.delete_outline_rounded, size: 19, color: C.muted), onPressed: () => _delete(p)),
            ]),
          ]),
        ),
      ),
    );
  }
}

/// v0.890 a title she typed in capitals ("FROM WHERE THEY EARN MONEY") reads as a sentence on the card; short
/// business words stay capitals (GST, PDF, UPI...). Anything not all-capitals is left exactly as it is.
const _keepCaps = {'GST', 'PDF', 'UPI', 'PAN', 'TDS', 'ITC', 'HSN', 'SEO', 'API', 'URL', 'AI', 'PC', 'ID', 'KYC', 'EMI',
  'CA', 'HR', 'CRM', 'ERP', 'IT', 'USA', 'UK', 'IOS', 'OTP', 'QR', 'SMS', 'B2B', 'B2C', 'MRP', 'FY', 'Q1', 'Q2', 'Q3', 'Q4'};
String sentenceCase(String t) {
  final letters = t.replaceAll(RegExp(r'[^A-Za-z]'), '');
  if (letters.length < 4 || letters != letters.toUpperCase()) return t;
  var first = true;
  return t.replaceAllMapped(RegExp(r'[A-Za-z0-9]+'), (m) {
    final w = m.group(0)!;
    final keep = _keepCaps.contains(w);
    final out = keep ? w : (first ? w[0] + w.substring(1).toLowerCase() : w.toLowerCase());
    first = false;
    return out;
  });
}

/// Chat card: Hoola just learned a way of doing a multi-step job.
class ProcedureLearnedCard extends StatelessWidget {
  const ProcedureLearnedCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Glass(
        padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
        child: Row(children: [
          const Icon(Icons.auto_awesome_rounded, color: C.accent, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(v['event'] == 'lesson' ? '${app.aName} learned how to fix getting stuck' : '${app.aName} learned to do this task', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
              const SizedBox(height: 2),
              Text(sentenceCase('${v['title'] ?? ''}'), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 13)),
            ]),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProceduresScreen(app: app))),
            child: const Text('View'),
          ),
        ]),
      );
}
