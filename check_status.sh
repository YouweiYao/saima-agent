#!/bin/bash
# 赛马智能体 - 状态检查脚本

STATUS_FILE="/tmp/saima_status.json"

if [ -f "$STATUS_FILE" ]; then
    cat "$STATUS_FILE"
else
    echo '{"status": "no_task"}'
fi
