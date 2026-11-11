import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.186 Lamba kaam pakka: the goal card. ONE card per goal id (state merges by `id`), a live checklist the
/// brain ticks itself with kaam_plan: ✓ done, ⏳ current, ✕ failed, – skipped. A blocked goal says plainly what
/// she must do; Rokiye stops the goal (the chat itself stays free).
class GoalCard extends StatelessWidget {
  const GoalCard({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;

  static const _ico = {'done': '✓', 'current': '⏳', 'failed': '✕', 'skipped': '–', 'pending': '•'};
  static const _col = {
    'done': C.ok, 'current': C.accent, 'failed': C.bad, 'skipped': C.faint, 'pending': C.faint,
  };

  @override
  Widget build(BuildContext context) {
    final v = it.data;
    final status = '${v['status'] ?? 'working'}';
    final steps = List<Map<String, dynamic>>.from((v['steps'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final done = (v['done'] as num?)?.toInt() ?? steps.where((s) => s['state'] == 'done').length;
    final total = (v['total'] as num?)?.toInt() ?? steps.length;
    final pct = (v['pct'] as num?)?.toInt() ?? (total > 0 ? (100 * done / total).round() : 0);
    final reason = '${v['reason'] ?? ''}';
    final hold = '${v['hold'] ?? ''}';
    final report = v['report'] is Map ? Map<String, dynamic>.from(v['report'] as Map) : const <String, dynamic>{};
    final head = <String, String>{
      'working': 'LONG TASK IN PROGRESS',
      'done': 'LONG TASK DONE',
      'blocked': 'WAITING FOR YOUR REPLY',
      'failed': 'LONG TASK INCOMPLETE',
      'stopped': 'LONG TASK STOPPED',
    }[status] ?? 'LONG TASK';
    final headCol = switch (status) { 'done' => C.ok, 'blocked' => C.accent, 'failed' => C.bad, 'stopped' => C.faint, _ => C.violet };
    return Glass(
      flat: true,
      tint: headCol,
      opacity: .05,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Container(width: 38, height: 38, alignment: Alignment.center,
            decoration: BoxDecoration(color: C.accent, borderRadius: BorderRadius.circular(12)),
            child: const Text('◎', style: TextStyle(color: C.onAccent, fontSize: 20, fontWeight: FontWeight.w800))),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(head, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: .6, color: C.faint)),
            const SizedBox(height: 2),
            Text('${v['title'] ?? v['goal'] ?? 'Long task'}',
                maxLines: 3, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w800, color: C.ink)),
          ])),
          if (total > 0)
            Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(999), border: Border.all(color: C.line)),
              child: Text('$done/$total', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: headCol))),
        ]),
        if (total > 0) ...[
          const SizedBox(height: 10),
          ClipRRect(borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(value: (pct.clamp(0, 100)) / 100, minHeight: 4,
              backgroundColor: Colors.white.withOpacity(.08),
              valueColor: AlwaysStoppedAnimation(headCol))),
        ],
        if (steps.isNotEmpty) ...[
          const SizedBox(height: 10),
          ...steps.take(15).map((s) {
            final st = '${s['state'] ?? 'pending'}';
            final col = _col[st] ?? C.faint;
            final cur = st == 'current';
            return Padding(padding: const EdgeInsets.only(top: 5), child: Row(children: [
              Container(width: 22, height: 22, alignment: Alignment.center,
                decoration: BoxDecoration(color: col.withOpacity(cur ? .22 : .13), borderRadius: BorderRadius.circular(7),
                  border: Border.all(color: col.withOpacity(cur ? .8 : .3))),
                child: Text(_ico[st] ?? '•', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: col))),
              const SizedBox(width: 8),
              Expanded(child: Text('${s['text'] ?? ''}',
                  style: TextStyle(fontSize: 12.5, color: st == 'done' ? C.faint : C.ink,
                      fontWeight: cur ? FontWeight.w700 : FontWeight.w500,
                      decoration: st == 'done' || st == 'skipped' ? TextDecoration.lineThrough : null))),
              if ('${s['note'] ?? ''}'.isNotEmpty)
                Flexible(child: Text('${s['note']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10.5, color: C.faint))),
            ]));
          }),
        ],
        if (reason.isNotEmpty && status != 'working' && report.isEmpty) ...[
          const SizedBox(height: 10),
          Text(reason, style: TextStyle(fontSize: 12.5, color: headCol, fontWeight: FontWeight.w600)),
        ],
        // v0.228 the four-part final report: kya hua / kya bana / kya baaki / aapko kya karna hai
        if (report.isNotEmpty) ...[
          const SizedBox(height: 12),
          _Report(report: report, col: headCol),
        ],
        // v0.228 the budget ran out: the job ASKS, her tap carries it on (done steps kept)
        if (status == 'blocked' && hold == 'limit') ...[
          const SizedBox(height: 12),
          SizedBox(height: 40, child: FilledButton.icon(
            onPressed: () async {
              final id = app.conversationId;
              final api = app.api;
              if (id == null || api == null) return;
              try {
                await api.continueGoal(id);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('OK, I am moving the work forward.'), duration: Duration(seconds: 2)));
                }
              } catch (_) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Could not move ahead right now, try again.'), duration: Duration(seconds: 2)));
                }
              }
            },
            style: FilledButton.styleFrom(backgroundColor: C.accent, foregroundColor: C.onAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
            icon: const Icon(Icons.play_arrow_rounded, size: 20),
            label: const Text('Move ahead', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13)))),
        ],
        if (status == 'working' || status == 'blocked') ...[
          const SizedBox(height: 12),
          SizedBox(height: 38, child: OutlinedButton.icon(
            onPressed: () async {
              final id = app.conversationId;
              final api = app.api;
              if (id == null || api == null) return;
              try {
                await api.stopGoal(id);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('The long task was stopped.'), duration: Duration(seconds: 2)));
                }
              } catch (_) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Could not stop it, try again.'), duration: Duration(seconds: 2)));
                }
              }
            },
            style: OutlinedButton.styleFrom(
              foregroundColor: C.bad, side: BorderSide(color: C.bad.withOpacity(.45)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
            icon: const Icon(Icons.stop_circle_outlined, size: 18),
            label: const Text('Stop', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)))),
        ],
      ]),
    );
  }
}


