import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.248 "Hoola ki yaad" (Claude's memory settings): the page Hoola keeps about her ("Mere baare mein") which she
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
        _loaded = true;
      });
    } catch (e) {
      if (mounted) setState(() {
        _note = 'Abhi load nahi ho saka: $e';
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
      if (mounted) setState(() => _note = 'Nahi ho saka: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _switch({bool? auto, bool? recall}) async {
    try {
      final sw = await widget.app.api!.memorySwitches(auto: auto, recall: recall);
      if (mounted) setState(() {
        _auto = sw['auto'] != false;
        _recall = sw['recall'] != false;
      });
    } catch (e) {
      if (mounted) setState(() => _note = 'Nahi badla: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final api = widget.app.api!;
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola ki yaad')),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Mere baare mein', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                  const SizedBox(height: 4),
                  Text(
                      _by == 'her'
                          ? 'Aapne ise badla hai. Hoola aapki baat ko sach maanta hai.'
                          : 'Hoola ise roz ek baar aapki baaton se likhta hai. Har chat aur call ise padhti hai. '
                              'Galat ho to yahin sudhaar dijiye.',
                      style: const TextStyle(color: C.faint, fontSize: 12)),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _text,
                    minLines: 6,
                    maxLines: 16,
                    maxLength: 1600,
                    style: const TextStyle(fontSize: 13.5, height: 1.4),
                    decoration: const InputDecoration(
                        hintText: 'Abhi khaali hai. Jaise: KAAM - bakery, Pune. PASAND - reports Marathi mein.',
                        border: OutlineInputBorder()),
                  ),
                  if (_note.isNotEmpty) Text(_note, style: const TextStyle(color: C.teal, fontSize: 12)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 8, runSpacing: 4, children: [
                    FilledButton.icon(
                      onPressed: _busy ? null : () => _run(() => api.aboutMeSave(_text.text), 'Save ho gaya.'),
                      icon: const Icon(Icons.check_rounded, size: 18),
                      label: const Text('Save'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _busy ? null : () => _run(api.aboutMeRebuild, 'Naya likh diya.'),
                      icon: const Icon(Icons.auto_awesome_rounded, size: 18),
                      label: Text(_busy ? 'Ho raha hai...' : 'Hoola se naya likhwao'),
                    ),
                    TextButton(
                      onPressed: _busy ? null : () => _run(() => api.aboutMeSave(''), 'Saaf kar diya.'),
                      child: const Text('Saaf karo'),
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
                    title: const Text('Khud yaad rakhna', style: TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: const Text('Hoola baaton se pakki baatein khud yaad rakhe aur yeh page likhe.',
                        style: TextStyle(fontSize: 12)),
                    onChanged: (v) => _switch(auto: v),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _recall,
                    title: const Text('Purani chats se yaad', style: TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: const Text('Hoola pichhli chats dhoondh sake aur yeh page har chat mein padhe.',
                        style: TextStyle(fontSize: 12)),
                    onChanged: (v) => _switch(recall: v),
                  ),
                ]),
              ),
              const SizedBox(height: 12),
              const Text(
                  'Kisi baat ko bilkul yaad na rakhwana ho? "Aapki chats" mein 🕶 Incognito chat kholiye: wahan ki baatein '
                  'kahin save nahi hoti. Session (folder) ki baatein usi Session tak rehti hain.',
                  style: TextStyle(color: C.faint, fontSize: 12)),
            ]),
    );
  }
}
