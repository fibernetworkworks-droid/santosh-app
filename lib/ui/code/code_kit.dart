// v0.921 HOOLA CODE NATIVE (owner: "OPTION B ::: SAME AS HOOLA CHAT SCREEN ... PREMIUM AND PERFECT SAME AS CLAUDE CODE"
// -> design canvas claude.ai/artifact/GF4AtP5MNfV8kARgTGymuh -> "GO"): the phone's own Hoola Code in the new design.
// This file holds what every Hoola Code screen shares: reading the server's maps, one way to call it, the words for a
// session's state, and the small pieces (top bar, pill buttons, chips, cards, the +/- count, the working ring).
// The server routes are the console's own (/api/devsahayak/*); merging, posting a review and starting a big plan are
// always her tap.
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../native.dart';
import '../../state.dart';
import '../hoola_theme.dart';

String cs(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> cm(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> cl(dynamic l) =>
    List<Map<String, dynamic>>.from(((l is List) ? l : const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
int ci(dynamic v) => v is num ? v.toInt() : (int.tryParse('${v ?? ''}') ?? 0);
String cPlural(int n, String one, [String? many]) => '$n ${n == 1 ? one : (many ?? '${one}s')}';
String cRepoShort(String full) {
  final i = full.indexOf('/');
  return i < 0 ? full : full.substring(i + 1);
}

/// A plain line at the bottom of the screen.
void codeToast(BuildContext context, String text) {
  if (text.trim().isEmpty) return;
  final m = ScaffoldMessenger.maybeOf(context);
  m?.hideCurrentSnackBar();
  m?.showSnackBar(SnackBar(content: Text(text), behavior: SnackBarBehavior.floating, duration: const Duration(seconds: 3)));
}

/// One call to the Hoola Code routes. A refusal is shown as the server's own words and returns null.
Future<Map<String, dynamic>?> codeCall(BuildContext context, Santosh app, String method, String path,
    {Object? body, Map<String, String>? query, bool quiet = false}) async {
  final api = app.api;
  if (api == null) return null;
  try {
    final r = await api.call(method, path, body: body, query: query, timeout: const Duration(minutes: 4));
    final m = r is Map ? Map<String, dynamic>.from(r) : <String, dynamic>{'list': r};
    if (!quiet && context.mounted) codeToast(context, cs(m['say']));
    return m;
  } catch (e) {
    if (!quiet && context.mounted) codeToast(context, '$e'.replaceFirst('Exception: ', ''));
    return null;
  }
}

Future<void> codeOpenGithub(String url) async {
  if (url.startsWith('https://github.com/')) await Native.openExternal(url: url);
}

// ---------------------------------------------------------------------------------------------- a session's state
const Map<String, String> codeStatusWords = {
  'new': 'Starting',
  'plan_wait': 'Plan ready',
  'ready': 'Ready to open the PR',
  'pr_open': 'PR open',
  'ci_running': 'CI running',
  'checks_failed': 'CI failed',
  'merged': 'Merged',
  'closed': 'PR closed',
  'explained': 'Answered',
  'refused': 'Stopped by a safety rule',
  'failed': 'Could not finish',
  'cancelled': 'Stopped',
};
const _needs = {'plan_wait', 'ready', 'checks_failed', 'refused'};
const codeCanRevise = {'pr_open', 'checks_failed', 'ready', 'refused'};

bool codeRunning(Map<String, dynamic> t) => t['running'] == true;
String codeStatus(Map<String, dynamic> t) => codeStatusWords[cs(t['status'])] ?? cs(t['status_label']);
String codeTitle(Map<String, dynamic> t) => cs(t['title']).isNotEmpty ? cs(t['title']) : cs(t['number']);

bool codeNeedsYou(Map<String, dynamic> t, List<Map<String, dynamic>> actions) {
  if (cs(t['question']).isNotEmpty) return true;
  if (_needs.contains(cs(t['status']))) return true;
  final pr = ci(t['pr_number']);
  if (pr == 0) return false;
  return actions.any((a) => cs(a['status']) == 'waiting' && cs(a['repo']) == cs(t['repo']) && ci(a['pr_number']) == pr);
}

/// 'run' | 'need' | 'old'
String codeGroup(Map<String, dynamic> t, List<Map<String, dynamic>> actions) =>
    codeRunning(t) ? 'run' : (codeNeedsYou(t, actions) ? 'need' : 'old');

/// Lines added / removed over every changed file.
(int, int) codeStat(Map<String, dynamic> t) {
  var a = 0, r = 0;
  for (final f in cl(t['files'])) {
    a += ci(f['added']);
    r += ci(f['removed']);
  }
  return (a, r);
}

String codeClock(int seconds) {
  final s = math.max(0, seconds);
  if (s < 3600) return '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';
  return '${s ~/ 3600}:${((s % 3600) ~/ 60).toString().padLeft(2, '0')}:${(s % 60).toString().padLeft(2, '0')}';
}

String codeLong(int seconds) {
  final s = math.max(0, seconds);
  if (s < 60) return '${s}s';
  if (s < 3600) return '${s ~/ 60}m ${(s % 60).toString().padLeft(2, '0')}s';
  return '${s ~/ 3600}h ${((s % 3600) ~/ 60).toString().padLeft(2, '0')}m';
}

String codeAgo(String iso) {
  final d = DateTime.tryParse(iso);
  if (d == null) return '';
  final m = DateTime.now().difference(d).inMinutes;
  if (m < 1) return 'just now';
  if (m < 60) return '$m min ago';
  if (m < 1440) return '${(m / 60).round()} h ago';
  if (m < 2880) return 'yesterday';
  return '${(m / 1440).round()} days ago';
}

// ---------------------------------------------------------------------------------------------- type
TextStyle codeMono(HoolaColors c, {double size = 12.5, Color? color}) =>
    TextStyle(fontFamily: HoolaFont.mono, fontSize: size, color: color ?? c.ink, height: 1.45);
TextStyle codeSans(HoolaColors c, {double size = 15, FontWeight weight = FontWeight.w400, Color? color, double height = 1.4}) =>
    TextStyle(fontFamily: HoolaFont.sans, fontSize: size, fontWeight: weight, color: color ?? c.ink, height: height);

// ---------------------------------------------------------------------------------------------- pieces
/// The +12 −4 count, in green and red.
class CodeStat extends StatelessWidget {
  const CodeStat(this.added, this.removed, {super.key, this.size = 12});
  final int added, removed;
  final double size;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    if (added == 0 && removed == 0) return const SizedBox.shrink();
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Text('+$added', style: codeMono(c, size: size, color: c.ok)),
      const SizedBox(width: 6),
      Text('−$removed', style: codeMono(c, size: size, color: c.bad)),
    ]);
  }
}

/// A round icon button (48 tap area).
class CodeIconButton extends StatelessWidget {
  const CodeIconButton({super.key, required this.icon, required this.label, this.onTap, this.size = 22});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final double size;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: label,
      child: Tooltip(
        message: label,
        child: InkResponse(
          onTap: onTap,
          radius: 24,
          child: SizedBox(width: 48, height: 48, child: Icon(icon, size: size, color: onTap == null ? c.ink3 : c.ink)),
        ),
      ),
    );
  }
}

