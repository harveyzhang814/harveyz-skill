#!/usr/bin/env node
// E2E 验证 scripts/merge-to-staging.sh：真实 git 子进程，不 mock。
// 对应 docs/superpowers/specs/2026-08-26-concurrent-worktree-staging-merge-test-plan.md
// 的场景 A / B / C。脚本只操作本地 refs/heads/staging（update-ref CAS），
// 不涉及任何远端，所以测试仓库也不需要 origin，直接一个 hub + 两个 worktree。

const { spawnSync, spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const MERGE_SCRIPT = path.resolve(__dirname, 'merge-to-staging.sh');

function sh(cwd, cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, { cwd, encoding: 'utf8', ...opts });
  if (result.status !== 0 && !opts.allowFail) {
    throw new Error(
      `命令失败: ${cmd} ${args.join(' ')} (cwd=${cwd})\nstdout: ${result.stdout}\nstderr: ${result.stderr}`
    );
  }
  return result;
}

function git(cwd, args, opts = {}) {
  return sh(cwd, 'git', args, opts);
}

function runMergeScript(cwd, env = {}) {
  return spawnSync(MERGE_SCRIPT, [], {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, ...env },
  });
}

function runMergeScriptAsync(cwd, env = {}) {
  return new Promise((resolve) => {
    const child = spawn(MERGE_SCRIPT, [], {
      cwd,
      env: { ...process.env, ...env },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => (stdout += d));
    child.stderr.on('data', (d) => (stderr += d));
    child.on('close', (status) => resolve({ status, stdout, stderr }));
  });
}

function assert(cond, msg) {
  if (!cond) throw new Error(`断言失败: ${msg}`);
}

function setupScenarioRepo(tag, sharedTxtContent = 'line1\nline2\nline3\n') {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `merge-to-staging-e2e-${tag}-`));
  const hubDir = path.join(root, 'hub');

  sh(root, 'git', ['init', '-q', hubDir]);
  git(hubDir, ['config', 'user.email', 'e2e@test.local']);
  git(hubDir, ['config', 'user.name', 'E2E Bot']);
  git(hubDir, ['checkout', '-q', '-b', 'staging']);
  fs.writeFileSync(path.join(hubDir, 'shared.txt'), sharedTxtContent);
  git(hubDir, ['add', '.']);
  git(hubDir, ['commit', '-q', '-m', 'chore: init']);

  const agentADir = path.join(root, 'agentA');
  const agentBDir = path.join(root, 'agentB');
  git(hubDir, ['worktree', 'add', '-q', agentADir, '-b', 'feature/a', 'staging']);
  git(hubDir, ['worktree', 'add', '-q', agentBDir, '-b', 'feature/b', 'staging']);
  for (const dir of [agentADir, agentBDir]) {
    git(dir, ['config', 'user.email', 'e2e@test.local']);
    git(dir, ['config', 'user.name', 'E2E Bot']);
  }

  // hub 始终停在 staging 上，模拟真实项目里"主 worktree 一直 checkout 着 staging"
  return { root, hubDir, agentADir, agentBDir };
}

function cleanup(root) {
  fs.rmSync(root, { recursive: true, force: true });
}

function stagingLogSubjects(hubDir) {
  const out = git(hubDir, ['log', '--format=%s', 'refs/heads/staging']).stdout;
  return out.split('\n').filter(Boolean);
}

function assertHubSynced(hubDir, expectedFiles) {
  assert(
    git(hubDir, ['symbolic-ref', '--short', 'HEAD']).stdout.trim() === 'staging',
    'hub 应该始终停在 staging 上'
  );
  const status = git(hubDir, ['status', '--porcelain']).stdout;
  assert(status === '', `hub 的 git status 应该干净（脚本应自动同步索引），实际:\n${status}`);
  for (const f of expectedFiles) {
    assert(fs.existsSync(path.join(hubDir, f)), `hub 工作目录应该出现 ${f}（脚本应自动同步工作区）`);
  }
}

