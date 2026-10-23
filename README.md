# lipi-data

The word lists inside **Lipi Manglish AI Keyboard** (Android) that are built from share-alike open data. They are
published here because their licences ask that changed versions are shared under the same licence. The keyboard app
itself is not open source; only these data files are.

Nothing typed by any user is in these files.

## `cc-by-sa-4.0/` — Creative Commons Attribution-ShareAlike 4.0 (`LICENSE.txt`)

| File | What it is | Built from |
|---|---|---|
| `ml_words.tsv` (`ml_words.bin`) | Malayalam words with `log10_count` (log10 of how often the word appears) and a flag (1 = offensive, not suggested first) | **Dakshina dataset v1.0** (Google Research; Malayalam Wikipedia text © Wikipedia contributors), **FrequencyWords** 2018 Malayalam (Hermit Dave, from OpenSubtitles) |
| `ml_spellings.tsv` (`ml_spellings.bin`) | Manglish spelling → Malayalam word, with how many people typed it that way | Dakshina romanization lexicon + Lipi's own chat spellings |
| `ml_pairs.txt`, `ml_triples.txt` | Which Malayalam word often comes next | Dakshina Malayalam Wikipedia sentences + Lipi's own chat pairs |
| `en_words.tsv` (`en_words.bin`) | English words with `log10_count` and an offensive flag | **FrequencyWords** 2018 English (Hermit Dave), filtered by SCOWL (MIT-style licence) |
| `hinglish_hi.tsv` | Hindi words in English letters, never autocorrected | Dakshina Hindi romanized sentences + Lipi's own list |

The `LICENSE-*.txt` files are the notices shipped with each list in the app.

## `odbl-1.0/` — Open Database License 1.0 (`LICENSE.txt`); contents under the Database Contents License 1.0

| File | What it is | Built from |
|---|---|---|
| `ml_dict_words.tsv` (`ml_dict_words.bin`) | Malayalam dictionary headwords, used as low-weight known words in suggestions | **Olam English–Malayalam** (Kailash Nadh) and **Datuk** Malayalam–Malayalam (K. J. Joseph; refined by Kailash Nadh), https://olam.in/open/ |
| `en_dict_words.txt` | English Olam headwords that are not in the main English list (never autocorrected away) | Olam |
| `build.py` | The script that makes these lists and the app's downloadable dictionary from Olam's files | — |

The full dictionary database the app downloads (`lipi-dictionary-v1.db.gz`) is at
https://lipi-fix.nikhilchappayil.workers.dev/v1/dictionary/lipi-dictionary-v1.db.gz (also ODbL 1.0).

## Credits

- Brian Roark, Lawrence Wolf-Sonkin, Christo Kirov, Sabrina J. Mielke, Cibu Johny, Işın Demirşahin and Keith Hall,
  "Processing South Asian Languages Written in the Latin Script: the Dakshina Dataset", LREC 2020.
  https://github.com/google-research-datasets/dakshina
- Hermit Dave, FrequencyWords. https://github.com/hermitdave/FrequencyWords
- Kevin Atkinson, SCOWL. https://github.com/en-wl/wordlist
- Kailash Nadh, Olam. https://olam.in
- K. J. Joseph, Datuk.

## Changes made

Text normalised (old chillu letters to the atomic ones), words counted and ranked, offensive words flagged (not
removed), very rare and broken entries removed, Lipi's own chat spellings added, dictionary meanings ranked and
shortened. Formats: `.tsv` are UTF-8 text with a header; `.bin` are the same lists in the app's compact format
(`LIPW` = Malayalam, one byte per letter as code point − 0x0D00; `LIPS` = spellings; `LIPE` = English).

## Updates

- This repository is updated on every Lipi release that changes one of these lists. Each update is one commit
  "Word lists for Lipi vX.Y.Z" and a tag `vX.Y.Z` matching the app version, so the files for any app version can
  be found.
- How an update is made (by the Lipi developer): the lists are rebuilt from the sources above with Lipi's build
  tools, exported with `tools/lipi-data/export.py`, copied over this repository, committed and tagged. The
  dictionary lists can be rebuilt by anyone with `odbl-1.0/build.py` from Olam's published files.
- Found a wrong word or spelling? Open an issue here, or email the address below.

Contact: Nikhil Annur, support@spoosa.com
