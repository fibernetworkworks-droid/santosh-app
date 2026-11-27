// v0.939 HOOLA CODE MAKES THINGS (owner, on the design canvas claude.ai/artifact/BjGPb7Tkqfx6QqpgkDznxH -> "GO BUILD"):
// the PRDs, web pages, prototypes, artboards and sheets Hoola Code makes beside the code. Each one is a card in her
// session (screens 1-3: while it makes = the part it is writing now and every part ticked off; ready = its own little
// picture, name and facts; a new version = "Updated"), the "Made in this session" sheet (screen 4), and a full-screen
// viewer per kind (screens 5-8): the PRD as easy reading (or its Markdown), a page / prototype / artboard in a sandboxed
// web view on its signed link, a sheet as a table with its formulas. Versions she can go back to; a change she asks for
// goes to Hoola as her next message.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../state.dart';
import '../chat/hoola_md.dart';
import '../hoola_theme.dart';
import 'code_kit.dart';

IconData codeMadeIcon(String kind) => switch (kind) {
      'doc' => Icons.description_outlined,
      'page' => Icons.web_outlined,
      'prototype' => Icons.touch_app_outlined,
      'artboard' => Icons.dashboard_outlined,
      'sheet' => Icons.grid_on_outlined,
      _ => Icons.insert_drive_file_outlined,
    };

/// The little picture on a card: drawn from what kind of thing it is.
class CodeMadeThumb extends StatelessWidget {
  const CodeMadeThumb(this.kind, {super.key, this.size = 56, this.making = false});
  final String kind;
  final double size;
  final bool making;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final s = size / 56;
    Widget bar(double w, double h, Color col) => Container(width: w * s, height: h * s, decoration: BoxDecoration(color: col, borderRadius: BorderRadius.circular(2)));
    final faint = making ? c.line : c.lineStrong;
    Widget body;
    Color bg = c.sunk;
    switch (kind) {
      case 'prototype':
        bg = c.accentSoft;
        body = Stack(alignment: Alignment.center, children: [
          Container(width: 24 * s, height: 40 * s, decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(5 * s), border: Border.all(color: c.accent, width: 1.5))),
          Positioned(
            right: 6 * s,
            bottom: 6 * s,
            child: Container(
              width: 18 * s,
              height: 18 * s,
              decoration: BoxDecoration(color: c.accent, shape: BoxShape.circle),
              child: Icon(Icons.play_arrow_rounded, size: 13 * s, color: c.onAccent),
            ),
          ),
        ]);
      case 'artboard':
        body = Padding(
          padding: EdgeInsets.all(8 * s),
          child: GridView.count(
            crossAxisCount: 3,
            mainAxisSpacing: 4 * s,
            crossAxisSpacing: 4 * s,
            physics: const NeverScrollableScrollPhysics(),
            padding: EdgeInsets.zero,
            children: [
              for (var i = 0; i < 6; i++)
                Container(decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(2), border: Border.all(color: i == 4 ? c.accent : faint))),
            ],
          ),
        );
      case 'sheet':
        bg = c.okSoft;
        body = Padding(
          padding: EdgeInsets.all(8 * s),
          child: Column(children: [
            for (var r = 0; r < 4; r++)
              Expanded(
                child: Padding(
                  padding: EdgeInsets.only(bottom: 2 * s),
                  child: Row(children: [
                    for (var k = 0; k < 3; k++)
                      Expanded(child: Container(margin: EdgeInsets.only(right: k < 2 ? 2 * s : 0), color: r == 0 ? c.ok : c.surface)),
                  ]),
                ),
              ),
          ]),
        );
      case 'page':
        body = Padding(
          padding: EdgeInsets.all(8 * s),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Container(height: 9 * s, decoration: BoxDecoration(color: c.ink, borderRadius: BorderRadius.circular(2))),
            for (var i = 0; i < 3; i++) ...[
              SizedBox(height: 3 * s),
              Container(height: 7 * s, decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(2), border: Border.all(color: faint))),
            ],
          ]),
        );
      default:
        body = Padding(
          padding: EdgeInsets.fromLTRB(9 * s, 10 * s, 9 * s, 8 * s),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            bar(30, 5, c.ink),
            for (final w in const [40.0, 36.0, 40.0, 24.0]) ...[SizedBox(height: 4 * s), bar(w, 3, faint)],
          ]),
        );
    }
    return Container(
      width: size,
      height: size,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(10 * s)),
      child: body,
    );
  }
}

