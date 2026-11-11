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
import 'ads_screen.dart';
import 'brand_screen.dart';
import 'aftersales_screen.dart';
import 'callcentre_screen.dart';
import 'feedback_screen.dart';
import 'helpdesk_screen.dart';
import 'samudaay_screen.dart';
import 'seva_screen.dart';
import 'shikayat_screen.dart';
import 'wapsi_screen.dart';
import 'appreview_screen.dart';
import 'cyber_screen.dart';
import 'devops_screen.dart';
import 'devsahayak_screen.dart';
import 'docwriter_screen.dart';
import 'ispnoc_screen.dart';
import 'itadmin_screen.dart';
import 'product_screen.dart';
import 'qa_screen.dart';
import 'courier_screen.dart';
import 'customs_screen.dart';
import 'drivers_screen.dart';
import 'fleet_screen.dart';
import 'logistics_screen.dart';
import 'travel_screen.dart';
import 'warehouse_screen.dart';
import 'archassist_screen.dart';
import 'memory_page_screen.dart';
import 'bahar_screen.dart';
import 'interior_screen.dart';
import 'propagent_screen.dart';
import 'rentdesk_screen.dart';
import 'sitesup_screen.dart';
import 'society_screen.dart';
import 'vakil_screen.dart';
import 'legalres_screen.dart';
import 'shiksha_screen.dart';
import 'guru_screen.dart';
import 'daftar_screen.dart';
import 'shodh_screen.dart';
import 'prayog_screen.dart';
import 'compliance_screen.dart';
import 'contracts_screen.dart';
import 'cosec_screen.dart';
import 'notary_screen.dart';
import 'pidesk_screen.dart';
import 'dpo_screen.dart';
import 'frontoffice_screen.dart';
import 'eventplan_screen.dart';
import 'shaadi_screen.dart';
import 'tourguide_screen.dart';
import 'homestay_screen.dart';
import 'banquet_screen.dart';
import 'editdesk_screen.dart';
import 'motiondesk_screen.dart';
import 'filmdesk_screen.dart';
import 'patrakar_screen.dart';
import 'photoassist_screen.dart';
import 'graphic_screen.dart';
import 'artistmgr_screen.dart';
import 'kitab_screen.dart';
import 'podcast_screen.dart';
import 'influencer_screen.dart';
import 'site_screen.dart';
import 'app_design_screen.dart';
import 'kalam_screen.dart';
import 'telecall_screen.dart';
import 'deal_screen.dart';
import 'dosti_screen.dart';
import 'handoff_screen.dart';
import 'video_editor.dart';
import 'operator_screen.dart';
import 'studio_screen.dart';
import 'home_devices_screen.dart';
import 'notebook_screen.dart';
import 'pc_screen.dart';
import 'hoola_pc_screen.dart';
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
import 'seo_screen.dart';
import 'thok_screen.dart';
import 'niryat_screen.dart';
import 'franchise_screen.dart';
import 'theka_screen.dart';
import 'kharcha_screen.dart';
import 'blender_screen.dart';
import 'gyaan_screen.dart';
import 'postgres_screen.dart';
import 'voice_learned_screen.dart';
import 'call_quality_screen.dart';
import 'enterprise_screen.dart';
import 'voice_engine_screen.dart';
import 'screen_link.dart';
import 'employees_screen.dart';

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
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not save: $e')));
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
      return Center(child: Text(app.connected ? 'Loading…' : 'Connecting to the server…', style: const TextStyle(color: C.muted)));
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
              title: Text('My Hoola: ${app.aName}', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Naam, ${app.aFemale ? 'mahila' : 'purush'}, roop, awaaz'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AvatarSetupScreen(app: app))),
            ),
            ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.palette_outlined, color: C.accent2),
                title: Text('${app.aName} ka roop', style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(app.aFemale ? '100 roop, duniya bhar se' : '100 voices, from all over the world, or the original Santosh'),
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
              subtitle: Text('My Hoola ID, QR, connected people, and talks with other Hoolas'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaNetScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.lightbulb_rounded, color: C.accent),
              title: Text('What ${app.aName} has learned', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Things learned, what was shared, installed skills'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaLearnedScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.rule_rounded, color: C.teal),
              title: const Text('My Rules', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('How other Hoolas can reach you through ${app.aName}'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AvatarSetupScreen(app: app, rulesOnly: true))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.groups_rounded, color: C.accent),
              title: const Text('Employees · hire AI staff', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('SEO Specialist works 24/7 on your website and Google; its desk appears once you hire it'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmployeesScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.work_rounded, color: C.accent),
              title: Text('${app.aName} · Employee', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('${app.aName} works in your business: team, trust, accounts, daily report'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmployeeScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.badge_rounded, color: C.accent),
              title: const Text('ID Locker', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Aadhaar, PAN, Voter ID… locked away. ${app.aName} will fill them into forms itself'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => IdLockerScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.engineering_rounded, color: C.accent),
              title: const Text('Theka sahayak (contractor)', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Tender dates, BOQ, measurements, RA bills and deductions, petty contractors, site diary, EOT: ${app.aName} does it, bills go out with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ThekaScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.storefront_rounded, color: C.accent),
              title: const Text('Franchise sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Sales and profit of each outlet, royalty statements, licences, agreement dates, SOP audits: ${app.aName} does it, reports go out with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FranchiseScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.public_rounded, color: C.accent),
              title: const Text('Niryat sahayak (export)', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Buyers, PI, invoice + packing list, papers, when money comes after the shipping bill, RoDTEP: ${app.aName} does it, sending needs your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NiryatScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.warehouse_rounded, color: C.accent),
              title: const Text('Thok sahayak (wholesale)', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('GST bills from orders, credit and recovery, cheques, supplier bills, what to order: ${app.aName} does it, bills go out with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ThokScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.travel_explore_rounded, color: C.accent),
              title: const Text('SEO sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Website checks, speed, Google Search Console, page plans, Google profile posts + review replies: ${app.aName} does it, you publish'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SeoScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.health_and_safety_rounded, color: C.accent),
              title: Text('${app.aName} Check', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Check every part now: what is broken, how to fix it, which website does not open from the server'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => JaanchScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.diversity_3_rounded, color: C.accent),
              title: Text('${app.aName} ki Dosti', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Talk work with friends\' avatars by itself, share your experience and skills; documents with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DostiScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.shopping_bag_rounded, color: C.accent),
              title: const Text('Buy and sell', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('A list to a shop / wholesaler, the quote from their Hoola, your yes; your own stock and selling rules'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DealsScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.verified_user_rounded, color: C.accent),
              title: const Text('Consents, papers, outside agents', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Check bank data (AA) and health (ABHA) consents, DigiLocker, ONDC sheet, A2A agents: the decision is yours, ${app.aName} will explain'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HandoffScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.health_and_safety_rounded, color: C.accent),
              title: const Text('Bima sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Policy book, premium reminders, cover gaps, quote comparison, claims: ${app.aName} does it, the customer pays the insurer directly'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InsuranceScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.headset_mic_rounded, color: C.accent),
              title: Text('${app.aName} · Telecaller', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Whom to call and when and why, a script for each customer, a log after the call; you make the calls'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TelecallScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.edit_note_rounded, color: C.accent),
              title: Text('${app.aName} · Content writer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Blog, product page, email in your voice; every claim checked; publish with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => KalamScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.campaign_rounded, color: C.accent),
              title: Text('${app.aName} · Performance marketer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Find wasted money from the ad report, budget changes with reasons (with your yes), test new ad copy'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AdsScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.web_rounded, color: C.teal),
              title: Text('${app.aName} · Website', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Say two words: plan, 3 looks, motion graphics, watch each part being built, checks, preview'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SiteScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.connected_tv_rounded, color: C.accent),
              title: const Text('Hoola Screen', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Connect a mini screen / TV: ${app.aName}\'s work and cards will show live there'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ScreenLinkScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.phone_android_rounded, color: C.accent),
              title: Text('${app.aName} · App designer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Design every screen of the Android + iPhone app first: 3 looks, try it by tapping, then "Confirm design"'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppDesignScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.palette_rounded, color: C.accent),
              title: Text('${app.aName} · Brand designer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Posters in your logo and colours, sizes for every platform, festival posts; final with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BrandScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.view_in_ar_rounded, color: C.accent),
              title: Text('${app.aName} · 3D Studio', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Real Blender: product mockups, layouts, gifts, 3D prints; renders, 360° video, GLB / STL'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => Blender3dScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.storage_rounded, color: C.accent),
              title: const Text('Postgres database', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Connect your database: Hoola reads it (read-only), changes only with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PostgresScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.auto_stories_rounded, color: C.accent),
              title: Text('${app.aName}\'s knowledge', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Answers from your files, Drive and mail, with sources; it does not make up what it does not know'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GyaanScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.support_agent_rounded, color: C.accent),
              title: Text('${app.aName} · Customer support', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Instant answers from knowledge, complaints + deadlines, refunds with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SevaScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.computer_rounded, color: C.accent),
              title: Text('${app.aName} · IT Helpdesk', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Computer, printer and internet problems step by step; technician; phishing checks'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HelpdeskScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.report_problem_rounded, color: C.accent),
              title: Text('${app.aName} · Shikayat sahayak', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Record complaints, evidence, deadlines, compensation with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShikayatScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.home_repair_service_rounded, color: C.accent),
              title: Text('${app.aName} · After-sales service', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Service due, technician visit, report, AMC, warranty claim'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AftersalesScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.reviews_rounded, color: C.accent),
              title: const Text('Feedback sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Reviews, surveys, what to fix first'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FeedbackScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.assignment_return_rounded, color: C.accent),
              title: Text('${app.aName} · Returns desk', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Returns helper: returns, pickups, QC, refunds (with your yes)'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => WapsiScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.groups_2_rounded, color: C.accent),
              title: const Text('Community sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Welcome in the group, FAQ answers, scam / abuse alerts'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SamudaayScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.phone_in_talk_rounded, color: C.accent),
              title: Text('${app.aName} · Call centre', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Hoola answers the business phone: only from your script, can connect to a human, call-back'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CallCentreScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.terminal_rounded, color: C.accent),
              title: Text('${app.aName} · Developer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Write code, bug-fix PRs, tests, reviews; merge / deploy with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DevsahayakScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.bug_report_rounded, color: C.accent),
              title: Text('${app.aName} · App tester (QA)', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Test cases, bugs, re-checks after fixes, is the release ready?'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => QaScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.admin_panel_settings_rounded, color: C.accent),
              title: Text('${app.aName} · IT Admin', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Licence, renewal, access, joiner-leaver, staff guides'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ItadminScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.lan_rounded, color: C.accent),
              title: Text('${app.aName} · NOC (ISP network)', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Find the real fault from OLT alarms, tickets, customer messages; changes with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => IspnocScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.shield_rounded, color: C.accent),
              title: Text('${app.aName} · Cyber suraksha', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Filter alert noise, suspicious mails / links, threats to your domain, incident notes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CyberScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.rocket_launch_rounded, color: C.accent),
              title: Text('${app.aName} · DevOps', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Explain builds and logs, scripts, monitoring; deploy on your tap'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DevopsScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.menu_book_rounded, color: C.accent),
              title: Text('${app.aName} · Technical writer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Manuals, quick starts, API docs, release notes; steps with screenshots'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DocwriterScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.verified_user_outlined, color: C.accent),
              title: Text('${app.aName} · App reviewer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Security of your app / code / website and Play policy checks, a fix list'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppReviewScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.route_rounded, color: C.accent),
              title: Text('${app.aName} · Product manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Feedback se roadmap, specs, release notes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProductScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.route_outlined, color: C.accent),
              title: Text('${app.aName} · Logistics', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Shipments, LR / challan, e-way bills, tracking, customer updates'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LogisticsScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.local_shipping_rounded, color: C.accent),
              title: Text('${app.aName} · Fleet manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Vehicles, papers, diesel, service, trips and loads'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FleetScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.warehouse_rounded, color: C.accent),
              title: Text('${app.aName} · Godown', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Bin-wise stock, goods received, pick lists, counts; changes with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => WarehouseScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.inventory_2_rounded, color: C.accent),
              title: Text('${app.aName} · Courier desk', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Book pickups (on your tap), where is the parcel, NDR, COD matching, return labels'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CourierScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.luggage_rounded, color: C.accent),
              title: Text('${app.aName} · Travel agent', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Trip plans, train / flight / hotel comparison, papers, Tatkal reminders; bookings with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TravelScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.badge_rounded, color: C.accent),
              title: Text('${app.aName} · Driver coordinator', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Duty, trip sheets, licence reminders, attendance'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DriversScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.directions_boat_rounded, color: C.accent),
              title: Text('${app.aName} · Import & customs', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Import papers, HS code checks, clearance and demurrage accounts; filing with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomsScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.home_work_rounded, color: C.accent),
              title: Text('${app.aName} · Real estate agent', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Listings, customers, site visits, deal papers, commission'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PropagentScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.house_rounded, color: C.accent),
              title: Text('${app.aName} · Property manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Kirayedar, kiraya, deposit, agreement, repair, move-out'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => RentdeskScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.construction_rounded, color: C.accent),
              title: Text('${app.aName} · Site supervisor', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Daily work, attendance, materials, safety, cube tests, snags, DPR'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SitesupScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.chair_rounded, color: C.accent),
              title: Text('${app.aName} · Interior designer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Brief, measurements, moodboard, BOQ quote, vendor orders, snags, handover'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InteriorScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.architecture_rounded, color: C.accent),
              title: Text('${app.aName} · Architect\'s assistant', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Project files, FSI checks, drawing register, approvals, RFI, fee invoices'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArchassistScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.apartment_rounded, color: C.accent),
              title: Text('${app.aName} · Society manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Flats, maintenance bill, baaki, shikayat, AGM / notice, vendor, gate'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SocietyScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.gavel_rounded, color: C.accent),
              title: Text('${app.aName} · Lawyer\'s junior', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Court diary, dates, cause lists, limitation, drafts, fee accounts'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VakilScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.menu_book_rounded, color: C.accent),
              title: Text('${app.aName} · Legal researcher', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Acts and judgments from official sources, a link for every point; IPC to BNS table'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LegalresScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.school_rounded, color: C.accent),
              title: Text('${app.aName} · Curriculum & exam designer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Question bank, board pattern ka paper + answer key, year / lesson plan, rubric'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShikshaScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.psychology_rounded, color: C.accent),
              title: Text('${app.aName} · Personal tutor', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Doubts solved with hints, practice + revision, English practice, weekly report'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GuruScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.fact_check_rounded, color: C.accent),
              title: Text('${app.aName} · School office', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Attendance, copy / OMR / Forms grading, timetable, report cards'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DaftarScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.science_rounded, color: C.accent),
              title: Text('${app.aName} · Research assistant', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Papers (OpenAlex / Crossref / arXiv / PubMed), review matrix, gaps, references'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShodhScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.biotech_rounded, color: C.accent),
              title: Text('${app.aName} · Prayogshala (3D labs)', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Real practicals in 3D: pendulum, lens, Ohm, meter bridge… knobs, meters, table'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PrayogScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.fact_check_rounded, color: C.accent),
              title: Text('${app.aName} · Compliance officer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('GST, TDS, PF, licence and pollution dates; evidence; monthly certificate'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ComplianceScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.description_rounded, color: C.accent),
              title: Text('${app.aName} · Contract manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Read contracts, risks, redlines, renewal register; sending / e-sign / e-stamp with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ContractsScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.business_center_rounded, color: C.accent),
              title: Text('${app.aName} · Company secretary', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('MCA form dates, Board / AGM notices + minutes, registers'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CosecScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.approval_rounded, color: C.accent),
              title: Text('${app.aName} · Notary desk', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Affidavit, POA, NOC drafts, stamps, register, receipts, apostille'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotaryScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.manage_search_rounded, color: C.accent),
              title: Text('${app.aName} · PI desk', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Business checks, paper checks, fraud evidence (no one is watched)'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PideskScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.shield_rounded, color: C.accent),
              title: Text('${app.aName} · Data protection officer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('DPDP: data register, privacy notice, consent, requests in 90 days, breach in 72 hours'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DpoScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.hotel_rounded, color: C.accent),
              title: Text('${app.aName} · Front office', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Hotel booking, check-in / out, rooms, bills, Form C'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FrontofficeScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.celebration_rounded, color: C.accent),
              title: Text('${app.aName} · Event planner', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Event file, vendor quotes, budget, booking, mehmaan + RSVP, run of show, report'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EventplanScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.favorite_rounded, color: C.accent),
              title: Text('${app.aName} · Wedding planner', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Functions, muhurat (panditji ka), mehmaan + RSVP, rooms, vendors, budget, shagun'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShaadiScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.tour_rounded, color: C.accent),
              title: Text('${app.aName} · Tour guide', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Tours, bookings, group files, day plans, safety, headcount, licences; confirmed bookings with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TourguideScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.cottage_rounded, color: C.accent),
              title: Text('${app.aName} · Homestay host', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Rooms, booking calendar, OTA mail, guests, Form C, cleaning, accounts'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HomestayScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.celebration_rounded, color: C.accent),
              title: Text('${app.aName} · Banquet sales', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Enquiry, khaali tareekh, hold, menu, quote, advance, BEO, bill'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BanquetScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.movie_creation_rounded, color: C.accent),
              title: Text('${app.aName} · Video editor desk', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Client, brief, versions, timecode notes, rounds, licence, quote, invoice, delivery'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EditdeskScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.movie_filter_rounded, color: C.accent),
              title: Text('${app.aName} · Motion designer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Client brand kit, storyboard, render, change rounds, licence, handover, bill'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MotiondeskScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.theaters_rounded, color: C.accent),
              title: Text('${app.aName} · AI film producer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Script, shots, permissions, studio budget, rights, release checklist'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FilmdeskScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.newspaper_rounded, color: C.accent),
              title: Text('${app.aName} · Journalist', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Story, source (identity sealed), fact check, right of reply, corrections, complaints'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PatrakarScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.photo_camera_rounded, color: C.accent),
              title: Text('${app.aName} · Photographer\'s assistant', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Shoot booking, shot list, gear, release, culling, edits, quote, gallery'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhotoassistScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.brush_rounded, color: C.accent),
              title: Text('${app.aName} · Graphic designer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Client brief, proof, revision rounds, print checks, files, invoice'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GraphicScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.mic_external_on_rounded, color: C.accent),
              title: Text('${app.aName} · Artist manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Roster, gig, hold, contract, invoice, royalty, release, payout'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArtistmgrScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.menu_book_rounded, color: C.accent),
              title: Text('${app.aName} · Author & editor', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Chapters, edit suggestions, style sheet, permissions, ISBN, pitch, royalty'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => KitabScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.podcasts_rounded, color: C.accent),
              title: Text('${app.aName} · Podcast producer', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Episode, guest release, transcript, show notes, sponsor #Ad, feed'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PodcastScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.campaign_rounded, color: C.accent),
              title: Text('${app.aName} · Influencer manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Creators, rate card, brand deals, #ad checks, invoice, report'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InfluencerScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.fact_check_rounded, color: C.accent),
              title: const Text("Auditor's assistant", style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('TB + day book checks, materiality, samples, confirmations, working papers: ${app.aName} does it, the opinion and signature are yours'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AuditScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.query_stats_rounded, color: C.accent),
              title: const Text('Financial analyst', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Profit from Tally + bank, ratios, days of cash, collections, MSME, loans, advance tax: ${app.aName} will explain'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FinanceScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.payments_rounded, color: C.accent),
              title: const Text('Payroll officer', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Monthly salary, PF / ESIC / PT / TDS, payslips, bank file: ${app.aName} prepares it, you make the payment'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PayrollScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.receipt_long_rounded, color: C.accent),
              title: const Text('GST sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Check every client\'s bills, GSTR-1 / 3B, 2B matching, due dates, notices: ${app.aName} does it, filing with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.account_balance_wallet_rounded, color: C.accent),
              title: const Text('AI ka kharcha', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(app.usage == null
                  ? 'Chat, call, website, video: what costs how much, and the monthly limit'
                  : 'This month ₹${((app.usage!['spent_inr'] as num?) ?? 0).round()}'
                      '${((app.usage!['limit_inr'] as num?) ?? 0) > 0 ? ' / ₹${((app.usage!['limit_inr'] as num?) ?? 0).round()} seema' : ''}'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => KharchaScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.fingerprint_rounded, color: C.accent),
              title: const Text('Fingerprint approval', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Cards involving money can be approved only with your fingerprint (safe even if the app key is stolen)'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ApproveKeyScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.healing_rounded, color: C.accent),
              title: const Text('Phone Doctor', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Phone slow, hot, network, battery, theft: ${app.aName} checks and guides you step by step'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhoneDocScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.phone_iphone_rounded, color: C.accent),
              title: const Text('Mobile dukaan sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Repair jobs + photos, warranty, ready-for-pickup messages, recharge register: ${app.aName} will handle it'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MShopScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.local_cafe_rounded, color: C.accent),
              title: const Text('Chai stall sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Daily UPI sales, the best hour, tomorrow\'s milk-sugar order: ${app.aName} will handle it'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ChaiScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.content_cut_rounded, color: C.accent),
              title: const Text('Darzi sahayak', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Tailoring orders, each customer\'s measurements, trial / delivery, prices: ${app.aName} will handle it'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DarziScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.business_center_rounded, color: C.accent),
              title: Text('${app.aName} · Office manager', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Supplies, repairs, renewals, team deadlines, petty cash, weekly note; spending with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => OfficeScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.edit_document, color: C.accent),
              title: Text('${app.aName} · Typist and translator', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Speak, and the letter is ready; Hindi / Marathi / English translation, grammar, Kruti Dev; signing with your yes'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LekhakScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.shopping_bag_rounded, color: C.accent),
              title: const Text('Place orders', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Amazon, Flipkart, Blinkit, Zepto, Swiggy, Zomato, IRCTC...: ${app.aName} does it all, you pay'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShopScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.auto_awesome_rounded, color: C.accentSoft),
              title: const Text('Learned tasks', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('How ${app.aName} did long tasks: view, change, turn off'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProceduresScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.record_voice_over_rounded, color: C.ok),
              title: const Text('Voice ID', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('${app.aName} can tell who is speaking by voice: you, Mom, Dad…'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VoiceIdScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.hearing_rounded, color: C.ok),
              title: Text('What ${app.aName} has learned', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Your language, speed, how long you pause, your words, what was misheard'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VoiceLearnedScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.record_voice_over_rounded, color: C.accentSoft),
              title: const Text('Call ki awaaz', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Gemini voice or Real voice (OpenAI) - and this month\'s cost'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VoiceEngineScreen(app: app))),
            ),
            ListTile(                                  // v0.396 CONNECT: the only door an enterprise credential has
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.hub_rounded, color: C.accentSoft),
              title: const Text('Connect your systems', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('ERP / CRM address and key - the key never goes into the chat'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EnterpriseScreen(app: app))),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.graphic_eq_rounded, color: C.accent),
              title: const Text('Call quality', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Numbers for every call, which calls were good / bad, and your listening test'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CallQualityScreen(app: app))),
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
          subtitle: const Text('AI video without shooting: ads, greetings, product reels — your yes for every cost'),
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
          subtitle: const Text('Online forms, government portals, downloads, status checks — you do the OTP / submit / payment'),
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
          subtitle: const Text('Give raw video: it makes a reel / Short / Status / YouTube video, checks it itself and hands it over'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VideoEditorScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.phone_android_rounded, color: C.accent),
          title: Text('${app.aName} on the phone', style: const TextStyle(fontWeight: FontWeight.w700)),
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
          title: const Text('My PC', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Connect YOUR personal PC: files, printing and Tally from the phone'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PcScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.dns_rounded, color: C.accent),
          title: const Text('Hoola ka PC', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('HOOLA\'s own computer (separate section): in its own container, always on — Chrome, files, software'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaPcScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.menu_book_rounded, color: C.teal),
          title: const Text('Hoola Notebook', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Like NotebookLM: chat with sources, audio / video overview, slides, mind map, quiz, 39 languages'),
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
          subtitle: const Text('Find videos, video summaries, my channel\'s views / analytics / comments'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => YouTubeScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.shield_rounded, color: C.ok),
          title: const Text('App Check', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Check an APK / EXE before installing: is it a fraud app?'),
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
          subtitle: const Text('Find and read files, send to phone / PC / email, upload, share'),
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
          subtitle: const Text('Make forms and quizzes, summaries of responses, alerts on new responses'),
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
          subtitle: const Text('Presentations on any topic, deck summaries, PDF / PowerPoint'),
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
          subtitle: const Text('Pick photos and send them (email / Drive / PC) · upload and albums in Photos'),
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
          subtitle: const Text('Read Sheets, accounts, add rows, new sheets, Excel import / export'),
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
          subtitle: const Text('Link Google Calendar · meetings, Meet links, free time, reminders before meetings'),
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
          subtitle: const Text('Connect Gmail, Outlook or any email · signature · daily inbox summary'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EmailScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.auto_awesome_mosaic_rounded, color: C.accent),
          title: const Text('My Artifacts', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Apps, trackers, charts and documents made by Hoola'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArtifactsScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.home_rounded, color: C.accentSoft),
          title: const Text('Home', style: TextStyle(fontWeight: FontWeight.w700)),
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
          subtitle: const Text('Bills, kirana, UPI, cab, Swiggy/Zomato · spending limit'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BazarScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(children: [
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'Naam')),
          TextField(controller: _city, decoration: const InputDecoration(labelText: 'City (for the weather)')),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Daily morning briefing'),
            subtitle: Text(_briefing == null ? 'Band' : 'Every day at $_briefing: weather, reminders, lists'),
            value: _briefing != null,
            onChanged: (on) => on ? _pickBriefing() : setState(() => _briefing = null),
          ),
          if (_briefing != null) Align(alignment: Alignment.centerLeft, child: TextButton(onPressed: _pickBriefing, child: const Text('Change time'))),
          const SizedBox(height: 6),
          GradientButton(label: 'Save', height: 48, onTap: _save),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Language and voice', style: TextStyle(fontWeight: FontWeight.w700)),
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
            Text('${app.aName}\'s voice (Talk tab)', style: const TextStyle(fontWeight: FontWeight.w700)),
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
            title: const Text('If I ask by voice, Hoola answers by voice'),
            value: app.speakReplies,
            onChanged: (v) async {
              await app.saveSettings(speak: v);
              setState(() {});
            },
          ),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(   // v0.616 BAHAR SE BAAT: her Hoola from WhatsApp / Telegram / Slack / Teams
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.forum_outlined, color: C.teal),
          title: const Text('Talk from outside', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Talk to your Hoola from WhatsApp, Telegram, Slack, Teams - only you'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BaharScreen(app: app))),
        ),
      ),
      const SizedBox(height: 12),
      Glass(   // v0.250 Claude-style memory: her page + switches
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.psychology_outlined, color: C.teal),
          title: const Text('Hoola\'s memory · About me', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('What Hoola knows about you - read it, correct it; memory switches'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MemoryPageScreen(app: app))),
        ),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('What Hoola remembers', style: TextStyle(fontWeight: FontWeight.w700)),
          const Text('Pin = always kept in mind (small things). Other memories are found by meaning; firm facts '
              'are also remembered from your conversations (remove any that are wrong).',
              style: TextStyle(color: C.faint, fontSize: 12)),
          if (_facts.isEmpty) const Padding(padding: EdgeInsets.only(top: 6), child: Text('Nothing yet. Say: "Remember that Mom\'s birthday is 5 June".', style: TextStyle(color: C.muted))),
          for (final f in _facts)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: IconButton(
                tooltip: f['pinned'] == true ? 'Pin hatao' : 'Always remembered (pin)',
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
              subtitle: f['auto'] == true
                  ? const Text('Hoola remembered this from conversations', style: TextStyle(color: C.faint, fontSize: 11))
                  : null,
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
          const Text('Account', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(app.dryRun ? 'WhatsApp: test mode' : 'WhatsApp: live', style: const TextStyle(color: C.muted)),
          TextButton(onPressed: () async {
            await app.signOut();
            if (!mounted) return;
            widget.onReset();
          }, child: const Text('Logout')),
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
        ? 'Off: when the app is closed, notifications and phone tasks stop'
        : !app.backgroundRunning
            ? 'Starting…'
            : st == 'connected'
                ? 'On · Hoola is on duty'
                : st.isEmpty
                    ? 'On'
                    : 'On · $st';
    Widget fix(String title, String sub, String button, Future<void> Function() onTap) => Container(
          margin: const EdgeInsets.only(top: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0x2EF4A24C), borderRadius: BorderRadius.circular(16)),
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
          title: const Text('Work in the background', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(statusText, style: TextStyle(color: on && app.backgroundRunning ? C.ok : C.muted, fontSize: 12.5)),
          value: on,
          onChanged: (v) => app.setBackground(v),
        ),
        const Text('Even when the app is closed: Hoola\'s replies come as notifications, alarms and timers ring, calendar entries are made, and Hoola\'s daily tasks keep running.',
            style: TextStyle(fontSize: 12.5, color: C.muted)),
        if (on && app.batteryOptimized)
          fix('Battery saver can stop Hoola', 'Set Hoola to "Unrestricted / Don\'t optimize"', 'Fix it', Native.askBattery),
        ValueListenableBuilder<Map<String, dynamic>?>(
          valueListenable: HoolaKeepAlive.last,
          builder: (context, r, _) {
            final n = (r?['problems'] as List? ?? const []).length;
            final kills = ((r?['counts'] as Map?)?['oem_kill'] as num? ?? 0).toInt();
            return fix(
                'Keep ${app.aName} from being stopped',
                r == null
                    ? 'Xiaomi / Oppo / Realme / Vivo / Samsung: fix the settings once'
                    : n == 0
                        ? 'All good · see the checklist'
                        : '$n things to fix${kills > 0 ? ' · the phone stopped Hoola $kills times in 7 days' : ''}',
                n == 0 && r != null ? 'View' : 'Fix it',
                () => HoolaKeepAlive.open(context, app));
          },
        ),
        if (!app.exactAlarms)
          fix('So alarms ring on time', 'Give the "Alarms & reminders" permission', 'Allow', () async {
            await Native.askExactAlarms();
            await Future.delayed(const Duration(seconds: 2));
            await app.refreshBackgroundInfo();
          }),
        if (on && !app.hasCalendar)
          fix('Calendar permission', 'So Hoola can save meetings straight into the calendar', 'Allow', () async {
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
        setState(() => _status = 'Give the microphone permission, then start again');
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
                : 'Even with the phone locked or the screen off, just say “Hey Santosh”. Your voice is recognised on the phone itself.'),
            value: _on,
            onChanged: _toggle,
          ),
          const Text('Only Talk opens on the lock screen. The phone must be unlocked for payments.',
              style: TextStyle(fontSize: 12, color: C.muted, height: 1.4)),
        ]),
      );
}