async function scenarioA() {
  const { root, hubDir, agentADir, agentBDir } = setupScenarioRepo('a');
  try {
    fs.writeFileSync(path.join(agentADir, 'fileA.txt'), 'from agent A\n');
    git(agentADir, ['add', '.']);
    git(agentADir, ['commit', '-q', '-m', 'feat: agent A change']);

    fs.writeFileSync(path.join(agentBDir, 'fileB.txt'), 'from agent B\n');
    git(agentBDir, ['add', '.']);
    git(agentBDir, ['commit', '-q', '-m', 'feat: agent B change']);

    const [resA, resB] = await Promise.all([
      runMergeScriptAsync(agentADir),
      runMergeScriptAsync(agentBDir),
    ]);

    assert(resA.status === 0, `agent A 应成功退出，实际: ${resA.status}\n${resA.stdout}\n${resA.stderr}`);
    assert(resB.status === 0, `agent B 应成功退出，实际: ${resB.status}\n${resB.stdout}\n${resB.stderr}`);

    const subjects = stagingLogSubjects(hubDir);
    assert(subjects.some((s) => s.includes('feature/a')), 'staging 历史应包含 feature/a 的合并');
    assert(subjects.some((s) => s.includes('feature/b')), 'staging 历史应包含 feature/b 的合并');

    assertHubSynced(hubDir, ['fileA.txt', 'fileB.txt']);

    const sawRetry = resA.stderr.includes('重试') || resB.stderr.includes('重试');
    console.log(`  [场景 A] 是否观察到过重试: ${sawRetry ? '是' : '否（两次没有真正撞车，属正常）'}`);
    console.log('  [场景 A] PASS：两个 agent 并发合并互不冲突的分支，均成功且都进入 staging，hub 自动同步。');
  } finally {
    cleanup(root);
  }
}

async function scenarioB() {
  const { root, hubDir, agentADir, agentBDir } = setupScenarioRepo('b');
  try {
    fs.writeFileSync(path.join(agentADir, 'fileA.txt'), 'from agent A\n');
    git(agentADir, ['add', '.']);
    git(agentADir, ['commit', '-q', '-m', 'feat: agent A change']);

    fs.writeFileSync(path.join(agentBDir, 'fileB.txt'), 'from agent B\n');
    git(agentBDir, ['add', '.']);
    git(agentBDir, ['commit', '-q', '-m', 'feat: agent B change']);

    // agent A 先起步，但在更新 ref 前人为插入延迟窗口
    const pendingA = runMergeScriptAsync(agentADir, { MERGE_TO_STAGING_TEST_DELAY_MS: '1500' });
    // 给 A 留出时间跑完 merge-tree/commit-tree，确保它正卡在延迟窗口里
    await new Promise((r) => setTimeout(r, 500));

    // agent B 在这个窗口期内完整跑完，应该顺利成功、且不需要重试
    const resB = runMergeScript(agentBDir);
    assert(resB.status === 0, `agent B 应成功退出，实际: ${resB.status}\n${resB.stdout}\n${resB.stderr}`);
    assert(!resB.stderr.includes('重试'), 'agent B 不应触发重试（它是窗口期内第一个更新 ref 的）');

    const resA = await pendingA;
    assert(resA.status === 0, `agent A 最终应成功退出，实际: ${resA.status}\n${resA.stdout}\n${resA.stderr}`);
    assert(resA.stderr.includes('重试'), 'agent A 应该确定性地触发过一次重试（ref 被抢先移动后重新计算）');

    const subjects = stagingLogSubjects(hubDir);
    assert(subjects.some((s) => s.includes('feature/a')), 'staging 历史应包含 feature/a 的合并');
    assert(subjects.some((s) => s.includes('feature/b')), 'staging 历史应包含 feature/b 的合并');

    assertHubSynced(hubDir, ['fileA.txt', 'fileB.txt']);

    console.log('  [场景 B] PASS：agent A 前后错开发起，被 B 抢先后确定性地触发一次重试并最终成功，hub 自动同步。');
  } finally {
    cleanup(root);
  }
}

