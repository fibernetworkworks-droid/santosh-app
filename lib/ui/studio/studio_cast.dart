import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_approve.dart';
import 'studio_kit.dart';

/// v0.159 Screen 7 · Cast: the people, places and products that must look the same in every shot. From her own photo
/// (a real person only with their permission) or painted by AI (Nano Banana Pro, a price card).
class CastTab extends StatefulWidget {
  const CastTab({super.key, required this.app, required this.v, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> v;
  final Future<void> Function() onChanged;
  @override
  State<CastTab> createState() => _CastTabState();
}

class _CastTabState extends State<CastTab> {
  bool _busy = false;

  Santosh get app => widget.app;
  String get name => '${widget.v['project']}';

  Future<void> _add({required bool photo, String kind = 'person', Map<String, dynamic>? replace}) async {
    XFile? x;
    List<int>? bytes;
    if (photo) {
      x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 90, maxWidth: 2000);
      if (x == null) return;
      bytes = await x.readAsBytes();
      if (!mounted) return;
    }
    final n = TextEditingController(text: '${replace?['name'] ?? ''}');
    final d = TextEditingController(text: '${replace?['description'] ?? ''}');
    var k = '${replace?['kind'] ?? kind}';
    var voice = 'female';
    var consent = replace != null;
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: SC.card,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => Padding(
          padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + MediaQuery.of(ctx).viewInsets.bottom),
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(photo ? 'Photo se jodiye' : 'AI se banaiye', style: sora(18)),
              const SizedBox(height: 14),
              if (replace == null)
                Wrap(spacing: 8, children: [
                  for (final e in const {'person': 'Insaan', 'product': 'Product / logo', 'place': 'Jagah'}.entries)
                    SChip(label: e.value, on: k == e.key, onTap: () => set(() => k = e.key)),
                ]),
              const SizedBox(height: 12),
              _field(n, k == 'person' ? 'Naam (jaise Meera)' : k == 'product' ? 'Naam (jaise Chai packet)' : 'Naam (jaise Nadi kinara)',
                  enabled: replace == null, onChanged: (_) => set(() {})),
              const SizedBox(height: 10),
              _field(d, k == 'person' ? 'Kaisa dikhta hai: umar, kapde, baal, rang' : k == 'product' ? 'Kaisa hai: rang, packet, naam' : 'Kaisi jagah: ped, nadi, imaarat, mausam',
                  lines: 2, onChanged: (_) => set(() {})),
              if (k == 'person') ...[
                const SizedBox(height: 12),
                Wrap(spacing: 8, children: [
                  SChip(label: 'Mahila awaaz', on: voice == 'female', onTap: () => set(() => voice = 'female')),
                  SChip(label: 'Purush awaaz', on: voice == 'male', onTap: () => set(() => voice = 'male')),
                ]),
                if (photo)
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: consent,
                    activeColor: C.accent,
                    onChanged: (x) => set(() => consent = x == true),
                    title: Text('Is insaan ne video ke liye ijazat di hai', style: body(13.5)),
                  ),
              ],
              const SizedBox(height: 14),
              SButton(
                label: photo ? 'Jodo' : 'Aage: daam dekho',
                onTap: n.text.trim().isEmpty || (!photo && d.text.trim().length < 4) || (photo && k == 'person' && !consent)
                    ? null
                    : () => Navigator.pop(ctx, true),
              ),
              const SizedBox(height: 8),
              Text('Asli insaan ka chehra sirf unki ijazat se. Neta, celebrity ya kisi brand ki nakal nahi banegi.',
                  style: body(11.5, color: C.faint, height: 1.4)),
            ]),
          ),
        ),
      ),
    );
    if (ok != true || !mounted) return;
    final body0 = {'name': n.text.trim(), 'description': d.text.trim(), 'consent': k != 'person' || consent, 'voice': voice, 'kind': k};
    if (photo) {
      setState(() => _busy = true);
      try {
        final f = await app.api!.chatFile(app.conversationId ?? '', x!.name.isEmpty ? 'photo.jpg' : x.name, bytes!);
        await app.api!.studioCharacter(name, {...body0, 'file_ids': ['${f['file_id']}']});
        if (mounted) studioSnack(context, '${n.text.trim()} jud gaya: har shot mein yahi dikhega');
      } catch (e) {
        if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
      }
      if (mounted) setState(() => _busy = false);
      await widget.onChanged();
      return;
    }
    final done = await approveSimple(context, app,
        title: '${n.text.trim()} ki tasveer',
        sub: '$name · Nano Banana Pro',
        rows: [PriceRow(Icons.auto_awesome_rounded, SC.violet, 'Ek reference tasveer', d.text.trim(), 12)],
        inr: 12,
        month: sMap(widget.v['month']),
        ask: () => app.api!.studioCharacter(name, body0));
    if (done && mounted) studioSnack(context, 'Tasveer ban rahi hai (lagbhag 30 sec)');
    await widget.onChanged();
  }

  Widget _field(TextEditingController c, String hint, {int lines = 1, bool enabled = true, ValueChanged<String>? onChanged}) =>
      TextField(
        controller: c,
        enabled: enabled,
        onChanged: onChanged,
        minLines: lines,
        maxLines: lines + 2,
        style: body(14.5, w: FontWeight.w500),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: body(13.5, w: FontWeight.w500, color: C.faint),
          filled: true,
          fillColor: SC.field,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final all = sList(widget.v['character_list']);
    final people = all.where((c) => c['kind'] == 'person').toList();
    final places = all.where((c) => c['kind'] == 'place').toList();
    final products = all.where((c) => c['kind'] == 'product').toList();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (_busy) const Padding(padding: EdgeInsets.only(bottom: 10), child: LinearProgressIndicator(color: C.accent, minHeight: 2)),
        SHead('Log', trailing: '${people.length}'),
        for (final c in people) ...[_person(c), const SizedBox(height: 10)],
        if (people.isEmpty) _empty('Koi insaan jo har shot mein ek jaisa dikhe? Photo daaliye ya AI se banwaiye.'),
        const SizedBox(height: 18),
        const SHead('Jagah'),
        _strip(places, 'place'),
        const SizedBox(height: 18),
        const SHead('Product aur logo'),
        _strip(products, 'product'),
        const SizedBox(height: 18),
        const SHead('Naya character'),
        Row(children: [
          Expanded(child: _newTile(Icons.photo_camera_rounded, 'Asli photo se', 'us insaan ki ijazat ke saath', () => _add(photo: true))),
          const SizedBox(width: 10),
          Expanded(child: _newTile(Icons.auto_awesome_rounded, 'AI se banao', 'likhkar · ₹12 tasveer',
              widget.v['can_paint'] == true ? () => _add(photo: false) : null)),
        ]),
        const SizedBox(height: 10),
        Text('Kisi asli insaan ka chehra sirf unki ijazat se. Neta, celebrity ya kisi brand ki nakal nahi banegi.',
            style: body(11.5, color: C.faint, height: 1.45)),
      ]),
    );
  }

  Widget _empty(String t) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), border: Border.all(color: Colors.white24)),
        child: Text(t, style: body(13, color: C.muted, height: 1.4)),
      );

  Widget _person(Map<String, dynamic> c) {
    final imgs = List<String>.from(((c['images'] as List?) ?? const []).map((e) => '$e'));
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(22), border: Border.all(color: SC.line)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        SizedBox(
          height: 150,
          child: Row(children: [
            Expanded(flex: 14, child: SImage(app: app, url: imgs.isEmpty ? '' : imgs[0], radius: 14, icon: Icons.person_rounded)),
            if (imgs.length > 1) ...[
              const SizedBox(width: 8),
              Expanded(
                flex: 10,
                child: Column(children: [
                  Expanded(child: SImage(app: app, url: imgs[1], radius: 12)),
                  if (imgs.length > 2) ...[const SizedBox(height: 8), Expanded(child: SImage(app: app, url: imgs[2], radius: 12))],
                ]),
              ),
            ],
          ]),
        ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: Text('${c['name']}', style: sora(16))),
          Tag(c['generated'] == true ? 'AI se bana' : 'Asli photo', fg: c['generated'] == true ? SC.violet : C.ok),
        ]),
        if ('${c['description'] ?? ''}'.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text('${c['description']}', style: body(12.5, color: C.muted, height: 1.45)),
        ],
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          _chip(Icons.mic_rounded, '${c['voice'] ?? ''}'.isEmpty ? 'Hoola ki awaaz' : 'Awaaz: ${c['voice']}'),
          _chip(Icons.movie_rounded, '${c['shots'] ?? 0} shots mein'),
        ]),
        const SizedBox(height: 10),
        SButton(label: 'Photo badlo', primary: false, height: 44, onTap: _busy ? null : () => _add(photo: true, replace: c)),
      ]),
    );
  }

  Widget _chip(IconData icon, String t) => Container(
        height: 32,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(color: SC.card2, borderRadius: BorderRadius.circular(999)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 14, color: C.chip),
          const SizedBox(width: 6),
          Text(t, style: body(12, w: FontWeight.w700)),
        ]),
      );

  Widget _strip(List<Map<String, dynamic>> items, String kind) => SizedBox(
        height: 116,
        child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final c in items) ...[
            SizedBox(
              width: 120,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(height: 84, width: 120, child: SImage(app: app, url: '${c['image'] ?? ''}', radius: 14,
                    icon: kind == 'place' ? Icons.landscape_rounded : Icons.inventory_2_rounded)),
                const SizedBox(height: 6),
                Text('${c['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: body(12.5, w: FontWeight.w700)),
              ]),
            ),
            const SizedBox(width: 10),
          ],
          Press(
            onTap: _busy ? null : () => _add(photo: true, kind: kind),
            child: Container(
              width: 120,
              height: 84,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.white24, width: 1.5)),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Icon(Icons.add_rounded, color: C.muted),
                const SizedBox(height: 4),
                Text(kind == 'place' ? 'Jagah jodiye' : 'Product photo', style: body(12, w: FontWeight.w700, color: C.muted)),
              ]),
            ),
          ),
        ]),
      );

  Widget _newTile(IconData icon, String title, String sub, VoidCallback? onTap) => Opacity(
        opacity: onTap == null ? .45 : 1,
        child: Press(
          onTap: onTap,
          child: Container(
            height: 96,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(16), border: Border.all(color: SC.line2)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(icon, size: 20, color: C.ink),
              const SizedBox(height: 6),
              Text(title, style: body(13, w: FontWeight.w800)),
              Text(sub, style: body(11, color: C.faint)),
            ]),
          ),
        ),
      );
}
