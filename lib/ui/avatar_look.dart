/// Hoola avatar looks: the original Santosh, or one of 100 female (v0.51) / 100 male (v0.52) 3D looks from around the world.
///
/// Images are pre-rendered from the same three.js builder the live 3D view uses (assets/santosh3d/avatar.js),
/// so the picture in a list, the face in a header and the 3D avatar in a call are the same person.
/// `currentLook` is the owner's look ('' = Santosh); widgets that show the avatar listen to it.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;

import 'glass.dart';

final ValueNotifier<String> currentLook = ValueNotifier<String>('');

final RegExp _lookRe = RegExp(r'^[fm]\d{3}$');
bool isLook(String? id) => id != null && _lookRe.hasMatch(id);
/// A look that belongs to this gender ('f' / 'm').
bool lookFits(String? id, String gender) => isLook(id) && id![0] == gender;
/// Full figure; '' = Santosh.
String lookFull(String id) => isLook(id) ? 'assets/avatars/$id.webp' : 'assets/images/santosh_happy.png';
String lookHead(String id) => 'assets/avatars/${id}_head.webp';

/// Head image for any avatar: a female look id, else Santosh.
String headAsset(String? look) => isLook(look) ? lookHead(look!) : 'assets/images/santosh_head.png';

class LookInfo {
  const LookInfo(this.id, this.name, this.city, this.country, this.region, this.hair, this.outfit, this.gender);
  final String id, name, city, country, region, hair, outfit, gender;
  factory LookInfo.from(Map<String, dynamic> m) => LookInfo('${m['id']}', '${m['name']}', '${m['city']}', '${m['country']}',
      '${m['region']}', '${m['hair'] ?? ''}', '${m['outfit'] ?? ''}', '${m['gender'] ?? (('${m['id']}').startsWith('m') ? 'm' : 'f')}');
  static const santosh = LookInfo('', 'Santosh', 'Hoola ka asli', 'roop', '', '', '', 'm');
}

List<LookInfo>? _looks;
Future<List<LookInfo>> loadLooks() async {
  if (_looks != null) return _looks!;
  final raw = jsonDecode(await rootBundle.loadString('assets/avatars/looks.json')) as List;
  return _looks = raw.map((e) => LookInfo.from(Map<String, dynamic>.from(e as Map))).toList();
}

const lookRegions = <String, String>{
  '': 'Sab',
  'sa': 'Bharat aur Dakshin Asia',
  'ea': 'Purvi Asia',
  'sea': 'Dakshin-Purv Asia',
  'me': 'Madhya Purv aur Madhya Asia',
  'af': 'Africa',
  'eu': 'Europe',
  'am': 'America',
  'oc': 'Oceania',
};

/// Round face of an avatar (any look). [look] null = the owner's current look.
class AvatarFace extends StatelessWidget {
  const AvatarFace({super.key, this.look, this.size = 40, this.ring = false});
  final String? look;
  final double size;
  final bool ring;
  @override
  Widget build(BuildContext context) {
    Widget face(String l) => ClipOval(
          child: Container(
            width: size,
            height: size,
            color: isLook(l) ? const Color(0xFFEDE7F6) : const Color(0xFF2A1F5E),
            child: Image.asset(headAsset(l), fit: BoxFit.cover, filterQuality: FilterQuality.medium,
                errorBuilder: (_, __, ___) => Image.asset('assets/images/santosh_head.png', fit: BoxFit.cover)),
          ),
        );
    final child = look != null ? face(look!) : ValueListenableBuilder<String>(valueListenable: currentLook, builder: (_, l, __) => face(l));
    if (!ring) return child;
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: const BoxDecoration(
          shape: BoxShape.circle, gradient: SweepGradient(colors: [Color(0xFFFFB15C), Color(0xFFC055F5), Color(0xFF7C5CFF), Color(0xFFFFB15C)])),
      child: child,
    );
  }
}

/// Full screen chooser: 100 looks of the avatar's gender (men also get the original Santosh), filter by region,
/// big preview of the one in hand. Pops with the chosen id ('' = Santosh).
class LookPickerScreen extends StatefulWidget {
  const LookPickerScreen({super.key, required this.initial, required this.avatarName, this.gender = 'f'});
  final String initial;
  final String avatarName;
  final String gender;
  @override
  State<LookPickerScreen> createState() => _LookPickerScreenState();
}

