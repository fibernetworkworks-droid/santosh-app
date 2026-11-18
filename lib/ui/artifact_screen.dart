import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../state.dart';
import 'chat/hoola_artifact.dart' show artifactSteps, artifactStepIndex, artifactClock;
import 'glass.dart';
import 'hoola_theme.dart';

int _num(Object? v) => v is num ? v.toInt() : (int.tryParse('${v ?? ''}') ?? 0);

String _clean(Object e) => e.toString().replaceFirst('Exception: ', '');

/// "5 min pehle" style time for an ISO timestamp.
String artifactAgo(String? iso) {
  final t = DateTime.tryParse(iso ?? '')?.toLocal();
  if (t == null) return '';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'now';
  if (d.inHours < 1) return '${d.inMinutes} min ago';
  if (d.inDays < 1) return '${d.inHours} hours ago';
  return '${d.inDays} days ago';
}

/// Open an artifact full-screen. Returns when the screen is closed.
Future<void> openArtifact(BuildContext context, Santosh app, String id, String title) async {
  // v0.902 the viewer is drawn in the new design for everyone (light / dark from her Appearance)
  await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => HoolaTheme(appearance: app.appearance, child: ArtifactScreen(app: app, id: id, title: title))));
}

/// Santosh Artifact: an interactive page Santosh built (app, calculator, tracker, chart, document, quiz, plan).
/// Opens full-screen, can be revised by asking, shared by link. The page talks to the app through `window.santosh`.
class ArtifactScreen extends StatefulWidget {
  const ArtifactScreen({super.key, required this.app, required this.id, required this.title});
  final Santosh app;
  final String id;
  final String title;
  @override
  State<ArtifactScreen> createState() => _ArtifactScreenState();
}

