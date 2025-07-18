"""
Agent相关的数据模式定义
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """Agent对话请求"""
    kb_id: str = Field(..., description="知识库ID")
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    use_agent: bool = Field(True, description="是否使用Agent模式")
    llm_type: str = Field("qwen", description="LLM类型")


class DocumentAnalysisRequest(BaseModel):
    """文档分析请求"""
    kb_id: str = Field(..., description="知识库ID")
    query: str = Field(..., description="分析查询")
    llm_type: str = Field("qwen", description="LLM类型")


class KnowledgeSearchRequest(BaseModel):
    """知识搜索请求"""
    kb_id: str = Field(..., description="知识库ID")
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(5, description="最大结果数")
    llm_type: str = Field("qwen", description="LLM类型")


class SummaryRequest(BaseModel):
    """摘要生成请求"""
    kb_id: str = Field(..., description="知识库ID")
    llm_type: str = Field("qwen", description="LLM类型")


# 响应模型
class AgentChatResponse(BaseModel):
    """Agent对话响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None


class DocumentAnalysisResponse(BaseModel):
    """文档分析响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class KnowledgeSearchResponse(BaseModel):
    """知识搜索响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SummaryResponse(BaseModel):
    """摘要生成响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """对话历史响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Agent状态响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None