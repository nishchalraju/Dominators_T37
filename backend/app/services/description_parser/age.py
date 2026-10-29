"""Find age expressions ("35 years old", "in his forties", "೩೫ ವರ್ಷ") in a token list.

Numbers are only treated as ages when the text around them says so (a unit such as
"years" or a word such as "aged"). A bare "70" could be a weight, so it is ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import ModuleType

from app.services.description_parser.base import Token
from app.services.description_parser.normalize import normalize_token

MIN_AGE = 1  # small numbers are kept so that children's ages can be reported as unsupported
MAX_AGE = 99
_RANGE_JOINERS = {"to", "or", "से", "ರಿಂದ"}
_FILLER_BEFORE_NUMBER = {"of", "about", "around", "approximately", "roughly", "approx", "लगभग", "करीब", "ಸುಮಾರು"}


def bucket_for_age(age: float) -> str | None:
    """Map an age in years to the controlled vocabulary. Under 18 is not supported."""
    if age < 18:
        return None
    if age < 30:
        return "young_adult"
    if age < 45:
        return "adult"
    if age < 60:
        return "middle_aged"
    return "elderly"


@dataclass
class AgeHit:
    age: float
    start: int  # token index (inclusive)
    end: int  # token index (exclusive)
    language: str
    note: str | None = None


def _matches(norm: str, word: str) -> bool:
    """Match a normalised token against a lexicon word; a trailing '*' means prefix."""
    word_norm = normalize_token(word.rstrip("*"))
    return norm.startswith(word_norm) if word.endswith("*") else norm == word_norm


def _any(norm: str, words) -> bool:
    return any(_matches(norm, w) for w in words)


def _lookup(norm: str, table: dict[str, int]) -> int | None:
    for word, value in table.items():
        if _matches(norm, word):
            return value
    return None


def _is_number(norm: str) -> int | None:
    return int(norm) if re.fullmatch(r"\d{1,3}", norm) else None


def find_age_expressions(tokens: list[Token], sentence: list[int], lexicons: list[ModuleType]) -> list[AgeHit]:
    hits: list[AgeHit] = []
    taken: set[int] = set()

    def unit_at(idx: int, anchor: int) -> tuple[bool, str]:
        """Is token ``idx`` an age unit ("years", "साल", "ವರ್ಷ") in the same sentence as ``anchor``?"""
        if idx >= len(tokens) or sentence[idx] != sentence[anchor]:
            return False, ""
        for lex in lexicons:
            if _any(tokens[idx].norm, lex.AGE_UNIT_WORDS):
                return True, lex.LANGUAGE
        return False, ""

    def context_before(idx: int) -> tuple[bool, str]:
        """An 'age' word right before the number (allowing 'of'/'about' in between)."""
        for back in (1, 2):
            j = idx - back
            if j < 0 or sentence[j] != sentence[idx]:
                break
            norm = tokens[j].norm
            for lex in lexicons:
                if _any(norm, lex.AGE_CONTEXT_WORDS):
                    return True, lex.LANGUAGE
            if norm not in _FILLER_BEFORE_NUMBER:
                break
        return False, ""

    def decade_offset(idx: int) -> tuple[int, int]:
        """('early' / 'mid' / 'late') before a decade; returns (offset, first token used)."""
        if idx > 0 and sentence[idx - 1] == sentence[idx]:
            for lex in lexicons:
                mod = _lookup(tokens[idx - 1].norm, lex.DECADE_MODIFIERS)
                if mod is not None:
                    return mod, idx - 1
        return 5, idx

    i = 0
    while i < len(tokens):
        if i in taken:
            i += 1
            continue
        norm = tokens[i].norm

        # A. "40s", "in her 30s"
        m = re.fullmatch(r"(\d)0s", norm)
        if m:
            offset, first = decade_offset(i)
            hits.append(AgeHit(int(m.group(1)) * 10 + offset, first, i + 1, "en"))
            taken.update(range(first, i + 1))
            i += 1
            continue

        # B. "forties", "early thirties"
        decade = None
        for lex in lexicons:
            decade = _lookup(norm, lex.DECADE_WORDS)
            if decade is not None:
                break
        if decade is not None:
            offset, first = decade_offset(i)
            hits.append(AgeHit(decade + offset, first, i + 1, "en"))
            taken.update(range(first, i + 1))
            i += 1
            continue

        # C. digits (any script): "35 years", "aged 35", "35-40 years old", "उम्र 35"
        number = _is_number(norm)
        if number is not None and MIN_AGE <= number <= MAX_AGE:
            values = [number]
            last = i
            while True:  # optional range: 35-40, 35 to 40
                nxt = last + 1
                if nxt < len(tokens) and sentence[nxt] == sentence[i] and _is_number(tokens[nxt].norm) is not None:
                    if any(c in tokens[nxt].sep for c in "-\u2013\u2014"):
                        values.append(int(tokens[nxt].norm))
                        last = nxt
                        continue
                if (
                    nxt + 1 < len(tokens)
                    and tokens[nxt].norm in _RANGE_JOINERS
                    and _is_number(tokens[nxt + 1].norm) is not None
                    and sentence[nxt + 1] == sentence[i]
                ):
                    values.append(int(tokens[nxt + 1].norm))
                    last = nxt + 1
                    continue
                break
            unit, unit_lang = unit_at(last + 1, i)
            ctx, ctx_lang = context_before(i)
            if unit and last + 2 < len(tokens) and tokens[last + 2].norm == "ago":
                unit = False  # "5 years ago" is a time, not an age
            if (unit or ctx) and all(MIN_AGE <= v <= MAX_AGE for v in values):
                end = last + 2 if unit else last + 1
                if unit and end < len(tokens) and tokens[end].norm == "old":
                    end += 1
                first = i
                hits.append(AgeHit(sum(values) / len(values), first, end, unit_lang or ctx_lang or "en"))
                taken.update(range(first, end))
                i = end
                continue

        # D. number words: "thirty five years old", "तीस साल", "ಮೂವತ್ತು ವರ್ಷ"
        tens, tens_lang = None, ""
        for lex in lexicons:
            tens = _lookup(norm, lex.TENS_WORDS)
            if tens is not None:
                tens_lang = lex.LANGUAGE
                break
        if tens is not None:
            idx = i + 1
            value = tens
            ones = None
            if idx < len(tokens):
                for lex in lexicons:
                    ones = _lookup(tokens[idx].norm, lex.ONES_WORDS)
                    if ones is not None:
                        break
            if ones is not None:
                value += ones
                idx += 1
            if idx < len(tokens) and any(_any(tokens[idx].norm, lex.AGE_CONNECTORS) for lex in lexicons):
                idx += 1  # e.g. Hindi "पचास के आसपास" (around fifty): skip "के"
            unit, _ = unit_at(idx, i)
            if unit:
                end = idx + 1
                if end < len(tokens) and tokens[end].norm == "old":
                    end += 1
                hits.append(AgeHit(value, i, end, tens_lang))
                taken.update(range(i, end))
                i = end
                continue
        i += 1
    return hits
