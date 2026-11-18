// v0.864 R4 THE CARDS (docs/HOOLA_APP_REDESIGN_PLAN.md R4): one card shell for the new chat, in the new design.
//
//   HoolaCard       the shell: a small label line (what desk + when), a tile, the title, a status in plain words, the
//                   body, and the buttons docked at the bottom. Surface + hairline + radius 18 from hoola_theme.dart.
//   HCApproval      "Needs your yes" (the Bazar confirm card): what, who, the items, the amount as the hero line,
//                   then Yes / Not now. Money never moves on this tap: a money card opens the existing approval sheet
//                   (deliberate slide + fingerprint when the phone has a key); the server checks again.
//   HCFile          a file Hoola made or brought from her PC: name, size, Open, Share link.
//   HCArtifact      a page (artifact) - v0.902 its own card in hoola_artifact.dart (thumbnail, real step + clock, Stop, Share, Open).
//   HCAny           every other kind with no screen of its own (the v0.555 default card), drawn in the new design.
// Every other kind keeps its old card in its dark frame for now (hoola_chat.dart `_OldCard`): those are the desk cards
// R8 moves. Nothing here acts by itself.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../native.dart';
import '../../state.dart';
import '../any_card.dart' show AnyEventCard;
import '../approve_sheet.dart';
import '../hoola_theme.dart';
import 'hoola_artifact.dart' show HCArtifact;

/// The new-look card for one feed item, or null when the kind still uses its old card.
Widget? hoolaCardFor(BuildContext context, Santosh app, FeedItem it) {
  switch (it.kind) {
    case 'bazar':
      return HCApproval(key: ValueKey('hcb${it.data['id']}${it.data['status']}${it.data['busy']}'), v: it.data, app: app);
    case 'pc_file':
      return HCFile(v: it.data, app: app);
    case 'artifact':
      return HCArtifact(v: it.data, app: app);
    case 'any_card':
      return HCAny(v: it.data, at: it.at);
  }
  return null;
}

/// The status a card shows: a coloured dot and plain words.
class HCStatus {
  const HCStatus(this.words, this.tone);
  final String words;
  final Color tone;
  static HCStatus needsYou(HoolaColors c) => HCStatus('Needs your yes', c.warn);
  static HCStatus working(HoolaColors c, [String w = 'Working']) => HCStatus(w, c.accent);
  static HCStatus done(HoolaColors c, [String w = 'Done']) => HCStatus(w, c.ok);
  static HCStatus failed(HoolaColors c, [String w = 'Did not work']) => HCStatus(w, c.bad);
  static HCStatus quiet(HoolaColors c, String w) => HCStatus(w, c.ink3);
}

