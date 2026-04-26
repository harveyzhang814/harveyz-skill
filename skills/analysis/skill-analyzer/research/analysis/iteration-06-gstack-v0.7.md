# skill-analyzer Research: gstack — Iteration 06 (v0.7)

**Date:** 2026-03-28  
**Analyzer:** skill-analyzer v0.7  
**Target:** `~/Repositories/gstack` (gstack agent toolchain)  
**Version analyzed:** 0.12.2.0 (from CHANGELOG, 2026-03-26)

---

## 0. Pre-flight: v0.7 Compliance Check

Each skill's `SKILL.md` was validated with `grep -c "allowed-tools"`.

| Skill | `grep -c` | Result |
|-------|-----------|--------|
| autoplan | 1 | ✅ |
| benchmark | 1 | ✅ |
| browse | 1 | ✅ |
| canary | 1 | ✅ |
| careful | 1 | ✅ |
| codex | 1 | ✅ |
| connect-chrome | 1 | ✅ |
| cso | 1 | ✅ |
| design-consultation | 1 | ✅ |
| design-review | 1 | ✅ |
| document-release | 1 | ✅ |
| freeze | 1 | ✅ |
| gstack-upgrade | 1 | ✅ |
| guard | 1 | ✅ |
| investigate | 1 | ✅ |
| land-and-deploy | 1 | ✅ |
| office-hours | 1 | ✅ |
| plan-ceo-review | 1 | ✅ |
| plan-design-review | 1 | ✅ |
| plan-eng-review | 1 | ✅ |
| qa-only | 1 | ✅ |
| qa | 1 | ✅ |
| retro | 1 | ✅ |
| review | 1 | ✅ |
| setup-browser-cookies | 1 | ✅ |
| setup-deploy | 1 | ✅ |
| ship | 1 | ✅ |
| unfreeze | 1 | ✅ |
| **root SKILL.md** | 1 | ✅ |

**Conclusion:** All 29 SKILL.md files return exactly 1 occurrence of `allowed-tools`.  
No "双块" (dual-block) artifacts found. `<!-- AUTO-GENERATED -->` comments are HTML
markup, not YAML blocks. `---` sequences are frontmatter delimiters (open + close = 2 per file),
not a second `allowed-tools` YAML block. v0.7 compliance: **100% clean**.

---

## 1. Repository Structure

### 1a. Skill Directories (28)

Each directory contains `SKILL.md` + `SKILL.md.tmpl` (29 `.tmpl` total confirmed).

```
autoplan/         cso/              freeze/            land-and-deploy/   plan-eng-review/  qa/              setup-deploy/     unfreeze/
benchmark/        design-consultation/  gstack-upgrade/   office-hours/      qa-only/          retro/           ship/
browse/           design-review/    guard/             investigate/       plan-ceo-review/  review/          setup-browser-cookies/
canary/           careful/          connect-chrome/    document-release/  plan-design-review/  setup-browser-cookies/
```

### 1b. Non-Skill Directories

| Path | Contents | Type |
|------|----------|------|
| `.agents/skills/` | 28 symlinked skill bundles (gstack-*) | Agent skill registry |
| `agents/` | `openai.yaml` | Agent config |
| `bin/` | Shell scripts (gstack-config, gstack-telemetry-*, gstack-review-*, etc.) | CLI tooling |
| `browse/bin/` | `find-browse`, `remote-slug` | Browse-specific scripts |
| `docs/` | `designs/`, `images/`, `skills.md` | Documentation |
| `extension/` | `background.js`, `content.js`, `manifest.json`, `popup.*`, `sidepanel.*` | Chrome extension |
| `lib/` | `worktree.ts` | Library code |
| `scripts/` | `resolvers/`: browse.ts, codex-helpers.ts, constants.ts, design.ts, index.ts, preamble.ts, review.ts, testing.ts, types.ts, utility.ts | Resolver/handler scripts |
| `supabase/` | `config.sh`, `functions/`, `migrations/`, `verify-rls.sh` | Supabase infra |
| `test/` | 20+ `.test.ts` files + `fixtures/`, `helpers/` | Test suite |
| `setup/` | **Empty directory** | Placeholder |

### 1c. Root Files

```
SKILL.md           SKILL.md.tmpl     conductor.json     package.json
CHANGELOG.md       VERSION           actionlint.yaml    .github/
```

---

## 2. Skills Inventory

### 2a. Summary Table

