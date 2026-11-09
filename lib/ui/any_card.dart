import 'dart:ui' show FontFeature;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'glass.dart';

/// v0.555 HOOLA CARD - the premium default card (design: claude.ai/artifact/NgbT6WLDj63Jhh7MbysuGD).
/// One anatomy for every card kind that has no screen of its own: an eyebrow (desk + time), a tile, the title, a
/// status signal (dot + plain words), one sentence, the amount as the hero, receipt facts on hairlines, step
/// segments, a secure band for money, and a docked action bar. The same rules live in the web console's hcard.js.
/// Nothing here acts by itself: a card that needs her tap to approve always has its own screen.
class AnyEventCard extends StatelessWidget {
  const AnyEventCard({super.key, required this.v, this.at});
  final Map<String, dynamic> v;
  final DateTime? at;

  static const _titleKeys = ['title', 'name', 'label', 'what', 'subject', 'brief', 'task', 'number'];
  static const _lineKeys = ['say', 'summary', 'text', 'reason', 'message', 'detail', 'now', 'stage_label'];
  static final _skip = RegExp(
      r'(^id$|_id$|^key$|^tenant|token|secret|^sig|hash|nonce|^at$|_at$|preview|thumb|^b64|^data$|^raw|^conv|^call$|^url$|^link$|^open_url$|^status$|^state$|^pct$|^progress$|^amount|^inr$|^push$|^kind$|^step$|^total$|^done$|^steps_total$|^error$|^_)',
      caseSensitive: false);
  static const _working = {'queued', 'running', 'working', 'writing', 'building', 'fixing', 'designing', 'checking', 'watching', 'planning',
    'rendering', 'generating', 'uploading', 'compiling', 'started', 'in_progress', 'processing', 'assembling'};
  static const _asking = {'pending', 'waiting', 'needs_tap', 'waiting_payment', 'waiting_sign', 'asking', 'approval', 'needs_confirm', 'looks', 'planned'};
  static const _done = {'done', 'completed', 'complete', 'approved', 'live', 'placed', 'finished', 'delivered', 'success', 'ok', 'ready', 'zip',
    'published', 'signed', 'final', 'sent'};

  static const _surf1 = Color(0xFF1C1838);
  static const _surf2 = Color(0xFF16132C);
  static const _hair = Color(0x13FFFFFF);
  static const _vio = Color(0xFFA28DFF);

  static String _str(Object? o) => o is String ? o.trim() : (o is num) ? '$o' : '';

  /// ask / work / done / failed / stopped / other
  static String stateOf(Map<String, dynamic> p) {
    final st = _str(p['status'] ?? p['state']).toLowerCase();
    if (st == 'failed' || st == 'error') return 'failed';
    if (st == 'stopped' || st == 'cancelled' || st == 'canceled' || st == 'rejected') return 'stopped';
    if (_asking.contains(st)) return 'ask';
    if (_working.contains(st)) return 'work';
    if (_done.contains(st) || st.isEmpty) return 'done';
    return 'other';
  }

  static bool isMoney(String kind, Map<String, dynamic> p) {
    if (RegExp(r'_pay|upi|bill|spend|khata|mandate').hasMatch(kind)) return true;
    if (_str(p['amount']).isNotEmpty || _str(p['amount_inr']).isNotEmpty || _str(p['amount_paise']).isNotEmpty || _str(p['inr']).isNotEmpty) {
      return true;
    }
    return RegExp(r'upi|card|wallet|pay|bank|cash', caseSensitive: false).hasMatch(_str(p['pay_method']));
  }

  /// "1,24,000" style (Indian grouping) or the text as given, without a leading ₹ / Rs.
  static String amountOf(Map<String, dynamic> p) {
    Object? raw = p['amount_inr'] ?? p['inr'] ?? p['amount'];
    if (raw == null && p['amount_paise'] is num) raw = (p['amount_paise'] as num) / 100;
    final s = _str(raw);
    if (s.isEmpty) return '';
    final n = num.tryParse(s.replaceAll(',', ''));
    if (n == null) return s.replaceFirst(RegExp(r'^\s*(₹|rs\.?|inr)\s*', caseSensitive: false), '');
    final whole = n.truncate();
    final frac = n - whole;
    var digits = whole.abs().toString();
    var out = '';
    if (digits.length > 3) {
      out = ',${digits.substring(digits.length - 3)}';
      digits = digits.substring(0, digits.length - 3);
      while (digits.length > 2) {
        out = ',${digits.substring(digits.length - 2)}$out';
        digits = digits.substring(0, digits.length - 2);
      }
      out = '$digits$out';
    } else {
      out = digits;
    }
    if (frac > 0.0001) out = '$out.${(frac * 100).round().toString().padLeft(2, '0')}';
    return whole < 0 ? '-$out' : out;
  }

