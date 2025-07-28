#!/usr/bin/env python3
"""
测试空活动记录情况下的接口行为
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import get_db, User, UserActivity
from app.services.activity_service import activity_service

def test_empty_activities():
    """测试空活动记录的情况"""
    print("🧪 测试空活动记录情况...")
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 查找一个测试用户
        test_user = db.query(User).first()
        if not test_user:
            print("❌ 没有找到测试用户")
            return False
        
        print(f"👤 使用测试用户: {test_user.username or test_user.email} (ID: {test_user.id})")
        
        # 检查该用户的活动记录数量
        activity_count = db.query(UserActivity).filter(UserActivity.user_id == test_user.id).count()
        print(f"📊 用户当前活动记录数: {activity_count}")
        
        # 测试 activity_service.get_user_activities 方法
        print("\n🔄 测试 ActivityService.get_user_activities...")
        activities = activity_service.get_user_activities(db, test_user.id, limit=5)
        print(f"📝 服务返回的活动记录数: {len(activities)}")
        
        # 测试不同的参数
        print("\n🔄 测试不同参数...")
        activities_with_type = activity_service.get_user_activities(
            db, test_user.id, limit=10, activity_type="user_login"
        )
        print(f"📝 指定类型的活动记录数: {len(activities_with_type)}")
        
        # 如果没有活动记录，创建一条测试记录
        if activity_count == 0:
            print("\n➕ 创建测试活动记录...")
            from app.schemas import ActivityType, UserActivityCreate
            
            test_activity = UserActivityCreate(
                activity_type=ActivityType.USER_LOGIN,
                activity_description="测试登录活动",
                ip_address="127.0.0.1",
                user_agent="Test Agent"
            )
            
            created_activity = activity_service.create_activity(db, test_user.id, test_activity)
            if created_activity:
                print(f"✅ 创建测试活动记录成功: {created_activity.id}")
                
                # 再次测试获取
                activities_after = activity_service.get_user_activities(db, test_user.id, limit=5)
                print(f"📝 创建后的活动记录数: {len(activities_after)}")
            else:
                print("❌ 创建测试活动记录失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 开始测试空活动记录情况")
    print("=" * 50)
    
    success = test_empty_activities()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试完成！")
    else:
        print("❌ 测试失败！")

if __name__ == "__main__":
    main()