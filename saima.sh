#!/bin/bash
# 赛马智能体 - 静默版（无输出）
# 所有输出重定向到 /dev/null

set -e

WORD_FILE="${1:-}"

if [ -z "$WORD_FILE" ]; then
    echo "用法: $0 <word文件>" >&2
    exit 1
fi

if [ ! -f "$WORD_FILE" ]; then
    echo "错误: 文件不存在: $WORD_FILE" >&2
    exit 1
fi

# 静默执行（所有输出重定向）
python3 /home/openclaw/niuniu/code/saima-agent/saima_main.py "$WORD_FILE" > /dev/null 2>&1

# 执行匹配
python3 /home/openclaw/niuniu/code/saima-agent/match.py > /dev/null 2>&1

echo "完成"
