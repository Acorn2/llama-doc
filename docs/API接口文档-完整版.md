# PDF文献智能分析服务 - API接口文档

## 基础信息

**服务名称**: 基于大语言模型的PDF文献智能分析服务  
**框架**: FastAPI  
**版本**: 根据settings.version动态获取  
**文档地址**: `/docs` (Swagger UI)  
**健康检查**: `/health`  

## 核心功能

- PDF文档上传与解析
- 智能文档问答  
- 知识库管理
- Agent智能对话
- 文档摘要生成

## API接口列表

### 1. 根路径接口

#### GET `/`
**描述**: 获取API基本信息  
**请求参数**: 无  
**返回结果**:
```json
{
  "message": "欢迎使用 [应用名称]",
  "version": "[版本号]",
  "description": "基于大语言模型的PDF文献智能分析服务",
  "docs": "/docs",
  "health": "/health",
  "features": [
    "PDF文档上传与解析",
    "智能文档问答",
    "知识库管理", 
    "Agent智能对话",
    "文档摘要生成"
  ]
}
```

### 2. Agent智能对话接口 (前缀: `/api/v1/agent`)

#### POST `/api/v1/agent/chat`
**描述**: 与Agent进行对话，支持Agent模式和普通对话模式  
**请求体**: `AgentChatRequest`
```json
{
  "kb_id": "string",           // 知识库ID (必填)
  "message": "string",         // 用户消息 (必填)
  "conversation_id": "string", // 对话ID (可选)
  "use_agent": true,           // 是否使用Agent模式 (默认true)
  "llm_type": "qwen"          // LLM类型 (默认"qwen")
}
```
**返回结果**: `AgentChatResponse`
```json
{
  "success": true,
  "data": {},                  // 对话结果数据
  "message": "string",         // 成功消息
  "error": null                // 错误信息
}
```

#### POST `/api/v1/agent/analyze`
**描述**: 使用Agent分析文档内容  
**请求体**: `DocumentAnalysisRequest`
```json
{
  "kb_id": "string",          // 知识库ID (必填)
  "query": "string",          // 分析查询 (必填)
  "llm_type": "qwen"         // LLM类型 (默认"qwen")
}
```
**返回结果**: `DocumentAnalysisResponse`
```json
{
  "success": true,
  "data": {},                 // 分析结果数据
  "error": null               // 错误信息
}
```

#### POST `/api/v1/agent/search`
**描述**: 在知识库中搜索信息  
**请求体**: `KnowledgeSearchRequest`
```json
{
  "kb_id": "string",          // 知识库ID (必填)
  "query": "string",          // 搜索查询 (必填)
  "max_results": 5,           // 最大结果数 (默认5)
  "llm_type": "qwen"         // LLM类型 (默认"qwen")
}
```
**返回结果**: `KnowledgeSearchResponse`
```json
{
  "success": true,
  "data": {},                 // 搜索结果数据
  "error": null               // 错误信息
}
```

#### POST `/api/v1/agent/summary`
**描述**: 生成文档摘要  
**请求体**: `SummaryRequest`
```json
{
  "kb_id": "string",          // 知识库ID (必填)
  "llm_type": "qwen"         // LLM类型 (默认"qwen")
}
```
**返回结果**: `SummaryResponse`
```json
{
  "success": true,
  "data": {},                 // 摘要结果数据
  "error": null               // 错误信息
}
```

#### GET `/api/v1/agent/history/{kb_id}`
**描述**: 获取Agent对话历史  
**路径参数**:
- `kb_id`: 知识库ID (必填)

**查询参数**:
- `llm_type`: LLM类型 (默认"qwen")

**返回结果**: `ConversationHistoryResponse`
```json
{
  "success": true,
  "data": {},                 // 对话历史数据
  "error": null               // 错误信息
}
```

#### DELETE `/api/v1/agent/memory/{kb_id}`
**描述**: 清除Agent对话记忆  
**路径参数**:
- `kb_id`: 知识库ID (必填)

**查询参数**:
- `llm_type`: LLM类型 (默认"qwen")

**返回结果**:
```json
{
  "success": true,
  "message": "记忆清除成功"
}
```

#### DELETE `/api/v1/agent/cache`
**描述**: 清除所有Agent缓存  
**请求参数**: 无  
**返回结果**:
```json
{
  "success": true,
  "message": "缓存清除成功"
}
```

#### GET `/api/v1/agent/status/{kb_id}`
**描述**: 获取Agent状态信息  
**路径参数**:
- `kb_id`: 知识库ID (必填)

**查询参数**:
- `llm_type`: LLM类型 (默认"qwen")

**返回结果**: `AgentStatusResponse`
```json
{
  "success": true,
  "data": {
    "status": "ready",        // Agent状态
    "memory_size": 10,        // 记忆大小
    "cache_hit_rate": 0.85    // 缓存命中率
  },
  "error": null
}
```

### 3. 健康检查接口 (前缀: `/health`)

#### GET `/health/`
**描述**: 基础健康检查  
**请求参数**: 无  
**返回结果**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "service": "Knowledge Base API",
  "version": "1.0.0"
}
```

#### GET `/health/detailed`
**描述**: 详细健康检查，包含系统资源和服务状态  
**请求参数**: 无  
**返回结果**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "service": "[应用名称]",
  "version": "[版本号]",
  "response_time": "0.123s",
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "disk_percent": 60.1,
    "load_average": [1.2, 1.1, 1.0]
  },
  "agent_cache": {
    "total_agents": 5,
    "cache_hit_rate": 0.85
  },
  "configuration": {
    "debug_mode": false,
    "llm_type": "qwen",
    "agent_cache_enabled": true,
    "agent_memory_enabled": true
  },
  "uptime": 86400
}
```

#### GET `/health/readiness`
**描述**: 就绪检查，检查服务是否准备好接收请求  
**请求参数**: 无  
**返回结果**:
```json
{
  "status": "ready",
  "timestamp": "2024-01-01T00:00:00",
  "checks": {
    "agent_service": {
      "status": "ready",
      "cached_agents": 5
    },
    "configuration": {
      "status": "ready",
      "app_name": "[应用名称]"
    }
  }
}
```

#### GET `/health/liveness`
**描述**: 存活检查，检查服务是否仍在运行  
**请求参数**: 无  
**返回结果**:
```json
{
  "status": "alive",
  "timestamp": "2024-01-01T00:00:00",
  "pid": 12345,
  "memory_usage": "128.50 MB"
}
```

## 技术架构特点

根据代码分析，该系统具有以下特点：

1. **企业级分层架构**: 清晰的4层架构设计
2. **依赖注入系统**: 使用FastAPI的依赖注入，便于测试和维护
3. **统一异常处理**: 全局异常处理机制
4. **集中配置管理**: 类型安全的配置管理
5. **LangChain Agent集成**: 具备真正的智能对话和任务执行能力
6. **完整监控体系**: 健康检查、性能监控、日志管理

## 使用说明

1. 所有接口都支持标准的HTTP状态码
2. 错误响应统一格式，包含详细的错误信息
3. 支持多种LLM类型，默认使用"qwen"
4. Agent功能支持记忆和缓存机制
5. 完整的健康检查体系，便于运维监控

## Postman测试建议

1. 先调用根路径接口确认服务正常
2. 使用健康检查接口验证各组件状态
3. 按照业务流程测试Agent相关接口
4. 注意设置正确的Content-Type为application/json
5. 关注返回的success字段判断操作是否成功

---

*本文档基于项目代码中的 `agent_router.py`、`main.py`、`health.py` 和相关配置文件生成。如需了解更多接口详情，建议查看完整的路由文件和schemas定义。*