/// One thing in her thread. [newest] = the latest card of the thread: Open / Share sit under it once it is ready.
class CodeMadeCard extends StatelessWidget {
  const CodeMadeCard({super.key, required this.row, required this.onOpen, this.newest = false, this.onShare});
  final Map<String, dynamic> row;
  final VoidCallback onOpen;
  final VoidCallback? onShare;
  final bool newest;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final kind = cs(row['kind']);
    final making = cs(row['state']) == 'making';
    final parts = cl(row['parts']);
    final v = ci(row['version']);
    final changed = [for (final x in (row['changed'] as List? ?? const [])) cs(x)];
    final now = cs(row['now']);
    final at = DateTime.tryParse(cs(row['at']));
    final secs = at == null ? 0 : DateTime.now().toUtc().difference(at.toUtc()).inSeconds.clamp(0, 359999).toInt();
    final done = parts.where((p) => p['done'] == true).length;
    String line;
    if (making) {
      line = now.isNotEmpty ? '${cs(row['kind_label'])} · writing $now' : '${cs(row['kind_label'])} · $done of ${parts.length} written';
    } else {
      line = [cs(row['kind_label']), cs(row['line'])].where((e) => e.isNotEmpty).join(' · ');
    }
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Semantics(
          button: true,
          label: '${cs(row['title'])}, ${making ? 'being made' : 'open'}',
          child: CodeCard(
            radius: 14,
            padding: const EdgeInsets.all(12),
            onTap: onOpen,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                CodeMadeThumb(kind, making: making),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(cs(row['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 15, weight: FontWeight.w600, height: 1.3)),
                    const SizedBox(height: 3),
                    Text(line, maxLines: 2, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 13, color: c.ink3, height: 1.35)),
                  ]),
                ),
                const SizedBox(width: 8),
                if (making)
                  Text(codeClock(secs), style: codeSans(c, size: 13, color: c.ink2).copyWith(fontFeatures: const [FontFeature.tabularFigures()]))
                else if (v > 1 && changed.isNotEmpty)
                  CodeBadge('Updated', fg: c.ok, bg: c.okSoft)
                else
                  Icon(Icons.chevron_right_rounded, size: 20, color: c.ink3),
              ]),
              if (making && parts.length > 1) ...[
                const SizedBox(height: 12),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final p in parts) _partChip(c, cs(p['name']), p['done'] == true, cs(p['name']) == now),
                ]),
              ],
              if (!making && v > 1 && changed.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text('Version $v · changed ${changed.take(4).join(', ')}${changed.length > 4 ? ' and ${changed.length - 4} more' : ''}',
                    style: codeSans(c, size: 13, color: c.ink2)),
              ],
            ]),
          ),
        ),
        if (newest)
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Wrap(spacing: 8, children: [
              CodeChip(making ? 'Peek' : 'Open', icon: making ? Icons.visibility_outlined : Icons.open_in_full_rounded, onTap: onOpen),
              if (!making && onShare != null) CodeChip(kind == 'sheet' ? 'Download' : 'Share link', icon: kind == 'sheet' ? Icons.download_rounded : Icons.ios_share_rounded, onTap: onShare),
            ]),
          ),
      ]),
    );
  }

  Widget _partChip(HoolaColors c, String name, bool done, bool now) {
    final fg = now ? c.accent : (done ? c.ok : c.ink2);
    final bg = now ? c.accentSoft : (done ? c.okSoft : c.sunk);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (done && !now) ...[Icon(Icons.check_rounded, size: 13, color: fg), const SizedBox(width: 3)],
        Text(name, style: codeSans(c, size: 12, weight: now ? FontWeight.w600 : FontWeight.w400, color: fg)),
      ]),
    );
  }
}

