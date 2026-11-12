#!/usr/bin/env node
// CLI：node compose-agentsmd.mjs <init|generate|check> [--root <dir>] [--force]
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { runInit, runGenerate, runCheck } from './lib/compose.mjs'

const packsDir = fileURLToPath(new URL('../assets/packs', import.meta.url))
const USAGE = 'usage: compose-agentsmd.mjs <init|generate|check> [--root <dir>] [--force]'

function parse(argv) {
  const [command, ...rest] = argv
  const opts = { root: process.cwd(), force: false }
  for (let i = 0; i < rest.length; i++) {
    if (rest[i] === '--root' && rest[i + 1] !== undefined) opts.root = resolve(rest[++i])
    else if (rest[i] === '--force') opts.force = true
    else return null
  }
  return { command, ...opts }
}

const args = parse(process.argv.slice(2))
const commands = {
  init: o => runInit({ root: o.root }),
  generate: o => runGenerate({ root: o.root, packsDir, force: o.force }),
  check: o => runCheck({ root: o.root, packsDir }),
}
if (!args || !commands[args.command]) {
  console.error(USAGE)
  process.exit(2)
}
const { code, lines, errors = [] } = commands[args.command](args)
if (lines.length) console.log(lines.join('\n'))
if (errors.length) console.error(errors.join('\n'))
process.exitCode = code
