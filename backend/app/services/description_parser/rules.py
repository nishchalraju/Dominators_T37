"""Rule-based multilingual description parser (English / Kannada / Hindi).

How it works (read top to bottom):

1. ``tokenize``       - split the text into words, remembering where each word was.
2. find matches       - look every word / phrase up in the three lexicons.
                        Kinds: noun, blocker, adjective, standalone, pronoun.
3. resolve overlaps   - the longest phrase wins ("short beard" beats "short" + "beard").
4. bind adjectives    - an adjective such as "thick" only counts when the nearest noun
                        (within a few words, same sentence) is one it can describe
                        ("thick" + "eyebrows" -> eyebrows=thick).
5. negation           - "no glasses", "बिना दाढ़ी", "ಗಡ್ಡ ಇಲ್ಲ" -> none.
6. collect + conflict - two different values for one attribute are NOT guessed between:
                        the attribute stays empty and a conflict is reported.
7. unrecognised       - everything that was not understood is reported back.

Nothing here is a statistical model, so there is no "confidence score". The output is
a list of *candidate* values with the exact words that triggered each one.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

from app.services.attributes import ATTRIBUTE_KEYS, LANGUAGE_LABELS
from app.services.description_parser import age as age_rules
from app.services.description_parser import lexicon_en, lexicon_hi, lexicon_kn
from app.services.description_parser.base import (
    Conflict,
    DescriptionParser,
    ExtractedValue,
    ParseResult,
    Token,
    Unrecognized,
)
from app.services.description_parser.normalize import (
    HARD_BOUNDARY_CHARS,
    SCRIPT_TO_LANGUAGE,
    SOFT_BOUNDARY_CHARS,
    detect_scripts,
    normalize_token,
    sentence_ids,
    tokenize,
)

PARSER_NAME = "rule_based_multilingual"
# Bump this whenever a lexicon or rule changes - evaluation results are tied to it.
#   1.0.0  first version        1.1.0  Kannada negation suffixes, two Hindi label fixes
#   1.2.0  skin colour (white / brown / black) in English, Hindi and Kannada; "darker" / "lighter" comparatives
PARSER_VERSION = "1.2.0"

BINDING_WINDOW = 4  # an adjective may be at most 4 words away from its noun
NEGATION_WINDOW = 3  # a negator may be at most 3 words away from what it negates
MAX_UNRECOGNIZED = 25
FACIAL_HAIR_TYPES = ("stubble", "mustache", "goatee", "beard")
# A hair word such as "bald" or "curly" may sit next to "head"/"face" ("bald head"): that noun is then understood too.
OWNER_ALIASES: dict[str, set[str]] = {"hair_length": {"face_shape"}, "hair_style": {"face_shape"}}
# In an INSTRUCTION ("make the face brown", "make the face darker") the face is the thing being coloured, so it may own
# a skin colour. In a witness DESCRIPTION it may not: "a black face mask" is not a skin colour.
REVISION_OWNER_ALIASES: dict[str, set[str]] = {"face_shape": {"skin_colour"}}
LEXICON_MODULES: tuple[ModuleType, ...] = (lexicon_en, lexicon_hi, lexicon_kn)


# --------------------------------------------------------------------------- patterns
@dataclass(frozen=True)
class Pattern:
    tokens: tuple[str, ...]
    prefix: tuple[bool, ...]
    length: int  # characters - used as "specificity" when two patterns overlap


def compile_pattern(phrase: str) -> Pattern:
    tokens, prefix = [], []
    for part in phrase.split():
        prefix.append(part.endswith("*"))
        tokens.append(normalize_token(part.rstrip("*")))
    return Pattern(tuple(tokens), tuple(prefix), sum(len(t) for t in tokens) + len(tokens) - 1)


class PatternIndex:
    """Looks up the patterns that could start at a given word."""

    def __init__(self, entries: list[tuple[Pattern, Any]]):
        self._exact: dict[str, list[tuple[Pattern, Any]]] = defaultdict(list)
        self._prefix: list[tuple[Pattern, Any]] = []
        for pattern, payload in entries:
            if pattern.prefix[0]:
                self._prefix.append((pattern, payload))
            else:
                self._exact[pattern.tokens[0]].append((pattern, payload))

    def candidates(self, norm: str):
        yield from self._exact.get(norm, ())
        for item in self._prefix:
            if norm.startswith(item[0].tokens[0]):
                yield item


class CompiledLexicon:
    def __init__(self, module: ModuleType):
        self.module = module
        self.language: str = module.LANGUAGE
        self.review_status: str = module.REVIEW_STATUS
        self.exceptions = tuple(normalize_token(e) for e in module.PREFIX_EXCEPTIONS)

        adjectives: list[tuple[Pattern, Any]] = []
        for attribute, by_value in module.ADJECTIVES.items():
            for value, phrases in by_value.items():
                adjectives.extend((compile_pattern(p), (attribute, value)) for p in phrases)

        self.indexes: dict[str, PatternIndex] = {
            "noun": PatternIndex([(compile_pattern(p), attrs) for p, attrs in module.NOUNS.items()]),
            "blocker": PatternIndex([(compile_pattern(p), None) for p in module.BLOCKERS]),
            "adjective": PatternIndex(adjectives),
            "standalone": PatternIndex([(compile_pattern(p), a) for p, a in module.STANDALONE.items()]),
            "pronoun": PatternIndex([(compile_pattern(p), a) for p, a in module.PRONOUNS.items()]),
        }
        self.negators_before = [compile_pattern(p) for p in module.NEGATORS_BEFORE]
        self.negators_after = [compile_pattern(p) for p in module.NEGATORS_AFTER]
        self.removal_verbs = [compile_pattern(p) for p in module.REMOVAL_VERBS]
        self.instruction_words = [compile_pattern(p) for p in module.INSTRUCTION_WORDS]
        self.verb_final: bool = module.VERB_FINAL
        self.contrast = [compile_pattern(p) for p in module.CONTRAST]
        self.conjunctions = [compile_pattern(p) for p in module.CONJUNCTIONS]
        self.negator_suffixes = tuple(normalize_token(x) for x in module.NEGATOR_SUFFIXES)
        self.stop_exact = frozenset(normalize_token(w) for w in module.STOPWORDS)
        self.stop_prefixes = tuple(normalize_token(w) for w in module.STOP_PREFIXES)

    def token_is(self, norm: str, patterns: list[Pattern]) -> bool:
        for pattern in patterns:
            if _token_matches(norm, pattern.tokens[0], pattern.prefix[0], self.exceptions):
                return True
        return False

    def has_negative_ending(self, norm: str) -> bool:
        return any(norm.endswith(suffix) and len(norm) > len(suffix) for suffix in self.negator_suffixes)

    def is_stopword(self, norm: str) -> bool:
        return norm in self.stop_exact or any(norm.startswith(p) for p in self.stop_prefixes)


def _token_matches(norm: str, pattern_token: str, is_prefix: bool, exceptions: tuple[str, ...]) -> bool:
    if norm == pattern_token:
        return True
    return is_prefix and norm.startswith(pattern_token) and not any(norm.startswith(e) for e in exceptions)


# --------------------------------------------------------------------------- data classes
@dataclass
class Match:
    kind: str  # noun | blocker | adjective | standalone | pronoun
    start: int  # token index (inclusive)
    end: int  # token index (exclusive)
    length: int
    payload: Any
    language: str
    inflected: bool


@dataclass
class Candidate:
    attribute: str
    value: str
    evidence: str
    language: str
    match_type: str
    note: str | None = None


@dataclass
class Analysis:
    """Everything the parser worked out. The revision interpreter reuses it."""

    text: str
    mode: str
    tokens: list[Token]
    sentence: list[int]
    matches: list[Match]
    used: set[int]
    result: ParseResult
    negated_facial_hair: set[str] = field(default_factory=set)
    weak: set[int] = field(default_factory=set)  # tokens that were only pronouns (weak evidence)
    clause: list[int] = field(default_factory=list)
    skipped: list[Unrecognized] = field(default_factory=list)

    @property
    def nouns(self) -> list[Match]:
        return [m for m in self.matches if m.kind == "noun"]


# --------------------------------------------------------------------------- parser
class RuleBasedParser(DescriptionParser):
    name = PARSER_NAME
    version = PARSER_VERSION

    def __init__(self) -> None:
        self.lexicons = [CompiledLexicon(m) for m in LEXICON_MODULES]

    # ----- public API ------------------------------------------------------
    def parse(self, text: str, language: str = "en") -> ParseResult:
        return self.analyze(text, language=language).result

    def unrecognized_for(self, analysis: Analysis, extra_used: set[int]) -> list[Unrecognized]:
        """Re-run the 'what was not understood' step after a caller consumed more words."""
        return self._unrecognized(
            analysis.text,
            analysis.tokens,
            analysis.clause,
            analysis.used | extra_used,
            analysis.weak,
            analysis.mode,
            analysis.skipped,
        )

    def clause_ids(self, tokens: list[Token]) -> list[int]:
        return self._clause_ids(tokens)

    def nearest_anchor(self, analysis: Analysis, start: int, end: int) -> Match | None:
        anchors = [m for m in analysis.matches if m.kind in ("noun", "blocker")]
        return self._nearest_anchor(start, end, anchors, analysis.sentence, analysis.clause)

    def lexicon_status(self) -> dict[str, str]:
        return {lex.language: lex.review_status for lex in self.lexicons}

    def analyze(self, text: str, *, language: str = "en", mode: str = "description") -> Analysis:
        """``mode`` is 'description' (witness text) or 'revision' (an edit instruction)."""
        tokens = tokenize(text)
        sentence = sentence_ids(tokens)
        raw_matches = self._find_matches(tokens, sentence)
        matches = self._resolve_overlaps(raw_matches)
        # "35 years OLD": the words of an age expression belong to it, not to the word lists
        # (otherwise "old" would also be read as the adjective 'elderly' and clash with the number).
        age_hits = age_rules.find_age_expressions(tokens, sentence, list(LEXICON_MODULES))
        age_tokens = {i for hit in age_hits for i in range(hit.start, hit.end)}
        if age_tokens:
            matches = [m for m in matches if not (set(range(m.start, m.end)) & age_tokens)]

        clause = self._clause_ids(tokens)
        scope = self._removal_scope(tokens, sentence) if mode == "revision" else {}
        candidates: list[Candidate] = []
        skipped: list[Unrecognized] = []  # understood but cannot be turned into a value
        used: set[int] = set()
        weak: set[int] = set()
        negated_facial_hair: set[str] = set()

        self._collect_standalone(text, tokens, sentence, clause, matches, scope, candidates, skipped, used, weak, mode)
        self._collect_adjectives(text, tokens, sentence, clause, matches, scope, candidates, skipped, used, mode)
        self._collect_ages(text, tokens, age_hits, candidates, skipped, used)

        attributes, details, conflicts, notes = self._aggregate(candidates, skipped, negated_facial_hair)
        unrecognized = self._unrecognized(text, tokens, clause, used, weak, mode, skipped)
        warnings = self._warnings(text, language, details, conflicts, attributes, notes)

        result = ParseResult(
            attributes=attributes,
            details=details,
            unrecognized=unrecognized,
            conflicts=conflicts,
            warnings=warnings,
            declared_language=language,
            detected_scripts=detect_scripts(text),
            parser_name=self.name,
            parser_version=self.version,
            lexicon_status=self.lexicon_status(),
        )
        return Analysis(text, mode, tokens, sentence, matches, used, result, negated_facial_hair, weak, clause, skipped)

    # ----- step 2: find matches ---------------------------------------------
    def _find_matches(self, tokens: list[Token], sentence: list[int]) -> list[Match]:
        found: list[Match] = []
        for lex in self.lexicons:
            for kind, index in lex.indexes.items():
                for i, tok in enumerate(tokens):
                    for pattern, payload in index.candidates(tok.norm):
                        inflected = self._match_at(pattern, tokens, sentence, i, lex.exceptions)
                        if inflected is None:
                            continue
                        found.append(
                            Match(kind, i, i + len(pattern.tokens), pattern.length, payload, lex.language, inflected)
                        )
        return found

    @staticmethod
    def _match_at(
        pattern: Pattern, tokens: list[Token], sentence: list[int], i: int, exceptions: tuple[str, ...]
    ) -> bool | None:
        """None = no match; otherwise whether an inflected (prefix) match was needed."""
        n = len(pattern.tokens)
        if i + n > len(tokens):
            return None
        inflected = False
        for k in range(n):
            if sentence[i + k] != sentence[i]:
                return None  # a phrase never spans a sentence boundary
            norm = tokens[i + k].norm
            if norm == pattern.tokens[k]:
                continue
            if _token_matches(norm, pattern.tokens[k], pattern.prefix[k], exceptions):
                inflected = True
                continue
            return None
        return inflected

    # ----- step 3: longest match wins ---------------------------------------
    @staticmethod
    def _resolve_overlaps(matches: list[Match]) -> list[Match]:
        by_span: dict[tuple[int, int], list[Match]] = defaultdict(list)
        for m in matches:
            by_span[(m.start, m.end)].append(m)
        groups = []
        for span, group in by_span.items():
            best = max(m.length for m in group)
            groups.append((span, best, [m for m in group if m.length == best]))
        # more words first, then more specific, then earlier in the text
        groups.sort(key=lambda g: (-(g[0][1] - g[0][0]), -g[1], g[0][0]))
        taken: set[int] = set()
        selected: list[Match] = []
        for (start, end), _best, group in groups:
            span = set(range(start, end))
            if span & taken:
                continue
            taken |= span
            selected.extend(group)
        selected.sort(key=lambda m: (m.start, m.kind))
        return selected

    # ----- helpers -------------------------------------------------------------
    def _is_any(self, norm: str, attr: str) -> bool:
        return any(lex.token_is(norm, getattr(lex, attr)) for lex in self.lexicons)

    def _is_negator_after(self, norm: str) -> bool:
        return self._is_any(norm, "negators_after") or any(lex.has_negative_ending(norm) for lex in self.lexicons)

    def _is_stopword(self, norm: str) -> bool:
        return any(lex.is_stopword(norm) for lex in self.lexicons)

    @staticmethod
    def _slice(text: str, tokens: list[Token], first: int, last: int) -> str:
        return text[tokens[first].start : tokens[last].end]

    def _clause_ids(self, tokens: list[Token]) -> list[int]:
        """Clause number of every word. Commas, sentence punctuation and conjunctions
        ("and", "और", "ಮತ್ತು") start a new clause; a conjunction is a clause of its own."""
        clause_of: list[int] = []
        current = 0
        for i, tok in enumerate(tokens):
            boundary = i > 0 and any(c in HARD_BOUNDARY_CHARS or c in SOFT_BOUNDARY_CHARS for c in tok.sep)
            is_conj = self._is_any(tok.norm, "conjunctions")
            if boundary or is_conj:
                current += 1
            clause_of.append(current)
            if is_conj:
                current += 1
        return clause_of

    def _removal_scope(self, tokens: list[Token], sentence: list[int]) -> dict[int, int]:
        """For instructions: token index -> index of the removal verb that covers it.

        English puts the verb first ("remove the beard and glasses" - covers everything up to the
        next action verb); Hindi / Kannada put it last ("दाढ़ी और चश्मा हटाओ" - covers what comes before).
        """
        scope: dict[int, int] = {}
        limit = 8  # words
        for v, tok in enumerate(tokens):
            for lex in self.lexicons:
                if not lex.token_is(tok.norm, lex.removal_verbs):
                    continue
                step = -1 if lex.verb_final else 1
                j = v + step
                while 0 <= j < len(tokens) and abs(j - v) <= limit and sentence[j] == sentence[v]:
                    norm = tokens[j].norm
                    if any(
                        other.token_is(norm, other.removal_verbs + other.instruction_words + other.contrast)
                        for other in self.lexicons
                    ):
                        break
                    scope.setdefault(j, v)
                    j += step
                break
        return scope

    def _negation(
        self, tokens: list[Token], sentence: list[int], start: int, end: int, scope: dict[int, int]
    ) -> tuple[bool, set[int]]:
        """Is the phrase at tokens[start:end] negated? Returns the negator's token indices."""
        # instruction mode: "remove the beard", "दाढ़ी हटाओ"
        for i in range(start, end):
            if i in scope:
                return True, {scope[i]}
        # words BEFORE the phrase: "no beard", "बिना दाढ़ी"
        for j in range(start - 1, max(-1, start - 1 - NEGATION_WINDOW), -1):
            if sentence[j] != sentence[start]:
                break
            norm = tokens[j].norm
            if self._is_any(norm, "contrast"):
                break
            if self._is_any(norm, "negators_before"):
                return True, {j}
        # words AFTER the phrase: "दाढ़ी नहीं", "ಗಡ್ಡ ಇಲ್ಲ"
        for j in range(end, min(len(tokens), end + NEGATION_WINDOW)):
            if sentence[j] != sentence[end - 1]:
                break
            norm = tokens[j].norm
            if self._is_any(norm, "contrast"):
                break
            if self._is_negator_after(norm):
                return True, {j}
        return False, set()

    # ----- step 4a: standalone phrases and pronouns -----------------------------------
    def _collect_standalone(
        self, text, tokens, sentence, clause, matches, scope, candidates, skipped, used, weak, mode
    ) -> None:  # noqa: ANN001
        nouns = [m for m in matches if m.kind == "noun"]
        for m in matches:
            if m.kind not in ("standalone", "pronoun"):
                continue
            if m.kind == "pronoun" and mode == "revision":
                continue  # "give her glasses" must not change the apparent gender
            span = set(range(m.start, m.end))
            match_type = "pronoun" if m.kind == "pronoun" else ("inflected" if m.inflected else "exact")
            negated, neg_tokens = (False, set())
            if m.kind == "standalone":
                negated, neg_tokens = self._negation(tokens, sentence, m.start, m.end, scope)
            # "almond EYES", "oval FACE": the noun that goes with the phrase is part of the evidence
            attrs = {a for a, _ in m.payload}
            first, last = m.start, m.end - 1
            if m.kind == "standalone" and not negated:
                first, last = self._attach_owner_nouns(m, attrs, nouns, sentence, clause, used)
            evidence = self._slice(text, tokens, first, last)

            for attribute, value in m.payload:
                note = None
                if m.kind == "pronoun":
                    note = f"Inferred only from the pronoun '{evidence}'."
                if negated:
                    full = self._slice(text, tokens, min(span | neg_tokens), max(span | neg_tokens))
                    if attribute == "glasses" and value == "glasses":
                        value, match_type, evidence_text = "none", "negation", full
                    elif attribute == "facial_hair" and value in FACIAL_HAIR_TYPES:
                        value, match_type, evidence_text = "!" + value, "negation", full
                    else:
                        skipped.append(Unrecognized(full, "Negated phrase - cannot be turned into a value."))
                        used |= span | neg_tokens
                        continue
                    used |= neg_tokens
                else:
                    evidence_text = evidence
                candidates.append(Candidate(attribute, value, evidence_text, m.language, match_type, note))
            (weak if m.kind == "pronoun" else used).update(span)

    @staticmethod
    def _attach_owner_nouns(m: Match, attrs: set[str], nouns: list[Match], sentence, clause, used) -> tuple[int, int]:  # noqa: ANN001
        """Mark a noun that 'owns' the matched attribute as used (at most one word away)."""
        wanted = set(attrs)
        for attribute in attrs:
            wanted |= OWNER_ALIASES.get(attribute, set())
        first, last = m.start, m.end - 1
        for noun in nouns:
            if sentence[noun.start] != sentence[m.start] or clause[noun.start] != clause[m.start]:
                continue
            if not (set(noun.payload) & wanted):
                continue
            gap = noun.start - m.end if noun.start >= m.end else m.start - noun.end
            if gap < 0 or gap > 1 or (noun.start < m.end and noun.end > m.start):
                continue
            used.update(range(noun.start, noun.end))
            first, last = min(first, noun.start), max(last, noun.end - 1)
        return first, last

    # ----- step 4b: adjectives bound to the nearest noun ---------------------------------
    def _collect_adjectives(self, text, tokens, sentence, clause, matches, scope, candidates, skipped, used, mode) -> None:  # noqa: ANN001
        anchors = [m for m in matches if m.kind in ("noun", "blocker")]
        groups: dict[tuple[int, int], list[Match]] = defaultdict(list)
        for m in matches:
            if m.kind == "adjective":
                groups[(m.start, m.end)].append(m)

        for (start, end), group in sorted(groups.items()):
            anchor = self._nearest_anchor(start, end, anchors, sentence, clause)
            if anchor is None or anchor.kind != "noun":
                continue  # unattached or attached to a body part we do not model
            owned = set(anchor.payload)
            if mode == "revision":
                for attribute in list(owned):
                    owned |= REVISION_OWNER_ALIASES.get(attribute, set())
            allowed = [(m.payload, m) for m in group if m.payload[0] in owned]
            if not allowed:
                continue
            first, last = min(start, anchor.start), max(end, anchor.end) - 1
            evidence = self._slice(text, tokens, first, last)
            negated, neg_tokens = self._negation(tokens, sentence, start, end, scope)
            if negated:
                full = self._slice(text, tokens, min({first} | neg_tokens), max({last} | neg_tokens))
                skipped.append(Unrecognized(full, "Negated phrase - cannot be turned into a value."))
                used |= set(range(start, end)) | set(range(anchor.start, anchor.end)) | neg_tokens
                continue
            for (attribute, value), m in allowed:
                candidates.append(
                    Candidate(attribute, value, evidence, m.language, "inflected" if m.inflected else "exact")
                )
            used |= set(range(start, end)) | set(range(anchor.start, anchor.end))

    @staticmethod
    def _nearest_anchor(start: int, end: int, anchors: list[Match], sentence: list[int], clause: list[int]) -> Match | None:
        """The noun (or unmodelled body part) an adjective most likely describes.

        1. Only nouns in the SAME clause count: in "चेहरा गोल, भौंहें मोटी" the comma keeps
           "मोटी" away from the face.
        2. If the adjective's clause has no noun at all ("thick, dark eyebrows",
           "thick and bushy eyebrows"), look at the nouns that follow it.
        """

        def nearest(pool: list[Match]) -> Match | None:
            best: tuple[tuple[int, int], Match] | None = None
            for anchor in pool:
                if sentence[anchor.start] != sentence[start]:
                    continue
                if anchor.start >= end:
                    distance, side = anchor.start - end + 1, 0  # noun after the adjective
                elif anchor.end <= start:
                    distance, side = start - anchor.end + 1, 1  # noun before the adjective
                else:
                    continue
                if distance > BINDING_WINDOW:
                    continue
                key = (distance, side)  # ties go to the noun that FOLLOWS ("thick eyebrows")
                if best is None or key < best[0]:
                    best = (key, anchor)
            return best[1] if best else None

        in_clause = [a for a in anchors if clause[a.start] == clause[start]]
        if in_clause:
            return nearest(in_clause)
        return nearest([a for a in anchors if a.start >= end])

    # ----- step 4c: ages ----------------------------------------------------------------
    def _collect_ages(self, text, tokens, age_hits, candidates, skipped, used) -> None:  # noqa: ANN001
        for hit in age_hits:
            evidence = self._slice(text, tokens, hit.start, hit.end - 1)
            used |= set(range(hit.start, hit.end))
            bucket = age_rules.bucket_for_age(hit.age)
            if bucket is None:
                skipped.append(Unrecognized(evidence, "Ages under 18 are not supported by this system."))
                continue
            rounded = round(hit.age)
            candidates.append(
                Candidate(
                    "age_description",
                    bucket,
                    evidence,
                    "number",
                    "number",
                    f"Stated age {rounded} grouped into a vocabulary band; the band edges are fixed rules.",
                )
            )

    # ----- step 6: combine candidates -------------------------------------------------------
    def _aggregate(self, candidates, skipped, negated_facial_hair):  # noqa: ANN001
        attributes: dict[str, str | None] = {key: None for key in ATTRIBUTE_KEYS}
        details: list[ExtractedValue] = []
        conflicts: list[Conflict] = []
        notes: list[str] = []

        by_attribute: dict[str, list[Candidate]] = defaultdict(list)
        for c in candidates:
            by_attribute[c.attribute].append(c)

        for attribute in ATTRIBUTE_KEYS:
            found = by_attribute.get(attribute)
            if not found:
                continue
            if attribute == "facial_hair":
                value, chosen, conflict, note = self._resolve_facial_hair(found, skipped, negated_facial_hair)
            else:
                values = list(dict.fromkeys(c.value for c in found))
                if len(values) == 1:
                    value, chosen, conflict, note = values[0], found, None, None
                else:
                    value, chosen, note = None, [], None
                    conflict = Conflict(attribute, values, list(dict.fromkeys(c.evidence for c in found)))
            if conflict:
                conflicts.append(conflict)
            if value is None:
                continue
            attributes[attribute] = value
            first = chosen[0]
            seen: set[str] = set()
            merged_evidence = [c.evidence for c in chosen if not (c.evidence in seen or seen.add(c.evidence))]
            detail_note = note or first.note
            details.append(
                ExtractedValue(
                    attribute=attribute,
                    value=value,
                    evidence=" | ".join(merged_evidence),
                    language=first.language,
                    match_type=first.match_type if value == first.value else "exact",
                    note=detail_note,
                )
            )
        return attributes, details, conflicts, notes

    @staticmethod
    def _resolve_facial_hair(found, skipped, negated_facial_hair):  # noqa: ANN001
        """Facial hair is the only attribute with combinable values ("beard and mustache")."""
        positives = [c for c in found if c.value in FACIAL_HAIR_TYPES]
        negatives = [c for c in found if c.value.startswith("!")]
        clean = [c for c in found if c.value == "none"]
        negated = {c.value[1:] for c in negatives}
        negated_facial_hair |= negated
        pos_types = {c.value for c in positives}

        def conflict(values, evidence):
            return None, [], Conflict("facial_hair", values, list(dict.fromkeys(evidence))), None

        if pos_types:
            if clean or (pos_types & negated):
                return conflict(
                    sorted(pos_types | ({"none"} if clean else set()) | {"!" + t for t in pos_types & negated}),
                    [c.evidence for c in found],
                )
            note = None
            if pos_types == {"beard", "mustache"}:
                value, note = "beard", "'beard' and 'mustache' were both mentioned; they are combined as 'beard'."
            elif pos_types == {"goatee", "mustache"}:
                value, note = "goatee", "'goatee' and 'mustache' were both mentioned; they are combined as 'goatee'."
            elif len(pos_types) == 1:
                value = next(iter(pos_types))
            else:
                return conflict(sorted(pos_types), [c.evidence for c in positives])
            return value, positives, None, note

        if clean:
            return "none", clean, None, None
        if "beard" in negated:
            chosen = [c for c in negatives if c.value == "!beard"]
            note = None
            if "mustache" not in negated:
                note = "'No beard' was read as no facial hair; a mustache may still be present - please check."
            return "none", chosen, None, note
        # e.g. only "no mustache": that does not tell us what the face DOES have
        for c in negatives:
            skipped.append(
                Unrecognized(c.evidence, "A single negated feature does not say what facial hair the face has.")
            )
        return None, [], None, None

    # ----- step 7: report what was not understood -------------------------------------------
    def _unrecognized(self, text, tokens, clause_of, used, weak, mode, skipped) -> list[Unrecognized]:  # noqa: ANN001
        exempt: set[int] = set(weak)  # function words never count as "content"
        for i, tok in enumerate(tokens):
            if (
                self._is_any(tok.norm, "conjunctions")
                or self._is_stopword(tok.norm)
                or self._is_any(tok.norm, "negators_before")
                or self._is_negator_after(tok.norm)
                or self._is_any(tok.norm, "contrast")
                or (
                    mode == "revision"
                    and (self._is_any(tok.norm, "removal_verbs") or self._is_any(tok.norm, "instruction_words"))
                )
            ):
                exempt.add(i)

        clauses: dict[int, list[int]] = defaultdict(list)
        for i, c in enumerate(clause_of):
            clauses[c].append(i)

        out: list[Unrecognized] = list(skipped)
        for indices in clauses.values():
            partly_understood = any(i in used for i in indices)
            reason = (
                "Not matched to a supported attribute value."
                if partly_understood
                else "No supported facial attribute was recognised in this phrase."
            )
            run: list[int] = []

            def flush(run: list[int] = run, reason: str = reason) -> None:
                content = [i for i in run if i not in exempt]
                if content:  # trim function words at both ends ("a scar on her left cheek" -> "scar on her left cheek")
                    out.append(Unrecognized(self._slice(text, tokens, content[0], content[-1]), reason))
                run.clear()

            for i in indices:
                if i in used:
                    flush()  # an understood word ends the fragment
                else:
                    run.append(i)
            flush()

        unique: dict[str, Unrecognized] = {}
        for item in out:
            unique.setdefault(re.sub(r"\s+", " ", item.text).casefold(), item)
        return list(unique.values())[:MAX_UNRECOGNIZED]

    # ----- warnings ---------------------------------------------------------------------------
    def _warnings(self, text, language, details, conflicts, attributes, notes) -> list[str]:  # noqa: ANN001
        warnings: list[str] = []
        scripts = detect_scripts(text)
        detected = [SCRIPT_TO_LANGUAGE[s] for s in scripts if s in SCRIPT_TO_LANGUAGE]
        if detected and language not in detected:
            warnings.append(
                f"The text looks like {LANGUAGE_LABELS[detected[0]]} but the language is set to "
                f"{LANGUAGE_LABELS.get(language, language)}. Phrases were matched in every supported language - "
                "please check the language label."
            )
        elif len(detected) > 1:
            warnings.append("The text mixes more than one script; phrases were matched in each language.")
        if "Other" in scripts:
            warnings.append("Some characters belong to a script this parser does not support; they were ignored.")

        review = {lex.language: lex.review_status for lex in self.lexicons}
        matched_languages = {d.language for d in details if d.language in review}
        for code in sorted(matched_languages):
            if review[code] != "reviewed" and code != "en":
                warnings.append(
                    f"The {LANGUAGE_LABELS[code]} word list is an unreviewed draft (no native-speaker review yet). "
                    "Treat these values as suggestions and check them."
                )
        for conflict in conflicts:
            warnings.append(
                f"Conflicting values for '{conflict.attribute}' ({', '.join(conflict.values)}). "
                "It was left empty - choose the right value yourself."
            )
        if not any(attributes.values()):
            warnings.append("No supported facial attributes were recognised. You can still set them manually.")
        warnings.extend(notes)
        return warnings
