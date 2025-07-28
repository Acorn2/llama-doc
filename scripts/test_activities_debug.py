#!/usr/bin/env python3
"""
调试用户活动记录接口的测试脚本
"""
import sys
import os
import requests
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_activities_endpoint():
    """测试活动记录接口"""
    print("🧪 开始测试用户活动记录接口...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试根路径
    print("\n1️⃣ 测试根路径...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ 根路径响应: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 响应内容: {response.json()}")
    except Exception as e:
        print(f"❌ 根路径测试失败: {str(e)}")
        return False
    
    # 2. 测试用户注册（如果需要）
    print("\n2️⃣ 测试用户注册...")
    register_data = {
        "username": "test_user_debug",
        "email": "test_debug@example.com",
        "password": "password123",
        "full_name": "测试用户"
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/users/register", json=register_data)
        if response.status_code == 201:
            print("✅ 用户注册成功")
            user_data = response.json()
            print(f"👤 用户信息: {user_data}")
        elif response.status_code == 400:
            print("ℹ️ 用户可能已存在，继续测试...")
        else:
            print(f"⚠️ 注册响应: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"❌ 用户注册失败: {str(e)}")
    
    # 3. 测试用户登录
    print("\n3️⃣ 测试用户登录...")
    login_data = {
        "login_credential": "test_debug@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/users/login", json=login_data)
        if response.status_code == 200:
            print("✅ 用户登录成功")
            token_data = response.json()
            access_token = token_data["access_token"]
            print(f"🔑 获取到访问令牌: {access_token[:50]}...")
        else:
            print(f"❌ 登录失败: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"❌ 用户登录失败: {str(e)}")
        return False
    
    # 4. 测试活动记录接口
    print("\n4️⃣ 测试活动记录接口...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        print("🔄 发送 GET /api/v1/users/activities 请求...")
        response = requests.get(f"{base_url}/api/v1/users/activities", headers=headers)
        
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📋 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ 活动记录接口调用成功")
            activities = response.json()
            print(f"📝 获取到 {len(activities)} 条活动记录")
            
            for i, activity in enumerate(activities):
                print(f"  📄 记录 {i+1}: {activity.get('activity_type')} - {activity.get('activity_description')}")
                
        elif response.status_code == 403:
            print("❌ 403 权限错误")
            print(f"📄 错误响应: {response.text}")
            
            # 尝试获取更多信息
            print("\n🔍 尝试获取用户信息...")
            me_response = requests.get(f"{base_url}/api/v1/users/me", headers=headers)
            print(f"👤 用户信息响应: {me_response.status_code}")
            if me_response.status_code == 200:
                print(f"👤 用户信息: {me_response.json()}")
            else:
                print(f"❌ 获取用户信息失败: {me_response.text}")
                
        else:
            print(f"❌ 接口调用失败: {response.status_code}")
            print(f"📄 错误响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 活动记录接口测试失败: {str(e)}")
        return False
    
    # 5. 测试仪表板统计接口（对比）
    print("\n5️⃣ 测试仪表板统计接口（对比）...")
    try:
        response = requests.get(f"{base_url}/api/v1/users/dashboard/stats", headers=headers)
        print(f"📊 仪表板统计响应: {response.status_code}")
        if response.status_code == 200:
            print("✅ 仪表板统计接口正常")
            stats = response.json()
            print(f"📈 统计数据: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 仪表板统计失败: {response.text}")
    except Exception as e:
        print(f"❌ 仪表板统计测试失败: {str(e)}")
    
    return True

def main():
    """主函数"""
    print("🚀 开始调试用户活动记录接口")
    print("=" * 60)
    
    success = test_activities_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试完成！请查看服务器日志获取详细信息。")
    else:
        print("❌ 测试过程中出现错误。")
    
    print("\n💡 提示:")
    print("1. 确保服务器正在运行: uvicorn app.main:app --reload")
    print("2. 查看服务器控制台日志以获取详细的调试信息")
    print("3. 检查数据库连接和 user_activities 表")

if __name__ == "__main__":
    main()