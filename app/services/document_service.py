"""
文档处理服务模块
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Set, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database import Document, get_db
from app.schemas import DocumentStatus
from app.core.document_processor import DocumentProcessor
from app.core.vector_store import VectorStoreManager
import os

# 配置日志
# logger = logging.getLogger(__name__)
logger = logging.getLogger("app.services.document_service")

class DocumentTaskProcessor:
    """定时任务文档处理器"""
    
    def __init__(self):
        self.processing: Set[str] = set()  # 正在处理的文档ID
        self.is_running = False
        self.poll_interval = 2  # 轮询间隔（2秒，提高响应速度）
        self.retry_interval = 300  # 重试间隔（5分钟）
        
    async def start_polling(self):
        """启动定时轮询"""
        self.is_running = True
        logger.info("文档处理轮询已启动")
        
        while self.is_running:
            try:
                await self.process_pending_documents()
                await self.process_failed_documents()  # 处理失败的文档
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"轮询处理失败: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def stop_polling(self):
        """停止轮询"""
        self.is_running = False
        logger.info("文档处理轮询已停止")
    
    async def process_pending_documents(self):
        """处理待处理的文档"""
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            # 查询待处理的文档（避免重复处理）
            pending_docs = db.query(Document).filter(
                Document.status == "pending"
            ).limit(5).all()  # 限制并发数
            
            if pending_docs:
                logger.info(f"发现 {len(pending_docs)} 个待处理文档")
                
                for doc in pending_docs:
                    if doc.id not in self.processing:
                        # 标记为正在处理
                        self.processing.add(doc.id)
                        doc.status = "processing"
                        doc.process_start_time = datetime.now()
                        db.commit()
                        
                        # 异步处理文档
                        asyncio.create_task(self.process_single_document(doc.id, doc.file_path))
                        
        except Exception as e:
            logger.error(f"查询待处理文档失败: {e}")
        finally:
            db.close()
    
    async def process_failed_documents(self):
        """处理失败的文档（重试逻辑）"""
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            # 查询需要重试的失败文档
            # 条件：状态为failed、重试次数小于最大重试次数、距离上次重试超过指定时间间隔
            retry_time_threshold = datetime.now() - timedelta(seconds=self.retry_interval)
            
            failed_docs = db.query(Document).filter(
                Document.status == "failed",
                Document.retry_count < Document.max_retries,
                # 首次失败或者距离上次重试已过指定时间
                (Document.last_retry_time.is_(None)) | (Document.last_retry_time < retry_time_threshold)
            ).limit(3).all()  # 限制重试并发数
            
            if failed_docs:
                logger.info(f"发现 {len(failed_docs)} 个需要重试的失败文档")
                
                for doc in failed_docs:
                    if doc.id not in self.processing:
                        # 标记为正在重试
                        self.processing.add(doc.id)
                        doc.status = "processing"
                        doc.retry_count += 1
                        doc.last_retry_time = datetime.now()
                        doc.process_start_time = datetime.now()
                        db.commit()
                        
                        logger.info(f"开始重试文档 {doc.id}，第 {doc.retry_count} 次重试")
                        
                        # 异步处理文档
                        asyncio.create_task(self.process_single_document(
                            doc.id, doc.file_path, is_retry=True
                        ))
                        
        except Exception as e:
            logger.error(f"查询重试文档失败: {e}")
        finally:
            db.close()
    
    async def process_single_document(self, document_id: str, file_path: str, is_retry: bool = False):
        """处理单个文档 - 支持COS存储"""
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            if is_retry:
                logger.info(f"开始重试处理文档: {document_id}")
            else:
                logger.info(f"开始处理文档: {document_id}")
            
            # 获取文档信息
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"文档不存在: {document_id}")
                return
            
            # 获取处理组件
            processor = DocumentProcessor()
            
            # 获取文件扩展名
            from pathlib import Path
            if document.cos_object_key:
                file_ext = Path(document.cos_object_key).suffix.lower()
            else:
                file_ext = Path(document.file_path).suffix.lower()
            
            logger.info(f"处理文档类型: {file_ext}, 文件名: {document.filename}")
            
            # 根据环境变量选择模型类型
            embedding_type = os.getenv("EMBEDDING_TYPE", "qwen")
            vector_store = VectorStoreManager(
                embedding_type=embedding_type,
                embedding_config={
                    "model": os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1")
                }
            )
            
            # 处理文档 - 支持COS存储
            result = processor.process_document(
                document_id=document_id,
                storage_type=document.storage_type,
                file_path=document.file_path,
                cos_object_key=document.cos_object_key
            )
            
            if result["success"]:
                try:
                    # 创建向量存储
                    logger.info(f"创建文档向量集合: {document_id}")
                    create_result = vector_store.create_document_collection(document_id)
                    if not create_result:
                        raise Exception("创建向量集合失败")
                    
                    # 添加向量
                    logger.info(f"添加文档块到向量存储，共{len(result['chunks'])}个块")
                    add_result = vector_store.add_document_chunks(document_id, result["chunks"])
                    if not add_result:
                        raise Exception("添加向量数据失败")
                    
                    # 更新数据库状态
                    document.status = "completed"
                    document.sync_status = "available"  # 设置为可同步状态
                    document.pages = result["metadata"]["pages"]
                    document.chunk_count = result["chunk_count"]
                    document.process_end_time = datetime.now()
                    # 如果文件类型字段为空，从元数据中获取
                    if not document.file_type and result["metadata"].get("file_type"):
                        document.file_type = result["metadata"]["file_type"]
                    # 成功后清空错误信息
                    document.error_message = None
                    db.commit()
                    
                    if is_retry:
                        logger.info(f"文档 {document_id} 重试处理成功，共{result['chunk_count']}个文本块")
                    else:
                        logger.info(f"文档 {document_id} 处理完成，共{result['chunk_count']}个文本块")
                except Exception as ve:
                    # 向量化失败
                    logger.error(f"向量化处理失败: {str(ve)}")
                    document.status = "failed"
                    error_msg = f"向量化处理失败: {str(ve)}"
                    document.error_message = error_msg
                    db.commit()
                    logger.error(f"文档 {document_id} 向量化失败: {error_msg}")
            else:
                # 处理失败
                if document.retry_count >= document.max_retries:
                    document.status = "failed_permanently"
                    error_msg = f"文档处理失败，已达最大重试次数({document.max_retries})。最后错误: {result['error']}"
                    logger.error(f"文档 {document_id} 永久失败: {error_msg}")
                else:
                    document.status = "failed"
                    error_msg = f"处理失败(第{document.retry_count}次重试): {result['error']}"
                    logger.error(f"文档 {document_id} 处理失败，将稍后重试: {result['error']}")
                
                document.error_message = error_msg
                db.commit()
        except Exception as e:
            logger.error(f"处理文档 {document_id} 时发生异常: {str(e)}", exc_info=True)
            # 更新文档状态为失败
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    if document.retry_count >= document.max_retries:
                        document.status = "failed_permanently"
                        logger.error(f"文档 {document_id} 永久失败: 已达最大重试次数")
                    else:
                        document.status = "failed"
                    document.error_message = f"处理异常: {str(e)}"
                    db.commit()
            except Exception as db_error:
                logger.error(f"更新文档状态失败: {str(db_error)}")
        finally:
            # 从处理集合中移除
            if document_id in self.processing:
                self.processing.remove(document_id)
            db.close()

    def get_processing_status(self) -> Dict[str, Any]:
        """获取处理状态"""
        return {
            "is_running": self.is_running,
            "processing_count": len(self.processing),
            "processing_documents": list(self.processing)
        }

# 创建全局文档处理器实例
document_task_processor = DocumentTaskProcessor() 