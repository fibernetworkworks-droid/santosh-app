import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'device.dart';
import 'native.dart';

class FeedItem {
  FeedItem(this.kind, this.data);
  final String kind; // message / steps / campaign / note
  Map<String, dynamic> data;
  final List<Map<String, dynamic>> steps = [];
}

const languages = <String, String>{
  'hi-IN': 'हिंदी',
  'mr-IN': 'मराठी',
  'en-IN': 'English',
  'gu-IN': 'ગુજરાતી',
  'ta-IN': 'தமிழ்',
  'te-IN': 'తెలుగు',
  'kn-IN': 'ಕನ್ನಡ',
  'bn-IN': 'বাংলা',
};

/// App-wide state: connection, chat feed, reminders, lists. Screens listen to it.
class Santosh extends ChangeNotifier {
  Santosh._(this._prefs);
  final SharedPreferences _prefs;

  static Future<Santosh> load() async => Santosh._(await SharedPreferences.getInstance());

  // settings
  String get serverUrl => _prefs.getString('server') ?? '';
  String get apiKey => _prefs.getString('key') ?? '';
  String get language => _prefs.getString('lang') ?? 'hi-IN';
  bool get speakReplies => _prefs.getBool('speak') ?? true;
  bool get configured => serverUrl.isNotEmpty;
  /// Background mode: a native service keeps Santosh working while the app is closed.
  bool get background => _prefs.getBool('bg') ?? true;
  /// Santosh's voice for live calls (a male Gemini voice id).
  String get voiceName => _prefs.getString('voice') ?? voiceDefault;
  Future<void> setVoice(String v) async {
    await _prefs.setString('voice', v);
    notifyListeners();
  }

  Api? api;
  String? conversationId;
  bool connected = false;
  bool dryRun = true;
  bool brainReady = true;
  bool typing = false;
  String? error;
  bool inBackground = false;
  bool backgroundRunning = false;
  String backgroundStatus = '';
  bool batteryOptimized = false;
  bool hasCalendar = false;
  /// While the voice screen is open it speaks replies itself.
  bool voiceMode = false;
  /// The server can run live human-like voice calls (Gemini Live).
  bool realtimeVoice = false;
  String voiceDefault = 'Puck';
  List<Map<String, dynamic>> voices = [];
  bool googleLogin = false;          // server offers Sign in with Google
  Map<String, dynamic>? account;     // /api/me when signed in
  String? currentStep;
  int lastEventId = 0;
  List<Map<String, dynamic>> routines = [];
  final StreamController<Map<String, dynamic>> _replies = StreamController<Map<String, dynamic>>.broadcast();
  /// Fresh replies from Santosh (not history replays). The voice screen listens to this.
  Stream<Map<String, dynamic>> get replies => _replies.stream;

  final List<FeedItem> feed = [];
  final Map<String, FeedItem> _campaigns = {};
  final Map<String, FeedItem> _emails = {};
  final Map<String, FeedItem> _bazar = {};   // confirm cards by approval id
  int bazarLinkedTick = 0;                    // bumps when an app account got linked (Apps screen refreshes)
  FeedItem? _steps;
  List<Map<String, dynamic>> reminders = [];
  Map<String, dynamic> lists = {};

  StreamSubscription<SantoshEvent>? _sub;
  final FlutterTts _tts = FlutterTts();
  bool _lastInputWasVoice = false;
  bool _replaying = true;
  DateTime _connectedAt = DateTime.now().toUtc();

  Future<void> saveSettings({String? server, String? key, String? lang, bool? speak}) async {
    if (server != null) await _prefs.setString('server', server.trim());
    if (key != null) await _prefs.setString('key', key.trim());
    if (lang != null) await _prefs.setString('lang', lang);
    if (speak != null) await _prefs.setBool('speak', speak);
    notifyListeners();
  }

