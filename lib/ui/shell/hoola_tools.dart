// v0.898 TOOLS TAB (owner: "REMOVE CONNECTOR INSTEAD PUT TOOLS IN TOOLS (SHOW ALL HOOLA FEATURES INTERACTIVE, VOCAL,
// FLOW, WEB DEVELOPMENT, APP DEVELOPMENT, CREATE, DESIGN, PROMPTING SAME AS CONSOLE PANEL SHOWN"): every Hoola studio
// as a tile; a tap opens that studio's own web console page inside the app, already signed in (hoolaOpenConsole), so
// the phone shows exactly what the console shows. Below them: Hoola Code, Game Dev, and Connectors (the old Connect
// tab, in the app's own design).
import 'package:flutter/material.dart';

import '../../state.dart';
import '../bazar_screen.dart';
import '../hoola_theme.dart';
import 'hoola_console_page.dart';
import 'hoola_settings.dart' show hoolaOpenNew, hoolaOpenOld;
import 'hoola_connect.dart';
import 'hoola_tabs.dart';

/// One studio: its name, what it does in a line, its icon, and the console page it opens.
typedef HoolaTool = ({String title, String sub, IconData icon, String path});

const List<HoolaTool> hoolaStudios = [
  (title: 'Create', sub: 'Pictures, videos, songs and voice-overs', icon: Icons.auto_awesome_rounded, path: '/console/?v=creative'),
  (title: 'Hoola Interactive', sub: 'Talking videos from a script', icon: Icons.movie_filter_outlined, path: '/console/?v=interactive'),
  (title: 'Hoola Vocal', sub: 'Voices, dubbing and sound', icon: Icons.graphic_eq_rounded, path: '/console/?v=vocal'),
  (title: 'Hoola Flow', sub: 'Speak, and it is written for you', icon: Icons.keyboard_voice_outlined, path: '/console/flow'),
  (title: 'Web Development', sub: 'Websites and web apps, built and put live', icon: Icons.language_rounded, path: '/console/web'),
  (title: 'App Development', sub: 'Android and iPhone apps for your business', icon: Icons.phone_iphone_rounded, path: '/console/apps'),
  (title: 'Hoola Design', sub: 'Screens, posters and layouts', icon: Icons.design_services_outlined, path: '/console/design'),
  (title: 'Prompting', sub: 'Turn a rough idea into a clear brief', icon: Icons.edit_note_rounded, path: '/console/prompting'),
];

const List<HoolaTool> hoolaMoreTools = [
  (title: 'Hoola Code', sub: 'Work on your code on GitHub', icon: Icons.code_rounded, path: '/console/code'),
  (title: 'Game Dev', sub: 'Make, test and ship games', icon: Icons.sports_esports_outlined, path: '/console/games'),
];

class HoolaTools extends StatelessWidget {
  const HoolaTools({super.key, required this.app});
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    // with big text (her phone's text size) the tiles become rows, so nothing is ever cut
    final big = MediaQuery.textScalerOf(context).scale(10) > 13;
    return LayoutBuilder(builder: (context, box) {
      final cols = box.maxWidth >= 600 ? 3 : 2;
      return ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        const HoolaTabHeader(title: 'Tools', sub: 'Every Hoola studio, the same as on the web console'),
        if (big)
          HoolaGroup(children: [
            for (final t in hoolaStudios)
              HoolaRow(
                title: t.title,
                sub: t.sub,
                icon: t.icon,
                tint: c.accent,
                trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
                onTap: () => hoolaOpenConsole(context, app, t.path, t.title),
              ),
          ])
        else
        Padding(
          padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
          child: GridView.count(
            crossAxisCount: cols,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.08,
            children: [for (final t in hoolaStudios) _Tile(tool: t, app: app)],
          ),
        ),
        const HoolaSection('More'),
        HoolaGroup(children: [
          for (final t in hoolaMoreTools)
            HoolaRow(
              title: t.title,
              sub: t.sub,
              icon: t.icon,
              trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
              onTap: () => hoolaOpenConsole(context, app, t.path, t.title),
            ),
          HoolaRow(
            title: 'Connectors',
            sub: 'Your apps and accounts linked to ${app.aName}',
            icon: Icons.power_outlined,
            trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
            onTap: () => hoolaOpenNew(context, app, HoolaConnectorsPage(app: app)),
          ),
        ]),
      ]);
    });
  }
}

class _Tile extends StatelessWidget {
  const _Tile({required this.tool, required this.app});
  final HoolaTool tool;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: '${tool.title}. ${tool.sub}',
      excludeSemantics: true,
      child: Material(
        color: c.surface,
        shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(20), side: BorderSide(color: c.line)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => hoolaOpenConsole(context, app, tool.path, tool.title),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(color: c.accentSoft, borderRadius: HoolaRadius.r(14)),
                child: Icon(tool.icon, color: c.accent, size: 24),
              ),
              const Spacer(),
              Text(tool.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
              const SizedBox(height: 2),
              Text(tool.sub, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
            ]),
          ),
        ),
      ),
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
