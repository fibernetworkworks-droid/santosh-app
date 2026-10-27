// v0.155 Hoola Notebook = NotebookLM on the phone: notebooks, Sources (files, photos, audio, recordings, links,
// YouTube, Drive, pasted text, Discover + Deep research), Chat with [n] citations, Configure chat, Studio (Audio /
// Video Overview, Slides, Infographic, Mind map, Reports, Flashcards, Quiz, Data table) in 39 languages, and Notes.
import 'dart:async';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import '../voice_recorder.dart';
import 'glass.dart';
import 'notebook_viewers.dart';

Color nbColor(Object? hex) {
  final h = '${hex ?? ''}'.replaceFirst('#', '');
  final v = int.tryParse(h.length == 6 ? 'FF$h' : h, radix: 16);
  return v == null ? C.violet : Color(v);
}

const _kindIcon = {
  'web': Icons.language_rounded, 'youtube': Icons.smart_display_rounded, 'text': Icons.notes_rounded,
  'drive': Icons.add_to_drive_rounded, 'sheet': Icons.table_chart_rounded, 'image': Icons.image_rounded,
  'audio': Icons.graphic_eq_rounded, 'email': Icons.mail_rounded, 'note': Icons.sticky_note_2_rounded,
  'research': Icons.travel_explore_rounded, 'pdf': Icons.picture_as_pdf_rounded,
};
IconData nbKindIcon(String k) => _kindIcon[k] ?? Icons.description_rounded;

const _studioTiles = [
  ('audio', 'Audio Overview', Icons.podcasts_rounded, Color(0xFF7C5CFF)),
  ('video', 'Video Overview', Icons.movie_creation_rounded, Color(0xFFE0458B)),
  ('slides', 'Slide deck', Icons.slideshow_rounded, Color(0xFFFF7A59)),
  ('infographic', 'Infographic', Icons.insert_chart_rounded, Color(0xFF00B3A4)),
  ('mind_map', 'Mind map', Icons.account_tree_rounded, Color(0xFF2F80ED)),
  ('report', 'Reports', Icons.article_rounded, Color(0xFFF2A900)),
  ('flashcards', 'Flashcards', Icons.style_rounded, Color(0xFF27AE60)),
  ('quiz', 'Quiz', Icons.quiz_rounded, Color(0xFF9B51E0)),
  ('table', 'Data table', Icons.grid_on_rounded, Color(0xFF2DD4BF)),
];
final _kindLabel = {for (final t in _studioTiles) t.$1: t.$2};
IconData nbStudioIcon(String k) =>
    k == 'research' ? Icons.travel_explore_rounded : _studioTiles.firstWhere((t) => t.$1 == k, orElse: () => _studioTiles[5]).$3;

// ================================================================ chat cards
/// Chat card: a notebook was made / changed by Hoola.
class NotebookCard extends StatelessWidget {
  const NotebookCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'created';
    final noteTitle = v['note_title'] as String?;
    final id = (v['id'] ?? v['notebook_id']) as String?;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Text(v['emoji'] as String? ?? '📒', style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 8),
            Expanded(child: Text(v['title'] as String? ?? 'Notebook', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(status == 'note' ? 'NAYA NOTE' : status == 'updated' ? 'SOURCES JUDE' : 'NOTEBOOK', fg: C.teal),
          ]),
          if (v['sources'] != null)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('${v['sources']} sources', style: const TextStyle(color: C.muted, fontSize: 12.5))),
          if (noteTitle != null) ...[
            const SizedBox(height: 6),
            Text(noteTitle, style: const TextStyle(fontWeight: FontWeight.w600)),
            Text(v['preview'] as String? ?? '', maxLines: 5, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: C.chip, fontSize: 13, height: 1.35)),
          ],
          const SizedBox(height: 10),
          if (id != null)
            GlassButton(label: 'Notebook kholiye', icon: Icons.menu_book_rounded, height: 42, onTap: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: app, id: id)));
            }),
        ]),
      ),
    );
  }
}

/// Chat / call card: one Studio item being made (live progress) or ready (open it).
class NotebookOutputCard extends StatelessWidget {
  const NotebookOutputCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final st = v['status'] as String? ?? 'queued';
    final kind = v['kind'] as String? ?? '';
    final nid = v['notebook_id'] as String? ?? '';
    final pct = ((v['pct'] as num?) ?? 0).toDouble();
    final cover = v['cover'] as String? ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Container(
              width: 40, height: 40,
              decoration: BoxDecoration(color: C.violet.withOpacity(.25), borderRadius: BorderRadius.circular(12)),
              child: Icon(nbStudioIcon(kind), color: C.accentSoft),
            ),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${v['emoji'] ?? '📒'} ${v['notebook'] ?? 'Notebook'} · ${v['label'] ?? _kindLabel[kind] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
              Text(v['title'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            ])),
            Pill(st == 'ready' ? 'TAIYAAR' : st == 'failed' ? 'NAHI BANA' : 'BAN RAHA',
                fg: st == 'ready' ? C.ok : st == 'failed' ? C.bad : C.accent),
          ]),
          if (st == 'queued' || st == 'working') ...[
            const SizedBox(height: 10),
            LinearProgressIndicator(value: pct > 0 ? pct / 100 : null, color: C.accent, backgroundColor: C.panel, minHeight: 6,
                borderRadius: BorderRadius.circular(4)),
            const SizedBox(height: 6),
            Text('${v['stage'] ?? 'Line mein'}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ],
          if (st == 'failed')
            Padding(padding: const EdgeInsets.only(top: 8), child: Text('${v['error'] ?? ''}', style: const TextStyle(color: C.bad, fontSize: 13))),
          if (st == 'ready' && cover.isNotEmpty) ...[
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Image.network(app.api!.absolute(cover), height: 150, fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const SizedBox.shrink()),
            ),
          ],
          const SizedBox(height: 10),
          Row(children: [
            if (st == 'ready')
              Expanded(child: GradientButton(label: 'Kholiye', icon: Icons.play_arrow_rounded, height: 44,
                  onTap: () => openNbOutput(context, app, nid, v))),
            if (st == 'ready') const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Notebook', icon: Icons.menu_book_rounded, height: 44, onTap: nid.isEmpty ? null : () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: app, id: nid, tab: 2)));
            })),
          ]),
        ]),
      ),
    );
  }
}

// ================================================================ list of notebooks
/// Profile > Hoola Notebook: all notebooks.
class NotebooksScreen extends StatefulWidget {
  const NotebooksScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<NotebooksScreen> createState() => _NotebooksScreenState();
}

class _NotebooksScreenState extends State<NotebooksScreen> {
  List<Map<String, dynamic>>? _list;
  String? _err;
  late int _tick = widget.app.notebookTick;

  @override
  void initState() {
    super.initState();
    widget.app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    widget.app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (widget.app.notebookTick != _tick) {
      _tick = widget.app.notebookTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final l = await widget.app.api!.notebooks();
      if (mounted) setState(() {
        _list = l;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _create() async {
    final t = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nayi notebook'),
        content: TextField(controller: t, autofocus: true, decoration: const InputDecoration(hintText: 'Naam (khaali chhodo: sources se ban jayega)')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, t.text.trim().isEmpty ? 'Nayi notebook' : t.text.trim()), child: const Text('Banao')),
        ],
      ),
    );
    if (name == null) return;
    try {
      final nb = await widget.app.api!.notebookCreate(name);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: widget.app, id: nb['id'] as String, addFirst: true)));
      _load();
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
    }
  }

  Future<void> _menu(Map<String, dynamic> nb) async {
    final a = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(leading: const Icon(Icons.edit_rounded), title: const Text('Naam badlo'), onTap: () => Navigator.pop(context, 'rename')),
        ListTile(leading: const Icon(Icons.copy_rounded), title: const Text('Copy banao'), onTap: () => Navigator.pop(context, 'copy')),
        ListTile(leading: const Icon(Icons.delete_outline_rounded, color: C.bad), title: const Text('Delete'), onTap: () => Navigator.pop(context, 'delete')),
      ])),
    );
    if (a == null || !mounted) return;
    await nbNotebookAction(context, widget.app, nb, a);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final l = _list;
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola Notebook'), backgroundColor: Colors.transparent),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: C.accent,
        foregroundColor: C.onAccent,
        onPressed: _create,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Nayi notebook', style: TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: l == null
              ? ListView(children: [
                  const SizedBox(height: 120),
                  Center(child: _err != null ? Text(_err!, style: const TextStyle(color: C.bad)) : const CircularProgressIndicator()),
                ])
              : l.isEmpty
                  ? ListView(padding: const EdgeInsets.all(24), children: [
                      const SizedBox(height: 40),
                      const Text('📒', textAlign: TextAlign.center, style: TextStyle(fontSize: 64)),
                      const SizedBox(height: 12),
                      Text('Apni pehli notebook banaiye', textAlign: TextAlign.center, style: display(22)),
                      const SizedBox(height: 10),
                      const Text('PDF, photo, audio, website, YouTube ya Drive file daaliye. Hoola sirf unhi se jawab dega (har baat ka '
                          'source [1] ke saath), aur ek tap mein podcast, video, slides, mind map, quiz, flashcards bana dega: '
                          'Hindi, Marathi, Tamil ya 39 bhashaon mein.',
                          textAlign: TextAlign.center, style: TextStyle(color: C.muted, height: 1.45)),
                      const SizedBox(height: 24),
                      GradientButton(label: 'Notebook banao', icon: Icons.add_rounded, onTap: _create),
                    ])
                  : GridView.builder(
                      padding: const EdgeInsets.fromLTRB(14, 8, 14, 100),
                      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent: 260, mainAxisExtent: 196,
                          crossAxisSpacing: 12, mainAxisSpacing: 12),
                      itemCount: l.length,
                      itemBuilder: (_, i) {
                        final nb = l[i];
                        final col = nbColor(nb['color']);
                        return Press(
                          onTap: () async {
                            await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: widget.app, id: nb['id'] as String)));
                            _load();
                          },
                          child: GestureDetector(
                            onLongPress: () => _menu(nb),
                            child: Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(22),
                                gradient: LinearGradient(colors: [col.withOpacity(.55), col.withOpacity(.18)],
                                    begin: Alignment.topLeft, end: Alignment.bottomRight),
                                border: Border.all(color: col.withOpacity(.6)),
                              ),
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Row(children: [
                                  Text(nb['emoji'] as String? ?? '📒', style: const TextStyle(fontSize: 30)),
                                  const Spacer(),
                                  InkWell(onTap: () => _menu(nb), child: const Icon(Icons.more_vert_rounded, color: C.ink)),
                                ]),
                                const SizedBox(height: 8),
                                Text(nb['title'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, height: 1.2)),
                                const SizedBox(height: 4),
                                Expanded(child: Text(nb['overview'] as String? ?? '', maxLines: 3, overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(color: C.chip, fontSize: 12, height: 1.3))),
                                Text('${nb['sources']} sources · ${nb['outputs']} Studio · ${(nb['updated'] as String? ?? '').replaceFirst('T', ' ')}',
                                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 11.5)),
                              ]),
                            ),
                          ),
                        );
                      },
                    ),
        ),
      ),
    );
  }
}

