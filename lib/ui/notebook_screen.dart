import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

const _makeKinds = <String, String>{
  'summary': 'Summary',
  'study_guide': 'Study guide',
  'briefing': 'Briefing',
  'faq': 'FAQ',
  'timeline': 'Timeline',
  'mind_map': 'Mind map',
  'quiz': 'Quiz',
  'action_items': 'Kaam ki list',
};
const _langs = <String, String>{'hinglish': 'Hinglish', 'hi': 'हिंदी', 'en': 'English', 'mr': 'मराठी'};

IconData _srcIcon(String kind) => switch (kind) {
      'web' => Icons.language_rounded,
      'youtube' => Icons.smart_display_rounded,
      'file' => Icons.description_rounded,
      'email' => Icons.mail_outline_rounded,
      'drive' => Icons.add_to_drive_rounded,
      'sheet' => Icons.table_chart_rounded,
      _ => Icons.notes_rounded,
    };

/// Chat card: a notebook Santosh made or updated, or a study guide / FAQ it wrote.
class NotebookCard extends StatelessWidget {
  const NotebookCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'created';
    final noteTitle = v['note_title'] as String?;
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
          GlassButton(label: 'Notebook kholiye', icon: Icons.menu_book_rounded, height: 42, onTap: () {
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: app, id: v['id'] as String)));
          }),
        ]),
      ),
    );
  }
}

/// Profile > Santosh Notebook: all notebooks.
class NotebooksScreen extends StatefulWidget {
  const NotebooksScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<NotebooksScreen> createState() => _NotebooksScreenState();
}

class _NotebooksScreenState extends State<NotebooksScreen> {
  List<Map<String, dynamic>> _list = [];
  bool _loaded = false;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.notebooks();
      if (mounted) setState(() { _list = r; _loaded = true; _err = null; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _new() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Nayi notebook'),
        content: TextField(controller: c, autofocus: true, decoration: const InputDecoration(hintText: 'Jaise: GST rules, ITPC training, Q3 review')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Banaiye')),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    try {
      final nb = await widget.app.api!.notebookCreate(c.text.trim());
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: widget.app, id: nb['id'] as String)));
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola Notebook'), backgroundColor: Colors.transparent),
      floatingActionButton: FloatingActionButton.extended(onPressed: _new, icon: const Icon(Icons.add_rounded), label: const Text('Nayi notebook')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 96), children: [
            const Text('NotebookLM jaisa: PDF, Word, PowerPoint, Drive files, emails, website links aur notes jodiye. Hoola '
                'sirf unhi se jawab deta hai (source ke saath), study guide / FAQ / briefing banata hai, aur do logon ki baatcheet '
                'wala audio overview Hindi / Hinglish mein sunata hai.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 14),
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded && _list.isEmpty)
              const Padding(padding: EdgeInsets.all(20), child: Text('Abhi koi notebook nahi. Neeche "Nayi notebook" dabaiye, ya boliye: '
                  '"GST ki in PDFs se ek notebook banao".', style: TextStyle(color: C.chip))),
            for (final nb in _list)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Text(nb['emoji'] as String? ?? '📒', style: const TextStyle(fontSize: 26)),
                  title: Text(nb['title'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('${nb['sources']} sources', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () async {
                    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebookDetailScreen(app: widget.app, id: nb['id'] as String)));
                    _load();
                  },
                )),
              ),
          ]),
        ),
      ),
    );
  }
}

