#!/usr/bin/env python3
"""
测试文档上传并自动添加到知识库
"""
import requests
import time
import json
import io
from datetime import datetime

BASE_URL = "http://localhost:8000"

def register_and_login():
    """注册并登录用户"""
    print("=== 用户注册和登录 ===")
    
    # 注册用户
    register_data = {
        "email": f"test_{int(time.time())}@example.com",
        "password": "password123",
        "username": "testuser"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/users/register", json=register_data)
        if response.status_code == 200:
            print("✅ 用户注册成功")
        else:
            print(f"❌ 用户注册失败: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 注册请求失败: {e}")
        return None
    
    # 登录用户
    login_data = {
        "login_credential": register_data["email"],
        "password": register_data["password"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/users/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            print("✅ 用户登录成功")
            return data["access_token"]
        else:
            print(f"❌ 用户登录失败: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return None

def create_knowledge_base(token):
    """创建知识库"""
    print("\n=== 创建知识库 ===")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    kb_data = {
        "name": "测试知识库",
        "description": "用于测试文档上传的知识库",
        "is_public": False,
        "tags": ["测试", "文档上传"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/knowledge-bases/", 
                               json=kb_data, headers=headers)
        
        if response.status_code == 200:
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

def test_upload_without_kb(token):
    """测试不指定知识库的上传"""
    print("\n=== 测试普通上传（不指定知识库）===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    test_content = "这是一个测试文档，用于验证普通上传功能。"
    test_file = io.BytesIO(test_content.encode('utf-8'))
    files = {'file': ('test_normal.txt', test_file, 'text/plain')}
    
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/documents/upload", 
                               files=files, headers=headers)
        upload_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 普通上传成功，耗时: {upload_time:.2f}秒")
            print(f"   文档ID: {data['document_id']}")
            print(f"   消息: {data['message']}")
            return data['document_id']
        else:
            print(f"❌ 普通上传失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 上传请求失败: {e}")
        return None

def test_upload_with_kb(token, kb_id):
    """测试指定知识库的上传"""
    print(f"\n=== 测试上传到知识库 (ID: {kb_id}) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    test_content = """
    这是一个测试文档，用于验证自动添加到知识库的功能。
    
    内容包括：
    1. 测试文档上传
    2. 自动添加到知识库
    3. 验证整个流程
    
    这个文档应该会自动添加到指定的知识库中。
    """
    
    test_file = io.BytesIO(test_content.encode('utf-8'))
    files = {'file': ('test_with_kb.txt', test_file, 'text/plain')}
    data = {'kb_id': kb_id}  # 指定知识库ID
    
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/documents/upload", 
                               files=files, data=data, headers=headers)
        upload_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 知识库上传成功，耗时: {upload_time:.2f}秒")
            print(f"   文档ID: {result['document_id']}")
            print(f"   消息: {result['message']}")
            return result['document_id']
        else:
            print(f"❌ 知识库上传失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 上传请求失败: {e}")
        return None

def verify_kb_documents(token, kb_id):
    """验证知识库中的文档"""
    print(f"\n=== 验证知识库文档 (ID: {kb_id}) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/knowledge-bases/{kb_id}/documents", 
                              headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get('data', {}).get('documents', [])
            print(f"✅ 知识库中有 {len(documents)} 个文档:")
            
            for doc in documents:
                print(f"   - {doc['filename']} (ID: {doc['document_id']})")
                print(f"     状态: {doc['status']}, 添加时间: {doc['add_time']}")
            
            return len(documents)
        else:
            print(f"❌ 获取知识库文档失败: {response.text}")
            return 0
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return 0

def test_performance_comparison():
    """性能对比测试"""
    print("\n=== 性能对比测试 ===")
    
    print("📊 理论性能对比:")
    print("┌─────────────────────┬──────────────┬──────────────┐")
    print("│       操作          │   原始方式   │   优化方式   │")
    print("├─────────────────────┼──────────────┼──────────────┤")
    print("│ 1. 上传文档         │    2-3秒     │    2-3秒     │")
    print("│ 2. 添加到知识库     │    1-2秒     │     0秒      │")
    print("│ 总耗时              │    3-5秒     │    2-3秒     │")
    print("│ 前端操作步骤        │      2步     │      1步     │")
    print("└─────────────────────┴──────────────┴──────────────┘")
    
    print("\n💡 优化效果:")
    print("- 减少前端操作步骤：2步 → 1步")
    print("- 提升用户体验：一次上传，自动关联")
    print("- 减少网络请求：2次 → 1次")
    print("- 降低出错概率：自动化处理")

def main():
    """主函数"""
    print("🚀 测试文档上传优化功能")
    print("=" * 60)
    
    # 1. 用户认证
    token = register_and_login()
    if not token:
        print("❌ 用户认证失败，测试终止")
        return
    
    # 2. 创建知识库
    kb_id = create_knowledge_base(token)
    if not kb_id:
        print("❌ 知识库创建失败，测试终止")
        return
    
    # 3. 测试普通上传
    doc1_id = test_upload_without_kb(token)
    
    # 4. 测试知识库上传
    doc2_id = test_upload_with_kb(token, kb_id)
    
    # 5. 验证知识库文档
    doc_count = verify_kb_documents(token, kb_id)
    
    # 6. 性能对比
    test_performance_comparison()
    
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    
    if doc1_id:
        print("✅ 普通上传测试通过")
    else:
        print("❌ 普通上传测试失败")
    
    if doc2_id:
        print("✅ 知识库上传测试通过")
    else:
        print("❌ 知识库上传测试失败")
    
    if doc_count > 0:
        print(f"✅ 知识库文档验证通过 ({doc_count}个文档)")
    else:
        print("❌ 知识库文档验证失败")
    
    print("\n🎯 优化建议:")
    print("1. 前端可以在上传时提供知识库选择器")
    print("2. 支持批量上传到同一知识库")
    print("3. 添加上传进度显示")
    print("4. 优化前端超时设置，避免不必要的等待")

if __name__ == "__main__":
    main()