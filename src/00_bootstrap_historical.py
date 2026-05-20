"""
Bootstrap Historical Bhavcopy Data
=====================================
Downloads the past 12 months of NSE bhavcopy files.
Run this ONCE manually to seed historical data for accurate ATH computation.
Skips files that already exist.

Usage: python src/00_bootstrap_historical.py
"""

import os, glob, time, requests
from datetime import datetime, timedelta, timezone

IST      = timezone(timedelta(hours=5, minutes=30))
NOW_IST  = datetime.now(tz=IST)
BHAV_ROOT = "bhav_data"
MONTHS_BACK = 14  # how many months of history to download


def get_session():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.nseindia.com",
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    session = requests.Session()
    print("Getting NSE session cookies...")
    session.get("https://www.nseindia.com", headers=headers, timeout=20)
    return session, headers


def download_one(session, headers, dt):
    dd   = dt.strftime("%d")
    mm   = dt.strftime("%m")
    yyyy = dt.strftime("%Y")
    fname    = f"sec_bhavdata_full_{dd}{mm}{yyyy}.csv"
    savepath = os.path.join(BHAV_ROOT, fname)

    if os.path.exists(savepath):
        return "skip"

    url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{dd}{mm}{yyyy}.csv"
    try:
        resp = session.get(url, headers=headers, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(savepath, "wb") as f:
                f.write(resp.content)
            return "ok"
        else:
            return "skip"  # weekend / holiday / not published
    except Exception as e:
        print(f"  Error {dt.date()}: {e}")
        return "err"


def main():
    os.makedirs(BHAV_ROOT, exist_ok=True)

    start_date = NOW_IST - timedelta(days=MONTHS_BACK * 30)
    end_date   = NOW_IST - timedelta(days=1)

    print(f"Bootstrapping bhav data: {start_date.date()} \u2192 {end_date.date()}")
    print(f"Target folder: {BHAV_ROOT}/")

    session, headers = get_session()
    downloaded = 0
    skipped    = 0
    errors     = 0

    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Mon\u2013Fri only
            result = download_one(session, headers, current)
            if result == "ok":
                print(f"  \u2705 {current.strftime('%d-%b-%Y')}")
                downloaded += 1
                # Refresh session every 50 downloads to avoid cookie expiry
                if downloaded % 50 == 0:
                    session, headers = get_session()
                time.sleep(0.3)
            elif result == "skip":
                skipped += 1
            else:
                errors += 1
        current += timedelta(days=1)

    print(f"\n\u2705 Bootstrap complete.")
    print(f"   Downloaded : {downloaded}")
    print(f"   Skipped    : {skipped} (weekends/holidays/existing)")
    print(f"   Errors     : {errors}")


if __name__ == "__main__":
    main()
