// v0.898 TOOLS TAB (owner: "REMOVE CONNECTOR INSTEAD PUT TOOLS IN TOOLS (SHOW ALL HOOLA FEATURES INTERACTIVE, VOCAL,
// FLOW, WEB DEVELOPMENT, APP DEVELOPMENT, CREATE, DESIGN, PROMPTING SAME AS CONSOLE PANEL SHOWN"): every Hoola studio
// as a tile; a tap opens that studio's own web console page inside the app, already signed in (hoolaOpenConsole), so
// the phone shows exactly what the console shows. Below them: Hoola Code, Game Dev, and Connectors (the old Connect
// tab, in the app's own design).
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../state.dart';
import '../bazar_screen.dart';
import '../hoola_theme.dart';
import 'hoola_console_page.dart';
import 'hoola_settings.dart' show hoolaOpenNew, hoolaOpenOld;
import 'hoola_connect.dart';
import 'hoola_tabs.dart';
import 'hoola_tool_icons.dart';

/// One studio: its name, what it does in a line, its icon, and the console page it opens.
typedef HoolaTool = ({String title, String sub, ToolGlyph glyph, String path});

const List<HoolaTool> hoolaStudios = [
  (title: 'Create', sub: 'Pictures, videos, songs and voice-overs', glyph: ToolGlyph.create, path: '/console/?v=creative'),
  (title: 'Hoola Interactive', sub: 'Talking videos from a script', glyph: ToolGlyph.interactive, path: '/console/?v=interactive'),
  (title: 'Hoola Vocal', sub: 'Voices, dubbing and sound', glyph: ToolGlyph.vocal, path: '/console/?v=vocal'),
  (title: 'Hoola Flow', sub: 'Speak, and it is written for you', glyph: ToolGlyph.flow, path: '/console/flow'),
  (title: 'Web Development', sub: 'Websites and web apps, built and put live', glyph: ToolGlyph.web, path: '/console/web'),
  (title: 'App Development', sub: 'Android and iPhone apps for your business', glyph: ToolGlyph.app, path: '/console/apps'),
  (title: 'Hoola Design', sub: 'Screens, posters and layouts', glyph: ToolGlyph.design, path: '/console/design'),
  (title: 'Prompting', sub: 'Turn a rough idea into a clear brief', glyph: ToolGlyph.prompting, path: '/console/prompting'),
];

const List<HoolaTool> hoolaMoreTools = [
  (title: 'Hoola Code', sub: 'Work on your code on GitHub', glyph: ToolGlyph.code, path: '/console/code'),
  (title: 'Game Dev', sub: 'Make, test and ship games', glyph: ToolGlyph.game, path: '/console/games'),
];

/// v0.907 TOOLS PRO (option B of claude.ai/artifact/KMa7vVmS1EpWNRBqCvB8SX): every studio a soft white card, its
/// own drawing centred on a black circle (the same black as the call button and the open tab), name and line centred
/// below. Opening: the cards rise in one after another and each drawing draws itself; then every drawing keeps one
/// small motion of its own. A press sinks the card. Reduce motion = no movement at all.
class HoolaTools extends StatefulWidget {
  const HoolaTools({super.key, required this.app});
  final Santosh app;

  /// The opening's length: the last card starts at 9 x 55 ms, its drawing ends 120 + 900 ms later.
  static const enter = Duration(milliseconds: 1600);

  @override
  State<HoolaTools> createState() => _HoolaToolsState();
}

class _HoolaToolsState extends State<HoolaTools> with TickerProviderStateMixin {
  late final AnimationController _enter = AnimationController(vsync: this, duration: HoolaTools.enter);
  // the drawings' quiet motion: a clock in seconds (an hour long, then it starts over)
  late final AnimationController _live = AnimationController(vsync: this, duration: const Duration(hours: 1));
  late final Animation<double> _secs = _live.drive(Tween(begin: 0.0, end: 3600.0));
  bool? _still;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final still = HoolaMotion.reduced(context);
    if (still == _still) return;
    _still = still;
    if (still) {
      _enter.value = 1;
      _live.stop();
    } else {
      if (_enter.value == 0) _enter.forward();
      _live.repeat();
    }
  }

  @override
  void dispose() {
    _enter.dispose();
    _live.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final c = HoolaColors.of(context);
    final clock = _still == true ? null : _secs;
    // with big text (her phone's text size) the tiles become rows, so nothing is ever cut
    final scaler = MediaQuery.textScalerOf(context);
    final big = scaler.scale(10) > 13;
    // a card holds the badge, two lines of name and two lines of its line, whatever the text size
    final extent = 32 + 60 + 16 + 4 + scaler.scale(16) * 1.3 * 2 + scaler.scale(13) * 1.4 * 2 + 2;
    Widget row(HoolaTool t, int i, VoidCallback onTap) => HoolaRow(
          title: t.title,
          sub: t.sub,
          tile: ToolBadge(glyph: t.glyph, size: 44, clock: clock, phase: i * .37),
          trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
          onTap: onTap,
        );
    return LayoutBuilder(builder: (context, box) {
      final cols = box.maxWidth >= 600 ? 3 : 2;
      return ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        const HoolaTabHeader(title: 'Tools', sub: 'Every Hoola studio, the same as on the web console'),
        if (big)
          HoolaGroup(children: [
            for (var i = 0; i < hoolaStudios.length; i++)
              row(hoolaStudios[i], i, () => hoolaOpenConsole(context, app, hoolaStudios[i].path, hoolaStudios[i].title)),
          ])
        else
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
            child: GridView(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: cols,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                mainAxisExtent: extent,
              ),
              children: [
                for (var i = 0; i < hoolaStudios.length; i++)
                  _Tile(tool: hoolaStudios[i], app: app, index: i, enter: _enter, clock: clock),
              ],
            ),
          ),
        const HoolaSection('More'),
        HoolaGroup(children: [
          for (var i = 0; i < hoolaMoreTools.length; i++)
            row(hoolaMoreTools[i], 8 + i, () => hoolaOpenConsole(context, app, hoolaMoreTools[i].path, hoolaMoreTools[i].title)),
          row((title: 'Connectors', sub: 'Your apps and accounts linked to ${app.aName}', glyph: ToolGlyph.connectors, path: ''), 10,
              () => hoolaOpenNew(context, app, HoolaConnectorsPage(app: app))),
        ]),
      ]);
    });
  }
}

