/// v0.164.2 UI language tables for the chat section.
/// Keys are the original Hinglish strings; 'en' is the default UI language.
/// Other Indian languages fall back to English until their table is filled in.
/// Placeholders: {a} = avatar name, {x} = a runtime value passed by the caller.
const Map<String, Map<String, String>> uiStrings = {
  'en': {
    // ---- chat header / status / tooltips ----
    'Connect ho raha hai…': 'Connecting…',
    'Kaam kar raha hoon…': 'Working on it…',
    'Bolkar baat karein': 'Talk by voice',
    'Purani chats': 'Older chats',
    'Naya chat': 'New chat',
    'Purani baatein dikhao': 'Show older messages',
    'Aapki haan chahiye ({x})': 'Needs your OK ({x})',
    'Aapki haan chahiye · {x}': 'Needs your OK · {x}',
    'Aapki haan chahiye': 'Needs your OK',
    'Sab ho gaya ✓': 'All done ✓',
    'Aapki chats': 'Your chats',
    'Chat khojo…': 'Search chats…',
    'Mitt do': 'Clear',
    'Koi chat nahi mili': 'No chats found',
    'Abhi': 'Now',
    'abhi': 'just now',
    '{x} min pehle': '{x} min ago',
    '{x} ghante pehle': '{x} hrs ago',
    '{x} din pehle': '{x} days ago',
    '(dobara koshish ke liye tap kijiye)': '(tap to try again)',
    'Hoola ka dimaag server par connect nahi hai (ANTHROPIC_API_KEY).': "Hoola's brain is not connected on the server (ANTHROPIC_API_KEY).",
    // ---- v0.178 chat premium: day heads, reply bar, hero invitation ----
    'IS PAR JAWAB': 'REPLYING TO',
    'Reply hatao': 'Remove reply',
    'Reply bar mein upar dikhega': 'It waits in the reply bar above',
    'Kaise madad karoon?': 'How can I help?',
    'Boliye ya likhiye — dono chalega.': 'Speak it or type it — both work.',
    'Baat aapki — sirf aapke phone aur server par.': 'Your words stay yours — on your phone and server only.',
    'Doodh list mein daalo': 'Add milk to my list',
    // ---- composer / mic / attach ----
    '{a} se boliye…': 'Message {a}…',
    'Sun raha hoon…': 'Listening…',
    'Sahi hai? {x} second mein bhej rahe hain…': 'Looks right? Sending in {x}s…',
    'Ruk jao': 'Wait',
    'Photo, PDF, video ya koi bhi file': 'Photo, PDF, video or any file',
    'Speak to {a}': 'Speak to {a}',
    'Microphone permission chahiye. Phone settings mein Hoola ko mic ki permission dijiye.':
        'Mic permission needed. Please allow Hoola microphone access in phone settings.',
    'nahi le paye (25 MB se badi, 6 se zyada, ya padh nahi paye). Badi file Google Drive link se bhejiye.':
        "couldn't be added (over 25 MB, more than 6, or unreadable). For big files, send a Google Drive link.",
    'PDF / Document / Excel / koi bhi file': 'PDF / Document / Excel / any file',
    'File chun nahi paye:': 'Could not pick a file:',
    '{x} MB hai, 25 MB tak bhej sakte hain. Badi file Drive link se bhejiye.':
        '{x} MB — the limit is 25 MB. For big files, send a Drive link.',
    '{x} padh nahi paye. Phone mein download karke dobara chuniye.':
        "Couldn't read {x}. Download it on the phone and pick again.",
    // ---- scroll-down button ----
    'naye message, neeche jaiye': 'new messages, jump down',
    'Sabse neeche jaiye': 'Jump to latest',
    // ---- quick chips ----
    'Kal subah 7 baje yaad dilana': 'Remind me tomorrow at 7 am',
    'Aaj ka mausam': "Today's weather",
    'Meri shopping list': 'My shopping list',
    'Roz subah briefing bhejna': 'Send me a daily briefing',
    'Meri haan kahan ruki hai?': "What's waiting for my OK?",
    'Kal ka plan banao': "Plan tomorrow",
    // ---- email card ----
    'Email': 'Email',
    'Email · forward': 'Email · forward',
    'Cc': 'Cc',
    'Bcc': 'Bcc',
    'Email · jawab': 'Email · reply',
    'BHEJ DIYA': 'SENT',
    'JA RAHA HAI': 'SENDING',
    'BHEJEGA · {x}': 'WILL SEND · {x}',
    'CANCEL': 'CANCELLED',
    'FAIL': 'FAILED',
    'Ko': 'To',
    'Ko (email)': 'To (email)',
    'Vishay': 'Subject',
    'File jodiye': 'Add file',
    'Bhej raha hoon…': 'Sending…',
    'Phir bhejo': 'Send again',
    'Bhejo · {x}': 'Send · {x}',
    'Bhejo': 'Send',
    'Badlo': 'Edit',
    'Abhi bhejo': 'Send now',
    'Email badlo': 'Edit email',
    'Rehne do': 'Cancel',
    'Save karo': 'Save',
    'Cancel': 'Cancel',
    // ---- bazar (money) card ----
    'APPROVE KAREIN': 'APPROVE',
    'HAAN CHAHIYE': 'NEEDS YOUR OK',
    'DEMO: test bill hai, asli paise nahi katenge.': 'DEMO: this is a test bill, no real money will move.',
    'Kisko': 'To',
    'Kahan': 'Where',
    'UPI PIN sirf aapke UPI app mein daaliye. Hoola kabhi PIN nahi maangega.':
        'Enter the UPI PIN only in your own UPI app. Hoola never asks for your PIN.',
    'Ho raha hai…': 'Doing it…',
    'Approve karein': 'Approve',
    'Haan, karo': 'Yes, do it',
    // ---- campaign card ----
    'Taiyaar': 'READY',
    'Bhej raha hoon': 'SENDING',
    'Poora': 'DONE',
    'Ruk gaya': 'STOPPED',
    'Ruka hua': 'PAUSED',
    'Kal tak': 'UNTIL TOMORROW',
    'Bheje': 'Sent',
    'Pahunche': 'Delivered',
    'Padhe': 'Read',
    'Jawab': 'Replied',
    'Haan, bhej do': 'Yes, send',
    'Rokiye': 'Stop',
    'Phir se chalao': 'Resume',
    // ---- link card / open buttons ----
    '{x} jodiye': 'Link {x}',
    'Ek baar apne account se login kijiye (OTP unke page par aayega). Phir Hoola aapke liye order kar sakta hai.':
        'Sign in once with your account (the OTP appears on their page). Then Hoola can order for you.',
    '{x} link karein': 'Link {x}',
    'Kholiye': 'Open',
    // ---- work strip ----
    'Ho gaya': 'Done',
    'Nahi ho paya': 'Failed',
    'Roka gaya': 'Stopped',
    'Chal raha hai': 'Running',
    'Kaam': 'Work',
    '{x} kadam': '{x} steps',
    'Rok raha…': 'Stopping…',
    'Band kijiye': 'Close',
    // ---- long-press message menu ----
    'Copy karo': 'Copy',
    'Copy ho gaya': 'Copied',
    'Jawab mein quote karo': 'Quote in reply',
    'Text chuniye': 'Select text',
    'Text ko dabakar kheenchiye': 'Long-press and drag the text',
    'Text chunna band karo': 'Done selecting',
    // ---- Jaldi Se Karo quick actions (today screen) ----
    'Bill bharo': 'Pay a bill',
    'Dukaan': 'Shop',
    'Rasta': 'Directions',
    'Cab': 'Book a cab',
    'Photo banao': 'Edit a photo',
    'Video banao': 'Make a reel',
    'Email likho': 'Write an email',
    'TV': 'Play on TV',
    // ---- Hoola Employee section ----
    'Naukri chuniye — Hoola wahi kaam sambhalegi': 'Pick a job — Hoola will own it',
    'Mujhe apni dukaan pe lagao': 'Put me on your shop',
    'Aur AI employee lagao — kaam hoga tez': 'Hire more AI employees — work faster',
    'AAJ KE KAAM': "TODAY'S WORK",
    // ---- Hoola Network section (v0.171) ----
    'Pehle dost se shuru kariye': 'Start with your first friend',
    'Dusre Hoolas se knocks, baatein, deals — sab yahan aayega': 'Knocks, talks and deals from other Hoolas will land here',
    'QR ya ID se pehla dost jodiye': 'Add your first friend — QR or ID',
    'Aapki haan ke bina koi jud nahi sakta': 'No one connects without your OK',
    'Aapka Hoola, dusre Hoolas se mila': 'Your Hoola met other Hoolas',
    'Knocks, baatein, deals — sab khud sambhalti hoon': 'Knocks, talks, deals — I handle them all',
    'AAJ KE KNOCKS': "TODAY'S KNOCKS",
    'AAJ KI BAATEIN': 'LATEST TALKS',
    'AAPKE DOST': 'YOUR PEOPLE',
    'Network kholo — knocks, baatein, deals': 'Open the network — knocks, talks, deals',
    'Aapka {x}: ': 'Your {x}: ',
    // ---- Hoola Notebook section (v0.173) ----
    'Pehla notebook banaiye': 'Create your first notebook',
    'Web, PDF, YouTube, Drive — jo daaloge, {a} padh kar yaad rakhegi': 'Add web, PDFs, YouTube or Drive — {a} reads and remembers',
    'Notebook banao': 'Create a notebook',
    'Sirf aapke sources — {a} inhi se seekhti hai': 'Only your sources — {a} learns from them alone',
    'Padho, poochho, studio banao': 'Read, ask and make in the studio',
    'Sources daalo — {a} padh kar jawab degi': 'Add sources — {a} reads and answers',
    'Naya notebook': 'New notebook',
    'Sab notebooks kholo': 'Open all notebooks',
    // ---- Aaj kya seekha section (v0.175): real learning, category-wise ----
    'AAJ KYA SEEKHA': 'WHAT I LEARNT TODAY',
    'BAATEIN SE': 'FROM CHATS',
    'AWAAZ SE': 'FROM HER VOICE',
    'NETWORK SE': 'FROM THE NETWORK',
    'Sab dekho': 'See all',
    'Bhool jao': 'Forget',
    'aaj · {x}': 'today · {x}',
    'khud seekha': 'picked up on her own',
    'Aapne sikhaya': 'You taught her',
    'Calls se pakda': 'Caught on calls',
    '{x} baar galat suna': 'Misheard {x} times',
    'pakka': 'confirmed',
    'Network se seekhi skill': 'Skill learnt on the network',
    '{x} se seekhi skill': 'Learnt from {x}',
    'Aaj baaton se kuch naya nahi.': 'Nothing new from chats today.',
    'Aaj awaaz se kuch naya nahi.': 'Nothing new from voice today.',
    'Network se aaj kuch naya nahi.': 'Nothing new from the network today.',
    'Aaj kuch naya nahi seekha': 'Nothing new learnt today',
    'Baat karo, calls lo, network chalao — jitna karengi, utna seekhungi.':
        'Chat, take calls, run the network — the more we do, the more I learn.',
    'Har baat aur har call se kuch naya sikhti hoon.': 'Every chat and every call teaches me something new.',
    '"Jo na pasand ho, ek tap mein bhula do."': '"Don\'t like something? One tap and it\'s forgotten."',
    // ---- Reminders section (v0.176): grouped by day, countdown, repeat chips ----
    'REMINDERS': 'REMINDERS',
    'AAJ': 'TODAY',
    'KAL': 'TOMORROW',
    'BAAD MEIN': 'LATER',
    'Koi reminder nahi': 'Nothing to remind — yet',
    'Boliye: "Kal 9 baje dawai yaad dilana" — main turant likh lungi.':
        'Say: "Remind me about my medicine tomorrow at 9" — I\'ll write it down at once.',
    'Baat shuru karo': 'Start a chat',
    'Har yaad time par dugi.': 'Every reminder, right on time.',
    'Roz': 'Daily',
    'Mon–Fri': 'Weekdays',
    'Har hafte': 'Weekly',
    'Har mahine': 'Monthly',
    '{x} min baad': 'in {x} min',
    '{x} ghante baad': 'in {x} hrs',
    '{x} din baad': 'in {x} days',
    'Reminder hata diya': 'Reminder removed',
    // ---- Hoola ke apne kaam + LISTS (v0.177): cadence tiles, proof-of-work, done-today with undo ----
    'HOOLA KE APNE KAAM': "HOOLA'S OWN JOBS",
    'AAGE': 'AHEAD',
    'Ek baar': 'Once',
    'Har ghante': 'Every hour',
    '{x} baar': '{x} times',
    'Hoola ka koi kaam chalu nahi': 'No self-run jobs yet',
    'Boliye: "Har subah 7 baje mausam bata dena" — main roz khud karungi, yaad dilana nahi padega.':
        'Say: "Tell me the weather every morning at 7" — I\'ll do it daily on my own; you never have to remind me.',
    'Mera kaam, meri zimmedari — time par, bina yaad dilaye.': 'My job, my responsibility — on time, without being asked.',
    'Kaam band kar diya': 'Job stopped',
    'LISTS': 'LISTS',
    'Koi list nahi': 'No lists yet',
    'Boliye: "Doodh aur bread shopping list mein daalo" — main likh lungi, aur tick karti jaungi.':
        'Say: "Add milk and bread to the shopping list" — I\'ll write it down and tick things off as they\'re done.',
    'Har chhoti cheez likhi jaayegi — poore hote hi neeche tikti jaayegi.':
        'Every little thing gets written down — and ticks itself off below the moment it\'s done.',
    '{x} baaki': '{x} left',
    'AAJ POORE KIYE': 'DONE TODAY',
    'Wapas list mein': 'Back in the list',
    // ---- v0.182.0 Mail aayi!: watcher cards + email screen ----
    'Nayi mail': 'New mail',
    'Inbox update': 'Inbox update',
    'ZAROORI': 'IMPORTANT',
    'Padho': 'Read',
    'Jawab do': 'Reply',
    'Archive': 'Archive',
    '1 ghanta': '1 hour',
    'Kal subah': 'Tomorrow morning',
    'Snooze khatam': 'Snooze over',
    'WAPAS': 'BACK',
    'Yeh mail wapas inbox mein hai (unread).': 'This mail is back in your inbox (unread).',
    'Is mail mein login/OTP ka code ho sakta hai — Santosh code kabhi nahi batata.':
        'This mail may hold a login/OTP code — Santosh never reads codes out.',
    'Nayi mail ki khabar': 'New-mail announcements',
    'Hoola har minute aapka inbox dekhta hai. Zaroori mail ya apne logon ki mail aaye to chat mein bata deta hai; newsletters chup rehte hain. OTP codes kabhi nahi batata.':
        'Hoola checks your inbox every minute and tells you in chat when important mail or mail from your own people arrives; newsletters stay quiet. OTP codes are never shown.',
    'Shant': 'Quiet',
    'Zaroori': 'Important',
    'Sab': 'All',
    'Mail rules': 'Mail rules',
    'Naya rule': 'New rule',
    'Rule ka naam': 'Rule name',
    'Kisase aaye to (jaise hdfcbank)': 'From contains (e.g. hdfcbank)',
    'Vishay mein shabd (jaise bill, invoice)': 'Subject words (e.g. bill, invoice)',
    'Kya karein': 'What to do',
    'Label lagao (naam)': 'Apply label (name)',
    'Archive karo': 'Archive it',
    'Star laga do': 'Star it',
    'Padha hua mark karo': 'Mark as read',
    'Rule chalu hai. Ab se aane wali nayi mail par chalega.':
        'The rule is on. It runs on new mail from now on.',
    'Rules nayi mail par chalte hain; bhejna hamesha aapke Bhejo par.':
        'Rules act on new mail; sending always waits for your tap.',
    'Koi rule nahi. Bolo "bank ki mail aaye to archive karo" jaisa rule chat mein.':
        'No rules yet. Say a rule in chat, like "archive mail from my bank".',
    'Gmail, poora': 'Gmail, poora',
    'Gmail ke saare kaam, chat se — hifazat ke saath':
        'Every Gmail job, from chat — with the guardrails on',
    'Padhna, chhaantna: inbox, thread poora, attachments (PDF, Excel, photos bhi), Gmail ke apne snoozed folder samet.':
        'Reading and sorting: inbox, whole threads, attachments (PDF, Excel, photos too), even Gmail\'s own snoozed folder.',
    'Likhte waqt: rich mail, Drive file attach, schedule, undo window, alias se bhejna (verified aliases).':
        'Writing: rich mail, attach Drive files, schedule, undo window, send from an alias (verified ones).',
    'Khud sambhale: rules, saved searches, labels (rang aur nesting ke saath), snooze, follow-up yaad, bulk mail.':
        'It organises itself: rules, saved searches, labels (colours and nesting), snooze, follow-up reminders, bulk mail.',
    'Gmail ki apni settings: vacation auto-reply, signature, send-as aliases, auto-forward — sab aapke tap par.':
        'Gmail\'s own settings: vacation auto-reply, signature, send-as aliases, auto-forward — all on your tap.',
    'Nayi mail ki khabar har minute, zaroori ka pehle; OTP codes kabhi nahi batata.':
        'New-mail alerts every minute, important mail first; OTP codes are never shown.',
    'Settings ke liye Gmail ek baar dobara jodna pade to is screen par “Jodiye” dabaiye — mail pehle jaisi chalti hai.':
        'If Gmail ever needs a one-time reconnect for settings, tap "Jodiye" here — mail keeps working as before.',
    'Saved searches': 'Saved searches',
    'Chat mein boliye “<naam> dikhao” — yeh sirf dikhata hai, kuch nahi badalta.':
        'Say "show <name>" in chat — it only shows what matches now, nothing changes.',
  },
};

/// Translate one UI string for [lang] (e.g. 'en-IN', 'hi-IN').
/// Hindi (Hinglish) strings are the keys themselves, so they pass through unchanged;
/// every other language looks up its table, then the English table, then returns the key.
String tr(String lang, String text, {String? a, String? x}) {
  final code = lang.split('-').first;
  if (code == 'hi') return text;
  final t = uiStrings[code]?[text] ?? uiStrings['en']![text] ?? text;
  return t.replaceAll('{a}', a ?? '').replaceAll('{x}', x ?? '');
}
