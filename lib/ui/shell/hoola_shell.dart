// v0.861 R2 THE SHELL (docs/HOOLA_APP_REDESIGN_PLAN.md R2): the Claude-style frame of the app in Hoola's brand.
//
//   4 tabs in a floating pill bar: Hoola (home + chat) · AI Employees · Tools · Computer (v0.898, owner: "BOTTOM WILL
//   HAVE 4 SECTION --- HOOLA, AI EMPLOYEE, TOOLS, COMPUTER"; Work and Made moved to the drawer, Connectors into Tools)
//   a drawer (her recent chats + calls, All chats, what Santosh remembers, her avatar -> Settings, New chat)
//   the pill composer (+ · "Type or hold to talk" · mic · the black voice button that opens Talk)
//
// Behind Santosh.newLook (Main > "Try the new design") until R7-R8 rebuild the rest: since R6 every tab is in the new
// design (Hoola = R3 chat, Work / Connect / Made = hoola_tabs.dart); old pages (Today, AI team, the full plugin list,
// Settings) open in their own Night Glass frame until their phase. Every colour / size / movement comes from hoola_theme.dart.
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../../state.dart';
import '../calls_sheet.dart';
import '../chat/hoola_attach.dart';
import '../chat/hoola_chat.dart';
import '../chat_attach.dart' show TrayFile, openAttachment;
import '../glass.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import '../talk/hoola_talk.dart';
import 'hoola_settings.dart';
import 'hoola_computer.dart';
import 'hoola_employees.dart';
import 'hoola_nav_icons.dart';
import 'hoola_tabs.dart';
import 'hoola_tools.dart';
import '../memory_page_screen.dart';
import '../today_screen.dart';
import '../voice_screen.dart';

/// v0.895 the composer's Add sheet asks the shell for a tab (v0.898: Your computers = 3).
final hoolaTabRequest = ValueNotifier<int?>(null);

/// The Hoola mark (the owner's logo) as drawn in the app.

class HoolaShell extends StatefulWidget {
  const HoolaShell({super.key, required this.app, required this.onReset});
  final Santosh app;
  final VoidCallback onReset;
  @override
  State<HoolaShell> createState() => _HoolaShellState();
}

