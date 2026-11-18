// v0.898 AI EMPLOYEES TAB (owner: "BOTTOM NAV ... REMOVE WORK SECTION INSTEAD PUT AI EMPLOYEE"): the console's AI
// Employees hub as a tab in the new design, on the same list (GET /api/employees: key, name, pitch, group, status,
// trust, live, does / needs / never).
//
// v0.910 AI EMPLOYEES PRO (owner: "CURRENTLY IT IS LOOK AI MADE AND STALE MAKE IT PROFESSIONAL AND PERFECT. FIRST
// CHECK HOW CONSOLE SHOWS THE DATA BASED ON EMPLOYEE CATEGORY ... PREMIUM, ADVANCE, SOFT AND STUNNING" -> design canvas
// claude.ai/artifact/VkbWNUPLT1s7UYycxjhnjJ -> "GO BUILD"): the console's three levels on the phone -
//   home: serif title, the numbers (roles / ready / departments), Your team (who works for her, Open desk), search,
//         twelve department cards, each its own drawing on a black circle, "4 of 6 ready" and a ready bar;
//   a department (HoolaDepartmentPage): its drawing, what it is for, chips, All / Ready / My team / Soon, role cards;
//   one employee (HoolaEmployeePage): initials on black with a soft ring, its pitch, how much it does on its own
//         (Learning / Partner / Trusted = seekh / saathi / bharosa, saved from here once hired), what it does, what it
//         needs, what it will never do, and Hire / Open desk / Pause / Resume / Let go (let go asks first).
// Cards rise in one by one, drawings draw in and then float, working dots pulse; reduce motion = still.
// A desk the phone has opens in the app (employeeDeskNative), any other opens the console's own desk signed in.
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../employees_screen.dart' show employeeDeskNative;
import '../hoola_theme.dart';
import 'hoola_console_page.dart';
import 'hoola_settings.dart' show HoolaTeam, hoolaOpenNew, hoolaOpenOld;
import 'hoola_tabs.dart';
import 'hoola_tool_icons.dart' show svgPath;

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

/// A department as the hub shows it: the server's group name, the name on the card, a line on what it is for
/// (the console's own words, employees.js DEPT) and its drawing (a 24-unit path).
typedef HoolaDept = ({String group, String name, String desc, String icon});

