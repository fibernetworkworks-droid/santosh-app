// v0.928 HOOLA CODE CHAT LIKE HOOLA CHAT (owner: "Make all chat feature same as hoola chat... App... Everything"):
// Hoola Code's words now behave like a Hoola chat reply - the same renderer (headings, lists, tables, code blocks with
// Copy), Copy · Read aloud · Share under the newest reply, and the same long-press sheet on every message (Copy,
// Quote in my reply, Edit and send again for hers, Read aloud for Hoola's, Select text).
import 'dart:io';

import 'package:flutter/material.dart';
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
      this.onQuote, this.onSelect});
  final Santosh app;
  final String text;
  final bool actions;
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
          child: HoolaMd(text, selectable: selecting),
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
