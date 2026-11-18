// v0.907 TOOLS PRO (owner: "CURRENTLY IT IS PINK ICON CARD MAKE IT MORE PREMIUM PROFESSIONAL AND SOFT WITH BLACK PERFECT
// ALIGNED ICONS WITH A CARD ANIMATION" -> "DIFFERENT UNIQUE ICON FOR ALL WITH BIG SIZE" -> "SHOW THE ICON AT CENTER" ->
// "EVERY ICON WITH SLIGHT AND PERFECT ANIMATION" -> "GO WITH B"; design canvas claude.ai/artifact/KMa7vVmS1EpWNRBqCvB8SX):
// one drawing per studio on one 24-unit grid with one line weight (1.7), the same family as the tab bar's icons.
// Each drawing has a still part and one small moving part; the moving part keeps a slow, quiet motion of its own
// (sparkles twinkle, the speech bubble bobs, the sound bars move, the lines get written...). On first show the still
// part draws itself in (`draw` 0..1). Reduce motion = everything still.
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

enum ToolGlyph { create, interactive, vocal, flow, web, app, design, prompting, code, game, connectors }

enum _Move { twinkle, bob, eq, write, breathe, pulse, tilt, spin, blink, press, plug }

/// (still part, moving part, its motion, its period in seconds) - SVG path data on a 24 x 24 grid.
const Map<ToolGlyph, (String, String, _Move, double)> _art = {
  // a magic wand with sparkles around it
  ToolGlyph.create: ('M3.5 20.5L13 11M11.4 9.4l3.2 3.2',
      'M15.5 3v3.4M13.8 4.7h3.4M20 8.2v2.6M18.7 9.5h2.6M19.5 15v2.4M18.3 16.2h2.4M8 4.5v2M7 5.5h2', _Move.twinkle, 2.4),
  // a presenter on a screen, a speech bubble beside it
  ToolGlyph.interactive: (
      'M5 7h8.5A2.5 2.5 0 0 1 16 9.5v8A2.5 2.5 0 0 1 13.5 20H5a2.5 2.5 0 0 1-2.5-2.5v-8A2.5 2.5 0 0 1 5 7zM9.25 14a2 2 0 1 0 0-4a2 2 0 1 0 0 4zM5.6 19.6c.5-2 1.9-3.1 3.65-3.1s3.15 1.1 3.65 3.1',
      'M18 3h3.5a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.3l-1.7 1.6V8H18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z', _Move.bob, 2.8),
  // headphones with a sound wave
  ToolGlyph.vocal: (
      'M3.5 15v-3a8.5 8.5 0 0 1 17 0v3M3.5 15H6a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1zM20.5 15H18a1 1 0 0 0-1 1v3a1 1 0 0 0 1 1h1.5a1 1 0 0 0 1-1z',
      'M10 13.5v3M12 11.5v7M14 13.5v3', _Move.eq, 1.3),
  // a mic turning into lines of text
  ToolGlyph.flow: ('M7 3a2.5 2.5 0 0 1 2.5 2.5v4a2.5 2.5 0 0 1-5 0v-4A2.5 2.5 0 0 1 7 3zM3 9.5a4 4 0 0 0 8 0M7 13.5V16M3.5 20h17',
      'M14 5h7M14 9h5M14 13h7', _Move.write, 3.2),
  // a browser window with code in it
  ToolGlyph.web: (
      'M5 4h14a2.5 2.5 0 0 1 2.5 2.5v11A2.5 2.5 0 0 1 19 20H5a2.5 2.5 0 0 1-2.5-2.5v-11A2.5 2.5 0 0 1 5 4zM2.5 8.5h19M5.6 6.25h.01M8 6.25h.01M10.3 6.25h.01',
      'M10 12l-2.3 2.3 2.3 2.3M14 12l2.3 2.3-2.3 2.3', _Move.breathe, 2.4),
  // a phone full of app tiles
  ToolGlyph.app: (
      'M8.3 2.5h7.4a2.8 2.8 0 0 1 2.8 2.8v13.4a2.8 2.8 0 0 1-2.8 2.8H8.3a2.8 2.8 0 0 1-2.8-2.8V5.3a2.8 2.8 0 0 1 2.8-2.8zM10.8 18h2.4',
      'M9 6.8h2.3v2.3H9zM12.7 6.8H15v2.3h-2.3zM9 10.6h2.3v2.3H9zM12.7 10.6H15v2.3h-2.3z', _Move.pulse, 2.6),
  // a pen curve with its anchors and handle
  ToolGlyph.design: ('M3 16.5h3v3H3zM18 16.5h3v3h-3zM4.5 16.5C5 11 7.6 7.6 10.5 6M19.5 16.5C19 11 16.4 7.6 13.5 6',
      'M10.5 4.5h3v3h-3zM2.5 6h8M13.5 6h8', _Move.tilt, 3.0),
  // a chat bubble with a spark
  ToolGlyph.prompting: (
      'M5 3.5h14A2.5 2.5 0 0 1 21.5 6v8.5A2.5 2.5 0 0 1 19 17h-7.5L7 20.5V17H5a2.5 2.5 0 0 1-2.5-2.5V6A2.5 2.5 0 0 1 5 3.5z',
      'M12 6.8l1.1 2.4 2.4 1.1-2.4 1.1L12 13.8l-1.1-2.4-2.4-1.1 2.4-1.1z', _Move.spin, 3.2),
  // code braces with a cursor between them
  ToolGlyph.code: (
      'M8 4C6 4 5.5 5 5.5 6.5v3c0 1-.7 2-2 2.5 1.3.5 2 1.5 2 2.5v3C5.5 19 6 20 8 20M16 4c2 0 2.5 1 2.5 2.5v3c0 1 .7 2 2 2.5-1.3.5-2 1.5-2 2.5v3c0 1.5-.5 2.5-2.5 2.5',
      'M13.5 8.5l-3 7', _Move.blink, 1.2),
  // a gamepad
  ToolGlyph.game: (
      'M7 7h10a4.5 4.5 0 0 1 4.4 5.4l-1 4.9a2.6 2.6 0 0 1-4.6 1L14.6 16H9.4l-1.2 2.3a2.6 2.6 0 0 1-4.6-1l-1-4.9A4.5 4.5 0 0 1 7 7zM8 10.5v3M6.5 12h3',
      'M15.5 11h.01M17.5 13h.01', _Move.press, 1.6),
  // a plug with its cable
  ToolGlyph.connectors: ('M6.5 6.5h11v3.8a5.5 5.5 0 0 1-11 0V6.5zM12 15.8V18a3 3 0 0 1-3 3H7', 'M8.5 2.5v4M15.5 2.5v4', _Move.plug, 2.2),
};