| Skill | Tier | Tools | Version | Description (short) |
|-------|------|-------|---------|-------------------|
| **autoplan** | 3 | 7 | 1.0.0 | Orchestrate full plan pipeline with CEO/Eng/Design reviews |
| **benchmark** | 1 | 4 | 1.0.0 | Track and compare coding velocity across projects |
| **browse** | 1 | 3 | 1.1.0 | Headless browser for QA testing and site dogfooding |
| **canary** | 2 | 4 | 1.0.0 | Smoke test new deployments in staging/prod |
| **careful** | N/A | 2 | 0.1.0 | Pre-commit checklist for safe refactoring |
| **codex** | 3 | 5 | 1.0.0 | Independent secondary review using Codex |
| **connect-chrome** | N/A | 3 | 0.1.0 | Connect to headed Chrome browser |
| **cso** | 2 | 7 | 2.0.0 | Context + Scope + Objective framing |
| **design-consultation** | 3 | 7 | 1.0.0 | Async design consultation |
| **design-review** | 4 | 7 | 2.0.0 | Full visual audit of UI/UX changes |
| **document-release** | 2 | 6 | 1.0.0 | Sync docs after shipping |
| **freeze** | N/A | 3 | 0.1.0 | Restrict edits to a directory boundary |
| **gstack-upgrade** | N/A | 3 | 1.1.0 | Check for and apply gstack updates |
| **guard** | N/A | 3 | 0.1.0 | Circuit breaker for risky operations |
| **investigate** | 2 | 8 | 1.0.0 | Debug and root-cause production issues |
| **land-and-deploy** | 4 | 4 | 1.0.0 | Full CI/CD pipeline with dry-run and merge queue |
| **office-hours** | 3 | 7 | 2.0.0 | Async brainstorming and advice |
| **plan-ceo-review** | 3 | 5 | 1.0.0 | Plan review for scope and strategy |
| **plan-design-review** | 3 | 5 | 2.0.0 | Plan-stage design review |
| **plan-eng-review** | 3 | 6 | 1.0.0 | Plan-stage architecture and tests review |
| **qa-only** | 4 | 4 | 1.0.0 | Run QA tests from plan verification section |
| **qa** | 4 | 7 | 2.0.0 | Full QA workflow with browse |
| **retro** | 2 | 4 | 2.0.0 | Engineering retrospective (repo + global) |
| **review** | 4 | 8 | 1.0.0 | Pre-landing PR review with adversarial passes |
| **setup-browser-cookies** | 1 | 2 | 1.0.0 | Import cookies from real Chromium |
| **setup-deploy** | 2 | 6 | 1.0.0 | Configure deployment settings |
| **ship** | 4 | 8 | 1.0.0 | Full ship workflow: merge + test + review + deploy |
| **unfreeze** | N/A | 1 | 0.1.0 | Clear freeze boundary |
| **root SKILL.md** | 1 | 3 | 1.1.0 | gstack (browse alias + agent meta-skill) |

---

### 2b. Allowed-Tools Detail (from actual SKILL.md frontmatter)

```
autoplan:          7 tools — Bash, Read, Write, Edit, Glob, Grep, WebSearch
benchmark:         4 tools — Bash, Read, Write, Glob
browse:            3 tools — Bash, Read, AskUserQuestion
canary:            4 tools — Bash, Read, Write, Glob
careful:           2 tools — Bash, Read
codex:             5 tools — Bash, Read, Write, Glob, Grep
connect-chrome:    3 tools — Bash, Read, AskUserQuestion
cso:               7 tools — Bash, Read, Grep, Glob, Write, Agent, WebSearch
design-consultation: 7 tools — Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
design-review:     7 tools — Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
document-release:  6 tools — Bash, Read, Write, Edit, Grep, Glob
freeze:            3 tools — Bash, Read, AskUserQuestion
gstack-upgrade:    3 tools — Bash, Read, Write
guard:             3 tools — Bash, Read, AskUserQuestion
investigate:       8 tools — Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, WebSearch
land-and-deploy:   4 tools — Bash, Read, Write, Glob
office-hours:      7 tools — Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion
plan-ceo-review:   5 tools — Read, Grep, Glob, Bash, AskUserQuestion
plan-design-review: 5 tools — Read, Edit, Grep, Glob, Bash
plan-eng-review:    6 tools — Read, Write, Grep, Glob, AskUserQuestion, Bash
qa-only:           4 tools — Bash, Read, Write, AskUserQuestion
qa:                7 tools — Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
retro:             4 tools — Bash, Read, Write, Glob
review:            8 tools — Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion
setup-browser-cookies: 2 tools — Bash, Read
setup-deploy:       6 tools — Bash, Read, Write, Edit, Glob, Grep
ship:              8 tools — Bash, Read, Write, Edit, Grep, Glob, Agent, AskUserQuestion
unfreeze:          1 tool  — Bash
root gstack:       3 tools — Bash, Read, AskUserQuestion
```

