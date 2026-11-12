// v0.867 R7 YOUR AI TEAM (docs/HOOLA_APP_REDESIGN_PLAN.md R7): every desk and tool that sat on the old Main page,
// grouped by kind of work, in ONE searchable list in the new design. GENERATED from the old page's own rows (titles,
// lines and the screen each opens), so nothing is lost; test/hoola_settings_test.dart checks every old row still has
// a way in. The desks open in their old frame until R8 rebuilds them.
// ignore_for_file: prefer_const_constructors
import 'package:flutter/material.dart';

import '../../state.dart';
import '../ads_screen.dart';
import '../aftersales_screen.dart';
import '../app_design_screen.dart';
import '../appcheck_screen.dart';
import '../appreview_screen.dart';
import '../archassist_screen.dart';
import '../artifacts_screen.dart';
import '../artistmgr_screen.dart';
import '../audit_screen.dart';
import '../banquet_screen.dart';
import '../bazar_screen.dart';
import '../blender_screen.dart';
import '../brand_screen.dart';
import '../calendar_screen.dart';
import '../callcentre_screen.dart';
import '../chai_screen.dart';
import '../compliance_screen.dart';
import '../contracts_screen.dart';
import '../cosec_screen.dart';
import '../courier_screen.dart';
import '../customs_screen.dart';
import '../cyber_screen.dart';
import '../daftar_screen.dart';
import '../darzi_screen.dart';
import '../deal_screen.dart';
import '../devops_screen.dart';
import '../devsahayak_screen.dart';
import '../docwriter_screen.dart';
import '../dosti_screen.dart';
import '../dpo_screen.dart';
import '../drive_screen.dart';
import '../drivers_screen.dart';
import '../editdesk_screen.dart';
import '../email_screen.dart';
import '../employee_screen.dart';
import '../employees_screen.dart';
import '../eventplan_screen.dart';
import '../feedback_screen.dart';
import '../filmdesk_screen.dart';
import '../finance_screen.dart';
import '../fleet_screen.dart';
import '../forms_screen.dart';
import '../franchise_screen.dart';
import '../frontoffice_screen.dart';
import '../graphic_screen.dart';
import '../gst_screen.dart';
import '../guru_screen.dart';
import '../gyaan_screen.dart';
import '../handoff_screen.dart';
import '../helpdesk_screen.dart';
import '../home_devices_screen.dart';
import '../homestay_screen.dart';
import '../hoola_pc_screen.dart';
import '../influencer_screen.dart';
import '../insurance_screen.dart';
import '../interior_screen.dart';
import '../ispnoc_screen.dart';
import '../itadmin_screen.dart';
import '../jaanch_screen.dart';
import '../kalam_screen.dart';
import '../kitab_screen.dart';
import '../legalres_screen.dart';
import '../lekhak_screen.dart';
import '../logistics_screen.dart';
import '../motiondesk_screen.dart';
import '../mshop_screen.dart';
import '../niryat_screen.dart';
import '../notary_screen.dart';
import '../notebook_screen.dart';
import '../office_screen.dart';
import '../operator_screen.dart';
import '../patrakar_screen.dart';
import '../payroll_screen.dart';
import '../pc_screen.dart';
import '../phonedoc_screen.dart';
import '../photoassist_screen.dart';
import '../photos_screen.dart';
import '../pidesk_screen.dart';
import '../podcast_screen.dart';
import '../postgres_screen.dart';
import '../prayog_screen.dart';
import '../product_screen.dart';
import '../propagent_screen.dart';
import '../qa_screen.dart';
import '../rentdesk_screen.dart';
import '../samudaay_screen.dart';
import '../seo_screen.dart';
import '../seva_screen.dart';
import '../shaadi_screen.dart';
import '../sheets_screen.dart';
import '../shikayat_screen.dart';
import '../shiksha_screen.dart';
import '../shodh_screen.dart';
import '../shop_screen.dart';
import '../site_screen.dart';
import '../sitesup_screen.dart';
import '../slides_screen.dart';
import '../society_screen.dart';
import '../studio/studio_home.dart';
import '../telecall_screen.dart';
import '../theka_screen.dart';
import '../thok_screen.dart';
import '../tourguide_screen.dart';
import '../travel_screen.dart';
import '../vakil_screen.dart';
import '../video_editor.dart';
import '../wapsi_screen.dart';
import '../warehouse_screen.dart';
import '../youtube_screen.dart';

