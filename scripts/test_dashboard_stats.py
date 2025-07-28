#!/usr/bin/env python3
"""
测试仪表板统计接口
"""
import sys
import os
import asyncio
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import get_db, User, UserActivity
from app.services.activity_service import activity_service
from app.schemas import ActivityType

def test_dashboard_stats():
    """测试仪表板统计功能"""
    print("🧪 开始测试仪表板统计功能...")
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 查找一个测试用户
        test_user = db.query(User).first()
        if not test_user:
            print("❌ 没有找到测试用户，请先创建用户")
            return False
        
        print(f"📝 使用测试用户: {test_user.username or test_user.email}")
        
        # 测试不同的统计周期
        periods = ["7d", "30d", "90d"]
        
        for period in periods:
            print(f"\n📊 测试统计周期: {period}")
            
            stats = activity_service.get_dashboard_stats(db, test_user.id, period)
            
            print(f"  📄 文档统计:")
            print(f"    - 总数: {stats['document_stats']['total']}")
            print(f"    - 增长率: {stats['document_stats']['growth_rate']:.1%}")
            print(f"    - 增长数量: {stats['document_stats']['growth_count']}")
            
            print(f"  📚 知识库统计:")
            print(f"    - 总数: {stats['knowledge_base_stats']['total']}")
            print(f"    - 增长率: {stats['knowledge_base_stats']['growth_rate']:.1%}")
            print(f"    - 增长数量: {stats['knowledge_base_stats']['growth_count']}")
            
            print(f"  💬 对话统计:")
            print(f"    - 今日: {stats['conversation_stats']['today']}")
            print(f"    - 增长率: {stats['conversation_stats']['growth_rate']:.1%}")
            print(f"    - 昨日: {stats['conversation_stats']['yesterday']}")
            
            print(f"  📈 活动摘要:")
            print(f"    - 总活动数: {stats['activity_summary']['total_activities']}")
            print(f"    - 最活跃类型: {stats['activity_summary']['most_active_type']}")
            print(f"    - 最近活动: {len(stats['activity_summary']['recent_activities'])} 项")
            
            # 显示最近活动详情
            for activity in stats['activity_summary']['recent_activities'][:3]:
                print(f"      - {activity['activity_type']}: {activity['count']} 次 ({activity['percentage']:.1f}%)")
        
        print("\n✅ 仪表板统计功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

def test_json_serialization():
    """测试JSON序列化"""
    print("\n🔄 测试JSON序列化...")
    
    db = next(get_db())
    
    try:
        test_user = db.query(User).first()
        if not test_user:
            print("❌ 没有找到测试用户")
            return False
        
        stats = activity_service.get_dashboard_stats(db, test_user.id, "30d")
        
        # 测试JSON序列化
        json_str = json.dumps(stats, default=str, ensure_ascii=False, indent=2)
        print("✅ JSON序列化成功")
        
        # 测试JSON反序列化
        parsed_stats = json.loads(json_str)
        print("✅ JSON反序列化成功")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON序列化测试失败: {str(e)}")
        return False
    
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 开始测试仪表板统计接口")
    print("=" * 50)
    
    success = True
    
    # 测试基本功能
    if not test_dashboard_stats():
        success = False
    
    # 测试JSON序列化
    if not test_json_serialization():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 所有测试通过！")
        print("\n📝 接口使用说明:")
        print("GET /api/v1/users/dashboard/stats?period=30d")
        print("Authorization: Bearer <token>")
        print("\n支持的period参数: 7d, 30d, 90d")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)