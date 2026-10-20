#!/usr/bin/env python3
"""UserPromptSubmit hook (Claude Code + Codex): Jev picks the one skill that fits.

Injects a one-line hint as additionalContext. Silent no-op on any failure.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jev  # noqa: E402

MIN_CONFIDENCE = float(os.environ.get("JEV_SKILL_MIN_CONFIDENCE", "0.6"))
LOG = os.path.expanduser("~/.agents/jev/log/skill_picker.log")


def frontmatter(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read(8000)
    except OSError:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return None
    fields, key = {}, None
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            fields[key] = "" if val in (">", "|", ">-", "|-") else val.strip("\"'")
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def skill_dirs(cwd, codex):
    """Only the directories the calling agent actually loads skills from."""
    home = os.path.expanduser("~")
    if codex:
        dirs = [f"{home}/.agents/skills", f"{home}/.codex/skills"]
        local = [".agents/skills", ".codex/skills"]
    else:
        dirs = [f"{home}/.claude/skills"]
        local = [".claude/skills"]
    if cwd:
        dirs += [os.path.join(cwd, d) for d in local]
    return dirs


def disabled_skills(cwd):
    """Claude skills set to "off" in skillOverrides (user, project and local settings)."""
    paths = [os.path.expanduser("~/.claude/settings.json")]
    if cwd:
        paths += [os.path.join(cwd, ".claude", f) for f in ("settings.json", "settings.local.json")]
    off = set()
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                overrides = json.load(f).get("skillOverrides") or {}
        except (OSError, ValueError):
            continue
        off.update(name for name, state in overrides.items() if state == "off")
    return off


def load_skills(cwd, codex):
    skills = {}
    off = set() if codex else disabled_skills(cwd)
    for d in skill_dirs(cwd, codex):
        if not os.path.isdir(d):
            continue
        for entry in sorted(os.listdir(d)):
            fm = frontmatter(os.path.join(d, entry, "SKILL.md"))
            if not fm:
                continue
            name = fm.get("name") or entry
            if fm.get("disable-model-invocation") == "true" or name in off or entry in off:
                continue
            skills.setdefault(name, fm.get("description", "")[:400])
    return skills


def log(line):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + line + "\n")
    except OSError:
        pass


def main():
    event = json.load(sys.stdin)
    prompt = (event.get("prompt") or "").strip()
    if not jev.api_key() or len(prompt) < 12 or prompt.startswith("/"):
        return
    skills = load_skills(event.get("cwd"), codex="turn_id" in event)
    if not skills:
        return
    criteria = dict(skills)
    criteria["none"] = "No skill fits: the request is ordinary coding, a question, or chat."
    started = time.time()
    answer = jev.ask(
        {"user_prompt": prompt[:4000]},
        {"skill": jev.choice(
            "Pick the single agent skill whose description best matches what the user is "
            "asking for in user_prompt. Pick 'none' unless a skill clearly applies.",
            criteria,
        )},
        timeout=5.0,
    )["skill"]
    pick, conf = answer.get("choice"), float(answer.get("confidence") or 0)
    log(f"{int((time.time() - started) * 1000)}ms pick={pick} conf={conf:.2f} prompt={prompt[:80]!r}")
    if not pick or pick == "none" or pick not in skills or conf < MIN_CONFIDENCE:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": f"Skill router (Jev, confidence {conf:.0%}): the `{pick}` skill "
                             f"matches this request. Use it unless it clearly does not apply.",
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block the prompt
        log(f"error: {e}")
    sys.exit(0)
