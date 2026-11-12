// v0.861 R2 THE SHELL (docs/HOOLA_APP_REDESIGN_PLAN.md R2): the Claude-style frame of the app in Hoola's brand.
//
//   4 tabs in a floating pill bar: Hoola (home + chat) · Work · Connect · Made
//   a drawer (her recent chats + calls, All chats, what Santosh remembers, her avatar -> Settings, New chat)
//   the pill composer (+ · "Type or hold to talk" · mic · the black voice button that opens Talk)
//
// Behind Santosh.newLook (Main > "Try the new design") until R3-R7 rebuild the screens inside it: today the tabs
// still show the old screens (Night Glass) in their own frame; only the frame, the drawer, the home and the composer
// are new. Every colour / size / movement comes from hoola_theme.dart.
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../artifacts_screen.dart';
import '../bazar_screen.dart';
import '../calls_sheet.dart';
import '../chat/hoola_chat.dart';
import '../glass.dart';
import '../hoola_theme.dart';
import '../talk/hoola_talk.dart';
import '../memory_page_screen.dart';
import '../profile_screen.dart';
import '../today_screen.dart';
import '../voice_screen.dart';

/// The Hoola mark (the owner's logo) as drawn in the app.
const _mark = 'assets/images/hoola_logo_fg.png';

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
    await app.connect(fresh: true);
  }

  @override
  Widget build(BuildContext context) => HoolaTheme(
        appearance: app.appearance,
        child: Builder(builder: (context) {
          final c = HoolaColors.of(context);
          final keyboard = MediaQuery.viewInsetsOf(context).bottom > 0;
          final pages = <Widget>[
            _HoolaTab(app: app, onTalk: _openTalk, onMenu: () => _scaffold.currentState?.openDrawer()),
            _OldLook(child: TodayScreen(app: app, onTab: (i) => _go(i == 1 ? 0 : i == 3 ? 2 : 1))),
            _OldLook(child: BazarScreen(app: app, embedded: true)),
            _OldLook(child: ArtifactsScreen(app: app)),
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
              onSettings: () {
                Navigator.of(context).maybePop();
                _openOld(ProfileScreen(app: app, onReset: widget.onReset));
              },
            ),
            body: SafeArea(
              bottom: false,
              child: Padding(
                padding: EdgeInsets.only(bottom: keyboard ? 0 : 96),
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
                      HoolaNav(tab: _tab, onTap: _go),
                    ]),
                  ),
          );
        }),
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
class HoolaNav extends StatelessWidget {
  const HoolaNav({super.key, required this.tab, required this.onTap});
  final int tab;
  final ValueChanged<int> onTap;

