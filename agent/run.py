"""Dharalu run: fetch -> analyse -> brief -> publish -> alert, for wheat, gold,
silver and platinum.

    python agent/run.py               # full run: today's wheat feed + all metals
    python agent/run.py --quick       # the 5-minute check: metals every time; wheat's
                                      #   full fetch only if the benchmark mandis have
                                      #   new prices (or the last full fetch is 6 h old)
    python agent/run.py --offline     # re-analyse the data already saved
    python agent/run.py --if-stale 3  # do nothing if a run published in the last 3 hours
                                      #   (GitHub Actions is the backup for the Mac)

Ends with "MATERIAL: <reasons>" when something worth publishing changed (a new
prices day, a call change, new mandi rows), else "MATERIAL: none".
"""
import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze  # noqa: E402
import briefing  # noqa: E402
import fetch  # noqa: E402
import metals  # noqa: E402
import notify  # noqa: E402

ROOT = fetch.ROOT
SITE = "https://sravankumartangudu.github.io/dharalu/"
DATA = os.path.join(ROOT, "docs", "data")
LOG = os.path.join(ROOT, "data", "signals_log.csv")
OUT = os.path.join(DATA, "latest.json")
SUMMARY = os.path.join(DATA, "summary.json")
LOG_FIELDS = ["date", "score", "signal", "price", "best_source", "best_landed"]
METAL_LOG_FIELDS = ["date", "score", "signal", "price"]
KEEP_OTHER_DAYS = 120  # all-India rows (not watched mandis) kept this long, for the state table
FULL_EVERY_H = 6       # --quick still does a full wheat fetch this often


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat(timespec="seconds")


def age_h(iso):
    try:
        return (now() - datetime.fromisoformat(iso)).total_seconds() / 3600.0
    except (TypeError, ValueError):
        return 1e9


def read_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def published_summary():
    """The summary as last committed (= published), so a change that wasn't pushed
    yet still counts as material on the next run. Falls back to the file on disk."""
    try:
        out = subprocess.run(["git", "show", "HEAD:docs/data/summary.json"], cwd=ROOT,
                             capture_output=True, timeout=20)
        if out.returncode == 0:
            return json.loads(out.stdout.decode("utf-8"))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return read_json(SUMMARY) or {}


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), default=str)
    os.replace(tmp, path)


def keeper(watched):
    """Watched mandis are kept for ever; the rest of India only for the state table."""
    cut = (date.today() - timedelta(days=KEEP_OTHER_DAYS)).isoformat()
    return lambda r: r["market"] in watched or r["date"] >= cut


