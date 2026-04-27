import fs from 'fs-extra'
import path from 'path'
import { confirm } from '@inquirer/prompts'
import chalk from 'chalk'

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

      await fs.copy(srcPath, destPath, { overwrite: true })
      installed.push(skillName)
    }

    if (installed.length > 0) {
      summary[targetName] = installed
    }
  }

  return summary
}
