#!/usr/bin/env python3
"""
Kerala, India and Gulf place names in Malayalam for typing suggestions (Nikhil, 5 Nov: "place" words).

Sources (in this order, THIRD_PARTY.md):
  1. Wikidata (CC0): Kerala towns, villages, wards, grama panchayats, municipalities, taluks, districts, post office
     and railway station places, with their Malayalam labels; India / Gulf / world cities from wikidata_named.csv.
  2. common_spellings.tsv: Lipi's own short list of the spellings Malayalis use in chat (ബാംഗ്ലൂർ, ദുബൈ, തൃശൂർ).
  3. MVD bus stop list (Kerala Motor Vehicles Department, obtained under RTI): English spellings only, used for the
     test set (typed spelling → Wikidata's Malayalam), never as Malayalam words.
  LGD / Census and OpenStreetMap are not used yet (LGD downloads sit behind a captcha form; the OSM Overpass server
  refused this build's connections). The raw downloads are kept in nikhilannur/lipi-data (places/sources/).

  python3 tools/places/build_places.py <sources dir>

Writes:
  tools/places/places_ml.tsv                    Malayalam name, English names, kind, Wikidata id
  lang/ml/assets/lexicon/ml_places.bin         the same names in the "LIPW" word list format (app)
  lang/ml/assets/lexicon/place_spellings_ml.txt  English spelling → Malayalam place (app)
  tests/data/places/place_cases.tsv             typed spelling → Malayalam (test set)
"""
import csv
import glob
import os
import re
import struct
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join(ROOT, "tools", "places")

# Wikidata kinds kept (P31). Schools, temples, hospitals and the like are left out.
KINDS = {
    "Q1195098": "ward",
    "Q56436498": "village",
    "Q2732840": "grama panchayat",
    "Q486972": "settlement",
    "Q3957": "town",
    "Q15284": "municipality",
    "Q6958514": "municipality",
    "Q6621940": "local body",
    "Q123705": "locality",
    "Q188509": "locality",
    "Q7680362": "taluk",
    "Q1149652": "district",
    "Q515": "city",
    "Q61443690": "post office",
    "Q61443591": "post office",
    "Q55488": "railway station",
}

# Words after the place's own name in a label ("കരീപ്ര ഗ്രാമ പഞ്ചായത്ത്" → കരീപ്ര).
ML_TAILS = [
    "ബ്രാഞ്ച് പോസ്റ്റ് ഓഫീസ്", "ഹെഡ് പോസ്റ്റ് ഓഫീസ്", "സബ് പോസ്റ്റ് ഓഫീസ്", "പോസ്റ്റ് ഓഫീസ്",
    "ഗ്രാമ പഞ്ചായത്ത്", "ഗ്രാമപഞ്ചായത്ത്", "പഞ്ചായത്ത്", "തീവണ്ടി നിലയം", "തീവണ്ടിനിലയം",
    "റെയിൽവേ സ്റ്റേഷൻ", "വാർഡ്", "മുനിസിപ്പാലിറ്റി", "നഗരസഭ", "ജില്ല", "താലൂക്ക്", "കോർപ്പറേഷൻ", "നഗരം",
]
EN_TAILS = re.compile(
    r"\s+(branch post office|head post office|sub post office|post office|grama panchayat|gram panchayat|panchayat|"
    r"railway station|ward|municipality|municipal corporation|corporation|district|taluk|city)$", re.I)

ML_WORD = re.compile(r"^[ഀ-ൿ]+$")
CHILLU = {"ന": "ൻ", "ല": "ൽ", "ര": "ർ", "ള": "ൾ", "ണ": "ൺ"}
VIRAMA = "്"


def modern(word: str) -> str:
    """Old chillu (consonant + ് + ZWJ) and a final consonant + ് written for a chillu → atomic chillu."""
    for c, ch in CHILLU.items():
        word = word.replace(c + VIRAMA + "‍", ch)
    if len(word) > 2 and word[-1] == VIRAMA and word[-2] in CHILLU and word[-3] != VIRAMA:
        word = word[:-2] + CHILLU[word[-2]]
    return word