class _HoolaShellState extends State<HoolaShell> {
  final _scaffold = GlobalKey<ScaffoldState>();
  int _tab = 0;
  bool _talkOpen = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    hoolaTabRequest.addListener(_tabAsked);
  }

  @override
  void dispose() {
    hoolaTabRequest.removeListener(_tabAsked);
    super.dispose();
  }

  void _tabAsked() {
    final i = hoolaTabRequest.value;
    if (i == null || !mounted) return;
    hoolaTabRequest.value = null;
    _go(i);
  }

  /// v0.888 the tab bar steps aside while Hoola is working in the open chat (the Hoola tab with a chat on it).
  bool get _navHidden => _tab == 0 && app.typing && app.feed.any((f) => f.kind == 'message');

  void _go(int i) {
    if (i == _tab) return;
    HapticFeedback.selectionClick();
    setState(() => _tab = i);
  }

  Future<void> _openTalk() async {
    if (_talkOpen) return;
    _talkOpen = true;
    HapticFeedback.mediumImpact();
    await Navigator.of(context).push(PageRouteBuilder<void>(
      transitionDuration: HoolaMotion.of(context, HoolaMotion.sheet),
      reverseTransitionDuration: HoolaMotion.of(context, HoolaMotion.page),
      // v0.865 R5 the live call in the new design; the older turn-by-turn voice screen stays until it is rebuilt
      pageBuilder: (_, __, ___) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => app.realtimeVoice
            ? HoolaTheme(appearance: app.appearance, child: HoolaTalk(app: app))
            : _OldLook(child: VoiceScreen(app: app)),
      ),
      transitionsBuilder: (context, a, _, child) => HoolaMotion.reduced(context)
          ? FadeTransition(opacity: a, child: child)
          : SlideTransition(
              position: Tween(begin: const Offset(0, 1), end: Offset.zero)
                  .animate(CurvedAnimation(parent: a, curve: HoolaMotion.ease, reverseCurve: HoolaMotion.exit)),
              child: child),
    ));
    _talkOpen = false;
  }

  void _openOld(Widget screen) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => _OldLook(child: screen)));

  Future<void> _newChat() async {
    Navigator.of(context).maybePop();   // the drawer
    _go(0);
    await app.newChat();
  }

  @override
  Widget build(BuildContext context) => HoolaTheme(
        appearance: app.appearance,
        child: Builder(builder: (context) {
          final c = HoolaColors.of(context);
          final keyboard = MediaQuery.viewInsetsOf(context).bottom > 0;
          final pages = <Widget>[
            _HoolaTab(app: app, onTalk: _openTalk, onMenu: () => _scaffold.currentState?.openDrawer()),
            // v0.898 the four tabs: Hoola, AI Employees, Tools, Computer (Work + Made live in the drawer now)
            HoolaEmployees(app: app),
            HoolaTools(app: app),
            HoolaComputer(app: app),   // v0.890 Hoola Computer: Hoola PC + Your PC, their own chats
          ];
          return Scaffold(
            key: _scaffold,
            backgroundColor: c.bg,
            extendBody: true,
            drawer: HoolaDrawer(
              app: app,
              onNewChat: _newChat,
              onOpenChat: (id) async {
                Navigator.of(context).maybePop();
                _go(0);
                await app.openChat(id);
              },
              onCalls: () {
                Navigator.of(context).maybePop();
                showCallsSheet(context, app);
              },
              onMemory: () {
                Navigator.of(context).maybePop();
                _openOld(MemoryPageScreen(app: app));
              },
              // v0.898 Work and Made left the tab bar: here, one tap away
              onWork: () {
                Navigator.of(context).maybePop();
                hoolaOpenNew(context, app, Builder(builder: (ctx) => HoolaPageFrame(
                      child: HoolaWork(
                        app: app,
                        onOpenChat: (id) async {
                          Navigator.of(ctx).maybePop();
                          _go(0);
                          await app.openChat(id);
                        },
                        onTeam: () => hoolaOpenNew(ctx, app, HoolaTeam(app: app)),
                        onToday: () => _openOld(TodayScreen(app: app, onTab: (_) {
                          Navigator.of(ctx).maybePop();   // Today
                          Navigator.of(ctx).maybePop();   // Work
                          _go(0);
                        })),
                      ),
                    )));
              },
              onMade: () {
                Navigator.of(context).maybePop();
                hoolaOpenNew(context, app, HoolaPageFrame(child: HoolaMade(app: app)));
              },
              onSettings: () {
                Navigator.of(context).maybePop();
                // v0.867 R7 Settings in the new design (every old Main row has a home there or in Your AI team)
                hoolaOpenNew(context, app, HoolaSettings(app: app, onReset: widget.onReset));
              },
            ),
            // v0.888 while Hoola works in the chat the tab bar slides away and the chat takes the room (her ask:
            // "when chat work in progress hide the bottom nav perfectly"); it comes back when the turn ends.
            body: SafeArea(
              bottom: false,
              child: ListenableBuilder(
                listenable: Listenable.merge([app, app.voiceCall]),
                builder: (context, child) {
                  final hide = _navHidden;
                  final pill = app.voiceCall.inCall ? HoolaSpace.touch + 8 : 0.0;
                  final bottom = keyboard ? 0.0 : hide ? MediaQuery.viewPaddingOf(context).bottom + 6 + pill : 96.0;
                  return AnimatedPadding(
                    duration: HoolaMotion.of(context, HoolaMotion.page),
                    curve: HoolaMotion.ease,
                    padding: EdgeInsets.only(bottom: bottom),
                    child: child,
                  );
                },
                child: AnimatedSwitcher(
                  duration: HoolaMotion.of(context, HoolaMotion.fade),
                  switchInCurve: HoolaMotion.ease,
                  child: KeyedSubtree(key: ValueKey(_tab), child: pages[_tab]),
                ),
              ),
            ),
            bottomNavigationBar: keyboard
                ? null
                : SafeArea(
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      ListenableBuilder(
                        listenable: app.voiceCall,
                        builder: (context, _) => app.voiceCall.inCall
                            ? Padding(
                                padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 8),
                                child: _CallPill(onOpen: _openTalk),
                              )
                            : const SizedBox.shrink(),
                      ),
                      ListenableBuilder(
                        listenable: app,
                        builder: (context, child) => _SlideAway(hidden: _navHidden, child: child!),
                        child: HoolaNav(tab: _tab, onTap: _go),
                      ),
                    ]),
                  ),
          );
        }),
      );
}

/// v0.888 the tab bar sliding down and out of the way (and folding its height so the chat gets the room),
/// then back up when the work ends. Reduce motion = a short fade.
class _SlideAway extends StatelessWidget {
  const _SlideAway({required this.hidden, required this.child});
  final bool hidden;
  final Widget child;
  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween(end: hidden ? 0 : 1),
        duration: HoolaMotion.of(context, HoolaMotion.page),
        curve: HoolaMotion.ease,
        builder: (context, v, child) => IgnorePointer(
          ignoring: hidden,
          child: ExcludeSemantics(
            excluding: hidden,
            child: ClipRect(
              child: Align(
                alignment: Alignment.topCenter,
                heightFactor: v,
                child: Opacity(
                  opacity: v.clamp(0.0, 1.0),
                  child: Transform.translate(offset: Offset(0, (1 - v) * 28), child: child),
                ),
              ),
            ),
          ),
        ),
        child: child,
      );
}

