# 🤖 智能文档分析与知识管理平台

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.0+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.2.0+-orange.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-blue.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-1.7+-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**基于LangChain Agent的企业级智能文档分析与知识共享平台**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [API文档](#-api接口) • [架构设计](#-系统架构) • [部署指南](#-部署指南)

</div>

## 📖 项目简介

智能文档分析与知识管理平台是一个基于FastAPI的现代化企业级智能文档分析系统，采用清晰的分层架构设计，集成了**LangChain Agent**智能体能力，提供完整的用户管理、文档处理、知识库管理、智能对话等功能，支持私有知识库和公开知识库共享。

### 🎯 核心亮点

- 🤖 **智能Agent系统**: 基于LangChain的完整Agent实现，支持文档分析、知识搜索、摘要生成等工具链式调用
- 👥 **完整用户系统**: JWT认证、用户注册登录、权限管理、活动记录追踪
- 🏗️ **现代化架构**: 清晰的4层分层架构，依赖注入系统，支持高并发和可扩展性
- 💬 **流式对话体验**: 支持实时流式AI对话，提供类ChatGPT的用户体验
- 📚 **知识库生态**: 私有知识库管理 + 公开知识库分享，构建知识共享社区
- 🔄 **多存储策略**: 腾讯云COS + 本地存储自动降级，确保数据安全
- 📊 **企业级特性**: 健康检查、性能监控、缓存优化、异常处理、用户活动追踪

## ✨ 功能特性

### 👥 用户管理系统
- **多方式注册登录**: 支持邮箱、手机号注册登录，JWT认证机制
- **权限管理**: 普通用户与超级用户权限体系，细粒度权限控制
- **用户资料管理**: 完整的用户信息管理，头像上传，个人设置
- **活动记录追踪**: 自动记录用户操作行为，支持活动统计和分析
- **仪表板统计**: 用户数据统计，文档、知识库、对话等多维度数据展示

### 🤖 智能Agent能力
- **智能对话**: 支持多轮对话和上下文理解，Agent模式与普通对话模式切换
- **文档分析**: 深度文档理解和结构化信息提取，支持复杂查询分析
- **知识搜索**: 语义理解搜索和智能结果筛选，支持跨文档检索
- **摘要生成**: 多层次摘要生成，学术规范格式，支持自定义摘要需求
- **工具协作**: 多工具链式调用完成复杂任务，支持自定义工具扩展

### 📄 文档处理
- **多格式支持**: PDF、TXT、DOC、DOCX文档处理，智能格式识别
- **智能解析**: 基于PyMuPDF和unstructured的文档解析，保持文档结构
- **向量化存储**: Qdrant向量数据库存储文档向量，支持高效相似度搜索
- **重复检测**: MD5文件重复检测机制，避免重复上传
- **异步处理**: 后台异步文档处理队列，支持大文件处理和批量操作
- **用户隔离**: 每个用户只能访问自己的文档，确保数据安全

### 💾 知识库管理
- **私有知识库**: 完整的知识库创建、查询、更新、删除，支持个人知识管理
- **公开知识库**: 知识库公开分享功能，构建知识共享社区
- **标签分类**: 知识库标签系统，支持分类管理和搜索过滤
- **社交功能**: 知识库点赞、访问统计、热门排序等社交化功能
- **权限控制**: 灵活的权限管理，支持知识库公开/私有状态切换
- **文档关联**: 灵活的文档与知识库关联管理，支持批量操作

### 🔄 对话管理
- **对话历史**: 完整的对话记录存储与检索，支持对话搜索和导出
- **流式输出**: 实时流式AI回复，支持SSE，提供类ChatGPT体验
- **上下文维护**: 多轮对话上下文管理，智能记忆机制
- **对话模式**: Agent模式与普通对话模式，适应不同使用场景
- **权限隔离**: 用户对话记录完全私有，即使使用公开知识库

### 🔧 系统管理
- **健康监控**: 完整的系统健康检查，数据库、向量库、存储状态监控
- **性能优化**: Agent缓存管理，向量同步服务，异步任务处理
- **存储管理**: 本地存储 + 腾讯云COS双存储策略，自动降级机制
- **日志系统**: 结构化日志记录，支持日志轮转和分析

## 🏗️ 系统架构

### 分层架构设计
```
┌─────────────────────────────────────────────────────────────┐
│                        API层 (API Layer)                    │
│  FastAPI路由 • JWT认证 • 请求验证 • 响应格式化 • 异常处理    │
├─────────────────────────────────────────────────────────────┤
│                      服务层 (Service Layer)                  │
│  用户管理 • Agent服务 • 对话管理 • 知识库管理 • 文档处理     │
├─────────────────────────────────────────────────────────────┤
│                      核心层 (Core Layer)                     │
│  LangChain Agent • 文档解析 • 向量化 • LLM适配 • 缓存管理   │
├─────────────────────────────────────────────────────────────┤
│                      数据层 (Data Layer)                     │
│  PostgreSQL • Qdrant • Redis • 文件存储 • 腾讯云COS        │
└─────────────────────────────────────────────────────────────┘
```

### 项目结构
```
intelligent-document-platform/
├── app/                          # 应用主目录
│   ├── main.py                   # FastAPI应用入口
│   ├── database.py               # 数据库模型和连接
│   ├── schemas.py                # Pydantic数据模型
│   ├── logging_config.py         # 日志配置
│   │
│   ├── api/                      # API层
│   │   ├── exception_handlers.py # 异常处理器
│   │   └── health.py            # 健康检查接口
│   │
│   ├── routers/                  # 路由模块
│   │   ├── user_router.py        # 用户管理路由
│   │   ├── document_routes.py    # 文档管理路由
│   │   ├── knowledge_base_router.py # 知识库路由
│   │   ├── conversation_routes.py   # 对话管理路由
│   │   ├── agent_router.py       # Agent智能体路由
│   │   ├── system_router.py      # 系统信息路由
│   │   └── test_routes.py        # 测试接口路由
│   │
│   ├── services/                 # 服务层
│   │   ├── user_service.py       # 用户服务
│   │   ├── agent_service.py      # Agent服务
│   │   ├── conversation_service.py # 对话服务
│   │   ├── knowledge_base_service.py # 知识库服务
│   │   ├── document_service.py   # 文档处理服务
│   │   ├── vector_sync_service.py # 向量同步服务
│   │   └── langchain_adapter.py  # LangChain适配器
│   │
│   ├── core/                     # 核心层
│   │   ├── langchain_agent.py    # LangChain Agent实现
│   │   ├── model_factory.py      # 模型工厂
│   │   ├── container.py          # 依赖注入容器
│   │   └── security.py           # 安全认证
│   │
│   ├── config/                   # 配置管理
│   │   └── settings.py           # 应用配置
│   │
│   ├── middleware/               # 中间件
│   │   └── error_handling.py     # 错误处理中间件
│   │
│   └── utils/                    # 工具模块
│       ├── download_manager.py   # 下载管理器
│       ├── file_utils.py         # 文件工具
│       └── activity_logger.py    # 活动记录器
│
├── docs/                         # 文档目录
│   ├── API接口文档-完整版.md      # API文档
│   ├── 后端服务完整接口文档-前端开发版.md
│   ├── 流式打字机效果使用指南.md
│   └── architecture/             # 架构文档
│
├── scripts/                      # 脚本目录
│   ├── test_dependencies.py      # 依赖测试脚本
│   ├── test_auth_debug.py        # 认证调试脚本
│   └── performance_analysis.py   # 性能分析脚本
│
├── tests/                        # 测试目录
├── logs/                         # 日志目录
├── uploads/                      # 上传文件目录
├── requirements.txt              # Python依赖
├── .env.development.example      # 开发环境配置示例
├── .env.production.example       # 生产环境配置示例
├── start.sh                      # 生产启动脚本
├── start_local.sh               # 本地启动脚本
└── README.md                     # 项目说明
```

### 核心技术栈
- **后端框架**: FastAPI 0.104.0+ + Uvicorn (ASGI服务器)
- **数据库**: PostgreSQL + SQLAlchemy 2.0+ (支持SQLite开发环境)
- **向量数据库**: Qdrant 1.7+ (高性能向量搜索)
- **AI框架**: LangChain 0.2.0+ + LangChain Community (Agent框架)
- **大语言模型**: 通义千问 + OpenAI GPT (多模型支持)
- **认证系统**: JWT + PyJWT (无状态认证)
- **文件存储**: 本地存储 + 腾讯云COS (双存储策略)
- **文档处理**: PyMuPDF + unstructured + python-docx (多格式解析)
- **缓存系统**: Redis + 内存缓存 (多层缓存策略)
- **监控工具**: 自定义健康检查 + 性能监控

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL 12+ (生产环境) / SQLite (开发环境)
- Qdrant 1.7+
- Redis 5.0+ (可选，用于缓存)
- 通义千问API Key 或 OpenAI API Key

### 1. 克隆项目
```bash
git clone https://github.com/your-username/pdf-analysis-service.git
cd pdf-analysis-service
```

### 2. 安装依赖
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
# 复制环境配置文件
cp .env.development.example .env.development

# 编辑配置文件，配置必要的环境变量
vim .env.development
```

**必需配置项**:
```bash
# 应用配置
APP_NAME="智能文档分析平台"
SECRET_KEY="your-production-secret-key-here"
DEBUG=true

# 数据库配置 (开发环境可使用SQLite)
DATABASE_URL="sqlite:///./document_analysis.db"
# 或 PostgreSQL: DATABASE_URL="postgresql://user:password@localhost:5432/dbname"

# Qdrant向量数据库
QDRANT_HOST="localhost"
QDRANT_PORT=6333

# 大语言模型配置 (至少配置一个)
DASHSCOPE_API_KEY="your_qwen_api_key"  # 通义千问
OPENAI_API_KEY="your_openai_api_key"   # OpenAI

# JWT配置
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7天

# 腾讯云COS配置 (可选)
COS_SECRET_ID="your_cos_secret_id"
COS_SECRET_KEY="your_cos_secret_key"
COS_REGION="ap-beijing"
COS_BUCKET="your-bucket-name"
```

### 4. 初始化数据库
```bash
# 数据库会在首次启动时自动创建表结构
# 如果使用PostgreSQL，请确保数据库已创建
```

### 5. 启动服务
```bash
# 开发模式启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 或使用启动脚本
chmod +x start_local.sh
./start_local.sh

# 生产环境启动
chmod +x start.sh
./start.sh
```

### 6. 访问服务
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

### 7. 创建第一个用户
```bash
# 通过API创建用户
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "admin123",
    "full_name": "管理员"
  }'
