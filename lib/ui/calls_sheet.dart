import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.646 ALAG CALL: the Calls section. Every voice call has its own record (transcript, tool rows, cards, receipt);
/// the chat stays the chat. Tapping a call opens its record like a chat, so its cards stay tappable there.
Future<void> showCallsSheet(BuildContext context, Santosh app) async {
  if (app.api == null) return;
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: const Color(0xF2141029),
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (ctx) => _CallsSheet(app: app),
  );
}

class _CallsSheet extends StatefulWidget {
  const _CallsSheet({required this.app});
  final Santosh app;
  @override
  State<_CallsSheet> createState() => _CallsSheetState();
}

class _CallsSheetState extends State<_CallsSheet> {
  List<Map<String, dynamic>>? _calls;
  String _err = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.calls();
      if (!mounted) return;
      setState(() => _calls = r);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _calls = const [];
        _err = 'Calls abhi nahi khul payi. Thodi der baad dobara dekhiye.';
      });
    }
  }

  String _when(String iso) {
    final t = DateTime.tryParse(iso)?.toLocal();
    if (t == null) return '';
    final d = DateTime.now().difference(t);
    final hm = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
    if (d.inDays < 1 && t.day == DateTime.now().day) return 'Aaj $hm';
    if (d.inDays < 2) return 'Kal $hm';
    return '${t.day}/${t.month} $hm';
  }

  String _len(int s) => s <= 0 ? '' : (s < 60 ? '$s sec' : '${(s / 60).round()} min');

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final calls = _calls;
    return SafeArea(
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * .7,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 4),
            child: Row(children: [
              const Icon(Icons.call_rounded, color: C.accent, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(app.g('Aapki calls'), style: display(18, w: FontWeight.w700))),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 0, 18, 8),
            child: Text(app.g('Har call ka apna hisaab. Chat alag rehti hai, yaad dono ki ek hai.'),
                style: const TextStyle(color: C.muted, fontSize: 13)),
          ),
          Expanded(
            child: calls == null
                ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
                : calls.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(_err.isNotEmpty ? _err : app.g('Abhi koi call nahi hai.'),
                              textAlign: TextAlign.center, style: const TextStyle(color: C.muted)),
                        ),
                      )
                    : ListView(
                        padding: const EdgeInsets.fromLTRB(10, 0, 10, 16),
                        children: [
                          for (final c in calls)
                            ListTile(
                              leading: Icon(c['id'] == app.conversationId ? Icons.call_rounded : Icons.call_outlined,
                                  color: c['id'] == app.conversationId ? C.accent : C.muted),
                              title: Text('${c['title'] ?? '📞 Call'}', maxLines: 1, overflow: TextOverflow.ellipsis),
                              subtitle: Text(
                                [_when('${c['at'] ?? ''}'), _len((c['seconds'] as num?)?.toInt() ?? 0)]
                                    .where((x) => x.isNotEmpty)
                                    .join(' · '),
                                style: const TextStyle(color: C.faint, fontSize: 12),
                              ),
                              onTap: () {
                                Navigator.pop(context);
                                app.openChat('${c['id']}', remember: false);
                              },
                            ),
                        ],
                      ),
          ),
        ]),
      ),
    );
  }
}
