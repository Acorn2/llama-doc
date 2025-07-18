"""
日志配置模块
"""

import os
import logging
import logging.handlers
from typing import Dict, Any
from pathlib import Path

from app.config.settings import get_settings


def setup_logging() -> None:
    """设置应用日志配置"""
    settings = get_settings()
    
    # 创建日志目录
    log_dir = Path(settings.logging.file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志配置
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": settings.logging.format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.logging.level,
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.logging.level,
                "formatter": "detailed",
                "filename": settings.logging.file_path,
                "maxBytes": settings.logging.max_file_size,
                "backupCount": settings.logging.backup_count,
                "encoding": "utf-8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(log_dir / "error.log"),
                "maxBytes": settings.logging.max_file_size,
                "backupCount": settings.logging.backup_count,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            # 应用日志
            "app": {
                "level": settings.logging.level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            # FastAPI日志
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            # LangChain日志
            "langchain": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False
            },
            # 第三方库日志
            "httpx": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "urllib3": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": settings.logging.level,
            "handlers": ["console", "file", "error_file"]
        }
    }
    
    # 应用日志配置
    logging.config.dictConfig(logging_config)
    
    # 设置应用日志记录器
    logger = logging.getLogger("app")
    logger.info(f"日志系统初始化完成 - 级别: {settings.logging.level}")
    logger.info(f"日志文件: {settings.logging.file_path}")


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(f"app.{name}")


# 在模块导入时自动设置日志
try:
    setup_logging()
except Exception as e:
    # 如果日志设置失败，使用基本配置
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.getLogger("app").error(f"日志配置失败，使用基本配置: {e}")