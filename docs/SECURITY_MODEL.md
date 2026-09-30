# Security model

Skillspector Web is designed for a trusted audience — yourself, a team, a homelab. What is and
isn't protected:

- **Authentication is your choice.** With `AUTH=none` (the self-hosted default) there's no
  sign-in: anyone who can reach the UI can run, read and delete every scan and use the admin page,
  including the server's Claude login. Keep it on a private network or behind your reverse proxy's
  authentication (for example Authentik or Authelia forward-auth). With `AUTH=accounts`:
  - Every page needs a sign-in. Scans belong to the user who ran them, and a user can't see,
    open or delete anyone else's (the API answers `404`). Admins see every scan, including ones
    from before accounts were turned on, and manage users, retention and the Claude login.
  - Passwords are hashed with scrypt. Sessions are random tokens stored only as SHA-256 hashes,
    kept in an `httpOnly`, `SameSite=Lax` cookie that page scripts can't read, and expire after
    `SESSION_DAYS`.
  - Sign-in and password-reset attempts are rate-limited per client IP.
  - **Forgotten passwords:** reset links are one-time, valid for 24 hours, stored only as a hash,
    and cancelled by a newer link. Using one signs the person out everywhere else.
    - With SMTP configured, "Forgot password?" on the sign-in page emails a link. The answer and
      its timing are the same whether or not the address has an account, and links always use
      `PUBLIC_URL`, never the request's `Host` header.
    - Without SMTP, an admin copies a link from the user's page in the backoffice and passes it on.
    - Anyone signed in can change their password from the Account page.
    - An admin locked out of their own account can print a link on the server:
      `docker exec skillspector-api uv run python -m app.auth.reset_link you@example.com`.
  - **Backoffice** (`/admin`, admins only):
    - An overview, and a user directory with each user's role, status, scans and last sign-in.
    - Per-user actions: promote or demote, suspend (which signs them out and blocks sign-in) or
      reactivate, send or copy a reset link, delete. Admins can't demote, suspend or delete
      themselves, and there's always at least one active admin.
    - An activity log of who created, changed, suspended, reset or deleted what, and when.
    - Server settings: sign-up, scan quotas and pausing, email status, retention and the Claude
      login.
- **The server's Claude login is shared.** When it's signed in, every visitor can run
  Claude-backed scans on it.
- **Scan targets are constrained** by skillspector: https only, an allowlist of Git and download
  hosts, private and internal addresses refused, no redirects followed, and size limits on clones,
  archives and downloads.
- **Where scans run.** Self-hosted, targets are fetched and analysed inside the API process. With
  `SCAN_EXECUTOR=sandbox` (the hosted default) each scan runs in its own short-lived Vercel Sandbox
  microVM instead: booted from a snapshot, 2 vCPUs, stopped after `SANDBOX_TIMEOUT_SECONDS`, outbound
  traffic limited to the code hosts above with private address ranges blocked, and nothing from
  the app's environment passed in.
- **Custom AI base URLs are not restricted.** A visitor-supplied Base URL makes the server send
  requests to that address — another reason not to expose the app without authentication.
- **API keys.**
  - A key pasted for one scan is held in memory only while that scan runs. On a hosted server,
    whose queue can't hold it in memory, it's kept encrypted until the scan has run, then deleted.
  - A Claude key a user saves to their account (Account → Claude) is checked with Anthropic,
    encrypted with `SECRET_KEY` and bound to that user, and only ever shown back as a hint
    (`…a1b2`). It's decrypted only for that user's own scans, and deleted on disconnect or
    account deletion.
  - Keys never appear in API responses, including validation errors, nor in logs, the activity
    log or browser storage.
  - In a hosted sandbox the key doesn't even enter the VM: the sandbox firewall adds it to requests
    to `api.anthropic.com`.
  - Hosted servers offer Claude only, with no shared Claude login and no custom base URLs.
- **Abuse limits.** Scans are limited per signed-in user, and per client IP across every account
  signed in from it; sign-in, sign-up and password reset attempts per client IP. A refused request
  gets a `429` saying when to try again.
  - **Quotas** (on by default when hosted) cap each user's scans per 24 hours and in progress at
    once, and users see their usage on the Account page. Admins have no quota.
  - **Pausing:** an admin can pause new scans for everyone from the backoffice (Settings → Scans),
    without a redeploy. New scans then get a `503`, and scans already running finish.
  - AI review always runs on the user's own Claude key when hosted, so its cost stays theirs.
  - Hosted, the counts live in the database so they hold across instances, BotID screens scan
    submissions, and Vercel Firewall rules add an edge-level limit in front (see
    [VERCEL_FIREWALL.md](./VERCEL_FIREWALL.md)).

Found a vulnerability? Please report it privately — see [SECURITY.md](../SECURITY.md).
