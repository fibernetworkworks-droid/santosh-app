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
    'Abhi': 'Now',
    'abhi': 'just now',
    '{x} min pehle': '{x} min ago',
    '{x} ghante pehle': '{x} hrs ago',
    '{x} din pehle': '{x} days ago',
    '(dobara koshish ke liye tap kijiye)': '(tap to try again)',
    'Hoola ka dimaag server par connect nahi hai (ANTHROPIC_API_KEY).': "Hoola's brain is not connected on the server (ANTHROPIC_API_KEY).",
    'Boliye: "Kal subah 7 baje yaad dilana", "Doodh list mein daalo", "Pune ka mausam?"':
        'Try: "Remind me tomorrow at 7 am", "Add milk to my list", "Weather in Pune?"',
    // ---- composer / mic / attach ----
    '{a} se boliye…': 'Message {a}…',
    'Sun raha hoon…': 'Listening…',
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
