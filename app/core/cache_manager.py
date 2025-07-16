import json
import hashlib
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class CacheManager:
    """简化的缓存管理器 - 只使用内存缓存"""
    
    def __init__(self):
        self.memory_cache = {}
        self.memory_cache_maxsize = 1000
        self.cache_timestamps = {}  # 存储缓存时间戳
        
        logger.info("缓存管理器初始化完成（内存缓存模式）")
    
    def _generate_key(self, prefix: str, data: str) -> str:
        """生成缓存键"""
        hash_value = hashlib.md5(data.encode('utf-8')).hexdigest()
        return f"{prefix}:{hash_value}"
    
    def _is_expired(self, key: str, expire: int) -> bool:
        """检查缓存是否过期"""
        if key not in self.cache_timestamps:
            return True
        
        cache_time = self.cache_timestamps[key]
        return (datetime.now() - cache_time).total_seconds() > expire
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"缓存获取失败: {e}")
        return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存值"""
        try:
            # 内存缓存简单LRU实现
            if len(self.memory_cache) >= self.memory_cache_maxsize:
                # 删除最旧的项
                oldest_key = next(iter(self.memory_cache))
                del self.memory_cache[oldest_key]
                if oldest_key in self.cache_timestamps:
                    del self.cache_timestamps[oldest_key]
            
            self.memory_cache[key] = value
            self.cache_timestamps[key] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"缓存设置失败: {e}")
        return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]
            return True
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
        return False
    
    def clear_expired(self):
        """清理过期缓存"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, timestamp in self.cache_timestamps.items():
                if (current_time - timestamp).total_seconds() > 3600:  # 默认1小时过期
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)
                
            if expired_keys:
                logger.info(f"清理了 {len(expired_keys)} 个过期缓存")
                
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
    
    def search_cache_key(self, document_id: str, query: str, k: int) -> str:
        """生成搜索缓存键"""
        cache_data = f"{document_id}:{query}:{k}"
        return self._generate_key("search", cache_data)
    
    def summary_cache_key(self, document_id: str) -> str:
        """生成摘要缓存键"""
        return self._generate_key("summary", document_id)

# 全局缓存实例
cache_manager = CacheManager() 