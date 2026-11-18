// v0.913 CREATE IN COLOUR (design canvas claude.ai/artifact/HXF8gGUqohSnZBnohRkbtu, "GO BUILD"): the colour and glass
// every Create screen stands on. A page has a hue (pictures, clips, films, songs, voices), a slow moving colour light
// behind it, and glass on top - see-through colour over that light, never a blur (the design rules: blur costs frames
// on a budget phone). The painted scenes stand in for a picture where there is none yet (a camera move, a style, an
// idea to start from); the camera moves really move, and everything stands still when the phone asks for less motion.
import 'dart:math' as math;
import 'dart:ui' show PointMode;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';

import '../hoola_theme.dart';

// ------------------------------------------------------------------------------------------------ hue
enum CrHue {
  image(CreateHues.image),
  video(CreateHues.video),
  film(CreateHues.film),
  song(CreateHues.song),
  voice(CreateHues.voice);

  const CrHue(this.pair);
  final List<Color> pair;
  Color get a => pair[0];
  Color get b => pair[1];
  LinearGradient get gradient => LinearGradient(begin: Alignment.centerLeft, end: Alignment.centerRight, colors: pair);

  /// The hue a page stands in (CrPage puts it there); pictures when none.
  static CrHue of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<CrHueScope>()?.hue ?? CrHue.image;
}

class CrHueScope extends InheritedWidget {
  const CrHueScope({super.key, required this.hue, required super.child});
  final CrHue hue;
  @override
  bool updateShouldNotify(CrHueScope old) => old.hue != hue;
}

// ------------------------------------------------------------------------------------------------ glass
/// Glass: a see-through surface over the colour light behind the page - a lit top, a soft diagonal sheen, a rim that
/// catches the light on its top-left edge and the page's hue on its lower-right one, and (with [tint]) a breath of
/// that hue inside. Painted, never blurred (the design rules: blur costs frames on a budget phone). [base] paints a
/// solid colour first, for a dock that must hide what scrolls under it.
Decoration crGlass(HoolaColors c,
        {double radius = 22, Color? edge, bool strong = false, BoxShape shape = BoxShape.rectangle, Color? tint, Color? base}) =>
    CrGlassDecoration(
        dark: c.dark, ink: c.ink, radius: radius, edge: edge, strong: strong, circle: shape == BoxShape.circle, tint: tint, base: base);

class CrGlassDecoration extends Decoration {
  const CrGlassDecoration({
    required this.dark,
    required this.ink,
    this.radius = 22,
    this.edge,
    this.strong = false,
    this.circle = false,
    this.tint,
    this.base,
  });
  final bool dark, strong, circle;
  final Color ink;
  final double radius;
  final Color? edge, tint, base;

  RRect shape(Rect r) => RRect.fromRectAndRadius(r, Radius.circular(circle ? r.shortestSide / 2 : math.min(radius, r.shortestSide / 2)));

  @override
  BoxPainter createBoxPainter([VoidCallback? onChanged]) => _GlassBoxPainter(this);

  @override
  Path getClipPath(Rect rect, TextDirection textDirection) => Path()..addRRect(shape(rect));

  @override
  bool hitTest(Size size, Offset position, {TextDirection? textDirection}) => shape(Offset.zero & size).contains(position);

  CrGlassDecoration _with(Color? e, Color? t) =>
      CrGlassDecoration(dark: dark, ink: ink, radius: radius, edge: e, strong: strong, circle: circle, tint: t, base: base);

  @override
  Decoration? lerpFrom(Decoration? a, double t) {
    if (a is CrGlassDecoration && a.circle == circle) {
      if (t >= 1) return this;
      if (t <= 0) return a;
      return _with(Color.lerp(a.edge ?? Colors.transparent, edge ?? Colors.transparent, t), Color.lerp(a.tint, tint, t));
    }
    return super.lerpFrom(a, t);
  }

  @override
  Decoration? lerpTo(Decoration? b, double t) {
    if (b is CrGlassDecoration && b.circle == circle) {
      if (t <= 0) return this;
      if (t >= 1) return b;
      return _with(Color.lerp(edge ?? Colors.transparent, b.edge ?? Colors.transparent, t), Color.lerp(tint, b.tint, t));
    }
    return super.lerpTo(b, t);
  }

  @override
  bool operator ==(Object o) =>
      o is CrGlassDecoration &&
      o.dark == dark && o.strong == strong && o.circle == circle && o.ink == ink && o.radius == radius &&
      o.edge == edge && o.tint == tint && o.base == base;

  @override
  int get hashCode => Object.hash(dark, strong, circle, ink, radius, edge, tint, base);
}

class _GlassBoxPainter extends BoxPainter {
  _GlassBoxPainter(this.d);
  final CrGlassDecoration d;

