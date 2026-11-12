// v0.866 R6 WORK + MADE + CONNECT (docs/HOOLA_APP_REDESIGN_PLAN.md R6): the three other tabs of the new shell, in the
// new design, on the APIs that already exist (nothing new on the server):
//
//   Work     - what needs her, what is running, what finished this week (GET /api/kaam/list) plus every chat whose
//              turn result (R3s) says needs you / working / did not finish; a tap opens the chat. Her AI team and the
//              old Today page stay one tap away until R7 / R8 move them.
//   Made     - everything Hoola made: pages (GET /api/artifacts) and Create studio pictures, songs, voice-overs and
//              scripts (GET /api/create/items); search + type filter; a page opens full screen, a picture opens large,
//              anything else is shared out to her phone's apps.
//   Connect  - search on top, Connected (her linked apps), Add a connection (apps waiting for her sign-in), Ready to
//              use (built in). Linking = the same server link as before (app.linkApp); removing asks first. The full
//              catalogue (spend limits, address, shops) stays one tap away until R7.
//
// Every colour / size / movement comes from hoola_theme.dart. Labels are English; state words come from the
// phone (never the server's Hinglish `say`).
import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import '../../native.dart';
import '../../state.dart';
import '../artifact_screen.dart' show openArtifact;
import '../hoola_theme.dart';

// ------------------------------------------------------------------ shared parts
/// Data the screenshot tests hand the tabs (the tests run without a server). Never set in the app.
class HoolaTabsDebug {
  static Map<String, dynamic>? kaam, catalog;
  static List<Map<String, dynamic>>? pages, creations, apps;
}

String _s(Object? v) => v == null ? '' : '$v';

/// "Today 14:05", "Yesterday 09:12", "12 Nov 18:40" (local time).
String hoolaWhen(DateTime? t) {
  if (t == null) return '';
  t = t.toLocal();
  final hm = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  final now = DateTime.now();
  bool same(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;
  if (same(t, now)) return 'Today $hm';
  if (same(t, now.subtract(const Duration(days: 1)))) return 'Yesterday $hm';
  const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return '${t.day} ${m[t.month - 1]} $hm';
}

DateTime? _date(Object? v) {
  if (v is num) return DateTime.fromMillisecondsSinceEpoch((v * 1000).round(), isUtc: true);
  return DateTime.tryParse(_s(v));
}

/// The big title of a tab + an optional action on the right.
class HoolaTabHeader extends StatelessWidget {
  const HoolaTabHeader({super.key, required this.title, this.sub = '', this.action});
  final String title, sub;
  final Widget? action;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, HoolaSpace.s16, HoolaSpace.s8, HoolaSpace.s8),
      child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Semantics(header: true, child: Text(title, style: HoolaType.display(c))),
            if (sub.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 2), child: Text(sub, style: HoolaType.small(c))),
          ]),
        ),
        if (action != null) action!,
      ]),
    );
  }
}

/// A small section label ("Needs you · 2").
class HoolaSection extends StatelessWidget {
  const HoolaSection(this.text, {super.key, this.count, this.color});
  final String text;
  final int? count;
  final Color? color;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, HoolaSpace.s20, HoolaSpace.gutter, HoolaSpace.s8),
      child: Row(children: [
        if (color != null) ...[
          Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 8),
        ],
        Text(count == null ? text : '$text · $count', style: HoolaType.label(c).copyWith(fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

/// One row inside a grouped card: tile, title, one line under it, something on the right.
class HoolaRow extends StatelessWidget {
  const HoolaRow({
    super.key,
    required this.title,
    this.sub = '',
    this.icon = Icons.circle_outlined,
    this.tint,
    this.tile,
    this.trailing,
    this.onTap,
    this.onLongPress,
    this.semantics = '',
  });
  final String title, sub, semantics;
  final IconData icon;
  final Color? tint;
  final Widget? tile, trailing;
  final VoidCallback? onTap, onLongPress;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final t = tint ?? c.ink2;
    return Semantics(
      button: onTap != null,
      label: semantics.isEmpty ? null : semantics,
      child: InkWell(
        onTap: onTap,
        onLongPress: onLongPress,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 60),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.s12, vertical: 10),
            child: Row(children: [
              tile ??
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(color: t.withOpacity(.12), borderRadius: BorderRadius.circular(HoolaRadius.tile)),
                    child: Icon(icon, size: 20, color: t),
                  ),
              const SizedBox(width: HoolaSpace.s12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Text(title, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                  if (sub.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
                    ),
                ]),
              ),
              if (trailing != null) ...[const SizedBox(width: HoolaSpace.s8), trailing!],
            ]),
          ),
        ),
      ),
    );
  }
}

