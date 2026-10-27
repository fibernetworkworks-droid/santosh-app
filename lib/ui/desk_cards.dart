import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// v0.108 Sheet Milaan card: two sheets compared by MAC / serial / ID on her PC. Shows new rows, changed cells
/// (old -> new) and rows missing in the new file. Her Haan saves an UPDATED COPY into the PC's Santosh Inbox (formatting
/// kept) and opens it; the original file stays untouched.
class SheetMilaanCard extends StatefulWidget {
  const SheetMilaanCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<SheetMilaanCard> createState() => _SheetMilaanCardState();
}

class _SheetMilaanCardState extends State<SheetMilaanCard> {
  bool _busy = false;
  String? _err;
  late bool _add = (widget.v['options'] as Map?)?['add'] != false;
  late String _missing = '${(widget.v['options'] as Map?)?['missing'] ?? 'keep'}';
  bool _highlight = false;
  bool _all = false;

  List<Map<String, dynamic>> _l(String k) =>
      List<Map<String, dynamic>>.from(((widget.v[k] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  Future<void> _decide(bool yes) async {
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final r = await widget.app.api!.deskDecide('${widget.v['id']}', yes,
          options: {'add': _add, 'missing': _missing, 'highlight': _highlight});
      widget.v.addAll(r);
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _head(String t, Color c, int n, int more) => Padding(
        padding: const EdgeInsets.only(top: 10, bottom: 2),
        child: Text('$t · $n${more > 0 ? ' (+$more aur)' : ''}', style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 12.5)),
      );

  Widget _line(String a, [String b = '']) => Padding(
        padding: const EdgeInsets.only(top: 3),
        child: Text.rich(TextSpan(children: [
          TextSpan(text: a, style: const TextStyle(color: C.ink, fontWeight: FontWeight.w600, fontSize: 13)),
          if (b.isNotEmpty) TextSpan(text: '  $b', style: const TextStyle(color: C.chip, fontSize: 12.5)),
        ])),
      );

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final counts = Map<String, dynamic>.from((v['counts'] as Map?) ?? const {});
    final key = Map<String, dynamic>.from((v['key'] as Map?) ?? const {});
    final more = Map<String, dynamic>.from((v['more'] as Map?) ?? const {});
    final status = '${v['status'] ?? 'ready'}';
    final out = Map<String, dynamic>.from((v['out'] as Map?) ?? const {});
    final changed = _l('changed'), added = _l('added'), missing = _l('missing');
    final show = _all ? 40 : 5;
    final warnings = [...((v['warnings'] as List?) ?? const []), ...((v['notes'] as List?) ?? const [])].map((e) => '$e').toList();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Glass(flat: true,
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.compare_arrows_rounded, color: C.teal, size: 20),
            const SizedBox(width: 8),
            const Expanded(child: Text('Sheet Milaan', style: TextStyle(fontWeight: FontWeight.w800))),
            _StatusChip(status),
          ]),
          const SizedBox(height: 6),
          Text('${v['name']}  ←  ${v['other'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (key.isNotEmpty)
            Text('Milaan "${key['old']}" se · ${key['why'] ?? ''}', style: const TextStyle(color: C.faint, fontSize: 11.5)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 6, children: [
            _Count('Badle', counts['changed'], C.accent),
            _Count('Naye', counts['added'], C.ok),
            _Count('Naye mein nahi', counts['missing'], C.bad),
            _Count('Same', counts['same'], C.faint),
          ]),
          if (changed.isNotEmpty) _head('Badle hue', C.accent, (counts['changed'] as num?)?.toInt() ?? changed.length, _all ? (more['changed'] ?? 0) : 0),
          for (final c in changed.take(show))
            for (final cell in List<Map<String, dynamic>>.from(((c['cells'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map))))
              _line('${c['key']} · ${cell['col']}', '${cell['old']}  →  ${cell['new']}'),
          if (added.isNotEmpty) _head('Naye rows', C.ok, (counts['added'] as num?)?.toInt() ?? added.length, _all ? (more['added'] ?? 0) : 0),
          for (final a in added.take(show))
            _line('${a['key']}', ((a['values'] as Map?) ?? const {}).values.take(4).join(' · ')),
          if (missing.isNotEmpty) _head('Nayi file mein nahi', C.bad, (counts['missing'] as num?)?.toInt() ?? missing.length, _all ? (more['missing'] ?? 0) : 0),
          for (final m in missing.take(show))
            _line('${m['key']}', ((m['values'] as Map?) ?? const {}).values.take(4).join(' · ')),
          if (!_all && (changed.length > 5 || added.length > 5 || missing.length > 5))
            TextButton(onPressed: () => setState(() => _all = true), child: const Text('Poori list dekhiye')),
          for (final w in warnings)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.info_outline_rounded, size: 15, color: C.warn),
                const SizedBox(width: 6),
                Expanded(child: Text(w, style: const TextStyle(color: C.warn, fontSize: 12))),
              ]),
            ),
          if (status == 'ready') ...[
            const SizedBox(height: 8),
            if (added.isNotEmpty)
              SwitchListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Naye rows bhi jodo', style: TextStyle(fontSize: 13)),
                  value: _add,
                  onChanged: _busy ? null : (x) => setState(() => _add = x)),
            if (missing.isNotEmpty)
              Wrap(spacing: 6, children: [
                for (final o in const [['keep', 'Rehne do'], ['mark', 'Note likho'], ['delete', 'Hata do']])
                  ChoiceChip(
                      label: Text(o[1]),
                      selected: _missing == o[0],
                      onSelected: _busy ? null : (_) => setState(() => _missing = o[0])),
              ]),
            SwitchListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: const Text('Badle cells peele karo', style: TextStyle(fontSize: 13)),
                value: _highlight,
                onChanged: _busy ? null : (x) => setState(() => _highlight = x)),
            const Text('Asli file waisi hi rahegi; nayi copy PC ke Santosh Inbox mein banegi aur khulegi.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
            const SizedBox(height: 8),
            _Buttons(busy: _busy, onYes: () => _decide(true), onNo: () => _decide(false), yes: 'Haan, update karo'),
          ],
          if (status == 'saved') _Saved(out: out, app: widget.app),
          if (status == 'failed') Text('${out['error'] ?? 'Nahi ho paya'}', style: const TextStyle(color: C.bad, fontSize: 12.5)),
          if (_err != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_err!, style: const TextStyle(color: C.bad, fontSize: 12))),
        ]),
      ),
    );
  }
}