def clean_ml(label: str):
    s = re.sub(r"\s*[\(,].*$", "", label).strip()
    for t in ML_TAILS:
        if s.endswith(t) and s != t:
            s = s[: -len(t)].strip()
    s = modern(s.replace("‌", ""))
    # Common slips in Wikidata labels: ള typed twice for ള്ള, a vowel sign typed twice (ുു).
    s = s.replace("ളള", "ള്ള")
    s = re.sub(r"([ാ-ൌൗ])\1+", r"\1", s)
    return s if ML_WORD.match(s) and len(s) > 1 else None


def clean_en(label: str) -> str:
    s = re.sub(r"\s*[\(,].*$", "", label or "").strip()
    return EN_TAILS.sub("", s).strip()


def key(en: str) -> str:
    """Typed form of an English name: lower case letters only ("Ras Al Khaimah" → rasalkhaimah)."""
    return re.sub(r"[^a-z]", "", en.lower())


def loose(k: str) -> str:
    """th → t, dh → d, zh → l, oo → u, ee → i, w → v, y between vowels dropped, doubled letters once."""
    for a, b in (("th", "t"), ("dh", "d"), ("zh", "l"), ("oo", "u"), ("ee", "i"), ("w", "v"), ("ph", "f")):
        k = k.replace(a, b)
    k = re.sub(r"(.)\1+", r"\1", k)
    return re.sub(r"(?<=[aeiou])y(?=[aeiou])", "", k)