/// An old (Night Glass) screen inside the new frame, until its phase rebuilds it.
class _OldLook extends StatelessWidget {
  const _OldLook({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) => Theme(data: santoshTheme(), child: Aurora(child: child));
}

// ------------------------------------------------------------------------------------------------ the tab bar
/// v0.903 NAV PRO: one soft floating bar, four equal cells. v0.904 NAV BLACK (owner: "DONT PUT PINK EVERY WHERE ...
/// MAKE IT PERFECT BLACK" -> option A): the selected tab shows a solid black pill behind its ICON only (the label sits
/// below it, never inside), its icon fills in white, its label goes to ink; the Hoola tab keeps its own violet logo.
/// Icons are vectors drawn on one grid (hoola_nav_icons.dart). A label too long for its cell at a big text size
/// shrinks to fit instead of running past the cell.
class HoolaNav extends StatelessWidget {
  const HoolaNav({super.key, required this.tab, required this.onTap});
  final int tab;
  final ValueChanged<int> onTap;

  static const items = [
    (NavGlyph.hoola, 'Hoola'),
    (NavGlyph.employees, 'AI Employees'),   // v0.898
    (NavGlyph.tools, 'Tools'),              // v0.898
    (NavGlyph.computer, 'Computer'),        // v0.890
  ];

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    // R9: the bar grows with the phone's text size (labels capped at 1.4x), never overflows
    return MediaQuery.withClampedTextScaling(
      maxScaleFactor: 1.4,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: c.nav,
            borderRadius: HoolaRadius.r(HoolaRadius.pill),
            border: Border.all(color: c.line, width: .8),
            boxShadow: HoolaShadow.float(c),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 7),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              for (var i = 0; i < items.length; i++)
                Expanded(child: _NavItem(glyph: items[i].$1, label: items[i].$2, selected: tab == i, onTap: () => onTap(i))),
            ]),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatefulWidget {
  const _NavItem({required this.glyph, required this.label, required this.selected, required this.onTap});
  final NavGlyph glyph;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  @override
  State<_NavItem> createState() => _NavItemState();
}

class _NavItemState extends State<_NavItem> {
  bool _down = false;

