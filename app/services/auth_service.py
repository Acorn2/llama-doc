"""
JWT认证服务
"""
import jwt
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database import User
from app.services.user_service import user_service
from app.schemas import UserLogin, TokenResponse, UserResponse

logger = logging.getLogger(__name__)

class AuthService:
    """JWT认证服务"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    def create_access_token(self, user: User) -> Dict[str, Any]:
        """
        创建访问令牌
        
        Args:
            user: 用户对象
            
        Returns:
            Dict[str, Any]: 包含token和过期时间的字典
        """
        # 设置过期时间
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        # 创建payload
        payload = {
            "user_id": user.id,
            "email": user.email,
            "phone": user.phone,
            "is_superuser": user.is_superuser,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        # 生成token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "expires_at": expire
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证访问令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            Dict[str, Any]: 解码后的payload，验证失败时返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查token类型
            if payload.get("type") != "access":
                logger.warning("无效的token类型")
                return None
            
            # 检查过期时间
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                logger.warning("Token已过期")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的Token: {e}")
            return None
    
    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """
        从token获取当前用户
        
        Args:
            db: 数据库会话
            token: JWT令牌
            
        Returns:
            User: 用户对象，验证失败时返回None
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Token中缺少用户ID")
            return None
        
        user = user_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            logger.warning(f"用户不存在或已被禁用: {user_id}")
            return None
        
        return user
    
    def login(self, db: Session, login_data: UserLogin) -> Optional[TokenResponse]:
        """
        用户登录
        
        Args:
            db: 数据库会话
            login_data: 登录数据
            
        Returns:
            TokenResponse: 登录成功返回token响应，失败时返回None
        """
        # 认证用户
        user = user_service.authenticate_user(db, login_data)
        if not user:
            return None
        
        # 创建访问令牌
        token_data = self.create_access_token(user)
        
        # 构建用户响应
        user_response = UserResponse(
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
        
        # 构建token响应
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user=user_response
        )
    
    def refresh_token(self, db: Session, token: str) -> Optional[TokenResponse]:
        """
        刷新访问令牌
        
        Args:
            db: 数据库会话
            token: 当前token
            
        Returns:
            TokenResponse: 新的token响应，失败时返回None
        """
        user = self.get_current_user(db, token)
        if not user:
            return None
        
        return self.login(db, UserLogin(
            login_credential=user.email or user.phone,
            password=""  # 这里不需要密码，因为token已经验证过了
        ))

# 创建服务实例
auth_service = AuthService() 