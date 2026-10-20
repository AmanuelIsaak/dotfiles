#!/usr/bin/env python3
"""Context meter: how full the agent's context window is, as a bar.

  ctx.py claude   Claude Code statusLine command (JSON on stdin, prints one line).
  ctx.py codex    Codex hook (Stop/PostToolUse); reads the rollout's last token_count.

Both also set the herdr pane title when running inside herdr, so every agent pane
shows its fill level. Thresholds follow CLAUDE.md: compact or start fresh near 100k.
"""
import json
import os
import subprocess
import sys

WARN_TOKENS = int(os.environ.get("CTX_WARN_TOKENS", "60000"))
HIGH_TOKENS = int(os.environ.get("CTX_HIGH_TOKENS", "100000"))
CACHE = os.path.expanduser("~/.cache/ctx-meter")
COLORS = {"ok": "\033[32m", "warn": "\033[33m", "high": "\033[31m"}
RESET, DIM = "\033[0m", "\033[2m"


def level(tokens, pct):
    if tokens >= HIGH_TOKENS or pct >= 50:
        return "high"
    if tokens >= WARN_TOKENS or pct >= 35:
        return "warn"
    return "ok"


def bar(pct, width=10):
    filled = max(0, min(width, round(pct / 100 * width)))
    return "▰" * filled + "▱" * (width - filled)


def short(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:g}M"
    return f"{n / 1000:.0f}k" if n >= 1000 else str(n)


def plain(tokens, size, pct):
    # The bar fills toward the /compact budget, not the full window: on a 1M
    # window, 100k would otherwise look like an almost empty bar.
    budget = min(size, HIGH_TOKENS) if size else HIGH_TOKENS
    hint = " → /compact" if level(tokens, pct) == "high" else ""
    return (f"{bar(tokens / budget * 100)} {short(tokens)}/{short(budget)}"
            f" · {pct:.0f}% of {short(size)}{hint}")


def report_herdr(text):
    """Set the herdr pane title, only when it changed; never blocks the agent."""
    pane = os.environ.get("HERDR_PANE_ID")
    if os.environ.get("HERDR_ENV") != "1" or not pane:
        return
    marker = os.path.join(CACHE, pane.replace(":", "_"))
    try:
        with open(marker) as f:
            if f.read() == text:
                return
    except OSError:
        pass
    try:
        os.makedirs(CACHE, exist_ok=True)
        with open(marker, "w") as f:
            f.write(text)
        herdr = os.environ.get("HERDR_BIN_PATH") or "herdr"
        subprocess.Popen([herdr, "pane", "report-metadata", pane, "--source", "ctx:meter",
                          "--title", text], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def claude(event):
    cw = event.get("context_window") or {}
    size = cw.get("context_window_size") or 200000
    usage = cw.get("current_usage") or {}
    tokens = sum(usage.get(k) or 0 for k in
                 ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    pct = cw.get("used_percentage")
    if pct is None:
        pct = tokens / size * 100 if size else 0
    model = (event.get("model") or {}).get("display_name") or "claude"
    cwd = (event.get("workspace") or {}).get("current_dir") or event.get("cwd") or ""
    text = plain(tokens, size, pct)
    report_herdr(f"claude {text}")
    color = COLORS[level(tokens, pct)]
    print(f"{DIM}{model} · {os.path.basename(cwd)}{RESET}  {color}{text}{RESET}")


def last_token_count(path, chunk=262144):
    """Newest token_count event in a Codex rollout, reading only the file's tail."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - chunk))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if '"token_count"' not in line:
            continue
        try:
            info = json.loads(line)["payload"]["info"]
        except (ValueError, KeyError, TypeError):
            continue
        if info:
            return info
    return None


def codex(event):
    info = last_token_count(event.get("transcript_path") or "")
    if not info:
        return
    size = info.get("model_context_window") or 0
    tokens = (info.get("last_token_usage") or {}).get("input_tokens") or 0
    if not size:
        return
    report_herdr(f"codex {plain(tokens, size, tokens / size * 100)}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "claude"
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    if mode == "codex":
        codex(event)
    else:
        claude(event)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a status line or hook must never break the agent
        pass
    sys.exit(0)
