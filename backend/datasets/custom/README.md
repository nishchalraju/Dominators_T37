# Custom attribute dataset

`attribute_samples.csv` is a **small SYNTHETIC demo**: 90 rows = 30 invented faces x 3 languages (English, Kannada,
Hindi). It contains **no real people and no photographs of people**. It exists to test the description parser and to
show the format - it is not a research dataset.

* The English rows are the originals. The Kannada and Hindi rows are **developer-written translations that no native
  speaker has reviewed** (`translation_review_status = unreviewed`). Do not treat them as verified.
* Labels describe what each text *says*. An attribute the text does not mention (or states contradictorily) is left empty.
* Six English rows reference a **schematic drawing** in `images/` (made by the project's rule-based renderer from the labels).
  These are diagrams, not photos.

## Files

| File | Purpose |
|---|---|
| `attribute_samples.csv` | the demo data (UTF-8) |
| `attribute_samples.template.csv` | empty template with one example row - copy it to start your own file |
| `attribute_sample.schema.json` | JSON Schema of one row, generated from the vocabulary (`scripts/generate_dataset_schema.py`) |
| `images/` | optional schematic images referenced by `image_file` |

## Columns

`sample_id`, `group_id`, `split`, `language`, `description_text`, the twelve attributes (`apparent_gender`,
`age_description`, `skin_colour`, `face_shape`, `hair_length`, `hair_style`, `eyebrows`, `eye_shape`, `nose_shape`, `mouth_shape`,
`facial_hair`, `glasses`), `translation_review_status`, `reviewer_id`, `reviewed_on`, `annotation_method`,
`permission_status`, `image_file`, `notes`. Allowed values for every column are in the JSON Schema and in the
backend/README.

`skin_colour` (`white`, `brown`, `black`) was added with vocabulary 1.1 and is the one **optional attribute column**: a file written for
vocabulary 1.0 does not have it and is still valid (the validator prints a note, and the skin colour counts as "not labelled" in every row).
In this demo only the six faces G25-G30 mention a skin colour, so only they are labelled; the older 24 faces leave it blank
(the "white" and "grey" in them describe hair).

## Validate

```
python scripts/validate_custom_dataset.py                 # this folder's CSV
python scripts/validate_custom_dataset.py my_file.csv     # your own file
```

The validator checks the header, the vocabulary, languages/scripts, unique IDs, that rows sharing a `group_id` carry
identical labels, image paths (must stay inside this folder and open as real images) and the review workflow below.

## Translation review workflow (how a Kannada / Hindi row becomes "reviewed")

1. A qualified native speaker reads the row and corrects `description_text` if needed.
2. Set `translation_review_status` to `reviewed`, fill `reviewer_id` (a neutral ID, not a name) and `reviewed_on` (YYYY-MM-DD).
3. Run the validator. A `reviewed` row without reviewer or date is rejected.
4. `python scripts/evaluate_parser.py --only-reviewed` then evaluates only human-reviewed text (English originals + reviewed rows).

**Never mark rows as reviewed on someone's behalf.** The application never does this automatically.

## Adding real data

Only add data you have the right to use: consented, licensed, or synthetic. Set `permission_status` honestly
(`consent_documented` / `licensed_dataset` need documentation outside this repository). Do not scrape photographs of
identifiable people.
