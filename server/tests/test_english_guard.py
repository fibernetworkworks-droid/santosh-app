"""English guard (v0.820 SAB ENGLISH wave 4): Hoola's own text must stay English.

A ratchet, not a ban: `hinglish_baseline.json` records how many string literals in each server file still look like
Hinglish (word lists that READ a user's Hinglish, Hindi / Marathi templates and sample asks all count, and are meant
to stay). A file may never have MORE than its recorded count, and a file not in the record may have none - so new
Hinglish text cannot creep back in. When you translate more, regenerate the record:
    python tests/test_english_guard.py --write
"""
import ast
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hinglish_baseline.json")
FROZEN = ("pc" + os.sep,)

STRONG = """hai hain nahi nahin karo kijiye kijiyega karein karen karna karta karti karte kiya kiye aap aapka aapki aapke aapko
kaam haan abhi bhej bhejo bhejiye bheja bheji liye wala wali wale kya kuch kuchh gaya gayi gaye hua hui hue raha rahi rahe
hoga hogi honge mila mili mile milta dekho dekhiye dekhna batao bataiye bataya likho likhiye likha chahiye sakta sakti sakte
pehle baad mein yahan wahan iska uska unka inka mera meri mere humara hamara tumhara apna apni apne koi sab sabhi
kaise kyun kyon kab kahan kaun kitna kitne kitni thoda bahut zyada kam accha achha theek thik galat sahi naya nayi naye
purana wapas dobara phir fir aur ya lekin magar agar toh tab jab jaise aise waise banao banaiye banaya bana bani chalu band
kholo kholiye khol jodiye jodo jod hatao hataiye daalo daaliye dijiye lijiye dena lena aaya aayi aaye jao jaiye
ruko rukiye suno suniye bolo boliye poochho poocho puchho samajh pata maloom zaroor zaroori shayad bilkul
taiyaar taiyar khatam shuru baaki bacha poora pura adhura intezaar ruka atka chal chalu gadbad galti dikkat mushkil aasaan
paisa paise rupaye kharcha hisaab bhugtan yaad suchna khabar jawab sawaal madad dhanyavaad shukriya namaste
ho gaya kar diya kar di kar raha kar rahi rahega chahte chahti chahta hoon hun hu tha thi the nahi. mat
abhi tak waqt samay din raat subah shaam kal aaj parso hafta mahina saal""".split()
STRONG=set(w for w in STRONG if len(w)>2) - {"the","mile","mat","tab","jab","chal","kam","kal","bana","fir","din","hue","jao","khol","jod","sab","aur","bani","saal","hui"}
# words that only count with another strong word nearby
WEAK=set("ka ki ke ko se par pe hi bhi to na ho kar le de ye yeh woh wo is us mat tab jab kal kam sab aur din".split())
tok=re.compile(r"[A-Za-z']+")
dev=re.compile(r"[ऀ-ॿ]")
def score(s):
    ws=[w.lower() for w in tok.findall(s)]
    st=[w for w in ws if w in STRONG]
    wk=[w for w in ws if w in WEAK]
    return len(st), len(wk), bool(dev.search(s))
IDENT=re.compile(r'^[A-Za-z0-9_.:/\\-]+$')
def hing(s):
    if IDENT.match(s.strip()): return False
    a,b,d=score(s)
    if d: return True
    if a>=2: return True
    if a>=1 and b>=1: return True
    if a==1 and len(tok.findall(s))<=4: return True
    return False
def py_strings(path):
    try: tree=ast.parse(open(path,encoding="utf-8").read())
    except Exception: return []
    out=[]
    docs=set()
    for n in ast.walk(tree):
        if isinstance(n,(ast.Module,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            b=getattr(n,"body",[])
            if b and isinstance(b[0],ast.Expr) and isinstance(getattr(b[0],"value",None),ast.Constant) and isinstance(b[0].value.value,str):
                docs.add(id(b[0].value))
    for n in ast.walk(tree):
        if isinstance(n,ast.Constant) and isinstance(n.value,str) and id(n) not in docs:
            out.append((n.lineno,n.value))
    return out


def count_all():
    out = {}
    for d, _, fs in os.walk(ROOT):
        if "static" in d.split(os.sep) or "vendor" in d.split(os.sep) or "__pycache__" in d:
            continue
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(d, f)
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            n = sum(1 for _ln, s in py_strings(p) if hing(s))
            if n:
                out[rel] = n
    return out


def test_no_new_hinglish_in_server_text():
    base = json.load(open(BASE, encoding="utf-8"))
    now = count_all()
    worse = {k: (base.get(k, 0), v) for k, v in now.items() if v > base.get(k, 0)}
    assert not worse, ("New Hinglish-looking text (file: allowed, found). Write it in English, or if it is a word list "
                       "that must read Hinglish input, regenerate the record: " + repr(worse))


if __name__ == "__main__":
    if "--write" in sys.argv:
        data = count_all()
        json.dump(dict(sorted(data.items())), open(BASE, "w", encoding="utf-8"), indent=0)
        print("written", len(data), "files,", sum(data.values()), "strings")
