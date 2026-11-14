// v0.898 AI EMPLOYEES TAB (owner: "BOTTOM NAV ... REMOVE WORK SECTION INSTEAD PUT AI EMPLOYEE"): the console's AI
// Employees hub as a tab in the new design, on the same list (GET /api/employees: key, name, pitch, group, status,
// live, does / needs / never). Working for you first (a tap opens the desk), then every department with search and a
// department filter; a tap on anyone opens their card: what they do, what they need, what they will never do, and
// Hire / Open desk / Pause / Resume / Let go (let go asks first). A desk the phone has opens in the app
// (employeeDeskNative), any other opens the console's own desk already signed in (hoolaOpenConsole).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../employees_screen.dart' show employeeDeskNative;
import '../hoola_theme.dart';
import 'hoola_console_page.dart';
import 'hoola_settings.dart' show HoolaTeam, hoolaOpenNew, hoolaOpenOld;
import 'hoola_tabs.dart';

String _s(Object? v) => v == null ? '' : '$v';

/// The console view that holds an employee's desk when the phone has none (employees.js DESKS).
String employeeConsolePath(String key) {
  const views = {
    'film': 'filmdesk', 'leads': 'leadsdesk', 'accounts': 'accountsdesk', 'seekh': 'seekh',
    'paisa_sahayak': 'deptdesk', 'vitt_sahayak': 'deptdesk', 'risk_desk': 'deptdesk', 'dukaan_desk': 'deptdesk',
    'retail_growth': 'deptdesk', 'retail_trust': 'deptdesk', 'bima_desk': 'deptdesk', 'bima_assist': 'deptdesk',
    'bima_risk': 'deptdesk',
  };
  if (key == 'kaan') return '/console/flow';
  final v = key.startsWith('const_') ? 'deptdesk' : views[key] ?? 'hire';
  return v == 'hire' ? '/console/?v=hire' : '/console/?v=$v&a=${Uri.encodeQueryComponent(key)}';
}

class HoolaEmployees extends StatefulWidget {
  const HoolaEmployees({super.key, required this.app});
  final Santosh app;
  /// Screenshot tests hand the list in (no server there). Never set in the app.
  static List<Map<String, dynamic>>? debugList;
  @override
  State<HoolaEmployees> createState() => _HoolaEmployeesState();
}

