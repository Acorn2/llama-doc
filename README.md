# 🤖 PDF文献智能分析服务

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1.20-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**基于LangChain Agent的现代化智能文档分析平台**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [API文档](#-api接口) • [架构设计](#-系统架构) • [部署指南](#-部署指南)

</div>

## 📖 项目简介

PDF文献智能分析服务是一个基于FastAPI的现代化智能文档分析系统，经过深度重构后采用清晰的分层架构，集成了**LangChain Agent**能力，提供PDF文档的智能上传、解析、问答、摘要生成等功能。

### 🎯 核心亮点

- 🤖 **真正的AI Agent**: 基于LangChain的完整Agent实现，支持工具链式调用
- 🏗️ **现代化架构**: 清晰的4层分层架构，依赖注入系统
- 💬 **流式对话**: 支持实时流式AI对话，提升用户体验
- 📚 **知识库管理**: 完整的知识库CRUD和跨文档智能搜索
- 🔄 **双存储策略**: 腾讯云COS + 本地存储自动降级
- 📊 **企业级特性**: 健康检查、监控、缓存、异常处理

## ✨ 功能特性

### 🤖 智能Agent能力
- **智能对话**: 支持多轮对话和上下文理解
- **文档分析**: 深度文档理解和结构化信息提取
- **知识搜索**: 语义理解搜索和智能结果筛选
- **摘要生成**: 多层次摘要生成，学术规范格式
- **工具协作**: 多工具链式调用完成复杂任务

### 📄 文档处理
- **多格式支持**: PDF、TXT、DOC、DOCX文档处理
- **智能解析**: 基于PyMuPDF和unstructured的文档解析
- **向量化存储**: Qdrant向量数据库存储文档向量
- **重复检测**: MD5文件重复检测机制
- **异步处理**: 后台异步文档处理队列

### 💾 知识库管理
- **知识库CRUD**: 完整的知识库创建、查询、更新、删除
- **文档关联**: 灵活的文档与知识库关联管理
- **跨文档搜索**: 支持跨多个文档的语义搜索
- **智能问答**: 基于知识库的智能问答系统

### 🔄 对话管理
- **对话历史**: 完整的对话记录存储与检索
- **流式输出**: 实时流式AI回复，支持SSE
- **上下文维护**: 多轮对话上下文管理
- **Agent模式**: 可选择Agent模式或普通对话模式

## 🏗️ 系统架构

### 分层架构设计
```
┌─────────────────────────────────────────────────────────────┐
│                        API层 (API Layer)                    │
│  FastAPI路由 • 请求验证 • 响应格式化 • 异常处理              │
├─────────────────────────────────────────────────────────────┤
│                      服务层 (Service Layer)                  │
│  业务逻辑 • Agent服务 • 对话管理 • 知识库管理                │
├─────────────────────────────────────────────────────────────┤
│                      核心层 (Core Layer)                     │
│  LangChain Agent • 文档处理 • 向量化 • LLM适配              │
├─────────────────────────────────────────────────────────────┤
│                      数据层 (Data Layer)                     │
│  PostgreSQL • Qdrant • 文件存储 • 缓存                     │
└─────────────────────────────────────────────────────────────┘
```

### 核心技术栈
- **后端框架**: FastAPI 0.104.1 + Uvicorn
- **数据库**: PostgreSQL + SQLAlchemy 2.0.23
- **向量数据库**: Qdrant 1.7.1
- **AI框架**: LangChain 0.1.20 + LangChain Community
- **大语言模型**: 通义千问 + OpenAI
- **文件存储**: 本地存储 + 腾讯云COS
- **文档处理**: PyMuPDF + unstructured + python-docx

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL 12+
- Qdrant 1.7+

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

# 编辑配置文件
vim .env.development
```

### 4. 启动服务
```bash
# 开发模式启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 或使用启动脚本
chmod +x start.sh
./start.sh
```

### 5. 访问服务
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

## 📡 API接口

### 🤖 智能Agent (`/api/v1/agent`)
```bash
# Agent智能对话
POST /api/v1/agent/chat
POST /api/v1/agent/chat/stream  # 流式对话

# 文档分析
POST /api/v1/agent/analyze

# 知识搜索
POST /api/v1/agent/search

# 摘要生成
POST /api/v1/agent/summary

# Agent管理
GET /api/v1/agent/history/{kb_id}
DELETE /api/v1/agent/memory/{kb_id}
GET /api/v1/agent/status/{kb_id}
```

### 📄 文档管理 (`/api/v1/documents`)
```bash
# 文档上传与管理
POST /api/v1/documents/upload
GET /api/v1/documents/{document_id}
GET /api/v1/documents
DELETE /api/v1/documents/{document_id}

# 文档状态与下载
GET /api/v1/documents/{document_id}/status
GET /api/v1/documents/{document_id}/download
POST /api/v1/documents/check-duplicate
```

### 📚 知识库管理 (`/api/v1/knowledge-bases`)
```bash
# 知识库CRUD
POST /api/v1/knowledge-bases/
GET /api/v1/knowledge-bases/
GET /api/v1/knowledge-bases/{kb_id}
PUT /api/v1/knowledge-bases/{kb_id}
DELETE /api/v1/knowledge-bases/{kb_id}

# 文档关联
POST /api/v1/knowledge-bases/{kb_id}/documents/{document_id}
DELETE /api/v1/knowledge-bases/{kb_id}/documents/{document_id}
GET /api/v1/knowledge-bases/{kb_id}/documents

# 知识库搜索
POST /api/v1/knowledge-bases/{kb_id}/search
```

### 💬 对话管理 (`/api/v1/conversations`)
```bash
# 对话管理
POST /api/v1/conversations/
GET /api/v1/conversations/
GET /api/v1/conversations/{conversation_id}
PUT /api/v1/conversations/{conversation_id}
DELETE /api/v1/conversations/{conversation_id}

# 对话交互
POST /api/v1/conversations/chat
POST /api/v1/conversations/chat/stream  # 流式对话
POST /api/v1/conversations/{conversation_id}/chat/stream

# 消息管理
GET /api/v1/conversations/{conversation_id}/messages
POST /api/v1/conversations/{conversation_id}/messages
```

## 🔧 配置说明

### 环境变量配置
```bash
# 应用配置
APP_NAME="PDF文献智能分析服务"
VERSION="2.0.0"
DEBUG=true
ENVIRONMENT="development"

# 数据库配置
DATABASE_URL="postgresql://user:password@localhost:5432/pdf_analysis"

# Qdrant向量数据库
QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_API_KEY=""

# 大语言模型配置
DASHSCOPE_API_KEY="your_qwen_api_key"
OPENAI_API_KEY="your_openai_api_key"

# 腾讯云COS配置
COS_SECRET_ID="your_cos_secret_id"
COS_SECRET_KEY="your_cos_secret_key"
COS_REGION="ap-beijing"
COS_BUCKET="your-bucket-name"
```

## 📊 使用示例

### Agent智能对话
```python
import requests

# 智能对话
response = requests.post("http://localhost:8000/api/v1/agent/chat", json={
    "kb_id": "your_knowledge_base_id",
    "message": "请分析这个文档的主要观点",
    "use_agent": True,
    "llm_type": "qwen"
})

print(response.json())
```

### 流式对话
```javascript
// 使用EventSource接收流式响应
const eventSource = new EventSource('/api/v1/conversations/chat/stream', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        kb_id: 'your_kb_id',
        message: '你好，请介绍一下这个文档',
        use_agent: true
    })
});

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.is_final) {
        console.log('对话完成:', data);
        eventSource.close();
    } else {
        console.log('接收内容:', data.content);
    }
};
```

### 文档上传与分析
```python
import requests

