# Video-Learner: capture uploader_id/channel_id/uploader_url Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This plan targets the `Video-Learner` repo** (`~/Projects/Video-Learner`), NOT the `harveyz-skill` worktree this file lives in. Before Task 1: `cd ~/Projects/Video-Learner`, confirm `git rev-parse --abbrev-ref HEAD` is `staging`, then `git checkout -b feature/creator-index-fields`. This repo has no worktree convention (see its `CLAUDE.md`) — a plain feature branch in the existing working tree is correct. Never commit to `staging`/`master` directly; merge with `--no-ff` only when this plan is fully done and reviewed.
>
> **Sequencing note:** This is step 1 of 3 sequential repo plans (Video-Learner → harveyz-skill/learn-video → scholia), per `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` §4.1. Do not start the harveyz-skill plan until Task 4 here (the real 67-task backfill) is done — its `archive.py` will start rejecting `meta.json` files that lack the contract fields this plan produces.

**Goal:** Make vdl capture and persist `uploader_id` / `channel_id` / `uploader_url` from yt-dlp, fix the playlist-URL multi-line-uploader bug, and make `meta.json` carry these 3 fields plus the unified-store contract fields (`source_url`/`title`/`fetched_at`) so it becomes the single, self-sufficient source of truth for `learn-video`'s downstream index.

**Architecture:** Three narrow additions to an existing pipeline — no new files, no new concepts. yt-dlp already returns these fields in its `--dump-json` output; vdl just wasn't reading them. The DB gets 3 more `TEXT` columns via the existing `PRAGMA table_info` migration idiom. `buildTaskMeta` (the sole `meta.json` writer going forward, per the design's decision to demote `learn-video`'s `archive.py` to a validator) reads them off the DB row like every other field.

**Tech Stack:** Bash + `yt-dlp` + `jq` + `sqlite3` (fetch step), Node.js + `better-sqlite3` (orchestrator/DB), plain `node:assert`-based test scripts (no test framework — see Global Constraints).

**Spec:** `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` (read alongside this plan — this plan implements §1.3, §1.4 row 1, §2.1, §2.2, §4.1 step 1, §4.2, §4.4).

## Global Constraints

- **`meta.json` becomes vdl's sole responsibility.** After this plan (and the harveyz-skill plan that follows it), nothing else writes `meta.json`. `buildTaskMeta` must emit both the 3 new platform fields AND the unified-store contract's 3 required fields (`source_url`, `title`, `fetched_at`) — spec §1.3.
- **The playlist bug fix and the 3 new fields must ship together** — both live in the same `yt-dlp --dump-json` call and the same `jq`/SQL block in `fetch_info.sh`; splitting them would leave a moment where new fields ship with the pre-existing multi-line-corruption bug.
- **Do not touch `registry.json`, `manage-creators`, `sync-ytchannel`, or `sync-xtimeline`.** Zero changes, per spec §1.5.
- **Test convention in this repo:** no framework. Every `tests/*.test.js` is a plain Node script using `require('assert')`, prints `<file>: PASS` and `process.exit(0)` on success, prints the error and `process.exit(1)` on failure. Run one file with `node tests/<file>.test.js`. There is no single `npm test` — CLAUDE.md lists scoped `npm run test:*` scripts; this plan's new/changed tests are run directly by filename.
- **Branch/commit convention:** feature branch only, `git merge --no-ff` at the end, never commit directly to `staging`.
- **The only irreversible operation in this whole cross-repo effort is inside Task 4** (`backfill_meta_json.js` overwrites all 68 `meta.json` files). Task 4 has an explicit backup step before that runs — do not skip it.

---

### Task 1: Add 3 DB columns and keep the two other schema copies in sync

