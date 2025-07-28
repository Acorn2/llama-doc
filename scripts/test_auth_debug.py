#!/usr/bin/env python3
"""
专门测试认证问题的调试脚本
"""
import requests
import json
import sys

def test_auth_endpoints():
    """测试认证相关的接口"""
    print("🔐 开始测试认证相关接口...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试无需认证的接口
    print("\n1️⃣ 测试无需认证的接口...")
    try:
        response = requests.get(f"{base_url}/api/v1/users/test-auth")
        print(f"📊 响应状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ 无需认证接口正常: {response.json()}")
        else:
            print(f"❌ 无需认证接口异常: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 无需认证接口测试失败: {str(e)}")
        return False
    
    # 2. 测试用户登录获取token
    print("\n2️⃣ 测试用户登录...")
    login_data = {
        "login_credential": "test_debug@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/users/login", json=login_data)
        print(f"📊 登录响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 用户登录成功")
            token_data = response.json()
            access_token = token_data["access_token"]
            print(f"🔑 获取到访问令牌: {access_token[:50]}...")
        else:
            print(f"❌ 登录失败: {response.status_code}")
            print(f"📄 错误响应: {response.text}")
            
            # 如果登录失败，尝试注册
            print("\n🔄 尝试注册用户...")
            register_data = {
                "username": "test_user_debug",
                "email": "test_debug@example.com",
                "password": "password123",
                "full_name": "测试用户"
            }
            
            reg_response = requests.post(f"{base_url}/api/v1/users/register", json=register_data)
            print(f"📊 注册响应状态码: {reg_response.status_code}")
            
            if reg_response.status_code == 201:
                print("✅ 用户注册成功，重新登录...")
                login_response = requests.post(f"{base_url}/api/v1/users/login", json=login_data)
                if login_response.status_code == 200:
                    token_data = login_response.json()
                    access_token = token_data["access_token"]
                    print(f"🔑 重新获取到访问令牌: {access_token[:50]}...")
                else:
                    print(f"❌ 重新登录失败: {login_response.text}")
                    return False
            else:
                print(f"❌ 注册失败: {reg_response.text}")
                return False
    except Exception as e:
        print(f"❌ 登录测试失败: {str(e)}")
        return False
    
    # 3. 测试需要认证的简单接口
    print("\n3️⃣ 测试需要认证的简单接口...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{base_url}/api/v1/users/test-auth-required", headers=headers)
        print(f"📊 认证测试响应状态码: {response.status_code}")
        print(f"📋 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ 认证测试成功")
            auth_result = response.json()
            print(f"👤 认证用户信息: {json.dumps(auth_result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 认证测试失败: {response.status_code}")
            print(f"📄 错误响应: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 认证测试异常: {str(e)}")
        return False
    
    # 4. 测试原始的 activities 接口
    print("\n4️⃣ 测试原始的 activities 接口...")
    try:
        response = requests.get(f"{base_url}/api/v1/users/activities", headers=headers)
        print(f"📊 activities 接口响应状态码: {response.status_code}")
        print(f"📋 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ activities 接口调用成功")
            activities = response.json()
            print(f"📝 获取到 {len(activities)} 条活动记录")
        elif response.status_code == 403:
            print("❌ activities 接口返回403权限错误")
            print(f"📄 错误响应: {response.text}")
        else:
            print(f"❌ activities 接口调用失败: {response.status_code}")
            print(f"📄 错误响应: {response.text}")
    except Exception as e:
        print(f"❌ activities 接口测试异常: {str(e)}")
    
    # 5. 测试 dashboard/stats 接口（对比）
    print("\n5️⃣ 测试 dashboard/stats 接口（对比）...")
    try:
        response = requests.get(f"{base_url}/api/v1/users/dashboard/stats", headers=headers)
        print(f"📊 dashboard/stats 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ dashboard/stats 接口正常")
        else:
            print(f"❌ dashboard/stats 接口异常: {response.text}")
    except Exception as e:
        print(f"❌ dashboard/stats 接口测试失败: {str(e)}")
    
    return True

def main():
    """主函数"""
    print("🚀 开始认证调试测试")
    print("=" * 60)
    
    success = test_auth_endpoints()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 认证调试测试完成！")
        print("\n💡 如果 activities 接口仍然返回403，请检查服务器日志中的详细认证过程。")
    else:
        print("❌ 认证调试测试失败！")
    
    print("\n📝 注意事项:")
    print("1. 确保服务器正在运行")
    print("2. 查看服务器控制台日志获取详细的认证调试信息")
    print("3. 特别关注 🔐 和 ❌ 标记的日志信息")

if __name__ == "__main__":
    main()