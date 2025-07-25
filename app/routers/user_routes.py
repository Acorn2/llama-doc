"""
用户管理相关的API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db, User
from app.schemas import (
    UserCreate, UserUpdate, UserLogin, UserResponse, UserListResponse, 
    TokenResponse
)
from app.services.user_service import user_service
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user, get_current_superuser

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
    db: Session = Depends(get_db)
):
    """用户注册"""
    try:
        user = user_service.create_user(db, user_data)
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

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    try:
        # 重新生成token
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