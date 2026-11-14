// v0.908 CHAT MENU (owner: "NOW LETS WORK ON CHAT SIDE BAR -- EVERY CHAT NAME SHOULD WE EDITED, DELETED SAME AS CONSOLE
// HAS CHECK THE CONSOLE SIDE AND DEPLOY SAME HERE FOR SESSIONS"): the console's chat ⋯ menu (chatlist.js openMenu) on the
// phone - Pin / Unpin, Rename, Compact chat, Archive / Restore from archive, Delete (asks first) - on the same server
// routes (PATCH / DELETE /api/conversations/{id}, POST .../compact). Opened from the ⋯ beside every chat in the drawer
// or by holding the chat. The Archive list (the console's Archive at the bottom of its list) is one tap away in More.
import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';

String chatTitle(Map<String, dynamic> ch) {
  final t = '${ch['title'] ?? ''}'.trim();
  return t.isEmpty ? 'New chat' : t;
}

/// The menu for one chat. [onOpen] opens it (used by the Archive list, where a tap on the row does nothing else).
Future<void> hoolaChatMenu(BuildContext context, Santosh app, Map<String, dynamic> ch, {VoidCallback? onOpen}) async {
  final id = '${ch['id'] ?? ''}';
  if (id.isEmpty) return;
  final archived = ch['archived'] == true;
  final pinned = ch['pinned'] == true;
  final title = chatTitle(ch);
  final pick = await hoolaMenuSheet<String>(context, app, header: title, rows: (ctx, c) => [
        if (onOpen != null)
          _MenuRow(icon: Icons.chat_bubble_outline_rounded, label: 'Open', onTap: () => Navigator.pop(ctx, 'open')),
        if (!archived)
          _MenuRow(
            icon: pinned ? Icons.push_pin_rounded : Icons.push_pin_outlined,
            label: pinned ? 'Unpin' : 'Pin',
            onTap: () => Navigator.pop(ctx, 'pin'),
          ),
        _MenuRow(icon: Icons.edit_outlined, label: 'Rename', onTap: () => Navigator.pop(ctx, 'rename')),
        if (!archived)
          _MenuRow(icon: Icons.compress_rounded, label: 'Compact chat', onTap: () => Navigator.pop(ctx, 'compact')),
        _MenuRow(
          icon: archived ? Icons.unarchive_outlined : Icons.archive_outlined,
          label: archived ? 'Restore from archive' : 'Archive',
          onTap: () => Navigator.pop(ctx, 'archive'),
        ),
        Divider(height: 17, indent: 20, endIndent: 20, color: c.line),
        _MenuRow(icon: Icons.delete_outline_rounded, label: 'Delete', danger: true, onTap: () => Navigator.pop(ctx, 'delete')),
      ]);
  if (pick == null || !context.mounted) return;
  String? err;
  switch (pick) {
    case 'open':
      onOpen?.call();
      return;
    case 'pin':
      err = await app.pinChat(id, !pinned);
      if (err == null && context.mounted) _toast(context, pinned ? 'Unpinned.' : 'Pinned to the top.');
    case 'rename':
      final name = await hoolaRenameSheet(context, app, title);
      if (name == null || name == title || !context.mounted) return;
      err = await app.renameChat(id, name);
      if (err == null && context.mounted) _toast(context, 'Renamed.');
    case 'compact':
      try {
        final r = await app.api!.compactNow(id);
        if (context.mounted) _toast(context, r.isNotEmpty ? 'Older messages summarised - the chat has room again.' : 'Nothing to summarise yet.');
      } catch (e) {
        err = '$e';
      }
    case 'archive':
      err = await app.archiveChat(id, !archived);
      if (err == null && context.mounted) _toast(context, archived ? 'Chat restored.' : 'Chat archived.');
    case 'delete':
      final ok = await hoolaConfirmSheet(context, app,
          title: 'Delete "$title"?', body: 'It leaves the chat list, search and its link.', yes: 'Delete', danger: true);
      if (!ok || !context.mounted) return;
      err = await app.deleteChat(id);
      if (err == null && context.mounted) _toast(context, 'Chat deleted.');
  }
  if (err != null && context.mounted) _toast(context, err);
}

void _toast(BuildContext context, String text) {
  final m = ScaffoldMessenger.maybeOf(context);
  m?.hideCurrentSnackBar();
  m?.showSnackBar(SnackBar(content: Text(text), behavior: SnackBarBehavior.floating, duration: const Duration(seconds: 2)));
}

/// A Claude-style menu sheet: a handle, the chat's name, then the rows.
Future<T?> hoolaMenuSheet<T>(BuildContext context, Santosh app,
    {required String header, required List<Widget> Function(BuildContext ctx, HoolaColors c) rows}) {
  final c = HoolaColors.of(context);
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: c.surface,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => HoolaTheme(
      appearance: app.appearance,
      child: Builder(builder: (ctx) {
        final c = HoolaColors.of(ctx);
        return SafeArea(
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Center(
                child: Container(
                  width: 40,
                  height: 5,
                  margin: const EdgeInsets.only(top: 10, bottom: 6),
                  decoration: BoxDecoration(color: c.lineStrong, borderRadius: BorderRadius.circular(5)),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 10),
                child: Text(header, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.heading(c)),
              ),
              ...rows(ctx, c),
              const SizedBox(height: 8),
            ]),
          ),
        );
      }),
    ),
  );
}

