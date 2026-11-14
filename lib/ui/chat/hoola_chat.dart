// v0.862 R3 THE CHAT (docs/HOOLA_APP_REDESIGN_PLAN.md R3): the conversation in the new design, inside the R2 shell.
//
//   her message      = a quiet bubble on the right (the sunk role), 16 sans
//   Santosh's reply  = no bubble, the serif at reading size, full width (hoola_md.dart)
//   while it works   = the working mark (thinking / the real step / writing) with a clock, Stop in the composer
//   tools it used    = one line "Used 4 steps ›" that opens the Steps sheet (an icon per kind of step)
//   thinking         = "Thought for 8s ›", opens to the thinking
//   under the newest reply = Copy · Read aloud · Share · Good · Not right · Ask again
//   long-press any message = Copy · Quote · Edit (hers) · Ask again (the newest reply) · Select text · Read aloud
//   scrolled up      = a round "to the newest" button with the count of what arrived
//   no connection    = "Reconnecting…" under the top bar, gone when it is back
// Every card (approval, draft, payment, plan ...) is still the card the old chat draws (feedCard), shown in its own
// dark frame until R4 redraws the cards. Nothing about sending, the stream or the server changed: the same Santosh
// state drives both chats.
import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import '../../native.dart';
import '../../state.dart';
import '../chat_screen.dart' show feedCard;
import '../glass.dart' show santoshTheme;
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import '../md_text.dart' show mdPlain;
import '../shell/hoola_shell.dart' show HoolaComposer;
import '../chat_attach.dart' show filesOnlyText;
import 'hoola_attach.dart';
import 'hoola_card.dart';
import 'hoola_md.dart';

class HoolaChat extends StatefulWidget {
  const HoolaChat({super.key, required this.app, required this.onTalk, required this.onMenu});
  final Santosh app;
  final VoidCallback onTalk;
  final VoidCallback onMenu;
  @override
  State<HoolaChat> createState() => _HoolaChatState();
}

