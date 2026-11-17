// v0.975 HOOLA PIPELINE P6: the receipt line under a reply - which model did which part.
// One small line ("Made with  Research: Claude Sonnet 4.6 · Writing: Claude Opus 4.6"); a tap opens the parts,
// their level, and any hand-over (which model took over from which, and why). Used by the new design
// (HCQuietLine) and the old chat screen alike, so it only leans on the app's Theme.
import 'package:flutter/material.dart';

String _t(Object? o) => o is String ? o.trim() : (o is num ? '$o' : '');

List<Map<String, dynamic>> _list(Object? v) =>
    v is List ? [for (final e in v) if (e is Map) Map<String, dynamic>.from(e)] : const [];

class ModelReceiptLine extends StatelessWidget {
  const ModelReceiptLine({super.key, required this.v, this.ink, this.muted});
  final Map<String, dynamic> v;
  final Color? ink;
  final Color? muted;

  @override
  Widget build(BuildContext context) {
    final say = _t(v['say']);
    if (say.isEmpty || _list(v['parts']).isEmpty) return const SizedBox.shrink();
    final th = Theme.of(context);
    final mute = muted ?? th.colorScheme.onSurface.withOpacity(0.62);
    final main = ink ?? th.colorScheme.onSurface;
    final hand = (v['handovers'] as num?)?.toInt() ?? 0;
    return Semantics(
      button: true,
      label: 'Made with $say. Tap to see each part.',
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => showModelReceipt(context, v),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 44),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
            child: Text.rich(
              TextSpan(children: [
                TextSpan(text: 'Made with  ', style: TextStyle(color: main, fontWeight: FontWeight.w500)),
                TextSpan(text: say, style: TextStyle(color: mute)),
                if (hand > 0) TextSpan(text: '  ·  $hand hand-over${hand > 1 ? 's' : ''}', style: TextStyle(color: mute)),
              ]),
              style: const TextStyle(fontSize: 13, height: 1.35),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
      ),
    );
  }
}

Future<void> showModelReceipt(BuildContext context, Map<String, dynamic> v) {
  final rows = _list(v['parts']);
  return showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (ctx) {
      final th = Theme.of(ctx);
      final mute = th.colorScheme.onSurface.withOpacity(0.62);
      return ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(16, 0, 16, 24), children: [
        Text('Which model did which part', style: th.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        Text('Hoola picks the lowest level that does each part well, from public leaderboards.',
            style: TextStyle(fontSize: 13, color: mute)),
        const SizedBox(height: 8),
        for (final r in rows) ...[
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_t(r['label']).isEmpty ? 'Part' : _t(r['label']),
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            subtitle: Text(
                [_t(r['name']), _t(r['level']), _t(r['note'])].where((x) => x.isNotEmpty).join('  ·  '),
                style: TextStyle(fontSize: 13, color: mute)),
          ),
          for (final h in _list(r['handover']))
            Padding(
              padding: const EdgeInsets.only(left: 12, bottom: 6),
              child: Text(
                  '${_t(h['to'])} took over from ${_t(h['from'])}${_t(h['why']).isEmpty ? '' : ' (${_t(h['why'])})'}',
                  style: TextStyle(fontSize: 12.5, color: mute)),
            ),
        ],
      ]);
    },
  );
}
