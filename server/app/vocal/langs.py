"""v0.999.89 HOOLA VOCAL GLOBAL - every language Hoola Vocal can speak, and which engine speaks it.

Sources, read 21 Nov 2026:
- Gemini 3.8 Flash TTS: the supported-language table on aistudio.google.com/docs/speech-generation (about 130 rows).
  Google gives names, not codes, so the codes below are the standard BCP-47 / ISO 639 codes for those names.
- ElevenLabs eleven_v4 and eleven_v3: the language-code lists on elevenlabs.io/docs/overview/models.

A language NO ready engine speaks is refused with a plain line. It is never read in another language. `quality` stays
"not_tested" until Hoola's own listening test has rated that language: never a guess.
"""
from __future__ import annotations

# code | English name | native name | region | G = Gemini 3.8 Flash TTS, 4 = ElevenLabs v4, 3 = ElevenLabs v3
_TABLE = """
af|Afrikaans|Afrikaans|Africa|G43
ak|Akan|Akan|Africa|G
am|Amharic|አማርኛ|Africa|G4
ar|Arabic|العربية|Middle East|G43
arz|Egyptian Arabic|مصرى|Middle East|G
ar-Latn|Arabic (Latin letters)|Arabizi|Middle East|G
hy|Armenian|Հայերեն|Europe|G43
as|Assamese|অসমীয়া|Asia|G43
ast|Asturian|Asturianu|Europe|43
awa|Awadhi|अवधी|Asia|G
az|Azerbaijani|Azərbaycan|Asia|G43
azb|South Azerbaijani|تۆرکجه|Middle East|G
ace|Acehnese|Acèh|Asia|G
ban|Balinese|Basa Bali|Asia|G
bjn|Banjar|Bahasa Banjar|Asia|G
ba|Bashkir|Башҡортса|Europe|G
eu|Basque|Euskara|Europe|G
be|Belarusian|Беларуская|Europe|G43
bem|Bemba|Ichibemba|Africa|G
bn|Bengali|বাংলা|Asia|G43
bho|Bhojpuri|भोजपुरी|Asia|G
bs|Bosnian|Bosanski|Europe|G43
bug|Buginese|Basa Ugi|Asia|G
bg|Bulgarian|Български|Europe|G43
my|Burmese|မြန်မာ|Asia|G43
yue|Cantonese|粵語|Asia|G43
ca|Catalan|Català|Europe|G43
ceb|Cebuano|Cebuano|Asia|G43
ckb|Central Kurdish|کوردی|Middle East|G4
hne|Chhattisgarhi|छत्तीसगढ़ी|Asia|G
zh|Chinese (Mandarin, Simplified)|中文（简体）|Asia|G43
zh-Hant|Chinese (Traditional)|中文（繁體）|Asia|G
ny|Chichewa (Nyanja)|Chichewa|Africa|G3
crh|Crimean Tatar|Qırımtatarca|Europe|G
hr|Croatian|Hrvatski|Europe|G43
cs|Czech|Čeština|Europe|G43
da|Danish|Dansk|Europe|G43
nl|Dutch|Nederlands|Europe|G43
dyu|Dyula|Jula|Africa|G
dz|Dzongkha|རྫོང་ཁ|Asia|G
en|English|English|Americas|G43
et|Estonian|Eesti|Europe|G43
fil|Filipino|Filipino|Asia|G43
fi|Finnish|Suomi|Europe|G43
fr|French|Français|Europe|G43
ff|Fula|Fulfulde|Africa|4
fuv|Nigerian Fulfulde|Fulfulde|Africa|G
gl|Galician|Galego|Europe|G43
lg|Ganda|Luganda|Africa|G4
ka|Georgian|ქართული|Europe|G43
de|German|Deutsch|Europe|G43
el|Greek|Ελληνικά|Europe|G43
gn|Guarani|Avañe'ẽ|Americas|G
gu|Gujarati|ગુજરાતી|Asia|G43
ht|Haitian Creole|Kreyòl ayisyen|Americas|G
ha|Hausa|Hausa|Africa|G43
he|Hebrew|עברית|Middle East|G43
hi|Hindi|हिन्दी|Asia|G43
hu|Hungarian|Magyar|Europe|G43
is|Icelandic|Íslenska|Europe|G43
ig|Igbo|Igbo|Africa|G
ilo|Ilocano|Ilokano|Asia|G
id|Indonesian|Bahasa Indonesia|Asia|G43
ga|Irish|Gaeilge|Europe|3
it|Italian|Italiano|Europe|G43
ja|Japanese|日本語|Asia|G43
jv|Javanese|Basa Jawa|Asia|G43
kab|Kabyle|Taqbaylit|Africa|G
kam|Kamba|Kikamba|Africa|G4
kn|Kannada|ಕನ್ನಡ|Asia|G43
ks|Kashmiri|کٲشُر|Asia|G
kk|Kazakh|Қазақша|Asia|G43
km|Khmer|ខ្មែរ|Asia|G
ki|Kikuyu|Gĩkũyũ|Africa|G
rw|Kinyarwanda|Ikinyarwanda|Africa|G
kg|Kongo|Kikongo|Africa|G
ko|Korean|한국어|Asia|G43
ky|Kyrgyz|Кыргызча|Asia|G43
lo|Lao|ລາວ|Asia|G4
ltg|Latgalian|Latgaļu|Europe|G
lv|Latvian|Latviešu|Europe|G43
ln|Lingala|Lingála|Africa|G43
lt|Lithuanian|Lietuvių|Europe|G43
lb|Luxembourgish|Lëtzebuergesch|Europe|G43
mk|Macedonian|Македонски|Europe|G43
mag|Magahi|मगही|Asia|G
mai|Maithili|मैथिली|Asia|G
ms|Malay|Bahasa Melayu|Asia|G43
ml|Malayalam|മലയാളം|Asia|G43
mt|Maltese|Malti|Europe|G43
mni|Manipuri|ꯃꯩꯇꯩꯂꯣꯟ|Asia|G
mi|Maori|Te reo Māori|Pacific|43
mr|Marathi|मराठी|Asia|G43
min|Minangkabau|Baso Minang|Asia|G
lus|Mizo|Mizo ṭawng|Asia|G
mn|Mongolian|Монгол|Asia|G43
ne|Nepali|नेपाली|Asia|G43
nso|Northern Sotho|Sesotho sa Leboa|Africa|G
nb|Norwegian (Bokmål)|Norsk bokmål|Europe|G43
nn|Norwegian (Nynorsk)|Norsk nynorsk|Europe|G
oc|Occitan|Occitan|Europe|G43
or|Odia|ଓଡ଼ିଆ|Asia|G43
pag|Pangasinan|Pangasinan|Asia|G
ps|Pashto|پښتو|Middle East|G43
fa|Persian|فارسی|Middle East|G43
prs|Dari (Afghan Persian)|دری|Middle East|G
pl|Polish|Polski|Europe|G43
pt|Portuguese|Português|Americas|G43
pa|Punjabi|ਪੰਜਾਬੀ|Asia|G43
ro|Romanian|Română|Europe|G43
ru|Russian|Русский|Europe|G43
sat|Santali|ᱥᱟᱱᱛᱟᱲᱤ|Asia|G
sr|Serbian|Српски|Europe|G43
sn|Shona|chiShona|Africa|4
sd|Sindhi|سنڌي|Asia|G43
si|Sinhala|සිංහල|Asia|G
sk|Slovak|Slovenčina|Europe|G43
sl|Slovenian|Slovenščina|Europe|G43
so|Somali|Soomaali|Africa|G43
st|Southern Sotho|Sesotho|Africa|G
es|Spanish|Español|Americas|G43
sw|Swahili|Kiswahili|Africa|G43
ss|Swati|SiSwati|Africa|G
sv|Swedish|Svenska|Europe|G43
tg|Tajik|Тоҷикӣ|Asia|G43
ta|Tamil|தமிழ்|Asia|G43
te|Telugu|తెలుగు|Asia|G43
th|Thai|ไทย|Asia|G43
ti|Tigrinya|ትግርኛ|Africa|G
sq|Albanian|Shqip|Europe|G
tr|Turkish|Türkçe|Europe|G43
uk|Ukrainian|Українська|Europe|43
ur|Urdu|اردو|Asia|43
ug|Uyghur|ئۇيغۇرچە|Asia|G
uz|Uzbek|Oʻzbekcha|Asia|G43
vi|Vietnamese|Tiếng Việt|Asia|G43
cy|Welsh|Cymraeg|Europe|43
wo|Wolof|Wolof|Africa|4
yo|Yoruba|Yorùbá|Africa|3
zu|Zulu|isiZulu|Africa|4
"""