/// rename / copy / delete one notebook (list menu and the detail app bar). Returns true when it changed.
Future<bool> nbNotebookAction(BuildContext context, Santosh app, Map<String, dynamic> nb, String a) async {
  final api = app.api!;
  final id = nb['id'] as String;
  try {
    if (a == 'rename') {
      final t = TextEditingController(text: nb['title'] as String? ?? '');
      String emoji = nb['emoji'] as String? ?? '📒';
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(builder: (ctx, set) => AlertDialog(
              title: const Text('Naam aur nishaan'),
              content: Column(mainAxisSize: MainAxisSize.min, children: [
                TextField(controller: t, autofocus: true),
                const SizedBox(height: 12),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final e in const ['📒', '📘', '📗', '📕', '📙', '🧠', '🔬', '📊', '💼', '🎓', '⚖️', '🏥', '🌾', '🏗️', '📡', '💡'])
                    GestureDetector(
                      onTap: () => set(() => emoji = e),
                      child: Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: emoji == e ? C.accent : Colors.transparent, width: 2)),
                        child: Text(e, style: const TextStyle(fontSize: 22)),
                      ),
                    ),
                ]),
              ]),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
                FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
              ],
            )),
      );
      if (ok != true) return false;
      await api.notebookPatch(id, title: t.text.trim(), emoji: emoji);
      return true;
    }
    if (a == 'copy') {
      await api.notebookCopy(id);
      if (context.mounted) nbSnack(context, 'Copy ban gayi (sources aur notes ke saath)');
      return true;
    }
    if (a == 'delete') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('"${nb['title']}" delete karein?'),
          content: const Text('Sources, chat, notes aur Studio ki saari files hamesha ke liye hat jayengi.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Nahi')),
            FilledButton(style: FilledButton.styleFrom(backgroundColor: C.bad), onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
          ],
        ),
      );
      if (ok != true) return false;
      await api.notebookDelete(id);
      return true;
    }
  } catch (e) {
    if (context.mounted) nbSnack(context, '$e');
  }
  return false;
}

// ================================================================ one notebook
class NotebookDetailScreen extends StatefulWidget {
  const NotebookDetailScreen({super.key, required this.app, required this.id, this.tab = 1, this.addFirst = false});
  final Santosh app;
  final String id;
  final int tab;
  final bool addFirst;
  @override
  State<NotebookDetailScreen> createState() => _NotebookDetailScreenState();
}

class _NotebookDetailScreenState extends State<NotebookDetailScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 3, vsync: this, initialIndex: widget.tab);
  Map<String, dynamic>? _d;
  Map<String, dynamic> _cat = {};
  String? _err;
  Timer? _poll;
  late int _tick = widget.app.notebookTick;
  final _chatKey = GlobalKey<_ChatTabState>();

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.addListener(_onApp);
    _load().then((_) {
      if (widget.addFirst && mounted && (_d?['sources'] as List? ?? const []).isEmpty) {
        _tabs.index = 0;
        nbAddSourceSheet(context, app, widget.id, _load, _startResearch);
      }
    });
    app.api!.notebookCatalogue().then((c) {
      if (mounted) setState(() => _cat = c);
    }).catchError((Object _) {});
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _poll?.cancel();
    _tabs.dispose();
    super.dispose();
  }

  void _onApp() {
    if (app.notebookTick != _tick) {
      _tick = app.notebookTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.notebook(widget.id);
      if (!mounted) return;
      setState(() {
        _d = d;
        _err = null;
      });
      final busy = nbList(d['outputs']).any((o) => o['status'] == 'queued' || o['status'] == 'working');
      _poll?.cancel();
      if (busy) _poll = Timer(const Duration(seconds: 4), _load);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _startResearch(String q) async {
    try {
      await app.api!.notebookStudio(widget.id, 'research', {'query': q}, conv: app.conversationId ?? '');
      if (mounted) {
        nbSnack(context, 'Deep research shuru: web padh kar report banega aur source ban jayega (kuch minute).');
        _tabs.index = 2;
      }
      _load();
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
    }
  }

  void askInChat(String q) {
    _tabs.index = 1;
    Future.delayed(const Duration(milliseconds: 250), () => _chatKey.currentState?.send(q));
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final srcs = nbList(d?['sources']);
    final on = srcs.where((s) => s['enabled'] == true).length;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Row(children: [
          Text(d?['emoji'] as String? ?? '📒', style: const TextStyle(fontSize: 22)),
          const SizedBox(width: 8),
          Expanded(child: Text(d?['title'] as String? ?? 'Notebook', maxLines: 1, overflow: TextOverflow.ellipsis)),
        ]),
        actions: [
          PopupMenuButton<String>(
            onSelected: (a) async {
              if (d == null) return;
              final changed = await nbNotebookAction(context, app, d, a);
              if (!mounted) return;
              if (a == 'delete' && changed) {
                Navigator.pop(context);
              } else {
                _load();
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'rename', child: Text('Naam / nishaan badlo')),
              PopupMenuItem(value: 'copy', child: Text('Copy banao')),
              PopupMenuItem(value: 'delete', child: Text('Delete')),
            ],
          ),
        ],
        bottom: TabBar(
          controller: _tabs,
          indicatorColor: C.accent,
          labelColor: C.accent,
          unselectedLabelColor: C.muted,
          tabs: [
            Tab(text: 'Sources ($on/${srcs.length})'),
            const Tab(text: 'Chat'),
            const Tab(text: 'Studio'),
          ],
        ),
      ),
      body: Aurora(
        child: d == null
            ? Center(child: _err != null ? Padding(padding: const EdgeInsets.all(24), child: Text(_err!, style: const TextStyle(color: C.bad)))
                : const CircularProgressIndicator())
            : TabBarView(controller: _tabs, children: [
                _SourcesTab(app: app, id: widget.id, d: d, reload: _load, research: _startResearch, ask: askInChat),
                _ChatTab(key: _chatKey, app: app, id: widget.id, d: d, reload: _load, openSources: () => _tabs.index = 0),
                _StudioTab(app: app, id: widget.id, d: d, cat: _cat, reload: _load, ask: askInChat),
              ]),
      ),
    );
  }
}

// ================================================================ Sources
class _SourcesTab extends StatelessWidget {
  const _SourcesTab({required this.app, required this.id, required this.d, required this.reload, required this.research, required this.ask});
  final Santosh app;
  final String id;
  final Map<String, dynamic> d;
  final Future<void> Function() reload;
  final Future<void> Function(String) research;
  final void Function(String) ask;

  Future<void> _toggle(BuildContext context, List<String>? ids, bool on, {bool only = false}) async {
    try {
      await app.api!.notebookSelect(id, ids, on, only: only);
      await reload();
    } catch (e) {
      if (context.mounted) nbSnack(context, '$e');
    }
  }

