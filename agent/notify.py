"""Telegram alerts (optional). Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.

Sends a message when:
  * the BUY/SELL signal changes,
  * the benchmark price moves more than alerts.daily_move_pct in a day,
  * once a week (alerts.weekly_summary_weekday, 0 = Monday) as a summary.
State is kept in data/state.json so the same alert is not sent twice.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import date

from fetch import ROOT

STATE = os.path.join(ROOT, "data", "state.json")


def _load():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(s):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


def telegram_ready():
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def send(text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen("https://api.telegram.org/bot%s/sendMessage" % tok, data=data, timeout=20).read()
        return True
    except Exception as e:
        print("  Telegram send failed: %s" % e)
        return False


def message(a, brief, reasons, site):
    s = a["signal"]
    lines = ["🌾 WheatWise - " + " / ".join(reasons), "", brief["english"], "", brief["telugu"], "",
             "Proof (rule -> points):"]
    for e in s["evidence"]:
        lines.append("%+d  %s: %s" % (e["points"], e["rule"], e["value"]))
    if site:
        lines += ["", site]
    text = "\n".join(lines)
    if len(text) > 4000:  # Telegram's limit is 4096
        text = text[:3900] + "\n...\n" + (site or "")
    return text


def maybe_alert(a, brief, cfg, site=None):
    st = _load()
    reasons = []
    key = a["signal"]["key"]
    if st.get("signal") and st["signal"] != key:
        reasons.append("signal changed %s -> %s" % (st["signal"], a["signal"]["label"]))
    move = a["benchmark"].get("chg_1d")
    if move is not None and abs(move) >= cfg["alerts"]["daily_move_pct"] and st.get("move_alert_for") != a["asof"]:
        reasons.append("price moved %+.1f%% in a day" % move)
    today = date.today()
    week = list(today.isocalendar()[:2])
    weekly = today.weekday() == cfg["alerts"]["weekly_summary_weekday"] and st.get("weekly") != week
    if weekly:
        reasons.append("weekly summary")
    if not st.get("signal"):
        reasons.append("monitoring started")
    sent = False
    if reasons:
        b = brief.get("ai") or brief["rules"]
        sent = send(message(a, b, reasons, site))
    # Only remember what was sent; a failed send is retried on the next run.
    if sent or not telegram_ready():
        st["signal"] = key
        if move is not None and abs(move) >= cfg["alerts"]["daily_move_pct"]:
            st["move_alert_for"] = a["asof"]
        if weekly:
            st["weekly"] = week
        _save(st)
    return reasons, sent
