import uuid
import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.database import KnowledgeBase, KnowledgeBaseDocument, Document
from app.core.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

class KnowledgeBaseManager:
    """知识库管理模块"""
    
    def __init__(self, vector_store_manager=None):
        self.vector_store_manager = vector_store_manager or VectorStoreManager()
    
    def create_knowledge_base(self, db: Session, name: str, description: Optional[str] = None) -> KnowledgeBase:
        """
        创建知识库
        
        Args:
            db: 数据库会话
            name: 知识库名称
            description: 知识库描述
            
        Returns:
            KnowledgeBase: 创建的知识库对象
        """
        # 生成唯一ID
        kb_id = str(uuid.uuid4())
        
        # 创建向量存储集合
        vector_store_name = f"kb_{kb_id}"
        created = self.vector_store_manager.create_document_collection(vector_store_name)
        
        if not created:
            logger.error(f"创建向量存储集合失败: {vector_store_name}")
            raise Exception("创建知识库向量存储失败")
        
        # 创建知识库记录
        kb = KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            vector_store_name=vector_store_name,
            document_count=0,
            status="active"
        )
        
        db.add(kb)
        db.commit()
        db.refresh(kb)
        
        logger.info(f"成功创建知识库: {kb.id}, 名称: {kb.name}")
        return kb
    
    def add_document_to_kb(
        self, 
        db: Session, 
        kb_id: str, 
        document_id: str
    ) -> Optional[KnowledgeBaseDocument]:
        """
        添加文档到知识库
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            document_id: 文档ID
            
        Returns:
            KnowledgeBaseDocument: 创建的知识库文档关联对象，如果已存在则返回None
        """
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"知识库不存在: {kb_id}")
            raise ValueError("知识库不存在")
        
        # 检查文档是否存在
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"文档不存在: {document_id}")
            raise ValueError("文档不存在")
        
        # 检查文档状态
        if document.status != "completed":
            logger.error(f"文档状态不允许添加到知识库: {document.status}")
            raise ValueError(f"文档状态为 {document.status}，无法添加到知识库")
        
        # 检查文档是否已经在知识库中
        existing = db.query(KnowledgeBaseDocument).filter(
            KnowledgeBaseDocument.kb_id == kb_id,
            KnowledgeBaseDocument.document_id == document_id
        ).first()
        
        if existing:
            logger.info(f"文档已在知识库中: KB {kb_id}, 文档 {document_id}")
            return None
        
        # 创建关联记录
        kb_doc = KnowledgeBaseDocument(
            id=str(uuid.uuid4()),
            kb_id=kb_id,
            document_id=document_id
        )
        
        db.add(kb_doc)
        
        # 更新知识库文档计数
        kb.document_count += 1
        
        db.commit()
        db.refresh(kb_doc)
        
        logger.info(f"成功添加文档到知识库: KB {kb_id}, 文档 {document_id}")
        return kb_doc
    
    def remove_document_from_kb(
        self, 
        db: Session, 
        kb_id: str, 
        document_id: str
    ) -> bool:
        """
        从知识库移除文档
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            document_id: 文档ID
            
        Returns:
            bool: 操作是否成功
        """
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"知识库不存在: {kb_id}")
            raise ValueError("知识库不存在")
        
        # 查找关联记录
        kb_doc = db.query(KnowledgeBaseDocument).filter(
            KnowledgeBaseDocument.kb_id == kb_id,
            KnowledgeBaseDocument.document_id == document_id
        ).first()
        
        if not kb_doc:
            logger.warning(f"文档不在知识库中: KB {kb_id}, 文档 {document_id}")
            return False
        
        # 删除关联记录
        db.delete(kb_doc)
        
        # 更新知识库文档计数
        if kb.document_count > 0:
            kb.document_count -= 1
        
        db.commit()
        
        logger.info(f"成功从知识库移除文档: KB {kb_id}, 文档 {document_id}")
        return True
    
    def search_knowledge_base(
        self, 
        kb_id: str, 
        query: str, 
        top_k: int = 5,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库内容
        
        Args:
            kb_id: 知识库ID
            query: 搜索查询
            top_k: 返回结果数量
            db: 数据库会话
            
        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        # 如果提供了数据库会话，则检查知识库是否存在
        if db:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                logger.error(f"知识库不存在: {kb_id}")
                raise ValueError("知识库不存在")
            
            vector_store_name = kb.vector_store_name
        else:
            # 否则使用默认的向量存储名称格式
            vector_store_name = f"kb_{kb_id}"
        
        # 使用向量存储搜索
        results = self.vector_store_manager.search_similar_chunks(
            vector_store_name, 
            query, 
            k=top_k
        )
        
        return results
    
    def get_knowledge_base(self, db: Session, kb_id: str) -> Optional[KnowledgeBase]:
        """
        获取知识库详细信息
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            KnowledgeBase: 知识库对象
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        return kb
    
    def list_knowledge_bases(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 10, 
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        列出所有知识库
        
        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 返回记录数
            status: 知识库状态过滤
            
        Returns:
            Dict[str, Any]: 包含知识库列表和总数的字典
        """
        query = db.query(KnowledgeBase)
        
        if status:
            query = query.filter(KnowledgeBase.status == status)
        
        total = query.count()
        items = query.order_by(KnowledgeBase.create_time.desc()).offset(skip).limit(limit).all()
        
        return {
            "items": items,
            "total": total
        }
    
    def list_kb_documents(
        self, 
        db: Session, 
        kb_id: str
    ) -> List[Document]:
        """
        列出知识库中的所有文档
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            List[Document]: 文档对象列表
        """
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"知识库不存在: {kb_id}")
            raise ValueError("知识库不存在")
        
        # 查询知识库中的文档
        documents = db.query(Document).join(
            KnowledgeBaseDocument, 
            Document.id == KnowledgeBaseDocument.document_id
        ).filter(
            KnowledgeBaseDocument.kb_id == kb_id
        ).all()
        
        return documents
    
    def update_knowledge_base(
        self, 
        db: Session, 
        kb_id: str, 
        name: Optional[str] = None, 
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[KnowledgeBase]:
        """
        更新知识库信息
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            name: 新名称
            description: 新描述
            status: 新状态
            
        Returns:
            KnowledgeBase: 更新后的知识库对象
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"知识库不存在: {kb_id}")
            return None
        
        # 更新字段
        if name is not None:
            kb.name = name
        
        if description is not None:
            kb.description = description
        
        if status is not None:
            kb.status = status
        
        db.commit()
        db.refresh(kb)
        
        logger.info(f"成功更新知识库: {kb_id}")
        return kb
    
    def delete_knowledge_base(self, db: Session, kb_id: str) -> bool:
        """
        删除知识库（逻辑删除）
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            bool: 操作是否成功
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"知识库不存在: {kb_id}")
            return False
        
        # 逻辑删除（更改状态）
        kb.status = "deleted"
        db.commit()
        
        logger.info(f"成功删除知识库: {kb_id}")
        return True 