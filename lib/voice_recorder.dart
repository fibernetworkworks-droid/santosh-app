import 'dart:async';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/services.dart';

import 'native.dart';

/// Records the microphone the same way a Hoola call hears it (16 kHz mono, the phone's call audio path), so a voice
/// enrolled here matches the voice in calls. Used by Awaaz Pehchaan.
class VoiceRecorder {
  static const _ch = MethodChannel('santosh/native');
  static const _mic = EventChannel('santosh/mic');

  final BytesBuilder _pcm = BytesBuilder(copy: false);
  StreamSubscription? _sub;
  bool recording = false;

  /// Smoothed loudness 0..1 for a level meter.
  double level = 0;

  Duration get length => Duration(milliseconds: _pcm.length ~/ 32); // 16 kHz * 2 bytes = 32 bytes per ms

  /// Null when recording started, else a reason to show.
  Future<String?> start() async {
    if (recording) return null;
    await Native.wakePause();
    String? err = await _ch.invokeMethod<String>('voiceStart');
    for (var i = 0; err == 'permission' && i < 20; i++) {
      await Future.delayed(const Duration(milliseconds: 700));
      err = await _ch.invokeMethod<String>('voiceStart');
    }
    if (err != null) {
      await Native.wakeResume();
      return err == 'permission' ? 'Microphone ki permission chahiye.' : err;
    }
    _pcm.clear();
    recording = true;
    _sub = _mic.receiveBroadcastStream().listen((b) {
      final bytes = b as Uint8List;
      _pcm.add(bytes);
      level = level * .7 + _rms(bytes) * .3;
    }, onError: (Object _) => stop());
    return null;
  }

  /// Stops and returns the recording as a 16 kHz mono 16-bit WAV.
  Future<Uint8List> stop() async {
    if (recording) {
      recording = false;
      await _sub?.cancel();
      _sub = null;
      try {
        await _ch.invokeMethod('voiceStop');
      } catch (_) {}
      await Native.wakeResume();
    }
    return wav(_pcm.toBytes());
  }

  static Uint8List wav(Uint8List pcm, {int rate = 16000}) {
    final h = ByteData(44);
    void str(int at, String s) {
      for (var i = 0; i < s.length; i++) {
        h.setUint8(at + i, s.codeUnitAt(i));
      }
    }

    str(0, 'RIFF');
    h.setUint32(4, 36 + pcm.length, Endian.little);
    str(8, 'WAVE');
    str(12, 'fmt ');
    h.setUint32(16, 16, Endian.little);
    h.setUint16(20, 1, Endian.little); // PCM
    h.setUint16(22, 1, Endian.little); // mono
    h.setUint32(24, rate, Endian.little);
    h.setUint32(28, rate * 2, Endian.little);
    h.setUint16(32, 2, Endian.little);
    h.setUint16(34, 16, Endian.little);
    str(36, 'data');
    h.setUint32(40, pcm.length, Endian.little);
    return (BytesBuilder()
          ..add(h.buffer.asUint8List())
          ..add(pcm))
        .toBytes();
  }

  static double _rms(Uint8List b) {
    final n = b.length ~/ 2;
    if (n == 0) return 0;
    final d = ByteData.sublistView(b);
    var sum = 0.0;
    for (var i = 0; i < n; i += 2) {
      final s = d.getInt16(i * 2, Endian.little) / 32768.0;
      sum += s * s;
    }
    return (math.sqrt(sum / (n / 2)) * 5).clamp(0.0, 1.0);
  }
}
