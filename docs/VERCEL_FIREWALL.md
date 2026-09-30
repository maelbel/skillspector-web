# Vercel Firewall rules (hosted version)

On the hosted version the app enforces its own limits (see "Abuse limits" in the
[README](../README.md#security-model)). These Vercel Firewall rules add a coarser limit at the edge in
front of them. Requests the firewall blocks never reach a function, and Vercel doesn't bill for
them. The app's limits stay the precise ones: they know who is signed in, and the firewall only
sees addresses.

The limits are set well above the app's own, so they catch floods, not people. Firewall counters
are per region, so a client spread over several regions can get a few times more through.
The app's limits, in the database, still hold.

## Rules

Run these from a linked project (`vercel link`). They are staged as drafts and do nothing until
published.

```bash
# Scan submissions: the app allows 20 per address per minute.
vercel firewall rules add "Scan submissions per IP" \
  --condition '{"type":"path","op":"eq","value":"/api/scan"}' \
  --condition '{"type":"method","op":"eq","value":"POST"}' \
  --action rate_limit \
  --rate-limit-window 60 --rate-limit-requests 40 --rate-limit-keys ip \
  --rate-limit-action log \
  --yes

# Sign-in, sign-up and password reset: the app allows 10 per address per 5 minutes.
vercel firewall rules add "Account endpoints per IP" \
  --condition '{"type":"path","op":"pre","value":"/api/auth/"}' \
  --condition '{"type":"method","op":"eq","value":"POST"}' \
  --action rate_limit \
  --rate-limit-window 300 --rate-limit-requests 50 --rate-limit-keys ip \
  --rate-limit-action log \
  --yes

vercel firewall diff
```

## Rolling them out

Both rules start with `--rate-limit-action log`, which records matches without blocking anything.

1. Publish with `vercel firewall publish --yes`. Then watch the matches under **Firewall →
   Traffic**, filtered by rule, for a few days.
2. If only floods match, switch each rule to return `429`:
   `vercel firewall rules edit "Scan submissions per IP" --rate-limit-action rate_limit --yes`.
   Then publish again.
3. If real users match, raise `--rate-limit-requests` instead.

When the firewall returns a `429`, the body isn't the app's. The UI then shows "Too many
requests — wait a minute and try again."

## Also turn on

- **BotID Deep Analysis.** Go to **Firewall → Rules → Vercel BotID Deep Analysis**. BotID itself
  is on when the app is built with `NUXT_PUBLIC_BOTID=true`.
