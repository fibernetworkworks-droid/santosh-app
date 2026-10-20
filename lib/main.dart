import 'dart:convert';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'device.dart';
import 'emotion.dart';
import 'native.dart';
import 'nav.dart';
import 'state.dart';
import 'ui/avatar_setup_screen.dart';
import 'ui/bazar_screen.dart';
import 'ui/catchup_screen.dart';
import 'ui/chat_screen.dart';
import 'ui/glass.dart';
import 'ui/profile_screen.dart';
import 'ui/setup_screen.dart';
import 'ui/today_screen.dart';
import 'ui/reels_screen.dart';
import 'ui/tv_screen.dart';
import 'ui/live_voice_screen.dart';
import 'ui/lock_safe.dart';
import 'ui/voice_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Device.instance.init();
  final app = await Santosh.load();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent, statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Color(0xFF0B0A1A), systemNavigationBarIconBrightness: Brightness.light));
  runApp(SantoshApp(app: app));
}

class SantoshApp extends StatefulWidget {
  const SantoshApp({super.key, required this.app});
  final Santosh app;
  @override
  State<SantoshApp> createState() => _SantoshAppState();
}

class _SantoshAppState extends State<SantoshApp> with WidgetsBindingObserver {
  bool _setup = false;
  static const _linkCh = EventChannel('santosh/links');
  StreamSubscription? _linkSub;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    HoolaTv.app = widget.app;
    LockSafe.app = widget.app;   // keep-alive steps per phone maker   // the TV player opens from links and phone actions too
    _setup = !widget.app.configured;
    if (!_setup) widget.app.connect();
    _listenForSignIn();
  }

  void _listenForSignIn() {
    // the native side sends the session token from santosh://auth?session=<token>
    _linkSub = _linkCh.receiveBroadcastStream().listen((token) async {
      final t = token?.toString() ?? '';
      if (t.isEmpty) return;
      if (t.startsWith('wake:')) {
        widget.app.wake(locked: t == 'wake:locked');
        return;
      }
      if (t.startsWith('share:')) {
        try {
          final share = Map<String, dynamic>.from(jsonDecode(t.substring(6)) as Map);
          // a reel (link from Instagram / YouTube / Facebook / Snapchat / Moj..., or one screen recording): the Reels card
          if (HoolaReels.isReelShare(share)) {
            if (!await openReel(share)) widget.app.onShared(share);
          } else {
            widget.app.onShared(share);
          }
        } catch (_) {}
        return;
      }
      if (t.startsWith('tv:')) {
        openTv(t.substring(3));
        return;
      }
      if (t.startsWith('bazar:')) {
        widget.app.onBazarLinked(t.endsWith('=1'));
        return;
      }
      if (t.startsWith('mail:')) {
        widget.app.onMailLinked(t.endsWith('=1'));
        return;
      }
      if (t.startsWith('calendar:')) {
        widget.app.onCalendarLinked(t.endsWith('=1'));
        return;
      }
      if (t.startsWith('connect:')) {
        widget.app.onConnectLink(t.substring(8));
        return;
      }
      for (final g in const ['sheets', 'drive', 'forms', 'slides', 'photos', 'youtube']) {
        if (t.startsWith('$g:')) {
          widget.app.onGoogleLinked(g, t.endsWith('=1'));
          return;
        }
      }
      await widget.app.applySession(t);
      if (widget.app.connected && mounted) setState(() => _setup = false);
    }, onError: (_) {});
  }

  @override
  void dispose() {
    _linkSub?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    widget.app.inBackground = s != AppLifecycleState.resumed;
    if (s == AppLifecycleState.paused) widget.app.markSeen();
    if (s == AppLifecycleState.resumed && widget.app.configured) {
      widget.app.catchUp().then((r) {
        final nav = navKey.currentState;
        if (r != null && nav != null) nav.push(MaterialPageRoute(builder: (_) => CatchUpScreen(app: widget.app, data: r)));
      });
      widget.app.refreshReminders();
      widget.app.refreshLists();
      widget.app.refreshRoutines();
      widget.app.refreshBackgroundInfo();
      widget.app.refreshBazar();
      widget.app.pushLocation();
    }
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        navigatorKey: navKey,
        title: 'Hoola',
        debugShowCheckedModeBanner: false,
        theme: santoshTheme(),
        home: _setup
            ? SetupScreen(app: widget.app, onDone: () => setState(() => _setup = false))
            : Home(app: widget.app, onReset: () => setState(() => _setup = true)),
      );
}

