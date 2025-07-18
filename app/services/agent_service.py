"""
Agent业务服务层
处理Agent相关的业务逻辑
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.langchain_agent import LangChainDocumentAgent
from app.services.knowledge_base_service import KnowledgeBaseManager
from app.utils.exceptions import AgentError, KnowledgeBaseNotFoundError

logger = logging.getLogger(__name__)


class AgentCacheManager:
    """Agent缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, LangChainDocumentAgent] = {}
    
    def get_cache_key(self, kb_id: str, llm_type: str) -> str:
        """生成缓存键"""
        return f"{kb_id}:{llm_type}"
    
    def get_agent(self, kb_id: str, llm_type: str = "qwen") -> LangChainDocumentAgent:
        """获取或创建Agent实例"""
        cache_key = self.get_cache_key(kb_id, llm_type)
        
        if cache_key not in self._cache:
            self._cache[cache_key] = LangChainDocumentAgent(
                kb_id=kb_id,
                llm_type=llm_type
            )
            logger.info(f"创建新的Agent实例: {cache_key}")
        
        return self._cache[cache_key]
    
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
        self.cache_manager = AgentCacheManager()
        self.kb_manager = KnowledgeBaseManager()
    
    async def _validate_knowledge_base(self, kb_id: str) -> None:
        """验证知识库是否存在"""
        kb_info = await self.kb_manager.get_knowledge_base(kb_id)
        if not kb_info:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: {kb_id}")
    
    async def chat_with_agent(
        self,
        kb_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        use_agent: bool = True,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        与Agent进行对话
        
        Args:
            kb_id: 知识库ID
            message: 用户消息
            conversation_id: 对话ID
            use_agent: 是否使用Agent模式
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 对话结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(kb_id)
            
            # 获取Agent实例
            agent = self.cache_manager.get_agent(kb_id, llm_type)
            
            # 执行对话
            response = agent.chat(
                message=message,
                conversation_id=conversation_id,
                use_agent=use_agent
            )
            
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
        kb_id: str,
        query: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        分析文档内容
        
        Args:
            kb_id: 知识库ID
            query: 分析查询
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(kb_id)
            
            # 获取Agent实例
            agent = self.cache_manager.get_agent(kb_id, llm_type)
            
            # 执行文档分析
            response = agent.analyze_document(query)
            
            if not response["success"]:
                raise AgentError(response.get("error", "文档分析失败"))
            
            return {
                "success": True,
                "data": {
                    "analysis": response["analysis"],
                    "query": response["query"],
                    "processing_time": response["processing_time"]
                }
            }
            
        except (KnowledgeBaseNotFoundError, AgentError):
            raise
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            raise AgentError(f"文档分析失败: {str(e)}")
    
    async def search_knowledge(
        self,
        kb_id: str,
        query: str,
        max_results: int = 5,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            kb_id: 知识库ID
            query: 搜索查询
            max_results: 最大结果数
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(kb_id)
            
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
        kb_id: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        生成文档摘要
        
        Args:
            kb_id: 知识库ID
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 摘要结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(kb_id)
            
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
        kb_id: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        获取对话历史
        
        Args:
            kb_id: 知识库ID
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 对话历史
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(kb_id)
            
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
        kb_id: str,
        llm_type: str = "qwen"
    ) -> Dict[str, Any]:
        """
        清除Agent对话记忆
        
        Args:
            kb_id: 知识库ID
            llm_type: LLM类型
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证知识库
            await self._validate_knowledge_base(kb_id)
            
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