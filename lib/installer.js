import fs from 'fs-extra'
import os from 'os'
import path from 'path'
import { confirm } from '@inquirer/prompts'
import chalk from 'chalk'
import { loadVarDefs, buildAutoVars, resolveVars, substituteVars } from './vars.js'
import { readVersion } from './bundles.js'

const BINARY_EXTS = new Set(['.db', '.pyc', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf'])
const SKIP_NAMES  = new Set(['vars.json', '__pycache__', '.DS_Store'])

async function copyDir(srcDir, destDir, varsMap) {
  await fs.ensureDir(destDir)
  const entries = await fs.readdir(srcDir, { withFileTypes: true })
  for (const entry of entries) {
    if (SKIP_NAMES.has(entry.name)) continue
    const src  = path.join(srcDir, entry.name)
    const dest = path.join(destDir, entry.name)
    if (entry.isDirectory()) {
      await copyDir(src, dest, varsMap)
    } else if (Object.keys(varsMap).length > 0 && !BINARY_EXTS.has(path.extname(entry.name).toLowerCase())) {
      const content = await fs.readFile(src, 'utf-8').catch(e => { throw new Error(`Failed to read ${src}: ${e.message}`) })
      await fs.writeFile(dest, substituteVars(content, varsMap), 'utf-8')
    } else {
      await fs.copy(src, dest, { overwrite: true })
    }
  }
}

// tools: [{ toolName, srcPath }]
// targetDir: string — path to ~/.local/bin
// force: boolean
export async function installTools(tools, targetDir, force = false) {
  const exists = await fs.pathExists(targetDir)
  if (!exists) {
    console.error(chalk.dim(`  · Creating directory: ${targetDir}`))
    await fs.ensureDir(targetDir)
  }

  const installed = []
  const skipped   = []
  const failed    = []

  for (const { toolName, srcPath } of tools) {
    const scriptSrc = path.join(srcPath, `${toolName}.sh`)
    const destPath  = path.join(targetDir, toolName)

    if (!await fs.pathExists(scriptSrc)) {
      console.error(chalk.red(`  ✗ Script not found: ${scriptSrc}`))
      failed.push({ name: toolName, reason: 'source_not_found' })
      continue
    }

    const destExists = await fs.pathExists(destPath)
    if (destExists && !force) {
      if (!process.stdout.isTTY) {
        skipped.push({ name: toolName, reason: 'already_exists' })
        console.error(chalk.dim(`  · Skipped ${toolName} (already exists — use --force to overwrite)`))
        continue
      }
      const ok = await confirm({ message: `${destPath} already exists. Overwrite?`, default: true })
      if (!ok) {
        skipped.push({ name: toolName, reason: 'already_exists' })
        console.error(chalk.dim(`  · Skipped ${toolName}`))
        continue
      }
    }

    try {
      const varDefs = await loadVarDefs(srcPath)
      let varsMap = {}
      if (varDefs.length > 0) {
        if (!process.stdout.isTTY) {
          const autoVars = buildAutoVars()
          for (const def of varDefs) {
            autoVars[def.name] = substituteVars(def.default ?? '', autoVars)
          }
          varsMap = autoVars
          console.error(chalk.dim(`  · ${toolName}: using default vars (non-TTY)`))
        } else {
          console.error(chalk.bold(`\n  Configure ${toolName}:`))
          varsMap = await resolveVars(varDefs, buildAutoVars())
          for (const def of varDefs) {
            if (def.configFile && def.configKey) {
              await _writeToolConfigVar(def, varsMap[def.name])
            }
          }
        }
      }
      const content = await fs.readFile(scriptSrc, 'utf-8')
      await fs.writeFile(destPath, substituteVars(content, varsMap), { encoding: 'utf-8', mode: 0o755 })

      const toolJsonSrc = path.join(srcPath, 'tool.json')
      if (await fs.pathExists(toolJsonSrc)) {
        const dataDir = path.join(os.homedir(), '.local', 'share', 'hskill', 'tools')
        await fs.ensureDir(dataDir)
        await fs.copy(toolJsonSrc, path.join(dataDir, `${toolName}.json`))
      }

      installed.push(toolName)
      await _patchZshrc(srcPath, toolName)
    } catch (err) {
      console.error(chalk.red(`  ✗ Failed to install ${toolName}: ${err.message}`))
      failed.push({ name: toolName, reason: 'copy_failed', detail: err.message })
    }
  }

  return { installed, skipped, failed }
}

async function _writeToolConfigVar(def, value) {
  const configPath = def.configFile.replace(/^~/, os.homedir())
  await fs.ensureDir(path.dirname(configPath))
  await fs.writeFile(configPath, `${def.configKey}=("${value}")\n`, 'utf-8')
  console.error(chalk.green(`  ✓ Config written to ${def.configFile}`))
}

async function _patchZshrc(srcPath, toolName) {
  const snippetPath = path.join(srcPath, 'zshrc.snippet')
  if (!await fs.pathExists(snippetPath)) return

  const zshrcPath = path.join(os.homedir(), '.zshrc')
  const marker = `# >>> ${toolName}`

  const existing = await fs.pathExists(zshrcPath)
    ? await fs.readFile(zshrcPath, 'utf-8')
    : ''

  if (existing.includes(marker)) {
    console.error(chalk.dim(`  · ~/.zshrc already has ${toolName} config, skipping`))
    return
  }

  if (!process.stdout.isTTY) {
    console.error(chalk.dim(`  · Skipped ~/.zshrc patch for ${toolName} (non-TTY — add manually)`))
    return
  }

  const ok = await confirm({
    message: `Add ${toolName} PATH and alias to ~/.zshrc?`,
    default: true,
  })
  if (!ok) return

  const snippet = await fs.readFile(snippetPath, 'utf-8')
  await fs.appendFile(zshrcPath, snippet, 'utf-8')
  console.error(chalk.green(`  ✓ Written to ~/.zshrc`))
}

// skills: [{ skillName, srcPath }]
// targets: [{ name, dir }]
// force: boolean
export async function installSkills(skills, targets, force = false) {
  const summary = {}

  for (const { name: targetName, dir: targetDir } of targets) {
    const exists = await fs.pathExists(targetDir)
    if (!exists) {
      console.error(chalk.dim(`  · Creating directory: ${targetDir}`))
      await fs.ensureDir(targetDir)
    }

    const installed = []
    const skipped   = []
    const failed    = []

    for (const { skillName, srcPath, version: availableVersion } of skills) {
      if (!await fs.pathExists(srcPath)) {
        console.error(chalk.red(`  ✗ Source not found: ${srcPath}`))
        failed.push({ name: skillName, reason: 'source_not_found' })
        continue
      }

      const destPath   = path.join(targetDir, skillName)
      const destExists = await fs.pathExists(destPath)

      if (destExists && !force) {
        const installedVersion = readVersion(destPath)
        if (availableVersion && installedVersion === availableVersion) {
          skipped.push({ name: skillName, reason: 'up-to-date', version: installedVersion })
          console.error(chalk.dim(`  · Skipped ${skillName} (up-to-date ${installedVersion})`))
          continue
        }

        if (!process.stdout.isTTY) {
          skipped.push({
            name: skillName, reason: 'outdated',
            installed: installedVersion, available: availableVersion ?? '—',
          })
          console.error(chalk.dim(`  · Skipped ${skillName} (outdated ${installedVersion} → ${availableVersion ?? '—'}, use --force to overwrite)`))
          continue
        }

        const ok = await confirm({
          message: `${targetName}/${skillName} ${installedVersion} → ${availableVersion ?? '?'}. Overwrite?`,
          default: false,
        })
        if (!ok) {
          skipped.push({
            name: skillName, reason: 'outdated',
            installed: installedVersion, available: availableVersion ?? '—',
          })
          console.error(chalk.dim(`  · Skipped ${skillName}`))
          continue
        }
      }

      try {
        const varDefs = await loadVarDefs(srcPath)
        let varsMap = {}
        if (varDefs.length > 0) {
          if (!process.stdout.isTTY) {
            const autoVars = buildAutoVars()
            for (const def of varDefs) {
              autoVars[def.name] = substituteVars(def.default ?? '', autoVars)
            }
            varsMap = autoVars
            console.error(chalk.dim(`  · ${skillName}: using default vars (non-TTY)`))
          } else {
            console.error(chalk.bold(`\n  Configure ${skillName}:`))
            varsMap = await resolveVars(varDefs, buildAutoVars())
          }
        }
        await copyDir(srcPath, destPath, varsMap)
        installed.push(skillName)
      } catch (err) {
        console.error(chalk.red(`  ✗ Failed to copy ${targetName}/${skillName}: ${err.message}`))
        failed.push({ name: skillName, reason: 'copy_failed', detail: err.message })
      }
    }

    summary[targetName] = { installed, skipped, failed }
  }

  return summary
}

// ── Hooks ────────────────────────────────────────────────────────────────────

function _hooksDir(scope, projectDir) {
  return scope === 'user'
    ? path.join(os.homedir(), '.claude', 'hooks')
    : path.join(projectDir, '.claude', 'hooks')
}

function _settingsPath(scope, projectDir) {
  return scope === 'user'
    ? path.join(os.homedir(), '.claude', 'settings.json')
    : path.join(projectDir, '.claude', 'settings.json')
}

function _hookCommand(hookName, scope) {
  return scope === 'user'
    ? `bash ~/.claude/hooks/${hookName}.sh`
    : `bash "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/${hookName}.sh"`
}

async function _patchSettings(settingsPath, hook, scope, force) {
  let settings = {}
  try {
    settings = JSON.parse(await fs.readFile(settingsPath, 'utf-8'))
  } catch { /* 文件不存在时从空对象开始 */ }

  if (!settings.hooks) settings.hooks = {}
  if (!settings.hooks[hook.event]) settings.hooks[hook.event] = []

  const command = _hookCommand(hook.name, scope)

  // 检查是否已有相同 command
  const alreadyRegistered = settings.hooks[hook.event].some(entry =>
    Array.isArray(entry.hooks) && entry.hooks.some(h => h.command === command)
  )

  if (alreadyRegistered && !force) return false
  if (alreadyRegistered && force) {
    settings.hooks[hook.event] = settings.hooks[hook.event].filter(entry =>
      !Array.isArray(entry.hooks) || !entry.hooks.some(h => h.command === command)
    )
  }

  const hookEntry = { type: 'command', command }
  if (hook.timeout)       hookEntry.timeout       = hook.timeout
  if (hook.statusMessage) hookEntry.statusMessage = hook.statusMessage

  settings.hooks[hook.event].push({
    matcher: hook.matcher ?? '',
    hooks: [hookEntry],
  })

  await fs.ensureDir(path.dirname(settingsPath))
  await fs.writeFile(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8')
  return true
}

export async function installHooks(hooks, scope, projectDir, force = false) {
  const hooksDir     = _hooksDir(scope, projectDir)
  const settingsPath = _settingsPath(scope, projectDir)

  await fs.ensureDir(hooksDir)

  const installed = []
  const skipped   = []
  const failed    = []

  for (const hook of hooks) {
    const destScript   = path.join(hooksDir, `${hook.name}.sh`)
    const scriptExists = await fs.pathExists(destScript)

    if (scriptExists && !force) {
      skipped.push({ name: hook.name, reason: 'already_exists' })
      console.error(chalk.dim(`  · Skipped ${hook.name} (already exists — use --force to overwrite)`))
      continue
    }

    try {
      if (!await fs.pathExists(hook.srcPath)) {
        failed.push({ name: hook.name, reason: 'source_not_found' })
        console.error(chalk.red(`  ✗ Source not found: ${hook.srcPath}`))
        continue
      }

      await fs.copy(hook.srcPath, destScript, { overwrite: true })
      await fs.chmod(destScript, 0o755)
      await _patchSettings(settingsPath, hook, scope, force)

      installed.push(hook.name)
      console.error(chalk.green(`  ✓ ${hook.name} → ${destScript}`))
    } catch (err) {
      failed.push({ name: hook.name, reason: 'copy_failed', detail: err.message })
      console.error(chalk.red(`  ✗ Failed to install ${hook.name}: ${err.message}`))
    }
  }

  return { installed, skipped, failed }
}

export async function uninstallHook(hookName, scope, projectDir) {
  const hooksDir     = _hooksDir(scope, projectDir)
  const settingsPath = _settingsPath(scope, projectDir)
  const destScript   = path.join(hooksDir, `${hookName}.sh`)
  let removed = false

  if (await fs.pathExists(destScript)) {
    await fs.remove(destScript)
    removed = true
    console.error(chalk.green(`  ✓ Removed ${destScript}`))
  }

  try {
    const settings = JSON.parse(await fs.readFile(settingsPath, 'utf-8'))
    let changed = false
    for (const event of Object.keys(settings.hooks ?? {})) {
      const before = settings.hooks[event].length
      settings.hooks[event] = settings.hooks[event].filter(entry =>
        !Array.isArray(entry.hooks) ||
        !entry.hooks.some(h => typeof h.command === 'string' && h.command.includes(`${hookName}.sh`))
      )
      if (settings.hooks[event].length !== before) {
        changed = true
        removed = true
        if (settings.hooks[event].length === 0) delete settings.hooks[event]
      }
    }
    if (changed && Object.keys(settings.hooks).length === 0) {
      delete settings.hooks
    }
    if (changed) {
      await fs.writeFile(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8')
      console.error(chalk.green(`  ✓ Unregistered from ${settingsPath}`))
    }
  } catch { /* settings.json 不存在，忽略 */ }

  return { removed }
}
