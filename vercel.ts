import type { VercelConfig } from '@vercel/config/v1'

// The hosted (Vercel) deployment. Docker Compose installs don't read this file.
export default {
  crons: [
    // Retention sweep (server/api/internal/retention.get.ts). Daily, the most often every Vercel
    // plan allows; changing the retention from the admin page also sweeps straight away.
    { path: '/api/internal/retention', schedule: '0 3 * * *' }
  ]
} satisfies VercelConfig
