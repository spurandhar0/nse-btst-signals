#!/usr/bin/env python3
"""
NSE BTST Signals — Dashboard Builder v2
Matches the style of the existing nse-btst-dashboard exactly.
"""
import os, json, sys
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── paths ──────────────────────────────────────────────────────────────────────
BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(BASE, 'config', 'params.json')
SIGS   = os.path.join(BASE, 'output', 'signals_latest.csv')
NIFTY  = os.path.join(BASE, 'data',   'nifty_index.json')
OUT    = os.path.join(BASE, 'docs',   'index.html')

# ── logo (inline, same as existing dashboard) ─────────────────────────────────
LOGO_PATH = os.path.join(BASE, 'docs', 'logo_b64.txt')

def load_logo():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH) as f:
            return f.read().strip()
    return ''

def load_signals():
    rows = []
    if not os.path.exists(SIGS):
        return rows, 'No signals yet'
    try:
        import csv
        with open(SIGS, newline='') as f:
            for r in csv.DictReader(f):
                rows.append(r)
        date_vals = [r.get('SIGNAL_DATE','') for r in rows if r.get('SIGNAL_DATE')]
        sig_date  = max(date_vals) if date_vals else '—'
        return rows, sig_date
    except Exception as e:
        return [], f'Error: {e}'

def load_configs():
    try:
        with open(CONFIG) as f:
            d = json.load(f)
        return d.get('configs', [])
    except:
        return []

def load_nifty():
    try:
        with open(NIFTY) as f:
            return json.load(f)
    except:
        return {}

def build_html(rows_json, meta, configs, nifty, logo):
    configs_json = json.dumps(configs)
    nifty_json   = json.dumps(nifty)
    generated    = meta.get('generated_at', '—')
    sig_date     = meta.get('signal_date',  '—')
    total        = meta.get('total_signals', 0)
    breakdown    = meta.get('config_breakdown', {})
    c1 = breakdown.get('C1', 0)
    c2 = breakdown.get('C2', 0)
    c3 = breakdown.get('C3', 0)
    c4 = breakdown.get('C4', 0)

    # build config table rows
    cfg_rows_html = ''
    for c in configs:
        cfg_rows_html += f"""
        <tr>
          <td><span class="cfg-badge">{c.get('id','')}</span></td>
          <td>{c.get('days_back','')}</td>
          <td>{c.get('pct_min','')}</td>
          <td>{c.get('pct_max','')}</td>
          <td>{c.get('ath_min','')}</td>
          <td>{c.get('ath_max','')}</td>
          <td>{c.get('max_buys','')}</td>
          <td>{c.get('buy_drop','')}</td>
          <td>{c.get('target','')}</td>
          <td>{c.get('stoploss','')}</td>
          <td>{c.get('max_duration','')}</td>
        </tr>"""

    logo_src = logo if logo else ''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PS Market — NSE BTST Signals</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<script>
  (function(){{
    var ts=new Date().getTime();
    if(window.location.search===''){{
      window.location.replace(window.location.href+'?v='+ts);
    }}
  }})();
</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
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
.flex1{{flex:1;}}

