// v0.900 SAB CARD NAYE (owner: "check the card in chat space looks stale and random ... make it perfect human native and
// smooth and advance" -> design canvas -> "GO BUILD ALL CARDS"). Every card in the new chat now uses the one card shell
// (hoola_card.dart HoolaCard): a quiet label line (where it comes from + when), a tinted tile, the title, the status in
// plain words with a dot, the body, and the buttons docked at the bottom (the quiet one on the left, the main one on
// the right). No card is drawn in the old dark frame any more.
//
//   HCGoal          the long task: step bar, finished steps with their time, the running step with what it is doing
//                   now, a live clock, Stop as a soft red button; waiting for her = an amber edge; done = the result.
//   HCOperatorTask  a job in Hoola's browser: live screen, the stage, Stop; Details = the old full card (proof, files).
//   HCOperatorAsk   a question from a job: choices / a yes / a short answer right in the card; an OTP, CAPTCHA, secret
//                   or payment step opens the old card (its own guarded boxes) with one tap.
//   HCQuietLine     memory used / remembered / older messages summarised: one quiet line under the reply, not a card.
//   HCCalendar, HCPlaces, HCPhoto, HCReconnect, HCLinkApp: redrawn with every button they had.
//   HCLegacy        every other kind (hundreds of desk cards): the new card read from its data (title, one line, up to
//                   three facts, progress, amount) + Details / Review, which opens that kind's full card in a sheet -
//                   every button it ever had is one tap away, nothing is lost.
// Nothing here acts by itself; money still goes only through the approval sheet.

import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../native.dart';
import '../../state.dart';
import '../any_card.dart' show AnyEventCard;
import '../chat_screen.dart' show feedCard;
import '../desk_cards.dart' show showCompactSheet;
import '../drive_screen.dart' show DriveScreen;
import '../glass.dart' show santoshTheme;
import '../hoola_theme.dart';
import '../operator_screen.dart' show OperatorFrame, openOperatorLive;
import 'hoola_card.dart';

String _s(Object? o) => o is String ? o.trim() : (o is num ? '$o' : '');

List<Map<String, dynamic>> _rows(Object? v) =>
    v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : <Map<String, dynamic>>[];

void _toast(BuildContext context, String t) =>
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t), duration: const Duration(seconds: 2)));

/// "4:12" / "1:02:40" - a clock for a job.
String hcClock(Duration d) {
  final s = d.inSeconds < 0 ? 0 : d.inSeconds;
  final h = s ~/ 3600, m = (s % 3600) ~/ 60, x = s % 60;
  String two(int n) => n.toString().padLeft(2, '0');
  return h > 0 ? '$h:${two(m)}:${two(x)}' : '$m:${two(x)}';
}

/// "10:01" in her phone's time.
String hcTime(DateTime? at) {
  if (at == null) return '';
  final l = at.toLocal();
  return '${l.hour}:${l.minute.toString().padLeft(2, '0')}';
}

/// The soft red Stop button of a running job.
Widget hcStop(BuildContext context, VoidCallback? onTap, {String label = 'Stop'}) {
  final c = HoolaColors.of(context);
  return TextButton.icon(
    onPressed: onTap,
    style: TextButton.styleFrom(
      backgroundColor: c.badSoft,
      foregroundColor: c.bad,
      minimumSize: const Size(0, 44),
      padding: const EdgeInsets.symmetric(horizontal: 16),
      shape: const StadiumBorder(),
    ),
    icon: Icon(Icons.stop_rounded, size: 18, color: c.bad),
    label: Text(label, style: HoolaType.button(c, color: c.bad).copyWith(fontSize: 15, fontWeight: FontWeight.w500)),
  );
}

/// A desk name for a card kind ("seva_ticket" -> "Customer care · ticket").
String hcDesk(String kind) {
  const names = {
    'hoola': 'Hoola Network', 'seva': 'Customer care', 'helpdesk': 'Help desk', 'shikayat': 'Complaints',
    'aftersales': 'After sales', 'feedback': 'Feedback', 'wapsi': 'Returns', 'samudaay': 'Community',
    'callcentre': 'Call centre', 'devsahayak': 'Hoola Code', 'qa': 'Testing', 'itadmin': 'IT admin', 'ispnoc': 'Network desk',
    'cyber': 'Security', 'devops': 'DevOps', 'docwriter': 'Docs', 'appreview': 'App review', 'mshop': 'Shop',
    'theka': 'Contracts', 'fr': 'Finance', 'niryat': 'Export', 'thok': 'Wholesale', 'seo': 'SEO', 'social': 'Social media',
    'ins': 'Insurance', 'audit': 'Audit', 'tele': 'Tele-calling', 'gst': 'GST', 'payroll': 'Payroll', 'a2a': 'Agents',
    'email': 'Email', 'studio': 'Create', 'video': 'Video', 'site': 'Website', 'app': 'App Studio', 'brand': 'Brand',
  };
  final k = kind.trim();
  if (k.isEmpty) return 'Card';
  final parts = k.split('_').where((w) => w.isNotEmpty).toList();
  final head = names[parts.first];
  final rest = (head == null ? parts : parts.skip(1)).join(' ');
  if (head == null) return '${rest[0].toUpperCase()}${rest.substring(1)}';
  return rest.isEmpty ? head : '$head · $rest';
}

