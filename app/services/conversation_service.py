import uuid
import json
import logging
import time
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.database import Conversation, Message, KnowledgeBase
from app.services.knowledge_base_service import KnowledgeBaseManager
from app.core.model_factory import ModelFactory

logger = logging.getLogger(__name__)

class ConversationManager:
    """对话管理模块"""
    
    def __init__(self, kb_manager=None, llm=None):
        self.kb_manager = kb_manager or KnowledgeBaseManager()
        self.llm = llm or ModelFactory.create_llm()
        self.memory_store = {}  # 内存中缓存对话历史
        
    def create_conversation(
        self, 
        db: Session, 
        kb_id: str, 
        user_id: str,
        title: Optional[str] = None
    ) -> Conversation:
        """
        创建新对话
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            user_id: 用户ID
            title: 对话标题，可选
            
        Returns:
            Conversation: 创建的对话对象
        """
        # 检查知识库是否存在且用户有权限访问
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"知识库不存在: {kb_id}")
            raise ValueError("知识库不存在")
        
        # 检查用户是否有权限访问知识库
        # 用户可以访问自己的知识库或公开的知识库
        if kb.user_id != user_id and not kb.is_public:
            logger.error(f"用户 {user_id} 无权限访问知识库 {kb_id}")
            raise ValueError("无权限访问该知识库")
        
        # 如果是公开知识库，记录访问
        if kb.is_public and kb.user_id != user_id:
            self.kb_manager.record_knowledge_base_access(
                db=db,
                kb_id=kb_id,
                user_id=user_id,
                access_type="chat",
                metadata={"action": "create_conversation"}
            )
        
        # 生成唯一ID
        conversation_id = str(uuid.uuid4())
        
        # 如果未提供标题，生成默认标题
        if not title:
            title = f"对话 {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 创建对话记录
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            kb_id=kb_id,
            title=title,
            status="active"
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"成功创建对话: {conversation_id}, 知识库: {kb_id}")
        return conversation
    
    def add_message(
        self, 
        db: Session, 
        conversation_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Message:
        """
        添加消息到对话
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            role: 消息角色 (user, assistant, system)
            content: 消息内容
            metadata: 消息元数据，可选
            user_id: 用户ID，用于权限检查
            
        Returns:
            Message: 创建的消息对象
        """
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"对话不存在: {conversation_id}")
            raise ValueError("对话不存在")
        
        # 检查用户权限（如果提供了user_id）
        if user_id and conversation.user_id != user_id:
            logger.error(f"用户 {user_id} 无权限访问对话 {conversation_id}")
            raise ValueError("无权限访问该对话")
        
        # 检查角色是否有效
        valid_roles = ["user", "assistant", "system"]
        if role not in valid_roles:
            logger.error(f"无效的消息角色: {role}")
            raise ValueError(f"无效的消息角色，必须是以下之一: {', '.join(valid_roles)}")
        
        # 获取当前对话中的最大序号
        from sqlalchemy import func
        max_sequence = db.query(func.max(Message.sequence_number)).filter(
            Message.conversation_id == conversation_id
        ).scalar() or 0
        
        # 序列化元数据
        metadata_json = None
        if metadata:
            try:
                metadata_json = json.dumps(metadata, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"元数据序列化失败: {e}")
        
        # 创建消息记录，序号自动递增
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            sequence_number=max_sequence + 1,  # 新增序号字段
            message_metadata=metadata_json
        )
        
        db.add(message)
        
        # 更新对话的更新时间（通过onupdate触发器自动更新）
        db.commit()
        db.refresh(message)
        
        # 更新内存缓存
        if conversation_id in self.memory_store:
            self.memory_store[conversation_id].append({
                "role": role,
                "content": content,
                "id": message.id,
                "sequence_number": message.sequence_number,  # 添加序号到缓存
                "metadata": metadata
            })
        
        logger.debug(f"已添加消息到对话: {conversation_id}, 角色: {role}, 序号: {message.sequence_number}, 长度: {len(content)}")
        return message
    
    def get_conversation_history(
        self, 
        db: Session, 
        conversation_id: str, 
        limit: int = 20,
        user_id: Optional[str] = None
    ) -> List[Message]:
        """
        获取对话历史
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            limit: 返回消息数量限制
            user_id: 用户ID，用于权限检查
            
        Returns:
            List[Message]: 消息对象列表
        """
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"对话不存在: {conversation_id}")
            raise ValueError("对话不存在")
        
        # 检查用户权限（如果提供了user_id）
        if user_id and conversation.user_id != user_id:
            logger.error(f"用户 {user_id} 无权限访问对话 {conversation_id}")
            raise ValueError("无权限访问该对话")
        
        # 查询消息历史，使用序号排序
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(
            Message.sequence_number.asc()  # 按序号升序排列
        ).limit(limit).all()
        
        return messages
    
    def get_conversation_context(
        self, 
        db: Session, 
        conversation_id: str, 
        message_limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取对话上下文（用于生成下一个回复）
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            message_limit: 消息数量限制
            
        Returns:
            List[Dict[str, Any]]: 消息字典列表，格式为LangChain兼容格式
        """
        # 检查内存缓存
        if conversation_id in self.memory_store:
            return self.memory_store[conversation_id][-message_limit:]
        
        # 从数据库加载
        messages = self.get_conversation_history(db, conversation_id, message_limit, user_id)
        
        # 转换为LangChain兼容格式
        context = []
        for msg in messages:
            metadata = None
            if msg.message_metadata:
                try:
                    metadata = json.loads(msg.message_metadata)
                except Exception:
                    pass
                
            context.append({
                "role": msg.role,
                "content": msg.content,
                "id": msg.id,
                "metadata": metadata
            })
        
        # 更新内存缓存
        self.memory_store[conversation_id] = context
        
        return context
    
    def generate_response(
        self, 
        db: Session, 
        conversation_id: str, 
        user_message: str,
        langchain_adapter=None,
        stream: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成助手回复
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            user_message: 用户消息
            langchain_adapter: LangChain适配器，可选
            stream: 是否使用流式输出
            
        Returns:
            Dict[str, Any]: 包含生成的回复和元数据的字典，或生成器（流式模式）
        """
        start_time = time.time()
        
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"对话不存在: {conversation_id}")
            raise ValueError("对话不存在")
        
        # 获取知识库ID
        kb_id = conversation.kb_id
        
        # 保存用户消息
        self.add_message(db, conversation_id, "user", user_message, user_id=user_id)
        
        # 从知识库检索相关内容
        search_results = self.kb_manager.search_knowledge_base(
            kb_id=kb_id,
            query=user_message,
            top_k=5,
            db=db
        )
        
        # 构建上下文
        context = self.get_conversation_context(db, conversation_id, user_id=user_id)
        
        # 如果提供了LangChain适配器，使用适配器生成回复
        if langchain_adapter:
            response = langchain_adapter.generate_conversation_response(
                kb_id=kb_id,
                conversation_id=conversation_id,
                user_message=user_message,
                context=context,
                search_results=search_results,
                stream=stream
            )
            
            if stream and "stream" in response:
                # 流式模式：返回生成器
                def generate_response_stream():
                    full_answer = ""
                    sources = response.get("sources", [])
                    
                    for chunk in response["stream"]:
                        full_answer += chunk
                        yield {
                            "chunk": chunk,
                            "sources": sources,
                            "is_final": False
                        }
                    
                    # 保存完整回复到数据库
                    processing_time = time.time() - start_time
                    metadata = {
                        "sources": sources,
                        "processing_time": processing_time
                    }
                    message = self.add_message(db, conversation_id, "assistant", full_answer, metadata, user_id=user_id)
                    
                    # 发送最终块
                    yield {
                        "chunk": "",
                        "sources": sources,
                        "processing_time": processing_time,
                        "message": message,
                        "is_final": True
                    }
                
                return {
                    "stream": generate_response_stream(),
                    "conversation_id": conversation_id
                }
            else:
                # 非流式模式
                answer = response["answer"]
                sources = response.get("sources", [])
        else:
            # 否则使用默认方式生成回复
            if stream:
                # 简单流式实现：将完整回复分块发送
                answer = self._generate_simple_response(
                    user_message=user_message,
                    context=context,
                    search_results=search_results
                )
                sources = [
                    {"content": result["content"], "score": result.get("similarity_score", 0)}
                    for result in search_results[:3]
                ]
                
                def generate_simple_stream():
                    # 将答案按句子分块
                    import re
                    sentences = re.split(r'[。！？\n]', answer)
                    
                    for sentence in sentences:
                        if sentence.strip():
                            yield {
                                "chunk": sentence + "。",
                                "sources": sources,
                                "is_final": False
                            }
                            time.sleep(0.1)  # 模拟流式延迟
                    
                    # 保存完整回复到数据库
                    processing_time = time.time() - start_time
                    metadata = {
                        "sources": sources,
                        "processing_time": processing_time
                    }
                    message = self.add_message(db, conversation_id, "assistant", answer, metadata, user_id=user_id)
                    
                    # 发送最终块
                    yield {
                        "chunk": "",
                        "sources": sources,
                        "processing_time": processing_time,
                        "message": message,
                        "is_final": True
                    }
                
                return {
                    "stream": generate_simple_stream(),
                    "conversation_id": conversation_id
                }
            else:
                answer = self._generate_simple_response(
                    user_message=user_message,
                    context=context,
                    search_results=search_results
                )
                sources = [
                    {"content": result["content"], "score": result.get("similarity_score", 0)}
                    for result in search_results[:3]
                ]
        
        # 非流式模式的处理
        if not stream:
            # 记录生成回复所需的时间
            processing_time = time.time() - start_time
            
            # 创建元数据
            metadata = {
                "sources": sources,
                "processing_time": processing_time
            }
            
            # 保存助手回复
            message = self.add_message(db, conversation_id, "assistant", answer, metadata, user_id=user_id)
            
            return {
                "message": message,
                "sources": sources,
                "processing_time": processing_time
            }
    
    def _generate_simple_response(
        self, 
        user_message: str, 
        context: List[Dict[str, Any]], 
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        使用简单方式生成回复
        
        Args:
            user_message: 用户消息
            context: 对话上下文
            search_results: 搜索结果
            
        Returns:
            str: 生成的回复
        """
        # 构建提示
        context_text = "\n\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in context[-5:]  # 仅使用最近5条消息
        ])
        
        search_text = "\n\n".join([
            f"文档片段 {i+1}:\n{result['content']}"
            for i, result in enumerate(search_results[:3])  # 仅使用前3条搜索结果
        ])
        
        prompt = f"""你是一个智能助手，基于以下对话历史和知识库检索结果回答用户的问题。

对话历史:
{context_text}

知识库检索结果:
{search_text}

请根据以上信息回答用户的问题: {user_message}
如果知识库中没有相关信息，请明确告知用户。
"""
        
        # 使用LLM生成回复
        response = self.llm.predict(prompt)
        
        return response.strip()
    
    def list_conversations(
        self, 
        db: Session, 
        user_id: str,
        kb_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        列出用户的对话
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            kb_id: 知识库ID过滤，可选
            skip: 跳过记录数
            limit: 返回记录数
            status: 对话状态过滤
            
        Returns:
            Dict[str, Any]: 包含对话列表和总数的字典
        """
        query = db.query(Conversation).filter(Conversation.user_id == user_id)
        
        if kb_id:
            query = query.filter(Conversation.kb_id == kb_id)
        
        if status:
            query = query.filter(Conversation.status == status)
        
        total = query.count()
        items = query.order_by(Conversation.update_time.desc()).offset(skip).limit(limit).all()
        
        return {
            "items": items,
            "total": total
        }
    
    def get_conversation(self, db: Session, conversation_id: str, user_id: Optional[str] = None) -> Optional[Conversation]:
        """
        获取对话详情
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            user_id: 用户ID，用于权限检查
            
        Returns:
            Conversation: 对话对象
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        
        # 检查用户权限（如果提供了user_id）
        if conversation and user_id and conversation.user_id != user_id:
            logger.error(f"用户 {user_id} 无权限访问对话 {conversation_id}")
            return None
            
        return conversation
    
    def update_conversation(
        self, 
        db: Session, 
        conversation_id: str, 
        user_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[Conversation]:
        """
        更新对话信息
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            user_id: 用户ID
            title: 新标题，可选
            status: 新状态，可选
            
        Returns:
            Conversation: 更新后的对话对象
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conversation:
            logger.error(f"对话不存在或无权限: {conversation_id}")
            return None
        
        if title is not None:
            conversation.title = title
        
        if status is not None:
            conversation.status = status
        
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    def delete_conversation(self, db: Session, conversation_id: str, user_id: str) -> bool:
        """
        删除对话（逻辑删除）
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            bool: 操作是否成功
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conversation:
            logger.error(f"对话不存在或无权限: {conversation_id}")
            return False
        
        # 逻辑删除
        conversation.status = "deleted"
        db.commit()
        
        # 清除内存缓存
        if conversation_id in self.memory_store:
            del self.memory_store[conversation_id]
        
        return True 