// v0.912 CREATE NATIVE (owner: "NOW LETS WORK ON CREATE IN TOOL SECTION ... MAKE A REAL APP NATIVE SCREENS FOR ALL
// PREMIUM, ADVANCE, USER-FRIENDLY AND PROFESSIONAL" -> design canvas claude.ai/artifact/SARfWkfWm8ZtmmnAcU8dYn ->
// "GO BUILD"): the shared parts of the 13 Create screens - one store that talks to the same routes the console's
// Create studio uses (/api/create, /api/create/jobs, /api/create/items, /api/create/write, /api/studio, /api/brand/kit),
// the Create icons (own vector drawings on the house 24-unit grid) and the building blocks every screen is made of:
// the top bar, soft cards, section labels, chips, segmented controls, setting rows with a picker sheet, the stepper,
// the pinned bottom bar with its price, job rows (working / failed) and a small audio player.
// Nothing here spends money: paid work goes through the server's price card and her Haan, as on the console.
import 'dart:async';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:video_player/video_player.dart';

import '../../native.dart';
import '../../state.dart';
import '../hoola_theme.dart';
import '../shell/hoola_tool_icons.dart' show svgPath;

// ------------------------------------------------------------------------------------------------ the store
/// Everything the Create screens read and start. One per Create visit; screens listen to it.
class CreateStore extends ChangeNotifier {
  CreateStore(this.app);
  final Santosh app;

  Map<String, dynamic> conf = const {};          // GET /api/create: ready, voices, styles, languages
  Map<String, dynamic> studio = const {};        // GET /api/studio: films, models, month spend
  Map<String, dynamic> kit = const {};           // GET /api/brand/kit
  List<Map<String, dynamic>> items = const [];   // GET /api/create/items: her shelf, newest first
  final Map<String, Map<String, dynamic>> jobs = {};   // jobs started or seen this visit, by id
  final Set<String> dismissed = {};
  bool loading = false;
  String error = '';
  Timer? _poll;
  bool _disposed = false;

  /// Test seam: the store's data without a server (screens_test, create_native_test).
  static Map<String, dynamic>? debugData;

  Future<void> load({bool quiet = false}) async {
    final d = debugData;
    if (d != null) {
      conf = _m(d['conf']);
      studio = _m(d['studio']);
      kit = _m(d['kit']);
      items = _list(d['items']);
      for (final j in _list(d['jobs'])) {
        jobs['${j['id']}'] = j;
      }
      _tell();
      return;
    }
    final api = app.api;
    if (api == null) {
      error = 'Not connected to the server right now';
      _tell();
      return;
    }
    if (!quiet) {
      loading = true;
      _tell();
    }
    final res = await Future.wait<Object?>([
      _try(() => api.call('GET', '/api/create')),
      _try(() => api.call('GET', '/api/create/items')),
      _try(() => api.call('GET', '/api/create/jobs')),
      _try(() => api.call('GET', '/api/studio')),
      _try(() => api.call('GET', '/api/brand/kit')),
    ]);
    if (res[0] is Map) conf = _m(res[0]);
    if (res[1] is Map) items = _list((res[1] as Map)['items']);
    if (res[2] is Map) {
      for (final j in _list((res[2] as Map)['jobs'])) {
        jobs['${j['id']}'] = j;
      }
    }
    if (res[3] is Map) studio = _m(res[3]);
    if (res[4] is Map) kit = _m(res[4]);
    error = res.every((r) => r == null) ? 'The server did not answer. Pull down to try again.' : '';
    loading = false;
    _tell();
    _keepPolling();
  }

  Future<Object?> _try(Future<dynamic> Function() f) async {
    try {
      return await f();
    } catch (_) {
      return null;
    }
  }

  Future<void> reloadItems() async {
    final api = app.api;
    if (api == null || debugData != null) return;
    try {
      items = _list(((await api.call('GET', '/api/create/items')) as Map)['items']);
      _tell();
    } catch (_) {}
  }

  Future<void> reloadStudio() async {
    final api = app.api;
    if (api == null || debugData != null) return;
    try {
      studio = _m(await api.call('GET', '/api/studio'));
      _tell();
    } catch (_) {}
  }

  /// Starts one Create job (image / cast / song / voice / dub). Its result also arrives in her open chat as a card.
  Future<Map<String, dynamic>> start(Map<String, dynamic> body) async {
    final api = app.api;
    if (api == null) throw Exception('Not connected to the server right now');
    final j = _m(await api.call('POST', '/api/create/jobs', body: {...body, 'conversation_id': app.conversationId ?? ''}));
    jobs['${j['id']}'] = j;
    _tell();
    _keepPolling();
    return j;
  }

  /// Writes a script or lyrics (the words come back here; a script is also kept on her shelf).
  Future<Map<String, dynamic>> write(Map<String, dynamic> body) async {
    final api = app.api;
    if (api == null) throw Exception('Not connected to the server right now');
    final r = _m(await api.call('POST', '/api/create/write', body: body, timeout: const Duration(seconds: 150)));
    if (r['item'] is Map) unawaited(reloadItems());
    return r;
  }

  Future<void> delete(String id) async {
    final api = app.api;
    if (api == null) return;
    await api.call('DELETE', '/api/create/items/${Uri.encodeComponent(id)}');
    items = items.where((i) => i['id'] != id).toList();
    _tell();
  }

  Future<Map<String, dynamic>> saveKit(Map<String, dynamic> body) async {
    final api = app.api;
    if (api == null) throw Exception('Not connected to the server right now');
    kit = _m(await api.call('PUT', '/api/brand/kit', body: body));
    _tell();
    return kit;
  }

