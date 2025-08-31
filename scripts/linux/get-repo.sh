#!/usr/bin/env bash
REPO_URL="https://github.com/Bakminstof/pki-chain-builder"
REPO_NAME="pki-chain-builder"
BRANCH="release"

git clone --depth=1 --single-branch --branch "$BRANCH" --no-checkout "$REPO_URL" "$REPO_NAME"

cd "$REPO_NAME"

git sparse-checkout set --no-cone "/.gitattributes" "/.gitignore" "!/env" "/env/python-3.12.10-embed-amd64-linux" "/src" "/LICENSE" "/pyproject.toml"

git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"
git pull -X theirs "origin" "$BRANCH"
