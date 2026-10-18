import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}

/// One event from the backend's live stream.
class SantoshEvent {
  SantoshEvent(this.id, this.kind, this.payload, this.at);
  final int id;
  final String kind;
  final Map<String, dynamic> payload;
  final DateTime at;

  static SantoshEvent fromJson(Map<String, dynamic> j) => SantoshEvent(
        (j['id'] as num).toInt(),
        j['kind'] as String,
        Map<String, dynamic>.from(j['payload'] as Map? ?? {}),
        DateTime.tryParse(j['at'] as String? ?? '')?.toUtc() ?? DateTime.now().toUtc(),
      );
}

/// Talks to Santosh Core (the FastAPI backend).
class Api {
  Api(this.baseUrl, this.apiKey);
  String baseUrl;
  String apiKey;
  final http.Client _http = http.Client();

  Uri _u(String path, [Map<String, String>? q]) {
    final b = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    return Uri.parse('$b$path').replace(queryParameters: q);
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (apiKey.isNotEmpty) 'Authorization': 'Bearer $apiKey',
      };

  Future<dynamic> _send(String method, String path, {Object? body, Map<String, String>? query}) async {
    final req = http.Request(method, _u(path, query))..headers.addAll(_headers);
    if (body != null) req.body = jsonEncode(body);
    final res = await http.Response.fromStream(await _http.send(req).timeout(const Duration(seconds: 25)));
    final text = utf8.decode(res.bodyBytes);
    if (res.statusCode >= 400) {
      var msg = 'Server error ${res.statusCode}';
      try {
        msg = (jsonDecode(text) as Map)['detail']?.toString() ?? msg;
      } catch (_) {}
      throw ApiException(res.statusCode, msg);
    }
    return text.isEmpty ? null : jsonDecode(text);
  }

  Future<Map<String, dynamic>> health() async => Map<String, dynamic>.from(await _send('GET', '/healthz'));

  Future<Map<String, dynamic>> me() async => Map<String, dynamic>.from(await _send('GET', '/api/me'));
  Future<void> disconnect(String provider) async => _send('DELETE', '/api/connections/$provider');
  Uri googleSignInUrl() => _u('/auth/google/start');
  Future<String> newConversation() async => (await _send('POST', '/api/conversations'))['id'] as String;
  Future<void> checkConversation(String id) async => _send('GET', '/api/conversations/$id/messages');
  Future<void> sendMessage(String conv, String text, {bool voice = false}) async =>
      _send('POST', '/api/conversations/$conv/messages', body: {'text': text, if (voice) 'voice': true});

  /// Santosh's automatic jobs. Older servers (before v0.3) have none: returns an empty list.
  Future<List<Map<String, dynamic>>> routines() async {
    try {
      return List<Map<String, dynamic>>.from((await _send('GET', '/api/routines'))['routines'] as List);
    } on ApiException catch (e) {
      if (e.status == 404) return [];
      rethrow;
    }
  }

  Future<void> cancelRoutine(String id) async => _send('POST', '/api/routines/$id/cancel');

  Future<List<Map<String, dynamic>>> pendingEmails() async {
    try {
      return List<Map<String, dynamic>>.from((await _send('GET', '/api/emails/pending'))['emails'] as List);
    } on ApiException catch (e) {
      if (e.status == 404) return [];
      rethrow;
    }
  }

  Future<void> sendEmail(String id, {String? to, String? cc, String? subject, String? body}) async =>
      _send('POST', '/api/emails/$id/send', body: {
        if (to != null) 'to': to, if (cc != null) 'cc': cc, if (subject != null) 'subject': subject, if (body != null) 'body': body,
      });

  Future<void> cancelEmail(String id) async => _send('POST', '/api/emails/$id/cancel');

  Future<List<Map<String, dynamic>>> reminders() async =>
      List<Map<String, dynamic>>.from((await _send('GET', '/api/reminders'))['reminders'] as List);
  Future<void> cancelReminder(String id) async => _send('POST', '/api/reminders/$id/cancel');

  Future<Map<String, dynamic>> lists() async => Map<String, dynamic>.from((await _send('GET', '/api/lists'))['lists'] as Map);
  Future<void> tickItem(int id) async => _send('POST', '/api/lists/items/$id/done');

  Future<List<Map<String, dynamic>>> memory() async =>
      List<Map<String, dynamic>>.from((await _send('GET', '/api/memory'))['facts'] as List);
  Future<void> forget(int id) async => _send('DELETE', '/api/memory/$id');

  Future<Map<String, dynamic>> profile() async => Map<String, dynamic>.from(await _send('GET', '/api/profile'));
  Future<Map<String, dynamic>> saveProfile(Map<String, dynamic> p) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/profile', body: p));

  Future<List<Map<String, dynamic>>> pendingActions() async =>
      List<Map<String, dynamic>>.from((await _send('GET', '/api/device-actions/pending'))['actions'] as List);
  Future<void> actionResult(String id, bool ok, [String? detail]) async =>
      _send('POST', '/api/device-actions/$id/result', body: {'ok': ok, 'detail': detail});

  Future<Map<String, dynamic>> campaignAction(String id, String action) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/campaigns/$id/action', body: {'action': action}));

  Future<Map<String, dynamic>> uploadLeads(String conv, String filename, List<int> bytes) async {
    final req = http.MultipartRequest('POST', _u('/api/leads/upload'))
      ..fields['conversation_id'] = conv
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    if (apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer $apiKey';
    final res = await http.Response.fromStream(await req.send());
    final body = jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) throw ApiException(res.statusCode, (body as Map)['detail']?.toString() ?? 'Upload failed');
    return Map<String, dynamic>.from(body as Map);
  }

  /// Server-sent events with automatic reconnect that resumes from the last event id.
  Stream<SantoshEvent> events(String conv, {int after = 0}) async* {
    var last = after;
    var backoff = 1;
    while (true) {
      try {
        final req = http.Request('GET', _u('/api/conversations/$conv/events', {'after': '$last'}))
          ..headers.addAll({..._headers, 'Accept': 'text/event-stream'});
        final client = http.Client();
        final res = await client.send(req);
        if (res.statusCode == 401 || res.statusCode == 404) {
          client.close();
          throw ApiException(res.statusCode, res.statusCode == 401 ? 'Wrong API key' : 'Conversation not found');
        }
        backoff = 1;
        final lines = res.stream.transform(utf8.decoder).transform(const LineSplitter());
        final buf = StringBuffer();
        await for (final line in lines) {
          if (line.startsWith('data:')) {
            buf.write(line.substring(5).trimLeft());
          } else if (line.isEmpty && buf.isNotEmpty) {
            final ev = SantoshEvent.fromJson(Map<String, dynamic>.from(jsonDecode(buf.toString()) as Map));
            buf.clear();
            if (ev.id > last) {
              last = ev.id;
              yield ev;
            }
          }
        }
        client.close();
      } on ApiException {
        rethrow;
      } catch (_) {
        // network blip: wait and resume
      }
      await Future.delayed(Duration(seconds: backoff));
      backoff = backoff >= 16 ? 16 : backoff * 2;
    }
  }
}