  void dismiss(String jobId) {
    dismissed.add(jobId);
    _tell();
  }

  List<Map<String, dynamic>> running(String kind) =>
      jobs.values.where((j) => j['kind'] == kind && j['status'] == 'running').toList();
  List<Map<String, dynamic>> failed(String kind) =>
      jobs.values.where((j) => j['kind'] == kind && j['status'] == 'failed' && !dismissed.contains('${j['id']}')).toList();
  List<Map<String, dynamic>> shelf(String kind) => items.where((i) => i['kind'] == kind).toList();
  List<Map<String, dynamic>> get films => _list(studio['projects']);

  void _keepPolling() {
    if (_poll != null || _disposed) return;
    if (!jobs.values.any((j) => j['status'] == 'running')) return;
    _poll = Timer.periodic(const Duration(milliseconds: 2500), (_) => _tick());
  }

  Future<void> _tick() async {
    final api = app.api;
    final live = jobs.values.where((j) => j['status'] == 'running').toList();
    if (api == null || live.isEmpty || _disposed) {
      _poll?.cancel();
      _poll = null;
      return;
    }
    var finished = false;
    for (final j in live) {
      try {
        final x = _m(await api.call('GET', '/api/create/jobs/${Uri.encodeComponent('${j['id']}')}'));
        jobs['${j['id']}'] = x;
        if (x['status'] != 'running') finished = true;
      } catch (_) {
        jobs['${j['id']}'] = {...j, 'status': 'failed', 'error': 'This job was lost (the server restarted). Start it again.'};
        finished = true;
      }
    }
    if (finished) await reloadItems();
    _tell();
  }

  void _tell() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _poll?.cancel();
    super.dispose();
  }
}

Map<String, dynamic> _m(Object? v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(Object? v) =>
    v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : <Map<String, dynamic>>[];
Map<String, dynamic> crMap(Object? v) => _m(v);
List<Map<String, dynamic>> crList(Object? v) => _list(v);
String crS(Object? v) => v == null ? '' : '$v';
int crInt(Object? v) => v is num ? v.round() : int.tryParse('$v') ?? 0;

/// A plain line from any error (server detail when there is one).
String crError(Object e) {
  final s = '$e';
  return s.startsWith('Exception: ') ? s.substring(11) : s.replaceFirst(RegExp(r'^ApiException\(\d+\):\s*'), '');
}

String crRupees(num v) => '₹${v >= 100 ? v.round() : (v == v.roundToDouble() ? v.round() : v.toStringAsFixed(1))}';

String crWhen(Object? epochSeconds) {
  final s = crInt(epochSeconds);
  if (s == 0) return '';
  final t = DateTime.fromMillisecondsSinceEpoch(s * 1000);
  final now = DateTime.now();
  final d = DateTime(now.year, now.month, now.day).difference(DateTime(t.year, t.month, t.day)).inDays;
  if (d == 0) return 'Today';
  if (d == 1) return 'Yesterday';
  const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return '${t.day} ${m[t.month - 1]}';
}

void crToast(BuildContext context, String text) {
  ScaffoldMessenger.maybeOf(context)
    ?..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(text), behavior: SnackBarBehavior.floating, duration: const Duration(seconds: 3)));
}

// ------------------------------------------------------------------------------------------------ icons
/// The Create drawings (the same strokes as the design canvas): one 24-unit grid, a 1.7 stroke, round ends.
enum CrGlyph { film, video, image, music, voice, dub, cut, pen, cast, cinema, folder, brand, grid, book, spark, wand, play, down,
  share, plus, minus, check, back, chevron, search, shield, info, mic, trash, refresh, camera, globe, clock, people, layers }

