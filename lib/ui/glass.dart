import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Santosh's visual language: lavender studio light, frosted glass, violet accent.
class C {
  static const ink = Color(0xFF1E1537);
  static const muted = Color(0xFF5E5780);
  static const accent = Color(0xFF6D3FE0);
  static const accent2 = Color(0xFFA21CAF);
  static const chip = Color(0xFF4A3596);
  static const ok = Color(0xFF15803D);
  static const warn = Color(0xFFB45309);
  static const bad = Color(0xFFB91C1C);
  static const bgTop = Color(0xFFF7F3FF);
  static const bgBottom = Color(0xFFE9E1FB);
  static const gradient = LinearGradient(colors: [Color(0xFF7C3AED), accent2], begin: Alignment.topLeft, end: Alignment.bottomRight);
}

TextStyle display(double size, {FontWeight w = FontWeight.w800, Color color = C.ink}) =>
    GoogleFonts.baloo2(fontSize: size, fontWeight: w, color: color, height: 1.05);

ThemeData santoshTheme() {
  final base = ThemeData(useMaterial3: true, colorSchemeSeed: C.accent, brightness: Brightness.light);
  return base.copyWith(
    textTheme: GoogleFonts.manropeTextTheme(base.textTheme).apply(bodyColor: C.ink, displayColor: C.ink),
    scaffoldBackgroundColor: C.bgTop,
  );
}

/// Soft coloured light behind every screen; glass panels blur it.
class Aurora extends StatelessWidget {
  const Aurora({super.key, required this.child});
  final Widget child;

  Widget _blob(Color c, double size, {double? l, double? t, double? r, double? b, double o = .5}) => Positioned(
        left: l,
        top: t,
        right: r,
        bottom: b,
        child: IgnorePointer(
          child: ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: 60, sigmaY: 60),
            child: Container(width: size, height: size, decoration: BoxDecoration(shape: BoxShape.circle, color: c.withOpacity(o))),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: const BoxDecoration(gradient: LinearGradient(colors: [C.bgTop, Color(0xFFEFE8FF), C.bgBottom], begin: Alignment.topCenter, end: Alignment.bottomCenter)),
        child: Stack(children: [
          _blob(const Color(0xFFA78BFA), 300, l: -110, t: 90),
          _blob(const Color(0xFFF9A8D4), 260, r: -90, t: 330, o: .55),
          _blob(const Color(0xFFFCD34D), 240, l: 60, b: -40, o: .35),
          Positioned.fill(child: child),
        ]),
      );
}

class Glass extends StatelessWidget {
  const Glass({super.key, required this.child, this.radius = 24, this.padding = const EdgeInsets.all(14), this.opacity = .58, this.margin});
  final Widget child;
  final double radius;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final double opacity;

  @override
  Widget build(BuildContext context) => Container(
        margin: margin,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(radius),
          boxShadow: const [BoxShadow(color: Color(0x1F4C1D95), blurRadius: 32, offset: Offset(0, 12))],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(radius),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
            child: Container(
              padding: padding,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(opacity),
                borderRadius: BorderRadius.circular(radius),
                border: Border.all(color: Colors.white.withOpacity(.85)),
              ),
              child: child,
            ),
          ),
        ),
      );
}

class GradientButton extends StatelessWidget {
  const GradientButton({super.key, required this.label, required this.onTap, this.icon, this.height = 54});
  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final double height;

  @override
  Widget build(BuildContext context) => Opacity(
        opacity: onTap == null ? .5 : 1,
        child: Material(
          color: Colors.transparent,
          child: Ink(
            height: height,
            decoration: BoxDecoration(gradient: C.gradient, borderRadius: BorderRadius.circular(18), boxShadow: const [
              BoxShadow(color: Color(0x5E7C3AED), blurRadius: 24, offset: Offset(0, 10)),
            ]),
            child: InkWell(
              borderRadius: BorderRadius.circular(18),
              onTap: onTap,
              child: Center(
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(label, style: display(18, w: FontWeight.w700, color: Colors.white)),
                  if (icon != null) ...[const SizedBox(width: 8), Icon(icon, color: Colors.white, size: 20)],
                ]),
              ),
            ),
          ),
        ),
      );
}

class Pill extends StatelessWidget {
  const Pill(this.text, {super.key, this.fg = C.chip, this.bg = const Color(0x1A6D3FE0)});
  final String text;
  final Color fg;
  final Color bg;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
        child: Text(text, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: fg, letterSpacing: .4)),
      );
}

class Avatar extends StatelessWidget {
  const Avatar({super.key, this.size = 48, this.online = true});
  final double size;
  final bool online;
  @override
  Widget build(BuildContext context) => Stack(clipBehavior: Clip.none, children: [
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 2),
            gradient: const LinearGradient(colors: [Color(0xFFEDE9FE), Color(0xFFFCE7F3)]),
            boxShadow: const [BoxShadow(color: Color(0x336D3FE0), blurRadius: 12, offset: Offset(0, 4))],
          ),
          child: ClipOval(child: Image.asset('assets/images/santosh_head.png', fit: BoxFit.cover)),
        ),
        if (online)
          Positioned(
            right: 0,
            bottom: 0,
            child: Container(
              width: size * .26,
              height: size * .26,
              decoration: BoxDecoration(color: const Color(0xFF16A34A), shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 2)),
            ),
          ),
      ]);
}
