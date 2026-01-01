from celery import Celery
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.getenv("ENV_FILE", ".env"))

def make_celery():
    # 获取Redis配置
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_password = os.getenv("REDIS_PASSWORD", "")
    redis_db = os.getenv("REDIS_DB", "0")
    
    # 构建Redis URL
    if redis_password:
        broker_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        result_backend = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        broker_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        result_backend = f"redis://{redis_host}:{redis_port}/{redis_db}"
    
    # 创建Celery实例，名为 'llama_doc'
    celery_app = Celery(
        "llama_doc",
        broker=broker_url,
        backend=result_backend,
        include=["app.tasks.document_tasks"]  # 预加载任务模块
    )
    
    # 配置Celery
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Shanghai",
        enable_utc=True,
        # 任务过期时间（可选）
        result_expires=3600,
        # 并发配置，默认是CPU核心数，可根据需要调整
        worker_concurrency=os.getenv("CELERY_WORKER_CONCURRENCY", 4),
        # 每个worker执行多少任务后销毁（防止内存泄漏）
        worker_max_tasks_per_child=100,
        # 任务确认机制
        task_acks_late=True,
    )
    
    return celery_app

celery_app = make_celery()
