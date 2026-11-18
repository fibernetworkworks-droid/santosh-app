// Fonts for the screen pictures: test machines draw boxes unless a font is loaded by hand.
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/services.dart';

import 'package:santosh/ui/hoola_theme.dart';

/// Real icon glyphs instead of test boxes: the Material Icons font ships inside the Flutter SDK cache.
Future<void> loadIconFont() async {
  final tried = <String>[];
  final roots = <String>[
    if (Platform.environment['FLUTTER_ROOT'] != null) '${Platform.environment['FLUTTER_ROOT']}/bin/cache/artifacts',
  ];
  // flutter_tester lives in <sdk>/bin/cache/artifacts/engine/<platform>/ - walk up to "artifacts"
  var dir = File(Platform.resolvedExecutable).parent;
  for (var i = 0; i < 6; i++) {
    if (dir.path.endsWith('artifacts')) roots.add(dir.path);
    dir = dir.parent;
  }
  for (final r in roots) {
    final f = File('$r/material_fonts/MaterialIcons-Regular.otf');
    tried.add(f.path);
    if (f.existsSync()) {
      final loader = FontLoader('MaterialIcons')..addFont(Future.value(ByteData.sublistView(f.readAsBytesSync())));
      await loader.load();
      return;
    }
  }
  // ignore: avoid_print
  print('R0: Material Icons font not found (icons show as boxes). Looked in: $tried');
}

/// The redesign's three families (pubspec `fonts:`), which flutter test does not load by itself.
Future<void> loadHoolaFamilies() async {
  const fams = {
    HoolaFont.sans: ['SchibstedGrotesk-Regular', 'SchibstedGrotesk-Medium', 'SchibstedGrotesk-SemiBold', 'SchibstedGrotesk-Bold'],
    HoolaFont.serif: ['Literata-Regular', 'Literata-Medium', 'Literata-SemiBold', 'Literata-Italic'],
    HoolaFont.mono: ['JetBrainsMono-Regular', 'JetBrainsMono-Medium'],
    HoolaFont.serifDark: ['LiterataDark-Regular', 'LiterataDark-SemiBold', 'LiterataDark-Italic'],   // v0.892
  };
  for (final e in fams.entries) {
    final l = FontLoader(e.key);
    for (final f in e.value) {
      l.addFont(rootBundle.load('assets/fonts/$f.ttf'));
    }
    await l.load();
  }
  final d = FontLoader(HoolaFont.dyslexic);   // v0.892 the Dyslexic chat font ships as OpenType (.otf)
  d.addFont(rootBundle.load('assets/fonts/OpenDyslexic-Regular.otf'));
  d.addFont(rootBundle.load('assets/fonts/OpenDyslexic-Bold.otf'));
  await d.load();
}
