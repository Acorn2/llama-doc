"""
API数据模型定义
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# 用户相关模型
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

# 状态枚举
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

# 文档相关模型
class DocumentBase(BaseModel):
    """文档基础模型"""
    filename: str

class DocumentCreate(DocumentBase):
    """文档创建模型"""
    id: Optional[str] = None
    file_path: str
    user_id: Optional[str] = Field(None, description="用户ID，可选（从认证token获取）")
    file_type: Optional[FileType] = None

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
    file_type: Optional[FileType] = None

class DocumentInfo(BaseModel):
    """文档信息"""
    document_id: str
    filename: str
    file_size: int
    file_md5: str
    pages: int
    upload_time: datetime
    status: TaskStatus
    file_type: Optional[FileType] = None
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
    user_id: Optional[str] = Field(None, description="用户ID，可选（从认证token获取）")

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
    user_id: Optional[str] = Field(None, description="用户ID，可选（从认证token获取）")

class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: str = Field(..., description="对话ID")
    user_id: str = Field(..., description="用户ID")
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

class ChatStreamChunk(BaseModel):
    """流式对话响应块"""
    conversation_id: str = Field(..., description="对话ID")
    content: str = Field(..., description="内容块")
    is_final: bool = Field(False, description="是否为最后一块")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="引用来源，仅在最后一块包含")
    processing_time: Optional[float] = Field(None, description="处理时间，仅在最后一块包含") 