// ============================================================================================ the old card, one tap away

/// Opens a kind's full old card in a sheet (all its buttons), live: it redraws as the card's state changes.
Future<void> showOldCardSheet(BuildContext context, Santosh app, FeedItem it) {
  final old = santoshTheme();
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    backgroundColor: old.scaffoldBackgroundColor,
    builder: (ctx) => Theme(
      data: old,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * .86),
        child: SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(12, 0, 12, 16 + MediaQuery.viewInsetsOf(ctx).bottom),
          child: ListenableBuilder(
            listenable: app,
            builder: (c, _) => feedCard(c, app, it) ?? const SizedBox(height: 80),
          ),
        ),
      ),
    ),
  );
}

/// Every kind without a card of its own in the new design: the new card read from the kind's data, and the full old
/// card (with all its buttons) behind Details / Review.
class HCLegacy extends StatelessWidget {
  const HCLegacy({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;

  @override
  Widget build(BuildContext context) {
    final v = <String, dynamic>{...it.data, '_kind': it.kind};
    final asks = AnyEventCard.stateOf(v) == 'ask';
    return HCAny(
      v: v,
      at: it.at,
      label: hcDesk(it.kind),
      lead: asks ? const [] : [hcQuiet(context, 'Details', () => showOldCardSheet(context, app, it))],
      main: asks ? hcMain(context, 'Review', () => showOldCardSheet(context, app, it), icon: Icons.chevron_right_rounded) : null,
    );
  }
}

// ============================================================================================ the long task

class HCGoal extends StatefulWidget {
  const HCGoal({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;
  @override
  State<HCGoal> createState() => _HCGoalState();
}

class _HCGoalState extends State<HCGoal> {
  Timer? _tick;
  bool _open = true;   // a running job's steps (she can hide them)
  bool _more = false;  // a finished long job's steps (folded at first)
  bool _busy = false;

  Map<String, dynamic> get v => widget.it.data;
  String get _status => _s(v['status']).isEmpty ? 'working' : _s(v['status']);
  bool get _running => _status == 'working' || _status == 'blocked';

  @override
  void initState() {
    super.initState();
    _clock();
  }

  @override
  void didUpdateWidget(covariant HCGoal old) {
    super.didUpdateWidget(old);
    _clock();
  }

  void _clock() {
    if (_running && _tick == null) {
      _tick = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() {});
      });
    } else if (!_running) {
      _tick?.cancel();
      _tick = null;
    }
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  Future<void> _call(Future<void> Function(String id) job, String ok, String bad) async {
    final id = widget.app.conversationId;
    if (id == null || widget.app.api == null || _busy) return;
    setState(() => _busy = true);
    try {
      await job(id);
      if (mounted) _toast(context, ok);
    } catch (_) {
      if (mounted) _toast(context, bad);
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final steps = _rows(v['steps']);
    final done = (v['done'] as num?)?.toInt() ?? steps.where((s) => s['state'] == 'done').length;
    final total = (v['total'] as num?)?.toInt() ?? steps.length;
    final reason = _s(v['reason']);
    final hold = _s(v['hold']);
    final report = v['report'] is Map ? Map<String, dynamic>.from(v['report'] as Map) : const <String, dynamic>{};
    final started = DateTime.tryParse(_s(v['started_at']));
    final ended = DateTime.tryParse(_s(v['updated_at']));
    final clock = started == null ? '' : hcClock((_running ? DateTime.now() : (ended ?? DateTime.now())).difference(started));
    final curIx = steps.indexWhere((s) => s['state'] == 'current');
    final st = switch (_status) {
      'done' => HCStatus.done(c, total > 0 ? 'Done · $done of $total steps' : 'Done'),
      'blocked' => HCStatus(hold == 'limit' ? 'Paused · needs your OK to go on' : 'Waiting for your answer', c.warn),
      'failed' => HCStatus.failed(c, 'Stopped before the end'),
      'stopped' => HCStatus.quiet(c, 'You stopped it'),
      _ => HCStatus.working(c, total > 0 ? 'Step ${(curIx < 0 ? done : curIx) + 1} of $total' : 'Working'),
    };
    // running: the steps show unless she hid them; finished: a short list shows, a long one folds behind Steps
    final showSteps = _running ? _open : (steps.length <= 6 || _more);
    return HoolaCard(
      icon: switch (_status) {
        'done' => Icons.check_rounded,
        'blocked' => Icons.help_outline_rounded,
        'failed' => Icons.error_outline_rounded,
        'stopped' => Icons.stop_circle_outlined,
        _ => Icons.manage_search_rounded,
      },
      label: started == null ? 'Long task' : 'Long task · ${_running ? 'started ' : ''}${hcTime(started)}',
      when: clock,
      whenMono: true,
      title: _s(v['title'] ?? v['goal']).isEmpty ? 'Long task' : _s(v['title'] ?? v['goal']),
      status: st,
      highlight: _status == 'blocked',
      children: [
        if (total > 0) _Segments(steps: steps, total: total, done: done),
        if (showSteps && steps.isNotEmpty)
          Column(children: [
            for (final s in steps.take(15)) _StepRow(s: s, app: widget.app, live: _status == 'working'),
          ]),
        if (reason.isNotEmpty && _status != 'working' && report.isEmpty)
          Text(reason, style: HoolaType.body(c).copyWith(color: _status == 'failed' ? c.bad : c.ink2)),
        if (report.isNotEmpty) _GoalReport(report: report),
      ],
      lead: [
        if (_running && steps.isNotEmpty) hcQuiet(context, _open ? 'Hide steps' : 'Show steps', () => setState(() => _open = !_open)),
        if (!_running && steps.length > 6) hcQuiet(context, _more ? 'Hide steps' : 'Steps', () => setState(() => _more = !_more)),
      ],
      actions: [
        if (_status == 'blocked' && hold == 'limit')
          hcMain(context, 'Go on', _busy ? null : () => _call(widget.app.api!.continueGoal, 'OK, moving the work forward.', 'Could not move ahead right now, try again.'),
              icon: Icons.play_arrow_rounded, busy: _busy),
        if (_running)
          hcStop(context, _busy ? null : () => _call(widget.app.api!.stopGoal, 'The long task was stopped.', 'Could not stop it, try again.')),
      ],
    );
  }
}

/// The thin step bar: done steps green, the running one violet, the rest empty.
class _Segments extends StatelessWidget {
  const _Segments({required this.steps, required this.total, required this.done});
  final List<Map<String, dynamic>> steps;
  final int total;
  final int done;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final n = total.clamp(1, 15);
    Color tone(int i) {
      final st = i < steps.length ? _s(steps[i]['state']) : (i < done ? 'done' : 'pending');
      return switch (st) { 'done' => c.ok, 'current' => c.accent, 'failed' => c.bad, 'skipped' => c.lineStrong, _ => c.sunk };
    }
    return Semantics(
      label: '$done of $total steps done',
      child: Row(children: [
        for (var i = 0; i < n; i++) ...[
          if (i > 0) const SizedBox(width: 4),
          Expanded(child: Container(height: 4, decoration: BoxDecoration(color: tone(i), borderRadius: HoolaRadius.r(4)))),
        ],
      ]),
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow({required this.s, required this.app, required this.live});
  final Map<String, dynamic> s;
  final Santosh app;
  final bool live;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final st = _s(s['state']).isEmpty ? 'pending' : _s(s['state']);
    final n = (s['n'] as num?)?.toInt();
    final note = _s(s['note']);
    final now = st == 'current' && live ? (app.currentStep ?? '') : '';
    final Widget ic = switch (st) {
      'done' => Icon(Icons.check_circle_rounded, size: 18, color: c.ok),
      'current' => SizedBox(width: 15, height: 15, child: CircularProgressIndicator(strokeWidth: 2, color: c.accent, backgroundColor: c.accentSoft)),
      'failed' => Icon(Icons.cancel_rounded, size: 18, color: c.bad),
      'skipped' => Icon(Icons.remove_circle_outline_rounded, size: 18, color: c.ink3),
      _ => Container(
          width: 18,
          height: 18,
          alignment: Alignment.center,
          decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: c.lineStrong, width: 1.5)),
          child: n == null ? null : Text('$n', style: HoolaType.label(c).copyWith(fontSize: 12, height: 1, color: c.ink3)),
        ),
    };
    final text = _s(s['text']);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(width: 20, height: 20, child: Center(child: ic)),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(text,
                style: HoolaType.body(c).copyWith(
                  fontSize: 14,
                  fontWeight: st == 'current' ? FontWeight.w600 : FontWeight.w400,
                  color: st == 'done' ? c.ink2 : (st == 'pending' || st == 'skipped') ? c.ink3 : c.ink,
                )),
            if (now.isNotEmpty && now != text)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(now, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.accent)),
              ),
            if (note.isNotEmpty && st != 'current')
              Text(note, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
          ]),
        ),
      ]),
    );
  }
}

