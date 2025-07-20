"""
测试路由 - 用于测试对话功能，不依赖向量搜索
"""

import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.model_factory import ModelFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/test", tags=["测试"])

class SimpleTestRequest(BaseModel):
    """简单测试请求"""
    message: str
    llm_type: str = "qwen"

class SimpleTestResponse(BaseModel):
    """简单测试响应"""
    success: bool
    answer: str
    timestamp: str
    processing_time: float
    error: str = None

@router.post("/simple-chat", response_model=SimpleTestResponse)
async def simple_chat_test(request: SimpleTestRequest):
    """
    简单对话测试 - 不依赖向量搜索，直接测试LLM
    """
    import time
    start_time = time.time()
    current_timestamp = datetime.now().isoformat()
    
    try:
        # 直接创建LLM实例进行测试
        llm = ModelFactory.create_llm(request.llm_type)
        
        # 创建简单的测试提示
        test_prompt = f"""
你是一个智能助手。请回答用户的问题：

用户问题：{request.message}

请提供一个简洁、有用的回答：
"""
        
        # 直接调用LLM
        answer = llm.invoke(test_prompt)
        
        processing_time = time.time() - start_time
        
        return SimpleTestResponse(
            success=True,
            answer=answer,
            timestamp=current_timestamp,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"简单对话测试失败: {e}")
        
        return SimpleTestResponse(
            success=False,
            answer="测试失败，请检查LLM配置",
            timestamp=current_timestamp,
            processing_time=processing_time,
            error=str(e)
        )

@router.get("/health")
async def test_health():
    """测试健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "测试路由正常工作"
    }

@router.post("/llm-direct")
async def test_llm_direct(request: SimpleTestRequest):
    """
    直接测试LLM连接
    """
    try:
        llm = ModelFactory.create_llm(request.llm_type)
        
        # 测试简单调用
        result = llm.invoke("你好，请回复'测试成功'")
        
        return {
            "success": True,
            "llm_type": request.llm_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"LLM直接测试失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }