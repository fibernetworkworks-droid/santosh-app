// v0.901 CONNECT (owner: "just show a composio connector in here. Make it more premium and category wise perfectly" ->
// design canvas claude.ai/artifact/CRtSQ8Ew7RN2w3GyaxsC49 -> "GO"): the Connect page shows ONLY her apps through
// Composio (~1,600), in ten plain groups the server works out (bazar/composio.py GROUPS):
//
//   home      - title, how many connected, search, group chips, Your apps (icons with a tick), Most used by Indian
//               businesses, Browse by category (the first four groups with their top three apps, the rest as tiles),
//               the sign-in promise, and the way to Built-in tools (UPI apps, banks, brokers = the old Bazar screen).
//   group     - one group: search inside it, Popular / A-Z / Connected, paged list.
//   app sheet - what Hoola can do there, what it will and won't do, one big button: Connect (her sign-in on the app's
//               own page), Add key (typed here, never in chat), Connected + Remove, or Coming soon.
//   waiting   - after the sign-in page opens the row says "Waiting"; when she comes back and the app is connected a
//               "<App> is connected" note shows on top.
//
// Every colour / size / movement comes from hoola_theme.dart. Labels are English; the server's Hinglish `say` is
// never shown.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../native.dart';
import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_tabs.dart' show HoolaSearch, HoolaChips, HoolaEmpty, HoolaGroup, HoolaRow, HoolaSection;

/// Data the screenshot tests hand the page (they run without a server). Never set in the app.
class HoolaConnectDebug {
  static Map<String, dynamic>? home;
  static Map<String, dynamic>? apps;
}

String _s(Object? v) => v == null ? '' : '$v';

/// One Composio app as her page shows it.
class ConnectApp {
  ConnectApp({required this.toolkit, required this.name, this.line = '', this.logo = '', this.group = 'more',
      this.groupName = '', this.tools = 0, this.status = 'needs_link'});
  final String toolkit, name, line, logo, group, groupName;
  final int tools;
  String status;   // ready | pending | needs_link | needs_key | needs_setup | not_configured

  factory ConnectApp.from(Map<String, dynamic> m) => ConnectApp(
        toolkit: _s(m['toolkit']),
        name: _s(m['name']),
        line: _s(m['line']).isNotEmpty ? _s(m['line']) : _s(m['does']),
        logo: _s(m['logo']),
        group: _s(m['group']).isEmpty ? 'more' : _s(m['group']),
        groupName: _s(m['group_name']),
        tools: (m['tools'] as num?)?.toInt() ?? 0,
        status: _s(m['status']).isEmpty ? 'needs_link' : _s(m['status']),
      );

  bool get connected => status == 'ready';
}

/// One of the ten groups.
class ConnectGroup {
  ConnectGroup({required this.id, required this.name, this.count = 0, this.connected = 0, this.top = const []});
  final String id, name;
  final int count, connected;
  final List<ConnectApp> top;

  factory ConnectGroup.from(Map<String, dynamic> m) => ConnectGroup(
        id: _s(m['id']),
        name: _s(m['name']),
        count: (m['count'] as num?)?.toInt() ?? 0,
        connected: (m['connected'] as num?)?.toInt() ?? 0,
        top: [for (final a in (m['top'] as List? ?? const [])) ConnectApp.from(Map<String, dynamic>.from(a as Map))],
      );
}

/// Pure: the server's home into what the page draws (tested). The first four groups with apps to show get a card of
/// their top apps; every other group is a tile; "More apps" always goes last.
({List<ConnectApp> mine, List<ConnectApp> featured, List<ConnectGroup> cards, List<ConnectGroup> tiles, int total})
    connectHome(Map<String, dynamic> h) {
  List<ConnectApp> apps(Object? l) =>
      [for (final a in (l as List? ?? const [])) ConnectApp.from(Map<String, dynamic>.from(a as Map))];
  final groups = [for (final g in (h['groups'] as List? ?? const [])) ConnectGroup.from(Map<String, dynamic>.from(g as Map))]
    ..removeWhere((g) => g.id.isEmpty || g.count == 0);
  final more = groups.where((g) => g.id == 'more').toList();
  groups.removeWhere((g) => g.id == 'more');
  final cards = <ConnectGroup>[], tiles = <ConnectGroup>[];
  for (final g in groups) {
    (cards.length < 4 && g.top.isNotEmpty ? cards : tiles).add(g);
  }
  tiles.addAll(more);
  return (
    mine: apps(h['mine']),
    featured: apps(h['featured']),
    cards: cards,
    tiles: tiles,
    total: (h['total'] as num?)?.toInt() ?? 0,
  );
}

/// The words on an app's button for each state (tested).
String connectActionLabel(String status, {bool waiting = false}) {
  if (waiting && status != 'ready') return 'Waiting';
  return switch (status) {
    'ready' => 'Connected',
    'pending' => 'Finish sign-in',
    'needs_key' => 'Add key',
    'needs_setup' || 'not_configured' => 'Coming soon',
    _ => 'Connect',
  };
}

IconData connectGroupIcon(String id) => switch (id) {
      'mail' => Icons.mail_outline_rounded,
      'crm' => Icons.groups_outlined,
      'money' => Icons.account_balance_wallet_outlined,
      'projects' => Icons.checklist_rounded,
      'marketing' => Icons.campaign_outlined,
      'calendar' => Icons.calendar_month_outlined,
      'docs' => Icons.description_outlined,
      'store' => Icons.storefront_outlined,
      'data' => Icons.bar_chart_rounded,
      'dev' => Icons.code_rounded,
      _ => Icons.apps_rounded,
    };

