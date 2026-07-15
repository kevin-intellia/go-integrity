#!/usr/bin/env python3
"""Build local HTML visualization for the Page 1 A/B split test."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "home-ab-test.html"
OUT_STATIC = ROOT / "static" / "home-ab-test.html"
GHL_STATS_STATIC = ROOT / "static" / "ghl_split_stats_home_ab.json"
SUBMISSIONS_CONFIG = ROOT / "config" / "form_submissions_home_ab.json"
GHL_STATS_CONFIG = ROOT / "config" / "ghl_split_stats_home_ab.json"
GHL_DB = ROOT / "sources" / "ghl" / "ghl.duckdb"
GHL_SNAPSHOT = ROOT / "sources" / "ghl" / "ghl.snapshot.duckdb"

TEST_START_UTC = "2026-07-15 15:19:56"
CONTROL_URL = "%main-production-page%"
CONTROL_PAGE_URL = "https://stowelegacyestate.com/stowe-auction---main-production-page"
VARIATION_PAGE_URL = "https://stowelegacyestate.com/home-184946"


def load_ghl_stats() -> dict:
    cfg = json.loads(GHL_STATS_CONFIG.read_text())
    return {
        "views": cfg["views"],
        "optins": cfg["optins"],
        "notes": cfg.get("notes", ""),
        "updated_at": cfg.get("updated_at", ""),
    }


def pick_db() -> Path:
    if GHL_DB.exists():
        return GHL_DB
    return GHL_SNAPSHOT


def load_submission_rows(
    entries: list[dict],
    *,
    form_name: str,
    url_key: str = "url",
) -> list[dict]:
    rows = []
    for i, row in enumerate(entries, start=1):
        rows.append(
            {
                "n": i,
                "time": row["time_edt"],
                "name": row["name"],
                "email": row["email"],
                "url": row.get(url_key, "—"),
                "source": row.get("source", form_name),
                "duplicate": bool(row.get("duplicate")),
                "unknown": bool(row.get("unknown")),
            }
        )
    return rows


def pad_to_ghl_count(rows: list[dict], target: int) -> list[dict]:
    out = list(rows)
    while len(out) < target:
        out.append(
            {
                "n": len(out) + 1,
                "time": "",
                "name": "Repeat submit",
                "email": "—",
                "url": "—",
                "source": "—",
                "duplicate": True,
                "unknown": True,
            }
        )
    for i, row in enumerate(out, start=1):
        row["n"] = i
    return out


def load_form_submissions(ghl_optins: dict) -> tuple[list[dict], list[dict]]:
    cfg = json.loads(SUBMISSIONS_CONFIG.read_text())
    control = load_submission_rows(
        cfg.get("control_submissions", []),
        form_name=cfg.get("control_form_name", "Control form"),
    )
    variation = load_submission_rows(
        cfg["variation_submissions"],
        form_name=cfg.get("variation_form_name", "Funnel Leads"),
    )
    control = pad_to_ghl_count(control, ghl_optins["control"])
    variation = pad_to_ghl_count(variation, ghl_optins["variation"])
    return control, variation


def fetch_control_rows(con: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = con.execute(
        f"""
        select date_added, first_name, last_name, email, source, page_url
        from ghl.contacts
        where date_added >= timestamp '{TEST_START_UTC}'
          and coalesce(email, '') != ''
          and page_url ilike '{CONTROL_URL}'
        order by date_added
        """
    ).fetchall()

    out = []
    for i, (date_added, first_name, last_name, email, source, page_url) in enumerate(rows, start=1):
        out.append(
            {
                "n": i,
                "time": date_added.isoformat() if hasattr(date_added, "isoformat") else str(date_added),
                "name": " ".join(
                    p for p in [first_name, last_name] if p and str(p) != "None"
                ).strip()
                or "—",
                "email": email or "—",
                "source": source or "—",
                "url": (page_url or "—")[:120],
                "duplicate": False,
            }
        )
    return out


def fetch_before_legacy(con: duckdb.DuckDBPyConnection) -> int:
    return int(
        con.execute(
            f"""
            select count(*) from ghl.contacts
            where date_added >= '2026-07-01'
              and date_added < timestamp '{TEST_START_UTC}'
              and coalesce(email, '') != ''
              and coalesce(source, '') not in ('', '-')
              and (
                page_url ilike '%stowelegacyestate.com/home%'
                or page_url ilike '%stowelegacyestate.com/?%'
                or page_url = 'https://stowelegacyestate.com/'
              )
            """
        ).fetchone()[0]
    )


def build_html(data: dict, *, embedded: bool = False) -> str:
    payload = json.dumps(data, indent=2)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body_padding = "1rem 1.25rem 1.5rem" if embedded else "1.5rem 2rem 2rem"
    header = (
        ""
        if embedded
        else f"""
  <div class="page-header">
    <h1>Page 1 A/B Split Test</h1>
    <p class="sub">Started Jul 15, 2026 ~11:19 AM EDT · Updated {updated}</p>
  </div>
