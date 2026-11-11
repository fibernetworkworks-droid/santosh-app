/// Profile > Lekhak (v0.87): Hoola as typist + translator.
/// Likho (speak or type a letter -> formal draft), Anuvaad (translation with locked facts + back-check), Sudhaar (grammar with
/// every change listed, Kruti Dev <-> Unicode), Kaagaz (all documents), Niyam (her name / address / letterhead, signature
/// picture, glossary, keep words, rules, address book). Chat cards: LekhakDocCard, LekhakSignCard (only her tap signs).
library;

import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import '../voice_recorder.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _langs = {'hi': 'हिंदी', 'mr': 'मराठी', 'en': 'English', 'gu': 'ગુજરાતી', 'ta': 'தமிழ்', 'te': 'తెలుగు', 'kn': 'ಕನ್ನಡ', 'bn': 'বাংলা', 'pa': 'ਪੰਜਾਬੀ', 'ml': 'മലയാളം', 'ur': 'اردو'};
const _kinds = {
  'application': 'Application',
  'leave': 'Holiday',
  'complaint': 'Complaint',
  'noc': 'NOC',
  'bank': 'Bank',
  'authority': 'Authority',
  'certificate': 'Certificate',
  'office': 'Office',
  'reply': 'Reply',
  'affidavit': 'Affidavit draft',
};
const _status = {'draft': 'Draft', 'waiting_sign': 'Signature pending', 'signed': 'Final', 'ready': 'Ready', 'rejected': 'Back'};
Color _statusCol(String s) => switch (s) { 'signed' => C.ok, 'waiting_sign' => C.accent, 'rejected' => C.faint, 'ready' => C.teal, _ => C.accentSoft };

Future<String?> _askText(BuildContext context, String title, {String label = '', String init = '', int lines = 1}) async {
  final c = TextEditingController(text: init);
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(controller: c, minLines: lines, maxLines: lines > 1 ? 14 : 1, autofocus: true, decoration: InputDecoration(labelText: label)),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Leave it')),
        FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('OK')),
      ],
    ),
  );
  return ok == true ? c.text.trim() : null;
}

class LekhakScreen extends StatefulWidget {
  const LekhakScreen({super.key, required this.app, this.tab = 0});
  final Santosh app;
  final int tab;
  @override
  State<LekhakScreen> createState() => _LekhakScreenState();
}

