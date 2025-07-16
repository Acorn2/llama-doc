import fitz  # PyMuPDF
import os
import hashlib
import re
import numpy as np
from typing import List, Dict, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from ..utils.file_storage import file_storage_manager
import logging
import jieba
import jieba.analyse
import tempfile

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """PDF文档处理器 - 增强版，支持COS存储"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        # 优化分块参数
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 使用更智能的分隔符序列
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n### ",  # 标题分隔符
                "\n\n",      # 段落分隔符
                "\n",        # 行分隔符
                "。",        # 中文句号
                "！",        # 中文感叹号
                "？",        # 中文问号
                "；",        # 中文分号
                "，",        # 中文逗号
                " ",         # 空格
                ""           # 字符级别
            ]
        )
        
        # 初始化jieba
        jieba.initialize()
    
    def extract_text_from_pdf(self, file_path: str) -> Dict[str, any]:
        """从PDF文件中提取文本和元数据 - 增强版"""
        try:
            # 预检查文件
            if not os.path.exists(file_path):
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {"success": False, "error": "文件为空"}
            
            # 尝试打开PDF
            try:
                with fitz.open(file_path) as doc:
                    # 检查文档是否可读
                    if doc.page_count == 0:
                        return {"success": False, "error": "PDF文档无页面"}
                    
                    # 检查PDF是否有密码保护
                    if doc.needs_pass:
                        return {
                            "metadata": {},
                            "full_text": "",
                            "page_texts": [],
                            "success": False,
                            "error": "PDF文件需要密码"
                        }
                    
                    # 提取基本信息
                    metadata = {
                        "pages": len(doc),
                        "title": doc.metadata.get("title", ""),
                        "author": doc.metadata.get("author", ""),
                        "subject": doc.metadata.get("subject", ""),
                        "keywords": doc.metadata.get("keywords", "")
                    }
                    
                    # 新增：结构化内容提取
                    structured_content = []
                    full_text = ""
                    page_texts = []
                    total_chars = 0
                    empty_pages = 0
                    
                    logger.info(f"开始处理PDF文档，共 {len(doc)} 页")
                    
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        
                        # 使用增强的文本提取方法
                        page_content = self._extract_page_content_enhanced(page, page_num + 1)
                        
                        if page_content["success"]:
                            structured_content.extend(page_content["blocks"])
                            page_texts.append({
                                "page_number": page_num + 1,
                                "text": page_content["cleaned_text"],
                                "char_count": len(page_content["cleaned_text"]),
                                "blocks": page_content["blocks"]
                            })
                            total_chars += len(page_content["cleaned_text"])
                        else:
                            empty_pages += 1
                            logger.warning(f"第{page_num + 1}页未提取到文本内容")
                            page_texts.append({
                                "page_number": page_num + 1,
                                "text": "",
                                "char_count": 0,
                                "blocks": []
                            })
                    
                    # 合并结构化内容为完整文本
                    full_text = self._merge_structured_content(structured_content)
                    
                    logger.info(f"PDF处理完成 - 总页数: {len(doc)}, 有效页数: {len(doc) - empty_pages}, 总字符数: {total_chars}")
                    
                    # 检查是否提取到有效内容
                    if total_chars < 100:
                        error_msg = f"PDF文档可能是扫描版或无有效文本内容，仅提取到 {total_chars} 个字符，空页数: {empty_pages}/{len(doc)}"
                        logger.error(error_msg)
                        return {
                            "metadata": metadata,
                            "full_text": full_text,
                            "page_texts": page_texts,
                            "structured_content": structured_content,
                            "success": False,
                            "error": error_msg
                        }
                    
                    return {
                        "metadata": metadata,
                        "full_text": full_text,
                        "page_texts": page_texts,
                        "structured_content": structured_content,
                        "success": True,
                        "error": None
                    }
                    
            except fitz.fitz.FileDataError as e:
                return {"success": False, "error": f"PDF文件数据错误: {str(e)}"}
            except fitz.fitz.FileNotFoundError as e:
                return {"success": False, "error": f"PDF文件未找到: {str(e)}"}
            except Exception as e:
                if "broken document" in str(e).lower():
                    return {"success": False, "error": f"PDF文件损坏或格式错误: {str(e)}"}
                else:
                    return {"success": False, "error": f"PDF处理异常: {str(e)}"}
                
        except Exception as e:
            logger.error(f"PDF文本提取失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_page_content_enhanced(self, page, page_num: int) -> Dict:
        """增强的页面内容提取"""
        try:
            # 获取结构化文本数据
            text_dict = page.get_text("dict")
            
            if not text_dict or "blocks" not in text_dict:
                return {"success": False, "blocks": [], "cleaned_text": ""}
            
            content_blocks = []
            page_text_parts = []
            
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                
                block_text = ""
                font_sizes = []
                is_bold = False
                
                for line in block["lines"]:
                    line_text = ""
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            line_text += text + " "
                            font_sizes.append(span.get("size", 12))
                            # 检查是否为粗体
                            font_flags = span.get("flags", 0)
                            if font_flags & 2**4:  # 粗体标志
                                is_bold = True
                    
                    if line_text.strip():
                        block_text += line_text.strip() + "\n"
                
                if block_text.strip():
                    # 分析文本块类型
                    avg_font_size = np.mean(font_sizes) if font_sizes else 12
                    block_type = self._classify_text_block(
                        block_text.strip(), 
                        avg_font_size, 
                        is_bold,
                        block.get("bbox", [0, 0, 0, 0])
                    )
                    
                    block_info = {
                        "page": page_num,
                        "type": block_type,
                        "text": block_text.strip(),
                        "font_size": avg_font_size,
                        "is_bold": is_bold,
                        "bbox": block.get("bbox", [])
                    }
                    
                    content_blocks.append(block_info)
                    
                    # 根据类型格式化文本
                    formatted_text = self._format_block_text(block_info)
                    page_text_parts.append(formatted_text)
            
            # 合并页面文本
            cleaned_text = self._clean_page_text("\n".join(page_text_parts))
            
            return {
                "success": True,
                "blocks": content_blocks,
                "cleaned_text": cleaned_text
            }
            
        except Exception as e:
            logger.error(f"页面内容提取失败: {e}")
            return {"success": False, "blocks": [], "cleaned_text": ""}
    
    def _classify_text_block(self, text: str, font_size: float, is_bold: bool, bbox: List) -> str:
        """分类文本块类型"""
        text_clean = text.strip()
        
        # 标题检测
        if (font_size > 14 or is_bold or 
            len(text_clean) < 100 or 
            re.match(r'^[\d\.\s]*[一二三四五六七八九十]+[、\.]', text_clean) or
            re.match(r'^\d+[\.\s]', text_clean) or
            re.match(r'^第[一二三四五六七八九十\d]+[章节部分]', text_clean)):
            return "heading"
        
        # 列表检测
        if (re.match(r'^[\s]*[•\-\*\d+\)\(]', text_clean) or
            '•' in text_clean or 
            text_clean.count('\n') > 2 and 
            any(line.strip().startswith(('•', '-', '*', '(', ')')) for line in text_clean.split('\n'))):
            return "list"
        
        # 表格检测
        if ('\t' in text_clean or 
            text_clean.count('|') > 2 or
            re.search(r'\d+\s+\d+\s+\d+', text_clean)):
            return "table"
        
        # 引用或代码检测
        if (text_clean.startswith('"') and text_clean.endswith('"') or
            text_clean.count('```') >= 2 or
            re.match(r'^\s*[>\|]', text_clean)):
            return "quote"
        
        return "paragraph"
    
    def _format_block_text(self, block_info: Dict) -> str:
        """根据块类型格式化文本"""
        text = block_info["text"]
        block_type = block_info["type"]
        
        if block_type == "heading":
            return f"\n\n### {text}\n"
        elif block_type == "list":
            return f"\n{text}\n"
        elif block_type == "table":
            return f"\n【表格内容】\n{text}\n"
        elif block_type == "quote":
            return f"\n> {text}\n"
        else:
            return f"\n{text}\n"
    
    def _merge_structured_content(self, structured_content: List[Dict]) -> str:
        """合并结构化内容"""
        merged_parts = []
        current_section = ""
        
        for block in structured_content:
            formatted_text = self._format_block_text(block)
            
            # 避免重复的页码标识
            if not re.match(r'^第\d+页', formatted_text.strip()):
                merged_parts.append(formatted_text)
        
        full_text = "".join(merged_parts)
        return self._final_text_cleanup(full_text)
    
    def _clean_page_text(self, text: str) -> str:
        """清理页面文本"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 修复断行问题
        text = re.sub(r'([a-zA-Z\u4e00-\u9fff])-\s*\n\s*([a-zA-Z\u4e00-\u9fff])', r'\1\2', text)
        
        # 移除页码等
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过纯数字页码、过短内容
            if (re.match(r'^\d+$', line) or 
                len(line) < 3 or
                re.match(r'^第\s*\d+\s*页', line) or
                line in ['', ' ']):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _final_text_cleanup(self, text: str) -> str:
        """最终文本清理"""
        # 规范化换行
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # 规范化空格
        text = re.sub(r'[ \t]+', ' ', text)
        # 移除行首行尾空格
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(line for line in lines if line)
        
        return text.strip()

    def split_text_into_chunks(self, text: str) -> List[Dict[str, any]]:
        """智能文本分块 - 优化版（降低过滤阈值）"""
        try:
            if not text or len(text.strip()) < 10:
                logger.warning(f"输入文本过短或为空，无法有效分块。文本长度: {len(text)}")
                return []
            
            # 1. 使用更温和的分块策略
            chunks = self._balanced_chunking(text)
            
            # 2. 处理和增强分块
            processed_chunks = []
            skipped_short = 0
            skipped_low_quality = 0
            
            for i, chunk in enumerate(chunks):
                chunk_content = chunk.strip()
                
                # 降低最小长度阈值：从50降到20
                if len(chunk_content) < 20:
                    skipped_short += 1
                    logger.debug(f"跳过过短的文本块 {i}: {chunk_content[:30]}")
                    continue
                
                # 计算文本质量分数
                quality_score = self._calculate_text_quality(chunk_content)
                
                # 降低质量阈值：从默认过滤改为只过滤极低质量的内容
                if quality_score < 0.2:
                    skipped_low_quality += 1
                    logger.debug(f"跳过低质量文本块 {i}: 质量分数={quality_score:.3f}")
                    continue
                
                # 生成块的唯一ID
                chunk_id = hashlib.md5(f"{chunk}_{i}".encode()).hexdigest()
                
                # 提取关键词和生成摘要
                keywords = self._extract_chunk_keywords(chunk_content)
                summary = self._generate_chunk_summary(chunk_content)
                
                chunk_data = {
                    "chunk_id": chunk_id,
                    "content": chunk_content,
                    "chunk_index": len(processed_chunks),
                    "chunk_length": len(chunk_content),
                    "keywords": keywords,
                    "summary": summary,
                    "quality_score": quality_score
                }
                
                processed_chunks.append(chunk_data)
            
            logger.info(f"智能分块完成 - 原始块数: {len(chunks)}, 有效块数: {len(processed_chunks)}, 跳过短块: {skipped_short}, 跳过低质量块: {skipped_low_quality}")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"文本分块失败: {str(e)}")
            return []

    def _balanced_chunking(self, text: str) -> List[str]:
        """平衡的分块策略 - 结合语义分块和固定分块"""
        chunks = []
        
        # 首先尝试语义分块
        semantic_chunks = self._semantic_chunking(text)
        
        # 如果语义分块产生的块太多或太小，降级到固定分块
        if len(semantic_chunks) > len(text) / 200:  # 平均每块小于200字符
            logger.info("语义分块产生过多小块，使用固定分块策略")
            chunks = self.text_splitter.split_text(text)
        else:
            # 对过长的语义块进行进一步分割
            for chunk in semantic_chunks:
                if len(chunk) <= self.chunk_size:
                    chunks.append(chunk)
                else:
                    sub_chunks = self.text_splitter.split_text(chunk)
                    chunks.extend(sub_chunks)
        
        return chunks

    def _semantic_chunking(self, text: str) -> List[str]:
        """优化的语义分块"""
        chunks = []
        
        # 按标题分段（更宽松的标题识别）
        sections = re.split(r'\n\s*#{1,3}\s*', text)  # 支持多级标题
        
        for section in sections:
            if not section.strip():
                continue
            
            # 每个section按段落进一步分割
            paragraphs = re.split(r'\n\s*\n\s*', section)
            
            current_chunk = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # 调整合并策略：允许更大的块
                potential_chunk = current_chunk + "\n\n" + para if current_chunk else para
                
                # 如果超过最大长度，保存当前块并开始新块
                if len(potential_chunk) > self.chunk_size * 1.2:  # 允许20%的超出
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk = potential_chunk
            
            # 保存最后一个块
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_chunk_keywords(self, text: str) -> List[str]:
        """提取文本块关键词"""
        try:
            # 使用jieba提取关键词
            keywords = jieba.analyse.extract_tags(text, topK=8, withWeight=False)
            return keywords
        except Exception as e:
            logger.warning(f"关键词提取失败: {e}")
            return []
    
    def _generate_chunk_summary(self, text: str) -> str:
        """生成文本块摘要"""
        try:
            # 提取第一个完整句子作为摘要
            sentences = re.split(r'[。！？]', text)
            if sentences and sentences[0].strip():
                summary = sentences[0].strip()
                return summary[:100] + "..." if len(summary) > 100 else summary
            
            # 如果没有句子，返回前100个字符
            return text[:100] + "..." if len(text) > 100 else text
            
        except Exception as e:
            logger.warning(f"摘要生成失败: {e}")
            return text[:50] + "..." if len(text) > 50 else text
    
    def _calculate_text_quality(self, text: str) -> float:
        """优化的文本质量分数计算"""
        try:
            score = 0.5  # 基础分数从1.0降到0.5，更宽松
            
            # 长度评分（更宽松）
            text_len = len(text)
            if text_len >= 30:  # 降低最小长度要求
                if text_len < 100:
                    score += 0.2
                elif text_len <= 800:
                    score += 0.3
                elif text_len <= 1500:
                    score += 0.2
                else:
                    score += 0.1
            
            # 中文字符比例（更宽松）
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            if text:
                chinese_ratio = chinese_chars / len(text)
                if chinese_ratio >= 0.1:  # 从0.3降到0.1
                    score += 0.2
            
            # 信息密度（更宽松）
            if text:
                char_diversity = len(set(text)) / len(text)
                if char_diversity >= 0.05:  # 从0.1降到0.05
                    score += 0.2
            
            # 结构完整性（更宽松）
            complete_sentences = len(re.findall(r'[。！？.!?]', text))
            if complete_sentences > 0 or len(text) <= 50:  # 短文本不要求完整句子
                score += 0.1
            
            # 特殊内容识别（加分项）
            if any(keyword in text for keyword in ['表', '图', '公式', '定义', '定理', '结论']):
                score += 0.1
            
            return min(max(score, 0.1), 1.0)
            
        except Exception as e:
            logger.warning(f"质量分数计算失败: {e}")
            return 0.5

    def process_document(self, document_id: str, storage_type: str, file_path: str, cos_object_key: str = None) -> Dict[str, any]:
        try:
            # 获取文件内容
            file_content = file_storage_manager.get_file_content(
                document_id=document_id,
                storage_type=storage_type,
                file_path=file_path,
                cos_object_key=cos_object_key
            )
            
            if not file_content:
                return {"success": False, "error": "无法获取文件内容"}
            
            # 验证文件大小
            if len(file_content) < 1024:  # PDF文件至少应该有1KB
                return {"success": False, "error": "文件内容过小，可能损坏"}
            
            # 验证PDF文件头
            if not file_content.startswith(b'%PDF-'):
                return {"success": False, "error": "文件不是有效的PDF格式"}
            
            # 创建临时文件时确保完全写入
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()  # 确保数据写入磁盘
                os.fsync(temp_file.fileno())  # 强制同步到磁盘
                temp_file_path = temp_file.name
            
            # 验证临时文件
            if not os.path.exists(temp_file_path):
                return {"success": False, "error": "临时文件创建失败"}
            
            temp_file_size = os.path.getsize(temp_file_path)
            if temp_file_size != len(file_content):
                return {"success": False, "error": f"临时文件大小不匹配：期望{len(file_content)}，实际{temp_file_size}"}
            
            try:
                # 提取文本
                extraction_result = self.extract_text_from_pdf(temp_file_path)
                
                if not extraction_result["success"]:
                    return extraction_result
                
                # 智能分块
                chunks = self.split_text_into_chunks(extraction_result["full_text"])
                
                # 计算处理质量指标
                quality_metrics = self._calculate_processing_quality(
                    extraction_result, chunks
                )
                
                return {
                    "metadata": extraction_result["metadata"],
                    "full_text": extraction_result["full_text"],
                    "page_texts": extraction_result["page_texts"],
                    "structured_content": extraction_result.get("structured_content", []),
                    "chunks": chunks,
                    "chunk_count": len(chunks),
                    "quality_metrics": quality_metrics,
                    "success": True,
                    "error": None
                }
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"文档处理失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_processing_quality(self, extraction_result: Dict, chunks: List[Dict]) -> Dict:
        """计算处理质量指标"""
        try:
            metrics = {
                "total_text_length": len(extraction_result["full_text"]),
                "valid_pages": sum(1 for page in extraction_result["page_texts"] if page["char_count"] > 0),
                "total_pages": len(extraction_result["page_texts"]),
                "chunk_count": len(chunks),
                "avg_chunk_length": np.mean([chunk["chunk_length"] for chunk in chunks]) if chunks else 0,
                "avg_quality_score": np.mean([chunk.get("quality_score", 0.5) for chunk in chunks]) if chunks else 0,
                "keywords_coverage": len(set(kw for chunk in chunks for kw in chunk.get("keywords", [])))
            }
            
            # 计算整体质量分数
            overall_quality = 0.0
            if metrics["total_pages"] > 0:
                page_coverage = metrics["valid_pages"] / metrics["total_pages"]
                overall_quality += page_coverage * 0.3
            
            if metrics["total_text_length"] > 500:
                overall_quality += 0.3
            
            overall_quality += metrics["avg_quality_score"] * 0.4
            
            metrics["overall_quality"] = min(overall_quality, 1.0)
            
            return metrics
            
        except Exception as e:
            logger.warning(f"质量指标计算失败: {e}")
            return {"overall_quality": 0.5} 