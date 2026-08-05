#!/bin/bash
# 《反方向的钟》多模态分析 Web 应用便捷启动脚本
#
# 用法：
#   ./run_webapp.sh          启动 Flask 后端应用
#
# 首次运行前请先安装依赖：
#   pip install -r webapp/requirements.txt
#
# 生成静态展示页（双击即开的 sample）：
#   cd static_showcase && python build.py

cd "$(dirname "$0")/webapp"

echo "================================================"
echo "  《反方向的钟》多模态分析 Web 应用"
echo "  访问 http://127.0.0.1:5000"
echo "  按 Ctrl+C 停止"
echo "================================================"

python3 app.py
