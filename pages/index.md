---
title: Meta Ads Dashboard
---

# Meta Ads Dashboard

Evidence + DuckDB reporting for Facebook/Instagram ads.

<Grid columns=1>
  <BigLink url="/client-report">Client Report (leads & performance)</BigLink>
</Grid>

## Refresh data

```bash
npm run refresh
npm run dev
```

## What's connected

- **Meta Ads** → Python sync script → DuckDB → Evidence charts
- **GHL** → contacts & opportunities → DuckDB → client report
