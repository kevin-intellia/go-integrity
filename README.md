# Meta Ads → Evidence Dashboard

Pull Facebook/Instagram ad metrics into DuckDB and visualize them with Evidence.

## Quick start

```bash
cd ~/Projects/meta-evidence-dashboard
npm install
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Demo data (no Meta credentials yet)
npm run refresh
npm run dev
```

Open http://localhost:3000/meta-ads

## Connect real Meta data

You're currently in **Events Manager** — that's for Pixel/CAPI (sending data *to* Meta). To **pull ad metrics**, use the **Marketing API** instead.

### 1. Create a Meta developer app

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. **My Apps → Create App → Business**
3. Add the **Marketing API** product

### 2. Get an access token

1. Open [Graph API Explorer](https://developers.facebook.com/tools/explore/)
2. Select your app
3. Add permission: `ads_read`
4. Click **Generate Access Token**

For long-running syncs, create a **System User** in Business Manager with a non-expiring token. Short-lived explorer tokens expire in ~1–2 hours.

### 3. Add credentials

```bash
cp .env.example .env
```

Edit `.env`:

```
META_ACCESS_TOKEN=your_token_here
META_AD_ACCOUNT_ID=act_913909870396927
```

Your ad account ID from the screenshot: `913909870396927` → use `act_913909870396927`.

### 4. Sync and view

```bash
npm run refresh   # pull Meta data + refresh Evidence cache
npm run dev       # open dashboard
```

## Project layout

```
scripts/sync_meta_ads.py   # Python → Meta Marketing API → DuckDB
scripts/sync_ghl.py        # Python → GoHighLevel API → DuckDB
sources/meta_ads/          # DuckDB file + Evidence source queries
sources/ghl/               # GHL contacts + opportunities
pages/meta-ads.md          # Internal dashboard
pages/client-report.md     # Client-facing dashboard
```

## Connect GoHighLevel

1. Sub-account → **Settings → Private Integrations → Create**
2. Scopes: `contacts.readonly`, `opportunities.readonly`
3. Add to `.env`:

```
GHL_PRIVATE_INTEGRATION_TOKEN=your_token_here
GHL_LOCATION_ID=fXxDgtMxnW842psPbTR8
```

```bash
npm run sync:ghl    # pull contacts + opportunities
npm run refresh     # sync Meta + GHL + refresh Evidence cache
```