/// One notebook: sources, ask with citations, make study guides etc., audio overview.
class NotebookDetailScreen extends StatefulWidget {
  const NotebookDetailScreen({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<NotebookDetailScreen> createState() => _NotebookDetailScreenState();
}

class _NotebookDetailScreenState extends State<NotebookDetailScreen> {
  Map<String, dynamic> _nb = {};
  bool _busy = false;
  String? _busyText;
  Map<String, dynamic>? _answer;
  final _q = TextEditingController();
  String _lang = 'hinglish';

  Santosh get app => widget.app;
  List<Map<String, dynamic>> _l(String k) =>
      List<Map<String, dynamic>>.from((_nb[k] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.notebook(widget.id);
      if (mounted) setState(() => _nb = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  void _snack(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _work(String label, Future<void> Function() f) async {
    setState(() { _busy = true; _busyText = label; });
    try {
      await f();
    } catch (e) {
      _snack(e.toString());
    } finally {
      if (mounted) setState(() { _busy = false; _busyText = null; });
    }
  }

  Future<void> _addLink() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Link jodiye'),
        content: TextField(controller: c, keyboardType: TextInputType.url, decoration: const InputDecoration(hintText: 'Website, PDF link ya YouTube')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodiye')),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    await _work('Link padh raha hoon…', () async {
      final r = await app.api!.notebookAddSource(widget.id, {'url': c.text.trim()});
      setState(() => _nb = r);
    });
  }

  Future<void> _addText() async {
    final t = TextEditingController();
    final body = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Notes jodiye'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: t, decoration: const InputDecoration(labelText: 'Naam')),
          TextField(controller: body, minLines: 5, maxLines: 12, decoration: const InputDecoration(labelText: 'Text paste kijiye')),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodiye')),
        ],
      ),
    );
    if (ok != true || body.text.trim().isEmpty) return;
    await _work('Jod raha hoon…', () async {
      final r = await app.api!.notebookAddSource(widget.id, {'text': body.text, 'title': t.text.trim()});
      setState(() => _nb = r);
    });
  }

  Future<void> _addFile() async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom,
        allowedExtensions: const ['pdf', 'docx', 'pptx', 'xlsx', 'csv', 'txt', 'md']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    await _work('${f.name} padh raha hoon…', () async {
      final r = await app.api!.notebookUpload(widget.id, f.name, f.bytes!);
      setState(() => _nb = r);
    });
  }

  Future<void> _ask() async {
    final q = _q.text.trim();
    if (q.isEmpty) return;
    FocusScope.of(context).unfocus();
    await _work('Sources mein dhoondh raha hoon…', () async {
      final r = await app.api!.notebookAsk(widget.id, q);
      setState(() => _answer = r);
    });
  }

  Future<void> _make(String kind) async {
    await _work('${_makeKinds[kind]} likh raha hoon…', () async {
      final r = await app.api!.notebookMake(widget.id, kind, language: _lang);
      await _load();
      if (mounted) _showNote(r['title'] as String? ?? '', r['content'] as String? ?? '');
    });
  }

