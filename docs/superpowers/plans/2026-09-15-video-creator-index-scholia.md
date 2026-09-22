# scholia: creator source module + /creator/:key route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This plan targets the `scholia` repo** (`~/Projects/scholia`), NOT the `harveyz-skill` worktree this file lives in. Before Task 1: `cd ~/Projects/scholia`, confirm `git rev-parse --abbrev-ref HEAD` is `master`, then `git checkout -b feature/creator-index`. This repo's `CLAUDE.md`/`AGENTS.md` has no branch/worktree convention documented — a plain feature branch in the existing working tree is correct, same as the handoff doc's instruction. Never commit to `master` directly.
>
> **Sequencing note:** This is step 3 of 3. Requires the harveyz-skill plan's Task 2 (`build_creator_index.py`) to exist and have been run at least once against real data so `<knowledgeRoot>/videos/creators.json` exists — otherwise this plan's manual smoke test (Task 4) has nothing to read. The automated tests in Tasks 1-3 use synthetic fixtures and don't depend on this.

**Goal:** Add a read-only `/api/creator/:key` endpoint that joins `<knowledgeRoot>/videos/creators.json` (built by `learn-video`) against the roster's `registry.json` (owned by `manage-creators`) to answer "is this creator someone I'm watching, and what have I read from them" — computed live on every request, never cached or stored, so `registry.json` changes take effect without any index rebuild (spec §3.3).

**Architecture:** One new read-only server module (`server/creator-source.js`, following the existing `server/x-source.js` pattern exactly: plain exported async functions, no class, no shared state), one new route, and matching frontend plumbing (API client method, React Query hook, route component) mirrored from the existing X-timeline detail page. Two small additions to `server/video-source.js`'s existing field allowlists and the frontend's `Task` type surface `uploader_id` so a video's detail page can link to its creator page — spec §1.4 explicitly names `video-source.js:36-45`'s fixed field list as a change this feature cannot skip.

**Tech Stack:** Koa + `@koa/router` (server), React + React Router + `@tanstack/react-query` (web), homegrown `node:assert/strict`-based test files (server), Vitest (web).

**Spec:** `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` (implements §1.4 row 3, §3.3, §6 criteria 5 and 6).

## Global Constraints

