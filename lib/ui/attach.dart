import 'dart:io' show File;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../native.dart';
import 'glass.dart';

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

Future<List<PickedFile>> pickAttachments(BuildContext context, {int max = 6, bool showSheet = true, FileType type = FileType.any}) async {
  if (showSheet) {
    final pick = await showModalBottomSheet<FileType>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.photo_library_rounded, color: C.accent), title: const Text('Photo / Video'),
              onTap: () => Navigator.pop(ctx, FileType.media)),
          ListTile(leading: const Icon(Icons.description_rounded, color: C.accent), title: const Text('PDF / Document / Excel / koi bhi file'),
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
    if (context.mounted) _snack(context, 'File chun nahi paye: $e');
    return const [];
  }
  if (res == null) return const [];
  final out = <PickedFile>[];
  for (final f in res.files.take(max)) {
    var path = f.path;
    var name = f.name;
    final isVideo = RegExp(r'\.(mp4|mov|m4v|3gp|mkv|webm)$', caseSensitive: false).hasMatch(name);
    if (isVideo && f.size > maxAttachBytes && path != null) {
      // v0.49 big phone video: shrink it on the phone (720p / 480p) so it fits, instead of refusing it
      if (context.mounted) _snack(context, '$name badi hai (${(f.size / 1024 / 1024).toStringAsFixed(0)} MB) — chhota kar raha hoon…');
      final r = await Native.compressVideo(path, mb: 24);
      if (r['path'] is String && (r['path'] as String).isNotEmpty) {
        path = r['path'] as String;
        name = name.replaceAll(RegExp(r'\.[A-Za-z0-9]+$'), '') + '.mp4';
        final size = await File(path).length();
        if (size <= maxAttachBytes) {
          out.add(PickedFile(name, await File(path).readAsBytes()));
          continue;
        }
      }
      if (context.mounted) _snack(context, '$name: ${r['error'] ?? 'chhota karke bhi 25 MB se badi hai'}');
      continue;
    }
    if (f.size > maxAttachBytes) {
      if (context.mounted) _snack(context, '${f.name}: ${(f.size / 1024 / 1024).toStringAsFixed(0)} MB hai, 25 MB tak bhej sakte hain. Badi file Drive link se bhejiye.');
      continue;
    }
    List<int>? bytes = f.bytes;
    if (bytes == null && path != null) {
      try {
        bytes = await File(path).readAsBytes();
      } catch (_) {}
    }
    if (bytes == null || bytes.isEmpty) {
      if (context.mounted) _snack(context, '${f.name} padh nahi paye. Phone mein download karke dobara chuniye.');
      continue;
    }
    out.add(PickedFile(f.name, bytes));
  }
  return out;
}

void _snack(BuildContext context, String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