```

## 📡 API接口

### 👥 用户管理 (`/api/v1/users`)
```bash
# 用户认证
POST /api/v1/users/register          # 用户注册
POST /api/v1/users/login             # 用户登录
POST /api/v1/users/refresh           # 刷新Token

# 用户信息
GET /api/v1/users/me                 # 获取当前用户信息
PUT /api/v1/users/me                 # 更新当前用户信息

# 用户活动
GET /api/v1/users/activities         # 获取用户活动记录
GET /api/v1/users/activities/stats   # 获取活动统计
GET /api/v1/users/dashboard/stats    # 获取仪表板统计

# 用户管理 (仅超级用户)
GET /api/v1/users/                   # 获取用户列表
GET /api/v1/users/{user_id}          # 获取指定用户信息
PUT /api/v1/users/{user_id}          # 更新指定用户信息
DELETE /api/v1/users/{user_id}       # 禁用用户账户
```

### 📄 文档管理 (`/api/v1/documents`)
```bash
# 文档上传与管理 (需要认证)
POST /api/v1/documents/upload        # 上传文档
GET /api/v1/documents                # 获取用户文档列表
GET /api/v1/documents/{document_id}  # 获取文档详情
DELETE /api/v1/documents/{document_id} # 删除文档

# 文档状态与操作
GET /api/v1/documents/{document_id}/status    # 获取处理状态
GET /api/v1/documents/{document_id}/download  # 获取下载链接
POST /api/v1/documents/check-duplicate       # 检查重复文档
```

### 📚 知识库管理 (`/api/v1/knowledge-bases`)
```bash
# 知识库CRUD (需要认证)
POST /api/v1/knowledge-bases/        # 创建知识库
GET /api/v1/knowledge-bases/         # 获取用户可访问的知识库
GET /api/v1/knowledge-bases/public   # 获取公开知识库列表
GET /api/v1/knowledge-bases/{kb_id}  # 获取知识库详情
PUT /api/v1/knowledge-bases/{kb_id}  # 更新知识库
DELETE /api/v1/knowledge-bases/{kb_id} # 删除知识库