  @override
  void paint(Canvas canvas, Offset offset, ImageConfiguration configuration) {
    final size = configuration.size;
    if (size == null || size.isEmpty) return;
    final rect = offset & size;
    final rr = d.shape(rect);
    final dark = d.dark;
    final strong = d.strong;

    // the shadow under the pane (BoxShadow's own paint)
    final shadow = BoxShadow(
        color: dark ? Colors.black.withOpacity(.5) : CreateHues.third.withOpacity(.14),
        blurRadius: 28, spreadRadius: -12, offset: const Offset(0, 14));
    // only OUTSIDE the pane: under see-through glass a shadow would read as a dark box inside it
    canvas.save();
    canvas.clipPath(Path()
      ..fillType = PathFillType.evenOdd
      ..addRect(rect.inflate(80))
      ..addRRect(rr));
    canvas.drawRRect(rr.shift(shadow.offset).inflate(shadow.spreadRadius), shadow.toPaint());
    canvas.restore();

    canvas.save();
    canvas.clipRRect(rr);
    if (d.base != null) canvas.drawRect(rect, Paint()..color = d.base!);
    // the pane: lit at the top, clearer below
    final fill = dark
        ? [Colors.white.withOpacity(strong ? .17 : .13), Colors.white.withOpacity(strong ? .085 : .06), Colors.white.withOpacity(strong ? .06 : .035)]
        : [Colors.white.withOpacity(strong ? .95 : .82), Colors.white.withOpacity(strong ? .8 : .58), Colors.white.withOpacity(strong ? .72 : .44)];
    canvas.drawRect(rect,
        Paint()..shader = LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: fill, stops: const [0, .45, 1]).createShader(rect));
    // a breath of the page's hue, coming in from the top-left corner
    if (d.tint != null) {
      final at = rect.topLeft + Offset(rect.width * .12, 0);
      final r = math.max(rect.width, rect.height) * 1.05;
      canvas.drawRect(rect, Paint()
        ..shader = RadialGradient(colors: [d.tint!.withOpacity(dark ? .2 : .13), d.tint!.withOpacity(0)])
            .createShader(Rect.fromCircle(center: at, radius: r)));
      final low = rect.bottomRight - Offset(rect.width * .1, 0);
      canvas.drawRect(rect, Paint()
        ..shader = RadialGradient(colors: [CreateHues.third.withOpacity(dark ? .1 : .06), CreateHues.third.withOpacity(0)])
            .createShader(Rect.fromCircle(center: low, radius: r * .7)));
    }
    // a soft diagonal sheen, as light lies on glass
    canvas.drawRect(rect, Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Colors.white.withOpacity(0), Colors.white.withOpacity(dark ? .06 : .3), Colors.white.withOpacity(0)],
        stops: const [.08, .26, .46],
      ).createShader(rect));
    canvas.restore();

    // the rim: bright where the light comes from, the hue where it leaves
    final rim = rr.deflate(.6);
    if (d.edge != null) {
      canvas.drawRRect(rim, Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6
        ..color = d.edge!);
    } else {
      final far = d.tint ?? (dark ? Colors.white : d.ink);
      final colors = dark
          ? [Colors.white.withOpacity(strong ? .42 : .32), Colors.white.withOpacity(.08), far.withOpacity(d.tint != null ? .3 : .06)]
          : [Colors.white, Colors.white.withOpacity(.55), (d.tint ?? d.ink).withOpacity(d.tint != null ? .22 : .08)];
      canvas.drawRRect(rim, Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.1
        ..shader = LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: colors, stops: const [0, .5, 1])
            .createShader(rect));
    }
  }
}

/// The soft fill of an unpicked chip or a quiet tray.
Color crWash(HoolaColors c) => c.dark ? Colors.white.withOpacity(.08) : c.ink.withOpacity(.055);

// ------------------------------------------------------------------------------------------------ the moving colour light
/// Three soft lights in the page's hue that drift very slowly behind everything (still under reduce motion).
class CrAura extends StatefulWidget {
  const CrAura({super.key, required this.hue});
  final CrHue hue;
  @override
  State<CrAura> createState() => _CrAuraState();
}

class _CrAuraState extends State<CrAura> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: const Duration(seconds: 16));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (HoolaMotion.reduced(context)) {
      _a.stop();
    } else if (!_a.isAnimating) {
      _a.repeat(reverse: true);
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
    return IgnorePointer(
      child: Stack(fit: StackFit.expand, children: [
        RepaintBoundary(child: CustomPaint(painter: _AuraPainter(_a, widget.hue, c.dark), size: Size.infinite)),
        // a fine still grain over the light, like film: colour that looks made, not rendered
        RepaintBoundary(child: CustomPaint(painter: _GrainPainter(c.dark), size: Size.infinite)),
      ]),
    );
  }
}

class _AuraPainter extends CustomPainter {
  _AuraPainter(this.t, this.hue, this.dark) : super(repaint: t);
  final Animation<double> t;
  final CrHue hue;
  final bool dark;
  @override
  void paint(Canvas canvas, Size size) {
    final v = Curves.easeInOut.transform(t.value);
    final w = size.width;
    final h = size.height;
    void blob(Offset at, double r, Color col, double alpha) {
      canvas.drawCircle(
        at,
        r,
        Paint()
          ..shader = RadialGradient(colors: [col.withOpacity(alpha), col.withOpacity(alpha * .45), col.withOpacity(0)], stops: const [0, .45, 1])
              .createShader(Rect.fromCircle(center: at, radius: r)),
      );
    }

    // the light lives across the whole page, not just its top: glass far down the page has colour to show through
    final k = dark ? 1.0 : 1.15;
    blob(Offset(w * (.14 + .07 * v), h * (.08 + .03 * v)), w * .78, hue.a, .4 * k);
    blob(Offset(w * (.9 - .06 * v), h * (.18 + .04 * v)), w * .66, hue.b, .34 * k);
    blob(Offset(w * (.5 + .06 * v), h * (.44 - .03 * v)), w * .62, CreateHues.third, .24 * k);
    blob(Offset(w * (.08 + .05 * v), h * (.7 + .04 * v)), w * .6, hue.b, .22 * k);
    blob(Offset(w * (.92 - .05 * v), h * (.9 - .03 * v)), w * .7, hue.a, .26 * k);
  }

  @override
  bool shouldRepaint(_AuraPainter o) => o.hue != hue || o.dark != dark;
}

