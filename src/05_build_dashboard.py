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
<title>NSE BTST Signals Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<script>
  (function() {{
    if (window.location.search === '') {{
      window.location.replace(window.location.href + '?v=' + Date.now());
    }}
  }})();
</script>
<style>
:root{{
  --navy:#0d1f3c;--navy2:#162847;
  --blue:#1d4ed8;--blue2:#2563eb;
  --cyan:#0891b2;--cyan2:#06b6d4;
  --green:#059669;--red:#dc2626;--amber:#d97706;
  --surface:#fff;--surface2:#f1f5f9;--surface3:#e2e8f0;
  --text:#0f172a;--text2:#334155;--text3:#64748b;
  --border:#cbd5e1;
  --shadow:0 2px 12px rgba(13,31,60,.10);
  --shadow-lg:0 8px 32px rgba(13,31,60,.18);
  --radius:10px;--radius-lg:16px;
}}
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{height:100%;}}
body{{font-family:'Segoe UI',system-ui,Arial,sans-serif;background:#eef2f7;color:var(--text);font-size:14px;min-height:100vh;display:flex;flex-direction:column;}}

/* HEADER */
header{{background:linear-gradient(135deg,#0a1628 0%,#0d1f3c 50%,#162847 100%);padding:0;border-bottom:3px solid var(--cyan2);box-shadow:0 4px 24px rgba(0,0,0,.3);position:sticky;top:0;z-index:100;}}
.hdr{{max-width:1700px;margin:auto;display:flex;align-items:center;justify-content:space-between;padding:10px 24px;gap:16px;}}
.hdr-left{{display:flex;align-items:center;gap:14px;}}
.hdr-icon{{width:44px;height:44px;background:linear-gradient(135deg,var(--blue2),var(--cyan2));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 2px 8px rgba(37,99,235,.4);flex-shrink:0;}}
.hdr-sep{{width:1.5px;height:38px;background:rgba(255,255,255,.18);border-radius:2px;}}
.hdr-title .t1{{font-size:19px;font-weight:800;color:#fff;letter-spacing:.2px;line-height:1.2;}}
.hdr-title .t2{{font-size:10.5px;color:rgba(255,255,255,.55);font-weight:500;letter-spacing:.7px;margin-top:3px;}}
.hdr-right{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}}
.hdr-badge{{padding:5px 13px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);color:rgba(255,255,255,.85);white-space:nowrap;}}
.hdr-badge.date{{background:rgba(6,182,212,.15);border-color:rgba(6,182,212,.4);color:#67e8f9;}}
.hdr-badge.gen{{background:rgba(255,255,255,.07);font-weight:500;color:rgba(255,255,255,.65);font-size:10.5px;}}
.hdr-btn{{display:flex;align-items:center;gap:6px;padding:9px 18px;border-radius:8px;background:linear-gradient(135deg,var(--blue2),var(--cyan2));border:none;color:#fff;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(37,99,235,.4);transition:all .2s;}}
.hdr-btn:hover{{transform:translateY(-1px);box-shadow:0 4px 16px rgba(37,99,235,.6);}}

/* CONTAINER */
.container{{max-width:1700px;margin:auto;padding:18px 24px;flex:1;}}

/* CARD */
.card{{background:var(--surface);border-radius:var(--radius-lg);padding:20px;margin-bottom:16px;border:1.5px solid var(--border);box-shadow:var(--shadow);transition:box-shadow .25s,border-color .25s;}}
.card:hover{{box-shadow:var(--shadow-lg);border-color:#93c5fd;}}
.card-title{{font-size:14px;font-weight:700;color:var(--navy);margin-bottom:16px;display:flex;align-items:center;gap:8px;}}

/* TABS */
.tabs{{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 16px;background:var(--surface);border-radius:var(--radius-lg);padding:10px 12px;border:1.5px solid var(--border);box-shadow:var(--shadow);}}
.tab{{padding:7px 16px;border-radius:7px;border:1.5px solid var(--border);cursor:pointer;color:var(--text2);font-weight:600;font-size:12.5px;transition:all .18s;background:var(--surface2);white-space:nowrap;}}
.tab:hover{{background:var(--surface3);color:var(--text);}}
.tab.active{{background:linear-gradient(135deg,var(--navy),var(--navy2));color:#fff;border-color:var(--navy);box-shadow:0 2px 8px rgba(13,31,60,.25);}}

/* STATS */
.stats-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:14px;margin-bottom:16px;}}
.stat-card{{background:var(--surface);border-radius:var(--radius-lg);padding:18px 20px;border:1.5px solid var(--border);box-shadow:var(--shadow);text-align:center;transition:box-shadow .2s;}}
.stat-card:hover{{box-shadow:var(--shadow-lg);}}
.stat-label{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--text3);margin-bottom:6px;}}
.stat-value{{font-size:34px;font-weight:800;line-height:1;}}
.stat-sub{{font-size:11px;color:var(--text3);margin-top:5px;}}
.sv-blue{{color:var(--blue2);}} .sv-green{{color:var(--green);}} .sv-amber{{color:var(--amber);}}
.sv-red{{color:var(--red);}} .sv-muted{{color:var(--text3);}}

/* CONTROLS STRIP */
.cstrip{{background:var(--surface);border-radius:var(--radius-lg);padding:13px 18px;margin-bottom:14px;border:1.5px solid var(--border);box-shadow:var(--shadow);display:flex;flex-wrap:wrap;gap:10px;align-items:center;}}
.slbl{{font-size:11px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;}}
.sinput{{padding:7px 12px;border-radius:8px;border:1.5px solid var(--border);font-size:13px;color:var(--text);background:var(--surface2);outline:none;transition:border-color .18s;min-width:200px;}}
.sinput:focus{{border-color:var(--blue2);box-shadow:0 0 0 2px rgba(37,99,235,.12);}}
.sbtn{{padding:7px 14px;border-radius:8px;border:1.5px solid var(--border);background:var(--surface2);color:var(--text2);font-size:12.5px;font-weight:600;cursor:pointer;transition:all .18s;white-space:nowrap;}}
.sbtn:hover{{background:var(--surface3);color:var(--text);}}
.sbtn.active{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff;border-color:var(--blue2);box-shadow:0 2px 8px rgba(37,99,235,.25);}}
.sbtn.export-xl{{background:linear-gradient(135deg,#059669,#10b981);color:#fff;border-color:#059669;}}
.sbtn.export-xl:hover{{box-shadow:0 2px 8px rgba(5,150,105,.4);transform:translateY(-1px);}}
.sbtn.export-csv{{background:linear-gradient(135deg,#0891b2,#06b6d4);color:#fff;border-color:#0891b2;}}
.sbtn.export-csv:hover{{box-shadow:0 2px 8px rgba(8,145,178,.4);transform:translateY(-1px);}}
.res-count{{font-size:12px;color:var(--text3);margin-left:auto;font-weight:600;}}

/* TABLE */
.tbl-wrap{{overflow-x:auto;border-radius:var(--radius);border:1.5px solid var(--border);background:var(--surface);}}
table{{width:100%;border-collapse:collapse;font-size:13px;}}
thead th{{background:var(--surface2);padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid var(--border);white-space:nowrap;cursor:pointer;user-select:none;}}
thead th:hover{{color:var(--text);background:var(--surface3);}}
thead th.sort-asc::after{{content:' ↑';color:var(--blue2);}}
thead th.sort-desc::after{{content:' ↓';color:var(--blue2);}}
thead th.no-sort{{cursor:default;}}
thead th.no-sort:hover{{color:var(--text3);background:var(--surface2);}}
tbody tr{{border-bottom:1px solid var(--surface3);transition:background .1s;}}
tbody tr:hover{{background:var(--surface2);}}
tbody tr:last-child{{border-bottom:none;}}
tbody td{{padding:11px 14px;vertical-align:middle;}}
.col-num{{color:var(--text3);font-size:12px;width:44px;text-align:center;}}
.col-sym{{font-weight:800;font-size:14px;color:var(--navy);letter-spacing:.3px;}}
.col-price{{font-weight:700;font-family:'Courier New',monospace;color:var(--text);}}
.pos{{color:var(--green);font-weight:700;}} .neg{{color:var(--red);font-weight:700;}} .neutral{{color:var(--text3);}}

/* BADGES */
.badges{{display:flex;gap:4px;flex-wrap:wrap;}}
.badge{{font-size:10.5px;font-weight:700;padding:2px 9px;border-radius:10px;}}
.badge-C1{{background:rgba(29,78,216,.1);color:#1d4ed8;border:1px solid rgba(29,78,216,.25);}}
.badge-C2{{background:rgba(124,58,237,.1);color:#7c3aed;border:1px solid rgba(124,58,237,.25);}}
.badge-C3{{background:rgba(5,150,105,.1);color:#059669;border:1px solid rgba(5,150,105,.25);}}
.badge-C4{{background:rgba(217,119,6,.1);color:#d97706;border:1px solid rgba(217,119,6,.25);}}
.cnt-badge{{font-size:11px;font-weight:800;padding:3px 10px;border-radius:10px;}}
.cnt-4{{background:rgba(220,38,38,.12);color:var(--red);border:1px solid rgba(220,38,38,.3);}}
.cnt-3{{background:rgba(217,119,6,.12);color:var(--amber);border:1px solid rgba(217,119,6,.3);}}
.cnt-2{{background:rgba(29,78,216,.12);color:var(--blue);border:1px solid rgba(29,78,216,.3);}}
.cnt-1{{background:rgba(100,116,139,.12);color:var(--text3);border:1px solid rgba(100,116,139,.3);}}

/* CONFIG CARDS */
.cfg-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;}}
.cfg-card{{background:var(--surface2);border-radius:var(--radius-lg);border:1.5px solid var(--border);padding:20px;box-shadow:var(--shadow);transition:box-shadow .2s;}}
.cfg-card:hover{{box-shadow:var(--shadow-lg);}}
.cfg-card.c-C1{{border-top:4px solid #1d4ed8;}} .cfg-card.c-C2{{border-top:4px solid #7c3aed;}}
.cfg-card.c-C3{{border-top:4px solid #059669;}} .cfg-card.c-C4{{border-top:4px solid #d97706;}}
.cfg-id{{font-size:15px;font-weight:800;margin-bottom:12px;}}
.cfg-id.c-C1{{color:#1d4ed8;}} .cfg-id.c-C2{{color:#7c3aed;}} .cfg-id.c-C3{{color:#059669;}} .cfg-id.c-C4{{color:#d97706;}}
.cfg-row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);font-size:12.5px;}}
.cfg-row:last-child{{border-bottom:none;padding-bottom:0;}}
.cfg-key{{color:var(--text3);font-weight:600;}}
.cfg-val{{font-weight:700;color:var(--text);}}

/* TABPANEL */
.tabpanel{{display:none;}} .tabpanel.active{{display:block;}}

/* DISCLAIMER */
.disclaimer{{background:#fff8f0;border:1.5px solid #fed7aa;border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:16px;}}
.disclaimer h3{{color:var(--amber);font-size:15px;margin-bottom:12px;}}
.disclaimer p{{color:var(--text2);font-size:13.5px;line-height:1.65;margin-bottom:8px;}}
.disclaimer p:last-child{{margin-bottom:0;}}

/* HOW IT WORKS */
.how-box{{background:var(--surface2);border:1.5px solid var(--border);border-radius:var(--radius-lg);padding:18px 22px;}}
.how-box h4{{color:var(--navy);font-size:14px;font-weight:700;margin-bottom:10px;}}
.how-box ol{{margin-left:20px;}}
.how-box li{{color:var(--text2);font-size:13px;line-height:1.7;padding:2px 0;}}

/* EMPTY STATE */
.empty-state{{text-align:center;padding:80px 20px;color:var(--text3);}}
.empty-state .icon{{font-size:52px;margin-bottom:16px;}}
.empty-state h3{{font-size:18px;color:var(--text2);margin-bottom:8px;font-weight:700;}}
.empty-state p{{font-size:13px;}}

::-webkit-scrollbar{{width:6px;height:6px;}}
::-webkit-scrollbar-track{{background:var(--surface2);}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px;}}
</style>
</head>
<body>
<header>
  <div class="hdr">
    <div class="hdr-left">
      <div class="hdr-icon">📡</div>
      <div class="hdr-sep"></div>
      <div class="hdr-title">
        <div class="t1">NSE BTST Signals</div>
        <div class="t2">BUY TODAY SELL TOMORROW &nbsp;·&nbsp; DAILY SIGNAL SCANNER &nbsp;·&nbsp; 4 FIXED CONFIGS</div>
      </div>
    </div>
    <div class="hdr-right">
      <div class="hdr-badge date" id="sigDate">📅 —</div>
      <div class="hdr-badge gen" id="genTime">Generated: —</div>
      <button class="hdr-btn" onclick="window.location.reload()">↻ Refresh</button>
    </div>
  </div>
</header>

<div class="container">

  <!-- STATS ROW -->
  <div class="stats-row" id="statsRow"></div>

  <!-- TABS -->
  <div class="tabs">
    <div class="tab active" onclick="showTab('signals',this)">📡 Today's Signals</div>
    <div class="tab" onclick="showTab('configs',this)">⚙️ Parameter Configs</div>
    <div class="tab" onclick="showTab('about',this)">ℹ️ About</div>
  </div>

  <!-- TAB: SIGNALS -->
  <div class="tabpanel active" id="tab-signals">
    <div class="cstrip">
      <span class="slbl">Search:</span>
      <input class="sinput" id="searchBox" type="text" placeholder="🔍  Search symbol..." oninput="applyFilters()">
      <span class="slbl" style="margin-left:4px;">Filter:</span>
      <button class="sbtn active" onclick="setFilter('all',this)">All</button>
      <button class="sbtn" onclick="setFilter('4',this)">★★★★ 4 Configs</button>
      <button class="sbtn" onclick="setFilter('3',this)">★★★ 3 Configs</button>
      <button class="sbtn" onclick="setFilter('2',this)">★★ 2 Configs</button>
      <button class="sbtn" onclick="setFilter('1',this)">★ 1 Config</button>
      <button class="sbtn export-xl" onclick="exportExcel()">⬇ Export Excel</button>
      <button class="sbtn export-csv" onclick="exportCSV()">⬇ Export CSV</button>
      <span class="res-count" id="resultCount"></span>
    </div>
    <div class="tbl-wrap">
      <table id="mainTable">
        <thead>
          <tr>
            <th class="no-sort col-num">#</th>
            <th onclick="sortTable('SYMBOL')">Symbol</th>
            <th onclick="sortTable('CLOSE')">Close ₹</th>
            <th onclick="sortTable('PCT_1D_CHANGE')">1D Chg %</th>
            <th onclick="sortTable('PCT_FROM_LOW')">% from 10D Low</th>
            <th onclick="sortTable('PCT_FROM_ATH')">% from ATH</th>
            <th class="no-sort">Configs Matched</th>
            <th onclick="sortTable('CONFIG_COUNT')">Count</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
      <div class="empty-state" id="emptyState" style="display:none">
        <div class="icon">📭</div>
        <h3>No signals found</h3>
        <p>Run the <strong>Bootstrap</strong> or <strong>Daily Signals</strong> workflow on GitHub Actions to generate signals.</p>
      </div>
    </div>
  </div>

  <!-- TAB: CONFIGS -->
  <div class="tabpanel" id="tab-configs">
    <div class="card">
      <div class="card-title">⚙️ Active Parameter Configurations</div>
      <div class="cfg-grid" id="configGrid"></div>
    </div>
  </div>

  <!-- TAB: ABOUT -->
  <div class="tabpanel" id="tab-about">
    <div class="card">
      <div class="card-title">ℹ️ About NSE BTST Signals Dashboard</div>
      <div class="disclaimer">
        <h3>⚠️ Disclaimer</h3>
        <p>This dashboard is strictly for <strong>educational and informational purposes only</strong>.</p>
        <p>All stock market views, trading ideas and analysis shown are <strong>personal opinions</strong> based on technical and historical data. They should <strong>NOT</strong> be considered as investment advice.</p>
        <p><strong>Past performance is not a guarantee of future results.</strong></p>
        <p>I am <strong>NOT responsible</strong> for any profit, loss, or damages arising from the use of this dashboard.</p>
        <p><strong>I am NOT a SEBI registered advisor.</strong> Please consult a certified financial advisor before investing.</p>
        <p>By using this dashboard, you acknowledge and agree to this disclaimer.</p>
      </div>
      <div class="how-box" style="margin-top:16px;">
        <h4>🔧 How it works</h4>
        <ol>
          <li>Every weekday at <strong>9:00 PM IST</strong>, the automated workflow triggers automatically.</li>
          <li>It downloads the latest NSE bhavcopy (EQ segment price data).</li>
          <li>Computes 10-day low proximity and All-Time-High (ATH) distance for every stock.</li>
          <li>Each stock is tested against all <strong>4 parameter configurations</strong>.</li>
          <li>Stocks matching one or more configs are reported as BTST signals.</li>
          <li>Duplicate entries are removed — each symbol appears only <strong>once</strong> with all matched configs shown.</li>
          <li>This dashboard is rebuilt and published automatically after every run.</li>
        </ol>
      </div>
    </div>
  </div>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<script>
const META    = {meta_json};
const SIGNALS = {rows_json};
const CONFIGS = {configs_json};

let allRows    = [...SIGNALS];
let filtered   = [...allRows];
let filterMode = 'all';
let sortKey    = 'CONFIG_COUNT';
let sortDir    = -1;

function showTab(id, el) {{
  document.querySelectorAll('.tabpanel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  el.classList.add('active');
}}

function init() {{
  document.getElementById('sigDate').textContent  = '📅 ' + (META.signal_date || '—');
  document.getElementById('genTime').textContent  = 'Generated: ' + (META.generated_at || '—');

  const total = allRows.length;
  const c4 = allRows.filter(r => r.CONFIG_COUNT === 4).length;
  const c3 = allRows.filter(r => r.CONFIG_COUNT === 3).length;
  const c2 = allRows.filter(r => r.CONFIG_COUNT === 2).length;
  const c1 = allRows.filter(r => r.CONFIG_COUNT === 1).length;

  document.getElementById('statsRow').innerHTML = `
    <div class="stat-card"><div class="stat-label">Total Signals</div><div class="stat-value sv-blue">${{total}}</div><div class="stat-sub">Unique stocks today</div></div>
    <div class="stat-card"><div class="stat-label">★★★★ 4 Configs</div><div class="stat-value sv-red">${{c4}}</div><div class="stat-sub">Strongest match</div></div>
    <div class="stat-card"><div class="stat-label">★★★ 3 Configs</div><div class="stat-value sv-amber">${{c3}}</div><div class="stat-sub">Strong match</div></div>
    <div class="stat-card"><div class="stat-label">★★ 2 Configs</div><div class="stat-value sv-blue">${{c2}}</div><div class="stat-sub">Moderate match</div></div>
    <div class="stat-card"><div class="stat-label">★ 1 Config</div><div class="stat-value sv-muted">${{c1}}</div><div class="stat-sub">Weak match</div></div>
  `;

  const cfgHTML = CONFIGS.map(c => `
    <div class="cfg-card c-${{c.id}}">
      <div class="cfg-id c-${{c.id}}">${{c.id}} — ${{c.name}}</div>
      <div class="cfg-row"><span class="cfg-key">Days Back</span><span class="cfg-val">${{c.days_back}} days</span></div>
      <div class="cfg-row"><span class="cfg-key">PCT Range</span><span class="cfg-val">${{(c.pct_min*100).toFixed(1)}}% to ${{(c.pct_max*100).toFixed(1)}}%</span></div>
      <div class="cfg-row"><span class="cfg-key">ATH Range</span><span class="cfg-val">${{(c.ath_min*100).toFixed(1)}}% to ${{(c.ath_max*100).toFixed(1)}}%</span></div>
      <div class="cfg-row"><span class="cfg-key">Max Buys</span><span class="cfg-val">${{c.max_buys}}</span></div>
      <div class="cfg-row"><span class="cfg-key">Buy Drop</span><span class="cfg-val">${{(c.buy_drop*100).toFixed(0)}}%</span></div>
      <div class="cfg-row"><span class="cfg-key">Target</span><span class="cfg-val">${{(c.target*100).toFixed(0)}}%</span></div>
      <div class="cfg-row"><span class="cfg-key">Stop Loss</span><span class="cfg-val">${{(c.stoploss*100).toFixed(0)}}%</span></div>
      <div class="cfg-row"><span class="cfg-key">Max Duration</span><span class="cfg-val">${{c.max_duration}} days</span></div>
    </div>
  `).join('');
  document.getElementById('configGrid').innerHTML = cfgHTML;

  applyFilters();
}}

function pct(v) {{
  if (v == null || v === '') return '<span class="neutral">—</span>';
  const cls = v >= 0 ? 'pos' : 'neg';
  return `<span class="${{cls}}">${{v >= 0 ? '+' : ''}}${{Number(v).toFixed(2)}}%</span>`;
}}

function badges(cfgs) {{
  if (!cfgs) return '';
  return cfgs.split(',').map(c => c.trim()).filter(Boolean)
    .map(c => `<span class="badge badge-${{c}}">${{c}}</span>`).join('');
}}

function countBadge(n) {{
  return `<span class="cnt-badge cnt-${{n}}">${{n}}</span>`;
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
      <td class="col-price">₹${{Number(r.CLOSE).toLocaleString('en-IN',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}</td>
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
  document.querySelectorAll('.sbtn:not(.export-xl):not(.export-csv)').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  const q = (document.getElementById('searchBox').value || '').trim().toUpperCase();
  filtered = allRows.filter(r => {{
    const symOk = !q || r.SYMBOL.includes(q);
    const cntOk = filterMode === 'all' || r.CONFIG_COUNT === parseInt(filterMode);
    return symOk && cntOk;
  }});
  sortData();
  renderTable();
  updateSortHeaders();
}}

function sortTable(key) {{
  if (sortKey === key) sortDir = -sortDir;
  else {{ sortKey = key; sortDir = -1; }}
  sortData();
  renderTable();
  updateSortHeaders();
}}

function sortData() {{
  filtered.sort((a, b) => {{
    const av = a[sortKey], bv = b[sortKey];
    if (typeof av === 'string') return sortDir * av.localeCompare(bv);
    return sortDir * ((av || 0) - (bv || 0));
  }});
}}

function updateSortHeaders() {{
  document.querySelectorAll('thead th').forEach(th => th.classList.remove('sort-asc','sort-desc'));
  const keyMap = {{'SYMBOL':1,'CLOSE':2,'PCT_1D_CHANGE':3,'PCT_FROM_LOW':4,'PCT_FROM_ATH':5,'CONFIG_COUNT':7}};
  const idx = keyMap[sortKey];
  if (idx !== undefined) {{
    const th = document.querySelectorAll('thead th')[idx];
    if (th) th.classList.add(sortDir === -1 ? 'sort-desc' : 'sort-asc');
  }}
}}

function exportExcel() {{
  if (!filtered.length) {{ alert('No data to export.'); return; }}
  const wsData = [['#','Symbol','Close ₹','1D Chg %','% from 10D Low','% from ATH','Configs Matched','Count']];
  filtered.forEach((r,i) => wsData.push([
    i+1, r.SYMBOL,
    Number(r.CLOSE).toFixed(2),
    r.PCT_1D_CHANGE != null ? Number(r.PCT_1D_CHANGE).toFixed(2) : '',
    r.PCT_FROM_LOW  != null ? Number(r.PCT_FROM_LOW).toFixed(2)  : '',
    r.PCT_FROM_ATH  != null ? Number(r.PCT_FROM_ATH).toFixed(2)  : '',
    r.CONFIGS_MATCHED, r.CONFIG_COUNT
  ]));
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Signals');
  const dateStr = (META.signal_date || 'latest').replace(/-/g,'');
  XLSX.writeFile(wb, `NSE_BTST_Signals_${{dateStr}}.xlsx`);
}}

function exportCSV() {{
  if (!filtered.length) {{ alert('No data to export.'); return; }}
  const rows = [['#','Symbol','Close','PCT_1D_CHANGE','PCT_FROM_LOW','PCT_FROM_ATH','CONFIGS_MATCHED','CONFIG_COUNT']];
  filtered.forEach((r,i) => rows.push([
    i+1,r.SYMBOL,r.CLOSE,r.PCT_1D_CHANGE,r.PCT_FROM_LOW,r.PCT_FROM_ATH,r.CONFIGS_MATCHED,r.CONFIG_COUNT
  ]));
  const csv = rows.map(r => r.join(',')).join('\n');
  const a   = document.createElement('a');
  a.href     = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
  const dateStr = (META.signal_date || 'latest').replace(/-/g,'');
  a.download = `NSE_BTST_Signals_${{dateStr}}.csv`;
  a.click();
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