  void _press(bool v) {
    if (_down != v) setState(() => _down = v);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final quick = HoolaMotion.of(context, HoolaMotion.page);
    return Semantics(
      button: true,
      selected: widget.selected,
      label: widget.label,
      onTap: widget.onTap,
      excludeSemantics: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => _press(true),
        onTapUp: (_) => _press(false),
        onTapCancel: () => _press(false),
        onTap: () {
          if (!widget.selected) HapticFeedback.selectionClick();
          widget.onTap();
        },
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 56),
          child: TweenAnimationBuilder<double>(
            tween: Tween(end: widget.selected ? 1 : 0),
            duration: quick,
            curve: HoolaMotion.ease,
            builder: (context, t, _) => AnimatedScale(
              scale: _down ? .94 : 1,
              duration: HoolaMotion.of(context, HoolaMotion.menu),
              curve: HoolaMotion.ease,
              child: Column(mainAxisSize: MainAxisSize.min, children: [   // top-aligned: a label that shrinks never moves its icon
                // the soft pill grows out from behind the icon
                SizedBox(
                  height: 32,
                  width: 64,
                  child: Stack(alignment: Alignment.center, children: [
                    if (t > 0)
                      Opacity(
                      opacity: t,
                      child: Container(
                        width: 36 + 24 * t,
                        height: 32,
                        decoration: BoxDecoration(color: c.pill, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
                      ),
                    ),
                    if (widget.glyph == NavGlyph.hoola)
                      // v0.904: the Hoola tab keeps its own violet Hoola logo; on the black pill the lighter violet
                      // (the one dark mode uses) so it still reads
                      HoolaMark(
                          size: 24,
                          animate: false,
                          color: widget.selected ? (c.dark ? HoolaColors.light.accent : HoolaColors.darkSet.accent) : null)
                    else
                      NavIcon(glyph: widget.glyph, on: t, cut: c.pill, color: Color.lerp(c.ink2, c.onPill, t)!),
                  ]),
                ),
                const SizedBox(height: 4),
                SizedBox(
                  width: double.infinity,
                  // one line box for every label, so a label that shrinks to fit still sits on the same line as the rest
                  height: MediaQuery.textScalerOf(context).scale(12) * 1.3 + 1,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(widget.label,
                        maxLines: 1,
                        style: HoolaType.label(c).copyWith(
                          color: Color.lerp(c.ink2, c.ink, t),
                          fontWeight: widget.selected ? FontWeight.w600 : FontWeight.w500,
                          letterSpacing: .1,
                        )),
                  ),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// While a call runs, a slim pill above the tab bar brings her back to it.
class _CallPill extends StatelessWidget {
  const _CallPill({required this.onOpen});
  final VoidCallback onOpen;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: 'Back to the call',
      excludeSemantics: true,
      child: GestureDetector(
        onTap: onOpen,
        child: Container(
          height: HoolaSpace.touch,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(color: c.pill, borderRadius: HoolaRadius.r(HoolaRadius.pill), boxShadow: HoolaShadow.float(c)),
          child: Row(children: [
            Container(width: 8, height: 8, decoration: BoxDecoration(color: c.ok, shape: BoxShape.circle)),
            const SizedBox(width: 10),
            Expanded(child: Text('On a call with Santosh', style: HoolaType.body(c).copyWith(color: c.onPill, fontWeight: FontWeight.w500))),
            Text('Open', style: HoolaType.body(c).copyWith(color: c.onPill, fontWeight: FontWeight.w600)),
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ the Hoola tab
/// Home (greeting + quick starts + composer) until the first message; then the chat (v0.862 R3: the new chat).
class _HoolaTab extends StatelessWidget {
  const _HoolaTab({required this.app, required this.onTalk, required this.onMenu});
  final Santosh app;
  final VoidCallback onTalk;
  final VoidCallback onMenu;

  bool get _hasChat => app.feed.any((f) => f.kind == 'message');

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => AnimatedSwitcher(
          duration: HoolaMotion.of(context, HoolaMotion.fade),
          child: _hasChat
              // v0.889 every chat its own session: its own scroll, reveal state and box (a switch crossfades)
              ? KeyedSubtree(key: ValueKey('chat:${app.conversationId}'), child: HoolaChat(app: app, onTalk: onTalk, onMenu: onMenu))
              : KeyedSubtree(key: const ValueKey('home'), child: HoolaHome(app: app, onTalk: onTalk, onMenu: onMenu)),
        ),
      );
}

class HoolaHome extends StatefulWidget {
  const HoolaHome({super.key, required this.app, required this.onTalk, required this.onMenu});
  final Santosh app;
  final VoidCallback onTalk;
  final VoidCallback onMenu;
  @override
  State<HoolaHome> createState() => _HoolaHomeState();
}

class _HoolaHomeState extends State<HoolaHome> {
  Santosh get app => widget.app;

  String _greeting() {
    final h = DateTime.now().hour;
    final part = h < 5 ? 'Good night' : h < 12 ? 'Morning' : h < 17 ? 'Afternoon' : h < 21 ? 'Evening' : 'Good night';
    final name = ((app.account?['name'] as String?) ?? '').trim().split(' ').first;
    return name.isEmpty ? part : '$part, $name';
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final waiting = app.waitingCards.length;
    final starts = <(IconData, String)>[
      if (waiting > 0) (Icons.circle, 'Review $waiting waiting ${waiting == 1 ? 'approval' : 'approvals'}'),
      (Icons.description_outlined, "Make this month's GST summary"),
      (Icons.chat_bubble_outline_rounded, "Reply to today's WhatsApp leads"),
      (Icons.event_outlined, "Plan tomorrow's calls"),
    ];
    return Column(children: [
      SizedBox(
        height: 60,
        child: Row(children: [
          const SizedBox(width: 6),
          IconButton(tooltip: 'Open chats', onPressed: widget.onMenu, icon: Icon(Icons.menu_rounded, color: c.ink)),
          const Spacer(),
          IconButton(tooltip: 'New chat', onPressed: () => app.newChat(), icon: Icon(Icons.edit_square, color: c.ink, size: 22)),
          const SizedBox(width: 6),
        ]),
      ),
      Expanded(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(children: [
            const SizedBox(height: 96),
            const _Appear(child: HoolaMark(size: 60, animate: false)),
            const SizedBox(height: 18),
            _Appear(delay: 60, child: Text(_greeting(), textAlign: TextAlign.center, style: HoolaType.hero(c))),
            const SizedBox(height: 10),
            _Appear(
              delay: 100,
              child: Text(
                waiting > 0 ? '${app.aName} is ready. $waiting ${waiting == 1 ? 'thing needs' : 'things need'} you.' : '${app.aName} is ready.',
                textAlign: TextAlign.center,
                style: HoolaType.body(c).copyWith(color: c.ink2),
              ),
            ),
            const SizedBox(height: 28),
            for (var i = 0; i < starts.length; i++)
              _Appear(
                delay: 140 + 40 * i,
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _StartChip(
                    icon: starts[i].$1,
                    dot: i == 0 && waiting > 0,
                    text: starts[i].$2,
                    onTap: () => app.send(starts[i].$2),
                  ),
                ),
              ),
          ]),
        ),
      ),
      HoolaComposer(app: app, onTalk: widget.onTalk),
      const SizedBox(height: 8),
    ]);
  }
}

class _StartChip extends StatelessWidget {
  const _StartChip({required this.icon, required this.text, required this.onTap, this.dot = false});
  final IconData icon;
  final String text;
  final VoidCallback onTap;
  final bool dot;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Material(
      color: c.surface,
      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), side: BorderSide(color: c.line)),
      child: InkWell(
        customBorder: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill)),
        onTap: onTap,
        child: Container(
          // R9: at least 48 dp; with big phone text the words wrap to a second line instead of being cut
          constraints: const BoxConstraints(minHeight: HoolaSpace.touch),
          padding: const EdgeInsets.fromLTRB(16, 6, 12, 6),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            if (dot)
              Container(width: 8, height: 8, decoration: BoxDecoration(color: c.warn, shape: BoxShape.circle))
            else
              Icon(icon, size: 18, color: c.ink2),
            const SizedBox(width: 10),
            Flexible(child: Text(text, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.body(c))),
            const SizedBox(width: 6),
            Icon(Icons.chevron_right_rounded, size: 18, color: c.ink3),
          ]),
        ),
      ),
    );
  }
}

/// Fade + rise once when the home appears (still under reduced motion).
class _Appear extends StatelessWidget {
  const _Appear({required this.child, this.delay = 0});
  final Widget child;
  final int delay;
  @override
  Widget build(BuildContext context) {
    if (HoolaMotion.reduced(context)) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 420 + delay),
      curve: Interval(delay / (420 + delay), 1, curve: HoolaMotion.ease),
      builder: (context, t, child) => Opacity(opacity: t, child: Transform.translate(offset: Offset(0, 8 * (1 - t)), child: child)),
      child: child,
    );
  }
}