  Future<void> connect({bool fresh = false}) async {
    error = null;
    await _sub?.cancel();
    feed.clear();
    lastEventId = 0;
    _campaigns.clear();
    _emails.clear();
    _steps = null;
    api = Api(serverUrl, apiKey);
    try {
      final h = await api!.health();
      dryRun = h['dry_run'] == true;
      brainReady = h['brain_configured'] == true;
      realtimeVoice = (h['features'] as List?)?.contains('realtime_voice') ?? false;
      voiceDefault = h['voice_default'] as String? ?? 'Puck';
      voices = List<Map<String, dynamic>>.from((h['voices'] as List?) ?? const []);
      googleLogin = h['google_login'] == true;
      conversationId = fresh ? null : _prefs.getString('conv');
      if (conversationId != null) {
        try {
          await api!.checkConversation(conversationId!);
        } on ApiException catch (e) {
          if (e.status == 401) rethrow;
          conversationId = null;
        }
      }
      conversationId ??= await api!.newConversation();
      await _prefs.setString('conv', conversationId!);
      connected = true;
      _replaying = true;
      _connectedAt = DateTime.now().toUtc();
      notifyListeners();
      _sub = api!.events(conversationId!).listen(_onEvent, onError: (e) {
        error = e.toString();
        connected = false;
        notifyListeners();
      });
      // once history has replayed, hand the latest event id to the background service
      Timer(const Duration(seconds: 2), () {
        _replaying = false;
        applyBackground();
      });
      await Device.instance.init();
      await Device.instance.askNotificationPermission();
      await refreshLists();
      await refreshRoutines();
      await refreshAccount();
      for (final a in await api!.pendingActions()) {
        await _runAction(a);
      }
    } catch (e) {
      connected = false;
      error = e is ApiException && e.status == 401 ? 'API key galat hai. Settings mein theek kijiye.' : 'Server se connect nahi ho paya: $e';
      notifyListeners();
    }
  }

  Future<void> refreshAccount() async {
    try {
      final m = await api!.me();
      account = m['signed_in'] == true ? m : null;
    } catch (_) {
      account = null;
    }
    notifyListeners();
  }

  /// Save the session token that came back from Sign in with Google (used as the bearer).
  Future<void> applySession(String token, {String? server}) async {
    if (server != null && server.isNotEmpty) await _prefs.setString('server', server);
    await _prefs.setString('key', token);
    await connect(fresh: true);
  }

  Future<void> disconnectProvider(String provider) async {
    try {
      await api!.disconnect(provider);
      await refreshAccount();
    } catch (e) {
      error = e.toString();
      notifyListeners();
    }
  }

    Future<void> refreshReminders() async {
    try {
      reminders = await api!.reminders();
      await _syncLocalReminders();
      notifyListeners();
    } catch (_) {}
  }

  /// With background mode on, the service shows reminders as the server fires them;
  /// otherwise the phone schedules its own notifications.
  Future<void> _syncLocalReminders() => Device.instance.syncReminders(backgroundRunning ? const [] : reminders);