/// Rows grouped on one card with hairlines between them.
class HoolaGroup extends StatelessWidget {
  const HoolaGroup({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
      child: Material(
        color: c.surface,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(HoolaRadius.card), side: BorderSide(color: c.line)),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          for (var i = 0; i < children.length; i++) ...[
            if (i > 0) Divider(height: 1, thickness: 1, indent: 64, color: c.line),
            children[i],
          ],
        ]),
      ),
    );
  }
}

/// The search field on top of Made and Connect.
class HoolaSearch extends StatelessWidget {
  const HoolaSearch({super.key, required this.controller, required this.hint, required this.onChanged});
  final TextEditingController controller;
  final String hint;
  final ValueChanged<String> onChanged;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s4, HoolaSpace.gutter, HoolaSpace.s4),
      child: TextField(
        controller: controller,
        onChanged: onChanged,
        textInputAction: TextInputAction.search,
        style: HoolaType.body(c),
        decoration: InputDecoration(
          isDense: true,
          hintText: hint,
          hintStyle: HoolaType.body(c).copyWith(color: c.ink3),
          prefixIcon: Icon(Icons.search_rounded, color: c.ink3, size: 20),
          suffixIcon: controller.text.isEmpty
              ? null
              : IconButton(
                  tooltip: 'Clear',
                  icon: Icon(Icons.close_rounded, color: c.ink3, size: 18),
                  onPressed: () {
                    controller.clear();
                    onChanged('');
                  }),
          filled: true,
          fillColor: c.sunk,
          contentPadding: const EdgeInsets.symmetric(vertical: 12),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(HoolaRadius.pill), borderSide: BorderSide.none),
        ),
      ),
    );
  }
}

