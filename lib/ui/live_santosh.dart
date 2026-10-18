import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'glass.dart';

const _art = {
  'happy': 'assets/images/santosh_happy.png',
  'idle': 'assets/images/santosh_happy.png',
  'working': 'assets/images/santosh_working.png',
  'thinking': 'assets/images/santosh_thinking.png',
};

/// Santosh's rendered art, alive: floats, breathes, sways, and swaps pose by mood.
class LiveSantosh extends StatefulWidget {
  const LiveSantosh({super.key, this.mood = 'happy', this.size = 190, this.talking = false});
  final String mood;
  final double size;
  final bool talking;
  @override
  State<LiveSantosh> createState() => _LiveSantoshState();
}

class _LiveSantoshState extends State<LiveSantosh> with SingleTickerProviderStateMixin {
  late final AnimationController _t = AnimationController(vsync: this, duration: const Duration(seconds: 6))..repeat();

  @override
  void dispose() {
    _t.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final img = _art[widget.mood] ?? _art['happy']!;
    return SizedBox(
      width: widget.size,
      height: widget.size * 1.08,
      child: AnimatedBuilder(
        animation: _t,
        builder: (context, child) {
          final a = _t.value * 2 * math.pi;
          final float = math.sin(a) * widget.size * .025;
          final breathe = 1 + math.sin(a * 2) * .012 + (widget.talking ? (math.sin(a * 22).abs() * .02) : 0);
          final sway = math.sin(a * .5) * .025 + (widget.mood == 'thinking' ? .04 : 0);
          return Stack(alignment: Alignment.bottomCenter, children: [
            // soft shadow that shrinks as he rises
            Positioned(
              bottom: widget.size * .02,
              child: Container(
                width: widget.size * (.5 - float / widget.size),
                height: widget.size * .06,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(widget.size),
                  boxShadow: [BoxShadow(color: const Color(0x334C1D95), blurRadius: widget.size * .08, spreadRadius: 1)],
                ),
              ),
            ),
            Transform.translate(
              offset: Offset(0, -float - widget.size * .04),
              child: Transform.rotate(angle: sway, child: Transform.scale(scale: breathe, child: child)),
            ),
          ]);
        },
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 450),
          switchInCurve: Curves.easeOutBack,
          transitionBuilder: (c, anim) => FadeTransition(opacity: anim, child: ScaleTransition(scale: Tween(begin: .92, end: 1.0).animate(anim), child: c)),
          child: Image.asset(img, key: ValueKey(img), height: widget.size, fit: BoxFit.contain),
        ),
      ),
    );
  }
}

/// Header avatar with a breathing glow ring while Santosh is busy.
class LiveAvatar extends StatefulWidget {
  const LiveAvatar({super.key, required this.online, required this.busy, this.size = 48});
  final bool online;
  final bool busy;
  final double size;
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
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _t,
        builder: (context, child) {
          final v = Curves.easeOut.transform(_t.value);
          return Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
            if (widget.busy)
              Container(
                width: widget.size + 14 * v,
                height: widget.size + 14 * v,
                decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: C.accent.withOpacity(.55 * (1 - v)), width: 3)),
              ),
            Transform.scale(scale: 1 + math.sin(_t.value * 2 * math.pi) * (widget.busy ? .03 : .012), child: child),
          ]);
        },
        child: Avatar(size: widget.size, online: widget.online),
      );
}
