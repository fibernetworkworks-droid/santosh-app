/// Profile > Brand designer (v0.118 Brand Sahayak): a brand kit read from her logo, posters in her colours for every
/// platform size, festival posters a week before, and FINAL artwork only on her tap (proofs carry a PROOF mark).
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import '../native.dart';
import '../state.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

Color _hex(String h, [Color or = C.chip]) {
  final v = h.replaceAll('#', '');
  if (v.length != 6) return or;
  return Color(int.parse('FF$v', radix: 16));
}

const _status = {'draft': 'Proof', 'waiting': 'Aapki haan', 'approved': 'Final', 'rejected': 'Mana'};
Color _stCol(String s) => switch (s) { 'approved' => C.ok, 'waiting' => C.accent, 'rejected' => C.bad, _ => C.chip };

const _setsUi = {'social': 'Social (4)', 'whatsapp': 'WhatsApp', 'all_social': 'Sab platform', 'print': 'Print A4'};
const _kindsUi = {'poster': 'Poster', 'offer': 'Offer / sale', 'festival': 'Tyohar', 'event': 'Event', 'product': 'Product',
  'hiring': 'Hiring', 'announcement': 'Suchna', 'quote': 'Vichar / review'};

/// A proof / final picture (needs the key, so it goes with authHeaders).
class BrandImage extends StatelessWidget {
  const BrandImage({super.key, required this.app, required this.path, this.height, this.fit = BoxFit.contain});
  final Santosh app;
  final String path;
  final double? height;
  final BoxFit fit;
  @override
  Widget build(BuildContext context) {
    if (path.isEmpty || app.api == null) return SizedBox(height: height ?? 120, child: const Center(child: Icon(Icons.image_outlined)));
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: Image.network(app.api!.absolute(path), headers: app.api!.authHeaders, height: height, fit: fit,
          errorBuilder: (_, __, ___) => SizedBox(height: height ?? 120, child: const Center(child: Icon(Icons.broken_image_outlined))),
          loadingBuilder: (c, w, p) => p == null ? w : SizedBox(height: height ?? 120, child: const Center(child: CircularProgressIndicator()))),
    );
  }
}

Future<String> _fetch(Santosh app, String path, String name) async {
  final bytes = await app.api!.brandBytes(path);
  final dir = await getTemporaryDirectory();
  final f = File('${dir.path}/$name');
  await f.writeAsBytes(bytes);
  return f.path;
}

class BrandScreen extends StatefulWidget {
  const BrandScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<BrandScreen> createState() => _BrandScreenState();
}