  static const _items = [
    (null, null, 'Hoola'),
    (Icons.work_outline_rounded, Icons.work_rounded, 'Work'),
    (Icons.power_outlined, Icons.power_rounded, 'Connect'),
    (Icons.layers_outlined, Icons.layers_rounded, 'Made'),
  ];

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
      child: Container(
        height: 68,
        padding: const EdgeInsets.all(5),
        decoration: BoxDecoration(
          color: c.nav,
          borderRadius: HoolaRadius.r(HoolaRadius.pill),
          border: Border.all(color: c.line),
          boxShadow: HoolaShadow.float(c),
        ),
        child: Row(children: [
          for (var i = 0; i < _items.length; i++)
            Expanded(
              child: Semantics(
                button: true,
                selected: tab == i,
                label: _items[i].$3,
                excludeSemantics: true,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => onTap(i),
                  child: AnimatedContainer(
                    duration: HoolaMotion.of(context, HoolaMotion.menu),
                    curve: HoolaMotion.ease,
                    decoration: BoxDecoration(
                      color: tab == i ? c.navOn : Colors.transparent,
                      borderRadius: HoolaRadius.r(HoolaRadius.pill),
                    ),
                    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      if (_items[i].$1 == null)
                        SizedBox(width: 24, height: 24, child: Transform.scale(scale: 1.7, child: Image.asset(_mark)))
                      else
                        AnimatedSwitcher(
                          duration: HoolaMotion.of(context, HoolaMotion.menu),
                          child: Icon(tab == i ? _items[i].$2 : _items[i].$1,
                              key: ValueKey(tab == i), size: 23, color: tab == i ? c.ink : c.ink2),
                        ),
                      const SizedBox(height: 3),
                      Text(_items[i].$3,
                          style: HoolaType.label(c).copyWith(
                              color: tab == i ? c.ink : c.ink2, fontWeight: tab == i ? FontWeight.w600 : FontWeight.w500)),
                    ]),
                  ),
                ),
              ),
            ),
        ]),
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
          height: 44,
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
              ? KeyedSubtree(key: const ValueKey('chat'), child: HoolaChat(app: app, onTalk: onTalk, onMenu: onMenu))
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
          IconButton(tooltip: 'New chat', onPressed: () => app.connect(fresh: true), icon: Icon(Icons.edit_square, color: c.ink, size: 22)),
          const SizedBox(width: 6),
        ]),
      ),
      Expanded(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(children: [
            const SizedBox(height: 96),
            _Appear(child: SizedBox(width: 64, height: 64, child: Transform.scale(scale: 1.5, child: Image.asset(_mark)))),
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
          height: HoolaSpace.touch,
          padding: const EdgeInsets.fromLTRB(16, 0, 12, 0),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            if (dot)
              Container(width: 8, height: 8, decoration: BoxDecoration(color: c.warn, shape: BoxShape.circle))
            else
              Icon(icon, size: 18, color: c.ink2),
            const SizedBox(width: 10),
            Flexible(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c))),
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
  /// Files added with +: name, the server's file id once uploaded (null while uploading), upload error.
  final List<({String name, String? id, String? error})> _files = [];

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

  bool get _uploading => _files.any((f) => f.id == null && f.error == null);
  List<String> get _ready => [for (final f in _files) if (f.id != null) f.id!];

  /// + : pick files; each goes up at once (the same upload as the chat's paperclip) and waits as a chip.
  Future<void> _add() async {
    final res = await FilePicker.platform.pickFiles(withData: true, allowMultiple: true);
    if (res == null) return;
    for (final f in res.files) {
      if (f.bytes == null) continue;
      final i = _files.length;
      setState(() => _files.add((name: f.name, id: null, error: null)));
      try {
        final r = await widget.app.attachChatFile(f.name, f.bytes!);
        if (mounted) setState(() => _files[i] = (name: f.name, id: '${r['file_id']}', error: null));
      } catch (e) {
        if (mounted) setState(() => _files[i] = (name: f.name, id: null, error: '$e'));
      }
    }
  }

  Future<void> _send() async {
    var t = _text.text.trim();
    final ids = _ready;
    if ((t.isEmpty && ids.isEmpty) || _uploading) return;
    if (t.isEmpty) t = ids.length == 1 ? 'Here is a file' : 'Here are ${ids.length} files';
    HapticFeedback.lightImpact();
    final keep = List.of(_files);
    _text.clear();
    setState(_files.clear);
    final ok = await widget.app.send(t, files: ids);
    if (!ok && mounted) {
      _text.text = t;   // nothing lost when it did not go
      setState(() => _files.addAll(keep));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget round(String tip, IconData icon, VoidCallback onTap, {bool filled = false, Color? bg}) => Semantics(
          button: true,
          label: tip,
          excludeSemantics: true,
          child: Material(
            color: filled ? (bg ?? c.pill) : Colors.transparent,
            shape: const CircleBorder(),
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: onTap,
              child: SizedBox(width: 42, height: 42, child: Icon(icon, size: 21, color: filled ? c.onPill : c.ink2)),
            ),
          ),
        );
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Container(
        constraints: const BoxConstraints(minHeight: 58),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: HoolaRadius.r(29),
          border: Border.all(color: c.line),
          boxShadow: HoolaShadow.float(c),
        ),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (_files.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(6, 2, 6, 8),
              child: Wrap(spacing: 8, runSpacing: 8, children: [
                for (var i = 0; i < _files.length; i++)
                  InputChip(
                    avatar: _files[i].id == null && _files[i].error == null
                        ? SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3))
                        : Icon(_files[i].error != null ? Icons.error_outline_rounded : Icons.insert_drive_file_outlined,
                            size: 16, color: _files[i].error != null ? c.bad : c.ink2),
                    label: Text(_files[i].error != null ? '${_files[i].name} · not added' : _files[i].name,
                        maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink)),
                    backgroundColor: c.sunk,
                    side: BorderSide.none,
                    deleteIconColor: c.ink3,
                    onDeleted: () => setState(() => _files.removeAt(i)),
                  ),
              ]),
            ),
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Semantics(
            button: true,
            label: 'Add a file or photo',
            excludeSemantics: true,
            child: Material(
              color: c.sunk,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: _add,
                child: SizedBox(width: 42, height: 42, child: Icon(Icons.add_rounded, size: 22, color: c.ink)),
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: TextField(
                controller: _text,
                focusNode: widget.focus,
                minLines: 1,
                maxLines: 6,
                textInputAction: TextInputAction.newline,
                style: HoolaType.bodyLarge(c),
                cursorColor: c.accent,
                decoration: InputDecoration(
                  hintText: widget.hint,
                  filled: false,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  isDense: true,
                  contentPadding: const EdgeInsets.symmetric(vertical: 11),
                ),
              ),
            ),
          ),
          AnimatedSwitcher(
            duration: HoolaMotion.of(context, HoolaMotion.menu),
            transitionBuilder: (child, a) => ScaleTransition(scale: a, child: FadeTransition(opacity: a, child: child)),
            child: (_typing || _ready.isNotEmpty)
                ? KeyedSubtree(key: const ValueKey('send'), child: round('Send', Icons.arrow_upward_rounded, _send, filled: true, bg: c.accent))
                : (widget.working && widget.onStop != null)
                ? KeyedSubtree(key: const ValueKey('stop'), child: round('Stop', Icons.stop_rounded, widget.onStop!, filled: true))
                : Row(key: const ValueKey('talk'), mainAxisSize: MainAxisSize.min, children: [
                    round('Talk to ${widget.app.aName}', Icons.mic_none_rounded, widget.onTalk),
                    const SizedBox(width: 4),
                    round('Start a call', Icons.graphic_eq_rounded, widget.onTalk, filled: true),
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
  });
  final Santosh app;
  final VoidCallback onNewChat;
  final ValueChanged<String> onOpenChat;
  final VoidCallback onCalls;
  final VoidCallback onMemory;
  final VoidCallback onSettings;
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
    if (st == 'working' || st == 'queued') {
      trail = SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.8, color: c.accent));
      say = 'working';
    } else if (r['needs_you'] == true || st == 'needs_you') {
      trail = Container(width: 9, height: 9, decoration: BoxDecoration(color: c.warn, shape: BoxShape.circle));
      say = 'needs your answer';
    } else if (st == 'failed' || st == 'stuck') {
      trail = Icon(Icons.error_outline_rounded, size: 16, color: c.bad);
      say = 'did not finish';
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
