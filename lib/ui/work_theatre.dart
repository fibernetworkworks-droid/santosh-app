import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../state.dart';
import 'avatar_look.dart';
import 'glass.dart';
import 'live_santosh.dart';

/// Hoola Work Theatre: the 3D scene (assets/theatre) of the tool Hoola is running, driven by the server's
/// `work` events. Every scene is built around the Hoola avatar; screens inside the scene show the real facts of
/// the call (senders, site, biller and amount, TV, the other avatar, the PC app).
class TheatreController {
  WebViewController? _web;
  bool ready = false;
  Map<String, dynamic>? _last;
  bool _paused = false;

  void _js(String code) {
    if (ready) _web?.runJavaScript('window.theatre && $code').catchError((_) {});
  }

  void set(Map<String, dynamic>? ev) {
    if (ev == null) return;
    _last = ev;
    _js('theatre.set(${jsonEncode(ev)})');
  }

  void pause(bool on) {
    if (on == _paused) return;
    _paused = on;
    _js('theatre.pause($on)');
  }

  /// v0.48: the owner's avatar look ('' = Santosh, f001..f100) inside every scene.
  void look(String id) => _js('theatre.look(${jsonEncode(isLook(id) ? id : '')})');

  void _restore() {
    look(currentLook.value);
    if (_last != null) _js('theatre.set(${jsonEncode(_last)})');
    _js('theatre.pause($_paused)');
  }
}

class WorkTheatre extends StatefulWidget {
  const WorkTheatre({super.key, required this.controller});
  final TheatreController controller;
  @override
  State<WorkTheatre> createState() => _WorkTheatreState();
}

class _WorkTheatreState extends State<WorkTheatre> {
  late final WebViewController _web;
  bool _ready = false;
  bool _failed = false;
  void _onLook() => widget.controller.look(currentLook.value);

  @override
  void initState() {
    super.initState();
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..addJavaScriptChannel('TheatreBridge', onMessageReceived: (m) {
        if (!mounted) return;
        if (m.message == 'ready') {
          widget.controller.ready = true;
          widget.controller._restore();
          setState(() => _ready = true);
        } else if (m.message == 'nogl') {
          setState(() => _failed = true);
        }
      })
      ..setNavigationDelegate(NavigationDelegate(onWebResourceError: (e) {
        // fonts are optional; only a failed page load means no theatre
        if (mounted && !_ready && (e.isForMainFrame ?? false)) setState(() => _failed = true);
      }))
      ..loadFlutterAsset('assets/theatre/index.html');
    widget.controller._web = _web;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    currentLook.removeListener(_onLook);
    currentLook.addListener(_onLook);
  }

  @override
  void dispose() {
    currentLook.removeListener(_onLook);
    widget.controller.ready = false;
    widget.controller._web = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Stack(fit: StackFit.expand, children: [
        if (!_failed)
          AnimatedOpacity(opacity: _ready ? 1 : 0, duration: const Duration(milliseconds: 400), child: WebViewWidget(controller: _web)),
        if (!_ready || _failed) const Center(child: LiveSantosh(size: 150)),
      ]);
}

const _sceneName = {
  'email': 'Email', 'browser': 'Hoola ka browser', 'payment': 'Bill / Payment', 'bluetooth': 'Bluetooth',
  'network': 'Hoola Network', 'pc': 'Aapka PC', 'work': 'Kaam',
};
const _sceneColor = {
  'email': Color(0xFF8B6DFF), 'browser': Color(0xFF14B8A6), 'payment': Color(0xFFFF9A3C), 'bluetooth': Color(0xFF3B82F6),
  'network': Color(0xFF7C5CFF), 'pc': Color(0xFFC026D3), 'work': Color(0xFFFF9A3C),
};

String _detail(Map<String, dynamic> w) {
  final d = Map<String, dynamic>.from(w['data'] as Map? ?? const {});
  final v = d['account'] ?? d['url'] ?? d['biller'] ?? d['device'] ?? d['peer'] ?? d['app'];
  return v is String && v.isNotEmpty ? v : '';
}

/// The panel above the chat: live 3D stage, what is running, Rokiye (stop), minimise.
class WorkTheatrePanel extends StatefulWidget {
  const WorkTheatrePanel({super.key, required this.app});
  final Santosh app;
  @override
  State<WorkTheatrePanel> createState() => _WorkTheatrePanelState();
}

class _WorkTheatrePanelState extends State<WorkTheatrePanel> {
  final _ctl = TheatreController();
  bool _created = false;
  bool _stopping = false;
  Object? _sent;

