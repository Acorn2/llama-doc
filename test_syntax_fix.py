#!/usr/bin/env python3
"""
测试语法修复后的认证问题
"""
import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

def test_specific_endpoints():
    """测试特定的端点"""
    
    # 1. 登录获取token
    login_data = {
        "login_credential": "test@example.com",
        "password": "password123"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/users/login", json=login_data)
    if response.status_code != 200:
        logger.error(f"登录失败: {response.text}")
        return
    
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 测试 /users/me 接口（应该工作）
    logger.info("🧪 测试 /users/me 接口...")
    response = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
    logger.info(f"/users/me 响应: {response.status_code}")
    if response.status_code == 200:
        logger.info("✅ /users/me 正常工作")
    else:
        logger.error(f"❌ /users/me 失败: {response.text}")
    
    # 3. 测试 /users/test-auth-required 接口
    logger.info("🧪 测试 /users/test-auth-required 接口...")
    response = requests.get(f"{BASE_URL}/api/v1/users/test-auth-required", headers=headers)
    logger.info(f"/users/test-auth-required 响应: {response.status_code}")
    if response.status_code == 200:
        logger.info("✅ /users/test-auth-required 正常工作")
    else:
        logger.error(f"❌ /users/test-auth-required 失败: {response.text}")
    
    # 4. 测试 /users/activities 接口
    logger.info("🧪 测试 /users/activities 接口...")
    response = requests.get(f"{BASE_URL}/api/v1/users/activities", headers=headers)
    logger.info(f"/users/activities 响应: {response.status_code}")
    if response.status_code == 200:
        logger.info("✅ /users/activities 正常工作")
        activities = response.json()
        logger.info(f"活动记录数量: {len(activities)}")
    else:
        logger.error(f"❌ /users/activities 失败: {response.text}")
    
    # 5. 测试 /users/activities/stats 接口
    logger.info("🧪 测试 /users/activities/stats 接口...")
    response = requests.get(f"{BASE_URL}/api/v1/users/activities/stats", headers=headers)
    logger.info(f"/users/activities/stats 响应: {response.status_code}")
    if response.status_code == 200:
        logger.info("✅ /users/activities/stats 正常工作")
    else:
        logger.error(f"❌ /users/activities/stats 失败: {response.text}")

if __name__ == "__main__":
    test_specific_endpoints()