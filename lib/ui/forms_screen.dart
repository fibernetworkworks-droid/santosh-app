import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication).catchError((_) => false);
}

/// A Google Form Santosh made or changed, shown in the chat.
class FormCard extends StatelessWidget {
  const FormCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'created';
    final title = v['title'] as String? ?? 'Google Form';
    final open = v['responder_link'] as String? ?? '';
    final edit = v['edit_link'] as String? ?? '';
    final n = (v['responses'] as num?)?.toInt();
    final qs = (v['questions'] as num?)?.toInt();
    final accepting = v['accepting'] != false;
    final (chip, fg) = switch (status) {
      'created' => ('BAN GAYA', C.ok),
      'updated' => ('BADAL DIYA', C.ok),
      _ => (status.toUpperCase(), C.chip),
    };
    final facts = [
      if (qs != null) '$qs sawaal',
      if (n != null) '$n jawab',
      if (v['is_quiz'] == true) 'quiz',
      accepting ? 'jawab le raha hai' : 'band hai',
    ].join(' · ');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.assignment_rounded, color: C.violet, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(chip, fg: fg),
          ]),
          const SizedBox(height: 6),
          Text(facts, style: const TextStyle(color: C.chip, fontSize: 13)),
          if (open.isNotEmpty || edit.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(children: [
              if (open.isNotEmpty)
                Expanded(child: GradientButton(label: 'Form kholiye', icon: Icons.open_in_new_rounded, height: 42, onTap: () => _open(open))),
              if (open.isNotEmpty && edit.isNotEmpty) const SizedBox(width: 8),
              if (edit.isNotEmpty)
                Expanded(child: GlassButton(label: 'Edit', icon: Icons.edit_rounded, height: 42, onTap: () => _open(edit))),
            ]),
          ],
        ]),
      ),
    );
  }
}

/// Profile > Google Forms: connect a Google account, see recent forms and which forms send new-answer alerts.
class FormsScreen extends StatefulWidget {
  const FormsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<FormsScreen> createState() => _FormsScreenState();
}

class _FormsScreenState extends State<FormsScreen> {
  Map<String, dynamic> _st = {};
  bool _loaded = false;
  String? _err;
  int _seenTick = 0;

  Santosh get app => widget.app;
  List<Map<String, dynamic>> _list(String k) =>
      List<Map<String, dynamic>>.from((_st[k] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  @override
  void initState() {
    super.initState();
    _seenTick = app.formsLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.formsLinkedTick != _seenTick) {
      _seenTick = app.formsLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.formsState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = null; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _link() async {
    try {
      await _open(await app.api!.formsLinkUrl());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _remove(String key) async {
    try {
      final r = await app.api!.formsRemove(key);
      if (mounted) setState(() => _st = r);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final accounts = _list('accounts');
    final recent = _list('recent');
    final watching = _list('watching');
    final canLink = _st['can_link'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('Google Forms'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Hoola ek line se Google Form ya quiz banata hai, sawaal badalta hai, jawab padhta aur samjhata hai, '
                'Sheet / Excel mein nikaalta hai aur naye jawab aane par batata hai. Doosron ko edit access dena aur '
                'jawab wale sawaal hatana hamesha aapke tap ke baad hi.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 14),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            for (final a in accounts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: Row(children: [
                  const Icon(Icons.assignment_turned_in_rounded, color: C.violet),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a['address'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(a['key'] == 'google' ? 'Google sign-in se' : 'Google Forms', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    if (a['status'] == 'error') Text(a['error'] as String? ?? 'Login fail', style: const TextStyle(color: C.bad, fontSize: 12)),
                  ])),
                  if (a['removable'] == true)
                    IconButton(tooltip: 'Hataiye', icon: const Icon(Icons.close_rounded, color: C.muted),
                        onPressed: () => _remove(a['key'] as String)),
                ])),
              ),
            if (_loaded) ...[
              accounts.isEmpty
                  ? GradientButton(label: 'Google Forms jodiye', icon: Icons.assignment_rounded, height: 50, onTap: canLink ? _link : null)
                  : GlassButton(label: 'Doosra Google account jodiye', icon: Icons.add_rounded, height: 44, onTap: canLink ? _link : null),
              if (!canLink)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text('Is server par Google sign-in abhi chalu nahi hai (GOOGLE_OAUTH_CLIENT_ID / SECRET).',
                      style: TextStyle(color: C.faint, fontSize: 12)),
                ),
              const SizedBox(height: 14),
            ],
            if (recent.isNotEmpty) ...[
              const Text('Haal ke forms', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Glass(child: Column(children: [
                for (final f in recent)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.description_outlined, color: C.chip),
                    title: Text(f['title'] as String? ?? ''),
                    subtitle: Text([
                      'Last: ${f['used'] ?? ''}',
                      if (watching.any((w) => w['form_id'] == f['id'])) 'naye jawab ka alert on',
                    ].join(' · '), style: const TextStyle(color: C.muted, fontSize: 12)),
                    trailing: const Icon(Icons.open_in_new_rounded, size: 18),
                    onTap: () => _open('https://docs.google.com/forms/d/${f['id']}/edit'),
                  ),
              ])),
              const SizedBox(height: 14),
            ],
            const Text('Bolkar dekhiye', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"Diwali Milan ke liye registration form banao: naam, phone, kitne log aayenge"',
              '"Customer feedback form banao, 1 se 5 rating ke saath"',
              '"Class 8 ke liye 10 sawaal ka GK quiz banao"',
              '"Feedback form mein kitne jawab aaye? Saar batao"',
              '"Jawab Google Sheet mein daal do"',
              '"Naye jawab aaye to mujhe batana"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}
