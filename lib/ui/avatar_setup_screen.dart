import 'dart:convert';

import 'package:flutter/material.dart';

import '../hoola.dart';
import '../state.dart';
import 'glass.dart';

const _names = ['Santosh', 'Raju', 'Arjun', 'Veer', 'Priya', 'Meera', 'Sakhi', 'Kavya'];

const _knock = {
  'id_or_qr': 'Jinke paas mera Hoola ID / QR ho',
  'verified': 'Sirf verified log',
  'anyone': 'Koi bhi',
  'nobody': 'Abhi koi nahi',
};
const _kinds = {
  'message': 'Message',
  'voice_note': 'Voice note',
  'file': 'File (PDF, photo, Excel)',
  'app_file': 'APK / EXE (App Jaanch ke baad)',
  'email': 'Email',
  'link': 'Website link',
  'presentation': 'Presentation',
  'meeting': 'Meeting request',
  'payment_request': 'Payment request',
  'contact_card': 'Contact card',
  'location': 'Location',
};
const _alwaysAsk = {'payment_request', 'app_file'};
const _share = {
  'free_busy': 'Main free hoon ya busy',
  'office_hours': 'Office ka samay',
  'business_info': 'Business ki jaankari',
  'price_list': 'Price list',
  'phone': 'Mera phone number',
  'email_address': 'Mera email ID',
  'address': 'Mera pata',
};
const _aboutKeys = {'business_info', 'office_hours', 'price_list'};
const _aboutHint = {
  'business_info': 'Business ke baare mein: kya karte hain, kahan, kaise sampark (sirf jo sab ko batana theek ho)',
  'office_hours': 'Jaise: Som-Shani 10 se 7, Ravivar band',
  'price_list': 'Jaise: ONT 1200, installation 500, 100 Mbps plan 599/mahina',
};
const _alone = {
  'fix_meetings': 'Khaali samay mein meeting khud fix kare',
  'answer_faq': 'Business ke aam sawaalon ka jawab khud de',
  'accept_files_from_vip': 'VIP ki file khud le le',
};
const _langs = {
  'hinglish': 'Hinglish', 'hindi': 'हिंदी', 'marathi': 'मराठी', 'english': 'English', 'gujarati': 'ગુજરાતી',
  'tamil': 'தமிழ்', 'telugu': 'తెలుగు', 'kannada': 'ಕನ್ನಡ', 'bengali': 'বাংলা', 'punjabi': 'ਪੰਜਾਬੀ', 'malayalam': 'മലയാളം',
};

/// First run (and Profile > Mera Hoola): name your avatar, pick male / female and a voice, then set Mere Niyam
/// (how other people's avatars may reach you). [rulesOnly] opens straight at the rules.
class AvatarSetupScreen extends StatefulWidget {
  const AvatarSetupScreen({super.key, required this.app, this.rulesOnly = false, this.firstRun = false});
  final Santosh app;
  final bool rulesOnly;
  final bool firstRun;
  @override
  State<AvatarSetupScreen> createState() => _AvatarSetupScreenState();
}

