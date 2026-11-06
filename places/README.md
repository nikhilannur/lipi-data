# places/ — Malayalam place names in Lipi's suggestions

| File | What it is | Source and licence |
|---|---|---|
| `places_ml.tsv` | 10,272 Kerala, India and Gulf place names in Malayalam, with their English names, kind and Wikidata id | **Wikidata** (CC0 1.0) + Lipi's `common_spellings.tsv` |
| `place_spellings_ml.txt` | English spelling → Malayalam place, as shipped in the app (`*` = hand-checked) | as above |
| `common_spellings.tsv` | Spellings Malayalis use that Wikidata's label lacks (ബാംഗ്ലൂർ, തൃശൂർ) | Lipi's own |
| `build_places.py` | Builds the lists (a copy of `tools/places/build_places.py` in the app repo) | — |
| `sources/wikidata_*.csv` | Raw Wikidata query results, downloaded 6 Nov 2026 (query.wikidata.org) | CC0 1.0 |
| `sources/mvd_bus_stops.csv` | 3,312 Kerala bus stops (English names): used only for the test set's spellings, not shipped | Kerala Motor Vehicles Department, obtained under the RTI Act |

Not used yet: LGD / Census (downloads behind a captcha form) and OpenStreetMap (Overpass refused the connection).

To change a place: edit `common_spellings.tsv` (or fix the label on Wikidata), run
`python3 tools/places/build_places.py <sources dir>` in the app repo, and ship the new `ml_places.bin` /
`place_spellings_ml.txt` in the next app version.
