/// Profile > Content writer (v0.101 Kalam Sahayak): blogs, product pages, emails, newsletters, social captions, website
/// pages and Google Business posts in HER brand voice, from HER facts. Every claim is checked (her facts, the web, the
/// rules: ASCI, CCPA, Legal Metrology, email rules) and NOTHING is published without her tap on the card.
/// Tabs: Likho (new piece), Lekh (all pieces), Ideas (festival / season ideas), Aawaz (her voice, fact list, words),
/// Niyam (business details, email footer, WordPress).
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _kinds = {
  'blog': ('Blog', Icons.article_rounded),
  'product': ('Product page', Icons.shopping_bag_rounded),
  'email': ('Email', Icons.mail_rounded),
  'newsletter': ('Newsletter', Icons.newspaper_rounded),
  'social': ('Social post', Icons.tag_rounded),
  'page': ('Website page', Icons.web_rounded),
  'gbp': ('Google Business', Icons.storefront_rounded),
};
const _langs = {'hinglish': 'Hinglish', 'hi': 'हिंदी', 'en': 'English', 'mr': 'मराठी', 'gu': 'ગુજરાતી', 'ta': 'தமிழ்', 'te': 'తెలుగు', 'kn': 'ಕನ್ನಡ', 'bn': 'বাংলা'};
const _statusLabel = {'draft': 'Draft', 'checked': 'Jaancha hua', 'waiting': 'Haan ka intezaar', 'published': 'Publish', 'rejected': 'Mana'};
const _copyWhere = ['instagram', 'facebook', 'linkedin', 'whatsapp', 'amazon', 'flipkart', 'shopify', 'website', 'google business'];

Color _statusCol(String s) => switch (s) {
      'published' => C.ok,
      'waiting' => C.accent,
      'checked' => C.teal,
      'rejected' => C.faint,
      _ => C.accentSoft,
    };

Color _levelCol(String l) => switch (l) { 'block' => C.bad, 'warn' => C.warn, _ => C.faint };

Future<void> openKalamPiece(BuildContext context, Santosh app, String id) =>
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => KalamPiecePage(app: app, id: id)));

class KalamScreen extends StatefulWidget {
  const KalamScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<KalamScreen> createState() => _KalamScreenState();
}

