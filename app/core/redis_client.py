"""
Redis连接管理器
"""
import redis
import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class RedisClient:
    """Redis客户端管理器"""
    
    def __init__(self):
        self.client = None
        self.enabled = os.getenv("USE_REDIS", "false").lower() == "true"
        self.key_prefix = os.getenv("REDIS_KEY_PREFIX", "llama")
        
        if self.enabled:
            self._connect()
    
    def _get_prefixed_key(self, key: str) -> str:
        """获取带前缀的key"""
        if key.startswith(f"{self.key_prefix}:"):
            return key
        return f"{self.key_prefix}:{key}"
    
    def _connect(self):
        """连接Redis"""
        try:
            # 从环境变量获取Redis配置
            redis_config = {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', 6379)),
                'db': int(os.getenv('REDIS_DB', 0)),
                'decode_responses': True,
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
                'retry_on_timeout': True,
                'health_check_interval': 30
            }
            
            # 如果有密码，添加密码
            password = os.getenv('REDIS_PASSWORD')
            if password:
                redis_config['password'] = password
            
            # 如果启用TLS
            tls_enabled = os.getenv('REDIS_TLS', 'false').lower() == 'true'
            if tls_enabled:
                redis_config['ssl'] = True
                redis_config['ssl_cert_reqs'] = None
            
            self.client = redis.Redis(**redis_config)
            
            # 测试连接
            self.client.ping()
            logger.info(f"Redis连接成功: {redis_config['host']}:{redis_config['port']}, 前缀: {self.key_prefix}")
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.client = None
            self.enabled = False
    
    def is_available(self) -> bool:
        """检查Redis是否可用"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except Exception:
            return False
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置缓存"""
        if not self.is_available():
            return False
        
        try:
            # 添加前缀
            prefixed_key = self._get_prefixed_key(key)
            
            # 如果值是字典或列表，序列化为JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            if expire:
                return self.client.setex(prefixed_key, expire, value)
            else:
                return self.client.set(prefixed_key, value)
        except Exception as e:
            logger.error(f"Redis设置失败: {key}, {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.is_available():
            return None
        
        try:
            # 添加前缀
            prefixed_key = self._get_prefixed_key(key)
            
            value = self.client.get(prefixed_key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis获取失败: {key}, {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_available():
            return False
        
        try:
            # 添加前缀
            prefixed_key = self._get_prefixed_key(key)
            return bool(self.client.delete(prefixed_key))
        except Exception as e:
            logger.error(f"Redis删除失败: {key}, {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.is_available():
            return False
        
        try:
            # 添加前缀
            prefixed_key = self._get_prefixed_key(key)
            return bool(self.client.exists(prefixed_key))
        except Exception as e:
            logger.error(f"Redis检查存在失败: {key}, {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if not self.is_available():
            return False
        
        try:
            # 添加前缀
            prefixed_key = self._get_prefixed_key(key)
            return bool(self.client.expire(prefixed_key, seconds))
        except Exception as e:
            logger.error(f"Redis设置过期时间失败: {key}, {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self.is_available():
            return -1
        
        try:
            # 添加前缀
            prefixed_key = self._get_prefixed_key(key)
            return self.client.ttl(prefixed_key)
        except Exception as e:
            logger.error(f"Redis获取TTL失败: {key}, {e}")
            return -1
    
    def hset(self, name: str, mapping: Dict[str, Any]) -> bool:
        """设置哈希表"""
        if not self.is_available():
            return False
        
        try:
            # 添加前缀
            prefixed_name = self._get_prefixed_key(name)
            
            # 序列化复杂对象
            serialized_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized_mapping[key] = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_mapping[key] = str(value)
            
            return bool(self.client.hset(prefixed_name, mapping=serialized_mapping))
        except Exception as e:
            logger.error(f"Redis哈希设置失败: {name}, {e}")
            return False
    
    def hget(self, name: str, key: str) -> Optional[Any]:
        """获取哈希表字段"""
        if not self.is_available():
            return None
        
        try:
            # 添加前缀
            prefixed_name = self._get_prefixed_key(name)
            
            value = self.client.hget(prefixed_name, key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis哈希获取失败: {name}:{key}, {e}")
            return None
    
    def hgetall(self, name: str) -> Dict[str, Any]:
        """获取整个哈希表"""
        if not self.is_available():
            return {}
        
        try:
            # 添加前缀
            prefixed_name = self._get_prefixed_key(name)
            
            result = self.client.hgetall(prefixed_name)
            # 尝试解析所有JSON值
            parsed_result = {}
            for key, value in result.items():
                try:
                    parsed_result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_result[key] = value
            return parsed_result
        except Exception as e:
            logger.error(f"Redis哈希获取全部失败: {name}, {e}")
            return {}
    
    def hdel(self, name: str, *keys: str) -> bool:
        """删除哈希表字段"""
        if not self.is_available():
            return False
        
        try:
            # 添加前缀
            prefixed_name = self._get_prefixed_key(name)
            return bool(self.client.hdel(prefixed_name, *keys))
        except Exception as e:
            logger.error(f"Redis哈希删除失败: {name}, {e}")
            return False
    
    def keys(self, pattern: str = "*") -> list:
        """获取匹配的key列表"""
        if not self.is_available():
            return []
        
        try:
            # 添加前缀到模式中
            if not pattern.startswith(f"{self.key_prefix}:"):
                prefixed_pattern = f"{self.key_prefix}:{pattern}"
            else:
                prefixed_pattern = pattern
            
            keys = self.client.keys(prefixed_pattern)
            # 移除前缀返回
            return [key.replace(f"{self.key_prefix}:", "", 1) for key in keys]
        except Exception as e:
            logger.error(f"Redis获取keys失败: {pattern}, {e}")
            return []
    
    def flushdb(self) -> bool:
        """清空当前数据库"""
        if not self.is_available():
            return False
        
        try:
            self.client.flushdb()
            logger.warning("Redis数据库已清空")
            return True
        except Exception as e:
            logger.error(f"Redis清空数据库失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis连接已关闭")
            except Exception as e:
                logger.error(f"关闭Redis连接失败: {e}")

# 创建全局Redis客户端实例
redis_client = RedisClient() 