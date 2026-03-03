#!/bin/bash
# 赛马智能体 - 完整流程启动脚本（静默版）

TASK_ID=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/saima_${TASK_ID}.log"
STATUS_FILE="/tmp/saima_status.json"

# 每次启动前清空 status 文件，确保是最新的
> "$STATUS_FILE"

# 静默启动 - 所有输出重定向
cd /home/openclaw/niuniu/code/saima-agent

# Step 1: 需求拆分（saima_main.py）
# 输入文件：最新上传的 .docx 文件
WORD_FILE=$(ls -t /home/openclaw/niuniu/saima/input/*.docx | head -1)
if [ -z "$WORD_FILE" ]; then
    echo "错误：未找到 .docx 文件"
    exit 1
fi

echo "使用文件: $WORD_FILE"

# 记录拆分开始时间
SPLIT_START=$(date +%s)

# 需求拆分
python3 saima_main.py "$WORD_FILE" > /dev/null 2>&1

# 记录拆分结束时间
SPLIT_END=$(date +%s)
SPLIT_TIME=$((SPLIT_END - SPLIT_START))

echo "需求拆分耗时: ${SPLIT_TIME}秒"

# 更新状态文件（添加拆分耗时）
cat > "$STATUS_FILE" << JSON
{
  "status": "running",
  "stage": "需求拆分完成",
  "split_time": "${SPLIT_TIME}秒"
}
JSON

# Step 2: 需求匹配（saima_background.py）
nohup python3 saima_background.py > /dev/null 2>&1 &

PID=$!
echo "PID: $PID"