/// The top bar: back, a title (and a mono line under it), the actions on the right.
class CodeTopBar extends StatelessWidget {
  const CodeTopBar({super.key, required this.title, this.sub = '', this.actions = const [], this.close = false, this.line = true});
  final String title, sub;
  final List<Widget> actions;
  final bool close, line;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(border: line ? Border(bottom: BorderSide(color: c.sunk)) : null),
      child: Row(children: [
        CodeIconButton(
            icon: close ? Icons.close_rounded : Icons.arrow_back_ios_new_rounded,
            size: close ? 22 : 19,
            label: close ? 'Close' : 'Back',
            onTap: () => Navigator.of(context).maybePop()),
        Expanded(
          child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 16, weight: FontWeight.w600, height: 1.25)),
            if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12, color: c.ink3)),
          ]),
        ),
        ...actions,
        const SizedBox(width: 4),
      ]),
    );
  }
}

/// The one main button of a screen: a black pill (light text).
class CodeMain extends StatelessWidget {
  const CodeMain(this.label, {super.key, this.onTap, this.icon, this.height = 50, this.busy = false});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final double height;
  final bool busy;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final on = onTap != null && !busy;
    return Semantics(
      button: true,
      label: label,
      child: Material(
        color: on ? c.pill : c.lineStrong,
        borderRadius: BorderRadius.circular(height / 2),
        child: InkWell(
          borderRadius: BorderRadius.circular(height / 2),
          onTap: on ? onTap : null,
          child: SizedBox(
            height: math.max(48, height),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [
                if (busy)
                  SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                else if (icon != null)
                  Icon(icon, size: 18, color: c.onPill),
                if (busy || icon != null) const SizedBox(width: 8),
                Flexible(
                  child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 15, weight: FontWeight.w600, color: c.onPill)),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// A quiet outline pill.
class CodeOutline extends StatelessWidget {
  const CodeOutline(this.label, {super.key, this.onTap, this.icon, this.height = 50, this.color});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final double height;
  final Color? color;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final ink = onTap == null ? c.ink3 : (color ?? c.ink);
    return Semantics(
      button: true,
      label: label,
      child: Material(
        color: c.surface,
        shape: StadiumBorder(side: BorderSide(color: c.lineStrong)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: SizedBox(
            height: math.max(48, height),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [
                if (icon != null) ...[Icon(icon, size: 17, color: ink), const SizedBox(width: 7)],
                Flexible(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14.5, weight: FontWeight.w500, color: ink))),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// A small chip (36 high, 48 tap area): optional leading icon, optional trailing chevron.
class CodeChip extends StatelessWidget {
  const CodeChip(this.label, {super.key, this.onTap, this.icon, this.mono = false, this.chevron = false, this.on = false, this.trailing});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final bool mono, chevron, on;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final fg = on ? c.onPill : c.ink;
    return Semantics(
      button: onTap != null,
      label: label,
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Container(
            height: 36,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: on ? c.pill : c.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: on ? c.pill : c.line),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              if (icon != null) ...[Icon(icon, size: 16, color: on ? c.onPill : c.ink2), const SizedBox(width: 6)],
              Flexible(
                child: Text(label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: mono ? codeMono(c, size: 12.5, color: fg) : codeSans(c, size: 13, weight: FontWeight.w500, color: fg)),
              ),
              if (trailing != null) ...[const SizedBox(width: 6), trailing!],
              if (chevron) ...[const SizedBox(width: 4), Icon(Icons.keyboard_arrow_down_rounded, size: 16, color: on ? c.onPill : c.ink3)],
            ]),
          ),
        ),
      ),
    );
  }
}

/// A white card on the paper page. [edge] draws a short coloured line on the left (waiting = amber).
class CodeCard extends StatelessWidget {
  const CodeCard({super.key, required this.child, this.padding = const EdgeInsets.all(14), this.edge, this.onTap, this.lifted = false, this.radius = 16});
  final Widget child;
  final EdgeInsets padding;
  final Color? edge;
  final VoidCallback? onTap;
  final bool lifted;
  final double radius;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget body = Padding(padding: padding, child: child);
    if (edge != null) {
      body = Stack(children: [
        body,
        Positioned(
          left: 0,
          top: 14,
          bottom: 14,
          child: Container(width: 3, decoration: BoxDecoration(color: edge, borderRadius: BorderRadius.circular(2))),
        ),
      ]);
    }
    return Container(
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: c.line.withOpacity(.8)),
        boxShadow: lifted && !c.dark ? [BoxShadow(color: c.shadow.withOpacity(.14), blurRadius: 24, spreadRadius: -14, offset: const Offset(0, 10))] : null,
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(borderRadius: BorderRadius.circular(radius), onTap: onTap, child: body),
      ),
    );
  }
}

