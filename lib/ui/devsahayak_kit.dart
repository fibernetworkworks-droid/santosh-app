/// v0.879 HOOLA CODE PHONE: the small pieces every Hoola Code phone screen shares, drawn to the owner-approved design
/// (docs/design/hoola_code/Phone*.png): the H mark, the cream main pill and the outline pill, the switch, the status
/// dot, a sheet head, the pill composer (+, field, hold-to-talk mic, violet send or cream Stop) and the way back to the
/// Hoola Code home. Colours come from CodeColors (lib/ui/hoola_theme.dart); no raw colour lives here.
library;

import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

import 'hoola_theme.dart';

String hcS(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> hcM(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> hcList(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
int hcInt(dynamic v) => v is num ? v.toInt() : (int.tryParse('${v ?? ''}') ?? 0);

void hcSay(BuildContext c, String t) {
  final w = t.replaceFirst('Exception: ', '').trim();
  if (w.isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(w)));
}

String hcShortRepo(String full) {
  final i = full.indexOf('/');
  return i < 0 ? full : full.substring(i + 1);
}

/// "1m 42s", "14s", "2h 05m".
String hcClock(int seconds) {
  final s = seconds < 0 ? 0 : seconds;
  if (s < 60) return '${s}s';
  if (s < 3600) return '${s ~/ 60}m ${(s % 60).toString().padLeft(2, '0')}s';
  return '${s ~/ 3600}h ${((s % 3600) ~/ 60).toString().padLeft(2, '0')}m';
}

/// The text styles of the Hoola Code screens (only 12 / 13 / 14 / 15 / 16 / 17 / 20 / 28).
class HcType {
  static TextStyle ui(CodeColors c, double size, {FontWeight weight = FontWeight.w400, Color? color, double height = 1.35}) =>
      TextStyle(fontFamily: HoolaFont.sans, fontSize: size, fontWeight: weight, color: color ?? c.ink, height: height);
  static TextStyle mono(CodeColors c, double size, {Color? color, double height = 1.45}) =>
      TextStyle(fontFamily: HoolaFont.mono, fontSize: size, fontWeight: FontWeight.w400, color: color ?? c.ink, height: height);
  static TextStyle serif(CodeColors c, double size, {FontWeight weight = FontWeight.w400, Color? color, double height = 1.25}) =>
      TextStyle(fontFamily: HoolaFont.serif, fontSize: size, fontWeight: weight, color: color ?? c.ink, height: height);

  /// Hoola's own words in a session: the serif at 16 (her chat-font pick is honoured).
  static TextStyle prose(CodeColors c) => TextStyle(
      fontFamily: ChatFont.family(c.dark ? HoolaColors.darkSet : HoolaColors.light),
      fontSize: 16,
      fontWeight: FontWeight.w400,
      color: c.ink,
      height: 1.55);
}

/// Remembers the Hoola Code home page so "New session" anywhere goes back to it.
class DevCodeNav {
  static Route<dynamic>? home;

  /// Back to the Hoola Code home (or one step back when the home is not open).
  static void toHome(BuildContext context) => toHomeNav(Navigator.of(context));

  static void toHomeNav(NavigatorState nav) {
    final h = home;
    if (h != null && h.isActive) {
      nav.popUntil((r) => r == h);
    } else {
      nav.maybePop();
    }
  }
}

/// The violet H mark (design: a 24-grid circle with an H cut in the on-accent ink).
class HcMark extends StatelessWidget {
  const HcMark({super.key, this.size = 64, this.dim = false});
  final double size;
  final bool dim;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return ExcludeSemantics(
      child: SizedBox(
        width: size,
        height: size,
        child: CustomPaint(painter: _MarkPainter(dim ? c.accent.withOpacity(.45) : c.accent, c.onAccent)),
      ),
    );
  }
}

class _MarkPainter extends CustomPainter {
  _MarkPainter(this.fill, this.ink);
  final Color fill, ink;

  @override
  void paint(Canvas canvas, Size size) {
    final u = size.width / 24;
    canvas.drawCircle(Offset(12 * u, 12 * u), 10 * u, Paint()..color = fill);
    final p = Paint()
      ..color = ink
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.4 * u
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(Offset(8 * u, 7 * u), Offset(8 * u, 17 * u), p);
    canvas.drawLine(Offset(16 * u, 7 * u), Offset(16 * u, 17 * u), p);
    canvas.drawLine(Offset(8 * u, 12 * u), Offset(16 * u, 12 * u), p);
  }

  @override
  bool shouldRepaint(_MarkPainter old) => old.fill != fill || old.ink != ink;
}

/// A 48 x 48 icon button with no fill (header buttons).
class HcIconButton extends StatelessWidget {
  const HcIconButton({super.key, required this.icon, required this.label, required this.onTap, this.color, this.size = 22});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final Color? color;
  final double size;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return IconButton(
      tooltip: label,
      onPressed: onTap,
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
      icon: Icon(icon, size: size, color: color ?? c.ink2),
    );
  }
}

