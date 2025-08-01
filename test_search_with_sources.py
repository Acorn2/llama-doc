#!/usr/bin/env python3
"""
测试搜索功能的来源信息
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.services.agent_service import AgentService
from app.utils.exceptions import KnowledgeBaseNotFoundError, AgentError

async def test_search_with_sources():
    """测试搜索功能的来源信息"""
    print("=" * 60)
    print("测试搜索功能的来源信息")
    print("=" * 60)
    
    # 初始化服务
    agent_service = AgentService()
    
    # 获取数据库会话
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        # 测试参数
        test_kb_id = "d5a1b6d0-94fb-41ab-8628-791d4528f0bc"  # 通辽狠人
        test_query = "苏联"  # 测试查询
        
        print(f"知识库ID: {test_kb_id}")
        print(f"搜索查询: {test_query}")
        print("-" * 40)
        
        # 执行搜索
        try:
            result = await agent_service.search_knowledge(
                db=db,
                kb_id=test_kb_id,
                query=test_query,
                max_results=3,
                llm_type="qwen"
            )
            
            print("搜索结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # 分析结果结构
            if result.get("success") and result.get("data", {}).get("results"):
                results = result["data"]["results"]
                print(f"\n找到 {len(results)} 个结果:")
                
                for i, item in enumerate(results, 1):
                    print(f"\n结果 {i}:")
                    print(f"  内容预览: {item.get('content', '')[:100]}...")
                    
                    source = item.get('source', {})
                    print(f"  来源信息:")
                    print(f"    文档ID: {source.get('document_id', 'N/A')}")
                    print(f"    文档名称: {source.get('document_name', 'N/A')}")
                    print(f"    文件类型: {source.get('file_type', 'N/A')}")
                    print(f"    块索引: {source.get('chunk_index', 'N/A')}")
                    print(f"    相似度分数: {item.get('similarity_score', 'N/A')}")
                    
                    metadata = item.get('metadata', {})
                    if metadata.get('keywords'):
                        print(f"    关键词: {metadata['keywords']}")
            else:
                print("搜索失败或无结果")
                
        except KnowledgeBaseNotFoundError as e:
            print(f"知识库不存在: {e}")
        except AgentError as e:
            print(f"Agent错误: {e}")
        except Exception as e:
            print(f"搜索失败: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

async def test_agent_status():
    """测试Agent状态"""
    print("\n" + "=" * 60)
    print("测试Agent状态")
    print("=" * 60)
    
    agent_service = AgentService()
    
    try:
        test_kb_id = "d5a1b6d0-94fb-41ab-8628-791d4528f0bc"
        
        status = agent_service.get_agent_status(
            kb_id=test_kb_id,
            llm_type="qwen"
        )
        
        print("Agent状态:")
        print(json.dumps(status, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"获取状态失败: {e}")

if __name__ == "__main__":
    print(f"开始测试 - {datetime.now()}")
    
    # 运行测试
    asyncio.run(test_search_with_sources())
    asyncio.run(test_agent_status())
    
    print(f"\n测试完成 - {datetime.now()}")