"""
PDF文献分析智能体服务主入口
整合了重构后的架构和原有功能
"""
# 禁用 ChromaDB 遥测功能，避免遥测错误
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from contextlib import asynccontextmanager

# 原有模块
from app.database import create_tables
from app.logging_config import setup_logging, RequestLoggingMiddleware
from app.services.document_service import document_task_processor
from app.routers import document_router, query_router, system_router, knowledge_base_router, conversation_router

# 新架构模块
from app.config.settings import get_settings
from app.core.container import get_container
from app.middleware.error_handling import ErrorHandlingMiddleware
from app.api.exception_handlers import register_exception_handlers
from app.routers import agent_router
from app.api import health

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 定义lifespan上下文管理器，整合新旧架构
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行的代码
    logger.info("🚀 PDF文献分析智能体服务启动")
    
    # 初始化新架构的依赖注入容器
    logger.info("正在初始化依赖注入容器...")
    container = get_container()
    logger.info("✅ 依赖注入容器初始化完成")
    
    # 初始化数据库（原有功能）
    logger.info("正在初始化数据库...")
    create_tables()
    logger.info("✅ 数据库初始化完成")
    
    # 启动文档处理轮询（原有功能）
    logger.info("正在启动文档处理服务...")
    task = asyncio.create_task(document_task_processor.start_polling())
    logger.info("✅ 文档处理服务启动完成")
    
    logger.info("🎉 所有服务启动完成")
    
    yield  # 应用运行期间
    
    # 关闭时执行的代码
    logger.info("🛑 PDF文献分析智能体服务关闭中...")
    
    # 停止文档处理轮询
    document_task_processor.stop_polling()
    logger.info("✅ 文档处理服务已停止")
    
    # 清理依赖注入容器
    container.clear()
    logger.info("✅ 依赖注入容器已清理")
    
    logger.info("👋 PDF文献分析智能体服务已关闭")

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="基于大语言模型的智能文档分析服务，支持PDF、TXT、DOC、DOCX文件",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.debug
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加新架构的错误处理中间件
app.add_middleware(ErrorHandlingMiddleware)

# 添加原有的请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 注册新架构的异常处理器
register_exception_handlers(app)

# 创建数据库表（保留原有功能）
create_tables()

# 注册路由 - 原有路由
app.include_router(document_router, prefix="/api/v1", tags=["文档管理"])
app.include_router(query_router, prefix="/api/v1", tags=["文档查询"])
app.include_router(system_router, prefix="/api/v1", tags=["系统信息"])
app.include_router(knowledge_base_router, prefix="/api/v1", tags=["知识库管理"])
app.include_router(conversation_router, prefix="/api/v1", tags=["对话管理"])

# 注册路由 - 新架构路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(agent_router, prefix="/api/v1", tags=["智能Agent"])

# 注册测试路由
from app.routers import test_routes
app.include_router(test_routes.router, tags=["测试接口"])

# 添加根路径处理
@app.get("/", tags=["Root"])
async def root():
    """根路径，返回API基本信息"""
    return {
        "message": f"欢迎使用 {settings.app_name}",
        "version": settings.version,
        "description": "基于大语言模型的PDF文献智能分析服务",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "PDF文档上传与解析",
            "智能文档问答",
            "知识库管理",
            "Agent智能对话",
            "文档摘要生成"
        ]
    }

# 移除废弃的on_event装饰器
# @app.on_event("startup")
# async def startup_event():
#     """应用启动时的初始化操作"""
#     logger.info("PDF文献分析智能体服务启动")
#     logger.info("正在初始化数据库...")
#     create_tables()
#     
#     # 启动文档处理轮询
#     asyncio.create_task(document_task_processor.start_polling())
# 
# @app.on_event("shutdown")
# async def shutdown_event():
#     """应用关闭时的清理操作"""
#     document_task_processor.stop_polling()
#     logger.info("PDF文献分析智能体服务已关闭") 