"""
Script 1: Consolidate NSE Bhavcopy CSVs
========================================
Reads all CSV files from bhav_data/**/*.csv
Merges into a single Parquet file: db/consolidated.parquet

If no CSV files are found but consolidated.parquet already exists,
skips consolidation (allows re-runs after cleanup step removes raw CSVs).
"""

import os, glob
import pandas as pd
from datetime import datetime

BHAV_DIR    = "bhav_data"
OUTPUT_DIR  = "db"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "consolidated.parquet")

REQUIRED_COLS = [
    "SYMBOL", "SERIES", "DATE1", "PREV_CLOSE", "OPEN_PRICE",
    "HIGH_PRICE", "LOW_PRICE", "LAST_PRICE", "CLOSE_PRICE",
    "AVG_PRICE", "TTL_TRD_QNTY", "TURNOVER_LACS",
    "NO_OF_TRADES", "DELIV_QTY", "DELIV_PER"
]


def parse_date(val):
    if pd.isna(val):
        return pd.NaT
    s = str(val).strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return pd.NaT


def extract_file_date(filepath):
    name = os.path.splitext(os.path.basename(filepath))[0]
    if len(name) >= 8:
        date_str = name[-8:]
        try:
            return datetime.strptime(date_str, "%d%m%Y")
        except ValueError:
            pass
    return datetime.min


def load_csv(filepath):
    try:
        df = pd.read_csv(filepath, dtype=str, low_memory=False)
        df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
        rename_map = {
            "DATE": "DATE1",
            "TOTTRDQTY": "TTL_TRD_QNTY",
            "TOTTRDVAL": "TURNOVER_LACS",
            "TOTALTRADES": "NO_OF_TRADES",
        }
        df.rename(columns=rename_map, inplace=True)
        for col in REQUIRED_COLS:
            if col not in df.columns:
                df[col] = ""
        df = df[REQUIRED_COLS].copy()
        df["SYMBOL"] = df["SYMBOL"].str.strip().str.upper()
        df["SERIES"] = df["SERIES"].str.strip().str.upper()
        df["DATE1"]  = df["DATE1"].apply(parse_date)
        df = df.dropna(subset=["DATE1", "SYMBOL"])
        df = df[df["SYMBOL"] != ""]
        num_cols = ["PREV_CLOSE", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE",
                    "LAST_PRICE", "CLOSE_PRICE", "AVG_PRICE",
                    "TTL_TRD_QNTY", "TURNOVER_LACS", "NO_OF_TRADES",
                    "DELIV_QTY", "DELIV_PER"]
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception as e:
        print(f"  \u26a0\ufe0f  Skipped {filepath}: {e}")
        return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    csv_files = glob.glob(os.path.join(BHAV_DIR, "**", "*.csv"), recursive=True)
    print(f"Found {len(csv_files)} CSV files in {BHAV_DIR}/")

    if not csv_files:
        if os.path.exists(OUTPUT_FILE):
            print("\u26a0\ufe0f  No CSV files found, but consolidated.parquet already exists — skipping consolidation.")
            print("\u2705 Using existing consolidated.parquet")
            return
        else:
            print("\u274c No CSV files found and no consolidated.parquet exists. Cannot continue.")
            raise SystemExit(1)

    csv_files = sorted(csv_files, key=extract_file_date)

    seen_dates = {}
    unique_files = []
    for f in csv_files:
        d = extract_file_date(f)
        key = d.strftime("%Y%m%d") if d != datetime.min else f
        if key not in seen_dates:
            seen_dates[key] = f
            unique_files.append(f)

    csv_files = unique_files
    print(f"Unique date files: {len(csv_files)}")

    parseable = [extract_file_date(f) for f in csv_files if extract_file_date(f) != datetime.min]
    if parseable:
        print(f"Date range: {min(parseable).strftime('%d-%b-%Y')} \u2192 {max(parseable).strftime('%d-%b-%Y')}")

    frames = []
    for i, f in enumerate(csv_files, 1):
        d = extract_file_date(f)
        label = d.strftime("%d-%b-%Y") if d != datetime.min else "?"
        if i % 50 == 0 or i == len(csv_files):
            print(f"  [{i:3d}/{len(csv_files)}] {label}")
        df = load_csv(f)
        if df is not None and len(df) > 0:
            frames.append(df)

    if not frames:
        print("\u274c No valid data loaded.")
        raise SystemExit(1)

    combined = pd.concat(frames, ignore_index=True)
    before = len(combined)
    combined.drop_duplicates(subset=["SYMBOL", "DATE1"], keep="last", inplace=True)
    after = len(combined)
    print(f"Deduplication: {before:,} \u2192 {after:,} rows")

    combined.sort_values(["SYMBOL", "DATE1"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    combined.to_parquet(OUTPUT_FILE, index=False)

    print(f"\u2705 Consolidated: {after:,} rows | {combined['SYMBOL'].nunique():,} symbols")
    print(f"\u2705 Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
