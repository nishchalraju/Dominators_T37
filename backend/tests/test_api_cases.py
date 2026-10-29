import re
from pathlib import Path

import pytest

from tests.helpers import ATTRS, generate, make_case

ID_RE = re.compile(r"^SA-\d{4}-[A-HJKMNP-Z2-9]{6}$")
VALID_BODY = {"title": "Valid title", "incident_date": "2026-10-20", "investigator_ref": "T-1",
              "investigator_name": "Test Investigator", "witness_name": "Test Witness"}  # fmt: skip


def test_case_gets_a_unique_well_formed_id(client, admin):
    ids = {make_case(client, admin, title=f"Case number {i}")["case_id"] for i in range(15)}
    assert len(ids) == 15 and all(ID_RE.match(i) for i in ids)


def test_case_validation(client, admin):
    bad = [
        {"title": "ab"},  # too short
        {"title": "   "},
        {"incident_date": "2999-01-01"},  # future
        {"incident_date": "not-a-date"},
        {"investigator_ref": ""},
        {"investigator_ref": "<script>"},
    ]
    for override in bad:
        r = client.post("/api/cases", headers=admin, json={**VALID_BODY, **override})
        assert r.status_code == 422 and r.json()["code"] == "validation_error" and r.json()["fields"], override
    assert client.post("/api/cases", headers=admin, json={**VALID_BODY, "surprise": 1}).status_code == 422


def test_list_search_filter_and_pagination(client, admin):
    make_case(client, admin, title="Market robbery", investigator_ref="AAA-1")
    make_case(client, admin, title="Bus station theft", investigator_ref="BBB-2")
    third = make_case(client, admin, title="Warehouse break-in", investigator_ref="CCC-3")
    client.patch(f"/api/cases/{third['case_id']}", headers=admin, json={"status": "closed"})

    everything = client.get("/api/cases", headers=admin).json()
    assert everything["total"] == 3 and len(everything["items"]) == 3
    assert [c["title"] for c in client.get("/api/cases", headers=admin, params={"q": "robbery"}).json()["items"]] == ["Market robbery"]
    assert client.get("/api/cases", headers=admin, params={"q": "bbb"}).json()["total"] == 1  # matches the reference, case-insensitive
    assert client.get("/api/cases", headers=admin, params={"q": third["case_id"][:9]}).json()["total"] >= 1
    assert client.get("/api/cases", headers=admin, params={"status": "closed"}).json()["total"] == 1
    assert client.get("/api/cases", headers=admin, params={"q": "100%"}).json()["total"] == 0  # '%' is literal, not a wildcard
    page = client.get("/api/cases", headers=admin, params={"page_size": 2, "page": 2, "sort": "title_asc"}).json()
    assert page["total"] == 3 and len(page["items"]) == 1 and page["page"] == 2


def test_cases_of_other_users_are_invisible_and_untouchable(client, admin, user2):
    case = make_case(client, admin)
    cid = case["case_id"]
    assert client.get("/api/cases", headers=user2).json()["total"] == 0
    for method, url, body in [("get", f"/api/cases/{cid}", None), ("patch", f"/api/cases/{cid}", {"title": "Hijacked"}),
                              ("delete", f"/api/cases/{cid}", None), ("get", f"/api/cases/{cid}/notes", None),
                              ("get", f"/api/cases/{cid}/report", None), ("get", f"/api/cases/{cid}/descriptions", None)]:
        r = getattr(client, method)(url, headers=user2, **({"json": body} if body else {}))
        assert r.status_code == 404, (method, url)
    assert client.get(f"/api/cases/{cid}", headers=admin).json()["title"] == case["title"]


def test_admin_can_see_other_users_cases(client, admin, user2):
    cid = make_case(client, user2, title="Bob's case")["case_id"]
    assert client.get(f"/api/cases/{cid}", headers=admin).status_code == 200
    assert client.get("/api/cases", headers=admin).json()["total"] == 1


def test_close_and_reopen(client, admin):
    cid = make_case(client, admin)["case_id"]
    assert client.patch(f"/api/cases/{cid}", headers=admin, json={"status": "closed"}).json()["status"] == "closed"
    blocked = client.patch(f"/api/cases/{cid}", headers=admin, json={"title": "Edited while closed"})
    assert blocked.status_code == 409 and blocked.json()["code"] == "case_closed"
    assert client.post(f"/api/cases/{cid}/notes", headers=admin, json={"body": "x"}).status_code == 409
    reopened = client.patch(f"/api/cases/{cid}", headers=admin, json={"status": "in_progress"}).json()
    assert reopened["status"] == "in_progress"
    assert client.patch(f"/api/cases/{cid}", headers=admin, json={"title": "Edited after reopening"}).status_code == 200
    activity = [a["summary"] for a in client.get("/api/activity", headers=admin).json()]
    assert any("Reopened" in s for s in activity)


