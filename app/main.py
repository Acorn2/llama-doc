"""
PDF文献分析智能体服务主入口
"""
# 禁用 ChromaDB 遥测功能，避免遥测错误
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from app.database import create_tables
from app.logging_config import setup_logging, RequestLoggingMiddleware
from app.services.document_service import document_task_processor
from app.routers import document_router, query_router, system_router, llamaindex_router

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="PDF文献分析智能体",
    description="基于大语言模型的PDF文献智能分析服务",
    version="1.0.0",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 创建数据库表
create_tables()

# 注册路由
app.include_router(document_router, prefix="/api/v1", tags=["文档管理"])
app.include_router(query_router, prefix="/api/v1", tags=["文档查询"])
app.include_router(system_router, prefix="/api/v1", tags=["系统信息"])
app.include_router(llamaindex_router, prefix="/api/v1/llamaindex", tags=["LlamaIndex"])

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化操作"""
    logger.info("PDF文献分析智能体服务启动")
    logger.info("正在初始化数据库...")
    create_tables()
    
    # 启动文档处理轮询
    asyncio.create_task(document_task_processor.start_polling())

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理操作"""
    document_task_processor.stop_polling()
    logger.info("PDF文献分析智能体服务已关闭") 