  Future<void> _menu(BuildContext context, Map<String, dynamic> s) async {
    final a = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(title: Text(s['title'] as String? ?? '', maxLines: 2, style: const TextStyle(fontWeight: FontWeight.w700))),
        ListTile(leading: const Icon(Icons.filter_1_rounded), title: const Text('Sirf yahi source chuno'), onTap: () => Navigator.pop(ctx, 'only')),
        ListTile(leading: const Icon(Icons.edit_rounded), title: const Text('Naam badlo'), onTap: () => Navigator.pop(ctx, 'rename')),
        if (s['refreshable'] == true)
          ListTile(leading: const Icon(Icons.sync_rounded), title: const Text('Naya version laao (sync)'), onTap: () => Navigator.pop(ctx, 'refresh')),
        if ((s['origin'] as String? ?? '').startsWith('http'))
          ListTile(leading: const Icon(Icons.open_in_new_rounded), title: const Text('Asli page kholo'), onTap: () => Navigator.pop(ctx, 'open')),
        ListTile(leading: const Icon(Icons.delete_outline_rounded, color: C.bad), title: const Text('Hatao'), onTap: () => Navigator.pop(ctx, 'remove')),
      ])),
    );
    if (a == null || !context.mounted) return;
    final api = app.api!;
    final sid = s['id'] as String;
    try {
      switch (a) {
        case 'only':
          await api.notebookSelect(id, [sid], true, only: true);
        case 'rename':
          final t = TextEditingController(text: s['title'] as String? ?? '');
          final name = await showDialog<String>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: const Text('Source ka naam'),
              content: TextField(controller: t, autofocus: true),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
                FilledButton(onPressed: () => Navigator.pop(ctx, t.text.trim()), child: const Text('Save')),
              ],
            ),
          );
          if (name == null || name.isEmpty) return;
          await api.notebookRenameSource(id, sid, name);
        case 'refresh':
          if (context.mounted) nbSnack(context, 'Source dobara padh raha hoon…');
          final r = await api.notebookRefreshSource(id, sid);
          if (context.mounted) nbSnack(context, r['changed'] == true ? 'Naya version aa gaya' : 'Koi badlav nahi tha');
        case 'open':
          await launchUrl(Uri.parse(s['origin'] as String), mode: LaunchMode.externalApplication);
          return;
        case 'remove':
          final ok = await showDialog<bool>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: const Text('Source hatayein?'),
              content: Text(s['title'] as String? ?? ''),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Nahi')),
                FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hatao')),
              ],
            ),
          );
          if (ok != true) return;
          await api.notebookRemoveSource(id, sid);
      }
      await reload();
    } catch (e) {
      if (context.mounted) nbSnack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final srcs = nbList(d['sources']);
    final on = srcs.where((s) => s['enabled'] == true).length;
    final max = (nbMap(d['limits'])['sources'] as num? ?? 100).toInt();
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(14, 12, 14, 40), children: [
        GradientButton(label: 'Source jodo', icon: Icons.add_rounded,
            onTap: srcs.length >= max ? null : () => nbAddSourceSheet(context, app, id, reload, research)),
        const SizedBox(height: 8),
        GlassButton(label: 'Web se dhoondho (Discover)', icon: Icons.travel_explore_rounded, height: 44,
            onTap: () => nbDiscoverSheet(context, app, id, reload, research)),
        const SizedBox(height: 14),
        if (srcs.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('Abhi koi source nahi. PDF, Word, PowerPoint, photo (likha hua bhi), audio, apni awaaz, website, YouTube, '
                'Google Drive / Sheets ya copy kiya text daaliye. Har jawab inhi sources se aayega.',
                textAlign: TextAlign.center, style: TextStyle(color: C.muted, height: 1.45)),
          )
        else ...[
          Row(children: [
            Checkbox(
              value: on == srcs.length ? true : on == 0 ? false : null,
              tristate: true,
              activeColor: C.accent,
              onChanged: (_) => _toggle(context, null, on != srcs.length),
            ),
            Expanded(child: Text('Sab chuno · $on / ${srcs.length} chune (limit $max)', style: const TextStyle(color: C.muted))),
          ]),
          const Text('Sirf tick wale sources se chat aur Studio bante hain.', style: TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 6),
          for (final s in srcs)
            Glass(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.fromLTRB(4, 8, 4, 8),
              child: InkWell(
                onTap: () async {
                  final q = await Navigator.of(context).push<String>(
                      MaterialPageRoute(builder: (_) => NbSourceScreen(app: app, nid: id, sid: s['id'] as String)));
                  if (q != null) ask(q);
                },
                onLongPress: () => _menu(context, s),
                child: Row(children: [
                  Checkbox(value: s['enabled'] == true, activeColor: C.accent,
                      onChanged: (v) => _toggle(context, [s['id'] as String], v == true)),
                  Icon(nbKindIcon(s['kind'] as String? ?? ''), color: C.accentSoft, size: 22),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(s['title'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontWeight: FontWeight.w700, color: s['enabled'] == true ? C.ink : C.muted)),
                    if ((s['summary'] as String? ?? '').isNotEmpty)
                      Text(s['summary'] as String, maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: C.muted, fontSize: 12, height: 1.3)),
                    Text('${s['kind']} · ${_size((s['chars'] as num? ?? 0).toInt())}${(s['note'] as String? ?? '').isNotEmpty ? ' · ${s['note']}' : ''}',
                        maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 11)),
                  ])),
                  IconButton(icon: const Icon(Icons.more_vert_rounded), onPressed: () => _menu(context, s)),
                ]),
              ),
            ),
        ],
      ]),
    );
  }

  static String _size(int chars) => chars >= 1000 ? '${(chars / 1000).toStringAsFixed(chars >= 10000 ? 0 : 1)}k akshar' : '$chars akshar';
}

// ---------------------------------------------------------------- add a source
Future<void> nbAddSourceSheet(BuildContext context, Santosh app, String id, Future<void> Function() reload,
    Future<void> Function(String) research) async {
  final a = await showModalBottomSheet<String>(
    context: context,
    backgroundColor: C.bgBottom,
    isScrollControlled: true,
    builder: (ctx) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Source jodiye', style: display(20)),
          const SizedBox(height: 4),
          const Text('Hoola inhi se jawab dega aur Studio banayega.', style: TextStyle(color: C.muted)),
          const SizedBox(height: 14),
          GridView.count(
            crossAxisCount: 3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.05,
            children: [
              for (final o in const [
                ('file', 'File', 'PDF, Word, PPT, Excel', Icons.upload_file_rounded),
                ('camera', 'Photo kheencho', 'Kitaab, notes, board', Icons.photo_camera_rounded),
                ('gallery', 'Gallery', 'Photo / screenshot', Icons.photo_library_rounded),
                ('record', 'Bol kar', 'Apni awaaz record', Icons.mic_rounded),
                ('audio', 'Audio file', 'Lecture, call, meeting', Icons.audio_file_rounded),
                ('link', 'Website / YouTube', 'Link daaliye', Icons.link_rounded),
                ('text', 'Text paste', 'Copy kiya hua', Icons.content_paste_rounded),
                ('drive', 'Google Drive', 'Doc / Sheet / file', Icons.add_to_drive_rounded),
                ('discover', 'Discover', 'Web se dhoondho', Icons.travel_explore_rounded),
              ])
                Press(
                  onTap: () => Navigator.pop(ctx, o.$1),
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(18), border: Border.all(color: const Color(0x22FFFFFF))),
                    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Icon(o.$4, color: C.accent, size: 28),
                      const SizedBox(height: 6),
                      Text(o.$2, textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                      Text(o.$3, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: C.faint, fontSize: 10.5)),
                    ]),
                  ),
                ),
            ],
          ),
        ]),
      ),
    ),
  );
  if (a == null || !context.mounted) return;
  final api = app.api!;

  Future<void> upload(String name, List<int> bytes, {String title = ''}) async {
    if (bytes.length > 200 * 1024 * 1024) {
      nbSnack(context, 'File 200 MB se badi hai.');
      return;
    }
    final close = _busy(context, 'Padh raha hoon: $name');
    try {
      final r = await api.notebookUpload(id, name, bytes, title: title);
      close();
      if (context.mounted) nbSnack(context, 'Source juda: ${r['title'] ?? name}${(r['note'] as String? ?? '').isNotEmpty ? ' · ${r['note']}' : ''}');
      await reload();
    } catch (e) {
      close();
      if (context.mounted) nbSnack(context, '$e');
    }
  }

  Future<void> add(Map<String, dynamic> src) async {
    final close = _busy(context, 'Source padh raha hoon…');
    try {
      final r = await api.notebookAddSource(id, src);
      close();
      if (context.mounted) nbSnack(context, 'Source juda: ${r['title'] ?? ''}${(r['note'] as String? ?? '').isNotEmpty ? ' · ${r['note']}' : ''}');
      await reload();
    } catch (e) {
      close();
      if (context.mounted) nbSnack(context, '$e');
    }
  }

  switch (a) {
    case 'file':
    case 'audio':
      FilePickerResult? res;
      try {
        res = await FilePicker.platform.pickFiles(type: a == 'audio' ? FileType.audio : FileType.any, allowMultiple: true, withData: false);
      } catch (e) {
        if (context.mounted) nbSnack(context, 'File chun nahi paye: $e');
        return;
      }
      for (final f in res?.files ?? const <PlatformFile>[]) {
        if (!context.mounted) return;
        final bytes = f.bytes ?? (f.path != null ? await File(f.path!).readAsBytes() : null);
        if (bytes == null) continue;
        await upload(f.name, bytes);
      }
    case 'camera':
    case 'gallery':
      try {
        final pick = ImagePicker();
        final List<XFile> xs;
        if (a == 'camera') {
          final x = await pick.pickImage(source: ImageSource.camera, imageQuality: 85, maxWidth: 2400);
          xs = x == null ? const [] : [x];
        } else {
          xs = await pick.pickMultiImage(imageQuality: 85, maxWidth: 2400);
        }
        for (final x in xs) {
          if (!context.mounted) return;
          await upload(x.name.isEmpty ? 'photo.jpg' : x.name, await x.readAsBytes());
        }
      } catch (e) {
        if (context.mounted) nbSnack(context, '$e');
      }
    case 'record':
      final wav = await showDialog<List<int>>(context: context, barrierDismissible: false, builder: (_) => const _RecordDialog());
      if (wav != null && context.mounted) {
        final stamp = DateTime.now().toIso8601String().substring(0, 16).replaceAll(':', '-');
        await upload('recording-$stamp.wav', wav, title: 'Meri recording $stamp'.replaceAll('T', ' '));
      }
    case 'link':
      final v = await _ask(context, 'Website ya YouTube link', 'https://…', multi: true,
          help: 'Ek se zyada link: har line mein ek. YouTube ka transcript padha jayega.');
      if (v == null) return;
      for (final u in v.split(RegExp(r'[\s,]+')).where((x) => x.startsWith('http'))) {
        if (!context.mounted) return;
        await add({'url': u});
      }
    case 'text':
      final t = TextEditingController();
      final body = TextEditingController();
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Text paste kijiye'),
          content: SizedBox(
            width: 520,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: t, decoration: const InputDecoration(hintText: 'Naam (optional)')),
              const SizedBox(height: 8),
              TextField(controller: body, minLines: 6, maxLines: 12, decoration: const InputDecoration(hintText: 'Yahan paste kijiye')),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  icon: const Icon(Icons.content_paste_rounded),
                  label: const Text('Clipboard se'),
                  onPressed: () async {
                    final c = await Clipboard.getData('text/plain');
                    if (c?.text != null) body.text = c!.text!;
                  },
                ),
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodo')),
          ],
        ),
      );
      if (ok == true && body.text.trim().isNotEmpty) await add({'text': body.text.trim(), if (t.text.trim().isNotEmpty) 'title': t.text.trim()});
    case 'drive':
      final dv = await _ask(context, 'Google Drive', 'Drive link ya file ka naam',
          help: 'Google Docs, Slides, Sheets, PDF ya koi bhi Drive file (Google se juda hona chahiye).');
      if (dv != null) await add({'drive': dv});
    case 'discover':
      if (context.mounted) await nbDiscoverSheet(context, app, id, reload, research);
  }
}