class _BrandScreenState extends State<BrandScreen> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  int _tick = -1;

  @override
  void initState() {
    super.initState();
    _tick = app.brandTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.brandTick != _tick) {
      _tick = app.brandTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.brandAll();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: Text('${app.aName} · Brand designer'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Banao'),
              Tab(text: 'Designs'),
              Tab(text: 'Brand kit'),
              Tab(text: 'Tyohar'),
            ]),
          ),
          body: Aurora(
            child: _d == null
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(children: [
                    _MakeTab(app: app, d: _d!, onDone: _load),
                    _DesignsTab(app: app, designs: _list(_d!['designs']), onChanged: _load),
                    _KitTab(app: app, kit: _map(_d!['kit']), onChanged: _load),
                    _FestTab(app: app, fests: _list(_d!['festivals']), onDone: _load),
                  ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- Banao
class _MakeTab extends StatefulWidget {
  const _MakeTab({required this.app, required this.d, required this.onDone});
  final Santosh app;
  final Map<String, dynamic> d;
  final Future<void> Function() onDone;
  @override
  State<_MakeTab> createState() => _MakeTabState();
}

class _MakeTabState extends State<_MakeTab> {
  final _brief = TextEditingController();
  String _kind = '';
  final Set<String> _sets = {'social'};
  PickedFile? _photo;
  bool _busy = false;

  Future<void> _make() async {
    if (_brief.text.trim().isEmpty && _kind != 'festival') {
      _snack(context, 'Poster kis baare mein? Offer, daam, din likhiye.');
      return;
    }
    setState(() => _busy = true);
    try {
      String photo = '';
      if (_photo != null) {
        final f = await widget.app.api!.chatFile(widget.app.conversationId ?? '', _photo!.name, _photo!.bytes);
        photo = _s(f['file_id']);
      }
      final r = await widget.app.api!.brandMake({
        'brief': _brief.text.trim(), 'kind': _kind, 'sizes': _sets.toList(), 'photo': photo,
        'conversation_id': widget.app.conversationId ?? ''
      });
      if (!mounted) return;
      _snack(context, _s(r['say']));
      final v = _map(r['design']);
      _brief.clear();
      setState(() => _photo = null);
      await widget.onDone();
      if (mounted && v.isNotEmpty) {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => BrandDesignPage(app: widget.app, id: _s(v['id']))));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final kit = _map(widget.d['kit']);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      if (kit['ready'] != true)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Glass(child: Row(children: [
            const Icon(Icons.info_outline_rounded, color: C.accent),
            const SizedBox(width: 10),
            const Expanded(child: Text('Pehle "Brand kit" mein business ka naam aur logo daaliye: rang logo se apne aap ban jaayenge.')),
          ])),
        ),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Naya poster', style: display(17)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 4, children: [
            ChoiceChip(label: const Text('Apne aap'), selected: _kind.isEmpty, onSelected: (_) => setState(() => _kind = '')),
            for (final e in _kindsUi.entries)
              ChoiceChip(label: Text(e.value), selected: _kind == e.key, onSelected: (_) => setState(() => _kind = e.key)),
          ]),
          const SizedBox(height: 6),
          TextField(
            controller: _brief,
            minLines: 3,
            maxLines: 6,
            decoration: const InputDecoration(labelText: 'Kya dikhana hai (offer, daam, din, pata)', hintText: 'Diwali offer: 100 Mbps Rs 499, 15 Nov tak, free installation'),
          ),
          const SizedBox(height: 10),
          const Text('Size', style: TextStyle(color: C.muted, fontSize: 12.5)),
          Wrap(spacing: 6, runSpacing: 4, children: [
            for (final e in _setsUi.entries)
              FilterChip(label: Text(e.value), selected: _sets.contains(e.key), onSelected: (v) => setState(() => v ? _sets.add(e.key) : _sets.remove(e.key))),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: GlassButton(
                label: _photo == null ? 'Photo lagao (optional)' : _photo!.name,
                icon: Icons.add_photo_alternate_rounded,
                height: 42,
                onTap: () async {
                  final f = await pickAttachments(context, max: 1);
                  if (f.isNotEmpty) setState(() => _photo = f.first);
                },
              ),
            ),
            if (_photo != null) IconButton(onPressed: () => setState(() => _photo = null), icon: const Icon(Icons.close_rounded)),
          ]),
          const SizedBox(height: 12),
          _busy
              ? const Column(children: [LinearProgressIndicator(), SizedBox(height: 6), Text('Har size ka proof ban raha hai...', style: TextStyle(color: C.muted))])
              : GradientButton(label: 'Proof banao', icon: Icons.brush_rounded, height: 48, onTap: _make),
          const SizedBox(height: 6),
          Text('Proof par PROOF likha hota hai. Saaf final files tabhi banengi jab aap card par "Haan, final" dabayengi.',
              style: const TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- Designs
class _DesignsTab extends StatelessWidget {
  const _DesignsTab({required this.app, required this.designs, required this.onChanged});
  final Santosh app;
  final List<Map<String, dynamic>> designs;
  final Future<void> Function() onChanged;
  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: onChanged,
        child: designs.isEmpty
            ? ListView(children: const [Padding(padding: EdgeInsets.all(24), child: Text('Abhi koi design nahi. "Banao" mein pehla poster banaiye.', style: TextStyle(color: C.muted)))])
            : GridView.builder(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, mainAxisSpacing: 12, crossAxisSpacing: 12, mainAxisExtent: 250),
                itemCount: designs.length,
                itemBuilder: (_, i) {
                  final v = designs[i];
                  return Press(
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BrandDesignPage(app: app, id: _s(v['id'])))),
                    child: Glass(
                      padding: const EdgeInsets.all(8),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Expanded(child: Center(child: BrandImage(app: app, path: _s(v['thumb'])))),
                        const SizedBox(height: 6),
                        Text('${v['number']} · ${v['title']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
                        Row(children: [
                          Pill(_status[_s(v['status'])] ?? _s(v['status']), fg: _stCol(_s(v['status']))),
                          const Spacer(),
                          if (v['template'] == true) const Icon(Icons.bookmark_rounded, size: 16, color: C.accent),
                          Text('${(v['sizes'] as List?)?.length ?? 0} size', style: const TextStyle(color: C.faint, fontSize: 11.5)),
                        ]),
                      ]),
                    ),
                  );
                },
              ),
      );
}