const List<HoolaDept> hoolaDepts = [
  (group: 'Business', name: 'Business',
   desc: 'Marketing, customers and back office for your shop or company. Plans and drafts first; nothing goes out without your OK.',
   icon: 'M4 8h16v11H4zM9 8V6a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M4 13h16M11 13v2h2v-2'),
  (group: 'Construction & Real Estate', name: 'Construction & Real Estate',
   desc: 'Site records, money, approvals and quality papers for builders and developers. It prepares; your engineer, CA or architect signs.',
   icon: 'M4 21V10l6-4v15M10 21V3h10v18M3 21h18M13.5 7h3M13.5 11h3M13.5 15h3'),
  (group: 'Enterprise Systems & ERP', name: 'Enterprise Systems & ERP',
   desc: 'ERP, CRM, PLM, supply chain and compliance work on your own systems. Every write is planned, dry-run and waits for your tap.',
   icon: 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3'),
  (group: 'Game Development, Simulation & VR', name: 'Games, Simulation & VR',
   desc: 'Games, worlds, physics, 3D sound and VR rooms. Each one is built, tested by Hoola itself, and playable from a link.',
   icon: 'M7 8h10a4 4 0 0 1 4 4v1a3 3 0 0 1-5.4 1.8L14.5 14h-5l-1.1.8A3 3 0 0 1 3 13v-1a4 4 0 0 1 4-4zM8 10.5v3M6.5 12h3M15.5 11h.01M17.5 13h.01'),
  (group: 'Education, Research & Lab', name: 'Education, Research & Lab',
   desc: 'A tutor, a school office, a paper setter, a research assistant, the register and a 3D science lab. Children only with guardian consent.',
   icon: 'M2 9l10-5 10 5-10 5zM6 11v5c3 2 9 2 12 0v-5M22 9v5'),
  (group: 'Finance & Banking', name: 'Finance & Banking',
   desc: 'Money safety: a loan\'s real cost, hidden charges, scam warnings, complaint letters. It explains and calculates; it never moves money or asks for a PIN or OTP.',
   icon: 'M3 9l9-5 9 5M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20.5h18'),
  (group: 'Retail & E-commerce', name: 'Retail & E-commerce',
   desc: 'A shop and online-seller copilot: sales, reorder, dead stock, margin and MRP checks, settlements. It prepares and checks; you set prices and place orders.',
   icon: 'M5 8h14l-1 12H6zM9 8V6.5a3 3 0 0 1 6 0V8'),
  (group: 'Health Insurance', name: 'Health Insurance',
   desc: 'Claims and servicing help: documents needed, a payable worksheet, why a settlement was cut, appeals and renewals. It prepares; the insurer or TPA decides.',
   icon: 'M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6zM12 9v6M9 12h6'),
  (group: 'Research, CAD, Hardware & Industrial Tech', name: 'Research, CAD & Hardware',
   desc: '3D parts, simulation and code drafts for engineering teams. Every number measured, never certified on its own.',
   icon: 'M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5'),
  (group: 'Software Architecture, Engineering & Core Systems', name: 'Software Architecture',
   desc: 'Architecture, systems and code work on your own repositories. Reads first, changes only on your tap.',
   icon: 'M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 5l-3 14'),
  (group: 'Voice, Meetings & Transcription', name: 'Voice & Meetings',
   desc: 'A meeting, a voice note or a video file becomes a clean transcript with per-word timing.',
   icon: 'M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4'),
  (group: 'Film, Media & Entertainment', name: 'Film & Media',
   desc: 'A producer\'s coworker: script facts, shot checks, schedule, budget from your rate card, festivals, deliverables. Nothing is sent or paid without your tap.',
   icon: 'M4 10h16v9H4zM4 10l1.5-4.5h14L18 10M9.5 5.5L8 10M14.5 5.5L13 10'),
];

/// A group the hub does not know yet still shows, plainly, with a plain drawing.
HoolaDept hoolaDeptOf(String group) => hoolaDepts.firstWhere((d) => d.group == group,
    orElse: () => (group: group, name: group, desc: '', icon: 'M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 1 0 0-17zM12 8v8M8 12h8'));

/// The initials on an employee's circle (the console's ini(): the words outside brackets, first two letters).
String employeeMono(String name) {
  final words = name.replaceAll(RegExp(r'\(.*?\)'), '').split(RegExp(r'[\s/-]+')).where((w) => RegExp(r'^[A-Za-z]').hasMatch(w));
  final out = words.take(2).map((w) => w[0].toUpperCase()).join();
  return out.isEmpty ? '•' : out;
}

/// How much an employee does on its own (the server's trust levels; names in English, her word beside it).
const Map<String, (String, String, String)> hoolaTrust = {
  'seekh': ('Learning', 'Seekh', 'Asks you before every change outside Hoola. Every new employee starts here.'),
  'saathi': ('Partner', 'Saathi', 'Makes small changes that can be undone, and tells you the same day.'),
  'bharosa': ('Trusted', 'Bharosa', 'Works on its own inside your limits, and sends you a weekly summary.'),
};

const Map<String, String> _short = {
  'seekh': 'asks before every change',
  'saathi': 'small changes, tells you',
  'bharosa': 'works on its own',
};

/// The list, shared by the tab and the pages it opens, so a hire on one page shows everywhere at once.
class HoolaStaff extends ChangeNotifier {
  HoolaStaff(this.app);
  final Santosh app;
  List<Map<String, dynamic>> all = [];
  bool loaded = false, busy = false;
  String? err;

  static String group(Map<String, dynamic> e) => _s(e['group']).isEmpty ? 'Business' : _s(e['group']);
  static bool hired(Map<String, dynamic> e) => e['status'] == 'hired' || e['status'] == 'paused';
  static bool live(Map<String, dynamic> e) => e['live'] == true;
  static String trust(Map<String, dynamic> e) => hoolaTrust.containsKey(e['trust']) ? '${e['trust']}' : 'seekh';

  List<Map<String, dynamic>> get team => all.where(hired).toList();
  int get ready => all.where(live).length;

  /// Departments in the hub's order, then any the hub does not know, each with its people.
  List<(HoolaDept, List<Map<String, dynamic>>)> get departments {
    final groups = <String>[for (final e in all) group(e)];
    final order = [for (final d in hoolaDepts) if (groups.contains(d.group)) d.group, ...groups.toSet().where((g) => !hoolaDepts.any((d) => d.group == g))];
    return [for (final g in order) (hoolaDeptOf(g), all.where((e) => group(e) == g).toList())];
  }

  Map<String, dynamic>? byKey(String key) {
    for (final e in all) {
      if (e['key'] == key) return e;
    }
    return null;
  }

  Future<void> load() async {
    final d = HoolaEmployees.debugList;
    if (d != null) {
      all = d;
      loaded = true;
      notifyListeners();
      return;
    }
    try {
      final r = await app.api!.employees();
      all = [for (final e in (r['employees'] as List? ?? const [])) Map<String, dynamic>.from(e as Map)];
      err = null;
    } catch (e) {
      err = '$e';
    }
    loaded = true;
    notifyListeners();
  }

  /// hire / pause / resume / leave. Null = done; else the reason it did not happen.
  Future<String?> act(String key, String action) async {
    busy = true;
    notifyListeners();
    String? out;
    try {
      await app.api!.employeeAct(key, action);
      HapticFeedback.lightImpact();
      await load();
    } catch (e) {
      out = '$e';
    }
    busy = false;
    notifyListeners();
    return out;
  }

  /// How much it does on its own, saved on the server (the same setting the console's desks save).
  Future<String?> setTrust(String key, String trust) async {
    try {
      await app.api!.employeeSettings(key, {'trust': trust});
      final e = byKey(key);
      if (e != null) e['trust'] = trust;
      HapticFeedback.selectionClick();
      notifyListeners();
      return null;
    } catch (e) {
      return '$e';
    }
  }
}

/// 0..1 of one part of an opening: starts [startMs] into it and lasts [ms].
double _at(Animation<double> enter, Duration total, int startMs, int ms) =>
    ((enter.value * total.inMilliseconds - startMs) / ms).clamp(0.0, 1.0);

/// Rises in (fade + a short lift) [delay] ms into the opening.
class _Rise extends StatelessWidget {
  const _Rise({required this.enter, required this.total, required this.delay, required this.child});
  final Animation<double> enter;
  final Duration total;
  final int delay;
  final Widget child;
  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: enter,
        child: child,
        builder: (context, child) {
          final t = const Cubic(.2, .8, .2, 1).transform(_at(enter, total, delay, 560));
          return Opacity(opacity: t, child: Transform.translate(offset: Offset(0, 14 * (1 - t)), child: child));
        },
      );
}

/// A department's drawing on the black circle; it draws itself in, then floats a little.
class DeptBadge extends StatelessWidget {
  const DeptBadge({super.key, required this.icon, this.size = 48, this.clock, this.draw = 1, this.phase = 0});
  final String icon;
  final double size;
  final ValueListenable<double>? clock;
  final double draw;
  final double phase;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle),
      child: RepaintBoundary(
        child: CustomPaint(
          size: Size.square(size * .5),
          painter: DeptIconPainter(icon: icon, color: c.onPill, clock: clock, draw: draw, phase: phase),
        ),
      ),
    );
  }
}

class DeptIconPainter extends CustomPainter {
  DeptIconPainter({required this.icon, required this.color, this.clock, this.draw = 1, this.phase = 0}) : super(repaint: clock);
  final String icon;
  final Color color;
  final ValueListenable<double>? clock;
  final double draw;
  final double phase;

  static final Map<String, Path> _cache = {};

  @override
  void paint(Canvas canvas, Size size) {
    final path = _cache.putIfAbsent(icon, () => svgPath(icon));
    final secs = clock?.value;
    // a 4-second float, a little over one unit of the 24-unit grid at most
    final lift = secs == null ? 0.0 : -1.1 * (1 - math.cos(2 * math.pi * ((secs + phase) / 4 % 1))) / 2;
    canvas.save();
    canvas.scale(size.width / 24, size.height / 24);
    canvas.translate(0, lift);
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.7
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..isAntiAlias = true;
    canvas.drawPath(draw >= 1 ? path : _part(path, draw), paint);
    canvas.restore();
  }

  static Path _part(Path src, double f) {
    final metrics = src.computeMetrics().toList();
    final total = metrics.fold<double>(0, (s, m) => s + m.length);
    var left = total * f.clamp(0.0, 1.0);
    final out = Path();
    for (final m in metrics) {
      if (left <= 0) break;
      out.addPath(m.extractPath(0, math.min(left, m.length)), Offset.zero);
      left -= m.length;
    }
    return out;
  }

