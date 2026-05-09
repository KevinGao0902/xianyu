#!/bin/bash
# 闲鱼自动回复系统停止脚本

echo "正在停止闲鱼自动回复系统..."

if pgrep -f "Start.py" > /dev/null; then
    # 先停掉项目内由 execjs/扫码链路拉起的 node 子进程。
    # 如果先杀 Python，node 往已关闭的 stdout/pipe 写数据时会抛 write EPIPE。
    pkill -TERM -f "utils/gen_tfstk.js" 2>/dev/null || true
    pkill -TERM -f "utils/et_f.js" 2>/dev/null || true
    sleep 0.3

    pkill -TERM -f "Start.py"
    sleep 2

    if pgrep -f "Start.py" > /dev/null; then
        echo "正在强制停止..."
        pkill -9 -f "Start.py"
    fi

    # 兜底清理 lite 扫码登录可能残留的 node 子进程
    pkill -9 -f "utils/gen_tfstk.js" 2>/dev/null || true
    pkill -9 -f "utils/et_f.js" 2>/dev/null || true

    echo "已停止"
else
    echo "程序未在运行"
fi