def test_empty_update_is_rejected(client, admin):
    cid = make_case(client, admin)["case_id"]
    assert client.patch(f"/api/cases/{cid}", headers=admin, json={}).status_code == 422
    assert client.patch(f"/api/cases/{cid}", headers=admin, json={"title": None}).status_code in (409, 422)


def test_notes_are_append_only_and_attributed(client, admin):
    cid = make_case(client, admin)["case_id"]
    v = generate(client, admin, cid).json()
    n = client.post(f"/api/cases/{cid}/notes", headers=admin, json={"body": "Witness unsure about the glasses.", "sketch_version_id": v["id"]})
    assert n.status_code == 201 and n.json()["author_username"] == "alice" and n.json()["sketch_version_id"] == v["id"]
    assert [x["body"] for x in client.get(f"/api/cases/{cid}/notes", headers=admin).json()] == ["Witness unsure about the glasses."]
    assert client.put(f"/api/cases/{cid}/notes/{n.json()['id']}", headers=admin, json={"body": "x"}).status_code in (404, 405)
    assert client.delete(f"/api/cases/{cid}/notes/{n.json()['id']}", headers=admin).status_code in (404, 405)
    other = make_case(client, admin, title="Another case")["case_id"]
    bad = client.post(f"/api/cases/{other}/notes", headers=admin, json={"body": "x", "sketch_version_id": v["id"]})
    assert bad.status_code == 422  # a note cannot point at another case's sketch


def test_delete_removes_the_case_its_files_and_keeps_an_audit_entry(client, admin, env):
    cid = make_case(client, admin)["case_id"]
    generate(client, admin, cid)
    folder = Path(env) / "storage" / "sketches"
    assert any(folder.rglob("*.png"))
    assert client.delete(f"/api/cases/{cid}", headers=admin).status_code == 204
    assert client.get(f"/api/cases/{cid}", headers=admin).status_code == 404
    assert not any(folder.rglob("*.png"))
    assert any(a["action"] == "case_deleted" and a["case_ref"] == cid for a in client.get("/api/activity", headers=admin).json())


def test_dashboard_numbers_come_from_the_database(client, admin, user2):
    empty = client.get("/api/dashboard", headers=admin).json()
    assert empty["total_cases"] == 0 and empty["sketch_versions"] == 0 and empty["recent_cases"] == []
    a = make_case(client, admin)["case_id"]
    generate(client, admin, a)
    generate(client, admin, a, {"face_shape": "square"})
    b = make_case(client, user2, title="Bob's case")["case_id"]
    client.patch(f"/api/cases/{b}", headers=user2, json={"status": "under_review"})
    mine = client.get("/api/dashboard", headers=user2).json()
    assert mine["scope"] == "own" and mine["total_cases"] == 1 and mine["status_counts"]["under_review"] == 1 and mine["sketch_versions"] == 0
    allc = client.get("/api/dashboard", headers=admin).json()
    assert allc["scope"] == "all" and allc["total_cases"] == 2 and allc["sketch_versions"] == 2
    assert allc["schematic_versions"] == 2 and allc["ai_versions"] == 0 and allc["cases_with_selected_sketch"] == 1
    assert allc["recent_activity"] and ATTRS  # real log rows


# ----------------------------------------------------------------------------- who investigates, who witnessed
def test_a_case_records_who_is_investigating_and_who_the_witness_is(client, admin):
    case = make_case(client, admin, investigator_name="  Inspector   Anita Rao ", witness_name="Ravi Kumar")
    assert case["investigator_name"] == "Inspector Anita Rao"  # spaces trimmed and collapsed
    assert case["witness_name"] == "Ravi Kumar"
    again = client.get(f"/api/cases/{case['case_id']}", headers=admin).json()
    assert (again["investigator_name"], again["witness_name"]) == ("Inspector Anita Rao", "Ravi Kumar")
    listed = client.get("/api/cases", headers=admin).json()["items"][0]
    assert (listed["investigator_name"], listed["witness_name"]) == ("Inspector Anita Rao", "Ravi Kumar")
    recent = client.get("/api/dashboard", headers=admin).json()["recent_cases"][0]
    assert (recent["investigator_name"], recent["witness_name"]) == ("Inspector Anita Rao", "Ravi Kumar")


