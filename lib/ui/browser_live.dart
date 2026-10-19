import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// Santosh Browser, watched live: the page Santosh's browser is on, refreshed about twice a second while it works,
/// with what it is doing right now ("Fees wale link par click…"). Stop any time.
class BrowserLive {
  static bool running(String? s) => s == 'running' || s == 'starting';

  static String label(Map<String, dynamic> v) => switch (v['status'] as String? ?? 'running') {
        'running' || 'starting' => 'LIVE',
        'done' => 'HO GAYA',
        'partial' => 'ADHURA',
        'needs_confirm' => 'MANZOORI',
        'needs_payment' => 'PAYMENT AAP',
        'needs_user' => 'AAPKA STEP',
        'cancelled' => 'ROKA',
        'blocked' => 'BLOCKED',
        _ => 'NAHI HUA',
      };

  static Color color(Map<String, dynamic> v) => switch (v['status'] as String? ?? 'running') {
        'running' || 'starting' => const Color(0xFFDC2626),
        'done' => C.ok,
        'needs_confirm' || 'needs_payment' || 'needs_user' || 'partial' => C.warn,
        _ => C.bad,
      };

  static void open(BuildContext context, Santosh app, Map<String, dynamic> v) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => BrowserLiveScreen(app: app, initial: v)));
  }
}

/// Polls the live state + frame of one browser task while it's on screen.
class _LiveFeed extends StatefulWidget {
  const _LiveFeed({super.key, required this.app, required this.v, required this.builder});
  final Santosh app;
  final Map<String, dynamic> v;
  final Widget Function(BuildContext context, Uint8List? frame, Map<String, dynamic> live) builder;
  @override
  State<_LiveFeed> createState() => _LiveFeedState();
}

class _LiveFeedState extends State<_LiveFeed> {
  Timer? _t;
  Uint8List? _frame;
  int _seq = -1;
  bool _busy = false;
  late Map<String, dynamic> _live = Map<String, dynamic>.from(widget.v);

  String get _sid => widget.v['session_id'] as String? ?? '';

  @override
  void initState() {
    super.initState();
    _poll();
    _t = Timer.periodic(const Duration(milliseconds: 650), (_) => _poll());
  }