class _ArtifactScreenState extends State<ArtifactScreen> {
  late final WebViewController _web;
  final _ask = TextEditingController();
  Timer? _poll;
  String _title = '';
  String _url = '';
  Uri? _home;            // the artifact's own address: only this origin opens inside
  int _latest = 0;       // newest ready version we know of
  int? _viewing;         // version on screen; null = latest
  int _shown = 0;        // version actually loaded
  String _status = 'ready';
  String? _failNote;
  String? _loadError;
  int _progress = 0;
  bool _loading = true;
  bool _sending = false;
  bool _shared = false;
  bool _pollBusy = false;
  int _seenV = -1;
  String _seenSt = '';
  String _stage = '';        // v0.902 the builder's real step + when it started (the building bar's clock)
  DateTime? _startedAt;
  Timer? _tick;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _title = widget.title;
    final it = app.artifactItem(widget.id);
    if (it != null) {
      _seenV = _num(it.data['version']);
      _seenSt = it.data['status'] as String? ?? 'ready';
      _status = _seenSt;
      if (_status == 'ready') _latest = _seenV;
      if (_status == 'failed') _failNote = it.data['error'] as String?;
      _stage = it.data['stage'] as String? ?? '';
      _startedAt = DateTime.tryParse(it.data['started_at'] as String? ?? '');
    }
    _tick = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted && _status == 'building') setState(() {});
    });
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..addJavaScriptChannel('SantoshBridge', onMessageReceived: _onBridge)
      ..setNavigationDelegate(NavigationDelegate(
        onProgress: (p) {
          if (mounted) setState(() => _progress = p);
        },
        onPageFinished: (_) {
          if (mounted) {
            setState(() {
              _progress = 100;
              _loading = false;
            });
          }
        },
        onWebResourceError: (e) {
          if (e.isForMainFrame == false || !mounted) return;
          setState(() {
            _loading = false;
            _loadError = 'Page did not load (${e.description})';
          });
        },
        onNavigationRequest: _onNav,
      ));
    app.addListener(_onApp);
    _poll = Timer.periodic(const Duration(seconds: 5), (_) => _pollStatus());
    _init();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _poll?.cancel();
    _tick?.cancel();
    _ask.dispose();
    super.dispose();
  }

  void _snack(String t) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _init() async {
    await _refreshDetail(reload: false);
    await _load();
  }

  /// Latest facts from the server (title, sharing, status, newest version).
  Future<void> _refreshDetail({bool reload = true}) async {
    final api = app.api;
    if (api == null) return;
    try {
      final d = await api.artifact(widget.id);
      if (!mounted) return;
      setState(() {
        final t = d['title'] as String?;
        if (t != null && t.isNotEmpty) _title = t;
        _shared = d['shared'] == true;
        _stage = d['stage'] as String? ?? _stage;
        _startedAt = DateTime.tryParse(d['started_at'] as String? ?? '') ?? _startedAt;
      });
      _apply(_num(d['version']), d['status'] as String? ?? 'ready', d['error'] as String?, reload: reload);
    } catch (_) {}
  }

  /// While Santosh is building, ask the server now and then (in case the chat stream is not this artifact's chat).
  Future<void> _pollStatus() async {
    if (_status != 'building' || _pollBusy) return;
    _pollBusy = true;
    try {
      await _refreshDetail();
    } finally {
      _pollBusy = false;
    }
  }

  /// The chat card for this artifact changed (live 'artifact' event).
  void _onApp() {
    final it = app.artifactItem(widget.id);
    if (it == null || !mounted) return;
    final v = _num(it.data['version']);
    final st = it.data['status'] as String? ?? 'ready';
    if (v == _seenV && st == _seenSt) return;
    _seenV = v;
    _seenSt = st;
    if (st == 'deleted') return;
    _stage = it.data['stage'] as String? ?? _stage;
    _startedAt = DateTime.tryParse(it.data['started_at'] as String? ?? '') ?? _startedAt;
    _apply(v, st, it.data['error'] as String?);
  }

  void _apply(int version, String status, String? error, {bool reload = true}) {
    if (!mounted) return;
    var reloadNow = false;
    setState(() {
      _status = status;
      _failNote = status == 'failed' ? ((error ?? '').isEmpty ? 'The change could not be made. Please say it again.' : error) : null;
      if (status == 'ready' && version > _latest) {
        _latest = version;
        _viewing = null; // a newer version is ready: show it
        reloadNow = reload;
      }
    });
    if (reloadNow) _load();
  }

  Future<void> _load() async {
    if (!mounted) return;
    final api = app.api;
    if (api == null) {
      setState(() {
        _loading = false;
        _loadError = 'Not connected to Hoola.';
      });
      return;
    }
    setState(() {
      _loading = true;
      _loadError = null;
      _progress = 0;
    });
    try {
      final url = await api.artifactViewUrl(widget.id, version: _viewing);
      if (!mounted) return;
      _url = url;
      _home = Uri.tryParse(url);
      await _web.loadRequest(Uri.parse(url));
      if (mounted) setState(() => _shown = _viewing ?? _latest);
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadError = _clean(e);
        });
      }
    }
  }

  /// The artifact's own address opens here; every other link opens outside the app.
  NavigationDecision _onNav(NavigationRequest r) {
    final uri = Uri.tryParse(r.url);
    if (uri == null) return NavigationDecision.prevent;
    if (!r.isMainFrame || uri.scheme == 'about') return NavigationDecision.navigate;
    final home = _home;
    if (home != null && uri.scheme == home.scheme && uri.host == home.host && uri.port == home.port) {
      return NavigationDecision.navigate;
    }
    if (uri.scheme == 'data' || uri.scheme == 'blob' || uri.scheme == 'javascript') return NavigationDecision.prevent;
    launchUrl(uri, mode: LaunchMode.externalApplication).catchError((_) => false);
    return NavigationDecision.prevent;
  }

  // ---------------- window.santosh bridge ----------------
  Future<void> _onBridge(JavaScriptMessage m) async {
    Object? callId;
    try {
      final msg = jsonDecode(m.message);
      if (msg is! Map) return;
      callId = msg['id'];
      final op = msg['op'];
      final rawArgs = msg['args'];
      final args = rawArgs is Map ? Map<String, dynamic>.from(rawArgs) : <String, dynamic>{};
      final api = app.api;
      if (api == null) throw Exception('Not connected to Hoola');
      Object? result;
      switch (op) {
        case 'storage.get':
          final getKey = '${args['key'] ?? ''}';
          if (getKey.isEmpty) throw Exception('key needed');
          result = (await api.artifactState(widget.id))[getKey];
        case 'storage.set':
          final setKey = '${args['key'] ?? ''}';
          if (setKey.isEmpty) throw Exception('key needed');
          await api.artifactSetState(widget.id, setKey, args['value']);
          result = true;
        case 'storage.all':
          result = await api.artifactState(widget.id);
        case 'ask':
          final q = '${args['question'] ?? ''}'.trim();
          if (q.isEmpty) throw Exception('question needed');
          result = await api.artifactAsk(widget.id, q);
        default:
          await _reply(callId, false, 'Unknown op: $op');
          return;
      }
      await _reply(callId, true, result);
    } catch (e) {
      await _reply(callId, false, _clean(e));
    }
  }

  Future<void> _reply(Object? callId, bool ok, Object? result) async {
    if (!mounted) return;
    try {
      await _web.runJavaScript(
          'window.__santoshReply && window.__santoshReply(${jsonEncode(callId)}, ${ok ? 'true' : 'false'}, ${jsonEncode(result)});');
    } catch (_) {}
  }

  // ---------------- actions ----------------
  Future<void> _revise() async {
    final req = _ask.text.trim();
    final api = app.api;
    if (req.isEmpty || _sending || api == null) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _sending = true;
      _failNote = null;
    });
    try {
      await api.artifactRevise(widget.id, req);
      _ask.clear();
      if (mounted) setState(() => _status = 'building');
    } catch (e) {
      _snack('Change not sent: ${_clean(e)}');
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _versions() async {
    final api = app.api;
    if (api == null) return;
    var vs = <Map<String, dynamic>>[];
    try {
      final d = await api.artifact(widget.id);
      vs = ((d['versions'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    } catch (e) {
      _snack(_clean(e));
      return;
    }
    if (!mounted) return;
    vs.sort((a, b) => _num(b['version']).compareTo(_num(a['version'])));
    final pick = await _sheet<int>((ctx, c) => [
          _sheetTitle(c, 'Versions', sub: vs.length < 2 ? 'Only one version so far' : '${vs.length} versions · newest first'),
          for (final v in vs)
            _sheetRow(
              ctx,
              c,
              icon: _num(v['version']) == _shown ? Icons.check_circle_rounded : Icons.history_rounded,
              tint: _num(v['version']) == _shown ? c.ok : c.ink2,
              title: (v['note'] as String? ?? '').isEmpty ? 'Version ${_num(v['version'])}' : 'Version ${_num(v['version'])} · ${v['note']}',
              sub: [if (_num(v['version']) == _latest) 'Newest', artifactAgo(v['created_at'] as String?)].where((x) => x.isNotEmpty).join(' · '),
              onTap: () => Navigator.pop(ctx, _num(v['version'])),
            ),
          if (vs.length > 1 && _status != 'building') ...[
            Divider(height: 17, indent: 20, endIndent: 20, color: c.line),
            _sheetRow(ctx, c,
                icon: Icons.undo_rounded,
                title: 'Undo the last change',
                sub: 'Version ${_latest - 1 < 1 ? 1 : _latest - 1} comes back as a new version',
                onTap: () => Navigator.pop(ctx, -1)),
          ],
        ]);
    if (pick == null || !mounted) return;
    if (pick == -1) return _undo();
    setState(() => _viewing = pick == _latest ? null : pick);
    await _load();
  }

  Future<void> _undo() async {
    final api = app.api;
    if (api == null) return;
    try {
      await api.artifactUndo(widget.id);
      await _refreshDetail();
      _snack('The version before is back.');
    } catch (e) {
      _snack(_clean(e));
    }
  }

  Future<void> _stop() async {
    final api = app.api;
    if (api == null) return;
    HapticFeedback.lightImpact();
    try {
      await api.artifactStop(widget.id);
      _snack('Stopping. The last version stays.');
    } catch (e) {
      _snack(_clean(e));
    }
  }

  Future<void> _copyLink() async {
    final api = app.api;
    if (api == null) return;
    try {
      final r = await api.artifactShare(widget.id, true);
      final raw = r['share_url'] as String? ?? '';
      if (raw.isEmpty) {
        _snack('The link could not be made. Please try again.');
        return;
      }
      await Clipboard.setData(ClipboardData(text: api.absolute(raw)));
      if (mounted) setState(() => _shared = true);
      _snack('Link copied. Anyone with the link can view this page.');
    } catch (e) {
      _snack(_clean(e));
    }
  }

  Future<void> _openBrowser() async {
    if (_url.isEmpty) return;
    try {
      final ok = await launchUrl(Uri.parse(_url), mode: LaunchMode.externalApplication);
      if (!ok) _snack('The browser did not open.');
    } catch (_) {
      _snack('The browser did not open.');
    }
  }

  Future<void> _delete() async {
    final go = await _sheet<bool>((ctx, c) => [
          _sheetTitle(c, 'Remove "$_title"?', sub: 'Every version is deleted for good, and a shared link stops working.'),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
            child: FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: FilledButton.styleFrom(
                  backgroundColor: c.bad, foregroundColor: c.onAccent, shape: const StadiumBorder(),
                  minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
              child: const Text('Remove'),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
            child: TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
              child: const Text('Keep it'),
            ),
          ),
        ]);
    final api = app.api;
    if (go != true || !mounted || api == null) return;
    try {
      await api.artifactDelete(widget.id);
      final it = app.artifactItem(widget.id);
      if (it != null) {
        it.data = {...it.data, 'status': 'deleted'};
        app.notifyChange();
      }
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      _snack('Could not remove it: ${_clean(e)}');
    }
  }

  /// The ⋮ menu: a sheet like Claude's (open in browser, copy link, share, versions, reload, remove).
  Future<void> _more() async {
    final pick = await _sheet<String>((ctx, c) => [
          _sheetRow(ctx, c, icon: Icons.open_in_new_rounded, title: 'Open in browser', onTap: () => Navigator.pop(ctx, 'browser')),
          _sheetRow(ctx, c, icon: Icons.link_rounded, title: 'Copy link', sub: _shared ? 'Shared by link' : 'Turns on a view-only link',
              onTap: () => Navigator.pop(ctx, 'copy')),
          _sheetRow(ctx, c, icon: Icons.ios_share_rounded, title: 'Share…', onTap: () => Navigator.pop(ctx, 'share')),
          Divider(height: 17, indent: 20, endIndent: 20, color: c.line),
          _sheetRow(ctx, c, icon: Icons.history_rounded, title: 'Versions', sub: _latest > 0 ? 'Newest is version $_latest' : '',
              onTap: () => Navigator.pop(ctx, 'versions')),
          _sheetRow(ctx, c, icon: Icons.refresh_rounded, title: 'Reload', onTap: () => Navigator.pop(ctx, 'reload')),
          Divider(height: 17, indent: 20, endIndent: 20, color: c.line),
          _sheetRow(ctx, c, icon: Icons.delete_outline_rounded, tint: c.bad, title: 'Remove', danger: true,
              onTap: () => Navigator.pop(ctx, 'delete')),
        ]);
    switch (pick) {
      case 'browser':
        _openBrowser();
      case 'copy':
        _copyLink();
      case 'share':
        final on = await openArtifactShare(context, app, widget.id, _title);
        if (on != null && mounted) setState(() => _shared = on);
      case 'versions':
        _versions();
      case 'reload':
        _load();
      case 'delete':
        _delete();
    }
  }

  Future<T?> _sheet<T>(List<Widget> Function(BuildContext ctx, HoolaColors c) rows) {
    final c = HoolaColors.of(context);
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => HoolaTheme(
        appearance: app.appearance,
        child: Builder(builder: (ctx) {
          final c = HoolaColors.of(ctx);
          return SafeArea(
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 5,
                    margin: const EdgeInsets.only(top: 10, bottom: 10),
                    decoration: BoxDecoration(color: c.lineStrong, borderRadius: BorderRadius.circular(5)),
                  ),
                ),
                ...rows(ctx, c),
                const SizedBox(height: 8),
              ]),
            ),
          );
        }),
      ),
    );
  }

  // ---------------- UI ----------------
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final building = _status == 'building';
    final old = _viewing != null && _viewing != _latest;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          _header(c),
          if (_progress < 100 && _loadError == null)
            LinearProgressIndicator(value: _progress / 100, minHeight: 2, color: c.accent, backgroundColor: Colors.transparent)
          else
            Divider(height: 2, thickness: 1, color: c.line),
          if (building) _buildingBar(c),
          if (old) _oldBar(c),
          if (_failNote != null && !building) _failBar(c),
          Expanded(
            child: Stack(children: [
              Positioned.fill(child: WebViewWidget(controller: _web)),
              if (_loading && _loadError == null)
                Positioned.fill(
                  child: ColoredBox(
                    color: c.bg,
                    child: Center(
                      child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3)),
                    ),
                  ),
                ),
              if (_loadError != null) Positioned.fill(child: _errorView(c, building)),
            ]),
          ),
          _composer(c, building),
        ]),
      ),
    );
  }

  Widget _header(HoolaColors c) {
    final sub = [
      if (_shown > 0) 'Version $_shown${_latest > _shown ? ' of $_latest' : ''}',
      if (_shared) 'Shared by link',
    ].join(' · ');
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 4, 4, 4),
      child: Row(children: [
        IconButton(tooltip: 'Close', icon: Icon(Icons.close_rounded, color: c.ink), onPressed: () => Navigator.of(context).pop()),
        const SizedBox(width: 2),
        Expanded(
          child: Semantics(
            header: true,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(_title.isEmpty ? 'Page' : _title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
              Text(sub.isEmpty ? 'Page' : 'Page · $sub', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
            ]),
          ),
        ),
        if (_latest > 1)
          IconButton(tooltip: 'Versions', icon: Icon(Icons.history_rounded, color: c.ink2), onPressed: _versions),
        IconButton(tooltip: 'Share', icon: Icon(Icons.ios_share_rounded, color: c.ink2), onPressed: () async {
          final on = await openArtifactShare(context, app, widget.id, _title);
          if (on != null && mounted) setState(() => _shared = on);
        }),
        IconButton(tooltip: 'More', icon: Icon(Icons.more_vert_rounded, color: c.ink2), onPressed: _more),
      ]),
    );
  }

  Widget _bar(HoolaColors c, {required Widget lead, required String text, required Color bg, Color? fg, Widget? action}) =>
      Container(
        margin: const EdgeInsets.fromLTRB(12, 8, 12, 4),
        padding: const EdgeInsets.fromLTRB(14, 6, 6, 6),
        constraints: const BoxConstraints(minHeight: 48),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(HoolaRadius.card)),
        child: Row(children: [
          lead,
          const SizedBox(width: 10),
          Expanded(
            child: Text(text,
                style: HoolaType.body(c).copyWith(fontSize: 14, color: fg ?? c.ink, fontFeatures: const [FontFeature.tabularFigures()])),
          ),
          if (action != null) action,
        ]),
      );

  Widget _buildingBar(HoolaColors c) {
    final step = artifactSteps[artifactStepIndex(_stage)].$2;
    final t0 = _startedAt;
    final clock = t0 == null ? '' : ' · ${artifactClock(DateTime.now().toUtc().difference(t0.toUtc()).inSeconds)}';
    return _bar(
      c,
      lead: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: c.accent)),
      text: _latest > 0 ? 'Making version ${_latest + 1} · $step$clock' : '$step$clock',
      bg: c.accentSoft,
      action: TextButton(
        onPressed: _stop,
        style: TextButton.styleFrom(foregroundColor: c.bad, minimumSize: const Size(64, 40), shape: const StadiumBorder()),
        child: const Text('Stop'),
      ),
    );
  }

  Widget _oldBar(HoolaColors c) => _bar(
        c,
        lead: Icon(Icons.history_rounded, size: 18, color: c.ink2),
        text: 'You are looking at version $_viewing',
        bg: c.sunk,
        action: TextButton(
          onPressed: () {
            setState(() => _viewing = null);
            _load();
          },
          style: TextButton.styleFrom(foregroundColor: c.accent, minimumSize: const Size(64, 40), shape: const StadiumBorder()),
          child: const Text('Newest'),
        ),
      );

  Widget _failBar(HoolaColors c) => _bar(
        c,
        lead: Icon(Icons.error_outline_rounded, size: 18, color: c.bad),
        text: _failNote ?? '',
        bg: c.badSoft,
        action: IconButton(
          tooltip: 'Dismiss',
          onPressed: () => setState(() => _failNote = null),
          icon: Icon(Icons.close_rounded, size: 18, color: c.ink3),
        ),
      );

  Widget _errorView(HoolaColors c, bool building) => ColoredBox(
        color: c.bg,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(color: c.sunk, shape: BoxShape.circle),
                child: Icon(building ? Icons.hourglass_top_rounded : Icons.cloud_off_rounded, color: c.ink3, size: 26),
              ),
              const SizedBox(height: 16),
              Text(building ? 'The page is being made' : 'The page did not open', textAlign: TextAlign.center, style: HoolaType.title(c)),
              const SizedBox(height: 6),
              Text(_loadError ?? '', textAlign: TextAlign.center, style: HoolaType.small(c)),
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed: _load,
                style: OutlinedButton.styleFrom(
                    foregroundColor: c.ink, side: BorderSide(color: c.lineStrong), shape: const StadiumBorder(),
                    minimumSize: const Size(0, HoolaSpace.touch)),
                child: const Text('Try again'),
              ),
            ]),
          ),
        ),
      );

  Widget _composer(HoolaColors c, bool building) => Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
        child: Container(
          padding: const EdgeInsets.fromLTRB(18, 4, 4, 4),
          decoration: BoxDecoration(
            color: c.surface,
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: c.lineStrong),
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: TextField(
                  controller: _ask,
                  minLines: 1,
                  maxLines: 4,
                  enabled: !building,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _revise(),
                  style: HoolaType.body(c),
                  decoration: InputDecoration(
                    hintText: building ? 'Making the new version…' : 'Ask for a change to this page',
                    hintStyle: HoolaType.body(c).copyWith(color: c.ink3),
                    isDense: true,
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    disabledBorder: InputBorder.none,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 6),
            Semantics(
              button: true,
              label: 'Send the change',
              child: SizedBox(
                width: 48,
                height: 48,
                child: Center(
                  child: Material(
                    color: _sending || building ? c.sunk : c.pill,
                    shape: const CircleBorder(),
                    child: InkWell(
                      customBorder: const CircleBorder(),
                      onTap: _sending || building ? null : _revise,
                      child: SizedBox(
                        width: 40,
                        height: 40,
                        child: Center(
                          child: _sending
                              ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3))
                              : Icon(Icons.arrow_upward_rounded, size: 22, color: building ? c.ink3 : c.onPill),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ]),
        ),
      );
}

Widget _sheetTitle(HoolaColors c, String title, {String sub = ''}) => Padding(
      padding: const EdgeInsets.fromLTRB(20, 2, 20, 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Semantics(header: true, child: Text(title, style: HoolaType.heading(c))),
        if (sub.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(sub, style: HoolaType.small(c))),
      ]),
    );

Widget _sheetRow(BuildContext ctx, HoolaColors c,
        {required IconData icon, required String title, String sub = '', Color? tint, bool danger = false, VoidCallback? onTap}) =>
    InkWell(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 56),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          child: Row(children: [
            Icon(icon, size: 22, color: tint ?? c.ink2),
            const SizedBox(width: 18),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(title, style: HoolaType.bodyLarge(c).copyWith(color: danger ? c.bad : c.ink)),
                if (sub.isNotEmpty) Text(sub, style: HoolaType.small(c)),
              ]),
            ),
          ]),
        ),
      ),
    );

