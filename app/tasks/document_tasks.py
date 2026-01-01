from app.celery_app import celery_app
from app.database import SessionLocal, Document
from app.core.document_processor import DocumentProcessor
from app.core.vector_store import VectorStoreManager
from datetime import datetime
import os
import logging
from pathlib import Path

# 获取Celery专属的logger
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, document_id: str):
    """
    后台处理文档任务
    使用 bind=True 可以访问 self (Task实例)，用于重试等操作
    """
    db = SessionLocal()
    try:
        logger.info(f"Celery开始处理文档: {document_id}")
        
        # 获取文档信息
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"文档不存在: {document_id}")
            return {"status": "error", "message": "Document not found"}
        
        # 更新状态为处理中（如果是重试，保持processing状态）
        if document.status != "processing":
            document.status = "processing"
            document.process_start_time = datetime.now()
            db.commit()
        
        # 获取处理组件
        processor = DocumentProcessor()
        
        # 获取文件扩展名
        if document.cos_object_key:
            file_ext = Path(document.cos_object_key).suffix.lower()
        else:
            file_ext = Path(document.file_path).suffix.lower()
        
        # 根据环境变量选择模型类型
        embedding_type = os.getenv("EMBEDDING_TYPE", "qwen")
        vector_store = VectorStoreManager(
            embedding_type=embedding_type,
            embedding_config={
                "model": os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1")
            }
        )
        
        # 处理文档 - 支持COS存储
        # 注意：这里是CPU密集型操作，Celery worker 会在独立进程中执行
        result = processor.process_document(
            document_id=document_id,
            storage_type=document.storage_type,
            file_path=document.file_path,
            cos_object_key=document.cos_object_key
        )
        
        if result["success"]:
            # 创建向量存储
            logger.info(f"创建文档向量集合: {document_id}")
            create_result = vector_store.create_document_collection(document_id, file_type=file_ext)
            if not create_result:
                raise Exception("创建向量集合失败")
            
            # 添加向量
            logger.info(f"添加文档块到向量存储，共{len(result['chunks'])}个块")
            add_result = vector_store.add_document_chunks(document_id, result["chunks"], file_type=file_ext)
            if not add_result:
                raise Exception("添加向量数据失败")
            
            # 更新数据库状态 - 成功
            document.status = "completed"
            document.sync_status = "available"
            document.pages = result["metadata"]["pages"]
            document.chunk_count = result["chunk_count"]
            document.process_end_time = datetime.now()
            
            # 如果文件类型字段为空，从元数据中获取
            if not document.file_type and result["metadata"].get("file_type"):
                document.file_type = result["metadata"]["file_type"]
            
            document.error_message = None
            db.commit()
            logger.info(f"文档 {document_id} 处理完成")
            return {"status": "success", "chunk_count": result["chunk_count"]}
            
        else:
            # 处理逻辑层面的失败
            error_msg = result['error']
            logger.error(f"处理失败: {error_msg}")
            
            # 手动抛出异常以触发重试机制
            raise Exception(error_msg)
            
    except Exception as exc:
        logger.error(f"任务执行异常: {exc}")
        
        # 更新数据库中的错误信息
        try:
            # 重新获取文档对象，防止事务中断
            db.expire_all()
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.error_message = str(exc)
                document.last_retry_time = datetime.now()
                db.commit()
        except:
            pass
            
        # 触发Celery重试
        # 如果达到最大重试次数，Celery会自动抛出MaxRetriesExceededError
        # 我们在最后一次失败时更新数据库状态
        if self.request.retries >= self.max_retries:
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.status = "failed"
                    document.error_message = f"由于重试达到上限而失败: {exc}"
                    db.commit()
            except:
                pass
        
        # 指数退避重试
        retry_delay = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)
        
    finally:
        db.close()
