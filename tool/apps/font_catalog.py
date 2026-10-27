"""Build server/app/appmaker/fontcat.json: open-licence font families (Fontsource packages on npm) the app designer
may use, with their scripts (subsets), weights, category, licence and the exact npm tarball + integrity the server
downloads on first use. Run when the list changes:  python tool/apps/font_catalog.py"""
import io
import json
import re
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "server/app/appmaker/fontcat.json"
REG = "https://registry.npmjs.org/@fontsource%2f"
OK_LICENCES = {"OFL-1.1", "Apache-2.0", "UFL-1.0", "MIT"}

CANDIDATES = """
Inter|Roboto|Open Sans|Lato|Montserrat|Poppins|Raleway|Nunito|Nunito Sans|Work Sans|DM Sans|DM Serif Display|DM Serif Text|Manrope|
Plus Jakarta Sans|Outfit|Sora|Urbanist|Lexend|Figtree|Onest|Space Grotesk|Syne|Bricolage Grotesque|Archivo|Archivo Black|Rubik|Karla|
IBM Plex Sans|IBM Plex Serif|IBM Plex Mono|IBM Plex Sans Devanagari|Fira Sans|Fira Code|JetBrains Mono|Source Sans 3|Source Serif 4|
Merriweather|Playfair Display|Lora|Libre Baskerville|Cormorant Garamond|EB Garamond|Crimson Pro|Fraunces|Instrument Serif|Instrument Sans|
Spectral|Noto Serif|Noto Sans|PT Serif|PT Sans|Quicksand|Comfortaa|Varela Round|Fredoka|Baloo 2|Bebas Neue|Oswald|Anton|Righteous|
Lobster|Pacifico|Dancing Script|Great Vibes|Satisfy|Caveat|Shadows Into Light|Permanent Marker|Abril Fatface|Bodoni Moda|Josefin Sans|
Josefin Slab|Cabin|Barlow|Barlow Condensed|Exo 2|Orbitron|Audiowide|Chakra Petch|Rajdhani|Saira|Titillium Web|Ubuntu|Mulish|Heebo|
Assistant|Hanken Grotesk|Red Hat Display|Red Hat Text|Albert Sans|Epilogue|Be Vietnam Pro|Public Sans|Inter Tight|Space Mono|Courier Prime|
Abel|Alegreya|Alegreya Sans|Cinzel|Marcellus|Prata|Yeseva One|Kanit|Prompt|Mitr|Unbounded|Gabarito|Schibsted Grotesk|Familjen Grotesk|
Big Shoulders Display|Darker Grotesque|Golos Text|Geologica|Reddit Sans|Wix Madefor Display|Young Serif|Gloock|Playfair|Libre Franklin|
Libre Caslon Text|Zilla Slab|Roboto Slab|Roboto Mono|Roboto Condensed|Roboto Flex|Noto Sans Mono|Overpass|Signika|Asap|Encode Sans|
Merriweather Sans|Bitter|Arvo|Rokkitt|Kalnia|Sofia Sans|Lilita One|Bungee|Luckiest Guy|Chewy|Gochi Hand|Patrick Hand|Indie Flower|
Amatic SC|Sacramento|Allura|Parisienne|Tangerine|Cookie|Kaushan Script|Yellowtail|Courgette|Philosopher|Comic Neue|Atkinson Hyperlegible|
Lexend Deca|Readex Pro|Noto Sans Display|Mukta|Mukta Vaani|Mukta Malar|Mukta Mahee|Hind|Hind Siliguri|Hind Madurai|Hind Guntur|Hind Vadodara|
Baloo Bhai 2|Baloo Bhaijaan 2|Baloo Tamma 2|Baloo Chettan 2|Baloo Thambi 2|Baloo Tammudu 2|Baloo Da 2|Baloo Paaji 2|Baloo Bhaina 2|
Noto Sans Devanagari|Noto Serif Devanagari|Noto Sans Tamil|Noto Serif Tamil|Noto Sans Telugu|Noto Serif Telugu|Noto Sans Kannada|
Noto Serif Kannada|Noto Sans Malayalam|Noto Serif Malayalam|Noto Sans Bengali|Noto Serif Bengali|Noto Sans Gujarati|Noto Serif Gujarati|
Noto Sans Gurmukhi|Noto Serif Gurmukhi|Noto Sans Oriya|Noto Serif Oriya|Noto Nastaliq Urdu|Noto Sans Arabic|Noto Naskh Arabic|
Tiro Devanagari Hindi|Tiro Devanagari Marathi|Tiro Devanagari Sanskrit|Tiro Bangla|Tiro Tamil|Tiro Telugu|Tiro Kannada|Tiro Gurmukhi|
Martel|Martel Sans|Rozha One|Teko|Khand|Kalam|Laila|Eczar|Yatra One|Palanquin|Palanquin Dark|Sarala|Karma|Amita|Arya|Biryani|Cambay|
Glegoo|Halant|Inknut Antiqua|Jaldi|Kadwa|Kurale|Modak|Pragati Narrow|Rhodium Libre|Sahitya|Sumana|Sura|Sarpanch|Vesper Libre|Yantramanav|
Gotu|Kumar One|Ranga|Asar|Dekko|Amiko|Akshar|Anek Devanagari|Anek Latin|Anek Tamil|Anek Telugu|Anek Kannada|Anek Malayalam|Anek Bangla|
Anek Gujarati|Anek Gurmukhi|Anek Odia|Catamaran|Pavanam|Mallanna|Ramabhadra|NTR|Tenali Ramakrishna|Gidugu|Suranna|Mandali|Gurajada|
Kavivanar|Gayathri|Chilanka|Manjari|Atma|Galada|Mina|Shrikhand|Farsan|Rasa|Yrsa|Mogra|Poppins|Sriracha|Noto Sans Sinhala|Noto Sans Thai|
Noto Sans JP|Noto Sans KR|Noto Sans SC|Noto Serif JP|M PLUS Rounded 1c|Zen Maru Gothic|Sawarabi Gothic|Rakkas|Cairo|Tajawal|Almarai|
Amiri|Lalezar|Vazirmatn|Noto Sans Hebrew|Rubik Mono One|Silkscreen|Press Start 2P|VT323|Major Mono Display|Monoton|Bungee Shade|
Rubik Glitch|Nabla|Honk|Climate Crisis|Bowlby One|Alfa Slab One|Ultra|Fjalla One|Passion One|Black Ops One|Russo One|Sigmar One
"""


