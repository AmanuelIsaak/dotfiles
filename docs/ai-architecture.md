# AI agent architecture

How the Claude Code setup in `home/.claude` and `home/.agents` fits together, with shared Jev hooks also used by Codex. Snapshot of 2026-10-08.

```mermaid
flowchart TB
    user([You in Ghostty / herdr]) --> cc

    subgraph cc["Claude Code (model: opus, effort: low, auto mode)"]
        direction TB
        prompt[Prompt] --> loop[Agent loop]
        loop --> tools[Tool calls]
        loop --> stop[Reply / stop]
    end

    subgraph instr["Instructions (~/.claude)"]
        claudemd[.agents/AGENTS.md<br/>plain writing · CLI over MCP · zero-cost CI · token discipline]
        memory[projects/*/memory<br/>per-project memories, not in repo]
    end
    instr -.loaded every session.-> loop

    subgraph hooks["Jev hooks (~/.agents/jev/hooks, settings.json)"]
        picker[skill_picker.py<br/>UserPromptSubmit: hints one skill]
        rules[rule_enforcer.py<br/>PreToolUse Edit/Write: per-repo .jev-rules.md]
        gate[action_gate.py<br/>PreToolUse Bash/MCP: destructive, exfil, injection, scope]
        done[done_check.py<br/>Stop: blocks false 'done']
        herdr[herdr-agent-state.sh<br/>SessionStart: pane status]
    end
    prompt --> picker
    tools --> rules
    tools --> gate
    stop --> done
    cc --> herdr

    jevapi[(Jev evaluation model<br/>Vercel AI Gateway<br/>key in ~/.agents/jev/.env)]
    picker & rules & gate & done --> jevapi

    subgraph skills["Skills (~/.claude/skills → ~/.agents/skills)"]
        coding[surgical-patch · safe-refactor · lean-build<br/>migration · investigate-first · verify-and-stop]
        misc[youtube-summary · find-skills<br/>caveman-commit]
        matt[grilling, manual only · wizard<br/>from mattpocock/skills, edited locally]
        off[caveman · cavecrew · caveman-review/compress/explore<br/>disabled via skillOverrides]
    end
    picker -.suggests.-> skills
    loop --> skills

    subgraph clis["CLIs used from Bash"]
        jevcli[jev explore · jev triage · jev logs<br/>~/.local/bin/jev]
        caveman[caveman learn/status]
        other[gh · rg · fd · yt-dlp · gradle · xcodebuild]
    end
    tools --> clis
    jevcli --> jevapi

    subgraph plugins["Plugins"]
        compaction[fast-jev-compaction<br/>Jev-scored context pruning]
        lsp[swift-lsp · kotlin-lsp]
    end
    compaction --> jevapi
    loop --> plugins

    subgraph mcp["MCP connectors (claude.ai)"]
        coros[COROS] --- strava[Strava] --- docs[Claude Docs]
    end
    tools --> mcp

    ci[[GitHub Actions on self-hosted Mac runner<br/>~/actions-runners/&lt;repo&gt;]]
    clis --> ci

    codex["Codex (same AGENTS.md, same skills)"]
    user --> codex
    codex --> picker & rules & gate & done

    meter[context-meter/ctx.py<br/>status line bar · yellow 60k · red 100k → /compact]
    cc --> meter
    codex --> meter
    meter -.pane title.-> herdrpane([herdr pane])
```

## Layers

| Layer | Where | Role |
|---|---|---|
| Instructions | `.agents/AGENTS.md` (Claude imports it from `.claude/CLAUDE.md`; `.codex/AGENTS.md` links to it) | Global defaults: short replies, CLI before MCP, self-hosted CI, token discipline. |
| Settings | `.claude/settings.json` | Model, auto mode, hooks, plugins, skill on/off overrides. |
| Hooks | `.agents/jev/hooks/*.py` | Jev-backed guardrails. Each one fails open if Jev is unreachable. |
| Codex hooks | `.codex/hooks.json` | Runs the shared skill picker, rule enforcer, action gate, and done check. Codex requires a local `/hooks` trust review after restore. |
| Jev client | `.agents/jev/jev.py` ([`jev/`](../jev/)) | Stdlib client for the Jev evaluate endpoint (boolean, choice, score). |
| Skills | `.agents/skills/*`, `.claude/skills/*` | Linked into `~/.claude/skills`; Codex reads `.agents/skills` directly. CLI-wrapper skills live in `.agents/skills-disabled`, which neither agent loads. The skill picker only suggests skills the calling agent loads and Claude has not switched off. `grilling` and `wizard` are copies of [mattpocock/skills](https://github.com/mattpocock/skills) from 2026-10-17. `grilling` is manual-only in both agents (`disable-model-invocation` for Claude, `agents/openai.yaml` policy for Codex) and looks facts up with `rg` before using sub-agents. Re-apply both edits if you re-download it. |
| CLIs | `.local/bin/jev`, caveman | `jev` runs `.agents/jev/cli/{explore,triage}.py`. |
| Context meter | `.agents/context-meter/ctx.py` | Claude status line and Codex hook; shows context fill as a bar and sets the herdr pane title. |
| Plugins | `.claude/plugins/*.json`, `.agents/jev/fast-jev-compaction` | Context compaction and Swift/Kotlin LSP. |
| MCP | claude.ai account | COROS, Strava and Claude Docs. Managed in the claude.ai account, not in files. |

## Not in this repo

- `~/.agents/jev/.env` (gateway API key) and `~/.agents/jev/log/`.
- `~/.codex/config.toml` (machine-specific settings, MCP connections, and hook trust state) and Codex OAuth credentials.
- `~/.claude/projects/*/memory/` (personal memories), history, sessions, caches and `skills/synced/`.
- `node_modules` for fast-jev-compaction: run `npm install` in `.agents/jev/fast-jev-compaction` after restoring.
