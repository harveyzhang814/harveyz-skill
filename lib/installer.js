import fs from 'fs-extra'
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
      const content = await fs.readFile(src, 'utf-8')
      await fs.writeFile(dest, substituteVars(content, varsMap), 'utf-8')
    } else {
      await fs.copy(src, dest, { overwrite: true })
    }
  }
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
