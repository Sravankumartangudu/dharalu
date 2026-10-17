"""Fetch wheat mandi prices from data.gov.in (Agmarknet feeds).

Two feeds are used:
  * CURRENT  - today's prices from every reporting mandi (refreshed daily).
  * ARCHIVE  - "Variety-wise Daily Market Prices" with history back to 2010,
               used to seed history for the markets we watch.

The free public sample key returns only 10 rows per call, so everything here
pages, paces itself and retries. Put your own free key from data.gov.in in the
DATA_GOV_IN_KEY environment variable (or GitHub secret) for faster runs.
"""
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime

SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
CURRENT = "9ef84268-d588-465a-a308-a864a43d0070"
ARCHIVE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE = "https://api.data.gov.in/resource/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_CSV = os.path.join(ROOT, "data", "prices.csv")
FIELDS = ["date", "state", "district", "market", "variety", "grade", "min", "max", "modal"]


def api_key():
    return os.environ.get("DATA_GOV_IN_KEY") or SAMPLE_KEY


def _get(resource, params, tries=6):
    q = {"api-key": api_key(), "format": "json"}
    q.update(params)
    url = BASE + resource + "?" + urllib.parse.urlencode(q)
    delay, why = 4, "no answer"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WheatWise/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read().decode("utf-8", "replace")
            data = json.loads(body)
            if "records" in data:
                return data
            why = "no records: %s" % (data.get("message") or body[:80])
        except Exception as e:  # 503 rate-limit pages, timeouts, bad JSON
            why = "%s: %s" % (type(e).__name__, str(e)[:80])
        time.sleep(delay)
        delay = min(delay * 2, 60)
    raise RuntimeError("data.gov.in did not answer after %d tries (last: %s)" % (tries, why))


def _paged(resource, filters, sort=None, max_rows=None, pace=1.2, log=None):
    params = {"filters[%s]" % k: v for k, v in filters.items()}
    if sort:
        params["sort[%s]" % sort[0]] = sort[1]
    want = 1000 if api_key() != SAMPLE_KEY else 10
    offset, rows, total = 0, [], None
    while True:
        params.update({"limit": want, "offset": offset})
        data = _get(resource, params)
        total = int(data.get("total") or 0)
        recs = data.get("records") or []
        rows.extend(recs)
        offset += len(recs)
        if log:
            log("  %d / %d" % (min(offset, max_rows or total), min(total, max_rows or total)))
        if not recs or offset >= total or (max_rows and offset >= max_rows):
            break
        time.sleep(pace)
    return rows


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _norm(rec):
    """Both feeds use different key casing - normalise to one row shape."""
    g = lambda *ks: next((rec[k] for k in ks if k in rec and rec[k] not in (None, "")), "")
    d = g("arrival_date", "Arrival_Date")
    try:
        iso = datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None
    modal = _num(g("modal_price", "Modal_Price"))
    if not modal or modal <= 0:
        return None
    return {
        "date": iso,
        "state": g("state", "State").strip(),
        "district": g("district", "District").strip(),
        "market": g("market", "Market").strip(),
        "variety": g("variety", "Variety").strip(),
        "grade": g("grade", "Grade").strip(),
        "min": _num(g("min_price", "Min_Price")) or "",
        "max": _num(g("max_price", "Max_Price")) or "",
        "modal": modal,
    }


def fetch_current(log=print):
    log("Fetching today's wheat prices from all mandis ...")
    recs = _paged(CURRENT, {"commodity": "Wheat"}, log=log)
    return [r for r in (_norm(x) for x in recs) if r]


def fetch_market_history(market, max_rows=1500, log=print):
    log("History for %s ..." % market)
    recs = _paged(ARCHIVE, {"Commodity": "Wheat", "Market": market},
                  sort=("Arrival_Date", "desc"), max_rows=max_rows, log=log)
    return [r for r in (_norm(x) for x in recs) if r]


def load_prices():
    if not os.path.exists(PRICES_CSV):
        return []
    with open(PRICES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["modal"] = float(r["modal"])
    return rows


def merge_prices(new_rows, keep=None):
    """Add rows to data/prices.csv, de-duplicated on date+market+variety+grade.
    keep(row) -> False drops a row from the file (stops it growing forever)."""
    rows = load_prices()
    key = lambda r: (r["date"], r["market"], r["variety"], r["grade"])
    seen = {key(r): i for i, r in enumerate(rows)}
    added = 0
    for r in new_rows:
        k = key(r)
        if k in seen:
            rows[seen[k]] = r
        else:
            seen[k] = len(rows)
            rows.append(r)
            added += 1
    if keep:
        rows = [r for r in rows if keep(r)]
    rows.sort(key=lambda r: (r["date"], r["state"], r["market"], r["variety"]))
    os.makedirs(os.path.dirname(PRICES_CSV), exist_ok=True)
    with open(PRICES_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    return added, len(rows)
