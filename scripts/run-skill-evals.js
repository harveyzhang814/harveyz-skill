#!/usr/bin/env node
// run-skill-evals.js
// Behavioral eval runner for skills.
//
// Discovers skills/*/tests/*.eval.json, runs each case by calling
// `claude -p "<skill_content + test_prompt>" --model <MODEL>`,
// applies deterministic (contains/not_contains/regex) and rubric (LLM-judge)
// checks, then saves results to eval-results/<timestamp>.json.
//
// Usage:
//   node scripts/run-skill-evals.js              # run all eval files
//   node scripts/run-skill-evals.js --skill brainstorming  # one skill only

import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { spawnSync } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..');
const MODEL = 'claude-haiku-4-5-20251001';
const CLAUDE_TIMEOUT_MS = 240_000;

// ── arg parsing ───────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const filterIdx = args.indexOf('--skill');
const skillFilter = filterIdx !== -1 ? args[filterIdx + 1] : null;

// ── helpers ───────────────────────────────────────────────────────────────────

function findEvalFiles() {
  const result = spawnSync(
    'find',
    [join(REPO_ROOT, 'skills'), '-name', '*.eval.json', '-print'],
    { encoding: 'utf8' }
  );
  const files = result.stdout.trim().split('\n').filter(Boolean).sort();
  if (!skillFilter) return files;
  return files.filter(f => f.includes(`/${skillFilter}/`));
}

function readSkillMd(skillPath) {
  const p = join(REPO_ROOT, skillPath, 'SKILL.md');
  return readFileSync(p, 'utf8');
}

function runClaude(prompt) {
  // Pass prompt via stdin to avoid CLI option parsing issues when the prompt
  // starts with `---` (SKILL.md frontmatter is misread as an unknown flag).
  // --tools "" disables all tools so the model can't block on tool-use approval
  // when a skill's instructions reference bash commands or file reads.
  const result = spawnSync('claude', ['--print', '--model', MODEL, '--tools', ''], {
    input: prompt,
    encoding: 'utf8',
    timeout: CLAUDE_TIMEOUT_MS,
    maxBuffer: 10 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`claude exited ${result.status}: ${result.stderr}`);
  return result.stdout;
}

function applyCheck(check, response) {
  switch (check.type) {
    case 'contains': {
      const passed = response.includes(check.value);
      return { passed, detail: passed ? `found "${check.value}"` : `missing "${check.value}"` };
    }
    case 'not_contains': {
      const passed = !response.includes(check.value);
      return { passed, detail: passed ? `correctly absent "${check.value}"` : `unexpected "${check.value}" found` };
    }
    case 'regex': {
      const passed = new RegExp(check.pattern, check.flags ?? '').test(response);
      return { passed, detail: passed ? 'regex matched' : `regex did not match: ${check.pattern}` };
    }
    case 'rubric': {
      const judgePrompt =
        `Response to evaluate:\n\n${response}\n\n---\n\n` +
        `Criteria: ${check.criteria}\n\n` +
        `Does the response satisfy the criteria? ` +
        `Answer YES or NO on the first line, then explain in one sentence.`;
      const judgment = runClaude(judgePrompt).trim();
      const passed = /^yes/i.test(judgment);
      const detail = judgment.split('\n').slice(0, 2).join(' ').slice(0, 200);
      return { passed, detail };
    }
    default:
      return { passed: false, detail: `unknown check type: ${check.type}` };
  }
}

function runCase(testCase, skillContent) {
  const prompt =
    `${skillContent}\n\n---\n\n` +
    `User request: ${testCase.prompt}\n\n` +
    `Please respond to the user request above, following the skill instructions exactly.`;

  let response, callError;
  try {
    response = runClaude(prompt);
  } catch (e) {
    callError = e.message;
  }

  if (callError) {
    return { id: testCase.id, description: testCase.description, passed: false, error: callError, checks: [], response: null };
  }

  const checkResults = testCase.checks.map(c => ({ type: c.type, ...applyCheck(c, response) }));
  const passed = checkResults.every(r => r.passed);
  return {
    id: testCase.id,
    description: testCase.description,
    passed,
    error: null,
    checks: checkResults,
    response: response.slice(0, 600),
  };
}

function runEvalFile(evalPath) {
  const evalData = JSON.parse(readFileSync(evalPath, 'utf8'));
  const skillContent = readSkillMd(evalData.skill_path);
  const relPath = evalPath.replace(REPO_ROOT + '/', '');

  console.log(`\n▶ ${evalData.skill}  (${relPath})`);

  const caseResults = [];
  for (const testCase of evalData.cases) {
    process.stdout.write(`  ${testCase.id} ... `);
    const result = runCase(testCase, skillContent);
    caseResults.push(result);
    console.log(result.passed ? '✓' : `✗  ${result.checks.find(c => !c.passed)?.detail ?? result.error}`);
  }

  const passed = caseResults.every(c => c.passed);
  return { skill: evalData.skill, eval_file: relPath, passed, cases: caseResults };
}

// ── main ──────────────────────────────────────────────────────────────────────

const evalFiles = findEvalFiles();
if (evalFiles.length === 0) {
  console.log(skillFilter ? `No eval files found for skill "${skillFilter}".` : 'No .eval.json files found.');
  process.exit(0);
}

const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const allResults = { timestamp, model: MODEL, skills: [] };

let totalCases = 0;
let passedCases = 0;

for (const evalFile of evalFiles) {
  const skillResult = runEvalFile(evalFile);
  allResults.skills.push(skillResult);
  for (const c of skillResult.cases) {
    totalCases++;
    if (c.passed) passedCases++;
  }
}

mkdirSync(join(REPO_ROOT, 'eval-results'), { recursive: true });
const outPath = join(REPO_ROOT, 'eval-results', `${timestamp}.json`);
writeFileSync(outPath, JSON.stringify(allResults, null, 2));

const label = passedCases === totalCases ? '✓ all passed' : `✗ ${totalCases - passedCases} failed`;
console.log(`\n── eval: ${passedCases}/${totalCases} cases  ${label}`);
console.log(`── results → eval-results/${timestamp}.json`);

if (passedCases < totalCases) process.exit(1);
