# Deploy to Cloudflare Pages

## 1. Push to GitHub

```bash
git add .
git commit -m "Prepare Cloudflare Pages deployment"
git push -u origin main
```

Do **not** commit `.env` — it is gitignored.

## 2. Create the Cloudflare Pages project

1. Log in at [dash.cloudflare.com](https://dash.cloudflare.com)
2. **Workers & Pages → Create → Pages → Connect to Git**
3. Select this repository
4. Choose **Pages** (not Worker). If you see `npx wrangler deploy` in the logs, the project type is wrong.

5. Build settings:

| Setting | Value |
|--------|--------|
| **Framework preset** | None |
| **Build command** | `npm run build:cloudflare` |
| **Build output directory** | `build` |
| **Deploy command** | leave empty / default (do **not** use `npx wrangler deploy`) |
| **Node.js version** | `20` (Environment variables → Production) |

## 3. Add build environment variables

In **Pages → your project → Settings → Build → Variables and secrets** (choose **Build** at the top):

| Variable | Purpose |
|----------|---------|
| `META_ACCESS_TOKEN` | Meta Marketing API token |
| `META_AD_ACCOUNT_ID` | e.g. `act_1369099874606476` |
| `GHL_PRIVATE_INTEGRATION_TOKEN` | GHL private integration token |
| `GHL_LOCATION_ID` | GHL location ID |

These are used during the build to pull fresh data.

**Important:** Add each one with **Encrypt** turned on (Secret). Encrypted secrets are reliably available during the build; Plaintext ones often are not.

After saving, open **Deployments → Details → Retry deployment**. A new build should show your variables being used (not `Build environment variables: (none found)`).

## 4. Optional: public Refresh button

1. **Pages → Settings → Builds → Deploy hooks** → Create hook
2. Copy the hook URL
3. Add **Functions** variables (Production):

| Variable | Purpose |
|----------|---------|
| `DEPLOY_HOOK_URL` | The deploy hook URL from step 1 |
| `REFRESH_PASSWORD` | Optional shared password for the refresh button |

The refresh button triggers a new deploy (2–3 minutes). If `REFRESH_PASSWORD` is set, you'll be prompted when clicking refresh.

## 5. Optional: password-protect the whole site

Use **Cloudflare Zero Trust → Access** to require login before anyone can view the report. Free for up to 50 users.

## 6. Custom domain (optional)

**Pages → Custom domains** → add e.g. `reports.yourdomain.com`

## Manual update without the button

**Pages → Deployments → Retry deployment** runs a fresh build with the latest API data.
