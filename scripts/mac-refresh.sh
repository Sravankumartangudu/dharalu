#!/usr/bin/env bash
# Dharalu: check prices from this Mac and publish them to GitHub Pages.
# launchd runs this every 5 minutes (scripts/mac-schedule.sh install). Each run:
#   * gold, silver, platinum: fetched and re-analysed every time;
#   * wheat: one quick call (one benchmark mandi, taking turns; a 429 pauses it 30 min);
#     the full fetch only when there are new prices, or every 6 hours (data.gov.in
#     refuses GitHub's servers, so wheat comes from here);
#   * publishes (commit + push) when something material changed - a new prices day, a
#     call change, new mandi rows - at most every 10 minutes, else once an hour.
#     GitHub Pages allows about 10 site builds an hour; the dashboard and the Mac app
#     fetch live metal prices themselves in between.
# If GitHub can't be reached, the run still analyses and commits locally; a later run
# pushes it.
#   scripts/mac-refresh.sh          # what launchd runs (quick check)
#   scripts/mac-refresh.sh --full   # full wheat fetch, publish now
set -uo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")/.."

MODE="${1:---quick}"
NAME="${DH_GIT_NAME:-Sravankumartangudu}"
EMAIL="${DH_GIT_EMAIL:-33101147+Sravankumartangudu@users.noreply.github.com}"
PUSHED=".git/dharalu-pushed"   # touched after every successful push
LOG="$HOME/Library/Logs/Dharalu/refresh.log"
MATERIAL_MIN=10
REGULAR_MIN=60

# Keep the log small: launchd reopens it on every run, so a rename is enough.
if [ -f "$LOG" ] && [ "$(stat -f %z "$LOG")" -gt 2000000 ]; then mv -f "$LOG" "$LOG.1"; fi

echo "== $(date '+%Y-%m-%d %H:%M:%S %Z') Dharalu refresh ($MODE)"
OUT="$(python3 agent/run.py "$MODE" 2>&1)"; RC=$?
echo "$OUT" | grep -vE '^ +[+-][0-9]+ ' # the proof lines are in the published data
[ $RC -eq 0 ] || { echo "! agent failed"; exit 1; }

MATERIAL="$(echo "$OUT" | sed -n 's/^MATERIAL: //p' | tail -1)"
age_min() { [ -f "$PUSHED" ] && echo $(( ($(date +%s) - $(stat -f %m "$PUSHED")) / 60 )) || echo 99999; }
AGE=$(age_min)
AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
if [ "$MODE" = "--quick" ] && [ "$AHEAD" -eq 0 ]; then
  if [ "$MATERIAL" = "none" ] || [ -z "$MATERIAL" ]; then
    [ "$AGE" -ge $REGULAR_MIN ] || { echo "Saved locally (published ${AGE} min ago)"; exit 0; }
  else
    [ "$AGE" -ge $MATERIAL_MIN ] || { echo "Change waits for the 10-minute gap: $MATERIAL"; exit 0; }
  fi
fi

git add data docs/data
if ! git diff --cached --quiet; then
  git -c user.name="$NAME" -c user.email="$EMAIL" commit -q -m "data: $(date '+%Y-%m-%d %H:%M') IST${MATERIAL:+ - $MATERIAL}"
fi
for i in 1 2 3; do
  # -X theirs: on a clash (the GitHub Actions backup also commits data) keep this run's newer data.
  if git pull -q --rebase -X theirs --autostash && git push -q; then
    touch "$PUSHED"; echo "Published"; exit 0
  fi
  git rebase --abort 2>/dev/null
  sleep $((i * 10))
done
echo "! push failed - committed locally, a later run will push it"; exit 0
