// HOOLA THREAD KIT (owner: "EVERY CHAT SECTION MUST HAVE SAME FEATURE, DESIGN AND TEXT LANDING, TIMING, SPACING ...
// CURRENTLY HOOLA CHAT AND HOOLA CODE IS PERFECT ... DO IT SAME FOR ALL TOOLS AND FEATURES" -> prototype -> "GO").
// The Hoola chat's own pieces (hoola_chat.dart) as public widgets, so every chat panel in the app draws a
// conversation the same way. The numbers are the chat's, not new ones:
//
//   her message   a quiet bubble on the right (the sunk role), 16 / 1.5 sans, 18 dp under it
//   Hoola's reply no bubble, the reply serif 16 / 1.5 (HoolaMd), words landing at 34 ms a word, each new word
//                 rising to full ink over 460 ms (the console's pacer; the same numbers as hoola_chat.dart _Paced)
//   while it works  the thinking mark, the real step, a clock from the first second
//   under the newest reply  Copy · Read aloud · Share (+ Good / Not right / Ask again where the screen can honour them)
//
// A screen that polls its server hands the whole list to HoolaThreadView each time; the view works out which replies
// are new and lands only those (history is drawn whole). A screen with its own list uses the pieces directly:
// HoolaHerBubble, HoolaLanding, HoolaWorkingRow, HoolaReplyActions.
//
// An OLD-design screen (Night Glass, always dark) wraps the thread in HoolaOnDark so the kit's colours are the dark set.
import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart' show Ticker;
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import '../../native.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import 'hoola_md.dart';

/// The landing pace every chat panel shares (static/console/stream.js Pacer, hoola_chat.dart kLandMsPerWord).
const kThreadMsPerWord = 34;
const kThreadSoftMs = 460;

List<String> _threadWords(String s) => s.isEmpty ? const [] : s.split(RegExp(r'(?<=\s)'));

/// The kit's colours as the dark set, for a thread drawn inside an old-design (always dark) screen.
ThemeData? _dark;

class HoolaOnDark extends StatelessWidget {
  const HoolaOnDark({super.key, required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) {
    final theme = _dark ??= hoolaTheme(Brightness.dark);   // built once: old screens wrap every message
    return Theme(data: theme, child: DefaultTextStyle(style: HoolaType.body(theme.extension<HoolaColors>()!), child: child));
  }
}

/// Hoola's words, landing one by one. [land] false = history: drawn whole. A text that grows (a snapshot that is
/// still being written) lands only its new part. [live] = more words may still come (open marks stay hidden).
class HoolaLanding extends StatefulWidget {
  const HoolaLanding(this.text, {super.key, this.land = true, this.live = false, this.selectable = false, this.sans = false, this.onLanded});
  final String text;
  final bool land;
  final bool live;
  final bool selectable;
  final bool sans;
  /// Called once, when the last word has landed (not for history).
  final VoidCallback? onLanded;
  @override
  State<HoolaLanding> createState() => _HoolaLandingState();
}

class _HoolaLandingState extends State<HoolaLanding> with SingleTickerProviderStateMixin {
  Ticker? _tk;   // made only when words must land: a history reply never makes one
  Ticker get _ticker => _tk ??= createTicker(_tick);
  double _t = 0;   // this reply's own clock (ms), moved by the ticker - so tests and the app agree
  Duration? _prev;
  List<String> _words = const [];
  int _shown = 0;
  final _born = <int>[];
  double _budget = 0;
  bool _told = false;

  @override
  void initState() {
    super.initState();
    _words = _threadWords(widget.text);
    if (!widget.land) {
      _shown = _words.length;
      _born.addAll(List.filled(_shown, -100000));
      _told = true;
    }
    _kick();
  }

  @override
  void didUpdateWidget(covariant HoolaLanding old) {
    super.didUpdateWidget(old);
    if (old.text == widget.text) {
      if (old.live != widget.live) _kick();
      return;
    }
    final before = _words.take(_shown).join();
    _words = _threadWords(widget.text);
    if (!widget.text.startsWith(before)) {
      // the words changed under us: a live reply starts again, a finished one is shown at once
      _shown = widget.live ? 0 : _words.length;
      _born
        ..clear()
        ..addAll(List.filled(_shown, -100000));
      _budget = 0;
    }
    if (_shown > _words.length) _shown = _words.length;
    if (_born.length > _shown) _born.removeRange(_shown, _born.length);
    if (_shown < _words.length) _told = false;
    _kick();
  }

  bool get _fading => _born.isNotEmpty && _t - _born.last < kThreadSoftMs;

