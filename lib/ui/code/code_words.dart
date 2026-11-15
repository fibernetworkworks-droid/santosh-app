// v0.928 HOOLA CODE CHAT LIKE HOOLA CHAT (owner: "Make all chat feature same as hoola chat... App... Everything"):
// Hoola Code's words now behave like a Hoola chat reply - the same renderer (headings, lists, tables, code blocks with
// Copy), Copy · Read aloud · Share under the newest reply, and the same long-press sheet on every message (Copy,
// Quote in my reply, Edit and send again for hers, Read aloud for Hoola's, Select text).
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import '../../native.dart';
import '../../state.dart';
import '../chat/hoola_md.dart';
import '../hoola_theme.dart';
import '../md_text.dart' show mdPlain;
import 'code_kit.dart';

/// Shares a reply as a text file (the same way the Hoola chat does); no share sheet = copied.
Future<void> codeShareText(BuildContext context, String text) async {
  try {
    final dir = await getTemporaryDirectory();
    final f = File('${dir.path}/hoola-code-reply.txt');
    await f.writeAsString(text);
    await Native.shareFile(f.path, mime: 'text/plain', title: 'Share the reply');
  } catch (_) {
    await Clipboard.setData(ClipboardData(text: text));
    if (context.mounted) codeToast(context, 'Copied - paste it where you want to share');
  }
}

/// The long-press sheet on a message: Copy, Quote in my reply, Edit and send again (hers), Read aloud (Hoola's),
/// Select text.
void codeMessageMenu(BuildContext context, Santosh app, String text,
    {required bool mine, VoidCallback? onQuote, VoidCallback? onEdit, VoidCallback? onSelect}) {
  final plain = mine ? text : mdPlain(text);
  if (plain.trim().isEmpty) return;
  HapticFeedback.mediumImpact();
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (ctx) {
      final c = HoolaColors.of(ctx);
      Widget row(IconData icon, String label, VoidCallback onTap, {String? sub}) => ListTile(
            leading: Icon(icon, color: c.ink2),
            title: Text(label),
            subtitle: sub == null ? null : Text(sub),
            onTap: () {
              Navigator.pop(ctx);
              onTap();
            },
          );
      return SafeArea(
        top: false,
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
            child: Text(plain, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
          ),
          row(Icons.copy_rounded, 'Copy', () async {
            await Clipboard.setData(ClipboardData(text: plain));
            if (context.mounted) codeToast(context, 'Copied');
          }),
          if (onQuote != null) row(Icons.format_quote_rounded, 'Quote in my reply', onQuote),
          if (mine && onEdit != null) row(Icons.edit_outlined, 'Edit and send again', onEdit, sub: 'Your words go back in the box to change'),
          if (!mine) row(Icons.volume_up_outlined, 'Read aloud', () => app.readAloud(plain)),
          if (!mine) row(Icons.ios_share_rounded, 'Share', () => codeShareText(context, plain)),
          if (onSelect != null) row(Icons.text_fields_rounded, 'Select text', onSelect),
          const SizedBox(height: 8),
        ]),
      );
    },
  );
}

/// Hoola's words in a session: the Hoola chat's renderer, the long-press sheet, and (on the newest reply) the action row.
class CodeReply extends StatelessWidget {
  const CodeReply({super.key, required this.app, required this.text, this.actions = false, this.selecting = false,
      this.onQuote, this.onSelect, this.streaming = false});
  final Santosh app;
  final String text;
  final bool actions;
  final bool streaming;               // v0.935 still landing: the newest words drawn lighter
  final bool selecting;
  final void Function(String text)? onQuote;
  final VoidCallback? onSelect;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final plain = mdPlain(text);
    Widget b(IconData icon, String label, VoidCallback onTap) => Semantics(
          button: true,
          label: label,
          excludeSemantics: true,
          child: InkResponse(
            onTap: () {
              HapticFeedback.selectionClick();
              onTap();
            },
            radius: 20,
            child: SizedBox(width: 38, height: 38, child: Icon(icon, size: 18, color: c.ink3)),
          ),
        );
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GestureDetector(
          behavior: HitTestBehavior.opaque,
          onLongPress: selecting
              ? null
              : () => codeMessageMenu(context, app, text,
                  mine: false, onQuote: onQuote == null ? null : () => onQuote!(plain), onSelect: onSelect),
          child: HoolaMd(text, streaming: streaming, selectable: selecting, sans: true, fade: true),
        ),
        if (actions)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Row(children: [
              b(Icons.copy_rounded, 'Copy', () async {
                await Clipboard.setData(ClipboardData(text: plain));
                if (context.mounted) codeToast(context, 'Copied');
              }),
              b(Icons.play_arrow_outlined, 'Read aloud', () => app.readAloud(plain)),
            ]),
          ),
      ]),
    );
  }
}

