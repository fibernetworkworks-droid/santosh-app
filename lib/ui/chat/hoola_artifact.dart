// v0.902 PAGE PRO (owner: "NOW LET'S WORK ON ARTIFACT :: CURRENTLY HOOLA ARTIFACT ARE MESSY MAKE IT MORE PROFESSIONAL AND
// ADVANCE", with pictures of Claude's own artifact card, viewer and its menu): a page Hoola makes is shown the way Claude
// shows an artifact.
//
//   the card      = a drawn page thumbnail, the title, one status line in plain words (the real step + a live clock
//                   while it is made, "Version 3 · made in 0:48" when ready), the summary, step marks while it works,
//                   Stop / Try again / Share + Open in the card's own footer.
//   the pages pill = "3 pages" above the composer when this chat made pages; tap = every page of the chat in a sheet.
//
// The viewer itself (header, versions, share, the change box) is ArtifactScreen in artifact_screen.dart.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../artifact_screen.dart' show openArtifact, artifactAgo, openArtifactShare;
import '../hoola_theme.dart';
import 'hoola_card.dart' show hcMain, hcQuiet;
import 'hoola_cards_all.dart' show hcStop;

String _s(Object? v) => v == null ? '' : '$v'.trim();
int _n(Object? v) => v is num ? v.toInt() : (int.tryParse('${v ?? ''}') ?? 0);

/// The builder's real steps, in order (the server's `stage`).
const artifactSteps = [('read', 'Brief read'), ('writing', 'Writing the page'), ('checking', 'Checking it opens'), ('done', 'Ready')];

/// Which step is running (1 = writing when the server named none).
int artifactStepIndex(String stage) {
  final i = artifactSteps.indexWhere((s) => s.$1 == stage);
  return i < 1 ? 1 : i;
}

/// "0:48" / "2:05" for a page's build time.
String artifactClock(num seconds) {
  final s = seconds < 0 ? 0 : seconds.floor();
  return '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';
}

/// What one page is doing, from its card data (tested).
({String state, String line}) artifactState(Map<String, dynamic> v, {DateTime? now}) {
  final status = _s(v['status']).isEmpty ? 'ready' : _s(v['status']);
  final stage = _s(v['stage']);
  final version = _n(v['version']) < 1 ? 1 : _n(v['version']);
  final took = v['build_s'] is num ? artifactClock(v['build_s'] as num) : '';
  switch (status) {
    case 'building':
      final step = artifactSteps[artifactStepIndex(stage)].$2;
      final t0 = DateTime.tryParse(_s(v['started_at']));
      final clock = t0 == null ? '' : ' · ${artifactClock((now ?? DateTime.now()).toUtc().difference(t0.toUtc()).inSeconds)}';
      return (state: 'building', line: '$step$clock');
    case 'failed':
      return (state: 'failed', line: stage == 'stopped' ? 'Stopped' : 'Not made');
    case 'deleted':
      return (state: 'deleted', line: 'Removed');
    default:
      final kept = (stage == 'stopped' || stage == 'failed') && version > 0;
      if (kept) return (state: 'ready', line: 'Version $version · the newer one was not made');
      return (state: 'ready', line: took.isEmpty ? 'Version $version' : 'Version $version · made in $took');
  }
}

/// A small drawn page: a title bar, lines and a block - the page's own look is in the viewer.
class PageThumb extends StatelessWidget {
  const PageThumb({super.key, this.size = 56, this.working = false, this.failed = false});
  final double size;
  final bool working, failed;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final tone = failed ? c.bad : c.accent;
    Widget bar(double w, Color col, {double h = 4}) =>
        Container(width: size * w, height: h, decoration: BoxDecoration(color: col, borderRadius: BorderRadius.circular(2)));
    return ExcludeSemantics(
      child: Container(
        width: size,
        height: size * 1.12,
        padding: EdgeInsets.all(size * .13),
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: BorderRadius.circular(HoolaRadius.tile),
          border: Border.all(color: c.lineStrong),
        ),
        child: Stack(children: [
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            bar(.46, tone.withOpacity(.75), h: 5),
            SizedBox(height: size * .09),
            bar(.72, c.line),
            SizedBox(height: size * .06),
            bar(.6, c.line),
            const Spacer(),
            Container(
              height: size * .26,
              decoration: BoxDecoration(color: tone.withOpacity(.14), borderRadius: BorderRadius.circular(4)),
            ),
          ]),
          if (working)
            Center(child: SizedBox(width: size * .34, height: size * .34, child: CircularProgressIndicator(strokeWidth: 2, color: c.accent))),
        ]),
      ),
    );
  }
}

