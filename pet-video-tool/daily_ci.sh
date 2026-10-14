#!/usr/bin/env bash
# 云端每日出片：content/<日期>.json 有排好的剧本就用它，没有就现写一条（有 LLM_API_KEY 用大模型，否则用内置剧本）。
set -euo pipefail
cd "$(dirname "$0")"

DATE="${1:-}"
DATE="${DATE:-$(TZ=Asia/Shanghai date +%F)}"
SCRIPT="content/$DATE.json"

if [ -f "$SCRIPT" ]; then
  python3 make_video.py --from-script "$SCRIPT" --date "$DATE"
else
  python3 make_video.py --date "$DATE"
  NEW_SCRIPT=1
fi

OUT="$(ls -d output/"$DATE"_* | head -1)"
[ "${NEW_SCRIPT:-}" = 1 ] && cp "$OUT/script.json" "$SCRIPT"

rm -rf release && mkdir -p release
cp "$OUT/final.mp4" "release/tuantuan-$DATE.mp4"
cp "$OUT/cover.jpg" "release/tuantuan-$DATE-cover.jpg"
if [ "${NEW_SCRIPT:-}" = 1 ] && [ -z "${LLM_API_KEY:-}" ]; then
  echo "> **注意：没有设置 LLM_API_KEY，也没有排好的剧本，这条用的是内置剧本，可能和以前发过的重复，建议不要发布。**" > release/notes.md
  echo >> release/notes.md
fi
python3 - "$OUT/script.json" "$DATE" >> release/notes.md <<'EOF'
import datetime as dt, json, sys
s = json.load(open(sys.argv[1], encoding="utf-8"))
day = dt.date.fromisoformat(sys.argv[2])
slot = {5: "10:00", 6: "21:00", 2: "12:00"}.get(day.weekday(), "18:30")
print(f"**标题**：{s['title']}\n")
print(f"**发布文案**（直接复制）：\n\n{s['title']}｜{s.get('caption', '')}\n\n" + " ".join("#" + t for t in s.get("tags", [])) + "\n")
print(f"**建议发布时间**：{sys.argv[2]} 周{'一二三四五六日'[day.weekday()]} {slot}\n")
print("发布时记得在「作品声明」里勾选「内容由 AI 生成」。\n")
print("**台词**：\n\n" + "\n".join(f"{i}. {l['text']}" for i, l in enumerate(s["lines"], 1)))
open("release/title.txt", "w", encoding="utf-8").write(s["title"])
EOF

echo "date=$DATE" >> "${GITHUB_OUTPUT:-/dev/null}"
echo "new_script=${NEW_SCRIPT:-0}" >> "${GITHUB_OUTPUT:-/dev/null}"
echo "[完成] $OUT"
