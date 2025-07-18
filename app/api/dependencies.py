"""
FastAPI依赖注入
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status

from app.core.container import get_agent_service, get_knowledge_base_manager
from app.services.agent_service import AgentService
from app.services.knowledge_base_service import KnowledgeBaseManager
from app.utils.exceptions import BaseAppException

logger = logging.getLogger(__name__)

# 重新导出容器中的依赖，保持API兼容性
def get_agent_service_dep() -> AgentService:
    """获取Agent服务实例"""
    return get_agent_service()


def get_knowledge_base_manager_dep() -> KnowledgeBaseManager:
    """获取知识库管理器实例"""
    return get_knowledge_base_manager()


async def validate_knowledge_base(
    kb_id: str,
    kb_manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager)
) -> str:
    """
    验证知识库是否存在的依赖
    
    Args:
        kb_id: 知识库ID
        kb_manager: 知识库管理器
        
    Returns:
        str: 验证通过的知识库ID
        
    Raises:
        HTTPException: 知识库不存在时抛出404异常
    """
    try:
        kb_info = await kb_manager.get_knowledge_base(kb_id)
        if not kb_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {kb_id}"
            )
        return kb_id
    except BaseAppException as e:
        logger.error(f"知识库验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"知识库验证异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="知识库验证失败"
        )


def handle_service_exceptions(func):
    """
    服务异常处理装饰器
    将服务层异常转换为HTTP异常
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BaseAppException as e:
            logger.error(f"服务异常: {e}")
            if e.error_code == "KB_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=e.message
                )
            elif e.error_code in ["AGENT_ERROR", "DOC_PROCESSING_ERROR", "LLM_ERROR"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=e.message
                )
            elif e.error_code == "VALIDATION_ERROR":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=e.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=e.message
                )
        except Exception as e:
            logger.error(f"未处理的异常: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="服务内部错误"
            )
    
    return wrapper