#!/usr/bin/env python3
"""
测试知识库文档列表接口修复
"""
import requests
import time
import json
import io

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
        "description": "用于测试文档列表的知识库",
        "is_public": False,
        "tags": ["测试", "文档列表"]
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

def upload_document(token):
    """上传测试文档"""
    print("\n=== 上传测试文档 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    test_content = """
    这是一个测试文档，用于验证知识库文档列表功能。
    
    内容包括：
    1. 测试文档上传
    2. 测试文档列表显示
    3. 验证字段映射
    
    这个文档将用于测试知识库文档列表接口。
    """
    
    test_file = io.BytesIO(test_content.encode('utf-8'))
    files = {'file': ('test_kb_document.txt', test_file, 'text/plain')}
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/documents/upload", 
                               files=files, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            document_id = data['document_id']
            print(f"✅ 文档上传成功: {data['filename']} (ID: {document_id})")
            return document_id
        else:
            print(f"❌ 文档上传失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 上传请求失败: {e}")
        return None

def add_document_to_kb(token, kb_id, document_id):
    """添加文档到知识库"""
    print(f"\n=== 添加文档到知识库 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/knowledge-bases/{kb_id}/documents/{document_id}", 
                               headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 文档添加成功: {data['message']}")
            return True
        else:
            print(f"❌ 文档添加失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 添加请求失败: {e}")
        return False

def test_kb_documents_list(token, kb_id):
    """测试知识库文档列表接口"""
    print(f"\n=== 测试知识库文档列表接口 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/knowledge-bases/{kb_id}/documents", 
                              headers=headers)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 知识库文档列表获取成功:")
            print(f"   知识库ID: {data['data']['kb_id']}")
            print(f"   知识库名称: {data['data']['kb_name']}")
            print(f"   文档总数: {data['data']['total']}")
            
            documents = data['data']['documents']
            if documents:
                print("   文档列表:")
                for doc in documents:
                    print(f"     - 文档ID: {doc['document_id']}")
                    print(f"       文件名: {doc['filename']}")
                    print(f"       文件大小: {doc['file_size']} bytes")
                    print(f"       状态: {doc['status']}")
                    print(f"       上传时间: {doc['upload_time']}")
                    if doc.get('file_type'):
                        print(f"       文件类型: {doc['file_type']}")
                    if doc.get('chunk_count'):
                        print(f"       文本块数: {doc['chunk_count']}")
            else:
                print("   暂无文档")
            
            return True
        else:
            print(f"❌ 获取文档列表失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_empty_kb_documents_list(token, kb_id):
    """测试空知识库的文档列表"""
    print(f"\n=== 测试空知识库文档列表 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/knowledge-bases/{kb_id}/documents", 
                              headers=headers)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 空知识库文档列表获取成功:")
            print(f"   文档总数: {data['data']['total']}")
            return True
        else:
            print(f"❌ 获取空文档列表失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 测试知识库文档列表接口修复")
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
    
    # 3. 测试空知识库文档列表
    test_empty_kb_documents_list(token, kb_id)
    
    # 4. 上传文档
    document_id = upload_document(token)
    if not document_id:
        print("❌ 文档上传失败，跳过后续测试")
        return
    
    # 5. 添加文档到知识库
    if not add_document_to_kb(token, kb_id, document_id):
        print("❌ 文档添加失败，跳过后续测试")
        return
    
    # 6. 测试有文档的知识库文档列表
    success = test_kb_documents_list(token, kb_id)
    
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    
    if success:
        print("✅ 知识库文档列表接口修复成功")
        print("✅ DocumentInfo模型字段映射正确")
        print("✅ 接口返回数据格式正确")
    else:
        print("❌ 知识库文档列表接口仍有问题")
    
    print("\n🔧 修复内容:")
    print("1. 统一DocumentInfo模型定义")
    print("2. 修复字段名不一致问题 (id vs document_id)")
    print("3. 移除不存在的max_retries字段传递")
    print("4. 添加缺失的file_md5字段")

if __name__ == "__main__":
    main()