class _HoolaChatState extends State<HoolaChat> {
  final _scroll = ScrollController();
  final _box = TextEditingController();
  final _focus = FocusNode();
  late final Set<FeedItem> _old = app.feed.toSet();
  /// v0.889 the chat this screen belongs to (the screen is keyed by it): her unfinished words are kept per chat.
  late final String? _conv = app.conversationId;   // on screen when the chat opened: no reveal animation
  /// Turns whose reply already came in word by word as a live stream: the finished message then shows at once
  /// (revealing it again would look like the reply started over).
  final Set<String> _streamed = {};
  int _lastLen = 0;
  bool _away = false;
  int _unseen = 0;
  FeedItem? _selecting;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _lastLen = app.feed.length;
    _box.text = app.draftFor(_conv);
    _box.addListener(() => app.saveDraft(_conv, _box.text));
    app.addListener(_onApp);
    _scroll.addListener(_onScroll);
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _scroll.dispose();
    _box.dispose();
    _focus.dispose();
    super.dispose();
  }

  void _onApp() {
    final added = app.feed.length - _lastLen;
    _lastLen = app.feed.length;
    if (added <= 0) return;
    if (app.replaying || added > 2) _old.addAll(app.feed.sublist(app.feed.length - added));   // history: shown at once
    if (_away) {
      if (mounted) setState(() => _unseen += added);
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (_scroll.hasClients && _scroll.offset > 0) {
        _scroll.animateTo(0, duration: HoolaMotion.of(context, HoolaMotion.page), curve: HoolaMotion.ease);
      }
    });
  }

  // the list is reversed: offset 0 = the newest message
  void _onScroll() {
    final away = _scroll.hasClients && _scroll.offset > 320;
    if (away != _away) {
      setState(() {
        _away = away;
        if (!away) _unseen = 0;
      });
    }
  }

  void _toNewest() {
    if (!_scroll.hasClients) return;
    if (_scroll.offset > 4000) _scroll.jumpTo(900);
    _scroll.animateTo(0, duration: HoolaMotion.of(context, HoolaMotion.page), curve: HoolaMotion.ease);
    setState(() => _unseen = 0);
  }

  void _toast(String t) =>
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t), duration: const Duration(seconds: 2)));

  String get _title {
    final id = app.conversationId;
    for (final c in app.chatList) {
      if (c['id'] == id) {
        final t = '${c['title'] ?? ''}'.trim();
        if (t.isNotEmpty) return t;
      }
    }
    return 'New chat';
  }

  /// The newest reply in the chat (only it can be asked again; its action row shows by itself).
  FeedItem? get _lastReply {
    for (var i = app.feed.length - 1; i >= 0; i--) {
      final f = app.feed[i];
      if (f.data['ack'] == true) continue;   // v0.888 the "Thinking, one minute..." placeholder is not a reply
      if (f.kind == 'message' && '${f.data['role']}' == 'assistant') return f;
      if (f.kind == 'message') return null;   // her message is newer than any reply
    }
    return null;
  }

  /// v0.888 the server's "Thinking, one minute..." line (an ephemeral placeholder until the real words come): it is
  /// shown as the working row with its clock, never as a reply with Copy / Share / Ask again under it.
  bool get _acked {
    for (var i = app.feed.length - 1; i >= 0 && i >= app.feed.length - 4; i--) {
      if (app.feed[i].data['ack'] == true) return true;
    }
    return false;
  }

  bool get _writing => app.feed.isNotEmpty && app.feed.last.kind == 'stream' && '${app.feed.last.data['text'] ?? ''}'.isNotEmpty;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) => Column(children: [
        _TopBar(title: _title, incognito: app.incognito, onMenu: widget.onMenu, onNew: () => app.newChat()),
        if (!app.connected && app.configured) const _Reconnecting(),
        Expanded(
          child: Stack(children: [
            _list(c),
            // v0.894 the reply fades into the page where it meets the composer and the top bar, like Claude's
            // (claude.ai: from-bg-100 gradients / mask-image fades) - a hard cut through a line looked unfinished
            Positioned(left: 0, right: 0, top: 0, height: 14, child: IgnorePointer(child: _Fade(c.bg, down: true))),
            Positioned(left: 0, right: 0, bottom: 0, height: 32, child: IgnorePointer(child: _Fade(c.bg, down: false))),
            Positioned(
              left: 0,
              right: 0,
              bottom: 10,
              child: IgnorePointer(
                ignoring: !_away,
                child: AnimatedOpacity(
                  opacity: _away ? 1 : 0,
                  duration: HoolaMotion.of(context, HoolaMotion.fade),
                  child: Center(child: _NewestButton(count: _unseen, onTap: _toNewest)),
                ),
              ),
            ),
          ]),
        ),
        HoolaComposer(
          app: app,
          onTalk: widget.onTalk,
          hint: 'Reply to ${app.aName}',
          controller: _box,
          focus: _focus,
          working: app.typing,
          onStop: () {
            HapticFeedback.lightImpact();
            app.stopWork();
            _toast('Stopping after this step');
          },
        ),
        const SizedBox(height: 8),
      ]),
    );
  }

  Widget _list(HoolaColors c) {
    final feed = app.feed;
    final working = (app.typing || _acked) && !_writing ? 1 : 0;
    final older = app.hasOlder ? 1 : 0;
    final last = _lastReply;
    // which items start a new day
    final dayStart = <int>{};
    DateTime? prev;
    for (var i = 0; i < feed.length; i++) {
      final t = _time(feed[i]);
      if (t == null) continue;
      if (prev == null || t.day != prev.day || t.month != prev.month || t.year != prev.year) dayStart.add(i);
      prev = t;
    }
    return ListView.builder(
      controller: _scroll,
      reverse: true,
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 8, HoolaSpace.gutter + 4, 16),
      itemCount: working + feed.length + older,
      itemBuilder: (context, i) {
        if (working == 1 && i == 0) {
          return _WorkingMark(key: const ValueKey('working'), name: app.aName, step: app.currentStep);
        }
        final k = i - working;
        if (k == feed.length) return _OlderButton(loading: app.loadingOlder, onTap: app.loadOlder);
        final fi = feed.length - 1 - k;
        final it = feed[fi];
        // a reply that arrived while the chat is open appears at reading speed (the same widget keeps its place
        // across rebuilds, so the reveal is never cut short) - unless it already streamed in word by word
        final fresh = it.kind == 'message' && !_old.contains(it) && !_streamed.contains('${it.data['turn'] ?? '-'}');
        Widget node = _item(it, c, fresh: fresh, actions: identical(it, last) && !app.typing);
        if (dayStart.contains(fi)) {
          node = Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min,
              children: [_DayHead(day: _time(it)!), node]);
        }
        return KeyedSubtree(key: ObjectKey(it), child: node);
      },
    );
  }

  DateTime? _time(FeedItem it) {
    if (it.kind != 'message') return null;
    return DateTime.tryParse('${it.data['at'] ?? ''}')?.toLocal();
  }

  Widget _item(FeedItem it, HoolaColors c, {bool fresh = false, bool actions = false}) {
    switch (it.kind) {
      case 'message':
        if (it.data['ack'] == true) return const SizedBox.shrink();   // v0.888 drawn as the working row instead
        final me = it.data['role'] == 'user';
        final text = '${it.data['text'] ?? ''}';
        final files = (it.data['files'] as List?) ?? const [];
        if (me) return _Mine(app: app, text: text, files: files, selecting: _selecting == it, onLongPress: () => _menu(it, text, true));
        final reply = fresh
            ? _Reveal(text: text, builder: (t, live) => HoolaMd(t, streaming: live, selectable: _selecting == it))
            : HoolaMd(text, selectable: _selecting == it);
        return Padding(
          padding: const EdgeInsets.only(bottom: 18),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            GestureDetector(behavior: HitTestBehavior.opaque, onLongPress: () => _menu(it, mdPlain(text), false), child: reply),
            if (_selecting == it) _DoneSelecting(onTap: () => setState(() => _selecting = null)),
            if (actions) _Actions(app: app, it: it, text: mdPlain(text), onToast: _toast),
          ]),
        );
      case 'stream':
        final turn = '${it.data['turn'] ?? ''}';
        if (turn.isNotEmpty && '${it.data['text'] ?? ''}'.isNotEmpty) _streamed.add(turn);
        return Padding(
          padding: const EdgeInsets.only(bottom: 18),
          child: HoolaMd('${it.data['text'] ?? ''}', streaming: true),
        );
      case 'think':
        return _Thinking(key: ObjectKey(it), it: it, name: app.aName);
      case 'say':
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(children: [
            Container(width: 6, height: 6, decoration: BoxDecoration(color: c.accent, shape: BoxShape.circle)),
            const SizedBox(width: 8),
            Expanded(child: Text('${it.data['text'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: HoolaType.small(c).copyWith(fontStyle: FontStyle.italic))),
          ]),
        );
      case 'steps':
        return _StepsLine(it: it);
      case 'note':
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text('${it.data['text'] ?? ''}', textAlign: TextAlign.center, style: HoolaType.small(c)),
        );
      default:
        final mine = hoolaCardFor(context, app, it);   // v0.864 R4 the cards redrawn so far
        if (mine != null) return mine;
        final card = feedCard(context, app, it);
        if (card == null) return const SizedBox.shrink();
        return _OldCard(child: card);
    }
  }

  // ------------------------------------------------------------------ the long-press sheet
  void _menu(FeedItem it, String text, bool me) {
    if (text.trim().isEmpty) return;
    HapticFeedback.mediumImpact();
    final lastReply = !me && identical(it, _lastReply);
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
              child: Text(text, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
            ),
            row(Icons.copy_rounded, 'Copy', () async {
              await Clipboard.setData(ClipboardData(text: text));
              _toast('Copied');
            }),
            row(Icons.format_quote_rounded, 'Quote in my reply', () => _quote(text)),
            if (me && it.eid != null && it.eid! > 0)
              row(Icons.edit_outlined, 'Edit message', () => _edit(it, text), sub: '${app.aName} answers again from here'),
            if (lastReply)
              row(Icons.refresh_rounded, 'Ask again', () async {
                final err = await app.retryLastReply();
                if (err != null) _toast('Could not ask again');
              }, sub: 'A new answer to the same message'),
            if (!me) row(Icons.volume_up_outlined, 'Read aloud', () => app.readAloud(text)),
            row(Icons.text_fields_rounded, 'Select text', () => setState(() => _selecting = it)),
            const SizedBox(height: 8),
          ]),
        );
      },
    );
  }

  void _quote(String text) {
    final q = text.trim().split('\n').take(4).map((l) => '> $l').join('\n');
    _box.text = '$q\n\n${_box.text}';
    _box.selection = TextSelection.collapsed(offset: _box.text.length);
    _focus.requestFocus();
  }

  Future<void> _edit(FeedItem it, String text) async {
    final ctl = TextEditingController(text: text);
    final out = await showDialog<String>(
      context: context,
      builder: (dctx) => AlertDialog(
        title: const Text('Edit message'),
        content: TextField(controller: ctl, autofocus: true, minLines: 1, maxLines: 8,
            decoration: const InputDecoration(hintText: 'Your message')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dctx), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(dctx, ctl.text), child: const Text('Send')),
        ],
      ),
    );
    ctl.dispose();
    if (out == null || out.trim().isEmpty || out.trim() == text.trim() || it.eid == null) return;
    final err = await app.editMessage(it.eid!, out);
    if (err != null) _toast('Could not edit the message');
  }
}

