"""Witness-description parsing (English / Kannada / Hindi).

``get_parser()`` returns the parser used by the API. To plug in a different
implementation (for example a trained model) implement ``DescriptionParser`` from
``base.py`` and return it here.
"""

from __future__ import annotations

from functools import lru_cache

from app.services.description_parser.base import DescriptionParser, ParseResult
from app.services.description_parser.rules import PARSER_NAME, PARSER_VERSION, RuleBasedParser


@lru_cache(maxsize=1)
def get_parser() -> RuleBasedParser:
    return RuleBasedParser()


__all__ = ["DescriptionParser", "ParseResult", "RuleBasedParser", "PARSER_NAME", "PARSER_VERSION", "get_parser"]
