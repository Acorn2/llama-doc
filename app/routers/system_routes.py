"""
系统信息相关的API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from datetime import datetime

from app.database import get_db, Document, get_db_info
from app.schemas import HealthCheck
from app.services.document_service import document_task_processor
from app.core.model_factory import ModelFactory

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/system",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """健康检查接口"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        services={
            "database": "connected",
            "vector_store": "ready",
            "llm": "ready"
        }
    )

@router.get("/models/info")
async def get_model_info():
    """获取模型信息"""
    model_factory = ModelFactory()
    
    return {
        "llm_models": model_factory.get_available_llm_models(),
        "embedding_models": model_factory.get_available_embedding_models(),
        "default_llm": model_factory.get_default_llm_model(),
        "default_embedding": model_factory.get_default_embedding_model()
    }

@router.get("/processing/status")
async def get_processing_status():
    """获取文档处理状态"""
    return document_task_processor.get_processing_status()

@router.get("/processing/retry-stats")
async def get_retry_stats(db: Session = Depends(get_db)):
    """获取重试统计信息"""
    try:
        # 获取各状态的文档数量
        status_counts = db.query(
            Document.status, 
            func.count(Document.id).label('count')
        ).group_by(Document.status).all()
        
        # 获取重试次数统计
        retry_counts = db.query(
            Document.retry_count,
            func.count(Document.id).label('count')
        ).filter(Document.retry_count > 0).group_by(Document.retry_count).all()
        
        # 获取失败文档的错误类型统计
        error_types = db.query(
            Document.error_message,
            func.count(Document.id).label('count')
        ).filter(Document.status.in_(["failed", "failed_permanently"])).group_by(Document.error_message).all()
        
        # 计算平均重试次数
        avg_retry = db.query(func.avg(Document.retry_count)).filter(Document.retry_count > 0).scalar() or 0
        
        # 获取重试成功率
        retried_docs = db.query(func.count(Document.id)).filter(Document.retry_count > 0).scalar() or 0
        success_after_retry = db.query(func.count(Document.id)).filter(
            Document.retry_count > 0,
            Document.status == "completed"
        ).scalar() or 0
        
        retry_success_rate = (success_after_retry / retried_docs) if retried_docs > 0 else 0
        
        return {
            "status_counts": {status: count for status, count in status_counts},
            "retry_counts": {retry: count for retry, count in retry_counts},
            "error_types": {error or "未知错误": count for error, count in error_types},
            "avg_retry_count": float(avg_retry),
            "retry_success_rate": retry_success_rate,
            "total_retried_docs": retried_docs,
            "success_after_retry": success_after_retry
        }
    except Exception as e:
        logger.error(f"获取重试统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取重试统计信息失败: {str(e)}")

@router.get("/database/info")
async def get_database_info():
    """获取数据库信息"""
    return get_db_info() 