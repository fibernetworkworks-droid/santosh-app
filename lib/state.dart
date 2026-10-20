import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'call_session.dart';
import 'ui/bluetooth_panel.dart' show btWhy;
import 'device.dart';
import 'emotion.dart';
import 'hoola.dart';
import 'native.dart';
import 'ui/avatar_look.dart' show currentLook, isLook;

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
  Santosh._(this._prefs) {
    currentLook.value = aLook;                  // last known look, before the server answers
  }
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

  // ---------------- Hoola avatar (the name, gender and voice the owner gave their AI coworker) ----------------
  Map<String, dynamic> avatar = {};
  bool avatarLoaded = false;
  String get aName => (avatar['name'] as String?)?.trim().isNotEmpty == true ? avatar['name'] as String : (_prefs.getString('a_name') ?? 'Santosh');
  bool get aFemale => (avatar['gender'] ?? _prefs.getString('a_gender')) == 'f';
  /// v0.48: '' = Santosh; f001..f100 = the female 3D look the owner picked.
  String get aLook {
    final l = (avatar['look'] as String?) ?? _prefs.getString('a_look') ?? '';
    return aFemale && isLook(l) ? l : '';
  }

  Future<void> _keepLook() async {
    await _prefs.setString('a_look', aLook);
    currentLook.value = aLook;
  }
  bool get needsAvatarSetup => connected && avatarLoaded && avatar['setup_done'] != true;
  Map<String, dynamic> get avatarRules => Map<String, dynamic>.from(avatar['rules'] as Map? ?? const {});

  /// Hindi verb forms for the avatar: "kar raha hoon" -> "kar rahi hoon" when she is female.
  String g(String text) => aFemale ? genderedHi(text) : text;

  Future<void> loadAvatar() async {
    try {
      avatar = await api!.avatarGet();
      avatarLoaded = true;
      await _prefs.setString('a_name', aName);
      await _prefs.setString('a_gender', aFemale ? 'f' : 'm');
      await _keepLook();
      final v = avatar['voice'] as String?;
      if (v != null && v.isNotEmpty && v != voiceName) await _prefs.setString('voice', v);
      notifyListeners();
    } catch (_) {
      // older server without /api/avatar: keep "Santosh", never block the app on setup
      avatarLoaded = false;
    }
  }

  /// Returns an error message, or null when saved.
  Future<String?> saveAvatar({String? name, String? gender, String? voice, bool? setupDone, Map<String, dynamic>? rules, String? look}) async {
    try {
      avatar = await api!.avatarPut({
        if (name != null) 'name': name,
        if (gender != null) 'gender': gender,
        if (voice != null) 'voice': voice,
        if (setupDone != null) 'setup_done': setupDone,
        if (rules != null) 'rules': rules,
        if (look != null) 'look': look,
      });
      avatarLoaded = true;
      await _prefs.setString('a_name', aName);
      await _prefs.setString('a_gender', aFemale ? 'f' : 'm');
      await _keepLook();
      final v = avatar['voice'] as String?;
      if (v != null && v.isNotEmpty) await _prefs.setString('voice', v);
      notifyListeners();
      return null;
    } on ApiException catch (e) {
      return e.message;
    } catch (e) {
      return e.toString();
    }
  }

  // ---------------- Hoola Network ----------------
  final Map<String, FeedItem> _hoola = {};
  int hoolaTick = 0;

  /// Owner's decision on a knock card. Returns an error message or null.
  Future<String?> hoolaDecide(String msgId, String action, {int? slot, int? minutes, String note = ''}) async {
    try {
      final r = await api!.netDecide(msgId, action, slot: slot, minutes: minutes, note: note);
      final it = _hoola['hoola_knock:$msgId'];
      if (it != null) it.data = {...it.data, 'status': r['status'] ?? action, if (r['effect'] != null) 'effect': r['effect']};
      hoolaTick++;
      notifyListeners();
      return null;
    } catch (e) {
      return e.toString();
    }
  }

  Future<String?> hoolaAnswer(String linkId, String action, {String relation = ''}) async {
    try {
      final r = await api!.netAnswer(linkId, action, relation: relation);
      final it = _hoola['hoola_connect:$linkId'];
      if (it != null) it.data = {...it.data, 'status': r['status'] ?? action};
      hoolaTick++;
      notifyListeners();
      return null;
    } catch (e) {
      return e.toString();
    }
  }

  /// santosh://connect?c=CODE (from a Hoola QR / invite link).
  Future<void> onConnectLink(String code) async {
    if (api == null || code.isEmpty) return;
    try {
      final r = await api!.netConnect(invite: code);
      final who = ((r['link'] as Map?)?['label'] as String?) ?? 'Hoola';
      feed.add(FeedItem('note', {'text': r['status'] == 'active' ? '$who se jud gaye ✓' : 'Request bhej di: $who haan kahenge to dono Hoola baat kar sakenge.'}));
    } catch (e) {
      feed.add(FeedItem('note', {'text': 'Connect nahi hua: $e'}));
    }
    hoolaTick++;
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
  bool exactAlarms = true;
  bool pushOn = false;   // this phone gets Firebase pushes (set once the token is known)
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

  // ---------------- Santosh's feelings ----------------
  Mood mood = Mood.idle;
  Timer? _moodTimer;
  DateTime? _stressedUntil;      // you sounded stressed: he stays gentle for a while
  bool get userStressed => _stressedUntil != null && DateTime.now().isBefore(_stressedUntil!);

  void setMood(Mood m, {Duration hold = const Duration(seconds: 7)}) {
    _moodTimer?.cancel();
    mood = m;
    if (hold > Duration.zero) {
      _moodTimer = Timer(hold, () {
        mood = typing ? Mood.think : (userStressed ? Mood.care : Mood.idle);
        notifyListeners();
      });
    }
    notifyListeners();
  }

  /// React to what you said (typed or spoken).
  void feelUser(String text) {
    final f = feel(text);
    if (f == null) {
      setMood(userStressed ? Mood.care : Mood.listening, hold: const Duration(seconds: 4));
      return;
    }
    if (f.mood == Mood.care) _stressedUntil = DateTime.now().add(const Duration(minutes: 15));
    if (f.mood == Mood.excited || f.mood == Mood.happy) _stressedUntil = null;
    setMood(f.mood, hold: Duration(seconds: (5 + f.intensity * 6).round()));
  }

  /// React to what he himself says (so his body matches his words).
  void feelReply(String text) {
    final f = feel(text);
    var m = f?.mood ?? Mood.happy;
    if (m == Mood.think || m == Mood.work) m = Mood.happy; // he finished: no longer pondering
    if (userStressed && m != Mood.excited) m = Mood.care;
    setMood(m, hold: const Duration(seconds: 8));
  }

  final List<FeedItem> feed = [];
  final Map<String, FeedItem> _campaigns = {};
  final Map<String, FeedItem> _emails = {};
  final Map<String, FeedItem> _bazar = {};   // confirm cards by approval id
  List<Map<String, dynamic>> get pendingApprovals =>
      [for (final it in _bazar.values) if ((it.data['status'] ?? 'pending') == 'pending') it.data];
  int bazarLinkedTick = 0;                    // bumps when an app account got linked (Apps screen refreshes)
  final Map<String, FeedItem> _artifacts = {}; // one card per artifact id, updated in place
  /// The chat card for an artifact (null when it was made in another chat).
  FeedItem? artifactItem(String id) => _artifacts[id];
  /// Newest live artifact event (not history replays); the voice screens show it.
  Map<String, dynamic>? latestArtifact;
  final Map<String, FeedItem> _browsers = {};   // one live card per browser task, updated in place
  Map<String, dynamic>? latestBrowser;           // the task the voice call screen shows
  FeedItem? browserItem(String sid) => _browsers[sid];
  int artifactTick = 0;                       // bumps with every live artifact event
  FeedItem? _steps;
  List<Map<String, dynamic>> reminders = [];
  Map<String, dynamic> lists = {};

  StreamSubscription<SantoshEvent>? _sub;
  final FlutterTts _tts = FlutterTts();
  bool _lastInputWasVoice = false;
  bool _replaying = true;
  /// True while the chat history is replaying after a (re)connect: those items show at once, without animation.
  bool get replaying => _replaying;
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
    _calEvents.clear();
    _picks.clear();
    _artifacts.clear();
    _browsers.clear();
    _hoola.clear();
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
      // push notifications when the app is closed / phone locked (the native side shows them; avoid doubles here)
      final serverPush = (h['features'] as List?)?.contains('push') ?? false;
      unawaited(Native.pushInit(serverUrl, apiKey).then((t) => pushOn = serverPush && (t ?? '').isNotEmpty));
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
        _syncBazar();
      });
      await Device.instance.init();
      await Device.instance.askNotificationPermission();
      if (!(_prefs.getBool('asked_location') ?? false)) {
        await _prefs.setBool('asked_location', true);
        await Native.askLocation();
      }
      pushLocation();
      await refreshLists();
      await refreshRoutines();
      await refreshAccount();
      await loadAvatar();
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
    exactAlarms = await Native.exactAlarms();
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
  Future<bool> send(String text, {bool voice = false, bool spoken = false, List<String> files = const []}) async {
    text = text.trim();
    if (text.isEmpty || api == null || conversationId == null) return false;
    _lastInputWasVoice = voice;
    pushLocation(); // "near me", directions and cab pickup use where the phone is
    feelUser(text);
    try {
      await api!.sendMessage(conversationId!, text, voice: spoken, files: files);
      return true;
    } catch (e) {
      error = 'Message nahi gaya: $e';
      notifyListeners();
      return false;
    }
  }

  /// The chat paperclip (v0.44.1): any file goes up and waits in the box until the message is sent.
  Future<Map<String, dynamic>> attachChatFile(String name, List<int> bytes) async {
    if (api == null || conversationId == null) throw Exception('Abhi server se nahi jude');
    return api!.chatFile(conversationId!, name, bytes);
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

  Future<void> sendEmail(String id, {String? to, String? cc, String? bcc, String? subject, String? body, bool sendNow = false}) async {
    final it = _emails[id];
    if (it != null) it.data = {...it.data, 'busy': true};
    notifyListeners();
    try {
      final r = await api!.sendEmail(id, to: to, cc: cc, bcc: bcc, subject: subject, body: body, sendNow: sendNow);
      if (it != null) {
        it.data = {...it.data, 'status': r['status'] ?? 'sent', 'error': null,
          if (to != null) 'to': to, if (cc != null) 'cc': cc, if (subject != null) 'subject': subject, if (body != null) 'body': body};
      }
    } catch (e) {
      error = e.toString();
      if (it != null) it.data = {...it.data, 'status': 'failed', 'error': e.toString()};
    }
    if (it != null) it.data = {...it.data, 'busy': false};
    notifyListeners();
  }

  /// Add a file from the phone to an email draft. Returns an error text, or null.
  Future<String?> addEmailAttachment(String id, String name, List<int> bytes) async {
    try {
      final v = await api!.addEmailAttachment(id, name, bytes);
      final it = _emails[id];
      if (it != null) it.data = {...it.data, ...v};
      notifyListeners();
      return null;
    } catch (e) {
      return e.toString();
    }
  }

  Future<void> removeEmailAttachment(String id, int index) async {
    try {
      final v = await api!.removeEmailAttachment(id, index);
      final it = _emails[id];
      if (it != null) it.data = {...it.data, ...v};
    } catch (e) {
      error = e.toString();
    }
    notifyListeners();
  }

  int sheetsLinkedTick = 0;
  int driveLinkedTick = 0;
  int formsLinkedTick = 0;
  int slidesLinkedTick = 0;
  int photosLinkedTick = 0;
  int youtubeLinkedTick = 0;
  void onGoogleLinked(String what, bool ok) {
    if (what == 'youtube') youtubeLinkedTick++;
    if (what == 'slides') slidesLinkedTick++;
    if (what == 'photos') photosLinkedTick++;
    if (what == 'sheets') sheetsLinkedTick++;
    if (what == 'drive') driveLinkedTick++;
    if (what == 'forms') formsLinkedTick++;
    final name = {'sheets': 'Google Sheets', 'drive': 'Google Drive', 'forms': 'Google Forms', 'slides': 'Google Slides',
      'photos': 'Google Photos', 'youtube': 'YouTube'}[what] ?? what;
    feed.add(FeedItem('note', {'text': ok ? '$name jud gaya ✓' : '$name nahi jud paya, dobara koshish kijiye.'}));
    notifyListeners();
  }

  int calendarLinkedTick = 0;                  // bumps when Google Calendar got connected
  final Map<String, FeedItem> _calEvents = {};
  final Map<String, FeedItem> _picks = {};
  void onCalendarLinked(bool ok) {
    calendarLinkedTick++;
    feed.add(FeedItem('note', {'text': ok ? g('Google Calendar jud gaya ✓ Ab $aName aapka schedule dekh aur bana sakta hai.') : 'Calendar nahi jud paya, dobara koshish kijiye.'}));
    notifyListeners();
  }

  int mailLinkedTick = 0;                      // bumps when a mailbox got connected (Email screen refreshes)
  void onMailLinked(bool ok) {
    mailLinkedTick++;
    feed.add(FeedItem('note', {'text': ok ? g('Email jud gaya ✓ Ab $aName aapki mail padh aur likh sakta hai.') : 'Email nahi jud paya, dobara koshish kijiye.'}));
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

  /// When the app was last in front of you (for "Jab aap offline the").
  Future<void> markSeen() async => _prefs.setString('last_seen', DateTime.now().toUtc().toIso8601String());

  /// What Santosh did while you were away (≥ 2 hours), or null.
  Future<Map<String, dynamic>?> catchUp() async {
    final raw = _prefs.getString('last_seen');
    if (raw == null) {
      await markSeen();
      return null;
    }
    if (api == null) return null;
    final since = DateTime.tryParse(raw);
    if (since == null || DateTime.now().toUtc().difference(since) < const Duration(hours: 2)) return null;
    await markSeen();
    try {
      final r = await api!.catchup(since);
      final n = (r['count'] as num? ?? 0).toInt() + ((r['pending'] as List?)?.length ?? 0);
      if (n == 0) return null;
      return {...r, 'away_hours': DateTime.now().toUtc().difference(since).inHours};
    } catch (_) {
      return null;
    }
  }

  // ---- "Hey Santosh" ----
  bool lockedMode = false;   // opened over the lock screen: only the voice call is shown
  /// The live voice call. Owned here so it keeps running while the owner moves between screens.
  late final CallSession voiceCall = CallSession(this);
  bool autoCall = false;     // start the call as soon as Baat opens
  int baatTick = 0;          // bumps when Baat should come to the front
  /// v0.49 something shared to Hoola from another app (files copied to the app cache + text); Chat picks it up.
  Map<String, dynamic>? pendingShare;
  int shareTick = 0;

  void onShared(Map<String, dynamic> s) {
    pendingShare = s;
    shareTick++;
    notifyListeners();
  }

  Map<String, dynamic>? takeShare() {
    final s = pendingShare;
    pendingShare = null;
    return s;
  }

  void wake({required bool locked}) {
    lockedMode = locked;
    autoCall = true;
    baatTick++;
    setMood(Mood.listening, hold: const Duration(seconds: 6));
  }

  Future<void> leaveLockedMode() async {
    if (!lockedMode) return;
    lockedMode = false;
    notifyListeners();
    await Native.leaveLockScreen();
  }

  DateTime? _locAt;

  /// Send the phone's position to Santosh (at most once a minute).
  Future<void> pushLocation() async {
    if (api == null) return;
    if (_locAt != null && DateTime.now().difference(_locAt!) < const Duration(minutes: 1)) return;
    _locAt = DateTime.now();
    try {
      final l = await Native.location();
      if (l == null) return;
      await api!.putLocation((l['lat'] as num).toDouble(), (l['lng'] as num).toDouble(), accuracy: (l['accuracy'] as num?)?.toDouble());
    } catch (_) {}
  }

  /// Safety net: show any pending confirm cards the live stream may have missed.
  Future<void> _syncBazar() async {
    try {
      final pend = await api!.bazarPending();
      var added = false;
      for (final c in pend) {
        final id = c['id'] as String? ?? '';
        if (id.isEmpty || _bazar.containsKey(id)) continue;
        _bazar[id] = FeedItem('bazar', c);
        feed.add(_bazar[id]!);
        added = true;
      }
      if (added) notifyListeners();
    } catch (_) {}
  }

  Future<void> refreshBazar() => _syncBazar();

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
    feed.add(FeedItem('note', {'text': ok ? g('App jud gaya ✓ Ab $aName order kar sakta hai.') : 'App link nahi ho paya, dobara koshish kijiye.'}));
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
          _syncBazar();
          feelReply(p['text'] as String? ?? '');
          _replies.add(p);
          if (inBackground && !backgroundRunning && !pushOn) Device.instance.showNow(aName, p['text'] as String? ?? '');
          if (!voiceMode && _lastInputWasVoice && speakReplies && p['source'] == 'agent') _speak(p['text'] as String? ?? '');
        }
        break;
      case 'work':
        if (!_replaying) _onWork(Map<String, dynamic>.from(p));
        break;
      case 'typing':
        if (p['on'] != true && !_replaying) _scheduleWorkHide(const Duration(seconds: 4));
        typing = p['on'] == true && !_replaying;
        if (p['on'] == true) _steps = null;
        if (!typing) currentStep = null;
        if (typing && mood != Mood.care && mood != Mood.excited && mood != Mood.wow) setMood(Mood.think, hold: Duration.zero);
        if (!typing && !_replaying && (mood == Mood.think || mood == Mood.work)) setMood(userStressed ? Mood.care : Mood.idle, hold: Duration.zero);
        break;
      case 'step':
        if (_steps == null) {
          _steps = FeedItem('steps', {});
          feed.add(_steps!);
        }
        if (!_replaying) currentStep = p['state'] == 'running' ? p['label'] as String? : currentStep;
        if (!_replaying && p['state'] == 'running' && mood != Mood.care) setMood(Mood.work, hold: Duration.zero);
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
        final known = _emails[p['id'] as String];
        if (known != null) {
          known.data = {...known.data, ...p};      // same draft changed (file added / removed)
        } else {
          _emails[p['id'] as String] = FeedItem('email', Map<String, dynamic>.from(p));
          feed.add(_emails[p['id']]!);
        }
        break;
      case 'sheet':
      case 'form':
      case 'slides':
      case 'notebook':
      case 'youtube':
      case 'app_check':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        break;
      case 'hoola_knock':
      case 'hoola_connect':
        final hk = '${ev.kind}:${p['id']}';
        final had = _hoola[hk];
        if (had != null) {
          had.data = {...had.data, ...p};
        } else {
          _hoola[hk] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_hoola[hk]!);
        }
        hoolaTick++;
        break;
      case 'hoola_msg':
        final mi = FeedItem(ev.kind, Map<String, dynamic>.from(p));
        if (p['id'] != null) _hoola['hoola_msg:${p['id']}'] = mi;
        feed.add(mi);
        hoolaTick++;
        break;
      case 'hoola_group':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        hoolaTick++;
        break;
      case 'hoola_update':                 // v0.43 the avatar looked at it: what it saw + reply ideas fill the card
        final up = {if (p['seen'] != null) 'seen': p['seen'], if (p['insight'] != null) 'insight': p['insight']};
        for (final k in ['hoola_knock:${p['msg_id']}', 'hoola_msg:${p['msg_id']}']) {
          final it = _hoola[k];
          if (it != null) it.data = {...it.data, ...up};
        }
        hoolaTick++;
        break;
      case 'hoola_group_post':
      case 'hoola_samaj':
        if (p['quiet'] != true) feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        hoolaTick++;
        break;
      case 'hoola_outbox':
      case 'hoola_ticket':
      case 'hoola_chain':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        hoolaTick++;
        break;
      case 'hoola_lesson':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        hoolaTick++;
        break;
      case 'photos_pick':
        final pk = '${p['pick_id']}';
        final had = _picks[pk];
        if (had != null) {
          had.data = {...had.data, ...p};        // waiting -> ready
        } else {
          _picks[pk] = FeedItem('photos_pick', Map<String, dynamic>.from(p));
          feed.add(_picks[pk]!);
        }
        break;
      case 'calendar_event':
        final cid = '${p['id']}';
        final had = _calEvents[cid];
        if (had != null && p['status'] != 'soon') {
          had.data = {...had.data, ...p};
        } else {
          _calEvents[cid] = FeedItem('calendar_event', Map<String, dynamic>.from(p));
          feed.add(_calEvents[cid]!);
        }
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
          if (inBackground && !_replaying && !pushOn) Device.instance.showNow('$aName: approve karein', '${p['title'] ?? ''} ${p['amount'] ?? ''}');
          if (!_replaying) setMood(Mood.think, hold: const Duration(seconds: 10));
        }
        break;
      case 'bazar_open':
        feed.add(FeedItem('open', Map<String, dynamic>.from(p)));
        break;
      case 'bazar_link':
        feed.add(FeedItem('link', Map<String, dynamic>.from(p)));
        break;
      case 'pc_file':
        feed.add(FeedItem('pc_file', Map<String, dynamic>.from(p)));
        if (inBackground && !_replaying && !pushOn) {
          Device.instance.showNow(p['source'] == 'bazar' ? '$aName ne PDF banaya' : 'PC se file aayi', p['name'] as String? ?? '');
        }
        break;
      case 'artifact':
        final aid = p['id'] as String? ?? '';
        if (aid.isEmpty) break;
        final prev = _artifacts[aid];
        final nowReady = p['status'] == 'ready' &&
            (prev == null || prev.data['status'] != 'ready' || prev.data['version'] != p['version']);
        if (prev != null) {
          prev.data = {...prev.data, ...p};
        } else {
          _artifacts[aid] = FeedItem('artifact', Map<String, dynamic>.from(p));
          feed.add(_artifacts[aid]!);
        }
        if (!_replaying) {
          latestArtifact = Map<String, dynamic>.from(_artifacts[aid]!.data);
          artifactTick++;
          if (nowReady && inBackground && !pushOn) Device.instance.showNow('$aName ne banaya', p['title'] as String? ?? '');
        }
        break;
      case 'browser':
        final bsid = p['session_id'] as String? ?? '';
        if (bsid.isEmpty) break;
        final bprev = _browsers[bsid];
        if (bprev != null) {
          bprev.data = {...bprev.data, ...p};
        } else {
          _browsers[bsid] = FeedItem('browser', Map<String, dynamic>.from(p));
          feed.add(_browsers[bsid]!);
        }
        if (!_replaying) {
          latestBrowser = Map<String, dynamic>.from(_browsers[bsid]!.data);
          artifactTick++;
        }
        break;
      case 'device_action':
        // in the background the native service does it (screens can't be opened from the background)
        if (!(inBackground && (backgroundRunning || pushOn))) await _runAction(p, at: ev.at);
        break;
      case 'device_action_result':
        if (p['status'] == 'done') {
          final what = {'set_alarm': 'Alarm laga diya', 'set_timer': 'Timer shuru', 'add_calendar_event': 'Calendar khul gaya', 'open_url': 'Phone par khul gaya', 'tv_play': 'Channel chal raha hai'};
          feed.add(FeedItem('note', {'text': '${what[p['type']] ?? 'Ho gaya'} ✓'}));
        }
        break;
      case 'home_device':
        unawaited(_runHomeDevice(Map<String, dynamic>.from(p), at: ev.at));
        break;
      case 'bt_request':
        unawaited(_runBt(Map<String, dynamic>.from(p), at: ev.at));
        break;
    }
    notifyListeners();
  }

  /// A Ghar command from Santosh (AC by IR, TV by Bluetooth/DIAL, music): run it once on this phone, then tell the
  /// server, which saves the AC's new state only when the phone says it was sent.
  Future<void> _runHomeDevice(Map<String, dynamic> a, {DateTime? at}) async {
    final id = a['command_id'] as String?;
    if (id == null) return;
    final done = _prefs.getStringList('done_home') ?? <String>[];
    if (done.contains(id)) return;
    // never fire an old AC/TV command when the chat history replays on start
    if (at != null && DateTime.now().toUtc().difference(at) > const Duration(minutes: 2)) return;
    if (!await Native.claim(id)) return; // the background service already did it
    final kept = done.length > 200 ? done.sublist(done.length - 200) : done;
    await _prefs.setStringList('done_home', [...kept, id]);
    var res = await Native.homeRun(a);
    if (res == 'permission') {
      await Native.homeAskBluetooth();
      res = 'TV ke liye "Nearby devices" ki permission dijiye, phir dobara boliye.';
    }
    final ok = res == 'ok';
    if (!ok) feed.add(FeedItem('note', {'text': 'Ghar: ${btWhy(res)}'}));
    try {
      await api?.homeResult(id, ok, ok ? '' : res);
    } catch (_) {}
    notifyListeners();
  }

  // ---- Hoola Work Theatre: the 3D scene of the tool Hoola is running right now ----
  Map<String, dynamic>? work;                       // latest `work` event {id, tool, scene, phase, label, data}
  final List<Map<String, dynamic>> workLog = [];   // this task's tool calls, oldest first
  bool workMin = false;
  Timer? _workHide;

  void _onWork(Map<String, dynamic> p) {
    final phase = p['phase'] as String? ?? 'start';
    if (phase == 'start') {
      _workHide?.cancel();
      if (work == null) workLog.clear();
    }
    work = p;
    if (p['id'] != 'stop') {
      final i = workLog.indexWhere((w) => w['id'] == p['id']);
      if (i >= 0) {
        workLog[i] = p;
      } else {
        workLog.add(p);
        if (workLog.length > 12) workLog.removeAt(0);
      }
    }
    if (phase == 'stopped') _scheduleWorkHide(const Duration(seconds: 2));
    notifyListeners();
  }

  void _scheduleWorkHide(Duration d) {
    if (work == null || work!['phase'] == 'waiting') return;
    _workHide?.cancel();
    _workHide = Timer(d, () {
      if (work != null && work!['phase'] != 'start' && work!['phase'] != 'waiting') {
        work = null;
        notifyListeners();
      }
    });
  }

  void toggleWorkMin() {
    workMin = !workMin;
    notifyListeners();
  }

  void closeWork() {
    work = null;
    notifyListeners();
  }

  /// "Rokiye": Hoola finishes the step it is on and starts nothing new.
  Future<void> stopWork() async {
    final c = conversationId;
    if (c == null) return;
    try {
      await api?.stopTurn(c);
    } catch (_) {}
  }

  /// A Bluetooth job from Hoola (scan, pair, connect, TV remote pairing): run it once on this phone, answer the server.
  Future<void> _runBt(Map<String, dynamic> a, {DateTime? at}) async {
    final id = a['request_id'] as String?;
    if (id == null) return;
    if (at != null && DateTime.now().toUtc().difference(at) > const Duration(minutes: 2)) return;
    if (!await Native.claim(id)) return;
    final args = Map<String, dynamic>.from(a['args'] as Map? ?? const {});
    final action = a['action'] as String? ?? 'status';
    if (action == 'scan' || action == 'pair' || action == 'tv_pair') {
      feed.add(FeedItem('note', {'text': {'scan': 'Bluetooth: aas-paas ke device dhoondh raha hoon…',
          'pair': 'Bluetooth: jod raha hoon, Android ka "Pair" dabaiye', 'tv_pair': 'Bluetooth: TV se jod raha hoon…'}[action]}));
      notifyListeners();
    }
    final r = await Native.btRun(action, args);
    final err = r['error'] as String? ?? '';
    if (err == 'permission') feed.add(FeedItem('note', {'text': 'Bluetooth ke liye "Nearby devices" ki permission dijiye.'}));
    try {
      await api?.btResult(id, r['ok'] == true, Map<String, dynamic>.from(r['result'] as Map? ?? const {}), err);
    } catch (_) {}
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
    _moodTimer?.cancel();
    _replies.close();
    _sub?.cancel();
    super.dispose();
  }
}
