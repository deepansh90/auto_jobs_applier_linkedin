#!/usr/bin/env python3
"""
prepare.py - FROZEN EVALUATOR. The agent must never modify this file, labels.jsonl, or master_resume.json.

Scores autoresearch/candidate_scorer.py against YOUR labelled jobs (apply / skip) and prints one
headline number (dev_auc, higher is better) plus guardrails.

    ./venv/bin/python autoresearch/prepare.py            # dev split  (what the agent loops on)
    ./venv/bin/python autoresearch/prepare.py --holdout  # held-out split (HUMAN ONLY, run once at the end)
    ./venv/bin/python autoresearch/prepare.py --smoke    # synthetic fixtures; only proves the harness works

Exit codes: 0 ok | 1 crash/guardrail violation | 2 not enough labels
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LABELS = os.path.join(HERE, "data", "labels.jsonl")
SMOKE_LABELS = os.path.join(HERE, "fixtures", "synthetic_labels.jsonl")
SCORER = os.path.join(HERE, "candidate_scorer.py")

MIN_DEV_LABELS = 30        # below this the number is noise - refuse to produce one
MIN_PER_CLASS = 8
MIN_HOLDOUT_LABELS = 15    # holdout is ~20% of labels; ~75+ total labels unlocks it
MIN_HOLDOUT_PER_CLASS = 5
RECALL_FLOOR = 0.80        # guardrail cap: never required to exceed 80% recall...
# ...and never required to beat production either: the effective floor is min(RECALL_FLOOR, production recall),
# i.e. "do not recall fewer of the jobs you'd apply to than the bot does today".


def effective_floor(production_recall):
    return min(RECALL_FLOOR, production_recall)


def production_scores(split, master_resume, config):
    """Score the split with the REAL production scorer: the honest baseline, never a stale copy."""
    sys.path.insert(0, ROOT)
    from applybot.job_matcher import score_job_match as production
    return [production(r["title"], r["description"], master_resume, config) for r in split]
TIME_BUDGET_S = 10.0
HOLDOUT_MOD = 5            # job_id hash % 5 == 0  -> holdout (20%), stable across runs


def die(code, msg):
    print(f"ERROR: {msg}")
    sys.exit(code)


def is_holdout(job_id):
    return int(hashlib.sha1(str(job_id).encode()).hexdigest(), 16) % HOLDOUT_MOD == 0


def load_labels(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_config(smoke=False):
    if smoke:  # never depend on the gitignored, personal master_resume.json
        with open(os.path.join(HERE, "fixtures", "synthetic_resume.json"), encoding="utf-8") as f:
            fx = json.load(f)
        return fx["master_resume"], {"search_terms": fx["search_terms"], "min_job_relevance_score": 60}, 60
    resume_path = os.path.join(ROOT, "config", "master_resume.json")
    if not os.path.exists(resume_path):
        die(1, f"missing {resume_path}")
    with open(resume_path, encoding="utf-8") as f:
        master_resume = json.load(f)
    config = {}
    overlay = os.path.join(ROOT, "config", "user.settings.json")
    if os.path.exists(overlay):
        with open(overlay, encoding="utf-8") as f:
            config["search_terms"] = json.load(f).get("search_terms", [])
    threshold = 60
    settings_py = os.path.join(ROOT, "config", "settings.py")
    if os.path.exists(settings_py):
        m = re.search(r"^min_job_relevance_score\s*=\s*(\d+)", open(settings_py, encoding="utf-8").read(), re.M)
        if m:
            threshold = int(m.group(1))
    config["min_job_relevance_score"] = threshold
    return master_resume, config, threshold


def auc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


ALLOWED_IMPORTS = {"re", "math", "collections", "itertools", "functools", "string", "statistics"}
BANNED_CALLS = {"open", "eval", "exec", "compile", "__import__", "getattr", "setattr", "globals", "locals", "vars"}


def guard_source(rows):
    """Reject scorers that smuggle in I/O, network, dynamic code, or memorised labels.
    Best-effort against a well-meaning agent, not a security boundary."""
    try:
        tree = ast.parse(open(SCORER, encoding="utf-8").read())
    except SyntaxError as e:
        die(1, f"candidate_scorer.py has a syntax error: {e}")
    literals = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [(node.module or "").split(".")[0]]
        else:
            mods = []
        for m in mods:
            if m not in ALLOWED_IMPORTS:
                die(1, f"guardrail: import '{m}' not allowed; use only {sorted(ALLOWED_IMPORTS)}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            die(1, f"guardrail: call to '{node.func.id}' not allowed in candidate_scorer.py")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value.lower())
    for r in rows:
        job_id = str(r["job_id"]).lower()
        if any(job_id in lit for lit in literals):
            die(1, f"guardrail: scorer hardcodes labelled job id {r['job_id']}")
        company = (r.get("company") or "").strip().lower()
        if len(company) >= 4 and any(re.search(r"\b" + re.escape(company) + r"\b", lit) for lit in literals):
            die(1, f"guardrail: scorer hardcodes labelled company '{company}'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true", help="evaluate the held-out split (human only)")
    ap.add_argument("--smoke", action="store_true", help="use synthetic fixtures (harness check only)")
    args = ap.parse_args()

    rows = load_labels(SMOKE_LABELS if args.smoke else LABELS)
    if args.smoke:
        print("!!! SMOKE MODE: synthetic data. This number means NOTHING - never tune on it. !!!")
    split = [r for r in rows if is_holdout(r["job_id"]) == args.holdout]
    n_pos = sum(1 for r in split if r["label"] == 1)
    n_neg = len(split) - n_pos
    # The holdout is only ~20% of all labels, so it gets a lower bar (and a warning) - otherwise the
    # overfitting check would stay locked until ~150 labels.
    min_n, min_cls = (MIN_HOLDOUT_LABELS, MIN_HOLDOUT_PER_CLASS) if args.holdout else (MIN_DEV_LABELS, MIN_PER_CLASS)
    if not args.smoke and (len(split) < min_n or n_pos < min_cls or n_neg < min_cls):
        die(2, f"only {len(split)} labels in this split ({n_pos} apply / {n_neg} skip); need >= {min_n} "
               f"with >= {min_cls} per class. Run: ./venv/bin/python autoresearch/label.py")
    if args.holdout and len(split) < MIN_DEV_LABELS:
        print(f"!!! HOLDOUT HAS ONLY {len(split)} LABELS: a sanity check for gross overfitting, not a measurement. "
              f"Expect +/-0.1 AUC noise; label more jobs for a firm answer. !!!")

    guard_source(rows)
    master_resume, config, threshold = load_config(smoke=args.smoke)

    spec = importlib.util.spec_from_file_location("candidate_scorer", SCORER)
    mod = importlib.util.module_from_spec(spec)
    t0 = time.time()
    try:
        spec.loader.exec_module(mod)
        run1 = [mod.score_job_match(r["title"], r["description"], master_resume, config) for r in split]
        run2 = [mod.score_job_match(r["title"], r["description"], master_resume, config) for r in split]
    except Exception as e:  # a crash is a result, not a reason to touch this file
        die(1, f"candidate_scorer crashed: {type(e).__name__}: {e}")
    elapsed = time.time() - t0
    if run1 != run2:
        die(1, "guardrail: scorer is non-deterministic")
    if elapsed > TIME_BUDGET_S:
        die(1, f"guardrail: eval took {elapsed:.1f}s (> {TIME_BUDGET_S}s budget)")
    if any((not isinstance(s, (int, float))) or s < 0 or s > 100 for s in run1):
        die(1, "guardrail: scores must be numbers in [0, 100]")

    labels = [r["label"] for r in split]
    tp = sum(1 for s, l in zip(run1, labels) if s >= threshold and l == 1)
    fp = sum(1 for s, l in zip(run1, labels) if s >= threshold and l == 0)
    recall = tp / n_pos if n_pos else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    base = production_scores(split, master_resume, config)
    base_tp = sum(1 for s, l in zip(base, labels) if s >= threshold and l == 1)
    base_recall = base_tp / n_pos if n_pos else float("nan")
    floor = effective_floor(base_recall)
    ok = recall >= floor - 1e-9

    print("---")
    print(f"{'holdout' if args.holdout else 'dev'}_auc:".ljust(22) + f"{auc(run1, labels):.4f}")
    print("recall_at_threshold:".ljust(22) + f"{recall:.3f}   (floor {floor:.3f} = min({RECALL_FLOOR}, production))")
    print("production_auc:".ljust(22) + f"{auc(base, labels):.4f}   (today's bot; your gain = dev_auc - this)")
    print("precision_at_threshold:".ljust(22) + f"{precision:.3f}")
    print("threshold:".ljust(22) + f"{threshold}")
    print("n:".ljust(22) + f"{len(split)} (apply {n_pos} / skip {n_neg})")
    print("eval_seconds:".ljust(22) + f"{elapsed:.2f}")
    print("guardrails:".ljust(22) + ("PASS" if ok else "FAIL (recalls fewer wanted jobs than production -> discard)"))
    sys.exit(0)


if __name__ == "__main__":
    main()