  @override
  bool shouldRepaint(DeptIconPainter old) => old.icon != icon || old.color != color || old.draw != draw || old.clock != clock;
}

/// An employee's initials on a circle: black when it can be hired, soft grey when it is still coming.
class EmployeeMono extends StatelessWidget {
  const EmployeeMono({super.key, required this.e, this.size = 48, this.serif = false});
  final Map<String, dynamic> e;
  final double size;
  final bool serif;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final live = HoolaStaff.live(e);
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: live ? c.pill : c.sunk, shape: BoxShape.circle),
      child: Text(
        employeeMono(_s(e['name'])),
        style: serif
            ? TextStyle(fontFamily: HoolaFont.serif, fontSize: size * .34, fontWeight: FontWeight.w500, color: live ? c.onPill : c.ink3)
            : HoolaType.title(c).copyWith(fontSize: size * .31, color: live ? c.onPill : c.ink3, height: 1),
      ),
    );
  }
}

/// A soft dot that breathes while the employee works.
class _LiveDot extends StatelessWidget {
  const _LiveDot({required this.color, this.clock});
  final Color color;
  final ValueListenable<double>? clock;
  @override
  Widget build(BuildContext context) {
    final dot = Container(width: 7, height: 7, decoration: BoxDecoration(color: color, shape: BoxShape.circle));
    final ck = clock;
    if (ck == null) return dot;
    return ValueListenableBuilder<double>(
      valueListenable: ck,
      child: dot,
      builder: (context, s, child) {
        final p = (s / 2.4) % 1;
        return Container(
          decoration: BoxDecoration(shape: BoxShape.circle, boxShadow: [
            BoxShadow(color: color.withOpacity(.45 * (1 - p)), spreadRadius: 6 * p),
          ]),
          child: child,
        );
      },
    );
  }
}

/// Working / Paused / Ready to hire / Coming soon.
class EmployeeStatus extends StatelessWidget {
  const EmployeeStatus({super.key, required this.e, this.clock});
  final Map<String, dynamic> e;
  final ValueListenable<double>? clock;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final (text, fg, bg, edge) = switch (e['status']) {
      'hired' => ('On your team · working', c.ok, c.okSoft, null),
      'paused' => ('On your team · paused', c.warn, c.warnSoft, null),
      _ => HoolaStaff.live(e) ? ('Ready to hire', c.ink, c.sunk, null) : ('Coming soon', c.ink3, Colors.transparent, c.lineStrong),
    };
    return Container(
      height: 26,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: HoolaRadius.r(HoolaRadius.pill),
        border: edge == null ? null : Border.all(color: edge),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        e['status'] == 'hired'
            ? _LiveDot(color: fg, clock: clock)
            : Container(width: 6, height: 6, decoration: BoxDecoration(color: fg, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Flexible(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.label(c).copyWith(color: fg))),
      ]),
    );
  }
}

/// The opening (cards rise in, drawings draw) and the quiet clock (floats, pulses) one screen runs on.
mixin _Motion<T extends StatefulWidget> on State<T>, TickerProviderStateMixin<T> {
  Duration get openFor => const Duration(milliseconds: 1500);
  late final AnimationController enter = AnimationController(vsync: this, duration: openFor);
  late final AnimationController _live = AnimationController(vsync: this, duration: const Duration(hours: 1));
  late final Animation<double> _secs = _live.drive(Tween(begin: 0.0, end: 3600.0));
  bool? _still;

  /// Seconds while things may move; null under reduce motion.
  ValueListenable<double>? get clock => _still == true ? null : _secs;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final still = HoolaMotion.reduced(context);
    if (still == _still) return;
    _still = still;
    if (still) {
      enter.value = 1;
      _live.stop();
    } else {
      if (enter.value == 0) enter.forward();
      _live.repeat();
    }
  }

  @override
  void dispose() {
    enter.dispose();
    _live.dispose();
    super.dispose();
  }
}

// ------------------------------------------------------------------------------------------------ the tab
class HoolaEmployees extends StatefulWidget {
  const HoolaEmployees({super.key, required this.app});
  final Santosh app;
  /// Screenshot tests hand the list in (no server there). Never set in the app.
  static List<Map<String, dynamic>>? debugList;
  @override
  State<HoolaEmployees> createState() => _HoolaEmployeesState();
}

class _HoolaEmployeesState extends State<HoolaEmployees> with TickerProviderStateMixin, _Motion {
  late final HoolaStaff staff = HoolaStaff(widget.app);
  final _search = TextEditingController();
  String _q = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => staff.load());
  }

  @override
  void dispose() {
    _search.dispose();
    staff.dispose();
    super.dispose();
  }

  bool _hit(Map<String, dynamic> e) {
    final words = _q.toLowerCase().split(RegExp(r'\s+')).where((w) => w.isNotEmpty);
    final d = hoolaDeptOf(HoolaStaff.group(e));
    final hay = '${e['name']} ${e['pitch']} ${d.group} ${d.name}'.toLowerCase();
    return words.every(hay.contains);
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(listenable: staff, builder: (context, _) => _body(context));

  Widget _body(BuildContext context) {
    final c = HoolaColors.of(context);
    final app = widget.app;
    Widget rise(int delay, Widget child) => _Rise(enter: enter, total: openFor, delay: delay, child: child);
    final head = rise(0, Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, HoolaSpace.s20, HoolaSpace.gutter + 4, 0),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Semantics(header: true, child: Text('AI Employees', style: HoolaType.hero(c).copyWith(fontSize: 34, height: 1.12))),
        const SizedBox(height: 10),
        Text('Hire a coworker for one job. It works all day, and it asks you before anything leaves Hoola.',
            style: HoolaType.body(c).copyWith(color: c.ink2)),
      ]),
    ));
    if (!staff.loaded) {
      return ListView(children: [head, const Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))]);
    }
    if (staff.err != null && staff.all.isEmpty) {
      return ListView(children: [
        head,
        HoolaEmpty(icon: Icons.cloud_off_rounded, title: 'Your AI employees did not load', sub: staff.err!, onRetry: staff.load),
      ]);
    }
    final team = staff.team;
    final depts = staff.departments;
    final found = _q.trim().isEmpty ? null : staff.all.where(_hit).toList();
    return RefreshIndicator(
      onRefresh: staff.load,
      child: ListView(padding: const EdgeInsets.only(bottom: 32), children: [
        head,
        const SizedBox(height: HoolaSpace.s24),
        rise(80, _Numbers(roles: staff.all.length, ready: staff.ready, depts: depts.length)),
        if (team.isNotEmpty) ...[
          const SizedBox(height: HoolaSpace.s24),
          rise(140, _Heading('Your team', trailing: '${team.length} ${team.length == 1 ? 'person' : 'people'}')),
          rise(160, _TeamStrip(staff: staff, team: team, clock: clock)),
        ],
        const SizedBox(height: HoolaSpace.s20),
        rise(200, HoolaSearch(
          controller: _search,
          hint: 'Search ${staff.all.length} roles, like GST or tutor',
          onChanged: (v) => setState(() => _q = v),
        )),
        if (found != null) ...[
          _Heading('Found', trailing: '${found.length}'),
          if (found.isEmpty)
            const HoolaEmpty(icon: Icons.search_off_rounded, title: 'Nobody matches', sub: 'Try another word, like the job you need done.')
          else
            for (final e in found) _RoleCard(staff: staff, e: e, clock: clock, showDept: true),
        ] else ...[
          rise(220, const _Heading('Departments', trailing: 'Tap one to meet its team')),
          _DeptGrid(staff: staff, depts: depts, enter: enter, total: openFor, clock: clock),
        ],
        const HoolaSection('More'),
        HoolaGroup(children: [
          HoolaRow(
            title: 'Every desk and tool',
            sub: 'The full list of what ${app.aName} can do for you',
            icon: Icons.apps_rounded,
            trailing: Icon(Icons.chevron_right_rounded, color: c.ink3),
            onTap: () => hoolaOpenNew(context, app, HoolaTeam(app: app)),
          ),
        ]),
      ]),
    );
  }
}

