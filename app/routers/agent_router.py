"""
Agent API路由
基于LangChain的智能Agent接口
"""

import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.schemas.agent_schemas import (
    AgentChatRequest, AgentChatResponse,
    DocumentAnalysisRequest, DocumentAnalysisResponse,
    KnowledgeSearchRequest, KnowledgeSearchResponse,
    SummaryRequest, SummaryResponse,
    ConversationHistoryResponse, AgentStatusResponse
)
from app.schemas import ChatStreamChunk
from app.services.agent_service import AgentService
from app.api.dependencies import get_agent_service_dep, handle_service_exceptions
from app.core.dependencies import get_current_user
from app.database import User, get_db
from sqlalchemy.orm import Session
from app.utils.activity_logger import log_user_activity
from app.schemas import ActivityType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/chat", response_model=AgentChatResponse, summary="Agent对话")
@handle_service_exceptions
async def agent_chat(
    request_data: AgentChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service_dep),
    db: Session = Depends(get_db)
):
    """
    与Agent进行对话
    支持Agent模式和普通对话模式
    """
    result = await agent_service.chat_with_agent(
        db=db,
        kb_id=request_data.kb_id,
        message=request_data.message,
        conversation_id=request_data.conversation_id,
        use_agent=request_data.use_agent,
        llm_type=request_data.llm_type
    )
    
    # 记录对话活动
    log_user_activity(
        db=db,
        user=current_user,
        activity_type=ActivityType.AGENT_CHAT if request_data.use_agent else ActivityType.CONVERSATION_CHAT,
        description=f"发送消息: {request_data.message[:50]}...",
        request=request,
        resource_type="conversation",
        resource_id=request_data.conversation_id or (result.get("data", {}).get("conversation_id") if isinstance(result, dict) and result.get("success") else None),
        metadata={
            "kb_id": request_data.kb_id,
            "use_agent": request_data.use_agent,
            "message_length": len(request_data.message)
        }
    )
    
    return result

@router.post("/analyze", response_model=DocumentAnalysisResponse, summary="文档分析")
@handle_service_exceptions
async def analyze_document(
    request_data: DocumentAnalysisRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service_dep),
    db: Session = Depends(get_db)
):
    """
    使用Agent分析文档内容
    """
    result = await agent_service.analyze_document(
        db=db,
        kb_id=request_data.kb_id,
        query=request_data.query,
        llm_type=request_data.llm_type
    )
    

    
    return result

@router.post("/search", response_model=KnowledgeSearchResponse, summary="知识搜索")
@handle_service_exceptions
async def search_knowledge(
    request_data: KnowledgeSearchRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service_dep),
    db: Session = Depends(get_db)
):
    """
    在知识库中搜索信息
    """
    result = await agent_service.search_knowledge(
        db=db,
        kb_id=request_data.kb_id,
        query=request_data.query,
        max_results=request_data.max_results,
        llm_type=request_data.llm_type
    )
    

    
    return result

@router.post("/summary", response_model=SummaryResponse, summary="生成摘要")
@handle_service_exceptions
async def generate_summary(
    request_data: SummaryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service_dep),
    db: Session = Depends(get_db)
):
    """
    生成文档摘要
    """
    result = await agent_service.generate_summary(
        db=db,
        kb_id=request_data.kb_id,
        llm_type=request_data.llm_type
    )
    

    
    return result

@router.get("/history/{kb_id}", response_model=ConversationHistoryResponse, summary="获取对话历史")
@handle_service_exceptions
async def get_conversation_history(
    kb_id: str, 
    llm_type: str = "qwen",
    agent_service: AgentService = Depends(get_agent_service_dep),
    db: Session = Depends(get_db)
):
    """
    获取Agent对话历史
    """
    result = await agent_service.get_conversation_history(
        db=db,
        kb_id=kb_id,
        llm_type=llm_type
    )
    return result