/// A faint line in the thread for an earlier version of a thing (the full card sits with its newest version).
class CodeMadeEarlier extends StatelessWidget {
  const CodeMadeEarlier({super.key, required this.title, required this.v, required this.onOpen});
  final String title;
  final int v;
  final VoidCallback onOpen;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return InkWell(
      onTap: onOpen,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Row(children: [
          Icon(Icons.history_rounded, size: 16, color: c.ink3),
          const SizedBox(width: 8),
          Expanded(child: Text('$title · version $v', maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14, color: c.ink3))),
        ]),
      ),
    );
  }
}

String codeMadeFullUrl(Santosh app, String path) {
  final b = app.api?.baseUrl ?? '';
  final base = b.endsWith('/') ? b.substring(0, b.length - 1) : b;
  return path.startsWith('http') ? path : '$base$path';
}

/// Share / download: the signed link opens in her browser (a sheet or a document downloads there).
Future<void> codeMadeShare(BuildContext context, Santosh app, String taskId, Map<String, dynamic> row) async {
  final d = await codeCall(context, app, 'GET', '/api/devsahayak/tasks/${Uri.encodeComponent(taskId)}/made/${Uri.encodeComponent(cs(row['id']))}', quiet: true);
  final url = cs(d?['url']);
  if (url.isEmpty) {
    if (context.mounted) codeToast(context, 'It is not ready yet.');
    return;
  }
  await launchUrl(Uri.parse(codeMadeFullUrl(app, url)), mode: LaunchMode.externalApplication);
}

/// Screen 4: everything made in this session, newest first, with a kind filter.
Future<void> showCodeMadeList(BuildContext context, Santosh app, String taskId, List<Map<String, dynamic>> rows,
    {required void Function(Map<String, dynamic> row) onOpen}) {
  var pick = 'All';
  const groups = {'Docs': {'doc'}, 'Designs': {'page', 'prototype', 'artboard'}, 'Sheets': {'sheet'}};
  return codeSheet<void>(context, app,
      title: 'Made in this session',
      body: (ctx) => StatefulBuilder(builder: (ctx, set) {
            final c = HoolaColors.of(ctx);
            final shown = [for (final r in rows.reversed) if (pick == 'All' || groups[pick]!.contains(cs(r['kind']))) r];
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('${cPlural(rows.length, 'thing')} · newest first', style: codeSans(c, size: 13, color: c.ink3)),
              const SizedBox(height: 6),
              Wrap(spacing: 6, children: [
                for (final g in const ['All', 'Docs', 'Designs', 'Sheets']) CodeChip(g, on: g == pick, onTap: () => set(() => pick = g)),
              ]),
              for (final r in shown)
                InkWell(
                  onTap: () {
                    Navigator.pop(ctx);
                    onOpen(r);
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.sunk))),
                    child: Row(children: [
                      CodeMadeThumb(cs(r['kind']), size: 44, making: cs(r['state']) == 'making'),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(cs(r['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 15, weight: FontWeight.w600)),
                          Text('${cs(r['kind_label'])} · v${ci(r['version'])}${cs(r['state']) == 'making' ? ' · being made' : (cs(r['line']).isNotEmpty ? ' · ${cs(r['line'])}' : '')}',
                              maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 13, color: c.ink3)),
                        ]),
                      ),
                      Text(codeAgo(cs(r['done_at']).isNotEmpty ? cs(r['done_at']) : cs(r['at'])), style: codeSans(c, size: 12, color: c.ink3)),
                    ]),
                  ),
                ),
              if (shown.isEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 18), child: Text('Nothing of this kind yet.', style: codeSans(c, size: 14, color: c.ink3))),
            ]);
          }));
}

/// Screens 5-8: one thing, full screen. Pops with her change request (text) when she asks for one.
class CodeMadeViewer extends StatefulWidget {
  const CodeMadeViewer({super.key, required this.app, required this.taskId, required this.madeId, this.version = 0});
  final Santosh app;
  final String taskId, madeId;
  final int version;
  @override
  State<CodeMadeViewer> createState() => _CodeMadeViewerState();
}

