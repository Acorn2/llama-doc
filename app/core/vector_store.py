import os
import logging
from typing import List, Dict, Optional
from .model_factory import ModelFactory
from .qdrant_adapter import QdrantAdapter

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """向量存储管理器 - Qdrant版本"""
    
    def __init__(
        self, 
        qdrant_host: str = None,
        qdrant_port: int = None,
        qdrant_https: bool = False,
        qdrant_api_key: str = None,
        embedding_type: str = None,
        embedding_config: dict = None
    ):
        # Qdrant配置
        self.qdrant_host = qdrant_host or os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))
        self.qdrant_https = qdrant_https or os.getenv("QDRANT_HTTPS", "false").lower() == "true"
        self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        
        # 初始化Qdrant客户端
        self.qdrant_client = QdrantAdapter(
            host=self.qdrant_host,
            port=self.qdrant_port,
            use_https=self.qdrant_https,
            api_key=self.qdrant_api_key
        )
        
        # 初始化嵌入模型
        self.embeddings = ModelFactory.create_embeddings(
            model_type=embedding_type,
            **(embedding_config or {})
        )
        
        logger.info(f"Qdrant向量存储管理器初始化完成 - 服务器: {self.qdrant_host}:{self.qdrant_port}")
    
    def create_document_collection(self, document_id: str) -> bool:
        """为文档创建向量集合"""
        try:
            collection_name = f"doc_{document_id}"
            
            # 获取嵌入维度
            dimension = 1536  # 默认维度
            if hasattr(self.embeddings, 'embed_query'):
                test_embedding = self.embeddings.embed_query("test")
                dimension = len(test_embedding)
            
            return self.qdrant_client.create_collection(collection_name, dimension)
            
        except Exception as e:
            logger.error(f"创建文档集合失败: {str(e)}")
            return False
    
    def add_document_chunks(self, document_id: str, chunks: List[Dict]) -> bool:
        """添加文档块到向量存储"""
        try:
            collection_name = f"doc_{document_id}"
            
            # 准备文本用于嵌入
            texts = [chunk["content"] for chunk in chunks]
            
            # 生成嵌入向量
            logger.info(f"正在为 {len(texts)} 个文档块生成嵌入向量...")
            embeddings = self.embeddings.embed_documents(texts)
            
            # 准备向量点数据
            points = []
            for i, chunk in enumerate(chunks):
                point = {
                    'id': chunk["chunk_id"],
                    'vector': embeddings[i],
                    'payload': {
                        "chunk_id": chunk["chunk_id"],
                        "chunk_index": chunk["chunk_index"],
                        "document_id": document_id,
                        "content": chunk["content"],
                        "chunk_length": chunk["chunk_length"],
                        "keywords": chunk.get("keywords", []),
                        "summary": chunk.get("summary", ""),
                        "quality_score": chunk.get("quality_score", 0.5)
                    }
                }
                points.append(point)
            
            # 添加到Qdrant
            return self.qdrant_client.add_points(collection_name, points)
            
        except Exception as e:
            logger.error(f"添加文档块失败: {str(e)}")
            return False
    
    def search_similar_chunks(
        self, 
        document_id: str, 
        query: str, 
        k: int = 5
    ) -> List[Dict]:
        """搜索相似文档块"""
        try:
            collection_name = f"doc_{document_id}"
            
            # 生成查询向量
            query_embedding = self.embeddings.embed_query(query)
            
            # 执行搜索
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=k,
                with_payload=True
            )
            
            # 格式化结果
            formatted_results = []
            for result in search_results:
                payload = result['payload']
                formatted_results.append({
                    "content": payload.get("content", ""),
                    "chunk_id": payload.get("chunk_id", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "similarity_score": result['score'],
                    "metadata": {
                        "keywords": payload.get("keywords", []),
                        "summary": payload.get("summary", ""),
                        "quality_score": payload.get("quality_score", 0.5),
                        "chunk_length": payload.get("chunk_length", 0)
                    }
                })
            
            logger.info(f"搜索完成，找到 {len(formatted_results)} 个相似块")
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索相似块失败: {str(e)}")
            return []
    
    def delete_document_collection(self, document_id: str) -> bool:
        """删除文档的向量集合"""
        try:
            collection_name = f"doc_{document_id}"
            return self.qdrant_client.delete_collection(collection_name)
            
        except Exception as e:
            logger.error(f"删除文档集合失败: {str(e)}")
            return False
    
    def get_collection_stats(self, document_id: str) -> Dict:
        """获取集合统计信息"""
        try:
            collection_name = f"doc_{document_id}"
            return self.qdrant_client.get_collection_info(collection_name)
            
        except Exception as e:
            logger.error(f"获取集合统计失败: {str(e)}")
            return {}
    
    def list_all_collections(self) -> List[str]:
        """列出所有集合"""
        return self.qdrant_client.list_collections() 