/// The end-of-job report: one line, then what happened / what was made / what is left / what she needs to do.
class _GoalReport extends StatelessWidget {
  const _GoalReport({required this.report});
  final Map<String, dynamic> report;
  List<String> _list(String k) => (report[k] as List? ?? const []).map((e) => '$e').where((e) => e.trim().isNotEmpty).toList();
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final summary = _s(report['summary']);
    final aapka = _s(report['aapka']);
    Widget part(String head, List<String> lines) => Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(head, style: HoolaType.label(c)),
            for (final l in lines.take(10))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Padding(padding: const EdgeInsets.only(top: 8), child: Container(width: 4, height: 4, decoration: BoxDecoration(color: c.ink3, shape: BoxShape.circle))),
                  const SizedBox(width: 8),
                  Expanded(child: SelectableText(l, style: HoolaType.body(c).copyWith(fontSize: 14))),
                ]),
              ),
          ]),
        );
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (summary.isNotEmpty) Text(summary, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
        if (_list('hua').isNotEmpty) part('What happened', _list('hua')),
        if (_list('bana').isNotEmpty) part('What was made', _list('bana')),
        if (_list('pending').isNotEmpty) part('What is left', _list('pending')),
        if (aapka.isNotEmpty) part('What you need to do', [aapka]),
      ]),
    );
  }
}