(Color, Color) _groupTint(HoolaColors c, String id) => switch (id) {
      'mail' || 'calendar' => (c.info, c.infoSoft),
      'crm' || 'store' => (c.warn, c.warnSoft),
      'money' || 'data' => (c.ok, c.okSoft),
      'projects' || 'dev' => (c.accent, c.accentSoft),
      'marketing' => (c.bad, c.badSoft),
      _ => (c.ink2, c.sunk),
    };

String _count(int n) {
  if (n < 1000) return '$n';
  final s = '$n';
  return '${s.substring(0, s.length - 3)},${s.substring(s.length - 3)}';
}

// ------------------------------------------------------------------ the flow every page shares
/// Connecting, adding a key and removing: the same on the home, a group page and search.
class ConnectFlow {
  /// Apps whose sign-in page she opened; their rows say "Waiting" until she comes back.
  static final waiting = <String>{};

  static String plainError(Object e) {
    final t = '$e'.replaceFirst('Exception: ', '').replaceFirst('ApiException: ', '');
    if (t.contains('SocketException') || t.contains('TimeoutException') || t.contains('Connection')) {
      return 'Hoola could not be reached. Check the internet and try again.';
    }
    return t.length > 160 ? '${t.substring(0, 159)}…' : t;
  }

  /// The app sheet. `onChanged` reloads the page behind it.
  static Future<void> open(BuildContext context, Santosh app, ConnectApp a, {required VoidCallback onChanged}) {
    final c = HoolaColors.of(context);
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: c.bg,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (_) => HoolaTheme(
        appearance: app.appearance,
        child: _AppSheet(app: app, a: a, onChanged: onChanged),
      ),
    );
  }

  /// Opens the app's own sign-in page (or the key form). Returns a plain error or null.
  static Future<String?> connect(BuildContext context, Santosh app, ConnectApp a, VoidCallback onChanged) async {
    final api = app.api;
    if (api == null) return 'Hoola is not signed in on this phone.';
    HapticFeedback.selectionClick();
    Map<String, dynamic> r;
    try {
      r = await api.composioConnect(a.toolkit);
    } catch (e) {
      return plainError(e);
    }
    final st = _s(r['status']);
    if (st == 'ready') {
      a.status = 'ready';
      onChanged();
      return null;
    }
    if (st == 'needs_key') {
      if (!context.mounted) return null;
      final fields = [for (final f in (r['fields'] as List? ?? const [])) Map<String, dynamic>.from(f as Map)];
      return _keySheet(context, app, a, fields, onChanged);
    }
    final url = _s(r['url']);
    if (url.isEmpty) {
      return st == 'needs_setup'
          ? '${a.name} is not switched on yet. Hoola has to set it up once before anyone can connect it.'
          : '${a.name} cannot be connected right now. Please try again later.';
    }
    final res = await Native.openExternal(url: url);
    if (res != 'ok') return res;
    waiting.add(a.toolkit);
    onChanged();
    return null;
  }

  static Future<String?> _keySheet(BuildContext context, Santosh app, ConnectApp a, List<Map<String, dynamic>> fields,
      VoidCallback onChanged) async {
    final list = fields.isEmpty
        ? [<String, dynamic>{'name': 'generic_api_key', 'label': 'API key', 'secret': true, 'required': true}]
        : fields;
    final ctl = {for (final f in list) _s(f['name']): TextEditingController()};
    final c = HoolaColors.of(context);
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => HoolaTheme(
        appearance: app.appearance,
        child: Builder(builder: (ctx) {
          final c = HoolaColors.of(ctx);
          return Padding(
            padding: EdgeInsets.fromLTRB(24, 20, 24, 16 + MediaQuery.of(ctx).viewInsets.bottom),
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('Add your ${a.name} key', style: HoolaType.heading(c)),
                const SizedBox(height: 6),
                Text('${a.name} uses a key instead of a sign-in page. ${a.name} checks it, and Hoola never shows it again.',
                    style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14)),
                for (final f in list) ...[
                  const SizedBox(height: 16),
                  TextField(
                    controller: ctl[_s(f['name'])],
                    obscureText: f['secret'] == true,
                    autocorrect: false,
                    enableSuggestions: false,
                    style: HoolaType.code(c, size: 14).copyWith(color: c.ink),
                    decoration: InputDecoration(
                      labelText: '${_s(f['label']).isEmpty ? _s(f['name']) : _s(f['label'])}${f['required'] == false ? ' (optional)' : ''}',
                      helperText: _s(f['hint']).isEmpty ? null : _s(f['hint']),
                      helperMaxLines: 3,
                      filled: true,
                      fillColor: c.bg,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(HoolaRadius.tile)),
                      focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(HoolaRadius.tile), borderSide: BorderSide(color: c.accent, width: 1.5)),
                    ),
                  ),
                ],
                const SizedBox(height: 8),
                Row(children: [
                  Icon(Icons.lock_outline_rounded, size: 14, color: c.ink3),
                  const SizedBox(width: 6),
                  Expanded(child: Text('Type it here only. Never paste a key in the chat.', style: HoolaType.small(c))),
                ]),
                const SizedBox(height: 20),
                Row(children: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx, false),
                    style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size(88, HoolaSpace.touchMain)),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder(),
                          minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                      child: const Text('Check and connect'),
                    ),
                  ),
                ]),
              ]),
            ),
          );
        }),
      ),
    );
    final values = {for (final e in ctl.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
    for (final x in ctl.values) {
      x.dispose();
    }
    if (ok != true) return null;
    if (values.isEmpty) return 'Nothing was typed, so ${a.name} was not connected.';
    try {
      final res = await app.api!.composioKey(a.toolkit, values);
      a.status = _s(res['status']) == 'ready' ? 'ready' : 'pending';
      onChanged();
      return null;
    } catch (e) {
      return plainError(e);
    }
  }

  static Future<String?> remove(BuildContext context, Santosh app, ConnectApp a, VoidCallback onChanged) async {
    final c = HoolaColors.of(context);
    final ok = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Remove ${a.name}?', style: HoolaType.heading(c)),
            const SizedBox(height: 8),
            Text('Hoola will stop working in your ${a.name} account until you connect it again.',
                style: HoolaType.body(c).copyWith(color: c.ink2)),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: FilledButton.styleFrom(backgroundColor: c.bad, foregroundColor: c.onAccent, shape: const StadiumBorder(),
                  minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
              child: const Text('Remove'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
              child: const Text('Keep it'),
            ),
          ]),
        ),
      ),
    );
    if (ok != true) return null;
    try {
      await app.api!.composioRemove(a.toolkit);
      a.status = 'needs_link';
      waiting.remove(a.toolkit);
      onChanged();
      return null;
    } catch (e) {
      return plainError(e);
    }
  }
}

