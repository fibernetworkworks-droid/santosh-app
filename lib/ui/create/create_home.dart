// v0.912 CREATE NATIVE + v0.913 CREATE IN COLOUR (design canvas claude.ai/artifact/HXF8gGUqohSnZBnohRkbtu, board 1): the
// Create home - "What are we making today?", the five kinds in one switch (each in its own colour; the page's light and
// the button follow it), the ask box that opens the right tool with her words in it, what is being made right now,
// camera moves that really move, the twelve studios as colour circles, her recent creations and ideas to start from.
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

typedef _Mode = ({String name, String tool, CrGlyph glyph, CrHue hue, String hint, List<String> facts, String note, String price});

/// v0.913 the five kinds, each in its own colour (the page's light, the switch, the button follow it).
const List<_Mode> _modes = [
  (name: 'Picture', tool: 'Image', glyph: CrGlyph.image, hue: CrHue.image,
      hint: 'A clay kulhad of masala chai on a brass tray, steam curling, diyas behind it, warm light…',
      facts: ['1:1', '1 picture', 'Standard'], note: 'Price for one picture', price: 'About ₹3'),
  (name: 'Clip', tool: 'Video', glyph: CrGlyph.video, hue: CrHue.video,
      hint: 'Steam rising from a kulhad of chai on a rainy Mumbai balcony, slow dolly in…',
      facts: ['9:16', '8 s', 'Sound on'], note: 'The live price shows before it starts', price: 'Price first'),
  (name: 'Film', tool: 'Director', glyph: CrGlyph.film, hue: CrHue.film,
      hint: 'A 30-second Diwali ad for my sweet shop, a family at the counter, ending on our logo…',
      facts: ['16:9', '30 s', 'Hindi'], note: 'Hoola writes the storyboard first', price: 'Storyboard free'),
  (name: 'Song', tool: 'Music', glyph: CrGlyph.music, hue: CrHue.song,
      hint: 'A happy Bollywood jingle for my sweet shop, dhol and shehnai, our name in the chorus…',
      facts: ['Hindi', '30 s', 'With words'], note: 'One whole song', price: 'About ₹7'),
  (name: 'Voice', tool: 'Voice-over', glyph: CrGlyph.voice, hue: CrHue.voice,
      hint: 'Is Diwali, Sharma Sweets laaye hain taaza kaju katli. Aaj hi aaiye!',
      facts: ['Your Hoola’s voice', 'Hindi'], note: 'Charged by the line', price: 'A few paise'),
];

typedef _Tool = ({String name, CrGlyph glyph, CrHue hue});

const List<_Tool> _tools = [
  (name: 'Image', glyph: CrGlyph.image, hue: CrHue.image),
  (name: 'Video', glyph: CrGlyph.video, hue: CrHue.video),
  (name: 'Director', glyph: CrGlyph.film, hue: CrHue.film),
  (name: 'Music', glyph: CrGlyph.music, hue: CrHue.song),
  (name: 'Voice-over', glyph: CrGlyph.voice, hue: CrHue.voice),
  (name: 'Dubbing', glyph: CrGlyph.dub, hue: CrHue.video),
  (name: 'Video editor', glyph: CrGlyph.cut, hue: CrHue.film),
  (name: 'Script writer', glyph: CrGlyph.pen, hue: CrHue.image),
  (name: 'AI casting', glyph: CrGlyph.cast, hue: CrHue.voice),
  (name: 'Hoola Cinema', glyph: CrGlyph.cinema, hue: CrHue.song),
  (name: 'Brand kit', glyph: CrGlyph.brand, hue: CrHue.film),
  (name: 'My creations', glyph: CrGlyph.grid, hue: CrHue.video),
];

