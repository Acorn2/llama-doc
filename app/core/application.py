"""
应用工厂
集中管理应用的创建和配置
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.core.container import get_container
from app.middleware.error_handling import ErrorHandlingMiddleware
from app.api.exception_handlers import register_exception_handlers
from app.routers import agent_router
from app.api import health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 应用启动中...")
    
    # 初始化依赖注入容器
    container = get_container()
    logger.info("✅ 依赖注入容器初始化完成")
    
    # 这里可以添加其他启动时的初始化逻辑
    # 比如数据库连接、缓存预热等
    
    logger.info("🎉 应用启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("🛑 应用关闭中...")
    
    # 清理资源
    container.clear()
    logger.info("✅ 资源清理完成")
    
    logger.info("👋 应用已关闭")


def create_application() -> FastAPI:
    """
    创建FastAPI应用实例
    
    Returns:
        FastAPI: 配置完成的应用实例
    """
    settings = get_settings()
    
    # 创建FastAPI应用
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="基于LangChain的智能知识库API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        debug=settings.debug
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加错误处理中间件
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 注册异常处理器
    register_exception_handlers(app)
    
    # 注册路由
    app.include_router(health.router)
    app.include_router(agent_router.router, prefix=settings.api_prefix)
    
    # 添加根路径处理
    @app.get("/", tags=["Root"])
    async def root():
        """根路径，返回API基本信息"""
        return {
            "message": f"欢迎使用 {settings.app_name}",
            "version": settings.version,
            "docs": "/docs",
            "health": "/health"
        }
    
    logger.info(f"✅ FastAPI应用创建完成: {settings.app_name} v{settings.version}")
    
    return app


# 创建应用实例
app = create_application()