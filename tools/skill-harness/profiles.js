// 差异表。capabilities 不驱动运行时分派——它是两件事：
// 写在代码里不会腐烂的可执行文档，以及配合 L1 整表快照的回归护栏。
// 唯一的生产消费者是 report.js（见 spec 风险 1：没有消费者的表会腐烂成谎言）。

export const claudeProfile = {
  id: 'claude',
  skillChannel: 'skill-dir',
  builtinSkillFloor: 15,
  injection: 'append-system-prompt',
  qualityChannel: 'stdout-json',
  processChannel: 'inline',
  transcriptFormat: 'claude-code-jsonl',
  isolation: ['HOME', 'CLAUDE_CONFIG_DIR', '--setting-sources user'],
  capabilities: new Set(['tool-trace', 'usage', 'cost-cap', 'tool-allowlist', 'structured-output', 'system-prompt-append']),
  compensation: '',
}

export const piProfile = {
  id: 'pi',
  skillChannel: 'explicit-flag',
  builtinSkillFloor: 0,
  injection: 'append-system-prompt',
  qualityChannel: 'stdout-json',
  processChannel: 'inline',
  transcriptFormat: 'pi-jsonl',
  isolation: ['-ns', '-ne', '-np', '--no-themes', '-nc', '--session-dir'],
  capabilities: new Set(['tool-trace', 'usage', 'tool-allowlist', 'structured-output', 'system-prompt-append']),
  compensation: '',
}

export const hermesProfile = {
  id: 'hermes',
  skillChannel: 'skill-dir',
  builtinSkillFloor: 0,
  injection: 'prompt-only',
  qualityChannel: 'stdout-text',
  processChannel: 'collect',
  transcriptFormat: 'claude-code-jsonl',
  isolation: ['HOME', '--safe-mode'],
  capabilities: new Set(['tool-trace', 'usage', 'tool-allowlist', 'structured-output']),
  compensation: '',
}

export const PROFILES = [claudeProfile, piProfile, hermesProfile]