class _CodeMadeViewerState extends State<CodeMadeViewer> {
  Map<String, dynamic>? _d;
  String? _error;
  int _v = 0;
  bool _markdown = false;
  int _tab = 0;
  String _cell = '';
  WebViewController? _web;
  String _webUrl = '';
  Timer? _poll;
  final _ask = TextEditingController();

  String get _path => '/api/devsahayak/tasks/${Uri.encodeComponent(widget.taskId)}/made/${Uri.encodeComponent(widget.madeId)}';

  @override
  void initState() {
    super.initState();
    _v = widget.version;
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    _ask.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) {
      await Future<void>.value();   // this can run from initState: setState only after it
      if (mounted && _d == null) setState(() => _error = codeLoadFailedLine);
      return;
    }
    if (_error != null && _d == null) setState(() => _error = null);
    try {
      final d = cm(await api.call('GET', _path, query: _v > 0 ? {'v': '$_v'} : null));
      if (!mounted) return;
      final url = cs(d['url']);
      final kind = cs(d['kind']);
      if (url.isNotEmpty && const {'page', 'prototype', 'artboard'}.contains(kind)) {
        final full = codeMadeFullUrl(widget.app, url);
        final sameFile = _webUrl.split('?').first == full.split('?').first;
        if (_web == null) {
          _web = WebViewController()..setJavaScriptMode(JavaScriptMode.unrestricted);
        }
        if (!sameFile || cs(d['shown_state']) == 'making') _web!.loadRequest(Uri.parse(full));
        _webUrl = full;
      }
      setState(() {
        _d = d;
        _error = null;
        if (_tab >= cl(d['sheet']).length) _tab = 0;
      });
      // while Hoola is still making the version she is looking at, it keeps growing in front of her
      final making = cs(d['shown_state']) == 'making';
      if (making && _poll == null) {
        _poll = Timer.periodic(const Duration(seconds: 3), (_) => _load());
      } else if (!making) {
        _poll?.cancel();
        _poll = null;
      }
    } catch (_) {
      // never the raw exception on her screen: one plain line, and Try again while nothing is shown yet
      if (mounted) setState(() => _error = codeLoadFailedLine);
    }
  }

  Future<void> _versions() async {
    final d = _d;
    if (d == null) return;
    final shown = ci(d['shown']);
    final newest = ci(d['version']);
    final pick = await codeSheet<Map<String, dynamic>>(context, widget.app,
        title: 'Versions',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            for (final x in cl(d['versions']))
              Container(
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.sunk))),
                child: Row(children: [
                  Expanded(
                    child: InkWell(
                      onTap: cs(x['state']) == 'ready' || ci(x['v']) == newest ? () => Navigator.pop(ctx, {'see': ci(x['v'])}) : null,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Version ${ci(x['v'])}${ci(x['v']) == shown ? ' · showing' : ''}${cs(x['state']) == 'making' ? ' · being made' : ''}',
                            style: codeSans(c, size: 15, weight: FontWeight.w600)),
                        Text(
                            [
                              if (cs(x['note']).isNotEmpty) cs(x['note']),
                              if ((x['changed'] as List? ?? const []).isNotEmpty)
                                'changed ${(x['changed'] as List).map(cs).take(3).join(', ')}',
                              codeAgo(cs(x['at'])),
                            ].where((e) => e.isNotEmpty).join(' · '),
                            maxLines: 2,
                            style: codeSans(c, size: 13, color: c.ink3)),
                      ]),
                    ),
                  ),
                  if (cs(x['state']) == 'ready' && ci(x['v']) != newest)
                    CodeChip('Bring back', icon: Icons.undo_rounded, onTap: () => Navigator.pop(ctx, {'back': ci(x['v'])})),
                ]),
              ),
            const SizedBox(height: 8),
            Text('Bringing one back makes it the newest version. Nothing is ever deleted.', style: codeSans(c, size: 13, color: c.ink3)),
          ]);
        });
    if (pick == null || !mounted) return;
    if (pick['see'] != null) {
      setState(() => _v = ci(pick['see']));
      _load();
      return;
    }
    final r = await codeCall(context, widget.app, 'POST', '$_path/restore', body: {'v': ci(pick['back'])});
    if (r != null && mounted) {
      codeToast(context, 'Version ${ci(pick['back'])} is back as version ${ci(r['version'])}.');
      setState(() => _v = 0);
      _load();
    }
  }

  void _askChange() {
    final text = _ask.text.trim();
    if (text.isEmpty) return;
    Navigator.of(context).pop(text);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final d = _d;
    final kind = cs(d?['kind']);
    final shown = ci(d?['shown']);
    final making = cs(d?['shown_state']) == 'making';
    final sub = d == null
        ? ''
        : [making ? 'Version $shown · being made' : 'Version $shown', if (ci(d['version']) != shown && !making) 'newest is ${ci(d['version'])}', cs(d['kind_label'])].join(' · ');
    return Scaffold(
      backgroundColor: c.surface,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(
            close: true,
            title: d == null ? 'Opening…' : cs(d['title']),
            sub: sub,
            actions: [
              if (kind == 'prototype') CodeIconButton(icon: Icons.replay_rounded, label: 'Restart', onTap: _web == null ? null : () => _web!.loadRequest(Uri.parse(_webUrl))),
              CodeIconButton(icon: Icons.history_rounded, label: 'Versions', onTap: d == null ? null : _versions),
              CodeIconButton(
                icon: kind == 'sheet' || kind == 'doc' ? Icons.download_rounded : Icons.open_in_browser_rounded,
                label: kind == 'sheet' || kind == 'doc' ? 'Download' : 'Open in browser',
                onTap: cs(d?['url']).isEmpty || making ? null : () => launchUrl(Uri.parse(codeMadeFullUrl(widget.app, cs(d!['url']))), mode: LaunchMode.externalApplication),
              ),
            ],
          ),
          if (making) LinearProgressIndicator(minHeight: 2, color: c.accent, backgroundColor: c.accentSoft),
          Expanded(
            child: d == null
                ? (_error == null ? const Center(child: CodeRing(size: 22)) : CodeLoadFailed(text: _error!, onRetry: _load))
                : _body(c, d, kind),
          ),
          _askBar(c, kind),
        ]),
      ),
    );
  }

  Widget _body(HoolaColors c, Map<String, dynamic> d, String kind) {
    if (kind == 'doc') {
      final text = cs(d['doc']);
      return Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
          child: Row(children: [
            CodeChip('Read', on: !_markdown, onTap: () => setState(() => _markdown = false)),
            const SizedBox(width: 6),
            CodeChip('Markdown', on: _markdown, onTap: () => setState(() => _markdown = true)),
            const Spacer(),
            Text('${cPlural(cl(d['parts']).length, 'section')}', style: codeSans(c, size: 13, color: c.ink3)),
          ]),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
            child: _markdown ? SelectableText(text, style: codeMono(c, size: 13, color: c.ink)) : HoolaMd(text, selectable: true),
          ),
        ),
      ]);
    }
    if (kind == 'sheet') return _sheet(c, d);
    if (_web == null) {
      return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('Nothing to show yet.', style: codeSans(c, color: c.ink2))));
    }
    return Container(color: c.sunk, child: WebViewWidget(controller: _web!));
  }

  Widget _sheet(HoolaColors c, Map<String, dynamic> d) {
    final tabs = cl(d['sheet']);
    if (tabs.isEmpty) return Center(child: Text('Nothing written yet.', style: codeSans(c, color: c.ink2)));
    final tab = tabs[_tab.clamp(0, tabs.length - 1).toInt()];
    final cols = [for (final x in (tab['columns'] as List? ?? const [])) cs(x)];
    final rows = [for (final r in (tab['rows'] as List? ?? const [])) [for (final x in (r as List)) cs(x)]];
    final formulas = cm(tab['formulas']);
    final problems = [for (final x in (tab['problems'] as List? ?? const [])) cs(x)];
    String colName(int i) {
      var s = '';
      var n = i + 1;
      while (n > 0) {
        final r = (n - 1) % 26;
        s = String.fromCharCode(65 + r) + s;
        n = (n - 1) ~/ 26;
      }
      return s;
    }

    bool numeric(String v) => RegExp(r'^-?[\d,]+(\.\d+)?%?$').hasMatch(v.trim());
    Widget cellBox(String text, {bool head = false, bool right = false, String ref = '', double w = 120}) {
      final picked = ref.isNotEmpty && ref == _cell;
      return GestureDetector(
        onTap: ref.isEmpty ? null : () => setState(() => _cell = picked ? '' : ref),
        child: Container(
          width: w,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          decoration: BoxDecoration(
            color: head ? c.sunk : c.surface,
            border: Border(right: BorderSide(color: c.sunk), bottom: BorderSide(color: head ? c.lineStrong : c.sunk)),
          ),
          foregroundDecoration: picked ? BoxDecoration(border: Border.all(color: c.ok, width: 2)) : null,
          child: Text(text,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: right ? TextAlign.right : TextAlign.left,
              style: codeSans(c, size: 14, weight: head ? FontWeight.w600 : FontWeight.w400).copyWith(fontFeatures: const [FontFeature.tabularFigures()])),
        ),
      );
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Container(
        height: 40,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        color: c.bg,
        child: Row(children: [
          if (_cell.isNotEmpty) Text(_cell, style: codeMono(c, size: 12, color: c.ink2)),
          const SizedBox(width: 10),
          Expanded(
            child: Text(_cell.isEmpty ? 'Tap a cell to see its formula' : cs(formulas[_cell]).isEmpty ? 'A value, not a formula' : cs(formulas[_cell]),
                maxLines: 1, overflow: TextOverflow.ellipsis, style: _cell.isEmpty ? codeSans(c, size: 13, color: c.ink3) : codeMono(c, size: 13, color: c.info)),
          ),
        ]),
      ),
      Expanded(
        child: SingleChildScrollView(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [cellBox('#', head: true, w: 44), for (final h in cols) cellBox(h, head: true)]),
              for (var r = 0; r < rows.length; r++)
                Row(children: [
                  cellBox('${r + 2}', w: 44),
                  for (var k = 0; k < cols.length; k++)
                    cellBox(k < rows[r].length ? rows[r][k] : '', right: k < rows[r].length && numeric(rows[r][k]), ref: '${colName(k)}${r + 2}'),
                ]),
            ]),
          ),
        ),
      ),
      if (problems.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Text('The preview could not work out: ${problems.take(3).join('; ')}. Excel or Google Sheets will.', style: codeSans(c, size: 13, color: c.warn)),
        ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
        child: Wrap(spacing: 6, children: [
          for (var i = 0; i < tabs.length; i++) CodeChip(cs(tabs[i]['name']), on: i == _tab, onTap: () => setState(() {
                _tab = i;
                _cell = '';
              })),
        ]),
      ),
    ]);
  }

  Widget _askBar(HoolaColors c, String kind) {
    final what = switch (kind) { 'doc' => 'this document', 'sheet' => 'this sheet', 'prototype' => 'this prototype', 'artboard' => 'these screens', _ => 'this page' };
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
      decoration: BoxDecoration(color: c.surface, border: Border(top: BorderSide(color: c.sunk))),
      child: Container(
        height: 48,
        padding: const EdgeInsets.only(left: 16, right: 4),
        decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(24), border: Border.all(color: c.lineStrong)),
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: _ask,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _askChange(),
              onChanged: (_) => setState(() {}),
              style: codeSans(c, size: 15),
              decoration: codeBareInput(c, hint: 'Ask for a change to $what', size: 15),
            ),
          ),
          Semantics(
            button: true,
            label: 'Send',
            child: InkResponse(
              onTap: _ask.text.trim().isEmpty ? null : _askChange,
              radius: 22,
              child: Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(color: _ask.text.trim().isEmpty ? c.line : c.pill, shape: BoxShape.circle),
                child: Icon(Icons.arrow_upward_rounded, size: 18, color: _ask.text.trim().isEmpty ? c.ink3 : c.onPill),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
