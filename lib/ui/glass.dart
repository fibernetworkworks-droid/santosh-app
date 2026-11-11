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
  // v0.488 CLAUDE-STYLE DESIGN: one quiet neutral ground, a warm off-white ink, saffron only where Hoola is acting.
  static const ink = Color(0xFFF3F1EC);       // main text
  static const muted = Color(0xFFA09B93);     // secondary text (>= 6:1 on the ground)
  static const faint = Color(0xFF8E8981);     // captions
  static const accent = Color(0xFFF4A24C);    // saffron: primary actions, active tab, "Hoola is working"
  static const accentSoft = Color(0xFFF6B66E);
  static const accent2 = Color(0xFFC055F5);
  static const violet = Color(0xFF7C5CFF);
  static const onAccent = Color(0xFF1B1305);  // text on saffron
  static const chip = Color(0xFFE2DFD8);      // icon / chip ink on neutral surfaces
  static const ok = Color(0xFF44CF95);
  static const warn = Color(0xFFF4B85C);
  static const bad = Color(0xFFF2706F);
  static const teal = Color(0xFF2DD4BF);
  static const bgTop = Color(0xFF151515);     // the ground
  static const bgBottom = Color(0xFF1A1A19);
  static const surface = Color(0xFF202020);   // composer, tab pill, cards
  static const bubble = Color(0xFF2A2A28);    // her own message
  static const hair = Color(0xFF30302D);      // hairline borders
  static const panel = Color(0x14FFFFFF);     // inner panels on glass
  static const line = Color(0x14FFFFFF);
  static const gradient = LinearGradient(colors: [Color(0xFFFFD9A8), Color(0xFFFF9A3C), Color(0xFFC055F5)],
      stops: [0, .45, 1], begin: Alignment.topLeft, end: Alignment.bottomRight);
  static const youGradient = LinearGradient(colors: [Color(0xFF7C5CFF), Color(0xFFB44CF0)], begin: Alignment.topLeft, end: Alignment.bottomRight);
}

/// v0.488 the interface sans: Schibsted Grotesk (the web console's own, the closest free match to the app this design
/// follows). Looked up by name so a google_fonts build that lacks the family falls back to Manrope instead of failing.
TextStyle uiSans({double? fontSize, FontWeight? fontWeight, Color? color, double? height, double? letterSpacing}) {
  try {
    return GoogleFonts.getFont('Schibsted Grotesk', fontSize: fontSize, fontWeight: fontWeight, color: color, height: height, letterSpacing: letterSpacing);
  } catch (_) {
    return GoogleFonts.manrope(fontSize: fontSize, fontWeight: fontWeight, color: color, height: height, letterSpacing: letterSpacing);
  }
}

TextTheme uiSansTheme(TextTheme base) {
  try {
    return GoogleFonts.getTextTheme('Schibsted Grotesk', base);
  } catch (_) {
    return GoogleFonts.manropeTextTheme(base);
  }
}

TextStyle display(double size, {FontWeight w = FontWeight.w700, Color color = C.ink}) =>
    uiSans(fontSize: size, fontWeight: w, color: color, height: 1.15, letterSpacing: -size * .01);

/// v0.249 CLAUDE JAISA AKSHAR: Hoola's reply is set the way Claude sets its own - a serif at 16px / 1.5,
/// weight 400 (Claude's own token is `--font-claude-response: Anthropic Serif; 1rem; 400; 1.5`).
/// Anthropic Serif is not ours to use, so this is Source Serif 4: the closest free one, with the same
/// optical-size axis. Her OWN message stays sans (Manrope), exactly as Claude keeps the user message sans.
/// v0.253: Source Serif 4 -> Literata. Measured at the same 16px, Source Serif 4 gives an x-height of 8 and a
/// cap of 11, Literata 9 and 12 - and Claude's own reply measures a 17px glyph band against our 16px. Literata
/// (the Google Play Books screen face) closes that gap without changing the size, so nothing reflows.
TextStyle replyText({double size = 16, Color color = C.ink}) =>
    GoogleFonts.literata(fontSize: size, fontWeight: FontWeight.w400, color: color, height: 1.5);

ThemeData santoshTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: C.accent, brightness: Brightness.dark).copyWith(
    primary: C.accent, onPrimary: C.onAccent, secondary: C.violet, surface: C.surface, onSurface: C.ink,
  );
  final base = ThemeData(useMaterial3: true, colorScheme: scheme, brightness: Brightness.dark);
  return base.copyWith(
    textTheme: uiSansTheme(base.textTheme).apply(bodyColor: C.ink, displayColor: C.ink),
    scaffoldBackgroundColor: C.bgTop,
    splashFactory: InkSparkle.splashFactory,
    appBarTheme: AppBarTheme(backgroundColor: Colors.transparent, elevation: 0, foregroundColor: C.ink,
        titleTextStyle: uiSans(fontSize: 18, fontWeight: FontWeight.w600, color: C.ink)),
    inputDecorationTheme: InputDecorationTheme(
      labelStyle: const TextStyle(color: C.muted),
      hintStyle: const TextStyle(color: C.faint),
      enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: Color(0x33FFFFFF))),
      focusedBorder: const UnderlineInputBorder(borderSide: BorderSide(color: C.accent, width: 1.6)),
    ),
    dialogTheme: DialogTheme(backgroundColor: C.surface, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26))),
    snackBarTheme: SnackBarThemeData(backgroundColor: C.bubble, contentTextStyle: const TextStyle(color: C.ink),
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

/// The ground behind every screen. v0.488: a flat neutral ground, like the app it is modelled on (the drifting
/// coloured light is gone - it was the costliest pixel on a budget phone and the loudest thing on screen). A [tint]
/// (the Baat mood colour) is a very faint glow from the top edge only.
class Aurora extends StatelessWidget {
  const Aurora({super.key, required this.child, this.tint});
  final Widget child;
  final Color? tint;   // optional mood colour (Baat screen)

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: C.bgTop,
          gradient: tint == null
              ? null
              : RadialGradient(center: const Alignment(0, -1.1), radius: 1.1, colors: [tint!.withOpacity(.16), C.bgTop]),
        ),
        child: child,
      );
}

/// A quiet panel: a faint lift over the ground and a hairline border. v0.488: no blur, no sheen, no glow
/// (the [flat] flag stays so every caller keeps compiling; every panel is flat now).
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
  final bool flat;

  @override
  Widget build(BuildContext context) => Container(
        margin: margin,
        padding: padding,
        decoration: BoxDecoration(
          color: (tint ?? Colors.white).withOpacity(opacity),
          borderRadius: BorderRadius.circular(radius),
          border: Border.all(color: border ?? C.hair),
        ),
        child: child,
      );
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
            decoration: BoxDecoration(color: C.accent, borderRadius: BorderRadius.circular(height > 54 ? 27.0 : height / 2)),
            child: Center(
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(label, style: uiSans(fontSize: height > 50 ? 16 : 14.5, fontWeight: FontWeight.w600, color: C.onAccent)),
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
          decoration: BoxDecoration(color: C.surface, borderRadius: BorderRadius.circular(24),
              border: Border.all(color: C.hair)),
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