// ---------------------------------------------------------------- one design
class BrandDesignPage extends StatefulWidget {
  const BrandDesignPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<BrandDesignPage> createState() => _BrandDesignPageState();
}

class _BrandDesignPageState extends State<BrandDesignPage> {
  Map<String, dynamic>? _v;
  String _busy = '';
  String _size = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await widget.app.api!.brandDesign(widget.id);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(String what, Future<Map<String, dynamic>> Function() fn) async {
    setState(() => _busy = what);
    try {
      final r = await fn();
      if (r['design'] is Map) setState(() => _v = Map<String, dynamic>.from(r['design'] as Map));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  Future<String?> _ask(String title, {String hint = '', int lines = 2}) async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, minLines: lines, maxLines: 6, autofocus: true, decoration: InputDecoration(hintText: hint)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Theek')),
        ],
      ),
    );
    return ok == true ? c.text.trim() : null;
  }

  Future<void> _ownWords() async {
    final ct = _map(_v!['content']);
    final ctl = {for (final k in ['headline', 'sub', 'offer', 'cta', 'date']) k: TextEditingController(text: _s(ct[k]))};
    const labels = {'headline': 'Headline', 'sub': 'Neeche ki line', 'offer': 'Offer / daam', 'cta': 'Button', 'date': 'Din / tareekh'};
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Apne shabd'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final e in ctl.entries) TextField(controller: e.value, decoration: InputDecoration(labelText: labels[e.key])),
          ]),
        ),
        actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Lagao'))],
      ),
    );
    if (ok != true) return;
    await _run('edit', () => widget.app.api!.brandAct(widget.id, 'edit', {'fields': {for (final e in ctl.entries) e.key: e.value.text.trim()}}));
  }

  Future<void> _sizes() async {
    final all = Map<String, dynamic>.from((await widget.app.api!.brandAll())['sizes'] as Map);
    if (!mounted) return;
    final cur = Set<String>.from((_v!['sizes'] as List).map((e) => '$e'));
    final pick = Set<String>.from(cur);
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (c) => StatefulBuilder(
        builder: (c, setS) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Kaun si size chahiye?', style: display(16)),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 4, children: [
                for (final e in all.entries)
                  FilterChip(
                    label: Text(_s(_map(e.value)['label'])),
                    selected: pick.contains(e.key),
                    onSelected: (v) => setS(() => v ? pick.add(e.key) : pick.remove(e.key)),
                  ),
              ]),
              const SizedBox(height: 12),
              GradientButton(label: 'Proof banao', height: 44, onTap: () => Navigator.pop(c, true)),
            ]),
          ),
        ),
      ),
    );
    if (ok != true || pick.isEmpty) return;
    await _run('resize', () => widget.app.api!.brandAct(widget.id, 'resize', {'sizes': pick.toList(), 'add': false}));
  }

  Future<void> _share(Map<String, dynamic> f, String sz, {bool gallery = false}) async {
    final ext = f.containsKey('png') ? 'png' : (f.containsKey('jpg') ? 'jpg' : 'pdf');
    final usePdf = !gallery && f.containsKey('pdf') && R.isPrint(sz);
    final key = usePdf ? 'pdf' : ext;
    final name = '${_v!['number']}_$sz.$key';
    await _run('share', () async {
      final path = await _fetch(widget.app, _s(f[key]), name);
      final err = gallery ? await Native.saveImage(path, name) : await Native.shareFile(path, mime: key == 'pdf' ? 'application/pdf' : 'image/$key', title: 'Poster bhejo');
      return {'say': err ?? (gallery ? 'Gallery mein save (Pictures/Hoola).' : '')};
    });
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(v == null ? 'Design' : '${v['number']} · ${v['title']}'), actions: [
        if (v != null)
          PopupMenuButton<String>(
            onSelected: (a) async {
              if (a == 'copy') await _run('copy', () => widget.app.api!.brandAct(widget.id, 'copy'));
              if (a == 'template') await _run('template', () => widget.app.api!.brandAct(widget.id, 'template', {'on': v['template'] != true}));
              if (a == 'delete') {
                await widget.app.api!.brandDelete(widget.id);
                if (context.mounted) Navigator.pop(context);
              }
            },
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'copy', child: Text('Copy banao')),
              PopupMenuItem(value: 'template', child: Text(v['template'] == true ? 'Template se hatao' : 'Template banao')),
              const PopupMenuItem(value: 'delete', child: Text('Hatao')),
            ],
          ),
      ]),
      body: Aurora(
        child: v == null
            ? const Center(child: CircularProgressIndicator())
            : _body(v),
      ),
    );
  }

  Widget _body(Map<String, dynamic> v) {
    final sizes = List<String>.from((v['sizes'] as List? ?? const []).map((e) => '$e'));
    final labels = _map(v['size_labels']);
    final sel = sizes.contains(_size) ? _size : (sizes.isNotEmpty ? sizes.first : '');
    final status = _s(v['status']);
    final finals = _map(v['finals']);
    final proofs = _map(v['proofs']);
    final checks = _list(v['checks']);
    final img = status == 'approved' && finals[sel] != null
        ? _s(_map(finals[sel])['png'] ?? _map(finals[sel])['jpg'])
        : _s(proofs[sel]);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 96), children: [
      Row(children: [
        Pill(_status[status] ?? status, fg: _stCol(status)),
        const SizedBox(width: 8),
        Text('v${v['version']} · ${v['kind_label']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
      ]),
      const SizedBox(height: 8),
      SizedBox(
        height: 38,
        child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final sz in sizes)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(label: Text(_s(labels[sz]).isEmpty ? sz : _s(labels[sz])), selected: sz == sel, onSelected: (_) => setState(() => _size = sz)),
            ),
        ]),
      ),
      const SizedBox(height: 8),
      GestureDetector(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => Scaffold(backgroundColor: Colors.black, appBar: AppBar(backgroundColor: Colors.black),
                body: InteractiveViewer(child: Center(child: BrandImage(app: widget.app, path: img)))))),
        child: Center(child: BrandImage(app: widget.app, path: img, height: 420)),
      ),
      if (_busy.isNotEmpty) const Padding(padding: EdgeInsets.all(10), child: LinearProgressIndicator()),
      if (checks.isNotEmpty) ...[
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Jaanch', style: display(15)),
            for (final c in checks)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Icon(c['level'] == 'block' ? Icons.block_rounded : (c['level'] == 'warn' ? Icons.warning_amber_rounded : Icons.info_outline_rounded),
                      size: 18, color: c['level'] == 'block' ? C.bad : (c['level'] == 'warn' ? C.warn : C.muted)),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_s(c['text']), style: const TextStyle(fontSize: 13))),
                ]),
              ),
          ]),
        ),
      ],
      const SizedBox(height: 12),
      if (status != 'approved') ...[
        Row(children: [
          Expanded(
            child: GlassButton(label: 'Badlav bolo', icon: Icons.edit_rounded, height: 42, onTap: _busy.isNotEmpty ? null : () async {
              final t = await _ask('Kya badlein?', hint: 'offer bada karo, background laal, "free" hatao');
              if (t != null && t.isNotEmpty) await _run('revise', () => widget.app.api!.brandAct(widget.id, 'revise', {'instruction': t}));
            }),
          ),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Khud likho', icon: Icons.text_fields_rounded, height: 42, onTap: _busy.isNotEmpty ? null : _ownWords)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: GlassButton(label: 'Size', icon: Icons.aspect_ratio_rounded, height: 42, onTap: _busy.isNotEmpty ? null : _sizes)),
          const SizedBox(width: 8),
          Expanded(
            child: GlassButton(label: 'Photo', icon: Icons.add_photo_alternate_rounded, height: 42, onTap: _busy.isNotEmpty ? null : () async {
              final f = await pickAttachments(context, max: 1);
              if (f.isEmpty) return;
              await _run('photo', () => widget.app.api!.brandPhoto(widget.id, f.first.name, f.first.bytes));
            }),
          ),
        ]),
        const SizedBox(height: 12),
        if (status == 'waiting')
          BrandApproveBox(app: widget.app, v: v, onDone: (nv) => setState(() => _v = nv))
        else
          GradientButton(
            label: 'Final haan ke liye bhejo',
            icon: Icons.verified_rounded,
            height: 48,
            onTap: _busy.isNotEmpty ? null : () => _run('approve', () => widget.app.api!.brandAct(widget.id, 'approve')),
          ),
      ] else ...[
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Final files', style: display(15)),
            for (final sz in sizes)
              if (finals[sz] != null)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(_s(labels[sz]).isEmpty ? sz : _s(labels[sz])),
                  subtitle: Text(_map(finals[sz]).keys.where((k) => ['png', 'jpg', 'pdf'].contains(k)).join(' + ').toUpperCase()),
                  trailing: Wrap(children: [
                    if (!R.isPrint(sz)) IconButton(tooltip: 'Gallery', icon: const Icon(Icons.download_rounded), onPressed: () => _share(_map(finals[sz]), sz, gallery: true)),
                    IconButton(tooltip: 'Bhejo', icon: const Icon(Icons.share_rounded), onPressed: () => _share(_map(finals[sz]), sz)),
                  ]),
                ),
          ]),
        ),
        const SizedBox(height: 8),
        GlassButton(label: 'Isme badlav (naya version)', icon: Icons.edit_rounded, height: 42, onTap: () async {
          final t = await _ask('Kya badlein?');
          if (t != null && t.isNotEmpty) await _run('revise', () => widget.app.api!.brandAct(widget.id, 'revise', {'instruction': t}));
        }),
      ],
    ]);
  }
}

