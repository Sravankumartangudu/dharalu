"""One-time history seed for the watched mandis (safe to re-run; it de-duplicates).

Agmarknet renamed most markets in Nov 2025 ("Indore" -> "Indore APMC"), so for
each watched market we pull both names: the new name for the recent year, and
the old name (longer history) for the seasonal pattern.

    python agent/bootstrap.py            # all watched markets
    python agent/bootstrap.py --quick    # recent history only (faster)
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # noqa: E402

ROOT = fetch.ROOT


def main():
    quick = "--quick" in sys.argv
    cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
    jobs = []
    for m in cfg["source_markets"]:
        jobs.append((m["name"], 1500))
        if not quick and m.get("old_name") and m.get("long_history"):
            jobs.append((m["old_name"], 2500))

    def run(job):
        name, cap = job
        try:
            rows = fetch.fetch_market_history(name, max_rows=cap, log=lambda _m: None)
            # Old-name rows are stored under the new name so each mandi is one series.
            new = next((m["name"] for m in cfg["source_markets"] if m.get("old_name") == name), name)
            for r in rows:
                r["market"] = new
            return name, rows
        except Exception as e:  # keep going - one bad market shouldn't stop the seed
            print("  ! %s: %s" % (name, e), flush=True)
            return name, []

    with ThreadPoolExecutor(max_workers=3) as pool:
        for name, rows in pool.map(run, jobs):
            added, total = fetch.merge_prices(rows)
            print("%-28s %5d rows (+%d new, %d total)" % (name, len(rows), added, total), flush=True)


if __name__ == "__main__":
    main()
