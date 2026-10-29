import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import 'avatar_look.dart';

/// v0.164.3 blur perf guard: the chat list flips this on while it scrolls fast, and the
/// Aurora drift freezes for a moment. The drifting blobs are the costliest pixels on a
/// budget phone — recomputed every frame while glass panels sit on top of them — and
/// nobody can see them move mid-flick anyway. The chat clears it a beat after the
/// scrolling stops (chat_screen.dart owns the timing), so the night sky glides on.
final ValueNotifier<bool> auroraPaused = ValueNotifier(false);

/// Santosh "Night Glass": deep indigo night, frosted glass, saffron action colour, violet for you.
class C {
  static const ink = Color(0xFFF4F2FF);       // main text
  static const muted = Color(0xFFB9B3DA);     // secondary text (≥ 7:1 on bg)
  static const faint = Color(0xFF9C96C2);     // captions
  static const accent = Color(0xFFFFB15C);    // saffron: primary actions, active tab
  static const accentSoft = Color(0xFFFFC27A);
  static const accent2 = Color(0xFFC055F5);
  static const violet = Color(0xFF7C5CFF);
  static const onAccent = Color(0xFF1B1030);  // text on saffron
  static const chip = Color(0xFFD7D2F2);
  static const ok = Color(0xFF34D399);
  static const warn = Color(0xFFFFC27A);
  static const bad = Color(0xFFF87171);
  static const teal = Color(0xFF2DD4BF);
  static const bgTop = Color(0xFF0B0A1A);
  static const bgBottom = Color(0xFF120E2A);
  static const panel = Color(0x14FFFFFF);     // inner panels on glass
  static const line = Color(0x14FFFFFF);
  static const gradient = LinearGradient(colors: [Color(0xFFFFD9A8), Color(0xFFFF9A3C), Color(0xFFC055F5)],
      stops: [0, .45, 1], begin: Alignment.topLeft, end: Alignment.bottomRight);
  static const youGradient = LinearGradient(colors: [Color(0xFF7C5CFF), Color(0xFFB44CF0)], begin: Alignment.topLeft, end: Alignment.bottomRight);
}

TextStyle display(double size, {FontWeight w = FontWeight.w700, Color color = C.ink}) =>
    GoogleFonts.sora(fontSize: size, fontWeight: w, color: color, height: 1.12, letterSpacing: -size * .015);

/// v0.248 CLAUDE JAISA AKSHAR: Hoola's reply is set the way Claude sets its own - a serif at 16px / 1.5,
/// weight 400 (Claude's own token is `--font-claude-response: Anthropic Serif; 1rem; 400; 1.5`).
/// Anthropic Serif is not ours to use, so this is Source Serif 4: the closest free one, with the same
/// optical-size axis. Her OWN message stays sans (Manrope), exactly as Claude keeps the user message sans.
TextStyle replyText({double size = 16, Color color = C.ink}) =>
    GoogleFonts.sourceSerif4(fontSize: size, fontWeight: FontWeight.w400, color: color, height: 1.5);

ThemeData santoshTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: C.accent, brightness: Brightness.dark).copyWith(
    primary: C.accent, onPrimary: C.onAccent, secondary: C.violet, surface: const Color(0xFF17122F), onSurface: C.ink,
  );
  final base = ThemeData(useMaterial3: true, colorScheme: scheme, brightness: Brightness.dark);
  return base.copyWith(
    textTheme: GoogleFonts.manropeTextTheme(base.textTheme).apply(bodyColor: C.ink, displayColor: C.ink),
    scaffoldBackgroundColor: C.bgTop,
    splashFactory: InkSparkle.splashFactory,
    appBarTheme: AppBarTheme(backgroundColor: Colors.transparent, elevation: 0, foregroundColor: C.ink,
        titleTextStyle: GoogleFonts.sora(fontSize: 19, fontWeight: FontWeight.w600, color: C.ink)),
    inputDecorationTheme: InputDecorationTheme(
      labelStyle: const TextStyle(color: C.muted),
      hintStyle: const TextStyle(color: C.faint),
      enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: Color(0x33FFFFFF))),
      focusedBorder: const UnderlineInputBorder(borderSide: BorderSide(color: C.accent, width: 1.6)),
    ),
    dialogTheme: DialogTheme(backgroundColor: const Color(0xF21A1438), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26))),
    snackBarTheme: SnackBarThemeData(backgroundColor: const Color(0xF2221A47), contentTextStyle: const TextStyle(color: C.ink),
        behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? C.onAccent : const Color(0xFFE9E6FA)),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? C.accent : const Color(0x2EFFFFFF)),
    ),
    chipTheme: base.chipTheme.copyWith(backgroundColor: const Color(0x17FFFFFF), side: const BorderSide(color: Color(0x29FFFFFF)),
        labelStyle: const TextStyle(color: C.ink, fontWeight: FontWeight.w600), selectedColor: const Color(0x38FFB15C)),
    pageTransitionsTheme: const PageTransitionsTheme(builders: {TargetPlatform.android: _GlassPageTransition()}),
  );
}