- **`registry.json` is read-only from this repo's perspective.** Never write to it — that's `manage-creators`'s job (spec §1.5).
- **Nothing here is cached.** `watched`/`creator_id` are computed fresh on every `/api/creator/:key` request by reading `registry.json` off disk — this is what makes criterion 5 ("`add` 一个人，不重跑 `build`，`watched` 立刻变真") true. Do not introduce an in-memory cache or a startup-time snapshot of the registry.
- **Handle normalization must match `learn-video`'s exactly**: strip a leading `@`, lowercase, trim. This was verified case-insensitive against Google's own YouTube handles documentation (spec §7.1) — don't second-guess it here.
- **Merged creators must resolve.** A registry `merge` consolidates two roster records' `channels[]` into the surviving record — resolving a request by either the old or the new YouTube handle key must return the union of both handles' videos (criterion 6). Do not implement a lookup that only checks the exact key against the exact matching channel and stops there.
- **Test convention — server side:** no framework. Plain `node:assert/strict`, a local `async function test(name, fn)` counter/reporter (see any `tests/*.test.js` for the exact shape), run individually via `node tests/<file>.test.js` or all together via `npm test` (a chained `&&` list in `package.json`). New test files must be added to that chain.
- **Test convention — web side:** `vitest run` (`web/package.json`'s `"test"` script). Config lives inline in `web/vite.config.ts` (`environment: 'jsdom'`).
- **No new config keys.** `cli/config.js`'s `readConfig()` stays untouched — the creators index path and the roster registry path are both derived/hardcoded the same way `store_config.py` hardcodes `~/.hskill/config.json` elsewhere in this cross-repo feature. Don't add a `CREATORS_INDEX_PATH` or `ROSTER_DIR` setting.
- **Scope discipline:** this plan does NOT touch the video list card (`components/task-card.tsx`) — nesting a creator link inside its existing whole-card `<Link>` would produce invalid nested-interactive-element HTML. The only new UI entry point to a creator page is a header link on the video detail page (`routes/tasks.$id.tsx`), which is not itself a link.

---

### Task 1: Surface `uploader_id` through `video-source.js` and the frontend `Task` type

**Files:**
- Modify: `server/video-source.js:34-46` (`listVideos`), `server/video-source.js:61-72` (`getVideoTask`)
- Modify: `web/src/lib/api.ts` (`BackendListTask`, `BackendTask.meta`, `Task` interfaces; `normalizeListTask`, `normalizeTask`)
- Modify: `web/src/routes/tasks.$id.tsx` (header — add a link to the creator page when present)
- Test: `tests/video-source.test.js` (extend)

**Interfaces:**
- Produces: `Task.uploader_id?: string` on both the list and detail API responses, carrying vdl's raw `@handle` value straight through (normalization to the index `key` happens client-side at the one call site that needs it, Step 5 below — no shared normalization module is introduced for a single use site).

- [ ] **Step 1: Write the failing server-side test**

In `tests/video-source.test.js`, add `uploader_id: '@chan_a'` to `task1`'s fixture meta object (line 22) and add these two new test blocks right after the existing `'getVideoTask returns BackendTask shape'` test:

```js
  await test('listVideos includes uploader_id', async () => {
    const videos = await listVideos(workDir);
    const v1 = videos.find((v) => v.id === task1);
    assert.equal(v1.uploader_id, '@chan_a');
  });

  await test('getVideoTask includes uploader_id in meta', async () => {
    const t = await getVideoTask(task1, workDir);
    assert.equal(t.meta.uploader_id, '@chan_a');
  });
```

- [ ] **Step 2: Run to confirm it fails**

Run: `node tests/video-source.test.js`
Expected: two `✗` lines — `v1.uploader_id` and `t.meta.uploader_id` are both `undefined`.

- [ ] **Step 3: Add `uploader_id` to both allowlists in `server/video-source.js`**

In `listVideos` (around line 34-46), add one line to the pushed object:

```js
      results.push({
        id: e.name,
        url: meta.url || '',
        title: meta.title,
        uploader: meta.uploader,
        uploader_id: meta.uploader_id,
        upload_date: meta.upload_date,
        duration: meta.duration != null ? String(meta.duration) : undefined,
        mode: meta.mode,
        output_lang: meta.output_lang,
        created_at: meta.ts || meta.created_at,
        updated_at: meta.ts || meta.created_at,
        updatedAt: occurrenceDate(meta, stat.mtimeMs),
      });
```

In `getVideoTask` (around line 61-72), add one line to the returned `meta` object:

```js
    meta: {
      id: taskId,
      url: meta.url || '',
      title: meta.title,
      uploader: meta.uploader,
      uploader_id: meta.uploader_id,
      upload_date: meta.upload_date,
      duration: meta.duration != null ? String(meta.duration) : undefined,
      mode: meta.mode || 'media',
      output_lang: meta.output_lang,
      ts,
      created_at: ts,
    },
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `node tests/video-source.test.js`
Expected: all tests pass, ending in `N passed, 0 failed`.

- [ ] **Step 5: Thread `uploader_id` through the frontend API layer**

In `web/src/lib/api.ts`:

Add `uploader_id?: string;` to the `Task` interface (near `uploader?: string;`, line 30), to `BackendListTask` (line 63), and to `BackendTask.meta`'s inline type (line 74).

Add `uploader_id: t.uploader_id,` to `normalizeListTask` (near line 108) and `uploader_id: m.uploader_id,` to `normalizeTask` (near line 132).

- [ ] **Step 6: Add a creator link to the video detail page header**

In `web/src/routes/tasks.$id.tsx`, in the header's right-side button group (right after the `{mediaKind && <ModeSwitcher />}` line, before the gantt `Link`), add:

```tsx
          {task.uploader_id && (
            <Link
              to={`/creator/${task.uploader_id.replace(/^@/, '').toLowerCase()}`}
              title={`查看${task.uploader ? ` ${task.uploader} ` : ''}的其他视频`}
              className="text-sm px-2 py-1 rounded hover:opacity-70 transition-opacity"
              style={{ color: 'var(--text-tertiary)' }}
            >
              {task.uploader ?? '创作者'}
            </Link>
          )}
```

(`Link` is already imported in this file for the gantt link — no new import needed.)

- [ ] **Step 7: Commit**

```bash
git add server/video-source.js web/src/lib/api.ts web/src/routes/tasks.$id.tsx tests/video-source.test.js
git commit -m "feat(video): surface uploader_id through the API and video detail page"
```

---

### Task 2: `server/creator-source.js` + `GET /api/creator/:key`

**Files:**
- Create: `server/creator-source.js`
- Modify: `server/index.js` (imports near line 13, route registration near line 160)
- Test: `tests/creator-source.test.js` (new)
- Modify: `package.json:22` (add the new test file to the `test` script's chain)

**Interfaces:**
- Produces: `getCreator(key: string, workDir: string) -> Promise<CreatorDetail | null>`, `normalizeHandle(handle: string) -> string`. `CreatorDetail` shape: `{ key, display_name, channel_id, uploader_url, videos: [{task_id, title, upload_date, duration}], watched: boolean, creator_id: string | null }`.
- Consumes: `<knowledgeRoot>/videos/creators.json` (the sibling of `workDir`, i.e. `path.join(path.dirname(workDir), 'creators.json')`) and `~/.hskill/roster/config.json` → `DATA_DIR/registry.json`.

- [ ] **Step 1: Write the failing test**

Create `tests/creator-source.test.js`:

```js
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

let passed = 0; let failed = 0;
async function test(name, fn) {
  try { await fn(); console.log(`  ✓ ${name}`); passed++; }
  catch (e) { console.error(`  ✗ ${name}: ${e.message}`); failed++; }
}

(async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'scholia-cs-'));
  const knowledgeRoot = path.join(tmp, 'knowledge');
  const workDir = path.join(knowledgeRoot, 'videos', 'work');
  fs.mkdirSync(workDir, { recursive: true });

  const rosterHome = path.join(tmp, 'home');
  fs.mkdirSync(path.join(rosterHome, '.hskill', 'roster'), { recursive: true });
  process.env.HOME = rosterHome; // creator-source.js resolves ~/.hskill/roster via os.homedir()

  function writeCreatorsIndex(creators) {
    fs.writeFileSync(
      path.join(knowledgeRoot, 'videos', 'creators.json'),
      JSON.stringify({ schema_version: 1, built_at: 'x', scanned: { entities: 0 }, creators, unresolved: [] })
    );
  }

  function writeRegistry(creators) {
    fs.writeFileSync(
      path.join(rosterHome, '.hskill', 'roster', 'registry.json'),
      JSON.stringify({ schema_version: 1, creators })
    );
    fs.writeFileSync(
      path.join(rosterHome, '.hskill', 'roster', 'config.json'),
      JSON.stringify({ DATA_DIR: path.join(rosterHome, '.hskill', 'roster') })
    );
  }

  const { getCreator, normalizeHandle } = require('../server/creator-source');

  await test('normalizeHandle strips @ and lowercases', () => {
    assert.equal(normalizeHandle('@Alejandro_AO'), 'alejandro_ao');
    assert.equal(normalizeHandle('alejandro_ao'), 'alejandro_ao');
  });

  await test('getCreator returns null when the key is not in the index', async () => {
    writeCreatorsIndex([]);
    writeRegistry([]);
    const result = await getCreator('nobody', workDir);
    assert.equal(result, null);
  });

  await test('getCreator returns watched=false when not in the registry', async () => {
    writeCreatorsIndex([
      { key: 'alejandro_ao', display_name: 'Alejandro AO', channel_id: 'UC1', uploader_url: 'https://youtube.com/@alejandro_ao',
        videos: [{ task_id: 't1', title: 'V1', upload_date: '2026-06-01', duration: '120' }] },
    ]);
    writeRegistry([]);
    const result = await getCreator('alejandro_ao', workDir);
    assert.equal(result.watched, false);
    assert.equal(result.creator_id, null);
    assert.equal(result.videos.length, 1);
  });

  await test('getCreator returns watched=true immediately after a registry add (no rebuild needed)', async () => {
    writeCreatorsIndex([
      { key: 'alejandro_ao', display_name: 'Alejandro AO', channel_id: 'UC1', uploader_url: 'https://youtube.com/@alejandro_ao',
        videos: [{ task_id: 't1', title: 'V1', upload_date: '2026-06-01', duration: '120' }] },
    ]);
    writeRegistry([
      { id: 'alejandro_ao', display_name: 'Alejandro AO', aliases: [], placeholder: false, added_at: '2026-09-15',
        channels: [{ platform: 'youtube', handle: '@alejandro_ao', url: 'https://youtube.com/@alejandro_ao' }] },
    ]);
    const result = await getCreator('alejandro_ao', workDir);
    assert.equal(result.watched, true);
    assert.equal(result.creator_id, 'alejandro_ao');
  });

  await test('getCreator folds a merged handle\'s videos into the surviving id (criterion #6)', async () => {
    // Two separate creators.json entries — same person, two different YouTube
    // handles over time — get merged in the registry into one record whose
    // channels[] lists both.
    writeCreatorsIndex([
      { key: 'old_handle', display_name: 'Old Name', channel_id: 'UC_OLD', uploader_url: 'https://youtube.com/@old_handle',
        videos: [{ task_id: 't1', title: 'Old Video', upload_date: '2025-01-01', duration: '100' }] },
      { key: 'new_handle', display_name: 'New Name', channel_id: 'UC_NEW', uploader_url: 'https://youtube.com/@new_handle',
        videos: [{ task_id: 't2', title: 'New Video', upload_date: '2026-01-01', duration: '200' }] },
    ]);
    writeRegistry([
      { id: 'new_handle', display_name: 'New Name', aliases: ['old_handle'], placeholder: false, added_at: '2026-09-15',
        channels: [
          { platform: 'youtube', handle: '@new_handle', url: 'https://youtube.com/@new_handle' },
          { platform: 'youtube', handle: '@old_handle', url: 'https://youtube.com/@old_handle' },
        ] },
    ]);

    const viaSurvivingKey = await getCreator('new_handle', workDir);
    assert.equal(viaSurvivingKey.watched, true);
    assert.equal(viaSurvivingKey.creator_id, 'new_handle');
    assert.deepEqual(new Set(viaSurvivingKey.videos.map((v) => v.task_id)), new Set(['t1', 't2']));

    const viaOldKey = await getCreator('old_handle', workDir);
    assert.equal(viaOldKey.watched, true);
    assert.equal(viaOldKey.creator_id, 'new_handle');
    assert.deepEqual(new Set(viaOldKey.videos.map((v) => v.task_id)), new Set(['t1', 't2']));
  });

  console.log(`\n${passed} passed, ${failed} failed`);
  if (failed > 0) process.exit(1);
})();
```

- [ ] **Step 2: Run to confirm it fails**

Run: `node tests/creator-source.test.js`
Expected: `Error: Cannot find module '../server/creator-source'`.

- [ ] **Step 3: Write `server/creator-source.js`**

```js
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

