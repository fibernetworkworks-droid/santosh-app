import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

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
    super.dispose();
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
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola\'s memory')),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
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
