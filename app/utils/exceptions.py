"""
自定义异常类
"""

from typing import Optional, Any, Dict


class BaseAppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AgentError(BaseAppException):
    """Agent相关异常"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "AGENT_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class KnowledgeBaseNotFoundError(BaseAppException):
    """知识库不存在异常"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "KB_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class DocumentProcessingError(BaseAppException):
    """文档处理异常"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DOC_PROCESSING_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class VectorStoreError(BaseAppException):
    """向量存储异常"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "VECTOR_STORE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class LLMError(BaseAppException):
    """大语言模型异常"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "LLM_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class ValidationError(BaseAppException):
    """数据验证异常"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)