const Map<CrGlyph, String> _crArt = {
  CrGlyph.film: 'M4 10h16v9H4zM4 10l1.5-4.5h14L18 10M9.5 5.5L8 10M14.5 5.5L13 10',
  CrGlyph.video: 'M3 7h12v10H3zM15 10.5l6-3.5v10l-6-3.5',
  CrGlyph.image: 'M4 5h16v14H4zM4 15l4.5-4.5 4 4 3-3L20 15M15.5 9h.01',
  CrGlyph.music: 'M9 18V6l11-2v12M9 18a3 3 0 1 1-6 0a3 3 0 1 1 6 0zM20 16a3 3 0 1 1-6 0a3 3 0 1 1 6 0z',
  CrGlyph.voice: 'M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3',
  CrGlyph.dub: 'M4 5h10v7H8.5L4 15zM10 15v1h5.5l4.5 3V9h-3',
  CrGlyph.cut: 'M6 9a3 3 0 1 0 0-6a3 3 0 1 0 0 6zM6 21a3 3 0 1 0 0-6a3 3 0 1 0 0 6zM8.2 7.8L20 18M8.2 16.2L20 6',
  CrGlyph.pen: 'M4 20l4-1 11-11-3-3L5 16zM14 6l3 3',
  CrGlyph.cast: 'M12 12a4 4 0 1 0 0-8a4 4 0 1 0 0 8zM4.5 20c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5',
  CrGlyph.cinema: 'M5 3h14v18H5zM9 3v18M15 3v18M5 7.5h4M5 12h4M5 16.5h4M15 7.5h4M15 12h4M15 16.5h4',
  CrGlyph.folder: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',
  CrGlyph.brand: 'M12 3l2.5 5.5L20 9l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.5z',
  CrGlyph.grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  CrGlyph.book: 'M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5M8 7h7',
  CrGlyph.spark: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z',
  CrGlyph.wand: 'M4 20L14 10M15 4v3M18.5 5.5l-2 2M20 9h-3',
  CrGlyph.play: 'M8 5v14l11-7z',
  CrGlyph.down: 'M12 4v11M7 10l5 5 5-5M5 20h14',
  CrGlyph.share: 'M12 15V4M8 8l4-4 4 4M5 13v6h14v-6',
  CrGlyph.plus: 'M12 5v14M5 12h14',
  CrGlyph.minus: 'M5 12h14',
  CrGlyph.check: 'M5 12l5 5 9-10',
  CrGlyph.back: 'M15 5l-7 7 7 7',
  CrGlyph.chevron: 'M9 5l7 7-7 7',
  CrGlyph.search: 'M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14zM20 20l-4-4',
  CrGlyph.shield: 'M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z',
  CrGlyph.info: 'M12 21a9 9 0 1 0 0-18a9 9 0 1 0 0 18zM12 11v5M12 8h.01',
  CrGlyph.mic: 'M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3',
  CrGlyph.trash: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13',
  CrGlyph.refresh: 'M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6',
  CrGlyph.camera: 'M3 7h4l2-3h6l2 3h4v12H3zM12 17a4 4 0 1 0 0-8a4 4 0 1 0 0 8z',
  CrGlyph.globe: 'M12 21a9 9 0 1 0 0-18a9 9 0 1 0 0 18zM3 12h18M12 3c2.5 2.5 3.5 5.5 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-5.5-3.5-9s1-6.5 3.5-9z',
  CrGlyph.clock: 'M12 21a9 9 0 1 0 0-18a9 9 0 1 0 0 18zM12 7v5l3 2',
  CrGlyph.people: 'M9 11.5a3.5 3.5 0 1 0 0-7a3.5 3.5 0 1 0 0 7zM3 20c1-3.5 3.3-5.5 6-5.5s5 2 6 5.5M16 4a3.5 3.5 0 0 1 0 7M18 14.5c1.5.8 2.5 2.6 3 5.5',
  CrGlyph.layers: 'M4 8l8-4 8 4-8 4zM4 12l8 4 8-4M4 16l8 4 8-4',
};
final Map<CrGlyph, Path> _crPaths = {};

class CrIcon extends StatelessWidget {
  const CrIcon(this.glyph, {super.key, this.size = 20, this.color, this.fill = false});
  final CrGlyph glyph;
  final double size;
  final Color? color;
  final bool fill;   // the play triangle reads better filled
  @override
  Widget build(BuildContext context) => CustomPaint(
        size: Size.square(size),
        painter: _CrIconPainter(_crPaths.putIfAbsent(glyph, () => svgPath(_crArt[glyph]!)),
            color ?? HoolaColors.of(context).ink, fill || glyph == CrGlyph.play),
      );
}

class _CrIconPainter extends CustomPainter {
  _CrIconPainter(this.path, this.color, this.fill);
  final Path path;
  final Color color;
  final bool fill;
  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 24, size.height / 24);
    canvas.drawPath(
        path,
        Paint()
          ..color = color
          ..style = fill ? PaintingStyle.fill : PaintingStyle.stroke
          ..strokeWidth = 1.7
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..isAntiAlias = true);
    canvas.restore();
  }

  @override
  bool shouldRepaint(_CrIconPainter o) => o.color != color || o.path != path || o.fill != fill;
}

/// The black circle every Create tool sits on.
class CrDisc extends StatelessWidget {
  const CrDisc(this.glyph, {super.key, this.size = 44});
  final CrGlyph glyph;
  final double size;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
      alignment: Alignment.center,
      child: CrIcon(glyph, size: size * .45, color: c.onPill),
    );
  }
}

/// The soft tiles behind a placeholder picture: four quiet tones from the theme, picked by a creation's id.
Color crTone(HoolaColors c, Object? seed) {
  final tones = [c.warnSoft, c.okSoft, c.accentSoft, c.infoSoft];
  return tones[('$seed'.codeUnits.fold<int>(0, (a, b) => a + b)) % tones.length];
}

// ------------------------------------------------------------------------------------------------ the page frame
/// A Create page: the round back button, a centred title, an optional right button, the scrolling body and, pinned at
/// the bottom over a soft fade, the main action (with its price).
class CrPage extends StatelessWidget {
  const CrPage({super.key, required this.title, required this.children, this.action, this.trailing, this.onRefresh});
  final String title;
  final List<Widget> children;
  final Widget? action;
  final Widget? trailing;
  final Future<void> Function()? onRefresh;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final bottom = MediaQuery.paddingOf(context).bottom;
    Widget list = ListView(
      padding: EdgeInsets.fromLTRB(HoolaSpace.s20, 4, HoolaSpace.s20, (action == null ? 32 : 120) + bottom),
      children: children,
    );
    if (onRefresh != null) list = RefreshIndicator(onRefresh: onRefresh!, child: list);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        bottom: false,
        child: Stack(children: [
          Column(children: [
            SizedBox(
              height: 60,
              child: Row(children: [
                const SizedBox(width: HoolaSpace.s12),
                SizedBox(
                  width: 88,
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: CrRoundButton(glyph: CrGlyph.back, label: 'Back', onTap: () => Navigator.of(context).maybePop()),
                  ),
                ),
                Expanded(
                  child: Semantics(
                    header: true,
                    child: Text(title, textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.title(c).copyWith(fontSize: 15.5)),
                  ),
                ),
                SizedBox(width: 88, child: Align(alignment: Alignment.centerRight, child: trailing)),
                const SizedBox(width: HoolaSpace.s12),
              ]),
            ),
            Expanded(child: list),
          ]),
          if (action != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: IgnorePointer(
                ignoring: false,
                child: Container(
                  padding: EdgeInsets.fromLTRB(HoolaSpace.s20, 24, HoolaSpace.s20, 14 + bottom),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [c.bg.withOpacity(0), c.bg, c.bg],
                      stops: const [0, .32, 1],
                    ),
                  ),
                  child: action,
                ),
              ),
            ),
        ]),
      ),
    );
  }
}