  Santosh get app => widget.app;

  @override
  Widget build(BuildContext context) {
    final w = app.work;
    final visible = w != null;
    if (visible) _created = true;
    final open = visible && !app.workMin;
    if (w != null && !identical(w, _sent)) {
      _sent = w;
      _ctl.set(w);
      if (w['phase'] == 'start') _stopping = false;
    }
    _ctl.pause(!open);
    if (!_created) return const SizedBox.shrink();
    final scene = w?['scene'] as String? ?? 'work';
    final phase = w?['phase'] as String? ?? 'start';
    final col = _sceneColor[scene] ?? C.accent;
    final status = switch (phase) {
      'done' => 'Ho gaya',
      'error' => 'Nahi ho paya',
      'waiting' => 'Aapka intezaar',
      'stopped' => 'Roka gaya',
      _ => 'Kaam chal raha hai',
    };
    final statusColor = switch (phase) { 'done' => C.ok, 'error' => C.bad, 'stopped' => C.faint, _ => C.accentSoft };
    final detail = w == null ? '' : _detail(w);
    return Offstage(
      offstage: !visible,
      child: Glass(
              margin: const EdgeInsets.fromLTRB(14, 0, 14, 6),
              padding: EdgeInsets.zero,
              radius: 22,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Offstage(
                  offstage: !open,
                  child: SizedBox(
                    height: 250,
                    child: ClipRRect(
                      borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
                      child: Stack(children: [
                        Positioned.fill(child: WorkTheatre(controller: _ctl)),
                        Positioned(
                          left: 10, top: 10,
                          child: Wrap(spacing: 6, children: [
                            _chip('LIVE 3D', const Color(0x29FFB15C), C.accentSoft),
                            _chip(_sceneName[scene] ?? 'Kaam', col, Colors.white),
                          ]),
                        ),
                      ]),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
                  child: Row(children: [
                    if (!open)
                      Container(width: 10, height: 10, margin: const EdgeInsets.only(right: 8),
                          decoration: BoxDecoration(color: col, shape: BoxShape.circle)),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(w?['label'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                        Text(detail.isEmpty ? status : '$status · $detail', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: statusColor)),
                      ]),
                    ),
                    IconButton(
                      tooltip: open ? 'Chhota kijiye' : 'Bada kijiye',
                      onPressed: app.toggleWorkMin,
                      icon: Icon(open ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: C.muted),
                    ),
                    if (phase == 'start')
                      TextButton.icon(
                        onPressed: _stopping
                            ? null
                            : () async {
                                setState(() => _stopping = true);
                                await app.stopWork();
                              },
                        style: TextButton.styleFrom(foregroundColor: const Color(0xFFFCA5A5), minimumSize: const Size(44, 44)),
                        icon: const Icon(Icons.stop_rounded, size: 18),
                        label: Text(_stopping ? 'Rok raha…' : 'Rokiye', style: const TextStyle(fontWeight: FontWeight.w800)),
                      )
                    else
                      IconButton(tooltip: 'Band kijiye', onPressed: app.closeWork, icon: const Icon(Icons.close_rounded, color: C.muted)),
                  ]),
                ),
                if (open && app.workLog.length > 1)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                    child: Column(children: [
                      for (final s in app.workLog.reversed.skip(1).take(3))
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Row(children: [
                            Icon(
                              s['phase'] == 'error' ? Icons.error_outline_rounded : s['phase'] == 'start' ? Icons.more_horiz_rounded : Icons.check_circle_rounded,
                              size: 15,
                              color: s['phase'] == 'error' ? C.bad : s['phase'] == 'start' ? C.faint : C.ok,
                            ),
                            const SizedBox(width: 8),
                            Expanded(child: Text(s['label'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12, color: C.faint))),
                          ]),
                        ),
                    ]),
                  ),
              ]),
            ),
    );
  }

  Widget _chip(String t, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(10)),
        child: Text(t, style: TextStyle(color: fg, fontSize: 10.5, fontWeight: FontWeight.w800)),
      );
}