async function scenarioC() {
  const { root, hubDir, agentADir, agentBDir } = setupScenarioRepo('c');
  try {
    fs.writeFileSync(path.join(agentADir, 'shared.txt'), 'line1\nAGENT A CHANGE\nline3\n');
    git(agentADir, ['add', '.']);
    git(agentADir, ['commit', '-q', '-m', 'feat: agent A edits shared line']);

    fs.writeFileSync(path.join(agentBDir, 'shared.txt'), 'line1\nAGENT B CHANGE\nline3\n');
    git(agentBDir, ['add', '.']);
    git(agentBDir, ['commit', '-q', '-m', 'feat: agent B edits shared line']);

    const resA = runMergeScript(agentADir);
    assert(resA.status === 0, `agent A 应成功退出，实际: ${resA.status}\n${resA.stdout}\n${resA.stderr}`);

    const resB1 = runMergeScript(agentBDir);
    assert(resB1.status === 2, `agent B 第一次应以冲突退出码 2 结束，实际: ${resB1.status}\n${resB1.stdout}\n${resB1.stderr}`);
    assert(resB1.stderr.includes('冲突'), 'agent B 的输出应提示检测到冲突');

    const conflicted = git(agentBDir, ['diff', '--name-only', '--diff-filter=U']).stdout.trim();
    assert(conflicted === 'shared.txt', `冲突文件应为 shared.txt，实际: "${conflicted}"`);

    const content = fs.readFileSync(path.join(agentBDir, 'shared.txt'), 'utf8');
    assert(content.includes('<<<<<<<'), 'agent B 的 worktree 里应该落下真实冲突标记');

    // 模拟 agent B 手动解决冲突（这是发生在 feature/b 分支上的普通提交，不受 staging 的
    // commit-msg 校验约束）
    fs.writeFileSync(path.join(agentBDir, 'shared.txt'), 'line1\nAGENT A CHANGE + AGENT B CHANGE\nline3\n');
    git(agentBDir, ['add', 'shared.txt']);
    git(agentBDir, ['commit', '-q', '-m', 'merge: resolve conflict with staging']);

    const resB2 = runMergeScript(agentBDir);
    assert(resB2.status === 0, `冲突解决后 agent B 重新合并应成功，实际: ${resB2.status}\n${resB2.stdout}\n${resB2.stderr}`);

    const subjects = stagingLogSubjects(hubDir);
    assert(subjects.some((s) => s.includes('feature/a')), 'staging 历史应包含 feature/a 的合并');
    assert(subjects.some((s) => s.includes('feature/b')), 'staging 历史应包含 feature/b 的合并（冲突解决后）');

    assertHubSynced(hubDir, []);
    const hubSharedContent = fs.readFileSync(path.join(hubDir, 'shared.txt'), 'utf8');
    assert(
      hubSharedContent.includes('AGENT A CHANGE + AGENT B CHANGE'),
      'hub 工作目录应同步到冲突解决后的最终内容'
    );

    console.log('  [场景 C] PASS：真实内容冲突被正确检测、落标记、解决后重新调用脚本成功合并，hub 自动同步。');
  } finally {
    cleanup(root);
  }
}

