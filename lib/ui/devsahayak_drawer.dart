/// v0.879 HOOLA CODE PHONE: the Sessions drawer (design docs/design/hoola_code/PhoneDrawer.png), the Scheduled tasks
/// page (PhoneScheduled.png) with its New / Edit form, and the Environments list. All on the existing server routes:
/// GET /api/devsahayak (overview), /tasks (archived, search), /schedules (+ PATCH on / off, Run now, DELETE), /envs.
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'devsahayak_kit.dart';
import 'devsahayak_new.dart';
import 'devsahayak_screen.dart' show DevCodeSettingsPage;
import 'devsahayak_session.dart';
import 'hoola_theme.dart';

const List<String> _needsStatus = ['plan_wait', 'ready', 'checks_failed', 'refused'];

/// Opens one session from anywhere in Hoola Code (from a session page it replaces that page).
void devOpenSession(NavigatorState nav, Santosh app, String id, {bool replace = false}) {
  if (id.isEmpty) return;
  final route = MaterialPageRoute<void>(builder: (_) => DevTaskPage(app: app, id: id));
  if (replace) {
    nav.pushReplacement(route);
  } else {
    nav.push(route);
  }
}

Color devDotColor(CodeColors c, Map<String, dynamic> t) {
  if (t['running'] == true) return c.accent;
  if (hcS(t['question']).isNotEmpty || _needsStatus.contains(hcS(t['status']))) return c.amber;
  final st = hcS(t['status']);
  if (hcInt(t['pr_number']) != 0 && (st == 'pr_open' || st == 'ci_running')) return c.green;
  return c.ink5;
}

String _day(DateTime d) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(d.year, d.month, d.day);
  final diff = today.difference(day).inDays;
  if (diff <= 0) return 'Today';
  if (diff == 1) return 'Yesterday';
  return 'Earlier';
}

String hcTime(DateTime d) {
  final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
  return '$h:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'am' : 'pm'}';
}

const _weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

String _when(DateTime d) {
  final l = d.toLocal();
  final now = DateTime.now();
  final days = DateTime(l.year, l.month, l.day).difference(DateTime(now.year, now.month, now.day)).inDays;
  if (days == 0) return hcTime(l);
  if (days == -1) return 'yesterday ${hcTime(l)}';
  if (days.abs() < 7) return '${_weekdays[l.weekday - 1]} ${hcTime(l)}';
  return '${l.day} ${const ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][l.month - 1]}';
}

// ================================================================================================== the drawer
class DevCodeDrawer extends StatefulWidget {
  const DevCodeDrawer({super.key, required this.app, this.current = ''});
  final Santosh app;
  final String current;   // the open session's id ('' on the home)

  @override
  State<DevCodeDrawer> createState() => _DevCodeDrawerState();
}

class _DevCodeDrawerState extends State<DevCodeDrawer> {
  Map<String, dynamic> _o = {};
  List<Map<String, dynamic>>? _tasks;
  bool _archived = false;
  String _repo = '';
  String _q = '';
  final _search = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadOverview();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _loadOverview() async {
    try {
      final o = hcM(await widget.app.api!.call('GET', '/api/devsahayak'));
      if (!mounted) return;
      setState(() {
        _o = o;
        if (!_archived && _q.isEmpty) _tasks = hcList(o['tasks']);
      });
    } catch (e) {
      if (mounted) setState(() => _tasks ??= const []);
    }
  }

  Future<void> _loadTasks() async {
    try {
      final r = hcM(await widget.app.api!.call('GET', '/api/devsahayak/tasks',
          query: {'archived': _archived ? '1' : '0', if (_q.isNotEmpty) 'q': _q, 'limit': '60'}));
      if (mounted) setState(() => _tasks = hcList(r['tasks']));
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  void _go(void Function(NavigatorState nav) then) {
    final nav = Navigator.of(context);
    nav.pop();   // the drawer
    then(nav);
  }

  Widget _navRow(CodeColors c, IconData icon, String label, VoidCallback onTap, {bool filled = false, String trail = ''}) => Semantics(
        button: true,
        label: trail.isEmpty ? label : '$label, $trail',
        excludeSemantics: true,
        child: Material(
          color: filled ? c.surface : Colors.transparent,
          borderRadius: HoolaRadius.r(HoolaRadius.tile),
          child: InkWell(
            borderRadius: HoolaRadius.r(HoolaRadius.tile),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Row(children: [
                  Icon(icon, size: filled ? 20 : 18, color: c.ink2),
                  const SizedBox(width: 12),
                  Expanded(child: Text(label, style: HcType.ui(c, 16, weight: filled ? FontWeight.w500 : FontWeight.w400))),
                  if (trail.isNotEmpty) Text(trail, style: HcType.ui(c, 13, color: c.ink4)),
                ]),
              ),
            ),
          ),
        ),
      );

