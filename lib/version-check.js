const DEFAULT_REGISTRY = 'https://registry.npmjs.org'
const REGISTRY_TIMEOUT_MS = 5000

export function compareVersions(a, b) {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] || 0) - (pb[i] || 0)
    if (diff !== 0) return diff
  }
  return 0
}

export async function checkNpmVersion(pkgName, currentVersion) {
  const registryUrl = process.env.HSKILL_NPM_REGISTRY || DEFAULT_REGISTRY
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REGISTRY_TIMEOUT_MS)
  let res
  try {
    res = await fetch(`${registryUrl}/${pkgName}/latest`, { signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
  if (!res.ok) {
    throw new Error(`npm registry returned ${res.status} for ${pkgName}`)
  }
  const { version: latest } = await res.json()
  return { current: currentVersion, latest, upToDate: compareVersions(currentVersion, latest) >= 0 }
}