def log_signal(path, fields, row):
    """One row per prices day (a later run on the same day replaces it)."""
    rows = list(csv.DictReader(open(path, encoding="utf-8"))) if os.path.exists(path) else []
    rows = [r for r in rows if r["date"] != row["date"]]
    rows.append(row)
    rows.sort(key=lambda r: r["date"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return rows


def live_record(log_rows, series):
    """Grade the agent's real past calls once 30 days have passed."""
    px = {p["date"]: p["price"] for p in series if p["price"]}
    graded = []
    for r in log_rows:
        # first real price 30-37 days later (mandis and markets skip holidays)
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


# --------------------------------------------------------------------------- wheat
def wheat(cfg, mode, rstate):
    """Returns (analysis, reasons it changed). mode: full | quick | offline."""
    watched = {m["name"] for m in cfg["source_markets"]}
    keep = keeper(watched)
    old = read_json(OUT)
    current, added, why = None, 0, []
    if mode != "offline":
        # A failed full fetch takes minutes of retries: after one, wait an hour before the next.
        full = mode == "full" or old is None or (
            age_h(rstate.get("wheat_full_at")) >= FULL_EVERY_H and age_h(rstate.get("wheat_try_at")) >= 1)
        bench = [m["name"] for m in cfg["source_markets"] if m.get("long_history")]
        if not full:
            # Cheap check: the newest 10 rows of each benchmark mandi (1 call each).
            new = []
            for name in bench:
                try:
                    new += fetch.fetch_market_history(name, max_rows=10, log=lambda _m: None, tries=2)
                except RuntimeError as e:
                    print("  ! wheat %s: %s" % (name, e))
            added, _ = fetch.merge_prices(new, keep)
            print("Wheat quick check: +%d new rows" % added)
            full = added > 0
        if full:
            rstate["wheat_try_at"] = stamp()
            try:
                current = fetch.fetch_current(log=lambda _m: None)
                rstate["wheat_full_at"] = stamp()
            except RuntimeError as e:  # data.gov.in is down now and then - analyse what we have
                print("! Today's wheat feed failed (%s) - using saved data" % e)
                current = []
            print("Today's wheat feed: %d rows" % len(current))
            new = list(current)
            # Fill any days the feed missed for the benchmark mandis (cheap: newest rows only).
            own_key = fetch.api_key() != fetch.SAMPLE_KEY
            for m in cfg["source_markets"]:
                if m.get("long_history") or own_key:
                    try:
                        new += fetch.fetch_market_history(m["name"], max_rows=30 if own_key else 20, log=lambda _m: None)
                    except RuntimeError as e:
                        print("  ! %s: %s" % (m["name"], e))
            more, total = fetch.merge_prices(new, keep)
            added += more
            print("Wheat merged: +%d rows (%d total)" % (more, total))
        if not full and old is not None:
            return old, []  # nothing new: keep the published analysis as it is
    if added:
        why.append("wheat +%d mandi rows" % added)
    rows = [r for r in fetch.load_prices() if keep(r)]
    a = analyze.run(rows, cfg, current_rows=current or None)
    best = a.get("best_source") or {}
    log_rows = log_signal(LOG, LOG_FIELDS, {
        "date": a["asof"], "score": a["signal"]["score"], "signal": a["signal"]["key"],
        "price": round(a["benchmark"]["price"]), "best_source": best.get("market", ""),
        "best_landed": best.get("landed", "")})
    a["track_record"]["live"] = live_record(log_rows, a["series"])
    # Claude writes the briefing once per prices day; later runs that day reuse it.
    reuse = old and old.get("asof") == a["asof"] and (old.get("briefing") or {}).get("ai")
    a["briefing"] = {"rules": briefing.rule_based(a), "ai": old["briefing"]["ai"]} if reuse else briefing.build(a)
    a["generated_at"] = stamp()
    a["config"] = {k: cfg[k] for k in ("business", "msp", "omss", "freight", "costs", "carrying",
                                       "source_markets", "state_km", "consumer_states")}
    a["series_weekly"] = weekly_wheat(rows, cfg)
    write_json(OUT, a)
    s = a["signal"]
    print("Wheat %s  %s  score %+d/%d  confidence %s  price %s" % (
        a["asof"], s["label"], s["score"], s["max_score"], s["confidence"], round(a["benchmark"]["price"])))
    for e in s["evidence"]:
        print("   %+d  %-34s %s" % (e["points"], e["rule"], e["value"]))
    return a, why


def weekly_wheat(rows, cfg):
    """Whole benchmark history, one point a week, for the timeline's "All" range."""
    md = analyze.market_daily(rows)
    bench = analyze.benchmark_series(md, [m["name"] for m in cfg["source_markets"] if m.get("long_history")])
    return metals.weekly(bench)


# --------------------------------------------------------------------------- metals
def metal_runs(cfg, offline):
    if offline:
        live = read_json(os.path.join(metals.DIR, "live.json")) or {}
    else:
        try:
            live = metals.update(cfg)
        except Exception as e:  # never let the metals stop wheat
            print("! metals fetch failed: %s" % e)
            live = read_json(os.path.join(metals.DIR, "live.json")) or {}
    out = {}
    for k in metals.METALS:
        try:
            a = metals.analyse(k, cfg, live)
        except Exception as e:
            print("! %s analysis failed: %s" % (k, e))
            old = read_json(os.path.join(DATA, k + ".json"))
            if old:
                out[k] = old
            continue
        log_rows = log_signal(os.path.join(ROOT, "data", "signals_%s.csv" % k), METAL_LOG_FIELDS, {
            "date": a["asof"], "score": a["signal"]["score"], "signal": a["signal"]["key"], "price": a["price"]})
        a["track_record"]["live"] = live_record(log_rows, a["series"])
        a["briefing"] = {"rules": metals.rule_brief(a), "ai": None}
        a["generated_at"] = stamp()
        # The long parts (10 years of prices, the day-by-day replay) go to <metal>-history.json,
        # rewritten once a day; <metal>.json (call, proof, forecast) is small and changes every run.
        # Publishing every few minutes would otherwise bloat the git history.
        hpath = os.path.join(DATA, k + "-history.json")
        old_h = read_json(hpath) or {}
        if old_h.get("asof") != a["asof"] or "--offline" in sys.argv:
            write_json(hpath, {"asof": a["asof"], "generated_at": a["generated_at"], "series": a["series"],
                               "series_weekly": a["series_weekly"], "predictions": a["predictions"],
                               "track_rows": a["track_record"]["rows"]})
        light = {x: v for x, v in a.items() if x not in ("series", "series_weekly", "predictions")}
        light["track_record"] = {x: v for x, v in a["track_record"].items() if x != "rows"}
        write_json(os.path.join(DATA, k + ".json"), light)
        s = a["signal"]
        print("%-8s %s  %s  score %+d/%d  %s  %s" % (
            a["label"], a["asof"], s["label"], s["score"], s["max_score"], s["confidence"], metals.inr(a["price"])))
        out[k] = a
    return out


# --------------------------------------------------------------------------- summary
def _same_call(tr, key):
    grp = {"STRONG_BUY": "buy_days", "BUY": "buy_days", "HOLD": "hold_days", "WAIT": "wait_days",
           "SELL": "sell_days", "STRONG_SELL": "sell_days"}[key]
    s = (tr.get("summary") or {}).get(grp)
    if not s or s["days"] < 10:
        return {"scope": "since %s" % (tr.get("since") or "start"), **((tr.get("summary_all") or {}).get(grp) or {})}
    return {"scope": "last 12 months", **s}


def entry(key, a):
    s = a["signal"]
    tr = a["track_record"]
    live = tr.get("live") or {}
    f30 = (a.get("forecast_points") or {}).get("30")
    e = {
        "key": key, "asof": a["asof"], "generated_at": a.get("generated_at"),
        "signal": {k: s[k] for k in ("key", "label", "telugu", "score", "max_score", "confidence", "buyer", "holder")},
        "evidence": [{k: x[k] for k in ("rule", "value", "test", "points", "max", "source")} for x in s["evidence"]],
        "forecast30": f30,
        "record": {"same_call": _same_call(tr, s["key"]), "live_right_pct": live.get("right_pct"),
                   "live_graded": live.get("graded", 0)},
        "briefing": (a.get("briefing") or {}).get("ai") or (a.get("briefing") or {}).get("rules"),
        "timing": {k: a["timing"][k] for k in ("cheapest_months", "dearest_months", "next_buy_window", "days_to_buy_window")},
        "carrying_cost_30d_pct": a.get("carrying_cost_30d_pct"),
    }
    if key == "wheat":
        b, best = a["benchmark"], a.get("best_source") or {}
        e.update({"label": "Wheat", "telugu_name": "గోధుమ", "emoji": "🌾", "unit": "Rs per quintal",
                  "unit_short": "/qtl", "price": round(b["price"]),
                  "chg_1d": b.get("chg_1d"), "chg_7d": b.get("chg_7d"), "chg_30d": b.get("chg_30d"),
                  "move_alert_pct": None, "live": None})
        lines = []
        if best:
            lines.append("Cheapest landed at Srikakulam: %s Rs %s/qtl (mandi Rs %s + freight Rs %s)" % (
                best["market"], format(best["landed"], ","), format(best["mandi_price"], ","), format(best["freight"], ",")))
        lines.append("MSP Rs %s (%+.1f%%)" % (format(a["msp"]["floor"], ","), analyze.pct(b["price"], a["msp"]["floor"])))
        e["lines"] = lines
    else:
        ind, w = a["indicators"], a["world"]
        factor = w["usdinr"] / a["convert"]["oz_g"] * a["grams"] * (1 + a["convert"]["duty_pct"] / 100.0)
        prev = [p for p in a.get("series") or [] if p["date"] < a["asof"]]
        e.update({"label": a["label"], "telugu_name": a["telugu_name"], "emoji": a["emoji"], "unit": a["unit"],
                  "unit_short": "/10 g" if a["grams"] == 10 else "/kg", "price": a["price"],
                  "price_with_gst": a["price_with_gst"], "gst_pct": a["costs"]["gst_pct"],
                  "chg_1d": ind.get("chg_1d"), "chg_7d": ind.get("chg_7d"), "chg_30d": ind.get("chg_30d"),
                  "move_alert_pct": None,
                  # The app/dashboard turn a live US$ spot price into Rs with: usd x factor.
                  "live": {"symbol": w["spot_symbol"], "usd": w["usd_oz"], "factor": round(factor, 6),
                           "prev_close": prev[-1]["price"] if prev else None, "updated": w["updated"]},
                  "lines": ["With %g%% GST: %s" % (a["costs"]["gst_pct"], metals.inr(a["price_with_gst"])),
                            "World US$%s/oz x Rs %.2f per US$ + %g%% duty" % (
                                format(w["usd_oz"], ",.2f"), w["usdinr"], a["convert"]["duty_pct"])]})
    return e


def main():
    args = sys.argv[1:]
    offline = "--offline" in args
    mode = "offline" if offline else "quick" if "--quick" in args else "full"
    old_sum = published_summary()
    if "--if-stale" in args:
        hours = float(args[args.index("--if-stale") + 1])
        if age_h(old_sum.get("generated_at")) < hours:
            print("Published %.1f h ago (< %g h) - nothing to do." % (age_h(old_sum.get("generated_at")), hours))
            print("MATERIAL: none")
            return
    cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
    state = notify.load_state()
    rstate = state.setdefault("run", {})

    w, why = wheat(cfg, mode, rstate)
    ms = metal_runs(cfg, offline)
    all_ = {"wheat": w, **ms}

    summary = {"generated_at": stamp(), "site": SITE, "order": ["wheat"] + list(metals.METALS),
               "items": {k: entry(k, a) for k, a in all_.items()}}
    for k, it in summary["items"].items():
        if k != "wheat":
            it["move_alert_pct"] = cfg["metals"][k]["move_alert_pct"]
    summary["items"]["wheat"]["move_alert_pct"] = cfg["alerts"]["daily_move_pct"]
    write_json(SUMMARY, summary)

    # What changed since the last published (committed) summary?
    olds = old_sum.get("items") or {}
    for k, it in summary["items"].items():
        o = olds.get(k)
        if not o:
            why.append("%s new" % k)
        elif o["signal"]["key"] != it["signal"]["key"]:
            why.append("%s call %s -> %s" % (k, o["signal"]["key"], it["signal"]["key"]))
        elif o["asof"] != it["asof"]:
            why.append("%s new day %s" % (k, it["asof"]))

    # Alerts
    for k, a in all_.items():
        if not a.get("briefing"):
            continue
        if k == "wheat":
            if mode == "quick" and not why:
                continue  # wheat only changes when mandi prices do
            reasons, sent = notify.maybe_alert(a, a["briefing"], cfg, SITE, key="wheat",
                                               title="🌾 Dharalu · Wheat", move=a["benchmark"].get("chg_1d"),
                                               state=state)
        else:
            m = cfg["metals"][k]
            reasons, sent = notify.maybe_alert(a, a["briefing"], cfg, SITE + "#" + k, key=k,
                                               title="%s Dharalu · %s" % (m["emoji"], m["label"]),
                                               move=a["indicators"].get("chg_1d"), move_limit=m["move_alert_pct"],
                                               confirm=2, state=state)
        if reasons:
            print("Alert %s: %s (%s)" % (k, ", ".join(reasons), "sent" if sent else "Telegram not set up"))
    notify.save_state(state)
    print("MATERIAL: %s" % ("; ".join(why) if why else "none"))


if __name__ == "__main__":
    main()
