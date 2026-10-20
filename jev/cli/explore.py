#!/usr/bin/env python3
"""Find the files most relevant to a question: ripgrep candidates, Jev ranks them.

Usage: explore.py "<question>" [--dir DIR] [--top N] [--terms a,b,c]
"""
import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.expanduser("~/.agents/jev"))
import jev  # noqa: E402

BATCH = 20
MAX_CANDIDATES = 120
LEVELS = ["unrelated", "mentions the topic in passing", "related", "central: where this is implemented or defined"]
STOP = set("""the a an and or of to in on for with from by at is are was were be been how what where
which who why does do did can could should would this that these those it its into about when then than
file files code find show me my our we i you your there here some any all use used using get set make
work works function class method""".split())


def terms_from(question):
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", question)
    out = []
    for w in words:
        if w.lower() in STOP:
            continue
        out.append(w)
        parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", w)  # camelCase / snake parts
        out += [p for p in parts if len(p) > 3 and p.lower() not in STOP and p != w]
    seen, uniq = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return uniq[:12]


def rg(args, cwd):
    # Explicit path + no stdin: rg searches stdin when it is not a tty (agents, hooks).
    r = subprocess.run(["rg", *args] if "--" in args else ["rg", *args, "."], cwd=cwd,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    return r.stdout.splitlines()


def candidates(terms, root):
    hits = {}
    pat = []
    for t in terms:
        pat += ["-e", re.escape(t)]
    for line in rg(["-i", "-c", "--no-messages", *pat], root):
        path, _, n = line.rpartition(":")
        if n.isdigit():
            hits[path] = hits.get(path, 0) + int(n)
    lowered = [t.lower() for t in terms]
    for path in rg(["--files"], root):  # file-name matches count extra
        name = os.path.basename(path).lower()
        if any(t in name for t in lowered):
            hits[path] = hits.get(path, 0) + 25
    return sorted(hits.items(), key=lambda kv: -kv[1])[:MAX_CANDIDATES]


def snippet(path, terms, root):
    pat = []
    for t in terms:
        pat += ["-e", re.escape(t)]
    lines = rg(["-i", "-n", "-m", "6", "--no-messages", *pat, "--", path], root)
    return "\n".join(l[:200] for l in lines)


def rank(question, cands, terms, root):
    snippets = {p: snippet(p, terms, root) for p, _ in cands}
    batches = [cands[i:i + BATCH] for i in range(0, len(cands), BATCH)]

    def run(batch):
        qs = {f"f{i}": jev.score(
            f"How relevant is the file `{p}` to the question in state? Matching lines:\n{snippets[p]}",
            LEVELS) for i, (p, _) in enumerate(batch)}
        ans = jev.ask({"question": question}, qs, timeout=10.0)
        return [(p, jev.expected_score(ans[f"f{i}"], LEVELS)) for i, (p, _) in enumerate(batch)]

    with ThreadPoolExecutor(max_workers=6) as pool:
        scored = [x for r in pool.map(run, batches) for x in r]
    return sorted(scored, key=lambda kv: -kv[1]), snippets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--dir", default=".")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--terms", help="comma-separated search terms (overrides extraction)")
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    terms = [t.strip() for t in a.terms.split(",")] if a.terms else terms_from(a.question)
    if not terms:
        sys.exit("No search terms; pass --terms.")
    cands = candidates(terms, root)
    print(f"terms: {', '.join(terms)} | candidates: {len(cands)}")
    if not cands:
        print("No keyword matches. Retry with --terms using likely identifiers.")
        return
    started = time.time()
    try:
        ranked, snippets = rank(a.question, cands, terms, root)
        print(f"ranked by Jev in {time.time() - started:.1f}s\n")
    except jev.JevUnavailable as e:
        print(f"Jev unavailable ({e}); ranked by keyword hits instead\n")
        ranked = [(p, n) for p, n in cands]
        snippets = {p: snippet(p, terms, root) for p, _ in ranked[:a.top]}
    for p, s in ranked[:a.top]:
        label = f"{s:.2f}" if isinstance(s, float) else f"{s} hits"
        print(f"== {p}  [{label}]")
        print("\n".join("   " + l for l in snippets[p].splitlines()[:4]))


if __name__ == "__main__":
    main()