// ------------------------------------------------------------------------------------------------ the composer
/// + · the field · mic · the voice button (or Send once she types).
class HoolaComposer extends StatefulWidget {
  const HoolaComposer({super.key, required this.app, required this.onTalk, this.hint = 'Type or hold to talk',
      this.controller, this.focus, this.working = false, this.onStop});
  final Santosh app;
  final VoidCallback onTalk;
  final String hint;
  /// v0.862 R3 the chat hands in its own box (Quote / Edit put text in it) and focus.
  final TextEditingController? controller;
  final FocusNode? focus;
  /// v0.862 R3 Santosh is working on this chat: the voice buttons become Stop until she types.
  final bool working;
  final VoidCallback? onStop;
  @override
  State<HoolaComposer> createState() => _HoolaComposerState();
}

class _HoolaComposerState extends State<HoolaComposer> {
  late final TextEditingController _text = widget.controller ?? TextEditingController();
  bool _typing = false;
  /// v0.895 files in the typing box: each shows at once (a photo is its own picture) and goes up in the background,
  /// three at a time; Send waits for the ones still going up.
  final List<TrayFile> _files = [];
  int _inFlight = 0;
  bool _waitingToSend = false;
  /// v0.895 Claude's Research switch (Add sheet): the next messages ask for deep research until she turns it off.
  bool _research = false;

  @override
  void initState() {
    super.initState();
    _typing = _text.text.trim().isNotEmpty;
    _text.addListener(() {
      final t = _text.text.trim().isNotEmpty;
      if (t != _typing && mounted) setState(() => _typing = t);
    });
  }

  @override
  void dispose() {
    if (widget.controller == null) _text.dispose();
    super.dispose();
  }

  bool get _uploading => _files.any((f) => f.uploading);
  List<String> get _ready => [for (final f in _files) if (f.done) '${f.sent!['file_id']}'];
  bool get _canSend => _typing || _files.any((f) => f.err == null);

