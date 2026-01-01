from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float, text, Index, inspect, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
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

class User(Base):
    """用户数据模型"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=True, index=True)  # 用户名，可选
    email = Column(String, nullable=True, unique=True, index=True)  # 邮箱，唯一
    phone = Column(String, nullable=True, unique=True, index=True)  # 手机号，唯一
    password_hash = Column(String, nullable=False)  # 密码哈希
    full_name = Column(String, nullable=True)  # 全名
    avatar_url = Column(String, nullable=True)  # 头像URL
    is_active = Column(Boolean, default=True)  # 是否激活
    is_superuser = Column(Boolean, default=False)  # 是否超级用户
    
    # 时间字段
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_time = Column(DateTime(timezone=True), nullable=True)
    
    # 用户设置
    preferences = Column(Text, nullable=True)  # JSON格式的用户偏好设置
    
    # 建立关系
    knowledge_bases = relationship("KnowledgeBase", back_populates="user")
    documents = relationship("Document", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_user_email', 'email'),
            Index('idx_user_phone', 'phone'),
            Index('idx_user_active', 'is_active'),
            Index('idx_user_create_time', 'create_time'),
        )

class Document(Base):
    """文档数据模型"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # 关联用户
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # 本地路径（向后兼容）
    file_size = Column(Integer, nullable=False)
    file_md5 = Column(String, nullable=False, index=True)
    pages = Column(Integer, default=0)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")
    chunk_count = Column(Integer, default=0)
    file_type = Column(String, nullable=True)  # 文件类型：pdf, txt, doc, docx 等
    
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
    
    # 同步状态字段：用于知识库向量同步
    # available(可同步), syncing(同步中), synced(已同步), sync_failed(同步失败)
    sync_status = Column(String, default="available", nullable=False)
    
    # 建立关系
    user = relationship("User", back_populates="documents")
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_file_md5_status', 'file_md5', 'status'),
            Index('idx_status_upload_time', 'status', 'upload_time'),
            Index('idx_status_retry', 'status', 'retry_count'),
            Index('idx_cos_object_key', 'cos_object_key'),  # 新增COS对象键索引
            Index('idx_sync_status', 'sync_status'),  # 同步状态索引
            Index('idx_status_sync_status', 'status', 'sync_status'),  # 复合索引
            Index('idx_storage_type', 'storage_type'),      # 新增存储类型索引
            Index('idx_file_type', 'file_type'),           # 新增文件类型索引
            Index('idx_user_upload_time', 'user_id', 'upload_time'),  # 用户文档索引
        )
    # SQLite 的索引会在数据库创建时自动处理

class QueryHistory(Base):
    """查询历史记录模型"""
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # 关联用户
    document_id = Column(String, nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    processing_time = Column(Float, default=0.0)
    query_time = Column(DateTime(timezone=True), server_default=func.now())

class KnowledgeBase(Base):
    """知识库数据模型"""
    __tablename__ = "knowledge_bases"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # 关联用户
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    vector_store_name = Column(String, nullable=False)  # 对应向量库名称
    document_count = Column(Integer, default=0)         # 包含的文档数量
    status = Column(String, default="active")           # active, archived, deleted
    
    # 公开访问相关字段
    is_public = Column(Boolean, default=False)          # 是否公开
    public_description = Column(Text, nullable=True)    # 公开描述（可与private description不同）
    tags = Column(String, nullable=True)                # 标签，用于分类和搜索，JSON格式存储
    view_count = Column(Integer, default=0)             # 浏览次数
    like_count = Column(Integer, default=0)             # 点赞次数
    
    # 建立关系
    user = relationship("User", back_populates="knowledge_bases")
    conversations = relationship("Conversation", back_populates="knowledge_base")
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_kb_status', 'status'),
            Index('idx_kb_create_time', 'create_time'),
            Index('idx_kb_user', 'user_id', 'status'),  # 用户知识库索引
            Index('idx_kb_public', 'is_public', 'status'),  # 公开知识库索引
            Index('idx_kb_public_create_time', 'is_public', 'create_time'),  # 公开知识库时间索引
        )

class KnowledgeBaseDocument(Base):
    """知识库文档关联模型"""
    __tablename__ = "kb_documents"
    
    id = Column(String, primary_key=True, index=True)
    kb_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    add_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # 向量同步状态：pending(待同步), syncing(同步中), completed(已完成), failed(失败)
    vector_sync_status = Column(String, default="pending", nullable=False)
    vector_sync_time = Column(DateTime(timezone=True), nullable=True)
    vector_sync_error = Column(Text, nullable=True)
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_kb_doc', 'kb_id', 'document_id'),
            Index('idx_vector_sync_status', 'vector_sync_status'),
        )

class KnowledgeBaseAccess(Base):
    """知识库访问记录模型"""
    __tablename__ = "kb_access"
    
    id = Column(String, primary_key=True, index=True)
    kb_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    access_type = Column(String, nullable=False)  # view, chat, like, unlike
    access_time = Column(DateTime(timezone=True), server_default=func.now())
    access_metadata = Column(Text, nullable=True)  # JSON格式，存储额外信息
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_kb_access_kb_user', 'kb_id', 'user_id'),
            Index('idx_kb_access_time', 'access_time'),
            Index('idx_kb_access_type', 'access_type'),
        )

