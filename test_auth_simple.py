#!/usr/bin/env python3
"""
简化的认证测试脚本
"""
import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

def test_auth_simple():
    """简化的认证测试"""
    
    # 1. 测试用户登录
    logger.info("🧪 测试用户登录...")
    login_data = {
        "login_credential": "test@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/users/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        logger.info(f"登录响应: {response.status_code}")
        if response.status_code == 200:
            login_result = response.json()
            token = login_result.get("access_token")
            if token:
                logger.info("✅ 用户登录成功，获得token")
                logger.info(f"Token前20字符: {token[:20]}...")
            else:
                logger.error("❌ 登录成功但未获得token")
                return
        else:
            logger.error(f"❌ 用户登录失败: {response.text}")
            return
    except Exception as e:
        logger.error(f"❌ 登录请求失败: {e}")
        return
    
    # 2. 测试活动记录接口
    logger.info("🧪 测试获取用户活动记录...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/users/activities?limit=5",
            headers=headers
        )
        logger.info(f"获取活动记录响应: {response.status_code}")
        
        if response.status_code == 200:
            activities = response.json()
            logger.info(f"✅ 获取活动记录成功，共 {len(activities)} 条记录")
            if activities:
                logger.info(f"第一条记录: {activities[0]}")
            else:
                logger.info("活动记录为空")
        else:
            logger.error(f"❌ 获取活动记录失败 ({response.status_code}): {response.text}")
    except Exception as e:
        logger.error(f"❌ 获取活动记录请求失败: {e}")

if __name__ == "__main__":
    test_auth_simple()