/// v0.228 the final report, the same four parts on every long job (like Claude's end-of-job summary).
class _Report extends StatelessWidget {
  const _Report({required this.report, required this.col});
  final Map<String, dynamic> report;
  final Color col;

  List<String> _list(String k) => (report[k] as List? ?? const []).map((e) => '$e').where((e) => e.isNotEmpty).toList();

  Widget _part(String head, List<String> lines) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(head, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: .4, color: C.faint)),
          ...lines.take(10).map((l) => Padding(
                padding: const EdgeInsets.only(top: 3),
                child: SelectableText('• $l', style: const TextStyle(fontSize: 12.5, color: C.ink, height: 1.3)))),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final summary = '${report['summary'] ?? ''}';
    final aapka = '${report['aapka'] ?? ''}';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14), border: Border.all(color: C.line)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (summary.isNotEmpty)
          Text(summary, style: TextStyle(fontSize: 13, color: col, fontWeight: FontWeight.w700)),
        if (_list('hua').isNotEmpty) _part('✅ WHAT HAPPENED', _list('hua')),
        if (_list('bana').isNotEmpty) _part('📎 WHAT WAS MADE', _list('bana')),
        if (_list('pending').isNotEmpty) _part('⏳ WHAT IS LEFT', _list('pending')),
        if (aapka.isNotEmpty) _part('👉 WHAT YOU NEED TO DO', [aapka]),
      ]),
    );
  }
}