class _KalamScreenState extends State<KalamScreen> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  int _tick = -1;

  @override
  void initState() {
    super.initState();
    _tick = app.kalamTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.kalamTick != _tick) {
      _tick = app.kalamTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.kalamAll();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 5,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: Text('${app.aName} · Content writer'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Likho'),
              Tab(text: 'Lekh'),
              Tab(text: 'Ideas'),
              Tab(text: 'Aawaz'),
              Tab(text: 'Niyam'),
            ]),
          ),
          body: Aurora(
            child: _d == null
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(children: [
                    _WriteTab(app: app, onDone: _load),
                    _PiecesTab(app: app, pieces: _list(_d!['pieces']), onChanged: _load),
                    _IdeasTab(app: app, onDone: _load),
                    _VoiceTab(app: app, st: _map(_d!['settings']), onChanged: _load),
                    _RulesTab(app: app, st: _map(_d!['settings']), onChanged: _load),
                  ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- Likho
class _WriteTab extends StatefulWidget {
  const _WriteTab({required this.app, required this.onDone});
  final Santosh app;
  final Future<void> Function() onDone;
  @override
  State<_WriteTab> createState() => _WriteTabState();
}

class _WriteTabState extends State<_WriteTab> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;
  String _kind = 'blog';
  String _lang = '';
  bool _paid = false;
  bool _busy = false;
  final _brief = TextEditingController();
  final _keyword = TextEditingController();
  final _exp = TextEditingController();
  final _links = TextEditingController();
  final List<Map<String, dynamic>> _files = [];
  final Map<String, TextEditingController> _prod = {
    for (final k in ['maker', 'generic_name', 'net_quantity', 'mrp', 'made_on', 'origin', 'care', 'fssai', 'best_before']) k: TextEditingController(),
  };
  static const _prodLabels = {
    'maker': 'Banane / pack / import wale ka naam + pata',
    'generic_name': 'Aam naam (jaise "Shrikhand")',
    'net_quantity': 'Net quantity (500 g, 1 L, 2 pcs)',
    'mrp': 'MRP (sab tax mila ke)',
    'made_on': 'Banane ka mahina / saal',
    'origin': 'Country of origin',
    'care': 'Consumer care (naam, phone, email)',
    'fssai': 'FSSAI licence no. (khane ki cheez)',
    'best_before': 'Best before / use by',
  };

  Future<void> _attach() async {
    final files = await pickAttachments(context, max: 3);
    for (final f in files) {
      try {
        final r = await widget.app.api!.chatFile(widget.app.conversationId ?? '', f.name, f.bytes);
        setState(() => _files.add({'file_id': r['file_id'], 'name': f.name}));
      } catch (e) {
        if (mounted) _snack(context, '$e');
      }
    }
  }

  Future<void> _write() async {
    if (_brief.text.trim().isEmpty && _files.isEmpty && _links.text.trim().isEmpty) {
      _snack(context, 'Kis baare mein likhna hai, ek line likhiye.');
      return;
    }
    setState(() => _busy = true);
    try {
      final prod = {for (final e in _prod.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
      final r = await widget.app.api!.kalamWrite({
        'brief': _brief.text.trim(),
        'kind': _kind,
        if (_lang.isNotEmpty) 'lang': _lang,
        'keyword': _keyword.text.trim(),
        'experience': _exp.text.trim(),
        'paid': _paid,
        'file_ids': [for (final f in _files) f['file_id']],
        'urls': _links.text.split(RegExp(r'[\s,]+')).where((x) => x.startsWith('http')).toList(),
        if (_kind == 'product' && prod.isNotEmpty) 'product': prod,
        'conversation_id': widget.app.conversationId ?? '',
      });
      final p = _map(r['piece']);
      _brief.clear();
      _exp.clear();
      _files.clear();
      await widget.onDone();
      if (mounted) {
        _snack(context, _s(r['say']));
        openKalamPiece(context, widget.app, _s(p['id']));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Kya likhna hai?', style: display(17)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final e in _kinds.entries)
              ChoiceChip(
                avatar: Icon(e.value.$2, size: 16),
                label: Text(e.value.$1),
                selected: _kind == e.key,
                onSelected: (_) => setState(() => _kind = e.key),
              ),
          ]),
          const SizedBox(height: 10),
          TextField(
            controller: _brief,
            minLines: 3,
            maxLines: 8,
            decoration: const InputDecoration(
                labelText: 'Apne shabdon mein bataiye', hintText: 'Jaise: Diwali par 20% chhoot ka email, 2 Nov tak, sirf purane graahakon ke liye'),
          ),
          TextField(controller: _keyword, decoration: const InputDecoration(labelText: 'Google keyword (blog / page ke liye, optional)')),
          if (_kind == 'blog' || _kind == 'page')
            TextField(controller: _exp, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Aapka apna anubhav / kissa (Google isse pasand karta hai)')),
          TextField(controller: _links, decoration: const InputDecoration(labelText: 'Link (apni site / product page), optional')),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 4, children: [
            ChoiceChip(label: const Text('Meri bhasha'), selected: _lang.isEmpty, onSelected: (_) => setState(() => _lang = '')),
            for (final e in _langs.entries) ChoiceChip(label: Text(e.value), selected: _lang == e.key, onSelected: (_) => setState(() => _lang = e.key)),
          ]),
          if (_kind == 'social')
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: _paid,
              title: const Text('Paid / sponsored post'),
              subtitle: const Text('Pehli line #Ad (ASCI niyam)'),
              onChanged: (v) => setState(() => _paid = v),
            ),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final f in _files) InputChip(label: Text(_s(f['name'])), onDeleted: () => setState(() => _files.remove(f))),
            ActionChip(avatar: const Icon(Icons.attach_file_rounded, size: 16), label: const Text('Brochure / price list / photo'), onPressed: _attach),
          ]),
        ]),
      ),
      if (_kind == 'product') ...[
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Zaroori jaankari (packed saamaan)', style: display(15)),
            const Text('Legal Metrology niyam: online bechne par yeh dikhana zaroori. Jo nahi pata, khaali chhodiye: Hoola khud nahi bharega.',
                style: TextStyle(color: C.faint, fontSize: 12)),
            for (final e in _prod.entries) TextField(controller: e.value, decoration: InputDecoration(labelText: _prodLabels[e.key])),
          ]),
        ),
      ],
      const SizedBox(height: 14),
      _busy
          ? const Center(child: Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator()))
          : GradientButton(label: 'Likho', icon: Icons.edit_rounded, onTap: _write),
      const SizedBox(height: 10),
      Text('${widget.app.aName} sirf aapke diye facts se likhta hai; jo pata nahi woh [khaali] chhodta hai. Publish aapki haan se hi.',
          style: const TextStyle(color: C.faint, fontSize: 12)),
    ]);
  }
}

// ---------------------------------------------------------------- Lekh
class _PiecesTab extends StatefulWidget {
  const _PiecesTab({required this.app, required this.pieces, required this.onChanged});
  final Santosh app;
  final List<Map<String, dynamic>> pieces;
  final Future<void> Function() onChanged;
  @override
  State<_PiecesTab> createState() => _PiecesTabState();
}

class _PiecesTabState extends State<_PiecesTab> {
  String _status = '';
  @override
  Widget build(BuildContext context) {
    final rows = widget.pieces.where((p) => _status.isEmpty || p['status'] == _status).toList();
    return RefreshIndicator(
      onRefresh: widget.onChanged,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Wrap(spacing: 6, runSpacing: 4, children: [
          ChoiceChip(label: const Text('Sab'), selected: _status.isEmpty, onSelected: (_) => setState(() => _status = '')),
          for (final e in _statusLabel.entries) ChoiceChip(label: Text(e.value), selected: _status == e.key, onSelected: (_) => setState(() => _status = e.key)),
        ]),
        const SizedBox(height: 8),
        if (rows.isEmpty) const Padding(padding: EdgeInsets.all(20), child: Text('Abhi koi lekh nahi. "Likho" se shuru kariye.', style: TextStyle(color: C.muted))),
        for (final p in rows)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Press(
              onTap: () => openKalamPiece(context, widget.app, _s(p['id'])),
              child: Glass(
                child: Row(children: [
                  Icon((_kinds[_s(p['kind'])] ?? ('', Icons.article_rounded)).$2, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(p['title']), style: display(14.5), maxLines: 2, overflow: TextOverflow.ellipsis),
                      Text('${p['number']} · ${p['kind_label']} · ${p['words']} shabd', style: const TextStyle(color: C.muted, fontSize: 12)),
                    ]),
                  ),
                  Pill(_statusLabel[_s(p['status'])] ?? _s(p['status']), fg: _statusCol(_s(p['status']))),
                ]),
              ),
            ),
          ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Ideas