# 知识库社交功能
POST /api/v1/knowledge-bases/{kb_id}/like    # 切换点赞状态
POST /api/v1/knowledge-bases/{kb_id}/access  # 记录访问行为

# 文档关联管理
POST /api/v1/knowledge-bases/{kb_id}/documents/{document_id}   # 添加文档
DELETE /api/v1/knowledge-bases/{kb_id}/documents/{document_id} # 移除文档
GET /api/v1/knowledge-bases/{kb_id}/documents                 # 列出文档

# 知识库搜索
POST /api/v1/knowledge-bases/{kb_id}/search  # 搜索知识库内容
```

### 🤖 智能Agent (`/api/v1/agent`)
```bash
# Agent智能对话 (需要认证)
POST /api/v1/agent/chat              # Agent对话
POST /api/v1/agent/chat/stream       # 流式Agent对话

# Agent分析功能
POST /api/v1/agent/analyze           # 文档分析
POST /api/v1/agent/search            # 知识搜索
POST /api/v1/agent/summary           # 生成摘要

# Agent管理
GET /api/v1/agent/history/{kb_id}    # 获取对话历史
DELETE /api/v1/agent/memory/{kb_id}  # 清除对话记忆
DELETE /api/v1/agent/cache           # 清除Agent缓存
GET /api/v1/agent/status/{kb_id}     # 获取Agent状态
```

### 💬 对话管理 (`/api/v1/conversations`)
```bash
# 对话管理 (需要认证)
POST /api/v1/conversations/          # 创建对话
GET /api/v1/conversations/           # 获取对话列表
GET /api/v1/conversations/{conversation_id}  # 获取对话详情
PUT /api/v1/conversations/{conversation_id}  # 更新对话
DELETE /api/v1/conversations/{conversation_id} # 删除对话

