/// Profile > Pehchaan Locker (v0.75): Aadhaar, PAN, Voter ID and other ID numbers, kept encrypted on the server.
/// Hoola itself only ever sees a masked reference ({id:...}); the computer operator types the real number into a
/// form box (government sites directly, other sites after her tap). OTP / PIN / CVV / card numbers never go here.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';

class IdLockerScreen extends StatefulWidget {
  const IdLockerScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<IdLockerScreen> createState() => _IdLockerScreenState();
}

class _IdLockerScreenState extends State<IdLockerScreen> {
  List<Map<String, dynamic>>? _rows;
  Map<String, String> _kinds = const {};
  Map<String, String> _people = const {};
  final Map<String, String> _shown = {};
  String? _err;
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await _api.idList();
      if (!mounted) return;
      setState(() {
        _rows = List<Map<String, dynamic>>.from(((r['ids'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        _kinds = Map<String, String>.from(((r['kinds'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', '$v')));
        _people = Map<String, String>.from(((r['people'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', '$v')));
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  void _say(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _add() async {
    String kind = 'aadhaar', person = 'self';
    final num = TextEditingController(), note = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setD) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: const Text('Naya number'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              DropdownButtonFormField<String>(
                value: person,
                decoration: const InputDecoration(labelText: 'Kiska'),
                items: [for (final e in (_people.isEmpty ? {'self': 'Aap'} : _people).entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
                onChanged: (v) => setD(() => person = v ?? 'self'),
              ),
              DropdownButtonFormField<String>(
                value: kind,
                decoration: const InputDecoration(labelText: 'Kaunsa'),
                items: [for (final e in (_kinds.isEmpty ? {'aadhaar': 'Aadhaar'} : _kinds).entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
                onChanged: (v) => setD(() => kind = v ?? 'aadhaar'),
              ),
              TextField(
                controller: num,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(labelText: 'Number'),
              ),
              TextField(controller: note, decoration: const InputDecoration(labelText: 'Note (zaroori nahi)')),
              const SizedBox(height: 8),
              const Text('OTP, PIN, CVV, card number yahan mat daliye. Woh aap khud bharti hain.',
                  style: TextStyle(color: C.warn, fontSize: 11.5)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true || num.text.trim().isEmpty) return;
    try {
      await _api.idSave(kind: kind, number: num.text.trim(), person: person, note: note.text.trim());
      await _load();
      _say('Locker mein rakh diya');
    } catch (e) {
      _say('$e');
    }
  }

  Future<void> _reveal(Map<String, dynamic> r) async {
    final id = r['id'] as String;
    if (_shown.containsKey(id)) {
      setState(() => _shown.remove(id));
      return;
    }
    try {
      final v = await _api.idReveal(id);
      if (!mounted) return;
      setState(() => _shown[id] = '${v['value']}');
      Future.delayed(const Duration(seconds: 20), () {
        if (mounted) setState(() => _shown.remove(id));
      });
    } catch (e) {
      _say('$e');
    }
  }

  Future<void> _delete(Map<String, dynamic> r) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('${r['person_label']} ka ${r['kind_label']} hata dein?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hatao', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _api.idDelete(r['id'] as String);
      _shown.remove(r['id']);
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;
    final name = widget.app.aName;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Pehchaan Locker')),
      floatingActionButton: FloatingActionButton.extended(
          onPressed: _add, icon: const Icon(Icons.add_rounded), label: const Text('Number jodiye')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 96), children: [
            Glass(
              child: Text(
                  'Aadhaar, PAN, Voter ID jaise number yahan taala band (encrypted) rehte hain. $name chat mein sirf aakhri 4 ank dekhta hai. '
                  'Form bharte waqt asli number seedha box mein bharta hai: sarkari site par turant, baaki site par aapke tap ke baad. '
                  'Chat mein number bolengi to $name khud yahan rakh dega.',
                  style: const TextStyle(color: C.chip, height: 1.35, fontSize: 13)),
            ),
            const SizedBox(height: 12),
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (rows == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (rows != null && rows.isEmpty)
              const Padding(
                padding: EdgeInsets.all(30),
                child: Center(
                    child: Text('Locker khaali hai. "Number jodiye" dabaiye, ya chat mein boliye: "mera aadhaar 1234 5678 9012 hai".',
                        textAlign: TextAlign.center, style: TextStyle(color: C.muted))),
              ),
            for (final r in rows ?? const <Map<String, dynamic>>[]) _card(r),
          ]),
        ),
      ),
    );
  }

  Widget _card(Map<String, dynamic> r) {
    final id = r['id'] as String;
    final shown = _shown[id];
    final note = '${r['note'] ?? ''}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Row(children: [
          const Icon(Icons.badge_rounded, color: C.accent, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${r['person_label']} · ${r['kind_label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
              const SizedBox(height: 3),
              SelectableText(shown ?? '${r['masked']}',
                  style: TextStyle(fontSize: 15, letterSpacing: 1.1, fontWeight: FontWeight.w600, color: shown != null ? C.ok : null)),
              if (note.isNotEmpty) Text(note, style: const TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
          if (shown != null)
            IconButton(
                tooltip: 'Copy',
                icon: const Icon(Icons.copy_rounded, size: 19),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: shown));
                  _say('Copy ho gaya');
                }),
          IconButton(
              tooltip: shown == null ? 'Dikhao' : 'Chhupao',
              icon: Icon(shown == null ? Icons.visibility_rounded : Icons.visibility_off_rounded, size: 20),
              onPressed: () => _reveal(r)),
          IconButton(tooltip: 'Hatao', icon: const Icon(Icons.delete_outline_rounded, size: 19, color: C.muted), onPressed: () => _delete(r)),
        ]),
      ),
    );
  }
}
