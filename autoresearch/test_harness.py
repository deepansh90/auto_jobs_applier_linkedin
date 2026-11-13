"""
Harness self-tests. Run: ./venv/bin/python -m pytest autoresearch/test_harness.py -q
These protect the *evaluator*, not the scorer: if they fail, results from prepare.py cannot be trusted.
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import prepare  # noqa: E402
from applybot.job_matcher import score_job_match as production_score  # noqa: E402
import candidate_scorer  # noqa: E402

FIXTURES = prepare.load_labels(prepare.SMOKE_LABELS)

RESUME = {
    "title": "Staff AI Engineer | Lead AI Engineer",
    "skills": {"technologies": ["Python", "Kafka", "AWS", "LLM", "RAG", "Docker"]},
}
CFG = {"search_terms": ["Agentic AI Architect"]}


def test_baseline_matches_production_on_fixtures():
    """A 'baseline' experiment must reproduce today's bot behaviour exactly."""
    assert FIXTURES, "fixtures missing"
    for r in FIXTURES:
        assert candidate_scorer.score_job_match(r["title"], r["description"], RESUME, CFG) == \
            production_score(r["title"], r["description"], RESUME, CFG), r["job_id"]


@pytest.mark.parametrize("title,desc", [
    ("", ""), ("Staff AI Engineer", ""), ("Principal Engineer", "python " * 500),
])
def test_baseline_matches_production_on_edge_cases(title, desc):
    assert candidate_scorer.score_job_match(title, desc, RESUME, CFG) == production_score(title, desc, RESUME, CFG)


def test_auc_known_values():
    assert prepare.auc([9, 8, 2, 1], [1, 1, 0, 0]) == 1.0
    assert prepare.auc([1, 2, 8, 9], [1, 1, 0, 0]) == 0.0
    assert prepare.auc([5, 5, 5, 5], [1, 1, 0, 0]) == 0.5


def test_split_is_stable_and_disjoint():
    ids = [f"job{i}" for i in range(200)]
    held = [i for i in ids if prepare.is_holdout(i)]
    assert held == [i for i in ids if prepare.is_holdout(i)]
    assert 20 < len(held) < 60  # ~20%


def test_smoke_run_succeeds_and_flags_itself():
    out = subprocess.run([sys.executable, os.path.join(HERE, "prepare.py"), "--smoke"],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "SMOKE MODE" in out.stdout and "dev_auc" in out.stdout and "guardrails" in out.stdout


def test_real_run_refuses_without_enough_labels(tmp_path, monkeypatch):
    """With no/too few real labels the evaluator must exit 2, never print a misleading number."""
    monkeypatch.setattr(prepare, "LABELS", str(tmp_path / "none.jsonl"))
    monkeypatch.setattr(sys, "argv", ["prepare.py"])
    with pytest.raises(SystemExit) as e:
        prepare.main()
    assert e.value.code == 2


@pytest.mark.parametrize("snippet", [
    "import requests\n", "import os\n", "import importlib\n", "from json import load\n",
    "x = open('f')\n", "y = getattr(re, 'sub')\n", "JOB = 'SYN-001'\n", "C = 'synthetic org 3'\n",
    "def broken(:\n",
])
def test_guardrails_reject_cheating_scorers(snippet, tmp_path, monkeypatch):
    bad = tmp_path / "candidate_scorer.py"
    bad.write_text(open(prepare.SCORER).read() + "\n" + snippet)
    monkeypatch.setattr(prepare, "SCORER", str(bad))
    with pytest.raises(SystemExit) as e:
        prepare.guard_source(FIXTURES)
    assert e.value.code == 1


def test_guardrails_allow_clean_scorer_and_ignore_comments(tmp_path, monkeypatch):
    ok = tmp_path / "candidate_scorer.py"
    ok.write_text(open(prepare.SCORER).read() + "\nimport math\n# synthetic org 3 and SYN-001 only in a comment\n")
    monkeypatch.setattr(prepare, "SCORER", str(ok))
    prepare.guard_source(FIXTURES)  # must not raise


def test_smoke_config_does_not_depend_on_personal_resume(monkeypatch):
    monkeypatch.setattr(prepare, "ROOT", "/nonexistent")
    resume, cfg, threshold = prepare.load_config(smoke=True)
    assert resume["skills"]["technologies"] and threshold == 60 and cfg["search_terms"]