/// Puts quoted lines in front of what she is typing (the Hoola chat's "Quote in my reply").
void codeQuoteInto(TextEditingController box, FocusNode focus, String text) {
  final q = text.trim().split('\n').take(4).map((l) => '> $l').join('\n');
  box.text = '$q\n\n${box.text}';
  box.selection = TextSelection.collapsed(offset: box.text.length);
  focus.requestFocus();
}

/// "Newest" - the round arrow that takes her back to the end of the session.
class CodeNewestButton extends StatelessWidget {
  const CodeNewestButton({super.key, required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: 'Go to the newest',
      excludeSemantics: true,
      child: Material(
        color: c.surface,
        shape: CircleBorder(side: BorderSide(color: c.line)),
        elevation: 2,
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onTap,
          child: SizedBox(width: 40, height: 40, child: Icon(Icons.arrow_downward_rounded, size: 20, color: c.ink)),
        ),
      ),
    );
  }
}

/// v0.935 a new message of Hoola's landing word by word at the Hoola chat's reading speed (34 ms a word, twice as fast
/// when more than 80 words wait), the newest words lighter. [text] may still grow (Hoola is writing it: [done] false);
/// [from] = words already shown, so a message that moved from "being written" to "said" carries on where it was.
/// Reduce motion = all of it at once.
class CodeLanding extends StatefulWidget {
  const CodeLanding({super.key, required this.text, required this.from, required this.done, required this.onLanded, required this.builder});
  final String text;
  final int from;
  final bool done;
  final void Function(int words) onLanded;
  final Widget Function(String shown, bool streaming) builder;

  @override
  State<CodeLanding> createState() => _CodeLandingState();
}

class _CodeLandingState extends State<CodeLanding> with SingleTickerProviderStateMixin {
  late final Ticker _ticker = createTicker(_onTick);
  late int _n = widget.from;
  Duration _last = Duration.zero;
  double _carry = 0;
  bool _reduced = false;

  List<String> get _words => widget.text.split(RegExp(r'(?<=\s)'));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduced = HoolaMotion.reduced(context);
    _go();
  }

  @override
  void didUpdateWidget(CodeLanding old) {
    super.didUpdateWidget(old);
    if (widget.from > _n) _n = widget.from;
    _go();
  }

  void _go() {
    final total = _words.length;
    if (_reduced) {
      if (_n != total) {
        _n = total;
        widget.onLanded(_n);
      }
      return;
    }
    if (_n < total && !_ticker.isActive) {
      _last = Duration.zero;
      _carry = 0;
      _ticker.start();
    }
  }

  void _onTick(Duration elapsed) {
    final dt = elapsed - _last;
    _last = elapsed;
    final total = _words.length;
    final waiting = total - _n;
    if (waiting <= 0) {
      _ticker.stop();
      return;
    }
    _carry += dt.inMicroseconds / 1000 / (waiting > 160 ? 26 : 52);   // v0.937 ~19 words a second, each fading in
    final step = _carry.floor();
    if (step <= 0) return;
    _carry -= step;
    setState(() => _n = (_n + step).clamp(0, total));
    widget.onLanded(_n);
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final w = _words;
    final n = _n.clamp(0, w.length);
    final shown = w.take(n).join();
    if (shown.trim().isEmpty) return const SizedBox.shrink();
    return widget.builder(shown, !widget.done || n < w.length);
  }
}

/// v0.935 the working row's words with a soft light passing across them (still under reduce motion).
class CodeShimmer extends StatefulWidget {
  const CodeShimmer(this.text, {super.key, required this.style});
  final String text;
  final TextStyle style;