@pytest.mark.parametrize("missing", ["investigator_name", "witness_name"])
def test_both_names_are_required_when_a_case_is_opened(client, admin, missing):
    body = {k: v for k, v in VALID_BODY.items() if k != missing}
    r = client.post("/api/cases", headers=admin, json=body)
    assert r.status_code == 422 and missing in r.json()["fields"]


@pytest.mark.parametrize("field", ["investigator_name", "witness_name"])
@pytest.mark.parametrize("bad", ["", "A", "   ", "12345", "<script>alert(1)</script>", "Name\u0000", "Ravi; DROP TABLE cases", "x" * 121, "Ravi!"])
def test_names_that_are_empty_too_long_or_contain_markup_are_rejected(client, admin, field, bad):
    r = client.post("/api/cases", headers=admin, json={**VALID_BODY, field: bad})
    assert r.status_code == 422 and field in r.json()["fields"], bad
    assert client.get("/api/cases", headers=admin).json()["total"] == 0  # nothing was created


@pytest.mark.parametrize("good", ["Ravi Kumar", "Dr. A. P. J. Abdul-Kalam", "O'Brien", "ರವಿ ಕುಮಾರ್", "रवि कुमार", "W-01", "Witness 2", "Anne\u2019s", "bob_second"])  # the last: an account name, which the form suggests
def test_real_names_in_any_script_and_neutral_codes_are_accepted(client, admin, good):
    case = make_case(client, admin, witness_name=good)
    assert case["witness_name"] == good  # stored exactly as typed (apart from spaces)


def test_names_can_be_searched_by_the_owner(client, admin):
    make_case(client, admin, title="Alpha case", investigator_name="Inspector Shah", witness_name="Meera Nair")
    make_case(client, admin, title="Beta case", investigator_name="Inspector Rao", witness_name="ರವಿ ಕುಮಾರ್")
    assert [c["title"] for c in client.get("/api/cases", headers=admin, params={"q": "meera"}).json()["items"]] == ["Alpha case"]
    assert [c["title"] for c in client.get("/api/cases", headers=admin, params={"q": "RAO"}).json()["items"]] == ["Beta case"]
    assert client.get("/api/cases", headers=admin, params={"q": "ಕುಮಾರ್"}).json()["total"] == 1
    assert client.get("/api/cases", headers=admin, params={"q": "nobody"}).json()["total"] == 0


def test_names_are_not_searchable_by_other_investigators(client, admin, user2):
    make_case(client, admin, witness_name="Secret Person")
    assert client.get("/api/cases", headers=user2, params={"q": "secret"}).json()["total"] == 0


def test_names_can_be_corrected_but_never_blanked_and_not_while_the_case_is_closed(client, admin):
    cid = make_case(client, admin)["case_id"]
    ok = client.patch(f"/api/cases/{cid}", headers=admin, json={"investigator_name": "Corrected Name", "witness_name": "W-07"}).json()
    assert (ok["investigator_name"], ok["witness_name"]) == ("Corrected Name", "W-07")
    for body in ({"witness_name": None}, {"investigator_name": None}, {"witness_name": "A"}, {"investigator_name": "<b>x</b>"}):
        assert client.patch(f"/api/cases/{cid}", headers=admin, json=body).status_code == 422, body
    client.patch(f"/api/cases/{cid}", headers=admin, json={"status": "closed"})
    blocked = client.patch(f"/api/cases/{cid}", headers=admin, json={"witness_name": "Changed Later"})
    assert blocked.status_code == 409 and blocked.json()["code"] == "case_closed"
    assert client.get(f"/api/cases/{cid}", headers=admin).json()["witness_name"] == "W-07"


def test_names_are_kept_out_of_the_activity_log(client, admin):
    cid = make_case(client, admin, witness_name="Unique Witness Name", investigator_name="Unique Officer Name")["case_id"]
    client.patch(f"/api/cases/{cid}", headers=admin, json={"witness_name": "Another Unique Name"})
    log = " ".join(a["summary"] for a in client.get("/api/activity", headers=admin).json())
    assert cid in log and "Unique" not in log
