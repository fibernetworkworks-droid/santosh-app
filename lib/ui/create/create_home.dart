// v0.912 CREATE NATIVE: the Create home (board 1 of claude.ai/artifact/SARfWkfWm8ZtmmnAcU8dYn). "What shall we create
// today?", the five modes (each changes the hint, the settings line and the price), the ask box that opens the right
// tool with her words already in it, the ten studio tools on black circles, her recent creations, starters, and the
// way to her films, brand kit, creations and the how-to guides. One CreateStore lives here for the whole visit.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import '../shell/hoola_settings.dart' show hoolaOpenNew;
import 'create_film.dart';
import 'create_keep.dart';
import 'create_kit.dart';
import 'create_make.dart';

/// Opens a Create screen in the new design, sharing [store].
Future<void> crOpen(BuildContext context, CreateStore store, Widget screen) => hoolaOpenNew(context, store.app, screen);

typedef _Mode = ({String name, CrGlyph glyph, String hint, String line, String price});

const List<_Mode> _modes = [
  (name: 'Film', glyph: CrGlyph.film, hint: 'A 30-second Diwali ad for my sweet shop, a family at the counter, ends on our logo…',
      line: '16:9 · 30 s · Hindi', price: 'Storyboard free'),
  (name: 'Picture', glyph: CrGlyph.image, hint: 'A festive poster of a clay kulhad of chai, steam rising, diyas, a headline in Hindi…',
      line: '1:1 · 1 picture', price: 'About ₹3'),
  (name: 'Video clip', glyph: CrGlyph.video, hint: 'Steam rising from a kulhad of chai on a rainy Mumbai balcony, slow dolly in…',
      line: '9:16 · 8 s', price: 'Price first'),
  (name: 'Song', glyph: CrGlyph.music, hint: 'A happy Bollywood-style jingle for my sweet shop, dhol and shehnai, 30 seconds…',
      line: 'Hindi', price: 'About ₹7'),
  (name: 'Voice-over', glyph: CrGlyph.voice, hint: 'Is Diwali, Sharma Sweets laaye hain taaza kaju katli. Aaj hi aaiye!',
      line: 'Your Hoola’s voice · Hindi', price: 'A few paise'),
];

typedef _Tool = ({String name, String line, CrGlyph glyph, String tag});

const List<_Tool> _tools = [
  (name: 'Director', line: 'A whole film from one line', glyph: CrGlyph.film, tag: 'Popular'),
  (name: 'Image', line: 'Posters, photos, product shots', glyph: CrGlyph.image, tag: ''),
  (name: 'Video', line: 'One clip, price before it starts', glyph: CrGlyph.video, tag: ''),
  (name: 'Music', line: 'Songs, jingles and scores', glyph: CrGlyph.music, tag: ''),
  (name: 'Voice-over', line: 'Any script, 11 languages', glyph: CrGlyph.voice, tag: ''),
  (name: 'Dubbing', line: 'Your video in more languages', glyph: CrGlyph.dub, tag: ''),
  (name: 'Video editor', line: 'Edit your clips with words', glyph: CrGlyph.cut, tag: ''),
  (name: 'Script writer', line: 'Ads, shorts and episodes', glyph: CrGlyph.pen, tag: ''),
  (name: 'AI casting', line: 'One face in every scene', glyph: CrGlyph.cast, tag: ''),
  (name: 'Hoola Cinema', line: 'Restyle, swap, talking photo', glyph: CrGlyph.cinema, tag: 'New'),
];

/// The starters (the console's own): a name, the tool, the words she starts from.
const List<(String, String, String)> crStarters = [
  ('Diwali sale reel', 'Video', 'A 15-second Diwali sale reel for my shop, diyas and fairy lights, warm gold light'),
  ('Chai brand poster', 'Image', 'A premium poster of a clay kulhad of masala chai on a wooden table, steam rising, warm morning light, space for a headline'),
  ('Founder intro voice-over', 'Voice-over', 'Namaste! Main hoon aapki team ki founder. Hum chhote business ke liye AI banate hain.'),
  ('Temple at dawn', 'Image', 'A South Indian temple gopuram at dawn, mist, golden rim light, birds in the sky, ultra detailed'),
  ('Lo-fi study beat', 'Music', 'A calm lo-fi study beat with soft keys, rain sounds and a slow tabla groove'),
  ('Ad film for my product', 'Director', 'A 30-second ad film for my product: hook in 2 seconds, the product in use, happy customers, ends on the logo.'),
];

