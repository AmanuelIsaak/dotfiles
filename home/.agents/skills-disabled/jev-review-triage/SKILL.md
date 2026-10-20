---
name: jev-review-triage
description: Run FIRST whenever you are asked to review, check, or verify a code change or diff. Jev answers seven yes/no risk questions in about a second and tells you whether one quick review pass is enough (LIGHT) or the change needs the full review (FULL).
---

# jev-review-triage

```bash
python3 ~/.agents/skills/jev-review-triage/triage.py [git diff args]
```

With no arguments it reviews uncommitted changes against HEAD. Pass a range like `main...HEAD` for a branch.

- **LIGHT**: every risk question came back low. Do one focused pass over the diff for obvious bugs, then report.
- **FULL**: at least one risk was flagged, the diff is large, or Jev was unavailable. Do the normal thorough review, starting with the flagged areas it lists.

This triage never replaces the review. It only decides how deep to go, and a flagged risk always gets the full treatment.
