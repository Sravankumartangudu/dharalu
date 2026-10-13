"""WheatWise daily run: fetch -> analyse -> brief -> publish -> alert.

    python agent/run.py             # normal run (what GitHub Actions does)
    python agent/run.py --offline   # re-analyse the data already saved
"""
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze  # noqa: E402
import briefing  # noqa: E402
import fetch  # noqa: E402
import notify  # noqa: E402

ROOT = fetch.ROOT
SITE = "https://sravankumartangudu.github.io/wheatwise/"
LOG = os.path.join(ROOT, "data", "signals_log.csv")
OUT = os.path.join(ROOT, "docs", "data", "latest.json")
LOG_FIELDS = ["date", "score", "signal", "price", "best_source", "best_landed"]
KEEP_OTHER_DAYS = 120  # all-India rows (not watched mandis) kept this long, for the state table


def keeper(watched):
    """Watched mandis are kept for ever; the rest of India only for the state table."""
    cut = (date.today() - timedelta(days=KEEP_OTHER_DAYS)).isoformat()
    return lambda r: r["market"] in watched or r["date"] >= cut


def log_signal(a):
    rows = []
    if os.path.exists(LOG):
        rows = list(csv.DictReader(open(LOG, encoding="utf-8")))
    rows = [r for r in rows if r["date"] != a["asof"]]
    best = a.get("best_source") or {}
    rows.append({"date": a["asof"], "score": a["signal"]["score"], "signal": a["signal"]["key"],
                 "price": round(a["benchmark"]["price"]), "best_source": best.get("market", ""),
                 "best_landed": best.get("landed", "")})
    rows.sort(key=lambda r: r["date"])
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return rows


def live_record(log_rows, series):
    """Grade the agent's real past calls once 30 days have passed."""
    px = {p["date"]: p["price"] for p in series if p["price"]}
    graded = []
    for r in log_rows:
        # first real price 30-37 days later (mandis skip holidays)
        later = next((k for k in ((analyze.d(r["date"]) + timedelta(days=30 + j)).isoformat() for j in range(8))
                      if k in px), None)
        if later:
            mv = analyze.pct(px[later], float(r["price"]))
            s = int(r["score"])
            # HOLD was right if keeping the stock paid (price rose); WAIT if nothing big happened
            right = (mv > 0) if s > 0 or r.get("signal") == "HOLD" else (mv < 0) if s < 0 else (abs(mv) < 3)
            graded.append({**r, "after30": px[later], "move_pct": round(mv, 2), "right": right})
    return {"calls": len(log_rows), "graded": len(graded),
            "right_pct": round(100.0 * sum(g["right"] for g in graded) / len(graded), 1) if graded else None,
            "rows": graded[-60:], "pending": [r for r in log_rows if r["date"] not in {g["date"] for g in graded}][-30:]}


def main():
    offline = "--offline" in sys.argv
    cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
    watched = {m["name"] for m in cfg["source_markets"]}
    current = None
    keep = keeper(watched)
    if not offline:
        try:
            current = fetch.fetch_current(log=lambda _m: None)
        except RuntimeError as e:  # data.gov.in is down now and then - analyse what we have
            print("! Today's feed failed (%s) - using saved data" % e)
            current = []
        print("Today's feed: %d rows" % len(current))
        new = list(current)
        # Fill any days the feed missed for the benchmark mandis (cheap: newest rows only).
        own_key = fetch.api_key() != fetch.SAMPLE_KEY
        for m in cfg["source_markets"]:
            if m.get("long_history") or own_key:
                try:
                    new += fetch.fetch_market_history(m["name"], max_rows=30 if own_key else 20, log=lambda _m: None)
                except RuntimeError as e:
                    print("  ! %s: %s" % (m["name"], e))
        added, total = fetch.merge_prices(new, keep)
        print("Merged: +%d rows (%d total)" % (added, total))
    rows = [r for r in fetch.load_prices() if keep(r)]
    a = analyze.run(rows, cfg, current_rows=current or None)
    log_rows = log_signal(a)
    a["track_record"]["live"] = live_record(log_rows, a["series"])
    a["briefing"] = briefing.build(a)
    a["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    a["config"] = {k: cfg[k] for k in ("business", "msp", "omss", "freight", "costs", "carrying",
                                       "source_markets", "state_km", "consumer_states")}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, separators=(",", ":"), default=str)
    s = a["signal"]
    print("%s  %s  score %+d/%d  confidence %s  price %s" % (
        a["asof"], s["label"], s["score"], s["max_score"], s["confidence"], round(a["benchmark"]["price"])))
    for e in s["evidence"]:
        print("   %+d  %-34s %s" % (e["points"], e["rule"], e["value"]))
    reasons, sent = notify.maybe_alert(a, a["briefing"], cfg, SITE)
    if reasons:
        print("Alert: %s (%s)" % (", ".join(reasons), "sent" if sent else "Telegram not set up"))


if __name__ == "__main__":
    main()
