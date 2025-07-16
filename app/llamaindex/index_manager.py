"""
LlamaIndex索引管理器，用于构建和管理文档索引
"""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex, 
    StorageContext,
    Settings,
    ServiceContext
)
from llama_index.core.schema import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI

from app.core.model_factory import get_embedding_model
from app.core.qdrant_adapter import QdrantAdapter
from app.llamaindex.document_loader import CustomPDFReader

logger = logging.getLogger(__name__)

class LlamaIndexManager:
    """LlamaIndex索引管理器"""
    
    def __init__(
        self,
        qdrant_client=None,
        embedding_model_name: str = "text-embedding-3-small",
        llm_model_name: str = "gpt-3.5-turbo",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        初始化LlamaIndex管理器
        
        Args:
            qdrant_client: Qdrant客户端实例
            embedding_model_name: 嵌入模型名称
            llm_model_name: LLM模型名称
            chunk_size: 文本分块大小
            chunk_overlap: 文本分块重叠大小
        """
        self.qdrant_adapter = QdrantAdapter() if qdrant_client is None else qdrant_client
        self.embedding_model_name = embedding_model_name
        self.llm_model_name = llm_model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 配置LlamaIndex设置
        self._configure_settings()
    
    def _configure_settings(self):
        """配置LlamaIndex全局设置"""
        # 设置嵌入模型
        if "text-embedding" in self.embedding_model_name:
            # 使用OpenAI嵌入模型
            embed_model = get_embedding_model(self.embedding_model_name)
        else:
            # 使用HuggingFace嵌入模型
            embed_model = HuggingFaceEmbedding(
                model_name=self.embedding_model_name
            )
        
        # 设置LLM模型
        if "gpt" in self.llm_model_name:
            llm = OpenAI(model=self.llm_model_name)
        else:
            # 默认使用OpenAI
            llm = OpenAI(model="gpt-3.5-turbo")
        
        # 配置全局设置
        Settings.embed_model = embed_model
        Settings.llm = llm
        Settings.chunk_size = self.chunk_size
        Settings.chunk_overlap = self.chunk_overlap
    
    def create_vector_store(self, collection_name: str) -> QdrantVectorStore:
        """
        创建Qdrant向量存储
        
        Args:
            collection_name: 集合名称
            
        Returns:
            QdrantVectorStore: Qdrant向量存储实例
        """
        # 确保集合存在
        self.qdrant_adapter.create_collection_if_not_exists(collection_name)
        
        # 创建Qdrant向量存储
        vector_store = QdrantVectorStore(
            client=self.qdrant_adapter.client,
            collection_name=collection_name
        )
        
        return vector_store
    
    def create_index_from_documents(
        self,
        documents: List[Document],
        collection_name: str
    ) -> VectorStoreIndex:
        """
        从文档创建索引
        
        Args:
            documents: 文档列表
            collection_name: 集合名称
            
        Returns:
            VectorStoreIndex: 向量存储索引
        """
        logger.info(f"为集合 {collection_name} 创建索引，文档数量: {len(documents)}")
        
        # 创建向量存储
        vector_store = self.create_vector_store(collection_name)
        
        # 创建存储上下文
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 创建节点解析器
        node_parser = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        # 创建服务上下文
        service_context = ServiceContext.from_defaults(
            node_parser=node_parser
        )
        
        # 创建索引
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            service_context=service_context
        )
        
        logger.info(f"成功创建索引，集合名称: {collection_name}")
        return index
    
    def load_index(self, collection_name: str) -> VectorStoreIndex:
        """
        加载已有索引
        
        Args:
            collection_name: 集合名称
            
        Returns:
            VectorStoreIndex: 向量存储索引
        """
        # 创建向量存储
        vector_store = self.create_vector_store(collection_name)
        
        # 创建存储上下文
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 加载索引
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context
        )
        
        logger.info(f"成功加载索引，集合名称: {collection_name}")
        return index
    
    def process_pdf(self, file_path: str, collection_name: str) -> VectorStoreIndex:
        """
        处理PDF文件并创建索引
        
        Args:
            file_path: PDF文件路径
            collection_name: 集合名称
            
        Returns:
            VectorStoreIndex: 向量存储索引
        """
        # 加载PDF文件
        pdf_reader = CustomPDFReader()
        documents = pdf_reader.load_data(file_path)
        
        # 提取元数据
        metadata = pdf_reader.extract_metadata(file_path)
        
        # 为文档添加元数据
        for doc in documents:
            doc.metadata.update(metadata)
        
        # 创建索引
        index = self.create_index_from_documents(documents, collection_name)
        
        return index 