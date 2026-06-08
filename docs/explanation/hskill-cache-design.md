# hskill Cache Design

Why the cache exists, and why TTL is configurable rather than fixed.

---

## Why cache at all

`hskill list` and `hskill status` scan the skills, tools, and hooks directories on every invocation. In workflows that call these commands repeatedly (e.g., an agent loop, a CI pipeline with multiple steps), the repeated filesystem scans add latency without producing new information. The cache stores the scan results in `~/.cache/hskill/index.json` and returns them until the TTL expires.

---

## Why TTL is configurable, not fixed

The initial design used a hard-coded 5-minute TTL. In CI pipelines, two `hskill status` calls within the same job are often separated by less than 5 minutes. The second call would return data generated before the job started, which could reflect a different installed state.

A configurable TTL lets users tune the trade-off between freshness and performance per environment:

- **CI / automation** — short TTL (e.g., 10–30 s) to ensure each step sees current state
- **Interactive shell** — longer TTL (e.g., 300 s) to avoid perceptible delay

The default TTL is 60 seconds, which is conservative enough to be safe in most CI environments while still providing a meaningful cache hit for rapid successive calls.

---

## Scope: what is cached

The cache covers three scan domains:

| Domain | Why included |
|--------|-------------|
| `skills` | Skill directory scans are the primary source of latency |
| `tools` | Tool scans follow the same pattern |
| `hooks` | Added in the revised design; hooks are read on every non-trivial command and were previously uncached |

See [reference/hskill-cache.md](hskill-cache.md) for the command interface and file format.
