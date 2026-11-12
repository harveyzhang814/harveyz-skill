import test from 'node:test'
import assert from 'node:assert/strict'
import { renderTemplate, templateParams, TemplateError } from '../skills/devflow/compose-agentsmd/scripts/lib/template.mjs'

test('substitutes @{name} with string params', () => {
  assert.equal(renderTemplate('branch @{b}.\n', { b: 'staging' }, 'm.md'), 'branch staging.\n')
})
test('leaves {{name}} untouched', () => {
  assert.equal(renderTemplate('{{x}} @{b}\n', { b: 'y' }, 'm.md'), '{{x}} y\n')
})
test('@if on true boolean keeps the if-branch and drops directives', () => {
  const t = 'a\n<!-- @if c -->\nyes\n<!-- @else -->\nno\n<!-- @endif -->\nb\n'
  assert.equal(renderTemplate(t, { c: true }, 'm.md'), 'a\nyes\nb\n')
  assert.equal(renderTemplate(t, { c: false }, 'm.md'), 'a\nno\nb\n')
})
test('@if on string tests non-empty', () => {
  const t = '<!-- @if e -->\nE2E: @{e}\n<!-- @endif -->\n'
  assert.equal(renderTemplate(t, { e: 'playwright' }, 'm.md'), 'E2E: playwright\n')
  assert.equal(renderTemplate(t, { e: '' }, 'm.md'), '')
})
test('collapses consecutive blank lines left by removed blocks', () => {
  const t = 'a\n\n<!-- @if c -->\nx\n<!-- @endif -->\n\nb\n'
  assert.equal(renderTemplate(t, { c: false }, 'm.md'), 'a\n\nb\n')
})
test('unknown parameter throws TemplateError with file and line', () => {
  assert.throws(() => renderTemplate('ok\n@{nope}\n', {}, 'm.md'),
    e => e instanceof TemplateError && e.file === 'm.md' && e.line === 2 && e.message.includes('m.md:2'))
})
test('unclosed @if throws', () => {
  assert.throws(() => renderTemplate('<!-- @if c -->\nx\n', { c: true }, 'm.md'), TemplateError)
})
test('nested @if throws', () => {
  const t = '<!-- @if c -->\n<!-- @if c -->\nx\n<!-- @endif -->\n<!-- @endif -->\n'
  assert.throws(() => renderTemplate(t, { c: true }, 'm.md'), e => e instanceof TemplateError && e.line === 2)
})
test('stray @else / @endif throws', () => {
  assert.throws(() => renderTemplate('<!-- @else -->\n', {}, 'm.md'), TemplateError)
  assert.throws(() => renderTemplate('<!-- @endif -->\n', {}, 'm.md'), TemplateError)
})
test('@if on unknown parameter throws', () => {
  assert.throws(() => renderTemplate('<!-- @if zz -->\nx\n<!-- @endif -->\n', {}, 'm.md'), TemplateError)
})
test('templateParams lists referenced names in order', () => {
  assert.deepEqual(templateParams('<!-- @if c -->\n@{b} @{a} @{b}\n<!-- @endif -->\n', 'm.md'), ['c', 'b', 'a'])
})