class _AvatarSetupScreenState extends State<AvatarSetupScreen> {
  late int _page;
  late final TextEditingController _name;
  final _words = TextEditingController();
  late final TextEditingController _vip;
  late final TextEditingController _blocked;
  late String _gender;
  String _voice = '';
  late Map<String, dynamic> _rules;
  bool _busy = false;
  String? _err;
  List<String> _summary = [];

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _page = widget.rulesOnly ? 2 : 0;
    _name = TextEditingController(text: app.aName);
    _gender = app.aFemale ? 'f' : 'm';
    _voice = app.avatar['voice'] as String? ?? '';
    _rules = Map<String, dynamic>.from(jsonDecode(jsonEncode(app.avatarRules)) as Map);
    _rules.putIfAbsent('accept', () => <String, dynamic>{});
    _rules.putIfAbsent('share', () => <String, dynamic>{});
    _rules.putIfAbsent('decide_alone', () => <String, dynamic>{});
    _rules.putIfAbsent('quiet', () => <String, dynamic>{'on': true, 'from': '22:00', 'to': '08:00', 'vip_can_ring': true});
    _rules.putIfAbsent('learning', () => <String, dynamic>{'learn_from_my_work': true, 'share_lessons': 'ask'});
    _rules.putIfAbsent('about', () => <String, dynamic>{'business_info': '', 'office_hours': '', 'price_list': ''});
    _vip = TextEditingController(text: List<String>.from(_rules['vip'] as List? ?? const []).join(', '));
    _blocked = TextEditingController(text: List<String>.from(_rules['blocked_topics'] as List? ?? const []).join(', '));
  }

  @override
  void dispose() {
    _name.dispose();
    _words.dispose();
    _vip.dispose();
    _blocked.dispose();
    super.dispose();
  }

  String get _n => _name.text.trim().isEmpty ? 'Santosh' : _name.text.trim();
  String _gv(String s) => _gender == 'f' ? genderedHi(s) : s;

  Map<String, dynamic> _sub(String k) => (_rules[k] as Map).cast<String, dynamic>();

  List<String> _split(String s) => s.split(RegExp(r'[,\n]')).map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

  Future<void> _next() async {
    setState(() => _err = null);
    if (_page == 0) {
      setState(() => _busy = true);
      final e = await app.saveAvatar(name: _n);
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null) {
        setState(() => _err = e);
        return;
      }
      setState(() => _page = 1);
    } else if (_page == 1) {
      setState(() => _busy = true);
      final e = await app.saveAvatar(gender: _gender, voice: _voice);
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null) {
        setState(() => _err = e);
        return;
      }
      setState(() => _page = 2);
    } else if (_page == 2) {
      _rules['vip'] = _split(_vip.text);
      _rules['blocked_topics'] = _split(_blocked.text);
      setState(() => _busy = true);
      final e = await app.saveAvatar(rules: _rules);
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null) {
        setState(() => _err = e);
        return;
      }
      setState(() {
        _summary = List<String>.from(app.avatar['rules_summary'] as List? ?? const []);
        _page = 3;
      });
    } else {
      setState(() => _busy = true);
      final e = await app.saveAvatar(setupDone: true);
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null) {
        setState(() => _err = e);
        return;
      }
      if (!widget.firstRun && Navigator.of(context).canPop()) Navigator.of(context).pop();
    }
  }

  Future<void> _understand() async {
    final t = _words.text.trim();
    if (t.isEmpty) return;
    setState(() { _busy = true; _err = null; });
    try {
      final r = await app.api!.avatarParseRules(t);
      if (!mounted) return;
      setState(() {
        _rules = Map<String, dynamic>.from(r['rules'] as Map);
        _vip.text = List<String>.from(_rules['vip'] as List? ?? const []).join(', ');
        _blocked.text = List<String>.from(_rules['blocked_topics'] as List? ?? const []).join(', ');
      });
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Samajh gaye. Neeche dekh lijiye, phir Aage dabaiye.')));
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickTime(String key) async {
    final q = _sub('quiet');
    final parts = (q[key] as String? ?? '22:00').split(':');
    final t = await showTimePicker(
        context: context, initialTime: TimeOfDay(hour: int.tryParse(parts[0]) ?? 22, minute: int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0));
    if (t == null) return;
    setState(() => q[key] = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}');
  }

  // ---------------------------------------------------------------- pages
  Widget _namePage() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Apne Hoola ko naam dijiye', style: display(26)),
        const SizedBox(height: 6),
        const Text('Yeh aapka AI saathi hai. Naam aap rakhiye: wo isi naam se aapse baat karega, aur doosron ke Hoola '
            'use "aapka" isi naam se jaanenge.', style: TextStyle(color: C.muted, fontSize: 13.5)),
        const SizedBox(height: 18),
        Glass(
          child: TextField(
            controller: _name,
            maxLength: 20,
            textCapitalization: TextCapitalization.words,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            decoration: const InputDecoration(border: InputBorder.none, counterText: '', hintText: 'Jaise Santosh'),
            onChanged: (_) => setState(() {}),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final n in _names)
            ChoiceChip(
              label: Text(n),
              selected: _name.text.trim() == n,
              showCheckmark: false,
              selectedColor: C.accent,
              labelStyle: TextStyle(color: _name.text.trim() == n ? C.onAccent : C.chip, fontWeight: FontWeight.w600),
              onSelected: (_) => setState(() => _name.text = n),
            ),
        ]),
        const SizedBox(height: 14),
        const Text('Hindi, Marathi ya kisi bhi bhasha mein naam likh sakte hain. Bank, police ya sarkari naam nahi chalenge.',
            style: TextStyle(color: C.faint, fontSize: 12)),
      ]);

  Widget _genderCard(String g, String title, String sub, IconData icon) {
    final on = _gender == g;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() {
          if (_gender != g) _voice = '';
          _gender = g;
        }),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: on ? const Color(0x33FFB15C) : C.panel,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: on ? C.accent : C.line, width: on ? 2 : 1),
          ),
          child: Column(children: [
            Icon(icon, size: 34, color: on ? C.accent : C.chip),
            const SizedBox(height: 6),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(sub, textAlign: TextAlign.center, style: const TextStyle(color: C.muted, fontSize: 12)),
          ]),
        ),
      ),
    );
  }

  Widget _voicePage() {
    final voices = List<Map<String, dynamic>>.from(((app.avatar['voices'] as Map?)?[_gender] as List? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map)));
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('$_n kaisa / kaisi ho?', style: display(24)),
      const SizedBox(height: 6),
      const Text('Isse Hindi mein bolne ka tareeka aur awaaz tay hoti hai.', style: TextStyle(color: C.muted, fontSize: 13.5)),
      const SizedBox(height: 16),
      Row(children: [
        _genderCard('m', 'Purush', '"$_n kaam kar raha hai"', Icons.face_rounded),
        const SizedBox(width: 12),
        _genderCard('f', 'Mahila', '"$_n kaam kar rahi hai"', Icons.face_3_rounded),
      ]),
      const SizedBox(height: 18),
      Text('$_n ki awaaz (call par)', style: const TextStyle(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final v in voices)
          ChoiceChip(
            label: Text('${v['id']} · ${v['label']}'),
            selected: (_voice.isEmpty ? (voices.isNotEmpty ? voices.first['id'] : '') : _voice) == v['id'],
            showCheckmark: false,
            selectedColor: C.accent,
            labelStyle: TextStyle(
                color: (_voice.isEmpty ? (voices.isNotEmpty ? voices.first['id'] : '') : _voice) == v['id'] ? C.onAccent : C.chip,
                fontWeight: FontWeight.w600,
                fontSize: 12.5),
            onSelected: (_) => setState(() => _voice = v['id'] as String),
          ),
      ]),
    ]);
  }

  Widget _section(String title, [String? sub]) => Padding(
        padding: const EdgeInsets.only(top: 18, bottom: 6),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
          if (sub != null) Text(sub, style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      );

  Widget _chip(String label, bool on, VoidCallback tap) => ChoiceChip(
        label: Text(label),
        selected: on,
        showCheckmark: false,
        selectedColor: C.accent,
        labelStyle: TextStyle(color: on ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
        onSelected: (_) => tap(),
      );

  Widget _rulesPage() {
    final accept = _sub('accept');
    final share = _sub('share');
    final alone = _sub('decide_alone');
    final quiet = _sub('quiet');
    final learning = _sub('learning');
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('Mere Niyam', style: display(26)),
      const SizedBox(height: 6),
      Text(_gv('Doosre logon ke Hoola aapse sirf $_n ke zariye baat karenge. $_n in niyamon se tay karega ki kya aapko '
          'batana hai, kya khud sambhalna hai aur kya mana karna hai.'), style: const TextStyle(color: C.muted, fontSize: 13.5)),
      const SizedBox(height: 14),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Apne shabdon mein boliye / likhiye', style: TextStyle(fontWeight: FontWeight.w700)),
          TextField(
            controller: _words,
            minLines: 2,
            maxLines: 5,
            decoration: const InputDecoration(
                border: InputBorder.none,
                hintText: 'Jaise: "Family aur Swati hamesha pahunche. Loan wale mana. Raat 11 ke baad disturb mat karna. '
                    'Meeting khaali samay mein khud fix kar lo."'),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
                onPressed: _busy ? null : _understand, icon: const Icon(Icons.auto_awesome_rounded, size: 18), label: const Text('Samjho')),
          ),
        ]),
      ),
      _section('Kaun request bhej sakta hai'),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final e in _knock.entries) _chip(e.value, _rules['knock'] == e.key, () => setState(() => _rules['knock'] = e.key)),
      ]),
      _section('VIP: hamesha pahunchenge', 'Naam ya Hoola ID, comma se alag'),
      Glass(child: TextField(controller: _vip, decoration: const InputDecoration(border: InputBorder.none, hintText: 'Family, Swati, @kunal.raj'))),
      _section('Seedha mana', 'Jin baaton ki request $_n khud mana kar de'),
      Glass(child: TextField(controller: _blocked, decoration: const InputDecoration(border: InputBorder.none, hintText: 'loan, insurance, sales pitch'))),
      _section('Kya aa sakta hai', 'Seedha = $_n le lega · Poochho = pehle aapse · Mana = nahi'),
      for (final e in _kinds.entries)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(children: [
            Expanded(child: Text(e.value, style: const TextStyle(fontSize: 13))),
            Wrap(spacing: 6, children: [
              if (!_alwaysAsk.contains(e.key))
                _chip('Seedha', accept[e.key] == 'auto', () => setState(() => accept[e.key] = 'auto')),
              _chip('Poochho', (accept[e.key] ?? 'ask') == 'ask', () => setState(() => accept[e.key] = 'ask')),
              _chip('Mana', accept[e.key] == 'never', () => setState(() => accept[e.key] = 'never')),
            ]),
          ]),
        ),
      _section(_gv('$_n doosron ko kya bata sakta hai')),
      for (final e in _share.entries) ...[
        SwitchListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(e.value),
          value: share[e.key] == true,
          onChanged: (v) => setState(() => share[e.key] = v),
        ),
        if (_aboutKeys.contains(e.key) && share[e.key] == true)
          Glass(
            child: TextFormField(
              initialValue: (_sub('about')[e.key] as String?) ?? '',
              minLines: 1,
              maxLines: 5,
              decoration: InputDecoration(border: InputBorder.none, hintText: _aboutHint[e.key]),
              onChanged: (t) => _sub('about')[e.key] = t,
            ),
          ),
      ],
      _section(_gv('$_n khud kya kar sakta hai'), 'Baaki sab pehle aapse poochhega. Paise kabhi aapke tap ke bina nahi.'),
      for (final e in _alone.entries)
        SwitchListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(e.value),
          value: alone[e.key] == true,
          onChanged: (v) => setState(() => alone[e.key] = v),
        ),
      _section('Shaant samay'),
      SwitchListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: const Text('Is samay disturb mat karna'),
        value: quiet['on'] == true,
        onChanged: (v) => setState(() => quiet['on'] = v),
      ),
      if (quiet['on'] == true) ...[
        Row(children: [
          TextButton(onPressed: () => _pickTime('from'), child: Text('Se ${quiet['from'] ?? '22:00'}')),
          TextButton(onPressed: () => _pickTime('to'), child: Text('Tak ${quiet['to'] ?? '08:00'}')),
        ]),
        SwitchListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: const Text('VIP tab bhi pahunch sakte hain'),
          value: quiet['vip_can_ring'] == true,
          onChanged: (v) => setState(() => quiet['vip_can_ring'] = v),
        ),
      ],
      _section(_gv('$_n aapko kis bhasha mein batayega')),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final e in _langs.entries) _chip(e.value, (_rules['language'] ?? 'hinglish') == e.key, () => setState(() => _rules['language'] = e.key)),
      ]),
      _section('Seekhna'),
      SwitchListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: Text(_gv('$_n mere kaam se seekhta rahe')),
        value: learning['learn_from_my_work'] == true,
        onChanged: (v) => setState(() => learning['learn_from_my_work'] = v),
      ),
      const SizedBox(height: 4),
      const Text('Seekhi baatein doosron ke saath (bina personal jaankari):', style: TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 8, children: [
        _chip('Kabhi nahi', learning['share_lessons'] == 'never', () => setState(() => learning['share_lessons'] = 'never')),
        _chip('Pehle poochho', (learning['share_lessons'] ?? 'ask') == 'ask', () => setState(() => learning['share_lessons'] = 'ask')),
        _chip('Mere groups mein', learning['share_lessons'] == 'groups', () => setState(() => learning['share_lessons'] = 'groups')),
      ]),
      const SizedBox(height: 14),
      const Text('Yeh hamesha rahega: paise sirf aapke tap se. PIN, OTP, password kabhi kisi ko nahi.',
          style: TextStyle(color: C.teal, fontSize: 12.5, fontWeight: FontWeight.w600)),
    ]);
  }

  Widget _confirmPage() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Namaste! Main $_n.', style: display(26)),
        const SizedBox(height: 6),
        Text(_gv('Aapke niyam yeh hain. $_n inhi ke hisaab se doosre Hoola se baat karega. Profile > Mere Niyam mein kabhi bhi badal sakte hain.'),
            style: const TextStyle(color: C.muted, fontSize: 13.5)),
        const SizedBox(height: 14),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final l in _summary)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Padding(padding: EdgeInsets.only(top: 2), child: Icon(Icons.check_rounded, size: 16, color: C.ok)),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_gv(l), style: const TextStyle(fontSize: 13))),
                ]),
              ),
          ]),
        ),
      ]);

  @override
  Widget build(BuildContext context) {
    final pages = [_namePage, _voicePage, _rulesPage, _confirmPage];
    final last = _page == 3;
    final canBack = _page > (widget.rulesOnly ? 2 : 0);
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        automaticallyImplyLeading: !widget.firstRun,
        title: Text(widget.firstRun ? appName : (widget.rulesOnly ? 'Mere Niyam' : 'Mera Hoola')),
      ),
      body: Aurora(
        child: SafeArea(
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                for (var i = widget.rulesOnly ? 2 : 0; i < 4; i++)
                  Expanded(
                    child: Container(
                      height: 4,
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      decoration: BoxDecoration(color: i <= _page ? C.accent : C.line, borderRadius: BorderRadius.circular(2)),
                    ),
                  ),
              ]),
            ),
            Expanded(
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
                pages[_page](),
                if (_err != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_err!, style: const TextStyle(color: C.bad))),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Row(children: [
                if (canBack)
                  Padding(
                    padding: const EdgeInsets.only(right: 10),
                    child: TextButton(onPressed: _busy ? null : () => setState(() => _page -= 1), child: const Text('Peeche')),
                  ),
                Expanded(
                  child: GradientButton(
                    label: _busy ? 'Ruk jaiye…' : (last ? 'Shuru karein' : 'Aage'),
                    icon: last ? Icons.check_rounded : Icons.arrow_forward_rounded,
                    onTap: _busy ? null : _next,
                  ),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
