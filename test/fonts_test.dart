// R0: the fonts the app draws with are bundled (assets/fonts, written by tool/fetch_fonts.py), named the way
// google_fonts looks for them, so no text waits for a download and the app works offline.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('every font family the app uses is bundled under assets/fonts', () {
    const files = [
      'Manrope-Regular.ttf', 'Manrope-SemiBold.ttf', 'Manrope-Bold.ttf', 'Manrope-ExtraBold.ttf',
      'Sora-Regular.ttf', 'Sora-SemiBold.ttf', 'Sora-Bold.ttf', 'Sora-ExtraBold.ttf',
      'Literata-Regular.ttf', 'Literata-Medium.ttf', 'Literata-SemiBold.ttf', 'Literata-Italic.ttf',
      'SchibstedGrotesk-Regular.ttf', 'SchibstedGrotesk-Medium.ttf', 'SchibstedGrotesk-SemiBold.ttf',
      'SchibstedGrotesk-Bold.ttf', 'JetBrainsMono-Regular.ttf', 'JetBrainsMono-Medium.ttf',
    ];
    for (final f in files) {
      final file = File('assets/fonts/$f');
      expect(file.existsSync(), isTrue, reason: '$f missing - run python3 tool/fetch_fonts.py');
      expect(file.lengthSync(), greaterThan(20000), reason: '$f looks cut short');
    }
    expect(File('pubspec.yaml').readAsStringSync(), contains('- assets/fonts/'));
  });
}
