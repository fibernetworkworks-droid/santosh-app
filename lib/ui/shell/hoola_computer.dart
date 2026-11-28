// v0.890 HOOLA COMPUTER on the phone: one tab, two computers.
// Hoola PC (Hoola's own cloud computer) opens straight into its workspace; Your PC shows the switch and the setup steps
// until her computer connects. Each computer has its OWN chats (server kind 'computer') that never show in her Hoola
// chats. The live screen shows whatever runs on that computer for her, even a task her voice call started.
import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../chat/hoola_thread.dart';
import '../hoola_theme.dart';
import 'hoola_tabs.dart';

const _name = {'hoola': 'Hoola PC', 'mine': 'Your PC'};
const _desktopPage = 'hoola.ainewtika.com/console/computer';

Map<String, dynamic> _m(Object? v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _l(Object? v) => v is List ? v.map(_m).toList() : <Map<String, dynamic>>[];
String _s(Object? v) => v == null ? '' : v.toString();
int _id(Map<String, dynamic> m) => int.tryParse(_s(m['id'])) ?? 0;

/// A server time, read as UTC when it carries no zone.
DateTime? _time(String iso) {
  final v = iso.trim();
  if (v.isEmpty) return null;
  return DateTime.tryParse(RegExp(r'(Z|[+-]\d\d:?\d\d)$').hasMatch(v) ? v : '${v}Z');
}

String _resultLine(Map<String, dynamic> r) {
  final st = _s(r['status']);
  if (st == 'working' || st == 'queued') return 'Working now';
  if (r['needs_you'] == true) return 'Waiting for you';
  if (st == 'done') return 'Done';
  return st.isEmpty ? '' : st[0].toUpperCase() + st.substring(1);
}

/// The Computer tab. v0.999.233 COMPUTER V2 (her prototype "a job on each computer, step by step" -> "GO"): she asks in
/// one box, Hoola picks the computer and says why, the chosen machine lights up and its screen opens on that job; the
/// two machines below show what each is doing right now; her recent jobs as result cards.
class HoolaComputer extends StatefulWidget {
  const HoolaComputer({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaComputer> createState() => _HoolaComputerState();
}

class _HoolaComputerState extends State<HoolaComputer> {
  Map<String, dynamic> _st = {};
  List<Map<String, dynamic>> _jobs = [];
  String? _err;
  Timer? _poll;
  final _ask = TextEditingController();
  String _where = 'auto';
  String _chosen = '', _why = '';
  bool _going = false;

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    _poll?.cancel();
    _ask.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/computer'));
      if (mounted) setState(() { _st = r; _err = null; });
    } catch (e) {
      if (mounted) setState(() => _err = 'Could not load Hoola Computer. Pull down to try again.');
    }
    try {
      final j = _m(await widget.app.api!.call('GET', '/api/pc/trace', query: {'limit': '5'}));
      if (mounted) setState(() => _jobs = _l(j['jobs']));
    } catch (_) {}
  }

  bool get _mineReady {
    final mine = _m(_st['mine']);
    return mine['on'] == true && _l(mine['devices']).isNotEmpty;
  }

  String get _myName {
    final d = _l(_m(_st['mine'])['devices']);
    return d.isEmpty ? 'Your PC' : _s(d.first['name']);
  }

  void _open(String which, {String chat = ''}) {
    final ready = which == 'hoola' || _mineReady;
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => HoolaTheme(
        appearance: widget.app.appearance,
        child: ready ? ComputerSpace(app: widget.app, which: which, chat: chat) : ComputerSetup(app: widget.app),
      ),
    )).then((_) { if (mounted) setState(() { _chosen = ''; _why = ''; }); _load(); });
  }

  /// Her job: Hoola chooses the computer (or she did), says why, the machine lights up, then its screen opens.
  Future<void> _go() async {
    final text = _ask.text.trim();
    if (text.isEmpty || _going) return;
    setState(() => _going = true);
    final api = widget.app.api!;
    final still = HoolaMotion.reduced(context);
    try {
      var which = _where, why = 'you chose it';
      if (which == 'auto') {
        final c = _m(await api.call('POST', '/api/computer/choose', body: {'text': text}));
        which = _s(c['which']) == 'mine' ? 'mine' : 'hoola';
        why = _s(c['why']);
      }
      if (which == 'mine' && !_mineReady) {
        _open('mine');
        return;
      }
      if (mounted) setState(() { _chosen = which; _why = why; });
      final r = _m(await api.call('POST', '/api/computer/$which/chats'));
      final chat = _s(r['id']);
      await api.call('POST', '/api/conversations/$chat/messages',
          body: {'text': text, 'client_id': 'hc${DateTime.now().microsecondsSinceEpoch}'});
      _ask.clear();
      await Future<void>.delayed(Duration(milliseconds: still ? 0 : 900));
      if (mounted) _open(which, chat: chat);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _going = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final h = _m(_st['hoola']), mine = _m(_st['mine']);
    final hRun = _m(h['running']), mRun = _m(mine['running']);
    final devs = _l(mine['devices']);
    final online = devs.where((d) => d['online'] == true).toList();
    String state(Map<String, dynamic> run, bool on, String idle) => run.isNotEmpty
        ? (_s(run['status']) == 'needs_confirm' ? 'Waiting for your yes' : 'Working · step ${_s(run['step'])}')
        : idle;
    final hState = _st.isEmpty ? 'Checking…' : state(hRun, h['online'] == true, h['online'] == true ? 'Ready' : 'Starting');
    final mState = !_mineReady
        ? (mine['on'] == true ? 'Waiting for your PC' : 'Not set up · tap to connect')
        : state(mRun, online.isNotEmpty,
            online.isNotEmpty ? 'Online${mine['chrome'] == true ? ' · Chrome connected' : ''}' : 'Offline · open Hoola Desktop');
    Widget chip(String key, String label) {
      final on = _where == key;
      return Padding(
        padding: const EdgeInsets.only(right: HoolaSpace.s8, bottom: HoolaSpace.s8),
        child: Semantics(
          selected: on,
          button: true,
          child: InkWell(
            borderRadius: HoolaRadius.r(HoolaRadius.pill),
            onTap: () => setState(() => _where = key),
            child: Container(
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: on ? c.pill : Colors.transparent,
                borderRadius: HoolaRadius.r(HoolaRadius.pill),
                border: Border.all(color: on ? c.pill : c.lineStrong),
              ),
              child: Text(label, style: HoolaType.label(c).copyWith(fontSize: 13, color: on ? c.onPill : c.ink2,
                  fontWeight: on ? FontWeight.w600 : FontWeight.w500)),
            ),
          ),
        ),
      );
    }
    return RefreshIndicator(
      color: c.accent,
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 120),
        children: [
          const HoolaTabHeader(title: 'Computer', sub: 'Hoola PC in the cloud, and your own PC'),
          if (_err != null)
            Padding(padding: const EdgeInsets.all(HoolaSpace.gutter), child: Text(_err!, style: HoolaType.small(c))),
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, HoolaSpace.s16),
            child: Text('What should a computer do for you?',
                style: HoolaType.hero(c).copyWith(fontSize: 30, height: 1.2)),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
            child: Container(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.s16, HoolaSpace.s8, HoolaSpace.s8, HoolaSpace.s8),
              decoration: BoxDecoration(
                color: c.surface,
                borderRadius: HoolaRadius.r(HoolaRadius.cardLg),
                border: Border.all(color: c.line),
                boxShadow: [BoxShadow(color: c.shadow, blurRadius: 24, offset: const Offset(0, 8))],
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                TextField(
                  controller: _ask,
                  minLines: 2,
                  maxLines: 5,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _go(),
                  style: HoolaType.reply(c).copyWith(fontSize: 17),
                  decoration: InputDecoration(
                    filled: false,
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    hintText: "Download my October GSTR-2B and tell me which suppliers haven't filed",
                    hintStyle: HoolaType.reply(c).copyWith(fontSize: 17, color: c.ink3),
                  ),
                ),
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Expanded(
                    child: Wrap(children: [
                      chip('auto', 'Let Hoola choose'),
                      chip('hoola', 'Hoola PC'),
                      chip('mine', _mineReady ? _myName : 'Your PC'),
                    ]),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(bottom: HoolaSpace.s8),
                    child: IconButton.filled(
                      tooltip: 'Start the job',
                      onPressed: _going ? null : _go,
                      style: IconButton.styleFrom(backgroundColor: c.accent, foregroundColor: c.onAccent),
                      icon: _going
                          ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onAccent))
                          : const Icon(Icons.arrow_upward_rounded),
                    ),
                  ),
                ]),
              ]),
            ),
          ),
          AnimatedSize(
            duration: HoolaMotion.reduced(context) ? Duration.zero : HoolaMotion.page,
            child: _chosen.isEmpty
                ? const SizedBox(width: double.infinity)
                : Padding(
                    padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s12, HoolaSpace.gutter, 0),
                    child: Semantics(
                      liveRegion: true,
                      child: Row(children: [
                        Icon(Icons.arrow_forward_rounded, size: 18, color: c.accent),
                        const SizedBox(width: HoolaSpace.s8),
                        Expanded(
                          child: Text.rich(TextSpan(children: [
                            TextSpan(text: _chosen == 'hoola' ? 'Hoola PC' : _myName,
                                style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600)),
                            TextSpan(text: _why.isEmpty ? '' : ' · $_why', style: HoolaType.body(c).copyWith(color: c.ink2)),
                          ])),
                        ),
                      ]),
                    ),
                  ),
          ),
          const SizedBox(height: HoolaSpace.s20),
          _Machine(
            cloud: true,
            name: 'Hoola PC',
            line: "Hoola's own computer in the cloud. Awake 24×7, your logins in your own locked folder.",
            state: hState,
            busy: hRun.isNotEmpty,
            ok: h['online'] == true,
            thought: _s(hRun['thought']).isEmpty ? _s(hRun['task']) : _s(hRun['thought']),
            chosen: _chosen == 'hoola',
            onTap: () => _open('hoola'),
          ),
          _Machine(
            cloud: false,
            name: _mineReady ? _myName : 'Your PC',
            line: _mineReady ? 'Your internet, your Chrome and your apps.' : 'Connect it for sites that refuse cloud computers.',
            state: mState,
            busy: mRun.isNotEmpty,
            ok: online.isNotEmpty,
            thought: _s(mRun['thought']).isEmpty ? _s(mRun['task']) : _s(mRun['thought']),
            chosen: _chosen == 'mine',
            onTap: () => _open('mine'),
          ),
          if (_jobs.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s20, HoolaSpace.gutter, HoolaSpace.s8),
              child: Text('Recent jobs', style: TextStyle(fontFamily: HoolaFont.title, fontSize: 20, color: c.ink, height: 1.3)),
            ),
            for (final j in _jobs) _JobCard(job: j, mine: _myName),
          ],
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s16, HoolaSpace.gutter, 0),
            child: Container(
              padding: const EdgeInsets.all(HoolaSpace.s16),
              decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
              child: Text(
                'Paying, sending, deleting and saving files always wait for your yes. Passwords and OTPs stay yours. '
                'Each computer keeps its own chats; one voice call works for both.',
                style: HoolaType.small(c).copyWith(color: c.ink2),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// One computer on the home: a drawing of the machine (a cloud screen or a laptop) beside its name, state and thought.
class _Machine extends StatelessWidget {
  const _Machine({required this.cloud, required this.name, required this.line, required this.state, required this.busy,
      required this.ok, required this.thought, required this.chosen, required this.onTap});
  final bool cloud, busy, ok, chosen;
  final String name, line, state, thought;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final stateColor = busy ? c.accent : ok ? c.ok : c.ink3;
    final art = cloud
        ? Container(
            width: 84,
            height: 62,
            decoration: BoxDecoration(
              borderRadius: HoolaRadius.r(HoolaRadius.tile),
              border: Border.all(color: const Color(0xFF1E1E26), width: 4),
              gradient: const RadialGradient(center: Alignment(-.4, -.6), radius: 1.2,
                  colors: [Color(0xFF3A3550), Color(0xFF1A1A22)]),
            ),
            child: const Icon(Icons.cloud_rounded, color: Color(0x33FFFFFF), size: 26),
          )
        : Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 74,
              height: 50,
              decoration: BoxDecoration(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(8), bottom: Radius.circular(2)),
                border: Border.all(color: const Color(0xFF1E1E26), width: 4),
                gradient: const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight,
                    colors: [Color(0xFFE7E3DA), Color(0xFFD6D1C5)]),
              ),
            ),
            Container(
              width: 84,
              height: 6,
              decoration: const BoxDecoration(
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(6)),
                color: Color(0xFFBDB7AB),
              ),
            ),
          ]);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, HoolaSpace.s12),
      child: AnimatedContainer(
        duration: HoolaMotion.reduced(context) ? Duration.zero : HoolaMotion.page,
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: HoolaRadius.r(HoolaRadius.cardLg),
          border: Border.all(color: chosen ? c.accent : c.line, width: chosen ? 2 : 1),
          boxShadow: chosen ? [BoxShadow(color: c.accent.withOpacity(.18), blurRadius: 0, spreadRadius: 4)] : null,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: HoolaRadius.r(HoolaRadius.cardLg),
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(HoolaSpace.s16),
              child: Row(children: [
                art,
                const SizedBox(width: HoolaSpace.s16),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(name, style: TextStyle(fontFamily: HoolaFont.title, fontSize: 19, color: c.ink, height: 1.3)),
                    const SizedBox(height: 2),
                    Text(line, style: HoolaType.small(c).copyWith(color: c.ink2)),
                    const SizedBox(height: 4),
                    Text(state, style: HoolaType.label(c).copyWith(color: stateColor, fontWeight: FontWeight.w600)),
                    if (busy && thought.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(thought, maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: HoolaType.reply(c).copyWith(fontSize: 14, fontStyle: FontStyle.italic, color: c.ink2)),
                    ],
                  ]),
                ),
                Icon(Icons.chevron_right_rounded, color: c.ink3),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// A finished (or running) job as a result card: where it ran, what it was, how it ended, steps and time.