function normalizeHandle(handle) {
  return String(handle || '').replace(/^@/, '').trim().toLowerCase();
}

function readJsonSync(filePath) {
  try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
  catch { return null; }
}

function creatorsIndexPath(workDir) {
  // workDir = <knowledgeRoot>/videos/work; creators.json is its sibling
  // (docs/superpowers/specs/2026-09-15-video-creator-index-design.md §2.4).
  return path.join(path.dirname(workDir), 'creators.json');
}

function registryPath() {
  const rosterConfig = readJsonSync(path.join(os.homedir(), '.hskill', 'roster', 'config.json'));
  const dataDir = (rosterConfig && rosterConfig.DATA_DIR) || path.join(os.homedir(), '.hskill', 'roster');
  return path.join(dataDir, 'registry.json');
}

// Finds the registry record (if any) whose YouTube channels include this
// normalized handle, and returns every other YouTube handle that same
// record owns — covers a merged-handle lookup either way (criterion #6).
function resolveRegistryMatch(key) {
  const registry = readJsonSync(registryPath());
  if (!registry || !Array.isArray(registry.creators)) return null;
  for (const creator of registry.creators) {
    const youtubeHandles = (creator.channels || [])
      .filter((c) => c.platform === 'youtube')
      .map((c) => normalizeHandle(c.handle));
    if (youtubeHandles.includes(key)) {
      return { creatorId: creator.id, youtubeHandles };
    }
  }
  return null;
}

