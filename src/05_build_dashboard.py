"""
Script 5: Build Dashboard HTML
================================
Reads: output/signals_latest.csv, output/meta.json
Output: docs/index.html (GitHub Pages)
"""

import os, json
import pandas as pd
from datetime import datetime, timedelta, timezone

OUTPUT_DIR  = "output"
DOCS_DIR    = "docs"
CONFIG_FILE = "config/params.json"

IST = timezone(timedelta(hours=5, minutes=30))


def build_html(rows_json, meta, configs):
    configs_json = json.dumps(configs, indent=2)
    meta_json    = json.dumps(meta, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NSE BTST Daily Signals</title>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --surface2: #1f2937;
    --border: #30363d; --text: #e6edf3; --muted: #8b949e;
    --accent: #58a6ff; --green: #3fb950; --red: #f85149;
    --orange: #f0883e; --yellow: #d29922; --purple: #bc8cff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%); border-bottom: 1px solid var(--border); padding: 0 24px; }}
  .header-top {{ display: flex; align-items: center; justify-content: space-between; padding: 16px 0 12px; flex-wrap: wrap; gap: 12px; }}
  .logo {{ display: flex; align-items: center; gap: 12px; }}
  .logo-icon {{ width: 36px; height: 36px; background: linear-gradient(135deg, #2563eb, #7c3aed); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }}
  .logo-text {{ font-size: 20px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }}
  .logo-sub {{ font-size: 12px; color: var(--muted); margin-top: 1px; }}
  .header-right {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  .signal-date {{ background: rgba(88,166,255,0.12); border: 1px solid rgba(88,166,255,0.3); color: var(--accent); padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }}
  .refresh-badge {{ background: rgba(63,185,80,0.1); border: 1px solid rgba(63,185,80,0.3); color: var(--green); padding: 6px 14px; border-radius: 20px; font-size: 13px; cursor: pointer; }}
  .refresh-badge:hover {{ background: rgba(63,185,80,0.2); }}
  .generated {{ color: var(--muted); font-size: 12px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; padding: 20px 24px; }}
  .stat-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }}
  .stat-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted); margin-bottom: 6px; }}
  .stat-value {{ font-size: 28px; font-weight: 700; line-height: 1; }}
  .stat-sub {{ font-size: 11px; color: var(--muted); margin-top: 4px; }}
  .stat-blue   {{ color: var(--accent); }}
  .stat-green  {{ color: var(--green); }}
  .stat-orange {{ color: var(--orange); }}
  .stat-purple {{ color: var(--purple); }}
  .config-section {{ padding: 0 24px 16px; }}
  .config-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted); margin-bottom: 8px; }}
  .config-cards {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .config-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; font-size: 12px; }}
  .config-card .cid {{ font-weight: 700; margin-right: 8px; }}
  .config-card .cparam {{ color: var(--muted); }}
  .c-C1 {{ border-color: #2563eb66; }} .c-C1 .cid {{ color: #60a5fa; }}
  .c-C2 {{ border-color: #7c3aed66; }} .c-C2 .cid {{ color: #a78bfa; }}
  .c-C3 {{ border-color: #059669aa; }} .c-C3 .cid {{ color: #34d399; }}
  .c-C4 {{ border-color: #d9770066; }} .c-C4 .cid {{ color: #fbbf24; }}
  .controls {{ padding: 0 24px 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .search-box {{ flex: 1; min-width: 200px; max-width: 360px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; color: var(--text); font-size: 14px; outline: none; }}
  .search-box:focus {{ border-color: var(--accent); }}
  .filter-btn {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
  .filter-btn:hover, .filter-btn.active {{ background: var(--surface2); border-color: var(--accent); color: var(--accent); }}
  .result-count {{ color: var(--muted); font-size: 13px; margin-left: auto; }}
  .table-wrap {{ padding: 0 24px 32px; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{ background: var(--surface); border-bottom: 2px solid var(--border); padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; color: var(--muted); white-space: nowrap; cursor: pointer; user-select: none; }}
  thead th:hover {{ color: var(--text); }}
  thead th.sort-asc::after {{ content: ' \u2191'; color: var(--accent); }}
  thead th.sort-desc::after {{ content: ' \u2193'; color: var(--accent); }}
  tbody tr {{ border-bottom: 1px solid var(--border); transition: background 0.1s; }}
  tbody tr:hover {{ background: var(--surface); }}
  tbody td {{ padding: 10px 12px; font-size: 13px; white-space: nowrap; }}
  .col-num {{ color: var(--muted); width: 36px; text-align: right; }}
  .col-sym {{ font-weight: 700; font-size: 14px; color: #fff; }}
  .col-close {{ font-weight: 600; font-family: 'Courier New', monospace; }}
  .pos {{ color: var(--green); }} .neg {{ color: var(--red); }}
  .badges {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .badge {{ font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }}
  .badge-C1 {{ background: rgba(37,99,235,0.2); color: #60a5fa; border: 1px solid #2563eb55; }}
  .badge-C2 {{ background: rgba(124,58,237,0.2); color: #a78bfa; border: 1px solid #7c3aed55; }}
  .badge-C3 {{ background: rgba(5,150,105,0.2); color: #34d399; border: 1px solid #05966955; }}
  .badge-C4 {{ background: rgba(217,119,6,0.2); color: #fbbf24; border: 1px solid #d9770655; }}
  .count-badge {{ font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 10px; }}
  .count-4 {{ background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid #f8514955; }}
  .count-3 {{ background: rgba(240,136,62,0.15); color: #f0883e; border: 1px solid #f0883e55; }}
  .count-2 {{ background: rgba(88,166,255,0.15); color: var(--accent); border: 1px solid #58a6ff55; }}
  .count-1 {{ background: rgba(139,148,158,0.15); color: var(--muted); border: 1px solid #8b949e55; }}
  .empty-state {{ text-align: center; padding: 80px 20px; color: var(--muted); }}
  .empty-state .icon {{ font-size: 48px; margin-bottom: 16px; }}
  .empty-state h3 {{ font-size: 18px; color: var(--text); margin-bottom: 8px; }}
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <div class="logo">
      <div class="logo-icon">\U0001f4c8</div>
      <div>
        <div class="logo-text">NSE BTST Daily Signals</div>
        <div class="logo-sub">Buy Today Sell Tomorrow \u00b7 4 Fixed Configs</div>
      </div>
    </div>
    <div class="header-right">
      <div class="signal-date" id="sigDate">\u2014</div>
      <div class="refresh-badge" onclick="window.location.reload()" id="refreshBtn">\u27f3 Refresh</div>
      <div class="generated" id="genTime">\u2014</div>
    </div>
  </div>
</div>
<div class="stats" id="statsRow"></div>
<div class="config-section">
  <div class="config-title">Parameter Configs</div>
  <div class="config-cards" id="configCards"></div>
</div>
<div class="controls">
  <input class="search-box" id="searchBox" type="text" placeholder="\U0001f50d  Search symbol..." oninput="applyFilters()">
  <button class="filter-btn active" data-filter="all" onclick="setFilter('all',this)">All</button>
  <button class="filter-btn" data-filter="4" onclick="setFilter('4',this)">4 Configs</button>
  <button class="filter-btn" data-filter="3" onclick="setFilter('3',this)">3 Configs</button>
  <button class="filter-btn" data-filter="2" onclick="setFilter('2',this)">2 Configs</button>
  <button class="filter-btn" data-filter="1" onclick="setFilter('1',this)">1 Config</button>
  <span class="result-count" id="resultCount"></span>
</div>
<div class="table-wrap">
  <table id="mainTable">
    <thead>
      <tr>
        <th class="col-num">#</th>
        <th onclick="sortTable('SYMBOL')">Symbol</th>
        <th onclick="sortTable('CLOSE')">Close \u20b9</th>
        <th onclick="sortTable('PCT_1D_CHANGE')">1D Chg%</th>
        <th onclick="sortTable('PCT_FROM_LOW')">% from Low (10D)</th>
        <th onclick="sortTable('PCT_FROM_ATH')">% from ATH</th>
        <th>Configs Matched</th>
        <th onclick="sortTable('CONFIG_COUNT')">Count</th>
      </tr>
    </thead>
    <tbody id="tableBody"></tbody>
  </table>
  <div class="empty-state" id="emptyState" style="display:none">
    <div class="icon">\U0001f4ed</div>
    <h3>No signals found</h3>
    <p>No stocks matched the filter criteria for today.</p>
  </div>
</div>
<script>
const META    = {meta_json};
const SIGNALS = {rows_json};
const CONFIGS = {configs_json};
let allRows    = [...SIGNALS];
let filtered   = [...allRows];
let filterMode = 'all';
let sortKey    = 'CONFIG_COUNT';
let sortDir    = -1;
function init() {{
  document.getElementById('sigDate').textContent = '\U0001f4c5 ' + (META.signal_date || '\u2014');
  document.getElementById('genTime').textContent  = 'Generated: ' + (META.generated_at || '\u2014');
  const total = allRows.length;
  const c4 = allRows.filter(r => r.CONFIG_COUNT === 4).length;
  const c3 = allRows.filter(r => r.CONFIG_COUNT === 3).length;
  const c2 = allRows.filter(r => r.CONFIG_COUNT === 2).length;
  const c1 = allRows.filter(r => r.CONFIG_COUNT === 1).length;
  document.getElementById('statsRow').innerHTML = `
    <div class="stat-card"><div class="stat-label">Total Signals</div><div class="stat-value stat-blue">${{total}}</div><div class="stat-sub">Unique stocks</div></div>
    <div class="stat-card"><div class="stat-label">4 Configs</div><div class="stat-value stat-green">${{c4}}</div><div class="stat-sub">Strongest match</div></div>
    <div class="stat-card"><div class="stat-label">3 Configs</div><div class="stat-value stat-orange">${{c3}}</div><div class="stat-sub"></div></div>
    <div class="stat-card"><div class="stat-label">2 Configs</div><div class="stat-value stat-blue">${{c2}}</div><div class="stat-sub"></div></div>
    <div class="stat-card"><div class="stat-label">1 Config</div><div class="stat-value" style="color:var(--muted)">${{c1}}</div><div class="stat-sub"></div></div>
  `;
  const configHTML = CONFIGS.map(c => `
    <div class="config-card c-${{c.id}}">
      <span class="cid">${{c.id}}</span>
      <span class="cparam">days=${{c.days_back}} pct=[${{(c.pct_min*100).toFixed(0)}}%,${{(c.pct_max*100).toFixed(0)}}%]
        ath=[${{(c.ath_min*100).toFixed(0)}}%,${{(c.ath_max*100).toFixed(0)}}%]
        buys=${{c.max_buys}} drop=${{(c.buy_drop*100).toFixed(0)}}%
        tgt=${{(c.target*100).toFixed(0)}}% sl=${{(c.stoploss*100).toFixed(0)}}% dur=${{c.max_duration}}d</span>
    </div>
  `).join('');
  document.getElementById('configCards').innerHTML = configHTML;
  applyFilters();
  let secs = 300;
  setInterval(() => {{
    secs--;
    if (secs <= 0) {{ window.location.reload(); return; }}
    const m = Math.floor(secs/60), s = secs%60;
    document.getElementById('refreshBtn').textContent = `\u27f3 ${{m}}:${{String(s).padStart(2,'0')}}`;
  }}, 1000);
}}
function pct(v) {{
  if (v == null) return '\u2014';
  const cls = v >= 0 ? 'pos' : 'neg';
  return `<span class="${{cls}}">${{v >= 0 ? '+' : ''}}${{Number(v).toFixed(2)}}%</span>`;
}}
function badges(cfgs) {{
  return cfgs.split(',').map(c => `<span class="badge badge-${{c}}">${{c}}</span>`).join('');
}}
function countBadge(n) {{
  return `<span class="count-badge count-${{n}}">${{n}}</span>`;
}}
function renderTable() {{
  const tbody = document.getElementById('tableBody');
  const empty = document.getElementById('emptyState');
  if (!filtered.length) {{
    tbody.innerHTML = '';
    empty.style.display = '';
    document.getElementById('resultCount').textContent = '0 results';
    return;
  }}
  empty.style.display = 'none';
  document.getElementById('resultCount').textContent = `${{filtered.length}} result${{filtered.length !== 1 ? 's' : ''}}`;
  tbody.innerHTML = filtered.map((r, i) => `
    <tr>
      <td class="col-num">${{i+1}}</td>
      <td class="col-sym">${{r.SYMBOL}}</td>
      <td class="col-close">\u20b9${{Number(r.CLOSE).toLocaleString('en-IN', {{minimumFractionDigits:2, maximumFractionDigits:2}})}}</td>
      <td>${{pct(r.PCT_1D_CHANGE)}}</td>
      <td>${{pct(r.PCT_FROM_LOW)}}</td>
      <td>${{pct(r.PCT_FROM_ATH)}}</td>
      <td><div class="badges">${{badges(r.CONFIGS_MATCHED)}}</div></td>
      <td>${{countBadge(r.CONFIG_COUNT)}}</td>
    </tr>
  `).join('');
}}
function setFilter(mode, btn) {{
  filterMode = mode;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}
function applyFilters() {{
  const q = (document.getElementById('searchBox').value || '').trim().toUpperCase();
  filtered = allRows.filter(r => {{
    const symOk  = !q || r.SYMBOL.includes(q);
    const cntOk  = filterMode === 'all' || r.CONFIG_COUNT === parseInt(filterMode);
    return symOk && cntOk;
  }});
  sortData();
  renderTable();
}}
function sortTable(key) {{
  if (sortKey === key) sortDir = -sortDir;
  else {{ sortKey = key; sortDir = -1; }}
  sortData();
  renderTable();
}}
function sortData() {{
  filtered.sort((a, b) => {{
    const av = a[sortKey], bv = b[sortKey];
    if (typeof av === 'string') return sortDir * av.localeCompare(bv);
    return sortDir * ((av || 0) - (bv || 0));
  }});
}}
init();
</script>
</body>
</html>"""


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)

    csv_path  = f"{OUTPUT_DIR}/signals_latest.csv"
    meta_path = f"{OUTPUT_DIR}/meta.json"

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        rows_json = df.to_json(orient="records")
    else:
        rows_json = "[]"
        print("Warning: No signals_latest.csv found - building empty dashboard")

    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {
            "generated_at": datetime.now(tz=IST).strftime("%d-%b-%Y %H:%M IST"),
            "signal_date": "N/A",
            "total_signals": 0,
            "config_breakdown": {},
            "configs": [],
        }

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    configs = cfg["configs"]
    meta["configs"] = configs

    html = build_html(rows_json, meta, configs)

    out_path = f"{DOCS_DIR}/index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard built: {out_path}")


if __name__ == "__main__":
    main()