/// The 44 dp round outline button (back, saves, small actions); 48 dp of tap room.
class CrRoundButton extends StatelessWidget {
  const CrRoundButton({super.key, required this.glyph, required this.label, required this.onTap, this.size = 44});
  final CrGlyph glyph;
  final String label;
  final VoidCallback? onTap;
  final double size;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: label,
      child: SizedBox(
        width: size < 48 ? 48.0 : size,
        height: size < 48 ? 48.0 : size,
        child: Center(
          child: Material(
            color: c.surface,
            shape: CircleBorder(side: BorderSide(color: c.line)),
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: onTap == null
                  ? null
                  : () {
                      HapticFeedback.selectionClick();
                      onTap!();
                    },
              child: SizedBox(width: size, height: size, child: Center(child: CrIcon(glyph, size: 18, color: c.ink))),
            ),
          ),
        ),
      ),
    );
  }
}

/// The black pill (the main action). [busy] shows a small spinner and stops a second tap.
class CrMain extends StatelessWidget {
  const CrMain({super.key, required this.label, required this.onTap, this.busy = false, this.height = 56, this.glyph});
  final String label;
  final VoidCallback? onTap;
  final bool busy;
  final double height;
  final CrGlyph? glyph;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final on = onTap != null && !busy;
    return Semantics(
      button: true,
      enabled: on,
      label: label,
      excludeSemantics: true,
      onTap: on ? onTap : null,
      child: Material(
        color: on ? c.pill : c.pill.withOpacity(.45),
        borderRadius: BorderRadius.circular(height / 2),
        child: InkWell(
          borderRadius: BorderRadius.circular(height / 2),
          onTap: on
              ? () {
                  HapticFeedback.lightImpact();
                  onTap!();
                }
              : null,
          child: SizedBox(
            height: height,
            child: Center(
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                if (busy)
                  SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                else if (glyph != null)
                  CrIcon(glyph!, size: 18, color: c.onPill),
                if (busy || glyph != null) const SizedBox(width: 10),
                Flexible(
                  child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: HoolaType.button(c, color: c.onPill).copyWith(fontSize: height < 52 ? 14.5 : 16)),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// The quiet outline pill beside the main one (Free preview, Not now, Skip).
class CrQuiet extends StatelessWidget {
  const CrQuiet({super.key, required this.label, required this.onTap, this.height = 56, this.color, this.expand = false});
  final String label;
  final VoidCallback? onTap;
  final double height;
  final Color? color;
  final bool expand;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Material(
      color: c.surface,
      shape: StadiumBorder(side: BorderSide(color: c.lineStrong)),
      child: InkWell(
        customBorder: const StadiumBorder(),
        onTap: onTap == null
            ? null
            : () {
                HapticFeedback.selectionClick();
                onTap!();
              },
        child: Container(
          height: height,
          padding: const EdgeInsets.symmetric(horizontal: 18),
          alignment: Alignment.center,
          width: expand ? double.infinity : null,
          child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500, color: onTap == null ? c.ink3 : (color ?? c.ink))),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ blocks
/// A soft white card.
class CrCard extends StatelessWidget {
  const CrCard({super.key, required this.child, this.padding = const EdgeInsets.all(14), this.onTap, this.edge});
  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Color? edge;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final r = BorderRadius.circular(22);
    final box = Container(
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: r,
        border: Border.all(color: edge ?? c.line, width: edge == null ? 1 : 1.4),
        boxShadow: c.dark ? null : HoolaShadow.card(c),
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          borderRadius: r,
          onTap: onTap == null
              ? null
              : () {
                  HapticFeedback.selectionClick();
                  onTap!();
                },
          child: Padding(padding: padding, child: child),
        ),
      ),
    );
    return box;
  }
}

/// A section label: bold left, a quiet note right.
class CrLabel extends StatelessWidget {
  const CrLabel(this.text, {super.key, this.note = ''});
  final String text, note;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
        Semantics(header: true, child: Text(text, style: HoolaType.title(c).copyWith(fontSize: 14))),
        const SizedBox(width: 10),
        Expanded(
          child: Text(note, textAlign: TextAlign.right, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: HoolaType.small(c).copyWith(fontSize: 12.5)),
        ),
      ]),
    );
  }
}

/// The space between sections.
const crGap = SizedBox(height: 22);

/// One chip; [on] = the black pill.
class CrChip extends StatelessWidget {
  const CrChip({super.key, required this.label, required this.on, required this.onTap, this.glyph});
  final String label;
  final bool on;
  final VoidCallback onTap;
  final CrGlyph? glyph;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      selected: on,
      label: label,
      excludeSemantics: true,
      onTap: onTap,
      child: crTap48(onTap, Material(
        color: on ? c.pill : c.surface,
        shape: StadiumBorder(side: BorderSide(color: on ? c.pill : c.line)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: () {
            HapticFeedback.selectionClick();
            onTap();
          },
          child: Container(
            height: 40,
            constraints: const BoxConstraints(minWidth: 48),
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              if (glyph != null) ...[CrIcon(glyph!, size: 15, color: on ? c.onPill : c.ink2), const SizedBox(width: 6)],
              if (on && glyph == null) ...[CrIcon(CrGlyph.check, size: 13, color: c.onPill), const SizedBox(width: 6)],
              Flexible(
                child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: HoolaType.body(c).copyWith(fontSize: 13.5, fontWeight: FontWeight.w500, color: on ? c.onPill : c.ink2)),
              ),
            ]),
          ),
        ),
      )),
    );
  }
}

