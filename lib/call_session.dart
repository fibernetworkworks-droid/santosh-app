import 'dart:async';

import 'package:flutter/foundation.dart';

import 'emotion.dart';
import 'live_voice.dart';
import 'native.dart';
import 'state.dart';
import 'ui/lock_safe.dart';

enum CallAct { idle, connecting, listening, userTalking, working, speaking }

/// Feed items that are cards the owner may need to act on or open during a call (approvals, downloads, drafts...).
const callCardKinds = {
  'bazar', 'email', 'pc_file', 'artifact', 'open', 'link', 'browser', 'calendar_event', 'sheet', 'form', 'slides',
  'notebook', 'youtube', 'app_check', 'photos_pick', 'campaign',
  'hoola_knock', 'hoola_connect', 'hoola_msg', 'hoola_group', 'hoola_group_post', 'hoola_outbox', 'hoola_chain',
  'hoola_ticket', 'hoola_lesson', 'hoola_samaj', 'employee_ask', 'biz_handover', 'operator_ask', 'operator_task', 'studio', 'studio_approval', 'google_reconnect',
  'office_spend', 'office_nudge', 'lekhak_doc', 'lekhak_sign',
  // v0.86 every card that waits for her answer shows inside the call too
  'darzi_quote', 'darzi_ready', 'chai_plan', 'video_job', 'motion',
  'ask_form', // v0.97
  'tele_logged', 'tele_day', // v0.99
  'kalam_publish', 'kalam_piece', // v0.101
  'ads_change', 'ads_report', // v0.111
  'hoola_deal', // v0.102
  'hoola_pick', // v0.105
  'hoola_khata', // v0.106
  'sheet_milaan', 'doc_edit', 'memory_saved', // v0.108
  'upi_result', // v0.109
  'hoola_rfq', 'hoola_mandate', 'hoola_promo', // v0.112
};

/// The live voice call, owned by the app (not by a screen): it keeps going while the owner opens Chat, Connect,
/// Main or any other screen, and only ends when they hang up (or the network is gone for good).
class CallSession extends ChangeNotifier {
  CallSession(this.app) {
    app.addListener(_onApp);
  }

  final Santosh app;
  LiveVoice? _call;
  Timer? _tick;
  CallAct act = CallAct.idle;
  bool inCall = false;
  bool muted = false;
  String heard = '';
  String reply = '';
  String? tool;
  String? note;
  String? lockIssue;  // why the call may stop when the phone locks
  String? linkNote;   // the connection is wobbling
  String? speaker;    // Awaaz Pehchaan: who Hoola recognised from the voice ("Asha (Maa)")
  bool speakerIsOwner = true;
  DateTime? startedAt;
  DateTime _lastHeard = DateTime.fromMillisecondsSinceEpoch(0);
  bool _turnOpen = false;
  int _lastSec = -1;
  Set<FeedItem> _before = {};
  final Set<FeedItem> dismissed = {};
  bool screenOpen = false;  // the Baat screen is showing the call

  double get inLevel => _call?.inLevel ?? 0;
  double get outLevel => _call?.outLevel ?? 0;

  /// Cards that arrived during this call and were not closed: shown right in the call.
  List<FeedItem> get cards => inCall || startedAt != null
      ? app.feed.where((f) => callCardKinds.contains(f.kind) && !_before.contains(f) && !dismissed.contains(f)).toList()
      : const [];

  void dismiss(FeedItem f) {
    dismissed.add(f);
    notifyListeners();
  }

  /// "Hey Santosh" was heard: pick up straight away, whatever screen is open.
  void _onApp() {
    if (!app.autoCall || !app.realtimeVoice) return;
    app.autoCall = false;
    if (!inCall) unawaited(start());
  }

  Duration get elapsed => startedAt == null ? Duration.zero : DateTime.now().difference(startedAt!);

  Future<void> start() async {
    if (inCall) return;
    if (app.conversationId == null || !app.connected) {
      note = 'Pehle server se connect hone dijiye.';
      notifyListeners();
      return;
    }
    inCall = true;
    act = CallAct.connecting;
    note = null;
    linkNote = null;
    heard = reply = '';
    tool = null;
    _before = app.feed.toSet();
    dismissed.clear();
    startedAt = DateTime.now();
    app.voiceMode = true;
    app.pushLocation();
    notifyListeners();
    await Native.wakePause();
    final call = LiveVoice(onEvent: _onEvent, onClosed: _onClosed);
    _call = call;
    final err = await call.start(
        server: app.serverUrl, key: app.apiKey, conv: app.conversationId!, voice: app.voiceName, lang: app.language);
    if (err != null) {
      _call = null;
      inCall = false;
      act = CallAct.idle;
      note = err;
      startedAt = null;
      app.voiceMode = false;
      Native.wakeResume();
      notifyListeners();
      return;
    }
    _tick = Timer.periodic(const Duration(milliseconds: 50), (_) => _update());
    Future.delayed(const Duration(seconds: 2), () async {
      if (!inCall) return;
      final st = await LockSafe.status();
      if (inCall) {
        lockIssue = LockSafe.issue(st, inCall: true);
        notifyListeners();
      }
    });
  }

  Future<void> end() async {
    _tick?.cancel();
    await _call?.stop();
    _closedState(null);
  }

  void toggleMute() {
    if (!inCall) return;
    muted = !muted;
    _call?.setMuted(muted);
    notifyListeners();
  }

  void cutSpeech() => _call?.cutSpeech();

