# browser-fetch-mcp: Chrome Profile Detection + Persistent Default — Design

## Goal

Move Chrome-profile detection out of `extract-url-mcp` and into `browser-fetch-mcp` as reusable MCP tools, and add a persisted default Chrome profile so the user picks one once (on first use) instead of being asked every time. `fetch_article` resolves that default automatically wherever it would otherwise have needed an explicitly-passed `chrome_profile` — the existing per-site policy for *whether* a profile is used at all does not change.

## Background

Today, `chrome_profile` detection is duplicated: `browser-fetch-mcp/browser_fetch_mcp/cookies.py`'s `extract_cookies()` decrypts real cookie values for one given profile (used for actual fetch injection), while `extract-url-mcp/scripts/detect_xcom_chrome_profile.py` independently re-implements "locate a Chrome profile dir, copy its `Cookies` sqlite file past the file lock, query it" — but only checks cookie-name *existence* (no decryption) across *all* profiles, to recommend one, hardcoded to x.com/twitter.com's auth cookie names.

`extract-url-mcp`'s `SKILL.md` currently only triggers this detect-and-confirm flow when the URL's hostname is x.com/twitter.com, and re-runs detection + re-asks the user on every such URL — there is no persistence.

## Non-goals

- No change to the "detect-then-confirm, never auto-use" constraint: a profile is only ever used automatically after the user has explicitly confirmed and stored it once. Detection alone never causes a profile to be used.
- No change to which sites need a profile at all. x.com remains the only site where a profile is mandatory; generic/wechat/arxiv remain opportunistic (thin-content retry only).
- No per-site *different* default profiles (e.g. "profile A for x.com, profile B for site Y") — one global default, matching the original `extract-url` skill's single `CHROME_PROFILE` value.
- `extract-url` (the original, real skill) is untouched, per this project's standing "build-only, no consumer migration" convention.

## Architecture

### New MCP tools (`browser-fetch-mcp`)

- **`list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> list[dict]`**
  Generalizes `detect_xcom_chrome_profile.py`'s logic into the MCP server: scans Chrome profiles under the Chrome user-data base dir (env-overridable for tests, mirroring today's `EXTRACT_URL_MCP_CHROME_BASE` pattern), reads each profile's `Preferences` for the account email, copies each profile's `Cookies` sqlite file to a temp path (dodging Chrome's file lock) and queries `SELECT DISTINCT name FROM cookies WHERE host_key IN (...)` using the caller-supplied `host_keys`. Returns, per profile: `profile_path`, `account_email`, `matched_cookie_names`, `looks_logged_in` (whether all of `cookie_names` were matched). Existence-only — never decrypts values, consistent with today's script.
  `extract-url-mcp` will call this with `host_keys=[".x.com", ".twitter.com"]`, `cookie_names=["auth_token", "ct0", "twid"]` — same values as today, just parameterized instead of hardcoded, so a future consumer needing a different site's login check can reuse the same tool.

- **`get_default_chrome_profile() -> {"profile_path": str | None}`**

- **`set_default_chrome_profile(profile_path: str) -> {"ok": true}`**
  Validates `profile_path` exists and is a directory before writing.

### Persistence

Config lives at `<data-dir>/config.json` where `<data-dir>` is the same directory `_data_dir()` already resolves (respecting `BROWSER_FETCH_MCP_DATA_DIR` for test isolation) — placed alongside the per-profile context subdirectories rather than introducing a second env var or a "parent of contexts" path, since the existing override already points tests at an isolated temp dir. Format: `{"default_chrome_profile": "<path>"}`.

### `fetch_article` resolution — single point, existing policy unchanged

At the top of `fetch_article`, resolve once:

```python
effective_chrome_profile = chrome_profile or get_default_chrome_profile()
```

Every downstream decision that currently reads `chrome_profile` (x.com's mandatory check/error, and the other three sites' `if chrome_profile:` thin-retry gate) reads `effective_chrome_profile` instead — no other logic changes. This is the key correction from the earlier proposal: **the default is a fallback for where the profile string comes from, not a new trigger for using cookies.** A generic/arxiv fetch that returns full content never touches `effective_chrome_profile` at all, default or not, because `is_thin()` is false and the retry branch never runs. A thin generic/arxiv fetch that previously wouldn't retry (no profile passed) will now opportunistically retry using the default, exactly as if the caller had passed it explicitly. x.com's mandatory check still hard-errors if `effective_chrome_profile` is still `None` after resolution (no default configured either).

### `extract-url-mcp` flow changes

`SKILL.md`'s step 2 changes from "gate on hostname == x.com/twitter.com, always re-detect and re-ask" to "gate on whether a default has ever been configured, checked once, regardless of URL":

1. Call `get_default_chrome_profile` (via a small MCP-calling script). If it returns a path, skip straight to dispatch — no detection, no question, ever again.
2. If it returns `None` (first use, any site): call `list_chrome_profiles` with x.com's `host_keys`/`cookie_names`, show the comparison table to the user, ask them to confirm the recommended profile or supply an alternate path. If confirmed, call `set_default_chrome_profile` to persist it, then dispatch. If the user declines to set one, proceed without a default — non-x.com URLs still work anonymously; an x.com URL will surface `fetch_article`'s existing mandatory-profile error.
3. Subagent 1 no longer needs an explicit `chrome_profile` value passed in the common case — `mcp_fetch_client.py` can omit it and let `fetch_article` resolve the default itself. The CLI's optional `[chrome_profile]` override argument stays, for the rare case of using a different profile than the stored default for one call.

`detect_xcom_chrome_profile.py` is replaced by a thin script that calls the MCP's `list_chrome_profiles`/`get_default_chrome_profile`/`set_default_chrome_profile` tools instead of querying Chrome's cookie database directly — removing the duplicated sqlite-reading logic from the skill layer entirely.

## Testing

- `browser-fetch-mcp`: real-network-style unit/integration tests for `list_chrome_profiles` (fixture Chrome profile dirs, same sqlite-fixture approach as today's `test_detect_xcom_chrome_profile.py`), `get_default_chrome_profile`/`set_default_chrome_profile` round-trip, and `fetch_article`'s resolution point — covering: (a) explicit `chrome_profile` still wins over a configured default, (b) x.com with no explicit profile falls back to a configured default and succeeds in resolving one, (c) x.com with no explicit profile and no default still hard-errors exactly as today, (d) a thin generic/arxiv result with no explicit profile picks up a configured default for the retry, (e) a non-thin generic/arxiv result never touches the default even when one is configured.
- `extract-url-mcp`: update/replace `test_detect_xcom_chrome_profile.py` for the new MCP-calling script; add a test that once-configured means no re-detection/no re-question on a second call.

## Migration note

Once merged, this is a genuine behavior change for `browser-fetch-mcp`'s existing consumers (currently only `extract-url-mcp`, per the standing build-only convention) — after a default is configured, thin generic/arxiv/wechat pages will opportunistically retry with cookies even when the caller passes nothing, where before they required an explicit `chrome_profile`. This is intentional and was explicitly requested.
