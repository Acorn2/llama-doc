#!/usr/bin/env python3
"""
测试用户活动记录功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import uuid
from datetime import datetime
from app.database import get_db_session, User, UserActivity
from app.services.activity_service import activity_service
from app.schemas import ActivityType, UserActivityCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_activity_service():
    """测试活动记录服务"""
    db = get_db_session()
    
    try:
        # 创建测试用户（如果不存在）
        test_user_id = "test-user-" + str(uuid.uuid4())[:8]
        test_user = User(
            id=test_user_id,
            username="test_user",
            email="test@example.com",
            password_hash="test_hash",
            is_active=True
        )
        db.add(test_user)
        db.commit()
        logger.info(f"创建测试用户: {test_user_id}")
        
        # 测试记录各种类型的活动
        activities_to_test = [
            {
                "type": ActivityType.USER_LOGIN,
                "description": "用户登录测试",
                "resource_type": None,
                "resource_id": None,
                "metadata": {"login_method": "email"}
            },
            {
                "type": ActivityType.DOCUMENT_UPLOAD,
                "description": "上传文档: test.pdf",
                "resource_type": "document",
                "resource_id": "doc-123",
                "metadata": {"filename": "test.pdf", "file_size": 1024}
            },
            {
                "type": ActivityType.KB_CREATE,
                "description": "创建知识库: 测试知识库",
                "resource_type": "knowledge_base",
                "resource_id": "kb-456",
                "metadata": {"name": "测试知识库", "is_public": False}
            },
            {
                "type": ActivityType.AGENT_CHAT,
                "description": "Agent对话: 你好，请帮我分析这个文档",
                "resource_type": "knowledge_base",
                "resource_id": "kb-456",
                "metadata": {"message_length": 15, "use_agent": True}
            },
            {
                "type": ActivityType.CONVERSATION_CREATE,
                "description": "创建对话",
                "resource_type": "conversation",
                "resource_id": "conv-789",
                "metadata": {"kb_id": "kb-456"}
            }
        ]
        
        # 记录测试活动
        for activity_data in activities_to_test:
            activity_create = UserActivityCreate(
                activity_type=activity_data["type"],
                activity_description=activity_data["description"],
                resource_type=activity_data["resource_type"],
                resource_id=activity_data["resource_id"],
                activity_metadata=activity_data["metadata"],
                ip_address="127.0.0.1",
                user_agent="Test Agent"
            )
            
            activity = activity_service.create_activity(db, test_user_id, activity_create)
            logger.info(f"记录活动: {activity.activity_type} - {activity.activity_description}")
        
        # 测试查询用户活动
        logger.info("\n=== 查询用户活动记录 ===")
        recent_activities = activity_service.get_recent_activities(db, test_user_id, limit=5)
        
        for activity in recent_activities:
            logger.info(f"活动: {activity.activity_type}")
            logger.info(f"  描述: {activity.activity_description}")
            logger.info(f"  资源: {activity.resource_type}:{activity.resource_id}")
            logger.info(f"  时间: {activity.create_time}")
            logger.info(f"  元数据: {activity.activity_metadata}")
            logger.info("---")
        
        # 测试活动统计
        logger.info("\n=== 用户活动统计 ===")
        stats = activity_service.get_activity_stats(db, test_user_id, days=30)
        logger.info(f"总活动数: {stats['total_activities']}")
        logger.info("按类型统计:")
        for activity_type, count in stats['activity_by_type'].items():
            logger.info(f"  {activity_type}: {count}")
        
        # 清理测试数据
        db.query(UserActivity).filter(UserActivity.user_id == test_user_id).delete()
        db.query(User).filter(User.id == test_user_id).delete()
        db.commit()
        logger.info(f"清理测试数据: {test_user_id}")
        
        logger.info("\n✅ 用户活动记录功能测试通过！")
        
    except Exception as e:
        db.rollback()
        logger.error(f"测试失败: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_activity_service()