  void _toast(String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

  /// Puts picked files in the box (20 at most, 30 MB each, like Claude) and starts their uploads.
  void _take(List<({String name, List<int> bytes, int size})> picked) {
    if (picked.isEmpty) return;
    var room = hoolaMaxFiles - _files.length;
    if (room <= 0) {
      _toast('Up to $hoolaMaxFiles files in one message');
      return;
    }
    if (picked.length > room) _toast('Up to $hoolaMaxFiles files in one message - added the first $room');
    for (final p in picked.take(room)) {
      final t = TrayFile(p.name, p.bytes);
      if (p.size > hoolaMaxBytes) {
        t.err = 'Over ${hoolaMaxBytes ~/ 1024 ~/ 1024} MB';
      } else if (p.bytes.isEmpty) {
        t.err = 'Empty file';
      } else if (p.bytes.length > hoolaMaxBytes) {
        t.err = 'Over ${hoolaMaxBytes ~/ 1024 ~/ 1024} MB';
      }
      _files.add(t);
    }
    setState(() {});
    _pump();
  }

  /// Three uploads at a time; each tile shows its own progress.
  void _pump() {
    for (final f in _files) {
      if (_inFlight >= 3) break;
      if (f.uploading && !_started.contains(f)) _upload(f);
    }
  }

  final Set<TrayFile> _started = {};

  Future<void> _upload(TrayFile f) async {
    _started.add(f);
    _inFlight++;
    try {
      final r = await widget.app.attachChatFile(f.name, f.bytes, onProgress: (p) {
        if (mounted && _files.contains(f)) setState(() => f.pct = p);
      });
      f.sent = r;
      final m = '${r['media'] ?? ''}';
      if (m.isNotEmpty && m != 'other') f.media = m;
    } catch (e) {
      f.err = _why(e);
    }
    _inFlight--;
    if (!mounted) return;
    setState(() {});
    _pump();
    if (_waitingToSend && !_uploading) _send();
  }

  String _why(Object e) {
    final t = '$e';
    if (t.contains('413')) return 'Too big';
    if (t.contains('khatarnak') || t.toLowerCase().contains('unsafe')) return 'Refused: unsafe';
    if (t.contains('Not connected')) return 'Not connected';
    return 'Not added';
  }

  void _retry(TrayFile f) {
    setState(() {
      f.err = null;
      f.pct = 0;
      _started.remove(f);
    });
    _pump();
  }

  void _remove(TrayFile f) => setState(() {
        _files.remove(f);
        _started.remove(f);
      });

  /// + : Claude's Add sheet - Camera / Photos / Files, Research and Memory switches, Connectors / computers / team.
  Future<void> _add() async {
    final pick = await showHoolaAddSheet(context, app: widget.app, research: _research, onResearch: (v) {
      if (mounted) setState(() => _research = v);
    });
    if (pick == null || !mounted) return;
    switch (pick) {
      case HoolaAddPick.camera:
        await _camera();
      case HoolaAddPick.photos:
        await _photos();
      case HoolaAddPick.files:
        await _pickFiles();
      case HoolaAddPick.connectors:
        await hoolaOpenNew(context, widget.app, HoolaConnectorsPage(app: widget.app));   // v0.898 inside Tools now
      case HoolaAddPick.computers:
        hoolaTabRequest.value = 3;
      case HoolaAddPick.team:
        await hoolaOpenNew(context, widget.app, HoolaTeam(app: widget.app));
    }
  }

  Future<void> _camera() async {
    try {
      final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 90, maxWidth: 3000, maxHeight: 3000);
      if (x == null) return;
      final b = await x.readAsBytes();
      _take([(name: x.name, bytes: b, size: b.length)]);
    } catch (e) {
      _toast('The camera did not open: $e');
    }
  }

  /// Photos AND videos, several at once (the phone's own photo picker).
  Future<void> _photos() async {
    try {
      final xs = await ImagePicker().pickMultipleMedia();
      final out = <({String name, List<int> bytes, int size})>[];
      for (final x in xs.take(hoolaMaxFiles)) {
        final n = await x.length();
        out.add((name: x.name, bytes: n > hoolaMaxBytes ? const <int>[] : await x.readAsBytes(), size: n));
      }
      _take(out);
    } catch (e) {
      _toast('Photos did not open: $e');
    }
  }

  /// Any file: documents, APKs, ZIPs, audio, code... several at once.
  Future<void> _pickFiles() async {
    try {
      final res = await FilePicker.platform.pickFiles(withData: true, allowMultiple: true, type: FileType.any);
      if (res == null) return;
      _take([
        for (final f in res.files)
          (name: f.name, bytes: f.size > hoolaMaxBytes ? const <int>[] : (f.bytes ?? const <int>[]), size: f.size),
      ]);
    } catch (e) {
      _toast('Files did not open: $e');
    }
  }