/// A row of filter chips (one picked).
class HoolaChips extends StatelessWidget {
  const HoolaChips({super.key, required this.items, required this.picked, required this.onPick});
  final List<(String, String)> items;   // (key, label)
  final String picked;
  final ValueChanged<String> onPick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return SizedBox(
      height: 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
        children: [
          for (final (k, label) in items)
            Padding(
              padding: const EdgeInsets.only(right: HoolaSpace.s8),
              child: Semantics(
                selected: k == picked,
                button: true,
                child: InkWell(
                  borderRadius: BorderRadius.circular(HoolaRadius.pill),
                  onTap: () {
                    HapticFeedback.selectionClick();
                    onPick(k);
                  },
                  // R9: the whole 48 dp row height takes the tap; the pill drawn inside stays 36
                  child: Center(child: AnimatedContainer(
                    height: 36,
                    duration: HoolaMotion.of(context, HoolaMotion.menu),
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: k == picked ? c.pill : c.surface,
                      borderRadius: BorderRadius.circular(HoolaRadius.pill),
                      border: Border.all(color: k == picked ? c.pill : c.line),
                    ),
                    child: Text(label,
                        style: HoolaType.label(c).copyWith(
                            fontSize: 13, color: k == picked ? c.onPill : c.ink2, fontWeight: FontWeight.w500)),
                  )),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Empty, loading and failed states, the same on every tab.
class HoolaEmpty extends StatelessWidget {
  const HoolaEmpty({super.key, required this.icon, required this.title, this.sub = '', this.onRetry});
  final IconData icon;
  final String title, sub;
  final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(32, 48, 32, 32),
      child: Column(children: [
        Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(color: c.sunk, shape: BoxShape.circle),
          child: Icon(icon, color: c.ink3, size: 26),
        ),
        const SizedBox(height: HoolaSpace.s16),
        Text(title, textAlign: TextAlign.center, style: HoolaType.title(c)),
        if (sub.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(sub, textAlign: TextAlign.center, style: HoolaType.small(c)),
          ),
        if (onRetry != null)
          Padding(
            padding: const EdgeInsets.only(top: HoolaSpace.s16),
            child: OutlinedButton(
              onPressed: onRetry,
              style: OutlinedButton.styleFrom(
                foregroundColor: c.ink,
                side: BorderSide(color: c.lineStrong),
                shape: const StadiumBorder(),
                minimumSize: const Size(0, HoolaSpace.touch),
              ),
              child: const Text('Try again'),
            ),
          ),
      ]),
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
            width: 22,
            height: 22,
            child: CircularProgressIndicator(strokeWidth: 2, color: HoolaColors.of(context).ink3),
          ),
        ),
      );
}

String _plainError(Object e) {
  final t = '$e'.replaceFirst('Exception: ', '');
  if (t.contains('SocketException') || t.contains('TimeoutException') || t.contains('Connection')) {
    return 'Hoola could not be reached. Check the internet and try again.';
  }
  return t.length > 160 ? '${t.substring(0, 159)}…' : t;
}

// ================================================================== WORK
/// The Work tab.
class HoolaWork extends StatefulWidget {
  const HoolaWork({super.key, required this.app, required this.onOpenChat, required this.onTeam, required this.onToday});
  final Santosh app;
  final ValueChanged<String> onOpenChat;
  final VoidCallback onTeam, onToday;
  @override
  State<HoolaWork> createState() => _HoolaWorkState();
}

/// One line of her work, from the kaam list or from a chat's turn result.
class WorkItem {
  WorkItem({required this.title, required this.state, this.detail = '', this.at, this.conv = '', this.call = false});
  final String title, state, detail, conv;   // state: waiting | working | queued | done | partial | failed | stopped
  final DateTime? at;
  final bool call;
}

/// Pure: turns the kaam list + the chat list's turn results into the three sections (tested).
({List<WorkItem> needs, List<WorkItem> running, List<WorkItem> done}) workSections(
    Map<String, dynamic> kaam, List<Map<String, dynamic>> chats) {
  List<Map<String, dynamic>> rows(String k) =>
      [for (final x in ((kaam[k] as List?) ?? const [])) Map<String, dynamic>.from(x as Map)];
  WorkItem item(Map<String, dynamic> r, String state) => WorkItem(
        title: _s(r['title']).isNotEmpty ? _s(r['title']) : (_s(r['label']).isNotEmpty ? _s(r['label']) : 'Work'),
        state: r['stuck'] == true ? 'stuck' : state,
        detail: _s(r['detail']),
        at: _date(r['at']),
        conv: _s(r['conversation_id']),
        call: r['from_call'] == true,
      );
  final needs = [for (final r in rows('waiting')) item(r, 'waiting')];
  final running = [for (final r in rows('running')) item(r, 'working')];
  final done = [
    for (final r in rows('done'))
      item(r, switch (_s(r['state'])) { 'failed' || 'stuck' => 'failed', 'stopped' => 'stopped', 'partial' => 'partial', _ => 'done' })
  ];
  final known = {for (final w in [...needs, ...running]) if (w.conv.isNotEmpty) w.conv};
  for (final ch in chats) {
    final id = _s(ch['id']);
    final res = ch['result'] is Map ? Map<String, dynamic>.from(ch['result'] as Map) : const <String, dynamic>{};
    final st = _s(res['status']);
    if (id.isEmpty || known.contains(id)) continue;
    final title = _s(ch['title']).isNotEmpty ? _s(ch['title']) : 'Chat';
    final at = _date(ch['updated_at'] ?? ch['at']);
    if (st == 'needs_you') {
      needs.add(WorkItem(title: title, state: 'waiting', detail: _s(res['line']), at: at, conv: id));
    } else if (st == 'working' || st == 'queued') {
      running.add(WorkItem(title: title, state: st, detail: _s(res['line']), at: at, conv: id));
    }
  }
  int newest(WorkItem a, WorkItem b) => (b.at ?? DateTime(2000)).compareTo(a.at ?? DateTime(2000));
  needs.sort(newest);
  running.sort(newest);
  done.sort(newest);
  return (needs: needs, running: running, done: done);
}

/// The plain word for a state (English; the server's Hinglish `say` is never shown).
String workStateWord(String state) => switch (state) {
      'waiting' => 'Needs your answer',
      'working' => 'Working',
      'queued' => 'Waiting to start',
      'stuck' => 'Stuck - no progress for a while',
      'partial' => 'Partly done',
      'failed' => 'Did not finish',
      'stopped' => 'Stopped',
      _ => 'Done',
    };

class _HoolaWorkState extends State<HoolaWork> {
  Map<String, dynamic>? _kaam;
  String _err = '';
  bool _showAllDone = false;
  Timer? _tick;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
    // her list moves while she looks at it: a quiet refresh every 30 s while this tab is open
    _tick = Timer.periodic(const Duration(seconds: 30), (_) => _load(quiet: true));
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  Future<void> _load({bool quiet = false}) async {
    final api = app.api;
    if (api == null) {
      if (mounted) setState(() => _kaam = HoolaTabsDebug.kaam ?? const {});
      return;
    }
    try {
      final r = await api.kaamList();
      unawaited(app.refreshChats().catchError((_) {}));
      if (!mounted) return;
      setState(() {
        _kaam = r;
        _err = '';
      });
    } catch (e) {
      if (!mounted || quiet) return;
      setState(() {
        _kaam ??= const {};
        _err = _plainError(e);
      });
    }
  }

  IconData _icon(String st) => switch (st) {
        'waiting' => Icons.pan_tool_alt_outlined,
        'working' || 'queued' => Icons.autorenew_rounded,
        'stuck' => Icons.hourglass_bottom_rounded,
        'failed' => Icons.error_outline_rounded,
        'stopped' => Icons.stop_circle_outlined,
        'partial' => Icons.timelapse_rounded,
        _ => Icons.check_circle_outline_rounded,
      };

