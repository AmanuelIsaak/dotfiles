#!/usr/bin/env bash
# Activates the Jev hooks, skills and compaction plugin for Claude Code and Codex,
# the Jev hooks for OpenCode and Mistral Vibe (when installed), and the `jev` CLI.
# Safe to re-run. Backs up both config files first. The key is read from
# ~/.agents/jev/.env (or AI_GATEWAY_API_KEY); without a working key every hook and
# skill falls back to normal behavior.
set -euo pipefail
J="$HOME/.agents/jev"
ts=$(date +%Y%m%d-%H%M%S)

cp "$HOME/.claude/settings.json" "$HOME/.claude/settings.json.bak-jev-$ts"
[ -f "$HOME/.codex/hooks.json" ] && cp "$HOME/.codex/hooks.json" "$HOME/.codex/hooks.json.bak-jev-$ts"

python3 - "$J" <<'EOF'
import json, os, sys
J = sys.argv[1]
picker = {"type": "command", "command": f"python3 {J}/hooks/skill_picker.py", "timeout": 8}
rules = {"type": "command", "command": f"python3 {J}/hooks/rule_enforcer.py", "timeout": 15}
gate = {"type": "command", "command": f"python3 {J}/hooks/action_gate.py", "timeout": 10}
done = {"type": "command", "command": f"python3 {J}/hooks/done_check.py", "timeout": 12}
compact = {"type": "command", "command": f"python3 {J}/hooks/codex_compaction.py", "timeout": 5}

def merge(path, edit_matcher, extra_env=None, claude_only=False):
    cfg = json.load(open(path)) if os.path.exists(path) else {}
    hooks = cfg.setdefault("hooks", {})
    entries = [("UserPromptSubmit", None, picker), ("PreToolUse", edit_matcher, rules)]
    if claude_only:  # these read the Claude Code transcript format
        entries += [("PreToolUse", "Bash|mcp__.*", gate), ("Stop", None, done)]
    else:
        entries += [("PreCompact", None, compact), ("PostCompact", None, compact)]
    for event, matcher, h in entries:
        groups = hooks.setdefault(event, [])
        if any(x.get("command") == h["command"] for g in groups for x in g.get("hooks", [])):
            continue
        g = {"hooks": [h]}
        if matcher:
            g["matcher"] = matcher
        groups.append(g)
    if extra_env:
        cfg.setdefault("env", {}).update(extra_env)
    json.dump(cfg, open(path, "w"), indent=2)
    print("updated", path)

merge(os.path.expanduser("~/.claude/settings.json"), "Edit|Write|MultiEdit",
      {"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"}, claude_only=True)
merge(os.path.expanduser("~/.codex/hooks.json"), "apply_patch|Edit|Write")
EOF

# explore/triage are plain CLIs (jev explore, jev triage), not skills.
mkdir -p "$HOME/.local/bin"
ln -sfn "$J/bin/jev" "$HOME/.local/bin/jev"

# The compaction plugin reads the key from the environment, and function hooks must be
# enabled when Claude Code starts, so export both from the shell.
grep -q CLAUDE_CODE_ENABLE_FUNCTION_HOOKS "$HOME/.zshrc" 2>/dev/null ||
  echo 'export CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1' >> "$HOME/.zshrc"
grep -q 'agents/jev/.env' "$HOME/.zshrc" 2>/dev/null ||
  echo '[ -f ~/.agents/jev/.env ] && export $(grep -v "^#" ~/.agents/jev/.env | xargs)' >> "$HOME/.zshrc"

claude plugin marketplace add "$J/fast-jev-compaction"
claude plugin install fast-jev-compaction@fast-jev-compaction

# `jev` CLI on PATH (~/.local/bin is on PATH in ~/.zshrc).
mkdir -p "$HOME/.local/bin"
ln -sfn "$J/bin/jev" "$HOME/.local/bin/jev"

# OpenCode: plugin runs the same hooks. Copied, not linked, so plugin discovery finds it.
if [ -d "$HOME/.config/opencode" ]; then
  mkdir -p "$HOME/.config/opencode/plugins"
  cp "$J/opencode/jev.ts" "$HOME/.config/opencode/plugins/jev.ts"
  echo "updated $HOME/.config/opencode/plugins/jev.ts"
fi

# Mistral Vibe: skills already load from ~/.agents/skills; add the rule-enforcer hook.
# Vibe has no prompt-submit hook, so there is no skill picker there.
V="$HOME/.vibe/hooks.toml"
if [ -d "$HOME/.vibe" ] && ! grep -q 'name = "jev-rules"' "$V" 2>/dev/null; then
  [ -f "$V" ] && cp "$V" "$V.bak-jev-$ts"
  cat >> "$V" <<TOML

# Jev rule enforcer: checks edits against .jev-rules.md
[[hooks]]
name = "jev-rules"
type = "pre_tool"
match = "re:edit|write_file"
command = "python3 $J/hooks/vibe_rule_enforcer.py"
timeout = 15
TOML
  echo "updated $V"
fi

echo
echo "Done. Open a new terminal (or restart Claude/Codex/OpenCode/Vibe). Logs: $J/log/"