class Home extends StatefulWidget {
  const Home({super.key, required this.app, required this.onReset});
  final Santosh app;
  final VoidCallback onReset;
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int _tab = 0;
  int _seenBaat = 0;
  int _seenShare = 0;

  @override
  void initState() {
    super.initState();
    _seenBaat = widget.app.baatTick;
    // create the call session now, so "Hey Santosh" can start a call from any screen
    _inCall = widget.app.voiceCall.inCall;
    widget.app.voiceCall.addListener(_onCall);
    widget.app.addListener(_onApp);
  }

  bool _inCall = false;

  void _onCall() {
    final now = widget.app.voiceCall.inCall;
    if (now != _inCall && mounted) setState(() => _inCall = now);
  }

  @override
  void dispose() {
    widget.app.voiceCall.removeListener(_onCall);
    widget.app.removeListener(_onApp);
    super.dispose();
  }

  bool _wasLocked = false;
  bool _wasSetup = false;

  void _onApp() {
    if (widget.app.needsAvatarSetup != _wasSetup) {
      _wasSetup = widget.app.needsAvatarSetup;
      if (mounted) setState(() {});
      return;
    }
    if (widget.app.shareTick != _seenShare) {
      _seenShare = widget.app.shareTick;
      if (mounted && _tab != 1) setState(() => _tab = 1);     // shared from another app: open Chat with it
      return;
    }
    if (widget.app.baatTick != _seenBaat) {
      _seenBaat = widget.app.baatTick;
      if (mounted) setState(() => _tab = 2);
    } else if (widget.app.lockedMode != _wasLocked && mounted) {
      setState(() {});
    }
    _wasLocked = widget.app.lockedMode;
  }

  void _go(int i) {
    if (i == _tab) return;
    HapticFeedback.selectionClick();
    setState(() => _tab = i);
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      TodayScreen(app: widget.app, onTab: _go),
      ChatScreen(app: widget.app, onVoice: () => _go(2)),
      // the screen is built only while open; the call itself lives in app.voiceCall and keeps going
      _tab == 2
          ? LiveVoiceGate(app: widget.app)
          : const SizedBox.shrink(),
      BazarScreen(app: widget.app, embedded: true),
      ProfileScreen(app: widget.app, onReset: widget.onReset),
    ];
    if (widget.app.needsAvatarSetup && !widget.app.lockedMode) {
      // first run of Hoola: the owner names their avatar and sets Mere Niyam before anything else
      return AvatarSetupScreen(app: widget.app, firstRun: true);
    }
    if (widget.app.lockedMode) {
      // over the lock screen: just the call. Nothing else of the app is visible until the phone is unlocked.
      return Scaffold(
        body: Aurora(
          tint: moodStyles[widget.app.mood]!.aura,
          child: SafeArea(
            child: Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                child: Row(children: [
                  const Icon(Icons.lock_outline_rounded, color: C.teal, size: 18),
                  const SizedBox(width: 6),
                  const Expanded(child: Text('Phone locked · sirf Baat', style: TextStyle(color: C.teal, fontWeight: FontWeight.w700, fontSize: 13))),
                  TextButton(
                    onPressed: () async {
                      if (await Native.requestUnlock()) {
                        widget.app.lockedMode = false;
                        widget.app.notifyChange();
                      }
                    },
                    child: const Text('Unlock karke poora app'),
                  ),
                ]),
              ),
              Expanded(child: LiveVoiceGate(app: widget.app)),
            ]),
          ),
        ),
      );
    }
    final keyboard = MediaQuery.viewInsetsOf(context).bottom > 0;
    return Scaffold(
      extendBody: true,
      body: ListenableBuilder(
        listenable: widget.app,
        builder: (context, child) => Aurora(tint: _tab == 2 ? moodStyles[widget.app.mood]!.aura : null, child: child!),
        child: SafeArea(
          bottom: false,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 280),
            switchInCurve: Curves.easeOutCubic,
            transitionBuilder: (c, a) => FadeTransition(opacity: a, child: SlideTransition(position: Tween(begin: const Offset(0, .015), end: Offset.zero).animate(a), child: c)),
            child: KeyedSubtree(key: ValueKey(_tab), child: Padding(padding: EdgeInsets.only(bottom: keyboard ? 0 : (_inCall && _tab != 2 ? 152 : 92)), child: pages[_tab])),
          ),
        ),
      ),
      // while typing, the tab bar steps aside so the message box sits right on the keyboard (no gap)
      bottomNavigationBar: keyboard ? null : SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          // the call keeps going on every screen; this bar brings you back to it
          if (_tab != 2) CallBar(app: widget.app, onOpen: () => _go(2)),
          _NavBar(tab: _tab, onTap: _go),
        ]),
      ),
    );
  }
}