  Color _tint(HoolaColors c, String st) => switch (st) {
        'waiting' || 'stuck' || 'partial' => c.warn,
        'working' || 'queued' => c.accent,
        'failed' => c.bad,
        'stopped' => c.ink3,
        _ => c.ok,
      };

  Widget _row(HoolaColors c, WorkItem w) {
    final sub = [
      if (w.detail.isNotEmpty && w.detail != w.title) w.detail else workStateWord(w.state),
      if (w.at != null) hoolaWhen(w.at),
      if (w.call) 'from a call',
    ].join(' · ');
    return HoolaRow(
      title: w.title,
      sub: sub,
      icon: _icon(w.state),
      tint: _tint(c, w.state),
      semantics: '${workStateWord(w.state)}: ${w.title}',
      trailing: w.conv.isEmpty ? null : Icon(Icons.chevron_right_rounded, color: c.ink3),
      onTap: w.conv.isEmpty ? null : () => widget.onOpenChat(w.conv),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final k = _kaam;
        final parts = k == null ? null : workSections(k, app.chatList);
        final done = parts == null ? const <WorkItem>[] : parts.done;
        final shownDone = _showAllDone ? done : done.take(8).toList();
        final empty = parts != null && parts.needs.isEmpty && parts.running.isEmpty && done.isEmpty;
        final sub = parts == null
            ? ''
            : [
                if (parts.needs.isNotEmpty) '${parts.needs.length} need${parts.needs.length == 1 ? 's' : ''} you',
                if (parts.running.isNotEmpty) '${parts.running.length} running',
                if (parts.needs.isEmpty && parts.running.isEmpty) 'Nothing waiting on you',
              ].join(' · ');
        return RefreshIndicator(
          color: c.accent,
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.only(bottom: HoolaSpace.s24),
            children: [
              HoolaTabHeader(title: 'Work', sub: sub),
              if (parts == null)
                const _Loading()
              else if (_err.isNotEmpty && empty)
                HoolaEmpty(icon: Icons.cloud_off_rounded, title: 'Your work could not be opened', sub: _err, onRetry: _load)
              else if (empty)
                const HoolaEmpty(
                    icon: Icons.task_alt_rounded,
                    title: 'No work this week yet',
                    sub: 'Ask Hoola for something in the chat. Long jobs, things waiting for your answer and finished work show here.')
              else ...[
                if (parts.needs.isNotEmpty) ...[
                  HoolaSection('Needs you', count: parts.needs.length, color: c.warn),
                  HoolaGroup(children: [for (final w in parts.needs) _row(c, w)]),
                ],
                if (parts.running.isNotEmpty) ...[
                  HoolaSection('In progress', count: parts.running.length, color: c.accent),
                  HoolaGroup(children: [for (final w in parts.running) _row(c, w)]),
                ],
                if (done.isNotEmpty) ...[
                  HoolaSection('Done this week', count: done.length, color: c.ok),
                  HoolaGroup(children: [
                    for (final w in shownDone) _row(c, w),
                    if (done.length > shownDone.length)
                      HoolaRow(
                        title: 'Show all ${done.length}',
                        icon: Icons.expand_more_rounded,
                        onTap: () => setState(() => _showAllDone = true),
                      ),
                  ]),
                ],
              ],
              const HoolaSection('More'),
              HoolaGroup(children: [
                HoolaRow(
                  title: 'Your AI team',
                  sub: 'The AI employees you hired and their desks',
                  icon: Icons.groups_2_outlined,
                  tint: c.accent,
                  trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
                  onTap: widget.onTeam,
                ),
                HoolaRow(
                  title: 'Today',
                  sub: 'Your briefing, reminders and live jobs (the older page)',
                  icon: Icons.wb_sunny_outlined,
                  trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
                  onTap: widget.onToday,
                ),
              ]),
            ],
          ),
        );
      },
    );
  }
}

// ================================================================== MADE
/// One thing Hoola made, from either list.
class MadeItem {
  MadeItem({required this.id, required this.kind, required this.title, this.sub = '', this.at, this.mime = '', this.status = 'ready', this.size = 0});
  final String id, kind, title, sub, mime, status;   // kind: page | picture | audio | document | other
  final DateTime? at;
  final int size;
}

