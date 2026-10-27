#!/bin/zsh
# AIGC 相关的 skill 和工作区配置的展示库。正本都在 skillshare 源（~/.config/skillshare/skills），这里只单向导出。
# 准入标准：只放我自己做的或改过的；原样下载的 skill 不进，README 里给上游链接。
# 单独建了仓库的 skill（角色设计 juese-sheji → ai-character-design-skill）不在这里留副本。
# 用法：./sync.sh "改了什么"
set -e
R="${0:A:h}"
SS="$HOME/.config/skillshare/skills"
EX=(--exclude .DS_Store --exclude __pycache__)

# 在 skillshare 源里按名字找 skill，不管它放在哪个分组
ss_skill() {
  local d=("$SS"/$1(/N) "$SS"/*/$1(/N))
  [[ -n "$d[1]" ]] || { echo "skillshare 源里找不到 skill：$1" >&2; return 1 }
  print -r -- "$d[1]"
}

mkdir -p "$R/skills"
# character-sheet、minimax-tts、virgin-vs-chad、yuyan-sheji、eagle-assets 自制；eagle-assets 只导出脚本和说明，素材图在我的 Eagle 库里，不进仓库；cinematic-director 改自 wuwangzhang1216/DirectorSKILL（MIT）
# virgin-vs-chad 的角色图不在 skill 目录里（出处和许可各不相同），导出的只有脚本和说明
for s in cinematic-director minimax-tts virgin-vs-chad yuyan-sheji eagle-assets; do
  src=$(ss_skill $s) || exit 1
  rsync -a --delete $EX "$src/" "$R/skills/$s/"
done
# 角色设定板：README 里的四张案例图只在这个仓库的 examples/ 里（不进正本，免得装 skill 的地方都多一兆图），同步时保留
src=$(ss_skill character-sheet) || exit 1
rsync -a --delete $EX --exclude examples "$src/" "$R/skills/character-sheet/"
# 古典式配图：SKILL.md 跟着正本走，examples/ 样图只在这个仓库里，同步时保留
src=$(ss_skill gudianshi-skill) || exit 1
rsync -a --delete $EX --exclude examples "$src/" "$R/skills/gudianshi-skill/"

# Eagle 音效：index.json 是我自己库里量出来的数，别人的库用不上，不导出
src=$(ss_skill eagle-sfx) || exit 1
rsync -a --delete $EX --exclude index.json "$src/" "$R/skills/eagle-sfx/"

# aigc 工作区的规则文件
mkdir -p "$R/agents/aigc-workspace"
cp "$HOME/claude/aigc/CLAUDE.md" "$R/agents/aigc-workspace/CLAUDE.md"

cd "$R"
git add -A
git diff --cached --quiet && { echo "没有改动"; exit 0; }
git commit -q -m "${1:-同步 skill}"
git push -q
echo "已推送：$(git log -1 --format='%h %s')"