class _JobCard extends StatelessWidget {
  const _JobCard({required this.job, required this.mine});
  final Map<String, dynamic> job;
  final String mine;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final st = _s(job['status']);
    final (word, tone) = switch (st) {
      'done' => ('Done', c.ok),
      'running' => ('Working', c.accent),
      'needs_confirm' => ('Waiting for you', c.warn),
      'partial' => ('Stopped part-way', c.warn),
      'failed' => ('Did not finish', c.bad),
      'cancelled' => ('Stopped', c.ink3),
      _ => (st, c.ink3),
    };
    final hoola = _s(job['kind']) == 'hoola_pc';
    final started = (job['started'] as num?)?.toDouble() ?? 0, ended = (job['ended'] as num?)?.toDouble() ?? 0;
    final secs = ended > started ? (ended - started).round() : 0;
    final took = secs <= 0 ? '' : secs < 60 ? ' · $secs s' : ' · ${secs ~/ 60} min ${secs % 60} s';
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, HoolaSpace.s8),
      child: Container(
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: HoolaRadius.r(HoolaRadius.card),
          border: Border(left: BorderSide(color: tone, width: 4), top: BorderSide(color: c.line),
              right: BorderSide(color: c.line), bottom: BorderSide(color: c.line)),
        ),
        padding: const EdgeInsets.all(HoolaSpace.s12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: hoola ? c.accentSoft : c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
            child: Text(hoola ? 'Hoola PC' : mine, style: HoolaType.label(c).copyWith(color: hoola ? c.accent : c.ink2)),
          ),
          const SizedBox(height: 6),
          Text(_s(job['task']).replaceAll(RegExp(r'\s*\(Originally:.*$'), ''), maxLines: 2, overflow: TextOverflow.ellipsis,
              style: HoolaType.body(c)),
          const SizedBox(height: 4),
          Text.rich(TextSpan(children: [
            TextSpan(text: word, style: HoolaType.small(c).copyWith(color: tone, fontWeight: FontWeight.w600)),
            TextSpan(text: ' · ${_s(job['steps'])} steps$took', style: HoolaType.small(c)),
          ])),
        ]),
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
        Text('Connect your PC', style: HoolaType.hero(c)),
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
/// The chat is the Hoola chat's own thread (lib/ui/chat/hoola_thread.dart): her message the moment she sends, the reply
/// in the reply serif with markdown and landing word by word when it arrives, one working row, Copy / Read aloud / Share.
class ComputerSpace extends StatefulWidget {
  const ComputerSpace({super.key, required this.app, required this.which, this.chat = ''});
  final Santosh app;
  final String which;
  final String chat;     // v0.999.233 the job she just gave from the home opens straight on its chat
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
  bool _loaded = false;          // this chat's first fetch is in: what it brought is history, later replies land
  String _pendId = '', _pendText = '';   // her message just sent, shown until the server's list carries it
  int _pendAfter = 0;            // the newest message id when she sent it
  DateTime? _sentAt;
  final _say = TextEditingController();
  Timer? _poll;
  // v0.999.37 her hands: take control of the Hoola PC screen, the private sign-in form
  double _fw = 0, _fh = 0;       // the live picture's own size (her tap is mapped onto it)
  final _typeCtl = TextEditingController();
  final _userCtl = TextEditingController();
  final _pwCtl = TextEditingController();
  bool _handBusy = false;
  bool _saveLogin = false;       // v0.999.47 'Save for next time' (her tick)
  bool _bg = false;              // v0.999.47 'Work in the background' on her own PC
  // v0.999.233 COMPUTER V2: the job's own steps (its step record), Hoola's pointer at its last click, the page it is on,
  // and her yes / not now on a step that waits for her
  List<Map<String, dynamic>> _steps = [];
  String _stepSig = '', _url = '';
  Offset? _ptr;
  bool _deciding = false;

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
    _typeCtl.dispose();
    _userCtl.dispose();
    _pwCtl.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (widget.chat.isNotEmpty) _chat = widget.chat;
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
      _loaded = false;
      _pendId = '';
      await _loadChats();
      if (mounted) setState(() {});
    } catch (_) {}
  }

  Future<void> _tick() async {
    final api = widget.app.api!;
    try {
      final chat = _chat;
      if (chat.isNotEmpty) {
        final r = _m(await api.call('GET', '/api/conversations/$chat/messages', query: {'limit': '80'}));
        final rows = _l(r['messages']);
        // (she may have opened another task while this was on its way: then it is not this chat's list)
        if (mounted && chat == _chat) {
          final changed = rows.length != _msgs.length || (rows.isNotEmpty && _id(rows.last) != _id(_msgs.last));
          final arrived = _pendId.isNotEmpty && rows.any((m) => m['role'] == 'user' && _id(m) > _pendAfter);
          if (!_loaded || changed || arrived) {
            setState(() {
              _msgs = rows;
              _loaded = true;
              if (arrived) _pendId = '';
            });
          }
        }
      }
      final st = _m(await api.call('GET', '/api/computer'));
      final run = _m(_m(st[_w])['running']);
      if (mounted) setState(() { _run = run; _bg = _m(st['mine'])['background'] == true; });
      final sid = _s(run['session_id']);
      if (sid.isEmpty && _steps.isNotEmpty && mounted) setState(() { _steps = []; _stepSig = ''; _ptr = null; _url = ''; });
      if (sid.isNotEmpty) {
        final sig = '$sid:${_s(run['step'])}:${_s(run['status'])}';
        if (sig != _stepSig) {
          _stepSig = sig;
          try {
            final t = _m(await api.call('GET', '/api/pc/trace/$sid'));
            final rows = _l(t['steps_list'] ?? t['steps']);
            Offset? ptr;
            for (final x in rows.reversed) {
              final a = _m(x['args']);
              final px = num.tryParse(_s(a['x'])), py = num.tryParse(_s(a['y']));
              if (px != null && py != null) { ptr = Offset(px.toDouble(), py.toDouble()); break; }
            }
            if (mounted) setState(() { _steps = rows; _ptr = ptr; });
          } catch (_) {}
        }
        final live = await api.browserLive(sid);
        final u = Uri.tryParse(_s(live['url']));
        if (u != null && u.host.isNotEmpty && mounted && u.host != _url) setState(() => _url = u.host.replaceFirst(RegExp(r'^www\.'), ''));
        final seq = (live['seq'] as num?)?.toInt() ?? -1;
        if (seq != _seq) {
          final b = await api.browserFrame(sid);
          if (b != null && mounted) {
            final bytes = Uint8List.fromList(b);
            try {
              final img = await decodeImageFromList(bytes);
              _fw = img.width.toDouble();
              _fh = img.height.toDouble();
              img.dispose();
            } catch (_) {}
            if (mounted) setState(() { _frame = bytes; _seq = seq; });
          }
        }
      }
    } catch (_) {}
  }

  bool get _takeover => _run['takeover'] == true;

  /// Her answer to a step that waits for her yes (paying, sending, deleting, saving a file).
  Future<void> _decide(bool yes) async {
    final sid = _s(_run['session_id']);
    final id = _s(_m(_run['pending'])['id']);
    if (sid.isEmpty || id.isEmpty || _deciding) return;
    setState(() => _deciding = true);
    try {
      await widget.app.api!.call('POST', '/api/computer/task/$sid/decide', body: {'yes': yes, 'id': id});
      _note(yes ? 'Hoola carries on.' : 'Hoola will not do that step.');
    } catch (e) {
      _note('$e');
    }
    if (mounted) setState(() => _deciding = false);
    _tick();
  }

  String _plain(Map<String, dynamic> x) {
    final a = _s(x['thought']).trim().isNotEmpty ? _s(x['thought']).trim() : _s(x['action'] ?? x['tool']).replaceAll('_', ' ');
    return a.length > 90 ? '${a.substring(0, 88)}…' : a;
  }

  /// The job panel: its title, the newest steps as a checklist (done in green, now in violet), and her yes card.
  Widget _jobPanel(HoolaColors c) {
    final pend = _m(_run['pending']);
    final waits = _s(_run['status']) == 'needs_confirm' && _s(pend['id']).isNotEmpty;
    final last = _steps.length > 3 ? _steps.sublist(_steps.length - 3) : _steps;
    final hidden = _steps.length - last.length;
    Widget row(Map<String, dynamic> x, bool now) => Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 18,
              height: 18,
              margin: const EdgeInsets.only(top: 1),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: now ? c.accentSoft : c.okSoft,
                border: now ? Border.all(color: c.accent, width: 2) : null,
              ),
              child: now ? null : Icon(Icons.check_rounded, size: 12, color: c.ok),
            ),
            const SizedBox(width: HoolaSpace.s8),
            Expanded(
              child: Text(_plain(x), maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: HoolaType.small(c).copyWith(color: now ? c.ink : c.ink2, fontWeight: now ? FontWeight.w600 : FontWeight.w400)),
            ),
          ]),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(_run['task']).replaceAll(RegExp(r'\s*\(Originally:.*$'), ''), maxLines: 2, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontFamily: HoolaFont.title, fontSize: 17, color: c.ink, height: 1.3)),
        if (hidden > 0)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text('$hidden earlier step${hidden == 1 ? '' : 's'}', style: HoolaType.label(c))),
        for (var i = 0; i < last.length; i++) row(last[i], i == last.length - 1 && !waits),
        if (waits)
          Container(
            margin: const EdgeInsets.only(top: HoolaSpace.s12),
            padding: const EdgeInsets.all(HoolaSpace.s12),
            decoration: BoxDecoration(
              color: c.warnSoft,
              borderRadius: HoolaRadius.r(HoolaRadius.tile),
              border: Border.all(color: c.warn.withOpacity(.35)),
            ),
            child: Semantics(
              liveRegion: true,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Icon(Icons.shield_outlined, size: 18, color: c.warn),
                  const SizedBox(width: HoolaSpace.s8),
                  Text('Hoola needs your yes', style: HoolaType.title(c).copyWith(fontSize: 15)),
                ]),
                const SizedBox(height: 4),
                Text(_s(pend['what']).isEmpty ? 'A step that cannot be undone' : _s(pend['what']), style: HoolaType.body(c).copyWith(color: c.ink2)),
                const SizedBox(height: HoolaSpace.s8),
                Wrap(spacing: HoolaSpace.s8, runSpacing: HoolaSpace.s8, children: [
                  FilledButton(
                    onPressed: _deciding ? null : () => _decide(true),
                    style: FilledButton.styleFrom(backgroundColor: c.accent, foregroundColor: c.onAccent),
                    child: const Text('Yes, do it'),
                  ),
                  OutlinedButton(onPressed: _deciding ? null : () => _decide(false), child: const Text('Not now')),
                ]),
              ]),
            ),
          ),
      ]),
    );
  }

  /// The machine itself: Hoola PC as a dark cloud screen with its address bar; her PC as her Chrome with Hoola's own
  /// tab and the violet "Hoola is working in this tab" banner with Stop. Hoola's pointer sits where it last clicked.
  Widget _device(HoolaColors c, bool running) {
    final hoola = _w == 'hoola';
    const dk = Color(0xFF1E1E26), dk2 = Color(0xFF15151B);
    final bar = hoola
        ? Container(
            height: 32,
            color: dk2,
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Row(children: [
              for (var i = 0; i < 3; i++)
                Container(width: 8, height: 8, margin: const EdgeInsets.only(right: 5),
                    decoration: const BoxDecoration(shape: BoxShape.circle, color: Color(0xFF3A3A46))),
              const SizedBox(width: 6),
              Expanded(
                child: Text(_url.isEmpty ? 'Hoola PC' : _url, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontFamily: HoolaFont.mono, fontSize: 11, color: Color(0xFFC9C6D6))),
              ),
              if (running) const Text('● live', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFFBDB2FF))),
            ]),
          )
        : Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              height: 30,
              color: c.sunk,
              padding: const EdgeInsets.only(left: 8, top: 4),
              alignment: Alignment.bottomLeft,
              child: Row(children: [
                Text('  Your tabs  ', style: HoolaType.label(c)),
                if (running)
                  Flexible(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: c.surface,
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
                        border: Border(top: BorderSide(color: c.accent, width: 2)),
                      ),
                      child: Text('Hoola${_url.isEmpty ? '' : ' · $_url'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: HoolaType.label(c).copyWith(color: c.accent, fontWeight: FontWeight.w600)),
                    ),
                  ),
              ]),
            ),
            if (running)
              Container(
                height: 30,
                color: c.accent,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Flexible(child: Text('Hoola is working in this tab', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: HoolaType.label(c).copyWith(color: c.onAccent))),
                  const SizedBox(width: 10),
                  InkWell(
                    onTap: () async {
                      try { await widget.app.api!.browserStop(_s(_run['session_id'])); } catch (_) {}
                      _tick();
                    },
                    child: Text('Stop', style: HoolaType.label(c).copyWith(color: c.onAccent, fontWeight: FontWeight.w700,
                        decoration: TextDecoration.underline, decorationColor: c.onAccent)),
                  ),
                ]),
              ),
          ]);
    final screen = SizedBox(
      height: _takeover ? 260 : 196,
      width: double.infinity,
      child: _frame != null && running
          ? LayoutBuilder(builder: (context, box) {
              final size = Size(box.maxWidth, box.maxHeight);
              Widget? pointer;
              if (_ptr != null && _fw > 0 && _fh > 0) {
                final scale = (size.width / _fw) < (size.height / _fh) ? size.width / _fw : size.height / _fh;
                final dx = (size.width - _fw * scale) / 2, dy = (size.height - _fh * scale) / 2;
                pointer = AnimatedPositioned(
                  duration: HoolaMotion.reduced(context) ? Duration.zero : const Duration(milliseconds: 700),
                  curve: HoolaMotion.ease,
                  left: dx + _ptr!.dx * scale - 3,
                  top: dy + _ptr!.dy * scale - 2,
                  child: ExcludeSemantics(
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Icon(Icons.navigation_rounded, size: 18, color: c.accent),
                      Container(
                        margin: const EdgeInsets.only(top: 12),
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(color: c.accent, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
                        child: Text('Hoola', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: c.onAccent)),
                      ),
                    ]),
                  ),
                );
              }
              return GestureDetector(
                onTapUp: (d) => _tapScreen(d, size),
                child: Stack(children: [
                  Positioned.fill(
                    child: Semantics(label: 'Live screen of ${_name[_w]}', image: true,
                        child: Image.memory(_frame!, fit: BoxFit.contain, gaplessPlayback: true)),
                  ),
                  if (pointer != null && !_takeover) pointer,
                ]),
              );
            })
          : Center(
              child: Padding(
                padding: const EdgeInsets.all(HoolaSpace.s16),
                child: Text('Give a job and watch it happen here.', textAlign: TextAlign.center,
                    style: HoolaType.small(c).copyWith(color: hoola ? const Color(0xFFA9A6B8) : c.ink3)),
              ),
            ),
    );
    final think = Container(
      color: hoola ? dk2 : c.surface,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Row(children: [
        Icon(Icons.circle, size: 8, color: _s(_run['status']) == 'needs_confirm' ? c.warn : running ? c.accent : c.ink3),
        const SizedBox(width: HoolaSpace.s8),
        Expanded(
          child: Text(
            !running ? 'Waiting for a job' : _s(_run['thought']).isEmpty ? 'Working…' : _s(_run['thought']),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontFamily: HoolaFont.serif, fontStyle: FontStyle.italic, fontSize: 14, height: 1.35,
                color: hoola ? const Color(0xFFDCD9E6) : c.ink2),
          ),
        ),
      ]),
    );
    return ClipRRect(
      borderRadius: HoolaRadius.r(HoolaRadius.card),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: hoola ? dk : c.sunk,
          border: Border.all(color: _takeover ? c.accent : (hoola ? const Color(0xFF2A2A34) : c.line), width: _takeover ? 2 : 1),
          borderRadius: HoolaRadius.r(HoolaRadius.card),
        ),
        child: Column(mainAxisSize: MainAxisSize.min, children: [bar, screen, think]),
      ),
    );
  }

  Future<void> _toggleBg() async {
    final on = !_bg;
    try {
      await widget.app.api!.call('PUT', '/api/computer/mine/background', body: {'on': on});
      if (mounted) setState(() => _bg = on);
      _note(on
          ? 'Hoola works in the background on your PC: it never takes your mouse or keyboard without asking.'
          : 'Hoola may use your mouse and keyboard again.');
    } catch (e) {
      _note('$e');
    }
  }

  Future<void> _toggleTake() async {
    final sid = _s(_run['session_id']);
    if (sid.isEmpty || _handBusy) return;
    final on = !_takeover;
    setState(() => _handBusy = true);
    try {
      await widget.app.api!.call('POST', '/api/computer/task/$sid/takeover', body: {'on': on});
      _note(on ? 'You have control. Hoola is waiting.' : 'Hoola carries on.');
    } catch (e) {
      _note('$e');
    }
    if (mounted) setState(() => _handBusy = false);
    _tick();
  }

  Future<void> _hand(Map<String, dynamic> body) async {
    final sid = _s(_run['session_id']);
    if (sid.isEmpty || !_takeover) return;
    try {
      await widget.app.api!.call('POST', '/api/computer/task/$sid/input', body: body);
      _seq = -1;
    } catch (e) {
      _note('$e');
    }
    _tick();
  }

  void _tapScreen(TapUpDetails d, Size box) {
    if (!_takeover || _fw <= 0 || _fh <= 0) return;
    final scale = (box.width / _fw) < (box.height / _fh) ? box.width / _fw : box.height / _fh;
    final dx = (box.width - _fw * scale) / 2, dy = (box.height - _fh * scale) / 2;
    final x = (d.localPosition.dx - dx) / scale, y = (d.localPosition.dy - dy) / scale;
    if (x < 0 || y < 0 || x > _fw || y > _fh) return;
    _hand({'op': 'click', 'x': x, 'y': y});
  }

  Future<void> _sendLogin({bool self = false, bool saved = false, bool onepw = false}) async {
    final sid = _s(_run['session_id']);
    final id = _s(_m(_run['login'])['id']);
    if (sid.isEmpty || id.isEmpty) return;
    final Map<String, dynamic> body = self
        ? {'id': id, 'skip': true}
        : onepw
            ? {'id': id, 'use_onepw': true}
            : saved
            ? {'id': id, 'use_saved': true}
            : {'id': id, 'username': _userCtl.text, 'password': _pwCtl.text, 'save': _saveLogin};
    _saveLogin = false;
    _userCtl.clear();
    _pwCtl.clear();
    try {
      await widget.app.api!.call('POST', '/api/computer/task/$sid/login', body: body);
      if (self) {
        await widget.app.api!.call('POST', '/api/computer/task/$sid/takeover', body: {'on': true});
        _note("You have control. Sign in, then tap I'm done.");
      } else {
        _note('Typed in for you.');
      }
    } catch (e) {
      _note('$e');
    }
    _tick();
  }

  void _note(String t) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Widget _handsPanel(HoolaColors c) {
    Widget key(String label, String k) => Padding(
          padding: const EdgeInsets.only(right: HoolaSpace.s8),
          child: OutlinedButton(onPressed: () => _hand({'op': 'key', 'keys': k}), child: Text(label)),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text("You have control. Tap on the screen, type below, then tap I'm done. Hoola never sees what you type.",
            style: HoolaType.small(c).copyWith(color: c.ink2)),
        const SizedBox(height: HoolaSpace.s8),
        Row(children: [
          Expanded(
            child: TextField(
              controller: _typeCtl,
              autocorrect: false,
              enableSuggestions: false,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) {
                final t = _typeCtl.text;
                _typeCtl.clear();
                if (t.isNotEmpty) _hand({'op': 'type', 'text': t});
              },
              style: HoolaType.body(c),
              decoration: const InputDecoration(hintText: 'Type into the PC', isDense: true),
            ),
          ),
          IconButton(
            tooltip: 'Type it',
            onPressed: () {
              final t = _typeCtl.text;
              _typeCtl.clear();
              if (t.isNotEmpty) _hand({'op': 'type', 'text': t});
            },
            icon: const Icon(Icons.keyboard_return_rounded),
          ),
        ]),
        const SizedBox(height: HoolaSpace.s8),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(children: [key('Enter', 'enter'), key('Tab', 'tab'), key('Backspace', 'backspace'), key('Esc', 'escape')]),
        ),
      ]),
    );
  }

  Widget _loginPanel(HoolaColors c, Map<String, dynamic> lg) {
    final pwOnly = _s(lg['fields']) == 'password';
    final saved = _m(lg['saved']);
    final onepw = _m(lg['onepw']);
    final canSave = lg['can_save'] == true;
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
      child: Container(
        padding: const EdgeInsets.all(HoolaSpace.s12),
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: HoolaRadius.r(HoolaRadius.tile),
          border: Border.all(color: c.accent),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Sign in to ${_s(lg['site'])}', style: HoolaType.label(c)),
          const SizedBox(height: 4),
          Text('Private: typed straight into ${_name[_w]}. Hoola never sees it${canSave ? ', and it is kept only if you tick Save' : ', and it is not kept'}.',
              style: HoolaType.small(c).copyWith(color: c.ink3)),
          if (onepw.isNotEmpty) ...[
            const SizedBox(height: HoolaSpace.s8),
            FilledButton(
              onPressed: () => _sendLogin(onepw: true),
              child: Text('Use 1Password sign-in · ${_s(onepw['title'])}'),
            ),
          ],
          if (saved.isNotEmpty) ...[
            const SizedBox(height: HoolaSpace.s8),
            FilledButton(
              onPressed: () => _sendLogin(saved: true),
              child: Text('Use saved sign-in${_s(saved['user']).isEmpty ? '' : ' (${_s(saved['user'])})'}'),
            ),
          ],
          if (!pwOnly) ...[
            const SizedBox(height: HoolaSpace.s8),
            TextField(
              controller: _userCtl,
              autocorrect: false,
              enableSuggestions: false,
              style: HoolaType.body(c),
              decoration: const InputDecoration(hintText: 'User name', isDense: true),
            ),
          ],
          const SizedBox(height: HoolaSpace.s8),
          TextField(
            controller: _pwCtl,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            style: HoolaType.body(c),
            decoration: const InputDecoration(hintText: 'Password', isDense: true),
          ),
          if (canSave)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              value: _saveLogin,
              onChanged: (v) => setState(() => _saveLogin = v == true),
              title: Text('Save for next time', style: HoolaType.small(c)),
            ),
          const SizedBox(height: HoolaSpace.s8),
          Wrap(spacing: HoolaSpace.s8, runSpacing: HoolaSpace.s8, children: [
            FilledButton(onPressed: () => _sendLogin(), child: const Text('Type it in')),
            OutlinedButton(onPressed: () => _sendLogin(self: true), child: const Text("I'll sign in myself")),
          ]),
        ]),
      ),
    );
  }

  Future<void> _send() async {
    final text = _say.text.trim();
    if (text.isEmpty || _sending || _chat.isEmpty) return;
    final cid = 'hc${DateTime.now().microsecondsSinceEpoch}';
    var newest = 0;
    for (final m in _msgs) {
      if (_id(m) > newest) newest = _id(m);
    }
    // her message is in the thread the moment she sends
    setState(() {
      _sending = true;
      _pendId = cid;
      _pendText = text;
      _pendAfter = newest;
      _sentAt = DateTime.now();
    });
    _say.clear();
    try {
      await widget.app.api!.call('POST', '/api/conversations/$_chat/messages', body: {'text': text, 'client_id': cid});
    } catch (_) {
      if (mounted) {
        // it did not go: her words leave the thread and go back into the box
        setState(() {
          if (_pendId == cid) _pendId = '';
        });
        if (_say.text.trim().isEmpty) {
          _say.text = text;
          _say.selection = TextSelection.collapsed(offset: text.length);
        }
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Not sent. Try again.')));
      }
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
                setState(() { _chat = _s(ch['id']); _msgs = []; _loaded = false; _pendId = ''; });
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
    final waiting = _sending || _pendId.isNotEmpty || (last != null && last['role'] == 'user');
    // the task running on this computer for THIS chat (one a call or another task started shows in the strip above only)
    final runHere = running && _s(_run['conv']) == _chat;
    final step = _s(_run['thought']).isEmpty ? _s(_run['task']) : _s(_run['thought']);
    final asked = _msgs.lastWhere((m) => m['role'] == 'user', orElse: () => const <String, dynamic>{});
    final since = _pendId.isNotEmpty ? _sentAt : (_time(_s(asked['at'])) ?? _sentAt);
    final thread = <HoolaMsg>[
      for (final m in _msgs)
        HoolaMsg(
          id: 'm${_id(m)}',
          mine: m['role'] == 'user',
          text: m['role'] == 'user' ? _s(m['text']).replaceAll(RegExp(r'(\n\n\[Web console [^\]\n]*\])+$'), '') : _s(m['text']),
        ),
      if (_pendId.isNotEmpty) HoolaMsg(id: _pendId, text: _pendText, mine: true, pending: true),
    ];
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
          if (_w == 'mine')
            IconButton(
              tooltip: 'Work in the background',
              onPressed: _toggleBg,
              icon: Icon(_bg ? Icons.visibility_off_rounded : Icons.mouse_rounded, color: _bg ? c.accent : c.ink2),
            ),
          IconButton(tooltip: '${_name[_w]} chats', onPressed: _pickChat, icon: const Icon(Icons.menu_rounded)),
        ],
      ),
      body: SafeArea(
        top: false,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
            child: _device(c, running),
          ),
          if (running)
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 2, HoolaSpace.s8, 0),
              child: Row(children: [
                Expanded(
                  child: Text('Step ${_s(_run['step'])}${fromCall ? ' · from your call' : ''}${_s(_run['conv']) == _chat ? '' : ' · from another chat'}',
                      style: HoolaType.small(c)),
                ),
                if (_w == 'hoola' && _s(_run['status']) != 'queued')
                  TextButton(
                    onPressed: _handBusy ? null : _toggleTake,
                    child: Text(_takeover ? "I'm done" : 'Take control', style: HoolaType.label(c).copyWith(color: c.accent)),
                  ),
                TextButton(
                  onPressed: () async {
                    try { await widget.app.api!.browserStop(_s(_run['session_id'])); } catch (_) {}
                    _tick();
                  },
                  child: Text('Stop', style: HoolaType.label(c).copyWith(color: c.bad)),
                ),
              ]),
            ),
          if (running && !_takeover) _jobPanel(c),
          if (running && _takeover) _handsPanel(c),
          if (running && _m(_run['login']).isNotEmpty) _loginPanel(c, _m(_run['login'])),
          Expanded(
            child: HoolaThreadView(
              messages: thread,
              threadKey: _chat,
              loaded: _loaded,
              working: _loaded && (waiting || runHere),
              label: runHere ? step : null,
              since: since,
              onAloud: widget.app.readAloud,
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
                      filled: false,   // v0.925: the theme's outlined, filled field otherwise draws a box inside the bar
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
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