class _Heading extends StatelessWidget {
  const _Heading(this.text, {this.trailing = ''});
  final String text, trailing;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, HoolaSpace.s12, HoolaSpace.gutter + 4, HoolaSpace.s12),
      child: Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
        Expanded(child: Semantics(header: true, child: Text(text, style: HoolaType.title(c).copyWith(fontSize: 17)))),
        if (trailing.isNotEmpty) Flexible(child: Text(trailing, textAlign: TextAlign.end, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c))),
      ]),
    );
  }
}

/// The three numbers in one soft card.
class _Numbers extends StatelessWidget {
  const _Numbers({required this.roles, required this.ready, required this.depts});
  final int roles, ready, depts;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget one(int n, String label) => Expanded(
          child: Column(children: [
            Text('$n', style: TextStyle(fontFamily: HoolaFont.serif, fontSize: 26, fontWeight: FontWeight.w500, color: c.ink, height: 1.2)),
            const SizedBox(height: 2),
            Text(label, textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(fontSize: 12)),
          ]),
        );
    final rule = Container(width: 1, height: 40, color: c.line);
    return Semantics(
      container: true,
      label: '$roles roles, $ready ready to hire, $depts departments',
      excludeSemantics: true,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: HoolaRadius.r(20),
          border: Border.all(color: c.line),
          boxShadow: HoolaShadow.card(c),
        ),
        child: Row(children: [one(roles, 'roles'), rule, one(ready, 'ready to hire'), rule, one(depts, 'departments')]),
      ),
    );
  }
}

/// Who works for her: a card each (two side by side, more scroll sideways).
class _TeamStrip extends StatelessWidget {
  const _TeamStrip({required this.staff, required this.team, this.clock});
  final HoolaStaff staff;
  final List<Map<String, dynamic>> team;
  final ValueListenable<double>? clock;
  @override
  Widget build(BuildContext context) {
    final cards = [for (final e in team) _TeamCard(staff: staff, e: e, clock: clock)];
    // with big text (her phone's text size) the cards go one under the other, full width, so nothing is cut
    if (MediaQuery.textScalerOf(context).scale(10) > 13) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
        child: Column(children: [
          for (var i = 0; i < cards.length; i++) ...[if (i > 0) const SizedBox(height: 12), IntrinsicHeight(child: cards[i])],
        ]),
      );
    }
    if (team.length <= 2) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
        child: IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            for (var i = 0; i < cards.length; i++) ...[if (i > 0) const SizedBox(width: 12), Expanded(child: cards[i])],
            if (cards.length == 1) ...[const SizedBox(width: 12), const Expanded(child: SizedBox())],
          ]),
        ),
      );
    }
    return SizedBox(
      height: 214 * MediaQuery.textScalerOf(context).scale(1).clamp(1.0, 1.6),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
        itemCount: cards.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (_, i) => SizedBox(width: 172, child: cards[i]),
      ),
    );
  }
}

class _TeamCard extends StatelessWidget {
  const _TeamCard({required this.staff, required this.e, this.clock});
  final HoolaStaff staff;
  final Map<String, dynamic> e;
  final ValueListenable<double>? clock;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final paused = e['status'] == 'paused';
    final t = hoolaTrust[HoolaStaff.trust(e)]!;
    return _Card(
      label: '${_s(e['name'])}, ${paused ? 'paused' : 'working'}, ${t.$1}',
      onTap: () => openEmployee(context, staff, e),
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          EmployeeMono(e: e, size: 40),
          const Spacer(),
          if (paused)
            Flexible(child: Text('Paused', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.label(c).copyWith(color: c.warn)))
          else ...[
            _LiveDot(color: c.ok, clock: clock),
            const SizedBox(width: 6),
            Flexible(child: Text('Working', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.label(c).copyWith(color: c.ok))),
          ],
        ]),
        const SizedBox(height: 12),
        Text(_s(e['name']), maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.title(c).copyWith(fontSize: 15, height: 1.25)),
        const SizedBox(height: 3),
        Text('${t.$1} · ${_short[HoolaStaff.trust(e)]}',
            maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12, height: 1.35)),
        const Spacer(),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: TextButton(
            onPressed: () => openEmployeeDesk(context, staff, e),
            style: TextButton.styleFrom(backgroundColor: c.sunk, foregroundColor: c.ink, shape: const StadiumBorder()),
            child: Text('Open desk', style: HoolaType.label(c).copyWith(fontSize: 13, color: c.ink)),
          ),
        ),
      ]),
    );
  }
}