// ======================================================================================== pieces

class _TopBar extends StatelessWidget {
  const _TopBar({required this.title, required this.incognito, required this.onMenu, required this.onNew});
  final String title;
  final bool incognito;
  final VoidCallback onMenu;
  final VoidCallback onNew;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return SizedBox(
      height: 56,
      child: Row(children: [
        const SizedBox(width: 6),
        IconButton(tooltip: 'Open chats', onPressed: onMenu, icon: Icon(Icons.menu_rounded, color: c.ink)),
        Expanded(
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            if (incognito) ...[Icon(Icons.visibility_off_outlined, size: 16, color: c.ink3), const SizedBox(width: 6)],
            Flexible(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center, style: HoolaType.title(c))),
          ]),
        ),
        IconButton(tooltip: 'New chat', onPressed: onNew, icon: Icon(Icons.edit_square, color: c.ink, size: 22)),
        const SizedBox(width: 6),
      ]),
    );
  }
}

class _Reconnecting extends StatelessWidget {
  const _Reconnecting();
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      liveRegion: true,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 1.6, color: c.ink3)),
          const SizedBox(width: 8),
          Text('Reconnecting…', style: HoolaType.small(c)),
        ]),
      ),
    );
  }
}

/// Her message: a quiet bubble on the right; v0.895 her files land above it like Claude's - one photo large in its own
/// shape, several as big thumbnails in a row she can swipe (the row runs the full width, starting at the right edge).
class _Mine extends StatelessWidget {
  const _Mine({required this.app, required this.text, required this.files, required this.selecting, required this.onLongPress});
  final Santosh app;
  final String text;
  final List files;
  final bool selecting;
  final VoidCallback onLongPress;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final hasFiles = files.any((f) => f is Map);
    final onlyFiles = hasFiles &&
        (RegExp(r'^here (is a file|are \d+ files)$', caseSensitive: false).hasMatch(text.trim()) || filesOnlyText(text, files));
    final style = HoolaType.bodyLarge(c);
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
        if (hasFiles) HoolaSentFiles(files: files, app: app),
        if (!onlyFiles && text.trim().isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(left: 48),
            child: GestureDetector(
              onLongPress: onLongPress,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
                decoration: BoxDecoration(
                  color: c.sunk,
                  borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(20), topRight: Radius.circular(20), bottomLeft: Radius.circular(20), bottomRight: Radius.circular(6)),
                ),
                child: selecting ? SelectableText(text, style: style) : Text(text, style: style),
              ),
            ),
          ),
      ]),
    );
  }
}

