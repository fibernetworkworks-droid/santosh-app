// v0.999.181 GOOGLE CONNECTIONS (owner: "NOW LETS WORK ON GMAIL, SHEET, FORM, DRIVE ETC CONNECTION TO HOOLA" -> the audit
// -> design canvas claude.ai/artifact/HatjjJRPedGgA5zfgq1TBK -> "GO").
//
// Settings > Google: every Google account and app Hoola works in, as the server really holds them (GET /api/google).
//   Your Google accounts  - each with its state; Reconnect on one Google ended; + Add another Google account
//   Everyday apps         - Gmail, Calendar, Drive, Docs, Sheets, Forms, Slides; Connect all = one tap on Google's page
//   More Google apps      - Photos, YouTube, Business Profile, Search Console, each with its own Connect
// An app opens a sheet: which accounts it uses (and which first), Reconnect, Disconnect.
// A connect always lands on THIS Hoola account (the server binds it); Google sends the phone back with
// santosh://google?ok=..&got=..&miss=.. and this screen shows what was granted and what was left unticked.
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_tabs.dart';

/// Open Settings > Google from anywhere (Settings row, chat cards).
Future<void> hoolaOpenGoogle(BuildContext context, Santosh app) => Navigator.of(context)
    .push(MaterialPageRoute<void>(builder: (_) => HoolaTheme(appearance: app.appearance, child: HoolaGoogle(app: app))));

const _core = ['gmail', 'calendar', 'drive', 'docs', 'sheets', 'forms', 'slides'];

// v0.999.182 Google's own product logos (assets/google/<key>.png), never redrawn
const Map<String, String> _look = {
  'gmail': 'Gmail',
  'calendar': 'Calendar',
  'drive': 'Drive',
  'docs': 'Docs',
  'sheets': 'Sheets',
  'forms': 'Forms',
  'slides': 'Slides',
  'photos': 'Photos',
  'youtube': 'YouTube',
  'business': 'Business Profile',
  'searchconsole': 'Search Console',
};

String _name(String k) => _look[k] ?? k;

Widget _tile(String k, {double size = 40}) {
  final logo = _look.containsKey(k) ? k : 'google';
  return Container(
    width: size,
    height: size,
    alignment: Alignment.center,
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(HoolaRadius.tile),
      border: Border.all(color: Colors.black.withOpacity(.08)),
    ),
    child: Image.asset('assets/google/$logo.png', width: size * .62, height: size * .62, fit: BoxFit.contain),
  );
}

List<String> _strs(dynamic v) => v is List ? v.map((e) => '$e').toList() : const [];

/// Ask Google for these apps (her account picked, the "unverified" note shown), then open Google's page.
Future<void> hoolaGoogleConnect(BuildContext context, Santosh app, List<String> apps, {String hint = ''}) async {
  final c = HoolaColors.of(context);
  final keys = apps.isEmpty || apps.contains('core') ? _core : apps;
  final go = await showModalBottomSheet<bool>(
    context: context,
    backgroundColor: c.surface,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(hint.isNotEmpty ? 'Connect $hint' : 'Connect Google', style: HoolaType.heading(c)),
          const SizedBox(height: 8),
          Text('Hoola will ask Google for ${keys.length > 1 ? 'these apps' : 'this app'}. You can untick any of them on Google’s page.',
              style: HoolaType.body(c).copyWith(color: c.ink2)),
          const SizedBox(height: 14),
          Wrap(spacing: 14, runSpacing: 10, children: [
            for (final k in keys)
              Row(mainAxisSize: MainAxisSize.min, children: [_tile(k, size: 30), const SizedBox(width: 8), Text(_name(k), style: HoolaType.body(c))]),
          ]),
          const SizedBox(height: 14),
          Text('Google may first say it hasn’t checked Hoola yet. Tap Advanced, then Go to Hoola.', style: HoolaType.small(c)),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(
                backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder(),
                minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Continue to Google'),
          ),
          const SizedBox(height: 6),
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Cancel'),
          ),
        ]),
      ),
    ),
  );
  if (go != true) return;
  try {
    final url = await app.api!.googleConnectUrl(apps.isEmpty || apps.contains('core') ? const ['core'] : apps, hint: hint);
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  } catch (e) {
    if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
  }
}

