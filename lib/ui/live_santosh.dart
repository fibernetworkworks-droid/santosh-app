import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../emotion.dart';
import 'avatar_look.dart';
import 'glass.dart';

Mood moodFromName(String m) => switch (m) {
      'working' || 'work' => Mood.work,
      'thinking' || 'think' => Mood.think,
      'listening' => Mood.listening,
      'excited' => Mood.excited,
      'care' => Mood.care,
      'wow' => Mood.wow,
      'talking' => Mood.talking,
      'idle' => Mood.idle,
      _ => Mood.happy,
    };

/// One frame of body language.
class _Pose {
  const _Pose(this.dy, this.rot, this.sx, this.sy, this.dx);
  final double dy, rot, sx, sy, dx; // dy/dx in fraction of size, rot in radians
  static _Pose lerp(_Pose a, _Pose b, double t) => _Pose(
      a.dy + (b.dy - a.dy) * t, a.rot + (b.rot - a.rot) * t, a.sx + (b.sx - a.sx) * t, a.sy + (b.sy - a.sy) * t, a.dx + (b.dx - a.dx) * t);
}

/// Santosh, alive. He moves differently for each feeling, reacts to your voice level while listening,
/// bobs with his own voice while talking, glows in the colour of his mood, and shows a thought bubble.
class LiveSantosh extends StatefulWidget {
  const LiveSantosh({super.key, this.mood = 'happy', this.feeling, this.size = 190, this.talking = false, this.level = 0,
      this.thought = false, this.aura = true});
  final String mood;        // legacy names: happy / working / thinking
  final Mood? feeling;      // preferred
  final double size;
  final bool talking;       // his voice is playing
  final double level;       // 0..1 live audio level (yours while listening, his while talking)
  final bool thought;       // show the thought bubble
  final bool aura;
  @override
  State<LiveSantosh> createState() => _LiveSantoshState();
}

class _LiveSantoshState extends State<LiveSantosh> with TickerProviderStateMixin {
  late final AnimationController _t = AnimationController(vsync: this, duration: const Duration(seconds: 12))..repeat();
  late final AnimationController _blend = AnimationController(vsync: this, duration: const Duration(milliseconds: 520), value: 1);
  late final AnimationController _pop = AnimationController(vsync: this, duration: const Duration(milliseconds: 650));
  Mood _from = Mood.idle, _to = Mood.idle;
  double _lvl = 0;

  Mood get _mood => widget.feeling ?? (widget.talking ? Mood.talking : moodFromName(widget.mood));

  @override
  void initState() {
    super.initState();
    _to = _from = _mood;
  }

  @override
  void didUpdateWidget(covariant LiveSantosh old) {
    super.didUpdateWidget(old);
    final m = _mood;
    if (m != _to) {
      _from = _to;
      _to = m;
      _blend.forward(from: 0);
      if (m == Mood.wow || m == Mood.excited || m == Mood.happy) _pop.forward(from: 0); // a little reaction "hop"
    }
  }

  @override
  void dispose() {
    _t.dispose();
    _blend.dispose();
    _pop.dispose();
    super.dispose();
  }