VoidCallback _busy(BuildContext context, String text) {
  var open = true;
  showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (_) => PopScope(
      canPop: false,
      child: AlertDialog(content: Row(children: [
        const CircularProgressIndicator(),
        const SizedBox(width: 16),
        Expanded(child: Text(text)),
      ])),
    ),
  ).then((_) => open = false);
  return () {
    if (open && context.mounted) Navigator.of(context, rootNavigator: true).pop();
    open = false;
  };
}

Future<String?> _ask(BuildContext context, String title, String hint, {bool multi = false, String help = '', String initial = ''}) async {
  final t = TextEditingController(text: initial);
  final v = await showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        TextField(controller: t, autofocus: true, minLines: 1, maxLines: multi ? 6 : 2, decoration: InputDecoration(hintText: hint)),
        if (help.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(help, style: const TextStyle(color: C.faint, fontSize: 12))),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
        FilledButton(onPressed: () => Navigator.pop(ctx, t.text.trim()), child: const Text('Theek hai')),
      ],
    ),
  );
  return (v == null || v.isEmpty) ? null : v;
}

class _RecordDialog extends StatefulWidget {
  const _RecordDialog();
  @override
  State<_RecordDialog> createState() => _RecordDialogState();
}

class _RecordDialogState extends State<_RecordDialog> {
  final _rec = VoiceRecorder();
  Timer? _t;
  String? _err;

  @override
  void initState() {
    super.initState();
    _rec.start().then((e) {
      if (!mounted) return;
      setState(() => _err = e);
      _t = Timer.periodic(const Duration(milliseconds: 150), (_) => setState(() {}));
    });
  }

  @override
  void dispose() {
    _t?.cancel();
    if (_rec.recording) _rec.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Bol kar source banaiye'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
          if (_err == null) ...[
            AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              width: 80 + _rec.level * 140,
              height: 80 + _rec.level * 140,
              decoration: BoxDecoration(shape: BoxShape.circle, color: C.bad.withOpacity(.25 + _rec.level * .5)),
              child: const Icon(Icons.mic_rounded, size: 40, color: Colors.white),
            ),
            const SizedBox(height: 12),
            Text(nbClock(_rec.length), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            const Text('Lecture, meeting ya apne notes boliye. Hoola sun kar likh lega.', textAlign: TextAlign.center,
                style: TextStyle(color: C.muted, fontSize: 12.5)),
          ],
        ]),
        actions: [
          TextButton(onPressed: () async {
            await _rec.stop();
            if (context.mounted) Navigator.pop(context);
          }, child: const Text('Rehne do')),
          if (_err == null)
            FilledButton(onPressed: () async {
              final w = await _rec.stop();
              if (context.mounted) Navigator.pop(context, w.length > 3200 ? w : null);
            }, child: const Text('Ho gaya, jodo')),
        ],
      );
}

// ---------------------------------------------------------------- Discover (fast) + Deep research
Future<void> nbDiscoverSheet(BuildContext context, Santosh app, String id, Future<void> Function() reload,
    Future<void> Function(String) research) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: C.bgBottom,
    builder: (_) => _DiscoverSheet(app: app, id: id, reload: reload, research: research),
  );
}

class _DiscoverSheet extends StatefulWidget {
  const _DiscoverSheet({required this.app, required this.id, required this.reload, required this.research});
  final Santosh app;
  final String id;
  final Future<void> Function() reload;
  final Future<void> Function(String) research;
  @override
  State<_DiscoverSheet> createState() => _DiscoverSheetState();
}

class _DiscoverSheetState extends State<_DiscoverSheet> {
  final _q = TextEditingController();
  bool _busy = false;
  Map<String, dynamic>? _r;
  final Set<String> _pick = {};
  int _adding = 0;

  Future<void> _go() async {
    if (_q.text.trim().isEmpty) return;
    setState(() {
      _busy = true;
      _r = null;
      _pick.clear();
    });
    try {
      final r = await widget.app.api!.notebookDiscover(widget.id, _q.text.trim());
      setState(() {
        _r = r;
        for (final s in nbList(r['sources'])) {
          if (s['added'] != true) _pick.add(s['url'] as String);
        }
      });
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _add() async {
    final urls = _pick.toList();
    var ok = 0;
    for (final u in urls) {
      setState(() => _adding = ok + 1);
      try {
        await widget.app.api!.notebookAddSource(widget.id, {'url': u});
        ok++;
      } catch (_) {}
    }
    await widget.reload();
    if (!mounted) return;
    nbSnack(context, '$ok / ${urls.length} sources jude');
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final srcs = nbList(r?['sources']);
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: .85,
        maxChildSize: .95,
        builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.fromLTRB(16, 16, 16, 30), children: [
          Text('Discover sources', style: display(20)),
          const SizedBox(height: 4),
          const Text('Vishay likhiye: Hoola web se achhe sources laayega, aap chun kar jodiye.', style: TextStyle(color: C.muted)),
          const SizedBox(height: 12),
          TextField(
            controller: _q,
            autofocus: true,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _go(),
            decoration: InputDecoration(
              hintText: 'Jaise: PM Kisan yojana ke niyam 2026',
              suffixIcon: IconButton(icon: const Icon(Icons.search_rounded), onPressed: _busy ? null : _go),
            ),
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: GlassButton(label: _busy ? 'Dhoondh raha hoon…' : 'Jaldi dhoondho', icon: Icons.bolt_rounded, height: 44,
                onTap: _busy ? null : _go)),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Deep research', icon: Icons.science_rounded, height: 44, onTap: () async {
              final q = _q.text.trim();
              if (q.isEmpty) {
                nbSnack(context, 'Pehle vishay likhiye');
                return;
              }
              Navigator.pop(context);
              await widget.research(q);
            })),
          ]),
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Deep research = kai searches + pages padh kar poori report (source bhi ban jati hai), kuch minute lagte hain.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
          if (_busy) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
          if (r != null) ...[
            if ((r['summary'] as String? ?? '').isNotEmpty) ...[
              const SizedBox(height: 14),
              Glass(child: NbMarkdown(r['summary'] as String, size: 13.5)),
            ],
            const SizedBox(height: 12),
            if (srcs.isEmpty) const Text('Kuch nahi mila. Doosre shabd try kijiye.', style: TextStyle(color: C.muted)),
            for (final s in srcs)
              CheckboxListTile(
                value: s['added'] == true || _pick.contains(s['url']),
                activeColor: C.accent,
                contentPadding: EdgeInsets.zero,
                onChanged: s['added'] == true ? null : (v) => setState(() => v == true ? _pick.add(s['url'] as String) : _pick.remove(s['url'])),
                title: Text(s['title'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('${s['added'] == true ? '✓ pehle se juda · ' : ''}${Uri.tryParse(s['url'] as String? ?? '')?.host ?? ''}\n${s['excerpt'] ?? ''}',
                    maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
              ),
            if (_pick.isNotEmpty) ...[
              const SizedBox(height: 10),
              GradientButton(label: _adding > 0 ? 'Jod raha hoon $_adding / ${_pick.length}…' : '${_pick.length} sources jodo',
                  icon: Icons.add_rounded, onTap: _adding > 0 ? null : _add),
            ],
          ],
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- one source (guide + passages)
class NbSourceScreen extends StatefulWidget {
  const NbSourceScreen({super.key, required this.app, required this.nid, required this.sid, this.highlight});
  final Santosh app;
  final String nid;
  final String sid;
  final int? highlight;
  @override
  State<NbSourceScreen> createState() => _NbSourceScreenState();
}

class _NbSourceScreenState extends State<NbSourceScreen> {
  Map<String, dynamic>? _s;
  Map<String, dynamic>? _guide;
  String? _err;
  final _hl = GlobalKey();

  @override
  void initState() {
    super.initState();
    widget.app.api!.notebookSource(widget.nid, widget.sid).then((s) {
      if (!mounted) return;
      setState(() {
        _s = s;
        final g = nbMap(s['guide']);
        if ((g['summary'] as String? ?? '').isNotEmpty) _guide = g;
      });
      if (widget.highlight != null) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          final c = _hl.currentContext;
          if (c != null) Scrollable.ensureVisible(c, duration: const Duration(milliseconds: 400), alignment: .15);
        });
      }
      if (_guide == null) {
        widget.app.api!.notebookSourceGuide(widget.nid, widget.sid).then((g) {
          if (mounted) setState(() => _guide = g);
        }).catchError((Object e) {
          if (mounted) setState(() => _guide = {'summary': '', 'error': '$e'});
        });
      }
    }).catchError((Object e) {
      if (mounted) setState(() => _err = '$e');
    });
  }

  @override
  Widget build(BuildContext context) {
    final s = _s;
    final g = _guide;
    final passages = List<String>.from(((s?['passages'] as List?) ?? const []).map((e) => '$e'));
    return Scaffold(
      appBar: nbBar(s?['title'] as String? ?? 'Source', actions: [
        if ((s?['origin'] as String? ?? '').startsWith('http'))
          IconButton(icon: const Icon(Icons.open_in_new_rounded),
              onPressed: () => launchUrl(Uri.parse(s!['origin'] as String), mode: LaunchMode.externalApplication)),
      ]),
      body: Aurora(
        child: s == null
            ? Center(child: _err != null ? Text(_err!, style: const TextStyle(color: C.bad)) : const CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 40),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const Row(children: [
                        Icon(Icons.auto_awesome_rounded, color: C.accent, size: 18),
                        SizedBox(width: 6),
                        Text('Source guide', style: TextStyle(fontWeight: FontWeight.w800)),
                      ]),
                      const SizedBox(height: 8),
                      if (g == null)
                        const LinearProgressIndicator(color: C.accent, backgroundColor: C.panel)
                      else if ((g['summary'] as String? ?? '').isEmpty)
                        Text('${g['error'] ?? 'Guide nahi bana'}', style: const TextStyle(color: C.muted))
                      else ...[
                        NbMarkdown(g['summary'] as String, size: 14),
                        if ((g['topics'] as List? ?? const []).isNotEmpty) ...[
                          const SizedBox(height: 10),
                          Wrap(spacing: 6, runSpacing: 6, children: [
                            for (final t in g['topics'] as List)
                              ActionChip(label: Text('$t'), onPressed: () => Navigator.pop(context, '"${s['title']}" mein $t ke baare mein samjhaiye')),
                          ]),
                        ],
                        for (final q in (g['questions'] as List? ?? const []))
                          ListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            leading: const Icon(Icons.help_outline_rounded, color: C.teal, size: 20),
                            title: Text('$q', style: const TextStyle(fontSize: 13.5)),
                            onTap: () => Navigator.pop(context, '$q'),
                          ),
                      ],
                    ]),
                  ),
                  if ((s['note'] as String? ?? '').isNotEmpty)
                    Padding(padding: const EdgeInsets.only(top: 8), child: Text('${s['note']}', style: const TextStyle(color: C.faint, fontSize: 12))),
                  const SizedBox(height: 14),
                  Caption('POORA TEXT · ${passages.length} HISSE'),
                  for (var i = 0; i < passages.length; i++)
                    Container(
                      key: i == widget.highlight ? _hl : null,
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: i == widget.highlight ? C.accent.withOpacity(.16) : C.panel,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: i == widget.highlight ? C.accent : const Color(0x14FFFFFF)),
                      ),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Hissa ${i + 1}', style: TextStyle(color: i == widget.highlight ? C.accent : C.faint, fontSize: 11, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        SelectableText(passages[i], style: const TextStyle(height: 1.45, fontSize: 13.5)),
                      ]),
                    ),
                ]),
              ),
      ),
    );
  }
}