  void _tell() {
    if (_told || widget.live) return;
    _told = true;
    final f = widget.onLanded;
    if (f != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) f();
      });
    }
  }

  void _kick() {
    if (!mounted) return;
    // reduce motion (read without a context: initState may call this)
    if (WidgetsBinding.instance.platformDispatcher.accessibilityFeatures.disableAnimations) {
      while (_born.length < _words.length) {
        _born.add(-100000);
      }
      _shown = _words.length;
      _tell();
      return;
    }
    if (_shown >= _words.length && !_fading) {
      _tell();
      return;
    }
    if (!_ticker.isActive) {
      if (_budget < kThreadMsPerWord) _budget = kThreadMsPerWord.toDouble();   // the first word comes at once
      _prev = null;
      _ticker.start();
    }
  }

  void _tick(Duration elapsed) {
    final dt = _prev == null ? 0.0 : (elapsed - _prev!).inMicroseconds / 1000.0;
    _prev = elapsed;
    _t += dt;
    final waiting = _words.length - _shown;
    if (waiting > 0) {
      _budget += dt;
      final steady = (_budget / kThreadMsPerWord).floor();
      _budget -= steady * kThreadMsPerWord;
      var n = steady + (waiting ~/ 80).clamp(0, 2);
      if (n > waiting) n = waiting;
      if (n > 0) {
        final now = _t.round();
        for (var i = 0; i < n; i++) {
          _born.add(now);
        }
        _shown += n;
      }
    } else {
      _budget = 0;
    }
    if (_shown >= _words.length && !_fading) {
      _ticker.stop();
      _tell();
    }
    setState(() {});
  }

  @override
  void dispose() {
    _tk?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final now = _t.round();
    final all = _shown >= _words.length;
    final ink = <double>[];
    for (var i = _born.length - 1; i >= 0 && i >= _born.length - 16; i--) {
      final age = now - _born[i];
      if (age >= kThreadSoftMs) break;
      ink.insert(0, Curves.ease.transform((age / kThreadSoftMs).clamp(0.0, 1.0)));
    }
    final text = all ? widget.text : _words.take(_shown).join();
    return HoolaMd(text,
        streaming: widget.live || !all || ink.isNotEmpty, fade: true, tail: ink, selectable: widget.selectable, sans: widget.sans);
  }
}

/// Her message: a quiet bubble on the right.
class HoolaHerBubble extends StatelessWidget {
  const HoolaHerBubble(this.text, {super.key, this.onLongPress, this.above, this.pending = false});
  final String text;
  final VoidCallback? onLongPress;
  /// Her files, drawn above the bubble (the screen's own tiles).
  final Widget? above;
  /// Sent, not yet confirmed by the server: drawn a little lighter.
  final bool pending;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final style = HoolaType.bodyLarge(c).copyWith(height: 1.5);
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
        if (above != null) above!,
        if (text.trim().isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(left: 48),
            child: GestureDetector(
              onLongPress: onLongPress,
              child: Opacity(
                opacity: pending ? .7 : 1.0,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
                  decoration: BoxDecoration(
                    color: c.sunk,
                    borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(20), topRight: Radius.circular(20), bottomLeft: Radius.circular(20), bottomRight: Radius.circular(6)),
                  ),
                  child: Text(text, style: style),
                ),
              ),
            ),
          ),
      ]),
    );
  }
}

/// While Hoola works: the thinking mark, the real step, and how long it has taken.
class HoolaWorkingRow extends StatefulWidget {
  const HoolaWorkingRow({super.key, this.label, this.since, this.name = 'Hoola'});
  /// What it is doing now ("Reading the sheet"); empty = "Thinking".
  final String? label;
  /// When the work started (her message's time); the clock counts from here.
  final DateTime? since;
  final String name;
  @override
  State<HoolaWorkingRow> createState() => _HoolaWorkingRowState();
}

class _HoolaWorkingRowState extends State<HoolaWorkingRow> {
  final _made = DateTime.now();
  DateTime get _t0 {
    final s = widget.since;
    if (s == null || s.isAfter(_made) || _made.difference(s) > const Duration(hours: 2)) return _made;
    return s;
  }
  Timer? _tick;

  @override
  void initState() {
    super.initState();
    _tick = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final s = DateTime.now().difference(_t0).inSeconds;
    final clock = s < 1 ? '' : (s < 60 ? '${s}s' : '${s ~/ 60}m ${(s % 60).toString().padLeft(2, '0')}s');
    final step = (widget.label ?? '').trim();
    final label = step.isEmpty ? 'Thinking' : step;
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Semantics(
        liveRegion: true,
        label: '${widget.name} is working: $label',
        excludeSemantics: true,
        child: Row(children: [
          const HoolaMark(size: 24),
          const SizedBox(width: 10),
          Flexible(
            child: AnimatedSwitcher(
              duration: HoolaMotion.of(context, HoolaMotion.fade),
              layoutBuilder: (cur, prev) => Stack(alignment: Alignment.centerLeft, children: [...prev, if (cur != null) cur]),
              child: Text(label, key: ValueKey(label), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: HoolaType.body(c).copyWith(color: c.ink2)),
            ),
          ),
          if (clock.isNotEmpty) ...[
            const SizedBox(width: 8),
            Text(clock, style: HoolaType.small(c).copyWith(fontFeatures: const [FontFeature.tabularFigures()])),
          ],
        ]),
      ),
    );
  }
}