/// Pure: pages + Create items into one newest-first list (tested).
List<MadeItem> madeItems(List<Map<String, dynamic>> pages, List<Map<String, dynamic>> creations) {
  String kindOf(Map<String, dynamic> i) {
    final k = _s(i['kind']), m = _s(i['mime']);
    if (k == 'image' || k == 'cast' || m.startsWith('image/')) return 'picture';
    if (k == 'song' || k == 'voice' || m.startsWith('audio/')) return 'audio';
    if (m.startsWith('video/')) return 'video';
    if (k == 'script' || m.startsWith('text/') || m.contains('pdf') || m.contains('word') || m.contains('sheet')) return 'document';
    return 'other';
  }

  final out = <MadeItem>[
    for (final a in pages)
      if (_s(a['id']).isNotEmpty)
        MadeItem(
          id: _s(a['id']),
          kind: 'page',
          title: _s(a['title']).isEmpty ? 'Page' : _s(a['title']),
          sub: _s(a['summary']),
          at: _date(a['updated_at'] ?? a['created_at']),
          status: _s(a['status']).isEmpty ? 'ready' : _s(a['status']),
        ),
    for (final i in creations)
      if (_s(i['id']).isNotEmpty)
        MadeItem(
          id: _s(i['id']),
          kind: kindOf(i),
          title: _s(i['title']).isEmpty ? 'Hoola creation' : _s(i['title']),
          at: _date(i['created']),
          mime: _s(i['mime']),
          size: (i['size'] as num?)?.toInt() ?? 0,
        ),
  ];
  out.sort((a, b) => (b.at ?? DateTime(2000)).compareTo(a.at ?? DateTime(2000)));
  return out;
}

/// The Made tab.
class HoolaMade extends StatefulWidget {
  const HoolaMade({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaMade> createState() => _HoolaMadeState();
}

class _HoolaMadeState extends State<HoolaMade> {
  List<MadeItem>? _items;
  String _err = '';
  String _kind = 'all';
  String _q = '';
  final _search = TextEditingController();
  int _artTick = 0;

  Santosh get app => widget.app;

  static const _kinds = [
    ('all', 'All'),
    ('page', 'Pages'),
    ('picture', 'Pictures'),
    ('audio', 'Audio'),
    ('video', 'Video'),
    ('document', 'Documents'),
  ];

  @override
  void initState() {
    super.initState();
    _artTick = app.artifactTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _search.dispose();
    super.dispose();
  }

  void _onApp() {
    if (app.artifactTick != _artTick) {
      _artTick = app.artifactTick;
      _load(quiet: true);
    }
  }

  Future<void> _load({bool quiet = false}) async {
    final api = app.api;
    if (api == null) {
      if (mounted) setState(() => _items = madeItems(HoolaTabsDebug.pages ?? const [], HoolaTabsDebug.creations ?? const []));
      return;
    }
    try {
      final r = await Future.wait([api.artifacts(), api.createItems().catchError((_) => <Map<String, dynamic>>[])]);
      if (!mounted) return;
      setState(() {
        _items = madeItems(r[0], r[1]);
        _err = '';
      });
    } catch (e) {
      if (!mounted || quiet) return;
      setState(() {
        _items ??= const [];
        _err = _plainError(e);
      });
    }
  }

  IconData _icon(String kind) => switch (kind) {
        'page' => Icons.auto_awesome_mosaic_outlined,
        'picture' => Icons.image_outlined,
        'audio' => Icons.graphic_eq_rounded,
        'video' => Icons.movie_outlined,
        'document' => Icons.description_outlined,
        _ => Icons.insert_drive_file_outlined,
      };

  String _kindWord(String kind) => switch (kind) {
        'page' => 'Page',
        'picture' => 'Picture',
        'audio' => 'Audio',
        'video' => 'Video',
        'document' => 'Document',
        _ => 'File',
      };

  Widget _thumb(HoolaColors c, MadeItem m) {
    final api = app.api;
    if (m.kind != 'picture' || api == null) {
      return Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(color: c.accentSoft, borderRadius: BorderRadius.circular(HoolaRadius.tile)),
        child: Icon(_icon(m.kind), color: c.accent, size: 22),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(HoolaRadius.tile),
      child: Container(
        width: 48,
        height: 48,
        color: c.sunk,
        child: Image.network(
          api.createItemUrl(m.id),
          headers: api.authHeaders,
          fit: BoxFit.cover,
          cacheWidth: 144,
          errorBuilder: (_, __, ___) => Icon(Icons.image_outlined, color: c.ink3, size: 22),
        ),
      ),
    );
  }

  Future<void> _open(MadeItem m) async {
    HapticFeedback.selectionClick();
    if (m.kind == 'page') {
      await openArtifact(context, app, m.id, m.title);
      unawaited(_load(quiet: true));
      return;
    }
    if (m.kind == 'picture') {
      await Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => HoolaTheme(appearance: app.appearance, child: _PictureView(app: app, item: m))));
      return;
    }
    await _share(m);
  }