  /// Body language per mood at time [s] seconds.
  _Pose _poseFor(Mood m, double s, double lvl) {
    double sn(double f, [double ph = 0]) => math.sin(s * f * 2 * math.pi + ph);
    switch (m) {
      case Mood.idle:
        return _Pose(-.02 + sn(.2) * .018, sn(.1) * .02, 1 + sn(.4) * .008, 1 - sn(.4) * .006, 0);
      case Mood.listening: // leans toward you, nods softly with your voice
        return _Pose(-.015 - lvl * .03, -.07 + sn(.35) * .015 - lvl * .03, 1.03 + lvl * .02, 1.03 + lvl * .02, -.02);
      case Mood.happy: // light springy bounce + sway
        final b = sn(.9).abs();
        return _Pose(-b * .05, sn(.45) * .035, 1 + b * .012, 1 - b * .008, 0);
      case Mood.excited: // jumps with squash and stretch
        final j = math.pow(sn(1.4).abs(), 1.6).toDouble();
        return _Pose(-j * .11, sn(.7) * .05, 1 - j * .03 + (1 - j) * .02, 1 + j * .04 - (1 - j) * .02, 0);
      case Mood.care: // slower, softer, leans in gently, a bit lower
        return _Pose(.02 + sn(.15) * .01, .05 + sn(.12) * .02, .98, .98, .01);
      case Mood.think: // slow head-tilt sway
        return _Pose(-.015 + sn(.25) * .01, sn(.22) * .06, 1, 1, 0);
      case Mood.wow: // pop, then a held stretch
        return _Pose(-.035 + sn(.6) * .01, sn(.3) * .02, .99, 1.04, 0);
      case Mood.work: // busy little tapping motion
        return _Pose(-.01 - sn(2.2).abs() * .015, sn(1.1) * .01, 1, 1, 0);
      case Mood.talking: // bobs with his own voice
        return _Pose(-.015 - lvl * .045 + sn(.3) * .008, sn(.5) * .025 + lvl * .02, 1 + lvl * .02, 1 + lvl * .025, 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = widget.size;
    return SizedBox(
      width: size * .95,
      height: size * 1.12,
      child: AnimatedBuilder(
        animation: Listenable.merge([_t, _blend, _pop]),
        builder: (context, _) {
          // smooth the audio level so he never jitters
          _lvl += (widget.level.clamp(0.0, 1.0) - _lvl) * .25;
          final s = _t.value * 12;
          final k = Curves.easeOutCubic.transform(_blend.value);
          final p = _Pose.lerp(_poseFor(_from, s, _lvl), _poseFor(_to, s, _lvl), k);
          final hop = math.sin(_pop.value * math.pi) * (1 - _pop.value * .3);
          final st = moodStyles[_to]!;
          final aura = Color.lerp(moodStyles[_from]!.aura, st.aura, k)!;
          final glowPulse = .75 + math.sin(s * .6 * 2 * math.pi) * .12 + _lvl * .25;
          return Stack(clipBehavior: Clip.none, alignment: Alignment.bottomCenter, children: [
            if (widget.aura)
              Positioned(
                top: size * .08,
                child: IgnorePointer(
                  child: Container(
                    width: size * .8,
                    height: size * .8,
                    decoration: BoxDecoration(shape: BoxShape.circle, boxShadow: [
                      BoxShadow(color: aura.withOpacity(.42 * glowPulse), blurRadius: size * .35, spreadRadius: size * .02),
                    ]),
                  ),
                ),
              ),
            Transform.translate(
              offset: Offset(p.dx * size, (p.dy - hop * .06) * size),
              child: Transform.rotate(
                angle: p.rot,
                alignment: Alignment.bottomCenter,
                child: Transform(
                  alignment: Alignment.bottomCenter,
                  transform: Matrix4.diagonal3Values(p.sx + hop * .02, p.sy + hop * .03, 1),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 380),
                    switchInCurve: Curves.easeOutBack,
                    transitionBuilder: (c, a) => FadeTransition(opacity: a, child: ScaleTransition(scale: Tween(begin: .94, end: 1.0).animate(a), child: c)),
                    child: ValueListenableBuilder<String>(
                      key: ValueKey(st.pose),
                      valueListenable: currentLook,
                      builder: (_, look, __) {
                        final src = isLook(look) ? lookFull(look) : st.pose;      // female look: one figure, same body language
                        return Image.asset(src, key: ValueKey(src), height: size, fit: BoxFit.contain, filterQuality: FilterQuality.medium);
                      },
                    ),
                  ),
                ),
              ),
            ),
            if (widget.thought && st.thought.isNotEmpty)
              Positioned(
                top: size * .02,
                right: -size * .22,
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 420),
                  transitionBuilder: (c, a) => ScaleTransition(scale: CurvedAnimation(parent: a, curve: Curves.elasticOut), alignment: Alignment.bottomLeft, child: FadeTransition(opacity: a, child: c)),
                  child: Glass(flat: true,
                    key: ValueKey(st.thought),
                    radius: 16,
                    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                    child: Text(st.thought, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
                  ),
                ),
              ),
          ]);
        },
      ),
    );
  }
}

/// Header avatar with a breathing glow ring while Santosh is busy, tinted by mood.
class LiveAvatar extends StatefulWidget {
  const LiveAvatar({super.key, required this.online, required this.busy, this.size = 44, this.feeling});
  final bool online;
  final bool busy;
  final double size;
  final Mood? feeling;
  @override
  State<LiveAvatar> createState() => _LiveAvatarState();
}

class _LiveAvatarState extends State<LiveAvatar> with SingleTickerProviderStateMixin {
  late final AnimationController _t = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))..repeat();

  @override
  void dispose() {
    _t.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final glow = moodStyles[widget.feeling ?? Mood.idle]!.aura;
    return AnimatedBuilder(
      animation: _t,
      builder: (context, child) {
        final v = Curves.easeOut.transform(_t.value);
        return Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
          if (widget.busy)
            Container(
              width: widget.size + 16 * v,
              height: widget.size + 16 * v,
              decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: glow.withOpacity(.6 * (1 - v)), width: 3)),
            ),
          Transform.scale(scale: 1 + math.sin(_t.value * 2 * math.pi) * (widget.busy ? .03 : .012), child: child),
        ]);
      },
      child: Avatar(size: widget.size, online: widget.online, glow: glow),
    );
  }
}
