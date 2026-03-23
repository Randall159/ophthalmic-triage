#!/bin/bash
# ────────────────────────────────────────────────
# Ophthalmic Triage System — Quick Start
# ────────────────────────────────────────────────

set -e

echo ""
echo "👁️  Ophthalmic Triage System"
echo "═══════════════════════════════════════"

# 1. Check ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "❌  请先设置 ANTHROPIC_API_KEY 环境变量："
  echo "    export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi
echo "✅  ANTHROPIC_API_KEY 已配置"

# 2. Install dependencies
cd "$(dirname "$0")/backend"
echo ""
echo "📦 安装 Python 依赖…"
pip install -r requirements.txt -q

# 3. Start backend
echo ""
echo "🚀 启动后端服务 (http://localhost:8000)…"
echo ""
echo "📊 可视化页面：用浏览器打开 visualization.html"
echo "💬 患者界面：  用浏览器打开 frontend/index.html"
echo ""
echo "按 Ctrl+C 停止服务"
echo "═══════════════════════════════════════"
echo ""

python main.py
