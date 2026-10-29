import subprocess
import sys
from pathlib import Path

from PIL import Image

from app.services import custom_dataset as cd
from app.services.description_parser import get_parser
from app.services.evaluation import evaluate_parser

BACKEND = Path(__file__).resolve().parents[1]


def write_image(path: Path, size=(64, 64)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (120, 130, 140)).save(path)


# ----------------------------------------------------------------------------- status / inspection
def test_status_shows_zero_for_datasets_that_are_not_installed(client, admin):
    body = client.get("/api/datasets/status", headers=admin).json()
    by_key = {d["key"]: d for d in body["datasets"]}
    for key in ("cufs", "cufsf", "uom_sgfs"):
        d = by_key[key]
        assert d["installed"] is False and d["records"] == 0 and d["files_found"] is None and d["inspected"] is False
        assert "never downloads" in " ".join(d["notes"]) and d["licence"] and d["access"] and d["citation"] and d["source_url"].startswith("https://")
    assert by_key["custom_attributes"]["installed"] is True and by_key["custom_attributes"]["records"] == 0  # present but not yet inspected
    assert body["totals"]["records"] == 0


def test_only_the_administrator_can_inspect(client, admin, user2):
    assert client.post("/api/datasets/inspect", headers=user2, json={}).status_code == 403
    assert client.post("/api/datasets/inspect", json={}).status_code == 401


def test_inspecting_empty_external_folders_reports_nothing_installed(client, admin):
    res = client.post("/api/datasets/inspect", headers=admin, json={"dataset_key": "cufs"}).json()["results"][0]
    assert res["installed"] is False and res["files_found"] == 0 and any("empty or missing" in n for n in res["notes"])
    d = next(x for x in client.get("/api/datasets/status", headers=admin).json()["datasets"] if x["key"] == "cufs")
    assert d["inspected"] is True and d["files_found"] == 0 and d["records"] == 0


def test_inspection_counts_real_images_and_flags_broken_ones(client, admin, env):
    root = Path(env) / "datasets" / "external" / "cufsf"
    write_image(root / "sketches" / "s1.png")
    write_image(root / "sketches" / "s2.jpg")
    write_image(root / "photos" / "p1.png")
    (root / "photos" / "broken.png").write_bytes(b"this is not an image")
    (root / "notes.txt").write_text("hello")
    res = client.post("/api/datasets/inspect", headers=admin, json={"dataset_key": "cufsf"}).json()["results"][0]
    assert res["installed"] is True and res["files_found"] == 5 and res["valid"] == 3 and res["invalid"] == 1
    assert res["summary"]["by_role"] == {"sketch": 2, "photo": 2} and res["summary"]["other_files"] == 1
    assert [p["record"] for p in res["problems"]] == ["photos/broken.png"]
    d = next(x for x in client.get("/api/datasets/status", headers=admin).json()["datasets"] if x["key"] == "cufsf")
    assert d["records"] == 4 and d["valid_records"] == 3 and d["files_found"] == 5
    assert client.post("/api/datasets/inspect", headers=admin, json={"dataset_key": "cufsf"}).json()["results"][0]["valid"] == 3  # repeatable, no duplicates


def test_custom_dataset_inspection_reports_review_status(client, admin):
    res = client.post("/api/datasets/inspect", headers=admin, json={"dataset_key": "custom_attributes"}).json()["results"][0]
    assert res["files_found"] == 90 and res["valid"] == 90 and res["invalid"] == 0
    assert res["summary"]["translation_review_status"] == {"original": 30, "unreviewed": 60}
    d = next(x for x in client.get("/api/datasets/status", headers=admin).json()["datasets"] if x["key"] == "custom_attributes")
    assert d["translation_review"] == {"original": 30, "unreviewed": 60} and d["records"] == 90 and d["labelled_records"] == 90


# ----------------------------------------------------------------------------- validator
HEADER = ",".join(cd.COLUMNS)


def csv_row(**kw) -> str:
    row = {c: "" for c in cd.COLUMNS}
    row.update(sample_id="R1", group_id="", split="dev", language="en", description_text="A man with a beard.", facial_hair="beard",
               translation_review_status="original", annotation_method="developer_authored", permission_status="synthetic_no_real_person")
    row.update(kw)
    return ",".join('"' + v.replace('"', '""') + '"' for v in row.values())


def validate(tmp_path, *rows, header=HEADER):
    f = tmp_path / "x.csv"
    f.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return cd.validate_file(f)


def errors(report):
    return [e for r in report.rows for e in r.errors]


def test_validator_accepts_a_good_file(tmp_path):
    assert validate(tmp_path, csv_row()).ok


