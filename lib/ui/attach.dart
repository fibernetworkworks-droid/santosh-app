import 'dart:io' show File;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../i18n.dart';
import 'glass.dart';
import 'video_shrink.dart';

/// v0.44.2 One picker for every paperclip (chat, voice call, Hoola chats): photo / video, document / PDF / any file,
/// audio. Reads the bytes even when the picker only hands back a path (cloud / big files), checks the size.
class PickedFile {
  PickedFile(this.name, this.bytes);
  final String name;
  final List<int> bytes;
}

const maxAttachBytes = 25 * 1024 * 1024;

/// One file of a known kind (no sheet).
Future<List<PickedFile>> pickAttachmentsOfType(BuildContext context, FileType type) =>
    pickAttachments(context, max: 1, showSheet: false, type: type);

Future<List<PickedFile>> pickAttachments(BuildContext context, {int max = 6, bool showSheet = true, FileType type = FileType.any, String lang = 'en-IN'}) async {
  if (showSheet) {
    final pick = await showModalBottomSheet<FileType>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.photo_library_rounded, color: C.accent), title: const Text('Photo / Video'),
              onTap: () => Navigator.pop(ctx, FileType.media)),
          ListTile(leading: const Icon(Icons.description_rounded, color: C.accent), title: Text(tr(lang, 'PDF / Document / Excel / koi bhi file')),
              onTap: () => Navigator.pop(ctx, FileType.any)),
          ListTile(leading: const Icon(Icons.audiotrack_rounded, color: C.accent), title: const Text('Audio'),
              onTap: () => Navigator.pop(ctx, FileType.audio)),
        ]),
      ),
    );
    if (pick == null) return const [];
    type = pick;
  }
  FilePickerResult? res;
  try {
    // bytes are read from the picked path ourselves: a 200 MB video is never loaded into memory just to be refused
    res = await FilePicker.platform.pickFiles(type: type, allowMultiple: max > 1, withData: false);
  } catch (e) {
    if (context.mounted) _snack(context, '${tr(lang, 'File chun nahi paye:')} $e');
    return const [];
  }
  if (res == null) return const [];
  final out = <PickedFile>[];
  for (final f in res.files.take(max)) {
    var path = f.path;
    var name = f.name;
    final isVideo = RegExp(r'\.(mp4|mov|m4v|3gp|mkv|webm)$', caseSensitive: false).hasMatch(name);
    if (isVideo && f.size > maxAttachBytes && path != null) {
      // big phone video: made smaller on the phone (progress + Rok do; long video -> first part) instead of refused
      if (!context.mounted) break;
      final small = await shrinkVideo(context, path, name, sizeBytes: f.size);
      if (small == null) continue;
      out.add(PickedFile(name.replaceAll(RegExp(r'\.[A-Za-z0-9]+$'), '') + '.mp4', await File(small).readAsBytes()));
      continue;
    }
    if (f.size > maxAttachBytes) {
      if (context.mounted) _snack(context, '${f.name}: ${tr(lang, '{x} MB hai, 25 MB tak bhej sakte hain. Badi file Drive link se bhejiye.', x: '${(f.size / 1024 / 1024).toStringAsFixed(0)}')}');
      continue;
    }
    List<int>? bytes = f.bytes;
    if (bytes == null && path != null) {
      try {
        bytes = await File(path).readAsBytes();
      } catch (_) {}
    }
    if (bytes == null || bytes.isEmpty) {
      if (context.mounted) _snack(context, tr(lang, '{x} padh nahi paye. Phone mein download karke dobara chuniye.', x: f.name));
      continue;
    }
    out.add(PickedFile(f.name, bytes));
  }
  return out;
}

void _snack(BuildContext context, String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