/// The one card shell every new-look card uses.
class HoolaCard extends StatelessWidget {
  const HoolaCard({
    super.key,
    required this.icon,
    required this.title,
    this.label = '',
    this.when = '',
    this.status,
    this.tileTone,
    this.children = const [],
    this.actions = const [],
    this.lead = const [],
    this.highlight = false,
    this.whenMono = false,
  });
  final IconData icon;
  final String title;
  /// The small line above: which desk / kind of thing ("Shopping", "File", "Page").
  final String label;
  final String when;
  final HCStatus? status;
  final Color? tileTone;
  final List<Widget> children;
  /// Buttons docked at the bottom on the right, left to right (the main one last).
  final List<Widget> actions;
  /// v0.900 quiet buttons docked at the bottom on the LEFT (Details, Hide steps, Not now).
  final List<Widget> lead;
  /// A card waiting for her answer gets an amber edge and a soft lift.
  final bool highlight;
  /// v0.900 `when` is a clock (tabular figures).
  final bool whenMono;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final tone = tileTone ?? status?.tone ?? c.ink2;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Container(
        decoration: BoxDecoration(
          color: c.surface,
          borderRadius: HoolaRadius.r(HoolaRadius.cardLg),
          border: Border.all(color: highlight ? Color.lerp(c.line, c.warn, .45)! : c.line),
          boxShadow: highlight ? [BoxShadow(color: c.warn.withOpacity(.14), blurRadius: 24, offset: const Offset(0, 8), spreadRadius: -12)] : null,
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              if (label.isNotEmpty || when.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(children: [
                    Expanded(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.label(c).copyWith(color: c.ink3))),
                    if (when.isNotEmpty)
                      Text(when,
                          style: HoolaType.label(c).copyWith(
                              color: c.ink3,
                              fontFamily: whenMono ? HoolaFont.mono : null,
                              fontFeatures: const [FontFeature.tabularFigures()])),
                  ]),
                ),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(color: tone.withOpacity(.12), borderRadius: HoolaRadius.r(HoolaRadius.tile)),
                  child: Icon(icon, size: 20, color: tone),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(title, maxLines: 3, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
                    if (status != null) ...[
                      const SizedBox(height: 4),
                      Row(children: [
                        Container(width: 7, height: 7, decoration: BoxDecoration(color: status!.tone, shape: BoxShape.circle)),
                        const SizedBox(width: 7),
                        Flexible(child: Text(status!.words, style: HoolaType.small(c).copyWith(color: status!.tone, fontWeight: FontWeight.w500))),
                      ]),
                    ],
                  ]),
                ),
              ]),
              for (final w in children) ...[const SizedBox(height: 12), w],
            ]),
          ),
          if (actions.isNotEmpty || lead.isNotEmpty)
            Container(
              padding: const EdgeInsets.fromLTRB(6, 8, 10, 10),
              decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
              child: Row(children: [
                for (var i = 0; i < lead.length; i++) ...[if (i > 0) const SizedBox(width: 4), Flexible(child: lead[i])],
                const Spacer(),
                for (var i = 0; i < actions.length; i++) ...[if (i > 0) const SizedBox(width: 8), actions[i]],
              ]),
            ),
        ]),
      ),
    );
  }
}

/// A fact line: label left, value right, on a hairline.
class HCFact extends StatelessWidget {
  const HCFact(this.label, this.value, {super.key, this.strong = false});
  final String label;
  final String value;
  final bool strong;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(border: Border(top: BorderSide(color: c.line))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // the label keeps its own width (up to 45 %), the value takes the rest and sits on the right edge
        ConstrainedBox(
          constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .45),
          child: Text(label, style: HoolaType.small(c).copyWith(color: c.ink2)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(value, textAlign: TextAlign.right,
              style: (strong ? HoolaType.title(c) : HoolaType.small(c).copyWith(color: c.ink))
                  .copyWith(fontFeatures: const [FontFeature.tabularFigures()])),
        ),
      ]),
    );
  }
}

/// The amount as the hero line of a money card.
class HCAmount extends StatelessWidget {
  const HCAmount(this.amount, {super.key, this.via = ''});
  final String amount;
  final String via;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final shown = amount.replaceFirst(RegExp(r'^\s*(₹|rs\.?|inr)\s*', caseSensitive: false), '');
    return Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
      Padding(padding: const EdgeInsets.only(bottom: 5), child: Text('₹', style: HoolaType.heading(c).copyWith(color: c.ink2))),
      const SizedBox(width: 2),
      Text(shown, style: HoolaType.display(c).copyWith(fontSize: 28, fontFeatures: const [FontFeature.tabularFigures()])),
      const SizedBox(width: 10),
      if (via.isNotEmpty)
        Expanded(child: Text(via, textAlign: TextAlign.right, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c))),
    ]);
  }
}

/// A quiet note band inside a card (safety lines: "UPI PIN only in your UPI app").
class HCNote extends StatelessWidget {
  const HCNote(this.text, {super.key, this.icon = Icons.lock_outline_rounded, this.warn = false});
  final String text;
  final IconData icon;
  final bool warn;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(color: warn ? c.warnSoft : c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, size: 16, color: warn ? c.warn : c.ink2),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: HoolaType.small(c).copyWith(color: c.ink2))),
      ]),
    );
  }
}

