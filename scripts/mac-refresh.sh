#!/usr/bin/env bash
# Fetch today's prices from this Mac, analyse, and publish to GitHub Pages.
# data.gov.in refuses GitHub's (US) servers, so the real fetch happens here; the
# GitHub Actions run then re-publishes whatever this pushed.
# Run by hand, or twice a day by launchd (see scripts/mac-schedule.sh).
set -uo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")/.."

NAME="${WW_GIT_NAME:-Sravankumartangudu}"
EMAIL="${WW_GIT_EMAIL:-33101147+Sravankumartangudu@users.noreply.github.com}"
echo "== $(date '+%Y-%m-%d %H:%M %Z') WheatWise refresh"

# Start from what GitHub has (the Actions run commits data too). Only the agent writes
# data/ and docs/data, and this run rebuilds them, so leftover local edits there are dropped.
git checkout -q -- data docs/data
git pull -q --rebase --autostash || { echo "! git pull failed"; exit 1; }

python3 agent/run.py || { echo "! agent failed"; exit 1; }

git add data docs/data
git diff --cached --quiet && { echo "Nothing new to save"; exit 0; }
git -c user.name="$NAME" -c user.email="$EMAIL" commit -q -m "data: $(date '+%Y-%m-%d %H:%M') IST (fetched from Mac)"
for i in 1 2 3; do
  git pull -q --rebase --autostash && git push -q && { echo "Published"; exit 0; }
  sleep $((i * 10))
done
echo "! push failed after 3 tries" >&2; exit 1