// ============================================================================================ jobs in Hoola's browser

class HCOperatorTask extends StatefulWidget {
  const HCOperatorTask({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;
  @override
  State<HCOperatorTask> createState() => _HCOperatorTaskState();
}

class _HCOperatorTaskState extends State<HCOperatorTask> {
  bool _busy = false;

  Future<void> _stop() async {
    if (widget.app.api == null || _busy) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.operatorCancel(_s(widget.it.data['id']));
      widget.it.data.addAll(r);
    } catch (e) {
      if (mounted) _toast(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = widget.it.data;
    final status = _s(v['status']).isEmpty ? 'queued' : _s(v['status']);
    final live = status == 'running' || status == 'waiting';
    final steps = (v['steps'] as num?)?.toInt() ?? 0;
    final stage = _s(v['stage']);
    final site = _s(v['site']);
    final st = switch (status) {
      'queued' => HCStatus.quiet(c, 'In the queue'),
      'running' => HCStatus.working(c, steps > 0 ? 'Working · step $steps' : 'Working'),
      'waiting' => HCStatus('Waiting for you', c.warn),
      'done' => HCStatus.done(c, steps > 0 ? 'Done · $steps steps' : 'Done'),
      'cancelled' || 'stopped' => HCStatus.quiet(c, 'Stopped'),
      _ => HCStatus.failed(c),
    };
    return HoolaCard(
      icon: Icons.travel_explore_rounded,
      label: ["${widget.app.aName}'s browser", if (site.isNotEmpty) site].join(' · '),
      when: hcAgo(widget.it.at),
      title: _s(v['task']).isEmpty ? 'A job on a website' : _s(v['task']),
      status: st,
      highlight: status == 'waiting',
      children: [
        if (live)
          GestureDetector(
            onTap: () => openOperatorLive(context, widget.app),
            child: ClipRRect(
              borderRadius: HoolaRadius.r(HoolaRadius.tile),
              child: Container(
                decoration: BoxDecoration(color: c.sunk, border: Border.all(color: c.line), borderRadius: HoolaRadius.r(HoolaRadius.tile)),
                constraints: const BoxConstraints(maxHeight: 200),
                child: OperatorFrame(app: widget.app, every: 900, fit: BoxFit.cover),
              ),
            ),
          ),
        if (stage.isNotEmpty)
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(width: 2, height: 20, margin: const EdgeInsets.only(right: 10, top: 1), color: c.accentSoft),
            Expanded(child: Text(stage, maxLines: 3, overflow: TextOverflow.ellipsis, style: HoolaType.reply(c).copyWith(fontSize: 14.5, fontStyle: FontStyle.italic, color: c.ink2))),
          ]),
      ],
      lead: [hcQuiet(context, live ? 'Watch' : 'Details', live ? () => openOperatorLive(context, widget.app) : () => showOldCardSheet(context, widget.app, widget.it))],
      actions: [if (live || status == 'queued') hcStop(context, _busy ? null : _stop)],
    );
  }
}

class HCOperatorAsk extends StatefulWidget {
  const HCOperatorAsk({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;
  @override
  State<HCOperatorAsk> createState() => _HCOperatorAskState();
}

class _HCOperatorAskState extends State<HCOperatorAsk> {
  final _box = TextEditingController();
  bool _busy = false;
  String? _pick;

  static const _titles = {
    'approve': 'Needs your OK', 'payment': 'Make the payment yourself', 'otp': 'Enter the OTP', 'captcha': 'Check the CAPTCHA',
    'secret': 'Enter this yourself', 'question': 'One question', 'choice': 'You choose', 'takeover': 'Do this step yourself',
  };

  @override
  void dispose() {
    _box.clear();
    _box.dispose();
    super.dispose();
  }

  Future<void> _answer(bool yes, {String answer = ''}) async {
    if (widget.app.api == null || _busy) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.operatorAnswer(_s(widget.it.data['id']), yes, answer: answer);
      widget.it.data.addAll(r);
      _box.clear();
    } catch (e) {
      if (mounted) _toast(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = widget.it.data;
    final kind = _s(v['kind']).isEmpty ? 'question' : _s(v['kind']);
    final status = _s(v['status']).isEmpty ? 'pending' : _s(v['status']);
    final pending = status == 'pending';
    final options = (v['options'] as List? ?? const []).map((e) => '$e').where((e) => e.trim().isNotEmpty).toList();
    final guarded = const {'otp', 'captcha', 'secret', 'payment', 'takeover'}.contains(kind);
    final where = [_s(v['site']), if (_s(v['target_name']).isNotEmpty) 'Button "${_s(v['target_name'])}"'].where((e) => e.isNotEmpty).join(' · ');
    final st = pending
        ? HCStatus('Waiting for you · the job waits too', c.warn)
        : (status == 'approved' || status == 'done')
            ? HCStatus.done(c, 'Answered')
            : status == 'expired'
                ? HCStatus.quiet(c, 'Time ran out')
                : HCStatus.quiet(c, 'Declined');
    final reason = _s(v['reason']);
    return HoolaCard(
      icon: switch (kind) {
        'payment' => Icons.currency_rupee_rounded,
        'otp' => Icons.sms_outlined,
        'captcha' => Icons.text_fields_rounded,
        'secret' => Icons.lock_outline_rounded,
        'approve' => Icons.task_alt_rounded,
        'takeover' => Icons.touch_app_outlined,
        _ => Icons.help_outline_rounded,
      },
      label: where.isEmpty ? 'Question from the job' : where,
      when: hcAgo(widget.it.at),
      title: reason.isEmpty ? (_titles[kind] ?? 'Question for you') : reason,
      status: st,
      highlight: pending,
      children: [
        if (pending && !guarded && options.isNotEmpty)
          Column(children: [
            for (final o in options.take(8))
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _Choice(label: o, on: _pick == o, onTap: () => setState(() => _pick = o)),
              ),
          ]),
        if (pending && !guarded && (kind == 'question' || options.isNotEmpty))
          TextField(
            controller: _box,
            minLines: 1,
            maxLines: 3,
            onChanged: (_) => setState(() => _pick = null),
            decoration: InputDecoration(
              hintText: options.isEmpty ? 'Your answer' : 'Or say something else',
              isDense: true,
              filled: true,
              fillColor: c.sunk,
              border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide.none),
            ),
          ),
        if (pending && guarded)
          HCNote(kind == 'payment'
              ? 'Pay in your own app or page. Hoola never types a PIN or card number.'
              : 'This goes straight into the website box. Hoola never sees or keeps it.'),
      ],
      lead: [
        if (pending && !guarded) hcQuiet(context, 'No', _busy ? null : () => _answer(false)),
      ],
      actions: [
        if (pending && guarded)
          hcMain(context, 'Answer', () => showOldCardSheet(context, widget.app, widget.it), icon: Icons.chevron_right_rounded)
        else if (pending && (options.isNotEmpty || kind == 'question'))
          hcMain(context, options.isEmpty ? 'Send' : 'Choose', _busy
              ? null
              : () {
                  final a = _box.text.trim().isNotEmpty ? _box.text.trim() : (_pick ?? '');
                  if (a.isEmpty) return;
                  HapticFeedback.selectionClick();
                  _answer(true, answer: a);
                }, busy: _busy)
        else if (pending)
          hcMain(context, 'Yes', _busy ? null : () => _answer(true), icon: Icons.check_rounded, busy: _busy),
      ],
    );
  }
}

/// One choice row (radio look), 52 tall.
class _Choice extends StatelessWidget {
  const _Choice({required this.label, required this.on, required this.onTap});
  final String label;
  final bool on;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      selected: on,
      button: true,
      child: Material(
        color: on ? c.accentSoft : c.surface,
        shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), side: BorderSide(color: on ? c.accent : c.line)),
        child: InkWell(
          borderRadius: HoolaRadius.r(HoolaRadius.tile),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 52),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(children: [
                Container(
                  width: 18,
                  height: 18,
                  decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: on ? c.accent : c.lineStrong, width: on ? 5 : 1.5)),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(label, style: HoolaType.body(c).copyWith(fontSize: 14))),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

// ============================================================================================ quiet lines under a reply

/// Memory used / remembered / older messages summarised: one quiet line, never a card.
class HCQuietLine extends StatefulWidget {
  const HCQuietLine({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;
  @override
  State<HCQuietLine> createState() => _HCQuietLineState();
}

class _HCQuietLineState extends State<HCQuietLine> {
  final Set<int> _gone = {};

  Future<void> _forgetUsed(List<Map<String, dynamic>> items) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) {
        final c = HoolaColors.of(ctx);
        return ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(16, 0, 16, 24), children: [
          Text('This memory helped in this answer', style: HoolaType.title(c)),
          const SizedBox(height: 8),
          for (var i = 0; i < items.length; i++)
            if (!_gone.contains(i))
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.menu_book_outlined, color: c.ink2),
                title: Text(_s(items[i]['label']).isEmpty ? 'Memory' : _s(items[i]['label'])),
                subtitle: Text(_s(items[i]['text']), maxLines: 3, overflow: TextOverflow.ellipsis),
                trailing: TextButton(
                  onPressed: () async {
                    try {
                      await widget.app.api!.unremember(items[i]);
                      setState(() => _gone.add(i));
                      setSheet(() {});
                    } catch (_) {}
                  },
                  child: const Text('Forget'),
                ),
              ),
        ]);
      }),
    );
  }

  Widget _line(BuildContext context, {required IconData icon, required String lead, required String text, String? act, VoidCallback? onAct, bool accent = false}) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        constraints: const BoxConstraints(minHeight: 44),
        padding: const EdgeInsets.only(left: 12, right: 4),
        decoration: BoxDecoration(color: accent ? c.accentSoft : c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
        child: Row(children: [
          Icon(icon, size: 16, color: accent ? c.accent : c.ink2),
          const SizedBox(width: 8),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Text.rich(
                TextSpan(children: [
                  TextSpan(text: lead, style: HoolaType.small(c).copyWith(color: c.ink2)),
                  TextSpan(text: text, style: HoolaType.small(c).copyWith(color: c.ink, fontWeight: FontWeight.w500)),
                ]),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
          if (act != null)
            TextButton(
              onPressed: onAct,
              style: TextButton.styleFrom(foregroundColor: c.accent, minimumSize: const Size(0, 44), shape: const StadiumBorder()),
              child: Text(act, style: HoolaType.label(c).copyWith(color: c.accent, fontSize: 13.5)),
            ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.it.data;
    switch (widget.it.kind) {
      case 'memory_saved':
        final facts = _rows(v['facts']).where((f) => !_gone.contains((f['id'] as num?)?.toInt() ?? -1)).toList();
        if (facts.isEmpty) return const SizedBox.shrink();
        return Column(children: [
          for (final f in facts)
            _line(context, icon: Icons.check_rounded, lead: 'Remembered: ', text: _s(f['text']), accent: true, act: 'Undo', onAct: () async {
              final id = (f['id'] as num?)?.toInt();
              if (id == null) return;
              try {
                await widget.app.api!.forget(id);
                setState(() => _gone.add(id));
              } catch (_) {}
            }),
        ]);
      case 'memory_used':
        final items = _rows(v['items']);
        final left = [for (var i = 0; i < items.length; i++) if (!_gone.contains(i)) items[i]];
        if (left.isEmpty) return const SizedBox.shrink();
        final labels = {for (final x in left) _s(x['label']).isEmpty ? 'Memory' : _s(x['label'])}.join(', ');
        return _line(context, icon: Icons.lightbulb_outline_rounded, lead: 'Used from memory: ', text: labels, act: 'See', onAct: () => _forgetUsed(items));
      default: // compact
        final n = (v['exchanges'] as num?)?.toInt() ?? 0;
        return _line(context,
            icon: Icons.unfold_less_rounded,
            lead: 'Older messages kept as a summary',
            text: n > 0 ? ' · $n' : '',
            act: 'View',
            onAct: () => showCompactSheet(context, widget.app));
    }
  }
}

// ============================================================================================ connections

class HCReconnect extends StatelessWidget {
  const HCReconnect({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final text = _s(it.data['text']);
    return HoolaCard(
      icon: Icons.sync_rounded,
      tileTone: c.info,
      label: 'Google account',
      when: hcAgo(it.at),
      title: 'Reconnect Google so Gmail and Drive keep working',
      status: HCStatus('Sign-in expired · one tap', c.info),
      children: [if (text.isNotEmpty) Text(text, style: HoolaType.body(c).copyWith(color: c.ink2))],
      lead: [hcQuiet(context, 'Check', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DriveScreen(app: app))))],
      actions: [
        hcMain(context, 'Reconnect', () async {
          try {
            final url = await app.api!.driveLinkUrl();
            await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
          } catch (e) {
            if (context.mounted) _toast(context, '$e');
          }
        }),
      ],
    );
  }
}

class HCLinkApp extends StatelessWidget {
  const HCLinkApp({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final name = _s(it.data['name']).isEmpty ? 'this app' : _s(it.data['name']);
    return HoolaCard(
      icon: Icons.link_rounded,
      tileTone: c.info,
      label: 'Connect an app',
      when: hcAgo(it.at),
      title: 'Connect $name',
      status: HCStatus('Sign in once with your own account', c.info),
      children: [
        Text('The OTP comes on their own page. After that ${app.aName} can order for you.', style: HoolaType.body(c).copyWith(color: c.ink2)),
      ],
      actions: [
        hcMain(context, 'Connect', () async {
          final err = await app.linkApp(_s(it.data['pack_id']));
          if (err != null && context.mounted) _toast(context, err);
        }, icon: Icons.link_rounded),
      ],
    );
  }
}

// ============================================================================================ calendar, places, photo

class HCCalendar extends StatelessWidget {
  const HCCalendar({super.key, required this.it});
  final FeedItem it;

  static Future<void> _open(String url) async {
    final u = Uri.tryParse(url);
    if (u != null) await launchUrl(u, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = it.data;
    final status = _s(v['status']).isEmpty ? 'added' : _s(v['status']);
    final gone = status == 'cancelled' || status == 'declined';
    final start = _s(v['start']);
    final end = _s(v['end']);
    final loc = _s(v['location']);
    final meet = _s(v['meet_link']);
    final link = _s(v['link']);
    final people = _rows(v['attendees']).map((e) => _s(e['email'])).where((e) => e.isNotEmpty).toList();
    final st = switch (status) {
      'added' => HCStatus.done(c, 'Added to your calendar'),
      'updated' => HCStatus.done(c, 'Changed in your calendar'),
      'accepted' => HCStatus.done(c, 'You said yes'),
      'tentative' => HCStatus('Maybe', c.warn),
      'soon' => HCStatus('Starting soon', c.warn),
      'cancelled' => HCStatus.quiet(c, 'Cancelled'),
      'declined' => HCStatus.quiet(c, 'You said no'),
      _ => HCStatus.quiet(c, status.replaceAll('_', ' ')),
    };
    final when = start.isEmpty ? '' : (end.isNotEmpty && v['all_day'] != true ? '$start – ${end.split(', ').last}' : start);
    return HoolaCard(
      icon: Icons.event_outlined,
      tileTone: c.info,
      label: 'Calendar',
      when: hcAgo(it.at),
      title: _s(v['title']).isEmpty ? 'Event' : _s(v['title']),
      status: st,
      children: [
        if (when.isNotEmpty) HCFact('When', when),
        if (loc.isNotEmpty) HCFact('Where', loc),
        if (people.isNotEmpty) HCFact('With', people.take(3).join(', ') + (people.length > 3 ? ' +${people.length - 3}' : '')),
      ],
      lead: [if (!gone && link.isNotEmpty) hcQuiet(context, 'Open calendar', () => _open(link))],
      actions: [if (!gone && meet.isNotEmpty) hcMain(context, 'Join Meet', () => _open(meet), icon: Icons.videocam_outlined)],
    );
  }
}

class HCPlaces extends StatefulWidget {
  const HCPlaces({super.key, required this.it});
  final FeedItem it;
  @override
  State<HCPlaces> createState() => _HCPlacesState();
}

class _HCPlacesState extends State<HCPlaces> {
  bool _all = false;

  static Future<void> _go(String url) async {
    final u = Uri.tryParse(url);
    if (u != null) await launchUrl(u, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = widget.it.data;
    final places = _rows(v['places']);
    if (places.isEmpty) return const SizedBox.shrink();
    final near = _s(v['near']);
    final cost = v['cost_inr'];
    final shown = _all ? places : places.take(3).toList();
    return HoolaCard(
      icon: Icons.place_outlined,
      tileTone: c.info,
      label: ['Maps', if (near.isNotEmpty) 'near $near'].join(' · '),
      when: '${places.length} found',
      title: _s(v['title']).isEmpty ? 'Places' : _s(v['title']),
      children: [
        for (var i = 0; i < shown.length; i++) _PlaceRow(n: i + 1, p: shown[i], go: _go),
        Text([_s(v['attribution']).isEmpty ? 'Google' : _s(v['attribution']), if (cost is num && cost > 0) '₹$cost' else if (cost is num) 'free'].join(' · '),
            style: HoolaType.small(c)),
      ],
      actions: [if (places.length > 3) hcQuiet(context, _all ? 'Show fewer' : 'Show all ${places.length}', () => setState(() => _all = !_all))],
    );
  }
}

class _PlaceRow extends StatelessWidget {
  const _PlaceRow({required this.n, required this.p, required this.go});
  final int n;
  final Map<String, dynamic> p;
  final Future<void> Function(String) go;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final open = p['open_now'];
    final bits = [
      if (p['rating'] != null) '★ ${p['rating']}${p['reviews'] != null ? ' (${p['reviews']})' : ''}',
      if (p['distance_km'] != null) '${p['distance_km']} km',
      if (open == true) 'open now' else if (open == false) 'closed',
      _s(p['type']),
    ].where((x) => x.isNotEmpty).join(' · ');
    final phone = _s(p['phone']);
    final website = _s(p['website']);
    final link = _s(p['maps_link']);
    final address = _s(p['address']);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: 26,
          height: 26,
          alignment: Alignment.center,
          decoration: BoxDecoration(color: c.sunk, shape: BoxShape.circle),
          child: Text('$n', style: HoolaType.label(c).copyWith(color: c.ink)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(p['name']), style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
            if (bits.isNotEmpty) Text(bits, style: HoolaType.small(c)),
            if (address.isNotEmpty) Text(address, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink2)),
            if (phone.isNotEmpty || website.isNotEmpty || link.isNotEmpty)
              Wrap(spacing: 4, children: [
                if (link.isNotEmpty) _mini(context, Icons.directions_outlined, 'Directions', () => go(link)),
                if (phone.isNotEmpty) _mini(context, Icons.call_outlined, 'Call', () => go('tel:${phone.replaceAll(RegExp(r'[^\d+]'), '')}')),
                if (website.isNotEmpty) _mini(context, Icons.language_rounded, 'Website', () => go(website)),
              ]),
          ]),
        ),
      ]),
    );
  }

  Widget _mini(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    final c = HoolaColors.of(context);
    return TextButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 16, color: c.ink),
      label: Text(label, style: HoolaType.label(c).copyWith(color: c.ink, fontSize: 13)),
      style: TextButton.styleFrom(minimumSize: const Size(0, 44), padding: const EdgeInsets.symmetric(horizontal: 8), shape: const StadiumBorder()),
    );
  }
}

