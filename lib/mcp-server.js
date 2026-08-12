import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import { z } from 'zod'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const CLI_PATH = path.join(__dirname, '..', 'bin', 'cli.js')

// Spawns `node bin/cli.js <argv>` and collects its full stdout/stderr/exit code.
// Never rejects — callers branch on `code`.
export function runCli(argv) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [CLI_PATH, ...argv], { stdio: ['ignore', 'pipe', 'pipe'] })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (d) => { stdout += d })
    child.stderr.on('data', (d) => { stderr += d })
    child.on('close', (code) => resolve({ code, stdout, stderr }))
  })
}

// Turns a runCli() result into an MCP CallToolResult. On success, the CLI's
// stdout JSON is forwarded as-is. On failure, stderr is parsed as the CLI's
// existing {error:true,message} shape; if that parse fails, the raw stderr
// text is used so a handler never throws on an unexpected crash.
export function toToolResult({ code, stdout, stderr }) {
  if (code === 0) {
    return { content: [{ type: 'text', text: stdout.trim() || '{}' }] }
  }
  let message = stderr.trim() || `hskill exited with code ${code}`
  const lastLine = stderr.trim().split('\n').pop()
  try {
    const parsed = JSON.parse(lastLine)
    if (parsed && parsed.error) message = parsed.message
  } catch {
    // stderr wasn't JSON — fall back to the raw text already assigned above
  }
  return { content: [{ type: 'text', text: message }], isError: true }
}

export function createServer() {
  const server = new McpServer({ name: 'hskill', version: '1.0.0' })

  server.registerTool('hskill_list', {
    description: 'List all available hskill skills and bundles, with per-target install status.',
    inputSchema: {},
  }, async () => toToolResult(await runCli(['list', '--json'])))

  server.registerTool('hskill_status', {
    description: 'Show install status for all skills, tools, and hooks across every target.',
    inputSchema: {},
  }, async () => toToolResult(await runCli(['status', '--json'])))

  server.registerTool('hskill_outdated', {
    description: 'List only the skills and tools that have an available update.',
    inputSchema: {},
  }, async () => toToolResult(await runCli(['outdated', '--json'])))

  server.registerTool('hskill_info', {
    description: 'Show install detail for one named skill or tool, as returned by hskill_list.',
    inputSchema: {
      name: z.string().describe('Skill or tool name, exactly as shown by hskill_list'),
    },
  }, async ({ name }) => toToolResult(await runCli(['info', name, '--json'])))

  server.registerTool('hskill_install', {
    description: 'Install a skill bundle, a specific skill, or a shell tool. Writes files under ~/.claude/skills (or the equivalent dir for --target) or a project directory. Provide exactly one of bundle, skill, or tool.',
    inputSchema: {
      bundle: z.string().optional().describe('Bundle name(s) to install, comma-separated'),
      skill: z.string().optional().describe('Specific skill name(s) to install, comma-separated'),
      tool: z.string().optional().describe('Specific shell tool name(s) to install, comma-separated'),
      target: z.string().optional().describe('Target host: claude, cursor, codex, opencode, etc., or "all"'),
      scope: z.enum(['user', 'project']).optional().describe('Install scope, defaults to user'),
      force: z.boolean().optional().describe('Overwrite an existing install'),
    },
  }, async ({ bundle, skill, tool, target, scope, force }) => {
    const argv = ['install']
    if (bundle) argv.push('--bundle', bundle)
    if (skill) argv.push('--skill', skill)
    if (tool) argv.push('--tool', tool)
    if (target) argv.push('--target', target)
    if (scope) argv.push('--scope', scope)
    if (force) argv.push('--force')
    argv.push('--json')
    return toToolResult(await runCli(argv))
  })

  return server
}

export async function startServer() {
  const server = createServer()
  const transport = new StdioServerTransport()
  await server.connect(transport)
}
