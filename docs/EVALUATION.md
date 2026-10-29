# Evaluation of the description parser

Only the **description parser** can be measured here, so only it is. No number in the application is invented: the
evaluation page shows stored results of real runs (with the number of examples, n) and shows "n = 0, nothing measured" before any run.

## What is measured

For every valid example of `backend/datasets/custom/attribute_samples.csv` the parser's output is compared with the labels:
per-attribute precision / recall / accuracy, **exact match** (all 12 attributes right), per-language results, **cross-language
agreement** (do the English, Hindi and Kannada versions of one face give the same attributes?) and the examples it got wrong.
A metric whose denominator is zero is shown as "-" (undefined), never as 0 %.

Run it: `python scripts/evaluate_parser.py --split dev|test|all [--only-reviewed] [--save]`, or as administrator on the web page
(the run is then stored with its data hash, parser version and date).

## Results (parser 1.2.0, vocabulary 1.1, data hash `272d0818be57`)

| Selection | n | Exact match | Micro precision | Micro recall |
|---|---|---|---|---|
| dev | 51 | 94.1 % (48/51) | 99.8 % | 99.5 % |
| test (**not a clean holdout any more - see history**) | 39 | 100 % (39/39) | 100 % | 100 % |
| all | 90 | 96.7 % (87/90) | 99.9 % | 99.7 % |

All: English 93.3 % (n=30), Hindi 100 % (30), Kannada 96.7 % (30) exact match; cross-language agreement 99.2 % over 30 faces.
**Skin colour** on its own (the attribute added in this version): 18 labelled examples, 18 read correctly, 0 wrong, and 0 skin
colours invented for the 72 older examples that never mention skin. These 18 are not independent evidence - see history item 4.
Still wrong (the same three as before the skin colour was added): `G04-kn` (a Kannada phrasing for "receding hairline" the word list lacks), `G10-en` ("about forty" - an age
without a unit), `G11-en` (hair that is "short at the sides but long on top": the parser does not flag the contradiction).

## How to read these numbers - please do

* **The examples and the word lists were written by the same person.** Scores measure "does the parser understand the author's
  phrasing", not accuracy on real witnesses, whose wording is messier. Expect much lower real-world performance.
* **The test split is not independent.** Both splits are by one author. The `split` column exists so an independently written
  test set can be added later.
* **Small n.** 90 examples; differences of a few points are noise.
* **The 18 skin-colour examples (G25-G30) are the weakest evidence of all.** The same person wrote them and the word lists, after
  trying similar sentences by hand. They show that the parser handles the author's own phrasing, nothing more.
* **Hindi and Kannada word lists and translations are unreviewed.** The 100 % Hindi figure says the *developer's* Hindi matches the
  *developer's* word list - it is not evidence that the parser understands native Hindi.
* Labels are the author's judgement of what each text says.

## History (so nobody has to trust a polished number)

1. First run of parser 1.0.0 on **dev** (n=42): exact match **71.4 %**. Failures showed real problems: the word "old" in "35 years
   **old**" was also read as the adjective "elderly" and cancelled the age (bug, fixed: an age expression now claims its own words);
   some Hindi / Kannada phrasings were missing (added to the word lists, e.g. "पीछे हटती हेयरलाइन", "त्रिकोणी", "X के आसपास",
   "ಹರೆಯ", "ಮಧ್ಯಮ ಉದ್ದ", and the stem `ಗಂಡಸ*` which missed the inflection ಗಂಡಸಿಗೆ). One *data* error was found and corrected: the Hindi text
   of group G05 never states a gender, so its "male" label was not supported by it. After this dev was 92.9 %.
2. The **test split was then run exactly once** (parser 1.0.0, untouched): exact match **93.3 %** (28/30), n=30. Two failures:
   one more data error (G14-hi, same kind as above) and one real, **dangerous** parser failure: Kannada
   "ಕನ್ನಡಕ ಧರಿಸುವುದಿಲ್ಲ" ("does not wear glasses") was read as *wears glasses*, because only some negative verb forms were listed.
3. Both were fixed after seeing them (negative Kannada verb endings `-ದಿಲ್ಲ` / `-ಲಿಲ್ಲ` are now recognised in general; the label text corrected)
   and the parser version became 1.1.0. Hence the test split now scores 100 % **but is no longer a held-out measurement**.
   The honest clean number for that split is the 93.3 % above.
4. **Skin colour added (parser 1.2.0, vocabulary 1.1).** Six new synthetic faces were written, each in English, Hindi and Kannada
   (G25-G30 = 18 rows; G25-G27 in `dev`, G28-G30 in `test`). They were run **once, before anything was changed**: all 18 were read
   correctly and the three known failures stayed as they were. That is a first-run result, but it is *not* a blind test (see above).
   Design decisions made while writing the word lists, before the rows existed (anticipated, not discovered by a failing test). They are
   about colour words that are **not** skin:
   "a black face mask", "a man in black / white", "बालों का रंग काला" (black hair), "काले रंग की जैकेट" (a black jacket) and
   "ಕಂದು ಬಣ್ಣದ ಕೂದಲು" (brown hair) must never become a skin colour. The rule: only skin words (skin, complexion,
   -skinned, त्वचा, ಚರ್ಮ, ಮೈಬಣ್ಣ ...) can own a skin colour, the bare word "face" cannot (except inside an *instruction* such as "make the face
   brown"), and the ambiguous word "light" is only read in "light skin / light complexion". The tests for all of these are in
   `backend/tests/test_parser.py`.

## Known weaknesses (all documented, none hidden)

Conflicts are only detected between statements within a few words of each other; negation is recognised within three words;
hair colour, eye colour, height, scars, tattoos and body build are outside the vocabulary and are listed as "not converted"
(so "black hair" is reported, never turned into anything). Skin colour has only three coarse values: *fair / pale / light* is read as
white, *wheatish / dusky / olive / tan / medium* as brown, *dark / black* as black - a witness meaning "dark brown" is therefore read as
black unless they say "brown", and the investigator is expected to correct it. A bare "a dark man" or "a fair man" is not read at all
(it could mean hair). The Hindi and Kannada word lists for skin colour are drafts like the rest; Hindi "रंग काला" is only read when the colour
clearly belongs to the person ("उसका रंग काला था"). Hindi and Kannada coverage is thin compared with English; the parser reads one person at a time.
