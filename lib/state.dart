import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'call_session.dart';
import 'ui/bluetooth_panel.dart' show btWhy;
import 'device.dart';
import 'emotion.dart';
import 'hoola.dart';
import 'i18n.dart';
import 'native.dart';
import 'ui/avatar_look.dart' show currentLook, lookFits;

class FeedItem {
  FeedItem(this.kind, this.data);
  final String kind; // message / steps / campaign / note
  Map<String, dynamic> data;
  final List<Map<String, dynamic>> steps = [];
  int? eid;        // v0.158 the server event that first made it (its place in the chat's story)
  String? call;    // the voice call whose tool made it (only those cards show in that call)
  String? key;     // v0.179 one card = one key (kind + its own id) - the server's own identity for this card
  DateTime? at;    // v0.179 when this card's latest state arrived (old asks leave the waiting strip)
  bool live = false; // arrived live (not loaded from history)
}

/// v0.158 statuses that mean "this card waits for her answer / tap now" (v0.187: + blocked = a goal waiting on her).
const waitStatuses = {
  'waiting', 'pending', 'needs_tap', 'waiting_payment', 'waiting_sign', 'notice_waiting', 'minutes_waiting', 'awaiting',
  'needs_approval', 'pending_tap', 'ask', 'blocked',
};

/// v0.179 a card that has waited this long stops nagging from the strip (the server's TTL closes it properly;
/// this is the phone-side net for old servers and odd states).
const needsHerMaxH = 48;