class _GrainPainter extends CustomPainter {
  _GrainPainter(this.dark);
  final bool dark;
  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final rnd = math.Random(7);
    final n = (size.width * size.height / 240).clamp(0, 4000).toInt();
    final light = <Offset>[], shade = <Offset>[];
    for (var i = 0; i < n; i++) {
      (i.isEven ? light : shade).add(Offset(rnd.nextDouble() * size.width, rnd.nextDouble() * size.height));
    }
    final p = Paint()
      ..strokeWidth = 1.1
      ..strokeCap = StrokeCap.round;
    canvas.drawPoints(PointMode.points, light, p..color = Colors.white.withOpacity(dark ? .035 : .18));
    canvas.drawPoints(PointMode.points, shade, p..color = Colors.black.withOpacity(dark ? .12 : .03));
  }

  @override
  bool shouldRepaint(_GrainPainter o) => o.dark != dark;
}

// ------------------------------------------------------------------------------------------------ painted scenes
/// A painted stand-in picture (see CreateScene in hoola_theme.dart).
class CrScene extends StatelessWidget {
  const CrScene(this.name, {super.key});
  final String name;
  @override
  Widget build(BuildContext context) =>
      RepaintBoundary(child: CustomPaint(painter: _ScenePainter(CreateScene.all[name] ?? CreateScene.sunset), size: Size.infinite));
}

class _ScenePainter extends CustomPainter {
  _ScenePainter(this.s);
  final CreateScene s;
  @override
  void paint(Canvas canvas, Size size) {
    final r = Offset.zero & size;
    final w = size.width, h = size.height;
    canvas.drawRect(r, Paint()..shader = LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: s.sky).createShader(r));
    for (final g in s.glows) {
      final at = Offset(w * g.$1, h * g.$2);
      final rad = w * g.$3;
      final halo = rad * 3.4;
      canvas.drawCircle(at, halo, Paint()
        ..shader = RadialGradient(colors: [g.$5.withOpacity(.75), g.$5.withOpacity(.22), g.$5.withOpacity(0)], stops: const [0, .45, 1])
            .createShader(Rect.fromCircle(center: at, radius: halo)));
      canvas.drawCircle(at, rad, Paint()
        ..shader = RadialGradient(colors: [g.$4, g.$5]).createShader(Rect.fromCircle(center: at, radius: rad)));
    }
    if (s.ground != null) {
      final top = h * s.groundTop;
      final p = Path()
        ..moveTo(0, top + h * .04)
        ..quadraticBezierTo(w * .35, top - h * .05, w * .62, top + h * .01)
        ..quadraticBezierTo(w * .85, top + h * .05, w, top - h * .02)
        ..lineTo(w, h)
        ..lineTo(0, h)
        ..close();
      canvas.drawPath(p, Paint()..color = s.ground!);
    }
    for (final o in s.shapes) {
      final at = Offset(w * o.$1, h * o.$2);
      final rad = w * o.$3;
      canvas.drawOval(Rect.fromCenter(center: at.translate(0, rad * 1.05), width: rad * 2.4, height: rad * .5),
          Paint()..color = Colors.black.withOpacity(.16));
      canvas.drawCircle(at, rad, Paint()..color = o.$5);
      canvas.drawCircle(at, rad * .82, Paint()..color = o.$4);
      canvas.drawCircle(at.translate(-rad * .32, -rad * .34), rad * .2, Paint()..color = Colors.white.withOpacity(.28));
    }
    if (s.rainy) {
      final p = Paint()
        ..color = Colors.white.withOpacity(.12)
        ..strokeWidth = 1.2;
      for (var x = -h; x < w; x += 13) {
        canvas.drawLine(Offset(x, h), Offset(x + h * .25, 0), p);
      }
    }
  }

  @override
  bool shouldRepaint(_ScenePainter o) => o.s != s;
}

// ------------------------------------------------------------------------------------------------ camera moves
/// The camera moves Create can ask for, as they look on a card: how the picture moves inside its frame.
class CrMove extends StatefulWidget {
  const CrMove({super.key, required this.move, required this.child, this.still = false});
  final String move;
  final Widget child;
  /// Hold still (a picked card in a long list, or reduce motion).
  final bool still;
  @override
  State<CrMove> createState() => _CrMoveState();
}

class _CrMoveState extends State<CrMove> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: _length(widget.move));

  static Duration _length(String m) => switch (m) {
        'Crash zoom' => const Duration(milliseconds: 2600),
        'Handheld' => const Duration(milliseconds: 2400),
        'Orbit' || 'Pan' || 'Tracking' => const Duration(seconds: 5),
        'Drone' => const Duration(seconds: 6),
        _ => const Duration(seconds: 4),
      };

  bool get _loops => widget.move == 'Crash zoom' || widget.move == 'Handheld';

  void _run() {
    if (widget.still || widget.move == 'Static' || HoolaMotion.reduced(context)) {
      _a.stop();
      _a.value = widget.move == 'Crash zoom' ? 0 : .35;
    } else if (!_a.isAnimating) {
      _loops ? _a.repeat() : _a.repeat(reverse: true);
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _run();
  }

  @override
  void didUpdateWidget(CrMove old) {
    super.didUpdateWidget(old);
    if (old.still != widget.still || old.move != widget.move) {
      _a.stop();
      _run();
    }
  }

  @override
  void dispose() {
    _a.dispose();
    super.dispose();
  }

  Matrix4 _at(double t) {
    final e = Curves.easeInOut.transform(t);
    final m = Matrix4.identity();
    // doubles only: Matrix4.translate / scale throw UnimplementedError for an int
    void scale(double s) => m.scale(s, s, 1.0);
    void move(double x, double y) => m.translate(x, y, 0.0);
    switch (widget.move) {
      case 'Dolly in' || 'Auto' || 'Low angle':
        scale(1 + .3 * e);
      case 'Dolly out':
        scale(1.3 - .3 * e);
      case 'Orbit' || 'Pan':
        move(-14 + 28 * e, 0);
        scale(1.22);
      case 'Tracking':
        move(14 - 28 * e, 0);
        scale(1.22);
      case 'Crane up':
        move(0, 16 - 30 * e);
        scale(1.26);
      case 'Crash zoom':
        final k = t < .4 ? 0.0 : (t < .55 ? Curves.easeOutCubic.transform((t - .4) / .15) : 1.0);
        scale(1 + .6 * k);
      case 'Handheld':
        final a = t * math.pi * 2;
        move(4 * math.sin(a), 3 * math.cos(a * 2));
        m.rotateZ(.012 * math.sin(a * 3));
        scale(1.16);
      case 'Drone':
        move(-8 + 16 * e, 0);
        m.rotateZ(-.06 + .1 * e);
        scale(1.12 + .3 * e);
      default:
        break;
    }
    return m;
  }

  @override
  Widget build(BuildContext context) => ClipRect(
        child: AnimatedBuilder(
          animation: _a,
          child: widget.child,
          builder: (_, child) => Transform(alignment: Alignment.center, transform: _at(_a.value), child: child),
        ),
      );
}