  Future<void> _send() async {
    var t = _text.text.trim();
    if (!_canSend) return;
    if (_uploading) {
      // Claude sends when the last one is up: hold the message, the tiles keep showing their progress
      setState(() => _waitingToSend = true);
      return;
    }
    _waitingToSend = false;
    final ids = _ready;
    if (t.isEmpty && ids.isEmpty) {
      setState(() {});
      return;
    }
    if (t.isEmpty) t = ids.length == 1 ? 'Here is a file' : 'Here are ${ids.length} files';
    HapticFeedback.lightImpact();
    final keep = List.of(_files);
    _text.clear();
    setState(() {
      _files.clear();
      _started.clear();
    });
    final ok = await widget.app.send(t, files: ids, research: _research);
    if (!ok && mounted) {
      _text.text = t;   // nothing lost when it did not go
      setState(() => _files.addAll(keep));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    // v0.888 one control, one size: every button is a 48 dp tap area holding a 40 dp circle and a 22 dp icon, so +,
    // mic, voice, Send and Stop sit on one line with the field (her report: the bar looked uneven - + was a grey
    // disc, mic bare, voice a white disc, all 42 dp hanging 3 dp below the 48 dp field). Plain controls are bare
    // icons; only the one main action (voice / Send / Stop) is filled, as in Claude.
    Widget ctl(String tip, IconData icon, VoidCallback onTap, {bool filled = false, Color? bg}) => Semantics(
          button: true,
          label: tip,
          excludeSemantics: true,
          child: SizedBox(
            width: HoolaSpace.touch,
            height: HoolaSpace.touch,
            child: Center(
              child: Material(
                color: filled ? (bg ?? c.pill) : Colors.transparent,
                shape: const CircleBorder(),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: onTap,
                  child: SizedBox(
                    width: 40,
                    height: 40,
                    child: Icon(icon, size: 22, color: filled ? (bg == c.accent ? c.onAccent : c.onPill) : c.ink2),
                  ),
                ),
              ),
            ),
          ),
        );
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: c.surface,
          // v0.895 a pill on one line; a rounded card (Claude's 28) once files or the Research chip sit in it
          borderRadius: (_files.isEmpty && !_research) ? HoolaRadius.r(HoolaRadius.pill) : BorderRadius.circular(28),
          border: Border.all(color: c.line),
          boxShadow: HoolaShadow.float(c),
        ),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          // v0.895 Claude's tray: big thumbnails, a dark x on each, a spinner while each goes up
          HoolaAttachTray(
            files: _files,
            onRemove: _remove,
            onRetry: _retry,
            onOpen: (f) => openAttachment(context, widget.app, [for (final x in _files) if (x.done) x.view],
                [for (final x in _files) if (x.done) x].indexOf(f)),
          ),
          if (_research)
            Align(
              alignment: Alignment.centerLeft,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 6, 10, 0),
                child: InputChip(
                  avatar: Icon(Icons.travel_explore_rounded, size: 16, color: c.accent),
                  label: Text('Research', style: HoolaType.small(c).copyWith(color: c.ink, fontWeight: FontWeight.w500)),
                  backgroundColor: c.accentSoft,
                  side: BorderSide.none,
                  deleteIconColor: c.ink2,
                  deleteButtonTooltipMessage: 'Turn Research off',
                  onDeleted: () => setState(() => _research = false),
                ),
              ),
            ),
          if (_waitingToSend && _uploading)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 0),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('Sends when the files are up', style: HoolaType.small(c)),
              ),
            ),
          // end-aligned: on one line every control centres on the field (all 48 dp); a long message grows upward
          // and the controls stay at its foot
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            ctl('Add photos, files and more', Icons.add_rounded, _add),
            Expanded(
              child: TextField(
                controller: _text,
                focusNode: widget.focus,
                minLines: 1,
                maxLines: 6,
                textInputAction: TextInputAction.newline,
                textAlignVertical: TextAlignVertical.center,
                style: HoolaType.bodyLarge(c),
                cursorColor: c.accent,
                decoration: InputDecoration(
                  hintText: widget.hint,
                  hintMaxLines: 1,
                  filled: false,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  isDense: true,
                  constraints: const BoxConstraints(minHeight: HoolaSpace.touch),   // R9: a 48 dp tap target
                  contentPadding: const EdgeInsets.fromLTRB(4, 12, 4, 12),
                ),
              ),
            ),
            AnimatedSwitcher(
              duration: HoolaMotion.of(context, HoolaMotion.menu),
              transitionBuilder: (child, a) => ScaleTransition(scale: a, child: FadeTransition(opacity: a, child: child)),
              child: _canSend
                  ? KeyedSubtree(key: const ValueKey('send'), child: ctl('Send', Icons.arrow_upward_rounded, _send, filled: true, bg: c.accent))
                  : (widget.working && widget.onStop != null)
                  ? KeyedSubtree(key: const ValueKey('stop'), child: ctl('Stop', Icons.stop_rounded, widget.onStop!, filled: true))
                  : Row(key: const ValueKey('talk'), mainAxisSize: MainAxisSize.min, children: [
                      ctl('Talk to ${widget.app.aName}', Icons.mic_none_rounded, widget.onTalk),
                      ctl('Start a call', Icons.graphic_eq_rounded, widget.onTalk, filled: true),
                    ]),
            ),
          ]),
        ]),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ the drawer
class HoolaDrawer extends StatefulWidget {
  const HoolaDrawer({
    super.key,
    required this.app,
    required this.onNewChat,
    required this.onOpenChat,
    required this.onCalls,
    required this.onMemory,
    required this.onSettings,
    this.onWork,
    this.onMade,
  });
  final Santosh app;
  final VoidCallback onNewChat;
  final ValueChanged<String> onOpenChat;
  final VoidCallback onCalls;
  final VoidCallback onMemory;
  final VoidCallback onSettings;
  final VoidCallback? onWork, onMade;   // v0.898
  @override
  State<HoolaDrawer> createState() => _HoolaDrawerState();
}

