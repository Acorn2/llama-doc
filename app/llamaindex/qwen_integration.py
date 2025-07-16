"""
通义千问模型的LlamaIndex集成适配器
"""
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.llms import CustomLLM
from llama_index.core.embeddings import BaseEmbedding

from app.llm.qwen_adapter import QwenLLM
from app.llm.qwen_embeddings import QwenEmbeddings

logger = logging.getLogger(__name__)

class QwenLlamaLLM(CustomLLM):
    """通义千问模型的LlamaIndex LLM适配器"""
    
    def __init__(
        self,
        model_name: str = "qwen-max",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ):
        """
        初始化通义千问LLM适配器
        
        Args:
            model_name: 模型名称
            api_key: API密钥
            temperature: 温度参数
            max_tokens: 最大生成token数
        """
        super().__init__()
        
        # 如果没有提供API密钥，则从环境变量中获取
        if api_key is None:
            api_key = os.environ.get("DASHSCOPE_API_KEY")
        
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.qwen_llm = QwenLLM(
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """获取元数据"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
    
    def complete(self, prompt: str, **kwargs) -> str:
        """
        完成文本生成
        
        Args:
            prompt: 提示文本
            
        Returns:
            str: 生成的文本
        """
        try:
            response = self.qwen_llm.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"通义千问文本生成失败: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> str:
        """
        聊天对话生成
        
        Args:
            messages: 聊天消息列表
            
        Returns:
            str: 生成的回复
        """
        try:
            # 转换消息格式
            qwen_messages = []
            for message in messages:
                role = self._convert_role(message.role)
                qwen_messages.append({"role": role, "content": message.content})
            
            # 调用通义千问对话接口
            response = self.qwen_llm.chat(qwen_messages)
            return response
        except Exception as e:
            logger.error(f"通义千问对话生成失败: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def _convert_role(self, role: MessageRole) -> str:
        """
        转换消息角色
        
        Args:
            role: LlamaIndex消息角色
            
        Returns:
            str: 通义千问消息角色
        """
        role_mapping = {
            MessageRole.USER: "user",
            MessageRole.ASSISTANT: "assistant",
            MessageRole.SYSTEM: "system"
        }
        return role_mapping.get(role, "user")


class QwenLlamaEmbedding(BaseEmbedding):
    """通义千问嵌入模型的LlamaIndex适配器"""
    
    def __init__(
        self,
        model_name: str = "text-embedding-v1",
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化通义千问嵌入模型适配器
        
        Args:
            model_name: 模型名称
            api_key: API密钥
        """
        super().__init__()
        
        # 如果没有提供API密钥，则从环境变量中获取
        if api_key is None:
            api_key = os.environ.get("DASHSCOPE_API_KEY")
        
        self.model_name = model_name
        self.qwen_embeddings = QwenEmbeddings(
            model_name=model_name,
            api_key=api_key,
            **kwargs
        )
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        try:
            embedding = self.qwen_embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"通义千问嵌入向量生成失败: {str(e)}")
            # 返回一个零向量作为备选
            return [0.0] * 1536  # 通义千问嵌入模型维度为1536
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入向量（兼容BaseEmbedding接口）
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        return self._get_embedding(text)
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取文本嵌入向量
        
        Args:
            texts: 输入文本列表
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        try:
            embeddings = self.qwen_embeddings.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"通义千问批量嵌入向量生成失败: {str(e)}")
            # 返回零向量列表作为备选
            return [[0.0] * 1536 for _ in range(len(texts))] 