/// v0.920 one camera move, alive: the chai stall at dusk (sun + hills, stall or lamp posts, her with a cup of chai,
/// the table up front) drawn in four layers that move the way that camera move moves - the near layers more than
/// the far ones, so a dolly, a crane or an orbit reads as a real camera. Design canvas KZ2Svgxm8fZPrEWt5zjKYD.
/// Still under reduce motion (and the steam rests).
class CrCamScene extends StatefulWidget {
  const CrCamScene({super.key, required this.move, this.still = false});
  final String move;
  final bool still;
  @override
  State<CrCamScene> createState() => _CrCamSceneState();
}

class _CrCamSceneState extends State<CrCamScene> with SingleTickerProviderStateMixin {
  final _clock = ValueNotifier<double>(0);
  late final Ticker _ticker = createTicker((d) => _clock.value = d.inMicroseconds / 1e6);

  void _run() {
    final hold = widget.still || HoolaMotion.reduced(context);
    if (hold) {
      if (_ticker.isActive) _ticker.stop();
      _clock.value = 0;
    } else if (!_ticker.isActive) {
      _ticker.start();
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _run();
  }

  @override
  void didUpdateWidget(CrCamScene old) {
    super.didUpdateWidget(old);
    if (old.still != widget.still) _run();
  }

  @override
  void dispose() {
    _ticker.dispose();
    _clock.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: CustomPaint(painter: _CamScenePainter(widget.move, _clock), size: Size.infinite),
      );
}

class _CamScenePainter extends CustomPainter {
  _CamScenePainter(this.move, this.clock) : super(repaint: clock);
  final String move;
  final ValueNotifier<double> clock;

  // ---- time helpers (CSS keyframes in the design, as numbers)
  static double _ease(double p) => Curves.easeInOut.transform(p.clamp(0.0, 1.0));
  static double _alt(double s, double dur) {
    final p = (s / dur) % 2;
    return _ease(p > 1 ? 2 - p : p);
  }

  static double _loop(double s, double dur) => (s / dur) % 1;

  /// A value through keys (at, value, the curve from that key to the next), p in 0..1.
  static double _keys(double p, List<(double, double, Curve)> k) {
    for (var i = 0; i < k.length - 1; i++) {
      final a = k[i], b = k[i + 1];
      if (p <= b.$1) {
        if (b.$1 == a.$1) return b.$2;
        final f = a.$3.transform(((p - a.$1) / (b.$1 - a.$1)).clamp(0.0, 1.0));
        return a.$2 + (b.$2 - a.$2) * f;
      }
    }
    return k.last.$2;
  }

  static double _lerp(double a, double b, double t) => a + (b - a) * t;

  // ---- matrix helpers: CSS "scale(a) translate(x, y)" about an origin
  static Matrix4 _st(double sx, double sy, double x, double y, [double ox = 122, double oy = 112]) =>
      Matrix4.translationValues(ox, oy, 0)
        ..scale(sx, sy, 1.0)
        ..translate(x, y, 0.0)
        ..translate(-ox, -oy, 0.0);
  static Matrix4 _s(double k, [double ox = 122, double oy = 112]) => _st(k, k, 0, 0, ox, oy);
  static Matrix4 _t(double x, double y) => Matrix4.translationValues(x, y, 0);

  static const _io = Curves.easeInOut;
  static const _crashIn = Cubic(.7, 0, .9, .4);

