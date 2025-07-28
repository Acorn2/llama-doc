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

# 用户相关模型定义
from pydantic import validator

class UserBase(BaseModel):
    """用户基础模型"""
    username: Optional[str] = Field(None, description="用户名")
    email: Optional[str] = Field(None, description="邮箱地址")
    phone: Optional[str] = Field(None, description="手机号")
    full_name: Optional[str] = Field(None, description="全名")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and (len(v) < 11 or not v.isdigit()):
            raise ValueError('手机号格式不正确')
        return v

class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=6, description="密码，至少6位")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少为6位')
        return v
    
    def __init__(self, **data):
        super().__init__(**data)
        # 确保至少提供邮箱或手机号之一
        if not self.email and not self.phone:
            raise ValueError('必须提供邮箱或手机号之一')

class UserUpdate(UserBase):
    """用户更新模型"""
    password: Optional[str] = Field(None, min_length=6, description="新密码")
    is_active: Optional[bool] = Field(None, description="是否激活")

class UserLogin(BaseModel):
    """用户登录模型"""
    login_credential: str = Field(..., description="登录凭据（邮箱或手机号）")
    password: str = Field(..., description="密码")

class UserResponse(UserBase):
    """用户响应模型"""
    id: str = Field(..., description="用户ID")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(..., description="是否超级用户")
    create_time: datetime = Field(..., description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    last_login_time: Optional[datetime] = Field(None, description="最后登录时间")
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """用户列表响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    users: List[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="总数")

class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: UserResponse = Field(..., description="用户信息")

# 流式对话相关模型
class ChatStreamChunk(BaseModel):
    """流式对话响应块"""
    conversation_id: str = Field(..., description="对话ID")
    content: str = Field(..., description="内容块")
    is_final: bool = Field(False, description="是否为最后一块")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="引用来源，仅在最后一块包含")
    processing_time: Optional[float] = Field(None, description="处理时间，仅在最后一块包含")

# 为了兼容性，在这里重新定义原有的文档模式
class DocumentStatus(str, Enum):
    """文档处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_PERMANENTLY = "failed_permanently"

# 文件类型枚举
class FileType(str, Enum):
    """文件类型枚举"""
    PDF = "pdf"
    TXT = "txt"
    DOC = "doc"
    DOCX = "docx"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_extension(cls, extension: str) -> 'FileType':
        """从文件扩展名获取文件类型"""
        if not extension:
            return cls.UNKNOWN
        
        extension = extension.lower().strip()
        if extension.startswith('.'):
            extension = extension[1:]
            
        if extension == 'pdf':
            return cls.PDF
        elif extension == 'txt':
            return cls.TXT
        elif extension == 'doc':
            return cls.DOC
        elif extension == 'docx':
            return cls.DOCX
        else:
            return cls.UNKNOWN

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
    file_type: Optional[FileType] = None

class DocumentInfo(BaseModel):
    """文档信息模型"""
    id: str
    filename: str
    file_size: int
    pages: int
    upload_time: datetime
    status: DocumentStatus
    file_type: Optional[FileType] = None
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
    file_type: Optional[FileType] = None

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
    """对话请求模型"""
    conversation_id: Optional[str] = Field(None, description="对话ID，如果为空则创建新对话")
    kb_id: str = Field(..., description="知识库ID")
    message: str = Field(..., description="用户消息")
    use_agent: Optional[bool] = Field(False, description="是否使用Agent模式")

class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="对话ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    create_time: datetime = Field(..., description="创建时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")

class ChatResponse(BaseModel):
    """对话响应模型"""
    conversation_id: str = Field(..., description="对话ID")
    message: MessageResponse = Field(..., description="助手回复")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="引用来源")
    processing_time: float = Field(..., description="处理时间")

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

