import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const PATH = 'skills/devflow/manage-worktree/SKILL.md'
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)

test('manage-worktree is registered in devflow with matching version and hash', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const index = JSON.parse(await readFile(resolve(root, 'skills-index.json'), 'utf8'))
  const entry = index.skills.find(s => s.path === 'devflow/manage-worktree')
  assert.match(body, /^name: manage-worktree$/m)
  assert.match(body, /^version: ["']?0\.5\.0["']?$/m)
  assert.equal(entry.bundle, 'devflow')
  assert.equal(entry.contentVersion, '0.5.0')
  assert.equal(entry.contentHash, hash(body))
})

test('manage-worktree states its actions, rules, hosts and boundaries', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  for (const phrase of [
    '「准备」', '「进入」', '「检测」', '「离开」',
    'scripts/inspect-worktree.sh',
    '「合并」', 'scripts/merge-worktree.sh', 'resolved.env',
    '`.worktrees/<分支名，/ 换成 +>`',
    '锚点',
    '不向用户确认',
    'EnterWorktree(path: "<工作区绝对路径>")', 'ExitWorktree(action: "keep")',
    'codex -C <工作区>', 'git -C <工作区>',
    '绝不删分支、绝不 `--force`', '禁止手写 `git worktree remove`、`git branch -d/-D`',
    'scripts/create-worktree.sh', 'scripts/leave-worktree.sh',
    '非 git 目录', '不适用',
  ]) assert.ok(body.includes(phrase), phrase)
})

test('manage-worktree names its callers without pinning their step numbers', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  assert.ok(body.includes('调用方：init-spec 建档前、develop-plan 开工前、handoff 的 author 阶段起草交接文档前调用「准备」'))
  assert.doesNotMatch(body, /(init-spec|develop-plan|handoff)[^。；\n]{0,12}第 ?\d+ ?步/)
})

test('manage-worktree no longer names the rule-file lookup chain or the old boundary', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  for (const gone of [
    '不合并、不清理 worktree、不删除分支',
    '新建前向用户一次确认', 'after one user confirmation', '用户拒绝确认',
    '.hskill/init-workflow/workflow-config.yml', '.claude/workflow-config.yml', '`rule_file`',
  ]) assert.ok(!body.includes(gone), gone)
})

test('manage-worktree tells Claude Code to leave the current worktree before entering one outside .claude/worktrees', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const section = body.slice(body.indexOf('### Claude Code'), body.indexOf('### Codex'))
  assert.ok(section.includes('Switching from this session is limited to worktrees managed by Claude Code'))
  assert.ok(section.includes('先 `ExitWorktree(action: "keep")` 回到启动目录，再 `EnterWorktree(path:)`'))
})

const leaseSection = body => body.slice(body.indexOf('## 画布节点内补调租约'), body.indexOf('## 「检测」'))

test('inside a canvas node, enter claims the worktree lease with an absolute path', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const section = leaseSection(body)
  assert.ok(section.length > 0, 'lease section exists before 「检测」')
  for (const phrase of [
    'AGENT_CANVAS_NODE_TOKEN', 'command -v agent-canvas-ctl',
    'agent-canvas-ctl claim-worktree --path <工作区绝对路径>',
  ]) assert.ok(section.includes(phrase), phrase)
  const enter = body.slice(body.indexOf('## 「进入」'), body.indexOf('## 按宿主进出'))
  assert.ok(enter.includes('画布节点内补调租约'))
  const prepare = body.slice(body.indexOf('### 收尾'), body.indexOf('## 「进入」'))
  assert.ok(prepare.includes('画布节点内补调租约'))
})

test('inside a canvas node, leave releases the lease', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  assert.ok(leaseSection(body).includes('leave-worktree.sh'))
  const hosts = body.slice(body.indexOf('## 按宿主进出'))
  assert.ok(hosts.includes('画布节点内补调租约'))
  const row = body.split('\n').find(l => l.startsWith('| 「离开」 |'))
  assert.ok(row.includes('leave-worktree.sh'))
  const intro = hosts.slice(0, hosts.indexOf('### Claude Code'))
  assert.ok(intro.includes('画布节点内补调租约') && intro.includes('leave-worktree.sh'))
  const claude = body.slice(body.indexOf('### Claude Code'), body.indexOf('### Codex'))
  assert.ok(claude.includes('leave-worktree.sh --path <离开前的工作区根>'))
  assert.ok(claude.includes('绝不 `remove`'))
})

test('lease call failures never fail enter or leave', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const section = leaseSection(body)
  assert.ok(section.includes('不影响「进入」「离开」本身的结果'))
  for (const code of ['lease-service-unavailable', 'not-ready', 'no-node-identity']) assert.ok(section.includes(code), code)
})

test('outside a canvas node nothing is called', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const section = leaseSection(body)
  assert.ok(section.includes('画布外'))
  assert.ok(section.includes('不调用'))
})
