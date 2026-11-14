// v0.899 NAYA CHAT KHULE (owner: "When click on new chat it won't open new chat"). The chat's live stream used to be
// an async* generator: cancelling it while it sat in `await for` only finished at its next `yield`, and a quiet chat
// sends nothing but `: ping` comments - so `await _sub?.cancel()` waited for ever and New chat (and switching chats)
// stayed on the old chat. These tests hold a real local SSE server that only pings and never closes.
import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:santosh/api.dart';

Future<HttpServer> _quietServer({void Function()? onClosed}) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((req) async {
    final res = req.response;
    res.headers.contentType = ContentType('text', 'event-stream');
    res.bufferOutput = false;
    res.write(': open\n\n');
    await res.flush();
    final ping = Timer.periodic(const Duration(milliseconds: 200), (_) {
      try {
        res.write(': ping\n\n');
        res.flush().catchError((_) {});
      } catch (_) {}
    });
    res.done.then((_) {}, onError: (_) {}).whenComplete(() {
      ping.cancel();
      onClosed?.call();
    });
  });
  return server;
}

void main() {
  test('a quiet chat stream stops at once when cancelled (New chat no longer waits on it)', () async {
    var closed = 0;
    final server = await _quietServer(onClosed: () => closed++);
    final api = Api('http://127.0.0.1:${server.port}', 'k');
    final got = <SantoshEvent>[];
    final sub = api.events('old', live: true).listen(got.add, onError: (_) {});
    await Future<void>.delayed(const Duration(milliseconds: 500));   // connected, pings flowing, no event yet
    final sw = Stopwatch()..start();
    await sub.cancel().timeout(const Duration(seconds: 2));
    expect(sw.elapsedMilliseconds, lessThan(1000));
    expect(got, isEmpty);
    for (var i = 0; i < 30 && closed == 0; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 100));   // the server notices at its next ping
    }
    expect(closed, 1, reason: 'the old chat\'s connection is closed, not left open on the server');
    await server.close(force: true);
  });

  test('the account stream stops at once too', () async {
    final server = await _quietServer();
    final api = Api('http://127.0.0.1:${server.port}', 'k');
    final sub = api.accountEvents().listen((_) {}, onError: (_) {});
    await Future<void>.delayed(const Duration(milliseconds: 500));
    await sub.cancel().timeout(const Duration(seconds: 2));
    await server.close(force: true);
  });

  test('events still arrive, in order, and a seen id is never delivered twice', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((req) async {
      final res = req.response;
      res.headers.contentType = ContentType('text', 'event-stream');
      res.bufferOutput = false;
      for (final id in [3, 4, 4, 2, 5]) {
        res.write('data: {"id": $id, "kind": "message", "payload": {"role": "assistant", "text": "m$id"}}\n\n');
      }
      await res.flush();
    });
    final api = Api('http://127.0.0.1:${server.port}', 'k');
    final ids = <int>[];
    final done = Completer<void>();
    final sub = api.events('c', after: 2).listen((e) {
      ids.add(e.id);
      if (e.id == 5 && !done.isCompleted) done.complete();
    }, onError: (_) {});
    await done.future.timeout(const Duration(seconds: 3));
    await sub.cancel();
    expect(ids, [3, 4, 5]);
    await server.close(force: true);
  });

  test('a refused key ends the chat stream with the error', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((req) {
      req.response.statusCode = 401;
      req.response.close();
    });
    final api = Api('http://127.0.0.1:${server.port}', 'bad');
    final err = Completer<Object>();
    final ended = Completer<void>();
    api.events('c').listen((_) {}, onError: (e) => err.complete(e), onDone: ended.complete);
    final e = await err.future.timeout(const Duration(seconds: 3));
    expect(e, isA<ApiException>());
    expect((e as ApiException).status, 401);
    await ended.future.timeout(const Duration(seconds: 3));
    await server.close(force: true);
  });
}
