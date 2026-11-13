// v0.890 HOOLA COMPUTER on the phone: one tab, two computers.
// Hoola PC (Hoola's own cloud computer) opens straight into its workspace; Your PC shows the switch and the setup steps
// until her computer connects. Each computer has its OWN chats (server kind 'computer') that never show in her Hoola
// chats. The live screen shows whatever runs on that computer for her, even a task her voice call started.
import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_tabs.dart';

const _name = {'hoola': 'Hoola PC', 'mine': 'Your PC'};
const _desktopPage = 'hoola.ainewtika.com/console/computer';

Map<String, dynamic> _m(Object? v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(Object? v) => v is List ? v.map(_m).toList() : <Map<String, dynamic>>[];
String _s(Object? v) => v == null ? '' : v.toString();

String _resultLine(Map<String, dynamic> r) {
  final st = _s(r['status']);
  if (st == 'working' || st == 'queued') return 'Working now';
  if (r['needs_you'] == true) return 'Waiting for you';
  if (st == 'done') return 'Done';
  return st.isEmpty ? '' : st[0].toUpperCase() + st.substring(1);
}

/// The Computer tab.
class HoolaComputer extends StatefulWidget {
  const HoolaComputer({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaComputer> createState() => _HoolaComputerState();
}

class _HoolaComputerState extends State<HoolaComputer> {
  Map<String, dynamic> _st = {};
  String? _err;
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/computer'));
      if (mounted) setState(() { _st = r; _err = null; });
    } catch (e) {
      if (mounted) setState(() => _err = 'Could not load Hoola Computer. Pull down to try again.');
    }
  }

  void _open(String which) {
    final mine = _m(_st['mine']);
    final ready = which == 'hoola' || (mine['on'] == true && _l(mine['devices']).isNotEmpty);
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => HoolaTheme(
        appearance: widget.app.appearance,
        child: ready ? ComputerSpace(app: widget.app, which: which) : ComputerSetup(app: widget.app),
      ),
    )).then((_) => _load());
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final h = _m(_st['hoola']), mine = _m(_st['mine']);
    final hRun = _m(h['running']), mRun = _m(mine['running']);
    final devs = _l(mine['devices']);
    final hLine = _st.isEmpty
        ? 'Checking…'
        : hRun.isNotEmpty
            ? 'Working · ${_s(hRun['task'])}'
            : h['online'] == true ? 'Online · ready' : 'Offline · Hoola is starting it';
    final mLine = mine['on'] != true
        ? 'Not set up · tap to connect'
        : devs.isEmpty
            ? 'Waiting for your PC to connect'
            : mRun.isNotEmpty
                ? 'Working · ${_s(mRun['task'])}'
                : mine['online'] == true ? 'Online · ${devs.where((d) => d['online'] == true).map((d) => _s(d['name'])).join(', ')}' : 'Offline · open Hoola Desktop on it';
    return RefreshIndicator(
      color: c.accent,
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 120),
        children: [
          const HoolaTabHeader(title: 'Hoola Computer', sub: 'Portals, forms, downloads, repeat entries'),
          if (_err != null)
            Padding(padding: const EdgeInsets.all(HoolaSpace.gutter), child: Text(_err!, style: HoolaType.small(c))),
          _Card(
            icon: Icons.cloud_outlined,
            tint: true,
            title: 'Hoola PC',
            line: hLine,
            lineColor: hRun.isNotEmpty ? c.accent : (h['online'] == true ? c.ok : c.ink3),
            body: "Hoola's own computer in the cloud. Works even when your PC is off. Your logins stay in your own locked folder.",
            onTap: () => _open('hoola'),
          ),
          _Card(
            icon: Icons.computer_rounded,
            title: 'Your PC',
            line: mLine,
            lineColor: mRun.isNotEmpty ? c.accent : (mine['online'] == true ? c.ok : c.ink3),
            body: 'Hoola works on your own Windows computer with your home internet. Best for Aadhaar, Parivahan and other sites that refuse cloud computers.',
            onTap: () => _open('mine'),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
            child: Container(
              padding: const EdgeInsets.all(HoolaSpace.s16),
              decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
              child: Text(
                'Each computer keeps its own chats. They never mix with your Hoola chats. One voice call works for both: '
                'say "Hoola PC pe karo" or "mere PC pe karo".',
                style: HoolaType.small(c),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.icon, required this.title, required this.line, required this.lineColor,
      required this.body, required this.onTap, this.tint = false});
  final IconData icon;
  final String title, line, body;
  final Color lineColor;
  final VoidCallback onTap;
  final bool tint;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, HoolaSpace.s12),
      child: Material(
        color: c.surface,
        shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.card), side: BorderSide(color: c.line)),
        child: InkWell(
          borderRadius: HoolaRadius.r(HoolaRadius.card),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(HoolaSpace.s16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(color: tint ? c.accentSoft : c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
                  child: Icon(icon, color: tint ? c.accent : c.ink2),
                ),
                const SizedBox(width: HoolaSpace.s12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(title, style: HoolaType.title(c)),
                    const SizedBox(height: 2),
                    Text(line, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: lineColor)),
                  ]),
                ),
                Icon(Icons.chevron_right_rounded, color: c.ink3),
              ]),
              const SizedBox(height: HoolaSpace.s12),
              Text(body, style: HoolaType.body(c).copyWith(color: c.ink2)),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Your PC: the switch and the three steps (the .exe is downloaded on the computer, so the phone gives the link).