  Future<void> _pickRepo(List<String> repos) async {
    final c = CodeColors.of(context);
    final v = await hcSheet<String>(
      context,
      (sheet) => SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const HcSheetHead(title: 'Show sessions in'),
            const SizedBox(height: 6),
            for (final r in ['', ...repos])
              InkWell(
                onTap: () => Navigator.pop(sheet, r),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 52),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Row(children: [
                      Expanded(child: Text(r.isEmpty ? 'All repos' : r, style: HcType.ui(c, 16))),
                      if (r == _repo) Icon(Icons.check_rounded, size: 22, color: c.ink),
                    ]),
                  ),
                ),
              ),
            const SizedBox(height: 12),
          ]),
        ),
      ),
    );
    if (v != null && mounted) setState(() => _repo = v);
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final tasks = [for (final t in _tasks ?? const <Map<String, dynamic>>[]) if (_repo.isEmpty || hcS(t['repo']) == _repo) t];
    final repos = <String>{for (final r in hcList(_o['repos'])) hcS(r['repo'])}.where((e) => e.isNotEmpty).toList();
    final schedules = hcList(_o['schedules']).length;
    final waiting = hcList(_o['actions']).where((a) => hcS(a['status']) == 'waiting').length;
    final reviews = hcList(_o['reviews']).where((r) => hcS(r['status']) == 'draft').length;
    final usage = hcM(_o['usage']);
    final spent = usage['spent_inr'] is num ? (usage['spent_inr'] as num) : 0;
    final limit = usage['limit_inr'] is num ? (usage['limit_inr'] as num) : 0;
    final name = ((widget.app.account?['name'] as String?) ?? '').trim();
    String rs(num v) => 'Rs ${v.round().toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},')}';

    final groups = <String, List<Map<String, dynamic>>>{};
    for (final t in tasks) {
      final d = DateTime.tryParse(hcS(t['updated']).isNotEmpty ? hcS(t['updated']) : hcS(t['at']));
      groups.putIfAbsent(d == null ? 'Earlier' : _day(d.toLocal()), () => []).add(t);
    }

    return Drawer(
      backgroundColor: c.drawer,
      surfaceTintColor: Colors.transparent,
      width: MediaQuery.sizeOf(context).width * .83 > 360 ? 360.0 : MediaQuery.sizeOf(context).width * .83,
      shape: Border(right: BorderSide(color: c.line)),
      child: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          SizedBox(
            height: 60,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                const HcMark(size: 26),
                const SizedBox(width: 10),
                Expanded(child: Text('Hoola Code', style: HcType.ui(c, 17, weight: FontWeight.w600))),
              ]),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Column(children: [
              _navRow(c, Icons.add_rounded, 'New session', () {
                _go((nav) {
                  if (widget.current.isNotEmpty) DevCodeNav.toHomeNav(nav);
                });
              }, filled: true),
              const SizedBox(height: 2),
              _navRow(c, Icons.schedule_rounded, 'Scheduled tasks',
                  () => _go((nav) => nav.push(MaterialPageRoute<void>(builder: (_) => DevScheduledPage(app: widget.app)))),
                  trail: schedules > 0 ? '$schedules' : ''),
              const SizedBox(height: 2),
              _navRow(c, Icons.cloud_outlined, 'Environments',
                  () => _go((nav) => nav.push(MaterialPageRoute<void>(builder: (_) => DevEnvironmentsPage(app: widget.app))))),
              if (waiting + reviews > 0) ...[
                const SizedBox(height: 2),
                _navRow(c, Icons.merge_rounded, 'PR reviews and merges',
                    () => _go((nav) => nav.push(MaterialPageRoute<void>(builder: (_) => DevCodeSettingsPage(app: widget.app)))),
                    trail: '${waiting + reviews} waiting'),
              ],
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
            child: TextField(
              controller: _search,
              style: HcType.ui(c, 15),
              cursorColor: c.accent,
              textInputAction: TextInputAction.search,
              onSubmitted: (v) {
                _q = v.trim();
                _loadTasks();
              },
              onChanged: (v) {
                if (v.trim().isEmpty && _q.isNotEmpty) {
                  _q = '';
                  _archived ? _loadTasks() : _loadOverview();
                }
              },
              decoration: InputDecoration(
                hintText: 'Search sessions',
                hintStyle: HcType.ui(c, 15, color: c.ink4),
                prefixIcon: Icon(Icons.search_rounded, size: 18, color: c.ink4),
                filled: true,
                fillColor: c.field,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
                border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line)),
                enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line)),
                focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 2, 12, 6),
            child: Wrap(spacing: 4, children: [
              HcFilterChip(
                label: 'Active',
                on: !_archived,
                onTap: () {
                  setState(() => _archived = false);
                  _q.isEmpty ? _loadOverview() : _loadTasks();
                },
              ),
              HcFilterChip(
                label: 'Archived',
                on: _archived,
                onTap: () {
                  setState(() => _archived = true);
                  _loadTasks();
                },
              ),
              HcFilterChip(
                label: _repo.isEmpty ? 'All repos' : hcShortRepo(_repo),
                on: false,
                trailing: Icons.expand_more_rounded,
                onTap: () => _pickRepo(repos),
              ),
            ]),
          ),
          Expanded(
            child: _tasks == null
                ? Center(child: CircularProgressIndicator(strokeWidth: 2, color: c.accent))
                : tasks.isEmpty
                    ? Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(_archived ? 'No archived sessions.' : (_q.isEmpty ? 'No sessions yet.' : 'No session matches.'),
                            textAlign: TextAlign.center, style: HcType.ui(c, 14, color: c.ink4)),
                      )
                    : RefreshIndicator(
                        color: c.accent,
                        onRefresh: () => _archived || _q.isNotEmpty ? _loadTasks() : _loadOverview(),
                        child: ListView(padding: const EdgeInsets.symmetric(horizontal: 8), children: [
                          for (final g in const ['Today', 'Yesterday', 'Earlier'])
                            if (groups[g] != null) ...[
                              Padding(
                                padding: const EdgeInsets.fromLTRB(10, 12, 10, 4),
                                child: Text(g, style: HcType.ui(c, 13, color: c.ink4)),
                              ),
                              for (final t in groups[g]!) _row(c, t),
                            ],
                        ]),
                      ),
          ),
          Container(
            height: 64,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
            child: Row(children: [
              Container(
                width: 36,
                height: 36,
                alignment: Alignment.center,
                decoration: BoxDecoration(color: CodeColors.darkSet.amber, shape: BoxShape.circle),
                child: Text(name.isEmpty ? 'H' : name[0].toUpperCase(),
                    style: HcType.ui(c, 15, weight: FontWeight.w600, color: CodeColors.darkSet.onCream)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name.isEmpty ? 'You' : name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 15)),
                  if (_o.isNotEmpty)
                    Text(limit > 0 ? '${rs(spent)} of ${rs(limit)} this month' : '${rs(spent)} this month',
                        maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink4)),
                ]),
              ),
              HcIconButton(
                icon: Icons.settings_outlined,
                label: 'Hoola Code settings',
                size: 20,
                color: c.ink3,
                onTap: () => _go((nav) => nav.push(MaterialPageRoute<void>(builder: (_) => DevCodeSettingsPage(app: widget.app)))),
              ),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _row(CodeColors c, Map<String, dynamic> t) {
    final id = hcS(t['id']);
    final on = id == widget.current;
    final sub = [hcShortRepo(hcS(t['repo'])), devStatusWords(t)].where((e) => e.isNotEmpty).join(' · ');
    return Semantics(
      button: true,
      selected: on,
      label: '${hcS(t['title'])}, $sub',
      excludeSemantics: true,
      child: Material(
        color: on ? c.surface : Colors.transparent,
        borderRadius: HoolaRadius.r(HoolaRadius.tile),
        child: InkWell(
          borderRadius: HoolaRadius.r(HoolaRadius.tile),
          onTap: () {
            if (on) {
              Navigator.of(context).pop();
              return;
            }
            _go((nav) => devOpenSession(nav, widget.app, id, replace: widget.current.isNotEmpty));
          },
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 56),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              child: Row(children: [
                HcDot(devDotColor(c, t)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(hcS(t['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 15)),
                    const SizedBox(height: 2),
                    Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink4)),
                  ]),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

// ================================================================================================== Scheduled tasks
class DevScheduledPage extends StatelessWidget {
  const DevScheduledPage({super.key, required this.app});
  final Santosh app;

  @override
  Widget build(BuildContext context) => HoolaTheme(appearance: app.appearance, child: _ScheduledBody(app: app));
}

class _ScheduledBody extends StatefulWidget {
  const _ScheduledBody({required this.app});
  final Santosh app;

  @override
  State<_ScheduledBody> createState() => _ScheduledBodyState();
}

class _ScheduledBodyState extends State<_ScheduledBody> {
  List<Map<String, dynamic>>? _list;
  bool _paused = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = hcM(await widget.app.api!.call('GET', '/api/devsahayak/schedules'));
      if (mounted) setState(() => _list = hcList(r['schedules']));
    } catch (e) {
      if (mounted) {
        setState(() => _list ??= const []);
        hcSay(context, '$e');
      }
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    Map<String, dynamic>? out;
    try {
      out = hcM(await widget.app.api!.call(method, path, body: body, timeout: const Duration(minutes: 2)));
      if (mounted) hcSay(context, hcS(out['say']));
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
    return out;
  }

  Future<void> _edit([Map<String, dynamic>? sc]) async {
    final saved = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => DevScheduleFormPage(app: widget.app, schedule: sc)));
    if (saved == true) await _load();
  }

  Future<void> _details(Map<String, dynamic> sc) async {
    final c = CodeColors.of(context);
    final runs = hcList(sc['runs']);
    final pick = await hcSheet<String>(
      context,
      (sheet) => SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            HcSheetHead(title: hcS(sc['title']), sub: hcS(sc['when'])),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
              child: Text(hcS(sc['text']), maxLines: 8, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14, color: c.ink3, height: 1.45)),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Row(children: [
                Expanded(child: HcCreamButton(label: 'Run now', size: 15, height: 46, onTap: () => Navigator.pop(sheet, 'run'))),
                const SizedBox(width: 8),
                Expanded(child: HcOutlineButton(label: 'Edit', onTap: () => Navigator.pop(sheet, 'edit'))),
                const SizedBox(width: 8),
                Expanded(child: HcOutlineButton(label: 'Delete', onTap: () => Navigator.pop(sheet, 'delete'))),
              ]),
            ),
            if (runs.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 4),
                child: Text('Recent runs', style: HcType.ui(c, 13, color: c.ink4)),
              ),
            for (final r in runs.take(6))
              InkWell(
                onTap: () => Navigator.pop(sheet, 'open:${hcS(r['id'])}'),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 48),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
                    child: Row(children: [
                      HcDot(devDotColor(c, r)),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text('${hcS(r['title'])} · ${devStatusWords(r)}',
                            maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14, color: c.ink2)),
                      ),
                      if (DateTime.tryParse(hcS(r['at'])) != null) Text(_when(DateTime.parse(hcS(r['at']))), style: HcType.ui(c, 12, color: c.ink4)),
                    ]),
                  ),
                ),
              ),
            const SizedBox(height: 16),
          ]),
        ),
      ),
    );
    if (pick == null || !mounted) return;
    if (pick == 'run') {
      final r = await _run('POST', '/api/devsahayak/schedules/${hcS(sc['id'])}/run');
      if (r != null && hcS(r['id']).isNotEmpty && mounted) devOpenSession(Navigator.of(context), widget.app, hcS(r['id']));
    } else if (pick == 'edit') {
      await _edit(sc);
    } else if (pick == 'delete') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text('Delete ${hcS(sc['title'])}?'),
          content: const Text('It stops starting by itself. Its past sessions stay in your list.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Delete')),
          ],
        ),
      );
      if (ok == true) await _run('DELETE', '/api/devsahayak/schedules/${hcS(sc['id'])}');
    } else if (pick.startsWith('open:')) {
      devOpenSession(Navigator.of(context), widget.app, pick.substring(5));
    }
  }

  String _trigger(Map<String, dynamic> sc) {
    final ev = hcS(sc['event']);
    if (ev.isNotEmpty) {
      return switch (ev) {
        'ci_failed' => 'GitHub · CI failed',
        'issue_opened' => 'GitHub · new issue',
        'issue_labeled' => 'GitHub · issue label',
        'pr_opened' => 'GitHub · new PR',
        'push' => 'GitHub · push',
        _ => 'GitHub event',
      };
    }
    final days = hcS(sc['days']);
    final at = hcS(sc['at']);
    final parts = at.split(':');
    var time = at;
    if (parts.length == 2) {
      final h = int.tryParse(parts[0]) ?? 0, m = int.tryParse(parts[1]) ?? 0;
      time = hcTime(DateTime(2000, 1, 1, h, m));
    }
    if (days == 'daily') return 'Daily · $time';
    if (days == 'weekdays') return 'Weekdays · $time';
    if (days.startsWith('weekly:')) {
      final i = int.tryParse(days.substring(7)) ?? 0;
      return '${const ['Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays', 'Sundays'][i < 0 ? 0 : (i > 6 ? 6 : i)]} · $time';
    }
    return 'On demand';
  }

  Widget _card(CodeColors c, Map<String, dynamic> sc) {
    final on = sc['enabled'] == true;
    final runs = hcList(sc['runs']);
    final last = runs.isEmpty ? null : runs.first;
    Color dot = c.ink5;
    String lastWords;
    if (!on) {
      lastWords = 'Paused';
    } else if (last == null) {
      lastWords = 'No run yet';
    } else {
      final st = hcS(last['status']);
      dot = (st == 'failed' || st == 'checks_failed' || st == 'refused') ? c.red : (st == 'cancelled' ? c.ink5 : c.green);
      final d = DateTime.tryParse(hcS(last['at']));
      final pr = hcInt(last['pr_number']);
      lastWords = ['Last run${d == null ? '' : ' ${_when(d)}'}', pr != 0 ? 'PR #$pr' : devStatusWords(last)].join(' · ');
    }
    if (hcS(sc['last_note']).isNotEmpty && on) {
      dot = c.red;
      lastWords = hcS(sc['last_note']);
    }
    final next = !on
        ? '—'
        : (hcS(sc['event']).isNotEmpty
            ? 'On event'
            : (DateTime.tryParse(hcS(sc['next_run'])) != null ? 'Next ${_when(DateTime.parse(hcS(sc['next_run'])))}' : 'Run now only'));
    return Material(
      color: c.card,
      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.card), side: BorderSide(color: c.line)),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: _busy ? null : () => _details(sc),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 8, 12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(hcS(sc['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 16, weight: FontWeight.w600))),
              HcSwitch(
                value: on,
                label: hcS(sc['title']),
                onChanged: _busy ? null : (v) => _run('PATCH', '/api/devsahayak/schedules/${hcS(sc['id'])}', {'enabled': v}),
              ),
            ]),
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: Wrap(spacing: 6, runSpacing: 6, children: [
                HcTag(_trigger(sc)),
                HcTag(hcShortRepo(hcS(sc['repo']))),
                HcTag(hcS(sc['mode']) == 'auto' ? 'Opens the PR' : 'Asks before the PR'),
              ]),
            ),
            const SizedBox(height: 10),
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: Row(children: [
                HcDot(dot),
                const SizedBox(width: 8),
                Expanded(child: Text(lastWords, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink3))),
                const SizedBox(width: 8),
                Text(next, style: HcType.ui(c, 13, color: c.ink4)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final all = _list ?? const <Map<String, dynamic>>[];
    final pausedN = all.where((s) => s['enabled'] != true).length;
    final shown = _paused ? all.where((s) => s['enabled'] != true).toList() : all;
    return Scaffold(
      backgroundColor: c.bg,
      drawer: DevCodeDrawer(app: widget.app, current: '-'),
      drawerScrimColor: c.scrim,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          SizedBox(
            height: 56,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Row(children: [
                Builder(builder: (ctx) => HcIconButton(icon: Icons.notes_rounded, label: 'Sessions', onTap: () => Scaffold.of(ctx).openDrawer())),
                const Spacer(),
                HcIconButton(icon: Icons.close_rounded, label: 'Close', onTap: () => Navigator.maybePop(context)),
              ]),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Scheduled tasks', style: HcType.serif(c, 28, weight: FontWeight.w500)),
              const SizedBox(height: 6),
              Text('Hoola starts a session by itself on a schedule, from your app, or when something happens on GitHub.',
                  style: HcType.ui(c, 14, color: c.ink3, height: 1.45)),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
            child: Wrap(spacing: 8, children: [
              HcFilterChip(label: 'All · ${all.length}', on: !_paused, size: 14, outlined: true, onTap: () => setState(() => _paused = false)),
              HcFilterChip(label: 'Paused · $pausedN', on: _paused, size: 14, outlined: true, onTap: () => setState(() => _paused = true)),
            ]),
          ),
          Expanded(
            child: _list == null
                ? Center(child: CircularProgressIndicator(strokeWidth: 2, color: c.accent))
                : RefreshIndicator(
                    color: c.accent,
                    onRefresh: _load,
                    child: shown.isEmpty
                        ? ListView(children: [
                            Padding(
                              padding: const EdgeInsets.all(32),
                              child: Text(_paused ? 'Nothing is paused.' : 'No scheduled tasks yet.',
                                  textAlign: TextAlign.center, style: HcType.ui(c, 14, color: c.ink4)),
                            ),
                          ])
                        : ListView.separated(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            itemCount: shown.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 10),
                            itemBuilder: (_, i) => _card(c, shown[i]),
                          ),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              HcCreamButton(label: 'New scheduled task', icon: Icons.add_rounded, onTap: _busy ? null : () => _edit()),
              const SizedBox(height: 10),
              Text('At most once a day · times in India time · each run is its own session',
                  textAlign: TextAlign.center, style: HcType.ui(c, 13, color: c.ink4)),
            ]),
          ),
        ]),
      ),
    );
  }
}