class _IdeasTab extends StatefulWidget {
  const _IdeasTab({required this.app, required this.onDone});
  final Santosh app;
  final Future<void> Function() onDone;
  @override
  State<_IdeasTab> createState() => _IdeasTabState();
}

class _IdeasTabState extends State<_IdeasTab> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;
  Map<String, dynamic>? _d;
  bool _busy = false;
  String _writing = '';

  Future<void> _load() async {
    setState(() => _busy = true);
    try {
      final d = await widget.app.api!.kalamIdeas();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _write(Map<String, dynamic> idea) async {
    setState(() => _writing = _s(idea['title']));
    try {
      final r = await widget.app.api!.kalamWrite({'brief': '${idea['title']}. ${idea['why']}', 'kind': idea['kind'], 'conversation_id': widget.app.conversationId ?? ''});
      await widget.onDone();
      if (mounted) openKalamPiece(context, widget.app, _s(_map(r['piece'])['id']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _writing = '');
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final ideas = _list(_d?['ideas']);
    final dates = _list(_d?['dates']);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Aage ke tyohar aur mauke', style: display(16)),
          const SizedBox(height: 4),
          const Text('Aapke business aur aane wale dino ke hisaab se kya likhein.', style: TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 10),
          _busy ? const Center(child: CircularProgressIndicator()) : GlassButton(label: 'Ideas dikhao', icon: Icons.lightbulb_rounded, onTap: _load),
        ]),
      ),
      if (dates.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Wrap(spacing: 6, runSpacing: 4, children: [for (final d in dates) Pill('${_s(d['date']).substring(5)} ${d['name']}', fg: C.accent2)]),
        ),
      for (final i in ideas)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon((_kinds[_s(i['kind'])] ?? ('', Icons.article_rounded)).$2, color: C.accent, size: 18),
                const SizedBox(width: 8),
                Expanded(child: Text(_s(i['title']), style: display(14.5))),
              ]),
              if (_s(i['why']).isNotEmpty) Text(_s(i['why']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (_s(i['date']).isNotEmpty) Text('Publish: ${i['date']}', style: const TextStyle(color: C.accent, fontSize: 12)),
              Align(
                alignment: Alignment.centerRight,
                child: _writing == _s(i['title'])
                    ? const Padding(padding: EdgeInsets.all(8), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
                    : TextButton(onPressed: _writing.isEmpty ? () => _write(i) : null, child: const Text('Yeh likho')),
              ),
            ]),
          ),
        ),
    ]);
  }
}