/// v0.108 A document change waiting for her Haan (Word / Excel / PDF / text): every change before -> after.
class DocEditCard extends StatefulWidget {
  const DocEditCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<DocEditCard> createState() => _DocEditCardState();
}

class _DocEditCardState extends State<DocEditCard> {
  bool _busy = false;
  String? _err;
  bool _all = false;

  Future<void> _decide(bool yes) async {
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      widget.v.addAll(await widget.app.api!.deskDecide('${widget.v['id']}', yes));
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = '${v['status'] ?? 'ready'}';
    final out = Map<String, dynamic>.from((v['out'] as Map?) ?? const {});
    final changes = List<Map<String, dynamic>>.from(((v['changes'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final missing = ((v['missing'] as List?) ?? const []).map((e) => '$e').toList();
    final warnings = ((v['warnings'] as List?) ?? const []).map((e) => '$e').toList();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Glass(flat: true,
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.edit_note_rounded, color: C.teal, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('${v['name']} mein badlav', style: const TextStyle(fontWeight: FontWeight.w800))),
            _StatusChip(status),
          ]),
          const SizedBox(height: 6),
          Text('${changes.length} jagah', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          for (final c in changes.take(_all ? 60 : 4))
            Container(
              margin: const EdgeInsets.only(top: 6),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${c['where'] ?? ''}', style: const TextStyle(color: C.faint, fontSize: 11)),
                Text('${c['before']}', style: const TextStyle(color: C.bad, fontSize: 12.5, decoration: TextDecoration.lineThrough)),
                Text('${c['after']}', style: const TextStyle(color: C.ok, fontSize: 12.5)),
              ]),
            ),
          if (!_all && changes.length > 4)
            TextButton(onPressed: () => setState(() => _all = true), child: Text('Saare ${changes.length} dekhiye')),
          if (missing.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text('Yeh nahi mile: ${missing.join('; ')}', style: const TextStyle(color: C.warn, fontSize: 12)),
            ),
          for (final w in warnings)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.info_outline_rounded, size: 15, color: C.warn),
                const SizedBox(width: 6),
                Expanded(child: Text(w, style: const TextStyle(color: C.warn, fontSize: 12))),
              ]),
            ),
          if (status == 'ready') ...[
            const SizedBox(height: 8),
            const Text('Asli file waisi hi rahegi; nayi copy PC ke Santosh Inbox mein banegi aur khulegi.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
            const SizedBox(height: 8),
            _Buttons(busy: _busy, onYes: () => _decide(true), onNo: () => _decide(false), yes: 'Haan, save karo'),
          ],
          if (status == 'saved') _Saved(out: out, app: widget.app),
          if (status == 'failed') Text('${out['error'] ?? 'Nahi ho paya'}', style: const TextStyle(color: C.bad, fontSize: 12.5)),
          if (_err != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_err!, style: const TextStyle(color: C.bad, fontSize: 12))),
        ]),
      ),
    );
  }
}

