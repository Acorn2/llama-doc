"""
向量同步服务 - 定时任务处理知识库向量数据同步
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db_session, KnowledgeBaseDocument, Document, KnowledgeBase
from app.services.knowledge_base_service import KnowledgeBaseManager

logger = logging.getLogger(__name__)

class VectorSyncProcessor:
    """向量同步处理器"""
    
    def __init__(self):
        self.is_running = False
        self.main_task = None
        self.kb_manager = KnowledgeBaseManager()
        self.sync_interval = 2  # 2秒检查一次，提高响应速度
        self.max_retry_count = 3  # 最大重试次数
        
    async def start_polling(self):
        """启动定时轮询"""
        self.is_running = True
        logger.info("向量同步轮询已启动")
        
        while self.is_running:
            try:
                await self.process_pending_vector_sync()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"向量同步轮询异常: {str(e)}")
                await asyncio.sleep(self.sync_interval)
    
    def stop_polling(self):
        """停止轮询"""
        self.is_running = False
        logger.info("向量同步轮询已停止")
    
    async def process_pending_vector_sync(self):
        """处理待同步的向量数据"""
        # 使用专门的数据库会话获取函数
        db = get_db_session()
        try:
            # 查找待同步的记录
            pending_records = self._get_pending_sync_records(db)
            
            if pending_records:
                logger.info(f"发现 {len(pending_records)} 个待同步的向量记录")
                
                for record in pending_records:
                    try:
                        await self._sync_single_record(db, record)
                    except Exception as e:
                        logger.error(f"同步记录失败 {record.id}: {str(e)}")
                        self._mark_sync_failed(db, record, str(e))
            
            # 处理失败重试
            await self._retry_failed_records(db)
            
        except Exception as e:
            logger.error(f"处理向量同步失败: {str(e)}")
        finally:
            db.close()
    
    def _get_pending_sync_records(self, db: Session) -> List[KnowledgeBaseDocument]:
        """获取待同步的记录"""
        # 查找状态为pending且文档可同步的记录
        records = db.query(KnowledgeBaseDocument).join(
            Document, KnowledgeBaseDocument.document_id == Document.id
        ).filter(
            and_(
                KnowledgeBaseDocument.vector_sync_status == "pending",
                Document.status == "completed",  # 文档处理已完成
                Document.sync_status == "available"  # 文档可同步
            )
        ).limit(10).all()  # 每次最多处理10个
        
        return records
    
    async def _sync_single_record(self, db: Session, record: KnowledgeBaseDocument):
        """同步单个记录的向量数据"""
        try:
            # 标记为同步中
            record.vector_sync_status = "syncing"
            
            # 同时更新文档的同步状态
            document = db.query(Document).filter(Document.id == record.document_id).first()
            if document:
                document.sync_status = "syncing"
            
            db.commit()
            
            logger.info(f"开始同步向量数据: KB {record.kb_id}, 文档 {record.document_id}")
            
            # 获取知识库信息
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == record.kb_id).first()
            
            if not kb or not document:
                raise ValueError("知识库或文档不存在")
            
            # 执行向量复制
            source_collection = f"doc_{record.document_id}"
            target_collection = kb.vector_store_name
            
            success = self.kb_manager._copy_document_vectors_to_kb(
                source_collection=source_collection,
                target_collection=target_collection,
                document_id=record.document_id
            )
            
            if success:
                # 标记为完成
                record.vector_sync_status = "completed"
                record.vector_sync_time = datetime.utcnow()
                record.vector_sync_error = None
                
                # 更新文档同步状态
                if document:
                    document.sync_status = "synced"
                
                db.commit()
                
                logger.info(f"向量同步成功: KB {record.kb_id}, 文档 {record.document_id}")
            else:
                raise Exception("向量复制失败")
                
        except Exception as e:
            logger.error(f"向量同步失败: KB {record.kb_id}, 文档 {record.document_id}, 错误: {str(e)}")
            self._mark_sync_failed(db, record, str(e))
            raise e
    
    def _mark_sync_failed(self, db: Session, record: KnowledgeBaseDocument, error_msg: str):
        """标记同步失败"""
        record.vector_sync_status = "failed"
        record.vector_sync_error = error_msg
        record.vector_sync_time = datetime.utcnow()
        
        # 同时更新文档的同步状态
        document = db.query(Document).filter(Document.id == record.document_id).first()
        if document:
            document.sync_status = "sync_failed"
        
        db.commit()
    
    async def _retry_failed_records(self, db: Session):
        """重试失败的记录"""
        # 查找失败且可以重试的记录（失败时间超过5分钟）
        retry_time = datetime.utcnow() - timedelta(minutes=5)
        
        failed_records = db.query(KnowledgeBaseDocument).filter(
            and_(
                KnowledgeBaseDocument.vector_sync_status == "failed",
                KnowledgeBaseDocument.vector_sync_time < retry_time
            )
        ).limit(5).all()  # 每次最多重试5个
        
        for record in failed_records:
            try:
                # 检查重试次数（通过错误信息中的重试计数）
                retry_count = self._get_retry_count(record.vector_sync_error or "")
                if retry_count < self.max_retry_count:
                    logger.info(f"重试向量同步: KB {record.kb_id}, 文档 {record.document_id}, 第{retry_count + 1}次重试")
                    
                    # 重置为pending状态进行重试
                    record.vector_sync_status = "pending"
                    record.vector_sync_error = f"重试次数: {retry_count + 1}"
                    db.commit()
                else:
                    logger.warning(f"向量同步达到最大重试次数: KB {record.kb_id}, 文档 {record.document_id}")
                    
            except Exception as e:
                logger.error(f"重试处理失败: {str(e)}")
    
    def _get_retry_count(self, error_msg: str) -> int:
        """从错误信息中提取重试次数"""
        try:
            if "重试次数:" in error_msg:
                return int(error_msg.split("重试次数:")[1].strip().split()[0])
        except:
            pass
        return 0
    
    def get_sync_status(self, db: Session) -> dict:
        """获取同步状态统计"""
        try:
            pending_count = db.query(KnowledgeBaseDocument).filter(
                KnowledgeBaseDocument.vector_sync_status == "pending"
            ).count()
            
            syncing_count = db.query(KnowledgeBaseDocument).filter(
                KnowledgeBaseDocument.vector_sync_status == "syncing"
            ).count()
            
            completed_count = db.query(KnowledgeBaseDocument).filter(
                KnowledgeBaseDocument.vector_sync_status == "completed"
            ).count()
            
            failed_count = db.query(KnowledgeBaseDocument).filter(
                KnowledgeBaseDocument.vector_sync_status == "failed"
            ).count()
            
            return {
                "pending": pending_count,
                "syncing": syncing_count,
                "completed": completed_count,
                "failed": failed_count,
                "total": pending_count + syncing_count + completed_count + failed_count
            }
        except Exception as e:
            logger.error(f"获取同步状态失败: {str(e)}")
            return {}

# 全局实例
vector_sync_processor = VectorSyncProcessor()