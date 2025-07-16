import os
from typing import Optional, Any
from langchain.embeddings.base import Embeddings
from langchain.llms.base import BaseLLM

# 导入不同的模型适配器
try:
    from langchain.chat_models import ChatOpenAI
    from langchain.embeddings import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from ..llm.qwen_adapter import QwenLLM, QwenChatModel
    from ..llm.qwen_embeddings import QwenEmbeddings
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False

class ModelFactory:
    """模型工厂，支持多种大模型"""
    
    @staticmethod
    def create_llm(model_type: str = None, **kwargs) -> Any:
        """创建语言模型"""
        if model_type is None:
            model_type = os.getenv("LLM_TYPE", "openai")
        
        if model_type.lower() == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI依赖未安装，请安装: pip install langchain-openai")
            
            return ChatOpenAI(
                temperature=kwargs.get("temperature", 0.1),
                model=kwargs.get("model", "gpt-3.5-turbo")
            )
        
        elif model_type.lower() == "qwen":
            if not QWEN_AVAILABLE:
                raise ImportError("通义千问依赖未安装，请安装: pip install dashscope")
            
            # 使用继承LLM基类的QwenLLM，而不是QwenChatModel
            return QwenLLM(
                model_name=kwargs.get("model", "qwen-plus"),
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 2000),
                top_p=kwargs.get("top_p", 0.8)
            )
        
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
    
    @staticmethod
    def create_embeddings(model_type: str = None, **kwargs) -> Embeddings:
        """创建嵌入模型"""
        if model_type is None:
            model_type = os.getenv("EMBEDDING_TYPE", "openai")
        
        if model_type.lower() == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI依赖未安装")
            
            return OpenAIEmbeddings()
        
        elif model_type.lower() == "qwen":
            if not QWEN_AVAILABLE:
                raise ImportError("通义千问依赖未安装")
            
            return QwenEmbeddings(
                model_name=kwargs.get("model", "text-embedding-v1")
            )
        
        else:
            raise ValueError(f"不支持的嵌入模型类型: {model_type}")
    
    @staticmethod
    def get_available_models() -> dict:
        """获取可用的模型列表"""
        available = {
            "llm": [],
            "embeddings": []
        }
        
        if OPENAI_AVAILABLE:
            available["llm"].append("openai")
            available["embeddings"].append("openai")
        
        if QWEN_AVAILABLE:
            available["llm"].append("qwen")
            available["embeddings"].append("qwen")
        
        return available 