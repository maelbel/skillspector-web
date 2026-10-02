export default defineAppConfig({
  site: {
    name: 'Skillspector Web',
    description: 'Scan agent skills for vulnerabilities before you install them.',
    // The link preview image, 1200×630, rendered by scripts/og-image/render.py.
    ogImage: {
      path: '/og-image.png',
      alt: 'Skillspector Web: Is this skill safe to install? Know whether an AI agent skill is safe before you install it.'
    },
    repo: 'maelbel/skillspector-web',
    scannerRepo: 'NVIDIA/skillspector'
  },
  ui: {
    colors: {
      primary: 'nv',
      neutral: 'graphite',
      success: 'nv',
      warning: 'amber',
      error: 'red'
    },
    button: {
      slots: {
        base: 'cursor-pointer rounded-xs font-semibold'
      },
      // NVIDIA-style call to action: green fill with black text, in both themes.
      compoundVariants: [{
        color: 'primary',
        variant: 'solid',
        class: 'bg-brand text-black hover:bg-nv-400 active:bg-nv-400 disabled:bg-brand aria-disabled:bg-brand focus-visible:outline-brand'
      }]
    },
    input: {
      slots: {
        base: 'rounded-xs'
      }
    },
    link: {
      base: 'cursor-pointer'
    },
    select: {
      slots: {
        base: 'cursor-pointer',
        item: 'cursor-pointer'
      }
    },
    selectMenu: {
      slots: {
        base: 'cursor-pointer',
        item: 'cursor-pointer'
      }
    },
    // The field itself is typed in; its toggle and items are clicked.
    inputMenu: {
      slots: {
        trailing: 'cursor-pointer',
        item: 'cursor-pointer'
      }
    },
    dropdownMenu: {
      slots: {
        item: 'cursor-pointer'
      }
    },
    checkbox: {
      slots: {
        base: 'cursor-pointer',
        label: 'cursor-pointer'
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