# 对话交互
POST /api/v1/conversations/chat      # 普通对话
POST /api/v1/conversations/chat/stream # 流式对话
POST /api/v1/conversations/{conversation_id}/chat/stream # 指定对话流式聊天

# 消息管理
GET /api/v1/conversations/{conversation_id}/messages  # 获取消息历史
POST /api/v1/conversations/{conversation_id}/messages # 添加消息
```

### 🔧 系统管理 (`/api/v1/system`)
```bash
# 系统监控 (无需认证)
GET /health                          # 基础健康检查
GET /api/v1/system/health           # 详细健康检查
GET /api/v1/system/models/info      # 获取模型信息

# 测试接口 (开发环境)
GET /api/v1/test/health             # 测试健康状态
GET /api/v1/test/database           # 测试数据库连接
```

## 🔧 配置说明

### 环境变量配置

**基础配置**:
```bash
# 应用配置
APP_NAME="智能文档分析平台"
VERSION="1.0.0"
DEBUG=true
ENVIRONMENT="development"

# 安全配置
SECRET_KEY="your-production-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7天

# 数据库配置
DATABASE_URL="postgresql://user:password@localhost:5432/document_analysis"
# 或开发环境: DATABASE_URL="sqlite:///./document_analysis.db"

# Qdrant向量数据库
QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_API_KEY=""
QDRANT_COLLECTION="documents"
```

**AI模型配置**:
```bash
# 通义千问配置
QWEN_API_KEY="your_qwen_api_key"
QWEN_MODEL="qwen-turbo"

# OpenAI配置
OPENAI_API_KEY="your_openai_api_key"
OPENAI_MODEL="gpt-3.5-turbo"
OPENAI_BASE_URL=""  # 可选，自定义API端点

# 默认LLM类型
DEFAULT_LLM_TYPE="qwen"
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

**存储配置**:
```bash
# 本地存储
UPLOAD_DIR="uploads"
MAX_FILE_SIZE=52428800  # 50MB
ALLOWED_EXTENSIONS=["pdf","txt","docx","md"]

# 腾讯云COS配置 (可选)
COS_SECRET_ID="your_cos_secret_id"
COS_SECRET_KEY="your_cos_secret_key"
COS_REGION="ap-beijing"
COS_BUCKET="your-bucket-name"
```