def slug(fam: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")


def one(fam: str):
    s = slug(fam)
    try:
        man = json.load(urllib.request.urlopen(REG + s + "/latest", timeout=40))
        tb = man["dist"]["tarball"]
        data = urllib.request.urlopen(tb, timeout=120).read()
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            meta = json.load(tf.extractfile("package/metadata.json"))
            files = [m.name.split("/")[-1] for m in tf.getmembers() if m.name.endswith(".woff2")]
    except Exception as e:     # not on Fontsource / network
        return fam, None, str(e)[:80]
    lic = (meta.get("license") or {}).get("type") or man.get("license") or ""
    if lic not in OK_LICENCES:
        return fam, None, f"licence {lic}"
    return fam, {"id": meta["id"], "family": meta["family"], "category": meta.get("category", ""),
                 "subsets": meta.get("subsets", []), "weights": meta.get("weights", []), "variable": bool(meta.get("variable")),
                 "license": lic, "version": man["version"], "tarball": tb, "integrity": man["dist"]["integrity"],
                 "size": len(data), "files": len(files)}, ""


def main() -> None:
    fams = list(dict.fromkeys(x.strip() for x in CANDIDATES.replace("\n", "").split("|") if x.strip()))
    out = {}
    with ThreadPoolExecutor(8) as ex:
        for fam, rec, err in ex.map(one, fams):
            if rec:
                out[rec["id"]] = rec
            else:
                print("skip", fam, err, file=sys.stderr)
    OUT.write_text(json.dumps(dict(sorted(out.items())), indent=0, ensure_ascii=False))
    print(len(fams), "candidates,", len(out), "families")


if __name__ == "__main__":
    main()
