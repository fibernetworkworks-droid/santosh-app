// v0.941 HOOLA CODE ON YOUR SERVER (owner: "Now how hoola code will take access of user vps .. give a perfect simple
// and secure way in hoola app") - design canvas claude.ai/artifact/B9nNvYXJTyMwH8mTfCJep5.
// Her server calls Hoola (an outbound long-poll), so no port is opened and no password or SSH key is kept. The helper
// on her server runs as its own unprivileged `hoola` user; the access rules live BOTH on the server and in that
// helper. Three screens: Servers (list + connect), Pair (one line + 6-digit code), one Server (access + activity).
// Routes: /api/devsahayak/servers*. Every change she runs is her tap; the server re-checks it.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../native.dart';
import '../../state.dart';
import '../hoola_theme.dart';
import 'code_kit.dart';

String _vpsBase(Santosh app) {
  final b = (app.api?.baseUrl ?? '').trim();
  return b.isEmpty ? 'https://hoola.ainewtika.com' : b.replaceAll(RegExp(r'/+$'), '');
}

// ============================================================================================== the list + connect
class CodeServersPage extends StatefulWidget {
  const CodeServersPage({super.key, required this.app});
  final Santosh app;
  @override
  State<CodeServersPage> createState() => _CodeServersPageState();
}

class _CodeServersPageState extends State<CodeServersPage> {
  List<Map<String, dynamic>> _servers = [];
  bool _loading = true, _failed = false, _loaded = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (_failed) {
      setState(() {
        _failed = false;
        _loading = true;
      });
    }
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/servers', quiet: true);
    if (!mounted) return;
    setState(() {
      if (r != null) {
        // a failed reload keeps the list it had; only a first load that failed shows the error
        _servers = cl(r['servers']);
        _loaded = true;
      } else if (!_loaded) {
        _failed = true;
      }
      _loading = false;
    });
  }

  Future<void> _connect() async {
    final ctl = TextEditingController(text: 'Main VPS');
    final c = HoolaColors.of(context);
    final name = await codeSheet<String>(context, widget.app,
        title: 'Connect a server',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('Your server calls Hoola. No port is opened, no password or key is kept, and the helper runs as its own user.',
                  style: codeSans(c, size: 13.5, color: c.ink2)),
              const SizedBox(height: 12),
              CodeField(controller: ctl, label: 'Name it'),
              CodeMain('Get my install line', onTap: () => Navigator.pop(ctx, ctl.text.trim())),
            ]));
    final nm = (name ?? '').trim();
    ctl.dispose();
    if (nm.isEmpty || !mounted) return;
    final r = await codeCall(context, widget.app, 'POST', '/api/devsahayak/servers/pair', body: {'name': nm}, quiet: true);
    if (!mounted || r == null) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodePairPage(app: widget.app, pair: r))));
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(title: 'Servers', line: false),
          Expanded(
            child: _failed
                ? CodeLoadFailed(onRetry: _load)
                : _loading
                ? const Center(child: CodeRing(size: 22))
                : RefreshIndicator(
                    onRefresh: _load,
                    color: c.ink,
                    child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: [
                      if (_servers.isEmpty) _empty(c),
                      for (final s in _servers) ...[_serverRow(c, s), const SizedBox(height: 10)],
                      const SizedBox(height: 8),
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: CodeOutline('Connect a server', icon: Icons.add_rounded, onTap: _connect),
                      ),
                      const SizedBox(height: 16),
                      _safetyNote(c),
                    ]),
                  ),
          ),
        ]),
      ),
    );
  }

  Widget _empty(HoolaColors c) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 40, 4, 24),
        child: Column(children: [
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(color: c.pill, borderRadius: BorderRadius.circular(30)),
            child: Icon(Icons.dns_rounded, color: c.onPill, size: 28),
          ),
          const SizedBox(height: 16),
          Text('Let Hoola work on your server', style: codeSans(c, size: 18, weight: FontWeight.w600), textAlign: TextAlign.center),
          const SizedBox(height: 8),
          Text('Deploy, read logs, restart your app and find out why something broke. You stay in charge of every change.',
              style: codeSans(c, size: 14, color: c.ink2, height: 1.5), textAlign: TextAlign.center),
        ]),
      );

  Widget _serverRow(HoolaColors c, Map<String, dynamic> s) {
    final online = s['online'] == true;
    return CodeCard(
      onTap: () async {
        await Navigator.of(context).push(MaterialPageRoute<void>(
            builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodeServerPage(app: widget.app, id: cs(s['id'])))));
        await _load();
      },
      child: Row(children: [
        Container(width: 10, height: 10, margin: const EdgeInsets.only(right: 12),
            decoration: BoxDecoration(color: online ? c.ok : c.ink3, borderRadius: BorderRadius.circular(5))),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(cs(s['name']), style: codeSans(c, size: 15.5, weight: FontWeight.w600)),
            const SizedBox(height: 2),
            Text([online ? 'Online' : 'Not connected', cs(s['line'])].where((e) => e.isNotEmpty).join(' · '),
                style: codeSans(c, size: 12.5, color: c.ink3)),
          ]),
        ),
        Icon(Icons.chevron_right_rounded, color: c.ink3, size: 20),
      ]),
    );
  }

  Widget _safetyNote(HoolaColors c) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('How it stays safe', style: codeSans(c, size: 13, weight: FontWeight.w600, color: c.ink)),
          const SizedBox(height: 8),
          for (final t in const [
            'Your server calls Hoola. No port opened, no password, no SSH key kept by Hoola.',
            'The helper runs as its own user, not root.',
            'Secret files (.env, keys) are never read.',
            'Dangerous commands are always refused and can never be approved.',
            'Every command is logged on your server and in the app.',
            'Disconnect removes everything.',
          ])
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(Icons.check_rounded, size: 15, color: c.ok),
                const SizedBox(width: 8),
                Expanded(child: Text(t, style: codeSans(c, size: 13, color: c.ink2, height: 1.4))),
              ]),
            ),
        ]),
      );
}