/// A studio's drawing centred on the black circle (near-white in dark mode).
class ToolBadge extends StatelessWidget {
  const ToolBadge({super.key, required this.glyph, this.size = 60, this.clock, this.draw = 1, this.phase = 0});
  final ToolGlyph glyph;
  final double size;
  final ValueListenable<double>? clock;
  final double draw;
  final double phase;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
      child: ToolIcon(glyph: glyph, color: c.onPill, size: size * .53, clock: clock, draw: draw, phase: phase),
    );
  }
}

class _Tile extends StatefulWidget {
  const _Tile({required this.tool, required this.app, required this.index, required this.enter, this.clock});
  final HoolaTool tool;
  final Santosh app;
  final int index;
  final Animation<double> enter;
  final ValueListenable<double>? clock;
  @override
  State<_Tile> createState() => _TileState();
}

class _TileState extends State<_Tile> {
  bool _down = false;

  /// 0..1 of one part of the opening: starts [startMs] into it, lasts [ms].
  double _at(int startMs, int ms) {
    final total = HoolaTools.enter.inMilliseconds;
    return ((widget.enter.value * total - startMs) / ms).clamp(0.0, 1.0);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final tool = widget.tool;
    final delay = widget.index * 55;
    return AnimatedBuilder(
      animation: widget.enter,
      builder: (context, child) {
        final rise = const Cubic(.2, .8, .2, 1).transform(_at(delay, 560));
        final pop = _at(delay + 120, 620);
        final draw = Curves.easeInOutCubic.transform(_at(delay + 120, 900));
        return Opacity(
          opacity: rise,
          child: Transform.translate(
            offset: Offset(0, 18 * (1 - rise)),
            child: Transform.scale(
              scale: .965 + .035 * rise,
              child: AnimatedScale(
                scale: _down ? .965 : 1,
                duration: const Duration(milliseconds: 160),
                curve: HoolaMotion.ease,
                child: Semantics(
                  button: true,
                  label: '${tool.title}. ${tool.sub}',
                  excludeSemantics: true,
                  child: DecoratedBox(
                    decoration: BoxDecoration(borderRadius: HoolaRadius.r(20), boxShadow: HoolaShadow.card(c)),
                    child: Material(
                      color: c.surface,
                      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(20), side: BorderSide(color: c.line)),
                      clipBehavior: Clip.antiAlias,
                      child: InkWell(
                        onHighlightChanged: (v) => setState(() => _down = v),
                        onTap: () => hoolaOpenConsole(context, widget.app, tool.path, tool.title),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                            Opacity(
                              opacity: pop,
                              child: Transform.rotate(
                                angle: -8 * (1 - pop) * math.pi / 180,
                                child: Transform.scale(
                                  scale: (.7 + .3 * Curves.easeOutBack.transform(pop)) * (_down ? .93 : 1),
                                  child: ToolBadge(glyph: tool.glyph, clock: widget.clock, draw: draw, phase: widget.index * .37),
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text(tool.title, maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                                style: HoolaType.title(c).copyWith(height: 1.3)),
                            const SizedBox(height: 4),
                            Text(tool.sub, maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                                style: HoolaType.small(c).copyWith(color: c.ink2)),
                          ]),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

/// The old Connect tab as its own page (a back arrow on top), opened from Tools > Connectors and the + sheet.
class HoolaConnectorsPage extends StatelessWidget {
  const HoolaConnectorsPage({super.key, required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) => HoolaPageFrame(
        child: HoolaConnect(app: app, onMore: () => hoolaOpenOld(context, BazarScreen(app: app))),
      );
}

/// A tab's body as a page of its own: the back arrow above it (Connectors, Work, Made from the drawer / Tools).
class HoolaPageFrame extends StatelessWidget {
  const HoolaPageFrame({super.key, required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: const EdgeInsets.only(left: 4, top: 4),
              child: IconButton(
                tooltip: 'Back',
                onPressed: () => Navigator.of(context).maybePop(),
                icon: Icon(Icons.arrow_back_rounded, color: c.ink),
              ),
            ),
          ),
          Expanded(child: child),
        ]),
      ),
    );
  }
}