// hub（= 真实项目里那个一直 checkout 着 staging 的主 worktree）带着未提交改动时，
// update-ref 移完指针不会自动更新它，索引和工作树会一起停在合并前。这两个场景锁住
// 「不重叠就照常同步、重叠才退让」这条分界——退让本身没问题，退让得太早才是问题。
async function scenarioD() {
  const { root, hubDir, agentADir } = setupScenarioRepo('d');
  try {
    // hub 上有别人的在制品，动的是与本次合并完全无关的文件。两种脏都覆盖：
    // 未暂存的改动，以及已暂存的新增——真实踩到的那次，主工作树里正是一堆已暂存条目。
    fs.writeFileSync(path.join(hubDir, 'wip.txt'), 'someone else WIP\n');
    fs.writeFileSync(path.join(hubDir, 'staged-wip.txt'), 'staged WIP\n');
    git(hubDir, ['add', 'staged-wip.txt']);

    fs.writeFileSync(path.join(agentADir, 'fileA.txt'), 'from agent A\n');
    git(agentADir, ['add', '.']);
    git(agentADir, ['commit', '-q', '-m', 'feat: agent A change']);

    const res = runMergeScript(agentADir);
    assert(res.status === 0, `合并应成功，实际: ${res.status}\n${res.stdout}\n${res.stderr}`);

    assert(
      git(hubDir, ['symbolic-ref', '--short', 'HEAD']).stdout.trim() === 'staging',
      'hub 应该始终停在 staging 上'
    );
    // 合并内容必须真的落到 hub 的工作区，而不是只移了指针
    assert(fs.existsSync(path.join(hubDir, 'fileA.txt')), 'hub 工作区应出现 fileA.txt（合并内容已同步进来）');
    // 别人的在制品必须一个字节都没丢
    assert(
      fs.readFileSync(path.join(hubDir, 'wip.txt'), 'utf8') === 'someone else WIP\n',
      'hub 上未暂存的在制品必须原样保留'
    );
    assert(
      fs.readFileSync(path.join(hubDir, 'staged-wip.txt'), 'utf8') === 'staged WIP\n',
      'hub 上已暂存的在制品必须原样保留'
    );
    // 同步之后，status 里只应剩那两份真实的在制品，不能有「已暂存删除」这类假象
    const status = git(hubDir, ['status', '--porcelain']).stdout.trim().split('\n').filter(Boolean);
    assert(
      status.length === 2 && status.every((l) => l.endsWith('wip.txt')),
      `hub 的 status 应只剩那两份在制品，实际:\n${status.join('\n')}`
    );
    // 走的是 stash 了但 pop 干净、没有残留兜底副本的路径，不是侥幸绕过 stash
    assert(
      git(hubDir, ['stash', 'list']).stdout.trim() === '',
      'hub 的 stash list 应为空（pop 成功后自动清空，没有残留兜底副本）'
    );

    console.log('  [场景 D] PASS：hub 脏但与合并不重叠 → 合并内容照常同步进工作区，在制品原样保留，stash 无残留。');
  } finally {
    cleanup(root);
  }
}

async function scenarioE() {
  const { root, hubDir, agentADir } = setupScenarioRepo('e');
  try {
    // hub 上的在制品动的正是本次合并也要改的文件——此时任何自动同步都可能覆盖它，
    // 脚本必须退让，并且退让要说清楚怎么恢复。
    fs.writeFileSync(path.join(hubDir, 'shared.txt'), 'line1\nHUB LOCAL EDIT\nline3\n');

    fs.writeFileSync(path.join(agentADir, 'shared.txt'), 'line1\nFROM AGENT A\nline3\n');
    git(agentADir, ['add', '.']);
    git(agentADir, ['commit', '-q', '-m', 'feat: agent A edits shared.txt']);

    const res = runMergeScript(agentADir);
    assert(res.status === 0, `合并本身应成功（冲突的是 hub 工作区，不是分支内容），实际: ${res.status}\n${res.stderr}`);

    // 合并进了 staging
    assert(
      stagingLogSubjects(hubDir).some((s) => s.includes('feature/a')),
      'staging 历史应包含 feature/a 的合并'
    );
    // stash pop 冲突：工作树里落下 git 原生冲突标记，两边内容都还在
    const hubSharedContent = fs.readFileSync(path.join(hubDir, 'shared.txt'), 'utf8');
    assert(hubSharedContent.includes('<<<<<<<'), 'hub 的 shared.txt 应该出现 git 冲突标记');
    assert(hubSharedContent.includes('======='), 'hub 的 shared.txt 应该出现冲突分隔符');
    assert(hubSharedContent.includes('>>>>>>>'), 'hub 的 shared.txt 应该出现冲突标记收尾');
    assert(hubSharedContent.includes('HUB LOCAL EDIT'), 'hub 本地编辑的内容必须还在冲突标记里');
    assert(hubSharedContent.includes('FROM AGENT A'), '合并带来的内容必须还在冲突标记里');
    // 兜底副本必须还在 stash 里，冲突解决失败不会丢东西
    assert(
      git(hubDir, ['stash', 'list']).stdout.trim() !== '',
      'hub 的 stash list 不应为空（pop 冲突失败时兜底副本必须保留）'
    );
    // 必须明确告诉调用方「没同步」、冲突标记在哪、以及兜底副本在 stash 里
    assert(res.stderr.includes('未自动同步'), `应提示未自动同步，实际 stderr:\n${res.stderr}`);
    assert(res.stderr.includes('冲突标记'), `应提示冲突标记，实际 stderr:\n${res.stderr}`);
    assert(res.stderr.includes('stash'), `应提示兜底副本在 stash 里，实际 stderr:\n${res.stderr}`);

    console.log('  [场景 E] PASS：hub 的在制品与合并同一处内容冲突 → 落 git 冲突标记，兜底副本留在 stash 里。');
  } finally {
    cleanup(root);
  }
}

