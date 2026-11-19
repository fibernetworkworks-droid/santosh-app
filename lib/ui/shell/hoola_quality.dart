// v0.999.23 THE TIER SHEET ON THE PHONE (owner: "every hoola chat show the 5 tiers only --- premium sheet" -> "DONT
// SHOW PRICE ... REMOVE THAT SESSION SECTION" -> "PERFECT ... DEPLOY IT EVERWHERE"): a small "Medium ▾" chip at the
// top right of the chat home and of every chat opens one bottom sheet titled Quality - five rows and nothing else:
// Normal (Hoola's own setup, recommended), Ultra (asks first: up to 70x credit), High, Medium, Low. No prices, no model
// names. GET / PUT /api/model/tier; the server clears an older one-model pick when she picks a tier. One shared
// notifier, so the chip on the home and in a chat always agree. A server without tiers shows no chip.
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_credits.dart';
import 'hoola_settings.dart' show hoolaOpenNew;

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
              locked: id.isNotEmpty && hoolaTierNow.value?['locked'] == true,
              onTap: () => Navigator.pop(ctx, id)),
        ]),
      ),
    ),
  );
  if (pick == null || !context.mounted) return;
  if (pick.isNotEmpty && hoolaTierNow.value?['locked'] == true) {   // v0.999.26 Free = Normal only: buy credits first
    await hoolaOpenNew(context, app, HoolaCreditsPage(app: app));
    if (context.mounted) await hoolaTierLoad(app);
    return;
  }
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
  const HoolaTierRow({super.key, required this.id, required this.on, required this.onTap, this.locked = false});
  final String id;
  final bool on, locked;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final tag = id.isEmpty ? 'Recommended' : locked ? '🔒 Buy credits' : id == 'ultra' ? hoolaUltraTag : '';
    final warn = id == 'ultra' && !locked;
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

// v0.999.29 QUALITY EVERYWHERE (owner: "GO BUILD 1 AND 2" after the audit of every chat panel): the row under a typing
// box on the tool screens - her credits (a pie + "4,820 credits" / "42 free today", opens Credits) and the quality chip
// above (the same choice everywhere). Credits read once and shared; hidden when credits are off or she is never charged.
final ValueNotifier<Map<String, dynamic>?> hoolaWalletNow = ValueNotifier(null);
int _hoolaPlanCredits = 0;

/// The server's rupee rate for one credit (pages that keep rupee figures on the server show them as credits).
double hoolaInrPerCredit = 0.088;
String hoolaCreditsOf(dynamic inr) {
  final n = (inr is num) ? inr : num.tryParse('$inr') ?? 0;
  final c = (n / (hoolaInrPerCredit > 0 ? hoolaInrPerCredit : 0.088)).round();
  return '${_hoolaCommas(c)} ${c == 1 ? 'credit' : 'credits'}';
}
bool _hoolaWalletLoading = false;

Future<void> hoolaWalletLoad(Santosh app) async {
  if (_hoolaWalletLoading || app.api == null) return;
  _hoolaWalletLoading = true;
  try {
    final v = await app.api!.credits(hoolaCountry());
    final w = Map<String, dynamic>.from((v['wallet'] as Map?) ?? const {});
    var plan = 0;
    for (final p in ((v['prices'] as Map?)?['plans'] as List?) ?? const []) {
      if (p is Map && '${p['id']}' == '${w['plan']}') plan = (p['credits'] as num?)?.toInt() ?? 0;
    }
    _hoolaPlanCredits = plan;
    final r = (v['inr_per_credit'] as num?)?.toDouble() ?? 0;
    if (r > 0) hoolaInrPerCredit = r;
    hoolaWalletNow.value = w;
  } catch (_) {
    // an older server without credits: no credits chip
  } finally {
    _hoolaWalletLoading = false;
  }
}

String _hoolaCommas(num v) => v.round().toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');

class HoolaQualityRow extends StatefulWidget {
  const HoolaQualityRow({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaQualityRow> createState() => _HoolaQualityRowState();
}

class _HoolaQualityRowState extends State<HoolaQualityRow> {
  @override
  void initState() {
    super.initState();
    if (hoolaWalletNow.value == null) hoolaWalletLoad(widget.app);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Row(mainAxisAlignment: MainAxisAlignment.end, mainAxisSize: MainAxisSize.max, children: [
      ValueListenableBuilder<Map<String, dynamic>?>(
        valueListenable: hoolaWalletNow,
        builder: (context, w, _) {
          if (w == null || w['on'] != true || w['exempt'] == true) return const SizedBox.shrink();
          final paid = w['unlocked'] == true;
          final left = ((paid ? w['paid_left'] : w['free_left']) as num?) ?? 0;
          final frac = paid
              ? (_hoolaPlanCredits > 0 ? (((w['plan_left'] as num?) ?? 0) / _hoolaPlanCredits) : 1.0)
              : (((w['free_left'] as num?) ?? 0) / math.max(1, ((w['free_daily'] as num?) ?? 60)));
          final say = paid ? '${_hoolaCommas(left)} credits' : '${_hoolaCommas(left)} free today';
          return Semantics(
            button: true,
            label: '$say. Open credits and plans',
            excludeSemantics: true,
            child: InkWell(
              borderRadius: BorderRadius.circular(HoolaRadius.chip),
              onTap: () async {
                await hoolaOpenNew(context, widget.app, HoolaCreditsPage(app: widget.app));
                hoolaWalletNow.value = null;
                await hoolaWalletLoad(widget.app);
                await hoolaTierLoad(widget.app);
              },
              child: SizedBox(
                height: HoolaSpace.touch,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    CustomPaint(size: const Size(16, 16), painter: _HoolaPie(frac.clamp(0.0, 1.0).toDouble(), c.ink2)),
                    const SizedBox(width: 6),
                    Text(say, style: HoolaType.small(c).copyWith(color: c.ink2, fontWeight: FontWeight.w500)),
                  ]),
                ),
              ),
            ),
          );
        },
      ),
      const SizedBox(width: 4),
      HoolaQualityChip(app: widget.app),
    ]);
  }
}

class _HoolaPie extends CustomPainter {
  _HoolaPie(this.frac, this.color);
  final double frac;
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final o = size.center(Offset.zero), r = size.width / 2 - 1;
    canvas.drawCircle(o, r, Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.4
      ..color = color);
    canvas.drawArc(Rect.fromCircle(center: o, radius: r - 2.6), -math.pi / 2, 2 * math.pi * math.max(frac, 0.08), true, Paint()..color = color);
  }

  @override
  bool shouldRepaint(_HoolaPie old) => old.frac != frac || old.color != color;
}
