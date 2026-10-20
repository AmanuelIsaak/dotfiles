# Jev

A small, cheap model that sits beside Claude Code and Codex: it answers yes/no questions so the agents can skip work or stop mistakes. Every hook lets everything through if Jev is unreachable.

## Install

```sh
ln -s ~/repos/dotfiles/jev ~/.agents/jev           # from a dotfiles clone
cp ~/.agents/jev/.env.example ~/.agents/jev/.env   # add AI_GATEWAY_API_KEY
(cd ~/.agents/jev/fast-jev-compaction && npm install)
~/.agents/jev/install.sh                            # safe to re-run
```

`install.sh` backs up and merges the hooks into `~/.claude/settings.json` and `~/.codex/hooks.json`, and links `~/.local/bin/jev`.

Codex's `PreCompact` and `PostCompact` hooks report when its built-in compaction starts and finishes. Codex does not expose the message replacement used by the Claude `fast-jev-compaction` function hook, so Jev does not select retained messages in Codex. Review and trust new Codex hooks with `/hooks` after installation.

## CLI

- `jev explore "<question>"`: find the files that answer a question about a codebase.
- `jev triage [git diff args]`: LIGHT or FULL before reviewing a diff.
- `jev logs [N]`: tail the hook logs in `log/`.

## Hooks

- `skill_picker`: suggests the one skill that fits the prompt.
- `rule_enforcer`: checks edits against a repo's `.jev-rules.md`.
- `action_gate`: vets shell and MCP commands for destructive or risky actions.
- `done_check`: blocks the agent from claiming it's done when it isn't.

`opencode/` and `vibe_rule_enforcer.py` cover OpenCode and Mistral Vibe. `fast-jev-compaction/` is the Claude Code compaction plugin.

## Tests

```sh
python3 hooks/test_codex_hooks.py
(cd fast-jev-compaction && npm test)
```