class _LekhakScreenState extends State<LekhakScreen> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  int _tick = -1;

  @override
  void initState() {
    super.initState();
    _tick = app.lekhakTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.lekhakTick != _tick) {
      _tick = app.lekhakTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.lekhakAll();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  void openDoc(Map<String, dynamic> d) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => LekhakDocPage(app: app, id: _s(d['id'])))).then((_) => _load());

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 5,
        initialIndex: widget.tab,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: Text('${app.aName} · Typist and translator'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Write'),
              Tab(text: 'Translation'),
              Tab(text: 'Improvement'),
              Tab(text: 'Paper'),
              Tab(text: 'Rules'),
            ]),
          ),
          body: Aurora(
            child: TabBarView(children: [
              _WriteTab(app: app, contacts: _list(_d?['contacts']), defLang: _s(_d?['settings']?['lang']), onDone: openDoc),
              _TranslateTab(app: app, onDone: openDoc),
              _FixTab(app: app, onDone: openDoc),
              _DocsTab(docs: _list(_d?['docs']), onOpen: openDoc, onRefresh: _load),
              _d == null ? const Center(child: CircularProgressIndicator()) : _RulesTab(app: app, d: _d!, onChanged: _load),
            ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- Likho: speak or type a letter
class _WriteTab extends StatefulWidget {
  const _WriteTab({required this.app, required this.contacts, required this.defLang, required this.onDone});
  final Santosh app;
  final List<Map<String, dynamic>> contacts;
  final String defLang;
  final void Function(Map<String, dynamic>) onDone;
  @override
  State<_WriteTab> createState() => _WriteTabState();
}

class _WriteTabState extends State<_WriteTab> {
  final _text = TextEditingController();
  final _to = TextEditingController();
  final _rec = VoiceRecorder();
  String _kind = '';
  String _lang = '';
  bool _busy = false;
  Timer? _t;
  String? _voiceId;
  Duration _voiceLen = Duration.zero;

  @override
  void dispose() {
    _t?.cancel();
    if (_rec.recording) _rec.stop();
    super.dispose();
  }

  Future<void> _mic() async {
    if (_rec.recording) {
      _t?.cancel();
      final wav = await _rec.stop();
      setState(() => _busy = true);
      try {
        final f = await widget.app.api!.chatFile(widget.app.conversationId ?? '', 'dictation.wav', wav);
        _voiceId = _s(f['file_id']);
        _voiceLen = _rec.length;
      } catch (e) {
        if (mounted) _snack(context, '$e');
      }
      if (mounted) setState(() => _busy = false);
      return;
    }
    final err = await _rec.start();
    if (err != null) {
      if (mounted) _snack(context, err);
      return;
    }
    _t = Timer.periodic(const Duration(milliseconds: 200), (_) => mounted ? setState(() {}) : null);
    setState(() {});
  }

  Future<void> _make() async {
    if (_text.text.trim().isEmpty && _voiceId == null) {
      _snack(context, 'Say or write what the letter should say');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.lekhakWrite({
        'dictation': _text.text.trim(),
        if (_text.text.trim().isEmpty && _voiceId != null) 'file_id': _voiceId,
        'kind': _kind,
        'lang': _lang.isEmpty ? widget.defLang : _lang,
        'to': _to.text.trim(),
        'conversation_id': widget.app.conversationId ?? '',
      });
      final d = Map<String, dynamic>.from(r['doc'] as Map);
      _text.clear();
      _voiceId = null;
      if (mounted) widget.onDone(d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final rec = _rec.recording;
    final secs = rec ? _rec.length.inSeconds : _voiceLen.inSeconds;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(children: [
          GestureDetector(
            onTap: _busy ? null : _mic,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 96 + (rec ? _rec.level * 60 : 0),
              height: 96 + (rec ? _rec.level * 60 : 0),
              decoration: BoxDecoration(shape: BoxShape.circle, color: rec ? C.bad : C.accent),
              child: Icon(rec ? Icons.stop_rounded : Icons.mic_rounded, size: 44, color: C.onAccent),
            ),
          ),
          const SizedBox(height: 10),
          Text(
              rec
                  ? 'Listening... ${secs}s (tap to stop)'
                  : _voiceId != null
                      ? 'Voice received (${secs}s) · tap "Make letter" below'
                      : 'Hold and say: to whom, about what, all the details',
              textAlign: TextAlign.center,
              style: const TextStyle(color: C.muted)),
          const SizedBox(height: 4),
          const Text('You can say "full stop", "comma", "new paragraph" to add punctuation', style: TextStyle(color: C.faint, fontSize: 11.5)),
        ]),
      ),
      const SizedBox(height: 12),
      TextField(controller: _text, minLines: 3, maxLines: 10, decoration: const InputDecoration(labelText: 'Or write here (just as you speak)')),
      const SizedBox(height: 10),
      TextField(controller: _to, decoration: const InputDecoration(labelText: 'To whom (Tehsildar Akot, MSEDCL, Bank manager...)')),
      if (widget.contacts.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Wrap(spacing: 6, runSpacing: 4, children: [
            for (final c in widget.contacts.take(10))
              ActionChip(label: Text(_s(c['name'])), onPressed: () => setState(() => _to.text = _s(c['name']))),
          ]),
        ),
      const SizedBox(height: 12),
      const Text('What kind of letter', style: TextStyle(color: C.muted, fontSize: 12.5)),
      Wrap(spacing: 6, runSpacing: 4, children: [
        ChoiceChip(label: const Text('Hoola understood'), selected: _kind.isEmpty, onSelected: (_) => setState(() => _kind = '')),
        for (final k in _kinds.entries) ChoiceChip(label: Text(k.value), selected: _kind == k.key, onSelected: (_) => setState(() => _kind = k.key)),
      ]),
      const SizedBox(height: 10),
      const Text('Language', style: TextStyle(color: C.muted, fontSize: 12.5)),
      Wrap(spacing: 6, children: [
        for (final l in ['hi', 'mr', 'en']) ChoiceChip(label: Text(_langs[l]!), selected: (_lang.isEmpty ? widget.defLang : _lang) == l, onSelected: (_) => setState(() => _lang = l)),
      ]),
      const SizedBox(height: 16),
      GradientButton(label: _busy ? 'Writing...' : 'Make letter', icon: Icons.edit_note_rounded, onTap: _busy ? null : _make),
      const SizedBox(height: 8),
      const Text('Whatever you did not say stays [blank]; Hoola adds nothing of its own. Signing only with your Yes.',
          style: TextStyle(color: C.faint, fontSize: 12)),
    ]);
  }
}

// ---------------------------------------------------------------- Anuvaad
class _TranslateTab extends StatefulWidget {
  const _TranslateTab({required this.app, required this.onDone});
  final Santosh app;
  final void Function(Map<String, dynamic>) onDone;
  @override
  State<_TranslateTab> createState() => _TranslateTabState();
}

class _TranslateTabState extends State<_TranslateTab> {
  final _text = TextEditingController();
  String _to = 'mr';
  bool _simple = false;
  bool _busy = false;
  String? _fileId;
  String _fileName = '';

  Future<void> _pick() async {
    final files = await pickAttachments(context, max: 1);
    if (files.isEmpty) return;
    setState(() => _busy = true);
    try {
      final f = await widget.app.api!.chatFile(widget.app.conversationId ?? '', files.first.name, files.first.bytes);
      setState(() {
        _fileId = _s(f['file_id']);
        _fileName = files.first.name;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _go() async {
    if (_text.text.trim().isEmpty && _fileId == null) {
      _snack(context, 'Write text or choose a file / photo');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.lekhakTranslate({
        'text': _text.text.trim(),
        if (_text.text.trim().isEmpty) 'file_id': _fileId,
        'to': _to,
        'register': _simple ? 'simple' : 'formal',
        'conversation_id': widget.app.conversationId ?? '',
      });
      if (mounted) widget.onDone(Map<String, dynamic>.from(r['doc'] as Map));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        TextField(controller: _text, minLines: 5, maxLines: 14, decoration: const InputDecoration(labelText: 'Enter text here')),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: GlassButton(label: _fileName.isEmpty ? 'Or choose a file / photo' : _fileName, icon: Icons.attach_file_rounded, onTap: _busy ? null : _pick)),
        ]),
        const SizedBox(height: 12),
        const Text('Which language', style: TextStyle(color: C.muted, fontSize: 12.5)),
        Wrap(spacing: 6, runSpacing: 4, children: [
          for (final l in _langs.entries) ChoiceChip(label: Text(l.value), selected: _to == l.key, onSelected: (_) => setState(() => _to = l.key)),
        ]),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: _simple,
          onChanged: (v) => setState(() => _simple = v),
          title: const Text('Everyday spoken language'),
          subtitle: const Text('Off = office / government language'),
        ),
        GradientButton(label: _busy ? 'Translating...' : 'Translate', icon: Icons.translate_rounded, onTap: _busy ? null : _go),
        const SizedBox(height: 8),
        const Text('Names, numbers, dates and amounts do not change (they stay locked); it is checked by translating back. '
            'Court / passport / embassy need a certified translator\'s stamp.', style: TextStyle(color: C.faint, fontSize: 12)),
      ]);
}

// ---------------------------------------------------------------- Sudhaar + Kruti Dev
class _FixTab extends StatefulWidget {
  const _FixTab({required this.app, required this.onDone});
  final Santosh app;
  final void Function(Map<String, dynamic>) onDone;
  @override
  State<_FixTab> createState() => _FixTabState();
}

class _FixTabState extends State<_FixTab> {
  final _text = TextEditingController();
  final _kd = TextEditingController();
  String _kdOut = '';
  bool _toKd = false;
  bool _busy = false;

  Future<void> _fix() async {
    if (_text.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.lekhakGrammar({'text': _text.text.trim(), 'conversation_id': widget.app.conversationId ?? ''});
      if (mounted) widget.onDone(Map<String, dynamic>.from(r['doc'] as Map));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _convert() async {
    try {
      final r = await widget.app.api!.lekhakKrutidev(_kd.text, toKrutidev: _toKd);
      setState(() => _kdOut = _s(r['text']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _typePhoto() async {
    final files = await pickAttachments(context, max: 1);
    if (files.isEmpty) return;
    setState(() => _busy = true);
    try {
      final f = await widget.app.api!.chatFile(widget.app.conversationId ?? '', files.first.name, files.first.bytes);
      final r = await widget.app.api!.lekhakType({'file_id': f['file_id'], 'conversation_id': widget.app.conversationId ?? ''});
      if (mounted) widget.onDone(Map<String, dynamic>.from(r['doc'] as Map));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Text('Fix grammar', style: display(16)),
        const SizedBox(height: 6),
        TextField(controller: _text, minLines: 4, maxLines: 12, decoration: const InputDecoration(labelText: 'Enter text')),
        const SizedBox(height: 8),
        GradientButton(label: _busy ? 'Checking...' : 'Fix mistakes', height: 48, icon: Icons.spellcheck_rounded, onTap: _busy ? null : _fix),
        const Padding(
          padding: EdgeInsets.only(top: 6),
          child: Text('Only mistakes; meaning, names and numbers do not change. Every change is shown.', style: TextStyle(color: C.faint, fontSize: 12)),
        ),
        const SizedBox(height: 18),
        Text('Type from photo / scan', style: display(16)),
        const SizedBox(height: 6),
        GlassButton(label: 'Choose a photo, scan or Kruti Dev file', icon: Icons.document_scanner_rounded, onTap: _busy ? null : _typePhoto),
        const SizedBox(height: 18),
        Text('Kruti Dev ↔ Unicode', style: display(16)),
        const SizedBox(height: 6),
        SegmentedButton<bool>(
          segments: const [ButtonSegment(value: false, label: Text('Kruti Dev → Unicode')), ButtonSegment(value: true, label: Text('Unicode → Kruti Dev'))],
          selected: {_toKd},
          onSelectionChanged: (s) => setState(() {
            _toKd = s.first;
            _kdOut = '';
          }),
        ),
        const SizedBox(height: 8),
        TextField(controller: _kd, minLines: 3, maxLines: 10, decoration: InputDecoration(labelText: _toKd ? 'हिंदी / मराठी text' : 'Kruti Dev text (for example: fgUnh)')),
        const SizedBox(height: 8),
        GlassButton(label: 'Change', icon: Icons.swap_horiz_rounded, onTap: _convert),
        if (_kdOut.isNotEmpty) ...[
          const SizedBox(height: 10),
          Glass(child: SelectableText(_kdOut, style: const TextStyle(color: C.chip, height: 1.5))),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              icon: const Icon(Icons.copy_rounded, size: 18),
              label: const Text('Copy'),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: _kdOut));
                _snack(context, 'Copied');
              },
            ),
          ),
          if (_toKd) const Text('Hindi shows correctly only in the Kruti Dev 010 font.', style: TextStyle(color: C.faint, fontSize: 12)),
        ],
      ]);
}

// ---------------------------------------------------------------- Kaagaz
class _DocsTab extends StatelessWidget {
  const _DocsTab({required this.docs, required this.onOpen, required this.onRefresh});
  final List<Map<String, dynamic>> docs;
  final void Function(Map<String, dynamic>) onOpen;
  final Future<void> Function() onRefresh;
  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: onRefresh,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
          if (docs.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Text('No papers yet.', style: TextStyle(color: C.muted))),
          for (final d in docs)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Press(
                onTap: () => onOpen(d),
                child: Glass(
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${d['number']} · ${d['title']}', style: display(14.5), maxLines: 1, overflow: TextOverflow.ellipsis),
                        const SizedBox(height: 3),
                        Text('${_kinds[d['kind']] ?? d['kind']} · ${_langs[d['lang']] ?? d['lang']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                      ]),
                    ),
                    Pill(_status[_s(d['status'])] ?? _s(d['status']), fg: _statusCol(_s(d['status']))),
                  ]),
                ),
              ),
            ),
        ]),
      );
}