// ============================================================================================== pair: one line + code
class CodePairPage extends StatefulWidget {
  const CodePairPage({super.key, required this.app, required this.pair});
  final Santosh app;
  final Map<String, dynamic> pair;
  @override
  State<CodePairPage> createState() => _CodePairPageState();
}

class _CodePairPageState extends State<CodePairPage> {
  Timer? _poll;
  bool _copied = false;
  int _left = 600;

  @override
  void initState() {
    super.initState();
    _left = ci(widget.pair['ends_in_s']);
    _poll = Timer.periodic(const Duration(seconds: 3), (_) => _check());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  String get _id => cs(widget.pair['id']);
  String get _code => cs(widget.pair['code']);
  String get _line => cs(widget.pair['install']);

  Future<void> _check() async {
    if (!mounted) return;
    setState(() => _left = (_left - 3).clamp(0, 3600));
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/servers/$_id', quiet: true);
    if (!mounted || r == null) return;
    if (r['online'] == true) {
      _poll?.cancel();
      Navigator.of(context).pushReplacement(MaterialPageRoute<void>(
          builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: CodeServerPage(app: widget.app, id: _id, justConnected: true))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final mins = _left ~/ 60, secs = _left % 60;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(title: cs(widget.pair['name']).isNotEmpty ? cs(widget.pair['name']) : 'Connect a server', line: false),
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 28), children: [
              Text('Paste this on your server', style: codeSans(c, size: 18, weight: FontWeight.w600)),
              const SizedBox(height: 8),
              Text('Open your server’s terminal (where you type pm2 or git pull) and paste this one line.',
                  style: codeSans(c, size: 14, color: c.ink2, height: 1.5)),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: c.pill, borderRadius: BorderRadius.circular(14)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  SelectableText(_line, style: codeMono(c, size: 12.5, color: c.onPill)),
                  const SizedBox(height: 12),
                  Row(children: [
                    CodeChip(_copied ? 'Copied' : 'Copy', icon: _copied ? Icons.check_rounded : Icons.copy_rounded, on: true,
                        onTap: () async {
                      await Clipboard.setData(ClipboardData(text: _line));
                      if (mounted) setState(() => _copied = true);
                    }),
                    const SizedBox(width: 8),
                    CodeChip('See what it installs', icon: Icons.open_in_new_rounded,
                        onTap: () => Native.openExternal(url: '${_vpsBase(widget.app)}/vps/install')),
                  ]),
                ]),
              ),
              const SizedBox(height: 10),
              Row(children: [
                Expanded(child: Text('Code ${_code.substring(0, 3)} ${_code.substring(3)} · works once',
                    style: codeSans(c, size: 12.5, color: c.ink3))),
                Text('ends in $mins:${secs.toString().padLeft(2, '0')}', style: codeSans(c, size: 12.5, color: c.ink3)),
              ]),
              const SizedBox(height: 18),
              CodeCard(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('What this line does', style: codeSans(c, size: 13, weight: FontWeight.w600, color: c.ink2)),
                  const SizedBox(height: 6),
                  Text('Makes a user called hoola, adds a small helper that starts with your server, and connects it to your Hoola. Nothing else on your server changes.',
                      style: codeSans(c, size: 14, height: 1.5)),
                ]),
              ),
              const SizedBox(height: 18),
              Row(children: [
                const CodeRing(size: 20),
                const SizedBox(width: 10),
                Text('Waiting for your server…', style: codeSans(c, size: 15, color: c.ink2)),
              ]),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ============================================================================================== one server
