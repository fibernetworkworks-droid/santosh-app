import 'dart:async';
import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'artifacts_screen.dart';
import 'bazar_screen.dart';
import 'calendar_screen.dart';
import 'drive_screen.dart';
import 'email_screen.dart';
import 'forms_screen.dart';
import 'glass.dart';
import 'keep_alive.dart';
import 'phone_hoola.dart';
import 'video_editor.dart';
import 'operator_screen.dart';
import 'studio_screen.dart';
import 'home_devices_screen.dart';
import 'notebook_screen.dart';
import 'pc_screen.dart';
import 'photos_screen.dart';
import 'sheets_screen.dart';
import 'slides_screen.dart';
import 'youtube_screen.dart';
import 'appcheck_screen.dart';
import 'avatar_look.dart';
import 'avatar_setup_screen.dart';
import 'hoola_net_screen.dart';
import 'hoola_samaj_screen.dart';
import 'voice_id_screen.dart';
import 'procedures_screen.dart';
import 'shop_screen.dart';
import 'id_locker_screen.dart';
import 'chai_screen.dart';
import 'darzi_screen.dart';
import 'lekhak_screen.dart';
import 'office_screen.dart';
import 'employee_screen.dart';
import 'mshop_screen.dart';
import 'phonedoc_screen.dart';
import 'jaanch_screen.dart';
import 'gst_screen.dart';
import 'payroll_screen.dart';
import 'finance_screen.dart';
import 'audit_screen.dart';
import 'approve_key_screen.dart';
import 'insurance_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key, required this.app, required this.onReset});
  final Santosh app;
  final VoidCallback onReset;
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _name = TextEditingController();
  final _city = TextEditingController();
  String? _briefing;
  List<Map<String, dynamic>> _facts = [];
  bool _loading = true;

  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    widget.app.addListener(_maybeLoad);
    _maybeLoad();
  }

  @override
  void dispose() {
    widget.app.removeListener(_maybeLoad);
    super.dispose();
  }

  void _maybeLoad() {
    if (!_loaded && widget.app.connected && widget.app.api != null) {
      _loaded = true;
      _load();
    }
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    try {
      final p = await api.profile();
      _name.text = p['name'] as String? ?? '';
      _city.text = p['city'] as String? ?? '';
      _briefing = p['briefing_time'] as String?;
      _facts = await api.memory();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _save() async {
    try {
      await widget.app.api!.saveProfile({
        'name': _name.text.trim(),
        'city': _city.text.trim(),
        'language': languages[widget.app.language],
        'briefing_time': _briefing ?? 'off',
        'conversation_id': widget.app.conversationId,
      });
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Save ho gaya')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save nahi hua: $e')));
    }
  }

  Future<void> _pickBriefing() async {
    final parts = (_briefing ?? '07:30').split(':');
    final t = await showTimePicker(context: context, initialTime: TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1])));
    if (t != null) setState(() => _briefing = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}');
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    if (_loading) {
      return Center(child: Text(app.connected ? 'Load ho raha hai…' : 'Server se connect ho raha hai…', style: const TextStyle(color: C.muted)));
    }
    return ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
      Text('Profile', style: display(28)),
      const SizedBox(height: 14),
      ListenableBuilder(
        listenable: app,
        builder: (context, _) => Glass(
          child: Column(children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const AvatarFace(size: 40, ring: true),
              title: Text('Mera Hoola: ${app.aName}', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Naam, ${app.aFemale ? 'mahila' : 'purush'}, roop, awaaz'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AvatarSetupScreen(app: app))),
            ),
            ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.palette_outlined, color: C.accent2),
                title: Text('${app.aName} ka roop', style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(app.aFemale ? '100 roop, duniya bhar se' : '100 roop, duniya bhar se, ya asli Santosh'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () async {
                  final id = await Navigator.of(context).push<String>(
                      MaterialPageRoute(builder: (_) => LookPickerScreen(initial: app.aLook, avatarName: app.aName, gender: app.aFemale ? 'f' : 'm')));
                  if (id == null) return;
                  final e = await app.saveAvatar(look: id);
                  if (e != null && context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e)));
                },
              ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.hub_rounded, color: C.violet),
              title: const Text('Hoola Network', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Mera Hoola ID, QR, jude log, aur doosre Hoola se baatein'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaNetScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.lightbulb_rounded, color: C.accent),
              title: Text('${app.aName} ne kya seekha', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Seekhi baatein, share kiya hua, lagi hui skills'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaLearnedScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.rule_rounded, color: C.teal),
              title: const Text('Mere Niyam', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Doosre Hoola ${app.aName} ke zariye aapse kaise jud sakte hain'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AvatarSetupScreen(app: app, rulesOnly: true))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.work_rounded, color: C.accent),
              title: Text('${app.aName} · Employee', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('${app.aName} aapke business mein kaam kare: team, bharosa, hisaab, roz ki report'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmployeeScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.badge_rounded, color: C.accent),
              title: const Text('Pehchaan Locker', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Aadhaar, PAN, Voter ID… taala band. ${app.aName} forms mein khud bharega'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => IdLockerScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.health_and_safety_rounded, color: C.accent),
              title: Text('${app.aName} Jaanch', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Har hissa abhi jaancho: kya kharab hai, kaise theek hoga, kaun si website server se nahi khulti'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => JaanchScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.health_and_safety_rounded, color: C.accent),
              title: const Text('Bima sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Policy book, premium yaad, cover ka gap, quote tulna, claim: ${app.aName} karega, paisa graahak seedha insurer ko'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InsuranceScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.fact_check_rounded, color: C.accent),
              title: const Text("Auditor's assistant", style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('TB + day book ki jaanch, materiality, sample, confirmation, working papers: ${app.aName} karega, raay aur sign aapke'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AuditScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.query_stats_rounded, color: C.accent),
              title: const Text('Financial analyst', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Tally + bank se munafa, ratio, cash kitne din, vasooli, MSME, loan, advance tax: ${app.aName} samjhayega'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FinanceScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.payments_rounded, color: C.accent),
              title: const Text('Payroll officer', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Har mahine ki salary, PF / ESIC / PT / TDS, payslip, bank file: ${app.aName} banayega, payment aap karengi'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PayrollScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.receipt_long_rounded, color: C.accent),
              title: const Text('GST sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Har client ke bill check, GSTR-1 / 3B, 2B milaan, due date, notice: ${app.aName} karega, filing aapki haan se'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.fingerprint_rounded, color: C.accent),
              title: const Text('Fingerprint se haan', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Paise wale card sirf aapke fingerprint se haan honge (app ki chaabi chori ho to bhi safe)'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ApproveKeyScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.healing_rounded, color: C.accent),
              title: const Text('Phone Doctor', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Phone slow, garam, network, battery, chori: ${app.aName} jaanch karke step-by-step theek karayega'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhoneDocScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.phone_iphone_rounded, color: C.accent),
              title: const Text('Mobile dukaan sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Repair job + photo, warranty, taiyaar hai message, recharge register: ${app.aName} sambhalega'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MShopScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.local_cafe_rounded, color: C.accent),
              title: const Text('Chai stall sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('UPI se roz ki bikri, sabse achha ghanta, kal ka doodh-chini: ${app.aName} sambhalega'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ChaiScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.content_cut_rounded, color: C.accent),
              title: const Text('Darzi sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Silai ke order, har graahak ka naap, trial / delivery, daam: ${app.aName} sambhalega'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DarziScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.business_center_rounded, color: C.accent),
              title: Text('${app.aName} · Office manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Saamaan, repair, renewal, team ki deadline, petty cash, hafte ka note; kharcha aapki Haan se'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => OfficeScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.edit_document, color: C.accent),
              title: Text('${app.aName} · Typist aur translator', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Boliye, letter taiyaar; Hindi / Marathi / English anuvaad, grammar, Kruti Dev; sign aapki Haan se'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LekhakScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.shopping_bag_rounded, color: C.accent),
              title: const Text('Order karo', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Amazon, Flipkart, Blinkit, Zepto, Swiggy, Zomato, IRCTC...: ${app.aName} sab karega, payment aap'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShopScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.auto_awesome_rounded, color: C.accentSoft),
              title: const Text('Seekhe hue kaam', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Lambe kaam ${app.aName} ne kaise kiye: dekhiye, badliye, band kijiye'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProceduresScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.record_voice_over_rounded, color: C.ok),
              title: const Text('Awaaz Pehchaan', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('${app.aName} awaaz se jaane kaun bol raha hai: aap, Maa, Papa…'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VoiceIdScreen(app: app))),
            ),
          ]),
        ),
      ),
      const SizedBox(height: 18),
      ListenableBuilder(listenable: app, builder: (context, _) => _BackgroundCard(app: app)),
      const SizedBox(height: 18),
      const _WakeCard(),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.auto_awesome_motion_rounded, color: C.accent),
          title: Text('${app.aName} · Video Studio', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Bina shooting ke AI video: ad, greeting, product reel — har kharche par aapki haan'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => StudioScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.computer_rounded, color: C.accent),
          title: Text('${app.aName} · Computer Operator', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Online form, sarkari portal, download, status check — OTP / submit / payment aap karti hain'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => OperatorScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.movie_creation_rounded, color: C.accent),
          title: Text('${app.aName} · Video Editor', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Kachcha video do: reel / Short / Status / YouTube banake, khud check karke deta hai'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VideoEditorScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.phone_android_rounded, color: C.accent),
          title: Text('Phone mein ${app.aName}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Assistant (home button), floating bubble, home-screen widget, app update'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhoneHoolaScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.computer_rounded, color: C.teal),
          title: const Text('Mera PC', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Office ka computer jodiye: files, print aur Tally phone se'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PcScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.menu_book_rounded, color: C.teal),
          title: const Text('Hoola Notebook', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('NotebookLM jaisa: files / links se jawab, study guide, Hindi audio overview'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotebooksScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.smart_display_rounded, color: Color(0xFFFF4D4D)),
          title: const Text('YouTube', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Video dhoondhna, video ka summary, mere channel ke views / analytics / comments'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => YouTubeScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.shield_rounded, color: C.ok),
          title: const Text('App Jaanch', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('APK / EXE install karne se pehle jaanchiye: fraud app to nahi?'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppCheckScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.add_to_drive_rounded, color: C.accent),
          title: const Text('Google Drive', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Files dhoondhna, padhna, phone / PC / email par bhejna, upload, share'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DriveScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.dynamic_form_rounded, color: C.accent2),
          title: const Text('Google Forms', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Form aur quiz banana, jawab ka summary, naye jawab par khabar'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FormsScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.slideshow_rounded, color: C.warn),
          title: const Text('Google Slides', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Kisi bhi topic par presentation, deck ka summary, PDF / PowerPoint'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SlidesScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.photo_library_rounded, color: C.accentSoft),
          title: const Text('Google Photos', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Photos chunkar bhejiye (email / Drive / PC) · Photos mein upload aur albums'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhotosScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.table_chart_rounded, color: C.ok),
          title: const Text('Google Sheets', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Sheets padhna, hisaab, rows jodna, nayi sheet, Excel import / export'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SheetsScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.event_rounded, color: C.teal),
          title: const Text('Calendar', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Google Calendar jodiye · meetings, Meet link, free time, meeting se pehle yaad'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CalendarScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.mail_rounded, color: C.accentSoft),
          title: const Text('Email', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Gmail, Outlook ya koi bhi email jodiye · signature · roz ki inbox summary'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmailScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.auto_awesome_mosaic_rounded, color: C.accent),
          title: const Text('Mere Artifacts', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Hoola ke banaye apps, tracker, chart aur documents'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArtifactsScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.home_rounded, color: C.accentSoft),
          title: const Text('Ghar', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('AC, TV, speaker phone se · Samsung / LG / Bosch appliances'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HomeDevicesScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      ListenableBuilder(listenable: app, builder: (context, _) => app.account != null ? _AccountCard(app: app) : const SizedBox.shrink()),
      if (app.account != null) const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.power_rounded, color: C.accent),
          title: const Text('Connectors · 700+ plugins', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Bill, kirana, UPI, cab, Swiggy/Zomato · kharch ki seema'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BazarScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(children: [
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'Naam')),
          TextField(controller: _city, decoration: const InputDecoration(labelText: 'Shehar (mausam ke liye)')),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Roz subah ki briefing'),
            subtitle: Text(_briefing == null ? 'Band' : 'Har din $_briefing baje: mausam, reminders, lists'),
            value: _briefing != null,
            onChanged: (on) => on ? _pickBriefing() : setState(() => _briefing = null),
          ),
          if (_briefing != null) Align(alignment: Alignment.centerLeft, child: TextButton(onPressed: _pickBriefing, child: const Text('Samay badlein'))),
          const SizedBox(height: 6),
          GradientButton(label: 'Save', height: 48, onTap: _save),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Bhasha aur awaaz', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final e in languages.entries)
              ChoiceChip(
                label: Text(e.value),
                selected: app.language == e.key,
                showCheckmark: false,
                selectedColor: C.accent,
                labelStyle: TextStyle(color: app.language == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600),
                onSelected: (_) async {
                  await app.saveSettings(lang: e.key);
                  setState(() {});
                },
              ),
          ]),
          if (app.realtimeVoice && ((app.avatar['voices'] as Map?)?[app.aFemale ? 'f' : 'm'] as List? ?? const []).isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('${app.aName} ki awaaz (Baat tab)', style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final v in ((app.avatar['voices'] as Map?)?[app.aFemale ? 'f' : 'm'] as List? ?? const []))
                ChoiceChip(
                  label: Text('${(v as Map)['id']} · ${v['label']}'),
                  selected: app.voiceName == v['id'],
                  showCheckmark: false,
                  selectedColor: C.accent,
                  labelStyle: TextStyle(color: app.voiceName == v['id'] ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                  onSelected: (_) async {
                    await app.saveAvatar(voice: v['id'] as String);
                    setState(() {});
                  },
                ),
            ]),
          ],
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Bolkar poochhun to Hoola bolkar jawab de'),
            value: app.speakReplies,
            onChanged: (v) async {
              await app.saveSettings(speak: v);
              setState(() {});
            },
          ),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Hoola ko yaad hai', style: TextStyle(fontWeight: FontWeight.w700)),
          const Text('Pin = hamesha dhyan mein (chhoti baatein). Baaki yaadein zaroorat par dhoondh leta hai.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          if (_facts.isEmpty) const Padding(padding: EdgeInsets.only(top: 6), child: Text('Abhi kuch nahi. Boliye: "Yaad rakhna, mummy ka birthday 5 June hai".', style: TextStyle(color: C.muted))),
          for (final f in _facts)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: IconButton(
                tooltip: f['pinned'] == true ? 'Pin hatao' : 'Hamesha yaad (pin)',
                icon: Icon(f['pinned'] == true ? Icons.push_pin_rounded : Icons.push_pin_outlined,
                    color: f['pinned'] == true ? C.accent : C.faint, size: 20),
                onPressed: () async {
                  try {
                    await app.api!.pinMemory((f['id'] as num).toInt(), f['pinned'] != true);
                    _facts = await app.api!.memory();
                    setState(() {});
                  } catch (e) {
                    if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                  }
                },
              ),
              title: Text(f['text'] as String? ?? ''),
              trailing: IconButton(
                tooltip: 'Bhool jao',
                icon: const Icon(Icons.delete_outline, color: C.muted),
                onPressed: () async {
                  await app.api!.forget((f['id'] as num).toInt());
                  _facts = await app.api!.memory();
                  setState(() {});
                },
              ),
            ),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Server', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(app.serverUrl, style: const TextStyle(color: C.muted)),
          Text(app.dryRun ? 'WhatsApp: test mode' : 'WhatsApp: live', style: const TextStyle(color: C.muted)),
          TextButton(onPressed: widget.onReset, child: const Text('Server badlein')),
        ]),
      ),
    ]);
  }
}


/// Background mode: Santosh keeps working (notifications, alarms, calendar, automatic jobs) with the app closed.
class _BackgroundCard extends StatefulWidget {
  const _BackgroundCard({required this.app});
  final Santosh app;
  @override
  State<_BackgroundCard> createState() => _BackgroundCardState();
}

class _BackgroundCardState extends State<_BackgroundCard> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    widget.app.refreshBackgroundInfo();
    HoolaKeepAlive.check(widget.app);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) {
      widget.app.refreshBackgroundInfo(); // back from a settings screen
      HoolaKeepAlive.check(widget.app);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final on = app.background;
    final st = app.backgroundStatus;
    final statusText = !on
        ? 'Band: app band hone par notifications aur phone ke kaam ruk jaate hain'
        : !app.backgroundRunning
            ? 'Shuru ho raha hai…'
            : st == 'connected'
                ? 'Chalu · Hoola duty par hai'
                : st.isEmpty
                    ? 'Chalu'
                    : 'Chalu · $st';
    Widget fix(String title, String sub, String button, Future<void> Function() onTap) => Container(
          margin: const EdgeInsets.only(top: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0x2EFFB15C), borderRadius: BorderRadius.circular(16)),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xFFFFD9A8))),
                Text(sub, style: const TextStyle(fontSize: 12.5, color: Color(0xFFFFD9A8))),
              ]),
            ),
            TextButton(onPressed: onTap, child: Text(button)),
          ]),
        );
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Background mein kaam', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(statusText, style: TextStyle(color: on && app.backgroundRunning ? C.ok : C.muted, fontSize: 12.5)),
          value: on,
          onChanged: (v) => app.setBackground(v),
        ),
        const Text('App band ho tab bhi: Hoola ke jawab notification mein, alarm aur timer bajenge, calendar mein entry, aur Hoola ke roz ke kaam chalte rahenge.',
            style: TextStyle(fontSize: 12.5, color: C.muted)),
        if (on && app.batteryOptimized)
          fix('Battery saver Hoola ko rok sakta hai', 'Hoola ko "Unrestricted / Don\'t optimize" par rakhiye', 'Theek karo', Native.askBattery),
        ValueListenableBuilder<Map<String, dynamic>?>(
          valueListenable: HoolaKeepAlive.last,
          builder: (context, r, _) {
            final n = (r?['problems'] as List? ?? const []).length;
            final kills = ((r?['counts'] as Map?)?['oem_kill'] as num? ?? 0).toInt();
            return fix(
                '${app.aName} band na ho',
                r == null
                    ? 'Xiaomi / Oppo / Realme / Vivo / Samsung: ek baar settings theek kijiye'
                    : n == 0
                        ? 'Sab theek · checklist dekhiye'
                        : '$n cheez theek karni hai${kills > 0 ? ' · phone ne 7 din mein $kills baar band kiya' : ''}',
                n == 0 && r != null ? 'Dekho' : 'Theek karo',
                () => HoolaKeepAlive.open(context, app));
          },
        ),
        if (!app.exactAlarms)
          fix('Alarm time par bajne ke liye', '"Alarms & reminders" ki permission dijiye', 'Allow', () async {
            await Native.askExactAlarms();
            await Future.delayed(const Duration(seconds: 2));
            await app.refreshBackgroundInfo();
          }),
        if (on && !app.hasCalendar)
          fix('Calendar permission', 'Taaki Hoola meetings seedha calendar mein save kare', 'Allow', () async {
            await Native.askCalendar();
            await Future.delayed(const Duration(seconds: 2));
            await app.refreshBackgroundInfo();
          }),
      ]),
    );
  }
}


