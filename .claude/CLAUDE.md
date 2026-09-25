# Saturday Docs — Claude Project Instructions

This is the Saturday documentation site, built with **Mintlify**.
Dev server: `mintlify dev` (or check `package.json` scripts).

A page naming endpoints, fields or webhook events: run `scripts/check-docs-drift.py` locally before merge (README, "Local checks"), against a fuel-backend worktree at `origin/main`, since the shared checkout is often on another branch. No PR check here can run it; fuel-backend's hourly Docs Drift catches it after merge.

<!-- MICHELLE-VISUAL-VERIFY-START -->
## Visual Verification Mandate

**NEVER claim a visual change looks good without a Playwright screenshot at the affected route.**

Before completing any visual work:

1. **Start the dev server** if it's not already running: `mintlify dev`
2. **Take a Playwright screenshot at mobile (375px width)** of the affected page(s)
3. **Take a Playwright screenshot at desktop (1440px width)** of the same page(s)
4. **Navigation or layout changes** require screenshots of **multiple pages**

Only after screenshots confirm the change looks right should you report completion.
<!-- MICHELLE-VISUAL-VERIFY-END -->
