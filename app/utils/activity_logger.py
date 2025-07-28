"""
用户活动记录工具
"""
import logging
from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy.orm import Session

from app.services.activity_service import activity_service
from app.schemas import ActivityType
from app.database import User

logger = logging.getLogger(__name__)

def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """从请求中获取客户端信息"""
    try:
        # 获取真实IP地址（考虑代理）
        ip_address = None
        if "x-forwarded-for" in request.headers:
            ip_address = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            ip_address = request.headers["x-real-ip"]
        else:
            ip_address = request.client.host if request.client else None
        
        # 获取用户代理
        user_agent = request.headers.get("user-agent")
        
        return ip_address, user_agent
    except Exception as e:
        logger.warning(f"获取客户端信息失败: {str(e)}")
        return None, None

def log_user_activity(
    db: Session,
    user: User,
    activity_type: ActivityType,
    description: str,
    request: Optional[Request] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """记录用户活动的便捷函数"""
    try:
        ip_address, user_agent = None, None
        if request:
            ip_address, user_agent = get_client_info(request)
        
        activity_service.log_activity(
            db=db,
            user_id=user.id,
            activity_type=activity_type,
            description=description,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return True
    except Exception as e:
        logger.error(f"记录用户活动失败: {str(e)}")
        return False

# 装饰器函数，用于自动记录活动
def activity_logger(
    activity_type: ActivityType,
    description: str,
    resource_type: Optional[str] = None,
    get_resource_id: Optional[callable] = None,
    get_metadata: Optional[callable] = None
):
    """
    活动记录装饰器
    
    Args:
        activity_type: 活动类型
        description: 活动描述
        resource_type: 资源类型
        get_resource_id: 从函数参数中获取资源ID的函数
        get_metadata: 从函数参数中获取元数据的函数
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 执行原函数
            result = await func(*args, **kwargs)
            
            try:
                # 从参数中提取必要信息
                db = None
                user = None
                request = None
                
                # 查找db, user, request参数
                for arg in args:
                    if hasattr(arg, 'query'):  # Session对象
                        db = arg
                    elif hasattr(arg, 'id') and hasattr(arg, 'username'):  # User对象
                        user = arg
                    elif hasattr(arg, 'client'):  # Request对象
                        request = arg
                
                # 从kwargs中查找
                if not db:
                    db = kwargs.get('db')
                if not user:
                    user = kwargs.get('current_user')
                if not request:
                    request = kwargs.get('request')
                
                if db and user:
                    resource_id = None
                    if get_resource_id:
                        resource_id = get_resource_id(*args, **kwargs)
                    
                    metadata = None
                    if get_metadata:
                        metadata = get_metadata(*args, **kwargs)
                    
                    log_user_activity(
                        db=db,
                        user=user,
                        activity_type=activity_type,
                        description=description,
                        request=request,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        metadata=metadata
                    )
            except Exception as e:
                logger.error(f"活动记录装饰器执行失败: {str(e)}")
            
            return result
        return wrapper
    return decorator