  void _showNote(String title, String content) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.85,
        builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.all(18), children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
          const SizedBox(height: 10),
          SelectableText(content, style: const TextStyle(fontSize: 14, height: 1.45, color: C.ink)),
        ]),
      ),
    );
  }

  Future<void> _audio(String style) async {
    await _work('Audio shuru kar raha hoon…', () async {
      await app.api!.notebookAudio(widget.id, style: style, language: _lang, conv: app.conversationId ?? '');
      _snack('Audio overview ban raha hai (2-5 min). Taiyaar hone par notification aayega.');
      await _load();
    });
  }

  Future<void> _play(String aid) async {
    try {
      final url = await app.api!.notebookAudioUrl(widget.id, aid);
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Notebook delete karein?'),
        content: const Text('Iske sources, notes aur audio hat jayenge. Aapki asli files par koi asar nahi.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await app.api!.notebookDelete(widget.id);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      _snack(e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final sources = _l('sources');
    final notes = _l('notes');
    final audio = _l('audio');
    final cites = List<Map<String, dynamic>>.from(((_answer?['citations'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Scaffold(
      appBar: AppBar(
        title: Text('${_nb['emoji'] ?? '📒'} ${_nb['title'] ?? 'Notebook'}'),
        backgroundColor: Colors.transparent,
        actions: [IconButton(tooltip: 'Delete', onPressed: _delete, icon: const Icon(Icons.delete_outline_rounded))],
      ),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            if (_busy)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(children: [
                  const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.accent)),
                  const SizedBox(width: 10),
                  Text(_busyText ?? '…', style: const TextStyle(color: C.chip)),
                ]),
              ),
            // ---- ask ----
            Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Poochiye', style: TextStyle(fontWeight: FontWeight.w700)),
              Row(children: [
                Expanded(child: TextField(controller: _q, minLines: 1, maxLines: 3, onSubmitted: (_) => _ask(),
                    decoration: const InputDecoration(hintText: 'Sources se kuch bhi poochiye…'))),
                IconButton(onPressed: _busy || sources.isEmpty ? null : _ask, icon: const Icon(Icons.send_rounded, color: C.accent)),
              ]),
              if (_answer != null) ...[
                const SizedBox(height: 8),
                SelectableText(_answer!['answer'] as String? ?? '', style: const TextStyle(fontSize: 14, height: 1.45)),
                for (final c in cites)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text('[${c['n']}] ${c['title']} — “${c['snippet']}”', maxLines: 3, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ),
              ],
            ])),
            const SizedBox(height: 14),
            // ---- sources ----
            Row(children: [
              Text('Sources (${sources.length})', style: const TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              IconButton(tooltip: 'File', onPressed: _busy ? null : _addFile, icon: const Icon(Icons.upload_file_rounded, color: C.chip)),
              IconButton(tooltip: 'Link', onPressed: _busy ? null : _addLink, icon: const Icon(Icons.link_rounded, color: C.chip)),
              IconButton(tooltip: 'Notes', onPressed: _busy ? null : _addText, icon: const Icon(Icons.edit_note_rounded, color: C.chip)),
            ]),
            if (sources.isEmpty)
              const Text('File, link ya notes jodiye. Ya chat mein boliye: "Drive ki GST wali PDF is notebook mein jodo".',
                  style: TextStyle(color: C.muted, fontSize: 13)),
            for (final s in sources)
              Glass(child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(_srcIcon(s['kind'] as String? ?? ''), color: C.teal),
                title: Text('${s['n']}. ${s['title']}', maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Text([
                  '${((s['chars'] as num? ?? 0) / 1000).toStringAsFixed(0)}k akshar',
                  if ((s['note'] as String? ?? '').isNotEmpty) s['note'] as String,
                ].join(' · '), style: const TextStyle(color: C.muted, fontSize: 12)),
                trailing: IconButton(icon: const Icon(Icons.close_rounded, color: C.muted, size: 20), onPressed: _busy ? null : () =>
                    _work('Hata raha hoon…', () async { final r = await app.api!.notebookRemoveSource(widget.id, s['id'] as String); setState(() => _nb = r); })),
              )),
            const SizedBox(height: 14),
            // ---- make ----
            Row(children: [
              const Text('Banaiye', style: TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              DropdownButton<String>(
                value: _lang,
                underline: const SizedBox.shrink(),
                items: [for (final e in _langs.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
                onChanged: (v) => setState(() => _lang = v ?? 'hinglish'),
              ),
            ]),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final e in _makeKinds.entries)
                ActionChip(label: Text(e.value), onPressed: _busy || sources.isEmpty ? null : () => _make(e.key)),
            ]),
            const SizedBox(height: 14),
            // ---- audio ----
            const Text('Audio overview (podcast)', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 8, children: [
              ActionChip(avatar: const Icon(Icons.headphones_rounded, size: 18), label: const Text('Chhota (3 min)'),
                  onPressed: _busy || sources.isEmpty ? null : () => _audio('brief')),
              ActionChip(avatar: const Icon(Icons.headphones_rounded, size: 18), label: const Text('Gehra (8 min)'),
                  onPressed: _busy || sources.isEmpty ? null : () => _audio('deep_dive')),
              ActionChip(avatar: const Icon(Icons.forum_rounded, size: 18), label: const Text('Bahas'),
                  onPressed: _busy || sources.isEmpty ? null : () => _audio('debate')),
            ]),
            for (final a in audio)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(a['status'] == 'ready' ? Icons.play_circle_fill_rounded : a['status'] == 'failed' ? Icons.error_outline_rounded : Icons.hourglass_top_rounded,
                    color: a['status'] == 'ready' ? C.accent : a['status'] == 'failed' ? C.bad : C.chip),
                title: Text('${_langs[a['language']] ?? a['language']} · ${a['style'] == 'brief' ? 'chhota' : a['style'] == 'debate' ? 'bahas' : 'gehra'}'),
                subtitle: Text(a['status'] == 'ready' ? '${((a['seconds'] as num? ?? 0) ~/ 60)} min ${((a['seconds'] as num? ?? 0) % 60)} sec'
                    : a['status'] == 'failed' ? (a['error'] as String? ?? 'fail') : 'ban raha hai…', style: const TextStyle(color: C.muted, fontSize: 12)),
                onTap: a['status'] == 'ready' ? () => _play(a['id'] as String) : _load,
              ),
            const SizedBox(height: 14),
            // ---- notes ----
            if (notes.isNotEmpty) ...[
              const Text('Notes', style: TextStyle(fontWeight: FontWeight.w700)),
              for (final n in notes)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.sticky_note_2_outlined, color: C.chip),
                  title: Text(n['title'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: Text(n['preview'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
                  onTap: () async {
                    try {
                      final full = await app.api!.notebookNote(widget.id, n['id'] as String);
                      _showNote(full['title'] as String? ?? '', full['content'] as String? ?? '');
                    } catch (e) {
                      _snack(e.toString());
                    }
                  },
                ),
            ],
          ]),
        ),
      ),
    );
  }
}