// ------------------------------------------------------------------ small parts
/// The app's own logo (served and cached by Hoola), else its first letter on a quiet tile.
class ConnectLogo extends StatelessWidget {
  const ConnectLogo({super.key, required this.app, required this.a, this.size = 44, this.tick = false});
  final Santosh app;
  final ConnectApp a;
  final double size;
  final bool tick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final r = BorderRadius.circular(size * .29);
    final letter = Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: c.sunk, borderRadius: r),
      child: Text(a.name.isEmpty ? '?' : a.name.characters.first.toUpperCase(),
          style: HoolaType.title(c).copyWith(color: c.ink2, fontSize: size * .4)),
    );
    final api = app.api;
    Widget tile = letter;
    if (a.logo.isNotEmpty && api != null) {
      tile = Container(
        width: size,
        height: size,
        padding: EdgeInsets.all(size * .14),
        decoration: BoxDecoration(color: c.surface, borderRadius: r, border: Border.all(color: c.line)),
        child: Image.network(a.logo.startsWith('http') ? a.logo : api.absolute(a.logo),
            fit: BoxFit.contain, cacheWidth: (size * 3).round(), errorBuilder: (_, __, ___) => letter),
      );
    }
    if (!tick) return ExcludeSemantics(child: tile);
    return ExcludeSemantics(
      child: Stack(clipBehavior: Clip.none, children: [
        tile,
        Positioned(
          right: -3,
          bottom: -3,
          child: Container(
            width: 18,
            height: 18,
            decoration: BoxDecoration(color: c.ok, shape: BoxShape.circle, border: Border.all(color: c.bg, width: 2.5)),
            child: Icon(Icons.check_rounded, size: 10, color: c.onAccent),
          ),
        ),
      ]),
    );
  }
}

/// What sits on the right of an app row.
class ConnectAction extends StatelessWidget {
  const ConnectAction({super.key, required this.a, required this.onTap, this.busy = false});
  final ConnectApp a;
  final VoidCallback onTap;
  final bool busy;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final waiting = ConnectFlow.waiting.contains(a.toolkit);
    if (a.connected) {
      return Semantics(label: 'Connected', child: Icon(Icons.check_circle_rounded, color: c.ok, size: 22));
    }
    if (busy || waiting || a.status == 'pending') {
      return Container(
        height: 36,
        padding: const EdgeInsets.only(left: 10, right: 12),
        decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(HoolaRadius.pill)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: c.accent)),
          const SizedBox(width: 7),
          Text(busy ? 'Opening' : 'Waiting', style: HoolaType.label(c).copyWith(color: c.accent, fontSize: 13)),
        ]),
      );
    }
    if (a.status == 'needs_setup' || a.status == 'not_configured') {
      return Text('Soon', style: HoolaType.label(c).copyWith(color: c.ink3));
    }
    return OutlinedButton(
      onPressed: onTap,
      style: OutlinedButton.styleFrom(
        foregroundColor: a.status == 'needs_key' ? c.ink2 : c.ink,
        side: BorderSide(color: c.lineStrong),
        shape: const StadiumBorder(),
        minimumSize: const Size(64, 36),
        tapTargetSize: MaterialTapTargetSize.padded,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        textStyle: HoolaType.label(c).copyWith(fontSize: 13.5),
      ),
      child: Text(connectActionLabel(a.status)),
    );
  }
}

/// One app as a row of a grouped card.
class ConnectRow extends StatelessWidget {
  const ConnectRow({super.key, required this.app, required this.a, required this.onOpen, required this.onAct, this.busy = false});
  final Santosh app;
  final ConnectApp a;
  final VoidCallback onOpen, onAct;
  final bool busy;
  @override
  Widget build(BuildContext context) {
    final waiting = ConnectFlow.waiting.contains(a.toolkit) && !a.connected;
    return HoolaRow(
      title: a.name,
      sub: waiting ? 'Finish signing in on ${a.name}\'s page' : a.line,
      tile: ConnectLogo(app: app, a: a),
      trailing: ConnectAction(a: a, onTap: onAct, busy: busy),
      semantics: '${a.name}, ${a.connected ? 'connected' : connectActionLabel(a.status, waiting: waiting).toLowerCase()}',
      onTap: onOpen,
    );
  }
}

/// The serif page title used on Connect and a group page.
class _BigTitle extends StatelessWidget {
  const _BigTitle(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      header: true,
      child: Text(text, style: HoolaType.hero(c).copyWith(fontSize: 30, fontWeight: FontWeight.w500, letterSpacing: -.2)),
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 64),
        child: Center(
          child: SizedBox(
              width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: HoolaColors.of(context).ink3)),
        ),
      );
}

