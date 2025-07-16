"""
LlamaIndex查询引擎，用于处理用户查询
"""
import logging
from typing import List, Dict, Any, Optional, Tuple

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.response_synthesizers import CompactAndRefine

from app.llamaindex.index_manager import LlamaIndexManager

logger = logging.getLogger(__name__)

class LlamaQueryEngine:
    """LlamaIndex查询引擎"""
    
    def __init__(
        self,
        index_manager: LlamaIndexManager = None,
        similarity_top_k: int = 3,
        similarity_cutoff: float = 0.7
    ):
        """
        初始化查询引擎
        
        Args:
            index_manager: LlamaIndex管理器实例
            similarity_top_k: 检索的最大相似文档数量
            similarity_cutoff: 相似度阈值，低于此值的文档将被过滤
        """
        self.index_manager = index_manager or LlamaIndexManager()
        self.similarity_top_k = similarity_top_k
        self.similarity_cutoff = similarity_cutoff
    
    def create_query_engine(
        self,
        index: VectorStoreIndex,
        similarity_top_k: int = None,
        similarity_cutoff: float = None
    ) -> RetrieverQueryEngine:
        """
        创建查询引擎
        
        Args:
            index: 向量存储索引
            similarity_top_k: 检索的最大相似文档数量
            similarity_cutoff: 相似度阈值，低于此值的文档将被过滤
            
        Returns:
            RetrieverQueryEngine: 查询引擎实例
        """
        # 使用默认值或传入的参数
        similarity_top_k = similarity_top_k or self.similarity_top_k
        similarity_cutoff = similarity_cutoff or self.similarity_cutoff
        
        # 创建检索器
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=similarity_top_k
        )
        
        # 创建相似度后处理器
        postprocessor = SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)
        
        # 创建响应合成器
        response_synthesizer = CompactAndRefine()
        
        # 创建查询引擎
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            node_postprocessors=[postprocessor],
            response_synthesizer=response_synthesizer
        )
        
        return query_engine
    
    def query(
        self,
        collection_name: str,
        query_text: str,
        similarity_top_k: int = None,
        similarity_cutoff: float = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        执行查询
        
        Args:
            collection_name: 集合名称
            query_text: 查询文本
            similarity_top_k: 检索的最大相似文档数量
            similarity_cutoff: 相似度阈值，低于此值的文档将被过滤
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: 查询响应和检索到的节点源信息
        """
        logger.info(f"执行查询: {query_text}, 集合: {collection_name}")
        
        # 加载索引
        index = self.index_manager.load_index(collection_name)
        
        # 创建查询引擎
        query_engine = self.create_query_engine(
            index,
            similarity_top_k=similarity_top_k,
            similarity_cutoff=similarity_cutoff
        )
        
        # 执行查询
        response = query_engine.query(query_text)
        
        # 提取源节点信息
        source_nodes = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                source_nodes.append({
                    "text": node.text,
                    "score": node.score if hasattr(node, "score") else None,
                    "metadata": node.metadata
                })
        
        logger.info(f"查询完成，检索到 {len(source_nodes)} 个相关文档片段")
        
        return str(response), source_nodes 