final Map<ToolGlyph, (Path, Path)> _paths = {};

(Path, Path) _pathsOf(ToolGlyph g) => _paths.putIfAbsent(g, () => (svgPath(_art[g]!.$1), svgPath(_art[g]!.$2)));

/// A small SVG path-data reader (M L H V C S Q A Z, absolute and relative) - enough for Hoola's own drawings.
Path svgPath(String d) {
  final toks = RegExp(r'[MmLlHhVvCcSsQqAaZz]|-?(?:\d+\.?\d*|\.\d+)').allMatches(d).map((m) => m.group(0)!).toList();
  final p = Path();
  var i = 0;
  var cmd = 'M';
  double x = 0, y = 0, sx = 0, sy = 0;
  double? cx2, cy2;   // the last cubic's second control point (for S)
  bool isCmd(String s) => RegExp(r'^[A-Za-z]$').hasMatch(s);
  double n() => double.parse(toks[i++]);
  while (i < toks.length) {
    if (isCmd(toks[i])) cmd = toks[i++];
    final rel = cmd == cmd.toLowerCase();
    final ox = rel ? x : 0.0, oy = rel ? y : 0.0;
    switch (cmd.toUpperCase()) {
      case 'Z':
        p.close();
        x = sx;
        y = sy;
        cx2 = null;
        continue;
      case 'M':
        x = ox + n();
        y = oy + n();
        p.moveTo(x, y);
        sx = x;
        sy = y;
        cmd = rel ? 'l' : 'L';   // more pairs after M are lines
        cx2 = null;
      case 'L':
        x = ox + n();
        y = oy + n();
        p.lineTo(x, y);
        cx2 = null;
      case 'H':
        x = ox + n();
        p.lineTo(x, y);
        cx2 = null;
      case 'V':
        y = oy + n();
        p.lineTo(x, y);
        cx2 = null;
      case 'C':
        final x1 = ox + n(), y1 = oy + n(), x2 = ox + n(), y2 = oy + n();
        x = ox + n();
        y = oy + n();
        p.cubicTo(x1, y1, x2, y2, x, y);
        cx2 = x2;
        cy2 = y2;
      case 'S':
        final x1 = cx2 == null ? x : 2 * x - cx2!, y1 = cy2 == null || cx2 == null ? y : 2 * y - cy2!;
        final x2 = ox + n(), y2 = oy + n();
        x = ox + n();
        y = oy + n();
        p.cubicTo(x1, y1, x2, y2, x, y);
        cx2 = x2;
        cy2 = y2;
      case 'Q':
        final x1 = ox + n(), y1 = oy + n();
        x = ox + n();
        y = oy + n();
        p.quadraticBezierTo(x1, y1, x, y);
        cx2 = null;
      case 'A':
        final rx = n(), ry = n(), rot = n(), large = n() != 0, sweep = n() != 0;
        x = ox + n();
        y = oy + n();
        p.arcToPoint(Offset(x, y), radius: Radius.elliptical(rx, ry), rotation: rot, largeArc: large, clockwise: sweep);
        cx2 = null;
      default:
        i++;   // unknown token: skip it rather than loop
    }
  }
  return p;
}

