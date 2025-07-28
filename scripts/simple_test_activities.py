#!/usr/bin/env python3
"""
简化的用户活动记录功能测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import uuid
import json
from datetime import datetime
from sqlalchemy import text

# 只导入数据库相关的模块
from app.database import get_db_session, User, UserActivity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_user_activities_table():
    """测试用户活动记录表的基本功能"""
    db = get_db_session()
    
    try:
        # 测试表是否存在
        result = db.execute(text("SELECT COUNT(*) FROM user_activities"))
        count = result.scalar()
        logger.info(f"用户活动记录表存在，当前记录数: {count}")
        
        # 创建测试用户
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
        
        # 创建测试活动记录
        activity_id = str(uuid.uuid4())
        test_metadata = {"test": "data", "number": 123}
        
        activity = UserActivity(
            id=activity_id,
            user_id=test_user_id,
            activity_type="user_login",
            activity_description="测试用户登录",
            resource_type="user",
            resource_id=test_user_id,
            activity_metadata=json.dumps(test_metadata),
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        db.add(activity)
        db.commit()
        logger.info(f"创建测试活动记录: {activity_id}")
        
        # 查询活动记录
        activities = db.query(UserActivity).filter(
            UserActivity.user_id == test_user_id
        ).all()
        
        logger.info(f"查询到 {len(activities)} 条活动记录")
        
        for activity in activities:
            logger.info(f"活动: {activity.activity_type}")
            logger.info(f"  描述: {activity.activity_description}")
            logger.info(f"  资源: {activity.resource_type}:{activity.resource_id}")
            logger.info(f"  时间: {activity.create_time}")
            logger.info(f"  元数据: {activity.activity_metadata}")
            
            # 测试元数据反序列化
            if activity.activity_metadata:
                metadata = json.loads(activity.activity_metadata)
                logger.info(f"  解析后的元数据: {metadata}")
        
        # 测试按时间排序查询
        recent_activities = db.query(UserActivity).filter(
            UserActivity.user_id == test_user_id
        ).order_by(UserActivity.create_time.desc()).limit(5).all()
        
        logger.info(f"最近的活动记录数: {len(recent_activities)}")
        
        # 清理测试数据
        db.query(UserActivity).filter(UserActivity.user_id == test_user_id).delete()
        db.query(User).filter(User.id == test_user_id).delete()
        db.commit()
        logger.info(f"清理测试数据: {test_user_id}")
        
        logger.info("\n✅ 用户活动记录表功能测试通过！")
        
    except Exception as e:
        db.rollback()
        logger.error(f"测试失败: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_user_activities_table()