/// The share sheet for a page: turns on a view-only link, shows it, Copy / Open / Stop sharing.
/// Returns whether the page is shared afterwards (null = nothing changed / failed).
Future<bool?> openArtifactShare(BuildContext context, Santosh app, String id, String title) async {
  final api = app.api;
  if (api == null) return null;
  final messenger = ScaffoldMessenger.maybeOf(context);
  String link;
  try {
    final r = await api.artifactShare(id, true);
    final raw = r['share_url'] as String? ?? '';
    if (raw.isEmpty) throw Exception('The link could not be made. Please try again.');
    link = api.absolute(raw);
  } catch (e) {
    messenger?.showSnackBar(SnackBar(content: Text(_clean(e))));
    return null;
  }
  if (!context.mounted) return true;
  final c0 = HoolaColors.of(context);
  final stop = await showModalBottomSheet<bool>(
    context: context,
    useSafeArea: true,
    backgroundColor: c0.surface,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => HoolaTheme(
      appearance: app.appearance,
      child: Builder(builder: (ctx) {
        final c = HoolaColors.of(ctx);
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 10, 20, 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Center(
              child: Container(
                width: 40,
                height: 5,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(color: c.lineStrong, borderRadius: BorderRadius.circular(5)),
              ),
            ),
            Semantics(header: true, child: Text('Share "$title"', maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.heading(c))),
            const SizedBox(height: 6),
            Row(children: [
              Icon(Icons.public_rounded, size: 16, color: c.ok),
              const SizedBox(width: 6),
              Expanded(child: Text('Anyone with the link can view this page. They cannot change it.', style: HoolaType.small(c))),
            ]),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(HoolaRadius.tile)),
              child: SelectableText(link, maxLines: 2, style: HoolaType.code(c, size: 13)),
            ),
            const SizedBox(height: 14),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication).catchError((_) => false),
                  icon: const Icon(Icons.open_in_new_rounded, size: 18),
                  label: const Text('Open'),
                  style: OutlinedButton.styleFrom(
                      foregroundColor: c.ink, side: BorderSide(color: c.lineStrong), shape: const StadiumBorder(),
                      minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: link));
                    if (ctx.mounted) Navigator.pop(ctx, false);
                    messenger?.showSnackBar(const SnackBar(content: Text('Link copied.')));
                  },
                  icon: const Icon(Icons.link_rounded, size: 18),
                  label: const Text('Copy link'),
                  style: FilledButton.styleFrom(
                      backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder(),
                      minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                ),
              ),
            ]),
            const SizedBox(height: 6),
            TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: TextButton.styleFrom(foregroundColor: c.bad, minimumSize: const Size.fromHeight(HoolaSpace.touch)),
              child: const Text('Stop sharing'),
            ),
          ]),
        );
      }),
    ),
  );
  if (stop != true) return true;
  try {
    await api.artifactShare(id, false);
    messenger?.showSnackBar(const SnackBar(content: Text('Sharing is off. The old link no longer opens.')));
    return false;
  } catch (e) {
    messenger?.showSnackBar(SnackBar(content: Text(_clean(e))));
    return true;
  }
}