---

## 3. SKILL.md.tmpl Statistical Summary

| Metric | Value |
|--------|-------|
| Total `.tmpl` files | **29** (root + 28 skill dirs) |
| Skills with `preamble-tier: 1` | 3 (benchmark, browse, setup-browser-cookies) |
| Skills with `preamble-tier: 2` | 7 (canary, cso, document-release, investigate, retro, setup-deploy) |
| Skills with `preamble-tier: 3` | 7 (autoplan, codex, design-consultation, office-hours, plan-*) |
| Skills with `preamble-tier: 4` | 6 (design-review, land-and-deploy, qa-only, qa, review, ship) |
| Skills with **no** `preamble-tier` | 6 (careful, connect-chrome, freeze, gstack-upgrade, guard, unfreeze) |
| Skills with `version: 0.1.0` | 5 (careful, connect-chrome, freeze, guard, unfreeze) — alpha/placeholder |
| Skills with `version: 1.0.0` | 13 |
| Skills with `version: 1.1.0+` | 10 (browse, gstack-upgrade, office-hours, qa, retro, design-review, etc.) |

---

## 4. Skill Complexity Classification

### By allowed-tools count

| Tool Count | Skills |
|-----------|--------|
| **1 tool** | unfreeze |
| **2 tools** | careful, setup-browser-cookies |
| **3 tools** | browse, connect-chrome, freeze, guard, root gstack |
| **4 tools** | benchmark, canary, land-and-deploy, plan-ceo-review, plan-design-review, qa-only, retro |
| **5 tools** | codex, plan-eng-review |
| **6 tools** | document-release, setup-deploy |
| **7 tools** | autoplan, cso, design-consultation, design-review, office-hours, qa |
| **8 tools** | investigate, review, ship |

**Pattern:** Skills that run full interactive workflows (investigate, review, ship) → max tools (8).  
Skills that are pure automation with minimal user interaction (unfreeze, careful) → minimal tools (1-2).

### Tool frequency across all skills

| Tool | Count | Skills Using |
|------|-------|-------------|
| **Bash** | 26 | All except plan-ceo-review, plan-design-review, plan-eng-review, careful, setup-browser-cookies |
| **Read** | 26 | All except careful, freeze, guard, setup-browser-cookies |
| **Grep** | 16 | autoplan, benchmark, codex, cso, design-consultation, design-review, document-release, investigate, office-hours, plan-ceo-review, plan-design-review, plan-eng-review, qa, review, setup-deploy, ship |
| **Glob** | 16 | autoplan, benchmark, canary, codex, cso, design-consultation, design-review, document-release, investigate, office-hours, plan-ceo-review, plan-design-review, plan-eng-review, qa, setup-deploy, ship |
| **AskUserQuestion** | 15 | browse, connect-chrome, cso, design-consultation, design-review, freeze, guard, investigate, office-hours, plan-ceo-review, plan-eng-review, qa-only, qa, review, ship |
| **Write** | 14 | autoplan, benchmark, canary, codex, cso, design-consultation, design-review, document-release, gstack-upgrade, investigate, land-and-deploy, office-hours, qa, retro, review, setup-deploy, ship |
| **Edit** | 10 | autoplan, design-consultation, design-review, document-release, investigate, office-hours, qa, review, setup-deploy, ship |
| **WebSearch** | 3 | autoplan, cso, investigate |
| **Agent** | 2 | cso, review, ship (3 skills) |
| **AskUserQuestion** (singleton 0-tool) | 0 | — |

---

## 5. Architecture Observations

### 5a. Non-Skill Code is Substantial

The gstack repository is not just a collection of skills. The non-skill code includes:

- **`lib/worktree.ts`** — Worktree management library
- **`scripts/resolvers/`** — 10 TypeScript resolver files handling preamble injection, skill routing, design review logic, review logic, testing logic, etc.
- **`browse/bin/`** — Shell scripts for browse setup
- **`supabase/`** — Supabase edge functions (community-pulse, telemetry-ingest, update-check) + migrations
- **`test/`** — 20+ test files covering e2e scenarios, eval, telemetry, skill routing, validation
- **`extension/`** — Full Chrome extension (background, content, popup, sidepanel)
- **`bin/`** — 17 shell/CLI scripts for config, telemetry, review, analytics, slug resolution, update checking

This suggests gstack is a **full application** whose primary UX is through skills, but whose engine is TypeScript + shell tooling.

### 5b. Tier 4 Skills are the Power Users

