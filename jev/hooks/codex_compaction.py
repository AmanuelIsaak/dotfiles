#!/usr/bin/env python3
"""Report Codex compaction lifecycle events without changing its history."""
import json
import os
import sys
import time

LOG = os.path.expanduser("~/.agents/jev/log/codex_compaction.log")


def response(event):
    name = event.get("hook_event_name")
    if name not in ("PreCompact", "PostCompact"):
        return None
    trigger = event.get("trigger")
    if trigger not in ("manual", "auto"):
        trigger = "unknown"
    phase = "started" if name == "PreCompact" else "finished"
    session = event.get("session_id") or "unknown"
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as stream:
            stream.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {session} {trigger} {phase}\n")
    except OSError:
        pass
    return {"systemMessage": f"Codex {trigger} compaction {phase}."}


if __name__ == "__main__":
    try:
        output = response(json.load(sys.stdin))
        if output:
            print(json.dumps(output))
    except (ValueError, TypeError):
        pass
