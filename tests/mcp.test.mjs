import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, rmSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { createServer } from '../lib/mcp-server.js'

async function connectedClient() {
  const server = createServer()
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair()
  const client = new Client({ name: 'test-client', version: '1.0.0' })
  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ])
  return { client, server }
}

test('hskill_list is registered and returns the real skill list as JSON', async () => {
  const { client, server } = await connectedClient()
  try {
    const { tools } = await client.listTools()
    const names = tools.map(t => t.name)
    assert.ok(names.includes('hskill_list'), `expected hskill_list in ${names.join(', ')}`)

    const result = await client.callTool({ name: 'hskill_list', arguments: {} })
    assert.equal(result.isError, undefined)
    const text = result.content[0].text
    const parsed = JSON.parse(text)
    assert.ok(parsed.skills, 'expected a "skills" key in hskill_list output')
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_status returns valid JSON', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_status', arguments: {} })
    assert.equal(result.isError, undefined)
    JSON.parse(result.content[0].text)
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_outdated returns valid JSON', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_outdated', arguments: {} })
    assert.equal(result.isError, undefined)
    JSON.parse(result.content[0].text)
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_info returns detail for a known skill', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_info', arguments: { name: 'survey-skillrepo' } })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.equal(parsed.name, 'survey-skillrepo')
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_info reports an MCP error for an unknown name', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_info', arguments: { name: 'does-not-exist' } })
    assert.equal(result.isError, true)
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_install writes the skill to a mocked HOME', async () => {
  const mockHome = mkdtempSync(path.join(tmpdir(), 'hskill-mcp-test-'))
  const originalHome = process.env.HOME
  process.env.HOME = mockHome
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({
      name: 'hskill_install',
      arguments: { skill: 'survey-skillrepo', target: 'claude', scope: 'user', force: true },
    })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.ok(parsed.skills, 'expected a "skills" key in hskill_install output')
    assert.ok(existsSync(path.join(mockHome, '.claude', 'skills', 'survey-skillrepo', 'SKILL.md')))
  } finally {
    await client.close()
    await server.close()
    process.env.HOME = originalHome
    rmSync(mockHome, { recursive: true, force: true })
  }
})

test('hskill_uninstall removes a previously installed skill', async () => {
  const mockHome = mkdtempSync(path.join(tmpdir(), 'hskill-mcp-test-'))
  const originalHome = process.env.HOME
  process.env.HOME = mockHome
  const { client, server } = await connectedClient()
  try {
    await client.callTool({
      name: 'hskill_install',
      arguments: { skill: 'survey-skillrepo', target: 'claude', scope: 'user', force: true },
    })
    assert.ok(existsSync(path.join(mockHome, '.claude', 'skills', 'survey-skillrepo')))

    const result = await client.callTool({
      name: 'hskill_uninstall',
      arguments: { name: 'survey-skillrepo', scope: 'user', target: 'claude' },
    })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.equal(parsed.removed, true)
    assert.ok(!existsSync(path.join(mockHome, '.claude', 'skills', 'survey-skillrepo')))
  } finally {
    await client.close()
    await server.close()
    process.env.HOME = originalHome
    rmSync(mockHome, { recursive: true, force: true })
  }
})

test('hskill_hooks list returns valid JSON with a hooks array', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_hooks', arguments: { action: 'list' } })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.ok(Array.isArray(parsed.hooks))
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_hooks install then uninstall round-trips in a mocked HOME', async () => {
  const mockHome = mkdtempSync(path.join(tmpdir(), 'hskill-mcp-test-'))
  const originalHome = process.env.HOME
  process.env.HOME = mockHome
  const { client, server } = await connectedClient()
  try {
    const installResult = await client.callTool({
      name: 'hskill_hooks',
      arguments: { action: 'install', name: 'check-similar-branch', scope: 'user' },
    })
    assert.equal(installResult.isError, undefined)
    const installed = JSON.parse(installResult.content[0].text)
    assert.ok(installed.installed.includes('check-similar-branch'))

    const uninstallResult = await client.callTool({
      name: 'hskill_hooks',
      arguments: { action: 'uninstall', name: 'check-similar-branch', scope: 'user' },
    })
    assert.equal(uninstallResult.isError, undefined)
    const uninstalled = JSON.parse(uninstallResult.content[0].text)
    assert.equal(uninstalled.removed, true)
  } finally {
    await client.close()
    await server.close()
    process.env.HOME = originalHome
    rmSync(mockHome, { recursive: true, force: true })
  }
})

test('hskill_update is registered with a description warning about irreversibility', async () => {
  const { client, server } = await connectedClient()
  try {
    const { tools } = await client.listTools()
    const updateTool = tools.find(t => t.name === 'hskill_update')
    assert.ok(updateTool, 'expected hskill_update to be registered')
    assert.match(updateTool.description, /irreversible/i)
    // Deliberately not calling this tool: it runs a real `npm install -g`
    // against the environment's actual global npm prefix.
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill mcp subcommand: spawns a real MCP server over stdio and serves hskill_list', async () => {
  const cliPath = new URL('../bin/cli.js', import.meta.url).pathname
  const transport = new StdioClientTransport({ command: process.execPath, args: [cliPath, 'mcp'] })
  const client = new Client({ name: 'test-client', version: '1.0.0' })
  await client.connect(transport)
  try {
    const { tools } = await client.listTools()
    assert.ok(tools.some(t => t.name === 'hskill_list'))
    const result = await client.callTool({ name: 'hskill_list', arguments: {} })
    assert.equal(result.isError, undefined)
    JSON.parse(result.content[0].text)
  } finally {
    await client.close()
  }
})