// hub 与合并改的是同一个文件，但离得足够远（超出 diff 默认 3 行上下文）的两行——
// 旧版 read-tree -m -u 按路径整体拒绝，这种情况必然落到「未自动同步」；新的
// stash+reset+pop 走 git 原生行级三方合并，必然自动成功。这是本次改动的核心收益，
// 场景 D/E 的既有覆盖证明不了它，需要专门的场景。
async function scenarioF() {
  const lines = Array.from({ length: 12 }, (_, i) => `line${i + 1}`).join('\n') + '\n';
  const { root, hubDir, agentADir } = setupScenarioRepo('f', lines);
  try {
    const hubLines = lines.split('\n');
    hubLines[0] = 'HUB EDITS LINE 1';
    fs.writeFileSync(path.join(hubDir, 'shared.txt'), hubLines.join('\n'));

    const agentLines = lines.split('\n');
    agentLines[9] = 'AGENT A EDITS LINE 10';
    fs.writeFileSync(path.join(agentADir, 'shared.txt'), agentLines.join('\n'));
    git(agentADir, ['add', '.']);
    git(agentADir, ['commit', '-q', '-m', 'feat: agent A edits line 10 of shared.txt']);

    const res = runMergeScript(agentADir);
    assert(res.status === 0, `合并应成功，实际: ${res.status}\n${res.stdout}\n${res.stderr}`);

    assert(
      stagingLogSubjects(hubDir).some((s) => s.includes('feature/a')),
      'staging 历史应包含 feature/a 的合并'
    );

    // 自动合并成功：hub 自己那行的编辑作为正常未提交改动保留（跟场景 D 的
    // wip.txt/staged-wip.txt 一样，「同步成功」不等于 status 清空，等于没有冲突、
    // 没有停在合并前），无冲突标记，也没有停在「UU」冲突态
    const status = git(hubDir, ['status', '--porcelain']).stdout.trim();
    assert(
      status === 'M shared.txt' || status === ' M shared.txt',
      `hub 应只剩 shared.txt 的正常未提交改动（不应是 UU 冲突态、也不应停在「未自动同步」的旧内容），实际:\n${status}`
    );
    const hubSharedContent = fs.readFileSync(path.join(hubDir, 'shared.txt'), 'utf8');
    assert(!hubSharedContent.includes('<<<<<<<'), 'hub 的 shared.txt 不应出现冲突标记');
    assert(hubSharedContent.includes('HUB EDITS LINE 1'), 'hub 自己那行的编辑必须保留');
    assert(hubSharedContent.includes('AGENT A EDITS LINE 10'), '合并带来的那行编辑必须同步进来');
    assert(
      git(hubDir, ['stash', 'list']).stdout.trim() === '',
      'hub 的 stash list 应为空（pop 干净后自动清空）'
    );

    console.log('  [场景 F] PASS：hub 与合并改到同一文件的不同行 → 自动合并成功（read-tree 版本做不到）。');
  } finally {
    cleanup(root);
  }
}

