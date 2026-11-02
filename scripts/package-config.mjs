import upstream from '../source/desktop/electron-builder.config.js'

// Public build profile; keep the authenticated privacy source files unchanged.
// The pinned base source has no sharp imports. Its native payload was still
// being collected from production dependencies for both installed CPU variants.
export default {
  ...upstream,
  compression: 'maximum',
  electronLanguages: [
    'ar', 'en', 'en-US', 'ja', 'ru',
    'zh-CN', 'zh_CN', 'zh-Hans', 'zh-TW', 'zh_TW', 'zh-Hant', 'Base',
  ],
  files: [
    ...upstream.files,
    '!**/node_modules/sharp/**/*',
    '!**/node_modules/@img/sharp*/**/*',
  ],
}
