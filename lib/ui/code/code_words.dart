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
/// v1.0 [onRewrite] = "Edit": her message changed in place (Hoola carries on from the new words); [rewriteOff] greys it
/// out while Hoola is working.
void codeMessageMenu(BuildContext context, Santosh app, String text,
    {required bool mine, VoidCallback? onQuote, VoidCallback? onEdit, VoidCallback? onSelect, VoidCallback? onRewrite,
    bool rewriteOff = false}) {
  final plain = mine ? text : mdPlain(text);
  if (plain.trim().isEmpty) return;
  HapticFeedback.mediumImpact();
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (ctx) {
      final c = HoolaColors.of(ctx);
      Widget row(IconData icon, String label, VoidCallback onTap, {String? sub, bool enabled = true}) => ListTile(
            enabled: enabled,
            leading: Icon(icon, color: enabled ? c.ink2 : c.ink3),
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
          if (mine && onRewrite != null)
            row(Icons.edit_rounded, 'Edit', onRewrite,
                sub: rewriteOff ? 'Wait until Hoola finishes this step' : 'Change this message; Hoola carries on from your new words',
                enabled: !rewriteOff),
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
      this.onQuote, this.onSelect, this.streaming = false, this.tail});
  final Santosh app;
  final List<double>? tail;           // v0.960 the ink of the newest words, worked out every frame by CodeLanding
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
          child: HoolaMd(text, streaming: streaming, selectable: selecting, fade: true, tail: tail),   // v0.999 the reply font, same as the web page
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
  const CodeLanding(
      {super.key, required this.text, required this.from, required this.done, required this.onLanded, required this.builder, this.hold = false});
  final String text;
  final bool hold;                    // v0.957 an earlier message is still landing: this one waits its turn (one at a time)
  final int from;
  final bool done;
  final void Function(int words) onLanded;

  /// v0.960 [tail] = how much ink each of the newest words has (oldest first, 0..1), worked out every frame.
  final Widget Function(String shown, bool streaming, List<double> tail) builder;

  /// v0.957 how long each word takes to land. Medium slow and steady - about 11 words a second, so a reply reads as
  /// written, not dropped in (it was ~19 a second and leapt to ~38 with a backlog). A long backlog speeds it up only
  /// gradually (never a jump in pace), down to ~22 a second once 300 words wait, so it never falls minutes behind.
  static double msPerWord(int waiting) {
    const slow = 90.0, fast = 45.0, from = 60, to = 300;
    if (waiting <= from) return slow;
    if (waiting >= to) return fast;
    final t = (waiting - from) / (to - from);
    return slow + (fast - slow) * (t * t * (3 - 2 * t));   // smoothstep: the pace eases, it never steps
  }

  /// v0.960 a new word rises from faint to full ink over this long, frame by frame, the same for every word whatever
  /// the pace (it jumped a shade each time the next word landed, and not at all when code was near the end).
  static const fadeMs = 280.0;

  /// v0.960 the ink of the newest words (oldest first) from how long ago each one appeared.
  static List<double> tailInk(List<double> agesMs) =>
      [for (final a in agesMs) (a / fadeMs).clamp(.06, 1.0).toDouble()];

  @override
  State<CodeLanding> createState() => _CodeLandingState();
}

class _CodeLandingState extends State<CodeLanding> with SingleTickerProviderStateMixin {
  late final Ticker _ticker = createTicker(_onTick);
  late int _n = widget.from;                     // words shown
  double _carry = 0;                             // part of the next word's time already gone
  final _clock = Stopwatch()..start();
  final Map<int, double> _born = {};             // v0.960 word index -> when it appeared (ms), the newest few only
  Duration _last = Duration.zero;
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

  bool get _fading => _born.values.any((t) => _clock.elapsedMilliseconds - t < CodeLanding.fadeMs);

  void _go() {
    final total = _words.length;
    if (_reduced) {
      if (_n != total) {
        _n = total;
        widget.onLanded(_n);
      }
      return;
    }
    if (widget.hold) {
      if (_ticker.isActive) _ticker.stop();
      return;
    }
    if ((_n < total || _fading) && !_ticker.isActive) {
      _last = Duration.zero;
      _ticker.start();
    }
  }