# 上传文档
with open('document.pdf', 'rb') as f:
    response = requests.post(
        "http://localhost:8000/api/v1/documents/upload",
        files={"file": f}
    )
    document_id = response.json()["document_id"]

# 创建知识库
kb_response = requests.post("http://localhost:8000/api/v1/knowledge-bases/", json={
    "name": "我的知识库",
    "description": "测试知识库"
})
kb_id = kb_response.json()["knowledge_base"]["id"]

# 添加文档到知识库
requests.post(f"http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/{document_id}")

# Agent分析文档
analysis = requests.post("http://localhost:8000/api/v1/agent/analyze", json={
    "kb_id": kb_id,
    "query": "请分析这个文档的核心内容",
    "llm_type": "qwen"
})

print(analysis.json())
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
- **处理队列**: 监控文档处理队列状态
- **资源使用**: 监控CPU、内存、磁盘使用情况
- **错误率**: 跟踪API错误率和异常情况

### 日志管理
```python
# 日志配置在 app/logging_config.py
# 支持不同级别的日志记录
# 结构化日志输出，便于分析
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest tests/

# 运行特定测试
python tests/test_dependencies.py
python tests/test_refactored_structure.py

# 测试覆盖率
pytest --cov=app tests/
```

### API测试
```bash
# 使用内置测试接口
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

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [LangChain](https://langchain.com/) - 构建LLM应用的框架
- [Qdrant](https://qdrant.tech/) - 向量数据库
- [通义千问](https://tongyi.aliyun.com/) - 阿里云大语言模型

## 📞 联系方式

- 项目主页: [GitHub Repository](https://github.com/your-username/pdf-analysis-service)
- 问题反馈: [Issues](https://github.com/your-username/pdf-analysis-service/issues)
- 邮箱: your-email@example.com

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个星标！**

Made with ❤️ by [Your Name]

</div>