def main(src: str) -> None:
    kinds = defaultdict(set)
    for f in glob.glob(os.path.join(src, "wikidata_types_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            k = KINDS.get(r["t"].rsplit("/", 1)[-1])
            if k:
                kinds[r["item"].rsplit("/", 1)[-1]].add(k)
    curated = set()  # (english, malayalam) from common_spellings.tsv: hand-checked, ranked like hand-made spellings
    places = {}  # ml → {"en": set, "kind": set, "ids": set}

    def add(ml_label, en_labels, kind, qid):
        ml = clean_ml(ml_label)
        if not ml:
            return
        p = places.setdefault(ml, {"en": set(), "kind": set(), "ids": set()})
        p["en"].update(e for e in (clean_en(x) for x in en_labels) if e)
        p["kind"].add(kind)
        if qid:
            p["ids"].add(qid)

    for f in glob.glob(os.path.join(src, "wikidata_places_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            qid = r["item"].rsplit("/", 1)[-1]
            if kinds.get(qid):
                add(r["ml"], [r["en"]] + r["aliases"].split("|"), sorted(kinds[qid])[0], qid)
    for name, kind in (("wikidata_districts.csv", "district"), ("wikidata_taluks.csv", "taluk"),
                       ("wikidata_countries.csv", "country")):
        for r in csv.DictReader(open(os.path.join(src, name), encoding="utf-8")):
            add(r["ml"], [r["en"]], kind, r["item"].rsplit("/", 1)[-1])
    seen = set()
    for r in csv.DictReader(open(os.path.join(src, "wikidata_named.csv"), encoding="utf-8")):
        if r["name"] in seen:  # the item with the most Wikipedia articles first
            continue
        seen.add(r["name"])
        add(r["ml"], [r["name"]], "india/gulf/world", r["item"].rsplit("/", 1)[-1])
    for line in open(os.path.join(HERE, "common_spellings.tsv"), encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            ml, en = line.rstrip("\n").split("\t")
            add(ml, en.split("|"), "common spelling", "")
            for e in en.split("|"):
                curated.add((e, clean_ml(ml)))

    with open(os.path.join(HERE, "places_ml.tsv"), "w", encoding="utf-8") as f:
        f.write("# Malayalam place names (Wikidata CC0 + Lipi's common spellings). Built by build_places.py.\n")
        f.write("# malayalam\tenglish\tkind\twikidata\n")
        for ml in sorted(places):
            p = places[ml]
            f.write(f"{ml}\t{'|'.join(sorted(p['en']))}\t{','.join(sorted(p['kind']))}\t{' '.join(sorted(p['ids']))}\n")
    entries = sorted(bytes(ord(c) - 0x0D00 for c in w) for w in places)
    out = os.path.join(ROOT, "lang", "ml", "assets", "lexicon", "ml_places.bin")
    with open(out, "wb") as f:
        f.write(b"LIPW" + struct.pack(">BI", 2, len(entries)))
        for b in entries:
            f.write(struct.pack(">B", len(b)) + b + struct.pack(">BB", 0, 0))

    # English spellings → Malayalam place ("payyanur" → പയ്യന്നൂർ): one-word English names and aliases only.
    spell = defaultdict(set)
    for ml, p in places.items():
        for e in p["en"]:
            if re.fullmatch(r"[A-Za-z]{3,}", e):
                spell[e.lower()].add(ml)
    with open(os.path.join(ROOT, "lang", "ml", "assets", "lexicon", "place_spellings_ml.txt"), "w", encoding="utf-8") as f:
        f.write("# English spelling of a place -> its Malayalam name(s) (tools/places, Wikidata CC0 + Lipi);"
                " * = hand-checked\n")
        for k in sorted(spell):
            # A hand-checked spelling comes first, marked "*".
            names = sorted(spell[k], key=lambda m: ((k, m) not in curated, m))
            f.write(f"{k}\t{'|'.join(('*' if (k, m) in curated else '') + m for m in names)}\n")

    # Test set: an English spelling that names exactly one Malayalam place → that place. The MVD bus stop spellings
    # come first (how people write them), then Wikidata's own English names.
    by_key = defaultdict(set)
    for ml, p in places.items():
        for e in p["en"]:
            if " " not in e:
                by_key[key(e)].add(ml)
    cases = {}
    noise = re.compile(r"\b(BUS|STAND|STOP|JN|JUNCTION|PVT|PRIVATE|KSRTC|KL\s*\d+|TEMPLE|COLLEGE|HOSPITAL|ROAD|"
                       r"CHURCH|SCHOOL|MASJID|BRIDGE|OFFICE|STATION|TOWN|MARKET)\b\.?", re.I)
    # A looser key finds the same place under another spelling (THALIPARAMBA / Taliparamba, PAYYANNUR / Payyanur).
    by_loose = defaultdict(set)
    for k, mls in by_key.items():
        by_loose[loose(k)].update(mls)
    for r in csv.DictReader(open(os.path.join(src, "mvd_bus_stops.csv"), encoding="utf-8", errors="replace")):
        name = noise.sub(" ", r["name"]).split()
        if len(name) != 1:
            continue
        typed = key(name[0])
        if len(by_key.get(typed, ())) == 1:
            cases[typed] = (next(iter(by_key[typed])), "mvd_same")
        elif typed not in by_key and len(by_loose.get(loose(typed), ())) == 1:
            cases[typed] = (next(iter(by_loose[loose(typed)])), "mvd_other")
    for line in open(os.path.join(HERE, "nikhil_cases.tsv"), encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            typed, want, who = line.rstrip("\n").split("\t")
            cases[typed] = (want, who)
    os.makedirs(os.path.join(ROOT, "tests", "data", "places"), exist_ok=True)
    with open(os.path.join(ROOT, "tests", "data", "places", "place_cases.tsv"), "w", encoding="utf-8") as f:
        f.write("# typed\texpected\tfrom (mvd_same = Kerala MVD bus stop spelling as in Wikidata, mvd_other = an MVD spelling Wikidata lacks, nikhil = Nikhil's cases, nikhil_2nd = his case where a real typed word (മതിൽ) stays 1st, lipi = common spellings for Nikhil to check)\n")
        for typed in sorted(cases):
            f.write(f"{typed}\t{cases[typed][0]}\t{cases[typed][1]}\n")
    print(f"{len(places)} places, {os.path.getsize(out)} bytes, {len(cases)} test cases")


if __name__ == "__main__":
    main(sys.argv[1])
