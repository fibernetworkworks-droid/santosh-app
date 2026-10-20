import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/services.dart';

import 'barge_gate.dart';

/// One live voice call with Santosh: mic audio streams up, his voice streams back (Gemini Live on the server).
///
/// The call survives a dropped network (Wi-Fi to mobile data, a lift, a tunnel): the server keeps it alive for a
/// short while and this class re-joins it on a new connection by itself, so the person just hears a short gap.
class LiveVoice {
  LiveVoice({required this.onEvent, required this.onClosed});

  /// Server events: ready, user_text, santosh_text, interrupted, turn_done, tool, error, status.
  /// This class adds `status` events too: phone_reconnecting (network gone, re-joining), live (back), audio_paused.
  final void Function(Map<String, dynamic> e) onEvent;
  final void Function(String? reason) onClosed;

  static const _ch = MethodChannel('santosh/native');
  static const _mic = EventChannel('santosh/mic');
  static const _vad = EventChannel('santosh/vad');   // v0.51 Silero VAD speech probability per mic chunk
  StreamSubscription? _vadSub;
  double? _speech;
  DateTime _speechAt = DateTime.fromMillisecondsSinceEpoch(0);
  static const _call = MethodChannel('santosh/call');

  /// How long a dropped connection is retried before the call is given up.
  static const _resumeWindow = Duration(seconds: 24);

  /// The call in progress (the lock-screen notification's "Call band karein" button ends it).
  static LiveVoice? _current;

  WebSocket? _ws;
  StreamSubscription? _micSub;
  final BargeGate _gate = BargeGate(); // room noise must not cut Hoola off mid-sentence
  final IdleGate _idle = IdleGate();    // v0.53 pure noise reaches Gemini as silence while nobody talks
  bool _idleOn = true;
  bool _vadSeen = false;
  Timer? _statsTimer;
  Timer? _beat;
  bool muted = false;
  bool _closed = false;
  bool _userEnded = false;
  bool _reconnecting = false;
  bool _noResume = false; // the server said the call is gone
  bool _audioPaused = false; // another app (a real phone call...) has the audio for a moment
  String? _callId;
  DateTime _lastRx = DateTime.now();

  // what is needed to open the connection again
  String _server = '';
  String _key = '';
  String _conv = '';
  String _voice = '';
  String _lang = '';

  /// True while the connection is being re-established after a drop.
  bool get reconnecting => _reconnecting;

  /// Mic loudness 0..1 (smoothed).
  double inLevel = 0;

  // Santosh's audio timeline: when each chunk plays and how loud it is (for the 3D mouth)
  final List<(DateTime, DateTime, double)> _timeline = [];
  DateTime _playEnd = DateTime.fromMillisecondsSinceEpoch(0);

  bool get santoshSpeaking => DateTime.now().isBefore(_playEnd);

  /// Mouth level of the chunk playing right now.
  double get outLevel {
    final now = DateTime.now();
    _timeline.removeWhere((c) => c.$2.isBefore(now));
    for (final c in _timeline) {
      if (!now.isBefore(c.$1)) return c.$3;
    }
    return 0;
  }