  void _onTick(Duration elapsed) {
    final dt = elapsed - _last;
    _last = elapsed;
    final total = _words.length;
    final waiting = total - _n;
    if (waiting <= 0) {
      _carry = 0;
      if (!_fading) {
        _ticker.stop();
        _born.clear();
      }
      setState(() {});                           // the last words finish rising
      return;
    }
    _carry += dt.inMicroseconds / 1000 / CodeLanding.msPerWord(waiting);   // v0.957 an even, medium-slow pace
    final step = _carry.floor();
    if (step > 0) {
      _carry -= step;
      final now = _clock.elapsedMilliseconds.toDouble();
      final to = (_n + step).clamp(0, total);
      for (var k = _n; k < to; k++) {
        _born[k] = now;
      }
      _born.removeWhere((k, _) => k < to - 8);
      _n = to;
      widget.onLanded(_n);
    }
    setState(() {});                             // every frame: the newest words keep rising
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
    final now = _clock.elapsedMilliseconds.toDouble();
    final ages = <double>[];
    if (!_reduced) {
      for (var k = n - 1; k >= 0 && k >= n - 8; k--) {
        final b = _born[k];
        if (b == null || now - b >= CodeLanding.fadeMs) break;
        ages.insert(0, now - b);
      }
    }
    final tail = CodeLanding.tailInk(ages);
    return widget.builder(shown, !widget.done || n < w.length || tail.isNotEmpty, tail);
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
        {
          // v0.999 the server says it in the past ("Ran the unit tests"); older steps had only the ask ("Run the unit tests")
          final did = _s(s['did']);
          if (did.isNotEmpty) {
            final at = did.indexOf(' ');
            return (Icons.terminal_rounded, at < 0 ? did : did.substring(0, at).replaceAll(':', ''), at < 0 ? '' : did.substring(at + 1), true);
          }
          return (Icons.terminal_rounded, 'Ran', _s(s['desc']).isNotEmpty ? 'a command: ${_s(s['desc'])}' : 'a command', true);
        }
      case 'read':
        return (Icons.description_outlined, 'Read', path, false);
      case 'list':
        return s['glob'] == true
            ? (Icons.search_rounded, 'Found', '${codeCount(s['n'], 'file')} · ${_s(s['path'])}', false)
            : (Icons.folder_open_rounded, 'Listed', _s(s['path']).isEmpty ? 'the repo' : _s(s['path']), false);
      case 'search' || 'grep' || 'usages':
        return (Icons.search_rounded, 'Searched', '${_s(s['q']).isNotEmpty ? 'for ${_s(s['q'])}' : 'the code'}${codeMatches(s)}', false);
      case 'edit':
        // v1.1 a notebook cell: "Edited cell 3 of analysis.ipynb"
        if (s.containsKey('cell')) return (Icons.edit_outlined, 'Edited', 'cell ${_s(s['cell'])} of $path', _hasChange(s));
        return (Icons.edit_outlined, 'Edited', path, _hasChange(s));
      case 'asked':
        return (Icons.help_outline_rounded, 'Asked you', _s(s['question']), true);
      case 'cmd':
        {
          final name = '/${_s(s['name']).replaceFirst(RegExp(r'^/'), '')}';
          return s['repo'] == true
              ? (Icons.terminal_rounded, 'Ran', 'your command $name', false)
              : (Icons.terminal_rounded, 'Started', name, false);
        }
      case 'mention':
        {
          final files = [for (final f in (s['files'] as List?) ?? const []) _s(f).split('/').last].where((e) => e.isNotEmpty).toList();
          return (Icons.alternate_email_rounded, 'Read', files.isEmpty ? 'the files you pointed at' : 'the files you pointed at: ${files.join(', ')}', false);
        }
      case 'hook':
        {
          final ev = _s(s['event']);
          return (
            s['block'] == true ? Icons.block_rounded : Icons.bolt_rounded,
            "This repo's",
            '${ev.isEmpty ? '' : '$ev '}hook ran${s['block'] == true ? ' and stopped the step' : ''}',
            _s(s['text']).trim().isNotEmpty
          );
        }
      case 'new':
        return (Icons.note_add_outlined, 'Wrote', path, _hasChange(s));
      case 'check':
        return (Icons.fact_check_outlined, 'Ran', s['ok'] == true ? 'your tests · passed' : 'your tests · failed', false);
      case 'agent':
        return (Icons.groups_outlined, 'Asked',
            (_s(s['name']).isNotEmpty ? 'a helper: ${_s(s['name'])}' : 'a helper') + (_s(s['model']).isNotEmpty ? ' · on ${_s(s['model'])}' : ''), false);
      case 'bgstart':
        {
          final did = _s(s['did']);
          if (did.isNotEmpty) {
            final at = did.indexOf(' ');
            return (Icons.terminal_rounded, at < 0 ? did : did.substring(0, at), at < 0 ? '' : did.substring(at + 1), false);
          }
          final what = _s(s['desc']).isNotEmpty ? _s(s['desc']) : _s(s['cmd']);
          return (Icons.terminal_rounded, 'Started', what.isEmpty ? 'a background command' : 'in the background: $what', false);
        }
      case 'bgout':
        return (Icons.terminal_rounded, 'Read', 'the output of ${_s(s['id'])}${_bgEnd(s)}', _tail(s).isNotEmpty);
      case 'bgkill':
        return (Icons.stop_circle_outlined, 'Stopped', _s(s['id']), false);
      case 'perm':
        {
          final yes = _s(s['answer']) != 'no';
          final note = _s(s['note']).trim();
          return (
            yes ? Icons.check_circle_outline_rounded : Icons.block_rounded,
            yes ? 'You allowed' : 'You said no',
            '${_s(s['what'])}${!yes && note.isNotEmpty ? ' · “$note”' : ''}',
            false
          );
        }
      case 'web':
        return (Icons.public_rounded, 'Read', '${codeHost(_s(s['url']))}${s['ok'] == false ? ' · could not open it' : ''}', false);
      case 'websearch':
        return (Icons.search_rounded, 'Searched', 'the web for “${_s(s['q'])}”${s['num'] is num ? ' · ${codeCount(s['num'], 'result')}' : ''}', false);
      case 'mcp':
        return _s(s['action']) == 'list'
            ? (Icons.hub_outlined, 'Listed', 'your MCP servers', false)
            : (Icons.hub_outlined, 'Used', '${_s(s['server'])}${_s(s['tool']).isEmpty ? '' : ' · ${_s(s['tool'])}'}', false);
      case 'skill':
        return _s(s['action']) == 'list'
            ? (Icons.menu_book_outlined, 'Listed', 'your skills', false)
            : (Icons.menu_book_outlined, 'Read', 'the skill ${_s(s['name'])}', false);
      default:
        return (Icons.circle_outlined, '', '', false);
    }
  }

  static List<String> _tail(Map<String, dynamic> s) => [for (final x in (s['tail'] as List?) ?? const []) _s(x)];

  /// " · still running" / " · exited 0" for a look at a background command.
  static String _bgEnd(Map<String, dynamic> s) {
    if (s['running'] == true) return ' · still running';
    if (s['rc'] != null) return ' · exited ${_s(s['rc'])}';
    return '';
  }

  /// The icon's colour when it says something (a yes in green, a no in red).
  static Color? _tint(HoolaColors c, Map<String, dynamic> s) {
    if (_s(s['k']) == 'hook') return s['block'] == true ? c.warn : null;
    if (_s(s['k']) != 'perm') return null;
    return _s(s['answer']) == 'no' ? c.bad : c.ok;
  }

  static bool _hasChange(Map<String, dynamic> s) =>
      ((s['hunk'] as List?)?.isNotEmpty ?? false) || ((s['diff'] as List?)?.isNotEmpty ?? false);

  Widget _detail(HoolaColors c, Map<String, dynamic> s) {
    final box = BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.line));
    if (_s(s['k']) == 'asked') {
      // v1.1 the question, the choices it offered and her answer
      final answer = _s(s['answer']).trim();
      final choices = [for (final x in (s['choices'] as List?) ?? const []) _s(x)].where((e) => e.isNotEmpty).toList();
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(_s(s['question']), style: codeSans(c, size: 14.5, height: 1.45)),
        if (choices.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('Choices: ${choices.join(' · ')}', style: codeSans(c, size: 13, color: c.ink3)),
          ),
        const SizedBox(height: 6),
        Text(answer.isEmpty ? 'No answer' : 'You: $answer',
            style: codeSans(c, size: 14, weight: FontWeight.w500, color: answer.isEmpty ? c.ink3 : c.ink)),
      ]);
    }
    if (_s(s['k']) == 'hook') {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: box,
        child: SelectableText(_s(s['text']).trim(), style: codeMono(c, size: 12.5, color: c.ink2)),
      );
    }
    if (_s(s['k']) == 'bgout') {
      final tail = _tail(s);
      return CodeTermBox(
          lines: tail.length > 24 ? tail.sublist(tail.length - 24) : tail,
          end: s['running'] == true ? 'still running' : (s['rc'] != null ? 'exited ${_s(s['rc'])}' : ''),
          endOk: s['running'] == true ? null : s['rc'] == 0);
    }
    if (_s(s['k']) == 'bash') {
      final rc = s['rc'];
      final ok = rc == 0 && s['timed_out'] != true;
      final tail = _tail(s);
      final secs = s['seconds'];
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        CodeTermBox(cmd: _s(s['cmd']), lines: tail.length > 24 ? tail.sublist(tail.length - 24) : tail),
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
    final hunk = (s['hunk'] as List?) ?? const [];
    if (hunk.isNotEmpty) {
      return CodeEditCard(
          verb: _s(s['k']) == 'new' ? 'Wrote' : 'Edited',
          path: _s(s['path']),
          added: (s['added'] as num?)?.toInt() ?? 0,
          removed: (s['removed'] as num?)?.toInt() ?? 0,
          rows: hunk);
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
      // v1.1 a question she was asked shows her answer under it at once (a tap folds it)
      final open = _s(s['k']) == 'asked' ? !_open.contains(i) : _open.contains(i);
      final Widget head = verb.isEmpty
          ? Container(constraints: const BoxConstraints(minHeight: 52), alignment: Alignment.centerLeft, child: widget.fallback(s))
          : Semantics(
              button: can,
              label: '$verb $words${can ? (open ? '. Hide the details' : '. Show the details') : ''}',
              excludeSemantics: true,
              child: InkWell(
                onTap: can ? () => setState(() => _open.contains(i) ? _open.remove(i) : _open.add(i)) : null,
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
                          : Icon(icon, size: 21, color: _tint(c, s) ?? c.ink2))),
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


/// v0.999 "7 matches in 3 files" / "3 files" - a search as Claude Code counts it ('' when the step has no count).
String codeMatches(Map<String, dynamic> s) {
  final n = s['num'] ?? s['n'];
  if (n is! num) return '';
  final f = s['files'];
  if (f is num && f != n) return ' · ${codeCount(n, 'match', 'matches')} in ${codeCount(f, 'file')}';
  return n == 0 ? ' · no matches' : ' · ${codeCount(n, 'file')}';
}

String codeCount(Object? n, String one, [String? many]) {
  final v = n is num ? n.round() : int.tryParse('$n') ?? 0;
  return '$v ${v == 1 ? one : (many ?? '${one}s')}';
}

/// v0.999 the real change as Claude Code shows it: old and new line numbers, red removed, green added, context grey.
/// Rows come from the server as [kind, old line, new line, text]; '@' is a gap between two parts.
class CodeHunk extends StatelessWidget {
  const CodeHunk({super.key, required this.rows, this.bare = false});
  final List rows;
  final bool bare;                    // v1.0 inside a CodeEditCard: no box of its own

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final small = codeMono(c, size: 12, color: c.ink3);
    String cell(Object? v) => v == null ? '' : '$v';
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: bare ? null : BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.line)),
      clipBehavior: bare ? Clip.none : Clip.antiAlias,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final r in rows)
            if (r is List && r.length >= 4)
              r[0] == '@' || r[0] == '…'
                  ? Padding(
                      padding: const EdgeInsets.fromLTRB(84, 2, 12, 2),
                      child: Text(r[0] == '@' ? '⋯' : cell(r[3]), style: small))
                  : Container(
                      color: r[0] == '+' ? c.okSoft : (r[0] == '-' ? c.badSoft : null),
                      padding: const EdgeInsets.only(right: 12),
                      child: Row(children: [
                        SizedBox(width: 34, child: Text(cell(r[1]), textAlign: TextAlign.right, style: small)),
                        SizedBox(width: 34, child: Text(cell(r[2]), textAlign: TextAlign.right, style: small)),
                        SizedBox(
                            width: 16,
                            child: Text(r[0] == '+' ? '+' : (r[0] == '-' ? '−' : ''),
                                textAlign: TextAlign.center,
                                style: codeMono(c, size: 12.5, color: r[0] == '+' ? c.ok : c.bad))),
                        Text(cell(r[3]),
                            style: codeMono(c, size: 12.5, color: r[0] == '+' ? c.ok : (r[0] == '-' ? c.bad : c.ink2))),
                      ]),
                    ),
        ]),
      ),
    );
  }
}