  @override
  void paint(Canvas canvas, Size size) {
    final s = clock.value;
    final pal = CreateCamScene.all[move] ?? CreateCamScene.all['Auto']!;
    final tracking = move == 'Tracking';
    Matrix4? rig, bg, mid, subj, fg;
    double hillsX = 0, postsX = 0, roadX = 0;

    switch (move) {
      case 'Auto':
        final e = _alt(s, 7);
        bg = _st(_lerp(1, 1.04, e), _lerp(1, 1.04, e), _lerp(0, -3, e), 0);
        mid = _st(_lerp(1, 1.09, e), _lerp(1, 1.09, e), _lerp(0, -5, e), 0);
        subj = _st(_lerp(1, 1.14, e), _lerp(1, 1.14, e), _lerp(0, -6, e), 0);
        fg = _st(_lerp(1, 1.22, e), _lerp(1, 1.22, e), _lerp(0, -10, e), 0);
      case 'Dolly in' || 'Dolly out':
        final p = _loop(s, 5);
        final inn = move == 'Dolly in';
        double k(double far) => inn
            ? _keys(p, [(0, 1, _io), (.12, 1, _io), (.78, far, _io), (.9, far, _io), (1, 1, _io)])
            : _keys(p, [(0, far, _io), (.12, far, _io), (.78, 1, _io), (.9, 1, _io), (1, far, _io)]);
        bg = _s(k(1.07));
        mid = _s(k(inn ? 1.18 : 1.2));
        subj = _s(k(inn ? 1.34 : 1.4));
        fg = _s(k(inn ? 1.62 : 1.7));
      case 'Crash zoom':
        final p = _loop(s, 3.4);
        rig = _s(_keys(p, [(0, 1, _io), (.38, 1, _crashIn), (.46, 1.95, _io), (.8, 1.95, _io), (.92, 1, _io), (1, 1, _io)]), 123, 98);
      case 'Orbit':
        final e = _alt(s, 4.5);
        bg = _t(_lerp(18, -18, e), 0);
        mid = _t(_lerp(10, -10, e), 0);
        final raw = (s / 4.5) % 2;
        final p = raw > 1 ? 2 - raw : raw;
        subj = _st(_keys(p, [(0, 1, _io), (.5, .84, _io), (1, 1, _io)]), 1, 0, 0);
        fg = _t(_lerp(-46, 46, e), 0);
      case 'Crane up':
        final e = _alt(s, 5);
        bg = _t(0, 4 * e);
        mid = _t(0, 16 * e);
        subj = _t(0, 24 * e);
        fg = _t(0, 52 * e);
      case 'Tracking':
        hillsX = -100 * _loop(s, 6);
        postsX = -60 * _loop(s, 1.6);
        roadX = -40 * _loop(s, .8);
        subj = _t(0, -2 * _alt(s, .4));
      case 'Pan':
        rig = _t(_lerp(20, -20, _alt(s, 5)), 0);
      case 'Drone':
        final e = _alt(s, 6);
        bg = _s(_lerp(1.2, 1, e), 110, 168);
        mid = _s(_lerp(1.5, .9, e), 110, 168);
        subj = _s(_lerp(1.6, .82, e), 110, 168);
        fg = _st(_lerp(2.2, .7, e), _lerp(2.2, .7, e), 0, _lerp(0, 30, e), 110, 168);
      case 'Handheld':
        final p = _loop(s, 2.2);
        final ks = [0.0, .17, .33, .5, .67, .83, 1.0];
        double at(List<double> v) => _keys(p, [for (var i = 0; i < ks.length; i++) (ks[i], v[i], _io)]);
        final x = at([0, 1.6, -1.2, .8, -1.6, 1, 0]);
        final y = at([0, -1, .8, 1.4, -.6, .4, 0]);
        final r = at([0, .5, -.4, .3, -.5, .2, 0]) * math.pi / 180;
        rig = Matrix4.translationValues(100, 100, 0)
          ..translate(x, y, 0.0)
          ..rotateZ(r)
          ..translate(-100.0, -100.0, 0.0);
      case 'Low angle':
        final e = _alt(s, 5);
        final k = _lerp(1.25, 1.33, e);
        subj = _st(k, k, 0, _lerp(0, -3, e), 123, 172);
        bg = _t(0, _lerp(28, 32, e));
        mid = _t(0, _lerp(22, 25, e));
        final f = _lerp(1.2, 1.24, e);
        fg = Matrix4.translationValues(0, _lerp(14, 16, e), 0)..multiply(_s(f));
      default:
        break; // Static: the camera holds, only the steam moves
    }

    // fit a 200 x 200 picture over the tile, cut at the sides (like "slice")
    final k = math.max(size.width, size.height) / 200;
    canvas.save();
    canvas.clipRect(Offset.zero & size);
    canvas.translate((size.width - 200 * k) / 2, (size.height - 200 * k) / 2);
    canvas.scale(k, k);

    const box = Rect.fromLTWH(0, 0, 200, 200);
    canvas.drawRect(box, Paint()..shader = LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [pal.skyTop, pal.skyBottom]).createShader(box));

    void layer(Matrix4? m, void Function() draw) {
      canvas.save();
      if (m != null) canvas.transform(m.storage);
      draw();
      canvas.restore();
    }

    final fill = Paint();
    Paint col(Color c) => fill..color = c;

