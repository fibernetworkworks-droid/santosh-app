import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/services.dart';

/// One live voice call with Santosh: mic audio streams up, his voice streams back (Gemini Live on the server).
class LiveVoice {
  LiveVoice({required this.onEvent, required this.onClosed});

  /// Server events: ready, user_text, santosh_text, interrupted, turn_done, tool, error.
  final void Function(Map<String, dynamic> e) onEvent;
  final void Function(String? reason) onClosed;

  static const _ch = MethodChannel('santosh/native');
  static const _mic = EventChannel('santosh/mic');
  static const _call = MethodChannel('santosh/call');

  /// The call in progress (the lock-screen notification's "Call band karein" button ends it).
  static LiveVoice? _current;

  WebSocket? _ws;
  StreamSubscription? _micSub;
  bool muted = false;
  bool _closed = false;

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

  static Uri _url(String server, String conv, String voice, String lang) {
    final base = Uri.parse(server.endsWith('/') ? server.substring(0, server.length - 1) : server);
    return base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: '${base.path}/api/voice/ws',
      queryParameters: {'conv': conv, 'voice': voice, 'lang': lang},
    );
  }

  /// Returns null when the call is up, or a reason it could not start.
  Future<String?> start({required String server, required String key, required String conv, required String voice, required String lang}) async {
    // microphone first (asks permission the first time)
    String? err = await _ch.invokeMethod<String>('voiceStart');
    for (var i = 0; err == 'permission' && i < 20; i++) {
      await Future.delayed(const Duration(milliseconds: 700));
      err = await _ch.invokeMethod<String>('voiceStart');
    }
    if (err == 'permission') return 'Microphone ki permission chahiye.';
    if (err != null) return err;
    try {
      _ws = await WebSocket.connect(_url(server, conv, voice, lang).toString(),
          headers: {if (key.isNotEmpty) 'Authorization': 'Bearer $key'}).timeout(const Duration(seconds: 15));
    } catch (e) {
      await _ch.invokeMethod('voiceStop');
      return 'Server se voice connect nahi hua: $e';
    }
    _ws!.pingInterval = const Duration(seconds: 15);
    _current = this;
    _call.setMethodCallHandler((c) async {
      if (c.method == 'hangup') await _current?.stop();
      return null;
    });
    _ws!.listen(_onData, onDone: () => _finish(_ws?.closeReason), onError: (e) => _finish('$e'), cancelOnError: true);
    _micSub = _mic.receiveBroadcastStream().listen((b) {
      final bytes = b as Uint8List;
      inLevel = inLevel * .7 + _rms(bytes) * .3;
      if (!muted && !_closed) _ws?.add(bytes);
    });
    return null;
  }

  void _onData(dynamic data) {
    if (data is List<int>) {
      final bytes = data is Uint8List ? data : Uint8List.fromList(data);
      _ch.invokeMethod('voicePlay', bytes);
      final now = DateTime.now();
      final start = _playEnd.isAfter(now) ? _playEnd : now.add(const Duration(milliseconds: 60));
      final end = start.add(Duration(microseconds: (bytes.length / 48000 * 1e6).round())); // 24 kHz * 2 bytes
      _timeline.add((start, end, (_rms(bytes) * 2.2).clamp(0.0, 1.0)));
      _playEnd = end;
    } else if (data is String) {
      try {
        final e = Map<String, dynamic>.from(jsonDecode(data) as Map);
        if (e['type'] == 'interrupted') cutSpeech();
        onEvent(e);
      } catch (_) {}
    }
  }

  /// Stop Santosh's current sentence immediately.
  void cutSpeech() {
    _ch.invokeMethod('voiceFlush');
    _timeline.clear();
    _playEnd = DateTime.now();
  }

  void setMuted(bool m) {
    muted = m;
    _ws?.add(jsonEncode({'type': m ? 'mute' : 'unmute'}));
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
    _micSub?.cancel();
    _ch.invokeMethod('voiceStop');
    onClosed(reason);
  }

  Future<void> stop() async {
    if (_closed) return;
    try {
      _ws?.add(jsonEncode({'type': 'end'}));
      await _ws?.close();
    } catch (_) {}
    _finish(null);
  }
}