  static String deskOf(String kind) => kind.replaceAll('_', ' ').split(' ').where((w) => w.isNotEmpty)
      .map((w) => '${w[0].toUpperCase()}${w.substring(1)}').join(' ');

  static String _ago(DateTime? at) {
    if (at == null) return '';
    final s = DateTime.now().toUtc().difference(at.toUtc()).inSeconds;
    if (s < 60) return 'just now';
    if (s < 3600) return '${s ~/ 60} min ago';
    if (s < 86400) return '${s ~/ 3600} hours ago';
    return '${at.day}/${at.month}';
  }

  @override
  Widget build(BuildContext context) {
    final kind = _str(v['_kind']);
    final st = stateOf(v);
    final money = isMoney(kind, v);
    final tone = money && st == 'ask'
        ? C.accent
        : switch (st) { 'ask' => _vio, 'work' => C.teal, 'failed' => C.bad, 'stopped' => C.faint, 'other' => _vio, _ => C.ok };
    final words = switch (st) {
      'ask' => 'Needs your OK',
      'work' => 'Running',
      'failed' => 'Stopped, a problem came up',
      'stopped' => 'Closed',
      'other' => _str(v['status'] ?? v['state']).replaceAll('_', ' '),
      _ => 'Ready',
    };
    final icon = money && st == 'ask'
        ? Icons.bolt_rounded
        : switch (st) {
            'ask' => Icons.help_outline_rounded,
            'work' => Icons.autorenew_rounded,
            'failed' => Icons.warning_amber_rounded,
            'stopped' => Icons.stop_rounded,
            _ => Icons.check_rounded,
          };
    final tk = _titleKeys.firstWhere((k) => _str(v[k]).isNotEmpty, orElse: () => '');
    final lineOrder = [if (st == 'failed') ...['reason', 'error'], ..._lineKeys, 'error'];   // a problem is the sentence, never a fact
    final lk = lineOrder.firstWhere((k) => k != tk && _str(v[k]).isNotEmpty, orElse: () => '');
    final desk = deskOf(kind.isEmpty ? 'card' : kind);
    final title = tk.isEmpty ? desk : _str(v[tk]);
    var line = lk.isEmpty ? '' : _str(v[lk]);
    if (line.length > 600) line = '${line.substring(0, 600)}…';
    final amt = money ? amountOf(v) : '';
    final via = _str(v['pay_method'] ?? v['via']);
    final link = [_str(v['url']), _str(v['link']), _str(v['open_url'])]
        .firstWhere((u) => u.startsWith('https://') || u.startsWith('http://'), orElse: () => '');
    final facts = <MapEntry<String, String>>[];
    for (final e in v.entries) {
      if (facts.length >= 3) break;
      if (_skip.hasMatch(e.key) || e.key == tk || e.key == lk || e.key == 'pay_method' || e.key == 'via') continue;
      final s = _str(e.value);
      if (s.isEmpty || s.length > 48) continue;
      final label = e.key.replaceAll('_', ' ');
      facts.add(MapEntry('${label[0].toUpperCase()}${label.substring(1)}', s));
    }
    // progress: pct, or step / total
    double? pct;
    final pRaw = v['pct'] ?? v['progress'];
    if (pRaw is num) pct = pRaw.toDouble();
    final done = v['step'] ?? v['done'], total = v['total'] ?? v['steps_total'];
    if (done is num && total is num && total > 0) pct = done / total * 100;
    if (pct != null && pct < 0) pct = null;
    if (pct != null && pct > 100) pct = 100;
    final when = _ago(at);
    final told = v['told_on_call'] == true;

    final eyebrow = Row(children: [
      Expanded(
        child: Text(desk.toUpperCase(), maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600, letterSpacing: 1.2, color: C.faint)),
      ),
      if (told) ...[
        const Icon(Icons.check_rounded, size: 12, color: C.ok),
        const SizedBox(width: 3),
        const Text('Told on the call', style: TextStyle(fontSize: 11, color: C.ok, fontWeight: FontWeight.w500)),
        const SizedBox(width: 8),
      ],
      if (when.isNotEmpty) Text(when, style: const TextStyle(fontSize: 11, color: C.faint, fontWeight: FontWeight.w500)),
    ]);

