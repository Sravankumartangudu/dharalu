#!/usr/bin/env bash
# Commit data/ and docs/data, then push - rebasing first in case config.json
# (or anything else) was edited on GitHub while this run was going.
set -euo pipefail
git config user.name "WheatWise bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add data docs/data
git diff --cached --quiet && { echo "Nothing new to save"; exit 0; }
git commit -q -m "$1"
for i in 1 2 3; do
  git pull -q --rebase --autostash && git push -q && exit 0
  sleep $((i * 5))
done
echo "Push failed after 3 tries" >&2; exit 1
