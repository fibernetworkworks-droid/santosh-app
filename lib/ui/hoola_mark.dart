// v0.716 NAYA ROOP: the owner's new Hoola mark as the phone's THINKING icon - the same one animation the console
// draws (server/app/static/console/mark.js), built from the four layers tool/make_mark.js renders
// (assets/images/mark_{outer,inner,needle,core}.png):
//   T3 the whole mark tilts in 3D, turns half way and rests;
//   T1 the outer and inner arcs orbit in opposite directions;
//   T2 the arcs breathe outward one after the other while the core floats in front and pulses.
// v0.874 EK RANG: the mark is ONE solid colour - the layers are white shapes tinted here with Hoola violet
// (#5B45E0 light, #9C88FF dark, the redesign's accent), or the colour a caller passes.
// With the system's "remove animations" setting on, it is the still mark.
import 'dart:math' as math;

import 'package:flutter/material.dart';

class HoolaMark extends StatefulWidget {
  const HoolaMark({super.key, this.size = 22, this.animate = true, this.color});
  final double size;
  final bool animate;
  final Color? color;
  @override
  State<HoolaMark> createState() => _HoolaMarkState();
}

class _HoolaMarkState extends State<HoolaMark> with SingleTickerProviderStateMixin {
  // one 6 s clock drives every part; each part reads its own phase from it so they never drift apart
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(seconds: 6));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final still = !widget.animate || MediaQuery.maybeDisableAnimationsOf(context) == true;
    if (still) {
      _c.stop();
    } else if (!_c.isAnimating) {
      _c.repeat();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  static double _ease(double t) => t < .5 ? 4 * t * t * t : 1 - math.pow(-2 * t + 2, 3) / 2;

  // T3: rest, half turn, rest, half turn (0-22% rest, 22-42% turn, 42-72% rest, 72-92% turn)
  static double _turn(double t) {
    if (t < .22) return 0;
    if (t < .42) return math.pi * _ease((t - .22) / .2);
    if (t < .72) return math.pi;
    if (t < .92) return math.pi + math.pi * _ease((t - .72) / .2);
    return 2 * math.pi;
  }

  Color _tint(BuildContext context) =>
      widget.color ??
      (Theme.of(context).brightness == Brightness.dark ? const Color(0xFF9C88FF) : const Color(0xFF5B45E0));

  Widget _layer(String name, Color tint, {double angle = 0, double scale = 1, double opacity = 1, double z = 0}) {
    final s = widget.size;
    return Transform(
      alignment: Alignment.center,                       // v0.874: the core sits at the exact centre
      transform: Matrix4.identity()
        ..translate(0.0, 0.0, z * s)
        ..rotateZ(angle)
        ..scale(scale, scale),
      child: Opacity(
        opacity: opacity.clamp(0.0, 1.0),
        child: Image.asset('assets/images/mark_$name.png',
            width: s, height: s, color: tint, colorBlendMode: BlendMode.srcIn, filterQuality: FilterQuality.medium),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.size;
    final tint = _tint(context);
    return SizedBox(
      width: s,
      height: s,
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          final t = _c.value;
          final w = 2 * math.pi * t;
          // T2 breathing (1.8 s) and the core pulse (1.6 s), expressed on the 6 s clock
          double breathe(double lag) => .5 - .5 * math.cos(2 * math.pi * ((t * 6 - lag) / 1.8));
          final bi = breathe(0), bo = breathe(.25);
          final core = .9 + .16 * (.5 - .5 * math.cos(2 * math.pi * (t * 6 / 1.6)));
          // T1 orbits: outer 3 s, inner 2.2 s the other way
          final orbO = 2 * math.pi * _ease((t * 6 / 3) % 1);
          final orbI = -2 * math.pi * _ease((t * 6 / 2.2) % 1);
          final turn = _turn(t);
          final tilt = Matrix4.identity()
            ..setEntry(3, 2, 0.0025)
            ..rotateX((16 - 28 * (.5 - .5 * math.cos(w))) * math.pi / 180)
            ..rotateY((-18 + 38 * (.5 - .5 * math.cos(w))) * math.pi / 180);
          return Transform(
            alignment: Alignment.center,
            transform: tilt,
            child: Stack(children: [
              _layer('outer', tint, angle: turn + orbO, scale: .94 + .12 * bo, opacity: .6 + .4 * bo, z: -.08),
              _layer('inner', tint, angle: turn + orbI, scale: .94 + .12 * bi, opacity: .6 + .4 * bi, z: -.02),
              _layer('needle', tint, angle: turn, z: .05),
              _layer('core', tint, scale: core, z: .14),
            ]),
          );
        },
      ),
    );
  }
}