**Agent配置**:
```bash
# Agent缓存配置
AGENT_ENABLE_CACHE=true
AGENT_CACHE_TTL=3600
AGENT_MAX_CACHE_SIZE=100

# Agent执行配置
AGENT_ENABLE_MEMORY=true
AGENT_MAX_MEMORY_LENGTH=20
AGENT_MAX_ITERATIONS=5
AGENT_TIMEOUT=60
```

**日志配置**:
```bash
# 日志配置
LOG_LEVEL="INFO"
LOG_FILE_PATH="logs/app.log"
LOG_MAX_FILE_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

## 📊 使用示例

### 用户注册与登录
```python
import requests

# 用户注册
register_response = requests.post("http://localhost:8000/api/v1/users/register", json={
    "username": "张三",
    "email": "zhangsan@example.com",
    "password": "password123",
    "full_name": "张三"
})
print("注册成功:", register_response.json())

# 用户登录
login_response = requests.post("http://localhost:8000/api/v1/users/login", json={
    "login_credential": "zhangsan@example.com",
    "password": "password123"
})
token_data = login_response.json()
access_token = token_data["access_token"]

# 设置认证头
headers = {"Authorization": f"Bearer {access_token}"}
```

### 文档上传与知识库管理
```python
# 上传文档 (需要认证)
with open('document.pdf', 'rb') as f:
    upload_response = requests.post(
        "http://localhost:8000/api/v1/documents/upload",
        files={"file": f},
        headers=headers
    )
    document_id = upload_response.json()["document_id"]

# 创建私有知识库
kb_response = requests.post("http://localhost:8000/api/v1/knowledge-bases/", 
    json={
        "name": "我的私有知识库",
        "description": "个人学习资料",
        "is_public": False,
        "tags": ["学习", "资料"]
    },
    headers=headers
)
kb_id = kb_response.json()["id"]

# 添加文档到知识库
requests.post(
    f"http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/{document_id}",
    headers=headers
)

# 设置知识库为公开
requests.put(f"http://localhost:8000/api/v1/knowledge-bases/{kb_id}",
    json={
        "is_public": True,
        "public_description": "分享给大家的学习资料"
    },
    headers=headers
)
```

### Agent智能对话
```python
# Agent智能对话
agent_response = requests.post("http://localhost:8000/api/v1/agent/chat", 
    json={
        "kb_id": kb_id,
        "message": "请分析这个文档的主要观点",
        "use_agent": True,
        "llm_type": "qwen"
    },
    headers=headers
)
print("Agent回复:", agent_response.json())

# 文档分析
analysis_response = requests.post("http://localhost:8000/api/v1/agent/analyze",
    json={
        "kb_id": kb_id,
        "query": "请提取文档中的关键信息",
        "llm_type": "qwen"
    },
    headers=headers
)
print("分析结果:", analysis_response.json())

# 生成摘要
summary_response = requests.post("http://localhost:8000/api/v1/agent/summary",
    json={
        "kb_id": kb_id,
        "llm_type": "qwen"
    },
    headers=headers
)
print("文档摘要:", summary_response.json())
```

### 流式对话体验
```javascript
// 使用fetch进行流式对话
async function streamChat(message, kbId, token) {
    const response = await fetch('/api/v1/conversations/chat/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            kb_id: kbId,
            message: message,
            use_agent: true
        })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                if (data.is_final) {
                    console.log('对话完成:', data);
                } else {
                    console.log('接收内容:', data.chunk);
                    // 在页面上显示内容
                    displayMessage(data.chunk);
                }
            }
        }
    }
}

// 使用示例
streamChat("请介绍一下这个文档的内容", "your_kb_id", "your_token");
```

### 公开知识库浏览
```python
# 获取公开知识库列表 (无需认证)
public_kbs = requests.get("http://localhost:8000/api/v1/knowledge-bases/public", 
    params={
        "search": "机器学习",
        "tags": "AI,深度学习",
        "sort_by": "like_count",
        "sort_order": "desc",
        "page": 1,
        "page_size": 10
    }
)
print("公开知识库:", public_kbs.json())

