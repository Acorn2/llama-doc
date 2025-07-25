"""
JWT认证服务 - 集成Redis
"""
import jwt
import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.database import User
from app.services.user_service import user_service
from app.schemas import UserLogin, TokenResponse, UserResponse
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

class AuthService:
    """JWT认证服务 - 集成Redis"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7天 = 7 * 24 * 60 = 10080分钟
        self.cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
    
    def _get_token_cache_key(self, jti: str) -> str:
        """获取token缓存键"""
        return f"token:{jti}"
    
    def _get_user_tokens_key(self, user_id: str) -> str:
        """获取用户token列表键"""
        return f"user_tokens:{user_id}"
    
    def _get_user_cache_key(self, user_id: str) -> str:
        """获取用户缓存键"""
        return f"user:{user_id}"
    
    def create_access_token(self, user: User) -> Dict[str, Any]:
        """
        创建访问令牌并存储到Redis（优化版）
        
        Args:
            user: 用户对象
            
        Returns:
            Dict[str, Any]: 包含token和过期时间的字典
        """
        # 生成唯一的token ID
        jti = str(uuid.uuid4())
        
        # 设置过期时间
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        # 创建payload
        payload = {
            "user_id": user.id,
            "email": user.email,
            "phone": user.phone,
            "is_superuser": user.is_superuser,
            "jti": jti,  # JWT ID，用于token管理
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        # 生成token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # 存储token到Redis（简化版）
        if redis_client.is_available():
            try:
                # 精简的token信息 - 只存储必要数据
                token_info = {
                    "user_id": user.id,
                    "created_at": datetime.utcnow().isoformat(),
                    "expires_at": expire.isoformat(),
                    "revoked": False,
                    # 可选：根据需要添加设备信息
                    # "user_agent": request.headers.get("User-Agent"),
                    # "ip_address": request.client.host
                }
                
                # 设置token缓存，过期时间比JWT稍长一点
                redis_client.set(
                    self._get_token_cache_key(jti),
                    token_info,
                    expire=self.access_token_expire_minutes * 60 + 3600  # 多1小时缓冲，适应7天有效期
                )
                
                # 将token ID添加到用户的token列表中
                user_tokens_key = self._get_user_tokens_key(user.id)
                current_tokens = redis_client.get(user_tokens_key) or []
                current_tokens.append(jti)
                
                # 只保留最近的token（可配置最大数量）
                max_tokens = int(os.getenv("MAX_USER_TOKENS", "5"))
                if len(current_tokens) > max_tokens:
                    # 删除最老的token
                    old_tokens = current_tokens[:-max_tokens]
                    for old_jti in old_tokens:
                        redis_client.delete(self._get_token_cache_key(old_jti))
                    current_tokens = current_tokens[-max_tokens:]
                
                redis_client.set(user_tokens_key, current_tokens, expire=max(self.cache_ttl, self.access_token_expire_minutes * 60))
                
                # 轻量级用户信息缓存 - 只缓存经常访问的字段
                user_cache_key = self._get_user_cache_key(user.id)
                if not redis_client.exists(user_cache_key):  # 只在不存在时创建
                    user_info = {
                        "id": user.id,
                        "is_active": user.is_active,
                        "is_superuser": user.is_superuser,
                        "last_cached": datetime.utcnow().isoformat()
                    }
                    redis_client.set(user_cache_key, user_info, expire=self.cache_ttl)
                
                logger.info(f"Token已缓存到Redis: user_id={user.id}, jti={jti}")
                
            except Exception as e:
                logger.error(f"存储token到Redis失败: {e}")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "expires_at": expire,
            "jti": jti
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证访问令牌，优先从Redis检查
        
        Args:
            token: JWT令牌
            
        Returns:
            Dict[str, Any]: 解码后的payload，验证失败时返回None
        """
        try:
            # 解码token（不验证过期时间，先获取jti）
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            
            # 检查token类型
            if payload.get("type") != "access":
                logger.warning("无效的token类型")
                return None
            
            jti = payload.get("jti")
            if not jti:
                logger.warning("Token缺少JTI")
                return None
            
            # 先检查Redis中的token状态
            if redis_client.is_available():
                token_info = redis_client.get(self._get_token_cache_key(jti))
                if not token_info:
                    logger.warning(f"Token在Redis中不存在或已过期: {jti}")
                    return None
                
                # 检查token是否在黑名单中
                if token_info.get("revoked"):
                    logger.warning(f"Token已被撤销: {jti}")
                    return None
            
            # 验证JWT的完整性和过期时间
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的Token: {e}")
            return None
    
    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """
        从token获取当前用户（优化版）
        
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
        
        # 优先从Redis缓存检查用户状态（只检查关键字段）
        user_cache_key = self._get_user_cache_key(user_id)
        cached_user_status = None
        
        if redis_client.is_available():
            cached_user_status = redis_client.get(user_cache_key)
            if cached_user_status:
                # 如果缓存显示用户已被禁用，直接返回None
                if not cached_user_status.get("is_active", True):
                    logger.warning(f"缓存显示用户已被禁用: {user_id}")
                    return None
        
        # 从数据库获取完整用户信息
        user = user_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            logger.warning(f"用户不存在或已被禁用: {user_id}")
            
            # 更新缓存状态
            if redis_client.is_available() and user:
                user_info = {
                    "id": user.id,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "last_cached": datetime.utcnow().isoformat()
                }
                redis_client.set(user_cache_key, user_info, expire=self.cache_ttl)
            
            return None
        
        # 更新Redis缓存（仅在状态变化时）
        if redis_client.is_available():
            should_update_cache = False
            
            if not cached_user_status:
                should_update_cache = True
            else:
                # 检查关键字段是否有变化
                if (cached_user_status.get("is_active") != user.is_active or 
                    cached_user_status.get("is_superuser") != user.is_superuser):
                    should_update_cache = True
            
            if should_update_cache:
                try:
                    user_info = {
                        "id": user.id,
                        "is_active": user.is_active,
                        "is_superuser": user.is_superuser,
                        "last_cached": datetime.utcnow().isoformat()
                    }
                    redis_client.set(user_cache_key, user_info, expire=self.cache_ttl)
                    logger.debug(f"用户状态缓存已更新: {user_id}")
                except Exception as e:
                    logger.error(f"更新用户缓存失败: {e}")
        
        return user
    
    def revoke_token(self, token: str) -> bool:
        """
        撤销token（加入黑名单）
        
        Args:
            token: JWT令牌
            
        Returns:
            bool: 是否成功撤销
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            jti = payload.get("jti")
            
            if not jti:
                return False
            
            if redis_client.is_available():
                # 获取现有token信息
                token_info = redis_client.get(self._get_token_cache_key(jti))
                if token_info:
                    # 标记为已撤销
                    token_info["revoked"] = True
                    token_info["revoked_at"] = datetime.utcnow().isoformat()
                    
                    # 保持到原过期时间
                    ttl = redis_client.ttl(self._get_token_cache_key(jti))
                    if ttl > 0:
                        redis_client.set(self._get_token_cache_key(jti), token_info, expire=ttl)
                        logger.info(f"Token已撤销: {jti}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"撤销token失败: {e}")
            return False
    
    def revoke_user_tokens(self, user_id: str) -> bool:
        """
        撤销用户的所有token
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        if not redis_client.is_available():
            return False
        
        try:
            # 获取用户所有token
            user_tokens = redis_client.get(self._get_user_tokens_key(user_id)) or []
            
            revoked_count = 0
            for jti in user_tokens:
                token_info = redis_client.get(self._get_token_cache_key(jti))
                if token_info and not token_info.get("revoked"):
                    token_info["revoked"] = True
                    token_info["revoked_at"] = datetime.utcnow().isoformat()
                    
                    ttl = redis_client.ttl(self._get_token_cache_key(jti))
                    if ttl > 0:
                        redis_client.set(self._get_token_cache_key(jti), token_info, expire=ttl)
                        revoked_count += 1
            
            # 清空用户token列表
            redis_client.delete(self._get_user_tokens_key(user_id))
            
            # 清空用户缓存
            redis_client.delete(self._get_user_cache_key(user_id))
            
            logger.info(f"已撤销用户 {user_id} 的 {revoked_count} 个token")
            return True
            
        except Exception as e:
            logger.error(f"撤销用户token失败: {e}")
            return False
    
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
    
    def logout(self, token: str) -> bool:
        """
        用户登出（撤销当前token）
        
        Args:
            token: 当前token
            
        Returns:
            bool: 是否成功登出
        """
        return self.revoke_token(token)
    
    def get_user_active_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的活跃token列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 活跃token信息列表
        """
        if not redis_client.is_available():
            return []
        
        try:
            user_tokens = redis_client.get(self._get_user_tokens_key(user_id)) or []
            active_tokens = []
            
            for jti in user_tokens:
                token_info = redis_client.get(self._get_token_cache_key(jti))
                if token_info and not token_info.get("revoked"):
                    active_tokens.append({
                        "jti": jti,
                        "created_at": token_info.get("created_at"),
                        "expires_at": token_info.get("expires_at"),
                        "user_agent": token_info.get("user_agent"),
                        "ip_address": token_info.get("ip_address")
                    })
            
            return active_tokens
            
        except Exception as e:
            logger.error(f"获取用户活跃token失败: {e}")
            return []

# 创建服务实例
auth_service = AuthService() 