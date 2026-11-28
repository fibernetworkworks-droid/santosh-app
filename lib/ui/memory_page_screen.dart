import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

/// v0.250 "Hoola ki yaad" (Claude's memory settings): the page Hoola keeps about her ("Mere baare mein") which she
/// can read, correct or clear, a "naya likho" tap, and her two switches - "Khud yaad rakhna" (Hoola picks up facts and
/// writes this page by itself) and "Purani chats se yaad" (search, recent chats and this page are used).
class MemoryPageScreen extends StatefulWidget {
  const MemoryPageScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<MemoryPageScreen> createState() => _MemoryPageScreenState();
}

class _MemoryPageScreenState extends State<MemoryPageScreen> {
  final _text = TextEditingController();
  final _paste = TextEditingController();   // v0.999 bring from another assistant
  List<PlatformFile> _files = [];
  Map<String, dynamic>? _preview;
  List<Map<String, dynamic>> _imports = [];
  String _impNote = '';
  bool _impBusy = false;
  bool _auto = true;
  bool _recall = true;
  bool _sensitive = false;
  bool _loaded = false;
  bool _busy = false;
  String _by = '';
  String _note = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _text.dispose();
    _paste.dispose();
    super.dispose();
  }

  Future<void> _loadImports() async {
    try {
      final l = await widget.app.api!.memoryImports();
      if (mounted) setState(() => _imports = l);
    } catch (_) {}
  }

  Future<void> _pickFiles() async {
    final r = await FilePicker.platform.pickFiles(
        allowMultiple: true, withData: true, type: FileType.custom, allowedExtensions: ['zip', 'md', 'markdown', 'txt', 'json']);
    if (r == null || !mounted) return;
    setState(() {
      _files = r.files.where((f) => f.bytes != null).toList();
      _preview = null;
    });
  }

  Future<void> _previewImport() async {
    if (_files.isEmpty && _paste.text.trim().isEmpty) {
      setState(() => _impNote = 'Choose your old assistant\'s files or paste your memories first.');
      return;
    }
    setState(() {
      _impBusy = true;
      _impNote = 'Reading your files...';
    });
    try {
      final p = await widget.app.api!
          .memoryImportPreview([for (final f in _files) (f.name, f.bytes!.toList())], text: _paste.text.trim());
      if (mounted) setState(() {
        _preview = p;
        _impNote = '';
      });
    } catch (e) {
      if (mounted) setState(() => _impNote = '$e');
    }
    if (mounted) setState(() => _impBusy = false);
  }

  Future<void> _applyImport() async {
    final p = _preview;
    if (p == null) return;
    setState(() => _impBusy = true);
    try {
      final r = await widget.app.api!.memoryImportApply('${p['token']}');
      if (mounted) setState(() {
        _preview = null;
        _files = [];
        _paste.clear();
        _impNote = '${r['said'] ?? 'Brought in.'}';
      });
      await _loadImports();
    } catch (e) {
      if (mounted) setState(() => _impNote = '$e');
    }
    if (mounted) setState(() => _impBusy = false);
  }

  Future<void> _undoImport(String id) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Take this import back out?'),
        content: const Text('The facts, notes, past chats and skills it brought in will leave Hoola\'s memory.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, take out')),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await widget.app.api!.memoryImportUndo(id);
      if (mounted) setState(() => _impNote = 'Taken back out.');
      await _loadImports();
    } catch (e) {
      if (mounted) setState(() => _impNote = '$e');
    }
  }

  Widget _importCard() {
    final p = _preview;
    final c = (p?['counts'] as Map?) ?? const {};
    final facts = [for (final f in (p?['facts'] as List?) ?? const []) '$f'];
    final skills = [for (final s in (p?['skills'] as List?) ?? const []) '${(s as Map)['name']}'];
    final skipped = [for (final x in (p?['skipped'] as List?) ?? const []) '${(x as Map)['n']} left out: ${x['what']}'];
    final name = '${((p?['persona'] as Map?) ?? const {})['name'] ?? ''}';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Bring from another assistant', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        const SizedBox(height: 4),
        const Text(
            'Bring your memories, skills and past chats from OpenClaw, Hermes, ChatGPT or Claude. You see everything first; '
            'nothing comes in until you tap Bring in. Keys and settings files are never read.',
            style: TextStyle(color: C.faint, fontSize: 12)),
        const SizedBox(height: 6),
        const Text(
            'OpenClaw: zip your workspace folder. Hermes: zip the memories and skills folders in .hermes. ChatGPT or Claude: '
            'the data export zip from their settings. ChatGPT\'s saved memories are not in its export: copy them from '
            'Settings > Personalization > Manage memories and paste them below.',
            style: TextStyle(color: C.faint, fontSize: 12)),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: _impBusy ? null : _pickFiles,
          icon: const Icon(Icons.upload_file_rounded, size: 18),
          label: Text(_files.isEmpty ? 'Choose files' : '${_files.length} file${_files.length == 1 ? '' : 's'} chosen'),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _paste,
          minLines: 2,
          maxLines: 6,
          style: const TextStyle(fontSize: 13.5),
          decoration: const InputDecoration(hintText: 'Or paste memories here, one per line', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 8),
        if (p == null)
          FilledButton(onPressed: _impBusy ? null : _previewImport, child: Text(_impBusy ? 'Reading...' : 'Preview')),
        if (p != null) ...[
          Text('From ${p['label']}: ${c['facts'] ?? 0} facts, ${c['notes'] ?? 0} notes and past chats, ${c['skills'] ?? 0} skills',
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
          for (final f in facts.take(8)) Text('• $f', style: const TextStyle(fontSize: 12.5)),
          if (facts.length > 8) Text('and ${facts.length - 8} more', style: const TextStyle(color: C.faint, fontSize: 12)),
          if (skills.isNotEmpty) Text('Skills: ${skills.join(', ')}', style: const TextStyle(color: C.faint, fontSize: 12)),
          if (name.isNotEmpty)
            Text('Your old assistant was called $name. Its personality and rules stay behind: Hoola keeps its own.',
                style: const TextStyle(color: C.faint, fontSize: 12)),
          for (final x in skipped) Text(x, style: const TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, children: [
            FilledButton(onPressed: _impBusy ? null : _applyImport, child: const Text('Bring in')),
            TextButton(onPressed: _impBusy ? null : () => setState(() => _preview = null), child: const Text('Cancel')),
          ]),
        ],
        if (_impNote.isNotEmpty) Padding(
            padding: const EdgeInsets.only(top: 6), child: Text(_impNote, style: const TextStyle(color: C.teal, fontSize: 12))),
        if (_imports.isNotEmpty) ...[
          const SizedBox(height: 10),
          const Text('Brought in before', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
          for (final r in _imports)
            Row(children: [
              Expanded(
                  child: Text(
                      '${r['label']}: ${(r['counts'] as Map?)?['facts'] ?? 0} facts, ${(r['counts'] as Map?)?['notes'] ?? 0} notes, '
                      '${(r['counts'] as Map?)?['skills'] ?? 0} skills',
                      style: const TextStyle(fontSize: 12.5))),
              r['undone'] == true
                  ? const Text('Taken out', style: TextStyle(color: C.faint, fontSize: 12))
                  : TextButton(onPressed: () => _undoImport('${r['id']}'), child: const Text('Undo')),
            ]),
        ],
      ]),
    );
  }

  void _take(Map<String, dynamic> about) {
    _text.text = '${about['text'] ?? ''}';
    _by = '${about['by'] ?? ''}';
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.aboutMe();
      final sw = Map<String, dynamic>.from((r['switches'] as Map?) ?? const {});
      if (!mounted) return;
      setState(() {
        _take(Map<String, dynamic>.from((r['about'] as Map?) ?? const {}));
        _auto = sw['auto'] != false;
        _recall = sw['recall'] != false;
        _sensitive = sw['sensitive'] == true;
        _loaded = true;
      });
      _loadImports();
    } catch (e) {
      if (mounted) setState(() {
        _note = 'Could not load right now: $e';
        _loaded = true;
      });
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() call, String ok) async {
    setState(() => _busy = true);
    try {
      final about = await call();
      if (!mounted) return;
      setState(() {
        _take(about);
        _note = ok;
      });
    } catch (e) {
      if (mounted) setState(() => _note = 'Could not do it: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _switch({bool? auto, bool? recall, bool? sensitive}) async {
    try {
      final sw = await widget.app.api!.memorySwitches(auto: auto, recall: recall, sensitive: sensitive);
      if (mounted) setState(() {
        _auto = sw['auto'] != false;
        _recall = sw['recall'] != false;
        _sensitive = sw['sensitive'] == true;
      });
    } catch (e) {
      if (mounted) setState(() => _note = 'Not changed: $e');
    }
  }

  /// v0.609 Claude's "reset memory": asks once, then every store forgets her (her chats are not deleted).
  Future<void> _resetAll() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Delete all memory?'),
        content: const Text('Everything Hoola remembers about you - facts, this page, memory of old chats, notes'
            'about work - will be deleted. Your chats will not be deleted. This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, delete')),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await widget.app.api!.memoryReset();
      if (!mounted) return;
      setState(() {
        _text.text = '';
        _note = 'All memory deleted. Your chats are as they were.';
      });
    } catch (e) {
      if (mounted) setState(() => _note = 'Could not do it: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final api = widget.app.api!;
    return DeskPage(
      title: 'Hoola\'s memory',
      loading: !_loaded,
      onRefresh: _load,
      body: () => ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('About me', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                  const SizedBox(height: 4),
                  Text(
                      _by == 'her'
                          ? 'You have edited this. Hoola treats what you wrote as true.'
                          : 'Hoola writes this once a day from your conversations. Every chat and call reads it.'
                              'If something is wrong, correct it right here.',
                      style: const TextStyle(color: C.faint, fontSize: 12)),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _text,
                    minLines: 6,
                    maxLines: 16,
                    maxLength: 1600,
                    style: const TextStyle(fontSize: 13.5, height: 1.4),
                    decoration: const InputDecoration(
                        hintText: 'It is empty for now. For example: WORK - bakery, Pune. LIKES - reports in Marathi.',
                        border: OutlineInputBorder()),
                  ),
                  if (_note.isNotEmpty) Text(_note, style: const TextStyle(color: C.teal, fontSize: 12)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 8, runSpacing: 4, children: [
                    FilledButton.icon(
                      onPressed: _busy ? null : () => _run(() => api.aboutMeSave(_text.text), 'Saved.'),
                      icon: const Icon(Icons.check_rounded, size: 18),
                      label: const Text('Save'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _busy ? null : () => _run(api.aboutMeRebuild, 'Wrote a new one.'),
                      icon: const Icon(Icons.auto_awesome_rounded, size: 18),
                      label: Text(_busy ? 'Working...' : 'Have Hoola write a new one'),
                    ),
                    TextButton(
                      onPressed: _busy ? null : () => _run(() => api.aboutMeSave(''), 'Cleared.'),
                      child: const Text('Clear'),
                    ),
                  ]),
                ]),
              ),
              const SizedBox(height: 16),
              Glass(
                child: Column(children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _auto,
                    title: const Text('Remember on its own', style: TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: const Text('Let Hoola remember solid facts from conversations by itself and write this page.',
                        style: TextStyle(fontSize: 12)),
                    onChanged: (v) => _switch(auto: v),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _recall,
                    title: const Text('Memory from past chats', style: TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: const Text('Let Hoola search past chats and read this page in every chat.',
                        style: TextStyle(fontSize: 12)),
                    onChanged: (v) => _switch(recall: v),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _sensitive,
                    title: const Text('Sensitive topics too', style: TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: const Text(
                        'Let it remember firm facts such as health, religion, politics. Never money, ID numbers or passwords.',
                        style: TextStyle(fontSize: 12)),
                    onChanged: (v) => _switch(sensitive: v),
                  ),
                ]),
              ),
              const SizedBox(height: 16),
              _importCard(),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: _busy ? null : _resetAll,
                icon: const Icon(Icons.delete_sweep_rounded, size: 18),
                label: const Text('Delete all memory'),
              ),
              const SizedBox(height: 12),
              const Text(
                  'Want something not remembered at all? Open a 🕶 Incognito chat in "Your chats": nothing there'
                  'is saved anywhere. What is said in a Session (folder) stays within that Session.',
                  style: TextStyle(color: C.faint, fontSize: 12)),
            ]),
    );
  }
}
