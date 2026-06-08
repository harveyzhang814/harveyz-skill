# hskill Cache Reference

Command interface and file format for the `hskill` local cache.

---

## Commands

| Command | Description |
|---------|-------------|
| `hskill cache clear` | Clear the cache immediately |
| `hskill cache status [--json]` | Show whether cache is valid and remaining TTL; `--json` returns machine-readable output |
| `hskill cache set-ttl <seconds>` | Set cache TTL (persists across invocations) |

---

## Cache File

Location: `~/.cache/hskill/index.json`

```json
{
  "generated_at": "2026-05-28T10:00:00Z",
  "ttl_seconds": 60,
  "skills": [ "..." ],
  "tools": [ "..." ],
  "hooks": [ "..." ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | ISO 8601 string | Timestamp when cache was written |
| `ttl_seconds` | integer | Configured TTL in seconds; default is 60 |
| `skills` | array | Cached output of skill scan |
| `tools` | array | Cached output of tool scan |
| `hooks` | array | Cached output of hooks scan (added in revised design) |

---

## Invalidation

The cache is invalidated when:

- The TTL has elapsed since `generated_at`
- `hskill cache clear` is run manually