  Future<void> _share(MadeItem m) async {
    final api = app.api;
    if (api == null) return;
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(const SnackBar(content: Text('Getting the file…'), duration: Duration(seconds: 2)));
    try {
      final bytes = await api.createItemBytes(m.id);
      if (bytes == null) throw Exception('This file is no longer on Hoola.');
      final ext = _ext(m.mime);
      final dir = await getTemporaryDirectory();
      final safe = m.title.replaceAll(RegExp(r'[^A-Za-z0-9 _-]'), '').trim();
      final f = File('${dir.path}/${safe.isEmpty ? 'hoola' : safe}$ext');
      await f.writeAsBytes(bytes, flush: true);
      await Native.shareFile(f.path, mime: m.mime.isEmpty ? 'application/octet-stream' : m.mime, title: m.title);
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(_plainError(e))));
    }
  }

  String _ext(String mime) => switch (mime) {
        'image/png' => '.png',
        'image/jpeg' => '.jpg',
        'image/webp' => '.webp',
        'audio/mpeg' => '.mp3',
        'audio/wav' || 'audio/x-wav' => '.wav',
        'video/mp4' => '.mp4',
        'text/markdown' => '.md',
        'text/plain' => '.txt',
        'application/pdf' => '.pdf',
        _ => '',
      };

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final all = _items;
    final q = _q.trim().toLowerCase();
    final shown = all == null
        ? const <MadeItem>[]
        : [
            for (final m in all)
              if ((_kind == 'all' || m.kind == _kind) && (q.isEmpty || '${m.title} ${m.sub}'.toLowerCase().contains(q))) m
          ];
    final present = {for (final m in all ?? const <MadeItem>[]) m.kind};
    final chips = [for (final k in _kinds) if (k.$1 == 'all' || present.contains(k.$1)) k];
    return RefreshIndicator(
      color: c.accent,
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: HoolaSpace.s24),
        children: [
          HoolaTabHeader(title: 'Made', sub: all == null || all.isEmpty ? '' : '${all.length} things Hoola made for you'),
          HoolaSearch(controller: _search, hint: 'Search what Hoola made', onChanged: (v) => setState(() => _q = v)),
          if (chips.length > 2) HoolaChips(items: chips, picked: _kind, onPick: (k) => setState(() => _kind = k)),
          if (all == null)
            const _Loading()
          else if (_err.isNotEmpty && all.isEmpty)
            HoolaEmpty(icon: Icons.cloud_off_rounded, title: 'What Hoola made could not be opened', sub: _err, onRetry: _load)
          else if (all.isEmpty)
            const HoolaEmpty(
                icon: Icons.auto_awesome_outlined,
                title: 'Nothing made yet',
                sub: 'Pages, pictures, songs and documents Hoola makes for you are kept here.')
          else if (shown.isEmpty)
            const HoolaEmpty(icon: Icons.search_off_rounded, title: 'Nothing matches', sub: 'Try another word or type.')
          else ...[
            const SizedBox(height: HoolaSpace.s8),
            HoolaGroup(children: [
              for (final m in shown)
                HoolaRow(
                  title: m.title,
                  sub: [
                    _kindWord(m.kind),
                    if (m.status == 'building') 'being made',
                    if (m.status == 'failed') 'not made',
                    if (m.at != null) hoolaWhen(m.at),
                  ].join(' · '),
                  tile: _thumb(c, m),
                  semantics: '${_kindWord(m.kind)}: ${m.title}',
                  trailing: m.status == 'building'
                      ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.accent))
                      : Icon(m.kind == 'page' || m.kind == 'picture' ? Icons.chevron_right_rounded : Icons.ios_share_rounded,
                          color: c.ink3, size: 20),
                  onTap: m.status == 'building' ? null : () => _open(m),
                ),
            ]),
          ],
        ],
      ),
    );
  }
}

/// A picture Hoola made, large, with Share.
class _PictureView extends StatelessWidget {
  const _PictureView({required this.app, required this.item});
  final Santosh app;
  final MadeItem item;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final api = app.api;
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(
        backgroundColor: c.bg,
        foregroundColor: c.ink,
        elevation: 0,
        title: Text(item.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
      ),
      body: api == null
          ? const SizedBox.shrink()
          : InteractiveViewer(
              maxScale: 5,
              child: Center(
                child: Image.network(api.createItemUrl(item.id),
                    headers: api.authHeaders,
                    fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) =>
                        const HoolaEmpty(icon: Icons.broken_image_outlined, title: 'This picture could not be opened')),
              ),
            ),
    );
  }
}

// ================================================================== CONNECT
/// One app or tool she can connect.
class ConnectItem {
  ConnectItem({required this.id, required this.name, this.does = '', this.logo = '', required this.state, this.noLogin = false});
  final String id, name, does, logo, state;   // state: connected | add | builtin | soon
  final bool noLogin;
}

