"""
API路由模块
"""
from app.routers.document_routes import router as document_router
from app.routers.query_routes import router as query_router
from app.routers.system_routes import router as system_router
from app.routers.llamaindex_routes import router as llamaindex_router

__all__ = [
    "document_router",
    "query_router", 
    "system_router",
    "llamaindex_router"
] 