/// The camera moves on the home's moving cards (the Video page has all twelve).
const List<(String, String, String)> _moves = [
  ('Dolly in', 'A slow push towards the face', 'sunset'),
  ('Orbit', 'Round and round the product', 'mint'),
  ('Crane up', 'Rises over the whole scene', 'temple'),
  ('Crash zoom', 'A sudden punch in', 'neon'),
  ('Handheld', 'Close, real, a little alive', 'rain'),
  ('Drone', 'A high flight forward', 'ocean'),
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
const _starterArt = ['diya', 'chai', 'rose', 'temple', 'neon', 'sunset'];
const _starterTall = [212.0, 176.0, 196.0, 236.0, 184.0, 204.0];

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

  Widget _screenFor(String tool, String words, {String camera = ''}) => switch (tool) {
        'Director' => CreateDirector(store: _store, brief: words),
        'Image' => CreateImage(store: _store, prompt: words),
        'Video' => CreateVideo(store: _store, prompt: words, camera: camera),
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

  void _go(String tool, [String words = '', String camera = '']) => crOpen(context, _store, _screenFor(tool, words, camera: camera));

  void _send() => _go(_modes[_mode].tool, _ask.text.trim());

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final m = _modes[_mode];
    return ListenableBuilder(
      listenable: _store,
      builder: (context, _) => CrPage(
        title: 'Create',
        hue: m.hue,
        trailing: CrRoundButton(glyph: CrGlyph.grid, label: 'My creations', onTap: () => _go('My creations')),
        onRefresh: () => _store.load(quiet: true),
        children: [
          const SizedBox(height: 6),
          Semantics(
            header: true,
            child: Text('What are we\nmaking today?',
                style: TextStyle(
                    fontFamily: c.dark ? HoolaFont.serifDark : HoolaFont.serif, fontSize: 34, height: 1.1, letterSpacing: -.4, color: c.ink)),
          ),
          const SizedBox(height: 10),
          Text('Pictures, clips, films, songs and voices from one line. Every price shows before anything is spent.',
              style: HoolaType.body(c).copyWith(color: c.ink2, fontSize: 14.5, height: 1.5)),
          const SizedBox(height: 20),
          _ModeSwitch(picked: _mode, onPick: (i) => setState(() => _mode = i)),
          const SizedBox(height: 12),
          _Compose(mode: m, controller: _ask, onSend: _send),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 0, children: [
            for (final q in const ['Diwali offer', 'Product launch', 'Festival greeting', 'Shop opening'])
              CrChip(label: q, on: false, onTap: () => setState(() => _ask.text = '${q == 'Shop opening' ? 'Our new shop opening' : q} for my business, warm and festive')),
          ]),
          if (_store.error.isNotEmpty) ...[const SizedBox(height: 14), CrNote(_store.error, glyph: CrGlyph.info)],
          if (_store.making.isNotEmpty) ...[
            crGap,
            CrHead('Making now', note: '${_store.making.length} working'),
            for (final j in _store.making) ...[CrJobRow(job: j, store: _store), const SizedBox(height: 10)],
          ],
          crGap,
          CrHead('Try a camera move', link: 'All moves', onLink: () => _go('Video')),
          SizedBox(
            height: 196,
            child: ListView.separated(
              clipBehavior: Clip.none,
              scrollDirection: Axis.horizontal,
              itemCount: _moves.length,
              separatorBuilder: (_, __) => const SizedBox(width: 10),
              itemBuilder: (_, i) => SizedBox(
                width: 138,
                child: CrHueScope(
                  hue: CrHue.video,
                  child: CrArtCard(
                    art: CrMove(move: _moves[i].$1, child: CrScene(_moves[i].$3)),
                    badge: const CrBadge('5 s', leading: CrIcon(CrGlyph.video, size: 13, color: Colors.white)),
                    title: _moves[i].$1,
                    line: _moves[i].$2,
                    label: 'Try ${_moves[i].$1}. ${_moves[i].$2}',
                    onTap: () => _go('Video', _ask.text.trim(), _moves[i].$1),
                  ),
                ),
              ),
            ),
          ),
          crGap,
          const CrHead('Every studio', note: '12 tools'),
          _Studios(onTap: _go),
          crGap,
          _Recent(store: _store, onAll: () => _go('My creations')),
          const CrHead('Start from an idea', note: 'Change the words, then make it'),
          _IdeaWall(onTap: (s) => _go(s.$2, s.$3)),
          crGap,
          CrCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(children: [
              _Thing(glyph: CrGlyph.folder, title: 'Film projects', sub: '${_store.films.length} ${_store.films.length == 1 ? 'film' : 'films'}',
                  onTap: () => _go('Film projects')),
              Divider(height: 1, color: c.dark ? Colors.white.withOpacity(.08) : c.line),
              _Thing(glyph: CrGlyph.book, title: 'How-to guides', sub: 'Short steps for each tool', onTap: () => _go('Guides')),
            ]),
          ),
        ],
      ),
    );
  }
}

