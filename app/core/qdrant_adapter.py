import os
import logging
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import hashlib
import numpy as np

logger = logging.getLogger(__name__)

class QdrantAdapter:
    """Qdrant向量数据库适配器"""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6333, 
                 use_https: bool = False,
                 api_key: str = None):
        """
        初始化Qdrant客户端
        
        Args:
            host: Qdrant服务器地址
            port: Qdrant服务器端口
            use_https: 是否使用HTTPS
            api_key: API密钥（可选）
        """
        try:
            self.client = QdrantClient(
                host=host,
                port=port,
                https=use_https,
                api_key=api_key
            )
            
            # 测试连接
            health_status = self._check_health()
            if health_status:
                logger.info(f"Qdrant连接成功: {host}:{port}")
            else:
                raise ConnectionError("Qdrant健康检查失败")
                
        except Exception as e:
            logger.error(f"Qdrant连接失败: {e}")
            raise e
    
    def _check_health(self) -> bool:
        """检查Qdrant服务健康状态"""
        try:
            # 尝试获取集合列表来测试连接
            collections = self.client.get_collections()
            logger.info(f"Qdrant健康检查成功，发现 {len(collections.collections)} 个集合")
            return True
        except Exception as e:
            logger.error(f"Qdrant健康检查失败: {e}")
            return False
    
    def create_collection(self, collection_name: str, dimension: int = 1536) -> bool:
        """创建向量集合"""
        try:
            # 检查集合是否已存在
            collections = self.client.get_collections()
            existing_names = [col.name for col in collections.collections]
            
            if collection_name in existing_names:
                logger.info(f"集合已存在: {collection_name}")
                return True
            
            # 创建新集合 - 使用简化的配置
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                ),
                # 使用字典格式的优化配置
                optimizers_config={
                    "deleted_threshold": 0.2,
                    "vacuum_min_vector_number": 1000,
                    "default_segment_number": 2,
                    "max_segment_size": 20000,
                    "memmap_threshold": 20000,
                    "indexing_threshold": 20000,
                    "flush_interval_sec": 5,
                    "max_optimization_threads": 2
                },
                # 使用字典格式的WAL配置
                wal_config={
                    "wal_capacity_mb": 32,
                    "wal_segments_ahead": 0
                },
                # 使用字典格式的HNSW配置
                hnsw_config={
                    "m": 16,
                    "ef_construct": 100,
                    "full_scan_threshold": 10000,
                    "max_indexing_threads": 0,
                    "on_disk": True
                }
            )
            
            logger.info(f"Qdrant集合创建成功: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建Qdrant集合失败: {e}")
            return False
    
    def add_points(self, collection_name: str, points: List[Dict]) -> bool:
        """批量添加向量点"""
        try:
            qdrant_points = []
            for point in points:
                qdrant_point = PointStruct(
                    id=point.get('id', hashlib.md5(str(point).encode()).hexdigest()),
                    vector=point['vector'],
                    payload=point.get('payload', {})
                )
                qdrant_points.append(qdrant_point)
            
            # 批量插入，分批处理避免超时
            batch_size = 100
            for i in range(0, len(qdrant_points), batch_size):
                batch_points = qdrant_points[i:i + batch_size]
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch_points,
                    wait=True
                )
                
                logger.info(f"批次 {i//batch_size + 1} 插入完成: {len(batch_points)} 条记录")
            
            logger.info(f"Qdrant点添加成功: {len(points)} 条")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant点添加失败: {e}")
            return False
    
    def search(self, collection_name: str, query_vector: List[float], 
               limit: int = 5, filter_dict: Dict = None, with_payload: bool = True) -> List[Dict]:
        """向量搜索"""
        try:
            # 构建过滤器
            query_filter = None
            if filter_dict:
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=conditions)
            
            # 执行搜索
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=with_payload,
                with_vectors=False
            )
            
            # 格式化结果
            formatted_results = []
            for result in search_result:
                formatted_results.append({
                    'id': result.id,
                    'score': float(result.score),
                    'payload': result.payload if with_payload else {}
                })
            
            logger.info(f"Qdrant搜索完成: {len(formatted_results)} 条结果")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Qdrant搜索失败: {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合"""
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Qdrant集合删除成功: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Qdrant集合删除失败: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """获取集合信息"""
        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count or 0,
                "indexed_vectors_count": info.indexed_vectors_count or 0,
                "points_count": info.points_count or 0,
                "segments_count": len(info.segments) if info.segments else 0,
                "disk_data_size": info.disk_data_size or 0,
                "ram_data_size": info.ram_data_size or 0,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.value
                }
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {}
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            collections = self.client.get_collections()
            return [col.name for col in collections.collections]
        except Exception as e:
            logger.error(f"列出集合失败: {e}")
            return [] 