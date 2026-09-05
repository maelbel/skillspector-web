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
    },
    button: {
      slots: {
        base: 'cursor-pointer'
      }
    },
    select: {
      slots: {
        base: 'cursor-pointer',
        item: 'cursor-pointer'
      }
    },
    switch: {
      slots: {
        base: 'cursor-pointer',
        label: 'cursor-pointer'
      }
    }
  }
})