// hub（= 一直 checkout 着 staging 的主 worktree）脏 + 多 agent 真并发合并：复现
// sync_staging_worktree() 没有锁保护时会互相踩踏的问题——index.lock 冲突、
// refs/heads/staging 的提交历史里少掉本该在的合并（脚本报告成功，但提交后来从
// 分支历史里消失，等同于悄悄回退丢已合并的工作）。hub 特意带大量未跟踪文件，
// 拖慢 stash push -u / reset --hard，拉宽并发窗口，逼近真实项目体量下才会稳定
// 复现的时序。对应 docs/superpowers/specs/2026-09-16-merge-to-staging-concurrency-lock-test-plan.md
// 的场景 G。
async function scenarioG(trials = 15, nAgents = 5, nHubWipFiles = 800) {
  for (let i = 0; i < trials; i++) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), `merge-to-staging-e2e-g${i}-`));
    const hubDir = path.join(root, 'hub');
    try {
      sh(root, 'git', ['init', '-q', hubDir]);
      git(hubDir, ['config', 'user.email', 'e2e@test.local']);
      git(hubDir, ['config', 'user.name', 'E2E Bot']);
      git(hubDir, ['checkout', '-q', '-b', 'staging']);
      fs.writeFileSync(path.join(hubDir, 'shared.txt'), 'line1\nline2\nline3\n');
      git(hubDir, ['add', '.']);
      git(hubDir, ['commit', '-q', '-m', 'chore: init']);

      const agents = [];
      for (let a = 0; a < nAgents; a++) {
        const letter = String.fromCharCode(97 + a);
        const dir = path.join(root, `agent${letter.toUpperCase()}`);
        git(hubDir, ['worktree', 'add', '-q', dir, '-b', `feature/${letter}`, 'staging']);
        git(dir, ['config', 'user.email', 'e2e@test.local']);
        git(dir, ['config', 'user.name', 'E2E Bot']);
        agents.push({ letter, dir });
      }

      // hub 脏：大量未跟踪文件 + 一份已暂存文件，都与各 agent 的改动不重叠，
      // 逼脚本走 detach/stash/reset 路径而不是干净分支的单条 reset --hard。
      for (let f = 0; f < nHubWipFiles; f++) {
        fs.writeFileSync(path.join(hubDir, `hub-untracked-${f}.txt`), `untracked wip ${f} trial ${i}\n`);
      }
      fs.writeFileSync(path.join(hubDir, 'hub-staged-wip.txt'), `staged wip trial ${i}\n`);
      git(hubDir, ['add', 'hub-staged-wip.txt']);

      for (const { letter, dir } of agents) {
        fs.writeFileSync(path.join(dir, `file${letter.toUpperCase()}.txt`), `from agent ${letter}\n`);
        git(dir, ['add', '.']);
        git(dir, ['commit', '-q', '-m', `feat: agent ${letter} change`]);
      }

      const results = await Promise.all(agents.map(({ dir }) => runMergeScriptAsync(dir)));
      results.forEach((r, idx) => {
        assert(r.status === 0, `agent ${agents[idx].letter} 应成功退出（trial ${i}），实际: ${r.status}\n${r.stderr}`);
      });

      assert(
        git(hubDir, ['symbolic-ref', '--short', 'HEAD']).stdout.trim() === 'staging',
        `hub 应始终停在 staging 上，不出现分离头指针（trial ${i}）`
      );

      const subjects = stagingLogSubjects(hubDir);
      for (const { letter } of agents) {
        assert(
          subjects.some((s) => s.includes(`feature/${letter}`)),
          `staging 历史应包含 feature/${letter} 的合并，不允许消失（trial ${i}）`
        );
      }

      assert(
        fs.readFileSync(path.join(hubDir, 'hub-staged-wip.txt'), 'utf8') === `staged wip trial ${i}\n`,
        `hub 原有在制品 hub-staged-wip.txt 必须原样保留（trial ${i}）`
      );
      for (const f of [0, Math.floor(nHubWipFiles / 2), nHubWipFiles - 1]) {
        assert(
          fs.existsSync(path.join(hubDir, `hub-untracked-${f}.txt`)),
          `hub 原有在制品 hub-untracked-${f}.txt 必须原样保留（trial ${i}）`
        );
      }
      for (const { letter } of agents) {
        assert(
          fs.existsSync(path.join(hubDir, `file${letter.toUpperCase()}.txt`)),
          `hub 工作区应同步 file${letter.toUpperCase()}.txt（trial ${i}）`
        );
      }

      const stashList = git(hubDir, ['stash', 'list']).stdout.trim();
      assert(stashList === '', `hub 的 stash list 应收尾为空（trial ${i}）：\n${stashList}`);
    } finally {
      cleanup(root);
    }
  }

  console.log(`  [场景 G] PASS：${nAgents} 个 agent 真并发合并 + hub 脏，重复 ${trials} 轮全部无回退/无冲突/无残留。`);
}

