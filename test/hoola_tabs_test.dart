// v0.866 R6: the three new tabs sort her data the same way every time.
import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/ui/shell/hoola_tabs.dart';

void main() {
  test('work: kaam list + chat results into needs you / in progress / done, no chat twice', () {
    final kaam = {
      'waiting': [
        {'title': 'Pick one of three looks', 'state': 'waiting', 'conversation_id': 'c1', 'at': '2026-11-12T10:00:00Z'}
      ],
      'running': [
        {'title': 'Website build', 'state': 'working', 'conversation_id': 'c2', 'at': '2026-11-12T11:00:00Z', 'stuck': true}
      ],
      'done': [
        {'title': 'GST summary', 'state': 'done', 'conversation_id': 'c3', 'at': '2026-11-11T09:00:00Z'},
        {'title': 'Invoices', 'state': 'stuck', 'conversation_id': 'c4', 'at': '2026-11-12T08:00:00Z'},
      ],
    };
    final chats = [
      {'id': 'c1', 'title': 'Website', 'result': {'status': 'needs_you', 'line': 'x'}},   // already from the kaam list
      {'id': 'c5', 'title': 'Poster', 'result': {'status': 'needs_you', 'line': 'Approve the poster text'}},
      {'id': 'c6', 'title': 'Weather', 'result': {'status': 'working', 'line': 'Working on it'}},
      {'id': 'c7', 'title': 'Hello', 'result': {'status': 'done', 'line': 'Hi'}},
      {'id': 'c8', 'title': 'Old', 'result': null},
    ];
    final p = workSections(kaam, chats);
    expect(p.needs.map((w) => w.conv), containsAll(['c1', 'c5']));
    expect(p.needs.length, 2);
    expect(p.running.map((w) => w.conv), containsAll(['c2', 'c6']));
    expect(p.running.firstWhere((w) => w.conv == 'c2').state, 'stuck');
    expect(p.done.map((w) => w.state), ['failed', 'done']);   // newest first, stuck -> did not finish
    expect(workStateWord('waiting'), 'Needs your answer');
    expect(workStateWord('failed'), 'Did not finish');
  });

  test('made: pages + creations newest first with the right kinds', () {
    final items = madeItems([
      {'id': 'a1', 'title': 'Diwali page', 'updated_at': '2026-10-20T10:00:00Z', 'status': 'ready'},
      {'id': '', 'title': 'no id'},
    ], [
      {'id': 'cr1', 'kind': 'image', 'title': 'Poster', 'mime': 'image/png', 'created': 1794000000},
      {'id': 'cr2', 'kind': 'song', 'title': 'Jingle', 'mime': 'audio/mpeg', 'created': 1793000000},
      {'id': 'cr3', 'kind': 'script', 'title': 'Reel script', 'mime': 'text/markdown', 'created': 1700000000},
    ]);
    expect(items.map((m) => m.id), ['cr1', 'cr2', 'a1', 'cr3']);
    expect(items.map((m) => m.kind), ['picture', 'audio', 'page', 'document']);
  });

  test('connect: connected, add, built in; an app is listed once', () {
    final p = connectSections({
      'packs': [
        {'id': 'swiggy', 'name': 'Swiggy', 'status': 'needs_link'},
        {'id': 'gmail', 'name': 'Gmail', 'status': 'ready'},
        {'id': 'calc', 'name': 'Calculator', 'status': 'core'},
        {'id': 'demo', 'name': 'Demo bill', 'status': 'demo'},
        {'pack_id': 'zomato', 'name': 'Zomato again', 'status': 'ready'},
      ]
    }, [
      {'pack_id': 'zomato', 'name': 'Zomato', 'status': 'ready'},
      {'pack_id': 'blinkit', 'name': 'Blinkit', 'status': 'needs_link'},
      {'pack_id': 'soon', 'name': 'Later', 'status': 'coming'},
    ]);
    expect(p.connected.map((i) => i.name), ['Gmail', 'Zomato']);
    expect(p.add.map((i) => i.name), ['Blinkit', 'Swiggy']);
    expect(p.builtin.map((i) => i.name), ['Calculator']);
  });

  test('when: today / yesterday / date', () {
    final now = DateTime.now();
    expect(hoolaWhen(DateTime(now.year, now.month, now.day, 9, 5)), 'Today 09:05');
    expect(hoolaWhen(null), '');
  });
}