/// 48 dp of tap room around a smaller control (the visual keeps its size; the margin taps too).
Widget crTap48(VoidCallback? onTap, Widget visual) => GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap == null
          ? null
          : () {
              HapticFeedback.selectionClick();
              onTap();
            },
      child: ConstrainedBox(constraints: const BoxConstraints(minHeight: 48, minWidth: 48), child: Center(widthFactor: 1, heightFactor: 1, child: visual)),
    );

/// A wrap of chips, one picked.
class CrChips extends StatelessWidget {
  const CrChips({super.key, required this.options, required this.picked, required this.onPick, this.multi});
  final List<String> options;
  final String picked;
  final ValueChanged<String> onPick;
  final Set<String>? multi;   // when given: every option in it is on
  @override
  Widget build(BuildContext context) => Wrap(spacing: 8, runSpacing: 8, children: [
        for (final o in options) CrChip(label: o, on: multi != null ? multi!.contains(o) : o == picked, onTap: () => onPick(o)),
      ]);
}

/// A segmented control in a sunk tray (the chosen one lifts out in white).
class CrSegment extends StatelessWidget {
  const CrSegment({super.key, required this.options, required this.picked, required this.onPick, this.height = 44});
  final List<String> options;
  final String picked;
  final ValueChanged<String> onPick;
  final double height;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(height / 2 + 4)),
      child: Row(children: [
        for (final o in options)
          Expanded(
            child: Semantics(
              button: true,
              selected: o == picked,
              label: o,
              excludeSemantics: true,
              onTap: () => onPick(o),
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () {
                  HapticFeedback.selectionClick();
                  onPick(o);
                },
                child: SizedBox(height: height + 8, child: Center(child: AnimatedContainer(
                  duration: HoolaMotion.of(context, HoolaMotion.menu),
                  curve: HoolaMotion.ease,
                  height: height,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: o == picked ? c.surface : c.sunk,
                    borderRadius: BorderRadius.circular(height / 2),
                    boxShadow: o == picked && !c.dark ? HoolaShadow.card(c) : null,
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: Text(o, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.body(c).copyWith(fontSize: 13.5, fontWeight: FontWeight.w500, color: o == picked ? c.ink : c.ink2)),
                  ),
                ))),
              ),
            ),
          ),
      ]),
    );
  }
}

/// A grid of equal tiles, one picked (styles, formats). [cols] across.
class CrTiles extends StatelessWidget {
  const CrTiles({super.key, required this.options, required this.picked, required this.onPick, this.cols = 3, this.swatch = false});
  final List<String> options;
  final String picked;
  final ValueChanged<String> onPick;
  final int cols;
  final bool swatch;   // a small toned dot before each name
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return LayoutBuilder(builder: (context, box) {
      final w = (box.maxWidth - 8 * (cols - 1)) / cols;
      return Wrap(spacing: 8, runSpacing: 8, children: [
        for (final o in options)
          SizedBox(
            width: w,
            child: Semantics(
              button: true,
              selected: o == picked,
              label: o,
              excludeSemantics: true,
              onTap: () => onPick(o),
              child: Material(
                color: o == picked && !swatch ? c.pill : c.surface,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                  side: BorderSide(color: o == picked ? (swatch ? c.ink : c.pill) : c.line, width: o == picked && swatch ? 1.6 : 1),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(14),
                  onTap: () {
                    HapticFeedback.selectionClick();
                    onPick(o);
                  },
                  child: Container(
                    constraints: const BoxConstraints(minHeight: 52),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    alignment: swatch ? Alignment.centerLeft : Alignment.center,
                    child: Row(mainAxisSize: swatch ? MainAxisSize.max : MainAxisSize.min, children: [
                      if (swatch) ...[
                        Container(width: 22, height: 22, decoration: BoxDecoration(color: crTone(c, o), shape: BoxShape.circle)),
                        const SizedBox(width: 8),
                      ],
                      Flexible(
                        child: Text(o, maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: swatch ? TextAlign.left : TextAlign.center,
                            style: HoolaType.body(c).copyWith(
                                fontSize: 13,
                                height: 1.25,
                                fontWeight: o == picked ? FontWeight.w600 : FontWeight.w500,
                                color: o == picked ? (swatch ? c.ink : c.onPill) : c.ink2)),
                      ),
                    ]),
                  ),
                ),
              ),
            ),
          ),
      ]);
    });
  }
}

/// One setting row: a quiet name, its value, a chevron; a tap opens [pick] as a sheet of choices.
class CrSetting {
  const CrSetting(this.name, this.value, this.choices, this.onPick, {this.notes = const {}});
  final String name, value;
  final List<String> choices;
  final ValueChanged<String> onPick;
  final Map<String, String> notes;
}

class CrSettings extends StatelessWidget {
  const CrSettings(this.rows, {super.key});
  final List<CrSetting> rows;

  Future<void> _open(BuildContext context, CrSetting r) async {
    HapticFeedback.selectionClick();
    final v = await crPick(context, r.name, r.choices, r.value, notes: r.notes);
    if (v != null) r.onPick(v);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrCard(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(children: [
        for (var i = 0; i < rows.length; i++) ...[
          if (i > 0) Divider(height: 1, thickness: 1, color: c.line),
          Semantics(
            button: true,
            label: '${rows[i].name}: ${rows[i].value}',
            excludeSemantics: true,
            onTap: () => _open(context, rows[i]),
            child: InkWell(
              onTap: () => _open(context, rows[i]),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 58),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                        Text(rows[i].name, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                        const SizedBox(height: 2),
                        Text(rows[i].value, maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                      ]),
                    ),
                    CrIcon(CrGlyph.chevron, size: 16, color: c.ink3),
                  ]),
                ),
              ),
            ),
          ),
        ],
      ]),
    );
  }
}