    layer(rig, () {
      // far: the sun and rolling hills
      layer(bg, () {
        canvas.drawCircle(const Offset(152, 46), 15, col(CreateCamScene.sun.withOpacity(.9)));
        canvas.save();
        canvas.translate(hillsX, 0);
        final hills = Path()..moveTo(-100, 128);
        // the design's "q25 -18 50 0 t50 0 ...": one bump up, one dip down, so the row repeats every 100
        var up = true;
        for (var x = -100.0; x < 300; x += 50) {
          hills.quadraticBezierTo(x + 25, up ? 110 : 146, x + 50, 128);
          up = !up;
        }
        hills
          ..lineTo(300, 200)
          ..lineTo(-100, 200)
          ..close();
        canvas.drawPath(hills, col(pal.hill));
        canvas.restore();
      });
      // middle: the ground and the chai stall (or lamp posts going by when tracking)
      layer(mid, () {
        canvas.drawRect(const Rect.fromLTWH(-100, 140, 400, 80), col(pal.ground));
        if (!tracking) {
          canvas.drawRect(const Rect.fromLTWH(28, 96, 4, 46), col(CreateCamScene.wood));
          canvas.drawRect(const Rect.fromLTWH(86, 96, 4, 46), col(CreateCamScene.wood));
          canvas.drawPath(
              Path()
                ..moveTo(22, 96)
                ..lineTo(30, 84)
                ..lineTo(88, 84)
                ..lineTo(96, 96)
                ..close(),
              col(CreateCamScene.awning));
          final stripe = Paint()
            ..color = CreateCamScene.stripe
            ..strokeWidth = 5;
          canvas.drawLine(const Offset(42, 84), const Offset(40, 96), stripe);
          canvas.drawLine(const Offset(58, 84), const Offset(58, 96), stripe);
          canvas.drawLine(const Offset(74, 84), const Offset(76, 96), stripe);
          canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(26, 118, 68, 24), const Radius.circular(2)), col(CreateCamScene.counter));
          for (final b in const [Offset(44, 102), Offset(60, 104), Offset(76, 102)]) {
            canvas.drawCircle(b, 2.5, col(CreateCamScene.bulb));
          }
        } else {
          canvas.save();
          canvas.translate(postsX, 0);
          for (var x = -60.0; x <= 240; x += 60) {
            canvas.drawRect(Rect.fromLTWH(x, 92, 3, 50), col(CreateCamScene.post));
            canvas.drawCircle(Offset(x + 1.5, 90), 4, col(CreateCamScene.bulb));
          }
          canvas.restore();
        }
      });
      // her, with a cup of chai and its steam
      layer(subj, () {
        canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(116, 146, 5, 24), const Radius.circular(2)), col(CreateCamScene.post));
        canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(125, 146, 5, 24), const Radius.circular(2)), col(CreateCamScene.post));
        canvas.drawPath(
            Path()
              ..moveTo(110, 150)
              ..quadraticBezierTo(112, 116, 123, 112)
              ..quadraticBezierTo(134, 116, 136, 150)
              ..close(),
            col(CreateCamScene.kurta));
        canvas.drawPath(
            Path()
              ..moveTo(114, 118)
              ..quadraticBezierTo(124, 132, 134, 120)
              ..lineTo(136, 128)
              ..quadraticBezierTo(124, 140, 112, 126)
              ..close(),
            col(CreateCamScene.dupatta));
        canvas.drawCircle(const Offset(123, 100), 10, col(CreateCamScene.skin));
        canvas.drawPath(
            Path()
              ..moveTo(113, 99)
              ..quadraticBezierTo(114, 88, 123, 88)
              ..quadraticBezierTo(133, 88, 133, 99)
              ..quadraticBezierTo(128, 93, 123, 94)
              ..quadraticBezierTo(117, 93, 113, 99)
              ..close(),
            col(CreateCamScene.hair));
        canvas.drawPath(
            Path()
              ..moveTo(132, 120)
              ..quadraticBezierTo(142, 128, 138, 136),
            Paint()
              ..color = CreateCamScene.skin
              ..style = PaintingStyle.stroke
              ..strokeWidth = 4
              ..strokeCap = StrokeCap.round);
        canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(134, 132, 8, 9), const Radius.circular(1.5)), col(CreateCamScene.cup));
        void steam(double delay, double x, double dx, double up) {
          final p = s == 0 ? .4 : _loop(s - delay, 2.6);
          final o = _keys(p, [(0, 0, _io), (.4, .85, _io), (1, 0, _io)]);
          if (o <= 0) return;
          final y = _lerp(4, -10, _ease(p));
          canvas.drawPath(
              Path()
                ..moveTo(x, 128 + y)
                ..quadraticBezierTo(x + dx, 123 + y, x, 128 - up + y),
              Paint()
                ..color = Colors.white.withOpacity(o)
                ..style = PaintingStyle.stroke
                ..strokeWidth = 1.4
                ..strokeCap = StrokeCap.round);
        }

        steam(0, 136, -3, 9);
        steam(1.1, 140, 3, 10);
      });
      // near: the table with a cup and two oranges (or the road rushing by when tracking)
      layer(fg, () {
        if (!tracking) {
          canvas.drawRect(const Rect.fromLTWH(-20, 172, 240, 40), col(CreateCamScene.table));
          canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(30, 160, 9, 12), const Radius.circular(1.5)), col(CreateCamScene.cup));
          canvas.drawCircle(const Offset(178, 166), 9, col(CreateCamScene.orange));
          canvas.drawCircle(const Offset(188, 171), 7, col(CreateCamScene.orange2));
        } else {
          canvas.save();
          canvas.translate(roadX, 0);
          final dash = Paint()..color = Colors.white.withOpacity(.4);
          for (var x = 0.0; x <= 240; x += 40) {
            canvas.drawRect(Rect.fromLTWH(x, 186, 20, 3), dash);
          }
          canvas.restore();
        }
      });
    });
    canvas.restore();
  }

  @override
  bool shouldRepaint(_CamScenePainter old) => old.move != move || old.clock != clock;
}

// ------------------------------------------------------------------------------------------------ pieces
/// A colour circle with a drawing on it (a studio, a voice). [child] sits on the hue in its dark ink.
class CrOrb extends StatelessWidget {
  const CrOrb({super.key, required this.hue, required this.child, this.size = 52, this.sweep});
  final CrHue hue;
  final Widget child;
  final double size;
  /// v0.915 a light passing across the bead (0..1), null = none.
  final double? sweep;
  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: hue.pair),
          boxShadow: [
            BoxShadow(color: hue.a.withOpacity(.38), blurRadius: 18, spreadRadius: -6, offset: const Offset(0, 7)),
            BoxShadow(color: hue.b.withOpacity(.22), blurRadius: 10, spreadRadius: -4, offset: const Offset(0, 2)),
          ],
        ),
        // a bright hairline round the bead, like the edge of glass
        foregroundDecoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white.withOpacity(.42), width: 1)),
        alignment: Alignment.center,
        child: Stack(alignment: Alignment.center, children: [
          Positioned.fill(child: IgnorePointer(child: CustomPaint(painter: _OrbGlass(sweep)))),
          child,
        ]),
      );
}

