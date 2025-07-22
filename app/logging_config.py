import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_dir: str = "./logs"):
    """配置应用日志系统"""
    
    # 创建日志目录
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 设置日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建格式化器
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 控制台错误格式化器 - 使错误日志在控制台更加突出
    console_error_formatter = logging.Formatter(
        '\033[31m%(asctime)s - ERROR - %(message)s\033[0m'  # 红色文本
    )
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器 - 处理所有级别的日志，包括错误
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    # 使用过滤器确保所有日志都显示在控制台上
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # 控制台错误处理器 - 专门处理ERROR级别及以上日志
    console_error_handler = logging.StreamHandler(sys.stderr)
    console_error_handler.setLevel(logging.ERROR)
    console_error_handler.setFormatter(console_error_formatter)
    root_logger.addHandler(console_error_handler)
    
    # 应用日志文件处理器（按时间轮转）
    app_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_file_handler)
    
    # API访问日志处理器
    api_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "api.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    api_file_handler.setLevel(logging.INFO)
    api_file_handler.setFormatter(detailed_formatter)
    
    # 为特定日志器配置
    api_logger = logging.getLogger("api")
    api_logger.addHandler(api_file_handler)
    api_logger.setLevel(logging.INFO)
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    # 确保核心模块日志级别正确设置
    logging.getLogger("app.core").setLevel(numeric_level)
    logging.getLogger("app.services").setLevel(numeric_level)
    logging.getLogger("app.utils").setLevel(numeric_level)
    
    # 专门设置文档处理器日志级别，确保能够输出到控制台
    document_processor_logger = logging.getLogger("app.core.document_processor")
    document_processor_logger.setLevel(logging.DEBUG)  # 使用更详细的DEBUG级别

       # 为document_service模块添加专用日志配置
    document_service_logger = logging.getLogger("app.services.document_service")
    document_service_logger.setLevel(logging.DEBUG)
    
    # 添加专用的控制台处理器，确保文档处理器日志输出到控制台
    doc_console_handler = logging.StreamHandler(sys.stdout)
    doc_console_handler.setLevel(logging.DEBUG)
    doc_console_handler.setFormatter(detailed_formatter)
    document_processor_logger.addHandler(doc_console_handler)
    
    return root_logger

def get_api_logger():
    """获取API专用日志器"""
    return logging.getLogger("api")

class RequestLoggingMiddleware:
    """请求日志中间件"""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_api_logger()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = datetime.now()
            
            # 记录请求开始
            self.logger.info(
                f"请求开始 - {scope['method']} {scope['path']} "
                f"来自 {scope.get('client', ['unknown'])[0]}"
            )
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    # 记录响应状态
                    duration = (datetime.now() - start_time).total_seconds()
                    self.logger.info(
                        f"请求完成 - {scope['method']} {scope['path']} "
                        f"状态: {message['status']} 耗时: {duration:.3f}s"
                    )
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send) 