/// The cream main pill (design: #F3F1EC with #1B1A17 text).
class HcCreamButton extends StatelessWidget {
  const HcCreamButton({super.key, required this.label, required this.onTap, this.icon, this.height = 52, this.size = 17, this.busy = false});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final double height;
  final double size;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final off = onTap == null;
    return Semantics(
      button: true,
      enabled: !off,
      label: label,
      excludeSemantics: true,
      child: Opacity(
        opacity: off && !busy ? .5 : 1.0,
        child: Material(
          color: c.cream,
          shape: const StadiumBorder(),
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: height),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                child: Row(mainAxisSize: MainAxisSize.min, mainAxisAlignment: MainAxisAlignment.center, children: [
                  if (busy)
                    SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onCream))
                  else if (icon != null)
                    Icon(icon, size: 20, color: c.onCream),
                  if (busy || icon != null) const SizedBox(width: 10),
                  Flexible(
                    child: Text(label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: HcType.ui(c, size, weight: FontWeight.w600, color: c.onCream, height: 1.2)),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The outline pill (design: 1px #3A3835, optional quiet fill).
class HcOutlineButton extends StatelessWidget {
  const HcOutlineButton(
      {super.key, required this.label, required this.onTap, this.icon, this.height = 46, this.size = 15, this.filled = false, this.weight = FontWeight.w500});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final double height;
  final double size;
  final bool filled;
  final FontWeight weight;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Semantics(
      button: true,
      enabled: onTap != null,
      label: label,
      excludeSemantics: true,
      child: Opacity(
        opacity: onTap == null ? .5 : 1.0,
        child: Material(
          color: filled ? c.chip : Colors.transparent,
          shape: StadiumBorder(side: BorderSide(color: c.line3)),
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: height),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                child: Row(mainAxisSize: MainAxisSize.min, mainAxisAlignment: MainAxisAlignment.center, children: [
                  if (icon != null) ...[Icon(icon, size: 20, color: c.ink), const SizedBox(width: 10)],
                  Flexible(
                    child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, size, weight: weight, height: 1.2)),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The design's switch: 46 x 28, violet when on, a cream knob.
class HcSwitch extends StatelessWidget {
  const HcSwitch({super.key, required this.value, required this.onChanged, required this.label});
  final bool value;
  final ValueChanged<bool>? onChanged;
  final String label;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final ms = HoolaMotion.of(context, HoolaMotion.menu);
    return Semantics(
      toggled: value,
      label: label,
      enabled: onChanged != null,
      excludeSemantics: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onChanged == null ? null : () => onChanged!(!value),
        child: SizedBox(
          width: 52,
          height: 48,
          child: Center(
            child: AnimatedContainer(
              duration: ms,
              curve: HoolaMotion.ease,
              width: 46,
              height: 28,
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(color: value ? c.accent : c.line3, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
              child: AnimatedAlign(
                duration: ms,
                curve: HoolaMotion.ease,
                alignment: value ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(width: 22, height: 22, decoration: BoxDecoration(color: c.knob, shape: BoxShape.circle)),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class HcDot extends StatelessWidget {
  const HcDot(this.color, {super.key, this.size = 8});
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) =>
      Container(width: size, height: size, decoration: BoxDecoration(color: color, shape: BoxShape.circle));
}

/// A small filled chip (schedule triggers, file names).
class HcTag extends StatelessWidget {
  const HcTag(this.text, {super.key, this.mono = false});
  final String text;
  final bool mono;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(color: c.chip, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
      child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: mono ? HcType.mono(c, 13, color: c.ink2) : HcType.ui(c, 13, color: c.ink2)),
    );
  }
}

/// A filter chip (Active / Archived, All / Paused): filled when on, outlined when off.
class HcFilterChip extends StatelessWidget {
  const HcFilterChip({super.key, required this.label, required this.on, required this.onTap, this.size = 13, this.outlined = false, this.trailing});
  final String label;
  final bool on;
  final VoidCallback onTap;
  final double size;
  final bool outlined;
  final IconData? trailing;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Semantics(
      button: true,
      selected: on,
      label: label,
      excludeSemantics: true,
      child: Material(
        color: on ? c.raised : Colors.transparent,
        shape: StadiumBorder(side: BorderSide(color: outlined && !on ? c.line3 : Colors.transparent)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 36),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(label, style: HcType.ui(c, size, color: on ? c.ink : c.ink4)),
                if (trailing != null) ...[const SizedBox(width: 2), Icon(trailing, size: 16, color: c.ink4)],
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// The head of a bottom sheet: the handle, Close on the left, the title (+ a line), a slot on the right.
class HcSheetHead extends StatelessWidget {
  const HcSheetHead({super.key, required this.title, this.sub = '', this.trailing});
  final String title;
  final String sub;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Container(
        width: 40,
        height: 4,
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(color: c.handle, borderRadius: HoolaRadius.r(4)),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Row(crossAxisAlignment: sub.isEmpty ? CrossAxisAlignment.center : CrossAxisAlignment.start, children: [
          HcIconButton(icon: Icons.close_rounded, label: 'Close', color: c.ink, onTap: () => Navigator.pop(context)),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(top: sub.isEmpty ? 0.0 : 6.0),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(title, textAlign: TextAlign.center, style: HcType.ui(c, 20, weight: FontWeight.w600)),
                if (sub.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(sub, textAlign: TextAlign.center, style: HcType.ui(c, 14, color: c.ink3)),
                ],
              ]),
            ),
          ),
          trailing ?? const SizedBox(width: 48),
        ]),
      ),
    ]);
  }
}

/// Opens a Hoola Code bottom sheet in the design's sheet colour and corners.
Future<T?> hcSheet<T>(BuildContext context, WidgetBuilder builder, {bool tall = false}) {
  final c = CodeColors.of(context);
  return showModalBottomSheet<T>(
    context: context,
    backgroundColor: c.sheet,
    barrierColor: c.scrim,
    isScrollControlled: true,
    useSafeArea: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (sheet) => Padding(
      padding: EdgeInsets.only(top: 10, bottom: MediaQuery.viewInsetsOf(sheet).bottom),
      child: tall
          ? SizedBox(height: MediaQuery.sizeOf(sheet).height * .9, child: builder(sheet))
          : builder(sheet),
    ),
  );
}

/// The pill composer: + (optional), the field, the hold-to-talk mic and either the violet send arrow or the cream Stop.
class HcComposer extends StatefulWidget {
  const HcComposer({
    super.key,
    required this.controller,
    required this.hint,
    required this.onSend,
    required this.language,
    this.sendLabel = 'Send',
    this.onPlus,
    this.busy = false,
    this.onStop,
    this.stopping = false,
    this.enabled = true,
  });
  final TextEditingController controller;
  final String hint;
  final VoidCallback onSend;
  final String language;
  final String sendLabel;
  final VoidCallback? onPlus;
  final bool busy;
  final VoidCallback? onStop;   // set = Hoola is working: the cream Stop shows (send stays possible while text is typed)
  final bool stopping;
  final bool enabled;

  @override
  State<HcComposer> createState() => _HcComposerState();
}

class _HcComposerState extends State<HcComposer> {
  final _stt = SpeechToText();
  bool _listening = false;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_redraw);
  }

  @override
  void didUpdateWidget(HcComposer old) {
    super.didUpdateWidget(old);
    if (old.controller != widget.controller) {
      old.controller.removeListener(_redraw);
      widget.controller.addListener(_redraw);
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_redraw);
    _stt.stop();
    super.dispose();
  }

  void _redraw() {
    if (mounted) setState(() {});
  }

  Future<void> _mic({bool hold = false}) async {
    if (_listening) {
      await _stt.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }
    final ok = await _stt.initialize(onStatus: (s) {
      if ((s == 'done' || s == 'notListening') && mounted) setState(() => _listening = false);
    });
    if (!ok) {
      if (mounted) hcSay(context, 'Microphone permission is needed.');
      return;
    }
    final before = widget.controller.text.trim();
    if (!mounted) return;
    setState(() => _listening = true);
    await _stt.listen(
      localeId: widget.language.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 90),
      pauseFor: Duration(seconds: hold ? 30 : 4),
      partialResults: true,
      onResult: (r) {
        if (!mounted) return;
        final t = before.isEmpty ? r.recognizedWords : '$before ${r.recognizedWords}';
        widget.controller.text = t;
        widget.controller.selection = TextSelection.collapsed(offset: t.length);
      },
    );
  }

  Widget _round({required String label, required Widget child, required Color fill, VoidCallback? onTap}) => Semantics(
        button: true,
        label: label,
        enabled: onTap != null,
        excludeSemantics: true,
        child: Material(
          color: fill,
          shape: const CircleBorder(),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: onTap,
            child: SizedBox(width: 44, height: 44, child: Center(child: child)),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final hasText = widget.controller.text.trim().isNotEmpty;
    final canSend = hasText && !widget.busy && widget.enabled;
    final showStop = widget.onStop != null && !hasText;
    Widget last;
    if (showStop) {
      last = _round(
        label: widget.stopping ? 'Stopping after this step' : 'Stop',
        fill: c.cream,
        onTap: widget.stopping || widget.busy ? null : widget.onStop,
        child: Container(width: 14, height: 14, decoration: BoxDecoration(color: c.onCream, borderRadius: HoolaRadius.r(3))),
      );
    } else {
      last = _round(
        label: widget.sendLabel,
        fill: canSend ? c.accent : c.raised,
        onTap: canSend ? widget.onSend : null,
        child: widget.busy
            ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3))
            : Icon(Icons.arrow_upward_rounded, size: 20, color: canSend ? c.onAccent : c.ink4),
      );
    }
    return Container(
      constraints: const BoxConstraints(minHeight: 56),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
      decoration: BoxDecoration(color: c.surface, borderRadius: HoolaRadius.r(28), border: Border.all(color: c.line3)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        if (widget.onPlus != null) ...[
          _round(label: 'Add files or photos', fill: c.raised, onTap: widget.onPlus, child: Icon(Icons.add_rounded, size: 22, color: c.ink)),
          const SizedBox(width: 6),
        ] else
          const SizedBox(width: 10),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: 2),
            child: TextField(
              controller: widget.controller,
              enabled: widget.enabled,
              minLines: 1,
              maxLines: 6,
              maxLength: 20000,
              cursorColor: c.accent,
              style: HcType.ui(c, 16, height: 1.4),
              textInputAction: TextInputAction.newline,
              decoration: InputDecoration(
                hintText: _listening ? 'Listening…' : widget.hint,
                hintStyle: HcType.ui(c, 16, color: c.ink4, height: 1.4),
                counterText: '',
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 12),
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                disabledBorder: InputBorder.none,
                filled: false,
              ),
            ),
          ),
        ),
        const SizedBox(width: 6),
        GestureDetector(
          onLongPressStart: (_) => _mic(hold: true),
          onLongPressEnd: (_) {
            if (_listening) _mic();
          },
          child: _round(
            label: _listening ? 'Stop listening' : 'Hold to talk',
            fill: _listening ? c.accentTint : c.raised,
            onTap: widget.enabled ? () => _mic() : null,
            child: Icon(_listening ? Icons.graphic_eq_rounded : Icons.mic_none_rounded, size: 20, color: _listening ? c.accent : c.ink2),
          ),
        ),
        const SizedBox(width: 6),
        last,
      ]),
    );
  }
}
