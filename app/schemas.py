"""
API数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# 状态枚举
class DocumentStatus(str, Enum):
    """文档处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_PERMANENTLY = "failed_permanently"

# 兼容旧代码的别名
TaskStatus = DocumentStatus

# 文档相关模型
class DocumentBase(BaseModel):
    """文档基础模型"""
    filename: str

class DocumentCreate(DocumentBase):
    """文档创建模型"""
    id: Optional[str] = None
    file_path: str
    user_id: Optional[str] = "system"

class DocumentUploadRequest(DocumentBase):
    """文档上传请求"""
    content_type: str = "application/octet-stream"  # 默认类型，实际会根据文件类型动态设置

class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    filename: str
    status: TaskStatus
    upload_time: datetime
    message: str

class DocumentInfo(BaseModel):
    """文档信息"""
    document_id: str
    filename: str
    file_size: int
    file_md5: str
    pages: int
    upload_time: datetime
    status: TaskStatus
    chunk_count: Optional[int] = None
    retry_count: Optional[int] = None
    max_retries: Optional[int] = None

class DocumentStatusResponse(BaseModel):
    """文档状态响应"""
    document_id: str
    status: str
    progress: int
    message: str
    error_message: Optional[str] = None

class DuplicateCheckResponse(BaseModel):
    """重复检测响应"""
    is_duplicate: bool
    existing_document_id: Optional[str] = None
    message: str

# 查询相关模型
class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., min_length=1, max_length=1000)
    max_results: int = Field(default=5, ge=1, le=20)

class QueryResponse(BaseModel):
    """查询响应"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    processing_time: float

# 系统相关模型
class HealthCheck(BaseModel):
    """健康检查"""
    status: str
    timestamp: datetime
    services: Dict[str, str]

# LlamaIndex相关模型
class LlamaIndexQueryRequest(BaseModel):
    """LlamaIndex查询请求"""
    query: str
    document_id: str
    similarity_top_k: Optional[int] = 3
    similarity_cutoff: Optional[float] = 0.7

class LlamaIndexQueryResponse(BaseModel):
    """LlamaIndex查询响应"""
    answer: str
    source_nodes: List[Dict[str, Any]] 

# 知识库相关模式
class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求模型"""
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")

class KnowledgeBaseResponse(BaseModel):
    """知识库响应模型"""
    id: str = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    create_time: datetime = Field(..., description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    document_count: int = Field(0, description="文档数量")
    status: str = Field(..., description="知识库状态")

class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应模型"""
    items: List[KnowledgeBaseResponse] = Field(..., description="知识库列表")
    total: int = Field(..., description="知识库总数")

class DocumentAddResponse(BaseModel):
    """添加文档到知识库响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    kb_id: str = Field(..., description="知识库ID")
    document_id: str = Field(..., description="文档ID")

# 对话相关模式
class ConversationCreate(BaseModel):
    """创建对话请求模型"""
    kb_id: str = Field(..., description="知识库ID")
    title: Optional[str] = Field(None, description="对话标题")

class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: str = Field(..., description="对话ID")
    kb_id: str = Field(..., description="知识库ID")
    title: Optional[str] = Field(None, description="对话标题")
    create_time: datetime = Field(..., description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    status: str = Field(..., description="对话状态")

class ConversationListResponse(BaseModel):
    """对话列表响应模型"""
    items: List[ConversationResponse] = Field(..., description="对话列表")
    total: int = Field(..., description="对话总数")

class MessageCreate(BaseModel):
    """创建消息请求模型"""
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")

class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="对话ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    create_time: datetime = Field(..., description="创建时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")

class ChatRequest(BaseModel):
    """对话请求模型"""
    conversation_id: Optional[str] = Field(None, description="对话ID，如果为空则创建新对话")
    kb_id: str = Field(..., description="知识库ID")
    message: str = Field(..., description="用户消息")
    use_agent: Optional[bool] = Field(False, description="是否使用Agent模式")

class ChatResponse(BaseModel):
    """对话响应模型"""
    conversation_id: str = Field(..., description="对话ID")
    message: MessageResponse = Field(..., description="助手回复")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="引用来源")
    processing_time: float = Field(..., description="处理时间") 