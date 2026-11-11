// v0.821 HOOLA DOCUMENTS on the phone (docs/DOCUMENT_KIT_PLAN.md D7): Scan to PDF with the camera, every pdf_kit
// tool as a list (the same grid the console page shows, read from /api/dockit/tools), her saved workflows.
// Every action runs the SAME pdf_kit the chat uses (/api/dockit/run); the result opens through its signed link.
// A password is never typed here: a lock gives a one-time link that opens in the browser.
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _ms(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

class _Hint extends StatelessWidget {
  const _Hint(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(text, style: const TextStyle(color: C.muted, fontSize: 13));
}

class _Doc {
  _Doc(this.id, this.name, this.size);
  final String id;
  final String name;
  final int size;
}

Future<_Doc> _upload(Santosh app, String name, List<int> bytes) async {
  final r = await app.api!.uploadFile('/api/dockit/upload', name, bytes, tries: 2, timeout: const Duration(seconds: 240));
  return _Doc(_s(r['file_id']), _s(r['name']).isEmpty ? name : _s(r['name']), (r['size'] as num?)?.toInt() ?? bytes.length);
}

Future<Map<String, dynamic>> _run(Santosh app, String action, Map<String, dynamic> args) async {
  final r = await app.api!.call('POST', '/api/dockit/run', body: {'action': action, 'args': args}, timeout: const Duration(minutes: 10));
  return _m(_m(r)['result']);
}

Future<void> _open(Santosh app, String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(app.api!.absolute(url)), mode: LaunchMode.externalApplication);
}

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  Map<String, dynamic>? _cat;
  Map<String, dynamic>? _flows;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = _m(await widget.app.api!.call('GET', '/api/dockit/tools'));
      final f = _m(await widget.app.api!.call('GET', '/api/dockit/flows'));
      if (mounted) setState(() {
        _cat = c;
        _flows = f;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  void _openTool(Map<String, dynamic> t) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => DocToolPage(app: widget.app, tool: t)));

  Widget _tools() {
    final groups = _ms(_cat?['groups']);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
      Glass(
        child: InkWell(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ScanToPdfPage(app: widget.app))),
          child: const Row(children: [
            Icon(Icons.document_scanner_rounded, color: C.accent, size: 32),
            SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Scan to PDF', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              Text('Photos of pages with the camera -> one searchable PDF', style: TextStyle(color: C.muted, fontSize: 13)),
            ])),
            Icon(Icons.chevron_right_rounded),
          ]),
        ),
      ),
      const SizedBox(height: 8),
      for (final g in groups) ...[
        Padding(padding: const EdgeInsets.fromLTRB(4, 16, 4, 6),
            child: Text(_s(g['group']), style: const TextStyle(color: C.faint, fontWeight: FontWeight.w700))),
        Glass(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          child: Column(children: [
            for (final t in _ms(g['items']))
              ListTile(
                dense: true,
                title: Text(_s(t['title']), style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(_s(t['line']), style: const TextStyle(color: C.muted)),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => _openTool(t),
              ),
          ]),
        ),
      ],
      const SizedBox(height: 12),
      const _Hint('Free, on Hoola\'s own server. Your original is never changed. Files are kept 24 hours.'),
    ]);
  }

  Widget _flowList() {
    final mine = _ms(_flows?['mine']);
    final ready = _ms(_flows?['ready_made']);
    Widget row(Map<String, dynamic> f, bool isMine) => ListTile(
          title: Text(_s(f['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text([_s(f['line']), _s(f['steps'])].where((x) => x.isNotEmpty).join(' · '),
              style: const TextStyle(color: C.muted)),
          trailing: const Icon(Icons.play_arrow_rounded, color: C.accent),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => DocToolPage(app: widget.app, tool: {
                    'id': 'flow', 'title': _s(f['name']), 'line': _s(f['steps']), 'input': 'files', 'opts': const [],
                    'workflow': _s(f['key']),
                  }))).then((_) => _load()),
          onLongPress: !isMine
              ? null
              : () async {
                  final ok = await showDialog<bool>(
                      context: context,
                      builder: (d) => AlertDialog(title: Text('Delete "${_s(f['name'])}"?'), actions: [
                            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep')),
                            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Delete')),
                          ]));
                  if (ok != true) return;
                  try {
                    await widget.app.api!.call('DELETE', '/api/dockit/flows/${Uri.encodeComponent(_s(f['key']))}');
                  } catch (e) {
                    if (mounted) _snack(context, '$e');
                  }
                  _load();
                },
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
      const _Hint('A chain of steps run as one job, on one file or a batch. Make your own by asking Hoola in chat: '
          '"save a workflow: merge, page numbers, under 5 MB, lock - name it CA ke liye".'),
      const SizedBox(height: 10),
      if (mine.isNotEmpty) ...[
        const Padding(padding: EdgeInsets.fromLTRB(4, 8, 4, 6), child: Text('Yours (long-press to delete)', style: TextStyle(color: C.faint))),
        Glass(padding: const EdgeInsets.symmetric(horizontal: 6), child: Column(children: [for (final f in mine) row(f, true)])),
      ],
      const Padding(padding: EdgeInsets.fromLTRB(4, 16, 4, 6), child: Text('Ready-made', style: TextStyle(color: C.faint))),
      Glass(padding: const EdgeInsets.symmetric(horizontal: 6), child: Column(children: [for (final f in ready) row(f, false)])),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Documents'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(children: [
            for (final (i, label) in [(0, 'All tools'), (1, 'Workflows')])
              Padding(padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(label: Text(label), selected: _tab == i, onSelected: (_) => setState(() => _tab = i))),
          ]),
        ),
        Expanded(child: _cat == null ? const Center(child: CircularProgressIndicator()) : (_tab == 0 ? _tools() : _flowList())),
      ]),
    );
  }
}

