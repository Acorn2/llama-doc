import fitz  # PyMuPDF
import os
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFDebugAnalyzer:
    """PDF内容提取调试分析器 - 专门用于排查PyMuPDF提取问题"""
    
    def __init__(self):
        self.debug_results = {}
    
    def comprehensive_analysis(self, file_path: str, max_pages: int = 20) -> Dict[str, Any]:
        """全面分析PDF文件的内容提取情况
        
        Args:
            file_path: PDF文件路径
            max_pages: 最大分析页数，默认20页（0表示分析所有页面）
        """
        print(f"\n{'='*60}")
        print(f"开始分析PDF文件: {os.path.basename(file_path)}")
        if max_pages > 0:
            print(f"分析范围: 前{max_pages}页")
        else:
            print(f"分析范围: 全部页面")
        print(f"{'='*60}")
        
        results = {
            "file_info": {},
            "basic_extraction": {},
            "method_comparison": {},
            "page_analysis": [],
            "page_contents": [],  # 新增：详细的页面内容
            "extracted_texts": {},  # 新增：每页的完整提取文本
            "content_statistics": {},
            "potential_issues": [],
            "recommendations": []
        }
        
        try:
            with fitz.open(file_path) as doc:
                # 确定分析页面范围
                total_pages = len(doc)
                analyze_pages = total_pages if max_pages == 0 else min(max_pages, total_pages)
                
                print(f"文档总页数: {total_pages}, 分析页数: {analyze_pages}")
                
                # 1. 基本文件信息
                results["file_info"] = self._analyze_file_info(doc, file_path)
                results["file_info"]["analyze_pages"] = analyze_pages
                results["file_info"]["total_pages"] = total_pages
                
                # 2. 基础提取测试
                results["basic_extraction"] = self._test_basic_extraction(doc, analyze_pages)
                
                # 3. 多种提取方法对比（使用第一页作为样本）
                results["method_comparison"] = self._compare_extraction_methods(doc)
                
                # 4. 逐页详细分析（增强版）
                page_analysis, page_contents, extracted_texts = self._analyze_pages_with_content(doc, analyze_pages)
                results["page_analysis"] = page_analysis
                results["page_contents"] = page_contents
                results["extracted_texts"] = extracted_texts
                
                # 5. 内容统计分析
                results["content_statistics"] = self._calculate_content_statistics(results["page_analysis"])
                
                # 6. 问题诊断
                results["potential_issues"] = self._diagnose_potential_issues(results)
                
                # 7. 改进建议
                results["recommendations"] = self._generate_recommendations(results)
                
                # 8. 生成详细报告
                self._print_analysis_report(results)
                
                return results
                
        except Exception as e:
            logger.error(f"PDF分析失败: {str(e)}")
            print(f"❌ PDF分析失败: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_file_info(self, doc, file_path: str) -> Dict:
        """分析文件基础信息"""
        file_info = {
            "file_path": file_path,
            "file_size_mb": round(os.path.getsize(file_path) / (1024*1024), 2),
            "total_pages": len(doc),
            "is_password_protected": doc.needs_pass,
            "metadata": {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", "")
            }
        }
        
        print(f"\n📄 文件信息:")
        print(f"   文件大小: {file_info['file_size_mb']} MB")
        print(f"   总页数: {file_info['total_pages']}")
        print(f"   是否加密: {'是' if file_info['is_password_protected'] else '否'}")
        if file_info['metadata']['title']:
            print(f"   文档标题: {file_info['metadata']['title']}")
        
        return file_info
    
    def _test_basic_extraction(self, doc, max_pages: int) -> Dict:
        """测试基础文本提取"""
        print(f"\n🔍 基础提取测试:")
        
        basic_results = {}
        analyze_pages = min(max_pages, len(doc))
        
        # 方法1: 简单文本提取
        try:
            simple_text = ""
            for page_num in range(analyze_pages):
                page = doc[page_num]
                simple_text += page.get_text()
            
            basic_results["simple_extraction"] = {
                "success": True,
                "total_chars": len(simple_text),
                "pages_analyzed": analyze_pages,
                "preview": simple_text[:200] + "..." if len(simple_text) > 200 else simple_text
            }
            print(f"   ✅ 简单提取: {len(simple_text)} 字符 ({analyze_pages}页)")
            
        except Exception as e:
            basic_results["simple_extraction"] = {"success": False, "error": str(e)}
            print(f"   ❌ 简单提取失败: {str(e)}")
        
        # 方法2: 布局保持提取
        try:
            layout_text = ""
            for page_num in range(analyze_pages):
                page = doc[page_num]
                layout_text += page.get_text("text")
            
            basic_results["layout_extraction"] = {
                "success": True,
                "total_chars": len(layout_text),
                "pages_analyzed": analyze_pages,
                "preview": layout_text[:200] + "..." if len(layout_text) > 200 else layout_text
            }
            print(f"   ✅ 布局提取: {len(layout_text)} 字符 ({analyze_pages}页)")
            
        except Exception as e:
            basic_results["layout_extraction"] = {"success": False, "error": str(e)}
            print(f"   ❌ 布局提取失败: {str(e)}")
        
        return basic_results
    
    def _compare_extraction_methods(self, doc) -> Dict:
        """对比不同提取方法的效果"""
        print(f"\n🔬 多种提取方法对比:")
        
        methods = {}
        
        # 测试所有页面的第一页作为样本
        if len(doc) > 0:
            sample_page = doc[0]
            
            # 方法1: get_text() - 纯文本
            try:
                text1 = sample_page.get_text()
                methods["pure_text"] = {
                    "method": "get_text()",
                    "chars": len(text1),
                    "lines": text1.count('\n'),
                    "preview": text1[:150] + "..." if len(text1) > 150 else text1
                }
                line_count = text1.count('\n')
                print(f"   方法1 - 纯文本: {len(text1)} 字符, {line_count} 行")
            except Exception as e:
                methods["pure_text"] = {"error": str(e)}
            
            # 方法2: get_text("text") - 布局文本
            try:
                text2 = sample_page.get_text("text")
                methods["layout_text"] = {
                    "method": "get_text('text')",
                    "chars": len(text2),
                    "lines": text2.count('\n'),
                    "preview": text2[:150] + "..." if len(text2) > 150 else text2
                }
                line_count2 = text2.count('\n')
                print(f"   方法2 - 布局文本: {len(text2)} 字符, {line_count2} 行")
            except Exception as e:
                methods["layout_text"] = {"error": str(e)}
            
            # 方法3: get_text("blocks") - 文本块
            try:
                blocks = sample_page.get_text("blocks")
                total_chars = sum(len(block[4]) for block in blocks if len(block) > 4)
                methods["blocks"] = {
                    "method": "get_text('blocks')",
                    "block_count": len(blocks),
                    "total_chars": total_chars,
                    "first_block": blocks[0][4][:100] + "..." if blocks and len(blocks[0]) > 4 else "无内容"
                }
                print(f"   方法3 - 文本块: {len(blocks)} 块, {total_chars} 字符")
            except Exception as e:
                methods["blocks"] = {"error": str(e)}
            
            # 方法4: get_text("dict") - 结构化数据（当前方法）
            try:
                text_dict = sample_page.get_text("dict")
                block_count = len(text_dict.get("blocks", []))
                
                # 统计总字符数
                total_chars = 0
                for block in text_dict.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            total_chars += len(span.get("text", ""))
                
                methods["structured_dict"] = {
                    "method": "get_text('dict')",
                    "block_count": block_count,
                    "total_chars": total_chars,
                    "has_font_info": True
                }
                print(f"   方法4 - 结构化字典: {block_count} 块, {total_chars} 字符")
            except Exception as e:
                methods["structured_dict"] = {"error": str(e)}
            
            # 方法5: get_text("html") - HTML格式
            try:
                html_text = sample_page.get_text("html")
                # 移除HTML标签来计算纯文本长度
                import re
                clean_text = re.sub(r'<[^>]+>', '', html_text)
                methods["html"] = {
                    "method": "get_text('html')",
                    "html_length": len(html_text),
                    "text_length": len(clean_text),
                    "has_formatting": True
                }
                print(f"   方法5 - HTML格式: HTML {len(html_text)} 字符, 纯文本 {len(clean_text)} 字符")
            except Exception as e:
                methods["html"] = {"error": str(e)}
        
        return methods
    
    def _analyze_pages_with_content(self, doc, max_pages: int) -> tuple[List[Dict], List[Dict], Dict]:
        """详细分析每一页的内容并保存完整文本"""
        print(f"\n📊 逐页内容分析:")
        
        page_analyses = []
        page_contents = []  # 详细的页面内容结构
        extracted_texts = {}  # 每页的完整提取文本
        
        analyze_pages = min(max_pages, len(doc))
        
        for page_num in range(analyze_pages):
            page = doc[page_num]
            
            analysis = {
                "page_number": page_num + 1,
                "extraction_methods": {},
                "content_types": {},
                "quality_metrics": {}
            }
            
            page_content = {
                "page_number": page_num + 1,
                "text_blocks": [],
                "images": [],
                "tables": [],
                "fonts_used": [],
                "bbox_info": {}
            }
            
            # 测试多种提取方法
            try:
                # 1. 纯文本提取
                simple_text = page.get_text()
                newline_count = simple_text.count('\n')
                analysis["extraction_methods"]["simple"] = {
                    "chars": len(simple_text),
                    "non_whitespace_chars": len(simple_text.replace(' ', '').replace('\n', '')),
                    "lines": newline_count
                }
                
                # 保存完整提取文本
                extracted_texts[f"page_{page_num + 1}"] = {
                    "simple_text": simple_text,
                    "simple_text_preview": simple_text[:500] + "..." if len(simple_text) > 500 else simple_text
                }
                
                # 2. 结构化提取
                text_dict = page.get_text("dict")
                
                # 统计结构化信息
                blocks = text_dict.get("blocks", [])
                text_blocks = [b for b in blocks if "lines" in b]
                image_blocks = [b for b in blocks if "lines" not in b]
                
                # 详细保存文本块信息
                for i, block in enumerate(text_blocks):
                    block_info = {
                        "block_index": i,
                        "bbox": block.get("bbox", []),
                        "block_type": block.get("type", 0),
                        "lines": []
                    }
                    
                    block_text = ""
                    for line in block.get("lines", []):
                        line_info = {
                            "bbox": line.get("bbox", []),
                            "wmode": line.get("wmode", 0),
                            "dir": line.get("dir", []),
                            "spans": []
                        }
                        
                        line_text = ""
                        for span in line.get("spans", []):
                            span_info = {
                                "text": span.get("text", ""),
                                "font": span.get("font", ""),
                                "size": span.get("size", 12),
                                "flags": span.get("flags", 0),
                                "color": span.get("color", 0),
                                "bbox": span.get("bbox", [])
                            }
                            line_info["spans"].append(span_info)
                            line_text += span.get("text", "")
                        
                        line_info["text"] = line_text
                        block_info["lines"].append(line_info)
                        block_text += line_text + "\n"
                    
                    block_info["text"] = block_text.strip()
                    page_content["text_blocks"].append(block_info)
                
                # 保存图片块信息
                for i, img_block in enumerate(image_blocks):
                    img_info = {
                        "block_index": i,
                        "bbox": img_block.get("bbox", []),
                        "block_type": img_block.get("type", 1),
                        "width": img_block.get("width", 0),
                        "height": img_block.get("height", 0)
                    }
                    page_content["images"].append(img_info)
                
                # 统计字体信息
                font_sizes = []
                font_names = []
                total_spans = 0
                
                for block in text_blocks:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            total_spans += 1
                            font_size = span.get("size", 12)
                            font_name = span.get("font", "")
                            font_sizes.append(font_size)
                            font_names.append(font_name)
                
                unique_fonts = list(set(font_names)) if font_names else []
                page_content["fonts_used"] = [
                    {"font": font, "count": font_names.count(font)} 
                    for font in unique_fonts
                ]
                
                analysis["extraction_methods"]["structured"] = {
                    "total_blocks": len(blocks),
                    "text_blocks": len(text_blocks),
                    "image_blocks": len(image_blocks),
                    "total_spans": total_spans,
                    "unique_fonts": len(unique_fonts),
                    "font_size_range": [min(font_sizes), max(font_sizes)] if font_sizes else [0, 0]
                }
                
                # 3. 内容类型分析
                chinese_chars = len([c for c in simple_text if '\u4e00' <= c <= '\u9fff'])
                english_chars = len([c for c in simple_text if c.isalpha() and ord(c) < 128])
                digit_chars = len([c for c in simple_text if c.isdigit()])
                
                analysis["content_types"] = {
                    "chinese_chars": chinese_chars,
                    "english_chars": english_chars,
                    "digit_chars": digit_chars,
                    "total_printable": chinese_chars + english_chars + digit_chars,
                    "chinese_ratio": chinese_chars / max(len(simple_text), 1)
                }
                
                # 4. 质量指标
                analysis["quality_metrics"] = {
                    "is_likely_scanned": analysis["content_types"]["total_printable"] < 50,
                    "has_structured_content": len(text_blocks) > 0,
                    "content_density": analysis["content_types"]["total_printable"] / max(len(simple_text), 1),
                    "extraction_success": len(simple_text) > 20
                }
                
                # 5. 页面边界信息
                page_content["bbox_info"] = {
                    "page_width": page.rect.width,
                    "page_height": page.rect.height,
                    "rotation": page.rotation
                }
                
            except Exception as e:
                analysis["error"] = str(e)
                page_content["error"] = str(e)
            
            page_analyses.append(analysis)
            page_contents.append(page_content)
            
            # 打印页面分析结果
            if "error" not in analysis:
                simple_chars = analysis["extraction_methods"]["simple"]["chars"]
                printable_chars = analysis["content_types"]["total_printable"]
                status = "✅" if analysis["quality_metrics"]["extraction_success"] else "❌"
                print(f"   第{page_num + 1}页: {status} {simple_chars}字符 ({printable_chars}有效)")
            else:
                print(f"   第{page_num + 1}页: ❌ 分析失败 - {analysis['error']}")
        
        if len(doc) > analyze_pages:
            print(f"   ... (共{len(doc)}页，分析了前{analyze_pages}页)")
        
        return page_analyses, page_contents, extracted_texts
    
    def _calculate_content_statistics(self, page_analyses: List[Dict]) -> Dict:
        """计算内容统计信息"""
        stats = {
            "total_pages_analyzed": len(page_analyses),
            "successful_extractions": 0,
            "total_characters": 0,
            "total_printable_characters": 0,
            "empty_pages": 0,
            "low_content_pages": 0,
            "average_chars_per_page": 0,
            "content_quality_distribution": {"high": 0, "medium": 0, "low": 0}
        }
        
        for analysis in page_analyses:
            if "error" not in analysis and analysis["quality_metrics"]["extraction_success"]:
                stats["successful_extractions"] += 1
                
                chars = analysis["extraction_methods"]["simple"]["chars"]
                printable = analysis["content_types"]["total_printable"]
                
                stats["total_characters"] += chars
                stats["total_printable_characters"] += printable
                
                if printable == 0:
                    stats["empty_pages"] += 1
                elif printable < 50:
                    stats["low_content_pages"] += 1
                
                # 质量分类
                density = analysis["quality_metrics"]["content_density"]
                if density > 0.3 and printable > 100:
                    stats["content_quality_distribution"]["high"] += 1
                elif density > 0.1 and printable > 20:
                    stats["content_quality_distribution"]["medium"] += 1
                else:
                    stats["content_quality_distribution"]["low"] += 1
        
        if stats["successful_extractions"] > 0:
            stats["average_chars_per_page"] = stats["total_characters"] / stats["successful_extractions"]
        
        return stats
    
    def _diagnose_potential_issues(self, results: Dict) -> List[str]:
        """诊断潜在问题"""
        issues = []
        
        stats = results["content_statistics"]
        
        # 检查整体提取成功率
        if stats["successful_extractions"] / max(stats["total_pages_analyzed"], 1) < 0.8:
            issues.append("⚠️  提取成功率偏低，可能存在页面格式问题")
        
        # 检查空页比例
        if stats["empty_pages"] > 0:
            issues.append(f"⚠️  发现 {stats['empty_pages']} 个空页，可能是扫描版或图片页")
        
        # 检查内容密度
        if stats["total_printable_characters"] / max(stats["total_characters"], 1) < 0.1:
            issues.append("⚠️  有效字符比例过低，可能包含大量格式字符或空白")
        
        # 检查平均页面内容
        if stats["average_chars_per_page"] < 200:
            issues.append("⚠️  平均每页字符数过少，可能是图片为主的文档")
        
        # 检查质量分布
        quality_dist = stats["content_quality_distribution"]
        if quality_dist["low"] > quality_dist["high"] + quality_dist["medium"]:
            issues.append("⚠️  低质量页面过多，建议检查文档类型和提取策略")
        
        # 检查方法对比
        methods = results.get("method_comparison", {})
        if "structured_dict" in methods and "pure_text" in methods:
            struct_chars = methods["structured_dict"].get("total_chars", 0)
            pure_chars = methods["pure_text"].get("chars", 0)
            
            if struct_chars < pure_chars * 0.8:
                issues.append("⚠️  结构化提取丢失了较多内容，建议优化提取逻辑")
        
        return issues
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        issues = results["potential_issues"]
        stats = results["content_statistics"]
        
        # 基于问题生成建议
        if any("空页" in issue for issue in issues):
            recommendations.append("💡 建议增加OCR处理能力，处理扫描版PDF")
        
        if any("字符数过少" in issue for issue in issues):
            recommendations.append("💡 建议检查是否为图片类文档，考虑图像文本识别")
        
        if any("结构化提取丢失" in issue for issue in issues):
            recommendations.append("💡 建议优化文本块合并逻辑，减少内容丢失")
        
        if stats["content_quality_distribution"]["low"] > 3:
            recommendations.append("💡 建议调整质量过滤阈值，避免过度过滤")
        
        # 通用建议
        if len(recommendations) == 0:
            recommendations.append("✅ 文档提取质量良好，建议保持当前提取策略")
        
        recommendations.append("💡 建议定期使用不同类型PDF文档测试提取效果")
        
        return recommendations
    
    def _print_analysis_report(self, results: Dict):
        """打印详细分析报告"""
        print(f"\n{'='*60}")
        print(f"📋 PDF内容提取分析报告")
        print(f"{'='*60}")
        
        # 文件概况
        file_info = results["file_info"]
        print(f"\n📄 文件概况:")
        print(f"   文件大小: {file_info['file_size_mb']} MB")
        print(f"   总页数: {file_info['total_pages']}")
        print(f"   分析页数: {file_info.get('analyze_pages', '未知')}")
        
        # 提取统计
        stats = results["content_statistics"]
        print(f"\n📊 提取统计:")
        print(f"   成功提取页数: {stats['successful_extractions']}/{stats['total_pages_analyzed']}")
        print(f"   总字符数: {stats['total_characters']:,}")
        print(f"   有效字符数: {stats['total_printable_characters']:,}")
        print(f"   平均每页字符: {stats['average_chars_per_page']:.0f}")
        print(f"   空页数: {stats['empty_pages']}")
        
        # 质量分布
        quality = stats["content_quality_distribution"]
        print(f"\n🎯 内容质量分布:")
        print(f"   高质量页面: {quality['high']}")
        print(f"   中等质量页面: {quality['medium']}")
        print(f"   低质量页面: {quality['low']}")
        
        # 问题诊断
        issues = results["potential_issues"]
        if issues:
            print(f"\n⚠️  发现的问题:")
            for issue in issues:
                print(f"   {issue}")
        
        # 改进建议
        recommendations = results["recommendations"]
        print(f"\n💡 改进建议:")
        for rec in recommendations:
            print(f"   {rec}")
        
        print(f"\n{'='*60}")
        print(f"分析完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
    
    def save_detailed_report(self, results: Dict, output_path: str):
        """保存详细分析报告到文件"""
        try:
            # 添加分析时间
            results["analysis_timestamp"] = datetime.now().isoformat()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 详细报告已保存到: {output_path}")
            
            # 额外保存一个纯文本版本，方便查看提取的内容
            text_output_path = output_path.replace('.json', '_extracted_text.txt')
            self._save_extracted_text_file(results, text_output_path)
            
        except Exception as e:
            print(f"❌ 保存报告失败: {str(e)}")
    
    def _save_extracted_text_file(self, results: Dict, output_path: str):
        """保存提取的纯文本内容到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("PDF提取文本内容详细报告\n")
                f.write("="*80 + "\n\n")
                
                # 基本信息
                file_info = results.get("file_info", {})
                f.write(f"文件路径: {file_info.get('file_path', '未知')}\n")
                f.write(f"文件大小: {file_info.get('file_size_mb', 0)} MB\n")
                f.write(f"总页数: {file_info.get('total_pages', 0)}\n")
                f.write(f"分析页数: {file_info.get('analyze_pages', 0)}\n\n")
                
                # 逐页内容
                extracted_texts = results.get("extracted_texts", {})
                page_contents = results.get("page_contents", [])
                
                for page_content in page_contents:
                    page_num = page_content["page_number"]
                    f.write(f"\n{'='*60}\n")
                    f.write(f"第 {page_num} 页内容\n")
                    f.write(f"{'='*60}\n")
                    
                    # 页面基本信息
                    if "bbox_info" in page_content:
                        bbox = page_content["bbox_info"]
                        f.write(f"页面尺寸: {bbox.get('page_width', 0):.1f} x {bbox.get('page_height', 0):.1f}\n")
                        f.write(f"页面旋转: {bbox.get('rotation', 0)}度\n")
                    
                    # 文本块信息
                    text_blocks = page_content.get("text_blocks", [])
                    f.write(f"文本块数量: {len(text_blocks)}\n")
                    
                    # 图片信息
                    images = page_content.get("images", [])
                    f.write(f"图片块数量: {len(images)}\n")
                    
                    # 字体信息
                    fonts = page_content.get("fonts_used", [])
                    if fonts:
                        f.write(f"使用字体: {', '.join([font['font'] for font in fonts[:5]])}\n")
                    
                    f.write(f"\n--- 提取的完整文本 ---\n")
                    
                    # 提取的文本内容
                    page_key = f"page_{page_num}"
                    if page_key in extracted_texts:
                        simple_text = extracted_texts[page_key].get("simple_text", "")
                        if simple_text.strip():
                            f.write(simple_text)
                            f.write(f"\n\n--- 字符统计 ---\n")
                            f.write(f"总字符数: {len(simple_text)}\n")
                            
                            # 修复：先计算非空白字符数，再写入
                            non_whitespace_count = len(simple_text.replace(' ', '').replace('\n', '').replace('\t', ''))
                            f.write(f"非空白字符数: {non_whitespace_count}\n")
                            
                            # 修复：先计算行数，再写入
                            line_count = simple_text.count('\n') + 1
                            f.write(f"行数: {line_count}\n")
                        else:
                            f.write("【此页无文本内容或提取失败】\n")
                    else:
                        f.write("【提取数据缺失】\n")
                    
                    # 详细的文本块内容
                    if text_blocks:
                        f.write(f"\n--- 结构化文本块详情 ---\n")
                        for i, block in enumerate(text_blocks):
                            f.write(f"\n文本块 {i+1}:\n")
                            f.write(f"位置: {block.get('bbox', [])}\n")
                            f.write(f"内容: {block.get('text', '').strip()}\n")
                            f.write("-" * 40 + "\n")
                
                # 总结信息
                f.write(f"\n{'='*80}\n")
                f.write(f"提取总结\n")
                f.write(f"{'='*80}\n")
                
                stats = results.get("content_statistics", {})
                f.write(f"成功提取页数: {stats.get('successful_extractions', 0)}/{stats.get('total_pages_analyzed', 0)}\n")
                f.write(f"总字符数: {stats.get('total_characters', 0):,}\n")
                f.write(f"有效字符数: {stats.get('total_printable_characters', 0):,}\n")
                f.write(f"平均每页字符数: {stats.get('average_chars_per_page', 0):.0f}\n")
                
                # 问题和建议
                issues = results.get("potential_issues", [])
                if issues:
                    f.write(f"\n发现的问题:\n")
                    for issue in issues:
                        f.write(f"- {issue}\n")
                
                recommendations = results.get("recommendations", [])
                if recommendations:
                    f.write(f"\n改进建议:\n")
                    for rec in recommendations:
                        f.write(f"- {rec}\n")
            
            print(f"💾 提取文本已保存到: {output_path}")
            
        except Exception as e:
            print(f"❌ 保存文本文件失败: {str(e)}")

# 快速使用函数
def analyze_pdf_extraction(pdf_path: str, save_report: bool = True, max_pages: int = 20):
    """快速分析PDF提取效果的入口函数
    
    Args:
        pdf_path: PDF文件路径
        save_report: 是否保存报告
        max_pages: 最大分析页数，0表示分析所有页面
    """
    analyzer = PDFDebugAnalyzer()
    results = analyzer.comprehensive_analysis(pdf_path, max_pages)
    
    if save_report and "error" not in results:
        report_path = pdf_path.replace('.pdf', '_detailed_extraction_analysis.json')
        analyzer.save_detailed_report(results, report_path)
    
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        analyze_pdf_extraction(pdf_path, max_pages=max_pages)
    else:
        print("用法: python pdf_debug_analyzer.py <PDF文件路径> [最大分析页数]")
        print("示例: python pdf_debug_analyzer.py document.pdf 20")
        print("      python pdf_debug_analyzer.py document.pdf 0  # 分析所有页面") 