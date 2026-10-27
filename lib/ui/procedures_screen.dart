/// Profile > Seekhe hue kaam (v0.63): the multi-step jobs Hoola learned to do by itself. Each one is only a hint for
/// the next similar job; the owner can switch one off, rename it, rewrite its steps in her own words, or delete it.
library;

import 'package:flutter/material.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';

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
        title: const Text('Badliye'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Naam')),
            const SizedBox(height: 8),
            TextField(
                controller: steps,
                minLines: 3,
                maxLines: 10,
                decoration: const InputDecoration(labelText: 'Kadam (har line ek)', helperText: 'Apne shabdon mein; Hoola isi tarah karega')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
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
        title: Text('"${p['title']}" bhool jayein?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Bhool jao', style: TextStyle(color: C.bad))),
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
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Seekhe hue kaam')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            Glass(
              child: Text(
                  'Jab $name koi lamba kaam (4+ kadam) theek se kar leta hai, woh tarika yahan yaad rakhta hai. Agli baar waisa kaam '
                  'aaye to isi tarike se jaldi karta hai. Sirf kadam yaad rehte hain, aapki details (number, naam, paise) nahi. '
                  'Jo tarika baar baar fail ho, woh apne aap band ho jata hai.',
                  style: const TextStyle(color: C.chip, height: 1.35, fontSize: 13)),
            ),
            const SizedBox(height: 12),
            if (_tasks != null) _hisaab(_tasks!),
            if (_lessons.isNotEmpty) ...[
              const SizedBox(height: 4),
              const Text('Seekhe hue hal', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              for (final l in _lessons.take(20)) _lesson(l),
              const SizedBox(height: 12),
              const Text('Seekhe hue tarike', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
            ],
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (rows == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (rows != null && rows.isEmpty)
              Padding(
                padding: const EdgeInsets.all(30),
                child: Center(
                    child: Text('Abhi kuch nahi seekha. $name se koi lamba kaam karwaiye, jaise "kirana list banao aur har mahine yaad dilao".',
                        textAlign: TextAlign.center, style: const TextStyle(color: C.muted))),
              ),
            for (final p in rows ?? const <Map<String, dynamic>>[]) _card(p),
          ]),
        ),
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
    String word(String o) => const {'done': 'Poora', 'partial': 'Adhoora', 'stuck': 'Atka', 'stopped': 'Roka'}[o] ?? o;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Kaam ka hisaab', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 4),
          Text(
              '${sum['tasks'] ?? 0} kaam · ${sum['done_pct'] ?? '-'}% poore · ${sum['fixed_on_the_way'] ?? 0} mein atakne par khud hal dhoondha',
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
                      Text('Baaki: ${x['left']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.warn, fontSize: 11.5)),
                    Text('${x['steps']} kadam · ${x['seconds']} sec${(x['fixes'] as num? ?? 0) > 0 ? ' · ${x['fixes']} hal' : ''}',
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
                Text('Atka: ${l['problem']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
                Text('Hal: ${l['fix']}', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.teal, fontSize: 12)),
                Text('${l['helped']} baar kaam aaya', style: const TextStyle(color: C.faint, fontSize: 11)),
              ]),
            ),
            IconButton(
                tooltip: 'Bhool jao',
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
                Text('Dhyan: $w', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.warn, fontSize: 11.5)),
            ],
            const SizedBox(height: 6),
            Row(children: [
              Expanded(
                child: Text(
                    '${p['uses']} baar kaam aaya · ${p['wins']} baar theek${(p['fails'] as num? ?? 0) > 0 ? ' · ${p['fails']} baar atka' : ''}',
                    style: const TextStyle(color: C.faint, fontSize: 11.5)),
              ),
              IconButton(tooltip: 'Badlo', icon: const Icon(Icons.edit_rounded, size: 19), onPressed: () => _edit(p)),
              IconButton(tooltip: 'Bhool jao', icon: const Icon(Icons.delete_outline_rounded, size: 19, color: C.muted), onPressed: () => _delete(p)),
            ]),
          ]),
        ),
      ),
    );
  }
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
              Text(v['event'] == 'lesson' ? '${app.aName} ne atakne ka hal seekh liya' : '${app.aName} ne yeh kaam karna seekh liya', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
              Text('${v['title'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ]),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProceduresScreen(app: app))),
            child: const Text('Dekho'),
          ),
        ]),
      );
}
