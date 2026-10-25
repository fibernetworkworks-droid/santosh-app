import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'kb.dart';

/// v0.97 One card with several questions from Hoola (ask_form). Answers go back as her next message; ID numbers go into
/// her Pehchaan Locker first (Hoola only sees a masked reference). Works in chat and inside a call.
class AskFormCard extends StatefulWidget {
  const AskFormCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<AskFormCard> createState() => _AskFormCardState();
}

class _AskFormCardState extends State<AskFormCard> {
  final Map<String, TextEditingController> _text = {};
  final Map<String, String> _choice = {};
  final Map<String, Set<String>> _multi = {};
  final Set<String> _showId = {};
  bool _busy = false;
  String? _err;

  List<Map<String, dynamic>> get _fields =>
      List<Map<String, dynamic>>.from(((widget.v['fields'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  @override
  void initState() {
    super.initState();
    for (final f in _fields) {
      final name = '${f['name']}';
      final value = '${f['value'] ?? ''}';
      switch (f['kind']) {
        case 'choice':
          if (value.isNotEmpty) _choice[name] = value;
        case 'multi':
          _multi[name] = value.isEmpty ? <String>{} : value.split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toSet();
        default:
          _text[name] = TextEditingController(text: value);
      }
    }
  }

  @override
  void dispose() {
    for (final c in _text.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _send() async {
    final values = <String, dynamic>{};
    for (final f in _fields) {
      final name = '${f['name']}';
      values[name] = switch (f['kind']) {
        'choice' => _choice[name] ?? '',
        'multi' => (_multi[name] ?? <String>{}).toList(),
        _ => _text[name]?.text.trim() ?? '',
      };
    }
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final r = await widget.app.api!.formAnswer('${widget.v['id']}', values);
      widget.v.addAll(r);
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _close() async {
    setState(() => _busy = true);
    try {
      widget.v.addAll(await widget.app.api!.formCancel('${widget.v['id']}'));
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _pickDate(String name) async {
    final now = DateTime.now();
    final cur = DateTime.tryParse(_text[name]?.text ?? '') ?? now;
    final d = await showDatePicker(context: context, initialDate: cur, firstDate: DateTime(now.year - 100), lastDate: DateTime(now.year + 5));
    if (d != null) {
      _text[name]?.text = '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
      setState(() {});
    }
  }

  Widget _field(Map<String, dynamic> f, bool open) {
    final name = '${f['name']}';
    final label = '${f['label']}${f['required'] == false ? ' (zaroori nahi)' : ''}';
    final hint = '${f['hint'] ?? ''}';
    final kind = '${f['kind']}';
    final opts = List<String>.from(((f['options'] as List?) ?? const []).map((e) => '$e'));
    Widget body;
    if (kind == 'choice') {
      body = Wrap(spacing: 6, runSpacing: 6, children: [
        for (final o in opts)
          ChoiceChip(label: Text(o), selected: _choice[name] == o, onSelected: open ? (_) => setState(() => _choice[name] = o) : null),
      ]);
    } else if (kind == 'multi') {
      final sel = _multi[name] ??= <String>{};
      body = Wrap(spacing: 6, runSpacing: 6, children: [
        for (final o in opts)
          FilterChip(
              label: Text(o),
              selected: sel.contains(o),
              onSelected: open ? (v) => setState(() => v ? sel.add(o) : sel.remove(o)) : null),
      ]);
    } else {
      final isId = kind == 'id';
      // v0.179 KbField: the keyboard must never hide the box she is typing in (chat feed, call tray, waiting sheet)
      body = KbField(
        child: TextField(
          controller: _text[name],
          enabled: open,
          readOnly: kind == 'date',
          onTap: kind == 'date' && open ? () => _pickDate(name) : null,
          obscureText: isId && !_showId.contains(name),
          keyboardType: switch (kind) {
            'number' => const TextInputType.numberWithOptions(decimal: true),
            'phone' => TextInputType.phone,
            'email' => TextInputType.emailAddress,
            'date' => TextInputType.none,
            _ => TextInputType.text,
          },
          textInputAction: TextInputAction.next,
          decoration: InputDecoration(
            isDense: true,
            hintText: hint.isNotEmpty ? hint : (kind == 'date' ? 'Tareekh chuniye' : null),
            helperText: isId ? 'Pehchaan Locker mein jayega; Hoola ko sirf aakhri 4 ank dikhenge' : null,
            suffixIcon: isId
                ? IconButton(
                    icon: Icon(_showId.contains(name) ? Icons.visibility_off_rounded : Icons.visibility_rounded, size: 18),
                    onPressed: () => setState(() => _showId.contains(name) ? _showId.remove(name) : _showId.add(name)))
                : (kind == 'date' ? const Icon(Icons.event_rounded, size: 18) : null),
          ),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
        const SizedBox(height: 4),
        body,
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = '${v['status'] ?? 'pending'}';
    final open = status == 'pending' && !_busy;
    final answers = Map<String, dynamic>.from((v['answers'] as Map?) ?? const {});
    return Glass(flat: true,
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.assignment_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['title'] ?? 'Form'}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
          Pill(switch (status) { 'answered' => 'Bhar diya', 'cancelled' => 'Band', _ => 'Bhariye' },
              fg: status == 'answered' ? C.ok : status == 'cancelled' ? C.faint : C.accent),
        ]),
        if ('${v['why'] ?? ''}'.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text('${v['why']}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
        if (status == 'answered')
          ..._fields.map((f) => Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text('${f['label']}: ${answers[f['name']] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 13)),
              ))
        else if (status == 'pending')
          ..._fields.map((f) => _field(f, open)),
        if (_err != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_err!, style: const TextStyle(color: C.bad))),
        if (status == 'pending')
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Row(children: [
              Expanded(child: GlassButton(label: _busy ? 'Bhej raha hoon…' : 'Bhejiye', icon: Icons.send_rounded, onTap: open ? _send : null)),
              const SizedBox(width: 8),
              TextButton(onPressed: open ? _close : null, child: const Text('Rehne do')),
            ]),
          ),
      ]),
    );
  }
}