/// v0.108 "Yaad rakha" chip: a lasting fact Hoola picked up by itself. ✕ forgets it at once.
class MemorySavedChip extends StatefulWidget {
  const MemorySavedChip({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<MemorySavedChip> createState() => _MemorySavedChipState();
}

class _MemorySavedChipState extends State<MemorySavedChip> {
  final Set<int> _gone = {};

  @override
  Widget build(BuildContext context) {
    final facts = List<Map<String, dynamic>>.from(((widget.v['facts'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final left = facts.where((f) => !_gone.contains((f['id'] as num?)?.toInt() ?? -1)).toList();
    if (left.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Wrap(spacing: 6, runSpacing: 6, children: [
        for (final f in left)
          InputChip(
            avatar: const Icon(Icons.bookmark_added_rounded, size: 16, color: C.teal),
            label: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 260),
              child: Text('Yaad rakha: ${f['text']}', overflow: TextOverflow.ellipsis, maxLines: 2, style: const TextStyle(fontSize: 12)),
            ),
            deleteIcon: const Icon(Icons.close_rounded, size: 16),
            deleteButtonTooltipMessage: 'Bhool jao',
            onDeleted: () async {
              final id = (f['id'] as num?)?.toInt();
              if (id == null) return;
              try {
                await widget.app.api!.forget(id);
                setState(() => _gone.add(id));
              } catch (_) {}
            },
          ),
      ]),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip(this.status);
  final String status;
  @override
  Widget build(BuildContext context) {
    final (t, c) = switch (status) {
      'saved' => ('Save ho gaya', C.ok),
      'rejected' => ('Mana kiya', C.faint),
      'failed' => ('Nahi hua', C.bad),
      _ => ('Aapki haan', C.accent),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withOpacity(.15), borderRadius: BorderRadius.circular(20)),
      child: Text(t, style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w700)),
    );
  }
}

class _Count extends StatelessWidget {
  const _Count(this.label, this.n, this.color);
  final String label;
  final Object? n;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
        child: Column(children: [
          Text('${n ?? 0}', style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 16)),
          Text(label, style: const TextStyle(color: C.faint, fontSize: 10.5)),
        ]),
      );
}

class _Buttons extends StatelessWidget {
  const _Buttons({required this.busy, required this.onYes, required this.onNo, required this.yes});
  final bool busy;
  final VoidCallback onYes, onNo;
  final String yes;
  @override
  Widget build(BuildContext context) => Row(children: [
        Expanded(
          child: FilledButton(
            onPressed: busy ? null : onYes,
            style: FilledButton.styleFrom(backgroundColor: C.accent, foregroundColor: C.onAccent),
            child: busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : Text(yes),
          ),
        ),
        const SizedBox(width: 8),
        OutlinedButton(onPressed: busy ? null : onNo, child: const Text('Mana')),
      ]);
}

class _Saved extends StatelessWidget {
  const _Saved({required this.out, required this.app});
  final Map<String, dynamic> out;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final onPc = out['where'] == 'pc';
    final url = '${out['url'] ?? ''}';
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if ('${out['summary'] ?? ''}'.isNotEmpty) Text('${out['summary']}', style: const TextStyle(color: C.ink, fontSize: 13)),
        const SizedBox(height: 4),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(onPc ? Icons.desktop_windows_rounded : Icons.phone_android_rounded, size: 16, color: C.ok),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
                onPc
                    ? '${out['saved_path']}${out['opened'] == true ? ' · PC par khul gayi' : ''}'
                    : 'PC offline tha: nayi copy yahan phone par hai',
                style: const TextStyle(color: C.chip, fontSize: 12.5)),
          ),
        ]),
        if (url.isNotEmpty)
          TextButton.icon(
            onPressed: () => Native.openExternal(url: app.api?.absolute(url) ?? url),
            icon: const Icon(Icons.download_rounded, size: 18),
            label: const Text('Phone par lo'),
          ),
      ]),
    );
  }
}
