import 'dart:async';

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.232 PHASE C (fix 6 of the long-task report): the Soch card on the phone, matching the console.
/// While Hoola thinks the card is open with a ticking clock and the newest lines of its thinking; when the reply is
/// over it folds to "<name> ne socha · 8s" and opens again on a tap. Thoughts are never saved on the server, so this
/// card lives only on the open screen.
class ThinkCard extends StatefulWidget {
  const ThinkCard({super.key, required this.it, required this.name});
  final FeedItem it;
  final String name;

  @override
  State<ThinkCard> createState() => _ThinkCardState();
}

class _ThinkCardState extends State<ThinkCard> {
  Timer? _tick;
  bool _open = false;

  bool get _done => widget.it.data['done'] == true;

  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(covariant ThinkCard old) {
    super.didUpdateWidget(old);
    _sync();
  }

  void _sync() {
    if (_done) {
      _tick?.cancel();
      _tick = null;
    } else {
      _tick ??= Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted || _done) {
          _tick?.cancel();
          _tick = null;
        }
        if (mounted) setState(() {});
      });
    }
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  static String clock(int s) => s < 60 ? '${s}s' : '${s ~/ 60}m${(s % 60).toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final d = widget.it.data;
    final text = '${d['text'] ?? ''}'.trim();
    final t0 = (d['t0'] as num?)?.toInt() ?? DateTime.now().millisecondsSinceEpoch;
    final secs = _done
        ? ((d['secs'] as num?)?.toInt() ?? 1)
        : ((DateTime.now().millisecondsSinceEpoch - t0) / 1000).floor().clamp(0, 99999).toInt();
    final showText = !_done || _open;
    // live: only the newest part, so the card stays small; folded and opened: all of it
    final shown = !_done && text.length > 420 ? '…${text.substring(text.length - 420)}' : text;
    final head = _done ? '${widget.name} ne socha · ${clock(secs)}' : 'Soch raha hoon · ${clock(secs)}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Align(
        alignment: Alignment.centerLeft,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .82),
          child: Semantics(
            button: _done,
            label: head,
            child: Press(
              onTap: _done ? () => setState(() => _open = !_open) : null,
              child: Glass(
                flat: true,
                radius: 16,
                tint: C.violet,
                opacity: .05,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(_done ? Icons.psychology_outlined : Icons.psychology_rounded, size: 16, color: _done ? C.faint : C.accentSoft),
                    const SizedBox(width: 6),
                    Flexible(child: Text(head, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _done ? C.faint : C.muted))),
                    if (_done) ...[
                      const SizedBox(width: 4),
                      Icon(_open ? Icons.expand_less_rounded : Icons.expand_more_rounded, size: 16, color: C.faint),
                    ],
                  ]),
                  if (showText && shown.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    ConstrainedBox(
                      constraints: BoxConstraints(maxHeight: _done ? 320 : 120),
                      child: SingleChildScrollView(
                        reverse: !_done,           // live: the newest line stays in view
                        child: Text(shown, style: const TextStyle(fontSize: 12.5, height: 1.45, fontStyle: FontStyle.italic, color: C.faint)),
                      ),
                    ),
                  ],
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