class _DoneSelecting extends StatelessWidget {
  const _DoneSelecting({required this.onTap});
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(onPressed: onTap, icon: const Icon(Icons.check_rounded, size: 18), label: const Text('Done selecting')),
      );
}

/// Under the newest reply: Copy · Read aloud · Share · Good · Not right · Ask again.
class _Actions extends StatelessWidget {
  const _Actions({required this.app, required this.it, required this.text, required this.onToast});
  final Santosh app;
  final FeedItem it;
  final String text;
  final void Function(String) onToast;

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
    final fb = it.data['fb'];
    final canRate = '${it.data['turn'] ?? ''}'.isNotEmpty;
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
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(children: [
        b(Icons.copy_rounded, 'Copy', () async {
          await Clipboard.setData(ClipboardData(text: text));
          onToast('Copied');
        }),
        b(Icons.volume_up_outlined, 'Read aloud', () => app.readAloud(text)),
        b(Icons.ios_share_rounded, 'Share', _share),
        if (canRate) ...[
          b(fb == 'up' ? Icons.thumb_up_rounded : Icons.thumb_up_outlined, 'Good answer', () async {
            final err = await app.rateReply(it, fb == 'up' ? 'none' : 'up');
            if (err != null) onToast('Could not save that');
          }, on: fb == 'up'),
          b(fb == 'down' ? Icons.thumb_down_rounded : Icons.thumb_down_outlined, 'Not right', () async {
            final err = await app.rateReply(it, fb == 'down' ? 'none' : 'down');
            if (err != null) {
              onToast('Could not save that');
            } else if (fb != 'down') {
              onToast('Thanks. Ask again for a better answer, or tell ${app.aName} what was wrong.');
            }
          }, on: fb == 'down'),
        ],
        b(Icons.refresh_rounded, 'Ask again', () async {
          final err = await app.retryLastReply();
          if (err != null) onToast('Could not ask again');
        }),
      ]),
    );
  }
}

