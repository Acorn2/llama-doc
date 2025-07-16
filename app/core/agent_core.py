from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from typing import List, Dict, Optional
import time
import logging
from .vector_store import VectorStoreManager
from .model_factory import ModelFactory

logger = logging.getLogger(__name__)

class DocumentAnalysisAgent:
    """文档分析智能体 - 支持多种大模型"""
    
    def __init__(
        self, 
        vector_store_manager: VectorStoreManager,
        llm_type: str = None,
        model_config: dict = None
    ):
        self.vector_store = vector_store_manager
        
        # 使用模型工厂创建LLM
        self.llm = ModelFactory.create_llm(
            model_type=llm_type,
            **(model_config or {})
        )
        
        # 针对通义千问优化的中文提示词
        if llm_type and llm_type.lower() == "qwen":
            self.qa_prompt = ChatPromptTemplate.from_template("""
你是一个专业的中文文献分析助手，具备深厚的学术背景和文献理解能力。请基于提供的文档内容，准确、专业地回答用户的问题。

文档相关内容：
{context}

用户问题：{question}

回答要求：
1. 严格基于提供的文档内容进行回答，不要添加文档中没有的信息
2. 如果文档中缺少相关信息，请明确指出并说明
3. 保持回答的学术性和客观性，使用准确的专业术语
4. 适当引用原文关键段落支持你的回答
5. 回答要条理清晰，重点突出，便于理解
6. 如果问题涉及多个方面，请分点详细说明

回答：
""")
            
            self.summary_prompt = ChatPromptTemplate.from_template("""
请为以下学术文档生成一份高质量的中文摘要：

文档内容：
{content}

摘要要求：
1. 准确概括文档的核心观点、主要发现和重要结论
2. 突出文档的学术价值和创新点
3. 保持逻辑结构清晰，语言表达准确
4. 摘要长度控制在300-600字之间
5. 使用规范的学术写作风格
6. 如果涉及数据或实验结果，请准确提及

摘要：
""")
        else:
            # 保持原有的通用提示词
            self.qa_prompt = ChatPromptTemplate.from_template("""
你是一个专业的文档分析助手。基于以下文档内容，请准确回答用户的问题。

文档相关内容：
{context}

用户问题：{question}

请遵循以下要求：
1. 基于提供的文档内容进行回答
2. 如果文档中没有相关信息，请明确说明
3. 保持回答的准确性和客观性
4. 如果需要，可以引用具体的文档段落
5. 回答要简洁明了，重点突出

回答：
""")
            
            self.summary_prompt = ChatPromptTemplate.from_template("""
请为以下文档内容生成一个简洁而全面的摘要：

文档内容：
{content}

摘要要求：
1. 突出文档的主要观点和核心内容
2. 保持逻辑清晰，结构合理
3. 长度控制在200-500字之间
4. 使用简洁明了的语言

摘要：
""")
    
    def answer_question(
        self, 
        document_id: str, 
        question: str, 
        max_results: int = 5
    ) -> Dict:
        """回答基于文档的问题"""
        start_time = time.time()
        
        try:
            # 1. 向量搜索相关内容
            search_results = self.vector_store.search_similar_chunks(
                document_id=document_id,
                query=question,
                k=max_results
            )
            
            if not search_results:
                return {
                    "answer": "抱歉，在该文档中未找到与您问题相关的内容。",
                    "confidence": 0.0,
                    "sources": [],
                    "processing_time": time.time() - start_time,
                    "success": True
                }
            
            # 2. 构建上下文
            context = self._build_context(search_results)
            
            # 3. 生成回答 - 兼容不同模型接口
            try:
                # 尝试使用LangChain链式调用
                chain = self.qa_prompt | self.llm | StrOutputParser()
                answer = chain.invoke({
                    "context": context,
                    "question": question
                })
            except Exception as e:
                # 降级到直接调用模型
                logger.warning(f"链式调用失败，使用直接调用: {str(e)}")
                prompt_text = self.qa_prompt.format(context=context, question=question)
                answer = self.llm.predict(prompt_text)
            
            # 4. 计算置信度
            confidence = self._calculate_confidence(search_results)
            
            # 5. 准备源信息
            sources = self._prepare_sources(search_results)
            
            processing_time = time.time() - start_time
            
            return {
                "answer": answer.strip(),
                "confidence": confidence,
                "sources": sources,
                "processing_time": processing_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"问答处理失败: {str(e)}")
            return {
                "answer": "处理问题时发生错误，请稍后重试。",
                "confidence": 0.0,
                "sources": [],
                "processing_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    def generate_summary(self, document_id: str) -> Dict:
        """生成文档摘要"""
        try:
            # 获取文档的所有块（用于生成摘要）
            search_results = self.vector_store.search_similar_chunks(
                document_id=document_id,
                query="文档主要内容 核心观点 关键信息",
                k=10
            )
            
            if not search_results:
                return {
                    "summary": "无法生成摘要：文档内容为空或未找到。",
                    "success": False
                }
            
            # 构建内容
            content = "\n\n".join([result["content"] for result in search_results[:5]])
            
            # 生成摘要
            chain = self.summary_prompt | self.llm | StrOutputParser()
            summary = chain.invoke({"content": content})
            
            return {
                "summary": summary.strip(),
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"摘要生成失败: {str(e)}")
            return {
                "summary": "生成摘要时发生错误。",
                "success": False,
                "error": str(e)
            }
    
    def _build_context(self, search_results: List[Dict]) -> str:
        """构建问答上下文"""
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"段落 {i} (相似度: {result['similarity_score']:.3f}):\n"
                f"{result['content']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _calculate_confidence(self, search_results: List[Dict]) -> float:
        """计算回答置信度"""
        if not search_results:
            return 0.0
        
        # 基于最高相似度分数计算置信度
        max_score = max(result["similarity_score"] for result in search_results)
        
        # 将相似度分数转换为置信度（0-1范围）
        # 这里使用简单的映射，可以根据实际情况调整
        confidence = min(max_score * 2, 1.0)
        
        return round(confidence, 3)
    
    def _prepare_sources(self, search_results: List[Dict]) -> List[Dict]:
        """准备源信息"""
        sources = []
        
        for result in search_results:
            sources.append({
                "chunk_id": result["chunk_id"],
                "chunk_index": result["chunk_index"],
                "similarity_score": result["similarity_score"],
                "content_preview": result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
            })
        
        return sources

    def answer_question_enhanced(
        self, 
        document_id: str, 
        question: str, 
        max_results: int = 5
    ) -> Dict:
        """增强的问答方法 - 包含质量评估和优化"""
        start_time = time.time()
        
        try:
            # 1. 使用增强向量存储进行混合搜索
            if hasattr(self.vector_store, 'hybrid_search'):
                search_results = self.vector_store.hybrid_search(
                    document_id=document_id,
                    query=question,
                    k=max_results
                )
            else:
                search_results = self.vector_store.search_similar_chunks(
                    document_id=document_id,
                    query=question,
                    k=max_results
                )
            
            if not search_results:
                return {
                    "answer": "抱歉，在该文档中未找到与您问题相关的内容。",
                    "confidence": 0.0,
                    "sources": [],
                    "processing_time": time.time() - start_time,
                    "quality_score": 0.0,
                    "success": True
                }
            
            # 2. 智能上下文构建
            context = self._build_enhanced_context(search_results, question)
            
            # 3. 生成增强回答
            answer = self._generate_enhanced_answer(context, question)
            
            # 4. 计算增强置信度和质量分数
            confidence = self._calculate_enhanced_confidence(search_results, question, answer)
            quality_score = self._evaluate_answer_quality(answer, question, search_results)
            
            # 5. 准备详细源信息
            sources = self._prepare_enhanced_sources(search_results)
            
            processing_time = time.time() - start_time
            
            return {
                "answer": answer.strip(),
                "confidence": confidence,
                "sources": sources,
                "processing_time": processing_time,
                "quality_score": quality_score,
                "search_method": "hybrid" if hasattr(self.vector_store, 'hybrid_search') else "vector",
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"增强问答处理失败: {str(e)}")
            return {
                "answer": "处理问题时发生错误，请稍后重试。",
                "confidence": 0.0,
                "sources": [],
                "processing_time": time.time() - start_time,
                "quality_score": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def _build_enhanced_context(self, search_results: List[Dict], question: str) -> str:
        """构建增强的问答上下文"""
        context_parts = []
        
        # 按相似度和质量分数排序
        sorted_results = sorted(
            search_results, 
            key=lambda x: (x['similarity_score'] * x.get('metadata', {}).get('quality_score', 0.5)),
            reverse=True
        )
        
        for i, result in enumerate(sorted_results, 1):
            metadata = result.get('metadata', {})
            quality_score = metadata.get('quality_score', 0.5)
            keywords = metadata.get('keywords', [])
            
            # 构建增强的上下文段落
            context_part = f"【文档片段 {i}】(相似度: {result['similarity_score']:.3f}, 质量: {quality_score:.2f})\n"
            
            # 如果有关键词，添加关键词信息
            if keywords:
                context_part += f"关键词: {', '.join(keywords[:5])}\n"
            
            context_part += f"内容: {result['content']}\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _generate_enhanced_answer(self, context: str, question: str) -> str:
        """生成增强的回答"""
        try:
            # 使用增强的提示词模板
            enhanced_prompt = ChatPromptTemplate.from_template("""
你是一个专业的中文文献分析助手，具备深厚的学术背景和文献理解能力。请基于提供的文档内容，准确、专业地回答用户的问题。

【文档相关内容】
{context}

【用户问题】
{question}

【回答要求】
1. 严格基于提供的文档内容进行回答，确保信息准确性
2. 如果文档中缺少直接相关信息，请明确指出并尽可能提供相关背景
3. 保持回答的学术性和客观性，使用准确的专业术语
4. 适当引用原文关键段落或数据支持你的回答
5. 回答要条理清晰，逻辑连贯，便于理解
6. 如果问题涉及多个方面，请分点详细说明
7. 回答长度要适中，既要全面又要简洁

【专业回答】
""")
            
            # 尝试使用链式调用
            try:
                chain = enhanced_prompt | self.llm | StrOutputParser()
                answer = chain.invoke({
                    "context": context,
                    "question": question
                })
            except Exception as e:
                # 降级到直接调用
                logger.warning(f"链式调用失败，使用直接调用: {str(e)}")
                prompt_text = enhanced_prompt.format(context=context, question=question)
                answer = self.llm.predict(prompt_text)
            
            return answer
            
        except Exception as e:
            logger.error(f"生成增强回答失败: {str(e)}")
            # 降级到基础回答生成
            return self._generate_basic_answer(context, question)
    
    def _generate_basic_answer(self, context: str, question: str) -> str:
        """生成基础回答（降级方案）"""
        try:
            chain = self.qa_prompt | self.llm | StrOutputParser()
            return chain.invoke({"context": context, "question": question})
        except Exception as e:
            logger.error(f"基础回答生成也失败: {str(e)}")
            return "抱歉，生成回答时遇到技术问题，请稍后重试。"
    
    def _calculate_enhanced_confidence(
        self, 
        search_results: List[Dict], 
        question: str, 
        answer: str
    ) -> float:
        """计算增强的置信度"""
        if not search_results:
            return 0.0
        
        # 基础相似度置信度
        base_confidence = max(result["similarity_score"] for result in search_results)
        
        # 质量加权置信度
        quality_weighted_confidence = sum(
            result["similarity_score"] * result.get('metadata', {}).get('quality_score', 0.5)
            for result in search_results
        ) / len(search_results)
        
        # 覆盖度置信度（多个结果一致性）
        coverage_confidence = min(len(search_results) / 3.0, 1.0)
        
        # 答案完整性评估
        answer_completeness = self._evaluate_answer_completeness(answer, question)
        
        # 综合置信度计算
        enhanced_confidence = (
            base_confidence * 0.3 +
            quality_weighted_confidence * 0.3 +
            coverage_confidence * 0.2 +
            answer_completeness * 0.2
        )
        
        return round(min(enhanced_confidence, 1.0), 3)
    
    def _evaluate_answer_completeness(self, answer: str, question: str) -> float:
        """评估回答完整性"""
        try:
            # 基础长度检查
            if len(answer.strip()) < 20:
                return 0.2
            
            # 结构完整性检查
            structure_score = 0.5
            
            # 检查是否有完整句子
            if any(punct in answer for punct in ['。', '！', '？', '.', '!', '?']):
                structure_score += 0.2
            
            # 检查是否直接回应了问题
            import jieba
            question_words = set(jieba.cut(question.lower()))
            answer_words = set(jieba.cut(answer.lower()))
            
            # 移除停用词
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个'}
            question_words = question_words - stop_words
            answer_words = answer_words - stop_words
            
            if question_words and answer_words:
                word_overlap = len(question_words & answer_words) / len(question_words)
                structure_score += word_overlap * 0.3
            
            return min(structure_score, 1.0)
            
        except Exception as e:
            logger.warning(f"回答完整性评估失败: {e}")
            return 0.5
    
    def _evaluate_answer_quality(
        self, 
        answer: str, 
        question: str, 
        search_results: List[Dict]
    ) -> float:
        """评估回答质量"""
        try:
            quality_score = 0.5  # 基础分数
            
            # 1. 答案长度适中性 (20%)
            answer_length = len(answer.strip())
            if 50 <= answer_length <= 800:
                quality_score += 0.2
            elif 20 <= answer_length < 50 or 800 < answer_length <= 1500:
                quality_score += 0.1
            
            # 2. 内容相关性 (30%)
            relevance_score = self._calculate_content_relevance(answer, search_results)
            quality_score += relevance_score * 0.3
            
            # 3. 语言流畅性 (25%)
            fluency_score = self._evaluate_language_fluency(answer)
            quality_score += fluency_score * 0.25
            
            # 4. 信息准确性 (25%)
            accuracy_score = self._evaluate_information_accuracy(answer, search_results)
            quality_score += accuracy_score * 0.25
            
            return round(min(quality_score, 1.0), 3)
            
        except Exception as e:
            logger.warning(f"回答质量评估失败: {e}")
            return 0.5
    
    def _calculate_content_relevance(self, answer: str, search_results: List[Dict]) -> float:
        """计算内容相关性"""
        try:
            import jieba
            answer_words = set(jieba.cut(answer.lower()))
            
            # 计算与检索结果的词汇重叠度
            total_overlap = 0
            total_words = 0
            
            for result in search_results:
                content_words = set(jieba.cut(result['content'].lower()))
                if content_words:
                    overlap = len(answer_words & content_words)
                    total_overlap += overlap
                    total_words += len(content_words)
            
            if total_words > 0:
                return min(total_overlap / total_words * 5, 1.0)  # 放大系数
            
            return 0.5
            
        except Exception as e:
            logger.warning(f"内容相关性计算失败: {e}")
            return 0.5
    
    def _evaluate_language_fluency(self, answer: str) -> float:
        """评估语言流畅性"""
        try:
            fluency_score = 0.5
            
            # 检查句子完整性
            sentence_endings = len([c for c in answer if c in '。！？.!?'])
            if sentence_endings > 0:
                fluency_score += 0.2
            
            # 检查逻辑连接词
            logical_connectors = ['因为', '所以', '但是', '然而', '此外', '另外', '首先', '其次', '最后', '总之']
            if any(connector in answer for connector in logical_connectors):
                fluency_score += 0.2
            
            # 检查重复内容
            words = answer.split()
            if len(set(words)) / max(len(words), 1) > 0.7:  # 词汇多样性
                fluency_score += 0.1
            
            return min(fluency_score, 1.0)
            
        except Exception as e:
            logger.warning(f"语言流畅性评估失败: {e}")
            return 0.5
    
    def _evaluate_information_accuracy(self, answer: str, search_results: List[Dict]) -> float:
        """评估信息准确性"""
        try:
            # 简单的准确性检查 - 检查是否包含明显错误信息
            accuracy_score = 0.7  # 基础准确性假设
            
            # 检查是否包含明确的不确定性表述（好的做法）
            uncertainty_phrases = ['可能', '大概', '据文档显示', '根据资料', '文档中提到']
            if any(phrase in answer for phrase in uncertainty_phrases):
                accuracy_score += 0.2
            
            # 检查是否直接引用了文档内容
            for result in search_results:
                content = result['content']
                # 检查是否有较长的重复片段（可能是直接引用）
                for i in range(len(answer) - 20):
                    if answer[i:i+20] in content:
                        accuracy_score += 0.1
                        break
            
            return min(accuracy_score, 1.0)
            
        except Exception as e:
            logger.warning(f"信息准确性评估失败: {e}")
            return 0.7
    
    def _prepare_enhanced_sources(self, search_results: List[Dict]) -> List[Dict]:
        """准备增强的源信息"""
        sources = []
        
        for result in search_results:
            metadata = result.get('metadata', {})
            
            source_info = {
                "chunk_id": result["chunk_id"],
                "chunk_index": result["chunk_index"],
                "similarity_score": result["similarity_score"],
                "quality_score": metadata.get("quality_score", 0.5),
                "keywords": metadata.get("keywords", []),
                "summary": metadata.get("summary", ""),
                "content_preview": result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"],
                "content_length": len(result["content"])
            }
            
            sources.append(source_info)
        
        return sources

    def generate_summary_enhanced(self, document_id: str) -> Dict:
        """生成增强的文档摘要"""
        try:
            # 1. 获取高质量的文档片段用于摘要
            if hasattr(self.vector_store, 'hybrid_search'):
                # 使用多个关键词进行综合搜索
                summary_queries = [
                    "文档主要内容 核心观点 关键信息",
                    "研究方法 实验结果 重要发现",
                    "结论 建议 总结"
                ]
                
                all_results = []
                for query in summary_queries:
                    results = self.vector_store.hybrid_search(
                        document_id=document_id,
                        query=query,
                        k=5
                    )
                    all_results.extend(results)
                
                # 去重并按质量排序
                unique_results = {}
                for result in all_results:
                    chunk_id = result['chunk_id']
                    if chunk_id not in unique_results:
                        unique_results[chunk_id] = result
                
                search_results = list(unique_results.values())
                search_results.sort(
                    key=lambda x: x['similarity_score'] * x.get('metadata', {}).get('quality_score', 0.5),
                    reverse=True
                )
                search_results = search_results[:8]  # 取前8个最优质的片段
                
            else:
                search_results = self.vector_store.search_similar_chunks(
                    document_id=document_id,
                    query="文档主要内容 核心观点 关键信息",
                    k=8
                )
            
            if not search_results:
                return {
                    "summary": "无法生成摘要：文档内容为空或未找到。",
                    "key_points": [],
                    "keywords": [],
                    "quality_score": 0.0,
                    "success": False
                }
            
            # 2. 构建结构化内容用于摘要
            content_sections = self._organize_content_for_summary(search_results)
            
            # 3. 生成增强摘要
            summary = self._generate_structured_summary(content_sections)
            
            # 4. 提取关键要点和关键词
            key_points = self._extract_key_points(search_results)
            keywords = self._extract_summary_keywords(search_results)
            
            # 5. 评估摘要质量
            quality_score = self._evaluate_summary_quality(summary, search_results)
            
            return {
                "summary": summary.strip(),
                "key_points": key_points,
                "keywords": keywords,
                "quality_score": quality_score,
                "source_chunks": len(search_results),
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"增强摘要生成失败: {str(e)}")
            return {
                "summary": "生成摘要时发生错误。",
                "key_points": [],
                "keywords": [],
                "quality_score": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def _organize_content_for_summary(self, search_results: List[Dict]) -> Dict:
        """为摘要组织内容"""
        content_sections = {
            "high_quality": [],  # 高质量内容
            "key_concepts": [],  # 关键概念
            "structured_info": []  # 结构化信息
        }
        
        for result in search_results:
            metadata = result.get('metadata', {})
            quality_score = metadata.get('quality_score', 0.5)
            content = result['content']
            
            # 分类内容
            if quality_score > 0.7:
                content_sections["high_quality"].append(content)
            
            # 提取关键概念
            keywords = metadata.get('keywords', [])
            if keywords:
                content_sections["key_concepts"].extend(keywords)
            
            # 识别结构化信息（如标题、列表等）
            if any(pattern in content for pattern in ['第', '章', '节', '一、', '二、', '(一)', '1.', '•']):
                content_sections["structured_info"].append(content)
        
        return content_sections
    
    def _generate_structured_summary(self, content_sections: Dict) -> str:
        """生成结构化摘要"""
        try:
            # 构建分层内容
            content_for_summary = ""
            
            if content_sections["high_quality"]:
                content_for_summary += "【核心内容】\n" + "\n\n".join(content_sections["high_quality"][:3])
            
            if content_sections["structured_info"]:
                content_for_summary += "\n\n【结构化信息】\n" + "\n\n".join(content_sections["structured_info"][:2])
            
            if content_sections["key_concepts"]:
                unique_concepts = list(set(content_sections["key_concepts"][:15]))
                content_for_summary += f"\n\n【关键概念】\n{', '.join(unique_concepts)}"
            
            # 使用增强的摘要提示词
            enhanced_summary_prompt = ChatPromptTemplate.from_template("""
请为以下学术文档生成一份高质量的中文摘要，要求结构清晰、内容准确、重点突出。

【文档内容】
{content}

【摘要生成要求】
1. 准确概括文档的核心观点、主要发现和重要结论
2. 突出文档的学术价值和创新点
3. 保持逻辑结构清晰，语言表达准确流畅
4. 摘要长度控制在300-600字之间
5. 使用规范的学术写作风格
6. 如果涉及数据或实验结果，请准确提及
7. 分段组织，便于阅读理解

【结构化摘要】
""")
            
            # 生成摘要
            try:
                chain = enhanced_summary_prompt | self.llm | StrOutputParser()
                summary = chain.invoke({"content": content_for_summary})
            except Exception as e:
                logger.warning(f"链式调用失败，使用直接调用: {str(e)}")
                prompt_text = enhanced_summary_prompt.format(content=content_for_summary)
                summary = self.llm.predict(prompt_text)
            
            return summary
            
        except Exception as e:
            logger.error(f"结构化摘要生成失败: {str(e)}")
            # 降级到基础摘要
            return self._generate_basic_summary(content_sections)
    
    def _generate_basic_summary(self, content_sections: Dict) -> str:
        """生成基础摘要（降级方案）"""
        try:
            content = "\n\n".join(content_sections.get("high_quality", [])[:3])
            if not content:
                content = "文档内容"
            
            chain = self.summary_prompt | self.llm | StrOutputParser()
            return chain.invoke({"content": content})
        except Exception as e:
            logger.error(f"基础摘要生成失败: {str(e)}")
            return "无法生成文档摘要，请稍后重试。"
    
    def _extract_key_points(self, search_results: List[Dict]) -> List[str]:
        """提取关键要点"""
        key_points = []
        
        try:
            for result in search_results[:5]:  # 取前5个高质量结果
                content = result['content']
                
                # 寻找明确的要点（如编号列表、重要结论等）
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    # 识别要点模式
                    if (any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '一、', '二、', '三、', '•', '-']) or
                        any(keyword in line for keyword in ['重要', '关键', '核心', '主要', '结论', '发现']) and
                        10 <= len(line) <= 200):
                        
                        if line not in key_points:
                            key_points.append(line)
                
                if len(key_points) >= 8:
                    break
            
            return key_points[:8]  # 最多返回8个要点
            
        except Exception as e:
            logger.warning(f"关键要点提取失败: {e}")
            return []
    
    def _extract_summary_keywords(self, search_results: List[Dict]) -> List[str]:
        """提取摘要关键词"""
        try:
            all_keywords = []
            
            # 从元数据中收集关键词
            for result in search_results:
                metadata = result.get('metadata', {})
                keywords = metadata.get('keywords', [])
                all_keywords.extend(keywords)
            
            # 统计关键词频率并去重
            from collections import Counter
            keyword_counts = Counter(all_keywords)
            
            # 返回出现频率最高的关键词
            top_keywords = [kw for kw, count in keyword_counts.most_common(15)]
            
            return top_keywords
            
        except Exception as e:
            logger.warning(f"摘要关键词提取失败: {e}")
            return []
    
    def _evaluate_summary_quality(self, summary: str, search_results: List[Dict]) -> float:
        """评估摘要质量"""
        try:
            quality_score = 0.5
            
            # 1. 长度适中性 (25%)
            summary_length = len(summary.strip())
            if 200 <= summary_length <= 800:
                quality_score += 0.25
            elif 100 <= summary_length < 200 or 800 < summary_length <= 1200:
                quality_score += 0.15
            
            # 2. 内容覆盖度 (30%)
            coverage_score = self._calculate_content_coverage(summary, search_results)
            quality_score += coverage_score * 0.3
            
            # 3. 结构完整性 (25%)
            structure_score = self._evaluate_summary_structure(summary)
            quality_score += structure_score * 0.25
            
            # 4. 语言质量 (20%)
            language_score = self._evaluate_language_fluency(summary)
            quality_score += language_score * 0.2
            
            return round(min(quality_score, 1.0), 3)
            
        except Exception as e:
            logger.warning(f"摘要质量评估失败: {e}")
            return 0.5
    
    def _calculate_content_coverage(self, summary: str, search_results: List[Dict]) -> float:
        """计算内容覆盖度"""
        try:
            import jieba
            summary_words = set(jieba.cut(summary.lower()))
            
            # 计算与源内容的重叠度
            total_source_words = set()
            for result in search_results[:5]:
                source_words = set(jieba.cut(result['content'].lower()))
                total_source_words.update(source_words)
            
            if total_source_words:
                coverage = len(summary_words & total_source_words) / len(total_source_words)
                return min(coverage * 3, 1.0)  # 放大系数
            
            return 0.5
            
        except Exception as e:
            logger.warning(f"内容覆盖度计算失败: {e}")
            return 0.5
    
    def _evaluate_summary_structure(self, summary: str) -> float:
        """评估摘要结构"""
        try:
            structure_score = 0.3
            
            # 检查段落结构
            paragraphs = summary.split('\n\n')
            if len(paragraphs) >= 2:
                structure_score += 0.3
            
            # 检查逻辑结构词
            structure_words = ['首先', '其次', '然后', '最后', '总之', '综上', '因此', '此外', '另外']
            if any(word in summary for word in structure_words):
                structure_score += 0.2
            
            # 检查完整句子
            if summary.count('。') >= 3:
                structure_score += 0.2
            
            return min(structure_score, 1.0)
            
        except Exception as e:
            logger.warning(f"摘要结构评估失败: {e}")
            return 0.5 