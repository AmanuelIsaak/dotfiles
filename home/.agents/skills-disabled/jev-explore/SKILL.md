---
name: jev-explore
description: Fast file finder. Use INSTEAD of spawning an Explore/search subagent when you need to locate which files implement, define, or handle something in the current repo. Keyword search plus Jev relevance ranking returns the top files in seconds, so you open only those.
---

# jev-explore

Run:

```bash
python3 ~/.agents/skills/jev-explore/explore.py "<the question, in plain words>" [--dir <repo path>] [--top 5] [--terms a,b,c]
```

- It extracts search terms from the question, finds candidate files with ripgrep, and has Jev score every candidate (20 per request, in parallel). It prints the top files with their best matching lines.
- Open only the top 1–3 files. If none of them is right, rerun with `--terms` set to likely identifiers (function, class, or route names) rather than opening more files.
- If it prints "Jev unavailable", the ranking is by keyword hits only; trust it less.
- For broad questions ("how does the whole app work"), use `rg` or a normal exploration instead. This skill is for "where is X".