class ComputerSetup extends StatefulWidget {
  const ComputerSetup({super.key, required this.app});
  final Santosh app;
  @override
  State<ComputerSetup> createState() => _ComputerSetupState();
}

class _ComputerSetupState extends State<ComputerSetup> {
  bool _on = false, _busy = false, _loaded = false;
  String _code = '';
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _check();
    _poll = Timer.periodic(const Duration(seconds: 3), (_) => _check());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _check() async {
    try {
      final st = _m(await widget.app.api!.call('GET', '/api/computer'));
      final mine = _m(st['mine']);
      if (!mounted) return;
      setState(() { _on = mine['on'] == true; _loaded = true; });
      if (_on && _l(mine['devices']).isNotEmpty) {
        _poll?.cancel();
        Navigator.of(context).pushReplacement(MaterialPageRoute<void>(
          builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: ComputerSpace(app: widget.app, which: 'mine')),
        ));
      }
    } catch (_) {}
  }

  Future<void> _switch(bool on) async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.call('PUT', '/api/computer/mine', body: {'on': on});
      setState(() => _on = on);
      if (on && _code.isEmpty) await _newCode();
    } catch (_) {}
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _newCode() async {
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/computer/mine/pair'));
      if (mounted) setState(() { _code = _s(r['code']); _on = true; });
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget step(int n, bool now, String title, Widget child) => Padding(
          padding: const EdgeInsets.only(bottom: HoolaSpace.s12),
          child: Container(
            padding: const EdgeInsets.all(HoolaSpace.s16),
            decoration: BoxDecoration(
              color: c.surface,
              borderRadius: HoolaRadius.r(HoolaRadius.tile),
              border: Border.all(color: now ? c.accent : c.line, width: now ? 2 : 1),
            ),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              CircleAvatar(
                radius: 14,
                backgroundColor: now ? c.accent : c.sunk,
                child: Text('$n', style: HoolaType.label(c).copyWith(color: now ? c.onAccent : c.ink2)),
              ),
              const SizedBox(width: HoolaSpace.s12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: HoolaType.title(c)),
                const SizedBox(height: HoolaSpace.s8),
                child,
              ])),
            ]),
          ),
        );
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(backgroundColor: c.bg, surfaceTintColor: c.bg, foregroundColor: c.ink, elevation: 0,
          title: Text('Your PC', style: HoolaType.title(c))),
      body: ListView(padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, HoolaSpace.s32), children: [
        Text('Connect your PC', style: HoolaType.display(c)),
        const SizedBox(height: HoolaSpace.s8),
        Text('Hoola works on your Windows computer with your home internet. Good for Aadhaar, Parivahan and other sites that block cloud computers.',
            style: HoolaType.body(c).copyWith(color: c.ink2)),
        const SizedBox(height: HoolaSpace.s16),
        Container(
          decoration: BoxDecoration(color: c.accentSoft, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
          child: SwitchListTile(
            value: _on,
            onChanged: !_loaded || _busy ? null : _switch,
            activeColor: c.accent,
            title: Text('Use my PC', style: HoolaType.title(c)),
          ),
        ),
        const SizedBox(height: HoolaSpace.s16),
        if (_on) ...[
          step(1, _code.isEmpty, 'On your computer, open this page', Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SelectableText(_desktopPage, style: HoolaType.body(c)),
            const SizedBox(height: HoolaSpace.s8),
            OutlinedButton.icon(
              onPressed: () {
                Clipboard.setData(const ClipboardData(text: 'https://$_desktopPage'));
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Link copied')));
              },
              icon: const Icon(Icons.copy_rounded, size: 18),
              label: const Text('Copy link'),
            ),
            const SizedBox(height: HoolaSpace.s4),
            Text('Download Hoola Desktop there (Windows 10 or 11, about 20 MB) and open it.', style: HoolaType.small(c)),
          ])),
          step(2, _code.isNotEmpty, 'Type this code in Hoola Desktop', Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (_code.isNotEmpty)
              Text(_code, style: HoolaType.code(c).copyWith(fontSize: 28, letterSpacing: 4))
            else
              Text('Tap below to get your code.', style: HoolaType.small(c)),
            const SizedBox(height: HoolaSpace.s8),
            TextButton(onPressed: _newCode, child: Text(_code.isEmpty ? 'Show my code' : 'New code')),
            if (_code.isNotEmpty) Text('Works once · expires in 10 minutes', style: HoolaType.small(c)),
          ])),
          step(3, false, 'Waiting for your PC…',
              Text('This screen opens your PC\'s workspace by itself when it connects.', style: HoolaType.small(c))),
        ],
        const SizedBox(height: HoolaSpace.s8),
        Text('A banner with a Stop button shows on your PC while Hoola works. Paying, sending, deleting and installing always wait for your tap.',
            style: HoolaType.small(c)),
      ]),
    );
  }
}