class _LookPickerScreenState extends State<LookPickerScreen> {
  late String _sel = lookFits(widget.initial, widget.gender) ? widget.initial : (widget.gender == 'm' ? '' : 'f001');
  String _region = '';
  List<LookInfo> _all = const [];

  @override
  void initState() {
    super.initState();
    loadLooks().then((l) {
      final mine = l.where((x) => x.gender == widget.gender).toList();
      if (mounted) setState(() => _all = widget.gender == 'm' ? [LookInfo.santosh, ...mine] : mine);
    });
  }

  LookInfo? get _cur {
    for (final l in _all) {
      if (l.id == _sel) return l;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final shown = _region.isEmpty ? _all : _all.where((l) => l.region == _region).toList();
    final mine = _all.where((l) => l.id.isNotEmpty).length;
    final cur = _cur;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${widget.avatarName} ka roop')),
      body: Aurora(
        child: SafeArea(
          child: Column(children: [
            // preview of the look in hand
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
              child: Glass(
                child: Row(children: [
                  SizedBox(
                    width: 104,
                    height: 150,
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 260),
                      switchInCurve: Curves.easeOutCubic,
                      transitionBuilder: (c, a) => FadeTransition(opacity: a, child: ScaleTransition(scale: Tween(begin: .96, end: 1.0).animate(a), child: c)),
                      child: Image.asset(lookFull(_sel), key: ValueKey(_sel), fit: BoxFit.contain),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(widget.avatarName, style: display(22)),
                      const SizedBox(height: 2),
                      if (cur != null)
                        Text(cur.id.isEmpty ? 'Roop: asli Santosh' : 'Roop: ${cur.name} · ${cur.city}, ${cur.country}', style: const TextStyle(color: C.muted, fontSize: 13)),
                      const SizedBox(height: 8),
                      const Text('Naam aapka diya hua hi rahega. Roop sirf dikhne ke liye hai: call mein, chat mein aur doosron ke Hoola par.',
                          style: TextStyle(color: C.faint, fontSize: 12)),
                    ]),
                  ),
                ]),
              ),
            ),
            SizedBox(
              height: 44,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
                for (final e in lookRegions.entries)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: ChoiceChip(
                      label: Text(e.key.isEmpty ? '${e.value} $mine' : '${e.value} · ${_all.where((l) => l.region == e.key).length}'),
                      selected: _region == e.key,
                      showCheckmark: false,
                      selectedColor: C.accent,
                      labelStyle: TextStyle(color: _region == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                      onSelected: (_) => setState(() => _region = e.key),
                    ),
                  ),
              ]),
            ),
            Expanded(
              child: _all.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : GridView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                          maxCrossAxisExtent: 128, mainAxisExtent: 196, crossAxisSpacing: 8, mainAxisSpacing: 8),
                      itemCount: shown.length,
                      itemBuilder: (_, i) => _tile(shown[i]),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: GradientButton(
                label: cur == null ? 'Yeh roop chuniye' : 'Yeh roop chuniye · ${cur.id.isEmpty ? 'Santosh' : cur.name}',
                icon: Icons.check_rounded,
                onTap: () => Navigator.of(context).pop(_sel),
              ),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _tile(LookInfo l) {
    final on = l.id == _sel;
    return Semantics(
      button: true,
      selected: on,
      label: '${l.name}, ${l.city}',
      child: GestureDetector(
        onTap: () => setState(() => _sel = l.id),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          decoration: BoxDecoration(
            color: on ? const Color(0x33FFB15C) : C.panel,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: on ? C.accent : C.line, width: on ? 2 : 1),
          ),
          padding: const EdgeInsets.fromLTRB(6, 8, 6, 6),
          child: Column(children: [
            Expanded(child: Image.asset(lookFull(l.id), fit: BoxFit.contain, cacheWidth: 220, filterQuality: FilterQuality.medium)),
            const SizedBox(height: 4),
            Text(l.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
            Text(l.city, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 10.5)),
          ]),
        ),
      ),
    );
  }
}