# 知识库相关模式
class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求模型"""
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    user_id: Optional[str] = Field(None, description="用户ID，可选（从认证token获取）")
    is_public: bool = Field(False, description="是否公开")
    public_description: Optional[str] = Field(None, description="公开描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")

class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求模型"""
    name: Optional[str] = Field(None, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    is_public: Optional[bool] = Field(None, description="是否公开")
    public_description: Optional[str] = Field(None, description="公开描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")

class KnowledgeBaseResponse(BaseModel):
    """知识库响应模型"""
    id: str = Field(..., description="知识库ID")
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    create_time: datetime = Field(..., description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    document_count: int = Field(0, description="文档数量")
    status: str = Field(..., description="知识库状态")
    is_public: bool = Field(..., description="是否公开")
    public_description: Optional[str] = Field(None, description="公开描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    view_count: int = Field(0, description="浏览次数")
    like_count: int = Field(0, description="点赞次数")
    
    # 扩展字段（仅在特定接口返回）
    owner_name: Optional[str] = Field(None, description="创建者名称")
    is_liked: Optional[bool] = Field(None, description="当前用户是否已点赞")
    is_owner: Optional[bool] = Field(None, description="当前用户是否为创建者")

class PublicKnowledgeBaseListRequest(BaseModel):
    """公开知识库列表请求模型"""
    search: Optional[str] = Field(None, description="搜索关键词")
    tags: Optional[List[str]] = Field(None, description="标签过滤")
    sort_by: str = Field("create_time", description="排序字段：create_time, view_count, like_count")
    sort_order: str = Field("desc", description="排序顺序：asc, desc")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=50, description="每页数量")

class KnowledgeBaseLikeResponse(BaseModel):
    """知识库点赞响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    is_liked: bool = Field(..., description="当前点赞状态")
    like_count: int = Field(..., description="总点赞数")

class KnowledgeBaseAccessLogRequest(BaseModel):
    """知识库访问记录请求模型"""
    kb_id: str = Field(..., description="知识库ID")
    access_type: str = Field(..., description="访问类型：view, chat")
    access_metadata: Optional[Dict[str, Any]] = Field(None, description="额外信息")

# 兼容性模型定义
class KnowledgeBaseInfo(BaseModel):
    """知识库信息（兼容性）"""
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

class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: List[KnowledgeBaseResponse]
    total: int

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
    message_metadata: Optional[Dict[str, Any]] = None

class MessageCreate(BaseModel):
    """消息创建请求"""
    conversation_id: str
    content: str
    role: str = "user"
    message_metadata: Optional[Dict[str, Any]] = None

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

# 用户活动记录相关模型
class ActivityType(str, Enum):
    """活动类型枚举"""
    # 用户认证相关
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    
    # 文档相关
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_DOWNLOAD = "document_download"
    
    # 知识库相关
    KB_CREATE = "kb_create"
    KB_UPDATE = "kb_update"
    KB_DELETE = "kb_delete"
    KB_VIEW = "kb_view"
    KB_LIKE = "kb_like"
    KB_UNLIKE = "kb_unlike"
    KB_SHARE = "kb_share"
    
    # 对话相关
    CONVERSATION_CREATE = "conversation_create"
    CONVERSATION_CHAT = "conversation_chat"
    CONVERSATION_DELETE = "conversation_delete"
    
    # Agent相关
    AGENT_CHAT = "agent_chat"
    AGENT_ANALYZE = "agent_analyze"
    AGENT_SEARCH = "agent_search"
    AGENT_SUMMARY = "agent_summary"
    
    # 系统相关
    SYSTEM_ACCESS = "system_access"

class UserActivityCreate(BaseModel):
    """创建用户活动记录请求模型"""
    activity_type: ActivityType = Field(..., description="活动类型")
    activity_description: str = Field(..., description="活动描述")
    resource_type: Optional[str] = Field(None, description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    activity_metadata: Optional[Dict[str, Any]] = Field(None, description="活动元数据")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

class UserActivityResponse(BaseModel):
    """用户活动记录响应模型"""
    id: str = Field(..., description="活动记录ID")
    user_id: str = Field(..., description="用户ID")
    activity_type: str = Field(..., description="活动类型")
    activity_description: str = Field(..., description="活动描述")
    resource_type: Optional[str] = Field(None, description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    activity_metadata: Optional[Dict[str, Any]] = Field(None, description="活动元数据")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    create_time: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True

class UserActivityListResponse(BaseModel):
    """用户活动记录列表响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    activities: List[UserActivityResponse] = Field(..., description="活动记录列表")
    total: int = Field(..., description="总数")

# 仪表板统计相关模型
class DashboardStatsItem(BaseModel):
    """仪表板统计项模型"""
    total: int = Field(..., description="总数")
    growth_rate: float = Field(..., description="增长率")
    growth_count: int = Field(..., description="增长数量")

class ConversationStatsItem(BaseModel):
    """对话统计项模型"""
    today: int = Field(..., description="今日数量")
    growth_rate: float = Field(..., description="增长率")
    yesterday: int = Field(..., description="昨日数量")

class ActivitySummaryItem(BaseModel):
    """活动摘要项模型"""
    activity_type: str = Field(..., description="活动类型")
    count: int = Field(..., description="数量")
    percentage: float = Field(..., description="百分比")

class DashboardStatsData(BaseModel):
    """仪表板统计数据模型"""
    document_stats: DashboardStatsItem = Field(..., description="文档统计")
    knowledge_base_stats: DashboardStatsItem = Field(..., description="知识库统计")
    conversation_stats: ConversationStatsItem = Field(..., description="对话统计")
    activity_summary: Dict[str, Any] = Field(..., description="活动摘要")
    period: str = Field(..., description="统计周期")
    last_updated: datetime = Field(..., description="最后更新时间")

class DashboardStatsResponse(BaseModel):
    """仪表板统计响应模型"""
    success: bool = Field(..., description="是否成功")
    data: DashboardStatsData = Field(..., description="统计数据")
    message: str = Field(..., description="响应消息")

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
    # 用户相关模式
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserLogin",
    "UserResponse",
    "UserListResponse",
    "TokenResponse",
    # 用户活动记录相关模式
    "ActivityType",
    "UserActivityCreate",
    "UserActivityResponse",
    "UserActivityListResponse",
    # 仪表板统计相关模式
    "DashboardStatsItem",
    "ConversationStatsItem", 
    "ActivitySummaryItem",
    "DashboardStatsData",
    "DashboardStatsResponse",
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
    # 流式对话相关
    "ChatStreamChunk",
    # 原有的文档模式（兼容性）
    "DocumentStatus",
    "TaskStatus",
    "FileType",
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
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "PublicKnowledgeBaseListRequest",
    "KnowledgeBaseLikeResponse",
    "KnowledgeBaseAccessLogRequest",
    "KnowledgeBaseInfo",
    "KnowledgeBaseList",
    "KnowledgeBaseDelete",
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