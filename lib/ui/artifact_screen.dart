import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../state.dart';
import 'glass.dart';

int _num(Object? v) => v is num ? v.toInt() : (int.tryParse('${v ?? ''}') ?? 0);

String _clean(Object e) => e.toString().replaceFirst('Exception: ', '');

/// "5 min pehle" style time for an ISO timestamp.
String artifactAgo(String? iso) {
  final t = DateTime.tryParse(iso ?? '')?.toLocal();
  if (t == null) return '';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'abhi';
  if (d.inHours < 1) return '${d.inMinutes} min pehle';
  if (d.inDays < 1) return '${d.inHours} ghante pehle';
  return '${d.inDays} din pehle';
}

/// Open an artifact full-screen. Returns when the screen is closed.
Future<void> openArtifact(BuildContext context, Santosh app, String id, String title) async {
  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArtifactScreen(app: app, id: id, title: title)));
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
    }
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
            _loadError = 'Page load nahi hua (${e.description})';
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
    _apply(v, st, it.data['error'] as String?);
  }

  void _apply(int version, String status, String? error, {bool reload = true}) {
    if (!mounted) return;
    var reloadNow = false;
    setState(() {
      _status = status;
      _failNote = status == 'failed' ? ((error ?? '').isEmpty ? 'Badlaav nahi ho paya. Dobara boliye.' : error) : null;
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
        _loadError = 'Hoola se connect nahi hai.';
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
      if (api == null) throw Exception('Hoola se connect nahi hai');
      Object? result;
      switch (op) {
        case 'storage.get':
          final getKey = '${args['key'] ?? ''}';
          if (getKey.isEmpty) throw Exception('key chahiye');
          result = (await api.artifactState(widget.id))[getKey];
        case 'storage.set':
          final setKey = '${args['key'] ?? ''}';
          if (setKey.isEmpty) throw Exception('key chahiye');
          await api.artifactSetState(widget.id, setKey, args['value']);
          result = true;
        case 'storage.all':
          result = await api.artifactState(widget.id);
        case 'ask':
          final q = '${args['question'] ?? ''}'.trim();
          if (q.isEmpty) throw Exception('question chahiye');
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
      _snack('Badlaav nahi bheja: ${_clean(e)}');
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
    final pick = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: const Color(0xF21A1438),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (ctx) => SafeArea(
        child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(8, 16, 8, 8), children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Text('Versions', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          ),
          if (vs.isEmpty) const ListTile(title: Text('Abhi sirf ek version hai')),
          for (final v in vs)
            ListTile(
              leading: Pill('v${_num(v['version'])}'),
              title: Text((v['note'] as String? ?? '').isEmpty ? 'Version ${_num(v['version'])}' : v['note'] as String,
                  maxLines: 2, overflow: TextOverflow.ellipsis),
              subtitle: Text(artifactAgo(v['created_at'] as String?), style: const TextStyle(color: C.faint, fontSize: 12)),
              trailing: _num(v['version']) == _shown ? const Icon(Icons.check_rounded, color: C.ok) : null,
              onTap: () => Navigator.pop(ctx, _num(v['version'])),
            ),
        ]),
      ),
    );
    if (pick == null || !mounted) return;
    setState(() => _viewing = pick == _latest ? null : pick);
    await _load();
  }

  Future<void> _share(bool on) async {
    final api = app.api;
    if (api == null) return;
    try {
      final r = await api.artifactShare(widget.id, on);
      if (!mounted) return;
      setState(() => _shared = r['shared'] == true);
      if (!on) {
        _snack('Sharing band. Purana link ab nahi khulega.');
        return;
      }
      final raw = r['share_url'] as String? ?? '';
      if (raw.isEmpty) {
        _snack('Share link nahi mila. Dobara koshish kijiye.');
        return;
      }
      await Clipboard.setData(ClipboardData(text: api.absolute(raw)));
      _snack('Link copy ho gaya. Jiske paas bhi yeh link hai, woh ise dekh sakta hai.');
    } catch (e) {
      _snack('Nahi ho paya: ${_clean(e)}');
    }
  }

  Future<void> _openBrowser() async {
    if (_url.isEmpty) return;
    try {
      final ok = await launchUrl(Uri.parse(_url), mode: LaunchMode.externalApplication);
      if (!ok) _snack('Browser nahi khula.');
    } catch (_) {
      _snack('Browser nahi khula.');
    }
  }

  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Artifact hataiye?'),
        content: Text('"$_title" aur iske saare versions hamesha ke liye hat jayenge. Share kiya hua link bhi band ho jayega.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: C.bad, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Hataiye'),
          ),
        ],
      ),
    );
    final api = app.api;
    if (ok != true || !mounted || api == null) return;
    try {
      await api.artifactDelete(widget.id);
      final it = app.artifactItem(widget.id);
      if (it != null) {
        it.data = {...it.data, 'status': 'deleted'};
        app.notifyChange();
      }
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      _snack('Nahi hata paya: ${_clean(e)}');
    }
  }

  void _menu(String v) {
    switch (v) {
      case 'versions':
        _versions();
      case 'share':
        _share(true);
      case 'unshare':
        _share(false);
      case 'browser':
        _openBrowser();
      case 'reload':
        _load();
      case 'delete':
        _delete();
    }
  }

  // ---------------- UI ----------------
  @override
  Widget build(BuildContext context) {
    final building = _status == 'building';
    final old = _viewing != null && _viewing != _latest;
    return Scaffold(
      backgroundColor: C.bgTop,
      body: SafeArea(
        child: Column(children: [
          _header(),
          if (old) _oldBanner(),
          if (building) _strip(),
          if (_failNote != null && !building) _failStrip(),
          if (_progress < 100 && _loadError == null)
            LinearProgressIndicator(value: _progress / 100, minHeight: 2.5, color: C.accent, backgroundColor: Colors.transparent),
          Expanded(
            child: Stack(children: [
              Positioned.fill(child: WebViewWidget(controller: _web)),
              if (_loading && _loadError == null)
                const Positioned.fill(
                  child: ColoredBox(color: C.bgTop, child: Center(child: CircularProgressIndicator(color: C.accent))),
                ),
              if (_loadError != null) Positioned.fill(child: _errorView(building)),
            ]),
          ),
          _composer(building),
        ]),
      ),
    );
  }

  Widget _header() => Glass(
        margin: const EdgeInsets.fromLTRB(10, 6, 10, 6),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        radius: 20,
        child: Row(children: [
          IconButton(tooltip: 'Band karo', icon: const Icon(Icons.close_rounded, color: C.chip), onPressed: () => Navigator.of(context).pop()),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(_title.isEmpty ? 'Artifact' : _title,
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
              Text(_shared ? 'Hoola Artifact · link se share' : 'Hoola Artifact',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
            ]),
          ),
          if (_shown > 0) Pill('v$_shown', fg: C.accent),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert_rounded, color: C.chip),
            onSelected: _menu,
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'versions', child: Text('Versions dekhiye')),
              const PopupMenuItem(value: 'share', child: Text('Link share karein')),
              if (_shared) const PopupMenuItem(value: 'unshare', child: Text('Sharing band karein')),
              const PopupMenuItem(value: 'browser', child: Text('Browser mein kholiye')),
              const PopupMenuItem(value: 'reload', child: Text('Dobara load karein')),
              const PopupMenuItem(value: 'delete', child: Text('Hataiye', style: TextStyle(color: C.bad))),
            ],
          ),
        ]),
      );

  Widget _note(Widget lead, String text, Color bg, Color fg, {Widget? action}) => Container(
        margin: const EdgeInsets.fromLTRB(10, 0, 10, 6),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          lead,
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: TextStyle(color: fg, fontSize: 12.5, fontWeight: FontWeight.w600))),
          if (action != null) action,
        ]),
      );

  Widget _strip() => _note(
        const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: C.accent)),
        'Hoola bana raha hai… naya version taiyaar hote hi yahin khul jayega',
        const Color(0x2EFFB15C),
        const Color(0xFFFFD9A8),
      );

  Widget _failStrip() => _note(
        const Icon(Icons.error_outline_rounded, color: C.bad, size: 18),
        _failNote ?? '',
        const Color(0x26F87171),
        const Color(0xFFFECACA),
        action: GestureDetector(
          onTap: () => setState(() => _failNote = null),
          child: const Padding(padding: EdgeInsets.all(4), child: Icon(Icons.close_rounded, color: C.muted, size: 18)),
        ),
      );

  Widget _oldBanner() => _note(
        const Icon(Icons.history_rounded, color: C.chip, size: 18),
        'Purana version v$_viewing dekh rahe hain',
        const Color(0x17FFFFFF),
        C.chip,
        action: TextButton(
          onPressed: () {
            setState(() => _viewing = null);
            _load();
          },
          child: const Text('Naya dekhiye'),
        ),
      );

  Widget _errorView(bool building) => ColoredBox(
        color: C.bgTop,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Icon(building ? Icons.hourglass_top_rounded : Icons.cloud_off_rounded, color: C.muted, size: 40),
              const SizedBox(height: 10),
              Text(building ? 'Abhi ban raha hai…' : 'Page nahi khula', style: display(18)),
              const SizedBox(height: 6),
              Text(_loadError ?? '', textAlign: TextAlign.center, style: const TextStyle(color: C.muted, fontSize: 13)),
              const SizedBox(height: 14),
              GlassButton(label: 'Dobara koshish', icon: Icons.refresh_rounded, onTap: _load),
            ]),
          ),
        ),
      );

  Widget _composer(bool building) => Glass(
        margin: const EdgeInsets.fromLTRB(10, 6, 10, 8),
        padding: const EdgeInsets.fromLTRB(14, 2, 4, 2),
        radius: 20,
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: _ask,
              minLines: 1,
              maxLines: 3,
              enabled: !building,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _revise(),
              style: const TextStyle(fontSize: 14.5, color: C.ink),
              decoration: InputDecoration(
                hintText: building ? 'Hoola bana raha hai…' : 'Badlaav batayiye… (e.g. dark mode, Hindi mein)',
                isDense: true,
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                disabledBorder: InputBorder.none,
              ),
            ),
          ),
          IconButton(
            tooltip: 'Badlaav bhejiye',
            onPressed: _sending || building ? null : _revise,
            icon: _sending
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: C.accent))
                : Icon(Icons.send_rounded, color: building ? C.faint : C.accent),
          ),
        ]),
      );
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
    String chip = version > 1 ? 'v$version' : 'TAIYAAR';
    Color chipFg = C.ok;
    if (status == 'failed') {
      chip = 'NAHI BANA';
      chipFg = C.bad;
    }
    if (status == 'deleted') {
      chip = 'HATA DIYA';
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
              child: Text('Bana raha hoon… thodi der mein taiyaar', style: TextStyle(color: C.warn, fontSize: 12.5, fontWeight: FontWeight.w600)),
            ),
          if (status == 'failed')
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(error.isEmpty ? 'Nahi ban paya. Hoola se dobara boliye.' : error, style: const TextStyle(color: C.bad, fontSize: 12.5)),
            ),
          if (status != 'deleted' && id.isNotEmpty) ...[
            const SizedBox(height: 10),
            GradientButton(label: 'Kholiye', height: 42, icon: Icons.open_in_full_rounded, onTap: () => openArtifact(context, app, id, title)),
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
    final id = a['id'] as String? ?? '';
    final rawTitle = a['title'] as String? ?? '';
    final title = rawTitle.isEmpty ? 'Artifact' : rawTitle;
    final status = a['status'] as String? ?? '';
    final ready = status == 'ready';
    final failed = status == 'failed';
    final canOpen = ready && id.isNotEmpty && !app.lockedMode;
    final text = ready
        ? (app.lockedMode ? '📄 $title — taiyaar, unlock karke dekhiye' : '📄 $title — taiyaar, Kholiye')
        : failed
            ? '📄 $title — nahi ban paya'
            : '📄 $title — bana raha hoon…';
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
