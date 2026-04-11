import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const repoRoot = resolve(import.meta.dirname, '..')
const packageJsonPath = resolve(repoRoot, 'package.json')
const pyprojectPath = resolve(repoRoot, 'pyproject.toml')

const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf8'))
const nextVersion = packageJson.version

if (typeof nextVersion !== 'string' || nextVersion.length === 0) {
  throw new Error('package.json version is missing or invalid')
}

const pyproject = readFileSync(pyprojectPath, 'utf8')
const versionPattern = /(\[project\][\s\S]*?^version\s*=\s*")([^"]+)(")/m

if (!versionPattern.test(pyproject)) {
  throw new Error('Could not locate [project].version in pyproject.toml')
}

const updatedPyproject = pyproject.replace(versionPattern, `$1${nextVersion}$3`)

writeFileSync(pyprojectPath, updatedPyproject)