/// The choices sheet: a title, one row per choice, a tick on the current one.
Future<String?> crPick(BuildContext context, String title, List<String> choices, String current,
    {Map<String, String> notes = const {}}) {
  return showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (ctx) {
      final c = HoolaColors.of(ctx);
      return SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * .72),
          child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(8, 0, 8, 16), children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
              child: Text(title, style: HoolaType.heading(c)),
            ),
            for (final o in choices)
              ListTile(
                minVerticalPadding: 12,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                title: Text(o, style: HoolaType.body(c).copyWith(fontWeight: o == current ? FontWeight.w600 : FontWeight.w400)),
                subtitle: notes[o] == null ? null : Text(notes[o]!, style: HoolaType.small(c)),
                trailing: o == current ? CrIcon(CrGlyph.check, size: 18, color: c.ink) : null,
                onTap: () => Navigator.of(ctx).pop(o),
              ),
          ]),
        ),
      );
    },
  );
}

/// A big number with - and + on each side (count, length, pace).
class CrStepper extends StatelessWidget {
  const CrStepper({super.key, required this.value, required this.onLess, required this.onMore, this.sub = '', this.height = 64,
      this.label = 'value'});
  final String value, sub, label;
  final VoidCallback? onLess, onMore;
  final double height;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget b(CrGlyph g, String l, VoidCallback? f) => SizedBox(
          child: IconButton(
            tooltip: l,
            onPressed: f == null
                ? null
                : () {
                    HapticFeedback.selectionClick();
                    f();
                  },
            style: IconButton.styleFrom(fixedSize: const Size.square(48)),
            icon: CrIcon(g, size: 16, color: f == null ? c.ink3 : c.ink),
          ),
        );
    return Container(
      height: height,
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: c.line)),
      child: Row(children: [
        b(CrGlyph.minus, 'Less $label', onLess),
        Expanded(
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(value, style: HoolaType.title(c).copyWith(fontSize: 17)),
            if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
        b(CrGlyph.plus, 'More $label', onMore),
      ]),
    );
  }
}

/// A switch row inside a card.
class CrSwitch extends StatelessWidget {
  const CrSwitch({super.key, required this.title, required this.sub, required this.value, required this.onChanged});
  final String title, sub;
  final bool value;
  final ValueChanged<bool> onChanged;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrCard(
      padding: const EdgeInsets.fromLTRB(16, 10, 10, 10),
      child: MergeSemantics(
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
              const SizedBox(height: 2),
              Text(sub, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
            ]),
          ),
          Switch(value: value, onChanged: (v) {
            HapticFeedback.selectionClick();
            onChanged(v);
          }),
        ]),
      ),
    );
  }
}

/// A text box inside a card, with its title, an optional action (Enhance / Write with Hoola) and a counter.
class CrTextCard extends StatelessWidget {
  const CrTextCard({super.key, required this.title, required this.controller, this.hint = '', this.max = 4000, this.lines = 4,
      this.action, this.footer, this.serif = false});
  final String title, hint;
  final TextEditingController controller;
  final int max, lines;
  final Widget? action, footer;
  final bool serif;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(title, style: HoolaType.title(c).copyWith(fontSize: 14))),
          if (action != null) action!,
        ]),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          minLines: lines,
          maxLines: lines + 6,
          maxLength: max,
          buildCounter: (_, {required int currentLength, required bool isFocused, required int? maxLength}) => null,
          style: serif
              ? TextStyle(fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 16, height: 1.6, color: c.ink)
              : HoolaType.bodyLarge(c).copyWith(fontSize: 15.5, height: 1.5),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: HoolaType.bodyLarge(c).copyWith(color: c.ink3, fontSize: 15.5),
            border: InputBorder.none,
            filled: false,
            isDense: true,
            contentPadding: EdgeInsets.zero,
          ),
        ),
        Divider(height: 20, thickness: 1, color: c.line),
        Row(children: [
          if (footer != null) Expanded(child: footer!) else const Spacer(),
          ValueListenableBuilder<TextEditingValue>(
            valueListenable: controller,
            builder: (_, v, __) => Text('${v.text.length} / $max', style: HoolaType.small(c).copyWith(fontSize: 12)),
          ),
        ]),
      ]),
    );
  }
}

/// The small outline action inside a card header (Enhance, Write with Hoola).
class CrSmall extends StatelessWidget {
  const CrSmall({super.key, required this.label, required this.onTap, this.glyph = CrGlyph.wand, this.busy = false});
  final String label;
  final VoidCallback? onTap;
  final CrGlyph glyph;
  final bool busy;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: label,
      excludeSemantics: true,
      onTap: busy ? null : onTap,
      child: crTap48(busy ? null : onTap, Material(
        color: c.surface,
        shape: StadiumBorder(side: BorderSide(color: c.line)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: busy || onTap == null ? null : onTap,
          child: Container(
            height: 36,
            constraints: const BoxConstraints(minWidth: 48),
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              if (busy)
                SizedBox(width: 13, height: 13, child: CircularProgressIndicator(strokeWidth: 1.8, color: c.ink2))
              else
                CrIcon(glyph, size: 14, color: c.ink),
              const SizedBox(width: 6),
              Flexible(
                child: Text(busy ? 'Working…' : label, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: HoolaType.body(c).copyWith(fontSize: 13, fontWeight: FontWeight.w500)),
              ),
            ]),
          ),
        ),
      )),
    );
  }
}