/// New / edit one scheduled task: name, what Hoola does each time, the repo, when (a clock in India time or a GitHub
/// event) and whether the run opens the PR or asks first - the fields the server takes (POST / PATCH /schedules).
class DevScheduleFormPage extends StatelessWidget {
  const DevScheduleFormPage({super.key, required this.app, this.schedule});
  final Santosh app;
  final Map<String, dynamic>? schedule;

  @override
  Widget build(BuildContext context) => HoolaTheme(appearance: app.appearance, child: _ScheduleForm(app: app, schedule: schedule));
}

class _ScheduleForm extends StatefulWidget {
  const _ScheduleForm({required this.app, this.schedule});
  final Santosh app;
  final Map<String, dynamic>? schedule;

  @override
  State<_ScheduleForm> createState() => _ScheduleFormState();
}

class _ScheduleFormState extends State<_ScheduleForm> {
  late final TextEditingController _title, _text, _filter;
  String _repo = '';
  List<String> _repos = [];
  String _how = 'daily';     // daily | weekdays | weekly | event | off
  int _weekday = 0;
  String _at = '09:00';
  String _event = 'ci_failed';
  String _mode = 'ask';
  bool _busy = false;

  bool get _isNew => widget.schedule == null;

  @override
  void initState() {
    super.initState();
    final s = widget.schedule ?? const <String, dynamic>{};
    _title = TextEditingController(text: hcS(s['title']));
    _text = TextEditingController(text: hcS(s['text']));
    final f = hcM(s['filter']);
    _filter = TextEditingController(text: hcS(f['label']).isNotEmpty ? hcS(f['label']) : hcS(f['branch']));
    _repo = hcS(s['repo']);
    if (hcS(s['mode']).isNotEmpty) _mode = hcS(s['mode']) == 'auto' ? 'auto' : 'ask';
    if (hcS(s['at']).isNotEmpty) _at = hcS(s['at']);
    final days = hcS(s['days']);
    if (hcS(s['event']).isNotEmpty) {
      _how = 'event';
      _event = hcS(s['event']);
    } else if (days.startsWith('weekly:')) {
      _how = 'weekly';
      final w = int.tryParse(days.substring(7)) ?? 0;
      _weekday = w < 0 ? 0 : (w > 6 ? 6 : w);
    } else if (days == 'daily' || days == 'weekdays' || days == 'off') {
      _how = days;
    }
    _loadRepos();
  }

