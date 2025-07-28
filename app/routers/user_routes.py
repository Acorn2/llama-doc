"""
用户管理相关的API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db, User
from app.schemas import (
    UserCreate, UserUpdate, UserLogin, UserResponse, UserListResponse, 
    TokenResponse, UserActivityResponse
)
from app.services.user_service import user_service
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user, get_current_superuser
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """用户注册"""
    try:
        user = user_service.create_user(db, user_data)
        
        # 记录用户注册活动
        from app.utils.activity_logger import log_user_activity
        from app.schemas import ActivityType
        log_user_activity(
            db=db,
            user=user,
            activity_type=ActivityType.USER_REGISTER,
            description=f"用户注册成功: {user.username or user.email or user.phone}",
            request=request,
            metadata={"registration_method": "email" if user.email else "phone"}
        )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            create_time=user.create_time,
            update_time=user.update_time,
            last_login_time=user.last_login_time
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="注册失败")

@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """用户登录"""
    try:
        token_response = auth_service.login(db, login_data)
        if not token_response:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 记录用户登录活动
        from app.utils.activity_logger import log_user_activity
        from app.schemas import ActivityType
        log_user_activity(
            db=db,
            user=token_response.user,
            activity_type=ActivityType.USER_LOGIN,
            description=f"用户登录成功: {login_data.login_credential}",
            request=request,
            metadata={"login_credential": login_data.login_credential}
        )
        
        return token_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="登录失败")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        create_time=current_user.create_time,
        update_time=current_user.update_time,
        last_login_time=current_user.last_login_time
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    try:
        updated_user = user_service.update_user(db, current_user.id, user_data)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            phone=updated_user.phone,
            full_name=updated_user.full_name,
            avatar_url=updated_user.avatar_url,
            is_active=updated_user.is_active,
            is_superuser=updated_user.is_superuser,
            create_time=updated_user.create_time,
            update_time=updated_user.update_time,
            last_login_time=updated_user.last_login_time
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新失败")

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户信息（需要超级用户权限或查看自己的信息）"""
    # 检查权限：超级用户或查看自己的信息
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        create_time=user.create_time,
        update_time=user.update_time,
        last_login_time=user.last_login_time
    )

@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 10,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """获取用户列表（仅超级用户）"""
    try:
        result = user_service.list_users(db, skip=skip, limit=limit, is_active=is_active)
        
        user_responses = [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                phone=user.phone,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                create_time=user.create_time,
                update_time=user.update_time,
                last_login_time=user.last_login_time
            )
            for user in result["items"]
        ]
        
        return UserListResponse(
            success=True,
            message="获取用户列表成功",
            users=user_responses,
            total=result["total"]
        )
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取用户列表失败")

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """更新用户信息（仅超级用户）"""
    try:
        updated_user = user_service.update_user(db, user_id, user_data)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            phone=updated_user.phone,
            full_name=updated_user.full_name,
            avatar_url=updated_user.avatar_url,
            is_active=updated_user.is_active,
            is_superuser=updated_user.is_superuser,
            create_time=updated_user.create_time,
            update_time=updated_user.update_time,
            last_login_time=updated_user.last_login_time
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新失败")

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """删除用户（软删除，仅超级用户）"""
    try:
        success = user_service.delete_user(db, user_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        
        return {"success": True, "message": "用户已被禁用"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除失败")

@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """用户登出"""
    try:
        token = credentials.credentials
        success = auth_service.logout(token)
        
        # 记录用户登出活动
        from app.utils.activity_logger import log_user_activity
        from app.schemas import ActivityType
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.USER_LOGOUT,
            description="用户登出",
            request=request
        )
        
        if success:
            return {"success": True, "message": "登出成功"}
        else:
            return {"success": False, "message": "登出失败"}
    except Exception as e:
        logger.error(f"用户登出失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="登出失败")

@router.post("/logout-all")
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """登出所有设备"""
    try:
        success = auth_service.revoke_user_tokens(current_user.id)
        
        if success:
            return {"success": True, "message": "已登出所有设备"}
        else:
            return {"success": False, "message": "操作失败"}
    except Exception as e:
        logger.error(f"登出所有设备失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="操作失败")

@router.get("/active-sessions")
async def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的活跃会话列表"""
    try:
        active_tokens = auth_service.get_user_active_tokens(current_user.id)
        
        return {
            "success": True,
            "data": {
                "active_sessions": active_tokens,
                "total": len(active_tokens)
            },
            "message": "获取活跃会话成功"
        }
    except Exception as e:
        logger.error(f"获取活跃会话失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取会话信息失败")

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    try:
        # 撤销当前token
        old_token = credentials.credentials
        auth_service.revoke_token(old_token)
        
        # 生成新token
        token_data = auth_service.create_access_token(current_user)
        
        user_response = UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            phone=current_user.phone,
            full_name=current_user.full_name,
            avatar_url=current_user.avatar_url,
            is_active=current_user.is_active,
            is_superuser=current_user.is_superuser,
            create_time=current_user.create_time,
            update_time=current_user.update_time,
            last_login_time=current_user.last_login_time
        )
        
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user=user_response
        )
    except Exception as e:
        logger.error(f"刷新令牌失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="刷新令牌失败")

@router.get("/activities", response_model=List[UserActivityResponse])
async def get_user_activities(
    limit: int = 5,
    activity_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的活动记录"""
    try:
        from app.services.activity_service import activity_service
        
        activities = activity_service.get_user_activities(
            db, current_user.id, limit=limit, activity_type=activity_type
        )
        
        return [
            UserActivityResponse(
                id=activity.id,
                user_id=activity.user_id,
                activity_type=activity.activity_type,
                activity_description=activity.activity_description,
                resource_type=activity.resource_type,
                resource_id=activity.resource_id,
                activity_metadata=activity.activity_metadata,
                ip_address=activity.ip_address,
                user_agent=activity.user_agent,
                create_time=activity.create_time
            )
            for activity in activities
        ]
    except Exception as e:
        logger.error(f"获取用户活动记录失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取活动记录失败")

@router.get("/activities/stats")
async def get_user_activity_stats(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户活动统计"""
    try:
        from app.services.activity_service import activity_service
        
        stats = activity_service.get_activity_stats(db, current_user.id, days=days)
        
        return {
            "success": True,
            "data": stats,
            "message": "获取活动统计成功"
        }
    except Exception as e:
        logger.error(f"获取用户活动统计失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取活动统计失败") 