@router.delete("/memory/{kb_id}", response_model=dict, summary="清除对话记忆")
@handle_service_exceptions
async def clear_agent_memory(
    kb_id: str, 
    llm_type: str = "qwen",
    agent_service: AgentService = Depends(get_agent_service_dep),
    db: Session = Depends(get_db)
):
    """
    清除Agent对话记忆
    """
    result = await agent_service.clear_agent_memory(
        db=db,
        kb_id=kb_id,
        llm_type=llm_type
    )
    return result

@router.delete("/cache", response_model=dict, summary="清除Agent缓存")
@handle_service_exceptions
async def clear_agent_cache(
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    清除所有Agent缓存
    """
    result = agent_service.clear_agent_cache()
    return result

@router.get("/status/{kb_id}", response_model=AgentStatusResponse, summary="获取Agent状态")
@handle_service_exceptions
async def get_agent_status(
    kb_id: str, 
    llm_type: str = "qwen",
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    获取Agent状态信息
    """
    result = agent_service.get_agent_status(
        kb_id=kb_id,
        llm_type=llm_type
    )
    return result

@router.post("/chat/stream", summary="Agent流式对话")
@handle_service_exceptions
async def agent_chat_stream(
    request: AgentChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service_dep),
    db: Session = Depends(get_db)
):
    """
    Agent流式对话接口
    支持打字机效果的实时流式输出
    """
    from app.utils.streaming_utils import StreamingResponseBuilder, StreamingPresets
    import json
    import time
    
    start_time = time.time()
    
    async def generate_stream():
        try:
            # 调用Agent服务获取完整回复
            result = await agent_service.chat_with_agent(
                db=db,
                kb_id=request.kb_id,
                message=request.message,
                conversation_id=request.conversation_id,
                use_agent=request.use_agent,
                llm_type=request.llm_type
            )
            

            # 记录对话活动
            log_user_activity(
                db=db,
                user=current_user,
                activity_type=ActivityType.AGENT_CHAT if request.use_agent else ActivityType.CONVERSATION_CHAT,
                description=f"发送流式消息: {request.message[:50]}...",
                request=http_request,
                resource_type="conversation",
                resource_id=request.conversation_id or (result.get("data", {}).get("conversation_id") if result.get("success") else None),
                metadata={
                    "kb_id": request.kb_id,
                    "use_agent": request.use_agent,
                    "message_length": len(request.message),
                    "is_stream": True
                }
            )
            
            if result["success"]:
                response_data = result["data"]
                
                # 根据消息长度和内容选择合适的打字机预设
                message_length = len(request.message)
                response_length = len(response_data.get("answer", ""))
                
                if response_length < 100:
                    preset = StreamingPresets.FAST_NATURAL
                elif response_length < 500:
                    preset = StreamingPresets.NATURAL
                else:
                    preset = StreamingPresets.STANDARD
                
                # 使用打字机效果流式输出
                stream_generator = StreamingResponseBuilder.create_agent_stream(
                    response_data=response_data,
                    kb_id=request.kb_id,
                    use_agent=request.use_agent,
                    typewriter_config=preset
                )
                
                async for chunk in stream_generator:
                    yield chunk
                    
            else:
                # 错误情况 - 使用打字机效果输出错误信息
                error_message = "抱歉，处理您的请求时发生了错误。"
                error_data = {"answer": error_message, "error": True}
                
                stream_generator = StreamingResponseBuilder.create_agent_stream(
                    response_data=error_data,
                    kb_id=request.kb_id,
                    use_agent=request.use_agent,
                    typewriter_config=StreamingPresets.FAST_NATURAL
                )
                
                async for chunk in stream_generator:
                    yield chunk
                
        except Exception as e:
            # 异常情况 - 使用打字机效果输出异常信息
            error_message = f"处理请求时发生错误: {str(e)}"
            error_data = {"answer": error_message, "error": True}
            
            stream_generator = StreamingResponseBuilder.create_agent_stream(
                response_data=error_data,
                kb_id=request.kb_id,
                use_agent=request.use_agent,
                typewriter_config=StreamingPresets.FAST_NATURAL
            )
            
            async for chunk in stream_generator:
                yield chunk
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )