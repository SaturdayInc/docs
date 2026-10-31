#!/usr/bin/env python3
"""Execute the published response-display examples with isolated fixtures."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


DOCS = Path(__file__).resolve().parents[1]
PAGE = (DOCS / "guides/freemium-model.mdx").read_text()
CASES = [
    {"tier": "full", "carb_g_per_hr": 70, "sodium_mg_per_hr": 900, "fluid_ml_per_hr": 1000},
    {"tier": "full", "carb_range_g_per_hr": "60-80", "sodium_range_mg_per_hr": "800-1000", "fluid_range_ml_per_hr": "900-1100"},
    {"tier": "teaser", "carb_range_g_per_hr": "60-90", "sodium_range_mg_per_hr": "500-1000", "fluid_range_ml_per_hr": "500-1000", "subscription_cta": {"subscribe_url": "https://example.test/subscribe"}},
    {"tier": "full"},
]


def snippet(language):
    return re.search(rf"```{language}[^\n]*\n(.*?)```", PAGE, re.S).group(1)


for payload in CASES:
    shown = []
    namespace = {
        "response": SimpleNamespace(json=lambda: payload),
        "show_range": lambda value: shown.append(["range", value]),
        "show_exact": lambda value: shown.append(["exact", value]),
        "show_upgrade_cta": lambda value: shown.append(["upgrade", value]),
    }
    exec(compile(snippet("python"), "freemium-model.mdx", "exec"), namespace)
    if "carb_range_g_per_hr" in payload:
        expected = [["range", payload[key]] for key in ("carb_range_g_per_hr", "sodium_range_mg_per_hr", "fluid_range_ml_per_hr")]
    else:
        expected = [["exact", payload.get(key, 0)] for key in ("carb_g_per_hr", "sodium_mg_per_hr", "fluid_ml_per_hr")]
    if payload["tier"] == "teaser":
        expected.append(["upgrade", payload["subscription_cta"]["subscribe_url"]])
    assert shown == expected, (payload, shown, expected)

    runner = r'''
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const { code, payload, expected } = JSON.parse(readFileSync(0, 'utf8'));
const shown = [];
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const run = new AsyncFunction('response', 'showRange', 'showExact', 'showUpgradeCTA', code);
await run(
  { json: async () => payload },
  value => shown.push(['range', value]),
  value => shown.push(['exact', value]),
  value => shown.push(['upgrade', value]),
);
assert.deepEqual(shown, expected);
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", runner],
        input=json.dumps({"code": snippet("typescript"), "payload": payload, "expected": expected}),
        text=True,
        check=True,
    )

print("Response examples passed: Python and TypeScript, exact/full-range/teaser/omitted-zero responses; no HTTP calls.")

batch_page = (DOCS / "guides/batch-operations.mdx").read_text()
batch_python = re.findall(r"```python[^\n]*\n(.*?)```", batch_page, re.S)
batch_typescript = re.findall(r"```typescript[^\n]*\n(.*?)```", batch_page, re.S)
batch_cases = [
    ({"results": [{"carb_range_g_per_hr": "60-80"}, {"carb_g_per_hr": 70}], "errors": [{"index": 1, "code": "example_error", "message": "Try again"}]},
     ["scenario 0: 60-80g carbs/hr", "scenario 1 failed: example_error Try again", "scenario 2: 70g carbs/hr"]),
    ({"results": [], "errors": [{"index": i, "code": "example_error", "message": "Try again"} for i in range(3)]},
     [f"scenario {i} failed: example_error Try again" for i in range(3)]),
]

batch_runner = r'''
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const { code, payload, expected, kind } = JSON.parse(readFileSync(0, 'utf8'));
const shown = [];
let body;
const fetch = async (url, init) => {
  assert.equal(init.method, 'POST');
  body = JSON.parse(init.body);
  return { json: async () => payload };
};
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
await new AsyncFunction('fetch', 'console', 'process', code)(
  fetch, { log: value => shown.push(value) }, { env: { SATURDAY_API_KEY: 'mock' } },
);
assert.deepEqual(shown, expected);
if (kind === 'athletes') for (const athlete of body.athletes) {
  assert.equal(typeof athlete.settings.fitness_level, 'number');
  assert.ok(!('fitness_level' in athlete));
  assert.ok(!('primary_sport' in athlete));
}
'''

for index, cases in enumerate([batch_cases, [({"created": []}, [])]]):
    for payload, expected in cases:
        shown, requests = [], []

        def post(url, **kwargs):
            requests.append(kwargs["json"])
            return SimpleNamespace(json=lambda: payload)

        with patch.dict(sys.modules, {"requests": SimpleNamespace(post=post)}), patch.dict(os.environ, {"SATURDAY_API_KEY": "mock"}):
            exec(compile(batch_python[index], "batch-operations.mdx", "exec"), {"print": shown.append})
        assert shown == expected, (shown, expected)
        if index == 1:
            for athlete in requests[0]["athletes"]:
                assert isinstance(athlete["settings"]["fitness_level"], int)
                assert "fitness_level" not in athlete and "primary_sport" not in athlete
        subprocess.run(
            ["node", "--input-type=module", "-e", batch_runner],
            input=json.dumps({"code": batch_typescript[index], "payload": payload, "expected": expected, "kind": "athletes" if index else "calculate"}),
            text=True, check=True,
        )

print("Batch examples passed: Python and TypeScript, partial/all failures and nested athlete settings; no HTTP calls.")

profile_page = (DOCS / "guides/fueling-profile.mdx").read_text()
profile_python = re.search(r"```python[^\n]*\n(.*?)```", profile_page, re.S).group(1)
profile_typescript = re.search(r"```typescript[^\n]*\n(.*?)```", profile_page, re.S).group(1)
# The page's response examples are the fixtures, so the snippets run against what the page shows.
profile_payloads = [json.loads(m) for m in re.findall(r"```json\n(\{\n  \"object\": \"fueling_profile\".*?)```", profile_page, re.S)]
assert [p["sharing"] for p in profile_payloads] == ["on", "off", "not_linked"], [p["sharing"] for p in profile_payloads]

profile_runner = r'''
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const { code, payload, expected } = JSON.parse(readFileSync(0, 'utf8'));
const shown = [];
const fetch = async (url, init) => {
  assert.match(url, /\/v1\/athletes\/[^/]+\/fueling-profile$/);
  assert.equal(init.headers.Authorization, 'Bearer mock');
  return { ok: true, status: 200, json: async () => payload };
};
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
await new AsyncFunction('fetch', 'console', 'process', code)(
  fetch, { log: value => shown.push(value) }, { env: { SATURDAY_API_KEY: 'mock' } },
);
assert.deepEqual(shown, expected);
'''

for payload in profile_payloads:
    if payload["sharing"] == "on":
        expected_py = [f"{field}: {answer['value']} (calculations use {answer['calculations_use']})" for field, answer in payload["profile"].items()]
        expected_ts = [f"{field}: {json.dumps(answer['value'], separators=(',', ':'))} (calculations use {answer['calculations_use']})" for field, answer in payload["profile"].items()]
    else:
        expected_py = expected_ts = [f"{payload['sharing']}: {payload['message']}"]
    shown, urls = [], []

    def get(url, **kwargs):
        urls.append(url)
        assert kwargs["headers"]["Authorization"] == "Bearer mock"
        return SimpleNamespace(json=lambda: payload, raise_for_status=lambda: None)

    with patch.dict(sys.modules, {"requests": SimpleNamespace(get=get)}), patch.dict(os.environ, {"SATURDAY_API_KEY": "mock"}):
        exec(compile(profile_python, "fueling-profile.mdx", "exec"), {"print": shown.append})
    assert shown == expected_py, (shown, expected_py)
    assert urls[0].endswith("/fueling-profile"), urls
    subprocess.run(
        ["node", "--input-type=module", "-e", profile_runner],
        input=json.dumps({"code": profile_typescript, "payload": payload, "expected": expected_ts}),
        text=True, check=True,
    )

print("Fueling profile examples passed: Python and TypeScript, on/off/not_linked responses from the page; no HTTP calls.")