// ---------------------------------------------------------------- Niyam
class _RulesTab extends StatelessWidget {
  const _RulesTab({required this.app, required this.d, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> d;
  final Future<void> Function() onChanged;

  Future<void> _save(BuildContext context, Map<String, dynamic> body) async {
    try {
      await app.api!.lekhakSettings(body);
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final st = Map<String, dynamic>.from(d['settings'] as Map);
    Widget row(String key, String label, String value, {int lines = 1, bool list = false}) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: Text(value.isEmpty ? '-' : value, maxLines: 3, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.edit_rounded, size: 18),
          onTap: () async {
            final v = await _askText(context, label, init: value, lines: lines);
            if (v == null) return;
            await _save(context, {key: list ? v.split('\n').map((x) => x.trim()).where((x) => x.isNotEmpty).toList() : v});
          },
        );
    final gl = _list(st['glossary']);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(children: [
          row('my_name', 'My name (below the letter)', _s(st['my_name'])),
          row('my_lines', 'Address / designation (one per line)', _strs(st['my_lines']).join('\n'), lines: 4, list: true),
          row('my_phone', 'Mobile', _s(st['my_phone'])),
          row('place', 'Place', _s(st['place'])),
          row('letterhead', 'Office letterhead (first line is the name)', _s(st['letterhead']), lines: 3),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Female / Male (grammar form)'),
            trailing: SegmentedButton<String>(
              segments: const [ButtonSegment(value: 'f', label: Text('Female')), ButtonSegment(value: 'm', label: Text('Male'))],
              selected: {_s(st['gender']).isEmpty ? 'm' : _s(st['gender'])},
              onSelectionChanged: (s) => _save(context, {'gender': s.first}),
            ),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Letter language'),
            trailing: DropdownButton<String>(
              value: const ['hi', 'mr', 'en'].contains(_s(st['lang'])) ? _s(st['lang']) : 'hi',
              items: [for (final l in ['hi', 'mr', 'en']) DropdownMenuItem(value: l, child: Text(_langs[l]!))],
              onChanged: (v) => v == null ? null : _save(context, {'lang': v}),
            ),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Signature photo', style: display(15))),
            if (st['has_sign'] == true) const Pill('Saved', fg: C.ok),
          ]),
          const SizedBox(height: 4),
          const Text('Used only when you choose "add photo" on the sign card. This is a photo, not a digital signature.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: GlassButton(
                label: st['has_sign'] == true ? 'Change' : 'Choose photo',
                icon: Icons.draw_rounded,
                onTap: () async {
                  final files = await pickAttachmentsOfType(context, FileType.image);
                  if (files.isEmpty) return;
                  try {
                    final f = await app.api!.chatFile(app.conversationId ?? '', 'signature.png', files.first.bytes);
                    await _save(context, {'sign_file': f['file_id']});
                  } catch (e) {
                    if (context.mounted) _snack(context, '$e');
                  }
                },
              ),
            ),
            if (st['has_sign'] == true) ...[
              const SizedBox(width: 8),
              GlassButton(label: 'Remove', onTap: () => _save(context, {'sign_file': ''})),
            ],
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          row('keep', 'Never translate (one word per line)', _strs(st['keep']).join('\n'), lines: 5, list: true),
          row('rules', 'My rules (one per line)', _strs(st['rules']).join('\n'), lines: 5, list: true),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Glossary (${gl.length})'),
            subtitle: Text(gl.take(4).map((e) => '${e['src']} → ${e['dst']}').join(' · ')),
            trailing: const Icon(Icons.add_rounded),
            onTap: () async {
              final v = await _askText(context, 'Word = translation', label: 'for example: ग्राहक क्रमांक = consumer number');
              if (v == null || !v.contains('=')) return;
              final p = v.split('=');
              await _save(context, {'glossary': [...gl, {'src': p[0].trim(), 'dst': p.sublist(1).join('=').trim()}]});
            },
          ),
          if (_strs(st['style']).isNotEmpty) ...[
            const SizedBox(height: 6),
            const Text('Learned from your changes:', style: TextStyle(color: C.muted, fontSize: 12.5)),
            for (final x in _strs(st['style']).reversed.take(6)) Text('• $x', style: const TextStyle(color: C.faint, fontSize: 12)),
          ],
        ]),
      ),
      const SizedBox(height: 12),
      Text('Addresses (${_list(d['contacts']).length})', style: display(15)),
      for (final c in _list(d['contacts']))
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.account_balance_rounded),
          title: Text(_s(c['name'])),
          subtitle: Text(_strs(c['lines']).join(', ')),
        ),
      TextButton.icon(
        icon: const Icon(Icons.add_rounded),
        label: const Text('New address'),
        onPressed: () async {
          final n = await _askText(context, 'To whom (short name)', label: 'Tehsildar Akot');
          if (n == null || n.isEmpty || !context.mounted) return;
          final lines = await _askText(context, 'Address as it will go on the letter', label: 'one per line', lines: 4);
          if (lines == null) return;
          try {
            await app.api!.lekhakContact({'name': n, 'lines': lines.split('\n').where((x) => x.trim().isNotEmpty).toList()});
          } catch (e) {
            if (context.mounted) _snack(context, '$e');
          }
          await onChanged();
        },
      ),
    ]);
  }
}