  @override
  void didUpdateWidget(covariant _LiveFeed old) {
    super.didUpdateWidget(old);
    // a newer event (e.g. done) arrived: take its status/summary and grab the last frame once more
    if (old.v['status'] != widget.v['status']) {
      _live = {..._live, ...widget.v};
      if (!BrowserLive.running(widget.v['status'] as String?)) _poll(force: true);
    }
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _poll({bool force = false}) async {
    final api = widget.app.api;
    if (_busy || api == null || _sid.isEmpty) return;
    if (!force && !BrowserLive.running(_live['status'] as String?) && _frame != null) {
      _t?.cancel();
      return;
    }
    _busy = true;
    try {
      final l = await api.browserLive(_sid);
      final seq = (l['seq'] as num?)?.toInt() ?? 0;
      Uint8List? img;
      if (seq != _seq || _frame == null) {
        final b = await api.browserFrame(_sid);
        if (b != null) img = Uint8List.fromList(b);
      }
      if (!mounted) return;
      setState(() {
        _live = {..._live, ...l};
        if (img != null) {
          _frame = img;
          _seq = seq;
        }
      });
    } catch (_) {
      // task gone (worker restarted / old card): keep what we have and stop asking
      if (!BrowserLive.running(widget.v['status'] as String?)) _t?.cancel();
    } finally {
      _busy = false;
    }
  }

  @override
  Widget build(BuildContext context) => widget.builder(context, _frame, _live);
}

Widget _frameBox(Uint8List? frame, {BoxFit fit = BoxFit.cover}) => frame == null
    ? Container(
        color: const Color(0xFF0E1220),
        alignment: Alignment.center,
        child: const Column(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.accent)),
          SizedBox(height: 8),
          Text('Browser khul raha hai…', style: TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      )
    : Image.memory(frame, gaplessPlayback: true, fit: fit, alignment: Alignment.topCenter, filterQuality: FilterQuality.medium);

/// Chat card: live thumbnail of the page + what Santosh is doing.
class BrowserLiveCard extends StatelessWidget {
  const BrowserLiveCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: _LiveFeed(
        app: app,
        v: v,
        builder: (context, frame, l) {
          final run = BrowserLive.running(l['status'] as String?);
          final site = (l['site'] as String?)?.isNotEmpty == true ? l['site'] as String : _host(l['url'] as String? ?? '');
          final action = (l['action'] as String? ?? '').trim();
          final summary = (l['summary'] as String? ?? '').trim();
          return Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                const Icon(Icons.travel_explore_rounded, color: C.accent, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(site.isEmpty ? 'Santosh Browser' : 'Santosh Browser · $site',
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                ),
                Pill(run ? '● ${BrowserLive.label(l)}' : BrowserLive.label(l), fg: Colors.white, bg: BrowserLive.color(l).withOpacity(.85)),
              ]),
              const SizedBox(height: 8),
              GestureDetector(
                onTap: () => BrowserLive.open(context, app, {...v, ...l}),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: AspectRatio(aspectRatio: 1280 / 860, child: _frameBox(frame)),
                ),
              ),
              const SizedBox(height: 8),
              if (run) ...[
                for (final st in _lastSteps(l, 2))
                  Text('✓ ${st['action']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 11.5)),
                Text(action.isEmpty ? 'Page padh raha hoon…' : '▶ $action',
                    maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.warn, fontSize: 12.5, fontWeight: FontWeight.w600)),
              ]
              else if (summary.isNotEmpty)
                Text(summary, maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: Color(0xFFD7D2F2))),
              const SizedBox(height: 4),
              Row(children: [
                TextButton.icon(
                  onPressed: () => BrowserLive.open(context, app, {...v, ...l}),
                  icon: const Icon(Icons.fullscreen_rounded, size: 18),
                  label: const Text('Bada dekho'),
                ),
                const Spacer(),
                if (run)
                  TextButton.icon(
                    onPressed: () => _stop(context, app, v['session_id'] as String? ?? ''),
                    icon: const Icon(Icons.stop_circle_outlined, size: 18, color: C.bad),
                    label: const Text('Rok do', style: TextStyle(color: C.bad)),
                  ),
              ]),
            ]),
          );
        },
      ),
    );
  }
}

Future<void> _stop(BuildContext context, Santosh app, String sid) async {
  try {
    await app.api?.browserStop(sid);
  } catch (_) {}
  if (context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Browser rok diya')));
  }
}

List<Map<String, dynamic>> _lastSteps(Map<String, dynamic> l, int n) {
  final t = (l['timeline'] as List?) ?? const [];
  final all = t.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
  return all.length <= n ? all : all.sublist(all.length - n);
}

/// Every step Santosh took on the web: what it did and on which page (newest at the bottom).
class _Timeline extends StatelessWidget {
  const _Timeline({required this.steps, required this.running});
  final List<Map<String, dynamic>> steps;
  final bool running;

  @override
  Widget build(BuildContext context) {
    if (steps.isEmpty) {
      return const Center(child: Text('Steps yahan dikhenge…', style: TextStyle(color: C.faint, fontSize: 12.5)));
    }
    return ListView.builder(
      reverse: true,
      padding: const EdgeInsets.fromLTRB(14, 6, 14, 6),
      itemCount: steps.length,
      itemBuilder: (context, i) {
        final st = steps[steps.length - 1 - i];
        final last = i == 0 && running;
        final host = _host(st['url'] as String? ?? '');
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 22,
              height: 22,
              alignment: Alignment.center,
              decoration: BoxDecoration(color: last ? C.accent : const Color(0x22FFFFFF), shape: BoxShape.circle),
              child: Text('${st['step'] ?? ''}', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: last ? C.onAccent : C.chip)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(st['action'] as String? ?? '', style: TextStyle(fontSize: 13, height: 1.3, color: last ? C.ink : const Color(0xFFD7D2F2))),
                if (host.isNotEmpty || (st['do'] as String? ?? '').isNotEmpty)
                  Text([if ((st['do'] as String? ?? '').isNotEmpty) st['do'], if (host.isNotEmpty) host].join(' · '),
                      style: const TextStyle(fontSize: 11, color: C.faint)),
              ]),
            ),
          ]),
        );
      },
    );
  }
}

String _host(String url) {
  final h = Uri.tryParse(url)?.host ?? '';
  return h.startsWith('www.') ? h.substring(4) : h;
}