/// Screens slide up a little and fade in (feels lighter than the default zoom).
class _GlassPageTransition extends PageTransitionsBuilder {
  const _GlassPageTransition();
  @override
  Widget buildTransitions<T>(PageRoute<T> route, BuildContext context, Animation<double> a, Animation<double> b, Widget child) {
    final c = CurvedAnimation(parent: a, curve: Curves.easeOutCubic);
    return FadeTransition(
      opacity: c,
      child: SlideTransition(position: Tween(begin: const Offset(0, .04), end: Offset.zero).animate(c), child: child),
    );
  }
}

/// The night sky behind every screen: slow-drifting coloured light that the glass panels blur.
class Aurora extends StatefulWidget {
  const Aurora({super.key, required this.child, this.tint});
  final Widget child;
  final Color? tint;   // optional mood colour (Baat screen)
  @override
  State<Aurora> createState() => _AuroraState();
}

class _AuroraState extends State<Aurora> with SingleTickerProviderStateMixin {
  late final AnimationController _t = AnimationController(vsync: this, duration: const Duration(seconds: 24))..repeat();

  @override
  void initState() {
    super.initState();
    auroraPaused.addListener(_onPaused);
  }

  void _onPaused() {
    if (auroraPaused.value) {
      _t.stop();   // ticker sleeps: no ticks, no repaints, zero GPU work while the list flies
    } else if (!_t.isAnimating) {
      _t.repeat();   // resumes from the value it froze at — the drift never jumps
    }
  }

  @override
  void dispose() {
    auroraPaused.removeListener(_onPaused);
    _t.dispose();
    super.dispose();
  }

  Widget _blob(Color c, double size, double x, double y, double o) => Positioned(
        left: x,
        top: y,
        child: IgnorePointer(
          child: ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: 70, sigmaY: 70),
            child: Container(width: size, height: size, decoration: BoxDecoration(shape: BoxShape.circle, color: c.withOpacity(o))),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: const BoxDecoration(color: C.bgTop),
        child: Stack(children: [
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _t,
              builder: (context, _) {
                final a = _t.value * 2 * math.pi;
                final w = MediaQuery.sizeOf(context).width;
                final h = MediaQuery.sizeOf(context).height;
                return Stack(children: [
                  _blob(const Color(0xFF6D4AFF), 340, -120 + math.sin(a) * 30, -90 + math.cos(a) * 24, .55),
                  _blob(widget.tint ?? const Color(0xFFFF8A2A), 290, w - 180 + math.cos(a * .8) * 26, h * .32 + math.sin(a) * 30, .33),
                  _blob(const Color(0xFF14B8A6), 260, 40 + math.sin(a * .6) * 40, h - 200 + math.cos(a * .7) * 20, .22),
                ]);
              },
            ),
          ),
          Positioned.fill(child: widget.child),
        ]),
      );
}

/// Frosted glass panel.
class Glass extends StatelessWidget {
  const Glass({super.key, required this.child, this.radius = 24, this.padding = const EdgeInsets.all(14), this.opacity = .07,
      this.margin, this.border, this.tint, this.flat = false});
  final Widget child;
  final double radius;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final double opacity;
  final Color? border;
  final Color? tint;

  /// v0.164.3 blur perf guard: [flat] skips the BackdropFilter and keeps the same
  /// night-glass paint (translucent fill, hairline border, top sheen, shadow). Every
  /// BackdropFilter re-blurs the whole layer beneath it each frame, so a Glass card
  /// inside the scrolling chat list is the #1 jank source on budget phones — cards
  /// there are flat. The true blur stays where it shines: the header and the composer.
  final bool flat;

  @override
  Widget build(BuildContext context) {
    final body = Container(
      padding: padding,
      decoration: BoxDecoration(
        color: (tint ?? Colors.white).withOpacity(opacity),
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: border ?? Colors.white.withOpacity(.14)),
        gradient: LinearGradient(colors: [Colors.white.withOpacity(.06), Colors.white.withOpacity(0)],
            begin: Alignment.topCenter, end: Alignment.center),
      ),
      child: child,
    );
    return Container(
      margin: margin,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        boxShadow: const [BoxShadow(color: Color(0x59050314), blurRadius: 30, offset: Offset(0, 10))],
      ),
      child: flat
          ? body
          : ClipRRect(
              borderRadius: BorderRadius.circular(radius),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
                child: body,
              ),
            ),
    );
  }
}

