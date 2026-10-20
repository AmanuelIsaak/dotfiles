#!/usr/bin/env python3
"""Mistral Vibe pre_tool hook: adapts Vibe's hook protocol to rule_enforcer.

Vibe names the tools `edit`/`write_file` and expects {"decision", "reason"};
rule_enforcer speaks the Claude Code shape. Fails open like rule_enforcer.
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rule_enforcer  # noqa: E402

TOOLS = {"edit": "Edit", "write_file": "Write"}


def main():
    event = json.load(sys.stdin)
    event["tool_name"] = TOOLS.get(event.get("tool_name"), event.get("tool_name"))
    sys.stdin = io.StringIO(json.dumps(event))
    out = io.StringIO()
    with redirect_stdout(out):
        rule_enforcer.main()
    h = (json.loads(out.getvalue()) if out.getvalue().strip() else {}).get("hookSpecificOutput", {})
    if h.get("permissionDecision") == "deny":
        print(json.dumps({"decision": "deny", "reason": h.get("permissionDecisionReason", "")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail open
        rule_enforcer.log(f"vibe error: {e}")
    sys.exit(0)