/// The two button looks of a card: the main one (filled pill) and the quiet one (text).
Widget hcMain(BuildContext context, String label, VoidCallback? onTap, {IconData? icon, bool busy = false}) {
  final c = HoolaColors.of(context);
  return FilledButton(
    onPressed: busy ? null : onTap,
    style: FilledButton.styleFrom(
      backgroundColor: c.pill,
      foregroundColor: c.onPill,
      minimumSize: const Size(0, 44),
      padding: const EdgeInsets.symmetric(horizontal: 18),
      shape: const StadiumBorder(),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      if (busy)
        SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
      else if (icon != null)
        Icon(icon, size: 18),
      if (busy || icon != null) const SizedBox(width: 8),
      Text(label, style: HoolaType.button(c, color: c.onPill).copyWith(fontSize: 15)),
    ]),
  );
}

Widget hcQuiet(BuildContext context, String label, VoidCallback? onTap) {
  final c = HoolaColors.of(context);
  return TextButton(
    onPressed: onTap,
    style: TextButton.styleFrom(
      foregroundColor: c.ink,
      minimumSize: const Size(0, 44),
      padding: const EdgeInsets.symmetric(horizontal: 14),
      shape: const StadiumBorder(),
    ),
    child: Text(label, style: HoolaType.button(c).copyWith(fontSize: 15, fontWeight: FontWeight.w500)),
  );
}

String _s(Object? o) => o is String ? o.trim() : (o is num ? '$o' : '');

String hcAgo(DateTime? at) {
  if (at == null) return '';
  final s = DateTime.now().toUtc().difference(at.toUtc()).inSeconds;
  if (s < 60) return 'Just now';
  if (s < 3600) return '${s ~/ 60} min ago';
  if (s < 86400) return '${s ~/ 3600} h ago';
  return '${at.day}/${at.month}';
}

String hcSize(num? b) {
  if (b == null || b <= 0) return '';
  if (b < 1024) return '$b B';
  if (b < 1024 * 1024) return '${(b / 1024).toStringAsFixed(0)} KB';
  return '${(b / 1024 / 1024).toStringAsFixed(1)} MB';
}

// ============================================================================================ the cards

/// "Needs your yes": the Bazar confirm card (orders, bookings, sends, payments).
class HCApproval extends StatelessWidget {
  const HCApproval({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final status = _s(v['status']).isEmpty ? 'pending' : _s(v['status']);
    final busy = v['busy'] == true;
    final pending = status == 'pending';
    final amount = _s(v['amount']);
    final money = (v['money'] as bool?) ?? amount.isNotEmpty;
    final items = (v['items'] as List? ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    final result = v['result'] as Map?;
    final message = _s(result?['message']);
    final open = result?['open'] as Map?;
    final payee = _s(v['payee']);
    final st = pending
        ? HCStatus.needsYou(c)
        : (status == 'approved' || status == 'auto')
            ? HCStatus.done(c, money ? 'Approved' : 'Yes given')
            : status == 'rejected'
                ? HCStatus.quiet(c, 'Not done - you said not now')
                : status == 'failed'
                    ? HCStatus.failed(c)
                    : HCStatus.quiet(c, status.replaceAll('_', ' '));
    return HoolaCard(
      icon: money ? Icons.currency_rupee_rounded : Icons.touch_app_outlined,
      label: money ? 'Payment' : 'Your yes',
      title: _s(v['title']).replaceFirst('[DEMO] ', ''),
      status: st,
      highlight: pending,
      children: [
        if (v['demo'] == true) const HCNote('Demo: a test bill, no real money moves.', icon: Icons.science_outlined, warn: true),
        if (payee.isNotEmpty) HCFact(money ? 'To' : 'Where', payee),
        for (final i in items.take(12)) HCFact(_s(i['name']), _s(i['price'])),
        if (amount.isNotEmpty) HCAmount(amount, via: _s(v['pay_method'])),
        if (pending && v['needs_pin'] == true)
          const HCNote('Your UPI PIN goes only into your UPI app. Hoola never asks for it.'),
        if (pending && money)
          const HCNote('Approving opens the approval sheet. Nothing is paid until you slide to approve.'),
        if (pending && v['voice_ok'] == true)
          const HCNote('You can also say "yes, do it" on a call or in the chat.', icon: Icons.graphic_eq_rounded),
        if (message.isNotEmpty) Text(message, style: HoolaType.body(c).copyWith(color: c.ink2)),
      ],
      lead: [if (pending) hcQuiet(context, 'Not now', busy ? null : () => app.decideBazar(_s(v['id']), 'reject'))],
      actions: [
        if (pending) ...[
          hcMain(context, money ? 'Review and approve' : 'Yes, do it', () {
            HapticFeedback.mediumImpact();
            // money: the deliberate slide (+ fingerprint when the phone has a key). Anything else: this card IS the
            // confirm card, so her tap is the yes (the server still refuses a money card without the fingerprint).
            if (money) {
              showApproveSheet(context, app, v);
            } else {
              app.decideBazar(_s(v['id']), 'approve');
            }
          }, icon: Icons.check_rounded, busy: busy),
        ] else if (open != null)
          hcMain(context, _s(open['label']).isEmpty ? 'Open' : _s(open['label']), () async {
            final r = await app.openBazar(Map<String, dynamic>.from(open));
            if (r != 'ok' && context.mounted) ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(r)));
          }, icon: Icons.open_in_new_rounded),
      ],
    );
  }
}