async function getCreator(key, workDir) {
  const index = readJsonSync(creatorsIndexPath(workDir));
  if (!index || !Array.isArray(index.creators)) return null;

  const byKey = new Map(index.creators.map((c) => [c.key, c]));
  const primary = byKey.get(key);
  if (!primary) return null;

  const match = resolveRegistryMatch(key);
  let videos = primary.videos.slice();
  let channelId = primary.channel_id;
  let uploaderUrl = primary.uploader_url;

  if (match) {
    for (const handle of match.youtubeHandles) {
      if (handle === key) continue;
      const other = byKey.get(handle);
      if (!other) continue;
      videos = videos.concat(other.videos);
      if (!channelId) channelId = other.channel_id;
      if (!uploaderUrl) uploaderUrl = other.uploader_url;
    }
  }

  return {
    key,
    display_name: primary.display_name,
    channel_id: channelId,
    uploader_url: uploaderUrl,
    videos,
    watched: Boolean(match),
    creator_id: match ? match.creatorId : null,
  };
}

module.exports = { getCreator, normalizeHandle };
```

- [ ] **Step 4: Run the test again to confirm it passes**

Run: `node tests/creator-source.test.js`
Expected: `5 passed, 0 failed`.

- [ ] **Step 5: Wire the route into `server/index.js`**

Add the import near the other source-module imports (line 13, next to `x-source`):

```js
const { getCreator } = require('./creator-source');
```

Add the route right after the existing `router.get('/x-timelines/:handle', ...)` block (around line 160):

```js
  // Get a creator's aggregated video list + roster watch status
  router.get('/creator/:key', async (ctx) => {
    const { key } = ctx.params;
    if (!WORK_DIR) { ctx.status = 404; ctx.body = { error: 'not found' }; return; }
    const creator = await getCreator(key, WORK_DIR);
    if (!creator) { ctx.status = 404; ctx.body = { error: 'not found' }; return; }
    ctx.body = creator;
  });
