# pip install yfinance pandas

import yfinance as yf
import json
import math
from datetime import datetime, timedelta, timezone


def sf(val, d=2):
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, d)
    except:
        return None


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
        ("NVO",  "Novo Nordisk A/S",     "Pharmaceuticals"),
        ("LLY",  "Eli Lilly",           "Pharmaceuticals"),
        ("CRSP", "CRISPR Therapeutics", "Biotech"),
    ],
    "markets": [
        ("V",           "Visa Inc.",          "Payments"),
        ("BLK",         "BlackRock Inc.",     "Asset Management"),
        ("JPM",         "JPMorgan Chase",     "Banking"),
        ("MELI",        "MercadoLibre Inc.", "E-commerce/Fintech"),
        ("RELIANCE.NS", "Reliance Industries","Conglomerate"),
    ],
    "defense": [
        ("LMT",   "Lockheed Martin",      "Defense"),
        ("RHM.DE","Rheinmetall AG",       "Defense"),
        ("CRWD",  "CrowdStrike Holdings", "Cybersecurity"),
        ("TSLA",  "Tesla Inc.",           "EV/Energy"),
        ("BYDDY", "BYD Company",          "EV/Battery"),
        ("CAT",   "Caterpillar Inc.",     "Heavy Equipment"),
    ],
}


def quarter_label(ts):
    q = (ts.month - 1) // 3 + 1
    return f"Q{q} {ts.year}"


def get_row(df, labels):
    """Find first matching row label in a DataFrame."""
    for lbl in labels:
        if lbl in df.index:
            return df.loc[lbl]
    return None


def build_annual_yoy(ticker):
    """Return {year: yoy_pct} from annual income statement."""
    result = {}
    try:
        ann = ticker.income_stmt
        if ann is None or ann.empty:
            return result
        rev = get_row(ann, ["Total Revenue", "Revenue"])
        if rev is None:
            return result
        cols = sorted(rev.index, reverse=True)
        for i in range(len(cols) - 1):
            c, p = cols[i], cols[i + 1]
            cv = float(rev.get(c) or 0)
            pv = float(rev.get(p) or 0)
            if pv != 0 and not math.isnan(cv) and not math.isnan(pv):
                result[c.year] = round((cv - pv) / abs(pv) * 100)
    except Exception:
        pass
    return result


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
        if fin is None or fin.empty:
            print("no data")
            return {"sym": sym, "name": name, "wave": wave,
                    "price": price, "ttm_pe": pe, "industry": industry,
                    "quarters": [], "spark": []}

        rev_row    = get_row(fin, ["Total Revenue", "Revenue"])
        ni_row     = get_row(fin, ["Net Income", "Net Income Common Stockholders",
                                    "Net Income Including Noncontrolling Interests"])
        shares_row = get_row(fin, ["Diluted Average Shares", "Basic Average Shares",
                                    "Ordinary Shares Number"])

        # Annual YoY as fallback for quarters without prior-year quarter data
        annual_yoy = build_annual_yoy(t)

        if rev_row is not None:
            cols = sorted(rev_row.index, reverse=True)

            # Spark: last 8 quarters oldest → newest
            for c in reversed(cols[:8]):
                v = sf((rev_row.get(c) or 0) / 1e9, 1)
                if v is not None:
                    spark.append(v)

            # Table: last 4 quarters
            for col in cols[:4]:
                rev_b = sf((rev_row.get(col) or 0) / 1e9, 2)

                # --- YoY: exact quarterly first ---
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
                            except Exception:
                                pass
                        break

                # --- YoY fallback: annual rate for that calendar year ---
                if yoy is None:
                    yoy = annual_yoy.get(col.year)

                # --- EPS: Net Income / Diluted Shares ---
                eps = None
                if ni_row is not None and shares_row is not None:
                    ni = ni_row.get(col)
                    sh = shares_row.get(col)
                    if ni and sh:
                        try:
                            ni_f, sh_f = float(ni), float(sh)
                            if sh_f != 0 and not math.isnan(ni_f) and not math.isnan(sh_f):
                                eps = sf(ni_f / sh_f)
                        except Exception:
                            pass

                # Fallback trailingEps only for most recent quarter
                if eps is None and col == cols[0]:
                    eps = sf(info.get("trailingEps"))

                quarters.append({
                    "label":   quarter_label(col),
                    "revenue": rev_b,
                    "eps":     eps,
                    "yoy":     yoy,
                })

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

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"generated": now, "companies": companies}, f,
                  ensure_ascii=False, indent=2)
    print(f"\ndata.json saved — {len(companies)} companies — {now}")


if __name__ == "__main__":
    main()