  /// v0.44.2 a photo / PDF / any file during the call: uploaded, then handed to the live call.
  String? fileNote;
  bool uploading = false;
  Timer? _fileNoteTimer;

  void _setFileNote(String? t, {int seconds = 8}) {
    fileNote = t;
    _fileNoteTimer?.cancel();
    if (t != null) {
      _fileNoteTimer = Timer(Duration(seconds: seconds), () {
        fileNote = null;
        notifyListeners();
      });
    }
    notifyListeners();
  }

  Future<void> attachFiles(List<({String name, List<int> bytes})> files) async {
    if (!inCall || files.isEmpty) return;
    uploading = true;
    _setFileNote('${files.map((f) => f.name).join(', ')} bhej raha hoon…', seconds: 600);
    final ids = <String>[];
    final failed = <String>[];
    for (final f in files) {
      try {
        final r = await app.attachChatFile(f.name, f.bytes);
        ids.add('${r['file_id']}');
      } catch (e) {
        failed.add('${f.name}: $e');
      }
    }
    uploading = false;
    if (ids.isNotEmpty && !(_call?.sendFiles(ids) ?? false)) {
      failed.add('Call ka connection nahi mila, file chat mein bhej di');
      await app.send(files.map((f) => '📎 ${f.name}').join('\n'), files: ids);
    }
    _setFileNote(failed.isEmpty ? '📎 File ${app.aName} tak pahunch gayi' : failed.join('\n'), seconds: failed.isEmpty ? 6 : 12);
  }

  void _onClosed(String? reason) {
    _tick?.cancel();
    if (inCall && reason != null && reason.isNotEmpty) note = 'Call band ho gayi: $reason';
    _closedState(reason);
  }

  /// v0.98 the call to rate when it ends (from 'ready').
  String? _ratedCallId;

  void _closedState(String? reason) {
    _call = null;
    final was = inCall;
    final secs = startedAt == null ? 0 : DateTime.now().difference(startedAt!).inSeconds;
    final cid = _ratedCallId;
    _ratedCallId = null;
    if (was && cid != null && secs >= 20) {
      // v0.98 one tap after a call: was it good? (feeds the voice-quality numbers)
      app.addLocalCard('call_rate', {'call_id': cid, 'seconds': secs});
    }
    inCall = false;
    act = CallAct.idle;
    tool = null;
    linkNote = null;
    speaker = null;
    muted = false;
    startedAt = null;
    app.voiceMode = false;
    if (was) {
      Native.wakeResume();
      app.leaveLockedMode();
    }
    notifyListeners();
  }

  void _onEvent(Map<String, dynamic> e) {
    switch (e['type']) {
      case 'ready':
        if (e['call_id'] is String) _ratedCallId ??= e['call_id'] as String;
        act = CallAct.listening;
        linkNote = null;
        speaker = null;
        speakerIsOwner = true;
      case 'files':
        _setFileNote(e['ok'] == true ? '📎 ${e['names'] ?? 'File'} ${app.aName} ko mil gayi' : '${e['message'] ?? 'File nahi pahunchi'}');
      case 'speaker':
        final owner = e['owner'] == true;
        speakerIsOwner = owner;
        speaker = owner ? '${e['name']}' : '${e['name']} (${e['relation']})';
      case 'status':
        linkNote = switch (e['state']) {
          'phone_reconnecting' => 'Network chala gaya, dobara jod raha hoon…',
          'reconnecting' => 'Connection thoda slow hai, sambhal raha hoon…',
          'audio_paused' => 'Dusri awaaz (phone call?) chal rahi hai, call ruki hui hai',
          _ => null,
        };
      case 'user_text':
        if (!_turnOpen) reply = '';
        _turnOpen = true;
        _lastHeard = DateTime.now();
        heard = e['text'] as String? ?? '';
      case 'santosh_text':
        reply = e['text'] as String? ?? '';
      case 'turn_done':
        _turnOpen = false;
        if (heard.isNotEmpty) app.feelUser(heard);
        final r = reply;
        if (r.isNotEmpty) Future.delayed(const Duration(milliseconds: 600), () => app.feelReply(r));
      case 'tool':
        tool = e['state'] == 'running' ? e['label'] as String? : null;
      case 'error':
        note = e['message'] as String?;
    }
    notifyListeners();
  }

  /// Every 50 ms: who is talking (drives the avatar and the rings).
  void _update() {
    final call = _call;
    if (call == null) return;
    final sec = elapsed.inSeconds;
    if (sec != _lastSec) {     // the call timer on the other screens
      _lastSec = sec;
      notifyListeners();
    }
    CallAct next;
    if (act == CallAct.connecting) {
      next = CallAct.connecting;
    } else if (call.santoshSpeaking) {
      next = CallAct.speaking;
    } else if (!muted && (call.inLevel > .14 || DateTime.now().difference(_lastHeard) < const Duration(milliseconds: 900))) {
      next = CallAct.userTalking;
    } else if (tool != null) {
      next = CallAct.working;
    } else {
      next = CallAct.listening;
    }
    if (next != act) {
      if (next == CallAct.userTalking) app.setMood(app.userStressed ? Mood.care : Mood.listening, hold: Duration.zero);
      act = next;
      notifyListeners();
    } else if (screenOpen && (next == CallAct.speaking || next == CallAct.userTalking)) {
      notifyListeners(); // keep the avatar in time with the voice (only while the call screen is visible)
    }
  }
}
