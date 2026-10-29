"""PDF case report (fpdf2).

Bundled Noto fonts + text shaping make Kannada and Hindi witness text print correctly (conjuncts
and vowel signs included). The report always states: preliminary investigative aid, human review
required, how each sketch was made (AI or not), the full version history and when it was generated.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace

from app.core.config import APP_NAME, APP_VERSION
from app.models import Case, InvestigatorNote, SketchVersion, WitnessDescription
from app.services.attributes import ATTRIBUTES, LANGUAGE_LABELS, attribute_diff
from app.services.description_parser import PARSER_NAME, PARSER_VERSION
from app.services.description_parser.rules import LEXICON_MODULES
from app.services.disclaimers import PDF_LIMITATIONS, PRELIMINARY
from app.services.image_tools import FONT_DIR, add_provenance_band
from app.services.provenance import caption_for
from app.services.sketch_models.registry import ENGINE_LABELS

NAVY = (13, 18, 28)
CYAN = (14, 116, 144)
MUTED = (90, 100, 120)
STATUS_LABELS = {"in_progress": "In progress", "under_review": "Under review", "closed": "Closed"}
NOT_RECORDED = "Not recorded"  # cases created before names existed


@dataclass
class ReportData:
    case: Case
    owner_username: str
    generated_by: str
    generated_at: datetime
    descriptions: list[WitnessDescription]
    versions: list[SketchVersion]
    selected: SketchVersion | None
    selected_png: bytes | None
    notes: list[tuple[InvestigatorNote, str]] = field(default_factory=list)  # (note, author username)


class _Pdf(FPDF):
    def __init__(self, case_ref: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.case_ref = case_ref
        self.set_margins(16, 18, 16)
        self.set_auto_page_break(auto=True, margin=22)
        for family, files in {
            "NotoSans": ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
            "NotoDeva": ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf"),
            "NotoKnda": ("NotoSansKannada-Regular.ttf", "NotoSansKannada-Bold.ttf"),
        }.items():
            self.add_font(family, "", str(FONT_DIR / files[0]))
            self.add_font(family, "B", str(FONT_DIR / files[1]))
        self.set_fallback_fonts(["NotoDeva", "NotoKnda"])
        self.set_text_shaping(True)
        self.set_title(f"{APP_NAME} case report {case_ref}")
        self.set_author(APP_NAME)
        self.set_creator(f"{APP_NAME} {APP_VERSION}")
        self.alias_nb_pages()

    # --- page furniture ---------------------------------------------------------------
    def header(self) -> None:
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 11, style="F")
        self.set_xy(16, 3)
        self.set_font("NotoSans", "B", 9)
        self.set_text_color(230, 237, 247)
        self.cell(100, 5, f"{APP_NAME}  |  Case report", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("NotoSans", "", 9)
        self.set_text_color(34, 211, 238)
        self.cell(0, 5, self.case_ref, align="R")
        self.set_y(18)
        self.set_text_color(20, 24, 34)

    def footer(self) -> None:
        self.set_y(-17)
        self.set_draw_color(180, 188, 200)
        self.line(16, self.get_y(), 194, self.get_y())
        self.set_font("NotoSans", "B", 8)
        self.set_text_color(160, 60, 20)
        self.cell(0, 5, PRELIMINARY.upper(), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("NotoSans", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 4, f"Not an identification. Page {self.page_no()} of {{nb}}", align="C")

    # --- building blocks ---------------------------------------------------------------------
    def h1(self, text: str) -> None:
        self.ln(3)
        self.set_font("NotoSans", "B", 13)
        self.set_text_color(*CYAN)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*CYAN)
        self.line(16, self.get_y(), 194, self.get_y())
        self.ln(2.5)
        self.set_text_color(20, 24, 34)

    def h2(self, text: str) -> None:
        self.set_font("NotoSans", "B", 10.5)
        self.cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def para(self, text: str, *, size: float = 9.5, bold: bool = False, color=(20, 24, 34), gap: float = 1.5) -> None:
        self.set_font("NotoSans", "B" if bold else "", size)
        self.set_text_color(*color)
        self.multi_cell(0, size * 0.52, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(gap)
        self.set_text_color(20, 24, 34)

    def bullets(self, items: list[str], size: float = 9) -> None:
        self.set_font("NotoSans", "", size)
        for item in items:
            self.set_x(20)
            self.multi_cell(0, size * 0.52, f"-  {item}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(0.8)

    def grid(self, headers: list[str], rows: list[list[str]], widths: list[float], size: float = 8.5) -> None:
        self.set_font("NotoSans", "", size)
        self.set_draw_color(190, 198, 210)
        with self.table(
            col_widths=widths, text_align="LEFT", line_height=size * 0.55, padding=1.2,
            headings_style=FontFace(emphasis="BOLD", fill_color=(226, 232, 240)),
        ) as table:
            head = table.row()
            for h in headers:
                head.cell(h)
            for r in rows:
                row = table.row()
                for cell in r:
                    row.cell(cell)
        self.ln(2)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _lexicon_review(language: str) -> str | None:
    for module in LEXICON_MODULES:
        if module.LANGUAGE == language and module.REVIEW_STATUS != "reviewed" and language != "en":
            return (
                f"The {LANGUAGE_LABELS[language]} word list used to read this text has not been reviewed by a native "
                "speaker. Treat the extracted values as suggestions."
            )
    return None


def build_case_report(data: ReportData) -> bytes:
    case = data.case
    pdf = _Pdf(case.case_id)
    pdf.add_page()

    # ---- title block -----------------------------------------------------------------------------
    pdf.set_font("NotoSans", "B", 18)
    pdf.multi_cell(0, 8, case.title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.grid(
        ["Field", "Value"],
        [
            ["Case ID", case.case_id],
            ["Status", STATUS_LABELS.get(case.status, case.status)],
            ["Incident date", case.incident_date.isoformat()],
            ["Investigator name", case.investigator_name or NOT_RECORDED],
            ["Investigator reference", case.investigator_ref],
            ["Witness name", case.witness_name or NOT_RECORDED],
            ["Case owner (account)", data.owner_username],
            ["Case created", _fmt(case.created_at)],
            ["Report generated", f"{_fmt(data.generated_at)} by {data.generated_by}"],
            ["Software", f"{APP_NAME} {APP_VERSION}"],
        ],
        [50, 128],
    )
    pdf.set_fill_color(255, 244, 229)
    pdf.set_draw_color(217, 119, 6)
    pdf.set_font("NotoSans", "B", 9.5)
    pdf.multi_cell(0, 5, "Preliminary investigative aid - requires human review. " + PDF_LIMITATIONS[1],
                   border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ---- incident ------------------------------------------------------------------------------------
    pdf.h1("1. Incident description")
    pdf.para(case.incident_description.strip() or "No incident description was entered.")

    # ---- witness descriptions -------------------------------------------------------------------------
    pdf.h1("2. Witness descriptions and extracted attributes")
    if not data.descriptions:
        pdf.para("No witness description has been saved for this case.", color=MUTED)
    for index, d in enumerate(data.descriptions, start=1):
        pdf.h2(f"Description {index}: {d.label} ({LANGUAGE_LABELS.get(d.language, d.language)})")
        pdf.para("Original text (preserved exactly as entered):", size=8.5, color=MUTED, gap=0.5)
        pdf.set_fill_color(244, 246, 250)
        pdf.set_font("NotoSans", "", 10)
        pdf.multi_cell(0, 5.4, d.original_text, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        rows = []
        for spec in ATTRIBUTES:
            reviewed, parsed = d.confirmed_attributes.get(spec.key), d.extracted_attributes.get(spec.key)
            if reviewed or parsed:
                changed = "" if reviewed == parsed else ("edited by investigator" if reviewed else "removed by investigator")
                rows.append([spec.label, spec.label_for(reviewed) if reviewed else "-", spec.label_for(parsed) if parsed else "-", changed])
        if rows:
            pdf.grid(["Attribute (estimate)", "Reviewed value", "Parser value", "Note"], rows, [46, 52, 46, 34])
        else:
            pdf.para("No attributes were recorded for this description.", color=MUTED)
        if d.additional_details.strip():
            pdf.para(f"Additional details (free text, used by AI engines only): {d.additional_details}", size=8.5)
        if d.unrecognized:
            pdf.para("Phrases the parser did not convert into attributes:", size=8.5, bold=True, gap=0.5)
            pdf.bullets([f"{u['text']} - {u['reason']}" for u in d.unrecognized], size=8.5)
        note = _lexicon_review(d.language)
        if note:
            pdf.para(note, size=8.5, color=(160, 60, 20))
        pdf.para(f"Parser: {PARSER_NAME} {d.parser_version or PARSER_VERSION}. Entered {_fmt(d.created_at)}.", size=8, color=MUTED)

    # ---- selected sketch ------------------------------------------------------------------------------------
    if data.selected is not None and pdf.get_y() > 120:
        pdf.add_page()  # never leave the heading alone at the bottom of a page
    pdf.h1("3. Selected sketch")
    if data.selected is None or data.selected_png is None:
        pdf.para("No sketch has been generated or selected for this case yet.", color=MUTED)
    else:
        v = data.selected
        headline, lines, warn = caption_for(v, case.case_id)
        captioned = add_provenance_band(data.selected_png, headline, lines, warning=warn)
        pdf.image(io.BytesIO(captioned), x=16, w=100)  # the caption band travels with the picture
        pdf.ln(2)
        # the same statement as real text, so screen readers and text search can find it too
        pdf.para(headline, size=9, bold=True, color=(160, 60, 20) if warn else CYAN, gap=0.3)
        pdf.para(lines[2], size=8.5, color=MUTED, gap=2)
        pdf.grid(
            ["Field", "Value"],
            [
                ["Version", f"{v.version_number} ({'revision' if v.kind == 'revision' else 'initial'})"],
                ["Engine", ENGINE_LABELS.get(v.engine, v.engine)],
                ["AI-generated", "YES - requires careful human review" if v.is_ai_generated else "No (rule-based drawing)"],
                ["Model", v.model_name or "-"],
                ["Created", _fmt(v.created_at)],
                ["Instruction", v.instruction or "-"],
                ["Image SHA-256", v.image_sha256[:32] + "..."],
            ],
            [46, 132],
        )
        rows = [[spec.label, spec.label_for(v.attributes.get(spec.key)) if v.attributes.get(spec.key) else "not specified"] for spec in ATTRIBUTES]
        pdf.h2("Attributes used for this sketch")
        pdf.grid(["Attribute", "Value"], rows, [60, 118])
        if v.notes:
            pdf.para("Engine notes:", size=8.5, bold=True, gap=0.5)
            pdf.bullets(v.notes, size=8.5)

    # ---- version history ------------------------------------------------------------------------------------------
    pdf.h1("4. Version history")
    if not data.versions:
        pdf.para("There are no sketch versions.", color=MUTED)
    else:
        rows = []
        by_id = {x.id: x for x in data.versions}
        for v in data.versions:
            parent = by_id.get(v.parent_id) if v.parent_id else None
            changes = []
            if parent:
                changes = [f"{c['label']}: {c['before'] or 'unspecified'} -> {c['after'] or 'unspecified'}" for c in attribute_diff(parent.attributes, v.attributes)]
            rows.append([
                f"V{v.version_number}" + (" *" if data.selected and v.id == data.selected.id else ""),
                f"V{parent.version_number}" if parent else "-",
                ("AI: " if v.is_ai_generated else "Schematic: ") + (v.model_name or v.engine),
                _fmt(v.created_at),
                (v.instruction or "(initial sketch)") + (("\n" + "; ".join(changes)) if changes else ""),
            ])
        pdf.grid(["Ver.", "From", "Engine", "Created", "Instruction and attribute changes"], rows, [13, 13, 40, 34, 78], size=8)
        pdf.para("* = selected sketch shown in section 3.", size=8, color=MUTED)

    # ---- notes -----------------------------------------------------------------------------------------------------------
    pdf.h1("5. Investigator notes")
    if not data.notes:
        pdf.para("No notes were recorded.", color=MUTED)
    for note, author in data.notes:
        pdf.para(f"{_fmt(note.created_at)} - {author}" + (f" (re: version {note.sketch_version_id})" if note.sketch_version_id else ""),
                 size=8, color=MUTED, gap=0.3)
        pdf.para(note.body, size=9.5)

    # ---- methods and limitations -----------------------------------------------------------------------------------------------
    pdf.h1("6. Methods and limitations")
    languages = {d.language for d in data.descriptions}
    items = list(PDF_LIMITATIONS)
    items.append(f"Attributes are estimates taken from witness wording by a rule-based parser ({PARSER_NAME} {PARSER_VERSION}) and "
                 "may have been corrected by the investigator. Phrases the parser did not understand were not converted.")
    if languages & {"hi", "kn"}:
        items.append("Hindi and Kannada support uses developer-written word lists that no native speaker has reviewed yet.")
    if any(v.is_ai_generated for v in data.versions):
        items.append("At least one version was produced by an AI model. AI images can contain invented details and biases, and the "
                     "model does not know the real person. Check every feature against the witness account.")
    if any(not v.is_ai_generated for v in data.versions):
        items.append("Schematic versions are drawn by fixed rules (not AI) from the listed attributes only; features that were "
                     "not specified are drawn in a neutral form.")
    pdf.bullets(items)
    pdf.ln(2)
    pdf.para(f"Report generated {_fmt(data.generated_at)} by {data.generated_by}.", size=8.5, color=MUTED)
    return bytes(pdf.output())
