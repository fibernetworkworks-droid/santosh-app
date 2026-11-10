import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.648 KAAM KA HISAAB: her work in one place - running now, waiting for her, and finished in the last 7 days.
/// Each row opens the chat (or the call record) it came from.
Future<void> showKaamSheet(BuildContext context, Santosh app) async {
  if (app.api == null) return;
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: const Color(0xF2141029),
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (ctx) => _KaamSheet(app: app),
  );
}

class _KaamSheet extends StatefulWidget {
  const _KaamSheet({required this.app});
  final Santosh app;
  @override
  State<_KaamSheet> createState() => _KaamSheetState();
}

class _KaamSheetState extends State<_KaamSheet> {
  Map<String, dynamic>? _d;
  String _err = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.kaamList();
      if (!mounted) return;
      setState(() => _d = r);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _d = const {};
        _err = 'Your work list could not be opened right now. Please try again in a little while.';
      });
    }
  }

  List<Map<String, dynamic>> _rows(String k) =>
      [for (final x in ((_d?[k] as List?) ?? const [])) Map<String, dynamic>.from(x as Map)];

  String _when(String iso) {
    final t = DateTime.tryParse(iso)?.toLocal();
    if (t == null) return '';
    final hm = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
    final now = DateTime.now();
    if (t.year == now.year && t.month == now.month && t.day == now.day) return 'Aaj $hm';
    final y = now.subtract(const Duration(days: 1));
    if (t.year == y.year && t.month == y.month && t.day == y.day) return 'Kal $hm';
    return '${t.day}/${t.month} $hm';
  }

  IconData _icon(Map<String, dynamic> r) {
    switch ('${r['state']}') {
      case 'working':
        return Icons.autorenew_rounded;
      case 'waiting':
        return Icons.pan_tool_alt_outlined;
      case 'failed':
        return Icons.error_outline_rounded;
      case 'stopped':
        return Icons.stop_circle_outlined;
      default:
        return Icons.check_circle_outline_rounded;
    }
  }

  Color _color(Map<String, dynamic> r) {
    switch ('${r['state']}') {
      case 'working':
        return C.accent;
      case 'waiting':
        return C.warn;
      case 'failed':
        return C.bad;
      case 'stopped':
        return C.muted;
      default:
        return C.ok;
    }
  }

  Widget _row(Map<String, dynamic> r) {
    final app = widget.app;
    final conv = '${r['conversation_id'] ?? ''}';
    final call = r['from_call'] == true;
    final detail = '${r['detail'] ?? ''}';
    final sub = [
      '${r['say'] ?? ''}',
      if (detail.isNotEmpty) detail,
      _when('${r['at'] ?? ''}'),
      if (call) '📞 call',
    ].where((x) => x.isNotEmpty).join(' · ');
    return ListTile(
      leading: Icon(_icon(r), color: _color(r)),
      title: Text('${r['title'] ?? r['label'] ?? 'Kaam'}', maxLines: 2, overflow: TextOverflow.ellipsis),
      subtitle: Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 12)),
      onTap: conv.isEmpty
          ? null
          : () {
              Navigator.pop(context);
              app.openChat(conv, remember: !call);
            },
    );
  }

  Widget _head(String text, int n) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 4),
        child: Text('$text ($n)', style: const TextStyle(color: C.muted, fontSize: 13, fontWeight: FontWeight.w600)),
      );

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final d = _d;
    final running = _rows('running'), waiting = _rows('waiting'), done = _rows('done');
    return SafeArea(
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * .75,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 2),
            child: Row(children: [
              const Icon(Icons.task_alt_rounded, color: C.accent, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(app.g('Your work'), style: display(18, w: FontWeight.w700))),
            ]),
          ),
          Expanded(
            child: d == null
                ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
                : (running.isEmpty && waiting.isEmpty && done.isEmpty)
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(_err.isNotEmpty ? _err : app.g('No work has been done this week yet.'),
                              textAlign: TextAlign.center, style: const TextStyle(color: C.muted)),
                        ),
                      )
                    : ListView(
                        padding: const EdgeInsets.fromLTRB(10, 0, 10, 16),
                        children: [
                          if (waiting.isNotEmpty) ...[_head(app.g('Needs your answer'), waiting.length), ...waiting.map(_row)],
                          if (running.isNotEmpty) ...[_head(app.g('In progress'), running.length), ...running.map(_row)],
                          if (done.isNotEmpty) ...[_head(app.g('Done in the last 7 days'), done.length), ...done.map(_row)],
                        ],
                      ),
          ),
        ]),
      ),
    );
  }
}
