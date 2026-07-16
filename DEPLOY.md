# Deploy to Cloudflare Pages

Two separate Cloudflare Pages projects share this repo. Each build publishes **only one dashboard** — the other page file is removed before build, so it does not exist on that URL at all.

| Project | Build command | Who visits |
|---------|---------------|------------|
| **Client** (existing) | `npm run build:cloudflare:client` | Clients |
| **Internal** (new) | `npm run build:cloudflare:internal` | Your team |

Client URL example: `https://go-integrity.pages.dev` → `/client-report/` only  
Internal URL example: `https://go-integrity-internal.pages.dev` → `/meta-ads/` only

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

The Page 1 A/B dashboard stores **shared GHL stats** (page views + opt-ins) in Cloudflare KV so one update applies for the whole team.

On the **internal** project only:

1. **Workers & Pages → KV → Create a namespace** (e.g. `go-integrity-ab-test`)
2. **Internal Pages project → Settings → Functions → KV namespace bindings**
3. Add binding:
   - **Variable name:** `AB_TEST_KV`
   - **KV namespace:** the namespace you created
4. **Retry deployment**

Until KV is bound, stats fall back to the static JSON from deploy. Saving via **Update data** requires the KV binding — paste all four numbers from GHL (views + opt-ins for each arm).

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