class CodeServerPage extends StatefulWidget {
  const CodeServerPage({super.key, required this.app, required this.id, this.justConnected = false});
  final Santosh app;
  final String id;
  final bool justConnected;
  @override
  State<CodeServerPage> createState() => _CodeServerPageState();
}

class _CodeServerPageState extends State<CodeServerPage> {
  Map<String, dynamic>? _s;
  bool _busy = false, _failed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (_failed) setState(() => _failed = false);
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/servers/${widget.id}', quiet: true);
    if (!mounted) return;
    if (r != null) {
      setState(() => _s = r);
    } else if (_s == null) {
      setState(() => _failed = true);
    }
  }

  Future<void> _put(Map<String, dynamic> body) async {
    if (_busy) return;
    setState(() => _busy = true);
    await codeCall(context, widget.app, 'PUT', '/api/devsahayak/servers/${widget.id}', body: body, quiet: true);
    if (!mounted) return;
    setState(() => _busy = false);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final s = _s;
    final online = s?['online'] == true;
    final access = cs(s?['access']).isEmpty ? 'ask' : cs(s?['access']);
    final folders = List<String>.from((s?['folders'] as List?)?.map((e) => '$e') ?? const []);
    final admin = List<String>.from((s?['admin_cmds'] as List?)?.map((e) => '$e') ?? const []);
    final activity = cl(s?['activity']);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(title: cs(s?['name']).isEmpty ? 'Server' : cs(s?['name']), line: false),
          Expanded(
            child: s == null
                ? (_failed ? CodeLoadFailed(onRetry: _load) : const Center(child: CodeRing(size: 22)))
                : RefreshIndicator(
                    onRefresh: _load,
                    color: c.ink,
                    child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: [
                      if (widget.justConnected)
                        _connectedBanner(c, s)
                      else
                        Row(children: [
                          Container(width: 10, height: 10, margin: const EdgeInsets.only(right: 8),
                              decoration: BoxDecoration(color: online ? c.ok : c.ink3, borderRadius: BorderRadius.circular(5))),
                          Text(online ? 'Online' : 'Not connected', style: codeSans(c, size: 15, weight: FontWeight.w600)),
                          if (cs(s['line']).isNotEmpty) ...[
                            const SizedBox(width: 6),
                            Expanded(child: Text('· ${cs(s['line'])}', style: codeSans(c, size: 12.5, color: c.ink3), maxLines: 1, overflow: TextOverflow.ellipsis)),
                          ],
                        ]),
                      const CodeSection('What may Hoola do here?'),
                      _accessChoice(c, 'look', 'Look only', '', 'Reads logs, status, disk and files in your folders. Changes nothing.', access),
                      _accessChoice(c, 'ask', 'Ask me first', 'Recommended', 'Every command that changes something waits for your tap, with the exact command shown.', access),
                      _accessChoice(c, 'trust', 'Trust my folders', '', 'Safe steps like git pull, tests and restarting your app run on their own inside your folders. Anything else asks.', access),
                      const CodeSection('Folders Hoola may work in'),
                      _folderBox(c, folders),
                      const CodeSection('Admin commands it may ask for'),
                      _adminBox(c, admin),
                      CodeSection('Activity', trailing: Text('Also kept on your server', style: codeSans(c, size: 12, color: c.ink3))),
                      _activityBox(c, activity),
                      const SizedBox(height: 14),
                      CodeSwitchRow(
                          label: 'Switch off when unused',
                          sub: 'After ${ci(s['auto_off_days'])} days with no session',
                          value: ci(s['auto_off_days']) > 0,
                          onChanged: _busy ? null : (v) => _put({'auto_off_days': v ? 7 : 0}),
                          last: true),
                      const SizedBox(height: 18),
                      CodeOutline('Disconnect this server', icon: Icons.link_off_rounded, color: c.bad, onTap: _disconnect),
                    ]),
                  ),
          ),
        ]),
      ),
    );
  }

  Widget _connectedBanner(HoolaColors c, Map<String, dynamic> s) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.okSoft, borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          Container(width: 36, height: 36, decoration: BoxDecoration(color: c.ok, borderRadius: BorderRadius.circular(18)),
              child: Icon(Icons.check_rounded, color: c.onPill, size: 20)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Connected', style: codeSans(c, size: 15, weight: FontWeight.w600, color: c.ok)),
              Text(cs(s['line']), style: codeSans(c, size: 12.5, color: c.ink2)),
            ]),
          ),
        ]),
      );

  Widget _accessChoice(HoolaColors c, String id, String name, String tag, String line, String cur) {
    final on = id == cur;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: on ? c.accentSoft : c.surface,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: _busy ? null : () => _put({'access': id}),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: on ? c.accent : c.line, width: on ? 1.4 : 1),
            ),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(on ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded,
                  size: 20, color: on ? c.accent : c.ink3),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Text(name, style: codeSans(c, size: 15, weight: FontWeight.w600)),
                    if (tag.isNotEmpty) ...[const SizedBox(width: 8), Text(tag, style: codeSans(c, size: 12, weight: FontWeight.w500, color: c.accent))],
                  ]),
                  const SizedBox(height: 3),
                  Text(line, style: codeSans(c, size: 13, color: c.ink2, height: 1.4)),
                ]),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _folderBox(HoolaColors c, List<String> folders) => CodeCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (folders.isEmpty) Text('None yet. Add the folders your app lives in.', style: codeSans(c, size: 13.5, color: c.ink3)),
          for (final f in folders)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(children: [
                Expanded(child: Text(f, style: codeMono(c, size: 13))),
                CodeIconButton(icon: Icons.close_rounded, size: 18, label: 'Remove',
                    onTap: _busy ? null : () => _put({'folders': folders.where((x) => x != f).toList()})),
              ]),
            ),
          const SizedBox(height: 4),
          CodeOutline('Add a folder', icon: Icons.add_rounded, height: 44, onTap: () => _addFolder(folders)),
        ]),
      );

  Future<void> _addFolder(List<String> folders) async {
    final ctl = TextEditingController();
    final ok = await codeSheet<bool>(context, widget.app,
        title: 'Add a folder',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              CodeField(controller: ctl, label: 'Folder on your server', hint: '~/apps/santosh-core', mono: true),
              CodeMain('Add', onTap: () => Navigator.pop(ctx, true)),
            ]));
    final v = ctl.text.trim();
    ctl.dispose();
    if (ok == true && v.isNotEmpty && mounted) await _put({'folders': [...folders, v]});
  }

  Widget _adminBox(HoolaColors c, List<String> admin) => CodeCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          for (final a in admin)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(children: [
                Expanded(child: Text(a, style: codeMono(c, size: 13))),
                CodeIconButton(icon: Icons.close_rounded, size: 18, label: 'Remove',
                    onTap: _busy ? null : () => _put({'admin_cmds': admin.where((x) => x != a).toList()})),
              ]),
            ),
          if (admin.isEmpty) Text('None. Add a root command only if your app needs it (like restarting a service).', style: codeSans(c, size: 13, color: c.ink3, height: 1.4)),
          const SizedBox(height: 4),
          CodeOutline('Add an admin command', icon: Icons.add_rounded, height: 44, onTap: () => _addAdmin(admin)),
          const SizedBox(height: 8),
          Text('Each one still asks you first, and only runs as root if you grant it on the server.', style: codeSans(c, size: 12, color: c.ink3, height: 1.4)),
        ]),
      );

  Future<void> _addAdmin(List<String> admin) async {
    final ctl = TextEditingController();
    final ok = await codeSheet<bool>(context, widget.app,
        title: 'Add an admin command',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              CodeField(controller: ctl, label: 'Command', hint: 'pm2 restart santosh', mono: true),
              CodeMain('Add', onTap: () => Navigator.pop(ctx, true)),
            ]));
    final v = ctl.text.trim();
    ctl.dispose();
    if (ok == true && v.isNotEmpty && mounted) await _put({'admin_cmds': [...admin, v]});
  }

  Widget _activityBox(HoolaColors c, List<Map<String, dynamic>> rows) => CodeCard(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Column(children: [
          if (rows.isEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 10), child: Text('Nothing yet.', style: codeSans(c, size: 13.5, color: c.ink3))),
          for (var i = 0; i < rows.length && i < 20; i++)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(border: i == 0 ? null : Border(top: BorderSide(color: c.sunk))),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(cs(rows[i]['cmd']), style: codeMono(c, size: 13), maxLines: 1, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 2),
                    Text(cs(rows[i]['who']), style: codeSans(c, size: 12, color: _whoColor(c, cs(rows[i]['status'])))),
                  ]),
                ),
              ]),
            ),
        ]),
      );

  Color _whoColor(HoolaColors c, String status) {
    if (status == 'done' || status == 'allowed') return c.ok;
    if (status == 'refused' || status == 'no' || status == 'failed') return c.bad;
    return c.ink3;
  }

  Future<void> _disconnect() async {
    final c = HoolaColors.of(context);
    final ok = await codeSheet<bool>(context, widget.app,
        title: 'Disconnect ${cs(_s?['name'])}?',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('Hoola stops at once. The helper and the hoola user are removed from your server within a minute. If it is offline, run this there:',
                  style: codeSans(c, size: 14, color: c.ink2, height: 1.5)),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(10)),
                child: SelectableText('sudo hoola-agent remove', style: codeMono(c, size: 13)),
              ),
              const SizedBox(height: 14),
              CodeMain('Disconnect', onTap: () => Navigator.pop(ctx, true)),
            ]));
    if (ok == true && mounted) {
      await codeCall(context, widget.app, 'POST', '/api/devsahayak/servers/${widget.id}/disconnect');
      if (mounted) Navigator.of(context).maybePop();
    }
  }
}