/// The five kinds in one glass tray; the picked one wears its colour.
class _ModeSwitch extends StatelessWidget {
  const _ModeSwitch({required this.picked, required this.onPick});
  final int picked;
  final ValueChanged<int> onPick;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: crGlass(c, radius: 28, tint: CrHue.of(context).a),
      child: Row(children: [
        for (var i = 0; i < _modes.length; i++)
          Expanded(
            child: Semantics(
              button: true,
              selected: i == picked,
              label: _modes[i].name,
              excludeSemantics: true,
              onTap: () => onPick(i),
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () {
                  HapticFeedback.selectionClick();
                  onPick(i);
                },
                child: AnimatedContainer(
                  duration: HoolaMotion.of(context, HoolaMotion.menu),
                  curve: HoolaMotion.ease,
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: i == picked ? _modes[i].hue.gradient : null,
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: i == picked
                        ? [BoxShadow(color: _modes[i].hue.a.withOpacity(.34), blurRadius: 16, spreadRadius: -6, offset: const Offset(0, 6))]
                        : null,
                  ),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    CrIcon(_modes[i].glyph, size: 18, color: i == picked ? CreateHues.onHue : c.ink2),
                    const SizedBox(height: 3),
                    Text(_modes[i].name, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: HoolaType.label(c).copyWith(
                            fontSize: 12, color: i == picked ? CreateHues.onHue : c.ink2, fontWeight: i == picked ? FontWeight.w600 : FontWeight.w500)),
                  ]),
                ),
              ),
            ),
          ),
      ]),
    );
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
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 14, 14),
      decoration: crGlass(c, radius: 26, strong: true, tint: CrHue.of(context).a),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        TextField(
          controller: controller,
          minLines: 3,
          maxLines: 7,
          textInputAction: TextInputAction.newline,
          style: HoolaType.bodyLarge(c).copyWith(fontSize: 16, height: 1.5),
          decoration: InputDecoration(
            hintText: mode.hint,
            hintMaxLines: 3,
            hintStyle: HoolaType.bodyLarge(c).copyWith(color: c.ink3, fontSize: 16, height: 1.5),
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
            filled: false,
            isDense: true,
            contentPadding: EdgeInsets.zero,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final f in mode.facts)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
              decoration: BoxDecoration(color: crWash(c), borderRadius: BorderRadius.circular(15)),
              child: Text(f, style: HoolaType.small(c).copyWith(color: c.ink2, fontSize: 12.5, fontWeight: FontWeight.w500)),
            ),
        ]),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(mode.note, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(fontSize: 12.5)),
              const SizedBox(height: 1),
              Text(mode.price, style: HoolaType.title(c).copyWith(fontSize: 15.5)),
            ]),
          ),
          Semantics(
            button: true,
            label: 'Continue with ${mode.name.toLowerCase()}',
            excludeSemantics: true,
            onTap: onSend,
            child: crPress(
              onTap: onSend,
              child: AnimatedContainer(
                duration: HoolaMotion.of(context, HoolaMotion.menu),
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 20),
                decoration: BoxDecoration(
                  gradient: mode.hue.gradient,
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [BoxShadow(color: mode.hue.a.withOpacity(.4), blurRadius: 20, spreadRadius: -8, offset: const Offset(0, 8))],
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('Continue', style: HoolaType.button(c, color: CreateHues.onHue).copyWith(fontSize: 15)),
                  const SizedBox(width: 8),
                  const CrIcon(CrGlyph.chevron, size: 16, color: CreateHues.onHue),
                ]),
              ),
            ),
          ),
        ]),
      ]),
    );
  }
}

