#!/usr/bin/env python3
"""
PDF提取效果测试脚本 - 增强版
用法: python test_pdf_extraction.py [分析页数]
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.pdf_debug_analyzer import analyze_pdf_extraction
from app.core.document_processor import DocumentProcessor

def test_pdf_extraction(pdf_path: str, max_pages: int = 20):
    """测试PDF提取效果
    
    Args:
        pdf_path: PDF文件路径
        max_pages: 最大分析页数，0表示分析所有页面
    """
    
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在: {pdf_path}")
        return
    
    print(f"🔍 开始测试PDF提取效果")
    print(f"文件路径: {pdf_path}")
    if max_pages > 0:
        print(f"分析页数: 前{max_pages}页")
    else:
        print(f"分析页数: 全部页面")
    
    # 1. 使用增强的调试分析器进行详细分析
    print(f"\n{'='*50}")
    print(f"第一步: 详细提取分析")
    print(f"{'='*50}")
    
    debug_results = analyze_pdf_extraction(pdf_path, save_report=True, max_pages=max_pages)
    
    # 2. 使用当前系统的文档处理器
    print(f"\n{'='*50}")
    print(f"第二步: 当前系统提取测试")
    print(f"{'='*50}")
    
    try:
        processor = DocumentProcessor()
        processing_result = processor.extract_text_from_pdf(pdf_path)
        
        if processing_result["success"]:
            print(f"✅ 系统提取成功")
            print(f"   提取字符数: {len(processing_result['full_text']):,}")
            print(f"   处理页数: {len(processing_result['page_texts'])}")
            print(f"   结构化块数: {len(processing_result.get('structured_content', []))}")
            
            # 显示前200字符预览
            preview = processing_result['full_text'][:200].replace('\n', ' ')
            print(f"   内容预览: {preview}...")
            
            # 分块测试
            chunks = processor.split_text_into_chunks(processing_result['full_text'])
            print(f"   生成分块数: {len(chunks)}")
            if chunks:
                avg_chunk_size = sum(len(chunk['content']) for chunk in chunks) / len(chunks)
                print(f"   平均分块大小: {avg_chunk_size:.0f} 字符")
        else:
            print(f"❌ 系统提取失败: {processing_result.get('error', '未知错误')}")
    
    except Exception as e:
        print(f"❌ 系统提取异常: {str(e)}")
    
    # 3. 生成对比分析
    print(f"\n{'='*50}")
    print(f"第三步: 对比分析")
    print(f"{'='*50}")
    
    if "error" not in debug_results and "content_statistics" in debug_results:
        debug_stats = debug_results["content_statistics"]
        debug_chars = debug_stats["total_characters"]
        debug_pages = debug_stats["total_pages_analyzed"]
        
        if processing_result["success"]:
            system_chars = len(processing_result['full_text'])
            system_pages = len(processing_result['page_texts'])
            
            print(f"📊 字符数对比:")
            print(f"   调试分析器提取: {debug_chars:,} 字符 ({debug_pages}页)")
            print(f"   当前系统提取: {system_chars:,} 字符 ({system_pages}页)")
            
            if debug_pages > 0 and system_pages > 0:
                # 按页面平均比较
                debug_avg = debug_chars / debug_pages
                system_avg = system_chars / system_pages
                print(f"   平均每页字符数:")
                print(f"     调试分析器: {debug_avg:.0f} 字符/页")
                print(f"     当前系统: {system_avg:.0f} 字符/页")
                
                if debug_pages == system_pages:
                    # 同等页面数的直接比较
                    ratio = debug_chars / system_chars if system_chars > 0 else 0
                    print(f"   提取比例: {ratio:.2%}")
                    
                    if ratio < 0.8:
                        print(f"⚠️  当前系统提取字符数明显偏少，可能存在内容丢失")
                    elif ratio > 1.2:
                        print(f"⚠️  当前系统提取字符数偏多，可能包含重复或格式字符")
                    else:
                        print(f"✅ 提取字符数基本一致")
                else:
                    # 不同页面数的比较
                    print(f"ℹ️  分析页面数不同，无法直接比较总字符数")
                    avg_ratio = debug_avg / system_avg if system_avg > 0 else 0
                    print(f"   平均每页字符比例: {avg_ratio:.2%}")
    
    # 4. 输出详细报告位置
    print(f"\n{'='*50}")
    print(f"第四步: 详细报告")
    print(f"{'='*50}")
    
    if "error" not in debug_results:
        base_name = pdf_path.replace('.pdf', '')
        json_report = f"{base_name}_detailed_extraction_analysis.json"
        text_report = f"{base_name}_detailed_extraction_analysis_extracted_text.txt"
        
        print(f"📄 详细分析报告: {json_report}")
        print(f"📝 提取文本报告: {text_report}")
        print(f"\n💡 建议:")
        print(f"   1. 查看JSON报告了解详细的提取数据和分析结果")
        print(f"   2. 查看TXT报告检查具体的提取文本内容")
        print(f"   3. 重点关注空页、低质量页面和提取失败的页面")

if __name__ == "__main__":
    # 硬编码PDF文件路径进行测试
    pdf_path = "/Users/ankanghao/AiProjects/pdf-document-rag/backend/uploads/dff89c2d-c57a-4090-8d1a-b7d782c1b7aa.pdf"
    
    # 从命令行参数获取分析页数（可选）
    max_pages = 20  # 默认分析前20页
    if len(sys.argv) > 1:
        try:
            max_pages = int(sys.argv[1])
        except ValueError:
            print("⚠️  页数参数无效，使用默认值20")
    
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        print(f"❌ 指定的PDF文件不存在: {pdf_path}")
        print("请确认文件路径是否正确")
        sys.exit(1)
    
    print(f"🎯 使用硬编码的PDF文件路径进行测试")
    if max_pages == 0:
        print(f"📖 将分析所有页面（可能耗时较长）")
    else:
        print(f"📖 将分析前{max_pages}页")
    
    test_pdf_extraction(pdf_path, max_pages)
    
    print(f"\n🎉 测试完成！")
    print(f"💡 使用方法:")
    print(f"   python scripts/test_pdf_extraction.py      # 分析前20页")
    print(f"   python scripts/test_pdf_extraction.py 50   # 分析前50页")
    print(f"   python scripts/test_pdf_extraction.py 0    # 分析所有页面")