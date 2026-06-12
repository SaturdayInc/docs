# Saturday API Docs

## Docs style contract (est. 2026-06-12)

1. **Every flow gets a narrative section** — written so an AI assistant can re-tell the user journey to its human (see `guides/athlete-onboarding-journey.mdx` for the canonical shape). Reference tables alone are not done.
2. **Verify against handlers before merging** — every field name, route, and enum in a guide must exist in fuel-backend (the organizations.mdx drift incident, fixed in #14, is why).
3. **llms-full.txt is NOT hand-maintained** — Mintlify auto-serves it from the MDX corpus. Never commit one (it shadows the generator). llms.txt stays a hand-curated index.
