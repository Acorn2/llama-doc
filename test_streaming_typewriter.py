#!/usr/bin/env python3

"""
测试流式打字机效果
演示不同的打字机预设配置
"""

import asyncio
import json
import time
from app.utils.streaming_utils import (
    TypewriterStreamer, 
    StreamingResponseBuilder, 
    StreamingPresets,
    create_typewriter_stream
)


async def test_basic_typewriter():
    """测试基础打字机效果"""
    print("=== 测试基础打字机效果 ===")
    
    text = "这是一个测试文本。它包含多个句子！还有一些问号？以及换行符。\n\n这是新的段落，用来测试段落延迟效果。"
    
    typewriter = TypewriterStreamer(
        chunk_size=1,
        delay=0.1,
        sentence_delay=0.3,
        paragraph_delay=0.6,
        enable_smart_delay=True
    )
    
    print("开始输出:")
    start_time = time.time()
    
    async for chunk in typewriter.stream_text(text):
        if chunk.type.value == "content":
            print(chunk.content, end='', flush=True)
        elif chunk.type.value == "final":
            print(f"\n\n输出完成，耗时: {time.time() - start_time:.2f}秒")


async def test_different_presets():
    """测试不同的预设配置"""
    print("\n=== 测试不同预设配置 ===")
    
    text = "人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。"
    
    presets = {
        "快速模式": StreamingPresets.FAST,
        "标准模式": StreamingPresets.STANDARD,
        "慢速模式": StreamingPresets.SLOW,
        "无延迟模式": StreamingPresets.NO_DELAY
    }
    
    for preset_name, preset_config in presets.items():
        print(f"\n--- {preset_name} ---")
        typewriter = TypewriterStreamer(**preset_config)
        
        start_time = time.time()
        async for chunk in typewriter.stream_text(text):
            if chunk.type.value == "content":
                print(chunk.content, end='', flush=True)
            elif chunk.type.value == "final":
                print(f" [耗时: {time.time() - start_time:.2f}s]")


async def test_conversation_stream():
    """测试对话流式输出"""
    print("\n=== 测试对话流式输出 ===")
    
    response_text = "根据您的问题，我可以为您提供以下信息：\n\n1. 机器学习是人工智能的一个重要分支\n2. 它通过算法让计算机从数据中学习\n3. 常见的应用包括图像识别、自然语言处理等"
    conversation_id = "test-conv-123"
    sources = [
        {"content": "机器学习基础知识", "score": 0.95},
        {"content": "人工智能应用案例", "score": 0.87}
    ]
    
    print("对话回复:")
    start_time = time.time()
    
    stream_generator = StreamingResponseBuilder.create_conversation_stream(
        response_text=response_text,
        conversation_id=conversation_id,
        sources=sources,
        processing_time=1.23,
        typewriter_config=StreamingPresets.STANDARD
    )
    
    async for sse_data in stream_generator:
        # 解析SSE数据
        if sse_data.startswith("data: "):
            json_data = sse_data[6:].strip()
            try:
                chunk_data = json.loads(json_data)
                if chunk_data["type"] == "content":
                    print(chunk_data["content"], end='', flush=True)
                elif chunk_data["type"] == "final":
                    print(f"\n\n对话完成，总耗时: {time.time() - start_time:.2f}秒")
                    print(f"元数据: {chunk_data['metadata']}")
            except json.JSONDecodeError:
                pass


async def test_agent_stream():
    """测试Agent流式输出"""
    print("\n=== 测试Agent流式输出 ===")
    
    response_data = {
        "answer": "经过分析，我发现以下几个关键点：\n\n首先，这个问题涉及到深度学习的核心概念。其次，需要考虑数据预处理的重要性。最后，模型的评估和优化也是关键环节。",
        "agent_mode": "analysis",
        "processing_time": 2.45,
        "sources": ["深度学习教程", "数据科学实践"]
    }
    
    kb_id = "kb-test-456"
    
    print("Agent分析结果:")
    start_time = time.time()
    
    stream_generator = StreamingResponseBuilder.create_agent_stream(
        response_data=response_data,
        kb_id=kb_id,
        use_agent=True,
        typewriter_config=StreamingPresets.STANDARD
    )
    
    async for sse_data in stream_generator:
        # 解析SSE数据
        if sse_data.startswith("data: "):
            json_data = sse_data[6:].strip()
            try:
                chunk_data = json.loads(json_data)
                if chunk_data["type"] == "content":
                    print(chunk_data["content"], end='', flush=True)
                elif chunk_data["type"] == "final":
                    print(f"\n\nAgent分析完成，总耗时: {time.time() - start_time:.2f}秒")
                    print(f"元数据: {chunk_data['metadata']}")
            except json.JSONDecodeError:
                pass


async def test_convenience_function():
    """测试便捷函数"""
    print("\n=== 测试便捷函数 ===")
    
    text = "这是使用便捷函数创建的打字机效果。它简化了使用流程，让开发者更容易集成打字机效果。"
    
    print("便捷函数输出:")
    start_time = time.time()
    
    async for sse_data in create_typewriter_stream(text, preset="FAST"):
        if sse_data.startswith("data: "):
            json_data = sse_data[6:].strip()
            try:
                chunk_data = json.loads(json_data)
                if chunk_data["type"] == "content":
                    print(chunk_data["content"], end='', flush=True)
                elif chunk_data["type"] == "final":
                    print(f"\n\n便捷函数完成，总耗时: {time.time() - start_time:.2f}秒")
            except json.JSONDecodeError:
                pass


async def main():
    """主测试函数"""
    print("🎯 流式打字机效果测试")
    print("=" * 50)
    
    # 运行所有测试
    await test_basic_typewriter()
    await test_different_presets()
    await test_conversation_stream()
    await test_agent_stream()
    await test_convenience_function()
    
    print("\n" + "=" * 50)
    print("✅ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())