// v0.896 CALL GLOW: the live call looks like her Claude + Gemini videos - the Hoola mark + "Hold tight, connecting…"
// while it opens, a light from below that follows the voice, her words in a bubble and his in serif; Settings picks
// 'glow' (mic in the middle) or 'pill' (a living pill of light between the buttons).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/call_session.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:santosh/ui/talk/hoola_talk.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app(String look) async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true, 'call_look': look});
  return Santosh.load();
}

Future<void> _show(WidgetTester t, Santosh app) async {
  t.view.physicalSize = const Size(1080, 2280);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(home: HoolaTheme(appearance: 'dark', child: HoolaTalk(app: app))));
  for (var i = 0; i < 20; i++) {
    await t.pump(const Duration(milliseconds: 50));   // the light rises frame by frame (a ticker: no pumpAndSettle)
  }
}

void main() {
  testWidgets('glow look: connecting line, the light from below, the mic in the middle and End', (t) async {
    final sem = t.ensureSemantics();
    final app = await _app('glow');
    app.voiceCall
      ..inCall = true
      ..act = CallAct.connecting;
    await _show(t, app);
    expect(find.text('Hold tight, connecting…'), findsOneWidget);
    expect(find.byType(CallMark), findsOneWidget);
    expect(find.byWidgetPredicate((w) => w is CustomPaint && w.painter is CallGlowPainter), findsOneWidget);
    expect(find.byWidgetPredicate((w) => w is CustomPaint && w.painter is CallPillPainter), findsNothing);
    expect(find.bySemanticsLabel('Mute'), findsOneWidget);
    expect(find.bySemanticsLabel('End the call'), findsOneWidget);
    expect(find.text('Type'), findsOneWidget);

    app.voiceCall.act = CallAct.listening;
    app.voiceCall.notifyListeners();
    await t.pump(const Duration(milliseconds: 600));
    expect(find.textContaining("Let's talk"), findsOneWidget);
    await t.tap(find.bySemanticsLabel('Mute'));
    await t.pump(const Duration(milliseconds: 100));
    expect(app.voiceCall.muted, isTrue);
    expect(find.bySemanticsLabel('Unmute'), findsOneWidget);
    expect(find.text('Your mic is off'), findsOneWidget);
    await t.pumpWidget(const SizedBox());
    sem.dispose();
  });

  testWidgets('pill look: her words in a bubble, his in the middle, the living pill between the buttons', (t) async {
    final app = await _app('pill');
    app.voiceCall
      ..inCall = true
      ..act = CallAct.speaking
      ..heard = 'Kal subah 10 baje Sharma ji ke saath meeting rakh do'
      ..reply = 'Theek hai. Kal subah 10 baje meeting rakh di.';
    await _show(t, app);
    expect(find.text(app.voiceCall.heard), findsOneWidget);
    expect(find.text(app.voiceCall.reply), findsOneWidget);
    expect(find.byWidgetPredicate((w) => w is CustomPaint && w.painter is CallPillPainter), findsOneWidget);
    expect(find.text('Tap to stop Santosh'), findsOneWidget);
    await t.pumpWidget(const SizedBox());
  });

  testWidgets('the look is her setting, glow by default', (t) async {
    SharedPreferences.setMockInitialValues({});
    final app = await Santosh.load();
    expect(app.callLook, 'glow');
    await app.setCallLook('pill');
    expect(app.callLook, 'pill');
    await app.setCallLook('nonsense');
    expect(app.callLook, 'glow');
  });
}