/// Pure: the catalogue + her app links into Connected / Add a connection / Ready to use (tested).
({List<ConnectItem> connected, List<ConnectItem> add, List<ConnectItem> builtin}) connectSections(
    Map<String, dynamic> catalog, List<Map<String, dynamic>> apps) {
  final connected = <ConnectItem>[], add = <ConnectItem>[], builtin = <ConnectItem>[];
  final seen = <String>{};
  ConnectItem item(Map<String, dynamic> p, String state) => ConnectItem(
        id: _s(p['pack_id']).isNotEmpty ? _s(p['pack_id']) : _s(p['id']),
        name: _s(p['name']),
        does: _s(p['does']),
        logo: _s(p['logo']),
        state: state,
        noLogin: p['no_login'] == true,
      );
  for (final a in apps) {
    final it = item(a, switch (_s(a['status'])) { 'ready' => 'connected', 'needs_link' => 'add', _ => 'soon' });
    if (it.id.isEmpty || it.name.isEmpty || it.state == 'soon' || !seen.add(it.id)) continue;
    (it.state == 'connected' ? connected : add).add(it);
  }
  for (final x in ((catalog['packs'] as List?) ?? const [])) {
    final p = Map<String, dynamic>.from(x as Map);
    final st = _s(p['status']);
    final state = switch (st) { 'ready' => 'connected', 'core' => 'builtin', 'needs_link' => 'add', _ => '' };
    final it = item(p, state);
    if (state.isEmpty || it.id.isEmpty || it.name.isEmpty || !seen.add(it.id)) continue;
    (state == 'connected' ? connected : state == 'add' ? add : builtin).add(it);
  }
  int byName(ConnectItem a, ConnectItem b) => a.name.toLowerCase().compareTo(b.name.toLowerCase());
  connected.sort(byName);
  add.sort(byName);
  builtin.sort(byName);
  return (connected: connected, add: add, builtin: builtin);
}

/// The Connect tab.
class HoolaConnect extends StatefulWidget {
  const HoolaConnect({super.key, required this.app, required this.onMore});
  final Santosh app;
  final VoidCallback onMore;
  @override
  State<HoolaConnect> createState() => _HoolaConnectState();
}

