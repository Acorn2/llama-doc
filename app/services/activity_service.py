"""
用户活动记录服务
"""
import logging
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
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
        logger.info(f"🔍 ActivityService.get_user_activities 开始 - user_id: {user_id}, limit: {limit}, activity_type: {activity_type}")
        
        try:
            # 构建基础查询
            logger.info("🔄 构建数据库查询...")
            query = db.query(UserActivity).filter(UserActivity.user_id == user_id)
            logger.info(f"✅ 基础查询构建完成，过滤用户ID: {user_id}")
            
            # 添加活动类型过滤
            if activity_type:
                logger.info(f"🔄 添加活动类型过滤: {activity_type}")
                query = query.filter(UserActivity.activity_type == activity_type)
            
            # 添加排序和限制
            logger.info(f"🔄 添加排序和限制，limit: {limit}")
            query = query.order_by(desc(UserActivity.create_time)).limit(limit)
            
            # 执行查询
            logger.info("🔄 执行数据库查询...")
            activities = query.all()
            logger.info(f"📊 查询完成，获取到 {len(activities)} 条记录")
            
            # 检查每条记录
            for i, activity in enumerate(activities):
                logger.info(f"📝 记录 {i+1}: ID={activity.id}, 类型={activity.activity_type}, 描述={activity.activity_description[:50]}...")
            
            # 反序列化元数据
            logger.info("🔄 开始处理元数据...")
            for i, activity in enumerate(activities):
                if activity.activity_metadata:
                    try:
                        logger.info(f"🔄 处理第 {i+1} 条记录的元数据...")
                        activity.activity_metadata = json.loads(activity.activity_metadata)
                        logger.info(f"✅ 第 {i+1} 条记录元数据处理成功")
                    except json.JSONDecodeError as json_error:
                        logger.warning(f"⚠️ 第 {i+1} 条记录元数据JSON解析失败: {str(json_error)}")
                        activity.activity_metadata = None
                else:
                    logger.info(f"ℹ️ 第 {i+1} 条记录无元数据")
            
            logger.info(f"🎉 ActivityService.get_user_activities 完成，返回 {len(activities)} 条记录")
            return activities
            
        except Exception as e:
            logger.error(f"❌ ActivityService.get_user_activities 失败: {str(e)}")
            logger.error(f"❌ 错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
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
    
    def get_dashboard_stats(self, db: Session, user_id: str) -> Dict[str, Any]:
        """获取用户仪表板统计数据"""
        try:
            from datetime import timedelta
            
            current_date = datetime.utcnow()
            
            # 获取文档总数
            try:
                from app.database import Document
                total_doc_count = db.query(Document).filter(
                    Document.user_id == user_id
                ).count()
            except Exception:
                # 如果Document表不存在或查询失败，使用默认值
                total_doc_count = 0
            
            # 获取知识库总数
            try:
                from app.database import KnowledgeBase
                total_kb_count = db.query(KnowledgeBase).filter(
                    KnowledgeBase.user_id == user_id
                ).count()
            except Exception:
                # 如果KnowledgeBase表不存在或查询失败，使用默认值
                total_kb_count = 0
            
            # 获取今日对话统计（指今日新建的对话 thread）
            # 使用带时区的时间对象，避免与数据库中带时区的字段比较时报错
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            try:
                from app.database import Conversation
                today_conversations = db.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    Conversation.create_time >= today_start,
                    Conversation.status != "deleted"  # 排除已删除的对话
                ).count()
            except Exception as e:
                logger.error(f"查询今日对话统计失败: {str(e)}")
                today_conversations = 0
            
            return {
                "document_count": total_doc_count,
                "knowledge_base_count": total_kb_count,
                "today_conversations": today_conversations,
                "last_updated": current_date
            }
            
        except Exception as e:
            logger.error(f"获取仪表板统计失败: {str(e)}")
            # 返回默认值
            return {
                "document_count": 0,
                "knowledge_base_count": 0,
                "today_conversations": 0,
                "last_updated": datetime.utcnow()
            }

# 创建全局实例
activity_service = ActivityService()