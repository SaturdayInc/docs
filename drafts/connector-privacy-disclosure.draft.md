# DRAFT — Alex legal review required

> **This is a DRAFT data-handling / privacy disclosure for the Saturday Claude connector and Coach API.**
> It was authored by Claude as a starting point for the Anthropic MCP directory submission and the connector's
> privacy disclosure. **It has NOT been reviewed by a lawyer and is NOT legally final.** Do not publish it to any
> live marketing site, app-store listing, or the Anthropic directory until Alex (and counsel, as appropriate) has
> reviewed and approved it. It deliberately lives under `docs/drafts/` (a `.mintignore`'d path) so it is NOT built
> into the live docs site.
>
> **Canonical home:** the public-facing version of this disclosure has been authored as a sweb LegalDoc page at
> `saturday.fit/legal/connector-privacy` (a DRAFT sweb PR, not merged). That sweb page — not this markdown — is the
> privacy URL for the Anthropic directory submission. This file is kept as the dev-facing source/working copy.
>
> Scope note: this describes the data behavior of the **shipped code** as of June 2026 (the consumer connector +
> coach API/MCP). Where a statement depends on a policy decision rather than code (e.g. retention windows for
> connector-accessed data, sub-processor lists), it is marked **[POLICY — confirm]**.

---

## Saturday Connector — Data Handling Disclosure

The Saturday connector lets a person connect their Saturday account to Claude (or another MCP client) so an AI
assistant can read their endurance-nutrition data and, for coaches, configure their own monitoring. This document
explains what data the connector accesses, how it is used, how long it is kept, and how a user disconnects.

### 1. Who connects, and what they connect

There is **one** Saturday connector. The data it can touch depends on who signs in:

| Principal | Who | What the connector can reach |
|-----------|-----|------------------------------|
| **Athlete** (consumer) | Any active Saturday subscriber | **Their own** Saturday data only — their profile and their activities/sessions under `users/{their-uid}`. |
| **Coach** (Business tier or higher) | A subscriber who also holds an API-eligible coach tier | Everything an athlete can reach for themselves, **plus** read access to the fueling data of athletes **on their own roster**, and write access to **their own** alerting/report configuration. |

A coach is also an athlete; the same sign-in serves both facets. An athlete-only subscriber can never reach any
coach data or another person's data.

### 2. What data the connector accesses

**For an athlete connecting their own account:**

- **Profile** (`users/{uid}`): the athlete's Saturday profile fields used to personalize fueling — e.g. body
  metrics, fueling preferences, account email, and settings the app already stores.
- **Activities & sessions** (`users/{uid}/activities`): planned and completed activities, the fuel/hydration/
  electrolyte **prescriptions** Saturday's engine produced, post-session adherence and feedback (what was actually
  consumed, symptoms, ratings), and associated context (e.g. weather, sleep) the app already records.
- **Derived nutrition outputs**: prescriptions and product-fit analysis computed by Saturday's engine on demand.

The connector can **write** a limited, athlete-owned subset: an athlete may create/update **their own** activities
and product choices. The connector can **never** write a prescription by hand — prescriptions come only from
Saturday's calculator engine. It cannot delete the athlete's account or write to another user.

**For a coach connecting (additional, roster-scoped):**

- **Roster** (via `coach_relationships` / organization membership): the list of athletes the coach is actively
  linked to, and per-athlete "needs-attention" markers derived from the one shared concern definition.
- **Per-athlete fueling reads**: for **athletes on the coach's roster only**, the same fueling rollup, AI report
  (narrative + structured), and per-session detail the coach already sees in the Saturday coach portal. Responses
  use **full athlete identity** (names and data as the coach sees them in the portal) — the coach owns the coaching
  relationship; there is no separate de-identification layer in the connector/API.
- **The coach's own configuration** (read & write): alert rules, AI-report settings, concern thresholds, groups,
  quiet hours, and webhook endpoints — scoped to the coach (overall / group / per-athlete). A coach can configure
  only their **own** monitoring; the coach can **never** author or alter an athlete's fueling data, debriefs, or
  prescriptions through the connector or API.

### 3. Scope-by-scope data access

The connector requests OAuth scopes; each maps to a specific, minimal data surface. A user sees the requested
scopes on the consent screen before granting.

| Scope | Data access granted |
|-------|---------------------|
| `athlete:read` | Read the signed-in athlete's own profile/settings. |
| `athlete:write` | Update the signed-in athlete's own profile/settings. |
| `activity:read` | Read the signed-in athlete's own activities and prescriptions. |
| `activity:write` | Create/update the signed-in athlete's own activities (never prescriptions). |
| `nutrition:read` | Compute nutrition prescriptions for the signed-in athlete. |
| `coach:roster` | (Coach) Read the coach's roster and per-athlete needs-attention markers. |
| `coach:reports` | (Coach) Read roster athletes' fueling rollups, AI reports, and the roster digest. |
| `coach:alerts` | (Coach) Create/update the coach's **own** alert rules and report settings. |
| `coach:webhooks` | (Coach) Register/manage the coach's **own** concern webhooks. |

