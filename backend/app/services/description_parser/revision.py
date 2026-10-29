"""Turn an editing instruction ("make the eyebrows thicker, add glasses") into attribute changes.

The result is a *plan*: every change says which attribute moves from what to what and which
words caused it. Nothing here touches an image - the sketch engines apply the plan.

Supported (and honest about the rest):
* explicit values in English / Hindi / Kannada   - "add glasses", "दाढ़ी हटाओ", "ಗಡ್ಡ ತೆಗೆಯಿರಿ", "curly hair"
* English comparatives                            - "thicker eyebrows", "longer hair", "broader nose", "rounder face", "darker skin"
* removal verbs                                   - "remove the beard and glasses"
Anything else is returned in ``ignored`` so the user can see exactly what was NOT applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.attributes import ATTRIBUTE_BY_KEY, STEP_BASELINES, Attributes
from app.services.description_parser import lexicon_en
from app.services.description_parser.base import Unrecognized
from app.services.description_parser.rules import REVISION_OWNER_ALIASES, RuleBasedParser


@dataclass
class RevisionChange:
    attribute: str
    label: str
    before: str | None
    after: str
    evidence: str
    kind: str  # set | step | remove
    note: str | None = None


@dataclass
class RevisionPlan:
    instruction: str
    language: str
    changes: list[RevisionChange] = field(default_factory=list)
    ignored: list[Unrecognized] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    new_attributes: Attributes = field(default_factory=dict)

    @property
    def target_attribute(self) -> str | None:
        return self.changes[0].attribute if self.changes else None

    @property
    def summary(self) -> str:
        parts = []
        for c in self.changes:
            spec = ATTRIBUTE_BY_KEY[c.attribute]
            parts.append(f"{c.label}: {spec.label_for(c.before)} -> {spec.label_for(c.after)}")
        return "; ".join(parts)


def interpret_revision(
    parser: RuleBasedParser, instruction: str, current: Attributes, language: str = "en"
) -> RevisionPlan:
    analysis = parser.analyze(instruction, language=language, mode="revision")
    result = analysis.result
    current = {k: v for k, v in current.items() if v}
    plan = RevisionPlan(instruction=instruction, language=language)
    changed: set[str] = set()
    extra_used: set[int] = set()
    details = {d.attribute: d for d in result.details}

    def label(attribute: str) -> str:
        return ATTRIBUTE_BY_KEY[attribute].label

    def value_label(attribute: str, value: str | None) -> str:
        return ATTRIBUTE_BY_KEY[attribute].label_for(value)

    # ---- 1. explicit values ("add glasses", "curly hair", "remove the beard") ----------------------
    for attribute, value in result.attributes.items():
        if not value:
            continue
        detail = details[attribute]
        before = current.get(attribute)

        if attribute == "apparent_gender":
            if before != value:
                plan.ignored.append(
                    Unrecognized(detail.evidence, "Apparent gender is not changed by instruction text - use the attribute editor.")
                )
            continue

        if attribute == "facial_hair" and detail.match_type == "negation":
            negated = analysis.negated_facial_hair
            if before and before != "none" and before in negated | ({"beard"} if "beard" in negated else set()):
                plan.changes.append(RevisionChange(attribute, label(attribute), before, "none", detail.evidence, "remove"))
                changed.add(attribute)
            elif not before or before == "none":
                plan.notes.append("The sketch already has no facial hair.")
            else:
                plan.ignored.append(
                    Unrecognized(
                        detail.evidence,
                        f"The sketch has '{value_label(attribute, before)}', so removing "
                        f"'{', '.join(sorted(negated))}' changes nothing.",
                    )
                )
            continue

        if before == value or (value == "none" and not before):
            plan.notes.append(f"{label(attribute)} is already '{value_label(attribute, value)}'.")
            continue
        kind = "remove" if value == "none" else "set"
        note = detail.note if detail.match_type == "number" else None
        plan.changes.append(RevisionChange(attribute, label(attribute), before, value, detail.evidence, kind, note))
        changed.add(attribute)

    # ---- 2. English comparatives ("thicker eyebrows", "broader nose") -------------------------------
    for i, token in enumerate(analysis.tokens):
        if i in analysis.used:
            continue
        steps = lexicon_en.COMPARATIVE_STEPS.get(token.norm, {})
        targets = lexicon_en.COMPARATIVE_TARGETS.get(token.norm, {})
        if not steps and not targets:
            continue
        anchor = parser.nearest_anchor(analysis, i, i + 1)
        extra_used.add(i)
        if anchor is None:
            plan.ignored.append(
                Unrecognized(token.raw, f"'{token.raw}' needs a feature to act on, for example '{token.raw} eyebrows'.")
            )
            continue
        span = range(anchor.start, anchor.end)
        phrase = analysis.text[
            analysis.tokens[min(i, anchor.start)].start : analysis.tokens[max(i, anchor.end - 1)].end
        ]
        extra_used.update(span)
        if anchor.kind != "noun":
            plan.ignored.append(Unrecognized(phrase, "This feature is not supported by the attribute vocabulary."))
            continue
        owned = set(anchor.payload)
        for attribute in list(owned):  # "make the FACE darker" colours the skin
            owned |= REVISION_OWNER_ALIASES.get(attribute, set())
        step_attrs = [a for a in steps if a in owned]
        target_attrs = [a for a in targets if a in owned]
        if step_attrs:
            attribute = step_attrs[0]
            if attribute in changed:
                plan.notes.append(f"'{phrase}' was skipped because {label(attribute)} was already set explicitly.")
                continue
            scale = ATTRIBUTE_BY_KEY[attribute].value_keys
            before = current.get(attribute)
            start_value = before or STEP_BASELINES[attribute]
            idx = scale.index(start_value)
            new_idx = max(0, min(len(scale) - 1, idx + steps[attribute]))
            if new_idx == idx:
                end = "maximum" if steps[attribute] > 0 else "minimum"
                plan.notes.append(f"{label(attribute)} is already at the {end} of the scale ('{value_label(attribute, start_value)}').")
                continue
            note = None
            if before is None:
                note = f"{label(attribute)} was not specified, so the step started from the default '{value_label(attribute, start_value)}'."
            plan.changes.append(
                RevisionChange(attribute, label(attribute), before, scale[new_idx], phrase, "step", note)
            )
            changed.add(attribute)
        elif target_attrs:
            attribute = target_attrs[0]
            value = targets[attribute]
            if attribute in changed:
                plan.notes.append(f"'{phrase}' was skipped because {label(attribute)} was already set explicitly.")
                continue
            before = current.get(attribute)
            if before == value:
                plan.notes.append(f"{label(attribute)} is already '{value_label(attribute, value)}'.")
                continue
            plan.changes.append(RevisionChange(attribute, label(attribute), before, value, phrase, "set"))
            changed.add(attribute)
        else:
            plan.ignored.append(
                Unrecognized(
                    phrase,
                    f"'{token.raw}' is not supported for this feature. Use an explicit value instead (for example 'round eyes').",
                )
            )

    # ---- 3. everything else is reported, never silently dropped --------------------------------------
    plan.ignored.extend(parser.unrecognized_for(analysis, extra_used))
    seen: set[str] = set()
    plan.ignored = [u for u in plan.ignored if not (u.text.casefold() in seen or seen.add(u.text.casefold()))]
    plan.warnings = [w for w in result.warnings if not w.startswith("No supported facial attributes")]
    plan.new_attributes = dict(current)
    for change in plan.changes:
        plan.new_attributes[change.attribute] = change.after
    return plan