// ================================================================ Chat
class _ChatTab extends StatefulWidget {
  const _ChatTab({super.key, required this.app, required this.id, required this.d, required this.reload, required this.openSources});
  final Santosh app;
  final String id;
  final Map<String, dynamic> d;
  final Future<void> Function() reload;
  final VoidCallback openSources;
  @override
  State<_ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends State<_ChatTab> with AutomaticKeepAliveClientMixin {
  List<Map<String, dynamic>> _msgs = [];
  Map<String, dynamic>? _guide;
  bool _guideBusy = false;
  bool _thinking = false;
  String _pending = '';
  final _t = TextEditingController();
  final _sc = ScrollController();
  final SpeechToText _stt = SpeechToText();
  bool _listening = false;

  @override
  bool get wantKeepAlive => true;

  Map<String, dynamic> get cfg => nbMap(widget.d['chat_config']);
  int get _on => nbList(widget.d['sources']).where((s) => s['enabled'] == true).length;

  @override
  void initState() {
    super.initState();
    _loadChat();
    _loadGuide();
  }

  @override
  void didUpdateWidget(covariant _ChatTab old) {
    super.didUpdateWidget(old);
    final key = nbMap(widget.d['guide'])['key'];
    if (key != null && key != _guide?['key'] && !_guideBusy) _loadGuide();
  }

  Future<void> _loadChat() async {
    try {
      final m = await widget.app.api!.notebookChat(widget.id);
      if (!mounted) return;
      setState(() => _msgs = m);
      _down();
    } catch (_) {}
  }

  Future<void> _loadGuide({bool refresh = false}) async {
    if (nbList(widget.d['sources']).isEmpty) return;
    setState(() => _guideBusy = true);
    try {
      final g = await widget.app.api!.notebookGuide(widget.id, refresh: refresh);
      if (mounted) setState(() => _guide = g);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _guideBusy = false);
    }
  }