**Files:**
- Modify: `core/orchestrator/db.js:113-121` (insert new migration block before the `steps` table creation at line 123)
- Modify: `cli/commands/config.js:38-56` (`initSchema` CREATE TABLE literal) and `cli/commands/config.js:97-106` (`migrateWorkDir`'s `insertTask` column list)
- Test: `tests/uploader-fields-db.test.js` (new)
- Test: `tests/cli-config-migrate.test.js` (add one case)

**Interfaces:**
- Produces: `tasks.uploader_id`, `tasks.channel_id`, `tasks.uploader_url` columns (all `TEXT`, nullable), readable via existing `db.getTask(id)` (uses `SELECT *`, no query change needed) and writable via existing `db.updateTask(id, { uploader_id, channel_id, uploader_url })` (fully dynamic, no change needed).

- [ ] **Step 1: Write the failing DB-roundtrip test**

Create `tests/uploader-fields-db.test.js`:

```js
'use strict';
/**
 * DB roundtrip for uploader_id/channel_id/uploader_url — same pattern as
 * tests/opencode-session-db.test.js.
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { createDb } = require('../core/orchestrator/db');

const ROOT_DIR = path.resolve(__dirname, '..');

async function run() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'vl-uploader-fields-db-'));
  process.env.WORK_ROOT = tmp;

  const db = createDb(ROOT_DIR);
  const taskId = `dbtest-uploader-${Date.now()}`;
  const url = `https://www.youtube.com/watch?v=dbtest${Date.now()}`;

  try {
    db.createTask(taskId, url);
    db.updateTask(taskId, {
      uploader_id: '@alejandro_ao',
      channel_id: 'UC1oXUA7qgs0GZc_yk46K2OQ',
      uploader_url: 'https://www.youtube.com/@alejandro_ao',
    });

    const row = db.getTask(taskId);
    assert.ok(row, 'task should exist in DB after createTask');
    assert.strictEqual(row.uploader_id, '@alejandro_ao');
    assert.strictEqual(row.channel_id, 'UC1oXUA7qgs0GZc_yk46K2OQ');
    assert.strictEqual(row.uploader_url, 'https://www.youtube.com/@alejandro_ao');

    console.log('uploader-fields-db: all tests passed');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

run().catch((e) => { console.error(e); process.exit(1); });
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `node tests/uploader-fields-db.test.js`
Expected: throws — `SqliteError: table tasks has no column named uploader_id` (columns don't exist yet).

- [ ] **Step 3: Add the migration block in `db.js`**

In `core/orchestrator/db.js`, insert this block right after the existing `opencode_session_id` migration (after line 121, before the `db.exec(\`CREATE TABLE IF NOT EXISTS steps ...\`)` at line 123):

```js
  // Migration: yt-dlp uploader identity fields (video-creator-index feature)
  try {
    const cols = db.prepare('PRAGMA table_info(tasks)').all();
    const names = cols.map((c) => c.name);
    if (!names.includes('uploader_id'))  db.exec(`ALTER TABLE tasks ADD COLUMN uploader_id TEXT`);
    if (!names.includes('channel_id'))   db.exec(`ALTER TABLE tasks ADD COLUMN channel_id TEXT`);
    if (!names.includes('uploader_url')) db.exec(`ALTER TABLE tasks ADD COLUMN uploader_url TEXT`);
  } catch (_) {
    // ignore
  }
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `node tests/uploader-fields-db.test.js`
Expected: `uploader-fields-db: all tests passed`

- [ ] **Step 5: Fix the two other schema copies (`cli/commands/config.js`)**

These are only exercised when a user runs `vdl config set work-root <path>` and it triggers a merge — but if left stale, the 3 new columns you just added would be silently dropped by that merge path, which is a bug this task would otherwise introduce (not pre-existing — `db.js`'s migration is what makes these columns real).

In `initSchema(db)` (around line 38-49 of `cli/commands/config.js`), add the 3 columns to the CREATE TABLE literal:

```js
function initSchema(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY, url TEXT NOT NULL, ts TEXT, title TEXT, lang TEXT,
      duration TEXT, output_lang TEXT DEFAULT 'zh-CN', focus TEXT, uploader TEXT,
      transcripts TEXT DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT,
      mode TEXT DEFAULT 'both', status TEXT, timeout_scale REAL DEFAULT 1,
      width INTEGER, height INTEGER, file_size INTEGER, bit_rate INTEGER,
      upload_date TEXT, uploader_id TEXT, channel_id TEXT, uploader_url TEXT
    );
    CREATE TABLE IF NOT EXISTS steps (
      id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
      step_name TEXT NOT NULL, status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0,
      error TEXT, started_at TEXT, completed_at TEXT,
      FOREIGN KEY (task_id) REFERENCES tasks(id), UNIQUE(task_id, step_name)
    );
  `);
}
```

In `migrateWorkDir`'s `insertTask` prepared statement (around line 97-106), add the 3 columns to both the column list and the `VALUES` placeholder list:

```js
  const insertTask = newDb.prepare(`
    INSERT OR IGNORE INTO tasks
      (id, url, ts, title, lang, duration, output_lang, focus, uploader,
       transcripts, created_at, updated_at, deleted_at, mode, status,
       timeout_scale, width, height, file_size, bit_rate, upload_date,
       uploader_id, channel_id, uploader_url)
    VALUES
      (@id, @url, @ts, @title, @lang, @duration, @output_lang, @focus, @uploader,
       @transcripts, @created_at, @updated_at, @deleted_at, @mode, @status,
       @timeout_scale, @width, @height, @file_size, @bit_rate, @upload_date,
       @uploader_id, @channel_id, @uploader_url)
  `);
```

> Note for the reviewer: this same literal is already missing `opencode_session_id` (a pre-existing gap, unrelated to this feature). Don't fix that here — flag it separately if you want it tracked; fixing it isn't part of this task's scope.

- [ ] **Step 6: Add a merge-path regression case to `tests/cli-config-migrate.test.js`**

Add this to `makeDb()`'s CREATE TABLE literal (the test's own fixture helper, near the top of the file) — append `, uploader_id TEXT, channel_id TEXT, uploader_url TEXT` right before the closing `)` of the `tasks` table:

```js
function makeDb(dbPath) {
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const db = new Database(dbPath);
  db.exec(`
    CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY, url TEXT NOT NULL, ts TEXT, title TEXT, lang TEXT,
      duration TEXT, output_lang TEXT DEFAULT 'zh-CN', focus TEXT, uploader TEXT,
      transcripts TEXT DEFAULT '{}', created_at TEXT, updated_at TEXT, deleted_at TEXT,
      mode TEXT DEFAULT 'both', status TEXT, timeout_scale REAL DEFAULT 1,
      width INTEGER, height INTEGER, file_size INTEGER, bit_rate INTEGER, upload_date TEXT,
      uploader_id TEXT, channel_id TEXT, uploader_url TEXT
    );
    CREATE TABLE IF NOT EXISTS steps (
      id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, step_name TEXT,
      status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0,
      error TEXT, started_at TEXT, completed_at TEXT
    );
  `);
  return db;
}
```

Then add a new `check(...)` block right after check #4 (`'merge: task A dir NOT copied when duplicate, task B dir copied'`), before check #5 (`'same path → no-op message'`):

```js
  // 4b. Merge preserves uploader_id/channel_id/uploader_url through the fixed column list
  await check('merge: uploader_id/channel_id/uploader_url survive', async () => {
    const tmp = makeTmp();
    const oldBase = path.join(tmp, 'old');
    const newBase = path.join(tmp, 'new');
    const oldWork = path.join(oldBase, 'work');
    const newWork = path.join(newBase, 'work');

    const oldDb = makeDb(path.join(oldWork, 'database.sqlite'));
    oldDb.prepare(
      'INSERT INTO tasks (id,url,title,uploader_id,channel_id,uploader_url) VALUES (?,?,?,?,?,?)'
    ).run('cccccccccccc', 'https://url-C', 'Task C', '@creator_c', 'UCccccccccccccccccccccccc', 'https://www.youtube.com/@creator_c');
    oldDb.close();
    makeTaskDir(oldWork, 'cccccccccccc', '# C content');

    const restore = stubPromptYes();
    await runSetWorkRoot(oldBase, newBase);
    restore();

    const mergedDb = new Database(path.join(newWork, 'database.sqlite'), { readonly: true });
    const row = mergedDb.prepare('SELECT uploader_id, channel_id, uploader_url FROM tasks WHERE id = ?').get('cccccccccccc');
    mergedDb.close();
    assert.ok(row, 'task C should exist in merged DB');
    assert.strictEqual(row.uploader_id, '@creator_c');
    assert.strictEqual(row.channel_id, 'UCccccccccccccccccccccccc');
    assert.strictEqual(row.uploader_url, 'https://www.youtube.com/@creator_c');

    fs.rmSync(tmp, { recursive: true, force: true });
  });
```

- [ ] **Step 7: Run both tests to confirm they pass**

Run: `node tests/uploader-fields-db.test.js && node tests/cli-config-migrate.test.js`
Expected: both print `PASS` / `all tests passed`, no `✗` lines in the migrate test's output.

- [ ] **Step 8: Commit**

```bash
git add core/orchestrator/db.js cli/commands/config.js tests/uploader-fields-db.test.js tests/cli-config-migrate.test.js
git commit -m "feat(db): add uploader_id/channel_id/uploader_url columns"
```

---

### Task 2: Fix the playlist bug and capture the 3 fields in `fetch_info.sh`

**Files:**
- Modify: `scripts/fetch_info.sh:51` (yt-dlp invocation), `:60-77` (field extraction), `:88-92` (escaping + SQL UPDATE)
- Test: `tests/fetch-info-no-playlist-flag.test.js` (new — mock-based, no network)
- Test: `tests/fetch-step.test.js` (extend — live network, existing convention)

**Interfaces:**
- Consumes: `tasks.uploader_id`/`channel_id`/`uploader_url` columns from Task 1.
- Produces: these 3 columns populated on every future `fetch` step run, and the playlist multi-line-uploader bug fixed for all 8 extracted fields (title/duration/uploader/uploader_id/uploader_url/channel_id/upload_date/lang), since they all now come from a single-document `yt-dlp` invocation.

- [ ] **Step 1: Write the failing mock test for the playlist-bug fix**

This avoids depending on a real playlist URL (unstable, and we have no verified stable playlist URL to hardcode) — it verifies the actual fix (`--no-playlist` flag reaches the `yt-dlp` invocation) via a fake `yt-dlp` binary that records its own argv.

Create `tests/fetch-info-no-playlist-flag.test.js`:

```js
'use strict';
/**
 * Verifies fetch_info.sh invokes yt-dlp with --no-playlist (the fix for the
 * playlist-URL multi-line-uploader bug, spec §2.2). Uses a fake `yt-dlp` on
 * PATH instead of a real playlist URL — deterministic, no network.
 */

const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');
const assert = require('assert');
const { generateId } = require('../core/id');

const ROOT_DIR = path.resolve(__dirname, '..');
const FAKE_URL = 'https://www.youtube.com/playlist?list=FAKE_TEST_LIST';

const MOCK_JSON = JSON.stringify({
  title: 'Mock Video', duration: 42, thumbnail: '', description: '',
  uploader: 'Mock Uploader', upload_date: '20260101', language: 'en',
  uploader_id: '@mock_uploader',
  uploader_url: 'https://www.youtube.com/@mock_uploader',
  channel_id: 'UCmockmockmockmockmockmoc',
});

function runScript(scriptName, args, env) {
  return new Promise((resolve, reject) => {
    const script = path.join(ROOT_DIR, 'scripts', scriptName);
    const proc = spawn('bash', [script, ...args], { cwd: ROOT_DIR, env });
    let stdout = '', stderr = '';
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    proc.on('close', (code) => resolve({ code, stdout, stderr }));
    proc.on('error', reject);
  });
}

async function run() {
  const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'vl-no-playlist-'));
  const binDir = path.join(sandbox, 'bin');
  fs.mkdirSync(binDir);
  const logPath = path.join(sandbox, 'ytdlp-args.log');

  const fakeYtDlp = `#!/usr/bin/env bash\necho "$@" >> "${logPath}"\ncat <<'JSON'\n${MOCK_JSON}\nJSON\n`;
  fs.writeFileSync(path.join(binDir, 'yt-dlp'), fakeYtDlp, { mode: 0o755 });

  process.env.WORK_ROOT = sandbox;
  const id = generateId(FAKE_URL);
  const workDir = path.join(sandbox, 'work', id);
  fs.mkdirSync(path.join(workDir, 'transcript'), { recursive: true });
  fs.mkdirSync(path.join(workDir, 'media'), { recursive: true });
  fs.mkdirSync(path.join(workDir, 'writing'), { recursive: true });

  const env = { ...process.env, PATH: `${binDir}:${process.env.PATH}` };
  const result = await runScript('fetch_info.sh', [FAKE_URL, workDir, id], env);

  if (result.code !== 0) {
    console.error(result.stdout, result.stderr);
    throw new Error(`fetch_info.sh exited with code ${result.code}`);
  }

  const loggedArgs = fs.readFileSync(logPath, 'utf8');
  assert.ok(loggedArgs.includes('--no-playlist'), `expected --no-playlist in yt-dlp invocation, got: ${loggedArgs}`);

  const dbPath = path.join(sandbox, 'work', 'database.sqlite');
  const { execSync } = require('child_process');
  const row = execSync(
    `sqlite3 "${dbPath}" "SELECT uploader_id, channel_id, uploader_url FROM tasks WHERE id='${id}';"`,
    { encoding: 'utf8' }
  ).trim();
  assert.strictEqual(
    row,
    '@mock_uploader|UCmockmockmockmockmockmoc|https://www.youtube.com/@mock_uploader'
  );

  console.log('fetch-info-no-playlist-flag: PASS');
  fs.rmSync(sandbox, { recursive: true, force: true });
}

