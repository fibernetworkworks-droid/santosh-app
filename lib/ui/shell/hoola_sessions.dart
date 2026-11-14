// v0.909 SESSIONS (owner: "ADD SESSIONS ALSO SAME AS CONSOLE"): the console's sessions (projects.js + chatlist.js
// session sections) on the phone. A session = a named folder of chats with an emoji, instructions every chat in it
// follows, its own memory notes (+ the "Use my main memory here" switch), files, and its chats. Same server routes
// (/api/projects, PATCH /api/conversations/{id} project_id, POST /api/conversations?project_id=).
//   HoolaSessionPage   - the console's session page
//   hoolaNewSession    - the console's "+ New session"
//   hoolaPickSession   - the chat menu's "Add to session" / "Change session"
import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_chat_menu.dart';

String sessionName(Map<String, dynamic> p) {
  final n = '${p['name'] ?? ''}'.trim();
  return n.isEmpty ? 'Session' : n;
}

String sessionEmoji(Map<String, dynamic> p) {
  final e = '${p['emoji'] ?? ''}'.trim();
  return e.isEmpty ? '📁' : e;
}

void _toast(BuildContext context, String text) {
  final m = ScaffoldMessenger.maybeOf(context);
  m?.hideCurrentSnackBar();
  m?.showSnackBar(SnackBar(content: Text(text), behavior: SnackBarBehavior.floating, duration: const Duration(seconds: 2)));
}

/// "+ New session": asks the name, makes it, returns its id (null when cancelled or refused).
Future<String?> hoolaNewSession(BuildContext context, Santosh app) async {
  final name = await hoolaRenameSheet(context, app, '',
      title: 'New session', hint: 'e.g. App design, Research, GST', action: 'Create');
  if (name == null || name.trim().isEmpty || !context.mounted) return null;
  try {
    final id = await app.createSession(name);
    if (context.mounted) _toast(context, 'Session created. Its instructions, files and chats live here.');
    return id;
  } catch (e) {
    if (context.mounted) _toast(context, '$e');
    return null;
  }
}

/// Move a chat into a session, to another one, or out of its session.
Future<void> hoolaPickSession(BuildContext context, Santosh app, Map<String, dynamic> ch) async {
  if (app.sessions.isEmpty) await app.refreshSessions();
  if (!context.mounted) return;
  final cur = '${ch['project_id'] ?? ''}';
  final pick = await hoolaMenuSheet<String>(context, app, header: cur.isEmpty ? 'Add to session' : 'Change session', rows: (ctx, c) => [
        for (final p in app.sessions)
          _PickRow(
            lead: Text(sessionEmoji(p), style: const TextStyle(fontSize: 20)),
            label: sessionName(p),
            on: p['id'] == cur,
            onTap: () => Navigator.pop(ctx, '${p['id']}'),
          ),
        _PickRow(lead: Icon(Icons.add_rounded, size: 22, color: c.ink2), label: 'New session', onTap: () => Navigator.pop(ctx, '+new')),
        if (cur.isNotEmpty) ...[
          Divider(height: 17, indent: 20, endIndent: 20, color: c.line),
          _PickRow(lead: Icon(Icons.logout_rounded, size: 22, color: c.ink2), label: 'Remove from session', onTap: () => Navigator.pop(ctx, '-')),
        ],
      ]);
  if (pick == null || !context.mounted) return;
  String? target = pick == '-' ? null : pick;
  if (pick == '+new') {
    target = await hoolaNewSession(context, app);
    if (target == null) return;
  }
  if ((target ?? '') == cur) return;
  final err = await app.moveChat('${ch['id']}', target);
  if (context.mounted) _toast(context, err ?? (target == null ? 'Chat moved out of the session.' : 'Chat moved into the session.'));
}

class _PickRow extends StatelessWidget {
  const _PickRow({required this.lead, required this.label, required this.onTap, this.on = false});
  final Widget lead;
  final String label;
  final VoidCallback onTap;
  final bool on;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      selected: on,
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          height: 52,
          child: Row(children: [
            const SizedBox(width: 24),
            SizedBox(width: 24, child: Center(child: lead)),
            const SizedBox(width: 18),
            Expanded(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.bodyLarge(c))),
            if (on) Icon(Icons.check_rounded, size: 20, color: c.ink),
            const SizedBox(width: 24),
          ]),
        ),
      ),
    );
  }
}

