import 'dart:async';

import 'package:flutter/material.dart';

/// v0.179 Keyboard-safe field wrapper for chat cards: she taps a field inside a card (an AI form in the chat
/// feed, in the call's card tray, in the waiting sheet), the keyboard rises, the list shrinks — and the field
/// she is typing in used to stay hidden behind the keyboard. [KbField] scrolls the field back into view:
/// the moment the keyboard starts rising (viewInsets change) and again when focus lands while it is already up.
class KbField extends StatefulWidget {
  const KbField({super.key, required this.child, this.alignment = 0.3});
  final Widget child;

  /// 0 = try to sit at the very top of the visible list, 1 = bottom. ~0.3 keeps the field comfortably
  /// above the keyboard with its label and a couple of the next fields in sight.
  final double alignment;

  @override
  State<KbField> createState() => _KbFieldState();
}

class _KbFieldState extends State<KbField> {
  double _lastInset = 0;
  Timer? _timer;
  bool _focused = false;

  void _reveal() {
    final ctx = context;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !ctx.mounted) return;
      Scrollable.ensureVisible(ctx,
          duration: const Duration(milliseconds: 280), curve: Curves.easeOutCubic, alignment: widget.alignment);
    });
  }

  void _onFocus(bool got) {
    _focused = got;
    if (!got) return;
    _timer?.cancel();
    // focus usually lands while the keyboard is still rising: the inset watcher below fires too,
    // this slow tick is the net for keyboards that report no inset change (or a second tap, same height).
    _timer = Timer(const Duration(milliseconds: 480), () {
      if (mounted && _focused) _reveal();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final inset = MediaQuery.viewInsetsOf(context).bottom;
    if (inset > _lastInset + 8 && _focused) _reveal();   // the keyboard is rising under a field she tapped
    _lastInset = inset;
    return Focus(
      canRequestFocus: false,
      skipTraversal: true,
      onFocusChange: _onFocus,   // fires when this field's subtree takes (or loses) focus
      child: widget.child,
    );
  }
}
