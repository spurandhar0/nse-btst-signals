"""
Script 4: Run Daily BTST Signals
===================================
Reads: db/eq_data.parquet, db/ath.parquet, config/params.json

For each of the 4 fixed configs, checks if stocks match filter criteria
AS OF THE LATEST DATE in the data. Deduplicates by SYMBOL.

Output:
  output/signals_latest.csv       - always overwritten with today's results
  output/signals_DDMMYYYY.csv     - archive copy
  output/meta.json                - metadata for dashboard
"""

import os, json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

CONFIG_FILE = "config/params.json"
EQ_FILE     = "db/eq_data.parquet"
ATH_FILE    = "db/ath.parquet"
OUTPUT_DIR  = "output"

IST = timezone(timedelta(hours=5, minutes=30))


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def check_signal(sym_df, ath_price, cfg):
    days_back = cfg["days_back"]
    pct_min   = cfg["pct_min"]
    pct_max   = cfg["pct_max"]
    ath_min   = cfg["ath_min"]
    ath_max   = cfg["ath_max"]

    arr    = sym_df[["DATE1", "CLOSE_PRICE", "LOW_PRICE"]].values
    dates  = arr[:, 0]
    closes = arr[:, 1].astype(float)
    lows   = arr[:, 2].astype(float)
    n      = len(dates)

    if n < days_back + 1:
        return None

    i = n - 1
    today_close = closes[i]
    if today_close <= 0:
        return None

    lookback_lows = lows[i - days_back: i]
    if len(lookback_lows) < days_back:
        return None
    min_low = float(np.min(lookback_lows))
    if min_low <= 0:
        return None
    pct_from_low = (today_close - min_low) / min_low

    if not (pct_min <= pct_from_low <= pct_max):
        return None

    pct_from_ath = (today_close - ath_price) / ath_price
    if not (ath_min <= pct_from_ath <= ath_max):
        return None

    prev_close = closes[i - 1] if i > 0 else 0.0
    pct_1d = ((today_close - prev_close) / prev_close) if prev_close > 0 else 0.0

    return {
        "SIGNAL_DATE":    dates[i],
        "CLOSE":          round(float(today_close), 2),
        "PREV_CLOSE":     round(float(prev_close), 2),
        "ATH_PRICE":      round(float(ath_price), 2),
        "MIN_LOW":        round(min_low, 2),
        "PCT_FROM_LOW":   round(pct_from_low * 100, 2),
        "PCT_FROM_ATH":   round(pct_from_ath * 100, 2),
        "PCT_1D_CHANGE":  round(pct_1d * 100, 2),
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for f in [CONFIG_FILE, EQ_FILE, ATH_FILE]:
        if not os.path.exists(f):
            print(f"\u274c Missing: {f}")
            raise SystemExit(1)

    cfg = load_config()
    configs = cfg["configs"]
    watch_syms = set(s.strip().upper() for s in cfg.get("watch_symbols", []) if s.strip())

    print(f"Loaded {len(configs)} configs:")
    for c in configs:
        print(f"  {c['id']}: days_back={c['days_back']}  pct=[{c['pct_min']},{c['pct_max']}]  ath=[{c['ath_min']},{c['ath_max']}]")

    print("\nLoading EQ data...")
    eq = pd.read_parquet(EQ_FILE, columns=["SYMBOL", "DATE1", "CLOSE_PRICE", "LOW_PRICE"])
    eq["DATE1"] = pd.to_datetime(eq["DATE1"])
    eq.sort_values(["SYMBOL", "DATE1"], inplace=True)

    if watch_syms:
        eq = eq[eq["SYMBOL"].isin(watch_syms)]
        print(f"Filtered to {len(watch_syms)} watch symbols")

    print("Loading ATH data...")
    ath_df  = pd.read_parquet(ATH_FILE, columns=["SYMBOL", "ATH_PRICE"])
    ath_map = dict(zip(ath_df["SYMBOL"], ath_df["ATH_PRICE"]))

    latest_date = eq["DATE1"].max()
    print(f"Latest data date: {latest_date.date()}")

    symbols = eq["SYMBOL"].unique()
    print(f"Scanning {len(symbols):,} symbols x {len(configs)} configs...\n")

    results = {}

    for sym_idx, sym in enumerate(symbols):
        if (sym_idx + 1) % 1000 == 0:
            print(f"  [{sym_idx+1}/{len(symbols)}] matched so far: {len(results)}")

        ath_price = ath_map.get(sym, 0)
        if ath_price <= 0:
            continue

        sym_df = eq[eq["SYMBOL"] == sym].reset_index(drop=True)

        if sym_df["DATE1"].iloc[-1] != latest_date:
            continue

        matched_configs = []
        signal_data     = None

        for c in configs:
            result = check_signal(sym_df, ath_price, c)
            if result is not None:
                matched_configs.append(c["id"])
                if signal_data is None:
                    signal_data = result

        if matched_configs and signal_data:
            results[sym] = {
                "SYMBOL":          sym,
                "SIGNAL_DATE":     latest_date.strftime("%Y-%m-%d"),
                "CLOSE":           signal_data["CLOSE"],
                "PREV_CLOSE":      signal_data["PREV_CLOSE"],
                "ATH_PRICE":       signal_data["ATH_PRICE"],
                "MIN_LOW_10D":     signal_data["MIN_LOW"],
                "PCT_FROM_LOW":    signal_data["PCT_FROM_LOW"],
                "PCT_FROM_ATH":    signal_data["PCT_FROM_ATH"],
                "PCT_1D_CHANGE":   signal_data["PCT_1D_CHANGE"],
                "CONFIGS_MATCHED": ",".join(matched_configs),
                "CONFIG_COUNT":    len(matched_configs),
            }

    rows = sorted(results.values(), key=lambda x: (-x["CONFIG_COUNT"], x["SYMBOL"]))
    print(f"\n\u2705 {len(rows)} unique symbols matched")

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "SYMBOL", "SIGNAL_DATE", "CLOSE", "PREV_CLOSE", "ATH_PRICE",
        "MIN_LOW_10D", "PCT_FROM_LOW", "PCT_FROM_ATH", "PCT_1D_CHANGE",
        "CONFIGS_MATCHED", "CONFIG_COUNT"
    ])

    date_str = latest_date.strftime("%d%m%Y")
    df.to_csv(f"{OUTPUT_DIR}/signals_{date_str}.csv", index=False)
    df.to_csv(f"{OUTPUT_DIR}/signals_latest.csv", index=False)
    print(f"\u2705 Saved output/signals_latest.csv")
    print(f"\u2705 Saved output/signals_{date_str}.csv")

    config_breakdown = {}
    for c in configs:
        cid = c["id"]
        count = sum(1 for r in rows if cid in r["CONFIGS_MATCHED"].split(","))
        config_breakdown[cid] = count

    meta = {
        "generated_at":   datetime.now(tz=IST).strftime("%d-%b-%Y %H:%M IST"),
        "signal_date":    latest_date.strftime("%d-%b-%Y"),
        "total_signals":  len(rows),
        "config_breakdown": config_breakdown,
        "configs": configs,
    }
    with open(f"{OUTPUT_DIR}/meta.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)
    print(f"\u2705 Saved output/meta.json")

    print(f"\n{'='*60}")
    print(f"SIGNAL SUMMARY - {latest_date.strftime('%d-%b-%Y')}")
    print(f"{'='*60}")
    print(f"Total signals : {len(rows)}")
    for cid, cnt in config_breakdown.items():
        print(f"  {cid}          : {cnt}")
    if rows:
        print(f"\nTop signals:")
        for r in rows[:10]:
            print(f"  {r['SYMBOL']:15s} close={r['CLOSE']:8.2f}  "
                  f"pct_low={r['PCT_FROM_LOW']:+.1f}%  "
                  f"pct_ath={r['PCT_FROM_ATH']:+.1f}%  "
                  f"configs={r['CONFIGS_MATCHED']}")


if __name__ == "__main__":
    main()
