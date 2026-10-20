#!/usr/bin/env bash
# 每日自动更新：在 Linux 服务器上刷新商人定位数据。
# 物品全集来自本地 Item.csv（wow.tools 导出），商人/坐标来自 Wowhead。
#
# 环境变量：
#   PY              python 解释器（默认 python3，建议指向 venv）
#   ITEM_CSV        Item.csv 在服务器上的路径（默认 /data/item.csv）
#   SOLD_BY_MAX_AGE wowhead 缓存页过期天数（默认 7；0=永不重抓）
#   DF_PROXY        服务器访问 wowhead/nether 的代理（默认空=直连）
#   PUSH=1          更新后 git commit + push（需在仓库内且已配好远端）
#
# 用法：放到 crontab 或 systemd timer，见 scripts/README.md「Linux 服务器每日更新」。
set -u
cd "$(dirname "$0")/.." || exit 1

PY="${PY:-python3}"
ITEM_CSV="${ITEM_CSV:-/data/item.csv}"
LOG_DIR=scripts/logs
mkdir -p "$LOG_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$LOG_DIR/gen_vendors_$STAMP.log"

echo "[$(date '+%F %T')] start（item.csv=$ITEM_CSV）" | tee "$LOG"

"$PY" scripts/gen_vendors.py \
  --item-db2 "$ITEM_CSV" \
  --headless \
  --soldby-max-age "${SOLD_BY_MAX_AGE:-7}" \
  >>"$LOG" 2>&1
RC=$?
echo "[$(date '+%F %T')] exit=$RC" | tee -a "$LOG"

if [ "$RC" -eq 0 ] && [ "${PUSH:-0}" = "1" ]; then
  git add scripts/out/vendors.csv scripts/out/npcs.csv \
    && git commit -m "vendor data: daily refresh $STAMP" >>"$LOG" 2>&1 \
    && git push >>"$LOG" 2>&1
fi

# 只保留最近 14 份日志
ls -t "$LOG_DIR"/gen_vendors_*.log 2>/dev/null | tail -n +15 | xargs -r rm -f
exit $RC