// ------------------------------------------------------------------ the home
class HoolaConnect extends StatefulWidget {
  const HoolaConnect({super.key, required this.app, required this.onMore});
  final Santosh app;
  /// Built-in tools: UPI apps, banks, brokers, shops (the full plugin screen).
  final VoidCallback onMore;
  @override
  State<HoolaConnect> createState() => _HoolaConnectState();
}

class _HoolaConnectState extends State<HoolaConnect> with WidgetsBindingObserver {
  Map<String, dynamic>? _home;
  String _err = '';
  bool _off = false;   // Composio is not switched on on this server
  final _search = TextEditingController();
  String _q = '';
  Timer? _debounce;
  Map<String, dynamic>? _found;
  bool _finding = false;
  int _linkTick = 0;
  final _busy = <String>{};
  final _justConnected = <String>[];

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _linkTick = app.bazarLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    app.removeListener(_onApp);
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // back from an app's sign-in page: read her apps again
    if (state == AppLifecycleState.resumed && ConnectFlow.waiting.isNotEmpty) _load(quiet: true);
  }

  void _onApp() {
    if (app.bazarLinkedTick != _linkTick) {
      _linkTick = app.bazarLinkedTick;
      _load(quiet: true);
    }
  }

  Future<void> _load({bool quiet = false}) async {
    final api = app.api;
    Map<String, dynamic> h;
    try {
      h = api == null ? (HoolaConnectDebug.home ?? const {'configured': false}) : await api.composioHome();
    } catch (e) {
      if (!mounted || quiet) return;
      setState(() {
        _home ??= const {};
        _err = ConnectFlow.plainError(e);
      });
      return;
    }
    if (!mounted) return;
    final mine = connectHome(h).mine;
    for (final a in mine) {
      if (a.connected && ConnectFlow.waiting.remove(a.toolkit) && !_justConnected.contains(a.name)) _justConnected.add(a.name);
    }
    setState(() {
      _home = h;
      _off = h['configured'] == false;
      _err = '';
    });
    if (_q.isNotEmpty) _find(_q);
  }

  void _onSearch(String v) {
    setState(() => _q = v.trim());
    _debounce?.cancel();
    if (_q.isEmpty) {
      setState(() => _found = null);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 350), () => _find(_q));
  }

  Future<void> _find(String q) async {
    final api = app.api;
    setState(() => _finding = true);
    try {
      final r = api == null ? (HoolaConnectDebug.apps ?? const {'apps': []}) : await api.composioApps(q: q);
      if (!mounted || q != _q) return;
      setState(() => _found = r);
    } catch (e) {
      if (mounted && q == _q) setState(() => _found = {'apps': [], 'error': ConnectFlow.plainError(e)});
    } finally {
      if (mounted) setState(() => _finding = false);
    }
  }

  void _changed() {
    if (mounted) setState(() {});
    _load(quiet: true);
  }

  void _snack(String? m) {
    if (m == null || m.isEmpty || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _act(ConnectApp a) async {
    if (a.status == 'needs_setup' || a.status == 'not_configured') return _openSheet(a);
    if (_busy.contains(a.toolkit)) return;
    setState(() => _busy.add(a.toolkit));
    final err = await ConnectFlow.connect(context, app, a, _changed);
    if (!mounted) return;
    setState(() => _busy.remove(a.toolkit));
    _snack(err);
  }

  Future<void> _openSheet(ConnectApp a) => ConnectFlow.open(context, app, a, onChanged: _changed);

  void _openGroup(String id, String name, {String sort = ''}) {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => HoolaTheme(appearance: app.appearance, child: ConnectGroupPage(app: app, group: id, name: name, sort: sort)),
    )).then((_) => _load(quiet: true));
  }

  Widget _row(ConnectApp a) => ConnectRow(
      app: app, a: a, busy: _busy.contains(a.toolkit), onOpen: () => _openSheet(a), onAct: () => _act(a));

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final h = _home;
    final parts = h == null ? null : connectHome(h);
    final total = parts?.total ?? 0;
    final mineN = parts?.mine.where((a) => a.connected).length ?? 0;
    return RefreshIndicator(
      color: c.accent,
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: HoolaSpace.s32),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 2, HoolaSpace.s12, HoolaSpace.gutter, 4),
            child: const _BigTitle('Connect'),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 2, 0, HoolaSpace.gutter, HoolaSpace.s12),
            child: Text(
              parts == null || _off
                  ? 'Apps Hoola can work in for you.'
                  : 'Apps Hoola can work in for you. $mineN connected · ${_count(total)} ready to add.',
              style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14),
            ),
          ),
          if (!_off)
            HoolaSearch(controller: _search, hint: total > 0 ? 'Search ${_count(total)} apps' : 'Search apps', onChanged: _onSearch),
          if (parts == null)
            const _Loading()
          else if (_off)
            HoolaEmpty(
                icon: Icons.extension_off_outlined,
                title: 'Apps are not switched on yet',
                sub: 'Hoola\'s app connections are being set up. Your built-in tools work meanwhile.')
          else if (_err.isNotEmpty && parts.cards.isEmpty)
            HoolaEmpty(icon: Icons.cloud_off_rounded, title: 'Apps could not be opened', sub: _err, onRetry: _load)
          else if (_q.isNotEmpty)
            ..._searchBody(c)
          else
            ..._homeBody(c, parts),
          _trust(c),
          _builtIn(c),
        ],
      ),
    );
  }

  List<Widget> _homeBody(HoolaColors c,
      ({List<ConnectApp> mine, List<ConnectApp> featured, List<ConnectGroup> cards, List<ConnectGroup> tiles, int total}) p) {
    final groups = [...p.cards, ...p.tiles];
    return [
      if (groups.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: HoolaChips(
            items: [('all', 'All'), for (final g in groups) (g.id, g.name)],
            picked: 'all',
            onPick: (k) {
              if (k == 'all') return;
              final g = groups.firstWhere((x) => x.id == k);
              _openGroup(g.id, g.name);
            },
          ),
        ),
      for (final name in _justConnected) _connectedNote(c, name),
      if (p.mine.isNotEmpty) ...[
        _sectionHead(c, 'Your apps', action: 'Manage', onAction: () => _openGroup('', 'Your apps', sort: 'connected')),
        SizedBox(
          height: 92,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
            children: [
              for (final a in p.mine)
                Semantics(
                  button: true,
                  label: '${a.name}, ${a.connected ? 'connected' : 'not connected yet'}',
                  child: InkWell(
                    borderRadius: BorderRadius.circular(HoolaRadius.card),
                    onTap: () => _openSheet(a),
                    child: SizedBox(
                      width: 72,
                      child: Column(children: [
                        const SizedBox(height: 4),
                        ConnectLogo(app: app, a: a, size: 56, tick: a.connected),
                        const SizedBox(height: 6),
                        ExcludeSemantics(
                          child: Text(a.name, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                              style: HoolaType.label(c)),
                        ),
                      ]),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
      if (p.featured.isNotEmpty) ...[
        _sectionHead(c, 'Most used by Indian businesses'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
          child: LayoutBuilder(builder: (context, box) {
            final w = (box.maxWidth - 10) / 2;
            return Wrap(spacing: 10, runSpacing: 10, children: [for (final a in p.featured) SizedBox(width: w, child: _featured(c, a))]);
          }),
        ),
      ],
      if (p.cards.isNotEmpty) _sectionHead(c, 'Browse by category', top: 32),
      for (final g in p.cards) ...[
        _groupHead(c, g),
        HoolaGroup(children: [for (final a in g.top) _row(a)]),
        const SizedBox(height: 14),
      ],
      if (p.tiles.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 8, HoolaSpace.gutter, 0),
          child: LayoutBuilder(builder: (context, box) {
            final w = (box.maxWidth - 10) / 2;
            return Wrap(spacing: 10, runSpacing: 10, children: [for (final g in p.tiles) SizedBox(width: w, child: _tile(c, g))]);
          }),
        ),
    ];
  }

  List<Widget> _searchBody(HoolaColors c) {
    final r = _found;
    if (r == null) return [const _Loading()];
    final apps = [for (final a in (r['apps'] as List? ?? const [])) ConnectApp.from(Map<String, dynamic>.from(a as Map))];
    final groups = [for (final g in (r['groups'] as List? ?? const [])) Map<String, dynamic>.from(g as Map)]
      ..removeWhere((g) => _s(g['id']) == 'more');
    final total = (r['total'] as num?)?.toInt() ?? apps.length;
    if (apps.isEmpty) {
      return [
        if (_finding) const _Loading()
        else
          HoolaEmpty(
            icon: Icons.search_off_rounded,
            title: _s(r['error']).isNotEmpty ? 'Search did not work' : 'No app called "$_q" here',
            sub: _s(r['error']).isNotEmpty
                ? _s(r['error'])
                : 'Try another name, or ask Hoola in the chat. Some tools, like UPI apps and banks, are in Built-in tools below.',
          ),
      ];
    }
    return [
      if (groups.isNotEmpty) ...[
        const HoolaSection('Categories that match'),
        HoolaChips(
          items: [for (final g in groups.take(4)) (_s(g['id']), '${_s(g['name'])}  ${g['count']}')],
          picked: '',
          onPick: (k) => _openGroup(k, _s(groups.firstWhere((g) => _s(g['id']) == k)['name'])),
        ),
      ],
      HoolaSection('Apps', count: total),
      HoolaGroup(children: [for (final a in apps) _row(a)]),
    ];
  }

  Widget _sectionHead(HoolaColors c, String text, {String? action, VoidCallback? onAction, double top = 24}) => Padding(
        padding: EdgeInsets.fromLTRB(HoolaSpace.gutter + 2, top, HoolaSpace.s8, 10),
        child: Row(children: [
          Expanded(child: Semantics(header: true, child: Text(text, style: HoolaType.title(c).copyWith(fontSize: 17)))),
          if (action != null)
            TextButton(
              onPressed: onAction,
              style: TextButton.styleFrom(foregroundColor: c.accent, minimumSize: const Size(48, 44)),
              child: Text(action),
            ),
        ]),
      );

  Widget _groupHead(HoolaColors c, ConnectGroup g) {
    final (fg, bg) = _groupTint(c, g.id);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 2, 6, HoolaSpace.s8, 8),
      child: Row(children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(11)),
          child: Icon(connectGroupIcon(g.id), size: 19, color: fg),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Semantics(header: true, child: Text(g.name, style: HoolaType.title(c))),
            Text(g.connected > 0 ? '${_count(g.count)} apps · ${g.connected} connected' : '${_count(g.count)} apps',
                style: HoolaType.small(c)),
          ]),
        ),
        TextButton(
          onPressed: () => _openGroup(g.id, g.name),
          style: TextButton.styleFrom(foregroundColor: c.accent, minimumSize: const Size(48, 44)),
          child: Text('See all', semanticsLabel: 'See all ${g.name}'),
        ),
      ]),
    );
  }

  Widget _featured(HoolaColors c, ConnectApp a) => Material(
        color: c.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(HoolaRadius.cardLg), side: BorderSide(color: c.line)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => _openSheet(a),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              ConnectLogo(app: app, a: a),
              const SizedBox(height: 10),
              Text(a.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c).copyWith(fontSize: 15)),
              const SizedBox(height: 2),
              SizedBox(
                height: 36,
                child: Text(a.line, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink2)),
              ),
              const SizedBox(height: 8),
              ConnectAction(a: a, busy: _busy.contains(a.toolkit), onTap: () => _act(a)),
            ]),
          ),
        ),
      );

  Widget _tile(HoolaColors c, ConnectGroup g) {
    final (fg, bg) = _groupTint(c, g.id);
    return Material(
      color: c.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(HoolaRadius.cardLg), side: BorderSide(color: c.line)),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openGroup(g.id, g.name),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 60),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(10)),
                child: Icon(connectGroupIcon(g.id), size: 17, color: fg),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(g.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: HoolaType.body(c).copyWith(fontSize: 14, fontWeight: FontWeight.w600)),
                  Text('${_count(g.count)} apps', style: HoolaType.small(c).copyWith(fontSize: 12)),
                ]),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _connectedNote(HoolaColors c, String name) => Padding(
        padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 14, HoolaSpace.gutter, 0),
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 4, 12),
          decoration: BoxDecoration(
              color: c.surface, borderRadius: BorderRadius.circular(HoolaRadius.cardLg), border: Border.all(color: c.line)),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(color: c.okSoft, shape: BoxShape.circle),
              child: Icon(Icons.check_rounded, size: 18, color: c.ok),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('$name is connected', style: HoolaType.title(c).copyWith(fontSize: 15)),
                const SizedBox(height: 2),
                Text('Ask Hoola in the chat to work in $name for you.', style: HoolaType.small(c).copyWith(color: c.ink2)),
              ]),
            ),
            IconButton(
              tooltip: 'Dismiss',
              icon: Icon(Icons.close_rounded, size: 18, color: c.ink3),
              onPressed: () => setState(() => _justConnected.remove(name)),
            ),
          ]),
        ),
      );

  Widget _trust(HoolaColors c) => Padding(
        padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 24, HoolaSpace.gutter + 4, 0),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(padding: const EdgeInsets.only(top: 1), child: Icon(Icons.lock_outline_rounded, size: 16, color: c.ink3)),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'You sign in on the app\'s own page. Hoola never sees your password, and asks before it sends, deletes or pays.',
              style: HoolaType.small(c),
            ),
          ),
        ]),
      );

  Widget _builtIn(HoolaColors c) => Padding(
        padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 20, HoolaSpace.gutter, 0),
        child: Material(
          color: c.sunk,
          borderRadius: BorderRadius.circular(HoolaRadius.card),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: widget.onMore,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(children: [
                Icon(Icons.widgets_outlined, size: 20, color: c.ink2),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Built-in tools', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                    Text('UPI apps, banks, brokers, shops and spend limits', style: HoolaType.small(c)),
                  ]),
                ),
                Icon(Icons.chevron_right_rounded, color: c.ink3),
              ]),
            ),
          ),
        ),
      );
}

