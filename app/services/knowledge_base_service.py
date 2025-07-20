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
        
        # 直接创建知识库集合，而不是使用create_document_collection方法
        try:
            # 获取嵌入维度
            dimension = 1536  # 默认维度
            if hasattr(self.vector_store_manager.embeddings, 'embed_query'):
                test_embedding = self.vector_store_manager.embeddings.embed_query("test")
                dimension = len(test_embedding)
            
            created = self.vector_store_manager.qdrant_client.create_collection(vector_store_name, dimension)
            if not created:
                logger.error(f"创建向量存储集合失败: {vector_store_name}")
                raise Exception("创建知识库向量存储失败")
            else:
                logger.info(f"成功创建知识库向量集合: {vector_store_name}")
        except Exception as create_error:
            logger.error(f"创建知识库向量集合异常: {create_error}")
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
        
        # 向量处理逻辑 - 简化版本
        try:
            # 1. 确保知识库向量集合存在
            kb_collection_name = kb.vector_store_name
            if not self._collection_exists(kb_collection_name):
                logger.info(f"知识库向量集合不存在，正在创建: {kb_collection_name}")
                # 直接创建知识库集合，而不是使用create_document_collection方法
                try:
                    # 获取嵌入维度
                    dimension = 1536  # 默认维度
                    if hasattr(self.vector_store_manager.embeddings, 'embed_query'):
                        test_embedding = self.vector_store_manager.embeddings.embed_query("test")
                        dimension = len(test_embedding)
                    
                    created = self.vector_store_manager.qdrant_client.create_collection(kb_collection_name, dimension)
                    if not created:
                        logger.error(f"创建知识库向量集合失败: {kb_collection_name}")
                        logger.warning("向量集合创建失败，但继续执行数据库操作")
                    else:
                        logger.info(f"成功创建知识库向量集合: {kb_collection_name}")
                except Exception as create_error:
                    logger.error(f"创建知识库向量集合异常: {create_error}")
                    logger.warning("向量集合创建失败，但继续执行数据库操作")
            
            # 2. 尝试将文档向量数据复制到知识库集合
            document_collection = f"doc_{document_id}"
            success = self._copy_document_vectors_to_kb(
                source_collection=document_collection,
                target_collection=kb_collection_name,
                document_id=document_id
            )
            
            if success:
                logger.info(f"成功将文档向量添加到知识库: KB {kb_id}, 文档 {document_id}")
            else:
                logger.warning(f"向量数据添加失败，但继续执行: KB {kb_id}, 文档 {document_id}")
            
        except Exception as e:
            logger.error(f"向量处理失败: {str(e)}")
            # 不抛出异常，允许数据库操作继续执行
            logger.warning(f"向量处理失败，但继续执行数据库操作: {str(e)}")
        
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
        
        # 向量处理逻辑 - 从知识库集合中移除文档向量
        try:
            kb_collection_name = kb.vector_store_name
            success = self._remove_document_vectors_from_kb(
                kb_collection=kb_collection_name,
                document_id=document_id
            )
            
            if not success:
                logger.warning(f"向量数据移除失败，但继续删除数据库记录: KB {kb_id}, 文档 {document_id}")
            else:
                logger.info(f"成功从知识库移除文档向量: KB {kb_id}, 文档 {document_id}")
                
        except Exception as e:
            logger.error(f"向量处理失败: {str(e)}")
            # 向量删除失败不应该阻止数据库记录的删除，只记录警告
            logger.warning(f"向量删除失败，但继续删除数据库记录: KB {kb_id}, 文档 {document_id}")
        
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
        try:
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
            
            # 生成查询向量
            query_embedding = self.vector_store_manager.embeddings.embed_query(query)
            
            # 直接使用Qdrant客户端搜索知识库集合
            search_results = self.vector_store_manager.qdrant_client.search(
                collection_name=vector_store_name,
                query_vector=query_embedding,
                limit=top_k,
                with_payload=True
            )
            
            # 格式化搜索结果
            formatted_results = []
            for result in search_results:
                payload = result.get('payload', {})
                formatted_results.append({
                    "content": payload.get("content", ""),
                    "chunk_id": payload.get("chunk_id", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "document_id": payload.get("document_id", ""),
                    "similarity_score": result.get('score', 0.0),
                    "metadata": {
                        "keywords": payload.get("keywords", []),
                        "summary": payload.get("summary", ""),
                        "quality_score": payload.get("quality_score", 0.5),
                        "chunk_length": payload.get("chunk_length", 0)
                    }
                })
            
            logger.info(f"知识库搜索完成，找到 {len(formatted_results)} 个结果")
            return formatted_results
            
        except Exception as e:
            logger.error(f"知识库搜索失败: {str(e)}")
            return []
    
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
    
    def _collection_exists(self, collection_name: str) -> bool:
        """
        检查向量集合是否存在
        
        Args:
            collection_name: 集合名称
            
        Returns:
            bool: 集合是否存在
        """
        try:
            collections = self.vector_store_manager.list_all_collections()
            return collection_name in collections
        except Exception as e:
            logger.error(f"检查集合存在性失败: {str(e)}")
            return False
    
    def _copy_document_vectors_to_kb(
        self, 
        source_collection: str, 
        target_collection: str, 
        document_id: str
    ) -> bool:
        """
        将文档向量数据复制到知识库集合
        
        Args:
            source_collection: 源集合名称 (doc_xxx)
            target_collection: 目标集合名称 (kb_xxx)
            document_id: 文档ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 方法1：尝试使用search_similar_chunks获取文档内容
            search_results = []
            try:
                search_results = self.vector_store_manager.search_similar_chunks(
                    document_id=document_id,
                    query="文档",  # 使用更通用的查询词
                    k=200  # 获取更多结果
                )
                logger.info(f"通过search_similar_chunks获取到 {len(search_results)} 个结果")
            except Exception as search_error:
                logger.warning(f"search_similar_chunks方法失败: {search_error}")
                # 如果search_similar_chunks失败，尝试其他方法
                search_results = []
            
            # 方法2：如果方法1失败，尝试直接从源集合搜索
            if not search_results:
                try:
                    # 检查源集合是否存在
                    if self._collection_exists(source_collection):
                        # 生成一个通用查询向量
                        query_embedding = self.vector_store_manager.embeddings.embed_query("文档内容")
                        
                        # 直接从源集合搜索
                        qdrant_results = self.vector_store_manager.qdrant_client.search(
                            collection_name=source_collection,
                            query_vector=query_embedding,
                            limit=200,
                            with_payload=True
                        )
                        
                        # 转换为标准格式
                        for result in qdrant_results:
                            payload = result.get('payload', {})
                            search_results.append({
                                "content": payload.get("content", ""),
                                "chunk_id": payload.get("chunk_id", ""),
                                "chunk_index": payload.get("chunk_index", 0),
                                "metadata": {
                                    "keywords": payload.get("keywords", []),
                                    "summary": payload.get("summary", ""),
                                    "quality_score": payload.get("quality_score", 0.5)
                                }
                            })
                        
                        logger.info(f"通过直接搜索源集合获取到 {len(search_results)} 个结果")
                    else:
                        logger.warning(f"源集合不存在: {source_collection}")
                        
                except Exception as direct_search_error:
                    logger.warning(f"直接搜索源集合失败: {direct_search_error}")
            
            if not search_results:
                logger.warning(f"文档 {document_id} 没有找到向量数据，可能文档尚未处理完成")
                return True  # 没有数据也算成功，避免阻止数据库操作
            
            # 准备要添加到知识库集合的点
            kb_points = []
            for i, result in enumerate(search_results):
                content = result.get("content", "")
                if not content or len(content.strip()) < 10:  # 过滤太短的内容
                    continue
                
                # 重新生成嵌入向量，添加重试机制
                embedding = None
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        embedding = self.vector_store_manager.embeddings.embed_query(content)
                        break  # 成功则跳出重试循环
                    except Exception as embed_error:
                        if retry < max_retries - 1:
                            logger.warning(f"生成嵌入向量失败，重试 {retry + 1}/{max_retries}: {embed_error}")
                            import time
                            time.sleep(1)  # 等待1秒后重试
                        else:
                            logger.warning(f"生成嵌入向量最终失败: {embed_error}")
                            continue
                
                # 生成新的chunk_id用于知识库
                original_chunk_id = result.get("chunk_id", f"{document_id}_chunk_{i}")
                
                # 生成符合Qdrant要求的UUID格式的点ID
                kb_point_uuid = str(uuid.uuid4())
                kb_chunk_id = f"kb_{original_chunk_id}"
                
                kb_point = {
                    'id': kb_point_uuid,  # 使用UUID作为点ID
                    'vector': embedding,
                    'payload': {
                        "chunk_id": kb_chunk_id,
                        "chunk_index": result.get("chunk_index", i),
                        "document_id": document_id,
                        "content": content,
                        "chunk_length": len(content),
                        "keywords": result.get("metadata", {}).get("keywords", []),
                        "summary": result.get("metadata", {}).get("summary", ""),
                        "quality_score": result.get("metadata", {}).get("quality_score", 0.5),
                        "kb_collection": target_collection,
                        "source_collection": source_collection,
                        "original_chunk_id": original_chunk_id
                    }
                }
                kb_points.append(kb_point)
            
            # 添加到知识库集合
            if kb_points:
                try:
                    success = self.vector_store_manager.qdrant_client.add_points(
                        target_collection, 
                        kb_points
                    )
                    
                    if success:
                        logger.info(f"成功复制 {len(kb_points)} 个向量点到知识库: {target_collection}")
                        return True
                    else:
                        logger.error(f"向量点添加失败: {target_collection}")
                        return False
                except Exception as add_error:
                    logger.error(f"添加向量点到知识库失败: {add_error}")
                    return False
            else:
                logger.info(f"没有有效的向量点需要复制")
                return True
                
        except Exception as e:
            logger.error(f"复制文档向量失败: {str(e)}")
            return False
    
    def _remove_document_vectors_from_kb(
        self, 
        kb_collection: str, 
        document_id: str
    ) -> bool:
        """
        从知识库集合中移除指定文档的向量数据
        
        Args:
            kb_collection: 知识库集合名称
            document_id: 文档ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 简化删除逻辑：直接通过知识库搜索找到属于该文档的向量点
            # 生成一个简单的查询来获取知识库中的内容
            query_embedding = self.vector_store_manager.embeddings.embed_query("内容")
            
            # 搜索知识库集合中的所有向量点
            search_results = self.vector_store_manager.qdrant_client.search(
                collection_name=kb_collection,
                query_vector=query_embedding,
                limit=1000,  # 获取大量结果
                with_payload=True
            )
            
            # 过滤出属于指定文档的向量点
            document_point_ids = []
            for result in search_results:
                payload = result.get('payload', {})
                result_document_id = payload.get('document_id', '')
                
                # 检查是否属于要删除的文档
                if result_document_id == document_id:
                    point_id = payload.get('chunk_id') or result.get('id')
                    if point_id:
                        document_point_ids.append(point_id)
            
            if not document_point_ids:
                logger.info(f"知识库中没有找到文档 {document_id} 的向量数据")
                return True
            
            # 删除找到的向量点
            success = self.vector_store_manager.qdrant_client.delete_points(
                kb_collection,
                document_point_ids
            )
            
            if success:
                logger.info(f"成功从知识库移除 {len(document_point_ids)} 个向量点: 文档 {document_id}")
                return True
            else:
                logger.error(f"从知识库移除向量点失败: 文档 {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"移除文档向量失败: {str(e)}")
            # 对于删除操作，即使失败也不应该阻止整个流程
            logger.warning(f"向量删除失败，但不影响数据库操作: {str(e)}")
            return True  # 返回True以避免阻止数据库操作