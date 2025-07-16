import jieba
import re
import numpy as np
from typing import List, Dict, Any, Optional
from .vector_store import VectorStoreManager
from .cache_manager import cache_manager
import logging

logger = logging.getLogger(__name__)

class EnhancedVectorStore(VectorStoreManager):
    """增强的向量存储 - Qdrant版本"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_manager = cache_manager
        
        # 扩展停用词列表
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '这', '那', '他', '她', '它', '们', '与', '及', '以', '为', '到', '从', '被',
            '把', '让', '使', '等', '等等', '如', '如果', '因为', '所以', '但是', '然而',
            '而且', '或者', '并且', '也', '还', '又', '再', '更', '最', '很', '非常'
        }
    
    def search_similar_chunks_with_cache(
        self, 
        document_id: str, 
        query: str, 
        k: int = 5
    ) -> List[Dict]:
        """带缓存的向量搜索"""
        
        # 检查缓存
        cache_key = self.cache_manager.search_cache_key(document_id, query, k)
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result:
            logger.info(f"命中搜索缓存: {document_id}")
            return cached_result
        
        # 执行搜索
        results = self.search_similar_chunks(document_id, query, k)
        
        # 缓存结果（1小时）
        self.cache_manager.set(cache_key, results, expire=3600)
        
        return results
    
    def add_document_chunks_enhanced(self, document_id: str, chunks: List[Dict]) -> bool:
        """增强的文档块添加"""
        try:
            collection_name = f"doc_{document_id}"
            
            # 增强文本内容用于向量化
            enhanced_texts = []
            for chunk in chunks:
                enhanced_text = self._enhance_text_for_embedding(chunk)
                enhanced_texts.append(enhanced_text)
                
            # 生成嵌入向量
            logger.info(f"正在为 {len(enhanced_texts)} 个增强文档块生成嵌入向量...")
            embeddings = self.embeddings.embed_documents(enhanced_texts)
            
            # 准备向量点数据
            points = []
            for i, chunk in enumerate(chunks):
                point = {
                    'id': chunk["chunk_id"],
                    'vector': embeddings[i],
                    'payload': {
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"],
                    "document_id": document_id,
                        "content": chunk["content"],  # 保存原始内容
                        "enhanced_content": enhanced_texts[i],  # 保存增强内容
                    "chunk_length": chunk["chunk_length"],
                    "keywords": chunk.get("keywords", []),
                    "summary": chunk.get("summary", ""),
                        "quality_score": chunk.get("quality_score", 0.5)
                    }
                }
                points.append(point)
            
            # 添加到Qdrant
            return self.qdrant_client.add_points(collection_name, points)
            
        except Exception as e:
            logger.error(f"增强文档块添加失败: {str(e)}")
            return False
    
    def _enhance_text_for_embedding(self, chunk: Dict) -> str:
        """增强文本用于向量化"""
        content = chunk["content"]
        keywords = chunk.get("keywords", [])
        summary = chunk.get("summary", "")
        
        # 构建增强文本
        enhanced_parts = [content]
        
        # 添加关键词（重复以增强权重）
        if keywords:
            keyword_text = " ".join(keywords)
            enhanced_parts.append(f"\n重要概念: {keyword_text}")
            # 再次添加关键词以提高权重
            enhanced_parts.append(keyword_text)
        
        # 添加摘要
        if summary and summary != content[:len(summary)]:
            enhanced_parts.append(f"\n内容要点: {summary}")
        
        return " ".join(enhanced_parts)
    
    def hybrid_search(
        self, 
        document_id: str, 
        query: str, 
        k: int = 5,
        alpha: float = 0.7
    ) -> List[Dict]:
        """混合检索：向量搜索 + 关键词搜索"""
        
        try:
            # 查询预处理和扩展
            expanded_query = self._expand_query(query)
            
            # 向量搜索（使用扩展查询）
            vector_results = self.search_similar_chunks_with_cache(
                document_id, expanded_query, k * 2
            )
            
            # 关键词搜索（使用原始查询）
            keyword_results = self._enhanced_keyword_search(document_id, query, k * 2)
            
            # 融合搜索结果
            combined_results = self._combine_search_results(
                vector_results, keyword_results, alpha
            )
            
            # 重排序优化
            reranked_results = self._rerank_results(combined_results, query)
            
            return reranked_results[:k]
            
        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            # 降级到普通向量搜索
            return self.search_similar_chunks_with_cache(document_id, query, k)
    
    def _expand_query(self, query: str) -> str:
        """查询扩展"""
        try:
            # 提取查询关键词
            query_keywords = jieba.analyse.extract_tags(query, topK=5)
            
            # 简单的同义词扩展
            synonyms_map = {
                "方法": ["手段", "途径", "策略"],
                "问题": ["难题", "困难", "挑战"],
                "结果": ["成果", "效果", "产出"],
                "分析": ["研究", "调查", "探讨"],
                "系统": ["体系", "框架", "平台"]
            }
            
            expanded_terms = [query]
            for keyword in query_keywords:
                if keyword in synonyms_map:
                    expanded_terms.extend(synonyms_map[keyword])
            
            return " ".join(expanded_terms)
            
        except Exception as e:
            logger.warning(f"查询扩展失败: {e}")
            return query
    
    def _enhanced_keyword_search(self, document_id: str, query: str, k: int) -> List[Dict]:
        """增强的关键词搜索"""
        try:
            collection_name = f"doc_{document_id}"
            
            # 获取所有点
            all_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=[0.0] * 1536,  # 虚拟向量
                limit=1000,  # 获取大量结果用于关键词匹配
                with_payload=True
            )
            
            if not all_results:
                return []
            
            results = []
            for result in all_results:
                payload = result['payload']
                content = payload.get('content', '')
                
                # 计算关键词匹配分数
                score = self._calculate_enhanced_keyword_score(content, query, payload)
                
                if score > 0:
                    results.append({
                        "content": content,
                        "chunk_id": payload.get("chunk_id", ""),
                        "chunk_index": payload.get("chunk_index", 0),
                        "similarity_score": score,
                        "metadata": {
                            "keywords": payload.get("keywords", []),
                            "summary": payload.get("summary", ""),
                            "quality_score": payload.get("quality_score", 0.5),
                            "chunk_length": payload.get("chunk_length", 0)
                        }
                    })
            
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:k]
            
        except Exception as e:
            logger.error(f"增强关键词搜索失败: {e}")
            return []
    
    def _calculate_enhanced_keyword_score(self, content: str, query: str, metadata: Dict) -> float:
        """计算增强的关键词匹配分数"""
        try:
            # 基础关键词匹配分数
            base_score = self._calculate_keyword_score(content, query)
            
            # 关键词匹配奖励
            keywords = metadata.get('keywords', [])
            query_words = set(jieba.cut(query.lower()))
            keyword_matches = len(set(keywords) & query_words)
            keyword_bonus = keyword_matches / max(len(keywords), 1) * 0.3
            
            # 摘要匹配奖励
            summary = metadata.get('summary', '')
            if summary:
                summary_score = self._calculate_keyword_score(summary, query)
                summary_bonus = summary_score * 0.2
            else:
                summary_bonus = 0
            
            # 质量分数权重
            quality_score = metadata.get('quality_score', 0.5)
            quality_weight = 0.8 + (quality_score * 0.4)
            
            # 计算最终分数
            final_score = (base_score + keyword_bonus + summary_bonus) * quality_weight
            
            return min(final_score, 1.0)
            
        except Exception as e:
            logger.error(f"增强关键词分数计算失败: {e}")
            return 0.0
    
    def _calculate_keyword_score(self, content: str, query: str) -> float:
        """计算关键词匹配分数"""
        try:
            # 分词
            query_words = set(jieba.cut(query.lower()))
            content_words = set(jieba.cut(content.lower()))
            
            # 移除停用词和单字符
            query_words = {w for w in query_words if len(w) > 1 and w not in self.stop_words}
            content_words = {w for w in content_words if len(w) > 1 and w not in self.stop_words}
            
            if not query_words:
                return 0.0
            
            # 计算交集
            intersection = query_words & content_words
            
            if not intersection:
                return 0.0
            
            # 计算Jaccard相似度
            jaccard_score = len(intersection) / len(query_words | content_words)
            
            # 完全匹配奖励
            exact_matches = sum(1 for word in query_words if word in content.lower())
            exact_match_bonus = exact_matches / len(query_words) * 0.5
            
            # 查询覆盖度奖励
            coverage_bonus = len(intersection) / len(query_words) * 0.3
            
            final_score = jaccard_score + exact_match_bonus + coverage_bonus
            
            return min(final_score, 1.0)
            
        except Exception as e:
            logger.error(f"关键词分数计算失败: {e}")
            return 0.0
    
    def _combine_search_results(
        self, 
        vector_results: List[Dict], 
        keyword_results: List[Dict], 
        alpha: float = 0.7
    ) -> List[Dict]:
        """融合搜索结果"""
        
        def normalize_scores(results):
            if not results:
                return results
            
            scores = [r['similarity_score'] for r in results]
            max_score = max(scores) if scores else 1.0
            min_score = min(scores) if scores else 0.0
            
            if max_score == min_score:
                for r in results:
                    r['similarity_score'] = 1.0
                return results
            
            for r in results:
                r['similarity_score'] = (r['similarity_score'] - min_score) / (max_score - min_score)
            
            return results
        
        # 归一化分数
        vector_results = normalize_scores(vector_results.copy())
        keyword_results = normalize_scores(keyword_results.copy())
        
        # 创建内容映射
        content_map = {}
        
        # 添加向量搜索结果
        for result in vector_results:
            content = result['content']
            content_map[content] = {
                **result,
                'vector_score': result['similarity_score'],
                'keyword_score': 0.0
            }
        
        # 添加关键词搜索结果
        for result in keyword_results:
            content = result['content']
            if content in content_map:
                content_map[content]['keyword_score'] = result['similarity_score']
            else:
                content_map[content] = {
                    **result,
                    'vector_score': 0.0,
                    'keyword_score': result['similarity_score']
                }
        
        # 计算综合分数
        for content, result in content_map.items():
            combined_score = (
                alpha * result['vector_score'] + 
                (1 - alpha) * result['keyword_score']
            )
            result['similarity_score'] = combined_score
        
        # 排序并返回
        final_results = list(content_map.values())
        final_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return final_results
    
    def _rerank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """重排序结果"""
        try:
            if not results:
                return results
            
            for result in results:
                # 获取质量分数加权
                quality_score = result.get('metadata', {}).get('quality_score', 0.5)
                
                # 基于查询长度的相关性调整
                content_length = len(result['content'])
                query_length = len(query)
                
                # 长查询偏好长内容，短查询偏好短内容
                length_preference = 1.0
                if query_length < 20:  # 短查询
                    if content_length > 1000:
                        length_preference = 0.9
                elif query_length > 50:  # 长查询
                    if content_length < 200:
                        length_preference = 0.9
                
                # 调整最终分数
                adjusted_score = (
                    result['similarity_score'] * 0.7 +
                    quality_score * 0.2 +
                    length_preference * 0.1
                )
                
                result['final_score'] = adjusted_score
                result['similarity_score'] = adjusted_score
            
            # 重新排序
            results.sort(key=lambda x: x['final_score'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.warning(f"结果重排序失败: {e}")
            return results