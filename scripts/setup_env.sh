#!/bin/bash

# 环境设置脚本 - 统一管理不同环境的配置和服务检查

set -e  # 遇到错误立即停止

ENVIRONMENT=${1:-development}

echo "🔧 设置 $ENVIRONMENT 环境..."

# 检查环境参数
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "production" && "$ENVIRONMENT" != "local" ]]; then
    echo "❌ 无效的环境类型: $ENVIRONMENT"
    echo "请使用: development (SQLite) | production (PostgreSQL) | local (本地SQLite)"
    exit 1
fi

# 设置环境配置文件和环境变量
if [ "$ENVIRONMENT" = "development" ]; then
    ENV_FILE=".env.development"
    echo "📋 使用开发环境配置 (SQLite)"
    
    # 导出SQLite环境变量
    export ENVIRONMENT=development
    export DB_TYPE=sqlite
    export DATABASE_URL=sqlite:///./document_analysis.db
    export API_PORT=8000
    
elif [ "$ENVIRONMENT" = "production" ]; then
    ENV_FILE=".env.production"
    echo "📋 使用生产环境配置 (PostgreSQL)"
    
    # 加载生产环境配置
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
        echo "✅ 已加载生产环境变量"
    fi
    
elif [ "$ENVIRONMENT" = "local" ]; then
    ENV_FILE=".env.development"
    echo "📋 使用本地开发配置 (SQLite)"
    
    # 导出本地SQLite环境变量
    export ENVIRONMENT=development
    export DB_TYPE=sqlite
    export DATABASE_URL=sqlite:///./document_analysis.db
    export API_PORT=8000
fi

# 复制环境配置文件到.env（保持向后兼容）
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" ".env"
    echo "✅ 已复制 $ENV_FILE 到 .env"
else
    echo "❌ 配置文件 $ENV_FILE 不存在"
    exit 1
fi

# 显示当前配置
echo "🔧 当前环境配置："
echo "  ENVIRONMENT: $ENVIRONMENT"
echo "  DB_TYPE: ${DB_TYPE:-未设置}"
if [ "$DB_TYPE" = "sqlite" ]; then
    echo "  DATABASE_URL: ${DATABASE_URL:-未设置}"
else
    echo "  DB_HOST: ${DB_HOST:-未设置}"
    echo "  DB_PORT: ${DB_PORT:-未设置}"
    echo "  DB_NAME: ${DB_NAME:-未设置}"
fi
echo "  API_PORT: ${API_PORT:-8000}"


mkdir -p uploads vector_db logs


if [ "$ENVIRONMENT" = "production" ]; then
    echo "🔍 检查生产环境配置..."
    
    # 检查PostgreSQL服务
    if command -v pg_isready &> /dev/null; then
        if pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432}; then
            echo "✅ PostgreSQL服务运行正常"
        else
            echo "❌ PostgreSQL服务未运行"
            echo "请启动PostgreSQL服务："
            echo "  macOS: brew services start postgresql"
            echo "  Ubuntu: sudo systemctl start postgresql"
            exit 1
        fi
    else
        echo "⚠️  未找到pg_isready命令，请确保PostgreSQL服务已启动"
    fi
    
    # 检查生产环境配置
    if grep -q "your_production_password" .env 2>/dev/null; then
        echo "⚠️  警告: 请修改生产环境数据库密码"
    fi
    
    if grep -q "your-production-" .env 2>/dev/null; then
        echo "⚠️  警告: 请配置生产环境API密钥"
    fi
    
    if grep -q "your-super-secret-key-here" .env 2>/dev/null; then
        echo "⚠️  警告: 请修改生产环境SECRET_KEY"
    fi
fi

echo "✅ 环境设置完成: $ENVIRONMENT"

# 返回环境信息供调用脚本使用
echo "ENV_TYPE=$ENVIRONMENT" > /tmp/setup_env_result
echo "DB_TYPE=${DB_TYPE}" >> /tmp/setup_env_result
echo "API_PORT=${API_PORT}" >> /tmp/setup_env_result

echo ""
echo "下一步："
if [ "$ENVIRONMENT" = "development" ]; then
    echo "  开发环境: ./start_simple.sh"
elif [ "$ENVIRONMENT" = "production" ]; then
    echo "  生产环境: ./start.sh"
fi 