import fs from 'fs-extra'
import os from 'os'
import path from 'path'
import { confirm } from '@inquirer/prompts'
import chalk from 'chalk'
import { loadVarDefs, buildAutoVars, resolveVars, substituteVars } from './vars.js'

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
    console.log(chalk.yellow(`  目录不存在，正在创建：${targetDir}`))
    await fs.ensureDir(targetDir)
  }

  const installed = []
  for (const { toolName, srcPath } of tools) {
    const scriptSrc = path.join(srcPath, `${toolName}.sh`)
    const destPath  = path.join(targetDir, toolName)

    if (!await fs.pathExists(scriptSrc)) {
      console.log(chalk.red(`  脚本不存在：${scriptSrc}`))
      continue
    }

    const destExists = await fs.pathExists(destPath)
    if (destExists && !force) {
      const ok = await confirm({ message: `${destPath} 已存在，覆盖？`, default: false })
      if (!ok) {
        console.log(chalk.gray(`  跳过 ${toolName}`))
        continue
      }
    }

    try {
      const varDefs = await loadVarDefs(srcPath)
      let varsMap = {}
      if (varDefs.length > 0) {
        console.log(chalk.cyan(`\n  配置 ${toolName}：`))
        varsMap = await resolveVars(varDefs, buildAutoVars())
      }
      const content = await fs.readFile(scriptSrc, 'utf-8')
      await fs.writeFile(destPath, substituteVars(content, varsMap), { encoding: 'utf-8', mode: 0o755 })
      installed.push(toolName)
      await _patchZshrc(srcPath, toolName)
    } catch (err) {
      console.log(chalk.red(`  安装失败 ${toolName}: ${err.message}`))
    }
  }

  return installed
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
    console.log(chalk.dim(`  .zshrc 中已有 ${toolName} 配置，跳过`))
    return
  }

  const ok = await confirm({
    message: `是否将 ${toolName} 的 PATH 和 alias 自动写入 ~/.zshrc？`,
    default: true,
  })
  if (!ok) return

  const snippet = await fs.readFile(snippetPath, 'utf-8')
  await fs.appendFile(zshrcPath, snippet, 'utf-8')
  console.log(chalk.green(`  ✓ 已写入 ~/.zshrc（重开终端或 source ~/.zshrc 后生效）`))
}

// skills: [{ skillName, srcPath }]
// targets: [{ name, dir }]
// force: boolean
export async function installSkills(skills, targets, force = false) {
  const summary = {}

  for (const { name: targetName, dir: targetDir } of targets) {
    const exists = await fs.pathExists(targetDir)
    if (!exists) {
      console.log(chalk.yellow(`  跳过 ${targetName}（目录不存在：${targetDir}）`))
      continue
    }

    const installed = []
    for (const { skillName, srcPath } of skills) {
      const destPath = path.join(targetDir, skillName)
      const destExists = await fs.pathExists(destPath)

      if (destExists && !force) {
        const ok = await confirm({ message: `${targetName}/${skillName} 已存在，覆盖？`, default: false })
        if (!ok) {
          console.log(chalk.gray(`  跳过 ${targetName}/${skillName}`))
          continue
        }
      }

      if (!await fs.pathExists(srcPath)) {
        console.log(chalk.red(`  源目录不存在：${srcPath}`))
        continue
      }

      try {
        const varDefs = await loadVarDefs(srcPath)
        let varsMap = {}
        if (varDefs.length > 0) {
          console.log(chalk.cyan(`\n  配置 ${skillName}：`))
          varsMap = await resolveVars(varDefs, buildAutoVars())
        }
        await copyDir(srcPath, destPath, varsMap)
        installed.push(skillName)
      } catch (err) {
        console.log(chalk.red(`  复制失败 ${targetName}/${skillName}: ${err.message}`))
      }
    }

    if (installed.length > 0) {
      summary[targetName] = installed
    }
  }

  return summary
}
