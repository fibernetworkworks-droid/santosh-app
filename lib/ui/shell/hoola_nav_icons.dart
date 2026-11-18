// v0.903 NAV PRO (owner: "CHECK THE BOTTOM NAV. MAKE IT MORE ALIGNED AND PROFESSIONAL, PREMIUM AND SOFT ... PROVIDE
// EVERY NAV PERFECT UNIQUE HD ICONS"): the four tab icons drawn as vectors on one 24-unit grid with one stroke weight,
// so they are sharp at any screen density and read as one family. Each has a quiet outline form and a filled form for
// the selected tab; `on` (0..1) blends between them so the change animates instead of jumping.
//   Hoola        - the Hoola mark: two broken rings, the needle through them, the core
//   AI Employees - a person with the AI spark
//   Tools        - three tiles and a round one (the studios)
//   Computer     - a screen with a prompt, on its stand
import 'dart:math' as math;

import 'package:flutter/material.dart';

enum NavGlyph { hoola, employees, tools, computer }

class NavIcon extends StatelessWidget {
  const NavIcon({super.key, required this.glyph, required this.color, required this.on, required this.cut, this.size = 24});
  final NavGlyph glyph;
  final Color color;
  /// 0 = outline, 1 = filled (selected).
  final double on;
  /// What shows through a filled shape (the prompt on the filled screen): the colour behind the icon.
  final Color cut;
  final double size;

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: CustomPaint(size: Size.square(size), painter: NavIconPainter(glyph, color, on.clamp(0.0, 1.0), cut)),
      );
}

class NavIconPainter extends CustomPainter {
  NavIconPainter(this.glyph, this.color, this.on, this.cut);
  final NavGlyph glyph;
  final Color color;
  final double on;
  final Color cut;

  static const double stroke = 1.7;

  Paint get _line => Paint()
    ..color = color
    ..style = PaintingStyle.stroke
    ..strokeWidth = stroke
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..isAntiAlias = true;

  Paint get _fill => Paint()
    ..color = color.withOpacity(color.opacity * on)
    ..style = PaintingStyle.fill
    ..isAntiAlias = true;

  Paint get _solid => Paint()
    ..color = color
    ..style = PaintingStyle.fill
    ..isAntiAlias = true;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 24, size.height / 24);
    switch (glyph) {
      case NavGlyph.hoola:
        _hoola(canvas);
      case NavGlyph.employees:
        _employees(canvas);
      case NavGlyph.tools:
        _tools(canvas);
      case NavGlyph.computer:
        _computer(canvas);
    }
    canvas.restore();
  }

  void _hoola(Canvas c) {
    const p = math.pi;
    final o = Rect.fromCircle(center: const Offset(12, 12), radius: 9.2);
    final i = Rect.fromCircle(center: const Offset(12, 12), radius: 5.4);
    const go = 26 * p / 180, gi = 34 * p / 180;
    // each ring is cut where the 45-degree needle passes (top right and bottom left)
    c.drawArc(o, -p / 4 + go, p - 2 * go, false, _line);
    c.drawArc(o, 3 * p / 4 + go, p - 2 * go, false, _line);
    c.drawArc(i, -p / 4 + gi, p - 2 * gi, false, _line);
    c.drawArc(i, 3 * p / 4 + gi, p - 2 * gi, false, _line);
    const k = 7.9;
    c.drawLine(const Offset(12 - k, 12 + k), const Offset(12 + k, 12 - k), _line);
    c.drawCircle(const Offset(12, 12), 1.9 + 0.7 * on, _solid);
  }

  void _spark(Canvas c, double cx, double cy, double r) {
    final path = Path()
      ..moveTo(cx, cy - r)
      ..quadraticBezierTo(cx, cy, cx + r, cy)
      ..quadraticBezierTo(cx, cy, cx, cy + r)
      ..quadraticBezierTo(cx, cy, cx - r, cy)
      ..quadraticBezierTo(cx, cy, cx, cy - r)
      ..close();
    c.drawPath(path, _solid);
    c.drawPath(path, _line..strokeWidth = 0.9);
  }

  void _employees(Canvas c) {
    c.drawCircle(const Offset(10, 8), 3.7, _fill);
    c.drawCircle(const Offset(10, 8), 3.7, _line);
    final body = Path()
      ..moveTo(3.4, 20.2)
      ..cubicTo(3.4, 16.2, 6.3, 13.6, 10, 13.6)
      ..cubicTo(13.7, 13.6, 16.6, 16.2, 16.6, 20.2)
      ..close();
    c.drawPath(body, _fill);
    c.drawPath(body, _line);
    _spark(c, 18.6, 5.2, 3.3);
  }

  void _tools(Canvas c) {
    for (final o in const [Offset(3.4, 3.4), Offset(3.4, 13.1), Offset(13.1, 13.1)]) {
      final r = RRect.fromRectAndRadius(o & const Size(7.5, 7.5), const Radius.circular(2.3));
      c.drawRRect(r, _fill);
      c.drawRRect(r, _line);
    }
    c.drawCircle(const Offset(16.85, 7.15), 3.9, _fill);
    c.drawCircle(const Offset(16.85, 7.15), 3.9, _line);
  }

  void _computer(Canvas c) {
    final screen = RRect.fromRectAndRadius(const Rect.fromLTWH(2.6, 3.8, 18.8, 12.6), const Radius.circular(2.6));
    c.drawRRect(screen, _fill);
    c.drawRRect(screen, _line);
    // the prompt: drawn in the line colour on the outline, cut out of the filled screen
    final prompt = _line..color = Color.lerp(color, cut, on)!;
    c.drawPath(Path()
      ..moveTo(7, 8)
      ..lineTo(9.4, 10.1)
      ..lineTo(7, 12.2), prompt);
    c.drawLine(const Offset(11.4, 12.2), const Offset(15, 12.2), prompt);
    c.drawLine(const Offset(12, 16.4), const Offset(12, 19.6), _line);
    c.drawLine(const Offset(8.2, 20.2), const Offset(15.8, 20.2), _line);
  }

  @override
  bool shouldRepaint(NavIconPainter old) => old.glyph != glyph || old.color != color || old.on != on || old.cut != cut;
}