// ---------------------------------------------------------------- one document
class LekhakDocPage extends StatefulWidget {
  const LekhakDocPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<LekhakDocPage> createState() => _LekhakDocPageState();
}

class _LekhakDocPageState extends State<LekhakDocPage> {
  Map<String, dynamic>? _d;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.lekhakDoc(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (r['doc'] is Map && mounted) setState(() => _d = Map<String, dynamic>.from(r['doc'] as Map));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final conv = widget.app.conversationId ?? '';
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(d == null ? '' : '${d['number']} · ${d['title']}')),
      body: Aurora(
        child: d == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
                Wrap(spacing: 8, children: [
                  Pill(_status[_s(d['status'])] ?? _s(d['status']), fg: _statusCol(_s(d['status']))),
                  Pill(_langs[d['lang']] ?? _s(d['lang'])),
                  Pill('${d['versions']} version'),
                ]),
                const SizedBox(height: 10),
                LekhakChecks(checks: Map<String, dynamic>.from((d['checks'] as Map?) ?? const {})),
                Container(
                  margin: const EdgeInsets.only(top: 6),
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(color: const Color(0xFFFDFBF6), borderRadius: BorderRadius.circular(12)),
                  child: SelectableText(_s(d['text']), style: const TextStyle(color: Color(0xFF1A1A1A), fontSize: 15, height: 1.6)),
                ),
                const SizedBox(height: 14),
                if (d['status'] != 'signed')
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    GlassButton(
                      label: 'Change (say it)',
                      icon: Icons.record_voice_over_rounded,
                      height: 42,
                      onTap: _busy
                          ? null
                          : () async {
                              final v = await _askText(context, 'What to change?', label: 'for example: shorten the subject, do it in Marathi');
                              if (v != null && v.isNotEmpty) await _run(() => widget.app.api!.lekhakRevise(widget.id, v, conversationId: conv));
                            },
                    ),
                    GlassButton(
                      label: 'Write it yourself',
                      icon: Icons.edit_rounded,
                      height: 42,
                      onTap: _busy
                          ? null
                          : () async {
                              final plain = ['translation', 'typing', 'grammar', 'convert'].contains(d['kind']);
                              final parts = Map<String, dynamic>.from((d['parts'] as Map?) ?? const {});
                              final init = plain ? _s(parts['text']) : _strs(parts['body']).join('\n\n');
                              final v = await _askText(context, plain ? 'Text' : 'Main body of the letter', init: init, lines: 10);
                              if (v == null) return;
                              await _run(() => widget.app.api!.lekhakEdit(widget.id,
                                  plain ? {'text': v} : {'parts': {'body': v.split(RegExp(r'\n\s*\n')).where((x) => x.trim().isNotEmpty).toList()}}));
                            },
                    ),
                    if (!['translation', 'typing', 'grammar', 'convert'].contains(d['kind']))
                      GlassButton(
                        label: 'For signing',
                        icon: Icons.draw_rounded,
                        height: 42,
                        onTap: _busy ? null : () => _run(() => widget.app.api!.lekhakSignRequest(widget.id, conversationId: conv)),
                      ),
                  ]),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GradientButton(label: 'Word + PDF', icon: Icons.picture_as_pdf_rounded, height: 44, onTap: _busy ? null : () => _run(() => widget.app.api!.lekhakFiles(widget.id, conversationId: conv))),
                  GlassButton(
                    label: 'Copy',
                    icon: Icons.copy_rounded,
                    height: 44,
                    onTap: () {
                      Clipboard.setData(ClipboardData(text: _s(d['text'])));
                      _snack(context, 'Copied');
                    },
                  ),
                  GlassButton(
                    label: 'WhatsApp draft',
                    icon: Icons.send_rounded,
                    height: 44,
                    onTap: () async {
                      final ph = await _askText(context, 'On which number?', label: '10 digits');
                      if (ph == null) return;
                      try {
                        final r = await widget.app.api!.lekhakShare(widget.id, phone: ph);
                        if (_s(r['wa_link']).isNotEmpty) await Native.openExternal(url: _s(r['wa_link']));
                      } catch (e) {
                        if (context.mounted) _snack(context, '$e');
                      }
                    },
                  ),
                  if (d['status'] == 'signed')
                    GlassButton(label: 'New copy', icon: Icons.copy_all_rounded, height: 44, onTap: () => _run(() => widget.app.api!.lekhakCopy(widget.id))),
                ]),
                for (final f in ((d['files'] as Map?) ?? const {}).entries)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(f.key == 'pdf' ? Icons.picture_as_pdf_rounded : Icons.description_rounded),
                    title: Text(_s((f.value as Map)['name'])),
                    trailing: const Icon(Icons.open_in_new_rounded),
                    onTap: () => Native.openExternal(url: widget.app.api!.absolute(_s((f.value as Map)['url']))),
                  ),
                if (_s(d['source']).isNotEmpty) ...[
                  const SizedBox(height: 12),
                  ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: const Text('What you said', style: TextStyle(color: C.muted)),
                    children: [SelectableText(_s(d['source']), style: const TextStyle(color: C.faint))],
                  ),
                ],
              ]),
      ),
    );
  }
}