/// The console's session page: name + emoji, + New chat in this session, instructions, memory (+ the main-memory
/// switch), files, chats, Delete session.
class HoolaSessionPage extends StatefulWidget {
  const HoolaSessionPage({super.key, required this.app, required this.id, required this.onOpenChat});
  final Santosh app;
  final String id;
  final ValueChanged<String> onOpenChat;
  @override
  State<HoolaSessionPage> createState() => _HoolaSessionPageState();
}

class _HoolaSessionPageState extends State<HoolaSessionPage> {
  Map<String, dynamic>? _p;
  List<Map<String, dynamic>> _chats = const [];
  String? _error;
  final _instructions = TextEditingController();
  final _memory = TextEditingController();
  Timer? _debounce;
  String _saved = '';
  bool _uploading = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _instructions.dispose();
    _memory.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final p = await app.api!.session(widget.id);
      final chats = await app.api!.sessionChats(widget.id).catchError((_) => <Map<String, dynamic>>[]);
      if (!mounted) return;
      setState(() {
        _p = p;
        _chats = chats;
        _error = null;
        if (_instructions.text.isEmpty) _instructions.text = '${p['instructions'] ?? ''}';
        if (_memory.text.isEmpty) _memory.text = '${p['memory'] ?? ''}';
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  Future<bool> _save(Map<String, dynamic> patch, {String? field}) async {
    try {
      await app.api!.sessionPatch(widget.id, patch);
      if (mounted && field != null) {
        setState(() => _saved = field);
        Future.delayed(const Duration(milliseconds: 1400), () {
          if (mounted && _saved == field) setState(() => _saved = '');
        });
      }
      return true;
    } catch (e) {
      if (mounted) _toast(context, '$e');
      return false;
    }
  }

  void _typed(String field, String text) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 700), () => _save({field: text}, field: field));
  }

  Future<void> _rename() async {
    final p = _p;
    if (p == null) return;
    final name = await hoolaRenameSheet(context, app, sessionName(p), title: 'Rename session', hint: 'Session name');
    if (name == null || name == sessionName(p) || !mounted) return;
    if (await _save({'name': name})) {
      setState(() => p['name'] = name);
      unawaited(app.refreshSessions());
    }
  }

  Future<void> _emoji() async {
    final p = _p;
    if (p == null) return;
    final e = await hoolaRenameSheet(context, app, sessionEmoji(p), title: 'Session emoji', hint: 'One emoji, e.g. 💍 🧾 🏪', max: 8);
    if (e == null || e.trim().isEmpty || !mounted) return;
    if (await _save({'emoji': e.trim()})) {
      setState(() => p['emoji'] = e.trim());
      unawaited(app.refreshSessions());
    }
  }

  Future<void> _newChat() async {
    final err = await app.newChatIn(widget.id);
    if (!mounted) return;
    if (err != null) {
      _toast(context, err);
      return;
    }
    Navigator.of(context).maybePop();
    widget.onOpenChat('');
  }

  Future<void> _addFiles() async {
    final res = await FilePicker.platform.pickFiles(allowMultiple: true, withData: true);
    if (res == null || !mounted) return;
    setState(() => _uploading = true);
    for (final f in res.files.take(10)) {
      final bytes = f.bytes;
      if (bytes == null) continue;
      if (bytes.length > 25 * 1024 * 1024) {
        if (mounted) _toast(context, '${f.name}: files over 25 MB are not supported.');
        continue;
      }
      try {
        await app.api!.sessionFileAdd(widget.id, f.name, bytes);
        if (mounted) _toast(context, '${f.name} added to the session.');
      } catch (e) {
        if (mounted) _toast(context, '${f.name}: $e');
      }
    }
    if (mounted) setState(() => _uploading = false);
    _load();
  }

  Future<void> _removeFile(Map<String, dynamic> f) async {
    final ok = await hoolaConfirmSheet(context, app,
        title: 'Remove ${f['name']}?', body: 'Remove this file from the session?', yes: 'Remove', danger: true);
    if (!ok || !mounted) return;
    try {
      await app.api!.sessionFileRemove(widget.id, '${f['id']}');
    } catch (e) {
      if (mounted) _toast(context, '$e');
    }
    _load();
  }

  Future<void> _delete() async {
    final p = _p;
    if (p == null) return;
    final ok = await hoolaConfirmSheet(context, app,
        title: 'Delete the "${sessionName(p)}" session?',
        body: 'Its chats stay; they just leave the session.',
        yes: 'Delete session',
        danger: true);
    if (!ok || !mounted) return;
    final err = await app.deleteSession(widget.id);
    if (!mounted) return;
    _toast(context, err ?? 'Session deleted.');
    if (err == null) Navigator.of(context).maybePop();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final p = _p;
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const SizedBox(width: 4),
            IconButton(tooltip: 'Back', onPressed: () => Navigator.of(context).maybePop(), icon: Icon(Icons.arrow_back_rounded, color: c.ink)),
            const Spacer(),
            if (p != null)
              IconButton(tooltip: 'Delete session', onPressed: _delete, icon: Icon(Icons.delete_outline_rounded, color: c.ink2)),
            const SizedBox(width: 4),
          ]),
          Expanded(
            child: p == null
                ? Center(
                    child: _error != null
                        ? Padding(padding: const EdgeInsets.all(24), child: Text(_error!, style: HoolaType.body(c).copyWith(color: c.ink2)))
                        : SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3)),
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView(padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 4, HoolaSpace.gutter, 32), children: [
                      Row(children: [
                        Semantics(
                          button: true,
                          label: 'Change emoji',
                          excludeSemantics: true,
                          child: InkWell(
                            onTap: _emoji,
                            borderRadius: HoolaRadius.r(14),
                            child: Container(
                              width: 52,
                              height: 52,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(14)),
                              child: Text(sessionEmoji(p), style: const TextStyle(fontSize: 26)),
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Semantics(
                            button: true,
                            label: 'Rename session: ${sessionName(p)}',
                            excludeSemantics: true,
                            child: InkWell(
                              onTap: _rename,
                              borderRadius: HoolaRadius.r(10),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(vertical: 6),
                                child: Row(children: [
                                  Flexible(
                                    child: Text(sessionName(p), maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.hero(c)),
                                  ),
                                  const SizedBox(width: 8),
                                  Icon(Icons.edit_outlined, size: 18, color: c.ink3),
                                ]),
                              ),
                            ),
                          ),
                        ),
                      ]),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: _newChat,
                        icon: const Icon(Icons.add_rounded, size: 20),
                        label: const Text('New chat in this session'),
                        style: FilledButton.styleFrom(
                          backgroundColor: c.pill,
                          foregroundColor: c.onPill,
                          shape: const StadiumBorder(),
                          minimumSize: const Size.fromHeight(HoolaSpace.touchMain),
                        ),
                      ),
                      const SizedBox(height: 24),
                      _block(c, 'Instructions', 'every chat', '${app.aName} follows these in every chat of this session '
                          '(for example "Budget 5 lakh", "Always reply in Hindi").', saved: _saved == 'instructions',
                          child: _area(c, _instructions, 'What should ${app.aName} know about this work?', (t) => _typed('instructions', t))),
                      const SizedBox(height: 16),
                      _block(c, 'Memory', 'notes', 'Key facts for this work: names, dates, decisions.', saved: _saved == 'memory',
                          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                            _area(c, _memory, 'Venue: Pune, 12 Dec · Caterer: Sharma ji', (t) => _typed('memory', t)),
                            const SizedBox(height: 8),
                            SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              value: p['use_main_memory'] != false,
                              onChanged: (v) async {
                                setState(() => p['use_main_memory'] = v);
                                if (!await _save({'use_main_memory': v}) && mounted) setState(() => p['use_main_memory'] = !v);
                              },
                              activeColor: c.onPill,
                              activeTrackColor: c.pill,
                              title: Text('Use my main memory here', style: HoolaType.bodyLarge(c).copyWith(fontWeight: FontWeight.w600)),
                              subtitle: Text(
                                  "Off: chats in this session use only this session's own memory (its facts and chats), never your "
                                  'other facts or your memory page. Pinned facts still apply.',
                                  style: HoolaType.small(c).copyWith(color: c.ink2)),
                            ),
                          ])),
                      const SizedBox(height: 16),
                      _block(c, 'Files', '${(p['file_list'] as List?)?.length ?? p['files'] ?? 0}',
                          'Up to 25 MB each; big files are searched through Gyaan.',
                          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                            for (final f in ((p['file_list'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)))
                              _fileRow(c, f),
                            const SizedBox(height: 6),
                            OutlinedButton.icon(
                              onPressed: _uploading ? null : _addFiles,
                              icon: _uploading
                                  ? SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3))
                                  : const Icon(Icons.attach_file_rounded, size: 18),
                              label: Text(_uploading ? 'Adding…' : 'Add files'),
                            ),
                          ])),
                      const SizedBox(height: 16),
                      _block(c, 'Chats', '${_chats.length}', '',
                          child: _chats.isEmpty
                              ? Text('No conversations yet. Press "New chat in this session".', style: HoolaType.body(c).copyWith(color: c.ink3))
                              : Column(children: [
                                  for (final ch in _chats)
                                    InkWell(
                                      borderRadius: HoolaRadius.r(HoolaRadius.tile),
                                      onTap: () {
                                        Navigator.of(context).maybePop();
                                        widget.onOpenChat('${ch['id']}');
                                      },
                                      child: SizedBox(
                                        height: 48,
                                        child: Row(children: [
                                          Icon(Icons.chat_bubble_outline_rounded, size: 18, color: c.ink2),
                                          const SizedBox(width: 14),
                                          Expanded(
                                            child: Text(chatTitle(ch), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.bodyLarge(c)),
                                          ),
                                          Icon(Icons.chevron_right_rounded, size: 18, color: c.ink3),
                                        ]),
                                      ),
                                    ),
                                ])),
                    ]),
                  ),
          ),
        ]),
      ),
    );
  }

  Widget _block(HoolaColors c, String title, String tag, String note, {required Widget child, bool saved = false}) => Container(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        decoration: BoxDecoration(color: c.surface, borderRadius: HoolaRadius.r(18), border: Border.all(color: c.line)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Text(title, style: HoolaType.title(c)),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
              child: Text(tag, style: HoolaType.label(c)),
            ),
            const Spacer(),
            AnimatedOpacity(
              opacity: saved ? 1 : 0,
              duration: HoolaMotion.of(context, HoolaMotion.fade),
              child: Text('Saved', style: HoolaType.label(c).copyWith(color: c.ok)),
            ),
          ]),
          if (note.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(note, style: HoolaType.small(c).copyWith(color: c.ink2)),
          ],
          const SizedBox(height: 12),
          child,
        ]),
      );

  Widget _area(HoolaColors c, TextEditingController box, String hint, ValueChanged<String> onChanged) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(14)),
        child: TextField(
          controller: box,
          minLines: 3,
          maxLines: 8,
          maxLength: 8000,
          onChanged: onChanged,
          style: HoolaType.body(c),
          decoration: InputDecoration.collapsed(hintText: hint, hintStyle: HoolaType.body(c).copyWith(color: c.ink3))
              .copyWith(counterText: ''),
        ),
      );

  Widget _fileRow(HoolaColors c, Map<String, dynamic> f) {
    final kb = ((f['size'] as num? ?? 0) / 1024).round().clamp(1, 1 << 30);
    return SizedBox(
      height: 44,
      child: Row(children: [
        Icon(Icons.description_outlined, size: 18, color: c.ink2),
        const SizedBox(width: 12),
        Expanded(child: Text('${f['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c))),
        Text('$kb KB', style: HoolaType.small(c)),
        IconButton(
          tooltip: 'Remove ${f['name']}',
          onPressed: () => _removeFile(f),
          icon: Icon(Icons.close_rounded, size: 18, color: c.ink3),
        ),
      ]),
    );
  }
}