def test_validator_names_every_kind_of_problem(tmp_path):
    cases = [
        (csv_row(face_shape="banana"), "not in the vocabulary"),
        (csv_row(split="holdout"), "split must be"),
        (csv_row(language="fr"), "language must be"),
        (csv_row(description_text=""), "description_text is empty"),
        (csv_row(language="hi", description_text="only english here"), "does not look like 'hi'"),
        (csv_row(translation_review_status="reviewed"), "needs reviewer_id"),
        (csv_row(translation_review_status="original", language="kn", description_text="ಗಡ್ಡ"), "only valid for English"),
        (csv_row(annotation_method="magic"), "annotation_method"),
        (csv_row(permission_status="whatever"), "permission_status"),
        (csv_row(sample_id=""), "sample_id is empty"),
        (csv_row(image_file="../../etc/passwd"), "inside the dataset folder"),
        (csv_row(image_file="missing.png"), "does not exist"),
    ]
    for row, needle in cases:
        report = validate(tmp_path, row)
        assert not report.ok and any(needle in e for e in errors(report)), (needle, errors(report))


def test_validator_checks_duplicates_groups_and_images(tmp_path):
    dup = validate(tmp_path, csv_row(), csv_row())
    assert any("duplicate sample_id" in e for e in errors(dup))
    grp = validate(tmp_path, csv_row(sample_id="A", group_id="G1"), csv_row(sample_id="B", group_id="G1", language="en", facial_hair="none"))
    assert any("labels differ" in e for e in errors(grp))
    write_image(tmp_path / "images" / "ok.png")
    (tmp_path / "images" / "bad.png").write_bytes(b"nope")
    assert validate(tmp_path, csv_row(image_file="images/ok.png")).ok
    assert any("not a usable image" in e for e in errors(validate(tmp_path, csv_row(image_file="images/bad.png"))))


def test_validator_reports_file_level_problems(tmp_path):
    assert any("Missing columns" in e for e in validate(tmp_path, header="sample_id,split").file_errors)
    assert any("not found" in e for e in cd.validate_file(tmp_path / "nope.csv").file_errors)
    f = tmp_path / "latin1.csv"
    f.write_bytes(HEADER.encode() + b"\n\xe9\n")
    assert any("UTF-8" in e for e in cd.validate_file(f).file_errors)
    assert any("no data rows" in e for e in validate(tmp_path).file_errors)


def test_shipped_demo_dataset_is_valid_and_clearly_labelled():
    report = cd.validate_file(BACKEND / "datasets" / "custom" / cd.CSV_NAME)
    assert report.ok and report.total == 90
    assert report.counts("permission_status") == {"synthetic_no_real_person": 90}
    assert report.counts("translation_review_status") == {"original": 30, "unreviewed": 60}  # nothing is marked reviewed automatically
    assert (BACKEND / "datasets" / "custom" / "README.md").read_text(encoding="utf-8").count("SYNTHETIC") >= 1


def test_validator_script_exit_codes(tmp_path):
    script = BACKEND / "scripts" / "validate_custom_dataset.py"
    good = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=BACKEND)
    assert good.returncode == 0 and "RESULT: valid" in good.stdout
    bad = tmp_path / "bad.csv"
    bad.write_text(HEADER + "\n" + csv_row(face_shape="banana") + "\n", encoding="utf-8")
    out = subprocess.run([sys.executable, str(script), str(bad)], capture_output=True, text=True, cwd=BACKEND)
    assert out.returncode == 1 and "INVALID" in out.stdout and "banana" in out.stdout


def test_json_schema_matches_the_vocabulary():
    out = subprocess.run([sys.executable, str(BACKEND / "scripts" / "generate_dataset_schema.py"), "--check"], capture_output=True, text=True, cwd=BACKEND)
    assert out.returncode == 0, out.stdout + out.stderr


# ----------------------------------------------------------------------------- evaluation
def row(sid, text, lang="en", group="", **labels):
    r = {c: "" for c in cd.COLUMNS}
    r.update(sample_id=sid, group_id=group, split="dev", language=lang, description_text=text, translation_review_status="original" if lang == "en" else "unreviewed")
    r.update(labels)
    return r


def test_metrics_are_computed_from_the_examples_and_hand_checkable():
    rows = [
        row("a", "A man with a round face.", apparent_gender="male", face_shape="round"),  # all correct
        row("b", "A man with a round face.", apparent_gender="male", face_shape="square"),  # face_shape wrong -> 1 fp + 1 fn
        row("c", "Nothing useful here.", face_shape="oval"),  # missed -> 1 fn
    ]
    m = evaluate_parser(rows, get_parser())
    assert m["n_examples"] == 3 and m["exact_match"] == round(1 / 3, 4)
    face = next(a for a in m["per_attribute"] if a["attribute"] == "face_shape")
    assert (face["tp"], face["fp"], face["fn"], face["n_gold"]) == (1, 1, 2, 3)
    assert face["precision"] == 0.5 and face["recall"] == round(1 / 3, 4)
    gender = next(a for a in m["per_attribute"] if a["attribute"] == "apparent_gender")
    assert gender["precision"] == 1.0 and gender["recall"] == 1.0
    assert m["by_language"][0]["n"] == 3 and len(m["failures_listed"]) == 2