/// Twelve studios as colour circles, four to a row, in one glass card.
class _Studios extends StatelessWidget {
  const _Studios({required this.onTap});
  final void Function(String) onTap;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(6, 16, 6, 10),
      decoration: crGlass(c, radius: 24, tint: CrHue.of(context).b),
      child: LayoutBuilder(builder: (context, box) {
        final w = box.maxWidth / 4;
        return Wrap(children: [
          for (final t in _tools)
            SizedBox(
              width: w,
              child: Semantics(
                button: true,
                label: t.name,
                excludeSemantics: true,
                onTap: () => onTap(t.name),
                child: crPress(
                  onTap: () => onTap(t.name),
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Column(children: [
                      CrDisc(t.glyph, size: 52, hue: t.hue),
                      const SizedBox(height: 7),
                      SizedBox(
                        height: 32,
                        child: Text(t.name, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                            style: HoolaType.small(c).copyWith(color: c.ink, fontSize: 12.5, height: 1.25)),
                      ),
                    ]),
                  ),
                ),
              ),
            ),
        ]);
      }),
    );
  }
}

class _Recent extends StatelessWidget {
  const _Recent({required this.store, required this.onAll});
  final CreateStore store;
  final VoidCallback onAll;
  @override
  Widget build(BuildContext context) {
    final items = store.items.take(10).toList();
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      CrHead('Recent', link: 'See all', onLink: onAll),
      SizedBox(
        height: 172,
        child: ListView.separated(
          clipBehavior: Clip.none,
          scrollDirection: Axis.horizontal,
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(width: 10),
          itemBuilder: (_, i) {
            final it = items[i];
            final pic = crS(it['mime']).startsWith('image/');
            return SizedBox(
              width: 128,
              child: CrArtCard(
                art: pic
                    ? CrItemImage(app: store.app, item: it, cache: 384)
                    : Stack(fit: StackFit.expand, children: [
                        CrScene(crSceneFor(it['id'])),
                        Center(child: CrIcon(_kindGlyph(crS(it['kind'])), size: 28, color: Colors.white)),
                      ]),
                badge: CrBadge(crKindName(crS(it['kind']))),
                title: crS(it['title']),
                label: '${crKindName(crS(it['kind']))}: ${crS(it['title'])}',
                onTap: () => crOpenItem(context, store, it),
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

/// The ideas to start from, in two columns of different heights (like a wall of pictures).
class _IdeaWall extends StatelessWidget {
  const _IdeaWall({required this.onTap});
  final ValueChanged<(String, String, String)> onTap;
  @override
  Widget build(BuildContext context) {
    Widget card(int i) {
      final s = crStarters[i];
      return Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: SizedBox(
          width: double.infinity,
          height: _starterTall[i],
          child: CrArtCard(
            art: CrScene(_starterArt[i]),
            badge: CrBadge(s.$2),
            title: s.$1,
            line: 'Use this',
            label: '${s.$1}, in ${s.$2}',
            onTap: () => onTap(s),
          ),
        ),
      );
    }

    return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Expanded(child: Column(children: [for (var i = 0; i < crStarters.length; i += 2) card(i)])),
      const SizedBox(width: 10),
      Expanded(child: Column(children: [for (var i = 1; i < crStarters.length; i += 2) card(i)])),
    ]);
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
            CrDisc(glyph, size: 40),
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
    return CrPage(hue: CrHue.film, title: 'How-to guides', children: [
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