/// The glass on a colour bead: a lit cap on top, a soft glow in the bottom, and (while the drawing moves) a band of light
/// crossing it. Painted, never blurred.
class _OrbGlass extends CustomPainter {
  _OrbGlass(this.sweep);
  final double? sweep;
  @override
  void paint(Canvas canvas, Size s) {
    if (s.isEmpty) return;
    final r = Offset.zero & s;
    canvas.save();
    canvas.clipPath(Path()..addOval(r));
    final cap = Rect.fromLTWH(s.width * .17, s.height * .05, s.width * .66, s.height * .44);
    canvas.drawOval(
        cap,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.white.withOpacity(.55), Colors.white.withOpacity(0)],
          ).createShader(cap));
    final low = Offset(s.width * .5, s.height * 1.04);
    canvas.drawCircle(
        low,
        s.width * .5,
        Paint()
          ..shader = RadialGradient(colors: [Colors.white.withOpacity(.26), Colors.white.withOpacity(0)])
              .createShader(Rect.fromCircle(center: low, radius: s.width * .5)));
    final w = sweep;
    if (w != null && w > 0 && w < 1) {
      final p = w.clamp(0.0, 1.0);
      final a = (p - .16).clamp(0.0, 1.0), b = (p + .16).clamp(0.0, 1.0);
      canvas.drawRect(
          r,
          Paint()
            ..shader = LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Colors.white.withOpacity(0), Colors.white.withOpacity(.42), Colors.white.withOpacity(0)],
              stops: [a, p, b],
            ).createShader(r));
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(_OrbGlass o) => o.sweep != sweep;
}

/// v0.915 each drawing's own small move: [a] runs 0..1 once, the drawing ends where it began.
Matrix4 crGlyphMove(String kind, double a, double px) {
  final s = math.sin(a * math.pi); // 0 -> 1 -> 0
  final w = math.sin(a * math.pi * 2); // 0 -> 1 -> -1 -> 0
  final u = px / 24;
  var dx = 0.0, dy = 0.0, rot = 0.0, sc = 1.0;
  switch (kind) {
    case 'image': // the picture tilts like a print picked up
      rot = .16 * w;
      sc = 1 + .1 * s;
    case 'video': // rolls forward
      dx = 2.2 * u * w;
      sc = 1 + .07 * s;
    case 'film': // the clapper claps
      rot = -.3 * s;
      dy = -1.2 * u * s;
    case 'music': // a note hops
      dy = -3.2 * u * s;
      rot = .18 * w;
    case 'voice': // breathes
      sc = 1 + .14 * s;
    case 'dub': // two voices, one after the other
      dx = 2.4 * u * w;
      rot = .1 * w;
    case 'cut': // snips
      rot = .42 * w;
    case 'pen': // writes a little line
      dx = 2.6 * u * w;
      dy = -1.6 * u * s;
      rot = -.18 * s;
    case 'cast': // a person steps up
      dy = -2.6 * u * s;
      sc = 1 + .06 * s;
    case 'cinema': // the reel turns
      rot = math.pi / 2 * Curves.easeInOutCubic.transform(a);
      sc = 1 + .05 * s;
    case 'brand': // the star turns one point and shines
      rot = 2 * math.pi / 5 * Curves.easeInOutCubic.transform(a);
      sc = 1 + .16 * s;
    case 'grid': // the tiles settle into place
      rot = math.pi / 2 * Curves.easeInOutCubic.transform(a);
      sc = 1 - .1 * s;
    default:
      sc = 1 + .08 * s;
  }
  return Matrix4.identity()
    ..translate(dx, dy, 0.0)
    ..rotateZ(rot)
    ..scale(sc, sc, 1.0);
}

/// Rings that spread from a sound bead while it moves (voice, music).
class CrRings extends CustomPainter {
  CrRings(this.a, this.color);
  final double a;
  final Color color;
  @override
  void paint(Canvas canvas, Size s) {
    if (a <= 0 || a >= 1) return;
    final c = s.center(Offset.zero);
    for (final lag in const [0.0, .3]) {
      final t = ((a - lag) / (1 - lag)).clamp(0.0, 1.0);
      if (t <= 0) continue;
      canvas.drawCircle(
          c,
          s.width / 2 * (1 + .42 * t),
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.6
            ..color = color.withOpacity(.55 * (1 - t)));
    }
  }

  @override
  bool shouldRepaint(CrRings o) => o.a != a || o.color != color;
}

/// A small dark see-through label over a picture (5 s, 4:5, Scene 2).
class CrBadge extends StatelessWidget {
  const CrBadge(this.text, {super.key, this.leading});
  final String text;
  final Widget? leading;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      height: 26,
      padding: const EdgeInsets.symmetric(horizontal: 9),
      decoration: BoxDecoration(
        color: CreateHues.night.withOpacity(.46),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: Colors.white.withOpacity(.22)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (leading != null) ...[leading!, const SizedBox(width: 5)],
        Flexible(
          child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: HoolaType.label(c).copyWith(color: Colors.white, fontSize: 12)),
        ),
      ]),
    );
  }
}

/// A picture-like card: [art] fills it, a dark fade at the bottom carries the words in white, an optional badge sits
/// top left. [picked] rings it in the page's hue.
class CrArtCard extends StatelessWidget {
  const CrArtCard({super.key, required this.art, this.title = '', this.line = '', this.badge, this.onTap, this.picked = false,
      this.radius = 18, this.label, this.trailing});
  final Widget art;
  final String title, line;
  final Widget? badge, trailing;
  final VoidCallback? onTap;
  final bool picked;
  final double radius;
  final String? label;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final hue = CrHue.of(context);
    final words = title.isNotEmpty || line.isNotEmpty;
    Widget card = ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: Stack(fit: StackFit.expand, children: [
        art,
        if (words)
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color.fromARGB(0, 10, 8, 18), Color.fromARGB(0, 10, 8, 18), Color.fromARGB(190, 10, 8, 18)],
                stops: [0, .42, 1],
              ),
            ),
          ),
        // v0.914 the card reads as glass over a picture: light on its top-left, a bright hairline round the edge
        IgnorePointer(
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(radius),
              border: Border.all(color: Colors.white.withOpacity(.2), width: 1),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Colors.white.withOpacity(.16), Colors.white.withOpacity(0)],
                stops: const [0, .34],
              ),
            ),
          ),
        ),
        if (badge != null) Positioned(left: 8, top: 8, right: 44, child: Align(alignment: Alignment.centerLeft, child: badge!)),
        if (trailing != null) Positioned(right: 8, top: 8, child: trailing!),
        if (words)
          Positioned(
            left: 11,
            right: 11,
            bottom: 10,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              if (title.isNotEmpty)
                Text(title, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: HoolaType.body(c).copyWith(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600, height: 1.25)),
              if (line.isNotEmpty)
                Text(line, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: HoolaType.small(c).copyWith(color: Colors.white.withOpacity(.88), fontSize: 12.5, height: 1.3)),
            ]),
          ),
      ]),
    );
    card = AnimatedContainer(
      duration: HoolaMotion.of(context, HoolaMotion.menu),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius + 4),
        border: Border.all(color: picked ? hue.b : Colors.transparent, width: 2.4),
        boxShadow: picked ? [BoxShadow(color: hue.b.withOpacity(.35), blurRadius: 18, spreadRadius: -6)] : null,
      ),
      padding: const EdgeInsets.all(2.5),
      child: card,
    );
    if (onTap == null) return card;
    return Semantics(
      button: true,
      selected: picked,
      label: label ?? [title, line].where((s) => s.isNotEmpty).join('. '),
      excludeSemantics: true,
      onTap: onTap,
      child: _Press(onTap: onTap!, child: card),
    );
  }
}

