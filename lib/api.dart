import 'dart:async';
import 'dart:convert';
import 'dart:io' show SocketException;
import 'dart:math' as math;

import 'package:http/http.dart' as http;

import 'native.dart';

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}

/// One event from the backend's live stream.
class SantoshEvent {
  SantoshEvent(this.id, this.kind, this.payload, this.at, {this.call, this.conv, this.key});
  final int id;
  final String kind;
  final Map<String, dynamic> payload;
  final DateTime at;
  final String? call;  // v0.158 the voice call whose tool made it (only those cards show in that call)
  final String? conv;  // the chat it was made in (cards from her other chats reach this one too)
  final String? key;   // one card = one key (timeline only)

  /// v0.158 the stream's own markers: catching up is over / reload the chat in order.
  bool get isMarker => id == 0 && (kind == 'replay_end' || kind == 'resync');

  static SantoshEvent fromJson(Map<String, dynamic> j) => SantoshEvent(
        (j['id'] as num?)?.toInt() ?? 0,
        j['kind'] as String? ?? '',
        Map<String, dynamic>.from(j['payload'] as Map? ?? {}),
        DateTime.tryParse(j['at'] as String? ?? '')?.toUtc() ?? DateTime.now().toUtc(),
        call: j['call'] as String?,
        conv: j['conv'] as String?,
        key: j['key'] as String?,
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

  /// Generic JSON call for feature screens (Seva suite and later): decoded JSON or an error with the server's detail.
  Future<dynamic> call(String method, String path, {Object? body, Map<String, String>? query, Duration? timeout}) =>
      _send(method, path, body: body, query: query, timeout: timeout ?? const Duration(seconds: 60));

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
  Future<Map<String, dynamic>> studioDecide(String approvalId, bool yes) async => Map<String, dynamic>.from(await _withFingerprint(
      'studio', approvalId, yes, (proof) => _send('POST', '/api/studio/approvals/$approvalId',
          body: {'yes': yes, if (proof != null) 'proof': proof}, timeout: const Duration(seconds: 60))) as Map);
  Future<Map<String, dynamic>> studioAssemble(String name) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/studio/projects/${Uri.encodeComponent(name)}/assemble') as Map);
  // v0.157 best model per shot: the app drives the whole studio too
  String _sp(String name) => '/api/studio/projects/${Uri.encodeComponent(name)}';
  Future<Map<String, dynamic>> studioNew(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/studio/projects', body: body, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioPlan(String name, String brief, int seconds) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/plan', body: {'brief': brief, 'seconds': seconds}) as Map);
  Future<Map<String, dynamic>> studioKeyframes(String name, {List<String>? shots}) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/keyframes', body: {'quality': 'final', 'shot_ids': shots}) as Map);
  Future<Map<String, dynamic>> studioGenerate(String name, String quality, {List<String>? shots, int variants = 1}) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/generate',
          body: {'quality': quality, 'shot_ids': shots, 'variants': variants}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioPick(String name, String shot, int take) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/pick', body: {'shot_id': shot, 'take': take}) as Map);
  Future<Map<String, dynamic>> studioShot(String name, String shot, Map<String, dynamic> changes) async =>
      Map<String, dynamic>.from(await _send('PATCH', '${_sp(name)}/shots/${Uri.encodeComponent(shot)}', body: changes) as Map);
  Future<Map<String, dynamic>> studioMusic(String name, String mood) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/music', body: {'mood': mood}) as Map);
  Future<Map<String, dynamic>> studioCharacter(String name, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/characters', body: body, timeout: const Duration(seconds: 60)) as Map);
  // v0.159 the full studio in the app
  Future<Map<String, dynamic>> studioSettings(String name, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/settings', body: body) as Map);
  Future<Map<String, dynamic>> studioAddShot(String name, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/shots', body: body) as Map);
  Future<Map<String, dynamic>> studioDeleteShot(String name, String shot) async =>
      Map<String, dynamic>.from(await _send('DELETE', '${_sp(name)}/shots/${Uri.encodeComponent(shot)}') as Map);
  Future<Map<String, dynamic>> studioRedo(String name, String shot, String change, {String quality = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/shots/${Uri.encodeComponent(shot)}/redo',
          body: {'change': change, 'quality': quality}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioLine(String name, String shot) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/shots/${Uri.encodeComponent(shot)}/line',
          timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioCancel(String name) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/cancel') as Map);
  Future<Map<String, dynamic>> studioLogo(String name, String fileId, String position) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/logo', body: {'file_id': fileId, 'position': position}) as Map);
  Future<Map<String, dynamic>> studioHide(String name) async =>
      Map<String, dynamic>.from(await _send('DELETE', _sp(name)) as Map);
  Future<Map<String, dynamic>> studioImprove(String brief, String language, int seconds) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/studio/improve',
          body: {'brief': brief, 'language': language, 'seconds': seconds}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioVoiceSample(String voice, String language) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/studio/voice_sample', query: {'voice': voice, 'language': language},
          timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioMusicMood(String name, String mood, {double volume = 0.25, String fileId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/music', body: {'mood': mood, 'volume': volume, 'file_id': fileId},
          timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> studioVoiceover(String name, String shot, String text) async =>
      Map<String, dynamic>.from(await _send('POST', '${_sp(name)}/voiceover', body: {'shot_id': shot, 'text': text},
          timeout: const Duration(seconds: 90)) as Map);

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
  Future<void> logout() async => _send('POST', '/api/logout');
  /// v0.98 everything the app needs to open, in one call (404 on an older server: the app falls back).
  Future<Map<String, dynamic>> bootstrap(String? conv, {bool fresh = false}) async => Map<String, dynamic>.from(
      await _send('GET', '/api/bootstrap', query: {if (conv != null && conv.isNotEmpty) 'conv': conv, if (fresh) 'new': 'true'},
          timeout: const Duration(seconds: 45)) as Map);   // v0.158.1 the first open after a server restart can be slow
  // ---- v0.158 the chat in order, old chats, self-check, call cards ----
  Future<Map<String, dynamic>> timeline(String conv, {int limit = 60, int before = 0}) async => Map<String, dynamic>.from(
      await _send('GET', '/api/conversations/$conv/timeline', query: {'limit': '$limit', if (before > 0) 'before': '$before'}) as Map);
  Future<Map<String, dynamic>> timelineHead(String conv, {int n = 40}) async => Map<String, dynamic>.from(
      await _send('GET', '/api/conversations/$conv/timeline/head', query: {'n': '$n'}) as Map);
  Future<Map<String, dynamic>> chats() async => Map<String, dynamic>.from(await _send('GET', '/api/conversations') as Map);
  Future<void> openChat(String conv) async => _send('POST', '/api/conversations/$conv/open');
  Future<void> chatHeal(String reason, Map<String, dynamic> data) async =>
      _send('POST', '/api/chat/heal', body: {'kind': 'resync', 'reason': reason, 'data': data});
  Future<Map<String, dynamic>> chatWaiting() async => Map<String, dynamic>.from(await _send('GET', '/api/chat/waiting') as Map);
  Future<Map<String, dynamic>> voiceCardRules() async => Map<String, dynamic>.from(await _send('GET', '/api/voice/card_rules') as Map);
  Future<void> voiceCallCards(String callId, String conv, List<Map<String, dynamic>> cards) async =>
      _send('POST', '/api/voice/calls/$callId/cards', body: {'conversation_id': conv, 'cards': cards});
  // ---- v0.98 Kharcha (AI cost) + call rating ----
  Future<Map<String, dynamic>> usageReport({int days = 30}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/usage', query: {'days': '$days'}) as Map);
  Future<Map<String, dynamic>> usageLimit(double inr) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/usage/limit', body: {'month_inr': inr}) as Map);
  // ---- v0.119 "<name> ne kya seekha": how she speaks, words misheard before, her words ----
  Future<Map<String, dynamic>> voiceLearned() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/voice/learned') as Map);
  Future<Map<String, dynamic>> voiceLearnSet(bool on) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/voice/learned', body: {'learn': on}) as Map);
  Future<Map<String, dynamic>> voiceForget(String part) async =>
      Map<String, dynamic>.from(await _send('DELETE', '/api/voice/learned', query: {'part': part}) as Map);
  Future<Map<String, dynamic>> voiceWordAdd(String term) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/voice/learned/words', body: {'term': term}) as Map);
  Future<void> voiceWordRemove(int id) async {
    await _send('DELETE', '/api/voice/learned/words/$id');
  }
  Future<Map<String, dynamic>> voiceFixAdd(String heard, String meant) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/voice/learned/fixes', body: {'heard': heard, 'meant': meant}) as Map);
  Future<void> voiceFixConfirm(int id) async {
    await _send('POST', '/api/voice/learned/fixes/$id/confirm');
  }
  Future<void> voiceFixRemove(int id) async {
    await _send('DELETE', '/api/voice/learned/fixes/$id');
  }
  Future<Map<String, dynamic>> rateCall(String callId, bool good, {List<String> reasons = const [], int seconds = 0}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/voice/calls/${Uri.encodeComponent(callId)}/rating',
          body: {'good': good, 'reasons': reasons, 'seconds': seconds}) as Map);

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

  // ---- Hoola Notebook (NotebookLM / Gemini Notebook): sources, cited chat, notes, Studio ----
  Map<String, dynamic> _m(Object? o) => Map<String, dynamic>.from(o as Map);
  List<Map<String, dynamic>> _ml(Object? o) => List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<List<Map<String, dynamic>>> notebooks() async => _ml((await _send('GET', '/api/notebooks'))['notebooks']);
  Future<Map<String, dynamic>> notebookCreate(String title, {String emoji = ''}) async =>
      _m(await _send('POST', '/api/notebooks', body: {'title': title, 'emoji': emoji}));
  Future<Map<String, dynamic>> notebook(String id) async => _m(await _send('GET', '/api/notebooks/$id'));
  Future<Map<String, dynamic>> notebookPatch(String id, {String title = '', String emoji = ''}) async =>
      _m(await _send('PATCH', '/api/notebooks/$id', body: {'title': title, 'emoji': emoji}));
  Future<void> notebookDelete(String id) async => _send('DELETE', '/api/notebooks/$id');
  Future<Map<String, dynamic>> notebookCopy(String id) async => _m(await _send('POST', '/api/notebooks/$id/copy', timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> notebookGuide(String id, {bool refresh = false}) async =>
      _m(await _send('GET', '/api/notebooks/$id/guide', query: {if (refresh) 'refresh': 'true'}, timeout: const Duration(seconds: 120)));
  Future<Map<String, dynamic>> notebookCatalogue() async => _m(await _send('GET', '/api/notebooks-catalogue'));
  // sources
  Future<Map<String, dynamic>> notebookAddSource(String id, Map<String, dynamic> src) async =>
      _m(await _send('POST', '/api/notebooks/$id/sources', body: src, timeout: const Duration(seconds: 180)));
  Future<Map<String, dynamic>> notebookUpload(String id, String filename, List<int> bytes, {String title = ''}) =>
      uploadFile('/api/notebooks/$id/upload', filename, bytes, fields: {if (title.isNotEmpty) 'title': title}, tries: 1);
  Future<Map<String, dynamic>> notebookSelect(String id, List<String>? ids, bool enabled, {bool only = false}) async =>
      _m(await _send('POST', '/api/notebooks/$id/sources/select', body: {'ids': ids, 'enabled': enabled, 'only': only}));
  Future<Map<String, dynamic>> notebookSource(String id, String sid) async => _m(await _send('GET', '/api/notebooks/$id/sources/$sid'));
  Future<Map<String, dynamic>> notebookSourceGuide(String id, String sid) async =>
      _m(await _send('GET', '/api/notebooks/$id/sources/$sid/guide', timeout: const Duration(seconds: 120)));
  Future<Map<String, dynamic>> notebookRenameSource(String id, String sid, String title) async =>
      _m(await _send('PATCH', '/api/notebooks/$id/sources/$sid', body: {'title': title}));
  Future<Map<String, dynamic>> notebookRefreshSource(String id, String sid) async =>
      _m(await _send('POST', '/api/notebooks/$id/sources/$sid/refresh', timeout: const Duration(seconds: 120)));
  Future<Map<String, dynamic>> notebookRemoveSource(String id, String sid) async => _m(await _send('DELETE', '/api/notebooks/$id/sources/$sid'));
  Future<Map<String, dynamic>> notebookDiscover(String id, String q) async =>
      _m(await _send('POST', '/api/notebooks/$id/discover', body: {'query': q}, timeout: const Duration(seconds: 90)));
  // chat
  Future<List<Map<String, dynamic>>> notebookChat(String id) async => _ml((await _send('GET', '/api/notebooks/$id/chat'))['messages']);
  Future<void> notebookClearChat(String id) async => _send('DELETE', '/api/notebooks/$id/chat');
  Future<Map<String, dynamic>> notebookConfig(String id, Map<String, String> cfg) async =>
      _m((await _send('PUT', '/api/notebooks/$id/chat/config', body: cfg))['chat_config']);
  Future<Map<String, dynamic>> notebookAsk(String id, String q, {List<String>? sources}) async =>
      _m(await _send('POST', '/api/notebooks/$id/ask', body: {'question': q, if (sources != null) 'sources': sources},
          timeout: const Duration(seconds: 180)));
  Future<Map<String, dynamic>> notebookSaveMessage(String id, String mid) async => _m(await _send('POST', '/api/notebooks/$id/chat/$mid/save'));
  // notes
  Future<Map<String, dynamic>> notebookNoteCreate(String id, String title, String content) async =>
      _m(await _send('POST', '/api/notebooks/$id/notes', body: {'title': title, 'content': content}));
  Future<Map<String, dynamic>> notebookNote(String id, String noteId) async => _m(await _send('GET', '/api/notebooks/$id/notes/$noteId'));
  Future<Map<String, dynamic>> notebookNoteUpdate(String id, String noteId, String title, String content) async =>
      _m(await _send('PATCH', '/api/notebooks/$id/notes/$noteId', body: {'title': title, 'content': content}));
  Future<void> notebookNoteDelete(String id, String noteId) async => _send('DELETE', '/api/notebooks/$id/notes/$noteId');
  Future<Map<String, dynamic>> notebookNoteToSource(String id, String noteId) async =>
      _m(await _send('POST', '/api/notebooks/$id/notes/$noteId/source', timeout: const Duration(seconds: 60)));
  // Studio
  Future<Map<String, dynamic>> notebookStudio(String id, String kind, Map<String, dynamic> options, {String conv = ''}) async =>
      _m(await _send('POST', '/api/notebooks/$id/studio', body: {'kind': kind, 'options': options, 'conversation_id': conv}));
  Future<Map<String, dynamic>> notebookOutput(String id, String oid) async => _m(await _send('GET', '/api/notebooks/$id/studio/$oid'));
  Future<Map<String, dynamic>> notebookOutputRename(String id, String oid, String title) async =>
      _m(await _send('PATCH', '/api/notebooks/$id/studio/$oid', body: {'title': title}));
  Future<void> notebookOutputDelete(String id, String oid) async => _send('DELETE', '/api/notebooks/$id/studio/$oid');
  Future<Map<String, dynamic>> notebookRevise(String id, String oid, List<Map<String, dynamic>> edits) async =>
      _m(await _send('POST', '/api/notebooks/$id/studio/$oid/revise', body: {'edits': edits}, timeout: const Duration(seconds: 300)));
  Future<Map<String, dynamic>> notebookJoin(String id, String oid, String q, {int at = 0}) async =>
      _m(await _send('POST', '/api/notebooks/$id/studio/$oid/join', body: {'question': q, 'at': at}, timeout: const Duration(seconds: 180)));
  Future<Map<String, dynamic>> notebookShare(String id, String oid, String name, {String conv = ''}) async =>
      _m(await _send('POST', '/api/notebooks/$id/studio/$oid/share', body: {'name': name, 'conversation_id': conv}));
  Future<List<Map<String, dynamic>>> notebookReportFormats(String id) async =>
      _ml((await _send('GET', '/api/notebooks/$id/studio-reports', timeout: const Duration(seconds: 120)))['formats']);
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

  Future<Map<String, dynamic>> lists() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/lists') as Map);   // v0.177: {lists, done_today}
  Future<void> tickItem(int id) async => _send('POST', '/api/lists/items/$id/done');
  Future<void> undoItem(int id) async => _send('POST', '/api/lists/items/$id/undo');   // v0.177: wapas list mein

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
  // ---- v0.85 Daftar Sahayak (office manager) ----
  Future<Map<String, dynamic>> officeAll() async => Map<String, dynamic>.from(await _send('GET', '/api/office') as Map);
  Future<Map<String, dynamic>> officeSettings(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('PUT', '/api/office/settings', body: body) as Map);
  Future<Map<String, dynamic>> officeItem(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/office/items', body: body) as Map);
  Future<Map<String, dynamic>> officeUse(String id, double qty) async => Map<String, dynamic>.from(await _send('POST', '/api/office/items/$id/use', body: {'qty': qty}) as Map);
  Future<Map<String, dynamic>> officeRestock(String id, double qty, {double? price}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/items/$id/restock', body: {'qty': qty, if (price != null) 'price': price}) as Map);
  Future<Map<String, dynamic>> officeReorder({String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/reorder', body: {'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> officeTicketNew(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/office/tickets', body: body) as Map);
  Future<Map<String, dynamic>> officeTicket(String id, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PATCH', '/api/office/tickets/$id', body: body) as Map);
  Future<Map<String, dynamic>> officeRenewal(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/office/renewals', body: body) as Map);
  Future<Map<String, dynamic>> officeRenewalDone(String id, {double? paid}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/renewals/$id/done', body: {if (paid != null) 'paid': paid}) as Map);
  Future<Map<String, dynamic>> officeRenewalPay(String id, {String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/renewals/$id/pay', body: {'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> officeDeadline(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/office/deadlines', body: body) as Map);
  Future<Map<String, dynamic>> officeDeadlineDone(String id, {bool dropped = false}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/deadlines/$id/done', body: {'dropped': dropped}) as Map);
  Future<Map<String, dynamic>> officeNudge({String deadline = '', String owner = '', String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/nudge', body: {'deadline': deadline, 'owner': owner, 'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> officePetty(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/office/petty', body: body) as Map);
  Future<Map<String, dynamic>> officeBill(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/office/bills', body: body) as Map);
  Future<Map<String, dynamic>> officeBillPaid(String id) async => Map<String, dynamic>.from(await _send('POST', '/api/office/bills/$id/paid', body: {}) as Map);
  Future<Map<String, dynamic>> officeDecideSpend(String id, bool approve, {double? amount}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/spends/$id', body: {'approve': approve, if (amount != null) 'amount': amount}) as Map);
  Future<Map<String, dynamic>> officeNote({bool file = false, String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/office/note', body: {'file': file, 'conversation_id': conversationId}) as Map);
  // ---- v0.87 Lekhak Sahayak (typist + translator) ----
  Future<Map<String, dynamic>> lekhakAll() async => Map<String, dynamic>.from(await _send('GET', '/api/lekhak') as Map);
  Future<Map<String, dynamic>> lekhakDoc(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/lekhak/docs/$id') as Map);
  Future<Map<String, dynamic>> lekhakWrite(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/write', body: body, timeout: const Duration(seconds: 150)) as Map);
  Future<Map<String, dynamic>> lekhakTranslate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/translate', body: body, timeout: const Duration(seconds: 200)) as Map);
  Future<Map<String, dynamic>> lekhakGrammar(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/grammar', body: body, timeout: const Duration(seconds: 120)) as Map);
  Future<Map<String, dynamic>> lekhakType(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/type', body: body, timeout: const Duration(seconds: 120)) as Map);
  Future<Map<String, dynamic>> lekhakKrutidev(String text, {bool toKrutidev = false}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/krutidev', body: {'text': text, 'to': toKrutidev ? 'krutidev' : 'unicode'}) as Map);
  Future<Map<String, dynamic>> lekhakRevise(String id, String instruction, {String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/docs/$id/revise', body: {'instruction': instruction, 'conversation_id': conversationId},
          timeout: const Duration(seconds: 120)) as Map);
  Future<Map<String, dynamic>> lekhakEdit(String id, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/lekhak/docs/$id', body: body) as Map);
  Future<Map<String, dynamic>> lekhakFiles(String id, {String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/docs/$id/files', body: {'conversation_id': conversationId}, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> lekhakSignRequest(String id, {String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/docs/$id/sign_request', body: {'conversation_id': conversationId}) as Map);
  Future<Map<String, dynamic>> lekhakSign(String id, bool approve, {String mode = 'paper', String hash = '', String conversationId = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/docs/$id/sign',
          body: {'approve': approve, 'mode': mode, 'hash': hash, 'conversation_id': conversationId}, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> lekhakCopy(String id) async => Map<String, dynamic>.from(await _send('POST', '/api/lekhak/docs/$id/copy', body: {}) as Map);
  Future<Map<String, dynamic>> lekhakShare(String id, {String phone = '', String email = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/lekhak/docs/$id/share', body: {'phone': phone, 'email': email}) as Map);
  Future<Map<String, dynamic>> lekhakContact(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/lekhak/contacts', body: body) as Map);
  Future<Map<String, dynamic>> lekhakSettings(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('PUT', '/api/lekhak/settings', body: body) as Map);
  // ---- v0.88 Mobile Dukaan Sahayak (recharge + repair shop) ----
  /// For Image.network on server photos (repair photos need the key).
  Map<String, String> get authHeaders => {if (apiKey.isNotEmpty) 'Authorization': 'Bearer $apiKey'};
  Future<Map<String, dynamic>> mshopToday() async => Map<String, dynamic>.from(await _send('GET', '/api/mshop/today') as Map);
  Future<List<Map<String, dynamic>>> mshopJobs({String status = 'open', String q = ''}) async =>
      _maps((await _send('GET', '/api/mshop/jobs', query: {'status': status, if (q.isNotEmpty) 'q': q}) as Map)['jobs']);
  Future<Map<String, dynamic>> mshopJob(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/mshop/jobs/$id') as Map);
  Future<Map<String, dynamic>> mshopNewJob(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/mshop/jobs', body: body) as Map);
  Future<Map<String, dynamic>> mshopCheck(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/mshop/check', body: body) as Map);
  Future<Map<String, dynamic>> mshopAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/mshop/jobs/$id/$action', body: body) as Map);
  Future<Map<String, dynamic>> mshopPhoto(String id, String filename, List<int> bytes, {String kind = 'in'}) async =>
      uploadFile('/api/mshop/jobs/$id/photos', filename, bytes, fields: {'kind': kind}, timeout: const Duration(seconds: 120));
  Future<Map<String, dynamic>> mshopWarranty(String q) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/mshop/warranty', query: {'q': q}) as Map);
  Future<Map<String, dynamic>> mshopRecharges() async => Map<String, dynamic>.from(await _send('GET', '/api/mshop/recharges') as Map);
  Future<Map<String, dynamic>> mshopAddRecharge(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/mshop/recharges', body: body) as Map);
  Future<void> mshopRechargeAct(String id, String action) async => _send('POST', '/api/mshop/recharges/$id/$action');
  // v0.90 Phone Doctor
  Future<List<Map<String, dynamic>>> phonedocIssues() async => _maps((await _send('GET', '/api/phonedoc/issues') as Map)['issues']);
  Future<Map<String, dynamic>> phonedocCheck(Map<String, dynamic> snapshot) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/phonedoc/check', body: {'snapshot': snapshot}) as Map);
  Future<Map<String, dynamic>> phonedocStart(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/phonedoc/cases', body: body) as Map);
  Future<List<Map<String, dynamic>>> phonedocCases({String status = ''}) async =>
      _maps((await _send('GET', '/api/phonedoc/cases', query: {if (status.isNotEmpty) 'status': status}) as Map)['cases']);
  Future<Map<String, dynamic>> phonedocCase(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/phonedoc/cases/$id') as Map);
  Future<Map<String, dynamic>> phonedocAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/phonedoc/cases/$id/$action', body: body) as Map);
  // v0.117 Theka Sahayak (contractor)
  Future<Map<String, dynamic>> thekaDay() async => Map<String, dynamic>.from(await _send('GET', '/api/theka/day') as Map);
  Future<Map<String, dynamic>> _tkPost(String path, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/theka/$path', body: body, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> thekaTender(Map<String, dynamic> body) => _tkPost('tenders', body);
  Future<Map<String, dynamic>> thekaProject(Map<String, dynamic> body) => _tkPost('projects', body);
  Future<Map<String, dynamic>> thekaProjectGet(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/theka/projects/$id') as Map);
  Future<Map<String, dynamic>> thekaProjectAct(String id, String action, Map<String, dynamic> body) => _tkPost('projects/$id/$action', body);
  Future<Map<String, dynamic>> thekaBill(String id, Map<String, dynamic> body) => _tkPost('bills/$id', body);
  Future<Map<String, dynamic>> thekaRegister() => _tkPost('register', const {});
  // v0.115 Franchise Sahayak
  Future<Map<String, dynamic>> frDay() async => Map<String, dynamic>.from(await _send('GET', '/api/franchise/day') as Map);
  Future<Map<String, dynamic>> frRead(String what, {String outlet = '', String month = ''}) async => Map<String, dynamic>.from(
      await _send('GET', '/api/franchise/$what', query: {if (outlet.isNotEmpty) 'outlet': outlet, if (month.isNotEmpty) 'month': month}) as Map);
  Future<Map<String, dynamic>> _frPost(String path, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/franchise/$path', body: body, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> frAgreement(Map<String, dynamic> body) => _frPost('agreements', body);
  Future<Map<String, dynamic>> frOutlet(Map<String, dynamic> body) => _frPost('outlets', body);
  Future<Map<String, dynamic>> frSale(Map<String, dynamic> body) => _frPost('sales', body);
  Future<Map<String, dynamic>> frCost(Map<String, dynamic> body) => _frPost('costs', body);
  Future<Map<String, dynamic>> frStatement(Map<String, dynamic> body) => _frPost('statements', body);
  Future<Map<String, dynamic>> frStatementAct(String id, String action) => _frPost('statements/$id/$action', const {});
  Future<Map<String, dynamic>> frLicence(Map<String, dynamic> body) => _frPost('licences', body);
  Future<Map<String, dynamic>> frAudit(Map<String, dynamic> body) => _frPost('audits', body);
  Future<Map<String, dynamic>> frPnlFile() => _frPost('pnl_file', const {});
  // v0.110 Niryat Sahayak (exporter)
  Future<Map<String, dynamic>> niryatDay() async => Map<String, dynamic>.from(await _send('GET', '/api/niryat/day') as Map);
  Future<List<Map<String, dynamic>>> niryatShipments({String status = ''}) async =>
      _maps((await _send('GET', '/api/niryat/shipments', query: {if (status.isNotEmpty) 'status': status}) as Map)['shipments']);
  Future<Map<String, dynamic>> niryatShipment(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/niryat/shipments/$id') as Map);
  Future<List<Map<String, dynamic>>> niryatBuyers() async => _maps((await _send('GET', '/api/niryat/buyers') as Map)['buyers']);
  Future<Map<String, dynamic>> niryatBuyer(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/niryat/buyers', body: body) as Map);
  Future<Map<String, dynamic>> niryatSettings(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/niryat/settings', body: body) as Map);
  Future<Map<String, dynamic>> niryatPi(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/niryat/shipments', body: body, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> niryatAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/niryat/shipments/$id/$action', body: body, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> niryatRegister() async => Map<String, dynamic>.from(await _send('POST', '/api/niryat/register', body: {}) as Map);
  // v0.107 Thok Sahayak (wholesale)
  Future<Map<String, dynamic>> thokDay() async => Map<String, dynamic>.from(await _send('GET', '/api/thok/day') as Map);
  Future<Map<String, dynamic>> thokRead(String what, {String route = ''}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/thok/$what', query: {if (route.isNotEmpty) 'route': route}) as Map);
  Future<List<Map<String, dynamic>>> thokParties() async => _maps((await _send('GET', '/api/thok/parties') as Map)['parties']);
  Future<List<Map<String, dynamic>>> thokItems() async => _maps((await _send('GET', '/api/thok/items') as Map)['items']);
  Future<List<Map<String, dynamic>>> thokOrders({String status = ''}) async =>
      _maps((await _send('GET', '/api/thok/orders', query: {if (status.isNotEmpty) 'status': status}) as Map)['orders']);
  Future<Map<String, dynamic>> thokGetOrder(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/thok/orders/$id') as Map);
  Future<Map<String, dynamic>> thokOrder(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/thok/orders', body: body) as Map);
  Future<Map<String, dynamic>> thokOrderAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/thok/orders/$id/$action', body: body, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> thokSettings(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/thok/settings', body: body) as Map);
  Future<Map<String, dynamic>> thokParty(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/thok/parties', body: body) as Map);
  Future<Map<String, dynamic>> thokItem(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/thok/items', body: body) as Map);
  Future<Map<String, dynamic>> thokReceive(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/thok/receive', body: body) as Map);
  // v0.103 SEO Sahayak
  Future<Map<String, dynamic>> seoSummary() async => Map<String, dynamic>.from(await _send('GET', '/api/seo/summary') as Map);
  Future<Map<String, dynamic>> seoSite(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/seo/site', body: body) as Map);
  Future<Map<String, dynamic>> seoAct(String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/seo/$action', body: body, timeout: const Duration(seconds: 180)) as Map);
  Future<Map<String, dynamic>> seoTask(String id, String status) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/seo/tasks/$id', body: {'status': status}) as Map);
  Future<List<Map<String, dynamic>>> seoDrafts() async => _maps((await _send('GET', '/api/seo/drafts') as Map)['drafts']);
  Future<Map<String, dynamic>> seoDraftOk(String id, String text) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/seo/drafts/$id', body: {'text': text}) as Map);
  Future<String> seoGscLink() async => (await _send('GET', '/api/seo/gsc/link'))['url'] as String;
  // v0.98 Bima Sahayak
  Future<Map<String, dynamic>> insSummary({int days = 15}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/insurance/summary', query: {'days': '$days'}) as Map);
  Future<Map<String, dynamic>> insReminders({int days = 15}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/insurance/reminders', query: {'days': '$days'}) as Map);
  Future<List<Map<String, dynamic>>> insClients() async => _maps((await _send('GET', '/api/insurance/clients') as Map)['clients']);
  Future<Map<String, dynamic>> insClientSave(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/insurance/clients', body: body) as Map);
  Future<Map<String, dynamic>> insNeeds(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/insurance/clients/$id/needs') as Map);
  Future<List<Map<String, dynamic>>> insPolicies({String client = '', String state = ''}) async => _maps((await _send('GET', '/api/insurance/policies',
      query: {if (client.isNotEmpty) 'client': client, if (state.isNotEmpty) 'state': state}) as Map)['policies']);
  Future<Map<String, dynamic>> insPolicySave(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/insurance/policies', body: body) as Map);
  Future<Map<String, dynamic>> insPaid(String id) async => Map<String, dynamic>.from(await _send('POST', '/api/insurance/policies/$id/paid', body: {}) as Map);
  Future<Map<String, dynamic>> insReminded(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/insurance/policies/$id/reminded', body: {}) as Map);
  Future<Map<String, dynamic>> insImport(String filename, List<int> bytes) async => uploadFile('/api/insurance/import', filename, bytes);
  Future<Map<String, dynamic>> insAdvice(String id, bool approve) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/insurance/advice/$id', body: {'approve': approve}) as Map);
  Future<Map<String, dynamic>> insBookFile() async => Map<String, dynamic>.from(await _send('POST', '/api/insurance/book_file', body: {}) as Map);
  // v0.96 Auditor's Assistant
  Future<List<Map<String, dynamic>>> audEngagements() async => _maps((await _send('GET', '/api/audit/engagements') as Map)['engagements']);
  Future<Map<String, dynamic>> audNew(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/audit/engagements', body: body) as Map);
  Future<Map<String, dynamic>> audGet(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/audit/engagements/$id') as Map);
  Future<Map<String, dynamic>> audUpload(String id, String what, String filename, List<int> bytes) async =>
      uploadFile('/api/audit/engagements/$id/upload/$what', filename, bytes);
  Future<List<Map<String, dynamic>>> audFindings(String id) async => _maps((await _send('GET', '/api/audit/engagements/$id/findings') as Map)['findings']);
  Future<Map<String, dynamic>> audAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/audit/engagements/$id/$action', body: body) as Map);
  Future<Map<String, dynamic>> audClose(String fid, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/audit/findings/$fid', body: body) as Map);
  // v0.95 Financial Analyst
  Future<Map<String, dynamic>> finAnalysis({String snapshot = ''}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/finance/analysis', query: {if (snapshot.isNotEmpty) 'snapshot': snapshot}) as Map);
  Future<Map<String, dynamic>> finBooks(String label, String start, String end, String filename, List<int> bytes) async =>
      uploadFile('/api/finance/books', filename, bytes, fields: {'label': label, 'start': start, 'end': end});
  Future<Map<String, dynamic>> finBank(String filename, List<int> bytes, {String account = ''}) async =>
      uploadFile('/api/finance/bank', filename, bytes, fields: {'account': account});
  Future<Map<String, dynamic>> finCash() async => Map<String, dynamic>.from(await _send('GET', '/api/finance/cash') as Map);
  Future<Map<String, dynamic>> finAging(String kind) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/finance/aging', query: {'kind': kind}) as Map);
  Future<Map<String, dynamic>> finAddItem(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/finance/items', body: body) as Map);
  Future<Map<String, dynamic>> finLoanCheck(double amount, double rate, double years) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/finance/loan_check', body: {'amount': amount, 'rate': rate, 'years': years}) as Map);
  Future<Map<String, dynamic>> finAct(String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/finance/act/$action', body: body) as Map);
  // v0.94 Payroll Officer
  Future<Map<String, dynamic>> payToday() async => Map<String, dynamic>.from(await _send('GET', '/api/payroll/today') as Map);
  Future<List<Map<String, dynamic>>> payEmployees() async => _maps((await _send('GET', '/api/payroll/employees') as Map)['employees']);
  Future<Map<String, dynamic>> paySaveEmployee(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/payroll/employees', body: body) as Map);
  Future<Map<String, dynamic>> payAttendance(String period, List<Map<String, dynamic>> entries) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/payroll/attendance', body: {'period': period, 'entries': entries}) as Map);
  Future<Map<String, dynamic>> payImportAttendance(String period, String filename, List<int> bytes) async =>
      uploadFile('/api/payroll/attendance/import', filename, bytes, fields: {'period': period});
  Future<List<Map<String, dynamic>>> payRuns() async => _maps((await _send('GET', '/api/payroll/runs') as Map)['runs']);
  Future<Map<String, dynamic>> payMakeRun(String period) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/payroll/runs', body: {'period': period}) as Map);
  Future<Map<String, dynamic>> payRun(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/payroll/runs/$id') as Map);
  Future<Map<String, dynamic>> payRunAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/payroll/runs/$id/$action', body: body) as Map);
  Future<Map<String, dynamic>> paySettings() async => Map<String, dynamic>.from(await _send('GET', '/api/payroll/settings') as Map);
  Future<Map<String, dynamic>> paySaveSettings(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/payroll/settings', body: body) as Map);
  // v0.93 GST Sahayak
  Future<Map<String, dynamic>> gstToday() async => Map<String, dynamic>.from(await _send('GET', '/api/gst/today') as Map);
  Future<List<Map<String, dynamic>>> gstClients() async => _maps((await _send('GET', '/api/gst/clients') as Map)['clients']);
  Future<Map<String, dynamic>> gstSaveClient(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/gst/clients', body: body) as Map);
  Future<List<Map<String, dynamic>>> gstBills(String client, {String period = '', String direction = ''}) async =>
      _maps((await _send('GET', '/api/gst/bills', query: {'client': client, if (period.isNotEmpty) 'period': period,
          if (direction.isNotEmpty) 'direction': direction}) as Map)['bills']);
  Future<Map<String, dynamic>> gstImport(String client, String direction, String period, String filename, List<int> bytes) async =>
      uploadFile('/api/gst/import', filename, bytes, fields: {'client': client, 'direction': direction, 'period': period});
  Future<Map<String, dynamic>> gstImport2b(String client, String period, String filename, List<int> bytes) async =>
      uploadFile('/api/gst/2b', filename, bytes, fields: {'client': client, 'period': period});
  Future<Map<String, dynamic>> gstReconcile(String client, String period) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/gst/reconcile', query: {'client': client, 'period': period}) as Map);
  Future<Map<String, dynamic>> gstIms(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/gst/ims', body: body) as Map);
  Future<List<Map<String, dynamic>>> gstReturns({String client = '', String status = ''}) async =>
      _maps((await _send('GET', '/api/gst/returns', query: {if (client.isNotEmpty) 'client': client, if (status.isNotEmpty) 'status': status}) as Map)['returns']);
  Future<Map<String, dynamic>> gstPrepare(String client, String period, String kind) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/gst/returns', body: {'client': client, 'period': period, 'kind': kind}) as Map);
  Future<Map<String, dynamic>> gstReturn(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/gst/returns/$id') as Map);
  Future<Map<String, dynamic>> gstReturnAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/gst/returns/$id/$action', body: body) as Map);
  Future<Map<String, dynamic>> gstDraft(String client, String period, {String kind = 'ask_bills'}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/gst/drafts', body: {'client': client, 'period': period, 'kind': kind}) as Map);
  Future<List<Map<String, dynamic>>> gstNotices({String status = 'open'}) async =>
      _maps((await _send('GET', '/api/gst/notices', query: {'status': status}) as Map)['notices']);
  Future<Map<String, dynamic>> gstAddNotice(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/gst/notices', body: body) as Map);
  Future<Map<String, dynamic>> gstNoticeAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/gst/notices/$id/$action', body: body) as Map);
  Future<Map<String, dynamic>> mshopSettings() async => Map<String, dynamic>.from(await _send('GET', '/api/mshop/settings') as Map);
  Future<Map<String, dynamic>> mshopSaveSettings(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/mshop/settings', body: body) as Map);
  // ---- v0.111 Ads Sahayak (performance marketer; ad money only on her tap) ----
  Future<Map<String, dynamic>> adsAll() async => Map<String, dynamic>.from(await _send('GET', '/api/ads', timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> adsReport(int days) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/ads/report', query: {'days': '$days'}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> adsImport(String filename, List<int> bytes, {String platform = ''}) async =>
      uploadFile('/api/ads/import', filename, bytes, fields: {if (platform.isNotEmpty) 'platform': platform}, tries: 1);
  Future<Map<String, dynamic>> adsPlan({int days = 14, double extra = 0}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/ads/plan', body: {'days': days, 'extra': extra}, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> adsChanges() async => Map<String, dynamic>.from(await _send('GET', '/api/ads/changes') as Map);
  Future<Map<String, dynamic>> adsDecide(String id, bool yes, {double? after}) async => Map<String, dynamic>.from(await _withFingerprint(
      'ads', id, yes, (proof) => _send('POST', '/api/ads/changes/$id/decide',
          body: {'yes': yes, if (after != null) 'after': after, if (proof != null) 'proof': proof}, timeout: const Duration(seconds: 60))) as Map);
  Future<Map<String, dynamic>> adsDone(String id) async => Map<String, dynamic>.from(await _send('POST', '/api/ads/changes/$id/done') as Map);
  Future<Map<String, dynamic>> adsCopies(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/ads/copies', body: body, timeout: const Duration(seconds: 120)) as Map);
  Future<Map<String, dynamic>> adsTestAct(String id, String action, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/ads/tests/$id/$action', body: body) as Map);
  Future<Map<String, dynamic>> adsSale(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/ads/sales', body: body) as Map);
  Future<Map<String, dynamic>> adsSettings(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('PUT', '/api/ads/settings', body: body) as Map);
  Future<Map<String, dynamic>> adsMeta(String account, String token) async => Map<String, dynamic>.from(
      await _send('PUT', '/api/ads/meta', body: {'account': account, 'token': token}, timeout: const Duration(seconds: 45)) as Map);
  Future<Map<String, dynamic>> adsMetaOff() async => Map<String, dynamic>.from(await _send('DELETE', '/api/ads/meta') as Map);
  Future<Map<String, dynamic>> adsMetaFetch(int days) async => Map<String, dynamic>.from(
      await _send('POST', '/api/ads/meta/fetch', body: {'days': days}, timeout: const Duration(seconds: 120)) as Map);
  // ---- v0.121 Website Sahayak (plan, 3 looks, live build board, checks, preview) ----
  Future<Map<String, dynamic>> siteAll() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/sites', timeout: const Duration(seconds: 45)) as Map);
  Future<Map<String, dynamic>> siteNew(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/sites', body: body, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> siteGet(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/sites/$id') as Map);
  Future<Map<String, dynamic>> siteAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/sites/$id/$action', body: body, timeout: const Duration(seconds: 120)) as Map);
  Future<Map<String, dynamic>> siteDelete(String id) async => Map<String, dynamic>.from(await _send('DELETE', '/api/sites/$id') as Map);
  Future<Map<String, dynamic>> sitePhoto(String id, String filename, List<int> bytes, String about) async =>
      uploadFile('/api/sites/$id/photo', filename, bytes, fields: {'about': about}, tries: 1, timeout: const Duration(seconds: 180));
  Future<Map<String, dynamic>> siteLibrary({String industry = '', String q = '', int offset = 0}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/sites-library', query: {'industry': industry, 'q': q, 'offset': '$offset'}) as Map);
  Future<List<Map<String, dynamic>>> siteLeads(String id) async => List<Map<String, dynamic>>.from(
      (((await _send('GET', '/api/sites/$id/leads')) as Map)['leads'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  // ---- v0.128 App Sahayak (every screen designed + tap-through prototype before the build) ----
  Future<Map<String, dynamic>> appAll() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/apps', timeout: const Duration(seconds: 45)) as Map);
  Future<Map<String, dynamic>> appNew(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/apps', body: body, timeout: const Duration(seconds: 60)) as Map);
  // ---- v0.136 the 1 crore app idea list ----
  Future<Map<String, dynamic>> appIdeas({String q = '', String field = '', int offset = 0, int limit = 20}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/apps-ideas',
          query: {'q': q, 'field': field, 'offset': '$offset', 'limit': '$limit'}, timeout: const Duration(seconds: 45)) as Map);
  Future<Map<String, dynamic>> appGet(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/apps/$id') as Map);
  Future<Map<String, dynamic>> appAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/apps/$id/$action', body: body, timeout: const Duration(seconds: 120)) as Map);
  Future<Map<String, dynamic>> appDelete(String id) async => Map<String, dynamic>.from(await _send('DELETE', '/api/apps/$id') as Map);
  // ---- v0.132 the native Android build (Kotlin + Compose, APK on her phone, project ZIP) ----
  Future<Map<String, dynamic>> appAndroid(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/apps/$id/android') as Map);
  // ---- v0.131 complex apps: blueprint (data model, roles, levels, login, phone features) + schema files ----
  Future<Map<String, dynamic>> appBlueprint(String id) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/apps/$id/blueprint') as Map);
  Future<String> appBlueprintText(String id, String name) async {
    final req = http.Request('GET', _u('/api/apps/$id/blueprint/$name'))..headers.addAll(_headers);
    final res = await http.Response.fromStream(await _http.send(req).timeout(const Duration(seconds: 30)));
    if (res.statusCode >= 400) throw ApiException(res.statusCode, 'Server error ${res.statusCode}');
    return utf8.decode(res.bodyBytes);
  }
  Future<Map<String, dynamic>> appCatalog(String kind, {String q = ''}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/apps-catalog/$kind', query: {'q': q}) as Map);
  Future<Map<String, dynamic>> appLibrary({String industry = '', String q = '', int offset = 0}) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/apps-library', query: {'industry': industry, 'q': q, 'offset': '$offset'}) as Map);
  // ---- v0.122 Website hosting: launch / rollback / domain / DNS / her keys ----
  Future<Map<String, dynamic>> siteHosting(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/sites/$id/hosting') as Map);
  Future<Map<String, dynamic>> siteDns(String planId, String action, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/sites-dns/$planId/$action', body: body, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> siteDnsCheck(String planId) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/sites-dns/$planId/check', timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> siteKeySet(String provider, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/sites-keys/$provider', body: body, timeout: const Duration(seconds: 40)) as Map);
  Future<Map<String, dynamic>> siteKeyForget(String provider) async =>
      Map<String, dynamic>.from(await _send('DELETE', '/api/sites-keys/$provider') as Map);
  // ---- v0.123 Domains: ideas + rupee prices, buy only on her fingerprint tap ----
  Future<Map<String, dynamic>> siteDomains() async => Map<String, dynamic>.from(await _send('GET', '/api/sites-domains') as Map);
  Future<Map<String, dynamic>> siteDomainIdeas(String site, {String name = '', String city = ''}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/sites-domains/ideas', body: {'site': site, 'name': name, 'city': city}, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> siteDomainCheck(List<String> domains) async => Map<String, dynamic>.from(
      await _send('POST', '/api/sites-domains/check', body: {'domains': domains}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> siteDomainRequest(String site, String domain, {bool autoRenew = false}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/sites-domains/request', body: {'site': site, 'domain': domain, 'auto_renew': autoRenew},
          timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> siteDomainBuy(String id, String hash) async => Map<String, dynamic>.from(await _withFingerprint(
      'domain', id, true, (proof) => _send('POST', '/api/sites-domains/$id/buy',
          body: {'hash': hash, if (proof != null) 'proof': proof}, timeout: const Duration(seconds: 90))) as Map);
  Future<Map<String, dynamic>> siteDomainCancel(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/sites-domains/$id/cancel') as Map);
  Future<Map<String, dynamic>> siteDomainKyc(String domain) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/sites-domains/kyc', body: {'domain': domain}) as Map);
  // ---- v0.124 Website care, agency, GitHub export ----
  Future<Map<String, dynamic>> siteCare(String id, {int days = 30}) async => Map<String, dynamic>.from(
      await _send('GET', '/api/sites/$id/care', query: {'days': '$days'}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> siteClients() async => Map<String, dynamic>.from(await _send('GET', '/api/sites-clients') as Map);
  Future<Map<String, dynamic>> siteAssign(String id, {String? client, String? staff}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/sites/$id/assign', body: {if (client != null) 'client': client, if (staff != null) 'staff': staff}) as Map);
  Future<Map<String, dynamic>> siteGithubRequest(String id, {String repo = '', bool private = true}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/sites/$id/github-request', body: {'repo': repo, 'private': private}, timeout: const Duration(seconds: 60)) as Map);
  Future<Map<String, dynamic>> siteGithubPush(String id, String hash) async => Map<String, dynamic>.from(
      await _send('POST', '/api/sites-github/$id/push', body: {'hash': hash}, timeout: const Duration(seconds: 180)) as Map);
  Future<Map<String, dynamic>> siteGithubCancel(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/sites-github/$id/cancel') as Map);
  // ---- v0.118 Brand Sahayak (brand designer; final artwork only on her tap) ----
  // v0.127 Hoola Screen (view-only live board)
  Future<Map<String, dynamic>> screenLink() async => Map<String, dynamic>.from(await _send('GET', '/api/screen/link') as Map);
  Future<Map<String, dynamic>> screenRevoke() async => Map<String, dynamic>.from(await _send('POST', '/api/screen/revoke') as Map);
  Future<Map<String, dynamic>> screenPreview() async => Map<String, dynamic>.from(await _send('GET', '/api/screen/preview') as Map);
  Future<Map<String, dynamic>> brandAll() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/brand', timeout: const Duration(seconds: 45)) as Map);
  Future<Map<String, dynamic>> brandMake(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/brand/designs', body: body, timeout: const Duration(seconds: 180)) as Map);
  Future<Map<String, dynamic>> brandDesign(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/brand/designs/$id') as Map);
  Future<Map<String, dynamic>> brandAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/brand/designs/$id/$action', body: body, timeout: const Duration(seconds: 240)) as Map);
  Future<Map<String, dynamic>> brandDelete(String id) async => Map<String, dynamic>.from(await _send('DELETE', '/api/brand/designs/$id') as Map);
  Future<Map<String, dynamic>> brandPhoto(String id, String filename, List<int> bytes) async =>
      uploadFile('/api/brand/designs/$id/photo', filename, bytes, tries: 1, timeout: const Duration(seconds: 180));
  Future<Map<String, dynamic>> brandKitSave(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/brand/kit', body: body) as Map);
  Future<Map<String, dynamic>> brandLogo(String filename, List<int> bytes, {bool cleanBg = false}) async =>
      uploadFile('/api/brand/logo', filename, bytes, fields: {'clean_bg': cleanBg ? 'true' : 'false'}, tries: 1);
  /// Proof / final picture bytes (they need the key, so Image.network gets authHeaders; downloads come through here).
  Future<List<int>> brandBytes(String path) async {
    final res = await http.get(Uri.parse(absolute(path)), headers: authHeaders).timeout(const Duration(seconds: 120));
    if (res.statusCode != 200) throw 'File nahi mili (${res.statusCode})';
    return res.bodyBytes;
  }
  // ---- v0.101 Kalam Sahayak (content writer; publishing only on her tap) ----
  Future<Map<String, dynamic>> kalamAll() async => Map<String, dynamic>.from(await _send('GET', '/api/kalam') as Map);
  Future<Map<String, dynamic>> kalamWrite(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/kalam/write', body: body, timeout: const Duration(seconds: 180)) as Map);
  Future<Map<String, dynamic>> kalamPiece(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/kalam/pieces/$id') as Map);
  Future<Map<String, dynamic>> kalamEdit(String id, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('PUT', '/api/kalam/pieces/$id', body: body, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> kalamDelete(String id) async => Map<String, dynamic>.from(await _send('DELETE', '/api/kalam/pieces/$id') as Map);
  Future<Map<String, dynamic>> kalamDo(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/kalam/pieces/$id/$action', body: body, timeout: const Duration(seconds: 180)) as Map);
  Future<Map<String, dynamic>> kalamIdeas() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/kalam/ideas', timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> kalamSettings(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('PUT', '/api/kalam/settings', body: body) as Map);
  Future<Map<String, dynamic>> kalamFact(String fact, String source) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/kalam/facts', body: {'fact': fact, 'source': source}) as Map);
  Future<Map<String, dynamic>> kalamVoice(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/kalam/voice', body: body, timeout: const Duration(seconds: 120)) as Map);
  Future<Map<String, dynamic>> kalamWordpress(String url, String user, String appPassword) async => Map<String, dynamic>.from(
      await _send('PUT', '/api/kalam/wordpress', body: {'url': url, 'user': user, 'app_password': appPassword}, timeout: const Duration(seconds: 45)) as Map);
  Future<Map<String, dynamic>> kalamWordpressOff() async => Map<String, dynamic>.from(await _send('DELETE', '/api/kalam/wordpress') as Map);
  // ---- v0.99 Telecaller Sahayak (a person makes every call) ----
  Future<Map<String, dynamic>> teleAll() async => Map<String, dynamic>.from(await _send('GET', '/api/telecall') as Map);
  Future<List<Map<String, dynamic>>> teleLeads({String q = '', String stage = ''}) async =>
      _maps((await _send('GET', '/api/telecall/leads', query: {if (q.isNotEmpty) 'q': q, if (stage.isNotEmpty) 'stage': stage}) as Map)['leads']);
  Future<Map<String, dynamic>> teleLead(String id) async => Map<String, dynamic>.from(await _send('GET', '/api/telecall/leads/$id') as Map);
  Future<Map<String, dynamic>> teleAdd(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('POST', '/api/telecall/leads', body: body) as Map);
  Future<Map<String, dynamic>> teleImport(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/telecall/import', body: body, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> teleUpdate(String id, Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('PATCH', '/api/telecall/leads/$id', body: body) as Map);
  Future<Map<String, dynamic>> teleScript(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/telecall/leads/$id/script', timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> teleStart(String id) async => Map<String, dynamic>.from(await _send('POST', '/api/telecall/leads/$id/call', body: {}) as Map);
  Future<Map<String, dynamic>> teleLogCall(String callId, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/telecall/calls/$callId/log', body: body, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> teleLogLead(String id, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/telecall/leads/$id/log', body: body, timeout: const Duration(seconds: 90)) as Map);
  Future<Map<String, dynamic>> teleDnd(String id, {bool wrong = false}) async => Map<String, dynamic>.from(await _send('POST', '/api/telecall/leads/$id/dnd', body: {'wrong': wrong}) as Map);
  Future<Map<String, dynamic>> teleForget(String id) async => Map<String, dynamic>.from(await _send('DELETE', '/api/telecall/leads/$id') as Map);
  Future<Map<String, dynamic>> teleReport(int days) async => Map<String, dynamic>.from(await _send('GET', '/api/telecall/report', query: {'days': '$days'}) as Map);
  Future<Map<String, dynamic>> teleSettings(Map<String, dynamic> body) async => Map<String, dynamic>.from(await _send('PUT', '/api/telecall/settings', body: body) as Map);
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

  /// v0.166 Aaj ka Din premium card: weather + today's remaining meetings + next reminder, one call.
  Future<Map<String, dynamic>> day() async => Map<String, dynamic>.from(await _send('GET', '/api/day') as Map);

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
  // ---- v0.102 Hoola Deals (buy / sell between avatars) ----
  Future<List<Map<String, dynamic>>> netDeals({String state = '', String role = ''}) async =>
      _hl((await _send('GET', '/api/net/deals', query: {'state': state, 'role': role}))['deals']);
  Future<Map<String, dynamic>> netDeal(String id) async => _hm(await _send('GET', '/api/net/deals/$id'));
  Future<Map<String, dynamic>> netDealAsk(String to, List<Map<String, dynamic>> items, {String mode = 'pickup', String note = ''}) async =>
      _hm(await _send('POST', '/api/net/deals', body: {'to': to, 'items': items, 'mode': mode, 'note': note}, timeout: const Duration(seconds: 60)));
  /// Her taps on a deal card. `confirm` places the order: fingerprint-signed once a phone is set up (428 -> sign -> again).
  Future<Map<String, dynamic>> netDealAct(String id, String action, [Map<String, dynamic> body = const {}]) async {
    if (action == 'confirm') {
      return Map<String, dynamic>.from(await _withFingerprint('deal', id, true, (proof) => _send('POST', '/api/net/deals/$id/confirm',
          body: {...body, if (proof != null) 'proof': proof}, timeout: const Duration(seconds: 60))) as Map);
    }
    return _hm(await _send('POST', '/api/net/deals/$id/$action', body: body, timeout: const Duration(seconds: 60)));
  }
  Future<Map<String, dynamic>> netStock({String q = ''}) async => _hm(await _send('GET', '/api/net/stock', query: {'q': q}));
  Future<Map<String, dynamic>> netStockPut(List<Map<String, dynamic>> items) async =>
      _hm(await _send('PUT', '/api/net/stock', body: {'items': items}));
  Future<void> netStockDelete(String id) async => _send('DELETE', '/api/net/stock/$id');
  Future<Map<String, dynamic>> netDealRulesPut(Map<String, dynamic> body) async => _hm(await _send('PUT', '/api/net/deal_rules', body: body));
  // ---- v0.113 services and bookings ----
  Future<Map<String, dynamic>> netBook(Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/bookings', body: body, timeout: const Duration(seconds: 60)));
  Future<List<Map<String, dynamic>>> netBookings({String role = ''}) async =>
      _hl((await _send('GET', '/api/net/bookings', query: {'role': role}))['bookings']);
  Future<Map<String, dynamic>> netServiceRules() async => _hm(await _send('GET', '/api/net/service_rules'));
  Future<Map<String, dynamic>> netServiceRulesPut(Map<String, dynamic> body) async =>
      _hm(await _send('PUT', '/api/net/service_rules', body: body));
  Future<Map<String, dynamic>> netDealPhoto(String id, String filename, List<int> bytes, {String stage = 'after'}) async =>
      uploadFile('/api/net/deals/$id/photo', filename, bytes, fields: {'stage': stage}, timeout: const Duration(seconds: 120));
  // ---- v0.112 compare quotes, trust tiers, standing orders, offers ----
  Future<Map<String, dynamic>> netRfqStart(Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/rfqs', body: body, timeout: const Duration(seconds: 90)));
  Future<List<Map<String, dynamic>>> netRfqs({bool all = false}) async =>
      _hl((await _send('GET', '/api/net/rfqs', query: {'all': '$all'}))['compares']);
  Future<Map<String, dynamic>> netRfq(String id) async => _hm(await _send('GET', '/api/net/rfqs/$id'));
  Future<Map<String, dynamic>> netRfqAct(String id, String action, {bool on = true}) async =>
      _hm(await _send('POST', '/api/net/rfqs/$id/$action', body: {'on': on}, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> netTrust(String to) async => _hm(await _send('GET', '/api/net/trust', query: {'to': to}));
  Future<Map<String, dynamic>> netTrustSet(String to, String level) async =>
      _hm(await _send('PUT', '/api/net/trust', body: {'to': to, 'level': level}));
  Future<Map<String, dynamic>> netTrustReport(String to, String reason, {String kind = ''}) async =>
      _hm(await _send('POST', '/api/net/trust/report', body: {'to': to, 'reason': reason, 'kind': kind}));
  Future<List<Map<String, dynamic>>> netMandates() async => _hl((await _send('GET', '/api/net/mandates'))['standing_orders']);
  Future<Map<String, dynamic>> netMandateCreate(Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/mandates', body: body));
  /// sign / resume = her tap that turns the rule on (fingerprint once a phone is set up); pause / stop / run.
  Future<Map<String, dynamic>> netMandateAct(String id, String action) async {
    if (action == 'sign' || action == 'resume') {
      return Map<String, dynamic>.from(await _withFingerprint('mandate', id, true, (proof) => _send('POST', '/api/net/mandates/$id/$action',
          body: {if (proof != null) 'proof': proof}, timeout: const Duration(seconds: 60))) as Map);
    }
    return _hm(await _send('POST', '/api/net/mandates/$id/$action', body: const {}, timeout: const Duration(seconds: 60)));
  }
  Future<Map<String, dynamic>> netPromos() async => _hm(await _send('GET', '/api/net/promos'));
  Future<Map<String, dynamic>> netPromoAudience() async => _hm(await _send('GET', '/api/net/promos/audience'));
  Future<Map<String, dynamic>> netPromoAct(String action, Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/promos/$action', body: body, timeout: const Duration(seconds: 90)));
  Future<Map<String, dynamic>> netPromoItem(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      _hm(await _send('POST', '/api/net/promos/$id/$action', body: body, timeout: const Duration(seconds: 60)));
  // ---- v0.160 Hoola Dosti: free talk, work diary, doc requests, friends' skills ----
  Future<Map<String, dynamic>> dosti() async => _hm(await _send('GET', '/api/net/dosti', timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> dostiSet(Map<String, dynamic> body) async => _hm(await _send('PUT', '/api/net/dosti', body: body));
  Future<Map<String, dynamic>> dostiAct(String action, Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/dosti/$action', body: body, timeout: const Duration(seconds: 90)));
  Future<Map<String, dynamic>> dostiThread(String threadId, String action) async =>
      _hm(await _send('POST', '/api/net/dosti/threads/$threadId/$action', body: const {}));
  Future<Map<String, dynamic>> dostiDiary(String id, Map<String, dynamic> body) async =>
      _hm(await _send('PATCH', '/api/net/dosti/diary/$id', body: body));
  Future<Map<String, dynamic>> dostiVideo(String id, String action, [String to = '']) async =>
      _hm(await _send('POST', '/api/net/dosti/diary/$id/$action', body: {'to': to}, timeout: const Duration(seconds: 90)));
  Future<Map<String, dynamic>> dostiDoc(String askId, String action, [String fileId = '']) async =>
      _hm(await _send('POST', '/api/net/dosti/docs/$askId', body: {'action': action, 'file_id': fileId}, timeout: const Duration(seconds: 90)));
  Future<Map<String, dynamic>> dostiItem(String itemId, String action) async =>
      _hm(await _send('POST', '/api/net/dosti/items/$itemId', body: {'action': action}));
  // ---- v0.116 A2A 1.0 (outside AI agents), AA / ABDM consent hand-offs, DigiLocker requester, ONDC listing ----
  Future<Map<String, dynamic>> a2aHome() async => _hm(await _send('GET', '/api/a2a'));
  Future<Map<String, dynamic>> a2aMode(String mode) async => _hm(await _send('PUT', '/api/a2a/mode', body: {'mode': mode}));
  /// her taps on an outside agent's request: reply / quote / accept / reject / ready / handed_over / cancel
  Future<Map<String, dynamic>> a2aTaskAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      _hm(await _send('POST', '/api/a2a/tasks/$id/$action', body: body, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> a2aDiscover(String url) async =>
      _hm(await _send('POST', '/api/a2a/discover', body: {'url': url}, timeout: const Duration(seconds: 40)));
  Future<Map<String, dynamic>> a2aOutNew(Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/a2a/out', body: body, timeout: const Duration(seconds: 40)));
  /// send (her tap) / drop / poll a message to an outside agent
  Future<Map<String, dynamic>> a2aOutAct(String id, String action) async =>
      _hm(await _send('POST', '/api/a2a/out/$id/$action', body: const {}, timeout: const Duration(seconds: 40)));
  Future<Map<String, dynamic>> handoff() async => _hm(await _send('GET', '/api/handoff'));
  Future<Map<String, dynamic>> handoffReview(String rail, Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/handoff/$rail/review', body: body));
  Future<Map<String, dynamic>> handoffMark(String rail, String id, String status) async =>
      _hm(await _send('POST', '/api/handoff/$rail/$id/mark', body: {'status': status}));
  Future<Map<String, dynamic>> handoffForget(String rail, String id) async => _hm(await _send('DELETE', '/api/handoff/$rail/$id'));
  Future<Map<String, dynamic>> abdmHelp(String topic) async =>
      _hm(await _send('GET', '/api/handoff/abdm/help', query: {'topic': topic}));
  Future<Map<String, dynamic>> digilocker() async => _hm(await _send('GET', '/api/digilocker'));
  Future<Map<String, dynamic>> digilockerStart([String doctype = '']) async =>
      _hm(await _send('POST', '/api/digilocker/start', body: {'doctype': doctype}));
  Future<Map<String, dynamic>> digilockerFetch(String uri) async =>
      _hm(await _send('POST', '/api/digilocker/fetch', body: {'uri': uri}, timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> digilockerOff() async => _hm(await _send('DELETE', '/api/digilocker'));
  Future<Map<String, dynamic>> ondc() async => _hm(await _send('GET', '/api/ondc'));
  Future<Map<String, dynamic>> ondcSetup(Map<String, dynamic> body) async => _hm(await _send('PUT', '/api/ondc', body: body));
  Future<Map<String, dynamic>> ondcItem(Map<String, dynamic> body) async => _hm(await _send('PUT', '/api/ondc/items', body: body));
  Future<Map<String, dynamic>> ondcExport() async =>
      _hm(await _send('POST', '/api/ondc/export', body: const {}, timeout: const Duration(seconds: 60)));
  // ---- v0.106 khata (udhaar) between Hoolas ----
  Future<Map<String, dynamic>> netKhata() async => _hm(await _send('GET', '/api/net/khata'));
  Future<Map<String, dynamic>> netKhataAct(String action, Map<String, dynamic> body) async =>
      _hm(await _send('POST', '/api/net/khata/$action', body: body, timeout: const Duration(seconds: 60)));
  // ---- v0.105 price lists, stock sheets, pick lists on a packer's own Hoola ----
  Future<Map<String, dynamic>> netDealCatalog(String to) async =>
      _hm(await _send('GET', '/api/net/deals/catalog', query: {'to': to}, timeout: const Duration(seconds: 40)));
  Future<Map<String, dynamic>> netStockImport(String filename, List<int> bytes) async =>
      uploadFile('/api/net/stock/import', filename, bytes, timeout: const Duration(seconds: 90));
  Future<List<Map<String, dynamic>>> netPicks({bool all = false}) async =>
      _hl((await _send('GET', '/api/net/picks', query: {'all': all ? 'true' : 'false'}))['picks']);
  Future<Map<String, dynamic>> netPickAct(String id, String action, [Map<String, dynamic> body = const {}]) async =>
      _hm(await _send('POST', '/api/net/picks/$id/$action', body: body, timeout: const Duration(seconds: 60)));
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
  /// v0.154 'Ek tap mein jodo': hosted servers join directly, packages run on Hoola's MCP runner (first start can take a minute).
  Future<Map<String, dynamic>> mcpOneTap(String ref, {Map<String, String> keys = const {}, bool acceptCaution = false}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/mcp/one_tap',
          body: {'ref': ref, 'keys': keys, 'accept_caution': acceptCaution}, timeout: const Duration(seconds: 300)));
  Future<Map<String, dynamic>> jaanch() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/jaanch', timeout: const Duration(seconds: 60)));
  Future<Map<String, dynamic>> mcpTools(String packId) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/bazar/mcp/$packId/tools', timeout: const Duration(seconds: 30)));
  Future<Map<String, dynamic>> mcpToolSet(String packId, String tool, {bool? enabled, bool? ask}) async =>
      Map<String, dynamic>.from(await _send('PATCH', '/api/bazar/mcp/$packId/tools/${Uri.encodeComponent(tool)}',
          body: {if (enabled != null) 'enabled': enabled, if (ask != null) 'ask': ask}, timeout: const Duration(seconds: 30)));
  Future<List<Map<String, dynamic>>> mcpFeatured() async =>
      List<Map<String, dynamic>>.from(((await _send('GET', '/api/bazar/mcp/featured'))['connectors'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
  Future<Map<String, dynamic>> mcpConnectFeatured(String id,
          {String url = '', String key = '', String header = '', bool? readonly, List<String>? toolsets, String? project}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/mcp/featured/$id', body: {
        'url': url, 'key': key, 'key_header': header,
        if (readonly != null) 'readonly': readonly,
        if (toolsets != null) 'toolsets': toolsets,
        if (project != null) 'project': project,
      }, timeout: const Duration(seconds: 40)));

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
  Future<Map<String, dynamic>> bazarDecide(String id, String decision) async => Map<String, dynamic>.from(await _withFingerprint(
      'bazar', id, decision == 'approve', (proof) => _send('POST', '/api/bazar/approvals/$id',
          body: {'decision': decision, if (proof != null) 'proof': proof})) as Map);

  /// v0.109 After 'Paisa bhejo': her answer on the card (done | not) or the phone's own report (result none).
  Future<Map<String, dynamic>> upiResult(String txnRef, {String answer = '', String result = '', String package = ''}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/bazar/upi/result',
          body: {'txn_ref': txnRef, 'answer': answer, 'result': result, 'package': package}) as Map);

  // ---- v0.97 fingerprint-signed approvals ----
  /// Sends an approval; when the server answers 428 (a money card, and a phone is set up for fingerprint approvals)
  /// the phone's fingerprint signs the server's challenge for THIS card and the approval is sent again with it.
  Future<dynamic> _withFingerprint(String kind, String target, bool approving,
      Future<dynamic> Function(Map<String, dynamic>? proof) send) async {
    try {
      return await send(null);
    } on ApiException catch (e) {
      if (!approving || e.status != 428) rethrow;
    }
    final proof = await fingerprintProof(kind, target);
    return send(proof);
  }

  /// Challenge from the server -> fingerprint sheet on this phone -> signature. Throws a plain-words ApiException.
  Future<Map<String, dynamic>> fingerprintProof(String kind, String target) async {
    final c = Map<String, dynamic>.from(await _send('POST', '/api/approvekey/challenge', body: {'kind': kind, 'target': target}) as Map);
    final show = Map<String, dynamic>.from((c['show'] as Map?) ?? const {});
    final sub = [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · ');
    final r = await Native.approveKeySign('${c['message']}', '${show['title'] ?? 'Haan dene ke liye fingerprint'}', sub);
    if (r['signature'] == null) {
      final err = '${r['error'] ?? ''}';
      throw ApiException(428, switch (err) {
        'cancelled' => 'Fingerprint nahi diya, isliye haan nahi hui.',
        'key_invalidated' => 'Phone mein naya fingerprint juda hai: Profile > Fingerprint se haan mein is phone ko phir se jodiye.',
        'no_key' || 'not_supported' => 'Yeh card fingerprint se hi haan hota hai, par is phone mein chaabi nahi hai. Jude hue phone se haan kijiye.',
        _ => 'Fingerprint se haan nahi ho payi ($err).',
      });
    }
    return {'challenge_id': c['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  // ---- v0.97 form card ----
  // v0.108 Document desk / Sheet Milaan: her tap on the card (Haan = new copy into the PC's Santosh Inbox)
  Future<Map<String, dynamic>> deskDecide(String id, bool yes, {Map<String, dynamic>? options}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/docdesk/edits/$id/decide',
          body: {'yes': yes, if (options != null) 'options': options}, timeout: const Duration(seconds: 240)) as Map);
  Future<Map<String, dynamic>> deskEdit(String id) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/docdesk/edits/$id') as Map);
  Future<Map<String, dynamic>> yaadSearch(String q) async =>
      Map<String, dynamic>.from(await _send('GET', '/api/yaad', query: {'q': q}) as Map);
  Future<Map<String, dynamic>> formAnswer(String id, Map<String, dynamic> values) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/forms/$id/answer', body: {'values': values}) as Map);
  Future<Map<String, dynamic>> formCancel(String id) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/forms/$id/cancel') as Map);

  Future<Map<String, dynamic>> approveKeyStatus() async => Map<String, dynamic>.from(await _send('GET', '/api/approvekey') as Map);
  Future<Map<String, dynamic>> approveKeyAdd(String deviceId, String publicKey, String label, bool strongbox,
          {Map<String, dynamic>? proof}) async =>
      Map<String, dynamic>.from(await _send('POST', '/api/approvekey/devices', body: {
        'device_id': deviceId, 'public_key': publicKey, 'label': label, 'strongbox': strongbox, if (proof != null) 'proof': proof,
      }) as Map);
  Future<Map<String, dynamic>> approveKeyRemove(String deviceId, {Map<String, dynamic>? proof}) async => Map<String, dynamic>.from(
      await _send('POST', '/api/approvekey/devices/${Uri.encodeComponent(deviceId)}/remove', body: {if (proof != null) 'proof': proof}) as Map);
  Future<Map<String, dynamic>> approveKeyCancel(String deviceId) async => Map<String, dynamic>.from(
      await _send('POST', '/api/approvekey/devices/${Uri.encodeComponent(deviceId)}/cancel') as Map);
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
            if (ev.isMarker) {
              yield ev; // v0.158 replay_end / resync
            } else if (ev.id > last) {
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