# 点赞知识库 (需要认证)
like_response = requests.post(
    f"http://localhost:8000/api/v1/knowledge-bases/{public_kb_id}/like",
    headers=headers
)
print("点赞结果:", like_response.json())

# 使用公开知识库进行对话
public_chat = requests.post("http://localhost:8000/api/v1/conversations/chat",
    json={
        "kb_id": public_kb_id,  # 使用别人的公开知识库
        "message": "这个知识库包含什么内容？"
    },
    headers=headers
)
print("公开知识库对话:", public_chat.json())
```

### 用户活动统计
```python
# 获取用户活动记录
activities = requests.get("http://localhost:8000/api/v1/users/activities",
    params={"limit": 10},
    headers=headers
)
print("用户活动:", activities.json())

# 获取仪表板统计
dashboard = requests.get("http://localhost:8000/api/v1/users/dashboard/stats",
    params={"period": "30d"},
    headers=headers
)
print("仪表板统计:", dashboard.json())
```

## 🚀 部署指南

### Docker部署
```bash
# 构建镜像
docker build -t pdf-analysis-service .

# 运行容器
docker run -d \
  --name pdf-analysis \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e QDRANT_HOST="qdrant-host" \
  -e DASHSCOPE_API_KEY="your_api_key" \
  pdf-analysis-service
```

### Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/pdf_analysis
      - QDRANT_HOST=qdrant
    depends_on:
      - db
      - qdrant

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: pdf_analysis
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:v1.7.1
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  postgres_data:
  qdrant_data:
```

### 生产环境部署
```bash
# 使用生产配置
cp .env.production.example .env.production

# 启动生产服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔍 监控与运维

### 健康检查
```bash
# 系统健康状态
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/api/v1/system/health
```

### 性能监控
- **响应时间**: 通过日志和监控工具跟踪API响应时间
- **处理队列**: 监控文档处理队列和向量同步服务状态
- **资源使用**: 监控CPU、内存、磁盘使用情况
- **错误率**: 跟踪API错误率和异常情况
- **用户活动**: 监控用户活动模式和系统使用情况
- **Agent性能**: 监控Agent缓存命中率和响应时间

### 日志管理
```python
# 日志配置在 app/logging_config.py
# 支持不同级别的日志记录
# 结构化日志输出，便于分析
# 支持日志轮转和文件管理

# 查看实时日志
tail -f logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log

# 查看用户活动日志
grep "用户活动" logs/app.log
```

### 系统维护
```bash
# 清理过期的用户活动记录
# 可以通过定时任务或手动执行

# 清理Agent缓存
curl -X DELETE "http://localhost:8000/api/v1/agent/cache" \
  -H "Authorization: Bearer your_token"

# 检查系统状态
curl http://localhost:8000/api/v1/system/health

# 查看数据库连接状态
curl http://localhost:8000/api/v1/test/database
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest tests/

# 运行特定测试
python scripts/test_dependencies.py
python scripts/test_auth_debug.py
python scripts/test_activities_debug.py

# 测试覆盖率
pytest --cov=app tests/
```

### API测试
```bash
# 系统健康检查
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/system/health

# 测试用户注册
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "test123"
  }'

# 测试用户登录
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "login_credential": "test@example.com",
    "password": "test123"
  }'

# 使用内置测试接口 (开发环境)
curl http://localhost:8000/api/v1/test/health
curl http://localhost:8000/api/v1/test/database
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 开发规范
- 遵循 PEP 8 代码规范
- 添加适当的类型注解
- 编写单元测试
- 更新相关文档
- 提交前运行测试脚本
- 保持代码注释的完整性

## 🔧 故障排除

### 常见问题

#### 1. 数据库连接问题
```bash
# 检查数据库连接
curl http://localhost:8000/api/v1/test/database

# 如果使用PostgreSQL，确保数据库已创建
createdb document_analysis

# 检查环境变量配置
echo $DATABASE_URL
```

#### 2. Qdrant连接问题
```bash
# 检查Qdrant服务状态
curl http://localhost:6333/health

# 启动Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant:v1.7.1
```

