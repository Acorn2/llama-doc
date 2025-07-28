"""
用户活动记录服务
"""
import logging
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import UserActivity, User
from app.schemas import UserActivityCreate, ActivityType

logger = logging.getLogger(__name__)

class ActivityService:
    """用户活动记录服务类"""
    
    def create_activity(
        self, 
        db: Session, 
        user_id: str, 
        activity_data: UserActivityCreate
    ) -> UserActivity:
        """创建用户活动记录"""
        try:
            activity_id = str(uuid.uuid4())
            
            # 序列化元数据
            metadata_json = None
            if activity_data.activity_metadata:
                metadata_json = json.dumps(activity_data.activity_metadata, ensure_ascii=False)
            
            activity = UserActivity(
                id=activity_id,
                user_id=user_id,
                activity_type=activity_data.activity_type.value,
                activity_description=activity_data.activity_description,
                resource_type=activity_data.resource_type,
                resource_id=activity_data.resource_id,
                activity_metadata=metadata_json,
                ip_address=activity_data.ip_address,
                user_agent=activity_data.user_agent
            )
            
            db.add(activity)
            db.commit()
            db.refresh(activity)
            
            logger.info(f"用户活动记录创建成功: {user_id} - {activity_data.activity_type.value}")
            return activity
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建用户活动记录失败: {str(e)}")
            raise
    
    def log_activity(
        self,
        db: Session,
        user_id: str,
        activity_type: ActivityType,
        description: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[UserActivity]:
        """便捷方法：记录用户活动"""
        try:
            activity_data = UserActivityCreate(
                activity_type=activity_type,
                activity_description=description,
                resource_type=resource_type,
                resource_id=resource_id,
                activity_metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return self.create_activity(db, user_id, activity_data)
            
        except Exception as e:
            logger.error(f"记录用户活动失败: {str(e)}")
            # 活动记录失败不应该影响主要业务流程
            return None
    
    def get_user_activities(
        self, 
        db: Session, 
        user_id: str, 
        limit: int = 5,
        activity_type: Optional[str] = None
    ) -> List[UserActivity]:
        """获取用户活动记录"""
        try:
            query = db.query(UserActivity).filter(UserActivity.user_id == user_id)
            
            if activity_type:
                query = query.filter(UserActivity.activity_type == activity_type)
            
            activities = query.order_by(desc(UserActivity.create_time)).limit(limit).all()
            
            # 反序列化元数据
            for activity in activities:
                if activity.activity_metadata:
                    try:
                        activity.activity_metadata = json.loads(activity.activity_metadata)
                    except json.JSONDecodeError:
                        activity.activity_metadata = None
            
            return activities
            
        except Exception as e:
            logger.error(f"获取用户活动记录失败: {str(e)}")
            return []
    
    def get_recent_activities(
        self, 
        db: Session, 
        user_id: str, 
        limit: int = 5
    ) -> List[UserActivity]:
        """获取用户最近的活动记录"""
        return self.get_user_activities(db, user_id, limit)
    
    def delete_old_activities(
        self, 
        db: Session, 
        days: int = 90
    ) -> int:
        """删除指定天数之前的活动记录"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = db.query(UserActivity).filter(
                UserActivity.create_time < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"删除了 {deleted_count} 条过期活动记录")
            return deleted_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"删除过期活动记录失败: {str(e)}")
            return 0
    
    def get_activity_stats(
        self, 
        db: Session, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户活动统计"""
        try:
            from datetime import timedelta
            from sqlalchemy import func
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 按活动类型统计
            type_stats = db.query(
                UserActivity.activity_type,
                func.count(UserActivity.id).label('count')
            ).filter(
                UserActivity.user_id == user_id,
                UserActivity.create_time >= start_date
            ).group_by(UserActivity.activity_type).all()
            
            # 总活动数
            total_activities = db.query(UserActivity).filter(
                UserActivity.user_id == user_id,
                UserActivity.create_time >= start_date
            ).count()
            
            return {
                "total_activities": total_activities,
                "activity_by_type": {stat.activity_type: stat.count for stat in type_stats},
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"获取活动统计失败: {str(e)}")
            return {"total_activities": 0, "activity_by_type": {}, "period_days": days}

# 创建全局实例
activity_service = ActivityService()