```

- [ ] **Step 6: Add the new test file to `package.json`'s test chain**

In `package.json` line 22, insert `node tests/creator-source.test.js` right after `node tests/x-source.test.js`:

```json
"test": "node tests/config.test.js && node tests/video-source.test.js && node tests/article-source.test.js && node tests/x-source.test.js && node tests/creator-source.test.js && node tests/server.test.js && node tests/integration.test.js",
```

- [ ] **Step 7: Run the full server test suite to check for regressions**

Run: `npm test`
Expected: all chained test files pass.

- [ ] **Step 8: Commit**

```bash
git add server/creator-source.js server/index.js tests/creator-source.test.js package.json
git commit -m "feat(server): add GET /api/creator/:key"
```

---

### Task 3: Frontend creator detail page

**Files:**
- Modify: `web/src/lib/api.ts` (new `CreatorVideo`/`CreatorDetail` interfaces, `getCreator` client method)
- Create: `web/src/hooks/use-creator.ts`
- Create: `web/src/routes/creator.$key.tsx`
- Modify: `web/src/main.tsx` (import + route registration)

**Interfaces:**
- Consumes: `GET /api/creator/:key` from Task 2.
- Produces: a page at `/creator/:key` rendering the creator's display name, a "关注中" / not-watched badge, and their video list (each linking to `/tasks/:task_id`).

- [ ] **Step 1: Add the API types and client method**

In `web/src/lib/api.ts`, add these interfaces near `XTimeline` (around line 203):

```ts
export interface CreatorVideo {
  task_id: string;
  title: string;
  upload_date: string;
  duration: string;
}

export interface CreatorDetail {
  key: string;
  display_name: string;
  channel_id: string;
  uploader_url: string;
  videos: CreatorVideo[];
  watched: boolean;
  creator_id: string | null;
}
```

Add the client method right after `getXTimeline` (around line 269):

```ts
  getCreator: (key: string) => request<CreatorDetail>(`/api/creator/${key}`),
```

- [ ] **Step 2: Create the data-fetching hook**

Create `web/src/hooks/use-creator.ts`, mirroring `use-x-timelines.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useCreator(key: string | undefined) {
  return useQuery({
    queryKey: ['creator', key],
    queryFn: () => api.getCreator(key!),
    enabled: Boolean(key),
    staleTime: 30_000,
  });
}
```

- [ ] **Step 3: Create the route component**

Create `web/src/routes/creator.$key.tsx`, mirroring `x.$handle.tsx`'s structure:

```tsx
import { Link, useParams, useNavigate } from 'react-router';
import { useCreator } from '@/hooks/use-creator';
import { Pill } from '@/components/pill';

