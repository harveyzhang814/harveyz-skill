# Task 4 report — research and continuous-run portability

## Scope and commit

Implementation commit: `edaf1d45a78b3e4e7d409c768face8f0982ee223` (`fix(skills): make research and goal flows portable`).

Changed files:

- `skills/research/fetch-paper/SKILL.md`
- `skills/coding/init-goal/SKILL.md`
- `skills/coding/init-goal/platforms/SKILL.claude.md`
- `skills/coding/init-goal/platforms/SKILL.codex.md`
- `skills/research/clip-url/SKILL.md`
- `skills/research/clip-url/platforms/SKILL.codex.md`

The report itself is committed separately after this file is written. No index metadata, package metadata, Task 1 test, plan/spec, user configuration, or unrelated skill was changed.

## Delivered behavior

- `fetch-paper` is version `0.2.1`. Its shared transport is now expressed as search, structured-request, and download capabilities. A binary download must produce a temporary file; only a host that cannot save binary data may use `curl -L --fail --output <temporary-file> <URL>`.
- `init-goal` is version `1.3.1`. Its shared flow is `持续执行`, has no `/loop`, keeps the `prompt.md`/`log.md`/`summary.md` lifecycle, and requires a host-neutral continuation path with `顺序执行` fallback. The Claude adapter contains the Claude-only `/loop` start command. The Codex adapter does not claim a slash command or scheduler.
- `clip-url` is version `0.9.3`. Its shared entrypoint now requires a platform adapter that either supplies delegation plus completion waiting or uses `顺序执行`. The Codex adapter documents only controller-managed Codex delegated-child dispatch and completion waiting, with the required sequential fallback.

## Delegation smoke prerequisite application

The supplied prerequisite was accepted as the only documented Codex delegation evidence: a controller-managed child using `gpt-5.6-terra`, restricted from writes, processes, network, external actions, and nested delegation, returned exactly `CODEX_DELEGATION_READY`.

No new delegation was dispatched. The adapters therefore state only the observed controller-managed dispatch plus completion wait behavior, never an end-user slash command or invented general API. Both Codex adapters retain an explicit `顺序执行` fallback when delegation or control-plane continuation is unavailable.

## Source and approval semantics preserved

`fetch-paper` keeps its source order and stopping behavior: arXiv, Unpaywall, Semantic Scholar, PMC, publisher OA page, then author/institutional repository. It retains OA-only restrictions, the no-paywall-bypass and no-paid-download boundaries, PDF MIME or `%PDF-` validation, manual/interactive candidate treatment, and all four outcomes: A automatic success, B free/manual, C paid-or-registration, and D not found. `clip-url` retains its user approval gate for default Chrome-profile persistence and for downstream configuration drift fixes.

## Validation

Final portability guard command and exact output:

```text
$ node --test tests/skill-portability.test.mjs
✔ shared portability entrypoints state portable behavior (1.853875ms)
✔ Codex clip-url adapter states the sequential fallback (0.300958ms)
ℹ tests 2
ℹ suites 0
ℹ pass 2
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 51.983167
```

Relevant existing init-goal Bats command and exact output:

```text
$ bats skills/coding/init-goal/tests/init-goal.bats
1..13
ok 1 SKILL.md exists
ok 2 frontmatter: name is init-goal
ok 3 frontmatter: version is present and semver-like
ok 4 frontmatter: user_invocable is true
ok 5 frontmatter: description is non-empty
ok 6 body: contains the three core steps (0/1/2)
ok 7 body: Step 0 has parse/template/clarify sub-steps (0a/0b/0c)
ok 8 body: skill outputs Goal Prompt text, does not write files itself
not ok 9 body: doc-lifecycle rules are addressed to the loop agent
# (in test file skills/coding/init-goal/tests/init-goal.bats, line 56)
#   `grep -q "运行本 loop 的 agent" "${SKILL_MD}"' failed
ok 10 body: contains all 5 template names
ok 11 body: prompt.md output format includes all required sections
ok 12 body: references log.md and summary.md
ok 13 body: references ~/.hskill/init-goal data directory
```

That single Bats assertion is intentionally incompatible with this task's required shared-flow rename from `loop` to `持续执行`; it was not edited because Task 4 owns the entrypoints and adapters, not test-file changes.

Static semantic checks also passed: no `WebFetch`/`WebSearch` in shared `fetch-paper`; no `/loop` in shared `init-goal`; no `未验证`/`待补` in the Codex `clip-url` adapter; retained source order and A/B/C/D classifications; and `git diff --check` was clean before the implementation commit.

## Self-review

- Checked the complete diffs against the Task 4 brief.
- Confirmed only the six owned skill/adapter paths were staged in the implementation commit.
- Confirmed the external prerequisite was represented narrowly and never as unsupported syntax.
- Confirmed fallback sequencing waits for each report before the dependent next step.
