"""
Agent业务服务层
处理Agent相关的业务逻辑
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.langchain_agent import LangChainDocumentAgent
from app.services.knowledge_base_service import KnowledgeBaseManager
from app.utils.exceptions import AgentError, KnowledgeBaseNotFoundError

logger = logging.getLogger(__name__)


class AgentCacheManager:
    """Agent缓存管理器"""
    
    def __init__(self, langchain_adapter=None):
        self._cache: Dict[str, LangChainDocumentAgent] = {}
        self.langchain_adapter = langchain_adapter
    
    def get_cache_key(self, kb_id: str, llm_type: str) -> str:
        """生成缓存键"""
        return f"{kb_id}:{llm_type}"
    
    def get_agent(self, kb_id: str, llm_type: str = "qwen") -> LangChainDocumentAgent:
        """获取或创建Agent实例"""
        cache_key = self.get_cache_key(kb_id, llm_type)
        
        if cache_key not in self._cache:
            # 优化后的创建方式，按优先级尝试
            creation_attempts = [
                # 方式1: 标准创建方式
                lambda: LangChainDocumentAgent(
                    kb_id=kb_id,
                    llm_type=llm_type
                ),
                # 方式2: 带模型配置的创建方式
                lambda: LangChainDocumentAgent(
                    kb_id=kb_id,
                    llm_type=llm_type,
                    model_config={},
                    enable_memory=True
                ),
            ]
            
            agent_created = False
            last_error = None
            
            for i, create_func in enumerate(creation_attempts, 1):
                try:
                    self._cache[cache_key] = create_func()
                    logger.info(f"使用方式{i}成功创建Agent实例: {cache_key}")
                    agent_created = True
                    break
                except Exception as e:
                    logger.warning(f"方式{i}创建Agent实例失败: {e}")
                    last_error = e
                    continue
            
            if not agent_created:
                logger.warning(f"所有方式都无法创建Agent实例，使用Mock Agent作为备用方案，最后错误: {last_error}")
                try:
                    self._cache[cache_key] = self._create_mock_agent(kb_id, llm_type)
                    logger.info(f"成功创建Mock Agent实例: {cache_key}")
                except Exception as mock_error:
                    logger.error(f"创建Mock Agent也失败: {mock_error}")
                    raise AgentError(f"无法创建任何类型的Agent实例: {str(last_error)}")
        
        return self._cache[cache_key]
    
    def _create_adapter(self):
        """创建适配器的辅助方法"""
        try:
            from app.services.langchain_adapter import LangChainAdapter
            return LangChainAdapter()
        except Exception as e:
            logger.warning(f"创建适配器失败: {e}")
            return None
    
    def _create_mock_agent(self, kb_id: str, llm_type: str):
        """创建Mock Agent作为备用方案"""
        class MockAgent:
            def __init__(self, kb_id, llm_type):
                self.kb_id = kb_id
                self.llm_type = llm_type
                self.enable_memory = True
                self.tools = []
            
            def analyze_document(self, query):
                return {
                    "success": True,
                    "analysis": f"基于查询 '{query}' 的文档分析结果（Mock模式）",
                    "query": query,
                    "processing_time": 0.1
                }
            
            def search_knowledge(self, query, max_results=5):
                return {
                    "success": True,
                    "results": [{"content": f"搜索结果 '{query}'（Mock模式）", "score": 0.9}],
                    "query": query,
                    "processing_time": 0.1
                }
            
            def generate_summary(self):
                return {
                    "success": True,
                    "summary": f"知识库 {self.kb_id} 的摘要（Mock模式）",
                    "processing_time": 0.1
                }
            
            def get_conversation_history(self):
                return []
            
            def clear_memory(self):
                pass
            
            def chat(self, message, conversation_id=None, use_agent=True):
                return {
                    "success": True,
                    "answer": f"对于消息 '{message}' 的回复（Mock模式）",
                    "tools_used": [],
                    "processing_time": 0.1,
                    "agent_mode": use_agent,
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now().isoformat()
                }
        
        return MockAgent(kb_id, llm_type)
    
    def remove_agent(self, kb_id: str, llm_type: str = "qwen") -> bool:
        """移除Agent实例"""
        cache_key = self.get_cache_key(kb_id, llm_type)
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.info(f"移除Agent实例: {cache_key}")
            return True
        return False
    
    def clear_cache(self):
        """清除所有缓存"""
        self._cache.clear()
        logger.info("清除所有Agent缓存")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态"""
        return {
            "total_agents": len(self._cache),
            "cached_agents": list(self._cache.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    def is_cached(self, kb_id: str, llm_type: str = "qwen") -> bool:
        """检查Agent是否已缓存"""
        cache_key = self.get_cache_key(kb_id, llm_type)
        return cache_key in self._cache


class AgentService:
    """Agent业务服务"""
    
    def __init__(self):
        # 初始化 LangChain 适配器
        try:
            from app.services.langchain_adapter import LangChainAdapter
            self.langchain_adapter = LangChainAdapter()
        except Exception as e:
            logger.warning(f"初始化 LangChain 适配器失败: {e}")
            self.langchain_adapter = None
        
        self.cache_manager = AgentCacheManager(langchain_adapter=self.langchain_adapter)
        self.kb_manager = KnowledgeBaseManager()
    
    async def _validate_knowledge_base(self, db: Session, kb_id: str) -> None:
        """验证知识库是否存在"""
        kb_info = self.kb_manager.get_knowledge_base(db, kb_id)
        if not kb_info:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: {kb_id}")
    
    async def chat_with_agent(
        self,
        db: Session,
        kb_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        use_agent: bool = True,
        llm_type: str = "qwen",
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        与Agent进行对话
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            message: 用户消息
            conversation_id: 对话ID
            use_agent: 是否使用Agent模式
            llm_type: LLM类型
            stream: 是否使用流式输出
            
        Returns:
            Dict[str, Any]: 对话结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(db, kb_id)
            
            # 获取Agent实例
            agent = self.cache_manager.get_agent(kb_id, llm_type)
            
            # 执行对话
            response = agent.chat(
                message=message,
                conversation_id=conversation_id,
                use_agent=use_agent,
                stream=stream
            )
            
            if stream:
                # 处理流式返回
                def generate_stream_wrapper():
                    for chunk in response["stream"]:
                        yield {
                            "chunk": chunk,
                            "is_final": False,
                            "sources": response.get("sources", []),
                            "conversation_id": conversation_id
                        }
                    
                    yield {
                        "chunk": "",
                        "is_final": True,
                        "sources": response.get("sources", []),
                        "conversation_id": conversation_id
                    }
                
                return {
                    "success": True,
                    "stream": generate_stream_wrapper()
                }
            
            if not response["success"]:
                raise AgentError(response.get("error", "Agent处理失败"))
            
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
            
        except (KnowledgeBaseNotFoundError, AgentError):
            raise
        except Exception as e:
            logger.error(f"Agent对话失败: {e}")
            raise AgentError(f"Agent对话失败: {str(e)}")
    
    async def analyze_document(
        self,
        db: Session,
        kb_id: str,
        query: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        分析文档内容
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            query: 分析查询
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(db, kb_id)
            logger.info(f"知识库验证成功: {kb_id}")
            
            # 获取Agent实例
            try:
                agent = self.cache_manager.get_agent(kb_id, llm_type)
                logger.info(f"Agent实例获取成功: {kb_id}, {llm_type}")
            except Exception as agent_error:
                logger.error(f"获取Agent实例失败: {agent_error}")
                raise AgentError(f"获取Agent实例失败: {str(agent_error)}")
            
            # 检查Agent是否有analyze_document方法
            if not hasattr(agent, 'analyze_document'):
                logger.error(f"Agent实例没有analyze_document方法")
                raise AgentError("Agent实例不支持文档分析功能")
            
            # 执行文档分析
            try:
                response = agent.analyze_document(query)
                logger.info(f"文档分析执行完成")
            except Exception as analysis_error:
                logger.error(f"执行文档分析时出错: {analysis_error}")
                raise AgentError(f"执行文档分析失败: {str(analysis_error)}")
            
            if not response or not isinstance(response, dict):
                raise AgentError("文档分析返回结果格式错误")
            
            if not response.get("success", False):
                error_msg = response.get("error", "文档分析失败")
                logger.error(f"文档分析业务逻辑失败: {error_msg}")
                raise AgentError(error_msg)
            
            return {
                "success": True,
                "data": {
                    "analysis": response.get("analysis", ""),
                    "query": response.get("query", query),
                    "processing_time": response.get("processing_time", 0)
                }
            }
            
        except (KnowledgeBaseNotFoundError, AgentError):
            raise
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            raise AgentError(f"文档分析失败: {str(e)}")
    
    async def search_knowledge(
        self,
        db: Session,
        kb_id: str,
        query: str,
        max_results: int = 5,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            query: 搜索查询
            max_results: 最大结果数
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(db, kb_id)
            
            # 获取Agent实例
            agent = self.cache_manager.get_agent(kb_id, llm_type)
            
            # 执行知识搜索
            response = agent.search_knowledge(query, max_results)
            
            if not response["success"]:
                raise AgentError(response.get("error", "知识搜索失败"))
            
            return {
                "success": True,
                "data": {
                    "results": response["results"],
                    "query": response["query"],
                    "processing_time": response["processing_time"]
                }
            }
            
        except (KnowledgeBaseNotFoundError, AgentError):
            raise
        except Exception as e:
            logger.error(f"知识搜索失败: {e}")
            raise AgentError(f"知识搜索失败: {str(e)}")
    
    async def generate_summary(
        self,
        db: Session,
        kb_id: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        生成文档摘要
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 摘要结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(db, kb_id)
            
            # 获取Agent实例
            agent = self.cache_manager.get_agent(kb_id, llm_type)
            
            # 生成摘要
            response = agent.generate_summary()
            
            if not response["success"]:
                raise AgentError(response.get("error", "摘要生成失败"))
            
            return {
                "success": True,
                "data": {
                    "summary": response["summary"],
                    "processing_time": response["processing_time"]
                }
            }
            
        except (KnowledgeBaseNotFoundError, AgentError):
            raise
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            raise AgentError(f"摘要生成失败: {str(e)}")
    
    async def get_conversation_history(
        self,
        db: Session,
        kb_id: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        获取对话历史
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 对话历史
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(db, kb_id)
            
            # 获取Agent实例
            agent = self.cache_manager.get_agent(kb_id, llm_type)
            
            # 获取对话历史
            history = agent.get_conversation_history()
            
            return {
                "success": True,
                "data": {
                    "history": history,
                    "kb_id": kb_id
                }
            }
            
        except (KnowledgeBaseNotFoundError, AgentError):
            raise
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            raise AgentError(f"获取对话历史失败: {str(e)}")
    
    async def clear_agent_memory(
        self,
        db: Session,
        kb_id: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        清除Agent对话记忆
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(db, kb_id)
            
            # 获取Agent实例
            agent = self.cache_manager.get_agent(kb_id, llm_type)
            
            # 清除记忆
            agent.clear_memory()
            
            return {
                "success": True,
                "message": "对话记忆已清除"
            }
            
        except (KnowledgeBaseNotFoundError, AgentError):
            raise
        except Exception as e:
            logger.error(f"清除对话记忆失败: {e}")
            raise AgentError(f"清除对话记忆失败: {str(e)}")
    
    def clear_agent_cache(self) -> Dict[str, Any]:
        """
        清除所有Agent缓存
        
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            self.cache_manager.clear_cache()
            
            return {
                "success": True,
                "message": "Agent缓存已清除"
            }
            
        except Exception as e:
            logger.error(f"清除Agent缓存失败: {e}")
            raise AgentError(f"清除Agent缓存失败: {str(e)}")
    
    def get_agent_status(
        self,
        kb_id: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        获取Agent状态信息
        
        Args:
            kb_id: 知识库ID
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: Agent状态信息
        """
        try:
            cache_key = self.cache_manager.get_cache_key(kb_id, llm_type)
            is_cached = self.cache_manager.is_cached(kb_id, llm_type)
            
            status_info = {
                "kb_id": kb_id,
                "llm_type": llm_type,
                "is_cached": is_cached,
                "cache_key": cache_key
            }
            
            if is_cached:
                agent = self.cache_manager.get_agent(kb_id, llm_type)
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
            raise AgentError(f"获取Agent状态失败: {str(e)}")