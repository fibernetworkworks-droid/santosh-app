// v0.999.23 THE TIER SHEET ON THE PHONE (owner: "every hoola chat show the 5 tiers only --- premium sheet" -> "DONT
// SHOW PRICE ... REMOVE THAT SESSION SECTION" -> "PERFECT ... DEPLOY IT EVERWHERE"): a small "Medium ▾" chip at the
// top right of the chat home and of every chat opens one bottom sheet titled Quality - five rows and nothing else:
// Normal (Hoola's own setup, recommended), Ultra (asks first: up to 70x credit), High, Medium, Low. No prices, no model
// names. GET / PUT /api/model/tier; the server clears an older one-model pick when she picks a tier. One shared
// notifier, so the chip on the home and in a chat always agree. A server without tiers shows no chip.
import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';

/// The last tier answer from the server (null = not loaded yet / not offered).
final ValueNotifier<Map<String, dynamic>?> hoolaTierNow = ValueNotifier(null);

const hoolaTierRows = <String>['', 'ultra', 'high', 'medium', 'low'];
const hoolaTierNames = {'': 'Normal', 'ultra': 'Ultra', 'high': 'High', 'medium': 'Medium', 'low': 'Low'};
const hoolaTierNote = 'Better models give better answers and use your credit faster.';
const hoolaUltraTag = '⚠ Up to 70× credit';

String hoolaTierName(Map<String, dynamic>? v) => hoolaTierNames['${v?['selected'] ?? ''}'] ?? 'Normal';

Future<void> hoolaTierLoad(Santosh app) async {
  try {
    final v = await app.api!.modelTier();
    hoolaTierNow.value = v['available'] == true ? v : null;
  } catch (_) {
    // no tiers on this server, or offline: the chip stays hidden
  }
}

/// The chip: "Medium ▾". Hidden until the server says tiers are offered.
class HoolaQualityChip extends StatefulWidget {
  const HoolaQualityChip({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaQualityChip> createState() => _HoolaQualityChipState();
}

class _HoolaQualityChipState extends State<HoolaQualityChip> {
  @override
  void initState() {
    super.initState();
    if (hoolaTierNow.value == null && widget.app.api != null) hoolaTierLoad(widget.app);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ValueListenableBuilder<Map<String, dynamic>?>(
      valueListenable: hoolaTierNow,
      builder: (context, v, _) {
        if (v == null) return const SizedBox(width: 48);
        final name = hoolaTierName(v);
        return Semantics(
          button: true,
          label: 'Quality: $name',
          excludeSemantics: true,
          child: SizedBox(
            height: HoolaSpace.touch,
            child: Center(
              child: Material(
                color: c.sunk,
                borderRadius: BorderRadius.circular(HoolaRadius.chip),
                child: InkWell(
                  borderRadius: BorderRadius.circular(HoolaRadius.chip),
                  onTap: () => showHoolaTierSheet(context, widget.app),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(10, 6, 8, 6),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Text(name, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                      const SizedBox(width: 4),
                      Icon(Icons.keyboard_arrow_down_rounded, size: 18, color: c.ink2),
                    ]),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

/// The Quality sheet: the note, five rows, a violet tick on hers. Ultra opens its own question first.
Future<void> showHoolaTierSheet(BuildContext context, Santosh app) async {
  final c = HoolaColors.of(context);
  final pick = await showModalBottomSheet<String>(
    context: context,
    backgroundColor: c.surface,
    showDragHandle: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(padding: const EdgeInsets.symmetric(horizontal: 4), child: Text('Quality', style: HoolaType.heading(c))),
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 6, 4, 12),
            child: Text(hoolaTierNote, style: HoolaType.small(c).copyWith(color: c.ink2)),
          ),
          for (final id in hoolaTierRows) HoolaTierRow(id: id, on: '${hoolaTierNow.value?['selected'] ?? ''}' == id,
              onTap: () => Navigator.pop(ctx, id)),
        ]),
      ),
    ),
  );
  if (pick == null || !context.mounted) return;
  final now = '${hoolaTierNow.value?['selected'] ?? ''}';
  if (pick == now) return;
  if (pick == 'ultra' && !await _askUltra(context)) return;
  try {
    final v = await app.api!.modelTierSet(pick, confirmUltra: pick == 'ultra');
    hoolaTierNow.value = v;
    if (context.mounted) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(
          content: Text(pick.isEmpty ? "Back to Hoola's normal setup." : 'Your next message runs on ${hoolaTierNames[pick]}.')));
    }
  } catch (e) {
    if (context.mounted) ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text('$e')));
  }
}

/// One row of the sheet: name, its tag (Recommended / the Ultra warning), a tick when hers. 52 dp.
class HoolaTierRow extends StatelessWidget {
  const HoolaTierRow({super.key, required this.id, required this.on, required this.onTap});
  final String id;
  final bool on;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final tag = id.isEmpty ? 'Recommended' : id == 'ultra' ? hoolaUltraTag : '';
    final warn = id == 'ultra';
    return Semantics(
      inMutuallyExclusiveGroup: true,
      checked: on,
      button: true,
      child: Material(
        color: on ? c.sunk : Colors.transparent,
        borderRadius: BorderRadius.circular(HoolaRadius.tile),
        child: InkWell(
          borderRadius: BorderRadius.circular(HoolaRadius.tile),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 52),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(children: [
                Text(hoolaTierNames[id] ?? id, style: HoolaType.bodyLarge(c).copyWith(fontWeight: FontWeight.w500)),
                if (tag.isNotEmpty) ...[
                  const SizedBox(width: 8),
                  Flexible(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                          color: warn ? c.warnSoft : c.sunk, borderRadius: BorderRadius.circular(6)),
                      child: Text(tag, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.label(c).copyWith(color: warn ? c.warn : c.ink2)),
                    ),
                  ),
                ],
                const Spacer(),
                SizedBox(width: 22, child: on ? Icon(Icons.check_rounded, size: 20, color: c.accent) : null),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

Future<bool> _askUltra(BuildContext context) async {
  final c = HoolaColors.of(context);
  final ok = await showModalBottomSheet<bool>(
    context: context,
    backgroundColor: c.surface,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Text('Use Ultra?', style: HoolaType.heading(c)),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(color: c.warnSoft, borderRadius: BorderRadius.circular(6)),
              child: Text(hoolaUltraTag, style: HoolaType.label(c).copyWith(color: c.warn)),
            ),
          ]),
          const SizedBox(height: 10),
          Text('Ultra runs the best and most expensive models in every field: chat, coding, AI employees, apps and videos.',
              style: HoolaType.body(c).copyWith(color: c.ink2)),
          const SizedBox(height: 8),
          Text('Your credit runs out up to 70 times faster than on Medium.', style: HoolaType.body(c).copyWith(color: c.ink2)),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(
                backgroundColor: c.pill,
                foregroundColor: c.onPill,
                shape: const StadiumBorder(),
                minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Use Ultra'),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Not now'),
          ),
        ]),
      ),
    ),
  );
  return ok == true;
}