// ---------------------------------------------------------------- Aawaz (brand voice + facts)
class _VoiceTab extends StatelessWidget {
  const _VoiceTab({required this.app, required this.st, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> st;
  final Future<void> Function() onChanged;

  Future<void> _learn(BuildContext context) async {
    final text = TextEditingController();
    final link = TextEditingController();
    final List<Map<String, dynamic>> files = [];
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Apna likha hua dijiye'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Text('Purane post, email, website ka text: jitna aapka asli likha, utna achha.', style: TextStyle(fontSize: 12.5)),
              TextField(controller: text, minLines: 4, maxLines: 10, decoration: const InputDecoration(labelText: 'Yahan paste kariye')),
              TextField(controller: link, decoration: const InputDecoration(labelText: 'Ya apni website / blog ka link')),
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                for (final f in files) Chip(label: Text(_s(f['name']))),
                ActionChip(
                  label: const Text('File'),
                  avatar: const Icon(Icons.attach_file_rounded, size: 16),
                  onPressed: () async {
                    final picked = await pickAttachments(c, max: 3);
                    for (final f in picked) {
                      try {
                        final r = await app.api!.chatFile(app.conversationId ?? '', f.name, f.bytes);
                        set(() => files.add({'file_id': r['file_id'], 'name': f.name}));
                      } catch (_) {}
                    }
                  },
                ),
              ]),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne do')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Seekho')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.kalamVoice({
        'text': text.text.trim(),
        'file_ids': [for (final f in files) f['file_id']],
        'urls': link.text.trim().startsWith('http') ? [link.text.trim()] : <String>[],
      });
      if (context.mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  Future<void> _addFact(BuildContext context) async {
    final f = TextEditingController();
    final src = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Pakki baat (fact)'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: f, minLines: 1, maxLines: 4, decoration: const InputDecoration(labelText: 'Jaise: 100 Mbps plan Rs 499 mahina')),
          TextField(controller: src, decoration: const InputDecoration(labelText: 'Kahan se (rate card, certificate...)')),
        ]),
        actions: [FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodo'))],
      ),
    );
    if (ok != true) return;
    try {
      await app.api!.kalamFact(f.text.trim(), src.text.trim());
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  Future<void> _removeFact(BuildContext context, int i) async {
    final facts = _list(st['facts'])..removeAt(i);
    try {
      await app.api!.kalamSettings({'facts': facts});
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final v = _map(st['voice']);
    final facts = _list(st['facts']);
    Widget words(String key, String label, List<String> value) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: Text(value.isEmpty ? '-' : value.join(', ')),
          trailing: const Icon(Icons.edit_rounded, size: 18),
          onTap: () async {
            final c = TextEditingController(text: value.join('\n'));
            final ok = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(
                title: Text(label),
                content: TextField(controller: c, minLines: 3, maxLines: 8, decoration: const InputDecoration(helperText: 'Har line ek')),
                actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
              ),
            );
            if (ok != true) return;
            try {
              await app.api!.kalamSettings({key: c.text.split('\n').map((x) => x.trim()).where((x) => x.isNotEmpty).toList()});
            } catch (e) {
              if (context.mounted) _snack(context, '$e');
            }
            await onChanged();
          },
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Aapki likhne ki aawaz', style: display(16))),
            Pill('${st['samples'] ?? 0} namune', fg: C.accent2),
          ]),
          const SizedBox(height: 6),
          if (_s(v['summary']).isNotEmpty) Text(_s(v['summary']), style: const TextStyle(color: C.chip)),
          if (v.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                  [if (_s(v['person']).isNotEmpty) 'Sambodhan: ${v['person']}', if (_s(v['sentences']).isNotEmpty) 'Vaakya: ${v['sentences']}', if (_s(v['emoji']).isNotEmpty) 'Emoji: ${v['emoji']}']
                      .join(' · '),
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ),
          for (final n in [..._strs(v['notes']), ..._strs(v['learned'])]) Text('• $n', style: const TextStyle(color: C.chip, fontSize: 13)),
          if (_strs(v['phrases']).isNotEmpty) Text('Aapke shabd: ${_strs(v['phrases']).join(', ')}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 10),
          GlassButton(label: 'Mera likha hua seekho', icon: Icons.school_rounded, onTap: () => _learn(context)),
          const SizedBox(height: 4),
          const Text('Aap draft khud badalti hain to bhi Hoola seekhta hai (upar "seekha" mein dikhega).', style: TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(children: [
          words('tone', 'Andaaz (jaise: dosti wala, seedha, izzat se)', _strs(st['tone'])),
          words('do_words', 'Yeh shabd pasand hain', _strs(st['do_words'])),
          words('dont_words', 'Yeh kabhi mat likho', _strs(st['dont_words'])),
          words('rules', 'Mere niyam', _strs(st['rules'])),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Pakki baatein (${facts.length})', style: display(16))),
            IconButton(onPressed: () => _addFact(context), icon: const Icon(Icons.add_circle_rounded, color: C.accent)),
          ]),
          const Text('Daam, aankde, certificate, award: lekh mein sirf yahi ya aapke brief / file ki baatein jaati hain.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          for (var i = 0; i < facts.length; i++)
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text(_s(facts[i]['fact'])),
              subtitle: Text(_s(facts[i]['source'])),
              trailing: IconButton(icon: const Icon(Icons.close_rounded, size: 18), onPressed: () => _removeFact(context, i)),
            ),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- Niyam (business details + WordPress)
class _RulesTab extends StatelessWidget {
  const _RulesTab({required this.app, required this.st, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> st;
  final Future<void> Function() onChanged;

  Future<void> _save(BuildContext context, Map<String, dynamic> body) async {
    try {
      await app.api!.kalamSettings(body);
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  Future<void> _wordpress(BuildContext context) async {
    final wp = _map(st['wordpress']);
    final url = TextEditingController(text: _s(wp['url']));
    final user = TextEditingController(text: _s(wp['user']));
    final pw = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('WordPress jodiye'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('WordPress > Users > Profile > Application Passwords mein "Hoola" naam se naya password banaiye (24 akshar). '
                'Apna login password mat daaliye.', style: TextStyle(fontSize: 12.5)),
            TextField(controller: url, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'Site (https://...)')),
            TextField(controller: user, decoration: const InputDecoration(labelText: 'WordPress username')),
            TextField(controller: pw, obscureText: true, enableSuggestions: false, autocorrect: false, decoration: const InputDecoration(labelText: 'Application Password')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodo')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.kalamWordpress(url.text.trim(), user.text.trim(), pw.text);
      if (context.mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    pw.clear();
    await onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final wp = _map(st['wordpress']);
    Widget row(String key, String label, String value, {int lines = 1}) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: Text(value.isEmpty ? '-' : value, maxLines: 3, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.edit_rounded, size: 18),
          onTap: () async {
            final c = TextEditingController(text: value);
            final ok = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(
                title: Text(label),
                content: TextField(controller: c, minLines: lines, maxLines: lines > 1 ? 8 : 1),
                actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
              ),
            );
            if (ok == true && context.mounted) await _save(context, {key: c.text.trim()});
          },
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(children: [
          row('business', 'Business ka naam', _s(st['business'])),
          row('about', 'Hum kya karte / bechte hain', _s(st['about']), lines: 4),
          row('audience', 'Hamare graahak kaun hain', _s(st['audience']), lines: 3),
          row('language', 'Bhasha (hinglish / hi / en / mr ...)', _s(st['language'])),
          row('cta', 'Aakhir mein kya karne ko kahein (call karein / order karein)', _s(st['cta'])),
          row('contact', 'Phone / WhatsApp', _s(st['contact'])),
          row('website', 'Website', _s(st['website'])),
          row('address', 'Business ka pata (email footer)', _s(st['address']), lines: 3),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: st['ai_note'] == true,
            title: const Text('"AI ki madad se likha" line jodo'),
            subtitle: const Text('Blog / page / newsletter ke neeche'),
            onChanged: (v) => _save(context, {'ai_note': v}),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.public_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('WordPress', style: display(16))),
            Pill(wp['ready'] == true ? 'Juda hai' : 'Nahi juda', fg: wp['ready'] == true ? C.ok : C.faint),
          ]),
          if (wp['ready'] == true) Text('${wp['url']} · ${wp['user']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GlassButton(label: wp['ready'] == true ? 'Badlo' : 'Jodo', icon: Icons.link_rounded, onTap: () => _wordpress(context))),
            if (wp['ready'] == true) ...[
              const SizedBox(width: 8),
              Expanded(
                child: GlassButton(
                  label: 'Hatao',
                  color: C.bad,
                  onTap: () async {
                    await app.api!.kalamWordpressOff();
                    await onChanged();
                  },
                ),
              ),
            ],
          ]),
          const SizedBox(height: 6),
          const Text('Password band tijori mein rehta hai; Hoola post sirf aapki haan ke baad daalta hai.', style: TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- one piece
class KalamPiecePage extends StatefulWidget {
  const KalamPiecePage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<KalamPiecePage> createState() => _KalamPiecePageState();
}

class _KalamPiecePageState extends State<KalamPiecePage> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _p;
  String _busy = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = await app.api!.kalamPiece(widget.id);
      if (mounted) setState(() => _p = p);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(String label, Future<Map<String, dynamic>> Function() fn) async {
    setState(() => _busy = label);
    try {
      final r = await fn();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  String _fullText() {
    final p = _p!;
    final m = _map(p['meta']);
    final caps = _map(m['captions']);
    return [
      if (_s(m['subject']).isNotEmpty) 'Subject: ${m['subject']}',
      if (_s(m['preheader']).isNotEmpty) 'Preheader: ${m['preheader']}',
      _s(p['body']),
      for (final e in caps.entries) '\n--- ${e.key} ---\n${e.value}',
    ].join('\n');
  }

  Future<void> _revise() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Kya badalna hai?'),
        content: TextField(controller: c, minLines: 2, maxLines: 6, decoration: const InputDecoration(hintText: 'Jaise: chhota karo, aur dosti wali bhasha, offer upar likho')),
        actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Badlo'))],
      ),
    );
    if (ok == true && c.text.trim().isNotEmpty) {
      await _do('revise', () => app.api!.kalamDo(widget.id, 'revise', {'instruction': c.text.trim(), 'conversation_id': app.conversationId ?? ''}));
    }
  }

  Future<void> _edit() async {
    final title = TextEditingController(text: _s(_p!['title']));
    final body = TextEditingController(text: _s(_p!['body']));
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(
      builder: (c) => Scaffold(
        appBar: AppBar(title: const Text('Khud likhiye'), actions: [TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Save'))]),
        body: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Title')),
            const SizedBox(height: 8),
            Expanded(child: TextField(controller: body, expands: true, maxLines: null, minLines: null, decoration: const InputDecoration(border: OutlineInputBorder()))),
          ]),
        ),
      ),
    ));
    if (ok == true) await _do('edit', () => app.api!.kalamEdit(widget.id, {'title': title.text, 'body': body.text}));
  }

  Future<void> _repurpose() async {
    final pick = <String>{};
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Isi se aur kya banaun?'),
          content: Wrap(spacing: 6, runSpacing: 6, children: [
            for (final e in _kinds.entries)
              if (e.key != _p!['kind'])
                FilterChip(label: Text(e.value.$1), selected: pick.contains(e.key), onSelected: (v) => set(() => v ? pick.add(e.key) : pick.remove(e.key))),
          ]),
          actions: [FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Banao'))],
        ),
      ),
    );
    if (ok == true && pick.isNotEmpty) {
      await _do('repurpose', () => app.api!.kalamDo(widget.id, 'repurpose', {'kinds': pick.toList(), 'conversation_id': app.conversationId ?? ''}));
    }
  }

  Future<void> _publish() async {
    String dest = _p!['kind'] == 'email' || _p!['kind'] == 'newsletter' ? 'email' : 'copy';
    String status = 'publish';
    String where = 'instagram';
    final to = TextEditingController();
    final when = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => Padding(
          padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(c).viewInsets.bottom),
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Kahan publish karna hai?', style: display(17)),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final d in const [('wordpress', 'Meri WordPress site'), ('email', 'Email'), ('page', 'Hoola page (link)'), ('copy', 'Main khud daalungi')])
                  ChoiceChip(label: Text(d.$2), selected: dest == d.$1, onSelected: (_) => set(() => dest = d.$1)),
              ]),
              const SizedBox(height: 10),
              if (dest == 'wordpress')
                Wrap(spacing: 6, children: [
                  for (final s in const [('publish', 'Abhi live'), ('draft', 'Draft mein'), ('future', 'Time par')])
                    ChoiceChip(label: Text(s.$2), selected: status == s.$1, onSelected: (_) => set(() => status = s.$1)),
                ]),
              if (dest == 'wordpress' && status == 'future') TextField(controller: when, decoration: const InputDecoration(labelText: 'Kab (jaise: kal 10 baje, 25/10 9:30)')),
              if (dest == 'email')
                TextField(controller: to, minLines: 1, maxLines: 4, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Kisko (email, 50 tak; comma se)')),
              if (dest == 'copy')
                Wrap(spacing: 6, runSpacing: 4, children: [
                  for (final w in _copyWhere) ChoiceChip(label: Text(w), selected: where == w, onSelected: (_) => set(() => where = w)),
                ]),
              const SizedBox(height: 10),
              const Text('Pehle saari jaanch hogi; phir ek card aayega, aapki Haan par hi publish.', style: TextStyle(color: C.faint, fontSize: 12)),
              const SizedBox(height: 10),
              GradientButton(label: 'Card banao', icon: Icons.verified_rounded, onTap: () => Navigator.pop(c, true)),
            ]),
          ),
        ),
      ),
    );
    if (ok != true) return;
    Future<Map<String, dynamic>> req(bool force) => app.api!.kalamDo(widget.id, 'publish', {
          'dest': dest,
          'status': status,
          'when': when.text.trim(),
          'where': where,
          'to': to.text.split(RegExp(r'[\s,;]+')).where((x) => x.contains('@')).toList(),
          'force': force,
          'conversation_id': app.conversationId ?? '',
        });
    setState(() => _busy = 'publish');
    try {
      var r = await req(false);
      if (r['status'] == 'blocked' && mounted) {
        final blockers = _list(r['blockers']);
        final go = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
            title: const Text('Pehle yeh dekhiye'),
            content: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                for (final b in blockers)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text('• ${b['text']}${_s(b['fix']).isNotEmpty ? '\n  ${b['fix']}' : ''}', style: const TextStyle(fontSize: 13)),
                  ),
              ]),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Theek karti hoon')),
              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Main jaanti hoon, phir bhi', style: TextStyle(color: C.bad))),
            ],
          ),
        );
        if (go == true) r = await req(true);
      }
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  Future<void> _result() async {
    final views = TextEditingController();
    final clicks = TextEditingController();
    final orders = TextEditingController();
    final url = TextEditingController(text: _s(_map(_p!['published'])['url']));
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Kaisa chala?'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: views, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Kitne logon ne dekha')),
          TextField(controller: clicks, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Clicks / reply')),
          TextField(controller: orders, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Order / enquiry')),
          TextField(controller: url, decoration: const InputDecoration(labelText: 'Link (jahan daala)')),
        ]),
        actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
      ),
    );
    if (ok == true) {
      await _do('result', () => app.api!.kalamDo(widget.id, 'result', {
            'views': int.tryParse(views.text.trim()),
            'clicks': int.tryParse(clicks.text.trim()),
            'orders': int.tryParse(orders.text.trim()),
            'url': url.text.trim(),
          }));
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text(p == null ? 'Lekh' : '${p['number']} · ${p['kind_label']}'),
        actions: [
          if (p != null)
            PopupMenuButton<String>(
              onSelected: (v) async {
                if (v == 'copy') await _do('copy', () => app.api!.kalamDo(widget.id, 'copy'));
                if (v == 'files') await _do('files', () => app.api!.kalamDo(widget.id, 'files', {'conversation_id': app.conversationId ?? ''}));
                if (v == 'result') await _result();
                if (v == 'unpage') await _do('unpage', () => app.api!.kalamDo(widget.id, 'unpage'));
                if (v == 'delete') {
                  await app.api!.kalamDelete(widget.id);
                  if (context.mounted) Navigator.pop(context);
                }
              },
              itemBuilder: (_) => [
                const PopupMenuItem(value: 'files', child: Text('Word / HTML file')),
                const PopupMenuItem(value: 'copy', child: Text('Nayi copy')),
                const PopupMenuItem(value: 'result', child: Text('Kaisa chala (nateeja)')),
                if (_s(p['page_url']).isNotEmpty) const PopupMenuItem(value: 'unpage', child: Text('Hoola page band karo')),
                const PopupMenuItem(value: 'delete', child: Text('Mitao')),
              ],
            ),
        ],
      ),
      body: Aurora(
        child: p == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 120), children: [
                  _head(p),
                  const SizedBox(height: 10),
                  _checks(p),
                  const SizedBox(height: 10),
                  _text(p),
                ]),
              ),
      ),
      bottomNavigationBar: p == null || p['status'] == 'published'
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
                child: _busy.isNotEmpty
                    ? const SizedBox(height: 48, child: Center(child: CircularProgressIndicator()))
                    : Row(children: [
                        Expanded(child: GlassButton(label: 'Jaancho', icon: Icons.fact_check_rounded, height: 46, onTap: () => _do('check', () => app.api!.kalamDo(widget.id, 'check', {'conversation_id': app.conversationId ?? ''})))),
                        const SizedBox(width: 8),
                        Expanded(child: GlassButton(label: 'Badlo', icon: Icons.auto_fix_high_rounded, height: 46, onTap: _revise)),
                        const SizedBox(width: 8),
                        Expanded(child: GradientButton(label: 'Publish', icon: Icons.send_rounded, height: 46, onTap: p['status'] == 'waiting' ? null : _publish)),
                      ]),
              ),
            ),
    );
  }

  Widget _head(Map<String, dynamic> p) {
    final m = _map(p['meta']);
    final pub = _map(p['published']);
    final blanks = _strs(p['blanks']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: SelectableText(_s(p['title']), style: display(18))),
          Pill(_statusLabel[_s(p['status'])] ?? _s(p['status']), fg: _statusCol(_s(p['status']))),
        ]),
        const SizedBox(height: 4),
        Text('${p['words']} shabd${(p['target_words'] ?? 0) != 0 ? ' (lakshya ${p['target_words']})' : ''}${_s(p['keyword']).isNotEmpty ? ' · keyword: ${p['keyword']}' : ''}',
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
        for (final k in const ['subject', 'preheader', 'meta_title', 'meta_description', 'slug', 'button'])
          if (_s(m[k]).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 3), child: Text('$k: ${m[k]}', style: const TextStyle(color: C.chip, fontSize: 12.5))),
        if (blanks.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('Bharna baaki: ${blanks.join(', ')}', style: const TextStyle(color: C.bad, fontSize: 13, fontWeight: FontWeight.w600)),
          ),
        if (_s(pub['url']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GlassButton(label: 'Publish link kholo', icon: Icons.open_in_new_rounded, height: 40, onTap: () => Native.openExternal(url: _s(pub['url']))),
          ),
        const SizedBox(height: 8),
        Wrap(spacing: 6, runSpacing: 6, children: [
          ActionChip(
            avatar: const Icon(Icons.copy_rounded, size: 16),
            label: const Text('Copy'),
            onPressed: () {
              Clipboard.setData(ClipboardData(text: _fullText()));
              _snack(context, 'Copy ho gaya');
            },
          ),
          if (p['status'] != 'published') ActionChip(avatar: const Icon(Icons.edit_rounded, size: 16), label: const Text('Khud likho'), onPressed: _edit),
          ActionChip(avatar: const Icon(Icons.transform_rounded, size: 16), label: const Text('Roop badlo'), onPressed: _repurpose),
        ]),
      ]),
    );
  }

  Widget _checks(Map<String, dynamic> p) {
    final ch = _map(p['checks']);
    final items = _list(ch['items']);
    final claims = _list(ch['claims']);
    final sm = _map(ch['summary']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('Jaanch', style: display(16))),
          if (sm.isNotEmpty) ...[
            Pill('${sm['blockers'] ?? 0} rukawat', fg: (sm['blockers'] ?? 0) == 0 ? C.ok : C.bad),
            const SizedBox(width: 6),
            Pill('${sm['backed'] ?? 0}/${sm['claims'] ?? 0} daave pakke', fg: C.teal),
          ],
        ]),
        if (p['fresh_check'] != true)
          const Padding(padding: EdgeInsets.only(top: 4), child: Text('Web se facts abhi nahi jaanche: "Jaancho" dabaiye (publish se pehle apne aap bhi hoga).', style: TextStyle(color: C.faint, fontSize: 12))),
        for (final i in items)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(i['level'] == 'block' ? Icons.block_rounded : (i['level'] == 'warn' ? Icons.warning_amber_rounded : Icons.info_outline_rounded),
                  size: 18, color: _levelCol(_s(i['level']))),
              const SizedBox(width: 8),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(i['text']), style: TextStyle(color: i['level'] == 'info' ? C.muted : C.ink, fontSize: 13)),
                  if (_s(i['fix']).isNotEmpty) Text(_s(i['fix']), style: const TextStyle(color: C.faint, fontSize: 12)),
                ]),
              ),
            ]),
          ),
        if (claims.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('Daave (${claims.length})', style: display(14)),
          for (final c in claims)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Pill(_verdict(_s(c['verdict'])), fg: _verdictCol(_s(c['verdict']))),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(c['text']), style: const TextStyle(fontSize: 12.5, color: C.chip)),
                    if (_s(c['source']).isNotEmpty || _s(c['why']).isNotEmpty)
                      Text([_s(c['source']), _s(c['why'])].where((x) => x.isNotEmpty).join(': '), style: const TextStyle(color: C.faint, fontSize: 11.5)),
                    if (_s(c['url']).isNotEmpty)
                      InkWell(onTap: () => Native.openExternal(url: _s(c['url'])), child: Text(_s(c['url']), style: const TextStyle(color: C.accent, fontSize: 11.5))),
                  ]),
                ),
              ]),
            ),
        ],
      ]),
    );
  }

  static String _verdict(String v) => switch (v) {
        'backed' => 'aapki baat',
        'supported' => 'web: sahi',
        'contradicted' => 'web: galat',
        'unclear' => 'pakka nahi',
        _ => 'jaancha nahi',
      };
  static Color _verdictCol(String v) => switch (v) {
        'backed' || 'supported' => C.ok,
        'contradicted' => C.bad,
        _ => C.faint,
      };

  Widget _text(Map<String, dynamic> p) {
    final caps = _map(_map(p['meta'])['captions']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final line in _s(p['body']).split('\n'))
          if (line.startsWith('#'))
            Padding(
              padding: const EdgeInsets.only(top: 10, bottom: 4),
              child: SelectableText(line.replaceFirst(RegExp(r'^#+\s*'), ''), style: display(line.startsWith('## ') ? 16 : 18)),
            )
          else
            SelectableText(line.replaceAll('**', ''), style: const TextStyle(color: C.chip, height: 1.45, fontSize: 14)),
        for (final e in caps.entries) ...[
          const SizedBox(height: 12),
          Text(e.key, style: display(14, color: C.accent)),
          SelectableText(_s(e.value), style: const TextStyle(color: C.chip, height: 1.4)),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- chat cards
class KalamPieceCard extends StatelessWidget {
  const KalamPieceCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final sm = _map(v['summary']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon((_kinds[_s(v['kind'])] ?? ('', Icons.article_rounded)).$2, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['number']} · ${v['title']}', style: display(15), maxLines: 2, overflow: TextOverflow.ellipsis)),
          Pill(_statusLabel[_s(v['status'])] ?? _s(v['status']), fg: _statusCol(_s(v['status']))),
        ]),
        if (_s(_map(v['meta'])['subject']).isNotEmpty) Text('Subject: ${_map(v['meta'])['subject']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        Text(_s(v['preview']), maxLines: 5, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.chip, height: 1.35)),
        if (sm.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('${v['words']} shabd · ${sm['blockers'] ?? 0} rukawat · ${sm['warnings'] ?? 0} dhyan dene wali', style: const TextStyle(color: C.faint, fontSize: 12)),
          ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(onPressed: () => openKalamPiece(context, app, _s(v['id'])), child: const Text('Kholo')),
        ),
      ]),
    );
  }
}

