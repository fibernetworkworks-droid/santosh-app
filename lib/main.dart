import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'device.dart';
import 'nav.dart';
import 'state.dart';
import 'ui/chat_screen.dart';
import 'ui/glass.dart';
import 'ui/profile_screen.dart';
import 'ui/setup_screen.dart';
import 'ui/today_screen.dart';
import 'ui/live_voice_screen.dart';
import 'ui/voice_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Device.instance.init();
  final app = await Santosh.load();
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
    _setup = !widget.app.configured;
    if (!_setup) widget.app.connect();
    _listenForSignIn();
  }

  void _listenForSignIn() {
    // the native side sends the session token from santosh://auth?session=<token>
    _linkSub = _linkCh.receiveBroadcastStream().listen((token) async {
      final t = token?.toString() ?? '';
      if (t.isEmpty) return;
      if (t.startsWith('bazar:')) {
        widget.app.onBazarLinked(t.endsWith('=1'));
        return;
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
    if (s == AppLifecycleState.resumed && widget.app.configured) {
      widget.app.refreshReminders();
      widget.app.refreshLists();
      widget.app.refreshRoutines();
      widget.app.refreshBackgroundInfo();
    }
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        navigatorKey: navKey,
        title: 'Santosh',
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

  @override
  Widget build(BuildContext context) {
    final pages = [
      ChatScreen(app: widget.app, onVoice: () => setState(() => _tab = 1)),
      // built only while open: the 3D view and the microphone stop when you leave the tab
      _tab == 1
          ? ListenableBuilder(
              listenable: widget.app,
              // live human-like call when the server has realtime voice, otherwise the phone's own speech
              builder: (context, _) => widget.app.realtimeVoice ? LiveVoiceScreen(app: widget.app) : VoiceScreen(app: widget.app),
            )
          : const SizedBox.shrink(),
      TodayScreen(app: widget.app),
      ProfileScreen(app: widget.app, onReset: widget.onReset),
    ];
    return Scaffold(
      body: Aurora(child: SafeArea(bottom: false, child: IndexedStack(index: _tab, children: pages))),
      bottomNavigationBar: SafeArea(
        child: Glass(
          margin: const EdgeInsets.fromLTRB(22, 0, 22, 10),
          padding: const EdgeInsets.symmetric(vertical: 4),
          radius: 26,
          child: NavigationBar(
            height: 62,
            backgroundColor: Colors.transparent,
            elevation: 0,
            indicatorColor: const Color(0x226D3FE0),
            selectedIndex: _tab,
            onDestinationSelected: (i) => setState(() => _tab = i),
            destinations: const [
              NavigationDestination(icon: Icon(Icons.chat_bubble_outline_rounded), selectedIcon: Icon(Icons.chat_bubble_rounded, color: C.accent), label: 'Chat'),
              NavigationDestination(icon: Icon(Icons.graphic_eq_rounded), selectedIcon: Icon(Icons.graphic_eq_rounded, color: C.accent), label: 'Baat'),
              NavigationDestination(icon: Icon(Icons.event_note_outlined), selectedIcon: Icon(Icons.event_note_rounded, color: C.accent), label: 'Aaj'),
              NavigationDestination(icon: Icon(Icons.person_outline_rounded), selectedIcon: Icon(Icons.person_rounded, color: C.accent), label: 'Profile'),
            ],
          ),
        ),
      ),
    );
  }
}