run().catch((err) => { console.error('fetch-info-no-playlist-flag: FAIL:', err.message); process.exit(1); });
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `node tests/fetch-info-no-playlist-flag.test.js`
Expected: fails — either the `--no-playlist` assertion (flag not present yet) or the SQL SELECT throwing because `uploader_id`/`channel_id`/`uploader_url` aren't populated (columns exist from Task 1, but nothing writes them yet).

- [ ] **Step 3: Fix `scripts/fetch_info.sh`**

Line 51 — add `--no-playlist`:

```bash
video_info=$(yt-dlp $YT_DLP_COOKIE_OPTS --no-playlist --dump-json --no-download "$URL") || true
```

Lines 60-67 — add 3 extraction lines (insert after the existing `uploader=` line, before `upload_date_raw=`):

```bash
title=$(echo "$video_info" | jq -r '.title // "Untitled"' 2>/dev/null)
duration=$(echo "$video_info" | jq -r '.duration // 0' 2>/dev/null)
thumbnail=$(echo "$video_info" | jq -r '.thumbnail // ""' 2>/dev/null)
description=$(echo "$video_info" | jq -r '.description // ""' 2>/dev/null)
uploader=$(echo "$video_info" | jq -r '.uploader // ""' 2>/dev/null)
uploader_id=$(echo "$video_info" | jq -r '.uploader_id // ""' 2>/dev/null)
uploader_url=$(echo "$video_info" | jq -r '.uploader_url // ""' 2>/dev/null)
channel_id=$(echo "$video_info" | jq -r '.channel_id // ""' 2>/dev/null)
upload_date_raw=$(echo "$video_info" | jq -r '.upload_date // ""' 2>/dev/null)
```

