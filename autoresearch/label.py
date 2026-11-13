#!/usr/bin/env python3
"""
label.py - build the ground truth the autoresearch loop optimises against: YOUR judgement.

    ./venv/bin/python autoresearch/label.py          # label unlabelled jobs, resumable
    ./venv/bin/python autoresearch/label.py --stats  # counts only

Pool = history/applications.csv (jobs the bot applied to) + autoresearch/data/seen_jobs.jsonl
(every job the bot evaluated, captured when you run the bot with AUTOAPPLY_CAPTURE_JDS=1).

Label by "would I genuinely want to apply to this?" - NOT "did the bot apply". The bot's own
decisions are deliberately not shown, so the scorer is never graded against itself.
Keys:  a = apply   s = skip   u = undo last   q = quit
"""
import csv
import json
import os
import sys
import textwrap
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
LABELS = os.path.join(DATA, "labels.jsonl")
SEEN = os.path.join(DATA, "seen_jobs.jsonl")
APPS = os.path.join(ROOT, "history", "applications.csv")


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def pool():
    jobs = {}
    if os.path.exists(APPS):
        csv.field_size_limit(10 ** 8)
        with open(APPS, encoding="utf-8", errors="ignore") as f:
            for r in csv.DictReader(f):
                if r.get("Job ID") and len(r.get("About Job", "")) > 200:
                    jobs[r["Job ID"]] = {"job_id": r["Job ID"], "title": r["Title"], "company": r["Company"],
                                         "description": r["About Job"]}
    for r in read_jsonl(SEEN):
        if len(r.get("description", "")) > 200:
            jobs[str(r["job_id"])] = r
    return jobs


def main():
    os.makedirs(DATA, exist_ok=True)
    labelled = read_jsonl(LABELS)
    done = {str(r["job_id"]) for r in labelled}
    todo = [j for jid, j in pool().items() if jid not in done]
    pos = sum(r["label"] for r in labelled)
    print(f"labelled: {len(labelled)} (apply {pos} / skip {len(labelled) - pos}) | unlabelled in pool: {len(todo)}")
    if "--stats" in sys.argv:
        return
    for i, j in enumerate(todo, 1):
        print("\n" + "=" * 78)
        print(f"[{i}/{len(todo)}] {j['title']}  @  {j['company']}")
        print("-" * 78)
        print(textwrap.shorten(" ".join(j["description"].split()), width=900, placeholder=" ..."))
        while True:
            try:
                k = input("\n(a)pply / (s)kip / (u)ndo / (q)uit > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nsaved; re-run to continue")
                return
            if k in ("a", "s"):
                row = {"job_id": str(j["job_id"]), "title": j["title"], "company": j["company"],
                       "description": j["description"], "label": 1 if k == "a" else 0,
                       "labelled_at": datetime.now().isoformat(timespec="seconds")}
                with open(LABELS, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
                break
            if k == "u":
                rows = read_jsonl(LABELS)
                if rows:
                    rows.pop()
                    with open(LABELS, "w", encoding="utf-8") as f:
                        f.writelines(json.dumps(r) + "\n" for r in rows)
                    print("undid last label (re-run to see it again)")
                continue
            if k == "q":
                return


if __name__ == "__main__":
    main()
