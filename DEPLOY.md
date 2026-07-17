# Deploy to Cloudflare Pages

Two separate Cloudflare Pages projects share this repo. Each build publishes **only one dashboard** — the other page file is removed before build, so it does not exist on that URL at all.

| Project | Build command | Who visits |
|---------|---------------|------------|
| **Client** (existing) | `npm run build:cloudflare:client` | Clients |
| **Internal** (new) | `npm run build:cloudflare:internal` | Your team |

Client URL example: `https://go-integrity.pages.dev` → `/client-report/` only  
Internal URL example: `https://go-integrity-internal.pages.dev` → `/` (All), `/facebook/`, `/home-ab-test/`

**Important:** Both projects can use `npm run build:cloudflare` — the script auto-selects **internal** when `CF_PAGES_PROJECT_NAME` contains `internal` (e.g. `go-integrity-internal`), otherwise **client**. You can still set `npm run build:cloudflare:client` or `:internal` explicitly.

## 1. Push to GitHub

```bash
git add .
git commit -m "Split client and internal Cloudflare deploys"
git push -u origin main
```

Do **not** commit `.env` — it is gitignored.

## 2. Client project (public)

Use your **existing** Cloudflare Pages project connected to `go-integrity`.

| Setting | Value |
|--------|--------|
| **Framework preset** | None |
| **Build command** | `npm run build:cloudflare:client` |
| **Build output directory** | `build` |
| **Deploy command** | leave empty (do **not** use `npx wrangler deploy`) |
| **Node.js version** | `20` |

Share this project's `*.pages.dev` URL (or custom domain) with the client.

## 3. Internal project (team)

Create a **second** Pages project from the same repo:

1. **Workers & Pages → Create → Pages → Connect to Git**
2. Select **`go-integrity`** again
3. Project name e.g. `go-integrity-internal`
4. Build settings:

| Setting | Value |
|--------|--------|
| **Build command** | `npm run build:cloudflare:internal` |
| **Build output directory** | `build` |
| **Node.js version** | `20` |

Bookmark this URL for internal use. Do not share it with clients.

## 4. Build environment variables

Add the same **Build** secrets to **both** projects (Settings → Build → Variables and secrets):

| Variable | Purpose |
|----------|---------|
| `META_ACCESS_TOKEN` | Meta Marketing API token |
| `META_AD_ACCOUNT_ID` | e.g. `act_1369099874606476` |
| `GHL_PRIVATE_INTEGRATION_TOKEN` | GHL private integration token |
| `GHL_LOCATION_ID` | GHL location ID |

Use **Encrypt** (Secret) for each. After saving, **Retry deployment**.

## 5. Internal A/B page views (KV)

The Page 1 A/B dashboard stores **shared page views** in Cloudflare KV so one **Update data** paste applies for the whole team. (Opt-in targets for table padding come from `config/ghl_split_stats_home_ab.json` at deploy time.)

On the **internal** project only (`go-integrity-internal`):

1. Open [Cloudflare dashboard](https://dash.cloudflare.com) → **Storage & databases** → **KV**
2. **Create a namespace** — name it e.g. `go-integrity-ab-test`
3. Go to **Workers & Pages** → open **`go-integrity-internal`** (not the client project)
4. **Settings** → **Bindings** → **Add** → **KV namespace**
5. Set:
   - **Variable name:** `AB_TEST_KV` (must match exactly)
   - **KV namespace:** `go-integrity-ab-test`
6. **Save**, then **Deployments → … → Retry deployment** on the latest build

Until KV is bound, **Update data** still reloads CRM submissions and applies page views for your browser session only. After KV is bound, saved views persist for everyone.

## 6. Optional: Refresh button

Per project:

1. **Settings → Builds → Deploy hooks** → Create hook
2. Add **Functions** variables (Production):

| Variable | Purpose |
|----------|---------|
| `DEPLOY_HOOK_URL` | That project's deploy hook URL |
| `REFRESH_PASSWORD` | Optional |

## 7. Custom domains (optional)

- Client project → e.g. `reports.yourdomain.com`
- Internal project → e.g. `analytics.yourdomain.com` (or skip and use the `*.pages.dev` URL)

## Manual update

**Deployments → Retry deployment** on either project rebuilds only that dashboard.
