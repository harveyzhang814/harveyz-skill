import { test, mock } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import {
  snapshot, diffSnapshots, harvestCell, mergeHarvest, capTranscript, cellDirName,
  TRANSCRIPT_LIMIT, HARNESS_FILES,
} from '../../tools/skill-harness/harvest.js'

test('差集只留 agent 真正写的东西——跑之前就在的内置 skill 副本不该被当成产出物', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  await fs.outputFile(path.join(dir, '.claude/skills/builtin/SKILL.md'), 'pre-existing')
  const before = await snapshot(dir)

  await fs.outputFile(path.join(dir, 'Documents/notes/report.md'), 'agent wrote this')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['Documents/notes/report.md'])
  await fs.remove(dir)
})

test('内容变了但大小相同的文件也要被认出来——只比 size 会漏掉原地改写', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  const f = path.join(dir, 'a.txt')
  await fs.outputFile(f, 'aaaa')
  const before = await snapshot(dir)
  await new Promise(r => setTimeout(r, 10))
  await fs.outputFile(f, 'bbbb')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['a.txt'])
  await fs.remove(dir)
})

test('harness 自己写的 stdout.log 不是 agent 的产出物，必须排除', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  await fs.outputFile(path.join(dir, 'stdout.log'), '')
  const before = await snapshot(dir)
  await fs.outputFile(path.join(dir, 'stdout.log'), 'lots of output')
  await fs.outputFile(path.join(dir, 'out.md'), 'agent')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['out.md'])
  assert.ok(HARNESS_FILES.has('stdout.log'))
  await fs.remove(dir)
})

test('transcript 截断了必须说——把不完整的原料当完整的用，比没有原料更危险', () => {
  const raw = 'x'.repeat(TRANSCRIPT_LIMIT + 100)
  const { text, truncated } = capTranscript(raw)
  assert.equal(truncated, true)
  assert.equal(text.length, TRANSCRIPT_LIMIT)

  const small = capTranscript('short')
  assert.equal(small.truncated, false)
  assert.equal(small.text, 'short')
})

test('cell 目录名把 skill 路径里的斜杠压掉——否则会在 cells/ 下建出意外的子目录层级', () => {
  assert.equal(
    cellDirName({ skill: 'mint/learn-skill', platform: 'pi', mode: 'native', repeat: 0 }),
    'mint-learn-skill__pi__native__r0',
  )
  assert.equal(
    cellDirName({ skill: 'a/b', platform: 'claude', mode: 'inject' }),
    'a-b__claude__inject__r0',
  )
})

test('snapshot 在路径不存在时拒绝而非返回空 Map——空 before 会让所有预先存在的文件看起来像 agent 产出物', async () => {
  const nonexistentDir = path.join(os.tmpdir(), 'harvest-test-nonexistent-' + Date.now())
  let threw = false
  try {
    await snapshot(nonexistentDir)
  } catch (err) {
    threw = true
    assert.equal(err.code, 'ENOENT')
  }
  assert.ok(threw, 'snapshot should throw on nonexistent directory')
})

test('snapshot 在子目录 readdir 返回 ENOENT 时仍成功——运行期间目录删除竞态需要容忍', async (t) => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  const subdir = path.join(dir, 'subdir')
  await fs.ensureDir(subdir)
  await fs.outputFile(path.join(subdir, 'file.txt'), 'content')
  const topfile = path.join(dir, 'top.txt')
  await fs.outputFile(topfile, 'top')

  // Mock fs.readdir: 根目录返回真实结果，子目录递归调用抛 ENOENT
  let callCount = 0
  t.mock.method(fs, 'readdir', async (cur, opts) => {
    callCount++
    // 第一次调用是根目录，返回真实结果
    if (callCount === 1) {
      const realReaddir = fs.promises.readdir || (await import('fs/promises')).readdir
      return realReaddir(cur, opts)
    }
    // 第二次调用是子目录，模拟竞态删除
    const err = new Error('ENOENT: no such file or directory')
    err.code = 'ENOENT'
    throw err
  })

  const snap = await snapshot(dir)
  assert.ok(snap.has('top.txt'), 'snapshot should capture top-level file')
  assert.ok(snap instanceof Map, 'snapshot should succeed despite subdir ENOENT')

  await fs.remove(dir)
})

test('snapshot 在子目录 readdir 返回 EACCES 时拒绝——不可读目录是真实故障', async (t) => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  const subdir = path.join(dir, 'subdir')
  await fs.ensureDir(subdir)
  await fs.outputFile(path.join(subdir, 'file.txt'), 'content')

  // Mock fs.readdir: 根目录返回真实结果，子目录递归调用抛 EACCES
  let callCount = 0
  t.mock.method(fs, 'readdir', async (cur, opts) => {
    callCount++
    // 第一次调用是根目录，返回真实结果
    if (callCount === 1) {
      const realReaddir = fs.promises.readdir || (await import('fs/promises')).readdir
      return realReaddir(cur, opts)
    }
    // 第二次调用是子目录，模拟权限错误
    const err = new Error('EACCES: permission denied')
    err.code = 'EACCES'
    throw err
  })

  let rejected = false
  try {
    await snapshot(dir)
  } catch (err) {
    rejected = true
    assert.equal(err.code, 'EACCES')
  }
  assert.ok(rejected, 'snapshot should reject on EACCES, not silently skip——otherwise before-snapshot 会不完整，已存在文件被误作为 agent 产出物')

  await fs.remove(dir)
})

