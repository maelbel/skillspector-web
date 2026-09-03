export default defineAppConfig({
  site: {
    name: 'Skillspector Web',
    description: 'Scan agent skills for vulnerabilities before you install them.',
    repo: 'maelbel/skillspector-web',
    scannerRepo: 'NVIDIA/skillspector'
  },
  ui: {
    colors: {
      primary: 'green',
      neutral: 'slate'
    }
  }
})
