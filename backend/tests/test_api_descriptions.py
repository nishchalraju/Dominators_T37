from tests.helpers import make_case

HI = "वह आदमी लगभग 35 साल का था। उसका चेहरा गोल, भौंहें मोटी, नाक पतली और छोटे घुंघराले बाल थे। दाढ़ी थी और चश्मा पहना था।"
KN = "ಅವನಿಗೆ ಸುಮಾರು ೩೫ ವರ್ಷ ವಯಸ್ಸು. ದುಂಡನೆಯ ಮುಖ, ದಪ್ಪ ಹುಬ್ಬುಗಳು, ತೆಳುವಾದ ಮೂಗು, ಚಿಕ್ಕ ಗುಂಗುರು ಕೂದಲು. ಗಡ್ಡ ಇದೆ ಮತ್ತು ಕನ್ನಡಕ ಧರಿಸಿದ್ದಾನೆ."


def test_parse_endpoint_returns_editable_estimates_with_evidence(client, admin):
    r = client.post("/api/descriptions/parse", headers=admin, json={"text": "A man with thick eyebrows and a scar.", "language": "en"})
    body = r.json()
    assert r.status_code == 200 and body["attributes"]["eyebrows"] == "thick" and body["attributes"]["glasses"] is None
    assert any(d["attribute"] == "eyebrows" and d["evidence"] == "thick eyebrows" for d in body["details"])
    assert any("scar" in u["text"] for u in body["unrecognized"])
    assert "editable estimates" in body["notice"] and "confidence" not in body


def test_parse_is_identical_across_languages(client, admin):
    a = client.post("/api/descriptions/parse", headers=admin, json={"text": HI, "language": "hi"}).json()
    b = client.post("/api/descriptions/parse", headers=admin, json={"text": KN, "language": "kn"}).json()
    assert a["attributes"] == b["attributes"]
    assert a["lexicon_status"]["hi"] == "unreviewed" and any("unreviewed" in w for w in a["warnings"])


def test_parse_validation(client, admin):
    assert client.post("/api/descriptions/parse", headers=admin, json={"text": "x", "language": "en"}).status_code == 422
    assert client.post("/api/descriptions/parse", headers=admin, json={"text": "a" * 4001, "language": "en"}).status_code == 422
    assert client.post("/api/descriptions/parse", headers=admin, json={"text": "A tall man", "language": "fr"}).status_code == 422
    assert client.post("/api/descriptions/parse", json={"text": "A tall man", "language": "en"}).status_code == 401


def test_saved_description_preserves_original_text_exactly_and_tracks_edits(client, admin):
    cid = make_case(client, admin)["case_id"]
    text = "  " + HI + "\n(second line)  "
    saved = client.post(f"/api/cases/{cid}/descriptions", headers=admin, json={"language": "hi", "original_text": text, "label": "Witness 1"})
    assert saved.status_code == 201
    body = saved.json()
    assert body["original_text"] == HI + "\n(second line)" or body["original_text"] == text.strip()  # edges trimmed, content untouched
    assert HI in body["original_text"]
    assert body["extracted_attributes"] == body["confirmed_attributes"] and body["review_status"] == "parser_output"

    edited = {**body["confirmed_attributes"], "eyebrows": "medium", "glasses": None}
    upd = client.put(f"/api/cases/{cid}/descriptions/{body['id']}", headers=admin, json={"confirmed_attributes": edited, "additional_details": "wears a cap"})
    assert upd.status_code == 200
    out = upd.json()
    assert out["original_text"] == body["original_text"]  # never edited
    assert out["extracted_attributes"]["eyebrows"] == "thick" and out["confirmed_attributes"]["eyebrows"] == "medium"
    assert out["review_status"] == "edited_by_investigator" and out["additional_details"] == "wears a cap"
    listed = client.get(f"/api/cases/{cid}/descriptions", headers=admin).json()
    assert len(listed) == 1 and listed[0]["id"] == body["id"]


def test_server_parses_for_itself_and_never_trusts_client_extraction(client, admin):
    cid = make_case(client, admin)["case_id"]
    r = client.post(f"/api/cases/{cid}/descriptions", headers=admin, json={"language": "en", "original_text": "A man with a beard.", "confirmed_attributes": {"face_shape": "round"}})
    body = r.json()
    assert body["extracted_attributes"]["facial_hair"] == "beard" and body["confirmed_attributes"]["face_shape"] == "round"
    assert body["confirmed_attributes"]["facial_hair"] is None  # the reviewer's version is stored as given


def test_invalid_attribute_values_are_rejected(client, admin):
    cid = make_case(client, admin)["case_id"]
    for bad in ({"face_shape": "banana"}, {"hair_colour": "red"}):
        r = client.post(f"/api/cases/{cid}/descriptions", headers=admin, json={"language": "en", "original_text": "A man.", "confirmed_attributes": bad})
        assert r.status_code == 422


def test_descriptions_of_closed_or_foreign_cases_are_refused(client, admin, user2):
    cid = make_case(client, admin)["case_id"]
    payload = {"language": "en", "original_text": "A man with a beard."}
    assert client.post(f"/api/cases/{cid}/descriptions", headers=user2, json=payload).status_code == 404
    client.patch(f"/api/cases/{cid}", headers=admin, json={"status": "closed"})
    assert client.post(f"/api/cases/{cid}/descriptions", headers=admin, json=payload).status_code == 409
