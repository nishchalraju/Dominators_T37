"""Text normalisation and tokenisation for English, Kannada and Hindi.

Why a custom tokenizer?  Python's ``\\w`` does NOT match Indic vowel signs and the
virama (they are combining marks), so ``re.findall(r"\\w+", "अंडाकार")`` would cut
the word into pieces. We treat letters (L*), combining marks (M*) and numbers (N*)
as word characters, plus the zero-width joiners that Indic keyboards insert.
"""

from __future__ import annotations

import unicodedata

from app.services.description_parser.base import Token

HARD_BOUNDARY_CHARS = set(".;!?\n\r\u0964\u0965|")  # . ; ! ? newline, danda, double danda
SOFT_BOUNDARY_CHARS = set(",\u060c\u3001:")  # comma-like separators
_JOINERS = {"\u200c", "\u200d", "\ufeff"}  # ZWNJ, ZWJ, BOM
_APOSTROPHES = {"'", "\u2019", "\u02bc"}

# Devanagari (U+0966..U+096F) and Kannada (U+0CE6..U+0CEF) digits -> ASCII digits
_DIGIT_TABLE = {
    **{0x0966 + i: ord(str(i)) for i in range(10)},
    **{0x0CE6 + i: ord(str(i)) for i in range(10)},
}


def normalize_token(raw: str) -> str:
    text = unicodedata.normalize("NFC", raw)
    text = "".join(ch for ch in text if ch not in _JOINERS and ch not in _APOSTROPHES)
    return text.casefold().translate(_DIGIT_TABLE)


def _is_word_char(ch: str) -> bool:
    return ch in _JOINERS or unicodedata.category(ch)[0] in "LMN"


def tokenize(text: str) -> list[Token]:
    """Split ``text`` into tokens, remembering the punctuation between them."""
    tokens: list[Token] = []
    i, n, prev_end = 0, len(text), 0
    while i < n:
        if not _is_word_char(text[i]):
            i += 1
            continue
        j = i + 1
        while j < n:
            ch = text[j]
            if _is_word_char(ch):
                j += 1
            elif ch in _APOSTROPHES and j + 1 < n and _is_word_char(text[j + 1]) and text[j - 1].isalpha():
                j += 1  # apostrophe inside a word: "doesn't", "o'clock"
            else:
                break
        raw = text[i:j]
        tokens.append(Token(raw=raw, norm=normalize_token(raw), start=i, end=j, sep=text[prev_end:i]))
        prev_end = j
        i = j
    return tokens


def sentence_ids(tokens: list[Token]) -> list[int]:
    """Sentence index of every token (hard punctuation starts a new sentence)."""
    ids: list[int] = []
    current = 0
    for idx, tok in enumerate(tokens):
        if idx > 0 and any(c in HARD_BOUNDARY_CHARS for c in tok.sep):
            current += 1
        ids.append(current)
    return ids


def detect_scripts(text: str) -> list[str]:
    """Which scripts occur in the text (letters only), most frequent first."""
    counts: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            script = "Devanagari"
        elif 0x0C80 <= cp <= 0x0CFF:
            script = "Kannada"
        elif ch.isascii() or 0x00C0 <= cp <= 0x024F:
            script = "Latin"
        else:
            script = "Other"
        counts[script] = counts.get(script, 0) + 1
    return [s for s, _ in sorted(counts.items(), key=lambda kv: -kv[1])]


SCRIPT_TO_LANGUAGE = {"Latin": "en", "Devanagari": "hi", "Kannada": "kn"}