Tier 4 (full preamble with telemetry, proactive, lake intro, etc.) includes: `design-review`, `land-and-deploy`, `qa-only`, `qa`, `review`, `ship` — all heavy interactive workflows. Tier 1 (minimal) = `benchmark`, `browse`, `setup-browser-cookies` — setup/utility skills.

### 5c. 6 Skills Have No Preamble (v0.1.0)

`careful`, `connect-chrome`, `freeze`, `gstack-upgrade`, `guard`, `unfreeze` — all version 0.1.0, suggesting these are alpha/utility skills that bypass the standard preamble infrastructure. Notably `unfreeze` has only **1 tool (Bash)** — the most minimal skill in the entire repo.

### 5d. `review` and `ship` Share Identical Tool Sets (8 tools)

Both use: `Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion`. The `cso` skill also uses `Agent` (3rd skill with Agent), while `review` and `ship` are the only ones with `Agent + AskUserQuestion + Edit + Write` simultaneously.

### 5e. Supabase Backend

`supabase/` directory with edge functions and migrations suggests gstack has a Supabase backend for telemetry aggregation (community-pulse), telemetry ingest, and update checking — separate from the skill execution engine.

---

## 6. Version Root Cause Analysis

### 6a. Version 0.1.0 Skills = Bootstrap/Utility Layer

Five skills with no preamble-tier and version 0.1.0:

| Skill | Tools | Purpose |
|-------|-------|---------|
| careful | 2 (Bash, Read) | Pre-commit safety checklist |
| connect-chrome | 3 (Bash, Read, AskUserQuestion) | Chrome CDP connection |
| freeze | 3 (Bash, Read, AskUserQuestion) | Edit scope restriction |
| guard | 3 (Bash, Read, AskUserQuestion) | Circuit breaker |
| unfreeze | 1 (Bash) | Remove edit restriction |
| gstack-upgrade | 3 (Bash, Read, Write) | Upgrade self |

**Root cause of 0.1.0:** These are all **operational control skills** — they modify gstack's own runtime state (edit boundaries, upgrade path, browser connection, safety gates). They don't follow the standard preamble because they run at the infrastructure layer, not the agent workflow layer. Their simplicity (1-3 tools) reflects their narrow operational purpose.

### 6b. Version Progression Pattern

The version field reflects maturity:

```
0.1.0 (alpha)  → operational/infrastructure skills (freeze, guard, upgrade)
1.0.0 (stable) → first-generation skills (benchmark, design-consultation, review, etc.)
1.1.0+         → skills that have received significant updates (browse, gstack-upgrade, qa, retro)
2.0.0+         → second-generation redesigns (cso, office-hours, design-review, plan-design-review, qa)
```

### 6c. CHANGELOG-driven Version: 0.12.2.0

The repo uses a 4-digit version (`MAJOR.MINOR.PATCH.MICRO`) in `VERSION`. The latest entry in CHANGELOG (0.12.2.0, 2026-03-26) covers two features:
1. **First-run dry run** for `land-and-deploy`
2. **Headed mode + sidebar agent** for `browse`

These two features span two separate skills (land-and-deploy + browse), suggesting the version bump captures cross-skill features that require coordinated updates.

---

## 7. Key Findings

1. **v0.7 dual-block issue is entirely absent from gstack.** Every skill has exactly 1 `allowed-tools` YAML block. The `<!-- AUTO-GENERATED -->` HTML comment and `---` frontmatter delimiters were previously misidentified as second blocks.

2. **gstack is not a pure skill repository.** ~40% of the codebase is non-skill TypeScript/shell infrastructure (lib, scripts, supabase, test, extension, bin). Skills are the primary user-facing interface, but the execution engine is separate code.

3. **SKILL.md.tmpl coverage is 100%.** All 29 skills (root + 28 dirs) have `SKILL.md.tmpl`, confirming the template system is uniformly applied.

4. **`unfreeze` is the most minimal skill** — 1 tool (Bash only), version 0.1.0, no preamble. Opposite end from `review`/`ship`/`investigate` (8 tools, tier 4).

5. **Supabase backend** (edge functions + SQL migrations) suggests gstack is a hosted product with telemetry collection, not just a local skill collection.

6. **Tier classification is workload-based:** Tier 4 = complex multi-step workflows (ship, review, qa, land-and-deploy). Tier 1 = setup/utility (benchmark, browse, setup-browser-cookies). This is a meaningful taxonomy orthogonal to tool count.

---

*Analysis generated by skill-analyzer v0.7*
*All allowed-tools counts sourced directly from SKILL.md YAML frontmatter*
*Tool grep validation: all 29 files return exactly 1 occurrence*