/// Sinks a little under the finger, then springs back.
class _Press extends StatefulWidget {
  const _Press({required this.onTap, required this.child});
  final VoidCallback onTap;
  final Widget child;
  @override
  State<_Press> createState() => _PressState();
}

class _PressState extends State<_Press> {
  bool _down = false;
  @override
  Widget build(BuildContext context) => GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => setState(() => _down = true),
        onTapCancel: () => setState(() => _down = false),
        onTapUp: (_) => setState(() => _down = false),
        onTap: () {
          HapticFeedback.selectionClick();
          widget.onTap();
        },
        child: AnimatedScale(
          scale: _down ? .97 : 1,
          duration: HoolaMotion.of(context, const Duration(milliseconds: 120)),
          curve: HoolaMotion.ease,
          child: widget.child,
        ),
      );
}

/// Press feedback for any tappable Create piece.
Widget crPress({required VoidCallback onTap, required Widget child}) => _Press(onTap: onTap, child: child);

/// A slow light sliding across a picture that is being made (still under reduce motion).
class CrSheen extends StatefulWidget {
  const CrSheen({super.key});
  @override
  State<CrSheen> createState() => _CrSheenState();
}

class _CrSheenState extends State<CrSheen> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: const Duration(milliseconds: 1900));
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
  Widget build(BuildContext context) => IgnorePointer(
        child: ClipRect(
          child: AnimatedBuilder(
            animation: _a,
            builder: (_, __) => FractionalTranslation(
              translation: Offset(-1.2 + 2.4 * _a.value, 0),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: [
                    Colors.white.withOpacity(0),
                    Colors.white.withOpacity(.24),
                    Colors.white.withOpacity(0),
                  ]),
                ),
              ),
            ),
          ),
        ),
      );
}

/// A bar in the page's hue. [value] null = working with no known share: a short light runs along it.
class CrBar extends StatefulWidget {
  const CrBar({super.key, this.value, this.height = 6, this.onDark = false});
  final double? value;
  final double height;
  final bool onDark;
  @override
  State<CrBar> createState() => _CrBarState();
}

class _CrBarState extends State<CrBar> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500));
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (widget.value != null || HoolaMotion.reduced(context)) {
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
    final hue = CrHue.of(context);
    final track = widget.onDark ? Colors.white.withOpacity(.22) : crWash(c);
    return ClipRRect(
      borderRadius: BorderRadius.circular(widget.height / 2),
      child: SizedBox(
        height: widget.height,
        child: LayoutBuilder(builder: (context, box) {
          final w = box.maxWidth;
          return Stack(children: [
            Positioned.fill(child: ColoredBox(color: track)),
            if (widget.value != null)
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                width: w * widget.value!.clamp(0, 1),
                child: DecoratedBox(decoration: BoxDecoration(gradient: hue.gradient, borderRadius: BorderRadius.circular(widget.height / 2))),
              )
            else
              Positioned.fill(
                child: AnimatedBuilder(
                  animation: _a,
                  builder: (_, __) => Stack(children: [
                    Positioned(
                      left: -w * .4 + w * 1.4 * _a.value,
                      top: 0,
                      bottom: 0,
                      width: w * .4,
                      child: DecoratedBox(decoration: BoxDecoration(gradient: hue.gradient, borderRadius: BorderRadius.circular(widget.height / 2))),
                    ),
                  ]),
                ),
              ),
          ]);
        }),
      ),
    );
  }
}

/// A heading for a group: the words, and (optionally) a quiet link on the right.
class CrHead extends StatelessWidget {
  const CrHead(this.text, {super.key, this.link, this.onLink, this.note = ''});
  final String text, note;
  final String? link;
  final VoidCallback? onLink;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(children: [
        Expanded(flex: 3, child: Semantics(header: true, child: Text(text, style: HoolaType.heading(c).copyWith(fontSize: 19, fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontWeight: FontWeight.w500, letterSpacing: -.2)))),
        if (link != null)
          Flexible(
            child: TextButton(
              onPressed: onLink,
              style: TextButton.styleFrom(foregroundColor: c.ink2, minimumSize: const Size(48, 48)),
              child: Text(link!, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: HoolaType.small(c).copyWith(color: c.ink2, fontWeight: FontWeight.w500)),
            ),
          )
        else if (note.isNotEmpty)
          Flexible(
            child: Text(note, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right,
                style: HoolaType.small(c).copyWith(fontSize: 12.5, color: c.ink2)),
          ),
      ]),
    );
  }
}
