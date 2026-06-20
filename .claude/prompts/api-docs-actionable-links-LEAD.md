# LEAD PROMPT — Make the Saturday API docs actionable (link injection)

> Self-contained launch prompt for a fresh Claude to **lead a small team** doing for the
> **API Guides** docs what was just done for the **Coaching** docs. You have no memory of
> the prior session — everything you need is below. Work in `~/code/s/docs` (Mintlify/MDX).

## Company purpose (load this — purpose-aware work is far better)

Saturday is a sports-nutrition app. Two doc audiences live in `docs.saturday.fit`:
- **Coaches** (the "Coaching" tab) — use the web coach portal at `https://coach.saturday.fit`.
- **Developers/partners** (the "API Guides" tab) — build integrations against `https://api.saturday.fit`.

Alex (cofounder, solo dev) wants the docs to stop being passive reading and become an
**actionable control surface**: wherever the prose tells a reader to *go do a thing in a UI*,
the words that name that place should be a **clickable link** straight to it. The Coaching
tab is already done. Your job is the **API Guides** tab — applied with judgment (see scoping).

## What was just shipped on the coaching side (the pattern you follow)

1. **Every coaching doc section that describes a coach action now bold-links** to the exact
   coach-portal location, absolute URL, e.g. `from your **[roster](https://coach.saturday.fit/dashboard)**`.
   Markdown form is always `**[text](url)**` (bold wrapping the link). ~123 portal links added.
2. **A reusable device-aware component already exists** at `/snippets/app-action.jsx`:
   `import { AppAction } from "/snippets/app-action.jsx"` then `<AppAction path="/open-app">label</AppAction>`.
   On a phone it deep-links into the Saturday mobile app via a universal link; on desktop it
   pops a scannable QR to the same deep link. **Reuse it** for any "do this in the mobile app"
   step. `path` MUST be a universal-link-claimed path — known-good set: **`/open-app` (safe
   generic default), `/manage`, `/coaching-mode`, `/offer`, `/redeem`, `/pair`, `/subscribe`,
   `/invite`, `/transfer`**. Do NOT use `/settings` or other unclaimed paths (they open a dead
   web page, not the app). When unsure, use `/open-app`.
3. **Auth carry-through is already shipped** (coach-portal `?redirect=`): a logged-out reader
   who clicks a `coach.saturday.fit/...` link is bounced to sign-in/anon-entry and then routed
   to their intended destination. So you just emit the correct absolute URLs — the login
   round-trip is handled.

## THE KEY DIFFERENCE FOR THE API SIDE — scope with judgment

The coaching docs are **task/navigation** docs (almost every section is "go do X" → link).
The API docs are mostly **reference + code** (endpoint signatures, request/response schemas,
enums, code samples). **A reference section has no "place to go" — do NOT force a link into
it.** Linking the response-shape of `POST /v1/athletes` to a portal page would be noise.

Apply the "section gets an action link" rule **only where a section actually instructs the
reader to act in a UI/console/portal/external app.** Those spots are real but **sparse and
concentrated**. From a scan, the genuine action-link surface on the API side is:

