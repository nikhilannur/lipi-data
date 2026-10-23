#!/usr/bin/env python3
"""Build Lipi's Malayalam Dictionary files (M8, docs/10-DICTIONARY.md).

Sources (both ODbL 1.0, https://olam.in/open/; the original downloads are in tools/dictionary/data/):
  enml.tar.gz   Olam English–Malayalam (Kailash Nadh): English word, part of speech, Malayalam meaning.
  datuk.tar.gz  Datuk Malayalam–Malayalam (K. J. Joseph; refined by Kailash Nadh): word, part of speech, meaning.
Optional, only to put the commonest meanings first: ml_words.tsv / en_words.tsv (word<TAB>count) from
tools/build_lexicon (our CC BY-SA word counts; only the order of meanings depends on them).

Usage:
  python3 -I tools/dictionary/build.py <out_dir> [ml_words.tsv] [en_words.tsv]

Outputs (all ODbL 1.0, as changed versions of Olam's data; published with LICENSE-dictionary.txt):
  lipi-dictionary.db(.gz)  SQLite, downloaded by the app on first open (not in the APK):
                           en(word, rank, pos, meaning)    English word (lower case) → Malayalam meanings
                           ml(word, rank, pos, meaning)    Malayalam word → English words (Olam read the other way)
                           datuk(word, rank, pos, meaning) Malayalam word → Malayalam meanings
  ml_dict_words.txt / .bin Malayalam headwords that are not in our word list (typing suggestions, low weight);
                           the .bin ("LIPW", like ml_words.bin) ships in the app
  en_dict_words.txt        English headwords that are not in our word list (fewer autocorrections)
"""
import collections
import csv
import gzip
import io
import math
import os
import re
import shutil
import sqlite3
import struct
import sys
import tarfile
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
VERSION = 1
MAX_EN = 8  # meanings kept per English word
MAX_ML = 6  # English words kept per Malayalam word
MAX_DATUK = 3  # meanings kept per Datuk word
MAX_DATUK_CHARS = 160
# Ranking English → Malayalam: log10(count) of the meaning, plus this when the meaning's own best English word is the
# one looked up (go ↔ പോകുക), or one of its 3 best.
MUTUAL_BEST = 1.5
MUTUAL_TOP3 = 0.7
COMMON_EN = 20000  # a Datuk meaning is cut after this many characters (at a comma when it can)

ML = re.compile(r"^[\u0D00-\u0D7F\u200C]+$")
# A real word starts with a vowel or a consonant, not a vowel sign, virama or anusvara (broken entries do).
ML_START = re.compile(r"^[\u0D05-\u0D14\u0D15-\u0D39\u0D7A-\u0D7F]")
EN_WORD = re.compile(r"^[a-z]{3,}$")

# Old chillu letters (consonant + virama + ZWJ) → the atomic chillus our word lists use.
CHILLU = [("ന്‍റ", "ന്റ"), ("ന്‍", "ൻ"), ("ര്‍", "ർ"), ("ല്‍", "ൽ"), ("ള്‍", "ൾ"),
          ("ണ്‍", "ൺ"), ("ക്‍", "ൿ"), ("ൌ", "ൗ")]


def norm(s):
    s = unicodedata.normalize("NFC", s.strip())
    for a, b in CHILLU:
        s = s.replace(a, b)
    return s.replace("‍", "").strip()


# Part of speech → a short code the app shows in Malayalam (n നാമം, v ക്രിയ, a വിശേഷണം, adv ക്രിയാവിശേഷണം,
# pron സർവനാമം); anything else is kept as "" (no label).
EN_POS = {"n": "n", "v": "v", "a": "a", "adv": "adv", "pron": "pron", "propn": "n", "auxv": "v"}
ML_POS = {"നാ.": "n", "ക്രി.": "v", "വി.": "a", "സ.നാ.": "pron"}


def en_pos(t):
    return EN_POS.get(t.strip("{}"), "")


def ml_pos(t):
    t = norm(t.strip("{}").strip('"'))
    return ML_POS.get(t.split(" ")[0] if t else "", "")


