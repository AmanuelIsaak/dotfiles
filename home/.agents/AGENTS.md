# Personal defaults
- Keep each user-facing reply at most 2,000 characters. Put longer artifacts in files and link them.
- Prefer an installed CLI over MCP when both can do the task. Use MCP when no equivalent CLI works.
- Keep tool output focused; preserve errors and evidence needed to verify results.
- Use caveman lite for user-facing replies: plain, short sentences with normal grammar. Keep every decision, risk and result clear.
- For proposals, lead with the recommended action and why in 2-4 sentences. Include only decisions I need to review now. Put detailed plans in a file and link it when needed; expand on request.

# Writing (replies and docs; not commit messages)
Adapted from Pstack's unslop skill.
- Say what it does, not how it feels: name the mechanism, number or command. Cut sentences that could appear unchanged in any project's docs.
- Plain words: "use" not "leverage/utilize", "is/has" not "serves as/boasts". No delve, crucial, pivotal, robust, seamless, landscape, testament, underscore.
- No em dashes; use periods or commas. No colons as mid-sentence connectors.
- No chatbot phrases ("I hope this helps", "Great question", "Let me know if…"), no generic conclusions, no stacked hedges.
- Active voice, one idea per sentence. Don't force groups of three; don't cycle synonyms for one thing.
- Bold sparingly; no bold-label-colon lines that repeat themselves; sentence-case headings; no decorative emoji.

# App playbook (rules for every app)
- `~/repos/template/app-playbook` holds the stack rules, assets and code examples for all my apps: web (Solid, SvelteKit, Astro; React only for React-only libraries), native mobile (Kotlin Multiplatform with Compose and SwiftUI), and new app types. Start at its `SKILL.md`.
- New app or stack decision: read `SKILL.md`, then `core/` and the matching `stacks/` module, and create the app with that module's commands (copy the assets, write the examples, replace placeholders). Don't hand-roll a stack the playbook covers.
- A generic fix or rule found in an app goes into the playbook module too. There is no sync, so apply it by hand in other apps that need it.
- Keep app-specific code and docs out of the playbook. Skip apps whose stack doesn't fit (e.g. MatchLens: pnpm + Python + Docker).

# Code search
- Search code with `rg` (ripgrep): `rg -n <pattern>`, `rg -l` for file lists, scope with `-t`/`-g`, cap output with `head`.
- Keep searches small at any repo size: `rg -l` first to list files, narrow with `-t`/`-g`, cap with `-m N` or `| head`, prefer exact patterns (`class Foo`) over broad words; then read only the matched regions.
- Never install or use graphify (or other code-graph tools); it was benchmarked and removed (Oct 2026): slower, noisier and less complete than rg.

# CI / hosting cost
- Zero budget: never add paid services or GitHub-hosted runner minutes. My repos are private by default (dotfiles is public), so hosted minutes (macOS ×10) burn the free quota.
- GitHub Actions jobs run on my Mac (Apple silicon) via a self-hosted runner: `runs-on: [self-hosted, macOS, ARM64]`. No `sudo`, no `xcode-select -s`, no KVM/disk-cleanup steps; reuse local Xcode, Android SDK and the existing AVD.
- Keep CI lean: `pull_request` only (no duplicate push-to-main run), `paths-ignore` docs, `concurrency` cancel-in-progress.
- Web hosting: Cloudflare Pages, built on the self-hosted runner and uploaded with `wrangler pages deploy` (secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`). No Vercel or other cloud builds; `app-playbook/assets/web/common/.github/workflows/deploy.yml` is the reference.
- When interacting with Cloudflare, use the cf CLI unless the project has a Wrangler configuration file (then `wrangler`). Never install or use a Cloudflare MCP server or plugin.
- A new repo with workflows needs its own runner: `~/actions-runners/<repo>`, registered via `gh api -X POST repos/<owner>/<repo>/actions/runners/registration-token`, installed as a launchd service (`./svc.sh install && ./svc.sh start`).

# Token discipline
- Pipe noisy commands (gradle, xcodebuild, npm, test runs) through `tail -n 40` or `grep -E 'error|FAIL|warning'`; rerun wider only if needed.
- Read files with offset/limit when you know the region; never re-read a file you just wrote or edited.
- Locate code with `rg` or `jev explore` before opening files; don't spawn Explore subagents for "where is X".
- Before reviewing a diff, run `jev triage [range]`: LIGHT → one focused pass, FULL → thorough review of flagged areas.
- Batch independent tool calls in one message; don't narrate plans you won't act on.
- Keep sessions short: one task per session. When context passes ~100k tokens or a task is done, suggest `/compact` or a fresh session (`/clear` in Claude, `/new` in Codex) with a short handoff note.
