"""
依赖注入容器
集中管理应用的所有依赖
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar, Callable
from functools import lru_cache

from app.config.settings import get_settings
from app.services.agent_service import AgentService
from app.services.knowledge_base_service import KnowledgeBaseManager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Container:
    """依赖注入容器"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._initialized = False
    
    def register_singleton(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """注册单例服务"""
        key = service_type.__name__
        self._factories[key] = factory
        logger.debug(f"注册单例服务: {key}")
    
    def register_transient(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """注册瞬态服务（每次调用都创建新实例）"""
        key = service_type.__name__
        self._services[key] = factory
        logger.debug(f"注册瞬态服务: {key}")
    
    def get(self, service_type: Type[T]) -> T:
        """获取服务实例"""
        key = service_type.__name__
        
        # 检查单例缓存
        if key in self._singletons:
            return self._singletons[key]
        
        # 检查单例工厂
        if key in self._factories:
            instance = self._factories[key]()
            self._singletons[key] = instance
            return instance
        
        # 检查瞬态服务
        if key in self._services:
            return self._services[key]()
        
        raise ValueError(f"服务未注册: {service_type.__name__}")
    
    def initialize(self) -> None:
        """初始化容器，注册所有服务"""
        if self._initialized:
            return
        
        # 注册配置服务
        self.register_singleton(type(get_settings()), get_settings)
        
        # 注册业务服务
        self.register_singleton(AgentService, lambda: AgentService())
        self.register_singleton(KnowledgeBaseManager, lambda: KnowledgeBaseManager())
        
        self._initialized = True
        logger.info("依赖注入容器初始化完成")
    
    def clear(self) -> None:
        """清除所有服务实例"""
        self._singletons.clear()
        logger.info("清除所有服务实例")


# 全局容器实例
_container: Optional[Container] = None


def get_container() -> Container:
    """获取全局容器实例"""
    global _container
    if _container is None:
        _container = Container()
        _container.initialize()
    return _container


@lru_cache()
def get_agent_service() -> AgentService:
    """获取Agent服务实例"""
    return get_container().get(AgentService)


@lru_cache()
def get_knowledge_base_manager() -> KnowledgeBaseManager:
    """获取知识库管理器实例"""
    return get_container().get(KnowledgeBaseManager)