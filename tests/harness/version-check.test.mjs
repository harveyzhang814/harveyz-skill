import { test } from 'node:test'
import assert from 'node:assert/strict'
import { compareVersions, checkNpmVersion } from '../../lib/version-check.js'

test('compareVersions：版本相同返回 0', () => {
  assert.equal(compareVersions('0.29.0', '0.29.0'), 0)
})

test('compareVersions：本地版本更旧时返回负数', () => {
  assert.ok(compareVersions('0.29.0', '0.30.0') < 0)
})

test('compareVersions：本地版本更新时返回正数', () => {
  assert.ok(compareVersions('1.3.0', '1.2.9') > 0)
})

test('compareVersions：段数不同时缺失段按 0 处理', () => {
  assert.equal(compareVersions('1.2', '1.2.0'), 0)
  assert.ok(compareVersions('1.2.1', '1.2') > 0)
})

test('checkNpmVersion：registry 返回更高版本时 upToDate 为 false，并带出 latest', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => ({
    ok: true,
    json: async () => ({ version: '0.30.0' }),
  }))

  const result = await checkNpmVersion('harveyz-skill', '0.29.0')
  assert.deepEqual(result, { current: '0.29.0', latest: '0.30.0', upToDate: false })
})

test('checkNpmVersion：registry 返回相同版本时 upToDate 为 true', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => ({
    ok: true,
    json: async () => ({ version: '0.29.0' }),
  }))

  const result = await checkNpmVersion('harveyz-skill', '0.29.0')
  assert.deepEqual(result, { current: '0.29.0', latest: '0.29.0', upToDate: true })
})

test('checkNpmVersion：请求带上包名，且遵循 HSKILL_NPM_REGISTRY 覆盖的 base URL', async (t) => {
  let requestedUrl
  t.mock.method(globalThis, 'fetch', async (url) => {
    requestedUrl = url
    return { ok: true, json: async () => ({ version: '0.29.0' }) }
  })
  process.env.HSKILL_NPM_REGISTRY = 'http://127.0.0.1:9999'

  await checkNpmVersion('harveyz-skill', '0.29.0')
  assert.equal(requestedUrl, 'http://127.0.0.1:9999/harveyz-skill/latest')

  delete process.env.HSKILL_NPM_REGISTRY
})

test('checkNpmVersion：registry 返回非 2xx 时抛出带状态码的错误', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => ({ ok: false, status: 404 }))

  await assert.rejects(
    () => checkNpmVersion('harveyz-skill', '0.29.0'),
    /404/,
  )
})

test('checkNpmVersion：fetch 自身抛出网络错误时原样向上抛出', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('network down') })

  await assert.rejects(
    () => checkNpmVersion('harveyz-skill', '0.29.0'),
    /network down/,
  )
})
