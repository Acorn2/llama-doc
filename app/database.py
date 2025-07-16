from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float, text, Index, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.pool import QueuePool, StaticPool
import os
from dotenv import load_dotenv
import time
import logging

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

def get_database_config():
    """根据环境变量获取数据库配置"""
    
    # 获取环境类型
    environment = os.getenv("ENVIRONMENT", "development")
    
    # 基础数据库配置
    database_url = os.getenv("DATABASE_URL")
    
    # 从数据库URL判断数据库类型
    if database_url:
        if database_url.startswith("sqlite"):
            db_type = "sqlite"
        elif database_url.startswith("postgresql"):
            db_type = "postgresql"
        else:
            raise ValueError(f"不支持的数据库URL: {database_url}")
    else:
        # 如果没有DATABASE_URL，根据DB_TYPE构建
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "sqlite":
            db_name = os.getenv("DB_NAME", "document_analysis.db")
            database_url = f"sqlite:///./{db_name}"
        elif db_type == "postgresql":
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            user = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "postgres")
            db_name = os.getenv("DB_NAME", "document_analysis")
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    # 根据数据库类型配置连接池
    if db_type == "sqlite":
        pool_config = {
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 30
            },
            "pool_pre_ping": True,
            "pool_recycle": -1  # SQLite不需要连接回收
        }
        logger.info(f"配置SQLite数据库: {database_url}")
        
    elif db_type == "postgresql":
        pool_config = {
            "poolclass": QueuePool,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            "connect_args": {
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000"
            }
        }
        # 隐藏密码信息
        safe_url = database_url.split('@')[0] + "@***" if '@' in database_url else database_url
        logger.info(f"配置PostgreSQL数据库: {safe_url}")
    
    return database_url, pool_config, db_type

# 获取数据库配置
DATABASE_URL, POOL_CONFIG, DB_TYPE = get_database_config()

# 创建数据库引擎
engine = create_engine(DATABASE_URL, **POOL_CONFIG)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

class Document(Base):
    """文档数据模型"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # 本地路径（向后兼容）
    file_size = Column(Integer, nullable=False)
    file_md5 = Column(String, nullable=False, index=True)
    pages = Column(Integer, default=0)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")
    chunk_count = Column(Integer, default=0)
    
    # 腾讯云COS相关字段
    cos_object_key = Column(String, nullable=True)  # COS对象键
    cos_file_url = Column(String, nullable=True)    # COS文件URL
    cos_etag = Column(String, nullable=True)        # COS ETag
    storage_type = Column(String, default="local")  # 存储类型：local/cos
    
    # 处理时间字段
    process_start_time = Column(DateTime(timezone=True), nullable=True)
    process_end_time = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 重试相关字段
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_retry_time = Column(DateTime(timezone=True), nullable=True)
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_file_md5_status', 'file_md5', 'status'),
            Index('idx_status_upload_time', 'status', 'upload_time'),
            Index('idx_status_retry', 'status', 'retry_count'),
            Index('idx_cos_object_key', 'cos_object_key'),  # 新增COS对象键索引
            Index('idx_storage_type', 'storage_type'),      # 新增存储类型索引
        )
    # SQLite 的索引会在数据库创建时自动处理

class QueryHistory(Base):
    """查询历史记录模型"""
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    processing_time = Column(Float, default=0.0)
    query_time = Column(DateTime(timezone=True), server_default=func.now())

def get_db_session():
    """获取数据库会话，带重试机制"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            
            # 根据数据库类型进行不同的连接测试
            if DB_TYPE == "sqlite":
                # SQLite简单测试
                db.execute(text("SELECT 1"))
            elif DB_TYPE == "postgresql":
                # PostgreSQL更详细的测试
                db.execute(text("SELECT version()"))
            
            logger.debug(f"数据库连接成功 (类型: {DB_TYPE})")
            return db
            
        except Exception as e:
            if db:
                db.close()
            if attempt < max_retries - 1:
                logger.warning(f"数据库连接失败，重试 {attempt + 1}/{max_retries}: {e}")
                time.sleep(1)
                continue
            else:
                logger.error(f"数据库连接失败，已达最大重试次数: {e}")
                raise

# 添加别名以兼容现有代码
get_db = get_db_session

def create_tables():
    """创建数据库表"""
    try:
        logger.info(f"开始创建数据库表 (数据库类型: {DB_TYPE}, URL: {DATABASE_URL})")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
        
        # 测试数据库连接
        test_db = get_db_session()
        test_db.close()
        logger.info("数据库连接测试成功")
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        logger.error(f"数据库配置 - 类型: {DB_TYPE}, URL: {DATABASE_URL}")
        logger.error(f"连接池配置: {POOL_CONFIG}")
        raise

def check_tables_exist():
    """检查数据库表是否已存在"""
    try:
        inspector = inspect(engine)
        
        # 检查核心表是否存在
        required_tables = ["documents", "query_history"]
        existing_tables = [table for table in required_tables if inspector.has_table(table)]
        
        # 如果所有必需的表都存在，则返回True
        tables_exist = len(existing_tables) == len(required_tables)
        
        if tables_exist:
            logger.info("数据库表检查: 所有必需的表都已存在")
        else:
            missing_tables = set(required_tables) - set(existing_tables)
            logger.info(f"数据库表检查: 缺少以下表: {', '.join(missing_tables)}")
        
        return tables_exist
    except Exception as e:
        logger.error(f"检查数据库表失败: {e}")
        # 出错时返回False，让程序尝试创建表
        return False

def get_db_info():
    """获取数据库信息"""
    safe_url = DATABASE_URL
    if '@' in DATABASE_URL:
        safe_url = DATABASE_URL.split('://')[0] + "://***"
    
    return {
        "database_type": DB_TYPE,
        "database_url": safe_url,
        "pool_size": POOL_CONFIG.get("pool_size", "N/A"),
        "max_overflow": POOL_CONFIG.get("max_overflow", "N/A"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# 在模块加载时记录数据库配置信息
logger.info(f"数据库配置完成: {get_db_info()}") 