class HoolaGoogle extends StatefulWidget {
  const HoolaGoogle({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaGoogle> createState() => _HoolaGoogleState();
}

class _HoolaGoogleState extends State<HoolaGoogle> {
  Map<String, dynamic>? _g;
  String _err = '';
  int _seenTick = 0;

  @override
  void initState() {
    super.initState();
    _seenTick = widget.app.googleTick;
    widget.app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    widget.app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (widget.app.googleTick == _seenTick) return;
    _seenTick = widget.app.googleTick;
    final r = widget.app.googleResult;
    widget.app.googleResult = null;
    _load().then((_) {
      if (mounted && r != null && r['ok'] == '1') _result(r);
    });
  }

  Future<void> _load() async {
    try {
      final g = await widget.app.api!.googleHub();
      if (mounted) {
        setState(() {
          _g = g;
          _err = '';
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  List<Map<String, dynamic>> get _accounts =>
      (_g?['accounts'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  List<Map<String, dynamic>> get _apps =>
      (_g?['apps'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  void _toast(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Widget _state(HoolaColors c, String st) {
    final (t, col) = switch (st) {
      'ok' => ('Connected', c.ok),
      'expired' => ('Reconnect', c.warn),
      _ => ('Not connected', c.ink3),
    };
    return Text(t, style: HoolaType.small(c).copyWith(color: col, fontWeight: FontWeight.w500));
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final accts = _accounts, apps = _apps;
    final core = apps.where((a) => a['group'] == 'core').toList(), more = apps.where((a) => a['group'] == 'more').toList();
    final allCore = core.isNotEmpty && core.every((a) => a['state'] == 'ok');
    final children = <Widget>[
      HoolaTabHeader(title: 'Google', sub: 'Gmail, Calendar, Drive and more, worked by Hoola'),
      if (_err.isNotEmpty)
        Padding(padding: const EdgeInsets.all(HoolaSpace.gutter), child: Text(_err, style: HoolaType.body(c).copyWith(color: c.bad))),
      if (_g == null && _err.isEmpty) const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())),
      if (_g != null) ...[
        const HoolaSection('Your Google accounts'),
        HoolaGroup(children: [
          for (final a in accts)
            HoolaRow(
              title: '${a['email']}${a['first'] == true && accts.length > 1 ? ' · used first' : ''}',
              sub: a['state'] == 'expired'
                  ? 'Google ended Hoola’s access. Apps on it have stopped.'
                  : (_strs(a['apps']).map(_name).join(', ').isEmpty ? 'No apps yet' : _strs(a['apps']).map(_name).join(', ')),
              tile: CircleAvatar(
                radius: 20,
                backgroundColor: (a['state'] == 'expired' ? c.warn : c.accent).withOpacity(.14),
                child: Text('${a['email']}'.isEmpty ? '?' : '${a['email']}'[0].toUpperCase(),
                    style: HoolaType.title(c).copyWith(color: a['state'] == 'expired' ? c.warn : c.accent)),
              ),
              trailing: a['state'] == 'expired'
                  ? FilledButton(
                      onPressed: () => hoolaGoogleConnect(context, widget.app,
                          _strs(a['apps']).isEmpty ? const ['core'] : _strs(a['apps']), hint: '${a['email']}'),
                      style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder()),
                      child: const Text('Reconnect'))
                  : Icon(Icons.chevron_right_rounded, color: c.ink3),
              onTap: () => _accountSheet(a),
            ),
          HoolaRow(
            title: accts.isEmpty ? 'Connect Google' : 'Add another Google account',
            icon: Icons.add_rounded,
            tint: c.accent,
            onTap: () => hoolaGoogleConnect(context, widget.app, const ['core']),
          ),
        ]),
        if (accts.isEmpty && '${_g!['signin'] ?? ''}'.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 8, HoolaSpace.gutter, 0),
            child: Text('You signed in with ${_g!['signin']}. Signing in only shares your name and email, so the apps still need connecting.',
                style: HoolaType.small(c)),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, HoolaSpace.s20, HoolaSpace.s8, HoolaSpace.s8),
          child: Row(children: [
            Expanded(child: Text('Everyday apps', style: HoolaType.label(c).copyWith(fontWeight: FontWeight.w600))),
            if (!allCore)
              TextButton(onPressed: () => hoolaGoogleConnect(context, widget.app, const ['core']), child: const Text('Connect all')),
          ]),
        ),
        HoolaGroup(children: [
          for (final a in core)
            HoolaRow(
              title: '${a['name']}',
              sub: '${a['does']}',
              tile: _tile('${a['key']}'),
              trailing: _state(c, '${a['state']}'),
              onTap: () => _appSheet(a),
            ),
        ]),
        const HoolaSection('More Google apps'),
        HoolaGroup(children: [
          for (final a in more)
            HoolaRow(
              title: '${a['name']}',
              sub: '${a['does']}',
              tile: _tile('${a['key']}'),
              trailing: a['state'] == 'none'
                  ? OutlinedButton(
                      onPressed: () => hoolaGoogleConnect(context, widget.app, ['${a['key']}']),
                      style: OutlinedButton.styleFrom(foregroundColor: c.ink, shape: const StadiumBorder()),
                      child: const Text('Connect'))
                  : _state(c, '${a['state']}'),
              onTap: () => _appSheet(a),
            ),
        ]),
        Padding(
          padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, HoolaSpace.s16, HoolaSpace.gutter, 0),
          child: Text(
              'Hoola never sends, shares, deletes or posts anything without your yes. Disconnecting an account also removes Hoola’s access in your Google account.',
              style: HoolaType.small(c)),
        ),
      ],
    ];
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(backgroundColor: c.bg, surfaceTintColor: c.bg, foregroundColor: c.ink, elevation: 0, toolbarHeight: 48),
      body: SafeArea(
        top: false,
        child: RefreshIndicator(
          color: c.accent,
          onRefresh: _load,
          child: ListView(physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.only(bottom: HoolaSpace.s32), children: children),
        ),
      ),
    );
  }

  Future<T?> _sheet<T>(Widget Function(BuildContext ctx, HoolaColors c) body) {
    final c = HoolaColors.of(context);
    return showModalBottomSheet<T>(
      context: context,
      backgroundColor: c.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(child: Padding(padding: const EdgeInsets.fromLTRB(20, 18, 20, 12), child: body(ctx, c))),
    );
  }

  Future<bool> _sure(String title, String body) async {
    final ok = await _sheet<bool>((ctx, c) => Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(title, style: HoolaType.heading(c)),
          const SizedBox(height: 8),
          Text(body, style: HoolaType.body(c).copyWith(color: c.ink2)),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: c.bad, foregroundColor: c.onAccent, shape: const StadiumBorder(),
                minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Disconnect'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Cancel'),
          ),
        ]));
    return ok == true;
  }

  void _appSheet(Map<String, dynamic> a) {
    final key = '${a['key']}', name = '${a['name']}';
    final accts = [for (final e in _strs(a['working'])) (e, 'ok'), for (final e in _strs(a['expired'])) (e, 'expired')];
    var first = '${a['first'] ?? ''}';
    _sheet<void>((ctx, c) => StatefulBuilder(builder: (ctx, setS) {
          return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              _tile(key, size: 44),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name, style: HoolaType.heading(c)),
                  Text('${a['does']}', style: HoolaType.small(c)),
                ]),
              ),
            ]),
            const SizedBox(height: 16),
            if (accts.isEmpty) Text('$name is not connected yet.', style: HoolaType.body(c).copyWith(color: c.ink2)),
            for (final (e, st) in accts)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Material(
                  color: st == 'expired' ? c.warnSoft : c.sunk,
                  borderRadius: BorderRadius.circular(HoolaRadius.card),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(4, 6, 10, 6),
                    child: Row(children: [
                      if (accts.length > 1)
                        Radio<String>(
                          value: e,
                          groupValue: first,
                          onChanged: (v) async {
                            if (v == null) return;
                            setS(() => first = v);
                            try {
                              await widget.app.api!.googleFirst(key, v);
                              a['first'] = v;
                              _toast('$name now uses $v first.');
                            } catch (x) {
                              _toast('$x');
                            }
                          },
                        )
                      else
                        const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(e, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                          Text(st == 'expired' ? 'Google ended Hoola’s access' : (accts.length > 1 && e == first ? 'Used first' : 'Working'),
                              style: HoolaType.small(c).copyWith(color: st == 'expired' ? c.warn : c.ink3)),
                        ]),
                      ),
                      if (st == 'expired')
                        TextButton(
                            onPressed: () {
                              Navigator.pop(ctx);
                              hoolaGoogleConnect(context, widget.app, [key], hint: e);
                            },
                            child: const Text('Reconnect'))
                      else
                        TextButton(
                          style: TextButton.styleFrom(foregroundColor: c.bad),
                          onPressed: () async {
                            Navigator.pop(ctx);
                            if (!await _sure('Disconnect $name?',
                                'Hoola stops using $name for $e. Your other apps stay connected. To remove all of Hoola’s access, disconnect the whole account.')) {
                              return;
                            }
                            try {
                              await widget.app.api!.googleDisconnect(e, app: key);
                              _toast('$name disconnected.');
                              await _load();
                            } catch (x) {
                              _toast('$x');
                            }
                          },
                          child: const Text('Disconnect'),
                        ),
                    ]),
                  ),
                ),
              ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: () {
                Navigator.pop(ctx);
                hoolaGoogleConnect(context, widget.app, [key]);
              },
              style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder(),
                  minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
              child: Text(accts.isEmpty ? 'Connect $name' : 'Connect another account'),
            ),
          ]);
        }));
  }

  void _accountSheet(Map<String, dynamic> a) {
    final email = '${a['email']}';
    _sheet<void>((ctx, c) => Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(email, style: HoolaType.heading(c)),
          Text(a['first'] == true ? 'Used first by every app' : 'Google account', style: HoolaType.small(c)),
          const SizedBox(height: 14),
          Wrap(spacing: 12, runSpacing: 10, children: [
            for (final k in _strs(a['apps']))
              Row(mainAxisSize: MainAxisSize.min, children: [_tile(k, size: 30), const SizedBox(width: 8), Text(_name(k), style: HoolaType.body(c))]),
          ]),
          const SizedBox(height: 18),
          OutlinedButton(
            onPressed: () {
              Navigator.pop(ctx);
              hoolaGoogleConnect(context, widget.app, const ['core'], hint: email);
            },
            style: OutlinedButton.styleFrom(foregroundColor: c.ink, shape: const StadiumBorder(),
                minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Add apps'),
          ),
          const SizedBox(height: 8),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: c.bad, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            onPressed: () async {
              Navigator.pop(ctx);
              if (!await _sure('Disconnect this Google account?',
                  'Hoola stops using every app on $email, and its access is removed in your Google account too.')) {
                return;
              }
              try {
                await widget.app.api!.googleDisconnect(email);
                _toast('Google account disconnected.');
                await _load();
              } catch (x) {
                _toast('$x');
              }
            },
            child: const Text('Disconnect this account'),
          ),
        ]));
  }

  void _result(Map<String, String> r) {
    final got = (r['got'] ?? '').split(',').where((x) => x.isNotEmpty).toList();
    final miss = (r['miss'] ?? '').split(',').where((x) => x.isNotEmpty).toList();
    _sheet<void>((ctx, c) => Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Google is connected', style: HoolaType.heading(c)),
          const SizedBox(height: 12),
          for (final k in got)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(children: [
                _tile(k, size: 30),
                const SizedBox(width: 10),
                Expanded(child: Text(_name(k), style: HoolaType.body(c))),
                Icon(Icons.check_rounded, color: c.ok),
              ]),
            ),
          for (final k in miss)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(children: [
                _tile(k, size: 30),
                const SizedBox(width: 10),
                Expanded(child: Text('${_name(k)}: you left it unticked', style: HoolaType.body(c).copyWith(color: c.ink2))),
                TextButton(
                    onPressed: () {
                      Navigator.pop(ctx);
                      hoolaGoogleConnect(context, widget.app, [k]);
                    },
                    child: const Text('Allow')),
              ]),
            ),
          const SizedBox(height: 10),
          FilledButton(
            onPressed: () => Navigator.pop(ctx),
            style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder(),
                minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Done'),
          ),
        ]));
  }
}

/// One line for the Settings row: "6 apps working · 1 account needs reconnecting".
String hoolaGoogleLine(Map<String, dynamic>? g) {
  if (g == null) return 'Gmail, Calendar, Drive and more';
  final apps = (g['apps'] as List? ?? const []).whereType<Map>().toList();
  final ok = apps.where((a) => a['state'] == 'ok').length;
  final bad = (g['accounts'] as List? ?? const []).whereType<Map>().where((a) => a['state'] == 'expired').length;
  final head = ok == 0 ? 'Not connected' : '$ok app${ok == 1 ? '' : 's'} working';
  return bad == 0 ? head : '$head · $bad account${bad == 1 ? '' : 's'} needs reconnecting';
}
