# Skill Testing Guide

Reference for AI agents writing or reviewing tests for skills in this repository.

---

## Overview

Skills have two independent testing layers, run separately:

| Layer | Command | What it tests |
|---|---|---|
| Structural | `npm test` | SKILL.md format, frontmatter fields, index registration |
| Behavioral | `npm run eval` | Does following the skill produce correct behavior? |

**Structural tests** catch authoring mistakes — missing fields, wrong versions, skills not registered in `skills-index.json`.

**Behavioral evals** catch semantic failures — a skill with perfect structure that doesn't actually enforce its intended constraints when followed by a model.

---

## Layer 1 — Structural Tests

### What runs

`npm test` includes `bats tests/skills.bats`, which loops over every skill registered in `skills-index.json` and checks:

1. `SKILL.md` file exists
2. Frontmatter delimiters (`---`) are present
3. `name`, `description`, `version` fields are non-empty
4. `version` matches `X.Y.Z` semver
5. `name` matches the directory name
6. `bundle` is defined in `bundleMeta`

All failures are collected and reported together — one bad skill does not hide others.

### Custom skill tests

`npm test` also runs `scripts/run-skill-tests.sh`, which discovers and runs any skill-specific bats/Python tests:

```
skills/<category>/<skill>/tests/*.bats   → bats
skills/<category>/<skill>/tests/*.py     → python3
```

Use these for skills that have external side-effects that can be deterministically verified (e.g., file generation, CLI output). They are intentionally narrow — only add them when there is something concrete and automatable to assert.

### When a structural test fails

- Missing `SKILL.md` → create the file at `skills/<category>/<skill>/SKILL.md`
- Frontmatter errors → fix the YAML block between the `---` delimiters
- Name mismatch → the `name:` field must equal the directory name exactly
- Bundle missing → add the bundle key to `bundleMeta` in `skills-index.json`

---

## Layer 2 — Behavioral Evals

### Mechanism

```
scripts/run-skill-evals.js
  └─ discovers skills/*/tests/*.eval.json
       └─ for each case:
            1. read SKILL.md → build prompt
            2. claude -p "<skill content>\n\nUser request: <prompt>" --model claude-haiku-4-5-20251001
            3. apply checks against the response
            4. rubric checks → second claude -p call as LLM judge
  └─ save results to eval-results/<timestamp>.json
```

The model used is `claude-haiku-4-5-20251001`. Switch to Sonnet only if Haiku cases are clearly too hard for that model tier.

### Eval file format

Each skill's evals live at `skills/<category>/<skill>/tests/<skill>.eval.json`:

```json
{
  "skill": "<skill-name>",
  "skill_path": "skills/<category>/<skill>",
  "cases": [
    {
      "id": "kebab-case-id",
      "description": "One sentence: what behavior this asserts",
      "prompt": "The user request to test (the 'user turn')",
      "checks": [
        { "type": "contains", "value": "some required string" },
        { "type": "not_contains", "value": "```" },
        { "type": "regex", "pattern": "option [123]", "flags": "i" },
        { "type": "rubric", "criteria": "The response does X before doing Y." }
      ]
    }
  ]
}
```

### Check types

| Type | Passes when | Use for |
|---|---|---|
| `contains` | Response includes the exact string | Required keywords, output paths, structural markers |
| `not_contains` | Response does NOT include the string | Forbidden content (e.g., code blocks before clarification) |
| `regex` | Pattern matches (supports `flags`) | Format constraints, alternation |
| `rubric` | LLM judge answers YES | Nuanced behavioral constraints that can't be expressed as string checks |

**Prefer deterministic checks.** Add `rubric` only when the behavior cannot be expressed as `contains`/`not_contains`/`regex`.

### Run commands

```bash
npm run eval                        # all skills
node scripts/run-skill-evals.js --skill brainstorming   # one skill
```

Results are always written to `eval-results/<timestamp>.json`.

---

## Current pilot skills

Three skills have behavioral evals. Use these as templates when writing evals for new skills.

### brainstorming

File: `skills/superpowers-fork/brainstorming/tests/brainstorming.eval.json`

| Case | What it asserts |
|---|---|
| `no-code-before-clarification` | Given a bare implementation request, no code block appears; asks clarifying question |
| `propose-multiple-options` | Given a feature request, proposes 2+ distinct options |
| `hard-gate-simple-task` | Even a "simple" task goes through design phase, not immediate code |

### systematic-debugging

File: `skills/superpowers-fork/systematic-debugging/tests/systematic-debugging.eval.json`

| Case | What it asserts |
|---|---|
| `no-fix-before-phase1` | Bug report → no code patch; begins Phase 1 investigation |
| `root-cause-first` | Test failure → focuses on root cause, not immediate fix |
| `investigation-steps-mentioned` | Intermittent bug → describes concrete investigation steps before any fix |

### skill-analyzer

File: `skills/analysis/skill-analyzer/tests/skill-analyzer.eval.json`

| Case | What it asserts |
|---|---|
| `trigger-activates-framework` | Trigger phrase → mentions the 4-layer onion model framework |
| `output-path-correct` | Trigger phrase → mentions `skill-analysis/` output directory, not skill's own dir |
| `project-type-detection-first` | Trigger phrase → mentions checking `SKILL.md` as first step |

---

## Writing new eval cases

### Decision tree

```
Does the skill enforce a HARD constraint?
  yes → write a not_contains or rubric check that verifies it is NOT violated
  no  → Does the skill require specific output structure?
          yes → write contains checks for structural markers
          no  → write a rubric check for the general behavioral intent
```

### Guidelines

- **One behavior per case.** Don't bundle multiple assertions into one case — a failure message becomes harder to diagnose.
- **Test the constraint, not the phrasing.** `rubric` criteria should describe the behavior, not the exact words.
- **Keep prompts realistic.** Use natural user requests, not artificial prompts designed to trick the model.
- **3–5 cases per skill** is the target range. More cases are fine if the skill has distinct modes; fewer is fine for simple skills.
- **Deterministic checks first.** If a `contains` check works, don't use `rubric` — LLM judge calls cost time and add variance.

### Template

```json
{
  "skill": "my-skill",
  "skill_path": "skills/category/my-skill",
  "cases": [
    {
      "id": "enforces-key-constraint",
      "description": "Given X, must do Y before Z",
      "prompt": "Natural user request that should trigger the constraint",
      "checks": [
        { "type": "not_contains", "value": "forbidden string" },
        { "type": "rubric", "criteria": "The response does Y before Z. It does not skip Y." }
      ]
    }
  ]
}
```

---

## Common mistakes

| Mistake | Fix |
|---|---|
| Rubric criteria describe exact phrasing | Describe the behavioral intent, not specific words |
| Single case tests everything | Split into one case per distinct constraint |
| `rubric` for something expressible as `contains` | Use the deterministic check — it's faster and more stable |
| Eval file placed outside `tests/` | Must be at `skills/<category>/<skill>/tests/<skill>.eval.json` |
| `skill_path` has leading `/` or trailing `/` | Use relative path from repo root, no slashes at start/end |
| Running evals as part of `npm test` | Evals are separate — run `npm run eval`; never add to `npm test` |