class HoolaCreate extends StatefulWidget {
  const HoolaCreate({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaCreate> createState() => _HoolaCreateState();
}

class _HoolaCreateState extends State<HoolaCreate> {
  late final CreateStore _store = CreateStore(widget.app);
  final _ask = TextEditingController();
  int _mode = 0;

  @override
  void initState() {
    super.initState();
    _store.load();
  }

  @override
  void dispose() {
    _store.dispose();
    _ask.dispose();
    super.dispose();
  }

  Widget _screenFor(String tool, String words) => switch (tool) {
        'Director' => CreateDirector(store: _store, brief: words),
        'Image' => CreateImage(store: _store, prompt: words),
        'Video' => CreateVideo(store: _store, prompt: words),
        'Music' => CreateMusic(store: _store, brief: words),
        'Voice-over' => CreateVoice(store: _store, text: words),
        'Dubbing' => CreateDub(store: _store),
        'Video editor' => CreateEditor(store: _store, brief: words),
        'Script writer' => CreateScript(store: _store, brief: words),
        'AI casting' => CreateCasting(store: _store),
        'Hoola Cinema' => CreateCinema(store: _store),
        'My creations' => CreateLibrary(store: _store),
        'Brand kit' => CreateBrand(store: _store),
        'Film projects' => CreateDirector(store: _store),
        _ => CreateGuides(store: _store, open: (t) => crOpen(context, _store, _screenFor(t, ''))),
      };

  void _go(String tool, [String words = '']) => crOpen(context, _store, _screenFor(tool, words));

  void _send() {
    final words = _ask.text.trim();
    final m = _modes[_mode];
    final tool = switch (m.name) {
      'Film' => 'Director',
      'Picture' => 'Image',
      'Video clip' => 'Video',
      'Song' => 'Music',
      _ => 'Voice-over',
    };
    _go(tool, words);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ListenableBuilder(
      listenable: _store,
      builder: (context, _) => CrPage(
        title: 'Create',
        trailing: CrRoundButton(glyph: CrGlyph.grid, label: 'My creations', onTap: () => _go('My creations')),
        onRefresh: () => _store.load(quiet: true),
        children: [
          const SizedBox(height: 8),
          Semantics(
            header: true,
            child: Text('What shall we create today?',
                style: TextStyle(fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 30, height: 1.2, color: c.ink)),
          ),
          const SizedBox(height: 6),
          Text('Pictures, films, songs and voices. Every paid step shows its price first.',
              style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14.5)),
          const SizedBox(height: 18),
          _ModePills(picked: _mode, onPick: (i) => setState(() => _mode = i)),
          const SizedBox(height: 12),
          _Compose(mode: _modes[_mode], controller: _ask, onSend: _send),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final q in const ['Diwali offer', 'Product launch', 'Festival greeting', 'Shop opening'])
              CrChip(label: q, on: false, onTap: () => setState(() => _ask.text = '${q == 'Shop opening' ? 'Our new shop opening' : q} for my business, warm and festive')),
          ]),
          if (_store.error.isNotEmpty) ...[const SizedBox(height: 14), CrNote(_store.error, glyph: CrGlyph.info)],
          crGap,
          const CrLabel('Studio tools', note: 'Tap one to start'),
          _ToolGrid(onTap: (t) => _go(t)),
          crGap,
          _Recent(store: _store, onAll: () => _go('My creations')),
          const CrLabel('Start from an idea', note: 'Change the words, then create'),
          SizedBox(
            height: 150,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: crStarters.length,
              separatorBuilder: (_, __) => const SizedBox(width: 10),
              itemBuilder: (_, i) => _Starter(s: crStarters[i], onTap: () => _go(crStarters[i].$2, crStarters[i].$3)),
            ),
          ),
          crGap,
          CrCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(children: [
              _Thing(glyph: CrGlyph.folder, title: 'Film projects', sub: '${_store.films.length} ${_store.films.length == 1 ? 'film' : 'films'}',
                  onTap: () => _go('Film projects')),
              Divider(height: 1, color: c.line),
              _Thing(glyph: CrGlyph.brand, title: 'Brand kit', sub: crS(_store.kit['name']).isEmpty ? 'Your logo, colours and words' : crS(_store.kit['name']),
                  onTap: () => _go('Brand kit')),
              Divider(height: 1, color: c.line),
              _Thing(glyph: CrGlyph.grid, title: 'My creations', sub: '${_store.items.length} kept', onTap: () => _go('My creations')),
              Divider(height: 1, color: c.line),
              _Thing(glyph: CrGlyph.book, title: 'How-to guides', sub: 'Short steps for each tool', onTap: () => _go('Guides')),
            ]),
          ),
        ],
      ),
    );
  }
}

