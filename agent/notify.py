"""Telegram alerts (optional). Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.

Sends a message, per commodity (wheat, gold, silver, platinum), when:
  * the BUY/SELL call changes (metals: only once the new call has held for two
    checks in a row, so a price wobbling on a threshold doesn't spam you),
  * the price moves more than the commodity's alert % in a day,
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


def load_state():
    try:
        s = json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if "signal" in s or "move_alert_for" in s:  # 1.x kept wheat's state at the top level
        s = {"wheat": s}
    return s


def save_state(s):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, sort_keys=True)
        f.write("\n")


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


def message(a, brief, reasons, site, title):
    s = a["signal"]
    lines = ["%s - %s" % (title, " / ".join(reasons)), "", brief["english"], "", brief["telugu"], "",
             "Proof (rule -> points x weight = counted):"]
    for e in s["evidence"]:
        lines.append("%+d x%g = %+g  %s: %s" % (e["points"], e.get("weight", 1), e.get("counted", e["points"]), e["rule"], e["value"]))
    if site:
        lines += ["", site]
    text = "\n".join(lines)
    if len(text) > 4000:  # Telegram's limit is 4096
        text = text[:3900] + "\n...\n" + (site or "")
    return text


def maybe_alert(a, brief, cfg, site=None, key="wheat", title="🌾 Dharalu · Wheat", move=None,
                move_limit=None, confirm=1, state=None):
    """state: the whole state dict (shared by all commodities); saved by the caller
    when given, otherwise loaded and saved here."""
    own = state is None
    allst = load_state() if own else state
    st = allst.setdefault(key, {})
    move_limit = move_limit if move_limit is not None else cfg["alerts"]["daily_move_pct"]
    reasons = []
    sig = a["signal"]["key"]
    changed = bool(st.get("signal")) and st["signal"] != sig
    if changed and confirm > 1:  # needs the same new call on `confirm` checks in a row
        n = st.get("pending_n", 0) + 1 if st.get("pending") == sig else 1
        st["pending"], st["pending_n"] = sig, n
        changed = n >= confirm
    elif not changed:
        st.pop("pending", None)
        st.pop("pending_n", None)
    if changed:
        reasons.append("call changed %s -> %s" % (st["signal"].replace("_", " "), a["signal"]["label"]))
    big = move is not None and abs(move) >= move_limit
    if big and st.get("move_alert_for") != a["asof"]:
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
        sent = send(message(a, b, reasons, site, title))
    # Only remember what was sent; a failed send is retried on the next run.
    if sent or not telegram_ready():
        if changed or not st.get("signal"):
            st["signal"] = sig
            st.pop("pending", None)
            st.pop("pending_n", None)
        if big:
            st["move_alert_for"] = a["asof"]
        if weekly:
            st["weekly"] = week
    if own:
        save_state(allst)
    return reasons, sent
