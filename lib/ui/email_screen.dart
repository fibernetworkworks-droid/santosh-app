import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

/// Profile > Email: connect Gmail / Outlook (official sign-in) or any other email (app password),
/// set a signature and the default mailbox. Passwords and tokens are stored encrypted on the Santosh server.
class EmailScreen extends StatefulWidget {
  const EmailScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<EmailScreen> createState() => _EmailScreenState();
}

class _EmailScreenState extends State<EmailScreen> {
  List<Map<String, dynamic>> _accounts = [];
  Map<String, dynamic> _canLink = {};
  List<Map<String, dynamic>> _rules = [];
  List<Map<String, dynamic>> _watch = [];
  List<Map<String, dynamic>> _searches = [];
  bool _loaded = false;
  bool _busy = false;
  String? _err;
  int _seenTick = 0;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _seenTick = app.mailLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.mailLinkedTick != _seenTick) {
      _seenTick = app.mailLinkedTick;
      _load();
    }
  }

  void _apply(Map<String, dynamic> r) {
    _accounts = List<Map<String, dynamic>>.from((r['accounts'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    if (r['can_link'] != null) _canLink = Map<String, dynamic>.from(r['can_link'] as Map);
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.mailAccounts();
      Map<String, dynamic> rules = {};
      try {
        rules = await app.api!.mailRules();
      } catch (_) {}                     // purana server: watcher section chhup jaati hai
      if (!mounted) return;
      setState(() {
        _apply(r);
        _rules = List<Map<String, dynamic>>.from((rules['rules'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        _watch = List<Map<String, dynamic>>.from((rules['watch'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        _searches = List<Map<String, dynamic>>.from((rules['searches'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        _loaded = true;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _link(String provider) async {
    try {
      final url = await app.api!.mailLinkUrl(provider);
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _imap() async {
    final addr = TextEditingController();
    final pass = TextEditingController();
    final name = TextEditingController();
    final imapHost = TextEditingController();
    final smtpHost = TextEditingController();
    final smtpPort = TextEditingController();
    var advanced = false;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setD) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Koi bhi email jodiye'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(controller: addr, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email address')),
          TextField(controller: pass, obscureText: true, decoration: const InputDecoration(labelText: 'App password')),
          const SizedBox(height: 6),
          const Text('Apna login password nahi, "app password" daaliye. Gmail: myaccount.google.com/apppasswords · '
              'Yahoo / Zoho / Outlook: Security settings > App password.',
              style: TextStyle(color: C.muted, fontSize: 12)),
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Bhejne wale ka naam (optional)')),
          TextButton(onPressed: () => setD(() => advanced = !advanced),
              child: Text(advanced ? 'Server settings chhupaiye' : 'Server settings (company email ke liye)')),
          if (advanced) ...[
            TextField(controller: imapHost, decoration: const InputDecoration(labelText: 'IMAP host (jaise imap.company.in)')),
            TextField(controller: smtpHost, decoration: const InputDecoration(labelText: 'SMTP host (jaise smtp.company.in)')),
            TextField(controller: smtpPort, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'SMTP port (587 ya 465)')),
          ],
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodiye')),
        ],
      )),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.mailConnectImap({
        'address': addr.text.trim(), 'password': pass.text, 'name': name.text.trim(),
        'imap_host': imapHost.text.trim(), 'smtp_host': smtpHost.text.trim(),
        'smtp_port': int.tryParse(smtpPort.text.trim()) ?? 0,
      });
      setState(() => _apply(r));
      _snack('Email jud gaya ✓');
    } catch (e) {
      _snack(e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _signature(Map<String, dynamic> a) async {
    final c = TextEditingController(text: a['signature'] as String? ?? '');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('Signature · ${a['address']}'),
        content: TextField(controller: c, minLines: 3, maxLines: 6,
            decoration: const InputDecoration(hintText: 'Meghana Ingle\nDirector, Newtika Pvt Ltd\n+91 …')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.mailAccountEdit(a['key'] as String, signature: c.text);
      setState(() => _apply(r));
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _makeDefault(Map<String, dynamic> a) async {
    try {
      final r = await app.api!.mailAccountEdit(a['key'] as String, makeDefault: true);
      setState(() => _apply(r));
    } catch (e) {
      _snack(e.toString());
    }
  }

  String get _watchMode {
    if (_watch.isEmpty) return 'vip';
    final off = _watch.where((w) => w['mode'] == 'off').length;
    if (off == _watch.length && _watch.isNotEmpty) return 'off';
    final all = _watch.where((w) => w['mode'] == 'all').length;
    if (all == _watch.length) return 'all';
    return 'vip';
  }

  Future<void> _setWatch(String mode) async {
    try {
      final r = await app.api!.mailWatch(mode);
      if (!mounted) return;
      setState(() => _watch = List<Map<String, dynamic>>.from((r['watch'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map))));
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _addRule() async {
    final name = TextEditingController();
    final from = TextEditingController();
    final subject = TextEditingController();
    final label = TextEditingController();
    var archive = false, star = false, markRead = false;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setD) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Naya rule'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Rule ka naam')),
          TextField(controller: from, decoration: const InputDecoration(labelText: 'Kisase aaye to (jaise hdfcbank)')),
          TextField(controller: subject, decoration: const InputDecoration(labelText: 'Vishay mein shabd (jaise bill, invoice)')),
          const SizedBox(height: 10),
          const Text('Kya karein', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          CheckboxListTile(dense: true, value: archive, onChanged: (v) => setD(() => archive = v ?? false),
              title: const Text('Archive karo')), 
          CheckboxListTile(dense: true, value: star, onChanged: (v) => setD(() => star = v ?? false),
              title: const Text('Star laga do')),
          CheckboxListTile(dense: true, value: markRead, onChanged: (v) => setD(() => markRead = v ?? false),
              title: const Text('Padha hua mark karo')),
          TextField(controller: label, decoration: const InputDecoration(labelText: 'Label lagao (naam)')),
          const SizedBox(height: 6),
          const Text('Rule nayi mail par chalte hain; bhejna hamesha aapke Bhejo par.',
              style: TextStyle(color: C.muted, fontSize: 12)),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Banaiye')),
        ],
      )),
    );
    if (ok != true) return;
    final match = <String, dynamic>{
      if (from.text.trim().isNotEmpty) 'from': from.text.trim(),
      if (subject.text.trim().isNotEmpty) 'subject': subject.text.trim(),
    };
    final actions = <String, dynamic>{
      if (label.text.trim().isNotEmpty) 'label': label.text.trim(),
      if (archive) 'archive': true,
      if (star) 'star': true,
      if (markRead) 'mark_read': true,
    };
    try {
      await app.api!.mailRuleCreate(name.text.trim(), match, actions);
      _snack('Rule chalu hai. Ab se aane wali nayi mail par chalega.');
      _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _toggleRule(Map<String, dynamic> r) async {
    try {
      await app.api!.mailRuleEdit(r['id'] as String, r['enabled'] != true);
      _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _delRule(Map<String, dynamic> r) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('Rule "${r['name']}" hatayein?'),
        content: const Text('Rule hi hatega; mail par koi asar nahi.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hataiye')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await app.api!.mailRuleRemove(r['id'] as String);
      _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  String _ruleSummary(Map<String, dynamic> r) {
    final m = Map<String, dynamic>.from(r['match'] as Map? ?? const {});
    final a = Map<String, dynamic>.from(r['actions'] as Map? ?? const {});
    final parts = <String>[
      if (m['from'] != null) '${m['from']} se',
      if (m['subject'] != null) '"${m['subject']}" vishay',
      if (m['has_attachment'] == true) 'attachment wali',
      if (m['bulk'] == true) 'bulk',
    ];
    final acts = <String>[
      if (a['label'] != null) 'label ${a['label']}',
      if (a['archive'] == true) 'archive',
      if (a['star'] == true) 'star',
      if (a['mark_read'] == true) 'padha hua',
      if (a['mute'] == true) 'shant',
      if (a['notify'] == true) 'khabar',
      if (a['forward_to'] != null) '${a['forward_to']} ko draft',
    ];
    return '${parts.join(' + ')} → ${acts.join(', ')}';
  }

  String _searchSummary(Map<String, dynamic> r) {
    final m = Map<String, dynamic>.from(r['match'] as Map? ?? const {});
    return [
      if (m['query'] != null) '“${m['query']}”',
      if (m['from'] != null) '${m['from']} se',
      if (m['subject'] != null) '“${m['subject']}” vishay',
      if (m['has_attachment'] == true) 'attachment wali',
      if (m['bulk'] == true) 'bulk',
    ].join(' + ');
  }

  Future<void> _remove(Map<String, dynamic> a) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Email hataiye?'),
        content: Text('${a['address']} Hoola se hat jayega. Aapki mail par koi asar nahi.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hataiye')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.mailAccountRemove(a['key'] as String);
      setState(() => _apply(r));
    } catch (e) {
      _snack(e.toString());
    }
  }

  IconData _icon(String kind) => kind == 'gmail' ? Icons.mark_email_unread_rounded : kind == 'outlook' ? Icons.business_center_rounded : Icons.alternate_email_rounded;
  String _kind(String kind) => kind == 'gmail' ? 'Gmail' : kind == 'outlook' ? 'Outlook' : 'Email (app password)';

  Widget _account(Map<String, dynamic> a) {
    final bad = a['status'] == 'error';
    final sig = (a['signature'] as String? ?? '').trim();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_icon(a['kind'] as String? ?? ''), color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(a['address'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(_kind(a['kind'] as String? ?? '') + (a['default'] == true ? ' · default' : ''), style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ])),
          if (bad) const Pill('LOGIN FAIL', fg: C.bad) else const Pill('JUDA', fg: C.ok),
        ]),
        if (bad && (a['error'] as String? ?? '').isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 6), child: Text(a['error'] as String, style: const TextStyle(color: C.bad, fontSize: 12))),
        const SizedBox(height: 8),
        Text(sig.isEmpty ? 'Signature: nahi hai' : 'Signature:\n$sig', style: const TextStyle(color: C.chip, fontSize: 12.5)),
        Wrap(spacing: 4, children: [
          TextButton(onPressed: () => _signature(a), child: const Text('Signature')),
          if (a['default'] != true && a['removable'] == true) TextButton(onPressed: () => _makeDefault(a), child: const Text('Default banaiye')),
          if (a['removable'] == true) TextButton(onPressed: () => _remove(a), child: const Text('Hataiye', style: TextStyle(color: C.muted))),
        ]),
      ])),
    );
  }

  @override
  Widget build(BuildContext context) {
    final google = _canLink['google'] == true;
    final ms = _canLink['microsoft'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('Email'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Hoola aapki mail padhta, chhaant-ta, jawab likhta, attachment kholta, follow-up yaad dilata aur '
                'bulk mail bhejta hai. Bhejna, delete aur bulk mail hamesha aapke tap ke baad hi.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 10),
            // v0.184.0 "Gmail, poora" — the one help card that says what Hoola now covers end to end
            Glass(child: Theme(data: Theme.of(context).copyWith(dividerColor: Colors.transparent), child: ExpansionTile(
              tilePadding: const EdgeInsets.symmetric(horizontal: 12),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              iconColor: C.accent, collapsedIconColor: C.accent,
              title: Text(app.g('Gmail, poora'), style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(app.g('Gmail ke saare kaam, chat se — hifazat ke saath'), style: const TextStyle(color: C.muted, fontSize: 12.5)),
              children: [
                for (final t in [
                  app.g('Padhna, chhaantna: inbox, thread poora, attachments (PDF, Excel, photos bhi), Gmail ke apne snoozed folder samet.'),
                  app.g('Likhte waqt: rich mail, Drive file attach, schedule, undo window, alias se bhejna (verified aliases).'),
                  app.g('Khud sambhale: rules, saved searches, labels (rang aur nesting ke saath), snooze, follow-up yaad, bulk mail.'),
                  app.g('Gmail ki apni settings: vacation auto-reply, signature, send-as aliases, auto-forward — sab aapke tap par.'),
                  app.g('Nayi mail ki khabar har minute, zaroori ka pehle; OTP codes kabhi nahi batata.'),
                  app.g('Settings ke liye Gmail ek baar dobara jodna pade to is screen par “Jodiye” dabaiye — mail pehle jaisi chalti hai.'),
                ])
                  Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Padding(padding: EdgeInsets.only(top: 2), child: Icon(Icons.check_circle_outline_rounded, size: 15, color: C.accent)),
                    const SizedBox(width: 7),
                    Expanded(child: Text(t, style: const TextStyle(color: C.chip, fontSize: 12.5))),
                  ])),
              ]))),
            const SizedBox(height: 14),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded && _accounts.isEmpty)
              const Padding(padding: EdgeInsets.only(bottom: 12), child: Text('Abhi koi email juda nahi hai.', style: TextStyle(fontWeight: FontWeight.w700))),
            for (final a in _accounts) _account(a),
            const SizedBox(height: 6),
            GlassButton(label: 'Gmail jodiye', icon: Icons.mark_email_unread_rounded, height: 48,
                onTap: google && !_busy ? () => _link('google') : null),
            const SizedBox(height: 8),
            GlassButton(label: 'Outlook / Hotmail / Office 365 jodiye', icon: Icons.business_center_rounded, height: 48,
                onTap: ms && !_busy ? () => _link('microsoft') : null),
            const SizedBox(height: 8),
            GlassButton(label: _busy ? 'Jod raha hoon…' : 'Koi aur email (Yahoo, Zoho, Rediff, company)', icon: Icons.alternate_email_rounded,
                height: 48, onTap: _busy ? null : _imap),
            if (_loaded && (!google || !ms))
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(
                    '${!google ? 'Gmail sign-in' : ''}${!google && !ms ? ' aur ' : ''}${!ms ? 'Outlook sign-in' : ''} is server par abhi chalu nahi hai. '
                    'Tab tak "Koi aur email" se app password daal kar jodiye (Gmail aur Outlook bhi chalte hain).',
                    style: const TextStyle(color: C.faint, fontSize: 12)),
              ),
            if (_accounts.isNotEmpty) ...[
              const SizedBox(height: 18),
              Text(app.g('Nayi mail ki khabar'), style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text(app.g('Hoola har minute aapka inbox dekhta hai. Zaroori mail ya apne logon ki mail aaye to chat mein bata deta hai; '
                  'newsletters chup rehte hain. OTP codes kabhi nahi batata.'),
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                for (final m in const [('off', 'Shant'), ('vip', 'Zaroori'), ('all', 'Sab')])
                  ChoiceChip(
                    label: Text(app.g(m.$2)),
                    selected: _watchMode == m.$1,
                    onSelected: (_) => _setWatch(m.$1),
                  ),
              ]),
              const SizedBox(height: 18),
              Row(children: [
                Expanded(child: Text(app.g('Mail rules'), style: const TextStyle(fontWeight: FontWeight.w700))),
                IconButton(tooltip: app.g('Naya rule'), onPressed: _addRule,
                    icon: const Icon(Icons.add_circle_outline_rounded, color: C.accent)),
              ]),
              if (_rules.isEmpty)
                Text(app.g('Koi rule nahi. Bolo "bank ki mail aaye to archive karo" jaisa rule chat mein.'),
                    style: const TextStyle(color: C.muted, fontSize: 12.5)),
              for (final r in _rules)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Glass(child: Row(children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(r['name'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text(_ruleSummary(r), style: const TextStyle(color: C.chip, fontSize: 12.5)),
                      if ((r['hits'] as int? ?? 0) > 0)
                        Padding(padding: const EdgeInsets.only(top: 2),
                            child: Text('${r['hits']} baar chala', style: const TextStyle(color: C.muted, fontSize: 11.5))),
                    ])),
                    Switch(value: r['enabled'] == true, onChanged: (_) => _toggleRule(r)),
                    IconButton(onPressed: () => _delRule(r), icon: const Icon(Icons.delete_outline_rounded, color: C.muted)),
                  ])),
                ),
              if (_searches.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(app.g('Saved searches'), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                const SizedBox(height: 4),
                for (final q in _searches)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Glass(child: Row(children: [
                      const Icon(Icons.search_rounded, color: C.accent, size: 20),
                      const SizedBox(width: 8),
                      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(q['name'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                        const SizedBox(height: 2),
                        Text(_searchSummary(q), style: const TextStyle(color: C.chip, fontSize: 12.5)),
                      ])),
                    ])),
                  ),
                Text(app.g('Chat mein boliye “<naam> dikhao” — yeh sirf dikhata hai, kuch nahi badalta.'),
                    style: const TextStyle(color: C.muted, fontSize: 11.5)),
              ],
            ],
            const SizedBox(height: 18),
            const Text('Bolkar dekhiye', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"Aaj ki zaroori mails batao"',
              '"Ramesh ki mail ka jawab do, quotation attach karke"',
              '"Bijli bill wali PDF padho, kitna dena hai?"',
              '"Har subah 9 baje inbox summary bhejo"',
              '"Har Somvaar ko weekly inbox digest do"',
              '"Bank wali mails save karo search mein"',
              '"hello@newtika.in se bhejo yeh mail"',
              '"Snoozed mails dikhao"',
              '"Bills label ko green rang do"',
              '"Is Excel ki list mein sabko Diwali offer mail karo"',
              '"Kal subah 9 baje Swati ko yeh mail bhejna"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}
