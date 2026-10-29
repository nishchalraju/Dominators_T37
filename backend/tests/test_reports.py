import io

from pypdf import PdfReader

from tests.helpers import ATTRS, generate, make_case

HI = "वह आदमी लगभग 35 साल का था। उसका चेहरा गोल, भौंहें मोटी।"
KN = "ದುಂಡನೆಯ ಮುಖ, ದಪ್ಪ ಹುಬ್ಬುಗಳು, ಗಡ್ಡ ಇದೆ."


def pdf_text(content: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)


def build_case(client, headers):
    cid = make_case(client, headers, title="Report test case", incident_description="Synthetic incident for the report.")["case_id"]
    client.post(f"/api/cases/{cid}/descriptions", headers=headers, json={"language": "hi", "original_text": HI})
    client.post(f"/api/cases/{cid}/descriptions", headers=headers, json={"language": "kn", "original_text": KN, "label": "Witness 2"})
    v1 = generate(client, headers, cid).json()
    client.post(f"/api/sketches/{v1['id']}/revise", headers=headers, json={"instruction": "make the eyebrows thicker and add glasses", "language": "en"})
    client.post(f"/api/cases/{cid}/notes", headers=headers, json={"body": "Witness is certain about the glasses."})
    return cid


def test_report_contains_every_required_section(client, admin):
    cid = build_case(client, admin)
    r = client.get(f"/api/cases/{cid}/report", headers=admin)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and "attachment" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    text = pdf_text(r.content)
    for needle in [
        cid, "Report test case", "Synthetic incident for the report", "T-100",  # metadata
        "Witness 1", "Witness 2", "Original text", "Apparent gender", "Eyebrow thickness",  # witness text + attributes
        "Selected sketch", "SCHEMATIC COMPOSITE - NOT AI-GENERATED",  # sketch with provenance
        "Version history", "make the eyebrows thicker and add glasses", "V2", "V1",  # versions + instructions
        "Investigator notes", "Witness is certain about the glasses",  # notes
        "Report generated", "UTC",  # timestamp
    ]:
        assert needle in text, needle


def test_report_carries_the_required_disclaimers(client, admin):
    text = pdf_text(client.get(f"/api/cases/{build_case(client, admin)}/report", headers=admin).content)
    flat = " ".join(text.split())
    assert "PRELIMINARY INVESTIGATIVE AID" in text.upper() and "requires human review" in flat
    assert "does not identify people" in flat and "no face matching" in flat
    assert "never overwritten" in flat
    assert "not been reviewed by a native speaker" in flat or "no native speaker has reviewed" in flat


def test_report_prints_hindi_and_kannada_witness_text(client, admin):
    r = client.get(f"/api/cases/{build_case(client, admin)}/report", headers=admin)
    text = pdf_text(r.content)
    assert any("\u0900" <= ch <= "\u097f" for ch in text), "no Devanagari text in the PDF"
    assert any("\u0c80" <= ch <= "\u0cff" for ch in text), "no Kannada text in the PDF"


def test_report_for_an_empty_case_says_so_instead_of_inventing_content(client, admin):
    cid = make_case(client, admin)["case_id"]
    flat = " ".join(pdf_text(client.get(f"/api/cases/{cid}/report", headers=admin).content).split())
    assert "No witness description has been saved" in flat and "No sketch has been generated" in flat and "No notes were recorded" in flat


def test_report_marks_ai_sketches_clearly(client, admin):
    from tests.test_api_sketches import StandInAI

    from app.services.sketch_models.registry import _instances

    _instances["huggingface"] = StandInAI()
    cid = make_case(client, admin)["case_id"]
    generate(client, admin, cid, ATTRS, engine="ai")
    flat = " ".join(pdf_text(client.get(f"/api/cases/{cid}/report", headers=admin).content).split())
    assert "YES - requires careful human review" in flat and "AI-generated" in flat


def test_report_is_logged_in_the_audit_trail(client, admin):
    cid = make_case(client, admin)["case_id"]
    client.get(f"/api/cases/{cid}/report", headers=admin)
    assert any(a["action"] == "report_generated" for a in client.get("/api/activity", headers=admin).json())


def test_report_names_the_investigator_and_the_witness(client, admin):
    cid = make_case(client, admin, investigator_name="Inspector Anita Rao", witness_name="Ravi Kumar")["case_id"]
    flat = " ".join(pdf_text(client.get(f"/api/cases/{cid}/report", headers=admin).content).split())
    for needle in ("Investigator name", "Inspector Anita Rao", "Witness name", "Ravi Kumar", "Investigator reference", "T-100"):
        assert needle in flat, needle


def test_report_prints_hindi_and_kannada_names(client, admin):
    cid = make_case(client, admin, investigator_name="ಅನಿತಾ ರಾವ್", witness_name="रवि कुमार")["case_id"]  # no descriptions at all
    text = pdf_text(client.get(f"/api/cases/{cid}/report", headers=admin).content)
    assert any("\u0900" <= ch <= "\u097f" for ch in text), "the Hindi witness name is missing from the PDF"
    assert any("\u0c80" <= ch <= "\u0cff" for ch in text), "the Kannada investigator name is missing from the PDF"