  @override
  State<CodeShimmer> createState() => _CodeShimmerState();
}

class _CodeShimmerState extends State<CodeShimmer> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1800));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (HoolaMotion.reduced(context)) {
      _c.stop();
    } else if (!_c.isAnimating) {
      _c.repeat();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final words = AnimatedSwitcher(
      duration: HoolaMotion.of(context, HoolaMotion.fade),
      layoutBuilder: (cur, prev) => Stack(alignment: Alignment.centerLeft, children: [...prev, if (cur != null) cur]),
      child: Text(widget.text, key: ValueKey(widget.text), maxLines: 1, overflow: TextOverflow.ellipsis, style: widget.style),
    );
    if (HoolaMotion.reduced(context)) return words;
    return AnimatedBuilder(
      animation: _c,
      child: words,
      builder: (context, child) => ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (r) => LinearGradient(
          colors: [c.ink3, c.ink3, c.ink, c.ink3, c.ink3],
          stops: const [0, .38, .5, .62, 1],
          transform: _Slide(_c.value),
        ).createShader(r),
        child: child,
      ),
    );
  }
}

class _Slide extends GradientTransform {
  const _Slide(this.v);
  final double v;
  @override
  Matrix4 transform(Rect bounds, {TextDirection? textDirection}) => Matrix4.translationValues(bounds.width * (1.2 - 2.4 * v), 0, 0);
}

/// v0.936 the steps inside one line of the work, Claude Code's sheet: a close button and the line as its title, then one
/// row per step - an icon, what it did in bold ("Ran", "Read", "Edited") and in plain grey words what for - joined by a
/// thin line. A command's text and output, or an edit's lines, only open under the row's arrow.
class CodeStepsSheet extends StatefulWidget {
  const CodeStepsSheet({super.key, required this.title, required this.steps, required this.scroll, required this.fallback});
  final String title;
  final List<Map<String, dynamic>> steps;
  final ScrollController scroll;
  final Widget? Function(Map<String, dynamic> step) fallback;

  @override
  State<CodeStepsSheet> createState() => _CodeStepsSheetState();
}

class _CodeStepsSheetState extends State<CodeStepsSheet> {
  final Set<int> _open = {};

  static String _s(Object? v) => v == null ? '' : '$v';

  /// (icon, verb, words, can open)
  (IconData, String, String, bool) _row(Map<String, dynamic> s) {
    final k = _s(s['k']);
    final path = _s(s['path']).split('/').last;
    switch (k) {
      case 'bash':
        return (Icons.terminal_rounded, 'Ran', _s(s['desc']).isNotEmpty ? _s(s['desc']) : 'a command', true);
      case 'read':
        return (Icons.description_outlined, 'Read', path, false);
      case 'list':
        return (Icons.folder_open_rounded, 'Looked in', _s(s['path']).isEmpty ? 'the repo' : _s(s['path']), false);
      case 'search' || 'grep' || 'usages':
        return (Icons.search_rounded, 'Searched', _s(s['q']).isNotEmpty ? 'for ${_s(s['q'])}' : 'the code', false);
      case 'edit':
        return (Icons.edit_outlined, 'Edited', path, (s['diff'] as List?)?.isNotEmpty ?? false);
      case 'new':
        return (Icons.note_add_outlined, 'Wrote', path, (s['diff'] as List?)?.isNotEmpty ?? false);
      case 'check':
        return (Icons.fact_check_outlined, 'Ran', s['ok'] == true ? 'your tests · passed' : 'your tests · failed', false);
      case 'agent':
        return (Icons.groups_outlined, 'Asked', _s(s['name']).isNotEmpty ? 'a helper: ${_s(s['name'])}' : 'a helper', false);
      default:
        return (Icons.circle_outlined, '', '', false);
    }
  }