class HCPhoto extends StatefulWidget {
  const HCPhoto({super.key, required this.app, required this.it});
  final Santosh app;
  final FeedItem it;
  @override
  State<HCPhoto> createState() => _HCPhotoState();
}

class _HCPhotoState extends State<HCPhoto> {
  bool _busy = false;
  Map<String, dynamic> get v => widget.it.data;
  String get _url => widget.app.api?.absolute(_s(v['url'])) ?? '';
  String get _name => _s(v['name']).isEmpty ? 'hoola_photo.png' : _s(v['name']);

  Future<String?> _local() async {
    final api = widget.app.api;
    if (api == null) return null;
    final bytes = await api.brandBytes(_s(v['url']));
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/${_name.replaceAll(RegExp(r'[^\w\-. ()]'), '_')}');
    await f.writeAsBytes(bytes);
    return f.path;
  }

  Future<void> _run(Future<void> Function() job) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await job();
    } catch (e) {
      if (mounted) _toast(context, 'Failed: $e (the link lasts 24 hours; for an old photo, have it made again)');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _open() {
    if (_url.isEmpty) return;
    Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => Scaffold(
              backgroundColor: Colors.black,
              appBar: AppBar(backgroundColor: Colors.black, foregroundColor: Colors.white, title: Text(_name)),
              body: InteractiveViewer(maxScale: 5, child: Center(child: Image.network(_url))),
            )));
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final edit = v['edit'] == true;
    final prompt = _s(v['prompt']);
    final meta = [_s(v['aspect']), v['quality'] == 'best' ? 'best' : 'fast', 'AI-made'].where((e) => e.isNotEmpty).join(' · ');
    return HoolaCard(
      icon: edit ? Icons.auto_fix_high_rounded : Icons.image_outlined,
      tileTone: c.accent,
      label: edit ? 'Photo changed' : 'Photo made',
      when: hcAgo(widget.it.at),
      title: prompt.isEmpty ? (edit ? 'Your photo, changed' : 'Your photo') : prompt,
      status: HCStatus.quiet(c, meta),
      children: [
        GestureDetector(
          onTap: _open,
          child: ClipRRect(
            borderRadius: HoolaRadius.r(HoolaRadius.tile),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 420),
              child: _url.isEmpty
                  ? Container(height: 160, color: c.sunk)
                  : Image.network(_url,
                      fit: BoxFit.contain,
                      loadingBuilder: (ctx, w, p) => p == null ? w : Container(height: 220, color: c.sunk),
                      errorBuilder: (ctx, e, s) => Container(
                            height: 120,
                            color: c.sunk,
                            alignment: Alignment.center,
                            child: Text('The photo link has expired (24 hours)', style: HoolaType.small(c)),
                          )),
            ),
          ),
        ),
      ],
      lead: [hcQuiet(context, 'Share', _busy ? null : () => _run(() async {
            final p = await _local();
            if (p == null) return;
            final err = await Native.shareFile(p, mime: 'image/png', title: 'Send photo');
            if (err != null && mounted) _toast(context, err);
          }))],
      actions: [
        hcMain(context, 'Save', _busy
            ? null
            : () => _run(() async {
                  final p = await _local();
                  if (p == null) return;
                  final err = await Native.saveImage(p, _name);
                  if (mounted) _toast(context, err ?? 'Saved to gallery (Pictures/Hoola)');
                }), icon: Icons.download_rounded, busy: _busy),
      ],
    );
  }
}

