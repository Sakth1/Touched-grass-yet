#!/usr/bin/env bash
# release-merge.sh — merge dev into master with a local git push
#
# Why this exists: gh pr merge --merge uses the GitHub API, which sometimes
# does NOT generate a push event. Without a push event, GitHub Actions
# workflows (auto-release, tests) will NOT trigger.
#
# A local git merge + push guarantees a real push event.
#
# Usage: ./scripts/release-merge.sh
# Must be on the dev branch with all changes committed and pushed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Release Merge: dev -> master ==="

# Ensure we're on dev
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "dev" ]; then
  echo "ERROR: Must be on dev branch. Currently on: $BRANCH"
  exit 1
fi

# Ensure working tree is clean
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: Working tree has uncommitted changes. Commit or stash first."
  exit 1
fi

# Fetch latest from remote
echo "--- Fetching latest from remote ---"
git fetch origin

# Ensure dev is up to date
LOCAL_DEV="$(git rev-parse dev)"
REMOTE_DEV="$(git rev-parse origin/dev)"
if [ "$LOCAL_DEV" != "$REMOTE_DEV" ]; then
  echo "ERROR: Local dev ($(echo $LOCAL_DEV | head -c8)) != origin/dev ($(echo $REMOTE_DEV | head -c8)). Push first."
  exit 1
fi

# Checkout master and merge dev
echo "--- Checking out master ---"
git checkout master
git pull origin master

echo "--- Merging dev into master ---"
git merge dev --no-edit

echo "--- Pushing to master ---"
git push origin master

# Return to dev
echo "--- Returning to dev ---"
git checkout dev

echo "=== Done ==="