/// Small helper: which sizes are print.
class R {
  static bool isPrint(String sz) => const {'a4', 'a3', 'a5', 'flex_6x3'}.contains(sz);
}

/// Her final approval: the exact version (hash) she sees. Mana asks why (it is learned).
class BrandApproveBox extends StatefulWidget {
  const BrandApproveBox({super.key, required this.app, required this.v, this.onDone});
  final Santosh app;
  final Map<String, dynamic> v;
  final void Function(Map<String, dynamic>)? onDone;
  @override
  State<BrandApproveBox> createState() => _BrandApproveBoxState();
}

class _BrandApproveBoxState extends State<BrandApproveBox> {
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    String reason = '';
    if (!yes) {
      final c = TextEditingController();
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Kya pasand nahi aaya?'),
          content: TextField(controller: c, decoration: const InputDecoration(hintText: 'rang, shabd, photo... (yaad rakha jayega)')),
          actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Mana karo'))],
        ),
      );
      if (ok != true) return;
      reason = c.text.trim();
    }
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.brandAct(_s(widget.v['id']), 'decide', {'yes': yes, 'hash': _s(widget.v['approve_hash']), 'reason': reason});
      if (mounted) _snack(context, _s(r['say']));
      if (r['design'] is Map) widget.onDone?.call(Map<String, dynamic>.from(r['design'] as Map));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Sab size dekh li? Haan dabate hi saaf final files (PNG / print PDF) banengi.', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        _busy
            ? const Column(children: [LinearProgressIndicator(), SizedBox(height: 6), Text('Final files ban rahi hain...', style: TextStyle(color: C.muted))])
            : Row(children: [
                Expanded(child: GlassButton(label: 'Mana', color: C.bad, height: 46, onTap: () => _decide(false))),
                const SizedBox(width: 8),
                Expanded(flex: 2, child: GradientButton(label: 'Haan, final', icon: Icons.check_rounded, height: 46, onTap: () => _decide(true))),
              ]),
      ]);
}

