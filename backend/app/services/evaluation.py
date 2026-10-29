"""Evaluation of the description parser against labelled examples.

Only real runs produce numbers. Every figure here is computed from the examples passed in, and the
number of examples (n) is reported next to it. Nothing is estimated, rounded up or invented.
"""

from __future__ import annotations

from collections import defaultdict

from app.services.attributes import ATTRIBUTE_BY_KEY, ATTRIBUTE_KEYS
from app.services.description_parser.rules import LEXICON_MODULES, RuleBasedParser

MAX_FAILURES_LISTED = 25


def _ratio(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def evaluate_parser(rows: list[dict[str, str]], parser: RuleBasedParser) -> dict:
    """``rows`` are valid dataset rows (see custom_dataset.COLUMNS). Returns a JSON-serialisable metrics dict."""
    review = {m.LANGUAGE: m.REVIEW_STATUS for m in LEXICON_MODULES}
    tp, fp, fn, correct = (defaultdict(int) for _ in range(4))
    gold_n: dict[str, int] = defaultdict(int)
    per_language: dict[str, dict] = defaultdict(lambda: {"n": 0, "exact": 0, "attr_correct": 0, "attr_total": 0, "reviewed": 0})
    predictions_by_group: dict[str, dict[str, dict[str, str | None]]] = defaultdict(dict)
    failures: list[dict] = []
    exact_total = 0
    unrecognized_total = 0

    for row in rows:
        result = parser.parse(row["description_text"], row["language"])
        unrecognized_total += len(result.unrecognized)
        wrong = []
        for key in ATTRIBUTE_KEYS:
            gold = row[key] or None
            pred = result.attributes.get(key)
            if gold:
                gold_n[key] += 1
            if pred == gold:
                correct[key] += 1
                if gold:
                    tp[key] += 1
            else:
                if pred:
                    fp[key] += 1
                if gold:
                    fn[key] += 1
                wrong.append({"attribute": key, "expected": gold, "got": pred})
        lang = per_language[row["language"]]
        lang["n"] += 1
        lang["attr_total"] += len(ATTRIBUTE_KEYS)
        lang["attr_correct"] += len(ATTRIBUTE_KEYS) - len(wrong)
        lang["reviewed"] += 1 if row["translation_review_status"] == "reviewed" else 0
        if not wrong:
            lang["exact"] += 1
            exact_total += 1
        elif len(failures) < MAX_FAILURES_LISTED:
            failures.append({"sample_id": row["sample_id"], "language": row["language"], "wrong": wrong})
        if row["group_id"]:
            predictions_by_group[row["group_id"]][row["language"]] = dict(result.attributes)

    n = len(rows)
    per_attribute = []
    for key in ATTRIBUTE_KEYS:
        per_attribute.append(
            {
                "attribute": key, "label": ATTRIBUTE_BY_KEY[key].label, "n_gold": gold_n[key], "tp": tp[key], "fp": fp[key],
                "fn": fn[key], "accuracy": _ratio(correct[key], n), "precision": _ratio(tp[key], tp[key] + fp[key]),
                "recall": _ratio(tp[key], tp[key] + fn[key]),
            }  # fmt: skip
        )
    sum_tp, sum_fp, sum_fn = sum(tp.values()), sum(fp.values()), sum(fn.values())
    precisions = [a["precision"] for a in per_attribute if a["precision"] is not None]
    recalls = [a["recall"] for a in per_attribute if a["recall"] is not None]

    agree = total_slots = groups_used = 0
    for predictions in predictions_by_group.values():
        if len(predictions) < 2:
            continue
        groups_used += 1
        for key in ATTRIBUTE_KEYS:
            values = {p.get(key) for p in predictions.values()}
            total_slots += 1
            agree += 1 if len(values) == 1 else 0

    return {
        "n_examples": n,
        "exact_match": _ratio(exact_total, n),
        "micro_precision": _ratio(sum_tp, sum_tp + sum_fp),
        "micro_recall": _ratio(sum_tp, sum_tp + sum_fn),
        "macro_precision": round(sum(precisions) / len(precisions), 4) if precisions else None,
        "macro_recall": round(sum(recalls) / len(recalls), 4) if recalls else None,
        "per_attribute": per_attribute,
        "by_language": [
            {
                "language": code, "n": v["n"], "exact_match": _ratio(v["exact"], v["n"]),
                "mean_attribute_accuracy": _ratio(v["attr_correct"], v["attr_total"]),
                "lexicon_review_status": review.get(code, "unknown"), "translation_reviewed_n": v["reviewed"],
            }
            for code, v in sorted(per_language.items())
        ],  # fmt: skip
        "cross_language_agreement": {"groups": groups_used, "agreement": _ratio(agree, total_slots)},
        "unrecognized_per_example": round(unrecognized_total / n, 3) if n else None,
        "failures_listed": failures,
    }


CAVEATS = [
    "The examples were written by the same developer who wrote the parser's word lists, so the scores are optimistic and are NOT an estimate of performance on real witness statements.",
    "The 'dev' and 'test' splits come from the same author; the 'test' split is therefore not independent. It exists so an independently written test set can be dropped in later.",
    "Kannada and Hindi examples are developer-written translations and the word lists have not been reviewed by native speakers.",
    "Sample sizes are small: treat differences of a few percentage points as noise.",
]
