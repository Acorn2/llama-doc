import os
import dashscope
from typing import List
from langchain.embeddings.base import Embeddings
import logging

logger = logging.getLogger(__name__)

class QwenEmbeddings(Embeddings):
    """通义千问嵌入模型适配器"""
    
    def __init__(self, model_name: str = "text-embedding-v1"):
        self.model_name = model_name
        
        # 设置API密钥
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请设置DASHSCOPE_API_KEY环境变量")
        
        dashscope.api_key = api_key
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入多个文档"""
        embeddings = []
        
        # 批量处理，避免单次请求过大
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self._get_embeddings(batch_texts)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        embeddings = self._get_embeddings([text])
        return embeddings[0] if embeddings else []
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """调用通义千问嵌入API"""
        try:
            response = dashscope.TextEmbedding.call(
                model=self.model_name,
                input=texts
            )
            
            if response.status_code == 200:
                embeddings = []
                for output in response.output['embeddings']:
                    embeddings.append(output['embedding'])
                return embeddings
            else:
                logger.error(f"通义千问嵌入API调用失败: {response.message}")
                raise Exception(f"嵌入API调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"通义千问嵌入调用异常: {str(e)}")
            raise e 