  void _down() => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_sc.hasClients) _sc.animateTo(_sc.position.maxScrollExtent + 200, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      });

  Future<void> send(String q) async {
    q = q.trim();
    if (q.isEmpty || _thinking) return;
    if (_on == 0) {
      nbSnack(context, nbList(widget.d['sources']).isEmpty ? 'Pehle koi source jodiye.' : 'Koi source chuna nahi hai: Sources mein tick kijiye.');
      widget.openSources();
      return;
    }
    _t.clear();
    setState(() {
      _thinking = true;
      _pending = q;
    });
    _down();
    try {
      await widget.app.api!.notebookAsk(widget.id, q);
      await _loadChat();
    } catch (e) {
      if (mounted) {
        nbSnack(context, '$e');
        _t.text = q;
      }
    } finally {
      if (mounted) setState(() {
        _thinking = false;
        _pending = '';
      });
    }
  }

  Future<void> _mic() async {
    if (_listening) {
      await _stt.stop();
      setState(() => _listening = false);
      return;
    }
    final ok = await _stt.initialize(onStatus: (s) {
      if ((s == 'done' || s == 'notListening') && mounted) setState(() => _listening = false);
    });
    if (!ok) {
      if (mounted) nbSnack(context, 'Microphone permission chahiye.');
      return;
    }
    setState(() => _listening = true);
    await _stt.listen(
      localeId: widget.app.language.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 40),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      onResult: (r) {
        setState(() => _t.text = r.recognizedWords);
        if (r.finalResult && r.recognizedWords.trim().isNotEmpty) send(r.recognizedWords);
      },
    );
  }

  void _cite(Map<String, dynamic> m, int n) {
    final cites = nbList(m['citations']);
    final c = cites.firstWhere((x) => x['n'] == n, orElse: () => <String, dynamic>{});
    if (c.isEmpty) return;
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              CircleAvatar(radius: 14, backgroundColor: C.violet, child: Text('$n', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13))),
              const SizedBox(width: 10),
              Icon(nbKindIcon(c['kind'] as String? ?? ''), color: C.accentSoft, size: 20),
              const SizedBox(width: 6),
              Expanded(child: Text('${c['title']}', maxLines: 2, style: const TextStyle(fontWeight: FontWeight.w800))),
            ]),
            const SizedBox(height: 4),
            Text('Source ${c['source']} · hissa ${c['passage']}', style: const TextStyle(color: C.faint, fontSize: 12)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: C.accent.withOpacity(.12), borderRadius: BorderRadius.circular(12),
                  border: const Border(left: BorderSide(color: C.accent, width: 4))),
              child: Text('“${c['snippet']}…”', style: const TextStyle(height: 1.45)),
            ),
            const SizedBox(height: 14),
            GlassButton(label: 'Source mein dekho', icon: Icons.menu_book_rounded, onTap: () async {
              Navigator.pop(ctx);
              final q = await Navigator.of(context).push<String>(MaterialPageRoute(builder: (_) => NbSourceScreen(
                  app: widget.app, nid: widget.id, sid: c['source_id'] as String, highlight: (c['chunk'] as num?)?.toInt())));
              if (q != null) send(q);
            }),
          ]),
        ),
      ),
    );
  }

  Future<void> _configure() async {
    final langs = Map<String, dynamic>.from(nbMap(widget.d['languages']));
    String goal = cfg['goal'] as String? ?? 'default';
    String length = cfg['length'] as String? ?? 'default';
    String lang = (cfg['language'] as String? ?? '').isEmpty ? 'auto' : cfg['language'] as String;
    final custom = TextEditingController(text: cfg['custom'] as String? ?? '');
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) => Padding(
            padding: EdgeInsets.fromLTRB(18, 18, 18, 18 + MediaQuery.of(ctx).viewInsets.bottom),
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('Chat set kijiye', style: display(20)),
                const SizedBox(height: 14),
                const Caption('MAQSAD'),
                Wrap(spacing: 8, children: [
                  for (final g in const [('default', 'Aam (research)'), ('learning', 'Seekhna (teacher)'), ('custom', 'Apna role')])
                    ChoiceChip(label: Text(g.$2), selected: goal == g.$1, onSelected: (_) => set(() => goal = g.$1)),
                ]),
                if (goal == 'learning')
                  const Padding(padding: EdgeInsets.only(top: 6), child: Text('Hoola seedha jawab dene ki jagah sawaal poochh kar sikhayega, step by step.',
                      style: TextStyle(color: C.faint, fontSize: 12))),
                if (goal == 'custom')
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: TextField(controller: custom, minLines: 2, maxLines: 5,
                        decoration: const InputDecoration(hintText: 'Jaise: Tum GST exam ke teacher ho, har jawab mein ek example do')),
                  ),
                const SizedBox(height: 14),
                const Caption('JAWAB KI LAMBAI'),
                Wrap(spacing: 8, children: [
                  for (final l in const [('shorter', 'Chhota'), ('default', 'Normal'), ('longer', 'Lamba')])
                    ChoiceChip(label: Text(l.$2), selected: length == l.$1, onSelected: (_) => set(() => length = l.$1)),
                ]),
                const SizedBox(height: 14),
                const Caption('JAWAB KI BHASHA'),
                DropdownButton<String>(
                  isExpanded: true,
                  value: lang,
                  dropdownColor: C.bgBottom,
                  items: [
                    const DropdownMenuItem(value: 'auto', child: Text('Jis bhasha mein poochha (auto)')),
                    for (final e in langs.entries) DropdownMenuItem(value: e.key, child: Text('${e.value}')),
                  ],
                  onChanged: (v) => set(() => lang = v ?? 'auto'),
                ),
                const SizedBox(height: 18),
                GradientButton(label: 'Save', icon: Icons.check_rounded, onTap: () => Navigator.pop(ctx, true)),
              ]),
            ),
          )),
    );
    if (ok != true) return;
    try {
      await widget.app.api!.notebookConfig(widget.id, {'goal': goal, 'custom': custom.text.trim(), 'length': length, 'language': lang});
      await widget.reload();
      if (mounted) nbSnack(context, 'Chat set ho gaya');
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
    }
  }

  Future<void> _clear() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Chat saaf karein?'),
        content: const Text('Saved notes rahenge, sirf baatcheet hategi.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Nahi')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Saaf karo')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.app.api!.notebookClearChat(widget.id);
      setState(() => _msgs = []);
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
    }
  }

  Widget _overview() {
    final g = _guide;
    if (nbList(widget.d['sources']).isEmpty) {
      return Glass(
        child: Column(children: [
          const Text('📚', style: TextStyle(fontSize: 40)),
          const SizedBox(height: 8),
          const Text('Chat shuru karne ke liye pehle source jodiye.', textAlign: TextAlign.center),
          const SizedBox(height: 10),
          GlassButton(label: 'Sources kholo', icon: Icons.add_rounded, onTap: widget.openSources),
        ]),
      );
    }
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(widget.d['emoji'] as String? ?? '📒', style: const TextStyle(fontSize: 26)),
          const SizedBox(width: 8),
          Expanded(child: Text(widget.d['title'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17))),
          IconButton(tooltip: 'Naya overview', icon: const Icon(Icons.refresh_rounded, size: 20),
              onPressed: _guideBusy ? null : () => _loadGuide(refresh: true)),
        ]),
        Text('${nbList(widget.d['sources']).length} sources', style: const TextStyle(color: C.muted, fontSize: 12)),
        const SizedBox(height: 8),
        if (g == null && _guideBusy) const LinearProgressIndicator(color: C.accent, backgroundColor: C.panel),
        if (g != null) ...[
          NbMarkdown(g['overview'] as String? ?? '', size: 14),
          const SizedBox(height: 10),
          for (final q in (g['questions'] as List? ?? const []))
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Press(
                onTap: () => send('$q'),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                  decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0x22FFFFFF))),
                  child: Text('$q', style: const TextStyle(fontSize: 13.5)),
                ),
              ),
            ),
        ],
      ]),
    );
  }

  Widget _bubble(Map<String, dynamic> m, bool last) {
    if (m['role'] == 'user') {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.only(bottom: 10, left: 50),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(gradient: C.youGradient, borderRadius: BorderRadius.circular(18)),
          child: Text(m['text'] as String? ?? '', style: const TextStyle(color: Colors.white, height: 1.35)),
        ),
      );
    }
    final follows = List<String>.from(((m['followups'] as List?) ?? const []).map((e) => '$e'));
    final cites = nbList(m['citations']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Glass(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            NbMarkdown(m['text'] as String? ?? '', onCite: (n) => _cite(m, n)),
            if (cites.isEmpty)
              const Padding(padding: EdgeInsets.only(top: 4), child: Text('Is jawab ka koi source hissa nahi mila.', style: TextStyle(color: C.faint, fontSize: 11.5))),
            Row(children: [
              if (cites.isNotEmpty)
                Expanded(child: Text('${cites.length} source hisse · [n] dabaiye', style: const TextStyle(color: C.faint, fontSize: 11.5)))
              else
                const Spacer(),
              IconButton(tooltip: 'Copy', visualDensity: VisualDensity.compact, icon: const Icon(Icons.copy_rounded, size: 18), onPressed: () {
                Clipboard.setData(ClipboardData(text: (m['text'] as String? ?? '').replaceAll(RegExp(r'\[\d+\]'), '')));
                nbSnack(context, 'Copy ho gaya');
              }),
              IconButton(tooltip: 'Note mein save', visualDensity: VisualDensity.compact, icon: const Icon(Icons.push_pin_outlined, size: 18),
                  onPressed: m['id'] == null ? null : () async {
                    try {
                      await widget.app.api!.notebookSaveMessage(widget.id, m['id'] as String);
                      await widget.reload();
                      if (mounted) nbSnack(context, 'Note mein save ho gaya (Studio > Notes)');
                    } catch (e) {
                      if (mounted) nbSnack(context, '$e');
                    }
                  }),
            ]),
          ]),
        ),
        if (last && follows.isNotEmpty && !_thinking) ...[
          const SizedBox(height: 8),
          for (final f in follows)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Align(
                alignment: Alignment.centerLeft,
                child: ActionChip(avatar: const Icon(Icons.subdirectory_arrow_right_rounded, size: 16, color: C.accent), label: Text(f), onPressed: () => send(f)),
              ),
            ),
        ],
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final c = cfg;
    final tags = [
      if (c['goal'] == 'learning') 'Seekhna',
      if (c['goal'] == 'custom') 'Apna role',
      if (c['length'] == 'shorter') 'Chhota',
      if (c['length'] == 'longer') 'Lamba',
      if ((c['language'] as String? ?? '').isNotEmpty) '${nbMap(widget.d['languages'])[c['language']] ?? c['language']}',
    ];
    return Column(children: [
      Expanded(
        child: ListView(controller: _sc, padding: const EdgeInsets.fromLTRB(14, 10, 14, 16), children: [
          _overview(),
          const SizedBox(height: 14),
          for (var i = 0; i < _msgs.length; i++) _bubble(_msgs[i], i == _msgs.length - 1),
          if (_thinking) ...[
            Align(
              alignment: Alignment.centerRight,
              child: Container(
                margin: const EdgeInsets.only(bottom: 10, left: 50),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(gradient: C.youGradient, borderRadius: BorderRadius.circular(18)),
                child: Text(_pending, style: const TextStyle(color: Colors.white)),
              ),
            ),
            const Glass(
              child: Row(children: [
                SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.accent)),
                SizedBox(width: 12),
                Expanded(child: Text('Sources padh raha hoon, jawab likh raha hoon…', style: TextStyle(color: C.muted))),
              ]),
            ),
          ],
        ]),
      ),
      Container(
        padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
        decoration: const BoxDecoration(color: Color(0x66120E2A), border: Border(top: BorderSide(color: Color(0x14FFFFFF)))),
        child: SafeArea(
          top: false,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Row(children: [
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(children: [
                    InkWell(
                      onTap: widget.openSources,
                      child: Text('$_on sources chune', style: const TextStyle(color: C.muted, fontSize: 12, decoration: TextDecoration.underline)),
                    ),
                    const SizedBox(width: 8),
                    for (final t in tags) Padding(padding: const EdgeInsets.only(right: 4), child: Pill(t, fg: C.teal)),
                  ]),
                ),
              ),
              IconButton(tooltip: 'Chat set karo', visualDensity: VisualDensity.compact, icon: const Icon(Icons.tune_rounded, size: 20), onPressed: _configure),
              IconButton(tooltip: 'Chat saaf karo', visualDensity: VisualDensity.compact, icon: const Icon(Icons.delete_sweep_outlined, size: 20),
                  onPressed: _msgs.isEmpty ? null : _clear),
            ]),
            Row(children: [
              Expanded(
                child: TextField(
                  controller: _t,
                  minLines: 1,
                  maxLines: 5,
                  textInputAction: TextInputAction.send,
                  onSubmitted: send,
                  decoration: InputDecoration(
                    hintText: _listening ? 'Sun raha hoon…' : 'Sources se kuch bhi poochhiye…',
                    filled: true,
                    fillColor: C.panel,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                    focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: const BorderSide(color: C.accent)),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              IconButton(onPressed: _mic, icon: Icon(_listening ? Icons.stop_circle_rounded : Icons.mic_rounded, color: _listening ? C.bad : C.accent)),
              Press(
                onTap: _thinking ? null : () => send(_t.text),
                child: Container(
                  width: 46, height: 46,
                  decoration: BoxDecoration(color: _thinking ? C.panel : C.accent, shape: BoxShape.circle),
                  child: const Icon(Icons.arrow_upward_rounded, color: C.onAccent),
                ),
              ),
            ]),
          ]),
        ),
      ),
    ]);
  }
}

// ================================================================ Studio
class _StudioTab extends StatelessWidget {
  const _StudioTab({required this.app, required this.id, required this.d, required this.cat, required this.reload, required this.ask});
  final Santosh app;
  final String id;
  final Map<String, dynamic> d;
  final Map<String, dynamic> cat;
  final Future<void> Function() reload;
  final void Function(String) ask;

  String get _lang {
    final l = nbMap(d['chat_config'])['language'] as String? ?? '';
    return l.isEmpty ? 'hinglish' : l;
  }

  Future<void> _start(BuildContext context, String kind, Map<String, dynamic> opts) async {
    try {
      final v = await app.api!.notebookStudio(id, kind, opts, conv: app.conversationId ?? '');
      if (context.mounted) nbSnack(context, '${_kindLabel[kind] ?? 'Studio'} ban raha hai: ${v['stage'] ?? ''}. Taiyaar hote hi bataunga.');
      await reload();
    } catch (e) {
      if (context.mounted) nbSnack(context, '$e');
    }
  }

