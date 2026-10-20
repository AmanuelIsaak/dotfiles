#!/usr/bin/env python3
"""Cheap first pass before a code review: Jev answers seven yes/no risk questions.

Usage: triage.py [git diff args...]   (default: staged + unstaged changes vs HEAD)
Prints LIGHT or FULL plus the per-question probabilities.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.expanduser("~/.agents/jev"))
import jev  # noqa: E402

FULL_AT = float(os.environ.get("JEV_TRIAGE_FULL_AT", "0.35"))
QUESTIONS = {
    "security": "Does the change touch authentication, authorization, secrets, crypto, input validation, or access to user data?",
    "data": "Does the change alter persisted data: a schema, migration, storage format, or deletion of records?",
    "api": "Does the change alter a public interface, API contract, or behavior that other code or clients depend on?",
    "concurrency": "Does the change add or modify concurrency, async flow, caching, or shared mutable state?",
    "error_paths": "Does the change add or alter error handling, retries, fallbacks, or failure behavior?",
    "rules": "Could the change conflict with project rules or conventions, or do something that should not be changed at all?",
    "logic": "Does the change contain non-trivial new logic (branching, arithmetic, parsing) that could be subtly wrong?",
}


def main():
    args = sys.argv[1:] or ["HEAD"]
    diff = subprocess.run(["git", "diff", *args], capture_output=True, text=True).stdout
    if not diff.strip():
        diff = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True).stdout
    if not diff.strip():
        sys.exit("No diff found.")
    stat = subprocess.run(["git", "diff", "--stat", *args], capture_output=True, text=True).stdout
    questions = {k: jev.boolean(v) for k, v in QUESTIONS.items()}
    try:
        answers = jev.ask({"diff_stat": stat[-3000:], "diff": diff}, questions, timeout=10.0)
    except jev.JevUnavailable as e:
        print(f"FULL  (Jev unavailable: {e})")
        return
    risky = {k: a["p"] for k, a in answers.items() if a["p"] >= FULL_AT}
    verdict = "FULL" if risky or len(diff) > 80_000 else "LIGHT"
    print(verdict)
    for k, a in sorted(answers.items(), key=lambda kv: -kv[1]["p"]):
        print(f"  {k:12} {a['p']:.2f}  {'<- flagged' if k in risky else ''}")


if __name__ == "__main__":
    main()
