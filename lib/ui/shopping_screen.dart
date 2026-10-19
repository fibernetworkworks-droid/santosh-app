import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';

/// Santosh Shopping: the user's orders, and tokens that connect Claude / ChatGPT to the Santosh Commerce MCP server.
class ShoppingScreen extends StatefulWidget {
  const ShoppingScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ShoppingScreen> createState() => _ShoppingScreenState();
}

const _statusHi = {
  'payment_pending': 'Payment baaki',
  'placed': 'Order ho gaya',
  'accepted': 'Seller ne accept kiya',
  'packed': 'Pack ho gaya',
  'shipped': 'Raste mein',
  'out_for_delivery': 'Delivery par nikla',
  'delivered': 'Deliver ho gaya',
  'cancelled': 'Cancel',
  'return_requested': 'Return maanga',
  'returned': 'Return ho gaya',
  'failed': 'Nahi hua',
};

class _ShoppingScreenState extends State<ShoppingScreen> {
  List<Map<String, dynamic>> _orders = [];
  List<Map<String, dynamic>> _tokens = [];
  String _mcpUrl = '';
  String? _err;
  bool _loading = true;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([app.api!.shopOrders(), app.api!.shopMcpTokens()]);
      if (!mounted) return;
      final t = r[1] as Map<String, dynamic>;
      setState(() {
        _orders = r[0] as List<Map<String, dynamic>>;
        _tokens = ((t['tokens'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _mcpUrl = t['mcp_url'] as String? ?? '';
        _err = null;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _err = e.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _newToken() async {
    final label = TextEditingController(text: 'Claude');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('AI assistant jodiye'),
        content: TextField(controller: label, decoration: const InputDecoration(labelText: 'Naam (jaise Claude, ChatGPT)')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Token banao')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.shopMcpTokenCreate(label.text.trim().isEmpty ? 'My AI assistant' : label.text.trim());
      if (!mounted) return;
      final token = r['token'] as String? ?? '';
      final url = r['mcp_url'] as String? ?? _mcpUrl;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Token tayyar'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Yeh token sirf ek baar dikhega. Apne AI assistant mein MCP server jodiye:', style: TextStyle(fontSize: 13)),
              const SizedBox(height: 10),
              const Text('Address', style: TextStyle(fontSize: 12, color: C.muted)),
              SelectableText(url, style: const TextStyle(fontSize: 13)),
              const SizedBox(height: 8),
              const Text('Header: Authorization: Bearer <token>', style: TextStyle(fontSize: 12, color: C.muted)),
              SelectableText(token, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              Text(r['note'] as String? ?? '', style: const TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
          actions: [
            TextButton(
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: token));
                if (ctx.mounted) ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content: Text('Token copy ho gaya')));
              },
              child: const Text('Token copy'),
            ),
            FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Ho gaya')),
          ],
        ),
      );
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _revoke(Map<String, dynamic> t) async {
    try {
      await app.api!.shopMcpTokenRevoke(t['id'] as String);
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Widget _order(Map<String, dynamic> o) {
    final st = o['status'] as String? ?? '';
    final items = ((o['items'] as List?) ?? const []).map((e) => e.toString()).join(', ');
    final good = st == 'delivered' || st == 'placed' || st == 'accepted' || st == 'packed';
    final bad = st == 'failed' || st == 'cancelled';
    final color = bad ? C.bad : (good ? C.ok : C.warn);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        radius: 18,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(o['seller'] as String? ?? '', style: display(15.5))),
            Text(o['total'] as String? ?? '', style: display(15.5)),
          ]),
          const SizedBox(height: 4),
          Text(items, style: const TextStyle(color: C.muted, fontSize: 13)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            Pill((_statusHi[st] ?? st.replaceAll('_', ' ')).toUpperCase(), fg: color, bg: color.withOpacity(.14)),
            if (o['demo'] == true) const Pill('DEMO', fg: C.accentSoft, bg: Color(0x24FFB15C)),
            Pill('#${(o['order_id'] as String? ?? '').padRight(6).substring(0, 6)}'),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final active = _tokens.where((t) => t['revoked'] != true).toList();
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(title: const Text('Santosh Shopping')),
      body: Aurora(
        child: SafeArea(
          child: RefreshIndicator(
            color: C.accent,
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
              if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
              const Caption('MERE ORDERS'),
              if (_loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
              if (!_loading && _orders.isEmpty)
                const Padding(
                  padding: EdgeInsets.only(bottom: 12),
                  child: Text('Abhi koi order nahi. Chat mein boliye: "ONDC pe atta dhundo".', style: TextStyle(color: C.muted, fontSize: 13)),
                ),
              for (final o in _orders) _order(o),
              const SizedBox(height: 12),
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Text('Claude / ChatGPT se shopping', style: display(16)),
                  const SizedBox(height: 4),
                  const Text('Apne AI assistant ko Santosh Shopping (MCP server) se jodiye. Har order par pehle poori keemat dikhegi, '
                      'aapki haan ke bina order nahi hoga, aur paise sirf aapke UPI PIN se jayenge.',
                      style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.4)),
                  const SizedBox(height: 10),
                  for (final t in active)
                    ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.key_rounded, color: C.teal),
                      title: Text(t['label'] as String? ?? ''),
                      subtitle: Text('Banaya: ${t['created_at'] ?? ''}', style: const TextStyle(fontSize: 12, color: C.muted)),
                      trailing: TextButton(onPressed: () => _revoke(t), child: const Text('Hatao', style: TextStyle(color: C.bad))),
                    ),
                  const SizedBox(height: 6),
                  GlassButton(label: 'Naya token banao', icon: Icons.add_link_rounded, color: C.accentSoft, onTap: _newToken),
                ]),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
