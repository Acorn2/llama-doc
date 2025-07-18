"""
API路由模块
"""
from app.routers.document_routes import router as document_router
from app.routers.query_routes import router as query_router
from app.routers.system_routes import router as system_router
from app.routers.knowledge_base_routes import router as knowledge_base_router
from app.routers.conversation_routes import router as conversation_router
from app.routers.agent_router import router as agent_router

__all__ = [
    "document_router",
    "query_router", 
    "system_router",
    "knowledge_base_router",
    "conversation_router",
    "agent_router"
] 