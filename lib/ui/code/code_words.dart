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
          child: HoolaMd(text, streaming: streaming, selectable: selecting),
        ),
        if (actions)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Row(children: [
              b(Icons.copy_rounded, 'Copy', () async {
                await Clipboard.setData(ClipboardData(text: plain));
                if (context.mounted) codeToast(context, 'Copied');
              }),
              b(Icons.volume_up_outlined, 'Read aloud', () => app.readAloud(plain)),
              b(Icons.ios_share_rounded, 'Share', () => codeShareText(context, plain)),
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
    _carry += dt.inMicroseconds / 1000 / (waiting > 80 ? 17 : 34);
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