// ============================================================================================== the approval card
// Shown in a session when a `server` step is waiting for her tap. money never moves here; it is a command card.
class CodeServerCard extends StatefulWidget {
  const CodeServerCard({super.key, required this.app, required this.step});
  final Santosh app;
  final Map<String, dynamic> step;
  @override
  State<CodeServerCard> createState() => _CodeServerCardState();
}

class _CodeServerCardState extends State<CodeServerCard> {
  String _done = '';
  bool _busy = false;

  Future<void> _decide(String choice) async {
    if (_busy) return;
    setState(() => _busy = true);
    final sid = cs(widget.step['server_id']);
    final cid = cs(widget.step['id']);
    final r = await codeCall(context, widget.app, 'POST',
        '/api/devsahayak/servers/$sid/cmds/$cid/decide', body: {'choice': choice}, quiet: true);
    if (!mounted) return;
    setState(() {
      _busy = false;
      _done = choice == 'no' ? 'Not run' : (r?['state'] == 'allowed' ? 'Running on your server' : cs(r?['state']));
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final st = widget.step;
    final state = cs(st['state']);
    if (state == 'refused') {
      return CodeCard(
        edge: c.bad,
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.block_rounded, size: 18, color: c.bad),
          const SizedBox(width: 10),
          Expanded(child: Text('Your server refused this — it ${cs(st['reason'])}.', style: codeSans(c, size: 14, height: 1.45))),
        ]),
      );
    }
    if (state != 'waiting') return const SizedBox.shrink();
    if (_done.isNotEmpty) {
      return CodeCard(child: Text(_done, style: codeSans(c, size: 13.5, color: c.ink2)));
    }
    return CodeCard(
      edge: c.warn,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.schedule_rounded, size: 16, color: c.warn),
          const SizedBox(width: 6),
          Expanded(child: Text('Needs your OK · runs on ${cs(st['server'])}', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.warn))),
        ]),
        const SizedBox(height: 10),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(10)),
          child: Text(cs(st['cmd']), style: codeMono(c, size: 13.5)),
        ),
        if (cs(st['reason']).isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(cs(st['reason']), style: codeSans(c, size: 13, color: c.ink2, height: 1.45)),
        ],
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          CodeMain('Allow once', height: 44, busy: _busy, onTap: () => _decide('once')),
          CodeOutline('Always in this folder', height: 44, onTap: _busy ? null : () => _decide('always')),
          CodeOutline('No', height: 44, onTap: _busy ? null : () => _decide('no')),
        ]),
      ]),
    );
  }
}