  Future<void> _customize(BuildContext context, String kind, {Map<String, dynamic>? preset}) async {
    final opts = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (_) => _StudioSheet(app: app, id: id, kind: kind, cat: cat, langs: nbMap(d['languages']), lang: _lang, preset: preset ?? const {}),
    );
    if (opts != null && context.mounted) await _start(context, kind, opts);
  }

  Future<void> _outMenu(BuildContext context, Map<String, dynamic> o) async {
    final files = nbMap(o['files']);
    final names = files.keys.where((n) => !n.startsWith('frame-') && !n.startsWith('pic-') && !n.startsWith('slide-') && !n.startsWith('join-')).toList()..sort();
    final a = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(title: Text(o['title'] as String? ?? '', maxLines: 2, style: const TextStyle(fontWeight: FontWeight.w700))),
        ListTile(leading: const Icon(Icons.edit_rounded), title: const Text('Naam badlo'), onTap: () => Navigator.pop(ctx, 'rename')),
        ListTile(leading: const Icon(Icons.replay_rounded), title: const Text('Inhi settings se dobara banao'), onTap: () => Navigator.pop(ctx, 'again')),
        if (o['status'] == 'ready')
          for (final n in names) ...[
            ListTile(leading: const Icon(Icons.share_rounded), title: Text('Bhejo: $n'), onTap: () => Navigator.pop(ctx, 'share:$n')),
            ListTile(leading: const Icon(Icons.chat_rounded), title: Text('Chat mein file card: $n'),
                subtitle: const Text('WhatsApp / email / Hoola Network par bhejne ke liye', style: TextStyle(fontSize: 11.5)),
                onTap: () => Navigator.pop(ctx, 'card:$n')),
          ],
        ListTile(leading: const Icon(Icons.delete_outline_rounded, color: C.bad), title: const Text('Delete'), onTap: () => Navigator.pop(ctx, 'delete')),
      ]))),
    );
    if (a == null || !context.mounted) return;
    final api = app.api!;
    final oid = o['id'] as String;
    try {
      if (a == 'rename') {
        final v = await _ask(context, 'Naya naam', '', initial: o['title'] as String? ?? '');
        if (v == null) return;
        await api.notebookOutputRename(id, oid, v);
      } else if (a == 'again') {
        await _start(context, o['kind'] as String, nbMap(o['options']));
        return;
      } else if (a.startsWith('share:')) {
        final n = a.substring(6);
        await nbShareFile(context, app, files[n] as String, n);
        return;
      } else if (a.startsWith('card:')) {
        await api.notebookShare(id, oid, a.substring(5), conv: app.conversationId ?? '');
        if (context.mounted) nbSnack(context, 'File chat mein aa gayi');
        return;
      } else if (a == 'delete') {
        await api.notebookOutputDelete(id, oid);
      }
      await reload();
    } catch (e) {
      if (context.mounted) nbSnack(context, '$e');
    }
  }

  Future<void> _open(BuildContext context, Map<String, dynamic> o) async {
    final q = await openNbOutput(context, app, id, o);
    if (q != null) ask(q);
  }

  @override
  Widget build(BuildContext context) {
    final outs = nbList(d['outputs']);
    final notes = nbList(d['notes']);
    final hasSrc = nbList(d['sources']).any((s) => s['enabled'] == true);
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(14, 12, 14, 40), children: [
        if (!hasSrc)
          const Padding(
            padding: EdgeInsets.only(bottom: 10),
            child: Text('Studio ke liye kam se kam ek source chuna hona chahiye.', style: TextStyle(color: C.warn)),
          ),
        Text('Studio', style: display(20)),
        const Text('Tap = turant banao · ✎ = apne hisaab se (bhasha, style, lambai, focus)', style: TextStyle(color: C.faint, fontSize: 12)),
        const SizedBox(height: 10),
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: .98,
          children: [
            for (final t in _studioTiles)
              Press(
                onTap: !hasSrc ? null : () {
                  if (t.$1 == 'report' || t.$1 == 'table') {
                    _customize(context, t.$1);
                  } else {
                    _start(context, t.$1, {'language': _lang});
                  }
                },
                child: Container(
                  padding: const EdgeInsets.fromLTRB(10, 10, 4, 8),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    gradient: LinearGradient(colors: [t.$4.withOpacity(.38), t.$4.withOpacity(.12)], begin: Alignment.topLeft, end: Alignment.bottomRight),
                    border: Border.all(color: t.$4.withOpacity(.55)),
                  ),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Icon(t.$3, color: Colors.white, size: 26),
                      const Spacer(),
                      InkWell(
                        onTap: !hasSrc ? null : () => _customize(context, t.$1),
                        child: const Padding(padding: EdgeInsets.all(4), child: Icon(Icons.edit_rounded, size: 17, color: C.ink)),
                      ),
                    ]),
                    const Spacer(),
                    Text(t.$2, maxLines: 2, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, height: 1.15)),
                  ]),
                ),
              ),
          ],
        ),
        const SizedBox(height: 18),
        if (outs.isNotEmpty) ...[
          const Caption('BANE HUE'),
          for (final o in outs) _OutputTile(app: app, o: o, onOpen: () => _open(context, o), onMenu: () => _outMenu(context, o)),
        ],
        const SizedBox(height: 14),
        Row(children: [
          const Expanded(child: Caption('NOTES')),
          TextButton.icon(
            icon: const Icon(Icons.add_rounded),
            label: const Text('Note likho'),
            onPressed: () async {
              await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NbNoteScreen(app: app, nid: id)));
              reload();
            },
          ),
        ]),
        if (notes.isEmpty)
          const Text('Chat ke jawab 📌 se yahan save hote hain. Notes ko source bhi bana sakte hain.', style: TextStyle(color: C.faint, fontSize: 12.5)),
        for (final n in notes)
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            child: InkWell(
              onTap: () async {
                await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NbNoteScreen(app: app, nid: id, note: n)));
                reload();
              },
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(n['kind'] == 'answer' ? Icons.push_pin_rounded : Icons.sticky_note_2_rounded, color: C.accentSoft, size: 20),
                const SizedBox(width: 10),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(n['title'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text((n['preview'] as String? ?? '').replaceAll(RegExp(r'[#*>\[\]]'), ''), maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ])),
              ]),
            ),
          ),
      ]),
    );
  }
}

class _OutputTile extends StatelessWidget {
  const _OutputTile({required this.app, required this.o, required this.onOpen, required this.onMenu});
  final Santosh app;
  final Map<String, dynamic> o;
  final VoidCallback onOpen;
  final VoidCallback onMenu;

  @override
  Widget build(BuildContext context) {
    final st = o['status'] as String? ?? '';
    final kind = o['kind'] as String? ?? '';
    final cover = o['cover'] as String? ?? '';
    final pct = ((o['pct'] as num?) ?? 0).toDouble();
    final secs = (o['seconds'] as num? ?? 0).toInt();
    final count = (o['count'] as num? ?? 0).toInt();
    final opts = nbMap(o['options']);
    final meta = [
      o['label'] ?? _kindLabel[kind] ?? kind,
      if (secs > 0) nbClock(Duration(seconds: secs)),
      if (count > 0) '$count',
      if ((opts['language'] as String? ?? '').isNotEmpty) opts['language'],
      (o['created'] as String? ?? '').replaceFirst('T', ' '),
    ].join(' · ');
    if (o['legacy'] == true) return const SizedBox.shrink();
    return Glass(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      child: InkWell(
        onTap: st == 'ready' ? onOpen : null,
        onLongPress: onMenu,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                width: 64,
                height: 48,
                child: st == 'ready' && cover.isNotEmpty
                    ? Image.network(app.api!.absolute(cover), fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => ColoredBox(color: C.panel, child: Icon(nbStudioIcon(kind), color: C.accentSoft)))
                    : ColoredBox(color: C.violet.withOpacity(.25), child: Icon(nbStudioIcon(kind), color: C.accentSoft)),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(o['title'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(meta, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 11.5)),
            ])),
            if (st == 'ready') const Icon(Icons.play_circle_fill_rounded, color: C.accent),
            if (st == 'failed') const Icon(Icons.error_outline_rounded, color: C.bad),
            IconButton(icon: const Icon(Icons.more_vert_rounded), onPressed: onMenu),
          ]),
          if (st == 'queued' || st == 'working') ...[
            const SizedBox(height: 8),
            LinearProgressIndicator(value: pct > 0 ? pct / 100 : null, color: C.accent, backgroundColor: C.panel, minHeight: 5,
                borderRadius: BorderRadius.circular(4)),
            const SizedBox(height: 4),
            Text('${o['stage'] ?? 'Line mein'}${kind == 'video' || kind == 'audio' ? ' · aap app band kar sakte hain, taiyaar hone par bataunga' : ''}',
                style: const TextStyle(color: C.muted, fontSize: 11.5)),
          ],
          if (st == 'failed')
            Padding(padding: const EdgeInsets.only(top: 6), child: Text('${o['error'] ?? ''}', style: const TextStyle(color: C.bad, fontSize: 12))),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- customize sheet (per Studio kind)
class _StudioSheet extends StatefulWidget {
  const _StudioSheet({required this.app, required this.id, required this.kind, required this.cat, required this.langs, required this.lang, required this.preset});
  final Santosh app;
  final String id;
  final String kind;
  final Map<String, dynamic> cat;
  final Map<String, dynamic> langs;
  final String lang;
  final Map<String, dynamic> preset;
  @override
  State<_StudioSheet> createState() => _StudioSheetState();
}

class _StudioSheetState extends State<_StudioSheet> {
  late final Map<String, dynamic> _o = {'language': widget.lang, ...widget.preset};
  final _focus = TextEditingController();
  final _custom = TextEditingController();
  final _audience = TextEditingController();
  final _topic = TextEditingController();
  final _cols = TextEditingController();
  List<Map<String, dynamic>>? _suggested;

  Map<String, dynamic> get c => nbMap(widget.cat[widget.kind]);

  @override
  void initState() {
    super.initState();
    if (widget.kind == 'report') {
      _o['type'] ??= 'briefing';
      widget.app.api!.notebookReportFormats(widget.id).then((f) {
        if (mounted) setState(() => _suggested = f);
      }).catchError((Object _) {
        if (mounted) setState(() => _suggested = const []);
      });
    }
  }

