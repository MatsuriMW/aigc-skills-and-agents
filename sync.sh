#!/bin/zsh
# 正本在 ~/claude/aigc（Claude Code 工作区）。改完那边的 skill，跑这个把副本同步进仓库并推送。
# 角色设计 juese-sheji 已经搬到独立仓库 ai-character-design-skill（在那边跑它自己的 sync.sh），这里不再同步。
# 用法：./sync.sh "改了什么"
set -e
R="${0:A:h}"
EX=(--exclude .DS_Store --exclude __pycache__)
mkdir -p "$R/skills"
for s in character-sheet; do rsync -a --delete $EX "$HOME/claude/aigc/.claude/skills/$s/" "$R/skills/$s/"; done
cd "$R"
git add -A
git diff --cached --quiet && { echo "没有改动"; exit 0; }
git commit -q -m "${1:-同步 skill}"
git push -q
echo "已推送：$(git log -1 --format='%h %s')"
