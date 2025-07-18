"""
Agent API路由
基于LangChain的智能Agent接口
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.langchain_agent import LangChainDocumentAgent
from app.schemas import ChatRequest, ChatResponse, MessageResponse
from app.services.knowledge_base_service import KnowledgeBaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])

# 请求模型
class AgentChatRequest(BaseModel):
    """Agent对话请求"""
    kb_id: str = Field(..., description="知识库ID")
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    use_agent: bool = Field(True, description="是否使用Agent模式")
    llm_type: str = Field("qwen", description="LLM类型")

class DocumentAnalysisRequest(BaseModel):
    """文档分析请求"""
    kb_id: str = Field(..., description="知识库ID")
    query: str = Field(..., description="分析查询")
    llm_type: str = Field("qwen", description="LLM类型")

class KnowledgeSearchRequest(BaseModel):
    """知识搜索请求"""
    kb_id: str = Field(..., description="知识库ID")
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(5, description="最大结果数")
    llm_type: str = Field("qwen", description="LLM类型")

class SummaryRequest(BaseModel):
    """摘要生成请求"""
    kb_id: str = Field(..., description="知识库ID")
    llm_type: str = Field("qwen", description="LLM类型")

# Agent实例缓存
agent_cache = {}

def get_agent(kb_id: str, llm_type: str = "qwen") -> LangChainDocumentAgent:
    """获取或创建Agent实例"""
    cache_key = f"{kb_id}:{llm_type}"
    
    if cache_key not in agent_cache:
        agent_cache[cache_key] = LangChainDocumentAgent(
            kb_id=kb_id,
            llm_type=llm_type
        )
    
    return agent_cache[cache_key]

@router.post("/chat", response_model=dict, summary="Agent对话")
async def agent_chat(request: AgentChatRequest):
    """
    与Agent进行对话
    支持Agent模式和普通对话模式
    """
    try:
        # 验证知识库是否存在
        kb_manager = KnowledgeBaseManager()
        kb_info = await kb_manager.get_knowledge_base(request.kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 获取Agent实例
        agent = get_agent(request.kb_id, request.llm_type)
        
        # 执行对话
        response = agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            use_agent=request.use_agent
        )
        
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response.get("error", "Agent处理失败"))
        
        return {
            "success": True,
            "data": {
                "answer": response["answer"],
                "tools_used": response.get("tools_used", []),
                "processing_time": response["processing_time"],
                "agent_mode": response["agent_mode"],
                "conversation_id": response.get("conversation_id"),
                "timestamp": response["timestamp"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"Agent对话失败: {str(e)}")

@router.post("/analyze", response_model=dict, summary="文档分析")
async def analyze_document(request: DocumentAnalysisRequest):
    """
    使用Agent分析文档内容
    """
    try:
        # 验证知识库是否存在
        kb_manager = KnowledgeBaseManager()
        kb_info = await kb_manager.get_knowledge_base(request.kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 获取Agent实例
        agent = get_agent(request.kb_id, request.llm_type)
        
        # 执行文档分析
        response = agent.analyze_document(request.query)
        
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response.get("error", "文档分析失败"))
        
        return {
            "success": True,
            "data": {
                "analysis": response["analysis"],
                "query": response["query"],
                "processing_time": response["processing_time"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档分析失败: {str(e)}")

@router.post("/search", response_model=dict, summary="知识搜索")
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    在知识库中搜索信息
    """
    try:
        # 验证知识库是否存在
        kb_manager = KnowledgeBaseManager()
        kb_info = await kb_manager.get_knowledge_base(request.kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 获取Agent实例
        agent = get_agent(request.kb_id, request.llm_type)
        
        # 执行知识搜索
        response = agent.search_knowledge(request.query, request.max_results)
        
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response.get("error", "知识搜索失败"))
        
        return {
            "success": True,
            "data": {
                "results": response["results"],
                "query": response["query"],
                "processing_time": response["processing_time"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"知识搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"知识搜索失败: {str(e)}")

@router.post("/summary", response_model=dict, summary="生成摘要")
async def generate_summary(request: SummaryRequest):
    """
    生成文档摘要
    """
    try:
        # 验证知识库是否存在
        kb_manager = KnowledgeBaseManager()
        kb_info = await kb_manager.get_knowledge_base(request.kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 获取Agent实例
        agent = get_agent(request.kb_id, request.llm_type)
        
        # 生成摘要
        response = agent.generate_summary()
        
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response.get("error", "摘要生成失败"))
        
        return {
            "success": True,
            "data": {
                "summary": response["summary"],
                "processing_time": response["processing_time"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"摘要生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"摘要生成失败: {str(e)}")

@router.get("/history/{kb_id}", response_model=dict, summary="获取对话历史")
async def get_conversation_history(kb_id: str, llm_type: str = "qwen"):
    """
    获取Agent对话历史
    """
    try:
        # 验证知识库是否存在
        kb_manager = KnowledgeBaseManager()
        kb_info = await kb_manager.get_knowledge_base(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 获取Agent实例
        agent = get_agent(kb_id, llm_type)
        
        # 获取对话历史
        history = agent.get_conversation_history()
        
        return {
            "success": True,
            "data": {
                "history": history,
                "kb_id": kb_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")

@router.delete("/memory/{kb_id}", response_model=dict, summary="清除对话记忆")
async def clear_agent_memory(kb_id: str, llm_type: str = "qwen"):
    """
    清除Agent对话记忆
    """
    try:
        # 验证知识库是否存在
        kb_manager = KnowledgeBaseManager()
        kb_info = await kb_manager.get_knowledge_base(kb_id)
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 获取Agent实例
        agent = get_agent(kb_id, llm_type)
        
        # 清除记忆
        agent.clear_memory()
        
        return {
            "success": True,
            "message": "对话记忆已清除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除对话记忆失败: {e}")
        raise HTTPException(status_code=500, detail=f"清除对话记忆失败: {str(e)}")

@router.delete("/cache", response_model=dict, summary="清除Agent缓存")
async def clear_agent_cache():
    """
    清除所有Agent缓存
    """
    try:
        global agent_cache
        agent_cache.clear()
        
        return {
            "success": True,
            "message": "Agent缓存已清除"
        }
        
    except Exception as e:
        logger.error(f"清除Agent缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清除Agent缓存失败: {str(e)}")

@router.get("/status/{kb_id}", response_model=dict, summary="获取Agent状态")
async def get_agent_status(kb_id: str, llm_type: str = "qwen"):
    """
    获取Agent状态信息
    """
    try:
        cache_key = f"{kb_id}:{llm_type}"
        is_cached = cache_key in agent_cache
        
        status_info = {
            "kb_id": kb_id,
            "llm_type": llm_type,
            "is_cached": is_cached,
            "cache_key": cache_key
        }
        
        if is_cached:
            agent = agent_cache[cache_key]
            history_count = len(agent.get_conversation_history())
            status_info.update({
                "conversation_history_count": history_count,
                "memory_enabled": agent.enable_memory,
                "tools_count": len(agent.tools)
            })
        
        return {
            "success": True,
            "data": status_info
        }
        
    except Exception as e:
        logger.error(f"获取Agent状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取Agent状态失败: {str(e)}")