/// What Hoola checked: blanks, facts not found, notes, grammar edits, back-translation differences.
class LekhakChecks extends StatelessWidget {
  const LekhakChecks({super.key, required this.checks});
  final Map<String, dynamic> checks;
  @override
  Widget build(BuildContext context) {
    final blanks = _strs(checks['blanks']);
    final missing = _strs(checks['missing_facts']);
    final lost = _strs(checks['lost']);
    final notes = _strs(checks['notes']);
    final edits = _list(checks['edits']);
    final refused = _list(checks['refused']);
    final back = (checks['back_check'] as Map?) ?? const {};
    final diffs = _strs(back['differences']);
    if (blanks.isEmpty && missing.isEmpty && lost.isEmpty && notes.isEmpty && edits.isEmpty && refused.isEmpty && diffs.isEmpty && checks['label'] == null) {
      return const SizedBox.shrink();
    }
    Widget line(IconData i, Color c, String t) => Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(i, size: 16, color: c),
            const SizedBox(width: 6),
            Expanded(child: Text(t, style: TextStyle(color: c, fontSize: 12.5))),
          ]),
        );
    return Glass(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (checks['label'] != null) line(Icons.info_outline_rounded, C.muted, _s(checks['label'])),
        if (blanks.isNotEmpty) line(Icons.edit_note_rounded, C.accent, 'Still to fill: ${blanks.join(', ')}'),
        if (missing.isNotEmpty) line(Icons.report_rounded, C.bad, 'Not in the letter from what you said: ${missing.join(', ')}'),
        if (lost.isNotEmpty) line(Icons.report_rounded, C.bad, 'Left out in the translation: ${lost.join(', ')}'),
        if (diffs.isNotEmpty) line(Icons.compare_arrows_rounded, C.accent, 'Difference when translated back: ${diffs.join('; ')}'),
        if (back.isNotEmpty && diffs.isEmpty) line(Icons.verified_rounded, C.ok, 'Translated back: the meaning is the same'),
        for (final e in edits) line(Icons.check_rounded, C.ok, '"${e['from']}" → "${e['to']}"  (${e['why']})'),
        for (final e in refused) line(Icons.block_rounded, C.faint, 'Blocked:"${e['from']}" → "${e['to']}" (${e['why']})'),
        for (final n in notes) line(Icons.lightbulb_outline_rounded, C.accent2, n),
      ]),
    );
  }
}