class _HoolaConnectState extends State<HoolaConnect> {
  Map<String, dynamic>? _cat;
  List<Map<String, dynamic>> _apps = const [];
  String _err = '';
  String _q = '';
  bool _allBuiltin = false;
  final _search = TextEditingController();
  int _linkTick = 0;
  final _busy = <String>{};

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _linkTick = app.bazarLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _search.dispose();
    super.dispose();
  }

  void _onApp() {
    if (app.bazarLinkedTick != _linkTick) {
      _linkTick = app.bazarLinkedTick;
      _load(quiet: true);
    }
  }

  Future<void> _load({bool quiet = false}) async {
    final api = app.api;
    if (api == null) {
      if (mounted) {
        setState(() {
          _cat = HoolaTabsDebug.catalog ?? const {};
          _apps = HoolaTabsDebug.apps ?? const [];
        });
      }
      return;
    }
    try {
      final r = await Future.wait([api.bazarCatalog(), api.bazarApps().catchError((_) => <Map<String, dynamic>>[])]);
      if (!mounted) return;
      setState(() {
        _cat = r[0] as Map<String, dynamic>;
        _apps = r[1] as List<Map<String, dynamic>>;
        _err = '';
      });
    } catch (e) {
      if (!mounted || quiet) return;
      setState(() {
        _cat ??= const {};
        _err = _plainError(e);
      });
    }
  }

  Future<void> _link(ConnectItem it) async {
    if (_busy.contains(it.id)) return;
    HapticFeedback.selectionClick();
    setState(() => _busy.add(it.id));
    final messenger = ScaffoldMessenger.of(context);
    final err = await app.linkApp(it.id);
    if (!mounted) return;
    setState(() => _busy.remove(it.id));
    if (err != null) messenger.showSnackBar(SnackBar(content: Text(err)));
  }

  Future<void> _remove(ConnectItem it) async {
    if (it.noLogin) return;   // a no-login app is on for everyone; there is nothing of hers to remove
    final c = HoolaColors.of(context);
    final ok = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Remove ${it.name}?', style: HoolaType.heading(c)),
            const SizedBox(height: 8),
            Text('Hoola will not be able to use this account until you connect it again.', style: HoolaType.body(c).copyWith(color: c.ink2)),
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
    if (ok != true || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await app.api!.bazarUnlink(it.id);
      unawaited(_load(quiet: true));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(_plainError(e))));
    }
  }

  Widget _logo(HoolaColors c, ConnectItem it) {
    final api = app.api;
    final letter = it.name.isEmpty ? '?' : it.name.characters.first.toUpperCase();
    final fallback = Container(
      width: 40,
      height: 40,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(HoolaRadius.tile)),
      child: Text(letter, style: HoolaType.title(c).copyWith(color: c.ink2)),
    );
    if (it.logo.isEmpty || api == null) return fallback;
    final url = it.logo.startsWith('http') ? it.logo : api.absolute(it.logo);
    return ClipRRect(
      borderRadius: BorderRadius.circular(HoolaRadius.tile),
      child: Container(
        width: 40,
        height: 40,
        color: c.surface,
        padding: const EdgeInsets.all(4),
        child: Image.network(url, fit: BoxFit.contain, cacheWidth: 120, errorBuilder: (_, __, ___) => fallback),
      ),
    );
  }

  Widget _row(HoolaColors c, ConnectItem it) {
    final busy = _busy.contains(it.id);
    final Widget trailing = switch (it.state) {
      'connected' => Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.check_circle_rounded, color: c.ok, size: 18),
          const SizedBox(width: 4),
          Text('Connected', style: HoolaType.label(c).copyWith(color: c.ok)),
        ]),
      'add' => busy
          ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.accent))
          : OutlinedButton(
              onPressed: () => _link(it),
              style: OutlinedButton.styleFrom(
                foregroundColor: c.ink,
                side: BorderSide(color: c.lineStrong),
                shape: const StadiumBorder(),
                minimumSize: const Size(64, 36),
                padding: const EdgeInsets.symmetric(horizontal: 14),
              ),
              child: const Text('Connect'),
            ),
      _ => Text('Ready', style: HoolaType.label(c)),
    };
    return HoolaRow(
      title: it.name,
      sub: it.does,
      tile: _logo(c, it),
      trailing: trailing,
      semantics: '${it.name}, ${it.state == 'connected' ? 'connected' : it.state == 'add' ? 'not connected' : 'ready'}',
      onTap: it.state == 'add' ? () => _link(it) : null,
      onLongPress: it.state == 'connected' && !it.noLogin ? () => _remove(it) : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final cat = _cat;
    final parts = cat == null ? null : connectSections(cat, _apps);
    final q = _q.trim().toLowerCase();
    bool hit(ConnectItem i) => q.isEmpty || '${i.name} ${i.does}'.toLowerCase().contains(q);
    final connected = [for (final i in parts?.connected ?? const <ConnectItem>[]) if (hit(i)) i];
    final add = [for (final i in parts?.add ?? const <ConnectItem>[]) if (hit(i)) i];
    final builtinAll = [for (final i in parts?.builtin ?? const <ConnectItem>[]) if (hit(i)) i];
    final builtin = (_allBuiltin || q.isNotEmpty) ? builtinAll : builtinAll.take(6).toList();
    final nothing = connected.isEmpty && add.isEmpty && builtinAll.isEmpty;
    return RefreshIndicator(
      color: c.accent,
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: HoolaSpace.s24),
        children: [
          HoolaTabHeader(
            title: 'Connect',
            sub: parts == null ? '' : '${parts.connected.length} connected',
          ),
          HoolaSearch(controller: _search, hint: 'Search apps and tools', onChanged: (v) => setState(() => _q = v)),
          if (parts == null)
            const _Loading()
          else if (_err.isNotEmpty && nothing)
            HoolaEmpty(icon: Icons.cloud_off_rounded, title: 'Connections could not be opened', sub: _err, onRetry: _load)
          else if (nothing)
            HoolaEmpty(
                icon: Icons.search_off_rounded,
                title: q.isEmpty ? 'Nothing to connect yet' : 'No app matches',
                sub: q.isEmpty ? '' : 'The full list of plugins has more. Open it below.')
          else ...[
            if (connected.isNotEmpty) ...[
              HoolaSection('Connected', count: connected.length, color: c.ok),
              HoolaGroup(children: [for (final i in connected) _row(c, i)]),
              Padding(
                padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 6, HoolaSpace.gutter, 0),
                child: Text('Press and hold a connected app to remove it.', style: HoolaType.small(c)),
              ),
            ],
            if (add.isNotEmpty) ...[
              HoolaSection('Add a connection', count: add.length),
              HoolaGroup(children: [for (final i in add) _row(c, i)]),
            ],
            if (builtinAll.isNotEmpty) ...[
              HoolaSection('Ready to use', count: builtinAll.length),
              HoolaGroup(children: [
                for (final i in builtin) _row(c, i),
                if (builtinAll.length > builtin.length)
                  HoolaRow(
                    title: 'Show all ${builtinAll.length}',
                    icon: Icons.expand_more_rounded,
                    onTap: () => setState(() => _allBuiltin = true),
                  ),
              ]),
            ],
          ],
          const HoolaSection('More'),
          HoolaGroup(children: [
            HoolaRow(
              title: 'All plugins and settings',
              sub: 'Every plugin, spend limits, delivery address, shops',
              icon: Icons.extension_outlined,
              trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
              onTap: widget.onMore,
            ),
          ]),
        ],
      ),
    );
  }
}
