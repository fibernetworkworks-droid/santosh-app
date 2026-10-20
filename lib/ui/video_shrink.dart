import 'dart:async';
import 'dart:io' show File;

import 'package:flutter/material.dart';

import '../native.dart';
import 'glass.dart';

/// v0.56 A big phone video is made smaller on the phone (Android's own encoder) so it fits the 25 MB limit:
/// a progress dialog with "Rok do", and for a very long video the choice to send only its first part.
/// Returns the path of the smaller video, or null (cancelled / failed; the reason was shown).
Future<String?> shrinkVideo(BuildContext context, String path, String name, {int sizeBytes = 0}) async {
  var clipMs = 0;
  for (var attempt = 0; attempt < 2; attempt++) {
    if (!context.mounted) return null;
    final r = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _ShrinkDialog(path: path, name: name, sizeBytes: sizeBytes, clipMs: clipMs),
    );
    final err = r?['error'] as String?;
    final out = r?['path'] as String?;
    if (out != null && out.isNotEmpty) {
      try {
        if (await File(out).length() <= 25 * 1024 * 1024) return out;
      } catch (_) {}
      _snack(context, '$name: chhota karke bhi 25 MB se badi hai. Drive link se bhejiye.');
      return null;
    }
    if (err == 'cancelled' || r == null) return null;
    if (err != null && err.startsWith('too_long:') && clipMs == 0) {
      final maxMs = int.tryParse(err.substring(9)) ?? 0;
      final mins = (maxMs / 60000).floor();
      if (mins < 1 || !context.mounted) break;
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: const Text('Video bahut lambi hai'),
          content: Text('25 MB mein poori video saaf nahi aayegi. Pehle $mins minute bhej doon?\n'
              '(Poori video ke liye Google Drive link sabse achha hai.)'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text('Pehle $mins min bhejo')),
          ],
        ),
      );
      if (ok != true) return null;
      clipMs = mins * 60000;
      continue;
    }
    _snack(context, '$name: ${err ?? 'video chhota nahi ho paya'}');
    return null;
  }
  return null;
}

void _snack(BuildContext context, String t) {
  if (context.mounted) ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));
}

class _ShrinkDialog extends StatefulWidget {
  const _ShrinkDialog({required this.path, required this.name, required this.sizeBytes, required this.clipMs});
  final String path;
  final String name;
  final int sizeBytes;
  final int clipMs;
  @override
  State<_ShrinkDialog> createState() => _ShrinkDialogState();
}

class _ShrinkDialogState extends State<_ShrinkDialog> {
  int _pct = 0;
  Timer? _poll;
  bool _stopping = false;
  bool _closed = false;

  void _close(Map<String, dynamic> r) {
    if (_closed || !mounted) return;     // cancel and the finished job both answer: close only once
    _closed = true;
    Navigator.of(context).pop(r);
  }
  final _started = DateTime.now();

  @override
  void initState() {
    super.initState();
    Native.compressVideo(widget.path, mb: 24, clipMs: widget.clipMs).then((r) {
      _close(r);
    });
    _poll = Timer.periodic(const Duration(milliseconds: 500), (_) async {
      final p = await Native.compressProgress();
      if (mounted && p >= 0) setState(() => _pct = p);
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  String get _eta {
    if (_pct < 5) return '';
    final spent = DateTime.now().difference(_started).inSeconds;
    final left = (spent * (100 - _pct) / _pct).round();
    return left < 60 ? ' · ~$left sec baaki' : ' · ~${(left / 60).ceil()} min baaki';
  }

  @override
  Widget build(BuildContext context) {
    final mb = widget.sizeBytes > 0 ? ' (${(widget.sizeBytes / 1024 / 1024).toStringAsFixed(0)} MB)' : '';
    return PopScope(
      canPop: false,
      child: AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Video chhoti kar raha hoon'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${widget.name}$mb → 25 MB se kam${widget.clipMs > 0 ? ' (pehle ${widget.clipMs ~/ 60000} min)' : ''}',
              style: const TextStyle(fontSize: 13, color: C.muted)),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: _pct <= 0 ? null : _pct / 100, minHeight: 8),
          ),
          const SizedBox(height: 8),
          Text('$_pct%$_eta', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          const Text('Phone par hi hota hai — video kahin upload nahi hoti jab tak aap bhejein nahi.',
              style: TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
        actions: [
          TextButton(
            onPressed: _stopping
                ? null
                : () async {
                    setState(() => _stopping = true);
                    await Native.compressCancel();
                    _close(<String, dynamic>{'error': 'cancelled'});
                  },
            child: const Text('Rok do'),
          ),
        ],
      ),
    );
  }
}