  Widget _chips(String title, String key, Map<String, String> items, String def) {
    final cur = (_o[key] as String?) ?? def;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SizedBox(height: 12),
      Caption(title),
      Wrap(spacing: 8, runSpacing: 6, children: [
        for (final e in items.entries) ChoiceChip(label: Text(e.value), selected: cur == e.key, onSelected: (_) => setState(() => _o[key] = e.key)),
      ]),
    ]);
  }

  Map<String, String> _labels(Object? m) {
    if (m is Map) {
      return {for (final e in m.entries) '${e.key}': e.value is Map ? '${(e.value as Map)['label'] ?? e.key}' : '${e.value}'};
    }
    if (m is List) return {for (final x in m) '$x': _nice('$x')};
    return {};
  }

  static String _nice(String k) => const {
        'shorter': 'Chhota', 'default': 'Normal', 'longer': 'Lamba', 'short': 'Chhota', 'long': 'Lamba',
        'fewer': 'Kam', 'standard': 'Normal', 'more': 'Zyada', 'easy': 'Aasaan', 'medium': 'Beech ka', 'hard': 'Mushkil',
        'portrait': 'Khada (phone)', 'landscape': 'Leta (screen)', 'square': 'Square', 'concise': 'Kam shabd', 'detailed': 'Vistaar se',
        'female': 'Mahila', 'male': 'Purush', 'warm': 'Narm', 'bright': 'Josh',
      }[k] ?? k;

  String? _about(String key) {
    final m = c[key == 'format' ? 'formats' : key];
    if (m is Map) {
      final v = m[_o[key] ?? m.keys.first];
      if (v is Map) return v['about'] as String?;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final k = widget.kind;
    final styles = _labels(c['styles']);
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: .86,
        maxChildSize: .95,
        builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.fromLTRB(18, 16, 18, 30), children: [
          Row(children: [
            Icon(nbStudioIcon(k), color: C.accent),
            const SizedBox(width: 8),
            Text(_kindLabel[k] ?? k, style: display(20)),
          ]),
          if (k == 'audio') ...[
            _chips('FORMAT', 'format', _labels(c['formats']), 'deep_dive'),
            if (_about('format') != null) Text(_about('format')!, style: const TextStyle(color: C.faint, fontSize: 12)),
            _chips('LAMBAI', 'length', _labels(c['lengths']), 'default'),
          ],
          if (k == 'video') ...[
            _chips('FORMAT', 'format', _labels(c['formats']), 'explainer'),
            if (_about('format') != null) Text(_about('format')!, style: const TextStyle(color: C.faint, fontSize: 12)),
            _chips('VISUAL STYLE', 'style', styles, 'classic'),
            if (_o['style'] == 'custom')
              TextField(controller: _custom, decoration: const InputDecoration(hintText: 'Kaisa dikhe? Jaise: chalk on blackboard, madhubani art')),
            _chips('AWAAZ', 'voice', _labels(c['voices']), 'female'),
          ],
          if (k == 'slides') ...[
            _chips('FORMAT', 'format', _labels(c['formats']), 'detailed'),
            if (_about('format') != null) Text(_about('format')!, style: const TextStyle(color: C.faint, fontSize: 12)),
            _chips('KITNI SLIDES', 'length', {for (final e in _labels(c['lengths']).entries) e.key: '${_nice(e.key)} (${const {'short': 6, 'default': 10, 'long': 15}[e.key] ?? ''})'}, 'default'),
            _chips('DESIGN', 'style', styles, 'classic'),
            if (_o['style'] == 'custom')
              TextField(controller: _custom, decoration: const InputDecoration(hintText: 'Kaisa design? Jaise: navy aur gold, corporate')),
            const SizedBox(height: 10),
            TextField(controller: _audience, decoration: const InputDecoration(labelText: 'Kiske liye? (optional)', hintText: 'Jaise: bank manager, class 10 students')),
          ],
          if (k == 'infographic') ...[
            _chips('SHAPE', 'orientation', _labels(c['orientations']), 'portrait'),
            _chips('DETAIL', 'detail', _labels(c['details']), 'standard'),
            _chips('STYLE', 'style', styles, 'classic'),
          ],
          if (k == 'report') ...[
            _chips('FORMAT', 'type', _labels(nbMap(c['types'])), 'briefing'),
            const SizedBox(height: 10),
            const Caption('IN SOURCES KE LIYE SUJHAV'),
            if (_suggested == null) const LinearProgressIndicator(color: C.accent, backgroundColor: C.panel),
            for (final f in _suggested ?? const <Map<String, dynamic>>[])
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.auto_awesome_rounded, color: C.accent),
                title: Text('${f['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('${f['description']}', style: const TextStyle(color: C.muted, fontSize: 12)),
                selected: _o['type'] == 'custom' && _focus.text == f['prompt'],
                onTap: () => setState(() {
                  _o['type'] = 'custom';
                  _o['title'] = f['title'];
                  _focus.text = '${f['prompt']}';
                }),
              ),
          ],
          if (k == 'flashcards' || k == 'quiz') ...[
            _chips('KITNE', 'count', _labels(c['counts']), 'standard'),
            _chips('MUSHKIL', 'difficulty', _labels(c['difficulty']), 'medium'),
            const SizedBox(height: 10),
            TextField(controller: _topic, decoration: const InputDecoration(labelText: 'Sirf is vishay par (optional)')),
          ],
          if (k == 'table') ...[
            const SizedBox(height: 10),
            TextField(controller: _cols, decoration: const InputDecoration(labelText: 'Columns (optional)', hintText: 'Jaise: Yojana, Kisko milega, Kitna paisa, Last date')),
          ],
          const SizedBox(height: 12),
          const Caption('BHASHA'),
          DropdownButton<String>(
            isExpanded: true,
            value: widget.langs.containsKey(_o['language']) ? _o['language'] as String : null,
            hint: const Text('Hinglish'),
            dropdownColor: C.bgBottom,
            items: [for (final e in widget.langs.entries) DropdownMenuItem(value: e.key, child: Text('${e.value}'))],
            onChanged: (v) => setState(() => _o['language'] = v),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _focus,
            minLines: 2,
            maxLines: 6,
            decoration: InputDecoration(
              labelText: k == 'report' && _o['type'] == 'custom' ? 'Report kaisi ho? (zaroori)' : 'Kis par dhyaan de? (optional)',
              hintText: switch (k) {
                'audio' => 'Jaise: naye logon ke liye samjhao, sirf chapter 3, ek doosre se behas karo',
                'video' => 'Jaise: kisanon ke liye, sirf fayde aur shartein',
                'slides' => 'Jaise: 5 minute ki baat, numbers zyada',
                _ => 'Jaise: sirf important dates, exam ke hisaab se',
              },
            ),
          ),
          const SizedBox(height: 18),
          GradientButton(
            label: 'Banao',
            icon: Icons.auto_awesome_rounded,
            onTap: () {
              final o = Map<String, dynamic>.from(_o);
              if (_focus.text.trim().isNotEmpty) o['focus'] = _focus.text.trim();
              if (_custom.text.trim().isNotEmpty) o['custom_style'] = _custom.text.trim();
              if (_audience.text.trim().isNotEmpty) o['audience'] = _audience.text.trim();
              if (_topic.text.trim().isNotEmpty) o['topic'] = _topic.text.trim();
              if (_cols.text.trim().isNotEmpty) o['columns'] = _cols.text.trim();
              if (k == 'report' && o['type'] == 'custom' && (o['focus'] as String? ?? '').isEmpty) {
                nbSnack(context, 'Batayiye report kaisi ho, ya upar se ek format chuniye.');
                return;
              }
              if ((o['style'] == 'custom') && (o['custom_style'] as String? ?? '').isEmpty) {
                nbSnack(context, 'Custom style ke liye batayiye kaisa dikhe.');
                return;
              }
              Navigator.pop(context, o);
            },
          ),
          if (k == 'audio' || k == 'video')
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('Banne mein kuch minute lagte hain. Aap app band kar dijiye, taiyaar hote hi notification aayegi.',
                  textAlign: TextAlign.center, style: TextStyle(color: C.faint, fontSize: 11.5)),
            ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- note editor
class NbNoteScreen extends StatefulWidget {
  const NbNoteScreen({super.key, required this.app, required this.nid, this.note});
  final Santosh app;
  final String nid;
  final Map<String, dynamic>? note;
  @override
  State<NbNoteScreen> createState() => _NbNoteScreenState();
}

class _NbNoteScreenState extends State<NbNoteScreen> {
  late final _title = TextEditingController(text: widget.note?['title'] as String? ?? '');
  late final _body = TextEditingController(text: widget.note?['content'] as String? ?? '');
  late String? _id = widget.note?['id'] as String?;
  bool _edit = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _edit = _id == null || widget.note?['kind'] == 'user';
  }

  Future<bool> _save() async {
    if (_body.text.trim().isEmpty) {
      nbSnack(context, 'Note khaali hai');
      return false;
    }
    setState(() => _busy = true);
    try {
      final api = widget.app.api!;
      if (_id == null) {
        final n = await api.notebookNoteCreate(widget.nid, _title.text.trim(), _body.text.trim());
        _id = n['id'] as String?;
      } else {
        await api.notebookNoteUpdate(widget.nid, _id!, _title.text.trim(), _body.text.trim());
      }
      if (mounted) nbSnack(context, 'Save ho gaya');
      return true;
    } catch (e) {
      if (mounted) nbSnack(context, '$e');
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: nbBar(_id == null ? 'Naya note' : 'Note', actions: [
          if (_id != null)
            IconButton(tooltip: _edit ? 'Dekho' : 'Badlo', icon: Icon(_edit ? Icons.visibility_rounded : Icons.edit_rounded),
                onPressed: () => setState(() => _edit = !_edit)),
          if (_id != null)
            PopupMenuButton<String>(
              onSelected: (a) async {
                final api = widget.app.api!;
                try {
                  if (a == 'source') {
                    if (_edit && !await _save()) return;
                    await api.notebookNoteToSource(widget.nid, _id!);
                    if (mounted) nbSnack(context, 'Note ab ek source hai: chat aur Studio isse bhi padhenge');
                  } else if (a == 'copy') {
                    await Clipboard.setData(ClipboardData(text: _body.text));
                    if (mounted) nbSnack(context, 'Copy ho gaya');
                  } else if (a == 'delete') {
                    await api.notebookNoteDelete(widget.nid, _id!);
                    if (mounted) Navigator.pop(context);
                  }
                } catch (e) {
                  if (mounted) nbSnack(context, '$e');
                }
              },
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'source', child: Text('Source banao')),
                PopupMenuItem(value: 'copy', child: Text('Copy')),
                PopupMenuItem(value: 'delete', child: Text('Delete')),
              ],
            ),
        ]),
        body: Aurora(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            if (_edit) ...[
              TextField(controller: _title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
                  decoration: const InputDecoration(hintText: 'Title')),
              const SizedBox(height: 10),
              TextField(controller: _body, minLines: 12, maxLines: null, decoration: const InputDecoration(hintText: 'Likhiye… (# heading, - list, **bold**)')),
              const SizedBox(height: 16),
              GradientButton(label: _busy ? 'Save ho raha hai…' : 'Save', icon: Icons.check_rounded, onTap: _busy ? null : () async {
                if (await _save() && mounted) setState(() => _edit = false);
              }),
            ] else ...[
              Text(_title.text, style: display(20)),
              const SizedBox(height: 12),
              Glass(padding: const EdgeInsets.all(16), child: NbMarkdown(_body.text)),
            ],
          ]),
        ),
      );
}
