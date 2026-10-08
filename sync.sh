#!/bin/zsh
# 正本在 ~/claude/aigc（Claude Code 工作区）。改完那边的 skill，跑这个把副本同步进仓库并推送。
# 用法：./sync.sh "改了什么"
set -e
R="${0:A:h}"
EX=(--exclude .DS_Store --exclude __pycache__)
mkdir -p "$R/skills" "$R/chatcut"
for s in juese-sheji character-sheet; do rsync -a --delete $EX "$HOME/claude/aigc/.claude/skills/$s/" "$R/skills/$s/"; done
rsync -a --delete $EX "$HOME/claude/aigc/exports/juese-sheji-chatcut/" "$R/chatcut/juese-sheji/"
cd "$R"
git add -A
git diff --cached --quiet && { echo "没有改动"; exit 0; }
git commit -q -m "${1:-同步 skill}"
git push -q
echo "已推送：$(git log -1 --format='%h %s')"
