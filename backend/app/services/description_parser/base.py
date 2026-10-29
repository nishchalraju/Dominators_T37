"""Shared types and the parser interface.

A parser turns free text (English / Kannada / Hindi) into *candidate* facial
attributes. The output is deliberately explicit about its evidence, about phrases
it could not convert, and about conflicts - it must never invent a value.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Token:
    raw: str  # the word exactly as the witness text has it
    norm: str  # normalised form used for matching (NFC, casefolded, digits -> ASCII)
    start: int  # character offsets in the ORIGINAL text
    end: int
    sep: str  # the characters between the previous token and this one (punctuation etc.)


@dataclass
class ExtractedValue:
    attribute: str
    value: str
    evidence: str  # words copied from the witness text
    language: str  # which rule set matched: en | hi | kn | number
    match_type: str  # exact | inflected | number | negation
    note: str | None = None  # shown to the investigator when the reading is uncertain


@dataclass
class Unrecognized:
    text: str
    reason: str


@dataclass
class Conflict:
    attribute: str
    values: list[str]
    evidence: list[str]


@dataclass
class ParseResult:
    attributes: dict[str, str | None]
    details: list[ExtractedValue] = field(default_factory=list)
    unrecognized: list[Unrecognized] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    declared_language: str = "en"
    detected_scripts: list[str] = field(default_factory=list)
    parser_name: str = ""
    parser_version: str = ""
    lexicon_status: dict[str, str] = field(default_factory=dict)

    @property
    def extracted(self) -> dict[str, str]:
        """Only the attributes that actually received a value."""
        return {k: v for k, v in self.attributes.items() if v}


class DescriptionParser(ABC):
    """Interface every parser implementation must follow."""

    name: str
    version: str

    @abstractmethod
    def parse(self, text: str, language: str = "en") -> ParseResult:
        """Extract facial attributes from ``text``."""
