// v0.860 R1: a picture of the new design system (lib/ui/hoola_theme.dart), light and dark, made on CI with the
// other screen pictures (app-screens.yml -> hoola-screens: 20_theme_light.png, 21_theme_dark.png).
// It shows only what the theme itself gives: the type scale, the colour roles, buttons, a card, a field, chips,
// rows and status badges - the real screens built from it come in R2+.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:santosh/ui/hoola_theme.dart';

import 'golden_fonts.dart';

class _Specimen extends StatelessWidget {
  const _Specimen();

  Widget _swatch(String name, Color fill, HoolaColors c) => Column(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 44, height: 44, decoration: BoxDecoration(color: fill, borderRadius: HoolaRadius.r(HoolaRadius.tile), border: Border.all(color: c.line))),
        const SizedBox(height: 4),
        Text(name, style: HoolaType.label(c)),
      ]);

  Widget _badge(String text, Color fg, Color bg, HoolaColors c) => Container(
        height: 26,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(color: bg, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 6, height: 6, decoration: BoxDecoration(color: fg, shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text(text, style: HoolaType.label(c).copyWith(color: fg, fontWeight: FontWeight.w600)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Design system')),
      body: ListView(padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 4, HoolaSpace.gutter, 24), children: [
        Text('Afternoon, Kunal', style: HoolaType.hero(c)),
        const SizedBox(height: 6),
        Text('Display 22 · Heading 18 · Title 16', style: HoolaType.display(c)),
        Text('Heading 18', style: HoolaType.heading(c)),
        Text('Title 16 semibold', style: HoolaType.title(c)),
        Text('Body 15 - the interface text, for rows and forms.', style: HoolaType.body(c)),
        Text('Small 13 - meta lines and captions', style: HoolaType.small(c)),
        Text('LABEL 12 · NOTHING SMALLER', style: HoolaType.label(c)),
        const SizedBox(height: 10),
        Text('Your October GST summary is ready. Two supplier bills are not filed yet.', style: HoolaType.reply(c)),
        const SizedBox(height: 4),
        Text('GSTR-2B · section 4', style: HoolaType.code(c, size: 14).copyWith(backgroundColor: c.code)),
        const SizedBox(height: 16),
        Wrap(spacing: 10, runSpacing: 10, children: [
          _swatch('bg', c.bg, c), _swatch('surface', c.surface, c), _swatch('sunk', c.sunk, c), _swatch('line', c.line, c),
          _swatch('ink', c.ink, c), _swatch('ink3', c.ink3, c), _swatch('accent', c.accent, c), _swatch('pill', c.pill, c),
        ]),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(child: OutlinedButton(onPressed: () {}, child: const Text('Not now'))),
          const SizedBox(width: 10),
          Expanded(child: FilledButton(onPressed: () {}, child: const Text('Yes, send'))),
        ]),
        const SizedBox(height: 12),
        const TextField(decoration: InputDecoration(hintText: 'Search what Hoola made', prefixIcon: Icon(Icons.search_rounded))),
        const SizedBox(height: 12),
        Wrap(spacing: 8, children: [
          _badge('Needs you', c.warn, c.warnSoft, c),
          _badge('Working', c.accent, c.accentSoft, c),
          _badge('Done', c.ok, c.okSoft, c),
          _badge('Failed', c.bad, c.badSoft, c),
        ]),
        const SizedBox(height: 12),
        Card(
          child: Column(children: [
            ListTile(leading: const Icon(Icons.mail_outline_rounded), title: const Text('Gmail'),
                subtitle: const Text('Reads and drafts mail · asks before sending'), trailing: const Icon(Icons.chevron_right_rounded)),
            const Divider(),
            ListTile(leading: const Icon(Icons.folder_outlined), title: const Text('Google Drive'),
                subtitle: const Text('Finds and saves your files'), trailing: const Icon(Icons.chevron_right_rounded)),
          ]),
        ),
      ]),
    );
  }
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await loadIconFont();
    await loadHoolaFamilies();
  });

  for (final b in Brightness.values) {
    final name = b == Brightness.light ? '20_theme_light' : '21_theme_dark';
    testWidgets('design system specimen ($name)', (t) async {
      t.view.physicalSize = const Size(780, 1688);
      t.view.devicePixelRatio = 2;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(debugShowCheckedModeBanner: false, theme: hoolaTheme(b), home: const _Specimen()));
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 200)));
      await t.pump(const Duration(milliseconds: 400));
      await expectLater(find.byType(MaterialApp), matchesGoldenFile('shots/$name.png'));
    });
  }
}