    final head = Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        width: 42, height: 42,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: tone.withOpacity(.14),
          border: Border.all(color: tone.withOpacity(.22)),
        ),
        child: Icon(icon, size: 20, color: tone),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: display(16, w: FontWeight.w600).copyWith(height: 1.28)),
          const SizedBox(height: 5),
          Row(children: [
            Container(
              width: 7, height: 7,
              decoration: BoxDecoration(shape: BoxShape.circle, color: tone,
                  boxShadow: [BoxShadow(color: tone.withOpacity(.35), blurRadius: 0, spreadRadius: 3)]),
            ),
            const SizedBox(width: 8),
            Flexible(child: Text(words, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: tone))),
          ]),
        ]),
      ),
    ]);

    Widget? steps;
    if (pct != null) {
      final on = (pct / 100 * 6 + 1e-9).floor();
      steps = Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          for (var i = 1; i <= 6; i++) ...[
            Expanded(
              child: Container(
                height: 4,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(2),
                  color: i <= on ? tone : (i == on + 1 && pct < 100 ? tone.withOpacity(.45) : const Color(0x17FFFFFF)),
                ),
              ),
            ),
            if (i < 6) const SizedBox(width: 4),
          ],
        ]),
        const SizedBox(height: 6),
        Text(done is num && total is num ? '$done / $total' : '${pct.round()}%',
            style: const TextStyle(fontSize: 12, color: C.ink, fontWeight: FontWeight.w500)),
      ]);
    }

    final body = <Widget>[
      eyebrow,
      head,
      if (line.isNotEmpty) Text(line, style: const TextStyle(fontSize: 13.5, height: 1.5, color: C.muted)),
      if (steps != null) steps,
      if (amt.isNotEmpty)
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text('₹', style: display(16, w: FontWeight.w500, color: C.muted)),
          ),
          const SizedBox(width: 2),
          Text(amt, style: display(32, w: FontWeight.w600)),
          const Spacer(),
          if (via.isNotEmpty) Text(via, style: const TextStyle(fontSize: 12, color: C.faint)),
        ]),
      if (facts.isNotEmpty)
        Column(children: [
          for (final f in facts)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 7),
              decoration: const BoxDecoration(border: Border(top: BorderSide(color: _hair))),
              child: Row(children: [
                Text(f.key, style: const TextStyle(fontSize: 13, color: C.faint)),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(f.value, textAlign: TextAlign.right,
                      style: const TextStyle(fontSize: 13, color: C.ink, fontFeatures: [FontFeature.tabularFigures()])),
                ),
              ]),
            ),
        ]),
      if (money && st == 'ask')
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: C.accent.withOpacity(.07),
            border: Border.all(color: C.accent.withOpacity(.16)),
          ),
          child: const Row(children: [
            Icon(Icons.lock_outline_rounded, size: 15, color: C.accent),
            SizedBox(width: 9),
            Expanded(child: Text('Approve with fingerprint. This cannot be done by voice on a call.', style: TextStyle(fontSize: 12, color: C.muted))),
          ]),
        ),
    ];

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: const LinearGradient(colors: [_surf1, _surf2], begin: Alignment.topCenter, end: Alignment.bottomCenter),
          border: Border.all(color: _hair),
          boxShadow: const [BoxShadow(color: Color(0x99000000), blurRadius: 40, offset: Offset(0, 20), spreadRadius: -28)],
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(15, 14, 15, 13),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (var i = 0; i < body.length; i++) ...[if (i > 0) const SizedBox(height: 11), body[i]],
            ]),
          ),
          if (link.isNotEmpty)
            Container(
              padding: const EdgeInsets.fromLTRB(15, 10, 12, 12),
              decoration: const BoxDecoration(
                color: Color(0x24000000),
                border: Border(top: BorderSide(color: _hair)),
              ),
              child: Row(children: [
                const Spacer(),
                Press(
                  onTap: () => launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication).catchError((_) => false),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      gradient: const LinearGradient(colors: [Color(0xFFFFC07A), Color(0xFFFFA94A)],
                          begin: Alignment.topCenter, end: Alignment.bottomCenter),
                      boxShadow: const [BoxShadow(color: Color(0x66FFA046), blurRadius: 16, offset: Offset(0, 6), spreadRadius: -8)],
                    ),
                    child: const Text('Open', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: C.onAccent)),
                  ),
                ),
              ]),
            ),
        ]),
      ),
    );
  }
}
