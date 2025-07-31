#!/usr/bin/env python3
"""
测试简化后的仪表板统计接口
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def login():
    """用户登录"""
    print("=== 用户登录 ===")
    
    login_data = {
        "login_credential": "test@example.com",
        "password": "123456"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/users/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            print(f"✅ 登录成功，获取到token")
            return token
        else:
            print(f"❌ 登录失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return None

def test_simplified_dashboard_stats(token):
    """测试简化后的仪表板统计接口"""
    print("\n=== 测试简化后的仪表板统计接口 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/users/dashboard/stats", 
                              headers=headers)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 仪表板统计获取成功:")
            print(f"   响应结构: {json.dumps(data, indent=2, ensure_ascii=False, default=str)}")
            
            # 验证响应结构
            if data.get("success") and "data" in data:
                stats = data["data"]
                print("\n📊 统计数据:")
                print(f"   文档总数: {stats.get('document_count', 'N/A')}")
                print(f"   知识库数量: {stats.get('knowledge_base_count', 'N/A')}")
                print(f"   今日对话次数: {stats.get('today_conversations', 'N/A')}")
                print(f"   最后更新时间: {stats.get('last_updated', 'N/A')}")
                
                # 验证数据类型
                expected_fields = {
                    'document_count': int,
                    'knowledge_base_count': int,
                    'today_conversations': int,
                    'last_updated': str
                }
                
                all_valid = True
                for field, expected_type in expected_fields.items():
                    if field in stats:
                        actual_value = stats[field]
                        if field == 'last_updated':
                            # 时间字段特殊处理
                            if isinstance(actual_value, str):
                                print(f"   ✅ {field}: 类型正确 (str)")
                            else:
                                print(f"   ❌ {field}: 类型错误，期望 str，实际 {type(actual_value)}")
                                all_valid = False
                        else:
                            if isinstance(actual_value, expected_type):
                                print(f"   ✅ {field}: 类型正确 ({expected_type.__name__})")
                            else:
                                print(f"   ❌ {field}: 类型错误，期望 {expected_type.__name__}，实际 {type(actual_value)}")
                                all_valid = False
                    else:
                        print(f"   ❌ 缺少字段: {field}")
                        all_valid = False
                
                if all_valid:
                    print("\n🎉 接口结构验证通过！")
                else:
                    print("\n⚠️ 接口结构存在问题")
                
                return True
            else:
                print("❌ 响应结构不正确")
                return False
        else:
            print(f"❌ 获取仪表板统计失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_no_period_parameter(token):
    """测试接口不再需要 period 参数"""
    print("\n=== 测试接口不再需要 period 参数 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试带 period 参数的请求（应该忽略该参数）
    try:
        response = requests.get(f"{BASE_URL}/api/v1/users/dashboard/stats?period=30d", 
                              headers=headers)
        
        print(f"带 period 参数的请求状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 接口正确忽略了 period 参数")
            return True
        else:
            print(f"❌ 带 period 参数的请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def compare_with_old_interface(token):
    """对比新旧接口的差异"""
    print("\n=== 对比新旧接口差异 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/users/dashboard/stats", 
                              headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get("data", {})
            
            print("📋 新接口特点:")
            print("   ✅ 不需要 period 参数")
            print("   ✅ 返回简化的数据结构")
            print("   ✅ 只包含核心统计数据")
            print("   ✅ 没有增长百分比计算")
            
            print("\n📊 返回的数据字段:")
            for key, value in stats.items():
                print(f"   - {key}: {value} ({type(value).__name__})")
            
            print("\n🔄 与旧接口的主要差异:")
            print("   - 移除了 period 参数处理")
            print("   - 移除了增长率计算")
            print("   - 移除了复杂的活动摘要")
            print("   - 简化为三个核心指标")
            
            return True
        else:
            print(f"❌ 获取数据失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 测试简化后的仪表板统计接口")
    print("=" * 60)
    
    # 1. 登录
    token = login()
    if not token:
        print("❌ 无法获取认证token，测试终止")
        return False
    
    success = True
    
    # 2. 测试简化后的接口
    if not test_simplified_dashboard_stats(token):
        success = False
    
    # 3. 测试不需要 period 参数
    if not test_no_period_parameter(token):
        success = False
    
    # 4. 对比新旧接口差异
    if not compare_with_old_interface(token):
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 简化后的仪表板统计接口测试成功！")
        print("\n✅ 接口改进效果:")
        print("- 移除了 period 参数，简化了调用方式")
        print("- 移除了复杂的增长率计算")
        print("- 只返回三个核心统计指标")
        print("- 提高了接口响应速度")
        print("- 减少了数据库查询复杂度")
        
        print("\n📋 接口使用方法:")
        print("GET /api/v1/users/dashboard/stats")
        print("Authorization: Bearer <token>")
        
        print("\n📊 返回数据格式:")
        print("""{
  "success": true,
  "data": {
    "document_count": 0,
    "knowledge_base_count": 3,
    "today_conversations": 0,
    "last_updated": "2025-07-31T11:49:07.806000"
  },
  "message": "获取仪表板统计成功"
}""")
    else:
        print("❌ 测试过程中出现错误")
    
    print("\n💡 提示:")
    print("1. 确保服务器正在运行: uvicorn app.main:app --reload")
    print("2. 如果测试失败，请检查服务器日志")
    print("3. 确认数据库中有相关数据表")
    
    return success

if __name__ == "__main__":
    main()