Lines 88-92 — add 3 escape vars and extend the SQL UPDATE:

```bash
_title_esc=$(echo "$title" | sed "s/'/''/g")
_duration_esc=$(echo "$duration" | sed "s/'/''/g")
_uploader_esc=$(echo "$uploader" | sed "s/'/''/g")
_uploader_id_esc=$(echo "$uploader_id" | sed "s/'/''/g")
_uploader_url_esc=$(echo "$uploader_url" | sed "s/'/''/g")
_channel_id_esc=$(echo "$channel_id" | sed "s/'/''/g")
_upload_date_esc=$(echo "$upload_date" | sed "s/'/''/g")
sqlite3 "$DB_PATH" "UPDATE tasks SET title = '$_title_esc', duration = '$_duration_esc', uploader = '$_uploader_esc', uploader_id = '$_uploader_id_esc', uploader_url = '$_uploader_url_esc', channel_id = '$_channel_id_esc', upload_date = '$_upload_date_esc', lang = '$lang', updated_at = datetime('now') WHERE id = '$ID';"
```

- [ ] **Step 4: Run the mock test again to confirm it passes**

Run: `node tests/fetch-info-no-playlist-flag.test.js`
Expected: `fetch-info-no-playlist-flag: PASS`

- [ ] **Step 5: Extend the existing live test with the 3 new fields**

