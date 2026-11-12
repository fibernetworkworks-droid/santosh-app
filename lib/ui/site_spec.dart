/// v0.414 HOOLA ARCHITECT on the phone: her one line -> the spec card (stories, pages, users, data, rules, payments,
/// notifications, other apps, features). She switches a part off, asks for a change in her words, or says Haan -> the
/// website + its app brain are built. Same card as the console (event `site_spec`), updated in place.
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

String _t(dynamic v) => v == null ? '' : '$v';
List _l(dynamic v) => v is List ? v : const [];

class SiteSpecCard extends StatefulWidget {
  const SiteSpecCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<SiteSpecCard> createState() => _SiteSpecCardState();
}

class _SiteSpecCardState extends State<SiteSpecCard> {
  final Set<String> _off = {};
  bool _busy = false;
  Map<String, dynamic>? _fresh;

  Map<String, dynamic> get v => _fresh ?? widget.v;

  void _snack(String s) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));
  }

  Future<void> _change() async {
    final ctl = TextEditingController();
    final w = await showDialog<String>(
        context: context,
        builder: (c) => AlertDialog(
              title: const Text('What should change?'),
              content: TextField(
                  controller: ctl,
                  autofocus: true,
                  maxLines: 3,
                  decoration: const InputDecoration(hintText: 'For example: add an alumni page too, let teachers mark attendance')),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c), child: const Text('Keep it')),
                TextButton(onPressed: () => Navigator.pop(c, ctl.text.trim()), child: const Text('Change')),
              ],
            ));
    if (w == null || w.isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.architectAct(_t(v['id']), 'revise', {'words': w});
      if (r['modules'] is List) _fresh = r;
      _snack(_t(r['say']).isEmpty ? 'Changed.' : _t(r['say']));
    } catch (e) {
      _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _build() async {
    final keep = [for (final m in _l(v['modules'])) if (!_off.contains(_t(m['key']))) _t(m['key'])];
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: Text('Create ${_t(v['name'])}?'),
              content: Text('These parts will be made: ${keep.join(', ')}'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Not now')),
                TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, build it')),
              ],
            ));
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.architectAct(_t(v['id']), 'approve', {'hash': _t(v['hash']), 'modules': keep});
      _fresh = {...v, 'status': 'built', 'site': _t(r['number'])};
      _snack(_t(r['say']).isEmpty ? 'Building.' : _t(r['say']));
    } catch (e) {
      _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void didUpdateWidget(covariant SiteSpecCard old) {
    super.didUpdateWidget(old);
    if (old.v != widget.v) _fresh = null;     // a newer card from the server wins
  }

  @override
  Widget build(BuildContext context) {
    final built = _t(v['status']) == 'built';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.architecture_rounded, color: C.teal, size: 20),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_t(v['number'])} · ${_t(v['name']).isEmpty ? 'Website plan' : _t(v['name'])}',
                  style: display(15), maxLines: 1, overflow: TextOverflow.ellipsis)),
          Pill(built ? 'Building: ${_t(v['site'])}' : 'Needs your yes', fg: built ? C.teal : C.accent),
        ]),
        if (_t(v['summary']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(_t(v['summary']), style: const TextStyle(color: C.chip, fontSize: 13)),
        ],
        for (final m in _l(v['modules'])) ...[
          const SizedBox(height: 8),
          Row(children: [
            SizedBox(
                width: 28,
                height: 28,
                child: Checkbox(
                    value: !_off.contains(_t(m['key'])),
                    onChanged: (built || m['required'] == true)
                        ? null
                        : (on) => setState(() => on == true ? _off.remove(_t(m['key'])) : _off.add(_t(m['key']))))),
            const SizedBox(width: 6),
            Expanded(child: Text(_t(m['title']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14))),
            if (m['ready'] == false) const Pill('needs fixing', fg: Colors.redAccent),
          ]),
          for (final line in _l(m['lines']).take(8))
            Padding(
                padding: const EdgeInsets.only(left: 34, top: 2),
                child: Text('• $line', style: const TextStyle(fontSize: 12, color: C.muted), maxLines: 3, overflow: TextOverflow.ellipsis)),
        ],
        for (final q in _l(v['questions']))
          Padding(padding: const EdgeInsets.only(top: 6), child: Text('? $q', style: const TextStyle(fontSize: 12, color: C.accent))),
        if (!built) ...[
          const SizedBox(height: 10),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(onPressed: _busy ? null : _change, child: const Text('Change something')),
            const SizedBox(width: 6),
            GlassButton(label: _busy ? 'Wait...' : 'Yes, build it', height: 38, color: C.accent, onTap: _busy ? null : _build),
          ]),
        ],
      ]),
    );
  }
}
