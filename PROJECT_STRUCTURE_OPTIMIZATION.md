# 项目结构优化方案

## 🎯 优化目标

1. **清晰的分层架构**：API层 -> 服务层 -> 核心层 -> 数据层
2. **单一职责原则**：每个模块只负责一个明确的功能
3. **依赖注入**：减少硬编码依赖，提高可测试性
4. **配置集中管理**：统一的配置管理机制

## 📁 优化后的项目结构

```
app/
├── api/                    # API层 - 处理HTTP请求
│   ├── __init__.py
│   ├── dependencies.py     # 依赖注入
│   └── v1/                 # API版本管理
│       ├── __init__.py
│       ├── agent.py        # Agent相关API
│       ├── documents.py    # 文档管理API
│       ├── knowledge.py    # 知识库API
│       └── system.py       # 系统API
│
├── services/               # 服务层 - 业务逻辑
│   ├── __init__.py
│   ├── agent_service.py    # Agent业务服务
│   ├── document_service.py # 文档处理服务
│   ├── knowledge_service.py# 知识库服务
│   └── conversation_service.py # 对话服务
│
├── core/                   # 核心层 - 核心业务逻辑
│   ├── __init__.py
│   ├── agents/             # Agent核心模块
│   │   ├── __init__.py
│   │   ├── base.py         # Agent基类
│   │   ├── document_agent.py # 文档分析Agent
│   │   └── tools/          # Agent工具
│   │       ├── __init__.py
│   │       ├── document_analyzer.py
│   │       ├── knowledge_searcher.py
│   │       └── summarizer.py
│   │
│   ├── models/             # 数据模型
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── conversation.py
│   │   └── knowledge_base.py
│   │
│   └── processors/         # 数据处理器
│       ├── __init__.py
│       ├── document_processor.py
│       └── text_processor.py
│
├── infrastructure/         # 基础设施层
│   ├── __init__.py
│   ├── database/           # 数据库相关
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── repositories/   # 数据访问层
│   │       ├── __init__.py
│   │       ├── document_repo.py
│   │       └── conversation_repo.py
│   │
│   ├── vector_stores/      # 向量数据库
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── qdrant_store.py
│   │
│   ├── llm/               # 大语言模型集成
│   │   ├── __init__.py
│   │   ├── factory.py
│   │   ├── qwen_adapter.py
│   │   └── openai_adapter.py
│   │
│   └── storage/           # 文件存储
│       ├── __init__.py
│       └── file_manager.py
│
├── config/                # 配置管理
│   ├── __init__.py
│   ├── settings.py        # 应用配置
│   └── logging.py         # 日志配置
│
├── schemas/               # 数据模式定义
│   ├── __init__.py
│   ├── api_schemas.py     # API请求/响应模式
│   ├── agent_schemas.py   # Agent相关模式
│   └── document_schemas.py # 文档相关模式
│
├── utils/                 # 工具函数
│   ├── __init__.py
│   ├── exceptions.py      # 自定义异常
│   ├── validators.py      # 数据验证
│   └── helpers.py         # 辅助函数
│
└── main.py               # 应用入口
```

## 🔧 关键优化点

### 1. 分层架构
- **API层**：只处理HTTP请求/响应，参数验证
- **服务层**：业务逻辑编排，事务管理
- **核心层**：核心业务逻辑，Agent实现
- **基础设施层**：外部系统集成，数据访问

### 2. 依赖注入
- 使用FastAPI的依赖注入系统
- 统一的依赖管理
- 便于单元测试

### 3. 配置集中化
- 所有配置集中在config模块
- 环境变量管理
- 类型安全的配置

### 4. 错误处理
- 统一的异常处理机制
- 结构化的错误响应
- 详细的日志记录

## 📋 迁移计划

### 阶段1：基础架构重构
1. 创建新的目录结构
2. 重构配置管理
3. 统一异常处理

### 阶段2：核心功能迁移
1. 重构Agent核心模块
2. 优化服务层设计
3. 重构数据访问层

### 阶段3：API层优化
1. 重构路由结构
2. 优化依赖注入
3. 完善API文档

### 阶段4：清理和测试
1. 移除冗余代码
2. 完善单元测试
3. 性能优化