/// A quiet note in a sunk band (safety, what is and is not done).
class CrNote extends StatelessWidget {
  const CrNote(this.text, {super.key, this.glyph = CrGlyph.shield});
  final String text;
  final CrGlyph glyph;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 16, 12),
      decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(18)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(padding: const EdgeInsets.only(top: 1), child: CrIcon(glyph, size: 17, color: c.ink2)),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: HoolaType.small(c).copyWith(color: c.ink2, height: 1.45))),
      ]),
    );
  }
}

/// A quiet title + line used at the top of a tool (Dubbing, Casting, Cinema).
class CrIntro extends StatelessWidget {
  const CrIntro(this.title, this.sub, {super.key});
  final String title, sub;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Semantics(
        header: true,
        child: Text(title,
            style: TextStyle(fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 26, height: 1.25, color: c.ink)),
      ),
      const SizedBox(height: 6),
      Text(sub, style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14.5)),
    ]);
  }
}

// ------------------------------------------------------------------------------------------------ jobs and results
/// A running job: its title, the step it is on, a moving bar.
class CrJobRow extends StatelessWidget {
  const CrJobRow({super.key, required this.job, required this.store, this.tone});
  final Map<String, dynamic> job;
  final CreateStore store;
  final Color? tone;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final failed = job['status'] == 'failed';
    final step = crS(job['step']);
    return CrCard(
      edge: failed ? c.bad.withOpacity(.5) : null,
      child: Row(children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(color: tone ?? crTone(c, job['id']), borderRadius: BorderRadius.circular(12)),
          alignment: Alignment.center,
          child: failed
              ? CrIcon(CrGlyph.info, size: 20, color: c.bad)
              : SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(crS(job['title']).isEmpty ? 'Working' : crS(job['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            if (failed)
              Text(crS(job['error']).isEmpty ? 'This did not work.' : crS(job['error']), maxLines: 3, overflow: TextOverflow.ellipsis,
                  style: HoolaType.small(c).copyWith(color: c.bad))
            else ...[
              Text(step.isEmpty ? 'Making it now…' : 'Making it · $step', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
              const SizedBox(height: 6),
              ClipRRect(
                borderRadius: BorderRadius.circular(3),
                child: LinearProgressIndicator(minHeight: 5, backgroundColor: c.sunk, color: c.ink),
              ),
            ],
          ]),
        ),
        if (failed) TextButton(onPressed: () => store.dismiss(crS(job['id'])), child: const Text('Dismiss')),
      ]),
    );
  }
}

/// Saves a creation to a temporary file and hands it to the phone's share sheet (save to files, WhatsApp, gallery…).
Future<void> crShareItem(BuildContext context, Santosh app, Map<String, dynamic> it) async {
  final api = app.api;
  if (api == null) return;
  crToast(context, 'Getting the file…');
  try {
    final bytes = await api.createItemBytes(crS(it['id']));
    if (bytes == null) throw Exception('This file is no longer on Hoola.');
    final mime = crS(it['mime']);
    final ext = switch (mime) {
      'image/png' => '.png',
      'image/jpeg' => '.jpg',
      'image/webp' => '.webp',
      'audio/mpeg' => '.mp3',
      'audio/wav' || 'audio/x-wav' => '.wav',
      'video/mp4' => '.mp4',
      'text/plain' => '.txt',
      _ => '',
    };
    if (!context.mounted) return;
    await crShareBytes(context, bytes, '${crS(it['title'])}$ext', mime);
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
  }
}

/// Bytes into a temporary file, then the phone's share sheet (save to files, gallery, WhatsApp…).
Future<void> crShareBytes(BuildContext context, List<int> bytes, String name, String mime) async {
  try {
    final dir = await getTemporaryDirectory();
    var dot = name.lastIndexOf('.');
    if (dot > 0 && !RegExp(r'^\.[A-Za-z0-9]{1,5}$').hasMatch(name.substring(dot))) dot = -1;
    final stem = (dot > 0 ? name.substring(0, dot) : name).replaceAll(RegExp(r'[^A-Za-z0-9 _-]'), '').trim();
    final ext = dot > 0 ? name.substring(dot) : '';
    final f = File('${dir.path}/${stem.isEmpty ? 'hoola' : stem}$ext');
    await f.writeAsBytes(bytes, flush: true);
    await Native.shareFile(f.path, mime: mime.isEmpty ? 'application/octet-stream' : mime, title: stem);
  } catch (e) {
    if (context.mounted) crToast(context, crError(e));
  }
}

/// A picture from her shelf (needs the key, so the headers ride along).
class CrItemImage extends StatelessWidget {
  const CrItemImage({super.key, required this.app, required this.item, this.fit = BoxFit.cover, this.cache = 600});
  final Santosh app;
  final Map<String, dynamic> item;
  final BoxFit fit;
  final int cache;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final api = app.api;
    final tone = Container(color: crTone(c, item['id']));
    if (api == null || !crS(item['mime']).startsWith('image/')) return tone;
    return Image.network(api.createItemUrl(crS(item['id'])),
        headers: api.authHeaders, fit: fit, cacheWidth: cache, errorBuilder: (_, __, ___) => tone);
  }
}

/// A network picture from a studio link (signed, so no headers are needed; the key rides anyway).
class CrNetImage extends StatelessWidget {
  const CrNetImage({super.key, required this.app, required this.url, this.seed});
  final Santosh app;
  final String url;
  final Object? seed;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final tone = Container(color: crTone(c, seed ?? url));
    final api = app.api;
    if (url.isEmpty || api == null) return tone;
    return Image.network(api.absolute(url), headers: api.authHeaders, fit: BoxFit.cover, cacheWidth: 600,
        errorBuilder: (_, __, ___) => tone);
  }
}