// ---------------------------------------------------------------- chat cards
class LekhakDocCard extends StatelessWidget {
  const LekhakDocCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final text = _s(v['text']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.edit_document, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['number']} · ${v['title']}', style: display(15), maxLines: 2, overflow: TextOverflow.ellipsis)),
          Pill(_status[_s(v['status'])] ?? _s(v['status']), fg: _statusCol(_s(v['status']))),
        ]),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xFFFDFBF6), borderRadius: BorderRadius.circular(10)),
          child: Text(text.length > 700 ? '${text.substring(0, 700)}…' : text,
              style: const TextStyle(color: Color(0xFF1A1A1A), fontSize: 13, height: 1.5)),
        ),
        const SizedBox(height: 6),
        LekhakChecks(checks: Map<String, dynamic>.from((v['checks'] as Map?) ?? const {})),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LekhakDocPage(app: app, id: _s(v['id'])))),
            child: const Text('Open / change / file'),
          ),
        ),
      ]),
    );
  }
}

/// The sign card: the exact final text, and only her tap signs (paper print, or her saved signature picture).
class LekhakSignCard extends StatefulWidget {
  const LekhakSignCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<LekhakSignCard> createState() => _LekhakSignCardState();
}

class _LekhakSignCardState extends State<LekhakSignCard> {
  bool _busy = false;
  String _mode = 'paper';

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.lekhakSign(_s(widget.v['id']), yes,
          mode: _mode, hash: _s(widget.v['hash']), conversationId: widget.app.conversationId ?? '');
      widget.v.addAll(Map<String, dynamic>.from((r['doc'] as Map?) ?? const {}));
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final st = _s(v['status']);
    final waiting = st == 'waiting_sign';
    final blanks = _strs(v['blanks']);
    return Glass(
      border: waiting ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.draw_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Do you want to sign? ${v['number']}', style: display(15))),
          if (!waiting) Pill(_status[st] ?? st, fg: _statusCol(st)),
        ]),
        const SizedBox(height: 8),
        Container(
          constraints: const BoxConstraints(maxHeight: 320),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xFFFDFBF6), borderRadius: BorderRadius.circular(10)),
          child: SingleChildScrollView(child: Text(_s(v['text']), style: const TextStyle(color: Color(0xFF1A1A1A), fontSize: 13, height: 1.5))),
        ),
        if (blanks.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 6), child: Text('Fill in first: ${blanks.join(', ')}', style: const TextStyle(color: C.bad, fontSize: 12.5))),
        if (waiting) ...[
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: [
              const ButtonSegment(value: 'paper', icon: Icon(Icons.print_rounded), label: Text('Print, I will sign')),
              ButtonSegment(value: 'image', icon: const Icon(Icons.draw_rounded), label: const Text('Add signature photo'), enabled: v['has_sign'] == true),
            ],
            selected: {_mode},
            onSelectionChanged: (x) => setState(() => _mode = x.first),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(v['has_sign'] == true ? 'The signature photo is only a photo, not a digital signature.' : 'Add a photo in Rules for the signature photo.',
                style: const TextStyle(color: C.faint, fontSize: 11.5)),
          ),
          const Text('For an official e-sign, use the Aadhaar eSign site.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GlassButton(label: 'Decline', onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Yes, final', height: 48, onTap: _busy || blanks.isNotEmpty ? null : () => _decide(true))),
          ]),
        ],
      ]),
    );
  }
}
