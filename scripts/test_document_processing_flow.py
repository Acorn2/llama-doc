#!/usr/bin/env python3
"""
测试文档处理流程 - 验证异步处理架构
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

def test_document_upload_flow(token):
    """测试文档上传和处理流程"""
    print("\n=== 测试文档上传流程 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建测试文档
    test_content = """
    这是一个测试文档。
    
    第一章：介绍
    本文档用于测试PDF文献智能分析服务的文档处理功能。
    
    第二章：功能特性
    1. 文档上传与解析
    2. 智能文档问答
    3. 知识库管理
    4. Agent智能对话
    
    第三章：技术架构
    系统采用FastAPI + LangChain + Qdrant + PostgreSQL的技术栈。
    支持异步文档处理，提高系统响应速度。
    
    结论：
    该系统能够有效处理PDF文档，提供智能分析服务。
    """
    
    test_file = io.BytesIO(test_content.encode('utf-8'))
    files = {'file': ('test_document.txt', test_file, 'text/plain')}
    
    # 1. 上传文档
    print("1. 上传文档...")
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/documents/upload", 
                               files=files, headers=headers)
        upload_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            document_id = data["document_id"]
            print(f"✅ 文档上传成功，耗时: {upload_time:.2f}秒")
            print(f"   文档ID: {document_id}")
            print(f"   状态: {data['status']}")
            print(f"   消息: {data['message']}")
            
            return document_id
        else:
            print(f"❌ 文档上传失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 上传请求失败: {e}")
        return None

def monitor_document_processing(token, document_id):
    """监控文档处理进度"""
    print(f"\n=== 监控文档处理进度 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    max_wait_time = 60  # 最大等待60秒
    check_interval = 2  # 每2秒检查一次
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(f"{BASE_URL}/api/v1/documents/{document_id}/status", 
                                  headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                status = data["status"]
                elapsed = time.time() - start_time
                
                print(f"[{elapsed:.1f}s] 状态: {status} - {data.get('message', '')}")
                
                if status == "completed":
                    print("✅ 文档处理完成！")
                    return True
                elif status in ["failed", "failed_permanently"]:
                    print(f"❌ 文档处理失败: {data.get('error_message', '')}")
                    return False
                    
            else:
                print(f"❌ 状态查询失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
        
        time.sleep(check_interval)
    
    print("⚠️ 处理超时，可能需要更长时间")
    return False

def get_document_info(token, document_id):
    """获取文档详细信息"""
    print(f"\n=== 获取文档详细信息 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/documents/{document_id}", 
                              headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 文档信息获取成功:")
            print(f"   文件名: {data['filename']}")
            print(f"   文件大小: {data['file_size']} bytes")
            print(f"   状态: {data['status']}")
            print(f"   文件类型: {data.get('file_type', 'N/A')}")
            print(f"   页数: {data.get('pages', 'N/A')}")
            print(f"   文本块数: {data.get('chunk_count', 'N/A')}")
            print(f"   上传时间: {data['upload_time']}")
            return data
        else:
            print(f"❌ 获取文档信息失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_processing_status():
    """测试处理状态接口"""
    print(f"\n=== 测试处理状态接口 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/processing/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 处理状态获取成功:")
            print(f"   轮询运行中: {data['is_running']}")
            print(f"   正在处理文档数: {data['processing_count']}")
            if data['processing_documents']:
                print(f"   处理中的文档: {data['processing_documents']}")
            return data
        else:
            print(f"❌ 获取处理状态失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def main():
    """主函数"""
    print("🚀 开始测试文档处理流程")
    print("=" * 60)
    
    # 1. 用户认证
    token = register_and_login()
    if not token:
        print("❌ 用户认证失败，测试终止")
        return
    
    # 2. 测试处理状态
    test_processing_status()
    
    # 3. 上传文档
    document_id = test_document_upload_flow(token)
    if not document_id:
        print("❌ 文档上传失败，测试终止")
        return
    
    # 4. 监控处理进度
    success = monitor_document_processing(token, document_id)
    
    # 5. 获取最终文档信息
    final_info = get_document_info(token, document_id)
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 文档处理流程测试成功！")
        print("\n📊 性能总结:")
        print("- 文档上传：快速响应（< 1秒）")
        print("- 异步处理：后台定时任务处理")
        print("- 状态监控：实时查询处理进度")
        print("- 架构优势：上传和处理分离，提升用户体验")
    else:
        print("❌ 文档处理流程测试失败")
    
    print("\n💡 架构说明:")
    print("1. /upload 接口只负责文件保存，快速响应")
    print("2. DocumentTaskProcessor 定时任务处理文档解析和向量化")
    print("3. VectorSyncProcessor 处理知识库向量同步")
    print("4. 轮询间隔已优化为2秒，提高响应速度")

if __name__ == "__main__":
    main()