def read_tsv(name):
    with tarfile.open(os.path.join(DATA, name + ".tar.gz")) as tar:
        member = next(m for m in tar.getmembers() if m.isfile())
        text = tar.extractfile(member).read().decode("utf-8")
    csv.field_size_limit(10 ** 8)
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    return [r for r in rows[1:] if len(r) == 3]


def counts(path):
    out = {}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2 and p[1].isdigit():
                    out[p[0]] = int(p[1])
    return out


def main():
    out = sys.argv[1]
    ml_count = counts(sys.argv[2] if len(sys.argv) > 2 else None)
    en_count = {k.lower(): v for k, v in counts(sys.argv[3] if len(sys.argv) > 3 else None).items()}
    os.makedirs(out, exist_ok=True)

    def ml_score(key, meaning):
        # Common single words first, then short phrases; Olam's own order breaks ties. A meaning whose own best
        # English word is this one comes first ("go" → പോകുക, whose best English is "go", before ചെയ്യുക = "do").
        words = meaning.split(" ")
        c = ml_count.get(meaning, 0) if len(words) == 1 else 0
        tops = best_english.get(meaning, ())
        mutual = MUTUAL_BEST if tops[:1] == (key,) else MUTUAL_TOP3 if key in tops else 0.0
        return (-(math.log10(1 + c) + mutual), len(words), len(meaning))

    en = collections.defaultdict(list)  # english → [(pos, meaning)]
    back = collections.defaultdict(list)  # malayalam word → [(pos, English)]
    for word, types, meaning in read_tsv("enml"):
        key = word.strip().lower()
        m = norm(meaning).strip(" .,;")
        if not key or not m:
            continue
        pos = en_pos(types)
        if (pos, m) not in en[key]:
            en[key].append((pos, m))
        if ML.match(m):
            english = word.strip()
            if (pos, english) not in back[m]:
                back[m].append((pos, english))

    def english_rank(word):
        return sorted(enumerate(back[word]),
                      key=lambda ie: (-math.log10(1 + en_count.get(ie[1][1].lower(), 0)), len(ie[1][1]), ie[0]))

    best_english = {w: tuple(e[1][1].lower() for e in english_rank(w)[:3]) for w in back}

    def short(m):
        if len(m) <= MAX_DATUK_CHARS:
            return m
        cut = m.rfind(",", 0, MAX_DATUK_CHARS)
        return (m[:cut] if cut > 40 else m[:MAX_DATUK_CHARS]).rstrip(" ,") + "…"

    datuk = collections.defaultdict(list)
    for word, types, meaning in read_tsv("datuk"):
        if "­" in word or "­" in meaning:  # broken entries of the old ASCII digitisation
            continue
        head = norm(re.sub(r"\d+$", "", word.split(",")[0])).strip(" -")
        m = short(norm(meaning).strip(' "'))
        if not ML.match(head) or not ML_START.match(head) or not m:
            continue
        if len(datuk[head]) < MAX_DATUK and (ml_pos(types), m) not in datuk[head]:
            datuk[head].append((ml_pos(types), m))

    db_path = os.path.join(out, "lipi-dictionary.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE en(word TEXT NOT NULL, rank INTEGER NOT NULL, pos TEXT NOT NULL, meaning TEXT NOT NULL,
                        PRIMARY KEY (word, rank)) WITHOUT ROWID;
        CREATE TABLE ml(word TEXT NOT NULL, rank INTEGER NOT NULL, pos TEXT NOT NULL, meaning TEXT NOT NULL,
                        PRIMARY KEY (word, rank)) WITHOUT ROWID;
        CREATE TABLE datuk(word TEXT NOT NULL, rank INTEGER NOT NULL, pos TEXT NOT NULL, meaning TEXT NOT NULL,
                           PRIMARY KEY (word, rank)) WITHOUT ROWID;
    """)
    db.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("version", str(VERSION)),
        ("licence", "ODbL 1.0: changed versions of Olam English-Malayalam (Kailash Nadh) and Datuk "
                    "(K. J. Joseph; refined by Kailash Nadh), https://olam.in/open/"),
    ])
    n_en = n_ml = n_dk = 0
    for key in sorted(en):
        ranked = sorted(enumerate(en[key]), key=lambda im: (ml_score(key, im[1][1]), im[0]))[:MAX_EN]
        db.executemany("INSERT INTO en VALUES (?, ?, ?, ?)",
                       [(key, r, pos, m) for r, (_, (pos, m)) in enumerate(ranked)])
        n_en += 1
    for word in sorted(back):
        ranked = english_rank(word)
        db.executemany("INSERT INTO ml VALUES (?, ?, ?, ?)",
                       [(word, r, pos, e) for r, (_, (pos, e)) in enumerate(ranked[:MAX_ML])])
        n_ml += 1
    for word in sorted(datuk):
        db.executemany("INSERT INTO datuk VALUES (?, ?, ?, ?)",
                       [(word, r, pos, m) for r, (pos, m) in enumerate(datuk[word])])
        n_dk += 1
    db.commit()
    db.execute("VACUUM")
    db.close()
    with open(db_path, "rb") as src, gzip.open(db_path + ".gz", "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst)

    header = ("# {what}\n# ODbL 1.0 (LICENSE-dictionary.txt): words from Olam English-Malayalam (Kailash Nadh) and Datuk "
              "(K. J. Joseph),\n# https://olam.in/open/, changed by tools/dictionary/build.py (Lipi). One word per line.\n")
    ml_words = sorted({w for w in list(datuk) + list(back)
                       if ML.match(w) and ML_START.match(w) and w not in ml_count and len(w) > 1})
    with open(os.path.join(out, "ml_dict_words.txt"), "w", encoding="utf-8") as f:
        f.write(header.format(what="Malayalam dictionary words not in Lipi's word list (typing suggestions, low weight)"))
        f.writelines(w + "\n" for w in ml_words)
    # The same "LIPW" format as ml_words.bin (tools/build_lexicon), so the app keeps 120k words in one byte array:
    # one byte per letter (code point − 0x0D00), sorted, no count (these are rare words), no flags.
    entries = sorted((bytes(ord(c) - 0x0D00 for c in w), w)
                     for w in ml_words if all(0x0D00 <= ord(c) <= 0x0D7F for c in w) and len(w) < 256)
    with open(os.path.join(out, "ml_dict_words.bin"), "wb") as f:
        f.write(b"LIPW" + struct.pack(">BI", 2, len(entries)))
        for b, _ in entries:
            f.write(struct.pack(">B", len(b)) + b + struct.pack(">BB", 0, 0))
    # Only words that cannot be a slip of a common word: a dictionary word one letter away from one of the 20,000
    # commonest English words ("thw" / "the") would stop autocorrect fixing that typo, so it is left out.
    common = {w for w, _ in sorted(en_count.items(), key=lambda wc: -wc[1])[:COMMON_EN]}

    def near_common(w):
        letters = "abcdefghijklmnopqrstuvwxyz"
        splits = [(w[:i], w[i:]) for i in range(len(w) + 1)]
        edits = {a + b[1:] for a, b in splits if b}
        edits |= {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
        edits |= {a + c + b[1:] for a, b in splits if b for c in letters}
        edits |= {a + c + b for a, b in splits for c in letters}
        edits.discard(w)
        return any(e in common for e in edits)

    with open(os.path.join(HERE, "../../ime/src/main/assets/lexicon/en_typos.txt"), encoding="utf-8") as f:
        typo_list = {l.split("\t")[0].strip().lower() for l in f if "\t" in l}  # teh, recieve …: keep fixing them
    en_words = sorted({k for k in en if EN_WORD.match(k) and k not in en_count and k not in typo_list
                       and not near_common(k)})
    with open(os.path.join(out, "en_dict_words.txt"), "w", encoding="utf-8") as f:
        f.write(header.format(what="English dictionary words not in Lipi's word list (never autocorrected away)"))
        f.writelines(w + "\n" for w in en_words)

    print(f"English words: {n_en:,}  Malayalam → English: {n_ml:,}  Datuk words: {n_dk:,}")
    print(f"db: {os.path.getsize(db_path):,} bytes, gz: {os.path.getsize(db_path + '.gz'):,} bytes")
    print(f"ml_dict_words: {len(ml_words):,}  en_dict_words: {len(en_words):,}")


if __name__ == "__main__":
    main()
