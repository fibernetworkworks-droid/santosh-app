import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// v0.91 One MCP server's tools with her switches: on / off (an off tool is never offered to Hoola) and
/// "pehle poochho" (a confirm card first). Tools that send / delete / pay / share are locked to "pehle poochho".
Future<void> showMcpTools(BuildContext context, Santosh app, Map<String, dynamic> server) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: C.bgBottom,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (_) => FractionallySizedBox(heightFactor: 0.88, child: _McpTools(app: app, server: server)),
  );
}

class _McpTools extends StatefulWidget {
  const _McpTools({required this.app, required this.server});
  final Santosh app;
  final Map<String, dynamic> server;
  @override
  State<_McpTools> createState() => _McpToolsState();
}

class _McpToolsState extends State<_McpTools> {
  List<Map<String, dynamic>> _tools = [];
  String? _err;
  bool _loading = true;
  bool _caution = false;
  final Set<String> _busy = {};

  String get _pack => '${widget.server['pack_id']}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await widget.app.api!.mcpTools(_pack);
      _tools = List<Map<String, dynamic>>.from(((r['tools'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
      _caution = r['caution'] == true;
      _err = null;
    } catch (e) {
      _err = e.toString();
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _set(Map<String, dynamic> t, {bool? enabled, bool? ask}) async {
    final name = '${t['name']}';
    setState(() => _busy.add(name));
    try {
      final r = await widget.app.api!.mcpToolSet(_pack, name, enabled: enabled, ask: ask);
      t['enabled'] = r['enabled'];
      t['ask'] = r['ask'];
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _busy.remove(name));
  }

  @override
  Widget build(BuildContext context) {
    final on = _tools.where((t) => t['enabled'] != false).length;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text('${widget.server['name'] ?? 'MCP server'} · tools',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16), overflow: TextOverflow.ellipsis),
            ),
            IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh_rounded, color: C.muted)),
          ]),
          Text(
            _loading ? 'Server se tools la raha hoon…' : '$on / ${_tools.length} chalu. Band tool ${widget.app.aName} ko dikhta hi nahi. '
                '"Pehle poochho" = har baar confirm card.',
            style: const TextStyle(color: C.muted, fontSize: 12.5),
          ),
          if (_caution)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text('Paise / code wala server: har tool par aapka tap lagega.', style: TextStyle(color: C.warn, fontSize: 12)),
            ),
          const SizedBox(height: 10),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _err != null
                    ? Center(child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: C.bad)))
                    : _tools.isEmpty
                        ? const Center(child: Text('Is server ne koi tool nahi bataya.', style: TextStyle(color: C.muted)))
                        : ListView.separated(
                            itemCount: _tools.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 8),
                            itemBuilder: (_, i) => _row(_tools[i]),
                          ),
          ),
        ]),
      ),
    );
  }

  Widget _row(Map<String, dynamic> t) {
    final name = '${t['name']}';
    final busy = _busy.contains(name);
    final enabled = t['enabled'] != false;
    final ask = t['ask'] == true;
    final locked = t['locked'] == true;
    return Glass(
      radius: 16,
      padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: Text(name, style: TextStyle(fontWeight: FontWeight.w700, color: enabled ? C.ink : C.faint)),
          ),
          if (busy) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
          Switch(value: enabled, onChanged: busy ? null : (v) => _set(t, enabled: v)),
        ]),
        if ('${t['description'] ?? ''}'.isNotEmpty)
          Text('${t['description']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
        if (enabled)
          Row(children: [
            Icon(locked ? Icons.lock_rounded : Icons.front_hand_outlined, size: 15, color: ask ? C.warn : C.faint),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                locked ? 'Pehle poochho (bhejna / mitana / paise: hamesha)' : (ask ? 'Pehle poochho' : 'Khud chalayega (sirf padhta hai)'),
                style: TextStyle(color: ask ? C.warn : C.faint, fontSize: 12),
              ),
            ),
            Switch(value: ask, onChanged: (busy || locked) ? null : (v) => _set(t, ask: v)),
          ]),
      ]),
    );
  }
}