/// A small coloured label ("Plan ready", "Draft").
class CodeBadge extends StatelessWidget {
  const CodeBadge(this.text, {super.key, required this.fg, required this.bg});
  final String text;
  final Color fg, bg;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(10)),
        child: Text(text, style: TextStyle(fontFamily: HoolaFont.sans, fontSize: 12, fontWeight: FontWeight.w600, color: fg)),
      );
}

/// A section label above a group of rows.
class CodeSection extends StatelessWidget {
  const CodeSection(this.text, {super.key, this.trailing});
  final String text;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 18, 4, 8),
      child: Row(children: [
        Expanded(child: Text(text, style: codeSans(c, size: 13, weight: FontWeight.w600, color: c.ink2))),
        if (trailing != null) trailing!,
      ]),
    );
  }
}

/// The violet working ring (a turning arc; still under reduce motion).
class CodeRing extends StatefulWidget {
  const CodeRing({super.key, this.size = 15});
  final double size;
  @override
  State<CodeRing> createState() => _CodeRingState();
}

class _CodeRingState extends State<CodeRing> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (HoolaMotion.reduced(context)) {
      _a.stop();
    } else if (!_a.isAnimating) {
      _a.repeat();
    }
  }

  @override
  void dispose() {
    _a.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: AnimatedBuilder(
        animation: _a,
        builder: (_, __) => Transform.rotate(
          angle: _a.value * math.pi * 2,
          child: CustomPaint(painter: _RingPainter(c.line, c.accent)),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.track, this.arc);
  final Color track, arc;
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width * .18;
    final r = Offset.zero & size;
    final p = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = w
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(r.deflate(w / 2), 0, math.pi * 2, false, p..color = track);
    canvas.drawArc(r.deflate(w / 2), -math.pi / 2, math.pi / 2, false, p..color = arc);
  }

  @override
  bool shouldRepaint(_RingPainter o) => o.track != track || o.arc != arc;
}

