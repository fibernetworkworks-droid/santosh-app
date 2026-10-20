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