/// Chat card for an artifact Santosh built. One card per artifact; it updates as new versions arrive.
class ArtifactCard extends StatelessWidget {
  const ArtifactCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'ready';
    final id = v['id'] as String? ?? '';
    final rawTitle = v['title'] as String? ?? '';
    final title = rawTitle.isEmpty ? 'Artifact' : rawTitle;
    final summary = v['summary'] as String? ?? '';
    final version = _num(v['version']);
    final error = v['error'] as String? ?? '';
    String chip = version > 1 ? 'v$version' : 'READY';
    Color chipFg = C.ok;
    if (status == 'failed') {
      chip = 'NOT MADE';
      chipFg = C.bad;
    }
    if (status == 'deleted') {
      chip = 'REMOVED';
      chipFg = C.muted;
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(gradient: C.gradient, borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.auto_awesome_mosaic_rounded, color: C.onAccent, size: 22),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                const Text('Hoola Artifact', style: TextStyle(color: C.faint, fontSize: 12)),
              ]),
            ),
            if (status == 'building')
              const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.accent))
            else
              Pill(chip, fg: chipFg),
          ]),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(summary, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: Color(0xFFD7D2F2))),
          ],
          if (status == 'building')
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('Building… ready in a moment', style: TextStyle(color: C.warn, fontSize: 12.5, fontWeight: FontWeight.w600)),
            ),
          if (status == 'failed')
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(error.isEmpty ? 'Could not be made. Ask Hoola again.' : error, style: const TextStyle(color: C.bad, fontSize: 12.5)),
            ),
          if (status != 'deleted' && id.isNotEmpty) ...[
            const SizedBox(height: 10),
            GradientButton(label: 'Open', height: 42, icon: Icons.open_in_full_rounded, onTap: () => openArtifact(context, app, id, title)),
          ],
        ]),
      ),
    );
  }
}

