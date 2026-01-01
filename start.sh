#!/bin/bash

# Configuration
venv_dir="venv"
marker_file="${venv_dir}/.installed"
req_file="requirements.txt"
PID_FILE=".running_pid"

echo "🚀 启动PDF文献分析智能体系统..."

# Clean up function
cleanup_and_exit() {
    echo ""
    echo "🛑 正在停止服务..."
    
    if [ ! -z "$API_PID" ]; then
        if kill -0 $API_PID 2>/dev/null; then
            echo "   发送停止信号给 API 进程 $API_PID..."
            kill $API_PID
        fi
    fi

    if [ ! -z "$CELERY_PID" ]; then
        if kill -0 $CELERY_PID 2>/dev/null; then
            echo "   发送停止信号给 Celery Worker $CELERY_PID..."
            kill $CELERY_PID
        fi
    fi
    
    # Wait for processes to exit
    sleep 2
    
    # Force kill if still running
    [ ! -z "$API_PID" ] && kill -9 $API_PID 2>/dev/null || true
    [ ! -z "$CELERY_PID" ] && kill -9 $CELERY_PID 2>/dev/null || true
    
    # Clean up pid files
    rm -f "$PID_FILE"
    rm -f ".celery_pid"
    exit 0
}

# Trap signals
trap cleanup_and_exit INT TERM

# Check for force install flag
FORCE_INSTALL=false
while getopts "f" opt; do
  case $opt in
    f) FORCE_INSTALL=true ;;
    *) ;;
  esac
done

# Basic checks
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3"
    exit 1
fi

# Setup Environment
if [ -f "./scripts/setup_env.sh" ]; then
    ./scripts/setup_env.sh production > /dev/null 2>&1
    if [ -f "/tmp/setup_env_result" ]; then
        source /tmp/setup_env_result
        rm -f /tmp/setup_env_result
    fi
fi

# Load env vars
if [ -f ".env.production" ]; then
    set -a
    source .env.production
    set +a
fi

# Virtual Environment & Dependencies
if [ ! -d "$venv_dir" ]; then
    echo "� 创建虚拟环境..."
    python3 -m venv "$venv_dir"
fi

source "$venv_dir/bin/activate"

# Check if need to install dependencies
INSTALL_NEEDED=true
if [ "$FORCE_INSTALL" = "false" ] && [ -f "$marker_file" ]; then
    # Function to check file modification times
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        req_time=$(stat -f %m "$req_file")
        mark_time=$(stat -f %m "$marker_file")
    else
        # Linux
        req_time=$(stat -c %Y "$req_file")
        mark_time=$(stat -c %Y "$marker_file")
    fi
    
    if [ $req_time -le $mark_time ]; then
        INSTALL_NEEDED=false
        echo "✅ 依赖已安装 (使用 -f 强制重新安装)"
    fi
fi

if [ "$INSTALL_NEEDED" = "true" ]; then
    echo "📦 安装/更新依赖..."
    pip install -r "$req_file"
    pip install psycopg2-binary
    touch "$marker_file"
    echo "✅ 依赖安装完成"
else
    # Quick check for critical imports only if we skipped install
    # Just to be safe, but silent unless error
    python3 -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null || {
        echo "⚠️ 发现依赖缺失，尝试重新安装..."
        pip install -r "$req_file"
        pip install psycopg2-binary
        touch "$marker_file"
    }
fi

# Check Port
PORT=${API_PORT:-8000}
pid_on_port=$(lsof -t -i :$PORT 2>/dev/null)
if [ ! -z "$pid_on_port" ]; then
    echo "⚠️ 端口 $PORT 被进程 $pid_on_port 占用，尝试释放..."
    kill -9 $pid_on_port 2>/dev/null || true
    sleep 1
fi

# DB Connection Check (Simplified)
# Only show output if it fails, or if explicitly requested (or on install)
# To keep it fast, we skip this on regular runs unless user asks or install happened.
# Actually user said "too cumbersome", so skipping aggressive DB checks every time is good.
# But we should probably do a quick ping to ensure DB is up, otherwise uvicorn fails ugly.
if [ "$INSTALL_NEEDED" = "true" ]; then
    echo "🗄️  检查数据库连接..."
    python3 -c "
import os, psycopg2, sys
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        database=os.getenv('DB_NAME', 'document_analysis'),
        connect_timeout=3
    )
    conn.close()
    print('✅ 数据库连接正常')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    sys.exit(1)
" || exit 1

    # Initialize tables
    echo "� 初始化/更新数据库表..."
    python3 -c "from app.database import create_tables; create_tables()" > /dev/null 2>&1 || echo "⚠️ 表初始化警告 (非致命)"
fi

# Start Service
echo "🚀 启动API服务 (Port: $PORT)..."
if [ "$ENVIRONMENT" = "production" ]; then
    uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 &
else
    uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload &
fi

API_PID=$!
echo $API_PID > "$PID_FILE"

# Start Celery Worker
echo "⚙️  启动 Celery Worker..."
celery -A app.celery_app worker --loglevel=info > logs/celery.log 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > ".celery_pid"

# Wait for startup
sleep 2

if kill -0 $API_PID 2>/dev/null; then
    echo ""
    echo "✅ 服务已启动!"
    echo "🔗 API地址: http://localhost:$PORT"
    echo "� 文档地址: http://localhost:$PORT/docs"
    echo ""
    echo "按 Ctrl+C 停止服务"
    
    wait $API_PID
else
    echo "❌ 服务启动失败"
    exit 1
fi