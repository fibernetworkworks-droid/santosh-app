import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

/// v0.47 Public APIs: 2,100+ free web APIs Hoola can use (github.com/public-apis/public-apis).
/// Free ones work at once; for key APIs the owner saves their own key here (sealed on the server, the avatar never sees it).
class PublicApisScreen extends StatefulWidget {
  const PublicApisScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PublicApisScreen> createState() => _PublicApisScreenState();
}

class _PublicApisScreenState extends State<PublicApisScreen> {
  List<Map<String, dynamic>> _rows = [];
  List<Map<String, dynamic>> _cats = [];
  int _total = 0;
  String _q = '';
  String _cat = '';
  String _auth = 'any';
  bool _busy = false;
  String? _err;
  Timer? _deb;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _deb?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final r = await app.api!.publicApis(q: _q, cat: _cat, auth: _auth);
      if (!mounted) return;
      setState(() {
        _rows = List<Map<String, dynamic>>.from((r['results'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        _total = (r['total'] as num?)?.toInt() ?? _total;
        final c = List<Map<String, dynamic>>.from((r['categories'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        if (c.isNotEmpty) _cats = c;
      });
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _search(String v) {
    _q = v.trim();
    _deb?.cancel();
    _deb = Timer(const Duration(milliseconds: 350), _load);
  }

  Future<void> _say(String t) async {
    final ok = await app.send(t);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok ? 'Chat mein bhej diya: "$t"' : 'Bhej nahi paya')));
    }
  }

  Future<void> _saveKey(Map<String, dynamic> a) async {
    final key = TextEditingController();
    final field = TextEditingController();
    var place = 'query';
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: Text('${a['name']} ki key'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Key sirf server par band (encrypted) rehti hai. Hoola use kabhi dekhta ya bolta nahi.',
                  style: TextStyle(color: C.muted, fontSize: 12.5)),
              TextField(controller: key, obscureText: true, decoration: const InputDecoration(labelText: 'API key')),
              const SizedBox(height: 8),
              const Text('Key kahan jaati hai? (docs mein likha hota hai)', style: TextStyle(color: C.muted, fontSize: 12.5)),
              Wrap(spacing: 8, children: [
                for (final e in const {'query': 'URL mein (?apikey=)', 'header': 'Header mein'}.entries)
                  ChoiceChip(
                    label: Text(e.value),
                    selected: place == e.key,
                    showCheckmark: false,
                    selectedColor: C.accent,
                    labelStyle: TextStyle(color: place == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                    onSelected: (_) => set(() => place = e.key),
                  ),
              ]),
              TextField(
                controller: field,
                decoration: InputDecoration(labelText: place == 'header' ? 'Header ka naam (jaise X-Api-Key)' : 'Parameter ka naam (jaise apikey, appid, key)'),
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true || key.text.trim().length < 4) return;
    try {
      await app.api!.publicApiKey('${a['id']}', key.text.trim(), place: place, field: field.text.trim());
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${a['name']} ki key save ho gayi')));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  void _open(Map<String, dynamic> a) {
    final free = a['free_no_key'] == true;
    final saved = a['key_saved'] == true;
    final worked = List<Map<String, dynamic>>.from((a['worked_before'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: C.bgBottom,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${a['name']}', style: display(19)),
            Text('${a['cat']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            const SizedBox(height: 8),
            Text('${a['desc']}', style: const TextStyle(fontSize: 14, height: 1.35)),
            const SizedBox(height: 10),
            _badge(a),
            if (worked.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text('${worked.first['worked']} baar chal chuki hai — Hoola seedha use karega', style: const TextStyle(color: C.ok, fontSize: 12.5)),
            ],
            const SizedBox(height: 14),
            Wrap(spacing: 8, runSpacing: 8, children: [
              FilledButton.icon(
                onPressed: () {
                  Navigator.pop(ctx);
                  _say('${a['name']} API (api_id ${a['id']}) se ${a['desc']} — mujhe dikhao');
                },
                icon: const Icon(Icons.auto_awesome_rounded, size: 18),
                label: Text('${app.aName} se use karwaiye'),
              ),
              if (!free)
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.pop(ctx);
                    _saveKey(a);
                  },
                  icon: Icon(saved ? Icons.key_rounded : Icons.key_off_rounded, size: 18),
                  label: Text(saved ? 'Key badliye' : 'Apni key save kijiye'),
                ),
              if (saved)
                TextButton(
                  onPressed: () async {
                    Navigator.pop(ctx);
                    await app.api!.publicApiKeyDelete('${a['id']}');
                    await _load();
                  },
                  child: const Text('Key hataiye', style: TextStyle(color: C.bad)),
                ),
              TextButton.icon(
                onPressed: () => launchUrl(Uri.parse('${a['link']}'), mode: LaunchMode.externalApplication),
                icon: const Icon(Icons.open_in_new_rounded, size: 18),
                label: Text(free ? 'Docs' : 'Docs / free key yahan'),
              ),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _badge(Map<String, dynamic> a) {
    final free = a['free_no_key'] == true;
    final saved = a['key_saved'] == true;
    final (String t, Color c) = free
        ? ('Free · key nahi chahiye', C.ok)
        : saved
            ? ('Key save hai', C.teal)
            : ('Key chahiye (${a['auth']})', C.warn);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withOpacity(.15), borderRadius: BorderRadius.circular(8)),
      child: Text(t, style: TextStyle(color: c, fontSize: 11.5, fontWeight: FontWeight.w700)),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Public APIs · ${_total == 0 ? '2,100+' : _total}'), backgroundColor: Colors.transparent),
        body: Aurora(
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 6),
              child: TextField(
                onChanged: _search,
                decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.search_rounded), hintText: 'Kya chahiye? mausam, IFSC, holidays, cricket, currency…'),
              ),
            ),
            SizedBox(
              height: 42,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
                for (final e in const {'any': 'Sab', 'none': 'Free (bina key)', 'key': 'Key wali'}.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ChoiceChip(
                      label: Text(e.value),
                      selected: _auth == e.key,
                      showCheckmark: false,
                      selectedColor: C.accent,
                      labelStyle: TextStyle(color: _auth == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                      onSelected: (_) {
                        setState(() => _auth = e.key);
                        _load();
                      },
                    ),
                  ),
                if (_cat.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: InputChip(
                      label: Text(_cat),
                      onDeleted: () {
                        setState(() => _cat = '');
                        _load();
                      },
                    ),
                  ),
              ]),
            ),
            if (_busy) const LinearProgressIndicator(minHeight: 2),
            if (_err != null) Padding(padding: const EdgeInsets.all(12), child: Text(_err!, style: const TextStyle(color: C.bad))),
            Expanded(
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
                if (_q.isEmpty && _cat.isEmpty && _cats.isNotEmpty) ...[
                  const Caption('CATEGORIES'),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    for (final c in _cats)
                      ActionChip(
                        label: Text('${c['cat']} · ${c['count']}', style: const TextStyle(fontSize: 12, color: C.chip)),
                        backgroundColor: const Color(0x14FFFFFF),
                        onPressed: () {
                          setState(() => _cat = '${c['cat']}');
                          _load();
                        },
                      ),
                  ]),
                  const SizedBox(height: 14),
                  const Caption('KUCH FREE APIs'),
                ],
                for (final a in _rows)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Glass(
                      padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
                      child: InkWell(
                        onTap: () => _open(a),
                        child: Row(children: [
                          Expanded(
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text('${a['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
                              Text('${a['desc']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.3)),
                              const SizedBox(height: 5),
                              Row(children: [
                                _badge(a),
                                const SizedBox(width: 6),
                                Flexible(child: Text('${a['cat']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 11.5))),
                                if ((a['worked_before'] as List? ?? const []).isNotEmpty)
                                  const Padding(padding: EdgeInsets.only(left: 6), child: Icon(Icons.verified_rounded, size: 14, color: C.ok)),
                              ]),
                            ]),
                          ),
                          const Icon(Icons.chevron_right_rounded, color: C.muted),
                        ]),
                      ),
                    ),
                  ),
                if (!_busy && _rows.isEmpty && _err == null)
                  const Padding(padding: EdgeInsets.all(20), child: Text('Kuch nahi mila. Dusre shabd try kijiye.', style: TextStyle(color: C.muted))),
                const SizedBox(height: 8),
                const Text('Source: github.com/public-apis/public-apis (MIT). Hoola sirf padhne wali (GET) calls karta hai.',
                    style: TextStyle(color: C.faint, fontSize: 11)),
              ]),
            ),
          ]),
        ),
      );
}