/// Shows the signed-in Google account and connected services (product mode).
class _AccountCard extends StatelessWidget {
  const _AccountCard({required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final acc = app.account!;
    final conns = List<Map<String, dynamic>>.from(acc['connections'] as List? ?? const []);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.account_circle_rounded, color: C.accent, size: 36),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${acc['name'] ?? ''}'.isEmpty ? 'Signed in' : '${acc['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              Text('${acc['email'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ]),
          ),
        ]),
        const SizedBox(height: 10),
        for (final c in conns)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.check_circle_rounded, color: C.ok),
            title: Text('${c['provider'] == 'google' ? 'Google' : c['provider']}  ·  ${c['account'] ?? ''}'),
            subtitle: const Text('Gmail · Calendar · Drive · Docs · Sheets', style: TextStyle(fontSize: 11.5, color: C.muted)),
            trailing: TextButton(onPressed: () => app.disconnectProvider(c['provider'] as String), child: const Text('Hatao')),
          ),
      ]),
    );
  }
}


/// "Hey Santosh": on-device wake word, works with the screen off and locked.
class _WakeCard extends StatefulWidget {
  const _WakeCard();
  @override
  State<_WakeCard> createState() => _WakeCardState();
}

class _WakeCardState extends State<_WakeCard> {
  bool _on = false;
  String _status = '';
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _refresh();
    _poll = Timer.periodic(const Duration(seconds: 3), (_) => _refresh());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    final s = await Native.wakeStatus();
    if (!mounted) return;
    setState(() {
      _on = s['on'] == true || s['wanted'] == true;
      _status = (s['status'] as String?) ?? '';
    });
  }

  Future<void> _toggle(bool on) async {
    if (on) {
      final r = await Native.wakeStart();
      if (r == 'permission' && mounted) {
        setState(() => _status = 'Mic ki permission dijiye, phir dobara chalu karein');
      }
    } else {
      await Native.wakeStop();
    }
    await Future.delayed(const Duration(milliseconds: 600));
    _refresh();
  }

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            secondary: const Icon(Icons.hearing_rounded, color: C.teal),
            title: const Text('“Hey Santosh”', style: TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(_status.isNotEmpty
                ? _status
                : 'Phone lock ho ya screen band, bas boliye “Hey Santosh”. Awaaz phone par hi pehchani jaati hai.'),
            value: _on,
            onChanged: _toggle,
          ),
          const Text('Lock screen par sirf Baat khulti hai. Payment ke liye phone unlock karna zaroori hai.',
              style: TextStyle(fontSize: 12, color: C.muted, height: 1.4)),
        ]),
      );
}