// ---------------------------------------------------------------- Brand kit
class _KitTab extends StatelessWidget {
  const _KitTab({required this.app, required this.kit, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> kit;
  final Future<void> Function() onChanged;

  Future<void> _save(BuildContext context, Map<String, dynamic> body) async {
    try {
      await app.api!.brandKitSave(body);
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  Future<String?> _ask(BuildContext context, String title, String value, {String hint = ''}) async {
    final c = TextEditingController(text: value);
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, autofocus: true, decoration: InputDecoration(hintText: hint)),
        actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
      ),
    );
    return ok == true ? c.text.trim() : null;
  }

  @override
  Widget build(BuildContext context) {
    final cols = _map(kit['colors']);
    final contact = _map(kit['contact']);
    final rules = List<String>.from((kit['rules'] as List? ?? const []).map((e) => '$e'));
    Widget row(String label, String value, Future<void> Function(String) onSave, {String hint = ''}) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: Text(value.isEmpty ? '-' : value),
          trailing: const Icon(Icons.edit_rounded, size: 18),
          onTap: () async {
            final v = await _ask(context, label, value, hint: hint);
            if (v != null) await onSave(v);
          },
        );
    return RefreshIndicator(
      onRefresh: onChanged,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Glass(
          child: Row(children: [
            Container(
              width: 84,
              height: 84,
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
              child: kit['logo'] == true && app.api != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.network('${app.api!.absolute('/api/brand/logo')}?t=${kit['palette']}', headers: app.api!.authHeaders, fit: BoxFit.contain))
                  : const Icon(Icons.image_outlined, color: Colors.black38, size: 36),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(kit['name']).isEmpty ? 'Business ka naam?' : _s(kit['name']), style: display(17)),
                const SizedBox(height: 6),
                GlassButton(label: kit['logo'] == true ? 'Logo badlo' : 'Logo daalo', icon: Icons.upload_rounded, height: 38, onTap: () async {
                  final f = await pickAttachments(context, max: 1);
                  if (f.isEmpty) return;
                  try {
                    final r = await app.api!.brandLogo(f.first.name, f.first.bytes);
                    if (context.mounted) _snack(context, _s(r['say']));
                  } catch (e) {
                    if (context.mounted) _snack(context, '$e');
                  }
                  await onChanged();
                }),
              ]),
            ),
          ]),
        ),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Rang', style: display(15)),
            const SizedBox(height: 8),
            Wrap(spacing: 10, runSpacing: 10, children: [
              for (final role in ['primary', 'secondary', 'accent', 'dark', 'light'])
                GestureDetector(
                  onTap: () async {
                    final v = await _ask(context, 'Rang ($role)', _s(cols[role]), hint: '#1565C0 ya laal / neela / hara');
                    if (v != null && v.isNotEmpty && context.mounted) await _save(context, {'colors': {role: v}});
                  },
                  child: Column(children: [
                    Container(width: 48, height: 48, decoration: BoxDecoration(color: _hex(_s(cols[role])), shape: BoxShape.circle, border: Border.all(color: C.line, width: 2))),
                    const SizedBox(height: 4),
                    Text({'primary': 'Mukhya', 'secondary': 'Doosra', 'accent': 'Button', 'dark': 'Gehra', 'light': 'Halka'}[role]!, style: const TextStyle(fontSize: 11.5, color: C.muted)),
                  ]),
                ),
            ]),
            if ((kit['palette'] as List?)?.isNotEmpty == true) ...[
              const SizedBox(height: 8),
              Text('Logo se mile: ${(kit['palette'] as List).join('  ')}', style: const TextStyle(color: C.faint, fontSize: 12)),
            ],
            const SizedBox(height: 8),
            Wrap(spacing: 6, children: [
              for (final f in _map(kit['fonts']).entries)
                ChoiceChip(label: Text(_s(f.value)), selected: kit['font'] == f.key, onSelected: (_) => _save(context, {'font': f.key})),
            ]),
          ]),
        ),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            row('Business ka naam', _s(kit['name']), (v) => _save(context, {'name': v})),
            row('Tagline', _s(kit['tagline']), (v) => _save(context, {'tagline': v})),
            row('Phone', _s(contact['phone']), (v) => _save(context, {'contact': {'phone': v}})),
            row('WhatsApp', _s(contact['whatsapp']), (v) => _save(context, {'contact': {'whatsapp': v}})),
            row('Website', _s(contact['website']), (v) => _save(context, {'contact': {'website': v}})),
            row('Instagram', _s(contact['instagram']), (v) => _save(context, {'contact': {'instagram': v}})),
            row('Pata (chhota)', _s(contact['address']), (v) => _save(context, {'contact': {'address': v}})),
            row('Rajya (tyohar ki tareekh ke liye)', _s(kit['state']), (v) => _save(context, {'state': v}), hint: 'Maharashtra'),
            row('Andaaz (tone)', _s(kit['tone']), (v) => _save(context, {'tone': v}), hint: 'garam, seedha, premium...'),
          ]),
        ),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('Mere niyam', style: display(15))),
              TextButton.icon(
                onPressed: () async {
                  final v = await _ask(context, 'Naya niyam', '', hint: 'Logo hamesha upar left; laal rang kabhi nahi');
                  if (v != null && v.isNotEmpty && context.mounted) await _save(context, {'rule': v});
                },
                icon: const Icon(Icons.add_rounded),
                label: const Text('Jodo'),
              ),
            ]),
            for (final r in rules)
              Row(children: [
                Expanded(child: Text('• $r', style: const TextStyle(fontSize: 13))),
                IconButton(icon: const Icon(Icons.close_rounded, size: 18), onPressed: () => _save(context, {'rules': [...rules]..remove(r)})),
              ]),
            const Divider(),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: kit['nudge'] == true,
              onChanged: (v) => _save(context, {'nudge': v}),
              title: const Text('Tyohar se pehle yaad dilao'),
              subtitle: Text('${kit['nudge_days'] ?? 7} din pehle poster ka sujhav'),
            ),
          ]),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Tyohar