class _HoolaEmployeesState extends State<HoolaEmployees> {
  final _search = TextEditingController();
  List<Map<String, dynamic>> _all = [];
  bool _loaded = false, _busy = false;
  String? _err;
  String _q = '', _dept = '';

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final d = HoolaEmployees.debugList;
    if (d != null) {
      setState(() {
        _all = d;
        _loaded = true;
      });
      return;
    }
    try {
      final r = await app.api!.employees();
      if (!mounted) return;
      setState(() {
        _all = [for (final e in (r['employees'] as List? ?? const [])) Map<String, dynamic>.from(e as Map)];
        _loaded = true;
        _err = null;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _loaded = true;
          _err = '$e';
        });
      }
    }
  }

  static String _group(Map<String, dynamic> e) => _s(e['group']).isEmpty ? 'Business' : _s(e['group']);
  static bool _hired(Map<String, dynamic> e) => e['status'] == 'hired' || e['status'] == 'paused';

  bool _hit(Map<String, dynamic> e) {
    final words = _q.toLowerCase().split(RegExp(r'\s+')).where((w) => w.isNotEmpty);
    final hay = '${e['name']} ${e['pitch']} ${_group(e)}'.toLowerCase();
    return words.every(hay.contains);
  }

  Future<void> _openDesk(Map<String, dynamic> e) async {
    final key = _s(e['key']);
    final native = employeeDeskNative(app, key);
    if (native != null) {
      await hoolaOpenOld(context, native);
    } else {
      await hoolaOpenConsole(context, app, employeeConsolePath(key), '${_s(e['name'])} desk');
    }
    if (mounted) await _load();
  }

  Future<void> _act(Map<String, dynamic> e, String action) async {
    final c = HoolaColors.of(context);
    if (action == 'leave') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('Let ${_s(e['name'])} go?'),
          content: const Text('Its jobs stop at once. Its history stays, read only.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text('Let go', style: TextStyle(color: c.bad))),
          ],
        ),
      );
      if (ok != true) return;
    }
    setState(() => _busy = true);
    try {
      await app.api!.employeeAct(_s(e['key']), action);
      HapticFeedback.lightImpact();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(switch (action) {
          'hire' => '${_s(e['name'])} is hired. Set it up on its desk.',
          'pause' => 'Paused. No jobs run until you resume.',
          'resume' => 'Back at work.',
          _ => 'Let go. Its jobs have stopped.',
        })));
      }
      await _load();
    } catch (err) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$err')));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _card(Map<String, dynamic> e) async {
    final c = HoolaColors.of(context);
    final hired = _hired(e), live = e['live'] == true, paused = e['status'] == 'paused';
    Widget list(String title, Object? xs) {
      final items = [for (final x in (xs as List? ?? const [])) '$x'];
      if (items.isEmpty) return const SizedBox.shrink();
      return Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: HoolaType.label(c).copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          for (final x in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Padding(padding: const EdgeInsets.only(top: 8, right: 10), child: Container(width: 5, height: 5, decoration: BoxDecoration(color: c.accent, shape: BoxShape.circle))),
                Expanded(child: Text(x, style: HoolaType.body(c))),
              ]),
            ),
        ]),
      );
    }

    final picked = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * .85),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 20),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(e['name']), style: HoolaType.heading(c))),
                _StatePill(e: e),
              ]),
              const SizedBox(height: 4),
              Text(_group(e), style: HoolaType.small(c)),
              const SizedBox(height: 12),
              Text(_s(e['pitch']), style: HoolaType.bodyLarge(c)),
              if (live) ...[list('What it does', e['does']), list('What it needs from you', e['needs']), list('What it will never do', e['never'])],
              const SizedBox(height: 20),
              if (!live)
                Text('Not ready to hire yet.', style: HoolaType.small(c))
              else if (!hired)
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: FilledButton.icon(
                    onPressed: () => Navigator.pop(ctx, 'hire'),
                    style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder()),
                    icon: const Icon(Icons.person_add_alt_1_rounded),
                    label: Text('Hire ${_s(e['name'])}', style: HoolaType.button(c, color: c.onPill)),
                  ),
                )
              else ...[
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: FilledButton.icon(
                    onPressed: () => Navigator.pop(ctx, 'desk'),
                    style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder()),
                    icon: const Icon(Icons.dashboard_outlined),
                    label: Text('Open desk', style: HoolaType.button(c, color: c.onPill)),
                  ),
                ),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(ctx, paused ? 'resume' : 'pause'),
                      style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), shape: const StadiumBorder()),
                      child: Text(paused ? 'Resume' : 'Pause'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextButton(
                      onPressed: () => Navigator.pop(ctx, 'leave'),
                      style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                      child: Text('Let go', style: TextStyle(color: c.bad)),
                    ),
                  ),
                ]),
              ],
            ]),
          ),
        ),
      ),
    );
    if (picked == null || !mounted) return;
    if (picked == 'desk') {
      await _openDesk(e);
    } else {
      await _act(e, picked);
      if (picked == 'hire' && mounted) {
        final now = _all.firstWhere((x) => x['key'] == e['key'], orElse: () => e);
        if (_hired(now)) await _openDesk(now);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final working = _all.where(_hired).toList();
    final groups = <String>[for (final e in _all) _group(e)].toSet().toList();
    final plain = _q.isEmpty && _dept.isEmpty;   // the plain view lists who works for her once, at the top
    final shown = _all.where((e) => (_dept.isEmpty || _group(e) == _dept) && _hit(e) && !(plain && _hired(e))).toList();
    final ready = _all.where((e) => e['live'] == true && !_hired(e)).length;
    Widget row(Map<String, dynamic> e) => HoolaRow(
          title: _s(e['name']),
          sub: _s(e['pitch']),
          icon: _hired(e) ? Icons.badge_rounded : Icons.badge_outlined,
          tint: _hired(e) ? c.accent : null,
          trailing: _StatePill(e: e),
          onTap: _busy ? null : () => _card(e),
        );
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        HoolaTabHeader(
          title: 'AI Employees',
          sub: _loaded && _err == null ? '${working.length} working for you · $ready ready to hire' : '',
        ),
        if (!_loaded)
          const Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))
        else if (_err != null && _all.isEmpty)
          HoolaEmpty(icon: Icons.cloud_off_rounded, title: 'Your AI employees did not load', sub: _err!, onRetry: _load)
        else ...[
          HoolaSearch(controller: _search, hint: 'Search AI employees', onChanged: (v) => setState(() => _q = v)),
          if (groups.length > 1)
            SizedBox(
              height: 48,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter), children: [
                for (final g in ['', ...groups])
                  Padding(
                    padding: const EdgeInsets.only(right: 8, top: 6),
                    child: ChoiceChip(
                      label: Text(g.isEmpty ? 'All' : g),
                      selected: _dept == g,
                      onSelected: (_) => setState(() => _dept = g),
                    ),
                  ),
              ]),
            ),
          if (working.isNotEmpty && plain) ...[
            HoolaSection('Working for you', count: working.length, color: c.ok),
            HoolaGroup(children: [for (final e in working) row(e)]),
          ],
          if (shown.isEmpty && !(plain && working.isNotEmpty))
            const HoolaEmpty(icon: Icons.search_off_rounded, title: 'Nobody matches', sub: 'Try another word or department.')
          else
            for (final g in groups)
              if (shown.any((e) => _group(e) == g)) ...[
                HoolaSection(g, count: shown.where((e) => _group(e) == g).length),
                HoolaGroup(children: [for (final e in shown.where((e) => _group(e) == g)) row(e)]),
              ],
          HoolaSection('More'),
          HoolaGroup(children: [
            HoolaRow(
              title: 'Every desk and tool',
              sub: 'The full list of what ${app.aName} can do for you',
              icon: Icons.apps_rounded,
              trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
              onTap: () => hoolaOpenNew(context, app, HoolaTeam(app: app)),
            ),
          ]),
        ],
      ]),
    );
  }
}

/// Working (green) / Paused / Hire / Soon.
class _StatePill extends StatelessWidget {
  const _StatePill({required this.e});
  final Map<String, dynamic> e;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final (text, fg, bg) = switch (e['status']) {
      'hired' => ('Working', c.ok, c.okSoft),
      'paused' => ('Paused', c.warn, c.warnSoft),
      _ => e['live'] == true ? ('Hire', c.accent, c.accentSoft) : ('Soon', c.ink3, c.sunk),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
      child: Text(text, style: HoolaType.label(c).copyWith(color: fg, fontWeight: FontWeight.w600)),
    );
  }
}
