// v1.0 HOOLA CODE TERMINAL: the commands Hoola left running in the background of a session (a dev server, a watcher),
// each a dark terminal card with what it is for, its command, how it stands and its newest lines; Stop while it runs.
// Read every 2 s while the page is open (GET /tasks/{id}/terminal; POST .../terminal/{bid}/stop).
import 'dart:async';

import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'code_kit.dart';
import 'code_words.dart';

class CodeTerminalPage extends StatefulWidget {
  const CodeTerminalPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<CodeTerminalPage> createState() => _CodeTerminalPageState();
}

class _CodeTerminalPageState extends State<CodeTerminalPage> {
  List<Map<String, dynamic>>? _shells;
  String? _error;
  Timer? _timer;
  bool _loading = false;
  final Set<String> _stopping = {};

  String get _base => '/api/devsahayak/tasks/${Uri.encodeComponent(widget.id)}/terminal';

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) {
      await Future<void>.value();       // this can run from initState: setState only after it
      if (mounted && _shells == null) setState(() => _error = codeLoadFailedLine);
      return;
    }
    if (_loading) return;
    _loading = true;
    try {
      final r = await api.call('GET', _base);
      if (!mounted) return;
      setState(() {
        _shells = cl(cm(r)['shells']);
        _error = null;
      });
    } catch (_) {
      if (mounted && _shells == null) setState(() => _error = codeLoadFailedLine);
    } finally {
      _loading = false;
    }
  }

  Future<void> _stop(String bid) async {
    if (bid.isEmpty || _stopping.contains(bid)) return;
    setState(() => _stopping.add(bid));
    final r = await codeCall(context, widget.app, 'POST', '$_base/${Uri.encodeComponent(bid)}/stop', body: const <String, dynamic>{});
    if (!mounted) return;
    setState(() {
      _stopping.remove(bid);
      if (r != null && r['shells'] is List) _shells = cl(r['shells']);
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final shells = _shells;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          const CodeTopBar(title: 'Terminal', sub: 'Commands running in the background'),
          Expanded(
            child: shells == null
                ? (_error == null
                    ? const Center(child: CodeRing(size: 22))
                    : CodeLoadFailed(
                        text: _error!,
                        onRetry: () {
                          setState(() => _error = null);
                          _load();
                        }))
                : RefreshIndicator(
                    onRefresh: _load,
                    color: c.ink,
                    child: shells.isEmpty
                        ? ListView(physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.fromLTRB(24, 80, 24, 24), children: [
                            Icon(Icons.terminal_rounded, size: 28, color: c.ink3),
                            const SizedBox(height: 12),
                            Text('No background commands. When Hoola starts a dev server or a watcher, it shows here.',
                                textAlign: TextAlign.center, style: codeSans(c, size: 14.5, color: c.ink2, height: 1.5)),
                          ])
                        : ListView.separated(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
                            itemCount: shells.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 12),
                            itemBuilder: (_, i) => _shell(c, shells[i]),
                          ),
                  ),
          ),
        ]),
      ),
    );
  }

  Widget _shell(HoolaColors c, Map<String, dynamic> s) {
    final id = cs(s['id']);
    final state = cs(s['state']);
    final running = state == 'running';
    final rc = s['rc'];
    final (String chip, Color fg) = running
        ? ('Running', HoolaTerminal.run)
        : state == 'killed'
            ? ('Stopped', CodeTerm.grey)
            : rc == null
                ? ('Ended', CodeTerm.grey)
                : (rc == 0 ? ('Exited 0', CodeTerm.green) : ('Exited $rc', CodeTerm.red));
    final all = [for (final x in (s['lines'] as List?) ?? const []) cs(x)];
    final lines = all.length > 60 ? all.sublist(all.length - 60) : all;
    final desc = cs(s['desc']).isNotEmpty ? cs(s['desc']) : (id.isEmpty ? 'A background command' : id);
    final ago = codeAgo(cs(s['at']));
    final stopping = _stopping.contains(id);
    return Semantics(
      container: true,
      label: '$desc. $chip',
      child: Container(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        decoration: BoxDecoration(
          color: CodeTerm.bg,
          borderRadius: BorderRadius.circular(14),
          border: c.dark ? Border.all(color: c.line) : null,
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text(desc, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: codeSans(c, size: 14.5, weight: FontWeight.w600, color: CodeTerm.ink)),
            ),
            const SizedBox(width: 8),
            Container(
              height: 24,
              padding: const EdgeInsets.symmetric(horizontal: 9),
              decoration: BoxDecoration(color: Colors.white.withOpacity(.08), borderRadius: BorderRadius.circular(12)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(width: 6, height: 6, decoration: BoxDecoration(color: fg, shape: BoxShape.circle)),
                const SizedBox(width: 6),
                Text(chip, style: codeSans(c, size: 12, weight: FontWeight.w600, color: fg)),
              ]),
            ),
          ]),
          const SizedBox(height: 6),
          Text('\$ ${cs(s['cmd'])}', style: codeMono(c, size: 12, color: CodeTerm.grey)),
          if ([id, ago].any((e) => e.isNotEmpty))
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text([id, if (ago.isNotEmpty) 'started $ago'].where((e) => e.isNotEmpty).join(' · '),
                  style: codeMono(c, size: 12, color: CodeTerm.grey)),
            ),
          if (lines.isNotEmpty)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(top: 10),
              padding: const EdgeInsets.only(top: 8),
              decoration: BoxDecoration(border: Border(top: BorderSide(color: Colors.white.withOpacity(.10)))),
              child: Text(lines.join('\n'), style: codeMono(c, size: 12, color: CodeTerm.ink)),
            ),
          if (running)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Align(
                alignment: Alignment.centerRight,
                child: Semantics(
                  button: true,
                  label: 'Stop $desc',
                  excludeSemantics: true,
                  child: Material(
                    color: Colors.white.withOpacity(.10),
                    shape: const StadiumBorder(),
                    child: InkWell(
                      customBorder: const StadiumBorder(),
                      onTap: stopping ? null : () => _stop(id),
                      child: Container(
                        height: 48,
                        padding: const EdgeInsets.symmetric(horizontal: 18),
                        child: Row(mainAxisSize: MainAxisSize.min, children: [
                          if (stopping)
                            const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: CodeTerm.red))
                          else
                            const Icon(Icons.stop_circle_outlined, size: 18, color: CodeTerm.red),
                          const SizedBox(width: 8),
                          Text(stopping ? 'Stopping' : 'Stop', style: codeSans(c, size: 14, weight: FontWeight.w600, color: CodeTerm.red)),
                        ]),
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
}