// ------------------------------------------------------------------------------------------- one tool
class DocToolPage extends StatefulWidget {
  const DocToolPage({super.key, required this.app, required this.tool});
  final Santosh app;
  final Map<String, dynamic> tool;
  @override
  State<DocToolPage> createState() => _DocToolPageState();
}

class _DocToolPageState extends State<DocToolPage> {
  final List<_Doc> _files = [];
  final Map<String, dynamic> _vals = {};
  final Map<String, TextEditingController> _text = {};
  bool _busy = false;
  bool _each = false;
  Map<String, dynamic>? _res;
  String _err = '';

  String get _input => _s(widget.tool['input']);

  @override
  void initState() {
    super.initState();
    for (final o in (widget.tool['opts'] as List? ?? const [])) {
      final l = List<dynamic>.from(o as List);
      final key = _s(l[0]), kind = _s(l[2]);
      _vals[key] = l[3];
      if (kind == 'text' || kind == 'number' || kind == 'pages') _text[key] = TextEditingController(text: _s(l[3]));
    }
  }

  @override
  void dispose() {
    for (final c in _text.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pick() async {
    final pdfOnly = _input == 'pdf' || _input == 'two';
    final pick = await FilePicker.platform.pickFiles(
        withData: true, allowMultiple: _input != 'pdf', type: pdfOnly ? FileType.custom : FileType.any,
        allowedExtensions: pdfOnly ? const ['pdf'] : null);
    if (pick == null) return;
    setState(() => _busy = true);
    try {
      for (final f in pick.files) {
        if (f.bytes == null) continue;
        if (f.bytes!.length > 25 * 1024 * 1024) {
          if (mounted) _snack(context, '${f.name} is over 25 MB. Send it to Hoola in chat as a Drive link.');
          continue;
        }
        final d = await _upload(widget.app, f.name, f.bytes!);
        if (_input == 'pdf') _files.clear();
        _files.add(d);
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Map<String, dynamic> _opts() {
    final out = <String, dynamic>{};
    for (final o in (widget.tool['opts'] as List? ?? const [])) {
      final l = List<dynamic>.from(o as List);
      final key = _s(l[0]), kind = _s(l[2]);
      if (_text.containsKey(key)) {
        final t = _text[key]!.text.trim();
        if (t.isEmpty) continue;
        out[key] = kind == 'number' ? (num.tryParse(t) ?? t) : t;
      } else if (_vals[key] != null) {
        out[key] = _vals[key];
      }
    }
    return out;
  }

  Future<void> _go() async {
    final ids = _files.map((f) => f.id).toList();
    final isFlow = widget.tool['id'] == 'flow';
    var action = _s(widget.tool['id']);
    var args = _opts();
    if (_input != 'url') {
      String? why;
      if (ids.isEmpty) {
        why = 'Add the file first.';
      } else if (_input == 'pdfs' && ids.length < 2) {
        why = 'Add two or more files.';
      } else if (_input == 'two' && ids.length != 2) {
        why = 'Add two PDFs: the old version, then the new.';
      }
      if (why != null) {
        _snack(context, why);
        return;
      }
    }
    if (isFlow) {
      args = {'workflow': widget.tool['workflow'], 'file_ids': ids, 'batch': _each};
    } else if (_each && ids.length > 1) {
      args = {'steps': [{'action': action, ...args}], 'file_ids': ids, 'batch': true, 'workflow': widget.tool['title']};
      action = 'flow';
    } else if (_input == 'pdf') {
      args['file_id'] = ids.first;
    } else if (_input != 'url') {
      args['file_ids'] = ids;
    }
    setState(() {
      _busy = true;
      _res = null;
      _err = '';
    });
    try {
      final r = await _run(widget.app, action, args);
      if (mounted) setState(() => _res = r);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _opt(List<dynamic> l) {
    final key = _s(l[0]), label = _s(l[1]), kind = _s(l[2]);
    if (kind == 'bool') {
      return SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(label), value: _vals[key] == true,
          onChanged: (v) => setState(() => _vals[key] = v));
    }
    if (kind == 'select') {
      final choices = (l[4] as List).map((e) => '$e').toList();
      final cur = choices.contains(_s(_vals[key])) ? _s(_vals[key]) : choices.first;
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: DropdownButtonFormField<String>(
          value: cur,
          decoration: InputDecoration(labelText: label),
          items: [for (final c in choices) DropdownMenuItem(value: c, child: Text(c))],
          onChanged: (v) => setState(() => _vals[key] = v),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: TextField(controller: _text[key], decoration: InputDecoration(labelText: label),
          keyboardType: kind == 'number' ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text),
    );
  }

  List<Map<String, dynamic>> _outs(Map<String, dynamic> r) {
    final out = <Map<String, dynamic>>[];
    if (r['zip'] is Map) {
      out.add(_m(r['zip']));
    } else if (r['files'] is List && _ms(r['files']).isNotEmpty && _ms(r['files']).first['file_id'] != null) {
      out.addAll(_ms(r['files']));
    } else if (r['file_id'] != null) {
      out.add(r);
    }
    if (r['report'] is Map) out.add(_m(r['report']));
    if (r['preview_file_id'] != null) out.add({'name': 'Redaction preview', 'url': r['preview_url']});
    return out;
  }

  Widget _result(Map<String, dynamic> r) {
    final lines = <String>[
      for (final k in ['money_changed', 'dates_changed', 'warnings', 'notes', 'check_these', 'did_not_fit'])
        for (final x in (r[k] as List? ?? const [])) '• $x',
      for (final f in _ms(r['failed'])) '✕ ${_s(f['why'])}',
    ];
    final links = <(String, String)>[
      if (_s(r['password_link']).isNotEmpty) ('See the password once', _s(r['password_link'])),
      for (final l in _ms(r['password_links'])) ('Password: ${_s(l['file'])}', _s(l['link'])),
      if (_s(r['link']).isNotEmpty) ('Open the private page', _s(r['link'])),
    ];
    return Glass(
      tint: C.ok,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Done', style: TextStyle(fontWeight: FontWeight.w800, color: C.ok)),
        for (final f in _outs(r))
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.description_rounded, color: C.accent),
            title: Text(_s(f['name']), maxLines: 2, overflow: TextOverflow.ellipsis),
            subtitle: f['kb'] != null ? Text('${f['kb']} KB') : null,
            trailing: IconButton(icon: const Icon(Icons.open_in_new_rounded), onPressed: () => _open(widget.app, _s(f['url']))),
          ),
        if (_s(r['checked']).isNotEmpty) Text(_s(r['checked']), style: const TextStyle(color: C.ok, fontSize: 13)),
        for (final (label, url) in links)
          Padding(padding: const EdgeInsets.only(top: 8),
              child: GlassButton(label: label, icon: Icons.lock_open_rounded, onTap: () => _open(widget.app, url))),
        if (r['redact_id'] != null) ...[
          const SizedBox(height: 8),
          const Text('Nothing is removed yet. Check the preview first.', style: TextStyle(color: C.warn)),
          const SizedBox(height: 6),
          GradientButton(label: 'Remove for good', icon: Icons.delete_forever_rounded, onTap: _busy ? null : () async {
            setState(() => _busy = true);
            try {
              final a = await _run(widget.app, 'redact_apply', {'redact_id': r['redact_id']});
              if (mounted) setState(() => _res = a);
            } catch (e) {
              if (mounted) setState(() => _err = '$e');
            }
            if (mounted) setState(() => _busy = false);
          }),
        ],
        if (_s(r['answer'] ?? r['summary']).isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 8), child: SelectableText(_s(r['answer'] ?? r['summary']))),
        for (final p in _ms(r['parts'])) Text('• ${_s(p['title'])}: pages ${_s(p['pages'])}'),
        if (_s(r['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_s(r['say']))),
        for (final l in lines.take(30)) Text(l, style: const TextStyle(color: C.warn, fontSize: 13)),
        if (_s(r['kept_for']).isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 8),
              child: Text('Kept for ${_s(r['kept_for'])}.', style: const TextStyle(color: C.faint, fontSize: 12))),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.tool;
    final opts = (t['opts'] as List? ?? const []).map((o) => List<dynamic>.from(o as List)).toList();
    final canBatch = _input == 'pdf' || _input == 'files';
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(t['title']))),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
        Text(_s(t['line']), style: const TextStyle(color: C.muted)),
        const SizedBox(height: 12),
        if (_input != 'url') ...[
          GlassButton(label: _files.isEmpty ? 'Choose files' : 'Add more files', icon: Icons.attach_file_rounded,
              onTap: _busy ? null : _pick),
          const SizedBox(height: 8),
          for (var i = 0; i < _files.length; i++)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Text('${i + 1}', style: const TextStyle(color: C.faint)),
              title: Text(_files[i].name, maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: Text('${(_files[i].size / 1024).ceil()} KB'),
              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                if (i > 0)
                  IconButton(icon: const Icon(Icons.arrow_upward_rounded), tooltip: 'Move up',
                      onPressed: () => setState(() => _files.insert(i - 1, _files.removeAt(i)))),
                IconButton(icon: const Icon(Icons.close_rounded), tooltip: 'Remove',
                    onPressed: () => setState(() => _files.removeAt(i))),
              ]),
            ),
        ],
        const SizedBox(height: 8),
        for (final o in opts) _opt(o),
        if (canBatch && _files.length > 1)
          SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Each file on its own (batch)'), value: _each,
              onChanged: (v) => setState(() => _each = v)),
        const SizedBox(height: 8),
        GradientButton(label: _busy ? 'Working on it…' : _s(t['title']), icon: Icons.play_arrow_rounded, onTap: _busy ? null : _go),
        if (_busy) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()),
        if (_err.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_err, style: const TextStyle(color: C.bad))),
        if (_res != null) Padding(padding: const EdgeInsets.only(top: 12), child: _result(_res!)),
      ]),
    );
  }
}

