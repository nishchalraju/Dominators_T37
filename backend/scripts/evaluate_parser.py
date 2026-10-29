"""Run the description-parser evaluation and print the numbers (optionally store them in the database).

    python scripts/evaluate_parser.py --split dev
    python scripts/evaluate_parser.py --split all --save

Every figure comes from running the parser on the examples in datasets/custom/attribute_samples.csv.
"""

import _paths  # noqa: F401
import argparse
import json

from app.core.config import get_settings
from app.core.database import get_session_factory, init_db
from app.models import ModelEvaluation
from app.services import custom_dataset, evaluation
from app.services.description_parser import PARSER_NAME, PARSER_VERSION, get_parser


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all")
    parser.add_argument("--only-reviewed", action="store_true", help="only rows whose translation was reviewed by a human")
    parser.add_argument("--save", action="store_true", help="store the run in the model_evaluations table")
    parser.add_argument("--json", action="store_true", help="print the full metrics as JSON")
    args = parser.parse_args()

    report = custom_dataset.validate_file(get_settings().datasets_dir / "custom" / custom_dataset.CSV_NAME)
    if report.file_errors:
        raise SystemExit("Dataset file problem: " + "; ".join(report.file_errors))
    rows = [r.row for r in report.valid_rows if args.split == "all" or r.row["split"] == args.split]
    if args.only_reviewed:
        rows = [r for r in rows if r["translation_review_status"] in ("original", "reviewed")]
    if not rows:
        raise SystemExit("No valid examples for this selection - nothing evaluated.")

    metrics = evaluation.evaluate_parser(rows, get_parser())
    metrics["caveats"] = evaluation.CAVEATS
    if args.json:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    else:
        print(f"Parser {PARSER_NAME} {PARSER_VERSION} | split={args.split} | n={metrics['n_examples']} | dataset sha {report.content_sha256[:12]}")
        print(f"exact match {metrics['exact_match']}  micro precision {metrics['micro_precision']}  micro recall {metrics['micro_recall']}")
        for lang in metrics["by_language"]:
            print(f"  {lang['language']}: n={lang['n']} exact={lang['exact_match']} attr-accuracy={lang['mean_attribute_accuracy']} (word list: {lang['lexicon_review_status']})")
        print("cross-language agreement:", metrics["cross_language_agreement"])
        for f in metrics["failures_listed"]:
            print("  FAIL", f["sample_id"], [(w["attribute"], w["expected"], w["got"]) for w in f["wrong"]])
        print("\nCAVEATS:")
        for c in evaluation.CAVEATS:
            print("  -", c)
    if args.save:
        init_db()
        with get_session_factory()() as db:
            db.add(ModelEvaluation(evaluation_type="description_parser", target_name=PARSER_NAME, target_version=PARSER_VERSION,
                                   dataset_name="custom_attributes (synthetic demo)", dataset_version=report.content_sha256[:12],
                                   split=args.split, n_examples=len(rows), metrics=metrics, status="completed",
                                   notes="Run from the command line. Synthetic, developer-authored examples."))  # fmt: skip
            db.commit()
        print("Saved to the database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
