import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'device.dart';

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

  Api? api;
  String? conversationId;
  bool connected = false;
  bool dryRun = true;
  bool brainReady = true;
  bool typing = false;
  String? error;
  bool inBackground = false;

  final List<FeedItem> feed = [];
  final Map<String, FeedItem> _campaigns = {};
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
    _campaigns.clear();
    _steps = null;
    api = Api(serverUrl, apiKey);
    try {
      final h = await api!.health();
      dryRun = h['dry_run'] == true;
      brainReady = h['brain_configured'] == true;
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
      Timer(const Duration(seconds: 2), () => _replaying = false);
      await Device.instance.init();
      await Device.instance.askNotificationPermission();
      await refreshReminders();
      await refreshLists();
      for (final a in await api!.pendingActions()) {
        await _runAction(a);
      }
    } catch (e) {
      connected = false;
      error = e is ApiException && e.status == 401 ? 'API key galat hai. Settings mein theek kijiye.' : 'Server se connect nahi ho paya: $e';
      notifyListeners();
    }
  }

  Future<void> refreshReminders() async {
    try {
      reminders = await api!.reminders();
      await Device.instance.syncReminders(reminders);
      notifyListeners();
    } catch (_) {}
  }

  Future<void> refreshLists() async {
    try {
      lists = await api!.lists();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> send(String text, {bool voice = false}) async {
    text = text.trim();
    if (text.isEmpty || api == null || conversationId == null) return;
    _lastInputWasVoice = voice;
    try {
      await api!.sendMessage(conversationId!, text);
    } catch (e) {
      error = 'Message nahi gaya: $e';
      notifyListeners();
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
    switch (ev.kind) {
      case 'message':
        if (p['role'] == 'user') _steps = null;
        feed.add(FeedItem('message', p));
        final fresh = !_replaying && ev.at.isAfter(_connectedAt.subtract(const Duration(seconds: 5)));
        if (p['role'] == 'assistant' && fresh) {
          if (inBackground) Device.instance.showNow('Santosh', p['text'] as String? ?? '');
          if (_lastInputWasVoice && speakReplies && p['source'] == 'agent') _speak(p['text'] as String? ?? '');
        }
        break;
      case 'typing':
        typing = p['on'] == true && !_replaying;
        if (p['on'] == true) _steps = null;
        break;
      case 'step':
        if (_steps == null) {
          _steps = FeedItem('steps', {});
          feed.add(_steps!);
        }
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
        await Device.instance.syncReminders(reminders);
        break;
      case 'lists':
        await refreshLists();
        break;
      case 'device_action':
        await _runAction(p, at: ev.at);
        break;
      case 'device_action_result':
        if (p['status'] == 'done') {
          final what = {'set_alarm': 'Alarm laga diya', 'set_timer': 'Timer shuru', 'add_calendar_event': 'Calendar khul gaya'};
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

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
