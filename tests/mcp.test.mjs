import { test } from 'node:test'
import assert from 'node:assert/strict'
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
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
