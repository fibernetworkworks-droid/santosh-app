// v0.900 SAB CARD NAYE (owner: "GO BUILD ALL CARDS"): every card in the chat is drawn in the new design. The kinds she
// meets most have their own redrawn card; every other kind gets the new card read from its data, and its full old
// card (every button it had) opens from Details / Review - nothing is drawn in the old dark frame any more.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:santosh/state.dart';
import 'package:santosh/ui/chat/hoola_card.dart';
import 'package:santosh/ui/chat/hoola_cards_all.dart';
import 'package:santosh/ui/hoola_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<Santosh> _app() async {
  SharedPreferences.setMockInitialValues({'a_name': 'Santosh', 'a_gender': 'm', 'new_look': true});
  return Santosh.load();
}

Widget _host(Widget Function(BuildContext) b) =>
    MaterialApp(home: HoolaTheme(appearance: 'light', child: Scaffold(body: SingleChildScrollView(child: Builder(builder: b)))));

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);   // fonts come from assets/fonts

  testWidgets('the kinds she meets most have their own new card', (t) async {
    final app = await _app();
    final want = <String, Type>{
      'goal': HCGoal,
      'operator_task': HCOperatorTask,
      'operator_ask': HCOperatorAsk,
      'memory_saved': HCQuietLine,
      'memory_used': HCQuietLine,
      'compact': HCQuietLine,
      'google_reconnect': HCReconnect,
      'link': HCLinkApp,
      'calendar_event': HCCalendar,
      'maps_places': HCPlaces,
      'photo_made': HCPhoto,
      'bazar': HCApproval,
      'pc_file': HCFile,
      'artifact': HCPage,
      'any_card': HCAny,
    };
    late BuildContext ctx;
    await t.pumpWidget(_host((c) {
      ctx = c;
      return const SizedBox();
    }));
    for (final e in want.entries) {
      final w = hoolaCardAll(ctx, app, FeedItem(e.key, {'id': 'x'}));
      expect(w.runtimeType, e.value, reason: e.key);
    }
    app.dispose();
  });

  testWidgets('every other kind gets the new card, never the old dark frame', (t) async {
    final app = await _app();
    late BuildContext ctx;
    await t.pumpWidget(_host((c) {
      ctx = c;
      return const SizedBox();
    }));
    for (final k in ['thok_order', 'seva_ticket', 'email', 'campaign', 'video_job', 'browser', 'employee_ask', 'studio_approval',
      'hoola_khata', 'devsahayak_task', 'gst_day', 'call_receipt', 'upi_result', 'open']) {
      final w = hoolaCardAll(ctx, app, FeedItem(k, {'id': 'x', 'title': 'Something'}));
      expect(w, isA<HCLegacy>(), reason: k);
    }
    // a kind with no card at all stays invisible, as before
    expect(hoolaCardAll(ctx, app, FeedItem('no_such_kind', {})), isNull);
    app.dispose();
  });

  testWidgets('Details opens the full card with all its buttons; a card that waits for her says Review', (t) async {
    final app = await _app();
    final it = FeedItem('open', {'pack': 'Swiggy', 'message': 'Your order is ready to pay in Swiggy'});
    await t.pumpWidget(_host((c) => hoolaCardAll(c, app, it)!));
    expect(find.byType(HoolaCard), findsOneWidget);
    expect(find.byType(OutlinedButton), findsNothing);
    await t.tap(find.text('Details'));
    await t.pumpAndSettle();
    expect(find.byType(BottomSheet), findsOneWidget);
    expect(find.byType(OutlinedButton), findsOneWidget, reason: 'the old card, with its button, in the sheet');

    final ask = FeedItem('studio_approval', {'id': 's1', 'status': 'pending', 'title': 'Make the Diwali reel for ₹120'});
    await t.pumpWidget(_host((c) => hoolaCardAll(c, app, ask)!));
    await t.pumpAndSettle();
    expect(find.text('Review'), findsOneWidget);
    expect(find.text('Needs your yes'), findsOneWidget);
    app.dispose();
  });

  testWidgets('the long task card: step bar, the running step, a clock, Stop; done shows the report', (t) async {
    final app = await _app();
    final it = FeedItem('goal', {
      'id': 'g1', 'title': 'Deep research on Indian banking', 'status': 'working', 'done': 1, 'total': 3,
      'started_at': DateTime.now().toUtc().subtract(const Duration(minutes: 4, seconds: 12)).toIso8601String(),
      'steps': [
        {'n': 1, 'text': 'Bank list', 'state': 'done'},
        {'n': 2, 'text': 'Public sector revenues', 'state': 'current'},
        {'n': 3, 'text': 'Build the PDF', 'state': 'pending'},
      ],
    });
    await t.pumpWidget(_host((c) => hoolaCardAll(c, app, it)!));
    await t.pump(const Duration(milliseconds: 100));
    expect(find.text('Step 2 of 3'), findsOneWidget);
    expect(find.text('Public sector revenues'), findsOneWidget);
    expect(find.text('Stop'), findsOneWidget);
    expect(find.text('Hide steps'), findsOneWidget);
    expect(find.textContaining(RegExp(r'^4:1\d$')), findsOneWidget, reason: 'the live clock');
    expect(find.text('LONG TASK IN PROGRESS'), findsNothing, reason: 'no shouting label');
    await t.tap(find.text('Hide steps'));
    await t.pump();
    expect(find.text('Public sector revenues'), findsNothing);

    final done = FeedItem('goal', {
      'id': 'g2', 'title': 'October GST summary', 'status': 'done', 'done': 2, 'total': 2,
      'steps': [{'n': 1, 'text': 'Read bills', 'state': 'done'}, {'n': 2, 'text': 'Build the PDF', 'state': 'done'}],
      'report': {'summary': 'The PDF is ready.', 'bana': ['October_GST_summary.pdf']},
    });
    await t.pumpWidget(_host((c) => hoolaCardAll(c, app, done)!));
    await t.pump();
    expect(find.text('Done · 2 of 2 steps'), findsOneWidget);
    expect(find.text('What was made'), findsOneWidget);
    expect(find.text('Stop'), findsNothing);
    await t.pumpWidget(const SizedBox());
    app.dispose();
  });

  testWidgets('a choice from a job is answered right in the card', (t) async {
    final app = await _app();
    final it = FeedItem('operator_ask', {'id': 'q1', 'kind': 'choice', 'status': 'pending', 'reason': 'Which pizza?',
      'options': ['Margherita', 'Farmhouse']});
    await t.pumpWidget(_host((c) => hoolaCardAll(c, app, it)!));
    expect(find.text('Which pizza?'), findsOneWidget);
    expect(find.text('Margherita'), findsOneWidget);
    expect(find.text('Choose'), findsOneWidget);
    // an OTP never gets a box in the chat card: one tap opens its own guarded card
    final otp = FeedItem('operator_ask', {'id': 'q2', 'kind': 'otp', 'status': 'pending'});
    await t.pumpWidget(_host((c) => hoolaCardAll(c, app, otp)!));
    expect(find.byType(TextField), findsNothing);
    expect(find.text('Answer'), findsOneWidget);
    app.dispose();
  });
}