/// The part of [src] from fraction [a] to [b] of its whole length (all its strokes laid end to end).
Path _part(Path src, double a, double b) {
  final metrics = src.computeMetrics().toList();
  final total = metrics.fold<double>(0, (s, m) => s + m.length);
  final from = total * a.clamp(0.0, 1.0), to = total * b.clamp(0.0, 1.0);
  final out = Path();
  var at = 0.0;
  for (final m in metrics) {
    final s = math.max(from - at, 0.0), e = math.min(to - at, m.length);
    if (e > s) out.addPath(m.extractPath(s, e), Offset.zero);
    at += m.length;
  }
  return out;
}

double _wave(double p) => (1 - math.cos(2 * math.pi * p)) / 2;   // 0 -> 1 -> 0, soft at both ends

/// One studio's icon. [clock] = seconds (a running clock makes the moving part move; null = still);
/// [draw] = how much of the still part is drawn (the opening draw-in); [phase] offsets the motion so icons
/// side by side never move together.
class ToolIcon extends StatelessWidget {
  const ToolIcon({super.key, required this.glyph, required this.color, this.size = 32, this.clock, this.draw = 1, this.phase = 0});
  final ToolGlyph glyph;
  final Color color;
  final double size;
  final ValueListenable<double>? clock;
  final double draw;
  final double phase;

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: CustomPaint(
          size: Size.square(size),
          painter: ToolIconPainter(glyph: glyph, color: color, clock: clock, draw: draw, phase: phase),
        ),
      );
}

class ToolIconPainter extends CustomPainter {
  ToolIconPainter({required this.glyph, required this.color, this.clock, this.draw = 1, this.phase = 0}) : super(repaint: clock);
  final ToolGlyph glyph;
  final Color color;
  final ValueListenable<double>? clock;
  final double draw;
  final double phase;

  static const double stroke = 1.7;

  Paint _paint(double opacity) => Paint()
    ..color = color.withOpacity(color.opacity * opacity.clamp(0.0, 1.0))
    ..style = PaintingStyle.stroke
    ..strokeWidth = stroke
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..isAntiAlias = true;

  @override
  void paint(Canvas canvas, Size size) {
    final (still, moving) = _pathsOf(glyph);
    final art = _art[glyph]!;
    canvas.save();
    canvas.scale(size.width / 24, size.height / 24);
    canvas.drawPath(draw >= 1 ? still : _part(still, 0, draw), _paint(1));

    final secs = clock?.value;
    final p = secs == null ? 0.0 : ((secs + phase) / art.$4) % 1.0;
    final w = secs == null ? 0.0 : _wave(p);
    final box = moving.getBounds();
    final c = box.center;
    var opacity = 1.0;
    var path = moving;
    double sx = 1, sy = 1, rot = 0, tx = 0, ty = 0;
    if (secs != null) {
      switch (art.$3) {
        case _Move.twinkle:
          sx = sy = 1 - .22 * w;
          opacity = 1 - .65 * w;
        case _Move.bob:
          ty = -1.6 * w;
          rot = -5 * w;
        case _Move.eq:
          sy = p < .3 ? 1 - .5 * Curves.easeInOut.transform(p / .3)
              : p < .62 ? .5 + .68 * Curves.easeInOut.transform((p - .3) / .32)
              : 1.18 - .18 * Curves.easeInOut.transform((p - .62) / .38);
        case _Move.write:
          path = p < .5 ? _part(moving, 0, Curves.easeInOut.transform(p / .5))
              : p < .78 ? moving
              : _part(moving, Curves.easeInOut.transform((p - .78) / .22), 1);
        case _Move.breathe:
          sx = 1 + .22 * w;
        case _Move.pulse:
          sx = sy = 1 - .16 * w;
        case _Move.tilt:
          rot = 8 * w;
        case _Move.spin:
          rot = 90 * Curves.easeInOut.transform(p);
          sx = sy = 1 - .2 * w;
        case _Move.blink:
          opacity = p < .45 ? 1 : p < .55 ? 1 - .88 * (p - .45) / .1 : p < .92 ? .12 : .12 + .88 * (p - .92) / .08;
        case _Move.press:
          opacity = 1 - .8 * w;
        case _Move.plug:
          ty = 1.8 * w;
      }
    }
    if (draw < 1) opacity *= ((draw - .6) / .4).clamp(0.0, 1.0);   // the moving part joins once the drawing is nearly done
    canvas.translate(c.dx + tx, c.dy + ty);
    canvas.rotate(rot * math.pi / 180);
    canvas.scale(sx, sy);
    canvas.translate(-c.dx, -c.dy);
    canvas.drawPath(path, _paint(opacity));
    canvas.restore();
  }

  @override
  bool shouldRepaint(ToolIconPainter old) =>
      old.glyph != glyph || old.color != color || old.draw != draw || old.phase != phase || old.clock != clock;
}