  @override
  void dispose() {
    _title.dispose();
    _text.dispose();
    _filter.dispose();
    super.dispose();
  }

  Future<void> _loadRepos() async {
    try {
      final r = hcM(await widget.app.api!.call('GET', '/api/devsahayak/repos'));
      if (!mounted) return;
      setState(() {
        _repos = [for (final x in hcList(r['repos'])) if (hcS(x['repo']).isNotEmpty) hcS(x['repo'])];
        if (_repo.isEmpty && _repos.isNotEmpty) _repo = _repos.first;
      });
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  Future<void> _pickTime() async {
    final parts = _at.split(':');
    final t = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: int.tryParse(parts.first) ?? 9, minute: parts.length > 1 ? (int.tryParse(parts[1]) ?? 0) : 0),
    );
    if (t != null && mounted) {
      setState(() => _at = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}');
    }
  }

  Future<void> _save() async {
    if (_text.text.trim().isEmpty) {
      hcSay(context, 'Write what Hoola should do each time.');
      return;
    }
    if (_repo.isEmpty) {
      hcSay(context, 'Add a repository first.');
      return;
    }
    final f = _filter.text.trim();
    final body = <String, dynamic>{
      'title': _title.text.trim(),
      'text': _text.text.trim(),
      'repo': _repo,
      'mode': _mode,
      if (_how == 'event') ...{
        'event': _event,
        'filter': {
          if (f.isNotEmpty && (_event == 'issue_opened' || _event == 'issue_labeled')) 'label': f,
          if (f.isNotEmpty && (_event == 'ci_failed' || _event == 'push')) 'branch': f,
        },
      } else ...{
        'event': '',
        'days': _how == 'weekly' ? 'weekly:$_weekday' : _how,
        'at': _at,
      },
      if (_isNew) 'enabled': true,
    };
    setState(() => _busy = true);
    try {
      if (_isNew) {
        await widget.app.api!.call('POST', '/api/devsahayak/schedules', body: body);
      } else {
        await widget.app.api!.call('PATCH', '/api/devsahayak/schedules/${hcS(widget.schedule!['id'])}', body: body);
      }
      if (mounted) Navigator.pop(context, true);
      return;
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    InputDecoration box(String hint) => InputDecoration(
          hintText: hint,
          hintStyle: HcType.ui(c, 15, color: c.ink4),
          filled: true,
          fillColor: c.surface,
          isDense: true,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
          enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
          focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
        );
    Widget label(String t) => Padding(padding: const EdgeInsets.only(bottom: 8, top: 18), child: Text(t, style: HcType.ui(c, 14, color: c.ink3)));
    Widget chips(List<(String, String)> items, String on, ValueChanged<String> pick) => Wrap(spacing: 8, runSpacing: 8, children: [
          for (final (k, l) in items) HcFilterChip(label: l, on: on == k, size: 14, outlined: true, onTap: () => setState(() => pick(k))),
        ]);
    const events = [
      ('ci_failed', 'A CI run fails'),
      ('issue_opened', 'A new issue'),
      ('issue_labeled', 'An issue gets a label'),
      ('pr_opened', 'Someone opens a PR'),
      ('push', 'Something is pushed'),
    ];
    final filterWords = (_event == 'issue_opened' || _event == 'issue_labeled')
        ? 'Label${_event == 'issue_labeled' ? ' (needed)' : ' (optional)'}'
        : ((_event == 'ci_failed' || _event == 'push') ? 'Branch (empty = the default branch)' : '');

    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          Container(
            height: 56,
            padding: const EdgeInsets.symmetric(horizontal: 8),
            decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
            child: Row(children: [
              HcIconButton(icon: Icons.arrow_back_ios_new_rounded, label: 'Back', color: c.ink, size: 20, onTap: () => Navigator.maybePop(context)),
              Expanded(
                child: Text(_isNew ? 'New scheduled task' : 'Edit scheduled task',
                    textAlign: TextAlign.center, style: HcType.ui(c, 17, weight: FontWeight.w600)),
              ),
              const SizedBox(width: 48),
            ]),
          ),
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 24), children: [
              label('Name'),
              TextField(controller: _title, maxLength: 120, style: HcType.ui(c, 16), cursorColor: c.accent, decoration: box('Nightly dependency check').copyWith(counterText: '')),
              label('What Hoola does each time'),
              TextField(
                controller: _text,
                minLines: 3,
                maxLines: 8,
                maxLength: 6000,
                style: HcType.ui(c, 15, height: 1.45),
                cursorColor: c.accent,
                decoration: box('Update outdated dependencies and open a PR if the tests pass').copyWith(counterText: ''),
              ),
              label('Repository'),
              if (_repos.isEmpty)
                Text('Add a repository from New session first.', style: HcType.ui(c, 14, color: c.ink4))
              else
                chips([for (final r in _repos) (r, hcShortRepo(r))], _repo, (v) => _repo = v),
              label('When'),
              chips(const [('daily', 'Every day'), ('weekdays', 'Weekdays'), ('weekly', 'Once a week'), ('event', 'On a GitHub event'), ('off', 'Only Run now')],
                  _how, (v) => _how = v),
              if (_how == 'weekly') ...[
                const SizedBox(height: 10),
                chips([for (var i = 0; i < 7; i++) ('$i', _weekdays[i])], '$_weekday', (v) => _weekday = int.parse(v)),
              ],
              if (_how == 'daily' || _how == 'weekdays' || _how == 'weekly') ...[
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerLeft,
                  child: HcOutlineButton(
                    label: 'At ${hcTime(DateTime(2000, 1, 1, int.tryParse(_at.split(':').first) ?? 9, int.tryParse(_at.split(':').last) ?? 0))} · India time',
                    icon: Icons.schedule_rounded,
                    onTap: _pickTime,
                  ),
                ),
              ],
              if (_how == 'event') ...[
                const SizedBox(height: 10),
                chips(events, _event, (v) => _event = v),
                if (filterWords.isNotEmpty) ...[
                  label(filterWords),
                  TextField(controller: _filter, style: HcType.mono(c, 14), cursorColor: c.accent, decoration: box(_event.startsWith('issue') ? 'hoola' : 'main')),
                ],
                const SizedBox(height: 8),
                Text('Events reach Hoola once you switch them on for the repo in Hoola Code settings on the web.',
                    style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
              ],
              label('Each run'),
              chips(const [('ask', 'Asks before the PR'), ('auto', 'Opens the PR')], _mode, (v) => _mode = v),
              const SizedBox(height: 10),
              Text('Merging is always your tap.', style: HcType.ui(c, 13, color: c.ink4)),
            ]),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
            decoration: BoxDecoration(color: c.bg, border: Border(top: BorderSide(color: c.line))),
            child: SizedBox(
              width: double.infinity,
              child: HcCreamButton(label: _isNew ? 'Create scheduled task' : 'Save changes', busy: _busy, onTap: _busy ? null : _save),
            ),
          ),
        ]),
      ),
    );
  }
}