In `tests/fetch-step.test.js`, after the existing `upload_date` block (ends around line 87, right before `console.log('[fetch-step.test] PASS');`), add:

```js
    const uploaderIdRow = execSync(`sqlite3 "${dbPath}" "SELECT uploader_id FROM tasks WHERE id='${id}';"`, { encoding: 'utf8' }).trim();
    if (uploaderIdRow.includes('\n')) {
      throw new Error(`uploader_id contains embedded newline (playlist-bug regression): ${JSON.stringify(uploaderIdRow)}`);
    }
    console.log('[fetch-step.test] DB uploader_id:', uploaderIdRow || '(empty)');

    const channelIdRow = execSync(`sqlite3 "${dbPath}" "SELECT channel_id FROM tasks WHERE id='${id}';"`, { encoding: 'utf8' }).trim();
    console.log('[fetch-step.test] DB channel_id:', channelIdRow || '(empty)');

    const uploaderUrlRow = execSync(`sqlite3 "${dbPath}" "SELECT uploader_url FROM tasks WHERE id='${id}';"`, { encoding: 'utf8' }).trim();
    console.log('[fetch-step.test] DB uploader_url:', uploaderUrlRow || '(empty)');
```

(This test hits real YouTube via a stable canonical test video already used by this file — no new URL introduced.)

