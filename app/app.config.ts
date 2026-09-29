export default defineAppConfig({
  site: {
    name: 'Skillspector Web',
    description: 'Scan agent skills for vulnerabilities before you install them.',
    repo: 'maelbel/skillspector-web',
    scannerRepo: 'NVIDIA/skillspector'
  },
  ui: {
    colors: {
      primary: 'matcha',
      neutral: 'oat',
      success: 'matcha',
      warning: 'amber',
      error: 'red'
    },
    button: {
      slots: {
        base: 'cursor-pointer rounded-full'
      }
    },
    input: {
      slots: {
        base: 'rounded-xl'
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