// 模拟"持锁进程被杀死后残留的锁目录"：手动在 hub 私有 git-dir 下建一个锁目录，
// 把 owner 文件的时间戳改到阈值（LOCK_STALE_SECONDS=60s）之外。脚本应该检测到
// 残留、打警告、强制清除后正常完成，而不是无限等待。对应测试清单场景 H。
async function scenarioH() {
  const { root, hubDir, agentADir } = setupScenarioRepo('h');
  try {
    const gitDirRaw = git(hubDir, ['rev-parse', '--git-dir']).stdout.trim();
    const gitDirAbs = path.isAbsolute(gitDirRaw) ? gitDirRaw : path.join(hubDir, gitDirRaw);
    const lockDir = path.join(gitDirAbs, 'merge-to-staging.lock');
    fs.mkdirSync(lockDir);
    const staleTs = Math.floor(Date.now() / 1000) - 120; // 120s 前，超过 60s 阈值
    fs.writeFileSync(path.join(lockDir, 'owner'), `pid=999999 ts=${staleTs}\n`);

    fs.writeFileSync(path.join(agentADir, 'fileA.txt'), 'from agent A\n');
    git(agentADir, ['add', '.']);
    git(agentADir, ['commit', '-q', '-m', 'feat: agent A change']);

    const res = runMergeScript(agentADir);
    assert(res.status === 0, `合并应正常完成，实际: ${res.status}\n${res.stdout}\n${res.stderr}`);
    assert(
      res.stderr.includes('残留') && res.stderr.includes('强制清除'),
      `应打印检测到残留锁并强制清除的警告，实际 stderr:\n${res.stderr}`
    );

    assertHubSynced(hubDir, ['fileA.txt']);
    assert(!fs.existsSync(lockDir), '锁目录应在同步完成后被释放，不应残留');

    console.log('  [场景 H] PASS：残留锁超过阈值 → 强制清除并打警告，合并正常完成，不会无限等待。');
  } finally {
    cleanup(root);
  }
}

async function main() {
  const scenarios = [
    ['场景 A：两个 agent 几乎同时发起', scenarioA],
    ['场景 B：两个 agent 前后错开发起', scenarioB],
    ['场景 C：真实内容冲突', scenarioC],
    ['场景 D：hub 脏但与合并不重叠', scenarioD],
    ['场景 E：hub 脏且与合并重叠（同一处内容冲突）', scenarioE],
    ['场景 F：hub 与合并改到同一文件的不同行', scenarioF],
    ['场景 G：多 agent 并发 + hub 脏（并发锁压力测试）', scenarioG],
    ['场景 H：残留锁过期回收', scenarioH],
  ];

  let failures = 0;
  for (const [name, fn] of scenarios) {
    console.log(`\n▶ ${name}`);
    try {
      await fn();
    } catch (err) {
      failures += 1;
      console.error(`  ✗ FAIL: ${err.message}`);
    }
  }

  console.log(`\n${scenarios.length - failures}/${scenarios.length} 场景通过`);
  process.exit(failures > 0 ? 1 : 0);
}

main();