/// While Santosh works and no words have come yet: the mark breathing, the real step, and how long it has taken.
class _WorkingMark extends StatefulWidget {
  const _WorkingMark({super.key, required this.name, this.step});
  final String name;
  final String? step;
  @override
  State<_WorkingMark> createState() => _WorkingMarkState();
}

class _WorkingMarkState extends State<_WorkingMark> {
  final _t0 = DateTime.now();
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
    final step = (widget.step ?? '').trim();
    final label = step.isEmpty ? 'Thinking' : step;
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Semantics(
        liveRegion: true,
        label: '${widget.name} is working: $label',
        excludeSemantics: true,
        child: Row(children: [
          const HoolaMark(size: 24),   // v0.888 the thinking mark (tinted, orbits; still under reduce motion)
          const SizedBox(width: 10),
          Expanded(
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

/// "Thinking · 4s" while it thinks (the newest lines showing); "Thought for 8s ›" after, opens on a tap.
class _Thinking extends StatefulWidget {
  const _Thinking({super.key, required this.it, required this.name});
  final FeedItem it;
  final String name;
  @override
  State<_Thinking> createState() => _ThinkingState();
}

class _ThinkingState extends State<_Thinking> {
  Timer? _tick;
  bool _open = false;
  bool get _done => widget.it.data['done'] == true;

  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(covariant _Thinking old) {
    super.didUpdateWidget(old);
    _sync();
  }

  void _sync() {
    if (_done) {
      _tick?.cancel();
      _tick = null;
    } else {
      _tick ??= Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() {});
      });
    }
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final d = widget.it.data;
    final text = '${d['text'] ?? ''}'.trim();
    final t0 = (d['t0'] as num?)?.toInt() ?? DateTime.now().millisecondsSinceEpoch;
    final secs = _done
        ? ((d['secs'] as num?)?.toInt() ?? 1)
        : ((DateTime.now().millisecondsSinceEpoch - t0) / 1000).floor().clamp(0, 99999).toInt();
    final clock = secs < 60 ? '${secs}s' : '${secs ~/ 60}m ${(secs % 60).toString().padLeft(2, '0')}s';
    final head = _done ? 'Thought for $clock' : 'Thinking · $clock';
    final shown = !_done && text.length > 360 ? '…${text.substring(text.length - 360)}' : text;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        InkWell(
          onTap: _done && text.isNotEmpty ? () => setState(() => _open = !_open) : null,
          borderRadius: HoolaRadius.r(HoolaRadius.chip),
          child: Container(
            constraints: const BoxConstraints(minHeight: HoolaSpace.touch),   // R9: a 48 dp tap target
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.psychology_outlined, size: 17, color: c.ink3),
              const SizedBox(width: 6),
              Text(head, style: HoolaType.small(c).copyWith(color: c.ink2)),
              if (_done && text.isNotEmpty) Icon(_open ? Icons.expand_less_rounded : Icons.chevron_right_rounded, size: 18, color: c.ink3),
            ]),
          ),
        ),
        if ((!_done || _open) && shown.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 4, left: 8),
            padding: const EdgeInsets.only(left: 12),
            decoration: BoxDecoration(border: Border(left: BorderSide(color: c.line, width: 2))),
            constraints: BoxConstraints(maxHeight: _done ? 320 : 110),
            child: SingleChildScrollView(
              reverse: !_done,
              child: Text(shown, style: HoolaType.small(c).copyWith(height: 1.5)),
            ),
          ),
      ]),
    );
  }
}

