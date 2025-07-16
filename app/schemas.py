from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_PERMANENTLY = "failed_permanently"  # 新增永久失败状态

class DocumentUploadRequest(BaseModel):
    filename: str
    content_type: str = "application/pdf"

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: TaskStatus
    upload_time: datetime
    message: str

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    max_results: int = Field(default=5, ge=1, le=20)

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[dict]
    processing_time: float

class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    file_size: int
    file_md5: str
    pages: int
    upload_time: datetime
    status: TaskStatus
    chunk_count: Optional[int] = None
    retry_count: Optional[int] = None  # 新增重试次数字段
    max_retries: Optional[int] = None  # 新增最大重试次数字段

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: dict

# 新增文档状态响应模型
class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    progress: int
    message: str
    error_message: Optional[str] = None

# 新增重复检测响应模型
class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    existing_document_id: Optional[str] = None
    message: str 