#!/usr/bin/env python3
"""
监控文档处理状态
"""
import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def check_system_health():
    """检查系统健康状态"""
    print("🏥 系统健康检查")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 系统状态: {data['status']}")
            print(f"   服务名称: {data['service']}")
            print(f"   检查时间: {data['timestamp']}")
            return True
        else:
            print(f"❌ 系统异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def check_processing_status():
    """检查文档处理状态"""
    print("\n📊 文档处理状态")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/processing/status")
        if response.status_code == 200:
            data = response.json()
            print(f"🔄 轮询状态: {'运行中' if data['is_running'] else '已停止'}")
            print(f"📝 处理中文档数: {data['processing_count']}")
            
            if data['processing_documents']:
                print("📋 处理中的文档:")
                for doc_id in data['processing_documents']:
                    print(f"   - {doc_id}")
            else:
                print("📋 当前无文档在处理")
            
            return data
        else:
            print(f"❌ 获取状态失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def check_api_endpoints():
    """检查关键API端点"""
    print("\n🔗 API端点检查")
    print("-" * 40)
    
    endpoints = [
        ("根路径", "GET", "/"),
        ("健康检查", "GET", "/health"),
        ("API文档", "GET", "/docs"),
        ("处理状态", "GET", "/api/v1/system/processing/status"),
    ]
    
    for name, method, path in endpoints:
        try:
            url = f"{BASE_URL}{path}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {name}: 正常")
            elif response.status_code == 401:
                print(f"🔐 {name}: 需要认证")
            else:
                print(f"⚠️ {name}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {name}: 连接失败")

def monitor_continuous():
    """持续监控模式"""
    print("\n🔍 持续监控模式 (按Ctrl+C停止)")
    print("=" * 50)
    
    try:
        while True:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{current_time}] 检查中...")
            
            # 检查处理状态
            status = check_processing_status()
            
            if status and status['processing_count'] > 0:
                print(f"🔥 发现 {status['processing_count']} 个文档正在处理")
            else:
                print("😴 系统空闲中")
            
            time.sleep(5)  # 每5秒检查一次
            
    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")

def main():
    """主函数"""
    print("🚀 文档处理监控工具")
    print("=" * 50)
    
    # 基础检查
    if not check_system_health():
        print("❌ 系统不可用，请检查服务是否启动")
        return
    
    check_processing_status()
    check_api_endpoints()
    
    print("\n" + "=" * 50)
    print("💡 使用说明:")
    print("1. 确保服务正在运行 (python -m uvicorn app.main:app --reload)")
    print("2. 上传文档后观察处理状态变化")
    print("3. 使用 scripts/test_document_processing_flow.py 进行完整测试")
    
    # 询问是否进入持续监控模式
    try:
        choice = input("\n是否进入持续监控模式? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            monitor_continuous()
    except KeyboardInterrupt:
        print("\n👋 再见!")

if __name__ == "__main__":
    main()