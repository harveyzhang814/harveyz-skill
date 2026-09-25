# A1 Skill portability verification

Date: 2026-09-25

| Scope | Evidence | Result |
|---|---|---|
| Static contracts | `node --test tests/skill-portability.test.mjs` | PASS: 5/5 |
| learn-video non-default path | Temporary `/tmp/learn-video-skill.zt8fBB/learn-video` symlink contained all three referenced scripts | PASS |
| extract-vision text fallback | Controlled OCR text extracted `日期 2026-09-25` and `总金额 ¥128.50`; no-original-vision stop is specified | PASS (static/isolated) |
| close-node safe no-detach branch | Static regression covers preserved worktree and stop before hide/stop-node | PASS (static) |
| Real video, image, Canvas hosts | Not exercised: no explicit authorization for real video/image/active Canvas node | NOT VERIFIED |
| Full suite | `npm test` reached hook E2E tests 37 and 38, which failed | BASELINE RED; see below |

## Baseline-red attribution

Both the fix worktree and local `staging` reproduce:

```bash
bats -f 'hook e2e: real LLM' tests/hook-script.bats
```

Both exit 1 at `tests/hook-script.bats:182` and `:199`, whose hook invokes the externally authenticated `claude -p` command. The A1 diff does not change that hook or its tests. This submission is therefore explicitly **带着这条红送验**; the two E2E cases must be re-run by acceptance alongside the full anchor set.