test('产出物按原相对路径落到 artifacts/ 下——扁平化会让同名文件互相覆盖', async () => {
  const jail = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-jail-'))
  const dest = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-dest-'))
  await fs.outputFile(path.join(jail, 'Documents/notes/a.md'), 'AAA')
  await fs.outputFile(path.join(jail, '.hskill/x/a.md'), 'BBB')

  const r = await harvestCell({
    jailDir: jail, destDir: dest, raw: '{"k":1}\n',
    changedFiles: ['Documents/notes/a.md', '.hskill/x/a.md'],
  })

  assert.deepEqual(r.errors, [])
  assert.equal(await fs.readFile(path.join(dest, 'artifacts/Documents/notes/a.md'), 'utf8'), 'AAA')
  assert.equal(await fs.readFile(path.join(dest, 'artifacts/.hskill/x/a.md'), 'utf8'), 'BBB')
  assert.equal(await fs.readFile(path.join(dest, 'transcript.jsonl'), 'utf8'), '{"k":1}\n')
  await fs.remove(jail); await fs.remove(dest)
})

test('采集不到的文件记进 errors 而不是抛出——采集故障不得让整格运行失败', async () => {
  const jail = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-jail-'))
  const dest = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-dest-'))

  const r = await harvestCell({
    jailDir: jail, destDir: dest, raw: 'x',
    changedFiles: ['does/not/exist.md'],
  })

  assert.equal(r.errors.length, 1)
  assert.match(r.errors[0], /does\/not\/exist\.md/)
  assert.equal(await fs.readFile(path.join(dest, 'transcript.jsonl'), 'utf8'), 'x')
  await fs.remove(jail); await fs.remove(dest)
})

// 不在 brief 列表里，是 task-3 额外要求的：runner.js 现在无论 snapshot
// 成不成功都会调用 harvestCell（fix 之后的行为——snapshot 失败只让
// changedFiles 退化成空，不再跳过整个 harvestCell），这条测试证明
// harvestCell 本身撑得住这个前提：即便 jailDir 已经整个消失，
// 它仍然完整落盘 transcript、把每个采不到的文件计入 errors 而不抛出。
// runOne 本身没有导出（brief 明确不希望为了可测性而改结构），这里在
// harvestCell 这一层验证的就是 runner 依赖的这条真实生产路径的前提条件。
test('jailDir 整个不存在时 harvestCell 仍不抛出——runner 现在无论 snapshot 是否失败都会调用它，这个前提必须扛得住', async () => {
  const missingJail = path.join(os.tmpdir(), 'harvest-jail-missing-' + Date.now())
  const dest = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-dest-'))

  const r = await harvestCell({
    jailDir: missingJail, destDir: dest, raw: 'transcript-data',
    changedFiles: ['some/file.md', 'other.txt'],
  })

  assert.equal(r.errors.length, 2)
  assert.match(r.errors[0], /some\/file\.md/)
  assert.match(r.errors[1], /other\.txt/)
  assert.equal(await fs.readFile(path.join(dest, 'transcript.jsonl'), 'utf8'), 'transcript-data')
  await fs.remove(dest)
})

// changedFiles 为空（runner.js 在 snapshot 失败时的退化情形）不该影响
// transcript 的落盘——transcript 是唯一花钱重跑模型也换不回来的证据，
// snapshot 拿不到基准不该连累它。
test('changedFiles 为空时 transcript 仍照常落盘——snapshot 失败退化成空 diff，不该连累 transcript', async () => {
  const jail = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-jail-'))
  const dest = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-dest-'))
  await fs.outputFile(path.join(jail, 'note.md'), 'ignored because changedFiles is empty')

  const result = await harvestCell({
    jailDir: jail, destDir: dest, raw: 'transcript-survives',
    changedFiles: [],
  })

  assert.deepEqual(result.errors, [])
  assert.equal(await fs.readFile(path.join(dest, 'transcript.jsonl'), 'utf8'), 'transcript-survives')
  await fs.remove(jail); await fs.remove(dest)
})

// mergeHarvest 是 runner.js 里两处合并逻辑（成功路径 + harvestCell 抛出的
// 兜底路径）唯一的实现，runner.js 不再手写 spread——测这个函数就是测
// 生产用的那份合并逻辑，不是重新拼一遍再断言拼接本身。
// 如果 snapshot 错误和 per-file 错误互相覆盖，采集失败要么被误判成
// 别的原因，要么直接从 errors 里消失，人根本查不到。
test('mergeHarvest：snapshot 错误排在前、harvestCell 自身 errors 跟在后面，谁都不能被覆盖', () => {
  const merged = mergeHarvest(['EACCES: permission denied'], { truncated: true, errors: ['artifact a.md: ENOENT'] })
  assert.deepEqual(merged.errors, ['EACCES: permission denied', 'artifact a.md: ENOENT'])
  assert.equal(merged.truncated, true)
})

test('mergeHarvest：没有 snapshot 错误时 truncated 与 errors 原样来自 result', () => {
  const merged = mergeHarvest([], { truncated: false, errors: ['artifact b.md: EACCES'] })
  assert.deepEqual(merged.errors, ['artifact b.md: EACCES'])
  assert.equal(merged.truncated, false)
})

test('mergeHarvest：result 缺失（harvestCell 自己抛出）时用调用方给的错误顶替，truncated 恒为 false', () => {
  const merged = mergeHarvest(['EACCES: permission denied'], null, 'ensureDir failed: EPERM')
  assert.deepEqual(merged.errors, ['EACCES: permission denied', 'ensureDir failed: EPERM'])
  assert.equal(merged.truncated, false)
})