The connector requests only the scopes its tools need; a user grants (or denies) them at consent time. When a
coach is granting `coach:*` scopes, the consent screen additionally discloses that Claude will be able to read the
coach's athletes' fueling data and manage the coach's alert settings.

### 4. How the data is used

- **Solely to power the connected assistant's tools** at the user's request — answering the user's questions about
  their (or their roster's) fueling, computing prescriptions on demand, and writing the user's own activities/
  configuration when the user asks.
- Saturday does **not** use connector-accessed data to train or fine-tune machine-learning or AI models, build
  competing algorithms, or sell/redistribute it. This is enforced contractually via the data license below and is
  the same prohibition that governs the partner API.
- Data flows only between the user's MCP client (e.g. Claude), Saturday's API, and Saturday's existing data store —
  the connector does not introduce a new third-party data path. **[POLICY — confirm the sub-processor list
  (e.g. Google Cloud / Firestore, Brevo for transactional email, the LLM provider used for report generation) and
  whether it must be enumerated here for the directory submission.]**

### 5. The `X-Saturday-Data-License` terms (no-train / no-reverse-engineer)

Every Saturday API response carries data-license headers that bind how response data may be used:

| Header | Value | Meaning |
|--------|-------|---------|
| `X-Saturday-Data-License` | `display-only` | Data may be displayed to the end user and cached for UX — not repurposed. |
| `X-Saturday-Data-Training` | `prohibited` | Using response data to train or fine-tune ML/AI models is prohibited. |
| `X-Saturday-Data-Attribution` | `required` / `optional` | Whether "Powered by Saturday" attribution is required (teaser tier) or optional (full tier). |

Prohibited uses (binding on any connector/API consumer): training or fine-tuning models on response data; building
a competing nutrition-prescription algorithm; reverse-engineering Saturday's calculation algorithms; aggregating
response data across athletes for resale or statistical products; redistributing response data to third parties;
or creating derivative databases from the product catalog. Saturday's prescriptions, product database, AI report
voice, and knowledge base are proprietary intellectual property.

### 6. Retention

- **Connector-accessed data is read live from the user's existing Saturday account** — the connector does not
  create a separate long-lived copy of athlete data. Saturday's own retention of the underlying account data is
  governed by Saturday's existing privacy policy and the API data policy (account data retained while the account
  is active, plus a 30-day grace period after deletion).
- **OAuth credentials**: access tokens are short-lived (1 hour); refresh tokens last up to 90 days and rotate on
  every use. A lapsed subscriber loses connector access within ~1 hour (the next refresh is denied).
- **AI reports** generated on demand may be cached briefly to avoid regenerating an unchanged report; a newer
  session or an explicit `refresh` regenerates them. **[POLICY — confirm the report-cache retention window to state
  a specific number here.]**
- **Webhook delivery**: a coach's registered webhook endpoint + its (hashed) signing secret persist until the coach
  deletes the endpoint; delivery attempts retry with backoff and auto-disable after repeated failures.
- A connected MCP client (e.g. Claude) may retain tool results within the user's own conversation per **that
  client's** retention policy — that retention is governed by the client, not by Saturday.

### 7. Deletion & disconnect

- **Disconnect the connector**: a user can revoke the connection at any time from their Saturday account settings,
  or programmatically (`POST /v1/oauth/token/revoke`). Revocation immediately invalidates the refresh token; access
  ends within ~1 hour as the access token expires. Disconnecting does not delete any of the user's underlying
  Saturday data — it only ends Claude's access to it.
- **Delete account data**: account/athlete data deletion follows Saturday's existing privacy controls and the API's
  GDPR endpoints (data export and right-to-erasure with cascading deletion), subject to the 30-day grace period.
- **Coach webhooks**: a coach can delete or disable any registered webhook endpoint, immediately stopping
  deliveries.
- **Roster changes**: if an athlete leaves a coach's roster (relationship no longer active), they are immediately
  excluded from all of that coach's roster reads, digests, and webhook scope.

### 8. Safety posture

Nutrition prescriptions surfaced through the connector are **guidance, not medical instructions**, and every
response carries safety metadata that must be presented to the user, not stripped. The connector cannot autonomously
act on prescriptions (e.g. ordering products); it surfaces guidance for human consideration.

---

### Open items for Alex / counsel before submission

1. **[POLICY]** Confirm the sub-processor list to disclose (cloud/data store, transactional email, LLM provider) and
   whether the directory submission requires it.
2. **[POLICY]** Confirm specific retention windows for (a) on-demand AI report cache and (b) any connector
   audit/usage logs, so the vague phrasing above can be replaced with numbers.
3. **[LEGAL]** Confirm whether this disclosure should reference or be folded into Saturday's existing public privacy
   policy URL, and whether a connector-specific privacy URL is required by the Anthropic directory form.
4. **[LEGAL]** Confirm the "full identity, no de-identification" coach-data posture is acceptable as worded for a
   public-facing disclosure (it is accurate to the code and to the product decision API-10).
5. **[POLICY]** Decide whether to publish an approved version of this as a public page (e.g. a `connector-privacy`
   docs page or a section of the marketing-site privacy page) — currently intentionally unpublished.