/// The Hoola Code mark: the code brackets in violet.
class CodeMark extends StatelessWidget {
  const CodeMark({super.key, this.size = 20});
  final double size;
  @override
  Widget build(BuildContext context) => Icon(Icons.code_rounded, size: size, color: HoolaColors.of(context).accent);
}

/// A bottom sheet in the new design: a handle, a title, the body.
Future<T?> codeSheet<T>(BuildContext context, Santosh app, {required String title, required Widget Function(BuildContext ctx) body}) {
  final c = HoolaColors.of(context);
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: c.bg,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => HoolaTheme(
      appearance: app.appearance,
      child: Builder(builder: (ctx) {
        final c = HoolaColors.of(ctx);
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: SafeArea(
            top: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 5,
                    margin: const EdgeInsets.only(top: 10, bottom: 12),
                    decoration: BoxDecoration(color: c.lineStrong, borderRadius: BorderRadius.circular(5)),
                  ),
                ),
                Text(title, style: HoolaType.heading(c)),
                const SizedBox(height: 14),
                body(ctx),
              ]),
            ),
          ),
        );
      }),
    ),
  );
}

/// A choice row inside a sheet (radio-like, 52 high).
class CodeChoiceRow extends StatelessWidget {
  const CodeChoiceRow({super.key, required this.label, this.sub = '', required this.on, required this.onTap, this.mono = false});
  final String label, sub;
  final bool on, mono;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      selected: on,
      button: true,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          constraints: const BoxConstraints(minHeight: 52),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          margin: const EdgeInsets.only(bottom: 8),
          decoration: BoxDecoration(
            color: c.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: on ? c.ink : c.line, width: on ? 1.5 : 1),
          ),
          child: Row(children: [
            Icon(on ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded, size: 20, color: on ? c.ink : c.ink3),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(label, style: mono ? codeMono(c, size: 13.5) : codeSans(c, size: 15, weight: FontWeight.w500)),
                if (sub.isNotEmpty) Text(sub, style: codeSans(c, size: 13, color: c.ink2, height: 1.35)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

/// A text field in the new design (labelled; used in sheets).
class CodeField extends StatelessWidget {
  const CodeField({super.key, required this.controller, required this.label, this.hint = '', this.lines = 1, this.mono = false, this.secret = false});
  final TextEditingController controller;
  final String label, hint;
  final int lines;
  final bool mono, secret;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink2)),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          minLines: lines,
          maxLines: secret ? 1 : (lines == 1 ? 1 : lines + 3),
          obscureText: secret,
          autocorrect: !secret && !mono,
          enableSuggestions: !secret && !mono,
          style: mono ? codeMono(c, size: 13.5) : codeSans(c, size: 15.5),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: codeSans(c, size: 15, color: c.ink3),
            filled: true,
            fillColor: c.surface,
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.line)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.line)),
            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.ink, width: 1.4)),
          ),
        ),
      ]),
    );
  }
}

/// A switch row in the new design.
class CodeSwitchRow extends StatelessWidget {
  const CodeSwitchRow({super.key, required this.label, this.sub = '', required this.value, required this.onChanged, this.last = false});
  final String label, sub;
  final bool value, last;
  final ValueChanged<bool>? onChanged;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      constraints: const BoxConstraints(minHeight: 52),
      padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
      decoration: BoxDecoration(border: last ? null : Border(bottom: BorderSide(color: c.sunk))),
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label, style: codeSans(c, size: 14.5)),
            if (sub.isNotEmpty) Text(sub, style: codeSans(c, size: 12.5, color: c.ink3, height: 1.35)),
          ]),
        ),
        Switch(
          value: value,
          onChanged: onChanged,
          activeColor: c.onPill,
          activeTrackColor: c.pill,
          inactiveThumbColor: c.surface,
          inactiveTrackColor: c.lineStrong,
          trackOutlineColor: WidgetStatePropertyAll(c.line.withOpacity(0)),
        ),
      ]),
    );
  }
}