/// The chat card for a page Hoola made (one card per page; it updates as new versions arrive).
class HCArtifact extends StatefulWidget {
  const HCArtifact({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HCArtifact> createState() => _HCArtifactState();
}

class _HCArtifactState extends State<HCArtifact> {
  Timer? _tick;
  bool _stopping = false;

  Map<String, dynamic> get v => widget.v;

  @override
  void initState() {
    super.initState();
    _clock();
  }

  @override
  void didUpdateWidget(HCArtifact old) {
    super.didUpdateWidget(old);
    _clock();
  }

  void _clock() {
    final building = _s(v['status']) == 'building';
    if (building && _tick == null) {
      _tick = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() {});
      });
    } else if (!building) {
      _tick?.cancel();
      _tick = null;
      _stopping = false;
    }
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  Future<void> _stop() async {
    final api = widget.app.api;
    final id = _s(v['id']);
    if (api == null || id.isEmpty) return;
    HapticFeedback.lightImpact();
    setState(() => _stopping = true);
    try {
      await api.artifactStop(id);
    } catch (e) {
      if (mounted) {
        setState(() => _stopping = false);
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text('$e'.replaceFirst('Exception: ', ''))));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final app = widget.app;
    final id = _s(v['id']);
    final title = _s(v['title']).isEmpty ? 'Page' : _s(v['title']);
    final st = artifactState(v);
    final building = st.state == 'building', failed = st.state == 'failed', deleted = st.state == 'deleted';
    final summary = _s(v['summary']);
    final error = _s(v['error']);
    final tone = building ? c.accent : failed ? c.bad : deleted ? c.ink3 : c.ok;
    final canOpen = !deleted && !failed && id.isNotEmpty && (!building || _n(v['version']) > 1);
    final cur = artifactStepIndex(_s(v['stage']));
    return Semantics(
      container: true,
      label: 'Page $title, ${st.line}',
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: BorderRadius.circular(HoolaRadius.cardLg),
          border: Border.all(color: c.line),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          InkWell(
            onTap: canOpen ? () => openArtifact(context, app, id, title) : null,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 14, 16, 14),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                PageThumb(working: building, failed: failed),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Page', style: HoolaType.label(c).copyWith(color: c.ink3)),
                    const SizedBox(height: 2),
                    Text(title, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
                    const SizedBox(height: 5),
                    Row(children: [
                      Container(width: 7, height: 7, decoration: BoxDecoration(color: tone, shape: BoxShape.circle)),
                      const SizedBox(width: 7),
                      Flexible(
                        child: Text(st.line,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: HoolaType.small(c).copyWith(
                                color: building ? c.accent : failed ? c.bad : c.ink2,
                                fontWeight: FontWeight.w500,
                                fontFeatures: const [FontFeature.tabularFigures()])),
                      ),
                    ]),
                    if (summary.isNotEmpty && !failed && !deleted) ...[
                      const SizedBox(height: 8),
                      Text(summary, maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14)),
                    ],
                    if (failed) ...[
                      const SizedBox(height: 8),
                      Text(error.isEmpty ? 'The page could not be made.' : error,
                          style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14)),
                    ],
                  ]),
                ),
              ]),
            ),
          ),
          if (building)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Row(children: [
                  for (var i = 0; i < artifactSteps.length; i++) ...[
                    if (i > 0) const SizedBox(width: 4),
                    Expanded(
                      child: Container(
                        height: 4,
                        decoration: BoxDecoration(
                          color: i < cur ? c.ok : i == cur ? c.accent : c.sunk,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                  ],
                ]),
                const SizedBox(height: 6),
                Text('Usually 20 to 90 seconds. It opens here when ready.', style: HoolaType.small(c)),
              ]),
            ),
          if (!deleted)
            Container(
              padding: const EdgeInsets.fromLTRB(6, 6, 10, 8),
              decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
              child: Row(children: [
                if (!building && !failed && id.isNotEmpty)
                  hcQuiet(context, 'Share', () => openArtifactShare(context, app, id, title)),
                const Spacer(),
                if (building) hcStop(context, _stopping ? null : _stop, label: _stopping ? 'Stopping…' : 'Stop'),
                if (building && canOpen) ...[const SizedBox(width: 8), hcMain(context, 'Open', () => openArtifact(context, app, id, title))],
                if (failed && _s(v['stage']) != 'stopped')
                  hcMain(context, 'Try again', () => app.send('Make the page "$title" again'), icon: Icons.refresh_rounded),
                if (failed && _s(v['stage']) == 'stopped')
                  hcQuiet(context, 'Make it again', () => app.send('Make the page "$title" again')),
                if (!building && !failed && id.isNotEmpty)
                  hcMain(context, 'Open', () => openArtifact(context, app, id, title), icon: Icons.open_in_full_rounded),
              ]),
            ),
        ]),
      ),
    );
  }
}