/// A soft white card that sinks a little when pressed.
class _Card extends StatefulWidget {
  const _Card({required this.child, required this.onTap, required this.label, this.padding = const EdgeInsets.all(16), this.radius = 22});
  final Widget child;
  final VoidCallback? onTap;
  final String label;
  final EdgeInsets padding;
  final double radius;
  @override
  State<_Card> createState() => _CardState();
}

class _CardState extends State<_Card> {
  bool _down = false;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return AnimatedScale(
      scale: _down ? .975 : 1,
      duration: const Duration(milliseconds: 160),
      curve: HoolaMotion.ease,
      child: Semantics(
        button: true,
        label: widget.label,
        child: DecoratedBox(
          decoration: BoxDecoration(borderRadius: HoolaRadius.r(widget.radius), boxShadow: HoolaShadow.card(c)),
          child: Material(
            color: c.surface,
            shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(widget.radius), side: BorderSide(color: c.line)),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onHighlightChanged: (v) => setState(() => _down = v),
              onTap: widget.onTap,
              child: Padding(padding: widget.padding, child: widget.child),
            ),
          ),
        ),
      ),
    );
  }
}

/// Twelve departments, two to a row; with big text they become one to a row so nothing is ever cut.
class _DeptGrid extends StatelessWidget {
  const _DeptGrid({required this.staff, required this.depts, required this.enter, required this.total, this.clock});
  final HoolaStaff staff;
  final List<(HoolaDept, List<Map<String, dynamic>>)> depts;
  final Animation<double> enter;
  final Duration total;
  final ValueListenable<double>? clock;
  @override
  Widget build(BuildContext context) {
    final scaler = MediaQuery.textScalerOf(context);
    final big = scaler.scale(10) > 13;
    return LayoutBuilder(builder: (context, box) {
      final cols = big ? 1 : (box.maxWidth >= 600 ? 3 : 2);
      // badge, two lines of name, the count, the bar, the gaps
      final extent = 32 + 48 + 14 + scaler.scale(15) * 1.3 * 2 + 14 + scaler.scale(12) * 1.35 + 8 + 4 + 4;
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
        child: GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: depts.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: cols,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            mainAxisExtent: extent,
          ),
          itemBuilder: (context, i) => _DeptCard(
            staff: staff, dept: depts[i].$1, people: depts[i].$2, index: i, enter: enter, total: total, clock: clock),
        ),
      );
    });
  }
}

String deptCount(List<Map<String, dynamic>> people) {
  final n = people.length, r = people.where(HoolaStaff.live).length;
  if (r == n) return n == 1 ? '1 role, ready' : '$n roles, all ready';
  return '$r of $n ready';
}

class _DeptCard extends StatelessWidget {
  const _DeptCard({required this.staff, required this.dept, required this.people, required this.index, required this.enter, required this.total, this.clock});
  final HoolaStaff staff;
  final HoolaDept dept;
  final List<Map<String, dynamic>> people;
  final int index;
  final Animation<double> enter;
  final Duration total;
  final ValueListenable<double>? clock;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final delay = 260 + index * 45;
    final ready = people.isEmpty ? 0.0 : people.where(HoolaStaff.live).length / people.length;
    final mine = people.where(HoolaStaff.hired).length;
    return AnimatedBuilder(
      animation: enter,
      builder: (context, _) {
        final rise = const Cubic(.2, .8, .2, 1).transform(_at(enter, total, delay, 560));
        final draw = Curves.easeInOutCubic.transform(_at(enter, total, delay + 100, 800));
        final bar = const Cubic(.2, .7, .2, 1).transform(_at(enter, total, delay + 300, 900));
        return Opacity(
          opacity: rise,
          child: Transform.translate(
            offset: Offset(0, 16 * (1 - rise)),
            child: _Card(
              label: '${dept.name}. ${deptCount(people)}${mine > 0 ? ', $mine on your team' : ''}',
              onTap: () => hoolaOpenNew(context, staff.app, HoolaDepartmentPage(staff: staff, group: dept.group)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  DeptBadge(icon: dept.icon, clock: clock, draw: draw, phase: index * .53),
                  const Spacer(),
                  if (mine > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(color: c.okSoft, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
                      child: Text('$mine', style: HoolaType.label(c).copyWith(color: c.ok)),
                    ),
                ]),
                const SizedBox(height: 14),
                Expanded(
                  child: Text(dept.name, maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: HoolaType.title(c).copyWith(fontSize: 15, height: 1.3)),
                ),
                Text(deptCount(people), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12, height: 1.35)),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: HoolaRadius.r(2),
                  child: Container(
                    height: 4,
                    color: c.sunk,
                    alignment: Alignment.centerLeft,
                    child: FractionallySizedBox(widthFactor: ready * bar, child: Container(color: c.ink)),
                  ),
                ),
              ]),
            ),
          ),
        );
      },
    );
  }
}

/// One role in a list: initials, name, two lines of what it does, its status.
class _RoleCard extends StatelessWidget {
  const _RoleCard({required this.staff, required this.e, this.clock, this.showDept = false});
  final HoolaStaff staff;
  final Map<String, dynamic> e;
  final ValueListenable<double>? clock;
  final bool showDept;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 12),
      child: _Card(
        label: '${_s(e['name'])}. ${_s(e['pitch'])}',
        onTap: () => openEmployee(context, staff, e),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          EmployeeMono(e: e),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(e['name']), style: HoolaType.title(c).copyWith(height: 1.25))),
                const SizedBox(width: 8),
                Icon(Icons.chevron_right_rounded, color: c.ink3, size: 20),
              ]),
              if (showDept) Text(hoolaDeptOf(HoolaStaff.group(e)).name, style: HoolaType.small(c).copyWith(fontSize: 12)),
              const SizedBox(height: 6),
              Text(_s(e['pitch']), maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 14, color: c.ink2, height: 1.45)),
              const SizedBox(height: 10),
              EmployeeStatus(e: e, clock: clock),
            ]),
          ),
        ]),
      ),
    );
  }
}

Future<void> openEmployee(BuildContext context, HoolaStaff staff, Map<String, dynamic> e) =>
    hoolaOpenNew(context, staff.app, HoolaEmployeePage(staff: staff, employeeKey: _s(e['key'])));

/// The employee's desk: on the phone when the phone has one, else the console's own desk, signed in.
Future<void> openEmployeeDesk(BuildContext context, HoolaStaff staff, Map<String, dynamic> e) async {
  final key = _s(e['key']);
  final native = employeeDeskNative(staff.app, key);
  if (native != null) {
    await hoolaOpenOld(context, native);
  } else {
    await hoolaOpenConsole(context, staff.app, employeeConsolePath(key), '${_s(e['name'])} desk');
  }
  await staff.load();
}