  Widget _detail(HoolaColors c, Map<String, dynamic> s) {
    final mono = codeMono(c, size: 12.5, color: c.ink2);
    final box = BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.line));
    if (_s(s['k']) == 'bash') {
      final rc = s['rc'];
      final ok = rc == 0 && s['timed_out'] != true;
      final tail = [for (final x in (s['tail'] as List?) ?? const []) _s(x)];
      final secs = s['seconds'];
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: box,
          child: Text.rich(TextSpan(children: [
            TextSpan(text: '\$ ${_s(s['cmd'])}', style: codeMono(c, size: 12.5, color: c.ink)),
            if (tail.isNotEmpty) TextSpan(text: '\n${tail.take(24).join('\n')}', style: mono),
          ])),
        ),
        const SizedBox(height: 6),
        Text(
            [
              if (s['timed_out'] == true) 'Timed out' else if (rc != null) (ok ? 'Passed' : 'Failed'),
              if (rc != null) 'exit $rc',
              if (secs != null) '${secs is num ? secs.round() : secs}s',
            ].join(' · '),
            style: codeSans(c, size: 13, color: s['timed_out'] == true || (rc != null && !ok) ? c.bad : c.ink3)),
      ]);
    }
    final lines = [for (final x in (s['diff'] as List?) ?? const []) _s(x)];
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: box,
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        for (final l in lines)
          Container(
            color: l.startsWith('+') ? c.okSoft : (l.startsWith('-') ? c.badSoft : null),
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(l, style: codeMono(c, size: 12.5, color: l.startsWith('+') ? c.ok : (l.startsWith('-') ? c.bad : c.ink2))),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final kids = <Widget>[];
    for (var i = 0; i < widget.steps.length; i++) {
      final s = widget.steps[i];
      final (icon, verb, words, can) = _row(s);
      final last = i == widget.steps.length - 1;
      final open = _open.contains(i);
      final Widget head = verb.isEmpty
          ? Container(constraints: const BoxConstraints(minHeight: 52), alignment: Alignment.centerLeft, child: widget.fallback(s))
          : Semantics(
              button: can,
              label: '$verb $words${can ? (open ? '. Hide the details' : '. Show the details') : ''}',
              excludeSemantics: true,
              child: InkWell(
                onTap: can ? () => setState(() => open ? _open.remove(i) : _open.add(i)) : null,
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  constraints: const BoxConstraints(minHeight: 52),
                  child: Row(children: [
                    Expanded(
                      child: Text.rich(
                        TextSpan(children: [
                          TextSpan(text: verb, style: codeSans(c, size: 16, weight: FontWeight.w500)),
                          TextSpan(text: '  $words', style: codeSans(c, size: 16, color: c.ink3)),
                        ]),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (_s(s['k']) == 'edit' || _s(s['k']) == 'new') ...[
                      const SizedBox(width: 6),
                      CodeStat((s['added'] as num?)?.toInt() ?? 0, (s['removed'] as num?)?.toInt() ?? 0, size: 12),
                    ],
                    if (can) ...[
                      const SizedBox(width: 4),
                      Icon(open ? Icons.keyboard_arrow_down_rounded : Icons.chevron_right_rounded, size: 20, color: c.ink3),
                    ],
                  ]),
                ),
              ),
            );
      kids.add(IntrinsicHeight(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          SizedBox(
            width: 30,
            child: Column(children: [
              SizedBox(
                  height: 52,
                  child: Center(
                      child: verb.isEmpty
                          ? Container(width: 5, height: 5, decoration: BoxDecoration(color: c.lineStrong, shape: BoxShape.circle))
                          : Icon(icon, size: 21, color: c.ink2))),
              if (!last) Expanded(child: Center(child: Container(width: 1, color: c.lineStrong))),
            ]),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              head,
              if (open) Padding(padding: const EdgeInsets.only(bottom: 12), child: _detail(c, s)),
            ]),
          ),
        ]),
      ));
    }
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(8, 0, 8, 4),
        child: Row(children: [
          Semantics(
            button: true,
            label: 'Close',
            excludeSemantics: true,
            child: InkResponse(
              onTap: () => Navigator.of(context).maybePop(),
              radius: 24,
              child: SizedBox(width: 48, height: 48, child: Icon(Icons.close_rounded, size: 24, color: c.ink)),
            ),
          ),
          Expanded(
            child: Text(widget.title, textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: codeSans(c, size: 18, weight: FontWeight.w600)),
          ),
          const SizedBox(width: 48),
        ]),
      ),
      Expanded(
        child: ListView(controller: widget.scroll, padding: const EdgeInsets.fromLTRB(20, 8, 20, 28), children: kids),
      ),
    ]);
  }
}