/// One computer's workspace: the live screen on top, that computer's own chat under it.
class ComputerSpace extends StatefulWidget {
  const ComputerSpace({super.key, required this.app, required this.which});
  final Santosh app;
  final String which;
  @override
  State<ComputerSpace> createState() => _ComputerSpaceState();
}

class _ComputerSpaceState extends State<ComputerSpace> {
  String _chat = '';
  List<Map<String, dynamic>> _chats = [], _msgs = [];
  Map<String, dynamic> _run = {};
  Uint8List? _frame;
  int _seq = -1;
  bool _sending = false;
  final _say = TextEditingController();
  final _scroll = ScrollController();
  Timer? _poll;

  String get _w => widget.which;

  @override
  void initState() {
    super.initState();
    _start();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _say.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    await _loadChats();
    if (_chat.isEmpty) {
      if (_chats.isNotEmpty) {
        _chat = _s(_chats.first['id']);
      } else {
        await _newTask();
      }
    }
    await _tick();
    _poll = Timer.periodic(const Duration(milliseconds: 2500), (_) => _tick());
  }

  Future<void> _loadChats() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/computer/$_w/chats'));
      if (mounted) setState(() => _chats = _l(r['chats']));
    } catch (_) {}
  }

  Future<void> _newTask() async {
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/computer/$_w/chats'));
      _chat = _s(r['id']);
      _msgs = [];
      await _loadChats();
      if (mounted) setState(() {});
    } catch (_) {}
  }

  Future<void> _tick() async {
    final api = widget.app.api!;
    try {
      if (_chat.isNotEmpty) {
        final r = _m(await api.call('GET', '/api/conversations/$_chat/messages', query: {'limit': '80'}));
        final rows = _l(r['messages']);
        if (mounted && rows.length != _msgs.length) {
          setState(() => _msgs = rows);
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
          });
        }
      }
      final st = _m(await api.call('GET', '/api/computer'));
      final run = _m(_m(st[_w])['running']);
      if (mounted) setState(() => _run = run);
      final sid = _s(run['session_id']);
      if (sid.isNotEmpty) {
        final live = await api.browserLive(sid);
        final seq = (live['seq'] as num?)?.toInt() ?? -1;
        if (seq != _seq) {
          final b = await api.browserFrame(sid);
          if (b != null && mounted) setState(() { _frame = Uint8List.fromList(b); _seq = seq; });
        }
      }
    } catch (_) {}
  }

  Future<void> _send() async {
    final text = _say.text.trim();
    if (text.isEmpty || _sending || _chat.isEmpty) return;
    setState(() => _sending = true);
    try {
      await widget.app.api!.call('POST', '/api/conversations/$_chat/messages',
          body: {'text': text, 'client_id': 'hc${DateTime.now().microsecondsSinceEpoch}'});
      _say.clear();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Not sent. Try again.')));
    }
    if (mounted) setState(() => _sending = false);
    _tick();
  }

  void _pickChat() {
    final c = HoolaColors.of(context);
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: c.surface,
      builder: (ctx) => SafeArea(
        child: ListView(shrinkWrap: true, children: [
          ListTile(
            leading: Icon(Icons.add_rounded, color: c.ink),
            title: Text('New task', style: HoolaType.title(c)),
            onTap: () async {
              Navigator.of(ctx).pop();
              await _newTask();
              _tick();
            },
          ),
          for (final ch in _chats)
            ListTile(
              selected: _s(ch['id']) == _chat,
              title: Text(ch['empty'] == true ? 'New task' : _s(ch['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: HoolaType.body(c)),
              subtitle: ch['result'] is Map ? Text(_resultLine(_m(ch['result'])), style: HoolaType.small(c)) : null,
              onTap: () {
                Navigator.of(ctx).pop();
                setState(() { _chat = _s(ch['id']); _msgs = []; });
                _tick();
              },
            ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final running = _run.isNotEmpty;
    final fromCall = _s(_run['from']) == 'call';
    final last = _msgs.isEmpty ? null : _msgs.last;
    final waiting = _sending || (last != null && last['role'] == 'user');
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(
        backgroundColor: c.bg,
        surfaceTintColor: c.bg,
        foregroundColor: c.ink,
        elevation: 0,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_name[_w] ?? '', style: HoolaType.title(c)),
          Text(running ? 'Step ${_s(_run['step'])}${fromCall ? ' · from your call' : ''}' : 'Ready',
              style: HoolaType.small(c).copyWith(color: running ? c.accent : c.ink3)),
        ]),
        actions: [
          IconButton(tooltip: '${_name[_w]} chats', onPressed: _pickChat, icon: const Icon(Icons.menu_rounded)),
        ],
      ),
      body: SafeArea(
        top: false,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
            child: ClipRRect(
              borderRadius: HoolaRadius.r(HoolaRadius.tile),
              child: Container(
                height: 196,
                width: double.infinity,
                decoration: BoxDecoration(color: c.sunk, border: Border.all(color: c.line)),
                alignment: Alignment.center,
                child: _frame != null && running
                    ? Semantics(label: 'Live screen of ${_name[_w]}', image: true, child: Image.memory(_frame!, fit: BoxFit.contain, gaplessPlayback: true))
                    : Padding(
                        padding: const EdgeInsets.all(HoolaSpace.s16),
                        child: Text('The live screen shows here while Hoola works.', textAlign: TextAlign.center, style: HoolaType.small(c)),
                      ),
              ),
            ),
          ),
          if (running)
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.s8, 0),
              child: Row(children: [
                Icon(Icons.circle, size: 8, color: c.accent),
                const SizedBox(width: HoolaSpace.s8),
                Expanded(child: Text(_s(_run['thought']).isEmpty ? _s(_run['task']) : _s(_run['thought']),
                    maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink2))),
                TextButton(
                  onPressed: () async {
                    try { await widget.app.api!.browserStop(_s(_run['session_id'])); } catch (_) {}
                    _tick();
                  },
                  child: Text('Stop', style: HoolaType.label(c).copyWith(color: c.bad)),
                ),
              ]),
            ),
          Expanded(
            child: ListView(
              controller: _scroll,
              padding: const EdgeInsets.all(HoolaSpace.gutter),
              children: [
                for (final m in _msgs)
                  Padding(
                    padding: const EdgeInsets.only(bottom: HoolaSpace.s12),
                    child: m['role'] == 'user'
                        ? Align(
                            alignment: Alignment.centerRight,
                            child: Container(
                              constraints: const BoxConstraints(maxWidth: 300),
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                              decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.card)),
                              child: Text(_s(m['text']).replaceAll(RegExp(r'(\n\n\[Web console [^\]\n]*\])+$'), ''),
                                  style: HoolaType.body(c)),
                            ),
                          )
                        : SelectableText(_s(m['text']), style: HoolaType.reply(c)),
                  ),
                if (waiting) Text('Hoola is working…', style: HoolaType.small(c).copyWith(color: c.accent)),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.s12, 0, HoolaSpace.s12, HoolaSpace.s12),
            child: Container(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.s16, 4, 4, 4),
              decoration: BoxDecoration(
                color: c.surface,
                borderRadius: HoolaRadius.r(HoolaRadius.pill),
                border: Border.all(color: c.lineStrong),
              ),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    controller: _say,
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _send(),
                    style: HoolaType.body(c),
                    decoration: InputDecoration(
                      border: InputBorder.none,
                      hintText: 'Tell ${_name[_w]} what to do…',
                      hintStyle: HoolaType.body(c).copyWith(color: c.ink3),
                    ),
                  ),
                ),
                IconButton.filled(
                  tooltip: 'Send',
                  onPressed: _sending ? null : _send,
                  style: IconButton.styleFrom(backgroundColor: c.accent, foregroundColor: c.onAccent),
                  icon: const Icon(Icons.arrow_upward_rounded),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