class _HoolaDrawerState extends State<HoolaDrawer> {
  bool _all = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => widget.app.refreshChats());
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final app = widget.app;
    final name = ((app.account?['name'] as String?) ?? '').trim();
    return Drawer(
      backgroundColor: c.bg,
      surfaceTintColor: Colors.transparent,
      width: MediaQuery.sizeOf(context).width * .86,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.horizontal(right: Radius.circular(HoolaRadius.sheet))),
      child: SafeArea(
        child: ListenableBuilder(
          listenable: app,
          builder: (context, _) {
            final chats = app.chatList;
            final shown = _all ? chats : chats.take(9).toList();
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 8),
                child: Text('Hoola', style: HoolaType.hero(c)),
              ),
              Expanded(
                child: ListView(padding: const EdgeInsets.symmetric(horizontal: 12), children: [
                  _section('Recents', c),
                  if (chats.isEmpty) Padding(
                    padding: const EdgeInsets.fromLTRB(10, 4, 10, 8),
                    child: Text('No chats yet', style: HoolaType.body(c).copyWith(color: c.ink3)),
                  ),
                  for (final ch in shown) _chatRow(ch, c),
                  if (!_all && chats.length > 9)
                    _row(c, null, 'All chats', () => setState(() => _all = true), chevron: true),
                  Padding(padding: const EdgeInsets.symmetric(vertical: 10), child: Divider(color: c.line, indent: 8, endIndent: 8)),
                  _section('More', c),
                  if (widget.onWork != null) _row(c, Icons.work_outline_rounded, 'Work', widget.onWork!),
                  if (widget.onMade != null) _row(c, Icons.layers_outlined, 'Made by ${app.aName}', widget.onMade!),
                  _row(c, Icons.call_outlined, 'Calls', widget.onCalls),
                  _row(c, Icons.lightbulb_outline_rounded, 'What ${app.aName} remembers', widget.onMemory),
                ]),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                child: Row(children: [
                  Semantics(
                    button: true,
                    label: 'Settings',
                    excludeSemantics: true,
                    child: GestureDetector(
                      onTap: widget.onSettings,
                      child: CircleAvatar(
                        radius: 22,
                        backgroundColor: c.accent,
                        child: Text(name.isEmpty ? 'H' : name[0].toUpperCase(),
                            style: HoolaType.title(c).copyWith(color: c.onAccent)),
                      ),
                    ),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: widget.onNewChat,
                    icon: const Icon(Icons.add_rounded, size: 20),
                    label: const Text('New chat'),
                  ),
                ]),
              ),
            ]);
          },
        ),
      ),
    );
  }

  Widget _section(String t, HoolaColors c) =>
      Padding(padding: const EdgeInsets.fromLTRB(10, 8, 10, 6), child: Text(t, style: HoolaType.body(c).copyWith(fontSize: 14, color: c.ink3)));

  Widget _chatRow(Map<String, dynamic> ch, HoolaColors c) {
    final id = '${ch['id'] ?? ''}';
    final call = '${ch['kind'] ?? ''}' == 'call';
    final title = '${ch['title'] ?? ''}'.trim();
    final on = id == widget.app.conversationId;
    // v0.863 R3s the chat's newest ask, from the server's one turn result: working / needs you / did not finish.
    // A finished chat stays quiet (no badge), like a read message.
    final r = ch['result'] is Map ? Map<String, dynamic>.from(ch['result'] as Map) : const <String, dynamic>{};
    final st = '${r['status'] ?? ''}';
    Widget? trail;
    String? say;
    final busy = widget.app.busyChats.contains(id);
    final unread = !on && widget.app.unreadChats.contains(id);
    if (busy || st == 'working' || st == 'queued') {
      trail = SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.8, color: c.accent));
      say = 'working';
    } else if (r['needs_you'] == true || st == 'needs_you') {
      trail = Container(width: 9, height: 9, decoration: BoxDecoration(color: c.warn, shape: BoxShape.circle));
      say = 'needs your answer';
    } else if (st == 'failed' || st == 'stuck') {
      trail = Icon(Icons.error_outline_rounded, size: 16, color: c.bad);
      say = 'did not finish';
    } else if (unread) {
      // v0.889 a reply came in this chat while she was in another one (the console's unread dot)
      trail = Container(width: 9, height: 9, decoration: BoxDecoration(color: c.accent, shape: BoxShape.circle));
      say = 'new reply';
    }
    return Semantics(
      label: say == null ? null : '${title.isEmpty ? 'New chat' : title}, $say',
      child: _row(c, call ? Icons.call_outlined : Icons.chat_bubble_outline_rounded, title.isEmpty ? 'New chat' : title,
          () => widget.onOpenChat(id), selected: on, trail: trail),
    );
  }

  Widget _row(HoolaColors c, IconData? icon, String text, VoidCallback onTap,
          {bool selected = false, bool chevron = false, Widget? trail}) =>
      Material(
        color: selected ? c.sunk : Colors.transparent,
        borderRadius: HoolaRadius.r(HoolaRadius.tile),
        child: InkWell(
          borderRadius: HoolaRadius.r(HoolaRadius.tile),
          onTap: onTap,
          child: SizedBox(
            height: 46,
            child: Row(children: [
              const SizedBox(width: 10),
              if (icon != null) ...[Icon(icon, size: 18, color: c.ink2), const SizedBox(width: 14)],
              Expanded(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.bodyLarge(c))),
              if (trail != null) ...[const SizedBox(width: 8), trail],
              if (chevron) Icon(Icons.chevron_right_rounded, size: 18, color: c.ink3),
              const SizedBox(width: 10),
            ]),
          ),
        ),
      );
}