class KnowledgeBaseLike(Base):
    """知识库点赞记录模型"""
    __tablename__ = "kb_likes"
    
    id = Column(String, primary_key=True, index=True)
    kb_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_kb_like_unique', 'kb_id', 'user_id', unique=True),  # 确保用户对同一知识库只能点赞一次
        )

class Conversation(Base):
    """对话数据模型"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # 关联用户
    kb_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String, default="active")  # active, archived, deleted
    
    # 建立关系
    user = relationship("User", back_populates="conversations")
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_conv_kb_id', 'kb_id'),
            Index('idx_conv_status', 'status'),
            Index('idx_conv_create_time', 'create_time'),
            Index('idx_conv_user', 'user_id', 'status'),  # 用户对话索引
        )

class Message(Base):
    """对话消息数据模型"""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sequence_number = Column(Integer, nullable=False, default=0)  # 消息在对话中的序号
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    message_metadata = Column(Text, nullable=True)  # JSON格式的元数据，包括使用的工具、引用等
    
    # 建立关系
    conversation = relationship("Conversation", back_populates="messages")
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_msg_conversation_id', 'conversation_id'),
            Index('idx_msg_role', 'role'),
            Index('idx_msg_create_time', 'create_time'),
            Index('idx_conversation_sequence', 'conversation_id', 'sequence_number'),  # 新增复合索引
        )

class UserActivity(Base):
    """用户活动记录数据模型"""
    __tablename__ = "user_activities"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    activity_type = Column(String, nullable=False, index=True)  # 活动类型
    activity_description = Column(String, nullable=False)  # 活动描述
    resource_type = Column(String, nullable=True, index=True)  # 资源类型：document, knowledge_base, conversation等
    resource_id = Column(String, nullable=True, index=True)  # 资源ID
    activity_metadata = Column(Text, nullable=True)  # JSON格式的活动元数据
    ip_address = Column(String, nullable=True)  # IP地址
    user_agent = Column(String, nullable=True)  # 用户代理
    create_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 建立关系
    user = relationship("User")
    
    # 根据数据库类型添加索引
    if DB_TYPE == "postgresql":
        __table_args__ = (
            Index('idx_activity_user_time', 'user_id', 'create_time'),  # 用户活动时间索引
            Index('idx_activity_type_time', 'activity_type', 'create_time'),  # 活动类型时间索引
            Index('idx_activity_resource', 'resource_type', 'resource_id'),  # 资源索引
        )

def get_db():
    """获取数据库会话，用于FastAPI依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_test_db():
    """获取测试数据库连接，带重试机制（用于启动检查）"""
    max_retries = 3
    db = None
    
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

def create_tables():
    """创建数据库表，仅在表不存在时创建"""
    try:
        # 首先检查表是否已存在
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = [
            "users", "documents", "query_history", "knowledge_bases", 
            "kb_documents", "kb_access", "kb_likes", "conversations", "messages", "user_activities"
        ]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if not missing_tables:
            logger.info("数据库表检查: 所有必需的表都已存在，跳过创建")
            return
        
        logger.info(f"开始创建缺失的数据库表: {missing_tables} (数据库类型: {DB_TYPE})")
        
        # 只创建缺失的表
        try:
            # 创建所有表，SQLAlchemy会自动跳过已存在的表
            Base.metadata.create_all(bind=engine, checkfirst=True)
            logger.info("数据库表创建/检查完成")
        except Exception as create_error:
            logger.warning(f"创建表时出现错误，但可能是因为表已存在: {create_error}")
            # 再次检查表是否真的创建成功了
            inspector = inspect(engine)
            current_tables = inspector.get_table_names()
            still_missing = [table for table in required_tables if table not in current_tables]
            if still_missing:
                logger.error(f"以下表仍然缺失: {still_missing}")
                raise Exception(f"无法创建必需的表: {still_missing}")
            else:
                logger.info("所有必需的表都已存在（可能是之前创建的）")
        
        # 测试数据库连接
        test_db = get_test_db()
        if test_db:
            test_db.close()
        logger.info("数据库连接测试成功")
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        logger.error(f"数据库配置 - 类型: {DB_TYPE}, URL: {DATABASE_URL}")
        logger.error(f"连接池配置: {POOL_CONFIG}")
        # 不要抛出异常，让应用继续运行
        logger.warning("数据库表创建失败，但应用将尝试继续运行")

def check_tables_exist():
    """检查数据库表是否已存在"""
    try:
        inspector = inspect(engine)
        
        # 检查核心表是否存在，增加用户表和新的公开知识库相关表
        required_tables = [
            "users", "documents", "query_history", "knowledge_bases", 
            "kb_documents", "kb_access", "kb_likes", "conversations", "messages", "user_activities"
        ]
        existing_tables = [table for table in required_tables if inspector.has_table(table)]
        
        # 如果所有必需的表都存在，则返回True
        tables_exist = len(existing_tables) == len(required_tables)
        
        if tables_exist:
            logger.info("数据库表检查: 所有必需的表都已存在")
        else:
            missing_tables = set(required_tables) - set(existing_tables)
            logger.warning(f"数据库表检查: 缺少以下表: {', '.join(missing_tables)}")
            logger.info(f"数据库表检查: 已存在的表: {', '.join(existing_tables) if existing_tables else '无'}")
        
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