/// The steps of a turn: the running step live; after, one line "Used 4 steps ›" that opens the Steps sheet.
class _StepsLine extends StatelessWidget {
  const _StepsLine({required this.it});
  final FeedItem it;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    // v0.863 R3s the server says which steps are Hoola's own housekeeping: they are not her work, not counted
    final steps = it.steps.where((s) => '${s['label'] ?? ''}'.trim().isNotEmpty && s['housekeeping'] != true).toList();
    if (steps.isEmpty) return const SizedBox.shrink();
    final running = steps.where((s) => s['state'] == 'running').toList();
    final failed = steps.where((s) => s['state'] == 'error' || s['state'] == 'failed').length;
    final n = steps.length;
    final label = running.isNotEmpty
        ? '${running.last['label']}'
        : 'Used $n ${n == 1 ? 'step' : 'steps'}${failed > 0 ? ' · $failed did not work' : ''}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Align(
        alignment: Alignment.centerLeft,
        child: InkWell(
          onTap: () => _sheet(context, steps),
          borderRadius: HoolaRadius.r(HoolaRadius.pill),
          child: Container(
            constraints: const BoxConstraints(minHeight: HoolaSpace.touch),   // R9: a 48 dp tap target
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.symmetric(vertical: 5, horizontal: 2),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              if (running.isNotEmpty)
                SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.8, color: c.accent))
              else
                Icon(stepIcon('${steps.last['label']}', kind: '${steps.last['kind'] ?? ''}'), size: 16, color: c.ink3),
              const SizedBox(width: 8),
              Flexible(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink2))),
              Icon(Icons.chevron_right_rounded, size: 18, color: c.ink3),
            ]),
          ),
        ),
      ),
    );
  }

  void _sheet(BuildContext context, List<Map<String, dynamic>> steps) => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        isScrollControlled: true,
        builder: (ctx) {
          final c = HoolaColors.of(ctx);
          return DraggableScrollableSheet(
            expand: false,
            initialChildSize: .5,
            maxChildSize: .9,
            builder: (ctx, scroll) => ListView(controller: scroll, padding: const EdgeInsets.fromLTRB(20, 0, 20, 24), children: [
              Text('Steps', style: HoolaType.heading(c)),
              const SizedBox(height: 12),
              for (var i = 0; i < steps.length; i++)
                _StepRow(step: steps[i], last: i == steps.length - 1),
            ]),
          );
        },
      );
}

