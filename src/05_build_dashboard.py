#!/usr/bin/env python3
"""
NSE BTST Signals — Dashboard Builder v3
Full tabs: Overview, Open, Closed, Force Exit, Stock History, Daily Ledger,
           Trade History, Today's Signals, Configs, Disclaimer
"""
import os, json, csv, glob, re
from datetime import datetime, timezone, timedelta

IST  = timezone(timedelta(hours=5, minutes=30))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG   = os.path.join(BASE, 'config', 'params.json')
BHAV_DIR = os.path.join(BASE, 'bhav_data')
SIM_JSON = os.path.join(BASE, 'docs',   'data', 'sim_results.json')
SIGS_CSV = os.path.join(BASE, 'output', 'signals_latest.csv')
NIFTY    = os.path.join(BASE, 'docs', 'data', 'nifty_index.json')
LOGO_TXT = os.path.join(BASE, 'docs',   'logo_b64.txt')
OUT      = os.path.join(BASE, 'docs',   'index.html')


def load_logo():
    if os.path.exists(LOGO_TXT):
        with open(LOGO_TXT) as f:
            return f.read().strip()
    return ''


def load_nifty():
    try:
        with open(NIFTY) as f:
            raw = json.load(f)

        label_to_key = {
            'NIFTY 50': 'nifty50',
            'BANKNIFTY': 'banknifty',
            'SENSEX': 'sensex',
            'NIFTY IT': 'niftyit',
        }

        result = {}

        for idx in raw.get('indices', []):
            key = label_to_key.get(idx.get('label'))

            if key:
                result[key] = {
                    'price': idx.get('close', 0),
                    'change': idx.get('change', 0),
                    'change_pct': idx.get('change_pct', 0),
                    'date': idx.get('date', ''),
                }

        result['updated_at'] = raw.get('updated_at', '')
        return result

    except Exception:
        return {}


def load_configs():
    try:
        with open(CONFIG) as f:
            return json.load(f).get('configs', [])
    except:
        return []


def load_sim():
    if not os.path.exists(SIM_JSON):
        return {}, {}, ''
    with open(SIM_JSON) as f:
        d = json.load(f)
    meta    = d.get('meta', {})
    results = d.get('results', {})
    return meta, results, meta.get('generated_at', '')


