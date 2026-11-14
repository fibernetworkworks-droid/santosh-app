// v0.913 CREATE IN COLOUR (design canvas claude.ai/artifact/HXF8gGUqohSnZBnohRkbtu, "GO BUILD"): the colour and glass
// every Create screen stands on. A page has a hue (pictures, clips, films, songs, voices), a slow moving colour light
// behind it, and glass on top - see-through colour over that light, never a blur (the design rules: blur costs frames
// on a budget phone). The painted scenes stand in for a picture where there is none yet (a camera move, a style, an
// idea to start from); the camera moves really move, and everything stands still when the phone asks for less motion.
import 'dart:math' as math;
import 'dart:ui' show PointMode;

import 'package:flutter/material.dart';
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
    canvas.drawRRect(rr.shift(shadow.offset).inflate(shadow.spreadRadius), shadow.toPaint());

    canvas.save();
    canvas.clipRRect(rr);
    if (d.base != null) canvas.drawRect(rect, Paint()..color = d.base!);
    // the pane: lit at the top, clearer below
    final fill = dark
        ? [Colors.white.withOpacity(strong ? .17 : .13), Colors.white.withOpacity(strong ? .085 : .06), Colors.white.withOpacity(strong ? .06 : .035)]
        : [Colors.white.withOpacity(strong ? .95 : .88), Colors.white.withOpacity(strong ? .8 : .68), Colors.white.withOpacity(strong ? .72 : .58)];
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

// ------------------------------------------------------------------------------------------------ pieces
/// A colour circle with a drawing on it (a studio, a voice). [child] sits on the hue in its dark ink.
class CrOrb extends StatelessWidget {
  const CrOrb({super.key, required this.hue, required this.child, this.size = 52});
  final CrHue hue;
  final Widget child;
  final double size;
  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: hue.pair),
          boxShadow: [BoxShadow(color: hue.a.withOpacity(.32), blurRadius: 16, spreadRadius: -6, offset: const Offset(0, 6))],
        ),
        alignment: Alignment.center,
        child: child,
      );
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
