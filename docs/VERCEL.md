# Deploying to Vercel (hosted version)

The hosted version runs the same repository as one Vercel project, with
`SKILLSPECTOR_WEB_MODE=hosted`. Docker Compose stays the self-hosted path and is unaffected: it
doesn't read anything described here.

## How it's laid out

[`vercel.ts`](../vercel.ts) defines the project as two [Vercel Services](https://vercel.com/docs/services),
built separately and deployed together:

| Service | Root | What it is | Public? |
|---|---|---|---|
| `web` | `.` | The Nuxt app, including its Nitro `/api/*` routes | Yes: every request lands here |
| `api` | `backend/` | The FastAPI app, plus the queue-triggered function that runs scans | No |

- **The browser never talks to the API.** No public rewrite reaches `api`. The web service calls it
  over a [service binding](https://vercel.com/docs/services/bindings). Vercel puts the binding's URL
  in `NUXT_API_BASE`, and it always points at the same deployment, so a preview's web app calls
  that preview's API.
- **What the `api` service builds** comes from `[tool.vercel]` in `backend/pyproject.toml`:
  - the FastAPI app (`app.main:app`)
  - the scan subscriber (`app.jobs.queue_worker`), a private function that only Vercel Queues can
    invoke
- **Scans** are published to the `scans` Vercel Queues topic. Topics are partitioned by deployment,
  so each deployment runs its own scans. Each scan runs in a Vercel Sandbox microVM booted from
  the snapshot recorded for the deployment's skillspector pin.
- **Vercel Cron** calls the retention sweep daily (`/api/internal/retention`). Cron jobs run on
  production only.

Vercel Queues and Vercel Sandbox authenticate with the deployment's OIDC token. There are no keys
to set for them.

## First deployment

You need:
- a Vercel account with access to Services (beta)
- the [Vercel CLI](https://vercel.com/docs/cli)
- [uv](https://docs.astral.sh/uv/) to build the sandbox snapshot

Run everything from the repository root.

1. **Create and link the project**:

   ```bash
   vercel link             # create a new project; with a GitHub remote it also connects the repository
   vercel api /v9/projects/<project-name> -X PATCH -F framework=services
   ```

   `vercel link` creates the project with the Nuxt preset. The second command switches it to the
   Services preset, which builds both services from `vercel.ts`. You can also switch it in
   **Settings → Build and Deployment → Framework Preset**. Use CLI 62 or later: older versions
   fail to link a project whose `vercel.ts` already defines services.

2. **Create two Postgres databases**, one for production and one for everything else. The prefix
   makes Neon's connection string arrive as `SKILLSPECTOR_WEB_DATABASE_URL`:

   ```bash
   vercel install neon --name skillspector-production --plan free_v3 -e production --prefix SKILLSPECTOR_WEB_
   vercel install neon --name skillspector-preview --plan free_v3 -e preview -e development --prefix SKILLSPECTOR_WEB_
   ```

   `--plan` picks Neon's free plan. Also available: `launch_v3` and `scale_v3`. Each install also
   writes Neon's agent skills (`.agents/`, `.claude/skills/`, `skills-lock.json`) into the working
   directory. They aren't part of this project, so don't commit them.

   Any Postgres works. Set `SKILLSPECTOR_WEB_DATABASE_URL` yourself for another provider. The API
   creates and migrates its tables on startup.

3. **Create a private Blob store for uploads.** Skills uploaded from the browser go straight to it,
   since function request bodies are limited to 4.5 MB, and each one is deleted once it's scanned.
   In the dashboard: **Storage → Create → Blob**, with **Private** access, connected to the project
   for all three environments. The API reads and deletes uploads with `BLOB_READ_WRITE_TOKEN`: check
   that connecting the store set it. Until it's set, the scan form doesn't offer uploads.

4. **Set up the sandbox snapshot.** Scans boot from a snapshot with skillspector preinstalled. Its
   ID is recorded next to the pin it was built from, in `backend/app/sandbox_snapshot_record.py`,
   and every deployment uses the one in its own code. The record in this repository points to a
   snapshot in the maintainer's Vercel team, so on your own project, build one and commit the
   record:

   ```bash
   vercel env run -- sh -c 'cd backend && uv run python -m app.sandbox_snapshot'
   ```

   The build VM installs a C compiler first: some skillspector dependencies have no prebuilt wheel
   for the sandbox image's Python.

   From then on, the **Sandbox snapshot** workflow (`.github/workflows/sandbox-snapshot.yml`)
   rebuilds it whenever a pull request changes the skillspector pin in `backend/pyproject.toml`,
   and commits the new record to the pull request's branch. The previous snapshots are kept, so a
   rollback still boots from its own. The workflow needs, in the GitHub repository's settings
   (**Secrets and variables → Actions**):
   - the secret `VERCEL_TOKEN`, a [Vercel access token](https://vercel.com/account/settings/tokens)
     scoped to the team
   - the variables `VERCEL_TEAM_ID` and `VERCEL_PROJECT_ID`: `orgId` and `projectId` in
     `.vercel/project.json` once the project is linked

   The record's commit is pushed with the workflow's own token, which doesn't start other
   workflows, so CI doesn't rerun on it. Vercel still deploys a preview of it.

5. **Set the environment variables** listed [below](#environment-variables). For each variable
   and environment, run `vercel env add NAME production` (or `preview`, or `development`), which
   prompts for the value. For example:

   ```bash
   vercel env add SKILLSPECTOR_WEB_MODE production           # hosted
   vercel env add SKILLSPECTOR_WEB_SECRET_KEY production --sensitive   # from: cd backend && uv run python -m app.secrets_box
   vercel env add SKILLSPECTOR_WEB_SECRET_KEY preview --sensitive      # a different key
   vercel env add SKILLSPECTOR_WEB_SECRET_KEY development    # the preview key: they share a database
   ```

   Store secrets as sensitive, except in Development, where Vercel doesn't allow sensitive
   variables.

6. **Deploy**:

   ```bash
   vercel deploy           # a preview
   vercel deploy --prod    # production
   ```

   With Git connected, [releases deploy production and `main` deploys preprod](#deployments).
   Set that up once with [the steps below](#setting-up-release-deployments).

7. **Check it**:
   - Open `/api/health`. It should report `"mode": "hosted"` and `"auth": "accounts"`.
   - The first account created becomes the admin.
   - If a setting is missing, the API refuses to start and names it in the function logs.

8. **Add the edge rules** from [VERCEL_FIREWALL.md](./VERCEL_FIREWALL.md).

9. **Check the scan limits** in the backoffice under **Settings → Scans**. Each user gets 10 scans
   per 24 hours and 2 at once until you change them. Pause new scans there if costs run away. It
   takes effect immediately, with no redeploy.

## Environment variables

Every service in the project sees the same variables. Scope each one as shown:
- **All**: Production, Preview and Development.
- **Each**: set in every environment, with a different value for Production than for the others.

| Variable | Scope | Value |
|---|---|---|
| `SKILLSPECTOR_WEB_MODE` | All | `hosted`. It turns on the hosted defaults: accounts, Queues, sandboxed scans, and logs and rate limits in the database. |
| `SKILLSPECTOR_WEB_DATABASE_URL` | Each | Set by the Neon integration (step 2): the production database for Production, the preview database for the others. |
| `SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID` | All | Optional: a snapshot to use when `backend/app/sandbox_snapshot_record.py` is missing. The recorded snapshot always takes priority. |
| `SKILLSPECTOR_WEB_SECRET_KEY` | Each | Encrypts saved Claude keys. Generate with `uv run python -m app.secrets_box` in `backend/`. A separate preview key means a preview can't decrypt production keys even if it were pointed at production data. Keep it: if it changes, users have to connect Claude again. |
| `BLOB_READ_WRITE_TOKEN` | All | Set by connecting the Blob store (step 3). Without it, uploads are off. |
| `CRON_SECRET` | Each | A random string (`openssl rand -hex 32`). Vercel Cron sends it to the retention sweep, and the API refuses to start in hosted mode without it. |
| `NUXT_TRUST_PROXY` | All | `true`. Vercel sets `X-Forwarded-For` to the client's address, and rate limits count by it. |
| `NUXT_PUBLIC_BOTID` | All | `true` turns on [BotID](https://vercel.com/docs/botid) for scan submissions. It's read at build time, so redeploy after changing it. |
| `NUXT_PUBLIC_ANALYTICS` | Production | `true` builds in [Web Analytics](https://vercel.com/docs/analytics): page views and three events (see [What Web Analytics records](./SECURITY_MODEL.md#web-analytics)). Also turn Web Analytics on in the project's **Analytics** tab. Read at build time, so redeploy after changing it. Leaving it off for previews keeps their visits out of the numbers. |
| `NUXT_PUBLIC_SPEED_INSIGHTS` | Production | `true` builds in [Speed Insights](https://vercel.com/docs/speed-insights): Core Web Vitals from real visits, by route. Also turn Speed Insights on in the project's **Speed Insights** tab. Read at build time, so redeploy after changing it. |
| `NUXT_PUBLIC_LEGAL_*` | All | The operator's details for the legal notice, privacy policy and terms of use: at least `NUXT_PUBLIC_LEGAL_OPERATOR_NAME` and `NUXT_PUBLIC_LEGAL_CONTACT_EMAIL`, and for the hosted version the host (Vercel), database (Neon) and email (Mailgun) providers. See [Legal pages](./CONFIGURATION.md#legal-pages). |
| `ENABLE_EXPERIMENTAL_COREPACK` | All | `1`, so the build uses the pnpm version pinned in `package.json`. |
| `SKILLSPECTOR_WEB_SMTP_HOST`<br>`SKILLSPECTOR_WEB_SMTP_PORT`<br>`SKILLSPECTOR_WEB_SMTP_USERNAME`<br>`SKILLSPECTOR_WEB_SMTP_PASSWORD`<br>`SKILLSPECTOR_WEB_MAIL_FROM`<br>`SKILLSPECTOR_WEB_PUBLIC_URL` | Production | Optional: password reset emails. `PUBLIC_URL` is the production domain. Previews go without them, so they never email real users links to production. |

Any other setting in the [configuration reference](./CONFIGURATION.md) can be set the same way. Don't
set these:
- `NUXT_API_BASE`: the binding sets it.
- `SKILLSPECTOR_WEB_AUTH`, `SKILLSPECTOR_WEB_SCAN_EXECUTOR`, `SKILLSPECTOR_WEB_LOG_STORE` and
  `SKILLSPECTOR_WEB_RATE_LIMIT_STORE`: hosted mode picks them and refuses values that can't work.

A deployment keeps the variables it was built with. Redeploy after changing one.

## Deployments

| What happens | Where it goes | Data |
|---|---|---|
| A release is published | **Production**, at exactly the release's tagged commit | Production database |
| A pull request is merged to `main` | **Preprod**: a preview, at the preprod domain | Preview database |
| A pull request is opened or updated | Nothing, unless you deploy it by hand | Preview database |

- **Production** is whatever the `production` branch points to. Vercel's production branch is
  `production`, not `main`. When release-please publishes a release, the
  [Release](../.github/workflows/release.yml) workflow runs
  [Deploy production](../.github/workflows/production.yml), which force-pushes the release's commit
  to `production`. Vercel then builds and deploys it.
- **Preprod** is the latest `main`, deployed as a preview with the Preview environment variables.
  The preprod domain always points at it, behind Vercel's sign-in like other previews.
- **Other branches** don't deploy by themselves (`git.deploymentEnabled` in `vercel.ts`). They would
  share preprod's database, and the API migrates the database it starts on, so an unreviewed
  migration would reach preprod. To check a pull request on Vercel anyway (the sandbox, Queues,
  BotID), deploy it by hand from its branch: `vercel deploy`.

**Roll back** by deploying an older release: Actions → **Deploy production** → **Run workflow**,
with the tag, for example `v1.1.1`. It moves `production` back and Vercel deploys that commit.
For an immediate switch with no build, `vercel rollback` points production at the previous
production deployment. Run Deploy production afterwards as well, so the branch and production
match again.

The API migrates the production database when a release starts. Migrations only add tables and
columns, so an older release still runs on the newer schema, and a rollback needs no database step.
Keep new migrations additive for that reason.

### Setting up release deployments

Once per project, after the workflows are on `main`:

1. **Create the `production` branch** at the commit production runs now, so the switch changes
   nothing:

   ```bash
   git push origin <commit>:refs/heads/production
   ```

2. **Make it Vercel's production branch:** project **Settings → Environments → Production →
   Branch Tracking**, set the branch to `production`. From then on, `main` deploys as a preview.
3. **Add the preprod domain:** **Settings → Domains → Add**, for example
   `<project>-preprod.vercel.app`, connected to **Preview** with the Git branch `main`.

## Previews and production data

Preview deployments never reach production data:

- **Database:** previews use the preview database, and the production connection string is scoped
  to Production only.
- **Saved keys:** previews encrypt with their own `SECRET_KEY`.
- **Scans:** queue topics are partitioned by deployment, so a preview only runs the scans it queued
  itself.
- **Cron:** Vercel runs cron jobs on production only.
- **Email:** previews have no SMTP settings, so they send none.
- **Access:** Vercel's Deployment Protection keeps previews behind a Vercel sign-in by default.
  Leave it on.

Preprod and every hand-deployed preview share the one preview database. A preview built from a
pull request migrates it, so deploy one only for a branch whose migrations you're ready to see on
preprod. If the schema gets ahead of `main`, recreate the preview database rather than pointing
previews at production.

## Local development

Self-hosted development is unchanged (`pnpm setup` or `docker compose up`). To run the hosted
layout locally, run `vercel dev` from the repository root. It starts both services and sets the
binding. It uses the Development environment's variables, so the preview database.