/// Small floating pill on the voice call screen when Santosh builds something during the call.
class ArtifactCallPill extends StatefulWidget {
  const ArtifactCallPill({super.key, required this.app});
  final Santosh app;
  @override
  State<ArtifactCallPill> createState() => _ArtifactCallPillState();
}

class _ArtifactCallPillState extends State<ArtifactCallPill> {
  int _seen = 0;  // only artifacts that arrive while this screen is open
  int _built = 0;

  @override
  void initState() {
    super.initState();
    _seen = _built = widget.app.artifactTick;
    widget.app.addListener(_onApp);
  }

  @override
  void dispose() {
    widget.app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (mounted && widget.app.artifactTick != _built) setState(() => _built = widget.app.artifactTick);
  }

  void _dismiss() => setState(() => _seen = widget.app.artifactTick);

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final a = app.latestArtifact;
    if (a == null || app.artifactTick <= _seen) return const SizedBox.shrink();
    // v0.158 during a call only a page this call made pops up here (the rest stays in the chat)
    if (app.voiceCall.inCall && a['_call'] != app.voiceCall.callId) return const SizedBox.shrink();
    final id = a['id'] as String? ?? '';
    final rawTitle = a['title'] as String? ?? '';
    final title = rawTitle.isEmpty ? 'Artifact' : rawTitle;
    final status = a['status'] as String? ?? '';
    final ready = status == 'ready';
    final failed = status == 'failed';
    final canOpen = ready && id.isNotEmpty && !app.lockedMode;
    final text = ready
        ? (app.lockedMode ? '📄 $title — ready, unlock to view' : '📄 $title — ready, Open')
        : failed
            ? '📄 $title — could not be made'
            : '📄 $title — building…';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Center(
        child: Semantics(
          button: canOpen,
          label: text,
          child: Press(
            onTap: canOpen
                ? () {
                    _dismiss();
                    openArtifact(context, app, id, title);
                  }
                : null,
            child: Container(
              padding: const EdgeInsets.fromLTRB(14, 6, 4, 6),
              decoration: BoxDecoration(
                color: const Color(0xE61A1438),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: ready ? C.accent.withOpacity(.6) : const Color(0x29FFFFFF)),
                boxShadow: const [BoxShadow(color: Color(0x59050314), blurRadius: 18, offset: Offset(0, 6))],
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                if (!ready && !failed) ...[
                  const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 1.8, color: C.accent)),
                  const SizedBox(width: 8),
                ],
                Flexible(
                  child: Text(text,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: ready ? C.accent : (failed ? C.bad : C.chip))),
                ),
                GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: _dismiss,
                  child: const Padding(padding: EdgeInsets.all(6), child: Icon(Icons.close_rounded, size: 16, color: C.muted)),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}