/// Full screen: watch the page large (pinch to zoom), see each step, stop.
class BrowserLiveScreen extends StatelessWidget {
  const BrowserLiveScreen({super.key, required this.app, required this.initial});
  final Santosh app;
  final Map<String, dynamic> initial;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final sid = initial['session_id'] as String? ?? '';
        final cur = app.browserItem(sid)?.data ?? initial;
        return Scaffold(
          backgroundColor: const Color(0xFF070912),
          appBar: AppBar(
            backgroundColor: const Color(0xFF0E1220),
            title: const Text('Santosh Browser · live'),
          ),
          body: _LiveFeed(
            app: app,
            v: {...initial, ...cur},
            builder: (context, frame, l) {
              final run = BrowserLive.running(l['status'] as String?);
              final action = (l['action'] as String? ?? '').trim();
              final summary = (l['summary'] as String? ?? '').trim();
              final url = l['url'] as String? ?? '';
              return Column(children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
                  color: const Color(0xFF111628),
                  child: Row(children: [
                    const Icon(Icons.lock_outline_rounded, size: 14, color: C.muted),
                    const SizedBox(width: 6),
                    Expanded(child: Text(url.isEmpty ? '…' : url, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12))),
                    const SizedBox(width: 8),
                    Pill(run ? '● ${BrowserLive.label(l)}' : BrowserLive.label(l), fg: Colors.white, bg: BrowserLive.color(l).withOpacity(.85)),
                  ]),
                ),
                Expanded(
                  flex: 5,
                  child: InteractiveViewer(
                    minScale: 1,
                    maxScale: 4,
                    child: Center(child: AspectRatio(aspectRatio: 1280 / 860, child: _frameBox(frame, fit: BoxFit.contain))),
                  ),
                ),
                Expanded(
                  flex: 3,
                  child: _Timeline(steps: _lastSteps(l, 60), running: run),
                ),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  color: const Color(0xFF0E1220),
                  child: SafeArea(
                    top: false,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                      Text(run ? 'Abhi kya kar raha hoon · step ${l['step'] ?? 0}' : 'Nateeja',
                          style: const TextStyle(color: C.faint, fontSize: 12, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 4),
                      Text(run ? (action.isEmpty ? 'Page padh raha hoon…' : action) : (summary.isEmpty ? BrowserLive.label(l) : summary),
                          maxLines: 6, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14.5, height: 1.35)),
                      if (run) ...[
                        const SizedBox(height: 10),
                        Row(children: [
                          const Expanded(
                            child: Text('Password, OTP aur payment Santosh kabhi nahi bharta. Submit se pehle aapse poochega.',
                                style: TextStyle(color: C.muted, fontSize: 11.5)),
                          ),
                          FilledButton.tonalIcon(
                            onPressed: () => _stop(context, app, sid),
                            icon: const Icon(Icons.stop_rounded),
                            label: const Text('Rok do'),
                          ),
                        ]),
                      ],
                    ]),
                  ),
                ),
              ]);
            },
          ),
        );
      },
    );
  }
}

/// On the voice call screen: a small live thumbnail while the browser works; tap to watch big.
class BrowserCallThumb extends StatelessWidget {
  const BrowserCallThumb({super.key, required this.app});
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final v = app.latestBrowser;
        if (v == null || app.lockedMode) return const SizedBox.shrink();
        final sid = v['session_id'] as String? ?? '';
        final cur = app.browserItem(sid)?.data ?? v;
        if (!BrowserLive.running(cur['status'] as String?)) return const SizedBox.shrink();
        return _LiveFeed(
          key: ValueKey(sid),
          app: app,
          v: cur,
          builder: (context, frame, l) => GestureDetector(
            onTap: () => BrowserLive.open(context, app, {...cur, ...l}),
            child: Container(
              width: 132,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0x55FFFFFF)),
                boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 12)],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(11),
                child: Stack(children: [
                  AspectRatio(aspectRatio: 1280 / 860, child: _frameBox(frame)),
                  Positioned(
                    left: 4,
                    top: 4,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(color: const Color(0xDDDC2626), borderRadius: BorderRadius.circular(6)),
                      child: const Text('● LIVE', style: TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800)),
                    ),
                  ),
                ]),
              ),
            ),
          ),
        );
      },
    );
  }
}