def _parse() -> list[dict]:
    out = []
    for line in _TABLE.strip().splitlines():
        code, en, native, region, eng = line.split("|")
        out.append({"code": code, "name": en, "native": native, "region": region,
                    "gemini": "G" in eng, "eleven4": "4" in eng, "eleven3": "3" in eng})
    return out


LANGS: list[dict] = _parse()
BY_CODE: dict[str, dict] = {x["code"]: x for x in LANGS}
REGIONS = ("Africa", "Americas", "Asia", "Europe", "Middle East", "Pacific")
# Words people write for a language -> its code, so "Swahili", "kiswahili", "sw" and "sw-KE" all land on one row.
_ALIAS: dict[str, str] = {}
for _x in LANGS:
    for _k in (_x["code"], _x["name"], _x["native"], _x["name"].split(" (")[0]):
        _ALIAS.setdefault(_k.lower(), _x["code"])
_ALIAS.update({"mandarin": "zh", "chinese": "zh", "norwegian": "nb", "no": "nb", "tagalog": "fil", "farsi": "fa",
               "kurdish": "ckb", "albanian": "sq", "hinglish": "hi", "brazilian portuguese": "pt", "castilian": "es",
               "swahili": "sw", "nyanja": "ny", "pashto": "ps", "sorani": "ckb", "tl": "fil", "iw": "he", "in": "id"})


