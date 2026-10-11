#!/bin/zsh
# character-sheet 的正本在 ~/claude/aigc（Claude Code 工作区）；古典式配图的公开版在 ~/claude/skills-agents-and-prompts。
# 改完正本，跑这个把副本同步进仓库并推送。
# 角色设计 juese-sheji 已经搬到独立仓库 ai-character-design-skill（在那边跑它自己的 sync.sh），这里不再同步。
# 用法：./sync.sh "改了什么"
set -e
R="${0:A:h}"
EX=(--exclude .DS_Store --exclude __pycache__)
mkdir -p "$R/skills"
for s in character-sheet; do rsync -a --delete $EX "$HOME/claude/aigc/.claude/skills/$s/" "$R/skills/$s/"; done
# 古典式配图：公开版（SKILL.md + examples/ 样图）在 skills-agents-and-prompts 仓库里维护，这里跟着它走
rsync -a --delete $EX "$HOME/claude/skills-agents-and-prompts/skills/gudianshi-skill/" "$R/skills/gudianshi-skill/"
cd "$R"
git add -A
git diff --cached --quiet && { echo "没有改动"; exit 0; }
git commit -q -m "${1:-同步 skill}"
git push -q
echo "已推送：$(git log -1 --format='%h %s')"