class _FestTab extends StatelessWidget {
  const _FestTab({required this.app, required this.fests, required this.onDone});
  final Santosh app;
  final List<Map<String, dynamic>> fests;
  final Future<void> Function() onDone;
  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        if (fests.isEmpty) const Padding(padding: EdgeInsets.all(20), child: Text('Agle 60 din mein koi bada tyohar nahi mila.', style: TextStyle(color: C.muted))),
        for (final f in fests)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Glass(
              child: Row(children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                      gradient: LinearGradient(colors: [for (final c in (f['colors'] as List? ?? const ['#888888', '#AAAAAA'])) _hex('$c')]),
                      borderRadius: BorderRadius.circular(12)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(f['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text('${f['date']} · ${f['days_left']} din', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  ]),
                ),
                f['made'] == true
                    ? const Pill('Bana hai', fg: C.ok)
                    : GlassButton(label: 'Banao', height: 36, onTap: () => brandFestival(context, app, f, onDone)),
              ]),
            ),
          ),
      ]);
}

Future<void> brandFestival(BuildContext context, Santosh app, Map<String, dynamic> f, [Future<void> Function()? onDone]) async {
  final c = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text('${f['name']} ka poster'),
      content: TextField(controller: c, minLines: 2, maxLines: 4, decoration: const InputDecoration(hintText: 'Koi offer ya sandesh? (khali chhodo to sirf badhai)')),
      actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Proof banao'))],
    ),
  );
  if (ok != true) return;
  try {
    final r = await app.api!.brandMake({
      'brief': '${f['name']} ki badhai. ${c.text.trim()}', 'kind': 'festival', 'festival': f['name'], 'sizes': ['festival'],
      'conversation_id': app.conversationId ?? ''
    });
    if (context.mounted) _snack(context, _s(r['say']));
    await onDone?.call();
    final v = _map(r['design']);
    if (context.mounted && v.isNotEmpty) {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => BrandDesignPage(app: app, id: _s(v['id']))));
    }
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
  }
}

