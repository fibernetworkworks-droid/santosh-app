/// v0.134 Gyaan: Profile > "<name> ka gyaan" (her knowledge base) + the source chips under answers.
/// What is in it (files, Drive folders, mail, notes), add a file / note / Drive folder, mail on-off, try a search,
/// forget one item or everything, and a quality check on the built-in test set.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _srcLabel = {
  'file': 'File',
  'drive': 'Drive',
  'mail': 'Mail',
  'note': 'Note',
  'web': 'Web',
  'record': 'Record',
  'chat': 'Pichhli baat',
};
const _srcIcon = {
  'file': Icons.description_rounded,
  'drive': Icons.add_to_drive_rounded,
  'mail': Icons.mail_rounded,
  'note': Icons.sticky_note_2_rounded,
  'web': Icons.public_rounded,
  'record': Icons.table_rows_rounded,
  'chat': Icons.forum_rounded,
};

class GyaanScreen extends StatefulWidget {
  const GyaanScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<GyaanScreen> createState() => _GyaanScreenState();
}

class _GyaanScreenState extends State<GyaanScreen> {
  Map<String, dynamic>? _st;
  String? _err;
  bool _busy = false;
  final _q = TextEditingController();
  Map<String, dynamic>? _found;
  Map<String, dynamic>? _eval;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.call('GET', '/api/gyaan');
      if (mounted) {
        setState(() {
          _st = _map(r);
          _err = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _do(Future<dynamic> Function() f, {String ok = ''}) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted && ok.isNotEmpty) _snack(context, ok);
      final note = r is Map ? _s(r['note']) : '';
      if (mounted && note.isNotEmpty) _snack(context, note);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Future<void> _addFile() async {
    final files = await pickAttachments(context, max: 6);
    for (final f in files) {
      await _do(() => widget.app.api!.uploadFile('/api/gyaan/upload', f.name, f.bytes, timeout: const Duration(seconds: 240)),
          ok: '${f.name} Gyaan mein joda');
    }
  }

  Future<String?> _ask(String title, String hint, {bool long = false}) async {
    final c = TextEditingController();
    final v = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, autofocus: true, maxLines: long ? 6 : 1, decoration: InputDecoration(hintText: hint)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(d, c.text.trim()), child: const Text('Jodo')),
        ],
      ),
    );
    return (v == null || v.isEmpty) ? null : v;
  }

  Future<void> _addNote() async {
    final title = await _ask('Note ka naam', 'jaise: Diwali offer');
    if (title == null || !mounted) return;
    final text = await _ask('Note', 'Jo Hoola ko shabdash yaad rakhna hai', long: true);
    if (text == null) return;
    await _do(() => widget.app.api!.call('POST', '/api/gyaan/notes', body: {'title': title, 'text': text}), ok: 'Note joda');
  }

  Future<void> _addDrive() async {
    final f = await _ask('Google Drive folder', 'Folder ka naam ya link');
    if (f == null) return;
    await _do(() => widget.app.api!.call('POST', '/api/gyaan/drive', body: {'folder': f}, timeout: const Duration(seconds: 240)),
        ok: 'Drive folder jud gaya; roz naya padhega');
  }

  Future<void> _setting(String key, bool v) async {
    if (key == 'mail_on' && v) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Mail Gyaan mein?'),
          content: const Text('Pichhle 60 din ki mail (newsletter / no-reply chhodkar) Gyaan mein judegi, taaki Hoola usme se '
              'jawab de sake. Aadhaar / PAN / card / OTP pehle hi chhupa diye jaate hain. Band karte hi mail Gyaan se mit jaati hai.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
            FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, jodo')),
          ],
        ),
      );
      if (ok != true) return;
    }
    await _do(() => widget.app.api!.call('PUT', '/api/gyaan/settings', body: {key: v}));
    if (key == 'mail_on' && v) {
      await _do(() => widget.app.api!.call('POST', '/api/gyaan/sync', timeout: const Duration(seconds: 240)), ok: 'Mail padh li');
    }
  }

  Future<void> _search() async {
    final q = _q.text.trim();
    if (q.isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.call('POST', '/api/gyaan/search', body: {'query': q});
      if (mounted) setState(() => _found = _map(r));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _runEval() async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.call('GET', '/api/gyaan/eval', timeout: const Duration(seconds: 120));
      if (mounted) setState(() => _eval = _map(r));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _forget(Map<String, dynamic> d) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Bhool jaun?'),
        content: Text('"${_s(d['title'])}" Gyaan se poori tarah mit jayegi (text, vectors, sab).'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Mita do')),
        ],
      ),
    );
    if (ok == true) await _do(() => widget.app.api!.call('DELETE', '/api/gyaan/docs/${d['id']}'), ok: 'Mita diya');
  }

  Future<void> _forgetAll() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Poora Gyaan mitaun?'),
        content: const Text('Files, Drive, mail, notes: sab Gyaan se mit jayega. Aapki asli files / Drive / mail ko kuch nahi hoga.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: C.bad), onPressed: () => Navigator.pop(c, true), child: const Text('Sab mita do')),
        ],
      ),
    );
    if (ok == true) await _do(() => widget.app.api!.call('DELETE', '/api/gyaan'), ok: 'Gyaan khaali');
  }

  Widget _stat(String n, String label) => Expanded(
        child: Column(children: [
          Text(n, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          Text(label, style: const TextStyle(color: C.muted, fontSize: 12)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final st = _st;
    final settings = _map(st?['settings']);
    final by = _map(st?['by_source']);
    final docs = _list(st?['recent']);
    final watches = _list(st?['watches']);
    return Scaffold(
      appBar: AppBar(title: Text('${widget.app.aName} ka gyaan'), actions: [
        IconButton(onPressed: _busy ? null : _load, icon: const Icon(Icons.refresh_rounded)),
      ]),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _busy ? null : _addFile,
        icon: const Icon(Icons.upload_file_rounded),
        label: const Text('File jodo'),
      ),
      body: st == null
          ? Center(child: _err == null ? const CircularProgressIndicator() : Padding(padding: const EdgeInsets.all(24), child: Text(_err!)))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 96), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                Glass(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${widget.app.aName} aapki files, Drive, mail aur pichhli baaton se jawab deta hai, source ke saath. '
                        'Jo usme nahi, uska andaza nahi lagata.', style: const TextStyle(color: C.muted, height: 1.35)),
                    const SizedBox(height: 12),
                    Row(children: [
                      _stat('${st['docs'] ?? 0}', 'cheezein'),
                      _stat('${st['chunks'] ?? 0}', 'hisse'),
                      _stat('${st['vectors_pct'] ?? 0}%', 'matlab-khoj'),
                    ]),
                    const SizedBox(height: 10),
                    Wrap(spacing: 6, runSpacing: 6, children: [
                      for (final e in by.entries)
                        Chip(
                          avatar: Icon(_srcIcon[e.key] ?? Icons.folder_rounded, size: 16),
                          label: Text('${_srcLabel[e.key] ?? e.key}: ${e.value}'),
                        ),
                    ]),
                    const SizedBox(height: 6),
                    Text('Khoj: ${_s(st['keyword'])} + ${_s(st['embedder'])}${_s(st['reranker']).isNotEmpty ? ' + ${st['reranker']}' : ''}',
                        style: const TextStyle(color: C.faint, fontSize: 11.5)),
                  ]),
                ),
                const SizedBox(height: 12),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Aazma ke dekhiye', style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    Row(children: [
                      Expanded(
                        child: TextField(
                          controller: _q,
                          textInputAction: TextInputAction.search,
                          onSubmitted: (_) => _search(),
                          decoration: const InputDecoration(hintText: 'jaise: dukan ka kiraya kitna hai'),
                        ),
                      ),
                      IconButton(onPressed: _busy ? null : _search, icon: const Icon(Icons.search_rounded, color: C.accent)),
                    ]),
                    if (_found != null) ...[
                      const SizedBox(height: 8),
                      if (_s(_found!['status']) != 'found')
                        Text(_s(_found!['say']), style: const TextStyle(color: C.warn))
                      else
                        for (final h in _list(_found!['hits']).take(5))
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Row(children: [
                                Icon(_srcIcon[_s(h['source'])] ?? Icons.description_rounded, size: 15, color: C.accent),
                                const SizedBox(width: 6),
                                Expanded(child: Text(_s(h['title']), style: const TextStyle(fontWeight: FontWeight.w700))),
                              ]),
                              Text(_s(h['text']), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12.5)),
                            ]),
                          ),
                    ],
                  ]),
                ),
                const SizedBox(height: 12),
                Glass(
                  child: Column(children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: settings['auto_files'] != false,
                      onChanged: _busy ? null : (v) => _setting('auto_files', v),
                      title: const Text('Chat / call mein bheji files khud jodo'),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: settings['mail_on'] == true,
                      onChanged: _busy ? null : (v) => _setting('mail_on', v),
                      title: const Text('Meri mail bhi (pichhle 60 din)'),
                      subtitle: Text(_s(st['mail_synced']).isEmpty ? 'Band' : 'Aakhri baar padhi: ${_s(st['mail_synced']).replaceFirst('T', ' ').split('.').first}'),
                    ),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.add_to_drive_rounded, color: C.accent),
                      title: const Text('Google Drive folder jodo'),
                      onTap: _busy ? null : _addDrive,
                    ),
                    for (final w in watches)
                      ListTile(
                        contentPadding: const EdgeInsets.only(left: 12),
                        dense: true,
                        title: Text(_s(w['name'])),
                        subtitle: Text(_s(w['error']).isNotEmpty ? 'Dikkat: ${_s(w['error'])}' : '${w['files'] ?? 0} files'),
                        trailing: IconButton(
                          icon: const Icon(Icons.link_off_rounded),
                          onPressed: _busy ? null : () => _do(() => widget.app.api!.call('DELETE', '/api/gyaan/drive/${w['id']}'), ok: 'Folder hata diya'),
                        ),
                      ),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.sticky_note_2_rounded, color: C.accent),
                      title: const Text('Note jodo'),
                      onTap: _busy ? null : _addNote,
                    ),
                  ]),
                ),
                const SizedBox(height: 12),
                const Padding(
                  padding: EdgeInsets.only(left: 4, bottom: 6),
                  child: Text('Gyaan mein kya hai', style: TextStyle(fontWeight: FontWeight.w700)),
                ),
                if (docs.isEmpty)
                  const Glass(child: Text('Abhi khaali. File, Drive folder ya note jodiye; chat mein bheji files khud judti hain.', style: TextStyle(color: C.muted))),
                for (final d in docs)
                  Glass(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.fromLTRB(12, 6, 4, 6),
                    child: Row(children: [
                      Icon(_srcIcon[_s(d['source'])] ?? Icons.description_rounded, color: C.accent),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(_s(d['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600)),
                          Text('${_srcLabel[_s(d['source'])] ?? _s(d['source'])} · ${d['chunks'] ?? 0} hisse'
                              '${((d['masked'] as List?) ?? const []).isNotEmpty ? ' · kuch number chhupaye' : ''}',
                              style: const TextStyle(color: C.faint, fontSize: 12)),
                        ]),
                      ),
                      if (_s(d['link']).isNotEmpty)
                        IconButton(
                          icon: const Icon(Icons.open_in_new_rounded, size: 18),
                          onPressed: () => launchUrl(Uri.parse(_s(d['link'])), mode: LaunchMode.externalApplication),
                        ),
                      IconButton(icon: const Icon(Icons.delete_outline_rounded, size: 20), onPressed: _busy ? null : () => _forget(d)),
                    ]),
                  ),
                const SizedBox(height: 12),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      const Expanded(child: Text('Khoj ki jaanch', style: TextStyle(fontWeight: FontWeight.w700))),
                      TextButton(onPressed: _busy ? null : _runEval, child: const Text('Chalao')),
                    ]),
                    const Text('Hindi, Hinglish, Marathi, English ke test sawaal: sahi source mila? Jo files mein nahi, '
                        'uspe "nahi mila" kaha?', style: TextStyle(color: C.muted, fontSize: 12.5)),
                    if (_eval != null) ...[
                      const SizedBox(height: 8),
                      Text('Sahi source: ${(((_eval!['recall'] as num?) ?? 0) * 100).round()}% · '
                          '"Nahi mila" sahi: ${(((_eval!['abstain'] as num?) ?? 0) * 100).round()}%',
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      for (final e in _map(_eval!['slices']).entries)
                        Text('${e.key}: ${((((_map(e.value))['recall'] as num?) ?? 0) * 100).round()}%', style: const TextStyle(color: C.muted)),
                    ],
                  ]),
                ),
                const SizedBox(height: 12),
                Center(
                  child: TextButton.icon(
                    onPressed: _busy ? null : _forgetAll,
                    icon: const Icon(Icons.delete_forever_rounded, color: C.bad),
                    label: const Text('Poora Gyaan mitao', style: TextStyle(color: C.bad)),
                  ),
                ),
              ]),
            ),
    );
  }
}

