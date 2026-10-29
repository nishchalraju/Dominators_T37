# Datasets

**Nothing is downloaded by this project.** Three published face-sketch collections were investigated; each has access
conditions, so you must obtain them yourself. Until files are really present the web page shows **0 records** for them - that is
correct behaviour, not a bug. (Facts below were read from the official pages in October 2026; **verify current terms at the
source** before use. The CUFS detail page could not be fetched automatically, so its numbers come from a search-result snippet
and the overview page.)

| Dataset | What it is | Licence / access | Folder |
|---|---|---|---|
| **CUFS** - CUHK Face Sketch Database | 606 face-sketch pairs: 188 CUHK students, 123 AR, 295 XM2VTS faces. Artist-drawn sketches from frontal, neutral photos | Research use only, no commercial use, citation required. AR and XM2VTS photos carry **separate third-party terms** (Purdue AR database, Surrey XM2VTSDB) | `backend/datasets/external/cufs/` |
| **CUFSF** - CUHK Face Sketch FERET | 1,194 FERET persons; photos with lighting variation, sketches with shape exaggeration | Sketches from CUHK (research use, cite). **Photos must come from NIST Color FERET**: emailed account request + signed release agreement; no redistribution; limits on publishing images | `backend/datasets/external/cufsf/` |
| **UoM-SGFS** - University of Malta | Colour composite sketches made with EFIT-V software for 300 Color-FERET subjects (Sets A and B). Closest published data to real composite practice | Access through a request form; the page says it may be used as provided; cite Galea & Farrugia (BIOSIG 2016). FERET photos not included | `backend/datasets/external/uom_sgfs/` |

Citations: Wang & Tang, *Face Photo-Sketch Synthesis and Recognition*, IEEE TPAMI 2009; Zhang, Wang & Tang, *Coupled
Information-Theoretic Encoding for Face Photo-Sketch Recognition*, CVPR 2011; Galea & Farrugia, BIOSIG 2016.

## What these datasets can and cannot do for this project

They are **photo-to-sketch pairs, not text-to-sketch pairs**. They cannot teach a model to draw from a witness description.
They are useful for photo-sketch synthesis / recognition research, and UoM-SGFS for studying composite-style images. This
application performs **no** face recognition or matching, so it does not use them that way. The inspector only counts files and checks
that images open; it does not pair photos with sketches.

## Installing a dataset you are allowed to use

1. Obtain it under its own terms (links on the *Dataset and AI Evaluation* page and in `backend/datasets/metadata/external_datasets.json`).
2. Unpack it into the matching folder above. Never into `processed/` - derived files go there so originals stay verifiable.
3. As administrator press **Inspect** on the page, or run `python scripts/inspect_datasets.py`. The page then shows the real
   number of files, how many images open, and any broken file by name.

## The custom attribute dataset (included, synthetic)

`backend/datasets/custom/attribute_samples.csv`: **90 rows = 30 invented faces x 3 languages** (English original, Kannada and
Hindi translations). No real people, no photographs. It exists to test the parser and to show the format.

* Kannada and Hindi rows are **developer-written, not reviewed by native speakers** (`translation_review_status = unreviewed`).
  The application never changes that status by itself.
* Labels describe what the text *says*; an attribute not mentioned, or contradicted, is left empty.
* Only the last six faces (G25-G30, added with vocabulary 1.1) mention a **skin colour**, so only they carry a `skin_colour` label; the
  `skin_colour` column is blank for the first 24 faces (their "white" / "grey" is hair). A CSV written for vocabulary 1.0 has no such column
  and is still accepted - the validator says so and treats the skin colour as "not labelled".
* 6 English rows reference schematic images (`images/`), which are diagrams drawn by the project's renderer, not photos.
* `group_id` links the three translations of one face; the validator requires identical labels inside a group.
* Files: `attribute_samples.csv`, `attribute_samples.template.csv` (header + one example row), `attribute_sample.schema.json`
  (generated from the vocabulary), `README.md` (columns, review workflow).

Validate any file: `python scripts/validate_custom_dataset.py [your.csv]` (exit code 0 = valid; every problem names the row).
Review workflow for a translation: a qualified speaker corrects the text, then you set `translation_review_status=reviewed`,
`reviewer_id` and `reviewed_on`; the validator rejects a "reviewed" row without them.

Only add data you have the right to use (consented, licensed, or synthetic) and set `permission_status` honestly. Do not scrape
photographs of identifiable people.