/// The round back button at the top of a page, with a small title in the middle.
class _TopBar extends StatelessWidget {
  const _TopBar({required this.middle});
  final String middle;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return SizedBox(
      height: 56,
      child: Row(children: [
        const SizedBox(width: HoolaSpace.gutter - 4),
        IconButton(
          tooltip: 'Back',
          onPressed: () => Navigator.of(context).maybePop(),
          style: IconButton.styleFrom(
            backgroundColor: c.surface,
            side: BorderSide(color: c.line),
            fixedSize: const Size.square(48),
          ),
          icon: Icon(Icons.arrow_back_ios_new_rounded, color: c.ink, size: 18),
        ),
        Expanded(child: Text(middle, textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c))),
        const SizedBox(width: 48 + HoolaSpace.gutter - 4),
      ]),
    );
  }
}

// ------------------------------------------------------------------------------------------------ a department
class HoolaDepartmentPage extends StatefulWidget {
  const HoolaDepartmentPage({super.key, required this.staff, required this.group});
  final HoolaStaff staff;
  final String group;
  @override
  State<HoolaDepartmentPage> createState() => _HoolaDepartmentPageState();
}

class _HoolaDepartmentPageState extends State<HoolaDepartmentPage> with TickerProviderStateMixin, _Motion {
  String _tab = 'all';

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: ListenableBuilder(
          listenable: widget.staff,
          builder: (context, _) {
            final dept = hoolaDeptOf(widget.group);
            final people = widget.staff.all.where((e) => HoolaStaff.group(e) == widget.group).toList();
            bool keep(Map<String, dynamic> e, String k) => switch (k) {
                  'ready' => HoolaStaff.live(e),
                  'team' => HoolaStaff.hired(e),
                  'soon' => !HoolaStaff.live(e),
                  _ => true,
                };
            final shown = people.where((e) => keep(e, _tab)).toList();
            final ready = people.where(HoolaStaff.live).length, mine = people.where(HoolaStaff.hired).length;
            Widget rise(int d, Widget w) => _Rise(enter: enter, total: openFor, delay: d, child: w);
            Widget chip(String text, {bool ok = false}) => Container(
                  height: 28,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: ok ? c.okSoft : c.surface,
                    borderRadius: HoolaRadius.r(HoolaRadius.pill),
                    border: ok ? null : Border.all(color: c.line),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    if (ok) ...[Container(width: 6, height: 6, decoration: BoxDecoration(color: c.ok, shape: BoxShape.circle)), const SizedBox(width: 6)],
                    Text(text, style: HoolaType.label(c).copyWith(color: ok ? c.ok : c.ink)),
                  ]),
                );
            return RefreshIndicator(
              onRefresh: widget.staff.load,
              child: ListView(padding: const EdgeInsets.only(bottom: 32), children: [
                const _TopBar(middle: 'AI Employees'),
                rise(0, Padding(
                  padding: const EdgeInsets.fromLTRB(28, 12, 28, 0),
                  child: Column(children: [
                    DecoratedBox(
                      decoration: BoxDecoration(shape: BoxShape.circle, boxShadow: HoolaShadow.float(c)),
                      child: AnimatedBuilder(
                        animation: enter,
                        builder: (context, _) => DeptBadge(
                          icon: dept.icon, size: 76, clock: clock,
                          draw: Curves.easeInOutCubic.transform(_at(enter, openFor, 150, 1000))),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Semantics(
                      header: true,
                      child: Text(dept.name, textAlign: TextAlign.center, style: HoolaType.hero(c).copyWith(fontSize: 30, height: 1.15)),
                    ),
                    if (dept.desc.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(dept.desc, textAlign: TextAlign.center, style: HoolaType.body(c).copyWith(color: c.ink2)),
                    ],
                    const SizedBox(height: 16),
                    Wrap(spacing: 8, runSpacing: 8, alignment: WrapAlignment.center, children: [
                      chip('${people.length} ${people.length == 1 ? 'role' : 'roles'}'),
                      chip('$ready ready'),
                      if (mine > 0) chip('$mine on your team', ok: true),
                    ]),
                  ]),
                )),
                const SizedBox(height: 24),
                rise(90, _Segments(
                  value: _tab,
                  options: [
                    ('all', 'All', people.length),
                    ('ready', 'Ready', ready),
                    ('team', 'My team', mine),
                    ('soon', 'Soon', people.length - ready),
                  ],
                  onPick: (k) {
                    HapticFeedback.selectionClick();
                    setState(() => _tab = k);
                  },
                )),
                const SizedBox(height: 16),
                if (shown.isEmpty)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(32, 32, 32, 16),
                    child: Text(_tab == 'team' ? 'Nobody from here works for you yet.' : 'Nobody here yet. Try All.',
                        textAlign: TextAlign.center, style: HoolaType.body(c).copyWith(color: c.ink3)),
                  )
                else
                  for (var i = 0; i < shown.length; i++)
                    rise(160 + i * 60, _RoleCard(staff: widget.staff, e: shown[i], clock: clock)),
              ]),
            );
          },
        ),
      ),
    );
  }
}

/// All / Ready / My team / Soon: a soft track with the chosen one on a black pill.
class _Segments extends StatelessWidget {
  const _Segments({required this.value, required this.options, required this.onPick});
  final String value;
  final List<(String, String, int)> options;
  final ValueChanged<String> onPick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
      child: Row(children: [
        for (final (k, label, n) in options)
          Expanded(
            child: Semantics(
              selected: k == value,
              button: true,
              label: '$label, $n',
              excludeSemantics: true,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => onPick(k),
                child: AnimatedContainer(
                  duration: HoolaMotion.of(context, HoolaMotion.menu),
                  curve: HoolaMotion.ease,
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: k == value ? c.pill : Colors.transparent,
                    borderRadius: HoolaRadius.r(HoolaRadius.pill),
                  ),
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                      child: Text('$label $n',
                          style: HoolaType.label(c).copyWith(fontSize: 13, color: k == value ? c.onPill : c.ink2)),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ]),
    );
  }
}

// ------------------------------------------------------------------------------------------------ one employee
class HoolaEmployeePage extends StatefulWidget {
  const HoolaEmployeePage({super.key, required this.staff, required this.employeeKey});
  final HoolaStaff staff;
  final String employeeKey;
  @override
  State<HoolaEmployeePage> createState() => _HoolaEmployeePageState();
}