/// A file Hoola made (PDF) or brought from her PC.
class HCFile extends StatelessWidget {
  const HCFile({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  bool get _made => v['source'] == 'bazar';

  Future<String> _url() async {
    final docId = v['doc_id'] as String?;
    if (_made && docId != null && app.api != null) {
      try {
        return await app.api!.bazarFileUrl(docId);
      } catch (_) {}
    }
    return app.api?.absolute(_s(v['url'])) ?? '';
  }

  @override
  Widget build(BuildContext context) {
    final name = _s(v['name']).isEmpty ? 'File' : _s(v['name']);
    final size = hcSize(v['size'] as num?);
    final ext = name.contains('.') ? name.split('.').last.toUpperCase() : '';
    return HoolaCard(
      icon: ext == 'PDF' ? Icons.picture_as_pdf_outlined : (_made ? Icons.description_outlined : Icons.computer_outlined),
      label: _made ? 'Made by ${app.aName}' : 'From your PC',
      title: name,
      status: HCStatus.quiet(HoolaColors.of(context), [if (ext.isNotEmpty) ext, if (size.isNotEmpty) size, 'link works for 24 h'].join(' · ')),
      lead: [
        hcQuiet(context, 'Share link', () async {
          final url = await _url();
          await Native.openExternal(url: 'https://wa.me/?text=${Uri.encodeComponent('$name: $url')}');
        }),
      ],
      actions: [
        hcMain(context, 'Open', () async => Native.openExternal(url: await _url()), icon: Icons.open_in_new_rounded),
      ],
    );
  }
}

/// A page (artifact) Hoola made: building, ready (Open) or not made (with the reason).
/// The default card for every kind that has no screen of its own, in the new design (same reading of the payload as
/// the v0.555 AnyEventCard: the title, one sentence, up to 3 facts, progress, the amount, an Open link).
class HCAny extends StatelessWidget {
  const HCAny({super.key, required this.v, this.at, this.label, this.lead = const [], this.main});
  final Map<String, dynamic> v;
  final DateTime? at;
  /// v0.900 the desk name (HCLegacy passes a friendly one); null = from the kind.
  final String? label;
  /// v0.900 quiet buttons on the left (Details) and the main button (Review) - HCLegacy's way to the full card.
  final List<Widget> lead;
  final Widget? main;

  static const _titleKeys = ['title', 'name', 'label', 'what', 'subject', 'brief', 'task', 'number'];
  static const _lineKeys = ['say', 'summary', 'text', 'reason', 'message', 'detail', 'now', 'stage_label'];
  static final _skip = RegExp(
      r'(^id$|_id$|^key$|^tenant|token|secret|^sig|hash|nonce|^at$|_at$|preview|thumb|^b64|^data$|^raw|^conv|^call$|^url$|^link$|^open_url$|^status$|^state$|^pct$|^progress$|^amount|^inr$|^push$|^kind$|^step$|^total$|^done$|^steps_total$|^error$|^_)',
      caseSensitive: false);

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final kind = _s(v['_kind']);
    final state = AnyEventCard.stateOf(v);
    final money = AnyEventCard.isMoney(kind, v);
    final st = switch (state) {
      'ask' => HCStatus.needsYou(c),
      'work' => HCStatus.working(c),
      'failed' => HCStatus.failed(c, 'Stopped, a problem came up'),
      'stopped' => HCStatus.quiet(c, 'Closed'),
      'other' => HCStatus.quiet(c, _s(v['status'] ?? v['state']).replaceAll('_', ' ')),
      _ => HCStatus.done(c, 'Ready'),
    };
    final tk = _titleKeys.firstWhere((k) => _s(v[k]).isNotEmpty, orElse: () => '');
    final order = [if (state == 'failed') ...['reason', 'error'], ..._lineKeys, 'error'];
    final lk = order.firstWhere((k) => k != tk && _s(v[k]).isNotEmpty, orElse: () => '');
    final desk = AnyEventCard.deskOf(kind.isEmpty ? 'card' : kind);
    var line = lk.isEmpty ? '' : _s(v[lk]);
    if (line.length > 600) line = '${line.substring(0, 600)}…';
    final amt = money ? AnyEventCard.amountOf(v) : '';
    final link = [_s(v['url']), _s(v['link']), _s(v['open_url'])]
        .firstWhere((u) => u.startsWith('https://') || u.startsWith('http://'), orElse: () => '');
    final facts = <MapEntry<String, String>>[];
    for (final e in v.entries) {
      if (facts.length >= 3) break;
      if (_skip.hasMatch(e.key) || e.key == tk || e.key == lk || e.key == 'pay_method' || e.key == 'via') continue;
      final s = _s(e.value);
      if (s.isEmpty || s.length > 48) continue;
      final label = e.key.replaceAll('_', ' ');
      facts.add(MapEntry('${label[0].toUpperCase()}${label.substring(1)}', s));
    }
    double? pct;
    final pRaw = v['pct'] ?? v['progress'];
    if (pRaw is num) pct = pRaw.toDouble();
    final done = v['step'] ?? v['done'], total = v['total'] ?? v['steps_total'];
    if (done is num && total is num && total > 0) pct = done / total * 100;
    if (pct != null) pct = pct.clamp(0, 100).toDouble();
    return HoolaCard(
      icon: switch (state) {
        'ask' => money ? Icons.currency_rupee_rounded : Icons.help_outline_rounded,
        'work' => Icons.autorenew_rounded,
        'failed' => Icons.error_outline_rounded,
        'stopped' => Icons.stop_circle_outlined,
        _ => Icons.check_rounded,
      },
      label: label ?? desk,
      when: hcAgo(at),
      title: tk.isEmpty ? (label ?? desk) : _s(v[tk]),
      status: st,
      highlight: state == 'ask',
      children: [
        if (v['told_on_call'] == true) Text('Told you on the call', style: HoolaType.small(c).copyWith(color: c.ok)),
        if (line.isNotEmpty) Text(line, style: HoolaType.body(c).copyWith(color: c.ink2)),
        if (pct != null)
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            ClipRRect(
              borderRadius: HoolaRadius.r(4),
              child: LinearProgressIndicator(value: pct / 100, minHeight: 4, color: st.tone, backgroundColor: c.sunk),
            ),
            const SizedBox(height: 6),
            Text(done is num && total is num ? '$done of $total' : '${pct.round()}%', style: HoolaType.small(c)),
          ]),
        if (amt.isNotEmpty) HCAmount(amt, via: _s(v['pay_method'] ?? v['via'])),
        if (facts.isNotEmpty) Column(children: [for (final f in facts) HCFact(f.key, f.value)]),
        if (money && state == 'ask') const HCNote('Money is approved only in the app with your fingerprint, never by voice.'),
      ],
      lead: lead,
      actions: [
        if (main != null)
          main!
        else if (link.isNotEmpty)
          hcMain(context, 'Open', () => launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication).catchError((_) => false),
              icon: Icons.open_in_new_rounded),
      ],
    );
  }
}
