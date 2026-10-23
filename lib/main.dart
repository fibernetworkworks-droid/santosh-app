import 'dart:convert';
import 'dart:io' show File;
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
import 'ui/feedback_screen.dart';
import 'ui/catchup_screen.dart';
import 'ui/chat_screen.dart';
import 'ui/glass.dart';
import 'ui/profile_screen.dart';
import 'ui/setup_screen.dart';
import 'ui/today_screen.dart';
import 'ui/reels_screen.dart';
import 'ui/scroll_screen.dart';
import 'ui/tv_screen.dart';
import 'ui/live_voice_screen.dart';
import 'ui/keep_alive.dart';
import 'ui/lock_safe.dart';
import 'ui/phone_hoola.dart';
import 'ui/video_shrink.dart';
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

  /// v0.56 "Share to Hoola" from any app: big videos are made smaller first (progress, Rok do), then
  /// a reel -> Hoola Reels card; during a voice call the files go into the call; otherwise into the Chat box.
  Future<void> _onShare(Map<String, dynamic> share) async {
    for (var i = 0; i < 25 && navKey.currentContext == null; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 200));
    }
    final files = <Map<String, dynamic>>[];
    final skipped = (share['skipped'] as num? ?? 0).toInt();
    for (final raw in (share['files'] as List? ?? const [])) {
      final f = Map<String, dynamic>.from(raw as Map);
      if (f['big'] == true) {
        final ctx = navKey.currentContext;
        final path = f['path'] as String? ?? '';
        final name = f['name'] as String? ?? 'video.mp4';
        final small = (ctx == null || f['video'] != true) ? null : await shrinkVideo(ctx, path, name, sizeBytes: (f['size'] as num? ?? 0).toInt());
        try {
          await File(path).delete();          // the big copy is not needed any more
        } catch (_) {}
        if (small == null) continue;           // the reason (or "Rok do") was already shown
        f['path'] = small;
        f['name'] = name.replaceAll(RegExp(r'\.[A-Za-z0-9]+$'), '') + '.mp4';
        f['size'] = await File(small).length();
        f['big'] = false;
      }
      files.add(f);
    }
    share = {...share, 'files': files};
    if (share['assist'] is Map && (share['text'] as String? ?? '').trim().isEmpty) {
      // v0.62 long-press home: the screen the owner was on arrives as pending files; she adds what she wants
      share['text'] = files.isEmpty ? '' : 'Is screen ke baare mein madad karo: ';
    }
    final text = (share['text'] as String? ?? '').trim();
    if (files.isEmpty && text.isEmpty) return;
    // a reel (link from Instagram / YouTube / Facebook / Snapchat / Moj..., or one screen recording): the Reels card
    if (share['assist'] is! Map && HoolaReels.isReelShare(share)) {
      if (!await openReel(share)) widget.app.onShared(share);
      return;
    }
    final call = widget.app.voiceCall;
    if (call.inCall && files.isNotEmpty) {
      final list = <({String name, List<int> bytes})>[];
      for (final f in files) {
        try {
          list.add((name: f['name'] as String? ?? 'file', bytes: await File(f['path'] as String).readAsBytes()));
        } catch (_) {}
      }
      await call.attachFiles(list);         // Hoola sees them right in the call
      if (text.isNotEmpty) widget.app.onShared({'text': text, 'files': const [], 'skipped': skipped});
      return;
    }
    widget.app.onShared(share);
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
      if (t.startsWith('update:')) {
        // v0.62 Android's installer answered (success restarts the app, so this is mostly a failure or a cancel)
        try {
          final u = Map<String, dynamic>.from(jsonDecode(t.substring(7)) as Map);
          final ctx = navKey.currentContext;
          if (ctx != null && u['ok'] != true) {
            ScaffoldMessenger.maybeOf(ctx)?.showSnackBar(SnackBar(content: Text(
                u['status'] == 3 ? 'Update roka gaya.' : 'Update install nahi hua${'${u['message'] ?? ''}'.isEmpty ? '' : ': ${u['message']}'}')));
          }
        } catch (_) {}
        return;
      }
      if (t.startsWith('share:')) {
        try {
          await _onShare(Map<String, dynamic>.from(jsonDecode(t.substring(6)) as Map));
        } catch (_) {}
        return;
      }
      if (t == 'scroll:open') {        // a reel-limit / bedtime notification was tapped
        navKey.currentState?.push(MaterialPageRoute(builder: (_) => const ScrollScreen()));
        return;
      }
      if (t.startsWith('feedback:')) {  // v0.133 back from the Google Business Profile sign-in (Feedback Sahayak)
        navKey.currentState?.push(MaterialPageRoute(builder: (_) => FeedbackScreen(app: widget.app)));
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
      ScrollSync.maybe();   // reel-app times for the scroll report (only when Usage Access is on)
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
    // v0.69 Hoola closed by itself last time: send the reason to the server and say so (once)
    Future<void>.delayed(const Duration(seconds: 2), _crashReport);
    // v0.56 strict phones (Xiaomi / Oppo / Realme / Vivo...): the keep-alive checklist once, and again if the phone
    // has stopped Hoola since the last look; never during a call or the first setup
    Future<void>.delayed(const Duration(seconds: 8), () {
      if (mounted && widget.app.configured && !widget.app.needsAvatarSetup && !widget.app.voiceCall.inCall) {
        HoolaKeepAlive.maybePrompt(context, widget.app);
      }
    });
    // v0.62 a newer GitHub APK: one gentle sheet per version (checked at most once a day)
    Future<void>.delayed(const Duration(seconds: 20), () {
      if (mounted && widget.app.configured && !widget.app.voiceCall.inCall) AppUpdater.maybeOffer(context, widget.app);
    });
  }

  Future<void> _crashReport() async {
    final r = await Native.lastCrash();
    if (r == null || !mounted) return;
    try {
      await widget.app.api?.reportCrash(r);
    } catch (_) {}
    if (!mounted) return;
    final inCall = r['during_call'] == true;
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hoola pichhli baar band ho gaya tha'),
        content: Text(inCall
            ? 'Call ke dauraan app band ho gaya. Wajah server ko bhej di hai. Agli calls ab "surakshit mode" mein chalengi '
                '(thodi kam samajhdaar shor-pehchaan, par app band nahi hoga) jab tak naya update na aaye.'
            : 'Wajah server ko bhej di hai, taaki theek ho sake.'),
        actions: [
          TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: '${r['kind']}\n${r['text']}'));
              Navigator.pop(ctx);
            },
            child: const Text('Report copy karo'),
          ),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Theek hai')),
        ],
      ),
    );
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