class _StepRow extends StatelessWidget {
  const _StepRow({required this.step, required this.last});
  final Map<String, dynamic> step;
  final bool last;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final label = '${step['label'] ?? ''}';
    final state = '${step['state'] ?? ''}';
    final bad = state == 'error' || state == 'failed';
    final running = state == 'running';
    return IntrinsicHeight(
      child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Column(children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(color: bad ? c.badSoft : c.sunk, shape: BoxShape.circle),
            child: running
                ? Padding(padding: const EdgeInsets.all(8), child: CircularProgressIndicator(strokeWidth: 1.8, color: c.accent))
                : Icon(bad ? Icons.error_outline_rounded : stepIcon(label, kind: '${step['kind'] ?? ''}'), size: 16, color: bad ? c.bad : c.ink2),
          ),
          if (!last) Expanded(child: Container(width: 1.5, color: c.line)),
        ]),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 5, bottom: 16),
            child: Text(label, style: HoolaType.body(c).copyWith(color: bad ? c.bad : c.ink)),
          ),
        ),
      ]),
    );
  }
}

/// The icon of a step: from the kind the server sends (v0.863 R3s); an older server's step falls back to its words.
const _kindIcon = <String, IconData>{
  'search': Icons.search_rounded,
  'read': Icons.description_outlined,
  'write': Icons.edit_note_rounded,
  'edit': Icons.edit_outlined,
  'web': Icons.public_rounded,
  'run': Icons.terminal_rounded,
  'agent': Icons.groups_outlined,
  'skill': Icons.auto_awesome_outlined,
  'question': Icons.help_outline_rounded,
  'card': Icons.task_alt_rounded,
  'memory': Icons.bookmark_border_rounded,
};

IconData stepIcon(String label, {String kind = ''}) {
  final k = _kindIcon[kind];
  if (k != null) return k;
  final l = label.toLowerCase();
  bool any(List<String> w) => w.any(l.contains);
  if (any(['search', 'looking up', 'finding', 'khoj'])) return Icons.search_rounded;
  if (any(['mail', 'email', 'inbox'])) return Icons.mail_outline_rounded;
  if (any(['whatsapp', 'message', 'sms'])) return Icons.chat_bubble_outline_rounded;
  if (any(['calendar', 'meeting', 'reminder', 'schedule'])) return Icons.event_outlined;
  if (any(['web', 'website', 'page', 'browser', 'open'])) return Icons.public_rounded;
  if (any(['read', 'reading', 'file', 'pdf', 'drive', 'document'])) return Icons.description_outlined;
  if (any(['writ', 'draft', 'making', 'creat', 'build'])) return Icons.edit_outlined;
  if (any(['run', 'python', 'calculat', 'code'])) return Icons.terminal_rounded;
  if (any(['agent', 'team', 'helper'])) return Icons.groups_outlined;
  if (any(['memory', 'remember', 'yaad'])) return Icons.bookmark_border_rounded;
  if (any(['ask', 'question', 'approval', 'waiting'])) return Icons.help_outline_rounded;
  return Icons.bolt_outlined;
}