/// "Worked for 12s" above a reply that needed steps.
class HoolaWorkedLine extends StatelessWidget {
  const HoolaWorkedLine(this.text, {super.key, this.onTap});
  final String text;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: HoolaRadius.r(HoolaRadius.chip),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(text, style: HoolaType.small(c).copyWith(color: c.ink2)),
          if (onTap != null) Icon(Icons.chevron_right_rounded, size: 18, color: c.ink3),
        ]),
      ),
    );
  }
}

/// Under the newest reply: Copy · Read aloud · Share, and Good / Not right / Ask again where the screen gives them.
class HoolaReplyActions extends StatelessWidget {
  const HoolaReplyActions({super.key, required this.text, required this.onToast, this.onAloud, this.share = true,
      this.vote, this.onVote, this.onAgain});
  final String text;
  final void Function(String) onToast;
  /// Read the reply aloud (a screen with the app passes `app.readAloud`).
  final Future<void> Function(String)? onAloud;
  final bool share;
  /// 'up', 'down' or null; shown only when [onVote] is given.
  final String? vote;
  final void Function(String value)? onVote;
  final VoidCallback? onAgain;

  Future<void> _share() async {
    try {
      final dir = await getTemporaryDirectory();
      final f = File('${dir.path}/hoola-reply.txt');
      await f.writeAsString(text);
      await Native.shareFile(f.path, mime: 'text/plain', title: 'Share the reply');
    } catch (_) {
      await Clipboard.setData(ClipboardData(text: text));
      onToast('Copied - paste it where you want to share');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    Widget b(IconData icon, String label, VoidCallback onTap, {bool on = false}) => Semantics(
          button: true,
          label: label,
          selected: on,
          excludeSemantics: true,
          child: InkResponse(
            onTap: () {
              HapticFeedback.selectionClick();
              onTap();
            },
            radius: 20,
            child: SizedBox(width: 38, height: 38, child: Icon(icon, size: 18, color: on ? c.accent : c.ink3)),
          ),
        );
    final aloud = onAloud;
    final rate = onVote;
    final again = onAgain;
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(children: [
        b(Icons.copy_rounded, 'Copy', () async {
          await Clipboard.setData(ClipboardData(text: text));
          onToast('Copied');
        }),
        if (aloud != null) b(Icons.volume_up_outlined, 'Read aloud', () => aloud(text)),
        if (share) b(Icons.ios_share_rounded, 'Share', _share),
        if (rate != null) ...[
          b(vote == 'up' ? Icons.thumb_up_rounded : Icons.thumb_up_outlined, 'Good answer', () => rate(vote == 'up' ? 'none' : 'up'), on: vote == 'up'),
          b(vote == 'down' ? Icons.thumb_down_rounded : Icons.thumb_down_outlined, 'Not right', () => rate(vote == 'down' ? 'none' : 'down'), on: vote == 'down'),
        ],
        if (again != null) b(Icons.refresh_rounded, 'Ask again', again),
      ]),
    );
  }
}

/// One entry of a thread.
class HoolaMsg {
  const HoolaMsg({required this.id, required this.text, this.mine = false, this.pending = false, this.worked, this.custom});
  final String id;
  final String text;
  /// Her message (else Hoola's reply).
  final bool mine;
  final bool pending;
  /// "Worked for 12s" shown above a reply, when the screen knows it.
  final String? worked;
  /// Anything else that sits in the thread (a card, a notice); drawn as it is.
  final Widget? custom;
}

/// A whole conversation for a screen that reloads its list (polling or one answer at a time).
/// History (what is there when [loaded] first becomes true, or after [threadKey] changes) is drawn whole;
/// a reply that arrives later lands word by word. Follows the end unless she has scrolled up.
class HoolaThreadView extends StatefulWidget {
  const HoolaThreadView({super.key, required this.messages, this.threadKey = '', this.loaded = true, this.working = false,
      this.label, this.since, this.name = 'Hoola', this.onAloud, this.onToast, this.onAgain, this.vote, this.onVote,
      this.share = true, this.padding = const EdgeInsets.fromLTRB(20, 16, 20, 16), this.header, this.empty, this.controller, this.sans = false});
  final List<HoolaMsg> messages;
  final String threadKey;
  /// False while the first load is still running (so that load is history, not a new reply).
  final bool loaded;
  final bool working;
  final String? label;
  final DateTime? since;
  final String name;
  final Future<void> Function(String)? onAloud;
  final void Function(String)? onToast;
  final VoidCallback? onAgain;
  final String? vote;
  final void Function(String value)? onVote;
  final bool share;
  final EdgeInsets padding;
  /// Drawn above the first message (a title card, a notice).
  final Widget? header;
  /// Drawn when there is nothing yet.
  final Widget? empty;
  final ScrollController? controller;
  final bool sans;
  @override
  State<HoolaThreadView> createState() => _HoolaThreadViewState();
}