/* HEADER */
header{{background:linear-gradient(135deg,#0a1628 0%,#0d1f3c 50%,#162847 100%);padding:0;border-bottom:3px solid var(--cyan2);box-shadow:0 4px 24px rgba(0,0,0,.3);position:sticky;top:0;z-index:100;}}
.hdr{{max-width:1700px;margin:auto;display:flex;align-items:center;justify-content:space-between;padding:10px 24px;gap:16px;}}
.hdr-left{{display:flex;align-items:center;gap:14px;}}
.hdr-logo{{height:42px;width:auto;background:#fff;border-radius:8px;padding:3px 8px;box-shadow:0 1px 4px rgba(0,0,0,0.15);}}
.hdr-sep{{width:1.5px;height:38px;background:rgba(255,255,255,.18);border-radius:2px;}}
.hdr-title .t1{{font-size:19px;font-weight:800;color:#fff;letter-spacing:.2px;line-height:1.2;}}
.hdr-title .t2{{font-size:10.5px;color:rgba(255,255,255,.55);font-weight:500;letter-spacing:.7px;margin-top:3px;}}
.hdr-right{{display:flex;align-items:center;gap:10px;}}
.hdr-badge{{padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);color:rgba(255,255,255,.85);white-space:nowrap;}}
.hdr-btn{{display:flex;align-items:center;gap:6px;padding:9px 18px;border-radius:8px;background:linear-gradient(135deg,var(--blue2),var(--cyan2));border:none;color:#fff;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(37,99,235,.4);transition:all .2s;}}
.hdr-btn:hover{{transform:translateY(-1px);box-shadow:0 4px 16px rgba(37,99,235,.6);}}

/* INDICES BAR */
.idx-bar{{background:linear-gradient(135deg,#0a1628,#0d1f3c);border-bottom:1px solid rgba(255,255,255,.08);padding:7px 24px;}}
.idx-inner{{max-width:1700px;margin:auto;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}}
.idx-label{{font-size:10px;font-weight:800;color:rgba(255,255,255,.4);letter-spacing:1px;text-transform:uppercase;margin-right:4px;}}
.idx-card{{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.13);border-radius:9px;padding:6px 14px;cursor:default;}}
.idx-name{{font-size:11px;font-weight:800;color:rgba(255,255,255,.6);letter-spacing:.5px;text-transform:uppercase;}}
.idx-price{{font-size:17px;font-weight:900;color:#fff;line-height:1;}}
.idx-chg{{font-size:11px;font-weight:700;white-space:nowrap;padding:2px 7px;border-radius:12px;}}
.idx-chg.pos{{background:rgba(5,150,105,.25);color:#10b981;}}
.idx-chg.neg{{background:rgba(220,38,38,.25);color:#ef4444;}}
.idx-chg.flat{{background:rgba(100,116,139,.2);color:#94a3b8;}}
.idx-date{{font-size:10px;color:rgba(255,255,255,.35);font-weight:500;}}
.idx-loading{{font-size:11px;color:rgba(255,255,255,.4);font-style:italic;}}

/* LIVE BANNER */
#liveBanner{{display:flex;align-items:center;justify-content:center;padding:8px 20px;background:rgba(5,150,105,.08);border-bottom:2px solid var(--green);font-size:13px;font-weight:600;color:var(--green);gap:8px;}}
#liveBanner.warn{{background:rgba(217,119,6,.08);border-color:var(--amber);color:var(--amber);}}

/* CONTAINER */
.container{{flex:1;max-width:1700px;margin:auto;padding:18px 24px;}}

/* CARD */
.card{{background:var(--surface);border-radius:var(--radius-lg);padding:20px;margin-bottom:16px;border:1.5px solid var(--border);box-shadow:var(--shadow);transition:box-shadow .25s,border-color .25s;}}
.card:hover{{box-shadow:var(--shadow-lg);border-color:#93c5fd;}}

/* CONTROLS STRIP */
.cstrip{{background:var(--surface);border-radius:var(--radius-lg);padding:13px 18px;margin-bottom:14px;border:1.5px solid var(--border);box-shadow:var(--shadow);display:flex;flex-wrap:wrap;gap:10px;align-items:center;}}
.slbl{{font-size:11px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;}}

/* TABS */
.tabs{{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 16px;background:var(--surface);border-radius:var(--radius-lg);padding:10px 12px;border:1.5px solid var(--border);box-shadow:var(--shadow);}}
.tab{{padding:7px 14px;border-radius:7px;border:1.5px solid var(--border);cursor:pointer;color:var(--text2);font-weight:600;font-size:12.5px;transition:all .18s;background:var(--surface2);white-space:nowrap;}}
.tab:hover{{border-color:var(--blue2);color:var(--blue2);background:#eff6ff;transform:translateY(-1px);}}
.tab.active{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff;border-color:var(--blue2);box-shadow:0 3px 10px rgba(37,99,235,.3);}}

/* STAT CARDS */
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:11px;margin-bottom:18px;}}
.stat-card{{background:linear-gradient(135deg,#f8faff,#eef2ff);border:1.5px solid #c7d7fe;border-radius:var(--radius);padding:14px 16px;text-align:center;transition:transform .18s;}}
.stat-card:hover{{transform:translateY(-2px);}}
.stat-val{{font-size:25px;font-weight:900;color:var(--blue2);line-height:1.1;}}
.stat-lbl{{font-size:10.5px;color:var(--text3);font-weight:600;margin-top:4px;text-transform:uppercase;letter-spacing:.4px;}}
.stat-card.gc{{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#86efac;}}.stat-card.gc .stat-val{{color:var(--green);}}
.stat-card.rc{{background:linear-gradient(135deg,#fff1f2,#ffe4e6);border-color:#fca5a5;}}.stat-card.rc .stat-val{{color:var(--red);}}
.stat-card.ac{{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fcd34d;}}.stat-card.ac .stat-val{{color:var(--amber);}}

/* TABLES */
.table-area{{overflow-x:auto;border-radius:var(--radius);}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;}}
thead th{{background:linear-gradient(135deg,#0d1f3c,#1e3a6e);color:#fff;padding:10px 9px;text-align:center;font-weight:700;font-size:11.5px;letter-spacing:.3px;position:sticky;top:0;z-index:2;white-space:nowrap;cursor:pointer;user-select:none;}}
thead th:first-child{{border-radius:8px 0 0 0;}}thead th:last-child{{border-radius:0 8px 0 0;}}
thead th:hover{{background:linear-gradient(135deg,#162847,#254a8a);}}
tbody tr{{transition:background .12s;}}
tbody tr:nth-child(even){{background:#f8fafc;}}
tbody tr:nth-child(odd){{background:#fff;}}
tbody tr:hover{{background:#eff6ff;}}
tbody td{{padding:8px 9px;text-align:center;border-bottom:1px solid #e9edf4;font-size:12px;}}

/* BADGES */
.badges{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 13px;}}
.badge{{padding:5px 13px;border-radius:20px;font-weight:700;font-size:11.5px;border:1.5px solid var(--blue2);color:var(--blue2);background:rgba(37,99,235,.07);}}
.badge.green{{border-color:var(--green);color:var(--green);background:rgba(5,150,105,.07);}}
.badge.red{{border-color:var(--red);color:var(--red);background:rgba(220,38,38,.07);}}
.badge.amber{{border-color:var(--amber);color:var(--amber);background:rgba(217,119,6,.07);}}
.cfg-badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:800;background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff;}}
.star-badge{{color:#f59e0b;font-weight:700;}}

/* UTILITY */
.green{{color:#059669;font-weight:700;}}.red{{color:#dc2626;font-weight:700;}}
.hidden{{display:none!important;}}
.empty{{padding:40px;text-align:center;color:var(--text3);font-size:15px;}}
.row{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;}}
.export{{display:flex;gap:8px;flex-wrap:wrap;}}
.pager{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:10px;font-size:13px;}}
.pager .info{{color:var(--text3);font-weight:600;}}

/* BUTTONS */
button{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));border:none;padding:8px 16px;border-radius:8px;font-weight:700;color:#fff;cursor:pointer;font-size:13px;transition:all .2s;box-shadow:0 2px 6px rgba(37,99,235,.3);}}
button:hover{{transform:translateY(-1px);box-shadow:0 4px 14px rgba(37,99,235,.5);}}
.btn-sm{{padding:5px 11px;font-size:12px;}}
.btn-outline{{background:transparent;border:1.5px solid var(--blue2);color:var(--blue2);box-shadow:none;}}
.btn-outline:hover{{background:var(--blue2);color:#fff;}}
.btn-green{{background:linear-gradient(135deg,#059669,#10b981);}}
.btn-teal{{background:linear-gradient(135deg,#0891b2,#06b6d4);}}
.btn-filter{{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;border:1.5px solid var(--border);background:var(--surface2);color:var(--text2);cursor:pointer;transition:all .18s;}}
.btn-filter.active,.btn-filter:hover{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff;border-color:var(--blue2);}}

/* INPUTS */
select,input[type="date"],input[type="text"]{{padding:7px 11px;border-radius:8px;background:var(--surface);color:var(--text);border:1.5px solid var(--border);font-weight:600;font-size:13px;cursor:pointer;transition:all .2s;}}
select:focus,input:focus{{border-color:var(--blue2);outline:none;box-shadow:0 0 0 3px rgba(37,99,235,.1);}}

/* TOAST */
#toast-container{{position:fixed;bottom:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:6px;max-width:300px;pointer-events:none;}}
.toast{{padding:8px 12px;border-radius:8px;font-weight:600;font-size:12px;color:#fff;box-shadow:0 4px 12px rgba(0,0,0,.18);animation:slideIn .25s ease;pointer-events:auto;}}
.toast.success{{background:linear-gradient(135deg,#059669,#10b981);}}
.toast.info{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));}}
@keyframes slideIn{{from{{transform:translateX(110%);opacity:0}}to{{transform:none;opacity:1}}}}
@keyframes fadeOut{{to{{opacity:0;transform:translateX(30%)}}}}

/* FOOTER */
footer{{background:var(--navy);color:rgba(255,255,255,.5);text-align:center;padding:14px;font-size:12px;border-top:2px solid rgba(255,255,255,.08);}}
footer a{{color:rgba(255,255,255,.7);text-decoration:none;}}

/* DISCLAIMER */
.disclaimer-box{{background:linear-gradient(135deg,#fff7ed,#fff);border:1.5px solid #fed7aa;border-radius:var(--radius-lg);padding:24px 28px;}}
.disclaimer-box h2{{color:#c2410c;margin-bottom:16px;font-size:16px;}}
.disclaimer-box p{{color:var(--text2);line-height:1.7;margin-bottom:10px;font-size:13.5px;}}
.disclaimer-box strong{{color:var(--text);}}

/* CONFIG TABLE */
.cfg-table thead th{{font-size:11px;}}
.cfg-table tbody td{{font-size:12px;}}

@media(max-width:768px){{
  .hdr{{padding:9px 12px;gap:8px;}}.hdr-logo{{height:34px;}}.hdr-title .t1{{font-size:14px;}}
  .container{{padding:12px;}}
  .stat-grid{{grid-template-columns:repeat(2,1fr);}}
}}
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <div class="hdr">
    <div class="hdr-left">
      {'<img class="hdr-logo" src="' + logo_src + '" alt="PS Market">' if logo_src else '<div class="hdr-title"><div class="t1">PS MARKET</div></div>'}
      <div class="hdr-sep"></div>
      <div class="hdr-title">
        <div class="t1">NSE BTST Signals</div>
        <div class="t2">DAILY SIGNAL SCANNER &middot; 4 FIXED CONFIGS</div>
      </div>
    </div>
    <div class="hdr-right">
      <span class="hdr-badge" id="liveStatus">&#9679; {generated}</span>
      <button class="hdr-btn" onclick="location.reload()">&#8635; Refresh</button>
    </div>
  </div>
</header>

<!-- INDICES BAR -->
<div class="idx-bar">
  <div class="idx-inner">
    <span class="idx-label">&#9776; INDICES</span>
    <div id="idx-nifty50" class="idx-card"><span class="idx-loading">Loading NIFTY 50&hellip;</span></div>
    <div id="idx-banknifty" class="idx-card"><span class="idx-loading">Loading BANKNIFTY&hellip;</span></div>
    <div id="idx-sensex" class="idx-card"><span class="idx-loading">Loading SENSEX&hellip;</span></div>
    <div id="idx-niftyit" class="idx-card"><span class="idx-loading">Loading NIFTY IT&hellip;</span></div>
  </div>
</div>

<!-- LIVE BANNER -->
<div id="liveBanner">
  <span>&#10003; Signal date &mdash; <strong id="sigDateBanner">{sig_date}</strong> &nbsp;|&nbsp; Generated: {generated}</span>
</div>

<div class="container flex1">

  <!-- TABS -->
  <div class="tabs">
    <div class="tab active" onclick="switchTab('signals',this)">&#9654; Today's Signals</div>
    <div class="tab" onclick="switchTab('configs',this)">&#9881; Parameter Configs</div>
    <div class="tab" onclick="switchTab('disclaimer',this)">&#9432; Disclaimer</div>
  </div>

  <!-- ═══ TAB: SIGNALS ═══ -->
  <div id="tab-signals">

    <!-- STAT CARDS -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-val">{total}</div>
        <div class="stat-lbl">Total Signals</div>
      </div>
      <div class="stat-card gc">
        <div class="stat-val">{c1}</div>
        <div class="stat-lbl">★★★★ All 4 Configs</div>
      </div>
      <div class="stat-card ac">
        <div class="stat-val">{c1+c2 if isinstance(c1,int) and isinstance(c2,int) else '—'}</div>
        <div class="stat-lbl">★★★ 3+ Configs</div>
      </div>
      <div class="stat-card rc">
        <div class="stat-val" id="statDate">{sig_date}</div>
        <div class="stat-lbl">Signal Date</div>
      </div>
    </div>

    <!-- SEARCH + FILTER + EXPORT -->
    <div class="cstrip">
      <span class="slbl">Search:</span>
      <input type="text" id="searchBox" placeholder="Search symbol..." oninput="applyFilters()" style="width:200px;">
      <span class="slbl" style="margin-left:8px;">Filter:</span>
      <button class="btn-filter active" id="fAll" onclick="setFilter('all',this)">All</button>
      <button class="btn-filter" id="f4" onclick="setFilter('4',this)">&#9733;&#9733;&#9733;&#9733; 4 Configs</button>
      <button class="btn-filter" id="f3" onclick="setFilter('3',this)">&#9733;&#9733;&#9733; 3 Configs</button>
      <button class="btn-filter" id="f2" onclick="setFilter('2',this)">&#9733;&#9733; 2 Configs</button>
      <button class="btn-filter" id="f1" onclick="setFilter('1',this)">&#9733; 1 Config</button>
      <div style="flex:1;"></div>
      <div class="export">
        <button class="btn-green btn-sm" onclick="exportExcel()">&#8595; Export Excel</button>
        <button class="btn-teal btn-sm" onclick="exportCSV()">&#8595; Export CSV</button>
      </div>
    </div>

    <!-- SIGNALS TABLE -->
    <div class="card" style="padding:0 0 12px;">
      <div class="table-area">
        <table id="sigTable">
          <thead>
            <tr>
              <th onclick="sortTable(0)">#</th>
              <th onclick="sortTable(1)">SYMBOL</th>
              <th onclick="sortTable(2)">CLOSE &#8377;</th>
              <th onclick="sortTable(3)">1D CHG %</th>
              <th onclick="sortTable(4)">% FROM {'{'}DAYS_BACK{'}'}D LOW</th>
              <th onclick="sortTable(5)">% FROM ATH</th>
              <th onclick="sortTable(6)">CONFIGS MATCHED</th>
              <th onclick="sortTable(7)">COUNT</th>
            </tr>
          </thead>
          <tbody id="sigBody"></tbody>
        </table>
      </div>
      <div class="pager" style="padding:0 16px;">
        <span class="info" id="pagerInfo"></span>
        <div style="flex:1;"></div>
        <button class="btn-sm btn-outline" onclick="prevPage()">&#8249; Prev</button>
        <button class="btn-sm btn-outline" onclick="nextPage()">Next &#8250;</button>
        <select id="pgSize" onchange="applyFilters()">
          <option value="25">25</option>
          <option value="50">50</option>
          <option value="100" selected>100</option>
          <option value="999999">All</option>
        </select>
      </div>
    </div>

  </div><!-- end tab-signals -->

  <!-- ═══ TAB: CONFIGS ═══ -->
  <div id="tab-configs" class="hidden">
    <div class="card">
      <h3 style="color:var(--navy);margin-bottom:16px;font-size:16px;">&#9881; Parameter Configurations</h3>
      <p style="color:var(--text3);margin-bottom:16px;font-size:13px;">
        These 4 fixed configurations are scanned every trading day. A stock that appears in more configurations is considered a stronger signal.
      </p>
      <div class="table-area">
        <table class="cfg-table">
          <thead>
            <tr>
              <th>CONFIG</th><th>DAYS BACK</th><th>PCT MIN</th><th>PCT MAX</th>
              <th>ATH MIN</th><th>ATH MAX</th><th>MAX BUYS</th><th>BUY DROP</th>
              <th>TARGET</th><th>STOP LOSS</th><th>MAX DURATION</th>
            </tr>
          </thead>
          <tbody>{cfg_rows_html}</tbody>
        </table>
      </div>
      <div style="margin-top:20px;padding:16px;background:#f8faff;border-radius:10px;border:1.5px solid #c7d7fe;">
        <p style="font-size:12.5px;color:var(--text2);line-height:1.7;">
          <strong>DAYS BACK:</strong> Look-back window for N-day low<br>
          <strong>PCT MIN/MAX:</strong> % change from N-day low range<br>
          <strong>ATH MIN/MAX:</strong> % from All-Time-High range<br>
          <strong>MAX BUYS:</strong> Max averaging positions<br>
          <strong>BUY DROP:</strong> Drop % to trigger next buy<br>
          <strong>TARGET/STOP LOSS:</strong> Exit thresholds<br>
          <strong>MAX DURATION:</strong> Max holding days before forced exit
        </p>
      </div>
    </div>
  </div>

  <!-- ═══ TAB: DISCLAIMER ═══ -->
  <div id="tab-disclaimer" class="hidden">
    <div class="disclaimer-box">
      <h2>&#9888; Disclaimer</h2>
      <p>This dashboard is strictly for <strong>educational and informational purposes only</strong>.</p>
      <p>All stock market views, trading ideas and analysis shown are <strong>personal opinions</strong> based on technical and historical data. They should <strong>NOT</strong> be considered as investment advice.</p>
      <p><strong>Past performance is not a guarantee of future results.</strong></p>
      <p>I am <strong>NOT responsible</strong> for any profit, loss, or damages arising from the use of this dashboard.</p>
      <p><strong>I am NOT a SEBI registered advisor.</strong> Please consult a certified financial advisor before investing.</p>
      <p>By using this dashboard, you acknowledge and agree to this disclaimer.</p>
    </div>
  </div>

</div><!-- end container -->

<footer>
  <strong>PS Market</strong> &mdash; NSE BTST Signals &nbsp;|&nbsp; Educational Purpose Only &nbsp;|&nbsp; Not SEBI Registered
</footer>

<div id="toast-container"></div>

<script>
// ── DATA ──────────────────────────────────────────────────────────────────────
const RAW_SIGNALS = {rows_json};
const CONFIGS     = {configs_json};
const NIFTY_DATA  = {nifty_json};

// ── INDICES ───────────────────────────────────────────────────────────────────
(function loadIndices(){{
  const map = {{
    'idx-nifty50':   {{key:'nifty50',   label:'NIFTY 50'}},
    'idx-banknifty': {{key:'banknifty', label:'BANKNIFTY'}},
    'idx-sensex':    {{key:'sensex',    label:'SENSEX'}},
    'idx-niftyit':   {{key:'niftyit',   label:'NIFTY IT'}},
  }};
  Object.entries(map).forEach(([id, {{key,label}}])=>{{
    const el = document.getElementById(id);
    const d  = NIFTY_DATA[key];
    if(!d || !d.price){{ el.innerHTML='<span class="idx-loading">'+label+' N/A</span>'; return; }}
    const chg   = d.change || 0;
    const chgPc = d.change_pct || 0;
    const cls   = chg>0?'pos':chg<0?'neg':'flat';
    const sign  = chg>0?'+':'';
    el.innerHTML=`
      <div>
        <div class="idx-name">${{label}}</div>
        <div class="idx-date">${{d.date||''}}</div>
      </div>
      <div>
        <div class="idx-price">${{Number(d.price).toLocaleString('en-IN',{{maximumFractionDigits:2}})}}</div>
        <div class="idx-chg ${{cls}}">${{sign}}${{Number(chg).toFixed(2)}} (${{sign}}${{Number(chgPc).toFixed(2)}}%)</div>
      </div>`;
  }});
}})();

// ── TAB SWITCHING ─────────────────────────────────────────────────────────────
function switchTab(name, el){{
  document.querySelectorAll('[id^="tab-"]').forEach(t=>t.classList.add('hidden'));
  document.getElementById('tab-'+name).classList.remove('hidden');
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
}}

// ── TABLE STATE ───────────────────────────────────────────────────────────────
let filtered   = [];
let sortCol    = 7;   // COUNT column default
let sortAsc    = false;
let curPage    = 1;
let filterMode = 'all';

// ── SORT ──────────────────────────────────────────────────────────────────────
function sortTable(col){{
  if(sortCol===col){{ sortAsc=!sortAsc; }}
  else{{ sortCol=col; sortAsc=col===1; }}  // symbol → asc, others → desc
  applyFilters();
}}

// ── FILTER ────────────────────────────────────────────────────────────────────
function setFilter(mode, btn){{
  filterMode=mode;
  document.querySelectorAll('.btn-filter').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  curPage=1;
  applyFilters();
}}

// ── APPLY FILTERS + RENDER ────────────────────────────────────────────────────
function applyFilters(){{
  const q    = (document.getElementById('searchBox').value||'').toLowerCase();
  const pgSz = parseInt(document.getElementById('pgSize').value);

  let data = RAW_SIGNALS.filter(r=>{{
    const cnt = parseInt(r.COUNT||r.count||0);
    if(filterMode==='4' && cnt<4) return false;
    if(filterMode==='3' && cnt<3) return false;
    if(filterMode==='2' && cnt<2) return false;
    if(filterMode==='1' && cnt<1) return false;
    if(q && !(r.SYMBOL||r.symbol||'').toLowerCase().includes(q)) return false;
    return true;
  }});

  // sort
  data.sort((a,b)=>{{
    let va, vb;
    const cols = ['#','SYMBOL','CLOSE','CHG_PCT','PCT_FROM_LOW','PCT_FROM_ATH','CONFIGS','COUNT'];
    if(sortCol===0){{ va=0;vb=0; }}
    else if(sortCol===1){{ va=(a.SYMBOL||a.symbol||''); vb=(b.SYMBOL||b.symbol||''); return sortAsc?(va<vb?-1:1):(va>vb?-1:1); }}
    else if(sortCol===2){{ va=parseFloat(a.CLOSE||a.close||0); vb=parseFloat(b.CLOSE||b.close||0); }}
    else if(sortCol===3){{ va=parseFloat(a.CHG_PCT||a.chg_pct||0); vb=parseFloat(b.CHG_PCT||b.chg_pct||0); }}
    else if(sortCol===4){{ va=parseFloat(a.PCT_FROM_LOW||a.pct_from_low||0); vb=parseFloat(b.PCT_FROM_LOW||b.pct_from_low||0); }}
    else if(sortCol===5){{ va=parseFloat(a.PCT_FROM_ATH||a.pct_from_ath||0); vb=parseFloat(b.PCT_FROM_ATH||b.pct_from_ath||0); }}
    else if(sortCol===6){{ va=(a.CONFIGS||a.configs||''); vb=(b.CONFIGS||b.configs||''); return sortAsc?(va<vb?-1:1):(va>vb?-1:1); }}
    else{{ va=parseFloat(a.COUNT||a.count||0); vb=parseFloat(b.COUNT||b.count||0); }}
    return sortAsc?(va-vb):(vb-va);
  }});

  filtered = data;
  const total = data.length;
  const pages = Math.max(1, Math.ceil(total/pgSz));
  if(curPage>pages) curPage=pages;

  const start = (curPage-1)*pgSz;
  const page  = data.slice(start, start+pgSz);

  renderTable(page, start);
  document.getElementById('pagerInfo').textContent = `${{start+1}}–${{Math.min(start+pgSz,total)}} of ${{total}} signals | Page ${{curPage}}/${{pages}}`;
}}

function renderTable(rows, offset){{
  const days = CONFIGS.length>0 ? CONFIGS[0].days_back : '?';
  // Update column header
  document.querySelector('#sigTable thead th:nth-child(5)').textContent = `% FROM ${{days}}D LOW`;

  const tb = document.getElementById('sigBody');
  if(!rows.length){{
    tb.innerHTML='<tr><td colspan="8" class="empty">No signals found for selected filter.</td></tr>';
    return;
  }}
  tb.innerHTML = rows.map((r,i)=>{{
    const sym   = r.SYMBOL||r.symbol||'—';
    const close = r.CLOSE||r.close||'—';
    const chg   = parseFloat(r.CHG_PCT||r.chg_pct||0);
    const low   = parseFloat(r.PCT_FROM_LOW||r.pct_from_low||0);
    const ath   = parseFloat(r.PCT_FROM_ATH||r.pct_from_ath||0);
    const cfgs  = r.CONFIGS||r.configs||'—';
    const cnt   = parseInt(r.COUNT||r.count||0);
    const stars = '&#9733;'.repeat(cnt) + '&#9734;'.repeat(Math.max(0,4-cnt));
    const chgCls= chg>=0?'green':'red';
    const lowCls= low>=0?'green':'red';
    const athCls= ath>=0?'green':'red';
    return `<tr>
      <td>${{offset+i+1}}</td>
      <td><strong>${{sym}}</strong></td>
      <td>&#8377;${{Number(close).toLocaleString('en-IN',{{maximumFractionDigits:2}})}}</td>
      <td class="${{chgCls}}">${{chg>=0?'+':''}}${{chg.toFixed(2)}}%</td>
      <td class="${{lowCls}}">${{low>=0?'+':''}}${{low.toFixed(2)}}%</td>
      <td class="${{athCls}}">${{ath>=0?'+':''}}${{ath.toFixed(2)}}%</td>
      <td style="font-size:11px;color:var(--text3);">${{cfgs}}</td>
      <td><span class="star-badge">${{stars}}</span></td>
    </tr>`;
  }}).join('');
}}

function prevPage(){{ if(curPage>1){{ curPage--; applyFilters(); }} }}
function nextPage(){{
  const pgSz = parseInt(document.getElementById('pgSize').value);
  const pages = Math.ceil(filtered.length/pgSz);
  if(curPage<pages){{ curPage++; applyFilters(); }}
}}

// ── EXPORT ────────────────────────────────────────────────────────────────────
function exportExcel(){{
  if(!filtered.length){{ toast('No data to export','info'); return; }}
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.json_to_sheet(filtered);
  XLSX.utils.book_append_sheet(wb, ws, 'BTST Signals');
  XLSX.writeFile(wb, 'NSE_BTST_Signals.xlsx');
  toast('Excel downloaded!','success');
}}
function exportCSV(){{
  if(!filtered.length){{ toast('No data to export','info'); return; }}
  const keys = Object.keys(filtered[0]);
  const csv  = [keys.join(','), ...filtered.map(r=>keys.map(k=>`"${{r[k]||''}}"`).join(','))].join('\\n');
  const a    = document.createElement('a');
  a.href     = 'data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download = 'NSE_BTST_Signals.csv';
  a.click();
  toast('CSV downloaded!','success');
}}

// ── TOAST ─────────────────────────────────────────────────────────────────────
function toast(msg, type='info'){{
  const el = document.createElement('div');
  el.className = `toast ${{type}}`;
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(()=>{{ el.style.animation='fadeOut .4s forwards'; setTimeout(()=>el.remove(),400); }}, 2500);
}}

// ── INIT ──────────────────────────────────────────────────────────────────────
applyFilters();
</script>
</body>
</html>"""
    return html

def main():
    try:
        import pandas as pd
    except ImportError:
        pd = None

    rows, sig_date = load_signals()
    configs        = load_configs()
    nifty          = load_nifty()
    logo           = load_logo()

    # build config breakdown
    breakdown = {{}}
    for c in configs:
        breakdown[c.get('id','')] = 0
    if rows and pd:
        df = pd.DataFrame(rows)
        cnt_col = next((c for c in df.columns if c.upper()=='COUNT'), None)
        if cnt_col:
            for threshold, key in [(4,'C1'),(3,'C2'),(2,'C3'),(1,'C4')]:
                try:
                    breakdown[key] = int((df[cnt_col].astype(int)==threshold).sum())
                except:
                    pass

    meta = {{
        'generated_at'    : datetime.now(tz=IST).strftime('%d-%b-%Y %H:%M IST'),
        'signal_date'     : sig_date,
        'total_signals'   : len(rows),
        'config_breakdown': breakdown,
        'configs'         : configs,
    }}

    import json as _json
    rows_json = _json.dumps(rows)
    html = build_html(rows_json, meta, configs, nifty, logo)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        f.write(html)
    print(f"Dashboard written → {{OUT}}")
    print(f"  Signals : {{len(rows)}}")
    print(f"  Date    : {{sig_date}}")

if __name__ == '__main__':
    main()