  Future<void> refreshRoutines() async {
    try {
      routines = await api!.routines();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> cancelRoutine(String id) async {
    try {
      await api!.cancelRoutine(id);
      routines.removeWhere((r) => r['id'] == id);
    } catch (e) {
      error = e.toString();
    }
    notifyListeners();
  }

  /// Start or stop the native background service to match the setting.
  Future<void> applyBackground() async {
    if (background && conversationId != null) {
      await Native.start(server: serverUrl, key: apiKey, conv: conversationId!, after: lastEventId);
    } else {
      await Native.stop();
    }
    await refreshBackgroundInfo();
    await refreshReminders();
  }

  Future<void> refreshBackgroundInfo() async {
    backgroundRunning = await Native.running();
    backgroundStatus = await Native.status();
    batteryOptimized = await Native.batteryOptimized();
    hasCalendar = await Native.hasCalendar();
    notifyListeners();
  }

  Future<void> setBackground(bool on) async {
    await _prefs.setBool('bg', on);
    await applyBackground();
  }

  Future<void> refreshLists() async {
    try {
      lists = await api!.lists();
      notifyListeners();
    } catch (_) {}
  }

  /// [voice]: typed by speaking in chat (reply is read aloud). [spoken]: from the voice screen
  /// (the server keeps the reply short and speakable).
  Future<bool> send(String text, {bool voice = false, bool spoken = false}) async {
    text = text.trim();
    if (text.isEmpty || api == null || conversationId == null) return false;
    _lastInputWasVoice = voice;
    try {
      await api!.sendMessage(conversationId!, text, voice: spoken);
      return true;
    } catch (e) {
      error = 'Message nahi gaya: $e';
      notifyListeners();
      return false;
    }
  }

  Future<String?> uploadLeads(String name, List<int> bytes) async {
    try {
      final r = await api!.uploadLeads(conversationId!, name, bytes);
      await send('Maine file upload ki hai: $name (list id: ${r['list_id']}, ${r['valid']} sahi number).');
      return null;
    } catch (e) {
      return e.toString();
    }
  }

  Future<void> sendEmail(String id, {String? to, String? cc, String? subject, String? body}) async {
    try {
      await api!.sendEmail(id, to: to, cc: cc, subject: subject, body: body);
      final it = _emails[id];
      if (it != null) it.data = {...it.data, 'status': 'sent'};
    } catch (e) {
      error = e.toString();
    }
    notifyListeners();
  }

  Future<void> cancelEmail(String id) async {
    try {
      await api!.cancelEmail(id);
      final it = _emails[id];
      if (it != null) it.data = {...it.data, 'status': 'cancelled'};
    } catch (e) {
      error = e.toString();
    }
    notifyListeners();
  }

  /// Approve or cancel a Bazar confirm card. On approve, opens the UPI app / link right away (user tap).
  Future<void> decideBazar(String id, String decision) async {
    final it = _bazar[id];
    if (it != null) it.data = {...it.data, 'busy': true};
    notifyListeners();
    try {
      final r = await api!.bazarDecide(id, decision);
      if (it != null) it.data = {...it.data, 'status': r['status'], 'busy': false, 'result': {'open': r['open'], 'message': (r['outcome'] as Map?)?['message'] ?? (r['outcome'] as Map?)?['error'] ?? ''}};
      final open = r['open'] as Map?;
      if (decision == 'approve' && open != null && (open['kind'] == 'upi' || open['kind'] == 'app')) {
        final res = await Native.openExternal(url: open['url'] as String? ?? '', package: open['package'] as String? ?? '');
        if (res != 'ok') feed.add(FeedItem('note', {'text': res}));
      }
    } catch (e) {
      if (it != null) it.data = {...it.data, 'busy': false};
      error = e.toString();
    }
    notifyListeners();
  }

  Future<String> openBazar(Map<String, dynamic> open) async =>
      Native.openExternal(url: open['url'] as String? ?? '', package: open['package'] as String? ?? '');

  Future<String?> linkApp(String packId) async {
    try {
      final url = await api!.bazarLink(packId);
      final res = await Native.openExternal(url: url);
      return res == 'ok' ? null : res;
    } catch (e) {
      return e.toString();
    }
  }

  void onBazarLinked(bool ok) {
    bazarLinkedTick++;
    feed.add(FeedItem('note', {'text': ok ? 'App jud gaya ✓ Ab Santosh order kar sakta hai.' : 'App link nahi ho paya, dobara koshish kijiye.'}));
    notifyListeners();
  }

  Future<void> campaignAction(String id, String action) async {
    try {
      final v = await api!.campaignAction(id, action);
      _campaign(v);
    } catch (e) {
      error = e.toString();
    }
    notifyListeners();
  }

  void _campaign(Map<String, dynamic> v) {
    final id = v['id'] as String;
    final existing = _campaigns[id];
    if (existing != null) {
      existing.data = v;
    } else {
      final it = FeedItem('campaign', v);
      _campaigns[id] = it;
      feed.add(it);
    }
  }

  Future<void> _onEvent(SantoshEvent ev) async {
    final p = ev.payload;
    if (ev.id > lastEventId) lastEventId = ev.id;
    switch (ev.kind) {
      case 'message':
        if (p['role'] == 'user') _steps = null;
        feed.add(FeedItem('message', p));
        final fresh = !_replaying && ev.at.isAfter(_connectedAt.subtract(const Duration(seconds: 5)));
        if (p['role'] == 'assistant' && fresh) {
          _replies.add(p);
          if (inBackground && !backgroundRunning) Device.instance.showNow('Santosh', p['text'] as String? ?? '');
          if (!voiceMode && _lastInputWasVoice && speakReplies && p['source'] == 'agent') _speak(p['text'] as String? ?? '');
        }
        break;
      case 'typing':
        typing = p['on'] == true && !_replaying;
        if (p['on'] == true) _steps = null;
        if (!typing) currentStep = null;
        break;
      case 'step':
        if (_steps == null) {
          _steps = FeedItem('steps', {});
          feed.add(_steps!);
        }
        if (!_replaying) currentStep = p['state'] == 'running' ? p['label'] as String? : currentStep;
        final i = _steps!.steps.indexWhere((s) => s['id'] == p['id']);
        if (i >= 0) {
          _steps!.steps[i] = p;
        } else {
          _steps!.steps.add(p);
        }
        break;
      case 'campaign':
        _campaign(p);
        break;
      case 'upload':
        feed.add(FeedItem('note', {'text': '${p['filename']} · ${p['valid']} sahi number'}));
        break;
      case 'reminders':
        reminders = List<Map<String, dynamic>>.from(p['reminders'] as List? ?? const []);
        await _syncLocalReminders();
        break;
      case 'routines':
        routines = List<Map<String, dynamic>>.from(p['routines'] as List? ?? const []);
        break;
      case 'email_draft':
        _emails[p['id'] as String] = FeedItem('email', Map<String, dynamic>.from(p));
        feed.add(_emails[p['id']]!);
        break;
      case 'email_sent':
        final it = _emails[p['id'] as String];
        if (it != null) it.data = {...it.data, ...p};
        break;
      case 'lists':
        await refreshLists();
        break;
      case 'bazar_approval':
        final id = p['id'] as String? ?? '';
        final existing = _bazar[id];
        if (existing != null) {
          existing.data = {...existing.data, ...p};
        } else {
          _bazar[id] = FeedItem('bazar', Map<String, dynamic>.from(p));
          feed.add(_bazar[id]!);
          if (inBackground && !_replaying) Device.instance.showNow('Santosh: approve karein', '${p['title'] ?? ''} ${p['amount'] ?? ''}');
        }
        break;
      case 'bazar_open':
        feed.add(FeedItem('open', Map<String, dynamic>.from(p)));
        break;
      case 'bazar_link':
        feed.add(FeedItem('link', Map<String, dynamic>.from(p)));
        break;
      case 'device_action':
        // in the background the native service does it (screens can't be opened from the background)
        if (!(inBackground && backgroundRunning)) await _runAction(p, at: ev.at);
        break;
      case 'device_action_result':
        if (p['status'] == 'done') {
          final what = {'set_alarm': 'Alarm laga diya', 'set_timer': 'Timer shuru', 'add_calendar_event': 'Calendar khul gaya', 'open_url': 'Phone par khul gaya'};
          feed.add(FeedItem('note', {'text': '${what[p['type']] ?? 'Ho gaya'} ✓'}));
        }
        break;
    }
    notifyListeners();
  }

  /// Run a phone action once, even though the stream replays history on every start.
  Future<void> _runAction(Map<String, dynamic> a, {DateTime? at}) async {
    final id = a['id'] as String?;
    if (id == null) return;
    final done = _prefs.getStringList('done_actions') ?? <String>[];
    if (done.contains(id)) return;
    if (at != null && DateTime.now().toUtc().difference(at) > const Duration(minutes: 15)) return;
    if (!await Native.claim(id)) return; // the background service already did it
    final kept = done.length > 300 ? done.sublist(done.length - 300) : done;
    await _prefs.setStringList('done_actions', [...kept, id]);
    final err = await Device.instance.run(a);
    try {
      await api!.actionResult(id, err == null, err);
    } catch (_) {}
  }

  Future<void> _speak(String text) async {
    try {
      await _tts.setLanguage(language);
      await _tts.setSpeechRate(0.5);
      await _tts.speak(text.replaceAll(RegExp(r'[*_#]'), ''));
    } catch (_) {}
  }

  Future<void> stopSpeaking() async => _tts.stop();

  /// Let the UI rebuild after an in-place edit of a feed item.
  void notifyChange() => notifyListeners();

  @override
  void dispose() {
    _replies.close();
    _sub?.cancel();
    super.dispose();
  }
}