| Where it appears | Anchor text | Link target |
|---|---|---|
| `authentication.mdx`, `guides/coach-api.mdx` | "Settings → API Keys" / "API Keys" (coach `cp_` keys) | `https://coach.saturday.fit/admin/api-keys` |
| `access.mdx`, `authentication.mdx`, `guides/coach-api.mdx` | "coach portal" | `https://coach.saturday.fit` (or the specific `/admin/*` surface in context) |
| coach webhooks (in `coach-api`/`coach-connector`) | "webhooks" | `https://coach.saturday.fit/admin/webhooks` |
| `quickstart.mdx`, `access.mdx` | "Get your API key" / self-serve signup | `https://saturday.fit/api` (already linked — verify it's there) |
| partner keys | "contact api@saturday.fit" | `mailto:api@saturday.fit` (already linked — verify) |
| `guides/coach-connector.mdx`, `guides/mcp-integration.mdx` | "add a custom connector" in Claude | `https://claude.ai` connectors (external — link if natural) |

OAuth2 app registration is **email-based** (no self-serve console) — there is no portal deep
link to add there; leave it. Most of `guides/*` (nutrition-calculation, athletes, activities,
batch-operations, webhooks-the-partner-API, error-handling, rate-limiting, safety, data-policy,
freemium-model, feature-gates, deployment) is pure reference — expect **few or zero** action
links there, and that's correct. **Do not invent links to hit a quota.**

## The full API-Guides corpus (the `docs.json` "API Guides" tab — 24 pages)

```
introduction.mdx  access.mdx  quickstart.mdx  authentication.mdx  error-handling.mdx  rate-limiting.mdx
guides/nutrition-calculation.mdx  guides/athletes.mdx  guides/activities.mdx  guides/freemium-model.mdx
guides/onboarding.mdx  guides/athlete-onboarding-journey.mdx  guides/safety.mdx
guides/ai-coach.mdx  guides/webhooks.mdx  guides/oauth2.mdx  guides/organizations.mdx
guides/batch-operations.mdx  guides/mcp-integration.mdx
guides/coach-api.mdx  guides/coach-connector.mdx
guides/feature-gates.mdx  guides/data-policy.mdx  guides/deployment.mdx
```

## Methodology (per file)

1. Read the file. Decide: is this **reference/code** or does it contain **UI/portal/console
   action steps**? If pure reference, likely no edits — note that and move on.
2. For each genuine action step, bold-link the naming words to the target (table above).
   Absolute `https://coach.saturday.fit/...`; `**[text](url)**` form. Reuse `<AppAction>` for
   "do this in the mobile app" steps (add the import once per file that uses it).
3. **Remove bragadocious / useless commentary** (self-congratulatory or filler that doesn't
   help the reader act). Keep substantive product/technical info.
4. **Keep all existing cross-links** (`/guides/...`, `/coaching/...`, external). You're ADDING
   action links, not replacing reference links.
5. Don't touch frontmatter, headings, code samples, or schema meaning. No meta-commentary.
   Don't over-link. Verify every portal URL resolves to a real Next.js route under
   `~/code/s/coach-portal/frontend-next/app` (e.g. `/admin/api-keys` → `app/admin/api-keys/page.tsx`).

## Team shape (your call — the surface is thin)

This corpus is reference-heavy, so the action-link surface is a fraction of the coaching one.
A small team fits: e.g. **2–3 parallel agents** partitioned by group (Getting-Started+Platform /
Core-Guides / Integration+Coach-API), each applying the methodology, plus **one adversarial
verifier** that re-reads every edit and confirms (a) no reference section was force-linked,
(b) every added portal URL resolves to a real route, (c) bragadocious lines are gone, (d) meaning
preserved, (e) `<AppAction>` paths are in the claimed set. Scale down to solo if you prefer —
the volume is modest. (The coaching pass used a Workflow: component → 5-family edit→verify
pipeline → broken-link sweep. Mirror as much as is warranted.)

## Heads-up: a pre-existing broken page

`guides/athlete-onboarding-journey.mdx:49` contains a literal `{your platform}` that MDX parses
as a JS expression → the page currently **404s in production** (broken since 2026-06-12). If you
touch that file, fix it (escape the braces `\{your platform\}`, or backtick/code the placeholder,
or rephrase) and verify with `npx mint broken-links`. If you leave it, know that the Mintlify CLI
will abort its link sweep on it — fall back to a manual static resolution of links like the
coaching pass did.

## Deliverable

- Branch off `origin/main` (e.g. `docs-api-links`), edit in place, open a PR in `SaturdayInc/docs`
  titled like the coaching one. Mintlify auto-deploys on merge to `main`.
- Report: per-file what was linked (and which files were correctly left as pure reference),
  total action links added, any broken-link findings, and the verifier verdict.
- Surface any incidental issues LOUDLY in chat before the PR body (Alex's rule), don't bury them.

## Acceptance criteria

- Every genuine UI/portal/console action step is bold-linked to a resolving target.
- Reference/code/schema sections are NOT force-linked.
- All portal URLs absolute (`https://coach.saturday.fit`), resolve to real routes.
- `<AppAction>` (if used) imported + uses a claimed path.
- Bragadocious commentary removed; meaning, code, and schemas untouched.
- Existing cross-links preserved.
