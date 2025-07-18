"""
数据模式定义模块
整合新架构的Agent模式和原有的文档模式
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 导入新架构的Agent模式
from .agent_schemas import (
    AgentChatRequest,
    AgentChatResponse,
    DocumentAnalysisRequest,
    DocumentAnalysisResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    SummaryRequest,
    SummaryResponse,
    ConversationHistoryResponse,
    AgentStatusResponse
)

# 为了兼容性，在这里重新定义原有的文档模式
class DocumentStatus(str, Enum):
    """文档处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_PERMANENTLY = "failed_permanently"

# 兼容旧代码的别名
TaskStatus = DocumentStatus

# 基础文档模型（兼容性）
class DocumentBase(BaseModel):
    """文档基础模型"""
    filename: str

class DocumentCreate(DocumentBase):
    """文档创建模型"""
    id: Optional[str] = None
    file_path: str
    user_id: Optional[str] = "system"

class DocumentInfo(BaseModel):
    """文档信息模型"""
    id: str
    filename: str
    file_size: int
    pages: int
    upload_time: datetime
    status: DocumentStatus
    chunk_count: Optional[int] = None
    retry_count: Optional[int] = None

class DocumentStatusResponse(BaseModel):
    """文档状态响应"""
    document_id: str
    status: DocumentStatus
    progress: int
    message: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    filename: str
    status: str
    message: str

class DuplicateCheckResponse(BaseModel):
    """重复检查响应"""
    is_duplicate: bool
    existing_document_id: Optional[str] = None
    message: str

class DocumentAddResponse(BaseModel):
    """文档添加响应"""
    success: bool
    message: str
    document_id: Optional[str] = None
    document: Optional[DocumentInfo] = None

class DocumentDeleteResponse(BaseModel):
    """文档删除响应"""
    success: bool
    message: str
    deleted_count: Optional[int] = None

class DocumentListResponse(BaseModel):
    """文档列表响应"""
    success: bool
    documents: List[DocumentInfo]
    total: int
    page: Optional[int] = None
    page_size: Optional[int] = None

# 基础对话模型（兼容性）
class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    """对话响应"""
    answer: str
    conversation_id: str
    timestamp: datetime

class MessageResponse(BaseModel):
    """消息响应"""
    message: str
    success: bool = True

# 查询模型（兼容性）
class QueryRequest(BaseModel):
    """查询请求"""
    query: str
    max_results: int = 5

class QueryResponse(BaseModel):
    """查询响应"""
    results: List[Dict[str, Any]]
    query: str
    total_results: int

class LlamaIndexQueryRequest(BaseModel):
    """LlamaIndex查询请求"""
    query: str
    document_ids: Optional[List[str]] = None
    max_results: int = 5

class LlamaIndexQueryResponse(BaseModel):
    """LlamaIndex查询响应"""
    answer: str
    sources: List[Dict[str, Any]]
    query: str