class _ModePills extends StatelessWidget {
  const _ModePills({required this.picked, required this.onPick});
  final int picked;
  final ValueChanged<int> onPick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Wrap(spacing: 8, runSpacing: 8, children: [
      for (var i = 0; i < _modes.length; i++)
        Semantics(
          button: true,
          selected: i == picked,
          label: _modes[i].name,
          excludeSemantics: true,
          onTap: () => onPick(i),
          child: Material(
            color: i == picked ? c.pill : c.surface,
            shape: StadiumBorder(side: BorderSide(color: i == picked ? c.pill : c.line)),
            child: InkWell(
              customBorder: const StadiumBorder(),
              onTap: () {
                HapticFeedback.selectionClick();
                onPick(i);
              },
              child: Container(
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  CrIcon(_modes[i].glyph, size: 16, color: i == picked ? c.onPill : c.ink2),
                  const SizedBox(width: 7),
                  Text(_modes[i].name,
                      style: HoolaType.body(c).copyWith(fontSize: 14, fontWeight: FontWeight.w500, color: i == picked ? c.onPill : c.ink2)),
                ]),
              ),
            ),
          ),
        ),
    ]);
  }
}

class _Compose extends StatelessWidget {
  const _Compose({required this.mode, required this.controller, required this.onSend});
  final _Mode mode;
  final TextEditingController controller;
  final VoidCallback onSend;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        TextField(
          controller: controller,
          minLines: 3,
          maxLines: 7,
          textInputAction: TextInputAction.newline,
          style: HoolaType.bodyLarge(c).copyWith(fontSize: 15.5, height: 1.5),
          decoration: InputDecoration(
            hintText: mode.hint,
            hintMaxLines: 3,
            hintStyle: HoolaType.bodyLarge(c).copyWith(color: c.ink3, fontSize: 15.5, height: 1.5),
            border: InputBorder.none,
            filled: false,
            isDense: true,
            contentPadding: EdgeInsets.zero,
          ),
        ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(mode.line, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink2)),
              const SizedBox(height: 2),
              Text(mode.price, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
            ]),
          ),
          Semantics(
            button: true,
            label: 'Start ${mode.name.toLowerCase()}',
            excludeSemantics: true,
            onTap: onSend,
            child: Material(
              color: c.pill,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: () {
                  HapticFeedback.lightImpact();
                  onSend();
                },
                child: SizedBox(
                  width: 48,
                  height: 48,
                  child: Center(child: Transform.rotate(angle: -1.5708, child: CrIcon(CrGlyph.chevron, size: 20, color: c.onPill))),
                ),
              ),
            ),
          ),
        ]),
      ]),
    );
  }
}

class _ToolGrid extends StatelessWidget {
  const _ToolGrid({required this.onTap});
  final ValueChanged<String> onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return LayoutBuilder(builder: (context, box) {
      final w = (box.maxWidth - 12) / 2;
      return Wrap(spacing: 12, runSpacing: 12, children: [
        for (final t in _tools)
          SizedBox(
            width: w,
            child: Semantics(
              button: true,
              label: '${t.name}. ${t.line}',
              excludeSemantics: true,
              onTap: () => onTap(t.name),
              child: CrCard(
                onTap: () => onTap(t.name),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 112),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      CrDisc(t.glyph),
                      const Spacer(),
                      if (t.tag.isNotEmpty)
                        Flexible(
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(10)),
                            child: Text(t.tag, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.label(c)),
                          ),
                        ),
                    ]),
                    const SizedBox(height: 12),
                    Text(t.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c).copyWith(fontSize: 14.5)),
                    const SizedBox(height: 2),
                    Text(t.line, maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
                  ]),
                ),
              ),
            ),
          ),
      ]);
    });
  }
}

class _Recent extends StatelessWidget {
  const _Recent({required this.store, required this.onAll});
  final CreateStore store;
  final VoidCallback onAll;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final items = store.items.take(10).toList();
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: Semantics(header: true, child: Text('Recent', style: HoolaType.title(c).copyWith(fontSize: 14)))),
        TextButton(onPressed: onAll, child: const Text('See all')),
      ]),
      SizedBox(
        height: 196,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(width: 10),
          itemBuilder: (_, i) {
            final it = items[i];
            return Semantics(
              button: true,
              label: '${crKindName(crS(it['kind']))}: ${crS(it['title'])}',
              excludeSemantics: true,
              onTap: () => crOpenItem(context, store, it),
              child: GestureDetector(
                onTap: () => crOpenItem(context, store, it),
                child: SizedBox(
                  width: 112,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: SizedBox(
                        width: 112,
                        height: 128,
                        child: Stack(fit: StackFit.expand, children: [
                          CrItemImage(app: store.app, item: it, cache: 336),
                          if (!crS(it['mime']).startsWith('image/'))
                            Center(child: CrIcon(_kindGlyph(crS(it['kind'])), size: 26, color: c.ink2)),
                        ]),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(crS(it['title']), maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.small(c).copyWith(color: c.ink, fontWeight: FontWeight.w500)),
                    Text(crKindName(crS(it['kind'])), style: HoolaType.small(c).copyWith(fontSize: 12)),
                  ]),
                ),
              ),
            );
          },
        ),
      ),
      crGap,
    ]);
  }
}