  static Uri _url(String server, String conv, String voice, String lang, {String? resume}) {
    final base = Uri.parse(server.endsWith('/') ? server.substring(0, server.length - 1) : server);
    return base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: '${base.path}/api/voice/ws',
      queryParameters: {'conv': conv, 'voice': voice, 'lang': lang, if (resume != null) 'resume': resume},
    );
  }

  Future<WebSocket> _open({String? resume}) => WebSocket.connect(
        _url(_server, _conv, _voice, _lang, resume: resume).toString(),
        headers: {if (_key.isNotEmpty) 'Authorization': 'Bearer $_key'},
      ).timeout(const Duration(seconds: 10));

  /// Returns null when the call is up, or a reason it could not start.
  Future<String?> start({required String server, required String key, required String conv, required String voice, required String lang}) async {
    _server = server;
    _key = key;
    _conv = conv;
    _voice = voice;
    _lang = lang;
    // microphone first (asks permission the first time)
    String? err = await _ch.invokeMethod<String>('voiceStart');
    for (var i = 0; err == 'permission' && i < 20; i++) {
      await Future.delayed(const Duration(milliseconds: 700));
      err = await _ch.invokeMethod<String>('voiceStart');
    }
    if (err == 'permission') return 'Microphone ki permission chahiye.';
    if (err != null) return err;
    final WebSocket ws;
    try {
      ws = await _open();
    } catch (e) {
      await _ch.invokeMethod('voiceStop');
      return 'Server se voice connect nahi hua: $e';
    }
    _current = this;
    _call.setMethodCallHandler((c) async {
      if (c.method == 'hangup') await _current?.stop();
      if (c.method == 'audio') _current?._audioState(Map<String, dynamic>.from((c.arguments as Map?) ?? const {}));
      return null;
    });
    _attach(ws);
    _vadSub = _vad.receiveBroadcastStream().listen((p) {
      _speech = (p as num).toDouble();
      _speechAt = DateTime.now();
    }, onError: (Object _) {});
    _micSub = _mic.receiveBroadcastStream().listen((b) {
      final bytes = b as Uint8List;
      inLevel = inLevel * .7 + _rms(bytes) * .3;
      final sock = _ws;
      if (!muted && !_closed && !_reconnecting && !_audioPaused && sock != null && sock.readyState == WebSocket.open) {
        // while he talks (and for a moment after), only clear speech over the room's noise gets through
        final speaking = DateTime.now().isBefore(_playEnd.add(const Duration(milliseconds: 300)));
        try {
          final fresh = DateTime.now().difference(_speechAt).inMilliseconds < 200;
          final p = fresh ? _speech : null;
          if (p != null) _vadSeen = true;
          for (final out in _gate.process(bytes, hoolaSpeaking: speaking, speech: p)) {
            if (speaking || !_idleOn) {
              _idle.reset();
              sock.add(out);
            } else {
              for (final o in _idle.process(out, p)) {
                sock.add(o);
              }
            }
          }
        } catch (_) {}
      }
    }, onError: (Object e) {
      // the phone's microphone failed and could not be restarted
      onEvent({'type': 'error', 'message': 'Microphone mein dikkat aayi: $e'});
      stop();
    });
    _beat = Timer.periodic(const Duration(seconds: 8), (_) => _heartbeat());
    _statsTimer = Timer.periodic(const Duration(seconds: 20), (_) => _sendGateStats());
    return null;
  }

  /// v0.53 the gates' counters for /api/voice/stats (cumulative for the call).
  void _sendGateStats() {
    final sock = _ws;
    if (sock == null || sock.readyState != WebSocket.open) return;
    try {
      sock.add(jsonEncode({
        'type': 'gate_stats', 'chunks': _gate.chunks, 'held_back': _gate.heldBack, 'vad_blocked': _gate.vadBlocked,
        'idle_muted': _idle.mutedChunks, 'opens': _gate.opens, 'vad': _vadSeen ? 1 : 0,
      }));
    } catch (_) {}
  }

  void _attach(WebSocket ws) {
    _ws = ws;
    _lastRx = DateTime.now();
    ws.pingInterval = const Duration(seconds: 8);
    ws.listen(_onData, onDone: () => _lost(ws, ws.closeReason), onError: (e) => _lost(ws, '$e'), cancelOnError: true);
  }

  /// Every 8 s: tell the server we are alive, and notice a connection that died without telling anyone.
  void _heartbeat() {
    final ws = _ws;
    if (_closed || _reconnecting || ws == null) return;
    try {
      ws.add(jsonEncode({'type': 'ping'}));
    } catch (_) {}
    if (DateTime.now().difference(_lastRx) > const Duration(seconds: 24)) _lost(ws, 'network chala gaya');
  }

  void _onData(dynamic data) {
    _lastRx = DateTime.now();
    if (data is List<int>) {
      final bytes = data is Uint8List ? data : Uint8List.fromList(data);
      if (_audioPaused) return;
      _ch.invokeMethod('voicePlay', bytes);
      final now = DateTime.now();
      final start = _playEnd.isAfter(now) ? _playEnd : now.add(const Duration(milliseconds: 100)); // the phone keeps a small cushion before a reply starts
      final end = start.add(Duration(microseconds: (bytes.length / 48000 * 1e6).round())); // 24 kHz * 2 bytes
      _timeline.add((start, end, (_rms(bytes) * 2.2).clamp(0.0, 1.0)));
      _playEnd = end;
    } else if (data is String) {
      try {
        final e = Map<String, dynamic>.from(jsonDecode(data) as Map);
        if (e['type'] == 'pong') return;
        if (e['type'] == 'ready' && e['call_id'] is String) _callId = e['call_id'] as String;
        if (e['type'] == 'ready' && e['vad'] is Map) {
          final v = Map<String, dynamic>.from(e['vad'] as Map);
          final need = (v['need'] as num?)?.toDouble();
          if (need != null && need > 0.05 && need < 0.95) {
            _gate.speechNeed = need;
            _idle.need = need;
          }
          _idleOn = v['idle_gate'] != false;
        }
        if (e['type'] == 'error' && e['code'] == 'gone') _noResume = true;
        if (e['type'] == 'interrupted') cutSpeech();
        onEvent(e);
      } catch (_) {}
    }
  }

  /// The connection to the server ended. If it was not on purpose, re-join the same call.
  void _lost(WebSocket ws, String? reason) {
    if (_closed || !identical(ws, _ws)) return;
    _ws = null;
    unawaited(() async {
      try {
        await ws.close();
      } catch (_) {}
    }());
    if (_userEnded || _noResume || _callId == null) {
      _finish(reason);
      return;
    }
    unawaited(_reconnect(reason));
  }

  Future<void> _reconnect(String? reason) async {
    if (_reconnecting || _closed) return;
    _reconnecting = true;
    cutSpeech();
    onEvent({'type': 'status', 'state': 'phone_reconnecting'});
    final until = DateTime.now().add(_resumeWindow);
    var wait = const Duration(milliseconds: 300);
    while (!_closed && !_noResume && DateTime.now().isBefore(until)) {
      try {
        final ws = await _open(resume: _callId);
        if (_closed) {
          unawaited(ws.close());
          break;
        }
        _attach(ws);
        _reconnecting = false;
        onEvent({'type': 'status', 'state': 'live'});
        return;
      } catch (_) {
        await Future.delayed(wait);
        wait = Duration(milliseconds: math.min(wait.inMilliseconds * 2, 3000));
      }
    }
    _reconnecting = false;
    if (!_closed) _finish(reason == null || reason.isEmpty ? 'network wapas nahi aaya' : reason);
  }

  /// Another app took the audio for a moment (a real phone call...) or the microphone / speaker failed for good.
  void _audioState(Map<String, dynamic> m) {
    switch (m['state']) {
      case 'paused':
        _audioPaused = true;
        inLevel = 0;
        cutSpeech();
        onEvent({'type': 'status', 'state': 'audio_paused'});
      case 'resumed':
        _audioPaused = false;
        onEvent({'type': 'status', 'state': 'live'});
      case 'audio_error':
        onEvent({'type': 'error', 'message': 'Microphone ya speaker band ho gaya, isliye call band ho gayi.'});
        stop();
    }
  }

  /// Stop Santosh's current sentence immediately.
  void cutSpeech() {
    _ch.invokeMethod('voiceFlush');
    _timeline.clear();
    _playEnd = DateTime.now();
  }

  /// Files the owner attached during the call (already uploaded): Hoola is told their file_ids.
  bool sendFiles(List<String> ids, {String text = ''}) {
    final ws = _ws;
    if (ws == null || ids.isEmpty) return false;
    try {
      ws.add(jsonEncode({'type': 'files', 'file_ids': ids, if (text.isNotEmpty) 'text': text}));
      return true;
    } catch (_) {
      return false;
    }
  }

  void setMuted(bool m) {
    muted = m;
    try {
      _ws?.add(jsonEncode({'type': m ? 'mute' : 'unmute'}));
    } catch (_) {}
  }

  static double _rms(Uint8List b) {
    if (b.length < 2) return 0;
    final d = ByteData.sublistView(b);
    var sum = 0.0;
    final n = b.length ~/ 2;
    for (var i = 0; i < n; i += 2) {
      final s = d.getInt16(i * 2, Endian.little) / 32768.0;
      sum += s * s;
    }
    return (math.sqrt(sum / (n / 2)) * 4).clamp(0.0, 1.0);
  }

  void _finish(String? reason) {
    if (_closed) return;
    _closed = true;
    if (identical(_current, this)) _current = null;
    _beat?.cancel();
    _sendGateStats();
    _statsTimer?.cancel();
    _micSub?.cancel();
    _vadSub?.cancel();
    _ch.invokeMethod('voiceStop');
    onClosed(reason);
  }

  Future<void> stop() async {
    if (_closed) return;
    _userEnded = true;
    _sendGateStats();          // last counters before the call ends
    final ws = _ws;
    final wasAway = _reconnecting;
    _ws = null;
    try {
      ws?.add(jsonEncode({'type': 'end'}));
      await ws?.close();
    } catch (_) {}
    _finish(null);
    // hanging up while the network was away: still tell the server, so the call does not linger
    if (ws == null && wasAway && _callId != null) unawaited(_hangUpQuietly());
  }

  Future<void> _hangUpQuietly() async {
    try {
      final ws = await _open(resume: _callId).timeout(const Duration(seconds: 6));
      ws.add(jsonEncode({'type': 'end'}));
      await ws.close();
    } catch (_) {}
  }
}
