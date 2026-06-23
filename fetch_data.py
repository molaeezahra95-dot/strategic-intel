# pip install yfinance pandas

import yfinance as yf
import json
import math
from datetime import datetime, timedelta


# ---- safe float conversion ----
def sf(val, d=2):
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, d)
    except:
        return None


# ---- company list by wave ----
WAVES = {
    "ai": [
        ("NVDA",  "NVIDIA Corporation",     "Semiconductors"),
        ("TSM",   "Taiwan Semiconductor",   "Foundry"),
        ("ASML",  "ASML Holding NV",        "Semiconductor Equip."),
        ("ARM",   "Arm Holdings PLC",       "Semiconductor IP"),
        ("MSFT",  "Microsoft Corporation",  "Cloud/Software"),
        ("GOOGL", "Alphabet Inc.",          "Internet Services"),
        ("META",  "Meta Platforms",         "Social Media"),
        ("AMZN",  "Amazon.com Inc.",        "Cloud/E-commerce"),
        ("AVGO",  "Broadcom Inc.",          "Semiconductors"),
        ("PLTR",  "Palantir Technologies",  "Data Analytics"),
    ],
    "energy": [
        ("2222.SR", "Saudi Aramco",         "Oil & Gas"),
        ("CEG",     "Constellation Energy", "Nuclear Power"),
        ("RIO",     "Rio Tinto Group",      "Mining"),
        ("DE",      "Deere & Company",      "Machinery"),
    ],
    "bio": [
        ("NVO",  "Novo Nordisk A/S",      "Pharmaceuticals"),
        ("LLY",  "Eli Lilly",            "Pharmaceuticals"),
        ("CRSP", "CRISPR Therapeutics",  "Biotech"),
    ],
    "markets": [
        ("V",            "Visa Inc.",          "Payments"),
        ("BLK",          "BlackRock Inc.",     "Asset Management"),
        ("JPM",          "JPMorgan Chase",     "Banking"),
        ("MELI",         "MercadoLibre Inc.", "E-commerce/Fintech"),
        ("RELIANCE.NS",  "Reliance Industries","Conglomerate"),
    ],
    "defense": [
        ("LMT",   "Lockheed Martin",       "Defense"),
        ("RHM.DE","Rheinmetall AG",        "Defense"),
        ("CRWD",  "CrowdStrike Holdings",  "Cybersecurity"),
        ("TSLA",  "Tesla Inc.",            "EV/Energy"),
        ("BYDDY", "BYD Company",           "EV/Battery"),
        ("CAT",   "Caterpillar Inc.",      "Heavy Equipment"),
    ],
}


def quarter_label(ts):
    q = (ts.month - 1) // 3 + 1
    return f"Q{q} {ts.year}"


def fetch_one(sym, name, wave, industry):
    print(f"  {sym}...", end=" ", flush=True)
    try:
        t = yf.Ticker(sym)
        info = t.info or {}

        price = sf(
            info.get("currentPrice") or
            info.get("regularMarketPrice") or
            info.get("previousClose")
        )
        pe = sf(info.get("trailingPE"))

        quarters, spark = [], []

        fin = t.quarterly_income_stmt
        if fin is not None and not fin.empty:
            rev_row = None
            for lbl in ["Total Revenue", "Revenue"]:
                if lbl in fin.index:
                    rev_row = fin.loc[lbl]
                    break

            if rev_row is not None:
                cols = sorted(rev_row.index, reverse=True)

                # spark: last 8 quarters, oldest to newest, in $B
                for c in reversed(cols[:8]):
                    v = sf((rev_row.get(c) or 0) / 1e9, 1)
                    if v is not None:
                        spark.append(v)

                # table: last 4 quarters
                for col in cols[:4]:
                    rev_b = sf((rev_row.get(col) or 0) / 1e9, 2)
                    yoy = None
                    target = col - timedelta(days=365)
                    for other in cols:
                        if abs((other - target).days) < 46:
                            prev = rev_row.get(other)
                            curr = rev_row.get(col)
                            if prev and curr and float(prev) != 0:
                                try:
                                    yoy = round(
                                        (float(curr) - float(prev)) / abs(float(prev)) * 100
                                    )
                                except:
                                    pass
                            break
                    quarters.append({
                        "label":   quarter_label(col),
                        "revenue": rev_b,
                        "eps":     None,
                        "yoy":     yoy,
                    })

        # EPS from quarterly_earnings
        try:
            earn = t.quarterly_earnings
            if earn is not None and not earn.empty:
                eps_col = next(
                    (c for c in earn.columns if "Earnings" in c and "Share" in c), None
                )
                if eps_col:
                    for q in quarters:
                        for idx in earn.index:
                            if q["label"] in str(idx) or str(idx) in q["label"]:
                                q["eps"] = sf(earn.loc[idx, eps_col])
                                break
        except:
            pass

        # fallback EPS for latest quarter only
        if quarters and quarters[0]["eps"] is None:
            quarters[0]["eps"] = sf(info.get("trailingEps"))

        print("OK")
        return {
            "sym":      sym,
            "name":     name,
            "wave":     wave,
            "price":    price,
            "ttm_pe":   pe,
            "industry": industry,
            "quarters": quarters,
            "spark":    spark,
        }

    except Exception as e:
        print(f"FAILED: {e}")
        return None


def main():
    companies = []
    for wave, items in WAVES.items():
        print(f"\n[{wave.upper()}]")
        for sym, name, industry in items:
            co = fetch_one(sym, name, wave, industry)
            if co:
                companies.append(co)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    out = {"generated": now, "companies": companies}

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\ndata.json saved — {len(companies)} companies — {now}")


if __name__ == "__main__":
    main()