def code_of(s: str) -> str:
    """Any way of writing a language -> its code here, or '' when unknown. 'auto' stays 'auto'."""
    t = (s or "").strip().lower()
    if t in ("", "auto", "auto language", "any"):
        return "auto"
    if t in _ALIAS:
        return _ALIAS[t]
    base = t.split("-")[0].split("_")[0]            # sw-KE, es_MX -> sw, es
    return _ALIAS.get(base, "")


def name_of(code: str) -> str:
    x = BY_CODE.get(code)
    return x["name"] if x else (code or "")


def gemini_speaks(code: str) -> bool:
    x = BY_CODE.get(code)
    return bool(x and x["gemini"])


def eleven_speaks(code: str) -> bool:
    x = BY_CODE.get(code)
    return bool(x and (x["eleven4"] or x["eleven3"]))


def eleven_model_for(code: str) -> str:
    """eleven_v3 for a language only v3 lists (Yoruba, Irish, Chichewa); eleven_v4 otherwise."""
    x = BY_CODE.get(code) or {}
    if x.get("eleven4"):
        return "eleven_v4"
    return "eleven_v3" if x.get("eleven3") else "eleven_v4"


# ---------------------------------------------------------------- telling the language of her words (no library)
_SCRIPTS = [                     # (first, last code point) -> the language most people writing it mean
    (0x0900, 0x097F, "hi"), (0x0980, 0x09FF, "bn"), (0x0A00, 0x0A7F, "pa"), (0x0A80, 0x0AFF, "gu"), (0x0B00, 0x0B7F, "or"),
    (0x0B80, 0x0BFF, "ta"), (0x0C00, 0x0C7F, "te"), (0x0C80, 0x0CFF, "kn"), (0x0D00, 0x0D7F, "ml"), (0x0D80, 0x0DFF, "si"),
    (0x0E00, 0x0E7F, "th"), (0x0E80, 0x0EFF, "lo"), (0x0F00, 0x0FFF, "dz"), (0x1000, 0x109F, "my"), (0x10A0, 0x10FF, "ka"),
    (0x1200, 0x137F, "am"), (0x1780, 0x17FF, "km"), (0x0530, 0x058F, "hy"), (0x0590, 0x05FF, "he"), (0x0600, 0x06FF, "ar"),
    (0x3040, 0x30FF, "ja"), (0xAC00, 0xD7AF, "ko"), (0x1100, 0x11FF, "ko"), (0x4E00, 0x9FFF, "zh"), (0x0370, 0x03FF, "el"),
    (0x0400, 0x04FF, "ru"), (0x1C50, 0x1C7F, "sat"), (0xABC0, 0xABFF, "mni"),
]
# A few very common words that tell Latin-script languages apart. Enough to pick a language for the reading; she can
# always choose one herself.
_WORDS = {
    "es": "el la los las que qué de y en un una es por para con no se mi su gracias hola bienvenidos nuestro muy bien tal está estás sí cómo buenos días",
    "pt": "o a os as que de e em um uma é para com não se meu seu obrigado olá bem-vindos nosso você",
    "fr": "le la les des que de et en un une est pour avec ne pas je vous bonjour merci bienvenue notre",
    "de": "der die das und ist nicht ein eine mit für auf ich sie wir willkommen danke unser auch",
    "it": "il la lo gli che di e un una è per con non sono ciao grazie benvenuti nostro anche",
    "nl": "de het een en van is dat niet met voor op ik je welkom dank onze ook",
    "id": "yang dan di ini itu dengan untuk tidak ada saya kami selamat datang terima kasih",
    "ms": "yang dan di ini itu dengan untuk tidak ada saya kami selamat datang terima kasih",
    "sw": "na ya wa kwa ni la za katika karibu asante habari sana yetu mkate kila",
    "tr": "ve bir bu da de için ile değil ben biz merhaba teşekkürler hoş geldiniz",
    "vi": "và của là có không một những cho với tôi chúng xin chào cảm ơn",
    "fil": "ang ng sa mga at na ay ito kami salamat po maligayang",
    "pl": "i w nie na się jest to że z do jak dziękuję witamy nasz",
    "sv": "och i att det som en är på för med inte jag vi välkommen tack",
    "en": "the and to of a in is it you that for with this we our welcome thank your are",
    "yo": "ni ati ti mo o wa e se jowo kaabo",
    "ha": "da a ya na ta ba sannu nagode barka",
    "zu": "ngi u si ku ukuthi sawubona ngiyabonga yebo",
    "af": "die en is van in nie dit ek ons welkom dankie",
}
_WORDSETS = {k: set(v.split()) for k, v in _WORDS.items()}


def detect(text: str) -> str:
    """The language of her words, from the script she writes in and a few common words. '' when unsure."""
    t = (text or "").strip()
    if not t:
        return ""
    counts: dict[str, int] = {}
    latin = 0
    for ch in t:
        o = ord(ch)
        if ("a" <= ch.lower() <= "z") or 0x00C0 <= o <= 0x024F or 0x1E00 <= o <= 0x1EFF:
            latin += 1
            continue
        for a, b, code in _SCRIPTS:
            if a <= o <= b:
                counts[code] = counts.get(code, 0) + 1
                break
    if counts and max(counts.values()) >= max(3, latin // 2):
        top = max(counts, key=counts.get)
        if top == "zh" and any(0x3040 <= ord(c) <= 0x30FF for c in t):
            return "ja"
        if top == "ar" and any(c in t for c in "پچژگ"):
            return "fa" if not any(c in t for c in "ٹڈڑں") else "ur"
        return top
    words = [w.strip(".,!?;:'\"()«»¿¡") for w in t.lower().split()]
    best, score = "", 0
    for code, ws in _WORDSETS.items():
        n = sum(1 for w in words if w in ws)
        if n > score:
            best, score = code, n
    return best if score >= 2 or (score == 1 and len(words) <= 3) else ""