# 系统相关模型（兼容性）
class HealthCheck(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    timestamp: datetime
    version: str
    uptime: Optional[float] = None
    system_info: Optional[Dict[str, Any]] = None

class SystemInfo(BaseModel):
    """系统信息"""
    version: str
    python_version: str
    platform: str
    memory_usage: Optional[Dict[str, Any]] = None
    disk_usage: Optional[Dict[str, Any]] = None
    cpu_usage: Optional[float] = None

class DatabaseStatus(BaseModel):
    """数据库状态"""
    connected: bool
    connection_count: Optional[int] = None
    last_check: datetime
    database_type: Optional[str] = None

class VectorStoreStatus(BaseModel):
    """向量存储状态"""
    connected: bool
    collection_count: Optional[int] = None
    total_vectors: Optional[int] = None
    last_check: datetime

# 知识库相关模型（兼容性）
class KnowledgeBaseCreate(BaseModel):
    """知识库创建请求"""
    name: str
    description: Optional[str] = None
    embedding_model: Optional[str] = None

class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""
    id: str
    name: str
    description: Optional[str] = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
    embedding_model: Optional[str] = None

class KnowledgeBaseList(BaseModel):
    """知识库列表响应"""
    knowledge_bases: List[KnowledgeBaseInfo]
    total: int

class KnowledgeBaseDelete(BaseModel):
    """知识库删除响应"""
    success: bool
    message: str

class KnowledgeBaseResponse(BaseModel):
    """知识库通用响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    knowledge_base: Optional[KnowledgeBaseInfo] = None

class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    success: bool
    data: KnowledgeBaseList
    message: Optional[str] = None

# 对话相关模型（兼容性）
class ConversationCreate(BaseModel):
    """对话创建请求"""
    title: Optional[str] = None
    kb_id: Optional[str] = None

class ConversationInfo(BaseModel):
    """对话信息"""
    id: str
    title: str
    kb_id: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

class ConversationList(BaseModel):
    """对话列表响应"""
    conversations: List[ConversationInfo]
    total: int

class ConversationMessage(BaseModel):
    """对话消息"""
    id: str
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class MessageCreate(BaseModel):
    """消息创建请求"""
    conversation_id: str
    content: str
    role: str = "user"
    metadata: Optional[Dict[str, Any]] = None

class ConversationHistory(BaseModel):
    """对话历史"""
    conversation_id: str
    messages: List[ConversationMessage]
    total_messages: int

class ConversationResponse(BaseModel):
    """对话通用响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    conversation: Optional[ConversationInfo] = None

class ConversationListResponse(BaseModel):
    """对话列表响应"""
    success: bool
    data: ConversationList
    message: Optional[str] = None

class ConversationDeleteResponse(BaseModel):
    """对话删除响应"""
    success: bool
    message: str
    deleted_count: Optional[int] = None

# 文件上传相关模型（兼容性）
class FileUploadResponse(BaseModel):
    """文件上传响应"""
    success: bool
    file_id: Optional[str] = None
    filename: Optional[str] = None
    message: str
    file_size: Optional[int] = None

class FileInfo(BaseModel):
    """文件信息"""
    id: str
    filename: str
    file_size: int
    content_type: str
    upload_time: datetime
    status: str

# 错误响应模型（兼容性）
class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

class ValidationErrorResponse(BaseModel):
    """验证错误响应"""
    success: bool = False
    error: str = "Validation Error"
    validation_errors: List[Dict[str, Any]]
    timestamp: datetime

__all__ = [
    # 新架构的Agent模式
    "AgentChatRequest",
    "AgentChatResponse", 
    "DocumentAnalysisRequest",
    "DocumentAnalysisResponse",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "SummaryRequest",
    "SummaryResponse",
    "ConversationHistoryResponse",
    "AgentStatusResponse",
    # 原有的文档模式（兼容性）
    "DocumentStatus",
    "TaskStatus",
    "DocumentBase",
    "DocumentCreate",
    "DocumentInfo",
    "DocumentStatusResponse",
    "DocumentUploadResponse",
    "DuplicateCheckResponse",
    "DocumentAddResponse",
    "DocumentDeleteResponse",
    "DocumentListResponse",
    # 对话模式（兼容性）
    "ChatRequest",
    "ChatResponse",
    "MessageResponse",
    # 查询模式（兼容性）
    "QueryRequest",
    "QueryResponse",
    "LlamaIndexQueryRequest",
    "LlamaIndexQueryResponse",
    # 系统相关模式（兼容性）
    "HealthCheck",
    "SystemInfo",
    "DatabaseStatus",
    "VectorStoreStatus",
    # 知识库相关模式（兼容性）
    "KnowledgeBaseCreate",
    "KnowledgeBaseInfo",
    "KnowledgeBaseList",
    "KnowledgeBaseDelete",
    "KnowledgeBaseResponse",
    "KnowledgeBaseListResponse",
    # 对话相关模式（兼容性）
    "ConversationCreate",
    "ConversationInfo",
    "ConversationList",
    "ConversationMessage",
    "MessageCreate",
    "ConversationHistory",
    "ConversationResponse",
    "ConversationListResponse",
    "ConversationDeleteResponse",
    # 文件上传相关模式（兼容性）
    "FileUploadResponse",
    "FileInfo",
    # 错误响应模式（兼容性）
    "ErrorResponse",
    "ValidationErrorResponse"
]