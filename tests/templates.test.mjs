import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { load } from 'js-yaml'

const root        = path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
const templateDir = path.join(root, 'skills/coding/init-project/assets/templates')
const index       = JSON.parse(readFileSync(path.join(root, 'skills-index.json'), 'utf8'))
const knownSkills = new Set(index.skills.map(s => path.basename(s.path)))

const templates = readdirSync(templateDir)
  .filter(f => f.endsWith('.yml'))
  .map(f => ({ file: f, doc: load(readFileSync(path.join(templateDir, f), 'utf8')) }))

test('模板目录至少有一套模板', () => {
  assert.ok(templates.length > 0, `没有 .yml 模板：${templateDir}`)
})

for (const { file, doc } of templates) {
  test(`${file}: name + 五段齐全`, () => {
    for (const key of ['name', 'scaffold', 'skills', 'init_phases', 'language_hints', 'register']) {
      assert.notEqual(doc[key], undefined, `缺顶层字段: ${key}`)
    }
  })

  test(`${file}: init_phases 引用的 skill 必须在 skills 清单里`, () => {
    const declared = new Set(doc.skills)
    for (const phase of doc.init_phases) {
      assert.ok(declared.has(phase.skill), `init_phases 引用了未声明的 skill: ${phase.skill}`)
    }
  })

  test(`${file}: skills 清单里每个名字都能在 skills-index.json 查到`, () => {
    for (const name of doc.skills) {
      assert.ok(knownSkills.has(name), `skills-index.json 里没有这个 skill: ${name}`)
    }
  })

  test(`${file}: on_exists 取值合法`, () => {
    for (const f of doc.scaffold.files) {
      if (f.on_exists === undefined) continue
      assert.ok(['skip', 'append-missing-lines'].includes(f.on_exists),
        `${f.path}: 非法 on_exists=${f.on_exists}`)
    }
  })

  test(`${file}: scaffold.files 的 from 路径都存在`, () => {
    const assetDir = path.join(templateDir, '..')
    for (const f of doc.scaffold.files) {
      const src = path.join(assetDir, f.from)
      assert.ok(existsSync(src), `找不到骨架资产: ${f.from}`)
    }
  })
}