/// Every page this chat made, newest first (deleted ones left out).
List<Map<String, dynamic>> chatPages(Santosh app) {
  final seen = <String>{};
  final out = <Map<String, dynamic>>[];
  for (var i = app.feed.length - 1; i >= 0; i--) {
    final f = app.feed[i];
    if (f.kind != 'artifact') continue;
    final id = _s(f.data['id']);
    if (id.isEmpty || !seen.add(id) || _s(f.data['status']) == 'deleted') continue;
    out.add(f.data);
  }
  return out;
}

/// "3 pages" above the composer; tap = the list of this chat's pages.
class PagesPill extends StatelessWidget {
  const PagesPill({super.key, required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final n = chatPages(app).length;
    if (n == 0) return const SizedBox.shrink();
    return Semantics(
      button: true,
      label: n == 1 ? '1 page in this chat' : '$n pages in this chat',
      child: Material(
        color: c.surface,
        shape: StadiumBorder(side: BorderSide(color: c.line)),
        elevation: 0,
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: () => showPagesSheet(context, app),
          child: Container(
            height: 48,   // the whole pill is the tap target (48 dp)
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.auto_awesome_mosaic_outlined, size: 17, color: c.ink2),
              const SizedBox(width: 8),
              ExcludeSemantics(
                child: Text(n == 1 ? '1 page' : '$n pages', style: HoolaType.body(c).copyWith(fontSize: 14, fontWeight: FontWeight.w500)),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

Future<void> showPagesSheet(BuildContext context, Santosh app) {
  final c = HoolaColors.of(context);
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: c.bg,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => HoolaTheme(
      appearance: app.appearance,
      child: Builder(builder: (ctx) {
        final c = HoolaColors.of(ctx);
        final pages = chatPages(app);
        return ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * .8),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Center(
              child: Container(
                width: 40,
                height: 5,
                margin: const EdgeInsets.only(top: 10, bottom: 14),
                decoration: BoxDecoration(color: c.lineStrong, borderRadius: BorderRadius.circular(5)),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
              child: Semantics(header: true, child: Text('Pages in this chat', style: HoolaType.heading(c))),
            ),
            Flexible(
              child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(12, 0, 12, 16), children: [
                for (final p in pages)
                  InkWell(
                    borderRadius: BorderRadius.circular(HoolaRadius.card),
                    onTap: _s(p['status']) == 'failed'
                        ? null
                        : () {
                            Navigator.of(ctx).pop();
                            openArtifact(context, app, _s(p['id']), _s(p['title']));
                          },
                    child: Padding(
                      padding: const EdgeInsets.all(8),
                      child: Row(children: [
                        PageThumb(size: 44, working: _s(p['status']) == 'building', failed: _s(p['status']) == 'failed'),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(_s(p['title']).isEmpty ? 'Page' : _s(p['title']),
                                maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                            Text([artifactState(p).line, artifactAgo(_s(p['updated_at']))].where((x) => x.isNotEmpty).join(' · '),
                                maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
                          ]),
                        ),
                        Icon(Icons.chevron_right_rounded, color: c.ink3),
                      ]),
                    ),
                  ),
              ]),
            ),
          ]),
        );
      }),
    ),
  );
}