/// One audio creation (a song or a voice-over): play / pause, its name and line, a progress line, save / share.
class CrAudioCard extends StatefulWidget {
  const CrAudioCard({super.key, required this.app, required this.item, required this.line});
  final Santosh app;
  final Map<String, dynamic> item;
  final String line;
  @override
  State<CrAudioCard> createState() => _CrAudioCardState();
}

class _CrAudioCardState extends State<CrAudioCard> {
  VideoPlayerController? _ctl;
  bool _loading = false;

  @override
  void dispose() {
    _ctl?.dispose();
    super.dispose();
  }

  Future<void> _toggle() async {
    final api = widget.app.api;
    if (api == null) return;
    var ctl = _ctl;
    if (ctl == null) {
      setState(() => _loading = true);
      ctl = VideoPlayerController.networkUrl(Uri.parse(api.createItemUrl(crS(widget.item['id']))), httpHeaders: api.authHeaders);
      try {
        await ctl.initialize();
      } catch (e) {
        await ctl.dispose();
        if (mounted) {
          setState(() => _loading = false);
          crToast(context, 'This sound did not open: ${crError(e)}');
        }
        return;
      }
      ctl.addListener(() {
        if (mounted) setState(() {});
      });
      if (!mounted) {
        await ctl.dispose();
        return;
      }
      setState(() {
        _ctl = ctl;
        _loading = false;
      });
    }
    if (ctl.value.isPlaying) {
      await ctl.pause();
    } else {
      if (ctl.value.position >= ctl.value.duration && ctl.value.duration > Duration.zero) await ctl.seekTo(Duration.zero);
      await ctl.play();
    }
  }

  String _t(Duration d) => '${d.inMinutes}:${(d.inSeconds % 60).toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = _ctl?.value;
    final playing = v?.isPlaying ?? false;
    final total = v?.duration ?? Duration.zero;
    final pos = v?.position ?? Duration.zero;
    final frac = total.inMilliseconds == 0 ? 0.0 : (pos.inMilliseconds / total.inMilliseconds).clamp(0.0, 1.0);
    return CrCard(
      child: Column(children: [
        Row(children: [
          Semantics(
            button: true,
            label: playing ? 'Pause ${crS(widget.item['title'])}' : 'Play ${crS(widget.item['title'])}',
            excludeSemantics: true,
            child: Material(
              color: c.pill,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: _loading ? null : _toggle,
                child: SizedBox(
                  width: 48,
                  height: 48,
                  child: Center(
                    child: _loading
                        ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                        : playing
                            ? Row(mainAxisSize: MainAxisSize.min, children: [
                                Container(width: 4, height: 15, decoration: BoxDecoration(color: c.onPill, borderRadius: BorderRadius.circular(2))),
                                const SizedBox(width: 4),
                                Container(width: 4, height: 15, decoration: BoxDecoration(color: c.onPill, borderRadius: BorderRadius.circular(2))),
                              ])
                            : CrIcon(CrGlyph.play, size: 18, color: c.onPill),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(crS(widget.item['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 2),
              Text(widget.line, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
            ]),
          ),
          CrRoundButton(glyph: CrGlyph.down, label: 'Save or share', onTap: () => crShareItem(context, widget.app, widget.item)),
        ]),
        const SizedBox(height: 12),
        _Wave(seed: crS(widget.item['id']), frac: frac),
        const SizedBox(height: 6),
        Row(children: [
          Text(_t(pos), style: HoolaType.small(c).copyWith(fontSize: 12)),
          const Spacer(),
          Text(total == Duration.zero ? crWhen(widget.item['created']) : _t(total), style: HoolaType.small(c).copyWith(fontSize: 12)),
        ]),
      ]),
    );
  }
}

/// A quiet waveform drawn from the item's id (the same shape every time), filled up to where it is playing.
class _Wave extends StatelessWidget {
  const _Wave({required this.seed, required this.frac});
  final String seed;
  final double frac;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ExcludeSemantics(
      child: SizedBox(height: 34, width: double.infinity, child: CustomPaint(painter: _WavePainter(seed, frac, c.ink, c.lineStrong))),
    );
  }
}

class _WavePainter extends CustomPainter {
  _WavePainter(this.seed, this.frac, this.on, this.off);
  final String seed;
  final double frac;
  final Color on, off;
  @override
  void paint(Canvas canvas, Size size) {
    const n = 44;
    final r = math.Random(seed.codeUnits.fold<int>(7, (a, b) => a * 31 + b) & 0x7fffffff);
    final w = size.width / n;
    for (var i = 0; i < n; i++) {
      final env = math.sin(math.pi * (i + .5) / n);
      final h = math.max(4.0, size.height * (.25 + .75 * r.nextDouble()) * (.35 + .65 * env));
      final paint = Paint()..color = (i + .5) / n <= frac ? on : off;
      canvas.drawRRect(
          RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(w * (i + .5), size.height / 2), width: w * .55, height: h),
              const Radius.circular(2)),
          paint);
    }
  }

  @override
  bool shouldRepaint(_WavePainter o) => o.frac != frac || o.on != on;
}

/// What a kind is called in a sentence (Song, Voice-over…).
String crKindName(String kind) => switch (kind) {
      'image' => 'Picture',
      'cast' => 'Character',
      'song' => 'Song',
      'voice' => 'Voice-over',
      'dub' => 'Dub',
      'script' => 'Script',
      _ => 'Creation',
    };
