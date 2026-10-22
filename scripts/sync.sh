#!/usr/bin/env bash
# Copy the live configuration from $HOME into home/, then refuse to finish if a
# secret-looking string slipped in. Review with `git status` / `git diff` before committing.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO/home"
SRC="$HOME"

copy() { # copy <path relative to $HOME> [rsync options...]
  local rel="$1"; shift
  if [ ! -e "$SRC/$rel" ] && [ ! -L "$SRC/$rel" ]; then
    echo "skip (missing): ~/$rel"; return
  fi
  mkdir -p "$DEST/$(dirname "$rel")"
  if [ -d "$SRC/$rel" ] && [ ! -L "$SRC/$rel" ]; then
    rsync -a --delete "$@" "$SRC/$rel/" "$DEST/$rel/"
  else
    rsync -a "$@" "$SRC/$rel" "$DEST/$rel"
  fi
}

COMMON=(--exclude .git --exclude .DS_Store --exclude __pycache__ --exclude node_modules --exclude '*.bak*' --exclude '*.log')

# Terminal and editor
copy .zshrc
copy .config/ghostty "${COMMON[@]}"
copy .config/herdr/config.toml
copy .config/atuin/config.toml
copy .config/bat/config
copy .config/git/ignore
copy .config/git/hooks "${COMMON[@]}"
copy .config/nvim "${COMMON[@]}" --exclude README.md

# Claude Code
copy .claude/CLAUDE.md
copy .claude/settings.json
copy .claude/hooks "${COMMON[@]}"
copy .claude/plugins/installed_plugins.json
copy .claude/plugins/known_marketplaces.json
copy .claude/skills "${COMMON[@]}" --exclude synced --exclude app-store-screenshots  # large; reinstall from .skill-lock.json

# Codex (config.toml stays local: machine paths, MCP connections, hook trust state)
copy .codex/hooks.json
copy .codex/AGENTS.md

# Shared skills (Jev has its own private repo; ~/.agents/jev links to ~/repos/jev)
copy .agents/AGENTS.md
copy .agents/.skill-lock.json
copy .agents/skills "${COMMON[@]}"
copy .agents/context-meter "${COMMON[@]}"

# Homebrew packages, minus the private ones listed in ~/.Brewfile (and their description comments).
touch "$HOME/.Brewfile"
brew bundle dump --file=- --force | awk 'NR==FNR { skip[$0]=1; next } /^#/ { c=$0; next } !skip[$0] { if (c) print c; print } { c="" }' "$HOME/.Brewfile" - > "$REPO/Brewfile"

# Secret scan over home/.
PATTERNS='(sk-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|vck_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.|(API_KEY|TOKEN|SECRET|PASSWORD|_ID)=[^[:space:]$"'"'"'{}<]{8,})'
if hits=$(grep -rIlE --exclude-dir=node_modules --exclude-dir=log --exclude=.env "$PATTERNS" "$DEST" 2>/dev/null); then
  echo "Possible secrets found; fix before committing:" >&2
  echo "$hits" | sed "s|$REPO/||" >&2
  exit 1
fi
if find "$DEST" -name .env -print -quit | grep -q .; then
  echo "A .env file was copied; remove it before committing." >&2
  exit 1
fi

echo "Synced into home/. Review with: git -C \"$REPO\" status"