- [ ] **Step 6: Run the live test to confirm it passes**

Run: `node tests/fetch-step.test.js`
Expected: `[fetch-step.test] PASS`, with `uploader_id`/`channel_id`/`uploader_url` printed as non-empty single-line values (this specific test video is a real YouTube upload, so these should resolve).

- [ ] **Step 7: Commit**

```bash
git add scripts/fetch_info.sh tests/fetch-info-no-playlist-flag.test.js tests/fetch-step.test.js
git commit -m "fix(fetch): add --no-playlist, capture uploader_id/channel_id/uploader_url"
```

---

### Task 3: `buildTaskMeta` outputs the 3 new fields plus the unified-store contract fields

**Files:**
- Modify: `core/orchestrator/task-meta.js:14-37` (`buildTaskMeta`)
- Test: `tests/orchestrator-task-meta.test.js` (extend existing blocks)

**Interfaces:**
- Consumes: `row.uploader_id`/`row.channel_id`/`row.uploader_url` (from Task 1's columns, populated by Task 2's fetch step).
- Produces: `meta.json` now contains, in addition to its existing 21 fields: `uploader_id`, `channel_id`, `uploader_url`, `source_url` (= `row.url`, the unified-store contract name), `fetched_at` (= first 10 chars of `row.ts || row.created_at`, `YYYY-MM-DD`). This makes `meta.json` self-sufficient per the unified-store contract (`docs/superpowers/specs/2026-09-01-unified-store-design.md` §3.2) without needing `learn-video`'s `archive.py` to write anything.

- [ ] **Step 1: Write the failing test**

In `tests/orchestrator-task-meta.test.js`, extend the first test block (the one with `row = { id: 'abc123def456', ... }`) — add these fields to the `row` object:

```js
        uploader_id: '@alejandro_ao',
        channel_id: 'UC1oXUA7qgs0GZc_yk46K2OQ',
        uploader_url: 'https://www.youtube.com/@alejandro_ao',
```

And add these assertions after the existing `assert.strictEqual(meta.bit_rate, 500000);` line:

```js
      assert.strictEqual(meta.uploader_id, '@alejandro_ao');
      assert.strictEqual(meta.channel_id, 'UC1oXUA7qgs0GZc_yk46K2OQ');
      assert.strictEqual(meta.uploader_url, 'https://www.youtube.com/@alejandro_ao');
      assert.strictEqual(meta.source_url, row.url, 'source_url should mirror url (unified-store contract field)');
      assert.strictEqual(meta.fetched_at, '2026-07-01', 'fetched_at should be ts truncated to YYYY-MM-DD');
```

And extend the second block (`row = { id: 'zzz999', url: '', ts: null, created_at: '2026-01-01T00:00:00.000Z' }`) with:

```js
      assert.strictEqual(meta.uploader_id, '', 'missing uploader_id defaults to empty string');
      assert.strictEqual(meta.source_url, '', 'source_url defaults to empty string when url is empty');
      assert.strictEqual(meta.fetched_at, '2026-01-01', 'fetched_at falls back to created_at when ts is null');
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `node tests/orchestrator-task-meta.test.js`
Expected: `AssertionError` — `meta.uploader_id` is `undefined`, not `'@alejandro_ao'`.

- [ ] **Step 3: Update `buildTaskMeta`**

```js
function buildTaskMeta(row, derived) {
  return {
    id: row.id,
    url: row.url || '',
    ts: row.ts || row.created_at || '',
    title: row.title || '',
    uploader: row.uploader || '',
    uploader_id: row.uploader_id || '',
    uploader_url: row.uploader_url || '',
    channel_id: row.channel_id || '',
    upload_date: row.upload_date || '',
    duration: row.duration != null ? String(row.duration) : '',
    lang: row.lang || '',
    output_lang: row.output_lang || 'zh-CN',
    focus: row.focus || '',
    mode: normalizeMode(row.mode),
    opencode_session_id: row.opencode_session_id ?? null,
    width: row.width ?? null,
    height: row.height ?? null,
    file_size: row.file_size ?? null,
    bit_rate: row.bit_rate ?? null,
    download_status: derived.download_status,
    transcript_done: !!derived.transcript_done,
    article_done: !!derived.article_done,
    summary_done: !!derived.summary_done,
    // Unified-store contract fields (docs/superpowers/specs/2026-09-01-unified-store-design.md §3.2).
    // Kept alongside vdl's own field names (url/ts), not replacing them.
    source_url: row.url || '',
    fetched_at: (row.ts || row.created_at || '').slice(0, 10),
  };
}
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `node tests/orchestrator-task-meta.test.js`
Expected: `orchestrator-task-meta.test.js: PASS`