// ================================================================================================== Environments
class DevEnvironmentsPage extends StatelessWidget {
  const DevEnvironmentsPage({super.key, required this.app});
  final Santosh app;

  @override
  Widget build(BuildContext context) => HoolaTheme(appearance: app.appearance, child: _EnvList(app: app));
}

class _EnvList extends StatefulWidget {
  const _EnvList({required this.app});
  final Santosh app;

  @override
  State<_EnvList> createState() => _EnvListState();
}

class _EnvListState extends State<_EnvList> {
  Map<String, dynamic>? _r;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = hcM(await widget.app.api!.call('GET', '/api/devsahayak/envs'));
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) {
        setState(() => _r ??= const {});
        hcSay(context, '$e');
      }
    }
  }

  Future<void> _edit(Map<String, dynamic>? env) async {
    final saved = await Navigator.push<Map<String, dynamic>>(
        context, MaterialPageRoute(builder: (_) => DevEnvPage(app: widget.app, env: env, netOn: _r?['net_on'] == true)));
    if (saved != null) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    final envs = [for (final e in hcList(_r?['envs'])) if (e['archived'] != true) e];
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          SizedBox(
            height: 56,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Row(children: [
                HcIconButton(icon: Icons.arrow_back_ios_new_rounded, label: 'Back', color: c.ink, size: 20, onTap: () => Navigator.maybePop(context)),
                const Spacer(),
              ]),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Environments', style: HcType.serif(c, 28, weight: FontWeight.w500)),
              const SizedBox(height: 6),
              Text('Where Hoola runs your repo\'s commands: the network it may reach, variables and a setup script.',
                  style: HcType.ui(c, 14, color: c.ink3, height: 1.45)),
            ]),
          ),
          Expanded(
            child: _r == null
                ? Center(child: CircularProgressIndicator(strokeWidth: 2, color: c.accent))
                : ListView(padding: const EdgeInsets.symmetric(horizontal: 8), children: [
                    _row(c, 'Auto', 'Follows your repositories', null),
                    for (final e in envs) _row(c, hcS(e['name']), devEnvSub(e), e),
                  ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
            child: HcCreamButton(label: 'Create environment', icon: Icons.add_rounded, onTap: () => _edit(null)),
          ),
        ]),
      ),
    );
  }

  Widget _row(CodeColors c, String name, String sub, Map<String, dynamic>? env) => InkWell(
        onTap: env == null ? null : () => _edit(env),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 64),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(children: [
              Icon(Icons.cloud_outlined, size: 20, color: c.ink2),
              const SizedBox(width: 14),
              Expanded(
                child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name, style: HcType.ui(c, 17)),
                  const SizedBox(height: 2),
                  Text(sub, style: HcType.ui(c, 14, color: c.ink3)),
                ]),
              ),
              if (env != null) HcIconButton(icon: Icons.settings_outlined, label: 'Edit $name', size: 20, onTap: () => _edit(env)),
            ]),
          ),
        ),
      );
}
