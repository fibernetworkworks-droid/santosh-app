import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'live_santosh.dart';

/// Drives the 3D Santosh (assets/santosh3d) from Dart: mood, talking, mic level, listening pose.
class Santosh3DController {
  WebViewController? _web;
  bool ready = false;
  String _mood = 'idle';
  bool _talk = false;
  bool _listen = false;

  void _js(String code) {
    if (ready) _web?.runJavaScript('window.santosh && $code').catchError((_) {});
  }

  void mood(String m) {
    if (m == _mood) return;
    _mood = m;
    _js("santosh.mood('$m')");
  }

  void talk(bool on) {
    if (on == _talk) return;
    _talk = on;
    _js('santosh.talk($on)');
  }

  void listen(bool on) {
    if (on == _listen) return;
    _listen = on;
    _js('santosh.listen($on)');
  }

  /// 0..1 mouth/lean level (mic volume while listening, speech energy while talking).
  void level(double v) => _js('santosh.level(${v.clamp(0, 1).toStringAsFixed(2)})');

  void _restore() {
    _js("santosh.mood('$_mood')");
    _js('santosh.talk($_talk)');
    _js('santosh.listen($_listen)');
  }
}

class Santosh3D extends StatefulWidget {
  const Santosh3D({super.key, required this.controller, this.fallbackMood = 'happy'});
  final Santosh3DController controller;
  final String fallbackMood;
  @override
  State<Santosh3D> createState() => _Santosh3DState();
}

class _Santosh3DState extends State<Santosh3D> {
  late final WebViewController _web;
  bool _ready = false;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..addJavaScriptChannel('SantoshBridge', onMessageReceived: (m) {
        if (!mounted) return;
        if (m.message == 'ready') {
          widget.controller.ready = true;
          widget.controller._restore();
          setState(() => _ready = true);
        } else if (m.message == 'nogl') {
          setState(() => _failed = true);
        }
      })
      ..setNavigationDelegate(NavigationDelegate(onWebResourceError: (_) {
        if (mounted && !_ready) setState(() => _failed = true);
      }))
      ..loadFlutterAsset('assets/santosh3d/index.html');
    widget.controller._web = _web;
  }

  @override
  void dispose() {
    widget.controller.ready = false;
    widget.controller._web = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Stack(fit: StackFit.expand, children: [
        if (!_failed)
          AnimatedOpacity(
            opacity: _ready ? 1 : 0,
            duration: const Duration(milliseconds: 500),
            child: WebViewWidget(controller: _web),
          ),
        if (!_ready || _failed)
          Center(child: LiveSantosh(mood: widget.fallbackMood, size: 260)),
      ]);
}