/// Floating glass tab bar with the live-voice button raised in the middle.
class _NavBar extends StatelessWidget {
  const _NavBar({required this.tab, required this.onTap});
  final int tab;
  final ValueChanged<int> onTap;

  Widget _item(int i, IconData icon, IconData on, String label) {
    final sel = tab == i;
    return Expanded(
      child: Semantics(
        selected: sel,
        button: true,
        label: label,
        child: Press(
          onTap: () => onTap(i),
          haptic: false,
          child: SizedBox(
            height: 62,
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              AnimatedScale(scale: sel ? 1.12 : 1, duration: const Duration(milliseconds: 220), curve: Curves.easeOutBack,
                  child: Icon(sel ? on : icon, color: sel ? C.accent : C.muted, size: 23)),
              const SizedBox(height: 3),
              AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 200),
                style: TextStyle(fontSize: 11, fontWeight: sel ? FontWeight.w800 : FontWeight.w600, color: sel ? C.accent : C.muted),
                child: Text(label),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
        child: SizedBox(
          height: 84,
          child: Stack(clipBehavior: Clip.none, alignment: Alignment.bottomCenter, children: [
            Glass(
              radius: 26,
              padding: const EdgeInsets.symmetric(horizontal: 4),
              opacity: .1,
              child: Row(children: [
                _item(0, Icons.home_outlined, Icons.home_rounded, 'Aaj'),
                _item(1, Icons.chat_bubble_outline_rounded, Icons.chat_bubble_rounded, 'Chat'),
                const Expanded(child: SizedBox()),
                _item(3, Icons.power_outlined, Icons.power_rounded, 'Connect'),
                _item(4, Icons.person_outline_rounded, Icons.person_rounded, 'Main'),
              ]),
            ),
            Positioned(
              top: -4,
              child: Semantics(
                button: true,
                label: 'Baat — live voice',
                child: Press(
                  onTap: () => onTap(2),
                  child: Container(
                    width: 62,
                    height: 62,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const RadialGradient(colors: [Color(0xFFFFE3BE), Color(0xFFFF9A3C), Color(0xFFB45CFF)], stops: [0, .35, 1], center: Alignment(-.35, -.4)),
                      boxShadow: [BoxShadow(color: const Color(0xFFFF8C3C).withOpacity(tab == 2 ? .75 : .5), blurRadius: tab == 2 ? 30 : 22, offset: const Offset(0, 8))],
                      border: Border.all(color: Colors.white.withOpacity(tab == 2 ? .7 : .25), width: 2),
                    ),
                    child: const Icon(Icons.mic_rounded, color: C.onAccent, size: 28),
                  ),
                ),
              ),
            ),
          ]),
        ),
      );
}


/// Live human-like call when the server has realtime voice, otherwise the phone's own speech.
class LiveVoiceGate extends StatelessWidget {
  const LiveVoiceGate({super.key, required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => app.realtimeVoice ? LiveVoiceScreen(app: app) : VoiceScreen(app: app),
      );
}