// ---------------------------------------------------------------- chat cards
class BrandDesignCard extends StatelessWidget {
  const BrandDesignCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final d = _map(v['design']);
    final status = _s(d['status']);
    final checks = _list(d['checks']).where((c) => c['level'] != 'info').toList();
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.palette_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${d['number']} · ${d['title']}', style: display(15), maxLines: 1, overflow: TextOverflow.ellipsis)),
          Pill(_status[status] ?? status, fg: _stCol(status)),
        ]),
        const SizedBox(height: 8),
        GestureDetector(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BrandDesignPage(app: app, id: _s(d['id'])))),
          child: Center(child: BrandImage(app: app, path: _s(d['thumb']), height: 260)),
        ),
        const SizedBox(height: 6),
        Text(_s(v['say']), style: const TextStyle(color: C.chip, fontSize: 13)),
        for (final c in checks.take(3))
          Text('${c['level'] == 'block' ? '⛔' : '⚠'} ${c['text']}', style: TextStyle(fontSize: 12, color: c['level'] == 'block' ? C.bad : C.warn)),
        const SizedBox(height: 8),
        if (status == 'waiting' && _s(d['approve_hash']).isNotEmpty)
          BrandApproveBox(app: app, v: d)
        else
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BrandDesignPage(app: app, id: _s(d['id'])))),
              child: Text(status == 'approved' ? 'Final files' : 'Sab size dekho / badlo'),
            ),
          ),
      ]),
    );
  }
}

class BrandIdeaCard extends StatelessWidget {
  const BrandIdeaCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final f = _map(v['festival']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.celebration_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(f['name']), style: display(15))),
        ]),
        const SizedBox(height: 6),
        Text(_s(v['say']), style: const TextStyle(color: C.chip, fontSize: 13)),
        const SizedBox(height: 8),
        Align(alignment: Alignment.centerRight, child: GlassButton(label: 'Poster banao', height: 38, onTap: () => brandFestival(context, app, f))),
      ]),
    );
  }
}
