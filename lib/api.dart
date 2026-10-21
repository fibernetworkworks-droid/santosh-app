import 'dart:async';
import 'dart:convert';
import 'dart:io' show SocketException;
import 'dart:math' as math;

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

  Future<dynamic> _send(String method, String path, {Object? body, Map<String, String>? query, Duration timeout = const Duration(seconds: 25)}) async {
    final req = http.Request(method, _u(path, query))..headers.addAll(_headers);
    if (body != null) req.body = jsonEncode(body);
    final res = await http.Response.fromStream(await _http.send(req).timeout(timeout));
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

  // ---- Awaaz Pehchaan: who is talking (owner / family), voice lock ----
  Future<Map<String, dynamic>> voiceId() async => Map<String, dynamic>.from(await _send('GET', '/api/voiceid') as Map);
  Future<void> voiceIdMode(String mode) async => _send('PUT', '/api/voiceid/mode', body: {'mode': mode});
  Future<Map<String, dynamic>> voiceIdEnrol(String name, String relation, {String? gender, String? level}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/voiceid/enrol', body: {
        'name': name, 'relation': relation, if (gender != null) 'gender': gender, if (level != null) 'level': level,
      }) as Map);
  Future<Map<String, dynamic>> voiceIdUpload(String enrolId, List<int> wav) async {
    final req = http.MultipartRequest('POST', _u('/api/voiceid/enrol/$enrolId'))
      ..files.add(http.MultipartFile.fromBytes('file', wav, filename: 'voice.wav'));
    if (apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer $apiKey';
    final res = await http.Response.fromStream(await req.send().timeout(const Duration(seconds: 90)));
    final text = utf8.decode(res.bodyBytes);
    if (res.statusCode >= 400) {
      var msg = 'Server error ${res.statusCode}';
      try {
        msg = (jsonDecode(text) as Map)['detail']?.toString() ?? msg;
      } catch (_) {}
      throw ApiException(res.statusCode, msg);
    }
    return Map<String, dynamic>.from(jsonDecode(text) as Map);
  }
  Future<Map<String, dynamic>> voiceIdUpdate(String id, {String? level, String? name}) async =>
      Map<String, dynamic>.from(await _send('PATCH', '/api/voiceid/members/$id', body: {
        if (level != null) 'level': level, if (name != null) 'name': name,
      }) as Map);
  Future<void> voiceIdDelete(String id) async => _send('DELETE', '/api/voiceid/members/$id');

  // ---- Hoola TV: free official live channels, on the phone or the TV ----
  Future<Map<String, dynamic>> tvChannels({String q = '', String category = '', String country = '', int offset = 0}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/tv/channels',
          query: {'q': q, 'category': category, 'country': country, 'offset': '$offset', 'limit': '90'}) as Map);
  Future<Map<String, dynamic>> tvChannel(String id) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/tv/channels/${Uri.encodeComponent(id)}') as Map);
  Future<Map<String, dynamic>> tvCast(String id, {String tv = ''}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/tv/cast', body: {'channel': id, 'tv': tv}, timeout: const Duration(seconds: 45)) as Map);
  Future<Map<String, dynamic>> tvStop() async =>
      Map<String, dynamic>.from(await _send('POST', '/api/tv/stop', timeout: const Duration(seconds: 30)) as Map);

  // ---- Hoola Reels ----
  Future<Map<String, dynamic>> reelLook(String text) async => Map<String, dynamic>.from(
      await _send('POST', '/api/reels/look', body: {'text': text}, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> reelLookFile(String name, List<int> bytes, {String text = ''}) =>
      uploadFile('/api/reels/look_file', name, bytes, fields: {'text': text}, timeout: const Duration(seconds: 180), tries: 2);
  Future<Map<String, dynamic>> reelGet(String id) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/reels/${Uri.encodeComponent(id)}') as Map);
  Future<List<Map<String, dynamic>>> reelsSaved({String q = ''}) async {
    final r = await _send('GET', '/api/reels', query: {'q': q}) as Map;
    return List<Map<String, dynamic>>.from((r['reels'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  }
  Future<Map<String, dynamic>> reelSave(String id, {String note = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/reels/$id/save', body: {'note': note}) as Map);
  Future<void> reelUnsave(String id) async => _send('DELETE', '/api/reels/$id/save');
  Future<Map<String, dynamic>> reelRemind(String id, String when, {String text = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/reels/$id/remind', body: {'when': when, 'text': text}) as Map);
  Future<Map<String, dynamic>> reelShop(String id, {List<String> items = const []}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/reels/$id/shop', body: {'items': items}) as Map);
  Future<String> reelShareText(String id) async => ((await _send('GET', '/api/reels/$id/share')) as Map)['text'] as String;
  Future<Map<String, dynamic>> reelCheck(String id) async => Map<String, dynamic>.from(
      await _send('POST', '/api/reels/$id/check', timeout: const Duration(seconds: 90)) as Map);

  // ---- Hoola Video Studio (v0.68) ----
  Future<Map<String, dynamic>> studioHome() async => Map<String, dynamic>.from(await _send('GET', '/api/studio') as Map);
  Future<Map<String, dynamic>> studioProject(String name) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/studio/projects/${Uri.encodeComponent(name)}') as Map);
  /// Her tap on a price card: only then does a paid AI generation start.
  Future<Map<String, dynamic>> studioDecide(String approvalId, bool yes) async => Map<String, dynamic>.from(
      await _send('POST', '/api/studio/approvals/$approvalId', body: {'yes': yes}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioAssemble(String name) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/studio/projects/${Uri.encodeComponent(name)}/assemble') as Map);

  // ---- Hoola Computer Operator (v0.67) ----
  Future<Map<String, dynamic>> operatorHome() async => Map<String, dynamic>.from(await _send('GET', '/api/operator') as Map);
  Future<Map<String, dynamic>> operatorTask(String id) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/operator/tasks/$id') as Map);
  Future<Map<String, dynamic>> operatorStart(String task, {String startUrl = '', List<String> fileIds = const [], String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/operator/tasks',
          body: {'task': task, 'start_url': startUrl, 'file_ids': fileIds, 'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> operatorCancel(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/operator/tasks/$id/cancel') as Map);
  /// Her answer to a request. For OTP / CAPTCHA / her secret, [answer] is typed straight into the page and never stored.
  Future<Map<String, dynamic>> operatorAnswer(String requestId, bool yes, {String answer = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/operator/requests/$requestId',
          body: {'status': yes ? 'approved' : 'rejected', 'answer': answer}, timeout: const Duration(seconds: 40)) as Map);
  /// Her own hands in the live view: tap at (x, y) in page pixels (1280 x 900), type text, or a key.
  Future<void> operatorInput(String kind, {double x = 0, double y = 0, String text = '', String key = ''}) async =>
      _send('POST', '/api/operator/input', body: {'kind': kind, 'x': x, 'y': y, 'text': text, 'key': key});
  Future<void> operatorForget(String name) async => _send('DELETE', '/api/operator/recipes/${Uri.encodeComponent(name)}');
  /// v0.76 the CAPTCHA picture of a waiting request (big, for her phone) and "naya CAPTCHA".
  Future<List<int>?> operatorCaptcha(String requestId) async {
    final req = http.Request('GET', _u('/api/operator/requests/$requestId/captcha'))..headers.addAll(_headers);
    final res = await http.Response.fromStream(await _http.send(req).timeout(const Duration(seconds: 15)));
    return res.statusCode == 200 && res.bodyBytes.isNotEmpty ? res.bodyBytes : null;
  }
  Future<bool> operatorCaptchaRefresh(String requestId) async =>
      ((await _send('POST', '/api/operator/requests/$requestId/captcha/refresh') as Map)['ok'] as bool?) ?? false;
  /// v0.78: ask Hoola to OCR-solve the CAPTCHA (returns the solved text).
  Future<String> operatorCaptchaSolve(String requestId) async =>
      (await _send('GET', '/api/operator/requests/$requestId/captcha/solve') as Map)['solved'] as String? ?? '';
  /// v0.78: fill the solved/corrected CAPTCHA into the page box.
  Future<Map<String, dynamic>> operatorCaptchaFill(String requestId, String value) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/operator/requests/$requestId/captcha/fill',
          body: {'value': value}) as Map);
  Future<List<int>?> operatorFrame() async {
    final req = http.Request('GET', _u('/api/operator/frame'))..headers.addAll(_headers);
    final res = await http.Response.fromStream(await _http.send(req).timeout(const Duration(seconds: 12)));
    return res.statusCode == 200 && res.bodyBytes.isNotEmpty ? res.bodyBytes : null;
  }

  // ---- Hoola Video Editor (v0.65) ----
  Future<Map<String, dynamic>> videoJobs() async => Map<String, dynamic>.from(await _send('GET', '/api/video/jobs') as Map);
  Future<Map<String, dynamic>> videoJob(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/video/jobs/$id') as Map);
  Future<Map<String, dynamic>> videoStart(List<String> fileIds, String brief,
          {String platform = 'reel', int? lengthS, bool captions = true, String logoFileId = '', String musicFileId = '',
          String title = '', String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/video/jobs', body: {
        'file_ids': fileIds, 'brief': brief, 'platform': platform, 'length_s': lengthS, 'captions': captions,
        'logo_file_id': logoFileId, 'music_file_id': musicFileId, 'title': title, 'conversation_id': conversationId,
      }, timeout: const Duration(seconds: 40)) as Map);
  Future<Map<String, dynamic>> videoRevise(String id, String instruction) async => Map<String, dynamic>.from(
      await _send('POST', '/api/video/jobs/$id/revise', body: {'instruction': instruction}) as Map);
  Future<Map<String, dynamic>> videoCancel(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/video/jobs/$id/cancel') as Map);

  // ---- Hoola Employee (v0.58) ----
  Map<String, dynamic> _em(Object? o) => Map<String, dynamic>.from(o as Map);
  Future<Map<String, dynamic>> employee() async => _em(await _send('GET', '/api/employee'));
  Future<Map<String, dynamic>> employeeSave(Map<String, dynamic> body) async => _em(await _send('PUT', '/api/employee', body: body));
  Future<Map<String, dynamic>> employeePause(bool paused) async =>
      _em(await _send('POST', '/api/employee/pause', body: {'paused': paused}));
  Future<Map<String, dynamic>> employeeAddMember(Map<String, dynamic> body) async =>
      _em(await _send('POST', '/api/employee/team', body: body));
  Future<Map<String, dynamic>> employeeEditMember(String id, Map<String, dynamic> body) async =>
      _em(await _send('PATCH', '/api/employee/team/$id', body: body));
  Future<void> employeeRemoveMember(String id) async => _send('DELETE', '/api/employee/team/$id');
  Future<Map<String, dynamic>> employeeTrust(String duty, {String? level, int? perDay}) async => _em(await _send(
      'PUT', '/api/employee/trust/$duty', body: {if (level != null) 'level': level, if (perDay != null) 'per_day': perDay}));
  Future<Map<String, dynamic>> employeeDecide(String askId, bool approve) async => _em(await _send(
      'POST', '/api/employee/asks/$askId', body: {'approve': approve}, timeout: const Duration(seconds: 90)));
  Future<List<Map<String, dynamic>>> employeeAudit({int limit = 100, String duty = ''}) async {
    final r = await _send('GET', '/api/employee/audit', query: {'limit': '$limit', 'duty': duty}) as Map;
    return List<Map<String, dynamic>>.from((r['entries'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  }
  Future<Map<String, dynamic>> employeeWrong(String entryId, String note) async =>
      _em(await _send('POST', '/api/employee/audit/$entryId/wrong', body: {'note': note}));
  Future<Map<String, dynamic>> employeeReport({String day = ''}) async =>
      _em(await _send('GET', '/api/employee/report', query: {'day': day}));
  Future<Map<String, dynamic>> employeeJobSheet() async => _em(await _send('GET', '/api/employee/job_sheet'));
  Future<Map<String, dynamic>> employeeSetJobSheet(String text) async =>
      _em(await _send('PUT', '/api/employee/job_sheet', body: {'text': text}));
  Future<List<Map<String, dynamic>>> employeeTasks() async {
    final r = await _send('GET', '/api/employee/tasks') as Map;
    return List<Map<String, dynamic>>.from((r['tasks'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  }

  // ---- Hoola Employee v0.59: business WhatsApp inbox ----
  List<Map<String, dynamic>> _eml(Object? o) =>
      List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> employeeInbox({String q = ''}) async => _em(await _send('GET', '/api/employee/inbox', query: {'q': q}));
  Future<Map<String, dynamic>> employeeThread(String id) async => _em(await _send('GET', '/api/employee/inbox/$id'));
  Future<Map<String, dynamic>> employeeSendTo(String id, String text) async =>
      _em(await _send('POST', '/api/employee/inbox/$id/send', body: {'text': text}, timeout: const Duration(seconds: 45)));
  Future<Map<String, dynamic>> employeeHuman(String id, bool human) async =>
      _em(await _send('POST', '/api/employee/inbox/$id/human', body: {'human': human}));
  Future<void> employeeAnswerNow(String id) async =>
      _send('POST', '/api/employee/inbox/$id/answer', timeout: const Duration(seconds: 90));
  Future<Map<String, dynamic>> employeeChannels() async => _em(await _send('GET', '/api/employee/channels'));
  Future<Map<String, dynamic>> employeeSetChannel(String pnid, String display, String token) async => _em(await _send(
      'PUT', '/api/employee/channels', body: {'phone_number_id': pnid, 'display_number': display, 'token': token}));
  Future<void> employeeRemoveChannel(String pnid) async => _send('DELETE', '/api/employee/channels/$pnid');
  Future<List<String>> employeeSlots({String date = '', int days = 3}) async {
    final r = await _send('GET', '/api/employee/slots', query: {'date': date, 'days': '$days'}) as Map;
    return List<String>.from((r['free'] as List).map((e) => '$e'));
  }
  Future<List<Map<String, dynamic>>> employeeAppointments({String day = ''}) async =>
      _eml((await _send('GET', '/api/employee/appointments', query: {'day': day}) as Map)['appointments']);
  Future<Map<String, dynamic>> employeeBook(String start, String name, String phone, String note) async => _em(await _send(
      'POST', '/api/employee/appointments', body: {'start': start, 'name': name, 'phone': phone, 'note': note}));
  Future<Map<String, dynamic>> employeeApptStatus(String id, String status) async =>
      _em(await _send('PATCH', '/api/employee/appointments/$id', body: {'status': status}));
  Future<Map<String, dynamic>> employeeDues({String status = ''}) async =>
      _em(await _send('GET', '/api/employee/dues', query: {'status': status}));
  Future<Map<String, dynamic>> employeeAddDue(Map<String, dynamic> body) async => _em(await _send('POST', '/api/employee/dues', body: body));
  Future<Map<String, dynamic>> employeeDueStatus(String id, String status) async =>
      _em(await _send('PATCH', '/api/employee/dues/$id', body: {'status': status}));
  Future<Map<String, dynamic>> employeeImportDues(String name, List<int> bytes) =>
      uploadFile('/api/employee/dues/import', name, bytes, timeout: const Duration(seconds: 60), tries: 2);

  // reel scroll analysis
  Future<Map<String, dynamic>> scrollSync(List<Map<String, dynamic>> days) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/reels/scroll/sync', body: {'days': days}) as Map);
  Future<Map<String, dynamic>> scrollReport({int days = 7}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/reels/scroll/report', query: {'days': '$days'}) as Map);
  Future<void> scrollBudget(int minutes) async => _send('POST', '/api/reels/scroll/budget', body: {'minutes': minutes});
  Future<Map<String, dynamic>> scrollImport(String name, List<int> bytes) =>
      uploadFile('/api/reels/scroll/import', name, bytes, timeout: const Duration(seconds: 400), tries: 2);
  Future<void> scrollForget() async => _send('DELETE', '/api/reels/scroll');

  /// v0.69 a crash report from the phone (stack trace / Android's exit record), so it can be fixed.
  Future<void> reportCrash(Map<String, dynamic> r) async => _send('POST', '/api/app/crash', body: {
        'kind': '${r['kind'] ?? ''}', 'text': '${r['text'] ?? ''}', 'during_call': r['during_call'] == true});
  // ---- Hoola Motion ----
  Future<Map<String, dynamic>> motionKinds() async => Map<String, dynamic>.from(await _send('GET', '/api/motion/kinds') as Map);
  Future<Map<String, dynamic>> motionPlan(String kind, String brief) async => Map<String, dynamic>.from(
      await _send('POST', '/api/motion/plan', body: {'kind': kind, 'brief': brief}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> motionMake(String kind, {Map<String, dynamic> data = const {}, String brief = '', String aspect = '9:16', String music = 'upbeat'}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/motion/videos',
          body: {'kind': kind, 'data': data, 'brief': brief, 'aspect': aspect, 'music': music}, timeout: const Duration(seconds: 40)) as Map);
  Future<List<Map<String, dynamic>>> motionList() async {
    final r = await _send('GET', '/api/motion/videos') as Map;
    return List<Map<String, dynamic>>.from((r['videos'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  }
  Future<Map<String, dynamic>> motionGet(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/motion/videos/$id') as Map);
  Future<void> motionDelete(String id) async => _send('DELETE', '/api/motion/videos/$id');
  Future<Map<String, dynamic>> motionYoutube(String id, {String title = '', String privacy = 'private'}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/motion/videos/$id/youtube', body: {'title': title, 'privacy': privacy}, timeout: const Duration(seconds: 90)) as Map);

  Future<Map<String, dynamic>> health() async => Map<String, dynamic>.from(await _send('GET', '/healthz'));

  Future<Map<String, dynamic>> me() async => Map<String, dynamic>.from(await _send('GET', '/api/me'));
  Future<void> disconnect(String provider) async => _send('DELETE', '/api/connections/$provider');
  Uri googleSignInUrl() => _u('/auth/google/start');
  Future<String> newConversation() async => (await _send('POST', '/api/conversations'))['id'] as String;
  Future<void> checkConversation(String id) async => _send('GET', '/api/conversations/$id/messages');
  /// Stop the task Hoola is running in this conversation (after the current step).
  Future<void> stopTurn(String id) async => _send('POST', '/api/conversations/$id/stop');
  /// Sends a message. A flaky mobile network is retried (same client_id, so the server runs it only once).
  /// Uploads one file (multipart) with retries on a bad network and plain-words errors, whatever the server or
  /// nginx answers (an HTML 404/413 page never shows up as "Not Found" / a JSON crash).
  Future<Map<String, dynamic>> uploadFile(String path, String filename, List<int> bytes,
      {Map<String, String> fields = const {}, Duration timeout = const Duration(seconds: 300), int tries = 3}) async {
    Object? last;
    for (var attempt = 0; attempt < tries; attempt++) {
      try {
        final req = http.MultipartRequest('POST', _u(path))
          ..fields.addAll(fields)
          ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
        if (apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer $apiKey';
        final res = await http.Response.fromStream(await req.send().timeout(timeout));
        dynamic body;
        try {
          body = jsonDecode(utf8.decode(res.bodyBytes));
        } catch (_) {
          body = null;
        }
        if (res.statusCode < 400 && body is Map) return Map<String, dynamic>.from(body);
        final detail = body is Map ? (body['detail']?.toString() ?? '') : '';
        final mb = (bytes.length / 1024 / 1024).toStringAsFixed(1);
        final msg = switch (res.statusCode) {
          404 when detail.isEmpty || detail == 'Not Found' =>
            'Server par file lene ka naya hissa abhi nahi hai — VPS ko latest version par update kijiye (git pull + pm2 restart).',
          413 => detail.isNotEmpty && detail != 'Request Entity Too Large'
              ? detail
              : 'File ($mb MB) server ne badi bataayi — VPS nginx mein client_max_body_size 30m kijiye.',
          401 || 403 => 'Server ne mana kiya (login / API key). App dobara kholiye.',
          502 || 503 || 504 => 'Server abhi jawab nahi de raha (restart ho raha hoga). Thodi der baad dobara.',
          _ => detail.isNotEmpty ? detail : 'Upload nahi hua (server ${res.statusCode}).',
        };
        if (res.statusCode >= 500 && attempt < tries - 1) {
          last = ApiException(res.statusCode, msg);
          await Future<void>.delayed(Duration(seconds: 2 + attempt * 2));
          continue;
        }
        throw ApiException(res.statusCode, msg);
      } on ApiException {
        rethrow;
      } on SocketException catch (e) {
        last = e;
      } on TimeoutException catch (e) {
        last = e;
      } on http.ClientException catch (e) {
        last = e;
      }
      if (attempt < tries - 1) await Future<void>.delayed(Duration(seconds: 2 + attempt * 2));
    }
    if (last is ApiException) throw last;
    throw ApiException(0, 'Network kamzor hai, file nahi gayi. Net check karke dobara bhejiye.');
  }

  /// v0.44.1 chat / call paperclip: any file; returns {file_id, name, url, media, preview, pages, leads?...}.
  Future<Map<String, dynamic>> chatFile(String conv, String filename, List<int> bytes) =>
      uploadFile('/api/conversations/$conv/files', filename, bytes);

  Future<void> sendMessage(String conv, String text, {bool voice = false, List<String> files = const []}) async {
    final id = '${DateTime.now().microsecondsSinceEpoch.toRadixString(36)}${math.Random().nextInt(1 << 30).toRadixString(36)}';
    Object? last;
    for (var i = 0; i < 3; i++) {
      try {
        await _send('POST', '/api/conversations/$conv/messages',
            body: {'text': text, 'client_id': id, if (voice) 'voice': true, if (files.isNotEmpty) 'files': files},
            timeout: const Duration(seconds: 20));
        return;
      } on ApiException catch (e) {
        if (e.status < 500) rethrow; // a refusal (wrong key, too long) will not change by asking again
        last = e;
      } on TimeoutException catch (e) {
        last = e;
      } on SocketException catch (e) {
        last = e;
      } on http.ClientException catch (e) {
        last = e;
      }
      if (i < 2) await Future.delayed(Duration(milliseconds: 800 * (i + 1)));
    }
    throw last ?? Exception('Message nahi gaya');
  }

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

  Future<Map<String, dynamic>> sendEmail(String id, {String? to, String? cc, String? bcc, String? subject, String? body, bool sendNow = false}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/emails/$id/send', timeout: const Duration(seconds: 90), body: {
        if (to != null) 'to': to, if (cc != null) 'cc': cc, if (bcc != null) 'bcc': bcc, if (subject != null) 'subject': subject,
        if (body != null) 'body': body, if (sendNow) 'send_now': true,
      }) as Map);

  Future<Map<String, dynamic>> addEmailAttachment(String id, String filename, List<int> bytes) async {
    final req = http.MultipartRequest('POST', _u('/api/emails/$id/attachments'))
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    if (apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer $apiKey';
    final res = await http.Response.fromStream(await req.send().timeout(const Duration(seconds: 200)));
    final body = jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) throw ApiException(res.statusCode, (body as Map)['detail']?.toString() ?? 'Upload failed');
    return Map<String, dynamic>.from(body as Map);
  }

  Future<Map<String, dynamic>> removeEmailAttachment(String id, int index) async =>
      Map<String, dynamic>.from(await _send('DELETE', '/api/emails/$id/attachments/$index') as Map);

  // ---- Google Sheets / Drive / Forms (each: accounts state, sign-in link, remove) ----
  Future<Map<String, dynamic>> _gState(String what) async => Map<String, dynamic>.from(await _send('GET', '/api/$what/accounts') as Map);
  Future<String> _gLink(String what) async => (await _send('GET', '/api/$what/link'))['url'] as String;
  Future<Map<String, dynamic>> _gRemove(String what, String key) async =>
      Map<String, dynamic>.from(await _send('DELETE', '/api/$what/accounts/$key') as Map);
  Future<Map<String, dynamic>> sheetsState() => _gState('sheets');
  Future<String> sheetsLinkUrl() => _gLink('sheets');
  Future<Map<String, dynamic>> sheetsRemove(String key) => _gRemove('sheets', key);
  Future<Map<String, dynamic>> driveState() => _gState('drive');
  // v0.70 why Google Drive / Gmail / Calendar do (not) work, with the fix
  Future<Map<String, dynamic>> googleStatus() async => Map<String, dynamic>.from(await _send('GET', '/api/google/status') as Map);
  Future<String> driveLinkUrl() => _gLink('drive');
  Future<Map<String, dynamic>> driveRemove(String key) => _gRemove('drive', key);
  Future<Map<String, dynamic>> formsState() => _gState('forms');
  Future<String> formsLinkUrl() => _gLink('forms');
  Future<Map<String, dynamic>> formsRemove(String key) => _gRemove('forms', key);
  Future<Map<String, dynamic>> slidesState() => _gState('slides');
  Future<String> slidesLinkUrl() => _gLink('slides');
  Future<Map<String, dynamic>> slidesRemove(String key) => _gRemove('slides', key);
  Future<Map<String, dynamic>> photosState() => _gState('photos');
  Future<String> photosLinkUrl() => _gLink('photos');
  Future<Map<String, dynamic>> photosRemove(String key) => _gRemove('photos', key);
  Future<Map<String, dynamic>> youtubeState() => _gState('youtube');
  Future<String> youtubeLinkUrl() => _gLink('youtube');
  Future<Map<String, dynamic>> youtubeRemove(String key) => _gRemove('youtube', key);

  // ---- Santosh Notebook (NotebookLM-style) ----
  Map<String, dynamic> _m(Object? o) => Map<String, dynamic>.from(o as Map);
  Future<List<Map<String, dynamic>>> notebooks() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/notebooks'))['notebooks'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> notebookCreate(String title) async => _m(await _send('POST', '/api/notebooks', body: {'title': title}));
  Future<Map<String, dynamic>> notebook(String id) async => _m(await _send('GET', '/api/notebooks/$id'));
  Future<void> notebookDelete(String id) async => _send('DELETE', '/api/notebooks/$id');
  Future<Map<String, dynamic>> notebookAddSource(String id, Map<String, dynamic> src) async =>
      _m(await _send('POST', '/api/notebooks/$id/sources', body: src, timeout: const Duration(seconds: 90)));
  Future<Map<String, dynamic>> notebookRemoveSource(String id, String sid) async => _m(await _send('DELETE', '/api/notebooks/$id/sources/$sid'));
  Future<Map<String, dynamic>> notebookUpload(String id, String filename, List<int> bytes) async {
    final req = http.MultipartRequest('POST', _u('/api/notebooks/$id/upload'))
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    if (apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer $apiKey';
    final res = await http.Response.fromStream(await req.send().timeout(const Duration(seconds: 200)));
    final body = jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) throw ApiException(res.statusCode, (body as Map)['detail']?.toString() ?? 'Upload failed');
    return Map<String, dynamic>.from(body as Map);
  }
  Future<Map<String, dynamic>> notebookAsk(String id, String q) async =>
      _m(await _send('POST', '/api/notebooks/$id/ask', body: {'question': q}, timeout: const Duration(seconds: 120)));
  Future<Map<String, dynamic>> notebookMake(String id, String kind, {String language = ''}) async =>
      _m(await _send('POST', '/api/notebooks/$id/make', body: {'kind': kind, 'language': language}, timeout: const Duration(seconds: 180)));
  Future<Map<String, dynamic>> notebookNote(String id, String noteId) async => _m(await _send('GET', '/api/notebooks/$id/notes/$noteId'));
  Future<Map<String, dynamic>> notebookAudio(String id, {String style = 'deep_dive', String language = 'hinglish', String conv = ''}) async =>
      _m(await _send('POST', '/api/notebooks/$id/audio', body: {'style': style, 'language': language, 'conversation_id': conv}));
  Future<String> notebookAudioUrl(String id, String aid) async =>
      absolute((await _send('GET', '/api/notebooks/$id/audio/$aid/file'))['url'] as String);

  // ---- Google Calendar ----
  Future<Map<String, dynamic>> calendarState() async => Map<String, dynamic>.from(await _send('GET', '/api/calendar/accounts') as Map);
  Future<String> calendarLinkUrl() async => (await _send('GET', '/api/calendar/link'))['url'] as String;
  Future<Map<String, dynamic>> calendarPrefs({List<String>? read, String? defaultCalendar, int? alertMinutes}) async =>
      Map<String, dynamic>.from(await _send('PATCH', '/api/calendar/prefs', body: {
        if (read != null) 'read_calendars': read, if (defaultCalendar != null) 'default_calendar': defaultCalendar,
        if (alertMinutes != null) 'alert_minutes': alertMinutes,
      }) as Map);
  Future<Map<String, dynamic>> calendarRemove(String key) async =>
      Map<String, dynamic>.from(await _send('DELETE', '/api/calendar/accounts/$key') as Map);

  // ---- mailboxes: Gmail / Outlook by sign-in, any email by app password ----
  Future<Map<String, dynamic>> mailAccounts() async => Map<String, dynamic>.from(await _send('GET', '/api/mail/accounts') as Map);
  Future<String> mailLinkUrl(String provider, {String hint = ''}) async =>
      (await _send('GET', '/api/mail/accounts/link', query: {'provider': provider, if (hint.isNotEmpty) 'login_hint': hint}))['url'] as String;
  Future<Map<String, dynamic>> mailConnectImap(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/mail/accounts/imap', body: body, timeout: const Duration(seconds: 70)) as Map);
  Future<Map<String, dynamic>> mailAccountEdit(String key, {String? signature, bool? makeDefault}) async =>
      Map<String, dynamic>.from(await _send('PATCH', '/api/mail/accounts/$key',
          body: {if (signature != null) 'signature': signature, if (makeDefault == true) 'default': true}) as Map);
  Future<Map<String, dynamic>> mailAccountRemove(String key) async =>
      Map<String, dynamic>.from(await _send('DELETE', '/api/mail/accounts/$key') as Map);

  Future<void> cancelEmail(String id) async => _send('POST', '/api/emails/$id/cancel');

  Future<List<Map<String, dynamic>>> reminders() async =>
      List<Map<String, dynamic>>.from((await _send('GET', '/api/reminders'))['reminders'] as List);
  Future<void> cancelReminder(String id) async => _send('POST', '/api/reminders/$id/cancel');

  Future<Map<String, dynamic>> lists() async => Map<String, dynamic>.from((await _send('GET', '/api/lists'))['lists'] as Map);
  Future<void> tickItem(int id) async => _send('POST', '/api/lists/items/$id/done');

  Future<List<Map<String, dynamic>>> memory() async =>
      List<Map<String, dynamic>>.from((await _send('GET', '/api/memory'))['facts'] as List);
  Future<void> forget(int id) async => _send('DELETE', '/api/memory/$id');
  /// "Hamesha yaad": pin / unpin a remembered fact (server refuses past its character limit).
  Future<void> pinMemory(int id, bool pinned) async => _send('PATCH', '/api/memory/$id', body: {'pinned': pinned});
  // ---- v0.75 Pehchaan Locker (Aadhaar / PAN / ID numbers, encrypted on the server) ----
  Future<Map<String, dynamic>> idList() async => Map<String, dynamic>.from(await _send('GET', '/api/ids') as Map);
  Future<Map<String, dynamic>> idSave({required String kind, required String number, String person = 'self', String note = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/ids', body: {'kind': kind, 'number': number, 'person': person, 'note': note}) as Map);
  Future<Map<String, dynamic>> idReveal(String id) async => Map<String, dynamic>.from(await _send('POST', '/api/ids/$id/reveal') as Map);
  Future<void> idDelete(String id) async => _send('DELETE', '/api/ids/$id');
  // ---- v0.63 seekhe hue kaam ----
  Future<List<Map<String, dynamic>>> procedures() async => List<Map<String, dynamic>>.from(
      ((await _send('GET', '/api/procedures') as Map)['procedures'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> procedureEdit(String id, {bool? active, String? title, List<String>? steps}) async =>
      Map<String, dynamic>.from(await _send('PATCH', '/api/procedures/$id',
          body: {if (active != null) 'active': active, if (title != null) 'title': title, if (steps != null) 'steps': steps}) as Map);
  Future<void> procedureDelete(String id) async => _send('DELETE', '/api/procedures/$id');
  // v0.80 Order karo
  Future<List<Map<String, dynamic>>> orderKaroList() async => List<Map<String, dynamic>>.from(
      ((await _send('GET', '/api/shop/orders') as Map)['orders'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<List<Map<String, dynamic>>> orderKaroSites() async => List<Map<String, dynamic>>.from(
      ((await _send('GET', '/api/shop/sites') as Map)['sites'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> orderKaroStart(String what, {String site = '', String budget = '', String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/shop/orders',
          body: {'what': what, 'site': site, 'budget': budget, 'conversation_id': conversationId}) as Map);
  // ---- v0.82 Darzi Sahayak (tailor / boutique coworker) ----
  List<Map<String, dynamic>> _maps(dynamic l) => List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> darziToday({String date = ''}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/darzi/today', query: {if (date.isNotEmpty) 'date': date}) as Map);
  Future<List<Map<String, dynamic>>> darziOrders({String status = 'open', String customer = ''}) async =>
      _maps((await _send('GET', '/api/darzi/orders', query: {'status': status, if (customer.isNotEmpty) 'customer': customer}) as Map)['orders']);
  Future<Map<String, dynamic>> darziOrder(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/darzi/orders/$id') as Map);
  Future<Map<String, dynamic>> darziNewOrder(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders', body: body) as Map);
  Future<Map<String, dynamic>> darziUpdateOrder(String id, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PATCH', '/api/darzi/orders/$id', body: body) as Map);
  Future<Map<String, dynamic>> darziStatus(String id, String status, {String note = '', String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders/$id/status',
          body: {'status': status, 'note': note, 'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> darziPay(String id, double amount, {String how = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders/$id/pay', body: {'amount': amount, 'how': how}) as Map);
  Future<Map<String, dynamic>> darziDeliver(String id, {double? paidNow, String note = '', String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders/$id/deliver',
          body: {'amount': paidNow, 'note': note, 'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> darziCancel(String id, {String reason = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders/$id/cancel', body: {'reason': reason}) as Map);
  Future<Map<String, dynamic>> darziSlip(String id, {String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders/$id/slip', body: {'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> darziReady(String id, {String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders/$id/ready', body: {'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> darziSendBusiness(String id, String text) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/orders/$id/send_business', body: {'text': text}) as Map);
  Future<void> darziTold(String id, String how) async => _send('POST', '/api/darzi/orders/$id/told', body: {'how': how});
  Future<List<Map<String, dynamic>>> darziCustomers({String q = ''}) async =>
      _maps((await _send('GET', '/api/darzi/customers', query: {if (q.isNotEmpty) 'q': q}) as Map)['customers']);
  Future<Map<String, dynamic>> darziCustomer(String id, {bool history = false}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/darzi/customers/$id', query: {if (history) 'history': 'true'}) as Map);
  Future<Map<String, dynamic>> darziAddCustomer(String name, String phone) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/customers', body: {'name': name, 'phone': phone}) as Map);
  Future<Map<String, dynamic>> darziMeasure(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/measures', body: body) as Map);
  Future<List<Map<String, dynamic>>> darziQuotes({String status = 'pending'}) async =>
      _maps((await _send('GET', '/api/darzi/quotes', query: {'status': status}) as Map)['quotes']);
  Future<Map<String, dynamic>> darziDecideQuote(String id, bool approve, {double? price, bool? toList}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/quotes/$id',
          body: {'approve': approve, if (price != null) 'price': price, if (toList != null) 'to_list': toList}) as Map);
  Future<Map<String, dynamic>> darziSettings() async => Map<String, dynamic>.from(await _send('GET', '/api/darzi/settings') as Map);
  Future<Map<String, dynamic>> darziSaveSettings(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/darzi/settings', body: body) as Map);
  Future<List<Map<String, dynamic>>> darziGarments() async => _maps((await _send('GET', '/api/darzi/garments') as Map)['garments']);
  Future<Map<String, dynamic>> darziCheck(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/darzi/check', body: body) as Map);
  // ---- v0.84 Galla + Chai Sahayak (chai stall coworker) ----
  Future<Map<String, dynamic>> gallaToday({String date = ''}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/galla/today', query: {if (date.isNotEmpty) 'date': date}) as Map);
  Future<Map<String, dynamic>> gallaHours({int days = 28}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/galla/hours', query: {'days': '$days'}) as Map);
  Future<List<Map<String, dynamic>>> gallaRecent() async => _maps((await _send('GET', '/api/galla/recent') as Map)['payments']);
  Future<Map<String, dynamic>> gallaCash(double amount, {String date = '', int? hour, String note = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/galla/cash',
          body: {'amount': amount, 'date': date, if (hour != null) 'hour': hour, 'note': note}) as Map);
  Future<void> gallaVoid(String id) async => _send('POST', '/api/galla/entries/$id/void');
  Future<Map<String, dynamic>> gallaStatement(String filename, List<int> bytes) async =>
      uploadFile('/api/galla/statement', filename, bytes, timeout: const Duration(seconds: 90));
  Future<Map<String, dynamic>> gallaSettings() async => Map<String, dynamic>.from(await _send('GET', '/api/galla/settings') as Map);
  Future<Map<String, dynamic>> gallaSaveSettings(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/galla/settings', body: body) as Map);
  Future<Map<String, dynamic>> chaiSettings() async => Map<String, dynamic>.from(await _send('GET', '/api/chai/settings') as Map);
  Future<Map<String, dynamic>> chaiSaveSettings(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/chai/settings', body: body) as Map);
  Future<Map<String, dynamic>> chaiStock({double? milkL, double? sugarKg, double? teaKg}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/chai/stock',
          body: {if (milkL != null) 'milk_l': milkL, if (sugarKg != null) 'sugar_kg': sugarKg, if (teaKg != null) 'tea_kg': teaKg}) as Map);
  Future<Map<String, dynamic>> chaiMakePlan({String forDate = '', String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/chai/plan', body: {'for_date': forDate, 'conversation_id': conversationId},
          timeout: const Duration(seconds: 40)) as Map);
  Future<Map<String, dynamic>?> chaiPlan({String date = ''}) async {
    final r = (await _send('GET', '/api/chai/plan', query: {if (date.isNotEmpty) 'date': date}) as Map)['plan'];
    return r == null ? null : Map<String, dynamic>.from(r as Map);
  }

  Future<Map<String, dynamic>> chaiDecide(String orderId, bool approve, {String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/chai/orders/$orderId',
          body: {'approve': approve, 'conversation_id': conversationId}, timeout: const Duration(seconds: 40)) as Map);
  Future<Map<String, dynamic>> chaiFeedback(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/chai/feedback', body: body) as Map);
  // v0.78 Pakka kaam: task log + lessons (failure -> what worked)
  Future<Map<String, dynamic>> agentTasks({int limit = 30}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/agent/tasks?limit=$limit') as Map);
  Future<List<Map<String, dynamic>>> agentLessons() async => List<Map<String, dynamic>>.from(
      ((await _send('GET', '/api/agent/lessons') as Map)['lessons'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<void> agentLessonDelete(String id) async => _send('DELETE', '/api/agent/lessons/$id');

  Future<Map<String, dynamic>> profile() async => Map<String, dynamic>.from(await _send('GET', '/api/profile'));
  Future<Map<String, dynamic>> saveProfile(Map<String, dynamic> p) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/profile', body: p));

  Future<List<Map<String, dynamic>>> pendingActions() async =>
      List<Map<String, dynamic>>.from((await _send('GET', '/api/device-actions/pending'))['actions'] as List);
  Future<void> actionResult(String id, bool ok, [String? detail]) async =>
      _send('POST', '/api/device-actions/$id/result', body: {'ok': ok, 'detail': detail});

  Future<Map<String, dynamic>> campaignAction(String id, String action) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/campaigns/$id/action', body: {'action': action}));

  Future<Map<String, dynamic>> catchup(DateTime since) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/catchup', query: {'since': since.toUtc().toIso8601String()}));

  Future<void> putLocation(double lat, double lng, {double? accuracy}) async =>
      _send('PUT', '/api/location', body: {'lat': lat, 'lng': lng, if (accuracy != null) 'accuracy_m': accuracy});

  // ---------------- Mera PC (Santosh Desktop) ----------------
  /// Absolute link for a server path like /api/pc/files/... (download links).
  String absolute(String path) => path.startsWith('http') ? path : _u(path).toString();
  Future<Map<String, dynamic>> pcPairStart() async => Map<String, dynamic>.from(await _send('POST', '/api/pc/pair/start'));
  Future<List<Map<String, dynamic>>> pcDevices() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/pc/devices'))['devices'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<void> pcRemove(String id) async => _send('DELETE', '/api/pc/devices/$id');
  Future<List<Map<String, dynamic>>> pcJobs() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/pc/jobs'))['jobs'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<List<Map<String, dynamic>>> pcSearch(String q, {String kind = 'any'}) async =>
      List<Map<String, dynamic>>.from(((await _send('POST', '/api/pc/search', body: {'query': q, 'kind': kind}, timeout: const Duration(seconds: 40)))['results'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> pcPull(String path) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/pc/pull', body: {'path': path}, timeout: const Duration(seconds: 200)));
  Future<Map<String, dynamic>> pcSend(String filename, List<int> bytes) async {
    final req = http.MultipartRequest('POST', _u('/api/pc/send'))
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    if (apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer $apiKey';
    final res = await http.Response.fromStream(await req.send().timeout(const Duration(seconds: 200)));
    final body = jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) throw ApiException(res.statusCode, (body as Map)['detail']?.toString() ?? 'Upload failed');
    return Map<String, dynamic>.from(body as Map);
  }

  /// v0.49 this phone maker's keep-alive steps (dontkillmyapp.com via our server).
  Future<Map<String, dynamic>> keepalive(String brand) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/device/keepalive', query: {'brand': brand}));
  /// v0.62 Newest GitHub APK release vs this app's version.
  Future<Map<String, dynamic>> appLatest(String current, {bool force = false}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/app/latest', query: {'current': current, if (force) 'force': 'true'}));
  /// v0.56 Sends Android's own background facts; answer = plain-word problems + this phone's checklist.
  Future<Map<String, dynamic>> bgHealth(Map<String, dynamic> report) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/device/bg_health', body: report));

  // ---------------- v0.47 Public APIs ----------------
  Future<Map<String, dynamic>> publicApis({String q = '', String cat = '', String auth = 'any'}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/publicapis', query: {'q': q, 'cat': cat, 'auth': auth, 'limit': '40'}));
  Future<Map<String, dynamic>> publicApiKey(String id, String key, {String place = 'query', String field = ''}) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/publicapis/${Uri.encodeComponent(id)}/key',
          body: {'key': key, 'place': place, 'field': field}));
  Future<void> publicApiKeyDelete(String id) async => _send('DELETE', '/api/publicapis/${Uri.encodeComponent(id)}/key');

  // ---------------- Hoola Network ----------------
  Map<String, dynamic> _hm(dynamic x) => Map<String, dynamic>.from(x as Map);
  List<Map<String, dynamic>> _hl(dynamic x) => List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> netMe() async => _hm(await _send('GET', '/api/net/me'));
  Future<Map<String, dynamic>> netSetMe({String? handle, bool? discoverable, String? phone}) async => _hm(await _send('PUT', '/api/net/me',
      body: {if (handle != null) 'handle': handle, if (discoverable != null) 'discoverable': discoverable, if (phone != null) 'phone': phone}));
  Future<Map<String, dynamic>> netInvite() async => _hm(await _send('POST', '/api/net/invite'));
  Future<List<Map<String, dynamic>>> netFind(String q) async => _hl((await _send('GET', '/api/net/find', query: {'q': q}))['results']);
  Future<Map<String, dynamic>> netConnect({String to = '', String invite = '', String relation = 'friend', String note = ''}) async =>
      _hm(await _send('POST', '/api/net/connect', body: {'to': to, 'invite': invite, 'relation': relation, 'note': note}));
  Future<List<Map<String, dynamic>>> netConnections() async => _hl((await _send('GET', '/api/net/connections'))['connections']);
  Future<Map<String, dynamic>> netAnswer(String linkId, String action, {String relation = ''}) async =>
      _hm(await _send('POST', '/api/net/connections/$linkId', body: {'action': action, 'relation': relation}));
  Future<Map<String, dynamic>> netUpdateLink(String linkId, Map<String, dynamic> body) async =>
      _hm(await _send('PATCH', '/api/net/connections/$linkId', body: body));
  Future<Map<String, dynamic>> netInbox() async => _hm(await _send('GET', '/api/net/inbox'));
  Future<Map<String, dynamic>> netDecide(String msgId, String action, {int? slot, int? minutes, String note = ''}) async =>
      _hm(await _send('POST', '/api/net/inbox/$msgId',
          body: {'action': action, if (slot != null) 'slot': slot, if (minutes != null) 'minutes': minutes, 'note': note}, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netSend(String to, String kind, Map<String, dynamic> body, {String threadId = ''}) async =>
      _hm(await _send('POST', '/api/net/send', body: {'to': to, 'kind': kind, 'body': body, 'thread_id': threadId}, timeout: const Duration(seconds: 60)));
  Future<List<Map<String, dynamic>>> netThreads() async => _hl((await _send('GET', '/api/net/threads'))['threads']);
  Future<Map<String, dynamic>> netThread(String id) async => _hm(await _send('GET', '/api/net/threads/$id'));
  /// v0.43 a real photo / video / PDF / any file into a Hoola chat (to = name / @handle, or the thread).
  Future<Map<String, dynamic>> netUpload(String filename, List<int> bytes, {String to = '', String threadId = '', String text = ''}) =>
      uploadFile('/api/net/upload', filename, bytes, fields: {'to': to, 'thread_id': threadId, 'text': text}, tries: 1);  // a retry could send it twice
  Future<Map<String, dynamic>> netMake(String kind, String title, String content) async =>
      _hm(await _send('POST', '/api/net/make', body: {'kind': kind, 'title': title, 'content': content}, timeout: const Duration(seconds: 120)));
  Future<Map<String, dynamic>> netThink(String msgId) async =>
      _hm(await _send('POST', '/api/net/messages/$msgId/think', timeout: const Duration(seconds: 120)));
  Future<Map<String, dynamic>> netHandle(String threadId, String action, {String goal = ''}) async =>
      _hm(await _send('POST', '/api/net/threads/$threadId/handle', body: {'action': action, 'goal': goal}, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netReply(String threadId, String text) async =>
      _hm(await _send('POST', '/api/net/threads/$threadId/reply', body: {'text': text}, timeout: const Duration(seconds: 60)));

  Future<List<Map<String, dynamic>>> netGroups() async => _hl((await _send('GET', '/api/net/groups'))['groups']);
  Future<Map<String, dynamic>> netGroupCreate(String name, List<String> members, {String emoji = ''}) async =>
      _hm(await _send('POST', '/api/net/groups', body: {'name': name, 'emoji': emoji, 'members': members}, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netGroup(String gid) async => _hm(await _send('GET', '/api/net/groups/$gid'));
  Future<Map<String, dynamic>> netGroupPost(String gid, Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/groups/$gid/post', body: body, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netGroupAct(String gid, String action, {String who = '', String mute = '', String answer = ''}) async =>
      _hm(await _send('POST', '/api/net/groups/$gid/act', body: {'action': action, 'who': who, 'mute': mute, 'answer': answer},
          timeout: const Duration(seconds: 90)));
  Future<Map<String, dynamic>> netGroupTask(String postId, String action) async =>
      _hm(await _send('POST', '/api/net/group-posts/$postId/task', body: {'action': action}));
  Future<Map<String, dynamic>> netGroupFile(String postId) async => _hm(await _send('POST', '/api/net/group-posts/$postId/file'));

  Future<Map<String, dynamic>> netLearned() async => _hm(await _send('GET', '/api/net/learned'));
  Future<Map<String, dynamic>> netLessonAct(String id, String action, {List<String> communities = const [], String text = ''}) async =>
      _hm(await _send('POST', '/api/net/learned/$id', body: {'action': action, 'communities': communities, 'text': text}, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netSkillAct(String id, String action) async => _hm(await _send('POST', '/api/net/skills/$id', body: {'action': action}));
  Future<Map<String, dynamic>> netSamaj({String q = ''}) async => _hm(await _send('GET', '/api/net/samaj', query: {'q': q}));
  Future<Map<String, dynamic>> netSamajCreate(Map<String, dynamic> body) async => _hm(await _send('POST', '/api/net/samaj', body: body));
  Future<Map<String, dynamic>> netSamajDetail(String cid, {String kind = ''}) async =>
      _hm(await _send('GET', '/api/net/samaj/$cid', query: {'kind': kind}));
  Future<Map<String, dynamic>> netSamajJoin(String cid) async => _hm(await _send('POST', '/api/net/samaj/$cid/join', timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netSamajPost(String cid, String kind, Map<String, dynamic> data) async =>
      _hm(await _send('POST', '/api/net/samaj/$cid/post', body: {'kind': kind, 'data': data}, timeout: const Duration(seconds: 90)));
  Future<Map<String, dynamic>> netSamajAct(String cid, Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/samaj/$cid/act', body: body, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netSamajItem(String iid, Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/samaj-items/$iid', body: body, timeout: const Duration(seconds: 60)));

  Future<Map<String, dynamic>> netBusiness() async => _hm(await _send('GET', '/api/net/business'));
  Future<Map<String, dynamic>> netBusinessPut(Map<String, dynamic> body) async => _hm(await _send('PUT', '/api/net/business', body: body));
  Future<Map<String, dynamic>> netBusinessVerify(String gstin) async => _hm(await _send('POST', '/api/net/business/verify', body: {'note': gstin}));
  Future<List<Map<String, dynamic>>> netBusinesses({String q = ''}) async => _hl((await _send('GET', '/api/net/businesses', query: {'q': q}))['businesses']);
  Future<Map<String, dynamic>> netBusinessContact(String business, String text, String kind) async =>
      _hm(await _send('POST', '/api/net/businesses/contact', body: {'business': business, 'text': text, 'kind': kind}, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netTicket(String number, {String status = '', String note = '', String to = ''}) async =>
      _hm(await _send('POST', '/api/net/tickets/$number', body: {'status': status, 'note': note, 'to': to}, timeout: const Duration(seconds: 60)));
  Future<List<Map<String, dynamic>>> netChains() async => _hl((await _send('GET', '/api/net/chains'))['chains']);
  Future<Map<String, dynamic>> netChainAct(String id, String action, {String to = '', String note = ''}) async =>
      _hm(await _send('POST', '/api/net/chains/$id', body: {'action': action, 'to': to, 'note': note}, timeout: const Duration(seconds: 60)));

  Future<Map<String, dynamic>> netOutbox(String id, String action) async =>
      _hm(await _send('POST', '/api/net/outbox/$id', body: {'action': action}, timeout: const Duration(seconds: 60)));

  // ---------------- Hoola avatar ----------------
  Future<Map<String, dynamic>> avatarGet() async => Map<String, dynamic>.from(await _send('GET', '/api/avatar'));
  Future<Map<String, dynamic>> avatarPut(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/avatar', body: body));
  Future<Map<String, dynamic>> avatarParseRules(String text) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/avatar/rules/parse', body: {'text': text}, timeout: const Duration(seconds: 60)));

  // ---------------- App Jaanch (REA static checks) ----------------
  Future<Map<String, dynamic>> appcheckState() async => Map<String, dynamic>.from(await _send('GET', '/api/appcheck'));
  Future<Map<String, dynamic>> appcheckGet(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/appcheck/$id'));
  Future<Map<String, dynamic>> appcheckUpload(String filename, List<int> bytes, {String conversationId = ''}) async {
    final req = http.MultipartRequest('POST', _u('/api/appcheck/upload'))
      ..fields['conversation_id'] = conversationId
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    if (apiKey.isNotEmpty) req.headers['Authorization'] = 'Bearer $apiKey';
    final res = await http.Response.fromStream(await req.send().timeout(const Duration(seconds: 420)));
    final body = jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) throw ApiException(res.statusCode, (body as Map)['detail']?.toString() ?? 'Jaanch nahi hui');
    return Map<String, dynamic>.from(body as Map);
  }

  // ---------------- MCP servers ----------------
  Future<List<Map<String, dynamic>>> mcpList() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/bazar/mcp'))['servers'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  /// What the avatar knows about each MCP server right now (status + tool names it can call).
  Future<List<Map<String, dynamic>>> mcpAvatar() async => List<Map<String, dynamic>>.from(
      ((await _send('GET', '/api/bazar/mcp/avatar', timeout: const Duration(seconds: 20)))['servers'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map)));
  // ---- Santosh Agent Army (open-source agents catalogue) ----
  Future<Map<String, dynamic>> agentsDirectory({String q = '', String field = '', String kind = '', String tier = ''}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/agents/directory',
          query: {'q': q, 'field': field, 'kind': kind, 'tier': tier, 'limit': '40'}));
  Future<Map<String, dynamic>> agentsFields() async => Map<String, dynamic>.from(await _send('GET', '/api/agents/fields'));
  Future<Map<String, dynamic>> agentItem(String ref) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/agents/item/${Uri.encodeComponent(ref)}'));

  Future<Map<String, dynamic>> mcpDirectory({String q = '', String field = ''}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/bazar/mcp/directory', query: {'q': q, 'field': field, 'limit': '30'}));
  Future<Map<String, dynamic>> mcpAdd(String url, {String name = '', String ref = '', String key = '', String header = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/mcp', body: {'url': url, 'name': name, 'ref': ref, 'key': key, 'key_header': header}));
  Future<Map<String, dynamic>> mcpKey(String packId, String key, {String header = ''}) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/bazar/mcp/$packId/key', body: {'key': key, 'header': header}));
  Future<void> mcpRemove(String packId) async => _send('DELETE', '/api/bazar/mcp/$packId');
  Future<List<Map<String, dynamic>>> mcpFeatured() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/bazar/mcp/featured'))['connectors'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> mcpConnectFeatured(String id, {String url = '', String key = '', String header = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/mcp/featured/$id', body: {'url': url, 'key': key, 'key_header': header},
          timeout: const Duration(seconds: 40)));

  // ---------------- Santosh Artifacts ----------------
  String _art(String id) => '/api/artifacts/${Uri.encodeComponent(id)}';

  // ---- Santosh Browser live view ----
  String _br(String sid) => '/api/browser/${Uri.encodeComponent(sid)}';
  Future<Map<String, dynamic>> browserLive(String sid) async =>
      Map<String, dynamic>.from(await _send('GET', '${_br(sid)}/live', timeout: const Duration(seconds: 12)));
  Future<void> browserStop(String sid) async => _send('POST', '${_br(sid)}/stop');

  /// The latest frame of the page Santosh's browser is on (JPEG), or null.
  Future<List<int>?> browserFrame(String sid) async {
    final req = http.Request('GET', _u('${_br(sid)}/frame'))..headers.addAll(_headers);
    final res = await http.Response.fromStream(await _http.send(req).timeout(const Duration(seconds: 12)));
    return res.statusCode == 200 && res.bodyBytes.isNotEmpty ? res.bodyBytes : null;
  }
  /// The user's artifacts. Older servers have none: returns an empty list.
  Future<List<Map<String, dynamic>>> artifacts() async {
    try {
      return List<Map<String, dynamic>>.from(((await _send('GET', '/api/artifacts'))['artifacts'] as List? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map)));
    } on ApiException catch (e) {
      if (e.status == 404) return [];
      rethrow;
    }
  }
  Future<Map<String, dynamic>> artifact(String id) async => Map<String, dynamic>.from(await _send('GET', _art(id)));
  /// Signed link (24h) to the page itself, always absolute.
  Future<String> artifactViewUrl(String id, {int? version}) async => absolute(
      (await _send('GET', '${_art(id)}/view', query: version == null ? null : {'version': '$version'}))['url'] as String? ?? '');
  Future<Map<String, dynamic>> artifactShare(String id, bool on) async =>
      Map<String, dynamic>.from(await _send('POST', '${_art(id)}/share', body: {'on': on}));
  Future<void> artifactDelete(String id) async => _send('DELETE', _art(id));
  Future<Map<String, dynamic>> artifactState(String id) async =>
      Map<String, dynamic>.from(((await _send('GET', '${_art(id)}/state'))['state'] as Map?) ?? const {});
  /// value null deletes the key.
  Future<void> artifactSetState(String id, String key, Object? value) async =>
      _send('PUT', '${_art(id)}/state', body: {'key': key, 'value': value});
  Future<String> artifactAsk(String id, String question) async =>
      ((await _send('POST', '${_art(id)}/ask', body: {'question': question}, timeout: const Duration(seconds: 90)))['answer'] as String?) ?? '';
  Future<Map<String, dynamic>> artifactRevise(String id, String request) async =>
      Map<String, dynamic>.from(await _send('POST', '${_art(id)}/revise', body: {'request': request}, timeout: const Duration(seconds: 40)));

  // ---------------- Santosh Bazar ----------------
  Future<Map<String, dynamic>> bazarDecide(String id, String decision) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/approvals/$id', body: {'decision': decision}));
  Future<List<Map<String, dynamic>>> bazarPending() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/bazar/approvals/pending'))['approvals'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> bazarCatalog() async => Map<String, dynamic>.from(await _send('GET', '/api/bazar/catalog'));
  Future<List<Map<String, dynamic>>> bazarApps() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/bazar/connections'))['apps'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<String> bazarLink(String packId) async => (await _send('POST', '/api/bazar/connections/$packId/link'))['url'] as String;
  /// Fresh signed link for a PDF Santosh made (invoice, salary slip, rent receipt, resume).
  Future<String> bazarFileUrl(String docId) async => absolute((await _send('GET', '/api/bazar/files/$docId/link'))['url'] as String);
  Future<void> bazarUnlink(String packId) async => _send('DELETE', '/api/bazar/connections/$packId');
  Future<Map<String, dynamic>> bazarSettings() async => Map<String, dynamic>.from(await _send('GET', '/api/bazar/settings'));
  Future<Map<String, dynamic>> saveBazarSettings(Map<String, dynamic> s) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/bazar/settings', body: s));
  Future<Map<String, dynamic>> bazarActivity() async => Map<String, dynamic>.from(await _send('GET', '/api/bazar/activity'));
  // Santosh Shopping: orders + tokens to connect Claude / ChatGPT to the Commerce MCP server
  Future<List<Map<String, dynamic>>> shopOrders() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/bazar/commerce/orders'))['orders'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> shopMcpTokens() async => Map<String, dynamic>.from(await _send('GET', '/api/bazar/commerce/mcp-tokens'));
  Future<Map<String, dynamic>> shopMcpTokenCreate(String label) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/commerce/mcp-tokens', body: {'label': label}));
  Future<void> shopMcpTokenRevoke(String id) async => _send('DELETE', '/api/bazar/commerce/mcp-tokens/$id');
  Future<List<Map<String, dynamic>>> bazarContacts() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/bazar/contacts'))['contacts'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> bazarCreateShop(Map<String, dynamic> shop) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/shops', body: shop));
  Future<void> bazarShopItems(String shopId, List<Map<String, dynamic>> items) async =>
      _send('POST', '/bazar/shops/$shopId/items', body: items);
  Future<void> bazarAddContact(String name, {String upi = '', String phone = ''}) async =>
      _send('POST', '/api/bazar/contacts', body: {'name': name, 'upi_id': upi, 'phone': phone});

  // ---- Ghar (home devices) ----
  Future<Map<String, dynamic>> homeDevices() async => Map<String, dynamic>.from(await _send('GET', '/api/bazar/devices'));
  Future<Map<String, dynamic>> homeAdd(String kind, String name, {String room = '', String brand = '', Map<String, dynamic>? target}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices',
          body: {'kind': kind, 'name': name, 'room': room, 'brand': brand, 'target': target ?? <String, dynamic>{}}));
  Future<void> homeRemove(String id) async => _send('DELETE', '/api/bazar/devices/$id');
  /// The test command for one AC remote type ({device_action, message}); the phone sends it and asks "did it beep?".
  Future<Map<String, dynamic>> homeIrTest(String id, String protocol) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices/$id/ir-test', body: {'protocol': protocol}));
  Future<Map<String, dynamic>> homeIrConfirm(String id, String protocol) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices/$id/ir-confirm', body: {'protocol': protocol}));
  Future<Map<String, dynamic>> homeTvTest(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices/$id/tv-test'));
  /// The phone reports whether it carried out a device command (IR AC state is saved only when ok).
  Future<Map<String, dynamic>> homeResult(String commandId, bool ok, [String error = '']) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices/commands/$commandId/result',
          body: {'ok': ok, 'error': error.length > 480 ? error.substring(0, 480) : error}));
  /// Answer to a Bluetooth job from Hoola (scan, pair, connect...).
  Future<Map<String, dynamic>> btResult(String requestId, bool ok, Map<String, dynamic> result, [String error = '']) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bt/requests/$requestId/result',
          body: {'ok': ok, 'result': result, 'error': error.length > 280 ? error.substring(0, 280) : error}));
  Future<Map<String, dynamic>> homeLinkStart(String provider) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices/link/$provider'));
  Future<Map<String, dynamic>> homeLinkLg(String token) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices/link/lg_thinq', body: {'token': token}, timeout: const Duration(seconds: 40)));
  Future<void> homeUnlink(String provider) async => _send('DELETE', '/api/bazar/devices/link/$provider');
  Future<Map<String, dynamic>> homeSync() async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/devices/sync', timeout: const Duration(seconds: 40)));

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