/// One desk or tool in the team list.
class HoolaTeamEntry {
  const HoolaTeamEntry(this.group, this.icon, this.title, this.sub, this.open);
  final String group;
  final IconData icon;
  final String title, sub;
  final Widget Function(Santosh app) open;
}

/// The order of the groups on the team screen.
const hoolaTeamGroups = ["Hire and manage", "Business and sales", "Finance and accounts", "Customer service", "Software and IT", "Logistics and travel", "Property and construction", "Legal and compliance", "Education and research", "Hospitality and events", "Media and creative", "Tools and apps"];

/// Every desk and tool, built with her avatar's name in the lines.
List<HoolaTeamEntry> hoolaTeamEntries(Santosh app) => [
    HoolaTeamEntry("Hire and manage", Icons.groups_rounded, 'Hire AI employees',
        'SEO Specialist works 24/7 on your website and Google; its desk appears once you hire it',
        (a) => EmployeesScreen(app: a)),
    HoolaTeamEntry("Hire and manage", Icons.work_rounded, 'Your business employee',
        '${app.aName} works in your business: team, trust, accounts, daily report',
        (a) => EmployeeScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.engineering_rounded, 'Contractor\'s assistant',
        'Tender dates, BOQ, measurements, RA bills and deductions, petty contractors, site diary, EOT: ${app.aName} does it, bills go out with your yes',
        (a) => ThekaScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.storefront_rounded, 'Franchise assistant',
        'Sales and profit of each outlet, royalty statements, licences, agreement dates, SOP audits: ${app.aName} does it, reports go out with your yes',
        (a) => FranchiseScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.public_rounded, 'Export assistant',
        'Buyers, PI, invoice + packing list, papers, when money comes after the shipping bill, RoDTEP: ${app.aName} does it, sending needs your yes',
        (a) => NiryatScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.warehouse_rounded, 'Wholesale assistant',
        'GST bills from orders, credit and recovery, cheques, supplier bills, what to order: ${app.aName} does it, bills go out with your yes',
        (a) => ThokScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.travel_explore_rounded, 'SEO specialist',
        'Website checks, speed, Google Search Console, page plans, Google profile posts + review replies: ${app.aName} does it, you publish',
        (a) => SeoScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.health_and_safety_rounded, 'Insurance assistant',
        'Policy book, premium reminders, cover gaps, quote comparison, claims: ${app.aName} does it, the customer pays the insurer directly',
        (a) => InsuranceScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.headset_mic_rounded, 'Telecaller',
        'Whom to call and when and why, a script for each customer, a log after the call; you make the calls',
        (a) => TelecallScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.edit_note_rounded, 'Content writer',
        'Blog, product page, email in your voice; every claim checked; publish with your yes',
        (a) => KalamScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.campaign_rounded, 'Performance marketer',
        'Find wasted money from the ad report, budget changes with reasons (with your yes), test new ad copy',
        (a) => AdsScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.web_rounded, 'Website',
        'Say two words: plan, 3 looks, motion graphics, watch each part being built, checks, preview',
        (a) => SiteScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.phone_android_rounded, 'App designer',
        'Design every screen of the Android + iPhone app first: 3 looks, try it by tapping, then "Confirm design"',
        (a) => AppDesignScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.palette_rounded, 'Brand designer',
        'Posters in your logo and colours, sizes for every platform, festival posts; final with your yes',
        (a) => BrandScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.view_in_ar_rounded, '3D Studio',
        'Real Blender: product mockups, layouts, gifts, 3D prints; renders, 360° video, GLB / STL',
        (a) => Blender3dScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.phone_iphone_rounded, 'Mobile shop assistant',
        'Repair jobs + photos, warranty, ready-for-pickup messages, recharge register: ${app.aName} will handle it',
        (a) => MShopScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.local_cafe_rounded, 'Tea stall assistant',
        'Daily UPI sales, the best hour, tomorrow\'s milk-sugar order: ${app.aName} will handle it',
        (a) => ChaiScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.content_cut_rounded, 'Tailor\'s assistant',
        'Tailoring orders, each customer\'s measurements, trial / delivery, prices: ${app.aName} will handle it',
        (a) => DarziScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.business_center_rounded, 'Office manager',
        'Supplies, repairs, renewals, team deadlines, petty cash, weekly note; spending with your yes',
        (a) => OfficeScreen(app: a)),
    HoolaTeamEntry("Business and sales", Icons.edit_document, 'Typist and translator',
        'Speak, and the letter is ready; Hindi / Marathi / English translation, grammar, Kruti Dev; signing with your yes',
        (a) => LekhakScreen(app: a)),
    HoolaTeamEntry("Finance and accounts", Icons.fact_check_rounded, "Auditor's assistant",
        'TB + day book checks, materiality, samples, confirmations, working papers: ${app.aName} does it, the opinion and signature are yours',
        (a) => AuditScreen(app: a)),
    HoolaTeamEntry("Finance and accounts", Icons.query_stats_rounded, 'Financial analyst',
        'Profit from Tally + bank, ratios, days of cash, collections, MSME, loans, advance tax: ${app.aName} will explain',
        (a) => FinanceScreen(app: a)),
    HoolaTeamEntry("Finance and accounts", Icons.payments_rounded, 'Payroll officer',
        'Monthly salary, PF / ESIC / PT / TDS, payslips, bank file: ${app.aName} prepares it, you make the payment',
        (a) => PayrollScreen(app: a)),
    HoolaTeamEntry("Finance and accounts", Icons.receipt_long_rounded, 'GST assistant',
        'Check every client\'s bills, GSTR-1 / 3B, 2B matching, due dates, notices: ${app.aName} does it, filing with your yes',
        (a) => GstScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.support_agent_rounded, 'Customer support',
        'Instant answers from knowledge, complaints + deadlines, refunds with your yes',
        (a) => SevaScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.computer_rounded, 'IT Helpdesk',
        'Computer, printer and internet problems step by step; technician; phishing checks',
        (a) => HelpdeskScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.report_problem_rounded, 'Complaints assistant',
        'Record complaints, evidence, deadlines, compensation with your yes',
        (a) => ShikayatScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.home_repair_service_rounded, 'After-sales service',
        'Service due, technician visit, report, AMC, warranty claim',
        (a) => AftersalesScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.reviews_rounded, 'Feedback assistant',
        'Reviews, surveys, what to fix first',
        (a) => FeedbackScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.assignment_return_rounded, 'Returns desk',
        'Returns helper: returns, pickups, QC, refunds (with your yes)',
        (a) => WapsiScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.groups_2_rounded, 'Community manager',
        'Welcome in the group, FAQ answers, scam / abuse alerts',
        (a) => SamudaayScreen(app: a)),
    HoolaTeamEntry("Customer service", Icons.phone_in_talk_rounded, 'Call centre',
        'Hoola answers the business phone: only from your script, can connect to a human, call-back',
        (a) => CallCentreScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.terminal_rounded, 'Developer',
        'Write code, bug-fix PRs, tests, reviews; merge / deploy with your yes',
        (a) => DevsahayakScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.bug_report_rounded, 'App tester (QA)',
        'Test cases, bugs, re-checks after fixes, is the release ready?',
        (a) => QaScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.admin_panel_settings_rounded, 'IT Admin',
        'Licence, renewal, access, joiner-leaver, staff guides',
        (a) => ItadminScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.lan_rounded, 'NOC (ISP network)',
        'Find the real fault from OLT alarms, tickets, customer messages; changes with your yes',
        (a) => IspnocScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.shield_rounded, 'Cyber security',
        'Filter alert noise, suspicious mails / links, threats to your domain, incident notes',
        (a) => CyberScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.rocket_launch_rounded, 'DevOps',
        'Explain builds and logs, scripts, monitoring; deploy on your tap',
        (a) => DevopsScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.menu_book_rounded, 'Technical writer',
        'Manuals, quick starts, API docs, release notes; steps with screenshots',
        (a) => DocwriterScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.verified_user_outlined, 'App reviewer',
        'Security of your app / code / website and Play policy checks, a fix list',
        (a) => AppReviewScreen(app: a)),
    HoolaTeamEntry("Software and IT", Icons.route_rounded, 'Product manager',
        'Feedback se roadmap, specs, release notes',
        (a) => ProductScreen(app: a)),
    HoolaTeamEntry("Logistics and travel", Icons.route_outlined, 'Logistics',
        'Shipments, LR / challan, e-way bills, tracking, customer updates',
        (a) => LogisticsScreen(app: a)),
    HoolaTeamEntry("Logistics and travel", Icons.local_shipping_rounded, 'Fleet manager',
        'Vehicles, papers, diesel, service, trips and loads',
        (a) => FleetScreen(app: a)),
    HoolaTeamEntry("Logistics and travel", Icons.warehouse_rounded, 'Warehouse',
        'Bin-wise stock, goods received, pick lists, counts; changes with your yes',
        (a) => WarehouseScreen(app: a)),
    HoolaTeamEntry("Logistics and travel", Icons.inventory_2_rounded, 'Courier desk',
        'Book pickups (on your tap), where is the parcel, NDR, COD matching, return labels',
        (a) => CourierScreen(app: a)),
    HoolaTeamEntry("Logistics and travel", Icons.luggage_rounded, 'Travel agent',
        'Trip plans, train / flight / hotel comparison, papers, Tatkal reminders; bookings with your yes',
        (a) => TravelScreen(app: a)),
    HoolaTeamEntry("Logistics and travel", Icons.badge_rounded, 'Driver coordinator',
        'Duty, trip sheets, licence reminders, attendance',
        (a) => DriversScreen(app: a)),
    HoolaTeamEntry("Logistics and travel", Icons.directions_boat_rounded, 'Import & customs',
        'Import papers, HS code checks, clearance and demurrage accounts; filing with your yes',
        (a) => CustomsScreen(app: a)),
    HoolaTeamEntry("Property and construction", Icons.home_work_rounded, 'Real estate agent',
        'Listings, customers, site visits, deal papers, commission',
        (a) => PropagentScreen(app: a)),
    HoolaTeamEntry("Property and construction", Icons.house_rounded, 'Property manager',
        'Kirayedar, kiraya, deposit, agreement, repair, move-out',
        (a) => RentdeskScreen(app: a)),
    HoolaTeamEntry("Property and construction", Icons.construction_rounded, 'Site supervisor',
        'Daily work, attendance, materials, safety, cube tests, snags, DPR',
        (a) => SitesupScreen(app: a)),
    HoolaTeamEntry("Property and construction", Icons.chair_rounded, 'Interior designer',
        'Brief, measurements, moodboard, BOQ quote, vendor orders, snags, handover',
        (a) => InteriorScreen(app: a)),
    HoolaTeamEntry("Property and construction", Icons.architecture_rounded, 'Architect\'s assistant',
        'Project files, FSI checks, drawing register, approvals, RFI, fee invoices',
        (a) => ArchassistScreen(app: a)),
    HoolaTeamEntry("Property and construction", Icons.apartment_rounded, 'Society manager',
        'Flats, maintenance bill, baaki, shikayat, AGM / notice, vendor, gate',
        (a) => SocietyScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.gavel_rounded, 'Lawyer\'s junior',
        'Court diary, dates, cause lists, limitation, drafts, fee accounts',
        (a) => VakilScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.menu_book_rounded, 'Legal researcher',
        'Acts and judgments from official sources, a link for every point; IPC to BNS table',
        (a) => LegalresScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.fact_check_rounded, 'Compliance officer',
        'GST, TDS, PF, licence and pollution dates; evidence; monthly certificate',
        (a) => ComplianceScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.description_rounded, 'Contract manager',
        'Read contracts, risks, redlines, renewal register; sending / e-sign / e-stamp with your yes',
        (a) => ContractsScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.business_center_rounded, 'Company secretary',
        'MCA form dates, Board / AGM notices + minutes, registers',
        (a) => CosecScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.approval_rounded, 'Notary desk',
        'Affidavit, POA, NOC drafts, stamps, register, receipts, apostille',
        (a) => NotaryScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.manage_search_rounded, 'PI desk',
        'Business checks, paper checks, fraud evidence (no one is watched)',
        (a) => PideskScreen(app: a)),
    HoolaTeamEntry("Legal and compliance", Icons.shield_rounded, 'Data protection officer',
        'DPDP: data register, privacy notice, consent, requests in 90 days, breach in 72 hours',
        (a) => DpoScreen(app: a)),
    HoolaTeamEntry("Education and research", Icons.school_rounded, 'Curriculum & exam designer',
        'Question bank, board pattern ka paper + answer key, year / lesson plan, rubric',
        (a) => ShikshaScreen(app: a)),
    HoolaTeamEntry("Education and research", Icons.psychology_rounded, 'Personal tutor',
        'Doubts solved with hints, practice + revision, English practice, weekly report',
        (a) => GuruScreen(app: a)),
    HoolaTeamEntry("Education and research", Icons.fact_check_rounded, 'School office',
        'Attendance, copy / OMR / Forms grading, timetable, report cards',
        (a) => DaftarScreen(app: a)),
    HoolaTeamEntry("Education and research", Icons.science_rounded, 'Research assistant',
        'Papers (OpenAlex / Crossref / arXiv / PubMed), review matrix, gaps, references',
        (a) => ShodhScreen(app: a)),
    HoolaTeamEntry("Education and research", Icons.biotech_rounded, '3D science labs',
        'Real practicals in 3D: pendulum, lens, Ohm, meter bridge… knobs, meters, table',
        (a) => PrayogScreen(app: a)),
    HoolaTeamEntry("Hospitality and events", Icons.hotel_rounded, 'Front office',
        'Hotel booking, check-in / out, rooms, bills, Form C',
        (a) => FrontofficeScreen(app: a)),
    HoolaTeamEntry("Hospitality and events", Icons.celebration_rounded, 'Event planner',
        'Event file, vendor quotes, budget, booking, mehmaan + RSVP, run of show, report',
        (a) => EventplanScreen(app: a)),
    HoolaTeamEntry("Hospitality and events", Icons.favorite_rounded, 'Wedding planner',
        'Functions, muhurat (panditji ka), mehmaan + RSVP, rooms, vendors, budget, shagun',
        (a) => ShaadiScreen(app: a)),
    HoolaTeamEntry("Hospitality and events", Icons.tour_rounded, 'Tour guide',
        'Tours, bookings, group files, day plans, safety, headcount, licences; confirmed bookings with your yes',
        (a) => TourguideScreen(app: a)),
    HoolaTeamEntry("Hospitality and events", Icons.cottage_rounded, 'Homestay host',
        'Rooms, booking calendar, OTA mail, guests, Form C, cleaning, accounts',
        (a) => HomestayScreen(app: a)),
    HoolaTeamEntry("Hospitality and events", Icons.celebration_rounded, 'Banquet sales',
        'Enquiry, khaali tareekh, hold, menu, quote, advance, BEO, bill',
        (a) => BanquetScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.movie_creation_rounded, 'Video editor desk',
        'Client, brief, versions, timecode notes, rounds, licence, quote, invoice, delivery',
        (a) => EditdeskScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.movie_filter_rounded, 'Motion designer',
        'Client brand kit, storyboard, render, change rounds, licence, handover, bill',
        (a) => MotiondeskScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.theaters_rounded, 'AI film producer',
        'Script, shots, permissions, studio budget, rights, release checklist',
        (a) => FilmdeskScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.newspaper_rounded, 'Journalist',
        'Story, source (identity sealed), fact check, right of reply, corrections, complaints',
        (a) => PatrakarScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.photo_camera_rounded, 'Photographer\'s assistant',
        'Shoot booking, shot list, gear, release, culling, edits, quote, gallery',
        (a) => PhotoassistScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.brush_rounded, 'Graphic designer',
        'Client brief, proof, revision rounds, print checks, files, invoice',
        (a) => GraphicScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.mic_external_on_rounded, 'Artist manager',
        'Roster, gig, hold, contract, invoice, royalty, release, payout',
        (a) => ArtistmgrScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.menu_book_rounded, 'Author & editor',
        'Chapters, edit suggestions, style sheet, permissions, ISBN, pitch, royalty',
        (a) => KitabScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.podcasts_rounded, 'Podcast producer',
        'Episode, guest release, transcript, show notes, sponsor #Ad, feed',
        (a) => PodcastScreen(app: a)),
    HoolaTeamEntry("Media and creative", Icons.campaign_rounded, 'Influencer manager',
        'Creators, rate card, brand deals, #ad checks, invoice, report',
        (a) => InfluencerScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.auto_awesome_motion_rounded, 'Video Studio',
        'AI video without shooting: ads, greetings, product reels — your yes for every cost',
        (a) => StudioScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.movie_creation_rounded, 'Video Editor',
        'Give raw video: it makes a reel / Short / Status / YouTube video, checks it itself and hands it over',
        (a) => VideoEditorScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.computer_rounded, 'Computer Operator',
        'Online forms, government portals, downloads, status checks — you do the OTP / submit / payment',
        (a) => OperatorScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.menu_book_rounded, 'Notebook',
        'Like NotebookLM: chat with sources, audio / video overview, slides, mind map, quiz, 39 languages',
        (a) => NotebooksScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.auto_stories_rounded, '${app.aName}\'s knowledge',
        'Answers from your files, Drive and mail, with sources; it does not make up what it does not know',
        (a) => GyaanScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.shopping_bag_rounded, 'Place orders',
        'Amazon, Flipkart, Blinkit, Zepto, Swiggy, Zomato, IRCTC...: ${app.aName} does it all, you pay',
        (a) => ShopScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.shopping_bag_rounded, 'Buy and sell',
        'A list to a shop / wholesaler, the quote from their Hoola, your yes; your own stock and selling rules',
        (a) => DealsScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.home_rounded, 'Home',
        'AC, TV, speaker phone se · Samsung / LG / Bosch appliances',
        (a) => HomeDevicesScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.healing_rounded, 'Phone Doctor',
        'Phone slow, hot, network, battery, theft: ${app.aName} checks and guides you step by step',
        (a) => PhoneDocScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.shield_rounded, 'App Check',
        'Check an APK / EXE before installing: is it a fraud app?',
        (a) => AppCheckScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.health_and_safety_rounded, '${app.aName} Check',
        'Check every part now: what is broken, how to fix it, which website does not open from the server',
        (a) => JaanchScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.diversity_3_rounded, '${app.aName}\'s friends',
        'Talk work with friends\' avatars by itself, share your experience and skills; documents with your yes',
        (a) => DostiScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.verified_user_rounded, 'Consents, papers, outside agents',
        'Check bank data (AA) and health (ABHA) consents, DigiLocker, ONDC sheet, A2A agents: the decision is yours, ${app.aName} will explain',
        (a) => HandoffScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.storage_rounded, 'Postgres database',
        'Connect your database: Hoola reads it (read-only), changes only with your yes',
        (a) => PostgresScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.smart_display_rounded, 'YouTube',
        'Find videos, video summaries, my channel\'s views / analytics / comments',
        (a) => YouTubeScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.add_to_drive_rounded, 'Google Drive',
        'Find and read files, send to phone / PC / email, upload, share',
        (a) => DriveScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.table_chart_rounded, 'Google Sheets',
        'Read Sheets, accounts, add rows, new sheets, Excel import / export',
        (a) => SheetsScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.dynamic_form_rounded, 'Google Forms',
        'Make forms and quizzes, summaries of responses, alerts on new responses',
        (a) => FormsScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.slideshow_rounded, 'Google Slides',
        'Presentations on any topic, deck summaries, PDF / PowerPoint',
        (a) => SlidesScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.photo_library_rounded, 'Google Photos',
        'Pick photos and send them (email / Drive / PC) · upload and albums in Photos',
        (a) => PhotosScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.event_rounded, 'Calendar',
        'Link Google Calendar · meetings, Meet links, free time, reminders before meetings',
        (a) => CalendarScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.mail_rounded, 'Email',
        'Connect Gmail, Outlook or any email · signature · daily inbox summary',
        (a) => EmailScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.auto_awesome_mosaic_rounded, 'My Artifacts',
        'Apps, trackers, charts and documents made by Hoola',
        (a) => ArtifactsScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.power_rounded, 'Connectors · 700+ plugins',
        'Bills, kirana, UPI, cab, Swiggy/Zomato · spending limit',
        (a) => BazarScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.computer_rounded, 'My PC',
        'Connect YOUR personal PC: files, printing and Tally from the phone',
        (a) => PcScreen(app: a)),
    HoolaTeamEntry("Tools and apps", Icons.dns_rounded, 'Hoola\'s own PC',
        'HOOLA\'s own computer (separate section): in its own container, always on — Chrome, files, software',
        (a) => HoolaPcScreen(app: a)),
    ];