// ------------------------------------------------------------------------------------------- scan to PDF
class ScanToPdfPage extends StatefulWidget {
  const ScanToPdfPage({super.key, required this.app});
  final Santosh app;
  @override
  State<ScanToPdfPage> createState() => _ScanToPdfPageState();
}

class _ScanToPdfPageState extends State<ScanToPdfPage> {
  final List<XFile> _shots = [];
  bool _busy = false;
  bool _searchable = true;
  String _state = '';
  Map<String, dynamic>? _res;

  Future<void> _shoot(ImageSource src) async {
    try {
      if (src == ImageSource.gallery) {
        final xs = await ImagePicker().pickMultiImage(imageQuality: 85, maxWidth: 2400);
        if (xs.isNotEmpty) setState(() => _shots.addAll(xs));
        return;
      }
      final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 85, maxWidth: 2400);
      if (x != null) setState(() => _shots.add(x));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _make() async {
    if (_shots.isEmpty) {
      _snack(context, 'Take a photo of the first page.');
      return;
    }
    setState(() {
      _busy = true;
      _res = null;
    });
    try {
      final ids = <String>[];
      for (var i = 0; i < _shots.length; i++) {
        setState(() => _state = 'Uploading page ${i + 1} of ${_shots.length}…');
        final bytes = await _shots[i].readAsBytes();
        ids.add((await _upload(widget.app, 'page ${i + 1}.jpg', bytes)).id);
      }
      setState(() => _state = 'Making the PDF…');
      final r = await _run(widget.app, 'flow', {
        'workflow': 'Scan',
        'steps': [
          {'action': 'to_pdf', 'page_size': 'a4', 'margin': 'small'},
          if (_searchable) {'action': 'ocr'},
          {'action': 'compress'},
        ],
        'file_ids': ids,
      });
      if (mounted) setState(() => _res = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() {
      _busy = false;
      _state = '';
    });
  }

  @override
  Widget build(BuildContext context) {
    final r = _res;
    final out = r == null ? null : (r['file_id'] != null ? r : (_ms(r['files']).isNotEmpty ? _ms(r['files']).first : null));
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Scan to PDF')),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
        const _Hint('Photograph each page flat, in good light. The pages go into one A4 PDF in this order.'),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: GlassButton(label: 'Camera', icon: Icons.photo_camera_rounded, onTap: _busy ? null : () => _shoot(ImageSource.camera))),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Gallery', icon: Icons.photo_library_rounded, onTap: _busy ? null : () => _shoot(ImageSource.gallery))),
        ]),
        const SizedBox(height: 8),
        for (var i = 0; i < _shots.length; i++)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.image_rounded, color: C.accent),
            title: Text('Page ${i + 1}'),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
              if (i > 0)
                IconButton(icon: const Icon(Icons.arrow_upward_rounded), tooltip: 'Move up',
                    onPressed: () => setState(() => _shots.insert(i - 1, _shots.removeAt(i)))),
              IconButton(icon: const Icon(Icons.close_rounded), tooltip: 'Remove', onPressed: () => setState(() => _shots.removeAt(i))),
            ]),
          ),
        SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Make the words searchable'),
            subtitle: const Text('Reads the pages so you can search and copy them'), value: _searchable,
            onChanged: (v) => setState(() => _searchable = v)),
        const SizedBox(height: 8),
        GradientButton(label: _busy ? 'Working on it…' : 'Make PDF (${_shots.length} pages)', icon: Icons.picture_as_pdf_rounded,
            onTap: _busy ? null : _make),
        if (_state.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_state, style: const TextStyle(color: C.muted))),
        if (_busy) const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator()),
        if (out != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Glass(
              tint: C.ok,
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.picture_as_pdf_rounded, color: C.ok),
                title: Text(_s(out['name'])),
                subtitle: Text('${_s(out['kb'])} KB · kept 24 hours'),
                trailing: IconButton(icon: const Icon(Icons.open_in_new_rounded), onPressed: () => _open(widget.app, _s(out['url']))),
              ),
            ),
          ),
      ]),
    );
  }
}
