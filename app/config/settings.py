"""
应用配置管理
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    username: str = Field(default="postgres", env="DB_USERNAME")
    password: str = Field(default="", env="DB_PASSWORD")
    database: str = Field(default="knowledge_base", env="DB_DATABASE")
    
    @property
    def url(self) -> str:
        """获取数据库连接URL"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    class Config:
        env_prefix = "DB_"


class QdrantSettings(BaseSettings):
    """Qdrant向量数据库配置"""
    
    host: str = Field(default="localhost", env="QDRANT_HOST")
    port: int = Field(default=6333, env="QDRANT_PORT")
    api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    collection_name: str = Field(default="documents", env="QDRANT_COLLECTION")
    
    @property
    def url(self) -> str:
        """获取Qdrant连接URL"""
        return f"http://{self.host}:{self.port}"
    
    class Config:
        env_prefix = "QDRANT_"


class LLMSettings(BaseSettings):
    """大语言模型配置"""
    
    # 通义千问配置
    qwen_api_key: Optional[str] = Field(default=None, env="QWEN_API_KEY")
    qwen_model: str = Field(default="qwen-turbo", env="QWEN_MODEL")
    
    # OpenAI配置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    
    # 默认LLM类型
    default_llm_type: str = Field(default="qwen", env="DEFAULT_LLM_TYPE")
    
    # 模型参数
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=2000, env="LLM_MAX_TOKENS")
    
    class Config:
        env_prefix = "LLM_"


class AgentSettings(BaseSettings):
    """Agent配置"""
    
    # 缓存配置
    enable_cache: bool = Field(default=True, env="AGENT_ENABLE_CACHE")
    cache_ttl: int = Field(default=3600, env="AGENT_CACHE_TTL")  # 秒
    max_cache_size: int = Field(default=100, env="AGENT_MAX_CACHE_SIZE")
    
    # 对话配置
    enable_memory: bool = Field(default=True, env="AGENT_ENABLE_MEMORY")
    max_memory_length: int = Field(default=20, env="AGENT_MAX_MEMORY_LENGTH")
    
    # Agent执行配置
    max_iterations: int = Field(default=5, env="AGENT_MAX_ITERATIONS")
    timeout: int = Field(default=60, env="AGENT_TIMEOUT")  # 秒
    
    class Config:
        env_prefix = "AGENT_"


class StorageSettings(BaseSettings):
    """存储配置"""
    
    # 本地存储
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_extensions: List[str] = Field(
        default=["pdf", "txt", "docx", "md"],
        env="ALLOWED_EXTENSIONS"
    )
    
    # 腾讯云COS配置
    cos_secret_id: Optional[str] = Field(default=None, env="COS_SECRET_ID")
    cos_secret_key: Optional[str] = Field(default=None, env="COS_SECRET_KEY")
    cos_region: str = Field(default="ap-beijing", env="COS_REGION")
    cos_bucket: Optional[str] = Field(default=None, env="COS_BUCKET")
    
    class Config:
        env_prefix = "STORAGE_"


class LoggingSettings(BaseSettings):
    """日志配置"""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    file_path: str = Field(default="logs/app.log", env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10 * 1024 * 1024, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_prefix = "LOG_"


class AppSettings(BaseSettings):
    """应用主配置"""
    
    # 应用基本信息
    app_name: str = Field(default="Knowledge Base API", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # API配置
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # 安全配置
    secret_key: str = Field(default="your-secret-key", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 子配置
    database: DatabaseSettings = DatabaseSettings()
    qdrant: QdrantSettings = QdrantSettings()
    llm: LLMSettings = LLMSettings()
    agent: AgentSettings = AgentSettings()
    storage: StorageSettings = StorageSettings()
    logging: LoggingSettings = LoggingSettings()
    
    class Config:
        env_file = [".env", ".env.development", ".env.production"]
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量


# 全局配置实例
settings = AppSettings()


def get_settings() -> AppSettings:
    """获取应用配置"""
    return settings