/// Does this chat card wait for her right now (by its own latest state)?
bool feedNeedsHer(FeedItem f) {
  if (f.kind == 'message' || f.kind == 'note' || f.kind == 'steps') return false;
  final d = f.data;
  final st = '${d['status'] ?? d['state'] ?? ''}'.toLowerCase();
  if (waitStatuses.contains(st) || const {'employee_ask', 'operator_ask', 'studio_approval', 'ask_form', 'pg_write'}.contains(f.kind)) {
    if (d['decided'] == true || d['answered'] == true) return false;
    final old = f.at != null && DateTime.now().toUtc().difference(f.at!).inHours >= needsHerMaxH;
    if (old) return false;                          // v0.179 days-old asks leave the strip (the card itself stays in the feed)
    if (waitStatuses.contains(st)) return true;
    return st.isEmpty || st == 'open';
  }
  return false;
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
  /// Hoola's own server. Fixed in the app (never typed or shown); a test build can override it with
  /// --dart-define=HOOLA_SERVER=https://... . Phones set up on the old address move here by themselves: same server, same key.
  static const String hoolaServer = String.fromEnvironment('HOOLA_SERVER', defaultValue: 'https://hoola.ainewtika.com');
  String get serverUrl => hoolaServer;
  String get apiKey => _prefs.getString('key') ?? '';
  String get language => _prefs.getString('lang') ?? 'en-IN';   // v0.164.2 English is the default UI language
  /// v0.181 the language the CALL starts in: Hinglish, not the UI language. Fresh users were getting English-locked
  /// calls in a Hinglish product; the server's learned language (voicelang) still wins after her first calls.
  String get voiceLang => _prefs.getString('vlang') ?? 'hi-IN';
  bool get speakReplies => _prefs.getBool('speak') ?? true;
  bool get configured => apiKey.isNotEmpty;
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
  /// '' = Santosh; f001..f100 / m001..m100 = the 3D look the owner picked (must match the avatar's gender).
  String get aLook {
    final l = (avatar['look'] as String?) ?? _prefs.getString('a_look') ?? '';
    return lookFits(l, aFemale ? 'f' : 'm') ? l : '';
  }

  Future<void> _keepLook() async {
    await _prefs.setString('a_look', aLook);
    currentLook.value = aLook;
  }
  bool get needsAvatarSetup => connected && avatarLoaded && avatar['setup_done'] != true;
  Map<String, dynamic> get avatarRules => Map<String, dynamic>.from(avatar['rules'] as Map? ?? const {});

  /// v0.164.2 UI text in her language: English default; हिंदी keeps the classic gender-aware Hinglish;
  /// other languages fall back to English until their table fills in (lib/i18n.dart).
  /// {a} = avatar name, {x} = a value the caller passes.
  String g(String text, {String? a, String? x}) {
    final code = language.split('-').first;
    var t = code == 'hi' ? (aFemale ? genderedHi(text) : text) : tr(language, text);
    return t.replaceAll('{a}', a ?? aName).replaceAll('{x}', x ?? '');
  }

  Future<void> loadAvatar() async {
    try {
      await _applyAvatar(await api!.avatarGet());
    } catch (_) {
      // older server without /api/avatar: keep "Santosh", never block the app on setup
      avatarLoaded = false;
    }
  }

  /// v0.98 this month's AI spend vs her limit (from /api/bootstrap; the Kharcha screen has the full report).
  Map<String, dynamic>? usage;

  /// v0.98 a card made on the phone itself (e.g. "call kaisi rahi?") joins the chat feed.
  void addLocalCard(String kind, Map<String, dynamic> data) {
    feed.add(FeedItem(kind, data));
    notifyListeners();
  }

  Future<void> _applyAvatar(Map<String, dynamic> a) async {
    avatar = a;
    avatarLoaded = true;
    await _prefs.setString('a_name', aName);
    await _prefs.setString('a_gender', aFemale ? 'f' : 'm');
    await _keepLook();
    final v = avatar['voice'] as String?;
    if (v != null && v.isNotEmpty && v != voiceName) await _prefs.setString('voice', v);
    notifyListeners();
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
  final Map<String, FeedItem> _deals = {};     // v0.102 one live card per Hoola deal
  final Map<String, FeedItem> _upiCards = {};  // v0.109 one card per UPI transfer, updated in place
  final Map<String, FeedItem> _pickCards = {}; // v0.105 one live card per pick list (packer side)
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
  Timer? _typingGuard;            // v0.178 typing shows only while the turn is really alive (the stream refreshes it)
  FeedItem? _streamItem;          // v0.178 the reply being written right now (grows word by word, live-only)
  FeedItem? _sayItem;             // v0.187 the little true lines between steps ("12 mails aaye"), live-only
  String? error;
  bool inBackground = false;

  /// v0.83 a website job waits for an OTP: the next OTP SMS gets Android's one-tap "Allow" sheet and only the code
  /// goes into the waiting box (no SMS permission; a bank / payment SMS is never filled).
  final Set<String> _otpSmsWait = {};
  Future<void> _otpFromSms(String id, int digits) async {
    if (api == null || _otpSmsWait.contains(id)) return;
    _otpSmsWait.add(id);
    final r = await Native.otpConsent(digits: digits);
    if (!_otpSmsWait.remove(id)) return;          // answered another way meanwhile
    final code = r['code'];
    if (code is String && code.isNotEmpty) {
      try {
        await api!.operatorAnswer(id, true, answer: code);
      } catch (_) {}
    } else if (r['error'] == 'bank') {
      Device.instance.showNow('$aName', 'Yeh bank / payment ka OTP lagta hai: main nahi bharunga, aap khud live screen mein bhariye.');
    }
  }
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
  final Map<String, FeedItem> _goals = {};   // v0.187 lamba kaam: one live goal card per goal id, updated in place
  final Map<String, FeedItem> _bazar = {};   // confirm cards by approval id
  final Map<String, FeedItem> _studio = {};       // v0.68 video studio: one live card per project
  final Map<String, FeedItem> _studioAsks = {};   // its price cards
  int studioTick = 0;
  final Map<String, FeedItem> _opTasks = {};   // v0.67 Computer Operator: one live card per job
  final Map<String, FeedItem> _opAsks = {};    // its questions for the owner, updated in place
  int operatorTick = 0;
  final Map<String, FeedItem> _videoJobs = {}; // v0.65 video editor: one live card per job, updated in place
  final Map<String, FeedItem> _pgCards = {};  // v0.147 Postgres change cards, one per card id
  final Map<String, FeedItem> _b3dCards = {};  // v0.141 3D Studio: one live card per project, updated in place
  final Map<String, FeedItem> _nbCards = {};   // v0.155 Notebook Studio: one live card per output, updated in place
  int notebookTick = 0;                        // v0.155 bumps on notebook / notebook_output events (Notebook screens refresh)
  int videoTick = 0;                          // bumps on every video_job event (the editor screen refreshes)
  final Map<String, FeedItem> _empAsks = {};  // Hoola Employee: actions waiting for the owner's tap, by ask id
  int employeeTick = 0;                       // bumps on any employee event (the Employee screen can refresh)
  final Map<String, FeedItem> _darziCards = {}; // v0.82 Darzi: price cards by id, 'ready' drafts by order, updated in place
  int darziTick = 0;                          // bumps on any darzi event (the Darzi screen refreshes)
  final Map<String, FeedItem> _chaiPlans = {}; // v0.84 Chai: one plan card per day, its order cards updated in place
  int chaiTick = 0;                           // bumps on galla / chai events (the Chai screen refreshes)
  final Map<String, FeedItem> _mshopCards = {}; // v0.88 Mobile shop: bill cards and 'ready' drafts by job, updated in place
  int mshopTick = 0;                          // bumps on mobile shop events (the Mobile shop screen refreshes)
  final Map<String, FeedItem> _phonedocCards = {}; // v0.90 Phone Doctor: one live card per case
  int phonedocTick = 0;                       // bumps on Phone Doctor events
  final Map<String, FeedItem> _gstCards = {};    // v0.93 GST: one live card per return
  int gstTick = 0;                            // bumps on GST events (the GST screen refreshes)
  final Map<String, FeedItem> _payCards = {};    // v0.94 Payroll: one live card per salary run
  int payTick = 0;                            // bumps on payroll events
  final Map<String, FeedItem> _officeCards = {}; // v0.85 Daftar: spend cards by id, nudge drafts by id, updated in place
  int officeTick = 0;                          // bumps on any office event (the Office screen refreshes)
  final Map<String, FeedItem> _lekhakCards = {}; // v0.87 Lekhak: one doc card + one sign card per document, updated in place
  final Map<String, FeedItem> _askForms = {}; // v0.97 form cards, updated in place when answered / closed
  int lekhakTick = 0;                          // bumps on any lekhak event (the Lekhak screen refreshes)
  int brandTick = 0;                           // v0.118 bumps on brand events (Brand screen refreshes)
  int siteTick = 0;                            // v0.121 bumps on website events (Website screens refresh)
  final Map<String, FeedItem> _siteCards = {}; // v0.121 one card per website, updated in place
  int appTick = 0;                             // v0.128 bumps on app design events (App designer screens refresh)
  final Map<String, FeedItem> _appCards = {};  // v0.128 one card per app design, updated in place
  final Map<String, FeedItem> _androidCards = {};  // v0.132 one native build card per app
  final Map<String, FeedItem> _brandCards = {}; // v0.118 one card per design, updated in place
  int sevaTick = 0;                            // v0.133 Seva suite screens refresh on their events
  final Map<String, FeedItem> _sevaCards = {};  // v0.133 one card per id where the suite updates a card in place
  int techTick = 0;                            // v0.137 Tech suite screens refresh on their events
  final Map<String, FeedItem> _techCards = {};  // v0.137 one card per id where the suite updates a card in place
  int safarTick = 0;                           // v0.139 Safar suite screens refresh on their events
  final Map<String, FeedItem> _safarCards = {}; // v0.139 one card per id where the suite updates a card in place
  int gharTick = 0;                            // v0.144 Makaan suite screens refresh on their events
  final Map<String, FeedItem> _gharCards = {};  // v0.144 one card per id where the suite updates a card in place
  int kanoonTick = 0;                          // v0.150 Kanoon suite screens refresh on their events
  final Map<String, FeedItem> _kanoonCards = {}; // v0.150 one card per id where the suite updates a card in place
  int mehmaanTick = 0;                         // v0.152 Mehmaan suite screens refresh on their events
  final Map<String, FeedItem> _mehmaanCards = {}; // v0.152 one card per id where the suite updates a card in place
  int kalaTick = 0;                            // v0.156 Kala suite screens refresh on their events
  final Map<String, FeedItem> _kalaCards = {};  // v0.156 one card per id where the suite updates a card in place
  int adsTick = 0;                             // v0.108 bumps on ads events (the Ads screen refreshes)
  final Map<String, FeedItem> _adsPlans = {};   // v0.108 one card per budget plan, changes updated in place
  int kalamTick = 0;                           // v0.101 bumps on content-writer events (the Kalam screen refreshes)
  final Map<String, FeedItem> _kalamCards = {}; // v0.101 one card per piece / publish request, updated in place
  final Map<String, FeedItem> _deskCards = {}; // v0.108 Sheet Milaan / document edit cards, updated in place
  int teleTick = 0;                            // v0.99 bumps on telecaller events (the Telecaller screen refreshes)
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
  List<Map<String, dynamic>> doneToday = [];   // v0.177: ticked today — the daily completed feed

  StreamSubscription<SantoshEvent>? _sub;
  final FlutterTts _tts = FlutterTts();
  bool _lastInputWasVoice = false;
  bool _replaying = true;
  /// True while the chat history is replaying after a (re)connect: those items show at once, without animation.
  bool get replaying => _replaying;
  DateTime _connectedAt = DateTime.now().toUtc();

  Future<void> saveSettings({String? server, String? key, String? lang, bool? speak}) async {
    if (key != null) await _prefs.setString('key', key.trim());
    if (lang != null) await _prefs.setString('lang', lang);
    if (speak != null) await _prefs.setBool('speak', speak);
    notifyListeners();
  }

  /// v0.90 Phone Doctor: the phone checks itself (settings, battery, storage, network; nothing personal) and tells the server.
  Future<Map<String, dynamic>> sendPhoneCheck() async {
    try {
      final snap = await Native.phoneCheck();
      if (snap.isEmpty || api == null) return const {};
      return await api!.phonedocCheck(snap);
    } catch (_) {
      return const {};
    }
  }

  /// Opens the exact settings screen (or official page) a Phone Doctor step needs.
  Future<void> openPhoneScreen(String key, {String package = '', String url = ''}) async {
    try {
      if (key.isNotEmpty) {
        await Native.openSetting(key, package: package);
      } else if (url.isNotEmpty) {
        await Native.openExternal(url: url);
      }
    } catch (_) {}
  }

  // v0.158.1 the server restarts for ~20-40 s on every update: the app keeps trying by itself instead of
  // stopping at "Server se connect nahi ho paya" until she taps the banner or reopens the app.
  bool _connecting = false;
  Timer? _retryTimer;
  int _retryWait = 0;
  bool _keyRefused = false;

  /// Try again soon (3 s, 6 s, 12 s ... up to 30 s) unless the key itself was refused.
  void _scheduleRetry() {
    if (_keyRefused || !configured) return;
    _retryTimer?.cancel();
    _retryWait = _retryWait == 0 ? 3 : (_retryWait >= 15 ? 30 : _retryWait * 2);
    _retryTimer = Timer(Duration(seconds: _retryWait), () {
      if (!connected && !_connecting) connect();
    });
  }

  /// Called when the app comes back on screen: reconnect at once if the last try failed.
  void reconnectIfNeeded() {
    if (connected || _connecting || _keyRefused || !configured) return;
    _retryTimer?.cancel();
    _retryWait = 0;
    connect();
  }

  Future<void> connect({bool fresh = false}) async {
    if (_connecting) return;
    _connecting = true;
    _retryTimer?.cancel();
    try {
      await _connect(fresh: fresh);
    } finally {
      _connecting = false;
    }
  }

  Future<void> _connect({bool fresh = false}) async {
    error = null;
    _keyRefused = false;
    await _sub?.cancel();
    _clearStory();
    _storyLimit = 60;
    hasOlder = false;
    lastEventId = 0;
    api = Api(serverUrl, apiKey);
    try {
      // v0.98 one call brings everything the app needs to open (it used to wait for 8 calls in a row)
      Map<String, dynamic>? boot;
      try {
        boot = await api!.bootstrap(fresh ? null : _prefs.getString('conv'), fresh: fresh);
      } on ApiException catch (e) {
        if (e.status == 401) rethrow;
        boot = null; // an older server: the old way below
      }
      final h = boot?['health'] is Map ? Map<String, dynamic>.from(boot!['health'] as Map) : await api!.health();
      dryRun = h['dry_run'] == true;
      brainReady = h['brain_configured'] == true;
      realtimeVoice = (h['features'] as List?)?.contains('realtime_voice') ?? false;
      voiceDefault = h['voice_default'] as String? ?? 'Puck';
      voices = List<Map<String, dynamic>>.from((h['voices'] as List?) ?? const []);
      googleLogin = h['google_login'] == true;
      conversationId = boot?['conversation_id'] as String? ?? (fresh ? null : _prefs.getString('conv'));
      if (conversationId != null && boot == null) {
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
      // v0.62 the bubble chat + home-screen widget talk to this same chat
      unawaited(Native.chatLink(serverUrl, apiKey, conversationId!));
      unawaited(screenSync());
      connected = true;
      _connectedAt = DateTime.now().toUtc();
      notifyListeners();
      await _openStory();   // v0.158 the chat in order (history from /timeline, then live from where it ended)
      await Device.instance.init();
      await Device.instance.askNotificationPermission();
      if (!(_prefs.getBool('asked_location') ?? false)) {
        await _prefs.setBool('asked_location', true);
        await Native.askLocation();
      }
      pushLocation();
      if (boot != null) {
        // v0.177: boot['lists'] is the full {lists, done_today} dict; older servers send just the inner map
        final bl = boot['lists'];
        if (bl is Map && bl['lists'] is Map) {
          lists = Map<String, dynamic>.from(bl['lists'] as Map);
          doneToday = List<Map<String, dynamic>>.from((bl['done_today'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        } else if (bl is Map) {
          lists = Map<String, dynamic>.from(bl);
        }
        if (boot['routines'] is List) routines = List<Map<String, dynamic>>.from((boot['routines'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
        final me = boot['me'] is Map ? Map<String, dynamic>.from(boot['me'] as Map) : null;
        account = me != null && me['signed_in'] == true ? me : null;
        if (boot['avatar'] is Map) {
          await _applyAvatar(Map<String, dynamic>.from(boot['avatar'] as Map));
        } else {
          await loadAvatar();
        }
        usage = boot['usage'] is Map ? Map<String, dynamic>.from(boot['usage'] as Map) : null;
        notifyListeners();
        for (final a in List<Map<String, dynamic>>.from(((boot['pending_actions'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)))) {
          await _runAction(a);
        }
      } else {
        await refreshLists();
        await refreshRoutines();
        await refreshAccount();
        await loadAvatar();
        for (final a in await api!.pendingActions()) {
          await _runAction(a);
        }
      }
    } catch (e) {
      connected = false;
      _keyRefused = e is ApiException && e.status == 401;
      if (_keyRefused) {
        error = 'API key galat hai. Settings mein theek kijiye.';
      } else {
        error = 'Hoola server se jud raha hoon… (server abhi update / restart ho raha ho sakta hai, main khud dobara koshish kar raha hoon. Abhi try karne ke liye yahan tap kijiye.)';
        _scheduleRetry();
      }
      notifyListeners();
      return;
    }
    _retryWait = 0;
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
    await _prefs.setString('key', token);
    await connect(fresh: true);
  }

  /// Log out of Hoola on this phone: the server forgets this session, the background service stops, setup shows again.
  Future<void> signOut() async {
    try {
      await api?.logout();
    } catch (_) {}
    await _sub?.cancel();
    _sub = null;
    try {
      await Native.stop();
    } catch (_) {}
    await _prefs.remove('key');
    await _prefs.remove('conv');
    connected = false;
    api = null;
    notifyListeners();
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
      widgetSync();
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
      final r = await api!.lists();
      lists = Map<String, dynamic>.from(r['lists'] as Map? ?? const {});
      doneToday = List<Map<String, dynamic>>.from((r['done_today'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
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
      if (decision == 'approve' && open != null && open['kind'] == 'upi_copy') {
        // v0.120 this UPI app refuses payment links to a person: copy the UPI ID, open the app itself
        await Clipboard.setData(ClipboardData(text: open['vpa'] as String? ?? ''));
        final res = await Native.openExternal(package: open['package'] as String? ?? '');
        if (res != 'ok') feed.add(FeedItem('note', {'text': res}));
      } else if (decision == 'approve' && open != null && (open['kind'] == 'upi' || open['kind'] == 'app')) {
        final res = await Native.openExternal(url: open['url'] as String? ?? '', package: open['package'] as String? ?? '');
        if (res != 'ok') {
          feed.add(FeedItem('note', {'text': res}));
          // v0.109 the app didn't open: the server asks her (and offers copy-and-pay) instead of waiting forever
          final ref = open['txn_ref'] as String? ?? '';
          if (open['kind'] == 'upi' && ref.isNotEmpty) {
            try { await api!.upiResult(ref, result: 'none', package: open['package'] as String? ?? ''); } catch (_) {}
          }
        }
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

  /// v0.62 The home-screen widget: avatar name, Hoola's last line, the next reminder.
  /// v0.127 Hoola Screen: keep a fresh view-only board link on the phone so a connected mini screen / TV
  /// shows Hoola's live work by itself. The link is renewed every 20 days (it lives 30).
  Future<Map<String, dynamic>> screenSync({bool force = false, bool? on, bool? awake}) async {
    try {
      final saved = _prefs.getString('hoola_screen_url') ?? '';
      final at = _prefs.getInt('hoola_screen_at') ?? 0;
      final age = DateTime.now().millisecondsSinceEpoch - at;
      String? url;
      if (api != null && (force || saved.isEmpty || age > const Duration(days: 20).inMilliseconds)) {
        final r = await api!.screenLink();
        var u = '${r['url'] ?? ''}';
        if (u.startsWith('/')) u = '${serverUrl.endsWith('/') ? serverUrl.substring(0, serverUrl.length - 1) : serverUrl}$u';
        if (u.startsWith('http')) {
          url = u;
          await _prefs.setString('hoola_screen_url', u);
          await _prefs.setInt('hoola_screen_at', DateTime.now().millisecondsSinceEpoch);
        }
      }
      return await Native.screenSetup(url: url ?? (saved.isEmpty ? null : saved), on: on, awake: awake);
    } catch (_) {
      return await Native.screenInfo();
    }
  }

  String get screenUrl => _prefs.getString('hoola_screen_url') ?? '';

  Future<void> screenRevoke() async {
    await api!.screenRevoke();
    await _prefs.remove('hoola_screen_url');
    await screenSync(force: true);
  }

  Future<void> widgetSync({String? last}) async {
    try {
      final r = reminders.isEmpty ? '' : [reminders.first['text'], reminders.first['when']].whereType<String>().join(' · ');
      await Native.widgetUpdate(name: aName, last: last, next: r);
    } catch (_) {}
  }

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

  // ---------------------------------------------------------------- v0.158 the chat as one story, in order
  bool hasOlder = false;          // older chat history exists above (tap "Purani baatein" to load)
  bool loadingOlder = false;
  int _storyLimit = 60;
  Timer? _healTimer;
  Timer? _replayGuard;
  bool _healing = false;
  int healFixes = 0;              // times this session's self-check found the chat different and reloaded it
  List<Map<String, dynamic>> chatList = [];

  void _clearStory() {
    feed.clear();
    _streamItem = null;
    _hoola.clear();
    _deals.clear();
    _upiCards.clear();
    _pickCards.clear();
    _campaigns.clear();
    _emails.clear();
    _bazar.clear();
    _studio.clear();
    _studioAsks.clear();
    _opTasks.clear();
    _opAsks.clear();
    _videoJobs.clear();
    _pgCards.clear();
    _b3dCards.clear();
    _nbCards.clear();
    _empAsks.clear();
    _darziCards.clear();
    _chaiPlans.clear();
    _mshopCards.clear();
    _phonedocCards.clear();
    _gstCards.clear();
    _payCards.clear();
    _officeCards.clear();
    _lekhakCards.clear();
    _askForms.clear();
    _siteCards.clear();
    _appCards.clear();
    _androidCards.clear();
    _brandCards.clear();
    _sevaCards.clear();
    _techCards.clear();
    _safarCards.clear();
    _gharCards.clear();
    _kanoonCards.clear();
    _mehmaanCards.clear();
    _kalaCards.clear();
    _adsPlans.clear();
    _kalamCards.clear();
    _deskCards.clear();
    _artifacts.clear();
    _browsers.clear();
    _calEvents.clear();
    _picks.clear();
    _steps = null;
  }

  /// Cards in this chat that wait for her now (the "Aapki haan chahiye" strip), newest first.
  List<FeedItem> get waitingCards => feed.reversed.where(feedNeedsHer).toList();

  /// Load the chat's story from the server in order, then stream live from where it ended.
  Future<void> _openStory({bool reload = false}) async {
    final conv = conversationId;
    if (conv == null || api == null) return;
    await _sub?.cancel();
    _replaying = true;
    var after = 0;
    try {
      final tl = await api!.timeline(conv, limit: _storyLimit);
      _clearStory();
      for (final j in (tl['events'] as List? ?? const [])) {
        await _onEvent(SantoshEvent.fromJson(Map<String, dynamic>.from(j as Map)));
      }
      hasOlder = tl['has_more'] == true;
      after = (tl['last_event_id'] as num?)?.toInt() ?? lastEventId;
      if (after > lastEventId) lastEventId = after;
    } on ApiException catch (e) {
      if (e.status == 401) rethrow;
      if (!reload) _clearStory();
      after = reload ? lastEventId : 0;   // an older server without /timeline: the old full replay
    } catch (_) {
      if (!reload) _clearStory();
      after = reload ? lastEventId : 0;
    }
    notifyListeners();
    // v0.178 the phone also streams the reply as it is written (word by word, like a person); an older server
    // simply ignores the live flag. A reply caught mid-writing on reload continues from /live (we are still
    // replaying here by design: this item is the live continuation, not history).
    try {
      final snap = await api!.liveReply(conv);
      final t = (snap?['text'] as String? ?? '').trim();
      if (snap != null && t.isNotEmpty) {
        _streamItem = FeedItem('stream', {'turn': snap?['turn'] ?? '', 'text': t, 'seg': snap?['seg'] ?? 0});
        feed.add(_streamItem!);
      }
    } catch (_) {}
    _sub = api!.events(conv, after: after, live: true).listen(_onEvent, onError: (e) {
      connected = false;
      if (e is ApiException && e.status == 401) {
        _keyRefused = true;
        error = 'API key galat hai. Settings mein theek kijiye.';
      } else {
        // v0.158.1 e.g. the chat is gone after a server change: open again by itself (a fresh chat if needed)
        error = 'Hoola server se dobara jud raha hoon…';
        if (e is ApiException && e.status == 404) _prefs.remove('conv');
        _scheduleRetry();
      }
      notifyListeners();
    });
    // the stream says when catching up is over (replay_end); an older server doesn't: give up waiting after 8 s
    _replayGuard?.cancel();
    _replayGuard = Timer(const Duration(seconds: 8), () => _replayDone());
    _healTimer?.cancel();
    _healTimer = Timer.periodic(const Duration(seconds: 90), (_) => unawaited(selfCheck()));
  }

  void _replayDone() {
    _replayGuard?.cancel();
    if (!_replaying) return;
    _replaying = false;
    applyBackground();
    _syncBazar();
    notifyListeners();
  }

  /// Older history above the first loaded item ("Purani baatein dikhao").
  Future<void> loadOlder() async {
    if (loadingOlder || !hasOlder) return;
    loadingOlder = true;
    notifyListeners();
    _storyLimit = (_storyLimit + 60).clamp(60, 400);
    await _openStory(reload: true);
    loadingOlder = false;
    notifyListeners();
  }

  /// v0.158 self-healing: the newest part of this chat must match the server's story (same items, same order);
  /// anything missing or out of order = reload the chat in order (and tell the server, for Hoola Jaanch).
  Future<void> selfCheck({String why = 'check'}) async {
    final conv = conversationId;
    if (_healing || conv == null || api == null || !connected || _replaying || inBackground || typing) return;
    _healing = true;
    try {
      final h = await api!.timelineHead(conv, n: 40);
      final want = List<int>.from(((h['ids'] as List?) ?? const []).map((e) => (e as num).toInt()));
      final mine = [for (final f in feed) if (f.eid != null) f.eid!];
      final have = mine.toSet();
      final floor = mine.isEmpty ? 0 : mine.first;
      final missing = want.where((i) => i >= floor && !have.contains(i)).length;
      var outOfOrder = 0;
      for (var i = 1; i < mine.length; i++) {
        if (mine[i] < mine[i - 1]) outOfOrder++;
      }
      // v0.179 the story's card keys must line up too: a card that survived as a zombie (same card shown twice
      // under different event ids) heals here, not just missing / reordered events.
      final wantKeys = List<String>.from(((h['keys'] as List?) ?? const []).map((e) => '$e'));
      final mineKeys = <int, String>{for (final f in feed) if (f.eid != null && (f.key ?? '').isNotEmpty) f.eid!: f.key!};
      var keyMismatch = 0;
      for (var i = 0; i < want.length && i < wantKeys.length; i++) {
        final k = mineKeys[want[i]];
        if (k != null && wantKeys[i].isNotEmpty && k != wantKeys[i]) keyMismatch++;
      }
      if (missing > 0 || outOfOrder > 0 || keyMismatch > 0) {
        healFixes++;
        unawaited(api!.chatHeal('missing $missing, out of order $outOfOrder, keys $keyMismatch ($why)',
            {'missing': missing, 'out_of_order': outOfOrder, 'key_mismatch': keyMismatch, 'items': mine.length}).catchError((_) {}));
        await _openStory(reload: true);
      }
    } catch (_) {
    } finally {
      _healing = false;
    }
  }

  /// Her old chats (newest first). Nothing is lost when she starts a new one.
  Future<void> refreshChats() async {
    try {
      final r = await api!.chats();
      chatList = List<Map<String, dynamic>>.from(((r['conversations'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
      notifyListeners();
    } catch (_) {}
  }

  /// Open one of her old chats.
  Future<void> openChat(String id) async {
    if (id == conversationId || api == null) return;
    conversationId = id;
    await _prefs.setString('conv', id);
    unawaited(api!.openChat(id).catchError((_) {}));
    unawaited(Native.chatLink(serverUrl, apiKey, id));
    _storyLimit = 60;
    lastEventId = 0;
    await _openStory();
    unawaited(refreshChats());
  }

  void _onMarker(SantoshEvent ev) {
    if (ev.kind == 'replay_end') {
      _replayDone();
    } else if (ev.kind == 'resync') {
      unawaited(_openStory(reload: true));   // too much to catch up: reload the chat in order
    }
  }

  Future<void> _onEvent(SantoshEvent ev) async {
    if (ev.isMarker) {
      _onMarker(ev);
      return;
    }
    final n0 = feed.length;
    await _handle(ev);
    for (var i = n0; i < feed.length; i++) {   // the new items get their place in the story (and their call)
      final f = feed[i];
      f.eid ??= ev.id;
      f.call ??= ev.call;
      f.key ??= ev.key;                        // v0.179 the server's card key (timeline rows carry it)
      f.at ??= ev.at;                          // v0.179 when this state arrived (old asks leave the waiting strip)
      if (!_replaying) f.live = true;
    }
  }

  Future<void> _handle(SantoshEvent ev) async {
    final p = ev.payload;
    if (ev.id > lastEventId) lastEventId = ev.id;
    switch (ev.kind) {
      case 'message':
        if (p['role'] == 'user') _steps = null;
        // v0.178 the bubble knows when it arrived: day separators and time stamps come from this
        feed.add(FeedItem('message', {...Map<String, dynamic>.from(p), 'at': ev.at.toIso8601String()}));
        final fresh = !_replaying && ev.at.isAfter(_connectedAt.subtract(const Duration(seconds: 5)));
        if (p['role'] == 'assistant' && fresh) {
          _syncBazar();
          feelReply(p['text'] as String? ?? '');
          _replies.add(p);
          widgetSync(last: p['text'] as String? ?? '');
          if (inBackground && !backgroundRunning && !pushOn) Device.instance.showNow(aName, p['text'] as String? ?? '');
          if (!voiceMode && _lastInputWasVoice && speakReplies && p['source'] == 'agent') _speak(p['text'] as String? ?? '');
        }
        if (p['role'] == 'assistant' && p['turn'] != null) _streamDrop(onlyTurn: p['turn'] as String?);   // v0.178 the bubble makes way for this final message
        break;
      case 'work':
        if (!_replaying) _onWork(Map<String, dynamic>.from(p));
        break;
      case 'reply_start':
        _streamDrop();                                   // a new reply begins: any leftover bubble goes
        _sayDrop();                                      // v0.187 and the old whisper too
        _streamItem = FeedItem('stream', {'turn': p['turn'] ?? '', 'text': '', 'seg': -1});
        feed.add(_streamItem!);
        notifyListeners();
        break;
      case 'delta':
        final turn = '${p['turn'] ?? ''}';
        if (_streamItem == null || '${_streamItem!.data['turn']}' != turn) {
          _streamDrop();
          _streamItem = FeedItem('stream', {'turn': turn, 'text': '', 'seg': -1});   // joined mid-reply
          feed.add(_streamItem!);
        }
        final seg = (p['seg'] as num?)?.toInt() ?? 0;
        final prevSeg = (_streamItem!.data['seg'] as num?)?.toInt() ?? -1;
        final cur = '${_streamItem!.data['text']}';
        _streamItem!.data['text'] = (cur.isEmpty || seg == prevSeg ? cur : '$cur\n\n') + '${p['text'] ?? ''}';
        _streamItem!.data['seg'] = seg;
        notifyListeners();
        break;
      case 'delta_reset':
        if (_streamItem != null && '${_streamItem!.data['turn']}' == '${p['turn'] ?? ''}') {
          _streamItem!.data['text'] = '';
          notifyListeners();
        }
        break;
      case 'reply_end':
        if (_streamItem != null && '${_streamItem!.data['turn']}' == '${p['turn'] ?? ''}') {
          if ('${_streamItem!.data['text']}'.trim().isEmpty) {
            feed.remove(_streamItem);   // nothing was shown: the final message arrives right after
            _streamItem = null;
          }
          notifyListeners();
        }
        _sayDrop();                     // v0.187 the whisper's job is done - the reply is here
        break;
      case 'say':                       // v0.187 one true line about what a tool just returned
        final text = '${p['text'] ?? ''}';
        if (text.isEmpty) break;
        if (_sayItem != null) {
          _sayItem!.data['text'] = text;
        } else {
          _sayItem = FeedItem('say', {'turn': p['turn'] ?? '', 'text': text});
          final at = _streamItem != null ? feed.indexOf(_streamItem!) : -1;
          if (at >= 0) {
            feed.insert(at, _sayItem!);
          } else {
            feed.add(_sayItem!);
          }
        }
        notifyListeners();
        break;
      case 'typing':
        if (p['on'] == true) {
          _typingGuard?.cancel();
          _typingGuard = Timer(const Duration(seconds: 75), () {
            // v0.178 the stream stopped refreshing (turn over / server gone): the dots must not hang for ever
            if (typing) {
              typing = false;
              currentStep = null;
              notifyListeners();
            }
          });
        } else {
          _typingGuard?.cancel();
        }
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
      case 'motion':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        if (ev.kind == 'notebook') notebookTick++;
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
      case 'hoola_deal':                   // v0.102: info steps update the card; a step that needs her brings it down
        final dk = '${p['id']}';
        final dOld = _deals[dk];
        if (dOld != null) {   // v0.158 updated where it is (a step that needs her shows in "Aapki haan chahiye")
          dOld.data = p['card'] == 'info' ? {...dOld.data, ...p} : Map<String, dynamic>.from(p);
        } else {
          _deals[dk] = FeedItem('hoola_deal', Map<String, dynamic>.from(p));
          feed.add(_deals[dk]!);
        }
        hoolaTick++;
        break;
      case 'upi_result':                   // v0.109 what the UPI app said after 'Paisa bhejo' (or her answer)
        final uk = '${p['txn_ref']}';
        final uOld = _upiCards[uk];
        if (uOld != null) {
          uOld.data = Map<String, dynamic>.from(p);
        } else {
          _upiCards[uk] = FeedItem('upi_result', Map<String, dynamic>.from(p));
          feed.add(_upiCards[uk]!);
        }
        break;
      case 'hoola_rfq':                    // v0.112 one live compare card per comparison
        final rk = 'rfq${p['id']}';
        final rOld = _deals[rk];
        if (rOld != null) {
          rOld.data = Map<String, dynamic>.from(p);
        } else {
          _deals[rk] = FeedItem('hoola_rfq', Map<String, dynamic>.from(p));
          feed.add(_deals[rk]!);
        }
        hoolaTick++;
        break;
      case 'a2a_task':                     // v0.116 an outside A2A agent at her counter: one live card per request
      case 'a2a_out':                      // v0.116 her message to an outside agent: one live card per message
        final inner = Map<String, dynamic>.from((p[ev.kind == 'a2a_task' ? 'task' : 'out'] ?? const {}) as Map);
        final ak = '${ev.kind}${inner['id']}';
        final aOld = _deals[ak];
        if (aOld != null) {
          aOld.data = Map<String, dynamic>.from(p);
        } else {
          _deals[ak] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_deals[ak]!);
        }
        hoolaTick++;
        break;
      case 'handoff_reminder':             // v0.116 AA / ABDM consent still on: revoke?
      case 'digilocker':                   // v0.116 DigiLocker sign-in link / documents
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        break;
      case 'hoola_dosti':                  // v0.160 Dosti: live chat updates only refresh; cards need her
        if (p['card'] != 'live') feed.add(FeedItem('hoola_dosti', Map<String, dynamic>.from(p)));
        hoolaTick++;
        break;
      case 'hoola_mandate':                // v0.112 standing order notices
      case 'hoola_promo':                  // v0.112 an offer from a shop she opted in to
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        hoolaTick++;
        break;
      case 'hoola_khata':                  // v0.106 khata payment card / claim / receipt / due date
        feed.add(FeedItem('hoola_khata', Map<String, dynamic>.from(p)));
        hoolaTick++;
        break;
      case 'hoola_pick':                   // v0.105 a pick list on the packer's own Hoola
        final pkk = '${p['id']}';
        final pOld = _pickCards[pkk];
        if (pOld != null) {
          pOld.data = p['card'] == 'info' ? {...pOld.data, ...p} : Map<String, dynamic>.from(p);
        } else {
          _pickCards[pkk] = FeedItem('hoola_pick', Map<String, dynamic>.from(p));
          feed.add(_pickCards[pkk]!);
        }
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
      case 'email_new':
      case 'email_snooze':          // v0.182.0 "Mail aayi!": watcher cards, merged by kind+id
        final wn = '${ev.kind}:${p['id']}';
        final knownW = _emails[wn];
        if (knownW != null) {
          knownW.data = {...knownW.data, ...p};
        } else {
          _emails[wn] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_emails[wn]!);
        }
        break;
      case 'goal':                  // v0.187 lamba kaam pakka: ONE live card per goal id, every tick updates in place
        final gid = '${p['id']}';
        final had = _goals[gid];
        if (had != null) {
          had.data = Map<String, dynamic>.from(p);
        } else {
          _goals[gid] = FeedItem('goal', Map<String, dynamic>.from(p));
          feed.add(_goals[gid]!);
          if (inBackground && !_replaying && !pushOn && p['status'] == 'blocked') {
            Device.instance.showNow(aName, 'Lamba kaam aapke jawab par ruka hai: ${p['title'] ?? ''}');
          }
        }
        if (!_replaying && p['status'] == 'blocked') setMood(Mood.think, hold: const Duration(seconds: 8));
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
      case 'employee_ask':
        final eid = '${p['id']}';
        final had = _empAsks[eid];
        if (had != null) {
          had.data = {...had.data, ...p};
        } else if (p['status'] == 'pending') {
          _empAsks[eid] = FeedItem('employee_ask', Map<String, dynamic>.from(p));
          feed.add(_empAsks[eid]!);
          if (inBackground && !_replaying && !pushOn) Device.instance.showNow('Aapki haan chahiye', '${p['what'] ?? ''} · ${p['who'] ?? ''}');
        }
        employeeTick++;
        break;
      case 'studio':
        final sp = '${p['project']}';
        final sv = _studio[sp];
        if (sv != null) {
          sv.data = Map<String, dynamic>.from(p);
        } else {
          _studio[sp] = FeedItem('studio', Map<String, dynamic>.from(p));
          feed.add(_studio[sp]!);
        }
        studioTick++;
        break;
      case 'google_reconnect':
        feed.add(FeedItem('google_reconnect', Map<String, dynamic>.from(p)));
        if (inBackground && !_replaying && !pushOn) Device.instance.showNow('Google dobara jodiye', '${p['text'] ?? ''}');
        break;
      case 'studio_approval':
        final sa = '${p['id']}';
        final sq = _studioAsks[sa];
        if (sq != null) {
          sq.data = {...sq.data, ...p};
        } else if (p['status'] == 'pending') {
          _studioAsks[sa] = FeedItem('studio_approval', Map<String, dynamic>.from(p));
          feed.add(_studioAsks[sa]!);
          if (inBackground && !_replaying && !pushOn) Device.instance.showNow('Video ka kharcha ₹${p['inr'] ?? ''}', 'Haan dabaiye tabhi banega');
        }
        studioTick++;
        break;
      case 'operator_task':
        final oid = '${p['id']}';
        final ot = _opTasks[oid];
        if (ot != null) {
          ot.data = {...ot.data, ...p};
        } else {
          _opTasks[oid] = FeedItem('operator_task', Map<String, dynamic>.from(p));
          feed.add(_opTasks[oid]!);
        }
        operatorTick++;
        break;
      case 'operator_ask':
        final qid = '${p['id']}';
        final oq = _opAsks[qid];
        if (oq != null) {
          oq.data = {...oq.data, ...p};
          if (p['status'] != null && p['status'] != 'pending' && _otpSmsWait.remove(qid)) Native.otpConsentCancel();
        } else if (p['status'] == 'pending') {
          _opAsks[qid] = FeedItem('operator_ask', Map<String, dynamic>.from(p));
          feed.add(_opAsks[qid]!);
          if (inBackground && !_replaying && !pushOn) Device.instance.showNow('$aName: aapki zaroorat hai', '${p['reason'] ?? ''}');
          if (p['kind'] == 'otp' && !_replaying) _otpFromSms(qid, (p['digits'] as num?)?.toInt() ?? 0);
        }
        operatorTick++;
        break;
      case 'pg_write': // v0.147 Postgres change card (runs only on her tap)
        final pid = '${p['id']}';
        final pc = _pgCards[pid];
        if (pc != null) {
          pc.data = {...pc.data, ...p};
        } else if (p['again'] != true) {
          _pgCards[pid] = FeedItem('pg_write', Map<String, dynamic>.from(p));
          feed.add(_pgCards[pid]!);
          if (p['status'] == 'pending' && inBackground && !_replaying && !pushOn) {
            Device.instance.showNow('$aName: database badlav ke liye haan chahiye', '${p['say'] ?? ''}');
          }
        }
        break;
      case 'notebook_output': // v0.155 Notebook Studio (audio / video / slides / ...)
        final noid = '${p['id']}';
        final nc = _nbCards[noid];
        if (nc != null) {
          nc.data = {...nc.data, ...p};
        } else {
          _nbCards[noid] = FeedItem('notebook_output', Map<String, dynamic>.from(p));
          feed.add(_nbCards[noid]!);
        }
        if (p['push'] == true && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow(p['status'] == 'ready' ? '${p['label'] ?? 'Notebook'} taiyaar' : 'Notebook Studio', '${p['say'] ?? p['title'] ?? ''}');
        }
        notebookTick++;
        break;
      case 'blender3d': // v0.141 3D Studio
        final bid = '${p['id']}';
        final bc = _b3dCards[bid];
        if (bc != null) {
          bc.data = {...bc.data, ...p};
        } else {
          _b3dCards[bid] = FeedItem('blender3d', Map<String, dynamic>.from(p));
          feed.add(_b3dCards[bid]!);
        }
        if (p['status'] == 'done' && p['push'] == true && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName ne 3D banaya', '${p['say'] ?? p['title'] ?? ''}');
        }
        break;
      case 'video_job':
        final vid = '${p['id']}';
        final vj = _videoJobs[vid];
        if (vj != null) {
          vj.data = {...vj.data, ...p};
        } else {
          _videoJobs[vid] = FeedItem('video_job', Map<String, dynamic>.from(p));
          feed.add(_videoJobs[vid]!);
        }
        if (p['status'] == 'done' && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('Video taiyaar', '${p['title'] ?? 'Aapka video'} — dekhiye');
        }
        videoTick++;
        break;
      case 'darzi_quote':
      case 'darzi_ready':
        final dk = ev.kind == 'darzi_quote' ? 'q${p['id']}' : 'r${p['order_id']}';
        final dc = _darziCards[dk];
        if (dc != null) {
          dc.data = {...dc.data, ...p};
        } else {
          _darziCards[dk] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_darziCards[dk]!);
        }
        if (ev.kind == 'darzi_quote' && p['status'] == 'pending' && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: naya daam, aapki haan?', '${p['customer'] ?? ''} · ${p['label'] ?? ''}: ${p['price'] ?? ''}');
        }
        darziTick++;
        break;
      case 'chai_plan':
        final cpid = '${p['for_date']}';
        final cp = _chaiPlans[cpid];
        if (cp != null) {
          cp.data = {...cp.data, ...p};
        } else {
          _chaiPlans[cpid] = FeedItem('chai_plan', Map<String, dynamic>.from(p));
          feed.add(_chaiPlans[cpid]!);
        }
        chaiTick++;
        break;
      case 'chai_order':
        for (final it in _chaiPlans.values) {
          final orders = List<Map<String, dynamic>>.from(((it.data['orders'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
          final i = orders.indexWhere((o) => o['id'] == p['id']);
          if (i >= 0) {
            orders[i] = {...orders[i], ...p};
            it.data = {...it.data, 'orders': orders};
          }
        }
        chaiTick++;
        break;
      case 'galla':
        chaiTick++;
        break;
      case 'mshop_bill':
      case 'mshop_ready':
        final mk = '${ev.kind}${p['job_id']}';
        final mc = _mshopCards[mk];
        if (mc != null) {
          mc.data = {...mc.data, ...p};
        } else {
          _mshopCards[mk] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_mshopCards[mk]!);
        }
        mshopTick++;
        break;
      case 'mshop_day':
        feed.add(FeedItem('mshop_day', Map<String, dynamic>.from(p)));
        mshopTick++;
        break;
      case 'mshop':
        mshopTick++;
        break;
      case 'ads_change':
        final pid = '${p['plan_id'] ?? ''}';
        if (pid.isNotEmpty && p['decided'] == null) {
          final it = FeedItem('ads_change', Map<String, dynamic>.from(p));
          _adsPlans[pid] = it;
          feed.add(it);
        } else {
          for (final c in (p['changes'] as List? ?? const [])) {
            final cm = Map<String, dynamic>.from(c as Map);
            final card = _adsPlans['${cm['plan_id']}'];
            if (card != null) {
              final list = [for (final x in (card.data['changes'] as List? ?? const [])) Map<String, dynamic>.from(x as Map)];
              final i = list.indexWhere((x) => x['id'] == cm['id']);
              if (i >= 0) list[i] = cm;
              card.data = {...card.data, 'changes': list, 'say': p['say']};
            }
          }
        }
        if (p['decided'] == null && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: ads mein badlav ki haan?', '${p['say'] ?? ''}');
        }
        adsTick++;
        break;
      case 'seva_exception':
      case 'seva_ticket':
      case 'seva_sla':
      case 'seva_day':
      case 'helpdesk_ticket':
      case 'helpdesk_change':
      case 'helpdesk_escalate':
      case 'helpdesk_alert':
      case 'helpdesk_day':
      case 'shikayat_comp':
      case 'shikayat_case':
      case 'shikayat_message':
      case 'shikayat_day':
      case 'shikayat_alert':
      case 'aftersales_charge':
      case 'aftersales_reminders':
      case 'aftersales_visit':
      case 'aftersales_report':
      case 'aftersales_day':
      case 'feedback_reply':
      case 'feedback_alert':
      case 'feedback_report':
      case 'feedback_update':
      case 'feedback_survey':
      case 'wapsi_return':
      case 'wapsi_refund':
      case 'wapsi_day':
      case 'samudaay_alert':
      case 'samudaay_action':
      case 'samudaay_question':
      case 'samudaay_join':
      case 'samudaay_template':
      case 'samudaay_week':
      case 'samudaay_info':
      case 'callcentre_script':
      case 'callcentre_call':
      case 'callcentre_message':
        // v0.133 Seva suite: cards keyed by their id are updated in place (a later event keeps the earlier fields)
        final sk = sevaCardKey(ev.kind, Map<String, dynamic>.from(p));
        final sOld = sk.isEmpty ? null : _sevaCards[sk];
        if (sOld != null) {
          sOld.data = {...sOld.data, ...Map<String, dynamic>.from(p)};
        } else {
          final it = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          if (sk.isNotEmpty) _sevaCards[sk] = it;
          feed.add(it);
        }
        sevaTick++;
        break;
      case 'devsahayak_task':
      case 'devsahayak_push':
      case 'devsahayak_review':
      case 'devsahayak_merge':
      case 'devsahayak_deploy':
      case 'qa_run':
      case 'qa_bug':
      case 'qa_export':
      case 'qa_ready':
      case 'qa_cases':
      case 'itadmin_change':
      case 'itadmin_checklist':
      case 'itadmin_renewal':
      case 'itadmin_review':
      case 'itadmin_guide':
      case 'itadmin_day':
      case 'ispnoc_fault':
      case 'ispnoc_ticket':
      case 'ispnoc_change':
      case 'ispnoc_alert':
      case 'ispnoc_day':
      case 'cyber_action':
      case 'cyber_alerts':
      case 'cyber_check':
      case 'cyber_incident':
      case 'cyber_advisory':
      case 'cyber_posture':
      case 'cyber_day':
      case 'devops_build':
      case 'devops_deploy':
      case 'devops_alert':
      case 'devops_script':
      case 'devops_day':
      case 'docwriter_doc':
      case 'docwriter_publish':
      case 'docwriter_sync':
      case 'docwriter_shots':
      case 'appreview_report':
      case 'appreview_handoff':
      case 'appreview_alert':
      case 'product_publish':
      case 'product_backlog':
      case 'product_spec':
      case 'product_release':
      case 'product_day':
        // v0.137 Tech suite: cards keyed by their id are updated in place; a later step of another kind (e.g. a task that now
        // waits for her PR tap) takes the card's place with the new kind so it also shows inside a call
        final tp = Map<String, dynamic>.from(p);
        final tk = techCardKey(ev.kind, tp);
        final tOld = tk.isEmpty ? null : _techCards[tk];
        if (tOld != null && tOld.kind == ev.kind) {
          tOld.data = {...tOld.data, ...tp};
        } else if (tOld != null) {
          final it = FeedItem(ev.kind, {...tOld.data, ...tp});
          final at = feed.indexOf(tOld);
          if (at >= 0) {
            feed[at] = it;
          } else {
            feed.add(it);
          }
          _techCards[tk] = it;
        } else {
          final it = FeedItem(ev.kind, tp);
          if (tk.isNotEmpty) _techCards[tk] = it;
          feed.add(it);
        }
        techTick++;
        break;
      case 'customs_filing':
      case 'customs_shipment':
      case 'customs_alert':
      case 'customs_day':
      case 'travel_booking':
      case 'travel_quote':
      case 'travel_trip':
      case 'travel_reminder':
      case 'travel_day':
      case 'warehouse_adjust':
      case 'warehouse_grn':
      case 'warehouse_pick':
      case 'warehouse_count':
      case 'warehouse_day':
      case 'fleet_spend':
      case 'fleet_trip':
      case 'fleet_alert':
      case 'fleet_day':
      case 'courier_card':
      case 'courier_parcel':
      case 'courier_day':
      case 'drivers_plan':
      case 'drivers_message':
      case 'drivers_alert':
      case 'drivers_day':
      case 'logistics_ewb':
      case 'logistics_update':
      case 'logistics_shipment':
      case 'logistics_alert':
      case 'logistics_day':
        // v0.139 Safar suite: cards keyed by their id are updated in place (the newest data wins)
        final sp = Map<String, dynamic>.from(p);
        final sk = safarCardKey(ev.kind, sp);
        final sOld = sk.isEmpty ? null : _safarCards[sk];
        if (sOld != null) {
          sOld.data = {...sOld.data, ...sp};
        } else {
          final it = FeedItem(ev.kind, sp);
          if (sk.isNotEmpty) _safarCards[sk] = it;
          feed.add(it);
        }
        safarTick++;
        break;
      case 'vakil_card':
      case 'vakil_draft':
      case 'vakil_alert':
      case 'vakil_day':
      case 'legalres_memo':
      case 'legalres_share':
      case 'compliance_filing':
      case 'compliance_cert':
      case 'compliance_alert':
      case 'compliance_day':
      case 'contracts_card':
      case 'contracts_review':
      case 'contracts_alert':
      case 'contracts_day':
      case 'cosec_filing':
      case 'cosec_notice':
      case 'cosec_minutes':
      case 'cosec_alert':
      case 'cosec_day':
      case 'cosec_event':
      case 'notary_print':
      case 'notary_doc':
      case 'notary_entry':
      case 'notary_alert':
      case 'notary_day':
      case 'pidesk_share':
      case 'pidesk_report':
      case 'pidesk_doc':
      case 'pidesk_case':
      case 'pidesk_alert':
      case 'dpo_card':
      case 'dpo_request':
      case 'dpo_breach':
      case 'dpo_alert':
      case 'dpo_day':
        // v0.150 Kanoon suite: cards keyed by their id are updated in place; a later step of another kind for the same id
        // (notary doc -> print card, cosec notice -> minutes) takes the card's place with the new kind
        final kp = Map<String, dynamic>.from(p);
        final kk = kanoonCardKey(ev.kind, kp);
        final kOld = kk.isEmpty ? null : _kanoonCards[kk];
        if (kOld != null && kOld.kind == ev.kind) {
          kOld.data = {...kOld.data, ...kp};
        } else if (kOld != null) {
          final it = FeedItem(ev.kind, {...kOld.data, ...kp});
          final at = feed.indexOf(kOld);
          if (at >= 0) {
            feed[at] = it;
          } else {
            feed.add(it);
          }
          _kanoonCards[kk] = it;
        } else {
          final it = FeedItem(ev.kind, kp);
          if (kk.isNotEmpty) _kanoonCards[kk] = it;
          feed.add(it);
        }
        kanoonTick++;
        break;
      case 'frontoffice_card':
      case 'frontoffice_message':
      case 'frontoffice_booking':
      case 'frontoffice_alert':
      case 'frontoffice_day':
      case 'eventplan_booking':
      case 'eventplan_doc':
      case 'eventplan_message':
      case 'eventplan_spend':
      case 'eventplan_alert':
      case 'eventplan_day':
      case 'shaadi_card':
      case 'shaadi_alert':
      case 'shaadi_day':
      case 'tourguide_card':
      case 'tourguide_booking':
      case 'tourguide_plan':
      case 'tourguide_script':
      case 'tourguide_alert':
      case 'tourguide_day':
      case 'homestay_card':
      case 'homestay_booking':
      case 'homestay_alert':
      case 'homestay_day':
      case 'banquet_card':
      case 'banquet_alert':
      case 'banquet_day':
        // v0.152 Mehmaan suite: cards keyed by their id are updated in place
        final mp = Map<String, dynamic>.from(p);
        final mk = mehmaanCardKey(ev.kind, mp);
        final mOld = mk.isEmpty ? null : _mehmaanCards[mk];
        if (mOld != null) {
          mOld.data = {...mOld.data, ...mp};
        } else {
          final it = FeedItem(ev.kind, mp);
          if (mk.isNotEmpty) _mehmaanCards[mk] = it;
          feed.add(it);
        }
        mehmaanTick++;
        break;
      case 'editdesk_card':
      case 'editdesk_alert':
      case 'editdesk_day':
      case 'editdesk_note':
      case 'motiondesk_card':
      case 'motiondesk_alert':
      case 'motiondesk_day':
      case 'motiondesk_update':
      case 'filmdesk_card':
      case 'filmdesk_alert':
      case 'filmdesk_day':
      case 'patrakar_card':
      case 'patrakar_alert':
      case 'patrakar_day':
      case 'patrakar_story':
      case 'photoassist_card':
      case 'photoassist_alert':
      case 'photoassist_day':
      case 'graphic_card':
      case 'graphic_alert':
      case 'graphic_day':
      case 'graphic_job':
      case 'artistmgr_card':
      case 'artistmgr_alert':
      case 'artistmgr_day':
      case 'artistmgr_gig':
      case 'kitab_card':
      case 'kitab_alert':
      case 'kitab_day':
      case 'kitab_update':
      case 'podcast_card':
      case 'podcast_alert':
      case 'podcast_day':
      case 'influencer_card':
      case 'influencer_alert':
      case 'influencer_day':
        // v0.156 Kala suite: cards keyed by their id are updated in place
        final kp = Map<String, dynamic>.from(p);
        final kk = kalaCardKey(ev.kind, kp);
        final kOld = kk.isEmpty ? null : _kalaCards[kk];
        if (kOld != null) {
          kOld.data = {...kOld.data, ...kp};
        } else {
          final it = FeedItem(ev.kind, kp);
          if (kk.isNotEmpty) _kalaCards[kk] = it;
          feed.add(it);
        }
        kalaTick++;
        break;
      case 'propagent_listing':
        gharTick++;                              // v0.144 refresh only (no card)
        break;
      case 'propagent_card':
      case 'propagent_visit':
      case 'propagent_alert':
      case 'propagent_day':
      case 'rentdesk_approval':
      case 'rentdesk_message':
      case 'rentdesk_receipt':
      case 'rentdesk_alert':
      case 'rentdesk_day':
      case 'sitesup_indent':
      case 'sitesup_stop':
      case 'sitesup_report':
      case 'sitesup_alert':
      case 'sitesup_day':
      case 'interior_quote':
      case 'interior_order':
      case 'interior_change':
      case 'interior_payment':
      case 'interior_concept':
      case 'interior_alert':
      case 'interior_day':
      case 'archassist_transmittal':
      case 'archassist_submission':
      case 'archassist_invoice':
      case 'archassist_area':
      case 'archassist_alert':
      case 'archassist_day':
      case 'society_card':
      case 'society_complaint':
      case 'society_alert':
      case 'society_day':
        // v0.144 Makaan suite: cards keyed by their id are updated in place (the newest data wins)
        final gp = Map<String, dynamic>.from(p);
        final gk = gharCardKey(ev.kind, gp);
        final gOld = gk.isEmpty ? null : _gharCards[gk];
        if (gOld != null) {
          gOld.data = {...gOld.data, ...gp};
        } else {
          final it = FeedItem(ev.kind, gp);
          if (gk.isNotEmpty) _gharCards[gk] = it;
          feed.add(it);
        }
        gharTick++;
        break;
      case 'brand_design':
      case 'brand_approval':
        final bd = Map<String, dynamic>.from((p['design'] as Map?) ?? const {});
        final bid = '${bd['id'] ?? ''}';
        final bdata = {...Map<String, dynamic>.from(p), 'approval': ev.kind == 'brand_approval'};
        final bc = _brandCards[bid];
        if (bc != null) {
          bc.data = bdata;
        } else if (bid.isNotEmpty) {
          final it = FeedItem('brand_design', bdata);
          _brandCards[bid] = it;
          feed.add(it);
        }
        if (ev.kind == 'brand_approval' && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: poster final karein?', '${bd['number'] ?? ''} ${bd['title'] ?? ''}');
        }
        brandTick++;
        break;
      case 'site_board':
        final sid = '${p['id'] ?? ''}';
        final sdata = Map<String, dynamic>.from(p);
        final sc = _siteCards[sid];
        if (sc != null) {
          sc.data = sdata;
        } else if (sid.isNotEmpty) {
          final it = FeedItem('site_board', sdata);
          _siteCards[sid] = it;
          feed.add(it);
        }
        if (p['push'] == true && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: website ${p['number'] ?? ''}', '${p['say'] ?? ''}');
        }
        siteTick++;
        break;
      case 'app_board':
        final aid = '${p['id'] ?? ''}';
        final adata = Map<String, dynamic>.from(p);
        final ac = _appCards[aid];
        if (ac != null) {
          ac.data = adata;
        } else if (aid.isNotEmpty) {
          final it = FeedItem('app_board', adata);
          _appCards[aid] = it;
          feed.add(it);
        }
        if (p['push'] == true && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: app ${p['number'] ?? ''}', '${p['say'] ?? ''}');
        }
        appTick++;
        break;
      case 'app_android':
        final nid = '${p['id'] ?? ''}';
        final ndata = Map<String, dynamic>.from(p);
        final nc = _androidCards[nid];
        if (nc != null) {
          nc.data = ndata;
        } else if (nid.isNotEmpty) {
          final it = FeedItem('app_android', ndata);
          _androidCards[nid] = it;
          feed.add(it);
        }
        if (p['push'] == true && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: Android app ${p['number'] ?? ''}', '${p['say'] ?? ''}');
        }
        appTick++;
        break;
      case 'site_launch':
      case 'site_dns':
      case 'site_live':
      case 'site_down':
      case 'site_domain':
      case 'site_care':
      case 'site_github':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        if (p['push'] == true && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: website', '${p['say'] ?? ''}');
        }
        siteTick++;
        break;
      case 'site_lead':
        feed.add(FeedItem('site_lead', Map<String, dynamic>.from(p)));
        if (inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: website par enquiry', '${p['say'] ?? ''}');
        }
        siteTick++;
        break;
      case 'brand_idea':
        feed.add(FeedItem('brand_idea', Map<String, dynamic>.from(p)));
        brandTick++;
        break;
      case 'ads_report':
      case 'ads_copy':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        adsTick++;
        break;
      case 'kalam_piece':
      case 'kalam_publish':
        final kKey = '${ev.kind}${p['id']}';
        final kc = _kalamCards[kKey];
        if (kc != null) {
          kc.data = {...kc.data, ...p};
        } else {
          _kalamCards[kKey] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_kalamCards[kKey]!);
        }
        if (ev.kind == 'kalam_publish' && p['decided'] == null && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: publish karne ki haan?', '${p['number'] ?? ''} ${p['title'] ?? ''}');
        }
        kalamTick++;
        break;
      case 'tele_day':
      case 'tele_logged':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        teleTick++;
        break;
      case 'fin_report':
      case 'fin_alert':
      case 'audit_update':
      case 'ins_day':
      case 'ins_advice':
      case 'seo_update':
      case 'seo_week':
      case 'seo_alert':
      case 'seo_draft':
      case 'thok_order':
      case 'thok_alert':
      case 'thok_day':
      case 'niryat_pi':
      case 'niryat_day':
      case 'fr_statement':
      case 'fr_day':
      case 'theka_bill':
      case 'theka_letter':
      case 'theka_day':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        break;
      case 'payroll_run':
        final pk2 = '${p['run_id']}';
        final pc2 = _payCards[pk2];
        if (pc2 != null) {
          pc2.data = {...pc2.data, ...p};
        } else if (p['status'] == 'ready') {
          _payCards[pk2] = FeedItem('payroll_run', Map<String, dynamic>.from(p));
          feed.add(_payCards[pk2]!);
        }
        payTick++;
        break;
      case 'payroll_day':
        feed.add(FeedItem('payroll_day', Map<String, dynamic>.from(p)));
        payTick++;
        break;
      case 'gst_return':
        final gk = '${p['return_id']}';
        final gc = _gstCards[gk];
        if (gc != null) {
          gc.data = {...gc.data, ...p};
        } else if (p['status'] == 'ready') {
          _gstCards[gk] = FeedItem('gst_return', Map<String, dynamic>.from(p));
          feed.add(_gstCards[gk]!);
        }
        gstTick++;
        break;
      case 'gst_day':
        feed.add(FeedItem('gst_day', Map<String, dynamic>.from(p)));
        gstTick++;
        break;
      case 'phonedoc_case':
        final pk = '${p['case']}';
        final pc = _phonedocCards[pk];
        if (pc != null) {
          pc.data = {...pc.data, ...p};
        } else {
          _phonedocCards[pk] = FeedItem('phonedoc_case', Map<String, dynamic>.from(p));
          feed.add(_phonedocCards[pk]!);
        }
        phonedocTick++;
        break;
      case 'phonedoc_check':
        unawaited(sendPhoneCheck());
        break;
      case 'phonedoc_open':
        unawaited(openPhoneScreen('${p['key'] ?? ''}', package: '${p['package'] ?? ''}', url: '${p['url'] ?? ''}'));
        break;
      case 'darzi_day':
        feed.add(FeedItem('darzi_day', Map<String, dynamic>.from(p)));
        darziTick++;
        break;
      case 'darzi_order':
        darziTick++;
        break;
      case 'office_spend':
      case 'office_nudge':
        final officeKey = '${ev.kind}${p['id']}';
        final oc = _officeCards[officeKey];
        if (oc != null) {
          oc.data = {...oc.data, ...p};
        } else {
          _officeCards[officeKey] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_officeCards[officeKey]!);
        }
        if (ev.kind == 'office_spend' && p['status'] == 'pending' && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: kharcha, aapki haan?', '${p['number'] ?? ''} ${p['title'] ?? ''}: ${p['amount'] ?? ''}');
        }
        officeTick++;
        break;
      case 'office_day':
      case 'office_note':
        feed.add(FeedItem(ev.kind, Map<String, dynamic>.from(p)));
        officeTick++;
        break;
      case 'office':
        officeTick++;
        break;
      case 'lekhak_doc':
      case 'lekhak_sign':
        final lekhakKey = '${ev.kind}${p['id']}';
        final lc = _lekhakCards[lekhakKey];
        if (lc != null) {
          lc.data = {...lc.data, ...p};
        } else {
          _lekhakCards[lekhakKey] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_lekhakCards[lekhakKey]!);
        }
        if (ev.kind == 'lekhak_sign' && p['status'] == 'waiting_sign' && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName: letter sign karna hai?', '${p['number'] ?? ''} ${p['title'] ?? ''}');
        }
        lekhakTick++;
        break;
      case 'employee_report':
        feed.add(FeedItem('employee_report', Map<String, dynamic>.from(p)));
        employeeTick++;
        break;
      case 'procedure':
        if (p['event'] == 'learned' || p['event'] == 'lesson') feed.add(FeedItem('procedure', Map<String, dynamic>.from(p)));
        break;
      case 'call_receipt':
        feed.add(FeedItem('call_receipt', Map<String, dynamic>.from(p)));
        break;
      case 'sheet_milaan':
      case 'doc_edit':
        final dKey = '${p['id']}';
        final dc = _deskCards[dKey];
        if (dc != null) {
          dc.data = {...dc.data, ...p};
        } else {
          _deskCards[dKey] = FeedItem(ev.kind, Map<String, dynamic>.from(p));
          feed.add(_deskCards[dKey]!);
        }
        if (p['status'] == 'ready' && inBackground && !_replaying && !pushOn) {
          Device.instance.showNow(ev.kind == 'sheet_milaan' ? '$aName: Sheet Milaan taiyaar' : '$aName: file mein badlav taiyaar',
              '${p['name'] ?? ''}: ${p['say'] ?? ''}');
        }
        break;
      case 'memory_saved':
        feed.add(FeedItem('memory_saved', Map<String, dynamic>.from(p)));
        break;
      case 'ask_form':
        final fid = '${p['id']}';
        final fc = _askForms[fid];
        if (fc != null) {
          fc.data = {...fc.data, ...p};
        } else {
          _askForms[fid] = FeedItem('ask_form', Map<String, dynamic>.from(p));
          feed.add(_askForms[fid]!);
        }
        break;
      case 'employee':
      case 'biz_appointment':
        employeeTick++;
        break;
      case 'biz_inbox':
        employeeTick++;
        if (p['handover'] == true) {
          feed.add(FeedItem('biz_handover', Map<String, dynamic>.from(p)));
          if (inBackground && !_replaying && !pushOn) {
            Device.instance.showNow('WhatsApp: aapki zaroorat hai', '${(p['contact'] as Map?)?['name'] ?? ''}: ${p['reason'] ?? ''}');
          }
        }
        break;
      case 'bazar_open':
        feed.add(FeedItem('open', Map<String, dynamic>.from(p)));
        break;
      case 'bazar_link':
        feed.add(FeedItem('link', Map<String, dynamic>.from(p)));
        break;
      case 'gyaan_sources': // v0.134 sources under an answer from her Gyaan
        feed.add(FeedItem('gyaan_sources', Map<String, dynamic>.from(p)));
        break;
      case 'photo_made':
        feed.add(FeedItem('photo_made', Map<String, dynamic>.from(p)));
        if (inBackground && !_replaying && !pushOn) {
          Device.instance.showNow('$aName ne photo ${p['edit'] == true ? 'badli' : 'banayi'}', p['prompt'] as String? ?? '');
        }
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
          latestArtifact = {...Map<String, dynamic>.from(_artifacts[aid]!.data), '_call': ev.call ?? _artifacts[aid]!.call};
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
        // v0.158 only a live, fresh event can bring up the live view (never history, never an old job)
        if (!_replaying && DateTime.now().toUtc().difference(ev.at) < const Duration(minutes: 2)) {
          latestBrowser = {...Map<String, dynamic>.from(_browsers[bsid]!.data), '_call': ev.call ?? _browsers[bsid]!.call};
        }
        break;
      case 'device_action':
        // in the background the native service does it (screens can't be opened from the background)
        if (!(inBackground && (backgroundRunning || pushOn))) await _runAction(p, at: ev.at);
        break;
      case 'device_action_result':
        if (p['status'] == 'done') {
          final what = {'set_alarm': 'Alarm laga diya', 'set_timer': 'Timer shuru', 'add_calendar_event': 'Calendar khul gaya', 'open_url': 'Phone par khul gaya', 'youtube_play': 'YouTube par chal raha hai', 'tv_play': 'Channel chal raha hai'};
          feed.add(FeedItem('note', {'text': '${what[p['type']] ?? 'Ho gaya'} ✓'}));
        }
        break;
      case 'home_device':
        unawaited(_runHomeDevice(Map<String, dynamic>.from(p), at: ev.at));
        break;
      case 'bt_request':
        unawaited(_runBt(Map<String, dynamic>.from(p), at: ev.at));
        break;
      case 'voice_ring': // v0.219 VOICE RING: the server is calling her (never over a live call, gated on the server); the app starts the call itself
        if (!_replaying) wake(locked: false);
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

  // ---- live work line (v0.158 WorkStrip; the 3D Work Theatre is gone): the tool Hoola is running right now ----
  Map<String, dynamic>? work;                       // latest `work` event {id, tool, scene, phase, label, data}
  final List<Map<String, dynamic>> workLog = [];   // this task's tool calls, oldest first
  bool workMin = false;
  Timer? _workHide;

  /// v0.178 the streamed reply bubble goes away: `onlyTurn` = only that reply's final message arrived;
  /// with no argument any leftover bubble goes (a new reply is starting / the chat is reloading).
  void _streamDrop({String? onlyTurn}) {
    final it = _streamItem;
    if (it != null) {
      if (onlyTurn == null || onlyTurn.isEmpty || onlyTurn == '${it.data['turn']}') {
        feed.remove(it);
        _streamItem = null;
        notifyListeners();
      }
    }
    _sayDrop();                       // v0.187 the whisper goes when the reply goes
  }

  void _sayDrop() {
    final s = _sayItem;
    if (s == null) return;
    feed.remove(s);
    _sayItem = null;
    notifyListeners();
  }

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

  /// v0.181 what goes to the phone TTS is cleaned like the voice screen does: no links, no emoji, no bullets -
  /// the old voice read "https://..." and every emoji out loud.
  String _speakable(String text) => text
      .replaceAll(RegExp(r'https?://\S+'), 'link')
      .replaceAll(RegExp(r'[\u{1F000}-\u{1FAFF}\u{2190}-\u{2BFF}\u{FE0F}\u{200D}]', unicode: true), '')
      .replaceAll(RegExp(r'\s*[-\u2022\u00B7\u2013]\s+'), ', ')
      .replaceAll(RegExp(r'[*_#`>|]'), '')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  Future<void> _speak(String text) async {
    try {
      await _tts.setLanguage(language);
      await _tts.setSpeechRate(0.5);
      await _tts.speak(_speakable(text));
    } catch (_) {}
  }

  Future<void> stopSpeaking() async => _tts.stop();

  /// Let the UI rebuild after an in-place edit of a feed item.
  void notifyChange() => notifyListeners();

  @override
  void dispose() {
    _retryTimer?.cancel();
    _moodTimer?.cancel();
    _replies.close();
    _sub?.cancel();
    super.dispose();
  }
}


/// v0.133 Seva suite: which cards are one-per-id (updated in place). '' = always a new card.
String sevaCardKey(String kind, Map<String, dynamic> p) {
  String sub(String k) => p[k] is Map ? '${(p[k] as Map)['id'] ?? ''}' : '';
  final id = switch (kind) {
    'seva_exception' => '${p['id'] ?? ''}',
    'helpdesk_ticket' => '${p['ticket'] ?? ''}',
    'helpdesk_change' => sub('change'),
    'shikayat_comp' => sub('comp'),
    'aftersales_charge' || 'aftersales_visit' => '${p['visit_id'] ?? ''}',
    'wapsi_refund' => sub('refund'),
    'wapsi_return' => sub('return'),
    'callcentre_script' => '${p['script_id'] ?? ''}',
    'callcentre_message' || 'callcentre_call' => '${p['id'] ?? ''}',
    _ => '',
  };
  return id.isEmpty || id == 'null' ? '' : '$kind:$id';
}


/// v0.137 Tech suite: which cards are one-per-id (updated in place). '' = always a new card.
String techCardKey(String kind, Map<String, dynamic> p) {
  String sub(String k) => p[k] is Map ? '${(p[k] as Map)['id'] ?? ''}' : '';
  final (group, id) = switch (kind) {
    'devsahayak_task' || 'devsahayak_push' => ('devtask', sub('task')),
    'devsahayak_review' => ('devreview', sub('review')),
    'devsahayak_merge' || 'devsahayak_deploy' => ('devaction', sub('action')),
    'qa_run' => ('qarun', sub('run')),
    'qa_bug' => ('qabug', sub('bug')),
    'qa_export' => ('qaexport', sub('export')),
    'itadmin_change' => ('itachange', sub('change')),
    'itadmin_checklist' => ('itachecklist', sub('checklist')),
    'itadmin_guide' => ('itaguide', sub('guide')),
    'ispnoc_fault' => ('nocfault', sub('fault')),
    'ispnoc_ticket' => ('nocticket', sub('ticket')),
    'ispnoc_change' => ('nocchange', sub('change')),
    'cyber_action' => ('cyberaction', sub('action')),
    'devops_deploy' => ('devopsdeploy', sub('deploy')),
    'docwriter_doc' => ('docdoc', sub('doc')),
    'docwriter_publish' => ('docpub', sub('doc').isEmpty ? '' : '${sub('doc')}:${p['hash'] ?? ''}'),
    'appreview_report' => ('arreport', '${p['id'] ?? ''}'),
    'appreview_handoff' => ('arhandoff', '${p['id'] ?? ''}'),
    'product_publish' => ('prodpub', '${p['id'] ?? ''}'),
    'product_spec' => ('prodspec', sub('spec')),
    'product_release' => ('prodrel', sub('release')),
    _ => ('', ''),
  };
  return group.isEmpty || id.isEmpty || id == 'null' ? '' : '$group:$id';
}


/// v0.139 Safar suite: which cards are one-per-id (updated in place). '' = always a new card.
String safarCardKey(String kind, Map<String, dynamic> p) {
  String sub(String k) => p[k] is Map ? '${(p[k] as Map)['id'] ?? ''}' : '';
  final id = switch (kind) {
    'customs_filing' => sub('filing'),
    'customs_shipment' => sub('shipment'),
    'travel_booking' || 'travel_quote' => '${p['id'] ?? ''}',
    'travel_trip' => sub('trip'),
    'warehouse_adjust' => sub('adjust'),
    'warehouse_grn' => sub('grn'),
    'warehouse_pick' => sub('pick'),
    'warehouse_count' => sub('count'),
    'fleet_spend' => sub('spend'),
    'fleet_trip' => sub('trip'),
    'courier_card' => sub('card'),
    'courier_parcel' => sub('parcel'),
    'drivers_plan' => (p['day'] ?? '') == '' ? '' : '${p['day']}:${p['title'] ?? ''}',
    'drivers_message' => '${p['id'] ?? ''}',
    'logistics_ewb' => sub('ask'),
    'logistics_update' => sub('message'),
    'logistics_shipment' => sub('shipment'),
    'logistics_alert' => (p['id'] ?? '') == '' ? '' : '${p['id']}:${p['kind'] ?? ''}',
    _ => '',
  };
  return id.isEmpty || id == 'null' ? '' : '$kind:$id';
}


/// v0.144 Makaan suite: which cards are one-per-id (updated in place). '' = always a new card.
String gharCardKey(String kind, Map<String, dynamic> p) {
  String sub(String k) => p[k] is Map ? '${(p[k] as Map)['id'] ?? ''}' : '';
  final id = switch (kind) {
    'propagent_card' || 'society_card' => sub('card'),
    'propagent_visit' => sub('visit'),
    'rentdesk_approval' => sub('approval'),
    'rentdesk_message' => sub('message'),
    'rentdesk_receipt' => sub('payment'),
    'sitesup_indent' => sub('indent'),
    'sitesup_stop' => sub('stop'),
    'sitesup_report' => sub('report'),
    'interior_quote' => sub('quote'),
    'interior_order' => sub('order'),
    'interior_change' => sub('change'),
    'interior_payment' => sub('stage'),
    'archassist_transmittal' => sub('transmittal'),
    'archassist_submission' => sub('submission'),
    'archassist_invoice' => sub('invoice'),
    'society_complaint' => sub('complaint'),
    _ => '',
  };
  return id.isEmpty || id == 'null' ? '' : '$kind:$id';
}


/// v0.150 Kanoon suite: which cards are one-per-id (updated in place). '' = always a new card.
String kanoonCardKey(String kind, Map<String, dynamic> p) {
  String sub(String k) => p[k] is Map ? '${(p[k] as Map)['id'] ?? ''}' : '';
  final (group, id) = switch (kind) {
    'vakil_card' => ('vkcard', sub('card')),
    'vakil_draft' => ('vkdraft', sub('draft')),
    'legalres_memo' => ('lrmemo', sub('matter').isEmpty ? '' : '${sub('matter')}:${(p['memo'] as Map?)?['v'] ?? ''}'),
    'legalres_share' => ('lrshare', sub('share')),
    'compliance_filing' => ('cofiling', sub('filing')),
    'compliance_cert' => ('cocert', sub('cert')),
    'contracts_card' => ('ctcard', sub('card')),
    'contracts_review' => ('ctreview', sub('contract')),
    'cosec_filing' => ('csfiling', sub('filing')),
    'cosec_notice' || 'cosec_minutes' => ('csmeeting', sub('meeting')),
    'notary_doc' || 'notary_print' => ('nydoc', sub('doc')),
    'pidesk_share' => ('pishare', sub('share')),
    'pidesk_case' => ('picase', sub('case')),
    'dpo_card' => ('dpcard', sub('card')),
    'dpo_request' => ('dprequest', sub('request')),
    'dpo_breach' => ('dpbreach', sub('breach')),
    _ => ('', ''),
  };
  return group.isEmpty || id.isEmpty || id == 'null' ? '' : '$group:$id';
}


/// v0.152 Mehmaan suite: which cards are one-per-id (updated in place). '' = always a new card.
String mehmaanCardKey(String kind, Map<String, dynamic> p) {
  String sub(String k) => p[k] is Map ? '${(p[k] as Map)['id'] ?? ''}' : '';
  final id = switch (kind) {
    'frontoffice_card' || 'shaadi_card' || 'tourguide_card' || 'homestay_card' || 'banquet_card' => sub('card'),
    'frontoffice_message' || 'eventplan_message' => sub('message'),
    'frontoffice_booking' || 'eventplan_booking' || 'tourguide_booking' || 'homestay_booking' => sub('booking'),
    'eventplan_doc' => sub('doc'),
    'eventplan_spend' => sub('spend'),
    _ => '',
  };
  return id.isEmpty || id == 'null' ? '' : '$kind:$id';
}


/// v0.156 Kala suite: which cards are one-per-id (updated in place). '' = always a new card.
String kalaCardKey(String kind, Map<String, dynamic> p) {
  if (!kind.endsWith('_card')) return '';
  final c = p['card'];
  final id = c is Map ? '${c['id'] ?? ''}' : '';
  return id.isEmpty || id == 'null' ? '' : '$kind:$id';
}