/// Source chips under an answer that used Gyaan: [1] Rent agreement · File ... tap = the passage it came from.
class GyaanSourcesCard extends StatelessWidget {
  const GyaanSourcesCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  void _open(BuildContext context, Map<String, dynamic> s) {
    showModalBottomSheet(
      context: context,
      backgroundColor: C.bgBottom,
      isScrollControlled: true,
      builder: (c) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('[${s['n']}] ${_s(s['title'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 4),
            Text([
              _srcLabel[_s(s['source'])] ?? _s(s['source']),
              if ((s['page'] as num? ?? 0) > 0) 'page ${s['page']}',
              if (_s(s['at']).isNotEmpty) _s(s['at']),
            ].join(' · '), style: const TextStyle(color: C.faint, fontSize: 12)),
            const SizedBox(height: 10),
            Flexible(child: SingleChildScrollView(child: SelectableText(_s(s['snippet']), style: const TextStyle(height: 1.4)))),
            const SizedBox(height: 10),
            Row(children: [
              TextButton.icon(
                onPressed: () => Clipboard.setData(ClipboardData(text: _s(s['snippet']))),
                icon: const Icon(Icons.copy_rounded, size: 16),
                label: const Text('Copy'),
              ),
              if (_s(s['link']).isNotEmpty)
                TextButton.icon(
                  onPressed: () => launchUrl(Uri.parse(_s(s['link'])), mode: LaunchMode.externalApplication),
                  icon: const Icon(Icons.open_in_new_rounded, size: 16),
                  label: const Text('Kholo'),
                ),
              const Spacer(),
              TextButton(
                onPressed: () {
                  Navigator.pop(c);
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => GyaanScreen(app: app)));
                },
                child: const Text('Gyaan'),
              ),
            ]),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final src = _list(data['sources']);
    if (src.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(left: 4, right: 40, bottom: 4),
      child: Wrap(spacing: 6, runSpacing: 6, children: [
        for (final s in src)
          ActionChip(
            avatar: Icon(_srcIcon[_s(s['source'])] ?? Icons.description_rounded, size: 15, color: C.accent),
            label: Text('[${s['n']}] ${_s(s['title'])}', overflow: TextOverflow.ellipsis),
            onPressed: () => _open(context, s),
          ),
      ]),
    );
  }
}
