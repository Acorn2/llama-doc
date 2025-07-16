#!/bin/bash

echo "🚀 启动PDF文献分析智能体系统（本地开发环境 - SQLite）..."

# 调用环境设置脚本
./scripts/setup_env.sh development

# 读取设置结果
if [ -f "/tmp/setup_env_result" ]; then
    source /tmp/setup_env_result
    rm -f /tmp/setup_env_result
fi

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python3"
    exit 1
fi

# 创建和激活虚拟环境
if [ ! -d "venv" ]; then
    echo "🐍 创建Python虚拟环境..."
    python3 -m venv venv
fi

echo "📦 激活虚拟环境..."
source venv/bin/activate

if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ 虚拟环境激活失败"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 检查关键依赖
echo "🔍 检查关键依赖..."
python -c "
try:
    import fastapi, dashscope, langchain, chromadb, sqlalchemy
    print('✅ 所有关键依赖检查通过')
except ImportError as e:
    print(f'❌ 依赖检查失败: {e}')
    exit(1)
" || exit 1

# 初始化数据库
echo "🗄️  初始化SQLite数据库..."
python -c "
from app.database import create_tables, get_db_info
import logging
logging.basicConfig(level=logging.INFO)
print('数据库配置信息:', get_db_info())
create_tables()
print('✅ SQLite数据库初始化完成')
" || exit 1

# 启动服务
echo "🚀 启动API服务..."
uvicorn app.main:app --reload --host 0.0.0.0 --port ${API_PORT:-8000} &
API_PID=$!

echo "✅ 本地开发环境启动完成！"
echo ""
echo "🗄️  数据库: SQLite (本地文件: ./document_analysis.db)"
echo "🔗 后端API: http://localhost:${API_PORT:-8000}"
echo "📚 API文档: http://localhost:${API_PORT:-8000}/docs"
echo "🔧 数据库信息: http://localhost:${API_PORT:-8000}/api/v1/database/info"
echo ""
echo "按 Ctrl+C 停止服务"

trap "echo '🛑 正在停止服务...'; kill $API_PID 2>/dev/null; exit" INT
wait 