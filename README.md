# dotfiles

My macOS terminal and AI coding setup: one place for the configs that make Ghostty, Neovim, Claude Code and Codex behave the way I want.

**Stack:** Ghostty · Zsh (no framework, autosuggestions, atuin) · herdr · LazyVim (Harpoon 2) · bat · Claude Code · Codex · Jev hooks · Tokyo Night (follows light/dark)

## What's in here

### Terminal and editor

| Path | What it does |
|---|---|
| `.zshrc` | Shell startup, aliases (`ls` → eza, `cat` → bat), fzf, zoxide, dev paths |
| `.config/ghostty` | Font size and Tokyo Night colors that follow the system theme |
| `.config/atuin` | Ctrl-R history search: compact view, Enter runs the command |
| `.config/herdr` | Workspace keys and colors for herdr, the terminal workspace the agents run in |
| `.config/bat` | Syntax colors that match the terminal |
| `.config/nvim` | LazyVim with Harpoon 2, Kotlin and Swift LSP, and format on save |

**Neovim format on save** (`lua/plugins/formatting.lua`):

| Language | Formatter |
|---|---|
| Python | ruff (also sorts imports) |
| JS · TS · React · Svelte | prettier, using the project's copy so Svelte gets its plugin |
| Swift | swiftformat |
| Kotlin | ktlint |
| Go | goimports + gofumpt |
| Rust | rustfmt |
| Lua | stylua |

`<leader>uf` turns it off for the current file and `<leader>uF` everywhere. Building and debugging happen in each project's scripts, Android Studio and Xcode, so there's no debugger setup.

### AI agents

Claude Code and Codex share one set of instructions, skills and guardrails.

| Path | What it does |
|---|---|
| `.agents/AGENTS.md` | Shared rules for Claude and Codex: short replies, plain writing (from Pstack's unslop), CLI over MCP, zero-cost self-hosted CI, token discipline, short sessions |
| `.claude/CLAUDE.md` | Imports `AGENTS.md` with `@~/.agents/AGENTS.md`, then Claude-only rules |
| `.codex/AGENTS.md` | Symlink to `.agents/AGENTS.md` |
| `.claude/settings.json` | Model, auto mode, hooks, plugins, status line, skill on/off |
| `.codex/hooks.json` | The same Jev hooks plus the context meter for Codex |
| `.agents/skills` | Skills both agents load (coding-style skills, youtube-summary, grilling and wizard from [mattpocock/skills](https://github.com/mattpocock/skills)…) |
| `.agents/skills-disabled` | Skills that only wrapped a CLI; neither agent loads them |
| `.agents/context-meter` | Context-window bar for both agents and herdr pane titles |

**Jev hooks** (in [`jev/`](jev/); each one lets everything through if Jev is unreachable):

- `skill_picker`: suggests the one skill that fits the prompt, only from skills that agent actually loads.
- `rule_enforcer`: checks edits against a repo's `.jev-rules.md`, for example no secrets and no edits to existing migrations.
- `action_gate`: vets shell and MCP commands for destructive or risky actions.
- `done_check`: blocks the agent from claiming it's done when it isn't.

**Context meter:** shows how full the context is, e.g. `▰▰▰▰▰▰▰▰▱▱ 76k/100k · 8% of 1M`. It turns yellow at 60k and red with a `→ /compact` hint at 100k. Change the limits with `CTX_WARN_TOKENS` and `CTX_HIGH_TOKENS`.

Codex CLI uses its built-in footer instead of a custom status-line command. Set `tui.status_line = ["model-with-reasoning", "used-tokens", "context-window-size", "context-used", "git-branch", "five-hour-limit"]` in the local `~/.codex/config.toml` to keep the token count, window size and percentage visible. The bar and threshold hint appear in herdr pane titles through the Codex hooks; Codex's own footer cannot render them.

The full picture is in **[docs/ai-architecture.md](docs/ai-architecture.md)**: a diagram of how the prompt, hooks, skills, CLIs, plugins, MCP connectors and CI fit together.

## Working habits

- One task per session. `/clear` (Codex: `/new`) when it's done.
- Before building something new, run `/grilling` (Codex: `$grilling`). It asks the open decisions in numbered rounds, each with a recommended answer. Run `/wizard` when a setup step needs a human, like dashboard tokens or GitHub secrets.
- Read a third-party skill's markdown before installing it, and copy only the skills that fit.
- When the meter turns red and the task isn't finished, `/compact keep <what matters>` at a natural pause, then continue.
- Run `jev triage` before reviewing a diff, and `jev explore` to find code.
- CI runs only on pull requests, on the self-hosted Mac runner. No paid services.

## Restore on a new Mac

1. **Install the tools:** Ghostty, Neovim, herdr, Claude Code, Codex, and from Homebrew `bat btop eza fd fzf ripgrep zoxide python@3.13`, plus the Android and Java tools the shell config uses. Install the Kotlin LSP from `jetbrains/utils/kotlin-lsp`; Swift uses Xcode's `sourcekit-lsp`.
2. **Check machine-specific values in `home/`:** the paths in `.zshrc` and `.codex/hooks.json`, Put IDs such as `CLOUDFLARE_ACCOUNT_ID` and `BUDGETLI_TEAM_ID` (an Apple development team) in `~/.zshrc.local`. `.zshrc` sources it, and sync never copies it.
3. **Copy the files**, after backing up what's there:

   ```sh
   rsync -av home/ "$HOME/"
   nvim --headless '+Lazy! sync' '+qa'
   ```

4. **Add the secrets and dependencies:**
   - Link Jev: `ln -s "$PWD/jev" ~/.agents/jev`, then follow [`jev/README.md`](jev/README.md) (key in `.env`, `npm install`, `install.sh`).
5. **Trust the Codex hooks** with `/hooks` in Codex, and reinstall herdr's Codex integration.

## Keeping it up to date

This repo is a snapshot, not symlinks, so it doesn't update itself. After changing a config:

```sh
scripts/sync.sh      # copy live config into home/, drop removed files, scan for secrets
git status           # review, then commit
```

`sync.sh` stops if anything looks like a secret.

## Never in this repo

- API keys (`~/.agents/jev/.env`), Codex credentials and `~/.codex/config.toml`
- Claude memories, history, sessions, caches and logs
- herdr's program and app data

## License

MIT, see `LICENSE`. Subfolders with their own license (such as `jev/fast-jev-compaction`) keep it.