class _MenuRow extends StatelessWidget {
  const _MenuRow({required this.icon, required this.label, required this.onTap, this.danger = false});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool danger;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final tint = danger ? c.bad : c.ink;
    return InkWell(
      onTap: onTap,
      child: SizedBox(
        height: 52,
        child: Row(children: [
          const SizedBox(width: 24),
          Icon(icon, size: 22, color: danger ? c.bad : c.ink2),
          const SizedBox(width: 18),
          Expanded(child: Text(label, style: HoolaType.bodyLarge(c).copyWith(color: tint))),
          const SizedBox(width: 24),
        ]),
      ),
    );
  }
}

/// The rename box: the old name selected, Save / Cancel; returns the new name (or null).
Future<String?> hoolaRenameSheet(BuildContext context, Santosh app, String current) {
  final c = HoolaColors.of(context);
  final box = TextEditingController(text: current)..selection = TextSelection(baseOffset: 0, extentOffset: current.length);
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: c.surface,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => HoolaTheme(
      appearance: app.appearance,
      child: Builder(builder: (ctx) {
        final c = HoolaColors.of(ctx);
        void save() {
          final t = box.text.trim();
          if (t.isNotEmpty) Navigator.pop(ctx, t);
        }
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(ctx).bottom),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('Rename chat', style: HoolaType.heading(c)),
                const SizedBox(height: 14),
                TextField(
                  controller: box,
                  autofocus: true,
                  maxLength: 120,
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => save(),
                  style: HoolaType.bodyLarge(c),
                  decoration: const InputDecoration(hintText: 'Chat name', counterText: ''),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: save,
                  style: FilledButton.styleFrom(
                      backgroundColor: c.pill,
                      foregroundColor: c.onPill,
                      shape: const StadiumBorder(),
                      minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                  child: const Text('Save'),
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                  child: const Text('Cancel'),
                ),
              ]),
            ),
          ),
        );
      }),
    ),
  );
}

/// Asks first (the console's confirm): a clear title, one line, the action and Cancel.
Future<bool> hoolaConfirmSheet(BuildContext context, Santosh app,
    {required String title, required String body, required String yes, bool danger = false}) async {
  final c = HoolaColors.of(context);
  final ok = await showModalBottomSheet<bool>(
    context: context,
    useSafeArea: true,
    backgroundColor: c.surface,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => HoolaTheme(
      appearance: app.appearance,
      child: Builder(builder: (ctx) {
        final c = HoolaColors.of(ctx);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(title, maxLines: 3, overflow: TextOverflow.ellipsis, style: HoolaType.heading(c)),
              const SizedBox(height: 8),
              Text(body, style: HoolaType.body(c).copyWith(color: c.ink2)),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                style: FilledButton.styleFrom(
                    backgroundColor: danger ? c.bad : c.pill,
                    foregroundColor: danger ? c.onAccent : c.onPill,
                    shape: const StadiumBorder(),
                    minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                child: Text(yes),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                child: const Text('Cancel'),
              ),
            ]),
          ),
        );
      }),
    ),
  );
  return ok == true;
}

/// The console's Archive list as a page: every archived chat, tap = its menu (Open / Rename / Restore / Delete).
class HoolaArchivePage extends StatefulWidget {
  const HoolaArchivePage({super.key, required this.app, required this.onOpenChat});
  final Santosh app;
  final ValueChanged<String> onOpenChat;
  @override
  State<HoolaArchivePage> createState() => _HoolaArchivePageState();
}

class _HoolaArchivePageState extends State<HoolaArchivePage> {
  List<Map<String, dynamic>>? _list;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final l = await widget.app.archivedChats();
    if (mounted) setState(() => _list = l);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final list = _list;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const SizedBox(width: 4),
            IconButton(tooltip: 'Back', onPressed: () => Navigator.of(context).maybePop(), icon: Icon(Icons.arrow_back_rounded, color: c.ink)),
            const SizedBox(width: 4),
            Expanded(child: Text('Archive', style: HoolaType.heading(c))),
          ]),
          Expanded(
            child: list == null
                ? Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3)))
                : list.isEmpty
                    ? Center(child: Text('Archive is empty.', style: HoolaType.body(c).copyWith(color: c.ink3)))
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4), children: [
                          for (final ch in list)
                            Material(
                              color: Colors.transparent,
                              child: InkWell(
                                borderRadius: HoolaRadius.r(HoolaRadius.tile),
                                onTap: () async {
                                  await hoolaChatMenu(context, widget.app, ch, onOpen: () {
                                    Navigator.of(context).maybePop();
                                    widget.onOpenChat('${ch['id']}');
                                  });
                                  _load();
                                },
                                child: SizedBox(
                                  height: 52,
                                  child: Row(children: [
                                    const SizedBox(width: 10),
                                    Icon(Icons.archive_outlined, size: 18, color: c.ink2),
                                    const SizedBox(width: 14),
                                    Expanded(
                                      child: Text(chatTitle(ch), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.bodyLarge(c)),
                                    ),
                                    Icon(Icons.more_horiz_rounded, size: 20, color: c.ink3),
                                    const SizedBox(width: 10),
                                  ]),
                                ),
                              ),
                            ),
                        ]),
                      ),
          ),
        ]),
      ),
    );
  }
}
