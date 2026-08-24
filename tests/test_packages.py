import pytest

from core import packages as P


@pytest.fixture()
def pkg():
    return P.new_package(subject="test_subject", title="My Quiz", level="Undergraduate")


def _fill_valid(pkg):
    P.add_mcq(pkg, "What is 2+2?", {"A": "3", "B": "4"}, "B")
    P.add_essay(pkg, "Explain X.", ["x"], [{"keyword": "x", "weight": 1}], total_points=1)


def test_new_package_canonical_key(pkg):
    assert pkg["package_key"] == "test_subject/my_quiz"
    assert pkg["status"] == "draft" and pkg["version"] == 1


def test_add_mcq_normalizes_options(pkg):
    P.add_mcq(pkg, "Q?", {"a)": "x", " b ": "y"}, "b")
    mcq = pkg["mcqs"][0]
    assert list(mcq["options"]) == ["A", "B"]
    assert mcq["correct_option"] == "B"


def test_validation_catches_bad_correct_option(pkg):
    pkg["mcqs"].append({"id": "m1", "question": "Q?", "options": {"A": "x"},
                        "correct_option": "Z"})
    issues = P.validate_package(pkg)
    messages = " ".join(i["message"] for i in issues)
    assert "needs 2-5 options" in messages
    assert "correct_option 'Z'" in messages


def test_validation_rejects_duplicate_ids_and_negative_weights(pkg):
    _fill_valid(pkg)
    pkg["mcqs"].append(dict(pkg["mcqs"][0]))
    pkg["essay"][0]["rubric"]["criteria"].append({"keyword": "y", "weight": -2})
    issues = P.validate_package(pkg)
    messages = [i["message"] for i in issues if i["severity"] == "error"]
    assert any("duplicate question id" in m for m in messages)
    assert any("non-negative" in m for m in messages)


def test_validation_package_key_must_match(pkg):
    pkg["package_key"] = "other/other"
    issues = P.validate_package(pkg)
    assert any("package_key" in i["message"] for i in issues)


def test_publish_requires_no_errors_then_immutability(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "DATABASE_DIR", tmp_path)
    pkg = P.new_package(subject="s", title="quiz")
    _fill_valid(pkg)

    broken = dict(pkg)
    broken["mcqs"] = [{"id": "", "question": "?", "options": {}, "correct_option": ""}]
    P.save_package(broken)
    with pytest.raises(ValueError):
        P.publish_package("s", "quiz")

    P.save_package({**pkg})
    snap1 = P.publish_package("s", "quiz")
    assert snap1["version"] == 1 and snap1["status"] == "published"

    working = P.load_package("s", "quiz")
    working["mcqs"].append({
        "id": "mcq_extra", "kind": "mcq", "question": "New?",
        "options": {"A": "a", "B": "b"}, "correct_option": "A",
        "difficulty": "easy", "learning_objective": "",
        "slide_refs": [], "node_links": [],
    })
    P.save_package(working)
    snap2 = P.publish_package("s", "quiz")

    v1 = P.load_published_version("s", "quiz", 1)
    v2 = P.load_published_version("s", "quiz", 2)
    assert len(v1["mcqs"]) == 1 and len(v2["mcqs"]) == 2
    assert snap2["version"] == 2
    assert snap2["content_hash"] != snap1["content_hash"]

    same_again = P.publish_package("s", "quiz")
    assert same_again["version"] == 2


def test_start_next_draft_bumps_version(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "DATABASE_DIR", tmp_path)
    pkg = P.new_package(subject="s", title="draft flow")
    P.save_package(pkg)
    P.publish_package("s", "draft_flow")
    nxt = P.start_next_draft("s", "draft_flow")
    assert nxt["status"] == "draft" and nxt["version"] == 2


def test_list_packages_finds_seeded_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "DATABASE_DIR", tmp_path)
    pkg = P.new_package(subject="math", title="Algebra Basics")
    P.save_package(pkg)
    found = P.list_packages()
    assert [(f["subject"], f["package_id"]) for f in found] == [("math", "algebra_basics")]
