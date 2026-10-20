#!/usr/bin/env python3
"""PreToolUse hook (Claude Code + Codex): Jev checks each edit against file rules.

Rules live in `.jev-rules.md` files; every one between the edited file and the
repo root applies. Each bullet (`- ` or `* `) is one rule. If Jev is at least
JEV_RULE_BLOCK_AT (default 0.8) sure a rule is broken, the edit is denied with
the rule named. Fails open: no key, no rules, or any error lets the edit through.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jev  # noqa: E402

BLOCK_AT = float(os.environ.get("JEV_RULE_BLOCK_AT", "0.8"))
RULES_FILE = ".jev-rules.md"
MAX_RULES = 40
LOG = os.path.expanduser("~/.agents/jev/log/rule_enforcer.log")


def log(line):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + line + "\n")
    except OSError:
        pass


def split_patch(patch):
    """Codex apply_patch text -> {path: change text}."""
    changes, path, buf = {}, None, []
    for line in patch.splitlines():
        m = re.match(r"^\*\*\* (Add|Update|Delete) File: (.+)$", line)
        if m:
            if path:
                changes[path] = "\n".join(buf)
            path, buf = m.group(2).strip(), [line]
        elif path and not line.startswith("*** End Patch"):
            buf.append(line)
    if path:
        changes[path] = "\n".join(buf)
    return changes


def edits_from(event):
    """-> {path: human-readable description of the change}."""
    tool, ti = event.get("tool_name", ""), event.get("tool_input") or {}
    if isinstance(ti, str):
        ti = {"input": ti}
    path = ti.get("file_path")
    if tool == "Write" and path:
        return {path: "NEW FILE CONTENT:\n" + (ti.get("content") or "")}
    if tool == "Edit" and path:
        return {path: f"REPLACE:\n{ti.get('old_string', '')}\nWITH:\n{ti.get('new_string', '')}"}
    if tool == "MultiEdit" and path:
        return {path: "\n\n".join(
            f"REPLACE:\n{e.get('old_string', '')}\nWITH:\n{e.get('new_string', '')}"
            for e in ti.get("edits") or [])}
    for v in ti.values():  # Codex apply_patch: the patch text is in one string field
        if isinstance(v, str) and "*** Begin Patch" in v:
            return split_patch(v)
    return {}


def repo_root(start):
    d = start
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d or d == os.path.expanduser("~"):
            return d
        d = parent


def rules_for(abs_path):
    d = os.path.dirname(abs_path)
    root = repo_root(d)
    rules = []
    while True:
        f = os.path.join(d, RULES_FILE)
        if os.path.isfile(f):
            rel = os.path.relpath(f, root)
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    m = re.match(r"^\s*[-*]\s+(.+)$", line)
                    if m:
                        rules.append((rel, m.group(1).strip()))
        if d == root or os.path.dirname(d) == d:
            return rules[:MAX_RULES]
        d = os.path.dirname(d)


def main():
    event = json.load(sys.stdin)
    cwd = event.get("cwd") or os.getcwd()
    violations = []
    for path, change in edits_from(event).items():
        abs_path = path if os.path.isabs(path) else os.path.join(cwd, path)
        rules = rules_for(abs_path)
        if not rules:
            continue
        if not jev.api_key():
            log(f"skip (no key) {path}: {len(rules)} rules unchecked")
            return
        questions = {
            f"r{i}": jev.boolean(
                f"Does the proposed change to file_path break this rule: {rule}",
                true="The change clearly does something the rule forbids, or omits something it requires.",
                false="The change complies with the rule, or the rule does not apply to it.",
            )
            for i, (_, rule) in enumerate(rules)
        }
        started = time.time()
        answers = jev.ask({"file_path": os.path.relpath(abs_path, cwd),
                           "file_already_exists": os.path.exists(abs_path),
                           "change": change[:20000]},
                          questions, timeout=8.0)
        scores = {q: a["p"] for q, a in answers.items()}
        log(f"{int((time.time() - started) * 1000)}ms {path} " +
            " ".join(f"{q}={p:.2f}" for q, p in scores.items()))
        for i, (src, rule) in enumerate(rules):
            if scores[f"r{i}"] >= BLOCK_AT:
                violations.append(f"- {rule}  ({src}, Jev {scores[f'r{i}']:.0%} sure) — edit to {path}")
    if violations:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Blocked by project rules (Jev rule enforcer):\n"
                                        + "\n".join(violations)
                                        + "\nRevise the change so it follows these rules.",
        }}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail open
        log(f"error: {e}")
    sys.exit(0)