def load_signals_csv():
    rows = []
    if not os.path.exists(SIGS_CSV):
        return rows, ''
    with open(SIGS_CSV, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    dates = [r.get('SIGNAL_DATE', '') for r in rows if r.get('SIGNAL_DATE')]
    sig_date = max(dates) if dates else ''
    return rows, sig_date


def load_bhav_ohlc(all_rows):
    """Build per-trade OHLC lookup from bhav CSVs."""
    try:
        bhav_files = sorted(glob.glob(os.path.join(BHAV_DIR, '*.csv')))
        if not bhav_files:
            return {}
        # Build date -> symbol -> {o,h,l,c} mapping
        date_sym_map = {}
        for fpath in bhav_files:
            fname = os.path.basename(fpath)
            # Extract date from filename: bhav_YYYYMMDD.csv or YYYYMMDD.csv
            dm = re.search(r'(\d{8})', fname)
            if not dm:
                continue
            ds = dm.group(1)  # YYYYMMDD
            date_str = f"{ds[:4]}-{ds[4:6]}-{ds[6:]}"
            try:
                with open(fpath, newline='', encoding='utf-8', errors='replace') as cf:
                    reader = csv.DictReader(cf)
                    hdrs = reader.fieldnames or []
                    # Detect column names
                    sym_col = next((h for h in hdrs if h.strip().upper() in ('SYMBOL','SC_CODE')), None)
                    o_col   = next((h for h in hdrs if h.strip().upper() in ('OPEN','OPEN_PRICE','OP')), None)
                    h_col   = next((h for h in hdrs if h.strip().upper() in ('HIGH','HIGH_PRICE','HP')), None)
                    l_col   = next((h for h in hdrs if h.strip().upper() in ('LOW','LOW_PRICE','LP')), None)
                    c_col   = next((h for h in hdrs if h.strip().upper() in ('CLOSE','CLOSE_PRICE','CP')), None)
                    if not all([sym_col, o_col, h_col, l_col, c_col]):
                        continue
                    sym_map = {}
                    for row in reader:
                        sym = row.get(sym_col,'').strip()
                        if not sym:
                            continue
                        try:
                            sym_map[sym] = {
                                'o': round(float(row.get(o_col,0) or 0), 2),
                                'h': round(float(row.get(h_col,0) or 0), 2),
                                'l': round(float(row.get(l_col,0) or 0), 2),
                                'c': round(float(row.get(c_col,0) or 0), 2),
                            }
                        except:
                            pass
                    date_sym_map[date_str] = sym_map
            except:
                pass

        # Build per-trade OHLC
        trade_ohlc = {}
        for r in all_rows:
            if r.get('ORDER') != 'Executed':
                continue
            sym = r.get('SYMBOL','')
            sig = r.get('SIGNAL_DATE','')
            ext = r.get('EXIT_DATE','') or ''
            cfg = r.get('CONFIG','')
            key = f"{sym}_{sig}_{cfg}"
            if key in trade_ohlc:
                continue
            end_d = ext if ext else datetime.now(tz=IST).strftime('%Y-%m-%d')
            ohlc_list = []
            prev_c = 0
            for d in sorted(date_sym_map.keys()):
                if d < sig or d > end_d:
                    continue
                if sym in date_sym_map[d]:
                    rec = dict(date_sym_map[d][sym])
                    if prev_c and prev_c > 0:
                        rec['chg'] = round((rec['c'] - prev_c) / prev_c * 100, 2)
                    else:
                        rec['chg'] = 0
                    rec['date'] = d
                    prev_c = rec['c']
                    ohlc_list.append(rec)
            trade_ohlc[key] = ohlc_list
        return trade_ohlc
    except Exception as e:
        return {}


def build_html(logo, nifty, configs, sim_meta, sim_results, signals_rows, sig_date):
    generated = sim_meta.get('generated_at', datetime.now(tz=IST).strftime('%d-%b-%Y %H:%M IST'))
    last_date = sim_meta.get('last_date', '')
    today_date = datetime.now(tz=IST).strftime('%Y-%m-%d')

    # Flatten all results across configs for JS
    all_rows = []
    for cid, rows in sim_results.items():
        for r in rows:
            r2 = dict(r)
            r2['CONFIG'] = cid
            all_rows.append(r2)

    rows_js    = json.dumps(all_rows, default=str)
    signals_js = json.dumps(signals_rows, default=str)
    nifty_js   = json.dumps(nifty, default=str)
    configs_js = json.dumps(configs, default=str)
    trade_ohlc = load_bhav_ohlc(all_rows)
    trade_ohlc_js = json.dumps(trade_ohlc, default=str)

    # Config table rows
    cfg_html = ''
    for c in configs:
        cfg_html += f"""<tr>
          <td><span class="cfg-badge">{c.get('id','')}</span></td>
          <td>{c.get('days_back','')}</td><td>{c.get('pct_min','')}</td>
          <td>{c.get('pct_max','')}</td><td>{c.get('ath_min','')}</td>
          <td>{c.get('ath_max','')}</td><td>{c.get('max_buys','')}</td>
          <td>{c.get('buy_drop','')}</td><td>{c.get('target','')}</td>
          <td>{c.get('stoploss','')}</td><td>{c.get('max_duration','')}</td>
        </tr>"""

    logo_tag = f'<img class="hdr-logo" src="{logo}" alt="PS Market">' if logo else '<span class="hdr-logo-txt">PS MARKET</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PS Market — NSE BTST Signals</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<style>
:root{{--navy:#0d1f3c;--navy2:#162847;--blue:#1d4ed8;--blue2:#2563eb;--cyan:#0891b2;--cyan2:#06b6d4;
  --green:#059669;--red:#dc2626;--amber:#d97706;--surface:#fff;--surface2:#f1f5f9;--surface3:#e2e8f0;
  --text:#0f172a;--text2:#334155;--text3:#64748b;--border:#cbd5e1;
  --shadow:0 2px 12px rgba(13,31,60,.10);--shadow-lg:0 8px 32px rgba(13,31,60,.18);
  --radius:10px;--radius-lg:16px;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{height:100%;}}
body{{font-family:'Segoe UI',system-ui,Arial,sans-serif;background:#eef2f7;color:var(--text);font-size:14px;min-height:100vh;display:flex;flex-direction:column;}}
header{{background:linear-gradient(135deg,#0a1628 0%,#0d1f3c 50%,#162847 100%);padding:0;border-bottom:3px solid var(--cyan2);box-shadow:0 4px 24px rgba(0,0,0,.3);position:sticky;top:0;z-index:100;}}
.hdr{{max-width:1800px;margin:auto;display:flex;align-items:center;justify-content:space-between;padding:10px 24px;gap:16px;}}
.hdr-left{{display:flex;align-items:center;gap:14px;}}
.hdr-logo{{height:42px;width:auto;background:#fff;border-radius:8px;padding:3px 8px;box-shadow:0 1px 4px rgba(0,0,0,0.15);}}
.hdr-logo-txt{{font-size:18px;font-weight:900;color:#fff;letter-spacing:1px;}}
.hdr-sep{{width:1.5px;height:38px;background:rgba(255,255,255,.18);border-radius:2px;}}
.hdr-title .t1{{font-size:19px;font-weight:800;color:#fff;letter-spacing:.2px;line-height:1.2;}}
.hdr-title .t2{{font-size:10.5px;color:rgba(255,255,255,.55);font-weight:500;letter-spacing:.7px;margin-top:3px;}}
.hdr-right{{display:flex;align-items:center;gap:10px;}}
.hdr-badge{{padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);color:rgba(255,255,255,.85);white-space:nowrap;}}
.hdr-btn{{display:flex;align-items:center;gap:6px;padding:9px 18px;border-radius:8px;background:linear-gradient(135deg,var(--blue2),var(--cyan2));border:none;color:#fff;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(37,99,235,.4);transition:all .2s;}}
.hdr-btn:hover{{transform:translateY(-1px);box-shadow:0 4px 16px rgba(37,99,235,.6);}}
.idx-bar{{background:linear-gradient(135deg,#0a1628,#0d1f3c);border-bottom:1px solid rgba(255,255,255,.08);padding:7px 24px;}}
.idx-inner{{max-width:1800px;margin:auto;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}}
.idx-label{{font-size:10px;font-weight:800;color:rgba(255,255,255,.4);letter-spacing:1px;text-transform:uppercase;margin-right:4px;}}
.idx-card{{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.13);border-radius:9px;padding:6px 14px;}}
.idx-name{{font-size:11px;font-weight:800;color:rgba(255,255,255,.6);letter-spacing:.5px;text-transform:uppercase;}}
.idx-price{{font-size:17px;font-weight:900;color:#fff;line-height:1;}}
.idx-chg{{font-size:11px;font-weight:700;white-space:nowrap;padding:2px 7px;border-radius:12px;}}
.idx-chg.pos{{background:rgba(5,150,105,.25);color:#10b981;}}.idx-chg.neg{{background:rgba(220,38,38,.25);color:#ef4444;}}.idx-chg.flat{{background:rgba(100,116,139,.2);color:#94a3b8;}}
.idx-date{{font-size:10px;color:rgba(255,255,255,.35);font-weight:500;}}
.idx-loading{{font-size:11px;color:rgba(255,255,255,.4);font-style:italic;}}
#liveBanner{{display:flex;align-items:center;justify-content:center;padding:8px 20px;background:rgba(5,150,105,.08);border-bottom:2px solid var(--green);font-size:13px;font-weight:600;color:var(--green);gap:8px;}}
.container{{flex:1;max-width:1800px;margin:auto;padding:18px 24px;}}
.card{{background:var(--surface);border-radius:var(--radius-lg);padding:20px;margin-bottom:16px;border:1.5px solid var(--border);box-shadow:var(--shadow);}}
.cstrip{{background:var(--surface);border-radius:var(--radius-lg);padding:12px 16px;margin-bottom:12px;border:1.5px solid var(--border);box-shadow:var(--shadow);display:flex;flex-wrap:wrap;gap:10px;align-items:center;}}
.slbl{{font-size:11px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;}}
.tabs{{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 16px;background:var(--surface);border-radius:var(--radius-lg);padding:10px 12px;border:1.5px solid var(--border);box-shadow:var(--shadow);}}
.tab{{padding:7px 14px;border-radius:7px;border:1.5px solid var(--border);cursor:pointer;color:var(--text2);font-weight:600;font-size:12.5px;transition:all .18s;background:var(--surface2);white-space:nowrap;}}
.tab:hover{{border-color:var(--blue2);color:var(--blue2);background:#eff6ff;transform:translateY(-1px);}}
.tab.active{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff;border-color:var(--blue2);box-shadow:0 3px 10px rgba(37,99,235,.3);}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:11px;margin-bottom:18px;}}
.stat-card{{background:linear-gradient(135deg,#f8faff,#eef2ff);border:1.5px solid #c7d7fe;border-radius:var(--radius);padding:14px 16px;text-align:center;transition:transform .18s;}}
.stat-card:hover{{transform:translateY(-2px);}}
.stat-val{{font-size:24px;font-weight:900;color:var(--blue2);line-height:1.1;}}
.stat-lbl{{font-size:10.5px;color:var(--text3);font-weight:600;margin-top:4px;text-transform:uppercase;letter-spacing:.4px;}}
.stat-card.gc{{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#86efac;}}.stat-card.gc .stat-val{{color:var(--green);}}
.stat-card.rc{{background:linear-gradient(135deg,#fff1f2,#ffe4e6);border-color:#fca5a5;}}.stat-card.rc .stat-val{{color:var(--red);}}
.stat-card.ac{{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fcd34d;}}.stat-card.ac .stat-val{{color:var(--amber);}}
.table-area{{overflow-x:auto;border-radius:var(--radius);}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;}}
thead th{{background:linear-gradient(135deg,#0d1f3c,#1e3a6e);color:#fff;padding:10px 9px;text-align:center;font-weight:700;font-size:11.5px;letter-spacing:.3px;position:sticky;top:0;z-index:2;white-space:nowrap;cursor:pointer;user-select:none;}}
thead th:first-child{{border-radius:8px 0 0 0;}}thead th:last-child{{border-radius:0 8px 0 0;}}
thead th:hover{{background:linear-gradient(135deg,#162847,#254a8a);}}
tbody tr{{transition:background .12s;}}
tbody tr:nth-child(even){{background:#f8fafc;}}tbody tr:nth-child(odd){{background:#fff;}}
tbody tr:hover{{background:#eff6ff;}}
tbody td{{padding:8px 9px;text-align:center;border-bottom:1px solid #e9edf4;font-size:12px;}}
.cfg-badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:800;background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff;}}
.cfg-badge.c1{{background:linear-gradient(135deg,#1d4ed8,#2563eb);}}.cfg-badge.c2{{background:linear-gradient(135deg,#0891b2,#06b6d4);}}.cfg-badge.c3{{background:linear-gradient(135deg,#059669,#10b981);}}.cfg-badge.c4{{background:linear-gradient(135deg,#7c3aed,#8b5cf6);}}
.result-badge{{display:inline-block;padding:3px 9px;border-radius:12px;font-size:11px;font-weight:700;white-space:nowrap;}}
.rb-profit{{background:#dcfce7;color:#059669;}}.rb-loss{{background:#ffe4e6;color:#dc2626;}}.rb-open{{background:#dbeafe;color:#1d4ed8;}}.rb-pending{{background:#fef3c7;color:#d97706;}}.rb-invalid{{background:#f1f5f9;color:#64748b;}}.rb-expired{{background:#f1f5f9;color:#64748b;}}
.green{{color:#059669;font-weight:700;}}.red{{color:#dc2626;font-weight:700;}}
.hidden{{display:none!important;}}
.empty{{padding:40px;text-align:center;color:var(--text3);font-size:15px;}}
.pager{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:10px;font-size:13px;padding:0 4px;}}
.pager .info{{color:var(--text3);font-weight:600;}}
button{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));border:none;padding:8px 16px;border-radius:8px;font-weight:700;color:#fff;cursor:pointer;font-size:13px;transition:all .2s;box-shadow:0 2px 6px rgba(37,99,235,.3);}}
button:hover{{transform:translateY(-1px);box-shadow:0 4px 14px rgba(37,99,235,.5);}}
.btn-sm{{padding:5px 11px;font-size:12px;}}
.btn-outline{{background:transparent;border:1.5px solid var(--blue2);color:var(--blue2);box-shadow:none;}}
.btn-outline:hover{{background:var(--blue2);color:#fff;}}
.btn-green{{background:linear-gradient(135deg,#059669,#10b981);}}.btn-teal{{background:linear-gradient(135deg,#0891b2,#06b6d4);}}
.btn-filter{{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;border:1.5px solid var(--border);background:var(--surface2);color:var(--text2);cursor:pointer;transition:all .18s;}}
.btn-filter.active,.btn-filter:hover{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff;border-color:var(--blue2);}}
select,input[type=text]{{padding:7px 11px;border-radius:8px;background:var(--surface);color:var(--text);border:1.5px solid var(--border);font-weight:600;font-size:13px;transition:all .2s;}}
select:focus,input:focus{{border-color:var(--blue2);outline:none;box-shadow:0 0 0 3px rgba(37,99,235,.1);}}
.ov-table thead th{{font-size:11px;}}
.disclaimer-box{{background:linear-gradient(135deg,#fff7ed,#fff);border:1.5px solid #fed7aa;border-radius:var(--radius-lg);padding:24px 28px;}}
.disclaimer-box h2{{color:#c2410c;margin-bottom:16px;font-size:16px;}}
.disclaimer-box p{{color:var(--text2);line-height:1.7;margin-bottom:10px;font-size:13.5px;}}
#toast-container{{position:fixed;bottom:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:6px;max-width:300px;pointer-events:none;}}
.toast{{padding:8px 12px;border-radius:8px;font-weight:600;font-size:12px;color:#fff;box-shadow:0 4px 12px rgba(0,0,0,.18);animation:slideIn .25s ease;pointer-events:auto;}}
.toast.success{{background:linear-gradient(135deg,#059669,#10b981);}}.toast.info{{background:linear-gradient(135deg,var(--blue2),var(--cyan2));}}
@keyframes slideIn{{from{{transform:translateX(110%);opacity:0}}to{{transform:none;opacity:1}}}}
footer{{background:var(--navy);color:rgba(255,255,255,.5);text-align:center;padding:14px;font-size:12px;border-top:2px solid rgba(255,255,255,.08);}}
.tab-badges{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;}}
.tbadge{{display:inline-flex;align-items:center;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700;border:1.5px solid;white-space:nowrap;cursor:default;}}
.tbadge.blue{{background:#dbeafe;color:#1d4ed8;border-color:#93c5fd;}}
.tbadge.green{{background:#dcfce7;color:#059669;border-color:#86efac;}}
.tbadge.red{{background:#ffe4e6;color:#dc2626;border-color:#fca5a5;}}
.tbadge.amber{{background:#fef3c7;color:#d97706;border-color:#fcd34d;}}
.tbadge.navy{{background:#e0e7ff;color:#3730a3;border-color:#a5b4fc;}}
.badge-fresh{{display:inline-block;padding:3px 11px;border-radius:12px;font-size:11px;font-weight:700;background:#dbeafe;color:#1d4ed8;border:1px solid #93c5fd;}}
.badge-opencall{{display:inline-block;padding:3px 11px;border-radius:12px;font-size:11px;font-weight:700;background:#fff7ed;color:#d97706;border:1px solid #fed7aa;}}
.perf-hero{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;}}
.phc{{background:linear-gradient(135deg,#f8faff,#eef2ff);border:1.5px solid #c7d7fe;border-radius:10px;padding:16px;text-align:center;}}
.phc.pos{{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#86efac;}}.phc.neg{{background:linear-gradient(135deg,#fff1f2,#ffe4e6);border-color:#fca5a5;}}
.phc-label{{font-size:11px;color:var(--text3);font-weight:600;text-transform:uppercase;letter-spacing:.4px;}}
.phc-value{{font-size:20px;font-weight:900;color:var(--navy);margin:6px 0 4px;}}
.phc.pos .phc-value{{color:var(--green);}}.phc.neg .phc-value{{color:var(--red);}}
.phc-sub{{font-size:11px;color:var(--text3);}}

/* ── STOCK DETAIL MODAL ── */
#stockDetailModal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;align-items:center;justify-content:center;}}
#stockDetailModal.open{{display:flex;}}
.sdm-box{{background:var(--surface);border-radius:12px;width:90%;max-width:960px;max-height:85vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.4);}}
.sdm-hdr{{background:var(--navy);color:#fff;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;}}
.sdm-hdr h3{{margin:0;font-size:16px;}}
.sdm-close{{background:transparent;border:none;color:#fff;font-size:20px;cursor:pointer;padding:4px 8px;border-radius:4px;}}
.sdm-close:hover{{background:rgba(255,255,255,.15);}}
.sdm-body{{padding:16px;overflow-y:auto;flex:1;}}
</style>
</head>
<body>

<header>
  <div class="hdr">
    <div class="hdr-left">
      {logo_tag}
      <div class="hdr-sep"></div>
      <div class="hdr-title">
        <div class="t1">NSE BTST Signals</div>
        <div class="t2">DAILY SIGNAL SCANNER &middot; 4 FIXED CONFIGS &middot; SIMULATION TRACKER</div>
      </div>
    </div>
    <div class="hdr-right">
      <span class="hdr-badge">&#9679; {generated}</span>
      <button class="hdr-btn" onclick="location.reload()">&#8635; Refresh</button>
    </div>
  </div>
</header>

<div class="idx-bar">
  <div class="idx-inner">
    <span class="idx-label">&#9776; INDICES</span>
    <div id="idx-nifty50"   class="idx-card"><span class="idx-loading">NIFTY 50&hellip;</span></div>
    <div id="idx-banknifty" class="idx-card"><span class="idx-loading">BANKNIFTY&hellip;</span></div>
    <div id="idx-sensex"    class="idx-card"><span class="idx-loading">SENSEX&hellip;</span></div>
    <div id="idx-niftyit"   class="idx-card"><span class="idx-loading">NIFTY IT&hellip;</span></div>
  </div>
</div>

<div id="liveBanner">
  &#10003; Last simulation: <strong id="bannerDate">{generated}</strong> &nbsp;|&nbsp; Data date: <strong>{last_date}</strong>
</div>

<div class="container">

<div class="cstrip">
  <span class="slbl">Range:</span>
  <input type="date" id="fromDate" value="" placeholder="From Date" style="padding:6px 10px;font-size:12px;min-width:130px;">
  <span style="color:var(--text3);font-weight:600;">to</span>
  <input type="date" id="toDate" value="{today_date}" style="padding:6px 10px;font-size:12px;min-width:130px;">
  <button onclick="applyDateRange()" style="padding:6px 14px;font-size:12px;">Apply</button>
  <button onclick="resetDateRange()" style="padding:6px 14px;font-size:12px;background:#64748b;">Reset</button>
  <span id="filterPill" class="pill" style="display:none;"></span>
  <span id="globalLastSignal" style="margin-left:auto;font-size:12px;font-weight:700;color:var(--blue2);"></span>
</div>

<div class="tabs">
  <div class="tab active"  onclick="showTab('overview',this)">&#9675; Overview</div>
  <div class="tab" onclick="showTab('open',this)">&#9711; Open Positions</div>
  <div class="tab" onclick="showTab('closed',this)">&#10003; Closed Positions</div>
  <div class="tab" onclick="showTab('fe',this)">&#9888; Force Exit</div>
  <div class="tab" onclick="showTab('history',this)">&#9776; Stock History</div>
  <div class="tab" onclick="showTab('ledger',this)">&#9781; Daily Ledger</div>
  <div class="tab" onclick="showTab('trades',this)">&#8635; Trade History</div>
  <div class="tab" onclick="showTab('signals',this)">&#9654; Today's Signals</div>
  <div class="tab" onclick="showTab('configs',this)">&#9881; Configs</div>
  <div class="tab" onclick="showTab('avgtrigger',this)">&#8681; Avg Trigger</div>
  <div class="tab" onclick="showTab('selltrigger',this)">&#8682; Sell Trigger</div>
  <div class="tab" onclick="showTab('avghistory',this)">&#9400; Avg History</div>
  <div class="tab" onclick="showTab('marketdata',this)">&#128200; Market Data</div>
  <div class="tab" onclick="showTab('performance',this)">&#128202; Performance</div>
  <div class="tab" onclick="showTab('disclaimer',this)">&#9432; Disclaimer</div>
</div>

<div id="tab-overview">
  <div id="ov-stats" class="stat-grid"></div>
  <div class="card" style="padding:0 0 8px">
    <div class="table-area">
      <table class="ov-table">
        <thead><tr>
          <th>CONFIG</th><th>TOTAL SIGNALS</th><th>EXECUTED</th>
          <th>OPEN</th><th>CLOSED</th><th>PROFIT-TGT</th><th>LOSS-SL</th>
          <th>FE-PROFIT</th><th>FE-LOSS</th><th>PENDING</th><th>EXPIRED</th><th>INVALID</th>
          <th>WIN RATE %</th><th>TOTAL P&amp;L &#8377;</th>
        </tr></thead>
        <tbody id="ov-body"></tbody>
      </table>
    </div>
  </div>
</div>

<div id="tab-open" class="hidden">
  <div class="tab-badges" id="open-badges"></div>
  <div class="cstrip">
    <span class="slbl">Config:</span>
    <button class="btn-filter active" onclick="cfgFilter('open','ALL',this)">All</button>
    <button class="btn-filter" onclick="cfgFilter('open','C1',this)">C1</button>
    <button class="btn-filter" onclick="cfgFilter('open','C2',this)">C2</button>
    <button class="btn-filter" onclick="cfgFilter('open','C3',this)">C3</button>
    <button class="btn-filter" onclick="cfgFilter('open','C4',this)">C4</button>
    <div style="flex:1"></div>
    <button class="btn-green btn-sm" onclick="exportTab('open')">&#8595; Excel</button>
    <button class="btn-teal btn-sm" onclick="exportCSVTab('open')">&#8595; CSV</button>
  </div>
  <div class="card" style="padding:0 0 8px">
    <div class="table-area">
      <table><thead><tr>
        <th onclick="srt('open',0)">#</th>
        <th onclick="srt('open',1)">CFG</th>
        <th onclick="srt('open',2)">SYMBOL</th>
        <th onclick="srt('open',3)">BUY DATE</th>
        <th onclick="srt('open',4)">AVG BUY &#8377;</th>
        <th onclick="srt('open',5)">CURRENT LTP &#8377;</th>
        <th onclick="srt('open',6)">TARGET &#8377;</th>
        <th onclick="srt('open',7)">STOP &#8377;</th>
        <th onclick="srt('open',8)">BUYS</th>
        <th onclick="srt('open',9)">QTY</th>
        <th onclick="srt('open',10)">INVESTED &#8377;</th>
        <th onclick="srt('open',11)">MARKET DAYS</th>
        <th onclick="srt('open',12)">UNREAL P&amp;L &#8377;</th>
        <th onclick="srt('open',13)">GAIN %</th>
      </tr></thead>
      <tbody id="open-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="open-info"></span><div style="flex:1"></div>
      <button class="btn-sm btn-outline" onclick="pg('open',-1)">&#8249; Prev</button>
      <button class="btn-sm btn-outline" onclick="pg('open',1)">Next &#8250;</button>
      <select id="open-pgsize" onchange="renderTab('open')"><option value="25">25</option><option value="50" selected>50</option><option value="100">100</option><option value="9999">All</option></select>
    </div>
  </div>
</div>

<div id="tab-closed" class="hidden">
  <div class="tab-badges" id="closed-badges"></div>
  <div class="cstrip">
    <span class="slbl">Config:</span>
    <button class="btn-filter active" onclick="cfgFilter('closed','ALL',this)">All</button>
    <button class="btn-filter" onclick="cfgFilter('closed','C1',this)">C1</button>
    <button class="btn-filter" onclick="cfgFilter('closed','C2',this)">C2</button>
    <button class="btn-filter" onclick="cfgFilter('closed','C3',this)">C3</button>
    <button class="btn-filter" onclick="cfgFilter('closed','C4',this)">C4</button>
    <span class="slbl" style="margin-left:8px">Result:</span>
    <button class="btn-filter active" id="closed-res-ALL" onclick="resFilter('closed','ALL',this)">All</button>
    <button class="btn-filter" id="closed-res-P" onclick="resFilter('closed','P',this)">Profit</button>
    <button class="btn-filter" id="closed-res-L" onclick="resFilter('closed','L',this)">Loss</button>
    <button class="btn-filter" id="closed-res-FE" onclick="resFilter('closed','FE',this)">FE Only</button>
    <div style="flex:1"></div>
    <button class="btn-green btn-sm" onclick="exportTab('closed')">&#8595; Excel</button>
    <button class="btn-teal btn-sm" onclick="exportCSVTab('closed')">&#8595; CSV</button>
  </div>
  <div class="card" style="padding:0 0 8px">
    <div class="table-area">
      <table><thead><tr>
        <th onclick="srt('closed',0)">#</th>
        <th onclick="srt('closed',1)">CFG</th>
        <th onclick="srt('closed',2)">SYMBOL</th>
        <th onclick="srt('closed',3)">BUY DATE</th>
        <th onclick="srt('closed',4)">EXIT DATE</th>
        <th onclick="srt('closed',5)">AVG BUY &#8377;</th>
        <th onclick="srt('closed',6)">EXIT PRICE &#8377;</th>
        <th onclick="srt('closed',7)">QTY</th>
        <th onclick="srt('closed',8)">INVESTED &#8377;</th>
        <th onclick="srt('closed',9)">P&amp;L &#8377;</th>
        <th onclick="srt('closed',10)">GAIN %</th>
        <th onclick="srt('closed',11)">MARKET DAYS</th>
        <th onclick="srt('closed',12)">RESULT</th>
      </tr></thead>
      <tbody id="closed-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="closed-info"></span><div style="flex:1"></div>
      <button class="btn-sm btn-outline" onclick="pg('closed',-1)">&#8249; Prev</button>
      <button class="btn-sm btn-outline" onclick="pg('closed',1)">Next &#8250;</button>
      <select id="closed-pgsize" onchange="renderTab('closed')"><option value="25">25</option><option value="50" selected>50</option><option value="100">100</option><option value="9999">All</option></select>
    </div>
  </div>
</div>

<div id="tab-fe" class="hidden">
  <div class="tab-badges" id="fe-badges"></div>
  <div class="cstrip">
    <span class="slbl">Config:</span>
    <button class="btn-filter active" onclick="cfgFilter('fe','ALL',this)">All</button>
    <button class="btn-filter" onclick="cfgFilter('fe','C1',this)">C1</button>
    <button class="btn-filter" onclick="cfgFilter('fe','C2',this)">C2</button>
    <button class="btn-filter" onclick="cfgFilter('fe','C3',this)">C3</button>
    <button class="btn-filter" onclick="cfgFilter('fe','C4',this)">C4</button>
    <div style="flex:1"></div>
    <button class="btn-green btn-sm" onclick="exportTab('fe')">&#8595; Excel</button>
    <button class="btn-teal btn-sm" onclick="exportCSVTab('fe')">&#8595; CSV</button>
  </div>
  <div class="card" style="padding:0 0 8px">
    <div class="table-area">
      <table><thead><tr>
        <th onclick="srt('fe',0)">#</th>
        <th onclick="srt('fe',1)">CFG</th>
        <th onclick="srt('fe',2)">SYMBOL</th>
        <th onclick="srt('fe',3)">BUY DATE</th>
        <th onclick="srt('fe',4)">AVG BUY &#8377;</th>
        <th onclick="srt('fe',5)">LTP &#8377;</th>
        <th onclick="srt('fe',6)">TARGET &#8377;</th>
        <th onclick="srt('fe',7)">STOP &#8377;</th>
        <th onclick="srt('fe',8)">DAYS HELD</th>
        <th onclick="srt('fe',9)">DAYS LEFT</th>
        <th onclick="srt('fe',10)">P&amp;L &#8377;</th>
        <th onclick="srt('fe',11)">GAIN %</th>
        <th onclick="srt('fe',12)">BUYS</th>
      </tr></thead>
      <tbody id="fe-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="fe-info"></span><div style="flex:1"></div>
      <button class="btn-sm btn-outline" onclick="pg('fe',-1)">&#8249; Prev</button>
      <button class="btn-sm btn-outline" onclick="pg('fe',1)">Next &#8250;</button>
      <select id="fe-pgsize" onchange="renderTab('fe')"><option value="25">25</option><option value="50" selected>50</option><option value="100">100</option><option value="9999">All</option></select>
    </div>
  </div>
</div>

<div id="tab-history" class="hidden">
  <div class="cstrip">
    <span class="slbl">Search symbol:</span>
    <input type="text" id="hist-search" placeholder="e.g. RELIANCE" oninput="buildHistory()" style="width:200px">
    <span class="slbl" style="margin-left:8px">Config:</span>
    <button class="btn-filter active" onclick="cfgFilter('hist','ALL',this)">All</button>
    <button class="btn-filter" onclick="cfgFilter('hist','C1',this)">C1</button>
    <button class="btn-filter" onclick="cfgFilter('hist','C2',this)">C2</button>
    <button class="btn-filter" onclick="cfgFilter('hist','C3',this)">C3</button>
    <button class="btn-filter" onclick="cfgFilter('hist','C4',this)">C4</button>
  </div>
  <div id="hist-stats" style="display:flex;gap:12px;flex-wrap:wrap;margin:0 0 12px 0"></div>
  <div id="hist-container"></div>
</div>

<div id="tab-ledger" class="hidden">
  <div class="cstrip">
    <span class="slbl">Config:</span>
    <button class="btn-filter active" onclick="cfgFilter('ledger','ALL',this)">All</button>
    <button class="btn-filter" onclick="cfgFilter('ledger','C1',this)">C1</button>
    <button class="btn-filter" onclick="cfgFilter('ledger','C2',this)">C2</button>
    <button class="btn-filter" onclick="cfgFilter('ledger','C3',this)">C3</button>
    <button class="btn-filter" onclick="cfgFilter('ledger','C4',this)">C4</button>
    <div style="flex:1"></div>
    <button class="btn-green btn-sm" onclick="exportTab('ledger')">&#8595; Excel</button>
  </div>
  <div class="card" style="padding:0 0 8px">
    <div class="table-area">
      <table><thead><tr>
        <th onclick="srt('ledger',0)">#</th>
        <th onclick="srt('ledger',1)">EXIT DATE</th>
        <th onclick="srt('ledger',2)">TOTAL TRADES</th>
        <th onclick="srt('ledger',3)">PROFIT TRADES</th>
        <th onclick="srt('ledger',4)">LOSS TRADES</th>
        <th onclick="srt('ledger',5)">DAILY P&amp;L &#8377;</th>
        <th onclick="srt('ledger',6)">CUMULATIVE P&amp;L &#8377;</th>
      </tr></thead>
      <tbody id="ledger-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="ledger-info"></span></div>
  </div>
</div>

<div id="tab-trades" class="hidden">
  <div class="tab-badges" id="trades-badges" style="margin-bottom:10px;"></div>
  <div class="cstrip">
    <span class="slbl">Search:</span>
    <input type="text" id="trades-search" placeholder="Search symbol..." oninput="renderTab('trades')" style="width:200px">
    <span class="slbl" style="margin-left:8px">Config:</span>
    <button class="btn-filter active" onclick="cfgFilter('trades','ALL',this)">All</button>
    <button class="btn-filter" onclick="cfgFilter('trades','C1',this)">C1</button>
    <button class="btn-filter" onclick="cfgFilter('trades','C2',this)">C2</button>
    <button class="btn-filter" onclick="cfgFilter('trades','C3',this)">C3</button>
    <button class="btn-filter" onclick="cfgFilter('trades','C4',this)">C4</button>
    <span class="slbl" style="margin-left:8px">Status:</span>
    <button class="btn-filter active" id="trades-status-ALL" onclick="statusFilter('ALL',this)">All</button>
    <button class="btn-filter" id="trades-status-Open" onclick="statusFilter('Open',this)">Open</button>
    <button class="btn-filter" id="trades-status-Closed" onclick="statusFilter('Closed',this)">Closed</button>
    <div style="flex:1"></div>
    <button class="btn-green btn-sm" onclick="exportTab('trades')">&#8595; Excel</button>
    <button class="btn-teal btn-sm" onclick="exportCSVTab('trades')">&#8595; CSV</button>
  </div>
  <div class="card" style="padding:0 0 8px">
    <div class="table-area">
      <table><thead><tr>
        <th onclick="srt('trades',0)">#</th>
        <th onclick="srt('trades',1)">CFG</th>
        <th onclick="srt('trades',2)">SYMBOL</th>
        <th onclick="srt('trades',3)">BUY DATE</th>
        <th onclick="srt('trades',4)">EXIT DATE</th>
        <th onclick="srt('trades',5)">STATUS</th>
        <th onclick="srt('trades',7)">AVG BUY &#8377;</th>
        <th onclick="srt('trades',8)">EXIT &#8377;</th>
        <th onclick="srt('trades',9)">QTY</th>
        <th onclick="srt('trades',10)">BUYS</th>
        <th onclick="srt('trades',11)">P&amp;L &#8377;</th>
        <th onclick="srt('trades',12)">GAIN %</th>
        <th onclick="srt('trades',13)">DAYS</th>
        <th onclick="srt('trades',14)">RESULT</th>
      </tr></thead>
      <tbody id="trades-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="trades-info"></span><div style="flex:1"></div>
      <button class="btn-sm btn-outline" onclick="pg('trades',-1)">&#8249; Prev</button>
      <button class="btn-sm btn-outline" onclick="pg('trades',1)">Next &#8250;</button>
      <select id="trades-pgsize" onchange="renderTab('trades')"><option value="25">25</option><option value="50" selected>50</option><option value="100">100</option><option value="9999">All</option></select>
    </div>
  </div>
</div>

<div id="tab-signals" class="hidden">
  <div class="tab-badges" id="sig-total-badges" style="margin-bottom:12px;"></div>
  <div class="cstrip">
    <span class="slbl">Config:</span>
    <button class="btn-filter active" onclick="sigCfgFilter('ALL',this)">All</button>
    <button class="btn-filter" onclick="sigCfgFilter('C1',this)">C1</button>
    <button class="btn-filter" onclick="sigCfgFilter('C2',this)">C2</button>
    <button class="btn-filter" onclick="sigCfgFilter('C3',this)">C3</button>
    <button class="btn-filter" onclick="sigCfgFilter('C4',this)">C4</button>
    <span class="slbl" style="margin-left:8px">Status:</span>
    <select id="sig-status-filter" onchange="renderTab('signals')" style="min-width:130px;padding:5px 8px;font-size:13px;">
      <option value="ALL">All</option>
      <option value="Fresh Call">Fresh Call</option>
      <option value="Open Call">Open Call</option>
    </select>
    <div style="flex:1"></div>
    <button class="btn-green btn-sm" onclick="exportTab('signals')">&#8595; Excel</button>
    <button class="btn-teal btn-sm" onclick="exportCSVTab('signals')">&#8595; CSV</button>
  </div>
  <div class="card" style="padding:0 0 8px">
    <div class="table-area">
      <table><thead><tr>
        <th onclick="srt('signals',0)">#</th>
        <th onclick="srt('signals',1)">DATE</th>
        <th onclick="srt('signals',2)">CFG</th>
        <th onclick="srt('signals',10)">STOCK</th>
        <th onclick="srt('signals',3)">1D %</th>
        <th onclick="srt('signals',4)">5D %</th>
        <th onclick="srt('signals',5)">BUY PRICE &#8377;</th>
        <th onclick="srt('signals',6)">LTP &#8377;</th>
        <th onclick="srt('signals',7)">TARGET &#8377;</th>
        <th onclick="srt('signals',8)">SL &#8377;</th>
        <th onclick="srt('signals',9)">STATUS</th>
      </tr></thead>
      <tbody id="signals-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="signals-info"></span><div style="flex:1"></div>
      <button class="btn-sm btn-outline" onclick="pg('signals',-1)">&#8249; Prev</button>
      <button class="btn-sm btn-outline" onclick="pg('signals',1)">Next &#8250;</button>
      <select id="signals-pgsize" onchange="renderTab('signals')"><option value="25">25</option><option value="50" selected>50</option><option value="100">100</option><option value="9999">All</option></select>
    </div>
  </div>
</div>

<div id="tab-configs" class="hidden">
  <div class="card">
    <h3 style="color:var(--navy);margin-bottom:16px">&#9881; Parameter Configurations</h3>
    <div class="table-area">
      <table class="ov-table"><thead><tr>
        <th>CONFIG</th><th>DAYS BACK</th><th>PCT MIN</th><th>PCT MAX</th>
        <th>ATH MIN</th><th>ATH MAX</th><th>MAX BUYS</th><th>BUY DROP</th>
        <th>TARGET</th><th>STOP LOSS</th><th>MAX DURATION</th>
      </tr></thead>
      <tbody>{cfg_html}</tbody></table>
    </div>
    <div style="margin-top:20px;padding:16px;background:#f8faff;border-radius:10px;border:1.5px solid #c7d7fe;font-size:13px;color:var(--text2);line-height:1.8">
      <strong>DAYS BACK:</strong> Look-back window for N-day low &nbsp;&bull;&nbsp;
      <strong>PCT MIN/MAX:</strong> % change from N-day low range &nbsp;&bull;&nbsp;
      <strong>ATH MIN/MAX:</strong> % from All-Time-High range<br>
      <strong>MAX BUYS:</strong> Max averaging positions &nbsp;&bull;&nbsp;
      <strong>BUY DROP:</strong> Drop % to trigger next buy &nbsp;&bull;&nbsp;
      <strong>TARGET/SL:</strong> Exit thresholds &nbsp;&bull;&nbsp;
      <strong>MAX DURATION:</strong> Max holding days
    </div>
  </div>
</div>

<div id="tab-disclaimer" class="hidden">
  <div class="disclaimer-box">
    <h2>&#9888; Disclaimer</h2>
    <p>This dashboard is strictly for <strong>educational and informational purposes only</strong>.</p>
    <p>All views and analysis are <strong>personal opinions</strong> based on technical and historical data. They should <strong>NOT</strong> be considered investment advice.</p>
    <p><strong>Past performance is not a guarantee of future results.</strong></p>
    <p>I am <strong>NOT responsible</strong> for any profit, loss, or damages from the use of this dashboard.</p>
    <p><strong>I am NOT a SEBI registered advisor.</strong> Please consult a certified financial advisor before investing.</p>
  </div>
</div>


<div id="tab-avgtrigger" class="hidden">
  <div class="card">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
      <h3 style="margin:0;color:var(--navy);font-size:16px;font-weight:800;">&#8681; Avg Trigger</h3>
      <span style="font-size:12px;color:var(--text3);">Open positions where price dropped 10%+ below avg buy — averaging candidates</span>
      <div style="margin-left:auto;display:flex;gap:6px;">
        <button class="btn-sm btn-green" onclick="exportTabCSV('avgtrigger')">Export CSV</button>
      </div>
    </div>
    <div id="avgtrigger-badges" class="tab-badges"></div>
    <div class="table-area">
      <table><thead><tr>
        <th>#</th><th>CFG</th><th>Symbol</th><th>Signal Date</th>
        <th>Avg Buy ₹</th><th>Current LTP ₹</th><th>Drop%</th>
        <th>Next Buy Price</th><th>Distance</th><th>Days Held</th>
      </tr></thead><tbody id="avgtrigger-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="avgtrigger-info"></span></div>
  </div>
</div>

<div id="tab-selltrigger" class="hidden">
  <div class="card">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
      <h3 style="margin:0;color:var(--navy);font-size:16px;font-weight:800;">&#8682; Sell Trigger</h3>
      <span style="font-size:12px;color:var(--text3);">Open positions within 3% of target price — sell candidates</span>
      <div style="margin-left:auto;display:flex;gap:6px;">
        <button class="btn-sm btn-green" onclick="exportTabCSV('selltrigger')">Export CSV</button>
      </div>
    </div>
    <div id="selltrigger-badges" class="tab-badges"></div>
    <div class="table-area">
      <table><thead><tr>
        <th>#</th><th>CFG</th><th>Symbol</th><th>Signal Date</th>
        <th>Avg Buy ₹</th><th>Current LTP ₹</th><th>Target ₹</th>
        <th>Distance to TGT</th><th>P&amp;L ₹</th><th>P&amp;L%</th><th>Days Held</th>
      </tr></thead><tbody id="selltrigger-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="selltrigger-info"></span></div>
  </div>
</div>

<div id="tab-avghistory" class="hidden">
  <div class="card">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
      <h3 style="margin:0;color:var(--navy);font-size:16px;font-weight:800;">&#9400; Avg History</h3>
      <span style="font-size:12px;color:var(--text3);">Trades with multiple buy legs (BUY_COUNT &gt; 1)</span>
      <span class="slbl">Config:</span>
      <button class="btn-filter active" onclick="avgHistCfgFilter('ALL',this)">All</button>
      <button class="btn-filter" onclick="avgHistCfgFilter('C1',this)">C1</button>
      <button class="btn-filter" onclick="avgHistCfgFilter('C2',this)">C2</button>
      <button class="btn-filter" onclick="avgHistCfgFilter('C3',this)">C3</button>
      <button class="btn-filter" onclick="avgHistCfgFilter('C4',this)">C4</button>
      <div style="margin-left:auto;display:flex;gap:6px;">
        <button class="btn-sm btn-green" onclick="exportTabCSV('avghistory')">Export CSV</button>
      </div>
    </div>
    <div id="avghistory-badges" class="tab-badges"></div>
    <div class="table-area">
      <table><thead><tr>
        <th>#</th><th>CFG</th><th>Symbol</th><th>Signal Date</th>
        <th>Buy Count</th><th>Avg Buy ₹</th><th>Total Invested ₹</th>
        <th>Current LTP ₹</th><th>P&amp;L ₹</th><th>P&amp;L%</th><th>Status</th>
      </tr></thead><tbody id="avghistory-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="avghistory-info"></span></div>
  </div>
</div>

<div id="tab-marketdata" class="hidden">
  <div class="card">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
      <h3 style="margin:0;color:var(--navy);font-size:16px;font-weight:800;">&#128200; Market Data</h3>
      <span style="font-size:12px;color:var(--text3);">All open positions with latest price & P&amp;L</span>
      <span class="slbl">Config:</span>
      <button class="btn-filter active" onclick="mdCfgFilter('ALL',this)">All</button>
      <button class="btn-filter" onclick="mdCfgFilter('C1',this)">C1</button>
      <button class="btn-filter" onclick="mdCfgFilter('C2',this)">C2</button>
      <button class="btn-filter" onclick="mdCfgFilter('C3',this)">C3</button>
      <button class="btn-filter" onclick="mdCfgFilter('C4',this)">C4</button>
      <div style="display:flex;gap:6px;margin-left:auto;">
        <button class="btn-filter active" id="md-all" onclick="mdSubTab('all',this)">All</button>
        <button class="btn-filter" id="md-gain" onclick="mdSubTab('gainers',this)">&#9650; Gainers</button>
        <button class="btn-filter" id="md-loss" onclick="mdSubTab('losers',this)">&#9660; Losers</button>
        <button class="btn-sm btn-green" onclick="exportTabCSV('marketdata')">Export CSV</button>
      </div>
    </div>
    <div id="marketdata-badges" class="tab-badges"></div>
    <div class="table-area">
      <table><thead><tr>
        <th>#</th><th>CFG</th><th>Symbol</th><th>Signal Date</th>
        <th>Avg Buy ₹</th><th>LTP ₹</th><th>P&amp;L ₹</th><th>P&amp;L%</th>
        <th>Target ₹</th><th>Stop ₹</th><th>Total Inv ₹</th><th>Mkt Val ₹</th><th>Days</th>
      </tr></thead><tbody id="marketdata-body"></tbody></table>
    </div>
    <div class="pager"><span class="info" id="marketdata-info"></span></div>
  </div>
</div>

<div id="tab-performance" class="hidden">
  <div class="card">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px;">
      <h3 style="margin:0;color:var(--navy);font-size:16px;font-weight:800;">&#128202; Performance Analytics</h3>
      <span style="font-size:12px;color:var(--text3);">Deep dive into closed and open trade statistics</span>
      <span class="slbl">Config:</span>
      <button class="btn-filter active" onclick="perfCfgFilter('ALL',this)">All</button>
      <button class="btn-filter" onclick="perfCfgFilter('C1',this)">C1</button>
      <button class="btn-filter" onclick="perfCfgFilter('C2',this)">C2</button>
      <button class="btn-filter" onclick="perfCfgFilter('C3',this)">C3</button>
      <button class="btn-filter" onclick="perfCfgFilter('C4',this)">C4</button>
    </div>
    <div id="perf-hero" class="perf-hero"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px;" class="perf-panels">
      <div class="card" style="margin:0;padding:16px;">
        <h4 style="color:var(--navy);margin-bottom:12px;">&#9989; Closed Trades Breakdown (Per Config)</h4>
        <div class="table-area">
          <table><thead><tr>
            <th>Config</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win%</th>
            <th>Avg Gain</th><th>Avg Loss</th><th>P Factor</th><th>Net P&amp;L</th>
          </tr></thead><tbody id="perf-closed-body"></tbody></table>
        </div>
      </div>
      <div class="card" style="margin:0;padding:16px;">
        <h4 style="color:var(--navy);margin-bottom:12px;">&#128200; Open Trades Breakdown (Per Config)</h4>
        <div class="table-area">
          <table><thead><tr>
            <th>Config</th><th>Open Trades</th><th>Total Invested</th><th>Market Value</th>
            <th>Unrealized P&amp;L</th><th>P&amp;L%</th>
          </tr></thead><tbody id="perf-open-body"></tbody></table>
        </div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px;">
      <div class="card" style="margin:0;padding:16px;">
        <h4 style="color:var(--green);margin-bottom:12px;">&#127942; Top 10 Profitable Stocks</h4>
        <div class="table-area">
          <table><thead><tr><th>Symbol</th><th>Trades</th><th>Net P&amp;L ₹</th><th>Win%</th></tr></thead>
          <tbody id="perf-top-profit"></tbody></table>
        </div>
      </div>
      <div class="card" style="margin:0;padding:16px;">
        <h4 style="color:var(--red);margin-bottom:12px;">&#128308; Top 10 Loss Stocks</h4>
        <div class="table-area">
          <table><thead><tr><th>Symbol</th><th>Trades</th><th>Net P&amp;L ₹</th><th>Win%</th></tr></thead>
          <tbody id="perf-top-loss"></tbody></table>
        </div>
      </div>
    </div>
  </div>
</div>

<div id="stockDetailModal">
  <div class="sdm-box" style="max-width:900px;width:96%;">
    <div class="sdm-hdr">
      <h3 id="sdm-title">Stock History</h3>
      <button class="sdm-close" onclick="closeStockDetail()">&#10005;</button>
    </div>
    <div class="sdm-body">
      <div id="sdm-badges" class="tab-badges" style="margin-bottom:12px;"></div>
      <div class="table-area">
        <table><thead><tr>
          <th>CFG</th><th>Buy Date</th><th>Avg Buy ₹</th><th>Exit Price ₹</th>
          <th>P&amp;L ₹</th><th>P&amp;L%</th><th>Status</th><th>Days</th><th>Result</th><th>OHLC</th>
        </tr></thead><tbody id="sdm-body"></tbody></table>
      </div>
      <div id="sdm-ohlc-panel" style="display:none;margin-top:14px;border-top:2px solid #e2e8f0;padding-top:12px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
          <strong id="sdm-ohlc-title" style="color:var(--navy);font-size:14px;">📈 OHLC Prices</strong>
          <button onclick="document.getElementById('sdm-ohlc-panel').style.display='none'" style="font-size:11px;padding:2px 8px;border:1px solid #cbd5e1;border-radius:6px;cursor:pointer;background:#f8faff;">✕ Close</button>
        </div>
        <div class="table-area" style="max-height:260px;overflow-y:auto;">
          <table><thead><tr>
            <th>Date</th><th>Open ₹</th><th>High ₹</th><th>Low ₹</th><th>Close ₹</th><th>Chg%</th>
          </tr></thead><tbody id="sdm-ohlc-body"></tbody></table>
        </div>
      </div>
    </div>
  </div>
</div>

</div><footer><strong>PS Market</strong> &mdash; NSE BTST Signals &nbsp;|&nbsp; Educational Purpose Only &nbsp;|&nbsp; Not SEBI Registered</footer>
<div id="toast-container"></div>

<script>
// ─── DATA ─────────────────────────────────────────────────────────────────────
const ALL_ROWS    = {rows_js};
const SIGNALS_RAW = {signals_js};
const NIFTY_DATA  = {nifty_js};
const CONFIGS_DEF = {configs_js};
const TRADE_OHLC  = {trade_ohlc_js};

// ─── OPEN POSITION MAPS ────────────────────────────────────────────────────────
const openSymbols = new Set(ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open').map(r=>r.SYMBOL));
const openMap = {{}};
ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open').forEach(r=>{{
  if(!openMap[r.SYMBOL]) openMap[r.SYMBOL]=parseFloat(r.CURRENT_LTP)||0;
}});

// ─── INDICES ─────────────────────────────────────────────────────────────────
(function(){{
  // Try to fetch fresh nifty data from nse-btst-dashboard first
  fetch('https://spurandhar0.github.io/nse-btst-dashboard/nifty_index.json')
    .then(r=>r.json())
    .then(liveData=>renderIndices(liveData))
    .catch(()=>renderIndices(NIFTY_DATA));

  function renderIndices(data){{
  const map = {{
    'idx-nifty50':  {{key:'nifty50',  label:'NIFTY 50'}},
    'idx-banknifty':{{key:'banknifty',label:'BANKNIFTY'}},
    'idx-sensex':   {{key:'sensex',   label:'SENSEX'}},
    'idx-niftyit':  {{key:'niftyit',  label:'NIFTY IT'}},
  }};
  Object.entries(map).forEach(([id,{{key,label}}])=>{{
    const el=document.getElementById(id), d=data[key];
    if(!d||!d.price){{
      // Fallback for array format
      let match;
      if(!d && Array.isArray(data.indices)){{
        match = data.indices.find(x => x.label === label);
      }}
      if(match){{
         const chg=match.change||0,chgPc=match.change_pct||0,cls=chg>0?'pos':chg<0?'neg':'flat',sign=chg>0?'+':'';
         el.innerHTML=`<div><div class="idx-name">${{label}}</div><div class="idx-date">${{match.date||''}}</div></div>
         <div><div class="idx-price">${{Number(match.close).toLocaleString('en-IN',{{maximumFractionDigits:2}})}}</div>
         <div class="idx-chg ${{cls}}">${{sign}}${{Number(chg).toFixed(2)}} (${{sign}}${{Number(chgPc).toFixed(2)}}%)</div></div>`;
      }} else {{
         el.innerHTML='<span class="idx-loading">'+label+' N/A</span>';
      }}
      return;
    }}
    const chg=d.change||0,chgPc=d.change_pct||0,cls=chg>0?'pos':chg<0?'neg':'flat',sign=chg>0?'+':'';
    el.innerHTML=`<div><div class="idx-name">${{label}}</div><div class="idx-date">${{d.date||''}}</div></div>
      <div><div class="idx-price">${{Number(d.price).toLocaleString('en-IN',{{maximumFractionDigits:2}})}}</div>
      <div class="idx-chg ${{cls}}">${{sign}}${{Number(chg).toFixed(2)}} (${{sign}}${{Number(chgPc).toFixed(2)}}%)</div></div>`;
  }});
  }} // end renderIndices
}})();

// ─── DATE RANGE GLOBALS ──────────────────────────────────────────────────────
let dateRangeActive=false, fromDateGlobal=null, toDateGlobal=null;

// ─── DATE RANGE FUNCTIONS ─────────────────────────────────────────────────────
function applyDateRange(){{
  const f=document.getElementById('fromDate').value;
  const t=document.getElementById('toDate').value;
  if(!f||!t){{toast('Select both From and To dates','info');return;}}
  if(new Date(f)>new Date(t)){{toast('From cannot be after To','info');return;}}
  fromDateGlobal=f; toDateGlobal=t; dateRangeActive=true;
  const pill=document.getElementById('filterPill');
  const days=Math.ceil((new Date(t)-new Date(f))/(864e5))+1;
  pill.textContent=`📅 ${{f}} → ${{t}} (${{days}}d)`;
  pill.style.display='inline-block'; pill.style.color='#2563eb'; pill.style.borderColor='#2563eb';
  // re-render current active tab
  const activeTab=document.querySelector('.tab.active');
  if(activeTab) activeTab.click();
  toast(`Range filter: ${{f}} to ${{t}}`,'success');
}}
function resetDateRange(){{
  fromDateGlobal=null; toDateGlobal=null; dateRangeActive=false;
  document.getElementById('fromDate').value='';
  document.getElementById('toDate').value='';
  const pill=document.getElementById('filterPill');
  pill.textContent=''; pill.style.display='none';
  const activeTab=document.querySelector('.tab.active');
  if(activeTab) activeTab.click();
  toast('Date range reset','info');
}}
function inDateRange(dateStr){{
  if(!dateRangeActive||!fromDateGlobal||!toDateGlobal) return true;
  if(!dateStr) return false;
  return dateStr>=fromDateGlobal && dateStr<=toDateGlobal;
}}

// ─── STATE ───────────────────────────────────────────────────────────────────
const state = {{
  open:    {{cfg:'ALL', page:1, sort:0, asc:false}},
  closed:  {{cfg:'ALL', res:'ALL', page:1, sort:0, asc:false}},
  fe:      {{cfg:'ALL', page:1, sort:0, asc:false}},
  hist:    {{cfg:'ALL'}},
  avghistory: {{cfg:'ALL'}},
  marketdata: {{cfg:'ALL'}},
  perf:    {{cfg:'ALL'}},
  ledger:  {{cfg:'ALL', page:1, sort:0, asc:false}},
  trades:  {{cfg:'ALL', status:'ALL', page:1, sort:0, asc:false}},
  signals: {{cfg:'ALL', page:1, sort:0, asc:false}},
}};

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const f2 = v => (v==null||v==='')?'—':Number(v).toFixed(2);
const fN = v => (v==null||v==='')?'—':Number(v).toLocaleString('en-IN',{{maximumFractionDigits:2}});
const fI = v => (v==null||v==='')?'—':parseInt(v);
const fD = v => v||'—';

function pnlColor(v){{
  if(v==null||v==='')return '';
  return parseFloat(v)>=0?'class="green"':'class="red"';
}}

function resultBadge(r){{
  if(!r)return '<span class="result-badge rb-invalid">—</span>';
  const lc=r.toLowerCase();
  if(lc.includes('profit'))return `<span class="result-badge rb-profit">${{r}}</span>`;
  if(lc.includes('loss'))  return `<span class="result-badge rb-loss">${{r}}</span>`;
  if(r==='Open')           return `<span class="result-badge rb-open">Open</span>`;
  if(r==='Pending')        return `<span class="result-badge rb-pending">Pending</span>`;
  return `<span class="result-badge rb-invalid">${{r}}</span>`;
}}

function orderBadge(order,status){{
  if(order==='Executed'&&status==='Open')   return resultBadge('Open');
  if(order==='Executed'&&status==='Closed') return resultBadge('Profit'); // will be overridden
  if(order==='Pending')  return `<span class="result-badge rb-pending">Pending</span>`;
  if(order==='Expired')  return `<span class="result-badge rb-expired">Expired</span>`;
  if(order==='Invalid')  return `<span class="result-badge rb-invalid">Invalid</span>`;
  return `<span class="result-badge rb-invalid">${{order||'—'}}</span>`;
}}

function cfgBadge(cfg){{
  const cls = cfg?cfg.toLowerCase():'';
  return `<span class="cfg-badge ${{cls}}">${{cfg||'—'}}</span>`;
}}

// ─── TABS ─────────────────────────────────────────────────────────────────────
function showTab(name,el){{
  document.querySelectorAll('[id^="tab-"]').forEach(t=>t.classList.add('hidden'));
  document.getElementById('tab-'+name).classList.remove('hidden');
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  if(name==='overview') buildOverview();
  else if(name==='open')    renderTab('open');
  else if(name==='closed')  renderTab('closed');
  else if(name==='fe')      renderTab('fe');
  else if(name==='history') buildHistory();
  else if(name==='ledger')  renderTab('ledger');
  else if(name==='trades')  renderTab('trades');
  else if(name==='signals')   renderTab('signals');
  else if(name==='avgtrigger')  renderAvgTrigger();
  else if(name==='selltrigger') renderSellTrigger();
  else if(name==='avghistory')  renderAvgHistory();
  else if(name==='marketdata')  renderMarketData();
  else if(name==='performance') renderPerformance();
}}

// ─── FILTER HELPERS ──────────────────────────────────────────────────────────
function cfgFilter(tab,val,btn){{
  state[tab].cfg=val;
  if(state[tab].page!==undefined)state[tab].page=1;
  btn.parentElement.querySelectorAll('.btn-filter').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  if(tab==='hist')buildHistory();
  else renderTab(tab);
}}

function resFilter(tab,val,btn){{
  state[tab].res=val;
  state[tab].page=1;
  // remove active from all res filters
  document.querySelectorAll(`[id^="${{tab}}-res-"]`).forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderTab(tab);
}}

function statusFilter(val,btn){{
  state.trades.status=val;
  state.trades.page=1;
  document.querySelectorAll('[id^="trades-status-"]').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderTab('trades');
}}

function srt(tab,col){{
  if(state[tab].sort===col)state[tab].asc=!state[tab].asc;
  else{{state[tab].sort=col;state[tab].asc=false;}}
  state[tab].page=1;
  renderTab(tab);
}}

function pg(tab,dir){{
  state[tab].page=Math.max(1,state[tab].page+dir);
  renderTab(tab);
}}

function setPager(tab,cur,total,pgSz){{
  const pages=Math.max(1,Math.ceil(total/pgSz));
  if(cur>pages){{state[tab].page=pages;}}
  document.getElementById(tab+'-info').textContent=`${{(cur-1)*pgSz+1}}–${{Math.min(cur*pgSz,total)}} of ${{total}} | Page ${{Math.min(cur,pages)}}/${{pages}}`;
}}

// ─── GET FILTERED DATA ────────────────────────────────────────────────────────
function getFiltered(tab){{
  let rows = ALL_ROWS;

  if(tab==='open'){{
    rows = rows.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open');
    if(state.open.cfg!=='ALL') rows=rows.filter(r=>r.CONFIG===state.open.cfg);
    if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE));
  }}
  else if(tab==='closed'){{
    rows = rows.filter(r=>r.STATUS==='Closed'&&r.RESULT);
    if(state.closed.cfg!=='ALL') rows=rows.filter(r=>r.CONFIG===state.closed.cfg);
    if(state.closed.res==='P') rows=rows.filter(r=>r.RESULT&&r.RESULT.toLowerCase().includes('profit')&&!r.RESULT.includes('FE'));
    if(state.closed.res==='L') rows=rows.filter(r=>r.RESULT&&r.RESULT.toLowerCase().includes('loss')&&!r.RESULT.includes('FE'));
    if(state.closed.res==='FE') rows=rows.filter(r=>r.RESULT&&r.RESULT.includes('FE'));
    if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE));
  }}
  else if(tab==='fe'){{
    const cfgDurMap={{}};
    CONFIGS_DEF.forEach(c=>{{ cfgDurMap[c.id||c.ID]=parseInt(c.max_duration||c.MAXDURA||90); }});
    rows = rows.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open');
    if(state.fe.cfg!=='ALL') rows=rows.filter(r=>r.CONFIG===state.fe.cfg);
    if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE));
    rows=rows.map(r=>{{
      const maxD=cfgDurMap[r.CONFIG]||90;
      const held=parseInt(r.MARKET_DAYS)||0;
      const left=Math.max(0,maxD-held);
      return {{...r,_MAX_DUR:maxD,_DAYS_LEFT:left}};
    }});
    // Show only trades that have used ≥60% of max duration (approaching FE threshold)
    rows=rows.filter(r=>r._DAYS_LEFT<=Math.ceil(r._MAX_DUR*0.4));
    rows.sort((a,b)=>a._DAYS_LEFT-b._DAYS_LEFT);
  }}
  else if(tab==='ledger'){{
    // Build ledger from closed rows
    let closed = ALL_ROWS.filter(r=>r.STATUS==='Closed'&&r.PROFIT!=null&&r.EXIT_DATE);
    if(state.ledger.cfg!=='ALL') closed=closed.filter(r=>r.CONFIG===state.ledger.cfg);
    if(dateRangeActive) closed=closed.filter(r=>inDateRange(r.SIGNAL_DATE)); // <-- ADDED GLOBAL FILTER
    const map={{}};
    closed.forEach(r=>{{
      const d=r.EXIT_DATE;
      if(!map[d])map[d]={{date:d,total:0,profit:0,loss:0,pnl:0}};
      map[d].total++;
      const p=parseFloat(r.PROFIT)||0;
      map[d].pnl+=p;
      if(p>=0)map[d].profit++;else map[d].loss++;
    }});
    rows = Object.values(map).sort((a,b)=>a.date<b.date?1:-1);
    // Add cumulative
    let cum=0;
    const sorted=[...rows].sort((a,b)=>a.date<b.date?-1:1);
    const cumMap={{}};
    sorted.forEach(r=>{{cum+=r.pnl;cumMap[r.date]=cum;}});
    rows=rows.map(r=>{{return{{...r,cum:cumMap[r.date]}}}});
    return rows;
  }}
  else if(tab==='trades'){{
    rows = rows.filter(r=>r.ORDER==='Executed');
    if(state.trades.cfg!=='ALL') rows=rows.filter(r=>r.CONFIG===state.trades.cfg);
    if(state.trades.status!=='ALL') rows=rows.filter(r=>r.STATUS===state.trades.status);
    const q=(document.getElementById('trades-search')||{{}}).value||'';
    if(q)rows=rows.filter(r=>(r.SYMBOL||'').toLowerCase().includes(q.toLowerCase()));
  }}
  else if(tab==='signals'){{
    rows=[...SIGNALS_RAW];
    if(sigCfg!=='ALL') rows=rows.filter(r=>{{
      const cfgRaw=(r.CONFIGS_MATCHED||r.configs_matched||r.CONFIG||'');
      return cfgRaw.split(',').map(s=>s.trim()).includes(sigCfg);
    }});
    const statusF=(document.getElementById('sig-status-filter')||{{}}).value||'ALL';
    if(statusF!=='ALL') rows=rows.filter(r=>{{
      const sym=r.SYMBOL||r.symbol||'';
      return (openSymbols.has(sym)?'Open Call':'Fresh Call')===statusF;
    }});
  }}

  // Sort
  const st=state[tab];
  if(st&&st.sort!==undefined){{
    rows=[...rows];
    rows.sort((a,b)=>{{
      let va,vb;
      // generic: use array index approach per tab
      const sv=getTabSortVals(tab,a,b,st.sort);
      va=sv[0];vb=sv[1];
      if(typeof va==='string') return st.asc?(va<vb?-1:1):(va>vb?-1:1);
      return st.asc?(va-vb):(vb-va);
    }});
  }}
  return rows;
}}

function getTabSortVals(tab,a,b,col){{
  const nv=x=>parseFloat(x)||0;
  const sv=x=>x||'';
  if(tab==='open'){{
    const cols=[0,'CONFIG','SYMBOL','SIGNAL_DATE','AVG_BUY_PRICE','CURRENT_LTP','TARGET_PRICE','STOP_PRICE','BUY_COUNT','TOTAL_QTY','TOTAL_INVESTMENT','MARKET_DAYS','PROFIT','GAIN_PCT'];
    const k=cols[col]||'SYMBOL';
    if(typeof a[k]==='string')return[sv(a[k]),sv(b[k])];
    return[nv(a[k]),nv(b[k])];
  }}
  if(tab==='closed'){{
    const cols=[0,'CONFIG','SYMBOL','SIGNAL_DATE','EXIT_DATE','AVG_BUY_PRICE','EXIT_PRICE','TOTAL_QTY','TOTAL_INVESTMENT','PROFIT','GAIN_PCT','MARKET_DAYS','RESULT'];
    const k=cols[col]||'EXIT_DATE';
    if(typeof a[k]==='string')return[sv(a[k]),sv(b[k])];
    return[nv(a[k]),nv(b[k])];
  }}
  if(tab==='fe'){{
    const cols=[0,'CONFIG','SYMBOL','SIGNAL_DATE','AVG_BUY_PRICE','CURRENT_LTP','TARGET_PRICE','STOP_PRICE','MARKET_DAYS','_DAYS_LEFT','PROFIT','GAIN_PCT','BUY_COUNT'];
    const k=cols[col]||'MARKET_DAYS';
    if(typeof a[k]==='string')return[sv(a[k]),sv(b[k])];
    return[nv(a[k]),nv(b[k])];
  }}
  if(tab==='ledger'){{
    const cols=[0,'date','total','profit','loss','pnl','cum'];
    const k=cols[col]||'date';
    if(k==='date')return[sv(a.date),sv(b.date)];
    return[nv(a[k]),nv(b[k])];
  }}
  if(tab==='trades'){{
    const cols=[0,'CONFIG','SYMBOL','SIGNAL_DATE','EXIT_DATE','STATUS','AVG_BUY_PRICE','EXIT_PRICE','TOTAL_QTY','BUY_COUNT','PROFIT','GAIN_PCT','MARKET_DAYS','RESULT'];
    const k=cols[col]||'SIGNAL_DATE';
    if(typeof a[k]==='string')return[sv(a[k]),sv(b[k])];
    return[nv(a[k]),nv(b[k])];
  }}
  if(tab==='signals'){{
    // cols: #, DATE, STOCK, 1D%, 5D%, BUY PRICE, LTP, TARGET, SL, STATUS
    if(col===1)return[sv(a.SIGNAL_DATE||a.signal_date||''),sv(b.SIGNAL_DATE||b.signal_date||'')];
    if(col===2)return[sv(a.SYMBOL||a.symbol||''),sv(b.SYMBOL||b.symbol||'')];
    if(col===3)return[nv(a.CHG_PCT||a.chg_pct||0),nv(b.CHG_PCT||b.chg_pct||0)];
    if(col===5||col===6){{
      const ac=parseFloat(a.CLOSE||a.close||0);
      const bc=parseFloat(b.CLOSE||b.close||0);
      return[ac,bc];
    }}
    if(col===9){{
      const as=openSymbols.has(a.SYMBOL||'')?'Open Call':'Fresh Call';
      const bs=openSymbols.has(b.SYMBOL||'')?'Open Call':'Fresh Call';
      return[sv(as),sv(bs)];
    }}
    return[0,0];
  }}
  return[0,0];
}}

// ─── RENDER TABS ─────────────────────────────────────────────────────────────
function renderTab(tab){{
  const rows=getFiltered(tab);
  if(tab==='ledger'){{ renderLedger(rows);return; }}
  if(tab==='signals'){{ renderSignals(rows);return; }}
  if(tab==='open') renderBadges('open-badges', rows, 'open');
  else if(tab==='closed') renderBadges('closed-badges', rows, 'closed');
  else if(tab==='fe') renderBadges('fe-badges', rows, 'open');
  else if(tab==='trades'){{
    const tProfit=rows.filter(r=>(parseFloat(r.PROFIT)||0)>0).length;
    const tLoss=rows.filter(r=>(parseFloat(r.PROFIT)||0)<0).length;
    const tOpen=rows.filter(r=>r.STATUS==='Open').length;
    const tNet=rows.reduce((s,r)=>s+(parseFloat(r.PROFIT)||0),0);
    const bd=document.getElementById('trades-badges');
    if(bd) bd.innerHTML=`<span class="tbadge blue">Total: ${{rows.length}}</span><span class="tbadge">Open: ${{tOpen}}</span><span class="tbadge green">Profit: ${{tProfit}}</span><span class="tbadge red">Loss: ${{tLoss}}</span><span class="tbadge ${{tNet>=0?'green':'red'}}">Net P&L: &#8377;${{fN(tNet)}}</span>`;
  }}
  const pgSzEl=document.getElementById(tab+'-pgsize');
  const pgSz=pgSzEl?parseInt(pgSzEl.value):50;
  const page=state[tab].page||1;
  const start=(page-1)*pgSz;
  const slice=rows.slice(start,start+pgSz);
  setPager(tab,page,rows.length,pgSz);
  const body=document.getElementById(tab+'-body');
  if(!slice.length){{
    const emptyMsg=tab==='fe'?
      '<tr><td colspan="13" class="empty">&#10003; No trades approaching Force Exit threshold — all open positions are within safe limits.</td></tr>':
      `<tr><td colspan="20" class="empty">No data.</td></tr>`;
    body.innerHTML=emptyMsg;return;
  }}
  body.innerHTML=slice.map((r,i)=>rowHTML(tab,r,start+i+1)).join('');
}}

function rowHTML(tab,r,n){{
  if(tab==='open'){{
    const pl=parseFloat(r.PROFIT)||0;
    const gp=parseFloat(r.GAIN_PCT)||0;
    const bc=parseInt(r.BUY_COUNT||1);
    const bcHtml=bc>1
      ?`<span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:900;background:linear-gradient(135deg,var(--blue2),var(--cyan2));color:#fff">${{bc}}x</span>`
      :`<span style="color:var(--text3)">${{bc}}</span>`;
    return `<tr>
      <td>${{n}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td>
      <td>&#8377;${{fN(r.AVG_BUY_PRICE)}}</td><td>&#8377;${{fN(r.CURRENT_LTP)}}</td>
      <td>&#8377;${{fN(r.TARGET_PRICE)}}</td><td>&#8377;${{fN(r.STOP_PRICE)}}</td>
      <td>${{bcHtml}}</td><td>${{fI(r.TOTAL_QTY)}}</td>
      <td>&#8377;${{fN(r.TOTAL_INVESTMENT)}}</td><td>${{fI(r.MARKET_DAYS)}}</td>
      <td ${{pnlColor(r.PROFIT)}}>&#8377;${{fN(r.PROFIT)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{gp>=0?'+':''}}${{f2(r.GAIN_PCT)}}%</td>
    </tr>`;
  }}
  if(tab==='closed'){{
    return `<tr>
      <td>${{n}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td><td>${{fD(r.EXIT_DATE)}}</td>
      <td>&#8377;${{fN(r.AVG_BUY_PRICE)}}</td><td>&#8377;${{fN(r.EXIT_PRICE)}}</td>
      <td>${{fI(r.TOTAL_QTY)}}</td><td>&#8377;${{fN(r.TOTAL_INVESTMENT)}}</td>
      <td ${{pnlColor(r.PROFIT)}}>&#8377;${{fN(r.PROFIT)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{(parseFloat(r.GAIN_PCT)||0)>=0?'+':''}}${{f2(r.GAIN_PCT)}}%</td>
      <td>${{fI(r.MARKET_DAYS)}}</td>
      <td>${{resultBadge(r.RESULT)}}</td>
    </tr>`;
  }}
  if(tab==='fe'){{
    const held=parseInt(r.MARKET_DAYS)||0;
    const left=r._DAYS_LEFT!=null?r._DAYS_LEFT:Math.max(0,(r._MAX_DUR||90)-held);
    const urgCls=left<=5?'color:#dc2626;font-weight:900':left<=15?'color:#d97706;font-weight:800':'color:#059669;font-weight:700';
    const urgIcon=left<=5?'🔴':left<=15?'⚠️':'✅';
    const bc=parseInt(r.BUY_COUNT||1);
    const bcHtml=bc>1?`<span style="font-weight:800;color:var(--blue2)">${{bc}}x</span>`:`${{bc}}`;
    return `<tr>
      <td>${{n}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td>
      <td>&#8377;${{fN(r.AVG_BUY_PRICE)}}</td>
      <td class="${{(parseFloat(r.GAIN_PCT)||0)>=0?'green':'red'}}">&#8377;${{fN(r.CURRENT_LTP)}}</td>
      <td>&#8377;${{fN(r.TARGET_PRICE)}}</td><td>&#8377;${{fN(r.STOP_PRICE)}}</td>
      <td>${{held}}d</td>
      <td style="${{urgCls}}">${{urgIcon}} ${{left}}d</td>
      <td ${{pnlColor(r.PROFIT)}}>&#8377;${{fN(r.PROFIT)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{(parseFloat(r.GAIN_PCT)||0)>=0?'+':''}}${{f2(r.GAIN_PCT)}}%</td>
      <td>${{bcHtml}}</td>
    </tr>`;
  }}
  if(tab==='trades'){{
    const bc=parseInt(r.BUY_COUNT||1);
    const bcHtml=bc>1?`<span style="font-weight:800;color:var(--blue2)">${{bc}}x</span>`:`${{bc}}`;
    return `<tr>
      <td>${{n}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td><td>${{fD(r.EXIT_DATE)}}</td>
      <td>${{r.STATUS||'—'}}</td>
      <td>&#8377;${{fN(r.AVG_BUY_PRICE)}}</td><td>&#8377;${{fN(r.EXIT_PRICE)}}</td>
      <td>${{fI(r.TOTAL_QTY)}}</td><td>${{bcHtml}}</td>
      <td ${{pnlColor(r.PROFIT)}}>&#8377;${{fN(r.PROFIT)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{(parseFloat(r.GAIN_PCT)||0)>=0?'+':''}}${{f2(r.GAIN_PCT)}}%</td>
      <td>${{fI(r.MARKET_DAYS)}}</td>
      <td>${{resultBadge(r.RESULT)}}</td>
    </tr>`;
  }}
  return '';
}}

function renderLedger(rows){{
  const body=document.getElementById('ledger-body');
  if(!rows.length){{body.innerHTML='<tr><td colspan="7" class="empty">No closed trades yet.</td></tr>';
    document.getElementById('ledger-info').textContent='';return;}}
  body.innerHTML=rows.map((r,i)=>`<tr>
    <td>${{i+1}}</td><td>${{r.date}}</td>
    <td>${{r.total}}</td>
    <td class="green">${{r.profit}}</td>
    <td class="red">${{r.loss}}</td>
    <td ${{pnlColor(r.pnl)}}>&#8377;${{fN(r.pnl)}}</td>
    <td ${{pnlColor(r.cum)}}>&#8377;${{fN(r.cum)}}</td>
  </tr>`).join('');
  document.getElementById('ledger-info').textContent=`${{rows.length}} trading days`;
}}

function renderSignals(rows){{
  const pgSz=parseInt((document.getElementById('signals-pgsize')||{{}}).value||50);
  const page=state.signals.page;
  const start=(page-1)*pgSz;
  const slice=rows.slice(start,start+pgSz);
  setPager('signals',page,rows.length,pgSz);
  const body=document.getElementById('signals-body');
  if(!slice.length){{body.innerHTML='<tr><td colspan="11" class="empty">No signals.</td></tr>';return;}}
  body.innerHTML=slice.map((r,i)=>{{
    const sym=r.SYMBOL||r.symbol||'—';
    const date=r.SIGNAL_DATE||r.signal_date||'—';
    const close=parseFloat(r.CLOSE||r.close||r.SIGNAL_CLOSE||0);
    const chg1d=parseFloat(r.CHG_PCT||r.chg_pct||r.PCT_1D_CHANGE||0);
    const chg5dRaw=r.CHG_5D||r.PCT_5D||r.pct_5d||r.CHG5D||r.CHANGE_5D||null;
    const chg5d=chg5dRaw!=null?parseFloat(chg5dRaw):null;
    const ltp=openMap[sym]||close;
    const target=close*1.10;
    const sl=close*0.75;
    const isOpen=openSymbols.has(sym);
    const statusBadge=isOpen?'<span class="badge-opencall">Open Call</span>':'<span class="badge-fresh">Fresh Call</span>';
    const ltpHtml=isOpen?`<span class="green">&#8377;${{fN(ltp)}}</span>`:`&#8377;${{fN(close)}}`;
    const sigCfgRaw=r.CONFIGS_MATCHED||r.configs_matched||r.CONFIG||r.config||'';
    const sigCfgs=sigCfgRaw.split(',').map(s=>s.trim()).filter(Boolean);
    return `<tr>
      <td>${{start+i+1}}</td>
      <td>${{date}}</td>
      <td>${{sigCfgs.length?sigCfgs.map(c=>cfgBadge(c)).join(' '):'—'}}</td>
      <td><strong>${{sym}}</strong></td>
      <td ${{pnlColor(chg1d)}}>${{chg1d>=0?'+':''}}${{f2(chg1d)}}%</td>
      <td>${{chg5d!=null?`<span ${{chg5d>=0?'class="green"':'class="red"'}}>${{chg5d>=0?'+':''}}${{f2(chg5d)}}%</span>`:'—'}}</td>
      <td>&#8377;${{fN(close)}}</td>
      <td>${{ltpHtml}}</td>
      <td style="color:#059669;font-weight:700">&#8377;${{fN(target)}}</td>
      <td style="color:#dc2626;font-weight:700">&#8377;${{fN(sl)}}</td>
      <td>${{statusBadge}}</td>
    </tr>`;
  }}).join('');
  // Update summary badges
  const freshCount=SIGNALS_RAW.filter(r=>!openSymbols.has(r.SYMBOL||r.symbol||'')).length;
  const openCount=SIGNALS_RAW.length-freshCount;
  const sigBadges=document.getElementById('sig-total-badges');
  if(sigBadges)sigBadges.innerHTML=`
    <span class="tbadge blue">Total: ${{SIGNALS_RAW.length}}</span>
    <span class="tbadge green">Fresh Call: ${{freshCount}}</span>
    <span class="tbadge amber">Open Call: ${{openCount}}</span>`;
}}

// ─── OVERVIEW ─────────────────────────────────────────────────────────────────
function buildOverview(){{
  const cfgIds=['C1','C2','C3','C4'];
  let totExec=0,totOpen=0,totClosed=0,totPnl=0,totPT=0,totLoss=0;
  const rows=[];

  cfgIds.forEach(cid=>{{
    let crows=ALL_ROWS.filter(r=>r.CONFIG===cid);
    if(dateRangeActive) crows=crows.filter(r=>inDateRange(r.SIGNAL_DATE)); // <-- ADDED GLOBAL FILTER
    
    const exec=crows.filter(r=>r.ORDER==='Executed');
    const open=exec.filter(r=>r.STATUS==='Open');
    const closed=exec.filter(r=>r.STATUS==='Closed');
    const pt=closed.filter(r=>r.RESULT==='Profit-TGT');
    const sl=closed.filter(r=>r.RESULT==='Loss-SL');
    const fep=closed.filter(r=>r.RESULT&&r.RESULT.includes('FE')&&r.RESULT.includes('Profit'));
    const fel=closed.filter(r=>r.RESULT&&r.RESULT.includes('FE')&&r.RESULT.includes('Loss'));
    const pend=crows.filter(r=>r.ORDER==='Pending');
    const exp=crows.filter(r=>r.ORDER==='Expired');
    const inv=crows.filter(r=>r.ORDER==='Invalid');
    const profitTrades=closed.filter(r=>r.RESULT&&r.RESULT.toLowerCase().startsWith('profit'));
    const lossTrades=closed.filter(r=>r.RESULT&&r.RESULT.toLowerCase().startsWith('loss'));
    const wr=profitTrades.length+lossTrades.length>0?
      (profitTrades.length/(profitTrades.length+lossTrades.length)*100).toFixed(1):'—';
    const pnl=exec.reduce((s,r)=>s+(parseFloat(r.PROFIT)||0),0);
    const wrCls=parseFloat(wr)>=50?'class="green"':'class="red"';
    const pnlCls=pnl>=0?'class="green"':'class="red"';
    rows.push(`<tr>
      <td>${{cfgBadge(cid)}}</td>
      <td>${{crows.length}}</td><td>${{exec.length}}</td><td>${{open.length}}</td><td>${{closed.length}}</td>
      <td class="green">${{pt.length}}</td><td class="red">${{sl.length}}</td>
      <td class="green">${{fep.length}}</td><td class="red">${{fel.length}}</td>
      <td>${{pend.length}}</td><td>${{exp.length}}</td><td>${{inv.length}}</td>
      <td ${{wrCls}}>${{wr}}%</td>
      <td ${{pnlCls}}>&#8377;${{fN(pnl)}}</td>
    </tr>`);
    totExec+=exec.length; totOpen+=open.length; totClosed+=closed.length;
    totPnl+=pnl; totPT+=profitTrades.length; totLoss+=lossTrades.length;
  }});

  document.getElementById('ov-body').innerHTML=rows.join('');
  const totWr=totPT+totLoss>0?(totPT/(totPT+totLoss)*100).toFixed(1)+'%':'—';
  
  // Calculate total signals based on date range for accurate display
  let totalSigsFiltered = ALL_ROWS;
  if(dateRangeActive) totalSigsFiltered = totalSigsFiltered.filter(r=>inDateRange(r.SIGNAL_DATE));
  
  document.getElementById('ov-stats').innerHTML=`
    <div class="stat-card"><div class="stat-val">${{totalSigsFiltered.length}}</div><div class="stat-lbl">Total Signals</div></div>
    <div class="stat-card gc"><div class="stat-val">${{totExec}}</div><div class="stat-lbl">Executed</div></div>
    <div class="stat-card"><div class="stat-val">${{totOpen}}</div><div class="stat-lbl">Open</div></div>
    <div class="stat-card"><div class="stat-val">${{totClosed}}</div><div class="stat-lbl">Closed</div></div>
    <div class="stat-card gc"><div class="stat-val">${{totWr}}</div><div class="stat-lbl">Win Rate</div></div>
    <div class="stat-card ${{totPnl>=0?'gc':'rc'}}"><div class="stat-val">&#8377;${{fN(totPnl)}}</div><div class="stat-lbl">Total P&amp;L</div></div>`;
}}

// ─── STOCK HISTORY ────────────────────────────────────────────────────────────
function buildHistory(){{
  const q=(document.getElementById('hist-search')||{{}}).value||'';
  const cfg=state.hist.cfg;
  let rows=ALL_ROWS.filter(r=>r.ORDER==='Executed');
  if(cfg!=='ALL') rows=rows.filter(r=>r.CONFIG===cfg);
  if(q) rows=rows.filter(r=>(r.SYMBOL||'').toLowerCase().includes(q.toLowerCase()));
  if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE)); // <-- ADDED GLOBAL FILTER

  // Stats bar
  const holdRows=rows.filter(r=>r.STATUS==='Open');
  const soldRows=rows.filter(r=>r.STATUS!=='Open');
  const holdNet=holdRows.reduce((s,r)=>s+(parseFloat(r.PROFIT)||0),0);
  const soldNet=soldRows.reduce((s,r)=>s+(parseFloat(r.PROFIT)||0),0);
  const statEl=document.getElementById('hist-stats');
  if(statEl) statEl.innerHTML=`
    <div style="flex:1;min-width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;text-align:center">
      <div style="font-size:10px;font-weight:600;color:#64748b;letter-spacing:.5px;text-transform:uppercase">Hold Count</div>
      <div style="font-size:22px;font-weight:700;color:#2563eb">${{holdRows.length}}</div>
    </div>
    <div style="flex:1;min-width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;text-align:center">
      <div style="font-size:10px;font-weight:600;color:#64748b;letter-spacing:.5px;text-transform:uppercase">Hold Net</div>
      <div style="font-size:22px;font-weight:700;color:${{holdNet>=0?'#059669':'#dc2626'}}">&#8377;${{fN(holdNet)}}</div>
    </div>
    <div style="flex:1;min-width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;text-align:center">
      <div style="font-size:10px;font-weight:600;color:#64748b;letter-spacing:.5px;text-transform:uppercase">Sold Count</div>
      <div style="font-size:22px;font-weight:700;color:#2563eb">${{soldRows.length}}</div>
    </div>
    <div style="flex:1;min-width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;text-align:center">
      <div style="font-size:10px;font-weight:600;color:#64748b;letter-spacing:.5px;text-transform:uppercase">Sold Net</div>
      <div style="font-size:22px;font-weight:700;color:${{soldNet>=0?'#059669':'#dc2626'}}">&#8377;${{fN(soldNet)}}</div>
    </div>`;

  // Sort: open first (by date desc), then sold (by exit date desc)
  rows.sort((a,b)=>{{
    const aOpen=a.STATUS==='Open',bOpen=b.STATUS==='Open';
    if(aOpen!==bOpen) return bOpen?1:-1;
    return (a.SIGNAL_DATE||'')<(b.SIGNAL_DATE||'')?1:-1;
  }});

  if(!rows.length){{
    document.getElementById('hist-container').innerHTML='<div class="card empty">No executed trades found.</div>';
    return;
  }}

  document.getElementById('hist-container').innerHTML=rows.slice(0,100).map((r,i)=>{{
    const pnl=parseFloat(r.PROFIT)||0;
    const pct=parseFloat(r.GAIN_PCT)||0;
    const isSold=r.STATUS!=='Open';
    const ltp=isSold?(r.EXIT_PRICE||0):(r.CURRENT_LTP||0);
    const cardKey=`${{r.CONFIG}}|${{r.SYMBOL}}`;
    const exitTypeBadge=r.EXIT_TYPE?
      `<span style="border:1px solid #6366f1;border-radius:12px;padding:2px 10px;font-size:11px;color:#4f46e5;background:#f5f3ff">${{r.EXIT_TYPE}}</span>`
      :'—';

    // BUY HISTORY rows - one per buy count
    const buyCount=parseInt(r.BUY_COUNT)||1;
    const buyRows=Array.from({{length:buyCount}},(_,bi)=>`
      <tr style="border-top:1px solid #e2e8f0">
        <td style="padding:5px 8px">${{bi+1}}</td>
        <td style="padding:5px 8px">${{fD(r.SIGNAL_DATE)}}</td>
        <td style="padding:5px 8px;text-align:right;color:#f59e0b;font-weight:600">&#8377;${{fN(r.AVG_BUY_PRICE)}}</td>
        <td style="padding:5px 8px;text-align:right;color:#f59e0b;font-weight:600">&#8377;${{fN(r.AVG_BUY_PRICE)}}</td>
        <td style="padding:5px 8px;text-align:right">${{fI(r.TOTAL_QTY)}}</td>
        <td style="padding:5px 8px;text-align:right">&#8377;${{fN(r.TOTAL_INVESTMENT)}}</td>
      </tr>`).join('');

    const sellSection=isSold?`
      <div style="font-size:11px;font-weight:700;color:#dc2626;letter-spacing:.5px;margin:10px 0 6px">SELL HISTORY</div>
      <table style="width:100%;font-size:12px;border-collapse:collapse">
        <thead><tr style="background:#fff5f5">
          <th style="padding:5px 8px;text-align:left;font-weight:600">Sell #</th>
          <th style="padding:5px 8px;text-align:left;font-weight:600">Date</th>
          <th style="padding:5px 8px;text-align:right;font-weight:600">Sell Price</th>
          <th style="padding:5px 8px;text-align:center;font-weight:600">Exit Type</th>
        </tr></thead>
        <tbody>
          <tr style="border-top:1px solid #fee2e2">
            <td style="padding:5px 8px">1</td>
            <td style="padding:5px 8px">${{fD(r.EXIT_DATE)}}</td>
            <td style="padding:5px 8px;text-align:right;font-weight:600">&#8377;${{fN(r.EXIT_PRICE)}}</td>
            <td style="padding:5px 8px;text-align:center">${{exitTypeBadge}}</td>
          </tr>
        </tbody>
      </table>`:'';

    return `<div class="card" style="margin-bottom:14px;padding:0;overflow:hidden">
      <div style="padding:12px 16px;background:linear-gradient(135deg,#f8faff,#eef2ff);border-bottom:1px solid #e2e8f0;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <strong style="font-size:15px;color:#1e3a5f">${{i+1}}. ${{r.SYMBOL}}</strong>
        <span style="font-size:12px;color:#64748b">(${{fD(r.SIGNAL_DATE)}})</span>
        ${{cfgBadge(r.CONFIG)}}
      </div>
      <div style="padding:0 16px 8px">
        <div style="font-size:11px;font-weight:700;color:#059669;letter-spacing:.5px;margin:12px 0 6px">BUY HISTORY</div>
        <table style="width:100%;font-size:12px;border-collapse:collapse">
          <thead><tr style="background:#f0fdf4">
            <th style="padding:5px 8px;text-align:left;font-weight:600">Buy #</th>
            <th style="padding:5px 8px;text-align:left;font-weight:600">Date</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600;color:#f59e0b">Buy Price</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600;color:#f59e0b">Avg Buy</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">Qty (&#8377;10k)</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">Investment</th>
          </tr></thead>
          <tbody>${{buyRows}}</tbody>
        </table>
        ${{sellSection}}
        <div style="font-size:11px;font-weight:700;color:#2563eb;letter-spacing:.5px;margin:10px 0 6px">FINAL SUMMARY</div>
        <table style="width:100%;font-size:12px;border-collapse:collapse">
          <thead><tr style="background:#eff6ff">
            <th style="padding:5px 8px;text-align:left;font-weight:600">Status</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">Total Qty</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">Avg Buy Price</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">Exit/LTP</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">Investment</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">Duration</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">P&amp;L &#8377;</th>
            <th style="padding:5px 8px;text-align:right;font-weight:600">P&amp;L %</th>
          </tr></thead>
          <tbody>
            <tr style="border-top:1px solid #dbeafe">
              <td style="padding:5px 8px;color:${{isSold?'#dc2626':'#2563eb'}};font-weight:700">${{isSold?'SOLD':'HOLD'}}</td>
              <td style="padding:5px 8px;text-align:right;color:#2563eb;font-weight:600">${{fI(r.TOTAL_QTY)}}</td>
              <td style="padding:5px 8px;text-align:right">&#8377;${{fN(r.AVG_BUY_PRICE)}}</td>
              <td style="padding:5px 8px;text-align:right">&#8377;${{fN(ltp)}}</td>
              <td style="padding:5px 8px;text-align:right">&#8377;${{fN(r.TOTAL_INVESTMENT)}}</td>
              <td style="padding:5px 8px;text-align:right;color:#f59e0b;font-weight:600">${{fI(r.MARKET_DAYS)}} Days</td>
              <td style="padding:5px 8px;text-align:right;font-weight:600" ${{pnlColor(r.PROFIT)}}>&#8377;${{fN(pnl)}}</td>
              <td style="padding:5px 8px;text-align:right;font-weight:600" ${{pnlColor(r.GAIN_PCT)}}>${{pct>=0?'+':''}}${{f2(pct)}}%</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div style="padding:10px 16px 14px;display:flex;gap:8px;flex-wrap:wrap">
        <button onclick="openStockDetail('${{cardKey}}')" style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:6px 14px;font-size:12px;cursor:pointer;font-weight:500">&#128202; Show Daily History</button>
        <button onclick="exportHistCard(this,'${{r.SYMBOL}}_${{r.CONFIG}}_${{r.SIGNAL_DATE}}')" style="background:#059669;color:#fff;border:none;border-radius:8px;padding:6px 14px;font-size:12px;cursor:pointer;font-weight:500">&#128247; Export Image</button>
        <button onclick="toast('Use browser Print (Ctrl+P) to save as PDF','info')" style="background:#dc2626;color:#fff;border:none;border-radius:8px;padding:6px 14px;font-size:12px;cursor:pointer;font-weight:500">&#128196; Export PDF</button>
      </div>
    </div>`;
  }}).join('')+
  (rows.length>100?`<div class="card empty">Showing first 100 trades. Use search to narrow down.</div>`:'');
}}
function exportHistCard(btn,name){{
  const card=btn.closest('.card');
  if(!card){{toast('Cannot export','error');return;}}
  if(typeof html2canvas==='undefined'){{
    toast('Export Image loading... try again','info');
    const s=document.createElement('script');
    s.src='https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
    document.head.appendChild(s);
    return;
  }}
  html2canvas(card,{{scale:2,backgroundColor:'#fff',useCORS:true}}).then(canvas=>{{
    const a=document.createElement('a');
    a.download=`Stock_${{name}}.png`;
    a.href=canvas.toDataURL('image/png');
    a.click();
    toast('Image downloaded!','success');
  }});
}}

// ─── EXPORTS ─────────────────────────────────────────────────────────────────
function exportTab(tab){{
  const rows=getFiltered(tab);
  if(!rows.length){{toast('No data','info');return;}}
  const wb=XLSX.utils.book_new();
  const ws=XLSX.utils.json_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb,ws,tab);
  XLSX.writeFile(wb,`NSE_BTST_${{tab}}_${{new Date().toISOString().slice(0,10)}}.xlsx`);
  toast('Excel downloaded!','success');
}}
function exportCSVTab(tab){{
  const rows=getFiltered(tab);
  if(!rows.length){{toast('No data','info');return;}}
  const keys=Object.keys(rows[0]);
  const csv=[keys.join(','),...rows.map(r=>keys.map(k=>`"${{r[k]!=null?r[k]:''}}"`)
    .join(','))].join('\\n');
  const a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download=`NSE_BTST_${{tab}}.csv`;a.click();
  toast('CSV downloaded!','success');
}}

// ─── TAB BADGES ──────────────────────────────────────────────────────────────
function renderBadges(containerId, rows, type){{
  const el=document.getElementById(containerId);
  if(!el) return;
  const profit=rows.reduce((s,r)=>{{const p=parseFloat(r.PROFIT)||0;return p>0?s+p:s;}},0);
  const loss=rows.reduce((s,r)=>{{const p=parseFloat(r.PROFIT)||0;return p<0?s+p:s;}},0);
  const net=profit+loss;
  const totalInv=rows.reduce((s,r)=>s+(parseFloat(r.TOTAL_INVESTMENT)||0),0);
  let lastBadge='';
  if(type==='open'){{
    const mktVal=rows.reduce((s,r)=>{{const ltp=parseFloat(r.CURRENT_LTP)||0;const qty=parseInt(r.TOTAL_QTY)||0;return s+ltp*qty;}},0);
    lastBadge=`<span class="tbadge navy">Market Val: ₹${{fN(mktVal)}}</span>`;
  }}else{{
    const exitVal=rows.reduce((s,r)=>{{const ep=parseFloat(r.EXIT_PRICE)||0;const qty=parseInt(r.TOTAL_QTY)||0;return s+ep*qty;}},0);
    lastBadge=`<span class="tbadge navy">Exit Val: ₹${{fN(exitVal)}}</span>`;
  }}
  el.innerHTML=`
    <span class="tbadge blue">Trades: ${{rows.length}}</span>
    <span class="tbadge green">Profit: ₹${{fN(profit)}}</span>
    <span class="tbadge red">Loss: ₹${{fN(loss)}}</span>
    <span class="tbadge ${{net>=0?'green':'red'}}">Net: ₹${{fN(net)}}</span>
    <span class="tbadge amber">Total Inv: ₹${{fN(totalInv)}}</span>
    ${{lastBadge}}`;
}}

// ─── MARKET DATA SUB-TAB ──────────────────────────────────────────────────────
let mdSubFilter='all';
let mdCfg='ALL';
function mdCfgFilter(val,btn){{
  mdCfg=val;
  document.querySelectorAll('#tab-marketdata .btn-filter:not([id^="md-"])').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderMarketData();
}}
function mdSubTab(type, btn){{
  mdSubFilter=type;
  document.querySelectorAll('[id^="md-"]').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderMarketData();
}}

// ─── NEW TABS: AVG TRIGGER ────────────────────────────────────────────────────
function renderAvgTrigger(){{
  let rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open');
  if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE));
  rows=rows.filter(r=>{{
    const ltp=parseFloat(r.CURRENT_LTP)||0;
    const avg=parseFloat(r.AVG_BUY_PRICE)||0;
    return avg>0&&ltp>0&&ltp<avg*0.90;
  }}).sort((a,b)=>{{
    const da=((parseFloat(a.CURRENT_LTP)||0)-(parseFloat(a.AVG_BUY_PRICE)||0))/(parseFloat(a.AVG_BUY_PRICE)||1);
    const db=((parseFloat(b.CURRENT_LTP)||0)-(parseFloat(b.AVG_BUY_PRICE)||0))/(parseFloat(b.AVG_BUY_PRICE)||1);
    return da-db; // most dropped first
  }});
  renderBadges('avgtrigger-badges', rows, 'open');
  const body=document.getElementById('avgtrigger-body');
  document.getElementById('avgtrigger-info').textContent=`${{rows.length}} stocks triggered`;
  if(!rows.length){{body.innerHTML='<tr><td colspan="10" class="empty">No stocks triggered for averaging</td></tr>';return;}}
  body.innerHTML=rows.map((r,i)=>{{
    const avg=parseFloat(r.AVG_BUY_PRICE)||0;
    const ltp=parseFloat(r.CURRENT_LTP)||0;
    const drop=avg>0?((ltp-avg)/avg*100):0;
    const nextBuy=avg*0.85;
    const dist=ltp>0?((ltp-avg*0.90)/(avg*0.90)*100):0;
    return `<tr>
      <td>${{i+1}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td>
      <td>₹${{fN(avg)}}</td>
      <td class="red">₹${{fN(ltp)}}</td>
      <td class="red">${{drop.toFixed(2)}}%</td>
      <td style="color:#f59e0b;font-weight:700">₹${{fN(nextBuy)}}</td>
      <td class="${{dist<=0?'red':'green'}}">${{dist.toFixed(2)}}%</td>
      <td>${{fI(r.MARKET_DAYS)}}d</td>
    </tr>`;
  }}).join('');
}}

// ─── SELL TRIGGER ─────────────────────────────────────────────────────────────
function renderSellTrigger(){{
  let rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open');
  if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE));
  rows=rows.filter(r=>{{
    const ltp=parseFloat(r.CURRENT_LTP)||0;
    const tgt=parseFloat(r.TARGET_PRICE)||0;
    return tgt>0&&ltp>=tgt*0.97;
  }}).sort((a,b)=>{{
    const da=(parseFloat(a.CURRENT_LTP)||0)/(parseFloat(a.TARGET_PRICE)||1);
    const db=(parseFloat(b.CURRENT_LTP)||0)/(parseFloat(b.TARGET_PRICE)||1);
    return db-da; // closest to target first
  }});
  renderBadges('selltrigger-badges', rows, 'open');
  const body=document.getElementById('selltrigger-body');
  document.getElementById('selltrigger-info').textContent=`${{rows.length}} stocks near target`;
  if(!rows.length){{body.innerHTML='<tr><td colspan="11" class="empty">No stocks near sell trigger</td></tr>';return;}}
  body.innerHTML=rows.map((r,i)=>{{
    const avg=parseFloat(r.AVG_BUY_PRICE)||0;
    const ltp=parseFloat(r.CURRENT_LTP)||0;
    const tgt=parseFloat(r.TARGET_PRICE)||0;
    const dist=tgt>0?((tgt-ltp)/tgt*100):0;
    const pnl=parseFloat(r.PROFIT)||0;
    const pct=parseFloat(r.GAIN_PCT)||0;
    return `<tr>
      <td>${{i+1}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td>
      <td>₹${{fN(avg)}}</td>
      <td class="green">₹${{fN(ltp)}}</td>
      <td style="color:#059669;font-weight:700">₹${{fN(tgt)}}</td>
      <td class="${{dist<=2?'green':''}}">${{dist.toFixed(2)}}%</td>
      <td ${{pnlColor(r.PROFIT)}}>₹${{fN(pnl)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{pct>=0?'+':''}}${{f2(pct)}}%</td>
      <td>${{fI(r.MARKET_DAYS)}}d</td>
    </tr>`;
  }}).join('');
}}

// ─── AVG HISTORY ──────────────────────────────────────────────────────────────
let avgHistCfg='ALL', sigCfg='ALL';
function sigCfgFilter(val,btn){{
  sigCfg=val;
  document.querySelectorAll('#tab-signals .btn-filter').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderTab('signals');
}}
function avgHistCfgFilter(val,btn){{
  avgHistCfg=val;
  document.querySelectorAll('#tab-avghistory .btn-filter').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderAvgHistory();
}}
function renderAvgHistory(){{
  let rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&parseInt(r.BUY_COUNT||0)>1);
  if(avgHistCfg!=='ALL') rows=rows.filter(r=>r.CONFIG===avgHistCfg);
  if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE));
  rows.sort((a,b)=>parseInt(b.BUY_COUNT||0)-parseInt(a.BUY_COUNT||0));
  renderBadges('avghistory-badges', rows, 'closed');
  const body=document.getElementById('avghistory-body');
  document.getElementById('avghistory-info').textContent=`${{rows.length}} multi-buy trades`;
  if(!rows.length){{body.innerHTML='<tr><td colspan="11" class="empty">No multi-buy trades found</td></tr>';return;}}
  body.innerHTML=rows.map((r,i)=>{{
    const pnl=parseFloat(r.PROFIT)||0;
    const pct=parseFloat(r.GAIN_PCT)||0;
    return `<tr>
      <td>${{i+1}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td>
      <td style="font-weight:800;color:var(--blue2)">${{fI(r.BUY_COUNT)}}x</td>
      <td>₹${{fN(r.AVG_BUY_PRICE)}}</td>
      <td>₹${{fN(r.TOTAL_INVESTMENT)}}</td>
      <td>₹${{fN(r.CURRENT_LTP)}}</td>
      <td ${{pnlColor(r.PROFIT)}}>₹${{fN(pnl)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{pct>=0?'+':''}}${{f2(pct)}}%</td>
      <td>${{resultBadge(r.STATUS==='Open'?'Open':r.RESULT)}}</td>
    </tr>`;
  }}).join('');
}}

// ─── MARKET DATA ──────────────────────────────────────────────────────────────
function renderMarketData(){{
  let rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open');
  if(mdCfg!=='ALL') rows=rows.filter(r=>r.CONFIG===mdCfg);
  if(dateRangeActive) rows=rows.filter(r=>inDateRange(r.SIGNAL_DATE));
  if(mdSubFilter==='gainers') rows=rows.filter(r=>(parseFloat(r.GAIN_PCT)||0)>0);
  else if(mdSubFilter==='losers') rows=rows.filter(r=>(parseFloat(r.GAIN_PCT)||0)<0);
  rows.sort((a,b)=>(parseFloat(b.GAIN_PCT)||0)-(parseFloat(a.GAIN_PCT)||0));
  renderBadges('marketdata-badges', rows, 'open');
  const body=document.getElementById('marketdata-body');
  document.getElementById('marketdata-info').textContent=`${{rows.length}} open positions`;
  if(!rows.length){{body.innerHTML='<tr><td colspan="13" class="empty">No open positions</td></tr>';return;}}
  body.innerHTML=rows.map((r,i)=>{{
    const ltp=parseFloat(r.CURRENT_LTP)||0;
    const qty=parseInt(r.TOTAL_QTY)||0;
    const mktVal=ltp*qty;
    const pnl=parseFloat(r.PROFIT)||0;
    const pct=parseFloat(r.GAIN_PCT)||0;
    return `<tr>
      <td>${{i+1}}</td><td>${{cfgBadge(r.CONFIG)}}</td><td><strong>${{r.SYMBOL}}</strong></td>
      <td>${{fD(r.SIGNAL_DATE)}}</td>
      <td>₹${{fN(r.AVG_BUY_PRICE)}}</td>
      <td class="${{pct>=0?'green':'red'}}">₹${{fN(ltp)}}</td>
      <td ${{pnlColor(r.PROFIT)}}>₹${{fN(pnl)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{pct>=0?'+':''}}${{f2(pct)}}%</td>
      <td>₹${{fN(r.TARGET_PRICE)}}</td>
      <td>₹${{fN(r.STOP_PRICE)}}</td>
      <td>₹${{fN(r.TOTAL_INVESTMENT)}}</td>
      <td>₹${{fN(mktVal)}}</td>
      <td>${{fI(r.MARKET_DAYS)}}d</td>
    </tr>`;
  }}).join('');
}}

// ─── PERFORMANCE ──────────────────────────────────────────────────────────────
let perfCfg='ALL';
function perfCfgFilter(val,btn){{
  perfCfg=val;
  document.querySelectorAll('#tab-performance .btn-filter').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderPerformance();
}}
function renderPerformance(){{
  const allCfgIds=['C1','C2','C3','C4'];
  const cfgIds=perfCfg==='ALL'?allCfgIds:[perfCfg];
  let closed=ALL_ROWS.filter(r=>r.STATUS==='Closed'&&r.RESULT&&!r.RESULT.includes('FE'));
  let open=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open');
  if(perfCfg!=='ALL'){{ closed=closed.filter(r=>r.CONFIG===perfCfg); open=open.filter(r=>r.CONFIG===perfCfg); }}
  if(dateRangeActive){{
    closed=closed.filter(r=>inDateRange(r.SIGNAL_DATE));
    open=open.filter(r=>inDateRange(r.SIGNAL_DATE));
  }}

  // Overall KPIs
  const allExec=[...closed,...open];
  const totalProfit=allExec.reduce((s,r)=>{{const p=parseFloat(r.PROFIT)||0;return p>0?s+p:s;}},0);
  const totalLoss=Math.abs(allExec.reduce((s,r)=>{{const p=parseFloat(r.PROFIT)||0;return p<0?s+p:s;}},0));
  const netPnl=totalProfit-totalLoss;
  const wins=allExec.filter(r=>(parseFloat(r.PROFIT)||0)>0).length;
  const wr=allExec.length>0?(wins/allExec.length*100):0;
  const durations=closed.map(r=>parseInt(r.MARKET_DAYS)||0).filter(d=>d>0);
  const avgDur=durations.length?durations.reduce((a,b)=>a+b,0)/durations.length:0;

  document.getElementById('perf-hero').innerHTML=`
    <div class="phc ${{netPnl>=0?'pos':'neg'}}"><div class="phc-label">Combined Net P&amp;L</div><div class="phc-value">₹${{fN(netPnl)}}</div><div class="phc-sub">${{allExec.length}} total trades</div></div>
    <div class="phc pos"><div class="phc-label">Total Win Amount</div><div class="phc-value">₹${{fN(totalProfit)}}</div><div class="phc-sub">${{wins}} wins</div></div>
    <div class="phc neg"><div class="phc-label">Total Loss Amount</div><div class="phc-value">₹${{fN(totalLoss)}}</div><div class="phc-sub">${{allExec.filter(r=>(parseFloat(r.PROFIT)||0)<0).length}} losses</div></div>
    <div class="phc ${{wr>=50?'pos':'neg'}}"><div class="phc-label">Win Rate</div><div class="phc-value">${{wr.toFixed(1)}}%</div><div class="phc-sub">${{wins}}/${{allExec.length}}</div></div>
    <div class="phc"><div class="phc-label">Avg Hold Duration</div><div class="phc-value">${{Math.round(avgDur)}}d</div><div class="phc-sub">closed trades</div></div>`;

  // Per-config closed breakdown
  document.getElementById('perf-closed-body').innerHTML=cfgIds.map(cid=>{{
    const crows=closed.filter(r=>r.CONFIG===cid);
    const cWins=crows.filter(r=>(parseFloat(r.PROFIT)||0)>0);
    const cLoss=crows.filter(r=>(parseFloat(r.PROFIT)||0)<0);
    const winAmt=cWins.reduce((s,r)=>s+(parseFloat(r.PROFIT)||0),0);
    const lossAmt=Math.abs(cLoss.reduce((s,r)=>s+(parseFloat(r.PROFIT)||0),0));
    const pFactor=lossAmt>0?(winAmt/lossAmt):winAmt>0?99:0;
    const net=winAmt-lossAmt;
    const wr=crows.length>0?(cWins.length/crows.length*100):0;
    const avgGain=cWins.length?winAmt/cWins.length:0;
    const avgLoss=cLoss.length?lossAmt/cLoss.length:0;
    return `<tr>
      <td>${{cfgBadge(cid)}}</td><td>${{crows.length}}</td>
      <td class="green">${{cWins.length}}</td><td class="red">${{cLoss.length}}</td>
      <td class="${{wr>=50?'green':'red'}}">${{wr.toFixed(1)}}%</td>
      <td class="green">₹${{fN(avgGain)}}</td><td class="red">₹${{fN(avgLoss)}}</td>
      <td class="${{pFactor>=1?'green':'red'}}">${{pFactor.toFixed(2)}}</td>
      <td ${{pnlColor(net)}}>₹${{fN(net)}}</td>
    </tr>`;
  }}).join('');

  // Open trades breakdown per config
  document.getElementById('perf-open-body').innerHTML=allCfgIds.map(cid=>{{
    const orows=open.filter(r=>r.CONFIG===cid);
    const oInv=orows.reduce((s,r)=>s+(parseFloat(r.TOTAL_INVESTMENT)||0),0);
    const oMkt=orows.reduce((s,r)=>s+(parseFloat(r.CURRENT_LTP)||0)*(parseInt(r.TOTAL_QTY)||0),0);
    const oPnl=orows.reduce((s,r)=>s+(parseFloat(r.PROFIT)||0),0);
    const oPct=oInv>0?(oPnl/oInv*100):0;
    return `<tr>
      <td>${{cfgBadge(cid)}}</td><td>${{orows.length}}</td>
      <td>&#8377;${{fN(oInv)}}</td>
      <td>&#8377;${{fN(oMkt)}}</td>
      <td ${{pnlColor(oPnl)}}>&#8377;${{fN(oPnl)}}</td>
      <td ${{pnlColor(oPct)}}>${{oPct>=0?'+':''}}${{f2(oPct)}}%</td>
    </tr>`;
  }}).join('');

  // Top stocks by P&L
  const symMap={{}};
  allExec.forEach(r=>{{
    const s=r.SYMBOL||'?';
    if(!symMap[s]) symMap[s]={{sym:s,trades:0,pnl:0,wins:0}};
    symMap[s].trades++;
    const p=parseFloat(r.PROFIT)||0;
    symMap[s].pnl+=p;
    if(p>0)symMap[s].wins++;
  }});
  const syms=Object.values(symMap);
  const topProfit=[...syms].sort((a,b)=>b.pnl-a.pnl).slice(0,10);
  const topLoss=[...syms].sort((a,b)=>a.pnl-b.pnl).slice(0,10);
  const mkRow=r=>`<tr>
    <td><strong>${{r.sym}}</strong></td><td>${{r.trades}}</td>
    <td ${{pnlColor(r.pnl)}}>₹${{fN(r.pnl)}}</td>
    <td class="${{r.trades>0&&(r.wins/r.trades*100)>=50?'green':'red'}}">${{r.trades>0?(r.wins/r.trades*100).toFixed(0):'0'}}%</td>
  </tr>`;
  document.getElementById('perf-top-profit').innerHTML=topProfit.map(mkRow).join('');
  document.getElementById('perf-top-loss').innerHTML=topLoss.map(mkRow).join('');
}}

// ─── STOCK DETAIL MODAL ───────────────────────────────────────────────────────
function openStockDetail(key){{
  const [kCfg,sym]=key.includes('|')?key.split('|',2):[null,key];
  const rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.SYMBOL===sym&&(!kCfg||r.CONFIG===kCfg));
  document.getElementById('sdm-title').textContent=`📊 Stock History: ${{kCfg?kCfg+' — ':''}}${{sym}}`;
  const modal=document.getElementById('stockDetailModal');
  modal.classList.add('open');
  document.body.style.overflow='hidden';
  
  const profit=rows.reduce((s,r)=>{{const p=parseFloat(r.PROFIT)||0;return p>0?s+p:s;}},0);
  const loss=rows.reduce((s,r)=>{{const p=parseFloat(r.PROFIT)||0;return p<0?s+p:s;}},0);
  const net=profit+loss;
  const wins=rows.filter(r=>(parseFloat(r.PROFIT)||0)>0).length;
  document.getElementById('sdm-badges').innerHTML=`
    <span class="tbadge blue">Trades: ${{rows.length}}</span>
    <span class="tbadge green">Wins: ${{wins}}</span>
    <span class="tbadge red">Losses: ${{rows.length-wins}}</span>
    <span class="tbadge ${{net>=0?'green':'red'}}">Net P&amp;L: ₹${{fN(net)}}</span>`;
  
  document.getElementById('sdm-body').innerHTML=rows.length?rows.map(r=>{{
    const pnl=parseFloat(r.PROFIT)||0;
    const pct=parseFloat(r.GAIN_PCT)||0;
    const oKey=`${{r.SYMBOL}}_${{r.SIGNAL_DATE}}_${{r.CONFIG}}`;
    const hasOHLC=TRADE_OHLC[oKey]&&TRADE_OHLC[oKey].length>0;
    return `<tr>
      <td>${{cfgBadge(r.CONFIG)}}</td>
      <td>${{fD(r.SIGNAL_DATE)}}</td>
      <td>₹${{fN(r.AVG_BUY_PRICE)}}</td>
      <td>₹${{fN(r.EXIT_PRICE)}}</td>
      <td ${{pnlColor(r.PROFIT)}}>₹${{fN(pnl)}}</td>
      <td ${{pnlColor(r.GAIN_PCT)}}>${{pct>=0?'+':''}}${{f2(pct)}}%</td>
      <td>${{resultBadge(r.STATUS==='Open'?'Open':r.RESULT)}}</td>
      <td>${{fI(r.MARKET_DAYS)}}d</td>
      <td>${{resultBadge(r.RESULT)}}</td>
      <td>${{hasOHLC?`<button onclick="showOHLC('${{oKey}}','${{r.SYMBOL}} (${{r.CONFIG}})')" style="font-size:11px;padding:2px 8px;border:1px solid #2563eb;border-radius:6px;cursor:pointer;background:#eff6ff;color:#2563eb;">📈 OHLC</button>`:'—'}}</td>
    </tr>`;
  }}).join(''):'<tr><td colspan="10" class="empty">No trades found</td></tr>';
}}
function closeStockDetail(){{
  document.getElementById('stockDetailModal').classList.remove('open');
  document.body.style.overflow='';
}}
function showOHLC(key, label){{
  const data=TRADE_OHLC[key]||[];
  document.getElementById('sdm-ohlc-title').textContent=`📈 OHLC Prices — ${{label}} (${{data.length}} days)`;
  const panel=document.getElementById('sdm-ohlc-panel');
  panel.style.display='block';
  if(!data.length){{document.getElementById('sdm-ohlc-body').innerHTML='<tr><td colspan="6" class="empty">No OHLC data</td></tr>';return;}}
  document.getElementById('sdm-ohlc-body').innerHTML=data.map(d=>{{
    const chg=parseFloat(d.chg)||0;
    return `<tr>
      <td>${{d.date}}</td>
      <td>&#8377;${{fN(d.o)}}</td>
      <td style="color:#059669">&#8377;${{fN(d.h)}}</td>
      <td style="color:#dc2626">&#8377;${{fN(d.l)}}</td>
      <td><strong>&#8377;${{fN(d.c)}}</strong></td>
      <td ${{pnlColor(chg)}}>${{chg>=0?'+':''}}${{f2(chg)}}%</td>
    </tr>`;
  }}).join('');
}}

// ─── EXPORT CSV FOR NEW TABS ──────────────────────────────────────────────────
function exportTabCSV(tab){{
  let rows=[];
  if(tab==='avgtrigger') rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open'&&(parseFloat(r.CURRENT_LTP)||0)<(parseFloat(r.AVG_BUY_PRICE)||0)*0.90);
  else if(tab==='selltrigger') rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open'&&(parseFloat(r.CURRENT_LTP)||0)>=(parseFloat(r.TARGET_PRICE)||0)*0.97);
  else if(tab==='avghistory') rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&parseInt(r.BUY_COUNT||0)>1);
  else if(tab==='marketdata') rows=ALL_ROWS.filter(r=>r.ORDER==='Executed'&&r.STATUS==='Open');
  if(!rows.length){{toast('No data to export','info');return;}}
  const keys=Object.keys(rows[0]);
  const csv=[keys.join(','),...rows.map(r=>keys.map(k=>`"${{r[k]!=null?r[k]:''}}"`)
    .join(','))].join('\\n');
  const a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download=`NSE_BTST_${{tab}}_${{new Date().toISOString().slice(0,10)}}.csv`;a.click();
  toast('CSV downloaded!','success');
}}

// ─── TOAST ───────────────────────────────────────────────────────────────────
function toast(msg,type='info'){{
  const el=document.createElement('div');
  el.className=`toast ${{type}}`;el.textContent=msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(()=>{{el.style.animation='fadeOut .4s forwards';setTimeout(()=>el.remove(),400);}},2500);
}}

// ─── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('keydown', e=>{{ if(e.key==='Escape') closeStockDetail(); }});
buildOverview();
</script>
</body>
</html>"""


def main():
    logo    = load_logo()
    nifty   = load_nifty()
    configs = load_configs()
    sim_meta, sim_results, gen_at = load_sim()
    signals_rows, sig_date = load_signals_csv()

    html = build_html(logo, nifty, configs, sim_meta, sim_results, signals_rows, sig_date)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)

    total_rows = sum(len(v) for v in sim_results.values())
    print(f"Dashboard written → {OUT}")
    print(f"  Sim rows : {total_rows} (across {len(sim_results)} configs)")
    print(f"  Signals  : {len(signals_rows)} (date: {sig_date})")
    print(f"  Generated: {gen_at or datetime.now(tz=IST).strftime('%d-%b-%Y %H:%M IST')}")


if __name__ == '__main__':
    main()