class _HoolaEmployeePageState extends State<HoolaEmployeePage> with TickerProviderStateMixin, _Motion {
  String? _look;   // the trust level she is reading about (null = the one it has)

  HoolaStaff get staff => widget.staff;

  void _say(String text) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _do(Map<String, dynamic> e, String action) async {
    final c = HoolaColors.of(context);
    final name = _s(e['name']);
    if (action == 'leave') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('Let $name go?'),
          content: const Text('Its jobs stop at once. Its history stays, read only.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text('Let go', style: TextStyle(color: c.bad))),
          ],
        ),
      );
      if (ok != true) return;
    }
    final err = await staff.act(_s(e['key']), action);
    if (err != null) return _say(err);
    _say(switch (action) {
      'hire' => '$name is hired. Set it up on its desk.',
      'pause' => 'Paused. No jobs run until you resume.',
      'resume' => 'Back at work.',
      _ => 'Let go. Its jobs have stopped.',
    });
    if (action == 'hire' && mounted) {
      final now = staff.byKey(_s(e['key']));
      if (now != null && HoolaStaff.hired(now)) await openEmployeeDesk(context, staff, now);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: ListenableBuilder(
          listenable: staff,
          builder: (context, _) {
            final e = staff.byKey(widget.employeeKey);
            if (e == null) {
              return Column(children: [
                const _TopBar(middle: 'AI Employees'),
                const Expanded(child: HoolaEmpty(icon: Icons.person_off_outlined, title: 'This employee is not on the list any more')),
              ]);
            }
            return Stack(children: [
              Positioned.fill(child: _page(context, e)),
              Positioned(left: 0, right: 0, bottom: 0, child: _actions(context, e)),
            ]);
          },
        ),
      ),
    );
  }

  Widget _page(BuildContext context, Map<String, dynamic> e) {
    final c = HoolaColors.of(context);
    final dept = hoolaDeptOf(HoolaStaff.group(e));
    final live = HoolaStaff.live(e);
    Widget rise(int d, Widget w) => _Rise(enter: enter, total: openFor, delay: d, child: w);
    List<String> items(String k) => [for (final x in (e[k] as List? ?? const [])) '$x'];
    final does = items('does'), needs = items('needs'), never = items('never');
    return ListView(padding: const EdgeInsets.only(bottom: 170), children: [
      _TopBar(middle: dept.name),
      rise(0, Padding(
        padding: const EdgeInsets.fromLTRB(28, 12, 28, 0),
        child: Column(children: [
          _Ringed(clock: live ? clock : null, child: EmployeeMono(e: e, size: 84, serif: true)),
          const SizedBox(height: 16),
          Semantics(header: true, child: Text(_s(e['name']), textAlign: TextAlign.center, style: HoolaType.hero(c).copyWith(fontSize: 30, height: 1.15))),
          const SizedBox(height: 10),
          EmployeeStatus(e: e, clock: clock),
          const SizedBox(height: 16),
          Text(_s(e['pitch']), textAlign: TextAlign.center,
              style: TextStyle(fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 17, height: 1.5, color: c.ink)),
        ]),
      )),
      if (live) ...[
        const SizedBox(height: 24),
        rise(100, _trustCard(context, e)),
      ],
      if (does.isNotEmpty) ...[
        rise(160, const _Heading('What it does')),
        rise(170, _ListCard(items: does, mark: _Mark.tick)),
      ],
      if (needs.isNotEmpty) ...[
        rise(220, const _Heading('What it needs from you')),
        rise(230, _ListCard(items: needs, mark: _Mark.number)),
      ],
      if (never.isNotEmpty) ...[
        rise(280, const _Heading('It will never')),
        rise(290, _ListCard(items: never, mark: _Mark.never)),
      ],
      if (!live)
        Padding(
          padding: const EdgeInsets.fromLTRB(32, 24, 32, 0),
          child: Text('This one is still being built. It can be hired as soon as it is ready.',
              textAlign: TextAlign.center, style: HoolaType.body(c).copyWith(color: c.ink3)),
        ),
    ]);
  }

  Widget _trustCard(BuildContext context, Map<String, dynamic> e) {
    final c = HoolaColors.of(context);
    final hired = HoolaStaff.hired(e);
    final has = hired ? HoolaStaff.trust(e) : 'seekh';
    final look = _look ?? has;
    final keys = hoolaTrust.keys.toList();
    final at = keys.indexOf(look);
    final t = hoolaTrust[look]!;
    final canSet = hired && look != has && look != 'bharosa';
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: c.surface,
        borderRadius: HoolaRadius.r(24),
        border: Border.all(color: c.line),
        boxShadow: HoolaShadow.card(c),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Semantics(header: true, child: Text('How much it does on its own', style: HoolaType.title(c))),
        const SizedBox(height: 4),
        Text(hired ? 'It is on ${hoolaTrust[has]!.$1} now. Tap a step to read it.' : 'Every new employee starts on Learning. You can change it after hiring.',
            style: HoolaType.small(c)),
        const SizedBox(height: 14),
        Row(children: [
          for (var i = 0; i < keys.length; i++) ...[
            if (i > 0) const SizedBox(width: 6),
            Expanded(
              child: Semantics(
                button: true,
                selected: keys[i] == look,
                label: '${hoolaTrust[keys[i]]!.$1}${keys[i] == has ? ', now' : ''}',
                excludeSemantics: true,
                child: InkWell(
                  borderRadius: HoolaRadius.r(12),
                  onTap: () {
                    HapticFeedback.selectionClick();
                    setState(() => _look = keys[i]);
                  },
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(minHeight: 48),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        ClipRRect(
                          borderRadius: HoolaRadius.r(3),
                          child: Container(
                            height: 6,
                            color: c.sunk,
                            alignment: Alignment.centerLeft,
                            child: AnimatedFractionallySizedBox(
                              duration: HoolaMotion.of(context, const Duration(milliseconds: 420)),
                              curve: HoolaMotion.ease,
                              widthFactor: i <= at ? 1 : 0,
                              child: Container(color: c.ink),
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(hoolaTrust[keys[i]]!.$1,
                            style: HoolaType.label(c).copyWith(
                                fontSize: 14,
                                color: keys[i] == look ? c.ink : c.ink2,
                                fontWeight: keys[i] == look ? FontWeight.w600 : FontWeight.w500)),
                        Text(hoolaTrust[keys[i]]!.$2, style: HoolaType.small(c).copyWith(fontSize: 12)),
                      ]),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ]),
        const SizedBox(height: 14),
        AnimatedSwitcher(
          duration: HoolaMotion.of(context, HoolaMotion.fade),
          child: Container(
            key: ValueKey(look),
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(16)),
            child: Text(t.$3, style: HoolaType.body(c).copyWith(fontSize: 14)),
          ),
        ),
        if (canSet) ...[
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: OutlinedButton(
              onPressed: () async {
                final err = await staff.setTrust(_s(e['key']), look);
                if (err != null) return _say(err);
                setState(() => _look = null);
                _say('${_s(e['name'])} is on ${t.$1} now.');
              },
              style: OutlinedButton.styleFrom(shape: const StadiumBorder(), side: BorderSide(color: c.lineStrong), foregroundColor: c.ink),
              child: Text('Use ${t.$1}', style: HoolaType.button(c).copyWith(fontSize: 15)),
            ),
          ),
        ] else if (hired && look == 'bharosa' && has != 'bharosa') ...[
          const SizedBox(height: 10),
          Text('Trusted is turned on from its desk, once it has shown good work.', style: HoolaType.small(c)),
        ],
      ]),
    );
  }

  Widget _actions(BuildContext context, Map<String, dynamic> e) {
    final c = HoolaColors.of(context);
    final hired = HoolaStaff.hired(e), live = HoolaStaff.live(e), paused = e['status'] == 'paused';
    final busy = staff.busy;
    final main = ButtonStyle(
      backgroundColor: WidgetStatePropertyAll(c.pill),
      foregroundColor: WidgetStatePropertyAll(c.onPill),
      shape: const WidgetStatePropertyAll(StadiumBorder()),
      elevation: const WidgetStatePropertyAll(0.0),
    );
    return Container(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 28, HoolaSpace.gutter + 4, 16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [c.bg.withOpacity(0), c.bg],
          stops: const [0, .32],
        ),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        if (!live)
          SizedBox(
            width: double.infinity,
            height: 56,
            child: FilledButton(
              onPressed: null,
              style: FilledButton.styleFrom(shape: const StadiumBorder()),
              child: const Text('Coming soon'),
            ),
          )
        else if (!hired) ...[
          DecoratedBox(
            decoration: BoxDecoration(borderRadius: HoolaRadius.r(HoolaRadius.pill), boxShadow: HoolaShadow.float(c)),
            child: SizedBox(
              width: double.infinity,
              height: 56,
              child: FilledButton(
                onPressed: busy ? null : () => _do(e, 'hire'),
                style: main,
                child: busy
                    ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                    : Text('Hire ${_s(e['name'])}', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.button(c, color: c.onPill)),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text('Pause or let it go any time.', style: HoolaType.small(c)),
        ] else ...[
          SizedBox(
            width: double.infinity,
            height: 56,
            child: FilledButton.icon(
              onPressed: busy ? null : () => openEmployeeDesk(context, staff, e),
              style: main,
              icon: const Icon(Icons.dashboard_outlined, size: 20),
              label: Text('Open desk', style: HoolaType.button(c, color: c.onPill)),
            ),
          ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: OutlinedButton(
                onPressed: busy ? null : () => _do(e, paused ? 'resume' : 'pause'),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                  shape: const StadiumBorder(),
                  side: BorderSide(color: c.lineStrong),
                  foregroundColor: c.ink,
                  backgroundColor: c.surface,
                ),
                child: Text(paused ? 'Resume' : 'Pause'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextButton(
                onPressed: busy ? null : () => _do(e, 'leave'),
                style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48), shape: const StadiumBorder()),
                child: Text('Let go', style: TextStyle(color: c.bad)),
              ),
            ),
          ]),
        ],
      ]),
    );
  }
}

