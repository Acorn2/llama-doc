#!/bin/bash

echo "🚀 启动PDF文献分析智能体系统（PostgreSQL环境）..."

# 调用环境设置脚本
./scripts/setup_env.sh production

# 读取设置结果
if [ -f "/tmp/setup_env_result" ]; then
    source /tmp/setup_env_result
    rm -f /tmp/setup_env_result
fi

# 加载环境变量
if [ -f ".env.production" ]; then
    echo "📋 加载生产环境变量..."
    export $(grep -v '^#' .env.production | xargs)
    echo "✅ 环境变量加载完成"
fi

# 显示数据库配置（调试用）
echo "🔧 数据库配置："
echo "  DB_HOST: ${DB_HOST:-未设置}"
echo "  DB_PORT: ${DB_PORT:-未设置}"
echo "  DB_NAME: ${DB_NAME:-未设置}"
echo "  DB_USER: ${DB_USER:-未设置}"

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

# 安装PostgreSQL依赖
echo "📦 安装PostgreSQL依赖..."
pip install psycopg2-binary

# 检查关键依赖
echo "🔍 检查关键依赖..."
python -c "
try:
    import fastapi, dashscope, langchain, sqlalchemy, psycopg2
    print('✅ 所有关键依赖检查通过')
except ImportError as e:
    print(f'❌ 依赖检查失败: {e}')
    exit(1)
" || exit 1

# 测试数据库连接（不创建数据库）
echo "🗄️  测试PostgreSQL连接..."
python -c "
import os
import psycopg2

# 从环境变量获取数据库配置
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', 'postgres')
db_name = os.getenv('DB_NAME', 'document_analysis')

print(f'尝试连接到: {db_host}:{db_port}')
print(f'用户: {db_user}')
print(f'数据库: {db_name}')

try:
    # 直接连接到目标数据库
    conn = psycopg2.connect(
        host=db_host,
        port=int(db_port),
        user=db_user,
        password=db_password,
        database=db_name,
        connect_timeout=10
    )
    
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()
    print(f'✅ PostgreSQL连接成功: {version[0][:50]}...')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    print('请检查：')
    print('1. 云服务器PostgreSQL服务是否运行')
    print('2. 防火墙是否开放5432端口')
    print('3. 数据库用户名密码是否正确')
    print('4. 数据库是否已创建')
    exit(1)
" || exit 1

# 初始化数据库表
echo "🗄️  初始化PostgreSQL数据库表..."
python -c "
from app.database import create_tables, get_db_info, get_db_session
import logging
logging.basicConfig(level=logging.INFO)

try:
    print('数据库配置信息:', get_db_info())
    
    # 测试连接
    db = get_db_session()
    db.close()
    print('✅ 数据库连接测试成功')
    
    # 创建表
    create_tables()
    print('✅ PostgreSQL数据库表初始化完成')
    
except Exception as e:
    print(f'❌ 数据库初始化失败: {e}')
    exit(1)
" || exit 1

# 启动服务
echo "🚀 启动API服务..."
uvicorn app.main:app --reload --host 0.0.0.0 --port ${API_PORT:-8000} &
API_PID=$!

# 等待服务启动
echo "⏳ 等待API服务启动..."
sleep 3

# 检查服务状态
if kill -0 $API_PID 2>/dev/null; then
    echo "✅ PostgreSQL环境启动完成！"
    echo ""
    echo "🗄️  数据库: PostgreSQL (${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-document_analysis})"
    echo "🔗 后端API: http://localhost:${API_PORT:-8000}"
    echo "📚 API文档: http://localhost:${API_PORT:-8000}/docs"
    echo "🔧 数据库信息: http://localhost:${API_PORT:-8000}/api/v1/database/info"
    echo ""
    echo "按 Ctrl+C 停止服务"
else
    echo "❌ API服务启动失败"
    exit 1
fi

trap "echo '🛑 正在停止服务...'; kill $API_PID 2>/dev/null; exit" INT
wait 