// ============================================================================================ one door for every kind

/// The new-design card for any feed item: the redrawn kinds, then the R4 cards, then every other kind as HCLegacy
/// (only when that kind has a card at all - a kind with no card stays invisible, as before).
Widget? hoolaCardAll(BuildContext context, Santosh app, FeedItem it) {
  switch (it.kind) {
    case 'goal':
      return HCGoal(key: ValueKey('hg${it.data['id']}'), app: app, it: it);
    case 'operator_task':
      return HCOperatorTask(key: ValueKey('hot${it.data['id']}'), app: app, it: it);
    case 'operator_ask':
      return HCOperatorAsk(key: ValueKey('hoq${it.data['id']}'), app: app, it: it);
    case 'memory_saved':
    case 'memory_used':
    case 'compact':
      return HCQuietLine(app: app, it: it);
    case 'google_reconnect':
      return HCReconnect(app: app, it: it);
    case 'link':
      return HCLinkApp(app: app, it: it);
    case 'calendar_event':
      return HCCalendar(it: it);
    case 'maps_places':
      return HCPlaces(it: it);
    case 'photo_made':
      return HCPhoto(key: ValueKey('hph${it.data['file_id']}'), app: app, it: it);
  }
  final mine = hoolaCardFor(context, app, it);
  if (mine != null) return mine;
  if (feedCard(context, app, it) == null) return null;
  return HCLegacy(app: app, it: it);
}