/// A soft ring going out from the circle while the employee can work.
class _Ringed extends StatelessWidget {
  const _Ringed({required this.child, this.clock});
  final Widget child;
  final ValueListenable<double>? clock;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final ck = clock;
    final lifted = DecoratedBox(decoration: BoxDecoration(shape: BoxShape.circle, boxShadow: HoolaShadow.float(c)), child: child);
    if (ck == null) return lifted;
    return ValueListenableBuilder<double>(
      valueListenable: ck,
      child: lifted,
      builder: (context, s, child) {
        final p = const Cubic(.2, .7, .2, 1).transform((s / 2.8) % 1);
        return Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
          IgnorePointer(
            child: Transform.scale(
              scale: .92 + .43 * p,
              child: Container(
                width: 84,
                height: 84,
                decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: c.ink.withOpacity(.55 * (1 - p)), width: 1.5)),
              ),
            ),
          ),
          child!,
        ]);
      },
    );
  }
}

enum _Mark { tick, number, never }

/// A list in one card: a tick (what it does), a number (what it needs) or a quiet minus (what it never does).
class _ListCard extends StatelessWidget {
  const _ListCard({required this.items, required this.mark});
  final List<String> items;
  final _Mark mark;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final quiet = mark == _Mark.never;
    Widget badge(int i) => Container(
          width: 26,
          height: 26,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: switch (mark) { _Mark.tick => c.pill, _Mark.number => c.sunk, _Mark.never => Colors.transparent },
            border: quiet ? Border.all(color: c.ink3, width: 1.5) : null,
          ),
          child: switch (mark) {
            _Mark.tick => Icon(Icons.check_rounded, size: 15, color: c.onPill),
            _Mark.number => Text('${i + 1}', style: HoolaType.label(c).copyWith(color: c.ink, fontWeight: FontWeight.w600)),
            _Mark.never => Icon(Icons.remove_rounded, size: 14, color: c.ink3),
          },
        );
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      decoration: BoxDecoration(
        color: quiet ? Colors.transparent : c.surface,
        borderRadius: HoolaRadius.r(24),
        border: Border.all(color: quiet ? c.lineStrong : c.line),
        boxShadow: quiet ? null : HoolaShadow.card(c),
      ),
      child: Column(children: [
        for (var i = 0; i < items.length; i++)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(border: i < items.length - 1 ? Border(bottom: BorderSide(color: c.line)) : null),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              badge(i),
              const SizedBox(width: 12),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(items[i], style: HoolaType.body(c).copyWith(fontSize: 14.5, color: quiet ? c.ink2 : c.ink)),
                ),
              ),
            ]),
          ),
      ]),
    );
  }
}
