"""
健康检查和系统监控API
"""

import logging
import time
import psutil
from typing import Dict, Any
from fastapi import APIRouter, Depends
from datetime import datetime

from app.config.settings import get_settings, AppSettings
from app.core.container import get_agent_service
from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", summary="基础健康检查")
async def health_check() -> Dict[str, Any]:
    """
    基础健康检查
    返回服务基本状态
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Knowledge Base API",
        "version": "1.0.0"
    }


@router.get("/detailed", summary="详细健康检查")
async def detailed_health_check(
    settings: AppSettings = Depends(get_settings),
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """
    详细健康检查
    包含系统资源、服务状态等信息
    """
    start_time = time.time()
    
    # 系统资源信息
    system_info = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
    }
    
    # Agent服务状态
    agent_cache_status = agent_service.cache_manager.get_cache_status()
    
    # 配置状态
    config_status = {
        "debug_mode": settings.debug,
        "llm_type": settings.llm.default_llm_type,
        "agent_cache_enabled": settings.agent.enable_cache,
        "agent_memory_enabled": settings.agent.enable_memory
    }
    
    response_time = time.time() - start_time
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": settings.app_name,
        "version": settings.version,
        "response_time": f"{response_time:.3f}s",
        "system": system_info,
        "agent_cache": agent_cache_status,
        "configuration": config_status,
        "uptime": time.time()  # 简化的运行时间
    }


@router.get("/readiness", summary="就绪检查")
async def readiness_check(
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """
    就绪检查
    检查服务是否准备好接收请求
    """
    checks = {}
    all_ready = True
    
    # 检查Agent服务
    try:
        cache_status = agent_service.cache_manager.get_cache_status()
        checks["agent_service"] = {
            "status": "ready",
            "cached_agents": cache_status["total_agents"]
        }
    except Exception as e:
        checks["agent_service"] = {
            "status": "not_ready",
            "error": str(e)
        }
        all_ready = False
    
    # 检查配置
    try:
        settings = get_settings()
        checks["configuration"] = {
            "status": "ready",
            "app_name": settings.app_name
        }
    except Exception as e:
        checks["configuration"] = {
            "status": "not_ready",
            "error": str(e)
        }
        all_ready = False
    
    return {
        "status": "ready" if all_ready else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "checks": checks
    }


@router.get("/liveness", summary="存活检查")
async def liveness_check() -> Dict[str, Any]:
    """
    存活检查
    检查服务是否仍在运行
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "pid": psutil.Process().pid,
        "memory_usage": f"{psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB"
    }