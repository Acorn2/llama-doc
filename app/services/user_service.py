"""
用户管理服务
"""
import uuid
import hashlib
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta

from app.database import User
from app.schemas import UserCreate, UserUpdate, UserLogin, UserResponse

logger = logging.getLogger(__name__)

class UserService:
    """用户管理服务"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """验证密码"""
        return hashlib.sha256(password.encode()).hexdigest() == hashed_password
    
    def create_user(self, db: Session, user_data: UserCreate) -> User:
        """
        创建用户
        
        Args:
            db: 数据库会话
            user_data: 用户创建数据
            
        Returns:
            User: 创建的用户对象
            
        Raises:
            ValueError: 当邮箱或手机号已存在时
        """
        # 检查邮箱是否已存在
        if user_data.email:
            existing_user = db.query(User).filter(User.email == user_data.email).first()
            if existing_user:
                raise ValueError("邮箱已被注册")
        
        # 检查手机号是否已存在
        if user_data.phone:
            existing_user = db.query(User).filter(User.phone == user_data.phone).first()
            if existing_user:
                raise ValueError("手机号已被注册")
        
        # 生成用户ID
        user_id = str(uuid.uuid4())
        
        # 创建用户
        user = User(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            password_hash=self.hash_password(user_data.password),
            full_name=user_data.full_name,
            avatar_url=user_data.avatar_url,
            is_active=True,
            is_superuser=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"成功创建用户: {user_id}, 邮箱: {user_data.email}, 手机: {user_data.phone}")
        return user
    
    def authenticate_user(self, db: Session, login_data: UserLogin) -> Optional[User]:
        """
        用户认证
        
        Args:
            db: 数据库会话
            login_data: 登录数据
            
        Returns:
            User: 认证成功的用户对象，失败时返回None
        """
        # 查找用户（邮箱或手机号）
        user = db.query(User).filter(
            or_(
                User.email == login_data.login_credential,
                User.phone == login_data.login_credential
            )
        ).first()
        
        if not user:
            logger.warning(f"用户不存在: {login_data.login_credential}")
            return None
        
        if not user.is_active:
            logger.warning(f"用户已被禁用: {login_data.login_credential}")
            return None
        
        if not self.verify_password(login_data.password, user.password_hash):
            logger.warning(f"密码错误: {login_data.login_credential}")
            return None
        
        # 更新最后登录时间
        user.last_login_time = datetime.utcnow()
        db.commit()
        
        logger.info(f"用户认证成功: {user.id}")
        return user
    
    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """
        根据ID获取用户
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            User: 用户对象，不存在时返回None
        """
        return db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        根据邮箱获取用户
        
        Args:
            db: 数据库会话
            email: 邮箱地址
            
        Returns:
            User: 用户对象，不存在时返回None
        """
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_phone(self, db: Session, phone: str) -> Optional[User]:
        """
        根据手机号获取用户
        
        Args:
            db: 数据库会话
            phone: 手机号
            
        Returns:
            User: 用户对象，不存在时返回None
        """
        return db.query(User).filter(User.phone == phone).first()
    
    def update_user(self, db: Session, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        更新用户信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            user_data: 更新数据
            
        Returns:
            User: 更新后的用户对象，不存在时返回None
        """
        user = self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # 更新字段
        if user_data.username is not None:
            user.username = user_data.username
        if user_data.email is not None:
            # 检查邮箱是否已被其他用户使用
            existing_user = db.query(User).filter(
                User.email == user_data.email,
                User.id != user_id
            ).first()
            if existing_user:
                raise ValueError("邮箱已被其他用户注册")
            user.email = user_data.email
        if user_data.phone is not None:
            # 检查手机号是否已被其他用户使用
            existing_user = db.query(User).filter(
                User.phone == user_data.phone,
                User.id != user_id
            ).first()
            if existing_user:
                raise ValueError("手机号已被其他用户注册")
            user.phone = user_data.phone
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url
        if user_data.password is not None:
            user.password_hash = self.hash_password(user_data.password)
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"用户信息已更新: {user_id}")
        return user
    
    def list_users(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 10, 
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        获取用户列表
        
        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 返回记录数
            is_active: 是否活跃用户过滤
            
        Returns:
            Dict[str, Any]: 包含用户列表和总数的字典
        """
        query = db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        total = query.count()
        users = query.order_by(User.create_time.desc()).offset(skip).limit(limit).all()
        
        return {
            "items": users,
            "total": total
        }
    
    def delete_user(self, db: Session, user_id: str) -> bool:
        """
        删除用户（软删除，设置为非活跃）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        user = self.get_user_by_id(db, user_id)
        if not user:
            return False
        
        user.is_active = False
        db.commit()
        
        logger.info(f"用户已被禁用: {user_id}")
        return True

# 创建服务实例
user_service = UserService() 