def test_cross_language_agreement_counts_groups():
    rows = [row("x-en", "A man with a beard.", group="G", facial_hair="beard"), row("x-hi", "आदमी की दाढ़ी", "hi", group="G", facial_hair="beard"),
            row("y-en", "round face", group="H"), row("y-hi", "गोल चेहरा", "hi", group="H")]
    m = evaluate_parser(rows, get_parser())
    assert m["cross_language_agreement"]["groups"] == 2 and 0 < m["cross_language_agreement"]["agreement"] <= 1


def test_metrics_are_null_not_zero_when_undefined():
    m = evaluate_parser([row("a", "Nothing here.")], get_parser())
    assert m["micro_precision"] is None and m["micro_recall"] is None and m["exact_match"] == 1.0


def test_evaluation_run_is_stored_with_n_and_caveats(client, admin):
    assert client.get("/api/evaluations", headers=admin).json() == []  # nothing is pre-filled
    r = client.post("/api/evaluations", headers=admin, json={"split": "dev"})
    run = r.json()
    assert r.status_code == 201 and run["n_examples"] == 51 and run["split"] == "dev" and run["status"] == "completed"
    assert run["metrics"]["n_examples"] == 51 and run["metrics"]["caveats"] and run["dataset_version"]
    assert {l["language"]: l["n"] for l in run["metrics"]["by_language"]} == {"en": 17, "hi": 17, "kn": 17}
    assert all(l["translation_reviewed_n"] in (0,) for l in run["metrics"]["by_language"] if l["language"] != "en")
    assert any("same developer" in c for c in run["metrics"]["caveats"])
    again = client.post("/api/evaluations", headers=admin, json={"split": "test"}).json()
    listed = client.get("/api/evaluations", headers=admin).json()
    assert [e["id"] for e in listed] == [again["id"], run["id"]] and again["n_examples"] == 39


def test_only_reviewed_translations_filters_to_originals_until_someone_reviews(client, admin):
    run = client.post("/api/evaluations", headers=admin, json={"split": "all", "only_reviewed_translations": True}).json()
    assert run["n_examples"] == 30 and [l["language"] for l in run["metrics"]["by_language"]] == ["en"]


def test_evaluation_requires_admin_and_a_valid_dataset(client, admin, user2, env):
    assert client.post("/api/evaluations", headers=user2, json={}).status_code == 403
    (Path(env) / "datasets" / "custom" / cd.CSV_NAME).write_text("garbage", encoding="utf-8")
    r = client.post("/api/evaluations", headers=admin, json={})
    assert r.status_code == 422 and r.json()["code"] == "dataset_invalid"
    assert client.get("/api/evaluations", headers=admin).json() == []  # a failed run stores nothing


# ----------------------------------------------------------------------------- skin colour in the dataset
def shipped_rows() -> list[dict]:
    return [r.row for r in cd.validate_file(BACKEND / "datasets" / "custom" / cd.CSV_NAME).rows]


def test_skin_colour_is_labelled_only_where_the_text_says_so():
    rows = shipped_rows()
    labelled = [r for r in rows if r["skin_colour"]]
    assert {r["skin_colour"] for r in labelled} == {"white", "brown", "black"}
    assert len(labelled) == 18 and {r["split"] for r in labelled} == {"dev", "test"}  # 6 faces x 3 languages, both splits
    # the first 24 faces never mention skin (their "white" / "grey" is hair), so they carry no skin label
    assert all(not r["skin_colour"] for r in rows if int(r["group_id"][1:]) <= 24)


def test_every_skin_colour_row_is_read_correctly_and_nothing_else_is_read_as_skin():
    m = evaluate_parser(shipped_rows(), get_parser())
    skin = next(a for a in m["per_attribute"] if a["attribute"] == "skin_colour")
    assert (skin["n_gold"], skin["tp"], skin["fp"], skin["fn"]) == (18, 18, 0, 0)


def test_a_vocabulary_1_0_file_without_the_skin_colour_column_is_still_valid_and_says_so(tmp_path):
    header = ",".join(c for c in cd.COLUMNS if c != "skin_colour")
    line = ",".join('"' + v + '"' for c, v in zip(cd.COLUMNS, csv_row().replace('"', "").split(",")) if c != "skin_colour")
    report = validate(tmp_path, line, header=header)
    assert report.ok and any("skin_colour" in n and "vocabulary 1.0" in n for n in report.notes)
    assert not validate(tmp_path, csv_row()).notes  # a current file has nothing to remark on
