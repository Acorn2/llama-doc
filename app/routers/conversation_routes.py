"""
对话相关的API路由
"""
import logging
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.database import get_db, Conversation, Message, User
from app.core.dependencies import get_current_user
from app.schemas import (
    ConversationCreate, 
    MessageCreate,
    ChatRequest,
    ChatStreamChunk,
    MessageResponse,
    ChatResponse,
    ActivityType
)
from app.utils.activity_logger import log_user_activity
from app.schemas.__init__ import (
    ConversationResponse,
    ConversationListResponse
)
from app.services.conversation_service import ConversationManager
from app.services.langchain_adapter import LangChainAdapter

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    responses={404: {"description": "Not found"}},
)

# 创建对话管理器实例
conversation_manager = ConversationManager()

# LangChain适配器延迟初始化
langchain_adapter = None

def get_langchain_adapter():
    """获取LangChain适配器实例（延迟初始化）"""
    global langchain_adapter
    if langchain_adapter is None:
        langchain_adapter = LangChainAdapter()
    return langchain_adapter

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新对话"""
    try:
        conversation = conversation_manager.create_conversation(
            db=db,
            kb_id=request.kb_id,
            user_id=current_user.id,
            title=request.title
        )
        
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.CONVERSATION_CREATE,
            description=f"创建会话: {conversation.title or '新对话'}",
            request=http_request,
            resource_type="conversation",
            resource_id=conversation.id,
            metadata={
                "kb_id": request.kb_id,
                "title": conversation.title
            }
        )
        
        # 转换为响应模型
        from app.schemas.__init__ import ConversationInfo
        
        conversation_info = ConversationInfo(
            id=conversation.id,
            title=conversation.title or "新对话",
            kb_id=conversation.kb_id,
            message_count=0,  # 新创建的对话消息数为0
            created_at=conversation.create_time,
            updated_at=conversation.update_time or conversation.create_time
        )
        
        return ConversationResponse(
            success=True,
            message="对话创建成功",
            conversation=conversation_info
        )
    except ValueError as e:
        logger.error(f"创建对话失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")

@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    kb_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    status: str = "active",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出所有对话"""
    try:
        result = conversation_manager.list_conversations(
            db=db,
            user_id=current_user.id,
            kb_id=kb_id,
            skip=skip,
            limit=limit,
            status=status
        )
        
        # 转换为响应模型
        from app.schemas.__init__ import ConversationInfo, ConversationList
        
        conversation_infos = []
        for conv in result["items"]:
            conversation_info = ConversationInfo(
                id=conv.id,
                title=conv.title or "新对话",
                kb_id=conv.kb_id,
                message_count=getattr(conv, 'message_count', 0),
                created_at=conv.create_time,
                updated_at=conv.update_time or conv.create_time
            )
            conversation_infos.append(conversation_info)
        
        conversation_list = ConversationList(
            conversations=conversation_infos,
            total=result["total"]
        )
        
        return ConversationListResponse(
            success=True,
            data=conversation_list,
            message="获取对话列表成功"
        )
    except Exception as e:
        logger.error(f"获取对话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取对话详情"""
    conversation = conversation_manager.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    # 转换为响应模型
    from app.schemas.__init__ import ConversationInfo
    
    conversation_info = ConversationInfo(
        id=conversation.id,
        title=conversation.title or "新对话",
        kb_id=conversation.kb_id,
        message_count=getattr(conversation, 'message_count', 0),
        created_at=conversation.create_time,
        updated_at=conversation.update_time or conversation.create_time
    )
    
    return ConversationResponse(
        success=True,
        message="获取对话详情成功",
        conversation=conversation_info
    )

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    title: str = Query(..., description="对话标题"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新对话"""
    conversation = conversation_manager.update_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        title=title
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    # 转换为响应模型
    from app.schemas.__init__ import ConversationInfo
    
    conversation_info = ConversationInfo(
        id=conversation.id,
        title=conversation.title or "新对话",
        kb_id=conversation.kb_id,
        message_count=getattr(conversation, 'message_count', 0),
        created_at=conversation.create_time,
        updated_at=conversation.update_time or conversation.create_time
    )
    
    return ConversationResponse(
        success=True,
        message="对话更新成功",
        conversation=conversation_info
    )

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除对话（逻辑删除）"""
    success = conversation_manager.delete_conversation(db, conversation_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    return {"success": True, "message": "对话已删除"}

@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取对话历史消息"""
    try:
        messages = conversation_manager.get_conversation_history(
            db=db,
            conversation_id=conversation_id,
            limit=limit,
            user_id=current_user.id
        )
        
        # 格式化输出
        result = []
        for msg in messages:
            metadata = None
            if msg.message_metadata:
                try:
                    import json
                    metadata = json.loads(msg.message_metadata)
                except Exception:
                    pass
            
            result.append({
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "create_time": msg.create_time,
                "metadata": metadata
            })
        
        return {"items": result, "total": len(result)}
    except ValueError as e:
        logger.error(f"获取对话消息失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取对话消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话消息失败: {str(e)}")

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: str,
    request: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加消息到对话"""
    try:
        message = conversation_manager.add_message(
            db=db,
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata,
            user_id=current_user.id
        )
        
        return message
    except ValueError as e:
        logger.error(f"添加消息失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"添加消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加消息失败: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """聊天接口 - 创建或继续对话"""
    start_time = time.time()
    
    try:
        # 如果没有提供对话ID，创建新对话
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = conversation_manager.create_conversation(
                db=db,
                kb_id=request.kb_id,
                user_id=current_user.id,
                title=None  # 使用默认标题
            )
            conversation_id = conversation.id
        
        # 生成回复
        use_agent = getattr(request, 'use_agent', False)
        if use_agent:
            # 使用Agent生成回复
            adapter = get_langchain_adapter()
            response = adapter.generate_agent_response(
                kb_id=request.kb_id,
                user_message=request.message,
                conversation_id=conversation_id
            )
            
            # 保存用户消息和助手回复
            conversation_manager.add_message(
                db=db,
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                user_id=current_user.id
            )
            
            message = conversation_manager.add_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=response["answer"],
                metadata={"agent_used": True},
                user_id=current_user.id
            )
            
            sources = []
        else:
            # 使用对话管理器生成回复
            adapter = get_langchain_adapter()
            result = conversation_manager.generate_response(
                db=db,
                conversation_id=conversation_id,
                user_message=request.message,
                langchain_adapter=adapter,
                user_id=current_user.id
            )
            
            message = result["message"]
            sources = result.get("sources", [])
        
        processing_time = time.time() - start_time
        
        # Convert Message object to MessageResponse dict
        metadata = None
        if hasattr(message, 'message_metadata') and message.message_metadata:
            try:
                import json
                metadata = json.loads(message.message_metadata)
            except Exception:
                metadata = None
        
        # Create MessageResponse object using the correct schema
        message_response = MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            create_time=message.create_time,
            metadata=metadata
        )
        
        # 记录对话活动
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.AGENT_CHAT if use_agent else ActivityType.CONVERSATION_CHAT,
            description=f"发送消息: {request.message[:50]}...",
            request=http_request,
            resource_type="conversation",
            resource_id=conversation_id,
            metadata={
                "kb_id": request.kb_id,
                "use_agent": use_agent,
                "message_length": len(request.message)
            }
        )
        
        return ChatResponse(
            conversation_id=conversation_id,
            message=message_response,
            sources=sources,
            processing_time=processing_time
        )
    except ValueError as e:
        logger.error(f"聊天失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"聊天失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")

@router.post("/{conversation_id}/chat", response_model=ChatResponse)
async def chat_in_conversation(
    conversation_id: str,
    http_request: Request,
    message: str = Query(..., description="用户消息"),
    use_agent: bool = Query(False, description="是否使用Agent模式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """在指定对话中聊天"""
    # 获取对话信息
    conversation = conversation_manager.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    # 创建聊天请求
    request = ChatRequest(
        conversation_id=conversation_id,
        kb_id=conversation.kb_id,
        message=message,
        use_agent=use_agent
    )
    
    # 调用聊天接口
    return await chat(request, http_request, current_user, db)

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """流式聊天接口 - 创建或继续对话"""
    start_time = time.time()
    use_agent = getattr(request, 'use_agent', False)
    
    try:
        # 如果没有提供对话ID，创建新对话
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = conversation_manager.create_conversation(
                db=db,
                kb_id=request.kb_id,
                user_id=current_user.id,
                title=None  # 使用默认标题
            )
            conversation_id = conversation.id
        
        # 记录对话活动
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.AGENT_CHAT if use_agent else ActivityType.CONVERSATION_CHAT,
            description=f"发送流式消息: {request.message[:50]}...",
            request=http_request,
            resource_type="conversation",
            resource_id=conversation_id,
            metadata={
                "kb_id": request.kb_id,
                "use_agent": use_agent,
                "message_length": len(request.message),
                "is_stream": True
            }
        )
        
        # 导入工具类
        from app.utils.streaming_utils import StreamingResponseBuilder, StreamingPresets
        
        if use_agent:
            # 使用Agent生成流式回复
            from app.services.agent_service import AgentService
            agent_service = AgentService()
            
            response = await agent_service.chat_with_agent(
                db=db,
                kb_id=request.kb_id,
                message=request.message,
                conversation_id=conversation_id,
                use_agent=True,
                stream=True
            )
            
            if response["success"]:
                return StreamingResponse(
                    StreamingResponseBuilder.create_realtime_stream(
                        llm_stream_generator=response["stream"],
                        conversation_id=conversation_id,
                        metadata={"kb_id": request.kb_id, "use_agent": True},
                        typewriter_config=StreamingPresets.FAST_NATURAL
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache", 
                        "Connection": "keep-alive"
                    }
                )
            else:
                raise ValueError(response.get("message", "Agent生成流式回复失败"))
        else:
            # 使用对话管理器生成真正的流式回复
            adapter = get_langchain_adapter()
            result = conversation_manager.generate_response(
                db=db,
                conversation_id=conversation_id,
                user_message=request.message,
                langchain_adapter=adapter,
                stream=True,
                user_id=current_user.id
            )
            
            return StreamingResponse(
                StreamingResponseBuilder.create_realtime_stream(
                    llm_stream_generator=result["stream"],
                    conversation_id=conversation_id,
                    metadata={"kb_id": request.kb_id, "use_agent": False},
                    typewriter_config=StreamingPresets.FAST_NATURAL
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache", 
                    "Connection": "keep-alive"
                }
            )
        
    except ValueError as e:
        logger.error(f"流式聊天逻辑错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"流式聊天系统异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/chat/stream")
async def chat_in_conversation_stream(
    conversation_id: str,
    http_request: Request,
    message: str = Query(..., description="用户消息"),
    use_agent: bool = Query(False, description="是否使用Agent模式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """在指定对话中进行流式聊天"""
    # 获取对话信息
    conversation = conversation_manager.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    # 创建聊天请求
    request = ChatRequest(
        conversation_id=conversation_id,
        kb_id=conversation.kb_id,
        message=message,
        use_agent=use_agent
    )
    
    # 调用流式聊天接口
    return await chat_stream(request, http_request, current_user, db)