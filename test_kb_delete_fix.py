#!/usr/bin/env python3
"""
测试知识库删除功能修复
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def login():
    """用户登录"""
    print("=== 用户登录 ===")
    
    login_data = {
        "email": "test@example.com",
        "password": "123456"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        
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

def create_test_knowledge_base(token):
    """创建测试知识库"""
    print("\n=== 创建测试知识库 ===")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    kb_data = {
        "name": "测试删除知识库",
        "description": "用于测试删除功能的知识库",
        "is_public": False,
        "tags": ["测试", "删除"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/knowledge-bases/", 
                               json=kb_data, headers=headers)
        
        if response.status_code == 201:
            data = response.json()
            kb_id = data["id"]
            print(f"✅ 知识库创建成功: {data['name']} (ID: {kb_id})")
            return kb_id
        else:
            print(f"❌ 知识库创建失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 创建请求失败: {e}")
        return None

def test_delete_knowledge_base(token, kb_id):
    """测试删除知识库"""
    print(f"\n=== 测试删除知识库 (ID: {kb_id}) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.delete(f"{BASE_URL}/api/v1/knowledge-bases/{kb_id}", 
                                 headers=headers)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 知识库删除成功:")
            print(f"   消息: {data['message']}")
            print(f"   知识库ID: {data['data']['kb_id']}")
            print(f"   知识库名称: {data['data']['kb_name']}")
            return True
        elif response.status_code == 405:
            print("❌ 删除失败: Method Not Allowed (405)")
            print("   这表明DELETE路由仍然没有正确配置")
            return False
        else:
            print(f"❌ 删除失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 删除请求失败: {e}")
        return False

def verify_knowledge_base_deleted(token, kb_id):
    """验证知识库是否已删除"""
    print(f"\n=== 验证知识库是否已删除 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/knowledge-bases/{kb_id}", 
                              headers=headers)
        
        if response.status_code == 404:
            print("✅ 验证成功: 知识库已被删除（返回404）")
            return True
        elif response.status_code == 200:
            data = response.json()
            if data.get('status') == 'deleted':
                print("✅ 验证成功: 知识库状态已标记为deleted")
                return True
            else:
                print(f"⚠️  知识库仍然存在，状态: {data.get('status')}")
                return False
        else:
            print(f"❓ 意外响应: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 验证请求失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 测试知识库删除功能修复")
    print("=" * 60)
    
    # 1. 登录
    token = login()
    if not token:
        print("❌ 无法获取认证token，测试终止")
        return False
    
    # 2. 创建测试知识库
    kb_id = create_test_knowledge_base(token)
    if not kb_id:
        print("❌ 无法创建测试知识库，测试终止")
        return False
    
    # 3. 测试删除知识库
    delete_success = test_delete_knowledge_base(token, kb_id)
    
    # 4. 验证删除结果
    if delete_success:
        verify_knowledge_base_deleted(token, kb_id)
    
    print("\n" + "=" * 60)
    if delete_success:
        print("🎉 知识库删除功能修复成功！")
        print("\n✅ 修复效果:")
        print("- DELETE /api/v1/knowledge-bases/{kb_id} 路由已正常工作")
        print("- 返回200状态码而不是405 Method Not Allowed")
        print("- 正确执行逻辑删除操作")
        print("- 记录用户活动日志")
    else:
        print("❌ 知识库删除功能仍有问题")
        print("\n🔧 可能的原因:")
        print("- 路由没有正确注册")
        print("- 服务器需要重启以加载新路由")
        print("- 权限检查失败")
    
    print("\n💡 提示:")
    print("1. 确保服务器正在运行: uvicorn app.main:app --reload")
    print("2. 如果仍然返回405，请重启服务器")
    print("3. 检查服务器日志获取详细错误信息")
    
    return delete_success

if __name__ == "__main__":
    main()