/// The publish card: she sees exactly where it goes; Haan publishes (copy = she pasted it herself), Mana stops it.
class KalamPublishCard extends StatefulWidget {
  const KalamPublishCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<KalamPublishCard> createState() => _KalamPublishCardState();
}

class _KalamPublishCardState extends State<KalamPublishCard> {
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.kalamDo(_s(widget.v['id']), 'decide',
          {'yes': yes, 'hash': _s(widget.v['hash']), 'conversation_id': widget.app.conversationId ?? ''});
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final decided = _s(v['decided']);
    final pub = _map(v['published']);
    final copy = v['dest'] == 'copy';
    final blockers = _list(v['blockers']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.publish_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(decided.isEmpty ? 'Publish karein?' : (decided == 'yes' ? 'Publish ho gaya' : 'Publish nahi kiya'), style: display(16))),
        ]),
        const SizedBox(height: 6),
        Text('${v['number']} · ${v['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
        Text(_s(v['where_label']), style: const TextStyle(color: C.accent, fontSize: 12.5)),
        const SizedBox(height: 6),
        Text(_s(v['preview']), maxLines: 6, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.chip, height: 1.35)),
        if (blockers.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('Aapne in rukawaton ke saath bhi kaha: ${blockers.map((b) => b['text']).join('; ')}', style: const TextStyle(color: C.bad, fontSize: 12.5)),
          ),
        if (_s(pub['url']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GlassButton(label: 'Link kholo', icon: Icons.open_in_new_rounded, height: 40, onTap: () => Native.openExternal(url: _s(pub['url']))),
          ),
        if (decided.isEmpty) ...[
          const SizedBox(height: 10),
          if (copy)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: Text('Copy karke khud daaliye; daal diya to "Daal diya" dabaiye.', style: TextStyle(color: C.faint, fontSize: 12)),
            ),
          _busy
              ? const Center(child: CircularProgressIndicator())
              : Row(children: [
                  Expanded(child: GlassButton(label: 'Mana', color: C.bad, height: 44, onTap: () => _decide(false))),
                  const SizedBox(width: 8),
                  if (copy) ...[
                    Expanded(
                      child: GlassButton(
                        label: 'Copy',
                        icon: Icons.copy_rounded,
                        height: 44,
                        onTap: () async {
                          try {
                            final p = await widget.app.api!.kalamPiece(_s(v['id']));
                            await Clipboard.setData(ClipboardData(text: _s(p['body'])));
                            if (context.mounted) _snack(context, 'Copy ho gaya');
                          } catch (e) {
                            if (context.mounted) _snack(context, '$e');
                          }
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                  ],
                  Expanded(child: GradientButton(label: copy ? 'Daal diya' : 'Haan, publish', height: 44, onTap: () => _decide(true))),
                ]),
        ],
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(onPressed: () => openKalamPiece(context, widget.app, _s(v['id'])), child: const Text('Poora dekho')),
        ),
      ]),
    );
  }
}