CrGlyph _kindGlyph(String kind) => switch (kind) {
      'song' => CrGlyph.music,
      'voice' => CrGlyph.voice,
      'dub' => CrGlyph.dub,
      'script' => CrGlyph.pen,
      'cast' => CrGlyph.cast,
      _ => CrGlyph.image,
    };

class _Starter extends StatelessWidget {
  const _Starter({required this.s, required this.onTap});
  final (String, String, String) s;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final g = switch (s.$2) {
      'Video' => CrGlyph.video,
      'Image' => CrGlyph.image,
      'Music' => CrGlyph.music,
      'Voice-over' => CrGlyph.voice,
      _ => CrGlyph.film,
    };
    return SizedBox(
      width: 200,
      child: Semantics(
        button: true,
        label: '${s.$1}, in ${s.$2}',
        excludeSemantics: true,
        onTap: onTap,
        child: CrCard(
          onTap: onTap,
          padding: EdgeInsets.zero,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              height: 72,
              decoration: BoxDecoration(color: crTone(c, s.$1), borderRadius: const BorderRadius.vertical(top: Radius.circular(21))),
              alignment: Alignment.center,
              child: CrIcon(g, size: 24, color: c.ink2),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s.$1, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w600, fontSize: 14)),
                Text('Use in ${s.$2}', style: HoolaType.small(c).copyWith(fontSize: 12.5)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

class _Thing extends StatelessWidget {
  const _Thing({required this.glyph, required this.title, required this.sub, required this.onTap});
  final CrGlyph glyph;
  final String title, sub;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: '$title. $sub',
      excludeSemantics: true,
      onTap: onTap,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(12)),
              alignment: Alignment.center,
              child: CrIcon(glyph, size: 19, color: c.ink),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500)),
                Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
              ]),
            ),
            CrIcon(CrGlyph.chevron, size: 16, color: c.ink3),
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ guides
const List<(String, String, CrGlyph, List<String>)> _guides = [
  ('Make your first ad film', 'Director', CrGlyph.film, [
    'Write one line in Director. Hoola writes the storyboard for free.',
    'Paint the opening pictures and watch the free preview.',
    'Make the HD shots and the final film. Every paid step shows its price first.',
  ]),
  ('Keep a character the same in every shot', 'AI casting', CrGlyph.cast, [
    'Cast the character once in AI casting.',
    'In your film, add it from Cast: the face, hair and outfit stay the same in every shot.',
  ]),
  ('Write and sing a Hindi song', 'Music', CrGlyph.music, [
    'Describe the song.',
    'Tap Write with Hoola for the lyrics, or paste yours.',
    'Pick the singers and the mood, then make the song.',
  ]),
  ('Dub a video into Tamil', 'Dubbing', CrGlyph.dub, [
    'Add your video (up to 3 minutes).',
    'Pick up to 4 languages and dub.',
    'Every language comes back as its own video.',
  ]),
  ('Edit with words, not clicks', 'Video editor', CrGlyph.cut, [
    'Add your clips in order.',
    'Say what you want: a 30 s reel, cuts on the beat, Hindi captions.',
    'Ask for changes in plain words.',
  ]),
  ('A voice-over in your Hoola’s voice', 'Voice-over', CrGlyph.voice, [
    'Write the script.',
    'Pick Your Hoola’s voice or any other voice, the language and the style.',
    'Make the voice-over.',
  ]),
];

class CreateGuides extends StatelessWidget {
  const CreateGuides({super.key, required this.store, required this.open});
  final CreateStore store;
  final ValueChanged<String> open;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return CrPage(title: 'How-to guides', children: [
      const CrIntro('Short steps for each tool', 'Every paid step shows its price first, and nothing is spent until you say Haan.'),
      crGap,
      for (final g in _guides) ...[
        CrCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              CrDisc(g.$3, size: 40),
              const SizedBox(width: 12),
              Expanded(child: Text(g.$1, style: HoolaType.title(c).copyWith(fontSize: 15))),
            ]),
            const SizedBox(height: 12),
            for (var i = 0; i < g.$4.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Container(
                    width: 22,
                    height: 22,
                    decoration: BoxDecoration(color: c.sunk, shape: BoxShape.circle),
                    alignment: Alignment.center,
                    child: Text('${i + 1}', style: HoolaType.label(c).copyWith(color: c.ink)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: Text(g.$4[i], style: HoolaType.body(c).copyWith(fontSize: 14, color: c.ink2))),
                ]),
              ),
            const SizedBox(height: 4),
            Align(alignment: Alignment.centerLeft, child: CrQuiet(label: 'Open ${g.$2}', height: 48, onTap: () => open(g.$2))),
          ]),
        ),
        const SizedBox(height: 12),
      ],
    ]);
  }
}