class _DayHead extends StatelessWidget {
  const _DayHead({required this.day});
  final DateTime day;
  static const _mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(day.year, day.month, day.day);
    final diff = today.difference(d).inDays;
    final text = diff == 0 ? 'Today' : diff == 1 ? 'Yesterday' : '${day.day} ${_mon[day.month - 1]}${day.year != now.year ? ' ${day.year}' : ''}';
    return Padding(
      padding: const EdgeInsets.only(top: 6, bottom: 14),
      child: Text(text, textAlign: TextAlign.center, style: HoolaType.label(c).copyWith(color: c.ink3)),
    );
  }
}

class _OlderButton extends StatelessWidget {
  const _OlderButton({required this.loading, required this.onTap});
  final bool loading;
  final Future<void> Function() onTap;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Center(
          child: loading
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : TextButton(onPressed: onTap, child: const Text('Show earlier messages')),
        ),
      );
}

class _NewestButton extends StatelessWidget {
  const _NewestButton({required this.count, required this.onTap});
  final int count;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: count > 0 ? '$count new, go to the newest' : 'Go to the newest message',
      excludeSemantics: true,
      child: Material(
        color: c.surface,
        shape: StadiumBorder(side: BorderSide(color: c.line)),
        elevation: 0,
        shadowColor: c.shadow,
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: count > 0 ? 14 : 10, vertical: 9),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.arrow_downward_rounded, size: 18, color: c.ink),
              if (count > 0) ...[const SizedBox(width: 6), Text('$count new', style: HoolaType.label(c).copyWith(color: c.ink))],
            ]),
          ),
        ),
      ),
    );
  }
}

/// An old card (Night Glass) in its own dark frame until R4 redraws the cards.
class _OldCard extends StatelessWidget {
  const _OldCard({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) {
    final old = santoshTheme();
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: ClipRRect(
        borderRadius: HoolaRadius.r(HoolaRadius.cardLg),
        child: Theme(
          data: old,
          child: ColoredBox(
            color: old.scaffoldBackgroundColor,
            child: Padding(padding: const EdgeInsets.fromLTRB(8, 8, 8, 0), child: child),
          ),
        ),
      ),
    );
  }
}

/// A reply that just arrived appears word by word at reading speed (34 ms a word, capped at 10 s), the newest
/// words lighter; history shows at once. Reduce motion = all at once.
class _Reveal extends StatefulWidget {
  const _Reveal({required this.text, required this.builder});
  final String text;
  final Widget Function(String text, bool live) builder;
  @override
  State<_Reveal> createState() => _RevealState();
}

class _RevealState extends State<_Reveal> with SingleTickerProviderStateMixin {
  late final List<String> _words = widget.text.split(RegExp(r'(?<=\s)'));
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: (_words.length * 34).clamp(300, 10000)),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (HoolaMotion.reduced(context)) {
      _c.value = 1;
    } else if (!_c.isAnimating && !_c.isCompleted) {
      _c.forward();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          if (_c.isCompleted) return widget.builder(widget.text, false);
          final n = (_words.length * Curves.easeOut.transform(_c.value)).ceil().clamp(1, _words.length);
          return Stack(children: [
            Opacity(opacity: 0, child: widget.builder(widget.text, false)),   // the full size, so nothing jumps
            widget.builder(_words.take(n).join(), true),
          ]);
        },
      );
}

/// v0.894 the page colour fading to clear: at the top it runs down, at the bottom it runs up.
class _Fade extends StatelessWidget {
  const _Fade(this.color, {required this.down});
  final Color color;
  final bool down;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: down ? Alignment.topCenter : Alignment.bottomCenter,
            end: down ? Alignment.bottomCenter : Alignment.topCenter,
            colors: [color, color.withOpacity(0)],
          ),
        ),
      );
}
