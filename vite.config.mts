import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const UNKNOWN_COMMIT_HASH = 'git-unavailable'
const UNKNOWN_PACKAGE_VERSION = 'package-version-unavailable'

function resolveBuildInfo() {
    let packageVersion = UNKNOWN_PACKAGE_VERSION

    try {
        const packageJson = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')) as {
            version?: string
        }
        packageVersion = packageJson.version?.trim() || UNKNOWN_PACKAGE_VERSION
    } catch {
        packageVersion = UNKNOWN_PACKAGE_VERSION
    }

    let commitHash = UNKNOWN_COMMIT_HASH

    try {
        const resolvedHash = execSync('git rev-parse --short=12 HEAD', {
            encoding: 'utf8',
            stdio: ['ignore', 'pipe', 'ignore']
        }).trim()
        commitHash = resolvedHash || UNKNOWN_COMMIT_HASH
    } catch {
        commitHash = UNKNOWN_COMMIT_HASH
    }

    return {
        commitHash,
        packageVersion
    }
}

export default defineConfig(async ({ command }) => {
    const plugins = [vue()]
    const buildInfo = resolveBuildInfo()

    if (command === 'serve') {
        const { default: vueDevTools } = await import('vite-plugin-vue-devtools')
        plugins.push(vueDevTools())
    }

    return {
        define: {
            __IMAGEGEN_TOOLKIT_BUILD_INFO__: JSON.stringify(buildInfo)
        },
        plugins,
        resolve: {
            alias: {
                '@': fileURLToPath(new URL('./src', import.meta.url))
            },
        },
        build: {
            lib: {
                entry: './src/main.ts',
                formats: ['es'],
                fileName: 'main'
            },
            rollupOptions: {
                external: [
                    '../../../scripts/app.js',
                    '../../../scripts/api.js',
                    '../../../scripts/domWidget.js',
                    '../../../scripts/utils.js',
                    'vue',
                    'vue-i18n',
                    /^primevue\/?.*/,
                    /^@primevue\/themes\/?.*/,
                ],
                output: {
                    dir: 'js',
                    assetFileNames: 'assets/[name].[ext]',
                    entryFileNames: 'main.js'
                }
            },
            outDir: 'js',
            sourcemap: false,
            assetsInlineLimit: 0,
            cssCodeSplit: false
        }
    }
})