/// v1.0 the host of a web address ("docs.python.org"), or the address itself.
String codeHost(String url) {
  final u = Uri.tryParse(url.trim());
  final h = u?.host ?? '';
  return h.isEmpty ? url : (h.startsWith('www.') ? h.substring(4) : h);
}

/// v1.0 the terminal's colours (the design: a dark card, light text, red and green for how it ended, grey for the
/// command line).
class CodeTerm {
  static const bg = HoolaTerminal.bg;
  static const ink = HoolaTerminal.ink;
  static const red = HoolaTerminal.red;
  static const green = HoolaTerminal.green;
  static const grey = HoolaTerminal.grey;
}

/// v1.0 a command run as a dark terminal card: "$ command" in grey, its output, and how it ended (green / red).
class CodeTermBox extends StatelessWidget {
  const CodeTermBox({super.key, this.cmd = '', this.lines = const [], this.end = '', this.endOk, this.size = 12});
  final String cmd;
  final List<String> lines;
  final String end;
  final bool? endOk;
  final double size;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final endColor = endOk == true ? CodeTerm.green : (endOk == false ? CodeTerm.red : CodeTerm.grey);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: CodeTerm.bg,
        borderRadius: BorderRadius.circular(12),
        border: c.dark ? Border.all(color: c.line) : null,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        if (cmd.isNotEmpty) Text('\$ $cmd', style: codeMono(c, size: size, color: CodeTerm.grey)),
        if (lines.isNotEmpty)
          Padding(
            padding: EdgeInsets.only(top: cmd.isNotEmpty ? 3 : 0),
            child: Text(lines.join('\n'), style: codeMono(c, size: size, color: CodeTerm.ink)),
          ),
        if (end.isNotEmpty)
          Padding(
            padding: EdgeInsets.only(top: cmd.isNotEmpty || lines.isNotEmpty ? 3 : 0),
            child: Text(end, style: codeMono(c, size: size, color: endColor)),
          ),
      ]),
    );
  }
}

/// v1.0 one file's change as a card: a header row ("Edited path +3 −1") over its lines.
class CodeEditCard extends StatelessWidget {
  const CodeEditCard({super.key, required this.verb, required this.path, this.added = 0, this.removed = 0, required this.rows});
  final String verb, path;
  final int added, removed;
  final List rows;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.line)),
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
        Container(
          constraints: const BoxConstraints(minHeight: 40),
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
          decoration: BoxDecoration(color: c.sunk, border: Border(bottom: BorderSide(color: c.line))),
          child: Row(children: [
            Text(verb, style: codeSans(c, size: 13.5, weight: FontWeight.w600)),
            const SizedBox(width: 8),
            Expanded(child: Text(path, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12.5, color: c.ink2))),
            const SizedBox(width: 8),
            CodeStat(added, removed, size: 12),
          ]),
        ),
        if (rows.isNotEmpty) CodeHunk(rows: rows, bare: true),
      ]),
    );
  }
}