// ------------------------------------------------------------------ one group
class ConnectGroupPage extends StatefulWidget {
  const ConnectGroupPage({super.key, required this.app, required this.group, required this.name, this.sort = ''});
  final Santosh app;
  final String group, name, sort;   // group '' + sort connected = every app she joined
  @override
  State<ConnectGroupPage> createState() => _ConnectGroupPageState();
}

class _ConnectGroupPageState extends State<ConnectGroupPage> with WidgetsBindingObserver {
  late String _sort = widget.sort;
  final _search = TextEditingController();
  String _q = '';
  Timer? _debounce;
  List<ConnectApp>? _apps;
  int _total = 0;
  bool _more = false;
  String _err = '';
  final _busy = <String>{};

  Santosh get app => widget.app;
  bool get _mineOnly => widget.group.isEmpty;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && ConnectFlow.waiting.isNotEmpty) _load();
  }

  Future<void> _load({bool more = false}) async {
    final api = app.api;
    final off = more ? (_apps?.length ?? 0) : 0;
    try {
      final r = api == null
          ? (HoolaConnectDebug.apps ?? const {'apps': []})
          : await api.composioApps(q: _q, group: widget.group, sort: _sort, offset: off);
      if (!mounted) return;
      final list = [for (final a in (r['apps'] as List? ?? const [])) ConnectApp.from(Map<String, dynamic>.from(a as Map))];
      for (final a in list) {
        if (a.connected) ConnectFlow.waiting.remove(a.toolkit);
      }
      setState(() {
        _apps = more ? [...?_apps, ...list] : list;
        _total = (r['total'] as num?)?.toInt() ?? _apps!.length;
        _err = '';
        _more = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _apps ??= const [];
        _err = ConnectFlow.plainError(e);
        _more = false;
      });
    }
  }

  void _onSearch(String v) {
    _q = v.trim();
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), _load);
    setState(() {});
  }

  void _changed() {
    if (mounted) setState(() {});
    _load();
  }

  Future<void> _act(ConnectApp a) async {
    if (a.status == 'needs_setup' || a.status == 'not_configured') {
      return ConnectFlow.open(context, app, a, onChanged: _changed);
    }
    if (_busy.contains(a.toolkit)) return;
    setState(() => _busy.add(a.toolkit));
    final err = await ConnectFlow.connect(context, app, a, _changed);
    if (!mounted) return;
    setState(() => _busy.remove(a.toolkit));
    if (err != null && err.isNotEmpty) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final (fg, bg) = _groupTint(c, widget.group);
    final apps = _apps;
    final connected = apps?.where((a) => a.connected).toList() ?? const <ConnectApp>[];
    final rest = apps?.where((a) => !a.connected).toList() ?? const <ConnectApp>[];
    Widget row(ConnectApp a) => ConnectRow(
        app: app, a: a, busy: _busy.contains(a.toolkit),
        onOpen: () => ConnectFlow.open(context, app, a, onChanged: _changed), onAct: () => _act(a));
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(
        backgroundColor: c.bg,
        surfaceTintColor: c.bg,
        elevation: 0,
        foregroundColor: c.ink,
        leading: IconButton(
          tooltip: 'Back',
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
      ),
      body: RefreshIndicator(
        color: c.accent,
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.only(bottom: HoolaSpace.s32),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 2, 0, HoolaSpace.gutter, 16),
              child: Row(children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(16)),
                  child: Icon(_mineOnly ? Icons.check_circle_outline_rounded : connectGroupIcon(widget.group), size: 26, color: fg),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    _BigTitle(widget.name),
                    if (apps != null)
                      Text(_mineOnly ? '$_total apps' : '${_count(_total)} apps${connected.isEmpty ? '' : ' · ${connected.length} connected'}',
                          style: HoolaType.small(c).copyWith(color: c.ink2)),
                  ]),
                ),
              ]),
            ),
            if (!_mineOnly) ...[
              HoolaSearch(controller: _search, hint: 'Search in ${widget.name}', onChanged: _onSearch),
              Padding(
                padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 10, HoolaSpace.gutter, 0),
                child: _Segments(
                  items: const [('', 'Popular'), ('az', 'A–Z'), ('connected', 'Connected')],
                  picked: _sort,
                  onPick: (k) {
                    setState(() {
                      _sort = k;
                      _apps = null;
                    });
                    _load();
                  },
                ),
              ),
            ],
            if (apps == null)
              const _Loading()
            else if (apps.isEmpty)
              HoolaEmpty(
                icon: _err.isNotEmpty ? Icons.cloud_off_rounded : Icons.search_off_rounded,
                title: _err.isNotEmpty
                    ? 'Apps could not be opened'
                    : _sort == 'connected' || _mineOnly
                        ? 'Nothing connected here yet'
                        : 'No app matches',
                sub: _err,
                onRetry: _err.isNotEmpty ? _load : null,
              )
            else ...[
              if (connected.isNotEmpty && _sort != 'connected' && !_mineOnly) ...[
                HoolaSection('Connected', color: c.ok),
                HoolaGroup(children: [for (final a in connected) row(a)]),
              ],
              if (_mineOnly || _sort == 'connected')
                ...[const SizedBox(height: 8), HoolaGroup(children: [for (final a in apps) row(a)])]
              else if (rest.isNotEmpty) ...[
                HoolaSection(_sort == 'az' ? 'A to Z' : 'Popular in ${widget.name}'),
                HoolaGroup(children: [for (final a in rest) row(a)]),
              ],
              if (apps.length < _total)
                Padding(
                  padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 14, HoolaSpace.gutter, 0),
                  child: OutlinedButton(
                    onPressed: _more
                        ? null
                        : () {
                            setState(() => _more = true);
                            _load(more: true);
                          },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: c.ink,
                      side: BorderSide(color: c.lineStrong),
                      shape: const StadiumBorder(),
                      minimumSize: const Size.fromHeight(HoolaSpace.touchMain),
                    ),
                    child: Text(_more ? 'Loading…' : 'Show ${_count(_total - apps.length)} more'),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Popular / A-Z / Connected.
class _Segments extends StatelessWidget {
  const _Segments({required this.items, required this.picked, required this.onPick});
  final List<(String, String)> items;
  final String picked;
  final ValueChanged<String> onPick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(HoolaRadius.pill)),
      child: Row(children: [
        for (final (k, label) in items)
          Expanded(
            child: Semantics(
              button: true,
              selected: k == picked,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () {
                  if (k == picked) return;
                  HapticFeedback.selectionClick();
                  onPick(k);
                },
                child: AnimatedContainer(
                  duration: HoolaMotion.of(context, HoolaMotion.menu),
                  height: 40,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: k == picked ? c.surface : c.sunk,
                    borderRadius: BorderRadius.circular(HoolaRadius.pill),
                    boxShadow: k == picked ? [BoxShadow(color: c.shadow, blurRadius: 3, offset: const Offset(0, 1))] : null,
                  ),
                  child: Text(label,
                      style: HoolaType.label(c).copyWith(fontSize: 13.5, color: k == picked ? c.ink : c.ink2)),
                ),
              ),
            ),
          ),
      ]),
    );
  }
}