"""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Page 1 A/B Split Test</title>
  <style>
    :root {{
      --bg: #0f1117;
      --card: #1a1d27;
      --border: #2a2f3d;
      --text: #e8eaef;
      --muted: #9aa3b2;
      --control: #5b8def;
      --control-dim: rgba(91,141,239,0.12);
      --variation: #4ec9b0;
      --variation-dim: rgba(78,201,176,0.12);
      --win: #7dd87d;
      --tie: #e8b84a;
      --dupe: #e8b84a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: {body_padding};
    }}
    .page-header {{ margin-bottom: 1.25rem; }}
    h1 {{ margin: 0 0 0.25rem; font-size: 1.5rem; font-weight: 600; }}
    .sub {{ color: var(--muted); font-size: 0.9rem; margin: 0; }}

    .ab-split {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 0;
      margin-bottom: 2rem;
      min-height: 320px;
    }}
    @media (max-width: 900px) {{
      .ab-split {{ grid-template-columns: 1fr; }}
      .vs-divider {{ display: none; }}
    }}

    .arm {{
      background: var(--card);
      border: 2px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .arm.control {{ border-top: 4px solid var(--control); }}
    .arm.variation {{ border-top: 4px solid var(--variation); }}

    .arm-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.75rem;
    }}
    .arm-label {{
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .arm-title {{
      font-size: 1.25rem;
      font-weight: 700;
      margin: 0.15rem 0 0;
    }}
    .arm.control .arm-title {{ color: var(--control); }}
    .arm.variation .arm-title {{ color: var(--variation); }}
    .arm-url {{
      font-family: ui-monospace, monospace;
      font-size: 0.72rem;
      word-break: break-all;
    }}
    .arm-url a {{
      color: inherit;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      max-width: 100%;
    }}
    .arm-url a:hover {{
      text-decoration: underline;
    }}
    .arm.control .arm-url a {{ color: var(--control); }}
    .arm.variation .arm-url a {{ color: var(--variation); }}
    .arm-url .link-icon {{
      font-size: 0.85em;
      opacity: 0.75;
      flex-shrink: 0;
    }}

    .hero-metric {{
      text-align: center;
      padding: 1rem 0;
    }}
    .hero-value {{
      font-size: 3.5rem;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
      line-height: 1;
    }}
    .arm.control .hero-value {{ color: var(--control); }}
    .arm.variation .hero-value {{ color: var(--variation); }}
    .hero-label {{
      color: var(--muted);
      font-size: 0.85rem;
      margin-top: 0.35rem;
    }}

    .stat-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }}
    .stat {{
      background: rgba(255,255,255,0.03);
      border-radius: 8px;
      padding: 0.75rem;
      text-align: center;
    }}
    .stat-val {{
      font-size: 1.5rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }}
    .stat-lbl {{
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 0.15rem;
    }}

    .vs-divider {{
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 1rem;
      color: var(--muted);
      font-size: 1.25rem;
      font-weight: 700;
    }}

    .tables-section {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }}
    @media (max-width: 900px) {{
      .tables-section {{ grid-template-columns: 1fr; }}
    }}
    .table-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem 1.25rem;
      overflow-x: auto;
    }}
    .table-card.control {{ border-top: 3px solid var(--control); }}
    .table-card.variation {{ border-top: 3px solid var(--variation); }}
    .table-card h2 {{
      margin: 0 0 0.75rem;
      font-size: 0.95rem;
      font-weight: 600;
    }}
    .table-card.control h2 {{ color: var(--control); }}
    .table-card.variation h2 {{ color: var(--variation); }}

    table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; table-layout: fixed; }}
    th, td {{
      text-align: left;
      padding: 0.45rem 0.5rem;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      height: 2.25rem;
      max-width: 0;
    }}
    th {{ color: var(--muted); font-weight: 500; font-size: 0.75rem; }}
    td:first-child, th:first-child {{ width: 2rem; max-width: 2rem; }}
    tr.dupe td {{ background: rgba(232,184,74,0.08); }}
    td.dupe-flag {{
      color: var(--dupe);
      font-weight: 600;
      font-size: 0.65rem;
      text-align: center;
    }}
    .tag {{
      display: inline-block;
      padding: 0.1rem 0.45rem;
      border-radius: 999px;
      font-size: 0.65rem;
      font-weight: 600;
      background: rgba(232,184,74,0.18);
      color: var(--dupe);
    }}
    .toolbar {{
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 1rem;
      flex-wrap: wrap;
      margin: 0 0 1rem;
    }}
    .toggle-wrap {{
      display: flex;
      align-items: center;
      gap: 0.65rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.55rem 0.85rem;
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .toggle {{
      position: relative;
      width: 42px;
      height: 24px;
      flex-shrink: 0;
    }}
    .toggle input {{
      opacity: 0;
      width: 0;
      height: 0;
      position: absolute;
    }}
    .toggle-track {{
      position: absolute;
      inset: 0;
      background: rgba(255,255,255,0.1);
      border-radius: 999px;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .toggle input:checked + .toggle-track {{
      background: rgba(125,216,125,0.35);
    }}
    .toggle-thumb {{
      position: absolute;
      top: 3px;
      left: 3px;
      width: 18px;
      height: 18px;
      background: #fff;
      border-radius: 50%;
      transition: transform 0.2s;
      pointer-events: none;
    }}
    .toggle input:checked ~ .toggle-thumb {{
      transform: translateX(18px);
    }}
    .toggle-label strong {{ color: var(--text); }}
    .reload-wrap {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.55rem 0.85rem;
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .reload-btn {{
      appearance: none;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.06);
      color: var(--text);
      border-radius: 8px;
      padding: 0.35rem 0.75rem;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s, border-color 0.2s, opacity 0.2s;
    }}
    .reload-btn:hover:not(:disabled) {{
      background: rgba(91,141,239,0.18);
      border-color: rgba(91,141,239,0.45);
    }}
    .reload-btn:disabled {{
      opacity: 0.55;
      cursor: not-allowed;
    }}
    .reload-status {{
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .reload-status.error {{
      color: #f08080;
    }}
  </style>
</head>
<body>
{header}
  <div class="ab-split">
    <div class="arm control" id="armControl">
      <div class="arm-head">
        <div>
          <div class="arm-label">A · Control</div>
          <div class="arm-title">Before design</div>
        </div>
      </div>
      <div class="arm-url">
        <a href="{CONTROL_PAGE_URL}" target="_blank" rel="noopener noreferrer">
          stowelegacyestate.com/stowe-auction---main-production-page
          <span class="link-icon" aria-hidden="true">↗</span>
        </a>
      </div>
      <div class="hero-metric">
        <div class="hero-value" id="rateControl">—</div>
        <div class="hero-label">Unique submission rate</div>
      </div>
      <div class="stat-row">
        <div class="stat">
          <div class="stat-val" id="subsControl">—</div>
          <div class="stat-lbl">Unique submissions</div>
        </div>
        <div class="stat">
          <div class="stat-val" id="viewsControl">—</div>
          <div class="stat-lbl">Page views</div>
        </div>
      </div>
    </div>

    <div class="vs-divider">VS</div>

    <div class="arm variation" id="armVariation">
      <div class="arm-head">
        <div>
          <div class="arm-label">B · Variation</div>
          <div class="arm-title">New design</div>
        </div>
      </div>
      <div class="arm-url">
        <a href="{VARIATION_PAGE_URL}" target="_blank" rel="noopener noreferrer">
          stowelegacyestate.com/home-184946 · Funnel Leads form
          <span class="link-icon" aria-hidden="true">↗</span>
        </a>
      </div>
      <div class="hero-metric">
        <div class="hero-value" id="rateVariation">—</div>
        <div class="hero-label">Unique submission rate</div>
      </div>
      <div class="stat-row">
        <div class="stat">
          <div class="stat-val" id="subsVariation">—</div>
          <div class="stat-lbl">Unique submissions</div>
        </div>
        <div class="stat">
          <div class="stat-val" id="viewsVariation">—</div>
          <div class="stat-lbl">Page views</div>
        </div>
      </div>
    </div>
  </div>

  <div class="toolbar">
    <div class="toggle-wrap">
      <label class="toggle" title="Exclude repeat submits from the same person">
        <input type="checkbox" id="removeDupes" checked />
        <span class="toggle-track"></span>
        <span class="toggle-thumb"></span>
      </label>
      <span class="toggle-label"><strong>Remove duplicates</strong> · show unique people only in tables</span>
    </div>
    <div class="reload-wrap">
      <button type="button" class="reload-btn" id="reloadData">Reload data</button>
      <span class="reload-status" id="lastUpdated">Last updated: {data.get("ghl", {}).get("updated_at") or updated}</span>
    </div>
  </div>

  <div class="tables-section">
    <div class="table-card control">
      <h2>Control — form submissions</h2>
      <table>
        <thead><tr><th>#</th><th>Time (EDT)</th><th>Name</th><th>Email</th><th>Form</th><th></th></tr></thead>
        <tbody id="controlTable"></tbody>
      </table>
    </div>
    <div class="table-card variation">
      <h2>Variation — form submissions</h2>
      <table>
        <thead><tr><th>#</th><th>Time (EDT)</th><th>Name</th><th>Email</th><th>URL</th><th></th></tr></thead>
        <tbody id="variationTable"></tbody>
      </table>
    </div>
  </div>

  <script>
    const DATA = {payload};

    function fmtTime(iso) {{
      const d = new Date(iso);
      return d.toLocaleString('en-US', {{ timeZone: 'America/New_York', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }});
    }}

    function countUnique(rows) {{
      return rows.filter(r => !r.duplicate).length;
    }}

    function calcRate(subs, views) {{
      return views ? (subs / views) * 100 : 0;
    }}

    function cell(value, extraClass) {{
      const text = value == null ? '' : String(value);
      const safe = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
      const cls = extraClass ? ` class="${{extraClass}}"` : '';
      return `<td${{cls}} title="${{safe}}">${{safe}}</td>`;
    }}

    function fillTable(id, rows, cols, removeDupes) {{
      const visible = removeDupes ? rows.filter(r => !r.duplicate) : rows;
      const tbody = document.getElementById(id);
      tbody.innerHTML = visible.map((r, idx) => {{
        const cls = r.duplicate ? ' class="dupe"' : '';
        return `<tr${{cls}}>${{cols.map((c, i) => {{
          const value = i === 0 ? idx + 1 : c(r);
          const extra = i === cols.length - 1 && value === 'DUPE' ? 'dupe-flag' : '';
          return cell(value, extra);
        }}).join('')}}</tr>`;
      }}).join('');
    }}

    function render(removeDupes) {{
      const ctrlRows = DATA.control_submissions;
      const varRows = DATA.variation_submissions;
      const views = DATA.ghl.views;

      const ctrlUnique = countUnique(ctrlRows);
      const varUnique = countUnique(varRows);
      const ctrlRate = calcRate(ctrlUnique, views.control);
      const varRate = calcRate(varUnique, views.variation);

      document.getElementById('rateControl').textContent = ctrlRate.toFixed(2) + '%';
      document.getElementById('rateVariation').textContent = varRate.toFixed(2) + '%';
      document.getElementById('subsControl').textContent = ctrlUnique;
      document.getElementById('subsVariation').textContent = varUnique;
      document.getElementById('viewsControl').textContent = views.control.toLocaleString();
      document.getElementById('viewsVariation').textContent = views.variation.toLocaleString();

      fillTable('controlTable', ctrlRows, [
        r => r.n,
        r => r.time ? fmtTime(r.time) : '—',
        r => r.name,
        r => r.email,
        r => r.source,
        r => r.duplicate ? 'DUPE' : ''
      ], removeDupes);
      fillTable('variationTable', varRows, [
        r => r.n,
        r => r.time ? fmtTime(r.time) : '—',
        r => r.name,
        r => r.email,
        r => r.url,
        r => r.duplicate ? 'DUPE' : ''
      ], removeDupes);

      const ctrlVisible = removeDupes ? ctrlRows.filter(r => !r.duplicate).length : ctrlRows.length;
      const varVisible = removeDupes ? varRows.filter(r => !r.duplicate).length : varRows.length;
      document.querySelector('.table-card.control h2').textContent =
        `Control — form submissions (${{ctrlVisible}})`;
      document.querySelector('.table-card.variation h2').textContent =
        `Variation — form submissions (${{varVisible}})`;
    }}

    function formatUpdatedAt(value) {{
      if (!value) return '—';
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return String(value);
      return d.toLocaleString('en-US', {{
        timeZone: 'America/New_York',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      }}) + ' EDT';
    }}

    function setReloadStatus(message, isError) {{
      const el = document.getElementById('lastUpdated');
      el.textContent = message;
      el.classList.toggle('error', Boolean(isError));
    }}

    async function reloadData() {{
      const btn = document.getElementById('reloadData');
      btn.disabled = true;
      setReloadStatus('Loading…', false);

      try {{
        const response = await fetch('/api/ab-test-data', {{ cache: 'no-store' }});
        const payload = await response.json().catch(() => ({{}}));

        if (!response.ok || !payload.ok) {{
          const detail = payload.error || `Request failed (${{response.status}})`;
          if (response.status === 404) {{
            throw new Error('Live reload available on deployed internal site');
          }}
          throw new Error(detail);
        }}

        DATA.control_submissions = payload.control_submissions;
        DATA.variation_submissions = payload.variation_submissions;
        DATA.ghl = payload.ghl;
        render(document.getElementById('removeDupes').checked);
        setReloadStatus('Last updated: ' + formatUpdatedAt(payload.updated_at), false);
      }} catch (error) {{
        const message = error instanceof Error ? error.message : 'Reload failed';
        setReloadStatus(message, true);
      }} finally {{
        btn.disabled = false;
      }}
    }}

    const toggle = document.getElementById('removeDupes');
    toggle.addEventListener('change', () => render(toggle.checked));
    document.getElementById('reloadData').addEventListener('click', reloadData);
    render(true);
  </script>
</body>
</html>
"""


def main() -> None:
    ghl_stats = load_ghl_stats()
    control_submissions, variation_submissions = load_form_submissions(ghl_stats["optins"])

    data = {
        "test_started_utc": TEST_START_UTC,
        "control_url": CONTROL_PAGE_URL,
        "variation_url": VARIATION_PAGE_URL,
        "control_submissions": control_submissions,
        "variation_submissions": variation_submissions,
        "ghl": ghl_stats,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(data, embedded=False))
    OUT_STATIC.parent.mkdir(parents=True, exist_ok=True)
    OUT_STATIC.write_text(build_html(data, embedded=True))
    GHL_STATS_STATIC.write_text(GHL_STATS_CONFIG.read_text())
    print(f"Wrote {OUT}")
    print(f"Wrote {OUT_STATIC}")
    print(f"  GHL form submissions: control {ghl_stats['optins']['control']}, variation {ghl_stats['optins']['variation']}")
    print(f"  Control rows in table: {len(control_submissions)}")
    print(f"  Variation rows in table: {len(variation_submissions)}")


if __name__ == "__main__":
    main()