#### 3. API Key配置问题
```bash
# 检查环境变量
echo $DASHSCOPE_API_KEY
echo $OPENAI_API_KEY

# 测试API Key有效性
python -c "
import os
from dashscope import Generation
print('QWEN API Key:', 'Valid' if os.getenv('DASHSCOPE_API_KEY') else 'Missing')
"
```

#### 4. 文件上传问题
```bash
# 检查上传目录权限
ls -la uploads/
chmod 755 uploads/

# 检查文件大小限制
# 默认50MB，可通过MAX_FILE_SIZE环境变量调整
```

#### 5. Agent缓存问题
```bash
# 清除Agent缓存
curl -X DELETE "http://localhost:8000/api/v1/agent/cache" \
  -H "Authorization: Bearer your_token"

# 检查Agent状态
curl "http://localhost:8000/api/v1/agent/status/your_kb_id" \
  -H "Authorization: Bearer your_token"
```

### 日志调试
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log | tail -20

# 查看特定用户活动
grep "用户ID: your_user_id" logs/app.log

# 查看Agent相关日志
grep "Agent" logs/app.log | tail -10
```

### 性能调优
```bash
# 监控系统资源
htop
df -h
free -h

# 检查数据库连接数
# PostgreSQL
SELECT count(*) FROM pg_stat_activity;

# 检查Qdrant集合状态
curl http://localhost:6333/collections
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🔒 安全特性

### 认证与授权
- **JWT认证**: 无状态认证机制，支持Token刷新
- **权限控制**: 基于角色的权限管理，普通用户与超级用户
- **数据隔离**: 用户数据完全隔离，确保数据安全
- **API保护**: 大部分API接口需要认证，防止未授权访问

### 数据安全
- **文件安全**: 文件上传类型限制，大小限制，MD5重复检测
- **数据加密**: 密码加密存储，敏感信息保护
- **访问控制**: 细粒度的资源访问控制
- **活动审计**: 完整的用户活动记录，支持安全审计

## 🚀 性能优化

### 缓存策略
- **Agent缓存**: 智能Agent实例缓存，提高响应速度
- **向量缓存**: 向量检索结果缓存
- **数据库连接池**: 优化数据库连接管理
- **静态资源缓存**: 文件和资源缓存策略

### 异步处理
- **文档处理**: 异步文档解析和向量化
- **向量同步**: 后台向量数据同步服务
- **流式响应**: 实时流式AI对话，提升用户体验
- **任务队列**: 后台任务队列处理

## 🌟 特色功能

### 知识共享社区
- **公开知识库**: 用户可以将知识库设为公开，分享给其他用户
- **社交功能**: 知识库点赞、访问统计、热门排序
- **标签系统**: 知识库标签分类，便于发现和管理
- **搜索发现**: 支持按标签、关键词搜索公开知识库

### 智能分析能力
- **多工具协作**: Agent支持文档分析、知识搜索、摘要生成等多种工具
- **上下文理解**: 支持多轮对话和上下文记忆
- **个性化体验**: 基于用户历史的个性化推荐
- **实时反馈**: 流式对话提供实时反馈

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [LangChain](https://langchain.com/) - 构建LLM应用的框架
- [Qdrant](https://qdrant.tech/) - 高性能向量数据库
- [PostgreSQL](https://www.postgresql.org/) - 强大的关系型数据库
- [通义千问](https://tongyi.aliyun.com/) - 阿里云大语言模型
- [OpenAI](https://openai.com/) - 先进的AI模型服务

## 📞 联系方式

- 项目主页: [GitHub Repository](https://github.com/your-username/intelligent-document-platform)
- 问题反馈: [Issues](https://github.com/your-username/intelligent-document-platform/issues)
- 功能建议: [Discussions](https://github.com/your-username/intelligent-document-platform/discussions)
- 邮箱: your-email@example.com

## 📄 更新日志

### v1.0.0 (2024-01-01)
- ✨ 完整的用户管理系统
- 🤖 基于LangChain的智能Agent
- 📚 公开知识库分享功能
- 💬 流式对话体验
- 📊 用户活动记录和统计
- 🔒 完善的权限控制系统
- 🚀 性能优化和缓存机制

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个星标！**

**🌟 欢迎贡献代码，一起构建更好的智能文档分析平台！**

Made with ❤️ by [Your Name]

</div>