/// Press feedback for any tappable: a soft squash + a light haptic tick.
class Press extends StatefulWidget {
  const Press({super.key, required this.child, required this.onTap, this.haptic = true});
  final Widget child;
  final VoidCallback? onTap;
  final bool haptic;
  @override
  State<Press> createState() => _PressState();
}

class _PressState extends State<Press> {
  bool _down = false;
  @override
  Widget build(BuildContext context) => GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: widget.onTap == null ? null : (_) => setState(() => _down = true),
        onTapCancel: () => setState(() => _down = false),
        onTapUp: (_) => setState(() => _down = false),
        onTap: widget.onTap == null
            ? null
            : () {
                if (widget.haptic) HapticFeedback.selectionClick();
                widget.onTap!();
              },
        child: AnimatedScale(scale: _down ? .96 : 1, duration: const Duration(milliseconds: 110), curve: Curves.easeOut, child: widget.child),
      );
}

/// Saffron primary button (dark text on saffron for contrast).
class GradientButton extends StatelessWidget {
  const GradientButton({super.key, required this.label, required this.onTap, this.icon, this.height = 54});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final double height;

  @override
  Widget build(BuildContext context) => Opacity(
        opacity: onTap == null ? .5 : 1,
        child: Press(
          onTap: onTap,
          child: Container(
            height: height,
            decoration: BoxDecoration(color: C.accent, borderRadius: BorderRadius.circular(18), boxShadow: const [
              BoxShadow(color: Color(0x59FFA046), blurRadius: 24, offset: Offset(0, 10)),
            ]),
            child: Center(
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(label, style: GoogleFonts.manrope(fontSize: height > 50 ? 16 : 14.5, fontWeight: FontWeight.w800, color: C.onAccent)),
                if (icon != null) ...[const SizedBox(width: 8), Icon(icon, color: C.onAccent, size: 20)],
              ]),
            ),
          ),
        ),
      );
}

/// Secondary glass button.
class GlassButton extends StatelessWidget {
  const GlassButton({super.key, required this.label, required this.onTap, this.icon, this.height = 48, this.color = C.ink});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final double height;
  final Color color;
  @override
  Widget build(BuildContext context) => Press(
        onTap: onTap,
        child: Container(
          height: height,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(color: const Color(0x17FFFFFF), borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0x29FFFFFF))),
          child: Row(mainAxisSize: MainAxisSize.min, mainAxisAlignment: MainAxisAlignment.center, children: [
            if (icon != null) ...[Icon(icon, color: color, size: 18), const SizedBox(width: 8)],
            Text(label, style: TextStyle(fontWeight: FontWeight.w700, color: color, fontSize: 14)),
          ]),
        ),
      );
}

class Pill extends StatelessWidget {
  const Pill(this.text, {super.key, this.fg = C.chip, this.bg = const Color(0x1FFFFFFF)});
  final String text;
  final Color fg;
  final Color bg;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
        child: Text(text, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: fg, letterSpacing: .5)),
      );
}

/// Santosh's face in a glowing ring (headers, notifications).
class Avatar extends StatelessWidget {
  const Avatar({super.key, this.size = 48, this.online = true, this.glow});
  final double size;
  final bool online;
  final Color? glow;
  @override
  Widget build(BuildContext context) => Stack(clipBehavior: Clip.none, children: [
        Container(
          width: size,
          height: size,
          padding: const EdgeInsets.all(2),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const SweepGradient(colors: [Color(0xFFFFB15C), Color(0xFFC055F5), Color(0xFF7C5CFF), Color(0xFFFFB15C)]),
            boxShadow: [BoxShadow(color: (glow ?? C.accent).withOpacity(.45), blurRadius: 16)],
          ),
          child: AvatarFace(size: size - 4),          // the owner's look: Santosh or a female look (v0.48)
        ),
        if (online)
          Positioned(
            right: 0,
            bottom: 0,
            child: Container(
              width: size * .26,
              height: size * .26,
              decoration: BoxDecoration(color: C.ok, shape: BoxShape.circle, border: Border.all(color: C.bgTop, width: 2)),
            ),
          ),
      ]);
}

/// Section caption.
class Caption extends StatelessWidget {
  const Caption(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 0, 4, 8),
        child: Text(text, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.faint, letterSpacing: .9)),
      );
}

/// Children slide up and fade in one after another (lists, cards).
class Stagger extends StatelessWidget {
  const Stagger({super.key, required this.index, required this.child});
  final int index;
  final Widget child;
  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: Duration(milliseconds: 420 + index * 70),
        curve: Curves.easeOutCubic,
        builder: (context, v, c) => Opacity(opacity: v, child: Transform.translate(offset: Offset(0, (1 - v) * 18), child: c)),
        child: child,
      );
}