- [ ] **Step 5: Run the related finalize-meta test to check for regressions**

Run: `node tests/orchestrator-finalize-meta.test.js`
Expected: `PASS` (this test exercises `finalizeTaskMeta` → `writeTaskMetaJson` → `buildTaskMeta`; it should keep passing since no existing field was removed or renamed, only added).

- [ ] **Step 6: Commit**

```bash
git add core/orchestrator/task-meta.js tests/orchestrator-task-meta.test.js
git commit -m "feat(meta): buildTaskMeta emits uploader_id/channel_id/uploader_url + contract fields"
```

---

### Task 4: Backfill the 67 historical YouTube tasks (operational — the irreversible step)

**Files:**
- Create: `scripts/backfill-uploader-fields.sh` (new, committed — this is a reusable, re-runnable tool, not a throwaway one-liner, because spec §4.4 requires a success/failure list rather than silent skipping)

**Interfaces:**
- Consumes: `vdl rerun <id> fetch --reset step` (existing CLI, confirmed by research to re-invoke `fetch_info.sh` without cascading a reset to transcript/article/summary steps) and `node scripts/backfill_meta_json.js` (existing, unmodified — it already iterates disk directories, not DB rows, which is required per spec §4.2 pitfall #4: 243 DB rows exist but only 68 are real, the rest are `example.com` test fixtures).
- Produces: refreshed `uploader_id`/`channel_id`/`uploader_url`/`source_url`/`fetched_at` in all 68 on-disk `meta.json` files.

- [ ] **Step 1: Back up the current `meta.json` files (mandatory, irreversible operation ahead)**

```bash
WORK_DIR="$(node -e "console.log(require('./core/paths').getWorkRoot(process.cwd()))")"
BACKUP_DIR="$HOME/vdl-meta-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
for d in "$WORK_DIR"/*/meta.json; do
  [ -f "$d" ] || continue
  task_id="$(basename "$(dirname "$d")")"
  cp "$d" "$BACKUP_DIR/$task_id.meta.json"
done
echo "Backed up $(ls "$BACKUP_DIR" | wc -l) meta.json files to $BACKUP_DIR"
```

Verify: `ls "$BACKUP_DIR" | wc -l` prints `68` (or whatever the current real count is — cross-check against `ls "$WORK_DIR" | grep -E '^[0-9a-f]{12}$' | wc -l` first if unsure, since the DB has 243 rows but only ~68 are real per spec §4.2 pitfall #4).

- [ ] **Step 2: Write `scripts/backfill-uploader-fields.sh`**

```bash
#!/usr/bin/env bash
# scripts/backfill-uploader-fields.sh — one-time: re-fetch uploader_id/
# channel_id/uploader_url for every existing YouTube task by re-running the
# fetch step, then regenerate every meta.json from the refreshed DB.
#
# Prereqs:
#   1. `npm run agent:serve` running in another terminal — `vdl rerun` talks
#      to it over HTTP, it does not start it.
#   2. meta.json backed up first (see Task 4 Step 1 of the plan this script
#      belongs to) — backfill_meta_json.js overwrites all 68 files.
#
# Usage: bash scripts/backfill-uploader-fields.sh
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK_DIR="$(node -e "console.log(require('$ROOT_DIR/core/paths').getWorkRoot('$ROOT_DIR'))")"
DB_PATH="$WORK_DIR/database.sqlite"

ok=()
fail=()
skipped_not_youtube=0

for task_dir in "$WORK_DIR"/*/; do
  id="$(basename "$task_dir")"
  [[ "$id" =~ ^[0-9a-f]{12}$ ]] || continue
  [[ -f "${task_dir}meta.json" ]] || continue  # only real, already-archived entities

  url="$(sqlite3 "$DB_PATH" "SELECT url FROM tasks WHERE id = '$id';")"
  if [[ ! "$url" =~ youtube\.com|youtu\.be ]]; then
    skipped_not_youtube=$((skipped_not_youtube + 1))
    continue
  fi

  echo "== $id ($url) =="
  if vdl rerun "$id" fetch --reset step; then
    ok+=("$id")
  else
    fail+=("$id")
  fi
done

echo ""
echo "成功 ${#ok[@]} 个: ${ok[*]:-（无）}"
echo "失败 ${#fail[@]} 个: ${fail[*]:-（无）}"
echo "跳过（非 YouTube）: $skipped_not_youtube 个"

if [[ ${#fail[@]} -gt 0 ]]; then
  exit 1
fi
```

```bash
chmod +x scripts/backfill-uploader-fields.sh
git add scripts/backfill-uploader-fields.sh
git commit -m "feat(backfill): add one-time uploader-fields backfill script"
```

- [ ] **Step 3: Start the agent server** (needed for `vdl rerun`'s HTTP calls)

Run: `npm run agent:serve` in a separate terminal/background process. Confirm it's listening before proceeding (check its log for a "listening" message, or `curl localhost:<port>/health` if such an endpoint exists — check `services/http-server/index.js` for the actual port/health path if unsure).

- [ ] **Step 4: Run the backfill script against the real 67 tasks**

Run: `bash scripts/backfill-uploader-fields.sh 2>&1 | tee /tmp/backfill-uploader-fields.log`

Expected: a `成功 NN 个` / `失败 0 个` summary. If any failures are listed, investigate each one individually (video may be private/deleted/region-locked — this is expected and acceptable per spec §4.3, those tasks will simply lack `uploader_id` and land in the index's `unresolved` bucket later) — do not silently retry-and-ignore; record which ones failed and why in this plan's checklist notes before moving on.

- [ ] **Step 5: Regenerate all `meta.json` files from the now-updated DB**

Run: `node scripts/backfill_meta_json.js`

Expected output ends with `Done. updated=68  notCompleted=X  noRow=Y` (or whatever the real completed count is — cross-check `updated` equals the number of real task directories with `meta.json`, per spec §4.2 pitfall #2: some tasks may be stuck outside the `isTaskCompleted` threshold and won't get updated by this pass — count how many, this is the "开工前必须先查清的事" item #... already resolved as informational in the spec, but the actual count for *this* run should be recorded here).

- [ ] **Step 6: Verify against the design spec's acceptance criterion #3**

```bash
python3 - "$WORK_DIR" <<'PY'
import json, sys, glob, os
work = sys.argv[1]
total = 0
have_uploader_id = 0
missing = []
for p in glob.glob(os.path.join(work, "*", "meta.json")):
    total += 1
    d = json.load(open(p))
    if d.get("uploader_id"):
        have_uploader_id += 1
    else:
        missing.append(os.path.basename(os.path.dirname(p)))
print(f"total meta.json: {total}")
print(f"with uploader_id: {have_uploader_id}")
print(f"without uploader_id ({len(missing)}): {missing}")
PY
```

Expected: `total` matches the pre-backfill count (no task disappeared — acceptance criterion #3's "没有任何一个任务从索引中消失" is actually verified at the *index-build* stage in the harveyz-skill plan, but this step confirms no `meta.json` was lost here, which is the precondition for that). Tasks in the `without uploader_id` list are expected to be non-accessible videos or Bilibili sources (spec §4.3) — they'll land in `unresolved` once the index is built; this is normal, not a failure.

- [ ] **Step 7: Record the actual backfill numbers in the design spec**

Update `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` §6 (validation criteria) or add a short note near the acceptance criteria recording: total tasks backfilled, how many got `uploader_id`, how many didn't and why (this directly informs the harveyz-skill plan's `build_creator_index.py` testing — the `unresolved` count should match what you found here). This edit happens in the `harveyz-skill` worktree, not this repo — do it as part of starting the next plan, not here.

- [ ] **Step 8: Merge this branch**

```bash
git checkout staging
git merge --no-ff feature/creator-index-fields
```

(Only do this once the harveyz-skill plan's `archive.py` change has been reviewed against real backfilled `meta.json` — or merge now if the design's locked sequencing (§4.1) means this repo's work is genuinely done and self-contained. Use judgment: if the two repos are being executed back-to-back, merging now is fine since this repo's tests all pass independently of the other repos.)
