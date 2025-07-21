"""
LlamaIndex适配器，将LlamaIndex集成到现有系统中
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import uuid

from app.database import get_db, Document as DBDocument
from app.schemas import DocumentCreate, DocumentStatus
from app.llamaindex.document_loader import CustomDocumentReader
from app.llamaindex.index_manager import LlamaIndexManager
from app.llamaindex.query_engine import LlamaQueryEngine
from app.utils.file_storage import FileStorageManager

logger = logging.getLogger(__name__)

class LlamaIndexAdapter:
    """LlamaIndex适配器，将LlamaIndex集成到现有系统中"""
    
    def __init__(
        self,
        embedding_model_name: str = "text-embedding-3-small",
        llm_model_name: str = "gpt-3.5-turbo",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        similarity_top_k: int = 3,
        similarity_cutoff: float = 0.7
    ):
        """
        初始化LlamaIndex适配器
        
        Args:
            embedding_model_name: 嵌入模型名称
            llm_model_name: LLM模型名称
            chunk_size: 文本分块大小
            chunk_overlap: 文本分块重叠大小
            similarity_top_k: 检索的最大相似文档数量
            similarity_cutoff: 相似度阈值，低于此值的文档将被过滤
        """
        self.index_manager = LlamaIndexManager(
            embedding_model_name=embedding_model_name,
            llm_model_name=llm_model_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        self.query_engine = LlamaQueryEngine(
            index_manager=self.index_manager,
            similarity_top_k=similarity_top_k,
            similarity_cutoff=similarity_cutoff
        )
        
        self.file_storage = FileStorageManager()
    
    def process_document(self, document_id: str, db=None) -> bool:
        """
        处理文档
        
        Args:
            document_id: 文档ID
            db: 数据库会话
            
        Returns:
            bool: 处理是否成功
        """
        logger.info(f"使用LlamaIndex处理文档: {document_id}")
        
        # 获取数据库会话
        if db is None:
            db = next(get_db())
        
        try:
            # 获取文档记录
            db_document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
            if not db_document:
                logger.error(f"文档不存在: {document_id}")
                return False
            
            # 更新文档状态为处理中
            db_document.status = DocumentStatus.PROCESSING
            db.commit()
            
            # 获取文档文件路径
            file_path = self.file_storage.get_file_path(db_document.file_path)
            if not os.path.exists(file_path):
                logger.error(f"文档文件不存在: {file_path}")
                db_document.status = DocumentStatus.FAILED
                db_document.error_message = "文档文件不存在"
                db.commit()
                return False
            
            # 处理文档文件并创建索引
            collection_name = f"doc_{document_id}"
            try:
                self.index_manager.process_document(file_path, collection_name)
            except Exception as e:
                logger.error(f"处理文档文件失败: {str(e)}")
                db_document.status = DocumentStatus.FAILED
                db_document.error_message = f"处理文档文件失败: {str(e)}"
                db.commit()
                return False
            
            # 更新文档状态为已处理
            db_document.status = DocumentStatus.PROCESSED
            db_document.collection_name = collection_name
            db.commit()
            
            logger.info(f"文档处理成功: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"处理文档时发生错误: {str(e)}")
            if db_document:
                db_document.status = DocumentStatus.FAILED
                db_document.error_message = f"处理文档时发生错误: {str(e)}"
                db.commit()
            return False
    
    def query_document(
        self,
        document_id: str,
        query_text: str,
        similarity_top_k: int = None,
        similarity_cutoff: float = None,
        db=None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        查询文档
        
        Args:
            document_id: 文档ID
            query_text: 查询文本
            similarity_top_k: 检索的最大相似文档数量
            similarity_cutoff: 相似度阈值，低于此值的文档将被过滤
            db: 数据库会话
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: 查询响应和检索到的节点源信息
        """
        logger.info(f"查询文档: {document_id}, 查询: {query_text}")
        
        # 获取数据库会话
        if db is None:
            db = next(get_db())
        
        try:
            # 获取文档记录
            db_document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
            if not db_document:
                logger.error(f"文档不存在: {document_id}")
                return "文档不存在", []
            
            # 检查文档状态
            if db_document.status != DocumentStatus.PROCESSED:
                logger.error(f"文档未处理完成: {document_id}, 状态: {db_document.status}")
                return f"文档未处理完成，当前状态: {db_document.status}", []
            
            # 获取集合名称
            collection_name = db_document.collection_name
            if not collection_name:
                collection_name = f"doc_{document_id}"
            
            # 执行查询
            response, source_nodes = self.query_engine.query(
                collection_name=collection_name,
                query_text=query_text,
                similarity_top_k=similarity_top_k,
                similarity_cutoff=similarity_cutoff
            )
            
            return response, source_nodes
            
        except Exception as e:
            logger.error(f"查询文档时发生错误: {str(e)}")
            return f"查询文档时发生错误: {str(e)}", []
    
    def upload_and_process_document(
        self,
        file_path: str,
        file_name: str = None,
        user_id: str = None,
        db=None
    ) -> Optional[str]:
        """
        上传并处理文档
        
        Args:
            file_path: 文件路径
            file_name: 文件名
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            Optional[str]: 文档ID，如果处理失败则返回None
        """
        logger.info(f"上传并处理文档: {file_path}")
        
        # 获取数据库会话
        if db is None:
            db = next(get_db())
        
        try:
            # 生成文档ID
            document_id = str(uuid.uuid4())
            
            # 如果没有提供文件名，则使用原始文件名
            if file_name is None:
                file_name = os.path.basename(file_path)
            
            # 存储文件
            stored_path = self.file_storage.store_file(file_path, document_id)
            
            # 创建文档记录
            document_create = DocumentCreate(
                id=document_id,
                title=file_name,
                file_path=stored_path,
                user_id=user_id or "system"
            )
            
            # 保存到数据库
            db_document = DBDocument(**document_create.dict())
            db.add(db_document)
            db.commit()
            
            # 处理文档
            success = self.process_document(document_id, db)
            if not success:
                logger.error(f"处理文档失败: {document_id}")
                return None
            
            return document_id
            
        except Exception as e:
            logger.error(f"上传并处理文档时发生错误: {str(e)}")
            return None 