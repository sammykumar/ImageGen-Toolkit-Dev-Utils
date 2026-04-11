import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(async ({ command }) => {
    const plugins = [vue()]

    if (command === 'serve') {
        const { default: vueDevTools } = await import('vite-plugin-vue-devtools')
        plugins.push(vueDevTools())
    }

    return {
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