// ------------------------------------------------------------------ the app sheet
class _AppSheet extends StatefulWidget {
  const _AppSheet({required this.app, required this.a, required this.onChanged});
  final Santosh app;
  final ConnectApp a;
  final VoidCallback onChanged;
  @override
  State<_AppSheet> createState() => _AppSheetState();
}

class _AppSheetState extends State<_AppSheet> {
  bool _busy = false;
  String _err = '';

  ConnectApp get a => widget.a;

  void _changed() {
    widget.onChanged();
    if (mounted) setState(() {});
  }

  Future<void> _go() async {
    setState(() {
      _busy = true;
      _err = '';
    });
    final err = await ConnectFlow.connect(context, widget.app, a, _changed);
    if (!mounted) return;
    setState(() {
      _busy = false;
      _err = err ?? '';
    });
    if (err == null && (a.connected || ConnectFlow.waiting.contains(a.toolkit))) Navigator.of(context).maybePop();
  }

  Future<void> _remove() async {
    final err = await ConnectFlow.remove(context, widget.app, a, _changed);
    if (!mounted) return;
    if (err != null) {
      setState(() => _err = err);
    } else if (!a.connected) {
      Navigator.of(context).maybePop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final soon = a.status == 'needs_setup' || a.status == 'not_configured';
    final key = a.status == 'needs_key';
    final waiting = ConnectFlow.waiting.contains(a.toolkit) && !a.connected;
    final signIn = a.connected
        ? 'Connected'
        : key
            ? 'Your key'
            : soon
                ? 'Not yet'
                : '${a.name} page';
    Widget fact(String k, String v) => Expanded(
          child: Container(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            decoration: BoxDecoration(
                color: c.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: c.line)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(k, style: HoolaType.small(c).copyWith(fontSize: 12)),
              const SizedBox(height: 2),
              Text(v, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c).copyWith(fontSize: 15)),
            ]),
          ),
        );
    Widget perm(IconData i, Color col, String b, String t) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 9),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(i, size: 18, color: col),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(b, style: HoolaType.body(c).copyWith(fontSize: 14, fontWeight: FontWeight.w500)),
                Text(t, style: HoolaType.small(c).copyWith(color: c.ink2)),
              ]),
            ),
          ]),
        );
    final String label = a.connected
        ? 'Connected'
        : waiting
            ? 'Open the sign-in page again'
            : soon
                ? 'Coming soon'
                : key
                    ? 'Add your ${a.name} key'
                    : a.status == 'pending'
                        ? 'Finish signing in'
                        : 'Connect ${a.name}';
    final String foot = a.connected
        ? 'Ask Hoola in the chat to work in ${a.name}.'
        : soon
            ? 'Hoola has to switch ${a.name} on once before anyone can connect it.'
            : key
                ? 'You type the key on the next screen. Never in the chat.'
                : 'Opens ${a.name}\'s sign-in page. Come back here when you\'re done.';
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: .86,
      minChildSize: .5,
      maxChildSize: .95,
      builder: (context, scroll) => Column(children: [
        Expanded(
          child: ListView(
            controller: scroll,
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 16),
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 5,
                  margin: const EdgeInsets.only(bottom: 18),
                  decoration: BoxDecoration(color: c.lineStrong, borderRadius: BorderRadius.circular(5)),
                ),
              ),
              Row(children: [
                ConnectLogo(app: widget.app, a: a, size: 64, tick: a.connected),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    _BigTitle(a.name),
                    if (a.groupName.isNotEmpty) Text(a.groupName, style: HoolaType.small(c).copyWith(color: c.ink2)),
                  ]),
                ),
              ]),
              if (a.line.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 18),
                  child: Text('Hoola can work in your ${a.name} account: ${a.line[0].toLowerCase()}${a.line.substring(1)}',
                      style: HoolaType.reply(c)),
                ),
              const SizedBox(height: 14),
              Row(children: [
                if (a.tools > 0) ...[fact('Actions', '${a.tools}'), const SizedBox(width: 8)],
                fact('Sign in', signIn),
                const SizedBox(width: 8),
                fact('Price', 'Free'),
              ]),
              const SizedBox(height: 18),
              Semantics(header: true, child: Text('What Hoola will do', style: HoolaType.title(c).copyWith(fontSize: 15))),
              const SizedBox(height: 4),
              perm(Icons.check_rounded, c.ok, 'Read what you let it read',
                  key ? 'Only what your key allows.' : 'You choose what to share on ${a.name}\'s own screen.'),
              perm(Icons.error_outline_rounded, c.warn, 'Ask you before it sends, deletes or pays',
                  'You see a card in the chat and tap yes first.'),
              perm(Icons.lock_outline_rounded, c.ink2, 'Never see your ${a.name} password',
                  'Sign-in is handled by Composio, Hoola\'s secure connector partner.'),
              if (_err.isNotEmpty)
                Container(
                  margin: const EdgeInsets.only(top: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: c.badSoft, borderRadius: BorderRadius.circular(HoolaRadius.tile)),
                  child: Text(_err, style: HoolaType.body(c).copyWith(fontSize: 14, color: c.bad)),
                ),
            ],
          ),
        ),
        Container(
          padding: EdgeInsets.fromLTRB(20, 12, 20, 12 + MediaQuery.of(context).padding.bottom),
          decoration: BoxDecoration(color: c.bg, border: Border(top: BorderSide(color: c.line))),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            if (a.connected)
              Row(children: [
                Expanded(
                  child: Container(
                    height: HoolaSpace.touchMain + 4,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(color: c.okSoft, borderRadius: BorderRadius.circular(HoolaRadius.pill)),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.check_rounded, size: 18, color: c.ok),
                      const SizedBox(width: 6),
                      Text('Connected', style: HoolaType.button(c, color: c.ok)),
                    ]),
                  ),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: _remove,
                  style: TextButton.styleFrom(foregroundColor: c.bad, minimumSize: const Size(88, HoolaSpace.touchMain + 4)),
                  child: const Text('Remove'),
                ),
              ])
            else
              FilledButton.icon(
                onPressed: soon || _busy ? null : _go,
                icon: _busy
                    ? SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                    : Icon(key ? Icons.key_rounded : Icons.open_in_new_rounded, size: 18),
                label: Text(label),
                style: FilledButton.styleFrom(
                  backgroundColor: c.pill,
                  foregroundColor: c.onPill,
                  disabledBackgroundColor: c.sunk,
                  disabledForegroundColor: c.ink3,
                  shape: const StadiumBorder(),
                  minimumSize: const Size.fromHeight(HoolaSpace.touchMain + 4),
                  textStyle: HoolaType.button(c),
                ),
              ),
            const SizedBox(height: 8),
            Text(foot, textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        ),
      ]),
    );
  }
}