export default function CreatorDetail() {
  const { key = '' } = useParams();
  const navigate = useNavigate();
  const goBack = () => {
    if (window.history.state?.idx > 0) navigate(-1);
    else navigate('/videos');
  };
  const { data: creator, isLoading } = useCreator(key);

  if (isLoading) return <div className="p-8 text-sm" style={{ color: 'var(--text-tertiary)' }}>加载中…</div>;
  if (!creator) return <div className="p-8 text-sm" style={{ color: 'var(--status-err)' }}>未找到该创作者</div>;

  return (
    <div className="h-screen flex flex-col">
      <header className="h-12 flex items-center gap-4 px-5 border-b flex-shrink-0"
              style={{ borderColor: 'var(--border-subtle)' }}>
        <button type="button" onClick={goBack} className="text-sm" style={{ color: 'var(--text-tertiary)' }}>←</button>
        <h1 className="text-sm font-medium">{creator.display_name}</h1>
        <Pill variant={creator.watched ? 'tag' : 'default'}>
          {creator.watched ? '关注中' : '未关注'}
        </Pill>
      </header>
      <div className="flex-1 overflow-y-auto" style={{ background: 'var(--bg-canvas)' }}>
        <div className="mx-auto py-7 pb-10" style={{ maxWidth: 640 }}>
          {creator.uploader_url && (
            <a
              href={creator.uploader_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs mb-4 inline-block"
              style={{ color: 'var(--text-tertiary)' }}
            >
              {creator.uploader_url}
            </a>
          )}
          {creator.videos.length === 0 ? (
            <div className="text-sm py-16 text-center" style={{ color: 'var(--text-tertiary)' }}>暂无深读视频</div>
          ) : (
            <ul className="flex flex-col gap-2">
              {creator.videos.map((v) => (
                <li key={v.task_id}>
                  <Link
                    to={`/tasks/${v.task_id}`}
                    className="block rounded-lg border p-3 text-sm hover:opacity-80 transition-opacity"
                    style={{ borderColor: 'var(--border-subtle)' }}
                  >
                    <div className="chinese line-clamp-1">{v.title}</div>
                    <div className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>{v.upload_date}</div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Register the route**

In `web/src/main.tsx`, add the import (near `XTimelineDetail`, line 9):

```tsx
import CreatorDetail from './routes/creator.$key';
```

Add the route entry (near `{ path: '/x/:handle', element: <XTimelineDetail /> }`, line 26):

```tsx
      { path: '/creator/:key', element: <CreatorDetail /> }
```

- [ ] **Step 5: Type-check and run the web test suite**

Run: `cd web && npx tsc --noEmit && npm test`
Expected: no type errors, all vitest suites pass (this task adds no new `.test.tsx`/`.test.ts` file — it's presentation wiring over an already-tested API layer from Task 2; if the repo's own review conventions want a smoke test for `CreatorDetail`, follow the pattern in an existing route test file such as one for `XTimelineDetail` if one exists, otherwise this is covered adequately by Task 4's manual smoke test).

- [ ] **Step 6: Commit**

```bash
git add web/src/lib/api.ts web/src/hooks/use-creator.ts web/src/routes/creator.\$key.tsx web/src/main.tsx
git commit -m "feat(web): add creator detail page at /creator/:key"
```

---

### Task 4: Manual smoke test against real data, then merge

**Files:** none — this is verification only.

- [ ] **Step 1: Start scholia against the real `knowledgeRoot`**

Confirm `~/.config/scholia/settings.conf`'s `WORK_DIR` points at `<knowledgeRoot>/videos/work` (should already be true — this is the "check-downstream" invariant `store_config.py` checks from the `learn-video` side). Start the dev server per this repo's normal run instructions.

- [ ] **Step 2: Hit the real endpoint for a known creator**

Pick a `key` from the real `<knowledgeRoot>/videos/creators.json` built in the harveyz-skill plan (Task 2) — e.g. `alejandro_ao` if that test fixture value happens to be a real entry, otherwise any entry from the actual file. `curl` (with the bearer token from scholia's running instance) `GET /api/creator/<key>` and confirm the response has the expected shape and `watched` matches whether that handle is actually in `~/.hskill/roster/registry.json`.

- [ ] **Step 3: Verify criterion #5 live**

Run `<roster-cli> registry add <a-youtube-url-for-a-currently-unwatched-creator-in-the-unresolved-or-creators-list>`, then immediately re-`curl` `/api/creator/<that-key>` **without** re-running `build_creator_index.py`. Confirm `watched` flips to `true` and `creator_id` is populated. This is the acceptance criterion that most directly tests "no caching" — do not skip it.

- [ ] **Step 4: Open the page in a browser**

Navigate to a video's detail page that has a resolvable `uploader_id`, confirm the new header link appears and navigates to `/creator/<key>`, and confirm that page renders the creator's video list with working links back to each video.

- [ ] **Step 5: Merge**

```bash
git checkout master
git merge --no-ff feature/creator-index
```

- [ ] **Step 6: Report back to the handoff document**

This is the last of the three plans. Once all three are merged in their respective repos, go back to `docs/commute/2026-09-15-video-creator-index-handoff.md` in the `harveyz-skill` worktree, run through the design spec's §6 acceptance criteria table end-to-end (all 8, this time for real, not per-repo unit tests), record the results, and set `status: 待验收` per this repo's handoff convention — the original session (`accept` phase) does the final sign-off, not this plan.