class _HoolaThreadViewState extends State<HoolaThreadView> {
  late final ScrollController _c = widget.controller ?? ScrollController();
  Set<String>? _seen;                 // null until the first load is in
  final _fresh = <String>{};          // replies that arrived while she watched: these land
  bool _stick = true;

  @override
  void initState() {
    super.initState();
    _take();
  }

  @override
  void didUpdateWidget(covariant HoolaThreadView old) {
    super.didUpdateWidget(old);
    if (old.threadKey != widget.threadKey) {
      _seen = null;
      _fresh.clear();
      _stick = true;
    }
    _take();
  }

  void _take() {
    if (!widget.loaded) return;
    final seen = _seen;
    if (seen == null) {
      _seen = widget.messages.map((m) => m.id).toSet();
      _later();
      return;
    }
    var grew = false;
    for (final m in widget.messages) {
      if (seen.add(m.id)) {
        grew = true;
        if (!m.mine && m.custom == null) _fresh.add(m.id);
        if (m.mine) _stick = true;      // her own message always brings the end into view
      }
    }
    if (grew) _later();
  }

  void _later() => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _stick) _toEnd();
      });

  void _toEnd() {
    if (!_c.hasClients) return;
    _c.jumpTo(_c.position.maxScrollExtent);
  }

  @override
  void dispose() {
    if (widget.controller == null) _c.dispose();
    super.dispose();
  }

  void _toast(String s) {
    final t = widget.onToast;
    if (t != null) {
      t(s);
    } else {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(s), duration: const Duration(seconds: 2)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final msgs = widget.messages;
    var lastReply = -1;
    for (var i = msgs.length - 1; i >= 0; i--) {
      if (!msgs[i].mine && msgs[i].custom == null && msgs[i].text.trim().isNotEmpty) {
        lastReply = i;
        break;
      }
    }
    final head = widget.header == null ? 0 : 1;
    final tail = widget.working ? 1 : 0;
    if (msgs.isEmpty && !widget.working && widget.empty != null) return widget.empty!;
    return NotificationListener<ScrollMetricsNotification>(
      onNotification: (n) {
        if (n.depth == 0 && _stick) _later();
        return false;
      },
      child: NotificationListener<ScrollNotification>(
        onNotification: (n) {
          if (n.depth != 0 || n.metrics.axis != Axis.vertical) return false;   // a wide table scrolling sideways
          if (n is ScrollEndNotification || (n is ScrollUpdateNotification && n.dragDetails != null)) {
            _stick = n.metrics.maxScrollExtent - n.metrics.pixels < 80;
          }
          return false;
        },
        child: ListView.builder(
          controller: _c,
          padding: widget.padding,
          itemCount: head + msgs.length + tail,
          itemBuilder: (context, i) {
            if (head == 1 && i == 0) return widget.header!;
            final k = i - head;
            if (k >= msgs.length) {
              return HoolaWorkingRow(key: const ValueKey('hoola-working'), label: widget.label, since: widget.since, name: widget.name);
            }
            final m = msgs[k];
            if (m.custom != null) return KeyedSubtree(key: ValueKey('c-${m.id}'), child: m.custom!);
            if (m.mine) return HoolaHerBubble(m.text, key: ValueKey('m-${m.id}'), pending: m.pending);
            final landing = _fresh.contains(m.id);
            final acts = k == lastReply && !widget.working && !landing;
            return Padding(
              key: ValueKey('r-${m.id}'),
              padding: const EdgeInsets.only(bottom: 18),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if ((m.worked ?? '').isNotEmpty) HoolaWorkedLine(m.worked!),
                HoolaLanding(m.text, key: ValueKey('l-${m.id}'), land: landing, sans: widget.sans, onLanded: () {
                  if (mounted && _fresh.remove(m.id)) setState(() {});
                }),
                if (acts)
                  HoolaReplyActions(text: m.text, onToast: _toast, onAloud: widget.onAloud, share: widget.share,
                      vote: widget.vote, onVote: widget.onVote, onAgain: widget.onAgain),
              ]),
            );
          },
        ),
      ),
    );
  }
}
